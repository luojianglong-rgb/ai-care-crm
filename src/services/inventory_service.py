from sqlalchemy.orm import Session
from db_models import InventoryItem as DBInventoryItem, InventoryUsageRecord as DBUsageRecord
from models import InventoryItemCreate, InventoryItemUpdate, InventoryUsageCreate

class InventoryService:
    @staticmethod
    def create_item(db: Session, item_in: InventoryItemCreate) -> DBInventoryItem:
        db_item = DBInventoryItem(**item_in.model_dump())
        db.add(db_item)
        db.commit()
        db.refresh(db_item)
        return db_item

    @staticmethod
    def get_all_items(db: Session):
        return db.query(DBInventoryItem).all()

    @staticmethod
    def update_item(db: Session, item_id: str, item_in: InventoryItemUpdate):
        db_item = db.query(DBInventoryItem).filter(DBInventoryItem.item_id == item_id).first()
        if not db_item:
            return None
        
        update_data = item_in.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_item, key, value)
            
        db.commit()
        db.refresh(db_item)
        return db_item

    @staticmethod
    def delete_item(db: Session, item_id: str):
        db_item = db.query(DBInventoryItem).filter(DBInventoryItem.item_id == item_id).first()
        if db_item:
            db.delete(db_item)
            db.commit()
            return True
        return False

    @staticmethod
    def record_usage(db: Session, usage_in: InventoryUsageCreate):
        db_item = db.query(DBInventoryItem).filter(DBInventoryItem.item_id == usage_in.item_id).first()
        if not db_item or db_item.quantity < usage_in.quantity:
            return None
            
        # 扣减库存
        db_item.quantity -= usage_in.quantity
        
        # 增加领用记录
        db_record = DBUsageRecord(**usage_in.model_dump())
        db.add(db_record)
        
        db.commit()
        db.refresh(db_record)
        return db_record

    @staticmethod
    def return_item(db: Session, return_in: InventoryUsageCreate):
        db_item = db.query(DBInventoryItem).filter(DBInventoryItem.item_id == return_in.item_id).first()
        if not db_item:
            return None
            
        # 增加库存
        db_item.quantity += return_in.quantity
        
        # 增加退还记录，数量记为负数以区分
        record_data = return_in.model_dump()
        record_data['quantity'] = -return_in.quantity
        db_record = DBUsageRecord(**record_data)
        db.add(db_record)
        
        db.commit()
        db.refresh(db_record)
        return db_record

    @staticmethod
    def get_usage_records(db: Session):
        return db.query(DBUsageRecord).order_by(DBUsageRecord.usage_date.desc()).all()