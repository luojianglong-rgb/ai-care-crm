from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
import bcrypt
from database import get_db
from db_models import ServiceItem as DBServiceItem, StaffMember as DBStaffMember
from models import ServiceItemCreate, ServiceItemModel, ServiceItemUpdate, StaffMemberCreate, StaffMemberModel, StaffMemberUpdate
from config import get_config

router = APIRouter()

def hash_password(password: str) -> str:
    """密码加密"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

# --- 服务项目 API ---
@router.get("/", response_model=List[ServiceItemModel])
def get_services(db: Session = Depends(get_db)):
    return db.query(DBServiceItem).filter(DBServiceItem.is_active == 1).all()

@router.post("/", response_model=ServiceItemModel)
def create_service(item: ServiceItemCreate, db: Session = Depends(get_db)):
    db_item = DBServiceItem(**item.model_dump())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@router.put("/{item_id}", response_model=ServiceItemModel)
def update_service(item_id: str, item_update: ServiceItemUpdate, db: Session = Depends(get_db)):
    db_item = db.query(DBServiceItem).filter(DBServiceItem.item_id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="未找到服务项目")
    
    update_data = item_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_item, key, value)
        
    db.commit()
    db.refresh(db_item)
    return db_item

@router.delete("/{item_id}")
def delete_service(item_id: str, db: Session = Depends(get_db)):
    db_item = db.query(DBServiceItem).filter(DBServiceItem.item_id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="未找到服务项目")
    db_item.is_active = 0
    db.commit()
    return {"success": True}

# --- 员工技师 API ---
@router.get("/staff/", response_model=List[StaffMemberModel])
def get_staff(db: Session = Depends(get_db)):
    return db.query(DBStaffMember).filter(DBStaffMember.is_active == 1).all()

@router.post("/staff/", response_model=StaffMemberModel)
def create_staff(staff: StaffMemberCreate, db: Session = Depends(get_db)):
    # 套餐配额校验：基础版员工上限
    config = get_config()
    if not config.server.dev_mode:
        quota = config.get_quota()
        if quota.max_staff > 0:
            current_count = db.query(func.count(DBStaffMember.staff_id)).filter(
                DBStaffMember.is_active == 1
            ).scalar() or 0
            if current_count >= quota.max_staff:
                raise HTTPException(
                    status_code=403,
                    detail=f"员工数量已达套餐上限（{current_count}/{quota.max_staff}），请激活正式版"
                )

    staff_data = staff.model_dump()
    # 处理密码加密
    password = staff_data.pop('password', None)
    if password:
        staff_data['password_hash'] = hash_password(password)

    db_staff = DBStaffMember(**staff_data)
    db.add(db_staff)
    db.commit()
    db.refresh(db_staff)
    return db_staff

@router.put("/staff/{staff_id}", response_model=StaffMemberModel)
def update_staff(staff_id: str, staff_update: StaffMemberUpdate, db: Session = Depends(get_db)):
    db_staff = db.query(DBStaffMember).filter(DBStaffMember.staff_id == staff_id).first()
    if not db_staff:
        raise HTTPException(status_code=404, detail="未找到员工")

    update_data = staff_update.model_dump(exclude_unset=True)
    # 处理密码加密
    password = update_data.pop('password', None)
    if password:
        update_data['password_hash'] = hash_password(password)

    for key, value in update_data.items():
        setattr(db_staff, key, value)

    db.commit()
    db.refresh(db_staff)
    return db_staff

@router.delete("/staff/{staff_id}")
def delete_staff(staff_id: str, db: Session = Depends(get_db)):
    db_staff = db.query(DBStaffMember).filter(DBStaffMember.staff_id == staff_id).first()
    if not db_staff:
        raise HTTPException(status_code=404, detail="未找到员工")
    db_staff.is_active = 0
    db.commit()
    return {"success": True}