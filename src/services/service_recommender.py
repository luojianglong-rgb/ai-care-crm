"""
服务项目推荐引擎
根据客户的体质、当前节气/养生节点，智能推荐匹配的店内服务项目
"""
import logging
from sqlalchemy.orm import Session
from sqlalchemy import or_

from db_models import ServiceItem, Client, ProfessionalAnalysis

logger = logging.getLogger(__name__)


class ServiceRecommender:
    """服务项目智能推荐引擎"""

    @staticmethod
    def get_recommendations(
        db: Session,
        client_id: str = None,
        analysis_type: str = None,
        current_season: str = None,
        current_term: str = None,
        tcm_periods: list = None,
        wellness_focus: str = None,
        limit: int = 3
    ) -> list[dict]:
        """
        根据多维度条件推荐服务项目

        Args:
            db: 数据库会话
            client_id: 客户 ID（可选，用于获取客户体质）
            analysis_type: 客户体质类型（如"阳虚质"）
            current_season: 当前季节（春/夏/秋/冬）
            current_term: 当前节气（如"立春"）
            tcm_periods: 当前中医养生节点（如 ["三九", "一九"]）
            wellness_focus: 养生重点（如"温阳散寒"）
            limit: 返回数量限制

        Returns:
            推荐服务项目列表，按匹配度排序
        """
        # 获取活跃的服务项目
        query = db.query(ServiceItem).filter(ServiceItem.is_active == 1)
        services = query.all()

        if not services:
            return []

        # 如果没有指定条件，尝试从客户获取
        if not analysis_type and client_id:
            client = db.query(Client).filter(Client.client_id == client_id).first()
            if client:
                analysis_type = client.primary_analysis_type

        # 计算每个服务的匹配分数
        scored_services = []
        for svc in services:
            score = 0
            match_reasons = []

            # 1. 体质匹配（权重：3 分）
            if analysis_type:
                suitable_types = svc.suitable_for_body_types or []
                if analysis_type in suitable_types:
                    score += 3
                    match_reasons.append(f"适合{analysis_type}")

            # 2. 季节匹配（权重：2 分）
            if current_season:
                suitable_seasons = svc.suitable_for_seasons or []
                if current_season in suitable_seasons:
                    score += 2
                    match_reasons.append(f"{current_season}季适宜")

            # 3. 节气/养生节点匹配（权重：4 分，最高优先级）
            if current_term or tcm_periods:
                suitable_terms = svc.suitable_for_terms or []
                # 检查节气
                if current_term and current_term in suitable_terms:
                    score += 4
                    match_reasons.append(f"{current_term}时节推荐")
                # 检查养生节点
                if tcm_periods:
                    for period in tcm_periods:
                        if period in suitable_terms:
                            score += 4
                            match_reasons.append(f"{period}适宜")
                            break

            # 4. 养生功效匹配（权重：3 分）
            if wellness_focus:
                wellness_effects = svc.wellness_effects or []
                # 提取养生重点的关键词
                keywords = ServiceRecommender._extract_keywords(wellness_focus)
                for keyword in keywords:
                    if any(keyword in effect for effect in wellness_effects):
                        score += 3
                        match_reasons.append(f"功效匹配：{keyword}")
                        break

            if score > 0:
                scored_services.append({
                    "service": svc,
                    "score": score,
                    "match_reasons": match_reasons,
                })

        # 按分数排序，返回 Top N
        scored_services.sort(key=lambda x: x["score"], reverse=True)
        return scored_services[:limit]

    @staticmethod
    def _extract_keywords(wellness_focus: str) -> list[str]:
        """从养生重点描述中提取关键词"""
        # 常见养生功效关键词
        keyword_map = {
            "温阳": ["温阳", "补阳", "助阳"],
            "散寒": ["散寒", "驱寒", "暖宫"],
            "祛湿": ["祛湿", "除湿", "化湿"],
            "排毒": ["排毒", "解毒"],
            "健脾": ["健脾", "养胃", "调理脾胃"],
            "润肺": ["润肺", "滋阴", "生津"],
            "养肝": ["养肝", "疏肝", "理气"],
            "补肾": ["补肾", "固本", "益气"],
            "清热": ["清热", "降火", "解毒"],
            "活血": ["活血", "化瘀", "通络"],
        }

        keywords = []
        for key, variants in keyword_map.items():
            if any(v in wellness_focus for v in variants):
                keywords.append(key)

        return keywords if keywords else [wellness_focus[:4]]

    @staticmethod
    def get_service_with_reason(service: ServiceItem, match_reasons: list[str]) -> dict:
        """生成服务项目推荐话术"""
        return {
            "name": service.name,
            "description": service.description or "",
            "match_reasons": match_reasons,
            "wellness_effects": service.wellness_effects or [],
            "recommended_reason": service.recommended_reason or "",
        }


# 默认服务 - 节气养生关联配置示例
DEFAULT_SERVICE_TERMS_MAPPING = {
    "中医艾灸": {
        "suitable_for_body_types": ["阳虚质", "气虚质", "血虚质"],
        "suitable_for_seasons": ["冬", "春"],
        "suitable_for_terms": ["三九", "一九", "二九", "三九", "立春", "冬至"],
        "wellness_effects": ["温阳散寒", "补气养血", "驱寒暖宫"],
        "recommended_reason": "三九/立春时节，艾灸可温补阳气，驱散寒邪",
    },
    "三伏贴": {
        "suitable_for_body_types": ["阳虚质", "气虚质", "痰湿质"],
        "suitable_for_seasons": ["夏"],
        "suitable_for_terms": ["三伏", "初伏", "中伏", "末伏", "夏至"],
        "wellness_effects": ["冬病夏治", "温阳驱寒", "扶正固本"],
        "recommended_reason": "三伏天穴位贴敷，冬病夏治最佳时机",
    },
    "拔罐祛湿": {
        "suitable_for_body_types": ["痰湿质", "湿热质"],
        "suitable_for_seasons": ["夏", "秋"],
        "suitable_for_terms": ["长夏", "处暑", "秋老虎"],
        "wellness_effects": ["祛湿排毒", "疏通经络", "清热解毒"],
        "recommended_reason": "长夏湿气重，拔罐帮助排出体内湿毒",
    },
    "经络按摩": {
        "suitable_for_body_types": ["气郁质", "血瘀质"],
        "suitable_for_seasons": ["春", "秋"],
        "suitable_for_terms": ["春分", "秋分", "惊蛰"],
        "wellness_effects": ["疏通经络", "理气活血", "缓解疲劳"],
        "recommended_reason": "春秋分时节，经络按摩调和阴阳",
    },
    "中药足浴": {
        "suitable_for_body_types": ["阳虚质", "血虚质", "气虚质"],
        "suitable_for_seasons": ["冬", "秋"],
        "suitable_for_terms": ["霜降", "立冬", "大雪", "冬至"],
        "wellness_effects": ["温经通络", "养血安神", "驱寒助眠"],
        "recommended_reason": "秋冬泡脚，温经养血，安神助眠",
    },
    "刮痧排毒": {
        "suitable_for_body_types": ["湿热质", "痰湿质"],
        "suitable_for_seasons": ["夏"],
        "suitable_for_terms": ["大暑", "小暑", "长夏"],
        "wellness_effects": ["清热解毒", "祛湿排毒", "疏通腠理"],
        "recommended_reason": "暑热湿重，刮痧帮助清热解毒",
    },
    "肩颈调理": {
        "suitable_for_body_types": ["气郁质", "血瘀质", "气虚质"],
        "suitable_for_seasons": ["春", "秋", "冬"],
        "suitable_for_terms": ["立春", "秋分", "霜降"],
        "wellness_effects": ["疏通经络", "缓解疲劳", "理气活血"],
        "recommended_reason": "节气交替时肩颈易紧张，及时调理",
    },
    "背部护理": {
        "suitable_for_body_types": ["痰湿质", "湿热质", "气虚质"],
        "suitable_for_seasons": ["夏", "秋"],
        "suitable_for_terms": ["长夏", "白露", "处暑"],
        "wellness_effects": ["祛湿排浊", "疏通膀胱经", "增强免疫"],
        "recommended_reason": "背部为阳，长夏祛湿重点部位",
    },
    "腹部温养": {
        "suitable_for_body_types": ["阳虚质", "血虚质"],
        "suitable_for_seasons": ["冬", "春"],
        "suitable_for_terms": ["三九", "立春", "雨水"],
        "wellness_effects": ["温经散寒", "暖宫调经", "健脾养胃"],
        "recommended_reason": "腹部为阴中之阴，三九温养最佳",
    },
    "头部舒缓": {
        "suitable_for_body_types": ["气郁质", "阴虚质"],
        "suitable_for_seasons": ["春", "秋"],
        "suitable_for_terms": ["春分", "秋分", "清明"],
        "wellness_effects": ["疏肝解郁", "安神助眠", "清热明目"],
        "recommended_reason": "春秋分阴阳交替，头部舒缓调和气血",
    },
}


def init_service_terms_mapping(db: Session):
    """
    初始化服务项目的节气/体质关联配置
    将默认配置应用到数据库中的服务项目
    """
    services = db.query(ServiceItem).all()
    updated_count = 0

    for svc in services:
        if svc.name in DEFAULT_SERVICE_TERMS_MAPPING:
            config = DEFAULT_SERVICE_TERMS_MAPPING[svc.name]
            svc.suitable_for_body_types = config["suitable_for_body_types"]
            svc.suitable_for_seasons = config["suitable_for_seasons"]
            svc.suitable_for_terms = config["suitable_for_terms"]
            svc.wellness_effects = config["wellness_effects"]
            svc.recommended_reason = config["recommended_reason"]
            updated_count += 1

    if updated_count > 0:
        db.commit()
        logger.info(f"Initialized service terms mapping for {updated_count} services")

    return updated_count
