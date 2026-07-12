"""
剧本管理 + 营销任务 API 端点
/api/v1/playbooks/* + /api/v1/campaigns/*
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from database import get_db
from config import get_config
from ai.llm_client import get_llm_client
from db_models import Playbook, CampaignTask, ClientLifecycle, Client
from playbook.engine import PlaybookEngine
from playbook.approval import ApprovalManager
from playbook.lifecycle import LifecycleManager
from sqlalchemy import func

playbook_router = APIRouter()
campaign_router = APIRouter()


# ── 请求/响应模型 ────────────────────────────────────────────────

class PlaybookCreate(BaseModel):
    name: str
    description: str = ""
    trigger_type: str
    trigger_config: dict = {}
    target_filter: dict = {}
    content_template: str = ""
    approval_mode: str = "auto"
    sampling_rate: float = 0.1
    send_window_start: str = "09:00"
    send_window_end: str = "18:00"
    send_channel: str = "auto"
    priority: int = 5
    cooldown_days: int = 3


class PlaybookUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    trigger_config: Optional[dict] = None
    target_filter: Optional[dict] = None
    content_template: Optional[str] = None
    approval_mode: Optional[str] = None
    sampling_rate: Optional[float] = None
    send_window_start: Optional[str] = None
    send_window_end: Optional[str] = None
    send_channel: Optional[str] = None
    priority: Optional[int] = None
    cooldown_days: Optional[int] = None


class PlaybookOut(BaseModel):
    id: str
    name: str
    description: str
    trigger_type: str
    trigger_config: dict
    target_filter: dict
    approval_mode: str
    send_channel: str
    is_active: int
    is_system: int = 0
    priority: int = 5
    cooldown_days: int = 3
    task_count: int = 0
    pending_count: int = 0


class TaskOut(BaseModel):
    id: str
    playbook_id: str
    playbook_name: str
    client_id: str
    client_name: str
    generated_content: str
    status: str
    approval_mode: str
    send_channel: str
    scheduled_at: Optional[str] = None
    sent_at: Optional[str] = None
    created_at: Optional[str] = None
    error_message: Optional[str] = None


class BatchApproveRequest(BaseModel):
    playbook_id: str


class RejectRequest(BaseModel):
    reason: str = ""


class LifecycleStatsOut(BaseModel):
    new: int = 0
    active: int = 0
    silent: int = 0
    churn_risk: int = 0
    total: int = 0


# ── 剧本 API ─────────────────────────────────────────────────────

@playbook_router.get("/", response_model=list[PlaybookOut])
def list_playbooks(db: Session = Depends(get_db)):
    """获取所有剧本（含任务统计）。"""
    playbooks = db.query(Playbook).order_by(Playbook.priority).all()
    result = []
    for pb in playbooks:
        task_count = db.query(func.count(CampaignTask.id)).filter(
            CampaignTask.playbook_id == pb.id).scalar() or 0
        pending_count = db.query(func.count(CampaignTask.id)).filter(
            CampaignTask.playbook_id == pb.id,
            CampaignTask.status == "pending_approval").scalar() or 0
        result.append(PlaybookOut(
            id=pb.id, name=pb.name, description=pb.description or "",
            trigger_type=pb.trigger_type, trigger_config=pb.trigger_config or {},
            target_filter=pb.target_filter or {},
            approval_mode=pb.approval_mode or "auto",
            send_channel=pb.send_channel or "auto",
            is_active=pb.is_active or 0,
            is_system=pb.is_system or 0,
            priority=pb.priority or 5,
            cooldown_days=pb.cooldown_days or 3,
            task_count=task_count, pending_count=pending_count,
        ))
    return result


@playbook_router.post("/", response_model=PlaybookOut)
def create_playbook(req: PlaybookCreate, db: Session = Depends(get_db)):
    """创建自定义剧本。"""
    config = get_config()
    if not config.get_quota().custom_playbooks:
        raise HTTPException(400, "基础版不支持自定义剧本，请升级专业版")
    pb = Playbook(**req.model_dump(), is_system=0)
    db.add(pb)
    db.commit()
    db.refresh(pb)
    return PlaybookOut(
        id=pb.id, name=pb.name, description=pb.description or "",
        trigger_type=pb.trigger_type, trigger_config=pb.trigger_config or {},
        target_filter=pb.target_filter or {},
        approval_mode=pb.approval_mode or "auto",
        send_channel=pb.send_channel or "auto",
        is_active=pb.is_active, is_system=pb.is_system,
        priority=pb.priority, cooldown_days=pb.cooldown_days,
    )


@playbook_router.put("/{playbook_id}")
def update_playbook(playbook_id: str, req: PlaybookUpdate, db: Session = Depends(get_db)):
    """更新剧本配置。"""
    pb = db.query(Playbook).filter(Playbook.id == playbook_id).first()
    if not pb:
        raise HTTPException(404, "剧本不存在")
    for field, value in req.model_dump(exclude_none=True).items():
        setattr(pb, field, value)
    pb.updated_at = datetime.now()
    db.commit()
    return {"success": True}


@playbook_router.put("/{playbook_id}/toggle")
def toggle_playbook(playbook_id: str, db: Session = Depends(get_db)):
    """启用/停用剧本。"""
    pb = db.query(Playbook).filter(Playbook.id == playbook_id).first()
    if not pb:
        raise HTTPException(404, "剧本不存在")
    pb.is_active = 0 if pb.is_active else 1
    db.commit()
    return {"success": True, "is_active": pb.is_active}


@playbook_router.delete("/{playbook_id}")
def delete_playbook(playbook_id: str, db: Session = Depends(get_db)):
    """删除自定义剧本（系统预设不可删）。"""
    pb = db.query(Playbook).filter(Playbook.id == playbook_id).first()
    if not pb:
        raise HTTPException(404, "剧本不存在")
    if pb.is_system:
        raise HTTPException(400, "系统预设剧本不可删除")
    db.delete(pb)
    db.commit()
    return {"success": True}


@playbook_router.post("/{playbook_id}/preview")
def preview_playbook(playbook_id: str, db: Session = Depends(get_db)):
    """预览：模拟执行并返回示例文案（不实际发送）。"""
    config = get_config()
    llm = get_llm_client()
    engine = PlaybookEngine(config, llm)
    return engine.preview_playbook(db, playbook_id)


@playbook_router.post("/scan")
def manual_scan(db: Session = Depends(get_db)):
    """手动触发一次剧本扫描（等同于每日定时任务）。"""
    config = get_config()
    llm = get_llm_client()
    engine = PlaybookEngine(config, llm)
    return engine.daily_scan(db)


@playbook_router.get("/lifecycle/stats", response_model=LifecycleStatsOut)
def get_lifecycle_stats(db: Session = Depends(get_db)):
    """获取各生命周期状态客户数量统计。"""
    lm = LifecycleManager()
    lm.init_all_clients(db)
    stats = lm.get_stats(db)
    total = sum(stats.values())
    return LifecycleStatsOut(
        new=stats.get("new", 0),
        active=stats.get("active", 0),
        silent=stats.get("silent", 0),
        churn_risk=stats.get("churn_risk", 0),
        total=total,
    )


@playbook_router.get("/lifecycle/client/{client_id}")
def get_client_lifecycle(client_id: str, db: Session = Depends(get_db)):
    """获取单个客户的生命周期详情。"""
    from db_models import Client
    lc = db.query(ClientLifecycle).filter(ClientLifecycle.client_id == client_id).first()
    client = db.query(Client).filter(Client.client_id == client_id).first()
    if not client:
        raise HTTPException(404, "客户不存在")
    if not lc:
        return {
            "client_id": client_id, "client_name": client.name,
            "current_status": client.lifecycle_status or "new",
            "visit_count": 0, "last_visit_at": None, "last_contact_at": None,
            "status_changed_at": None,
        }
    return {
        "client_id": client_id, "client_name": client.name,
        "current_status": lc.current_status,
        "visit_count": lc.visit_count,
        "last_visit_at": lc.last_visit_at.isoformat() if lc.last_visit_at else None,
        "last_contact_at": lc.last_contact_at.isoformat() if lc.last_contact_at else None,
        "status_changed_at": lc.status_changed_at.isoformat() if lc.status_changed_at else None,
    }


# ── 营销任务 API ──────────────────────────────────────────────────

@campaign_router.get("/tasks", response_model=list[TaskOut])
def list_tasks(
    status: Optional[str] = None,
    playbook_id: Optional[str] = None,
    client_id: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    db: Session = Depends(get_db),
):
    """查询营销任务列表。"""
    query = db.query(CampaignTask).order_by(CampaignTask.created_at.desc())
    if status:
        query = query.filter(CampaignTask.status == status)
    if playbook_id:
        query = query.filter(CampaignTask.playbook_id == playbook_id)
    if client_id:
        query = query.filter(CampaignTask.client_id == client_id)
    tasks = query.limit(limit).all()
    return [_task_to_out(db, t) for t in tasks]


@campaign_router.get("/tasks/pending", response_model=list[TaskOut])
def list_pending_tasks(db: Session = Depends(get_db)):
    """获取待审批任务。"""
    tasks = db.query(CampaignTask).filter(
        CampaignTask.status == "pending_approval"
    ).order_by(CampaignTask.created_at.desc()).all()
    return [_task_to_out(db, t) for t in tasks]


@campaign_router.put("/tasks/{task_id}/approve")
def approve_task(task_id: str, db: Session = Depends(get_db)):
    """审批通过单条。"""
    am = ApprovalManager()
    if am.approve(db, task_id):
        return {"success": True}
    raise HTTPException(400, "任务不存在或状态不允许审批")


@campaign_router.put("/tasks/{task_id}/reject")
def reject_task(task_id: str, req: RejectRequest, db: Session = Depends(get_db)):
    """驳回单条。"""
    am = ApprovalManager()
    if am.reject(db, task_id, req.reason):
        return {"success": True}
    raise HTTPException(400, "任务不存在或状态不允许驳回")


@campaign_router.post("/tasks/batch-approve")
def batch_approve(req: BatchApproveRequest, db: Session = Depends(get_db)):
    """批量审批某剧本下所有待审批任务。"""
    am = ApprovalManager()
    count = am.approve_batch(db, req.playbook_id)
    return {"success": True, "approved_count": count}


@campaign_router.get("/tasks/{task_id}/preview")
def preview_task(task_id: str, db: Session = Depends(get_db)):
    """预览单条任务文案。"""
    task = db.query(CampaignTask).filter(CampaignTask.id == task_id).first()
    if not task:
        raise HTTPException(404, "任务不存在")
    return {
        "id": task.id,
        "content": task.generated_content,
        "status": task.status,
        "client_id": task.client_id,
    }


@campaign_router.post("/tasks/{task_id}/send")
def manual_send_task(task_id: str, db: Session = Depends(get_db)):
    """手动触发发送单条任务（通过短信 ML307A 发送）。"""
    config = get_config()
    # 开发模式绕过权限限制
    if not config.server.dev_mode and config.current_tier != "business":
        raise HTTPException(403, "自动发送为至尊版功能，请升级套餐")

    from channels.drivers.ml307a import ML307ADriver
    from channels.base import SendResult

    # 检查任务状态
    task = db.query(CampaignTask).filter(CampaignTask.id == task_id).first()
    if not task:
        raise HTTPException(404, "任务不存在")
    if task.status not in ("queued", "approved", "failed"):
        raise HTTPException(400, f"任务状态不允许发送: {task.status}")

    # 获取客户信息
    client = db.query(Client).filter(Client.client_id == task.client_id).first()
    if not client:
        raise HTTPException(404, "客户不存在")

    # 检查 ML307A 是否可用
    raw_ch = config.raw.get("channels", {})
    ml307a_config = raw_ch.get("ml307a", {})

    if not ml307a_config.get("enabled", False):
        return {"success": False, "channel": "ml307a", "error": "ML307A 短信功能未启用"}

    driver = ML307ADriver(ml307a_config)

    if not driver.is_available():
        return {"success": False, "channel": "ml307a", "error": "ML307A 设备不可用，请检查连接"}

    # 直接发送短信
    try:
        result = driver.send(
            recipient=client.phone or "",
            content=task.generated_content or "",
            client_name=client.name,
        )
    except Exception as e:
        result = SendResult(success=False, channel="ml307a", error=str(e))

    # 更新任务状态
    task.send_channel = "ml307a"
    if result.success:
        task.status = "sent"
        task.sent_at = datetime.now()
        task.error_message = None
    else:
        task.status = "failed"
        task.error_message = result.error
    db.commit()

    return {
        "success": result.success,
        "channel": "ml307a",
        "error": result.error,
    }


@campaign_router.get("/channels")
def list_channels():
    """获取当前可用的渠道列表。"""
    config = get_config()
    from channels.router import ChannelRouter
    router = ChannelRouter(config)
    return {
        "tier": config.current_tier,
        "sms_enabled": config.server.dev_mode or config.current_tier == "business",
        "dev_mode": config.server.dev_mode,
        "available_channels": router.get_available_channels(),
    }


# ── 辅助 ─────────────────────────────────────────────────────────

def _task_to_out(db: Session, task: CampaignTask) -> TaskOut:
    from db_models import Client
    pb = task.playbook
    client = db.query(Client).filter(Client.client_id == task.client_id).first()
    return TaskOut(
        id=task.id,
        playbook_id=task.playbook_id,
        playbook_name=pb.name if pb else "",
        client_id=task.client_id,
        client_name=client.name if client else "",
        generated_content=task.generated_content or "",
        status=task.status,
        approval_mode=task.approval_mode or "",
        send_channel=task.send_channel or "auto",
        scheduled_at=task.scheduled_at.isoformat() if task.scheduled_at else None,
        sent_at=task.sent_at.isoformat() if task.sent_at else None,
        created_at=task.created_at.isoformat() if task.created_at else None,
        error_message=task.error_message,
    )
