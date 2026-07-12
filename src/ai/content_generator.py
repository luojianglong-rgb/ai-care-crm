"""
营销文案生成服务
7 种场景 Prompt，业态自适应，调用 LLM 生成个性化文案。
支持中医养生节点（三九、三伏、长夏等）的文案注入。
支持智能服务项目推荐，促进销售和回购。
"""
import logging
import json
from sqlalchemy.orm import Session

from config import AppConfig
from ai.llm_client import LLMClient
from ai.pii_masker import PIIMasker
from services.quota_service import QuotaService
from playbook.solar_terms import SolarTermCalendar

logger = logging.getLogger(__name__)

# 场景 Prompt 模板（{变量} 在运行时注入）
SCENE_PROMPTS = {
    "seasonal_care": {
        "style": "温馨关怀、知识科普",
        "max_chars": 150,
        "prompt": """你是一位{business_display}的专业顾问。请为以下客户撰写一条季节关怀消息。

当前季节节气：{season}
中医养生节点：{tcm_period}
五运六气：{wuyun_sixqi}
养生重点：{wellness_focus}
客户称呼：{client_name}
客户专业分析：{analysis_type}
关键特征：{key_symptoms}
推荐服务项目：{recommended_services_json}
店铺名称：{store_name}

要求：
1. 80-150 字，温馨关怀风格
2. 融入当前季节/节气的专业护理知识
3. 结合中医养生节点的建议
4. 自然植入 1 个推荐服务项目（从推荐列表中选择最匹配的），说明为什么这个服务适合客户当前状况
5. 结尾引导客户回复或预约"""
    },
    "new_client_welcome": {
        "style": "热情专业、建立信任",
        "max_chars": 200,
        "prompt": """你是{store_name}的专业顾问。请为新客户撰写一条欢迎消息。

客户称呼：{client_name}
首次服务项目：{service_info}
专业分析结果：{analysis_type}
推荐服务项目：{recommended_services_json}
店铺名称：{store_name}

要求：
1. 100-200 字，热情欢迎
2. 简要提及分析结果
3. 从推荐服务项目中选择 1-2 个，推荐下次到店的适合项目
4. 说明推荐理由（结合体质特点）"""
    },
    "post_service_followup": {
        "style": "关切询问、引导回访",
        "max_chars": 100,
        "prompt": """你是{store_name}的专业顾问。请为客户撰写一条服务后随访消息。

客户称呼：{client_name}
上次服务项目：{service_info}
距上次服务天数：{days_info}
客户专业分析：{analysis_type}
推荐服务项目：{recommended_services_json}

要求：
1. 60-100 字，关切询问服务效果和身体变化
2. 根据客户体质，从推荐服务中选择 1 个适合的后续调理项目
3. 说明服务组合的协同效果，引导预约"""
    },
    "silent_client_wakeup": {
        "style": "不打扰、给价值",
        "max_chars": 120,
        "prompt": """你是{store_name}的专业顾问。请为一位较久未到店的客户撰写一条唤醒消息。

客户称呼：{client_name}
未到店天数：{days_info}
客户专业分析：{analysis_type}
当前季节：{season}
中医养生节点：{tcm_period}
推荐服务项目：{recommended_services_json}

要求：
1. 80-120 字，不要用"好久不见"等群发感用语
2. 提供有价值的专业信息（节气/体质养生建议）
3. 从推荐服务中选择 1 个最匹配的项目，作为回访理由
4. 自然引导，不显推销"""
    },
    "churn_rescue": {
        "style": "诚恳、高价值吸引",
        "max_chars": 150,
        "prompt": """你是{store_name}的顾问。请为一位流失预警客户撰写一条挽留消息。

客户称呼：{client_name}
未到店天数：{days_info}
客户专业分析：{analysis_type}
当前季节：{season}
中医养生节点：{tcm_period}
推荐服务项目：{recommended_services_json}

要求：
1. 100-150 字，诚恳关怀
2. 提供针对性的专业建议
3. 从推荐服务中选择 1 个核心项目，暗示专属优惠或体验
4. 强调服务的独特价值和时效性"""
    },
    "birthday_greeting": {
        "style": "祝福、专属感",
        "max_chars": 80,
        "prompt": """你是{store_name}的顾问。请为客户撰写一条生日祝福消息。

客户称呼：{client_name}
店铺名称：{store_name}
推荐服务项目：{recommended_services_json}

要求：
1. 50-80 字，真诚祝福
2. 可暗示生日专属福利（从推荐服务中选择 1 个作为礼遇项目）
3. 语气像朋友而非商家"""
    },
    "weather_alert": {
        "style": "贴心实用、自然不生硬",
        "max_chars": 100,
        "prompt": """你是{store_name}的专业顾问。请为客户撰写一条天气变化关怀消息。

客户称呼：{client_name}
客户专业分析：{analysis_type}
天气情况：{weather_info}
推荐服务项目：{recommended_services_json}
店铺名称：{store_name}

要求：
1. 60-100 字，贴心提醒与专业分析结合
2. 从推荐服务中选择 1 个适合当前天气状况的项目
3. 说明天气对体质的影响，自然推荐"""
    },
    "holiday_care": {
        "style": "节日关怀、预约引导",
        "max_chars": 150,
        "prompt": """你是{store_name}的专业顾问。请为客户撰写一条节日关怀消息。

客户称呼：{client_name}
即将到来的节日：{holiday_name}
距节日天数：{days_until_holiday}
假期天数：{holiday_days}
关怀类型：{holiday_care_type}
客户专业分析：{analysis_type}
推荐服务项目：{recommended_services_json}
店铺名称：{store_name}
放假安排：{holiday_schedule}

要求：
1. 80-150 字，节日关怀风格
2. 如是预约提醒：提醒节前预约，说明放假安排
3. 如是不出游关怀：提供店内服务和专属优惠信息
4. 结合节日特点和客户体质，推荐 1 个适合的服务项目
5. 自然引导预约或咨询"""
    },
    "holiday_greeting": {
        "style": "节日祝福、温馨亲切",
        "max_chars": 80,
        "prompt": """你是{store_name}的专业顾问。请为客户撰写一条节日祝福消息。

客户称呼：{client_name}
节日名称：{holiday_name}
祝福类型：{greeting_type}
店铺名称：{store_name}

要求：
1. 50-80 字，真诚祝福
2. 结合节日特点（如春节祝福新年、中秋祝福团圆）
3. 可暗示节日专属福利或服务
4. 语气温馨，像朋友问候"""
    },
}

# 所有场景共用的约束
CONTENT_CONSTRAINTS = """
## 文案约束
- 语气自然亲切，像朋友聊天而非机器群发
- 严禁出现"尊敬的客户"、"温馨提示"等群发话术感强的用语
- 必须结合客户的具体分析结果和状况，体现个性化
- 从推荐服务项目中选择最匹配的 1 个，自然植入并说明推荐理由
- 结尾留一个开放性问题或关怀，引导客户回复互动
- 当前业态：{business_display}，请确保用语符合该行业习惯
- 直接输出文案正文，不要输出标题、引号或其他格式标记
"""


class ContentGenerator:

    def __init__(self, config: AppConfig, llm: LLMClient):
        self.config = config
        self.llm = llm
        self.masker = PIIMasker()
        self.quota = QuotaService(config)

    def generate(self, db: Session, scene: str, variables: dict) -> dict:
        """
        生成营销文案。
        Args:
            scene: 场景名（seasonal_care / new_client_welcome / ...）
            variables: 模板变量（client_name, analysis_type, season 等）
        Returns:
            {"success": bool, "content": str, "error": str, "tokens_used": int}
        """
        # 额度检查
        allowed, msg = self.quota.check_quota(db, "content")
        if not allowed:
            return {"success": False, "content": "", "error": msg, "tokens_used": 0}

        scene_cfg = SCENE_PROMPTS.get(scene)
        if not scene_cfg:
            return {"success": False, "content": "", "error": f"未知场景：{scene}", "tokens_used": 0}

        # 注入默认变量
        business_display = self.config.get_terminology("analysis_name") or self.config.store.business_type
        variables.setdefault("store_name", self.config.store.name)
        variables.setdefault("business_display", business_display)

        # 获取当前中医养生节点信息
        tcm_context = SolarTermCalendar.get_current_tcm_context()
        variables.setdefault("season", tcm_context["season_display"])

        # 注入中医养生节点信息
        if tcm_context["active_periods"]:
            variables.setdefault("tcm_period", "、".join(tcm_context["active_periods"]))
            variables.setdefault("wellness_focus", tcm_context.get("wellness_advice", "顺应时节、调养身心"))
        else:
            variables.setdefault("tcm_period", tcm_context["season"])
            variables.setdefault("wellness_focus", "顺应时节、调养身心")

        # 注入五运六气信息
        variables.setdefault("wuyun_sixqi", tcm_context.get("wuyun_sixqi", ""))

        # 格式化推荐服务项目为 JSON 字符串
        recommended_services = variables.get("recommended_services", [])
        if recommended_services:
            variables.setdefault("recommended_services_json", json.dumps(recommended_services, ensure_ascii=False))
        else:
            variables.setdefault("recommended_services_json", "[]")

        # PII 脱敏客户名（保留称呼但脱敏真实全名）
        client_name = variables.get("client_name", "")
        # 对于发送文案，保留称呼不脱敏（文案本身就是要发给客户的）

        # 组装 Prompt
        prompt_template = scene_cfg["prompt"] + CONTENT_CONSTRAINTS
        try:
            system_prompt = prompt_template.format(**variables)
        except KeyError as e:
            return {"success": False, "content": "", "error": f"缺少变量：{e}", "tokens_used": 0}

        # 调用 LLM
        resp = self.llm.chat(system_prompt, "请直接输出文案内容", temperature=0.6)

        # 记录用量
        self.quota.record_usage(
            db, usage_type="content",
            model_provider=self.config.llm.provider,
            model_name=resp.model,
            tokens_used=resp.tokens_used,
            success=resp.success,
            error_message=resp.error if not resp.success else None,
        )

        if not resp.success:
            return {"success": False, "content": "", "error": resp.error, "tokens_used": resp.tokens_used}

        content = resp.content.strip().strip('"').strip("'")
        return {"success": True, "content": content, "error": "", "tokens_used": resp.tokens_used}
