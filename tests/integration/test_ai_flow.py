#!/usr/bin/env python3
"""
AI 分析完整流程集成测试
"""
import pytest
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from db_models import Client, ProfessionalAnalysis, AIUsageRecord
from services.client_service import ClientService
from models import ClientCreate
from tests.utils.mock_llm import create_mock_llm_for_analysis
import uuid


class TestAIAnalysisFlow:
    """AI 分析完整流程测试"""

    def test_full_analysis_flow_basic(self, test_db, mock_config):
        """测试基本 AI 分析流程"""
        # 1. 创建客户
        client_in = ClientCreate(
            name="测试客户",
            phone="13800138000",
            gender="女",
            age_group="30-40",
        )
        client = ClientService.create_client(test_db, client_in)

        # 2. Mock LLM 分析
        mock_llm = create_mock_llm_for_analysis()
        parsed, response = mock_llm.chat_json(
            "体质分析",
            "最近感觉疲乏无力，气短懒言"
        )

        # 3. 验证分析结果
        assert response.success == True
        assert parsed["type"] == "气虚质"

        # 4. 存储分析结果（模拟）
        analysis = ProfessionalAnalysis(
            id=str(uuid.uuid4()),
            client_id=client.client_id,
            analysis_type="体质辨识",
            result=parsed,
            created_at=datetime.now(),
        )
        test_db.add(analysis)
        test_db.commit()

        # 5. 验证存储
        saved = test_db.query(ProfessionalAnalysis).filter(
            ProfessionalAnalysis.client_id == client.client_id
        ).first()

        assert saved is not None
        assert saved.analysis_type == "体质辨识"

    def test_full_analysis_flow_with_quota(self, test_db, mock_config):
        """测试含额度扣减的 AI 分析流程"""
        from services.quota_service import QuotaService

        # 1. 设置额度
        mock_config.current_tier = "basic"
        mock_config._quota_cache = {"basic": {"ai_total_limit": 20}}

        # 2. 创建客户
        client = Client(
            client_id=str(uuid.uuid4()),
            name="额度测试客户",
            phone="13800138001",
            gender="女",
            age_group="30-40",
            created_at=datetime.now(),
        )
        test_db.add(client)
        test_db.commit()

        # 3. 检查额度
        quota_service = QuotaService(mock_config)
        allowed, msg = quota_service.check_quota(test_db, "analysis")

        assert allowed == True

        # 4. 执行分析
        mock_llm = create_mock_llm_for_analysis()
        parsed, response = mock_llm.chat_json("体质分析", "测试症状")

        assert response.success == True

        # 5. 记录使用（模拟）
        record = AIUsageRecord(
            id=str(uuid.uuid4()),
            usage_type="analysis",
            success=1,
            created_at=datetime.now(),
        )
        test_db.add(record)
        test_db.commit()

        # 6. 再次检查额度（应该减少）
        count = test_db.query(AIUsageRecord).filter(
            AIUsageRecord.usage_type == "analysis",
            AIUsageRecord.success == 1
        ).count()

        assert count == 1


class TestAIContentFlow:
    """AI 文案生成完整流程测试"""

    def test_full_content_flow(self, test_db, mock_config):
        """测试文案生成流程"""
        from ai.content_generator import ContentGenerator
        from tests.utils.mock_llm import create_mock_llm_for_content

        # 1. 创建客户
        client = Client(
            client_id=str(uuid.uuid4()),
            name="文案测试客户",
            phone="13800138002",
            birth_date="1990-06-15",
            lifecycle_status="active",
            created_at=datetime.now(),
        )
        test_db.add(client)
        test_db.commit()

        # 2. 生成文案
        mock_llm = create_mock_llm_for_content()
        generator = ContentGenerator(mock_config, mock_llm)

        variables = {
            "client_name": client.name,
            "birth_date": client.birth_date,
        }

        result = generator.generate(test_db, "birthday_greeting", variables)

        # 3. 验证文案
        assert result["success"] == True
        assert "生日" in result["content"]

        # 4. 记录使用
        record = AIUsageRecord(
            id=str(uuid.uuid4()),
            usage_type="content",
            success=1,
            created_at=datetime.now(),
        )
        test_db.add(record)
        test_db.commit()

        assert test_db.query(AIUsageRecord).count() == 1


class TestAIReplyFlow:
    """AI 回复解析完整流程测试"""

    def test_full_reply_flow(self, test_db, mock_config):
        """测试回复解析流程"""
        from ai.reply_parser import ReplyParser
        from db_models import ClientReply
        from tests.utils.mock_llm import create_mock_llm_for_reply

        # 1. 创建客户
        client = Client(
            client_id=str(uuid.uuid4()),
            name="回复测试客户",
            phone="13800138003",
            lifecycle_status="active",
            created_at=datetime.now(),
        )
        test_db.add(client)
        test_db.commit()

        # 2. 解析回复
        mock_llm = create_mock_llm_for_reply()
        parser = ReplyParser(mock_config, mock_llm)

        result = parser.parse("明天下午想预约艾灸服务")

        # 3. 验证解析结果
        assert result["intent"] == "appointment"
        assert result["suggested_action"] == "创建预约"

        # 4. 存储回复
        reply = ClientReply(
            id=str(uuid.uuid4()),
            client_id=client.client_id,
            raw_content="明天下午想预约艾灸服务",
            ai_parsed_intent=result["intent"],
            ai_parsed_details=result["details"],
            auto_action_taken=result["suggested_action"],
            created_at=datetime.now(),
        )
        test_db.add(reply)
        test_db.commit()

        # 5. 验证存储
        saved = test_db.query(ClientReply).filter(
            ClientReply.client_id == client.client_id
        ).first()

        assert saved is not None
        assert saved.ai_parsed_intent == "appointment"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])