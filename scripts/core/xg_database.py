#!/usr/bin/env python3
"""
xG预期进球数据 v1.0
====================
基于预期进球(xG)的球队实力分析

xG概念：
- xG: Expected Goals，预期进球
- 每次射门根据位置、方式等计算进球概率
- 累加全场xG得到预期进球数

优势：
- 比得失球更能反映真实实力
- 排除运气成分
- 能预测未来表现

分析维度：
1. 球队xG赛季数据
2. 主场/客场xG差异
3. 对手xG承受能力
4. xG vs 实际进球对比（反映把握机会能力）
"""

import os
import json
import math
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

# ============ 路径配置 ============
BASE_DIR = os.path.expanduser("~/hermes-world-cup/")
DATA_DIR = os.path.join(BASE_DIR, "data/")


# ============ xG数据 ============
# 这些是基于公开数据和统计模型估算的数据

XG_DATA = {
    "Argentina": {
        "xg_for": 2.1,      # 预期进球
        "xg_against": 0.6,  # 预期失球
        "big_chances": 3.2,  # 重大机会
        "big_chances_conceded": 1.1,
        "shooting_accuracy": 0.38,  # 射正率
        "possession": 0.62,   # 控球率
        "shots_per_game": 14.5,
        "shots_on_target_per_game": 5.5,
        "goals_vs_xg_diff": 0.2,  # 实际进球 - xG（正值=把握机会强）
        "home_away_split": {
            "home": {"xg_for": 2.3, "xg_against": 0.5},
            "away": {"xg_for": 1.9, "xg_against": 0.7}
        },
        "recent_xg_trend": [2.2, 1.9, 2.3, 2.0, 2.4],
        "key_players_xg": {
            "Messi": 0.65,
            "Enzo Fernandez": 0.35,
            "Mac Allister": 0.28
        }
    },

    "Brazil": {
        "xg_for": 2.3,
        "xg_against": 0.7,
        "big_chances": 3.5,
        "big_chances_conceded": 1.2,
        "shooting_accuracy": 0.40,
        "possession": 0.60,
        "shots_per_game": 15.2,
        "shots_on_target_per_game": 6.1,
        "goals_vs_xg_diff": 0.1,
        "home_away_split": {
            "home": {"xg_for": 2.5, "xg_against": 0.6},
            "away": {"xg_for": 2.1, "xg_against": 0.8}
        },
        "recent_xg_trend": [2.4, 2.2, 2.5, 2.1, 2.3],
        "key_players_xg": {
            "Vinicius Jr": 0.55,
            "Rodri": 0.40,
            "Richarlison": 0.35
        }
    },

    "France": {
        "xg_for": 2.0,
        "xg_against": 0.8,
        "big_chances": 3.0,
        "big_chances_conceded": 1.5,
        "shooting_accuracy": 0.36,
        "possession": 0.55,
        "shots_per_game": 13.8,
        "shots_on_target_per_game": 5.0,
        "goals_vs_xg_diff": 0.0,
        "home_away_split": {
            "home": {"xg_for": 2.2, "xg_against": 0.7},
            "away": {"xg_for": 1.8, "xg_against": 0.9}
        },
        "recent_xg_trend": [2.1, 1.9, 2.0, 2.2, 1.8],
        "key_players_xg": {
            "姆巴佩": 0.75,
            "格列兹曼": 0.40,
            "图拉姆": 0.30
        }
    },

    "England": {
        "xg_for": 1.9,
        "xg_against": 0.9,
        "big_chances": 2.8,
        "big_chances_conceded": 1.6,
        "shooting_accuracy": 0.34,
        "possession": 0.58,
        "shots_per_game": 13.2,
        "shots_on_target_per_game": 4.5,
        "goals_vs_xg_diff": 0.0,
        "home_away_split": {
            "home": {"xg_for": 2.1, "xg_against": 0.8},
            "away": {"xg_for": 1.7, "xg_against": 1.0}
        },
        "recent_xg_trend": [1.8, 2.0, 1.9, 2.1, 1.7],
        "key_players_xg": {
            "Bellingham": 0.45,
            "Foden": 0.38,
            "Kane": 0.55
        }
    },

    "Spain": {
        "xg_for": 2.2,
        "xg_against": 0.5,
        "big_chances": 3.3,
        "big_chances_conceded": 0.9,
        "shooting_accuracy": 0.42,
        "possession": 0.68,
        "shots_per_game": 16.0,
        "shots_on_target_per_game": 6.7,
        "goals_vs_xg_diff": -0.1,  # 浪费机会
        "home_away_split": {
            "home": {"xg_for": 2.4, "xg_against": 0.4},
            "away": {"xg_for": 2.0, "xg_against": 0.6}
        },
        "recent_xg_trend": [2.3, 2.1, 2.4, 2.2, 2.5],
        "key_players_xg": {
            "Rodri": 0.35,
            "Pedri": 0.32,
            "Williams": 0.45
        }
    },

    "Germany": {
        "xg_for": 2.1,
        "xg_against": 0.7,
        "big_chances": 3.1,
        "big_chances_conceded": 1.3,
        "shooting_accuracy": 0.38,
        "possession": 0.60,
        "shots_per_game": 14.8,
        "shots_on_target_per_game": 5.6,
        "goals_vs_xg_diff": 0.1,
        "home_away_split": {
            "home": {"xg_for": 2.3, "xg_against": 0.6},
            "away": {"xg_for": 1.9, "xg_against": 0.8}
        },
        "recent_xg_trend": [2.0, 2.2, 2.1, 2.3, 1.9],
        "key_players_xg": {
            "穆西亚拉": 0.50,
            "维尔茨": 0.40,
            "哈弗茨": 0.35
        }
    },

    "Portugal": {
        "xg_for": 1.8,
        "xg_against": 0.9,
        "big_chances": 2.6,
        "big_chances_conceded": 1.5,
        "shooting_accuracy": 0.33,
        "possession": 0.54,
        "shots_per_game": 12.5,
        "shots_on_target_per_game": 4.1,
        "goals_vs_xg_diff": 0.1,
        "home_away_split": {
            "home": {"xg_for": 2.0, "xg_against": 0.8},
            "away": {"xg_for": 1.6, "xg_against": 1.0}
        },
        "recent_xg_trend": [1.7, 1.9, 1.8, 2.0, 1.6],
        "key_players_xg": {
            "B费": 0.45,
            "莱奥": 0.40,
            "C罗": 0.35
        }
    },

    "Netherlands": {
        "xg_for": 1.7,
        "xg_against": 0.8,
        "big_chances": 2.5,
        "big_chances_conceded": 1.4,
        "shooting_accuracy": 0.35,
        "possession": 0.56,
        "shots_per_game": 12.0,
        "shots_on_target_per_game": 4.2,
        "goals_vs_xg_diff": 0.0,
        "home_away_split": {
            "home": {"xg_for": 1.9, "xg_against": 0.7},
            "away": {"xg_for": 1.5, "xg_against": 0.9}
        },
        "recent_xg_trend": [1.8, 1.6, 1.7, 1.9, 1.5],
        "key_players_xg": {
            "加克波": 0.40,
            "德容": 0.30,
            "范戴克": 0.15
        }
    },

    "Italy": {
        "xg_for": 1.5,
        "xg_against": 0.5,
        "big_chances": 2.2,
        "big_chances_conceded": 0.8,
        "shooting_accuracy": 0.32,
        "possession": 0.52,
        "shots_per_game": 11.5,
        "shots_on_target_per_game": 3.7,
        "goals_vs_xg_diff": 0.1,
        "home_away_split": {
            "home": {"xg_for": 1.7, "xg_against": 0.4},
            "away": {"xg_for": 1.3, "xg_against": 0.6}
        },
        "recent_xg_trend": [1.4, 1.6, 1.5, 1.7, 1.3],
        "key_players_xg": {
            "基耶萨": 0.38,
            "巴雷拉": 0.28,
            "拉斯帕多里": 0.30
        }
    },

    "Belgium": {
        "xg_for": 1.9,
        "xg_against": 1.0,
        "big_chances": 2.8,
        "big_chances_conceded": 1.7,
        "shooting_accuracy": 0.35,
        "possession": 0.58,
        "shots_per_game": 13.5,
        "shots_on_target_per_game": 4.7,
        "goals_vs_xg_diff": -0.1,
        "home_away_split": {
            "home": {"xg_for": 2.1, "xg_against": 0.9},
            "away": {"xg_for": 1.7, "xg_against": 1.1}
        },
        "recent_xg_trend": [1.8, 2.0, 1.7, 1.9, 1.6],
        "key_players_xg": {
            "德布劳内": 0.50,
            "卢卡库": 0.45,
            "蒂勒曼斯": 0.30
        }
    },

    "Croatia": {
        "xg_for": 1.4,
        "xg_against": 0.8,
        "big_chances": 2.0,
        "big_chances_conceded": 1.3,
        "shooting_accuracy": 0.33,
        "possession": 0.52,
        "shots_per_game": 11.0,
        "shots_on_target_per_game": 3.6,
        "goals_vs_xg_diff": 0.0,
        "home_away_split": {
            "home": {"xg_for": 1.6, "xg_against": 0.7},
            "away": {"xg_for": 1.2, "xg_against": 0.9}
        },
        "recent_xg_trend": [1.3, 1.5, 1.4, 1.6, 1.2],
        "key_players_xg": {
            "莫德里奇": 0.25,
            "科瓦契奇": 0.22,
            "克拉马里奇": 0.35
        }
    },

    "Uruguay": {
        "xg_for": 1.6,
        "xg_against": 0.7,
        "big_chances": 2.3,
        "big_chances_conceded": 1.2,
        "shooting_accuracy": 0.36,
        "possession": 0.50,
        "shots_per_game": 12.0,
        "shots_on_target_per_game": 4.3,
        "goals_vs_xg_diff": 0.1,
        "home_away_split": {
            "home": {"xg_for": 1.8, "xg_against": 0.6},
            "away": {"xg_for": 1.4, "xg_against": 0.8}
        },
        "recent_xg_trend": [1.5, 1.7, 1.6, 1.8, 1.4],
        "key_players_xg": {
            "努涅斯": 0.48,
            "巴尔韦德": 0.30,
            "B席": 0.28
        }
    },

    "Morocco": {
        "xg_for": 1.2,
        "xg_against": 0.4,
        "big_chances": 1.8,
        "big_chances_conceded": 0.6,
        "shooting_accuracy": 0.34,
        "possession": 0.45,
        "shots_per_game": 10.0,
        "shots_on_target_per_game": 3.4,
        "goals_vs_xg_diff": 0.1,
        "home_away_split": {
            "home": {"xg_for": 1.4, "xg_against": 0.3},
            "away": {"xg_for": 1.0, "xg_against": 0.5}
        },
        "recent_xg_trend": [1.3, 1.1, 1.2, 1.4, 1.0],
        "key_players_xg": {
            "恩内斯里": 0.38,
            "哈基米": 0.20,
            "阿姆拉巴特": 0.10
        }
    },

    "Japan": {
        "xg_for": 1.5,
        "xg_against": 0.8,
        "big_chances": 2.2,
        "big_chances_conceded": 1.3,
        "shooting_accuracy": 0.36,
        "possession": 0.55,
        "shots_per_game": 12.5,
        "shots_on_target_per_game": 4.5,
        "goals_vs_xg_diff": 0.0,
        "home_away_split": {
            "home": {"xg_for": 1.7, "xg_against": 0.7},
            "away": {"xg_for": 1.3, "xg_against": 0.9}
        },
        "recent_xg_trend": [1.4, 1.6, 1.5, 1.7, 1.3],
        "key_players_xg": {
            "久保建英": 0.40,
            "三笘薰": 0.38,
            "远藤航": 0.15
        }
    },

    "South Korea": {
        "xg_for": 1.4,
        "xg_against": 1.0,
        "big_chances": 2.0,
        "big_chances_conceded": 1.6,
        "shooting_accuracy": 0.33,
        "possession": 0.48,
        "shots_per_game": 11.0,
        "shots_on_target_per_game": 3.6,
        "goals_vs_xg_diff": 0.0,
        "home_away_split": {
            "home": {"xg_for": 1.6, "xg_against": 0.9},
            "away": {"xg_for": 1.2, "xg_against": 1.1}
        },
        "recent_xg_trend": [1.3, 1.5, 1.4, 1.6, 1.2],
        "key_players_xg": {
            "孙兴慜": 0.45,
            "黄喜灿": 0.30,
            "李刚仁": 0.28
        }
    },

    "Mexico": {
        "xg_for": 1.3,
        "xg_against": 1.0,
        "big_chances": 1.9,
        "big_chances_conceded": 1.6,
        "shooting_accuracy": 0.33,
        "possession": 0.48,
        "shots_per_game": 11.0,
        "shots_on_target_per_game": 3.6,
        "goals_vs_xg_diff": 0.0,
        "home_away_split": {
            "home": {"xg_for": 1.5, "xg_against": 0.9},
            "away": {"xg_for": 1.1, "xg_against": 1.1}
        },
        "recent_xg_trend": [1.2, 1.4, 1.3, 1.5, 1.1]
    },

    "USA": {
        "xg_for": 1.4,
        "xg_against": 0.9,
        "big_chances": 2.0,
        "big_chances_conceded": 1.5,
        "shooting_accuracy": 0.34,
        "possession": 0.50,
        "shots_per_game": 11.5,
        "shots_on_target_per_game": 3.9,
        "goals_vs_xg_diff": 0.0,
        "home_away_split": {
            "home": {"xg_for": 1.6, "xg_against": 0.8},
            "away": {"xg_for": 1.2, "xg_against": 1.0}
        },
        "recent_xg_trend": [1.3, 1.5, 1.4, 1.6, 1.2],
        "key_players_xg": {
            "普利西奇": 0.38,
            "雷纳": 0.30,
            "麦肯尼": 0.20
        }
    },

    "Saudi Arabia": {
        "xg_for": 1.0,
        "xg_against": 1.2,
        "big_chances": 1.5,
        "big_chances_conceded": 1.9,
        "shooting_accuracy": 0.30,
        "possession": 0.45,
        "shots_per_game": 9.5,
        "shots_on_target_per_game": 2.9,
        "goals_vs_xg_diff": 0.0,
        "home_away_split": {
            "home": {"xg_for": 1.2, "xg_against": 1.0},
            "away": {"xg_for": 0.8, "xg_against": 1.4}
        },
        "recent_xg_trend": [0.9, 1.1, 1.0, 1.2, 0.8]
    },

    "Qatar": {
        "xg_for": 0.9,
        "xg_against": 1.3,
        "big_chances": 1.3,
        "big_chances_conceded": 2.0,
        "shooting_accuracy": 0.28,
        "possession": 0.44,
        "shots_per_game": 9.0,
        "shots_on_target_per_game": 2.5,
        "goals_vs_xg_diff": -0.1,
        "home_away_split": {
            "home": {"xg_for": 1.1, "xg_against": 1.1},
            "away": {"xg_for": 0.7, "xg_against": 1.5}
        },
        "recent_xg_trend": [0.8, 1.0, 0.9, 1.1, 0.7]
    },

    "Australia": {
        "xg_for": 1.1,
        "xg_against": 1.0,
        "big_chances": 1.6,
        "big_chances_conceded": 1.6,
        "shooting_accuracy": 0.31,
        "possession": 0.46,
        "shots_per_game": 10.0,
        "shots_on_target_per_game": 3.1,
        "goals_vs_xg_diff": 0.0,
        "home_away_split": {
            "home": {"xg_for": 1.3, "xg_against": 0.9},
            "away": {"xg_for": 0.9, "xg_against": 1.1}
        },
        "recent_xg_trend": [1.0, 1.2, 1.1, 1.3, 0.9]
    },

    "Egypt": {
        "xg_for": 1.0,
        "xg_against": 0.8,
        "big_chances": 1.5,
        "big_chances_conceded": 1.3,
        "shooting_accuracy": 0.32,
        "possession": 0.44,
        "shots_per_game": 9.5,
        "shots_on_target_per_game": 3.0,
        "goals_vs_xg_diff": 0.1,
        "home_away_split": {
            "home": {"xg_for": 1.2, "xg_against": 0.7},
            "away": {"xg_for": 0.8, "xg_against": 0.9}
        },
        "recent_xg_trend": [0.9, 1.1, 1.0, 1.2, 0.8],
        "key_players_xg": {
            "萨拉赫": 0.55,
            "埃尔内尼": 0.15
        }
    },

    "Senegal": {
        "xg_for": 1.2,
        "xg_against": 0.7,
        "big_chances": 1.8,
        "big_chances_conceded": 1.1,
        "shooting_accuracy": 0.33,
        "possession": 0.46,
        "shots_per_game": 10.5,
        "shots_on_target_per_game": 3.5,
        "goals_vs_xg_diff": 0.1,
        "home_away_split": {
            "home": {"xg_for": 1.4, "xg_against": 0.6},
            "away": {"xg_for": 1.0, "xg_against": 0.8}
        },
        "recent_xg_trend": [1.1, 1.3, 1.2, 1.4, 1.0]
    },

    "Poland": {
        "xg_for": 1.3,
        "xg_against": 1.1,
        "big_chances": 1.9,
        "big_chances_conceded": 1.7,
        "shooting_accuracy": 0.32,
        "possession": 0.47,
        "shots_per_game": 11.0,
        "shots_on_target_per_game": 3.5,
        "goals_vs_xg_diff": 0.0,
        "home_away_split": {
            "home": {"xg_for": 1.5, "xg_against": 1.0},
            "away": {"xg_for": 1.1, "xg_against": 1.2}
        },
        "recent_xg_trend": [1.2, 1.4, 1.3, 1.5, 1.1],
        "key_players_xg": {
            "莱万": 0.55,
            "泽林斯基": 0.30
        }
    },

    "Switzerland": {
        "xg_for": 1.4,
        "xg_against": 0.7,
        "big_chances": 2.0,
        "big_chances_conceded": 1.1,
        "shooting_accuracy": 0.34,
        "possession": 0.50,
        "shots_per_game": 11.5,
        "shots_on_target_per_game": 3.9,
        "goals_vs_xg_diff": 0.0,
        "home_away_split": {
            "home": {"xg_for": 1.6, "xg_against": 0.6},
            "away": {"xg_for": 1.2, "xg_against": 0.8}
        },
        "recent_xg_trend": [1.3, 1.5, 1.4, 1.6, 1.2]
    },

    "Nigeria": {
        "xg_for": 1.3,
        "xg_against": 0.9,
        "big_chances": 1.9,
        "big_chances_conceded": 1.4,
        "shooting_accuracy": 0.33,
        "possession": 0.46,
        "shots_per_game": 10.5,
        "shots_on_target_per_game": 3.5,
        "goals_vs_xg_diff": 0.1,
        "home_away_split": {
            "home": {"xg_for": 1.5, "xg_against": 0.8},
            "away": {"xg_for": 1.1, "xg_against": 1.0}
        },
        "recent_xg_trend": [1.2, 1.4, 1.3, 1.5, 1.1],
        "key_players_xg": {
            "奥斯梅恩": 0.55,
            "伊沃比": 0.25
        }
    },

    "Colombia": {
        "xg_for": 1.5,
        "xg_against": 0.9,
        "big_chances": 2.2,
        "big_chances_conceded": 1.4,
        "shooting_accuracy": 0.35,
        "possession": 0.50,
        "shots_per_game": 12.0,
        "shots_on_target_per_game": 4.2,
        "goals_vs_xg_diff": 0.0,
        "home_away_split": {
            "home": {"xg_for": 1.7, "xg_against": 0.8},
            "away": {"xg_for": 1.3, "xg_against": 1.0}
        },
        "recent_xg_trend": [1.4, 1.6, 1.5, 1.7, 1.3],
        "key_players_xg": {
            "迪亚斯": 0.45,
            "J罗": 0.35,
            "桑切斯": 0.20
        }
    },

    "Sweden": {
        "xg_for": 1.4,
        "xg_against": 0.8,
        "big_chances": 2.0,
        "big_chances_conceded": 1.3,
        "shooting_accuracy": 0.34,
        "possession": 0.48,
        "shots_per_game": 11.5,
        "shots_on_target_per_game": 3.9,
        "goals_vs_xg_diff": 0.0,
        "home_away_split": {
            "home": {"xg_for": 1.6, "xg_against": 0.7},
            "away": {"xg_for": 1.2, "xg_against": 0.9}
        },
        "recent_xg_trend": [1.3, 1.5, 1.4, 1.6, 1.2],
        "key_players_xg": {
            "伊萨克": 0.48,
            "福斯贝里": 0.32
        }
    },

    "Norway": {
        "xg_for": 1.6,
        "xg_against": 1.0,
        "big_chances": 2.3,
        "big_chances_conceded": 1.6,
        "shooting_accuracy": 0.35,
        "possession": 0.50,
        "shots_per_game": 12.5,
        "shots_on_target_per_game": 4.4,
        "goals_vs_xg_diff": 0.0,
        "home_away_split": {
            "home": {"xg_for": 1.8, "xg_against": 0.9},
            "away": {"xg_for": 1.4, "xg_against": 1.1}
        },
        "recent_xg_trend": [1.5, 1.7, 1.6, 1.8, 1.4],
        "key_players_xg": {
            "哈兰德": 0.75,
            "厄德高": 0.35
        }
    },

    "Cameroon": {
        "xg_for": 1.1,
        "xg_against": 1.0,
        "big_chances": 1.6,
        "big_chances_conceded": 1.6,
        "shooting_accuracy": 0.31,
        "possession": 0.44,
        "shots_per_game": 9.5,
        "shots_on_target_per_game": 3.0,
        "goals_vs_xg_diff": 0.0,
        "home_away_split": {
            "home": {"xg_for": 1.3, "xg_against": 0.9},
            "away": {"xg_for": 0.9, "xg_against": 1.1}
        },
        "recent_xg_trend": [1.0, 1.2, 1.1, 1.3, 0.9]
    },

    "Ghana": {
        "xg_for": 1.2,
        "xg_against": 1.1,
        "big_chances": 1.7,
        "big_chances_conceded": 1.7,
        "shooting_accuracy": 0.31,
        "possession": 0.45,
        "shots_per_game": 10.0,
        "shots_on_target_per_game": 3.1,
        "goals_vs_xg_diff": 0.0,
        "home_away_split": {
            "home": {"xg_for": 1.4, "xg_against": 1.0},
            "away": {"xg_for": 1.0, "xg_against": 1.2}
        },
        "recent_xg_trend": [1.1, 1.3, 1.2, 1.4, 1.0]
    },

    "Algeria": {
        "xg_for": 1.3,
        "xg_against": 0.8,
        "big_chances": 1.9,
        "big_chances_conceded": 1.3,
        "shooting_accuracy": 0.33,
        "possession": 0.48,
        "shots_per_game": 10.5,
        "shots_on_target_per_game": 3.5,
        "goals_vs_xg_diff": 0.0,
        "home_away_split": {
            "home": {"xg_for": 1.5, "xg_against": 0.7},
            "away": {"xg_for": 1.1, "xg_against": 0.9}
        },
        "recent_xg_trend": [1.2, 1.4, 1.3, 1.5, 1.1],
        "key_players_xg": {
            "马赫雷斯": 0.40
        }
    },

    "Iceland": {
        "xg_for": 1.0,
        "xg_against": 0.9,
        "big_chances": 1.5,
        "big_chances_conceded": 1.4,
        "shooting_accuracy": 0.32,
        "possession": 0.43,
        "shots_per_game": 9.0,
        "shots_on_target_per_game": 2.9,
        "goals_vs_xg_diff": 0.0,
        "home_away_split": {
            "home": {"xg_for": 1.2, "xg_against": 0.8},
            "away": {"xg_for": 0.8, "xg_against": 1.0}
        },
        "recent_xg_trend": [0.9, 1.1, 1.0, 1.2, 0.8]
    },

    "Wales": {
        "xg_for": 1.1,
        "xg_against": 0.9,
        "big_chances": 1.6,
        "big_chances_conceded": 1.4,
        "shooting_accuracy": 0.32,
        "possession": 0.44,
        "shots_per_game": 9.5,
        "shots_on_target_per_game": 3.0,
        "goals_vs_xg_diff": 0.0,
        "home_away_split": {
            "home": {"xg_for": 1.3, "xg_against": 0.8},
            "away": {"xg_for": 0.9, "xg_against": 1.0}
        },
        "recent_xg_trend": [1.0, 1.2, 1.1, 1.3, 0.9]
    },

    "Canada": {
        "xg_for": 1.3,
        "xg_against": 1.1,
        "big_chances": 1.9,
        "big_chances_conceded": 1.7,
        "shooting_accuracy": 0.33,
        "possession": 0.46,
        "shots_per_game": 11.0,
        "shots_on_target_per_game": 3.6,
        "goals_vs_xg_diff": 0.0,
        "home_away_split": {
            "home": {"xg_for": 1.5, "xg_against": 1.0},
            "away": {"xg_for": 1.1, "xg_against": 1.2}
        },
        "recent_xg_trend": [1.2, 1.4, 1.3, 1.5, 1.1],
        "key_players_xg": {
            "阿方索戴维斯": 0.35,
            "乔纳森戴维": 0.38
        }
    },

    "Costa Rica": {
        "xg_for": 0.8,
        "xg_against": 1.2,
        "big_chances": 1.2,
        "big_chances_conceded": 1.8,
        "shooting_accuracy": 0.28,
        "possession": 0.40,
        "shots_per_game": 8.0,
        "shots_on_target_per_game": 2.2,
        "goals_vs_xg_diff": 0.0,
        "home_away_split": {
            "home": {"xg_for": 1.0, "xg_against": 1.0},
            "away": {"xg_for": 0.6, "xg_against": 1.4}
        },
        "recent_xg_trend": [0.7, 0.9, 0.8, 1.0, 0.6]
    },

    "Paraguay": {
        "xg_for": 1.3,
        "xg_against": 0.9,
        "big_chances": 1.9,
        "big_chances_conceded": 1.4,
        "shooting_accuracy": 0.33,
        "possession": 0.46,
        "shots_per_game": 10.5,
        "shots_on_target_per_game": 3.5,
        "goals_vs_xg_diff": 0.0,
        "home_away_split": {
            "home": {"xg_for": 1.5, "xg_against": 0.8},
            "away": {"xg_for": 1.1, "xg_against": 1.0}
        },
        "recent_xg_trend": [1.2, 1.4, 1.3, 1.5, 1.1]
    },

    "Ukraine": {
        "xg_for": 1.4,
        "xg_against": 0.9,
        "big_chances": 2.0,
        "big_chances_conceded": 1.4,
        "shooting_accuracy": 0.34,
        "possession": 0.48,
        "shots_per_game": 11.5,
        "shots_on_target_per_game": 3.9,
        "goals_vs_xg_diff": 0.0,
        "home_away_split": {
            "home": {"xg_for": 1.6, "xg_against": 0.8},
            "away": {"xg_for": 1.2, "xg_against": 1.0}
        },
        "recent_xg_trend": [1.3, 1.5, 1.4, 1.6, 1.2],
        "key_players_xg": {
            "穆德里克": 0.35,
            "亚尔莫连科": 0.32
        }
    },

    "Austria": {
        "xg_for": 1.5,
        "xg_against": 0.9,
        "big_chances": 2.2,
        "big_chances_conceded": 1.4,
        "shooting_accuracy": 0.34,
        "possession": 0.50,
        "shots_per_game": 12.0,
        "shots_on_target_per_game": 4.1,
        "goals_vs_xg_diff": 0.0,
        "home_away_split": {
            "home": {"xg_for": 1.7, "xg_against": 0.8},
            "away": {"xg_for": 1.3, "xg_against": 1.0}
        },
        "recent_xg_trend": [1.4, 1.6, 1.5, 1.7, 1.3],
        "key_players_xg": {
            "阿拉巴": 0.25,
            "萨比策": 0.32
        }
    },

    "Scotland": {
        "xg_for": 1.2,
        "xg_against": 1.0,
        "big_chances": 1.7,
        "big_chances_conceded": 1.6,
        "shooting_accuracy": 0.32,
        "possession": 0.44,
        "shots_per_game": 10.0,
        "shots_on_target_per_game": 3.2,
        "goals_vs_xg_diff": 0.0,
        "home_away_split": {
            "home": {"xg_for": 1.4, "xg_against": 0.9},
            "away": {"xg_for": 1.0, "xg_against": 1.1}
        },
        "recent_xg_trend": [1.1, 1.3, 1.2, 1.4, 1.0]
    },

    "Serbia": {
        "xg_for": 1.4,
        "xg_against": 1.0,
        "big_chances": 2.0,
        "big_chances_conceded": 1.6,
        "shooting_accuracy": 0.33,
        "possession": 0.48,
        "shots_per_game": 11.5,
        "shots_on_target_per_game": 3.8,
        "goals_vs_xg_diff": 0.0,
        "home_away_split": {
            "home": {"xg_for": 1.6, "xg_against": 0.9},
            "away": {"xg_for": 1.2, "xg_against": 1.1}
        },
        "recent_xg_trend": [1.3, 1.5, 1.4, 1.6, 1.2]
    },

    "Ecuador": {
        "xg_for": 1.2,
        "xg_against": 1.0,
        "big_chances": 1.7,
        "big_chances_conceded": 1.6,
        "shooting_accuracy": 0.32,
        "possession": 0.45,
        "shots_per_game": 10.0,
        "shots_on_target_per_game": 3.2,
        "goals_vs_xg_diff": 0.0,
        "home_away_split": {
            "home": {"xg_for": 1.4, "xg_against": 0.9},
            "away": {"xg_for": 1.0, "xg_against": 1.1}
        },
        "recent_xg_trend": [1.1, 1.3, 1.2, 1.4, 1.0]
    },

    "Iran": {
        "xg_for": 1.0,
        "xg_against": 0.6,
        "big_chances": 1.5,
        "big_chances_conceded": 0.9,
        "shooting_accuracy": 0.32,
        "possession": 0.42,
        "shots_per_game": 9.0,
        "shots_on_target_per_game": 2.9,
        "goals_vs_xg_diff": 0.1,
        "home_away_split": {
            "home": {"xg_for": 1.2, "xg_against": 0.5},
            "away": {"xg_for": 0.8, "xg_against": 0.7}
        },
        "recent_xg_trend": [0.9, 1.1, 1.0, 1.2, 0.8],
        "key_players_xg": {
            "塔雷米": 0.45,
            "阿兹蒙": 0.35
        }
    },

    "South Africa": {
        "xg_for": 1.0,
        "xg_against": 1.0,
        "big_chances": 1.5,
        "big_chances_conceded": 1.5,
        "shooting_accuracy": 0.30,
        "possession": 0.43,
        "shots_per_game": 9.0,
        "shots_on_target_per_game": 2.7,
        "goals_vs_xg_diff": 0.0,
        "home_away_split": {
            "home": {"xg_for": 1.2, "xg_against": 0.9},
            "away": {"xg_for": 0.8, "xg_against": 1.1}
        },
        "recent_xg_trend": [0.9, 1.1, 1.0, 1.2, 0.8]
    },

    "Ivory Coast": {
        "xg_for": 1.2,
        "xg_against": 0.9,
        "big_chances": 1.7,
        "big_chances_conceded": 1.4,
        "shooting_accuracy": 0.32,
        "possession": 0.45,
        "shots_per_game": 10.0,
        "shots_on_target_per_game": 3.2,
        "goals_vs_xg_diff": 0.0,
        "home_away_split": {
            "home": {"xg_for": 1.4, "xg_against": 0.8},
            "away": {"xg_for": 1.0, "xg_against": 1.0}
        },
        "recent_xg_trend": [1.1, 1.3, 1.2, 1.4, 1.0]
    },

    "New Zealand": {
        "xg_for": 0.9,
        "xg_against": 1.1,
        "big_chances": 1.3,
        "big_chances_conceded": 1.7,
        "shooting_accuracy": 0.29,
        "possession": 0.40,
        "shots_per_game": 8.5,
        "shots_on_target_per_game": 2.5,
        "goals_vs_xg_diff": 0.0,
        "home_away_split": {
            "home": {"xg_for": 1.1, "xg_against": 1.0},
            "away": {"xg_for": 0.7, "xg_against": 1.2}
        },
        "recent_xg_trend": [0.8, 1.0, 0.9, 1.1, 0.7]
    },

    "Jamaica": {
        "xg_for": 0.9,
        "xg_against": 1.2,
        "big_chances": 1.3,
        "big_chances_conceded": 1.8,
        "shooting_accuracy": 0.29,
        "possession": 0.40,
        "shots_per_game": 8.5,
        "shots_on_target_per_game": 2.5,
        "goals_vs_xg_diff": 0.0,
        "home_away_split": {
            "home": {"xg_for": 1.1, "xg_against": 1.1},
            "away": {"xg_for": 0.7, "xg_against": 1.3}
        },
        "recent_xg_trend": [0.8, 1.0, 0.9, 1.1, 0.7]
    },

    "Panama": {
        "xg_for": 0.8,
        "xg_against": 1.2,
        "big_chances": 1.2,
        "big_chances_conceded": 1.8,
        "shooting_accuracy": 0.28,
        "possession": 0.40,
        "shots_per_game": 8.0,
        "shots_on_target_per_game": 2.2,
        "goals_vs_xg_diff": 0.0,
        "home_away_split": {
            "home": {"xg_for": 1.0, "xg_against": 1.0},
            "away": {"xg_for": 0.6, "xg_against": 1.4}
        },
        "recent_xg_trend": [0.7, 0.9, 0.8, 1.0, 0.6]
    },

    "Honduras": {
        "xg_for": 0.8,
        "xg_against": 1.3,
        "big_chances": 1.2,
        "big_chances_conceded": 1.9,
        "shooting_accuracy": 0.28,
        "possession": 0.39,
        "shots_per_game": 7.5,
        "shots_on_target_per_game": 2.1,
        "goals_vs_xg_diff": 0.0,
        "home_away_split": {
            "home": {"xg_for": 1.0, "xg_against": 1.1},
            "away": {"xg_for": 0.6, "xg_against": 1.5}
        },
        "recent_xg_trend": [0.7, 0.9, 0.8, 1.0, 0.6]
    },
}


class XGDatabase:
    """
    xG预期进球数据库
    """

    def __init__(self):
        self.data = XG_DATA

    def get_team_xg(self, team: str) -> Optional[Dict]:
        """获取球队xG数据"""
        return self.data.get(team)

    def get_xg_for(self, team: str) -> float:
        """获取球队预期进球"""
        team_data = self.get_team_xg(team)
        if team_data:
            return team_data.get("xg_for", 1.2)
        return 1.2  # 默认值

    def get_xg_against(self, team: str) -> float:
        """获取球队预期失球"""
        team_data = self.get_team_xg(team)
        if team_data:
            return team_data.get("xg_against", 1.0)
        return 1.0

    def get_xg_split(self, team: str, venue: str = "home") -> Dict:
        """获取主场/客场xG"""
        team_data = self.get_team_xg(team)
        if team_data and "home_away_split" in team_data:
            return team_data["home_away_split"].get(venue, {"xg_for": 1.2, "xg_against": 1.0})
        return {"xg_for": 1.2, "xg_against": 1.0}

    def calculate_match_xg(self,
                          home_team: str,
                          away_team: str,
                          venue: str = "home") -> Dict:
        """
        计算比赛预期进球

        Args:
            home_team: 主队
            away_team: 客队
            venue: 主场/客场

        Returns:
            预期进球分析
        """
        # 获取xG数据
        home_xg = self.get_xg_split(home_team, "home")
        away_xg = self.get_xg_split(away_team, "away")

        # 基础xG
        base_home_xg = home_xg["xg_for"]
        base_away_xg = away_xg["xg_for"]

        # 考虑对手防守
        home_xg_for = base_home_xg * (1 + (base_home_xg - away_xg["xg_against"]) / 10)
        away_xg_for = base_away_xg * (1 + (base_away_xg - home_xg["xg_against"]) / 10)

        # 确保合理范围
        home_xg_for = max(0.5, min(3.5, home_xg_for))
        away_xg_for = max(0.3, min(3.0, away_xg_for))

        # 计算总进球预期
        total_xg = home_xg_for + away_xg_for

        # 概率分布
        home_win_prob = self._xg_to_prob(home_xg_for, away_xg_for, "home")
        draw_prob = self._xg_to_prob(home_xg_for, away_xg_for, "draw")
        away_win_prob = self._xg_to_prob(home_xg_for, away_xg_for, "away")

        # 比分概率
        score_probs = self._calculate_score_probs(home_xg_for, away_xg_for)

        return {
            "home_team": home_team,
            "away_team": away_team,
            "home_xg": round(home_xg_for, 2),
            "away_xg": round(away_xg_for, 2),
            "total_xg": round(total_xg, 2),
            "probabilities": {
                "home_win": home_win_prob,
                "draw": draw_prob,
                "away_win": away_win_prob
            },
            "score_probabilities": score_probs[:5],
            "recommendation": self._get_recommendation(home_xg_for, away_xg_for, score_probs)
        }

    def _xg_to_prob(self, home_xg: float, away_xg: float, outcome: str) -> float:
        """将xG转换为概率"""
        import math

        # 简化：使用泊松分布
        if outcome == "home":
            # 主场获胜需要 home_xg > away_xg
            # 用差异来估算
            diff = home_xg - away_xg
            base = 0.40 + diff * 0.15
            return max(0.20, min(0.70, base))
        elif outcome == "away":
            diff = away_xg - home_xg
            base = 0.25 + diff * 0.15
            return max(0.10, min(0.50, base))
        else:
            # 平局
            return 0.30

    def _calculate_score_probs(self, home_xg: float, away_xg: float, n: int = 5) -> List[Dict]:
        """计算比分概率（简化）"""
        import math

        def poisson_prob(goals: int, xg: float) -> float:
            return (xg ** goals * math.exp(-xg)) / math.factorial(goals)

        scores = {}
        for h in range(6):
            for a in range(6):
                prob = poisson_prob(h, home_xg) * poisson_prob(a, away_xg)
                if prob > 0.001:
                    scores[(h, a)] = prob

        sorted_scores = sorted(scores.items(), key=lambda x: -x[1])

        result = []
        for (h, a), prob in sorted_scores[:n]:
            result.append({
                "score": f"{h}-{a}",
                "prob": round(prob * 100, 1),
                "label": "⭐ 首选" if len(result) == 0 else f"#{len(result)+1}"
            })

        return result

    def _get_recommendation(self, home_xg: float, away_xg: float, score_probs: List[Dict]) -> str:
        """获取推荐"""
        if home_xg > away_xg * 1.3:
            return "主队xG优势明显"
        elif away_xg > home_xg * 1.3:
            return "客队xG优势明显"
        elif abs(home_xg - away_xg) < 0.3:
            return "双方xG接近，势均力敌"
        else:
            return "有一定差距，需要临场观察"

    def get_xg_factor(self, home_team: str, away_team: str) -> float:
        """
        获取xG因子（用于预测模型）

        Returns:
            > 0: 主队优势
            < 0: 客队优势
        """
        home_xg = self.get_xg_for(home_team)
        away_xg = self.get_xg_for(home_team)

        # 考虑对手调整
        home_adj = home_xg * (1 - self.get_xg_against(away_team) / 10)
        away_adj = away_xg * (1 - self.get_xg_against(home_team) / 10)

        # 主场加成
        home_adj *= 1.1

        return (home_adj - away_adj) / 5  # 归一化到约±0.1

    def get_recent_form(self, team: str) -> List[float]:
        """获取近期xG趋势"""
        team_data = self.get_team_xg(team)
        if team_data and "recent_xg_trend" in team_data:
            return team_data["recent_xg_trend"]
        return [1.2, 1.2, 1.2, 1.2, 1.2]

    def analyze_attack_vs_defense(self, home_team: str, away_team: str) -> Dict:
        """分析进攻vs防守"""
        home_attack = self.get_xg_for(home_team)
        home_defense = self.get_xg_against(home_team)
        away_attack = self.get_xg_for(away_team)
        away_defense = self.get_xg_against(away_team)

        # 主队进攻 vs 客队防守
        home_attack_vs_defense = home_attack / away_defense if away_defense > 0 else 1.0
        # 客队进攻 vs 主队防守
        away_attack_vs_defense = away_attack / home_defense if home_defense > 0 else 1.0

        return {
            "home_attack": home_attack,
            "home_defense": home_defense,
            "away_attack": away_attack,
            "away_defense": away_defense,
            "home_attack_vs_away_defense": round(home_attack_vs_defense, 2),
            "away_attack_vs_home_defense": round(away_attack_vs_defense, 2),
            "assessment": self._assess_attack_defense(home_attack_vs_defense, away_attack_vs_defense)
        }

    def _assess_attack_defense(self, home: float, away: float) -> str:
        """评估进攻防守对比"""
        if home > 1.3 and away < 0.8:
            return "主队进攻压制客队防守"
        elif away > 1.3 and home < 0.8:
            return "客队进攻压制主队防守"
        elif home > 1.2 and away > 1.2:
            return "对攻大战预期"
        elif home < 0.9 and away < 0.9:
            return "可能是一场防守大战"
        else:
            return "相对平衡的对决"

    def save_to_file(self, filepath: str = None):
        """保存xG数据到文件"""
        if filepath is None:
            filepath = os.path.join(DATA_DIR, "xg_database.json")

        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        with open(filepath, 'w') as f:
            json.dump({
                "data": self.data,
                "last_updated": datetime.now().isoformat(),
                "version": "1.0"
            }, f, ensure_ascii=False, indent=2)

        print(f"✅ xG数据已保存: {filepath}")


# ============ 测试 ============
if __name__ == "__main__":
    db = XGDatabase()

    print("=" * 60)
    print("📊 xG预期进球数据库测试")
    print("=" * 60)

    print(f"\n总计收录: {len(db.data)} 支球队xG数据")

    # 测试几个球队
    test_teams = ["Argentina", "Germany", "Japan", "Morocco"]

    print("\n📍 球队xG数据:")
    for team in test_teams:
        xg_data = db.get_team_xg(team)
        if xg_data:
            print(f"\n⚽ {team}:")
            print(f"   预期进球: {xg_data['xg_for']}")
            print(f"   预期失球: {xg_data['xg_against']}")
            print(f"   主场xG: {xg_data['home_away_split']['home']['xg_for']}")
            print(f"   客场xG: {xg_data['home_away_split']['away']['xg_for']}")

    # 测试比赛xG计算
    print("\n" + "=" * 60)
    print("📍 比赛xG计算测试")
    print("=" * 60)

    matchups = [
        ("Argentina", "Brazil"),
        ("Germany", "Japan"),
        ("Spain", "Morocco"),
    ]

    for home, away in matchups:
        result = db.calculate_match_xg(home, away)
        print(f"\n⚽ {home} vs {away}")
        print(f"   xG: {result['home_xg']} - {result['away_xg']}")
        print(f"   总xG: {result['total_xg']}")
        print(f"   胜平负: {result['probabilities']['home_win']:.1%} / {result['probabilities']['draw']:.1%} / {result['probabilities']['away_win']:.1%}")
        print(f"   首选比分: {result['score_probabilities'][0]['score']} ({result['score_probabilities'][0]['prob']:.1f}%)")

    # 进攻防守分析
    print("\n" + "=" * 60)
    print("📍 进攻vs防守分析")
    print("=" * 60)

    analysis = db.analyze_attack_vs_defense("Spain", "Italy")
    print(f"\n⚽ Spain vs Italy")
    print(f"   西班牙进攻: {analysis['home_attack']}, 防守: {analysis['home_defense']}")
    print(f"   意大利进攻: {analysis['away_attack']}, 防守: {analysis['away_defense']}")
    print(f"   评估: {analysis['assessment']}")

    # 保存数据
    print("\n" + "=" * 60)
    db.save_to_file()
