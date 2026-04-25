"""
权重优化器
系统地测试不同权重配置，找到最优组合
"""
import sys
sys.path.insert(0, 'core')
sys.path.insert(0, '.')

from unified_predictor import UnifiedPredictor
from tournament_data import TournamentDataCollector
from datetime import datetime, timedelta
import random


class WeightOptimizer:
    """权重优化器"""

    def __init__(self):
        self.collector = TournamentDataCollector()
        self.matches = self.collector.get_matches(include_upset=True)
        self.now = datetime.now()

    def evaluate_weights(self, weights: dict) -> float:
        """评估给定权重的准确率"""
        predictor = UnifiedPredictor()

        # 设置权重
        predictor.weights.update(weights)

        correct = 0
        for match in self.matches:
            try:
                pred = predictor.predict(
                    home_team=match['home'],
                    away_team=match['away'],
                    home_last_match_date=self.now - timedelta(days=5),
                    away_last_match_date=self.now - timedelta(days=4),
                    match_date=self.now,
                    venue='Stadium',
                    weather={'temp': 20, 'humidity': 60, 'precipitation': 0, 'wind': 10},
                    group_standings={'home': {'points': 3}, 'away': {'points': 0}},
                    match_stage=match.get('stage', 'group'),
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

                parts = match['score'].split('-')
                if parts[0] == parts[1]:
                    actual = 'draw'
                elif parts[0] > parts[1]:
                    actual = 'home'
                else:
                    actual = 'away'

                if pred_winner == actual:
                    correct += 1
            except:
                continue

        return correct / len(self.matches)

    def random_search(self, n_iterations: int = 100) -> dict:
        """随机搜索最优权重"""
        print(f"开始随机搜索 ({n_iterations} 次迭代)...")

        best_weights = None
        best_accuracy = 0

        for i in range(n_iterations):
            # 随机生成权重
            weights = {
                'elo_weight': random.uniform(0.15, 0.35),
                'odds_weight': random.uniform(0.15, 0.35),
                'form_weight': random.uniform(0.08, 0.20),
                'home_advantage_weight': random.uniform(0.05, 0.15),
                'xg_weight': random.uniform(0.05, 0.15),
                'h2h_weight': random.uniform(0.03, 0.15),
                'odds_movement_weight': random.uniform(0.02, 0.10),
                'fatigue_weight': random.uniform(0.01, 0.08),
                'referee_weight': random.uniform(0.01, 0.05),
                'style_matchup_weight': random.uniform(0.01, 0.05),
                'motivation_weight': random.uniform(0.005, 0.03),
                'weather_weight': random.uniform(0.005, 0.03),
                'head_to_head_weight': random.uniform(0.03, 0.10),
                'injury_weight': random.uniform(0.005, 0.03),
            }

            accuracy = self.evaluate_weights(weights)

            if accuracy > best_accuracy:
                best_accuracy = accuracy
                best_weights = weights.copy()
                print(f"  迭代 {i+1}: 新最佳准确率 {accuracy:.1%}")

        return best_weights, best_accuracy

    def grid_search(self) -> dict:
        """网格搜索关键权重"""
        print("开始网格搜索...")

        best_weights = None
        best_accuracy = 0

        # 测试不同的elo_weight和odds_weight组合
        for elo_w in [0.20, 0.25, 0.30]:
            for odds_w in [0.20, 0.25, 0.30]:
                for h2h_w in [0.05, 0.08, 0.10, 0.12]:
                    weights = {
                        'elo_weight': elo_w,
                        'odds_weight': odds_w,
                        'form_weight': 0.15,
                        'home_advantage_weight': 0.08,
                        'xg_weight': 0.08,
                        'h2h_weight': h2h_w,
                        'odds_movement_weight': 0.05,
                        'fatigue_weight': 0.03,
                        'referee_weight': 0.02,
                        'style_matchup_weight': 0.02,
                        'motivation_weight': 0.01,
                        'weather_weight': 0.01,
                        'head_to_head_weight': 0.05,
                        'injury_weight': 0.01,
                    }

                    accuracy = self.evaluate_weights(weights)

                    if accuracy > best_accuracy:
                        best_accuracy = accuracy
                        best_weights = weights.copy()
                        print(f"  新最佳: elo={elo_w}, odds={odds_w}, h2h={h2h_w} -> {accuracy:.1%}")

        return best_weights, best_accuracy


if __name__ == '__main__':
    optimizer = WeightOptimizer()

    # 先用网格搜索快速定位
    print("="*60)
    print("网格搜索")
    print("="*60)
    best_weights, best_accuracy = optimizer.grid_search()

    print(f"\n网格搜索最佳: {best_accuracy:.1%}")
    print(f"最佳权重: {best_weights}")

    # 再用随机搜索精细调整
    print("\n" + "="*60)
    print("随机搜索")
    print("="*60)
    rand_weights, rand_accuracy = optimizer.random_search(n_iterations=50)

    if rand_accuracy > best_accuracy:
        print(f"\n随机搜索更优: {rand_accuracy:.1%}")
        print(f"最佳权重: {rand_weights}")
    else:
        print(f"\n网格搜索最佳: {best_accuracy:.1%}")
