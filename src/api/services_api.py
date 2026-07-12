"""
服务项目推荐 API 端点
/api/v1/service-recs/*
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
from db_models import ServiceItem
from services.service_recommender import ServiceRecommender, init_service_terms_mapping, DEFAULT_SERVICE_TERMS_MAPPING

router = APIRouter()


@router.get("/recommendations")
def get_service_recommendations(
    client_id: Optional[str] = None,
    analysis_type: Optional[str] = None,
    season: Optional[str] = None,
    term: Optional[str] = None,
    limit: int = Query(default=3, le=10),
    db: Session = Depends(get_db)
):
    """
    根据条件获取服务项目推荐

    参数:
    - client_id: 客户 ID（可选，用于获取体质）
    - analysis_type: 体质类型（如"阳虚质"）
    - season: 季节（春/夏/秋/冬）
    - term: 节气/养生节点（如"三伏"、"立春"）
    - limit: 返回数量限制
    """
    from playbook.solar_terms import SolarTermCalendar
    from datetime import date

    # 如果没有传入，获取当前节气信息
    if not season or not term:
        tcm_context = SolarTermCalendar.get_current_tcm_context()
        if not season:
            season = tcm_context["season"]
        if not term:
            term = tcm_context["current_term"]

    recommendations = ServiceRecommender.get_recommendations(
        db=db,
        client_id=client_id,
        analysis_type=analysis_type,
        current_season=season,
        current_term=term,
        limit=limit,
    )

    return [
        {
            "item_id": rec["service"].item_id,
            "name": rec["service"].name,
            "description": rec["service"].description or "",
            "score": rec["score"],
            "match_reasons": rec["match_reasons"],
            "wellness_effects": rec["service"].wellness_effects or [],
            "recommended_reason": rec["service"].recommended_reason or "",
        }
        for rec in recommendations
    ]


@router.get("/terms-mapping/init")
def initialize_terms_mapping(db: Session = Depends(get_db)):
    """
    初始化服务项目的节气/体质关联配置
    将默认配置应用到数据库中的服务项目
    """
    count = init_service_terms_mapping(db)
    return {
        "success": True,
        "updated_count": count,
        "default_mappings": list(DEFAULT_SERVICE_TERMS_MAPPING.keys()),
    }


@router.get("/terms-mapping/defaults")
def get_default_terms_mapping():
    """
    获取默认的服务项目节气/体质关联配置
    """
    return {
        name: {
            "suitable_for_body_types": config["suitable_for_body_types"],
            "suitable_for_seasons": config["suitable_for_seasons"],
            "suitable_for_terms": config["suitable_for_terms"],
            "wellness_effects": config["wellness_effects"],
            "recommended_reason": config["recommended_reason"],
        }
        for name, config in DEFAULT_SERVICE_TERMS_MAPPING.items()
    }


@router.put("/{item_id}/terms-mapping")
def update_service_terms_mapping(
    item_id: str,
    suitable_for_body_types: Optional[str] = None,
    suitable_for_seasons: Optional[str] = None,
    suitable_for_terms: Optional[str] = None,
    wellness_effects: Optional[str] = None,
    recommended_reason: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    更新单个服务项目的节气/体质关联配置

    参数接受 JSON 数组的字符串形式，如：'["阳虚质", "气虚质"]'
    """
    import json

    service = db.query(ServiceItem).filter(ServiceItem.item_id == item_id).first()
    if not service:
        return {"success": False, "error": "服务项目不存在"}

    if suitable_for_body_types is not None:
        service.suitable_for_body_types = json.loads(suitable_for_body_types)
    if suitable_for_seasons is not None:
        service.suitable_for_seasons = json.loads(suitable_for_seasons)
    if suitable_for_terms is not None:
        service.suitable_for_terms = json.loads(suitable_for_terms)
    if wellness_effects is not None:
        service.wellness_effects = json.loads(wellness_effects)
    if recommended_reason is not None:
        service.recommended_reason = recommended_reason

    db.commit()
    db.refresh(service)

    return {
        "success": True,
        "service": {
            "item_id": service.item_id,
            "name": service.name,
            "suitable_for_body_types": service.suitable_for_body_types,
            "suitable_for_seasons": service.suitable_for_seasons,
            "suitable_for_terms": service.suitable_for_terms,
            "wellness_effects": service.wellness_effects,
            "recommended_reason": service.recommended_reason,
        }
    }


@router.get("/{item_id}/terms-mapping")
def get_service_terms_mapping(item_id: str, db: Session = Depends(get_db)):
    """
    获取单个服务项目的节气/体质关联配置
    """
    service = db.query(ServiceItem).filter(ServiceItem.item_id == item_id).first()
    if not service:
        return {"success": False, "error": "服务项目不存在"}

    return {
        "item_id": service.item_id,
        "name": service.name,
        "suitable_for_body_types": service.suitable_for_body_types or [],
        "suitable_for_seasons": service.suitable_for_seasons or [],
        "suitable_for_terms": service.suitable_for_terms or [],
        "wellness_effects": service.wellness_effects or [],
        "recommended_reason": service.recommended_reason or "",
    }
