"""
WeChat 个人微信渠道驱动（基于 WeChatFerry/wcferry 风格的本地 RPC）

实现位置：src/channels/drivers/wechat_cli.py
依赖：与现有渠道驱动一致（BaseChannelDriver / SendResult）。

工作流：
1. 启动时通过 HTTP RPC 拉取一次通讯录，缓存 phone -> wxid 映射
2. 定时（phone_cache_ttl_min）刷新一次缓存
3. 发送时按客户手机号查 wxid，调用本地 HTTP RPC 发送文本
4. 失败时回落到 ML307A 短信猫（由上层 SendExecutor 处理）

注意：所有非官方微信协议都存在封号/失效风险，请仅在商户机器本地使用。
"""
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Optional

from channels.base import BaseChannelDriver, SendResult

logger = logging.getLogger(__name__)

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logger.warning("requests 未安装，wechat_cli 渠道不可用。请运行：pip install requests")


class WeChatCliDriver(BaseChannelDriver):
    """个人微信 CLI 渠道驱动（通过本地 HTTP RPC 调用 wcferry 之类服务）

    配置项（config.yaml 中 channels.wechat_cli 下）：
    - enabled: bool，是否启用
    - host: str，RPC 地址，默认 127.0.0.1
    - port: int，RPC 端口，默认 9999
    - timeout: int，HTTP 超时秒数，默认 10
    - dry_run: bool，True 时不真实发送，仅记录日志
    - phone_cache_ttl_min: int，通讯录缓存 TTL（分钟），默认 1440
    - login_check_path: str，探活路径，默认 /login
    - friends_path: str，通讯录接口，默认 /friends
    - send_text_path: str，发送文本接口，默认 /send-text
    """

    channel_name = "wechat_cli"

    def __init__(self, config_raw: dict):
        self.enabled = config_raw.get("enabled", False)
        self.host = config_raw.get("host", "127.0.0.1")
        self.port = int(config_raw.get("port", 9999))
        self.timeout = int(config_raw.get("timeout", 10))
        self.dry_run = bool(config_raw.get("dry_run", False))
        self.phone_cache_ttl_min = int(config_raw.get("phone_cache_ttl_min", 1440))

        # 兼容不同 RPC 实现暴露的接口路径
        self.login_check_path = config_raw.get("login_check_path", "/login")
        self.friends_path = config_raw.get("friends_path", "/friends")
        self.send_text_path = config_raw.get("send_text_path", "/send-text")

        # 通讯录缓存：list of dict，至少含 wxid/phone/nickname/remark
        self._friends: list[dict] = []
        self._cache_loaded_at: Optional[datetime] = None
        self._lock = threading.Lock()

        # 用于单测中替换 requests 的 session
        self._session = None

    # ── 工具方法 ───────────────────────────────────────────────

    def _base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def _get_session(self):
        """获取 requests.Session，未注入自定义 session 时创建默认"""
        if self._session is not None:
            return self._session
        if not REQUESTS_AVAILABLE:
            return None
        return requests.Session()

    def _mask_phone(self, phone: str) -> str:
        if not phone or len(phone) < 7:
            return "***"
        return phone[:3] + "****" + phone[-4:]

    def _cache_expired(self) -> bool:
        if self._cache_loaded_at is None:
            return True
        return datetime.now() - self._cache_loaded_at > timedelta(minutes=self.phone_cache_ttl_min)

    # ── 渠道能力 ───────────────────────────────────────────────

    def is_available(self) -> bool:
        """探活：能连上 RPC 服务并返回已登录即可用"""
        if not self.enabled:
            return False
        if not REQUESTS_AVAILABLE:
            return False
        session = self._get_session()
        if session is None:
            return False
        try:
            resp = session.get(
                f"{self._base_url()}{self.login_check_path}",
                timeout=self.timeout,
            )
            if resp.status_code != 200:
                logger.warning(f"[wechat_cli] 探活失败：HTTP {resp.status_code}")
                return False
            # wcferry 风格：返回 JSON 含 success/code/wxid
            data = {}
            try:
                data = resp.json()
            except Exception:
                # 退化：非 JSON 也视为可用
                return True
            if isinstance(data, dict):
                if data.get("success") is True:
                    return True
                if data.get("code") == 0:
                    return True
                if data.get("wxid"):
                    return True
            return True
        except Exception as e:
            logger.error(f"[wechat_cli] 探活异常：{e}")
            return False

    # ── 通讯录缓存 ─────────────────────────────────────────────

    def load_friend_cache(self, force: bool = False) -> int:
        """从 RPC 拉取通讯录并写入内存缓存

        Returns:
            缓存条数；失败返回 0。
        """
        if not self.enabled or not REQUESTS_AVAILABLE:
            return 0
        if not force and not self._cache_expired():
            return len(self._friends)

        session = self._get_session()
        if session is None:
            return 0

        try:
            resp = session.get(
                f"{self._base_url()}{self.friends_path}",
                timeout=self.timeout,
            )
            if resp.status_code != 200:
                logger.warning(f"[wechat_cli] 拉取通讯录失败：HTTP {resp.status_code}")
                return 0
            data = resp.json()
        except Exception as e:
            logger.error(f"[wechat_cli] 拉取通讯录异常：{e}")
            return 0

        friends: list[dict] = []
        # 兼容多种返回结构
        if isinstance(data, list):
            friends = data
        elif isinstance(data, dict):
            for key in ("friends", "data", "contacts", "result"):
                if key in data and isinstance(data[key], list):
                    friends = data[key]
                    break

        # 字段规整化：只保留需要的列
        normalized: list[dict] = []
        for item in friends:
            if not isinstance(item, dict):
                continue
            normalized.append({
                "wxid": item.get("wxid") or item.get("userName") or "",
                "phone": (item.get("phone") or item.get("mobile") or "").strip(),
                "nickname": item.get("nickname") or item.get("nickName") or "",
                "remark": item.get("remark") or item.get("displayName") or "",
            })

        with self._lock:
            self._friends = normalized
            self._cache_loaded_at = datetime.now()
        logger.info(f"[wechat_cli] 通讯录缓存已更新：{len(normalized)} 条")
        return len(normalized)

    def find_wxid_by_phone(self, phone: str) -> Optional[str]:
        """在缓存里查 wxid；缓存过期则尝试刷新一次。"""
        if not phone:
            return None
        if self._cache_expired():
            self.load_friend_cache(force=True)
        with self._lock:
            for friend in self._friends:
                # 去掉空格 / +86 后比较
                fp = (friend.get("phone") or "").replace(" ", "").replace("+86", "").lstrip("+")
                if fp and fp == phone:
                    wxid = friend.get("wxid")
                    if wxid:
                        return wxid
        return None

    def get_friend_count(self) -> int:
        with self._lock:
            return len(self._friends)

    # ── 发送 ───────────────────────────────────────────────────

    def send(self, recipient: str, content: str, **kwargs) -> SendResult:
        """发送消息。recipient 为客户手机号。

        kwargs:
            client_name: 客户姓名（用于日志）
        """
        if not self.enabled:
            return SendResult(success=False, channel=self.channel_name, error="wechat_cli 未启用")
        if not REQUESTS_AVAILABLE:
            return SendResult(success=False, channel=self.channel_name, error="requests 库未安装")

        client_name = kwargs.get("client_name", "")
        if not recipient:
            return SendResult(
                success=False, channel=self.channel_name,
                error="recipient 为空（缺少手机号）",
            )
        if not content:
            return SendResult(
                success=False, channel=self.channel_name,
                error="content 为空",
            )

        # 查 wxid
        wxid = self.find_wxid_by_phone(recipient)
        if not wxid:
            return SendResult(
                success=False, channel=self.channel_name,
                error=f"未找到手机号 {self._mask_phone(recipient)} 对应的微信好友，请先添加或刷新通讯录",
            )

        if self.dry_run:
            logger.info(
                f"[wechat_cli][dry_run] -> wxid={wxid} name={client_name} "
                f"phone={self._mask_phone(recipient)} content_len={len(content)}"
            )
            return SendResult(
                success=True, channel=self.channel_name,
                external_id=f"dry_run_{int(time.time())}",
            )

        # 真实发送：POST {base_url}/send-text  {wxid, msg}
        session = self._get_session()
        if session is None:
            return SendResult(success=False, channel=self.channel_name, error="requests session 不可用")

        try:
            resp = session.post(
                f"{self._base_url()}{self.send_text_path}",
                json={"wxid": wxid, "msg": content},
                timeout=self.timeout,
            )
        except Exception as e:
            return SendResult(
                success=False, channel=self.channel_name,
                error=f"RPC 调用失败：{e}",
            )

        if resp.status_code != 200:
            return SendResult(
                success=False, channel=self.channel_name,
                error=f"HTTP {resp.status_code}: {resp.text[:200]}",
            )

        external_id: Optional[str] = None
        try:
            data = resp.json()
            if isinstance(data, dict):
                external_id = (
                    data.get("msg_id")
                    or data.get("id")
                    or data.get("msgId")
                )
                # 失败判定：success=False 或 code != 0
                if data.get("success") is False or (
                    isinstance(data.get("code"), int) and data.get("code") != 0
                ):
                    return SendResult(
                        success=False, channel=self.channel_name,
                        error=data.get("message") or f"RPC 返回失败：{data}",
                    )
        except Exception:
            # 非 JSON 视为成功
            pass

        logger.info(
            f"[wechat_cli] 发送成功 wxid={wxid} name={client_name} "
            f"phone={self._mask_phone(recipient)} content_len={len(content)}"
        )
        return SendResult(
            success=True, channel=self.channel_name,
            external_id=str(external_id) if external_id is not None else None,
        )
