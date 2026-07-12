from sqlalchemy.orm import Session
from db_models import Client, HealthRecord as DBHealthRecord, Transaction as DBTransaction
from models import ClientCreate, ClientUpdate, HealthRecord as PydanticHealthRecord, WalletAction, HealthRecordUpdate

class ClientService:
    @staticmethod
    def create_client(db: Session, client_in: ClientCreate) -> Client:
        db_client = Client(**client_in.model_dump())
        db.add(db_client)
        db.commit()
        db.refresh(db_client)
        return db_client

    @staticmethod
    def update_wallet(db: Session, client_id: str, action: WalletAction):
        db_client = db.query(Client).filter(Client.client_id == client_id).first()
        if not db_client:
            return None

        if action.action_type == "times":
            # 次卡充值：增加次卡余额
            db_client.times_card_balance += int(action.amount)
            # 记录交易流水 - 次卡充值
            db_tx = DBTransaction(
                client_id=client_id,
                amount=int(action.amount),  # 次数
                transaction_type="times_recharge",
                payment_method="member_card",
                times_count=int(action.amount),  # 充值的次数
                cash_amount=action.cash_amount or 0,  # 实际收款金额
                notes=action.notes or f"次卡充值{int(action.amount)}次，实收¥{action.cash_amount or 0}元"
            )
        elif action.action_type == "cash":
            # 现金充值：增加现金余额
            db_client.cash_card_balance += action.amount
            # 记录交易流水 - 现金充值
            db_tx = DBTransaction(
                client_id=client_id,
                amount=action.amount,  # 金额
                transaction_type="cash_recharge",
                payment_method="member_card",
                times_count=0,
                cash_amount=action.amount,  # 实际收款金额
                notes=action.notes or f"现金充值¥{action.amount}元"
            )

        db.add(db_tx)
        db.commit()
        db.refresh(db_client)
        return db_client

    @staticmethod
    def get_all_clients(db: Session):
        return db.query(Client).all()

    @staticmethod
    def get_client(db: Session, client_id: str):
        return db.query(Client).filter(Client.client_id == client_id).first()

    @staticmethod
    def update_client(db: Session, client_id: str, client_in: ClientUpdate):
        db_client = db.query(Client).filter(Client.client_id == client_id).first()
        if not db_client:
            return None
        
        update_data = client_in.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_client, key, value)
            
        db.commit()
        db.refresh(db_client)
        return db_client

    @staticmethod
    def add_health_record(db: Session, client_id: str, record: PydanticHealthRecord):
        db_client = db.query(Client).filter(Client.client_id == client_id).first()
        if not db_client:
            return None
            
        db_record = DBHealthRecord(
            client_id=client_id,
            symptoms=record.symptoms,
            description=record.description,
            treatment_provided=record.treatment_provided,
            deduct_times=record.deduct_times,
            deduct_cash=record.deduct_cash,
            notes=record.notes
        )
        db.add(db_record)
        
        # 处理扣减逻辑
        if record.deduct_times > 0:
            db_client.times_card_balance -= record.deduct_times
            
        if record.deduct_cash > 0:
            db_client.cash_card_balance -= record.deduct_cash
            db_tx = DBTransaction(
                client_id=client_id,
                amount=-record.deduct_cash,
                transaction_type="payment",
                payment_method="member_card",
                notes=f"调理项目扣费: {record.treatment_provided}"
            )
            db.add(db_tx)
            
        db.commit()
        db.refresh(db_record)
        return db_record

    @staticmethod
    def update_health_record(db: Session, record_id: str, record_update: HealthRecordUpdate):
        db_record = db.query(DBHealthRecord).filter(DBHealthRecord.record_id == record_id).first()
        if not db_record:
            return None
        
        update_data = record_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_record, key, value)
            
        db.commit()
        db.refresh(db_record)
        return db_record

    @staticmethod
    def delete_client(db: Session, client_id: str):
        db_client = db.query(Client).filter(Client.client_id == client_id).first()
        if db_client:
            db.delete(db_client)
            db.commit()
            return True
        return False