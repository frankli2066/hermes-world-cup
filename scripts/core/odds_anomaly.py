#!/usr/bin/env python3
"""
赔率异常检测模块 v1.0
=====================
检测赔率的异常波动，挖掘庄家知道的信息

核心功能：
1. 赔率变化检测：赛前赔率大幅波动通常有内幕
2. 异常赔率识别：偏离正常范围的赔率
3. 凯利指数计算：最优下注比例
4. 庄家意图分析：识别赔率背后的信息
"""

import os
import json
import math
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional

# ============ 路径配置 ============
BASE_DIR = os.path.expanduser("~/hermes-world-cup/")
DATA_DIR = os.path.join(BASE_DIR, "data/")


class OddsAnomalyDetector:
    """
    赔率异常检测器

    庄家赔率包含大量信息：
    - 赔率上升 = 市场看好（庄家有消息）
    - 赔率下降 = 市场看衰
    - 剧烈波动 = 可能有内幕消息或大户投注
    """

    def __init__(self):
        self.data_dir = DATA_DIR
        self.odds_history = self._load_odds_history()

        # 赔率异常阈值
        self.rapid_change_threshold = 0.15  # 15%的赔率变化视为剧烈
        self.suspicious_movement = 0.25      # 25%的变化视为可疑

        # 历史准确率记录
        self.historical_accuracy = self._load_historical_accuracy()

    def _load_odds_history(self) -> Dict:
        """加载赔率历史数据"""
        history_file = os.path.join(self.data_dir, "odds_history.json")
        if os.path.exists(history_file):
            try:
                with open(history_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def _load_historical_accuracy(self) -> Dict:
        """加载历史准确率数据"""
        accuracy_file = os.path.join(self.data_dir, "odds_accuracy.json")
        if os.path.exists(accuracy_file):
            try:
                with open(accuracy_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def save_odds_history(self):
        """保存赔率历史"""
        history_file = os.path.join(self.data_dir, "odds_history.json")
        os.makedirs(os.path.dirname(history_file), exist_ok=True)
        with open(history_file, 'w') as f:
            json.dump(self.odds_history, f, ensure_ascii=False, indent=2)

    def record_odds(self, match_id: str, odds_data: Dict):
        """记录赔率数据"""
        if match_id not in self.odds_history:
            self.odds_history[match_id] = []

        odds_data['timestamp'] = datetime.now().isoformat()
        self.odds_history[match_id].append(odds_data)

    def odds_to_probability(self, odds: float) -> float:
        """赔率转换为隐含概率"""
        if odds <= 0:
            return 0
        # 简化：概率 = 1 / 赔率
        implied_prob = 1 / odds
        # 归一化（vig/juice考虑）
        # 通常庄家抽5%左右
        vig = 0.05
        fair_prob = implied_prob * (1 - vig)
        return fair_prob

    def probability_to_odds(self, prob: float) -> float:
        """概率转换为赔率"""
        if prob <= 0:
            return 0
        return 1 / prob

    def calculate_kelly_criterion(self,
                                   prob: float,
                                   odds: float,
                                   fraction: float = 1.0) -> float:
        """
        计算凯利指数（最优下注比例）

        Args:
            prob: 预测概率
            odds: 赔率
            fraction: 凯利分数（通常用1/2或1/3凯利降低风险）

        Returns:
            建议下注比例（0-1之间）
        """
        if odds <= 0 or prob <= 0:
            return 0

        # 凯利公式: f* = (bp - q) / b
        # b = 赔率 - 1
        # p = 获胜概率
        # q = 失败概率 = 1 - p

        b = odds - 1
        p = prob
        q = 1 - p

        kelly = (b * p - q) / b

        # 应用凯利分数（降低风险）
        kelly = kelly * fraction

        # 限制范围
        return max(0, min(kelly, 0.25))  # 最多下注25%

    def detect_odds_movement(self, match_id: str) -> Dict:
        """
        检测赔率变动

        Args:
            match_id: 比赛ID

        Returns:
            赔率变动分析
        """
        if match_id not in self.odds_history or len(self.odds_history[match_id]) < 2:
            return {"status": "insufficient_data"}

        history = self.odds_history[match_id]

        # 获取最新和最早的赔率
        latest = history[-1]
        earliest = history[0]

        # 计算变化率
        changes = {}
        for key in ['home', 'draw', 'away']:
            if key in latest and key in earliest:
                latest_odds = latest[key]
                earliest_odds = earliest[key]

                if earliest_odds > 0:
                    change_pct = (latest_odds - earliest_odds) / earliest_odds
                    changes[key] = {
                        "from": earliest_odds,
                        "to": latest_odds,
                        "change_pct": change_pct,
                        "direction": "up" if change_pct > 0 else "down"
                    }

        # 分析整体趋势
        avg_change = sum(c['change_pct'] for c in changes.values()) / len(changes)

        # 识别异常
        anomalies = []
        for key, change in changes.items():
            if abs(change['change_pct']) > self.rapid_change_threshold:
                anomalies.append({
                    "market": key,
                    "change": change,
                    "severity": "rapid" if abs(change['change_pct']) < self.suspicious_movement else "suspicious"
                })

        return {
            "match_id": match_id,
            "changes": changes,
            "average_change": avg_change,
            "anomalies": anomalies,
            "has_significant_movement": len(anomalies) > 0,
            "latest_update": latest.get('timestamp'),
            "time_span_hours": len(history)  # 简化
        }

    def analyze_odds_anomaly(self,
                             home_odds: float,
                             draw_odds: float,
                             away_odds: float,
                             model_home_prob: float,
                             model_draw_prob: float,
                             model_away_prob: float,
                             market_home_prob: float = None,
                             market_draw_prob: float = None,
                             market_away_prob: float = None) -> Dict:
        """
        分析赔率异常

        Args:
            home_odds: 主队赔率
            draw_odds: 平局赔率
            away_odds: 客队赔率
            model_home_prob: 模型预测主队胜率
            model_draw_prob: 模型预测平局概率
            model_away_prob: 模型预测客队胜率
            market_*: 市场隐含概率（可选）

        Returns:
            异常分析报告
        """
        # 从赔率计算隐含概率
        implied_home = self.odds_to_probability(home_odds)
        implied_draw = self.odds_to_probability(draw_odds)
        implied_away = self.odds_to_probability(away_odds)

        # 归一化
        total_implied = implied_home + implied_draw + implied_away
        if total_implied > 0:
            implied_home /= total_implied
            implied_draw /= total_implied
            implied_away /= total_implied

        # 如果没有提供市场概率，使用隐含概率
        if market_home_prob is None:
            market_home_prob = implied_home
            market_draw_prob = implied_draw
            market_away_prob = implied_away

        # 计算模型与赔率的偏差
        home_deviation = model_home_prob - market_home_prob
        draw_deviation = model_draw_prob - market_draw_prob
        away_deviation = model_away_prob - market_away_prob

        # 检测异常
        anomalies = []

        # 1. 赔率大幅偏离模型
        if abs(home_deviation) > 0.15:
            anomalies.append({
                "type": "significant_deviation",
                "market": "home",
                "deviation": home_deviation,
                "interpretation": "庄家对主队更有信心" if home_deviation < 0 else "庄家对主队信心不足"
            })

        if abs(away_deviation) > 0.15:
            anomalies.append({
                "type": "significant_deviation",
                "market": "away",
                "deviation": away_deviation,
                "interpretation": "庄家对客队更有信心" if away_deviation < 0 else "庄家对客队信心不足"
            })

        # 2. 赔率异常（远低于或远高于预期）
        # 低赔率（<1.5）通常很准，高赔率（>4.0）需要小心
        if home_odds < 1.5:
            reliability = "high"
        elif home_odds < 2.0:
            reliability = "medium"
        elif home_odds < 3.0:
            reliability = "low"
        else:
            reliability = "very_low"

        # 3. 计算价值赌注（Value Bet）
        # 如果模型概率 > 市场概率，说明有价值
        value_bets = []
        for market, model_prob, market_prob, odds in [
            ("home", model_home_prob, market_home_prob, home_odds),
            ("draw", model_draw_prob, market_draw_prob, draw_odds),
            ("away", model_away_prob, market_away_prob, away_odds)
        ]:
            if model_prob > market_prob + 0.05:  # 模型概率超过市场5%以上
                expected_value = (odds * model_prob) - 1
                kelly = self.calculate_kelly_criterion(model_prob, odds, fraction=0.5)

                value_bets.append({
                    "market": market,
                    "model_prob": model_prob,
                    "market_prob": market_prob,
                    "odds": odds,
                    "edge": model_prob - market_prob,
                    "expected_value": expected_value,
                    "kelly_recommendation": kelly,
                    "recommendation": "BET" if kelly > 0.05 else "SKIP"
                })

        # 4. 综合判断
        # 如果庄家赔率与模型差异大，跟随还是反向？
        market_wins_home = market_home_prob > max(market_draw_prob, market_away_prob)
        model_wins_home = model_home_prob > max(model_draw_prob, model_away_prob)

        consensus_signal = "follow_market" if market_wins_home != model_wins_home else "align"

        # 市场与模型一致时信号更强
        confidence_boost = 0.05 if consensus_signal == "align" else -0.05

        return {
            "implied_probabilities": {
                "home": implied_home,
                "draw": implied_draw,
                "away": implied_away
            },
            "deviations": {
                "home": home_deviation,
                "draw": draw_deviation,
                "away": away_deviation
            },
            "anomalies": anomalies,
            "value_bets": value_bets,
            "reliability": reliability,
            "consensus_signal": consensus_signal,
            "confidence_boost": confidence_boost,
            "interpretation": self._interpret_analysis(
                anomalies, value_bets, consensus_signal, reliability
            )
        }

    def _interpret_analysis(self,
                            anomalies: List,
                            value_bets: List,
                            consensus: str,
                            reliability: str) -> str:
        """解释分析结果"""
        if reliability in ["high"]:
            return "赔率可靠，建议信任市场信号"

        if len(value_bets) > 0:
            strong_value = [b for b in value_bets if b['edge'] > 0.10]
            if strong_value:
                return f"发现价值赌注: {strong_value[0]['market']} (信心充足)"

        if consensus == "follow_market":
            return "市场与模型分歧，建议跟随市场"

        if len(anomalies) > 0:
            return f"发现{len(anomalies)}个异常，需要谨慎"

        return "赔率正常，无明显异常"

    def get_handicap_adjustment(self,
                                 handicap_odds: float,
                                 team: str,
                                 actual_handicap: float = 0) -> Dict:
        """
        让球盘分析

        Args:
            handicap_odds: 让球盘赔率
            team: 球队名称
            actual_handicap: 实际让球数

        Returns:
            让球盘调整建议
        """
        # 从让球盘赔率推断市场对球队的信心
        implied_prob = self.odds_to_probability(handicap_odds)

        # 让球盘概率转换为让球优势
        # 如果一队在让球盘上概率高，说明市场认为他们能赢下让球
        handicap_advantage = (implied_prob - 0.5) * 2  # 转换为让球优势

        return {
            "team": team,
            "handicap": actual_handicap,
            "market_implied_prob": implied_prob,
            "market_handicap_advantage": handicap_advantage,
            "interpretation": self._interpret_handicap(implied_prob, actual_handicap)
        }

    def _interpret_handicap(self, prob: float, handicap: float) -> str:
        """解释让球盘"""
        if prob > 0.6:
            if handicap > 0:
                return f"市场看好该队能赢{handicap}球以上"
            else:
                return "市场明显看好该队"
        elif prob > 0.5:
            return "市场略看好该队"
        else:
            return "市场不看好该队"


# ============ 测试代码 ============
if __name__ == "__main__":
    detector = OddsAnomalyDetector()

    print("=" * 60)
    print("赔率异常检测测试")
    print("=" * 60)

    # 模拟赔率
    home_odds = 2.0
    draw_odds = 3.2
    away_odds = 3.8

    # 模型预测
    model_home = 0.45
    model_draw = 0.25
    model_away = 0.30

    result = detector.analyze_odds_anomaly(
        home_odds, draw_odds, away_odds,
        model_home, model_draw, model_away
    )

    print(f"主队赔率: {home_odds} -> 隐含概率: {result['implied_probabilities']['home']:.1%}")
    print(f"平局赔率: {draw_odds} -> 隐含概率: {result['implied_probabilities']['draw']:.1%}")
    print(f"客队赔率: {away_odds} -> 隐含概率: {result['implied_probabilities']['away']:.1%}")
    print()

    print(f"模型预测: 主队 {model_home:.1%} | 平局 {model_draw:.1%} | 客队 {model_away:.1%}")
    print(f"市场偏差: 主队 {result['deviations']['home']:+.1%} | 平局 {result['deviations']['draw']:+.1%} | 客队 {result['deviations']['away']:+.1%}")
    print()

    if result['value_bets']:
        print("发现价值赌注:")
        for bet in result['value_bets']:
            print(f"  {bet['market']}: 模型{bet['model_prob']:.1%} vs 市场{bet['market_prob']:.1%}")
            print(f"    赔率: {bet['odds']}, 凯利指数: {bet['kelly_recommendation']:.1%}")
            print(f"    建议: {bet['recommendation']}")
    else:
        print("未发现明显价值赌注")

    print()
    print(f"赔率可靠性: {result['reliability']}")
    print(f"解读: {result['interpretation']}")

    print()
    print("=" * 60)
    print("凯利指数计算示例")
    print("=" * 60)

    # 假设模型认为某队有60%概率胜，赔率是2.1
    kelly = detector.calculate_kelly_criterion(0.60, 2.1, fraction=0.5)
    print(f"概率60%, 赔率2.1, 凯利建议下注: {kelly:.1%}")
    print(f"期望价值: {(2.1 * 0.60) - 1:.2f}")
