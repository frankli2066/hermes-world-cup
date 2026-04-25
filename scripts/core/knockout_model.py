#!/usr/bin/env python3
"""
淘汰赛和点球大战模型 v2.0

功能：
1. 淘汰赛阶段调整
2. 加时赛模拟
3. 点球大战预测
4. 比赛压力模型
"""

import numpy as np
import random
from typing import Dict, Tuple, Optional, List
from dataclasses import dataclass


@dataclass
class KnockoutConfig:
    """淘汰赛配置"""
    # 加时赛配置
    overtime_enabled: bool = True
    overtime_duration: int = 30  # 分钟
    extra_time_home_advantage: float = 0.05  # 加时赛主场优势减少
    
    # 点球配置
    penalty_rounds: int = 5
    sudden_death: bool = True
    
    # 压力系数
    final_pressure: float = 1.15  # 决赛压力
    semi_pressure: float = 1.08  # 半决赛压力
    quarter_pressure: float = 1.03  # 8强压力


class KnockoutModel:
    """淘汰赛模型 v2.0"""
    
    def __init__(self, config: KnockoutConfig = None):
        self.config = config or KnockoutConfig()
        
        # 各阶段压力系数
        self.stage_pressure = {
            "final": self.config.final_pressure,
            "third_place": 1.05,
            "semi": self.config.semi_pressure,
            "quarter": self.config.quarter_pressure,
            "round_of_16": 1.0,
            "round16": 1.0,
            "group": 1.0,
        }
        
        # 关键球员压力处理能力（简化版）
        self.pressure_handling = {
            # 球队: (大赛经验系数, 关键球员冷静度)
            "Brazil": (1.2, 1.1),
            "Germany": (1.25, 1.15),
            "France": (1.15, 1.1),
            "Argentina": (1.18, 1.12),
            "Spain": (1.1, 1.05),
            "Italy": (1.2, 1.15),
            "England": (1.05, 1.0),
            "Netherlands": (1.1, 1.05),
            "Portugal": (1.08, 1.02),
            "Uruguay": (1.1, 1.05),
        }
    
    def get_stage_pressure(self, stage: str) -> float:
        """获取比赛阶段压力系数"""
        return self.stage_pressure.get(stage, 1.0)
    
    def get_pressure_handling(self, team: str) -> Tuple[float, float]:
        """获取球队的压力处理能力"""
        return self.pressure_handling.get(team, (1.0, 1.0))
    
    def adjust_for_stage(
        self,
        home_win_prob: float,
        away_win_prob: float,
        draw_prob: float,
        stage: str
    ) -> Tuple[float, float, float]:
        """
        根据比赛阶段调整概率
        
        淘汰赛特点：
        - 决赛/关键比赛强队胜率更高（压力下强队更稳定）
        - 平局概率增加（保守打法）
        """
        if stage == "group":
            return home_win_prob, draw_prob, away_win_prob
        
        pressure = self.get_stage_pressure(stage)
        
        # 计算优势差距
        prob_diff = home_win_prob - away_win_prob
        
        # 压力调整：强队（概率高的一方）压力下表现更好
        if prob_diff > 0:
            # 主队更强
            adjustment = abs(prob_diff) * (pressure - 1.0)
            home_win_prob += adjustment
            away_win_prob -= adjustment * 0.5
            draw_prob -= adjustment * 0.5
        elif prob_diff < 0:
            # 客队更强
            adjustment = abs(prob_diff) * (pressure - 1.0)
            away_win_prob += adjustment
            home_win_prob -= adjustment * 0.5
            draw_prob -= adjustment * 0.5
        else:
            # 实力相近，平局概率增加
            draw_prob *= pressure
        
        # 归一化
        total = home_win_prob + draw_prob + away_win_prob
        return home_win_prob/total, draw_prob/total, away_win_prob/total
    
    def simulate_overtime(
        self,
        home_xg: float,
        away_xg: float,
        home_elo: float,
        away_elo: float,
        stage: str,
        monte_carlo: int = 5000
    ) -> Dict:
        """
        模拟加时赛（30分钟）
        
        加时赛特点：
        - 体能下降导致进球率降低
        - 主场优势减少
        - 压力下保守
        """
        # 加时赛xG调整（30分钟 = 0.5场）
        ot_factor = 0.5
        
        # 体能消耗：每15分钟降低约5%
        ot_home_xg = home_xg * ot_factor * 0.9
        ot_away_xg = away_xg * ot_factor * 0.9
        
        # 主场优势减少
        home_adv_reduction = self.config.extra_time_home_advantage
        if home_elo > away_elo:
            # 强队主场优势减少更多
            elo_advantage = (home_elo - away_elo) / 100
            home_adv_reduction *= (1 + elo_advantage * 0.1)
        
        ot_home_xg *= (1 - home_adv_reduction)
        
        # 蒙特卡洛模拟
        home_wins_ot, away_wins_ot, draws_ot = 0, 0, 0
        home_goals_ot, away_goals_ot = [], []
        
        for _ in range(monte_carlo):
            h = max(0, np.random.poisson(ot_home_xg))
            a = max(0, np.random.poisson(ot_away_xg))
            
            home_goals_ot.append(h)
            away_goals_ot.append(a)
            
            if h > a:
                home_wins_ot += 1
            elif h < a:
                away_wins_ot += 1
            else:
                draws_ot += 1
        
        total = monte_carlo
        
        return {
            "prob_home_wins_ot": home_wins_ot / total,
            "prob_away_wins_ot": away_wins_ot / total,
            "prob_draw_ot": draws_ot / total,
            "avg_home_goals_ot": sum(home_goals_ot) / total,
            "avg_away_goals_ot": sum(away_goals_ot) / total,
            "requires_penalties": draws_ot / total,
        }
    
    def simulate_penalty_shootout(
        self,
        home_team: str,
        away_team: str,
        home_elo: int,
        away_elo: int,
        monte_carlo: int = 10000
    ) -> Dict:
        """
        模拟点球大战
        
        点球大战模型：
        - 每轮5球机会
        - 考虑球队压力处理能力
        - 强队点球命中率更高
        """
        home_exp, home_composure = self.get_pressure_handling(home_team)
        away_exp, away_composure = self.get_pressure_handling(away_team)
        
        # 基础点球成功率（根据Elo调整）
        home_base = 0.75 + (home_elo - 1700) / 2000 * 0.15
        away_base = 0.75 + (away_elo - 1700) / 2000 * 0.15
        
        # 调整
        home_success_rate = min(0.95, max(0.55, home_base * home_composure))
        away_success_rate = min(0.95, max(0.55, away_base * away_composure))
        
        home_wins_pen, away_wins_pen = 0, 0
        
        for _ in range(monte_carlo):
            # 模拟5轮点球
            home_score = 0
            away_score = 0
            
            for i in range(5):
                if np.random.random() < home_success_rate:
                    home_score += 1
                if np.random.random() < away_success_rate:
                    away_score += 1
                
                # 提前结束：如果一方即使最好情况也追不上
                remaining = 5 - i - 1
                if home_score > away_score + remaining:
                    break
                if away_score > home_score + remaining:
                    break
            
            # 突然死亡
            if home_score == away_score:
                sudden_death = True
                while sudden_death:
                    if np.random.random() < home_success_rate:
                        home_score += 1
                    if np.random.random() < away_success_rate:
                        away_score += 1
                    
                    if home_score != away_score:
                        sudden_death = False
            
            if home_score > away_score:
                home_wins_pen += 1
            else:
                away_wins_pen += 1
        
        total = monte_carlo
        
        return {
            "prob_home_wins_pen": home_wins_pen / total,
            "prob_away_wins_pen": away_wins_pen / total,
            "home_penalty_success_rate": home_success_rate,
            "away_penalty_success_rate": away_success_rate,
        }
    
    def predict_knockout(
        self,
        home_team: str,
        away_team: str,
        home_elo: int,
        away_elo: int,
        home_xg: float,
        away_xg: float,
        stage: str = "round_of_16",
        monte_carlo: int = 10000,
        include_penalties: bool = True
    ) -> Dict:
        """
        预测淘汰赛结果（包括点球）
        
        Args:
            home_team: 主队
            away_team: 客队
            home_elo: 主队Elo
            away_elo: 客队Elo
            home_xg: 主队预期进球
            away_xg: 客队预期进球
            stage: 比赛阶段
            monte_carlo: 模拟次数
            include_penalties: 是否计算点球概率
        
        Returns:
            淘汰赛预测结果
        """
        # 阶段压力调整
        pressure = self.get_stage_pressure(stage)
        
        # 90分钟模拟
        score_counts = {}
        home_wins_90, away_wins_90, draws_90 = 0, 0, 0
        
        # 考虑压力调整的xG
        adj_home_xg = home_xg * (1.0 if home_elo >= away_elo else 1.0 - (pressure - 1))
        adj_away_xg = away_xg * (1.0 if away_elo >= home_elo else 1.0 - (pressure - 1))
        
        # 方差调整
        variance = 1.15 if stage in ["quarter", "semi", "final"] else 1.20
        
        for _ in range(monte_carlo):
            h = max(0, np.random.poisson(adj_home_xg * variance))
            a = max(0, np.random.poisson(adj_away_xg * variance))
            
            score_counts[(h, a)] = score_counts.get((h, a), 0) + 1
            
            if h > a:
                home_wins_90 += 1
            elif h < a:
                away_wins_90 += 1
            else:
                draws_90 += 1
        
        total = monte_carlo
        
        # 90分钟结果
        prob_home_90 = home_wins_90 / total
        prob_away_90 = away_wins_90 / total
        prob_draw_90 = draws_90 / total
        
        # 加时赛（如果打平）
        if self.config.overtime_enabled and prob_draw_90 > 0.1:
            ot_result = self.simulate_overtime(
                home_xg, away_xg, home_elo, away_elo, stage,
                monte_carlo=min(monte_carlo, 5000)
            )
            
            # 加时赛结果（只考虑打平的情况）
            prob_home_ot = ot_result["prob_home_wins_ot"] * prob_draw_90
            prob_away_ot = ot_result["prob_away_wins_ot"] * prob_draw_90
            prob_draw_after_ot = ot_result["prob_draw_ot"] * prob_draw_90
        else:
            prob_home_ot = 0
            prob_away_ot = 0
            prob_draw_after_ot = 0 if prob_draw_90 == 0 else 0.05
        
        # 点球大战（如果加时赛还是打平）
        if include_penalties and (prob_draw_90 + prob_draw_after_ot) > 0.05:
            pen_result = self.simulate_penalty_shootout(
                home_team, away_team, home_elo, away_elo,
                monte_carlo=min(monte_carlo, 5000)
            )
            
            # 实际需要点球的概率
            pen_prob = (prob_draw_90 + prob_draw_after_ot) * 0.5
            prob_home_pen = pen_result["prob_home_wins_pen"] * pen_prob
            prob_away_pen = pen_result["prob_away_wins_pen"] * pen_prob
        else:
            pen_result = None
            prob_home_pen = 0
            prob_away_pen = 0
        
        # 总概率
        prob_home_total = prob_home_90 + prob_home_ot + prob_home_pen
        prob_away_total = prob_away_90 + prob_away_ot + prob_away_pen
        
        # 归一化
        total_prob = prob_home_total + prob_away_total
        if total_prob > 0:
            prob_home_total /= total_prob
            prob_away_total /= total_prob
            prob_draw = 1 - prob_home_total - prob_away_total
        else:
            prob_home_total = 0.5
            prob_away_total = 0.5
            prob_draw = 0
        
        # 最可能比分
        most_likely = max(score_counts.items(), key=lambda x: x[1])
        most_likely_score = f"{most_likely[0][0]}-{most_likely[0][1]}"
        
        return {
            "home_team": home_team,
            "away_team": away_team,
            "stage": stage,
            
            # 90分钟
            "prob_home_90min": round(prob_home_90, 3),
            "prob_draw_90min": round(prob_draw_90, 3),
            "prob_away_90min": round(prob_away_90, 3),
            
            # 加时赛（如果需要）
            "prob_overtime": round(prob_draw_90, 3) if self.config.overtime_enabled else 0,
            "prob_home_overtime": round(prob_home_ot, 3),
            "prob_away_overtime": round(prob_away_ot, 3),
            
            # 点球（如果需要）
            "prob_penalties": round(prob_home_pen + prob_away_pen, 3),
            "prob_home_penalties": round(prob_home_pen, 3),
            "prob_away_penalties": round(prob_away_pen, 3),
            
            # 最终结果
            "prob_home_total": round(prob_home_total, 3),
            "prob_away_total": round(prob_away_total, 3),
            "prob_draw": round(max(0, prob_draw), 3),
            
            # 关键数据
            "pressure_factor": pressure,
            "most_likely_score_90min": most_likely_score,
            "most_likely_prob": round(most_likely[1] / total, 3),
            
            # 点球数据
            "penalty_details": pen_result,
            
            "monte_carlo_runs": monte_carlo,
        }
    
    def get_confidence(self, prob: float) -> Tuple[str, float]:
        """
        获取预测置信度
        
        Returns:
            (等级描述, 置信度百分比)
        """
        if prob >= 0.75:
            return "高置信度", 0.90
        elif prob >= 0.60:
            return "中等置信度", 0.75
        elif prob >= 0.45:
            return "低置信度", 0.60
        else:
            return "不确定", 0.50


# 兼容性
KnockoutSimulator = KnockoutModel


if __name__ == "__main__":
    km = KnockoutModel()
    
    print("=== 淘汰赛模型测试 ===\n")
    
    # 决赛预测
    result = km.predict_knockout(
        "France", "Argentina",
        home_elo=1974, away_elo=1920,
        home_xg=1.85, away_xg=1.65,
        stage="final",
        monte_carlo=5000
    )
    
    print(f"法国 vs 阿根廷 (决赛):")
    print(f"  90分钟: {result['prob_home_90min']*100:.0f}% - {result['prob_draw_90min']*100:.0f}% - {result['prob_away_90min']*100:.0f}%")
    print(f"  总计:   {result['prob_home_total']*100:.0f}% - {result['prob_away_total']*100:.0f}%")
    print(f"  压力系数: {result['pressure_factor']}")
    if result['penalty_details']:
        print(f"  点球胜率: 法{result['penalty_details']['home_penalty_success_rate']*100:.0f}% vs 阿{result['penalty_details']['away_penalty_success_rate']*100:.0f}%")
    print()
    
    # 16强预测
    result2 = km.predict_knockout(
        "Brazil", "Mexico",
        home_elo=1982, away_elo=1780,
        home_xg=1.95, away_xg=1.20,
        stage="round_of_16",
        monte_carlo=5000
    )
    
    print(f"Brazil vs Mexico (16强):")
    print(f"  90分钟: {result2['prob_home_90min']*100:.0f}% - {result2['prob_draw_90min']*100:.0f}% - {result2['prob_away_90min']*100:.0f}%")
    print(f"  总计:   {result2['prob_home_total']*100:.0f}% - {result2['prob_away_total']*100:.0f}%")
