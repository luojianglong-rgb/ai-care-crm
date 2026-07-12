"""
客户生命周期状态机
状态流转：new → active → silent → churn_risk
任意状态再次到店 → active（回流）
"""
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func

from db_models import ClientLifecycle, Client, Booking

logger = logging.getLogger(__name__)

# 状态流转规则
VISIT_THRESHOLD_ACTIVE = 2       # 到店 >= 2 次 → active
DAYS_SILENT = 30                  # 30 天未到店 → silent
DAYS_CHURN_RISK = 60              # 60 天未到店 → churn_risk


class LifecycleManager:

    def ensure_lifecycle(self, db: Session, client_id: str) -> ClientLifecycle:
        """确保客户有 lifecycle 记录，没有则创建。"""
        lc = db.query(ClientLifecycle).filter(
            ClientLifecycle.client_id == client_id
        ).first()
        if not lc:
            lc = ClientLifecycle(client_id=client_id, current_status="new")
            db.add(lc)
            db.commit()
            db.refresh(lc)
        return lc

    def on_visit_completed(self, db: Session, client_id: str):
        """实时触发：客户完成到店服务时调用。"""
        lc = self.ensure_lifecycle(db, client_id)
        lc.visit_count += 1
        lc.last_visit_at = datetime.now()
        lc.updated_at = datetime.now()

        old_status = lc.current_status
        # 任意状态到店 → 评估是否升级为 active
        if lc.visit_count >= VISIT_THRESHOLD_ACTIVE:
            lc.current_status = "active"
        elif old_status in ("silent", "churn_risk"):
            # 沉默/流失预警客户回来了，直接回流到 active
            lc.current_status = "active"

        if lc.current_status != old_status:
            lc.status_changed_at = datetime.now()
            # 同步更新 Client 表冗余字段
            client = db.query(Client).filter(Client.client_id == client_id).first()
            if client:
                client.lifecycle_status = lc.current_status

        db.commit()
        if lc.current_status != old_status:
            logger.info(f"Lifecycle: {client_id} {old_status} -> {lc.current_status}")

    def daily_batch_update(self, db: Session) -> dict:
        """
        每日批量扫描全部客户，更新状态。
        返回 {"updated": int, "transitions": [...]}
        """
        now = datetime.now()
        all_lc = db.query(ClientLifecycle).all()
        updated = 0
        transitions = []

        for lc in all_lc:
            old_status = lc.current_status
            new_status = self._evaluate(lc, now)

            if new_status and new_status != old_status:
                lc.current_status = new_status
                lc.status_changed_at = now
                lc.updated_at = now
                # 同步 Client 表
                client = db.query(Client).filter(Client.client_id == lc.client_id).first()
                if client:
                    client.lifecycle_status = new_status
                updated += 1
                transitions.append({
                    "client_id": lc.client_id,
                    "from": old_status,
                    "to": new_status,
                })

        if updated > 0:
            db.commit()
        logger.info(f"Lifecycle daily update: {updated} transitions out of {len(all_lc)} clients")
        return {"updated": updated, "transitions": transitions}

    def _evaluate(self, lc: ClientLifecycle, now: datetime) -> str | None:
        """根据规则评估新状态，返回 None 表示无需变更。"""
        if not lc.last_visit_at:
            return None  # 从未到店，保持 new

        days_since = (now - lc.last_visit_at).days

        if lc.current_status == "new":
            if lc.visit_count >= VISIT_THRESHOLD_ACTIVE:
                return "active"
        elif lc.current_status == "active":
            if days_since >= DAYS_CHURN_RISK:
                return "churn_risk"
            elif days_since >= DAYS_SILENT:
                return "silent"
        elif lc.current_status == "silent":
            if days_since >= DAYS_CHURN_RISK:
                return "churn_risk"

        return None

    def init_all_clients(self, db: Session):
        """为所有还没有 lifecycle 记录的客户初始化。"""
        existing_ids = {r[0] for r in db.query(ClientLifecycle.client_id).all()}
        all_clients = db.query(Client.client_id).all()
        count = 0
        for (cid,) in all_clients:
            if cid not in existing_ids:
                db.add(ClientLifecycle(client_id=cid, current_status="new"))
                count += 1
        if count:
            db.commit()
            logger.info(f"Lifecycle init: created {count} records")

    def get_stats(self, db: Session) -> dict:
        """获取各状态客户数量。"""
        rows = db.query(
            ClientLifecycle.current_status,
            func.count(ClientLifecycle.id)
        ).group_by(ClientLifecycle.current_status).all()
        return {status: count for status, count in rows}
