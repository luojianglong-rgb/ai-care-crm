"""
AI-Care CRM 大模型统一客户端
双模式：direct（商户自带 Key 直连）/ proxy（开发者 Token 代理）
通过 OpenAI 兼容协议统一调用国内大模型。
"""
import json
import logging
from dataclasses import dataclass
from typing import Optional

from config import AppConfig

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    content: str
    tokens_used: int = 0
    model: str = ""
    success: bool = True
    error: str = ""


class LLMClient:
    """
    双模式大模型客户端。
    direct: 直连 DeepSeek/通义/智谱/Kimi/百川/星火
    proxy:  经开发者代理网关转发
    两种模式对上层调用方完全透明。
    """

    def __init__(self, config: AppConfig):
        self.config = config
        self._client = None
        self._init_client()

    def _init_client(self):
        """延迟初始化 OpenAI 客户端（仅在有 API Key 时初始化）。"""
        base_url = self.config.llm.get_base_url()
        api_key = self.config.llm.get_api_key()

        if not api_key or not base_url:
            logger.warning("LLM 未配置 API Key 或 base_url，AI 功能不可用")
            self._client = None
            return

        try:
            from openai import OpenAI
            self._client = OpenAI(
                api_key=api_key,
                base_url=base_url,
                timeout=self.config.llm.timeout,
            )
            logger.info(f"LLM 客户端初始化成功 [mode={self.config.llm.mode}, "
                        f"provider={self.config.llm.provider}]")
        except ImportError:
            logger.warning("openai 包未安装，AI 功能不可用。请运行: pip install openai")
            self._client = None

    @property
    def is_available(self) -> bool:
        return self._client is not None

    def chat(self, system_prompt: str, user_message: str,
             temperature: Optional[float] = None,
             max_tokens: Optional[int] = None) -> LLMResponse:
        """
        同步调用大模型。
        返回 LLMResponse（包含 content、tokens_used 等）。
        """
        if not self.is_available:
            return LLMResponse(
                content="", success=False,
                error="AI 功能未就绪：请在 config.yaml 中配置 LLM API Key"
            )

        model = self.config.llm.get_model()
        temp = temperature if temperature is not None else self.config.llm.temperature
        max_tok = max_tokens if max_tokens is not None else self.config.llm.max_tokens

        try:
            response = self._client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=temp,
                max_tokens=max_tok,
            )

            content = response.choices[0].message.content or ""
            tokens = 0
            if response.usage:
                tokens = response.usage.total_tokens

            return LLMResponse(
                content=content,
                tokens_used=tokens,
                model=response.model or model,
                success=True,
            )

        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            return LLMResponse(
                content="", success=False,
                error=str(e), model=model,
            )

    def chat_json(self, system_prompt: str, user_message: str,
                  temperature: Optional[float] = None) -> tuple[Optional[dict], LLMResponse]:
        """
        调用大模型并期望 JSON 格式返回。
        返回 (parsed_dict_or_None, raw_response)。
        """
        # 在 system prompt 末尾追加 JSON 格式要求
        json_prompt = system_prompt + "\n\n请严格按 JSON 格式返回，不要包含 markdown 代码块标记。"

        resp = self.chat(json_prompt, user_message, temperature)
        if not resp.success:
            return None, resp

        # 尝试解析 JSON
        content = resp.content.strip()
        # 去除可能的 markdown 代码块
        if content.startswith("```"):
            lines = content.split("\n")
            lines = [l for l in lines if not l.startswith("```")]
            content = "\n".join(lines)

        try:
            parsed = json.loads(content)
            return parsed, resp
        except json.JSONDecodeError as e:
            logger.warning(f"LLM 返回非 JSON 格式: {e}")
            return None, LLMResponse(
                content=resp.content, tokens_used=resp.tokens_used,
                model=resp.model, success=False,
                error=f"AI 返回的内容不是有效 JSON: {e}"
            )


# ── 全局单例 ──────────────────────────────────────────────────────

_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    global _llm_client
    if _llm_client is None:
        from config import get_config
        _llm_client = LLMClient(get_config())
    return _llm_client


def reinit_llm_client(config: AppConfig):
    global _llm_client
    _llm_client = LLMClient(config)
