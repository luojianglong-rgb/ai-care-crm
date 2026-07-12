"""
个性化服务方案生成服务
基于分析结果 + 店内服务项目 + 季节信息，调用 LLM 生成方案。
"""
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from config import AppConfig
from ai.llm_client import LLMClient
from ai.prompts import get_plan_prompt
from db_models import ProfessionalAnalysis, CarePlan, ServiceItem, Client
from services.quota_service import QuotaService

logger = logging.getLogger(__name__)

# 简易季节判断
def _get_current_season() -> str:
    month = datetime.now().month
    if month in (3, 4, 5):
        return "春季"
    elif month in (6, 7, 8):
        return "夏季"
    elif month in (9, 10, 11):
        return "秋季"
    else:
        return "冬季"


class CarePlanGenerator:

    def __init__(self, config: AppConfig, llm: LLMClient):
        self.config = config
        self.llm = llm
        self.domain = config.analysis_domain
        self.quota = QuotaService(config)

    def generate(self, db: Session, client_id: str, analysis_id: str) -> dict:
        """
        基于已有的专业分析结果生成服务方案。
        返回 {"success": bool, "data": dict or None, "error": str}
        """
        # 1. 额度检查
        allowed, msg = self.quota.check_quota(db, "plan")
        if not allowed:
            return {"success": False, "data": None, "error": msg}

        # 2. 获取分析记录
        analysis = db.query(ProfessionalAnalysis).filter(
            ProfessionalAnalysis.id == analysis_id
        ).first()
        if not analysis:
            return {"success": False, "data": None, "error": "分析记录不存在"}
        if analysis.client_id != client_id:
            return {"success": False, "data": None, "error": "分析记录与客户不匹配"}

        # 3. 获取店内可用服务项目
        services = db.query(ServiceItem).filter(ServiceItem.is_active == 1).all()
        service_names = [s.name for s in services]

        # 4. 组装 user message
        season = _get_current_season()
        recs = analysis.ai_recommendations or {}

        user_msg = f"""当前季节：{season}
客户分析结果：{analysis.primary_type}（{analysis.secondary_type or '无兼夹'}）
置信度：{analysis.confidence_score}
分析摘要：{analysis.ai_analysis_summary}
关键特征：{', '.join(recs.get('key_symptoms', []))}
禁忌事项：{', '.join(recs.get('contraindications', []))}
店内可选项目：{', '.join(service_names) if service_names else '暂无配置'}"""

        # 5. 调用 LLM
        system_prompt = get_plan_prompt(self.domain)
        if not system_prompt:
            return {"success": False, "data": None, "error": f"未找到领域 {self.domain} 的方案 Prompt"}

        parsed, resp = self.llm.chat_json(system_prompt, user_msg, temperature=0.4)

        # 6. 记录用量
        self.quota.record_usage(
            db, usage_type="plan", client_id=client_id,
            model_provider=self.config.llm.provider,
            model_name=resp.model,
            tokens_used=resp.tokens_used,
            success=resp.success,
            error_message=resp.error if not resp.success else None,
        )

        if not resp.success or parsed is None:
            return {"success": False, "data": None, "error": resp.error or "AI 返回格式异常"}

        # 7. 将之前的方案标记为 superseded
        db.query(CarePlan).filter(
            CarePlan.client_id == client_id,
            CarePlan.status == "active",
        ).update({"status": "superseded"})

        # 8. 存入数据库
        plan = CarePlan(
            client_id=client_id,
            analysis_id=analysis_id,
            in_store_services=parsed.get("in_store_services", []),
            home_care_advice=parsed.get("home_care_advice", []),
            seasonal_notes=parsed.get("seasonal_notes", ""),
            plan_summary=parsed.get("plan_summary", ""),
            valid_until=datetime.now() + timedelta(days=30),
            status="active",
        )
        db.add(plan)
        db.commit()
        db.refresh(plan)

        return {
            "success": True,
            "data": {
                "id": plan.id,
                "client_id": plan.client_id,
                "analysis_id": plan.analysis_id,
                "in_store_services": plan.in_store_services,
                "home_care_advice": plan.home_care_advice,
                "seasonal_notes": plan.seasonal_notes,
                "plan_summary": plan.plan_summary,
                "valid_until": plan.valid_until.isoformat() if plan.valid_until else None,
                "status": plan.status,
                "created_at": plan.created_at.isoformat() if plan.created_at else None,
            },
            "error": "",
        }
