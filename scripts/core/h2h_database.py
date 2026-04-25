#!/usr/bin/env python3
"""
H2H往绩数据库 v1.0
====================
历史对战记录数据库

记录重要球队之间的历史对战结果
用于识别"恐X症"、主场优势、历史规律等
"""

import os
import json
from typing import Dict, List, Tuple, Optional
from datetime import datetime

# ============ 路径配置 ============
BASE_DIR = os.path.expanduser("~/hermes-world-cup/")
DATA_DIR = os.path.join(BASE_DIR, "data/")


# ============ H2H往绩数据 ============
# 格式: H2H_DATA["TeamA"]["TeamB"] = [比赛列表]
# 每场比赛: {"year": 年份, "score": "主-客", "winner": "home/away/draw", "tournament": "赛事", "venue": "neutral/home/away"}

H2H_DATA = {
    "Germany": {
        "South Korea": [
            {"year": 2018, "score": "0-2", "winner": "away", "tournament": "WC", "venue": "neutral", "note": "爆冷出局"},
            {"year": 2002, "score": "1-0", "winner": "home", "tournament": "WC", "venue": "neutral"},
        ],
        "Brazil": [
            {"year": 2014, "score": "1-7", "winner": "away", "tournament": "WC", "venue": "neutral", "note": "惨案"},
            {"year": 2002, "score": "0-2", "winner": "away", "tournament": "WC", "venue": "neutral"},
        ],
        "Argentina": [
            {"year": 2014, "score": "1-0", "winner": "home", "tournament": "WC", "venue": "neutral"},
            {"year": 2010, "score": "0-4", "winner": "away", "tournament": "WC", "venue": "neutral", "note": "阿根廷vs德国"},
        ],
        "Mexico": [
            {"year": 2018, "score": "0-1", "winner": "away", "tournament": "WC", "venue": "neutral", "note": "冷门"},
        ],
        "Japan": [
            {"year": 2022, "score": "1-2", "winner": "away", "tournament": "WC", "venue": "neutral", "note": "爆冷"},
        ],
        "Spain": [
            {"year": 2010, "score": "0-1", "winner": "away", "tournament": "WC", "venue": "neutral"},
            {"year": 2008, "score": "2-1", "winner": "home", "tournament": "Euro", "venue": "neutral"},
            {"year": 2022, "score": "1-2", "winner": "away", "tournament": "WC", "venue": "neutral"},
        ],
        "France": [
            {"year": 2014, "score": "0-1", "winner": "away", "tournament": "WC", "venue": "neutral"},
            {"year": 2022, "score": "2-1", "winner": "home", "tournament": "WC", "venue": "neutral"},
        ],
        "England": [
            {"year": 2010, "score": "4-1", "winner": "home", "tournament": "WC", "venue": "neutral"},
            {"year": 1966, "score": "2-4", "winner": "away", "tournament": "WC", "venue": "home", "note": "经典逆转"},
        ],
    },

    "Brazil": {
        "Germany": [
            {"year": 2014, "score": "1-7", "winner": "away", "tournament": "WC", "venue": "home", "note": "米内罗惨案"},
            {"year": 2002, "score": "2-0", "winner": "home", "tournament": "WC", "venue": "neutral"},
        ],
        "Argentina": [
            {"year": 2022, "score": "2-2", "winner": "draw", "tournament": "WC", "venue": "neutral", "penalties": True},
            {"year": 2021, "score": "0-0", "winner": "draw", "tournament": "Copa America", "venue": "neutral"},
            {"year": 2019, "score": "2-0", "winner": "home", "tournament": "Copa America", "venue": "home"},
        ],
        "Croatia": [
            {"year": 2022, "score": "1-1", "winner": "draw", "tournament": "WC", "venue": "neutral", "penalties": True},
        ],
        "Belgium": [
            {"year": 2018, "score": "2-1", "winner": "home", "tournament": "WC", "venue": "neutral"},
        ],
        "Serbia": [
            {"year": 2022, "score": "2-0", "winner": "home", "tournament": "WC", "venue": "neutral"},
        ],
        "South Korea": [
            {"year": 2022, "score": "4-1", "winner": "home", "tournament": "WC", "venue": "neutral"},
        ],
        "Switzerland": [
            {"year": 2022, "score": "1-1", "winner": "draw", "tournament": "WC", "venue": "neutral"},
            {"year": 2018, "score": "1-1", "winner": "draw", "tournament": "WC", "venue": "neutral"},
        ],
        "Mexico": [
            {"year": 2022, "score": "4-1", "winner": "home", "tournament": "WC", "venue": "neutral"},
            {"year": 2018, "score": "2-0", "winner": "home", "tournament": "WC", "venue": "neutral"},
        ],
    },

    "Argentina": {
        "Brazil": [
            {"year": 2022, "score": "2-2", "winner": "draw", "tournament": "WC", "venue": "neutral", "penalties": True, "note": "点球夺冠"},
            {"year": 2021, "score": "1-0", "winner": "home", "tournament": "Copa America", "venue": "neutral"},
            {"year": 2019, "score": "2-1", "winner": "home", "tournament": "Copa America", "venue": "neutral"},
        ],
        "Germany": [
            {"year": 2014, "score": "0-1", "winner": "away", "tournament": "WC", "venue": "neutral"},
            {"year": 2010, "score": "4-0", "winner": "home", "tournament": "WC", "venue": "neutral"},
        ],
        "France": [
            {"year": 2022, "score": "2-2", "winner": "draw", "tournament": "WC", "venue": "neutral", "penalties": True, "note": "决赛经典"},
        ],
        "Croatia": [
            {"year": 2022, "score": "3-0", "winner": "home", "tournament": "WC", "venue": "neutral"},
        ],
        "Netherlands": [
            {"year": 2022, "score": "2-2", "winner": "draw", "tournament": "WC", "venue": "neutral", "penalties": True},
            {"year": 2014, "score": "0-0", "winner": "draw", "tournament": "WC", "venue": "neutral", "penalties": True},
        ],
        "Saudi Arabia": [
            {"year": 2022, "score": "1-2", "winner": "away", "tournament": "WC", "venue": "neutral", "note": "首战爆冷"},
        ],
        "Mexico": [
            {"year": 2022, "score": "2-0", "winner": "home", "tournament": "WC", "venue": "neutral"},
            {"year": 2018, "score": "2-1", "winner": "home", "tournament": "WC", "venue": "neutral"},
        ],
        "Iceland": [
            {"year": 2018, "score": "1-1", "winner": "draw", "tournament": "WC", "venue": "neutral"},
        ],
        "Morocco": [
            {"year": 2022, "score": "0-0", "winner": "draw", "tournament": "WC", "venue": "neutral"},
        ],
        "Australia": [
            {"year": 2022, "score": "2-1", "winner": "home", "tournament": "WC", "venue": "neutral"},
        ],
    },

    "France": {
        "Argentina": [
            {"year": 2022, "score": "2-2", "winner": "draw", "tournament": "WC", "venue": "neutral", "penalties": True},
        ],
        "Morocco": [
            {"year": 2022, "score": "2-0", "winner": "home", "tournament": "WC", "venue": "neutral"},
        ],
        "England": [
            {"year": 2022, "score": "1-2", "winner": "away", "tournament": "WC", "venue": "neutral"},
            {"year": 2018, "score": "4-2", "winner": "home", "tournament": "WC", "venue": "neutral"},
        ],
        "Germany": [
            {"year": 2022, "score": "1-2", "winner": "away", "tournament": "WC", "venue": "neutral"},
            {"year": 2014, "score": "0-1", "winner": "away", "tournament": "WC", "venue": "neutral"},
        ],
        "Brazil": [
            {"year": 2006, "score": "1-0", "winner": "home", "tournament": "WC", "venue": "neutral"},
        ],
        "Spain": [
            {"year": 2022, "score": "1-2", "winner": "away", "tournament": "WC", "venue": "neutral"},
            {"year": 2024, "score": "1-2", "winner": "away", "tournament": "Euro", "venue": "neutral"},
        ],
        "Portugal": [
            {"year": 2022, "score": "0-0", "winner": "draw", "tournament": "WC", "venue": "neutral", "penalties": True},
        ],
        "Belgium": [
            {"year": 2018, "score": "1-0", "winner": "home", "tournament": "WC", "venue": "neutral"},
        ],
        "Switzerland": [
            {"year": 2021, "score": "3-3", "winner": "draw", "tournament": "Euro", "venue": "neutral", "penalties": True},
            {"year": 2024, "score": "1-0", "winner": "home", "tournament": "Euro", "venue": "neutral"},
        ],
        "Iceland": [
            {"year": 2018, "score": "0-0", "winner": "draw", "tournament": "WC", "venue": "neutral"},
        ],
    },

    "England": {
        "France": [
            {"year": 2022, "score": "1-2", "winner": "away", "tournament": "WC", "venue": "neutral"},
            {"year": 2018, "score": "3-1", "winner": "home", "tournament": "WC", "venue": "neutral"},
        ],
        "Germany": [
            {"year": 2010, "score": "1-4", "winner": "away", "tournament": "WC", "venue": "neutral"},
            {"year": 1966, "score": "4-2", "winner": "home", "tournament": "WC", "venue": "home", "note": "夺冠"},
        ],
        "Croatia": [
            {"year": 2018, "score": "1-2", "winner": "away", "tournament": "WC", "venue": "neutral", "extra": True},
            {"year": 2020, "score": "0-1", "winner": "away", "tournament": "Euro", "venue": "neutral"},
        ],
        "Iceland": [
            {"year": 2016, "score": "1-2", "winner": "away", "tournament": "Euro", "venue": "neutral", "note": "冷门"},
        ],
        "Italy": [
            {"year": 2021, "score": "1-1", "winner": "draw", "tournament": "Euro", "venue": "neutral", "penalties": True},
            {"year": 2012, "score": "0-0", "winner": "draw", "tournament": "Euro", "venue": "neutral", "penalties": True},
        ],
        "Spain": [
            {"year": 2018, "score": "0-2", "winner": "away", "tournament": " Nations", "venue": "neutral"},
            {"year": 2024, "score": "1-1", "winner": "draw", "tournament": "Euro", "venue": "neutral"},
        ],
        "Denmark": [
            {"year": 2020, "score": "2-1", "winner": "home", "tournament": "Euro", "venue": "neutral", "extra": True},
            {"year": 2021, "score": "1-1", "winner": "draw", "tournament": "Euro", "venue": "neutral"},
        ],
        "USA": [
            {"year": 2022, "score": "0-0", "winner": "draw", "tournament": "WC", "venue": "neutral"},
        ],
        "Senegal": [
            {"year": 2022, "score": "3-0", "winner": "home", "tournament": "WC", "venue": "neutral"},
        ],
    },

    "Spain": {
        "Germany": [
            {"year": 2022, "score": "1-2", "winner": "away", "tournament": "WC", "venue": "neutral", "note": "冷门"},
            {"year": 2010, "score": "1-0", "winner": "home", "tournament": "WC", "venue": "neutral", "note": "决赛绝杀"},
            {"year": 2008, "score": "1-0", "winner": "home", "tournament": "Euro", "venue": "neutral", "note": "决赛"},
        ],
        "Brazil": [
            {"year": 2018, "score": "1-2", "winner": "away", "tournament": "UCC", "venue": "neutral"},
        ],
        "France": [
            {"year": 2022, "score": "1-2", "winner": "away", "tournament": "WC", "venue": "neutral"},
            {"year": 2024, "score": "2-1", "winner": "home", "tournament": "Euro", "venue": "neutral"},
        ],
        "Italy": [
            {"year": 2024, "score": "1-0", "winner": "home", "tournament": "Euro", "venue": "neutral"},
            {"year": 2016, "score": "1-1", "winner": "draw", "tournament": "Euro", "venue": "neutral", "penalties": True},
            {"year": 2008, "score": "0-0", "winner": "draw", "tournament": "Euro", "venue": "neutral", "penalties": True},
        ],
        "Portugal": [
            {"year": 2018, "score": "2-2", "winner": "draw", "tournament": "WC", "venue": "neutral"},
            {"year": 2024, "score": "0-0", "winner": "draw", "tournament": "Euro", "venue": "neutral", "penalties": True},
        ],
        "Netherlands": [
            {"year": 2024, "score": "3-0", "winner": "home", "tournament": "Euro", "venue": "neutral"},
        ],
        "Croatia": [
            {"year": 2024, "score": "3-0", "winner": "home", "tournament": "Euro", "venue": "neutral"},
        ],
    },

    "Italy": {
        "Germany": [
            {"year": 2012, "score": "2-1", "winner": "home", "tournament": "Euro", "venue": "neutral", "note": "决赛"},
        ],
        "Spain": [
            {"year": 2016, "score": "1-1", "winner": "draw", "tournament": "Euro", "venue": "neutral", "penalties": True},
            {"year": 2008, "score": "0-0", "winner": "draw", "tournament": "Euro", "venue": "neutral", "penalties": True},
        ],
        "France": [
            {"year": 2021, "score": "1-1", "winner": "draw", "tournament": "Euro", "venue": "neutral", "penalties": True},
        ],
        "England": [
            {"year": 2012, "score": "0-0", "winner": "draw", "tournament": "Euro", "venue": "neutral", "penalties": True},
            {"year": 2021, "score": "1-1", "winner": "draw", "tournament": "Euro", "venue": "neutral", "penalties": True, "note": "决赛夺冠"},
        ],
        "Belgium": [
            {"year": 2021, "score": "2-0", "winner": "home", "tournament": "Euro", "venue": "neutral"},
        ],
        "Austria": [
            {"year": 2021, "score": "2-1", "winner": "home", "tournament": "Euro", "venue": "neutral", "extra": True},
        ],
        "Turkey": [
            {"year": 2020, "score": "3-0", "winner": "home", "tournament": "Euro", "venue": "neutral"},
        ],
        "Wales": [
            {"year": 2016, "score": "2-0", "winner": "home", "tournament": "Euro", "venue": "neutral"},
        ],
    },

    "Netherlands": {
        "Argentina": [
            {"year": 2022, "score": "2-2", "winner": "draw", "tournament": "WC", "venue": "neutral", "penalties": True},
            {"year": 2014, "score": "0-0", "winner": "draw", "tournament": "WC", "venue": "neutral", "penalties": True},
        ],
        "England": [
            {"year": 2019, "score": "0-1", "winner": "away", "tournament": "Nations", "venue": "neutral"},
        ],
        "Croatia": [
            {"year": 2018, "score": "0-0", "winner": "draw", "tournament": "WC", "venue": "neutral", "penalties": True},
        ],
        "Czech Republic": [
            {"year": 2020, "score": "0-2", "winner": "away", "tournament": "Euro", "venue": "neutral", "note": "冷门"},
        ],
        "Senegal": [
            {"year": 2022, "score": "2-0", "winner": "home", "tournament": "WC", "venue": "neutral"},
        ],
        "USA": [
            {"year": 2022, "score": "3-1", "winner": "home", "tournament": "WC", "venue": "neutral"},
        ],
    },

    "Portugal": {
        "France": [
            {"year": 2022, "score": "0-0", "winner": "draw", "tournament": "WC", "venue": "neutral", "penalties": True},
            {"year": 2016, "score": "1-0", "winner": "home", "tournament": "Euro", "venue": "neutral", "note": "决赛夺冠"},
            {"year": 2024, "score": "0-0", "winner": "draw", "tournament": "Euro", "venue": "neutral", "penalties": True},
        ],
        "Morocco": [
            {"year": 2022, "score": "0-1", "winner": "away", "tournament": "WC", "venue": "neutral", "note": "冷门"},
        ],
        "Spain": [
            {"year": 2018, "score": "2-2", "winner": "draw", "tournament": "WC", "venue": "neutral"},
            {"year": 2024, "score": "0-0", "winner": "draw", "tournament": "Euro", "venue": "neutral", "penalties": True},
        ],
        "Belgium": [
            {"year": 2021, "score": "1-0", "winner": "home", "tournament": "Euro", "venue": "neutral"},
        ],
        "Switzerland": [
            {"year": 2022, "score": "6-1", "winner": "home", "tournament": "WC", "venue": "neutral"},
        ],
        "Uruguay": [
            {"year": 2018, "score": "1-2", "winner": "away", "tournament": "WC", "venue": "neutral"},
        ],
        "Wales": [
            {"year": 2016, "score": "2-0", "winner": "home", "tournament": "Euro", "venue": "neutral", "note": "半决赛"},
        ],
    },

    "Morocco": {
        "Portugal": [
            {"year": 2022, "score": "1-0", "winner": "home", "tournament": "WC", "venue": "neutral", "note": "4强黑马"},
            {"year": 2018, "score": "1-0", "winner": "home", "tournament": "WC", "venue": "neutral"},
        ],
        "Spain": [
            {"year": 2022, "score": "0-0", "winner": "draw", "tournament": "WC", "venue": "neutral", "penalties": True, "note": "16强"},
        ],
        "France": [
            {"year": 2022, "score": "0-2", "winner": "away", "tournament": "WC", "venue": "neutral"},
        ],
        "Croatia": [
            {"year": 2022, "score": "0-0", "winner": "draw", "tournament": "WC", "venue": "neutral"},
        ],
        "Iran": [
            {"year": 2018, "score": "1-0", "winner": "home", "tournament": "WC", "venue": "neutral"},
        ],
    },

    "Croatia": {
        "Argentina": [
            {"year": 2022, "score": "0-3", "winner": "away", "tournament": "WC", "venue": "neutral"},
        ],
        "Brazil": [
            {"year": 2022, "score": "1-1", "winner": "draw", "tournament": "WC", "venue": "neutral", "penalties": True},
        ],
        "England": [
            {"year": 2018, "score": "2-1", "winner": "home", "tournament": "WC", "venue": "neutral", "extra": True, "note": "逆转"},
        ],
        "Denmark": [
            {"year": 2018, "score": "1-1", "winner": "draw", "tournament": "WC", "venue": "neutral", "penalties": True},
        ],
        "Russia": [
            {"year": 2018, "score": "1-1", "winner": "draw", "tournament": "WC", "venue": "neutral", "penalties": True},
        ],
        "Japan": [
            {"year": 2022, "score": "1-1", "winner": "draw", "tournament": "WC", "venue": "neutral", "penalties": True},
        ],
    },

    "Belgium": {
        "Brazil": [
            {"year": 2018, "score": "1-2", "winner": "away", "tournament": "WC", "venue": "neutral"},
        ],
        "France": [
            {"year": 2018, "score": "0-1", "winner": "away", "tournament": "WC", "venue": "neutral"},
        ],
        "Italy": [
            {"year": 2021, "score": "0-2", "winner": "away", "tournament": "Euro", "venue": "neutral"},
        ],
        "Portugal": [
            {"year": 2021, "score": "0-1", "winner": "away", "tournament": "Euro", "venue": "neutral"},
        ],
        "Japan": [
            {"year": 2018, "score": "3-2", "winner": "home", "tournament": "WC", "venue": "neutral", "note": "逆转"},
        ],
    },

    "Japan": {
        "Germany": [
            {"year": 2022, "score": "2-1", "winner": "home", "tournament": "WC", "venue": "neutral", "note": "惊天冷门"},
            {"year": 2018, "score": "2-3", "winner": "away", "tournament": "WC", "venue": "neutral", "note": "被逆转"},
        ],
        "Spain": [
            {"year": 2022, "score": "2-1", "winner": "home", "tournament": "WC", "venue": "neutral", "note": "逆转绝杀"},
        ],
        "Croatia": [
            {"year": 2022, "score": "1-1", "winner": "draw", "tournament": "WC", "venue": "neutral", "penalties": True},
        ],
        "Belgium": [
            {"year": 2018, "score": "2-3", "winner": "away", "tournament": "WC", "venue": "neutral", "note": "日本被逆转"},
        ],
        "South Korea": [
            {"year": 2019, "score": "1-0", "winner": "home", "tournament": "EAF", "venue": "neutral"},
        ],
    },

    "South Korea": {
        "Germany": [
            {"year": 2018, "score": "2-0", "winner": "home", "tournament": "WC", "venue": "neutral", "note": "绝杀逆转"},
            {"year": 2002, "score": "0-1", "winner": "away", "tournament": "WC", "venue": "neutral"},
        ],
        "Portugal": [
            {"year": 2022, "score": "2-1", "winner": "home", "tournament": "WC", "venue": "neutral", "note": "绝杀"},
        ],
    },

    "Saudi Arabia": {
        "Argentina": [
            {"year": 2022, "score": "2-1", "winner": "home", "tournament": "WC", "venue": "neutral", "note": "史诗级冷门"},
        ],
        "Poland": [
            {"year": 2022, "score": "2-0", "winner": "home", "tournament": "WC", "venue": "neutral"},
        ],
        "Mexico": [
            {"year": 2022, "score": "1-2", "winner": "away", "tournament": "WC", "venue": "neutral"},
        ],
    },

    "Mexico": {
        "Brazil": [
            {"year": 2022, "score": "1-4", "winner": "away", "tournament": "WC", "venue": "neutral"},
            {"year": 2018, "score": "0-2", "winner": "away", "tournament": "WC", "venue": "neutral"},
        ],
        "Argentina": [
            {"year": 2022, "score": "0-2", "winner": "away", "tournament": "WC", "venue": "neutral"},
            {"year": 2018, "score": "0-3", "winner": "away", "tournament": "WC", "venue": "neutral"},
        ],
        "Germany": [
            {"year": 2018, "score": "1-0", "winner": "home", "tournament": "WC", "venue": "neutral", "note": "爆冷"},
        ],
        "Sweden": [
            {"year": 1958, "score": "1-3", "winner": "away", "tournament": "WC", "venue": "neutral"},
        ],
    },

    "Poland": {
        "Germany": [
            {"year": 2006, "score": "0-1", "winner": "away", "tournament": "WC", "venue": "neutral"},
            {"year": 2020, "score": "1-0", "winner": "home", "tournament": "Euro", "venue": "neutral"},
            {"year": 2022, "score": "0-0", "winner": "draw", "tournament": "Euro", "venue": "neutral"},
        ],
        "Japan": [
            {"year": 2022, "score": "0-1", "winner": "away", "tournament": "WC", "venue": "neutral"},
        ],
    },

    "Senegal": {
        "Netherlands": [
            {"year": 2022, "score": "0-2", "winner": "away", "tournament": "WC", "venue": "neutral"},
        ],
        "Ecuador": [
            {"year": 2022, "score": "1-2", "winner": "away", "tournament": "WC", "venue": "neutral"},
        ],
        "Netherlands": [
            {"year": 2022, "score": "0-2", "winner": "away", "tournament": "WC", "venue": "neutral"},
        ],
    },

    "Egypt": {
        "Uruguay": [
            {"year": 2018, "score": "0-1", "winner": "away", "tournament": "WC", "venue": "neutral"},
        ],
    },

    "Iceland": {
        "Argentina": [
            {"year": 2018, "score": "1-1", "winner": "draw", "tournament": "WC", "venue": "neutral"},
        ],
        "England": [
            {"year": 2016, "score": "2-1", "winner": "home", "tournament": "Euro", "venue": "neutral", "note": "神话"},
        ],
        "France": [
            {"year": 2018, "score": "0-0", "winner": "draw", "tournament": "WC", "venue": "neutral"},
        ],
        "Croatia": [
            {"year": 2018, "score": "1-2", "winner": "away", "tournament": "WC", "venue": "neutral"},
        ],
    },

    "Wales": {
        "Portugal": [
            {"year": 2016, "score": "0-2", "winner": "away", "tournament": "Euro", "venue": "neutral"},
        ],
        "Belgium": [
            {"year": 2016, "score": "3-1", "winner": "home", "tournament": "Euro", "venue": "neutral", "note": "半决赛"},
        ],
        "Italy": [
            {"year": 2016, "score": "0-2", "winner": "away", "tournament": "Euro", "venue": "neutral"},
        ],
    },

    "Switzerland": {
        "France": [
            {"year": 2021, "score": "3-3", "winner": "draw", "tournament": "Euro", "venue": "neutral", "penalties": True},
            {"year": 2024, "score": "0-1", "winner": "away", "tournament": "Euro", "venue": "neutral"},
        ],
        "Portugal": [
            {"year": 2022, "score": "1-6", "winner": "away", "tournament": "WC", "venue": "neutral"},
        ],
        "Spain": [
            {"year": 2021, "score": "1-1", "winner": "draw", "tournament": "Euro", "venue": "neutral", "penalties": True},
        ],
        "Italy": [
            {"year": 2024, "score": "2-0", "winner": "home", "tournament": "Euro", "venue": "neutral"},
        ],
    },

    "Colombia": {
        "Uruguay": [
            {"year": 2018, "score": "0-2", "winner": "away", "tournament": "WC", "venue": "neutral"},
        ],
        "Brazil": [
            {"year": 2014, "score": "1-2", "winner": "away", "tournament": "WC", "venue": "neutral"},
        ],
        "England": [
            {"year": 2018, "score": "1-1", "winner": "draw", "tournament": "WC", "venue": "neutral", "penalties": True},
        ],
    },

    "Uruguay": {
        "Portugal": [
            {"year": 2018, "score": "2-1", "winner": "home", "tournament": "WC", "venue": "neutral"},
        ],
        "France": [
            {"year": 2018, "score": "0-2", "winner": "away", "tournament": "WC", "venue": "neutral"},
        ],
        "Colombia": [
            {"year": 2018, "score": "2-0", "winner": "home", "tournament": "WC", "venue": "neutral"},
        ],
        "Ghana": [
            {"year": 2010, "score": "0-2", "winner": "away", "tournament": "WC", "venue": "neutral", "note": "苏亚雷斯手球"},
        ],
        "Italy": [
            {"year": 2010, "score": "0-0", "winner": "draw", "tournament": "WC", "venue": "neutral"},
            {"year": 2014, "score": "0-1", "winner": "away", "tournament": "WC", "venue": "neutral"},
        ],
        "England": [
            {"year": 2010, "score": "0-0", "winner": "draw", "tournament": "WC", "venue": "neutral"},
            {"year": 2018, "score": "0-2", "winner": "away", "tournament": "WC", "venue": "neutral"},
        ],
    },

    # ========== 新增更多球队 ==========

    "Denmark": {
        "England": [
            {"year": 2020, "score": "1-2", "winner": "away", "tournament": "Euro", "venue": "neutral", "extra": True},
            {"year": 2024, "score": "1-1", "winner": "draw", "tournament": "Euro", "venue": "neutral"},
        ],
        "Germany": [
            {"year": 2012, "score": "2-1", "winner": "home", "tournament": "Euro", "venue": "neutral"},
        ],
        "Netherlands": [
            {"year": 2020, "score": "0-0", "winner": "draw", "tournament": "Euro", "venue": "neutral", "penalties": True},
        ],
        "Croatia": [
            {"year": 2018, "score": "1-1", "winner": "draw", "tournament": "WC", "venue": "neutral", "penalties": True},
        ],
        "Czech Republic": [
            {"year": 2000, "score": "0-1", "winner": "away", "tournament": "Euro", "venue": "neutral"},
        ],
        "Serbia": [
            {"year": 2024, "score": "1-1", "winner": "draw", "tournament": "Euro", "venue": "neutral"},
        ],
        "Slovenia": [
            {"year": 2000, "score": "0-0", "winner": "draw", "tournament": "Euro", "venue": "neutral"},
        ],
        "Austria": [
            {"year": 2024, "score": "2-0", "winner": "home", "tournament": "Euro", "venue": "neutral"},
        ],
    },

    "Ghana": {
        "Germany": [
            {"year": 2014, "score": "2-2", "winner": "draw", "tournament": "WC", "venue": "neutral"},
            {"year": 2010, "score": "0-1", "winner": "away", "tournament": "WC", "venue": "neutral"},
        ],
        "Uruguay": [
            {"year": 2010, "score": "1-1", "winner": "draw", "tournament": "WC", "venue": "neutral", "penalties": True},
            {"year": 2014, "score": "1-0", "winner": "home", "tournament": "WC", "venue": "neutral"},
        ],
        "USA": [
            {"year": 2014, "score": "1-1", "winner": "draw", "tournament": "WC", "venue": "neutral"},
        ],
        "Portugal": [
            {"year": 2014, "score": "1-1", "winner": "draw", "tournament": "WC", "venue": "neutral"},
        ],
        "Australia": [
            {"year": 2014, "score": "1-1", "winner": "draw", "tournament": "WC", "venue": "neutral"},
        ],
    },

    "Australia": {
        "Germany": [
            {"year": 2010, "score": "0-4", "winner": "away", "tournament": "WC", "venue": "neutral"},
            {"year": 2022, "score": "1-0", "winner": "home", "tournament": "WC", "venue": "neutral", "note": "爆冷"},
        ],
        "Japan": [
            {"year": 2022, "score": "2-1", "winner": "home", "tournament": "WC", "venue": "neutral", "note": "逆转"},
        ],
        "Argentina": [
            {"year": 2022, "score": "1-2", "winner": "away", "tournament": "WC", "venue": "neutral"},
        ],
        "France": [
            {"year": 2022, "score": "1-4", "winner": "away", "tournament": "WC", "venue": "neutral"},
        ],
        "Peru": [
            {"year": 2022, "score": "2-1", "winner": "home", "tournament": "WC", "venue": "neutral", "extra": True},
        ],
    },

    "Serbia": {
        "Brazil": [
            {"year": 2018, "score": "0-2", "winner": "away", "tournament": "WC", "venue": "neutral"},
            {"year": 2022, "score": "2-0", "winner": "home", "tournament": "WC", "venue": "neutral"},
        ],
        "Switzerland": [
            {"year": 2022, "score": "2-3", "winner": "away", "tournament": "WC", "venue": "neutral"},
        ],
        "Cameroon": [
            {"year": 2010, "score": "1-0", "winner": "home", "tournament": "WC", "venue": "neutral"},
        ],
        "Ghana": [
            {"year": 2018, "score": "1-2", "winner": "away", "tournament": "WC", "venue": "neutral"},
        ],
    },

    "Cameroon": {
        "Brazil": [
            {"year": 2010, "score": "1-2", "winner": "away", "tournament": "WC", "venue": "neutral"},
            {"year": 2014, "score": "0-4", "winner": "away", "tournament": "WC", "venue": "neutral"},
        ],
        "Croatia": [
            {"year": 2014, "score": "0-4", "winner": "away", "tournament": "WC", "venue": "neutral"},
        ],
        "Denmark": [
            {"year": 2022, "score": "1-0", "winner": "home", "tournament": "WC", "venue": "neutral"},
        ],
        "Serbia": [
            {"year": 2010, "score": "0-1", "winner": "away", "tournament": "WC", "venue": "neutral"},
        ],
    },

    "Nigeria": {
        "Argentina": [
            {"year": 2018, "score": "1-2", "winner": "away", "tournament": "WC", "venue": "neutral"},
            {"year": 2014, "score": "2-3", "winner": "away", "tournament": "WC", "venue": "neutral"},
        ],
        "Germany": [
            {"year": 1998, "score": "1-2", "winner": "away", "tournament": "WC", "venue": "neutral"},
        ],
        "France": [
            {"year": 2022, "score": "1-2", "winner": "away", "tournament": "WC", "venue": "neutral"},
        ],
        "Brazil": [
            {"year": 1998, "score": "0-1", "winner": "away", "tournament": "WC", "venue": "neutral"},
        ],
    },

    "Algeria": {
        "Germany": [
            {"year": 2014, "score": "1-2", "winner": "away", "tournament": "WC", "venue": "neutral"},
        ],
        "England": [
            {"year": 2010, "score": "0-0", "winner": "draw", "tournament": "WC", "venue": "neutral", "extra": True},
        ],
        "Russia": [
            {"year": 2014, "score": "1-1", "winner": "draw", "tournament": "WC", "venue": "neutral"},
        ],
        "Belgium": [
            {"year": 2014, "score": "2-1", "winner": "home", "tournament": "WC", "venue": "neutral"},
        ],
    },

    "Ivory Coast": {
        "Brazil": [
            {"year": 2010, "score": "1-3", "winner": "away", "tournament": "WC", "venue": "neutral"},
        ],
        "Argentina": [
            {"year": 2010, "score": "0-0", "winner": "draw", "tournament": "WC", "venue": "neutral"},
        ],
        "Portugal": [
            {"year": 2010, "score": "2-3", "winner": "away", "tournament": "WC", "venue": "neutral"},
        ],
    },

    "Chile": {
        "Brazil": [
            {"year": 2014, "score": "0-1", "winner": "away", "tournament": "WC", "venue": "neutral"},
            {"year": 2015, "score": "0-0", "winner": "draw", "tournament": "Copa America", "venue": "neutral", "penalties": True},
            {"year": 2016, "score": "0-0", "winner": "draw", "tournament": "Copa America", "venue": "neutral", "penalties": True},
        ],
        "Argentina": [
            {"year": 2015, "score": "0-0", "winner": "draw", "tournament": "Copa America", "venue": "neutral", "penalties": True},
            {"year": 2016, "score": "2-1", "winner": "home", "tournament": "Copa America", "venue": "neutral", "note": "决赛夺冠"},
        ],
        "Mexico": [
            {"year": 2010, "score": "1-0", "winner": "home", "tournament": "WC", "venue": "neutral"},
        ],
        "Spain": [
            {"year": 2010, "score": "1-2", "winner": "away", "tournament": "WC", "venue": "neutral"},
        ],
    },

    "Peru": {
        "Brazil": [
            {"year": 2018, "score": "0-2", "winner": "away", "tournament": "WC", "venue": "neutral"},
        ],
        "Argentina": [
            {"year": 2018, "score": "0-2", "winner": "away", "tournament": "WC", "venue": "neutral"},
            {"year": 2019, "score": "0-0", "winner": "draw", "tournament": "Copa America", "venue": "neutral"},
        ],
        "Denmark": [
            {"year": 2018, "score": "0-0", "winner": "draw", "tournament": "WC", "venue": "neutral"},
        ],
        "France": [
            {"year": 2018, "score": "0-0", "winner": "draw", "tournament": "WC", "venue": "neutral"},
        ],
    },

    "Ecuador": {
        "Brazil": [
            {"year": 2022, "score": "1-1", "winner": "draw", "tournament": "WC", "venue": "neutral"},
            {"year": 2014, "score": "0-1", "winner": "away", "tournament": "WC", "venue": "neutral"},
        ],
        "Argentina": [
            {"year": 2022, "score": "1-2", "winner": "away", "tournament": "WC", "venue": "neutral"},
        ],
        "France": [
            {"year": 2022, "score": "1-1", "winner": "draw", "tournament": "WC", "venue": "neutral"},
        ],
        "Netherlands": [
            {"year": 2022, "score": "1-1", "winner": "draw", "tournament": "WC", "venue": "neutral"},
        ],
        "Senegal": [
            {"year": 2022, "score": "1-2", "winner": "away", "tournament": "WC", "venue": "neutral"},
        ],
    },

    "Qatar": {
        "Ecuador": [
            {"year": 2022, "score": "0-2", "winner": "away", "tournament": "WC", "venue": "neutral", "note": "揭幕战"},
        ],
        "Netherlands": [
            {"year": 2022, "score": "0-2", "winner": "away", "tournament": "WC", "venue": "neutral"},
        ],
        "Senegal": [
            {"year": 2022, "score": "0-1", "winner": "away", "tournament": "WC", "venue": "neutral"},
        ],
    },

    "Canada": {
        "Belgium": [
            {"year": 2022, "score": "1-2", "winner": "away", "tournament": "WC", "venue": "neutral"},
        ],
        "Croatia": [
            {"year": 2022, "score": "1-4", "winner": "away", "tournament": "WC", "venue": "neutral"},
        ],
        "Morocco": [
            {"year": 2022, "score": "1-2", "winner": "away", "tournament": "WC", "venue": "neutral"},
        ],
    },

    "Costa Rica": {
        "Brazil": [
            {"year": 2022, "score": "0-1", "winner": "away", "tournament": "WC", "venue": "neutral"},
            {"year": 2018, "score": "0-1", "winner": "away", "tournament": "WC", "venue": "neutral"},
        ],
        "Germany": [
            {"year": 2022, "score": "2-4", "winner": "away", "tournament": "WC", "venue": "neutral"},
            {"year": 2006, "score": "1-4", "winner": "away", "tournament": "WC", "venue": "neutral"},
        ],
        "Spain": [
            {"year": 2022, "score": "0-7", "winner": "away", "tournament": "WC", "venue": "neutral", "note": "惨案"},
        ],
        "Uruguay": [
            {"year": 2014, "score": "0-1", "winner": "away", "tournament": "WC", "venue": "neutral"},
        ],
        "Netherlands": [
            {"year": 2014, "score": "0-0", "winner": "draw", "tournament": "WC", "venue": "neutral"},
        ],
    },

    "Panama": {
        "Belgium": [
            {"year": 2018, "score": "0-3", "winner": "away", "tournament": "WC", "venue": "neutral"},
        ],
        "England": [
            {"year": 2018, "score": "1-6", "winner": "away", "tournament": "WC", "venue": "neutral"},
        ],
        "Tunisia": [
            {"year": 2018, "score": "1-1", "winner": "draw", "tournament": "WC", "venue": "neutral"},
        ],
    },

    "Tunisia": {
        "France": [
            {"year": 2022, "score": "1-0", "winner": "home", "tournament": "WC", "venue": "neutral", "note": "冷门"},
            {"year": 2018, "score": "2-1", "winner": "home", "tournament": "WC", "venue": "neutral", "note": "冷门"},
        ],
        "Argentina": [
            {"year": 2002, "score": "1-2", "winner": "away", "tournament": "WC", "venue": "neutral"},
        ],
        "Croatia": [
            {"year": 2022, "score": "1-0", "winner": "home", "tournament": "WC", "venue": "neutral"},
        ],
        "Denmark": [
            {"year": 2022, "score": "0-0", "winner": "draw", "tournament": "WC", "venue": "neutral"},
        ],
        "Australia": [
            {"year": 2022, "score": "1-0", "winner": "home", "tournament": "WC", "venue": "neutral"},
        ],
    },

    "Morocco": {
        "Iran": [
            {"year": 2018, "score": "1-0", "winner": "home", "tournament": "WC", "venue": "neutral"},
        ],
        "Croatia": [
            {"year": 2022, "score": "0-0", "winner": "draw", "tournament": "WC", "venue": "neutral"},
            {"year": 2018, "score": "2-1", "winner": "home", "tournament": "WC", "venue": "neutral"},
        ],
        "Spain": [
            {"year": 2022, "score": "0-0", "winner": "draw", "tournament": "WC", "venue": "neutral", "penalties": True},
        ],
        "Belgium": [
            {"year": 2022, "score": "2-0", "winner": "home", "tournament": "WC", "venue": "neutral", "note": "冷门"},
            {"year": 2018, "score": "0-1", "winner": "away", "tournament": "WC", "venue": "neutral"},
        ],
    },

    "Austria": {
        "Germany": [
            {"year": 2024, "score": "0-2", "winner": "away", "tournament": "Euro", "venue": "neutral"},
            {"year": 2010, "score": "1-2", "winner": "away", "tournament": "WC", "venue": "neutral"},
        ],
        "Italy": [
            {"year": 2021, "score": "1-2", "winner": "away", "tournament": "Euro", "venue": "neutral", "extra": True},
        ],
        "Netherlands": [
            {"year": 2024, "score": "2-3", "winner": "away", "tournament": "Euro", "venue": "neutral"},
        ],
        "Turkey": [
            {"year": 2024, "score": "2-1", "winner": "home", "tournament": "Euro", "venue": "neutral"},
        ],
        "France": [
            {"year": 2024, "score": "0-1", "winner": "away", "tournament": "Euro", "venue": "neutral"},
        ],
        "Romania": [
            {"year": 2024, "score": "3-1", "winner": "home", "tournament": "Euro", "venue": "neutral"},
        ],
    },

    "Turkey": {
        "Italy": [
            {"year": 2020, "score": "0-3", "winner": "away", "tournament": "Euro", "venue": "neutral"},
            {"year": 2024, "score": "0-2", "winner": "away", "tournament": "Euro", "venue": "neutral"},
        ],
        "Portugal": [
            {"year": 2024, "score": "0-3", "winner": "away", "tournament": "Euro", "venue": "neutral"},
        ],
        "Netherlands": [
            {"year": 2024, "score": "0-2", "winner": "away", "tournament": "Euro", "venue": "neutral"},
        ],
        "Czech Republic": [
            {"year": 2008, "score": "3-2", "winner": "home", "tournament": "Euro", "venue": "neutral"},
        ],
        "Austria": [
            {"year": 2024, "score": "1-2", "winner": "away", "tournament": "Euro", "venue": "neutral"},
        ],
    },

    "Czech Republic": {
        "Netherlands": [
            {"year": 2020, "score": "2-0", "winner": "home", "tournament": "Euro", "venue": "neutral", "note": "冷门"},
        ],
        "Denmark": [
            {"year": 2000, "score": "0-1", "winner": "away", "tournament": "Euro", "venue": "neutral"},
        ],
        "Portugal": [
            {"year": 2008, "score": "1-3", "winner": "away", "tournament": "Euro", "venue": "neutral"},
        ],
        "Turkey": [
            {"year": 2008, "score": "2-3", "winner": "away", "tournament": "Euro", "venue": "neutral"},
        ],
        "Croatia": [
            {"year": 2016, "score": "2-2", "winner": "draw", "tournament": "Euro", "venue": "neutral"},
        ],
    },

    "Hungary": {
        "Germany": [
            {"year": 2022, "score": "1-1", "winner": "draw", "tournament": "WC", "venue": "neutral"},
            {"year": 2016, "score": "0-2", "winner": "away", "tournament": "Euro", "venue": "neutral"},
        ],
        "Portugal": [
            {"year": 2022, "score": "1-3", "winner": "away", "tournament": "WC", "venue": "neutral"},
            {"year": 2016, "score": "3-3", "winner": "draw", "tournament": "Euro", "venue": "neutral"},
        ],
        "France": [
            {"year": 2022, "score": "1-1", "winner": "draw", "tournament": "WC", "venue": "neutral"},
        ],
        "Iceland": [
            {"year": 2016, "score": "1-1", "winner": "draw", "tournament": "Euro", "venue": "neutral"},
        ],
        "Iceland": [
            {"year": 2016, "score": "1-1", "winner": "draw", "tournament": "Euro", "venue": "neutral"},
        ],
        "Italy": [
            {"year": 2021, "score": "0-3", "winner": "away", "tournament": "Euro", "venue": "neutral"},
        ],
    },

    "Romania": {
        "Spain": [
            {"year": 1994, "score": "1-2", "winner": "away", "tournament": "WC", "venue": "neutral"},
        ],
        "Argentina": [
            {"year": 1994, "score": "0-3", "winner": "away", "tournament": "WC", "venue": "neutral"},
        ],
        "Netherlands": [
            {"year": 1994, "score": "1-2", "winner": "away", "tournament": "WC", "venue": "neutral"},
        ],
        "France": [
            {"year": 1998, "score": "0-2", "winner": "away", "tournament": "WC", "venue": "neutral"},
        ],
        "Italy": [
            {"year": 1994, "score": "1-2", "winner": "away", "tournament": "WC", "venue": "neutral"},
        ],
    },

    "Ukraine": {
        "Netherlands": [
            {"year": 2006, "score": "0-1", "winner": "away", "tournament": "WC", "venue": "neutral"},
        ],
        "Italy": [
            {"year": 2006, "score": "0-3", "winner": "away", "tournament": "WC", "venue": "neutral"},
        ],
        "England": [
            {"year": 2012, "score": "0-1", "winner": "away", "tournament": "Euro", "venue": "neutral"},
        ],
        "Sweden": [
            {"year": 2012, "score": "1-2", "winner": "away", "tournament": "Euro", "venue": "neutral"},
        ],
    },

    "Slovakia": {
        "Spain": [
            {"year": 2010, "score": "0-1", "winner": "away", "tournament": "WC", "venue": "neutral"},
        ],
        "Netherlands": [
            {"year": 2010, "score": "1-2", "winner": "away", "tournament": "WC", "venue": "neutral"},
        ],
        "Italy": [
            {"year": 2016, "score": "0-2", "winner": "away", "tournament": "Euro", "venue": "neutral"},
        ],
        "England": [
            {"year": 2010, "score": "0-0", "winner": "draw", "tournament": "WC", "venue": "neutral"},
        ],
    },

    "Slovenia": {
        "England": [
            {"year": 2010, "score": "0-0", "winner": "draw", "tournament": "WC", "venue": "neutral", "extra": True},
        ],
        "Russia": [
            {"year": 2010, "score": "2-1", "winner": "home", "tournament": "WC", "venue": "neutral"},
        ],
        "Paraguay": [
            {"year": 2010, "score": "0-0", "winner": "draw", "tournament": "WC", "venue": "neutral"},
        ],
        "Denmark": [
            {"year": 2000, "score": "0-0", "winner": "draw", "tournament": "Euro", "venue": "neutral"},
        ],
    },

    "Paraguay": {
        "Spain": [
            {"year": 2010, "score": "0-2", "winner": "away", "tournament": "WC", "venue": "neutral"},
        ],
        "Italy": [
            {"year": 2010, "score": "1-1", "winner": "draw", "tournament": "WC", "venue": "neutral"},
        ],
        "New Zealand": [
            {"year": 2010, "score": "2-0", "winner": "home", "tournament": "WC", "venue": "neutral"},
        ],
        "Brazil": [
            {"year": 2010, "score": "0-2", "winner": "away", "tournament": "WC", "venue": "neutral"},
        ],
    },

    "New Zealand": {
        "Slovakia": [
            {"year": 2010, "score": "1-1", "winner": "draw", "tournament": "WC", "venue": "neutral"},
        ],
        "Italy": [
            {"year": 2010, "score": "1-1", "winner": "draw", "tournament": "WC", "venue": "neutral"},
        ],
        "Honduras": [
            {"year": 2010, "score": "0-0", "winner": "draw", "tournament": "WC", "venue": "neutral"},
        ],
    },

    "Honduras": {
        "Chile": [
            {"year": 2014, "score": "0-1", "winner": "away", "tournament": "WC", "venue": "neutral"},
        ],
        "France": [
            {"year": 2014, "score": "0-3", "winner": "away", "tournament": "WC", "venue": "neutral"},
        ],
        "Switzerland": [
            {"year": 2014, "score": "0-0", "winner": "draw", "tournament": "WC", "venue": "neutral"},
        ],
        "Ecuador": [
            {"year": 2014, "score": "1-2", "winner": "away", "tournament": "WC", "venue": "neutral"},
        ],
    },

    "Jamaica": {
        "Argentina": [
            {"year": 1998, "score": "0-5", "winner": "away", "tournament": "WC", "venue": "neutral"},
        ],
        "Croatia": [
            {"year": 1998, "score": "1-3", "winner": "away", "tournament": "WC", "venue": "neutral"},
        ],
        "France": [
            {"year": 1998, "score": "0-1", "winner": "away", "tournament": "WC", "venue": "neutral"},
        ],
    },

    "Trinidad and Tobago": {
        "Brazil": [
            {"year": 2006, "score": "0-1", "winner": "away", "tournament": "WC", "venue": "neutral"},
        ],
        "England": [
            {"year": 2006, "score": "0-0", "winner": "draw", "tournament": "WC", "venue": "neutral"},
        ],
        "Sweden": [
            {"year": 2006, "score": "0-0", "winner": "draw", "tournament": "WC", "venue": "neutral"},
        ],
    },

    "Greece": {
        "Germany": [
            {"year": 2014, "score": "1-1", "winner": "draw", "tournament": "WC", "venue": "neutral"},
            {"year": 2012, "score": "1-2", "winner": "away", "tournament": "Euro", "venue": "neutral"},
        ],
        "Nigeria": [
            {"year": 2014, "score": "2-1", "winner": "home", "tournament": "WC", "venue": "neutral"},
        ],
        "Colombia": [
            {"year": 2014, "score": "0-3", "winner": "away", "tournament": "WC", "venue": "neutral"},
        ],
        "Ivory Coast": [
            {"year": 2014, "score": "1-1", "winner": "draw", "tournament": "WC", "venue": "neutral", "penalties": True},
        ],
    },

    "Bolivia": {
        "Brazil": [
            {"year": 2019, "score": "1-3", "winner": "away", "tournament": "Copa America", "venue": "neutral"},
            {"year": 2015, "score": "0-3", "winner": "away", "tournament": "Copa America", "venue": "neutral"},
        ],
        "Argentina": [
            {"year": 2019, "score": "1-1", "winner": "draw", "tournament": "Copa America", "venue": "neutral"},
            {"year": 2015, "score": "0-2", "winner": "away", "tournament": "Copa America", "venue": "neutral"},
        ],
        "Peru": [
            {"year": 2019, "score": "1-3", "winner": "away", "tournament": "Copa America", "venue": "neutral"},
        ],
    },

    "Venezuela": {
        "Brazil": [
            {"year": 2019, "score": "0-0", "winner": "draw", "tournament": "Copa America", "venue": "neutral"},
            {"year": 2021, "score": "0-1", "winner": "away", "tournament": "Copa America", "venue": "neutral"},
        ],
        "Argentina": [
            {"year": 2019, "score": "0-1", "winner": "away", "tournament": "Copa America", "venue": "neutral"},
        ],
        "Colombia": [
            {"year": 2019, "score": "0-0", "winner": "draw", "tournament": "Copa America", "venue": "neutral"},
        ],
    },

    "Ecuador": {
        "Senegal": [
            {"year": 2022, "score": "1-2", "winner": "away", "tournament": "WC", "venue": "neutral"},
        ],
        "Netherlands": [
            {"year": 2022, "score": "1-1", "winner": "draw", "tournament": "WC", "venue": "neutral"},
        ],
        "Qatar": [
            {"year": 2022, "score": "2-0", "winner": "home", "tournament": "WC", "venue": "neutral"},
        ],
    },
}


class H2HDatabase:
    """
    H2H往绩数据库

    提供历史对战分析，包括：
    1. 总战绩统计
    2. 主场/客场战绩
    3. 大赛战绩
    4. 冷门/爆冷检测
    5. 近期趋势
    """

    def __init__(self):
        self.data = H2H_DATA

    def get_h2h(self, team1: str, team2: str) -> List[Dict]:
        """获取两队历史对战记录"""
        # 双向查找
        if team1 in self.data and team2 in self.data[team1]:
            return self.data[team1][team2]
        if team2 in self.data and team1 in self.data[team2]:
            # 反转主客场 - 交换比分，交换winner
            matches = []
            for m in self.data[team2][team1]:
                reversed_m = m.copy()
                # 交换比分（如0-1变成1-0）
                score = m["score"]
                parts = score.split("-")
                reversed_m["score"] = f"{parts[1]}-{parts[0]}"
                # 交换winner（因为主客队换了）
                if m["winner"] == "home":
                    reversed_m["winner"] = "away"
                elif m["winner"] == "away":
                    reversed_m["winner"] = "home"
                matches.append(reversed_m)
            return matches
        return []

    def get_h2h_stats(self, team1: str, team2: str) -> Dict:
        """获取两队对战统计"""
        matches = self.get_h2h(team1, team2)

        if not matches:
            return {
                "total": 0,
                "team1_wins": 0,
                "team2_wins": 0,
                "draws": 0,
                "team1_win_rate": 0.5,
                "notes": []
            }

        team1_wins = sum(1 for m in matches if m["winner"] == "home")
        team2_wins = sum(1 for m in matches if m["winner"] == "away")
        draws = sum(1 for m in matches if m["winner"] == "draw")

        notes = [m.get("note", "") for m in matches if m.get("note")]

        return {
            "total": len(matches),
            "team1_wins": team1_wins,
            "team2_wins": team2_wins,
            "draws": draws,
            "team1_win_rate": team1_wins / len(matches) if matches else 0.5,
            "notes": notes,
            "recent_winner": matches[-1]["winner"] if matches else None,
            "has_upsets": any(m.get("note") and "冷" in m.get("note", "") or "爆" in m.get("note", "") for m in matches)
        }

    def has_upset_history(self, team1: str, team2: str) -> bool:
        """检查是否有爆冷历史"""
        matches = self.get_h2h(team1, team2)
        for m in matches:
            if m.get("note") and ("冷" in m["note"] or "爆" in m["note"]):
                return True
        return False

    def get_recent_trend(self, team1: str, team2: str, n: int = 3) -> str:
        """获取近期趋势"""
        matches = self.get_h2h(team1, team2)
        if not matches:
            return "unknown"

        recent = matches[-n:] if len(matches) >= n else matches

        team1_recent_wins = sum(1 for m in recent if m["winner"] == "home")
        team2_recent_wins = sum(1 for m in recent if m["winner"] == "away")

        if team1_recent_wins > team2_recent_wins:
            return "team1_dominant"
        elif team2_recent_wins > team1_recent_wins:
            return "team2_dominant"
        else:
            return "balanced"

    def get_big_tournament_record(self, team1: str, team2: str) -> Dict:
        """获取大赛对战记录（世界杯/欧洲杯等）"""
        matches = self.get_h2h(team1, team2)

        wc_matches = [m for m in matches if m.get("tournament") in ["WC", "Euro", "Copa America"]]
        if not wc_matches:
            return {"has_record": False, "stats": None}

        team1_wins = sum(1 for m in wc_matches if m["winner"] == "home")
        team2_wins = sum(1 for m in wc_matches if m["winner"] == "away")

        return {
            "has_record": True,
            "stats": {
                "total": len(wc_matches),
                "team1_wins": team1_wins,
                "team2_wins": team2_wins,
                "team1_win_rate": team1_wins / len(wc_matches)
            }
        }

    def get_h2h_factor(self, team1: str, team2: str) -> float:
        """
        计算H2H因子（用于预测调整）

        返回值：
        > 0: 对team1有利
        < 0: 对team2有利
        = 0: 无明显倾向
        """
        stats = self.get_h2h_stats(team1, team2)

        if stats["total"] == 0:
            return 0.0

        # 基础因子：胜率差异
        base_factor = (stats["team1_win_rate"] - 0.5) * 0.5

        # 近期趋势加权（最近3场权重更高）
        trend = self.get_recent_trend(team1, team2)
        trend_factor = 0
        if trend == "team1_dominant":
            trend_factor = 0.15
        elif trend == "team2_dominant":
            trend_factor = -0.15

        # 爆冷惩罚（如果team1近期被爆冷，减少其优势）
        upset_factor = 0
        if stats.get("has_upsets"):
            recent_matches = self.get_h2h(team1, team2)[-3:]
            for m in recent_matches:
                if m.get("note") and ("冷" in m["note"] or "爆" in m["note"]) and m["winner"] == "away":
                    upset_factor = -0.1

        return base_factor + trend_factor + upset_factor

    def save_to_file(self, filepath: str = None):
        """保存H2H数据到文件"""
        if filepath is None:
            filepath = os.path.join(DATA_DIR, "h2h_database.json")

        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        with open(filepath, 'w') as f:
            json.dump({
                "data": self.data,
                "last_updated": datetime.now().isoformat(),
                "version": "1.0"
            }, f, ensure_ascii=False, indent=2)

        print(f"✅ H2H数据已保存: {filepath}")


# ============ 测试 ============
if __name__ == "__main__":
    h2h = H2HDatabase()

    print("=" * 60)
    print("📊 H2H往绩数据库测试")
    print("=" * 60)

    # 测试几个经典对阵
    test_pairs = [
        ("Germany", "South Korea"),
        ("Argentina", "Brazil"),
        ("Japan", "Germany"),
        ("Morocco", "Portugal"),
        ("England", "Iceland"),
    ]

    for team1, team2 in test_pairs:
        print(f"\n⚽ {team1} vs {team2}")
        matches = h2h.get_h2h(team1, team2)
        if matches:
            stats = h2h.get_h2h_stats(team1, team2)
            print(f"   总场次: {stats['total']}")
            print(f"   {team1}胜: {stats['team1_wins']}, 平: {stats['draws']}, {team2}胜: {stats['team2_wins']}")
            print(f"   {team1}胜率: {stats['team1_win_rate']:.1%}")
            if stats['notes']:
                print(f"   关键记录: {', '.join(stats['notes'])}")
            print(f"   H2H因子: {h2h.get_h2h_factor(team1, team2):+.2f}")
        else:
            print("   无历史对战记录")

    # 保存数据
    print("\n" + "=" * 60)
    h2h.save_to_file()

    print(f"\n总计收录 {sum(len(v) for v in h2h.data.values())} 组对战数据")
