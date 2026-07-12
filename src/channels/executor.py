"""
发送执行器 — 轮询已审批的营销任务，通过渠道驱动执行发送
由 APScheduler 定时调用，或手动触发单条发送。
"""
import logging
import random
import time
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from config import AppConfig
from db_models import CampaignTask, Client
from channels.base import BaseChannelDriver, SendResult
from channels.router import ChannelRouter
from channels.safety import SendSafetyChecker

logger = logging.getLogger(__name__)


class SendExecutor:
    """营销任务发送执行器"""

    def __init__(self, config: AppConfig, drivers: dict[str, BaseChannelDriver]):
        """
        Args:
            config: 系统配置
            drivers: 渠道名 → 驱动实例 的映射 {"sms_api": SmsApiDriver(), ...}
        """
        self.config = config
        self.drivers = drivers
        self.router = ChannelRouter(config)
        self.delay_min = config.playbook.send_delay_min  # 秒
        self.delay_max = config.playbook.send_delay_max
        # 发送安全检查器
        self.safety_checker = SendSafetyChecker(config)
        # 异常暂停状态
        self.paused_until = None  # 暂停到某个时间点

    def send_single(self, db: Session, task_id: str) -> SendResult:
        """手动发送单条任务"""
        task = db.query(CampaignTask).filter(CampaignTask.id == task_id).first()
        if not task:
            return SendResult(success=False, channel="unknown", error="任务不存在")
        if task.status not in ("queued", "approved"):
            return SendResult(success=False, channel="unknown", error=f"任务状态不允许发送: {task.status}")

        client = db.query(Client).filter(Client.client_id == task.client_id).first()
        if not client:
            task.status = "failed"
            task.error_message = "客户不存在"
            db.commit()
            return SendResult(success=False, channel="unknown", error="客户不存在")

        return self._execute_send(db, task, client)

    def execute_batch(self, db: Session, max_count: int = 20) -> dict:
        """
        批量执行已排队的任务（由定时调度调用）。
        只发送 status='queued' 且 scheduled_at <= now 的任务。
        """
        # 检查是否处于异常暂停状态
        if self.paused_until and datetime.now() < self.paused_until:
            logger.warning(f"[发送] 当前处于异常暂停状态，暂停至 {self.paused_until}")
            return {"sent": 0, "failed": 0, "total": 0, "paused": True}
        self.paused_until = None

        # 检查每日发送上限
        if self.safety_checker.check_daily_limit(db, datetime.now()):
            logger.warning("[发送] 达到每日发送上限，停止发送")
            return {"sent": 0, "failed": 0, "total": 0, "daily_limit_reached": True}

        now = datetime.now()
        tasks = db.query(CampaignTask).filter(
            CampaignTask.status == "queued",
            CampaignTask.scheduled_at <= now,
        ).order_by(CampaignTask.scheduled_at).limit(max_count).all()

        sent = 0
        failed = 0
        consecutive_failures = 0

        for task in tasks:
            client = db.query(Client).filter(Client.client_id == task.client_id).first()
            if not client:
                task.status = "failed"
                task.error_message = "客户不存在"
                db.commit()
                failed += 1
                continue

            # 黑名单检查
            if self.safety_checker.is_client_in_blacklist(client):
                logger.info(f"[发送] 跳过黑名单客户：{client.name}")
                task.status = "failed"
                task.error_message = "客户在黑名单中"
                db.commit()
                continue

            # 敏感词检查
            is_sensitive, reason = self.safety_checker.check_content_sensitivity(task.generated_content or "")
            if is_sensitive:
                logger.warning(f"[发送] 跳过敏感内容：{reason}")
                task.status = "failed"
                task.error_message = f"内容敏感：{reason}"
                db.commit()
                continue

            result = self._execute_send(db, task, client)
            if result.success:
                sent += 1
                consecutive_failures = 0  # 重置连续失败计数
            else:
                failed += 1
                consecutive_failures += 1

            # 检查连续失败
            if consecutive_failures >= self.safety_checker.consecutive_failure_threshold:
                pause_minutes = 30
                self.paused_until = datetime.now() + timedelta(minutes=pause_minutes)
                logger.error(f"[发送] 连续失败 {consecutive_failures} 次，暂停发送 {pause_minutes} 分钟")
                break

            # 模拟人工节奏：随机间隔
            if self.delay_min > 0 and self.delay_max > 0:
                delay = random.uniform(self.delay_min, self.delay_max)
                time.sleep(delay)

        if sent + failed > 0:
            logger.info(f"[发送] 本轮执行 {sent + failed} 条: 成功 {sent}, 失败 {failed}")
        return {"sent": sent, "failed": failed, "total": sent + failed}

    def _execute_send(self, db: Session, task: CampaignTask, client: Client) -> SendResult:
        """执行单条发送"""
        # 路由选择渠道
        channel = self.router.select(
            send_channel=task.send_channel or "auto",
            client_phone=client.phone or "",
            content=task.generated_content or "",
        )

        driver = self.drivers.get(channel)

        # 如果首选渠道不可用，尝试降级到其他可用渠道
        if not driver or not driver.is_available():
            logger.warning(f"[发送] 首选渠道 {channel} 不可用，尝试其他渠道")
            fallback_channel = self._find_fallback_channel()
            if fallback_channel:
                logger.info(f"[发送] 降级到渠道 {fallback_channel}")
                channel = fallback_channel
                driver = self.drivers.get(channel)
            else:
                task.status = "failed"
                task.error_message = f"渠道 {channel} 不可用且无其他可用渠道"
                task.send_channel = channel
                db.commit()
                return SendResult(success=False, channel=channel, error=f"渠道 {channel} 不可用且无其他可用渠道")

        if not driver:
            task.status = "failed"
            task.error_message = f"渠道 {channel} 未配置驱动"
            task.send_channel = channel
            db.commit()
            return SendResult(success=False, channel=channel, error=f"渠道 {channel} 未配置")

        if not driver.is_available():
            task.status = "failed"
            task.error_message = f"渠道 {channel} 当前不可用"
            task.send_channel = channel
            db.commit()
            return SendResult(success=False, channel=channel, error=f"渠道 {channel} 不可用")

        # 执行发送
        try:
            result = driver.send(
                recipient=client.phone or "",
                content=task.generated_content or "",
                client_name=client.name,
            )
        except Exception as e:
            logger.error(f"[发送] 渠道 {channel} 异常: {e}")
            result = SendResult(success=False, channel=channel, error=str(e))

        # 更新任务状态
        task.send_channel = channel
        if result.success:
            task.status = "sent"
            task.sent_at = datetime.now()
            task.error_message = None
        else:
            task.status = "failed"
            task.error_message = result.error
        db.commit()

        return result

    def _find_fallback_channel(self) -> str:
        """找到一个可用的备用渠道（按 wechat_cli -> ml307a 顺序回退）"""
        for name in ("wechat_cli", "ml307a"):
            driver = self.drivers.get(name)
            if driver and driver.is_available():
                return name
        return ""
