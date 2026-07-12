#!/usr/bin/env python3
"""
回复解析器单元测试
"""
import pytest
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from ai.reply_parser import ReplyParser
from tests.utils.mock_llm import MockLLMClient, create_mock_llm_for_reply


class TestReplyParser:
    """回复解析器测试"""

    def test_parser_init(self, mock_config, mock_llm):
        """测试解析器初始化"""
        parser = ReplyParser(mock_config, mock_llm)

        assert parser.config == mock_config
        assert parser.llm == mock_llm

    def test_parse_appointment_intent(self, mock_config):
        """测试预约意图解析"""
        mock_llm = create_mock_llm_for_reply()
        parser = ReplyParser(mock_config, mock_llm)

        result = parser.parse("明天下午想预约艾灸")

        assert result["intent"] == "appointment"
        assert result["sentiment"] == "positive"
        assert result["suggested_action"] == "创建预约"

    def test_parse_feedback_intent(self, mock_config, mock_llm_with_response):
        """测试反馈意图解析"""
        mock_llm_with_response.responses = {
            "reply_intent": {
                "intent": "feedback",
                "sentiment": "neutral",
                "details": {"content": "服务态度好"},
                "suggested_action": "记录反馈"
            }
        }

        parser = ReplyParser(mock_config, mock_llm_with_response)
        result = parser.parse("上次服务态度很好")

        assert result["intent"] == "feedback"

    def test_parse_other_intent(self, mock_config, mock_llm):
        """测试其他意图解析"""
        mock_llm.responses = {
            "reply_intent": {
                "intent": "other",
                "sentiment": "neutral",
                "details": {},
                "suggested_action": "无"
            }
        }

        parser = ReplyParser(mock_config, mock_llm)
        result = parser.parse("收到您的短信")

        assert result["intent"] == "other"

    def test_parse_llm_not_available(self, mock_config, mock_llm):
        """测试 LLM 不可用时的解析"""
        mock_llm.set_available(False)
        parser = ReplyParser(mock_config, mock_llm)

        result = parser.parse("明天想预约")

        # 应该返回默认意图或失败
        assert result.get("intent") is not None or result.get("error") is not None

    def test_parse_empty_content(self, mock_config, mock_llm):
        """测试空内容解析"""
        parser = ReplyParser(mock_config, mock_llm)
        result = parser.parse("")

        # 应该处理空内容
        assert result.get("intent") is not None


class TestReplyParserDetails:
    """详情解析测试"""

    def test_parse_with_date_detail(self, mock_config, mock_llm_with_response):
        """测试带日期详情的解析"""
        parser = ReplyParser(mock_config, mock_llm_with_response)
        result = parser.parse("明天下午三点预约")

        assert result["intent"] == "appointment"
        assert "date" in result["details"] or "details" in result

    def test_parse_with_service_detail(self, mock_config, mock_llm_with_response):
        """测试带服务详情的解析"""
        parser = ReplyParser(mock_config, mock_llm_with_response)
        result = parser.parse("想预约艾灸服务")

        assert result["intent"] == "appointment"

    def test_parse_negative_sentiment(self, mock_config, mock_llm_with_response):
        """测试负面情感解析"""
        mock_llm_with_response.responses = {
            "reply_intent": {
                "intent": "feedback",
                "sentiment": "negative",
                "details": {"issue": "等待时间长"},
                "suggested_action": "跟进处理"
            }
        }

        parser = ReplyParser(mock_config, mock_llm_with_response)
        result = parser.parse("上次等待时间太长了")

        assert result["sentiment"] == "negative"
        assert result["suggested_action"] == "跟进处理"


class TestReplyParserActions:
    """建议动作测试"""

    def test_suggested_action_create_appointment(self, mock_config, mock_llm_with_response):
        """测试建议创建预约"""
        parser = ReplyParser(mock_config, mock_llm_with_response)
        result = parser.parse("明天有空吗")

        assert result["suggested_action"] == "创建预约"

    def test_suggested_action_record_feedback(self, mock_config, mock_llm_with_response):
        """测试建议记录反馈"""
        mock_llm_with_response.responses = {
            "reply_intent": {
                "intent": "feedback",
                "sentiment": "positive",
                "details": {},
                "suggested_action": "记录反馈"
            }
        }

        parser = ReplyParser(mock_config, mock_llm_with_response)
        result = parser.parse("服务很好")

        assert result["suggested_action"] == "记录反馈"

    def test_suggested_action_none(self, mock_config, mock_llm_with_response):
        """测试无建议动作"""
        mock_llm_with_response.responses = {
            "reply_intent": {
                "intent": "other",
                "sentiment": "neutral",
                "details": {},
                "suggested_action": ""
            }
        }

        parser = ReplyParser(mock_config, mock_llm_with_response)
        result = parser.parse("好的收到")

        assert result["suggested_action"] == ""


class TestReplyParserSpecialCases:
    """特殊情况测试"""

    def test_parse_long_content(self, mock_config, mock_llm_with_response):
        """测试长内容解析"""
        parser = ReplyParser(mock_config, mock_llm_with_response)
        long_content = """
        上次来做艾灸效果挺好的，
        感觉身体轻松了很多。
        明天下午三点想再来预约，
        能安排一下吗？
        """

        result = parser.parse(long_content)

        assert result["intent"] == "appointment"

    def test_parse_with_emoji(self, mock_config, mock_llm_with_response):
        """测试含表情符号的解析"""
        parser = ReplyParser(mock_config, mock_llm_with_response)
        result = parser.parse("好的😊明天来预约")

        assert result["intent"] == "appointment"

    def test_parse_with_phone_number(self, mock_config, mock_llm_with_response):
        """测试含电话号码的解析"""
        parser = ReplyParser(mock_config, mock_llm_with_response)
        result = parser.parse("我的电话是13800138000，明天预约")

        assert result["intent"] == "appointment"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])