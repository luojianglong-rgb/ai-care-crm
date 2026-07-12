"""
AI 专业分析与方案 API 端点
/api/v1/ai/*
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
import uuid

from database import get_db
from config import get_config
from ai.llm_client import get_llm_client
from ai.professional_analyzer import ProfessionalAnalyzer
from ai.care_plan_generator import CarePlanGenerator
from db_models import ProfessionalAnalysis, CarePlan, Client, CampaignTask

router = APIRouter()


# ── 请求/响应模型 ────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    client_id: str
    symptoms: str
    observations: str = ""
    assessed_by: str = "ai_auto"
    include_service_history: bool = True  # 是否包含历史服务记录


class AnalysisResult(BaseModel):
    id: str
    client_id: str
    domain: str
    primary_type: str
    secondary_type: Optional[str] = None
    confidence_score: float
    ai_analysis_summary: str
    ai_recommendations: dict
    assessed_at: Optional[str] = None


class AnalyzeResponse(BaseModel):
    success: bool
    data: Optional[AnalysisResult] = None
    error: str = ""


class GeneratePlanRequest(BaseModel):
    client_id: str
    analysis_id: str


class PlanServiceItem(BaseModel):
    name: str
    frequency: str = ""
    reason: str = ""


class PlanAdviceItem(BaseModel):
    category: str = ""
    advice: str = ""


class PlanResult(BaseModel):
    id: str
    client_id: str
    analysis_id: str
    in_store_services: list
    home_care_advice: list
    seasonal_notes: str = ""
    plan_summary: str = ""
    valid_until: Optional[str] = None
    status: str
    created_at: Optional[str] = None


class PlanResponse(BaseModel):
    success: bool
    data: Optional[PlanResult] = None
    error: str = ""


class AnalysisListItem(BaseModel):
    id: str
    domain: str
    primary_type: str
    secondary_type: Optional[str] = None
    confidence_score: float
    ai_analysis_summary: str
    assessed_at: Optional[str] = None


class PlanListItem(BaseModel):
    id: str
    analysis_id: str
    plan_summary: str
    status: str
    valid_until: Optional[str] = None
    created_at: Optional[str] = None


class SendPlanRequest(BaseModel):
    """发送调理方案请求"""
    plan_id: str
    channel: str = "auto"  # auto / ml307a
    recipient_phone: str  # 接收者手机号
    message_content: Optional[str] = None  # 可选：自定义消息内容（不填则使用方案摘要）


class SendPlanResponse(BaseModel):
    """发送调理方案响应"""
    success: bool
    task_id: Optional[str] = None
    message: str = ""
    error: str = ""


# ── API 端点 ──────────────────────────────────────────────────────

@router.post("/analyze", response_model=AnalyzeResponse)
def run_analysis(req: AnalyzeRequest, db: Session = Depends(get_db)):
    """提交客户状况，AI 返回专业分析结果。"""
    config = get_config()
    llm = get_llm_client()

    if not llm.is_available:
        return AnalyzeResponse(success=False, error="AI 功能未就绪：请在 config.yaml 中配置 LLM API Key")

    analyzer = ProfessionalAnalyzer(config, llm)
    result = analyzer.analyze(
        db=db,
        client_id=req.client_id,
        symptoms=req.symptoms,
        observations=req.observations,
        assessed_by=req.assessed_by,
        include_service_history=req.include_service_history,
    )

    if result["success"]:
        return AnalyzeResponse(success=True, data=AnalysisResult(**result["data"]))
    else:
        return AnalyzeResponse(success=False, error=result["error"])


@router.get("/analyses/{client_id}", response_model=list[AnalysisListItem])
def get_client_analyses(client_id: str, db: Session = Depends(get_db)):
    """获取客户历史分析列表（按时间倒序）。"""
    records = db.query(ProfessionalAnalysis).filter(
        ProfessionalAnalysis.client_id == client_id
    ).order_by(ProfessionalAnalysis.assessed_at.desc()).all()

    return [
        AnalysisListItem(
            id=r.id,
            domain=r.domain,
            primary_type=r.primary_type,
            secondary_type=r.secondary_type,
            confidence_score=r.confidence_score,
            ai_analysis_summary=r.ai_analysis_summary or "",
            assessed_at=r.assessed_at.isoformat() if r.assessed_at else None,
        )
        for r in records
    ]


@router.get("/analyses/{client_id}/latest", response_model=Optional[AnalysisResult])
def get_latest_analysis(client_id: str, db: Session = Depends(get_db)):
    """获取客户最新的分析结果。"""
    record = db.query(ProfessionalAnalysis).filter(
        ProfessionalAnalysis.client_id == client_id
    ).order_by(ProfessionalAnalysis.assessed_at.desc()).first()

    if not record:
        return None

    return AnalysisResult(
        id=record.id,
        client_id=record.client_id,
        domain=record.domain,
        primary_type=record.primary_type,
        secondary_type=record.secondary_type,
        confidence_score=record.confidence_score,
        ai_analysis_summary=record.ai_analysis_summary or "",
        ai_recommendations=record.ai_recommendations or {},
        assessed_at=record.assessed_at.isoformat() if record.assessed_at else None,
    )


@router.post("/plan/generate", response_model=PlanResponse)
def generate_plan(req: GeneratePlanRequest, db: Session = Depends(get_db)):
    """基于分析结果生成个性化服务方案。"""
    config = get_config()
    llm = get_llm_client()

    if not llm.is_available:
        return PlanResponse(success=False, error="AI 功能未就绪：请在 config.yaml 中配置 LLM API Key")

    generator = CarePlanGenerator(config, llm)
    result = generator.generate(
        db=db,
        client_id=req.client_id,
        analysis_id=req.analysis_id,
    )

    if result["success"]:
        return PlanResponse(success=True, data=PlanResult(**result["data"]))
    else:
        return PlanResponse(success=False, error=result["error"])


@router.get("/plans/{client_id}", response_model=list[PlanListItem])
def get_client_plans(client_id: str, db: Session = Depends(get_db)):
    """获取客户的方案列表（按时间倒序）。"""
    plans = db.query(CarePlan).filter(
        CarePlan.client_id == client_id
    ).order_by(CarePlan.created_at.desc()).all()

    return [
        PlanListItem(
            id=p.id,
            analysis_id=p.analysis_id,
            plan_summary=p.plan_summary or "",
            status=p.status,
            valid_until=p.valid_until.isoformat() if p.valid_until else None,
            created_at=p.created_at.isoformat() if p.created_at else None,
        )
        for p in plans
    ]


@router.put("/plans/{plan_id}/status")
def update_plan_status(plan_id: str, status: str, db: Session = Depends(get_db)):
    """更新方案状态（active/expired/superseded）。"""
    plan = db.query(CarePlan).filter(CarePlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="方案不存在")
    if status not in ("active", "expired", "superseded"):
        raise HTTPException(status_code=400, detail="无效的状态值")
    plan.status = status
    db.commit()
    return {"success": True, "plan_id": plan_id, "status": status}


@router.post("/plans/{plan_id}/send", response_model=SendPlanResponse)
def send_care_plan(plan_id: str, req: SendPlanRequest, db: Session = Depends(get_db)):
    """
    一键发送调理方案给客户（高级功能）。
    创建营销任务队列，由发送执行器通过渠道驱动发送（微信 RPA 或短信 API）。
    """
    # 获取方案
    plan = db.query(CarePlan).filter(CarePlan.id == plan_id).first()
    if not plan:
        return SendPlanResponse(success=False, error="方案不存在")

    # 获取客户信息
    client = db.query(Client).filter(Client.client_id == plan.client_id).first()
    if not client:
        return SendPlanResponse(success=False, error="客户不存在")

    # 确定消息内容
    message_content = req.message_content or plan.plan_summary
    if not message_content:
        return SendPlanResponse(success=False, error="方案内容为空，无法发送")

    # 构建完整的消息（包含问候语和方案内容）
    full_message = f"{client.name}您好，这是为您定制的调理方案：\n\n{message_content}\n\n如有任何疑问，请随时联系我们。"

    # 创建营销任务
    task_id = str(uuid.uuid4())
    task = CampaignTask(
        id=task_id,
        playbook_id="ai_plan_manual",  # 标记为 AI 方案手动发送
        client_id=plan.client_id,
        generated_content=full_message,
        status="approved",  # 手动发送的任务直接审批通过
        approval_mode="manual",
        is_sampled=0,
        scheduled_at=datetime.now(),  # 立即发送
        send_channel=req.channel,
    )
    db.add(task)
    db.commit()

    logger.info(f"[AI 方案发送] 已创建任务 {task_id}，客户={client.name}, 渠道={req.channel}")

    return SendPlanResponse(
        success=True,
        task_id=task_id,
        message=f"调理方案已加入发送队列，将通过{req.channel}发送给客户"
    )
