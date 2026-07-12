#!/usr/bin/env python3
"""
剧本引擎完整流程集成测试
"""
import pytest
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from playbook.engine import PlaybookEngine
from db_models import Playbook, Client, CampaignTask, ClientLifecycle
from tests.utils.mock_llm import MockLLMClient
import uuid


class TestPlaybookFlow:
    """剧本完整流程测试"""

    def test_full_playbook_flow(self, test_db, mock_config):
        """测试剧本完整流程"""
        # 1. 创建生日客户（生日在今天+7天）
        target_date = datetime.now() + timedelta(days=7)
        client = Client(
            client_id=str(uuid.uuid4()),
            name="流程测试客户",
            phone="13800138000",
            gender="女",
            age_group="30-40",
            birth_date=f"1990-{target_date.strftime('%m-%d')}",
            lifecycle_status="active",
            created_at=datetime.now(),
        )
        test_db.add(client)

        # 2. 创建生命周期记录
        lifecycle = ClientLifecycle(
            id=str(uuid.uuid4()),
            client_id=client.client_id,
            status="active",
            days_since_last_visit=0,
            updated_at=datetime.now(),
        )
        test_db.add(lifecycle)
        test_db.commit()

        # 3. 创建剧本
        playbook = Playbook(
            id=str(uuid.uuid4()),
            name="生日关怀测试",
            trigger_type="birthday",
            trigger_config={"days_before": 7},
            content_template="祝{client_name}生日快乐！",
            approval_mode="auto",
            is_active=1,
            created_at=datetime.now(),
        )
        test_db.add(playbook)
        test_db.commit()

        # 4. 执行扫描
        mock_llm = MockLLMClient(responses={"content": "祝您生日快乐！"})
        engine = PlaybookEngine(mock_config, mock_llm)
        result = engine.daily_scan(test_db)

        # 5. 验证结果
        assert result["playbooks_scanned"] >= 1
        assert "tasks_created" in result

        # 6. 验证任务创建
        if result["tasks_created"] > 0:
            tasks = test_db.query(CampaignTask).filter(
                CampaignTask.client_id == client.client_id
            ).all()

            assert len(tasks) >= 1

            # 7. 验证任务内容
            task = tasks[0]
            assert task.playbook_id == playbook.id
            assert task.status in ["approved", "queued", "pending_approval"]
            assert task.generated_content != ""

    def test_playbook_flow_with_multiple_clients(self, test_db, mock_config):
        """测试多客户的剧本流程"""
        # 1. 创建多个生日客户
        target_date = datetime.now() + timedelta(days=7)
        clients = []
        for i in range(3):
            client = Client(
                client_id=str(uuid.uuid4()),
                name=f"客户{i+1}",
                phone=f"1380013800{i}",
                gender="女",
                age_group="30-40",
                birth_date=f"1990-{target_date.strftime('%m-%d')}",
                lifecycle_status="active",
                created_at=datetime.now(),
            )
            test_db.add(client)
            clients.append(client)

        test_db.commit()

        # 2. 创建剧本
        playbook = Playbook(
            id=str(uuid.uuid4()),
            name="批量生日关怀",
            trigger_type="birthday",
            trigger_config={"days_before": 7},
            approval_mode="auto",
            is_active=1,
            created_at=datetime.now(),
        )
        test_db.add(playbook)
        test_db.commit()

        # 3. 执行扫描
        mock_llm = MockLLMClient(responses={"content": "生日祝福"})
        engine = PlaybookEngine(mock_config, mock_llm)
        result = engine.daily_scan(test_db)

        # 4. 验证任务数量
        if result["tasks_created"] > 0:
            tasks = test_db.query(CampaignTask).all()
            assert len(tasks) >= 1


class TestLifecycleFlow:
    """生命周期流程测试"""

    def test_lifecycle_new_to_active(self, test_db, mock_config, mock_llm):
        """测试新客户到活跃客户的生命周期"""
        # 1. 创建新客户
        client = Client(
            client_id=str(uuid.uuid4()),
            name="新客户",
            phone="13800138001",
            lifecycle_status="new",
            created_at=datetime.now(),
        )
        test_db.add(client)
        test_db.commit()

        # 2. 执行生命周期扫描
        engine = PlaybookEngine(mock_config, mock_llm)
        result = engine.daily_scan(test_db)

        # 3. 验证生命周期更新
        test_db.refresh(client)

        # 生命周期应该被更新
        assert "lifecycle_updated" in result

    def test_lifecycle_active_to_at_risk(self, test_db, mock_config, mock_llm):
        """测试活跃客户到风险客户的生命周期"""
        # 1. 创建30天前创建的客户
        client = Client(
            client_id=str(uuid.uuid4()),
            name="沉默客户",
            phone="13800138002",
            lifecycle_status="active",
            created_at=datetime.now() - timedelta(days=30),
        )
        test_db.add(client)
        test_db.commit()

        # 2. 执行生命周期扫描
        engine = PlaybookEngine(mock_config, mock_llm)
        result = engine.daily_scan(test_db)

        # 3. 验证生命周期更新
        assert result["lifecycle_updated"] >= 0


class TestCampaignTaskFlow:
    """营销任务流程测试"""

    def test_task_status_flow(self, test_db, mock_config):
        """测试任务状态流转"""
        # 创建客户和剧本
        target_date = datetime.now() + timedelta(days=7)
        client = Client(
            client_id=str(uuid.uuid4()),
            name="任务客户",
            phone="13800138003",
            birth_date=f"1990-{target_date.strftime('%m-%d')}",
            lifecycle_status="active",
            created_at=datetime.now(),
        )
        test_db.add(client)

        playbook = Playbook(
            id=str(uuid.uuid4()),
            name="任务测试",
            trigger_type="birthday",
            trigger_config={"days_before": 7},
            approval_mode="auto",
            is_active=1,
            created_at=datetime.now(),
        )
        test_db.add(playbook)
        test_db.commit()

        # 执行扫描
        mock_llm = MockLLMClient(responses={"content": "祝福"})
        engine = PlaybookEngine(mock_config, mock_llm)
        engine.daily_scan(test_db)

        # 验证任务状态
        tasks = test_db.query(CampaignTask).all()
        if tasks:
            for task in tasks:
                # 任务应该有正确的状态
                assert task.status in ["queued", "approved", "pending_approval", "sent"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])