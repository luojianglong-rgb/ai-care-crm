from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List
from models import InventoryItem, InventoryItemCreate, InventoryItemUpdate, InventoryUsageCreate, InventoryUsageRecordModel, InventoryCategoryCreate, InventoryCategoryUpdate, InventoryCategoryModel
from services.inventory_service import InventoryService
from database import get_db
from db_models import InventoryCategory as DBInventoryCategory

router = APIRouter()

@router.get("/", response_model=List[InventoryItem])
def list_items(db: Session = Depends(get_db)):
    return InventoryService.get_all_items(db)

@router.post("/", response_model=InventoryItem)
def create_item(item: InventoryItemCreate, db: Session = Depends(get_db)):
    return InventoryService.create_item(db, item)

@router.put("/{item_id}", response_model=InventoryItem)
def update_item(item_id: str, item_update: InventoryItemUpdate, db: Session = Depends(get_db)):
    item = InventoryService.update_item(db, item_id, item_update)
    if not item:
        raise HTTPException(status_code=404, detail="未找到该库存项")
    return item

@router.delete("/{item_id}")
def delete_item(item_id: str, db: Session = Depends(get_db)):
    success = InventoryService.delete_item(db, item_id)
    if not success:
        raise HTTPException(status_code=404, detail="未找到该库存项")
    return {"message": "库存记录已删除"}

@router.post("/usage", response_model=InventoryUsageRecordModel)
def record_usage(usage: InventoryUsageCreate, db: Session = Depends(get_db)):
    record = InventoryService.record_usage(db, usage)
    if not record:
        raise HTTPException(status_code=400, detail="扣减失败，可能是库存不足或物品不存在")
    return record

@router.post("/return", response_model=InventoryUsageRecordModel)
def return_item(usage: InventoryUsageCreate, db: Session = Depends(get_db)):
    record = InventoryService.return_item(db, usage)
    if not record:
        raise HTTPException(status_code=400, detail="退还失败，可能是物品不存在")
    return record

@router.get("/usage/history", response_model=List[InventoryUsageRecordModel])
def get_usage_history(db: Session = Depends(get_db)):
    return InventoryService.get_usage_records(db)

# --- 耗材分类管理 API ---
@router.get("/categories", response_model=List[InventoryCategoryModel])
def get_categories(db: Session = Depends(get_db)):
    return db.query(DBInventoryCategory).filter(DBInventoryCategory.is_active == 1).all()

@router.post("/categories", response_model=InventoryCategoryModel)
def create_category(category: InventoryCategoryCreate, db: Session = Depends(get_db)):
    db_item = DBInventoryCategory(**category.model_dump())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@router.put("/categories/{category_id}", response_model=InventoryCategoryModel)
def update_category(category_id: str, category_update: InventoryCategoryUpdate, db: Session = Depends(get_db)):
    db_category = db.query(DBInventoryCategory).filter(DBInventoryCategory.category_id == category_id).first()
    if not db_category:
        raise HTTPException(status_code=404, detail="未找到该分类")

    update_data = category_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_category, key, value)

    db.commit()
    db.refresh(db_category)
    return db_category

@router.delete("/categories/{category_id}")
def delete_category(category_id: str, db: Session = Depends(get_db)):
    db_category = db.query(DBInventoryCategory).filter(DBInventoryCategory.category_id == category_id).first()
    if not db_category:
        raise HTTPException(status_code=404, detail="未找到该分类")

    db_category.is_active = 0
    db.commit()
    return {"message": "分类已禁用"}