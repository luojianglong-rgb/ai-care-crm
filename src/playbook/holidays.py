"""
中国法定节假日数据模块
提供节假日日期、判断临近节假日、获取不出游客户特征等功能。
支持：节前预约提醒、不出游客户关怀、节日祝福问候。
"""
import logging
from datetime import datetime, timedelta, date
from typing import Optional

logger = logging.getLogger(__name__)

# ── 中国法定节假日配置 ──────────────────────────────────────────────
# 格式：{"name": 节日名, "date": MM-DD, "days": 假期天数, "type": 类型}

HOLIDAYS_CONFIG = {
    # 传统节日（适合祝福问候）
    "spring_festival": {
        "name": "春节",
        "date": None,  # 动态计算（农历正月初一）
        "days": 7,
        "type": "traditional",
        "greeting_type": "新春祝福",
        "care_before_days": 14,  # 节前14天开始关怀
        "appointment_before_days": 7,  # 节前7天预约提醒
    },
    "qingming": {
        "name": "清明节",
        "date": "04-04",  # 或04-05，需动态调整
        "days": 3,
        "type": "traditional",
        "greeting_type": "清明安康",
        "care_before_days": 5,
        "appointment_before_days": 3,
    },
    "labor_day": {
        "name": "五一劳动节",
        "date": "05-01",
        "days": 5,
        "type": "modern",
        "greeting_type": "节日快乐",
        "care_before_days": 10,
        "appointment_before_days": 5,
    },
    "dragon_boat": {
        "name": "端午节",
        "date": None,  # 动态计算（农历五月初五）
        "days": 3,
        "type": "traditional",
        "greeting_type": "端午安康",
        "care_before_days": 7,
        "appointment_before_days": 3,
    },
    "mid_autumn": {
        "name": "中秋节",
        "date": None,  # 动态计算（农历八月十五）
        "days": 3,
        "type": "traditional",
        "greeting_type": "中秋团圆",
        "care_before_days": 7,
        "appointment_before_days": 3,
    },
    "national_day": {
        "name": "国庆节",
        "date": "10-01",
        "days": 7,
        "type": "modern",
        "greeting_type": "节日快乐",
        "care_before_days": 14,
        "appointment_before_days": 7,
    },
    "new_year": {
        "name": "元旦",
        "date": "01-01",
        "days": 3,
        "type": "modern",
        "greeting_type": "新年快乐",
        "care_before_days": 7,
        "appointment_before_days": 3,
    },
    # 西方节日（可选，适合SPA、美甲等业态）
    "valentine": {
        "name": "情人节",
        "date": "02-14",
        "days": 1,
        "type": "western",
        "greeting_type": "甜蜜祝福",
        "care_before_days": 5,
        "appointment_before_days": 3,
        "suitable_business": ["spa", "nail_lash", "hair_salon"],  # 仅适用特定业态
    },
    "womens_day": {
        "name": "三八妇女节",
        "date": "03-08",
        "days": 1,
        "type": "modern",
        "greeting_type": "女神节快乐",
        "care_before_days": 5,
        "appointment_before_days": 3,
        "suitable_business": ["spa", "nail_lash", "skin_care", "hair_salon"],
    },
    "mothers_day": {
        "name": "母亲节",
        "date": None,  # 动态计算（5月第二个周日）
        "days": 1,
        "type": "modern",
        "greeting_type": "感恩母爱",
        "care_before_days": 7,
        "appointment_before_days": 5,
        "suitable_business": ["spa", "nail_lash", "skin_care", "postpartum"],
    },
}

# 2026年节假日日期（春节、端午、中秋为农历节日，需要预先设置）
HOLIDAY_DATES_2026 = {
    "spring_festival": "2026-02-17",  # 2026年春节
    "dragon_boat": "2026-05-31",      # 2026年端午
    "mid_autumn": "2026-10-06",       # 2026年中秋
    "mothers_day": "2026-05-10",      # 2026母亲节（5月第二个周日）
}


class HolidayCalendar:
    """节假日日历计算"""

    @staticmethod
    def get_holiday_date(holiday_key: str, year: int = None) -> Optional[date]:
        """获取指定节日的日期"""
        if year is None:
            year = datetime.now().year

        config = HOLIDAYS_CONFIG.get(holiday_key)
        if not config:
            return None

        date_str = config["date"]
        if date_str is None:
            # 动态日期，从预置数据获取
            year_key = f"{holiday_key}"
            if year == 2026 and year_key in HOLIDAY_DATES_2026:
                return datetime.strptime(HOLIDAY_DATES_2026[year_key], "%Y-%m-%d").date()
            # 其他年份需要计算（简化：返回None）
            logger.warning(f"Holiday {holiday_key} date not configured for year {year}")
            return None

        # 固定日期（MM-DD格式）
        month, day = date_str.split("-")
        return date(year, int(month), int(day))

    @staticmethod
    def get_upcoming_holidays(days_ahead: int = 14) -> list[dict]:
        """获取未来N天内即将到来的节假日"""
        today = date.today()
        upcoming = []

        for holiday_key, config in HOLIDAYS_CONFIG.items():
            holiday_date = HolidayCalendar.get_holiday_date(holiday_key)
            if not holiday_date:
                continue

            days_until = (holiday_date - today).days
            if 0 <= days_until <= days_ahead:
                upcoming.append({
                    "key": holiday_key,
                    "name": config["name"],
                    "date": holiday_date.strftime("%Y-%m-%d"),
                    "days_until": days_until,
                    "type": config["type"],
                    "holiday_days": config["days"],
                    "greeting_type": config.get("greeting_type", "节日快乐"),
                    "care_before_days": config.get("care_before_days", 7),
                    "suitable_business": config.get("suitable_business", None),
                })

        # 按距离排序
        upcoming.sort(key=lambda x: x["days_until"])
        return upcoming

    @staticmethod
    def is_near_holiday(days_threshold: int = 7) -> tuple[bool, dict | None]:
        """判断是否临近节假日（节前N天内）"""
        upcoming = HolidayCalendar.get_upcoming_holidays(days_threshold)
        if upcoming:
            return True, upcoming[0]
        return False, None

    @staticmethod
    def is_holiday_today() -> tuple[bool, dict | None]:
        """判断今天是否是节假日"""
        today = date.today()
        for holiday_key, config in HOLIDAYS_CONFIG.items():
            holiday_date = HolidayCalendar.get_holiday_date(holiday_key)
            if holiday_date and holiday_date == today:
                return True, {
                    "key": holiday_key,
                    "name": config["name"],
                    "type": config["type"],
                    "greeting_type": config.get("greeting_type", "节日快乐"),
                }
        return False, None

    @staticmethod
    def get_non_travel_client_criteria(holiday_key: str, business_type: str) -> dict:
        """获取不出游客户的筛选条件

        根据业态特点，判断哪些客户更可能不出游：
        - 有小孩/老人的客户（家庭出游可能性低）
        - 近期刚到店的客户（可能选择店内服务）
        - 卡项余额充足的客户（有消费意愿）
        - 年龄较大的客户（出游意愿低）
        """
        config = HOLIDAYS_CONFIG.get(holiday_key)
        if not config:
            return {}

        # 长假（7天）vs 短假（1-3天）
        is_long_holiday = config["days"] >= 5

        criteria = {
            "prefer_local": True,  # 优先本地服务
            "age_groups": ["40+", "50+"] if is_long_holiday else [],  # 长假更关注年长者
            "days_since_visit_max": 30,  # 最近30天到店过
            "min_card_balance": 100,  # 最低卡项余额
        }

        # 业态特定条件
        if business_type in ["postpartum", "tcm_wellness"]:
            # 产后修复、中医养生：这类客户本身出游意愿低
            criteria["prefer_local"] = True
            criteria["age_groups"] = []  # 不限年龄

        if business_type in ["spa", "nail_lash", "skin_care"]:
            # SPA/美甲/皮肤管理：长假可能出游，短假更可能本地
            criteria["prefer_local"] = not is_long_holiday

        return criteria

    @staticmethod
    def get_holiday_context() -> dict:
        """获取当前节假日上下文信息"""
        today = date.today()

        # 今天是否是节假日
        is_holiday, holiday_info = HolidayCalendar.is_holiday_today()

        # 是否临近节假日
        is_near, near_info = HolidayCalendar.is_near_holiday(14)

        # 获取即将到来的所有节假日
        upcoming = HolidayCalendar.get_upcoming_holidays(30)

        return {
            "is_holiday_today": is_holiday,
            "today_holiday": holiday_info,
            "is_near_holiday": is_near,
            "nearest_holiday": near_info,
            "upcoming_holidays": upcoming,
            "holiday_count_next_30_days": len(upcoming),
        }


def get_holiday_greeting_prompt(holiday_info: dict, business_type: str) -> str:
    """生成节假日问候提示词片段"""
    name = holiday_info.get("name", "")
    greeting_type = holiday_info.get("greeting_type", "节日快乐")

    return f"""
当前节日：{name}
问候类型：{greeting_type}
业态适配：{business_type}

请在文案中：
1. 表达节日问候（{greeting_type}）
2. 结合业态特点给出节日关怀建议
3. 如是传统节日，可融入节日养生/护理知识
"""


def should_trigger_holiday_care(holiday_key: str, business_type: str) -> bool:
    """判断该业态是否应该触发节假日关怀"""
    config = HOLIDAYS_CONFIG.get(holiday_key)
    if not config:
        return False

    # 检查业态适配
    suitable = config.get("suitable_business")
    if suitable:
        return business_type in suitable

    # 默认所有业态都触发传统节日和法定节假日
    return config["type"] in ["traditional", "modern"]