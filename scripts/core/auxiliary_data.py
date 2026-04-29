#!/usr/bin/env python3
"""
辅助数据管理器
====================
管理球员数据、近期状态、战术信息等辅助预测数据

这些数据需要手动更新或从外部数据源获取
"""

import json
import os
from typing import Dict, List, Optional

BASE_DIR = os.path.expanduser("~/hermes-world-cup/")
DATA_DIR = os.path.join(BASE_DIR, "data/")


class AuxiliaryDataManager:
    """
    辅助数据管理器
    
    管理以下辅助预测数据：
    1. 球员伤停信息
    2. 近期状态
    3. 战术阵型
    4. 球队内部信息（换帅、内讧等）
    5. 场馆因素
    """
    
    def __init__(self):
        self.file_path = os.path.join(DATA_DIR, "teams", "auxiliary_data.json")
        self.data = self._load_data()
    
    def _load_data(self) -> Dict:
        """加载辅助数据"""
        if os.path.exists(self.file_path):
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def _save_data(self):
        """保存辅助数据"""
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
    
    def get_player_data(self, team: str) -> Dict:
        """获取球员数据"""
        team_lower = team.lower()
        teams = self.data.get("players", {})
        for name, data in teams.items():
            if name.lower() == team_lower or team_lower in name.lower():
                return data
        return self._default_player_data()
    
    def _default_player_data(self) -> Dict:
        """默认球员数据"""
        return {
            "key_players_available": 3,
            "total_stars": 5,
            "injuries": [],
            "suspensions": [],
            "availability": "good"  # good/suspect/doubtful/bad
        }
    
    def get_recent_form(self, team: str) -> Dict:
        """获取近期状态数据"""
        team_lower = team.lower()
        forms = self.data.get("recent_form", {})
        for name, data in forms.items():
            if name.lower() == team_lower or team_lower in name.lower():
                return data
        return self._default_recent_form()
    
    def _default_recent_form(self) -> Dict:
        """默认近期状态"""
        return {
            "form_rating": 0.5,  # 0-1，0.5为平均水平
            "trend": "stable",  # improving/stable/declining
            "last_5_results": [],
            "goals_scored_avg": 1.5,
            "goals_conceded_avg": 1.0,
            "clean_sheets": 1,
            "confidence": "medium"  # high/medium/low
        }
    
    def get_tactics(self, team: str) -> Dict:
        """获取战术信息"""
        team_lower = team.lower()
        tactics_data = self.data.get("tactics", {})
        for name, data in tactics_data.items():
            if name.lower() == team_lower or team_lower in name.lower():
                return data
        return self._default_tactics()
    
    def _default_tactics(self) -> Dict:
        """默认战术信息"""
        return {
            "preferred_formation": "4-3-3",
            "formation_variations": ["4-3-3", "4-2-3-1"],
            "pressing_intensity": "medium",  # high/medium/low
            "build_up_style": "possession",  # possession/direct/counter
            "defensive_line": "medium",  # high/medium/low
            "set_piece_strength": 0.5  # 0-1
        }
    
    def get_team_morale(self, team: str) -> Dict:
        """获取球队内部信息"""
        team_lower = team.lower()
        morale_data = self.data.get("team_morale", {})
        for name, data in morale_data.items():
            if name.lower() == team_lower or team_lower in name.lower():
                return data
        return self._default_team_morale()
    
    def _default_team_morale(self) -> Dict:
        """默认球队内部信息"""
        return {
            "coach_change": False,
            "coach_change_date": None,
            "internal_issues": False,
            "issues_desc": "",
            "morale_rating": 0.7,  # 0-1
            " unity ": "good",  # good/medium/poor
            "motivation_factors": []
        }
    
    def get_venue_info(self, team: str) -> Dict:
        """获取场馆因素"""
        team_lower = team.lower()
        venues = self.data.get("venues", {})
        for name, data in venues.items():
            if name.lower() == team_lower or team_lower in name.lower():
                return data
        return self._default_venue()
    
    def _default_venue(self) -> Dict:
        """默认场馆信息"""
        return {
            "is_home": True,
            "stadium_name": "未知",
            "fan_atmosphere": 0.7,  # 0-1
            "pitch_condition": "good",  # good/medium/poor
            "travel_distance": 0,  # 飞行小时数
            "weather_advantage": 0  # 天气适应度 0-1
        }
    
    def update_player_data(self, team: str, data: Dict):
        """更新球员数据"""
        if "players" not in self.data:
            self.data["players"] = {}
        self.data["players"][team] = data
        self._save_data()
    
    def update_recent_form(self, team: str, data: Dict):
        """更新近期状态"""
        if "recent_form" not in self.data:
            self.data["recent_form"] = {}
        self.data["recent_form"][team] = data
        self._save_data()
    
    def update_tactics(self, team: str, data: Dict):
        """更新战术信息"""
        if "tactics" not in self.data:
            self.data["tactics"] = {}
        self.data["tactics"][team] = data
        self._save_data()
    
    def update_team_morale(self, team: str, data: Dict):
        """更新球队内部信息"""
        if "team_morale" not in self.data:
            self.data["team_morale"] = {}
        self.data["team_morale"][team] = data
        self._save_data()
    
    def update_venue_info(self, team: str, data: Dict):
        """更新场馆信息"""
        if "venues" not in self.data:
            self.data["venues"] = {}
        self.data["venues"][team] = data
        self._save_data()
    
    def calculate_momentum_bonus(self, team: str) -> float:
        """
        计算球队势头加成
        基于近期状态、士气等因素
        返回 -0.1 到 +0.1 的调整值
        """
        form = self.get_recent_form(team)
        morale = self.get_team_morale(team)
        
        bonus = 0.0
        
        # 近期状态加成
        form_rating = form.get("form_rating", 0.5)
        if form_rating > 0.6:
            bonus += 0.03
        elif form_rating < 0.4:
            bonus -= 0.03
        
        # 趋势加成
        trend = form.get("trend", "stable")
        if trend == "improving":
            bonus += 0.02
        elif trend == "declining":
            bonus -= 0.02
        
        # 士气加成
        morale_rating = morale.get("morale_rating", 0.7)
        if morale_rating > 0.8:
            bonus += 0.02
        elif morale_rating < 0.5:
            bonus -= 0.02
        
        # 内部问题惩罚
        if morale.get("internal_issues", False):
            bonus -= 0.05
        
        # 换帅后蜜月期加成
        if morale.get("coach_change", False):
            bonus += 0.02
        
        return max(-0.1, min(0.1, bonus))  # 限制在±0.1
    
    def calculate_player_penalty(self, team: str) -> float:
        """
        计算球员缺阵惩罚
        返回 0.0 到 -0.15 的惩罚值
        """
        player_data = self.get_player_data(team)
        
        availability = player_data.get("availability", "good")
        
        if availability == "good":
            return 0.0
        elif availability == "suspect":
            return -0.03
        elif availability == "doubtful":
            return -0.08
        elif availability == "bad":
            return -0.15
        
        return 0.0
    
    def calculate_venue_advantage(self, team: str, is_home: bool) -> float:
        """
        计算场馆优势加成
        返回 -0.1 到 +0.1 的调整值
        """
        venue = self.get_venue_info(team)
        morale = self.get_team_morale(team)
        
        bonus = 0.0
        
        if is_home:
            # 主场球迷加成
            fan_atm = venue.get("fan_atmosphere", 0.7)
            bonus += fan_atm * 0.05
            
            # 场地条件加成
            pitch = venue.get("pitch_condition", "good")
            if pitch == "good":
                bonus += 0.02
            elif pitch == "poor":
                bonus -= 0.02
            
            # 飞行距离惩罚（客队）
            travel = venue.get("travel_distance", 0)
            if travel > 10:
                bonus -= 0.02
        
        return max(-0.1, min(0.1, bonus))


# 全局实例
aux_data = None

def get_aux_data() -> AuxiliaryDataManager:
    """获取辅助数据管理器单例"""
    global aux_data
    if aux_data is None:
        aux_data = AuxiliaryDataManager()
    return aux_data