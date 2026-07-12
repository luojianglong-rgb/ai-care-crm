#!/usr/bin/env python3
"""
测试数据库工具
提供数据库创建、清理、数据初始化功能
"""
import os
import tempfile
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 添加 src 目录到路径
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from database import Base
from db_models import Client, AdminUser, Playbook, ServiceItem, InventoryCategory
import bcrypt
import uuid
from datetime import datetime


class TestDatabase:
    """测试数据库管理器"""

    def __init__(self, db_path: str = None, in_memory: bool = True):
        """
        Args:
            db_path: 数据库文件路径（None 使用临时文件）
            in_memory: 是否使用内存数据库
        """
        if in_memory:
            self.engine = create_engine("sqlite:///:memory:", echo=False)
        else:
            if db_path is None:
                fd, db_path = tempfile.mkstemp(suffix=".db")
                os.close(fd)
            self.engine = create_engine(f"sqlite:///{db_path}", echo=False)
            self.db_path = db_path

        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.session = None

    def create_tables(self):
        """创建所有表"""
        Base.metadata.create_all(bind=self.engine)

    def drop_tables(self):
        """删除所有表"""
        Base.metadata.drop_all(bind=self.engine)

    def get_session(self):
        """获取 Session"""
        if self.session is None:
            self.session = self.SessionLocal()
        return self.session

    def close(self):
        """关闭连接"""
        if self.session:
            self.session.close()
            self.session = None

    def cleanup(self):
        """清理数据库"""
        self.close()
        self.drop_tables()
        if hasattr(self, 'db_path') and self.db_path:
            try:
                os.unlink(self.db_path)
            except:
                pass

    # ── 数据初始化 ────────────────────────────────────────────────────────

    def init_admin(self, username: str = "admin", password: str = "admin"):
        """创建管理员"""
        session = self.get_session()
        hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        admin = AdminUser(
            username=username,
            password_hash=hashed,
            display_name=username,
        )
        session.add(admin)
        session.commit()
        return admin

    def init_client(self, name: str = "测试客户", phone: str = "13800138000",
                    gender: str = "女", age_group: str = "30-40",
                    times_balance: int = 10, cash_balance: float = 500.0,
                    birth_date: str = None):
        """创建客户"""
        session = self.get_session()
        client = Client(
            client_id=str(uuid.uuid4()),
            name=name,
            phone=phone,
            gender=gender,
            age_group=age_group,
            birth_date=birth_date or "1990-06-15",
            preferences=["艾灸"],
            times_card_balance=times_balance,
            cash_card_balance=cash_balance,
            lifecycle_status="active",
            created_at=datetime.now(),
        )
        session.add(client)
        session.commit()
        session.refresh(client)
        return client

    def init_clients_batch(self, count: int = 5):
        """批量创建客户"""
        session = self.get_session()
        clients = []
        for i in range(count):
            client = Client(
                client_id=str(uuid.uuid4()),
                name=f"测试客户{i+1}",
                phone=f"1380013800{i}",
                gender="女" if i % 2 == 0 else "男",
                age_group="30-40",
                birth_date=f"1990-0{i+1}-15",
                preferences=["艾灸"],
                times_card_balance=10,
                cash_card_balance=500.0,
                lifecycle_status="active",
                created_at=datetime.now(),
            )
            session.add(client)
            clients.append(client)
        session.commit()
        for c in clients:
            session.refresh(c)
        return clients

    def init_playbook(self, name: str = "生日关怀", trigger_type: str = "birthday",
                      trigger_config: dict = None, is_active: int = 1):
        """创建剧本"""
        session = self.get_session()
        playbook = Playbook(
            id=str(uuid.uuid4()),
            name=name,
            trigger_type=trigger_type,
            trigger_config=trigger_config or {"days_before": 7},
            content_template="祝您生日快乐！",
            approval_mode="auto",
            is_active=is_active,
            created_at=datetime.now(),
        )
        session.add(playbook)
        session.commit()
        session.refresh(playbook)
        return playbook

    def init_service_item(self, name: str = "艾灸", description: str = "温经散寒"):
        """创建服务项目"""
        session = self.get_session()
        item = ServiceItem(
            item_id=str(uuid.uuid4()),
            name=name,
            description=description,
            is_active=1,
        )
        session.add(item)
        session.commit()
        session.refresh(item)
        return item

    def init_categories(self):
        """创建默认耗材分类"""
        session = self.get_session()
        categories = [
            {"name": "日常耗材", "description": "日常基础耗材"},
            {"name": "精油/原液", "description": "按摩精油、护肤原液"},
            {"name": "院线售卖产品", "description": "面向客户销售的产品"},
        ]
        for cat in categories:
            existing = session.query(InventoryCategory).filter(
                InventoryCategory.name == cat["name"]
            ).first()
            if not existing:
                category = InventoryCategory(**cat, is_active=1)
                session.add(category)
        session.commit()


# ── 便捷函数 ────────────────────────────────────────────────────────────

def create_test_db() -> TestDatabase:
    """创建内存测试数据库"""
    db = TestDatabase(in_memory=True)
    db.create_tables()
    return db


def create_test_db_with_data() -> TestDatabase:
    """创建带初始数据的测试数据库"""
    db = create_test_db()
    db.init_admin()
    db.init_client()
    db.init_playbook()
    return db