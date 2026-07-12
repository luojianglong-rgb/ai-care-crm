#!/usr/bin/env python3
"""
渠道路由单元测试
"""
import pytest
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from channels.router import ChannelRouter


class TestChannelRouter:
    """渠道路由测试"""

    def test_select_ml307a_enabled(self, mock_config_business):
        """测试 ML307A 启用时选择渠道"""
        mock_config_business.raw = {
            "channels": {
                "ml307a": {"enabled": True},
            }
        }
        router = ChannelRouter(mock_config_business)
        channel = router.select("auto", "13800138000", "测试内容")

        assert channel == "ml307a"

    def test_select_ml307a_disabled(self, mock_config):
        """测试 ML307A 禁用时选择渠道"""
        mock_config.raw = {
            "channels": {
                "ml307a": {"enabled": False},
            }
        }
        router = ChannelRouter(mock_config)
        channel = router.select("auto", "13800138000", "测试内容")

        assert channel == ""  # 无可用渠道

    def test_select_ml307a_explicit(self, mock_config):
        """测试明确指定 ML307A 渠道"""
        mock_config.raw = {
            "channels": {
                "ml307a": {"enabled": True},
            }
        }
        router = ChannelRouter(mock_config)
        channel = router.select("ml307a", "13800138000", "测试内容")

        assert channel == "ml307a"

    def test_get_available_channels_ml307a_enabled(self, mock_config_business):
        """测试获取可用渠道列表（ML307A启用）"""
        mock_config_business.raw = {
            "channels": {
                "ml307a": {"enabled": True},
            }
        }
        router = ChannelRouter(mock_config_business)
        channels = router.get_available_channels()

        assert channels == ["ml307a"]

    def test_get_available_channels_ml307a_disabled(self, mock_config):
        """测试获取可用渠道列表（ML307A禁用）"""
        mock_config.raw = {
            "channels": {
                "ml307a": {"enabled": False},
            }
        }
        router = ChannelRouter(mock_config)
        channels = router.get_available_channels()

        assert channels == []

    def test_select_with_empty_phone(self, mock_config_business):
        """测试空手机号"""
        mock_config_business.raw = {
            "channels": {
                "ml307a": {"enabled": True},
            }
        }
        router = ChannelRouter(mock_config_business)
        channel = router.select("auto", "", "测试内容")

        # ML307A 启用时仍然返回 ml307a（发送时会失败）
        assert channel == "ml307a"

    def test_select_with_long_content(self, mock_config_business):
        """测试长内容短信"""
        mock_config_business.raw = {
            "channels": {
                "ml307a": {"enabled": True},
            }
        }
        router = ChannelRouter(mock_config_business)

        # 70字以上会拆条，但路由选择不受影响
        long_content = "这是一条超过70字的测试短信内容，用于测试短信拆条功能是否正常工作。这是一条超过70字的测试短信内容，用于测试短信拆条功能是否正常工作。"
        channel = router.select("auto", "13800138000", long_content)

        assert channel == "ml307a"

    def test_router_init_with_no_raw(self, mock_config):
        """测试无 raw 配置时初始化"""
        mock_config.raw = {}
        router = ChannelRouter(mock_config)

        # 应该不崩溃
        assert router.ml307a_enabled == False


class TestChannelRouterIntegration:
    """渠道路由集成测试"""

    def test_full_flow_ml307a(self, mock_config_business):
        """测试完整流程：选择渠道 -> 检查可用"""
        mock_config_business.raw = {
            "channels": {
                "ml307a": {"enabled": True},
            }
        }
        router = ChannelRouter(mock_config_business)

        # 选择渠道
        channel = router.select("auto", "13800138000", "生日祝福")
        assert channel == "ml307a"

        # 检查可用
        available = router.get_available_channels()
        assert "ml307a" in available


if __name__ == "__main__":
    pytest.main([__file__, "-v"])