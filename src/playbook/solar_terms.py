"""
二十四节气 / 季节日历工具 + 中医养生重要节点
内置 2024-2030 年节气精确日期，用于剧本触发和 Prompt 注入。
支持：二十四节气、三九、三伏、长夏、四季、梅雨、秋老虎等中医养生节点
"""
from datetime import date, datetime, timedelta

# 2024-2030 年二十四节气日期表（精确到日）
SOLAR_TERMS = {
    2024: {
        "小寒": "01-06", "大寒": "01-20", "立春": "02-04", "雨水": "02-19",
        "惊蛰": "03-05", "春分": "03-20", "清明": "04-04", "谷雨": "04-19",
        "立夏": "05-05", "小满": "05-20", "芒种": "06-05", "夏至": "06-21",
        "小暑": "07-06", "大暑": "07-22", "立秋": "08-07", "处暑": "08-22",
        "白露": "09-07", "秋分": "09-22", "寒露": "10-08", "霜降": "10-23",
        "立冬": "11-07", "小雪": "11-22", "大雪": "12-06", "冬至": "12-21",
    },
    2025: {
        "小寒": "01-05", "大寒": "01-20", "立春": "02-03", "雨水": "02-18",
        "惊蛰": "03-05", "春分": "03-20", "清明": "04-04", "谷雨": "04-20",
        "立夏": "05-05", "小满": "05-21", "芒种": "06-05", "夏至": "06-21",
        "小暑": "07-07", "大暑": "07-22", "立秋": "08-07", "处暑": "08-23",
        "白露": "09-07", "秋分": "09-22", "寒露": "10-08", "霜降": "10-23",
        "立冬": "11-07", "小雪": "11-22", "大雪": "12-07", "冬至": "12-21",
    },
    2026: {
        "小寒": "01-06", "大寒": "01-20", "立春": "02-04", "雨水": "02-19",
        "惊蛰": "03-06", "春分": "03-21", "清明": "04-05", "谷雨": "04-20",
        "立夏": "05-06", "小满": "05-21", "芒种": "06-06", "夏至": "06-21",
        "小暑": "07-07", "大暑": "07-23", "立秋": "08-07", "处暑": "08-23",
        "白露": "09-08", "秋分": "09-23", "寒露": "10-08", "霜降": "10-23",
        "立冬": "11-07", "小雪": "11-22", "大雪": "12-07", "冬至": "12-22",
    },
    2027: {
        "小寒": "01-05", "大寒": "01-20", "立春": "02-04", "雨水": "02-19",
        "惊蛰": "03-06", "春分": "03-21", "清明": "04-05", "谷雨": "04-20",
        "立夏": "05-06", "小满": "05-21", "芒种": "06-06", "夏至": "06-21",
        "小暑": "07-07", "大暑": "07-23", "立秋": "08-08", "处暑": "08-23",
        "白露": "09-08", "秋分": "09-23", "寒露": "10-09", "霜降": "10-24",
        "立冬": "11-08", "小雪": "11-22", "大雪": "12-07", "冬至": "12-22",
    },
    2028: {
        "小寒": "01-06", "大寒": "01-20", "立春": "02-04", "雨水": "02-19",
        "惊蛰": "03-05", "春分": "03-20", "清明": "04-04", "谷雨": "04-19",
        "立夏": "05-05", "小满": "05-20", "芒种": "06-05", "夏至": "06-21",
        "小暑": "07-07", "大暑": "07-22", "立秋": "08-07", "处暑": "08-22",
        "白露": "09-07", "秋分": "09-22", "寒露": "10-08", "霜降": "10-23",
        "立冬": "11-07", "小雪": "11-22", "大雪": "12-06", "冬至": "12-21",
    },
    2029: {
        "小寒": "01-05", "大寒": "01-19", "立春": "02-03", "雨水": "02-18",
        "惊蛰": "03-05", "春分": "03-20", "清明": "04-04", "谷雨": "04-19",
        "立夏": "05-05", "小满": "05-20", "芒种": "06-05", "夏至": "06-21",
        "小暑": "07-07", "大暑": "07-22", "立秋": "08-07", "处暑": "08-22",
        "白露": "09-07", "秋分": "09-22", "寒露": "10-08", "霜降": "10-23",
        "立冬": "11-07", "小雪": "11-22", "大雪": "12-06", "冬至": "12-21",
    },
    2030: {
        "小寒": "01-05", "大寒": "01-20", "立春": "02-03", "雨水": "02-18",
        "惊蛰": "03-05", "春分": "03-20", "清明": "04-04", "谷雨": "04-20",
        "立夏": "05-05", "小满": "05-21", "芒种": "06-05", "夏至": "06-21",
        "小暑": "07-07", "大暑": "07-23", "立秋": "08-07", "处暑": "08-23",
        "白露": "09-07", "秋分": "09-23", "寒露": "10-08", "霜降": "10-23",
        "立冬": "11-07", "小雪": "11-22", "大雪": "12-07", "冬至": "12-22",
    },
}

# 节气顺序
TERM_ORDER = [
    "小寒", "大寒", "立春", "雨水", "惊蛰", "春分",
    "清明", "谷雨", "立夏", "小满", "芒种", "夏至",
    "小暑", "大暑", "立秋", "处暑", "白露", "秋分",
    "寒露", "霜降", "立冬", "小雪", "大雪", "冬至",
]

# 节气→季节映射
TERM_SEASON = {
    "立春": "春", "雨水": "春", "惊蛰": "春", "春分": "春", "清明": "春", "谷雨": "春",
    "立夏": "夏", "小满": "夏", "芒种": "夏", "夏至": "夏", "小暑": "夏", "大暑": "夏",
    "立秋": "秋", "处暑": "秋", "白露": "秋", "秋分": "秋", "寒露": "秋", "霜降": "秋",
    "立冬": "冬", "小雪": "冬", "大雪": "冬", "冬至": "冬", "小寒": "冬", "大寒": "冬",
}

# 四季划分（按节气）
SEASON_TERMS = {
    "春": ["立春", "雨水", "惊蛰", "春分", "清明", "谷雨"],
    "夏": ["立夏", "小满", "芒种", "夏至", "小暑", "大暑"],
    "秋": ["立秋", "处暑", "白露", "秋分", "寒露", "霜降"],
    "冬": ["立冬", "小雪", "大雪", "冬至", "小寒", "大寒"],
}

# 五运六气时间段（按节气划分）
WUYUN_SIXQI = {
    "初之气": {"terms": ["大寒", "雨水", "惊蛰", "春分"], "element": "厥阴风木", "focus": "疏风养肝"},
    "二之气": {"terms": ["春分", "清明", "谷雨", "立夏", "小满"], "element": "少阴君火", "focus": "清心降火"},
    "三之气": {"terms": ["小满", "芒种", "夏至", "小暑", "大暑"], "element": "少阳相火", "focus": "清热解暑"},
    "四之气": {"terms": ["大暑", "立秋", "处暑", "白露", "秋分"], "element": "太阴湿土", "focus": "健脾祛湿"},
    "五之气": {"terms": ["秋分", "寒露", "霜降", "立冬", "小雪"], "element": "阳明燥金", "focus": "润肺生津"},
    "终之气": {"terms": ["小雪", "大雪", "冬至", "小寒", "大寒"], "element": "太阳寒水", "focus": "温肾固本"},
}

# 传统节日（农历转公历需要复杂计算，这里使用近似日期）
LUNAR_FESTIVALS = {
    "春节": {"month": 1, "day": 1, "focus": "辞旧迎新，养肝起始"},
    "元宵": {"month": 1, "day": 15, "focus": "团圆养生，健脾和胃"},
    "端午": {"month": 5, "day": 5, "focus": "祛毒避邪，艾草养生"},
    "七夕": {"month": 7, "day": 7, "focus": "情人养生，美容养颜"},
    "中秋": {"month": 8, "day": 15, "focus": "团圆养肺，滋阴润燥"},
    "重阳": {"month": 9, "day": 9, "focus": "登高敬老，补肾强身"},
    "腊八": {"month": 12, "day": 8, "focus": "腊八粥养生，健脾养胃"},
}

# 中医养生重要节点说明
"""
三九天：冬至后的三个庚日（每 10 天为一个庚日），是一年中最寒冷的时期
  - 一九：冬至后第 1 个庚日开始 9 天
  - 二九：一九结束后开始 9 天
  - 三九：二九结束后开始 9 天（最冷）
  - 四九/五九/六九：延续寒冷

三伏天：夏至后的第三个庚日开始，是一年中最炎热潮湿的时期
  - 初伏：10 天（夏至后第 3 个庚日）
  - 中伏：10 或 20 天（夏至后第 4 个庚日）
  - 末伏：10 天（立秋后第 1 个庚日）

长夏：中医特有概念，指夏秋交替之际（大暑至白露），湿气最重
  - 时间：约 7 月下旬至 9 月上旬
  - 养生重点：健脾祛湿

梅雨季：长江中下游地区特有，约 6 月中旬至 7 月上旬
  - 养生重点：祛湿排毒

秋老虎：处暑后至秋分前，气温回升
  - 时间：约 8 月下旬至 9 月中旬
  - 养生重点：润燥养肺

五运六气：中医时间医学理论，将一年分为六个气候阶段
  - 初之气（大寒 - 春分）：厥阴风木，疏风养肝
  - 二之气（春分 - 小满）：少阴君火，清心降火
  - 三之气（小满 - 大暑）：少阳相火，清热解暑
  - 四之气（大暑 - 秋分）：太阴湿土，健脾祛湿
  - 五之气（秋分 - 小雪）：阳明燥金，润肺生津
  - 终之气（小雪 - 大寒）：太阳寒水，温肾固本

特殊节气养生：
  - 立春：养肝起始日，宜疏肝理气
  - 春分：阴阳平衡日，宜调和气血
  - 夏至：阳气最旺日，冬病夏治最佳时机
  - 秋分：滋阴润燥日，宜养肺润燥
  - 冬至：一阳始生日，进补最佳时机

朔望月相：
  - 朔日（初一）：月球在地球和太阳之间，阳气始生
  - 上弦（初七/初八）：阳气渐长
  - 望日（十五）：满月，阳气最盛
  - 下弦（廿二/廿三）：阴气渐长
  - 晦日（三十）：阴气最盛
"""


class SolarTermCalendar:

    @staticmethod
    def _get_terms_for_year(year: int) -> dict[str, date]:
        """获取某年的节气日期字典。"""
        raw = SOLAR_TERMS.get(year, {})
        result = {}
        for name, md in raw.items():
            result[name] = date(year, int(md[:2]), int(md[3:]))
        return result

    @staticmethod
    def _get_geng_days(year: int) -> list[date]:
        """
        计算某年的所有庚日（天干为庚的日子）。
        庚日计算公式：以 1900-01-08 为基准庚日，每 10 天一个庚日
        """
        base_geng = date(1900, 1, 8)  # 基准庚日
        start = date(year, 1, 1)
        end = date(year, 12, 31)

        geng_days = []
        delta = (start - base_geng).days
        offset = (10 - (delta % 10)) % 10
        first_geng = start + timedelta(days=offset)

        current = first_geng
        while current <= end:
            geng_days.append(current)
            current += timedelta(days=10)

        return geng_days

    @staticmethod
    def get_sanjiu_dates(year: int) -> dict[str, list[date]]:
        """
        计算某年的三九日期。
        三九从冬至后的第一个庚日开始，每 9 天为一九。
        """
        terms = SolarTermCalendar._get_terms_for_year(year)
        dongzhi = terms.get("冬至")
        if not dongzhi:
            return {}

        geng_days = SolarTermCalendar._get_geng_days(year)
        # 找到冬至后的第一个庚日
        after_dongzhi = [g for g in geng_days if g >= dongzhi]

        if len(after_dongzhi) < 1:
            # 可能跨年到下一年
            next_geng = SolarTermCalendar._get_geng_days(year + 1)
            after_dongzhi.extend(next_geng)

        result = {}
        if len(after_dongzhi) >= 1:
            # 一九从冬至后第一个庚日开始
            start_1jiu = after_dongzhi[0]
            result["一九"] = [start_1jiu + timedelta(days=j) for j in range(9)]

            # 二九紧接一九
            start_2jiu = start_1jiu + timedelta(days=9)
            result["二九"] = [start_2jiu + timedelta(days=j) for j in range(9)]

            # 三九
            start_3jiu = start_2jiu + timedelta(days=9)
            result["三九"] = [start_3jiu + timedelta(days=j) for j in range(9)]

            # 四九
            start_4jiu = start_3jiu + timedelta(days=9)
            result["四九"] = [start_4jiu + timedelta(days=j) for j in range(9)]

            # 五九
            start_5jiu = start_4jiu + timedelta(days=9)
            result["五九"] = [start_5jiu + timedelta(days=j) for j in range(9)]

            # 六九
            start_6jiu = start_5jiu + timedelta(days=9)
            result["六九"] = [start_6jiu + timedelta(days=j) for j in range(9)]

        return result

    @staticmethod
    def get_sanfu_dates(year: int) -> dict[str, list[date]]:
        """
        计算某年的三伏日期。
        初伏：夏至后第 3 个庚日，10 天
        中伏：夏至后第 4 个庚日，10 或 20 天
        末伏：立秋后第 1 个庚日，10 天
        """
        terms = SolarTermCalendar._get_terms_for_year(year)
        xiazhi = terms.get("夏至")
        liqiu = terms.get("立秋")
        if not xiazhi or not liqiu:
            return {}

        geng_days = SolarTermCalendar._get_geng_days(year)

        # 夏至后的庚日
        after_xiazhi = [g for g in geng_days if g >= xiazhi]
        # 立秋后的庚日
        after_liqiu = [g for g in geng_days if g >= liqiu]

        result = {}

        # 初伏（夏至后第 3 个庚日开始，10 天）
        if len(after_xiazhi) >= 3:
            start = after_xiazhi[2]
            result["初伏"] = [start + timedelta(days=j) for j in range(10)]

        # 中伏（夏至后第 4 个庚日开始，10 或 20 天）
        if len(after_xiazhi) >= 4:
            start = after_xiazhi[3]
            # 中伏长度：如果立秋在初伏后 20 天内，则中伏 10 天，否则 20 天
            days_to_liqiu = (liqiu - after_xiazhi[2]).days
            fu_length = 10 if days_to_liqiu <= 20 else 20
            result["中伏"] = [start + timedelta(days=j) for j in range(fu_length)]

        # 末伏（立秋后第 1 个庚日开始，10 天）
        if len(after_liqiu) >= 1:
            start = after_liqiu[0]
            result["末伏"] = [start + timedelta(days=j) for j in range(10)]

        return result

    @staticmethod
    def get_changxia_period(year: int) -> list[date]:
        """
        获取长夏时期（大暑至白露，约 7 月下旬至 9 月上旬）。
        中医认为长夏属土，主湿，对应脾。
        """
        terms = SolarTermCalendar._get_terms_for_year(year)
        dashu = terms.get("大暑")
        bailu = terms.get("白露")

        if not dashu or not bailu:
            return []

        # 返回大暑到白露之间的所有日期
        days = []
        current = dashu
        while current <= bailu:
            days.append(current)
            current += timedelta(days=1)
        return days

    @staticmethod
    def get_plum_rain_period(year: int) -> list[date]:
        """
        获取梅雨季节（约 6 月 10 日 -7 月 10 日，江南地区）。
        注意：这是近似日期，实际梅雨入梅/出梅每年不同。
        """
        start = date(year, 6, 10)
        end = date(year, 7, 10)
        return [start + timedelta(days=i) for i in range((end - start).days + 1)]

    @staticmethod
    def get_autumn_tiger_period(year: int) -> list[date]:
        """
        获取秋老虎时期（处暑至秋分，约 8 月 23 日 -9 月 22 日）。
        处暑后气温短暂回升，干燥渐重。
        """
        terms = SolarTermCalendar._get_terms_for_year(year)
        chushu = terms.get("处暑")
        qiufen = terms.get("秋分")

        if not chushu or not qiufen:
            return []

        days = []
        current = chushu
        while current <= qiufen:
            days.append(current)
            current += timedelta(days=1)
        return days

    @staticmethod
    def get_wuyun_sixqi_period(year: int) -> dict[str, dict]:
        """
        获取某年的五运六气时间段。
        返回字典包含各时段的日期范围和养生重点。
        """
        terms = SolarTermCalendar._get_terms_for_year(year)
        result = {}

        for qi_name, qi_info in WUYUN_SIXQI.items():
            start_term = qi_info["terms"][0]
            end_term = qi_info["terms"][-1]

            # 找到起始节气和结束节气的日期
            start_date = terms.get(start_term)
            # 结束日期是下一时段的开始前一天
            end_idx = TERM_ORDER.index(end_term) + 1
            if end_idx < len(TERM_ORDER):
                next_term = TERM_ORDER[end_idx]
                end_date = terms.get(next_term)
                if end_date:
                    end_date = end_date - timedelta(days=1)
            else:
                # 终之气结束是大寒，即到年底
                end_date = date(year, 12, 31)

            if start_date and end_date:
                days = []
                current = start_date
                while current <= end_date:
                    days.append(current)
                    current += timedelta(days=1)

                result[qi_name] = {
                    "dates": days,
                    "element": qi_info["element"],
                    "focus": qi_info["focus"],
                }

        return result

    @staticmethod
    def get_special_solar_terms(year: int) -> dict[str, date]:
        """
        获取特殊养生节气的日期。
        """
        terms = SolarTermCalendar._get_terms_for_year(year)
        special = {}

        # 立春：养肝起始
        if "立春" in terms:
            special["立春"] = {"date": terms["立春"], "focus": "养肝起始，疏肝理气"}

        # 春分：阴阳平衡
        if "春分" in terms:
            special["春分"] = {"date": terms["春分"], "focus": "阴阳平衡，调和气血"}

        # 夏至：阳气最旺，冬病夏治
        if "夏至" in terms:
            special["夏至"] = {"date": terms["夏至"], "focus": "阳气最旺，冬病夏治最佳时机"}

        # 秋分：滋阴润燥
        if "秋分" in terms:
            special["秋分"] = {"date": terms["秋分"], "focus": "滋阴润燥，养肺补肾"}

        # 冬至：一阳始生，进补最佳
        if "冬至" in terms:
            special["冬至"] = {"date": terms["冬至"], "focus": "一阳始生，进补最佳时机"}

        return special

    @staticmethod
    def get_lunar_festivals_approximate(year: int) -> dict[str, dict]:
        """
        获取传统节日的近似公历日期（简化计算，实际需农历转公历）。
        注意：这是近似日期，精确日期需要农历转换。
        """
        # 农历转公历的近似偏移（每年不同）
        # 这里使用简化方法，实际应使用农历库
        result = {}

        for name, info in LUNAR_FESTIVALS.items():
            # 春节在 1 月 21 日 -2 月 20 日之间浮动
            if name == "春节":
                # 2024-2030 年春节日期
                spring_festival_dates = {
                    2024: (2, 10), 2025: (1, 29), 2026: (2, 17),
                    2027: (2, 6), 2028: (1, 26), 2029: (2, 13),
                    2030: (2, 3),
                }
                if year in spring_festival_dates:
                    m, d = spring_festival_dates[year]
                    result[name] = {
                        "date": date(year, m, d),
                        "focus": info["focus"],
                    }
            else:
                # 其他节日简化处理，用月份 *30 作为近似偏移
                approx_month = info["month"]
                approx_day = info["day"]
                # 农历月份转公历的近似
                if approx_month <= 2:
                    pub_month = approx_month + 1
                elif approx_month <= 5:
                    pub_month = approx_month + 1
                elif approx_month <= 8:
                    pub_month = approx_month + 1
                elif approx_month <= 11:
                    pub_month = approx_month + 1
                else:
                    pub_month = 1
                    # 跨年

                try:
                    result[name] = {
                        "date": date(year, min(pub_month, 12), min(approx_day + 15, 28)),
                        "focus": info["focus"],
                    }
                except ValueError:
                    pass

        return result

    @staticmethod
    def get_tcm_periods(year: int = None) -> dict[str, dict]:
        """
        获取某年所有中医养生重要节点。
        返回字典包含各节点的日期范围和养生重点。
        """
        if year is None:
            year = datetime.now().year

        return {
            "三九": {
                "dates": SolarTermCalendar.get_sanjiu_dates(year),
                "description": "一年中最寒冷时期，温补阳气最佳时机",
                "wellness_focus": "温阳散寒、补肾暖宫",
            },
            "三伏": {
                "dates": SolarTermCalendar.get_sanfu_dates(year),
                "description": "一年中最炎热潮湿时期，冬病夏治最佳时机",
                "wellness_focus": "温阳驱寒、祛湿排毒",
            },
            "长夏": {
                "dates": SolarTermCalendar.get_changxia_period(year),
                "description": "夏秋交替之际，湿气最重",
                "wellness_focus": "健脾祛湿、养胃消食",
            },
            "梅雨": {
                "dates": SolarTermCalendar.get_plum_rain_period(year),
                "description": "江南地区梅雨季节，湿邪困脾",
                "wellness_focus": "祛湿化痰、疏肝理气",
            },
            "秋老虎": {
                "dates": SolarTermCalendar.get_autumn_tiger_period(year),
                "description": "处暑后气温回升，燥气渐重",
                "wellness_focus": "润肺生津、养阴清热",
            },
            "五运六气": {
                "periods": SolarTermCalendar.get_wuyun_sixqi_period(year),
                "description": "中医时间医学，六气主时",
            },
            "特殊节气": {
                "dates": SolarTermCalendar.get_special_solar_terms(year),
                "description": "关键养生节点",
            },
            "传统节日": {
                "dates": SolarTermCalendar.get_lunar_festivals_approximate(year),
                "description": "传统节日养生",
            },
        }

    @staticmethod
    def get_next_term(from_date: date = None) -> tuple[str, int]:
        """
        返回 (下一个节气名称，距今天数)。
        如果找不到（年份超出预置范围），返回 ("", -1)。
        """
        today = from_date or date.today()
        # 搜索今年和明年
        for year in [today.year, today.year + 1]:
            terms = SolarTermCalendar._get_terms_for_year(year)
            for name in TERM_ORDER:
                d = terms.get(name)
                if d and d >= today:
                    return name, (d - today).days
        return "", -1

    @staticmethod
    def get_next_tcm_period(from_date: date = None, days_ahead: int = 30) -> tuple[str, date, int]:
        """
        返回接下来 N 天内的中医养生节点。
        返回 (节点名称，开始日期，距今天数)。
        优先级：三九/三伏 > 二十四节气 > 长夏/秋老虎等
        """
        today = from_date or date.today()
        target_end = today + timedelta(days=days_ahead)

        candidates = []

        # 检查三九
        sanjiu = SolarTermCalendar.get_sanjiu_dates(today.year)
        for name, dates in sanjiu.items():
            if dates and dates[0] <= target_end and dates[-1] >= today:
                if dates[0] >= today:
                    candidates.append((name, dates[0], (dates[0] - today).days))
                else:
                    # 已经在进行中
                    candidates.append((name, dates[0], 0))

        # 检查三伏
        sanfu = SolarTermCalendar.get_sanfu_dates(today.year)
        for name, dates in sanfu.items():
            if dates and dates[0] <= target_end and dates[-1] >= today:
                if dates[0] >= today:
                    candidates.append((name, dates[0], (dates[0] - today).days))
                else:
                    candidates.append((name, dates[0], 0))

        # 检查长夏
        changxia = SolarTermCalendar.get_changxia_period(today.year)
        if changxia and changxia[0] <= target_end and changxia[-1] >= today:
            if changxia[0] >= today:
                candidates.append(("长夏", changxia[0], (changxia[0] - today).days))
            else:
                candidates.append(("长夏", changxia[0], 0))

        # 检查秋老虎
        autumn_tiger = SolarTermCalendar.get_autumn_tiger_period(today.year)
        if autumn_tiger and autumn_tiger[0] <= target_end and autumn_tiger[-1] >= today:
            if autumn_tiger[0] >= today:
                candidates.append(("秋老虎", autumn_tiger[0], (autumn_tiger[0] - today).days))
            else:
                candidates.append(("秋老虎", autumn_tiger[0], 0))

        # 检查下一个节气
        next_term, days = SolarTermCalendar.get_next_term(today)
        if days >= 0 and days <= days_ahead:
            candidates.append((next_term, today + timedelta(days=days), days))

        # 检查特殊节气（未来 N 天内）
        special = SolarTermCalendar.get_special_solar_terms(today.year)
        for name, info in special.items():
            d = info["date"]
            days_until = (d - today).days
            if 0 <= days_until <= days_ahead:
                candidates.append((name, d, days_until))

        if not candidates:
            return "", None, -1

        # 返回最近的节点（优先返回正在进行的）
        in_progress = [(n, d, days) for n, d, days in candidates if days == 0]
        if in_progress:
            return in_progress[0]

        candidates.sort(key=lambda x: x[2])
        return candidates[0]

    @staticmethod
    def get_current_term(from_date: date = None) -> str:
        """返回当前所处的节气（最近过去的那个）。"""
        today = from_date or date.today()
        last_term = ""
        for year in [today.year - 1, today.year]:
            terms = SolarTermCalendar._get_terms_for_year(year)
            for name in TERM_ORDER:
                d = terms.get(name)
                if d and d <= today:
                    last_term = name
        return last_term

    @staticmethod
    def get_current_season(from_date: date = None) -> str:
        """返回当前季节（春/夏/秋/冬）。"""
        term = SolarTermCalendar.get_current_term(from_date)
        return TERM_SEASON.get(term, "春")

    @staticmethod
    def get_season_display(from_date: date = None) -> str:
        """返回季节 + 节气的显示文本，如'春季·春分'。"""
        term = SolarTermCalendar.get_current_term(from_date)
        season = TERM_SEASON.get(term, "春")
        return f"{season}季·{term}" if term else f"{season}季"

    @staticmethod
    def get_current_wuyun_sixqi(from_date: date = None) -> tuple[str, str, str]:
        """
        获取当前五运六气阶段。
        返回 (阶段名称，元素，养生重点)
        """
        today = from_date or date.today()
        current_term = SolarTermCalendar.get_current_term(today)

        for qi_name, qi_info in WUYUN_SIXQI.items():
            if current_term in qi_info["terms"]:
                return qi_name, qi_info["element"], qi_info["focus"]

        return "未知", "未知", "顺应时节"

    @staticmethod
    def get_current_tcm_context(from_date: date = None) -> dict:
        """
        获取当前中医养生上下文。
        返回当前所处的中医节点及养生重点。
        """
        today = from_date or date.today()
        result = {
            "season": SolarTermCalendar.get_current_season(today),
            "season_display": SolarTermCalendar.get_season_display(today),
            "current_term": SolarTermCalendar.get_current_term(today),
            "active_periods": [],
            "wellness_advice": "",
            "wuyun_sixqi": "",
            "wuyun_focus": "",
        }

        # 五运六气
        qi_name, element, focus = SolarTermCalendar.get_current_wuyun_sixqi(today)
        result["wuyun_sixqi"] = f"{qi_name} ({element})"
        result["wuyun_focus"] = focus

        # 检查是否在特殊时期
        year = today.year
        sanjiu = SolarTermCalendar.get_sanjiu_dates(year)
        sanfu = SolarTermCalendar.get_sanfu_dates(year)
        changxia = SolarTermCalendar.get_changxia_period(year)
        autumn_tiger = SolarTermCalendar.get_autumn_tiger_period(year)

        for name, dates in sanjiu.items():
            if dates and dates[0] <= today <= dates[-1]:
                result["active_periods"].append(name)
                result["wellness_advice"] = "当前为三九期间，建议温补阳气、驱寒保暖。"

        for name, dates in sanfu.items():
            if dates and dates[0] <= today <= dates[-1]:
                result["active_periods"].append(name)
                result["wellness_advice"] = "当前为三伏期间，建议冬病夏治、祛湿排毒。"

        if changxia and changxia[0] <= today <= changxia[-1]:
            result["active_periods"].append("长夏")
            result["wellness_advice"] = "当前为长夏，湿气较重，建议健脾祛湿。"

        if autumn_tiger and autumn_tiger[0] <= today <= autumn_tiger[-1]:
            result["active_periods"].append("秋老虎")
            result["wellness_advice"] = "当前为秋老虎，燥气渐重，建议润肺生津。"

        # 如果没有特殊节点，使用五运六气建议
        if not result["wellness_advice"]:
            result["wellness_advice"] = f"当前{result['wuyun_sixqi']}，建议{result['wuyun_focus']}。"

        return result
