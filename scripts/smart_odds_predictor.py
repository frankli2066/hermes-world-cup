"""
自适应赔率模拟器
根据Elo差距生成更真实的赔率
"""
import sys
sys.path.insert(0, 'core')
sys.path.insert(0, '.')

from unified_predictor import UnifiedPredictor
from tournament_data import TournamentDataCollector
from team_data import TeamDataManager
from h2h_database import H2HDatabase
from datetime import datetime, timedelta
import random


class SmartOddsPredictor:
    """智能赔率预测器"""

    def __init__(self):
        self.rule_predictor = UnifiedPredictor()
        self.team_data = TeamDataManager()
        self.h2h = H2HDatabase()

    def generate_smart_odds(self, home: str, away: str, match_stage: str = 'group') -> dict:
        """根据Elo和H2H生成更智能的赔率"""
        home_elo = self.team_data.get_elo(home)
        away_elo = self.team_data.get_away_elo(away) if hasattr(self.team_data, 'get_away_elo') else self.team_data.get_elo(away)
        elo_diff = home_elo - away_elo

        # H2H调整
        stats = self.h2h.get_h2h_stats(home, away)
        draw_rate = stats['draws'] / stats['total'] if stats['total'] > 0 else 0.26  # 基础平局率26%

        # 根据Elo差距和比赛阶段调整赔率
        abs_diff = abs(elo_diff)

        # 基础赔率（转换为概率）
        if abs_diff < 50:
            # 实力接近
            home_prob = 0.38
            away_prob = 0.33
            draw_prob = 0.29
        elif abs_diff < 100:
            home_prob = 0.42
            away_prob = 0.30
            draw_prob = 0.28
        elif abs_diff < 150:
            home_prob = 0.48
            away_prob = 0.27
            draw_prob = 0.25
        elif abs_diff < 200:
            home_prob = 0.55
            away_prob = 0.22
            draw_prob = 0.23
        else:
            # 悬殊差距
            home_prob = 0.65
            away_prob = 0.17
            draw_prob = 0.18

        # 淘汰赛阶段平局概率降低
        if match_stage in ['16', 'round16', '8', 'quarter', '4', 'semi', 'final']:
            draw_prob *= 0.7
            total = home_prob + away_prob + draw_prob
            home_prob /= total / (1 - draw_prob)
            away_prob /= total / (1 - draw_prob)

        # H2H高平局率时增加平局概率
        if draw_rate > 0.35:
            draw_prob *= (1 + draw_rate)
            total = home_prob + away_prob + draw_prob
            home_prob /= total
            away_prob /= total
            draw_prob /= total

        # 转换回赔率
        home_odds = 1 / home_prob
        away_odds = 1 / away_prob
        draw_odds = 1 / draw_prob

        # 添加随机波动（模拟市场变化）
        home_odds *= (1 + random.uniform(-0.05, 0.05))
        away_odds *= (1 + random.uniform(-0.05, 0.05))
        draw_odds *= (1 + random.uniform(-0.05, 0.05))

        return {
            "home": home_odds,
            "away": away_odds,
            "draw": draw_odds
        }

    def predict(self, home: str, away: str, match_date: datetime,
                match_stage: str = 'group', use_smart_odds: bool = True) -> dict:
        """预测"""

        # 生成智能赔率
        if use_smart_odds:
            odds = self.generate_smart_odds(home, away, match_stage)
        else:
            odds = None

        # 调用规则预测器
        pred = self.rule_predictor.predict(
            home_team=home,
            away_team=away,
            match_date=match_date,
            match_stage=match_stage,
            odds=odds
        )

        return pred


def backtest_smart_odds():
    """回测智能赔率预测"""
    predictor = SmartOddsPredictor()
    collector = TournamentDataCollector()
    matches = collector.get_matches(include_upset=True)

    now = datetime.now()
    correct = 0
    correct_no_odds = 0

    for match in matches:
        # 使用智能赔率
        pred = predictor.predict(
            home=match['home'],
            away=match['away'],
            match_date=now,
            match_stage=match.get('stage', 'group'),
            use_smart_odds=True
        )

        probs = pred['prediction']
        max_prob = max(probs['home_win'], probs['draw'], probs['away_win'])

        if probs['home_win'] > max(probs['draw'], probs['away_win']):
            pred_winner = 'home'
        elif probs['away_win'] > probs['draw']:
            pred_winner = 'away'
        else:
            pred_winner = 'draw'

        # 不使用赔率的预测
        pred_no = predictor.rule_predictor.predict(
            home_team=match['home'],
            away_team=match['away'],
            home_last_match_date=now - timedelta(days=5),
            away_last_match_date=now - timedelta(days=4),
            match_date=now,
            match_stage=match.get('stage', 'group')
        )

        probs_no = pred_no['prediction']
        if probs_no['home_win'] > max(probs_no['draw'], probs_no['away_win']):
            pred_no_winner = 'home'
        elif probs_no['away_win'] > probs_no['draw']:
            pred_no_winner = 'away'
        else:
            pred_no_winner = 'draw'

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
        if pred_no_winner == actual:
            correct_no_odds += 1

    print(f"智能赔率准确率: {correct}/{len(matches)} = {correct/len(matches):.1%}")
    print(f"无赔率准确率: {correct_no_odds}/{len(matches)} = {correct_no_odds/len(matches):.1%}")


if __name__ == '__main__':
    backtest_smart_odds()
