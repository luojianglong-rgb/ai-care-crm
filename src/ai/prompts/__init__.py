"""
业态 Prompt 模板加载器
根据 business_type / analysis_domain 动态加载对应的 Prompt 模块。
"""
from typing import Optional

_MODULES = {}


def _load_module(domain: str):
    if domain in _MODULES:
        return _MODULES[domain]
    try:
        mod = __import__(f"ai.prompts.{domain}", fromlist=[domain])
    except ImportError:
        mod = __import__("ai.prompts.general", fromlist=["general"])
    _MODULES[domain] = mod
    return mod


def get_analysis_prompt(domain: str) -> str:
    """获取专业分析的 System Prompt。"""
    mod = _load_module(domain)
    return getattr(mod, "ANALYSIS_PROMPT", "")


def get_plan_prompt(domain: str) -> str:
    """获取方案生成的 System Prompt。"""
    mod = _load_module(domain)
    return getattr(mod, "PLAN_PROMPT", "")
