"""
数据库迁移模块
管理版本升级时的数据库结构迁移，确保客户数据安全。

迁移规则：
1. 迁移前必须备份
2. 新字段必须有默认值
3. 禁止删除表或字段
4. 迁移脚本按版本号命名
"""

from migrations.base import MigrationManager, get_db_version, run_migrations, CURRENT_DB_VERSION

__all__ = ["MigrationManager", "get_db_version", "run_migrations", "CURRENT_DB_VERSION"]