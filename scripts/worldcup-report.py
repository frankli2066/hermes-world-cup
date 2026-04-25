#!/usr/bin/env python3
"""
世界杯完整分析报告 v3.4

生成完整的世界杯分析报告，包含：
1. 夺冠热门分析
2. 各小组形势
3. 淘汰赛路径分析
4. 关键球员影响
5. 价值投注建议

使用方法：
    python3 worldcup-report.py
"""

import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "core"))

from core.prediction_engine import PredictionEngine
from core.elo_calibrator import EloCalibrator, simulate_champion_probs
from core.data_pipeline import DataPipeline


def print_header(text: str):
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)


def analyze_championship():
    """生成完整的世界杯分析报告"""
    
    print()
    print("╔" + "═" * 68 + "╗")
    print("║" + "🏆 2026 世界杯完整分析报告 v3.4".center(68) + "║")
    print("║" + f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}".center(68) + "║")
    print("╚" + "═" * 68 + "╝")
    
    # 初始化
    print("\n🚀 初始化预测引擎...")
    engine = PredictionEngine(use_live_data=True)
    engine.calibrate_elo(learning_rate=0.3)
    
    pm_data = engine.pipeline.fetch_polymarket_champion_odds()
    teams_pm = {t["team"]: t["yes_price"] for t in pm_data.get("teams", [])}
    
    elo_dict = engine.team_stats.elo.ratings.copy()
    
    # 1. 夺冠热门分析
    print_header("📊 夺冠热门分析")
    
    sim_probs = simulate_champion_probs(elo_dict, monte_carlo=5000)
    
    # 按市场赔率排序
    sorted_teams = sorted(teams_pm.items(), key=lambda x: x[1], reverse=True)[:12]
    
    print(f"\n{'排名':>4} {'球队':<18} {'Elo':>8} {'市场赔率':>10} {'模型模拟':>10} {'评估':>8}")
    print("-" * 70)
    
    for i, (team, pm_prob) in enumerate(sorted_teams, 1):
        elo = elo_dict.get(team, 1500)
        sim_prob = sim_probs.get(team, 0)
        
        bias = (sim_prob / pm_prob - 1) * 100 if pm_prob > 0 else 0
        if bias > 30:
            assessment = "高估"
        elif bias < -30:
            assessment = "低估"
        else:
            assessment = "正常"
        
        print(f"{i:>4} {team:<18} {elo:>8.0f} "
              f"{pm_prob*100:>9.2f}% {sim_prob*100:>9.2f}% {assessment:>8}")
    
    # 2. 小组形势分析
    print_header("📋 小组形势分析")
    
    from quick_group_simulator_v341 import simulate_group_ranking, GROUPS
    
    for group_name, teams in sorted(GROUPS.items()):
        print(f"\n🏌️ 组 {group_name}: {', '.join(teams)}")
        
        results = simulate_group_ranking(teams, elo_dict, monte_carlo=1000)
        
        sorted_results = sorted(results.items(), 
                              key=lambda x: x[1]["qualify_prob"], 
                              reverse=True)
        
        for team, stats in sorted_results:
            symbol = "✅" if stats["qualify_prob"] > 50 else "❌"
            bar_len = int(stats["qualify_prob"] / 5)
            bar = "█" * bar_len
            print(f"   {symbol} {team:<15} {bar:<20} {stats['qualify_prob']:>5.1f}%  "
                  f"均分:{stats['avg_points']:.1f}pt")
    
    # 3. 淘汰赛关键对阵
    print_header("⚔️ 淘汰赛关键对阵")
    
    knockout_matches = [
        ("Brazil", "Portugal"),
        ("Spain", "France"),
        ("Argentina", "England"),
        ("Germany", "Brazil"),
    ]
    
    print(f"\n{'主队':<15} {'客队':<15} {'主胜':>8} {'平局':>8} {'客胜':>8} {'推荐':<10}")
    print("-" * 70)
    
    for home, away in knockout_matches:
        result = engine.predict_match(home, away, monte_carlo=5000)
        
        home_prob = result["win_probability"]["home"] * 100
        draw_prob = result["win_probability"]["draw"] * 100
        away_prob = result["win_probability"]["away"] * 100
        
        # 推荐
        if home_prob > draw_prob + 10 and home_prob > away_prob + 5:
            rec = f"主胜 {home_prob:.0f}%"
        elif away_prob > home_prob + 10 and away_prob > draw_prob + 5:
            rec = f"客胜 {away_prob:.0f}%"
        elif abs(home_prob - away_prob) < 10:
            rec = "谨慎投注"
        else:
            rec = f"平局 {draw_prob:.0f}%"
        
        print(f"{home:<15} {away:<15} {home_prob:>7.1f}% {draw_prob:>7.1f}% "
              f"{away_prob:>7.1f}% {rec:<10}")
    
    # 4. 球员影响分析
    print_header("👥 球员影响分析")
    
    key_players = [
        ("Kylian Mbappe", "France"),
        ("Harry Kane", "England"),
        ("Vinicius Jr", "Brazil"),
        ("Erling Haaland", "Norway"),
    ]
    
    for player, team in key_players:
        print(f"\n⚠️  {player} ({team}) 缺阵影响:")
        
        # 找替补对手
        opponents = {
            "France": ("Germany", []),
            "England": ("USA", []),
            "Brazil": ("Switzerland", []),
            "Norway": ("Spain", []),
        }
        
        if team in opponents:
            opponent, missing = opponents[team]
            result_full = engine.predict_match(team, opponent, monte_carlo=2000)
            result_miss = engine.predict_match(team, opponent, monte_carlo=2000, 
                                            home_missing=[player] if team == opponent else [],
                                            away_missing=[player] if opponent == team else [])
            
            full_prob = result_full["win_probability"]["home"] if team == opponent else result_full["win_probability"]["away"]
            miss_prob = result_miss["win_probability"]["home"] if team == opponent else result_miss["win_probability"]["away"]
            
            impact = abs(full_prob - miss_prob) * 100
            
            print(f"   {team} 完整阵容 vs {opponent}: {full_prob*100:.1f}%")
            print(f"   {team} 缺少{player}: {miss_prob*100:.1f}%")
            print(f"   影响: -{impact:.1f}%")
    
    # 5. 价值投注建议
    print_header("💰 价值投注建议")
    
    print("\n基于模型 vs 市场赔率对比，以下球队可能被低估：")
    
    undervalued = []
    for team, pm_prob in teams_pm.items():
        if pm_prob < 0.02:  # 只看低于2%的
            sim_prob = sim_probs.get(team, 0)
            if sim_prob > pm_prob * 1.5:  # 模型比市场高50%以上
                undervalued.append((team, pm_prob, sim_prob))
    
    undervalued.sort(key=lambda x: x[2] - x[1], reverse=True)
    
    for team, pm_prob, sim_prob in undervalued[:5]:
        expected_value = (sim_prob - pm_prob) * 100
        print(f"   🟢 {team:<15} 市场:{pm_prob*100:>5.2f}% → 模型:{sim_prob*100:>5.2f}%  "
              f"预期价值:+{expected_value:.2f}%")
    
    # 6. 决赛预测
    print_header("🏆 决赛预测")
    
    final_candidates = ["Spain", "France", "Brazil", "Argentina", "England", "Germany"]
    
    print(f"\n{'球队A':<12} {'球队B':<12} {'A胜':>8} {'平局':>8} {'B胜':>8}")
    print("-" * 55)
    
    for i, team_a in enumerate(final_candidates[:3]):
        for team_b in final_candidates[i+1:i+3]:
            result = engine.predict_match(team_a, team_b, monte_carlo=3000)
            
            home_prob = result["win_probability"]["home"] * 100
            draw_prob = result["win_probability"]["draw"] * 100
            away_prob = result["win_probability"]["away"] * 100
            
            if result["predicted_score"] == f"{team_a}-{team_b}":
                print(f"{team_a:<12} {team_b:<12} {home_prob:>7.1f}% {draw_prob:>7.1f}% {away_prob:>7.1f}%")
            else:
                print(f"{team_b:<12} {team_a:<12} {away_prob:>7.1f}% {draw_prob:>7.1f}% {home_prob:>7.1f}%")
    
    # 结束
    print()
    print("=" * 70)
    print("  ✅ 报告生成完毕")
    print("=" * 70)
    print()


if __name__ == "__main__":
    analyze_championship()
