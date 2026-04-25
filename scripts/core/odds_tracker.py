#!/usr/bin/env python3
"""
赔率变化趋势追踪 v1.0
========================
记录和分析赔率从初盘到临场的变化

核心概念：
1. 初盘赔率 (Opening Odds): 比赛开始前7天的赔率
2. 终盘赔率 (Closing Odds): 比赛开始前1-2小时的赔率
3. 赔率变化率: (终盘 - 初盘) / 初盘

分析方法：
1. 赔率向某队下降 → 该队受资金青睐
2. 赔率大幅波动 → 市场不确定
3. 临场赔率与模型预测差异 → 价值投注机会

关键指标：
- movement_rate: 变化率
- sharp_money: 专业资金流向
- reverse_line: 反向资金
- steam_move: 热门方向
"""

import os
import json
import math
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

# ============ 路径配置 ============
BASE_DIR = os.path.expanduser("~/hermes-world-cup/")
DATA_DIR = os.path.join(BASE_DIR, "data/")


# ============ 赔率数据模型 ============
# 这些是模拟数据，实际使用时应该从API获取

class OddsTracker:
    """
    赔率变化趋势追踪器
    """

    def __init__(self):
        self.data_file = os.path.join(DATA_DIR, "odds_tracking.json")
        self.odds_history = self._load_data()

    def _load_data(self) -> Dict:
        """加载历史赔率数据"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {"matches": []}

    def _save_data(self):
        """保存赔率数据"""
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
        with open(self.data_file, 'w') as f:
            json.dump(self.odds_history, f, ensure_ascii=False, indent=2)

    def calculate_implied_prob(self, odds: float) -> float:
        """赔率转换为隐含概率"""
        if odds <= 0:
            return 0.33
        return 1.0 / odds

    def calculate_movement(self,
                          opening: Dict[str, float],
                          closing: Dict[str, float]) -> Dict:
        """
        计算赔率变化

        Args:
            opening: 初盘 {"home": 2.0, "draw": 3.2, "away": 3.8}
            closing: 终盘

        Returns:
            变化分析
        """
        # 计算隐含概率
        open_home = self.calculate_implied_prob(opening.get("home", 2.0))
        open_draw = self.calculate_implied_prob(opening.get("draw", 3.2))
        open_away = self.calculate_implied_prob(opening.get("away", 3.8))

        close_home = self.calculate_implied_prob(closing.get("home", 2.0))
        close_draw = self.calculate_implied_prob(closing.get("draw", 3.2))
        close_away = self.calculate_implied_prob(closing.get("away", 3.8))

        # 归一化
        open_total = open_home + open_draw + open_away
        close_total = close_home + close_draw + close_away

        open_home /= open_total
        open_draw /= open_total
        open_away /= open_total
        close_home /= close_total
        close_draw /= close_total
        close_away /= close_total

        # 计算变化
        home_change = close_home - open_home
        draw_change = close_draw - open_draw
        away_change = close_away - open_away

        # 赔率变化率（负数表示赔率下降，资金涌入）
        home_movement = (closing.get("home", 2.0) - opening.get("home", 2.0)) / opening.get("home", 2.0)
        away_movement = (closing.get("away", 3.8) - opening.get("away", 3.8)) / opening.get("away", 3.8)

        # 总变化幅度
        total_movement = abs(home_movement) + abs(away_movement)

        # 判断方向
        if home_change > 0.02:
            direction = "home_heavy"  # 主队受资金青睐
            confidence_boost = home_change * 0.5
        elif away_change > 0.02:
            direction = "away_heavy"  # 客队受资金青睐
            confidence_boost = away_change * 0.5
        elif draw_change > 0.03:
            direction = "draw_heavy"  # 平局被买入
            confidence_boost = 0
        else:
            direction = "balanced"  # 资金平衡
            confidence_boost = 0

        # 波动性（高波动=不确定）
        volatility = total_movement * 10  # 转换为百分比

        return {
            "direction": direction,
            "home_change": home_change,
            "away_change": away_change,
            "draw_change": draw_change,
            "home_movement_pct": home_movement * 100,
            "away_movement_pct": away_movement * 100,
            "total_volatility": volatility,
            "confidence_boost": confidence_boost,
            "is_sharp_money": abs(home_change) > 0.05 or abs(away_change) > 0.05,
            "is_steam_move": total_movement > 0.15,  # 超过15%的变化
            "assessment": self._assess_movement(
                direction, volatility, total_movement
            )
        }

    def _assess_movement(self,
                        direction: str,
                        volatility: float,
                        total_movement: float) -> str:
        """评估赔率变化"""
        if volatility > 10:
            return "高波动，市场不确定"
        elif volatility > 5:
            return "中等波动，有明显资金流向"
        else:
            return "低波动，赔率稳定"

    def analyze_odds(self,
                    opening: Dict[str, float],
                    closing: Dict[str, float],
                    model_prediction: Dict[str, float] = None) -> Dict:
        """
        综合分析赔率

        Args:
            opening: 初盘
            closing: 终盘
            model_prediction: 模型预测 {"home": 0.45, "draw": 0.25, "away": 0.30}

        Returns:
            完整分析
        """
        movement = self.calculate_movement(opening, closing)

        # 计算市场概率（从终盘）
        close_home = self.calculate_implied_prob(closing.get("home", 2.0))
        close_draw = self.calculate_implied_prob(closing.get("draw", 3.2))
        close_away = self.calculate_implied_prob(closing.get("away", 3.8))

        total = close_home + close_draw + close_away
        market_prob = {
            "home": close_home / total,
            "draw": close_draw / total,
            "away": close_away / total
        }

        # 市场 vs 模型对比
        value_opportunities = []
        if model_prediction:
            for key in ["home", "draw", "away"]:
                model_prob = model_prediction.get(key, 0.33)
                market_prob_val = market_prob.get(key, 0.33)
                diff = model_prob - market_prob_val

                if abs(diff) > 0.05:
                    if diff > 0:
                        value_opportunities.append({
                            "outcome": key,
                            "type": "overvalued",
                            "edge": diff,
                            "reason": f"模型{key}概率{model_prob:.1%} > 市场{market_prob_val:.1%}"
                        })
                    else:
                        value_opportunities.append({
                            "outcome": key,
                            "type": "undervalued",
                            "edge": abs(diff),
                            "reason": f"模型{key}概率{model_prob:.1%} < 市场{market_prob_val:.1%}"
                        })

        return {
            "movement": movement,
            "market_probabilities": market_prob,
            "model_vs_market": {
                "has_value": len(value_opportunities) > 0,
                "opportunities": value_opportunities
            },
            "recommendation": self._get_recommendation(movement, value_opportunities)
        }

    def _get_recommendation(self,
                           movement: Dict,
                           value_opportunities: List) -> str:
        """获取赔率相关的推荐"""
        if movement["is_steam_move"]:
            return "热门方向明确，跟随资金"

        if movement["is_sharp_money"]:
            return "专业资金入场，参考价值高"

        if value_opportunities:
            best = max(value_opportunities, key=lambda x: x["edge"])
            if best["type"] == "overvalued":
                return f"{best['outcome']}被高估，有价值"
            else:
                return f"{best['outcome']}被低估，关注"

        return "赔率无明显异常"

    def get_odds_factor(self,
                        opening: Dict[str, float],
                        closing: Dict[str, float]) -> float:
        """
        获取赔率因子（用于预测模型）

        Returns:
            调整因子
            > 0: 主队被低估
            < 0: 客队被低估
        """
        movement = self.calculate_movement(opening, closing)

        # 基于资金流向调整
        if movement["direction"] == "home_heavy":
            # 主队被资金推高，但可能过热
            # 返回负值表示主队被高估
            return -movement["confidence_boost"]
        elif movement["direction"] == "away_heavy":
            return movement["confidence_boost"]
        else:
            return 0.0

    def simulate_odds_data(self, match_id: str, home_team: str, away_team: str) -> Dict:
        """
        模拟赔率数据（实际使用时应该从API获取）

        用于测试和演示
        """
        import random

        # 基于球队实力生成基准赔率
        # 简化：主队优势0.1
        base_home_prob = 0.45 + random.uniform(-0.1, 0.1)
        base_away_prob = 0.30 + random.uniform(-0.1, 0.1)
        base_draw_prob = 1 - base_home_prob - base_away_prob

        # 转换为赔率
        open_home = 1.0 / base_home_prob * (1 + random.uniform(-0.05, 0.05))
        open_draw = 1.0 / base_draw_prob * (1 + random.uniform(-0.05, 0.05))
        open_away = 1.0 / base_away_prob * (1 + random.uniform(-0.05, 0.05))

        # 模拟终盘变化
        movement = random.uniform(-0.1, 0.1)  # 赔率变化方向
        close_home = open_home * (1 + movement * 0.3)
        close_draw = open_draw * (1 + random.uniform(-0.05, 0.05))
        close_away = open_away * (1 - movement * 0.3)

        return {
            "match_id": match_id,
            "home_team": home_team,
            "away_team": away_team,
            "opening": {
                "home": round(open_home, 2),
                "draw": round(open_draw, 2),
                "away": round(open_away, 2)
            },
            "closing": {
                "home": round(close_home, 2),
                "draw": round(close_draw, 2),
                "away": round(close_away, 2)
            },
            "timestamp": datetime.now().isoformat()
        }

    def save_match_odds(self, odds_data: Dict):
        """保存比赛赔率数据"""
        if "matches" not in self.odds_history:
            self.odds_history["matches"] = []

        self.odds_history["matches"].append(odds_data)

        # 只保留最近1000条
        if len(self.odds_history["matches"]) > 1000:
            self.odds_history["matches"] = self.odds_history["matches"][-1000:]

        self._save_data()

    def get_odds_history(self, home_team: str, away_team: str) -> List[Dict]:
        """获取两队历史赔率数据"""
        matches = self.odds_history.get("matches", [])
        return [
            m for m in matches
            if m.get("home_team") == home_team and m.get("away_team") == away_team
        ]

    def save_to_file(self, filepath: str = None):
        """保存到文件"""
        if filepath is None:
            filepath = os.path.join(DATA_DIR, "odds_tracking.json")

        self._save_data()
        print(f"✅ 赔率数据已保存: {filepath}")


# ============ 简化接口函数 ============
def quick_odds_analysis(opening: Dict, closing: Dict, model_pred: Dict = None) -> Dict:
    """快速赔率分析"""
    tracker = OddsTracker()
    return tracker.analyze_odds(opening, closing, model_pred)


def get_odds_factor(opening: Dict, closing: Dict) -> float:
    """快速获取赔率因子"""
    tracker = OddsTracker()
    return tracker.get_odds_factor(opening, closing)


# ============ 测试 ============
if __name__ == "__main__":
    tracker = OddsTracker()

    print("=" * 60)
    print("📊 赔率变化趋势追踪测试")
    print("=" * 60)

    # 测试1：主队受资金青睐
    print("\n📍 测试1：主队受资金青睐")
    opening1 = {"home": 2.0, "draw": 3.2, "away": 3.8}
    closing1 = {"home": 1.8, "draw": 3.4, "away": 4.5}
    result1 = tracker.analyze_odds(opening1, closing1)
    print(f"   初盘: {opening1}")
    print(f"   终盘: {closing1}")
    print(f"   方向: {result1['movement']['direction']}")
    print(f"   波动: {result1['movement']['total_volatility']:.1f}%")
    print(f"   评估: {result1['recommendation']}")

    # 测试2：客队被低估
    print("\n📍 测试2：客队被低估")
    opening2 = {"home": 1.6, "draw": 4.0, "away": 5.0}
    closing2 = {"home": 1.7, "draw": 3.8, "away": 4.5}
    result2 = tracker.analyze_odds(opening2, closing2)
    print(f"   初盘: {opening2}")
    print(f"   终盘: {closing2}")
    print(f"   方向: {result2['movement']['direction']}")
    print(f"   波动: {result2['movement']['total_volatility']:.1f}%")

    # 测试3：高波动市场
    print("\n📍 测试3：高波动市场")
    opening3 = {"home": 2.0, "draw": 3.2, "away": 3.8}
    closing3 = {"home": 2.3, "draw": 3.0, "away": 3.0}
    result3 = tracker.analyze_odds(opening3, closing3)
    print(f"   初盘: {opening3}")
    print(f"   终盘: {closing3}")
    print(f"   方向: {result3['movement']['direction']}")
    print(f"   波动: {result3['movement']['total_volatility']:.1f}%")
    print(f"   评估: {result3['recommendation']}")

    # 测试4：模型对比
    print("\n📍 测试4：模型vs市场对比")
    model_pred = {"home": 0.50, "draw": 0.25, "away": 0.25}
    result4 = tracker.analyze_odds(opening1, closing1, model_pred)
    print(f"   模型预测: {model_pred}")
    print(f"   市场概率: {result4['market_probabilities']}")
    if result4['model_vs_market']['has_value']:
        print(f"   价值机会: {result4['model_vs_market']['opportunities']}")

    # 测试5：模拟数据生成
    print("\n📍 测试5：模拟赔率数据")
    sim = tracker.simulate_odds_data("test_001", "Germany", "Brazil")
    print(f"   模拟数据: {sim['home_team']} vs {sim['away_team']}")
    print(f"   初盘: {sim['opening']}")
    print(f"   终盘: {sim['closing']}")

    # 保存数据
    print("\n" + "=" * 60)
    tracker.save_to_file()
