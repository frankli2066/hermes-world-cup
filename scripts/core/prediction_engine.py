#!/usr/bin/env python3
"""
核心预测引擎
整合所有模块：Elo评分、xG模型、H2H、数据管道
为淘汰赛模拟器提供统一的预测接口
"""

import json
import os
import random
from datetime import datetime
from typing import Dict, List, Tuple, Optional

# 导入本地模块（支持 core/ 和脚本根目录两种导入方式）
try:
    from core.team_stats import TeamRating, EloSystem, HeadToHead
    from core.xg_model import DynamicxGModel, xGModel
    from core.data_pipeline import DataPipeline
    from core.ml_calibrator import WeightCalibrator
    from core.odds_fusion import OddsFusion, MarketOddsEngine
    from core.player_impact import PlayerImpactEvaluator
    from core.match_stage import MatchStageAdjuster
    from core.elo_calibrator import EloCalibrator
    from core.knockout_model import KnockoutModel
    from core.realtime_data import RealTimeData, get_realtime_data
    from core.match_odds import MatchOddsEngine, get_market_consensus
except ModuleNotFoundError:
    from team_stats import TeamRating, EloSystem, HeadToHead
    from xg_model import DynamicxGModel, xGModel
    from data_pipeline import DataPipeline
    from ml_calibrator import WeightCalibrator
    from odds_fusion import OddsFusion, MarketOddsEngine
    from player_impact import PlayerImpactEvaluator
    from match_stage import MatchStageAdjuster
    from elo_calibrator import EloCalibrator
    from knockout_model import KnockoutModel
    from realtime_data import RealTimeData, get_realtime_data
    from match_odds import MatchOddsEngine, get_market_consensus

# ============ 路径配置 ============
BASE_DIR = os.path.expanduser("~/hermes-world-cup/")
OUTPUT_DIR = os.path.join(BASE_DIR, "data/")
os.makedirs(OUTPUT_DIR, exist_ok=True)


class PredictionEngine:
    """
    核心预测引擎

    整合所有数据源和模型，提供统一的预测接口
    """

    def __init__(self, use_live_data: bool = True):
        """
        初始化预测引擎

        Args:
            use_live_data: 是否使用实时数据（False则使用缓存）
        """
        print("🚀 初始化预测引擎...")

        # 初始化各模块
        self.team_stats = TeamRating()
        self.xg_model = DynamicxGModel()  # v6.0动态xG模型
        self.pipeline = DataPipeline(use_cache=not use_live_data)

        # 校准器（获取最优权重）
        self.calibrator = WeightCalibrator()
        self.weights = self.calibrator.get_optimal_weights()
        print(f"   权重: Elo={self.weights['elo_weight']:.0%} "
              f"FIFA={self.weights['fifa_weight']:.0%} "
              f"Form={self.weights['form_weight']:.0%} "
              f"Exp={self.weights['experience_weight']:.0%}")

        # 如果使用实时数据，先加载Polymarket赔率
        if use_live_data:
            self._load_live_data()

        # 赔率融合引擎（整合市场赔率与模型预测）
        self.odds_fusion = OddsFusion(
            model_weight=0.40,
            market_weight=0.60,
            auto_adjust=True,
        )

        # 球员影响评估器（v3.3新增）
        self.player_impact = PlayerImpactEvaluator()

        # 比赛阶段调整器（v3.3新增）
        self.match_stage = MatchStageAdjuster()

        # 淘汰赛模型（v4.0新增）
        self.knockout_model = KnockoutModel()

        # 实时数据模块（v4.0新增）
        self.realtime_data = get_realtime_data()
        self.realtime_data.initialize_world_cup_data()

        # 比赛赔率引擎（v4.3新增）- 真实赔率数据
        self.match_odds = MatchOddsEngine()

        # Elo校准器（v3.4新增）- 用市场赔率校准Elo
        self.elo_calibrator = None
        self._elo_calibrated = False

        print("✅ 预测引擎初始化完成\n")

    def _load_live_data(self):
        """加载实时数据"""
        try:
            pm_data = self.pipeline.fetch_polymarket_champion_odds()
            if pm_data and pm_data.get("teams"):
                print(f"   Polymarket: {len(pm_data['teams'])} 支球队")
        except Exception as e:
            print(f"   Polymarket加载失败: {e}")

    def calibrate_elo(self, learning_rate: float = 0.3) -> bool:
        """
        用Polymarket市场赔率校准Elo（v3.4新增）

        Args:
            learning_rate: 调整速度（0-1），默认0.3

        Returns:
            是否成功
        """
        pm_data = self.pipeline.fetch_polymarket_champion_odds()
        if not pm_data or not pm_data.get("teams"):
            print("⚠️ 没有Polymarket数据，无法校准Elo")
            return False

        print("🔧 开始Elo校准（基于市场赔率）...")

        # 创建校准器
        self.elo_calibrator = EloCalibrator(self.team_stats.elo, pm_data)

        # 执行校准
        calibrated = self.elo_calibrator.calibrate(learning_rate)

        # 打印对比
        self.elo_calibrator.print_comparison(top_n=10)

        # 应用校准
        self.elo_calibrator.apply_calibration()
        self._elo_calibrated = True

        print(f"✅ Elo校准完成！调整了 {len(calibrated)} 支球队的评分")
        return True

    def predict_match(self, home_team: str, away_team: str,
                     monte_carlo: int = 10000,
                     use_adjustments: bool = True,
                     home_missing: list = None,
                     away_missing: list = None,
                     match_stage: str = "group",
                     neutral_venue: bool = False) -> Dict:
        """
        预测单场比赛

        Args:
            home_team: 主队
            away_team: 客队
            monte_carlo: 蒙特卡洛模拟次数
            use_adjustments: 是否使用附加调整
            home_missing: 主队缺阵球员列表（如["Mbappe", "Kante"]）
            away_missing: 客队缺阵球员列表
            match_stage: 比赛阶段
                - "group": 小组赛
                - "round_of_16": 16强
                - "quarter": 8强
                - "semi": 半决赛
                - "third_place": 三四名决赛
                - "final": 决赛
            neutral_venue: 是否是中立场地（决赛/世界杯中立场）
                - True: 关闭主场优势
                - False: 正常主场优势

        Returns:
            完整预测结果
        """
        # 获取球队对比
        comparison = self.team_stats.compare_teams(home_team, away_team)

        # 使用真实的Elo差距（用于xG调整）
        home_elo = self.team_stats.elo.get_rating(home_team)
        away_elo = self.team_stats.elo.get_rating(away_team)
        elo_diff = home_elo - away_elo  # 真实Elo差距

        # xG模型预测
        xg_result = self.xg_model.simulate_score(
            home_team, away_team,
            elo_diff=elo_diff,  # 直接使用Elo差距，不需要乘10
            monte_carlo=monte_carlo,
            neutral_venue=neutral_venue,  # v4.1: 中立场地处理
        )

        # ============ 比赛阶段xG调整（v3.3新增） ============
        # 决赛/淘汰赛进球数普遍偏低
        adj_xg = self.match_stage.adjust_xg(
            xg_result["home_xg"],
            xg_result["away_xg"],
            match_stage
        )
        xg_result["home_xg"] = adj_xg[0]
        xg_result["away_xg"] = adj_xg[1]

        # 获取H2H数据
        h2h_data = self.team_stats.h2h.get_h2h(home_team, away_team)

        # 获取伤病信息
        home_injuries = self.pipeline.fetch_injuries(home_team)
        away_injuries = self.pipeline.fetch_injuries(away_team)

        # ============ 球员影响评估（v3.3新增） ============
        # 评估核心球员缺阵对比赛的影响
        player_impact = None
        if home_missing or away_missing:
            player_impact = self.player_impact.compare_teams_with_impact(
                home_team, away_team,
                home_missing=home_missing or [],
                away_missing=away_missing or [],
            )

        # ============ v4.2 动态权重调整 ============
        # 根据Elo差距调整各因子权重
        abs_elo_diff = abs(elo_diff)

        if abs_elo_diff > 250:
            # 差距极大时，更多依赖Elo/xG，其他因子权重降低
            xg_weight = 0.60
            comp_weight = 0.35
            h2h_weight = 0.05
        elif abs_elo_diff > 150:
            # 差距较大时，Elo/xG为主
            xg_weight = 0.55
            comp_weight = 0.38
            h2h_weight = 0.07
        elif abs_elo_diff > 75:
            # 中等差距，均衡权重
            xg_weight = 0.50
            comp_weight = 0.40
            h2h_weight = 0.10
        else:
            # 差距较小，考虑更多因素
            xg_weight = 0.45
            comp_weight = 0.40
            h2h_weight = 0.15

        # 综合预测
        prob_home_raw = (
            xg_result["prob_home_win"] * xg_weight +
            comparison["win_prob_a"] * comp_weight +
            (0.5 if not h2h_data else 0.5 + h2h_data.get("wins_a", 0) /
             max(h2h_data.get("games", 1), 1) * 0.5 - 0.25) * h2h_weight
        )
        prob_away_raw = (
            xg_result["prob_away_win"] * xg_weight +
            comparison["win_prob_b"] * comp_weight +
            (0.5 if not h2h_data else 0.5 + h2h_data.get("wins_b", 0) /
             max(h2h_data.get("games", 1), 1) * 0.5 - 0.25) * h2h_weight
        )

        # 胜平负综合（需要合理分配平局概率）
        # 基础模型显示的平局概率
        base_draw = xg_result.get("prob_draw", 0.25)

        # 最终概率（使用原始胜/负概率，假设平局概率在两者之间）
        model_prob_home = prob_home_raw * (1 - base_draw * 0.5)
        model_prob_away = prob_away_raw * (1 - base_draw * 0.5)
        model_prob_draw = base_draw

        # ============ 赔率融合 ============
        # 使用市场赔率校准概率（关键优化！）
        # 市场赔率包含内幕信息，权重更高(60%)
        fused = self.odds_fusion.fuse_probabilities(
            model_home=model_prob_home,
            model_draw=model_prob_draw,
            model_away=model_prob_away,
            home_team=home_team,
            away_team=away_team,
        )

        # 融合后的概率
        final_prob_home = fused["home"]
        final_prob_away = fused["away"]
        final_prob_draw = fused["draw"]
        fusion_info = {
            "source": fused.get("source", "unknown"),
            "market_quality": fused.get("market_quality", 0),
            "weights": fused.get("weights", {}),
        }

        # ============ v4.1 平局概率校准 ============
        # 实际世界杯平局概率约25%，但模型通常偏低
        # 根据Elo差距调整：差距越小，平局概率越高
        elo_gap = abs(elo_diff)
        if elo_gap < 100:
            # 差距小，增加平局概率
            draw_boost = 0.03
        elif elo_gap < 200:
            draw_boost = 0.02
        elif elo_gap < 300:
            draw_boost = 0.01
        else:
            draw_boost = 0.0
        
        if draw_boost > 0:
            total_before = final_prob_home + final_prob_away + final_prob_draw
            final_prob_draw = min(0.35, final_prob_draw + draw_boost)
            remaining = total_before - final_prob_draw
            if remaining > 0:
                scale = (total_before - final_prob_draw) / (final_prob_home + final_prob_away)
                final_prob_home *= scale
                final_prob_away *= scale
        
        # ============ v4.1 弱队主场压力调整 ============
        # 弱队主场（Elo差>100）往往因为压力表现不佳
        if not neutral_venue and elo_diff > 100:
            # 主队强，不需要调整
            pass
        elif not neutral_venue and elo_diff < -100:
            # 弱队主场 - 降低主队胜率
            pressure_factor = min(0.08, abs(elo_diff) / 2000)  # 最多降低8%
            home_loss = final_prob_home * pressure_factor
            final_prob_home -= home_loss
            final_prob_draw += home_loss * 0.6
            final_prob_away += home_loss * 0.4

        # 归一化
        total = final_prob_home + final_prob_away + final_prob_draw
        if total > 0:
            final_prob_home /= total
            final_prob_away /= total
            final_prob_draw /= total

        # ============ v4.1 Elo差距100-200区间优化 ============
        # 这个区间的比赛最难预测，强队胜率被高估
        # 实际这个区间弱队胜率约38-40%，不是模型预测的45-55%
        if 100 <= abs(elo_diff) <= 200:
            # 计算强队被高估的程度
            stronger_prob = max(final_prob_home, final_prob_away)
            weaker_prob = min(final_prob_home, final_prob_away)

            # 根据Elo差距设定不同的目标
            if abs(elo_diff) >= 150:
                # 150-200区间：目标强队概率更低
                target_stronger = 0.42
            else:
                # 100-150区间：目标强队概率适中
                target_stronger = 0.45

            # 如果强队概率超过目标，向目标回归
            if stronger_prob > target_stronger:
                # 回归系数：0.20表示保留20%的高估，80%回归均值
                regression = 0.20
                target_weaker = 1.0 - target_stronger - final_prob_draw

                # 调整
                stronger_adj = (stronger_prob - target_stronger) * regression
                weaker_adj = (target_weaker - weaker_prob) * regression

                if final_prob_home > final_prob_away:
                    final_prob_home -= stronger_adj
                    final_prob_away += weaker_adj
                else:
                    final_prob_away -= stronger_adj
                    final_prob_home += weaker_adj

                # 归一化
                total = final_prob_home + final_prob_away + final_prob_draw
                if total > 0:
                    final_prob_home /= total
                    final_prob_away /= total
                    final_prob_draw /= total

        # ============ v4.2 淘汰赛保平策略 ============
        # 淘汰赛球队倾向于保守，平局概率应该更高
        if match_stage in ["quarter", "semi", "final"] and final_prob_draw < 0.20:
            # 淘汰赛最低平局概率20%
            draw_floor = 0.20 if match_stage == "final" else 0.18
            if final_prob_draw < draw_floor:
                deficit = draw_floor - final_prob_draw
                final_prob_draw = draw_floor
                # 从胜/负概率中扣除
                if final_prob_home > final_prob_away:
                    final_prob_away -= deficit * 0.3
                    final_prob_home -= deficit * 0.7
                else:
                    final_prob_home -= deficit * 0.3
                    final_prob_away -= deficit * 0.7
                # 归一化
                total = final_prob_home + final_prob_away + final_prob_draw
                if total > 0:
                    final_prob_home /= total
                    final_prob_away /= total
                    final_prob_draw /= total

        # ============ v4.2 模型一致性校准 ============
        # 当多个模型一致时增强信心，不一致时保守

        # 检查xG和comparison的一致性
        xg_home_better = xg_result["prob_home_win"] > xg_result["prob_away_win"]
        comp_home_better = comparison["win_prob_a"] > comparison["win_prob_b"]

        if xg_home_better == comp_home_better:
            # 模型一致 - 增强信心
            if xg_home_better:
                # 两模型都认为主队更好
                confidence_boost = 0.03
                final_prob_home += confidence_boost
                final_prob_away -= confidence_boost * 0.5
                final_prob_draw -= confidence_boost * 0.5
            else:
                # 两模型都认为客队更好
                confidence_boost = 0.03
                final_prob_away += confidence_boost
                final_prob_home -= confidence_boost * 0.5
                final_prob_draw -= confidence_boost * 0.5
        else:
            # 模型不一致 - 保守，向平局靠拢
            conservative_shift = 0.02
            stronger = max(final_prob_home, final_prob_away)
            weaker = min(final_prob_home, final_prob_away)
            final_prob_draw += conservative_shift
            if final_prob_home > final_prob_away:
                final_prob_home -= conservative_shift * 0.7
                final_prob_away -= conservative_shift * 0.3
            else:
                final_prob_away -= conservative_shift * 0.7
                final_prob_home -= conservative_shift * 0.3

        # 归一化
        total = final_prob_home + final_prob_away + final_prob_draw
        if total > 0:
            final_prob_home /= total
            final_prob_away /= total
            final_prob_draw /= total

        # ============ 球员影响调整（v3.3新增） ============
        # 将球员缺阵影响应用到概率上
        if player_impact:
            home_impact_pct = player_impact["home"]["impact_percent"] / 100
            away_impact_pct = player_impact["away"]["impact_percent"] / 100

            # 调整强度：impact的40%真正影响比赛结果
            adj_strength = 0.4

            # 计算调整因子
            home_adj = 1 - home_impact_pct * adj_strength
            away_adj = 1 - away_impact_pct * adj_strength

            # 应用调整
            # 主队缺阵：主队胜率降低，降低的部分分给客队和平局
            home_loss = final_prob_home * (1 - home_adj)
            away_loss = final_prob_away * (1 - away_adj)

            final_prob_home *= home_adj
            final_prob_away *= away_adj

            # 把损失分配给平局（保守假设）
            # 主队损失 → 平局+部分给客队
            final_prob_draw += home_loss * 0.6
            final_prob_away += home_loss * 0.4

            # 客队损失 → 平局+部分给主队
            final_prob_draw += away_loss * 0.6
            final_prob_home += away_loss * 0.4

            # 归一化
            total = final_prob_home + final_prob_away + final_prob_draw
            if total > 0:
                final_prob_home /= total
                final_prob_away /= total
                final_prob_draw /= total

        # ============ 比赛阶段概率调整（v3.3新增） ============
        # 淘汰赛/决赛：平局概率更高，明星球员影响更大
        if match_stage != "group":
            stage_info = self.match_stage.get_stage(match_stage)
            # 调整平局概率
            base_draw_prob = final_prob_draw
            new_draw_prob = self.match_stage.adjust_draw_probability(
                base_draw_prob, match_stage
            )
            draw_increase = new_draw_prob - base_draw_prob

            if draw_increase > 0:
                # 从胜/负概率中扣除给平局
                total_win_prob = final_prob_home + final_prob_away
                if total_win_prob > 0:
                    home_ratio = final_prob_home / total_win_prob
                    final_prob_draw = new_draw_prob
                    final_prob_home -= draw_increase * home_ratio
                    final_prob_away -= draw_increase * (1 - home_ratio)

                    # 归一化
                    total = final_prob_home + final_prob_away + final_prob_draw
                    if total > 0:
                        final_prob_home /= total
                        final_prob_away /= total
                        final_prob_draw /= total

        # ============ v4.3 真实赔率校准 ============
        # 如果有真实赔率数据，用它来校准最终概率
        # 博彩公司的赔率包含了大量信息和智慧
        market_probs = self.match_odds.get_implied_probs(home_team, away_team)
        if market_probs:
            # 市场概率
            market_home, market_draw, market_away = market_probs

            # 计算模型与市场的一致性
            prob_diff = abs(final_prob_home - market_home) + abs(final_prob_away - market_away)

            # 根据一致性动态调整市场权重
            # 如果模型和市场差距大，相信市场更多
            if prob_diff > 0.15:
                # 差距大，市场权重提高到50%
                market_weight = 0.50
            elif prob_diff > 0.08:
                market_weight = 0.40
            else:
                # 差距小，市场权重35%
                market_weight = 0.35

            # 融合
            final_prob_home = final_prob_home * (1 - market_weight) + market_home * market_weight
            final_prob_away = final_prob_away * (1 - market_weight) + market_away * market_weight
            final_prob_draw = final_prob_draw * (1 - market_weight) + market_draw * market_weight

            # 归一化
            total = final_prob_home + final_prob_away + final_prob_draw
            if total > 0:
                final_prob_home /= total
                final_prob_away /= total
                final_prob_draw /= total

        # 生成预测比分 - 基于综合胜率调整xG比分！
        # 如果综合胜率偏向某一方，需要调整比分预测方向
        home_xg = xg_result["home_xg"]
        away_xg = xg_result["away_xg"]

        # 根据综合胜率调整xG
        if final_prob_home > final_prob_away + 0.05:
            # 主队占优 - 调高主队xG，降低客队xG
            adj_home_xg = home_xg * 1.12
            adj_away_xg = away_xg * 0.88
        elif final_prob_away > final_prob_home + 0.05:
            # 客队占优 - 调高客队xG，降低主队xG
            adj_home_xg = home_xg * 0.88
            adj_away_xg = away_xg * 1.12
        else:
            # 接近的比赛 - 保持原xG
            adj_home_xg = home_xg
            adj_away_xg = away_xg

        # 基于调整后的xG生成预测比分
        import numpy as np
        np.random.seed(None)
        predicted_home_goals = max(0, np.random.poisson(adj_home_xg))
        predicted_away_goals = max(0, np.random.poisson(adj_away_xg))

        # 限制极端比分 - 足球比赛通常不会太大分差
        max_goals = 4  # 最多4个进球
        predicted_home_goals = min(predicted_home_goals, max_goals)
        predicted_away_goals = min(predicted_away_goals, max_goals)

        # 如果综合胜率显示某队明显占优，确保比分方向一致
        if final_prob_home > final_prob_away + 0.1 and predicted_home_goals <= predicted_away_goals:
            # 主队应该赢但采样出平或负，强制调整
            predicted_home_goals = predicted_away_goals + 1
        elif final_prob_away > final_prob_home + 0.1 and predicted_away_goals <= predicted_home_goals:
            predicted_away_goals = predicted_home_goals + 1

        predicted_score = f"{predicted_home_goals}-{predicted_away_goals}"

        # 【v5.3 优化】Elo差距分段预测策略
        # 当Elo差距很小时（极端势均力敌），直接推荐平局
        abs_elo_diff = abs(elo_diff)
        
        if abs_elo_diff < 50:
            # 极端势均力敌比赛：直接推荐平局
            recommendation = "平局"
            confidence = "🔴 低信心"
        elif final_prob_home > 0.45:
            recommendation = home_team
            confidence = "🟢 高信心" if final_prob_home > 0.60 else "🟡 中信心"
        elif final_prob_away > 0.45:
            recommendation = away_team
            confidence = "🟢 高信心" if final_prob_away > 0.60 else "🟡 中信心"
        else:
            recommendation = "平局"
            confidence = "🔴 低信心"

        return {
            "match": f"{home_team} vs {away_team}",
            "timestamp": datetime.now().isoformat(),
            # 比分预测
            "predicted_score": predicted_score,
            "most_likely_score": xg_result["most_likely_score"],
            "most_likely_prob": xg_result["most_likely_prob"],
            # xG数据
            "xg": {
                "home": xg_result["home_xg"],
                "away": xg_result["away_xg"],
                "total": xg_result["expected_total_goals"],
            },
            # 胜率预测
            "win_probability": {
                "home": round(final_prob_home, 3),
                "draw": round(final_prob_draw, 3),
                "away": round(final_prob_away, 3),
            },
            # 基础分析
            "team_strength": {
                "home": comparison["strength_a"],
                "away": comparison["strength_b"],
                "diff": comparison["strength_a"] - comparison["strength_b"],
            },
            # H2H
            "h2h": h2h_data,
            # 伤病
            "injuries": {
                "home": home_injuries,
                "away": away_injuries,
            },
            # 推荐
            "recommendation": recommendation,
            "confidence": confidence,
            # 附加选项
            "over_2_5": round(xg_result["over_2_5_prob"], 3),
            "btts_yes": round(xg_result["btts_yes_prob"], 3),
            "common_scores": xg_result["common_scores"][:3],
            # 蒙特卡洛信息
            "monte_carlo_runs": monte_carlo,
            # 赔率融合信息（v2.0新增）
            "odds_fusion": {
                "source": fusion_info["source"],
                "market_quality": fusion_info["market_quality"],
                "model_weight": fusion_info["weights"].get("model", 0.4),
                "market_weight": fusion_info["weights"].get("market", 0.6),
            },
            # 球员影响评估（v3.3新增）
            "player_impact": player_impact,
        }

    def predict_tournament(self, monte_carlo: int = 1000) -> Dict:
        """
        预测整届世界杯

        运行蒙特卡洛模拟，返回各队夺冠概率
        """
        print("🔮 开始世界杯冠军预测...")

        # 获取所有球队
        teams = list(self.team_stats.elo.ratings.keys())

        # 收集各队综合实力
        team_strengths = {}
        for team in teams:
            team_strengths[team] = self.team_stats.get_team_strength(team)

        # 基于Polymarket冠军赔率调整
        pm_data = self.pipeline.fetch_polymarket_champion_odds()
        pm_probs = {t["team"]: t["prob"] / 100 for t in pm_data.get("teams", [])}

        # 蒙特卡洛模拟
        champion_counts = {team: 0 for team in teams}
        top4_counts = {team: 0 for team in teams}
        group_winners = {}

        for sim in range(monte_carlo):
            if (sim + 1) % 100 == 0:
                print(f"   模拟进度: {sim + 1}/{monte_carlo}")

            # 简化模拟：基于实力+随机因素
            probs = []
            for team in teams:
                base = team_strengths.get(team, 50)
                # 加入Polymarket影响
                pm_factor = pm_probs.get(team, 0.01)
                combined = base * 0.6 + pm_factor * 100 * 0.4
                probs.append(max(0.1, combined))

            total = sum(probs)
            probs = [p / total for p in probs]

            # 随机选择冠军（加权）
            champion = random.choices(teams, weights=probs, k=1)[0]
            champion_counts[champion] += 1

            # Top 4
            top4 = random.choices(teams, weights=probs, k=4)
            for t in top4:
                top4_counts[t] += 1

        # 计算概率
        champion_probs = {t: c / monte_carlo * 100 for t, c in champion_counts.items()}
        top4_probs = {t: c / monte_carlo * 100 / 4 for t, c in top4_counts.items()}

        # 排序
        champion_ranking = sorted(champion_probs.items(), key=lambda x: x[1], reverse=True)
        top4_ranking = sorted(top4_probs.items(), key=lambda x: x[1], reverse=True)

        result = {
            "timestamp": datetime.now().isoformat(),
            "monte_carlo_runs": monte_carlo,
            "champion_prediction": [
                {"rank": i + 1, "team": t, "prob": round(p, 2)}
                for i, (t, p) in enumerate(champion_ranking[:10])
            ],
            "top4_prediction": [
                {"rank": i + 1, "team": t, "prob": round(p, 2)}
                for i, (t, p) in enumerate(top4_ranking[:10])
            ],
        }

        print(f"✅ 模拟完成，共 {monte_carlo} 次")

        return result

    def update_elo_from_result(self, home_team: str, away_team: str,
                               home_goals: int, away_goals: int):
        """根据比赛结果更新Elo评分"""
        is_home_winner = home_goals > away_goals
        is_away_winner = home_goals < away_goals
        is_draw = home_goals == away_goals

        if is_draw:
            self.team_stats.elo.update(home_team, away_team, draw=True)
        elif is_home_winner:
            self.team_stats.elo.update(home_team, away_team, is_home_winner=True)
        else:
            self.team_stats.elo.update(away_team, home_team, is_home_winner=False)

        self.team_stats.elo.save()

        # 更新近期战绩
        self.team_stats.form.add_result(home_team, away_team, home_goals, away_goals,
                                        is_home=True)
        self.team_stats.form.add_result(away_team, home_team, away_goals, home_goals,
                                        is_home=False)
        self.team_stats.form.save()


# ============ 小组赛模拟器（改进版）============

class GroupStageSimulator:
    """小组赛模拟器（使用新的预测引擎）"""

    def __init__(self, engine: PredictionEngine):
        self.engine = engine

    def simulate_group(self, group_name: str, teams: List[str],
                       monte_carlo: int = 5000) -> Dict:
        """
        模拟小组赛

        Args:
            group_name: 组别字母
            teams: 球队列表
            monte_carlo: 模拟次数
        """
        standings_sum = {t: {"Pts": 0, "GD": 0, "GF": 0, "GA": 0, "W": 0, "D": 0, "L": 0}
                         for t in teams}
        qualified_counts = {t: 0 for t in teams}
        group_winner_counts = {t: 0 for t in teams}
        third_place_counts = {t: 0 for t in teams}

        for _ in range(monte_carlo):
            # 模拟所有比赛
            points = {t: 0 for t in teams}
            gd = {t: 0 for t in teams}
            gf = {t: 0 for t in teams}

            for i, home in enumerate(teams):
                for j, away in enumerate(teams):
                    if i >= j:
                        continue

                    # 预测比赛
                    result = self.engine.predict_match(home, away, monte_carlo=1000)
                    home_prob = result["win_probability"]["home"]
                    draw_prob = result["win_probability"]["draw"]
                    # 获取xG模型的比分预测（使用加权随机采样）
                    predicted_score = result["predicted_score"]
                    home_goals, away_goals = map(int, predicted_score.split("-"))

                    # 如果有明确的胜平负概率，使用概率决定结果
                    # 但使用xG模型的比分作为参考
                    home_prob = result["win_probability"]["home"]
                    draw_prob = result["win_probability"]["draw"]
                    away_prob = result["win_probability"]["away"]

                    # 随机决定结果（但更倾向于xG模型的预测方向）
                    rand = random.random()
                    if rand < home_prob:
                        # 主队获胜 - 使用xG比分或1-0
                        points[home] += 3
                        if home_goals > away_goals:
                            gf[home] += home_goals
                            gf[away] += away_goals
                        else:
                            gf[home] += 1
                            gf[away] += 0
                        gd[home] = gf[home] - gf[away]
                        gd[away] = -gd[home]
                    elif rand < home_prob + draw_prob:
                        # 平局 - 使用xG比分或1-1
                        points[home] += 1
                        points[away] += 1
                        if home_goals == away_goals:
                            gf[home] += home_goals
                            gf[away] += away_goals
                        else:
                            gf[home] += 1
                            gf[away] += 1
                        gd[home] = 0
                        gd[away] = 0
                    else:
                        # 客队获胜 - 使用xG比分或0-1
                        points[away] += 3
                        if away_goals > home_goals:
                            gf[away] += away_goals
                            gf[home] += home_goals
                        else:
                            gf[away] += 1
                            gf[home] += 0
                        gd[away] = gf[away] - gf[home]
                        gd[home] = -gd[away]

            # 排序
            sorted_teams = sorted(teams, key=lambda t: (points[t], gd[t], gf[t]), reverse=True)

            # 统计
            for i, t in enumerate(sorted_teams):
                if i < 2:
                    qualified_counts[t] += 1
                if i == 0:
                    group_winner_counts[t] += 1
                if i == 2:
                    third_place_counts[t] += 1

            # 累计积分
            for t in teams:
                standings_sum[t]["Pts"] += points[t]
                standings_sum[t]["GD"] += gd[t]
                standings_sum[t]["GF"] += gf[t]
                standings_sum[t]["GA"] += gf[t] - gd[t]

        # 计算概率
        result = {
            "group": group_name,
            "teams": teams,
            "simulation_runs": monte_carlo,
            "advancement_probability": {},
            "average_standings": {},
        }

        for t in teams:
            result["advancement_probability"][t] = {
                "qualify_prob": round(qualified_counts[t] / monte_carlo * 100, 1),
                "winner_prob": round(group_winner_counts[t] / monte_carlo * 100, 1),
                "third_place_prob": round(third_place_counts[t] / monte_carlo * 100, 1),
            }
            result["average_standings"][t] = {
                "avg_points": round(standings_sum[t]["Pts"] / monte_carlo, 1),
                "avg_gd": round(standings_sum[t]["GD"] / monte_carlo, 1),
                "avg_gf": round(standings_sum[t]["GF"] / monte_carlo, 1),
            }

        return result


# ============ 淘汰赛模拟器（改进版）============

class KnockoutSimulator:
    """淘汰赛模拟器（使用新的预测引擎）"""

    def __init__(self, engine: PredictionEngine):
        self.engine = engine

    def simulate_knockout(self, team_a: str, team_b: str,
                         monte_carlo: int = 10000) -> Dict:
        """模拟淘汰赛（支持加时赛和点球）"""
        a_wins = 0
        b_wins = 0
        a_wins_extra = 0
        b_wins_extra = 0
        a_wins_penalties = 0
        b_wins_penalties = 0

        for _ in range(monte_carlo):
            # 90分钟 - 使用综合胜率决定胜负，而不是随机比分
            result = self.engine.predict_match(team_a, team_b, monte_carlo=500)

            # 使用综合胜率来决定胜负
            home_prob = result["win_probability"]["home"]
            draw_prob = result["win_probability"]["draw"]
            away_prob = result["win_probability"]["away"]

            # 归一化
            total = home_prob + draw_prob + away_prob
            if total > 0:
                home_prob /= total
                draw_prob /= total
                away_prob /= total

            rand = random.random()
            if rand < home_prob:
                # A队赢 - 但使用xG比分作为参考
                home_goals, away_goals = map(int, result["predicted_score"].split("-"))
                if home_goals <= away_goals:
                    # 确保A队确实赢
                    home_goals = away_goals + 1
            elif rand < home_prob + draw_prob:
                # 平局
                home_goals, away_goals = 1, 1
            else:
                # B队赢
                home_goals, away_goals = map(int, result["predicted_score"].split("-"))
                if away_goals <= home_goals:
                    away_goals = home_goals + 1

            if home_goals > away_goals:
                a_wins += 1
            elif away_goals > home_goals:
                b_wins += 1
            else:
                # 平局 - 加时赛
                # 简化：加时赛各队有30%机会进球
                extra_home = random.choices([0, 1, 2], weights=[70, 25, 5])[0]
                extra_away = random.choices([0, 1, 2], weights=[70, 25, 5])[0]

                if extra_home > extra_away:
                    a_wins_extra += 1
                    a_wins += 1
                elif extra_away > extra_home:
                    b_wins_extra += 1
                    b_wins += 1
                else:
                    # 点球大战 - 纯随机
                    if random.random() < 0.5:
                        a_wins_penalties += 1
                        a_wins += 1
                    else:
                        b_wins_penalties += 1
                        b_wins += 1

        return {
            "match": f"{team_a} vs {team_b}",
            "simulation_runs": monte_carlo,
            "prob_a_wins": round(a_wins / monte_carlo * 100, 1),
            "prob_b_wins": round(b_wins / monte_carlo * 100, 1),
            "extra_time_wins": {
                team_a: round(a_wins_extra / monte_carlo * 100, 1),
                team_b: round(b_wins_extra / monte_carlo * 100, 1),
            },
            "penalty_wins": {
                team_a: round(a_wins_penalties / monte_carlo * 100, 1),
                team_b: round(b_wins_penalties / monte_carlo * 100, 1),
            },
            "recommended": team_a if a_wins > b_wins else team_b,
        }


# ============ 主程序 ============

if __name__ == "__main__":
    print("=" * 60)
    print("⚽ 核心预测引擎测试")
    print("=" * 60)

    # 初始化引擎
    engine = PredictionEngine(use_live_data=True)

    # 测试单场预测
    print("\n" + "=" * 60)
    print("📊 单场预测测试")
    print("=" * 60)

    test_matches = [
        ("France", "Germany"),
        ("Spain", "Brazil"),
        ("Argentina", "England"),
        ("Japan", "Korea South"),
    ]

    for home, away in test_matches:
        result = engine.predict_match(home, away, monte_carlo=5000)

        print(f"\n⚽ {result['match']}")
        print(f"   预测比分: {result['predicted_score']} "
              f"(最可能: {result['most_likely_score']} {result['most_likely_prob']*100:.1f}%)")
        print(f"   xG: {result['xg']['home']:.2f} vs {result['xg']['away']:.2f}")
        print(f"   胜率: {result['win_probability']['home']*100:.1f}% / "
              f"{result['win_probability']['draw']*100:.1f}% / "
              f"{result['win_probability']['away']*100:.1f}%")
        print(f"   推荐: {result['recommendation']} ({result['confidence']})")

        if result['injuries']['home'] or result['injuries']['away']:
            print(f"   伤病: {home}: {result['injuries']['home']} | "
                  f"{away}: {result['injuries']['away']}")

    # 测试冠军预测
    print("\n" + "=" * 60)
    print("🏆 世界杯冠军预测")
    print("=" * 60)

    tournament = engine.predict_tournament(monte_carlo=1000)

    print("\n冠军概率 Top 10:")
    for item in tournament["champion_prediction"][:10]:
        print(f"   {item['rank']:>2}. {item['team']:<20} {item['prob']:>5.1f}%")

    print("\nTop 4 概率:")
    for item in tournament["top4_prediction"][:10]:
        print(f"   {item['rank']:>2}. {item['team']:<20} {item['prob']:>5.1f}%")

    print("\n" + "=" * 60)
    print("✅ 预测引擎测试完成")
