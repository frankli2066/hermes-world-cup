#!/usr/bin/env python3
"""
UnifiedPredictor 完整回测 v1.0
测试UnifiedPredictor在247场比赛上的表现

使用方法：
    python3 backtest_unified.py
"""

import sys
import os
from typing import Dict, List, Tuple, Any
from collections import defaultdict
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "core"))

from core.unified_predictor import UnifiedPredictor

# 历史比赛数据（2010-2022世界杯 + 其他赛事）
HISTORICAL_MATCHES = {
    "2010": [
        # 小组赛
        {"home": "South Africa", "away": "Mexico", "score": "1-1", "stage": "group"},
        {"home": "Uruguay", "away": "France", "score": "0-0", "stage": "group"},
        {"home": "Mexico", "away": "France", "score": "0-2", "stage": "group"},
        {"home": "South Africa", "away": "Uruguay", "score": "0-3", "stage": "group"},
        {"home": "Mexico", "away": "Uruguay", "score": "0-0", "stage": "group"},
        {"home": "South Africa", "away": "France", "score": "2-1", "stage": "group"},
        {"home": "Argentina", "away": "Nigeria", "score": "1-0", "stage": "group"},
        {"home": "South Korea", "away": "Greece", "score": "2-0", "stage": "group"},
        {"home": "Greece", "away": "Nigeria", "score": "2-1", "stage": "group"},
        {"home": "Argentina", "away": "South Korea", "score": "4-1", "stage": "group"},
        {"home": "Greece", "away": "Argentina", "score": "0-2", "stage": "group"},
        {"home": "Nigeria", "away": "South Korea", "score": "2-2", "stage": "group"},
        {"home": "England", "away": "USA", "score": "1-1", "stage": "group"},
        {"home": "Germany", "away": "Australia", "score": "4-0", "stage": "group"},
        {"home": "Germany", "away": "Ghana", "score": "0-1", "stage": "group"},
        {"home": "Australia", "away": "Ghana", "score": "1-1", "stage": "group"},
        {"home": "Germany", "away": "England", "score": "4-1", "stage": "group"},
        {"home": "Australia", "away": "Germany", "score": "0-0", "stage": "group"},
        {"home": "Ghana", "away": "USA", "score": "1-0", "stage": "group"},
        {"home": "Netherlands", "away": "Denmark", "score": "2-0", "stage": "group"},
        {"home": "Japan", "away": "Cameroon", "score": "1-0", "stage": "group"},
        {"home": "Netherlands", "away": "Japan", "score": "0-0", "stage": "group"},
        {"home": "Denmark", "away": "Cameroon", "score": "1-2", "stage": "group"},
        {"home": "Netherlands", "away": "Cameroon", "score": "2-1", "stage": "group"},
        {"home": "Denmark", "away": "Japan", "score": "2-3", "stage": "group"},
        {"home": "Italy", "away": "Paraguay", "score": "1-1", "stage": "group"},
        {"home": "Slovakia", "away": "New Zealand", "score": "1-1", "stage": "group"},
        {"home": "Italy", "away": "New Zealand", "score": "1-1", "stage": "group"},
        {"home": "Paraguay", "away": "Slovakia", "score": "2-0", "stage": "group"},
        {"home": "Italy", "away": "Slovakia", "score": "3-2", "stage": "group"},
        {"home": "Paraguay", "away": "New Zealand", "score": "0-0", "stage": "group"},
        {"home": "Brazil", "away": "North Korea", "score": "2-1", "stage": "group"},
        {"home": "Portugal", "away": "Ivory Coast", "score": "0-0", "stage": "group"},
        {"home": "Brazil", "away": "Ivory Coast", "score": "3-1", "stage": "group"},
        {"home": "Portugal", "away": "North Korea", "score": "7-0", "stage": "group"},
        {"home": "Brazil", "away": "Portugal", "score": "0-0", "stage": "group"},
        {"home": "Ivory Coast", "away": "North Korea", "score": "1-0", "stage": "group"},
        {"home": "Spain", "away": "Switzerland", "score": "0-1", "stage": "group"},
        {"home": "Honduras", "away": "Chile", "score": "0-1", "stage": "group"},
        {"home": "Spain", "away": "Honduras", "score": "6-0", "stage": "group"},
        {"home": "Chile", "away": "Switzerland", "score": "1-0", "stage": "group"},
        {"home": "Spain", "away": "Chile", "score": "1-2", "stage": "group"},
        {"home": "Switzerland", "away": "Honduras", "score": "0-0", "stage": "group"},
        # 淘汰赛
        {"home": "Uruguay", "away": "South Korea", "score": "2-1", "stage": "round_of_16"},
        {"home": "USA", "away": "Ghana", "score": "1-2", "stage": "round_of_16"},
        {"home": "Germany", "away": "England", "score": "4-1", "stage": "round_of_16"},
        {"home": "Argentina", "away": "Mexico", "score": "3-1", "stage": "round_of_16"},
        {"home": "Netherlands", "away": "Slovakia", "score": "2-1", "stage": "round_of_16"},
        {"home": "Brazil", "away": "Chile", "score": "3-0", "stage": "round_of_16"},
        {"home": "Paraguay", "away": "Spain", "score": "0-1", "stage": "round_of_16"},
        {"home": "Portugal", "away": "Spain", "score": "0-1", "stage": "round_of_16"},
        {"home": "Netherlands", "away": "Brazil", "score": "2-1", "stage": "quarter"},
        {"home": "Uruguay", "away": "Ghana", "score": "0-0", "stage": "quarter"},
        {"home": "Germany", "away": "Argentina", "score": "4-0", "stage": "quarter"},
        {"home": "Spain", "away": "Paraguay", "score": "1-0", "stage": "quarter"},
        {"home": "Uruguay", "away": "Netherlands", "score": "2-3", "stage": "semi"},
        {"home": "Germany", "away": "Spain", "score": "0-1", "stage": "semi"},
        {"home": "Netherlands", "away": "Spain", "score": "0-1", "stage": "final"},
    ],
    "2014": [
        # 小组赛
        {"home": "Brazil", "away": "Croatia", "score": "3-1", "stage": "group"},
        {"home": "Mexico", "away": "Cameroon", "score": "1-4", "stage": "group"},
        {"home": "Brazil", "away": "Mexico", "score": "0-0", "stage": "group"},
        {"home": "Cameroon", "away": "Croatia", "score": "0-4", "stage": "group"},
        {"home": "Brazil", "away": "Cameroon", "score": "4-1", "stage": "group"},
        {"home": "Croatia", "away": "Mexico", "score": "1-3", "stage": "group"},
        {"home": "Spain", "away": "Netherlands", "score": "1-5", "stage": "group"},
        {"home": "Chile", "away": "Australia", "score": "3-1", "stage": "group"},
        {"home": "Spain", "away": "Chile", "score": "0-2", "stage": "group"},
        {"home": "Australia", "away": "Netherlands", "score": "2-3", "stage": "group"},
        {"home": "Spain", "away": "Australia", "score": "3-0", "stage": "group"},
        {"home": "Netherlands", "away": "Chile", "score": "2-0", "stage": "group"},
        {"home": "Colombia", "away": "Greece", "score": "3-0", "stage": "group"},
        {"home": "Ivory Coast", "away": "Japan", "score": "2-1", "stage": "group"},
        {"home": "Colombia", "away": "Ivory Coast", "score": "2-1", "stage": "group"},
        {"home": "Japan", "away": "Greece", "score": "0-0", "stage": "group"},
        {"home": "Colombia", "away": "Japan", "score": "4-1", "stage": "group"},
        {"home": "Greece", "away": "Ivory Coast", "score": "2-1", "stage": "group"},
        {"home": "Uruguay", "away": "Costa Rica", "score": "1-3", "stage": "group"},
        {"home": "England", "away": "Italy", "score": "1-2", "stage": "group"},
        {"home": "Uruguay", "away": "England", "score": "2-1", "stage": "group"},
        {"home": "Italy", "away": "Costa Rica", "score": "0-1", "stage": "group"},
        {"home": "Italy", "away": "Uruguay", "score": "0-1", "stage": "group"},
        {"home": "Costa Rica", "away": "England", "score": "0-0", "stage": "group"},
        {"home": "France", "away": "Honduras", "score": "3-0", "stage": "group"},
        {"home": "Switzerland", "away": "Ecuador", "score": "2-1", "stage": "group"},
        {"home": "France", "away": "Switzerland", "score": "5-2", "stage": "group"},
        {"home": "Ecuador", "away": "Honduras", "score": "1-2", "stage": "group"},
        {"home": "France", "away": "Ecuador", "score": "0-0", "stage": "group"},
        {"home": "Honduras", "away": "Switzerland", "score": "0-3", "stage": "group"},
        {"home": "Argentina", "away": "Bosnia", "score": "2-1", "stage": "group"},
        {"home": "Iran", "away": "Nigeria", "score": "0-0", "stage": "group"},
        {"home": "Argentina", "away": "Iran", "score": "1-0", "stage": "group"},
        {"home": "Nigeria", "away": "Bosnia", "score": "1-0", "stage": "group"},
        {"home": "Nigeria", "away": "Argentina", "score": "2-3", "stage": "group"},
        {"home": "Bosnia", "away": "Iran", "score": "3-1", "stage": "group"},
        {"home": "Germany", "away": "Portugal", "score": "4-0", "stage": "group"},
        {"home": "Ghana", "away": "USA", "score": "1-2", "stage": "group"},
        {"home": "Germany", "away": "Ghana", "score": "2-2", "stage": "group"},
        {"home": "USA", "away": "Portugal", "score": "2-2", "stage": "group"},
        {"home": "Germany", "away": "USA", "score": "1-0", "stage": "group"},
        {"home": "Portugal", "away": "Ghana", "score": "1-0", "stage": "group"},
        {"home": "Belgium", "away": "Algeria", "score": "2-1", "stage": "group"},
        {"home": "Russia", "away": "South Korea", "score": "1-1", "stage": "group"},
        {"home": "Belgium", "away": "Russia", "score": "1-0", "stage": "group"},
        {"home": "South Korea", "away": "Algeria", "score": "2-4", "stage": "group"},
        {"home": "Belgium", "away": "South Korea", "score": "1-0", "stage": "group"},
        {"home": "Algeria", "away": "Russia", "score": "1-1", "stage": "group"},
        # 淘汰赛
        {"home": "Brazil", "away": "Chile", "score": "1-1", "stage": "round_of_16"},
        {"home": "Colombia", "away": "Uruguay", "score": "2-0", "stage": "round_of_16"},
        {"home": "France", "away": "Nigeria", "score": "2-0", "stage": "round_of_16"},
        {"home": "Germany", "away": "Algeria", "score": "2-1", "stage": "round_of_16"},
        {"home": "Belgium", "away": "USA", "score": "2-1", "stage": "round_of_16"},
        {"home": "Argentina", "away": "Switzerland", "score": "1-0", "stage": "round_of_16"},
        {"home": "Netherlands", "away": "Mexico", "score": "2-1", "stage": "round_of_16"},
        {"home": "Costa Rica", "away": "Greece", "score": "1-1", "stage": "round_of_16"},
        {"home": "Brazil", "away": "Colombia", "score": "2-1", "stage": "quarter"},
        {"home": "France", "away": "Germany", "score": "0-1", "stage": "quarter"},
        {"home": "Belgium", "away": "Argentina", "score": "0-1", "stage": "quarter"},
        {"home": "Netherlands", "away": "Costa Rica", "score": "0-0", "stage": "quarter"},
        {"home": "Brazil", "away": "Germany", "score": "1-7", "stage": "semi"},
        {"home": "Netherlands", "away": "Argentina", "score": "0-0", "stage": "semi"},
        {"home": "Germany", "away": "Argentina", "score": "1-0", "stage": "final"},
    ],
    "2018": [
        # 小组赛
        {"home": "Russia", "away": "Saudi Arabia", "score": "5-0", "stage": "group"},
        {"home": "Egypt", "away": "Uruguay", "score": "0-1", "stage": "group"},
        {"home": "Russia", "away": "Egypt", "score": "3-1", "stage": "group"},
        {"home": "Uruguay", "away": "Saudi Arabia", "score": "1-0", "stage": "group"},
        {"home": "Uruguay", "away": "Russia", "score": "3-0", "stage": "group"},
        {"home": "Saudi Arabia", "away": "Egypt", "score": "2-1", "stage": "group"},
        {"home": "Portugal", "away": "Spain", "score": "3-3", "stage": "group"},
        {"home": "Iran", "away": "Morocco", "score": "1-0", "stage": "group"},
        {"home": "Portugal", "away": "Morocco", "score": "1-0", "stage": "group"},
        {"home": "Iran", "away": "Spain", "score": "1-1", "stage": "group"},
        {"home": "Portugal", "away": "Iran", "score": "1-1", "stage": "group"},
        {"home": "Spain", "away": "Morocco", "score": "2-2", "stage": "group"},
        {"home": "France", "away": "Australia", "score": "2-1", "stage": "group"},
        {"home": "Peru", "away": "Denmark", "score": "2-0", "stage": "group"},
        {"home": "France", "away": "Peru", "score": "1-0", "stage": "group"},
        {"home": "Denmark", "away": "Australia", "score": "1-1", "stage": "group"},
        {"home": "Denmark", "away": "France", "score": "0-0", "stage": "group"},
        {"home": "Australia", "away": "Peru", "score": "0-2", "stage": "group"},
        {"home": "Argentina", "away": "Iceland", "score": "1-1", "stage": "group"},
        {"home": "Croatia", "away": "Nigeria", "score": "2-0", "stage": "group"},
        {"home": "Argentina", "away": "Croatia", "score": "0-3", "stage": "group"},
        {"home": "Nigeria", "away": "Iceland", "score": "2-0", "stage": "group"},
        {"home": "Nigeria", "away": "Argentina", "score": "1-2", "stage": "group"},
        {"home": "Iceland", "away": "Croatia", "score": "1-2", "stage": "group"},
        {"home": "Brazil", "away": "Switzerland", "score": "1-1", "stage": "group"},
        {"home": "Costa Rica", "away": "Serbia", "score": "0-1", "stage": "group"},
        {"home": "Brazil", "away": "Costa Rica", "score": "2-0", "stage": "group"},
        {"home": "Serbia", "away": "Switzerland", "score": "2-1", "stage": "group"},
        {"home": "Serbia", "away": "Brazil", "score": "0-2", "stage": "group"},
        {"home": "Switzerland", "away": "Costa Rica", "score": "2-2", "stage": "group"},
        {"home": "Germany", "away": "Mexico", "score": "0-1", "stage": "group"},
        {"home": "Sweden", "away": "South Korea", "score": "1-0", "stage": "group"},
        {"home": "Germany", "away": "Sweden", "score": "2-1", "stage": "group"},
        {"home": "South Korea", "away": "Mexico", "score": "2-1", "stage": "group"},
        {"home": "Mexico", "away": "Sweden", "score": "0-3", "stage": "group"},
        {"home": "South Korea", "away": "Germany", "score": "2-0", "stage": "group"},
        {"home": "Belgium", "away": "Panama", "score": "3-0", "stage": "group"},
        {"home": "Tunisia", "away": "England", "score": "1-2", "stage": "group"},
        {"home": "Belgium", "away": "Tunisia", "score": "5-2", "stage": "group"},
        {"home": "England", "away": "Panama", "score": "6-1", "stage": "group"},
        {"home": "England", "away": "Belgium", "score": "0-1", "stage": "group"},
        {"home": "Panama", "away": "Tunisia", "score": "1-1", "stage": "group"},
        {"home": "Poland", "away": "Senegal", "score": "0-3", "stage": "group"},
        {"home": "Colombia", "away": "Japan", "score": "1-2", "stage": "group"},
        {"home": "Poland", "away": "Colombia", "score": "0-3", "stage": "group"},
        {"home": "Japan", "away": "Senegal", "score": "2-2", "stage": "group"},
        {"home": "Japan", "away": "Poland", "score": "0-1", "stage": "group"},
        {"home": "Senegal", "away": "Colombia", "score": "0-1", "stage": "group"},
        # 淘汰赛
        {"home": "France", "away": "Argentina", "score": "4-3", "stage": "round_of_16"},
        {"home": "Uruguay", "away": "Portugal", "score": "2-1", "stage": "round_of_16"},
        {"home": "Spain", "away": "Russia", "score": "1-1", "stage": "round_of_16"},
        {"home": "Croatia", "away": "Denmark", "score": "1-1", "stage": "round_of_16"},
        {"home": "Brazil", "away": "Mexico", "score": "2-0", "stage": "round_of_16"},
        {"home": "Belgium", "away": "Japan", "score": "3-2", "stage": "round_of_16"},
        {"home": "Sweden", "away": "Switzerland", "score": "1-0", "stage": "round_of_16"},
        {"home": "Colombia", "away": "England", "score": "1-1", "stage": "round_of_16"},
        {"home": "Uruguay", "away": "France", "score": "0-2", "stage": "quarter"},
        {"home": "Brazil", "away": "Belgium", "score": "2-1", "stage": "quarter"},
        {"home": "Sweden", "away": "England", "score": "0-2", "stage": "quarter"},
        {"home": "Russia", "away": "Croatia", "score": "2-2", "stage": "quarter"},
        {"home": "France", "away": "Belgium", "score": "1-0", "stage": "semi"},
        {"home": "Croatia", "away": "England", "score": "2-1", "stage": "semi"},
        {"home": "France", "away": "Croatia", "score": "4-2", "stage": "final"},
    ],
    "2022": [
        # 小组赛
        {"home": "Qatar", "away": "Ecuador", "score": "0-2", "stage": "group"},
        {"home": "England", "away": "Iran", "score": "6-2", "stage": "group"},
        {"home": "Senegal", "away": "Netherlands", "score": "0-2", "stage": "group"},
        {"home": "Netherlands", "away": "Ecuador", "score": "1-1", "stage": "group"},
        {"home": "Qatar", "away": "Senegal", "score": "1-3", "stage": "group"},
        {"home": "Netherlands", "away": "Qatar", "score": "2-0", "stage": "group"},
        {"home": "England", "away": "USA", "score": "0-0", "stage": "group"},
        {"home": "Iran", "away": "USA", "score": "0-1", "stage": "group"},
        {"home": "Wales", "away": "Iran", "score": "0-2", "stage": "group"},
        {"home": "England", "away": "Wales", "score": "3-0", "stage": "group"},
        {"home": "Iran", "away": "Wales", "score": "0-1", "stage": "group"},
        {"home": "USA", "away": "Wales", "score": "0-1", "stage": "group"},
        {"home": "Argentina", "away": "Saudi Arabia", "score": "1-2", "stage": "group"},
        {"home": "Mexico", "away": "Poland", "score": "0-0", "stage": "group"},
        {"home": "Poland", "away": "Saudi Arabia", "score": "2-0", "stage": "group"},
        {"home": "Argentina", "away": "Mexico", "score": "2-0", "stage": "group"},
        {"home": "Poland", "away": "Argentina", "score": "0-2", "stage": "group"},
        {"home": "Saudi Arabia", "away": "Mexico", "score": "1-2", "stage": "group"},
        {"home": "Denmark", "away": "Tunisia", "score": "0-0", "stage": "group"},
        {"home": "France", "away": "Australia", "score": "4-1", "stage": "group"},
        {"home": "Tunisia", "away": "Australia", "score": "1-0", "stage": "group"},
        {"home": "France", "away": "Denmark", "score": "2-1", "stage": "group"},
        {"home": "Australia", "away": "Denmark", "score": "1-0", "stage": "group"},
        {"home": "Tunisia", "away": "France", "score": "1-0", "stage": "group"},
        {"home": "Germany", "away": "Japan", "score": "1-2", "stage": "group"},
        {"home": "Spain", "away": "Costa Rica", "score": "7-0", "stage": "group"},
        {"home": "Japan", "away": "Costa Rica", "score": "0-1", "stage": "group"},
        {"home": "Spain", "away": "Germany", "score": "1-2", "stage": "group"},
        {"home": "Japan", "away": "Spain", "score": "2-1", "stage": "group"},
        {"home": "Costa Rica", "away": "Germany", "score": "2-4", "stage": "group"},
        {"home": "Morocco", "away": "Croatia", "score": "0-0", "stage": "group"},
        {"home": "Belgium", "away": "Canada", "score": "1-2", "stage": "group"},
        {"home": "Croatia", "away": "Canada", "score": "4-1", "stage": "group"},
        {"home": "Morocco", "away": "Belgium", "score": "2-0", "stage": "group"},
        {"home": "Croatia", "away": "Belgium", "score": "0-0", "stage": "group"},
        {"home": "Canada", "away": "Morocco", "score": "1-2", "stage": "group"},
        {"home": "Brazil", "away": "Serbia", "score": "2-0", "stage": "group"},
        {"home": "Switzerland", "away": "Cameroon", "score": "1-0", "stage": "group"},
        {"home": "Cameroon", "away": "Serbia", "score": "3-3", "stage": "group"},
        {"home": "Brazil", "away": "Switzerland", "score": "1-0", "stage": "group"},
        {"home": "Serbia", "away": "Switzerland", "score": "2-3", "stage": "group"},
        {"home": "Cameroon", "away": "Brazil", "score": "1-0", "stage": "group"},
        {"home": "Portugal", "away": "Ghana", "score": "3-2", "stage": "group"},
        {"home": "South Korea", "away": "Uruguay", "score": "0-0", "stage": "group"},
        {"home": "South Korea", "away": "Ghana", "score": "3-2", "stage": "group"},
        {"home": "Uruguay", "away": "Ghana", "score": "0-0", "stage": "group"},
        {"home": "Portugal", "away": "Uruguay", "score": "2-0", "stage": "group"},
        {"home": "Ghana", "away": "Uruguay", "score": "0-0", "stage": "group"},
        {"home": "South Korea", "away": "Portugal", "score": "1-1", "stage": "group"},
        # 淘汰赛
        {"home": "Netherlands", "away": "USA", "score": "3-1", "stage": "round_of_16"},
        {"home": "Argentina", "away": "Australia", "score": "2-1", "stage": "round_of_16"},
        {"home": "France", "away": "Poland", "score": "3-1", "stage": "round_of_16"},
        {"home": "England", "away": "Senegal", "score": "3-0", "stage": "round_of_16"},
        {"home": "Croatia", "away": "Japan", "score": "1-1", "stage": "round_of_16"},
        {"home": "Brazil", "away": "South Korea", "score": "4-1", "stage": "round_of_16"},
        {"home": "Morocco", "away": "Spain", "score": "0-0", "stage": "round_of_16"},
        {"home": "Portugal", "away": "Switzerland", "score": "6-1", "stage": "round_of_16"},
        {"home": "Netherlands", "away": "Argentina", "score": "2-2", "stage": "quarter"},
        {"home": "Croatia", "away": "Brazil", "score": "1-1", "stage": "quarter"},
        {"home": "Morocco", "away": "Portugal", "score": "1-0", "stage": "quarter"},
        {"home": "England", "away": "France", "score": "1-2", "stage": "quarter"},
        {"home": "Argentina", "away": "Croatia", "score": "3-0", "stage": "semi"},
        {"home": "France", "away": "Morocco", "score": "2-0", "stage": "semi"},
        {"home": "Argentina", "away": "France", "score": "3-3", "stage": "final"},
    ],
}

def get_actual_result(score: str) -> str:
    """从比分判断实际结果"""
    home_goals, away_goals = map(int, score.split("-"))
    if home_goals > away_goals:
        return "home"
    elif home_goals < away_goals:
        return "away"
    else:
        return "draw"

def get_score_prediction(prediction: Dict, home_team: str, away_team: str) -> str:
    """从预测结果中提取比分预测"""
    scores = prediction.get("scores", [])
    if scores:
        return scores[0].get("score", "N/A")
    return "N/A"

def main():
    print("=" * 60)
    print("🏆 UnifiedPredictor 完整回测 v1.0")
    print("=" * 60)
    
    # 初始化预测器
    predictor = UnifiedPredictor()
    
    # 收集所有比赛
    all_matches = []
    for year, matches in HISTORICAL_MATCHES.items():
        for match in matches:
            match["year"] = year
            all_matches.append(match)
    
    print(f"\n📊 数据集概览:")
    for year in HISTORICAL_MATCHES.keys():
        count = len(HISTORICAL_MATCHES[year])
        print(f"  {year}年世界杯: {count}场")
    print(f"\n总计: {len(all_matches)}场比赛\n")
    
    # 回测统计
    stats = {
        "total": 0,
        "correct_result": 0,
        "correct_score": 0,
        "by_stage": defaultdict(lambda: {"total": 0, "correct": 0}),
        "by_year": defaultdict(lambda: {"total": 0, "correct": 0}),
        "upsets": [],  # 冷门比赛
        "correct_upsets": 0,
    }
    
    # 运行回测
    print("🔄 开始回测...")
    for match in all_matches:
        home = match["home"]
        away = match["away"]
        actual_score = match["score"]
        actual_result = get_actual_result(actual_score)
        stage = match["stage"]
        year = match["year"]
        
        try:
            # 使用UnifiedPredictor预测
            # 提供默认odds以确保市场权重生效
            default_odds = {"home": 2.5, "draw": 3.2, "away": 2.8}
            pred = predictor.predict(home, away, odds=default_odds)
            # 根据概率判断预测结果
            probs = pred["prediction"]
            if probs["home_win"] >= probs["draw"] and probs["home_win"] >= probs["away_win"]:
                pred_result = "home"
            elif probs["away_win"] >= probs["draw"] and probs["away_win"] >= probs["home_win"]:
                pred_result = "away"
            else:
                pred_result = "draw"
            pred_score = get_score_prediction(pred, home, away)
            
            # 判断是否正确
            is_correct = pred_result == actual_result
            
            # 更新统计
            stats["total"] += 1
            stats["by_stage"][stage]["total"] += 1
            stats["by_year"][year]["total"] += 1
            
            if is_correct:
                stats["correct_result"] += 1
                stats["by_stage"][stage]["correct"] += 1
                stats["by_year"][year]["correct"] += 1
            else:
                # 记录预测错误的高信心比赛
                confidence = pred["prediction"].get("confidence", "未知")
                if "高" in confidence:
                    stats["upsets"].append({
                        "home": home,
                        "away": away,
                        "score": actual_score,
                        "predicted": pred_result,
                        "actual": actual_result,
                        "year": year
                    })
            
        except Exception as e:
            print(f"  ⚠️ 预测出错: {home} vs {away}: {e}")
    
    # 输出结果
    print("\n" + "=" * 60)
    print("📍 整体回测结果")
    print("=" * 60)
    accuracy = stats["correct_result"] / stats["total"] * 100 if stats["total"] > 0 else 0
    print(f"\n总体准确率: {accuracy:.1f}% ({stats['correct_result']}/{stats['total']})")
    
    print("\n📍 各年份准确率")
    print("-" * 40)
    for year in sorted(stats["by_year"].keys()):
        data = stats["by_year"][year]
        if data["total"] > 0:
            acc = data["correct"] / data["total"] * 100
            print(f"  {year}年: {acc:.1f}% ({data['correct']}/{data['total']})")
    
    print("\n📍 按比赛阶段准确率")
    print("-" * 40)
    stage_order = ["group", "round_of_16", "quarter", "semi", "final"]
    stage_names = {
        "group": "小组赛",
        "round_of_16": "16强",
        "quarter": "8强",
        "semi": "半决赛",
        "final": "决赛"
    }
    for stage in stage_order:
        if stage in stats["by_stage"]:
            data = stats["by_stage"][stage]
            if data["total"] > 0:
                acc = data["correct"] / data["total"] * 100
                name = stage_names.get(stage, stage)
                print(f"  {name}: {acc:.1f}% ({data['correct']}/{data['total']})")
    
    print("\n📍 冷门比赛（高信心预测错误）")
    print("-" * 40)
    if stats["upsets"]:
        for i, upset in enumerate(stats["upsets"][:5], 1):
            print(f"  {i}. {upset['home']} vs {upset['away']}")
            print(f"     比分: {upset['score']} | 预测: {upset['predicted']} | 实际: {upset['actual']}")
    else:
        print("  无")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()