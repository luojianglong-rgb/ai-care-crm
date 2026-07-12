#!/usr/bin/env python3
"""
LLM 客户端单元测试
"""
import pytest
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from ai.llm_client import LLMClient, LLMResponse, get_llm_client, reinit_llm_client
from tests.utils.mock_llm import MockLLMClient


class TestLLMClientAvailability:
    """LLM 可用性测试"""

    def test_is_available_true(self, mock_llm):
        """测试 LLM 可用状态"""
        mock_llm.set_available(True)
        assert mock_llm.is_available == True

    def test_is_available_false(self, mock_llm):
        """测试 LLM 不可用状态"""
        mock_llm.set_available(False)
        assert mock_llm.is_available == False


class TestLLMClientChat:
    """LLM Chat 测试"""

    def test_chat_success(self, mock_llm):
        """测试 chat 成功"""
        mock_llm.set_available(True)
        response = mock_llm.chat("系统提示", "用户消息")

        assert response.success == True
        assert response.content != ""
        assert response.tokens_used > 0

    def test_chat_failure_not_available(self, mock_llm):
        """测试 chat 失败（LLM 不可用）"""
        mock_llm.set_available(False)
        response = mock_llm.chat("系统提示", "用户消息")

        assert response.success == False
        assert "不可用" in response.error

    def test_chat_records_call(self, mock_llm):
        """测试 chat 记录调用信息"""
        mock_llm.set_available(True)
        mock_llm.chat("系统提示", "用户消息", temperature=0.5, max_tokens=500)

        assert mock_llm.call_count == 1
        assert mock_llm.last_call["system_prompt"] == "系统提示"
        assert mock_llm.last_call["user_message"] == "用户消息"
        assert mock_llm.last_call["temperature"] == 0.5
        assert mock_llm.last_call["max_tokens"] == 500

    def test_chat_multiple_calls(self, mock_llm):
        """测试多次调用计数"""
        mock_llm.set_available(True)
        mock_llm.chat("提示1", "消息1")
        mock_llm.chat("提示2", "消息2")
        mock_llm.chat("提示3", "消息3")

        assert mock_llm.call_count == 3


class TestLLMClientChatJson:
    """LLM ChatJSON 测试"""

    def test_chat_json_success(self, mock_llm_with_response):
        """测试 chat_json 成功"""
        mock_llm_with_response.set_available(True)

        parsed, response = mock_llm_with_response.chat_json(
            "分析意图", "明天下午想预约艾灸"
        )

        assert response.success == True
        assert parsed is not None
        assert parsed["intent"] == "appointment"

    def test_chat_json_failure_not_available(self, mock_llm):
        """测试 chat_json 失败（不可用）"""
        mock_llm.set_available(False)

        parsed, response = mock_llm.chat_json("系统提示", "用户消息")

        assert parsed is None
        assert response.success == False

    def test_chat_json_failure_invalid_json(self, mock_llm):
        """测试 chat_json 失败（无效 JSON）"""
        mock_llm.set_available(True)
        # Mock 返回非 JSON 内容
        mock_llm.responses = {"default": "这不是 JSON 格式"}

        parsed, response = mock_llm.chat_json("系统提示", "用户消息")

        # 尝试解析失败
        assert response.success == False or parsed is None


class TestMockLLMResponses:
    """Mock LLM 预设响应测试"""

    def test_analysis_response(self):
        """测试体质分析预设响应"""
        from tests.utils.mock_llm import create_mock_llm_for_analysis

        mock = create_mock_llm_for_analysis()
        parsed, response = mock.chat_json("分析", "我最近感觉疲乏无力")

        assert response.success == True
        assert parsed["type"] == "气虚质"
        assert "疲乏无力" in parsed["symptoms"]

    def test_content_response(self):
        """测试文案生成预设响应"""
        from tests.utils.mock_llm import create_mock_llm_for_content

        mock = create_mock_llm_for_content()
        response = mock.chat("生成文案", "生日祝福")

        assert response.success == True
        assert "生日快乐" in response.content

    def test_reply_response(self):
        """测试回复解析预设响应"""
        from tests.utils.mock_llm import create_mock_llm_for_reply

        mock = create_mock_llm_for_reply()
        parsed, response = mock.chat_json("意图", "明天想预约")

        assert response.success == True
        assert parsed["intent"] == "appointment"
        assert parsed["suggested_action"] == "创建预约"


class TestLLMResponseDataclass:
    """LLMResponse 数据类测试"""

    def test_llm_response_defaults(self):
        """测试 LLMResponse 默认值"""
        response = LLMResponse(content="测试内容")

        assert response.content == "测试内容"
        assert response.tokens_used == 0
        assert response.model == ""
        assert response.success == True
        assert response.error == ""

    def test_llm_response_failure(self):
        """测试 LLMResponse 失败状态"""
        response = LLMResponse(
            content="",
            success=False,
            error="API 调用失败"
        )

        assert response.success == False
        assert response.error == "API 调用失败"

    def test_llm_response_with_tokens(self):
        """测试 LLMResponse 含 token 数"""
        response = LLMResponse(
            content="回复内容",
            tokens_used=150,
            model="deepseek-chat",
            success=True,
        )

        assert response.tokens_used == 150
        assert response.model == "deepseek-chat"


class TestLLMClientReset:
    """Mock LLM 重置测试"""

    def test_reset_clears_count(self, mock_llm):
        """测试重置清空计数"""
        mock_llm.chat("提示", "消息")
        mock_llm.chat("提示", "消息")
        assert mock_llm.call_count == 2

        mock_llm.reset()
        assert mock_llm.call_count == 0

    def test_reset_clears_last_call(self, mock_llm):
        """测试重置清空最后调用"""
        mock_llm.chat("提示", "消息")
        assert mock_llm.last_call is not None

        mock_llm.reset()
        assert mock_llm.last_call is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])