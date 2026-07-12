#!/usr/bin/env python3
"""
真实 LLM 回复解析专项测试
使用 parse_and_save 方法（需要数据库）
"""
import pytest
import os
import sys
from datetime import datetime
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


@pytest.mark.real_llm
class TestRealReplyParsing:
    """真实回复解析测试"""

    @pytest.fixture(scope="class")
    def parser(self, real_llm, real_config):
        from ai.reply_parser import ReplyParser
        return ReplyParser(real_config, real_llm)

    def test_appointment_reply(self, parser, real_db):
        """测试预约回复解析"""
        # 创建测试客户
        from db_models import Client
        client = Client(
            client_id=str(uuid.uuid4()),
            name="测试客户",
            phone="13800138000",
            lifecycle_status="active",
            created_at=datetime.now(),
        )
        real_db.add(client)
        real_db.commit()

        result = parser.parse_and_save(
            real_db,
            client.client_id,
            "明天下午三点想预约艾灸，能安排吗？"
        )

        print(f"\n预约回复解析结果: {result['data']}")
        assert result["success"] == True
        assert result["data"]["intent"] == "want_booking"
        assert result["data"]["sentiment"] in ["positive", "neutral"]

    def test_feedback_positive(self, parser, real_db):
        """测试正面反馈解析"""
        from db_models import Client
        client = Client(
            client_id=str(uuid.uuid4()),
            name="测试客户",
            phone="13800138001",
            lifecycle_status="active",
            created_at=datetime.now(),
        )
        real_db.add(client)
        real_db.commit()

        result = parser.parse_and_save(
            real_db,
            client.client_id,
            "上次服务效果很好，谢谢"
        )

        print(f"\n正面反馈解析结果: {result['data']}")
        assert result["success"] == True
        assert result["data"]["intent"] == "symptom_improved"
        assert result["data"]["sentiment"] == "positive"

    def test_negative_feedback(self, parser, real_db):
        """测试负面反馈解析"""
        from db_models import Client
        client = Client(
            client_id=str(uuid.uuid4()),
            name="测试客户",
            phone="13800138002",
            lifecycle_status="active",
            created_at=datetime.now(),
        )
        real_db.add(client)
        real_db.commit()

        result = parser.parse_and_save(
            real_db,
            client.client_id,
            "上次等待时间太长了，很不满意"
        )

        print(f"\n负面反馈解析结果: {result['data']}")
        assert result["success"] == True
        assert result["data"]["intent"] == "negative"
        assert result["data"]["sentiment"] == "negative"

    def test_general_chat(self, parser, real_db):
        """测试普通寒暄"""
        from db_models import Client
        client = Client(
            client_id=str(uuid.uuid4()),
            name="测试客户",
            phone="13800138003",
            lifecycle_status="active",
            created_at=datetime.now(),
        )
        real_db.add(client)
        real_db.commit()

        result = parser.parse_and_save(
            real_db,
            client.client_id,
            "收到，谢谢"
        )

        print(f"\n普通寒暄解析结果: {result['data']}")
        assert result["success"] == True
        assert result["data"]["intent"] == "general_chat"


@pytest.mark.real_llm
class TestRealContentGeneration:
    """真实内容生成测试"""

    def test_post_service_content(self, real_llm, real_config, real_db):
        """测试服务后关怀文案"""
        from ai.content_generator import ContentGenerator

        generator = ContentGenerator(real_config, real_llm)
        variables = {
            "client_name": "张女士",
            "service_info": "艾灸调理",
            "days_info": "3天",
            "analysis_type": "气虚质",
        }

        result = generator.generate(real_db, "post_service_followup", variables)

        print(f"\n服务后关怀文案: {result}")
        if result["success"]:
            print(f"内容: {result['content'][:200]}...")
        assert result["success"] == True or "缺少变量" in result["error"]
        assert len(result["content"]) > 20

    def test_birthday_content(self, real_llm, real_config, real_db):
        """测试生日祝福文案"""
        from ai.content_generator import ContentGenerator

        generator = ContentGenerator(real_config, real_llm)
        variables = {
            "client_name": "李先生",
            "birth_date": "1990-06-15",
        }

        result = generator.generate(real_db, "birthday_greeting", variables)

        print(f"\n生日祝福文案: {result['content'][:200]}...")
        assert result["success"] == True
        assert "生日" in result["content"] or "祝福" in result["content"]

    def test_seasonal_content(self, real_llm, real_config, real_db):
        """测试节气养生文案"""
        from ai.content_generator import ContentGenerator

        generator = ContentGenerator(real_config, real_llm)
        variables = {
            "client_name": "王女士",
            "season": "春季",
            "analysis_type": "阳虚质",
            "key_symptoms": "怕冷、手脚冰凉",
        }

        result = generator.generate(real_db, "seasonal_care", variables)

        print(f"\n节气养生文案: {result}")
        if result["success"]:
            print(f"内容: {result['content'][:200]}...")
        assert result["success"] == True or "缺少变量" in result["error"]


# 运行命令:
# pytest tests/test_reply_parser_real.py -v

if __name__ == "__main__":
    pytest.main([__file__, "-v"])