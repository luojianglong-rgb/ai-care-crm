from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from datetime import datetime

class HealthRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    record_id: Optional[str] = None
    date: datetime = Field(default_factory=datetime.now)
    symptoms: List[str] = []  # 症状标签：如 ["怕冷", "失眠"]
    description: str          # 详细描述
    treatment_provided: str   # 本次调理项目
    deduct_times: int = 0     # 本次扣减次卡次数
    deduct_cash: float = 0.0  # 本次扣减现金金额
    notes: Optional[str] = None # 备注

class HealthRecordUpdate(BaseModel):
    symptoms: Optional[List[str]] = None
    description: Optional[str] = None
    treatment_provided: Optional[str] = None
    notes: Optional[str] = None

class ClientProfile(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    client_id: Optional[str] = None
    name: str                 # 真实姓名 (本地存储)
    phone: str                # 手机号 (本地存储)
    gender: str               # 性别
    age_group: str            # 年龄段：如 "30-40"
    birth_date: Optional[str] = None  # 出生年月
    address: Optional[str] = None # 住址 (本地存储)
    preferences: List[str] = []   # 消费偏好
    times_card_balance: int = 0   # 次卡余额
    cash_card_balance: float = 0.0 # 现金储值余额
    health_history: List[HealthRecord] = [] # 历史健康档案
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

class ClientCreate(BaseModel):
    name: str
    phone: str
    gender: str
    age_group: str
    birth_date: Optional[str] = None
    address: Optional[str] = None
    preferences: List[str] = []
    times_card_balance: int = 0
    cash_card_balance: float = 0.0

class WalletAction(BaseModel):
    amount: float # 增加为正，减少为负（次卡充值时为次数，现金充值时为金额）
    action_type: str # "times" 或 "cash"
    notes: Optional[str] = None
    cash_amount: Optional[float] = None  # 实际收款金额（次卡充值时使用）

class ClientUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    preferences: Optional[List[str]] = None
    updated_at: datetime = Field(default_factory=datetime.now)

# --- 服务项目设置模块 ---
class ServiceItemCreate(BaseModel):
    name: str
    description: Optional[str] = None
    is_active: int = 1

class ServiceItemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[int] = None

class ServiceItemModel(ServiceItemCreate):
    model_config = ConfigDict(from_attributes=True)
    item_id: str

class StaffMemberCreate(BaseModel):
    name: str
    role: str = "技师"
    phone: Optional[str] = None
    password: Optional[str] = None  # 初始密码（明文，后端会加密存储）
    services_supported: List[str] = []
    is_active: int = 1

class StaffMemberUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    phone: Optional[str] = None
    password: Optional[str] = None  # 新密码（用于修改密码）
    services_supported: Optional[List[str]] = None
    is_active: Optional[int] = None

class StaffMemberModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    staff_id: str
    name: str
    role: str = "技师"
    phone: Optional[str] = None
    services_supported: List[str] = []
    is_active: int = 1

# --- 预约管理模块 ---
class BookingCreate(BaseModel):
    client_id: str
    service_name: str
    staff_name: str
    start_time: datetime
    end_time: datetime
    status: str = "pending" # pending, confirmed, completed, cancelled

class Booking(BookingCreate):
    model_config = ConfigDict(from_attributes=True)
    booking_id: str

class BookingUpdate(BaseModel):
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: Optional[str] = None
    staff_name: Optional[str] = None

# --- 库存管理模块 ---
class InventoryItemCreate(BaseModel):
    name: str
    category: str
    quantity: int
    unit: str
    price: float

class InventoryItem(InventoryItemCreate):
    model_config = ConfigDict(from_attributes=True)
    item_id: str
    last_updated: datetime

class InventoryItemUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    quantity: Optional[int] = None
    unit: Optional[str] = None
    price: Optional[float] = None

class InventoryUsageCreate(BaseModel):
    item_id: str
    staff_name: str
    quantity: int
    notes: Optional[str] = None

class InventoryUsageRecordModel(InventoryUsageCreate):
    model_config = ConfigDict(from_attributes=True)
    usage_id: str
    usage_date: datetime

# --- 耗材分类管理模块 ---
class InventoryCategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None
    is_active: int = 1

class InventoryCategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[int] = None

class InventoryCategoryModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    category_id: str
    name: str
    description: Optional[str] = None
    is_active: int = 1

# --- 财务收银模块 ---
class TransactionCreate(BaseModel):
    client_id: str
    amount: float
    transaction_type: str # "payment" (支付), "refund" (退款), "recharge" (充值)
    payment_method: str # "wechat", "alipay", "card", "cash", "member_card"
    notes: Optional[str] = None
    times_count: Optional[int] = None  # 次卡次数（次卡充值/消费时使用）
    cash_amount: Optional[float] = None  # 实际收付金额（次卡充值时记录收款金额）

class Transaction(TransactionCreate):
    model_config = ConfigDict(from_attributes=True)
    transaction_id: str
    date: datetime