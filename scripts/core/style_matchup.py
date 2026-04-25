#!/usr/bin/env python3
"""
球队风格相克系统 v1.0
=====================
基于球队风格类型的相克关系调整预测

核心功能：
1. 球队风格分类（防守反击、控球渗透、高压逼抢等）
2. 风格相克矩阵
3. 根据对手风格调整概率
"""

import os
import json
from typing import Dict, List, Tuple, Optional

# ============ 路径配置 ============
BASE_DIR = os.path.expanduser("~/hermes-world-cup/")
DATA_DIR = os.path.join(BASE_DIR, "data/")


# ============ 球队风格定义 ============
# 基于球队特点和典型战术风格
TEAM_STYLES = {
    # 防守反击型
    "Italy": "counter_attack",
    "Portugal": "counter_attack",
    "Greece": "counter_attack",
    "Iceland": "counter_attack",
    "Iceland": "counter_attack",
    "Wales": "counter_attack",
    "Costa Rica": "counter_attack",
    "Morocco": "counter_attack",
    "Egypt": "counter_attack",
    "Saudi Arabia": "counter_attack",
    "Iran": "counter_attack",

    # 控球渗透型
    "Spain": "possession",
    "Barcelona": "possession",
    "Manchester City": "possession",
    "Argentina": "possession",
    "Brazil": "possession",
    "Germany": "possession",
    "Chelsea": "possession",

    # 高压逼抢型
    "Germany": "high_press",
    "Liverpool": "high_press",
    "Bayern Munich": "high_press",
    "Dortmund": "high_press",
    "Leeds": "high_press",
    "Marcelo's Real Madrid": "high_press",

    # 稳守突击型（介于防守和进攻之间）
    "France": "balanced",
    "England": "balanced",
    "Netherlands": "balanced",
    "Belgium": "balanced",
    "Croatia": "balanced",
    "Uruguay": "balanced",
    "Mexico": "balanced",
    "Colombia": "balanced",
    "Japan": "balanced",
    "South Korea": "balanced",
    "Australia": "balanced",

    # 直接进攻型
    "Brazil": "direct",
    "Netherlands": "direct",
    "Belgium": "direct",
    "Portugal": "direct",
    "Wales": "direct",
    "Sweden": "direct",
    "Norway": "direct",
    "Poland": "direct",
    "Austria": "direct",

    # 传统力量型
    "Brazil": "physical",
    "England": "physical",
    "Germany": "physical",
    "France": "physical",
    "Italy": "physical",
    "Netherlands": "physical",
    "Argentina": "physical",
    "Nigeria": "physical",
    "Cameroon": "physical",
    "Ghana": "physical",
    "Ivory Coast": "physical",
    "Senegal": "physical",
}


# ============ 风格相克矩阵 ============
# 正数 = 进攻方优势, 负数 = 防守方优势
# 格式: STYLE_MATCHUP[进攻方风格][防守方风格] = 胜率调整

STYLE_MATCHUP = {
    # 防守反击 vs ...
    "counter_attack": {
        "high_press": 0.08,     # 反击打高压逼抢很有效
        "possession": -0.05,    # 面对控球队容易被动
        "balanced": 0.03,       # 略占优势
        "direct": 0.0,          # 旗鼓相当
        "physical": -0.03,       # 身体对抗可能吃亏
    },

    # 高压逼抢 vs ...
    "high_press": {
        "counter_attack": -0.08,  # 被反击克制
        "possession": 0.05,        # 压迫控球队效果好
        "balanced": 0.03,         # 略占优势
        "direct": 0.05,           # 高压对直接进攻有效
        "physical": 0.0,          # 相当
    },

    # 控球渗透 vs ...
    "possession": {
        "counter_attack": 0.05,   # 控球让反击队没有空间
        "high_press": -0.05,     # 控球队怕高压
        "balanced": 0.03,         # 略占优势
        "direct": 0.0,            # 相当
        "physical": -0.03,        # 身体对抗可能吃亏
    },

    # 稳守突击 vs ...
    "balanced": {
        "counter_attack": -0.03,  # 被反击克制
        "high_press": -0.03,     # 略被压制
        "possession": -0.03,     # 略被控球压制
        "direct": 0.0,            # 相当
        "physical": 0.0,          # 相当
    },

    # 直接进攻 vs ...
    "direct": {
        "counter_attack": 0.0,    # 相当
        "high_press": -0.05,     # 直接进攻怕高压
        "possession": 0.0,        # 相当
        "balanced": 0.0,          # 相当
        "physical": 0.03,         # 略占身体优势
    },

    # 身体力量型 vs ...
    "physical": {
        "counter_attack": 0.03,   # 身体对抗反击队
        "high_press": 0.0,        # 相当
        "possession": 0.03,        # 身体对抗控球队
        "balanced": 0.0,          # 相当
        "direct": -0.03,          # 略被直接进攻压制
    },
}


class StyleMatchupAnalyzer:
    """
    球队风格相克分析器

    基于球队风格类型和相克关系调整比赛预测
    """

    def __init__(self):
        self.data_dir = DATA_DIR
        self.team_styles = self._load_team_styles()
        self.matchup_history = self._load_matchup_history()

    def _load_team_styles(self) -> Dict:
        """加载球队风格数据"""
        style_file = os.path.join(self.data_dir, "team_styles.json")
        if os.path.exists(style_file):
            try:
                with open(style_file, 'r') as f:
                    return json.load(f)
            except:
                pass

        # 使用默认风格
        return TEAM_STYLES.copy()

    def _load_matchup_history(self) -> Dict:
        """加载历史对战数据"""
        history_file = os.path.join(self.data_dir, "style_matchup_history.json")
        if os.path.exists(history_file):
            try:
                with open(history_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def save_team_styles(self):
        """保存球队风格数据"""
        style_file = os.path.join(self.data_dir, "team_styles.json")
        os.makedirs(os.path.dirname(style_file), exist_ok=True)
        with open(style_file, 'w') as f:
            json.dump(self.team_styles, f, ensure_ascii=False, indent=2)

    def get_team_style(self, team: str) -> str:
        """获取球队风格"""
        # 精确匹配
        if team in self.team_styles:
            return self.team_styles[team]

        # 模糊匹配（包含检查）
        for known_team, style in self.team_styles.items():
            if known_team.lower() in team.lower() or team.lower() in known_team.lower():
                return style

        # 默认风格（根据队伍特性推断）
        # 弱队默认防守反击，强队默认控球或均衡
        return "balanced"  # 默认均衡风格

    def set_team_style(self, team: str, style: str):
        """设置球队风格"""
        valid_styles = ["counter_attack", "high_press", "possession", "balanced", "direct", "physical"]
        if style not in valid_styles:
            raise ValueError(f"无效风格: {style}. 必须是 {valid_styles}")

        self.team_styles[team] = style

    def analyze_matchup(self, home_team: str, away_team: str) -> Dict:
        """
        分析比赛双方的风格相克

        Args:
            home_team: 主队
            away_team: 客队

        Returns:
            风格相克分析报告
        """
        home_style = self.get_team_style(home_team)
        away_style = self.get_team_style(away_team)

        # 主队进攻时的相克（主队 vs 客队防守）
        home_attack_bonus = STYLE_MATCHUP.get(home_style, {}).get(away_style, 0)

        # 客队进攻时的相克（客队 vs 主队防守）
        away_attack_bonus = STYLE_MATCHUP.get(away_style, {}).get(home_style, 0)

        # 综合调整
        # 主场进攻时：主队优势 = 主场风格优势 - 客队反击威胁
        home_advantage = home_attack_bonus - away_attack_bonus * 0.5

        # 解释
        interpretations = self._interpret_matchup(home_style, away_style, home_advantage)

        return {
            "home_team": home_team,
            "away_team": away_team,
            "home_style": home_style,
            "away_style": away_style,
            "home_attack_bonus": home_attack_bonus,
            "away_attack_bonus": away_attack_bonus,
            "home_advantage": home_advantage,
            "style_description": f"{self._style_to_chinese(home_style)} vs {self._style_to_chinese(away_style)}",
            "interpretations": interpretations,
            "recommendation": self._get_recommendation(home_advantage)
        }

    def _style_to_chinese(self, style: str) -> str:
        """风格名称翻译"""
        translations = {
            "counter_attack": "防守反击型",
            "high_press": "高压逼抢型",
            "possession": "控球渗透型",
            "balanced": "稳守突击型",
            "direct": "直接进攻型",
            "physical": "身体力量型",
        }
        return translations.get(style, style)

    def _interpret_matchup(self, home_style: str, away_style: str, advantage: float) -> List[str]:
        """解释风格相克"""
        interpretations = []

        # 主队风格 vs 客队风格
        if home_style == "counter_attack" and away_style == "high_press":
            interpretations.append("主队防守反击克制客队高压逼抢")
        elif home_style == "high_press" and away_style == "counter_attack":
            interpretations.append("主队高压逼抢被客队防守反击克制")
        elif home_style == "possession" and away_style == "high_press":
            interpretations.append("主队控球被客队高压逼抢压制")
        elif home_style == "high_press" and away_style == "possession":
            interpretations.append("主队高压逼抢压制客队控球")
        elif home_style == "counter_attack" and away_style == "possession":
            interpretations.append("主队防守反击对阵客队控球")

        # 优势程度
        if abs(advantage) > 0.05:
            interpretations.append(f"{'主队' if advantage > 0 else '客队'}风格优势明显")
        elif abs(advantage) > 0.02:
            interpretations.append(f"{'主队' if advantage > 0 else '客队'}风格略有优势")

        if not interpretations:
            interpretations.append("双方风格旗鼓相当")

        return interpretations

    def _get_recommendation(self, advantage: float) -> str:
        """根据优势给出推荐"""
        if advantage > 0.05:
            return "主队风格优势明显"
        elif advantage > 0.02:
            return "主队风格略有优势"
        elif advantage > -0.02:
            return "双方风格均衡"
        elif advantage > -0.05:
            return "客队风格略有优势"
        else:
            return "客队风格优势明显"

    def apply_style_adjustment(self,
                               home_win_prob: float,
                               draw_prob: float,
                               away_win_prob: float,
                               home_team: str,
                               away_team: str) -> Dict:
        """
        应用风格相克调整到概率

        Args:
            home_win_prob: 原始主队胜率
            draw_prob: 原始平局概率
            away_win_prob: 原始客队胜率
            home_team: 主队
            away_team: 客队

        Returns:
            调整后的概率和分析
        """
        analysis = self.analyze_matchup(home_team, away_team)

        # 风格调整因子
        # 风格优势通常带来3-8%的胜率提升
        style_factor = analysis["home_advantage"]

        # 应用调整
        adj_home = home_win_prob + style_factor * 0.5
        adj_away = away_win_prob - style_factor * 0.5

        # 平局概率不变
        adj_draw = draw_prob

        # 归一化
        total = adj_home + adj_draw + adj_away
        if total > 0:
            adj_home /= total
            adj_draw /= total
            adj_away /= total

        return {
            "adjusted_home": adj_home,
            "adjusted_draw": adj_draw,
            "adjusted_away": adj_away,
            "style_analysis": analysis,
            "adjustment_factor": style_factor
        }

    def get_style_advantages(self, team: str) -> Dict:
        """获取球队对各类风格的相对优势"""
        style = self.get_team_style(team)

        advantages = {}
        for opponent_style, bonus in STYLE_MATCHUP.get(style, {}).items():
            advantages[opponent_style] = {
                "style": opponent_style,
                "bonus": bonus,
                "description": self._style_to_chinese(opponent_style)
            }

        return {
            "team": team,
            "own_style": style,
            "own_style_chinese": self._style_to_chinese(style),
            "advantages": advantages
        }


# ============ 测试代码 ============
if __name__ == "__main__":
    analyzer = StyleMatchupAnalyzer()

    print("=" * 60)
    print("球队风格相克测试")
    print("=" * 60)

    # 测试1：意大利（防守反击）vs 德国（高压逼抢）
    print("\n测试1：意大利 vs 德国")
    result = analyzer.analyze_matchup("Italy", "Germany")
    print(f"主队风格: {result['home_style_chinese'] if 'home_style_chinese' in str(analyzer._style_to_chinese(result['home_style'])) else result['home_style']}")
    print(f"客队风格: {result['away_style']}")
    print(f"主队优势: {result['home_advantage']:+.3f}")
    print(f"推荐: {result['recommendation']}")

    # 测试2：西班牙（控球）vs 意大利（防守反击）
    print("\n测试2：西班牙 vs 意大利")
    result = analyzer.analyze_matchup("Spain", "Italy")
    print(f"主队风格: {result['home_style']}")
    print(f"客队风格: {result['away_style']}")
    print(f"主队优势: {result['home_advantage']:+.3f}")
    print(f"解读: {result['interpretations']}")

    # 测试3：应用风格调整
    print("\n测试3：应用风格调整")
    print("原始概率: 主队 50% | 平局 25% | 客队 25%")

    adjusted = analyzer.apply_style_adjustment(
        0.50, 0.25, 0.25,
        "Spain", "Italy"
    )

    print(f"调整后: 主队 {adjusted['adjusted_home']:.1%} | 平局 {adjusted['adjusted_draw']:.1%} | 客队 {adjusted['adjusted_away']:.1%}")
    print(f"调整因子: {adjusted['adjustment_factor']:+.3f}")

    # 测试4：球队对各类风格的优势
    print("\n测试4：西班牙对各类风格的相对优势")
    advantages = analyzer.get_style_advantages("Spain")
    print(f"西班牙风格: {advantages['own_style_chinese']}")
    for opp, data in advantages['advantages'].items():
        print(f"  vs {data['description']}: {data['bonus']:+.2f}")
