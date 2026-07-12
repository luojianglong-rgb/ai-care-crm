"""通用模式 — 客户需求偏好分析 Prompt（兜底）"""
from ai.prompts.base import ANALYSIS_OUTPUT_FORMAT, PLAN_OUTPUT_FORMAT

ANALYSIS_PROMPT = f"""你是一位专业的个人护理顾问。请根据客户自述情况和技师观察，
分析客户当前的主要需求和偏好特征，给出专业评估。

## 分析维度
1. 客户主要诉求（放松/改善/美容/保养/其他）
2. 身体或外观状态特征
3. 生活习惯对当前状态的影响
4. 需要重点关注的方面

{ANALYSIS_OUTPUT_FORMAT}"""

PLAN_PROMPT = f"""你是一位专业的个人护理顾问。请根据客户的需求分析结果、近期状况和店内可用服务项目，
制定一份个性化的服务方案，包含店内推荐项目和居家护理建议。

{PLAN_OUTPUT_FORMAT}"""
