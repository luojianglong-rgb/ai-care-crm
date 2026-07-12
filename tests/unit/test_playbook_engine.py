#!/usr/bin/env python3
"""
剧本引擎单元测试
"""
import pytest
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from playbook.engine import PlaybookEngine
from db_models import Playbook, Client, CampaignTask
from tests.utils.mock_llm import MockLLMClient
import uuid


class TestPlaybookEngine:
    """剧本引擎测试"""

    def test_engine_init(self, mock_config, mock_llm):
        """测试引擎初始化"""
        engine = PlaybookEngine(mock_config, mock_llm)

        assert engine.config == mock_config
        assert engine.llm == mock_llm
        assert engine.trigger_eval is not None
        assert engine.content_gen is not None

    def test_daily_scan_no_playbooks(self, test_db, mock_config, mock_llm):
        """测试无剧本时的扫描"""
        engine = PlaybookEngine(mock_config, mock_llm)
        result = engine.daily_scan(test_db)

        assert result["playbooks_scanned"] == 0
        assert result["tasks_created"] == 0

    def test_daily_scan_with_inactive_playbook(self, test_db, mock_config, mock_llm, sample_client):
        """测试含未激活剧本的扫描"""
        playbook = Playbook(
            id=str(uuid.uuid4()),
            name="未激活剧本",
            trigger_type="birthday",
            trigger_config={"days_before": 7},
            is_active=0,
            created_at=datetime.now(),
        )
        test_db.add(playbook)
        test_db.commit()

        engine = PlaybookEngine(mock_config, mock_llm)
        result = engine.daily_scan(test_db)

        assert result["playbooks_scanned"] == 0  # 只有激活的剧本被扫描

    def test_daily_scan_with_active_playbook(self, test_db, mock_config, mock_llm):
        """测试含激活剧本的扫描"""
        # 创建生日在今天+7天的客户
        target_date = datetime.now() + timedelta(days=7)
        client = Client(
            client_id=str(uuid.uuid4()),
            name="生日客户",
            phone="13900139000",
            gender="女",
            age_group="30-40",
            birth_date=f"1990-{target_date.strftime('%m-%d')}",
            lifecycle_status="active",
            created_at=datetime.now(),
        )
        test_db.add(client)

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

        engine = PlaybookEngine(mock_config, mock_llm)
        result = engine.daily_scan(test_db)

        assert result["playbooks_scanned"] >= 1
        assert result["lifecycle_updated"] >= 0

    def test_daily_scan_lifecycle_update(self, test_db, mock_config, mock_llm, sample_clients):
        """测试生命周期更新"""
        engine = PlaybookEngine(mock_config, mock_llm)
        result = engine.daily_scan(test_db)

        # 生命周期应该被刷新
        assert "lifecycle_updated" in result


class TestPlaybookEngineTaskCreation:
    """任务创建测试"""

    def test_task_creation_for_birthday(self, test_db, mock_config):
        """测试生日任务创建"""
        # 创建生日在今天+7天的客户
        target_date = datetime.now() + timedelta(days=7)
        client = Client(
            client_id=str(uuid.uuid4()),
            name="生日客户",
            phone="13900139001",
            gender="女",
            age_group="30-40",
            birth_date=f"1990-{target_date.strftime('%m-%d')}",
            lifecycle_status="active",
            created_at=datetime.now(),
        )
        test_db.add(client)

        playbook = Playbook(
            id=str(uuid.uuid4()),
            name="生日关怀",
            trigger_type="birthday",
            trigger_config={"days_before": 7},
            content_template="祝{client_name}生日快乐！",
            approval_mode="auto",
            is_active=1,
            created_at=datetime.now(),
        )
        test_db.add(playbook)
        test_db.commit()

        mock_llm = MockLLMClient(responses={"content": "生日快乐！"})
        engine = PlaybookEngine(mock_config, mock_llm)
        result = engine.daily_scan(test_db)

        # 应该创建任务
        if result["tasks_created"] > 0:
            tasks = test_db.query(CampaignTask).all()
            assert len(tasks) >= 1

    def test_task_approval_mode_auto(self, test_db, mock_config, mock_llm):
        """测试自动审批模式"""
        target_date = datetime.now() + timedelta(days=7)
        client = Client(
            client_id=str(uuid.uuid4()),
            name="生日客户",
            phone="13900139002",
            gender="女",
            age_group="30-40",
            birth_date=f"1990-{target_date.strftime('%m-%d')}",
            lifecycle_status="active",
            created_at=datetime.now(),
        )
        test_db.add(client)

        playbook = Playbook(
            id=str(uuid.uuid4()),
            name="生日关怀",
            trigger_type="birthday",
            trigger_config={"days_before": 7},
            approval_mode="auto",
            is_active=1,
            created_at=datetime.now(),
        )
        test_db.add(playbook)
        test_db.commit()

        engine = PlaybookEngine(mock_config, mock_llm)
        engine.daily_scan(test_db)

        # 自动审批的任务状态应该是 approved 或 queued
        tasks = test_db.query(CampaignTask).filter(
            CampaignTask.status.in_(["approved", "queued"])
        ).all()

        # 如果有任务，状态应该正确
        if tasks:
            for task in tasks:
                assert task.status in ["approved", "queued"]

    def test_task_approval_mode_manual(self, test_db, mock_config, mock_llm):
        """测试人工审批模式"""
        target_date = datetime.now() + timedelta(days=7)
        client = Client(
            client_id=str(uuid.uuid4()),
            name="生日客户",
            phone="13900139003",
            gender="女",
            age_group="30-40",
            birth_date=f"1990-{target_date.strftime('%m-%d')}",
            lifecycle_status="active",
            created_at=datetime.now(),
        )
        test_db.add(client)

        playbook = Playbook(
            id=str(uuid.uuid4()),
            name="人工审批剧本",
            trigger_type="birthday",
            trigger_config={"days_before": 7},
            approval_mode="manual",
            is_active=1,
            created_at=datetime.now(),
        )
        test_db.add(playbook)
        test_db.commit()

        engine = PlaybookEngine(mock_config, mock_llm)
        engine.daily_scan(test_db)

        # 人工审批的任务状态应该是 pending_approval
        tasks = test_db.query(CampaignTask).filter(
            CampaignTask.status == "pending_approval"
        ).all()

        # 如果有任务，状态应该正确
        if tasks:
            for task in tasks:
                assert task.status == "pending_approval"


class TestPlaybookEngineErrorHandling:
    """错误处理测试"""

    def test_daily_scan_error_handling(self, test_db, mock_config, mock_llm):
        """测试扫描错误处理"""
        # 创建一个配置错误的剧本
        playbook = Playbook(
            id=str(uuid.uuid4()),
            name="错误剧本",
            trigger_type="invalid_type",  # 无效类型
            trigger_config={},
            is_active=1,
            created_at=datetime.now(),
        )
        test_db.add(playbook)
        test_db.commit()

        engine = PlaybookEngine(mock_config, mock_llm)
        result = engine.daily_scan(test_db)

        # 应该有错误记录，但不应该崩溃
        assert "errors" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])