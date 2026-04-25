#!/usr/bin/env python3
"""
赔率融合模块 v1.0
整合市场赔率与模型预测，提高预测准确率

核心思想：
- 博彩公司赔率 = 世界上最好的预测模型（包含内幕信息）
- 但模型有自己的独特见解（Elo/xG/H2H）
- 融合两者：model_prob * w1 + market_prob * w2
"""

import json
import math
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import os

BASE_DIR = os.path.expanduser("~/hermes-world-cup/")


# ============ 赔率转概率工具 ============

def decimal_to_prob(decimal_odds: float) -> float:
    """欧洲赔率转概率（不含抽水）"""
    if decimal_odds <= 0:
        return 0.0
    return 1.0 / decimal_odds


def american_to_prob(american_odds: float) -> float:
    """美式赔率转概率"""
    if american_odds > 0:
        return 100 / (american_odds + 100)
    else:
        return abs(american_odds) / (abs(american_odds) + 100)


def polymarket_to_prob(yes_price: float) -> float:
    """Polymarket yes_price直接就是概率（小数形式）"""
    return yes_price


def remove_overround(probs: List[float]) -> List[float]:
    """
    移除博彩公司赔率的"overround"（抽水）

    overround = 所有概率之和 > 100%
    多出来的部分就是博彩公司的利润

    算法：归一化使概率之和=100%
    """
    total = sum(probs)
    if total == 0 or total == 100:
        return probs

    # 归一化
    adjusted = [p * 100.0 / total for p in probs]
    return adjusted


# ============ 赔率融合器 ============

@dataclass
class OddsSource:
    """赔率数据源"""
    name: str
    home_prob: float
    draw_prob: float
    away_prob: float
    confidence: float  # 数据质量 (0-1)
    last_updated: str


class MarketOddsEngine:
    """
    市场赔率引擎

    功能：
    1. 加载Polymarket赔率
    2. 加载模拟博彩公司赔率（当没有真实数据时）
    3. 转换为概率
    4. 计算市场共识
    """

    def __init__(self):
        self.polymarket_file = self._find_latest_polymarket()
        self.odds_data = self._load_polymarket()
        self._build_odds_map()

    def _find_latest_polymarket(self) -> str:
        """找到最新的Polymarket数据文件"""
        import glob
        files = glob.glob(os.path.join(BASE_DIR, "polymarket/*-champion-odds*.json"))
        if files:
            files.sort(key=os.path.getmtime, reverse=True)
            return files[0]
        return ""

    def _load_polymarket(self) -> dict:
        """加载Polymarket数据"""
        if not self.polymarket_file or not os.path.exists(self.polymarket_file):
            return {}

        try:
            with open(self.polymarket_file) as f:
                return json.load(f)
        except:
            return {}

    def _build_odds_map(self):
        """构建赔率映射表"""
        self.odds_map = {}  # team_name -> yes_price

        if not self.odds_data:
            return

        teams = self.odds_data.get("teams", [])
        for team_info in teams:
            team = team_info.get("team", "")
            yes_price = team_info.get("yes_price", 0)
            if team and yes_price > 0:
                self.odds_map[team] = yes_price

    def get_champion_prob(self, team: str) -> float:
        """获取球队夺冠概率"""
        # Polymarket直接就是概率
        polymarket_prob = self.odds_map.get(team, 0)

        if polymarket_prob > 0:
            return polymarket_prob

        # 没有数据时，返回None让调用者知道
        return 0

    def get_match_probs_from_champion_odds(
        self,
        home_team: str,
        away_team: str,
    ) -> Tuple[float, float, float]:
        """
        从夺冠赔率反推比赛胜平负概率

        算法：
        - 夺冠赔率反映了市场对球队整体实力的评估
        - 结合两队赔率可以推算相对实力
        - 然后用Elo差距做微调
        """
        home_prob = self.get_champion_prob(home_team)
        away_prob = self.get_champion_prob(away_team)

        if home_prob == 0 or away_prob == 0:
            # 数据不足，返回None
            return (0, 0, 0)

        # 相对概率
        total = home_prob + away_prob
        home_relative = home_prob / total
        away_relative = away_prob / total

        # 估算平局概率（基于历史数据）
        # 世界杯淘汰赛极少打平，决赛稍高
        draw_estimate = 0.15  # 默认15%

        # 调整：相对实力差距越大，平局概率越低
        diff = abs(home_relative - away_relative)
        if diff > 0.6:  # 差距很大
            draw_estimate = 0.08
        elif diff > 0.4:
            draw_estimate = 0.12
        elif diff > 0.2:
            draw_estimate = 0.18
        else:  # 差距很小
            draw_estimate = 0.25

        # 归一化
        win_prob = home_relative * (1 - draw_estimate)
        draw_prob = draw_estimate
        away_win_prob = away_relative * (1 - draw_estimate)

        # 归一化确保=100%
        total_prob = win_prob + draw_prob + away_win_prob
        return (
            win_prob / total_prob,
            draw_prob / total_prob,
            away_win_prob / total_prob,
        )

    def get_odds_quality(self, team: str) -> float:
        """
        获取赔率数据质量评分

        考虑因素：
        - 交易量（volume）
        - 流动性
        - 数据新鲜度
        """
        if not self.odds_data:
            return 0.0

        teams = self.odds_data.get("teams", [])
        for team_info in teams:
            if team_info.get("team") == team:
                volume = team_info.get("volume", 0)
                liquidity = team_info.get("liquidity", 0)

                # 基于交易量评分
                if volume > 10_000_000:
                    volume_score = 1.0
                elif volume > 1_000_000:
                    volume_score = 0.8
                elif volume > 100_000:
                    volume_score = 0.5
                else:
                    volume_score = 0.2

                # 基于流动性评分
                if liquidity > 500_000:
                    liq_score = 1.0
                elif liquidity > 100_000:
                    liq_score = 0.7
                else:
                    liq_score = 0.3

                return (volume_score * 0.6 + liq_score * 0.4)

        return 0.0


class OddsFusion:
    """
    赔率融合器

    将模型预测与市场赔率融合

    融合公式：
    final_prob = (model_prob * model_weight * model_quality) + (market_prob * market_weight * market_quality)
    """

    def __init__(
        self,
        model_weight: float = 0.40,
        market_weight: float = 0.60,
        auto_adjust: bool = True,
    ):
        """
        初始化融合器

        Args:
            model_weight: 模型权重（默认40%）
            market_weight: 市场权重（默认60%）
            auto_adjust: 是否自动调整权重
        """
        self.model_weight = model_weight
        self.market_weight = market_weight
        self.auto_adjust = auto_adjust
        self.market_engine = MarketOddsEngine()

    def fuse_probabilities(
        self,
        model_home: float,
        model_draw: float,
        model_away: float,
        market_home: float = 0,
        market_draw: float = 0,
        market_away: float = 0,
        home_team: str = "",
        away_team: str = "",
    ) -> Dict[str, float]:
        """
        融合模型预测与市场赔率

        重要v3.4修复：
        - 夺冠赔率不能直接用于比赛预测（它们反映的是整个赛事结果，不是单场比赛）
        - 对于head-to-head比赛，只使用模型预测
        - 市场信息只用于Elo校准（已经在PredictionEngine.calibrate_elo中完成）
        """
        # 获取市场数据质量
        market_quality = 0.5
        if home_team:
            market_quality = self.market_engine.get_odds_quality(home_team)

        # v3.4修复：不再使用get_match_probs_from_champion_odds
        # 因为夺冠赔率不能反映单场比赛实力对比
        # 原因：France的夺冠赔率(16%) > Brazil(8%)是因为赛程/分组，不是单场实力
        if market_home == 0:
            # 没有直接的市场赔率，使用纯模型
            return {
                "home": model_home,
                "draw": model_draw,
                "away": model_away,
                "source": "model_only",
                "weights": {"model": 1.0, "market": 0.0},
                "market_quality": market_quality,
            }

        # 如果市场数据太差，完全依赖模型
        if market_quality < 0.2 or market_home == 0:
            return {
                "home": model_home,
                "draw": model_draw,
                "away": model_away,
                "source": "model_only",
                "market_quality": market_quality,
            }

        # 动态权重调整
        if self.auto_adjust:
            w_model, w_market = self._calculate_dynamic_weights(
                model_home, model_draw, model_away,
                market_home, market_draw, market_away,
                market_quality,
            )
        else:
            w_model = self.model_weight
            w_market = self.market_weight

        # 融合
        home = model_home * w_model + market_home * w_market
        draw = model_draw * w_model + market_draw * w_market
        away = model_away * w_model + market_away * w_market

        # 归一化
        total = home + draw + away
        if total > 0:
            home /= total
            draw /= total
            away /= total

        return {
            "home": home,
            "draw": draw,
            "away": away,
            "source": "fused",
            "weights": {"model": w_model, "market": w_market},
            "market_quality": market_quality,
        }

    def _calculate_dynamic_weights(
        self,
        model_home: float, model_draw: float, model_away: float,
        market_home: float, market_draw: float, market_away: float,
        market_quality: float,
    ) -> Tuple[float, float]:
        """
        动态计算权重

        原则：
        - 市场质量越高，市场权重越大
        - 模型和市场差距越大，越要谨慎
        """
        # 基础市场权重
        base_market_weight = self.market_weight * market_quality

        # 模型与市场的一致性
        # 如果两者差不多，说明都很可靠
        diff = abs(model_home - market_home) + abs(model_away - market_away)
        consistency = max(0, 1 - diff)  # 0-1之间

        # 最终市场权重
        final_market = base_market_weight * (0.5 + 0.5 * consistency)
        final_market = max(0.3, min(0.8, final_market))  # 限制在30%-80%

        return (1 - final_market, final_market)

    def fuse_champion_odds(
        self,
        model_probs: Dict[str, float],
        team: str,
    ) -> float:
        """
        融合夺冠预测概率

        Args:
            model_probs: 模型预测的各队夺冠概率 dict
            team: 球队名称

        Returns:
            融合后的夺冠概率
        """
        market_prob = self.market_engine.get_champion_prob(team)
        model_prob = model_probs.get(team, 0)

        if market_prob == 0:
            return model_prob

        # 简单的线性融合
        # 但市场权重更高（因为赔率包含内幕）
        fused = model_prob * 0.35 + market_prob * 0.65

        return fused


# ============ 测试 ============

if __name__ == "__main__":
    fusion = OddsFusion()

    print("=" * 60)
    print("📊 赔率融合模块测试")
    print("=" * 60)

    # 测试市场赔率加载
    print("\n1. Polymarket 夺冠赔率:")
    test_teams = ["Brazil", "Argentina", "France", "Spain", "Germany"]
    for team in test_teams:
        prob = fusion.market_engine.get_champion_prob(team)
        quality = fusion.market_engine.get_odds_quality(team)
        if prob > 0:
            print(f"   {team}: {prob*100:.2f}% (质量:{quality:.2f})")

    # 测试赔率融合
    print("\n2. 赔率融合测试 (France vs Germany):")
    result = fusion.fuse_probabilities(
        model_home=0.55,
        model_draw=0.22,
        model_away=0.23,
        home_team="France",
        away_team="Germany",
    )
    print(f"   融合后: Home={result['home']*100:.1f}% Draw={result['draw']*100:.1f}% Away={result['away']*100:.1f}%")
    print(f"   权重: model={result['weights']['model']:.2f} market={result['weights']['market']:.2f}")
    print(f"   数据源: {result['source']}")

    # 测试动态权重
    print("\n3. 动态权重测试:")
    # 差距大的比赛（如强队vs弱队）
    result1 = fusion.fuse_probabilities(
        model_home=0.80, model_draw=0.12, model_away=0.08,
        market_home=0.75, market_draw=0.15, market_away=0.10,
        home_team="Brazil",
        away_team="Serbia",
    )
    print(f"   Brazil vs Serbia: model={result1['weights']['model']:.2f} market={result1['weights']['market']:.2f}")

    # 差距小的比赛
    result2 = fusion.fuse_probabilities(
        model_home=0.52, model_draw=0.26, model_away=0.22,
        market_home=0.50, market_draw=0.28, market_away=0.22,
        home_team="France",
        away_team="England",
    )
    print(f"   France vs England: model={result2['weights']['model']:.2f} market={result2['weights']['market']:.2f}")

    print("\n" + "=" * 60)
