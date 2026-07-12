"""
客户回复 API
/api/v1/replies/*
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
from config import get_config
from ai.llm_client import get_llm_client
from ai.reply_parser import ReplyParser
from db_models import ClientReply

router = APIRouter()
logger = logging.getLogger(__name__)


class SubmitReplyRequest(BaseModel):
    client_id: str
    raw_content: str
    campaign_task_id: Optional[str] = None


class ReplyOut(BaseModel):
    id: str
    client_id: str
    raw_content: str
    intent: Optional[str] = None
    sentiment: Optional[str] = None
    details: dict = {}
    auto_action: Optional[str] = None
    campaign_task_id: Optional[str] = None
    created_at: Optional[str] = None


class OverrideActionRequest(BaseModel):
    action: str  # 人工覆盖的后续动作


@router.post("/", response_model=ReplyOut)
def submit_reply(req: SubmitReplyRequest, db: Session = Depends(get_db)):
    """提交客户回复（手动录入或 RPA 采集），AI 自动解析意图。"""
    config = get_config()
    llm = get_llm_client()
    parser = ReplyParser(config, llm)
    result = parser.parse_and_save(
        db, client_id=req.client_id,
        raw_content=req.raw_content,
        campaign_task_id=req.campaign_task_id,
    )
    if result["success"]:
        d = result["data"]
        return ReplyOut(
            id=d["id"], client_id=d["client_id"],
            raw_content=d["raw_content"], intent=d["intent"],
            sentiment=d["sentiment"], details=d["details"],
            auto_action=d["auto_action"],
            campaign_task_id=req.campaign_task_id,
            created_at=d["created_at"],
        )
    raise HTTPException(500, result["error"])


@router.get("/", response_model=list[ReplyOut])
def list_replies(
    client_id: Optional[str] = None,
    intent: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    db: Session = Depends(get_db),
):
    """获取回复列表（支持按客户/意图筛选）。"""
    query = db.query(ClientReply).order_by(ClientReply.created_at.desc())
    if client_id:
        query = query.filter(ClientReply.client_id == client_id)
    if intent:
        query = query.filter(ClientReply.ai_parsed_intent == intent)
    replies = query.limit(limit).all()
    return [_reply_to_out(r) for r in replies]


@router.get("/{reply_id}", response_model=ReplyOut)
def get_reply(reply_id: str, db: Session = Depends(get_db)):
    """获取单条回复详情。"""
    r = db.query(ClientReply).filter(ClientReply.id == reply_id).first()
    if not r:
        raise HTTPException(404, "回复不存在")
    return _reply_to_out(r)


@router.post("/{reply_id}/action")
def override_action(reply_id: str, req: OverrideActionRequest, db: Session = Depends(get_db)):
    """人工确认/覆盖 AI 建议的后续动作。"""
    r = db.query(ClientReply).filter(ClientReply.id == reply_id).first()
    if not r:
        raise HTTPException(404, "回复不存在")
    r.auto_action_taken = req.action
    db.commit()
    return {"success": True, "reply_id": reply_id, "action": req.action}


@router.post("/collect/sms")
def collect_sms_messages(db: Session = Depends(get_db)):
    """采集短信回复并 AI 解析。

    从 ML307A 短信猫读取新短信，存入回复表，AI 解析意图。
    支持意见反馈、预约等分类，提示管理员处理。
    """
    from services.sms_receiver_service import get_sms_receiver_service
    from channels.drivers.ml307a import ML307ADriver
    from ai.llm_client import get_llm_client
    from ai.reply_parser import ReplyParser
    from db_models import Client
    import uuid

    config = get_config()
    raw_channels = config.raw.get("channels", {}) if hasattr(config, 'raw') else {}
    ml307a_config = raw_channels.get("ml307a", {})

    if not ml307a_config.get("enabled", False):
        return {"success": False, "message": "ML307A 短信功能未启用"}

    # 获取短信接收服务
    driver = ML307ADriver(ml307a_config)
    receiver = get_sms_receiver_service(driver)
    receiver.start()

    # 检查新短信
    receiver._check_new_sms()

    # 获取待处理短信
    pending_sms = receiver.get_pending_sms()

    if not pending_sms:
        return {"success": True, "collected": 0, "message": "无新短信"}

    # AI 解析器
    llm = get_llm_client()
    parser = ReplyParser(config, llm)

    saved_count = 0
    parsed_count = 0

    for sms in pending_sms:
        try:
            # 查找关联客户
            sender_clean = sms.sender.replace('+86', '').replace('+', '')
            client = db.query(Client).filter(Client.phone == sender_clean).first()

            # 创建回复记录
            reply = ClientReply(
                id=str(uuid.uuid4()),
                client_id=str(client.id) if client else None,
                raw_content=sms.content,
                campaign_task_id=None,
            )
            db.add(reply)
            db.flush()  # 获取 ID

            # AI 解析
            try:
                parsed = parser.parse(sms.content)
                reply.ai_parsed_intent = parsed.get("intent") or sms.category.value
                reply.ai_parsed_details = {
                    **parsed.get("details", {}),
                    "sms_category": sms.category.value,
                    "sender": sender_clean,
                    "received_at": sms.received_at.isoformat()
                }
                reply.auto_action_taken = parsed.get("suggested_action")
                parsed_count += 1
            except Exception as e:
                logger.error(f"[短信采集] AI 解析失败: {e}")
                reply.ai_parsed_intent = sms.category.value

            saved_count += 1

        except Exception as e:
            logger.error(f"[短信采集] 保存失败: {e}")

    db.commit()

    return {
        "success": True,
        "collected": saved_count,
        "parsed": parsed_count,
        "message": f"采集 {saved_count} 条短信，解析 {parsed_count} 条"
    }


def _reply_to_out(r: ClientReply) -> ReplyOut:
    details = r.ai_parsed_details or {}
    return ReplyOut(
        id=r.id, client_id=r.client_id,
        raw_content=r.raw_content or "",
        intent=r.ai_parsed_intent,
        sentiment=details.get("sentiment"),
        details=details,
        auto_action=r.auto_action_taken,
        campaign_task_id=r.campaign_task_id,
        created_at=r.created_at.isoformat() if r.created_at else None,
    )
