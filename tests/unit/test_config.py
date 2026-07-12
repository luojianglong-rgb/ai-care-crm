#!/usr/bin/env python3
"""
配置模块单元测试
"""
import pytest
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from config import (
    load_config, get_config_path, AppConfig,
    StoreConfig, LLMConfig, ServerConfig, QuotaTier,
    BUSINESS_DEFAULTS
)


class TestConfigLoading:
    """配置加载测试"""

    def test_business_defaults_exist(self):
        """测试业态默认值存在"""
        assert "tcm_wellness" in BUSINESS_DEFAULTS
        assert "spa" in BUSINESS_DEFAULTS
        assert "hair_salon" in BUSINESS_DEFAULTS
        assert "general" in BUSINESS_DEFAULTS

    def test_business_defaults_tcm_wellness(self):
        """测试中医养生业态默认值"""
        defaults = BUSINESS_DEFAULTS["tcm_wellness"]
        assert defaults["staff_title"] == "理疗师"
        assert defaults["analysis_name"] == "中医体质辨识"
        assert defaults["plan_name"] == "调理方案"
        assert defaults["analysis_domain"] == "tcm"
        assert "艾灸" in defaults["default_categories"]

    def test_business_defaults_spa(self):
        """测试SPA业态默认值"""
        defaults = BUSINESS_DEFAULTS["spa"]
        assert defaults["staff_title"] == "美容师"
        assert defaults["analysis_name"] == "肤质分析"
        assert defaults["plan_name"] == "护肤方案"
        assert defaults["analysis_domain"] == "skin"

    def test_business_defaults_general(self):
        """测试通用业态默认值"""
        defaults = BUSINESS_DEFAULTS["general"]
        assert defaults["staff_title"] == "技师"
        assert defaults["analysis_domain"] == "general"


class TestQuotaTier:
    """套餐额度测试"""

    def test_quota_tier_basic_defaults(self):
        """测试基础版默认额度"""
        quota = QuotaTier()
        assert quota.max_clients == 50
        assert quota.max_staff == 3
        assert quota.ai_total_limit == 0

    def test_quota_tier_pro(self):
        """测试专业版额度"""
        quota = QuotaTier(
            max_clients=-1,
            max_staff=-1,
            ai_weekly_limit=50,
            custom_playbooks=True,
        )
        assert quota.max_clients == -1  # 无限制
        assert quota.ai_weekly_limit == 50
        assert quota.custom_playbooks == True

    def test_quota_tier_business(self):
        """测试至尊版额度"""
        quota = QuotaTier(
            max_clients=-1,
            max_staff=-1,
            ai_analysis_per_month=-1,
            ai_plan_per_month=-1,
            ai_content_per_month=-1,
            custom_playbooks=True,
        )
        assert quota.ai_analysis_per_month == -1  # 无限制
        assert quota.custom_playbooks == True


class TestStoreConfig:
    """门店配置测试"""

    def test_store_config_defaults(self):
        """测试门店默认配置"""
        store = StoreConfig()
        assert store.name == "AI-Care CRM"
        assert store.business_type == "general"

    def test_store_config_custom(self):
        """测试自定义门店配置"""
        store = StoreConfig(name="测试门店", business_type="tcm_wellness")
        assert store.name == "测试门店"
        assert store.business_type == "tcm_wellness"


class TestLLMConfig:
    """LLM配置测试"""

    def test_llm_config_defaults(self):
        """测试LLM默认配置"""
        llm = LLMConfig()
        assert llm.mode == "direct"
        assert llm.provider == "deepseek"
        assert llm.temperature == 0.3
        assert llm.max_tokens == 2000

    def test_llm_config_custom(self):
        """测试自定义LLM配置"""
        llm = LLMConfig(
            provider="qwen",
            model="qwen-plus",
            temperature=0.5,
        )
        assert llm.provider == "qwen"
        assert llm.model == "qwen-plus"
        assert llm.temperature == 0.5


class TestServerConfig:
    """服务器配置测试"""

    def test_server_config_defaults(self):
        """测试服务器默认配置"""
        server = ServerConfig()
        assert server.host == "0.0.0.0"
        assert server.port == 8000
        assert server.dev_mode == False

    def test_server_config_custom(self):
        """测试自定义服务器配置"""
        server = ServerConfig(port=8888, dev_mode=True)
        assert server.port == 8888
        assert server.dev_mode == True


class TestConfigPath:
    """配置文件路径测试"""

    def test_get_config_path_development(self):
        """测试开发环境配置路径"""
        # 不在 PyInstaller 环境中
        import sys
        if not hasattr(sys, '_MEIPASS'):
            path = get_config_path()
            assert "config.yaml" in path

    def test_get_config_path_pyinstaller(self):
        """测试 PyInstaller 环境配置路径（模拟）"""
        # 这个测试需要模拟 PyInstaller 环境
        # 实际测试在打包后的 EXE 中进行
        pass


class TestLoadConfig:
    """配置加载测试"""

    def test_load_config_empty(self):
        """测试加载空配置（使用默认值）"""
        # 使用临时文件
        fd, temp_path = tempfile.mkstemp(suffix=".yaml")
        os.close(fd)
        os.unlink(temp_path)

        config = load_config(temp_path)
        assert config.store.name == "AI-Care CRM"
        assert config.store.business_type == "general"

    def test_load_config_with_file(self):
        """测试从文件加载配置"""
        # 创建临时配置文件
        fd, temp_path = tempfile.mkstemp(suffix=".yaml")
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write("""
store:
  name: 测试门店
  business_type: tcm_wellness
llm:
  provider: deepseek
  api_key: test_key
server:
  port: 8888
""")
        try:
            config = load_config(temp_path)
            assert config.store.name == "测试门店"
            assert config.store.business_type == "tcm_wellness"
            assert config.server.port == 8888
        finally:
            os.unlink(temp_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])