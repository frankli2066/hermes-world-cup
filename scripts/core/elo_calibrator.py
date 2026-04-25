#!/usr/bin/env python3
"""
Elo校准模块 v1.0

用Polymarket市场赔率校准Elo初始值

核心思想：
- Polymarket的夺冠赔率是世界上最好的预测模型
- 赔率中包含了：球员实力、大赛经验、战术状态等所有因素
- 用市场赔率来校准Elo，可以使模型更准确

算法：
1. 把Polymarket夺冠概率转换为相对实力
2. 计算每个球队应该有的"市场Elo"
3. 比较当前Elo和市场Elo，计算偏差
4. 用偏差来调整Elo
"""

import json
import os
import math
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

BASE_DIR = os.path.expanduser("~/hermes-world-cup/")


# ============ Elo转换工具 ============

def market_prob_to_elo(prob: float, base_elo: int = 1500, total_teams: int = 32) -> float:
    """
    把市场夺冠概率转换为Elo评分

    原理：
    - Elo差距 = 200 per 75% vs 25% 概率
    - 假设最热门球队（概率p）的Elo = base_elo + X
    - 其他球队按概率比例分配Elo

    Args:
        prob: 夺冠概率（0-1）
        base_elo: 基准Elo（默认1500）
        total_teams: 总球队数

    Returns:
        该概率对应的Elo值
    """
    if prob <= 0:
        return base_elo - 200  # 弱队

    # 参考：p=0.20的球队应该有多少Elo
    # 假设最热1.0概率 = 1900 Elo，最冷0.01概率 = 1500 Elo
    # Elo = 1400 + prob * 2500 （简化公式）

    # 更合理的公式：考虑概率分布
    # 使用对数来压缩高概率区域
    elo = base_elo + math.log(prob + 0.001) * 400 + 1500

    return elo


def elo_to_win_prob(elo_a: float, elo_b: float, home_advantage: float = 0) -> Tuple[float, float, float]:
    """
    用Elo计算胜平负概率

    Args:
        elo_a: 主队Elo
        elo_b: 客队Elo
        home_advantage: 主场优势（Elo加分）

    Returns:
        (主队胜率, 平局概率, 客队胜率)
    """
    # 转换为概率差距
    elo_diff = elo_a + home_advantage - elo_b

    # 基础赢概率（使用Elo公式）
    prob_a_win = 1 / (1 + 10 ** (-elo_diff / 400))

    # 平局概率估算（基于Elo差距）
    # 差距越大，平局概率越低
    draw_base = 0.25
    if abs(elo_diff) > 200:
        draw_prob = 0.18
    elif abs(elo_diff) > 100:
        draw_prob = 0.22
    elif abs(elo_diff) > 50:
        draw_prob = 0.25
    else:
        draw_prob = 0.28

    # 调整：赢家拿走平局概率的一部分
    prob_a_adjusted = prob_a_win * (1 - draw_prob * 0.5)
    prob_b_adjusted = (1 - prob_a_win) * (1 - draw_prob * 0.5)

    return (prob_a_adjusted, draw_prob, prob_b_adjusted)


def calibrate_elo_with_market(
    current_elo: Dict[str, float],
    market_probs: Dict[str, float],
    learning_rate: float = 0.3,
) -> Dict[str, float]:
    """
    用市场概率校准Elo

    算法：
    1. 计算当前Elo的市场夺冠概率分布
    2. 与实际市场概率对比
    3. 调整Elo使两者一致

    Args:
        current_elo: 当前Elo dict {team: elo}
        market_probs: 市场夺冠概率 {team: prob}
        learning_rate: 调整速度（0-1）

    Returns:
        校准后的Elo dict
    """
    # 计算当前Elo的"市场表现"
    teams = [k for k in current_elo.keys() if not str(k).startswith('---')]
    n = len(teams)

    # 计算Elo总和（用于归一化），过滤非数值（如注释行）
    numeric_values = [v for v in current_elo.values() if isinstance(v, (int, float))]
    n = len(numeric_values)
    total_elo = sum(numeric_values)
    avg_elo = total_elo / n if n > 0 else 1500

    # 计算当前Elo的"隐含概率"
    elo_implied_probs = {}
    for team in teams:
        # 与平均水平的差距
        elo_diff = current_elo[team] - avg_elo
        # 转换为概率（简化：每100 Elo = 2倍概率）
        implied_prob = 0.03 * (1 + elo_diff / 400)  # 基准3%
        elo_implied_probs[team] = max(implied_prob, 0.001)

    # 归一化
    total_implied = sum(elo_implied_probs.values())
    for team in elo_implied_probs:
        elo_implied_probs[team] /= total_implied

    # 与市场概率对比，计算调整
    calibrated_elo = {}
    adjustment_log = []

    for team in teams:
        current = current_elo.get(team, 1500)
        market = market_probs.get(team, 0.01)
        implied = elo_implied_probs.get(team, 0.01)

        if market > 0 and implied > 0:
            # 概率比率
            ratio = market / implied

            # 转换为Elo调整
            # ratio > 1 = 市场比Elo更看好
            # ratio < 1 = 市场比Elo更看衰
            elo_adjustment = math.log(ratio) * 200 * learning_rate

            calibrated_elo[team] = current + elo_adjustment

            adjustment_log.append({
                "team": team,
                "market": market,
                "implied": implied,
                "ratio": ratio,
                "adjustment": elo_adjustment,
                "old_elo": current,
                "new_elo": calibrated_elo[team],
            })

    # 按调整幅度排序
    adjustment_log.sort(key=lambda x: abs(x["adjustment"]), reverse=True)

    return calibrated_elo, adjustment_log


def simulate_champion_probs(
    elo_ratings: Dict[str, float],
    monte_carlo: int = 10000,
    home_advantage: float = 50,
) -> Dict[str, float]:
    """
    用Elo模拟各队夺冠概率

    这个函数用于验证Elo校准后的效果
    """
    import random

    teams = list(elo_ratings.keys())
    elo_values = [elo_ratings[t] for t in teams]

    champion_counts = {t: 0 for t in teams}

    # 简化的世界杯模拟（48队分8组，每组前2名出线，16强后单淘汰）
    # 这里用更简单的方法：基于Elo的随机淘汰赛

    for _ in range(monte_carlo):
        # 每轮随机淘汰一半
        remaining = list(teams)
        remaining_elo = [elo_ratings[t] for t in remaining]

        # 16强到决赛（4轮）
        for round_num in range(4):
            new_remaining = []
            new_elo = []

            # 随机配对
            indices = list(range(len(remaining)))
            random.shuffle(indices)

            for i in range(0, len(indices) - 1, 2):
                idx_a = indices[i]
                idx_b = indices[i + 1]

                team_a = remaining[idx_a]
                team_b = remaining[idx_b]
                elo_a = elo_ratings[team_a]
                elo_b = elo_ratings[team_b]

                # 主场优势给排名高的
                if elo_a >= elo_b:
                    ha = home_advantage
                else:
                    ha = -home_advantage

                prob_a, _, prob_b = elo_to_win_prob(elo_a, elo_b, ha)

                # 随机决定胜负（简化：90分钟）
                rand = random.random()
                if rand < prob_a:
                    winner = team_a
                elif rand < prob_a + prob_b:
                    winner = team_b
                else:
                    # 平局：随机选一个
                    winner = team_a if random.random() < 0.5 else team_b

                new_remaining.append(winner)
                new_elo.append(elo_ratings[winner])

            remaining = new_remaining

        # 冠军
        if remaining:
            champion_counts[remaining[0]] += 1

    # 转换为概率
    champion_probs = {
        team: count / monte_carlo
        for team, count in champion_counts.items()
    }

    return champion_probs


# ============ 校准器主类 ============

class EloCalibrator:
    """
    Elo校准器

    用Polymarket市场数据校准Elo评分
    """

    def __init__(self, elo_system, market_data: dict = None):
        """
        Args:
            elo_system: EloSystem对象
            market_data: Polymarket数据
        """
        self.elo_system = elo_system
        self.market_data = market_data or {}
        self.calibrated_elo = None
        self.adjustment_log = []

    def load_market_data(self, market_data: dict):
        """加载市场数据"""
        self.market_data = market_data

    def calibrate(self, learning_rate: float = 0.3) -> Dict[str, float]:
        """
        执行Elo校准

        Args:
            learning_rate: 调整速度（0-1）

        Returns:
            校准后的Elo dict
        """
        if not self.market_data:
            print("⚠️ 没有市场数据，无法校准")
            return self.elo_system.ratings.copy()

        # 提取市场概率
        market_probs = {}
        teams_data = self.market_data.get("teams", [])
        for team_info in teams_data:
            team = team_info.get("team", "")
            yes_price = team_info.get("yes_price", 0)
            if team and yes_price > 0:
                market_probs[team] = yes_price

        if not market_probs:
            print("⚠️ 市场数据格式错误，无法校准")
            return self.elo_system.ratings.copy()

        # 执行校准
        current_elo = self.elo_system.ratings.copy()
        self.calibrated_elo, self.adjustment_log = calibrate_elo_with_market(
            current_elo, market_probs, learning_rate
        )

        return self.calibrated_elo

    def apply_calibration(self):
        """将校准结果应用到Elo系统"""
        if self.calibrated_elo is None:
            print("⚠️ 请先执行calibrate()")
            return

        self.elo_system.ratings = self.calibrated_elo.copy()
        print("✅ Elo校准已应用")

    def print_comparison(self, top_n: int = 15):
        """打印校准前后对比"""
        if not self.adjustment_log:
            print("⚠️ 没有校准数据")
            return

        print("\n" + "=" * 70)
        print("📊 Elo校准对比")
        print("=" * 70)
        print(f"{'球队':<18} {'市场概率':>10} {'校准前':>10} {'校准后':>10} {'调整':>10}")
        print("-" * 70)

        for item in self.adjustment_log[:top_n]:
            adj = item["adjustment"]
            sign = "+" if adj > 0 else ""
            print(f"{item['team']:<18} {item['market']*100:>9.2f}% "
                  f"{item['old_elo']:>10.0f} {item['new_elo']:>10.0f} "
                  f"{sign+str(round(adj,1)):>10}")

        print("=" * 70)

    def validate_calibration(self, monte_carlo: int = 5000) -> Dict:
        """验证校准效果：模拟夺冠概率与市场对比"""
        if self.calibrated_elo is None:
            return {}

        # 模拟Elo的夺冠概率
        simulated_probs = simulate_champion_probs(
            self.calibrated_elo, monte_carlo
        )

        # 提取市场概率
        market_probs = {}
        teams_data = self.market_data.get("teams", [])
        for team_info in teams_data:
            team = team_info.get("team", "")
            yes_price = team_info.get("yes_price", 0)
            if team and yes_price > 0:
                market_probs[team] = yes_price

        # 对比
        comparison = []
        for team in list(self.calibrated_elo.keys())[:15]:
            sim_prob = simulated_probs.get(team, 0)
            mkt_prob = market_probs.get(team, 0)
            diff = abs(sim_prob - mkt_prob)
            comparison.append({
                "team": team,
                "simulated": sim_prob,
                "market": mkt_prob,
                "diff": diff,
            })

        comparison.sort(key=lambda x: x["diff"], reverse=True)

        print("\n📈 校准验证（模拟 vs 市场）:")
        for item in comparison[:10]:
            print(f"  {item['team']:<18} 模拟={item['simulated']*100:5.2f}%  市场={item['market']*100:5.2f}%  误差={item['diff']*100:5.2f}%")

        avg_error = sum(x["diff"] for x in comparison) / len(comparison) if comparison else 0
        print(f"\n  平均误差: {avg_error*100:.2f}%")

        return comparison


# ============ 测试 ============

if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "core"))

    from team_stats import EloSystem
    import json

    print("=" * 60)
    print("🔧 Elo校准模块测试")
    print("=" * 60)

    # 加载Elo系统
    elo = EloSystem()

    # 加载Polymarket数据
    pm_file = os.path.join(BASE_DIR, "polymarket/2026-04-13-11-champion-odds.json")
    if os.path.exists(pm_file):
        with open(pm_file) as f:
            pm_data = json.load(f)
    else:
        # 使用示例数据
        pm_data = {
            "teams": [
                {"team": "Spain", "yes_price": 0.1745},
                {"team": "France", "yes_price": 0.1605},
                {"team": "England", "yes_price": 0.1115},
                {"team": "Argentina", "yes_price": 0.0890},
                {"team": "Brazil", "yes_price": 0.0865},
                {"team": "Portugal", "yes_price": 0.0690},
                {"team": "Germany", "yes_price": 0.0530},
            ]
        }

    print(f"\n加载了 {len(pm_data.get('teams', []))} 支球队的市场数据")

    # 创建校准器
    calibrator = EloCalibrator(elo, pm_data)

    # 执行校准
    print("\n执行Elo校准...")
    calibrated = calibrator.calibrate(learning_rate=0.3)

    # 打印对比
    calibrator.print_comparison(top_n=10)

    # 验证校准效果
    print("\n验证校准效果...")
    calibrator.validate_calibration(monte_carlo=3000)

    print("\n" + "=" * 60)
