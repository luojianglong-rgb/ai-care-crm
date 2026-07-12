"""
AI-Care CRM 配置加载器
从 config.yaml 加载配置，并根据 business_type 自动映射业态默认值。
"""
import os
import yaml
from dataclasses import dataclass, field
from typing import Optional

# ── 业态默认值映射表 ──────────────────────────────────────────────

BUSINESS_DEFAULTS = {
    "tcm_wellness": {
        "staff_title": "理疗师",
        "analysis_name": "中医体质辨识",
        "plan_name": "调理方案",
        "analysis_domain": "tcm",
        "default_categories": ["艾灸", "推拿", "拔罐", "经络疏通", "刮痧"],
    },
    "spa": {
        "staff_title": "美容师",
        "analysis_name": "肤质分析",
        "plan_name": "护肤方案",
        "analysis_domain": "skin",
        "default_categories": ["面部护理", "身体护理", "精油SPA", "眼部护理"],
    },
    "hair_salon": {
        "staff_title": "发型师",
        "analysis_name": "发质/头皮分析",
        "plan_name": "护发方案",
        "analysis_domain": "hair",
        "default_categories": ["剪发", "染发", "烫发", "头皮护理", "造型"],
    },
    "nail_lash": {
        "staff_title": "美甲师",
        "analysis_name": "甲型适配分析",
        "plan_name": "美甲方案",
        "analysis_domain": "nail",
        "default_categories": ["美甲", "美睫", "手部护理"],
    },
    "skin_care": {
        "staff_title": "皮肤管理师",
        "analysis_name": "皮肤问题诊断",
        "plan_name": "管理方案",
        "analysis_domain": "skin",
        "default_categories": ["小气泡", "光子嫩肤", "果酸焕肤", "屏障修复"],
    },
    "postpartum": {
        "staff_title": "修复师",
        "analysis_name": "产后体质评估",
        "plan_name": "修复方案",
        "analysis_domain": "postpartum",
        "default_categories": ["盆底修复", "腹直肌修复", "体质调理", "产后塑形"],
    },
    "general": {
        "staff_title": "技师",
        "analysis_name": "需求偏好分析",
        "plan_name": "服务方案",
        "analysis_domain": "general",
        "default_categories": ["基础服务"],
    },
}


# ── 业态剧本配置 ──────────────────────────────────────────────────────

PLAYBOOK_BUSINESS_MAPPING = {
    "tcm_wellness": {
        "enabled_presets": ["birthday", "solar_term", "churn_rescue", "holiday", "holiday_greeting"],
        "disabled_presets": [],  # 无禁用
        "ai_reach_enabled": True,
        "ai_reach_frequency": "weekly",  # 每周智能触达
        "ai_reach_focus": ["seasonal_care", "service_recommend"],  # AI触达重点关注类型
        "holiday_enabled": True,
        "holiday_types": ["traditional", "modern"],  # 传统节日和法定节假日都启用
        "holiday_care_types": ["appointment_reminder", "non_travel_care", "greeting"],  # 三种关怀类型
    },
    "spa": {
        "enabled_presets": ["birthday", "solar_term", "churn_rescue", "holiday", "holiday_greeting"],
        "disabled_presets": [],
        "ai_reach_enabled": True,
        "ai_reach_frequency": "weekly",
        "ai_reach_focus": ["seasonal_care", "service_recommend"],
        "holiday_enabled": True,
        "holiday_types": ["traditional", "modern", "western"],  # SPA也支持西方节日（情人节、女神节）
        "holiday_care_types": ["appointment_reminder", "non_travel_care", "greeting"],
    },
    "hair_salon": {
        "enabled_presets": ["birthday", "churn_rescue", "holiday"],
        "disabled_presets": ["solar_term"],  # 美发店不需要节气关怀
        "ai_reach_enabled": True,
        "ai_reach_frequency": "biweekly",  # 每两周
        "ai_reach_focus": ["service_recommend", "card_reminder"],
        "holiday_enabled": True,
        "holiday_types": ["modern", "western"],  # 主要法定节假日和西方节日
        "holiday_care_types": ["appointment_reminder", "greeting"],
    },
    "nail_lash": {
        "enabled_presets": ["birthday", "churn_rescue", "holiday"],
        "disabled_presets": ["solar_term", "weather_change"],  # 美甲店不需要节气、天气关怀
        "ai_reach_enabled": True,
        "ai_reach_frequency": "monthly",  # 每月（美甲周期较长）
        "ai_reach_focus": ["followup", "card_reminder"],
        "holiday_enabled": True,
        "holiday_types": ["modern", "western"],  # 美甲适合女神节、情人节等
        "holiday_care_types": ["appointment_reminder", "greeting"],
    },
    "skin_care": {
        "enabled_presets": ["birthday", "solar_term", "churn_rescue", "holiday", "holiday_greeting"],
        "disabled_presets": [],
        "ai_reach_enabled": True,
        "ai_reach_frequency": "weekly",
        "ai_reach_focus": ["seasonal_care", "service_recommend"],
        "holiday_enabled": True,
        "holiday_types": ["traditional", "modern", "western"],
        "holiday_care_types": ["appointment_reminder", "non_travel_care", "greeting"],
    },
    "postpartum": {
        "enabled_presets": ["birthday", "solar_term", "churn_rescue", "holiday", "holiday_greeting"],
        "disabled_presets": [],
        "ai_reach_enabled": True,
        "ai_reach_frequency": "weekly",
        "ai_reach_focus": ["followup", "service_recommend"],
        "holiday_enabled": True,
        "holiday_types": ["traditional", "modern"],  # 传统节日和法定节假日
        "holiday_care_types": ["appointment_reminder", "non_travel_care", "greeting"],
    },
    "general": {
        "enabled_presets": ["birthday", "churn_rescue", "holiday"],
        "disabled_presets": ["solar_term"],
        "ai_reach_enabled": True,
        "ai_reach_frequency": "biweekly",
        "ai_reach_focus": ["general_care", "service_recommend"],
        "holiday_enabled": True,
        "holiday_types": ["modern"],  # 仅法定节假日
        "holiday_care_types": ["appointment_reminder", "greeting"],
    },
}


# ── 配置数据类 ────────────────────────────────────────────────────

@dataclass
class StoreConfig:
    name: str = "AI-Care CRM"
    business_type: str = "general"


@dataclass
class TerminologyConfig:
    staff_title: str = ""
    analysis_name: str = ""
    plan_name: str = ""


@dataclass
class QuotaTier:
    max_clients: int = 50
    max_staff: int = 3
    # AI 额度：基础版用 total（总次数），专业版用 weekly（每周），至尊版不限
    ai_total_limit: int = 0  # 总次数限制（基础版用，0 表示不启用）
    ai_weekly_limit: int = 0  # 每周次数限制（专业版用，0 表示不启用）
    ai_analysis_per_month: int = 10  # 兼容旧逻辑
    ai_plan_per_month: int = 10
    ai_content_per_month: int = 20
    custom_playbooks: bool = False
    sms_monthly: int = 0  # 短信月限额（至尊版用）
    export_monthly: int = 0  # 数据导出月限额（专业版用）


@dataclass
class LicenseConfig:
    key: str = ""


@dataclass
class LLMProxyConfig:
    endpoint: str = ""
    merchant_token: str = ""


@dataclass
class LLMProviderInfo:
    base_url: str = ""
    default_model: str = ""


@dataclass
class LLMConfig:
    mode: str = "direct"
    provider: str = "deepseek"
    api_key: str = ""
    model: str = "deepseek-chat"
    temperature: float = 0.3
    max_tokens: int = 2000
    timeout: int = 30
    proxy: LLMProxyConfig = field(default_factory=LLMProxyConfig)
    providers: dict[str, LLMProviderInfo] = field(default_factory=dict)

    def get_base_url(self) -> str:
        if self.mode == "proxy":
            return self.proxy.endpoint
        info = self.providers.get(self.provider)
        return info.base_url if info else ""

    def get_api_key(self) -> str:
        if self.mode == "proxy":
            return self.proxy.merchant_token
        return self.api_key

    def get_model(self) -> str:
        if self.mode == "proxy":
            return "auto"
        return self.model


@dataclass
class PlaybookConfig:
    scan_hour: int = 6
    send_interval_min: int = 10
    send_delay_min: int = 30
    send_delay_max: int = 90


@dataclass
class ServerConfig:
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    dev_mode: bool = False  # 开发模式：绕过会员等级限制


# ── 主配置类 ──────────────────────────────────────────────────────

@dataclass
class AppConfig:
    store: StoreConfig = field(default_factory=StoreConfig)
    terminology: TerminologyConfig = field(default_factory=TerminologyConfig)
    license: LicenseConfig = field(default_factory=LicenseConfig)
    quotas: dict[str, QuotaTier] = field(default_factory=dict)
    llm: LLMConfig = field(default_factory=LLMConfig)
    playbook: PlaybookConfig = field(default_factory=PlaybookConfig)
    server: ServerConfig = field(default_factory=ServerConfig)

    # 运行时计算的属性
    current_tier: str = "basic"  # 由 license_manager 验证后设置
    business_defaults: dict = field(default_factory=dict)
    playbook_business_config: dict = field(default_factory=dict)  # 业态剧本配置
    raw: dict = field(default_factory=dict)  # 原始 yaml 字典，供渠道等模块读取

    # License 运行时状态（由 license_manager 在启动/激活时写入）
    read_only_mode: bool = False          # 宽限期内只读
    license_status: str = "unactivated"   # active / trial_active / grace_period / expired / invalid / unactivated
    is_trial: bool = False                # 是否试用版
    grace_days_remaining: int = 0         # 宽限期剩余天数
    days_remaining: int = 0               # 授权剩余天数

    def get_terminology(self, key: str) -> str:
        """获取术语：优先用自定义值，否则用业态默认值。"""
        custom = getattr(self.terminology, key, "")
        if custom:
            return custom
        return self.business_defaults.get(key, "")

    def get_quota(self) -> QuotaTier:
        """获取当前套餐的额度配置。"""
        return self.quotas.get(self.current_tier, self.quotas.get("basic", QuotaTier()))

    @property
    def analysis_domain(self) -> str:
        return self.business_defaults.get("analysis_domain", "general")


# ── 加载函数 ──────────────────────────────────────────────────────

def _parse_providers(raw: dict) -> dict[str, LLMProviderInfo]:
    result = {}
    for name, info in (raw or {}).items():
        result[name] = LLMProviderInfo(
            base_url=info.get("base_url", ""),
            default_model=info.get("default_model", ""),
        )
    return result


def _parse_quotas(raw: dict) -> dict[str, QuotaTier]:
    result = {}
    for tier_name, vals in (raw or {}).items():
        result[tier_name] = QuotaTier(
            max_clients=vals.get("max_clients", 50),
            max_staff=vals.get("max_staff", 3),
            ai_total_limit=vals.get("ai_total_limit", 0),
            ai_weekly_limit=vals.get("ai_weekly_limit", 0),
            ai_analysis_per_month=vals.get("ai_analysis_per_month", 10),
            ai_plan_per_month=vals.get("ai_plan_per_month", 10),
            ai_content_per_month=vals.get("ai_content_per_month", 20),
            custom_playbooks=vals.get("custom_playbooks", False),
            sms_monthly=vals.get("sms_monthly", 0),
            export_monthly=vals.get("export_monthly", 0),
        )
    return result


def get_config_path() -> str:
    """获取配置文件路径（支持 PyInstaller 打包环境）"""
    import sys
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller 打包环境：配置文件在 EXE 同级的 config 目录
        # 使用 sys.executable 获取 EXE 实际路径，而不是 os.getcwd()
        exe_dir = os.path.dirname(sys.executable)
        return os.path.join(exe_dir, "config", "config.yaml")
    else:
        # 开发环境：配置文件在 src 目录
        return os.path.join(os.path.dirname(__file__), "config.yaml")


def load_config(config_path: Optional[str] = None) -> AppConfig:
    """
    从 config.yaml 加载配置。
    若文件不存在，使用全部默认值（基础版 + general 业态）。
    """
    if config_path is None:
        config_path = get_config_path()

    raw = {}
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

    # 解析各段
    store_raw = raw.get("store", {})
    store = StoreConfig(
        name=store_raw.get("name", "AI-Care CRM"),
        business_type=store_raw.get("business_type", "general"),
    )

    term_raw = raw.get("terminology", {})
    terminology = TerminologyConfig(
        staff_title=term_raw.get("staff_title", "") or "",
        analysis_name=term_raw.get("analysis_name", "") or "",
        plan_name=term_raw.get("plan_name", "") or "",
    )

    license_raw = raw.get("license", {})
    license_cfg = LicenseConfig(key=license_raw.get("key", "") or "")

    quotas = _parse_quotas(raw.get("quotas", {}))
    # 确保三个 tier 都存在
    if "basic" not in quotas:
        quotas["basic"] = QuotaTier(
            max_clients=10, max_staff=3,
            ai_total_limit=5,  # 基础版（永久免费）：AI 总次数 5 次，仅作功能体验
        )
    if "pro" not in quotas:
        quotas["pro"] = QuotaTier(
            max_clients=100, max_staff=10,
            ai_weekly_limit=20,  # 专业版：AI 每周 20 次
            custom_playbooks=False,  # 不可自定义剧本
            export_monthly=1,  # 数据导出每月 1 次
        )
    if "business" not in quotas:
        quotas["business"] = QuotaTier(
            max_clients=-1, max_staff=-1,
            ai_analysis_per_month=200, ai_plan_per_month=200, ai_content_per_month=200,  # 至尊版：AI 每月 200 次
            custom_playbooks=True,
            sms_monthly=100,  # 短信每月 100 条
        )

    llm_raw = raw.get("llm", {})
    proxy_raw = llm_raw.get("proxy", {})
    llm = LLMConfig(
        mode=llm_raw.get("mode", "direct"),
        provider=llm_raw.get("provider", "deepseek"),
        api_key=llm_raw.get("api_key", "") or "",
        model=llm_raw.get("model", "deepseek-chat"),
        temperature=llm_raw.get("temperature", 0.3),
        max_tokens=llm_raw.get("max_tokens", 2000),
        timeout=llm_raw.get("timeout", 30),
        proxy=LLMProxyConfig(
            endpoint=proxy_raw.get("endpoint", "") or "",
            merchant_token=proxy_raw.get("merchant_token", "") or "",
        ),
        providers=_parse_providers(llm_raw.get("providers", {})),
    )

    pb_raw = raw.get("playbook", {})
    playbook = PlaybookConfig(
        scan_hour=pb_raw.get("scan_hour", 6),
        send_interval_min=pb_raw.get("send_interval_min", 10),
        send_delay_min=pb_raw.get("send_delay_min", 30),
        send_delay_max=pb_raw.get("send_delay_max", 90),
    )

    srv_raw = raw.get("server", {})
    server = ServerConfig(
        host=srv_raw.get("host", "0.0.0.0"),
        port=srv_raw.get("port", 8000),
        debug=srv_raw.get("debug", False),
        dev_mode=srv_raw.get("dev_mode", False),
    )

    # 加载业态默认值
    btype = store.business_type
    business_defaults = BUSINESS_DEFAULTS.get(btype, BUSINESS_DEFAULTS["general"])
    playbook_business_config = PLAYBOOK_BUSINESS_MAPPING.get(btype, PLAYBOOK_BUSINESS_MAPPING["general"])

    config = AppConfig(
        store=store,
        terminology=terminology,
        license=license_cfg,
        quotas=quotas,
        llm=llm,
        playbook=playbook,
        server=server,
        business_defaults=business_defaults,
        playbook_business_config=playbook_business_config,
        raw=raw,
    )

    return config


# ── 全局单例 ──────────────────────────────────────────────────────

_config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """获取全局配置单例。首次调用时自动加载。"""
    global _config
    if _config is None:
        _config = load_config()
    return _config


def reload_config(config_path: Optional[str] = None) -> AppConfig:
    """重新加载配置（用于热更新场景）。"""
    global _config
    _config = load_config(config_path)
    return _config
