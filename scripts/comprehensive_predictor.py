#!/usr/bin/env python3
"""
综合预测输出脚本
包含：三个比分、大小球、上半场大小球

使用方法:
    python3 comprehensive_predictor.py --match "Arsenal" "Liverpool"
"""

import argparse
import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Tuple

# 路径配置
BASE_DIR = os.path.expanduser("~/hermes-world-cup/")
sys.path.insert(0, os.path.join(BASE_DIR, "scripts"))

from core.unified_predictor import UnifiedPredictor
from core.team_stats import EloSystem
from core.xg_model import DynamicxGModel

# 中文队名映射
TEAM_NAMES_CN = {
    # EPL
    "Manchester City": "曼城",
    "Arsenal": "阿森纳",
    "Liverpool": "利物浦",
    "Chelsea": "切尔西",
    "Manchester United": "曼联",
    "Tottenham": "热刺",
    "Newcastle": "纽卡斯尔",
    "Brighton": "布莱顿",
    "Aston Villa": "维拉",
    "West Ham": "西汉姆",
    "Brentford": "布伦特福德",
    "Crystal Palace": "水晶宫",
    "Wolves": "狼队",
    "Wolverhampton": "狼队",
    "Fulham": "富勒姆",
    "Leicester": "莱斯特城",
    "Leeds": "利兹联",
    "Southampton": "南安普顿",
    "Everton": "埃弗顿",
    "Bournemouth": "伯恩茅斯",
    "Nottingham Forest": "诺丁汉森林",
    "Ipswich": "伊普斯维奇",
    "Luton": "卢顿",
    "Burnley": "伯恩利",
    "Sheffield United": "谢菲联",
    # 世界杯
    "Brazil": "巴西",
    "Spain": "西班牙",
    "France": "法国",
    "Argentina": "阿根廷",
    "England": "英格兰",
    "Germany": "德国",
    "Portugal": "葡萄牙",
    "Netherlands": "荷兰",
    "Italy": "意大利",
    "Belgium": "比利时",
    "Croatia": "克罗地亚",
    "Uruguay": "乌拉圭",
    "Morocco": "摩洛哥",
    "USA": "美国",
    "Mexico": "墨西哥",
    "Colombia": "哥伦比亚",
    "Japan": "日本",
    "Senegal": "塞内加尔",
    "Poland": "波兰",
    "Denmark": "丹麦",
    "Switzerland": "瑞士",
    "Ukraine": "乌克兰",
    "Australia": "澳大利亚",
    "Serbia": "塞尔维亚",
    "Egypt": "埃及",
    "South Korea": "韩国",
    "Iran": "伊朗",
    "Canada": "加拿大",
    "Turkey": "土耳其",
    "Wales": "威尔士",
    "Chile": "智利",
    # 西甲
    "Real Madrid": "皇家马德里",
    "Barcelona": "巴塞罗那",
    "Atletico Madrid": "马德里竞技",
    "Sevilla": "塞维利亚",
    "Real Sociedad": "皇家社会",
    "Villarreal": "比利亚雷亚尔",
    "Athletic Bilbao": "毕尔巴鄂",
    "Real Betis": "贝蒂斯",
    # 意甲
    "Inter Milan": "国际米兰",
    "AC Milan": "AC米兰",
    "Juventus": "尤文图斯",
    "Napoli": "那不勒斯",
    "AS Roma": "罗马",
    "Lazio": "拉齐奥",
    # 德甲
    "Bayern Munich": "拜仁慕尼黑",
    "Borussia Dortmund": "多特蒙德",
    "RB Leipzig": "莱比锡",
    "Bayer Leverkusen": "勒沃库森",
    "Eintracht Frankfurt": "法兰克福",
    # 法甲
    "Paris Saint-Germain": "巴黎圣日耳曼",
    "Monaco": "摩纳哥",
    "Marseille": "马赛",
    "Lyon": "里昂",
    "Lille": "里尔",
}


def get_cn_name(en_name: str) -> str:
    """获取中文名"""
    return TEAM_NAMES_CN.get(en_name, en_name)


class ComprehensivePredictor:
    """
    综合预测器
    
    输出内容:
    1. 三个比分推荐
    2. 胜平负预测
    3. 全场大球/小球
    4. 上半场大球/小球
    """
    
    def __init__(self):
        self.predictor = UnifiedPredictor()
        self.elo_system = EloSystem()
        self.xg_model = DynamicxGModel()
    
    def calculate_over_under(
        self, 
        total_xg: float, 
        threshold: float = 2.5
    ) -> Tuple[float, str]:
        """
        计算大球/小球
        
        Args:
            total_xg: 总xG
            threshold: 临界值 (默认2.5)
            
        Returns:
            (概率, 推荐)
        """
        # xG高于阈值=大球概率高
        over_prob = min(total_xg / (threshold + 1) * 100, 95)
        over_prob = max(over_prob, 30)  # 最低30%
        
        if over_prob > 50:
            return over_prob, "大球 🟢"
        else:
            return 100 - over_prob, "小球 🔴"
    
    def calculate_half_over_under(
        self, 
        total_xg: float
    ) -> Tuple[float, str]:
        """
        计算上半场大球/小球
        
        上半场xG通常约为全场的40-50%
        """
        half_xg = total_xg * 0.45  # 上半场占总xG约45%
        threshold = 1.0  # 上半场临界值1.0
        
        if half_xg > threshold:
            prob = min(half_xg / 1.5 * 100, 90)
            return prob, "上半场大球 🟢"
        else:
            prob = min((1.5 - half_xg) / 1.5 * 100, 85)
            return 100 - prob, "上半场小球 🔴"
    
    def generate_score_predictions(
        self, 
        home_xg: float, 
        away_xg: float
    ) -> List[Tuple[str, float]]:
        """
        生成三个比分预测
        
        Returns:
            [(比分, 概率), ...]
        """
        import math
        
        scores = []
        
        # 泊松分布模拟
        for _ in range(1000):
            home_goals = max(0, int(home_xg + (hash(_) % 3 - 1)))
            away_goals = max(0, int(away_xg + (hash(_+1) % 3 - 1)))
            scores.append((home_goals, away_goals))
        
        # 统计最常见的比分
        from collections import Counter
        counter = Counter(scores)
        
        # 转换为概率
        total = len(scores)
        top_scores = []
        
        for (h, a), count in counter.most_common(10):
            prob = count / total * 100
            score_str = f"{h}-{a}"
            
            # 过滤掉概率太低的
            if prob > 3:
                top_scores.append((score_str, prob))
        
        # 返回前3个
        return top_scores[:3]
    
    def predict(self, home_team: str, away_team: str) -> Dict:
        """
        综合预测
        
        Returns:
            完整预测结果
        """
        home_cn = get_cn_name(home_team)
        away_cn = get_cn_name(away_team)
        
        result = {
            "match": f"{home_cn} vs {away_cn}",
            "home_team_en": home_team,
            "away_team_en": away_team,
            "home_team_cn": home_cn,
            "away_team_cn": away_cn,
        }
        
        # 1. 获取基础预测
        base_pred = self.predictor.predict(home_team, away_team)
        
        # 2. 获取xG
        xg_data = self.xg_model.calculate_match_xg(home_team, away_team)
        home_xg = xg_data[0]
        away_xg = xg_data[1]
        total_xg = home_xg + away_xg
        
        result["xg"] = {
            "home": home_xg,
            "away": away_xg,
            "total": total_xg
        }
        
        # 3. 生成三个比分
        score_predictions = self.generate_score_predictions(home_xg, away_xg)
        result["score_predictions"] = score_predictions
        
        # 4. 计算大小球
        full_over_prob, full_recommendation = self.calculate_over_under(total_xg, 2.5)
        half_over_prob, half_recommendation = self.calculate_half_over_under(total_xg)
        
        result["full_match"] = {
            "total_xg": total_xg,
            "over_prob": full_over_prob,
            "recommendation": full_recommendation,
            "threshold": 2.5
        }
        
        result["first_half"] = {
            "estimated_xg": total_xg * 0.45,
            "over_prob": half_over_prob,
            "recommendation": half_recommendation,
            "threshold": 1.0
        }
        
        # 5. 胜平负预测
        pred = base_pred["prediction"]
        home_prob = pred["home_win"] * 100
        draw_prob = pred["draw"] * 100
        away_prob = pred["away_win"] * 100
        
        # 推荐
        if home_prob > away_prob and home_prob > draw_prob:
            win_recommendation = home_cn
        elif away_prob > home_prob and away_prob > draw_prob:
            win_recommendation = away_cn
        else:
            win_recommendation = "平局"
        
        result["win_prediction"] = {
            "home_prob": home_prob,
            "draw_prob": draw_prob,
            "away_prob": away_prob,
            "recommendation": win_recommendation
        }
        
        return result
    
    def print_prediction(self, home_team: str, away_team: str):
        """打印完整预测"""
        pred = self.predict(home_team, away_team)
        
        home_cn = pred["home_team_cn"]
        away_cn = pred["away_team_cn"]
        total_xg = pred["xg"]["total"]
        home_xg = pred["xg"]["home"]
        away_xg = pred["xg"]["away"]
        
        print(f"\n{'='*60}")
        print(f"⚽ {home_cn} vs {away_cn}")
        print(f"{'='*60}")
        
        # xG
        print(f"\n📊 xG预期:")
        print(f"   {home_cn}: {home_xg:.1f}")
        print(f"   {away_cn}: {away_xg:.1f}")
        print(f"   总额: {total_xg:.1f}")
        
        # 三个比分
        scores = pred["score_predictions"]
        print(f"\n⚽ 比分推荐:")
        for i, (score, prob) in enumerate(scores):
            emoji = "⭐" if i == 0 else "🔶" if i == 1 else "#3"
            print(f"   {emoji} 首选: {score} ({prob:.1f}%)" if i == 0 else f"   {emoji} 次选: {score} ({prob:.1f}%)" if i == 1 else f"   {emoji} {i+1}: {score} ({prob:.1f}%)")
        
        # 胜平负
        win_pred = pred["win_prediction"]
        print(f"\n🏆 胜平负预测:")
        print(f"   {home_cn}: {win_pred['home_prob']:.0f}%")
        print(f"   平局: {win_pred['draw_prob']:.0f}%")
        print(f"   {away_cn}: {win_pred['away_prob']:.0f}%")
        print(f"   推荐: {win_pred['recommendation']}")
        
        # 全场大小球
        full = pred["full_match"]
        print(f"\n🥅 全场大小球 (临界{full['threshold']}):")
        print(f"   预期总进球: {full['total_xg']:.1f}")
        print(f"   大球概率: {full['over_prob']:.0f}%")
        print(f"   推荐: {full['recommendation']}")
        
        # 上半场大小球
        half = pred["first_half"]
        print(f"\n⏱️ 上半场大小球 (临界{half['threshold']}):")
        print(f"   预期上半场进球: {half['estimated_xg']:.1f}")
        print(f"   大球概率: {half['over_prob']:.0f}%")
        print(f"   推荐: {half['recommendation']}")
        
        print(f"\n{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(description="综合预测工具")
    parser.add_argument("--match", nargs=2, metavar=("HOME", "AWAY"), help="比赛")
    
    args = parser.parse_args()
    
    predictor = ComprehensivePredictor()
    
    if args.match:
        home, away = args.match
        predictor.print_prediction(home, away)
        return
    
    # 默认测试
    print("⚽ 综合预测测试")
    
    test_matches = [
        ("Brentford", "Fulham"),
        ("Leeds", "Wolves"),
        ("Newcastle", "Bournemouth"),
    ]
    
    for home, away in test_matches:
        predictor.print_prediction(home, away)


if __name__ == "__main__":
    main()
