"""各业态 Prompt 共用的 JSON 输出格式和约束。"""

ANALYSIS_OUTPUT_FORMAT = """
## 输出要求
严格按以下 JSON 格式返回，不要包含 markdown 代码块标记：
{
  "primary_type": "主分类名称",
  "secondary_type": "次要分类（无则null）",
  "confidence": 0.85,
  "analysis": "200字以内的分析说明，用通俗易懂的语言",
  "key_symptoms": ["匹配的关键特征1", "特征2"],
  "risk_factors": ["需要注意的风险"],
  "contraindications": ["禁忌事项"]
}

## 重要约束
- 不要做出医疗诊断，仅做专业倾向性分析
- 如果信息不足以判断，confidence 应低于 0.5 并在 analysis 中说明
- 所有输出使用中文

## 历史服务记录分析（如有提供）
- 重点关注客户症状的变化趋势（改善/加重/持续）
- 评估之前服务项目的效果
- 如症状持续或加重，应在 risk_factors 中标注
- 根据服务效果调整推荐方案
"""

PLAN_OUTPUT_FORMAT = """
## 输出要求
严格按以下 JSON 格式返回，不要包含 markdown 代码块标记：
{
  "in_store_services": [
    {"name": "推荐服务项目名", "frequency": "建议频次", "reason": "推荐理由"}
  ],
  "home_care_advice": [
    {"category": "类别（如饮食/作息/护理）", "advice": "具体建议内容"}
  ],
  "seasonal_notes": "当前季节特别注意事项（50字以内）",
  "plan_summary": "方案综述（200字以内，通俗易懂，可直接发给客户）"
}

## 重要约束
- 推荐的店内服务项目必须从"可选项目列表"中选择，不要编造不存在的项目
- 居家建议要具体可操作，不要泛泛而谈
- 语气亲切专业，像顾问给建议而非医生开处方
- 所有输出使用中文
"""
