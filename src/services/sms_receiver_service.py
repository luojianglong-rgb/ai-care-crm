"""
短信接收服务
- 轮询读取新短信
- 存入接收队列
- 分类判断（意见反馈/预约/其他）
- 通知管理员处理
"""
import logging
import threading
import time
import re
from datetime import datetime
from queue import Queue, Empty
from dataclasses import dataclass, field
from typing import Optional, Callable, List
from enum import Enum

logger = logging.getLogger(__name__)


class SmsCategory(Enum):
    """短信分类"""
    FEEDBACK = "feedback"      # 意见反馈
    APPOINTMENT = "appointment"  # 预约
    REPLY = "reply"            # 客户回复
    OTHER = "other"            # 其他


@dataclass
class ReceivedSms:
    """接收到的短信"""
    index: int                    # SIM 卡存储索引
    sender: str                   # 发送者号码
    content: str                  # 短信内容
    received_at: datetime         # 接收时间
    category: SmsCategory = SmsCategory.OTHER  # 分类
    client_id: Optional[str] = None  # 关联的客户 ID
    client_name: Optional[str] = None  # 客户名称
    processed: bool = False       # 是否已处理
    notes: str = ""               # 处理备注


class SmsReceiverService:
    """短信接收服务"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, driver=None, db_session_factory=None):
        if hasattr(self, '_initialized') and self._initialized:
            return

        self.driver = driver
        self.db_session_factory = db_session_factory
        self.receive_queue: Queue[ReceivedSms] = Queue()
        self.running = False
        self.poll_thread: Optional[threading.Thread] = None
        self.poll_interval = 30  # 轮询间隔（秒）
        self._initialized = True
        self._last_indexes = set()  # 已处理的短信索引

        # 分类关键词
        self.feedback_keywords = [
            "建议", "意见", "反馈", "投诉", "不满", "问题",
            "改进", "希望", "觉得", "感觉", "体验"
        ]
        self.appointment_keywords = [
            "预约", "约", "预订", "订", "明天", "后天",
            "几点", "有空", "想过来", "过去", "过来"
        ]

    def set_driver(self, driver):
        """设置短信驱动"""
        self.driver = driver

    def start(self):
        """启动接收服务"""
        if self.running:
            return
        self.running = True
        self.poll_thread = threading.Thread(target=self._poll_worker, daemon=True)
        self.poll_thread.start()
        logger.info("[短信接收] 服务已启动，每 %d 秒轮询一次", self.poll_interval)

    def stop(self):
        """停止接收服务"""
        self.running = False
        if self.poll_thread:
            self.poll_thread.join(timeout=5)
        logger.info("[短信接收] 服务已停止")

    def _poll_worker(self):
        """轮询工作线程"""
        while self.running:
            try:
                self._check_new_sms()
            except Exception as e:
                logger.error(f"[短信接收] 轮询异常: {e}")

            time.sleep(self.poll_interval)

    def _check_new_sms(self):
        """检查新短信"""
        try:
            import serial
            # 直接打开串口
            port = self.driver._scan_serial_port() if self.driver else None
            if not port:
                logger.warning("[短信接收] 未找到串口设备")
                return

            ser = serial.Serial(
                port=port,
                baudrate=115200,
                timeout=5
            )
            time.sleep(0.5)

            # 使用 PDU 模式读取（支持中文）
            ser.write(b'AT+CMGF=0\r\n')
            time.sleep(0.5)
            ser.read_all()

            # 列出所有短信 (status=4 表示全部)
            ser.write(b'AT+CMGL=4\r\n')
            time.sleep(3)
            response = ser.read(5000).decode('gbk', errors='ignore')

            # 解析 PDU 短信
            messages = self._parse_pdu_sms_list(response)

            for sms in messages:
                if sms.index not in self._last_indexes:
                    self._last_indexes.add(sms.index)
                    self._process_incoming_sms(sms)

            ser.close()

        except Exception as e:
            logger.error(f"[短信接收] 检查新短信失败: {e}")

    def _parse_pdu_sms_list(self, response: str) -> List[ReceivedSms]:
        """解析 PDU 格式短信列表"""
        messages = []
        lines = response.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith('+CMGL:'):
                try:
                    # +CMGL: index,status,,length
                    match = re.match(r'\+CMGL:\s*(\d+),(\d+),,(\d+)', line)
                    if match:
                        index = int(match.group(1))
                        # status = int(match.group(2))  # 0=未读,1=已读,2=已发送,3=未发送
                        pdu_length = int(match.group(3))

                        # 下一行是 PDU 数据
                        i += 1
                        if i < len(lines):
                            pdu_data = lines[i].strip()
                            sms = self._parse_pdu(index, pdu_data)
                            if sms:
                                messages.append(sms)

                except Exception as e:
                    logger.warning(f"[短信接收] 解析 PDU 失败: {e}")
            i += 1

        return messages

    def _parse_pdu(self, index: int, pdu_data: str) -> Optional[ReceivedSms]:
        """解析单条 PDU 短信"""
        try:
            pos = 0

            # SCA (短信中心)
            sca_len = int(pdu_data[pos:pos+2], 16)
            pos += 2 + sca_len * 2

            # PDU 类型
            pdu_type = int(pdu_data[pos:pos+2], 16)
            pos += 2

            # 发送者号码
            sender_len = int(pdu_data[pos:pos+2], 16)
            pos += 2
            sender_type = pdu_data[pos:pos+2]
            pos += 2

            # 发送者号码（半字节交换）
            sender_raw_len = sender_len + (sender_len % 2)  # 补F凑偶数
            sender_raw = pdu_data[pos:pos+sender_raw_len]
            sender = ''
            for j in range(0, len(sender_raw), 2):
                if j+1 < len(sender_raw):
                    sender += sender_raw[j+1] + sender_raw[j]
            sender = sender.replace('F', '').replace('f', '')
            if sender_type == '91' and not sender.startswith('+'):
                sender = '+' + sender
            pos += sender_raw_len

            # PID
            pos += 2

            # DCS (数据编码方案)
            dcs = pdu_data[pos:pos+2]
            pos += 2

            # 时间戳 (14 个字符)
            timestamp_raw = pdu_data[pos:pos+14]
            pos += 14

            # 解析时间戳
            try:
                # 格式: YYMMDDHHMMSSzz (半字节交换)
                year = int(timestamp_raw[0:2], 16) + 2000
                month = int(timestamp_raw[2:4], 16)
                day = int(timestamp_raw[4:6], 16)
                hour = int(timestamp_raw[6:8], 16)
                minute = int(timestamp_raw[8:10], 16)
                second = int(timestamp_raw[10:12], 16)
                received_at = datetime(year, month, day, hour, minute, second)
            except:
                received_at = datetime.now()

            # 用户数据长度
            udl = int(pdu_data[pos:pos+2], 16)
            pos += 2

            # 用户数据
            user_data = pdu_data[pos:]

            # 解码内容
            content = self._decode_user_data(user_data, dcs)

            logger.info(f"[短信接收] 解析PDU: {sender} -> {content[:30]}...")

            return ReceivedSms(
                index=index,
                sender=sender,
                content=content,
                received_at=received_at
            )

        except Exception as e:
            logger.error(f"[短信接收] 解析PDU异常: {e}")
            return None

    def _decode_user_data(self, user_data: str, dcs: str) -> str:
        """解码用户数据"""
        if not user_data:
            return ""

        try:
            # DCS=08 或 18 表示 UCS2 编码
            if dcs in ('08', '18'):
                # 检查长短信头 (050003...)
                if user_data.startswith('050003'):
                    user_data = user_data[12:]  # 跳过 6 字节头

                content_bytes = bytes.fromhex(user_data)
                return content_bytes.decode('utf-16-be', errors='ignore').strip()

            # DCS=00 表示 GSM 7bit
            elif dcs == '00':
                # TODO: GSM 7bit 解码
                return user_data

            # 其他情况尝试直接解码
            else:
                try:
                    content_bytes = bytes.fromhex(user_data)
                    return content_bytes.decode('utf-16-be', errors='ignore').strip()
                except:
                    return user_data

        except Exception as e:
            logger.warning(f"[短信接收] 解码失败: {e}")
            return user_data

    def _parse_sms_list(self, response: str) -> List[ReceivedSms]:
        """解析短信列表响应"""
        messages = []
        # 格式: +CMGL: index,"status","sender",,"datetime"\ncontent
        # 注意：内容可能在下一行
        lines = response.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith('+CMGL:'):
                try:
                    # 解析头部
                    # +CMGL: 1,"REC READ","10684682700001009366",,"26/04/03,21:08:43+32"
                    match = re.match(
                        r'\+CMGL:\s*(\d+),"([^"]+)","([^"]+)",,"([^"]+)"',
                        line
                    )
                    if match:
                        index = int(match.group(1))
                        status = match.group(2)
                        sender = match.group(3)
                        datetime_str = match.group(4)

                        # 下一行是内容
                        i += 1
                        if i < len(lines):
                            content_raw = lines[i].strip()
                            # 尝试解码 UCS2/PDU 格式
                            content = self._decode_sms_content(content_raw)
                        else:
                            content = ""

                        # 解析时间
                        try:
                            # 格式: yy/MM/dd,HH:MM:SS+tz
                            received_at = datetime.strptime(datetime_str[:17], "%y/%m/%d,%H:%M:%S")
                        except:
                            received_at = datetime.now()

                        sms = ReceivedSms(
                            index=index,
                            sender=sender,
                            content=content,
                            received_at=received_at
                        )
                        messages.append(sms)
                        logger.info(f"[短信接收] 解析短信: 来自 {sender}, 内容: {content[:30]}...")

                except Exception as e:
                    logger.warning(f"[短信接收] 解析短信失败: {e}")
            i += 1

        return messages

    def _decode_sms_content(self, content_raw: str) -> str:
        """解码短信内容（可能是 UCS2/PDU 编码）"""
        if not content_raw:
            return ""

        # 检查是否是十六进制编码（UCS2/PDU）
        # 内容只包含 0-9A-F 且长度为偶数
        if all(c in '0123456789ABCDEFabcdef' for c in content_raw) and len(content_raw) % 4 == 0:
            try:
                # 尝试 UCS2 解码
                content_bytes = bytes.fromhex(content_raw)
                decoded = content_bytes.decode('utf-16-be', errors='ignore')
                if decoded and not decoded.startswith('\x00'):
                    return decoded.strip()
            except:
                pass

        # 检查是否有 PDU 头（050003 表示长短信）
        if content_raw.startswith('050003'):
            try:
                # 跳过 PDU 头（6字节）后解码
                payload = content_raw[12:]  # 跳过 050003XXYYZZ
                if all(c in '0123456789ABCDEFabcdef' for c in payload):
                    content_bytes = bytes.fromhex(payload)
                    decoded = content_bytes.decode('utf-16-be', errors='ignore')
                    return decoded.strip()
            except:
                pass

        # 直接返回原文
        return content_raw

    def _process_incoming_sms(self, sms: ReceivedSms):
        """处理接收到的短信"""
        # 分类
        sms.category = self._classify_sms(sms.content)

        # 查找关联客户
        self._match_client(sms)

        # 加入队列
        self.receive_queue.put(sms)

        logger.info(f"[短信接收] 新短信入队: {sms.sender} - [{sms.category.value}] {sms.content[:30]}...")

    def _classify_sms(self, content: str) -> SmsCategory:
        """分类短信内容"""
        content_lower = content.lower()

        # 检查预约关键词
        for keyword in self.appointment_keywords:
            if keyword in content:
                return SmsCategory.APPOINTMENT

        # 检查反馈关键词
        for keyword in self.feedback_keywords:
            if keyword in content:
                return SmsCategory.FEEDBACK

        # 默认为回复
        return SmsCategory.REPLY

    def _match_client(self, sms: ReceivedSms):
        """匹配关联客户"""
        if not self.db_session_factory:
            return

        try:
            from database import get_db
            from db_models import Client

            # 清理发送者号码
            sender_clean = sms.sender.replace('+86', '').replace('+', '')

            db = next(get_db())
            client = db.query(Client).filter(
                Client.phone == sender_clean
            ).first()

            if client:
                sms.client_id = str(client.id)
                sms.client_name = client.name
                logger.info(f"[短信接收] 匹配到客户: {client.name}")

        except Exception as e:
            logger.warning(f"[短信接收] 匹配客户失败: {e}")

    def get_pending_sms(self) -> List[ReceivedSms]:
        """获取待处理的短信"""
        pending = []
        while True:
            try:
                sms = self.receive_queue.get_nowait()
                pending.append(sms)
            except Empty:
                break
        return pending

    def get_stats(self) -> dict:
        """获取接收统计"""
        return {
            "queue_size": self.receive_queue.qsize(),
            "processed_count": len(self._last_indexes),
            "running": self.running
        }


# 全局单例
_sms_receiver_service: Optional[SmsReceiverService] = None


def get_sms_receiver_service(driver=None, db_session_factory=None) -> SmsReceiverService:
    """获取短信接收服务单例"""
    global _sms_receiver_service
    if _sms_receiver_service is None:
        _sms_receiver_service = SmsReceiverService(driver, db_session_factory)
    return _sms_receiver_service