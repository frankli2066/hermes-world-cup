#!/usr/bin/env python3
"""
小组赛快速模拟器 v3.4.1

优化版小组赛模拟：
- 直接使用校准后的Elo + xG模型
- 正确的积分系统和排名规则
- 避免之前的100%晋级率bug

使用方法：
    python3 quick-group-simulator.py
"""

import random
import math
from collections import defaultdict
from typing import Dict, List, Tuple

# 小组分组
GROUPS = {
    "A": ["Qatar", "Ecuador", "Senegal", "Netherlands"],
    "B": ["England", "Iran", "USA", "Wales"],
    "C": ["Argentina", "Saudi Arabia", "Mexico", "Poland"],
    "D": ["France", "Australia", "Denmark", "Tunisia"],
    "E": ["Spain", "Costa Rica", "Germany", "Japan"],
    "F": ["Belgium", "Canada", "Morocco", "Croatia"],
    "G": ["Brazil", "Serbia", "Switzerland", "Cameroon"],
    "H": ["Portugal", "Ghana", "Uruguay", "South Korea"],
}


def elo_win_prob(elo_a: float, elo_b: float, home_adv: float = 50) -> Tuple[float, float, float]:
    """
    用Elo计算胜平负概率
    
    Returns:
        (胜率, 平率, 负率)
    """
    diff = elo_a + home_adv - elo_b
    
    # S型曲线
    prob_a = 1 / (1 + 10 ** (-diff / 400))
    prob_b = 1 - prob_a
    
    # 平局概率（差距越大，平局越少）
    if abs(diff) > 150:
        draw_prob = 0.18
    elif abs(diff) > 80:
        draw_prob = 0.22
    elif abs(diff) > 40:
        draw_prob = 0.25
    else:
        draw_prob = 0.28
    
    # 调整
    home_win = prob_a * (1 - draw_prob * 0.4)
    away_win = prob_b * (1 - draw_prob * 0.4)
    
    return (home_win, draw_prob, away_win)


def poisson_goals(expected: float) -> int:
    """泊松分布生成进球数"""
    # 使用反函数法简化
    L = math.exp(-expected)
    k = 0
    p = 1.0
    while p > L:
        k += 1
        p *= random.random()
    return k - 1


def simulate_match(home_elo: float, away_elo: float) -> Tuple[int, int]:
    """
    模拟单场比赛，返回进球数
    
    Returns:
        (主队进球, 客队进球)
    """
    home_win, draw_prob, away_win = elo_win_prob(home_elo, away_elo, home_adv=50)
    
    # 基础xG（主客场调整）
    base_xg_home = 1.4
    base_xg_away = 1.0
    
    # Elo差距影响xG
    elo_diff = (home_elo - away_elo) / 100
    home_xg = base_xg_home + elo_diff * 0.1
    away_xg = base_xg_away - elo_diff * 0.1
    
    # 限制范围
    home_xg = max(0.3, min(3.0, home_xg))
    away_xg = max(0.2, min(2.5, away_xg))
    
    # 生成进球
    home_goals = poisson_goals(home_xg)
    away_goals = poisson_goals(away_xg)
    
    return (home_goals, away_goals)


def simulate_group_ranking(teams: List[str], elo_dict: Dict[str, float],
                          monte_carlo: int = 2000) -> Dict:
    """
    模拟小组赛排名
    
    Args:
        teams: 4支队伍的列表
        elo_dict: {team: elo} 字典
        monte_carlo: 模拟次数
    
    Returns:
        各队晋级概率
    """
    qualify_counts = defaultdict(int)
    points_totals = defaultdict(float)
    goals_for_totals = defaultdict(float)
    goals_against_totals = defaultdict(float)
    
    # 对阵顺序
    matches = [
        (0, 1),  # 队0 vs 队1
        (2, 3),  # 队2 vs 队3
        (0, 2),  # 队0 vs 队2
        (1, 3),  # 队1 vs 队3
        (0, 3),  # 队0 vs 队3
        (1, 2),  # 队1 vs 队2
    ]
    
    for _ in range(monte_carlo):
        # 每队积分和进球
        team_points = defaultdict(int)
        team_gf = defaultdict(int)
        team_ga = defaultdict(int)
        
        # 6场比赛
        for home_idx, away_idx in matches:
            home_team = teams[home_idx]
            away_team = teams[away_idx]
            
            home_elo = elo_dict.get(home_team, 1500)
            away_elo = elo_dict.get(away_team, 1500)
            
            home_goals, away_goals = simulate_match(home_elo, away_elo)
            
            team_gf[home_team] += home_goals
            team_ga[home_team] += away_goals
            team_gf[away_team] += away_goals
            team_ga[away_team] += home_goals
            
            if home_goals > away_goals:
                team_points[home_team] += 3
            elif away_goals > home_goals:
                team_points[away_team] += 3
            else:
                team_points[home_team] += 1
                team_points[away_team] += 1
        
        # 排名（积分相同看净胜球，再看进球）
        sorted_teams = sorted(teams, key=lambda t: (
            team_points[t],
            team_gf[t] - team_ga[t],
            team_gf[t]
        ), reverse=True)
        
        # 统计前2名
        for i, team in enumerate(sorted_teams):
            if i < 2:
                qualify_counts[team] += 1
            points_totals[team] += team_points[team]
            goals_for_totals[team] += team_gf[team]
            goals_against_totals[team] += team_ga[team]
    
    n = monte_carlo
    results = {}
    for team in teams:
        results[team] = {
            "qualify_prob": qualify_counts[team] / n * 100,
            "avg_points": points_totals[team] / n,
            "avg_gf": goals_for_totals[team] / n,
            "avg_ga": goals_against_totals[team] / n,
            "avg_gd": (goals_for_totals[team] - goals_against_totals[team]) / n,
        }
    
    return results


def run_quick_simulation(elo_dict: Dict[str, float], monte_carlo: int = 2000) -> Dict:
    """
    运行完整的小组赛模拟
    """
    all_results = {}
    
    print("=" * 70)
    print(f"🏆 世界杯小组赛快速模拟 (每组 {monte_carlo} 次)")
    print("=" * 70)
    
    for group_name, teams in sorted(GROUPS.items()):
        print(f"\n📊 组 {group_name}: {', '.join(teams)}")
        
        results = simulate_group_ranking(teams, elo_dict, monte_carlo)
        
        # 按晋级概率排序
        sorted_teams = sorted(results.items(), 
                             key=lambda x: x[1]["qualify_prob"], 
                             reverse=True)
        
        for team, stats in sorted_teams:
            qual_symbol = "✅" if stats["qualify_prob"] > 50 else "❌"
            print(f"   {qual_symbol} {team:<15} 晋级:{stats['qualify_prob']:>5.1f}%  "
                  f"均分:{stats['avg_points']:.1f}pt  "
                  f"进球:{stats['avg_gf']:.1f}  "
                  f"净胜:{stats['avg_gd']:+.1f}")
        
        all_results[group_name] = results
    
    return all_results


# ============ 主程序 ============

if __name__ == "__main__":
    import sys
    import os
    
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "core"))
    
    from core.team_stats import EloSystem
    from core.elo_calibrator import EloCalibrator
    from core.data_pipeline import DataPipeline
    
    print("\n🚀 小组赛快速模拟开始...\n")
    
    # 加载并校准Elo
    elo_system = EloSystem()
    
    pipeline = DataPipeline()
    pm_data = pipeline.fetch_polymarket_champion_odds()
    
    if pm_data and pm_data.get("teams"):
        print("🔧 正在用Polymarket校准Elo...")
        calibrator = EloCalibrator(elo_system, pm_data)
        calibrator.calibrate(learning_rate=0.3)
        calibrator.apply_calibration()
    
    elo_dict = elo_system.ratings.copy()
    
    results = run_quick_simulation(elo_dict, monte_carlo=2000)
    
    print("\n" + "=" * 70)
    print("✅ 模拟完成!")
    print("=" * 70)
