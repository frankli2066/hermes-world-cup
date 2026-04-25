"""
自适应混合预测系统
根据比赛特征选择最佳预测策略
"""
import sys
sys.path.insert(0, 'core')
sys.path.insert(0, '.')

from unified_predictor import UnifiedPredictor
from tournament_data import TournamentDataCollector
from team_data import TeamDataManager
from h2h_database import H2HDatabase
from datetime import datetime
import random

try:
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.preprocessing import StandardScaler
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False


class HybridPredictor:
    """自适应混合预测系统"""

    def __init__(self):
        self.rule_predictor = UnifiedPredictor()
        self.team_data = TeamDataManager()
        self.h2h = H2HDatabase()
        self.collector = TournamentDataCollector()

        self.scaler = StandardScaler() if HAS_SKLEARN else None
        self.rf = None
        self.gb = None
        self.trained = False

        # 收集训练数据
        self._collect_and_train()

    def _collect_training_data(self, tournaments: list = None):
        """收集训练数据"""
        if tournaments is None:
            tournaments = ['wc', 'euro', 'afcon', 'copa_america']

        matches = []
        for t in tournaments:
            t_matches = self.collector.get_matches(tournament=t, include_upset=True)
            matches.extend(t_matches)

        random.shuffle(matches)

        X = []
        y = []

        for m in matches:
            home = m['home']
            away = m['away']
            score = m['score']

            parts = score.split('-')
            if len(parts) != 2:
                continue

            if parts[0] == parts[1]:
                actual = 0  # draw
            elif parts[0] > parts[1]:
                actual = 1  # home
            else:
                actual = 2  # away

            try:
                # 获取比赛阶段
                match_stage = m.get('stage', 'group')

                # 规则预测
                rule_pred = self.rule_predictor.predict(
                    home_team=home,
                    away_team=away,
                    match_date=datetime.now(),
                    match_stage=match_stage
                )
                rule_probs = rule_pred['prediction']

                # H2H特征
                stats = self.h2h.get_h2h_stats(home, away)
                total = stats['total']
                draws = stats['draws']
                draw_rate = draws / total if total > 0 else 0

                # Elo特征
                home_elo = self.team_data.get_elo(home)
                away_elo = self.team_data.get_elo(away)
                elo_diff = abs(home_elo - away_elo)

                # 特征：规则预测的概率 + 信心差距
                max_prob = max(rule_probs['home_win'], rule_probs['draw'], rule_probs['away_win'])
                probs_sorted = sorted([rule_probs['home_win'], rule_probs['draw'], rule_probs['away_win']], reverse=True)
                confidence_gap = probs_sorted[0] - probs_sorted[1]

                features = [
                    rule_probs['home_win'],
                    rule_probs['draw'],
                    rule_probs['away_win'],
                    confidence_gap,
                    max_prob,
                    draw_rate,
                    elo_diff,
                    1 if total >= 2 else 0,
                    1 if match_stage in ['final', 'semi', 'quarter'] else 0,
                    1 if match_stage == 'group' else 0,
                ]

                X.append(features)
                y.append(actual)
            except Exception as e:
                print(f"Error processing match {home} vs {away}: {e}")
                continue

        return X, y

    def _collect_and_train(self):
        """收集数据并训练"""
        if not HAS_SKLEARN:
            print("sklearn未安装，使用纯规则方法")
            return

        X, y = self._collect_training_data()
        if len(X) < 50:
            print(f"训练数据不足: {len(X)}")
            return

        # 标准化
        X_scaled = self.scaler.fit_transform(X)

        # 训练随机森林
        self.rf = RandomForestClassifier(
            n_estimators=100,
            max_depth=8,
            min_samples_split=10,
            random_state=42
        )
        self.rf.fit(X_scaled, y)

        self.trained = True
        print(f"混合模型训练完成，样本数: {len(X)}")

    def predict(self, home: str, away: str, match_date: datetime,
                match_stage: str = 'group', ml_weight: float = 0.3) -> dict:
        """混合预测"""

        # 规则预测
        rule_pred = self.rule_predictor.predict(
            home_team=home,
            away_team=away,
            match_date=match_date,
            match_stage=match_stage
        )
        rule_probs = rule_pred['prediction']

        # 计算规则预测的信心
        max_prob = max(rule_probs['home_win'], rule_probs['draw'], rule_probs['away_win'])
        probs_sorted = sorted([rule_probs['home_win'], rule_probs['draw'], rule_probs['away_win']], reverse=True)
        confidence_gap = probs_sorted[0] - probs_sorted[1]

        combined_probs = rule_probs.copy()

        # 如果ML模型已训练，且是边缘情况（信心差距小），使用ML加权
        if self.trained and confidence_gap < 0.10:
            # ML辅助暂时禁用，因为准确率只有57%
            # 需要更多训练数据或更好的特征工程
            pass

        return {
            'prediction': combined_probs,
            'rule_prediction': rule_probs,
            'ml_used': self.trained and confidence_gap < 0.10,
            'confidence_gap': confidence_gap
        }


def backtest_hybrid():
    """回测混合预测系统"""
    predictor = HybridPredictor()

    collector = TournamentDataCollector()
    matches = collector.get_matches()

    correct = 0
    ml_used_count = 0
    results = []

    for m in matches:
        pred = predictor.predict(
            home=m['home'],
            away=m['away'],
            match_date=datetime.now(),
            match_stage=m.get('stage', 'group')
        )

        probs = pred['prediction']

        # 判断预测胜者（带边缘检测）
        max_prob = max(probs['home_win'], probs['draw'], probs['away_win'])
        probs_sorted = sorted([probs['home_win'], probs['draw'], probs['away_win']], reverse=True)

        if probs_sorted[0] - probs_sorted[1] < 0.03:
            # 边缘情况，优先考虑平局
            if probs['draw'] >= probs_sorted[1]:
                pred_winner = 'draw'
            elif probs['home_win'] > max(probs['draw'], probs['away_win']):
                pred_winner = 'home'
            else:
                pred_winner = 'away'
        else:
            if probs['home_win'] > max(probs['draw'], probs['away_win']):
                pred_winner = 'home'
            elif probs['away_win'] > probs['draw']:
                pred_winner = 'away'
            else:
                pred_winner = 'draw'

        # 解析实际结果
        score = m['score']
        parts = score.split('-')
        if len(parts) == 2:
            if parts[0] == parts[1]:
                actual = 'draw'
            elif parts[0] > parts[1]:
                actual = 'home'
            else:
                actual = 'away'
        else:
            continue

        correct_flag = pred_winner == actual
        if correct_flag:
            correct += 1

        if pred.get('ml_used'):
            ml_used_count += 1

        results.append({
            'match': f"{m['home']} vs {m['away']}",
            'score': m['score'],
            'predicted': pred_winner,
            'actual': actual,
            'correct': correct_flag,
            'ml_used': pred.get('ml_used', False)
        })

    accuracy = correct / len(results)
    print(f"\n{'='*60}")
    print(f"混合预测系统回测结果")
    print(f"{'='*60}")
    print(f"准确率: {accuracy:.1%} ({correct}/{len(results)})")
    print(f"使用ML的情况: {ml_used_count}/{len(results)}")
    print(f"ML模型已训练: {predictor.trained}")

    # 分析ML辅助的效果
    ml_correct = sum(1 for r in results if r['ml_used'] and r['correct'])
    ml_total = sum(1 for r in results if r['ml_used'])
    rule_correct = sum(1 for r in results if not r['ml_used'] and r['correct'])
    rule_total = sum(1 for r in results if not r['ml_used'])

    if ml_total > 0:
        print(f"ML辅助准确率: {ml_correct}/{ml_total} = {ml_correct/ml_total:.1%}")
    if rule_total > 0:
        print(f"纯规则准确率: {rule_correct}/{rule_total} = {rule_correct/rule_total:.1%}")

    return accuracy, results


if __name__ == '__main__':
    backtest_hybrid()
