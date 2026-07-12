"""
管理台认证 API
/api/v1/auth/*
"""
import uuid
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
import bcrypt
import jwt

from database import get_db
from db_models import AdminUser
from config import get_config

router = APIRouter()

# JWT 配置（本地部署，密钥固定即可）
JWT_SECRET = "ai-care-crm-local-jwt-secret-2026"
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 24


# ── 请求/响应模型 ────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    user: dict


class AdminCreate(BaseModel):
    username: str
    password: str
    display_name: str = ""


class AdminUpdate(BaseModel):
    display_name: Optional[str] = None
    password: Optional[str] = None


class AdminOut(BaseModel):
    id: str
    username: str
    display_name: str
    is_active: int
    created_at: Optional[str] = None


# ── 工具函数 ─────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


def create_token(user_id: str, username: str) -> str:
    payload = {
        "sub": user_id,
        "username": username,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRE_HOURS),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "登录已过期，请重新登录")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "无效的认证令牌")


def get_current_admin(request: Request, db: Session = Depends(get_db)) -> AdminUser:
    """从请求头中提取并验证 JWT，返回当前管理员。"""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(401, "未登录")
    token = auth_header[7:]
    payload = decode_token(token)
    user = db.query(AdminUser).filter(
        AdminUser.id == payload["sub"],
        AdminUser.is_active == 1,
    ).first()
    if not user:
        raise HTTPException(401, "账号不存在或已停用")
    return user


# ── API 端点 ──────────────────────────────────────────────────────

@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    """管理台登录。"""
    user = db.query(AdminUser).filter(
        AdminUser.username == req.username,
        AdminUser.is_active == 1,
    ).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(401, "用户名或密码错误")
    token = create_token(user.id, user.username)
    return LoginResponse(
        token=token,
        user={"id": user.id, "username": user.username, "display_name": user.display_name},
    )


@router.get("/me")
def get_me(admin: AdminUser = Depends(get_current_admin)):
    """获取当前登录管理员信息。"""
    return {"id": admin.id, "username": admin.username, "display_name": admin.display_name}


@router.get("/admins", response_model=list[AdminOut])
def list_admins(db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    """获取所有管理员列表。"""
    admins = db.query(AdminUser).filter(AdminUser.is_active == 1).all()
    return [
        AdminOut(
            id=a.id, username=a.username, display_name=a.display_name or "",
            is_active=a.is_active, created_at=a.created_at.isoformat() if a.created_at else None,
        )
        for a in admins
    ]


@router.post("/admins", response_model=AdminOut)
def create_admin(req: AdminCreate, db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    """新增管理员。"""
    if db.query(AdminUser).filter(AdminUser.username == req.username).first():
        raise HTTPException(400, "用户名已存在")
    # 套餐配额校验：复用 max_staff（管理员视作员工的一类）
    config = get_config()
    if not config.server.dev_mode:
        quota = config.get_quota()
        if quota.max_staff > 0:
            current_count = db.query(func.count(AdminUser.id)).filter(
                AdminUser.is_active == 1
            ).scalar() or 0
            if current_count >= quota.max_staff:
                raise HTTPException(
                    status_code=403,
                    detail=f"管理员数量已达套餐上限（{current_count}/{quota.max_staff}），请激活正式版"
                )
    new_admin = AdminUser(
        id=str(uuid.uuid4()),
        username=req.username,
        password_hash=hash_password(req.password),
        display_name=req.display_name,
    )
    db.add(new_admin)
    db.commit()
    db.refresh(new_admin)
    return AdminOut(
        id=new_admin.id, username=new_admin.username,
        display_name=new_admin.display_name or "", is_active=new_admin.is_active,
        created_at=new_admin.created_at.isoformat() if new_admin.created_at else None,
    )


@router.put("/admins/{admin_id}", response_model=AdminOut)
def update_admin(admin_id: str, req: AdminUpdate, db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    """修改管理员信息（名称/密码）。"""
    target = db.query(AdminUser).filter(AdminUser.id == admin_id, AdminUser.is_active == 1).first()
    if not target:
        raise HTTPException(404, "管理员不存在")
    if req.display_name is not None:
        target.display_name = req.display_name
    if req.password:
        target.password_hash = hash_password(req.password)
    db.commit()
    db.refresh(target)
    return AdminOut(
        id=target.id, username=target.username,
        display_name=target.display_name or "", is_active=target.is_active,
        created_at=target.created_at.isoformat() if target.created_at else None,
    )


@router.delete("/admins/{admin_id}")
def delete_admin(admin_id: str, db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    """删除管理员（不能删除自己）。"""
    if admin_id == admin.id:
        raise HTTPException(400, "不能删除当前登录的管理员账号")
    target = db.query(AdminUser).filter(AdminUser.id == admin_id).first()
    if not target:
        raise HTTPException(404, "管理员不存在")
    target.is_active = 0
    db.commit()
    return {"success": True}
