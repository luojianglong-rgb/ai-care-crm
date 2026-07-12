#!/usr/bin/env python3
"""
AI-Care CRM API 测试
"""
import pytest
import requests
import time

BASE_URL = "http://localhost:8888"
TOKEN = None


@pytest.fixture(scope="module")
def auth_token():
    """获取认证 token"""
    global TOKEN
    if TOKEN:
        return TOKEN

    response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
        "username": "admin",
        "password": "admin"
    })
    assert response.status_code == 200
    data = response.json()
    TOKEN = data.get("token")
    return TOKEN


class TestAuth:
    """认证模块测试"""

    def test_login_success(self):
        """测试登录成功"""
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "username": "admin",
            "password": "admin"
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["username"] == "admin"

    def test_login_failure_wrong_password(self):
        """测试登录失败 - 密码错误"""
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "username": "admin",
            "password": "wrongpassword"
        })
        assert response.status_code == 401

    def test_login_failure_wrong_username(self):
        """测试登录失败 - 用户名错误"""
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "username": "nonexistent",
            "password": "admin"
        })
        assert response.status_code == 401


class TestSystem:
    """系统接口测试"""

    def test_ping(self):
        """测试健康检查接口"""
        response = requests.get(f"{BASE_URL}/api/v1/ping")
        assert response.status_code == 200
        data = response.json()
        assert data["ping"] == "pong"

    def test_root(self):
        """测试根路径"""
        response = requests.get(f"{BASE_URL}/")
        assert response.status_code == 200


class TestClients:
    """客户档案模块测试"""

    def test_get_clients_list(self, auth_token):
        """测试获取客户列表"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/v1/clients/", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestBookings:
    """预约排班模块测试"""

    def test_get_bookings_list(self, auth_token):
        """测试获取预约列表"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/v1/bookings/", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestInventory:
    """库存耗材模块测试"""

    def test_get_inventory_list(self, auth_token):
        """测试获取库存列表"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/v1/inventory/", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestBilling:
    """财务收银模块测试"""

    def test_get_billing_list(self, auth_token):
        """测试获取账单列表"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/v1/billing/", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestServices:
    """服务项目模块测试"""

    def test_get_services_list(self, auth_token):
        """测试获取服务列表"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/v1/services/", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestWAP:
    """WAP 手机端模块测试"""

    def test_wap_index(self):
        """测试 WAP 首页"""
        response = requests.get(f"{BASE_URL}/wap/")
        assert response.status_code == 200


class TestDashboard:
    """驾驶舱模块测试"""

    def test_dashboard_data(self, auth_token):
        """测试驾驶舱数据接口"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/v1/dashboard/today", headers=headers)
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
