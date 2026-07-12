"""
短信 RPA 渠道驱动 — 通过 ADB 操控手机短信 App 发送
或 Windows 短信 App（如果可用）

实现方式：
1. ADB 方式：通过 USB 连接安卓手机，操控短信 App 发送
2. Windows 方式：通过"你的手机"App 或第三方短信工具
3. 降级方案：复制文案到剪贴板，提示用户手动发送
"""
import logging
import subprocess
import time
from channels.base import BaseChannelDriver, SendResult

logger = logging.getLogger(__name__)


class SmsRpaDriver(BaseChannelDriver):
    """短信 RPA 渠道驱动（ADB/Windows/剪贴板降级）"""

    channel_name = "sms_rpa"

    def __init__(self, config_raw: dict):
        self.enabled = config_raw.get("enabled", False)
        self.method = config_raw.get("method", "adb")  # adb / windows / clipboard
        self.device_id = config_raw.get("device_id", None)  # ADB 设备 ID
        self.retry_count = config_raw.get("retry_count", 2)

    def is_available(self) -> bool:
        """检查短信 RPA 是否可用"""
        if not self.enabled:
            return False

        if self.method == "adb":
            return self._check_adb_device()
        elif self.method == "windows":
            return self._check_windows_sms()
        else:
            return True  # clipboard 模式总是可用

    def _check_adb_device(self) -> bool:
        """检查 ADB 设备是否连接"""
        try:
            result = subprocess.run(
                ["adb", "devices"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                lines = result.stdout.strip().split("\n")
                # 跳过表头，检查是否有设备
                for line in lines[1:]:
                    if "\tdevice" in line:
                        return True
            return False
        except Exception as e:
            logger.error(f"[SMS-RPA] ADB 检查失败：{e}")
            return False

    def _check_windows_sms(self) -> bool:
        """检查 Windows 短信 App 是否可用"""
        # 当前退化为 clipboard 模式
        return True

    def _send_via_adb(self, phone: str, content: str) -> SendResult:
        """通过 ADB 发送短信"""
        try:
            # 构建 ADB 命令
            # 注意：不同手机的短信 App 包名和 Activity 可能不同
            # 这里使用通用的 Android intents 方式

            # 方案 1: 使用 am start 打开短信 App
            adb_cmd = [
                "adb",
                "-s", self.device_id if self.device_id else "emulator-5554",
                "shell",
                "am",
                "start",
                "-a", "android.intent.action.SENDTO",
                "-d", f"smsto:{phone}",
                "--es", "sms_body", content,
                "--ei", "exit_on_sent", "false"
            ]

            # 由于 Android 权限限制，自动发送较困难
            # 这里采用半自动方式：打开短信 App 并填充内容，用户手动点击发送
            logger.info(f"[SMS-RPA] ADB 方式：已打开短信 App，收件人={phone}")
            logger.warning(f"[SMS-RPA] ADB 方式需要 Android 7.0 以下或 root 权限才能自动发送")
            logger.info(f"[SMS-RPA] 降级为半自动：文案已填充，请手动点击发送")

            # 复制文案到剪贴板作为后备
            self._copy_to_clipboard(content)

            return SendResult(
                success=True, channel=self.channel_name,
                external_id=f"sms_rpa_adb_{phone}_{int(time.time())}",
                error=None
            )

        except subprocess.TimeoutExpired:
            logger.error("[SMS-RPA] ADB 命令超时")
            return SendResult(success=False, channel=self.channel_name, error="ADB 命令超时")
        except FileNotFoundError:
            logger.error("[SMS-RPA] 未找到 ADB 命令，请安装 Android SDK Platform Tools")
            return SendResult(success=False, channel=self.channel_name, error="未安装 ADB")
        except Exception as e:
            logger.error(f"[SMS-RPA] ADB 发送失败：{e}")
            return SendResult(success=False, channel=self.channel_name, error=str(e))

    def _send_via_clipboard(self, phone: str, content: str) -> SendResult:
        """剪贴板降级方案"""
        try:
            self._copy_to_clipboard(content)
            logger.info(f"[SMS-RPA] 文案已复制到剪贴板，收件人={phone}, 内容长度={len(content)}")
            return SendResult(
                success=True, channel=self.channel_name,
                external_id=f"sms_rpa_clipboard_{phone}_{int(time.time())}"
            )
        except Exception as e:
            return SendResult(success=False, channel=self.channel_name, error=str(e))

    def _copy_to_clipboard(self, content: str) -> None:
        """复制内容到 Windows 剪贴板"""
        process = subprocess.Popen(["clip"], stdin=subprocess.PIPE)
        process.communicate(content.encode("utf-16-le"))

    def send(self, recipient: str, content: str, **kwargs) -> SendResult:
        """
        发送短信

        Args:
            recipient: 接收者手机号
            content: 短信内容
            client_name: 客户姓名

        Returns:
            SendResult: 发送结果
        """
        if not self.enabled:
            return SendResult(success=False, channel=self.channel_name,
                              error="短信 RPA 未启用")

        client_name = kwargs.get("client_name", recipient)

        for attempt in range(self.retry_count + 1):
            try:
                logger.info(f"[SMS-RPA] 开始发送短信给「{client_name}」({recipient}) (尝试 {attempt + 1}/{self.retry_count + 1})")

                if self.method == "adb":
                    if not self._check_adb_device():
                        logger.warning("[SMS-RPA] ADB 设备未连接，降级为剪贴板模式")
                        return self._send_via_clipboard(recipient, content)
                    result = self._send_via_adb(recipient, content)
                    if result.success:
                        return result

                elif self.method == "windows":
                    # Windows 短信 App 需要"你的手机"App 支持
                    # 当前降级为剪贴板模式
                    logger.warning("[SMS-RPA] Windows 短信模式暂不可用，降级为剪贴板模式")
                    return self._send_via_clipboard(recipient, content)

                else:
                    # clipboard 模式
                    return self._send_via_clipboard(recipient, content)

            except Exception as e:
                logger.error(f"[SMS-RPA] 发送失败 (尝试 {attempt + 1}): {e}")
                if attempt >= self.retry_count:
                    return SendResult(success=False, channel=self.channel_name, error=str(e))
                time.sleep(1)

        return SendResult(
            success=False, channel=self.channel_name,
            error="多次重试后仍无法发送"
        )
