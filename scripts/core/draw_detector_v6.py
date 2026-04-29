#!/usr/bin/env python3
"""
V6 平局检测增强模块 — DeepSeek V4-Pro 博弈论逻辑
==============================================
新增三大平局信号:
1. qualify_on_draw — 平局即可出线的博弈策略
2. player_dependency_index — 动态缺阵降权
3. tournament_draw_triggers — 赛事阶段平局倾向
"""

import json, os, math
from typing import Dict, Tuple, Optional

class DrawDetectorV6:
    """V6平局检测器 — V4-Pro博弈论注入"""
    
    def __init__(self, data_dir: str = None):
        self.data_dir = data_dir or os.path.expanduser("~/hermes-world-cup/data/")
        self._load_data()
    
    def _load_data(self):
        """加载球队/赛事数据"""
        # 球员依赖度数据库
        self.player_dependency = {
            # 格式: "team": {"player": dependency_index(0-1)}
            # 依赖度 = 该球员贡献的进攻/防守比例
            "阿根廷": {"Lionel Messi": 0.42},
            "葡萄牙": {"Cristiano Ronaldo": 0.35},
            "法国": {"Kylian Mbappe": 0.38},
            "巴西": {"Vinicius Junior": 0.28, "Neymar": 0.22},
            "英格兰": {"Harry Kane": 0.30, "Jude Bellingham": 0.20},
            "西班牙": {"Lamine Yamal": 0.18, "Rodri": 0.25},
            "德国": {"Jamal Musiala": 0.20},
            "荷兰": {"Virgil van Dijk": 0.22},
            "比利时": {"Kevin De Bruyne": 0.30},
            "意大利": {"Nicolo Barella": 0.15},
        }
        
        # 小组赛出线形势数据库（需实时更新）
        self.group_standings = {}
        
        # 赛事平局历史
        self.tournament_draw_rates = {
            "FIFA World Cup": {"group": 0.245, "knockout": 0.185},
            "UEFA Euro": {"group": 0.35, "knockout": 0.22},
            "Copa America": {"group": 0.28, "knockout": 0.20},
            "AFC Asian Cup": {"group": 0.26, "knockout": 0.18},
        }
    
    def detect_draw_signals(self, home: str, away: str, elo_diff: float, 
                           stage: str = "group", tournament: str = "FIFA World Cup",
                           home_missing: list = None, away_missing: list = None,
                           home_can_qualify_draw: bool = False,
                           away_can_qualify_draw: bool = False) -> Dict:
        """
        核心: 多维度平局信号检测
        
        返回: draw_score(0-10) + 各信号详情
        """
        signals = {}
        total_score = 0.0
        
        # === 信号1: Elo接近度 (20分权重) ===
        elo_closeness = max(0, 1 - abs(elo_diff) / 200)
        elo_score = elo_closeness * 2.0
        signals["elo_closeness"] = {
            "value": round(elo_closeness, 2),
            "score": round(elo_score, 1),
            "desc": f"Elo差{abs(elo_diff):.0f} → 接近度{elo_closeness:.2f}"
        }
        total_score += elo_score
        
        # === 信号2: 平局出线博弈 (30分权重, 核心新增) ===
        qualify_score = 0.0
        if home_can_qualify_draw and away_can_qualify_draw:
            # 双方平局都出线 → 最高平局概率 (默契球)
            qualify_score = 3.0
            signals["qualify_on_draw"] = {
                "value": "双向",
                "score": 3.0,
                "desc": "⚠️ 双方平局均可出线 → 默契球高风险"
            }
        elif home_can_qualify_draw:
            qualify_score = 2.0
            signals["qualify_on_draw"] = {
                "value": "主队",
                "score": 2.0,
                "desc": f"{home}平局出线 → 保守策略, 求平优先"
            }
        elif away_can_qualify_draw:
            qualify_score = 2.0
            signals["qualify_on_draw"] = {
                "value": "客队",
                "score": 2.0,
                "desc": f"{away}平局出线 → 客场死守, 求平优先"
            }
        else:
            signals["qualify_on_draw"] = {
                "value": "无",
                "score": 0.0,
                "desc": "双方需争胜, 平局概率正常"
            }
        total_score += qualify_score
        
        # === 信号3: 球员依赖度降权 (25分权重, V4-Pro动态计算) ===
        dependency_score = self._calc_dependency_impact(home, away, home_missing, away_missing)
        signals["player_dependency"] = dependency_score
        total_score += dependency_score["score"]
        
        # === 信号4: 赛事阶段平局概率 (15分权重) ===
        stage_rates = self.tournament_draw_rates.get(tournament, {"group": 0.25, "knockout": 0.20})
        base_draw_rate = stage_rates.get(stage, 0.25)
        stage_score = base_draw_rate * 3.0  # 最高1.5分
        signals["stage_draw_rate"] = {
            "value": round(base_draw_rate, 3),
            "score": round(stage_score, 1),
            "desc": f"{tournament} {stage}阶段基线平局率{base_draw_rate:.1%}"
        }
        total_score += stage_score
        
        # === 信号5: 赔率平局异常 (10分权重) ===
        # 通过赔率市场判断: draw赔率低于3.0暗示市场预期平局
        signals["odds_draw_signal"] = {
            "value": "N/A",
            "score": 0.0,
            "desc": "需实时赔率数据(odds_tracker)"
        }
        
        return {
            "total_draw_score": round(total_score, 1),
            "max_score": 10.0,
            "signals": signals,
            "verdict": self._verdict(total_score),
            "recommendation": self._recommend(total_score, elo_diff, stage)
        }
    
    def _calc_dependency_impact(self, home: str, away: str, 
                                home_missing: list, away_missing: list) -> Dict:
        """V4-Pro: 动态依赖度降权 — 非线性计算"""
        home_impact = 0.0
        away_impact = 0.0
        
        if home_missing and home in self.player_dependency:
            deps = self.player_dependency[home]
            for player in home_missing:
                if player in deps:
                    dep = deps[player]
                    # 非线性: 依赖度>0.3时指数级放大影响
                    impact = dep ** 1.5 * 2.5  # 0.3→0.41分, 0.4→0.63分
                    home_impact += impact
        
        if away_missing and away in self.player_dependency:
            deps = self.player_dependency[away]
            for player in away_missing:
                if player in deps:
                    dep = deps[player]
                    impact = dep ** 1.5 * 2.5
                    away_impact += impact
        
        total_impact = min(2.5, home_impact + away_impact)
        
        desc_parts = []
        if home_impact > 0:
            desc_parts.append(f"{home}缺阵影响:{home_impact:.1f}")
        if away_impact > 0:
            desc_parts.append(f"{away}缺阵影响:{away_impact:.1f}")
        
        return {
            "value": ",".join(home_missing or []) + "|" + ",".join(away_missing or []),
            "score": round(total_impact, 1),
            "desc": "|".join(desc_parts) if desc_parts else "双方核心在阵"
        }
    
    def _verdict(self, score: float) -> str:
        if score >= 7.0: return "🔴 极高平局概率 (强烈建议双选)"
        if score >= 5.0: return "🟠 较高平局概率 (建议关注平局)"
        if score >= 3.0: return "🟡 中等平局概率"
        return "🟢 平局概率正常"
    
    def _recommend(self, score: float, elo_diff: float, stage: str) -> str:
        if stage == "knockout" and score >= 6.0:
            return "双选: 平局+弱队胜"
        if score >= 7.0:
            return "首选平局, 次选Elo优队"
        if score >= 5.0:
            return "平局值得下注, 配合小2.5球"
        return "正常预测, 按模型输出"


# ===== 集成到现有UnifiedPredictor的补丁 =====
def inject_into_predictor(predictor, detector: DrawDetectorV6 = None):
    """
    将V6平局检测注入现有UnifiedPredictor
    在 predict() 方法中调用 detector.detect_draw_signals()
    """
    if detector is None:
        detector = DrawDetectorV6()
    
    # 保存原始方法
    original_predict = type(predictor).predict
    
    def v6_predict(self, home, away, **kwargs):
        result = original_predict(self, home, away, **kwargs)
        
        # 提取elo差
        elo_home = kwargs.get('elo_home', getattr(self, 'elo_home', 1500))
        elo_away = kwargs.get('elo_away', getattr(self, 'elo_away', 1500))
        elo_diff = elo_home - elo_away
        
        # V6平局检测
        stage = kwargs.get('stage', 'group')
        draw_signals = detector.detect_draw_signals(
            home, away, elo_diff, stage=stage,
            home_missing=kwargs.get('home_missing', []),
            away_missing=kwargs.get('away_missing', []),
            home_can_qualify_draw=kwargs.get('home_can_qualify_draw', False),
            away_can_qualify_draw=kwargs.get('away_can_qualify_draw', False)
        )
        
        # 根据平局分数调整预测
        draw_score = draw_signals['total_draw_score']
        if draw_score >= 5.0:
            # 提高平局概率
            base_draw = result.get('draw_prob', 0.25)
            boost = min(0.15, draw_score * 0.02)
            result['draw_prob'] = base_draw + boost
            result['draw_prob_v6_boost'] = round(boost, 3)
            result['draw_signals_v6'] = draw_signals
        
        return result
    
    # 注入
    type(predictor).predict = v6_predict
    return detector


if __name__ == "__main__":
    detector = DrawDetectorV6()
    
    # 测试场景
    print("═══ V6平局检测测试 ═══\n")
    
    test_cases = [
        ("巴西", "阿根廷", 30, "group", ["Vinicius Junior"], [], True, False),
        ("葡萄牙", "法国", 15, "group", [], ["Kylian Mbappe"], True, True),
        ("英格兰", "德国", 50, "knockout", ["Harry Kane"], [], False, False),
        ("日本", "韩国", -10, "group", [], [], False, False),
    ]
    
    for home, away, elo_diff, stage, hm, am, hq, aq in test_cases:
        result = detector.detect_draw_signals(
            home, away, elo_diff, stage=stage,
            home_missing=hm, away_missing=am,
            home_can_qualify_draw=hq, away_can_qualify_draw=aq
        )
        print(f"{home} vs {away}")
        print(f"  Elo差:{elo_diff} | 阶段:{stage}")
        print(f"  缺阵: {hm}/{am} | 平局出线: {hq}/{aq}")
        print(f"  → {result['verdict']} (分数:{result['total_draw_score']}/10)")
        print(f"  → 建议: {result['recommendation']}")
        for k, v in result['signals'].items():
            if v['score'] > 0:
                print(f"    {k}: +{v['score']}分 — {v['desc']}")
        print()
