"""
多领域专业分析服务
根据 config.yaml 中的 business_type，自动加载对应领域的 Prompt，
调用 LLM 返回专业分析结果，存入 professional_analyses 表。
"""
import logging
from datetime import datetime
from sqlalchemy.orm import Session

from config import AppConfig
from ai.llm_client import LLMClient
from ai.pii_masker import PIIMasker
from ai.prompts import get_analysis_prompt
from db_models import ProfessionalAnalysis, Client, HealthRecord
from services.quota_service import QuotaService

logger = logging.getLogger(__name__)


class ProfessionalAnalyzer:

    def __init__(self, config: AppConfig, llm: LLMClient):
        self.config = config
        self.llm = llm
        self.domain = config.analysis_domain
        self.masker = PIIMasker()
        self.quota = QuotaService(config)

    def analyze(self, db: Session, client_id: str,
                symptoms: str, observations: str = "",
                assessed_by: str = "ai_auto",
                include_service_history: bool = True) -> dict:
        """
        执行专业分析。
        返回 {"success": bool, "data": ProfessionalAnalysis dict or None, "error": str}
        """
        # 1. 额度检查
        allowed, msg = self.quota.check_quota(db, "analysis")
        if not allowed:
            return {"success": False, "data": None, "error": msg}

        # 2. 获取客户信息（用于 PII 脱敏）
        client = db.query(Client).filter(Client.client_id == client_id).first()
        if not client:
            return {"success": False, "data": None, "error": "客户不存在"}

        # 2.5 获取历史服务记录（如启用）
        service_history_text = ""
        if include_service_history:
            service_records = db.query(HealthRecord).filter(
                HealthRecord.client_id == client_id
            ).order_by(HealthRecord.date.desc()).limit(5).all()

            if service_records:
                service_history_text = "\n\n【历史服务记录】\n"
                for i, rec in enumerate(service_records, 1):
                    date_str = rec.date.strftime("%Y-%m-%d") if rec.date else "未知日期"
                    symptoms_str = ", ".join(rec.symptoms) if isinstance(rec.symptoms, list) else str(rec.symptoms)
                    service_history_text += f"{i}. {date_str} | 症状：{symptoms_str} | 服务：{rec.treatment_provided or '无'}\n"
                    if rec.description:
                        service_history_text += f"   描述：{rec.description}\n"
                    if rec.notes:
                        service_history_text += f"   备注：{rec.notes}\n"

        # 3. PII 脱敏
        known_names = [client.name] if client.name else []
        raw_text = f"客户自述：{symptoms}"
        if observations:
            raw_text += f"\n技师观察：{observations}"
        if service_history_text:
            raw_text += service_history_text
        masked_text, pii_mapping = self.masker.mask(raw_text, known_names)

        # 4. 加载业态 Prompt + 调用 LLM
        system_prompt = get_analysis_prompt(self.domain)
        if not system_prompt:
            return {"success": False, "data": None, "error": f"未找到领域 {self.domain} 的分析 Prompt"}

        # 构建用户消息，明确告知 LLM 包含历史服务记录
        user_message = masked_text
        if service_history_text:
            user_message += "\n\n请结合历史服务记录进行分析，重点关注症状的变化趋势和服务效果。"

        parsed, resp = self.llm.chat_json(system_prompt, user_message)

        # 5. 记录用量
        self.quota.record_usage(
            db, usage_type="analysis", client_id=client_id,
            model_provider=self.config.llm.provider,
            model_name=resp.model,
            tokens_used=resp.tokens_used,
            success=resp.success,
            error_message=resp.error if not resp.success else None,
        )

        if not resp.success or parsed is None:
            return {"success": False, "data": None, "error": resp.error or "AI 返回格式异常"}

        # 6. 回填 PII（analysis 文字中可能有占位符）
        analysis_text = parsed.get("analysis", "")
        analysis_text = self.masker.unmask(analysis_text, pii_mapping)
        parsed["analysis"] = analysis_text

        # 7. 存入数据库
        record = ProfessionalAnalysis(
            client_id=client_id,
            domain=self.domain,
            primary_type=parsed.get("primary_type", ""),
            secondary_type=parsed.get("secondary_type"),
            symptoms_snapshot={"symptoms": symptoms, "observations": observations},
            observation_notes=observations or None,
            ai_analysis_summary=analysis_text,
            ai_recommendations={
                "key_symptoms": parsed.get("key_symptoms", []),
                "risk_factors": parsed.get("risk_factors", []),
                "contraindications": parsed.get("contraindications", []),
            },
            confidence_score=parsed.get("confidence", 0.0),
            assessed_by=assessed_by,
        )
        db.add(record)

        # 更新客户表冗余字段
        client.primary_analysis_type = parsed.get("primary_type", "")
        db.commit()
        db.refresh(record)

        return {
            "success": True,
            "data": {
                "id": record.id,
                "client_id": record.client_id,
                "domain": record.domain,
                "primary_type": record.primary_type,
                "secondary_type": record.secondary_type,
                "confidence_score": record.confidence_score,
                "ai_analysis_summary": record.ai_analysis_summary,
                "ai_recommendations": record.ai_recommendations,
                "assessed_at": record.assessed_at.isoformat() if record.assessed_at else None,
            },
            "error": "",
        }
