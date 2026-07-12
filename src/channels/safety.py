"""
发送安全防护模块 — 黑名单、每日上限、异常检测
"""
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from db_models import CampaignTask, Client

logger = logging.getLogger(__name__)


class SendSafetyChecker:
    """发送安全检查器"""

    def __init__(self, config):
        self.config = config
        # 从配置读取安全参数
        self.daily_limit = config.raw.get("playbook", {}).get("daily_send_limit", 100)
        self.consecutive_failure_threshold = config.raw.get("playbook", {}).get("consecutive_failure_threshold", 5)
        self.auto_pause_enabled = config.raw.get("playbook", {}).get("auto_pause_enabled", True)

    def is_client_in_blacklist(self, client: Client) -> bool:
        """检查客户是否在黑名单中"""
        # 黑名单判断逻辑：
        # 1. 客户标记为 is_blacklist (需要在 Client 模型中添加)
        # 2. 手机号在黑名单列表中
        if hasattr(client, 'is_blacklist') and client.is_blacklist:
            return True

        # 从配置中读取黑名单手机号列表
        blacklist_phones = self.config.raw.get("playbook", {}).get("blacklist_phones", [])
        if client.phone in blacklist_phones:
            return True

        return False

    def check_daily_limit(self, db: Session, today: datetime) -> bool:
        """
        检查是否超过每日发送上限
        返回 True 表示已达到上限，应停止发送
        """
        today_start = today.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)

        count = db.query(CampaignTask).filter(
            CampaignTask.sent_at >= today_start,
            CampaignTask.sent_at < today_end,
            CampaignTask.status == "sent"
        ).count()

        if count >= self.daily_limit:
            logger.warning(f"[发送安全] 今日已发送 {count}/{self.daily_limit} 条，达到每日上限")
            return True

        logger.info(f"[发送安全] 今日已发送 {count}/{self.daily_limit} 条")
        return False

    def check_consecutive_failures(self, db: Session, channel: str, window_minutes: int = 30) -> tuple[bool, int]:
        """
        检查连续失败次数
        返回 (是否应暂停发送，连续失败次数)
        """
        now = datetime.now()
        window_start = now - timedelta(minutes=window_minutes)

        # 查询指定时间窗口内的失败记录
        failed_tasks = db.query(CampaignTask).filter(
            CampaignTask.status == "failed",
            CampaignTask.sent_at >= window_start,
            CampaignTask.send_channel == channel
        ).order_by(CampaignTask.sent_at.desc()).all()

        # 计算连续失败次数（从最近一条往前数，直到遇到成功的）
        consecutive_failures = 0
        for task in failed_tasks:
            consecutive_failures += 1

        if consecutive_failures >= self.consecutive_failure_threshold:
            logger.warning(f"[发送安全] {channel} 渠道在 {window_minutes} 分钟内失败 {consecutive_failures} 次，达到阈值")
            if self.auto_pause_enabled:
                return True, consecutive_failures

        return False, consecutive_failures

    def check_content_sensitivity(self, content: str) -> tuple[bool, str]:
        """
        检查内容是否包含敏感词
        返回 (是否敏感，原因)
        """
        sensitive_keywords = self.config.raw.get("playbook", {}).get("sensitive_keywords", [])

        for keyword in sensitive_keywords:
            if keyword.lower() in content.lower():
                return True, f"包含敏感词：{keyword}"

        return False, ""

    def log_send_result(self, db: Session, task: CampaignTask, result, client: Client):
        """记录发送结果用于分析"""
        if not result.success:
            logger.warning(f"[发送安全] 发送给 {client.name} 失败：{result.error}")
