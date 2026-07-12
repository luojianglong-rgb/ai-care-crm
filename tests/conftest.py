#!/usr/bin/env python3
"""
AI-Care CRM Pytest 配置和共享 Fixtures
"""
import pytest
import os
import sys
import tempfile
from datetime import datetime

# 添加 src 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# ── 数据库 Fixtures ──────────────────────────────────────────────────────

@pytest.fixture(scope="function")
def test_db():
    """创建测试数据库（内存 SQLite）"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker, Session
    from database import Base

    # 使用内存数据库
    engine = create_engine("sqlite:///:memory:", echo=False)

    # 创建所有表
    Base.metadata.create_all(bind=engine)

    # 创建 session
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()

    yield session

    # 清理
    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def test_db_path():
    """创建临时数据库文件路径"""
    import tempfile
    fd, path = tempfile.mkstemp(suffix=".db")
    yield path
    os.close(fd)
    os.unlink(path)


# ── 配置 Fixtures ────────────────────────────────────────────────────────

@pytest.fixture(scope="function")
def mock_config():
    """创建测试配置（基础版）"""
    from config import AppConfig, StoreConfig, LLMConfig, ServerConfig, QuotaTier

    config = AppConfig(
        store=StoreConfig(name="测试门店", business_type="tcm_wellness"),
        server=ServerConfig(port=8888, dev_mode=False),
        llm=LLMConfig(api_key="test_key", provider="deepseek"),
        current_tier="basic",
    )
    config._quota_cache = {
        "basic": QuotaTier(
            max_clients=50,
            max_staff=3,
            ai_total_limit=20,
        ),
        "pro": QuotaTier(
            max_clients=-1,
            max_staff=-1,
            ai_weekly_limit=50,
            custom_playbooks=True,
        ),
        "business": QuotaTier(
            max_clients=-1,
            max_staff=-1,
            ai_analysis_per_month=-1,
            ai_plan_per_month=-1,
            ai_content_per_month=-1,
            custom_playbooks=True,
        ),
    }
    config.raw = {
        "channels": {
            "ml307a": {"enabled": False},
        }
    }
    return config


@pytest.fixture(scope="function")
def mock_config_pro():
    """创建测试配置（专业版）"""
    from config import AppConfig, StoreConfig, LLMConfig, ServerConfig, QuotaTier

    config = AppConfig(
        store=StoreConfig(name="测试门店", business_type="spa"),
        server=ServerConfig(port=8888, dev_mode=False),
        llm=LLMConfig(api_key="test_key", provider="deepseek"),
        current_tier="pro",
    )
    config._quota_cache = {
        "pro": QuotaTier(
            max_clients=-1,
            max_staff=-1,
            ai_weekly_limit=50,
            custom_playbooks=True,
        ),
    }
    return config


@pytest.fixture(scope="function")
def mock_config_business():
    """创建测试配置（至尊版）"""
    from config import AppConfig, StoreConfig, LLMConfig, ServerConfig, QuotaTier

    config = AppConfig(
        store=StoreConfig(name="测试门店", business_type="tcm_wellness"),
        server=ServerConfig(port=8888, dev_mode=False),
        llm=LLMConfig(api_key="test_key", provider="deepseek"),
        current_tier="business",
    )
    config._quota_cache = {
        "business": QuotaTier(
            max_clients=-1,
            max_staff=-1,
            ai_analysis_per_month=-1,
            ai_plan_per_month=-1,
            ai_content_per_month=-1,
            custom_playbooks=True,
            sms_monthly=100,
        ),
    }
    config.raw = {
        "channels": {
            "ml307a": {"enabled": True},
        }
    }
    return config


@pytest.fixture(scope="function")
def mock_config_dev():
    """创建测试配置（开发模式）"""
    from config import AppConfig, StoreConfig, LLMConfig, ServerConfig

    config = AppConfig(
        store=StoreConfig(name="测试门店", business_type="general"),
        server=ServerConfig(port=8888, dev_mode=True),
        llm=LLMConfig(api_key="test_key", provider="deepseek"),
        current_tier="basic",
    )
    return config


# ── LLM Mock Fixtures ─────────────────────────────────────────────────────

@pytest.fixture(scope="function")
def mock_llm():
    """Mock LLM 客户端"""
    from tests.utils.mock_llm import MockLLMClient
    return MockLLMClient()


@pytest.fixture(scope="function")
def mock_llm_with_response():
    """Mock LLM 客户端（带预设响应）"""
    from tests.utils.mock_llm import MockLLMClient

    responses = {
        "analysis": {
            "type": "气虚质",
            "description": "容易疲劳，气短懒言",
            "recommendations": ["补气健脾", "适度运动"]
        },
        "content": "亲爱的客户，祝您生日快乐！愿您身体健康，万事如意。",
        "reply_intent": {
            "intent": "appointment",
            "sentiment": "positive",
            "details": {"date": "明天下午"},
            "suggested_action": "创建预约"
        }
    }
    return MockLLMClient(responses=responses)


# ── 客户数据 Fixtures ─────────────────────────────────────────────────────

@pytest.fixture(scope="function")
def sample_client(test_db):
    """创建示例客户"""
    from db_models import Client
    import uuid

    client = Client(
        client_id=str(uuid.uuid4()),
        name="测试客户",
        phone="13800138000",
        gender="女",
        age_group="30-40",
        birth_date="1990-06-15",
        preferences=["艾灸", "推拿"],
        times_card_balance=10,
        cash_card_balance=500.0,
        lifecycle_status="active",
        created_at=datetime.now(),
    )
    test_db.add(client)
    test_db.commit()
    test_db.refresh(client)
    return client


@pytest.fixture(scope="function")
def sample_clients(test_db):
    """创建多个示例客户"""
    from db_models import Client
    import uuid

    clients = []
    for i in range(5):
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
        test_db.add(client)
        clients.append(client)

    test_db.commit()
    for c in clients:
        test_db.refresh(c)
    return clients


# ── Playbook Fixtures ─────────────────────────────────────────────────────

@pytest.fixture(scope="function")
def sample_playbook(test_db):
    """创建示例剧本"""
    from db_models import Playbook
    import uuid

    playbook = Playbook(
        id=str(uuid.uuid4()),
        name="生日关怀",
        trigger_type="birthday",
        trigger_config={"days_before": 7},
        content_template="祝您生日快乐！",
        approval_mode="auto",
        is_active=1,
        created_at=datetime.now(),
    )
    test_db.add(playbook)
    test_db.commit()
    test_db.refresh(playbook)
    return playbook


# ── Admin User Fixtures ────────────────────────────────────────────────────

@pytest.fixture(scope="function")
def sample_admin(test_db):
    """创建示例管理员"""
    from db_models import AdminUser
    import bcrypt

    hashed = bcrypt.hashpw("admin".encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    admin = AdminUser(
        username="admin",
        password_hash=hashed,
        display_name="管理员",
    )
    test_db.add(admin)
    test_db.commit()
    test_db.refresh(admin)
    return admin


# ── Playwright Fixtures (保留原有) ────────────────────────────────────────

@pytest.fixture(scope="session")
def browser_context_args():
    """浏览器上下文配置"""
    return {
        "viewport": {"width": 1920, "height": 1080},
    }


# ── 真实 LLM Fixtures (使用 config.yaml 配置) ────────────────────────────────

@pytest.fixture(scope="session")
def real_llm():
    """真实 LLM 客户端（使用 config.yaml 配置）"""
    from ai.llm_client import LLMClient
    from config import get_config

    config = get_config()
    client = LLMClient(config)

    if not client.is_available:
        pytest.skip("LLM API 未配置，跳过真实 LLM 测试")

    return client


@pytest.fixture(scope="session")
def real_config():
    """真实配置（从 config.yaml 加载）"""
    from config import get_config
    return get_config()


@pytest.fixture(scope="function")
def real_db():
    """真实数据库连接（测试用临时数据库）"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from database import Base
    # 导入所有模型确保表定义注册到 Base
    import db_models
    import tempfile

    # 创建临时数据库文件
    fd, path = tempfile.mkstemp(suffix="_test.db")
    os.close(fd)

    engine = create_engine(f"sqlite:///{path}", echo=False)
    # 创建所有表（包括 ai_usage_records）
    Base.metadata.create_all(bind=engine)

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()

    yield session

    session.close()
    try:
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
        os.unlink(path)
    except:
        pass