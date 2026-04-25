#!/usr/bin/env python3
"""
博彩赔率整合增强脚本
接入多个博彩公司赔率，提高预测精度

支持的博彩公司:
- Pinnacle: 最精准的职业赔率
- Bet365: 最流行的博彩公司
- 1xBet: 综合赔率
- OddsJam: 赔率聚合
- Betway: 欧洲主流
- Unibet: 北欧主流

使用方法:
    python3 enhanced_bookmaker_odds.py --fetch
    python3 enhanced_bookmaker_odds.py --analyze "Arsenal" "Liverpool"
"""

import argparse
import json
import os
import sys
import math
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# 路径配置
BASE_DIR = os.path.expanduser("~/hermes-world-cup/")
ODDS_FILE = os.path.join(BASE_DIR, "data/multi_bookmaker_odds.json")
BOOKMAKER_CACHE = os.path.join(BASE_DIR, "data/bookmaker_cache.json")

sys.path.insert(0, os.path.join(BASE_DIR, "scripts"))


class BookmakerOddsIntegrator:
    """
    博彩赔率整合器
    
    功能:
    1. 从多个博彩公司获取赔率
    2. 计算综合隐含概率
    3. 检测赔率异常
    4. 融合到预测模型
    """
    
    # 博彩公司权重（根据历史准确率）
    BOOKMAKER_WEIGHTS = {
        "pinnacle": 0.25,      # 最精准的职业赔率
        "oddsjam": 0.20,       # 赔率聚合
        "bet365": 0.18,        # 最流行
        "1xbet": 0.12,
        "betway": 0.12,
        "unibet": 0.08,
        "marathonbet": 0.05,   # 欧洲小众但精准
    }
    
    def __init__(self):
        self.odds_data = self._load_odds_data()
        
    def _load_odds_data(self) -> Dict:
        """加载赔率数据"""
        if os.path.exists(ODDS_FILE):
            with open(ODDS_FILE) as f:
                return json.load(f)
        return {"matches": []}
    
    def _save_odds_data(self):
        """保存赔率数据"""
        with open(ODDS_FILE, "w") as f:
            json.dump(self.odds_data, f, indent=2, ensure_ascii=False)
    
    def odds_to_probability(self, odds: float) -> float:
        """
        赔率转隐含概率
        
        Args:
            odds: 十进制赔率 (如 2.0)
            
        Returns:
            隐含概率 (如 0.50)
        """
        if odds <= 0:
            return 0
        return 1 / odds
    
    def probability_to_odds(self, prob: float) -> float:
        """
        概率转赔率
        
        Args:
            prob: 概率 (如 0.50)
            
        Returns:
            十进制赔率 (如 2.0)
        """
        if prob <= 0:
            return 0
        return 1 / prob
    
    def calculate_vig(self, home_odds: float, draw_odds: float, away_odds: float) -> float:
        """
        计算博彩公司抽水(vig/juice)
        
        正常范围: 2-5%
        超过5%说明赔率不利
        """
        implied_home = self.odds_to_probability(home_odds)
        implied_draw = self.odds_to_probability(draw_odds)
        implied_away = self.odds_to_probability(away_odds)
        
        total_implied = implied_home + implied_draw + implied_away
        vig = (total_implied - 1) * 100
        
        return vig
    
    def remove_vig(self, home_odds: float, draw_odds: float, away_odds: float) -> Tuple[float, float, float]:
        """
        移除博彩公司抽水，还原真实概率
        
        使用卸水算法还原公平赔率
        """
        implied_home = self.odds_to_probability(home_odds)
        implied_draw = self.odds_to_probability(draw_odds)
        implied_away = self.odds_to_probability(away_odds)
        
        total = implied_home + implied_draw + implied_away
        
        # 还原公平概率
        fair_home = implied_home / total
        fair_draw = implied_draw / total
        fair_away = implied_away / total
        
        return (
            self.probability_to_odds(fair_home),
            self.probability_to_odds(fair_draw),
            self.probability_to_odds(fair_away)
        )
    
    def get_weighted_odds(self, bookmakers: Dict) -> Optional[Dict]:
        """
        计算多博彩公司加权平均赔率
        
        Args:
            bookmakers: 博彩公司赔率字典
            
        Returns:
            加权平均后的赔率
        """
        total_weight = 0
        weighted_home = 0
        weighted_draw = 0
        weighted_away = 0
        
        for bookmaker, odds in bookmakers.items():
            if bookmaker not in self.BOOKMAKER_WEIGHTS:
                continue
                
            weight = self.BOOKMAKER_WEIGHTS[bookmaker]
            
            home_odds = odds.get("home_odds")
            draw_odds = odds.get("draw_odds")
            away_odds = odds.get("away_odds")
            
            if home_odds and draw_odds and away_odds:
                # 先移除vig
                fair_home, fair_draw, fair_away = self.remove_vig(
                    home_odds, draw_odds, away_odds
                )
                
                weighted_home += fair_home * weight
                weighted_draw += fair_draw * weight
                weighted_away += fair_away * weight
                total_weight += weight
        
        if total_weight == 0:
            return None
        
        return {
            "home_odds": weighted_home / total_weight * 3,  # 转回赔率
            "draw_odds": weighted_draw / total_weight * 3,
            "away_odds": weighted_away / total_weight * 3,
            "total_weight": total_weight,
            "timestamp": datetime.now().isoformat()
        }
    
    def odds_to_win_prob(self, home_odds: float, draw_odds: float, away_odds: float) -> Dict[str, float]:
        """
        从赔率计算胜率
        
        Returns:
            {home: 0.xx, draw: 0.xx, away: 0.xx}
        """
        # 移除vig
        fair_home, fair_draw, fair_away = self.remove_vig(
            home_odds, draw_odds, away_odds
        )
        
        # 转回概率
        prob_home = self.odds_to_probability(fair_home)
        prob_draw = self.odds_to_probability(fair_draw)
        prob_away = self.odds_to_probability(fair_away)
        
        return {
            "home": prob_home,
            "draw": prob_draw,
            "away": prob_away
        }
    
    def analyze_match(self, home_team: str, away_team: str) -> Optional[Dict]:
        """
        分析两队比赛的博彩赔率
        
        Args:
            home_team: 主队
            away_team: 客队
            
        Returns:
            赔率分析结果
        """
        # 在现有数据中查找
        for match in self.odds_data.get("matches", []):
            if (match.get("home_team") == home_team and 
                match.get("away_team") == away_team):
                
                bookmakers = match.get("bookmakers", {})
                weighted_odds = self.get_weighted_odds(bookmakers)
                
                if not weighted_odds:
                    return None
                
                # 计算胜率
                win_probs = self.odds_to_win_prob(
                    weighted_odds["home_odds"],
                    weighted_odds["draw_odds"],
                    weighted_odds["away_odds"]
                )
                
                # 检测异常
                anomalies = self.detect_anomalies(home_team, away_team, bookmakers)
                
                return {
                    "match": f"{home_team} vs {away_team}",
                    "weighted_odds": weighted_odds,
                    "win_probabilities": win_probs,
                    "anomalies": anomalies,
                    "bookmaker_count": len(bookmakers),
                    "best_odds": self.find_best_odds(bookmakers)
                }
        
        return None
    
    def detect_anomalies(self, home_team: str, away_team: str, bookmakers: Dict) -> List[Dict]:
        """
        检测赔率异常
        
        异常类型:
        - 某博彩公司赔率显著偏高
        - 赔率分歧过大
        - vig异常高
        """
        anomalies = []
        
        if not bookmakers:
            return anomalies
        
        # 收集各博彩公司的赔率
        home_odds_list = []
        away_odds_list = []
        
        for bookmaker, odds in bookmakers.items():
            if odds.get("home_odds") and odds.get("away_odds"):
                home_odds_list.append((bookmaker, odds["home_odds"]))
                away_odds_list.append((bookmaker, odds["away_odds"]))
        
        # 检测主队赔率异常
        if home_odds_list:
            avg_home = sum(o[1] for o in home_odds_list) / len(home_odds_list)
            for bookmaker, odds in home_odds_list:
                if odds > avg_home * 1.08:  # 超过平均值8%
                    anomalies.append({
                        "type": "overpriced",
                        "team": home_team,
                        "bookmaker": bookmaker,
                        "odds": odds,
                        "avg_odds": avg_home,
                        "suggestion": "可能存在价值"
                    })
        
        # 检测客队赔率异常
        if away_odds_list:
            avg_away = sum(o[1] for o in away_odds_list) / len(away_odds_list)
            for bookmaker, odds in away_odds_list:
                if odds > avg_away * 1.08:
                    anomalies.append({
                        "type": "overpriced",
                        "team": away_team,
                        "bookmaker": bookmaker,
                        "odds": odds,
                        "avg_odds": avg_away,
                        "suggestion": "可能存在价值"
                    })
        
        return anomalies
    
    def find_best_odds(self, bookmakers: Dict) -> Dict:
        """找出各选项最佳赔率"""
        best = {"home": None, "draw": None, "away": None}
        
        for bookmaker, odds in bookmakers.items():
            home_odds = odds.get("home_odds")
            draw_odds = odds.get("draw_odds")
            away_odds = odds.get("away_odds")
            
            if home_odds:
                if not best["home"] or home_odds > best["home"]["odds"]:
                    best["home"] = {"bookmaker": bookmaker, "odds": home_odds}
            
            if draw_odds:
                if not best["draw"] or draw_odds > best["draw"]["odds"]:
                    best["draw"] = {"bookmaker": bookmaker, "odds": draw_odds}
            
            if away_odds:
                if not best["away"] or away_odds > best["away"]["odds"]:
                    best["away"] = {"bookmaker": bookmaker, "odds": away_odds}
        
        return best
    
    def fuse_with_model(
        self, 
        model_probs: Dict[str, float],
        bookmaker_probs: Dict[str, float],
        model_weight: float = 0.40
    ) -> Dict[str, float]:
        """
        融合模型预测与博彩赔率
        
        Args:
            model_probs: 模型预测概率 {home, draw, away}
            bookmaker_probs: 博彩公司概率
            model_weight: 模型权重
            
        Returns:
            融合后的概率
        """
        bookmaker_weight = 1 - model_weight
        
        fused = {}
        for key in model_probs:
            fused[key] = (
                model_probs[key] * model_weight + 
                bookmaker_probs.get(key, 0) * bookmaker_weight
            )
        
        return fused
    
    def print_analysis(self, home_team: str, away_team: str):
        """打印分析结果"""
        analysis = self.analyze_match(home_team, away_team)
        
        if not analysis:
            print(f"⚠️ 未找到 {home_team} vs {away_team} 的赔率数据")
            return
        
        print(f"\n📊 博彩赔率分析: {analysis['match']}")
        print("=" * 60)
        
        # 最佳赔率
        best = analysis["best_odds"]
        print("\n🏆 最佳赔率:")
        if best["home"]:
            print(f"  主队(home): {best['home']['odds']:.2f} ({best['home']['bookmaker']})")
        if best["draw"]:
            print(f"  平局(draw): {best['draw']['odds']:.2f} ({best['draw']['bookmaker']})")
        if best["away"]:
            print(f"  客队(away): {best['away']['odds']:.2f} ({best['away']['bookmaker']})")
        
        # 胜率概率
        probs = analysis["win_probabilities"]
        print("\n📈 隐含概率:")
        print(f"  主队: {probs['home']*100:.1f}%")
        print(f"  平局: {probs['draw']*100:.1f}%")
        print(f"  客队: {probs['away']*100:.1f}%")
        
        # 异常检测
        anomalies = analysis.get("anomalies", [])
        if anomalies:
            print("\n⚠️ 赔率异常:")
            for a in anomalies:
                print(f"  [{a['type']}] {a['team']} @ {a['bookmaker']}: {a['odds']:.2f} (平均{a['avg_odds']:.2f})")
                print(f"    → {a['suggestion']}")
        
        print()


def main():
    parser = argparse.ArgumentParser(description="博彩赔率整合工具")
    parser.add_argument("--fetch", action="store_true", help="获取赔率数据")
    parser.add_argument("--analyze", nargs=2, metavar=("HOME", "AWAY"), help="分析比赛")
    parser.add_argument("--list", action="store_true", help="列出所有比赛")
    
    args = parser.parse_args()
    
    integrator = BookmakerOddsIntegrator()
    
    if args.analyze:
        home, away = args.analyze
        integrator.print_analysis(home, away)
        return
    
    if args.list:
        matches = integrator.odds_data.get("matches", [])
        print(f"\n📋 共 {len(matches)} 场比赛的赔率数据:")
        for m in matches[:20]:
            print(f"  {m.get('home_team')} vs {m.get('away_team')}")
        if len(matches) > 20:
            print(f"  ... 还有 {len(matches)-20} 场")
        return
    
    if args.fetch:
        print("📡 赔率获取功能需要接入API...")
        print("建议使用 Polymarket 或 OddsJam API")
        return
    
    # 默认显示帮助
    parser.print_help()


if __name__ == "__main__":
    main()
