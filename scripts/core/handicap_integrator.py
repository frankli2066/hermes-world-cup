#!/usr/bin/env python3
"""
让球盘整合模块 v1.0
====================
整合让球盘(Handicap)数据到预测系统

核心功能：
1. 让球盘赔率转概率
2. 让球盘与胜平负概率转换
3. 盘口分析（强队让球时）
4. 大小球盘口整合
"""

import os
import json
import math
from typing import Dict, List, Tuple, Optional

# ============ 路径配置 ============
BASE_DIR = os.path.expanduser("~/hermes-world-cup/")
DATA_DIR = os.path.join(BASE_DIR, "data/")


class HandicapIntegrator:
    """
    让球盘整合器

    让球盘（Handicap）是比胜平负更精确的预测工具：
    - 强队让弱队1-2球
    - 盘口反映了庄家对实力差距的判断
    """

    def __init__(self):
        self.data_dir = DATA_DIR
        self.handicap_history = self._load_handicap_history()

        # 让球盘标准盘口
        self.standard_handicaps = [-2.0, -1.5, -1.0, -0.75, -0.5, -0.25, 0, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0]

    def _load_handicap_history(self) -> Dict:
        """加载让球盘历史"""
        history_file = os.path.join(self.data_dir, "handicap_history.json")
        if os.path.exists(history_file):
            try:
                with open(history_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def save_handicap_history(self):
        """保存让球盘历史"""
        history_file = os.path.join(self.data_dir, "handicap_history.json")
        os.makedirs(os.path.dirname(history_file), exist_ok=True)
        with open(history_file, 'w') as f:
            json.dump(self.handicap_history, f, ensure_ascii=False, indent=2)

    def handicap_to_win_prob(self,
                             handicap: float,
                             home_odds: float,
                             away_odds: float) -> Dict:
        """
        从让球盘赔率转换为胜平负概率

        Args:
            handicap: 让球数（正数=主队让，负数=客队让）
            home_odds: 主队让球盘赔率
            away_odds: 客队受让盘赔率

        Returns:
            胜平负概率
        """
        # 标准化盘口
        # 让球盘表示：强队需要"让"一定数量的球
        # 例如：-1.5 表示主队需要赢2球才能赢盘

        # 从赔率计算隐含概率
        vig = 0.05  # 庄家抽水

        home_implied = (1 / home_odds) if home_odds > 0 else 0
        away_implied = (1 / away_odds) if away_odds > 0 else 0

        # 归一化（去除水钱）
        total = home_implied + away_implied
        if total > 0:
            home_prob = home_implied / total
            away_prob = away_implied / total
        else:
            home_prob = 0.5
            away_prob = 0.5

        # 根据盘口调整
        # 如果盘口偏向主队让球，说明主队被看好
        handicap_factor = handicap / 4  # 归一化

        # 平局概率（让球盘通常有平局选项，这里简化处理）
        draw_prob = 0.25 - abs(handicap_factor) * 0.1

        # 调整后的胜平负
        adjusted_home = home_prob * (1 + handicap_factor * 0.3)
        adjusted_away = away_prob * (1 - handicap_factor * 0.3)

        # 归一化
        total = adjusted_home + adjusted_away + draw_prob
        if total > 0:
            adjusted_home /= total
            adjusted_away /= total
            draw_prob /= total

        return {
            "home_win": max(0, min(1, adjusted_home)),
            "draw": max(0, min(1, draw_prob)),
            "away_win": max(0, min(1, adjusted_away)),
            "handicap": handicap,
            "home_odds": home_odds,
            "away_odds": away_odds,
            "market_favor": "home" if handicap > 0 else "away"
        }

    def get_handicap_from_elo_diff(self, elo_diff: float) -> float:
        """
        根据Elo差距估算合适的让球盘口

        Args:
            elo_diff: Elo差距（正值=主队强）

        Returns:
            估算的让球盘口
        """
        # Elo差距与盘口的映射
        # 大约每50 Elo对应0.25球盘口
        handicap = elo_diff / 200

        # 限制范围
        handicap = max(-2.0, min(2.0, handicap))

        # 转换为标准盘口
        standard = self._round_to_standard(handicap)

        return standard

    def _round_to_standard(self, handicap: float) -> float:
        """四舍五入到标准盘口"""
        # 常见盘口：0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0
        standard_values = [0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0]
        closest = min(standard_values, key=lambda x: abs(x - handicap))
        return closest

    def analyze_handicap(self,
                         handicap: float,
                         home_team: str,
                         away_team: str,
                         elo_diff: float) -> Dict:
        """
        分析让球盘口

        Args:
            handicap: 让球数
            home_team: 主队
            away_team: 客队
            elo_diff: Elo差距

        Returns:
            盘口分析报告
        """
        # 估算盘口
        estimated_handicap = self.get_handicap_from_elo_diff(elo_diff)

        # 盘口偏差
        handicap_diff = handicap - estimated_handicap

        # 解读盘口
        if handicap > 0:
            interpretation = f"主队让{handicap}球"
            favor = "home"
            if handicap > estimated_handicap:
                line_assessment = "盘口偏深，主队被高估"
                market_bias = -0.05  # 对主队不利
            elif handicap < estimated_handicap:
                line_assessment = "盘口偏浅，主队被低估"
                market_bias = 0.05  # 对主队有利
            else:
                line_assessment = "盘口合理"
                market_bias = 0
        else:
            interpretation = f"客队受让{abs(handicap)}球"
            favor = "away"
            if abs(handicap) > abs(estimated_handicap):
                line_assessment = "盘口偏深，客队被低估"
                market_bias = 0.05
            else:
                line_assessment = "盘口合理"
                market_bias = 0

        return {
            "handicap": handicap,
            "estimated_handicap": estimated_handicap,
            "handicap_diff": handicap_diff,
            "interpretation": interpretation,
            "favor": favor,
            "line_assessment": line_assessment,
            "market_bias": market_bias,
            "recommendation": self._get_handicap_recommendation(market_bias, handicap, favor)
        }

    def _get_handicap_recommendation(self, market_bias: float, handicap: float, favor: str) -> str:
        """获取让球盘推荐"""
        if abs(market_bias) > 0.03:
            if market_bias > 0:
                return f"支持{favor}队让球（市场低估）"
            else:
                opposite = "home" if favor == "away" else "away"
                return f"支持受让方（市场高估{favor}队）"
        else:
            return "盘口合理，无明显价值"

    def get_over_under_line(self,
                            total_goals_estimate: float,
                            market_line: float = 2.5) -> Dict:
        """
        分析大小球盘口

        Args:
            total_goals_estimate: 预期总进球数
            market_line: 市场盘口（默认2.5）

        Returns:
            大小球分析
        """
        # 计算大球概率（基于预期进球）
        import math
        # 使用泊松分布计算大于市场线的概率
        over_prob = 1 - self._poisson_cdf(int(market_line), total_goals_estimate)

        if over_prob > 0.55:
            recommendation = f"推荐大{market_line}球"
            value = over_prob - 0.5
        elif over_prob < 0.45:
            recommendation = f"推荐小{market_line}球"
            value = 0.5 - over_prob
        else:
            recommendation = "无明显价值"
            value = 0

        return {
            "total_goals_estimate": total_goals_estimate,
            "market_line": market_line,
            "over_prob": over_prob,
            "under_prob": 1 - over_prob,
            "recommendation": recommendation,
            "value": value,
            "edge": value * 100
        }

    def _poisson_cdf(self, k: int, lambda_: float) -> float:
        """泊松分布累积分布函数"""
        import math
        if k < 0:
            return 0

        # P(X <= k)
        cdf = 0
        for i in range(k + 1):
            cdf += (math.exp(-lambda_) * (lambda_ ** i)) / math.factorial(i)

        return cdf

    def integrate_with_prediction(self,
                                  handicap: float,
                                  home_odds: float,
                                  away_odds: float,
                                  model_home_prob: float,
                                  model_draw_prob: float,
                                  model_away_prob: float,
                                  elo_diff: float) -> Dict:
        """
        将让球盘整合到预测中

        Args:
            handicap: 让球数
            home_odds: 主队让球赔率
            away_odds: 客队受让赔率
            model_*: 模型预测的概率
            elo_diff: Elo差距

        Returns:
            整合后的预测
        """
        # 从让球盘获取概率
        handicap_probs = self.handicap_to_win_prob(handicap, home_odds, away_odds)

        # 分析盘口
        analysis = self.analyze_handicap(handicap, "", "", elo_diff)

        # 权重融合
        # 如果让球盘与模型一致，增加信心
        # 如果不一致，使用让球盘作为主要信号

        handicap_weight = 0.3  # 让球盘占30%权重

        # 最终概率
        final_home = model_home_prob * (1 - handicap_weight) + handicap_probs["home_win"] * handicap_weight
        final_draw = model_draw_prob * (1 - handicap_weight) + handicap_probs["draw"] * handicap_weight
        final_away = model_away_prob * (1 - handicap_weight) + handicap_probs["away_win"] * handicap_weight

        # 应用市场偏差调整
        if analysis["market_bias"] != 0:
            if analysis["favor"] == "home":
                adjustment = analysis["market_bias"]
                final_home += adjustment * 0.5
                final_away -= adjustment * 0.5
            else:
                adjustment = analysis["market_bias"]
                final_away += adjustment * 0.5
                final_home -= adjustment * 0.5

        # 归一化
        total = final_home + final_draw + final_away
        if total > 0:
            final_home /= total
            final_draw /= total
            final_away /= total

        # 调整信心
        confidence_boost = abs(analysis["market_bias"]) if analysis["line_assessment"] != "盘口合理" else 0

        return {
            "final_home_prob": final_home,
            "final_draw_prob": final_draw,
            "final_away_prob": final_away,
            "handicap_analysis": analysis,
            "confidence_boost": confidence_boost,
            "integration_method": "weighted_average",
            "recommendation": "home" if final_home > max(final_draw, final_away)
                             else ("away" if final_away > final_draw else "draw")
        }


# ============ 测试代码 ============
if __name__ == "__main__":
    integrator = HandicapIntegrator()

    print("=" * 60)
    print("让球盘整合测试")
    print("=" * 60)

    # 测试：根据Elo差距估算盘口
    print("\nElo差距与盘口映射:")
    for elo_diff in [-300, -200, -100, -50, 0, 50, 100, 200, 300]:
        handicap = integrator.get_handicap_from_elo_diff(elo_diff)
        print(f"  Elo差{elo_diff:+4d} -> 盘口: {handicap:+.2f}")

    # 测试盘口分析
    print("\n盘口分析示例:")
    analysis = integrator.analyze_handicap(
        handicap=1.0,
        home_team="Germany",
        away_team="Costa Rica",
        elo_diff=250
    )

    for key, value in analysis.items():
        print(f"  {key}: {value}")

    # 测试大小球
    print("\n大小球分析示例:")
    ou = integrator.get_over_under_line(total_goals_estimate=2.8, market_line=2.5)
    for key, value in ou.items():
        print(f"  {key}: {value}")
