"""
数据库迁移基础模块
提供版本检查、备份、迁移执行等核心功能。
"""
import os
import shutil
import logging
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# 当前系统版本（与 config.yaml 中的 db_version 对应）
CURRENT_DB_VERSION = 2  # v2 包含 AI智能触达 + 节假日关怀 新增字段

# 迁移脚本注册表（版本号 → 迁移函数）
MIGRATIONS = {}


def register_migration(version: int, func):
    """注册迁移脚本"""
    MIGRATIONS[version] = func


def get_db_version(engine) -> int:
    """获取数据库当前版本号"""
    # 检查是否存在版本表
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version FROM db_meta LIMIT 1"))
            row = result.fetchone()
            if row:
                return row[0]
    except Exception:
        # 表不存在，返回版本 0
        pass
    return 0


def set_db_version(engine, version: int):
    """设置数据库版本号"""
    with engine.connect() as conn:
        # 确保表存在
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS db_meta (
                version INTEGER PRIMARY KEY,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """))
        # 更新版本
        conn.execute(text("""
            INSERT OR REPLACE INTO db_meta (version, updated_at)
            VALUES (:version, :timestamp)
        """), {"version": version, "timestamp": datetime.now().isoformat()})
        conn.commit()


def backup_database(db_path: str) -> str:
    """备份数据库文件"""
    if not os.path.exists(db_path):
        logger.warning(f"Database file not found: {db_path}")
        return ""

    # 创建备份目录
    backup_dir = os.path.join(os.path.dirname(db_path), "..", "backups")
    os.makedirs(backup_dir, exist_ok=True)

    # 生成备份文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    current_version = 0
    try:
        from sqlalchemy import create_engine
        engine = create_engine(f"sqlite:///{db_path}")
        current_version = get_db_version(engine)
    except Exception:
        pass

    backup_name = f"wellness_crm_v{current_version}_backup_{timestamp}.db"
    backup_path = os.path.join(backup_dir, backup_name)

    # 执行备份
    shutil.copy2(db_path, backup_path)
    logger.info(f"Database backed up to: {backup_path}")

    return backup_path


def run_migrations(engine, db_path: str = None) -> dict:
    """
    执行数据库迁移
    Args:
        engine: SQLAlchemy engine
        db_path: 数据库文件路径（用于备份）
    Returns:
        {"success": bool, "migrations_run": list, "backup_path": str, "error": str}
    """
    current_version = get_db_version(engine)
    result = {
        "success": True,
        "migrations_run": [],
        "backup_path": "",
        "error": "",
        "from_version": current_version,
        "to_version": CURRENT_DB_VERSION,
    }

    if current_version >= CURRENT_DB_VERSION:
        logger.info(f"Database already at version {current_version}, no migration needed")
        return result

    # 备份数据库
    if db_path:
        try:
            result["backup_path"] = backup_database(db_path)
        except Exception as e:
            result["success"] = False
            result["error"] = f"Backup failed: {e}"
            logger.error(result["error"])
            return result

    # 执行迁移
    for version in range(current_version + 1, CURRENT_DB_VERSION + 1):
        migration_func = MIGRATIONS.get(version)
        if migration_func:
            try:
                logger.info(f"Running migration to version {version}")
                migration_func(engine)
                set_db_version(engine, version)
                result["migrations_run"].append(version)
                logger.info(f"Migration to version {version} completed")
            except Exception as e:
                result["success"] = False
                result["error"] = f"Migration to version {version} failed: {e}"
                logger.error(result["error"])

                # 尝试恢复备份
                if result["backup_path"] and db_path:
                    try:
                        shutil.copy2(result["backup_path"], db_path)
                        logger.info("Database restored from backup")
                    except Exception as restore_error:
                        logger.error(f"Restore failed: {restore_error}")

                return result
        else:
            logger.warning(f"No migration script for version {version}")

    result["success"] = True
    return result


class MigrationManager:
    """迁移管理器（供 main.py 调用）"""

    def __init__(self, engine, db_path: str = None):
        self.engine = engine
        self.db_path = db_path

    def check_and_migrate(self) -> dict:
        """检查版本并执行迁移"""
        return run_migrations(self.engine, self.db_path)

    def get_version_info(self) -> dict:
        """获取版本信息"""
        current = get_db_version(self.engine)
        return {
            "current_db_version": current,
            "system_db_version": CURRENT_DB_VERSION,
            "needs_migration": current < CURRENT_DB_VERSION,
            "migration_count": CURRENT_DB_VERSION - current if current < CURRENT_DB_VERSION else 0,
        }


# ── 迁移脚本 ──────────────────────────────────────────────

def migration_v0_to_v1(engine):
    """
    v0 → v1 迁移（初始版本）
    创建 db_meta 版本表，记录初始版本。
    """
    with engine.connect() as conn:
        # 创建版本表
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS db_meta (
                version INTEGER PRIMARY KEY,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.commit()
    logger.info("Migration v0 → v1 completed (db_meta table created)")


def migration_v1_to_v2(engine):
    """
    v1 → v2 迁移
    新增字段：
    - CampaignTask: ai_content_type, ai_reason
    - CampaignTask: playbook_id nullable

    新增触发类型：
    - holiday, holiday_greeting
    """
    with engine.connect() as conn:
        # 1. CampaignTask 新增字段
        try:
            conn.execute(text("""
                ALTER TABLE campaign_tasks
                ADD COLUMN ai_content_type TEXT DEFAULT NULL
            """))
            logger.info("Added ai_content_type to campaign_tasks")
        except Exception as e:
            if "duplicate column" not in str(e).lower():
                logger.warning(f"ai_content_type may already exist: {e}")

        try:
            conn.execute(text("""
                ALTER TABLE campaign_tasks
                ADD COLUMN ai_reason TEXT DEFAULT NULL
            """))
            logger.info("Added ai_reason to campaign_tasks")
        except Exception as e:
            if "duplicate column" not in str(e).lower():
                logger.warning(f"ai_reason may already exist: {e}")

        conn.commit()

    logger.info("Migration v1 → v2 completed")


# 注册迁移脚本
register_migration(1, migration_v0_to_v1)
register_migration(2, migration_v1_to_v2)