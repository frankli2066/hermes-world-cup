#!/usr/bin/env python3
"""
比赛级别调整模块 v1.0

针对不同比赛阶段（小组赛/淘汰赛/决赛）调整预测权重

核心洞察：
1. 淘汰赛：经验更重要、压力更大、更保守（平局概率升高）
2. 决赛：心理因素最关键、明星球员作用最大化
3. 小组赛：可以接受平局、轮换可能影响发挥

调整维度：
- 平局概率：淘汰赛 > 决赛 > 小组赛
- 经验权重：淘汰赛/决赛 > 小组赛
- 明星球员影响：决赛 > 淘汰赛 > 小组赛
- 防守倾向：淘汰赛最强，决赛次之，小组赛最开放
"""

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import math


# ============ 比赛阶段定义 ============

@dataclass
class MatchStage:
    """比赛阶段配置"""
    name: str
    min_goals_home: float  # 最低预期进球（主场）
    min_goals_away: float  # 最低预期进球（客场）
    experience_weight: float  # 经验权重倍数
    star_player_weight: float  # 明星球员权重倍数
    draw_prob_boost: float  # 平局概率加成
    upset_factor: float  # 冷门概率因子


# 预定义比赛阶段
MATCH_STAGES = {
    "group": MatchStage(
        name="小组赛",
        min_goals_home=0.8,
        min_goals_away=0.6,
        experience_weight=1.0,
        star_player_weight=1.0,
        draw_prob_boost=0.0,  # 小组赛平局正常
        upset_factor=1.0,
    ),
    "round_of_16": MatchStage(
        name="16强",
        min_goals_home=0.9,
        min_goals_away=0.7,
        experience_weight=1.15,
        star_player_weight=1.15,
        draw_prob_boost=0.08,  # 淘汰赛更保守
        upset_factor=1.1,
    ),
    "quarter": MatchStage(
        name="8强",
        min_goals_home=0.85,
        min_goals_away=0.7,
        experience_weight=1.2,
        star_player_weight=1.2,
        draw_prob_boost=0.10,
        upset_factor=1.15,
    ),
    "semi": MatchStage(
        name="半决赛",
        min_goals_home=0.8,
        min_goals_away=0.65,
        experience_weight=1.3,
        star_player_weight=1.35,
        draw_prob_boost=0.12,
        upset_factor=1.2,
    ),
    "third_place": MatchStage(
        name="三四名决赛",
        min_goals_home=1.0,
        min_goals_away=0.9,
        experience_weight=0.9,  # 输了反而可能更放开
        star_player_weight=1.0,
        draw_prob_boost=0.0,
        upset_factor=1.1,
    ),
    "final": MatchStage(
        name="决赛",
        min_goals_home=0.75,
        min_goals_away=0.6,
        experience_weight=1.4,
        star_player_weight=1.5,  # 决赛靠明星
        draw_prob_boost=0.15,  # 决赛最容易平局
        upset_factor=1.3,  # 决赛冷门最多
    ),
}


# ============ 比赛级别调整器 ============

class MatchStageAdjuster:
    """
    比赛级别调整器

    根据比赛阶段调整预测参数
    """

    def __init__(self):
        self.stages = MATCH_STAGES

    def get_stage(self, stage_name: str) -> MatchStage:
        """获取比赛阶段配置"""
        return self.stages.get(stage_name, self.stages["group"])

    def adjust_xg(
        self,
        xg_home: float,
        xg_away: float,
        stage_name: str = "group",
    ) -> Tuple[float, float]:
        """
        根据比赛阶段调整xG预期进球

        淘汰赛和决赛：进球数普遍偏低
        决赛：尤其保守
        """
        stage = self.get_stage(stage_name)

        # 最低进球保障
        adj_home = max(xg_home, stage.min_goals_home)
        adj_away = max(xg_away, stage.min_goals_away)

        # 决赛：进一步压低（决赛往往0-0进加时）
        if stage_name == "final":
            adj_home *= 0.85
            adj_away *= 0.85

        # 淘汰赛：稍微压低
        elif stage_name in ("semi", "quarter"):
            adj_home *= 0.92
            adj_away *= 0.92

        return (adj_home, adj_away)

    def adjust_draw_probability(
        self,
        base_draw_prob: float,
        stage_name: str = "group",
    ) -> float:
        """
        根据比赛阶段调整平局概率

        决赛最容易平局（很多决赛0-0进加时）
        淘汰赛其次
        小组赛最低
        """
        stage = self.get_stage(stage_name)

        # 基础平局概率 + 阶段加成
        adjusted = base_draw_prob + stage.draw_prob_boost

        # 限制在合理范围
        return min(adjusted, 0.45)  # 平局概率最高不超过45%

    def adjust_win_probability(
        self,
        prob_home: float,
        prob_away: float,
        prob_draw: float,
        stage_name: str = "group",
        home_team: str = "",
        away_team: str = "",
        home_stars_important: float = 1.0,  # 0-2, 明星球员重要性
        away_stars_important: float = 1.0,
    ) -> Tuple[float, float, float]:
        """
        根据比赛阶段调整胜平负概率

        Args:
            prob_*: 基础概率
            stage_name: 比赛阶段
            home/away_team: 球队名称
            home/away_stars_important: 明星球员重要性 (0-2)
        """
        stage = self.get_stage(stage_name)

        # 1. 经验加成
        # 有经验的球队在淘汰赛/决赛更有优势
        # （这里简化处理，假设experience已经包含在基础概率中）

        # 2. 明星球员加成（决赛最关键）
        star_weight = stage.star_player_weight
        if star_weight > 1.0:
            # 决赛：明星球员强的队伍概率提升
            # 简化：给主队+2%，给客队+2%（按重要性比例）
            star_boost_home = (star_weight - 1.0) * 0.02 * home_stars_important
            star_boost_away = (star_weight - 1.0) * 0.02 * away_stars_important

            # 从平局概率中扣除
            total_boost = star_boost_home + star_boost_away
            if total_boost > 0 and prob_draw > total_boost:
                prob_draw -= total_boost
                prob_home += star_boost_home
                prob_away += star_boost_away

        # 3. 平局概率加成
        draw_boost = stage.draw_prob_boost
        if draw_boost > 0:
            # 从胜/负概率中扣除，加到平局
            total_prob = prob_home + prob_away + prob_draw
            # 按当前胜平负比例分配平局增量
            win_share = prob_home / (prob_home + prob_away) if (prob_home + prob_away) > 0 else 0.5
            draw_increase = draw_boost * total_prob

            prob_home -= draw_increase * win_share * 0.5
            prob_away -= draw_increase * (1 - win_share) * 0.5
            prob_draw += draw_increase * 0.8  # 80%给平局

        # 归一化
        total = prob_home + prob_away + prob_draw
        if total > 0:
            prob_home /= total
            prob_away /= total
            prob_draw /= total

        return (prob_home, prob_draw, prob_away)

    def get_upset_multiplier(
        self,
        favorite_prob: float,
        stage_name: str = "group",
    ) -> float:
        """
        获取冷门概率倍数

        决赛最容易出冷门（如2004希腊、2016法国...好吧法国赢了）
        2004希腊夺冠：赔率1/80 → 决赛冷门之最
        """
        stage = self.get_stage(stage_name)

        # 基础冷门概率 = 1 - 热门赢的概率
        base_upset_prob = 1 - favorite_prob

        # 阶段加成
        upset_prob = base_upset_prob * stage.upset_factor

        # 限制在合理范围
        return min(upset_prob, 0.5)

    def predict_score_range(
        self,
        xg_home: float,
        xg_away: float,
        stage_name: str = "group",
    ) -> Dict:
        """
        预测比分范围

        根据比赛阶段给出合理的比分预测范围
        """
        adj_home, adj_away = self.adjust_xg(xg_home, xg_away, stage_name)

        # 决赛/淘汰赛比分普遍偏低
        if stage_name in ("final", "semi"):
            # 常见：0-0, 1-0, 0-1, 1-1, 加时赛
            likely_home = round(adj_home * 0.8)
            likely_away = round(adj_away * 0.8)
        elif stage_name in ("quarter", "round_of_16"):
            # 1-0, 2-0, 1-1, 0-1, 2-1
            likely_home = round(adj_home * 0.9)
            likely_away = round(adj_away * 0.9)
        else:
            # 小组赛最开放
            likely_home = round(adj_home)
            likely_away = round(adj_away)

        return {
            "expected_home": likely_home,
            "expected_away": likely_away,
            "most_likely_score": f"{likely_home}-{likely_away}",
            "stage": self.stages[stage_name].name if stage_name in self.stages else "未知",
        }


# ============ 测试 ============

if __name__ == "__main__":
    adjuster = MatchStageAdjuster()

    print("=" * 60)
    print("🏆 比赛级别调整测试")
    print("=" * 60)

    # 测试xG调整
    print("\n1. xG调整（基础：Home 1.5, Away 1.0）:")
    base_home, base_away = 1.5, 1.0
    for stage in ["group", "round_of_16", "quarter", "semi", "final"]:
        adj = adjuster.adjust_xg(base_home, base_away, stage)
        stage_info = adjuster.get_stage(stage)
        print(f"   {stage_info.name}: {adj[0]:.2f} - {adj[1]:.2f}")

    # 测试平局概率调整
    print("\n2. 平局概率调整（基础25%）:")
    base_draw = 0.25
    for stage in ["group", "round_of_16", "semi", "final"]:
        adj = adjuster.adjust_draw_probability(base_draw, stage)
        stage_info = adjuster.get_stage(stage)
        print(f"   {stage_info.name}: {base_draw*100:.0f}% → {adj*100:.1f}% (+{(adj-base_draw)*100:.1f}%)")

    # 测试比分范围
    print("\n3. 比分范围预测:")
    for stage in ["group", "semi", "final"]:
        result = adjuster.predict_score_range(1.5, 1.0, stage)
        print(f"   {result['stage']}: {result['most_likely_score']}")

    # 测试冷门倍数
    print("\n4. 冷门概率（热门胜率60%时）:")
    for stage in ["group", "semi", "final"]:
        upset = adjuster.get_upset_multiplier(0.6, stage)
        stage_info = adjuster.get_stage(stage)
        print(f"   {stage_info.name}: 冷门概率 {upset*100:.1f}% (倍数 {stage_info.upset_factor:.2f})")

    print("\n" + "=" * 60)
