#!/usr/bin/env python3
"""
额度服务单元测试
"""
import pytest
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from services.quota_service import QuotaService
from config import AppConfig, QuotaTier


class TestQuotaServiceBasic:
    """基础版额度测试"""

    def test_check_quota_basic_allowed(self, test_db, mock_config):
        """测试基础版额度检查（允许）"""
        mock_config.current_tier = "basic"
        mock_config._quota_cache = {"basic": QuotaTier(ai_total_limit=20)}

        service = QuotaService(mock_config)
        allowed, msg = service.check_quota(test_db, "analysis")

        assert allowed == True
        assert "额度充足" in msg or "20" in msg

    def test_check_quota_basic_exceeded(self, test_db, mock_config):
        """测试基础版额度检查（已用完）"""
        from db_models import AIUsageRecord

        mock_config.current_tier = "basic"
        mock_config._quota_cache = {"basic": QuotaTier(ai_total_limit=20)}

        # 创建20条使用记录
        for i in range(20):
            record = AIUsageRecord(
                id=i+1,
                usage_type="analysis",
                success=1,
                created_at=datetime.now(),
            )
            test_db.add(record)
        test_db.commit()

        service = QuotaService(mock_config)
        allowed, msg = service.check_quota(test_db, "analysis")

        assert allowed == False
        assert "用完" in msg or "20" in msg

    def test_check_quota_basic_with_limit_10(self, test_db, mock_config):
        """测试基础版10次限制"""
        from db_models import AIUsageRecord

        mock_config.current_tier = "basic"
        mock_config._quota_cache = {"basic": QuotaTier(ai_total_limit=10)}

        # 创建5条使用记录
        for i in range(5):
            record = AIUsageRecord(
                id=i+1,
                usage_type="plan",
                success=1,
                created_at=datetime.now(),
            )
            test_db.add(record)
        test_db.commit()

        service = QuotaService(mock_config)
        allowed, msg = service.check_quota(test_db, "plan")

        assert allowed == True
        assert "5" in msg or "额度充足" in msg


class TestQuotaServicePro:
    """专业版额度测试"""

    def test_check_quota_pro_weekly_allowed(self, test_db, mock_config_pro):
        """测试专业版每周额度检查（允许）"""
        service = QuotaService(mock_config_pro)
        allowed, msg = service.check_quota(test_db, "analysis")

        assert allowed == True

    def test_check_quota_pro_weekly_exceeded(self, test_db, mock_config_pro):
        """测试专业版每周额度检查（已用完）"""
        from db_models import AIUsageRecord

        # 创建本周的50条使用记录
        week_start = datetime.now() - timedelta(days=datetime.now().weekday())
        for i in range(50):
            record = AIUsageRecord(
                id=i+1,
                usage_type="content",
                success=1,
                created_at=week_start + timedelta(days=i % 7),
            )
            test_db.add(record)
        test_db.commit()

        service = QuotaService(mock_config_pro)
        allowed, msg = service.check_quota(test_db, "content")

        assert allowed == False
        assert "用完" in msg or "升级" in msg

    def test_get_weekly_usage(self, test_db, mock_config_pro):
        """测试获取本周使用次数"""
        from db_models import AIUsageRecord

        # 创建本周的5条记录
        week_start = datetime.now() - timedelta(days=datetime.now().weekday())
        for i in range(5):
            record = AIUsageRecord(
                id=i+1,
                usage_type="analysis",
                success=1,
                created_at=datetime.now(),
            )
            test_db.add(record)
        test_db.commit()

        service = QuotaService(mock_config_pro)
        count = service.get_weekly_usage(test_db, "analysis")

        assert count == 5


class TestQuotaServiceBusiness:
    """至尊版额度测试"""

    def test_check_quota_business_unlimited(self, test_db, mock_config_business):
        """测试至尊版无限制"""
        service = QuotaService(mock_config_business)
        allowed, msg = service.check_quota(test_db, "analysis")

        assert allowed == True
        assert "不限" in msg or "额度充足" in msg

    def test_check_quota_business_monthly(self, test_db, mock_config_business):
        """测试至尊版月度额度（有限制时）"""
        from db_models import AIUsageRecord

        # 设置月度限制
        mock_config_business._quota_cache["business"].ai_analysis_per_month = 200

        # 创建100条本月记录
        month_key = datetime.now().strftime("%Y-%m")
        for i in range(100):
            record = AIUsageRecord(
                id=i+1,
                usage_type="analysis",
                month_key=month_key,
                success=1,
                created_at=datetime.now(),
            )
            test_db.add(record)
        test_db.commit()

        service = QuotaService(mock_config_business)
        allowed, msg = service.check_quota(test_db, "analysis")

        assert allowed == True
        assert "100" in msg or "额度充足" in msg


class TestQuotaServiceDevMode:
    """开发模式测试"""

    def test_check_quota_dev_mode_bypass(self, test_db, mock_config_dev):
        """测试开发模式绕过限制"""
        service = QuotaService(mock_config_dev)
        allowed, msg = service.check_quota(test_db, "analysis")

        assert allowed == True
        assert "开发模式" in msg or "不限" in msg


class TestQuotaHelperMethods:
    """辅助方法测试"""

    def test_current_month_key(self, mock_config):
        """测试月度 Key 生成"""
        service = QuotaService(mock_config)
        key = service._current_month_key()

        assert key == datetime.now().strftime("%Y-%m")

    def test_current_week_key(self, mock_config):
        """测试周 Key 生成"""
        service = QuotaService(mock_config)
        key = service._current_week_key()

        assert key == datetime.now().strftime("%Y-%W")

    def test_week_start_date(self, mock_config):
        """测试本周一日期"""
        service = QuotaService(mock_config)
        week_start = service._week_start_date()

        # 应该是本周一
        today = datetime.now()
        expected = today - timedelta(days=today.weekday())

        assert week_start.date() == expected.date()


class TestSMSQuota:
    """短信额度测试"""

    def test_check_sms_quota_business_allowed(self, test_db, mock_config_business):
        """测试至尊版短信额度"""
        service = QuotaService(mock_config_business)
        allowed, msg = service.check_sms_quota(test_db)

        # 至尊版应该允许
        assert allowed == True

    def test_check_sms_quota_basic_denied(self, test_db, mock_config):
        """测试基础版短信额度（不允许）"""
        mock_config.current_tier = "basic"
        service = QuotaService(mock_config)
        allowed, msg = service.check_sms_quota(test_db)

        # 基础版不应该允许
        assert allowed == False
        assert "至尊版" in msg or "升级" in msg


if __name__ == "__main__":
    pytest.main([__file__, "-v"])