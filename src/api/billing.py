from fastapi import APIRouter, HTTPException, Depends, Response
from sqlalchemy.orm import Session
from typing import List
from models import Transaction, TransactionCreate
from services.billing_service import BillingService
from database import get_db
from config import get_config
import io

router = APIRouter()

# ===== 导出功能（放在动态路由之前） =====

@router.get("/export/excel")
def export_transactions_excel(db: Session = Depends(get_db)):
    """导出交易记录为 Excel 文件（专业版功能）"""
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

    transactions = BillingService.get_all_transactions(db)

    # 创建 Excel 工作簿
    wb = Workbook()
    ws = wb.active
    ws.title = "交易记录"

    # 表头
    headers = ["交易 ID", "客户 ID", "交易类型", "金额", "现金金额", "次数", "支付方式", "备注", "交易时间"]
    ws.append(headers)

    # 数据行
    for tx in transactions:
        ws.append([
            tx.transaction_id,
            tx.client_id,
            tx.transaction_type,
            tx.amount,
            tx.cash_amount or 0,
            tx.times_count or 0,
            tx.payment_method,
            tx.notes or "",
            tx.date.strftime("%Y-%m-%d %H:%M") if tx.date else ""
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
        headers={"Content-Disposition": "attachment; filename=transactions_export.xlsx"}
    )


# ===== 交易管理路由 =====

@router.post("/", response_model=Transaction)
def create_transaction(transaction: TransactionCreate, db: Session = Depends(get_db)):
    return BillingService.create_transaction(db, transaction)

@router.get("/", response_model=List[Transaction])
def list_transactions(db: Session = Depends(get_db)):
    return BillingService.get_all_transactions(db)

@router.get("/client/{client_id}", response_model=List[Transaction])
def get_client_transactions(client_id: str, db: Session = Depends(get_db)):
    return BillingService.get_client_transactions(db, client_id)