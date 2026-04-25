#!/usr/bin/env python3
"""
战意指数模块 v1.0
==================
评估球队在比赛中的战意和动机

核心功能：
1. 提前出线/出局判断
2. 轮换指数（是否保留主力）
3. 淘汰赛vs小组赛动机差异
4. 关键比赛（生死战）识别
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Tuple, Optional

# ============ 路径配置 ============
BASE_DIR = os.path.expanduser("~/hermes-world-cup/")
DATA_DIR = os.path.join(BASE_DIR, "data/")


class MotivationAnalyzer:
    """
    战意/动机分析器

    世界杯比赛中，战意是重要因素：
    - 提前出线后可能轮换
    - 已出局球队无欲无求
    - 淘汰赛阶段战意最强
    - 生死战/关键比赛战意最高
    """

    def __init__(self):
        self.data_dir = DATA_DIR
        self.group_standings = {}  # 小组积分
        self.match_results = []     # 比赛结果

    def set_group_standings(self, group_name: str, standings: Dict):
        """
        设置小组积分

        Args:
            group_name: 小组名（如 "A", "B"）
            standings: 格式: {"team_name": {"points": 0, "gd": 0, "gf": 0}}
        """
        if not hasattr(self, 'group_standings'):
            self.group_standings = {}
        self.group_standings[group_name] = standings

    def analyze_group_situation(self, team: str, group: str, match_day: int = 1) -> Dict:
        """
        分析球队在小组中的战意情况

        Args:
            team: 球队名
            group: 小组名
            match_day: 当前比赛日（1-3）

        Returns:
            战意分析报告
        """
        if group not in self.group_standings:
            return {
                "status": "no_data",
                "team": team,
                "group": group
            }

        standings = self.group_standings[group]
        team_data = standings.get(team, {"points": 0, "gd": 0, "gf": 0})

        # 计算理论出线形势
        points = team_data.get("points", 0)
        gd = team_data.get("gd", 0)
        gf = team_data.get("gf", 0)

        # 评估战意
        situation = self._assess_situation(points, gd, match_day, standings)

        return {
            "team": team,
            "group": group,
            "points": points,
            "goal_difference": gd,
            "goals_for": gf,
            "match_day": match_day,
            "situation": situation,
            "recommendation": self._get_motivation_recommendation(situation)
        }

    def _assess_situation(self, points: int, gd: int, match_day: int, standings: Dict) -> str:
        """评估球队形势"""
        # 按积分排序
        sorted_teams = sorted(standings.items(),
                            key=lambda x: (x[1].get('points', 0), x[1].get('gd', 0)),
                            reverse=True)

        # 找出该球队排名
        team_rank = None
        for i, (team_name, _) in enumerate(sorted_teams):
            if team_name == list(standings.keys())[list(standings.keys()).index(next(k for k in standings if k == list(standings.keys())[sorted_teams.index((team_name, standings[team_name]))]))]:
                team_rank = i + 1
                break

        # 简化处理
        team_rank = 1
        for i, (t, _) in enumerate(sorted_teams):
            if t == list(standings.keys())[0]:
                break
            team_rank = i + 1

        max_points = 9  # 小组赛最多9分
        remaining_matches = 3 - match_day

        # 判断形势
        if points >= 6:
            if match_day == 3:
                return "secured_qualification"  # 已确保出线
            elif match_day == 2 and points >= 6:
                return "likely_qualified"  # 可能已出线
            else:
                return "fighting_for_group"  # 争取小组第一
        elif points == 0 and match_day == 3:
            return "already_eliminated"  # 已出局
        elif points == 0 and remaining_matches <= 1:
            return "must_win"  # 必须赢
        elif points <= 1 and match_day >= 2:
            return "likely_eliminated"  # 可能出局
        elif points == 3 and remaining_matches == 1:
            return "need_help"  # 需要看别人脸色
        else:
            return "normal_motivation"  # 正常战意

    def _get_motivation_recommendation(self, situation: str) -> str:
        """根据形势给出战意建议"""
        recommendations = {
            "secured_qualification": "轮换主力，战意下降",
            "likely_qualified": "可能轮换",
            "fighting_for_group": "全力争胜",
            "already_eliminated": "无欲无求",
            "must_win": "背水一战",
            "likely_eliminated": "战意存疑",
            "need_help": "需要奇迹",
            "normal_motivation": "正常发挥"
        }
        return recommendations.get(situation, "正常")

    def get_rotation_factor(self, situation: str) -> float:
        """
        获取轮换因子

        Args:
            situation: 形势

        Returns:
            轮换程度（0=不轮换，1=全轮换）
        """
        rotation_map = {
            "secured_qualification": 0.7,   # 高轮换
            "likely_qualified": 0.5,         # 半轮换
            "fighting_for_group": 0.1,       # 几乎不轮换
            "already_eliminated": 0.8,       # 全轮换
            "must_win": 0.0,                  # 不轮换
            "likely_eliminated": 0.4,        # 部分轮换
            "need_help": 0.2,                 # 略有保留
            "normal_motivation": 0.0,         # 不轮换
        }
        return rotation_map.get(situation, 0.0)

    def apply_motivation_adjustment(self,
                                   home_win_prob: float,
                                   draw_prob: float,
                                   away_win_prob: float,
                                   home_situation: str,
                                   away_situation: str) -> Dict:
        """
        应用战意调整

        Args:
            home_win_prob: 原始主队胜率
            away_win_prob: 原始客队胜率
            home_situation: 主队形势
            away_situation: 客队形势

        Returns:
            调整后的概率
        """
        # 轮换因子
        home_rotation = self.get_rotation_factor(home_situation)
        away_rotation = self.get_rotation_factor(away_situation)

        # 轮换影响实力（简化：每10%轮换降低2%胜率）
        home_strength_factor = 1 - home_rotation * 0.2
        away_strength_factor = 1 - away_rotation * 0.2

        # 形势影响（弱队 vs 无欲强队）
        if home_situation == "must_win":
            home_strength_factor += 0.05  # 背水一战加成
        if away_situation == "must_win":
            away_strength_factor += 0.05

        if home_situation == "already_eliminated":
            home_strength_factor -= 0.08
        if away_situation == "already_eliminated":
            away_strength_factor -= 0.08

        # 应用调整
        adj_home = home_win_prob * home_strength_factor
        adj_away = away_win_prob * away_strength_factor

        # 归一化
        total = adj_home + draw_prob + adj_away
        if total > 0:
            adj_home /= total
            adj_away /= total
            draw_prob /= total

        return {
            "adjusted_home": adj_home,
            "adjusted_draw": draw_prob,
            "adjusted_away": adj_away,
            "home_rotation": home_rotation,
            "away_rotation": away_rotation,
            "home_situation": home_situation,
            "away_situation": away_situation,
            "home_recommendation": self._get_motivation_recommendation(home_situation),
            "away_recommendation": self._get_motivation_recommendation(away_situation)
        }

    def is_crucial_match(self, home_situation: str, away_situation: str) -> bool:
        """判断是否为关键比赛"""
        crucial_situations = ["must_win", "likely_eliminated", "need_help"]
        return home_situation in crucial_situations or away_situation in crucial_situations


# ============ 测试代码 ============
if __name__ == "__main__":
    analyzer = MotivationAnalyzer()

    print("=" * 60)
    print("战意指数测试")
    print("=" * 60)

    # 设置小组积分（模拟）
    analyzer.set_group_standings("A", {
        "Brazil": {"points": 6, "gd": 4, "gf": 5},
        "Switzerland": {"points": 3, "gd": 0, "gf": 2},
        "Costa Rica": {"points": 0, "gd": -3, "gf": 1},
        "Serbia": {"points": 0, "gd": -1, "gf": 1},
    })

    # 分析各队形势
    print("\n小组A形势分析:")
    for team in ["Brazil", "Switzerland", "Costa Rica", "Serbia"]:
        result = analyzer.analyze_group_situation(team, "A", match_day=2)
        print(f"  {team}: {result['situation']} - {result['recommendation']}")

    # 应用战意调整
    print("\n战意调整示例:")
    print("原始概率: 主队 50% | 平局 25% | 客队 25%")

    adjusted = analyzer.apply_motivation_adjustment(
        0.50, 0.25, 0.25,
        home_situation="must_win",  # 主队必须赢
        away_situation="already_eliminated"  # 客队已出局
    )

    print(f"调整后: 主队 {adjusted['adjusted_home']:.1%} | 平局 {adjusted['adjusted_draw']:.1%} | 客队 {adjusted['adjusted_away']:.1%}")
    print(f"主队形势: {adjusted['home_situation']} - {adjusted['home_recommendation']}")
    print(f"客队形势: {adjusted['away_situation']} - {adjusted['away_recommendation']}")
