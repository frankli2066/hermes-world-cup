"""
机器学习集成预测器
使用随机森林和梯度提升组合来提升预测准确率
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

try:
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.preprocessing import StandardScaler
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False


class MLEnsemblePredictor:
    """机器学习集成预测器"""

    def __init__(self):
        self.predictor = UnifiedPredictor()
        self.team_data = TeamDataManager()
        self.h2h = H2HDatabase()
        self.collector = TournamentDataCollector()

        # 特征缩放器
        self.scaler = StandardScaler() if HAS_SKLEARN else None

        # 训练数据
        self.X_train = []
        self.y_train = []

        # 是否已训练
        self.trained = False

    def extract_features(self, home: str, away: str, match_date: datetime, match_stage: str = 'group') -> list:
        """提取比赛特征"""
        features = []

        # 1. Elo特征
        home_elo = self.team_data.get_elo(home)
        away_elo = self.team_data.get_elo(away)
        elo_diff = home_elo - away_elo
        elo_sum = home_elo + away_elo

        features.append(home_elo)
        features.append(away_elo)
        features.append(elo_diff)
        features.append(elo_sum)

        # 2. Elo差距分段
        abs_elo_diff = abs(elo_diff)
        features.append(1 if abs_elo_diff < 50 else 0)  # 非常接近
        features.append(1 if 50 <= abs_elo_diff < 100 else 0)  # 接近
        features.append(1 if 100 <= abs_elo_diff < 150 else 0)  # 中等
        features.append(1 if 150 <= abs_elo_diff < 200 else 0)  # 较大
        features.append(1 if abs_elo_diff >= 200 else 0)  # 悬殊

        # 3. H2H特征
        stats = self.h2h.get_h2h_stats(home, away)
        total = stats['total']
        draws = stats['draws']
        team1_wins = stats['team1_wins']
        team2_wins = stats['team2_wins']

        features.append(total)
        features.append(draws)
        features.append(team1_wins)
        features.append(team2_wins)
        features.append(draws / total if total > 0 else 0)  # 平局率
        features.append(team1_wins / total if total > 0 else 0.5)  # 主队胜率
        features.append(team2_wins / total if total > 0 else 0.5)  # 客队胜率

        # 4. H2H分段特征
        features.append(1 if total >= 3 else 0)  # 有足够历史
        features.append(1 if total > 0 and draws / total >= 0.4 else 0)  # 高平局率
        features.append(1 if total > 0 and draws / total >= 0.25 else 0)  # 中等平局率

        # 5. 基础预测概率（从UnifiedPredictor获取）
        pred = self.predictor.predict(
            home_team=home,
            away_team=away,
            match_date=match_date,
            match_stage=match_stage
        )
        probs = pred['prediction']
        features.append(probs['home_win'])
        features.append(probs['away_win'])
        features.append(probs['draw'])

        # 6. 比赛阶段特征
        features.append(1 if match_stage == 'group' else 0)
        features.append(1 if match_stage in ['16', 'round16'] else 0)
        features.append(1 if match_stage in ['8', 'quarter'] else 0)
        features.append(1 if match_stage in ['4', 'semi'] else 0)
        features.append(1 if match_stage == 'final' else 0)
        features.append(1 if match_stage == 'qualifier' else 0)

        # 7. 概率差距特征
        max_prob = max(probs['home_win'], probs['away_win'], probs['draw'])
        second_prob = sorted([probs['home_win'], probs['away_win'], probs['draw']], reverse=True)[1]
        features.append(max_prob)
        features.append(max_prob - second_prob)  # 信心差距
        features.append(1 if max_prob - second_prob < 0.03 else 0)  # 边缘情况

        # 8. 强队主场优势
        home_elo_advantage = 50 if home_elo > away_elo else -50
        features.append(home_elo_advantage)

        return features

    def collect_training_data(self, n_samples: int = 100, tournaments: list = None):
        """收集训练数据"""
        if tournaments is None:
            tournaments = ['wc', 'euro']

        matches = []
        for t in tournaments:
            t_matches = self.collector.get_matches(tournament=t, include_upset=True)
            matches.extend(t_matches)

        print(f"收集到 {len(matches)} 个比赛")

        # 打乱顺序
        random.shuffle(matches)

        # 限制样本数
        if n_samples and len(matches) > n_samples:
            matches = matches[:n_samples]

        X = []
        y = []

        for m in matches:
            home = m['home']
            away = m['away']
            score = m['score']

            # 解析实际结果
            parts = score.split('-')
            if len(parts) != 2:
                continue

            if parts[0] == parts[1]:
                actual = 0  # draw
            elif parts[0] > parts[1]:
                actual = 1  # home win
            else:
                actual = 2  # away win

            # 提取特征
            try:
                features = self.extract_features(
                    home, away,
                    datetime.now(),
                    m.get('stage', 'group')
                )
                X.append(features)
                y.append(actual)
            except Exception as e:
                continue

        self.X_train = X
        self.y_train = y
        print(f"收集了 {len(X)} 个训练样本")

        return X, y

    def train(self):
        """训练机器学习模型"""
        if not HAS_SKLEARN:
            print("sklearn未安装，使用规则方法")
            self.trained = False
            return

        if len(self.X_train) < 50:
            print(f"训练数据不足: {len(self.X_train)}，跳过ML训练")
            self.trained = False
            return

        # 标准化特征
        X_scaled = self.scaler.fit_transform(self.X_train)

        # 训练随机森林
        self.rf = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            random_state=42
        )
        self.rf.fit(X_scaled, self.y_train)

        # 训练梯度提升
        self.gb = GradientBoostingClassifier(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            random_state=42
        )
        self.gb.fit(X_scaled, self.y_train)

        self.trained = True
        print("ML模型训练完成")

    def predict_ml(self, home: str, away: str, match_date: datetime, match_stage: str = 'group') -> dict:
        """使用机器学习模型预测"""
        if not self.trained:
            # 回退到规则方法
            pred = self.predictor.predict(
                home_team=home,
                away_team=away,
                match_date=match_date,
                match_stage=match_stage
            )
            return pred

        # 提取特征
        features = self.extract_features(home, away, match_date, match_stage)
        features_scaled = self.scaler.transform([features])

        # 集成预测
        rf_proba = self.rf.predict_proba(features_scaled)[0]
        gb_proba = self.gb.predict_proba(features_scaled)[0]

        # 平均集成
        ensemble_proba = (rf_proba + gb_proba) / 2

        # 归一化
        total = sum(ensemble_proba)
        ensemble_proba = [p / total for p in ensemble_proba]

        return {
            'home_win': ensemble_proba[1],
            'draw': ensemble_proba[0],
            'away_win': ensemble_proba[2],
        }

    def predict_ensemble(self, home: str, away: str, match_date: datetime,
                        match_stage: str = 'group', ml_weight: float = 0.3) -> dict:
        """集成预测：结合规则和ML模型"""
        # 规则预测
        rule_pred = self.predictor.predict(
            home_team=home,
            away_team=away,
            match_date=match_date,
            match_stage=match_stage
        )
        rule_probs = rule_pred['prediction']

        if not self.trained:
            return rule_pred

        # ML预测
        ml_probs = self.predict_ml(home, away, match_date, match_stage)

        # 加权集成
        combined = {
            'home_win': rule_probs['home_win'] * (1 - ml_weight) + ml_probs['home_win'] * ml_weight,
            'draw': rule_probs['draw'] * (1 - ml_weight) + ml_probs['draw'] * ml_weight,
            'away_win': rule_probs['away_win'] * (1 - ml_weight) + ml_probs['away_win'] * ml_weight,
        }

        # 归一化
        total = sum(combined.values())
        combined = {k: v / total for k, v in combined.items()}

        return {
            'prediction': combined,
            'rule_prediction': rule_probs,
            'ml_prediction': ml_probs,
            'ensemble': True
        }


def backtest_ml():
    """回测ML集成模型 - 严格分离训练和测试数据"""
    collector = TournamentDataCollector()

    # 用不同赛事的数据分离训练和测试
    # 训练：世界杯 + 欧洲杯预选 + 非洲杯
    train_tournaments = ['wc', 'afcon']
    # 测试：欧洲杯 + 世界杯预选 + 南美预选
    test_tournaments = ['euro', 'wc_qualifier', 'copa_america']

    predictor = MLEnsemblePredictor()

    # 收集训练数据
    print("收集训练数据...")
    predictor.collect_training_data(tournaments=train_tournaments)

    # 训练
    predictor.train()

    # 回测（使用未参与训练的赛事）
    print("\n回测（使用未参与训练的赛事）...")
    matches = []
    for t in test_tournaments:
        t_matches = collector.get_matches(tournament=t, include_upset=True)
        matches.extend(t_matches)

    print(f"测试集: {len(matches)} 个比赛")

    correct = 0
    results = []

    for m in matches:
        pred = predictor.predict_ensemble(
            home=m['home'],
            away=m['away'],
            match_date=datetime.now(),
            match_stage=m.get('stage', 'group'),
            ml_weight=0.3
        )

        probs = pred['prediction']

        # 判断预测胜者
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

        results.append({
            'match': f"{m['home']} vs {m['away']}",
            'score': m['score'],
            'predicted': pred_winner,
            'actual': actual,
            'correct': correct_flag
        })

    accuracy = correct / len(results) if results else 0
    print(f"\n{'='*60}")
    print(f"ML集成回测结果（严格分离训练/测试数据）")
    print(f"{'='*60}")
    print(f"训练赛事: {train_tournaments}")
    print(f"测试赛事: {test_tournaments}")
    print(f"训练样本: {len(predictor.X_train)}")
    print(f"测试样本: {len(results)}")
    print(f"准确率: {accuracy:.1%} ({correct}/{len(results)})")
    print(f"ML模型已训练: {predictor.trained}")

    return accuracy, results


def backtest_ml_all():
    """使用所有数据训练，但用交叉验证方式测试"""
    from sklearn.model_selection import cross_val_score

    predictor = MLEnsemblePredictor()

    # 收集所有数据
    print("收集所有数据...")
    predictor.collect_training_data(n_samples=None)  # 不限制样本数

    if len(predictor.X_train) < 50:
        print("数据不足，跳过ML训练")
        return

    # 标准化
    X_scaled = predictor.scaler.fit_transform(predictor.X_train)

    # 训练随机森林
    rf = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        min_samples_split=5,
        random_state=42
    )

    # 5折交叉验证
    print("\n5折交叉验证...")
    cv_scores = cross_val_score(rf, X_scaled, predictor.y_train, cv=5)

    print(f"交叉验证准确率: {cv_scores.mean():.1%} (+/- {cv_scores.std()*2:.1%})")
    print(f"各折准确率: {[f'{s:.1%}' for s in cv_scores]}")


if __name__ == '__main__':
    print("="*60)
    print("测试1: 严格分离训练/测试数据")
    print("="*60)
    backtest_ml()

    print("\n")
    print("="*60)
    print("测试2: 交叉验证（使用全部数据）")
    print("="*60)
    backtest_ml_all()
