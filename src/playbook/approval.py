"""
智能审批处理
三种模式：auto（全自动）/ sampling（抽检）/ manual（逐条审批）
"""
import random
from sqlalchemy.orm import Session

from db_models import CampaignTask, Playbook


class ApprovalManager:

    def process_batch(self, db: Session, tasks: list[CampaignTask], playbook: Playbook):
        """根据剧本的审批模式处理一批任务。"""
        mode = playbook.approval_mode or "auto"

        if mode == "auto":
            for t in tasks:
                t.status = "queued"
                t.approval_mode = "auto"

        elif mode == "sampling":
            rate = playbook.sampling_rate or 0.1
            sample_size = max(1, int(len(tasks) * rate))
            sampled = set(random.sample(range(len(tasks)), min(sample_size, len(tasks))))
            for i, t in enumerate(tasks):
                t.approval_mode = "sampling"
                if i in sampled:
                    t.status = "pending_approval"
                    t.is_sampled = 1
                else:
                    t.status = "queued"

        elif mode == "manual":
            for t in tasks:
                t.status = "pending_approval"
                t.approval_mode = "manual"

        db.commit()

    def approve(self, db: Session, task_id: str) -> bool:
        """审批通过单条任务。"""
        task = db.query(CampaignTask).filter(CampaignTask.id == task_id).first()
        if not task or task.status != "pending_approval":
            return False
        task.status = "queued"
        db.commit()
        return True

    def approve_batch(self, db: Session, playbook_id: str) -> int:
        """一键批准某剧本下所有待审批任务。返回审批数量。"""
        count = db.query(CampaignTask).filter(
            CampaignTask.playbook_id == playbook_id,
            CampaignTask.status == "pending_approval",
        ).update({"status": "queued"})
        db.commit()
        return count

    def reject(self, db: Session, task_id: str, reason: str = "") -> bool:
        """驳回任务。"""
        task = db.query(CampaignTask).filter(CampaignTask.id == task_id).first()
        if not task or task.status != "pending_approval":
            return False
        task.status = "rejected"
        task.error_message = reason or None
        db.commit()
        return True
