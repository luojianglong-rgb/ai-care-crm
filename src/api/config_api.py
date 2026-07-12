"""
系统配置与额度 API 端点
/api/v1/config/*
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional, List
import os
from datetime import datetime

from database import get_db
from config import get_config, AppConfig
from license_manager import get_license_manager
from services.quota_service import QuotaService

router = APIRouter()


# ── 响应模型 ──────────────────────────────────────────────────────

class StoreInfo(BaseModel):
    name: str
    business_type: str


class TerminologyInfo(BaseModel):
    staff_title: str
    analysis_name: str
    plan_name: str


class LicenseStatus(BaseModel):
    tier: str
    valid: bool
    message: str
    expire_date: str
    days_remaining: int
    machine_id: str
    # 试用 / 宽限期扩展字段
    status: str = "unactivated"          # active / trial_active / grace_period / expired / invalid / unactivated
    is_trial: bool = False               # 是否试用版
    in_grace_period: bool = False        # 是否处于宽限期
    grace_days_remaining: int = 0        # 宽限期剩余天数
    read_only_mode: bool = False         # 是否只读模式


class LLMStatus(BaseModel):
    mode: str
    provider: str
    model: str
    available: bool


class QuotaItem(BaseModel):
    used: int
    limit: int
    remaining: int
    unlimited: bool


class QuotaSummary(BaseModel):
    month: str
    tier: str
    analysis: QuotaItem
    plan: QuotaItem
    content: QuotaItem


class SystemInfoResponse(BaseModel):
    store: StoreInfo
    terminology: TerminologyInfo
    license: LicenseStatus
    llm: LLMStatus
    server: dict = {}  # dev_mode, debug 等服务配置
    version: str = "2.1.0"
    db_version: int = 2


class ActivateLicenseRequest(BaseModel):
    key: str


class MachineIdResponse(BaseModel):
    machine_id: str


class SmsTestRequest(BaseModel):
    phone: str
    content: str


class SmsTestResponse(BaseModel):
    success: bool
    message: str
    channel: str = ""


class SmsStatusResponse(BaseModel):
    enabled: bool
    available: bool
    port: str
    signal: str


class SmsQueueResponse(BaseModel):
    task_id: str
    queue_size: int
    message: str


class SmsQueueStatusResponse(BaseModel):
    queue_size: int
    sent_count: int
    failed_count: int
    running: bool


# ── 数据库备份模型 ──────────────────────────────────────────────────────

class BackupResponse(BaseModel):
    success: bool
    backup_path: str
    backup_size: int  # bytes
    message: str


class BackupListResponse(BaseModel):
    backups: List[dict]
    total: int


class DbVersionResponse(BaseModel):
    current_version: int
    system_version: int
    needs_migration: bool


# ── API 端点 ──────────────────────────────────────────────────────

@router.get("/info", response_model=SystemInfoResponse)
def get_system_info():
    """获取系统配置概览（隐藏 API Key 等敏感信息）。"""
    config = get_config()
    lm = get_license_manager()
    license_info = lm.verify(config.license.key)

    # 检查 LLM 是否可用
    from ai.llm_client import get_llm_client
    llm_client = get_llm_client()

    return SystemInfoResponse(
        store=StoreInfo(
            name=config.store.name,
            business_type=config.store.business_type,
        ),
        terminology=TerminologyInfo(
            staff_title=config.get_terminology("staff_title"),
            analysis_name=config.get_terminology("analysis_name"),
            plan_name=config.get_terminology("plan_name"),
        ),
        license=LicenseStatus(
            tier=config.current_tier,
            valid=license_info.valid if config.license.key else False,
            message=license_info.message if config.license.key else "基础版（永久免费）· 联系销售获取试用",
            expire_date=license_info.expire_date or "",
            days_remaining=license_info.days_remaining,
            machine_id=lm.get_machine_id(),
            status=license_info.status,
            is_trial=license_info.is_trial,
            in_grace_period=license_info.in_grace_period,
            grace_days_remaining=license_info.grace_days_remaining,
            read_only_mode=license_info.read_only_mode,
        ),
        llm=LLMStatus(
            mode=config.llm.mode,
            provider=config.llm.provider if config.llm.mode == "direct" else "proxy",
            model=config.llm.get_model(),
            available=llm_client.is_available,
        ),
        server={
            "dev_mode": config.server.dev_mode,
            "debug": config.server.debug,
        },
    )


@router.get("/quota", response_model=QuotaSummary)
def get_quota_usage(db: Session = Depends(get_db)):
    """获取当月 AI 额度使用情况。"""
    config = get_config()
    qs = QuotaService(config)
    summary = qs.get_usage_summary(db)

    return QuotaSummary(
        month=summary["month"],
        tier=summary["tier"],
        analysis=QuotaItem(**summary["analysis"]),
        plan=QuotaItem(**summary["plan"]),
        content=QuotaItem(**summary["content"]),
    )


@router.get("/machine-id", response_model=MachineIdResponse)
def get_machine_id():
    """获取本机特征码（购买激活码时需提供给开发者）。"""
    lm = get_license_manager()
    return MachineIdResponse(machine_id=lm.get_machine_id())


@router.post("/activate", response_model=LicenseStatus)
def activate_license(req: ActivateLicenseRequest):
    """验证并保存激活码。验证成功后写入 config.yaml 并刷新运行时状态。"""
    import yaml
    from pathlib import Path

    lm = get_license_manager()
    info = lm.verify(req.key)

    if info.valid:
        # 验证成功，保存到 config.yaml
        config_path = Path(__file__).parent.parent / "config.yaml"
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f) or {}

            # 更新 license 配置
            if 'license' not in config_data:
                config_data['license'] = {}
            config_data['license']['key'] = req.key

            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)

            # 重新加载配置并刷新运行时 license 状态
            from config import reload_config
            new_config = reload_config()
            new_config.current_tier = lm.get_current_tier(req.key)
            new_config.read_only_mode = info.read_only_mode
            new_config.license_status = info.status
            new_config.is_trial = info.is_trial
            new_config.grace_days_remaining = info.grace_days_remaining
            new_config.days_remaining = info.days_remaining
        except Exception as e:
            info.valid = False
            info.message = f"激活码验证通过，但保存失败：{str(e)}"

    return LicenseStatus(
        tier=info.tier if info.valid else "basic",
        valid=info.valid,
        message=info.message,
        expire_date=info.expire_date or "",
        days_remaining=info.days_remaining,
        machine_id=lm.get_machine_id(),
        status=info.status,
        is_trial=info.is_trial,
        in_grace_period=info.in_grace_period,
        grace_days_remaining=info.grace_days_remaining,
        read_only_mode=info.read_only_mode,
    )


# ── 短信测试 API ──────────────────────────────────────────────────────

@router.get("/sms/status", response_model=SmsStatusResponse)
def get_sms_status():
    """获取 ML307A 短信猫状态。"""
    config = get_config()
    raw_channels = config.raw.get("channels", {}) if hasattr(config, 'raw') else {}
    ml307a_config = raw_channels.get("ml307a", {})

    enabled = ml307a_config.get("enabled", False)

    # 检查设备是否可用
    available = False
    port = ""
    signal = ""

    if enabled:
        try:
            from channels.drivers.ml307a import ML307ADriver
            driver = ML307ADriver(ml307a_config)
            available = driver.is_available()

            if available:
                # 获取信号强度
                import serial
                import time
                ser = serial.Serial(
                    port=driver._scan_serial_port() or "COM7",
                    baudrate=115200,
                    timeout=3
                )
                time.sleep(0.5)
                ser.write(b'AT+CSQ\r\n')
                time.sleep(0.5)
                response = ser.read(100).decode('gbk', errors='ignore')
                ser.close()

                if "+CSQ:" in response:
                    signal = response.split("+CSQ:")[1].split("\r")[0].strip()
                port = driver._scan_serial_port() or "未知"
        except Exception as e:
            available = False

    return SmsStatusResponse(
        enabled=enabled,
        available=available,
        port=port,
        signal=signal
    )


@router.post("/sms/test", response_model=SmsTestResponse)
def test_send_sms(req: SmsTestRequest):
    """发送测试短信（立即发送，不经过队列）。"""
    config = get_config()
    raw_channels = config.raw.get("channels", {}) if hasattr(config, 'raw') else {}
    ml307a_config = raw_channels.get("ml307a", {})

    if not ml307a_config.get("enabled", False):
        return SmsTestResponse(
            success=False,
            message="ML307A 短信功能未启用，请在 config.yaml 中配置 channels.ml307a.enabled: true"
        )

    # 权限检查（开发模式绕过限制）
    dev_mode = config.server.dev_mode
    tier = config.current_tier
    from services.sms_queue_service import get_sms_queue_service
    sms_service = get_sms_queue_service()
    has_perm, perm_msg = sms_service.check_permission(tier, dev_mode)
    if not has_perm:
        return SmsTestResponse(
            success=False,
            message=perm_msg
        )

    try:
        from channels.drivers.ml307a import ML307ADriver
        driver = ML307ADriver(ml307a_config)

        if not driver.is_available():
            return SmsTestResponse(
                success=False,
                message="ML307A 设备不可用，请检查设备连接和驱动",
                channel="ml307a"
            )

        result = driver.send(
            recipient=req.phone,
            content=req.content,
            client_name="测试"
        )

        return SmsTestResponse(
            success=result.success,
            message="发送成功" if result.success else f"发送失败: {result.error}",
            channel="ml307a"
        )

    except Exception as e:
        return SmsTestResponse(
            success=False,
            message=f"发送异常: {str(e)}",
            channel="ml307a"
        )


@router.post("/sms/send", response_model=SmsQueueResponse)
def send_sms_to_queue(req: SmsTestRequest):
    """
    发送短信（加入队列，随机 30-60 秒间隔发送）。
    用于批量发送，避免运营商流控。
    """
    config = get_config()
    raw_channels = config.raw.get("channels", {}) if hasattr(config, 'raw') else {}
    ml307a_config = raw_channels.get("ml307a", {})

    if not ml307a_config.get("enabled", False):
        return SmsQueueResponse(
            task_id="",
            queue_size=0,
            message="ML307A 短信功能未启用"
        )

    # 权限检查（开发模式绕过限制）
    dev_mode = config.server.dev_mode
    tier = config.current_tier
    from services.sms_queue_service import get_sms_queue_service
    sms_service = get_sms_queue_service()
    has_perm, perm_msg = sms_service.check_permission(tier, dev_mode)
    if not has_perm:
        return SmsQueueResponse(
            task_id="",
            queue_size=0,
            message=perm_msg
        )

    # 初始化驱动
    from channels.drivers.ml307a import ML307ADriver
    driver = ML307ADriver(ml307a_config)
    sms_service.set_driver(driver)

    # 确保队列服务运行
    if not sms_service.running:
        sms_service.start()

    # 加入队列
    task_id = sms_service.enqueue(
        phone=req.phone,
        content=req.content,
        client_name="API发送"
    )

    stats = sms_service.get_stats()

    return SmsQueueResponse(
        task_id=task_id,
        queue_size=stats["queue_size"],
        message=f"短信已加入发送队列，当前队列长度: {stats['queue_size']}"
    )


@router.get("/sms/queue", response_model=SmsQueueStatusResponse)
def get_sms_queue_status():
    """获取短信发送队列状态。"""
    from services.sms_queue_service import get_sms_queue_service
    sms_service = get_sms_queue_service()
    stats = sms_service.get_stats()
    return SmsQueueStatusResponse(**stats)


# ── 短信接收 API ──────────────────────────────────────────────────────

class ReceivedSmsResponse(BaseModel):
    index: int
    sender: str
    content: str
    received_at: str
    category: str
    client_id: Optional[str] = None
    client_name: Optional[str] = None
    processed: bool


class ReceivedSmsListResponse(BaseModel):
    messages: List[ReceivedSmsResponse]
    total: int


@router.get("/sms/received", response_model=ReceivedSmsListResponse)
def get_received_sms():
    """获取接收到的短信列表。"""
    from services.sms_receiver_service import get_sms_receiver_service
    receiver = get_sms_receiver_service()
    pending = receiver.get_pending_sms()

    messages = []
    for sms in pending:
        messages.append(ReceivedSmsResponse(
            index=sms.index,
            sender=sms.sender,
            content=sms.content,
            received_at=sms.received_at.strftime("%Y-%m-%d %H:%M:%S"),
            category=sms.category.value,
            client_id=sms.client_id,
            client_name=sms.client_name,
            processed=sms.processed
        ))

    return ReceivedSmsListResponse(messages=messages, total=len(messages))


@router.get("/sms/receiver/status")
def get_sms_receiver_status():
    """获取短信接收服务状态。"""
    from services.sms_receiver_service import get_sms_receiver_service
    receiver = get_sms_receiver_service()
    return receiver.get_stats()


@router.post("/sms/receiver/start")
def start_sms_receiver():
    """启动短信接收服务。"""
    from services.sms_receiver_service import get_sms_receiver_service
    from channels.drivers.ml307a import ML307ADriver

    config = get_config()
    raw_channels = config.raw.get("channels", {}) if hasattr(config, 'raw') else {}
    ml307a_config = raw_channels.get("ml307a", {})

    if not ml307a_config.get("enabled", False):
        return {"success": False, "message": "ML307A 短信功能未启用"}

    driver = ML307ADriver(ml307a_config)
    receiver = get_sms_receiver_service()
    receiver.set_driver(driver)
    receiver.start()

    return {"success": True, "message": "短信接收服务已启动"}


@router.post("/sms/receiver/stop")
def stop_sms_receiver():
    """停止短信接收服务。"""
    from services.sms_receiver_service import get_sms_receiver_service
    receiver = get_sms_receiver_service()
    receiver.stop()
    return {"success": True, "message": "短信接收服务已停止"}


# ── 数据库备份 API ──────────────────────────────────────────────────────

@router.post("/db/backup", response_model=BackupResponse)
def create_database_backup():
    """手动创建数据库备份。"""
    from database import get_db_path
    from migrations.base import backup_database

    db_path = get_db_path()
    if not os.path.exists(db_path):
        return BackupResponse(
            success=False,
            backup_path="",
            backup_size=0,
            message="数据库文件不存在"
        )

    try:
        backup_path = backup_database(db_path)
        backup_size = os.path.getsize(backup_path) if backup_path else 0

        return BackupResponse(
            success=True,
            backup_path=backup_path,
            backup_size=backup_size,
            message=f"备份成功，文件大小: {backup_size / 1024:.1f} KB"
        )
    except Exception as e:
        return BackupResponse(
            success=False,
            backup_path="",
            backup_size=0,
            message=f"备份失败: {str(e)}"
        )


@router.get("/db/backups", response_model=BackupListResponse)
def list_database_backups():
    """列出所有数据库备份文件。"""
    from database import get_db_path

    # 备份目录
    db_path = get_db_path()
    backup_dir = os.path.join(os.path.dirname(db_path), "..", "backups")

    if not os.path.exists(backup_dir):
        return BackupListResponse(backups=[], total=0)

    backups = []
    for f in os.listdir(backup_dir):
        if f.endswith(".db") and "backup" in f:
            filepath = os.path.join(backup_dir, f)
            stat = os.stat(filepath)
            backups.append({
                "filename": f,
                "path": filepath,
                "size": stat.st_size,
                "size_kb": stat.st_size / 1024,
                "created_at": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            })

    # 按时间倒序排列
    backups.sort(key=lambda x: x["created_at"], reverse=True)

    return BackupListResponse(backups=backups, total=len(backups))


@router.get("/db/version", response_model=DbVersionResponse)
def get_database_version():
    """获取数据库版本信息。"""
    from database import engine
    from migrations import CURRENT_DB_VERSION, MigrationManager

    manager = MigrationManager(engine)
    version_info = manager.get_version_info()

    return DbVersionResponse(
        current_version=version_info["current_db_version"],
        system_version=version_info["system_db_version"],
        needs_migration=version_info["needs_migration"]
    )


@router.post("/db/restore")
def restore_database_backup(filename: str):
    """从备份恢复数据库（需谨慎操作）。"""
    import shutil
    from database import get_db_path

    db_path = get_db_path()
    backup_dir = os.path.join(os.path.dirname(db_path), "..", "backups")
    backup_path = os.path.join(backup_dir, filename)

    if not os.path.exists(backup_path):
        return {"success": False, "message": f"备份文件不存在: {filename}"}

    try:
        # 恢复前先备份当前数据库
        from migrations.base import backup_database
        current_backup = backup_database(db_path)

        # 恢复备份
        shutil.copy2(backup_path, db_path)

        return {
            "success": True,
            "message": f"已从 {filename} 恢复数据库",
            "current_backup": current_backup,
            "warning": "恢复后请重启系统以应用变更"
        }
    except Exception as e:
        return {"success": False, "message": f"恢复失败: {str(e)}"}
