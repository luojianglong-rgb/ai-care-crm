#!/usr/bin/env python3
"""
AI-Care CRM UI 测试
"""
import pytest
from playwright.sync_api import Page, expect

BASE_URL = "http://localhost:8888"


class TestLogin:
    """登录页面测试"""

    def test_login_page_loads(self, page: Page):
        """测试登录页面加载"""
        page.goto(f"{BASE_URL}/login")
        expect(page).to_have_title("AI-Care CRM")
        expect(page.locator("input[name='username']")).to_be_visible()
        expect(page.locator("input[name='password']")).to_be_visible()

    def test_login_success(self, page: Page):
        """测试登录成功"""
        page.goto(f"{BASE_URL}/login")
        page.fill("input[name='username']", "admin")
        page.fill("input[name='password']", "admin")
        page.click("button[type='submit']")
        page.wait_for_url(f"{BASE_URL}/")
        expect(page).to_have_url(f"{BASE_URL}/")

    def test_login_failure_wrong_password(self, page: Page):
        """测试登录失败 - 密码错误"""
        page.goto(f"{BASE_URL}/login")
        page.fill("input[name='username']", "admin")
        page.fill("input[name='password']", "wrongpassword")
        page.click("button[type='submit']")
        # 应该显示错误消息
        expect(page.locator(".ant-message-error, .error")).to_be_visible(timeout=5000)


class TestNavigation:
    """导航菜单测试"""

    def test_dashboard_link(self, page: Page):
        """测试驾驶舱链接"""
        page.goto(f"{BASE_URL}/login")
        page.fill("input[name='username']", "admin")
        page.fill("input[name='password']", "admin")
        page.click("button[type='submit']")
        page.wait_for_url(f"{BASE_URL}/")

        # 点击驾驶舱链接
        page.click("a[href='/dashboard'], .ant-menu-item:has-text('驾驶舱')")
        page.wait_for_url(f"{BASE_URL}/dashboard")
        expect(page).to_have_url(f"{BASE_URL}/dashboard")

    def test_clients_link(self, page: Page):
        """测试客户档案链接"""
        page.goto(f"{BASE_URL}/login")
        page.fill("input[name='username']", "admin")
        page.fill("input[name='password']", "admin")
        page.click("button[type='submit']")
        page.wait_for_url(f"{BASE_URL}/")

        # 点击客户档案链接
        page.click("a[href='/clients'], .ant-menu-item:has-text('客户')")
        page.wait_for_url(f"{BASE_URL}/clients")
        expect(page).to_have_url(f"{BASE_URL}/clients")

    def test_inventory_link(self, page: Page):
        """测试库存耗材链接"""
        page.goto(f"{BASE_URL}/login")
        page.fill("input[name='username']", "admin")
        page.fill("input[name='password']", "admin")
        page.click("button[type='submit']")
        page.wait_for_url(f"{BASE_URL}/")

        # 点击库存耗材链接
        page.click("a[href='/inventory'], .ant-menu-item:has-text('库存')")
        page.wait_for_url(f"{BASE_URL}/inventory")
        expect(page).to_have_url(f"{BASE_URL}/inventory")


class TestClientsPage:
    """页面加载测试"""

    def test_clients_page_loads(self, page: Page):
        """测试客户档案页面加载"""
        page.goto(f"{BASE_URL}/login")
        page.fill("input[name='username']", "admin")
        page.fill("input[name='password']", "admin")
        page.click("button[type='submit']")
        page.wait_for_url(f"{BASE_URL}/")

        # 点击客户档案链接
        page.click("a[href='/clients'], .ant-menu-item:has-text('客户')")
        page.wait_for_url(f"{BASE_URL}/clients")

        # 验证页面元素
        expect(page.locator("text=客户档案")).to_be_visible(timeout=5000)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
