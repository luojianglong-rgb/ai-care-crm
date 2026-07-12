"""
渠道驱动基类 — 所有渠道（短信猫/短信API）实现此接口
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class SendResult:
    success: bool
    channel: str                    # "ml307a" / "sms_api"
    timestamp: datetime = None
    error: Optional[str] = None
    external_id: Optional[str] = None  # 外部追踪ID（短信API的回执ID等）

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class BaseChannelDriver:
    """渠道驱动统一接口"""

    channel_name: str = "unknown"

    def send(self, recipient: str, content: str, **kwargs) -> SendResult:
        """
        发送消息。
        Args:
            recipient: 接收方标识（手机号 / 微信备注名）
            content: 纯文本消息内容
        Returns:
            SendResult
        """
        raise NotImplementedError

    def is_available(self) -> bool:
        """检查渠道是否可用（配置完整、设备在线等）。"""
        return False
