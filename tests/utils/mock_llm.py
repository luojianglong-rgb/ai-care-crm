#!/usr/bin/env python3
"""
Mock LLM 客户端
用于测试 AI 模块，无需真实 API 调用
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any
import json


@dataclass
class MockLLMResponse:
    """Mock LLM 响应"""
    content: str
    tokens_used: int = 100
    model: str = "mock-model"
    success: bool = True
    error: str = ""


class MockLLMClient:
    """
    Mock LLM 客户端
    支持预设响应，用于单元测试
    """

    def __init__(self, responses: Optional[Dict[str, Any]] = None, available: bool = True):
        """
        Args:
            responses: 预设响应字典 {"analysis": ..., "content": ...}
            available: 是否模拟可用状态
        """
        self.responses = responses or {}
        self._available = available
        self.call_count = 0
        self.last_call = None

    @property
    def is_available(self) -> bool:
        return self._available

    def set_available(self, available: bool):
        """设置可用状态"""
        self._available = available

    def chat(self, system_prompt: str, user_message: str,
             temperature: Optional[float] = None,
             max_tokens: Optional[int] = None) -> MockLLMResponse:
        """
        Mock chat 调用
        """
        self.call_count += 1
        self.last_call = {
            "system_prompt": system_prompt,
            "user_message": user_message,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if not self._available:
            return MockLLMResponse(
                content="",
                success=False,
                error="LLM 不可用"
            )

        # 根据系统提示判断场景
        content = self._determine_response(system_prompt, user_message)

        return MockLLMResponse(
            content=content,
            tokens_used=100,
            success=True,
        )

    def chat_json(self, system_prompt: str, user_message: str,
                  temperature: Optional[float] = None) -> tuple[Optional[dict], MockLLMResponse]:
        """
        Mock JSON chat 调用
        """
        resp = self.chat(system_prompt + "\n\n请严格按 JSON 格式返回。", user_message, temperature)

        if not resp.success:
            return None, resp

        # 尝试解析 JSON
        try:
            # 如果响应已经是 dict，直接返回
            if isinstance(resp.content, dict):
                return resp.content, resp

            # 尝试解析字符串
            content = resp.content.strip()
            if content.startswith("```"):
                lines = content.split("\n")
                lines = [l for l in lines if not l.startswith("```")]
                content = "\n".join(lines)

            parsed = json.loads(content)
            return parsed, resp
        except json.JSONDecodeError:
            return None, MockLLMResponse(
                content=resp.content,
                success=False,
                error="JSON 解析失败"
            )

    def _determine_response(self, system_prompt: str, user_message: str) -> str:
        """根据提示词确定响应"""
        # 检查是否有预设响应
        if "分析" in system_prompt or "体质" in system_prompt:
            if "analysis" in self.responses:
                resp = self.responses["analysis"]
                if isinstance(resp, dict):
                    return json.dumps(resp, ensure_ascii=False)
                return resp

        if "文案" in system_prompt or "生成" in system_prompt:
            if "content" in self.responses:
                return self.responses["content"]

        if "意图" in system_prompt or "回复" in system_prompt:
            if "reply_intent" in self.responses:
                resp = self.responses["reply_intent"]
                if isinstance(resp, dict):
                    return json.dumps(resp, ensure_ascii=False)
                return resp

        # 默认响应
        return "这是一个 Mock 响应，用于测试。"

    def reset(self):
        """重置计数器"""
        self.call_count = 0
        self.last_call = None


# ── 便捷工厂函数 ────────────────────────────────────────────────────────

def create_mock_llm_for_analysis():
    """创建用于体质分析的 Mock LLM"""
    responses = {
        "analysis": {
            "type": "气虚质",
            "description": "容易疲劳，气短懒言，面色偏白",
            "symptoms": ["疲乏无力", "气短", "自汗"],
            "recommendations": ["补气健脾", "适度运动", "保持良好作息"],
            "suitable_services": ["艾灸", "推拿"],
        }
    }
    return MockLLMClient(responses=responses)


def create_mock_llm_for_content():
    """创建用于文案生成的 Mock LLM"""
    responses = {
        "content": "亲爱的客户，祝您生日快乐！感谢您一直以来对我们的信任与支持。愿您身体健康，万事如意！"
    }
    return MockLLMClient(responses=responses)


def create_mock_llm_for_reply():
    """创建用于回复解析的 Mock LLM"""
    responses = {
        "reply_intent": {
            "intent": "appointment",
            "sentiment": "positive",
            "details": {"date": "明天下午", "service": "艾灸"},
            "suggested_action": "创建预约"
        }
    }
    return MockLLMClient(responses=responses)