"""
店长驾驶舱 API
/api/v1/dashboard/*
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta

from database import get_db
from config import get_config
from services.quota_service import QuotaService
from db_models import (
    CampaignTask, ClientLifecycle, Client, Playbook,
    ClientReply, ProfessionalAnalysis,
)

router = APIRouter()


class TodayOutreach(BaseModel):
    sent: int = 0
    queued: int = 0
    pending_approval: int = 0
    failed: int = 0
    total: int = 0


class ClientDynamics(BaseModel):
    total_clients: int = 0
    new_this_week: int = 0
    silent_warning: int = 0
    churn_risk: int = 0
    returned_this_week: int = 0


class QuotaOverview(BaseModel):
    tier: str = "basic"
    analysis_used: int = 0
    analysis_limit: int = 10
    plan_used: int = 0
    plan_limit: int = 10
    content_used: int = 0
    content_limit: int = 20


class PlaybookReport(BaseModel):
    name: str
    is_active: bool
    total_tasks: int = 0
    sent_tasks: int = 0
    pending_tasks: int = 0


class RecentReply(BaseModel):
    client_name: str = ""
    intent: str = ""
    raw_content: str = ""
    created_at: str = ""


class DashboardResponse(BaseModel):
    today_outreach: TodayOutreach
    client_dynamics: ClientDynamics
    quota: QuotaOverview
    playbook_reports: list[PlaybookReport]
    recent_replies: list[RecentReply]


@router.get("/today", response_model=DashboardResponse)
def get_dashboard(db: Session = Depends(get_db)):
    """店长驾驶舱：一个接口返回全局概览。"""
    config = get_config()
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = datetime.now() - timedelta(days=7)

    # ── 今日触达 ──
    today_tasks = db.query(CampaignTask).filter(CampaignTask.created_at >= today_start).all()
    outreach = TodayOutreach(
        sent=sum(1 for t in today_tasks if t.status == "sent"),
        queued=sum(1 for t in today_tasks if t.status == "queued"),
        pending_approval=sum(1 for t in today_tasks if t.status == "pending_approval"),
        failed=sum(1 for t in today_tasks if t.status == "failed"),
        total=len(today_tasks),
    )

    # ── 客户动态 ──
    total_clients = db.query(func.count(Client.client_id)).scalar() or 0
    new_this_week = db.query(func.count(Client.client_id)).filter(
        Client.created_at >= week_ago).scalar() or 0
    lc_stats = {}
    for status, cnt in db.query(
        ClientLifecycle.current_status, func.count(ClientLifecycle.id)
    ).group_by(ClientLifecycle.current_status).all():
        lc_stats[status] = cnt
    returned = db.query(func.count(ClientLifecycle.id)).filter(
        ClientLifecycle.current_status == "active",
        ClientLifecycle.status_changed_at >= week_ago,
    ).scalar() or 0

    dynamics = ClientDynamics(
        total_clients=total_clients,
        new_this_week=new_this_week,
        silent_warning=lc_stats.get("silent", 0),
        churn_risk=lc_stats.get("churn_risk", 0),
        returned_this_week=returned,
    )

    # ── AI 额度 ──
    qs = QuotaService(config)
    usage = qs.get_usage_summary(db)
    quota = QuotaOverview(
        tier=config.current_tier,
        analysis_used=usage["analysis"]["used"],
        analysis_limit=usage["analysis"]["limit"],
        plan_used=usage["plan"]["used"],
        plan_limit=usage["plan"]["limit"],
        content_used=usage["content"]["used"],
        content_limit=usage["content"]["limit"],
    )

    # ── 剧本报表 ──
    playbooks = db.query(Playbook).order_by(Playbook.priority).all()
    pb_reports = []
    for pb in playbooks:
        total = db.query(func.count(CampaignTask.id)).filter(
            CampaignTask.playbook_id == pb.id).scalar() or 0
        sent = db.query(func.count(CampaignTask.id)).filter(
            CampaignTask.playbook_id == pb.id,
            CampaignTask.status == "sent").scalar() or 0
        pending = db.query(func.count(CampaignTask.id)).filter(
            CampaignTask.playbook_id == pb.id,
            CampaignTask.status == "pending_approval").scalar() or 0
        pb_reports.append(PlaybookReport(
            name=pb.name, is_active=bool(pb.is_active),
            total_tasks=total, sent_tasks=sent, pending_tasks=pending,
        ))

    # ── 最近回复 ──
    recent = db.query(ClientReply).order_by(
        ClientReply.created_at.desc()).limit(5).all()
    recent_replies = []
    for r in recent:
        client = db.query(Client).filter(Client.client_id == r.client_id).first()
        recent_replies.append(RecentReply(
            client_name=client.name if client else "",
            intent=r.ai_parsed_intent or "",
            raw_content=(r.raw_content or "")[:100],
            created_at=r.created_at.isoformat() if r.created_at else "",
        ))

    return DashboardResponse(
        today_outreach=outreach,
        client_dynamics=dynamics,
        quota=quota,
        playbook_reports=pb_reports,
        recent_replies=recent_replies,
    )


@router.get("/client-dynamics", response_model=ClientDynamics)
def get_client_dynamics(db: Session = Depends(get_db)):
    """本周客户动态（独立端点，轻量查询）。"""
    week_ago = datetime.now() - timedelta(days=7)
    total = db.query(func.count(Client.client_id)).scalar() or 0
    new_week = db.query(func.count(Client.client_id)).filter(
        Client.created_at >= week_ago).scalar() or 0
    silent = db.query(func.count(ClientLifecycle.id)).filter(
        ClientLifecycle.current_status == "silent").scalar() or 0
    churn = db.query(func.count(ClientLifecycle.id)).filter(
        ClientLifecycle.current_status == "churn_risk").scalar() or 0
    returned = db.query(func.count(ClientLifecycle.id)).filter(
        ClientLifecycle.current_status == "active",
        ClientLifecycle.status_changed_at >= week_ago).scalar() or 0
    return ClientDynamics(
        total_clients=total, new_this_week=new_week,
        silent_warning=silent, churn_risk=churn,
        returned_this_week=returned,
    )
