#!/usr/bin/env python3
"""
天气数据整合模块 v1.0
====================
整合天气因素到预测系统

核心功能：
1. 天气类型对比赛的影响（雨天、晴天、阴天）
2. 温度对球员表现的影响
3. 湿度和海拔的影响
4. 极端天气识别
"""

import os
import json
import math
from datetime import datetime
from typing import Dict, List, Tuple, Optional

# ============ 路径配置 ============
BASE_DIR = os.path.expanduser("~/hermes-world-cup/")
DATA_DIR = os.path.join(BASE_DIR, "data/")


# ============ 世界杯场地天气数据 ============
# 2026世界杯美国/加拿大/墨西哥
VENUE_WEATHER = {
    # 美国
    "New York": {"typical_temp": 15, "typical_humidity": 60, "altitude": 10},
    "Los Angeles": {"typical_temp": 22, "typical_humidity": 50, "altitude": 71},
    "Miami": {"typical_temp": 28, "typical_humidity": 75, "altitude": 2},
    "Dallas": {"typical_temp": 25, "typical_humidity": 55, "altitude": 133},
    "Houston": {"typical_temp": 27, "typical_humidity": 70, "altitude": 12},
    "Chicago": {"typical_temp": 18, "typical_humidity": 60, "altitude": 176},
    "Seattle": {"typical_temp": 14, "typical_humidity": 70, "altitude": 56},
    "San Francisco": {"typical_temp": 18, "typical_humidity": 65, "altitude": 16},
    "Denver": {"typical_temp": 15, "typical_humidity": 40, "altitude": 1609},
    "Phoenix": {"typical_temp": 32, "typical_humidity": 25, "altitude": 331},
    "Atlanta": {"typical_temp": 22, "typical_humidity": 60, "altitude": 320},
    "Boston": {"typical_temp": 14, "typical_humidity": 60, "altitude": 6},

    # 加拿大
    "Toronto": {"typical_temp": 12, "typical_humidity": 55, "altitude": 76},
    "Vancouver": {"typical_temp": 12, "typical_humidity": 65, "altitude": 0},

    # 墨西哥
    "Mexico City": {"typical_temp": 18, "typical_humidity": 50, "altitude": 2240},
    "Guadalajara": {"typical_temp": 22, "typical_humidity": 45, "altitude": 1560},
    "Monterrey": {"typical_temp": 25, "typical_humidity": 55, "altitude": 540},

    # 卡塔尔（参考）
    "Doha": {"typical_temp": 32, "typical_humidity": 60, "altitude": 10},

    # 欧洲主要城市
    "Munich": {"typical_temp": 15, "typical_humidity": 65, "altitude": 519},
    "Berlin": {"typical_temp": 14, "typical_humidity": 60, "altitude": 35},
    "Paris": {"typical_temp": 16, "typical_humidity": 65, "altitude": 35},
    "London": {"typical_temp": 13, "typical_humidity": 70, "altitude": 11},
    "Rome": {"typical_temp": 20, "typical_humidity": 55, "altitude": 21},
    "Madrid": {"typical_temp": 20, "typical_humidity": 45, "altitude": 650},
}


class WeatherAnalyzer:
    """
    天气分析器

    天气对比赛的影响：
    - 雨天：进球减少15-20%，高空球战术受限
    - 高温：体能消耗增加，下半场进球可能更多
    - 高海拔：球员疲劳更快，长传增加
    - 低温：肌肉伤病风险增加
    """

    def __init__(self):
        self.data_dir = DATA_DIR
        self.weather_cache = self._load_weather_cache()

        # 天气影响系数
        self.weather_effects = {
            "rain_heavy": {
                "goal_factor": 0.75,  # 进球减少25%
                "home_advantage": -0.03,  # 主场优势减少
                "description": "大雨"
            },
            "rain_light": {
                "goal_factor": 0.88,
                "home_advantage": -0.01,
                "description": "小雨"
            },
            "overcast": {
                "goal_factor": 0.95,
                "home_advantage": 0,
                "description": "阴天"
            },
            "clear": {
                "goal_factor": 1.0,
                "home_advantage": 0,
                "description": "晴天"
            },
            "hot": {
                "goal_factor": 0.92,
                "home_advantage": 0.02,  # 主场更适应
                "description": "高温"
            },
            "cold": {
                "goal_factor": 0.97,
                "home_advantage": 0.01,
                "description": "低温"
            },
            "humid": {
                "goal_factor": 0.93,
                "home_advantage": 0,
                "description": "高湿度"
            },
            "high_altitude": {
                "goal_factor": 0.90,
                "home_advantage": 0.05,  # 主场适应更好
                "description": "高海拔"
            },
        }

    def _load_weather_cache(self) -> Dict:
        """加载天气缓存"""
        cache_file = os.path.join(self.data_dir, "weather_cache.json")
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def save_weather_cache(self):
        """保存天气缓存"""
        cache_file = os.path.join(self.data_dir, "weather_cache.json")
        os.makedirs(os.path.dirname(cache_file), exist_ok=True)
        with open(cache_file, 'w') as f:
            json.dump(self.weather_cache, f, ensure_ascii=False, indent=2)

    def get_venue_weather(self, city: str) -> Dict:
        """获取场地典型天气"""
        return VENUE_WEATHER.get(city, {
            "typical_temp": 20,
            "typical_humidity": 60,
            "altitude": 0
        })

    def analyze_weather_impact(self,
                               temperature: float,
                               humidity: float,
                               precipitation: float,
                               wind_speed: float,
                               altitude: float = 0) -> Dict:
        """
        分析天气影响

        Args:
            temperature: 温度（摄氏度）
            humidity: 湿度（%）
            precipitation: 降水量（mm）
            wind_speed: 风速（km/h）
            altitude: 海拔（米）

        Returns:
            天气影响分析
        """
        conditions = []
        effects = []

        # 温度影响
        if temperature > 30:
            conditions.append("hot")
            effects.append(self.weather_effects["hot"])
        elif temperature < 5:
            conditions.append("cold")
            effects.append(self.weather_effects["cold"])

        # 降水影响
        if precipitation > 10:
            conditions.append("rain_heavy")
            effects.append(self.weather_effects["rain_heavy"])
        elif precipitation > 2:
            conditions.append("rain_light")
            effects.append(self.weather_effects["rain_light"])
        elif precipitation == 0 and humidity > 80:
            conditions.append("overcast")
            effects.append(self.weather_effects["overcast"])
        elif precipitation == 0:
            conditions.append("clear")
            effects.append(self.weather_effects["clear"])

        # 湿度影响
        if humidity > 75:
            conditions.append("humid")
            effects.append(self.weather_effects["humid"])

        # 海拔影响
        if altitude > 1500:
            conditions.append("high_altitude")
            effects.append(self.weather_effects["high_altitude"])
        elif altitude > 1000:
            effects.append({
                "goal_factor": 0.97,
                "home_advantage": 0.02,
                "description": "中等海拔"
            })

        # 综合计算
        goal_factor = 1.0
        home_advantage_mod = 0.0

        for effect in effects:
            goal_factor *= effect["goal_factor"]
            home_advantage_mod += effect["home_advantage"]

        # 风速影响（风速>30km/h影响大）
        if wind_speed > 30:
            goal_factor *= 0.95
            effects.append({
                "goal_factor": 0.95,
                "home_advantage": 0,
                "description": "大风"
            })

        # 极端天气
        extreme = len([c for c in conditions if "rain" in c or "hot" in c]) >= 2

        return {
            "conditions": conditions,
            "goal_factor": max(0.7, min(1.05, goal_factor)),  # 限制范围
            "home_advantage_mod": home_advantage_mod,
            "is_extreme": extreme,
            "effects": effects,
            "description": self._get_weather_description(conditions),
            "recommendation": self._get_weather_recommendation(goal_factor, home_advantage_mod)
        }

    def _get_weather_description(self, conditions: List[str]) -> str:
        """获取天气描述"""
        if not conditions:
            return "良好天气"

        descriptions = []
        for cond in conditions:
            if cond in self.weather_effects:
                descriptions.append(self.weather_effects[cond]["description"])

        return "、".join(descriptions) if descriptions else "良好天气"

    def _get_weather_recommendation(self, goal_factor: float, home_advantage_mod: float) -> str:
        """获取天气建议"""
        recommendations = []

        # 进球因素
        if goal_factor < 0.85:
            recommendations.append("小球倾向明显")
        elif goal_factor < 0.95:
            recommendations.append("进球可能略少")

        # 主场优势
        if home_advantage_mod > 0.03:
            recommendations.append("主场优势增强")
        elif home_advantage_mod < -0.03:
            recommendations.append("主场优势减弱")

        return "，".join(recommendations) if recommendations else "天气影响可忽略"

    def apply_weather_adjustment(self,
                                 home_xg: float,
                                 away_xg: float,
                                 home_win_prob: float,
                                 draw_prob: float,
                                 away_win_prob: float,
                                 weather_analysis: Dict) -> Dict:
        """
        应用天气调整

        Args:
            home_xg: 主队预期进球
            away_xg: 客队预期进球
            home_win_prob: 主队胜率
            draw_prob: 平局概率
            away_win_prob: 客队胜率
            weather_analysis: 天气分析结果

        Returns:
            调整后的预测
        """
        goal_factor = weather_analysis.get("goal_factor", 1.0)
        home_advantage_mod = weather_analysis.get("home_advantage_mod", 0)

        # 调整xG
        adj_home_xg = home_xg * goal_factor
        adj_away_xg = away_xg * goal_factor

        # 调整主队优势
        adj_home = home_win_prob + home_advantage_mod * 0.3
        adj_away = away_win_prob - home_advantage_mod * 0.3

        # 归一化
        total = adj_home + draw_prob + adj_away
        if total > 0:
            adj_home /= total
            adj_away /= total

        return {
            "adjusted_home_xg": adj_home_xg,
            "adjusted_away_xg": adj_away_xg,
            "adjusted_home_prob": adj_home,
            "adjusted_draw_prob": draw_prob,
            "adjusted_away_prob": adj_away,
            "goal_factor": goal_factor,
            "home_advantage_mod": home_advantage_mod,
            "weather_description": weather_analysis.get("description", ""),
            "recommendation": weather_analysis.get("recommendation", "")
        }


# ============ 测试代码 ============
if __name__ == "__main__":
    analyzer = WeatherAnalyzer()

    print("=" * 60)
    print("天气影响测试")
    print("=" * 60)

    # 测试1：晴好天气
    print("\n测试1：晴好天气 (25°C, 湿度50%, 无降水)")
    result = analyzer.analyze_weather_impact(
        temperature=25, humidity=50, precipitation=0,
        wind_speed=10, altitude=0
    )
    print(f"  天气条件: {result['description']}")
    print(f"  进球因子: {result['goal_factor']:.2f}")
    print(f"  主场优势调整: {result['home_advantage_mod']:+.2f}")
    print(f"  建议: {result['recommendation']}")

    # 测试2：雨天
    print("\n测试2：大雨天气 (15°C, 湿度90%, 降水15mm)")
    result = analyzer.analyze_weather_impact(
        temperature=15, humidity=90, precipitation=15,
        wind_speed=20, altitude=0
    )
    print(f"  天气条件: {result['description']}")
    print(f"  进球因子: {result['goal_factor']:.2f}")
    print(f"  主场优势调整: {result['home_advantage_mod']:+.2f}")
    print(f"  建议: {result['recommendation']}")

    # 测试3：高海拔
    print("\n测试3：高海拔 + 高温 (35°C, 湿度40%, 墨西哥城)")
    result = analyzer.analyze_weather_impact(
        temperature=35, humidity=40, precipitation=0,
        wind_speed=15, altitude=2240
    )
    print(f"  天气条件: {result['description']}")
    print(f"  进球因子: {result['goal_factor']:.2f}")
    print(f"  主场优势调整: {result['home_advantage_mod']:+.2f}")
    print(f"  建议: {result['recommendation']}")

    # 测试4：应用天气调整
    print("\n测试4：应用天气调整到xG")
    print("原始xG: 主队 1.5 | 客队 1.0")

    adjusted = analyzer.apply_weather_adjustment(
        home_xg=1.5, away_xg=1.0,
        home_win_prob=0.50, draw_prob=0.25, away_win_prob=0.25,
        weather_analysis=result
    )

    print(f"调整后xG: 主队 {adjusted['adjusted_home_xg']:.2f} | 客队 {adjusted['adjusted_away_xg']:.2f}")
