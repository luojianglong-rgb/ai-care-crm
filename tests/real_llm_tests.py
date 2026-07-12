#!/usr/bin/env python3
"""
真实 LLM 集成测试
使用 config.yaml 中配置的真实 API Key
"""
import pytest
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))


@pytest.mark.real_llm
class TestRealLLMConnection:
    """真实 LLM 连接测试"""

    def test_llm_is_available(self, real_llm):
        """测试 LLM 是否可用"""
        assert real_llm.is_available == True
        print(f"\nLLM 已连接，可用状态: {real_llm.is_available}")

    def test_llm_simple_chat(self, real_llm):
        """测试简单对话"""
        response = real_llm.chat(
            "你是一个友好的助手",
            "请说一句问候语"
        )

        assert response.success == True
        assert len(response.content) > 0
        print(f"\nLLM 响应: {response.content[:100]}...")

    def test_llm_chat_with_temperature(self, real_llm):
        """测试不同温度参数"""
        # 低温度（更确定性）
        response1 = real_llm.chat(
            "回复简短",
            "你好",
            temperature=0.1
        )

        # 高温度（更随机）
        response2 = real_llm.chat(
            "回复简短",
            "你好",
            temperature=0.9
        )

        assert response1.success == True
        assert response2.success == True
        print(f"\n低温度响应: {response1.content[:50]}...")
        print(f"高温度响应: {response2.content[:50]}...")


@pytest.mark.real_llm
class TestRealLLMJSON:
    """真实 LLM JSON 输出测试"""

    def test_llm_chat_json_success(self, real_llm):
        """测试 JSON 格式输出"""
        parsed, response = real_llm.chat_json(
            "分析客户体质，返回 JSON 格式：{\"type\": \"体质类型\", \"description\": \"描述\", \"symptoms\": [\"症状列表\"]}",
            "客户说最近感觉疲乏无力，气短懒言，面色偏白。请分析体质类型。"
        )

        assert response.success == True
        assert parsed is not None
        print(f"\n体质分析 JSON 结果: {parsed}")

    def test_llm_chat_json_intent(self, real_llm):
        """测试意图识别 JSON"""
        parsed, response = real_llm.chat_json(
            """分析短信回复的意图。
            返回 JSON 格式: {"intent": "want_booking|symptom_improved|negative|general_chat", "sentiment": "positive|neutral|negative", "details": {}, "suggested_next_action": "建议动作"}""",
            "明天下午三点想预约艾灸服务"
        )

        assert response.success == True
        assert parsed is not None
        assert parsed.get("intent") in ["want_booking", "symptom_improved", "negative", "general_chat", "appointment"]
        print(f"\n意图识别 JSON 结果: {parsed}")


@pytest.mark.real_llm
class TestRealLLMPerformance:
    """真实 LLM 性能测试"""

    def test_response_time(self, real_llm):
        """测试响应时间"""
        import time

        start = time.time()
        response = real_llm.chat("简短回复", "你好")
        elapsed = time.time() - start

        assert response.success == True
        assert elapsed < 10  # 10秒内响应
        print(f"\n响应时间: {elapsed:.2f}秒")

    def test_token_usage(self, real_llm):
        """测试 token 使用统计"""
        response = real_llm.chat(
            "回复约50字",
            "请介绍一下中医体质的概念"
        )

        assert response.success == True
        assert response.tokens_used > 0
        print(f"\nToken 使用: {response.tokens_used}")
        print(f"内容: {response.content[:100]}...")


# 运行命令:
# pytest tests/real_llm_tests.py -v

if __name__ == "__main__":
    pytest.main([__file__, "-v"])