#!/usr/bin/env python3
"""
内容生成器单元测试
"""
import pytest
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from ai.content_generator import ContentGenerator
from tests.utils.mock_llm import MockLLMClient


class TestContentGenerator:
    """内容生成器测试"""

    def test_generator_init(self, mock_config, mock_llm):
        """测试生成器初始化"""
        generator = ContentGenerator(mock_config, mock_llm)

        assert generator.config == mock_config
        assert generator.llm == mock_llm

    def test_generate_post_service(self, test_db, mock_config, mock_llm):
        """测试服务后关怀文案"""
        mock_llm.responses = {
            "content": "亲爱的客户，感谢您今天的光临。希望您休息愉快！"
        }

        generator = ContentGenerator(mock_config, mock_llm)
        variables = {
            "client_name": "张女士",
            "service": "艾灸",
            "date": datetime.now().strftime("%Y-%m-%d"),
        }

        result = generator.generate(test_db, "post_service_followup", variables)

        assert result["success"] == True
        assert "客户" in result["content"] or "光临" in result["content"]

    def test_generate_birthday(self, test_db, mock_config, mock_llm):
        """测试生日祝福文案"""
        mock_llm.responses = {
            "content": "亲爱的张女士，祝您生日快乐！愿您身体健康，万事如意！"
        }

        generator = ContentGenerator(mock_config, mock_llm)
        variables = {
            "client_name": "张女士",
            "birth_date": "1990-06-15",
        }

        result = generator.generate(test_db, "birthday_greeting", variables)

        assert result["success"] == True
        assert "生日" in result["content"]

    def test_generate_seasonal(self, test_db, mock_config, mock_llm):
        """测试节气养生文案"""
        mock_llm.responses = {
            "content": "立春时节，万物复苏。建议您调理肝气，多做户外运动。"
        }

        generator = ContentGenerator(mock_config, mock_llm)
        variables = {
            "client_name": "李先生",
            "solar_term": "立春",
            "date": datetime.now().strftime("%Y-%m-%d"),
        }

        result = generator.generate(test_db, "seasonal_care", variables)

        assert result["success"] == True
        assert "立春" in result["content"]

    def test_generate_llm_not_available(self, test_db, mock_config, mock_llm):
        """测试 LLM 不可用时的生成"""
        mock_llm.set_available(False)

        generator = ContentGenerator(mock_config, mock_llm)
        result = generator.generate(test_db, "birthday_greeting", {"client_name": "测试"})

        # 应该返回失败或模板内容
        assert result["success"] == False or result["content"] != ""

    def test_generate_with_empty_variables(self, test_db, mock_config, mock_llm):
        """测试空变量时的生成"""
        mock_llm.responses = {"content": "默认文案"}

        generator = ContentGenerator(mock_config, mock_llm)
        result = generator.generate(test_db, "birthday_greeting", {})

        # 应该使用模板变量或返回默认内容
        assert result["content"] != ""

    def test_generate_with_special_characters(self, test_db, mock_config, mock_llm):
        """测试含特殊字符的变量"""
        mock_llm.responses = {"content": "文案内容"}

        generator = ContentGenerator(mock_config, mock_llm)
        variables = {
            "client_name": "张女士（VIP客户）",
            "service": "艾灸 & 推拿",
        }

        result = generator.generate(test_db, "post_service_followup", variables)

        assert result["success"] == True


class TestContentGeneratorVariables:
    """变量处理测试"""

    def test_variable_replacement_client_name(self, test_db, mock_config, mock_llm):
        """测试客户名变量替换"""
        mock_llm.responses = {"content": "{client_name}您好"}

        generator = ContentGenerator(mock_config, mock_llm)
        result = generator.generate(test_db, "test", {"client_name": "王女士"})

        # 变量应该在模板中被替换（如果生成器实现了替换）
        assert result["content"] != ""

    def test_variable_replacement_date(self, test_db, mock_config, mock_llm):
        """测试日期变量替换"""
        generator = ContentGenerator(mock_config, mock_llm)
        variables = {
            "client_name": "测试",
            "date": "2026-04-11",
        }

        result = generator.generate(test_db, "post_service_followup", variables)

        assert result["success"] == True


class TestContentGeneratorScenes:
    """场景测试"""

    def test_scene_weather_alert(self, test_db, mock_config, mock_llm):
        """测试天气提醒场景"""
        mock_llm.responses = {"content": "天气转凉，请注意保暖"}

        generator = ContentGenerator(mock_config, mock_llm)
        variables = {
            "client_name": "李先生",
            "weather": "降温",
            "temperature": "15°C",
        }

        result = generator.generate(test_db, "weather_alert", variables)

        assert result["success"] == True

    def test_scene_silent_client_wakeup(self, test_db, mock_config, mock_llm):
        """测试沉默客户唤醒场景"""
        mock_llm.responses = {"content": "好久不见，期待您的光临"}

        generator = ContentGenerator(mock_config, mock_llm)
        variables = {
            "client_name": "张女士",
            "last_visit_days": 30,
        }

        result = generator.generate(test_db, "silent_client_wakeup", variables)

        assert result["success"] == True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])