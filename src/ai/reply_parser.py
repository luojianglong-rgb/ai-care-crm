"""
客户回复语义解析
调用 LLM 分析客户回复的意图和情感，映射自动后续动作。
"""
import logging
from datetime import datetime
from sqlalchemy.orm import Session

from config import AppConfig
from ai.llm_client import LLMClient
from db_models import ClientReply, CampaignTask, Client

logger = logging.getLogger(__name__)

REPLY_ANALYSIS_PROMPT = """你是一个客户回复分析助手。请分析以下客户回复的意图和情感。

背景：我们之前向该客户发送了一条关怀消息：
"{original_message}"

客户回复：
"{reply_content}"

请严格按以下 JSON 格式返回，不要包含 markdown 代码块标记：
{{
  "intent": "symptom_improved / symptom_persists / want_booking / price_inquiry / general_chat / negative",
  "sentiment": "positive / neutral / negative",
  "symptoms_mentioned": ["如果回复中提到了具体症状或身体变化"],
  "needs_human_followup": true或false,
  "suggested_next_action": "建议的后续动作描述"
}}

intent 枚举说明：
- symptom_improved: 客户反馈症状好转、效果不错
- symptom_persists: 症状持续、效果不明显
- want_booking: 想预约/到店
- price_inquiry: 询问价格/优惠
- general_chat: 普通寒暄、感谢等
- negative: 负面情绪、投诉、不满
"""

# 意图 → 自动动作映射
INTENT_ACTION_MAP = {
    "symptom_improved": "updated_health_record",
    "symptom_persists": "triggered_followup",
    "want_booking": "none",           # 需人工跟进预约
    "price_inquiry": "none",          # 需人工回复
    "general_chat": "none",
    "negative": "notified_manager",   # 通知店长
}


class ReplyParser:

    def __init__(self, config: AppConfig, llm: LLMClient):
        self.config = config
        self.llm = llm

    def parse_and_save(self, db: Session, client_id: str, raw_content: str,
                       campaign_task_id: str = None) -> dict:
        """
        解析客户回复并存储。
        返回 {"success": bool, "data": dict, "error": str}
        """
        # 获取关联的营销消息（如有）
        original_message = ""
        if campaign_task_id:
            task = db.query(CampaignTask).filter(CampaignTask.id == campaign_task_id).first()
            if task:
                original_message = task.generated_content or ""

        # AI 解析
        parsed = None
        if self.llm.is_available and raw_content.strip():
            prompt = REPLY_ANALYSIS_PROMPT.format(
                original_message=original_message or "（无关联消息）",
                reply_content=raw_content,
            )
            result, resp = self.llm.chat_json(prompt, "请分析", temperature=0.2)
            if result:
                parsed = result

        # 确定意图和动作
        intent = parsed.get("intent", "general_chat") if parsed else "general_chat"
        sentiment = parsed.get("sentiment", "neutral") if parsed else "neutral"
        details = {
            "sentiment": sentiment,
            "symptoms_mentioned": parsed.get("symptoms_mentioned", []) if parsed else [],
            "needs_human_followup": parsed.get("needs_human_followup", False) if parsed else False,
            "suggested_next_action": parsed.get("suggested_next_action", "") if parsed else "",
        }
        auto_action = INTENT_ACTION_MAP.get(intent, "none")

        # 存储
        reply = ClientReply(
            client_id=client_id,
            campaign_task_id=campaign_task_id or None,
            raw_content=raw_content,
            ai_parsed_intent=intent,
            ai_parsed_details=details,
            auto_action_taken=auto_action,
        )
        db.add(reply)
        db.commit()
        db.refresh(reply)

        return {
            "success": True,
            "data": {
                "id": reply.id,
                "client_id": reply.client_id,
                "raw_content": reply.raw_content,
                "intent": intent,
                "sentiment": sentiment,
                "details": details,
                "auto_action": auto_action,
                "created_at": reply.created_at.isoformat() if reply.created_at else None,
            },
            "error": "",
        }
