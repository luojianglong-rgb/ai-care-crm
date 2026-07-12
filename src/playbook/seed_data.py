"""
系统预设剧本 Seed Data
系统首次部署时自动初始化（含节假日关怀剧本）。
"""
from db_models import Playbook
from sqlalchemy.orm import Session


PRESET_PLAYBOOKS = [
    {
        "name": "新客欢迎回访",
        "description": "新客首次服务后 3 天自动发送分析报告和居家建议",
        "trigger_type": "post_service",
        "trigger_config": {"days_after_service": 3},
        "target_filter": {"lifecycle_status": "new"},
        "approval_mode": "auto",
        "priority": 2,
        "cooldown_days": 30,
    },
    {
        "name": "服务效果追踪",
        "description": "每次服务后 7 天自动询问效果和身体变化",
        "trigger_type": "post_service",
        "trigger_config": {"days_after_service": 7},
        "target_filter": {"lifecycle_status": "active"},
        "approval_mode": "auto",
        "priority": 3,
        "cooldown_days": 10,
    },
    {
        "name": "季节/节气关怀",
        "description": "节气前 3 天向匹配客户推送季节养护提醒",
        "trigger_type": "solar_term",
        "trigger_config": {"days_before": 3, "terms": []},  # 空=所有节气
        "target_filter": {},
        "approval_mode": "auto",
        "priority": 5,
        "cooldown_days": 15,
    },
    {
        "name": "生日关怀",
        "description": "客户生日前 7 天发送祝福和专属福利",
        "trigger_type": "birthday",
        "trigger_config": {"days_before": 7},
        "target_filter": {},
        "approval_mode": "auto",
        "priority": 1,
        "cooldown_days": 365,
    },
    {
        "name": "沉默客唤醒",
        "description": "客户进入沉默状态（30天未到店）时自动触发唤醒",
        "trigger_type": "lifecycle_change",
        "trigger_config": {"on_enter_status": "silent"},
        "target_filter": {},
        "approval_mode": "sampling",
        "sampling_rate": 0.1,
        "priority": 4,
        "cooldown_days": 15,
    },
    {
        "name": "流失预警挽留",
        "description": "客户进入流失预警（60天未到店）时触发挽留，需店长审批",
        "trigger_type": "lifecycle_change",
        "trigger_config": {"on_enter_status": "churn_risk"},
        "target_filter": {},
        "approval_mode": "manual",
        "priority": 1,
        "cooldown_days": 30,
    },
    {
        "name": "天气骤变关怀",
        "description": "降温超过 8°C 时向相关客户发送温馨提醒",
        "trigger_type": "weather_change",
        "trigger_config": {"temp_drop_threshold": 8},
        "target_filter": {},
        "approval_mode": "auto",
        "priority": 3,
        "cooldown_days": 7,
        "is_active": 0,  # 默认关闭（需配置天气 API 后启用）
    },
    # ── 节假日关怀剧本 ──────────────────────────────────────────────
    {
        "name": "节前预约提醒",
        "description": "长假前 7 天提醒客户预约服务，并通知放假安排",
        "trigger_type": "holiday",
        "trigger_config": {
            "care_type": "appointment_reminder",
            "days_before": 7,
            "holidays": ["spring_festival", "national_day", "labor_day"],  # 长假
        },
        "target_filter": {},
        "approval_mode": "auto",
        "priority": 2,
        "cooldown_days": 30,
    },
    {
        "name": "不出游客户关怀",
        "description": "长假期间向不出游客户提供店内服务和专属优惠",
        "trigger_type": "holiday",
        "trigger_config": {
            "care_type": "non_travel_care",
            "days_before": 5,
            "holidays": ["spring_festival", "national_day"],
            "target_non_travel": True,
        },
        "target_filter": {},
        "approval_mode": "auto",
        "priority": 3,
        "cooldown_days": 15,
    },
    {
        "name": "节日祝福问候",
        "description": "传统节日当天发送祝福消息",
        "trigger_type": "holiday_greeting",
        "trigger_config": {
            "holidays": ["spring_festival", "mid_autumn", "dragon_boat", "qingming"],
        },
        "target_filter": {},
        "approval_mode": "auto",
        "priority": 1,
        "cooldown_days": 365,
    },
]


def init_preset_playbooks(db: Session):
    """初始化系统预设剧本（已存在则跳过）。"""
    existing = {pb.name for pb in db.query(Playbook.name).filter(Playbook.is_system == 1).all()}
    count = 0
    for data in PRESET_PLAYBOOKS:
        if data["name"] in existing:
            continue
        pb = Playbook(
            name=data["name"],
            description=data.get("description", ""),
            trigger_type=data["trigger_type"],
            trigger_config=data.get("trigger_config", {}),
            target_filter=data.get("target_filter", {}),
            content_template=data.get("content_template", ""),
            approval_mode=data.get("approval_mode", "auto"),
            sampling_rate=data.get("sampling_rate", 0.1),
            priority=data.get("priority", 5),
            cooldown_days=data.get("cooldown_days", 3),
            is_active=data.get("is_active", 1),
            is_system=1,
        )
        db.add(pb)
        count += 1

    if count:
        db.commit()
    return count
