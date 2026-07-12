"""
本地 PII 脱敏模块
在将数据发送给云端大模型前，本地完成脱敏。
脱敏策略：正则匹配 + 字典映射，零网络请求。
"""
import re
from typing import Optional


class PIIMasker:
    """
    本地 PII 脱敏/回填工具。
    所有操作均在本地完成，无任何网络请求。

    使用方式：
        masker = PIIMasker()
        masked_text, mapping = masker.mask("王女士，手机号13812345678，住在朝阳区阳光小区")
        # masked_text: "[客户_001]，手机号[已隐藏_P1]，住在[已隐藏_A1]"
        # mapping: {"[客户_001]": "王女士", "[已隐藏_P1]": "13812345678", ...}

        result = masker.unmask("建议[客户_001]每周来店一次", mapping)
        # result: "建议王女士每周来店一次"
    """

    # 正则规则
    PHONE_PATTERN = re.compile(r'1[3-9]\d{9}')
    ID_CARD_PATTERN = re.compile(r'\d{17}[\dXx]')
    # 地址关键词后跟 2-30 个字符
    ADDRESS_PATTERN = re.compile(
        r'(?:住在|地址[是为：:]*|家在)(.{2,30}?)(?:[，。,.\s]|$)'
    )

    def __init__(self):
        self._counter = {"name": 0, "phone": 0, "address": 0, "id_card": 0}

    def _next_placeholder(self, category: str) -> str:
        self._counter[category] = self._counter.get(category, 0) + 1
        prefix_map = {
            "name": "客户",
            "phone": "已隐藏_P",
            "address": "已隐藏_A",
            "id_card": "已隐藏_ID",
        }
        prefix = prefix_map.get(category, "已隐藏")
        return f"[{prefix}{self._counter[category]}]"

    def mask(self, text: str, known_names: Optional[list[str]] = None) -> tuple[str, dict]:
        """
        对文本进行 PII 脱敏。
        Args:
            text: 原始文本
            known_names: 已知的客户姓名列表（从数据库中获取），用于精确匹配姓名
        Returns:
            (脱敏后文本, 映射表)。映射表用于后续 unmask 回填。
        """
        self._counter = {"name": 0, "phone": 0, "address": 0, "id_card": 0}
        mapping = {}
        masked = text

        # 1. 脱敏身份证号
        for match in self.ID_CARD_PATTERN.finditer(masked):
            original = match.group()
            placeholder = self._next_placeholder("id_card")
            mapping[placeholder] = original
            masked = masked.replace(original, placeholder, 1)

        # 2. 脱敏手机号
        for match in self.PHONE_PATTERN.finditer(masked):
            original = match.group()
            placeholder = self._next_placeholder("phone")
            mapping[placeholder] = original
            masked = masked.replace(original, placeholder, 1)

        # 3. 脱敏地址
        for match in self.ADDRESS_PATTERN.finditer(masked):
            original = match.group(1)
            if original and len(original) >= 2:
                placeholder = self._next_placeholder("address")
                mapping[placeholder] = original
                masked = masked.replace(original, placeholder, 1)

        # 4. 脱敏已知姓名
        if known_names:
            # 按长度降序排列，避免短名匹配到长名的子串
            sorted_names = sorted(known_names, key=len, reverse=True)
            for name in sorted_names:
                if name and name in masked:
                    placeholder = self._next_placeholder("name")
                    mapping[placeholder] = name
                    masked = masked.replace(name, placeholder)

        return masked, mapping

    def unmask(self, text: str, mapping: dict) -> str:
        """将大模型返回结果中的占位符还原为原始信息。"""
        result = text
        for placeholder, original in mapping.items():
            result = result.replace(placeholder, original)
        return result
