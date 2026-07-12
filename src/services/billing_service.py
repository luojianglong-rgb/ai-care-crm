from sqlalchemy.orm import Session
from db_models import Transaction as DBTransaction
from models import TransactionCreate

class BillingService:
    @staticmethod
    def create_transaction(db: Session, transaction_in: TransactionCreate) -> DBTransaction:
        db_tx = DBTransaction(**transaction_in.model_dump())
        db.add(db_tx)
        db.commit()
        db.refresh(db_tx)
        return db_tx

    @staticmethod
    def get_all_transactions(db: Session):
        return db.query(DBTransaction).all()

    @staticmethod
    def get_client_transactions(db: Session, client_id: str):
        return db.query(DBTransaction).filter(DBTransaction.client_id == client_id).all()