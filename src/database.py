"""
数据库连接和初始化模块
支持版本检查和自动迁移，确保客户数据安全。
"""
import os
import sys
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

logger = logging.getLogger(__name__)

# 数据库文件路径：支持 PyInstaller 打包环境
# 打包后：数据库在 EXE 同级的 data/ 目录
# 开发环境：在当前文件同目录
def get_db_path():
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller 打包环境：使用 EXE 所在目录下的 data
        exe_dir = os.path.dirname(sys.executable)
        db_dir = os.path.join(exe_dir, 'data')
        os.makedirs(db_dir, exist_ok=True)
        return os.path.join(db_dir, 'wellness_crm.db')
    else:
        # 开发环境：使用当前文件所在目录
        return os.path.join(os.path.dirname(__file__), 'wellness_crm.db')


SQLALCHEMY_DATABASE_URL = f"sqlite:///{get_db_path()}"

# SQLite 必须添加 check_same_thread=False
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


# 获取数据库会话的依赖函数
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    初始化数据库：检查版本、执行迁移、创建表。
    在 main.py 启动时调用。
    """
    # 导入所有模型确保表定义注册到 Base
    import db_models

    # 检查并执行迁移
    from migrations import MigrationManager
    db_path = get_db_path()
    manager = MigrationManager(engine, db_path)

    # 获取版本信息
    version_info = manager.get_version_info()
    logger.info(f"DB version: {version_info['current_db_version']}, System version: {version_info['system_db_version']}")

    # 执行迁移（如需要）
    if version_info['needs_migration']:
        logger.info(f"Migration needed: v{version_info['current_db_version']} → v{version_info['system_db_version']}")
        result = manager.check_and_migrate()
        if result['success']:
            logger.info(f"Migration completed: {result['migrations_run']}")
        else:
            logger.error(f"Migration failed: {result['error']}")
            raise Exception(f"数据库迁移失败: {result['error']}")

    # 创建所有表（新增表会自动创建）
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created/verified")
