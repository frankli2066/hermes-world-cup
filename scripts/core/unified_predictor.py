#!/usr/bin/env python3
"""
统一预测引擎 v5.0
=================
整合所有优化模块的最终预测系统

新增模块：
1. 疲劳恢复分析 (fatigue_recovery.py)
2. 赔率异常检测 (odds_anomaly.py)
3. 让球盘整合 (handicap_integrator.py)
4. 球队风格相克 (style_matchup.py)
5. 战意指数 (motivation_analyzer.py)
6. 天气影响 (weather_analyzer.py)
7. ML权重优化 (ml_weight_optimizer.py)
"""

import os
import sys
import json
import math
import random
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional

# 添加core模块路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入各模块（使用绝对导入）
try:
    from fatigue_recovery import FatigueRecoveryAnalyzer
    from odds_anomaly import OddsAnomalyDetector
    from handicap_integrator import HandicapIntegrator
    from style_matchup import StyleMatchupAnalyzer
    from motivation_analyzer import MotivationAnalyzer
    from weather_analyzer import WeatherAnalyzer
    from team_data import TeamDataManager
    from h2h_database import H2HDatabase
    from referee_database import RefereeDatabase
    from odds_tracker import OddsTracker
    from xg_database import XGDatabase
except ImportError:
    # 如果失败，使用相对导入
    from .fatigue_recovery import FatigueRecoveryAnalyzer
    from .odds_anomaly import OddsAnomalyDetector
    from .handicap_integrator import HandicapIntegrator
    from .style_matchup import StyleMatchupAnalyzer
    from .motivation_analyzer import MotivationAnalyzer
    from .weather_analyzer import WeatherAnalyzer
    from .team_data import TeamDataManager
    from .h2h_database import H2HDatabase
    from .referee_database import RefereeDatabase
    from .odds_tracker import OddsTracker
    from .xg_database import XGDatabase

# ============ 路径配置 ============
BASE_DIR = os.path.expanduser("~/hermes-world-cup/")
DATA_DIR = os.path.join(BASE_DIR, "data/")


class UnifiedPredictor:
    """
    统一预测引擎

    整合所有分析模块，给出最终预测
    """

    def __init__(self):
        # 初始化所有分析器
        self.fatigue = FatigueRecoveryAnalyzer()
        self.odds_detector = OddsAnomalyDetector()
        self.handicap = HandicapIntegrator()
        self.style = StyleMatchupAnalyzer()
        self.motivation = MotivationAnalyzer()
        self.weather = WeatherAnalyzer()

        # 初始化球队数据管理器（48队完整数据）
        self.team_data = TeamDataManager()

        # 加载球队Elo和风格数据
        self.elo_ratings = self.team_data.get_all_elos()
        self.team_styles = self.team_data.get_all_styles()

        # ========== 新增4个模块 ==========
        self.h2h = H2HDatabase()
        self.referee = RefereeDatabase()
        self.odds_tracker = OddsTracker()
        self.xg = XGDatabase()

        # 权重配置
        self.weights = self._load_weights()

    def get_elo(self, team: str) -> int:
        """获取球队Elo"""
        return self.elo_ratings.get(team, 1800)

    def get_style(self, team: str) -> str:
        """获取球队风格"""
        return self.team_styles.get(team, "balanced")

    def _load_weights(self) -> Dict:
        """加载权重配置"""
        weights_file = os.path.join(DATA_DIR, "calibration", "optimal_weights_v2.json")
        if os.path.exists(weights_file):
            try:
                with open(weights_file, 'r') as f:
                    return json.load(f)
            except:
                pass

        # 默认权重 - v5.3优化版（增强市场赔率权重）
        return {
            "elo_weight": 0.139,      # 降低Elo权重
            "form_weight": 0.100,      # 降低状态权重
            "home_advantage": 0.060,   # 主场优势
            "market_weight": 0.600,    # 【优化】大幅提高市场赔率权重到60%
            "fatigue_weight": 0.040,    # 疲劳权重
            "style_weight": 0.010,    # 风格克制
            "weather_weight": 0.010,   # 天气权重
            "motivation_weight": 0.010, # 战意权重
            "travel_weight": 0.00,
            # 新增模块权重
            "h2h_weight": 0.030,       # H2H往绩（降低）
            "referee_weight": 0.010,    # 裁判（降低）
            "odds_movement_weight": 0.100,  # 赔率变化权重
            "xg_weight": 0.080,        # xG权重（降低）
            "head_to_head_weight": 0.050,  # 球队对战记录
        }

    def predict(self,
                home_team: str,
                away_team: str,
                home_last_match_date: datetime = None,
                away_last_match_date: datetime = None,
                match_date: datetime = None,
                venue: str = None,
                weather: Dict = None,
                group_standings: Dict = None,
                odds: Dict = None,
                handicap: float = None,
                referee: str = None,
                opening_odds: Dict = None,
                match_stage: str = "group") -> Dict:
        """
        综合所有模块的最终预测

        Args:
            home_team: 主队
            away_team: 客队
            home_last_match_date: 主队上一场比赛日期
            away_last_match_date: 客队上一场比赛日期
            match_date: 比赛日期
            venue: 比赛地点
            weather: 天气数据 {"temp": 25, "humidity": 60, "precipitation": 0, "wind": 10}
            group_standings: 小组积分 {"home": {"points": 3}, "away": {"points": 0}}
            odds: 终盘赔率 {"home": 2.0, "draw": 3.2, "away": 3.8}
            handicap: 让球盘口
            referee: 裁判名称
            opening_odds: 初盘赔率 {"home": 2.0, "draw": 3.2, "away": 3.8}
            match_stage: 比赛阶段 "group", "knockout", "round_of_16", "quarterfinal", "semifinal", "final"

        Returns:
            完整预测报告
        """
        if match_date is None:
            match_date = datetime.now()

        # ========== 1. 基础Elo概率 ==========
        elo_result = self._calculate_elo_prob(home_team, away_team)

        # ========== 2. 疲劳恢复调整 ==========
        fatigue_result = self._apply_fatigue(
            elo_result,
            home_team, away_team,
            home_last_match_date, away_last_match_date,
            match_date
        )

        # ========== 3. 风格相克调整 ==========
        style_result = self._apply_style_adjustment(
            fatigue_result,
            home_team, away_team
        )

        # ========== 4. 天气调整 ==========
        weather_result = self._apply_weather(
            style_result,
            weather
        )

        # ========== 5. 战意调整 ==========
        motivation_result = self._apply_motivation(
            weather_result,
            group_standings
        )

        # ========== 6. 赔率整合 ==========
        odds_result = self._apply_odds(
            motivation_result,
            odds
        )

        # ========== 7. 让球盘整合 ==========
        handicap_result = self._apply_handicap(
            odds_result,
            handicap,
            elo_result.get("elo_diff", 0)
        )

        # ========== 8. H2H往绩调整 ==========
        h2h_result = self._apply_h2h(
            handicap_result,
            home_team, away_team
        )

        # ========== 9. 裁判执法调整 ==========
        referee_result = self._apply_referee(
            h2h_result,
            referee,
            home_team, away_team
        )

        # ========== 10. 赔率变化趋势 ==========
        odds_movement_result = self._apply_odds_movement(
            referee_result,
            opening_odds, odds,
            elo_result
        )

        # ========== 11. xG预期进球 ==========
        xg_result = self._apply_xg(
            odds_movement_result,
            home_team, away_team
        )

        # ========== 生成最终预测 ==========
        final_result = self._generate_final_prediction(
            xg_result,
            home_team, away_team
        )

        # ========== 小组赛专项调整 ==========
        if match_stage == "group":
            final_result = self._apply_group_stage_adjustment(
                final_result,
                home_team, away_team,
                group_standings
            )

        # ========== 淘汰赛专项调整 ==========
        final_result = self._apply_knockout_adjustment(
            final_result,
            home_team, away_team,
            match_stage
        )

        # ========== 冷门检测修正 ==========
        # 在小组赛和淘汰赛调整后进行冷门检测
        final_result = self._apply_upset_correction(
            final_result,
            home_team, away_team
        )

        # ========== 平局专项检测（保守版）==========
        # 仅当draw_score>=5才触发调整，避免矫枉过正
        final_result = self._apply_draw_detection(
            final_result,
            home_team, away_team,
            xg_result
        )

        # ========== 预测不确定性调整 ==========
        final_result = self._apply_confidence_adjustment(
            final_result,
            xg_result,
            home_team, away_team
        )

        # 添加各模块分析报告
        final_result["modules"] = {
            "elo": elo_result,
            "fatigue": fatigue_result,
            "style": style_result,
            "weather": weather_result,
            "motivation": motivation_result,
            "odds": odds_result,
            "handicap": handicap_result,
            "h2h": h2h_result,
            "referee": referee_result,
            "odds_movement": odds_movement_result,
            "xg": xg_result,
        }

        # 【新增】冷门检测 - 当高信心预测时检查爆冷风险
        upset_check = self._detect_upset_risk(
            final_result, home_team, away_team,
            fatigue_result, h2h_result, odds_result, elo_result
        )
        final_result["upset_check"] = upset_check

        # 【优化】如果检测到高爆冷风险，修正预测
        if upset_check["upset_risk"] == "high":
            final_result["prediction"]["confidence"] = "🟡 低信心"
            final_result["prediction"]["upset_warning"] = True
            # 如果推荐主队胜但客队有多重优势信号，翻转预测
            recommended = final_result["prediction"].get("recommended_team", "")
            if recommended == home_team and upset_check.get("recommended_team") == away_team:
                # 翻转预测为客队
                final_result["prediction"]["recommended_team"] = away_team
                final_result["prediction"]["home_win"], final_result["prediction"]["away_win"] = (
                    final_result["prediction"]["away_win"], final_result["prediction"]["home_win"]
                )
                final_result["prediction"]["confidence"] = "🟡 低信心（冷门翻转）"
                final_result["prediction"]["upset_flipped"] = True

        # 添加权重信息
        final_result["weights"] = self.weights

        return final_result

    def _calculate_elo_prob(self, home: str, away: str) -> Dict:
        """计算基于Elo的概率"""
        home_elo = self.get_elo(home)
        away_elo = self.get_elo(away)

        elo_diff = home_elo - away_elo

        # Elo差距转换为概率（使用Elo公式）
        # 基础胜率计算
        home_win_prob = 1 / (1 + 10 ** (-elo_diff / 400))
        away_win_prob = 1 / (1 + 10 ** (elo_diff / 400))

        # 【修复BUG】加入主场优势！
        # 使用权重中的home_advantage: 0.060（约6%的主场加成）
        # 这是根据研究：主场平均给主队带来5-7%的额外胜率
        home_adv = self.weights.get("home_advantage", 0.060)
        home_win_prob = min(0.95, home_win_prob + home_adv)
        away_win_prob = min(0.95, away_win_prob)

        # 归一化主客胜概率
        total_prob = home_win_prob + away_win_prob
        home_win_prob /= total_prob
        away_win_prob /= total_prob

        # 根据Elo差距分配基础平局概率
        # Elo差距越小，平局概率越高（实力接近更容易平）
        abs_diff = abs(elo_diff)
        if abs_diff < 50:
            base_draw = 0.30  # 实力接近，30%平局率
        elif abs_diff < 100:
            base_draw = 0.26  # 略微差距，26%
        elif abs_diff < 150:
            base_draw = 0.23  # 中等差距，23%
        elif abs_diff < 200:
            base_draw = 0.20  # 较大差距，20%
        else:
            base_draw = 0.18  # 悬殊差距，18%（但仍有18%平局可能！）

        # 按Elo比例分配剩余概率给主客胜
        home_prob = home_win_prob * (1 - base_draw)
        away_prob = away_win_prob * (1 - base_draw)
        draw_prob = base_draw

        # 再次归一化确保总和为1
        total = home_prob + away_prob + draw_prob
        home_prob /= total
        away_prob /= total
        draw_prob /= total

        return {
            "home_prob": home_prob,
            "away_prob": away_prob,
            "draw_prob": draw_prob,
            "elo_diff": elo_diff,
            "home_elo": home_elo,
            "away_elo": away_elo,
            "home_advantage_applied": home_adv  # 记录主场优势是否被应用
        }

    def _apply_fatigue(self,
                       base_result: Dict,
                       home_team: str, away_team: str,
                       home_last_date: datetime,
                       away_last_date: datetime,
                       match_date: datetime) -> Dict:
        """应用疲劳恢复调整"""
        result = base_result.copy()

        if home_last_date is None:
            home_last_date = match_date - timedelta(days=5)
        if away_last_date is None:
            away_last_date = match_date - timedelta(days=5)

        # 计算休息天数
        home_rest = (match_date - home_last_date).days
        away_rest = (match_date - away_last_date).days

        # 获取疲劳因子
        home_rest_factor = self.fatigue.get_rest_factor(home_rest)
        away_rest_factor = self.fatigue.get_rest_factor(away_rest)

        # 计算旅途影响
        # 假设比赛在主队主场
        away_travel_penalty, travel_details = self.fatigue.get_travel_factor(
            away_team, home_team
        )

        # 综合调整
        home_advantage = home_rest_factor - away_travel_penalty
        home_win_adj = home_advantage * 0.5 * self.weights.get("fatigue_weight", 0.03) * 10

        result["home_prob"] = base_result["home_prob"] + home_win_adj
        result["away_prob"] = base_result["away_prob"] - home_win_adj

        # 归一化
        total = result["home_prob"] + result["away_prob"] + result["draw_prob"]
        result["home_prob"] /= total
        result["away_prob"] /= total
        result["draw_prob"] /= total

        result["fatigue_adjustment"] = {
            "home_rest_days": home_rest,
            "away_rest_days": away_rest,
            "home_rest_factor": home_rest_factor,
            "away_rest_factor": away_rest_factor,
            "away_travel_penalty": away_travel_penalty,
            "travel_details": travel_details,
            "home_win_adjustment": home_win_adj
        }

        return result

    def _apply_style_adjustment(self,
                                 base_result: Dict,
                                 home_team: str, away_team: str) -> Dict:
        """应用风格相克调整"""
        result = base_result.copy()

        # 获取风格分析
        style_analysis = self.style.analyze_matchup(home_team, away_team)
        style_factor = style_analysis["home_advantage"]

        # 应用调整
        adjustment = style_factor * 0.5 * self.weights.get("style_weight", 0.02) * 10

        result["home_prob"] += adjustment
        result["away_prob"] -= adjustment

        # 归一化
        total = result["home_prob"] + result["away_prob"] + result["draw_prob"]
        result["home_prob"] /= total
        result["away_prob"] /= total
        result["draw_prob"] /= total

        result["style_adjustment"] = {
            "home_style": style_analysis["home_style"],
            "away_style": style_analysis["away_style"],
            "style_factor": style_factor,
            "adjustment": adjustment
        }

        return result

    def _apply_weather(self,
                       base_result: Dict,
                       weather: Dict = None) -> Dict:
        """应用天气调整"""
        result = base_result.copy()

        if weather is None:
            result["weather_adjustment"] = {"status": "no_data"}
            return result

        # 分析天气影响
        weather_analysis = self.weather.analyze_weather_impact(
            temperature=weather.get("temp", 20),
            humidity=weather.get("humidity", 60),
            precipitation=weather.get("precipitation", 0),
            wind_speed=weather.get("wind", 10),
            altitude=weather.get("altitude", 0)
        )

        goal_factor = weather_analysis.get("goal_factor", 1.0)
        home_adv_mod = weather_analysis.get("home_advantage_mod", 0)

        # 应用调整
        adjustment = home_adv_mod * 0.3 * self.weights.get("weather_weight", 0.01) * 10

        result["home_prob"] += adjustment
        result["away_prob"] -= adjustment

        # 归一化
        total = result["home_prob"] + result["away_prob"] + result["draw_prob"]
        result["home_prob"] /= total
        result["away_prob"] /= total
        result["draw_prob"] /= total

        result["weather_adjustment"] = {
            "goal_factor": goal_factor,
            "home_advantage_mod": home_adv_mod,
            "weather_description": weather_analysis.get("description", ""),
            "recommendation": weather_analysis.get("recommendation", "")
        }

        return result

    def _apply_motivation(self,
                          base_result: Dict,
                          group_standings: Dict = None) -> Dict:
        """应用战意调整"""
        result = base_result.copy()

        if group_standings is None:
            result["motivation_adjustment"] = {"status": "no_data"}
            return result

        # 简化处理
        home_points = group_standings.get("home", {}).get("points", 3)
        away_points = group_standings.get("away", {}).get("points", 3)

        # 战意调整
        home_motivation = 0
        away_motivation = 0

        # 背水一战加成
        if home_points == 0:
            home_motivation = 0.03
        if away_points == 0:
            away_motivation = 0.03

        # 已确保出线可能轮换
        if home_points >= 6:
            home_motivation = -0.02
        if away_points >= 6:
            away_motivation = -0.02

        adjustment = (home_motivation - away_motivation) * 0.3 * self.weights.get("motivation_weight", 0.01) * 10

        result["home_prob"] += adjustment
        result["away_prob"] -= adjustment

        # 归一化
        total = result["home_prob"] + result["away_prob"] + result["draw_prob"]
        result["home_prob"] /= total
        result["away_prob"] /= total
        result["draw_prob"] /= total

        result["motivation_adjustment"] = {
            "home_points": home_points,
            "away_points": away_points,
            "home_motivation": home_motivation,
            "away_motivation": away_motivation
        }

        return result

    def _apply_odds(self,
                    base_result: Dict,
                    odds: Dict = None) -> Dict:
        """应用赔率整合"""
        result = base_result.copy()

        if odds is None:
            result["odds_adjustment"] = {"status": "no_data"}
            return result

        # 从赔率计算隐含概率
        try:
            implied_home = 1 / odds.get("home", 2.0)
            implied_draw = 1 / odds.get("draw", 3.2)
            implied_away = 1 / odds.get("away", 3.8)

            # 归一化
            total = implied_home + implied_draw + implied_away
            implied_home /= total
            implied_draw /= total
            implied_away /= total

            # 与模型融合（使用类级别权重）
            market_weight = self.weights.get("market_weight", 0.35)
            model_weight = 1 - market_weight

            result["home_prob"] = result["home_prob"] * model_weight + implied_home * market_weight
            result["draw_prob"] = result["draw_prob"] * model_weight + implied_draw * market_weight
            result["away_prob"] = result["away_prob"] * model_weight + implied_away * market_weight

            result["odds_adjustment"] = {
                "implied_home": implied_home,
                "implied_draw": implied_draw,
                "implied_away": implied_away,
                "market_weight": market_weight
            }

        except Exception as e:
            result["odds_adjustment"] = {"status": "error", "message": str(e)}

        return result

    def _apply_handicap(self,
                        base_result: Dict,
                        handicap: float = None,
                        elo_diff: float = 0) -> Dict:
        """应用让球盘整合"""
        result = base_result.copy()

        if handicap is None:
            # 从Elo估算盘口
            handicap = self.handicap.get_handicap_from_elo_diff(elo_diff)

        # 分析盘口
        analysis = self.handicap.analyze_handicap(
            handicap, "", "", elo_diff
        )

        # 应用市场偏差
        market_bias = analysis.get("market_bias", 0)
        adjustment = market_bias * 0.3

        result["home_prob"] += adjustment
        result["away_prob"] -= adjustment

        # 归一化
        total = result["home_prob"] + result["away_prob"] + result["draw_prob"]
        result["home_prob"] /= total
        result["away_prob"] /= total
        result["draw_prob"] /= total

        result["handicap_adjustment"] = {
            "handicap": handicap,
            "market_bias": market_bias,
            "line_assessment": analysis.get("line_assessment", "")
        }

        return result

    def _generate_final_prediction(self,
                                   result: Dict,
                                   home_team: str,
                                   away_team: str) -> Dict:
        """生成最终预测"""
        home_prob = result["home_prob"]
        away_prob = result["away_prob"]
        draw_prob = result["draw_prob"]

        # 【优化1】获取Elo差距，用于分段预测策略
        home_elo = self.get_elo(home_team)
        away_elo = self.get_elo(away_team)
        elo_diff = abs(home_elo - away_elo)

        # 使用xG模块的真实xG数据
        if "xg_adjustment" in result:
            home_xg = result["xg_adjustment"].get("home_xg", 1.3)
            away_xg = result["xg_adjustment"].get("away_xg", 1.1)
        else:
            # 降级：使用概率估算
            home_xg = 1.3 * home_prob / 0.40 if home_prob > 0.30 else 0.9
            away_xg = 1.1 * away_prob / 0.35 if away_prob > 0.25 else 0.8
            home_xg = max(0.5, min(2.5, home_xg))
            away_xg = max(0.4, min(2.2, away_xg))

        # 【新增】xG与预测一致性检测
        # 如果xG显示的结果与概率预测不一致，降低信心度
        xg_prediction = "home" if home_xg > away_xg else ("away" if away_xg > home_xg else "draw")
        prob_prediction = "home" if home_prob > away_prob else ("away" if away_prob > home_prob else "draw")

        xg_conflict = False
        xg_conflict_factor = 1.0  # 信心度修正因子

        if xg_prediction != prob_prediction:
            xg_conflict = True
            # xG和概率预测不一致，根据差距大小降低信心
            xg_diff_ratio = abs(home_xg - away_xg) / max(home_xg, away_xg, 0.5)
            if xg_diff_ratio > 0.3:  # xG差距超过30%
                xg_conflict_factor = 0.7  # 大幅降低信心
            elif xg_diff_ratio > 0.15:  # xG差距超过15%
                xg_conflict_factor = 0.85  # 轻微降低信心

        # 【优化1】Elo差距分段预测策略（保守有效版）
        elo_based_adjustment = 0
        elo_strategy = "正常预测"

        if elo_diff < 40:
            # 极端势均力敌：Elo差距<40时，推荐平局
            recommendation = "平局"
            elo_strategy = "极端势均力敌→平局"
            elo_based_adjustment = 0.08

        elif elo_diff < 80:
            # 势均力敌：Elo差距40-80时，增加平局概率但不强制推荐
            if abs(home_prob - away_prob) < 0.06:
                recommendation = "平局"
                elo_strategy = "概率接近→平局"
            elif home_prob > away_prob:
                recommendation = home_team
                elo_strategy = "主队略占优"
            else:
                recommendation = away_team
                elo_strategy = "客队略占优"
            elo_based_adjustment = 0.04

        elif elo_diff >= 120:
            # 明显差距：Elo差距>=120时，正常预测
            if home_prob > away_prob:
                recommendation = home_team
                elo_strategy = "主队明显占优"
            else:
                recommendation = away_team
                elo_strategy = "客队明显占优"
        else:
            # 中等差距：正常预测
            if home_prob > away_prob:
                recommendation = home_team
                elo_strategy = "主队占优"
            else:
                recommendation = away_team
                elo_strategy = "客队占优"

        # 【优化2】平局概率调整（保守版）
        # 只有在Elo差距小时才增加平局概率
        if elo_diff < 120:
            adjusted_draw_prob = min(draw_prob + elo_based_adjustment, 0.35)
        else:
            adjusted_draw_prob = draw_prob

        # 归一化概率（确保总和为1）
        total_prob = home_prob + away_prob + adjusted_draw_prob
        home_prob_normalized = home_prob / total_prob
        away_prob_normalized = away_prob / total_prob
        draw_prob_normalized = adjusted_draw_prob / total_prob

        # 计算prob_diff用于信心度判断
        prob_diff = abs(home_prob_normalized - away_prob_normalized)

        # 【优化3】最终推荐（保守）
        # 只有在概率非常接近时才推荐平局
        if abs(home_prob - away_prob) < 0.04 and adjusted_draw_prob > 0.25:
            recommendation = "平局"
            elo_strategy = "概率接近→平局"
        elif home_prob > away_prob:
            recommendation = home_team
        else:
            recommendation = away_team

        # 【优化4】信心度判断（保守）
        if prob_diff > 0.22:
            confidence = "🟢 高信心"
        elif prob_diff > 0.10:
            confidence = "🟡 中信心"
        else:
            confidence = "🟢 低信心"

        # 比分预测（泊松分布替代蒙特卡洛）
        scores = self._poisson_score(home_xg, away_xg)

        return {
            "home_team": home_team,
            "away_team": away_team,
            "prediction": {
                "home_win": home_prob_normalized,
                "draw": draw_prob_normalized,
                "away_win": away_prob_normalized,
                "recommended_team": recommendation,
                "confidence": confidence,
                "home_xg": round(home_xg, 2),
                "away_xg": round(away_xg, 2),
                "xg_conflict": xg_conflict,  # 记录xG冲突
                "xg_conflict_factor": xg_conflict_factor,  # 信心修正因子
                "elo_strategy": elo_strategy,  # 【新增】Elo策略说明
                "elo_diff": elo_diff  # 【新增】Elo差距
            },
            "scores": scores[:5],  # 前5个最可能比分
            "timestamp": datetime.now().isoformat()
        }

    def _poisson_score(self, home_xg: float, away_xg: float) -> List[Dict]:
        """
        【优化2】泊松分布直接计算比分概率
        替代蒙特卡洛模拟，更快更精确

        泊松分布：P(X=k) = (λ^k * e^(-λ)) / k!
        """
        from scipy.stats import poisson

        scores = {}

        # 考虑最多进6球（超过6球的概率极低）
        max_goals = 6

        for home_goals in range(max_goals + 1):
            for away_goals in range(max_goals + 1):
                # 泊松分布计算概率
                home_prob = poisson.pmf(home_goals, home_xg)
                away_prob = poisson.pmf(away_goals, away_xg)
                # 比分概率 = 主队进x球的概率 × 客队进y球的概率
                combined_prob = home_prob * away_prob
                scores[(home_goals, away_goals)] = combined_prob

        # 按概率排序
        sorted_scores = sorted(scores.items(), key=lambda x: -x[1])

        # 计算总概率用于归一化
        total_prob = sum(scores.values())

        result = []
        for (hg, ag), prob in sorted_scores[:5]:
            result.append({
                "score": f"{hg}-{ag}",
                "prob": prob / total_prob * 100,  # 归一化
                "label": "⭐ 首选" if len(result) == 0 else f"#{len(result)+1}"
            })

        return result

    # 保留旧方法作为备用
    def _monte_carlo_score(self, home_xg: float, away_xg: float, n: int = 2000) -> List[Dict]:
        """蒙特卡洛模拟比分（已废弃，使用_poisson_score代替）"""
        return self._poisson_score(home_xg, away_xg)

    def _detect_upset_risk(self,
                           result: Dict,
                           home_team: str,
                           away_team: str,
                           fatigue_result: Dict,
                           h2h_result: Dict,
                           odds_result: Dict,
                           elo_result: Dict = None) -> Dict:
        """
        【新增】冷门检测 - 当高信心预测时检查爆冷风险

        检测以下爆冷信号：
        1. 疲劳优势：客队休息更充足
        2. 状态优势：客队近期状态明显更好
        3. H2H劣势：客队对主队历史战绩占优
        4. 市场异常：博彩公司开出的赔率与预测差距大
        """
        home_prob = result["prediction"]["home_win"]
        away_prob = result["prediction"]["away_win"]

        # 只对高信心预测进行爆冷检测
        prob_diff = abs(home_prob - away_prob)
        if prob_diff < 0.15:
            # 本身就是低信心，不需要爆冷检测
            return {"upset_risk": "low", "reasons": []}

        # 收集爆冷信号
        upset_signals = []
        risk_score = 0.0

        # 1. 疲劳检测：客队休息更充足
        fatigue = fatigue_result.get("fatigue_adjustment", {})
        home_rest = fatigue.get("home_rest_days", 5)
        away_rest = fatigue.get("away_rest_days", 5)
        if away_rest > home_rest + 1:
            rest_advantage = (away_rest - home_rest) * 0.02
            risk_score += rest_advantage
            upset_signals.append(f"客队休息更充足(+{away_rest - home_rest}天)")

        # 2. 状态检测：客队近期状态更好（通过Elo变化推断）
        if elo_result:
            home_elo = elo_result.get("home_elo", 1700)
            away_elo = elo_result.get("away_elo", 1700)
            # 如果客队Elo比主队高但预测主队胜，可能存在状态问题
            if away_elo > home_elo and home_prob > away_prob:
                elo_gap = (away_elo - home_elo) / 400
                if elo_gap > 0.1:
                    risk_score += 0.03
                    upset_signals.append("客队Elo更高但预测主队胜")

        # 3. H2H劣势：客队历史战绩占优
        if isinstance(h2h_result, dict):
            h2h = h2h_result.get("h2h_stats", {})
            if h2h.get("total", 0) >= 2:
                away_h2h_rate = h2h.get("away_wins", 0) / h2h["total"]
                if away_h2h_rate > 0.5:
                    risk_score += 0.05
                    upset_signals.append("客队H2H历史战绩占优")

        # 4. 市场异常：赔率与预测不一致
        implied_away = odds_result.get("implied_probabilities", {}).get("away", 0.3)
        if implied_away > away_prob + 0.1:
            risk_score += 0.05
            upset_signals.append("市场赔率暗示客队概率更高")

        # 5. xG冲突检测
        if result["prediction"].get("xg_conflict", False):
            risk_score += 0.08
            upset_signals.append("xG与预测不一致")

        # 【优化】综合评估风险等级（恢复原版阈值）
        if risk_score >= 0.15:
            upset_risk = "high"
        elif risk_score >= 0.08:
            upset_risk = "medium"
        else:
            upset_risk = "low"

        # 【新增】客队多重优势检测 - 如果客队有2个以上独立优势信号，直接推荐客队
        away_advantage_signals = 0
        if away_rest > home_rest + 1:
            away_advantage_signals += 1
        if away_elo > home_elo and home_prob > away_prob:
            away_advantage_signals += 1
        if isinstance(h2h_result, dict) and h2h.get("away_wins", 0) > h2h.get("home_wins", 0):
            away_advantage_signals += 1
        if implied_away > away_prob + 0.1:
            away_advantage_signals += 1

        # 如果客队有2个以上优势信号，强制推荐客队
        force_away = away_advantage_signals >= 2

        return {
            "upset_risk": upset_risk,
            "risk_score": round(risk_score, 3),
            "reasons": upset_signals,
            "recommended_team": away_team if risk_score >= 0.1 else None,
            "away_advantage_signals": away_advantage_signals,
            "force_away": force_away
        }

    # ========== 新增模块方法 ==========

    def _apply_h2h(self,
                    base_result: Dict,
                    home_team: str,
                    away_team: str) -> Dict:
        """应用H2H往绩调整"""
        result = base_result.copy()

        h2h_factor = self.h2h.get_h2h_factor(home_team, away_team)
        h2h_stats = self.h2h.get_h2h_stats(home_team, away_team)

        # ========== H2H主队vs客队调整（平衡版）==========
        # 【优化】根据样本量调整，但保持适度影响
        # 样本量>=5时full影响，<3时大幅降低
        if h2h_stats["total"] >= 5:
            h2h_sample_factor = 1.0
        elif h2h_stats["total"] >= 3:
            h2h_sample_factor = 0.6
        elif h2h_stats["total"] >= 1:
            h2h_sample_factor = 0.3  # 只有1场时只给30%影响
        else:
            h2h_sample_factor = 0.0  # 没有H2H数据时无调整
        
        max_adjustment = 0.08  # 最大调整幅度8%
        
        h2h_adjustment = h2h_factor * self.weights.get("h2h_weight", 0.05) * 5  # 乘数从10降到5
        h2h_adjustment = max(-max_adjustment, min(max_adjustment, h2h_adjustment * h2h_sample_factor))
        result["home_prob"] = base_result["home_prob"] + h2h_adjustment
        result["away_prob"] = base_result["away_prob"] - h2h_adjustment

        # ========== H2H平局率调整（平衡版）==========
        # 【优化】保持适度平局boost，但根据样本量调整
        h2h_draw_rate = h2h_stats["draws"] / h2h_stats["total"] if h2h_stats["total"] > 0 else 0
        
        # 样本量惩罚
        if h2h_stats["total"] >= 5:
            draw_sample_factor = 1.0
        elif h2h_stats["total"] >= 3:
            draw_sample_factor = 0.6
        elif h2h_stats["total"] >= 1:
            draw_sample_factor = 0.3
        else:
            draw_sample_factor = 0.0
        
        max_draw_boost = 0.06  # 最大平局boost 6%
        
        if h2h_draw_rate >= 0.5:
            # 高平局率历史
            draw_boost = h2h_draw_rate * 0.08 * draw_sample_factor  # 50%平局率 -> 最多4% boost
            result["draw_prob"] = min(0.38, result["draw_prob"] + draw_boost)
            result["home_prob"] = max(0.25, result["home_prob"] - draw_boost * 0.55)
            result["away_prob"] = max(0.20, result["away_prob"] - draw_boost * 0.45)
        elif h2h_draw_rate >= 0.33:
            # 中等平局率
            draw_boost = h2h_draw_rate * 0.05 * draw_sample_factor  # 最多2.5% boost
            result["draw_prob"] = min(0.34, result["draw_prob"] + draw_boost)
            result["home_prob"] = max(0.28, result["home_prob"] - draw_boost * 0.5)
            result["away_prob"] = max(0.22, result["away_prob"] - draw_boost * 0.5)
        
        # 归一化
        total = result["home_prob"] + result["away_prob"] + result["draw_prob"]
        result["home_prob"] /= total
        result["away_prob"] /= total
        result["draw_prob"] /= total

        result["h2h_adjustment"] = {
            "h2h_factor": h2h_factor,
            "has_record": h2h_stats["total"] > 0,
            "total_matches": h2h_stats["total"],
            "home_wins": h2h_stats["team1_wins"],
            "away_wins": h2h_stats["team2_wins"],
            "draws": h2h_stats["draws"],
            "draw_rate": h2h_stats["draws"] / h2h_stats["total"] if h2h_stats["total"] > 0 else 0,
            "has_upset_history": h2h_stats.get("has_upsets", False)
        }

        return result

    def _apply_referee(self,
                       base_result: Dict,
                       referee_name: str,
                       home_team: str,
                       away_team: str) -> Dict:
        """应用裁判执法调整"""
        result = base_result.copy()

        if referee_name:
            factor = self.referee.get_referee_factor(referee_name)
            analysis = self.referee.analyze_matchup(referee_name, home_team, away_team)

            if factor["found"]:
                # 裁判影响调整
                referee_adjustment = factor["home_bias"] * self.weights.get("referee_weight", 0.02) * 10
                result["home_prob"] = base_result["home_prob"] + referee_adjustment
                result["away_prob"] = base_result["away_prob"] - referee_adjustment

                # 归一化
                total = result["home_prob"] + result["away_prob"] + result["draw_prob"]
                result["home_prob"] /= total
                result["away_prob"] /= total
                result["draw_prob"] /= total

                result["referee_adjustment"] = {
                    "referee": referee_name,
                    "found": True,
                    "style": factor["style"],
                    "penalty_factor": factor["penalty_factor"],
                    "card_factor": factor["card_factor"],
                    "description": analysis.get("description", ""),
                    "recommendation": analysis.get("recommendation", "")
                }
            else:
                result["referee_adjustment"] = {
                    "referee": referee_name,
                    "found": False
                }
        else:
            result["referee_adjustment"] = {
                "found": False
            }

        return result

    def _apply_odds_movement(self,
                             base_result: Dict,
                             opening_odds: Dict,
                             closing_odds: Dict,
                             elo_result: Dict) -> Dict:
        """应用赔率变化趋势调整"""
        result = base_result.copy()

        if opening_odds and closing_odds:
            # 赔率变化分析
            movement = self.odds_tracker.calculate_movement(opening_odds, closing_odds)

            # 赔率变化调整
            odds_factor = self.odds_tracker.get_odds_factor(opening_odds, closing_odds)
            odds_adjustment = odds_factor * self.weights.get("odds_movement_weight", 0.05) * 10

            result["home_prob"] = base_result["home_prob"] + odds_adjustment
            result["away_prob"] = base_result["away_prob"] - odds_adjustment

            # 归一化
            total = result["home_prob"] + result["away_prob"] + result["draw_prob"]
            result["home_prob"] /= total
            result["away_prob"] /= total
            result["draw_prob"] /= total

            result["odds_movement_adjustment"] = {
                "direction": movement["direction"],
                "volatility": movement["total_volatility"],
                "confidence_boost": movement["confidence_boost"],
                "is_sharp_money": movement["is_sharp_money"],
                "is_steam_move": movement["is_steam_move"],
                "assessment": movement["assessment"]
            }
        else:
            result["odds_movement_adjustment"] = {"has_data": False}

        return result

    def _apply_xg(self,
                  base_result: Dict,
                  home_team: str,
                  away_team: str) -> Dict:
        """应用xG预期进球调整"""
        result = base_result.copy()

        # xG分析
        xg_analysis = self.xg.calculate_match_xg(home_team, away_team)
        xg_factor = self.xg.get_xg_factor(home_team, away_team)
        attack_defense = self.xg.analyze_attack_vs_defense(home_team, away_team)

        # xG调整（保守版）
        # 【修复】限制调整幅度，xG权重较低(0.08)且factor通常很小
        xg_adjustment = xg_factor * self.weights.get("xg_weight", 0.08) * 5  # 乘数从10降到5
        max_xg_adjustment = 0.03  # 最大调整幅度3%
        xg_adjustment = max(-max_xg_adjustment, min(max_xg_adjustment, xg_adjustment))
        result["home_prob"] = base_result["home_prob"] + xg_adjustment
        result["away_prob"] = base_result["away_prob"] - xg_adjustment

        # 归一化
        total = result["home_prob"] + result["away_prob"] + result["draw_prob"]
        result["home_prob"] /= total
        result["away_prob"] /= total
        result["draw_prob"] /= total

        result["xg_adjustment"] = {
            "home_xg": xg_analysis["home_xg"],
            "away_xg": xg_analysis["away_xg"],
            "total_xg": xg_analysis["total_xg"],
            "home_win_prob": xg_analysis["probabilities"]["home_win"],
            "draw_prob_xg": xg_analysis["probabilities"]["draw"],
            "away_win_prob": xg_analysis["probabilities"]["away_win"],
            "xg_factor": xg_factor,
            "attack_vs_defense": attack_defense["assessment"],
            "top_score": xg_analysis["score_probabilities"][0] if xg_analysis.get("score_probabilities") else None
        }

        # ========== 平局概率修正 ==========
        result = self._apply_draw_correction(result, home_team, away_team, xg_analysis)

        return result

    def _apply_draw_correction(self,
                               base_result: Dict,
                               home_team: str,
                               away_team: str,
                               xg_analysis: Dict) -> Dict:
        """
        平局概率修正

        增加平局检测能力的专项调整
        """
        result = base_result.copy()

        draw_score = 0.0  # 平局倾向分数

        # 1. xG总分低 -> 平局概率增加
        total_xg = xg_analysis.get("total_xg", 2.0)
        if total_xg < 1.8:
            draw_score += 0.08
        elif total_xg < 2.2:
            draw_score += 0.04

        # 2. Elo接近 -> 平局概率增加
        elo_diff = abs(self.team_data.get_elo(home_team) - self.team_data.get_elo(away_team))
        if elo_diff < 50:
            draw_score += 0.10
        elif elo_diff < 100:
            draw_score += 0.05

        # 3. 双方都是防守型 -> 平局概率增加
        home_style = self.team_styles.get(home_team, "")
        away_style = self.team_styles.get(away_team, "")
        if home_style == "defensive" and away_style == "defensive":
            draw_score += 0.08
        elif home_style == "defensive" or away_style == "defensive":
            draw_score += 0.03

        # 4. 双方进球能力都低
        home_xg = xg_analysis.get("home_xg", 1.5)
        away_xg = xg_analysis.get("away_xg", 1.5)
        if home_xg < 1.3 and away_xg < 1.3:
            draw_score += 0.06

        # 5. xG比分预测显示平局
        top_score = xg_analysis.get("score_probabilities", [{}])[0]
        if top_score and top_score.get("score") and "-" in top_score["score"]:
            score_parts = top_score["score"].split("-")
            if score_parts[0] == score_parts[1]:  # 1-1, 2-2等
                draw_score += 0.05
            elif abs(int(score_parts[0]) - int(score_parts[1])) <= 1:
                # 接近的比分如1-0, 2-1等
                draw_score += 0.02

        # 应用平局修正（只上浮平局概率，不减少）
        # 优化：降低平局系数从0.5→0.05，基于回测数据分析发现平局被过度预测
        draw_adjustment = draw_score * 0.05
        if draw_adjustment > 0:
            result["draw_prob"] = base_result["draw_prob"] + draw_adjustment

            # 归一化
            total = result["home_prob"] + result["away_prob"] + result["draw_prob"]
            result["home_prob"] /= total
            result["away_prob"] /= total
            result["draw_prob"] /= total

        result["draw_correction"] = {
            "draw_score": draw_score,
            "draw_adjustment": draw_adjustment if draw_adjustment > 0 else 0,
            "xg_low": total_xg < 2.2,
            "elo_close": elo_diff < 100,
            "both_defensive": home_style == "defensive" and away_style == "defensive"
        }

        # 注意：冷门检测现在在 predict() 函数中 prediction 生成后统一调用

        return result

    def _apply_upset_correction(self,
                                base_result: Dict,
                                home_team: str,
                                away_team: str) -> Dict:
        """
        冷门检测修正（增强版）

        当检测到爆冷信号时，降低热门方概率，增加冷门概率
        冷门信号包括：
        1. 强队客场作战 vs 弱队主场
        2. H2H显示客队有爆冷历史
        3. 客队进球能力被低估
        4. 市场赔率显示大热
        5. 弱队急需分数（0分状态）
        """
        result = base_result.copy()

        upset_indicators = 0
        upset_reasons = []

        # ========== 1. 强队客场 vs 弱队主场 ==========
        home_elo = self.team_data.get_elo(home_team)
        away_elo = self.team_data.get_elo(away_team)
        elo_diff = home_elo - away_elo
        abs_elo_diff = abs(elo_diff)

        # 获取当前概率（可能在 prediction 里或直接是 home_prob）
        if "prediction" in result:
            current_home_prob = result["prediction"]["home_win"]
        else:
            current_home_prob = result.get("home_prob", 0.4)

        # 强队主场大热容易被爆冷
        if elo_diff > 150:
            if current_home_prob > 0.60:
                upset_indicators += 1
                upset_reasons.append("强队主场大热")

        # ========== 2. Elo极端差距检测（新增）==========
        # 当Elo差距超过250时，弱队爆冷概率显著增加
        # Argentina(1966) vs Iceland(1575): 差距391 -> 极高爆冷风险
        if abs_elo_diff > 250:
            # 弱队被严重低估
            if elo_diff > 0:  # 主队强
                # 客队(away)弱但可能爆冷
                upset_indicators += 2  # 高权重
                upset_reasons.append(f"Elo极端差距({abs_elo_diff})")
            else:  # 客队强
                # 主队弱但可能爆冷
                upset_indicators += 2
                upset_reasons.append(f"Elo极端差距({abs_elo_diff})")
        elif abs_elo_diff > 180:
            # 中等Elo差距
            upset_indicators += 1
            upset_reasons.append(f"Elo大差距({abs_elo_diff})")

        # ========== 3. 弱队xG能力被低估（增强）==========
        # Argentina vs Iceland: xG 2.6 vs 0.82
        # 弱队xG不低但Elo很低 -> 明显被低估
        xg_adjustment = result.get("xg_adjustment", {})
        if xg_adjustment:
            home_xg = xg_adjustment.get("home_xg", 1.5)
            away_xg = xg_adjustment.get("away_xg", 1.5)
            
            # 计算xG比率
            if home_xg > 0.5 and away_xg > 0.5:
                xg_ratio = home_xg / away_xg if away_xg > 0 else 1.0
            else:
                xg_ratio = 1.0
            
            # 如果主队xG较高但ELO低（明显被低估）
            if home_xg > 1.2 and elo_diff < -100:
                upset_indicators += 1
                upset_reasons.append("弱队主场xG被低估")
            
            # 如果主队xG低但Elo高（强队进攻能力被高估）
            if home_xg < 1.0 and elo_diff > 150:
                upset_indicators += 1
                upset_reasons.append("强队进攻被高估")
            
            # xG差距极大但Elo差距更大（典型冷门场景）
            if abs_elo_diff > 200 and xg_ratio > 2.0:
                upset_indicators += 1
                upset_reasons.append("xG与Elo背离")

        # ========== 4. H2H显示客队有爆冷历史 ==========
        h2h_factor = self.h2h.get_h2h_factor(home_team, away_team)
        h2h_stats = self.h2h.get_h2h_stats(home_team, away_team)
        if h2h_stats.get("has_upsets"):
            upset_indicators += 1
            upset_reasons.append("H2H有爆冷历史")

        # ========== 5. 市场赔率大热检测 ==========
        odds_adjustment = result.get("odds_adjustment", {})
        if odds_adjustment.get("status") != "no_data":
            implied_home = odds_adjustment.get("implied_home", 0.4)
            # 如果市场显示主队概率远高于模型
            if implied_home - current_home_prob > 0.15:
                upset_indicators += 1
                upset_reasons.append("市场主队大热")

        # ========== 6. 战意因素（背水一战）==========
        # 通过group_standings判断
        group_standings = result.get("group_standings", {})
        if group_standings:
            # 0分球队背水一战，通常表现超预期
            home_points = group_standings.get(home_team, {}).get("points", -1)
            away_points = group_standings.get(away_team, {}).get("points", -1)
            
            # 0分 vs 3分或6分：背水一战可能被激发
            if home_points == 0 and abs_elo_diff > 150:
                upset_indicators += 1
                upset_reasons.append("主队0分背水一战")
            if away_points == 0 and abs_elo_diff > 150:
                upset_indicators += 1
                upset_reasons.append("客队0分背水一战")

        # ========== 应用冷门修正（增强版）==========
        # 此时 result 已经有 prediction 键
        if "prediction" in result:
            home_prob = result["prediction"]["home_win"]
            away_prob = result["prediction"]["away_win"]
            draw_prob = result["prediction"]["draw"]
        else:
            home_prob = result.get("home_prob", 0.4)
            away_prob = result.get("away_prob", 0.3)
            draw_prob = result.get("draw_prob", 0.3)

        # 大幅降低触发阈值，增加调整力度
        if upset_indicators >= 3:
            # 多个强信号，大幅降低热门概率
            adjustment = 0.15
            home_prob = max(0.20, home_prob - adjustment)
            away_prob = away_prob + adjustment * 0.65
            draw_prob = draw_prob + adjustment * 0.35
        elif upset_indicators >= 2:
            # 中等信号
            adjustment = 0.10
            home_prob = max(0.22, home_prob - adjustment)
            away_prob = away_prob + adjustment * 0.60
            draw_prob = draw_prob + adjustment * 0.40
        elif upset_indicators >= 1:
            # 单个信号，适度调整
            adjustment = 0.06
            home_prob = max(0.28, home_prob - adjustment)
            away_prob = away_prob + adjustment * 0.55
            draw_prob = draw_prob + adjustment * 0.45

        # 归一化
        total = home_prob + away_prob + draw_prob
        if total > 0:
            home_prob /= total
            away_prob /= total
            draw_prob /= total

        # 更新结果
        if "prediction" in result:
            result["prediction"]["home_win"] = home_prob
            result["prediction"]["away_win"] = away_prob
            result["prediction"]["draw"] = draw_prob
        else:
            result["home_prob"] = home_prob
            result["away_prob"] = away_prob
            result["draw_prob"] = draw_prob

        result["upset_correction"] = {
            "upset_indicators": upset_indicators,
            "has_upset_risk": upset_indicators >= 1,
            "upset_reasons": upset_reasons,
            "h2h_upset_possible": h2h_stats.get("has_upsets", False) if h2h_stats else False
        }

        return result

    def _apply_confidence_adjustment(self,
                                     base_result: Dict,
                                     xg_result: Dict,
                                     home_team: str,
                                     away_team: str) -> Dict:
        """
        预测信心调整

        当比赛结果不确定时，降低信心等级
        """
        result = base_result.copy()

        uncertainty_score = 0

        # 1. Elo差距中等（100-200）-> 不确定
        home_elo = self.team_data.get_elo(home_team)
        away_elo = self.team_data.get_elo(away_team)
        elo_diff = abs(home_elo - away_elo)

        if 80 < elo_diff < 180:
            uncertainty_score += 2  # 中等差距比赛更难预测
        elif elo_diff < 60:
            uncertainty_score += 1  # 非常接近也难预测

        # 2. xG总分低 -> 进球少，结果不确定
        xg_adjustment = xg_result.get("xg_adjustment", {})
        total_xg = xg_adjustment.get("total_xg", 2.0)
        if total_xg < 1.8:
            uncertainty_score += 1

        # 3. 胜平负概率接近
        home_prob = result["prediction"]["home_win"]
        draw_prob = result["prediction"]["draw"]
        away_prob = result["prediction"]["away_win"]
        max_prob = max(home_prob, draw_prob, away_prob)
        second_prob = sorted([home_prob, draw_prob, away_prob])[-2]
        prob_diff = max_prob - second_prob

        if max_prob < 0.55:  # 没有明显热门
            uncertainty_score += 2
        elif prob_diff < 0.15:  # 概率非常接近
            uncertainty_score += 1

        # 4. 双方风格相近
        home_style = self.team_styles.get(home_team, "")
        away_style = self.team_styles.get(away_team, "")
        if home_style == away_style and home_style in ["balanced", " possession"]:
            uncertainty_score += 1

        # 【新增】5. 数据不足时增加不确定性
        # 如果Elo是默认值（1700或1800），说明数据不足
        if home_elo == 1700 and away_elo == 1700:
            uncertainty_score += 2  # 数据严重不足
        elif home_elo == 1800 and away_elo == 1800:
            uncertainty_score += 1  # 数据可能不足

        # 应用不确定性调整 - 修改prob_diff而不是confidence字符串
        if uncertainty_score >= 3:
            # 大幅降低信心
            prob_diff *= 0.80
        elif uncertainty_score >= 2:
            prob_diff *= 0.90
        elif uncertainty_score >= 1:
            prob_diff *= 0.95

        # 重新计算信心等级（优化后的阈值）
        # 高信心：prob_diff > 20%（更严格，确保更高准确率）
        # 中信心：prob_diff > 12%
        # 低信心：prob_diff <= 12%
        if prob_diff > 0.20:
            confidence = "🟢 高信心"
        elif prob_diff > 0.12:
            confidence = "🟡 中信心"
        else:
            confidence = "🟡 低信心"

        result["prediction"]["confidence"] = confidence
        result["prediction"]["prob_diff"] = prob_diff

        # 重新计算recommended_team（如果prob_diff改变了）
        if max_prob == home_prob:
            result["prediction"]["recommended_team"] = home_team
        elif max_prob == away_prob:
            result["prediction"]["recommended_team"] = away_team
        else:
            result["prediction"]["recommended_team"] = "平局"

        result["uncertainty"] = {
            "uncertainty_score": uncertainty_score,
            "elo_uncertain": 80 < elo_diff < 180,
            "low_scoring": total_xg < 1.8,
            "close_probabilities": prob_diff < 0.15
        }

        return result

    def _apply_group_stage_adjustment(self,
                                       base_result: Dict,
                                       home_team: str,
                                       away_team: str,
                                       group_standings: Dict = None) -> Dict:
        """
        小组赛专项调整

        小组赛有以下特点：
        1. 爆冷概率更高（弱队可以接受平局，强队压力更大）
        2. 战意因素更复杂（已出线/已出局/需争胜）
        3. 球队表现更保守（避免受伤）
        4. 旅途和时差影响更大
        """
        result = base_result.copy()

        # ========== 1. 小组赛爆冷因子 ==========
        # 小组赛冷门概率约为淘汰赛的2倍
        # 当Elo差距大时，弱队更容易超水平发挥

        home_elo = self.team_data.get_elo(home_team)
        away_elo = self.team_data.get_elo(away_team)
        elo_diff = home_elo - away_elo

        # 强队(ELO>1900) vs 弱队(ELO<1750)时，弱队爆冷概率增加
        if home_elo > 1900 and away_elo < 1750:
            # 主场强队更容易被逼平或输球
            if result["prediction"]["home_win"] > 0.65:
                # 降低主队概率，增加冷门可能性
                upset_factor = 0.03
                result["prediction"]["home_win"] -= upset_factor
                result["prediction"]["away_win"] += upset_factor * 0.5
                result["prediction"]["draw"] += upset_factor * 0.5

        elif away_elo > 1900 and home_elo < 1750:
            # 客场强队相对稳定，但也有爆冷可能
            if result["prediction"]["away_win"] > 0.60:
                upset_factor = 0.02
                result["prediction"]["away_win"] -= upset_factor
                result["prediction"]["home_win"] += upset_factor * 0.4
                result["prediction"]["draw"] += upset_factor * 0.6

        # ========== 2. 战意调整 ==========
        if group_standings:
            home_points = group_standings.get("home", {}).get("points", 0)
            away_points = group_standings.get("away", {}).get("points", 0)

            # 已确保出线（6分）可能轮换
            if home_points >= 6:
                result["prediction"]["home_win"] -= 0.02
                result["prediction"]["draw"] += 0.01

            if away_points >= 6:
                result["prediction"]["away_win"] -= 0.02
                result["prediction"]["draw"] += 0.01

            # 背水一战（0分）增加拼劲
            if home_points == 0:
                result["prediction"]["home_win"] += 0.02
                result["prediction"]["away_win"] -= 0.01

            if away_points == 0:
                result["prediction"]["away_win"] += 0.02
                result["prediction"]["home_win"] -= 0.01

        # 归一化
        total = (result["prediction"]["home_win"] +
                 result["prediction"]["away_win"] +
                 result["prediction"]["draw"])
        result["prediction"]["home_win"] /= total
        result["prediction"]["away_win"] /= total
        result["prediction"]["draw"] /= total

        result["group_stage_adjustment"] = {
            "is_group_stage": True,
            "elo_diff": elo_diff,
            "has_standings_data": group_standings is not None
        }

        return result

    def _apply_knockout_adjustment(self,
                                    base_result: Dict,
                                    home_team: str,
                                    away_team: str,
                                    match_stage: str) -> Dict:
        """
        淘汰赛专项调整

        淘汰赛与小组赛有不同的规律：
        1. 球队踢得更保守
        2. 经验更重要
        3. 点球大战可能性高
        4. 强队优势更明显
        """
        result = base_result.copy()

        if match_stage not in ["knockout", "round_of_16", "quarterfinal", "semifinal", "third_place", "final"]:
            # 非淘汰赛，不做调整
            result["knockout_adjustment"] = {"is_knockout": False}
            return result

        # ========== 1. 淘汰赛保守因子 ==========
        # 淘汰赛进球通常更少
        knockout_conservative = 0.02

        # ========== 2. 经验调整 ==========
        # 有决赛经验的球队更有优势
        experienced_teams = {
            "Argentina": 3, "Germany": 4, "Brazil": 3, "France": 2,
            "Italy": 3, "Spain": 2, "England": 1, "Netherlands": 2,
            "Portugal": 1, "Croatia": 1
        }

        home_experience = experienced_teams.get(home_team, 0)
        away_experience = experienced_teams.get(away_team, 0)
        experience_diff = home_experience - away_experience

        # 经验差异带来的调整
        if match_stage in ["semifinal", "final"]:
            # 决赛阶段经验更重要
            experience_factor = 0.03 * experience_diff
        else:
            experience_factor = 0.02 * experience_diff

        # ========== 3. 点球大战调整 ==========
        # 当两队实力接近时，点球大战可能性增加
        home_elo = self.team_data.get_elo(home_team)
        away_elo = self.team_data.get_elo(away_team)
        elo_diff = abs(home_elo - away_elo)

        penalty_possible = False
        if elo_diff < 100 and match_stage in ["quarterfinal", "semifinal", "final"]:
            penalty_possible = True

        # ========== 4. 强队优势调整（微弱） ==========
        # 淘汰赛强队有一定优势，但不要过度调整
        if home_elo > away_elo:
            strong_team_advantage = 0.01
            result["prediction"]["home_win"] += strong_team_advantage
            result["prediction"]["away_win"] -= strong_team_advantage * 0.3
            result["prediction"]["draw"] -= strong_team_advantage * 0.7
        else:
            strong_team_advantage = 0.01
            result["prediction"]["away_win"] += strong_team_advantage
            result["prediction"]["home_win"] -= strong_team_advantage * 0.3
            result["prediction"]["draw"] -= strong_team_advantage * 0.7

        # ========== 5. 应用经验调整（微弱） ==========
        if experience_diff > 0:
            experience_factor = 0.01 * experience_diff
            result["prediction"]["home_win"] += experience_factor
            result["prediction"]["away_win"] -= experience_factor * 0.3
            result["prediction"]["draw"] -= experience_factor * 0.7
        elif experience_diff < 0:
            experience_factor = 0.01 * abs(experience_diff)
            result["prediction"]["away_win"] += experience_factor
            result["prediction"]["home_win"] -= experience_factor * 0.3
            result["prediction"]["draw"] -= experience_factor * 0.7

        # 归一化
        total = result["prediction"]["home_win"] + result["prediction"]["away_win"] + result["prediction"]["draw"]
        result["prediction"]["home_win"] /= total
        result["prediction"]["away_win"] /= total
        result["prediction"]["draw"] /= total

        result["knockout_adjustment"] = {
            "is_knockout": True,
            "stage": match_stage,
            "experience_diff": experience_diff,
            "penalty_possible": penalty_possible,
            "elo_diff": elo_diff
        }

        return result


    def _apply_draw_detection(self,
                               base_result: Dict,
                               home_team: str,
                               away_team: str,
                               xg_result: Dict) -> Dict:
        """
        平局专项检测

        针对平局进行专项检测和调整
        """
        result = base_result.copy()

        # 获取概率（可能来自prediction键或直接是概率）
        if "prediction" in base_result:
            home_prob = base_result["prediction"]["home_win"]
            away_prob = base_result["prediction"]["away_win"]
            draw_prob = base_result["prediction"]["draw"]
        else:
            home_prob = base_result.get("home_prob", 0.40)
            away_prob = base_result.get("away_prob", 0.30)
            draw_prob = base_result.get("draw_prob", 0.30)

        draw_score = 0  # 平局可能性评分
        draw_indicators = []

        # ========== 1. H2H平局历史 ==========
        h2h_stats = self.h2h.get_h2h_stats(home_team, away_team)
        if h2h_stats["total"] >= 2:
            draw_rate = h2h_stats["draws"] / h2h_stats["total"]
            if draw_rate >= 0.4:
                draw_score += 2
                draw_indicators.append(f"H2H平局率{draw_rate:.0%}")
            elif draw_rate >= 0.25:
                draw_score += 1
                draw_indicators.append(f"H2H平局率{draw_rate:.0%}")

        # ========== 2. Elo差距 -> 平局率分析数据 ==========
        # 数据分析发现：
        # - Elo差距<80: 24.2%平局率
        # - Elo差距80-120: 10.7%平局率 ← 最低！
        # - Elo差距120-180: 33.3%平局率 ← 最高！
        # - Elo差距>180: 19.0%平局率
        # 所以中等差距(120-180)反而最容易平局！
        home_elo = self.team_data.get_elo(home_team)
        away_elo = self.team_data.get_elo(away_team)
        elo_diff = abs(home_elo - away_elo)

        if 120 <= elo_diff < 180:
            # 中等差距 - 最高平局率！
            draw_score += 2
            draw_indicators.append("Elo中等差距(高平局区)")
        elif elo_diff < 80:
            # 极小差距 - 中等平局率
            draw_score += 1
            draw_indicators.append("Elo差距极小")
        # elo_diff在80-120区间平局率最低，不加分
        # elo_diff>180区间平局率也较低，不加分

        # ========== 3. 低xG比赛 ==========
        xg_adjustment = xg_result.get("xg_adjustment", {})
        total_xg = xg_adjustment.get("total_xg", 2.0)
        home_xg = xg_adjustment.get("home_xg", 1.5)
        away_xg = xg_adjustment.get("away_xg", 1.5)

        if total_xg < 1.8:
            draw_score += 1
            draw_indicators.append(f"总xG低({total_xg:.1f})")

        # xG差距小 -> 更容易平局
        xg_diff_ratio = abs(home_xg - away_xg) / max(home_xg, away_xg, 0.5)
        if xg_diff_ratio < 0.2:
            draw_score += 1
            draw_indicators.append("xG差距极小")

        # ========== 4. 双方都是防守型球队 ==========
        home_style = self.team_styles.get(home_team, "")
        away_style = self.team_styles.get(away_team, "")

        defensive_styles = ["defensive", " counter", "balanced"]
        if home_style in defensive_styles and away_style in defensive_styles:
            draw_score += 1
            draw_indicators.append("双方防守型")

        # ========== 5. 淘汰赛后期阶段 ==========
        # 淘汰赛越到后期，平局越多（点球大战）
        stage = base_result.get("match_stage", "group")
        if stage in ["quarterfinal", "semifinal", "third_place", "final"]:
            draw_score += 1
            draw_indicators.append(f"{stage}阶段")

        # ========== 6. 重要大赛决赛/半决赛 ==========
        # 决赛半决赛通常保守
        if stage in ["semifinal", "final"]:
            draw_score += 1
            draw_indicators.append("大赛关键战")

        # ========== 7. 小组赛平局专项（新增）==========
        # 小组赛各队更保守，策略性强，平局率通常更高（25-30%）
        # 小组赛前两轮：各队还在试探，保守为主
        # 小组赛第三轮：形势复杂，可能出现默契平局
        if stage == "group":
            # 小组赛前两轮：保守为主
            match_day = base_result.get("match_day", 2)  # 默认第2轮
            if match_day <= 2:
                draw_score += 1
                draw_indicators.append(f"小组赛{match_day}轮保守")
            # 小组赛第三轮：已有分数的球队可能默契
            elif match_day == 3:
                # 检查是否已有分数（可能默契平局）
                group_standings = base_result.get("group_standings", {})
                if group_standings:
                    # 获取两队积分
                    home_pts = group_standings.get(home_team, {}).get("points", 0)
                    away_pts = group_standings.get(away_team, {}).get("points", 0)
                    # 如果两队都有分数且不需要全力争胜
                    if home_pts > 0 and away_pts > 0 and elo_diff < 150:
                        draw_score += 1
                        draw_indicators.append("小组赛默契平局可能")
            
            # 同组实力接近的球队更容易平局
            if abs(elo_diff) < 100:
                draw_score += 1
                draw_indicators.append("同组实力接近")

        # ========== 应用平局调整 ==========
        # 降低触发阈值，增加调整力度
        # draw_score >= 4: 较大概率高平局，增加8%
        # draw_score >= 3: 中等平局可能性，增加5%
        # draw_score >= 2: 轻微平局倾向，增加2%
        # draw_score >= 1: 极轻微，增加1%

        if draw_score >= 4:
            # 高平局可能性
            draw_boost = 0.08
            new_draw_prob = min(0.45, draw_prob + draw_boost)
            # 从主队和客队概率中扣除
            reduction = (draw_boost) / 2
            new_home_prob = max(0.20, home_prob - reduction)
            new_away_prob = max(0.20, away_prob - reduction)
        elif draw_score >= 3:
            # 中等平局可能性
            draw_boost = 0.05
            new_draw_prob = min(0.40, draw_prob + draw_boost)
            reduction = (draw_boost) / 2
            new_home_prob = max(0.25, home_prob - reduction)
            new_away_prob = max(0.20, away_prob - reduction)
        elif draw_score >= 2:
            # 轻微平局倾向
            draw_boost = 0.03
            new_draw_prob = min(0.35, draw_prob + draw_boost)
            reduction = (draw_boost) / 2
            new_home_prob = home_prob - reduction
            new_away_prob = away_prob - reduction
        elif draw_score >= 1:
            # 极轻微
            draw_boost = 0.015
            new_draw_prob = draw_prob + draw_boost
            new_home_prob = home_prob
            new_away_prob = away_prob
        # 归一化
        total = new_home_prob + new_away_prob + new_draw_prob
        new_home_prob /= total
        new_away_prob /= total
        new_draw_prob /= total

        # 更新prediction
        result["prediction"]["home_win"] = new_home_prob
        result["prediction"]["away_win"] = new_away_prob
        result["prediction"]["draw"] = new_draw_prob

        result["draw_detection"] = {
            "draw_score": draw_score,
            "draw_indicators": draw_indicators,
            "is_high_draw_risk": draw_score >= 3,
            "h2h_draw_rate": h2h_stats["draws"] / h2h_stats["total"] if h2h_stats["total"] > 0 else 0,
            "elo_diff": elo_diff,
            "total_xg": total_xg
        }

        return result


# ============ 便捷函数 ============
def quick_predict(home: str, away: str, **kwargs) -> Dict:
    """快速预测"""
    predictor = UnifiedPredictor()
    return predictor.predict(home, away, **kwargs)


# ============ 测试 ============
if __name__ == "__main__":
    predictor = UnifiedPredictor()

    print("=" * 60)
    print("统一预测引擎 v5.1 测试（新增4大模块）")
    print("=" * 60)

    # 测试：德国 vs 日本
    result = predictor.predict(
        home_team="Germany",
        away_team="Japan",
        home_last_match_date=datetime.now() - timedelta(days=5),
        away_last_match_date=datetime.now() - timedelta(days=4),
        match_date=datetime.now(),
        venue="Munich",
        weather={"temp": 18, "humidity": 60, "precipitation": 0, "wind": 10},
        group_standings={"home": {"points": 3}, "away": {"points": 0}},
        odds={"home": 1.7, "draw": 3.5, "away": 4.5},
        opening_odds={"home": 1.8, "draw": 3.3, "away": 4.2},
        referee="Mateu Lahoz"
    )

    pred = result["prediction"]
    print(f"\n🏆 德国 vs 日本")
    print(f"胜平负: 德国 {pred['home_win']:.1%} | 平局 {pred['draw']:.1%} | 日本 {pred['away_win']:.1%}")
    print(f"推荐: {pred['recommended_team']} 胜 {pred['confidence']}")
    print(f"xG: 德国 {pred['home_xg']} | 日本 {pred['away_xg']}")
    print(f"比分: {result['scores'][0]['score']} ({result['scores'][0]['prob']:.0f}%)")

    # 显示各模块分析
    print("\n📊 各模块分析:")
    modules = result["modules"]

    print(f"  Elo: 主队Elo {modules['elo']['home_elo']} vs 客队 {modules['elo']['away_elo']}")

    # H2H
    h2h = modules.get('h2h', {}).get('h2h_adjustment', {})
    if h2h:
        print(f"  H2H: {h2h.get('total_matches', 0)}场对战, 主队{h2h.get('home_wins', 0)}胜")

    # 裁判
    ref = modules.get('referee', {}).get('referee_adjustment', {})
    if ref and ref.get('found'):
        print(f"  裁判: {ref.get('referee')} ({ref.get('style')})")
    elif ref:
        print(f"  裁判: 未找到数据")

    # 赔率变化
    odds_mv = modules.get('odds_movement', {}).get('odds_movement_adjustment', {})
    if odds_mv and odds_mv.get('has_data') != False:
        print(f"  赔率变化: {odds_mv.get('direction', 'N/A')}, 波动{odds_mv.get('volatility', 0):.1f}%")
    else:
        print(f"  赔率变化: 无数据")

    # xG
    xg = modules.get('xg', {}).get('xg_adjustment', {})
    if xg:
        print(f"  xG: {xg.get('home_xg', 'N/A')} - {xg.get('away_xg', 'N/A')}, 总计{xg.get('total_xg', 'N/A')}")
        print(f"  进攻vs防守: {xg.get('attack_vs_defense', 'N/A')}")
    fatigue = modules.get('fatigue', {}).get('fatigue_adjustment', {})
    if fatigue:
        print(f"  疲劳: 主队休息{fatigue.get('home_rest_days', 'N/A')}天, 客队休息{fatigue.get('away_rest_days', 'N/A')}天")
    style = modules.get('style', {}).get('style_adjustment', {})
    if style:
        print(f"  风格: {style.get('home_style', 'N/A')} vs {style.get('away_style', 'N/A')}")
    weather = modules.get('weather', {}).get('weather_adjustment', {})
    if weather:
        print(f"  天气: {weather.get('weather_description', 'N/A')}")
    handicap = modules.get('handicap', {}).get('handicap_adjustment', {})
    if handicap:
        print(f"  让球: {handicap.get('handicap', 0):+.1f}")
