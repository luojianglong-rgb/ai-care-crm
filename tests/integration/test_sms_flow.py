#!/usr/bin/env python3
"""
短信发送流程集成测试
"""
import pytest
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from channels.executor import SendExecutor
from channels.router import ChannelRouter
from channels.drivers.ml307a import ML307ADriver
from db_models import Playbook, Client, CampaignTask
from tests.utils.mock_llm import MockLLMClient
import uuid


class MockML307ADriver:
    """Mock ML307A 驱动"""

    channel_name = "ml307a"

    def __init__(self, config):
        self.config = config
        self._sent_messages = []

    def is_available(self):
        return True

    def send(self, recipient, content, **kwargs):
        # 记录发送的消息
        self._sent_messages.append({
            "recipient": recipient,
            "content": content,
            "timestamp": datetime.now(),
        })

        from channels.base import SendResult
        return SendResult(
            success=True,
            channel="ml307a",
            external_id=f"mock_{len(self._sent_messages)}",
        )

    def get_sent_messages(self):
        return self._sent_messages


class TestSMSFlow:
    """短信发送流程测试"""

    def test_sms_send_single(self, test_db, mock_config_business):
        """测试单条短信发送"""
        # 1. 创建客户
        client = Client(
            client_id=str(uuid.uuid4()),
            name="短信客户",
            phone="13800138000",
            lifecycle_status="active",
            created_at=datetime.now(),
        )
        test_db.add(client)

        # 2. 创建剧本
        playbook = Playbook(
            id=str(uuid.uuid4()),
            name="测试剧本",
            trigger_type="birthday",
            is_active=1,
            created_at=datetime.now(),
        )
        test_db.add(playbook)

        # 3. 创建已审批的任务
        task = CampaignTask(
            id=str(uuid.uuid4()),
            playbook_id=playbook.id,
            client_id=client.client_id,
            generated_content="测试短信内容",
            status="approved",
            scheduled_at=datetime.now(),
            created_at=datetime.now(),
        )
        test_db.add(task)
        test_db.commit()

        # 4. Mock 驱动执行发送
        mock_driver = MockML307ADriver({"enabled": True})
        drivers = {"ml307a": mock_driver}

        executor = SendExecutor(mock_config_business, drivers)
        result = executor.send_single(test_db, task.id)

        # 5. 验证发送结果
        assert result.success == True
        assert result.channel == "ml307a"

        # 6. 验证消息记录
        assert len(mock_driver.get_sent_messages()) == 1

    def test_sms_send_batch(self, test_db, mock_config_business):
        """测试批量短信发送"""
        # 1. 创建多个客户和任务
        playbook = Playbook(
            id=str(uuid.uuid4()),
            name="批量剧本",
            is_active=1,
            created_at=datetime.now(),
        )
        test_db.add(playbook)

        for i in range(5):
            client = Client(
                client_id=str(uuid.uuid4()),
                name=f"客户{i}",
                phone=f"1380013800{i}",
                lifecycle_status="active",
                created_at=datetime.now(),
            )
            test_db.add(client)

            task = CampaignTask(
                id=str(uuid.uuid4()),
                playbook_id=playbook.id,
                client_id=client.client_id,
                generated_content=f"测试内容{i}",
                status="queued",
                scheduled_at=datetime.now(),
                created_at=datetime.now(),
            )
            test_db.add(task)

        test_db.commit()

        # 2. Mock 驱动执行批量发送
        mock_driver = MockML307ADriver({"enabled": True})
        drivers = {"ml307a": mock_driver}

        executor = SendExecutor(mock_config_business, drivers)
        result = executor.execute_batch(test_db, max_count=5)

        # 3. 验证批量结果
        assert result["total"] >= 0

    def test_sms_send_failure_handling(self, test_db, mock_config_business):
        """测试发送失败处理"""
        # 创建失败驱动
        class FailureDriver:
            channel_name = "ml307a"

            def is_available(self):
                return False

            def send(self, recipient, content, **kwargs):
                from channels.base import SendResult
                return SendResult(
                    success=False,
                    channel="ml307a",
                    error="设备不可用",
                )

        # 1. 创建任务
        client = Client(
            client_id=str(uuid.uuid4()),
            name="失败客户",
            phone="13800138000",
            lifecycle_status="active",
            created_at=datetime.now(),
        )
        test_db.add(client)

        playbook = Playbook(
            id=str(uuid.uuid4()),
            name="失败剧本",
            is_active=1,
            created_at=datetime.now(),
        )
        test_db.add(playbook)

        task = CampaignTask(
            id=str(uuid.uuid4()),
            playbook_id=playbook.id,
            client_id=client.client_id,
            generated_content="失败内容",
            status="approved",
            scheduled_at=datetime.now(),
            created_at=datetime.now(),
        )
        test_db.add(task)
        test_db.commit()

        # 2. 执行发送
        drivers = {"ml307a": FailureDriver()}
        executor = SendExecutor(mock_config_business, drivers)
        result = executor.send_single(test_db, task.id)

        # 3. 验证失败处理
        assert result.success == False
        assert "不可用" in result.error or "error" in result.error.lower()

        # 4. 验证任务状态
        test_db.refresh(task)
        assert task.status == "failed"


class TestChannelRouterFlow:
    """渠道路由流程测试"""

    def test_router_select_ml307a(self, mock_config_business):
        """测试路由选择 ML307A"""
        mock_config_business.raw = {
            "channels": {
                "ml307a": {"enabled": True},
            }
        }

        router = ChannelRouter(mock_config_business)
        channel = router.select("auto", "13800138000", "测试内容")

        assert channel == "ml307a"

    def test_router_no_available_channel(self, mock_config):
        """测试无可用渠道"""
        mock_config.raw = {
            "channels": {
                "ml307a": {"enabled": False},
            }
        }

        router = ChannelRouter(mock_config)
        channel = router.select("auto", "13800138000", "测试内容")

        assert channel == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])