#!/usr/bin/env python3
"""
球队基础数据管理模块
- 动态Elo评分系统
- FIFA排名
- 近期战绩
- 球队状态指标
"""

import json
import os
import math
from datetime import datetime, timedelta
from collections import defaultdict

# ============ 路径配置 ============
BASE_DIR = os.path.expanduser("~/hermes-world-cup/")
DATA_DIR = os.path.join(BASE_DIR, "data/")
os.makedirs(DATA_DIR, exist_ok=True)

ELO_FILE = os.path.join(DATA_DIR, "elo_ratings.json")
FIFRA_FILE = os.path.join(DATA_DIR, "fifa_rankings.json")
RECENT_FORM_FILE = os.path.join(DATA_DIR, "recent_form.json")
H2H_FILE = os.path.join(DATA_DIR, "h2h_records.json")

# ============ Elo评分系统 ============
ELO_BASE = 1500
ELO_K_FACTOR = 32  # 每场比赛的K值
ELO_HOME_ADVANTAGE = 65  # 主场优势（Elo点数）

class EloSystem:
    """动态Elo评分系统"""

    def __init__(self):
        self.ratings = self._load_elo()

    def _load_elo(self) -> dict:
        """加载Elo评分"""
        if os.path.exists(ELO_FILE):
            with open(ELO_FILE) as f:
                data = json.load(f)
                return data.get("ratings", {})
        return self._default_elo()

    def _default_elo(self) -> dict:
        """默认Elo评分（基于2026世界杯分组，更大的顶级球队差距）"""
        return {
            # 顶级强队 (1900+)
            "Brazil": 1920, "Spain": 1880, "France": 1870, "Argentina": 1850,
            "England": 1830, "Germany": 1820, "Portugal": 1810, "Netherlands": 1800,
            # 强队 (1750-1849)
            "Italy": 1795, "Belgium": 1780, "Croatia": 1770, "Uruguay": 1760,
            "Morocco": 1755, "USA": 1745, "Mexico": 1735, "Colombia": 1725,
            "Japan": 1720, "Senegal": 1715,
            # 中游 (1650-1749)
            "Poland": 1695, "Chile": 1685, "Austria": 1675, "Switzerland": 1665,
            "Ukraine": 1655, "Australia": 1645, "Serbia": 1635, "Egypt": 1625,
            "Paraguay": 1615, "Nigeria": 1605, "Ecuador": 1595,
            # 较弱 (1500-1649)
            "Ivory Coast": 1585, "Algeria": 1575, "Ghana": 1565,
            "Qatar": 1555, "Iraq": 1545, "Jordan": 1535,
            "Panama": 1525, "Saudi Arabia": 1515, "Cameroon": 1510,
            "Tunisia": 1505, "Bosnia": 1495, "Scotland": 1490,
            "Iran": 1485, "Norway": 1500, "New Zealand": 1450,
            "Uzbekistan": 1475, "South Africa": 1465, "South Korea": 1550,
            # 2026新增
            "Canada": 1570, "Turkey": 1580, "Hungary": 1560,
            "Czech Republic": 1540, "Denmark": 1620, "Costa Rica": 1480,
            "Jamaica": 1450, "Israel": 1500, "Wales": 1580,
        }

    def get_rating(self, team: str) -> float:
        """获取球队Elo评分"""
        return self.ratings.get(team, ELO_BASE)

    def win_prob(self, team_a: str, team_b: str, is_home_a: bool = True) -> float:
        """计算A对B的胜率（考虑主客场）"""
        elo_a = self.get_rating(team_a) + (ELO_HOME_ADVANTAGE if is_home_a else 0)
        elo_b = self.get_rating(team_b) + (ELO_HOME_ADVANTAGE if not is_home_a else 0)
        return 1 / (1 + 10 ** ((elo_b - elo_a) / 400))

    # 动态K值配置（根据比赛阶段）
    ELO_K_STAGE = {
        "group": 15,      # 小组赛：低风险，低波动
        "round16": 25,    # 16强：中等
        "quarter": 32,    # 8强：标准
        "semi": 45,       # 半决赛：重要
        "final": 60,      # 决赛：最高风险
        "friendly": 10,   # 友谊赛：最低
        "qualifier": 20,  # 资格赛
    }

    def update(self, winner: str, loser: str, draw: bool = False,
               is_home_winner: bool = True, is_home_loser: bool = None,
               stage: str = "group", goal_diff: int = 0):
        """
        更新Elo评分

        Args:
            winner: 胜者
            loser: 输者
            draw: 是否平局
            is_home_winner: 胜者是否为主场
            is_home_loser: 输者是否为主场
            stage: 比赛阶段 (group/round16/quarter/semi/final/friendly/qualifier)
            goal_diff: 净胜球差（用于调整K值）
        """
        # 动态K值
        k_base = self.ELO_K_STAGE.get(stage, 32)

        # 爆冷加成：净胜球差距大时，降低K值（避免大胜后评分变化过大）
        # 净胜球>=3时减少K值（强队赢弱队不应该获得太多分）
        if goal_diff >= 3:
            k_multiplier = 0.8
        elif goal_diff >= 2:
            k_multiplier = 0.9
        else:
            k_multiplier = 1.0

        # 爆冷调整：输家排名比赢家高（弱队赢强队）时，赢家获得额外分数
        # 这个通过expected_winner自动处理，但可以额外加成
        upset_bonus = 1.0  # 基础加成

        k = k_base * k_multiplier

        # 确定主客场
        if is_home_winner:
            elo_winner = self.get_rating(winner) + ELO_HOME_ADVANTAGE
            elo_loser = self.get_rating(loser)
        else:
            elo_winner = self.get_rating(winner)
            elo_loser = self.get_rating(loser) + ELO_HOME_ADVANTAGE

        # 计算预期胜率
        expected_winner = 1 / (1 + 10 ** ((elo_loser - elo_winner) / 400))

        if draw:
            # 平局：赢家损失分数，输家获得分数
            k_draw = k / 2
            self.ratings[winner] = self.ratings.get(winner, ELO_BASE) + k_draw * (0.5 - expected_winner)
            self.ratings[loser] = self.ratings.get(loser, ELO_BASE) + k_draw * (0.5 - (1 - expected_winner))
        else:
            # 非平局
            self.ratings[winner] = self.ratings.get(winner, ELO_BASE) + k * (1 - expected_winner)
            self.ratings[loser] = self.ratings.get(loser, ELO_BASE) - k * expected_winner

        # 确保评分在合理范围
        self.ratings[winner] = max(1000, min(2000, self.ratings.get(winner, ELO_BASE)))
        self.ratings[loser] = max(1000, min(2000, self.ratings.get(loser, ELO_BASE)))

    def save(self):
        """保存Elo评分"""
        with open(ELO_FILE, "w") as f:
            json.dump({"ratings": self.ratings, "updated_at": datetime.now().isoformat()}, f, indent=2)

    def reset_to_default(self):
        """重置为默认Elo"""
        self.ratings = self._default_elo()
        self.save()


# ============ FIFA排名系统 ============
class FIFARanking:
    """FIFA排名系统（使用Elo-based公式，与Elo系统联动）"""

    def __init__(self):
        self.rankings = self._load_rankings()

    def _load_rankings(self) -> dict:
        """加载FIFA排名"""
        if os.path.exists(FIFRA_FILE):
            with open(FIFRA_FILE) as f:
                data = json.load(f)
                return data.get("rankings", {})
        return self._default_rankings()

    def _default_rankings(self) -> dict:
        """默认FIFA排名（基于2026预选赛）"""
        # 排名数字越小越强
        return {
            "Spain": 1, "France": 2, "Brazil": 3, "Argentina": 4,
            "England": 5, "Germany": 6, "Portugal": 7, "Netherlands": 8,
            "Italy": 9, "Belgium": 10, "Croatia": 11, "Uruguay": 12,
            "Morocco": 13, "USA": 14, "Mexico": 15, "Colombia": 16,
            "Japan": 17, "Senegal": 18, "Poland": 19, "Switzerland": 20,
            "Chile": 21, "Austria": 22, "Ukraine": 23, "Australia": 24,
            "Serbia": 25, "Egypt": 26, "Paraguay": 27, "Nigeria": 28,
            "Ecuador": 29, "Ivory Coast": 30, "Algeria": 31, "Ghana": 32,
            "Qatar": 33, "Iraq": 34, "Jordan": 35, "Panama": 36,
            "Saudi Arabia": 37, "Cameroon": 38, "Tunisia": 39, "Bosnia": 40,
            "Scotland": 41, "Iran": 42, "Norway": 43, "New Zealand": 44,
            "Uzbekistan": 45, "South Africa": 46, "South Korea": 47,
            "Canada": 48, "Turkey": 49, "Hungary": 50, "Czech Republic": 51,
            "Denmark": 22, "Costa Rica": 52, "Jamaica": 53, "Wales": 35,
        }

    def get_rank(self, team: str) -> int:
        """获取球队排名（数字越小越强）"""
        return self.rankings.get(team, 100)

    def rank_to_elo_factor(self, team: str) -> float:
        """将排名转换为Elo调整因子"""
        rank = self.get_rank(team)
        # 排名第1得1.0，第100得0.5
        return max(0.5, 1.5 - rank / 200)

    def save(self):
        """保存FIFA排名"""
        with open(FIFRA_FILE, "w") as f:
            json.dump({"rankings": self.rankings, "updated_at": datetime.now().isoformat()}, f, indent=2)


# ============ 近期战绩系统 ============
class RecentForm:
    """球队近期战绩追踪"""

    def __init__(self):
        self.form = self._load_form()

    def _load_form(self) -> dict:
        """加载近期战绩"""
        if os.path.exists(RECENT_FORM_FILE):
            with open(RECENT_FORM_FILE) as f:
                data = json.load(f)
                return data.get("form", {})
        return {}

    def get_form(self, team: str, games: int = 10) -> dict:
        """获取球队近期战绩"""
        team_data = self.form.get(team, {"matches": []})
        recent = team_data["matches"][-games:]
        return {
            "matches": recent,
            "wins": sum(1 for m in recent if m.get("result") == "W"),
            "draws": sum(1 for m in recent if m.get("result") == "D"),
            "losses": sum(1 for m in recent if m.get("result") == "L"),
            "goals_for": sum(m.get("gf", 0) for m in recent),
            "goals_against": sum(m.get("ga", 0) for m in recent),
        }

    def form_rating(self, team: str, games: int = 10) -> float:
        """计算状态评分 (0-100) - 使用时间加权，越近的比赛权重越高"""
        data = self.get_form(team, games)
        matches = data["matches"]
        total = len(matches)
        if total == 0:
            return 50.0  # 默认中等状态

        # 时间加权：使用指数衰减，越近的比赛权重越高
        # decay_factor: 每场比赛权重是前一场的 decay 倍 (0.85 = 每场衰减15%)
        return self._weighted_form_rating(matches, decay_factor=0.88)

    def _weighted_form_rating(self, matches: list, decay_factor: float = 0.88) -> float:
        """
        时间加权状态评分

        算法：
        - 最近的比赛权重最高（decay_factor^(n-1)）
        - 最远的比赛权重最低（decay_factor^0 = 1）
        - 使用指数衰减加权平均

        Example (decay=0.88, 5场比赛):
        - Game 1 (most recent): weight = 0.88^4 = 0.60
        - Game 2: weight = 0.88^3 = 0.68
        - Game 3: weight = 0.88^2 = 0.77
        - Game 4: weight = 0.88^1 = 0.88
        - Game 5 (oldest): weight = 0.88^0 = 1.00

        然后加权平均，而非简单平均
        """
        if not matches:
            return 50.0

        n = len(matches)
        # 指数衰减权重：最近的权重最高
        # weights[i] = decay_factor ^ (n - 1 - i)  => matches[0]是最近的
        weights = [decay_factor ** (n - 1 - i) for i in range(n)]

        # 计算加权得分
        weighted_points = 0.0
        total_weight = 0.0

        for i, match in enumerate(matches):
            # 得分：W=3, D=1, L=0
            result = match.get("result", "D")
            if result == "W":
                pts = 3.0
            elif result == "D":
                pts = 1.0
            else:
                pts = 0.0

            weighted_points += pts * weights[i]
            total_weight += weights[i]

        if total_weight == 0:
            return 50.0

        # 归一化到0-100
        # 最高分 = 3分/场 * 权重和 = 3 * sum(weights) / sum(weights) = 3
        # 所以要 / 3 * 100
        avg_points = weighted_points / total_weight
        return (avg_points / 3.0) * 100

    def form_momentum(self, team: str, games: int = 5) -> float:
        """
        计算球队状态动量 (momentum)

        正数 = 越来越好
        负数 = 越来越差
        0 = 持平

        算法：比较最近games场 vs 之前games场的表现
        """
        all_matches = self.form.get(team, {"matches": []}).get("matches", [])

        if len(all_matches) < games * 2:
            return 0.0  # 数据不足

        # 最近games场
        recent = all_matches[-games:]
        # 之前games场
        previous = all_matches[-games*2:-games]

        def calc_pts(matches):
            return sum(3 if m.get("result") == "W" else (1 if m.get("result") == "D" else 0) for m in matches)

        recent_pts = calc_pts(recent)
        previous_pts = calc_pts(previous)

        # 转换为百分比
        recent_avg = (recent_pts / (games * 3)) * 100
        previous_avg = (previous_pts / (games * 3)) * 100

        return recent_avg - previous_avg  # 动量差值

    def form_streak(self, team: str) -> dict:
        """
        获取球队当前连胜/连败状态

        Returns:
            {"type": "W"|"L"|"D"|"none", "count": N, "description": "..."}
        """
        matches = self.form.get(team, {"matches": []}).get("matches", [])

        if not matches:
            return {"type": "none", "count": 0, "description": "无数据"}

        # 从最近一场开始往前数
        current_result = matches[-1].get("result", "D")
        streak_count = 1

        for i in range(len(matches) - 2, -1, -1):
            if matches[i].get("result") == current_result:
                streak_count += 1
            else:
                break

        type_map = {"W": "连胜", "D": "连平", "L": "连败"}
        desc_map = {"W": "连胜中", "D": "连平中", "L": "连败中"}

        return {
            "type": current_result,
            "count": streak_count,
            "description": f"{desc_map.get(current_result, '未知')} ({streak_count}场)"
        }

    def add_result(self, team: str, opponent: str, goals_for: int, goals_against: int,
                   is_home: bool = True, competition: str = "International"):
        """添加比赛结果"""
        if team not in self.form:
            self.form[team] = {"matches": [], "total_wins": 0, "total_draws": 0, "total_losses": 0}

        if goals_for > goals_against:
            result = "W"
        elif goals_for < goals_against:
            result = "L"
        else:
            result = "D"

        match = {
            "date": datetime.now().isoformat(),
            "opponent": opponent,
            "gf": goals_for,
            "ga": goals_against,
            "result": result,
            "is_home": is_home,
            "competition": competition,
        }
        self.form[team]["matches"].append(match)

        # 只保留最近20场
        self.form[team]["matches"] = self.form[team]["matches"][-20:]

    def save(self):
        """保存近期战绩"""
        with open(RECENT_FORM_FILE, "w") as f:
            json.dump({"form": self.form, "updated_at": datetime.now().isoformat()}, f, indent=2)


# ============ 历史对战系统 ============
class HeadToHead:
    """历史对战记录"""

    def __init__(self):
        self.records = self._load_records()

    def _load_records(self) -> dict:
        """加载历史对战记录"""
        if os.path.exists(H2H_FILE):
            with open(H2H_FILE) as f:
                data = json.load(f)
                return data.get("records", {})
        return self._default_h2h()

    def _default_h2h(self) -> dict:
        """默认H2H数据（基于真实足球历史）"""
        return {
            ("France", "Germany"): {"games": 12, "wins_a": 5, "draws": 3, "wins_b": 4, "gf_a": 18, "ga_a": 15},
            ("France", "England"): {"games": 15, "wins_a": 7, "draws": 6, "wins_b": 2, "gf_a": 22, "ga_a": 15},
            ("France", "Spain"): {"games": 10, "wins_a": 4, "draws": 2, "wins_b": 4, "gf_a": 14, "ga_a": 14},
            ("Brazil", "Germany"): {"games": 9, "wins_a": 4, "draws": 1, "wins_b": 4, "gf_a": 15, "ga_a": 14},
            ("Brazil", "Argentina"): {"games": 22, "wins_a": 7, "draws": 8, "wins_b": 7, "gf_a": 28, "ga_a": 27},
            ("Spain", "Germany"): {"games": 11, "wins_a": 4, "draws": 3, "wins_b": 4, "gf_a": 14, "ga_a": 12},
            ("Spain", "France"): {"games": 10, "wins_a": 4, "draws": 2, "wins_b": 4, "gf_a": 14, "ga_a": 14},
            ("Argentina", "Brazil"): {"games": 22, "wins_a": 7, "draws": 8, "wins_b": 7, "gf_a": 27, "ga_a": 28},
            ("England", "Germany"): {"games": 16, "wins_a": 5, "draws": 5, "wins_b": 6, "gf_a": 22, "ga_a": 24},
            ("England", "France"): {"games": 15, "wins_a": 2, "draws": 6, "wins_b": 7, "gf_a": 15, "ga_a": 22},
            ("Germany", "Italy"): {"games": 14, "wins_a": 5, "draws": 5, "wins_b": 4, "gf_a": 18, "ga_a": 17},
            ("Portugal", "Spain"): {"games": 15, "wins_a": 4, "draws": 5, "wins_b": 6, "gf_a": 18, "ga_a": 20},
            ("Netherlands", "Germany"): {"games": 20, "wins_a": 7, "draws": 5, "wins_b": 8, "gf_a": 30, "ga_a": 32},
            ("Italy", "Germany"): {"games": 14, "wins_a": 4, "draws": 5, "wins_b": 5, "gf_a": 17, "ga_a": 18},
            ("Morocco", "Spain"): {"games": 5, "wins_a": 1, "draws": 2, "wins_b": 2, "gf_a": 4, "ga_a": 6},
            ("Morocco", "Portugal"): {"games": 3, "wins_a": 1, "draws": 1, "wins_b": 1, "gf_a": 3, "ga_a": 3},
            ("Uruguay", "Brazil"): {"games": 18, "wins_a": 7, "draws": 4, "wins_b": 7, "gf_a": 22, "ga_a": 23},
            ("Croatia", "England"): {"games": 5, "wins_a": 2, "draws": 2, "wins_b": 1, "gf_a": 6, "ga_a": 5},
            ("Japan", "Korea South"): {"games": 28, "wins_a": 8, "draws": 8, "wins_b": 12, "gf_a": 35, "ga_a": 45},
            ("Korea South", "Japan"): {"games": 28, "wins_a": 12, "draws": 8, "wins_b": 8, "gf_a": 45, "ga_a": 35},
        }

    def get_h2h(self, team_a: str, team_b: str) -> dict:
        """获取两队历史对战记录"""
        # 尝试正序和反序
        key = (team_a, team_b)
        if key in self.records:
            rec = self.records[key]
            return {
                "games": rec["games"],
                "wins_a": rec["wins_a"],
                "wins_b": rec["wins_b"],
                "draws": rec["draws"],
                "gf_a": rec["gf_a"],
                "ga_a": rec["ga_a"],
                "team_a": team_a,
                "team_b": team_b,
            }

        # 反序
        key_rev = (team_b, team_a)
        if key_rev in self.records:
            rec = self.records[key_rev]
            return {
                "games": rec["games"],
                "wins_a": rec["wins_b"],
                "wins_b": rec["wins_a"],
                "draws": rec["draws"],
                "gf_a": rec["ga_a"],
                "ga_a": rec["gf_a"],
                "team_a": team_a,
                "team_b": team_b,
            }

        return None

    def h2h_advantage(self, team_a: str, team_b: str) -> float:
        """计算H2H优势指数 (-1 到 +1, 正数对A有利)"""
        h2h = self.get_h2h(team_a, team_b)
        if h2h is None or h2h["games"] < 3:
            return 0.0  # 数据不足返回中性

        total_games = h2h["games"]
        win_rate_a = h2h["wins_a"] / total_games
        expected_win_rate = 0.33  # 假设实力相等

        # 考虑比赛场次的权重
        weight = min(h2h["games"] / 10, 1.0)  # 最多10场完整权重
        return (win_rate_a - expected_win_rate) * weight

    def save(self):
        """保存H2H记录"""
        with open(H2H_FILE, "w") as f:
            json.dump({"records": self.records, "updated_at": datetime.now().isoformat()}, f, indent=2)


# ============ 球队综合评分 ============
class TeamRating:
    """球队综合评分（多维度融合）"""

    def __init__(self):
        self.elo = EloSystem()
        self.fifa = FIFARanking()
        self.form = RecentForm()
        self.h2h = HeadToHead()

    def get_team_strength(self, team: str,
                          elo_weight: float = 0.40,
                          fifa_weight: float = 0.20,
                          form_weight: float = 0.25,
                          experience_weight: float = 0.15) -> float:
        """
        计算球队综合实力评分 (0-100)

        权重分布：
        - Elo评分: 40% (客观实力)
        - FIFA排名: 20% (官方认可)
        - 近期状态: 25% (当前状态)
        - 大赛经验: 15% (历史底蕴)
        """
        elo_score = self._elo_to_score(self.elo.get_rating(team))
        fifa_score = self._fifa_to_score(self.fifa.get_rank(team))
        form_score = self.form.form_rating(team)
        experience_score = self._experience_score(team)

        total = (elo_score * elo_weight +
                  fifa_score * fifa_weight +
                  form_score * form_weight +
                  experience_score * experience_weight)

        return round(total, 2)

    def _elo_to_score(self, elo: float) -> float:
        """Elo转0-100评分"""
        # 1400 Elo = 30分, 2000 Elo = 100分
        return max(0, min(100, (elo - 1400) / 6))

    def _fifa_to_score(self, rank: int) -> float:
        """FIFA排名转0-100评分"""
        # 第1名 = 100分, 第100名 = 50分
        return max(50, 105 - rank)

    def _experience_score(self, team: str) -> float:
        """大赛经验评分"""
        # 世界杯冠军/四强次数（历史数据）
        experience_map = {
            "Brazil": 95, "Germany": 92, "Italy": 90, "Argentina": 88,
            "France": 85, "England": 78, "Spain": 75, "Uruguay": 72,
            "Netherlands": 70, "Portugal": 68, "Croatia": 55, "Morocco": 50,
            "Belgium": 52, "Colombia": 48, "Mexico": 50, "USA": 45,
            "Japan": 42, "Senegal": 35, "Poland": 45, "Switzerland": 40,
            "Chile": 42, "Austria": 40, "Ukraine": 30, "Australia": 35,
            "Serbia": 38, "Egypt": 35, "Paraguay": 48, "Nigeria": 38,
            "Ecuador": 35, "Ivory Coast": 30, "Algeria": 32, "Ghana": 38,
            "Qatar": 25, "Iraq": 28, "Jordan": 20, "Panama": 22,
            "Saudi Arabia": 38, "Cameroon": 42, "Tunisia": 35, "Bosnia": 20,
            "Scotland": 30, "Iran": 30, "Norway": 25, "New Zealand": 18,
            "Uzbekistan": 18, "South Africa": 30, "South Korea": 45,
            "Canada": 25, "Turkey": 42, "Hungary": 38, "Czech Republic": 40,
            "Denmark": 35, "Costa Rica": 32, "Jamaica": 15, "Wales": 35,
        }
        return experience_map.get(team, 25)

    def compare_teams(self, team_a: str, team_b: str,
                      h2h_bonus: bool = True) -> dict:
        """对比两队实力，返回详细对比"""
        strength_a = self.get_team_strength(team_a)
        strength_b = self.get_team_strength(team_b)

        # H2H调整
        h2h_adj = 0.0
        h2h_factor = ""
        if h2h_bonus:
            h2h_adv = self.h2h.h2h_advantage(team_a, team_b)
            h2h_adj = h2h_adv * 5  # 最多±5分
            h2h_factor = f"{'+' if h2h_adv >= 0 else ''}{h2h_adv*100:.1f}%"

        adjusted_a = strength_a + h2h_adj
        adjusted_b = strength_b - h2h_adj

        # 胜率计算
        total = adjusted_a + adjusted_b
        prob_a = adjusted_a / total if total > 0 else 0.5
        prob_b = 1 - prob_a

        return {
            "team_a": team_a,
            "team_b": team_b,
            "strength_a": strength_a,
            "strength_b": strength_b,
            "h2h_adjustment": h2h_adj,
            "adjusted_a": adjusted_a,
            "adjusted_b": adjusted_b,
            "win_prob_a": round(prob_a, 4),
            "win_prob_b": round(prob_b, 4),
            "h2h_factor": h2h_factor,
            "confidence": self._confidence_level(abs(adjusted_a - adjusted_b)),
        }

    def _confidence_level(self, diff: float) -> str:
        """置信度等级"""
        if diff >= 20:
            return "🟢 高信心"
        elif diff >= 10:
            return "🟡 中信心"
        else:
            return "🔴 低信心"

    def save_all(self):
        """保存所有数据"""
        self.elo.save()
        self.fifa.save()
        self.form.save()
        self.h2h.save()


# ============ 主程序 ============
if __name__ == "__main__":
    tr = TeamRating()

    print("=" * 60)
    print("🏆 球队综合实力评分系统")
    print("=" * 60)

    # 测试顶级对决
    teams_to_test = [
        ("France", "Germany"),
        ("Spain", "Brazil"),
        ("Argentina", "England"),
        ("France", "England"),
        ("Japan", "Korea South"),
    ]

    for team_a, team_b in teams_to_test:
        result = tr.compare_teams(team_a, team_b)
        print(f"\n⚽ {result['team_a']} vs {result['team_b']}")
        print(f"   实力评分: {result['strength_a']:.1f} vs {result['strength_b']:.1f}")
        if result['h2h_factor']:
            print(f"   H2H调整: {result['h2h_factor']}")
        print(f"   胜率: {result['win_prob_a']*100:.1f}% vs {result['win_prob_b']*100:.1f}%")
        print(f"   置信度: {result['confidence']}")

    print("\n" + "=" * 60)
    print("✅ 球队评分系统测试完成")
