"""
AI 智能触达引擎
分析客户状态，智能判断触达时机和内容类型。
双层触达体系：剧本触发（关键业务规则）+ AI智能触发（日常智能判断）。
"""
import logging
import json
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func

from config import AppConfig
from ai.llm_client import LLMClient
from db_models import (
    Client, ClientLifecycle, Booking, CampaignTask,
    ClientReply, ProfessionalAnalysis, Transaction
)

logger = logging.getLogger(__name__)

# AI智能触达约束配置
AI_REACH_CONSTRAINTS = {
    "max_frequency_days": 7,       # 同一客户最多每7天1次AI触达
    "cooldown_after_playbook": 7,  # 剧本触达后7天内不触发AI触达
    "booking_exempt_days": 3,      # 有未来预约的客户豁免触达
    "min_days_since_visit": 5,     # 最少5天未到店才考虑触达
}


class IntelligentReachEngine:
    """AI智能触达引擎"""

    def __init__(self, config: AppConfig, llm: LLMClient):
        self.config = config
        self.llm = llm

    def scan_clients(self, db: Session, max_clients: int = 50) -> dict:
        """
        扫描所有活跃客户，AI判断是否需要触达。
        返回: {"analyzed": int, "suggestions": list, "errors": list}
        """
        logger.info("=== AI Intelligent Reach Scan Started ===")
        summary = {"analyzed": 0, "suggestions": [], "errors": []}

        # 1. 获取候选客户（排除有明显豁免条件的）
        candidate_ids = self._get_candidate_clients(db, max_clients)
        summary["analyzed"] = len(candidate_ids)

        if not candidate_ids:
            logger.info("No candidates for AI reach analysis")
            return summary

        # 2. 对每个客户进行AI分析
        for cid in candidate_ids:
            try:
                suggestion = self.analyze_client(db, cid)
                if suggestion and suggestion.get("should_reach"):
                    summary["suggestions"].append(suggestion)
            except Exception as e:
                logger.error(f"AI analysis failed for {cid}: {e}")
                summary["errors"].append(str(e))

        logger.info(f"=== AI Reach Scan Done: {len(summary['suggestions'])} suggestions ===")
        return summary

    def analyze_client(self, db: Session, client_id: str) -> dict | None:
        """
        AI分析单个客户，返回触达建议。
        返回: {
            "client_id": str,
            "should_reach": bool,
            "urgency": "high/medium/low",
            "content_type": str,
            "reason": str,
            "recommended_services": list,
            "variables": dict  # 用于文案生成
        }
        """
        client = db.query(Client).filter(Client.client_id == client_id).first()
        if not client:
            return None

        # 收集客户画像
        profile = self._get_client_profile(db, client)

        # 快速规则过滤（避免不必要的AI调用）
        if self._quick_filter(profile):
            return {"client_id": client_id, "should_reach": False, "reason": "快速规则过滤"}

        # LLM不可用时返回简单建议
        if not self.llm.is_available:
            return self._fallback_suggestion(profile)

        # 调用AI分析
        prompt = self._build_analysis_prompt(profile)
        parsed, response = self.llm.chat_json(prompt, "请返回JSON格式的分析结果")

        if not parsed:
            logger.warning(f"AI analysis parse failed for {client_id}")
            return self._fallback_suggestion(profile)

        # 构建完整的建议
        suggestion = {
            "client_id": client_id,
            "client_name": client.name,
            "should_reach": parsed.get("should_reach", False),
            "urgency": parsed.get("urgency", "low"),
            "content_type": parsed.get("content_type", "general_care"),
            "reason": parsed.get("reason", ""),
            "recommended_services": parsed.get("recommended_services", []),
            "variables": self._build_content_variables(profile),
        }

        return suggestion

    def _get_candidate_clients(self, db: Session, max_clients: int) -> list[str]:
        """获取候选客户ID列表（排除明显豁免的）"""
        now = datetime.now()

        # 获取所有活跃客户（非流失预警）
        active_clients = db.query(ClientLifecycle.client_id).filter(
            ClientLifecycle.current_status.in_(["new", "active", "silent"])
        ).limit(max_clients * 2).all()

        candidate_ids = [r[0] for r in active_clients]

        # 过滤：
        # 1. 有未来预约的豁免
        # 2. 最近有剧本触达的豁免
        # 3. 最近有AI触达的豁免

        # 有未来预约
        future_bookings = db.query(Booking.client_id).filter(
            Booking.start_time >= now - timedelta(days=AI_REACH_CONSTRAINTS["booking_exempt_days"]),
            Booking.status.in_(["pending", "confirmed"])
        ).distinct().all()
        exempt_booking = {r[0] for r in future_bookings}

        # 最近剧本触达
        recent_playbook = db.query(CampaignTask.client_id).filter(
            CampaignTask.created_at >= now - timedelta(days=AI_REACH_CONSTRAINTS["cooldown_after_playbook"]),
            CampaignTask.status.in_(["approved", "queued", "sent"])
        ).distinct().all()
        exempt_playbook = {r[0] for r in recent_playbook}

        # 最近AI触达记录（需要从CampaignTask中识别，或新增表）
        # 暂时用CampaignTask的playbook_id为空来判断AI触达
        recent_ai = db.query(CampaignTask.client_id).filter(
            CampaignTask.created_at >= now - timedelta(days=AI_REACH_CONSTRAINTS["max_frequency_days"]),
            CampaignTask.playbook_id.is_(None)  # AI触达没有playbook_id
        ).distinct().all()
        exempt_ai = {r[0] for r in recent_ai}

        # 应用过滤
        filtered = [
            cid for cid in candidate_ids
            if cid not in exempt_booking
            and cid not in exempt_playbook
            and cid not in exempt_ai
        ]

        return filtered[:max_clients]

    def _get_client_profile(self, db: Session, client: Client) -> dict:
        """收集客户画像信息"""
        now = datetime.now()

        # 生命周期
        lc = db.query(ClientLifecycle).filter(
            ClientLifecycle.client_id == client.client_id
        ).first()

        days_since_visit = 0
        if lc and lc.last_visit_at:
            days_since_visit = (now - lc.last_visit_at).days

        # 最近预约
        upcoming_bookings = db.query(Booking).filter(
            Booking.client_id == client.client_id,
            Booking.start_time >= now,
            Booking.status.in_(["pending", "confirmed"])
        ).all()
        upcoming_str = ", ".join([b.service_name for b in upcoming_bookings]) if upcoming_bookings else "无"

        # 最近消费
        recent_transactions = db.query(func.sum(Transaction.amount)).filter(
            Transaction.client_id == client.client_id,
            Transaction.date >= now - timedelta(days=30)
        ).scalar() or 0.0

        # 最近触达历史
        recent_tasks = db.query(CampaignTask).filter(
            CampaignTask.client_id == client.client_id,
            CampaignTask.created_at >= now - timedelta(days=30)
        ).order_by(CampaignTask.created_at.desc()).limit(5).all()
        touch_history = [
            {"date": t.created_at.strftime("%Y-%m-%d"), "status": t.status}
            for t in recent_tasks
        ]

        # 最近回复
        recent_replies = db.query(ClientReply).filter(
            ClientReply.client_id == client.client_id,
            ClientReply.replied_at >= now - timedelta(days=30)
        ).order_by(ClientReply.replied_at.desc()).limit(3).all()
        reply_history = [r.raw_content[:50] for r in recent_replies if r.raw_content]

        # 专业分析
        analysis = db.query(ProfessionalAnalysis).filter(
            ProfessionalAnalysis.client_id == client.client_id
        ).order_by(ProfessionalAnalysis.assessed_at.desc()).first()

        analysis_type = client.primary_analysis_type or "未分析"
        analysis_details = {}
        if analysis:
            analysis_details = {
                "domain": analysis.domain,
                "primary_type": analysis.primary_type,
                "symptoms": analysis.symptoms_snapshot or {},
                "recommendations": analysis.ai_recommendations or {},
            }

        # 获取当前季节信息
        from playbook.solar_terms import SolarTermCalendar
        tcm_context = SolarTermCalendar.get_current_tcm_context()

        return {
            "client_id": client.client_id,
            "name": client.name or "客户",
            "phone": client.phone,
            "gender": client.gender,
            "age_group": client.age_group,
            "birth_date": client.birth_date,
            "lifecycle_status": lc.current_status if lc else "new",
            "days_since_visit": days_since_visit,
            "upcoming_bookings": upcoming_str,
            "recent_spending": recent_transactions,
            "touch_history": touch_history,
            "reply_history": reply_history,
            "analysis_type": analysis_type,
            "analysis_details": analysis_details,
            "times_card_balance": client.times_card_balance,
            "cash_card_balance": client.cash_card_balance,
            "preferences": client.preferences or [],
            "business_type": self.config.store.business_type,
            "season": tcm_context["season_display"],
            "tcm_periods": tcm_context["active_periods"],
        }

    def _quick_filter(self, profile: dict) -> bool:
        """快速规则过滤，返回True表示应该豁免"""
        # 1. 有预约豁免
        if profile["upcoming_bookings"] != "无":
            return True

        # 2. 太近刚到店
        if profile["days_since_visit"] < AI_REACH_CONSTRAINTS["min_days_since_visit"]:
            return True

        # 3. 最近刚触达过（从touch_history判断）
        if profile["touch_history"]:
            last_touch = profile["touch_history"][0]
            last_date = datetime.strptime(last_touch["date"], "%Y-%m-%d")
            if (datetime.now() - last_date).days < AI_REACH_CONSTRAINTS["max_frequency_days"]:
                return True

        return False

    def _build_analysis_prompt(self, profile: dict) -> str:
        """构建AI分析的Prompt"""
        business_display = self.config.get_terminology("analysis_name") or profile["business_type"]

        prompt = f"""你是{profile['business_type']}行业的专业客户关系顾问。
请分析以下客户是否需要进行智能触达，并给出建议。

## 客户画像
- 姓名：{profile['name']}
- 生命周期状态：{profile['lifecycle_status']}
- 上次到店：{profile['days_since_visit']}天前
- 近期预约：{profile['upcoming_bookings']}
- 专业分析：{profile['analysis_type']}
- 卡项余额：次卡{profile['times_card_balance']}次，储值{profile['cash_card_balance']}元
- 偏好项目：{', '.join(profile['preferences']) if profile['preferences'] else '未记录'}
- 近期消费：{profile['recent_spending']}元
- 近期触达历史：{json.dumps(profile['touch_history'], ensure_ascii=False)}
- 近期回复：{profile['reply_history'][:2] if profile['reply_history'] else '无'}

## 当前环境
- 业态：{business_display}
- 季节：{profile['season']}
- 养生节点：{', '.join(profile['tcm_periods']) if profile['tcm_periods'] else '无'}

## 分析要求
1. 判断是否需要触达（综合考虑：到店间隔、卡项余额、季节适配、触达历史）
2. 如需触达，判断紧迫程度（high/medium/low）
3. 选择最合适的内容类型：
   - general_care: 一般关怀问候
   - seasonal_care: 季节/节气养生提醒
   - service_recommend: 服务项目推荐
   - card_reminder: 卡项余额提醒
   - followup: 服务效果随访
   - wakeup: 沉默客户唤醒
4. 给出触达理由
5. 推荐1-2个适合的服务项目（基于体质/季节）

## 返回格式（JSON）
{
    "should_reach": true/false,
    "urgency": "high/medium/low",
    "content_type": "内容类型",
    "reason": "触达理由",
    "recommended_services": ["服务1", "服务2"]
}
"""
        return prompt

    def _fallback_suggestion(self, profile: dict) -> dict:
        """LLM不可用时的兜底建议"""
        # 简单规则：根据到店间隔判断
        days = profile["days_since_visit"]

        if days >= 30:
            content_type = "wakeup"
            urgency = "high"
        elif days >= 14:
            content_type = "followup"
            urgency = "medium"
        elif profile["tcm_periods"]:
            content_type = "seasonal_care"
            urgency = "low"
        else:
            content_type = "general_care"
            urgency = "low"

        return {
            "client_id": profile["client_id"],
            "client_name": profile["name"],
            "should_reach": True,
            "urgency": urgency,
            "content_type": content_type,
            "reason": f"距上次到店{days}天，建议触达",
            "recommended_services": profile["preferences"][:2] if profile["preferences"] else [],
            "variables": self._build_content_variables(profile),
        }

    def _build_content_variables(self, profile: dict) -> dict:
        """构建文案生成所需的变量"""
        return {
            "client_name": profile["name"],
            "analysis_type": profile["analysis_type"],
            "days_info": f"{profile['days_since_visit']}天",
            "season": profile["season"],
            "tcm_period": ", ".join(profile["tcm_periods"]) if profile["tcm_periods"] else profile["season"],
            "times_card_balance": profile["times_card_balance"],
            "cash_card_balance": profile["cash_card_balance"],
            "preferences": profile["preferences"],
            "business_display": self.config.get_terminology("analysis_name") or self.config.store.business_type,
        }

    def create_ai_task(self, db: Session, suggestion: dict) -> CampaignTask | None:
        """根据AI建议创建触达任务"""
        if not suggestion.get("should_reach"):
            return None

        # 内容类型映射到文案场景
        content_type_map = {
            "general_care": "seasonal_care",
            "seasonal_care": "seasonal_care",
            "service_recommend": "post_service_followup",
            "card_reminder": "silent_client_wakeup",
            "followup": "post_service_followup",
            "wakeup": "silent_client_wakeup",
        }

        scene = content_type_map.get(suggestion["content_type"], "seasonal_care")

        # 创建任务（playbook_id为None表示AI智能触达）
        task = CampaignTask(
            playbook_id=None,  # AI触达没有剧本ID
            client_id=suggestion["client_id"],
            generated_content="",  # 后续由ContentGenerator填充
            status="pending_approval",
            approval_mode="manual",  # AI触达默认需要审批
            is_sampled=0,
            ai_content_type=suggestion.get("content_type", "general_care"),  # AI触达类型
            ai_reason=suggestion.get("reason", ""),  # AI判断理由
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        return task