#!/usr/bin/env python3
"""
赛前分析脚本 v3.4

快速输出比赛预测，包含：
- 胜平负概率
- 比分预测
- 关键球员缺阵
- 比赛阶段调整
- Elo校准信息

使用方法：
    python3 pre-match-analysis.py "Brazil" "France"
    python3 pre-match-analysis.py "Spain" "Argentina" --stage final
    python3 pre-match-analysis.py "Germany" "France" --missing "Kylian Mbappe"
"""

import sys
import os
import argparse

# 添加core模块路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "core"))

from prediction_engine import PredictionEngine


def print_banner(text: str):
    """打印标题"""
    print()
    print("=" * 60)
    print(f"  {text}")
    print("=" * 60)


def print_team_info(engine: PredictionEngine, team: str):
    """打印球队信息"""
    elo = engine.team_stats.elo.get_rating(team)
    strength = engine.team_stats.get_team_strength(team)
    fifa_rank = engine.team_stats.fifa.get_rank(team)

    print(f"  🏆 FIFA排名: #{fifa_rank}")
    print(f"  📊 Elo评分: {elo:.0f}")
    print(f"  💪 实力评分: {strength:.1f}/100")


def analyze_match(
    home_team: str,
    away_team: str,
    stage: str = "group",
    home_missing: list = None,
    away_missing: list = None,
    calibrate_elo: bool = True,
):
    """
    分析比赛并输出结果
    """
    # 初始化引擎
    engine = PredictionEngine(use_live_data=True)

    # Elo校准
    if calibrate_elo:
        engine.calibrate_elo(learning_rate=0.3)

    print_banner(f"⚽ 赛前分析: {home_team} vs {away_team}")

    # 比赛阶段
    stage_names = {
        "group": "小组赛",
        "round_of_16": "16强",
        "quarter": "8强",
        "semi": "半决赛",
        "third_place": "三四名决赛",
        "final": "决赛",
    }
    print(f"\n📅 比赛阶段: {stage_names.get(stage, stage)}")

    # 球队信息
    print(f"\n🏠 主队: {home_team}")
    print_team_info(engine, home_team)

    if home_missing:
        print(f"  ⚠️ 缺阵: {', '.join(home_missing)}")

    print(f"\n✈️ 客队: {away_team}")
    print_team_info(engine, away_team)

    if away_missing:
        print(f"  ⚠️ 缺阵: {', '.join(away_missing)}")

    # 执行预测
    print_banner("📈 预测结果")

    result = engine.predict_match(
        home_team,
        away_team,
        monte_carlo=10000,
        match_stage=stage,
        home_missing=home_missing,
        away_missing=away_missing,
    )

    # 胜平负
    home_win = result["win_probability"]["home"] * 100
    draw = result["win_probability"]["draw"] * 100
    away_win = result["win_probability"]["away"] * 100

    print(f"\n  {'胜率':>8}  {'平率':>8}  {'负率':>8}")
    print(f"  {home_win:>7.1f}%  {draw:>7.1f}%  {away_win:>7.1f}%")
    print()

    # 可视化条形图
    max_bar = 40
    home_bar = int(home_win / 100 * max_bar)
    draw_bar = int(draw / 100 * max_bar)
    away_bar = int(away_win / 100 * max_bar)

    print(f"  {home_team[:10]:<10} {'█' * home_bar} {home_win:.1f}%")
    print(f"  {'平局':<10} {'█' * draw_bar} {draw:.1f}%")
    print(f"  {away_team[:10]:<10} {'█' * away_bar} {away_win:.1f}%")

    # 比分预测
    print(f"\n  🎯 预测比分: {result['predicted_score']}")
    print(f"  📊 预测总进球: {result.get('expected_total_goals', 'N/A')}")

    # 球员影响
    if result.get("player_impact"):
        pi = result["player_impact"]
        print(f"\n  👥 球员影响:")
        if pi["home"]["impact_percent"] > 0:
            print(f"    {home_team}: -{pi['home']['impact_percent']:.1f}%")
            for p in pi["home"].get("missing_players", []):
                print(f"      - {p['name']} ({p['position']})")
        if pi["away"]["impact_percent"] > 0:
            print(f"    {away_team}: -{pi['away']['impact_percent']:.1f}%")
            for p in pi["away"].get("missing_players", []):
                print(f"      - {p['name']} ({p['position']})")

    # 推荐
    print(f"\n  💡 推荐: {result['recommendation']} ({result['confidence']})")

    # 融合来源
    fusion = result.get("odds_fusion", {})
    print(f"\n  📡 数据来源: {fusion.get('source', 'N/A')}")

    # xG信息
    xg = result.get("xg_prediction", {})
    if xg:
        print(f"\n  ⚽ 预期进球 (xG):")
        print(f"    {home_team}: {xg.get('home_xg', 'N/A'):.2f}")
        print(f"    {away_team}: {xg.get('away_xg', 'N/A'):.2f}")

    print()


def main():
    parser = argparse.ArgumentParser(description="世界杯赛前分析")
    parser.add_argument("home_team", help="主队")
    parser.add_argument("away_team", help="客队")
    parser.add_argument("--stage", "-s", default="group",
                       choices=["group", "round_of_16", "quarter", "semi", "third_place", "final"],
                       help="比赛阶段")
    parser.add_argument("--home-missing", nargs="+", help="主队缺阵球员")
    parser.add_argument("--away-missing", nargs="+", help="客队缺阵球员")
    parser.add_argument("--no-calibrate", action="store_true", help="跳过Elo校准")

    args = parser.parse_args()

    analyze_match(
        args.home_team,
        args.away_team,
        stage=args.stage,
        home_missing=args.home_missing,
        away_missing=args.away_missing,
        calibrate_elo=not args.no_calibrate,
    )


if __name__ == "__main__":
    main()
