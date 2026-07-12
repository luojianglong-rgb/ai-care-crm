#!/usr/bin/env python3
"""
剧本触发评估器单元测试
"""
import pytest
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from playbook.triggers import TriggerEvaluator
from db_models import Playbook, Client, ClientLifecycle
import uuid


class TestTriggerEvaluator:
    """触发评估器测试"""

    def test_evaluator_init(self):
        """测试评估器初始化"""
        evaluator = TriggerEvaluator()
        assert evaluator is not None

    def test_evaluate_birthday_trigger(self, test_db):
        """测试生日触发评估"""
        # 创建生日在今天+7天的客户
        birthday_date = (datetime.now() + timedelta(days=7)).strftime("%m-%d")
        client = Client(
            client_id=str(uuid.uuid4()),
            name="生日客户",
            phone="13900139000",
            gender="女",
            age_group="30-40",
            birth_date=f"1990-{birthday_date}",
            lifecycle_status="active",
            created_at=datetime.now(),
        )
        test_db.add(client)
        test_db.commit()

        # 创建生日剧本
        playbook = Playbook(
            id=str(uuid.uuid4()),
            name="生日关怀",
            trigger_type="birthday",
            trigger_config={"days_before": 7},
            is_active=1,
            created_at=datetime.now(),
        )
        test_db.add(playbook)
        test_db.commit()

        evaluator = TriggerEvaluator()
        client_ids = evaluator.evaluate(test_db, playbook)

        assert len(client_ids) >= 1
        assert client.client_id in client_ids

    def test_evaluate_time_since_visit_trigger(self, test_db):
        """测试距上次服务触发评估"""
        # 创建30天前有服务记录的客户
        client = Client(
            client_id=str(uuid.uuid4()),
            name="沉默客户",
            phone="13900139001",
            gender="女",
            age_group="30-40",
            lifecycle_status="at_risk",
            created_at=datetime.now() - timedelta(days=60),
        )
        test_db.add(client)
        test_db.commit()

        # 创建沉默唤醒剧本
        playbook = Playbook(
            id=str(uuid.uuid4()),
            name="沉默唤醒",
            trigger_type="time_since_visit",
            trigger_config={"min_days": 30},
            is_active=1,
            created_at=datetime.now(),
        )
        test_db.add(playbook)
        test_db.commit()

        evaluator = TriggerEvaluator()
        client_ids = evaluator.evaluate(test_db, playbook)

        # 沉默客户应该触发
        assert len(client_ids) >= 1

    def test_evaluate_inactive_playbook(self, test_db, sample_client):
        """测试未激活剧本不触发"""
        playbook = Playbook(
            id=str(uuid.uuid4()),
            name="未激活剧本",
            trigger_type="birthday",
            trigger_config={"days_before": 7},
            is_active=0,  # 未激活
            created_at=datetime.now(),
        )
        test_db.add(playbook)
        test_db.commit()

        evaluator = TriggerEvaluator()
        client_ids = evaluator.evaluate(test_db, playbook)

        assert len(client_ids) == 0

    def test_evaluate_empty_result(self, test_db):
        """测试无匹配客户"""
        playbook = Playbook(
            id=str(uuid.uuid4()),
            name="无客户剧本",
            trigger_type="birthday",
            trigger_config={"days_before": 365},  # 365天后，无客户
            is_active=1,
            created_at=datetime.now(),
        )
        test_db.add(playbook)
        test_db.commit()

        evaluator = TriggerEvaluator()
        client_ids = evaluator.evaluate(test_db, playbook)

        assert len(client_ids) == 0


class TestBirthdayTrigger:
    """生日触发详细测试"""

    def test_birthday_days_before_7(self, test_db):
        """测试生日前7天触发"""
        # 创建生日在7天后的客户
        target_date = datetime.now() + timedelta(days=7)
        client = Client(
            client_id=str(uuid.uuid4()),
            name="测试客户",
            phone="13900139002",
            gender="女",
            age_group="30-40",
            birth_date=f"1990-{target_date.strftime('%m-%d')}",
            lifecycle_status="active",
            created_at=datetime.now(),
        )
        test_db.add(client)
        test_db.commit()

        playbook = Playbook(
            id=str(uuid.uuid4()),
            name="生日关怀",
            trigger_type="birthday",
            trigger_config={"days_before": 7},
            is_active=1,
            created_at=datetime.now(),
        )
        test_db.add(playbook)
        test_db.commit()

        evaluator = TriggerEvaluator()
        client_ids = evaluator.evaluate(test_db, playbook)

        assert client.client_id in client_ids

    def test_birthday_days_before_3(self, test_db):
        """测试生日前3天触发"""
        target_date = datetime.now() + timedelta(days=3)
        client = Client(
            client_id=str(uuid.uuid4()),
            name="测试客户",
            phone="13900139003",
            gender="女",
            age_group="30-40",
            birth_date=f"1990-{target_date.strftime('%m-%d')}",
            lifecycle_status="active",
            created_at=datetime.now(),
        )
        test_db.add(client)
        test_db.commit()

        playbook = Playbook(
            id=str(uuid.uuid4()),
            name="生日关怀",
            trigger_type="birthday",
            trigger_config={"days_before": 3},
            is_active=1,
            created_at=datetime.now(),
        )
        test_db.add(playbook)
        test_db.commit()

        evaluator = TriggerEvaluator()
        client_ids = evaluator.evaluate(test_db, playbook)

        assert client.client_id in client_ids


class TestTimeSinceVisitTrigger:
    """距上次服务触发详细测试"""

    def test_min_days_30(self, test_db):
        """测试30天阈值"""
        # 创建生命周期为 at_risk 的客户
        client = Client(
            client_id=str(uuid.uuid4()),
            name="沉默客户",
            phone="13900139004",
            gender="女",
            age_group="30-40",
            lifecycle_status="at_risk",
            created_at=datetime.now() - timedelta(days=40),
        )
        test_db.add(client)
        test_db.commit()

        playbook = Playbook(
            id=str(uuid.uuid4()),
            name="沉默唤醒",
            trigger_type="time_since_visit",
            trigger_config={"min_days": 30},
            is_active=1,
            created_at=datetime.now(),
        )
        test_db.add(playbook)
        test_db.commit()

        evaluator = TriggerEvaluator()
        client_ids = evaluator.evaluate(test_db, playbook)

        # at_risk 状态的客户应该触发
        assert len(client_ids) >= 1

    def test_min_days_60(self, test_db):
        """测试60天阈值"""
        # 创建生命周期为 churned 的客户
        client = Client(
            client_id=str(uuid.uuid4()),
            name="流失客户",
            phone="13900139005",
            gender="女",
            age_group="30-40",
            lifecycle_status="churned",
            created_at=datetime.now() - timedelta(days=90),
        )
        test_db.add(client)
        test_db.commit()

        playbook = Playbook(
            id=str(uuid.uuid4()),
            name="流失挽回",
            trigger_type="time_since_visit",
            trigger_config={"min_days": 60},
            is_active=1,
            created_at=datetime.now(),
        )
        test_db.add(playbook)
        test_db.commit()

        evaluator = TriggerEvaluator()
        client_ids = evaluator.evaluate(test_db, playbook)

        # churned 状态的客户应该触发
        assert len(client_ids) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])