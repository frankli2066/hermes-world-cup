#!/usr/bin/env python3
"""
2026世界杯 - 整合版淘汰赛模拟器 v3.0
整合了所有优化模块：
- 动态Elo评分系统
- xG预期进球模型
- H2H历史对战克星指数
- 多数据源融合
- 机器学习权重校准
"""

import json
import os
import random
import sys
from datetime import datetime
from collections import defaultdict

# 添加core模块路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "core"))

try:
    from prediction_engine import PredictionEngine, GroupStageSimulator, KnockoutSimulator
    from xg_model import xGModel
    from team_stats import TeamRating
    from ml_calibrator import Backtester
    USE_STANDALONE = False
except ImportError as e:
    print(f"⚠️ 核心模块导入失败: {e}")
    print("   使用独立模式运行...")
    USE_STANDALONE = True

# ============ 路径配置 ============
BASE_DIR = os.path.expanduser("~/hermes-world-cup/")
OUTPUT_DIR = os.path.join(BASE_DIR, "knockout/")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ============ 2026世界杯分组 ============
GROUPS = {
    "A": ["Mexico", "South Korea", "Chile", "South Africa"],
    "B": ["Italy", "Switzerland", "Qatar", "Bosnia"],
    "C": ["Brazil", "Morocco", "Nigeria", "Scotland"],
    "D": ["USA", "Australia", "Ukraine", "Paraguay"],
    "E": ["Germany", "Ecuador", "Poland", "Ivory Coast"],
    "F": ["Netherlands", "Japan", "Sweden", "Tunisia"],
    "G": ["Belgium", "Serbia", "Egypt", "Iran"],
    "H": ["Spain", "Uruguay", "Cameroon", "Saudi Arabia"],
    "I": ["France", "Senegal", "Norway", "Iraq"],
    "J": ["Argentina", "Austria", "Algeria", "Jordan"],
    "K": ["Portugal", "Colombia", "Uzbekistan", "New Zealand"],
    "L": ["England", "Croatia", "Ghana", "Panama"],
}

# ============ 主模拟器类 ============

class WorldCupSimulator:
    """世界杯完整模拟器"""

    def __init__(self, use_engine: bool = True):
        self.use_engine = use_engine
        self.engine = None
        self.xg = None
        self.team_stats = None
        self.group_simulator = None

        if use_engine and not USE_STANDALONE:
            print("🔧 初始化预测引擎...")
            self.engine = PredictionEngine(use_live_data=True)
            self.xg = self.engine.xg_model
            self.team_stats = self.engine.team_stats
            # 注意：GroupStageSimulator太慢，暂时使用独立xG模型
            # self.group_simulator = GroupStageSimulator(self.engine)
            self.group_simulator = None
            print("✅ 引擎初始化完成\n")

        if not self.engine:
            print("⚠️ 使用独立模式（无实时数据）")
            self.xg = xGModel()

    def simulate_group(self, group_name: str, teams: list,
                       monte_carlo: int = 5000) -> dict:
        """模拟小组赛"""
        print(f"\n🏟️  模拟第 {group_name} 组 ({monte_carlo} 次)...")

        # 如果有预测引擎的GroupStageSimulator，使用它（包含赔率融合）
        if self.group_simulator:
            result = self.group_simulator.simulate_group(group_name, teams, monte_carlo)
            return result

        # 否则使用旧的独立xG模型（为了向后兼容）

        standings_sum = {t: {"Pts": 0, "GD": 0, "GF": 0, "GA": 0}
                         for t in teams}
        qualify_counts = {t: 0 for t in teams}
        winner_counts = {t: 0 for t in teams}

        for _ in range(monte_carlo):
            points = {t: 0 for t in teams}
            gd = {t: 0 for t in teams}
            gf = {t: 0 for t in teams}

            # 模拟每场比赛
            for i, home in enumerate(teams):
                for j, away in enumerate(teams):
                    if i >= j:
                        continue

                    # 使用xG模型预测
                    home_xg, away_xg = self.xg.calculate_match_xg(home, away)
                    home_goals = self.xg.simulate_goals_poisson(home_xg)
                    away_goals = self.xg.simulate_goals_poisson(away_xg)

                    if home_goals > away_goals:
                        points[home] += 3
                    elif home_goals < away_goals:
                        points[away] += 3
                    else:
                        # 平局：各得1分
                        points[home] += 1
                        points[away] += 1

                    gd[home] += home_goals - away_goals
                    gd[away] += away_goals - home_goals
                    gf[home] += home_goals
                    gf[away] += away_goals

            # 排序
            sorted_teams = sorted(teams, key=lambda t: (points[t], gd[t], gf[t]), reverse=True)

            # 统计
            for i, t in enumerate(sorted_teams):
                if i < 2:
                    qualify_counts[t] += 1
                if i == 0:
                    winner_counts[t] += 1

            for t in teams:
                standings_sum[t]["Pts"] += points[t]
                standings_sum[t]["GD"] += gd[t]
                standings_sum[t]["GF"] += gf[t]

        # 计算概率
        result = {
            "group": group_name,
            "teams": teams,
            "runs": monte_carlo,
            "advancement": {},
        }

        for t in teams:
            result["advancement"][t] = {
                "qualify_prob": round(qualify_counts[t] / monte_carlo * 100, 1),
                "winner_prob": round(winner_counts[t] / monte_carlo * 100, 1),
                "avg_points": round(standings_sum[t]["Pts"] / monte_carlo, 1),
                "avg_gd": round(standings_sum[t]["GD"] / monte_carlo, 1),
            }

        return result

    def simulate_all_groups(self, monte_carlo: int = 5000) -> dict:
        """模拟所有小组赛"""
        print(f"\n{'='*60}")
        print(f"🏆 世界杯小组赛模拟 ({monte_carlo} 次/组)")
        print(f"{'='*60}")

        all_results = {}

        for group_name, teams in GROUPS.items():
            result = self.simulate_group(group_name, teams, monte_carlo)

            # 兼容新旧格式
            # 新格式: "advancement_probability" + "average_standings"
            # 旧格式: "advancement"
            if "advancement" not in result and "advancement_probability" in result:
                # 转换为旧格式
                result["advancement"] = {}
                for team, adv_stats in result["advancement_probability"].items():
                    avg_stats = result["average_standings"].get(team, {})
                    result["advancement"][team] = {
                        "qualify_prob": adv_stats["qualify_prob"],
                        "winner_prob": adv_stats["winner_prob"],
                        "avg_points": avg_stats.get("avg_points", 0),
                    }

            # 排序显示
            sorted_teams = sorted(result["advancement"].items(),
                                  key=lambda x: x[1]["qualify_prob"], reverse=True)

            print(f"\n📊 组 {group_name}:")
            for team, stats in sorted_teams:
                qual = "✅" if stats["qualify_prob"] > 50 else "❌"
                print(f"   {qual} {team:<20} 晋级:{stats['qualify_prob']:>5.1f}%  "
                      f"冠军:{stats['winner_prob']:>5.1f}%  "
                      f"均分:{stats['avg_points']:.1f}pt")

            all_results[group_name] = result

        return all_results

    def simulate_knockout_stage(self, monte_carlo: int = 10000,
                                 group_results: dict = None) -> dict:
        """模拟淘汰赛阶段"""
        print(f"\n{'='*60}")
        print(f"🎯 淘汰赛模拟 ({monte_carlo} 次完整世界杯)")
        print(f"{'='*60}")

        # 统计各队进入各阶段的次数
        from collections import defaultdict
        stage_counts = defaultdict(lambda: {
            "round_of_16": 0, "quarter": 0, "semi": 0, "final": 0, "champion": 0
        })

        for sim in range(monte_carlo):
            if (sim + 1) % 500 == 0:
                print(f"   淘汰赛进度: {sim + 1}/{monte_carlo}")

            # 基于小组赛结果确定16强（动态生成）
            ro16_teams = []

            if group_results:
                # 从小组赛结果获取晋级队伍
                for group_name in ["A", "B", "C", "D", "E", "F", "G", "H",
                                   "I", "J", "K", "L"]:
                    if group_name in group_results:
                        adv = group_results[group_name]["advancement"]
                        teams_in_group = list(adv.keys())
                        probs = [adv[t]["qualify_prob"] / 100 for t in teams_in_group]
                        if sum(probs) > 0:
                            qualifiers = random.choices(
                                teams_in_group,
                                weights=[max(p, 0.01) for p in probs],
                                k=2
                            )
                            ro16_teams.extend(qualifiers)
                        else:
                            ro16_teams.extend(teams_in_group[:2])
                    else:
                        ro16_teams.extend(["Team_A", "Team_B"])
            else:
                ro16_teams = [
                    "Spain", "Portugal", "France", "Argentina",
                    "Germany", "Brazil", "England", "Netherlands",
                    "Italy", "Croatia", "Belgium", "Mexico",
                    "USA", "Uruguay", "Japan", "Morocco",
                ]

            while len(ro16_teams) < 16:
                ro16_teams.append(f"Unknown_{len(ro16_teams)}")
            ro16_teams = ro16_teams[:16]

            # 16强对阵
            ro16_matches = [
                (0, 1), (2, 3), (4, 5), (6, 7),
                (8, 9), (10, 11), (12, 13), (14, 15)
            ]

            qf_winners = []
            for a_idx, b_idx in ro16_matches:
                team_a = ro16_teams[a_idx]
                team_b = ro16_teams[b_idx]
                winner = self._simulate_single_match(team_a, team_b)
                qf_winners.append(winner)
                stage_counts[winner]["round_of_16"] += 1

            # 8强
            qf_matches = [(0, 1), (2, 3), (4, 5), (6, 7)]
            sf_winners = []
            for a_idx, b_idx in qf_matches:
                team_a = qf_winners[a_idx]
                team_b = qf_winners[b_idx]
                winner = self._simulate_single_match(team_a, team_b)
                sf_winners.append(winner)
                stage_counts[winner]["quarter"] += 1

            # 4强
            sf_matches = [(0, 1), (2, 3)]
            final_winners = []
            for a_idx, b_idx in sf_matches:
                team_a = sf_winners[a_idx]
                team_b = sf_winners[b_idx]
                winner = self._simulate_single_match(team_a, team_b)
                final_winners.append(winner)
                stage_counts[winner]["semi"] += 1

            # 决赛
            team_a = final_winners[0]
            team_b = final_winners[1]
            champion = self._simulate_single_match(team_a, team_b)
            stage_counts[champion]["final"] += 1
            stage_counts[champion]["champion"] += 1
            loser = team_a if champion == team_b else team_b
            stage_counts[loser]["final"] += 1

        # 计算概率
        champion_probs = {
            t: round(c["champion"] / monte_carlo * 100, 2)
            for t, c in stage_counts.items()
        }
        sorted_champions = sorted(champion_probs.items(), key=lambda x: x[1], reverse=True)

        print(f"\n🏆 冠军概率 Top 10:")
        for team, prob in sorted_champions[:10]:
            bar = "█" * max(1, int(prob))
            print(f"   {team:<20} {prob:>5.2f}% {bar}")

        return {
            "monte_carlo": monte_carlo,
            "champion_probs": dict(sorted_champions[:10]),
            "stage_counts": dict(stage_counts),
        }

    def _simulate_single_match(self, team_a: str, team_b: str) -> str:
        """模拟单场比赛，返回胜者"""
        home_xg, away_xg = self.xg.calculate_match_xg(team_a, team_b)
        home_goals = self.xg.simulate_goals_poisson(home_xg)
        away_goals = self.xg.simulate_goals_poisson(away_xg)

        if home_goals > away_goals:
            return team_a
        elif away_goals > home_goals:
            return team_b
        else:
            # 加时赛/点球 - 简化：55开
            return team_a if random.random() < 0.52 else team_b

    def _simulate_elimination(self, team_a: str, team_b: str,
                              monte_carlo: int = 10000) -> dict:
        """模拟淘汰赛（单场决胜）"""
        a_wins = 0

        for _ in range(monte_carlo):
            home_xg, away_xg = self.xg.calculate_match_xg(team_a, team_b)
            home_goals = self.xg.simulate_goals_poisson(home_xg)
            away_goals = self.xg.simulate_goals_poisson(away_xg)

            if home_goals > away_goals:
                a_wins += 1
            elif away_goals > home_goals:
                pass  # B赢
            else:
                # 加时赛/点球 - 简化：55开
                if random.random() < 0.52:
                    a_wins += 1

        return {
            "winner": team_a if a_wins > monte_carlo / 2 else team_b,
            "prob_a": round(a_wins / monte_carlo, 3),
        }

    def run_full_simulation(self, monte_carlo_groups: int = 5000,
                           monte_carlo_knockout: int = 10000) -> dict:
        """运行完整世界杯模拟"""
        print(f"\n{'#'*60}")
        print(f"#  2026 世界杯完整模拟")
        print(f"#  小组赛: {monte_carlo_groups}次 | 淘汰赛: {monte_carlo_knockout}次")
        print(f"{'#'*60}")

        timestamp = datetime.now().isoformat()

        # 1. 小组赛
        group_results = self.simulate_all_groups(monte_carlo_groups)

        # 2. 淘汰赛（传入小组赛结果）
        knockout_results = self.simulate_knockout_stage(
            monte_carlo_knockout,
            group_results=group_results
        )

        # 3. 冠军统计（从淘汰赛结果获取）
        print(f"\n{'='*60}")
        print(f"🏆 冠军概率统计 (基于 {monte_carlo_knockout} 次完整世界杯模拟)")
        print(f"{'='*60}")

        # 淘汰赛结果已包含 stage_counts
        champion_probs = knockout_results.get("champion_probs", {})
        sorted_champions = sorted(champion_probs.items(), key=lambda x: x[1], reverse=True)

        for team, prob in sorted_champions[:10]:
            bar = "█" * max(1, int(prob))
            print(f"   {team:<20} {prob:>5.2f}% {bar}")

        # 4. 保存结果
        output = {
            "timestamp": timestamp,
            "simulation_params": {
                "monte_carlo_groups": monte_carlo_groups,
                "monte_carlo_knockout": monte_carlo_knockout,
                "version": "3.0_optimized",
            },
            "group_results": group_results,
            "knockout_results": knockout_results,
        }

        save_path = os.path.join(OUTPUT_DIR, f"simulation-{datetime.now().strftime('%Y-%m-%d-%H%M')}.json")
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        print(f"\n✅ 结果已保存: {save_path}")

        return output


# ============ 回测模块 ============

def run_backtest():
    """运行回测验证准确率"""
    print(f"\n{'='*60}")
    print(f"📊 回测验证")
    print(f"{'='*60}")

    if USE_STANDALONE:
        print("⚠️ 独立模式无法运行回测")
        return

    try:
        backtester = Backtester()
        xg = xGModel()
        team_stats = TeamRating()

        result = backtester.run_backtest(team_stats, xg, monte_carlo=5000)

        print(f"\n📈 回测结果:")
        print(f"   胜负预测准确率: {result['summary']['outcome_accuracy']*100:.1f}%")
        print(f"   比分精确正确率: {result['summary']['exact_score_accuracy']*100:.1f}%")
        print(f"   平均进球误差: {result['summary']['avg_goal_error']:.2f}")

        # 保存回测结果
        btest_path = os.path.join(BASE_DIR, "data/calibration/last_backtest.json")
        os.makedirs(os.path.dirname(btest_path), exist_ok=True)
        with open(btest_path, "w") as f:
            json.dump(result, f, indent=2)
        print(f"✅ 回测结果已保存")

    except Exception as e:
        print(f"❌ 回测失败: {e}")


# ============ 主程序 ============

def main():
    print(f"\n{'#'*60}")
    print(f"#  2026 世界杯预测系统 v3.0")
    print(f"#  优化版 - 整合xG+Elo+H2H+ML校准")
    print(f"{'#'*60}")

    # 创建模拟器
    simulator = WorldCupSimulator(use_engine=not USE_STANDALONE)

    # 询问运行模式
    import argparse
    parser = argparse.ArgumentParser(description="世界杯模拟器")
    parser.add_argument("--mode", choices=["full", "groups", "knockout", "backtest"],
                       default="full", help="运行模式")
    parser.add_argument("--mc-groups", type=int, default=5000,
                       help="小组赛蒙特卡洛次数")
    parser.add_argument("--mc-knockout", type=int, default=10000,
                       help="淘汰赛蒙特卡洛次数")
    args = parser.parse_args()

    if args.mode == "backtest":
        run_backtest()
    elif args.mode == "groups":
        simulator.simulate_all_groups(args.mc_groups)
    elif args.mode == "knockout":
        simulator.simulate_knockout_stage(args.mc_knockout)
    else:
        simulator.run_full_simulation(args.mc_groups, args.mc_knockout)

    print(f"\n{'='*60}")
    print(f"✅ 运行完成")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
