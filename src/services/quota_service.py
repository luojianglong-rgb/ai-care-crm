"""
AI 额度管理服务
本地校验 AI 调用额度，根据套餐 tier 判断限制。

额度规则：
- 基础版: AI 总次数限制（用完即止，不重置）
- 专业版: AI 每周次数限制（每周一重置）
- 至尊版: AI 不限
- 开发模式: 绕过所有限制
"""
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func

from db_models import AIUsageRecord
from config import AppConfig


# usage_type → quota 字段名映射
_QUOTA_MAP = {
    "analysis": "ai_analysis_per_month",
    "plan": "ai_plan_per_month",
    "content": "ai_content_per_month",
}


class QuotaService:

    def __init__(self, config: AppConfig):
        self.config = config

    def _current_month_key(self) -> str:
        return datetime.now().strftime("%Y-%m")

    def _current_week_key(self) -> str:
        """获取当前周的 key（格式：YYYY-WW，基于 ISO 周）。"""
        return datetime.now().strftime("%Y-%W")

    def _week_start_date(self) -> datetime:
        """获取本周一的开始时间。"""
        today = datetime.now()
        return today - timedelta(days=today.weekday())

    def get_total_usage(self, db: Session, usage_type: str) -> int:
        """获取 AI 总使用次数（不限时间，用于基础版）。"""
        count = db.query(func.count(AIUsageRecord.id)).filter(
            AIUsageRecord.usage_type == usage_type,
            AIUsageRecord.success == 1,
        ).scalar()
        return count or 0

    def get_weekly_usage(self, db: Session, usage_type: str) -> int:
        """获取本周 AI 使用次数（用于专业版）。"""
        week_start = self._week_start_date()
        count = db.query(func.count(AIUsageRecord.id)).filter(
            AIUsageRecord.usage_type == usage_type,
            AIUsageRecord.success == 1,
            AIUsageRecord.created_at >= week_start,
        ).scalar()
        return count or 0

    def get_monthly_usage(self, db: Session, usage_type: str) -> int:
        """获取当月某类型的 AI 调用次数。"""
        month_key = self._current_month_key()
        count = db.query(func.count(AIUsageRecord.id)).filter(
            AIUsageRecord.usage_type == usage_type,
            AIUsageRecord.month_key == month_key,
            AIUsageRecord.success == 1,
        ).scalar()
        return count or 0

    def get_monthly_limit(self, usage_type: str) -> int:
        """获取当前套餐下某类型的月度上限。-1 表示不限。"""
        quota = self.config.get_quota()
        field_name = _QUOTA_MAP.get(usage_type)
        if field_name is None:
            return 0
        return getattr(quota, field_name, 0)

    def check_quota(self, db: Session, usage_type: str) -> tuple[bool, str]:
        """
        检查额度是否充足。
        返回 (allowed, message)。

        规则：
        - 开发模式: 绕过限制
        - 基础版: 检查 ai_total_limit（总次数）
        - 专业版: 检查 ai_weekly_limit（每周）
        - 至尊版: 检查月限额（每月 200 次）
        """
        # 开发模式绕过限制
        if self.config.server.dev_mode:
            return True, "开发模式：不限额度"

        tier = self.config.current_tier
        quota = self.config.get_quota()

        # 专业版：周限额
        if tier == "pro" and quota.ai_weekly_limit > 0:
            used = self.get_weekly_usage(db, usage_type)
            limit = quota.ai_weekly_limit
            if used >= limit:
                return False, f"本周 AI 额度已用完（{used}/{limit}），请激活正式版"
            return True, f"额度充足（本周 {used}/{limit}）"

        # 基础版：总次数限额
        if tier == "basic" and quota.ai_total_limit > 0:
            used = self.get_total_usage(db, usage_type)
            limit = quota.ai_total_limit
            if used >= limit:
                return False, f"AI 试用次数已用完（{used}/{limit}），请激活正式版"
            return True, f"额度充足（{used}/{limit}）"

        # Business 或兼容旧逻辑：月度限额
        limit = self.get_monthly_limit(usage_type)
        if limit == -1:
            return True, "不限额度"

        used = self.get_monthly_usage(db, usage_type)
        if limit > 0 and used >= limit:
            return False, f"本月额度已用完（{used}/{limit}），请下月再试"

        return True, f"额度充足（本月 {used}/{limit}）"

    def check_export_quota(self, db: Session) -> tuple[bool, str]:
        """检查数据导出额度（专业版每月 1 次）。"""
        # 开发模式绕过限制
        if self.config.server.dev_mode:
            return True, "开发模式：不限导出次数"

        tier = self.config.current_tier
        quota = self.config.get_quota()

        if tier == "business":
            return True, "至尊版不限导出次数"

        if tier == "pro" and quota.export_monthly > 0:
            # 检查本月导出次数（从 AIUsageRecord 中查找 type=export）
            month_key = self._current_month_key()
            count = db.query(func.count(AIUsageRecord.id)).filter(
                AIUsageRecord.usage_type == "export",
                AIUsageRecord.month_key == month_key,
            ).scalar() or 0
            if count >= quota.export_monthly:
                return False, f"本月导出次数已用完（{count}/{quota.export_monthly}）"
            return True, f"可导出（本月 {count}/{quota.export_monthly}）"

        return False, "数据导出为专业版功能，请激活正式版"

    def check_sms_quota(self, db: Session) -> tuple[bool, str]:
        """检查短信发送额度（至尊版每月 100 条）。"""
        # 开发模式绕过限制
        if self.config.server.dev_mode:
            return True, "开发模式：不限短信发送"

        tier = self.config.current_tier
        quota = self.config.get_quota()

        if tier != "business":
            return False, "短信发送为至尊版功能，请激活正式版"

        if quota.sms_monthly > 0:
            month_key = self._current_month_key()
            count = db.query(func.count(AIUsageRecord.id)).filter(
                AIUsageRecord.usage_type == "sms",
                AIUsageRecord.month_key == month_key,
            ).scalar() or 0
            if count >= quota.sms_monthly:
                return False, f"本月短信额度已用完（{count}/{quota.sms_monthly}）"
            return True, f"可发送（本月 {count}/{quota.sms_monthly}）"

        return True, "不限发送"

    def record_usage(self, db: Session, usage_type: str, client_id: str = None,
                     model_provider: str = "", model_name: str = "",
                     tokens_used: int = 0, success: bool = True,
                     error_message: str = None) -> AIUsageRecord:
        """记录一次 AI 调用。"""
        record = AIUsageRecord(
            usage_type=usage_type,
            client_id=client_id,
            model_provider=model_provider,
            model_name=model_name,
            tokens_used=tokens_used,
            cost_estimate=tokens_used * 0.00002,  # 粗估，按 DeepSeek 价格
            success=1 if success else 0,
            error_message=error_message,
            month_key=self._current_month_key(),
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    def get_usage_summary(self, db: Session) -> dict:
        """获取当月所有类型的使用情况摘要。"""
        tier = self.config.current_tier
        quota = self.config.get_quota()
        month_key = self._current_month_key()
        summary = {"month": month_key, "tier": tier}

        # AI 额度显示
        if tier == "basic" and quota.ai_total_limit > 0:
            # 基础版：显示总次数
            total_used = sum(self.get_total_usage(db, t) for t in ["analysis", "plan", "content"])
            summary["ai"] = {
                "used": total_used,
                "limit": quota.ai_total_limit,
                "remaining": max(0, quota.ai_total_limit - total_used),
                "unlimited": False,
                "type": "total",
            }
        elif tier == "pro" and quota.ai_weekly_limit > 0:
            # 专业版：显示周次数
            weekly_used = sum(self.get_weekly_usage(db, t) for t in ["analysis", "plan", "content"])
            summary["ai"] = {
                "used": weekly_used,
                "limit": quota.ai_weekly_limit,
                "remaining": max(0, quota.ai_weekly_limit - weekly_used),
                "unlimited": False,
                "type": "weekly",
            }
        else:
            # 至尊版：月度限额
            total_used = sum(self.get_monthly_usage(db, t) for t in ["analysis", "plan", "content"])
            limit = quota.ai_analysis_per_month
            summary["ai"] = {
                "used": total_used,
                "limit": limit,
                "remaining": max(0, limit - total_used) if limit > 0 else -1,
                "unlimited": limit == -1,
                "type": "monthly",
            }

        # 兼容旧 API 的分类型数据
        for usage_type, field_name in _QUOTA_MAP.items():
            used = self.get_monthly_usage(db, usage_type)
            limit = self.get_monthly_limit(usage_type)
            summary[usage_type] = {
                "used": used,
                "limit": limit,
                "remaining": -1 if limit == -1 else max(0, limit - used),
                "unlimited": limit == -1,
            }

        return summary
