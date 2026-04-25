#!/usr/bin/env python3
"""
实时数据模块 v2.0

功能：
1. 近期状态追踪
2. 伤病更新
3. 热身赛结果
4. 天气数据（可选）
5. 球队动态调整
"""

import json
import os
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict


@dataclass
class TeamForm:
    """球队近期状态"""
    team: str
    last_5_results: List[str]  # W/D/L
    goals_scored: List[int]
    goals_conceded: List[int]
    clean_sheets: int
    avg_goals_scored: float
    avg_goals_conceded: float
    form_score: float  # 0-10
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class Injury:
    """伤病信息"""
    player: str
    position: str
    severity: str  # minor, moderate, serious
    expected_return: Optional[str]  # date or "out for tournament"
    

@dataclass
class TeamNews:
    """球队最新消息"""
    team: str
    timestamp: str
    news_type: str  # injury, transfer, suspension, tactical
    headline: str
    details: str
    impact_score: float  # -1.0 to +1.0 (negative=bad, positive=good)


class RealTimeData:
    """实时数据管理器 v2.0"""
    
    def __init__(self, data_dir: str = None):
        if data_dir is None:
            data_dir = os.path.expanduser("~/hermes-world-cup/data/")
        
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        
        # 数据存储
        self.form_data = {}
        self.injury_data = {}
        self.team_news = {}
        
        # 加载缓存数据
        self._load_cached_data()
    
    def _cache_file(self, name: str) -> str:
        return os.path.join(self.data_dir, f"realtime_{name}.json")
    
    def _load_cached_data(self):
        """加载缓存的实时数据"""
        # 加载形式数据
        form_file = self._cache_file("form")
        if os.path.exists(form_file):
            try:
                with open(form_file) as f:
                    self.form_data = json.load(f)
            except:
                pass
        
        # 加载伤病数据
        injury_file = self._cache_file("injuries")
        if os.path.exists(injury_file):
            try:
                with open(injury_file) as f:
                    self.injury_data = json.load(f)
            except:
                pass
    
    def _save_cached_data(self):
        """保存数据到缓存"""
        with open(self._cache_file("form"), "w") as f:
            json.dump(self.form_data, f, indent=2)
        
        with open(self._cache_file("injuries"), "w") as f:
            json.dump(self.injury_data, f, indent=2)
    
    def get_team_form(self, team: str) -> Optional[TeamForm]:
        """获取球队近期状态"""
        if team in self.form_data:
            data = self.form_data[team]
            return TeamForm(**data)
        return None
    
    def update_team_form(
        self,
        team: str,
        last_5_results: List[str] = None,
        goals_scored: List[int] = None,
        goals_conceded: List[int] = None
    ):
        """更新球队状态"""
        if last_5_results is None:
            last_5_results = ["D", "W", "L", "W", "D"]
        if goals_scored is None:
            goals_scored = [1, 2, 0, 3, 1]
        if goals_conceded is None:
            goals_conceded = [1, 0, 2, 1, 1]
        
        # 计算clean sheets
        clean_sheets = sum(1 for gc in goals_conceded if gc == 0)
        
        # 计算平均进球
        avg_scored = sum(goals_scored) / len(goals_scored)
        avg_conceded = sum(goals_conceded) / len(goals_conceded)
        
        # 计算形式分数
        form_score = 0
        for r in last_5_results:
            if r == "W":
                form_score += 3
            elif r == "D":
                form_score += 1
        
        form_score = form_score / (len(last_5_results) * 3) * 10
        
        self.form_data[team] = {
            "team": team,
            "last_5_results": last_5_results,
            "goals_scored": goals_scored,
            "goals_conceded": goals_conceded,
            "clean_sheets": clean_sheets,
            "avg_goals_scored": avg_scored,
            "avg_goals_conceded": avg_conceded,
            "form_score": round(form_score, 2)
        }
        
        self._save_cached_data()
    
    def get_form_adjustment(self, team: str) -> Tuple[float, float]:
        """
        获取形式调整因子
        
        Returns:
            (attack_adj, defense_adj)
            attack_adj: 正值表示状态好，负值表示状态差
            defense_adj: 负值表示状态好（丢球少），正值表示状态差
        """
        form = self.get_team_form(team)
        
        if form is None:
            return 0.0, 0.0
        
        # 形式分数转换为调整因子
        # form_score范围0-10，转换到-0.2到+0.2
        form_factor = (form.form_score - 5) / 25  # -0.2到+0.2
        
        # 进攻调整
        # avg_goals_scored基准是1.3左右
        attack_factor = (form.avg_goals_scored - 1.3) / 3
        
        # 防守调整
        # avg_goals_conceded基准是1.2左右
        defense_factor = -(form.avg_goals_conceded - 1.2) / 3
        
        # 综合调整
        attack_adj = (form_factor + attack_factor) / 2
        defense_adj = (form_factor + defense_factor) / 2
        
        # 限制范围
        attack_adj = max(-0.3, min(0.3, attack_adj))
        defense_adj = max(-0.3, min(0.3, defense_adj))
        
        return round(attack_adj, 3), round(defense_adj, 3)
    
    def add_injury(self, team: str, player: str, position: str, 
                   severity: str = "moderate", expected_return: str = None):
        """添加伤病信息"""
        if team not in self.injury_data:
            self.injury_data[team] = []
        
        injury = {
            "player": player,
            "position": position,
            "severity": severity,
            "expected_return": expected_return
        }
        
        # 检查是否已存在
        existing = [i for i in self.injury_data[team] if i["player"] == player]
        if existing:
            self.injury_data[team] = [
                i if i["player"] != player else injury 
                for i in self.injury_data[team]
            ]
        else:
            self.injury_data[team].append(injury)
        
        self._save_cached_data()
    
    def remove_injury(self, team: str, player: str):
        """移除伤病信息（球员复出）"""
        if team in self.injury_data:
            self.injury_data[team] = [
                i for i in self.injury_data[team] if i["player"] != player
            ]
            self._save_cached_data()
    
    def get_injuries(self, team: str) -> List[Injury]:
        """获取球队伤病列表"""
        if team not in self.injury_data:
            return []
        
        return [Injury(**i) for i in self.injury_data[team]]
    
    def get_injury_impact(self, team: str) -> float:
        """
        评估伤病对球队的影响
        
        Returns:
            -1.0 到 +1.0（负值表示削弱，正值表示增强）
        """
        injuries = self.get_injuries(team)
        
        if not injuries:
            return 0.0
        
        # 关键位置权重
        position_weights = {
            "GK": 1.5,  # 守门员最重要
            "CB": 1.2,
            "LB": 1.0,
            "RB": 1.0,
            "CDM": 1.1,
            "CM": 1.0,
            "CAM": 1.3,  # 进攻核心
            "LW": 1.2,
            "RW": 1.2,
            "ST": 1.4,  # 前锋
        }
        
        severity_weights = {
            "minor": 0.3,
            "moderate": 0.6,
            "serious": 1.0,
        }
        
        total_impact = 0.0
        for injury in injuries:
            pos_weight = position_weights.get(injury.position, 1.0)
            sev_weight = severity_weights.get(injury.severity, 0.5)
            total_impact -= pos_weight * sev_weight * 0.15
        
        return round(max(-1.0, min(0.5, total_impact)), 3)
    
    def get_missing_players(self, team: str) -> List[str]:
        """获取缺阵球员名单"""
        injuries = self.get_injuries(team)
        return [i.player for i in injuries if i.severity in ["moderate", "serious"]]
    
    def initialize_world_cup_data(self):
        """初始化世界杯参赛球队的基础数据"""
        # 为32强设置基础状态数据
        teams_data = {
            # 强队 - 状态好
            "Argentina": {
                "last_5_results": ["W", "W", "D", "W", "W"],
                "goals_scored": [2, 3, 1, 2, 3],
                "goals_conceded": [0, 0, 1, 0, 1],
            },
            "Brazil": {
                "last_5_results": ["W", "W", "W", "D", "W"],
                "goals_scored": [3, 2, 4, 1, 2],
                "goals_conceded": [0, 1, 0, 1, 1],
            },
            "France": {
                "last_5_results": ["W", "W", "L", "W", "D"],
                "goals_scored": [2, 3, 0, 2, 1],
                "goals_conceded": [1, 0, 1, 1, 1],
            },
            "England": {
                "last_5_results": ["W", "D", "W", "W", "L"],
                "goals_scored": [2, 1, 3, 2, 0],
                "goals_conceded": [0, 1, 1, 0, 1],
            },
            "Germany": {
                "last_5_results": ["W", "L", "W", "D", "W"],
                "goals_scored": [3, 0, 2, 1, 2],
                "goals_conceded": [1, 2, 0, 1, 0],
            },
            "Spain": {
                "last_5_results": ["W", "W", "W", "D", "W"],
                "goals_scored": [4, 3, 2, 1, 3],
                "goals_conceded": [0, 1, 0, 1, 0],
            },
            # 中等球队
            "Netherlands": {
                "last_5_results": ["W", "D", "W", "L", "D"],
                "goals_scored": [2, 1, 2, 0, 1],
                "goals_conceded": [0, 1, 1, 2, 1],
            },
            "Portugal": {
                "last_5_results": ["W", "W", "L", "W", "D"],
                "goals_scored": [3, 2, 0, 2, 1],
                "goals_conceded": [0, 0, 1, 1, 1],
            },
            "Belgium": {
                "last_5_results": ["W", "L", "D", "W", "L"],
                "goals_scored": [2, 0, 1, 3, 0],
                "goals_conceded": [0, 2, 1, 1, 2],
            },
            "Croatia": {
                "last_5_results": ["D", "W", "L", "W", "D"],
                "goals_scored": [1, 2, 0, 2, 1],
                "goals_conceded": [1, 0, 1, 1, 1],
            },
            "Uruguay": {
                "last_5_results": ["W", "W", "D", "L", "W"],
                "goals_scored": [2, 2, 1, 0, 2],
                "goals_conceded": [0, 1, 1, 2, 1],
            },
            "Mexico": {
                "last_5_results": ["W", "D", "W", "L", "D"],
                "goals_scored": [2, 1, 2, 0, 1],
                "goals_conceded": [1, 1, 0, 2, 1],
            },
            "USA": {
                "last_5_results": ["W", "W", "D", "L", "W"],
                "goals_scored": [2, 2, 1, 0, 2],
                "goals_conceded": [0, 1, 1, 1, 1],
            },
            # 弱队 - 状态一般
            "Qatar": {
                "last_5_results": ["L", "D", "L", "W", "L"],
                "goals_scored": [0, 1, 0, 2, 0],
                "goals_conceded": [2, 1, 2, 1, 3],
            },
            "Saudi Arabia": {
                "last_5_results": ["L", "W", "L", "D", "L"],
                "goals_scored": [0, 2, 0, 1, 0],
                "goals_conceded": [3, 1, 2, 1, 2],
            },
        }
        
        # 默认数据（用于未列出的球队）
        default_data = {
            "last_5_results": ["D", "L", "W", "L", "D"],
            "goals_scored": [1, 0, 2, 0, 1],
            "goals_conceded": [1, 2, 1, 2, 1],
        }
        
        for team, data in teams_data.items():
            self.update_team_form(team, **data)
        
        # 为其他球队设置默认数据
        all_teams = [
            "Ecuador", "Senegal", "Netherlands", "Iran", "Wales",
            "Poland", "Australia", "Denmark", "Tunisia", "Costa Rica",
            "Japan", "Canada", "Morocco", "Switzerland", "Cameroon",
            "Ghana", "South Korea", "Serbia", "Egypt", "Ivory Coast"
        ]
        
        for team in all_teams:
            if team not in self.form_data:
                self.update_team_form(team, **default_data)
        
        self._save_cached_data()
    
    def simulate_friendly_results(self, team1: str, team2: str) -> Tuple[str, int, int]:
        """
        模拟热身赛结果（当没有真实数据时）
        
        Returns:
            (result, team1_goals, team2_goals)
        """
        form1 = self.get_team_form(team1)
        form2 = self.get_team_form(team2)
        
        # 基于形式估算xG
        xg1 = 1.3 + (form1.avg_goals_scored - 1.3) * 0.3 if form1 else 1.3
        xg2 = 1.2 + (form2.avg_goals_scored - 1.2) * 0.3 if form2 else 1.2
        
        # 添加一些随机性
        import numpy as np
        goals1 = max(0, int(np.random.poisson(xg1 * 1.2)))
        goals2 = max(0, int(np.random.poisson(xg2)))
        
        if goals1 > goals2:
            result = "W"
        elif goals1 < goals2:
            result = "L"
        else:
            result = "D"
        
        return result, goals1, goals2


# 全局实例
_realtime_data = None

def get_realtime_data() -> RealTimeData:
    """获取实时数据全局实例"""
    global _realtime_data
    if _realtime_data is None:
        _realtime_data = RealTimeData()
    return _realtime_data


if __name__ == "__main__":
    rtd = RealTimeData()
    
    print("=== 实时数据模块测试 ===\n")
    
    # 初始化世界杯数据
    rtd.initialize_world_cup_data()
    
    # 测试形式调整
    teams = ["Argentina", "Brazil", "Qatar"]
    for team in teams:
        form = rtd.get_team_form(team)
        attack_adj, defense_adj = rtd.get_form_adjustment(team)
        print(f"{team}:")
        print(f"  形式: {form.last_5_results} | 分数: {form.form_score}")
        print(f"  调整: 进攻={attack_adj:+.2f}, 防守={defense_adj:+.2f}")
        print()
    
    # 测试伤病
    rtd.add_injury("France", "Mbappe", "ST", "minor")
    rtd.add_injury("France", "Kante", "CDM", "serious", "out for tournament")
    
    print("法国伤病:")
    for injury in rtd.get_injuries("France"):
        print(f"  {injury.player} ({injury.position}): {injury.severity}")
    print(f"  影响: {rtd.get_injury_impact('France'):.2f}")
