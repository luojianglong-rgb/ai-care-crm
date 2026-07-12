import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Float, Integer, Text, Boolean
from sqlalchemy.orm import relationship
from database import Base

class Client(Base):
    __tablename__ = "clients"

    client_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, index=True)
    phone = Column(String, index=True)
    gender = Column(String)
    age_group = Column(String)
    birth_date = Column(String, nullable=True)  # 出生年月
    address = Column(String, nullable=True)
    preferences = Column(JSON, default=list)

    # 消费模式与余额
    times_card_balance = Column(Integer, default=0)  # 次卡剩余次数
    cash_card_balance = Column(Float, default=0.0)   # 现金卡/储值余额

    # Phase 2 新增
    primary_analysis_type = Column(String, nullable=True)  # 最新专业分析主分类（冗余缓存）
    lifecycle_status = Column(String, default="new")       # 最新生命周期状态

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    health_history = relationship("HealthRecord", back_populates="client", cascade="all, delete-orphan")

class HealthRecord(Base):
    __tablename__ = "health_records"
    
    record_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    client_id = Column(String, ForeignKey("clients.client_id"))
    date = Column(DateTime, default=datetime.now)
    symptoms = Column(JSON, default=list)
    description = Column(String)
    treatment_provided = Column(String)
    deduct_times = Column(Integer, default=0)
    deduct_cash = Column(Float, default=0.0)
    notes = Column(String, nullable=True)
    
    client = relationship("Client", back_populates="health_history")

# --- 技师/员工表 (系统设置) ---
class StaffMember(Base):
    __tablename__ = "staff_members"
    staff_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, index=True)
    role = Column(String, default="技师") # 如 "店长", "高级理疗师", "美容师"
    phone = Column(String, nullable=True)
    password_hash = Column(String, nullable=True)  # WAP 端登录密码 (bcrypt 加密)
    services_supported = Column(JSON, default=list) # 存放该技师支持的服务项目名称列表
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.now)

# --- 预约表 ---
class Booking(Base):
    __tablename__ = "bookings"
    booking_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    client_id = Column(String, ForeignKey("clients.client_id"))
    service_name = Column(String)
    staff_name = Column(String)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    status = Column(String, default="pending")
    
    client = relationship("Client", backref="bookings")

# --- 服务项目表 (系统设置) ---
class ServiceItem(Base):
    __tablename__ = "service_items"
    item_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, index=True, unique=True)
    description = Column(String, nullable=True)
    is_active = Column(Integer, default=1)  # 1 for active, 0 for disabled

    # 新增：服务项目关联信息
    suitable_for_body_types = Column(JSON, nullable=True)  # 适合的体质类型 ["阳虚质", "气虚质", ...]
    suitable_for_seasons = Column(JSON, nullable=True)     # 适合的季节 ["春", "夏", "秋", "冬"]
    suitable_for_terms = Column(JSON, nullable=True)       # 适合的节气/养生节点 ["三伏", "三九", "长夏", ...]
    wellness_effects = Column(JSON, nullable=True)         # 养生功效 ["温阳散寒", "祛湿排毒", "健脾养胃", ...]
    recommended_reason = Column(String, nullable=True)     # 推荐话术要点

# --- 耗材分类表 (系统设置) ---
class InventoryCategory(Base):
    __tablename__ = "inventory_categories"
    category_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, index=True, unique=True)
    description = Column(String, nullable=True)
    is_active = Column(Integer, default=1)  # 1 for active, 0 for disabled

class InventoryItem(Base):
    __tablename__ = "inventory_items"
    item_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, index=True)
    category = Column(String)
    quantity = Column(Integer, default=0)
    unit = Column(String)
    price = Column(Float)
    last_updated = Column(DateTime, default=datetime.now, onupdate=datetime.now)

class InventoryUsageRecord(Base):
    __tablename__ = "inventory_usage_records"
    usage_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    item_id = Column(String, ForeignKey("inventory_items.item_id"))
    staff_name = Column(String) # Record staff name directly for simplicity
    quantity = Column(Integer)
    usage_date = Column(DateTime, default=datetime.now)
    notes = Column(String, nullable=True)

# --- 交易记录表 ---
class Transaction(Base):
    __tablename__ = "transactions"
    transaction_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    client_id = Column(String, ForeignKey("clients.client_id"))
    amount = Column(Float)
    transaction_type = Column(String)
    payment_method = Column(String)
    date = Column(DateTime, default=datetime.now)
    notes = Column(String, nullable=True)
    times_count = Column(Integer, default=0)  # 次卡次数（次卡充值/消费时使用）
    cash_amount = Column(Float, default=0.0)  # 实际收付金额（次卡充值时记录收款金额）

    client = relationship("Client", backref="transactions")


# ══════════════════════════════════════════════════════════════════
# 管理员表
# ══════════════════════════════════════════════════════════════════

class AdminUser(Base):
    """管理台登录账号"""
    __tablename__ = "admin_users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    display_name = Column(String, default="")
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.now)


# ══════════════════════════════════════════════════════════════════
# Phase 2 新增表
# ══════════════════════════════════════════════════════════════════

class AIUsageRecord(Base):
    """AI 调用额度记录"""
    __tablename__ = "ai_usage_records"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    usage_type = Column(String, index=True)  # analysis / plan / content
    client_id = Column(String, ForeignKey("clients.client_id"), nullable=True)
    model_provider = Column(String)
    model_name = Column(String)
    tokens_used = Column(Integer, default=0)
    cost_estimate = Column(Float, default=0.0)
    success = Column(Integer, default=1)  # 1=success, 0=failed
    error_message = Column(String, nullable=True)
    month_key = Column(String, index=True)  # "2026-03"
    created_at = Column(DateTime, default=datetime.now)


class ProfessionalAnalysis(Base):
    """多领域专业分析（通用化：体质辨识/肤质分析/发质分析等）"""
    __tablename__ = "professional_analyses"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    client_id = Column(String, ForeignKey("clients.client_id"), index=True)
    domain = Column(String)  # tcm / skin / hair / nail / postpartum / general
    primary_type = Column(String)  # 主分类（阳虚质/敏感肌/受损发质...）
    secondary_type = Column(String, nullable=True)
    symptoms_snapshot = Column(JSON, default=dict)
    observation_notes = Column(String, nullable=True)
    ai_analysis_summary = Column(Text)
    ai_recommendations = Column(JSON, default=dict)
    confidence_score = Column(Float, default=0.0)
    assessed_at = Column(DateTime, default=datetime.now)
    assessed_by = Column(String, nullable=True)  # staff_id or "ai_auto"
    created_at = Column(DateTime, default=datetime.now)

    client = relationship("Client", backref="professional_analyses")


class CarePlan(Base):
    """个性化服务方案（通用化）"""
    __tablename__ = "care_plans"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    client_id = Column(String, ForeignKey("clients.client_id"), index=True)
    analysis_id = Column(String, ForeignKey("professional_analyses.id"))
    in_store_services = Column(JSON, default=list)
    home_care_advice = Column(JSON, default=list)
    seasonal_notes = Column(Text, nullable=True)
    plan_summary = Column(Text)
    valid_until = Column(DateTime, nullable=True)
    status = Column(String, default="active")  # active / expired / superseded
    created_at = Column(DateTime, default=datetime.now)

    client = relationship("Client", backref="care_plans")
    analysis = relationship("ProfessionalAnalysis", backref="care_plans")


# ══════════════════════════════════════════════════════════════════
# Phase 2.2 剧本引擎
# ══════════════════════════════════════════════════════════════════

class ClientLifecycle(Base):
    """客户生命周期状态"""
    __tablename__ = "client_lifecycle"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    client_id = Column(String, ForeignKey("clients.client_id"), unique=True, index=True)
    current_status = Column(String, default="new")  # new / active / silent / churn_risk
    visit_count = Column(Integer, default=0)
    last_visit_at = Column(DateTime, nullable=True)
    last_contact_at = Column(DateTime, nullable=True)
    status_changed_at = Column(DateTime, default=datetime.now)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    client = relationship("Client", backref="lifecycle")


class Playbook(Base):
    """运营剧本"""
    __tablename__ = "playbooks"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, index=True)
    description = Column(Text, nullable=True)
    trigger_type = Column(String)  # time_since_visit / solar_term / weather_change / birthday / post_service / lifecycle_change
    trigger_config = Column(JSON, default=dict)
    target_filter = Column(JSON, default=dict)  # 目标客户筛选（体质类型、生命周期状态等）
    content_template = Column(Text, nullable=True)  # AI 文案生成 Prompt 模板
    approval_mode = Column(String, default="auto")  # auto / sampling / manual
    sampling_rate = Column(Float, default=0.1)
    send_window_start = Column(String, default="09:00")
    send_window_end = Column(String, default="18:00")
    send_channel = Column(String, default="ml307a")  # ml307a / auto（短信猫或手动）
    is_active = Column(Integer, default=1)
    is_system = Column(Integer, default=0)  # 系统预设不可删
    priority = Column(Integer, default=5)  # 1最高10最低
    cooldown_days = Column(Integer, default=3)  # 同一客户最短触达间隔
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class CampaignTask(Base):
    """营销任务队列（支持剧本触发和AI智能触达）"""
    __tablename__ = "campaign_tasks"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    playbook_id = Column(String, ForeignKey("playbooks.id"), index=True, nullable=True)  # null表示AI智能触达
    client_id = Column(String, ForeignKey("clients.client_id"), index=True)
    generated_content = Column(Text)
    status = Column(String, default="pending_approval", index=True)
    # pending_approval / approved / queued / sent / failed / rejected
    approval_mode = Column(String)
    is_sampled = Column(Integer, default=0)
    scheduled_at = Column(DateTime, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    send_channel = Column(String, default="ml307a")  # 实际发送渠道
    error_message = Column(String, nullable=True)
    # AI智能触达专属字段
    ai_content_type = Column(String, nullable=True)  # AI触达类型：seasonal_care / service_recommend / wakeup 等
    ai_reason = Column(Text, nullable=True)  # AI判断理由
    created_at = Column(DateTime, default=datetime.now)

    playbook = relationship("Playbook", backref="tasks")
    client = relationship("Client", backref="campaign_tasks")


# ══════════════════════════════════════════════════════════════════
# Phase 2.3 回复闭环
# ══════════════════════════════════════════════════════════════════

class ClientReply(Base):
    """客户回复采集"""
    __tablename__ = "client_replies"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    client_id = Column(String, ForeignKey("clients.client_id"), index=True)
    campaign_task_id = Column(String, ForeignKey("campaign_tasks.id"), nullable=True)
    raw_content = Column(Text)  # 客户原始回复
    ai_parsed_intent = Column(String, nullable=True)
    # symptom_improved / symptom_persists / want_booking / price_inquiry / general_chat / negative
    ai_parsed_details = Column(JSON, default=dict)
    # {"sentiment": "positive", "symptoms_mentioned": [...], "suggested_next_action": "..."}
    auto_action_taken = Column(String, nullable=True)
    # updated_health_record / triggered_followup / notified_manager / none
    replied_at = Column(DateTime, default=datetime.now)
    created_at = Column(DateTime, default=datetime.now)

    client = relationship("Client", backref="replies")
    campaign_task = relationship("CampaignTask", backref="replies")