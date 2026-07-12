#!/usr/bin/env python3
"""
客户服务单元测试
"""
import pytest
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from services.client_service import ClientService
from models import ClientCreate, ClientUpdate, WalletAction, HealthRecord, HealthRecordUpdate
from db_models import Client


class TestClientServiceCreate:
    """客户创建测试"""

    def test_create_client_success(self, test_db):
        """测试创建客户成功"""
        client_in = ClientCreate(
            name="新客户",
            phone="13900139000",
            gender="女",
            age_group="20-30",
            preferences=["艾灸", "推拿"],
        )

        client = ClientService.create_client(test_db, client_in)

        assert client.name == "新客户"
        assert client.phone == "13900139000"
        assert client.gender == "女"
        assert client.preferences == ["艾灸", "推拿"]

    def test_create_client_with_birth_date(self, test_db):
        """测试创建带出生日期的客户"""
        client_in = ClientCreate(
            name="生日客户",
            phone="13900139001",
            gender="男",
            age_group="30-40",
            birth_date="1990-06-15",
        )

        client = ClientService.create_client(test_db, client_in)

        assert client.birth_date == "1990-06-15"

    def test_create_client_with_card_balance(self, test_db):
        """测试创建带储值余额的客户"""
        client_in = ClientCreate(
            name="储值客户",
            phone="13900139002",
            gender="女",
            age_group="40-50",
            times_card_balance=20,
            cash_card_balance=1000.0,
        )

        client = ClientService.create_client(test_db, client_in)

        assert client.times_card_balance == 20
        assert client.cash_card_balance == 1000.0


class TestClientServiceGet:
    """客户查询测试"""

    def test_get_all_clients(self, test_db, sample_clients):
        """测试获取所有客户"""
        clients = ClientService.get_all_clients(test_db)

        assert len(clients) >= 5
        assert all(c.name.startswith("测试客户") for c in clients)

    def test_get_client_by_id(self, test_db, sample_client):
        """测试按ID获取客户"""
        client = ClientService.get_client(test_db, sample_client.client_id)

        assert client is not None
        assert client.name == "测试客户"

    def test_get_client_not_found(self, test_db):
        """测试获取不存在的客户"""
        client = ClientService.get_client(test_db, "nonexistent_id")

        assert client is None


class TestClientServiceUpdate:
    """客户更新测试"""

    def test_update_client_name(self, test_db, sample_client):
        """测试更新客户姓名"""
        update = ClientUpdate(name="新名字")
        client = ClientService.update_client(test_db, sample_client.client_id, update)

        assert client.name == "新名字"

    def test_update_client_phone(self, test_db, sample_client):
        """测试更新客户电话"""
        update = ClientUpdate(phone="13700137000")
        client = ClientService.update_client(test_db, sample_client.client_id, update)

        assert client.phone == "13700137000"

    def test_update_client_preferences(self, test_db, sample_client):
        """测试更新客户偏好"""
        update = ClientUpdate(preferences=["按摩", "SPA"])
        client = ClientService.update_client(test_db, sample_client.client_id, update)

        assert client.preferences == ["按摩", "SPA"]

    def test_update_client_not_found(self, test_db):
        """测试更新不存在的客户"""
        update = ClientUpdate(name="不存在")
        client = ClientService.update_client(test_db, "nonexistent_id", update)

        assert client is None


class TestClientServiceWallet:
    """钱包操作测试"""

    def test_update_wallet_times_recharge(self, test_db, sample_client):
        """测试次卡充值"""
        action = WalletAction(
            amount=10,
            action_type="times",
            notes="充值10次",
            cash_amount=500.0,
        )

        client = ClientService.update_wallet(test_db, sample_client.client_id, action)

        assert client.times_card_balance == 20  # 原有10 + 充值10

    def test_update_wallet_cash_recharge(self, test_db, sample_client):
        """测试现金充值"""
        action = WalletAction(
            amount=1000.0,
            action_type="cash",
            notes="充值1000元",
        )

        client = ClientService.update_wallet(test_db, sample_client.client_id, action)

        assert client.cash_card_balance == 1500.0  # 原有500 + 充值1000

    def test_update_wallet_client_not_found(self, test_db):
        """测试钱包操作客户不存在"""
        action = WalletAction(amount=100, action_type="times")
        client = ClientService.update_wallet(test_db, "nonexistent_id", action)

        assert client is None


class TestClientServiceHealthRecord:
    """健康档案测试"""

    def test_add_health_record_success(self, test_db, sample_client):
        """测试添加健康档案成功"""
        record = HealthRecord(
            symptoms=["疲乏", "失眠"],
            description="最近睡眠质量差",
            treatment_provided="艾灸调理",
            deduct_times=1,
            deduct_cash=100.0,
            notes="首次调理",
        )

        db_record = ClientService.add_health_record(test_db, sample_client.client_id, record)

        assert db_record is not None
        assert db_record.symptoms == ["疲乏", "失眠"]
        assert db_record.treatment_provided == "艾灸调理"

    def test_add_health_record_deduct_times(self, test_db, sample_client):
        """测试健康档案扣减次数"""
        original_balance = sample_client.times_card_balance

        record = HealthRecord(
            symptoms=["腰痛"],
            description="腰部不适",
            treatment_provided="推拿",
            deduct_times=2,
            deduct_cash=0,
        )

        ClientService.add_health_record(test_db, sample_client.client_id, record)

        # 刷新客户
        test_db.refresh(sample_client)
        assert sample_client.times_card_balance == original_balance - 2

    def test_add_health_record_deduct_cash(self, test_db, sample_client):
        """测试健康档案扣减现金"""
        original_balance = sample_client.cash_card_balance

        record = HealthRecord(
            symptoms=["肩颈僵硬"],
            description="肩颈不适",
            treatment_provided="按摩",
            deduct_times=0,
            deduct_cash=200.0,
        )

        ClientService.add_health_record(test_db, sample_client.client_id, record)

        # 刷新客户
        test_db.refresh(sample_client)
        assert sample_client.cash_card_balance == original_balance - 200.0

    def test_add_health_record_client_not_found(self, test_db):
        """测试健康档案客户不存在"""
        record = HealthRecord(
            symptoms=["头痛"],
            description="头部不适",
            treatment_provided="刮痧",
            deduct_times=1,
            deduct_cash=0,
        )

        result = ClientService.add_health_record(test_db, "nonexistent_id", record)

        assert result is None

    def test_update_health_record(self, test_db, sample_client):
        """测试更新健康档案"""
        # 先创建档案
        record = HealthRecord(
            symptoms=["头痛"],
            description="头痛症状",
            treatment_provided="刮痧",
            deduct_times=1,
            deduct_cash=0,
        )
        db_record = ClientService.add_health_record(test_db, sample_client.client_id, record)

        # 更新档案
        update = HealthRecordUpdate(
            symptoms=["头痛", "失眠"],
            notes="症状改善",
        )
        updated = ClientService.update_health_record(test_db, db_record.record_id, update)

        assert updated.symptoms == ["头痛", "失眠"]
        assert updated.notes == "症状改善"


class TestClientServiceDelete:
    """客户删除测试"""

    def test_delete_client_success(self, test_db, sample_client):
        """测试删除客户成功"""
        result = ClientService.delete_client(test_db, sample_client.client_id)

        assert result == True

        # 验证已删除
        client = ClientService.get_client(test_db, sample_client.client_id)
        assert client is None

    def test_delete_client_not_found(self, test_db):
        """测试删除不存在的客户"""
        result = ClientService.delete_client(test_db, "nonexistent_id")

        assert result == False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])