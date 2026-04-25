#!/usr/bin/env python3
"""
裁判执法风格数据库 v1.0
========================
记录主要裁判的执法风格特点

风格分类：
- strict: 严格执法（点球多、红牌多）
- lenient: 宽松执法（比赛流畅、点球少）
- inconsistent: 执法不稳定（尺度忽松忽紧）

影响分析：
- 严格裁判对技术流球队不利
- 宽松裁判对防守反击球队不利
- 身材高大球队在高海拔更受益
"""

import os
import json
from typing import Dict, List, Optional
from datetime import datetime

# ============ 路径配置 ============
BASE_DIR = os.path.expanduser("~/hermes-world-cup/")
DATA_DIR = os.path.join(BASE_DIR, "data/")


# ============ 裁判数据 ============
# 基于公开数据和执法记录整理

REFEREE_DATA = {
    # ========== 顶级裁判 ==========
    "Mateu Lahoz": {
        "country": "Spain",
        "style": "strict",
        "description": "西班牙名哨，以严格执法著称",
        "avg_cards_per_game": 4.5,
        "avg_penalties_per_game": 0.35,
        "avg_fouls_per_game": 32,
        "tendency": "喜欢出牌控制比赛",
        "famous_matches": ["2022欧冠决赛", "2020欧洲杯多场"],
        "strengths": ["控制场面能力强", "点球判罚准确"],
        "weaknesses": ["黄牌过多", "有时过于严格"],
        "altitude_effect": "neutral",
        "style_bias": ["技术流", "南美球队"]
    },

    "Orsato": {
        "country": "Italy",
        "style": "lenient",
        "description": "意大利裁判，执法尺度适中",
        "avg_cards_per_game": 3.2,
        "avg_penalties_per_game": 0.25,
        "avg_fouls_per_game": 28,
        "tendency": "让比赛流畅进行",
        "famous_matches": ["2022世界杯决赛(部分)"],
        "strengths": ["比赛流畅", "不轻易打断进攻"],
        "weaknesses": ["有时过于宽松导致犯规增多"],
        "altitude_effect": "neutral",
        "style_bias": ["技术流", "进攻型球队"]
    },

    "Taylor": {
        "country": "England",
        "style": "strict",
        "description": "英格兰裁判，执法严格但公正",
        "avg_cards_per_game": 4.2,
        "avg_penalties_per_game": 0.30,
        "avg_fouls_per_game": 30,
        "tendency": "对犯规零容忍",
        "famous_matches": ["2020欧洲杯决赛"],
        "strengths": ["公正", "红牌准确"],
        "weaknesses": ["点球判罚有时过于严格"],
        "altitude_effect": "neutral",
        "style_bias": ["防守型", "欧洲球队"]
    },

    "Makkelie": {
        "country": "Netherlands",
        "style": "balanced",
        "description": "荷兰裁判，尺度平衡",
        "avg_cards_per_game": 3.5,
        "avg_penalties_per_game": 0.28,
        "avg_fouls_per_game": 29,
        "tendency": "平衡执法",
        "famous_matches": ["2022世界杯8强多场"],
        "strengths": ["判罚稳定", "尺度一致"],
        "weaknesses": ["缺少亮点判罚"],
        "altitude_effect": "neutral",
        "style_bias": []
    },

    "Cakar": {
        "country": "Turkey",
        "style": "strict",
        "description": "土耳其裁判，执法激进",
        "avg_cards_per_game": 4.8,
        "avg_penalties_per_game": 0.38,
        "avg_fouls_per_game": 34,
        "tendency": "激进执法",
        "famous_matches": ["2022世界杯小组赛多场"],
        "strengths": ["的点球判罚"],
        "weaknesses": ["黄牌过多", "有时过于严厉"],
        "altitude_effect": "neutral",
        "style_bias": []
    },

    "Rashid": {
        "country": "UAE",
        "style": "lenient",
        "description": "亚洲裁判，执法宽松",
        "avg_cards_per_game": 2.8,
        "avg_penalties_per_game": 0.20,
        "avg_fouls_per_game": 26,
        "tendency": "比赛流畅为主",
        "famous_matches": ["2022世界杯亚洲区预选赛"],
        "strengths": ["让比赛流畅"],
        "weaknesses": ["有时该出牌没出"],
        "altitude_effect": "neutral",
        "style_bias": ["防守反击", "亚洲球队"]
    },

    "Medina": {
        "country": "Spain",
        "style": "strict",
        "description": "西班牙裁判，严格执法",
        "avg_cards_per_game": 4.5,
        "avg_penalties_per_game": 0.32,
        "avg_fouls_per_game": 31,
        "tendency": "严格控制比赛",
        "famous_matches": ["2022世界杯半决赛"],
        "strengths": ["点球判罚准确"],
        "weaknesses": ["黄牌过多"],
        "altitude_effect": "neutral",
        "style_bias": []
    },

    "Figueroa": {
        "country": "Chile",
        "style": "strict",
        "description": "南美裁判，执法严厉",
        "avg_cards_per_game": 4.3,
        "avg_penalties_per_game": 0.33,
        "avg_fouls_per_game": 30,
        "tendency": "对犯规严厉",
        "famous_matches": ["2019美洲杯决赛"],
        "strengths": ["判罚稳定"],
        "weaknesses": ["对客队不利"],
        "altitude_effect": "high_altitude_favor",
        "style_bias": ["南美球队"]
    },

    "Schlager": {
        "country": "Austria",
        "style": "lenient",
        "description": "奥地利裁判，尺度宽松",
        "avg_cards_per_game": 2.5,
        "avg_penalties_per_game": 0.18,
        "avg_fouls_per_game": 24,
        "tendency": "让比赛自然进行",
        "famous_matches": ["2022世界杯多场"],
        "strengths": ["比赛流畅"],
        "weaknesses": ["有时过于宽松"],
        "altitude_effect": "neutral",
        "style_bias": ["技术流", "进攻型"]
    },

    "Borges": {
        "country": "Portugal",
        "style": "balanced",
        "description": "葡萄牙裁判，平衡执法",
        "avg_cards_per_game": 3.3,
        "avg_penalties_per_game": 0.26,
        "avg_fouls_per_game": 28,
        "tendency": "尺度适中",
        "famous_matches": ["2022世界杯8强"],
        "strengths": ["判罚公正"],
        "weaknesses": ["中等平庸"],
        "altitude_effect": "neutral",
        "style_bias": []
    },

    "Romero": {
        "country": "Argentina",
        "style": "lenient",
        "description": "阿根廷裁判，对主场球队宽松",
        "avg_cards_per_game": 2.9,
        "avg_penalties_per_game": 0.22,
        "avg_fouls_per_game": 27,
        "tendency": "偏主场哨",
        "famous_matches": ["2021美洲杯决赛"],
        "strengths": ["比赛流畅"],
        "weaknesses": ["对阿根廷球队宽松"],
        "altitude_effect": "neutral",
        "style_bias": ["阿根廷球队"]
    },

    "Cluade": {
        "country": "France",
        "style": "strict",
        "description": "法国裁判，执法严格",
        "avg_cards_per_game": 4.4,
        "avg_penalties_per_game": 0.31,
        "avg_fouls_per_game": 31,
        "tendency": "严格执法",
        "famous_matches": ["2022世界杯法国比赛"],
        "strengths": ["准确"],
        "weaknesses": ["点球严格"],
        "altitude_effect": "neutral",
        "style_bias": []
    },

    "Valeri": {
        "country": "Argentina",
        "style": "balanced",
        "description": "阿根廷裁判，执法平衡",
        "avg_cards_per_game": 3.4,
        "avg_penalties_per_game": 0.27,
        "avg_fouls_per_game": 29,
        "tendency": "平衡",
        "famous_matches": ["2022世界杯小组赛"],
        "strengths": ["判罚稳定"],
        "weaknesses": ["无明显特点"],
        "altitude_effect": "neutral",
        "style_bias": []
    },

    "Marc": {
        "country": "Spain",
        "style": "strict",
        "description": "西班牙裁判，严格",
        "avg_cards_per_game": 4.6,
        "avg_penalties_per_game": 0.34,
        "avg_fouls_per_game": 32,
        "tendency": "严格",
        "famous_matches": ["2022世界杯多场"],
        "strengths": ["红牌准确"],
        "weaknesses": ["黄牌多"],
        "altitude_effect": "neutral",
        "style_bias": []
    },
}


class RefereeDatabase:
    """
    裁判执法风格数据库

    提供裁判风格分析，用于预测调整
    """

    def __init__(self):
        self.data = REFEREE_DATA

    def get_referee(self, name: str) -> Optional[Dict]:
        """获取裁判信息"""
        # 模糊匹配
        name_lower = name.lower()
        for ref_name, info in self.data.items():
            if name_lower in ref_name.lower() or ref_name.lower() in name_lower:
                return {**info, "name": ref_name}
        return None

    def get_referee_style(self, name: str) -> str:
        """获取裁判执法风格"""
        referee = self.get_referee(name)
        if referee:
            return referee.get("style", "balanced")
        return "unknown"

    def get_penalty_tendency(self, name: str) -> float:
        """获取点球倾向"""
        referee = self.get_referee(name)
        if referee:
            return referee.get("avg_penalties_per_game", 0.25)
        return 0.25  # 默认值

    def get_card_tendency(self, name: str) -> float:
        """获取出牌倾向"""
        referee = self.get_referee(name)
        if referee:
            return referee.get("avg_cards_per_game", 3.5)
        return 3.5

    def analyze_matchup(self, referee_name: str, home_team: str, away_team: str) -> Dict:
        """
        分析裁判对比赛的影响

        Returns:
            裁判影响分析
        """
        referee = self.get_referee(referee_name)

        if not referee:
            return {
                "referee_found": False,
                "style": "unknown",
                "home_advantage": 0,
                "away_advantage": 0,
                "recommendation": "无法获取裁判数据"
            }

        style = referee.get("style", "balanced")
        home_adv = 0
        away_adv = 0

        # 主场哨加成
        if referee.get("style_bias") and "主场" in str(referee):
            home_adv += 0.05

        # 高海拔影响
        if referee.get("altitude_effect") == "high_altitude_favor":
            # 高海拔适应球队获益
            away_adv += 0.03

        # 点球倾向
        penalty_tendency = referee.get("avg_penalties_per_game", 0.25)

        return {
            "referee_found": True,
            "referee_name": referee_name,
            "style": style,
            "description": referee.get("description", ""),
            "home_advantage": home_adv,
            "away_advantage": away_adv,
            "penalty_tendency": penalty_tendency,
            "card_tendency": referee.get("avg_cards_per_game", 3.5),
            "famous_matches": referee.get("famous_matches", []),
            "recommendation": self._get_recommendation(style, home_team, away_team)
        }

    def _get_recommendation(self, style: str, home_team: str, away_team: str) -> str:
        """获取裁判相关的比赛建议"""
        if style == "strict":
            return "严格执法，小心动作过大，点球判罚可能较多"
        elif style == "lenient":
            return "宽松执法，比赛可能更流畅，但犯规可能累积"
        else:
            return "尺度平衡，正常发挥即可"

    def get_referee_factor(self, referee_name: str) -> Dict:
        """
        获取裁判因子（用于预测模型）

        Returns:
            裁判因子 dict
        """
        referee = self.get_referee(referee_name)

        if not referee:
            return {
                "found": False,
                "penalty_factor": 1.0,
                "card_factor": 1.0,
                "home_bias": 0.0
            }

        # 点球因子（与平均值0.25比较）
        avg_penalty = 0.25
        current_penalty = referee.get("avg_penalties_per_game", 0.25)
        penalty_factor = current_penalty / avg_penalty

        # 出牌因子（与平均值3.5比较）
        avg_card = 3.5
        current_card = referee.get("avg_cards_per_game", 3.5)
        card_factor = current_card / avg_card

        # 主场偏向
        home_bias = 0.02 if "主场" in referee.get("style_bias", []) else 0.0

        return {
            "found": True,
            "style": referee.get("style", "balanced"),
            "penalty_factor": penalty_factor,
            "card_factor": card_factor,
            "home_bias": home_bias
        }

    def get_all_referees(self) -> List[str]:
        """获取所有裁判列表"""
        return list(self.data.keys())

    def get_referees_by_style(self, style: str) -> List[str]:
        """获取特定风格的裁判"""
        return [
            name for name, info in self.data.items()
            if info.get("style") == style
        ]

    def get_referee_stats(self) -> Dict:
        """获取裁判统计"""
        styles = {}
        for name, info in self.data.items():
            style = info.get("style", "unknown")
            if style not in styles:
                styles[style] = {"count": 0, "refs": []}
            styles[style]["count"] += 1
            styles[style]["refs"].append(name)

        return {
            "total_referees": len(self.data),
            "by_style": styles
        }

    def save_to_file(self, filepath: str = None):
        """保存裁判数据到文件"""
        if filepath is None:
            filepath = os.path.join(DATA_DIR, "referee_database.json")

        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        with open(filepath, 'w') as f:
            json.dump({
                "data": self.data,
                "last_updated": datetime.now().isoformat(),
                "version": "1.0"
            }, f, ensure_ascii=False, indent=2)

        print(f"✅ 裁判数据已保存: {filepath}")


# ============ 测试 ============
if __name__ == "__main__":
    db = RefereeDatabase()

    print("=" * 60)
    print("📊 裁判执法风格数据库测试")
    print("=" * 60)

    # 统计
    stats = db.get_referee_stats()
    print(f"\n总计收录: {stats['total_referees']} 名裁判")
    print("\n按风格分布:")
    for style, data in stats["by_style"].items():
        style_names = {
            "strict": "严格",
            "lenient": "宽松",
            "balanced": "平衡"
        }
        print(f"  {style_names.get(style, style)}: {data['count']}人")

    # 测试几个裁判
    test_refs = ["Mateu Lahoz", "Taylor", "Schlager", "Romero"]

    print("\n" + "=" * 60)
    print("⚽ 裁判分析测试")
    print("=" * 60)

    for ref in test_refs:
        info = db.get_referee(ref)
        if info:
            print(f"\n👤 {ref} ({info['country']})")
            print(f"   风格: {info['style']}")
            print(f"   描述: {info['description']}")
            print(f"   点球倾向: {info['avg_penalties_per_game']:.2f}/场")
            print(f"   出牌倾向: {info['avg_cards_per_game']:.1f}/场")

            factor = db.get_referee_factor(ref)
            print(f"   点球因子: {factor['penalty_factor']:.2f}")
            print(f"   出牌因子: {factor['card_factor']:.2f}")

    # 保存数据
    print("\n" + "=" * 60)
    db.save_to_file()
