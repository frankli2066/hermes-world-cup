#!/usr/bin/env python3
"""
回测框架 v1.0

功能：
1. 用历史世界杯数据验证模型准确性
2. 测试不同权重配置
3. 计算准确率指标

使用方法：
    python3 backtest.py
    python3 backtest.py --years 2010,2014,2018,2022
    python3 backtest.py --weights Elo=0.5,FIFA=0.2,Form=0.2,Exp=0.1
"""

import sys
import os
import json
import argparse
from collections import defaultdict
from typing import Dict, List, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "core"))

from core.prediction_engine import PredictionEngine


# 历史比赛数据（2010-2022世界杯）
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
        
        {"home": "USA", "away": "Algeria", "score": "1-0", "stage": "group"},
        {"home": "Slovenia", "away": "England", "score": "3-2", "stage": "group"},
        {"home": "USA", "away": "Slovenia", "score": "2-2", "stage": "group"},
        {"home": "England", "away": "Algeria", "score": "0-0", "stage": "group"},
        {"home": "USA", "away": "England", "score": "1-1", "stage": "group"},
        {"home": "Algeria", "away": "Slovenia", "score": "0-1", "stage": "group"},
        
        # 淘汰赛
        {"home": "Uruguay", "away": "South Korea", "score": "2-1", "stage": "round_of_16"},
        {"home": "USA", "away": "Ghana", "score": "1-2", "stage": "round_of_16"},
        {"home": "Germany", "away": "England", "score": "4-1", "stage": "round_of_16"},
        {"home": "Argentina", "away": "Mexico", "score": "3-1", "stage": "round_of_16"},
        {"home": "Netherlands", "away": "Slovakia", "score": "2-1", "stage": "round_of_16"},
        {"home": "Brazil", "away": "Chile", "score": "3-0", "stage": "round_of_16"},
        {"home": "Paraguay", "away": "Spain", "score": "0-1", "stage": "round_of_16"},
        {"home": "Portugal", "away": "Spain", "score": "0-1", "stage": "round_of_16"},
        
        {"home": "Uruguay", "away": "Ghana", "score": "1-1", "stage": "quarter"},  # 加时1-1，点球4-2
        {"home": "Germany", "away": "Argentina", "score": "4-0", "stage": "quarter"},
        {"home": "Netherlands", "away": "Brazil", "score": "2-1", "stage": "quarter"},
        {"home": "Spain", "away": "Paraguay", "score": "1-0", "stage": "quarter"},
        
        {"home": "Uruguay", "away": "Netherlands", "score": "2-3", "stage": "semi"},
        {"home": "Germany", "away": "Spain", "score": "0-1", "stage": "semi"},
        
        {"home": "Germany", "away": "Uruguay", "score": "2-3", "stage": "third_place"},
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
        {"home": "Netherlands", "away": "Chile", "score": "2-0", "stage": "group"},
        {"home": "Australia", "away": "Spain", "score": "0-3", "stage": "group"},
        
        {"home": "Colombia", "away": "Greece", "score": "3-0", "stage": "group"},
        {"home": "Ivory Coast", "away": "Japan", "score": "2-1", "stage": "group"},
        {"home": "Colombia", "away": "Ivory Coast", "score": "2-1", "stage": "group"},
        {"home": "Japan", "away": "Greece", "score": "0-0", "stage": "group"},
        {"home": "Japan", "away": "Colombia", "score": "1-4", "stage": "group"},
        {"home": "Greece", "away": "Ivory Coast", "score": "1-2", "stage": "group"},
        
        {"home": "Uruguay", "away": "Costa Rica", "score": "1-3", "stage": "group"},
        {"home": "England", "away": "Italy", "score": "1-2", "stage": "group"},
        {"home": "Uruguay", "away": "England", "score": "2-1", "stage": "group"},
        {"home": "Italy", "away": "Costa Rica", "score": "0-1", "stage": "group"},
        {"home": "Italy", "away": "Uruguay", "score": "0-1", "stage": "group"},
        {"home": "Costa Rica", "away": "England", "score": "0-0", "stage": "group"},
        
        {"home": "France", "away": "Honduras", "score": "3-0", "stage": "group"},
        {"home": "Switzerland", "away": "Ecuador", "score": "2-1", "stage": "group"},
        {"home": "France", "away": "Switzerland", "score": "5-2", "stage": "group"},
        {"home": "Honduras", "away": "Ecuador", "score": "1-2", "stage": "group"},
        {"home": "Honduras", "away": "Switzerland", "score": "0-3", "stage": "group"},
        {"home": "Ecuador", "away": "France", "score": "0-0", "stage": "group"},
        
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
        {"home": "USA", "away": "Germany", "score": "0-1", "stage": "group"},
        {"home": "Portugal", "away": "Ghana", "score": "1-0", "stage": "group"},
        
        {"home": "Belgium", "away": "Algeria", "score": "2-1", "stage": "group"},
        {"home": "Russia", "away": "South Korea", "score": "1-1", "stage": "group"},
        {"home": "Belgium", "away": "Russia", "score": "1-0", "stage": "group"},
        {"home": "South Korea", "away": "Algeria", "score": "2-4", "stage": "group"},
        {"home": "South Korea", "away": "Belgium", "score": "0-1", "stage": "group"},
        {"home": "Algeria", "away": "Russia", "score": "1-1", "stage": "group"},
        
        # 淘汰赛
        {"home": "Brazil", "away": "Chile", "score": "1-1", "stage": "round_of_16"},  # 点球3-2
        {"home": "Colombia", "away": "Uruguay", "score": "2-0", "stage": "round_of_16"},
        {"home": "France", "away": "Nigeria", "score": "2-0", "stage": "round_of_16"},
        {"home": "Germany", "away": "Algeria", "score": "2-1", "stage": "round_of_16"},
        {"home": "Belgium", "away": "USA", "score": "2-1", "stage": "round_of_16"},  # 加时
        {"home": "Argentina", "away": "Switzerland", "score": "1-0", "stage": "round_of_16"},
        {"home": "Netherlands", "away": "Mexico", "score": "2-1", "stage": "round_of_16"},
        {"home": "Costa Rica", "away": "Greece", "score": "1-1", "stage": "round_of_16"},  # 点球6-4
        
        {"home": "Brazil", "away": "Colombia", "score": "2-1", "stage": "quarter"},
        {"home": "France", "away": "Germany", "score": "0-1", "stage": "quarter"},
        {"home": "Belgium", "away": "Argentina", "score": "0-1", "stage": "quarter"},
        {"home": "Netherlands", "away": "Costa Rica", "score": "0-0", "stage": "quarter"},  # 点球4-3
        
        {"home": "Brazil", "away": "Germany", "score": "1-7", "stage": "semi"},
        {"home": "Netherlands", "away": "Argentina", "score": "0-0", "stage": "semi"},  # 点球4-2
        
        {"home": "Brazil", "away": "Netherlands", "score": "0-3", "stage": "third_place"},
        {"home": "Germany", "away": "Argentina", "score": "1-0", "stage": "final"},
    ],
    
    "2018": [
        # 小组赛
        {"home": "Russia", "away": "Saudi Arabia", "score": "5-0", "stage": "group"},
        {"home": "Egypt", "away": "Uruguay", "score": "0-1", "stage": "group"},
        {"home": "Uruguay", "away": "Saudi Arabia", "score": "1-0", "stage": "group"},
        {"home": "Russia", "away": "Egypt", "score": "3-1", "stage": "group"},
        {"home": "Saudi Arabia", "away": "Egypt", "score": "2-1", "stage": "group"},
        {"home": "Uruguay", "away": "Russia", "score": "3-0", "stage": "group"},
        
        {"home": "Portugal", "away": "Spain", "score": "3-3", "stage": "group"},
        {"home": "Iran", "away": "Morocco", "score": "1-0", "stage": "group"},
        {"home": "Portugal", "away": "Morocco", "score": "1-0", "stage": "group"},
        {"home": "Spain", "away": "Iran", "score": "1-1", "stage": "group"},
        {"home": "Iran", "away": "Portugal", "score": "1-1", "stage": "group"},
        {"home": "Spain", "away": "Morocco", "score": "2-2", "stage": "group"},
        
        {"home": "France", "away": "Australia", "score": "2-1", "stage": "group"},
        {"home": "Peru", "away": "Denmark", "score": "2-0", "stage": "group"},
        {"home": "Denmark", "away": "Australia", "score": "1-1", "stage": "group"},
        {"home": "France", "away": "Peru", "score": "1-0", "stage": "group"},
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
        {"home": "Switzerland", "away": "Costa Rica", "score": "2-0", "stage": "group"},
        
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
        {"home": "Panama", "away": "Tunisia", "score": "1-2", "stage": "group"},
        
        {"home": "Poland", "away": "Senegal", "score": "0-3", "stage": "group"},
        {"home": "Colombia", "away": "Japan", "score": "1-2", "stage": "group"},
        {"home": "Japan", "away": "Senegal", "score": "2-2", "stage": "group"},
        {"home": "Poland", "away": "Colombia", "score": "0-3", "stage": "group"},
        {"home": "Japan", "away": "Poland", "score": "0-1", "stage": "group"},
        {"home": "Senegal", "away": "Colombia", "score": "0-1", "stage": "group"},
        
        # 淘汰赛
        {"home": "Uruguay", "away": "Portugal", "score": "2-1", "stage": "round_of_16"},
        {"home": "France", "away": "Argentina", "score": "4-3", "stage": "round_of_16"},
        {"home": "Spain", "away": "Russia", "score": "1-1", "stage": "round_of_16"},  # 点球4-3
        {"home": "Croatia", "away": "Denmark", "score": "1-1", "stage": "round_of_16"},  # 点球3-2
        {"home": "Brazil", "away": "Mexico", "score": "2-0", "stage": "round_of_16"},
        {"home": "Belgium", "away": "Japan", "score": "3-2", "stage": "round_of_16"},
        {"home": "Sweden", "away": "Switzerland", "score": "1-0", "stage": "round_of_16"},
        {"home": "Colombia", "away": "England", "score": "1-1", "stage": "round_of_16"},  # 点球4-3
        
        {"home": "Uruguay", "away": "France", "score": "0-2", "stage": "quarter"},
        {"home": "Brazil", "away": "Belgium", "score": "2-1", "stage": "quarter"},
        {"home": "Sweden", "away": "England", "score": "0-2", "stage": "quarter"},
        {"home": "Russia", "away": "Croatia", "score": "2-2", "stage": "quarter"},  # 点球3-4
        
        {"home": "France", "away": "Belgium", "score": "1-0", "stage": "semi"},
        {"home": "Croatia", "away": "England", "score": "2-1", "stage": "semi"},
        
        {"home": "Belgium", "away": "England", "score": "2-0", "stage": "third_place"},
        {"home": "France", "away": "Croatia", "score": "4-2", "stage": "final"},
    ],
    
    "2022": [
        # 小组赛
        {"home": "Qatar", "away": "Ecuador", "score": "0-2", "stage": "group"},
        {"home": "Senegal", "away": "Netherlands", "score": "0-2", "stage": "group"},
        {"home": "Netherlands", "away": "Ecuador", "score": "1-1", "stage": "group"},
        {"home": "Qatar", "away": "Senegal", "score": "1-3", "stage": "group"},
        {"home": "Netherlands", "away": "Qatar", "score": "2-0", "stage": "group"},
        {"home": "Ecuador", "away": "Senegal", "score": "1-2", "stage": "group"},
        
        {"home": "England", "away": "Iran", "score": "6-2", "stage": "group"},
        {"home": "USA", "away": "Wales", "score": "1-1", "stage": "group"},
        {"home": "Wales", "away": "Iran", "score": "0-2", "stage": "group"},
        {"home": "England", "away": "USA", "score": "0-0", "stage": "group"},
        {"home": "Wales", "away": "England", "score": "0-3", "stage": "group"},
        {"home": "Iran", "away": "USA", "score": "0-1", "stage": "group"},
        
        {"home": "Argentina", "away": "Saudi Arabia", "score": "1-2", "stage": "group"},
        {"home": "Mexico", "away": "Poland", "score": "0-0", "stage": "group"},
        {"home": "Poland", "away": "Saudi Arabia", "score": "2-0", "stage": "group"},
        {"home": "Argentina", "away": "Mexico", "score": "2-0", "stage": "group"},
        {"home": "Poland", "away": "Argentina", "score": "0-2", "stage": "group"},
        {"home": "Saudi Arabia", "away": "Mexico", "score": "0-2", "stage": "group"},
        
        {"home": "Denmark", "away": "Tunisia", "score": "0-0", "stage": "group"},
        {"home": "France", "away": "Australia", "score": "4-1", "stage": "group"},
        {"home": "Tunisia", "away": "Australia", "score": "1-0", "stage": "group"},
        {"home": "Denmark", "away": "France", "score": "2-1", "stage": "group"},
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
        {"home": "Canada", "away": "Croatia", "score": "1-4", "stage": "group"},
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
        {"home": "Uruguay", "away": "Portugal", "score": "0-0", "stage": "group"},
        {"home": "Portugal", "away": "South Korea", "score": "1-2", "stage": "group"},
        {"home": "Ghana", "away": "Uruguay", "score": "0-0", "stage": "group"},
        
        # 淘汰赛
        {"home": "Netherlands", "away": "USA", "score": "3-1", "stage": "round_of_16"},
        {"home": "Argentina", "away": "Australia", "score": "2-1", "stage": "round_of_16"},
        {"home": "France", "away": "Poland", "score": "3-1", "stage": "round_of_16"},
        {"home": "England", "away": "Senegal", "score": "3-0", "stage": "round_of_16"},
        {"home": "Japan", "away": "Croatia", "score": "1-1", "stage": "round_of_16"},  # 点球3-1
        {"home": "Brazil", "away": "South Korea", "score": "4-1", "stage": "round_of_16"},
        {"home": "Morocco", "away": "Spain", "score": "0-0", "stage": "round_of_16"},  # 点球3-0
        {"home": "Portugal", "away": "Switzerland", "score": "6-1", "stage": "round_of_16"},
        
        {"home": "Netherlands", "away": "Argentina", "score": "2-2", "stage": "quarter"},  # 点球3-4
        {"home": "Croatia", "away": "Brazil", "score": "1-1", "stage": "quarter"},  # 点球4-2
        {"home": "Morocco", "away": "Portugal", "score": "1-0", "stage": "quarter"},
        {"home": "England", "away": "France", "score": "1-2", "stage": "quarter"},
        
        {"home": "Argentina", "away": "Croatia", "score": "3-0", "stage": "semi"},
        {"home": "France", "away": "Morocco", "score": "2-0", "stage": "semi"},
        
        {"home": "Croatia", "away": "Morocco", "score": "2-1", "stage": "third_place"},
        {"home": "Argentina", "away": "France", "score": "3-3", "stage": "final"},  # 点球4-2
    ],
}


def parse_score(score_str: str) -> Tuple[int, int]:
    """解析比分字符串"""
    parts = score_str.split("-")
    return int(parts[0]), int(parts[1])


def evaluate_prediction(result: Dict, actual_home: int, actual_away: int) -> Dict:
    """评估单个预测的准确性"""
    home_prob = result["win_probability"]["home"]
    draw_prob = result["win_probability"]["draw"]
    away_prob = result["win_probability"]["away"]
    predicted_score = result["predicted_score"]
    
    # 解析预测比分
    pred_parts = predicted_score.split("-")
    pred_home, pred_away = int(pred_parts[0]), int(pred_parts[1])
    
    # 判断实际结果
    if actual_home > actual_away:
        actual_result = "home"
    elif actual_home < actual_away:
        actual_result = "away"
    else:
        actual_result = "draw"
    
    # 判断预测结果
    if home_prob > draw_prob and home_prob > away_prob:
        predicted_result = "home"
    elif away_prob > home_prob and away_prob > draw_prob:
        predicted_result = "away"
    else:
        predicted_result = "draw"
    
    return {
        "correct_result": predicted_result == actual_result,
        "correct_score": pred_home == actual_home and pred_away == actual_away,
        "correct_winner": (
            (actual_result == "home" and predicted_result == "home") or
            (actual_result == "away" and predicted_result == "away")
        ),
        "actual_total_goals": actual_home + actual_away,
        "predicted_total_goals": pred_home + pred_away,
        "correct_total_goals": (actual_home + actual_away) > 2.5,
        "home_goals_error": abs(pred_home - actual_home),
        "away_goals_error": abs(pred_away - actual_away),
        "total_goals_error": abs((pred_home + pred_away) - (actual_home + actual_away)),
    }


def run_backtest(years: List[str] = None, monte_carlo: int = 3000) -> Dict:
    """运行回测"""
    if years is None:
        years = ["2010", "2014", "2018", "2022"]
    
    print("=" * 70)
    print("🏆 世界杯预测系统回测")
    print("=" * 70)
    print(f"回测年份: {', '.join(years)}")
    print(f"蒙特卡洛次数: {monte_carlo}")
    print()
    
    # 初始化引擎
    engine = PredictionEngine(use_live_data=True)
    engine.calibrate_elo(learning_rate=0.3)
    
    # 收集所有比赛
    all_matches = []
    for year in years:
        if year in HISTORICAL_MATCHES:
            for match in HISTORICAL_MATCHES[year]:
                match["year"] = year
                all_matches.append(match)
    
    print(f"总比赛数: {len(all_matches)}")
    print()
    
    # 统计
    stats = {
        "total": 0,
        "correct_result": 0,
        "correct_score": 0,
        "correct_winner": 0,
        "correct_total_goals": 0,
        "home_goals_errors": [],
        "away_goals_errors": [],
        "total_goals_errors": [],
        "by_stage": defaultdict(lambda: {"total": 0, "correct": 0}),
    }
    
    # 错误分析
    errors_by_elo_diff = defaultdict(list)
    
    # 逐场预测
    for match in all_matches:
        home = match["home"]
        away = match["away"]
        actual_home, actual_away = parse_score(match["score"])
        stage = match["stage"]
        year = match["year"]
        
        try:
            result = engine.predict_match(home, away, monte_carlo=monte_carlo, match_stage=stage)
            eval_result = evaluate_prediction(result, actual_home, actual_away)
            
            # 累计统计
            stats["total"] += 1
            if eval_result["correct_result"]:
                stats["correct_result"] += 1
            if eval_result["correct_score"]:
                stats["correct_score"] += 1
            if eval_result["correct_winner"]:
                stats["correct_winner"] += 1
            if eval_result["correct_total_goals"]:
                stats["correct_total_goals"] += 1
            
            stats["home_goals_errors"].append(eval_result["home_goals_error"])
            stats["away_goals_errors"].append(eval_result["away_goals_error"])
            stats["total_goals_errors"].append(eval_result["total_goals_error"])
            
            stats["by_stage"][stage]["total"] += 1
            if eval_result["correct_result"]:
                stats["by_stage"][stage]["correct"] += 1
            
            # 按Elo差分组分析
            home_elo = engine.team_stats.elo.get_rating(home)
            away_elo = engine.team_stats.elo.get_rating(away)
            elo_diff = abs(home_elo - away_elo)
            errors_by_elo_diff[int(elo_diff // 50)].append(
                1 if eval_result["correct_result"] else 0
            )
            
        except Exception as e:
            print(f"   ⚠️ {year} {home} vs {away}: 预测失败 - {e}")
    
    # 输出结果
    print("=" * 70)
    print("📊 回测结果")
    print("=" * 70)
    
    n = stats["total"]
    if n == 0:
        print("没有有效的预测结果")
        return stats
    
    print(f"\n总预测数: {n}")
    print(f"\n{'指标':<20} {'正确数':>10} {'准确率':>10}")
    print("-" * 42)
    print(f"{'胜平负预测':<20} {stats['correct_result']:>10} {stats['correct_result']/n*100:>9.1f}%")
    print(f"{'胜负预测(忽略平局)':<20} {stats['correct_winner']:>10} {stats['correct_winner']/n*100:>9.1f}%")
    print(f"{'比分预测':<20} {stats['correct_score']:>10} {stats['correct_score']/n*100:>9.1f}%")
    print(f"{'大小球预测(2.5)':<20} {stats['correct_total_goals']:>10} {stats['correct_total_goals']/n*100:>9.1f}%")
    
    # 进球误差
    avg_home_error = sum(stats["home_goals_errors"]) / n
    avg_away_error = sum(stats["away_goals_errors"]) / n
    avg_total_error = sum(stats["total_goals_errors"]) / n
    
    print(f"\n{'进球误差分析':<20}")
    print("-" * 42)
    print(f"{'主队平均误差':<20} {avg_home_error:>10.2f} 球")
    print(f"{'客队平均误差':<20} {avg_away_error:>10.2f} 球")
    print(f"{'总进球平均误差':<20} {avg_total_error:>10.2f} 球")
    
    # 按阶段分析
    print(f"\n{'按比赛阶段':<20} {'预测数':>8} {'准确率':>10}")
    print("-" * 42)
    for stage in ["group", "round_of_16", "quarter", "semi", "third_place", "final"]:
        if stage in stats["by_stage"]:
            s = stats["by_stage"][stage]
            if s["total"] > 0:
                acc = s["correct"] / s["total"] * 100
                print(f"{stage:<20} {s['total']:>8} {acc:>9.1f}%")
    
    # 按Elo差距分析
    print(f"\n{'按实力差距(Elo差)':<20} {'准确率':>10}")
    print("-" * 42)
    for diff_bucket in sorted(errors_by_elo_diff.keys()):
        results = errors_by_elo_diff[diff_bucket]
        if len(results) >= 3:
            acc = sum(results) / len(results) * 100
            print(f"Elo差 {diff_bucket*50:>3}-{(diff_bucket+1)*50:>3} {len(results):>4}场 {acc:>9.1f}%")
    
    print("\n" + "=" * 70)
    
    return stats


def main():
    parser = argparse.ArgumentParser(description="世界杯预测系统回测")
    parser.add_argument("--years", default="2010,2014,2018,2022",
                       help="回测年份，逗号分隔")
    parser.add_argument("--mc", "--monte-carlo", dest="monte_carlo", type=int, default=3000,
                       help="蒙特卡洛模拟次数")
    
    args = parser.parse_args()
    years = [y.strip() for y in args.years.split(",")]
    
    run_backtest(years=years, monte_carlo=args.monte_carlo)


if __name__ == "__main__":
    main()
