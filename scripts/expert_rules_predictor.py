"""
专家规则引擎
基于历史数据和专家知识的高级规则
"""
import sys
sys.path.insert(0, 'core')
sys.path.insert(0, '.')

from unified_predictor import UnifiedPredictor
from tournament_data import TournamentDataCollector
from team_data import TeamDataManager
from h2h_database import H2HDatabase
from datetime import datetime, timedelta


class ExpertRulesPredictor:
    """专家规则预测器"""

    def __init__(self):
        self.rule_predictor = UnifiedPredictor()
        self.team_data = TeamDataManager()
        self.h2h = H2HDatabase()

    def apply_expert_rules(self, home: str, away: str, match_stage: str, probs: dict) -> dict:
        """应用专家规则来调整概率"""
        result = probs.copy()

        home_elo = self.team_data.get_elo(home)
        away_elo = self.team_data.get_elo(away)
        elo_diff = abs(home_elo - away_elo)

        # 规则1: 淘汰赛阶段，强队优势更大
        if match_stage in ['16', 'round16', '8', 'quarter', '4', 'semi', 'final']:
            if home_elo > away_elo and elo_diff > 100:
                # 强队主场打淘汰赛，更值得信任
                result['home_win'] *= 1.1
            elif away_elo > home_elo and elo_diff > 100:
                result['away_win'] *= 1.1

        # 规则2: H2H显示高平局率时增加平局
        stats = self.h2h.get_h2h_stats(home, away)
        if stats['total'] >= 2:
            draw_rate = stats['draws'] / stats['total']
            if draw_rate >= 0.5:
                # 50%以上平局率，大幅增加平局
                result['draw'] *= 1.3
            elif draw_rate >= 0.33:
                result['draw'] *= 1.15

        # 规则3: Elo差距极大的比赛，平局概率降低
        if elo_diff > 200:
            # 悬殊差距，减少平局
            result['draw'] *= 0.85

        # 规则4: 积分接近时(小组赛)，平局概率增加
        # 这个需要知道具体积分，暂时用主胜概率来判断
        if result['home_win'] > 0.45 and result['home_win'] < 0.55:
            # 中等信心区域，可能是实力接近的比赛
            result['draw'] *= 1.1

        # 规则5: 排名接近时
        home_rank = self.team_data.get_rank(home) if hasattr(self.team_data, 'get_rank') else None
        away_rank = self.team_data.get_rank(away) if hasattr(self.team_data, 'get_rank') else None
        if home_rank and away_rank:
            rank_diff = abs(home_rank - away_rank)
            if rank_diff < 10:
                # 排名接近，增加平局
                result['draw'] *= 1.1

        # 归一化
        total = result['home_win'] + result['draw'] + result['away_win']
        result['home_win'] /= total
        result['draw'] /= total
        result['away_win'] /= total

        return result

    def predict(self, home: str, away: str, match_date: datetime,
                match_stage: str = 'group', **kwargs) -> dict:
        """预测"""

        # 基础预测
        pred = self.rule_predictor.predict(
            home_team=home,
            away_team=away,
            match_date=match_date,
            match_stage=match_stage,
            **kwargs
        )

        # 应用专家规则
        adjusted_probs = self.apply_expert_rules(
            home, away, match_stage, pred['prediction']
        )

        pred['prediction'] = adjusted_probs
        return pred


def backtest_expert_rules():
    """回测专家规则"""
    predictor = ExpertRulesPredictor()
    collector = TournamentDataCollector()
    matches = collector.get_matches(include_upset=True)

    now = datetime.now()
    correct = 0
    correct_base = 0

    for match in matches:
        # 专家规则预测
        pred = predictor.predict(
            home=match['home'],
            away=match['away'],
            match_date=now,
            match_stage=match.get('stage', 'group'),
            home_last_match_date=now - timedelta(days=5),
            away_last_match_date=now - timedelta(days=4),
            odds={'home': 2.0, 'draw': 3.2, 'away': 3.8}
        )

        probs = pred['prediction']
        max_prob = max(probs['home_win'], probs['draw'], probs['away_win'])

        if probs['home_win'] > max(probs['draw'], probs['away_win']):
            pred_winner = 'home'
        elif probs['away_win'] > probs['draw']:
            pred_winner = 'away'
        else:
            pred_winner = 'draw'

        # 基础预测（无专家规则）
        base_pred = predictor.rule_predictor.predict(
            home_team=match['home'],
            away_team=match['away'],
            home_last_match_date=now - timedelta(days=5),
            away_last_match_date=now - timedelta(days=4),
            match_date=now,
            match_stage=match.get('stage', 'group'),
            odds={'home': 2.0, 'draw': 3.2, 'away': 3.8}
        )

        base_probs = base_pred['prediction']
        base_max = max(base_probs['home_win'], base_probs['draw'], base_probs['away_win'])
        if base_probs['home_win'] > max(base_probs['draw'], base_probs['away_win']):
            base_winner = 'home'
        elif base_probs['away_win'] > base_probs['draw']:
            base_winner = 'away'
        else:
            base_winner = 'draw'

        # 实际结果
        parts = match['score'].split('-')
        if parts[0] == parts[1]:
            actual = 'draw'
        elif parts[0] > parts[1]:
            actual = 'home'
        else:
            actual = 'away'

        if pred_winner == actual:
            correct += 1
        if base_winner == actual:
            correct_base += 1

    print(f"专家规则准确率: {correct}/{len(matches)} = {correct/len(matches):.1%}")
    print(f"基础预测准确率: {correct_base}/{len(matches)} = {correct_base/len(matches):.1%}")


if __name__ == '__main__':
    backtest_expert_rules()
