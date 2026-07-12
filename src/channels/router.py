"""
渠道路由器 — 支持 wechat_cli（个人微信 CLI）与 ml307a（短信猫）
"""
import logging
from config import AppConfig

logger = logging.getLogger(__name__)


class ChannelRouter:
    """渠道选择

    优先级（auto 模式）：
        wechat_cli -> ml307a -> 空（人工复制）
    """

    def __init__(self, config: AppConfig):
        self.config = config
        raw_channels = config.raw.get("channels", {}) if hasattr(config, 'raw') else {}
        self.wechat_cli_enabled = bool(raw_channels.get("wechat_cli", {}).get("enabled", False))
        self.ml307a_enabled = bool(raw_channels.get("ml307a", {}).get("enabled", False))

    def select(self, send_channel: str, client_phone: str = "",
               content: str = "") -> str:
        """
        选择发送渠道。
        Args:
            send_channel: 剧本指定的渠道 ("auto" / "wechat_cli" / "ml307a")
            client_phone: 客户手机号
            content: 消息内容
        Returns:
            渠道名称（空字符串表示无自动渠道）
        """
        # 显式指定渠道
        if send_channel == "wechat_cli":
            return "wechat_cli" if self.wechat_cli_enabled else ""
        if send_channel == "ml307a":
            return "ml307a" if self.ml307a_enabled else ""

        # auto：按优先级回退
        if self.wechat_cli_enabled:
            return "wechat_cli"
        if self.ml307a_enabled:
            return "ml307a"
        return ""

    def get_available_channels(self) -> list[str]:
        """返回当前已启用的渠道列表（按优先级排序）"""
        channels: list[str] = []
        if self.wechat_cli_enabled:
            channels.append("wechat_cli")
        if self.ml307a_enabled:
            channels.append("ml307a")
        return channels
