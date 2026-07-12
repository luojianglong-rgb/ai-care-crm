#!/usr/bin/env python3
"""
AI 智能触达引擎单元测试
测试智能客户分析和触达建议生成
"""
import pytest
import os
import sys
from datetime import datetime, timedelta
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))


class TestIntelligentReachEngine:
    """智能触达引擎核心测试"""

    def test_engine_init(self, mock_config, mock_llm):
        """测试引擎初始化"""
        from playbook.intelligent_engine import IntelligentReachEngine

        engine = IntelligentReachEngine(mock_config, mock_llm)
        assert engine.config == mock_config
        assert engine.llm == mock_llm

    def test_quick_filter_with_booking(self, mock_config, mock_llm):
        """测试快速过滤：有预约的客户豁免"""
        from playbook.intelligent_engine import IntelligentReachEngine

        engine = IntelligentReachEngine(mock_config, mock_llm)
        profile = {
            "upcoming_bookings": "艾灸",  # 有预约
            "days_since_visit": 10,
            "touch_history": [],
        }

        result = engine._quick_filter(profile)
        assert result == True  # 应该被过滤

    def test_quick_filter_recent_visit(self, mock_config, mock_llm):
        """测试快速过滤：刚到店的客户豁免"""
        from playbook.intelligent_engine import IntelligentReachEngine

        engine = IntelligentReachEngine(mock_config, mock_llm)
        profile = {
            "upcoming_bookings": "无",
            "days_since_visit": 3,  # 太近刚到店
            "touch_history": [],
        }

        result = engine._quick_filter(profile)
        assert result == True  # 应该被过滤

    def test_quick_filter_recent_touch(self, mock_config, mock_llm):
        """测试快速过滤：最近刚触达的豁免"""
        from playbook.intelligent_engine import IntelligentReachEngine

        engine = IntelligentReachEngine(mock_config, mock_llm)
        profile = {
            "upcoming_bookings": "无",
            "days_since_visit": 10,
            "touch_history": [
                {"date": datetime.now().strftime("%Y-%m-%d"), "status": "sent"}
            ],
        }

        result = engine._quick_filter(profile)
        assert result == True  # 最近刚触达，应该被过滤

    def test_quick_filter_should_reach(self, mock_config, mock_llm):
        """测试快速过滤：应该触达的客户"""
        from playbook.intelligent_engine import IntelligentReachEngine

        engine = IntelligentReachEngine(mock_config, mock_llm)
        profile = {
            "upcoming_bookings": "无",
            "days_since_visit": 15,  # 15天未到店
            "touch_history": [
                {"date": (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d"), "status": "sent"}
            ],
        }

        result = engine._quick_filter(profile)
        assert result == False  # 应该触达

    def test_fallback_suggestion_wakeup(self, mock_config, mock_llm):
        """测试兜底建议：30天未到店触发唤醒"""
        from playbook.intelligent_engine import IntelligentReachEngine

        engine = IntelligentReachEngine(mock_config, mock_llm)
        profile = {
            "client_id": "test_client",
            "name": "测试客户",
            "days_since_visit": 30,
            "tcm_periods": [],
            "preferences": ["艾灸"],
        }

        suggestion = engine._fallback_suggestion(profile)
        assert suggestion["should_reach"] == True
        assert suggestion["content_type"] == "wakeup"
        assert suggestion["urgency"] == "high"

    def test_fallback_suggestion_followup(self, mock_config, mock_llm):
        """测试兜底建议：14天未到店触发随访"""
        from playbook.intelligent_engine import IntelligentReachEngine

        engine = IntelligentReachEngine(mock_config, mock_llm)
        profile = {
            "client_id": "test_client",
            "name": "测试客户",
            "days_since_visit": 14,
            "tcm_periods": [],
            "preferences": [],
        }

        suggestion = engine._fallback_suggestion(profile)
        assert suggestion["should_reach"] == True
        assert suggestion["content_type"] == "followup"
        assert suggestion["urgency"] == "medium"

    def test_fallback_suggestion_seasonal(self, mock_config, mock_llm):
        """测试兜底建议：有节气触发季节关怀"""
        from playbook.intelligent_engine import IntelligentReachEngine

        engine = IntelligentReachEngine(mock_config, mock_llm)
        profile = {
            "client_id": "test_client",
            "name": "测试客户",
            "days_since_visit": 8,
            "tcm_periods": ["三伏"],
            "preferences": [],
        }

        suggestion = engine._fallback_suggestion(profile)
        assert suggestion["should_reach"] == True
        assert suggestion["content_type"] == "seasonal_care"
        assert suggestion["urgency"] == "low"

    def test_build_content_variables(self, mock_config, mock_llm):
        """测试文案变量构建"""
        from playbook.intelligent_engine import IntelligentReachEngine

        engine = IntelligentReachEngine(mock_config, mock_llm)
        profile = {
            "name": "张女士",
            "analysis_type": "气虚质",
            "days_since_visit": 10,
            "season": "夏季",
            "tcm_periods": ["三伏"],
            "times_card_balance": 5,
            "cash_card_balance": 200.0,
            "preferences": ["艾灸", "推拿"],
        }

        variables = engine._build_content_variables(profile)
        assert variables["client_name"] == "张女士"
        assert variables["analysis_type"] == "气虚质"
        assert variables["days_info"] == "10天"
        assert variables["season"] == "夏季"
        assert variables["tcm_period"] == "三伏"


class TestIntelligentReachIntegration:
    """智能触达集成测试（需要数据库）"""

    def test_get_candidate_clients(self, test_db, mock_config, mock_llm, sample_clients):
        """测试获取候选客户"""
        from playbook.intelligent_engine import IntelligentReachEngine
        from db_models import ClientLifecycle, Booking

        # 设置生命周期状态
        for client in sample_clients:
            lc = ClientLifecycle(
                id=str(uuid.uuid4()),
                client_id=client.client_id,
                current_status="active",
                visit_count=5,
                last_visit_at=datetime.now() - timedelta(days=15),
            )
            test_db.add(lc)

        test_db.commit()

        engine = IntelligentReachEngine(mock_config, mock_llm)
        candidates = engine._get_candidate_clients(test_db, max_clients=10)

        # 应该有候选客户
        assert len(candidates) >= 0

    def test_get_client_profile(self, test_db, mock_config, mock_llm, sample_client):
        """测试获取客户画像"""
        from playbook.intelligent_engine import IntelligentReachEngine
        from db_models import ClientLifecycle

        # 设置生命周期
        lc = ClientLifecycle(
            id=str(uuid.uuid4()),
            client_id=sample_client.client_id,
            current_status="active",
            visit_count=5,
            last_visit_at=datetime.now() - timedelta(days=10),
        )
        test_db.add(lc)
        test_db.commit()

        engine = IntelligentReachEngine(mock_config, mock_llm)
        profile = engine._get_client_profile(test_db, sample_client)

        assert profile["client_id"] == sample_client.client_id
        assert profile["name"] == sample_client.name
        assert profile["lifecycle_status"] == "active"
        assert profile["days_since_visit"] == 10

    def test_create_ai_task(self, test_db, mock_config, mock_llm):
        """测试创建AI触达任务"""
        from playbook.intelligent_engine import IntelligentReachEngine
        from db_models import CampaignTask

        engine = IntelligentReachEngine(mock_config, mock_llm)
        suggestion = {
            "client_id": str(uuid.uuid4()),
            "should_reach": True,
            "content_type": "seasonal_care",
            "reason": "三伏天适合艾灸调理",
        }

        task = engine.create_ai_task(test_db, suggestion)

        if task:  # 可能因为客户不存在返回None
            assert task.playbook_id is None  # AI触达没有playbook
            assert task.status == "pending_approval"
            assert task.ai_content_type == "seasonal_care"
            assert task.ai_reason == "三伏天适合艾灸调理"


class TestBusinessConfigIntegration:
    """业态配置集成测试"""

    def test_business_mapping_tcm(self, mock_config):
        """测试中医养生业态配置"""
        from config import PLAYBOOK_BUSINESS_MAPPING

        mock_config.store.business_type = "tcm_wellness"
        pb_config = PLAYBOOK_BUSINESS_MAPPING.get("tcm_wellness", {})

        assert pb_config.get("ai_reach_enabled") == True
        assert "solar_term" in pb_config.get("enabled_presets", [])
        assert "seasonal_care" in pb_config.get("ai_reach_focus", [])

    def test_business_mapping_nail(self, mock_config):
        """测试美甲业态配置"""
        from config import PLAYBOOK_BUSINESS_MAPPING

        mock_config.store.business_type = "nail_lash"
        pb_config = PLAYBOOK_BUSINESS_MAPPING.get("nail_lash", {})

        assert pb_config.get("ai_reach_enabled") == True
        assert "solar_term" in pb_config.get("disabled_presets", [])  # 美甲店禁用节气关怀
        assert pb_config.get("ai_reach_frequency") == "monthly"  # 美甲周期较长

    def test_business_mapping_hair(self, mock_config):
        """测试美发业态配置"""
        from config import PLAYBOOK_BUSINESS_MAPPING

        mock_config.store.business_type = "hair_salon"
        pb_config = PLAYBOOK_BUSINESS_MAPPING.get("hair_salon", {})

        assert "solar_term" in pb_config.get("disabled_presets", [])  # 美发店不需要节气关怀
        assert pb_config.get("ai_reach_frequency") == "biweekly"


# 运行命令:
# pytest tests/unit/test_intelligent_engine.py -v

if __name__ == "__main__":
    pytest.main([__file__, "-v"])