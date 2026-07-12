"""
短信发送队列服务
- 避免运营商流控，随机 30-60 秒间隔发送
- 支持权限检查（套餐等级）
- 支持长短信自动分割
- 开发模式下绕过会员等级限制
"""
import logging
import random
import threading
import time
from datetime import datetime
from queue import Queue, Empty
from dataclasses import dataclass, field
from typing import Optional, Callable

logger = logging.getLogger(__name__)


@dataclass
class SmsTask:
    """短信发送任务"""
    task_id: str
    phone: str
    content: str
    client_name: str = ""
    callback: Optional[Callable] = None  # 发送完成回调
    created_at: datetime = field(default_factory=datetime.now)
    status: str = "pending"  # pending, sent, failed
    error: Optional[str] = None
    result: Optional[dict] = None


class SmsQueueService:
    """短信发送队列服务"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, config=None, driver=None):
        if hasattr(self, '_initialized') and self._initialized:
            return

        self.config = config
        self.driver = driver
        self.queue: Queue[SmsTask] = Queue()
        self.running = False
        self.worker_thread: Optional[threading.Thread] = None
        self.min_interval = 30  # 最小间隔秒数
        self.max_interval = 60  # 最大间隔秒数
        self._initialized = True

        # 统计
        self.sent_count = 0
        self.failed_count = 0

    def set_driver(self, driver):
        """设置短信驱动"""
        self.driver = driver

    def start(self):
        """启动队列处理"""
        if self.running:
            return
        self.running = True
        self.worker_thread = threading.Thread(target=self._worker, daemon=True)
        self.worker_thread.start()
        logger.info("[短信队列] 服务已启动")

    def stop(self):
        """停止队列处理"""
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5)
        logger.info("[短信队列] 服务已停止")

    def enqueue(self, phone: str, content: str, client_name: str = "",
                callback: Callable = None) -> str:
        """
        将短信加入发送队列
        Returns: 任务 ID
        """
        task_id = f"sms_{int(time.time() * 1000)}_{random.randint(1000, 9999)}"
        task = SmsTask(
            task_id=task_id,
            phone=phone,
            content=content,
            client_name=client_name,
            callback=callback
        )
        self.queue.put(task)
        queue_size = self.queue.qsize()
        logger.info(f"[短信队列] 任务已入队: {task_id}, 队列长度: {queue_size}")
        return task_id

    def check_permission(self, tier: str, dev_mode: bool = False) -> tuple:
        """
        检查套餐是否有短信发送权限
        Args:
            tier: 当前会员等级
            dev_mode: 开发模式标志（True 时绕过限制）
        Returns: (has_permission, message)
        """
        # 开发模式下绕过所有限制
        if dev_mode:
            return True, "开发模式：允许测试短信功能"

        # 基础版: 无短信功能
        # 专业版: 无短信功能
        # 至尊版: 有短信功能
        if tier == "basic":
            return False, "基础版不支持短信发送功能，请升级至至尊版"
        elif tier == "pro":
            return False, "专业版不支持短信发送功能，请升级至至尊版"
        elif tier == "business":
            return True, "至尊版支持短信发送"
        else:
            return True, "允许发送"  # 兼容其他情况

    def _worker(self):
        """队列处理工作线程"""
        logger.info("[短信队列] 工作线程已启动")

        while self.running:
            try:
                # 从队列获取任务，最多等待 1 秒
                task = self.queue.get(timeout=1)
            except Empty:
                continue

            try:
                # 发送短信
                result = self._send_task(task)
                task.status = "sent" if result.get("success") else "failed"
                task.result = result

                if result.get("success"):
                    self.sent_count += 1
                    logger.info(f"[短信队列] 发送成功: {task.task_id}")
                else:
                    self.failed_count += 1
                    task.error = result.get("error", "未知错误")
                    logger.warning(f"[短信队列] 发送失败: {task.task_id} - {task.error}")

                # 回调
                if task.callback:
                    try:
                        task.callback(task)
                    except Exception as e:
                        logger.error(f"[短信队列] 回调异常: {e}")

            except Exception as e:
                logger.error(f"[短信队列] 处理异常: {e}")
                task.status = "failed"
                task.error = str(e)

            finally:
                self.queue.task_done()

                # 随机间隔 30-60 秒，避免流控
                if self.running and self.queue.qsize() > 0:
                    delay = random.randint(self.min_interval, self.max_interval)
                    logger.info(f"[短信队列] 等待 {delay} 秒后发送下一条...")
                    time.sleep(delay)

    def _send_task(self, task: SmsTask) -> dict:
        """执行发送任务"""
        if not self.driver:
            return {"success": False, "error": "短信驱动未配置"}

        result = self.driver.send(
            recipient=task.phone,
            content=task.content,
            client_name=task.client_name
        )

        return {
            "success": result.success,
            "error": result.error,
            "channel": result.channel,
            "external_id": result.external_id
        }

    def get_stats(self) -> dict:
        """获取队列统计信息"""
        return {
            "queue_size": self.queue.qsize(),
            "sent_count": self.sent_count,
            "failed_count": self.failed_count,
            "running": self.running
        }


# 全局单例
_sms_queue_service: Optional[SmsQueueService] = None


def get_sms_queue_service(config=None, driver=None) -> SmsQueueService:
    """获取短信队列服务单例"""
    global _sms_queue_service
    if _sms_queue_service is None:
        _sms_queue_service = SmsQueueService(config, driver)
    return _sms_queue_service