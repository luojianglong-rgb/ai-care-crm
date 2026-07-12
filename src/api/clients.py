from fastapi import APIRouter, HTTPException, Depends, Response
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from models import ClientProfile, ClientCreate, ClientUpdate, HealthRecord, WalletAction, HealthRecordUpdate
from services.client_service import ClientService
from database import get_db
from config import get_config
from db_models import Client as DBClient
import io

router = APIRouter()

# ===== 导出功能（放在动态路由之前） =====

@router.get("/export/excel")
def export_clients_excel(db: Session = Depends(get_db)):
    """导出客户档案为 Excel 文件（专业版功能）"""
    config = get_config()
    # 版本控制：基础版不支持导出（开发模式绕过）
    if not config.server.dev_mode and config.current_tier == "basic":
        raise HTTPException(
            status_code=403,
            detail="数据导出为专业版功能，请激活正式版。激活后可无限导出客户档案和交易记录。"
        )

    try:
        import openpyxl
        from openpyxl import Workbook
    except ImportError:
        raise HTTPException(status_code=500, detail="请安装 openpyxl: pip install openpyxl")

    clients = ClientService.get_all_clients(db)

    # 创建 Excel 工作簿
    wb = Workbook()
    ws = wb.active
    ws.title = "客户档案"

    # 表头
    headers = ["客户 ID", "姓名", "手机号", "性别", "年龄段", "出生年月", "消费偏好", "次卡余额", "储值余额", "创建时间"]
    ws.append(headers)

    # 数据行
    for client in clients:
        ws.append([
            client.client_id,
            client.name,
            client.phone,
            client.gender,
            client.age_group,
            client.birth_date or "",
            ", ".join(client.preferences) if client.preferences else "",
            client.times_card_balance,
            client.cash_card_balance,
            client.created_at.strftime("%Y-%m-%d %H:%M") if client.created_at else ""
        ])

    # 调整列宽
    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = min(max_length + 2, 50)
        ws.column_dimensions[column].width = adjusted_width

    # 保存到字节流
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    return Response(
        content=output.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=clients_export.xlsx"}
    )


# ===== 客户管理路由 =====

@router.put("/{client_id}/records/{record_id}", response_model=HealthRecord)
def update_health_record(client_id: str, record_id: str, record_update: HealthRecordUpdate, db: Session = Depends(get_db)):
    updated_record = ClientService.update_health_record(db, record_id, record_update)
    if not updated_record:
        raise HTTPException(status_code=404, detail="未找到该健康档案记录")
    return updated_record

@router.post("/{client_id}/wallet", response_model=ClientProfile)
def update_wallet(client_id: str, action: WalletAction, db: Session = Depends(get_db)):
    client = ClientService.update_wallet(db, client_id, action)
    if not client:
        raise HTTPException(status_code=404, detail="未找到该客户")
    return client

@router.post("/", response_model=ClientProfile)
def create_client(client: ClientCreate, db: Session = Depends(get_db)):
    # 套餐配额校验：基础版客户上限
    config = get_config()
    if not config.server.dev_mode:
        quota = config.get_quota()
        if quota.max_clients > 0:
            current_count = db.query(func.count(DBClient.client_id)).scalar() or 0
            if current_count >= quota.max_clients:
                raise HTTPException(
                    status_code=403,
                    detail=f"客户数量已达套餐上限（{current_count}/{quota.max_clients}），请激活正式版"
                )
    return ClientService.create_client(db, client)

@router.get("/", response_model=List[ClientProfile])
def list_clients(db: Session = Depends(get_db)):
    return ClientService.get_all_clients(db)

@router.get("/{client_id}", response_model=ClientProfile)
def get_client(client_id: str, db: Session = Depends(get_db)):
    client = ClientService.get_client(db, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="未找到该客户")
    return client

@router.put("/{client_id}", response_model=ClientProfile)
def update_client(client_id: str, client_update: ClientUpdate, db: Session = Depends(get_db)):
    client = ClientService.update_client(db, client_id, client_update)
    if not client:
        raise HTTPException(status_code=404, detail="未找到该客户")
    return client

@router.post("/{client_id}/records", response_model=HealthRecord)
def add_health_record(client_id: str, record: HealthRecord, db: Session = Depends(get_db)):
    new_record = ClientService.add_health_record(db, client_id, record)
    if not new_record:
        raise HTTPException(status_code=404, detail="未找到该客户，无法添加记录")
    return new_record

@router.get("/{client_id}/records", response_model=List[HealthRecord])
def get_client_records(client_id: str, db: Session = Depends(get_db)):
    """获取客户的历史服务记录（按时间倒序）"""
    from db_models import HealthRecord as DBHealthRecord
    records = db.query(DBHealthRecord).filter(
        DBHealthRecord.client_id == client_id
    ).order_by(DBHealthRecord.date.desc()).all()
    return records

@router.delete("/{client_id}")
def delete_client(client_id: str, db: Session = Depends(get_db)):
    success = ClientService.delete_client(db, client_id)
    if not success:
        raise HTTPException(status_code=404, detail="未找到该客户")
    return {"message": "删除成功"}