"""
ML307A 4G Cat.1 短信猫驱动
移远通信 ML307A/合宙 Air780E 等基于 ML307A 的 USB 短信设备

支持设备：
- 合宙 Air780E (ML307A 方案)
- 移远 ML307A 开发板
- 其他基于 ML307A 的 USB 短信猫

硬件连接：USB 转串口（虚拟 COM 口），即插即用
"""
import logging
import time
from channels.base import BaseChannelDriver, SendResult

logger = logging.getLogger(__name__)

try:
    import serial
    import serial.tools.list_ports
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False
    logger.warning("pyserial 未安装，ML307A 短信猫功能不可用。请运行：pip install pyserial")


class ML307ADriver(BaseChannelDriver):
    """ML307A 4G 短信猫驱动（USB 成品盒子方案）

    短信编码支持：
    - 英文短信：文本模式 (IRA/GSM 7bit)
    - 中文短信：文本模式 + CSMP设置DCS=8 + UCS2编码内容

    发送中文短信的关键：
    1. AT+CMGF=1 (文本模式)
    2. AT+CSMP=17,167,0,8 (设置DCS=8表示UCS2编码)
    3. 内容转换为UTF-16-BE十六进制字符串
    """

    channel_name = "ml307a"

    # 设备能力标记 - ML307A 支持通过 CSMP 设置发送中文短信
    supports_chinese = True

    def __init__(self, config_raw: dict):
        self.enabled = config_raw.get("enabled", False)
        self.port = config_raw.get("port", None)  # 串口号，None 表示自动扫描
        self.baudrate = config_raw.get("baudrate", 115200)  # ML307A 默认波特率
        self.timeout = config_raw.get("timeout", 5)
        self.sim_pin = config_raw.get("sim_pin", "")
        self.carrier = config_raw.get("carrier", "auto")  # 运营商类型
        self.smsc = config_raw.get("smsc", "")  # 手动指定短信中心号码
        self.retry_count = config_raw.get("retry_count", 2)
        self._ser = None

    def is_available(self) -> bool:
        if not self.enabled:
            return False
        if not SERIAL_AVAILABLE:
            return False
        try:
            if not self._connect():
                return False
            response = self._send_command("AT", timeout=1)
            self._disconnect()
            return "OK" in response
        except Exception as e:
            logger.error(f"[ML307A] 检查失败：{e}")
            return False

    def _connect(self) -> bool:
        if self._ser and self._ser.is_open:
            return True
        try:
            port = self.port or self._scan_serial_port()
            if not port:
                logger.error("[ML307A] 未找到串口设备")
                return False
            logger.info(f"[ML307A] 连接串口：{port} @ {self.baudrate}")
            self._ser = serial.Serial(
                port=port,
                baudrate=self.baudrate,
                timeout=self.timeout,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                rtscts=False,
                xonxoff=False,
            )
            time.sleep(0.5)
            self._ser.reset_input_buffer()
            self._ser.reset_output_buffer()
            return True
        except Exception as e:
            logger.error(f"[ML307A] 连接失败：{e}")
            return False

    def _disconnect(self):
        if self._ser:
            try:
                if self._ser.is_open:
                    self._ser.close()
            except Exception:
                pass
            self._ser = None

    def _scan_serial_port(self) -> str:
        """自动扫描 ML307A 设备"""
        if not SERIAL_AVAILABLE:
            return None
        # ML307A/合宙/ASR 常见 VID/PID
        known_devices = [
            (0x2C7C, 0x0125),  # 合宙
            (0x2C7C, 0x0210),  # 移远
            (0x2C7C, None),    # 合宙其他设备
            (0x2ECC, None),    # ASR 芯片 (ML307A 兼容)
        ]
        ports = serial.tools.list_ports.comports()
        for port in ports:
            if port.vid is not None:
                for vid, pid in known_devices:
                    if port.vid == vid and (pid is None or port.pid == pid):
                        logger.info(f"[ML307A] 发现设备：{port.device}")
                        return port.device
        # 无匹配则返回第一个 USB 串口
        for port in ports:
            if "USB" in port.description.upper() or "CH340" in port.description.upper() or "ASR" in port.description.upper() or "Modem" in port.description.upper():
                return port.device
        return None

    def _send_command(self, cmd: str, timeout: float = 1.0) -> str:
        if not self._ser or not self._ser.is_open:
            return ""
        try:
            self._ser.write(f"{cmd.strip()}\r\n".encode('ascii'))
            self._ser.flush()
            time.sleep(timeout)
            return self._ser.read_all().decode('gbk', errors='ignore')
        except Exception as e:
            logger.error(f"[ML307A] AT 指令失败：{cmd} - {e}")
            return ""

    def _initialize(self) -> bool:
        """初始化 ML307A"""
        try:
            # 测试
            if "OK" not in self._send_command("AT", timeout=1):
                logger.error("[ML307A] 设备无响应")
                return False
            # 设置文本模式（英文短信）
            self._send_command("AT+CMGF=1", timeout=1)
            # 检查 SIM 卡
            response = self._send_command("AT+CPIN?", timeout=2)
            if "READY" not in response:
                if "SIM PIN" in response and self.sim_pin:
                    self._send_command(f"AT+CPIN={self.sim_pin}", timeout=2)
                else:
                    logger.error(f"[ML307A] SIM 卡未就绪：{response}")
                    return False
            # 信号强度
            response = self._send_command("AT+CSQ", timeout=1)
            if "+CSQ:" in response:
                csq = response.split(":")[1].strip().split(",")[0]
                logger.info(f"[ML307A] 信号强度：CSQ={csq}")
            # 检测运营商（用于日志记录）
            self._detect_carrier()
            return True
        except Exception as e:
            logger.error(f"[ML307A] 初始化失败：{e}")
            return False

    def _detect_carrier(self):
        """检测 SIM 卡运营商"""
        if self.carrier != "auto":
            logger.info(f"[ML307A] 配置运营商：{self.carrier}")
            return
        try:
            # 通过 IMSI 检测运营商
            response = self._send_command("AT+CIMI", timeout=2)
            imsi = response.strip().replace("OK", "").strip()
            if imsi:
                # IMSI 前5位是 MCC+MNC
                # 46000/46002/46007 = 中国移动
                # 46001/46006/46009 = 中国联通
                # 46003/46005/46011 = 中国电信
                mcc_mnc = imsi[:5]
                if mcc_mnc in ("46000", "46002", "46007", "46008"):
                    detected = "移动"
                elif mcc_mnc in ("46001", "46006", "46009"):
                    detected = "联通"
                elif mcc_mnc in ("46003", "46005", "46011", "46012"):
                    detected = "电信"
                else:
                    detected = "未知"
                logger.info(f"[ML307A] 检测运营商：{detected} (IMSI: {imsi[:10]}...)")
        except Exception as e:
            logger.debug(f"[ML307A] 运营商检测失败：{e}")

    def _to_ucs2_hex(self, text: str) -> str:
        """文本转 UCS2 十六进制"""
        return text.encode('utf-16-be').hex().upper()

    def _contains_chinese(self, text: str) -> bool:
        """检查是否包含中文"""
        for char in text:
            if '\u4e00' <= char <= '\u9fff':
                return True
        return False

    def _encode_pdu(self, phone: str, content: str) -> tuple:
        """
        编码 PDU 格式短信
        Returns: (pdu_length, pdu_string)
        """
        # 获取短信中心号码
        smsc_pdu = self._get_smsc()

        # 手机号转换：去掉+号，补F凑偶数，反转每两位
        phone_clean = phone.replace('+', '')
        if len(phone_clean) % 2 == 1:
            phone_clean += 'F'
        phone_swapped = ''
        for i in range(0, len(phone_clean), 2):
            phone_swapped += phone_clean[i+1] + phone_clean[i]
        phone_len = len(phone.replace('+', ''))

        # 内容转 UCS2
        content_hex = content.encode('utf-16-be').hex().upper()
        content_bytes = len(content.encode('utf-16-be'))  # 字节数，不是字符数

        # 构建 TPDU (SMS-SUBMIT)
        # 11: 首字节 (TP-VPF=00, 无有效期字段)
        # 00: TP-Message-Reference
        # 号号长度 + 91国际格式 + 号码
        # 00: TP-PID
        # 08: TP-DCS (UCS2 编码)
        # 内容长度(字节数) + 内容
        tpdu = f'1100{phone_len:02X}91{phone_swapped}0008{content_bytes:02X}{content_hex}'

        # 完整 PDU = SCA + TPDU
        pdu = smsc_pdu + tpdu

        # AT+CMGS 的长度 = TPDU 长度 / 2
        pdu_length = len(tpdu) // 2

        return pdu_length, pdu

    def _get_smsc(self) -> str:
        """获取短信中心号码并编码为 PDU 格式"""
        # 优先使用手动配置的短信中心
        if self.smsc:
            smsc = self.smsc.replace('+', '')
            logger.info(f"[ML307A] 使用配置的短信中心：{self.smsc}")
        else:
            # 自动获取
            try:
                response = self._send_command("AT+CSCA?", timeout=2)
                import re
                match = re.search(r'\+CSCA:\s*"(\+?\d+)"', response)
                if match:
                    smsc = match.group(1).replace('+', '')
                    logger.info(f"[ML307A] 自动获取短信中心：{match.group(1)}")
                else:
                    logger.warning("[ML307A] 未获取到短信中心，使用默认")
                    return "00"
            except Exception as e:
                logger.warning(f"[ML307A] 获取短信中心失败：{e}，使用默认")
                return "00"

        # 编码 SCA
        if len(smsc) % 2 == 1:
            smsc += 'F'
        smsc_swapped = ''
        for i in range(0, len(smsc), 2):
            smsc_swapped += smsc[i+1] + smsc[i]
        # 长度 = 类型(1) + 号码字节数
        smsc_len = (len(smsc) // 2) + 1
        return f'{smsc_len:02X}91{smsc_swapped}'

    def send(self, recipient: str, content: str, **kwargs) -> SendResult:
        client_name = kwargs.get("client_name", recipient)
        if not self.enabled:
            return SendResult(success=False, channel=self.channel_name, error="ML307A 未启用")
        if not SERIAL_AVAILABLE:
            return SendResult(success=False, channel=self.channel_name, error="pyserial 未安装")
        if not recipient or not content:
            return SendResult(success=False, channel=self.channel_name, error="收件人或内容为空")

        # 检查是否有中文
        has_chinese = self._contains_chinese(content)

        # 中文短信使用文本模式 + CSMP设置DCS=8 + UCS2编码
        if has_chinese:
            return self._send_chinese(recipient, content, client_name)

        # 英文短信使用文本模式（IRA/GSM 7bit）
        # GSM 编码下短信最大 160 字符
        max_len = 160

        # 长短信分割
        if len(content) > max_len:
            return self._send_long_sms(recipient, content, client_name)

        return self._send_single(recipient, content, client_name)

    def _send_single(self, recipient: str, content: str, client_name: str) -> SendResult:
        """发送单条短信（仅支持英文）"""
        for attempt in range(self.retry_count + 1):
            try:
                logger.info(f"[ML307A] 发送短信给「{client_name}」({recipient}) (尝试 {attempt + 1}/{self.retry_count + 1})")
                if not self._connect():
                    return SendResult(success=False, channel=self.channel_name, error="无法连接设备")

                # 使用文本模式发送英文
                self._send_command("AT+CMGF=1", timeout=1)
                self._send_command("AT+CSCS=\"GSM\"", timeout=1)
                self._send_command(f'AT+CMGS="{recipient}"', timeout=2)
                time.sleep(0.5)
                self._ser.write(f"{content}\x1A".encode('ascii'))

                self._ser.flush()
                time.sleep(3)
                response = self._ser.read_all().decode('gbk', errors='ignore')
                self._disconnect()

                if "+CMGS:" in response or "OK" in response:
                    logger.info(f"[ML307A] 短信发送成功：{client_name}")
                    return SendResult(success=True, channel=self.channel_name, external_id=f"ml307a_{recipient}_{int(time.time())}")
                return SendResult(success=False, channel=self.channel_name, error=f"发送失败：{response.strip()}")
            except Exception as e:
                logger.error(f"[ML307A] 发送异常：{e}")
                self._disconnect()
                if attempt >= self.retry_count:
                    return SendResult(success=False, channel=self.channel_name, error=str(e))
                time.sleep(2)
        return SendResult(success=False, channel=self.channel_name, error="多次重试失败")

    def _send_long_sms(self, recipient: str, content: str, client_name: str) -> SendResult:
        """发送长短信（分割为多条，仅支持英文）"""
        max_len = 153  # 长短信每条实际可发送字数
        segments = []
        for i in range(0, len(content), max_len):
            segments.append(content[i:i+max_len])

        total = len(segments)
        logger.info(f"[ML307A] 长短信分割为 {total} 条发送")

        success_count = 0
        for idx, segment in enumerate(segments):
            # 添加分段标识
            segment_content = f"({idx+1}/{total}){segment}"
            result = self._send_single(recipient, segment_content, client_name)
            if result.success:
                success_count += 1
            else:
                logger.warning(f"[ML307A] 第 {idx+1}/{total} 条发送失败")
            # 分段发送间隔
            if idx < total - 1:
                time.sleep(2)

        if success_count == total:
            return SendResult(success=True, channel=self.channel_name, external_id=f"ml307a_{recipient}_{int(time.time())}")
        elif success_count > 0:
            return SendResult(success=True, channel=self.channel_name, error=f"部分发送成功：{success_count}/{total}")
        return SendResult(success=False, channel=self.channel_name, error="长短信发送失败")

    def _send_chinese(self, recipient: str, content: str, client_name: str) -> SendResult:
        """发送中文短信（文本模式 + CSMP设置DCS=8 + UCS2编码）

        ML307A 发送中文短信的正确方法：
        1. AT+CMGF=1 (文本模式)
        2. AT+CSMP=17,167,0,8 (设置DCS=8表示UCS2编码)
        3. 内容转换为UTF-16-BE十六进制字符串
        4. 手机号保持原样，不需要转换
        """
        for attempt in range(self.retry_count + 1):
            try:
                logger.info(f"[ML307A] 发送中文短信给「{client_name}」({recipient}) (尝试 {attempt + 1}/{self.retry_count + 1})")
                if not self._connect():
                    return SendResult(success=False, channel=self.channel_name, error="无法连接设备")

                # 内容转换为 UCS2 (UTF-16-BE) 十六进制
                content_hex = content.encode('utf-16-be').hex().upper()
                logger.debug(f"[ML307A] 中文内容HEX: {content_hex}")

                # 文本模式
                self._ser.write(b'AT+CMGF=1\r\n')
                self._ser.flush()
                time.sleep(0.5)
                self._ser.read_all()

                # 设置 CSMP: fo=17, vp=167, pid=0, dcs=8 (UCS2编码)
                self._ser.write(b'AT+CSMP=17,167,0,8\r\n')
                self._ser.flush()
                time.sleep(0.5)
                self._ser.read_all()

                # 发送命令
                self._ser.write(f'AT+CMGS="{recipient}"\r\n'.encode())
                self._ser.flush()
                time.sleep(1)
                self._ser.read_all()

                # 发送 UCS2 编码的内容 + Ctrl-Z
                self._ser.write(content_hex.encode())
                self._ser.write(b'\x1A')
                self._ser.flush()

                time.sleep(5)
                response = self._ser.read_all().decode('gbk', errors='ignore')
                self._disconnect()

                if "+CMGS:" in response or "OK" in response:
                    logger.info(f"[ML307A] 中文短信发送成功：{client_name}")
                    return SendResult(success=True, channel=self.channel_name, external_id=f"ml307a_{recipient}_{int(time.time())}")
                else:
                    logger.warning(f"[ML307A] 中文短信发送响应：{response.strip()}")
                    return SendResult(success=False, channel=self.channel_name, error=f"发送失败：{response.strip()}")

            except Exception as e:
                logger.error(f"[ML307A] 中文短信发送异常：{e}")
                self._disconnect()
                if attempt >= self.retry_count:
                    return SendResult(success=False, channel=self.channel_name, error=str(e))
                time.sleep(2)

        return SendResult(success=False, channel=self.channel_name, error="多次重试失败")