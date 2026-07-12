"""
触发条件计算器
根据 playbook.trigger_type + trigger_config 计算今日应触发的客户列表。
支持 8 种触发类型（新增节假日关怀）。
"""
import logging
from datetime import datetime, timedelta, date
from sqlalchemy.orm import Session
from sqlalchemy import func

from db_models import ClientLifecycle, Client, Booking, CampaignTask
from playbook.solar_terms import SolarTermCalendar
from playbook.holidays import HolidayCalendar, should_trigger_holiday_care

logger = logging.getLogger(__name__)


class TriggerEvaluator:

    def evaluate(self, db: Session, playbook) -> list[str]:
        """
        根据剧本配置，返回今日应触发的 client_id 列表。
        已含 target_filter 和 cooldown 过滤。
        """
        trigger_type = playbook.trigger_type
        config = playbook.trigger_config or {}

        handler = getattr(self, f"_eval_{trigger_type}", None)
        if handler is None:
            logger.warning(f"Unknown trigger type: {trigger_type}")
            return []

        raw_ids = handler(db, config)
        if not raw_ids:
            return []

        # 应用 target_filter
        filtered = self._apply_target_filter(db, raw_ids, playbook.target_filter or {})
        # 应用 cooldown
        final = self._apply_cooldown(db, filtered, playbook.id, playbook.cooldown_days or 3)
        return final

    # ── 8 种触发类型 ──────────────────────────────────────────────

    def _eval_time_since_visit(self, db: Session, config: dict) -> list[str]:
        """距上次到店 N 天触发。"""
        days = config.get("days_since_visit", 30)
        cutoff = datetime.now() - timedelta(days=days)
        rows = db.query(ClientLifecycle.client_id).filter(
            ClientLifecycle.last_visit_at <= cutoff,
            ClientLifecycle.last_visit_at.isnot(None),
        ).all()
        return [r[0] for r in rows]

    def _eval_solar_term(self, db: Session, config: dict) -> list[str]:
        """节气/中医养生节点触发。
        支持传统节气和三伏、三九、长夏等中医养生节点。
        """
        days_before = config.get("days_before", 3)
        target_terms = config.get("terms", [])  # 如 ["三伏", "三九", "长夏", "立春", ...]

        # 获取下一个中医养生节点
        from playbook.solar_terms import SolarTermCalendar
        next_period, start_date, days_until = SolarTermCalendar.get_next_tcm_period(
            days_ahead=days_before * 2
        )

        if not next_period or days_until < 0 or days_until > days_before:
            return []

        # 如果配置了特定节点列表，检查是否匹配
        if target_terms and next_period not in target_terms:
            # 检查是否是节气且在目标列表中
            if next_period not in target_terms:
                return []

        # 触发：返回所有有 lifecycle 的客户
        rows = db.query(ClientLifecycle.client_id).all()
        return [r[0] for r in rows]

    def _eval_weather_change(self, db: Session, config: dict) -> list[str]:
        """天气骤变触发（当前简化：总是返回空，需接入天气 API 后实现）。"""
        # TODO: 接入和风天气 API
        return []

    def _eval_birthday(self, db: Session, config: dict) -> list[str]:
        """生日前 N 天触发。"""
        days_before = config.get("days_before", 7)
        target = (date.today() + timedelta(days=days_before)).strftime("%m-%d")
        rows = db.query(Client.client_id).filter(
            Client.birth_date.isnot(None),
            Client.birth_date.like(f"%-{target}"),
        ).all()
        return [r[0] for r in rows]

    def _eval_post_service(self, db: Session, config: dict) -> list[str]:
        """服务后 N 天触发。"""
        days = config.get("days_after_service", 3)
        target_date = (date.today() - timedelta(days=days))
        rows = db.query(Booking.client_id).filter(
            func.date(Booking.end_time) == target_date,
            Booking.status == "completed",
        ).distinct().all()
        return [r[0] for r in rows]

    def _eval_lifecycle_change(self, db: Session, config: dict) -> list[str]:
        """状态变更时触发（查昨日变更记录）。"""
        target_status = config.get("on_enter_status", "silent")
        yesterday = datetime.now() - timedelta(days=1)
        rows = db.query(ClientLifecycle.client_id).filter(
            ClientLifecycle.current_status == target_status,
            ClientLifecycle.status_changed_at >= yesterday,
        ).all()
        return [r[0] for r in rows]

    def _eval_holiday(self, db: Session, config: dict) -> list[str]:
        """节假日关怀触发（节前预约提醒 / 不出游客户关怀）。

        trigger_config 示例:
        {
            "care_type": "appointment_reminder" | "non_travel_care",
            "days_before": 7,  # 节前N天触发
            "holidays": ["spring_festival", "national_day"],  # 指定节假日，空=所有
            "target_non_travel": true,  # 是否筛选不出游客户
        }
        """
        days_before = config.get("days_before", 7)
        target_holidays = config.get("holidays", [])
        care_type = config.get("care_type", "appointment_reminder")
        target_non_travel = config.get("target_non_travel", False)

        # 获取即将到来的节假日
        upcoming = HolidayCalendar.get_upcoming_holidays(days_before)
        if not upcoming:
            return []

        # 筛选符合条件的节假日
        matching = []
        for h in upcoming:
            if target_holidays and h["key"] not in target_holidays:
                continue
            # 检查是否在节前关怀窗口内
            if h["days_until"] <= days_before:
                matching.append(h)

        if not matching:
            return []

        # 获取目标客户
        if care_type == "non_travel_care" and target_non_travel:
            # 筛选不出游客户特征
            client_ids = self._get_non_travel_clients(db)
        else:
            # 节前预约提醒：所有活跃客户
            rows = db.query(ClientLifecycle.client_id).filter(
                ClientLifecycle.current_status.in_(["active", "silent"])
            ).all()
            client_ids = [r[0] for r in rows]

        return client_ids

    def _eval_holiday_greeting(self, db: Session, config: dict) -> list[str]:
        """节日当天祝福问候触发。

        trigger_config 示例:
        {
            "holidays": ["spring_festival", "mid_autumn"],  # 指定节日
        }
        """
        target_holidays = config.get("holidays", [])

        # 判断今天是否是节假日
        is_holiday, holiday_info = HolidayCalendar.is_holiday_today()
        if not is_holiday:
            return []

        # 检查是否是目标节假日
        if target_holidays and holiday_info["key"] not in target_holidays:
            return []

        # 返回所有活跃客户
        rows = db.query(ClientLifecycle.client_id).filter(
            ClientLifecycle.current_status.in_(["new", "active", "silent"])
        ).all()
        return [r[0] for r in rows]

    def _get_non_travel_clients(self, db: Session) -> list[str]:
        """获取可能不出游的客户列表。

        筛选条件：
        - 年龄较大（40+）或偏好本地服务
        - 近期有到店记录
        - 有卡项余额
        """
        # 简化筛选：活跃客户 + 有余额
        rows = db.query(Client.client_id).join(
            ClientLifecycle, Client.client_id == ClientLifecycle.client_id
        ).filter(
            ClientLifecycle.current_status == "active",
            ClientLifecycle.last_visit_at >= datetime.now() - timedelta(days=30),
            (Client.times_card_balance > 0) | (Client.cash_card_balance > 100),
        ).all()
        return [r[0] for r in rows]

    # ── 过滤器 ────────────────────────────────────────────────────

    def _apply_target_filter(self, db: Session, client_ids: list[str],
                             target_filter: dict) -> list[str]:
        """按体质类型、生命周期状态等筛选目标客户。"""
        if not target_filter:
            return client_ids

        query = db.query(Client.client_id).filter(Client.client_id.in_(client_ids))

        lifecycle_status = target_filter.get("lifecycle_status")
        if lifecycle_status:
            lc_ids = db.query(ClientLifecycle.client_id).filter(
                ClientLifecycle.current_status == lifecycle_status
            ).all()
            lc_set = {r[0] for r in lc_ids}
            client_ids = [cid for cid in client_ids if cid in lc_set]

        analysis_type = target_filter.get("analysis_type")
        if analysis_type:
            query = query.filter(Client.primary_analysis_type == analysis_type)
            rows = query.all()
            type_set = {r[0] for r in rows}
            client_ids = [cid for cid in client_ids if cid in type_set]

        return client_ids

    def _apply_cooldown(self, db: Session, client_ids: list[str],
                        playbook_id: str, cooldown_days: int) -> list[str]:
        """排除 cooldown_days 内已触达的客户。"""
        if not client_ids or cooldown_days <= 0:
            return client_ids

        cutoff = datetime.now() - timedelta(days=cooldown_days)
        recent = db.query(CampaignTask.client_id).filter(
            CampaignTask.playbook_id == playbook_id,
            CampaignTask.client_id.in_(client_ids),
            CampaignTask.created_at >= cutoff,
        ).distinct().all()
        recent_set = {r[0] for r in recent}

        return [cid for cid in client_ids if cid not in recent_set]
