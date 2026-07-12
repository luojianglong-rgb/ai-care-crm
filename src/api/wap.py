"""
手机 WAP 端 - 技师移动工作台 API
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from datetime import datetime, timedelta
from typing import List, Optional
import bcrypt

from database import get_db
from db_models import StaffMember, Booking, Client, HealthRecord, Transaction
from models import StaffMemberModel
from services.booking_service import BookingService

router = APIRouter()
security = HTTPBearer(auto_error=False)

# === 工具函数 ===
def get_current_staff(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> StaffMember:
    """验证 Token 并获取当前登录技师"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未登录，请先登录",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials
    # Token 格式：staff_id (简单方案，生产环境可使用 JWT)
    staff = db.query(StaffMember).filter(
        StaffMember.staff_id == token,
        StaffMember.is_active == 1
    ).first()
    if not staff:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="技师不存在或已禁用",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return staff


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


def hash_password(password: str) -> str:
    """密码加密"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


# === 登录相关 ===
@router.post("/login")
def wap_login(name: str, password: str, db: Session = Depends(get_db)):
    """
    技师登录（姓名 + 密码）
    返回：{ "token": staff_id, "staff": {...} }
    """
    staff = db.query(StaffMember).filter(
        StaffMember.name == name,
        StaffMember.is_active == 1
    ).first()

    if not staff:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="技师不存在或已禁用"
        )

    if not staff.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="密码未设置，请联系管理员初始化密码"
        )

    if not verify_password(password, staff.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="密码错误"
        )

    return {
        "token": staff.staff_id,
        "staff": StaffMemberModel.model_validate(staff)
    }


@router.get("/me")
def get_current_staff_info(current_staff: StaffMember = Depends(get_current_staff)):
    """获取当前登录技师信息"""
    return StaffMemberModel.model_validate(current_staff)


@router.put("/change-password")
def change_password(
    old_password: str,
    new_password: str,
    current_staff: StaffMember = Depends(get_current_staff),
    db: Session = Depends(get_db)
):
    """修改登录密码"""
    # 验证旧密码
    if not verify_password(old_password, current_staff.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="原密码错误"
        )

    # 更新新密码
    current_staff.password_hash = hash_password(new_password)
    db.commit()

    return {"message": "密码修改成功"}


# === 排班相关 ===
@router.get("/my-bookings")
def get_my_bookings(
    date: Optional[str] = None,  # YYYY-MM-DD 格式，不传则默认为今天
    current_staff: StaffMember = Depends(get_current_staff),
    db: Session = Depends(get_db)
):
    """
    获取我的排班
    返回指定日期的所有排班，按时间排序
    """
    if date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="日期格式错误，请使用 YYYY-MM-DD 格式"
            )
    else:
        target_date = datetime.now().date()

    start_of_day = datetime.combine(target_date, datetime.min.time())
    end_of_day = datetime.combine(target_date, datetime.max.time())

    bookings = db.query(Booking).filter(
        Booking.staff_name == current_staff.name,
        Booking.start_time >= start_of_day,
        Booking.start_time <= end_of_day,
        Booking.status != "cancelled"
    ).order_by(Booking.start_time).all()

    # 关联客户信息
    result = []
    for b in bookings:
        client = db.query(Client).filter(Client.client_id == b.client_id).first()
        result.append({
            "booking": b,
            "client_name": client.name if client else "未知",
            "client_phone": client.phone if client else "未知"
        })

    return result


@router.get("/bookings/{booking_id}")
def get_booking_detail(
    booking_id: str,
    current_staff: StaffMember = Depends(get_current_staff),
    db: Session = Depends(get_db)
):
    """获取单个排班详情（用于服务录入）"""
    booking = db.query(Booking).filter(
        Booking.booking_id == booking_id,
        Booking.staff_name == current_staff.name
    ).first()

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到该排班记录"
        )

    client = db.query(Client).filter(Client.client_id == booking.client_id).first()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到关联客户"
        )

    return {
        "booking": booking,
        "client": {
            "client_id": client.client_id,
            "name": client.name,
            "phone": client.phone,
            "times_card_balance": client.times_card_balance,
            "cash_card_balance": client.cash_card_balance
        }
    }


# === 服务记录相关 ===
@router.post("/records")
def create_service_record(
    client_id: str,
    service_name: str,
    symptoms: List[str],
    description: str,
    deduct_times: int = 0,
    deduct_cash: float = 0.0,
    notes: Optional[str] = None,
    current_staff: StaffMember = Depends(get_current_staff),
    db: Session = Depends(get_db)
):
    """
    提交服务记录（同时更新健康档案和扣费）
    """
    client = db.query(Client).filter(Client.client_id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="未找到该客户")

    # 验证余额
    if deduct_times > client.times_card_balance:
        raise HTTPException(
            status_code=400,
            detail=f"次卡余额不足（剩余{client.times_card_balance}次，需要{deduct_times}次）"
        )
    if deduct_cash > client.cash_card_balance:
        raise HTTPException(
            status_code=400,
            detail=f"储值卡余额不足（剩余{client.cash_card_balance}元，需要{deduct_cash}元）"
        )

    # 创建健康记录
    record = HealthRecord(
        client_id=client_id,
        symptoms=symptoms,
        description=description,
        treatment_provided=service_name,
        deduct_times=deduct_times,
        deduct_cash=deduct_cash,
        notes=notes
    )
    db.add(record)

    # 扣减余额
    if deduct_times > 0:
        client.times_card_balance -= deduct_times
    if deduct_cash > 0:
        client.cash_card_balance -= deduct_cash
        # 记录交易流水
        transaction = Transaction(
            client_id=client_id,
            amount=-deduct_cash,
            transaction_type="payment",
            payment_method="member_card",
            notes=f"服务扣费：{service_name} - 技师{current_staff.name}"
        )
        db.add(transaction)

    db.commit()
    db.refresh(record)

    return {"message": "服务记录提交成功", "record_id": record.record_id}


@router.get("/my-records")
def get_my_records(
    start_date: Optional[str] = None,  # YYYY-MM-DD
    end_date: Optional[str] = None,
    limit: int = 50,
    current_staff: StaffMember = Depends(get_current_staff),
    db: Session = Depends(get_db)
):
    """
    获取我的服务历史记录
    """
    query = db.query(HealthRecord, Client.name.label("client_name")).join(
        Client, HealthRecord.client_id == Client.client_id
    ).filter(
        HealthRecord.treatment_provided.like(f"%{current_staff.name}%") |
        (HealthRecord.deduct_times > 0) | (HealthRecord.deduct_cash > 0)
    )

    if start_date:
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
            query = query.filter(HealthRecord.date >= datetime.combine(start, datetime.min.time()))
        except ValueError:
            raise HTTPException(status_code=400, detail="开始日期格式错误")

    if end_date:
        try:
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
            query = query.filter(HealthRecord.date <= datetime.combine(end, datetime.max.time()))
        except ValueError:
            raise HTTPException(status_code=400, detail="结束日期格式错误")

    records = query.order_by(HealthRecord.date.desc()).limit(limit).all()

    return [
        {
            "record_id": r.record_id,
            "client_name": r.client_name,
            "date": r.date,
            "symptoms": r.symptoms,
            "description": r.description,
            "treatment_provided": r.treatment_provided,
            "deduct_times": r.deduct_times,
            "deduct_cash": r.deduct_cash
        }
        for r in records
    ]


# === 业绩统计相关 ===
@router.get("/my-performance")
def get_my_performance(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_staff: StaffMember = Depends(get_current_staff),
    db: Session = Depends(get_db)
):
    """
    获取个人业绩统计
    - 服务次数
    - 总业绩金额（扣除的次卡次数和储值金额）
    """
    # 默认统计本月
    if not start_date:
        start_date = datetime.now().replace(day=1).strftime("%Y-%m-%d")
    if not end_date:
        end_date = datetime.now().strftime("%Y-%m-%d")

    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式错误")

    # 统计该技师的服务记录
    records = db.query(HealthRecord).filter(
        (HealthRecord.deduct_times > 0) | (HealthRecord.deduct_cash > 0),
        HealthRecord.date >= datetime.combine(start, datetime.min.time()),
        HealthRecord.date <= datetime.combine(end, datetime.max.time())
    ).all()

    total_deduct_times = sum(r.deduct_times for r in records)
    total_deduct_cash = sum(r.deduct_cash for r in records)
    service_count = len(records)

    return {
        "period": {
            "start": start_date,
            "end": end_date
        },
        "statistics": {
            "service_count": service_count,
            "total_deduct_times": total_deduct_times,
            "total_deduct_cash": total_deduct_cash
        }
    }
