#!/usr/bin/env python3
"""
多赛事数据收集器 v1.0
========================
收集和整理各类足球赛事的历史数据

赛事范围：
- 世界杯
- 欧洲杯
- 欧洲预选赛
- 南美世预赛
- 亚洲预选赛
- 非洲杯
- 联合会杯
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Optional

# ============ 路径配置 ============
BASE_DIR = os.path.expanduser("~/hermes-world-cup/")
DATA_DIR = os.path.join(BASE_DIR, "data/")


# ============ 世界杯数据 (2010-2026) ============
WORLD_CUP_DATA = [
    # ========== 2022世界杯 ==========
    # 决赛
    {"home": "Argentina", "away": "France", "score": "2-2", "year": 2022, "stage": "final", "tournament": "wc", "penalties": True},
    # 半决赛
    {"home": "France", "away": "Morocco", "score": "2-0", "year": 2022, "stage": "semi", "tournament": "wc"},
    {"home": "Argentina", "away": "Croatia", "score": "3-0", "year": 2022, "stage": "semi", "tournament": "wc"},
    # 8强
    {"home": "Morocco", "away": "Portugal", "score": "1-0", "year": 2022, "stage": "quarter", "tournament": "wc"},
    {"home": "England", "away": "France", "score": "1-2", "year": 2022, "stage": "quarter", "tournament": "wc"},
    {"home": "Netherlands", "away": "Argentina", "score": "2-2", "year": 2022, "stage": "quarter", "tournament": "wc", "penalties": True},
    {"home": "Brazil", "away": "Croatia", "score": "1-1", "year": 2022, "stage": "quarter", "tournament": "wc", "extra": True},
    {"home": "Portugal", "away": "Switzerland", "score": "6-1", "year": 2022, "stage": "quarter", "tournament": "wc"},
    # 16强
    {"home": "Spain", "away": "Germany", "score": "1-2", "year": 2022, "stage": "round16", "tournament": "wc"},
    {"home": "Brazil", "away": "South Korea", "score": "4-1", "year": 2022, "stage": "round16", "tournament": "wc"},
    {"home": "Netherlands", "away": "USA", "score": "3-1", "year": 2022, "stage": "round16", "tournament": "wc"},
    {"home": "Argentina", "away": "Australia", "score": "2-1", "year": 2022, "stage": "round16", "tournament": "wc"},
    {"home": "France", "away": "Poland", "score": "3-1", "year": 2022, "stage": "round16", "tournament": "wc"},
    {"home": "England", "away": "Senegal", "score": "3-0", "year": 2022, "stage": "round16", "tournament": "wc"},
    {"home": "Croatia", "away": "Japan", "score": "1-1", "year": 2022, "stage": "round16", "tournament": "wc", "penalties": True},
    {"home": "Morocco", "away": "Spain", "score": "0-0", "year": 2022, "stage": "round16", "tournament": "wc", "penalties": True},
    # 小组赛
    {"home": "Germany", "away": "Japan", "score": "1-2", "year": 2022, "stage": "group", "tournament": "wc", "upset": True},
    {"home": "Argentina", "away": "Saudi Arabia", "score": "1-2", "year": 2022, "stage": "group", "tournament": "wc", "upset": True},
    {"home": "Brazil", "away": "Serbia", "score": "2-0", "year": 2022, "stage": "group", "tournament": "wc"},
    {"home": "France", "away": "Denmark", "score": "2-1", "year": 2022, "stage": "group", "tournament": "wc"},
    {"home": "Spain", "away": "Costa Rica", "score": "7-0", "year": 2022, "stage": "group", "tournament": "wc"},
    {"home": "Germany", "away": "Spain", "score": "1-1", "year": 2022, "stage": "group", "tournament": "wc"},
    {"home": "England", "away": "Iran", "score": "6-2", "year": 2022, "stage": "group", "tournament": "wc"},
    {"home": "Portugal", "away": "Uruguay", "score": "2-0", "year": 2022, "stage": "group", "tournament": "wc"},
    {"home": "Brazil", "away": "Switzerland", "score": "1-1", "year": 2022, "stage": "group", "tournament": "wc"},
    {"home": "South Korea", "away": "Portugal", "score": "2-1", "year": 2022, "stage": "group", "tournament": "wc", "stoppage": True},
    {"home": "Wales", "away": "England", "score": "0-3", "year": 2022, "stage": "group", "tournament": "wc"},
    {"home": "Australia", "away": "Denmark", "score": "1-0", "year": 2022, "stage": "group", "tournament": "wc"},
    {"home": "Ecuador", "away": "Senegal", "score": "1-2", "year": 2022, "stage": "group", "tournament": "wc"},
    {"home": "Japan", "away": "Spain", "score": "2-1", "year": 2022, "stage": "group", "tournament": "wc"},
    {"home": "Canada", "away": "Morocco", "score": "1-2", "year": 2022, "stage": "group", "tournament": "wc"},
    {"home": "Croatia", "away": "Belgium", "score": "0-0", "year": 2022, "stage": "group", "tournament": "wc"},
    {"home": "Germany", "away": "Costa Rica", "score": "4-2", "year": 2022, "stage": "group", "tournament": "wc"},
    {"home": "Korea", "away": "Haiti", "score": "0-0", "year": 2022, "stage": "group", "tournament": "wc"},
    {"home": "Serbia", "away": "Cameroon", "score": "3-3", "year": 2022, "stage": "group", "tournament": "wc"},
    {"home": "Netherlands", "away": "Ecuador", "score": "1-1", "year": 2022, "stage": "group", "tournament": "wc"},
    {"home": "England", "away": "USA", "score": "0-0", "year": 2022, "stage": "group", "tournament": "wc"},
    {"home": "Qatar", "away": "Ecuador", "score": "0-2", "year": 2022, "stage": "group", "tournament": "wc"},
    {"home": "Saudi Arabia", "away": "Poland", "score": "2-0", "year": 2022, "stage": "group", "tournament": "wc"},
    {"home": "France", "away": "Australia", "score": "4-1", "year": 2022, "stage": "group", "tournament": "wc"},
    {"home": "Argentina", "away": "Mexico", "score": "2-0", "year": 2022, "stage": "group", "tournament": "wc"},
    {"home": "Belgium", "away": "Canada", "score": "2-1", "year": 2022, "stage": "group", "tournament": "wc"},
    {"home": "Croatia", "away": "Denmark", "score": "0-0", "year": 2022, "stage": "group", "tournament": "wc"},
    {"home": "Spain", "away": "Germany", "score": "1-2", "year": 2022, "stage": "group", "tournament": "wc", "upset": True},

    # ========== 2018世界杯 ==========
    {"home": "France", "away": "Croatia", "score": "4-2", "year": 2018, "stage": "final", "tournament": "wc"},
    {"home": "Belgium", "away": "France", "score": "0-1", "year": 2018, "stage": "semi", "tournament": "wc"},
    {"home": "England", "away": "Croatia", "score": "1-2", "year": 2018, "stage": "semi", "tournament": "wc", "extra": True},
    {"home": "Uruguay", "away": "France", "score": "0-2", "year": 2018, "stage": "quarter", "tournament": "wc"},
    {"home": "Brazil", "away": "Belgium", "score": "2-1", "year": 2018, "stage": "quarter", "tournament": "wc"},
    {"home": "Sweden", "away": "England", "score": "0-2", "year": 2018, "stage": "quarter", "tournament": "wc"},
    {"home": "Russia", "away": "Croatia", "score": "1-1", "year": 2018, "stage": "quarter", "tournament": "wc", "penalties": True},
    {"home": "France", "away": "Argentina", "score": "4-3", "year": 2018, "stage": "round16", "tournament": "wc"},
    {"home": "Uruguay", "away": "Portugal", "score": "2-1", "year": 2018, "stage": "round16", "tournament": "wc"},
    {"home": "Spain", "away": "Russia", "score": "1-1", "year": 2018, "stage": "round16", "tournament": "wc", "penalties": True},
    {"home": "Denmark", "away": "Croatia", "score": "1-1", "year": 2018, "stage": "round16", "tournament": "wc", "penalties": True},
    {"home": "Mexico", "away": "Brazil", "score": "0-2", "year": 2018, "stage": "round16", "tournament": "wc"},
    {"home": "Japan", "away": "Belgium", "score": "2-3", "year": 2018, "stage": "round16", "tournament": "wc", "stoppage": True},
    {"home": "Sweden", "away": "Switzerland", "score": "1-0", "year": 2018, "stage": "round16", "tournament": "wc"},
    {"home": "Colombia", "away": "England", "score": "1-1", "year": 2018, "stage": "round16", "tournament": "wc", "penalties": True},
    # 小组赛
    {"home": "Germany", "away": "Mexico", "score": "0-1", "year": 2018, "stage": "group", "tournament": "wc", "upset": True},
    {"home": "Germany", "away": "South Korea", "score": "0-2", "year": 2018, "stage": "group", "tournament": "wc", "upset": True},
    {"home": "Brazil", "away": "Switzerland", "score": "1-1", "year": 2018, "stage": "group", "tournament": "wc"},
    {"home": "Argentina", "away": "Iceland", "score": "1-1", "year": 2018, "stage": "group", "tournament": "wc"},
    {"home": "Brazil", "away": "Costa Rica", "score": "2-0", "year": 2018, "stage": "group", "tournament": "wc"},
    {"home": "Germany", "away": "Sweden", "score": "2-1", "year": 2018, "stage": "group", "tournament": "wc"},
    {"home": "England", "away": "Panama", "score": "6-1", "year": 2018, "stage": "group", "tournament": "wc"},
    {"home": "Belgium", "away": "Japan", "score": "3-2", "year": 2018, "stage": "group", "tournament": "wc", "upset": True},
    {"home": "Poland", "away": "Colombia", "score": "0-3", "year": 2018, "stage": "group", "tournament": "wc"},
    {"home": "Russia", "away": "Saudi Arabia", "score": "5-0", "year": 2018, "stage": "group", "tournament": "wc"},
    {"home": "Uruguay", "away": "Russia", "score": "3-0", "year": 2018, "stage": "group", "tournament": "wc"},
    {"home": "Portugal", "away": "Iran", "score": "1-1", "year": 2018, "stage": "group", "tournament": "wc"},
    {"home": "Denmark", "away": "Australia", "score": "1-1", "year": 2018, "stage": "group", "tournament": "wc"},
    {"home": "France", "away": "Denmark", "score": "0-0", "year": 2018, "stage": "group", "tournament": "wc"},
    {"home": "Argentina", "away": "Croatia", "score": "0-3", "year": 2018, "stage": "group", "tournament": "wc", "upset": True},

    # ========== 2014世界杯 ==========
    {"home": "Germany", "away": "Argentina", "score": "1-0", "year": 2014, "stage": "final", "tournament": "wc"},
    {"home": "Brazil", "away": "Germany", "score": "1-7", "year": 2014, "stage": "semi", "tournament": "wc", "upset": True},
    {"home": "Netherlands", "away": "Brazil", "score": "0-0", "year": 2014, "stage": "semi", "tournament": "wc", "penalties": True},
    {"home": "Brazil", "away": "Netherlands", "score": "0-3", "year": 2014, "stage": "third_place", "tournament": "wc"},
    {"home": "Germany", "away": "France", "score": "1-0", "year": 2014, "stage": "quarter", "tournament": "wc"},
    {"home": "Brazil", "away": "Colombia", "score": "2-1", "year": 2014, "stage": "quarter", "tournament": "wc"},
    {"home": "France", "away": "Germany", "score": "0-1", "year": 2014, "stage": "quarter", "tournament": "wc"},
    {"home": "Belgium", "away": "Argentina", "score": "0-1", "year": 2014, "stage": "quarter", "tournament": "wc"},
    {"home": "Germany", "away": "Algeria", "score": "2-1", "year": 2014, "stage": "round16", "tournament": "wc", "extra": True},
    {"home": "Belgium", "away": "USA", "score": "2-1", "year": 2014, "stage": "round16", "tournament": "wc", "extra": True},
    {"home": "Argentina", "away": "Switzerland", "score": "1-0", "year": 2014, "stage": "round16", "tournament": "wc", "extra": True},
    {"home": "France", "away": "Nigeria", "score": "2-0", "year": 2014, "stage": "round16", "tournament": "wc"},
    {"home": "Brazil", "away": "Chile", "score": "1-1", "year": 2014, "stage": "round16", "tournament": "wc", "penalties": True},
    {"home": "Netherlands", "away": "Mexico", "score": "2-1", "year": 2014, "stage": "round16", "tournament": "wc", "extra": True},
    {"home": "Colombia", "away": "Uruguay", "score": "2-0", "year": 2014, "stage": "round16", "tournament": "wc"},
    {"home": "Germany", "away": "Ghana", "score": "2-2", "year": 2014, "stage": "group", "tournament": "wc"},
    {"home": "Germany", "away": "Portugal", "score": "4-0", "year": 2014, "stage": "group", "tournament": "wc"},
    {"home": "Germany", "away": "USA", "score": "1-0", "year": 2014, "stage": "group", "tournament": "wc"},
    {"home": "Brazil", "away": "Croatia", "score": "3-1", "year": 2014, "stage": "group", "tournament": "wc"},
    {"home": "Spain", "away": "Netherlands", "score": "1-5", "year": 2014, "stage": "group", "tournament": "wc", "upset": True},
    {"home": "Chile", "away": "Netherlands", "score": "0-2", "year": 2014, "stage": "group", "tournament": "wc"},
    {"home": "Australia", "away": "Japan", "score": "1-3", "year": 2014, "stage": "group", "tournament": "wc"},
    {"home": "Argentina", "away": "Bosnia", "score": "2-1", "year": 2014, "stage": "group", "tournament": "wc"},
    {"home": "France", "away": "Honduras", "score": "6-0", "year": 2014, "stage": "group", "tournament": "wc"},
    {"home": "Italy", "away": "England", "score": "2-1", "year": 2014, "stage": "group", "tournament": "wc"},
    {"home": "Colombia", "away": "Greece", "score": "3-0", "year": 2014, "stage": "group", "tournament": "wc"},
    {"home": "England", "away": "Italy", "score": "1-2", "year": 2014, "stage": "group", "tournament": "wc"},
    {"home": "Uruguay", "away": "Costa Rica", "score": "1-0", "year": 2014, "stage": "group", "tournament": "wc"},
    {"home": "Italy", "away": "Costa Rica", "score": "0-1", "year": 2014, "stage": "group", "tournament": "wc", "upset": True},
    {"home": "England", "away": "Uruguay", "score": "1-2", "year": 2014, "stage": "group", "tournament": "wc"},
    {"home": "Japan", "away": "Poland", "score": "0-1", "year": 2014, "stage": "group", "tournament": "wc"},
    {"home": "Belgium", "away": "Russia", "score": "1-0", "year": 2014, "stage": "group", "tournament": "wc"},
    {"home": "South Korea", "away": "Algeria", "score": "2-4", "year": 2014, "stage": "group", "tournament": "wc", "upset": True},

    # ========== 2010世界杯 ==========
    {"home": "Spain", "away": "Netherlands", "score": "1-0", "year": 2010, "stage": "final", "tournament": "wc"},
    {"home": "Germany", "away": "Spain", "score": "0-1", "year": 2010, "stage": "semi", "tournament": "wc"},
    {"home": "Netherlands", "away": "Uruguay", "score": "3-2", "year": 2010, "stage": "semi", "tournament": "wc"},
    {"home": "Germany", "away": "Uruguay", "score": "2-3", "year": 2010, "stage": "third_place", "tournament": "wc"},
    {"home": "Spain", "away": "Germany", "score": "1-0", "year": 2010, "stage": "semi", "tournament": "wc"},
    {"home": "Netherlands", "away": "Brazil", "score": "2-1", "year": 2010, "stage": "quarter", "tournament": "wc"},
    {"home": "Spain", "away": "Paraguay", "score": "1-0", "year": 2010, "stage": "quarter", "tournament": "wc"},
    {"home": "Argentina", "away": "Germany", "score": "0-4", "year": 2010, "stage": "quarter", "tournament": "wc", "upset": True},
    {"home": "England", "away": "Germany", "score": "1-4", "year": 2010, "stage": "round16", "tournament": "wc"},
    {"home": "Netherlands", "away": "Slovakia", "score": "2-1", "year": 2010, "stage": "round16", "tournament": "wc"},
    {"home": "Brazil", "away": "Chile", "score": "3-0", "year": 2010, "stage": "round16", "tournament": "wc"},
    {"home": "Spain", "away": "Portugal", "score": "1-0", "year": 2010, "stage": "round16", "tournament": "wc"},
    {"home": "Germany", "away": "England", "score": "4-1", "year": 2010, "stage": "round16", "tournament": "wc"},
    {"home": "Argentina", "away": "Mexico", "score": "3-1", "year": 2010, "stage": "round16", "tournament": "wc"},
    {"home": "Uruguay", "away": "South Korea", "score": "2-0", "year": 2010, "stage": "round16", "tournament": "wc"},
    {"home": "Paraguay", "away": "Japan", "score": "5-3", "year": 2010, "stage": "round16", "tournament": "wc", "penalties": True},
]


# ============ 欧洲杯数据 (2016-2024) ============
EURO_DATA = [
    # ========== 2024欧洲杯 ==========
    {"home": "Spain", "away": "England", "score": "2-1", "year": 2024, "stage": "final", "tournament": "euro"},
    {"home": "Spain", "away": "France", "score": "2-1", "year": 2024, "stage": "semi", "tournament": "euro"},
    {"home": "England", "away": "Netherlands", "score": "2-1", "year": 2024, "stage": "semi", "tournament": "euro"},
    {"home": "Portugal", "away": "France", "score": "0-0", "year": 2024, "stage": "quarter", "tournament": "euro", "penalties": True},
    {"home": "Spain", "away": "Germany", "score": "2-1", "year": 2024, "stage": "quarter", "tournament": "euro", "extra": True},
    {"home": "England", "away": "Switzerland", "score": "1-1", "year": 2024, "stage": "quarter", "tournament": "euro", "penalties": True},
    {"home": "Netherlands", "away": "Turkey", "score": "2-1", "year": 2024, "stage": "quarter", "tournament": "euro"},
    {"home": "Portugal", "away": "Slovenia", "score": "0-0", "year": 2024, "stage": "round16", "tournament": "euro", "penalties": True},
    {"home": "France", "away": "Belgium", "score": "1-0", "year": 2024, "stage": "round16", "tournament": "euro"},
    {"home": "Spain", "away": "Georgia", "score": "4-1", "year": 2024, "stage": "round16", "tournament": "euro"},
    {"home": "Germany", "away": "Denmark", "score": "2-0", "year": 2024, "stage": "round16", "tournament": "euro"},
    {"home": "England", "away": "Slovakia", "score": "2-1", "year": 2024, "stage": "round16", "tournament": "euro", "extra": True},
    {"home": "Italy", "away": "Switzerland", "score": "0-2", "year": 2024, "stage": "round16", "tournament": "euro"},
    {"home": "Netherlands", "away": "Romania", "score": "3-0", "year": 2024, "stage": "round16", "tournament": "euro"},
    {"home": "Austria", "away": "Turkey", "score": "1-2", "year": 2024, "stage": "round16", "tournament": "euro"},
    {"home": "Romania", "away": "Netherlands", "score": "0-3", "year": 2024, "stage": "group", "tournament": "euro"},
    {"home": "Spain", "away": "Italy", "score": "1-0", "year": 2024, "stage": "group", "tournament": "euro"},
    {"home": "Germany", "away": "Hungary", "score": "2-0", "year": 2024, "stage": "group", "tournament": "euro"},
    {"home": "England", "away": "Denmark", "score": "1-1", "year": 2024, "stage": "group", "tournament": "euro"},
    {"home": "Portugal", "away": "Czech Republic", "score": "2-1", "year": 2024, "stage": "group", "tournament": "euro"},
    {"home": "France", "away": "Austria", "score": "1-0", "year": 2024, "stage": "group", "tournament": "euro"},
    {"home": "Netherlands", "away": "France", "score": "0-0", "year": 2024, "stage": "group", "tournament": "euro"},
    {"home": "Germany", "away": "Scotland", "score": "5-1", "year": 2024, "stage": "group", "tournament": "euro"},
    {"home": "Spain", "away": "Croatia", "score": "3-0", "year": 2024, "stage": "group", "tournament": "euro"},
    {"home": "Italy", "away": "Albania", "score": "2-1", "year": 2024, "stage": "group", "tournament": "euro"},
    {"home": "Denmark", "away": "Serbia", "score": "0-0", "year": 2024, "stage": "group", "tournament": "euro"},
    {"home": "England", "away": "Serbia", "score": "1-0", "year": 2024, "stage": "group", "tournament": "euro"},
    {"home": "Slovenia", "away": "Denmark", "score": "1-1", "year": 2024, "stage": "group", "tournament": "euro"},
    {"home": "Portugal", "away": "Turkey", "score": "3-0", "year": 2024, "stage": "group", "tournament": "euro"},
    {"home": "Georgia", "away": "Czech Republic", "score": "1-1", "year": 2024, "stage": "group", "tournament": "euro"},

    # ========== 2020欧洲杯 ==========
    {"home": "Italy", "away": "England", "score": "1-1", "year": 2020, "stage": "final", "tournament": "euro", "penalties": True},
    {"home": "Italy", "away": "Spain", "score": "1-1", "year": 2020, "stage": "semi", "tournament": "euro", "penalties": True},
    {"home": "England", "away": "Denmark", "score": "2-1", "year": 2020, "stage": "semi", "tournament": "euro", "extra": True},
    {"home": "Spain", "away": "Italy", "score": "1-1", "year": 2020, "stage": "semi", "tournament": "euro", "penalties": True},
    {"home": "Italy", "away": "Austria", "score": "2-1", "year": 2020, "stage": "round16", "tournament": "euro", "extra": True},
    {"home": "England", "away": "Germany", "score": "2-0", "year": 2020, "stage": "round16", "tournament": "euro"},
    {"home": "France", "away": "Switzerland", "score": "3-3", "year": 2020, "stage": "round16", "tournament": "euro", "penalties": True, "upset": True},
    {"home": "Portugal", "away": "Belgium", "score": "0-1", "year": 2020, "stage": "round16", "tournament": "euro", "upset": True},
    {"home": "Germany", "away": "Hungary", "score": "2-2", "year": 2020, "stage": "group", "tournament": "euro"},
    {"home": "France", "away": "Germany", "score": "1-0", "year": 2020, "stage": "group", "tournament": "euro"},
    {"home": "England", "away": "Croatia", "score": "0-1", "year": 2020, "stage": "group", "tournament": "euro"},
    {"home": "Netherlands", "away": "Czech Republic", "score": "0-2", "year": 2020, "stage": "round16", "tournament": "euro", "upset": True},
    {"home": "Belgium", "away": "Italy", "score": "1-2", "year": 2020, "stage": "quarter", "tournament": "euro"},
    {"home": "Spain", "away": "Switzerland", "score": "1-1", "year": 2020, "stage": "quarter", "tournament": "euro", "penalties": True},
    {"home": "Italy", "away": "Belgium", "score": "2-1", "year": 2020, "stage": "quarter", "tournament": "euro"},
    {"home": "Czech Republic", "away": "Denmark", "score": "1-2", "year": 2020, "stage": "quarter", "tournament": "euro"},

    # ========== 2016欧洲杯 ==========
    {"home": "Portugal", "away": "France", "score": "1-0", "year": 2016, "stage": "final", "tournament": "euro"},
    {"home": "Portugal", "away": "Wales", "score": "2-0", "year": 2016, "stage": "semi", "tournament": "euro"},
    {"home": "France", "away": "Germany", "score": "2-0", "year": 2016, "stage": "semi", "tournament": "euro"},
    {"home": "Wales", "away": "Belgium", "score": "3-1", "year": 2016, "stage": "quarter", "tournament": "euro"},
    {"home": "Portugal", "away": "Poland", "score": "1-1", "year": 2016, "stage": "quarter", "tournament": "euro", "penalties": True},
    {"home": "Germany", "away": "Italy", "score": "1-1", "year": 2016, "stage": "quarter", "tournament": "euro", "penalties": True},
    {"home": "France", "away": "Iceland", "score": "5-2", "year": 2016, "stage": "quarter", "tournament": "euro"},
    {"home": "Belgium", "away": "Italy", "score": "0-2", "year": 2016, "stage": "round16", "tournament": "euro", "upset": True},
    {"home": "France", "away": "Republic of Ireland", "score": "2-1", "year": 2016, "stage": "round16", "tournament": "euro"},
    {"home": "Germany", "away": "Slovakia", "score": "3-0", "year": 2016, "stage": "round16", "tournament": "euro"},
    {"home": "Hungary", "away": "Belgium", "score": "0-4", "year": 2016, "stage": "round16", "tournament": "euro"},
    {"home": "Italy", "away": "Spain", "score": "2-0", "year": 2016, "stage": "round16", "tournament": "euro"},
    {"home": "England", "away": "Iceland", "score": "1-2", "year": 2016, "stage": "round16", "tournament": "euro", "upset": True},
    {"home": "Portugal", "away": "Croatia", "score": "1-0", "year": 2016, "stage": "round16", "tournament": "euro", "extra": True},
    {"home": "Wales", "away": "Northern Ireland", "score": "1-0", "year": 2016, "stage": "round16", "tournament": "euro"},
    {"home": "Spain", "away": "Turkey", "score": "3-0", "year": 2016, "stage": "group", "tournament": "euro"},
    {"home": "Germany", "away": "Ukraine", "score": "2-0", "year": 2016, "stage": "group", "tournament": "euro"},
    {"home": "Poland", "away": "Northern Ireland", "score": "1-0", "year": 2016, "stage": "group", "tournament": "euro"},
    {"home": "Spain", "away": "Italy", "score": "1-1", "year": 2016, "stage": "group", "tournament": "euro"},
    {"home": "Belgium", "away": "Italy", "score": "0-2", "year": 2016, "stage": "group", "tournament": "euro", "upset": True},
    {"home": "Portugal", "away": "Iceland", "score": "1-1", "year": 2016, "stage": "group", "tournament": "euro"},
    {"home": "France", "away": "Romania", "score": "2-1", "year": 2016, "stage": "group", "tournament": "euro"},
    {"home": "England", "away": "Russia", "score": "1-1", "year": 2016, "stage": "group", "tournament": "euro"},
    {"home": "Germany", "away": "Poland", "score": "0-0", "year": 2016, "stage": "group", "tournament": "euro"},
    {"home": "Italy", "away": "Belgium", "score": "2-0", "year": 2016, "stage": "group", "tournament": "euro"},
    {"home": "Iceland", "away": "Austria", "score": "2-1", "year": 2016, "stage": "group", "tournament": "euro"},
    {"home": "Portugal", "away": "Austria", "score": "3-3", "year": 2016, "stage": "group", "tournament": "euro"},
    {"home": "Hungary", "away": "Iceland", "score": "1-1", "year": 2016, "stage": "group", "tournament": "euro"},
]


# ============ 欧洲预选赛数据 ============
EURO_QUALIFIERS = [
    # 2024欧洲杯预选赛
    {"home": "Spain", "away": "Scotland", "score": "2-0", "year": 2023, "stage": "qualifier", "tournament": "eq"},
    {"home": "Germany", "away": "Turkey", "score": "2-1", "year": 2023, "stage": "qualifier", "tournament": "eq"},
    {"home": "England", "away": "Italy", "score": "3-1", "year": 2023, "stage": "qualifier", "tournament": "eq"},
    {"home": "France", "away": "Greece", "score": "1-0", "year": 2023, "stage": "qualifier", "tournament": "eq"},
    {"home": "Italy", "away": "Ukraine", "score": "2-1", "year": 2023, "stage": "qualifier", "tournament": "eq"},
    {"home": "Portugal", "away": "Luxembourg", "score": "6-0", "year": 2023, "stage": "qualifier", "tournament": "eq"},
    {"home": "Netherlands", "away": "Greece", "score": "3-0", "year": 2023, "stage": "qualifier", "tournament": "eq"},
    {"home": "Croatia", "away": "Turkey", "score": "2-0", "year": 2023, "stage": "qualifier", "tournament": "eq"},
    {"home": "Belgium", "away": "Austria", "score": "1-1", "year": 2023, "stage": "qualifier", "tournament": "eq"},
    {"home": "Serbia", "away": "Hungary", "score": "1-2", "year": 2023, "stage": "qualifier", "tournament": "eq", "upset": True},
    {"home": "Wales", "away": "Armenia", "score": "2-1", "year": 2023, "stage": "qualifier", "tournament": "eq"},
    {"home": "Scotland", "away": "Georgia", "score": "2-0", "year": 2023, "stage": "qualifier", "tournament": "eq"},

    # 2022世界杯欧洲预选赛
    {"home": "England", "away": "San Marino", "score": "10-0", "year": 2021, "stage": "qualifier", "tournament": "wq"},
    {"home": "Germany", "away": "North Macedonia", "score": "4-0", "year": 2021, "stage": "qualifier", "tournament": "wq"},
    {"home": "Italy", "away": "Switzerland", "score": "0-0", "year": 2021, "stage": "qualifier", "tournament": "wq"},
    {"home": "Spain", "away": "Georgia", "score": "4-0", "year": 2021, "stage": "qualifier", "tournament": "wq"},
    {"home": "France", "away": "Kazakhstan", "score": "8-0", "year": 2021, "stage": "qualifier", "tournament": "wq"},
    {"home": "Portugal", "away": "Luxembourg", "score": "5-0", "year": 2021, "stage": "qualifier", "tournament": "wq"},
    {"home": "Belgium", "away": "Estonia", "score": "3-1", "year": 2021, "stage": "qualifier", "tournament": "wq"},
    {"home": "Netherlands", "away": "Norway", "score": "1-1", "year": 2021, "stage": "qualifier", "tournament": "wq"},
    {"home": "Croatia", "away": "Slovakia", "score": "2-1", "year": 2021, "stage": "qualifier", "tournament": "wq"},
    {"home": "Denmark", "away": "Scotland", "score": "2-0", "year": 2021, "stage": "qualifier", "tournament": "wq"},
    {"home": "Serbia", "away": "Portugal", "score": "1-2", "year": 2021, "stage": "qualifier", "tournament": "wq", "upset": True},
    {"home": "Sweden", "away": "Spain", "score": "2-1", "year": 2021, "stage": "qualifier", "tournament": "wq", "upset": True},
    {"home": "Italy", "away": "North Macedonia", "score": "0-1", "year": 2021, "stage": "qualifier", "tournament": "wq", "upset": True},
]


# ============ 南美世预赛数据 ============
CONMEBOL_QUALIFIERS = [
    {"home": "Brazil", "away": "Argentina", "score": "0-0", "year": 2022, "stage": "qualifier", "tournament": "saq"},
    {"home": "Argentina", "away": "Brazil", "score": "3-0", "year": 2021, "stage": "qualifier", "tournament": "saq"},
    {"home": "Brazil", "away": "Uruguay", "score": "4-1", "year": 2021, "stage": "qualifier", "tournament": "saq"},
    {"home": "Argentina", "away": "Uruguay", "score": "3-0", "year": 2021, "stage": "qualifier", "tournament": "saq"},
    {"home": "Brazil", "away": "Colombia", "score": "1-0", "year": 2021, "stage": "qualifier", "tournament": "saq"},
    {"home": "Argentina", "away": "Chile", "score": "2-1", "year": 2021, "stage": "qualifier", "tournament": "saq"},
    {"home": "Uruguay", "away": "Colombia", "score": "0-0", "year": 2021, "stage": "qualifier", "tournament": "saq"},
    {"home": "Brazil", "away": "Venezuela", "score": "3-1", "year": 2021, "stage": "qualifier", "tournament": "saq"},
    {"home": "Argentina", "away": "Bolivia", "score": "3-0", "year": 2021, "stage": "qualifier", "tournament": "saq"},
    {"home": "Ecuador", "away": "Colombia", "score": "1-0", "year": 2021, "stage": "qualifier", "tournament": "saq", "upset": True},
    {"home": "Paraguay", "away": "Ecuador", "score": "2-0", "year": 2021, "stage": "qualifier", "tournament": "saq"},
    {"home": "Peru", "away": "Venezuela", "score": "2-1", "year": 2021, "stage": "qualifier", "tournament": "saq"},
    {"home": "Chile", "away": "Venezuela", "score": "1-2", "year": 2021, "stage": "qualifier", "tournament": "saq", "upset": True},
    {"home": "Colombia", "away": "Peru", "score": "0-1", "year": 2021, "stage": "qualifier", "tournament": "saq", "upset": True},
    {"home": "Bolivia", "away": "Paraguay", "score": "4-0", "year": 2021, "stage": "qualifier", "tournament": "saq"},
]


# ============ 非洲杯数据 ============
AFRICA_CUP = [
    {"home": "Senegal", "away": "Egypt", "score": "0-0", "year": 2022, "stage": "final", "tournament": "afcon", "penalties": True},
    {"home": "Egypt", "away": "Morocco", "score": "2-1", "year": 2022, "stage": "semi", "tournament": "afcon"},
    {"home": "Senegal", "away": "Burkina Faso", "score": "3-1", "year": 2022, "stage": "semi", "tournament": "afcon"},
    {"home": "Cameroon", "away": "Burkina Faso", "score": "2-1", "year": 2021, "stage": "quarter", "tournament": "afcon"},
    {"home": "Algeria", "away": "Ivory Coast", "score": "1-1", "year": 2021, "stage": "quarter", "tournament": "afcon", "penalties": True, "upset": True},
    {"home": "Egypt", "away": "Morocco", "score": "2-1", "year": 2021, "stage": "quarter", "tournament": "afcon"},
    {"home": "Senegal", "away": "Equatorial Guinea", "score": "2-0", "year": 2021, "stage": "quarter", "tournament": "afcon"},
    {"home": "Nigeria", "away": "Tunisia", "score": "0-1", "year": 2021, "stage": "quarter", "tournament": "afcon", "upset": True},
    {"home": "Morocco", "away": "Comoros", "score": "2-0", "year": 2021, "stage": "group", "tournament": "afcon"},
    {"home": "Algeria", "away": "Sierra Leone", "score": "0-0", "year": 2021, "stage": "group", "tournament": "afcon"},
    {"home": "Ghana", "away": "Nigeria", "score": "0-1", "year": 2021, "stage": "group", "tournament": "afcon", "upset": True},
    {"home": "Cameroon", "away": "Ethiopia", "score": "4-1", "year": 2021, "stage": "group", "tournament": "afcon"},
]


class TournamentDataCollector:
    """
    赛事数据收集器

    统一管理各类赛事的比赛数据
    """

    def __init__(self):
        self.data_dir = DATA_DIR
        self.all_data = self._load_all_data()

    def _load_all_data(self) -> List[Dict]:
        """加载所有赛事数据"""
        all_matches = []

        # 世界杯
        all_matches.extend(WORLD_CUP_DATA)

        # 欧洲杯
        all_matches.extend(EURO_DATA)

        # 欧洲预选赛
        all_matches.extend(EURO_QUALIFIERS)

        # 南美预选赛
        all_matches.extend(CONMEBOL_QUALIFIERS)

        # 非洲杯
        all_matches.extend(AFRICA_CUP)

        # 去重（基于年份、主队、客队）
        seen = set()
        unique = []
        for m in all_matches:
            key = (m.get("year"), m.get("home"), m.get("away"))
            if key not in seen:
                seen.add(key)
                unique.append(m)

        return unique

    def get_matches(self,
                   tournament: str = None,
                   year: int = None,
                   stage: str = None,
                   include_upset: bool = True) -> List[Dict]:
        """
        获取比赛数据

        Args:
            tournament: 赛事类型 (wc/euro/eq/wq/saq/afcon)
            year: 年份
            stage: 阶段 (group/quarter/semi/final)
            include_upset: 是否包含冷门比赛

        Returns:
            比赛列表
        """
        matches = self.all_data

        # 按赛事过滤
        if tournament:
            matches = [m for m in matches if m.get("tournament") == tournament]

        # 按年份过滤
        if year:
            matches = [m for m in matches if m.get("year") == year]

        # 按阶段过滤
        if stage:
            matches = [m for m in matches if m.get("stage") == stage]

        # 排除冷门（可选）
        if not include_upset:
            matches = [m for m in matches if not m.get("upset")]

        return matches

    def get_tournament_stats(self) -> Dict:
        """获取各赛事统计"""
        stats = {}

        tournaments = ["wc", "euro", "eq", "wq", "saq", "afcon"]
        tournament_names = {
            "wc": "世界杯",
            "euro": "欧洲杯",
            "eq": "欧洲杯预选",
            "wq": "世界杯预选(欧洲)",
            "saq": "南美预选赛",
            "afcon": "非洲杯"
        }

        for t in tournaments:
            matches = self.get_matches(tournament=t)
            if matches:
                stats[tournament_names[t]] = {
                    "count": len(matches),
                    "upset_count": len([m for m in matches if m.get("upset")]),
                    "years": sorted(set(m.get("year", 0) for m in matches))
                }

        return stats

    def save_to_file(self):
        """保存到文件"""
        output_file = os.path.join(self.data_dir, "tournament_matches.json")
        os.makedirs(os.path.dirname(output_file), exist_ok=True)

        with open(output_file, 'w') as f:
            json.dump({
                "matches": self.all_data,
                "stats": self.get_tournament_stats(),
                "last_updated": datetime.now().isoformat()
            }, f, ensure_ascii=False, indent=2)

        print(f"✅ 保存了 {len(self.all_data)} 场比赛到 {output_file}")

    def get_backtest_set(self, limit: int = None) -> List[Dict]:
        """获取回测数据集"""
        matches = self.get_matches(include_upset=True)

        # 打乱顺序
        import random
        random.seed(42)
        random.shuffle(matches)

        if limit:
            matches = matches[:limit]

        return matches


# ============ 测试 ============
if __name__ == "__main__":
    collector = TournamentDataCollector()

    print("=" * 60)
    print("📊 赛事数据统计")
    print("=" * 60)

    stats = collector.get_tournament_stats()
    for name, data in stats.items():
        upset_pct = data["upset_count"] / data["count"] * 100 if data["count"] > 0 else 0
        print(f"\n{name}:")
        print(f"  比赛数量: {data['count']}")
        print(f"  冷门数量: {data['upset_count']} ({upset_pct:.0f}%)")
        print(f"  年份范围: {min(data['years'])}-{max(data['years'])}")

    # 保存数据
    print("\n" + "=" * 60)
    collector.save_to_file()

    print(f"\n总计: {len(collector.all_data)} 场比赛")
