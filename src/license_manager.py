"""
AI-Care CRM 激活码离线验证模块
使用 HMAC-SHA256 离线验证，无需联网。

激活码格式：CARE-XXXX-XXXX-XXXX-XXXX（Base32 编码的签名 payload）
Payload: {m: machine_id, t: tier, e: expire_date, r: is_trial(可选)}

状态机：
  active        - 正式版有效
  trial_active  - 试用版有效
  grace_period  - 已过期 ≤ 7 天，进入只读宽限期（数据可见、写入被拦截）
  expired       - 已过期 > 7 天，tier 回退 basic
  invalid       - 签名/格式/机器绑定校验失败
  unactivated   - 未输入激活码
"""
import hashlib
import json
import platform
import subprocess
import base64
import hmac
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Optional


# ── 常量 ──────────────────────────────────────────────────────────

GRACE_PERIOD_DAYS = 7  # 试用/正式过期后的只读宽限期天数


# ── 机器特征码 ────────────────────────────────────────────────────

def _get_machine_id() -> str:
    """
    获取机器特征码：基于平台信息 + 主板序列号的 SHA256。
    """
    parts = [
        platform.node(),
        platform.machine(),
        platform.processor(),
    ]
    # Windows: 尝试获取主板序列号
    if platform.system() == "Windows":
        try:
            result = subprocess.run(
                ["wmic", "baseboard", "get", "serialnumber"],
                capture_output=True, text=True, timeout=5
            )
            serial = result.stdout.strip().split("\n")[-1].strip()
            if serial and serial != "To be filled by O.E.M.":
                parts.append(serial)
        except Exception:
            pass
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


# ── 激活码数据结构 ────────────────────────────────────────────────

@dataclass
class LicenseInfo:
    tier: str  # "pro" / "business" / "basic"
    expire_date: str  # "YYYY-MM-DD"
    machine_id: str
    valid: bool = True
    message: str = ""
    # 扩展字段（带默认值，向后兼容）
    is_trial: bool = False
    in_grace_period: bool = False
    grace_days_remaining: int = 0
    read_only_mode: bool = False
    status: str = "active"  # active / trial_active / grace_period / expired / invalid / unactivated

    @property
    def is_expired(self) -> bool:
        """已过到期日（不考虑宽限期）。"""
        try:
            exp = datetime.strptime(self.expire_date, "%Y-%m-%d").date()
            return date.today() > exp
        except ValueError:
            return True

    @property
    def is_in_grace_period(self) -> bool:
        """已过到期日，但仍在 7 天宽限期内。"""
        try:
            exp = datetime.strptime(self.expire_date, "%Y-%m-%d").date()
            grace_end = exp + timedelta(days=GRACE_PERIOD_DAYS)
            today = date.today()
            return today > exp and today <= grace_end
        except ValueError:
            return False

    @property
    def is_fully_expired(self) -> bool:
        """已过宽限期，必须重新激活。"""
        try:
            exp = datetime.strptime(self.expire_date, "%Y-%m-%d").date()
            grace_end = exp + timedelta(days=GRACE_PERIOD_DAYS)
            return date.today() > grace_end
        except ValueError:
            return True

    @property
    def days_remaining(self) -> int:
        try:
            exp = datetime.strptime(self.expire_date, "%Y-%m-%d").date()
            delta = exp - date.today()
            return max(0, delta.days)
        except ValueError:
            return 0


# ── 激活码签名/验证（HMAC-SHA256 方案） ──────────────────────────

# 内置签名密钥（开发者侧和软件侧共用）
_SECRET = b"ai-care-crm-license-secret-v1"


def generate_license_key(machine_id: str, tier: str, expire_date: str,
                         is_trial: bool = False) -> str:
    """
    【开发者侧工具】生成激活码。
    此函数不应随软件分发，仅供开发者使用。

    is_trial=True 时，payload 多写 "r":1 标记，前端用于显示"试用版"标签。
    业务限制（功能/额度）不区分试用与正式，全部由 tier 决定。
    """
    payload_dict = {
        "m": machine_id,
        "t": tier,
        "e": expire_date,
    }
    if is_trial:
        payload_dict["r"] = 1

    payload = json.dumps(payload_dict, separators=(",", ":"), sort_keys=True)

    sig = hmac.new(_SECRET, payload.encode(), hashlib.sha256).digest()
    # 使用长度前缀方式组合，避免分隔符冲突
    payload_bytes = payload.encode()
    raw = len(payload_bytes).to_bytes(4, 'big') + payload_bytes + sig
    encoded = base64.b32encode(raw).decode().rstrip("=")

    # 格式化为 CARE-XXXX-XXXX-... 格式
    chunks = [encoded[i:i+4] for i in range(0, len(encoded), 4)]
    return "CARE-" + "-".join(chunks)


def _decode_license_key(key: str) -> Optional[tuple[dict, bytes]]:
    """解码激活码，返回 (payload_dict, signature) 或 None。"""
    try:
        # 去掉 CARE- 前缀和分隔符
        clean = key.replace("CARE-", "").replace("-", "")
        # 补齐 Base32 padding
        padding = (8 - len(clean) % 8) % 8
        clean += "=" * padding
        raw = base64.b32decode(clean)

        # 使用长度前缀方式分离 payload 和 signature
        # 格式: [4字节payload长度][payload][signature(32字节)]
        if len(raw) < 4:
            return None
        payload_len = int.from_bytes(raw[:4], 'big')
        if len(raw) < 4 + payload_len:
            return None
        payload_bytes = raw[4:4 + payload_len]
        sig = raw[4 + payload_len:]

        payload = json.loads(payload_bytes.decode())
        return payload, sig
    except Exception:
        return None


# ── 验证主函数 ────────────────────────────────────────────────────

class LicenseManager:

    def __init__(self):
        self.machine_id = _get_machine_id()
        self._cached: Optional[LicenseInfo] = None

    def verify(self, license_key: str) -> LicenseInfo:
        """
        离线验证激活码，返回完整状态机结果。
        """
        # 未输入激活码
        if not license_key or not license_key.strip():
            return LicenseInfo(
                tier="basic", expire_date="", machine_id=self.machine_id,
                valid=False, message="未输入激活码", status="unactivated"
            )

        # 解码
        result = _decode_license_key(license_key.strip())
        if result is None:
            return LicenseInfo(
                tier="basic", expire_date="", machine_id=self.machine_id,
                valid=False, message="激活码格式无效", status="invalid"
            )

        payload, sig = result
        machine_id = payload.get("m", "")
        tier = payload.get("t", "basic")
        if tier not in ("pro", "business"):
            tier = "basic"
        expire_date = payload.get("e", "")
        is_trial = bool(payload.get("r", 0))

        # 验证签名
        payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True)
        expected_sig = hmac.new(_SECRET, payload_json.encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(sig, expected_sig):
            return LicenseInfo(
                tier="basic", expire_date=expire_date, machine_id=self.machine_id,
                valid=False, message="激活码签名验证失败", status="invalid",
                is_trial=is_trial,
            )

        # 验证机器绑定
        if machine_id != self.machine_id:
            return LicenseInfo(
                tier=tier, expire_date=expire_date, machine_id=self.machine_id,
                valid=False, message=f"激活码与本机不匹配（本机: {self.machine_id}）",
                status="invalid", is_trial=is_trial,
            )

        # 构造基本信息
        info = LicenseInfo(
            tier=tier, expire_date=expire_date, machine_id=self.machine_id,
            is_trial=is_trial,
        )

        # 三态判定
        if not info.is_expired:
            # 未过期：active 或 trial_active
            info.valid = True
            info.status = "trial_active" if is_trial else "active"
            info.message = "试用版有效" if is_trial else "正式版有效"
            return info

        if info.is_in_grace_period:
            # 宽限期：仍 valid，但 read_only
            try:
                exp = datetime.strptime(expire_date, "%Y-%m-%d").date()
                grace_end = exp + timedelta(days=GRACE_PERIOD_DAYS)
                grace_left = max(0, (grace_end - date.today()).days)
            except ValueError:
                grace_left = 0
            info.valid = True
            info.status = "grace_period"
            info.in_grace_period = True
            info.read_only_mode = True
            info.grace_days_remaining = grace_left
            info.message = f"试用已到期 · 只读宽限期还剩 {grace_left} 天，请激活正式版"
            return info

        # 完全过期
        info.valid = False
        info.status = "expired"
        info.message = f"激活码已过期且超出宽限期（到期日: {expire_date}）"
        return info

    def get_current_tier(self, license_key: str) -> str:
        """
        返回当前 tier。
        - active / trial_active / grace_period → 返回原 tier（宽限期内付费功能仍可见，写入由中间件拦截）
        - expired / invalid / unactivated → 返回 "basic"
        """
        self._cached = self.verify(license_key)
        if self._cached.status in ("active", "trial_active", "grace_period"):
            return self._cached.tier
        return "basic"

    def get_machine_id(self) -> str:
        """返回本机特征码（供商户购买激活码时提供给开发者）。"""
        return self.machine_id


# ── 全局单例 ──────────────────────────────────────────────────────

_manager: Optional[LicenseManager] = None


def get_license_manager() -> LicenseManager:
    global _manager
    if _manager is None:
        _manager = LicenseManager()
    return _manager
