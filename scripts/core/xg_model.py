#!/usr/bin/env python3
"""
xG预期进球模型 v6.0

增强版动态xG模型：
1. 动态调整因子：根据近期状态调整xG
2. 更好的主客场处理
3. Elo差距影响优化
4. 比赛阶段调整
"""

import numpy as np
import random
from typing import Tuple, Dict, Optional
import os
import json

np.random.seed(None)


# 球队基础xG数据（进攻和防守）
TEAM_ATTACK_BASE = {
    "Spain": 2.1, "France": 2.05, "Brazil": 2.0, "Argentina": 1.95,
    "England": 1.88, "Germany": 1.85, "Portugal": 1.82, "Netherlands": 1.78,
    "Italy": 1.75, "Belgium": 1.72, "Colombia": 1.68, "Uruguay": 1.65,
    "Croatia": 1.62, "Mexico": 1.58, "USA": 1.52, "Poland": 1.50,
    "Chile": 1.48, "Senegal": 1.46, "Morocco": 1.45, "Austria": 1.42,
    "Switzerland": 1.40, "Japan": 1.40, "Serbia": 1.38, "Egypt": 1.36,
    "Denmark": 1.38, "Sweden": 1.35, "Turkey": 1.35, "Wales": 1.30,
    "Paraguay": 1.32, "Ukraine": 1.28, "Australia": 1.28, "Nigeria": 1.25,
    "South Korea": 1.28, "Ecuador": 1.25, "Cameroon": 1.22, "Saudi Arabia": 1.18,
    "Algeria": 1.15, "Iran": 1.12, "Hungary": 1.20, "Ghana": 1.10,
    "Ivory Coast": 1.08, "Qatar": 1.05, "Tunisia": 1.05, "Panama": 0.98,
    # 2026世界杯新加入/需要数据的球队
    "Costa Rica": 1.05, "Canada": 1.15,
}

TEAM_DEFENSE_BASE = {
    "France": 0.65, "Spain": 0.70, "Italy": 0.72, "Argentina": 0.75,
    "Morocco": 0.78, "Brazil": 0.80, "Germany": 0.82, "England": 0.85,
    "Netherlands": 0.88, "Portugal": 0.90, "Belgium": 0.92, "Croatia": 0.92,
    "Uruguay": 0.94, "Switzerland": 0.95, "Austria": 0.98, "Poland": 1.0,
    "Mexico": 1.10, "USA": 1.10, "Colombia": 1.12, "Senegal": 1.14,
    "Chile": 1.18, "Japan": 1.10, "Serbia": 1.20, "Egypt": 1.22,
    "Denmark": 1.15, "Sweden": 1.22, "Turkey": 1.22, "Wales": 1.18,
    "Australia": 1.28, "South Korea": 1.25, "Nigeria": 1.35,
    "Ecuador": 1.32, "Saudi Arabia": 1.42, "Iran": 1.40, "Paraguay": 1.35,
    "Panama": 1.50, "Qatar": 1.45, "Tunisia": 1.45,
    # 2026世界杯新加入/需要数据的球队
    "Costa Rica": 1.35, "Canada": 1.25,
}

# 主场优势调整（根据不同联赛/大洲）
HOME_ADVANTAGE = {
    # 中北美
    "USA": 0.18, "Mexico": 0.15, "Costa Rica": 0.12, "Canada": 0.14, "Panama": 0.10,
    # 南美（高原主场优势大）
    "Ecuador": 0.25, "Bolivia": 0.28, "Colombia": 0.12,
    # 亚洲
    "Qatar": 0.08, "Japan": 0.10, "South Korea": 0.10, "Iran": 0.12, "Saudi Arabia": 0.08,
    # 欧洲
    "Spain": 0.12, "France": 0.13, "Germany": 0.12, "England": 0.13, "Italy": 0.12,
    "Portugal": 0.11, "Netherlands": 0.11, "Belgium": 0.11, "Poland": 0.10,
    "Croatia": 0.10, "Serbia": 0.11, "Switzerland": 0.10, "Denmark": 0.10,
    "Sweden": 0.10, "Austria": 0.10, "Wales": 0.10, "Ukraine": 0.10,
    # 非洲
    "Morocco": 0.10, "Senegal": 0.10, "Ghana": 0.10, "Nigeria": 0.10,
    "Cameroon": 0.10, "Ivory Coast": 0.10, "Algeria": 0.10, "Tunisia": 0.10,
    "Egypt": 0.10,
    # 大洋洲
    "Australia": 0.08,
    # 默认
    "default": 0.12,
}


class DynamicxGModel:
    """动态xG模型 v6.0"""
    
    def __init__(self):
        self.team_attack = TEAM_ATTACK_BASE.copy()
        self.team_defense = TEAM_DEFENSE_BASE.copy()
        
        # 动态调整因子（可以被外部更新）
        self.form_adjustment = {}  # {team: (attack_adj, defense_adj)}
        
        # 加载缓存的调整因子
        self._load_cached_adjustments()
    
    def _load_cached_adjustments(self):
        """加载缓存的动态调整因子"""
        cache_file = os.path.expanduser("~/hermes-world-cup/data/xg_adjustments.json")
        if os.path.exists(cache_file):
            try:
                with open(cache_file) as f:
                    data = json.load(f)
                    self.form_adjustment = data.get("form_adjustment", {})
            except:
                pass
    
    def save_adjustments(self):
        """保存调整因子到缓存"""
        cache_file = os.path.expanduser("~/hermes-world-cup/data/xg_adjustments.json")
        os.makedirs(os.path.dirname(cache_file), exist_ok=True)
        with open(cache_file, "w") as f:
            json.dump({"form_adjustment": self.form_adjustment}, f)
    
    def update_form(self, team: str, attack_adj: float, defense_adj: float):
        """
        更新球队状态调整因子
        
        Args:
            team: 球队名
            attack_adj: 进攻调整 (正值=状态好, 负值=状态差)
            defense_adj: 防守调整 (负值=状态好, 正值=状态差)
        """
        self.form_adjustment[team] = (attack_adj, defense_adj)
    
    def calculate_form_factor(self, team: str, is_home: bool) -> Tuple[float, float]:
        """
        计算基于状态的调整因子
        
        Returns:
            (attack_factor, defense_factor)
        """
        if team not in self.form_adjustment:
            return 1.0, 1.0
        
        attack_adj, defense_adj = self.form_adjustment[team]
        
        # 主场/客场调整
        if is_home:
            return 1.0 + attack_adj, 1.0 - defense_adj
        else:
            return 1.0 + attack_adj * 0.8, 1.0 - defense_adj * 0.8
    
    def get_home_advantage(self, team: str) -> float:
        """获取主场优势"""
        return HOME_ADVANTAGE.get(team, HOME_ADVANTAGE["default"])
    
    def calculate_match_xg(
        self, 
        home_team: str, 
        away_team: str,
        elo_diff: float = 0.0,
        home_form_adj: float = 0.0,
        away_form_adj: float = 0.0,
        neutral_venue: bool = False,
    ) -> Tuple[float, float]:
        """
        计算比赛xG（动态版）
        
        Args:
            home_team: 主队
            away_team: 客队
            elo_diff: Elo差距 (主队Elo - 客队Elo)
            home_form_adj: 主队状态调整 (-0.2 到 +0.2)
            away_form_adj: 客队状态调整 (-0.2 到 +0.2)
            neutral_venue: 是否是中立场地
        
        Returns:
            (home_xg, away_xg)
        """
        # 基础xG
        home_attack = self.team_attack.get(home_team, 1.0)
        away_defense = self.team_defense.get(away_team, 1.3)
        away_attack = self.team_attack.get(away_team, 1.0)
        home_defense = self.team_defense.get(home_team, 1.3)
        
        # 防守评分转换（低=好，转换为xG因子）
        away_defense_factor = max(0.4, min(1.4, 2.0 - away_defense))
        home_defense_factor = max(0.4, min(1.4, 2.0 - home_defense))
        
        # 状态调整
        home_form, away_form = 1.0, 1.0
        if home_form_adj != 0 or away_form_adj != 0:
            home_form = 1.0 + home_form_adj
            away_form = 1.0 + away_form_adj
        
        # 计算xG
        home_xg = home_attack * away_defense_factor * home_form
        away_xg = away_attack * home_defense_factor * away_form
        
        # 主场优势（除非是中立场）
        if not neutral_venue:
            home_adv = self.get_home_advantage(home_team)
            home_xg += home_adv
        
        # Elo差距调整（优化后的系数）
        if elo_diff != 0:
            elo_factor = elo_diff / 100 * 0.05
            home_xg += elo_factor
            away_xg -= elo_factor
        
        # 确保合理范围
        home_xg = max(0.25, min(4.0, round(home_xg, 2)))
        away_xg = max(0.20, min(3.5, round(away_xg, 2)))
        
        return home_xg, away_xg
    
    def poisson_sample(self, xg: float) -> int:
        """泊松分布采样"""
        return max(0, np.random.poisson(xg))
    
    def simulate_score(
        self, 
        home_team: str, 
        away_team: str,
        elo_diff: float = 0.0,
        stage: str = "group",
        monte_carlo: int = 10000,
        home_form_adj: float = 0.0,
        away_form_adj: float = 0.0,
        neutral_venue: bool = False,
    ) -> Dict:
        """
        蒙特卡洛模拟
        
        Args:
            home_team: 主队
            away_team: 客队
            elo_diff: Elo差距
            stage: 比赛阶段
            monte_carlo: 模拟次数
            home_form_adj: 主队状态调整
            away_form_adj: 客队状态调整
            neutral_venue: 是否是中立场地
        
        Returns:
            预测结果字典
        """
        home_xg, away_xg = self.calculate_match_xg(
            home_team, away_team, 
            elo_diff=elo_diff,
            home_form_adj=home_form_adj,
            away_form_adj=away_form_adj,
            neutral_venue=neutral_venue,
        )
        
        # 方差（比赛阶段调整）
        stage_variance = {
            "final": 1.05,
            "semi": 1.08,
            "quarter": 1.12,
            "round_of_16": 1.15,
            "round16": 1.15,
            "group": 1.20,
            "friendly": 1.30,
        }
        variance = stage_variance.get(stage, 1.15)
        
        # Elo差距大时增加方差（弱队可能爆冷）
        if abs(elo_diff) > 200:
            variance *= 1.08
        elif abs(elo_diff) > 100:
            variance *= 1.04
        
        # 蒙特卡洛模拟
        score_counts = {}
        home_wins, away_wins, draws = 0, 0, 0
        home_goals_list = []
        away_goals_list = []
        
        for _ in range(monte_carlo):
            adj_home = home_xg * variance
            adj_away = away_xg * variance
            
            h = self.poisson_sample(adj_home)
            a = self.poisson_sample(adj_away)
            
            score_counts[(h, a)] = score_counts.get((h, a), 0) + 1
            home_goals_list.append(h)
            away_goals_list.append(a)
            
            if h > a:
                home_wins += 1
            elif h < a:
                away_wins += 1
            else:
                draws += 1
        
        total = monte_carlo
        
        # 最可能比分
        most_likely = max(score_counts.items(), key=lambda x: x[1])
        ml_score = most_likely[0]
        ml_prob = most_likely[1] / total
        
        # 常见比分
        common = [(f"{h}-{a}", c/total) for (h, a), c in
                 sorted(score_counts.items(), key=lambda x: x[1], reverse=True)[:5]]
        
        # 最终比分预测（加权采样）
        top_scores = sorted(score_counts.items(), key=lambda x: x[1], reverse=True)[:8]
        scores = [s[0] for s in top_scores]
        weights = [s[1] ** 0.7 for s in top_scores]
        total_w = sum(weights)
        weights = [w/total_w for w in weights]
        pred = scores[np.random.choice(len(scores), p=weights)]
        
        # 预测总进球分布
        total_goals_dist = {}
        for (h, a), count in score_counts.items():
            tg = h + a
            total_goals_dist[tg] = total_goals_dist.get(tg, 0) + count
        
        # 计算平均进球
        avg_home_goals = sum(home_goals_list) / total
        avg_away_goals = sum(away_goals_list) / total
        
        return {
            "home_team": home_team,
            "away_team": away_team,
            "home_xg": home_xg,
            "away_xg": away_xg,
            "xg_diff": round(home_xg - away_xg, 2),  # 【优化4】xG差异分析 - 两队xG差距比单独xG更有预测价值
            "xg_ratio": round(home_xg / away_xg, 2) if away_xg > 0 else 1.0,  # xG比率
            "expected_total_goals": round(home_xg + away_xg, 2),
            "predicted_score": f"{pred[0]}-{pred[1]}",
            "most_likely_score": f"{ml_score[0]}-{ml_score[1]}",
            "most_likely_prob": round(ml_prob, 3),
            "prob_home_win": round(home_wins / total, 3),
            "prob_draw": round(draws / total, 3),
            "prob_away_win": round(away_wins / total, 3),
            "over_2_5_prob": round(sum(c for (h, a), c in score_counts.items() if h + a > 2.5) / total, 3),
            "under_2_5_prob": round(sum(c for (h, a), c in score_counts.items() if h + a <= 2.5) / total, 3),
            "btts_yes_prob": round(sum(c for (h, a), c in score_counts.items() if h > 0 and a > 0) / total, 3),
            "btts_no_prob": round(sum(c for (h, a), c in score_counts.items() if h == 0 or a == 0) / total, 3),
            "common_scores": common,
            "avg_home_goals": round(avg_home_goals, 2),
            "avg_away_goals": round(avg_away_goals, 2),
            "home_goals_distribution": {k: round(v/total, 3) for k, v in sorted(total_goals_dist.items()) if v/total > 0.01},
            "monte_carlo_runs": monte_carlo,
        }
    
    def quick_predict(self, home_team: str, away_team: str,
                     elo_diff: float = 0.0) -> Tuple[int, int]:
        """快速预测比分"""
        home_xg, away_xg = self.calculate_match_xg(home_team, away_team, elo_diff)
        return self.poisson_sample(home_xg), self.poisson_sample(away_xg)
    
    def add_missing_teams(self, teams_data: Dict[str, Tuple[float, float]]):
        """
        添加缺失球队的xG数据
        
        Args:
            teams_data: {team: (attack_xg, defense_xg)}
        """
        for team, (attack, defense) in teams_data.items():
            self.team_attack[team] = attack
            self.team_defense[team] = defense


# 兼容性：保留旧的类名
xGModel = DynamicxGModel


if __name__ == "__main__":
    xg = DynamicxGModel()
    
    # 测试
    print("=== xG v6.0 测试 ===\n")
    
    tests = [
        ("Brazil", "France", 0),
        ("Spain", "Germany", 50),
        ("Argentina", "Brazil", -62),
        ("USA", "Mexico", 0),
    ]
    
    for home, away, elo_diff in tests:
        r = xg.simulate_score(home, away, elo_diff=elo_diff, monte_carlo=5000)
        print(f"{home} vs {away} (Elo差={elo_diff:+d}):")
        print(f"  xG: {r['home_xg']:.2f} - {r['away_xg']:.2f}")
        print(f"  预测: {r['predicted_score']} | 最可能: {r['most_likely_score']} ({r['most_likely_prob']:.1%})")
        print(f"  胜平负: {r['prob_home_win']*100:.0f}% - {r['prob_draw']*100:.0f}% - {r['prob_away_win']*100:.0f}%")
        print(f"  大球: {r['over_2_5_prob']*100:.0f}%")
        print()
