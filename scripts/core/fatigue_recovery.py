#!/usr/bin/env python3
"""
疲劳恢复 & 旅途距离调整模块 v1.0
===============================
核心调整因子：
1. 休息天数：休息>7天体能优势，<4天体能劣势
2. 旅途距离：跨洲/长途飞行后表现下滑
3. 时差适应：有时差适应期
"""

import os
import json
import math
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional

# ============ 路径配置 ============
BASE_DIR = os.path.expanduser("~/hermes-world-cup/")
DATA_DIR = os.path.join(BASE_DIR, "data/")


# ============ 球队地理位置数据 ============
# 用于计算旅途距离和时差
TEAM_LOCATIONS = {
    # 北美洲
    "USA": {"continent": "NA", "lat": 38.9, "lon": -77.0, "timezone": -5},
    "Mexico": {"continent": "NA", "lat": 19.4, "lon": -99.1, "timezone": -6},
    "Canada": {"continent": "NA", "lat": 45.4, "lon": -75.7, "timezone": -5},

    # 南美洲
    "Argentina": {"continent": "SA", "lat": -34.6, "lon": -58.4, "timezone": -3},
    "Brazil": {"continent": "SA", "lat": -23.5, "lon": -46.6, "timezone": -3},
    "Colombia": {"continent": "SA", "lat": 4.6, "lon": -74.1, "timezone": -5},
    "Ecuador": {"continent": "SA", "lat": -0.2, "lon": -78.5, "timezone": -5},
    "Uruguay": {"continent": "SA", "lat": -34.9, "lon": -56.2, "timezone": -3},
    "Chile": {"continent": "SA", "lat": -33.4, "lon": -70.6, "timezone": -4},
    "Paraguay": {"continent": "SA", "lat": -25.3, "lon": -57.6, "timezone": -4},
    "Peru": {"continent": "SA", "lat": -12.0, "lon": -77.0, "timezone": -5},
    "Venezuela": {"continent": "SA", "lat": 10.5, "lon": -66.9, "timezone": -4},

    # 欧洲
    "Germany": {"continent": "EU", "lat": 52.5, "lon": 13.4, "timezone": 1},
    "France": {"continent": "EU", "lat": 48.9, "lon": 2.3, "timezone": 1},
    "England": {"continent": "EU", "lat": 51.5, "lon": -0.1, "timezone": 0},
    "Spain": {"continent": "EU", "lat": 40.4, "lon": -3.7, "timezone": 1},
    "Portugal": {"continent": "EU", "lat": 38.7, "lon": -9.1, "timezone": 0},
    "Italy": {"continent": "EU", "lat": 41.9, "lon": 12.5, "timezone": 1},
    "Netherlands": {"continent": "EU", "lat": 52.4, "lon": 4.9, "timezone": 1},
    "Belgium": {"continent": "EU", "lat": 50.9, "lon": 4.5, "timezone": 1},
    "Switzerland": {"continent": "EU", "lat": 46.9, "lon": 7.4, "timezone": 1},
    "Poland": {"continent": "EU", "lat": 52.2, "lon": 21.0, "timezone": 1},
    "Ukraine": {"continent": "EU", "lat": 50.4, "lon": 30.5, "timezone": 2},
    "Serbia": {"continent": "EU", "lat": 44.8, "lon": 20.5, "timezone": 1},
    "Croatia": {"continent": "EU", "lat": 45.8, "lon": 16.0, "timezone": 1},
    "Denmark": {"continent": "EU", "lat": 55.7, "lon": 12.6, "timezone": 1},
    "Sweden": {"continent": "EU", "lat": 59.3, "lon": 18.1, "timezone": 1},
    "Norway": {"continent": "EU", "lat": 59.9, "lon": 10.8, "timezone": 1},
    "Austria": {"continent": "EU", "lat": 48.2, "lon": 16.4, "timezone": 1},
    "Romania": {"continent": "EU", "lat": 44.4, "lon": 26.1, "timezone": 2},
    "Czech Republic": {"continent": "EU", "lat": 50.1, "lon": 14.4, "timezone": 1},
    "Hungary": {"continent": "EU", "lat": 47.5, "lon": 19.0, "timezone": 1},
    "Slovakia": {"continent": "EU", "lat": 48.1, "lon": 17.1, "timezone": 1},
    "Greece": {"continent": "EU", "lat": 37.9, "lon": 23.7, "timezone": 2},
    "Turkey": {"continent": "EU", "lat": 39.9, "lon": 32.9, "timezone": 3},
    "Albania": {"continent": "EU", "lat": 41.3, "lon": 19.8, "timezone": 1},
    "Slovenia": {"continent": "EU", "lat": 46.1, "lon": 14.6, "timezone": 1},
    "Wales": {"continent": "EU", "lat": 51.5, "lon": -3.2, "timezone": 0},
    "Scotland": {"continent": "EU", "lat": 56.5, "lon": -4.2, "timezone": 0},
    "Northern Ireland": {"continent": "EU", "lat": 54.6, "lon": -5.9, "timezone": 0},
    "Republic of Ireland": {"continent": "EU", "lat": 53.3, "lon": -6.3, "timezone": 0},
    "Iceland": {"continent": "EU", "lat": 64.1, "lon": -21.9, "timezone": 0},
    "Finland": {"continent": "EU", "lat": 60.2, "lon": 25.0, "timezone": 2},
    "Russia": {"continent": "EU", "lat": 55.8, "lon": 37.6, "timezone": 3},
    "Kosovo": {"continent": "EU", "lat": 42.6, "lon": 21.2, "timezone": 1},
    "Montenegro": {"continent": "EU", "lat": 42.4, "lon": 19.3, "timezone": 1},
    "Bosnia and Herzegovina": {"continent": "EU", "lat": 43.9, "lon": 18.4, "timezone": 1},
    "North Macedonia": {"continent": "EU", "lat": 42.0, "lon": 21.4, "timezone": 1},
    "Georgia": {"continent": "EU", "lat": 41.7, "lon": 44.8, "timezone": 4},
    "Armenia": {"continent": "EU", "lat": 40.2, "lon": 44.5, "timezone": 4},
    "Azerbaijan": {"continent": "EU", "lat": 40.4, "lon": 49.9, "timezone": 4},
    "Kazakhstan": {"continent": "EU", "lat": 51.2, "lon": 71.4, "timezone": 5},
    "Cyprus": {"continent": "EU", "lat": 35.2, "lon": 33.4, "timezone": 2},
    "Malta": {"continent": "EU", "lat": 35.9, "lon": 14.4, "timezone": 1},
    "Luxembourg": {"continent": "EU", "lat": 49.6, "lon": 6.1, "timezone": 1},
    "Liechtenstein": {"continent": "EU", "lat": 47.1, "lon": 9.5, "timezone": 1},
    "Andorra": {"continent": "EU", "lat": 42.5, "lon": 1.5, "timezone": 1},
    "San Marino": {"continent": "EU", "lat": 43.9, "lon": 12.4, "timezone": 1},
    "Monaco": {"continent": "EU", "lat": 43.7, "lon": 7.4, "timezone": 1},
    "Faroe Islands": {"continent": "EU", "lat": 62.0, "lon": -6.8, "timezone": 0},
    "Gibraltar": {"continent": "EU", "lat": 36.1, "lon": -5.3, "timezone": 1},

    # 亚洲
    "Japan": {"continent": "AS", "lat": 35.7, "lon": 139.7, "timezone": 9},
    "South Korea": {"continent": "AS", "lat": 37.6, "lon": 127.0, "timezone": 9},
    "Iran": {"continent": "AS", "lat": 35.7, "lon": 51.4, "timezone": 3.5},
    "Saudi Arabia": {"continent": "AS", "lat": 24.7, "lon": 46.7, "timezone": 3},
    "Australia": {"continent": "AS", "lat": -33.9, "lon": 151.2, "timezone": 10},
    "Qatar": {"continent": "AS", "lat": 25.3, "lon": 51.5, "timezone": 3},
    "UAE": {"continent": "AS", "lat": 25.2, "lon": 55.3, "timezone": 4},
    "China": {"continent": "AS", "lat": 39.9, "lon": 116.4, "timezone": 8},
    "India": {"continent": "AS", "lat": 28.6, "lon": 77.2, "timezone": 5.5},
    "Iraq": {"continent": "AS", "lat": 33.3, "lon": 44.4, "timezone": 3},
    "Jordan": {"continent": "AS", "lat": 31.9, "lon": 35.9, "timezone": 3},
    "Uzbekistan": {"continent": "AS", "lat": 41.3, "lon": 69.2, "timezone": 5},
    "Oman": {"continent": "AS", "lat": 23.6, "lon": 58.5, "timezone": 4},
    "Kuwait": {"continent": "AS", "lat": 29.4, "lon": 48.0, "timezone": 3},
    "Thailand": {"continent": "AS", "lat": 13.8, "lon": 100.5, "timezone": 7},
    "North Korea": {"continent": "AS", "lat": 39.0, "lon": 125.8, "timezone": 9},
    "Indonesia": {"continent": "AS", "lat": -6.2, "lon": 106.8, "timezone": 7},
    "Malaysia": {"continent": "AS", "lat": 3.1, "lon": 101.7, "timezone": 8},
    "Philippines": {"continent": "AS", "lat": 14.6, "lon": 121.0, "timezone": 8},
    "Singapore": {"continent": "AS", "lat": 1.4, "lon": 103.8, "timezone": 8},
    "Vietnam": {"continent": "AS", "lat": 21.0, "lon": 105.8, "timezone": 7},
    "Bangladesh": {"continent": "AS", "lat": 23.8, "lon": 90.4, "timezone": 6},
    "Afghanistan": {"continent": "AS", "lat": 34.5, "lon": 69.2, "timezone": 4.5},
    "Kyrgyzstan": {"continent": "AS", "lat": 42.9, "lon": 74.6, "timezone": 6},
    "Tajikistan": {"continent": "AS", "lat": 38.6, "lon": 68.8, "timezone": 5},
    "Turkmenistan": {"continent": "AS", "lat": 37.9, "lon": 58.4, "timezone": 5},
    "Palestine": {"continent": "AS", "lat": 31.9, "lon": 35.2, "timezone": 2},
    "Lebanon": {"continent": "AS", "lat": 33.9, "lon": 35.5, "timezone": 2},
    "Syria": {"continent": "AS", "lat": 33.5, "lon": 36.3, "timezone": 3},
    "Yemen": {"continent": "AS", "lat": 15.4, "lon": 44.2, "timezone": 3},
    "Bahrain": {"continent": "AS", "lat": 26.1, "lon": 50.5, "timezone": 3},
    "Mongolia": {"continent": "AS", "lat": 47.9, "lon": 106.9, "timezone": 8},
    "Nepal": {"continent": "AS", "lat": 27.7, "lon": 85.3, "timezone": 5.75},
    "Sri Lanka": {"continent": "AS", "lat": 6.9, "lon": 79.9, "timezone": 5.5},
    "Myanmar": {"continent": "AS", "lat": 16.9, "lon": 96.1, "timezone": 6.5},
    "Cambodia": {"continent": "AS", "lat": 11.6, "lon": 104.9, "timezone": 7},
    "Laos": {"continent": "AS", "lat": 17.9, "lon": 102.6, "timezone": 7},
    "Brunei": {"continent": "AS", "lat": 4.9, "lon": 114.9, "timezone": 8},
    "Maldives": {"continent": "AS", "lat": 4.2, "lon": 73.5, "timezone": 5},
    "Timor-Leste": {"continent": "AS", "lat": -8.6, "lon": 125.6, "timezone": 9},
    "Pakistan": {"continent": "AS", "lat": 33.7, "lon": 73.0, "timezone": 5},

    # 非洲
    "Egypt": {"continent": "AF", "lat": 30.1, "lon": 31.2, "timezone": 2},
    "South Africa": {"continent": "AF", "lat": -26.2, "lon": 28.0, "timezone": 2},
    "Morocco": {"continent": "AF", "lat": 33.9, "lon": -6.9, "timezone": 1},
    "Algeria": {"continent": "AF", "lat": 36.8, "lon": 3.0, "timezone": 1},
    "Nigeria": {"continent": "AF", "lat": 6.5, "lon": 3.4, "timezone": 1},
    "Cameroon": {"continent": "AF", "lat": 3.9, "lon": 11.5, "timezone": 1},
    "Senegal": {"continent": "AF", "lat": 14.7, "lon": -17.4, "timezone": 0},
    "Ghana": {"continent": "AF", "lat": 5.6, "lon": -0.2, "timezone": 0},
    "Ivory Coast": {"continent": "AF", "lat": 5.3, "lon": -4.0, "timezone": 0},
    "Tunisia": {"continent": "AF", "lat": 36.8, "lon": 10.2, "timezone": 1},
    "DR Congo": {"continent": "AF", "lat": -4.3, "lon": 15.3, "timezone": 1},
    "Zambia": {"continent": "AF", "lat": -15.4, "lon": 28.3, "timezone": 2},
    "Mali": {"continent": "AF", "lat": 12.6, "lon": -8.0, "timezone": 0},
    "Burkina Faso": {"continent": "AF", "lat": 12.4, "lon": -1.5, "timezone": 0},
    "Equatorial Guinea": {"continent": "AF", "lat": 3.8, "lon": 8.8, "timezone": 1},
    "Gabon": {"continent": "AF", "lat": 0.4, "lon": 9.5, "timezone": 1},
    "Mozambique": {"continent": "AF", "lat": -25.9, "lon": 32.6, "timezone": 2},
    "Madagascar": {"continent": "AF", "lat": -18.9, "lon": 47.5, "timezone": 3},
    "Kenya": {"continent": "AF", "lat": -1.3, "lon": 36.8, "timezone": 3},
    "Ethiopia": {"continent": "AF", "lat": 9.1, "lon": 38.7, "timezone": 3},
    "Uganda": {"continent": "AF", "lat": 0.3, "lon": 32.6, "timezone": 3},
    "Tanzania": {"continent": "AF", "lat": -6.8, "lon": 39.2, "timezone": 3},
    "Algeria": {"continent": "AF", "lat": 36.8, "lon": 3.0, "timezone": 1},
    "Sudan": {"continent": "AF", "lat": 15.5, "lon": 32.5, "timezone": 3},
    "Libya": {"continent": "AF", "lat": 32.9, "lon": 13.2, "timezone": 2},
    "Angola": {"continent": "AF", "lat": -8.8, "lon": 13.2, "timezone": 1},
    "Zimbabwe": {"continent": "AF", "lat": -17.8, "lon": 31.0, "timezone": 2},
    "Namibia": {"continent": "AF", "lat": -22.6, "lon": 17.1, "timezone": 2},
    "Botswana": {"continent": "AF", "lat": -24.6, "lon": 25.9, "timezone": 2},
    "Rwanda": {"continent": "AF", "lat": -1.9, "lon": 29.9, "timezone": 2},
    "Benin": {"continent": "AF", "lat": 6.5, "lon": 2.6, "timezone": 1},
    "Togo": {"continent": "AF", "lat": 6.1, "lon": 1.2, "timezone": 0},
    "Niger": {"continent": "AF", "lat": 13.5, "lon": 2.1, "timezone": 1},
    "Chad": {"continent": "AF", "lat": 12.1, "lon": 15.0, "timezone": 1},
    "Central African Republic": {"continent": "AF", "lat": 4.4, "lon": 18.6, "timezone": 1},
    "Republic of the Congo": {"continent": "AF", "lat": -4.0, "lon": 15.3, "timezone": 1},
    "Mauritania": {"continent": "AF", "lat": 18.1, "lon": -15.9, "timezone": 0},
    "Liberia": {"continent": "AF", "lat": 6.3, "lon": -10.8, "timezone": 0},
    "Sierra Leone": {"continent": "AF", "lat": 8.5, "lon": -13.2, "timezone": 0},
    "Guinea": {"continent": "AF", "lat": 9.6, "lon": -13.6, "timezone": 0},
    "Guinea-Bissau": {"continent": "AF", "lat": 11.9, "lon": -15.6, "timezone": 0},
    " Gambia": {"continent": "AF", "lat": 13.4, "lon": -16.6, "timezone": 0},
    "Cape Verde": {"continent": "AF", "lat": 14.9, "lon": -23.5, "timezone": -1},
    "Mauritius": {"continent": "AF", "lat": -20.2, "lon": 57.5, "timezone": 4},
    "Seychelles": {"continent": "AF", "lat": -4.7, "lon": 55.5, "timezone": 4},
    "Comoros": {"continent": "AF", "lat": -11.6, "lon": 43.3, "timezone": 3},
    "Eswatini": {"continent": "AF", "lat": -26.3, "lon": 31.1, "timezone": 2},
    "Lesotho": {"continent": "AF", "lat": -29.6, "lon": 28.2, "timezone": 2},
    "Djibouti": {"continent": "AF", "lat": 11.8, "lon": 42.5, "timezone": 3},
    "Eritrea": {"continent": "AF", "lat": 15.3, "lon": 38.9, "timezone": 3},
    "Somalia": {"continent": "AF", "lat": 2.0, "lon": 45.3, "timezone": 3},
    "Burundi": {"continent": "AF", "lat": -3.4, "lon": 29.9, "timezone": 2},
    "Malawi": {"continent": "AF", "lat": -14.0, "lon": 33.8, "timezone": 2},
    "South Sudan": {"continent": "AF", "lat": 4.9, "lon": 31.3, "timezone": 3},
    "Tanzania": {"continent": "AF", "lat": -6.8, "lon": 39.2, "timezone": 3},
    "Egypt": {"continent": "AF", "lat": 30.1, "lon": 31.2, "timezone": 2},

    # 大洋洲
    "New Zealand": {"continent": "OC", "lat": -41.3, "lon": 174.8, "timezone": 12},
    "Fiji": {"continent": "OC", "lat": -18.1, "lon": 178.4, "timezone": 12},
    "Papua New Guinea": {"continent": "OC", "lat": -9.5, "lon": 147.2, "timezone": 10},
    "Solomon Islands": {"continent": "OC", "lat": -9.6, "lon": 160.2, "timezone": 11},
    "Tahiti": {"continent": "OC", "lat": -17.7, "lon": -149.4, "timezone": -10},
}


class FatigueRecoveryAnalyzer:
    """
    疲劳恢复 & 旅途距离分析器

    核心功能：
    1. 计算休息天数对体能的影响
    2. 计算旅途距离对表现的影响
    3. 计算时差适应期的影响
    4. 综合调整胜平负概率
    """

    def __init__(self):
        self.data_dir = DATA_DIR

        # 休息天数影响表（相对于最佳状态）
        # 休息太久也不好，会失去比赛节奏
        self.rest_bonus = {
            1: -0.08,   # 休息1天：极度疲劳
            2: -0.05,   # 休息2天：较疲劳
            3: -0.02,   # 休息3天：略有疲劳
            4: 0.0,     # 休息4天：正常
            5: 0.02,    # 休息5天：良好
            6: 0.03,    # 休息6天：最佳
            7: 0.02,    # 休息7天：略好
            8: 0.0,     # 休息8天：正常
            9: -0.02,   # 休息9天：略差
            10: -0.04,  # 休息10天：较差
            11: -0.06,  # 休息11天：差
            12: -0.08,  # 休息12天+：失去节奏
        }

        # 旅途距离影响（跨洲长途飞行后）
        # 基于flight research data
        self.flight_penalty = {
            # (出发洲, 到达洲): 表现下降百分比
            ("NA", "EU"): -0.03,   # 北美到欧洲：轻微影响
            ("EU", "NA"): -0.03,
            ("SA", "EU"): -0.05,   # 南美到欧洲：中等影响
            ("EU", "SA"): -0.05,
            ("AS", "EU"): -0.04,   # 亚洲到欧洲：中等影响
            ("EU", "AS"): -0.04,
            ("AF", "EU"): -0.02,   # 非洲到欧洲：轻微影响
            ("EU", "AF"): -0.02,
            ("OC", "EU"): -0.06,   # 大洋洲到欧洲：较大影响
            ("EU", "OC"): -0.06,
            ("SA", "NA"): -0.04,   # 南美到北美
            ("NA", "SA"): -0.04,
            ("AS", "NA"): -0.05,   # 亚洲到北美
            ("NA", "AS"): -0.05,
            ("AF", "AS"): -0.03,   # 非洲到亚洲
            ("AS", "AF"): -0.03,
            ("NA", "OC"): -0.05,
            ("OC", "NA"): -0.05,
            ("SA", "AS"): -0.04,
            ("AS", "SA"): -0.04,
            ("EU", "EU"): 0.0,     # 欧洲内部：无影响
            ("NA", "NA"): 0.0,     # 北美内部：无影响
            ("AF", "AF"): 0.0,     # 非洲内部：无影响
        }

        # 时差适应系数（每小时时差需要约1天适应）
        self.timezone_penalty = 0.015  # 每小时时差下降1.5%

        # 飞行时间影响（每小时飞行增加疲劳）
        self.flight_hour_penalty = 0.005  # 每小时0.5%下降

        # 加载旅途数据
        self._load_travel_data()

    def _load_travel_data(self):
        """加载旅途数据"""
        travel_file = os.path.join(self.data_dir, "travel_data.json")
        if os.path.exists(travel_file):
            try:
                with open(travel_file, 'r') as f:
                    self.travel_data = json.load(f)
            except:
                self.travel_data = {}
        else:
            self.travel_data = {}

    def save_travel_data(self):
        """保存旅途数据"""
        travel_file = os.path.join(self.data_dir, "travel_data.json")
        os.makedirs(os.path.dirname(travel_file), exist_ok=True)
        with open(travel_file, 'w') as f:
            json.dump(self.travel_data, f, ensure_ascii=False, indent=2)

    def get_team_location(self, team: str) -> Optional[Dict]:
        """获取球队地理位置"""
        return TEAM_LOCATIONS.get(team)

    def calculate_distance_km(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """使用Haversine公式计算两点间距离（公里）"""
        R = 6371  # 地球半径（公里）

        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)

        a = math.sin(delta_lat / 2) ** 2 + \
            math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c

    def estimate_flight_hours(self, distance_km: float) -> float:
        """估算飞行时间（小时）"""
        # 平均飞行速度约800km/h，加上起飞降落时间
        if distance_km < 500:
            return distance_km / 600 + 0.5  # 短途
        elif distance_km < 3000:
            return distance_km / 800 + 1.0  # 中途
        else:
            return distance_km / 850 + 1.5  # 长途（需要巡航高度）

    def get_rest_factor(self, days_since_last_match: int) -> float:
        """
        获取休息天数因子

        Args:
            days_since_last_match: 距离上一场比赛的天数

        Returns:
            调整因子（正数表示有利，负数表示不利）
        """
        if days_since_last_match <= 0:
            # 今天比赛或数据异常，按4天处理
            return self.rest_bonus.get(4, 0)

        # 查找最接近的休息天数
        closest = min(self.rest_bonus.keys(), key=lambda x: abs(x - days_since_last_match))
        return self.rest_bonus.get(closest, 0)

    def get_travel_factor(self, from_team: str, to_venue: str) -> Tuple[float, Dict]:
        """
        获取旅途影响因子

        Args:
            from_team: 出发球队
            to_venue: 比赛地点

        Returns:
            (调整因子, 详情字典)
        """
        details = {}

        from_loc = self.get_team_location(from_team)
        to_loc = self.get_team_location(to_venue)

        if not from_loc or not to_loc:
            # 找不到，使用默认值
            return 0, {"status": "unknown", "penalty": 0}

        from_continent = from_loc["continent"]
        to_continent = to_loc["continent"]

        # 计算飞行距离
        distance = self.calculate_distance_km(
            from_loc["lat"], from_loc["lon"],
            to_loc["lat"], to_loc["lon"]
        )
        details["distance_km"] = round(distance, 0)
        details["from_continent"] = from_continent
        details["to_continent"] = to_continent

        # 跨洲影响
        continent_key = (from_continent, to_continent)
        continent_penalty = self.flight_penalty.get(continent_key, 0)
        details["continent_penalty"] = continent_penalty

        # 时差影响
        time_diff = abs(from_loc["timezone"] - to_loc["timezone"])
        details["timezone_diff_hours"] = time_diff
        timezone_penalty = time_diff * self.timezone_penalty
        details["timezone_penalty"] = timezone_penalty

        # 飞行时间疲劳
        flight_hours = self.estimate_flight_hours(distance)
        details["estimated_flight_hours"] = round(flight_hours, 1)
        flight_penalty = flight_hours * self.flight_hour_penalty
        details["flight_fatigue_penalty"] = flight_penalty

        # 总惩罚
        total_penalty = continent_penalty + timezone_penalty + flight_penalty
        details["total_penalty"] = total_penalty

        # 长途飞行额外惩罚（>10小时飞行）
        if flight_hours > 10:
            long_flight_bonus = -0.02  # 额外-2%
            total_penalty += long_flight_bonus
            details["long_flight_bonus"] = long_flight_bonus

        # 连续客场惩罚
        # 如果球队连续踢客场，额外惩罚
        # （这个需要在比赛中追踪，暂时标记）
        details["status"] = "calculated"

        return total_penalty, details

    def analyze_match_fatigue(self,
                              home_team: str,
                              away_team: str,
                              home_last_match_date: datetime,
                              away_last_match_date: datetime,
                              venue_continent: str = "AS") -> Dict:
        """
        分析比赛双方的疲劳和旅途因素

        Args:
            home_team: 主队
            away_team: 客队
            home_last_match_date: 主队上一场比赛日期
            away_last_match_date: 客队上一场比赛日期
            venue_continent: 比赛地点所在洲

        Returns:
            完整的疲劳分析报告
        """
        today = datetime.now()
        match_date = today  # 假设是今天比赛

        # 计算休息天数
        home_rest_days = (match_date - home_last_match_date).days
        away_rest_days = (match_date - away_last_match_date).days

        home_rest_factor = self.get_rest_factor(home_rest_days)
        away_rest_factor = self.get_rest_factor(away_rest_days)

        # 计算旅途因素
        # 假设比赛地点是主队所在地（世界杯通常是这样）
        away_travel_penalty, away_travel_details = self.get_travel_factor(
            away_team, home_team  # 客队飞往主队所在地
        )

        # 主队通常在自己国家比赛，旅途影响很小
        home_travel_penalty = 0

        # 综合调整
        # 主队休息优势 - 客队旅途劣势
        home_advantage = home_rest_factor - away_travel_penalty
        away_advantage = away_rest_factor + away_travel_penalty

        # 注意：away_travel_penalty是负数（惩罚），所以 -away_travel_penalty 变成正数（对主队有利）

        # 转换为概率调整
        # 假设基础主胜概率为P，则调整后主胜概率约为 P + home_advantage * 0.5
        home_win_adjustment = home_advantage * 0.5
        away_win_adjustment = -home_advantage * 0.5  # 对称调整

        return {
            "home_rest_days": home_rest_days,
            "away_rest_days": away_rest_days,
            "home_rest_factor": home_rest_factor,
            "away_rest_factor": away_rest_factor,
            "away_travel_details": away_travel_details,
            "home_travel_penalty": home_travel_penalty,
            "away_travel_penalty": away_travel_penalty,
            "home_advantage": home_advantage,
            "away_advantage": away_advantage,
            "home_win_adjustment": home_win_adjustment,
            "away_win_adjustment": away_win_adjustment,
            "recommendation": self._get_recommendation(home_advantage)
        }

    def _get_recommendation(self, home_advantage: float) -> str:
        """根据优势给出推荐"""
        if home_advantage > 0.05:
            return "主队明显优势"
        elif home_advantage > 0.02:
            return "主队略有优势"
        elif home_advantage > -0.02:
            return "双方相当"
        elif home_advantage > -0.05:
            return "客队略有优势"
        else:
            return "客队明显优势"

    def apply_fatigue_adjustment(self,
                                 home_win_prob: float,
                                 draw_prob: float,
                                 away_win_prob: float,
                                 home_team: str,
                                 away_team: str,
                                 home_rest_days: int,
                                 away_rest_days: int,
                                 venue_continent: str = "AS") -> Dict:
        """
        将疲劳因素应用到概率上

        Args:
            home_win_prob: 原始主队胜率
            draw_prob: 原始平局概率
            away_win_prob: 原始客队胜率
            home_team: 主队
            away_team: 客队
            home_rest_days: 主队休息天数
            away_rest_days: 客队休息天数
            venue_continent: 比赛地点洲

        Returns:
            调整后的概率和详情
        """
        # 分析疲劳
        analysis = self.analyze_match_fatigue(
            home_team, away_team,
            datetime.now() - timedelta(days=home_rest_days),
            datetime.now() - timedelta(days=away_rest_days),
            venue_continent
        )

        # 应用调整
        adj_home = home_win_prob + analysis["home_win_adjustment"]
        adj_away = away_win_prob + analysis["away_win_adjustment"]

        # 平局保持不变（或者微调）
        adj_draw = draw_prob

        # 归一化
        total = adj_home + adj_draw + adj_away
        if total > 0:
            adj_home /= total
            adj_draw /= total
            adj_away /= total
        else:
            # 异常情况，返回原始值
            adj_home = home_win_prob
            adj_draw = draw_prob
            adj_away = away_win_prob

        return {
            "adjusted_home": adj_home,
            "adjusted_draw": adj_draw,
            "adjusted_away": adj_away,
            "adjustment_details": analysis,
            "home_rest_days": home_rest_days,
            "away_rest_days": away_rest_days,
        }


# ============ 测试代码 ============
if __name__ == "__main__":
    analyzer = FatigueRecoveryAnalyzer()

    # 测试：德国 vs 阿根廷（假设在欧洲比赛，德国主场）
    print("=" * 60)
    print("疲劳分析测试：德国 vs 阿根廷")
    print("=" * 60)

    result = analyzer.analyze_match_fatigue(
        home_team="Germany",
        away_team="Argentina",
        home_last_match_date=datetime.now() - timedelta(days=5),
        away_last_match_date=datetime.now() - timedelta(days=4),
        venue_continent="EU"
    )

    print(f"主队(德国)休息天数: {result['home_rest_days']}天")
    print(f"主队休息因子: {result['home_rest_factor']:+.3f}")
    print()
    print(f"客队(阿根廷)休息天数: {result['away_rest_days']}天")
    print(f"客队休息因子: {result['away_rest_factor']:+.3f}")
    print()
    print("客队旅途详情:")
    for k, v in result['away_travel_details'].items():
        print(f"  {k}: {v}")
    print()
    print(f"主队优势: {result['home_advantage']:+.3f}")
    print(f"主队胜率调整: {result['home_win_adjustment']:+.3f}")
    print(f"推荐: {result['recommendation']}")

    print()
    print("=" * 60)
    print("应用概率调整测试")
    print("=" * 60)

    # 原始概率
    home = 0.50
    draw = 0.25
    away = 0.25

    adjusted = analyzer.apply_fatigue_adjustment(
        home, draw, away,
        "Germany", "Argentina",
        home_rest_days=5,
        away_rest_days=4,
        venue_continent="EU"
    )

    print(f"原始概率: 德国 {home:.1%} | 平局 {draw:.1%} | 阿根廷 {away:.1%}")
    print(f"调整后:   德国 {adjusted['adjusted_home']:.1%} | 平局 {adjusted['adjusted_draw']:.1%} | 阿根廷 {adjusted['adjusted_away']:.1%}")
