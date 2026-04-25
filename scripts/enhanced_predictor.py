#!/usr/bin/env python3
"""
增强版预测脚本
整合博彩赔率和Elo动态更新

使用方法:
    python3 enhanced_predictor.py --match "Arsenal" "Liverpool"
"""

import argparse
import json
import os
import sys
from datetime import datetime
from typing import Dict

# 路径配置
BASE_DIR = os.path.expanduser("~/hermes-world-cup/")
sys.path.insert(0, os.path.join(BASE_DIR, "scripts"))

from elo_dynamic_updater import EloDynamicUpdater
from enhanced_bookmaker_odds import BookmakerOddsIntegrator


class EnhancedPredictor:
    """
    增强版预测器
    
    整合:
    1. Elo动态更新 - 根据历史比赛实时调整球队实力
    2. 博彩赔率融合 - 接入市场智慧
    3. 多维度分析 - 综合多个数据源
    """
    
    def __init__(self):
        self.elo_updater = EloDynamicUpdater()
        self.odds_integrator = BookmakerOddsIntegrator()
        
    def predict(
        self, 
        home_team: str, 
        away_team: str,
        use_elo_update: bool = True,
        use_bookmaker: bool = True
    ) -> Dict:
        """
        增强预测
        
        Args:
            home_team: 主队
            away_team: 客队
            use_elo_update: 是否使用动态Elo
            use_bookmaker: 是否使用博彩赔率
            
        Returns:
            预测结果
        """
        result = {
            "match": f"{home_team} vs {away_team}",
            "timestamp": datetime.now().isoformat(),
            "components": {}
        }
        
        # 1. Elo评分（可动态更新）
        if use_elo_update:
            elo_home = self.elo_updater.elo_system.get_rating(home_team)
            elo_away = self.elo_updater.elo_system.get_rating(away_team)
        else:
            elo_home = self.elo_updater.elo_system.get_rating(home_team)
            elo_away = self.elo_updater.elo_system.get_rating(away_team)
        
        result["components"]["elo"] = {
            "home": elo_home,
            "away": elo_away,
            "diff": elo_home - elo_away
        }
        
        # 2. 博彩赔率分析
        if use_bookmaker:
            odds_analysis = self.odds_integrator.analyze_match(home_team, away_team)
            if odds_analysis:
                result["components"]["bookmaker"] = {
                    "probabilities": odds_analysis["win_probabilities"],
                    "best_odds": odds_analysis["best_odds"],
                    "anomalies": odds_analysis.get("anomalies", [])
                }
        
        # 3. 综合预测
        model_probs = self._calculate_model_probs(elo_home, elo_away)
        
        if use_bookmaker and odds_analysis:
            bookmaker_probs = odds_analysis["win_probabilities"]
            # 融合：模型40% + 博彩60%
            fused_probs = self.odds_integrator.fuse_with_model(
                model_probs, 
                bookmaker_probs,
                model_weight=0.40
            )
            result["prediction"] = {
                "probabilities": fused_probs,
                "recommended": max(fused_probs, key=fused_probs.get),
                "confidence": max(fused_probs.values())
            }
        else:
            result["prediction"] = {
                "probabilities": model_probs,
                "recommended": max(model_probs, key=model_probs.get),
                "confidence": max(model_probs.values())
            }
        
        return result
    
    def _calculate_model_probs(self, elo_home: float, elo_away: float) -> Dict[str, float]:
        """基于Elo计算基础概率"""
        # Elo差距转胜率
        elo_diff = elo_home - elo_away
        
        # 使用Elo公式计算
        home_win_prob = 1 / (1 + 10 ** ((elo_away - elo_home) / 400))
        away_win_prob = 1 / (1 + 10 ** ((elo_home - elo_away) / 400))
        
        # 平局概率（根据历史数据约25-28%）
        draw_prob = 1 - home_win_prob - away_win_prob
        
        return {
            "home": home_win_prob,
            "draw": max(draw_prob, 0.20),  # 最低20%
            "away": away_win_prob
        }
    
    def print_prediction(self, home_team: str, away_team: str):
        """打印预测结果"""
        pred = self.predict(home_team, away_team)
        
        print(f"\n{'='*60}")
        print(f"⚽ 增强预测: {pred['match']}")
        print(f"{'='*60}")
        
        # Elo评分
        elo = pred["components"]["elo"]
        print(f"\n📊 Elo评分:")
        print(f"   {home_team}: {elo['home']:.0f}")
        print(f"   {away_team}: {elo['away']:.0f}")
        print(f"   差距: {elo['diff']:+.0f}")
        
        # 博彩赔率
        if "bookmaker" in pred["components"]:
            bm = pred["components"]["bookmaker"]
            probs = bm["probabilities"]
            print(f"\n🏦 博彩公司分析:")
            print(f"   主队概率: {probs['home']*100:.1f}%")
            print(f"   平局概率: {probs['draw']*100:.1f}%")
            print(f"   客队概率: {probs['away']*100:.1f}%")
            
            # 异常
            anomalies = bm.get("anomalies", [])
            if anomalies:
                print(f"\n⚠️ 赔率异常:")
                for a in anomalies[:2]:
                    print(f"   [{a['type']}] {a['team']} @ {a['bookmaker']}")
        
        # 最终预测
        final = pred["prediction"]
        probs = final["probabilities"]
        print(f"\n🎯 综合预测:")
        print(f"   主队胜: {probs['home']*100:.1f}%")
        print(f"   平局: {probs['draw']*100:.1f}%")
        print(f"   客队胜: {probs['away']*100:.1f}%")
        print(f"\n   推荐: {final['recommended'].upper()}")
        print(f"   置信度: {final['confidence']*100:.1f}%")
        print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(description="增强版预测工具")
    parser.add_argument("--match", nargs=2, metavar=("HOME", "AWAY"), help="比赛")
    parser.add_argument("--list", action="store_true", help="列出可用比赛")
    parser.add_argument("--no-elo", action="store_true", help="不使用动态Elo")
    parser.add_argument("--no-bookmaker", action="store_true", help="不使用博彩赔率")
    
    args = parser.parse_args()
    
    predictor = EnhancedPredictor()
    
    if args.list:
        matches = predictor.odds_integrator.odds_data.get("matches", [])
        print(f"\n📋 共有 {len(matches)} 场比赛的赔率数据:")
        for m in matches:
            print(f"  {m.get('home_team')} vs {m.get('away_team')}")
        return
    
    if args.match:
        home, away = args.match
        predictor.print_prediction(home, away)
        return
    
    # 默认测试
    print("⚽ 增强预测测试:")
    test_matches = [
        ("Arsenal", "Liverpool"),
        ("Manchester City", "Chelsea"),
        ("Brentford", "Fulham")
    ]
    
    for home, away in test_matches:
        predictor.print_prediction(home, away)


if __name__ == "__main__":
    main()
