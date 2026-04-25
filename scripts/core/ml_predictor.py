#!/usr/bin/env python3
"""
足球比赛预测 - 机器学习模型
使用sklearn进行真正的ML训练和预测
"""

import numpy as np
import json
import os
from typing import Tuple, Dict, List
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score
from sklearn.preprocessing import StandardScaler

BASE_DIR = os.path.expanduser("~/hermes-world-cup/")


class MLPredictor:
    """
    机器学习预测器

    使用多种特征进行胜负/比分预测
    """

    def __init__(self):
        self.feature_names = [
            "elo_diff",           # Elo差距
            "fifa_diff",         # FIFA排名差距
            "form_diff",         # 近期状态差距
            "h2h_home_wins",    # 主队H2H胜率
            "home_elo",          # 主队Elo
            "away_elo",          # 客队Elo
            "elo_diff_normalized", # 归一化Elo差
        ]

        # 训练数据
        self.history = self._load_history()

        # 训练好的模型
        self.outcome_model = None
        self.score_model = None
        self.scaler = StandardScaler()

    def _load_history(self) -> List[dict]:
        """加载历史比赛数据"""
        history_file = os.path.join(BASE_DIR, "data/calibration/match_history.json")
        if os.path.exists(history_file):
            try:
                with open(history_file) as f:
                    data = json.load(f)
                    return data.get("matches", [])
            except:
                pass

        # 默认历史数据
        return [
            # 2022世界杯
            {"home": "Argentina", "away": "France", "score": "2-2", "year": 2022, "stage": "final"},
            {"home": "France", "away": "Morocco", "score": "2-0", "year": 2022, "stage": "semi"},
            {"home": "Argentina", "away": "Croatia", "score": "3-0", "year": 2022, "stage": "semi"},
            {"home": "Morocco", "away": "Portugal", "score": "1-0", "year": 2022, "stage": "quarter"},
            {"home": "England", "away": "France", "score": "1-2", "year": 2022, "stage": "quarter"},
            {"home": "Netherlands", "away": "Argentina", "score": "2-2", "year": 2022, "stage": "quarter"},
            {"home": "Brazil", "away": "Croatia", "score": "1-1", "year": 2022, "stage": "quarter"},
            {"home": "Portugal", "away": "Switzerland", "score": "6-1", "year": 2022, "stage": "round16"},
            {"home": "Spain", "away": "Germany", "score": "1-2", "year": 2022, "stage": "round16"},
            {"home": "Brazil", "away": "South Korea", "score": "4-1", "year": 2022, "stage": "round16"},
            {"home": "Netherlands", "away": "USA", "score": "3-1", "year": 2022, "stage": "round16"},
            {"home": "Argentina", "away": "Australia", "score": "2-1", "year": 2022, "stage": "round16"},
            {"home": "France", "away": "Poland", "score": "3-1", "year": 2022, "stage": "round16"},
            {"home": "England", "away": "Senegal", "score": "3-0", "year": 2022, "stage": "round16"},
            {"home": "Germany", "away": "Japan", "score": "1-2", "year": 2022, "stage": "group"},
            {"home": "Argentina", "away": "Saudi Arabia", "score": "1-2", "year": 2022, "stage": "group"},
            {"home": "Brazil", "away": "Serbia", "score": "2-0", "year": 2022, "stage": "group"},
            {"home": "France", "away": "Denmark", "score": "2-1", "year": 2022, "stage": "group"},
            {"home": "Spain", "away": "Costa Rica", "score": "7-0", "year": 2022, "stage": "group"},
            {"home": "Germany", "away": "Spain", "score": "1-1", "year": 2022, "stage": "group"},
            # 2018世界杯
            {"home": "France", "away": "Croatia", "score": "4-2", "year": 2018, "stage": "final"},
            {"home": "Belgium", "away": "France", "score": "0-1", "year": 2018, "stage": "semi"},
            {"home": "England", "away": "Croatia", "score": "1-2", "year": 2018, "stage": "semi"},
            {"home": "Uruguay", "away": "France", "score": "0-2", "year": 2018, "stage": "quarter"},
            {"home": "Brazil", "away": "Belgium", "score": "2-1", "year": 2018, "stage": "quarter"},
            {"home": "Sweden", "away": "England", "score": "0-2", "year": 2018, "stage": "quarter"},
            {"home": "France", "away": "Argentina", "score": "4-3", "year": 2018, "stage": "round16"},
            {"home": "Uruguay", "away": "Portugal", "score": "2-1", "year": 2018, "stage": "round16"},
            {"home": "Japan", "away": "Belgium", "score": "2-3", "year": 2018, "stage": "round16"},
            {"home": "Germany", "away": "Mexico", "score": "0-1", "year": 2018, "stage": "group"},
            {"home": "Brazil", "away": "Switzerland", "score": "1-1", "year": 2018, "stage": "group"},
            {"home": "Germany", "away": "South Korea", "score": "0-2", "year": 2018, "stage": "group"},
            # 2014世界杯
            {"home": "Germany", "away": "Argentina", "score": "1-0", "year": 2014, "stage": "final"},
            {"home": "Brazil", "away": "Germany", "score": "1-7", "year": 2014, "stage": "semi"},
            {"home": "Netherlands", "away": "Brazil", "score": "0-0", "year": 2014, "stage": "semi"},
            {"home": "Germany", "away": "Algeria", "score": "2-1", "year": 2014, "stage": "round16"},
            # 2010世界杯
            {"home": "Spain", "away": "Netherlands", "score": "1-0", "year": 2010, "stage": "final"},
            {"home": "Germany", "away": "Spain", "score": "0-1", "year": 2010, "stage": "semi"},
            # 欧洲杯2021
            {"home": "Italy", "away": "England", "score": "1-1", "year": 2021, "stage": "final"},
            {"home": "Italy", "away": "Spain", "score": "1-1", "year": 2021, "stage": "semi"},
            {"home": "Portugal", "away": "France", "score": "3-3", "year": 2021, "stage": "group"},
            {"home": "Spain", "away": "Croatia", "score": "5-3", "year": 2021, "stage": "round16"},
            {"home": "France", "away": "Switzerland", "score": "3-3", "year": 2021, "stage": "round16"},
            # 欧洲杯2024
            {"home": "Spain", "away": "England", "score": "2-1", "year": 2024, "stage": "final"},
            {"home": "Netherlands", "away": "England", "score": "1-2", "year": 2024, "stage": "semi"},
            {"home": "Spain", "away": "France", "score": "2-1", "year": 2024, "stage": "semi"},
            {"home": "Germany", "away": "Spain", "score": "1-2", "year": 2024, "stage": "quarter"},
            # 美洲杯
            {"home": "Argentina", "away": "Brazil", "score": "1-0", "year": 2021, "stage": "final"},
        ]

    def _get_features(self, home: str, away: str,
                     elo_diff: float, fifa_diff: float,
                     form_diff: float, h2h_home_wins: float) -> np.ndarray:
        """构建特征向量"""
        features = [
            elo_diff / 100,           # 归一化Elo差
            fifa_diff / 50,           # 归一化FIFA差
            form_diff / 10,           # 归一化状态差
            h2h_home_wins,            # H2H胜率
            elo_diff / 200,           # 另一个归一化版本
        ]
        return np.array(features)

    def train(self, team_stats) -> Dict:
        """
        训练ML模型

        使用历史数据训练胜负和比分预测模型
        """
        print("🤖 训练机器学习模型...")

        X = []
        y_outcome = []  # 0=away win, 1=draw, 2=home win
        y_home_goals = []
        y_away_goals = []

        # 球队基础数据
        elo_map = team_stats.elo.ratings if hasattr(team_stats.elo, 'ratings') else {}
        fifa_map = team_stats.fifa if hasattr(team_stats.fifa, '__dict__') else {}
        form_map = team_stats.form if hasattr(team_stats.form, '__dict__') else {}

        for match in self.history:
            home = match["home"]
            away = match["away"]
            score = match["score"]
            home_goals, away_goals = map(int, score.split("-"))

            # 获取特征
            home_elo = elo_map.get(home, 1700)
            away_elo = elo_map.get(away, 1700)
            elo_diff = home_elo - away_elo

            home_fifa = getattr(fifa_map, home, [1700])[0] if isinstance(getattr(fifa_map, home, None), list) else 1700
            away_fifa = getattr(fifa_map, away, [1700])[0] if isinstance(getattr(fifa_map, away, None), list) else 1700
            fifa_diff = away_fifa - home_fifa  # FIFA排名低=更强

            home_form = getattr(form_map, home, [0.5])[0] if isinstance(getattr(form_map, home, None), list) else 0.5
            away_form = getattr(form_map, away, [0.5])[0] if isinstance(getattr(form_map, away, None), list) else 0.5
            form_diff = home_form - away_form

            # H2H简化（没有真实H2H数据）
            h2h_home_wins = 0.5

            # 特征
            features = self._get_features(home, away, elo_diff, fifa_diff, form_diff, h2h_home_wins)
            X.append(features)

            # 标签
            if home_goals > away_goals:
                y_outcome.append(2)
            elif home_goals < away_goals:
                y_outcome.append(0)
            else:
                y_outcome.append(1)

            y_home_goals.append(home_goals)
            y_away_goals.append(away_goals)

        X = np.array(X)
        y_outcome = np.array(y_outcome)
        y_home_goals = np.array(y_home_goals)
        y_away_goals = np.array(y_away_goals)

        # 标准化
        X_scaled = self.scaler.fit_transform(X)

        # 训练胜负模型
        print("  训练胜负预测模型...")
        self.outcome_model = GradientBoostingClassifier(
            n_estimators=100,
            max_depth=3,
            learning_rate=0.1,
            random_state=42
        )
        self.outcome_model.fit(X_scaled, y_outcome)

        # 交叉验证
        cv_scores = cross_val_score(self.outcome_model, X_scaled, y_outcome, cv=5)
        print(f"  交叉验证准确率: {cv_scores.mean()*100:.1f}% (+/- {cv_scores.std()*100:.1f}%)")

        return {
            "cv_accuracy": cv_scores.mean(),
            "cv_std": cv_scores.std(),
            "n_samples": len(X),
        }

    def predict_outcome(self, home: str, away: str,
                       elo_diff: float, fifa_diff: float = 0,
                       form_diff: float = 0, h2h_home_wins: float = 0.5) -> Dict:
        """
        预测比赛胜负

        Returns:
            {"prob_draw": float, "prob_home": float, "prob_away": float,
             "predicted_outcome": "home"/"draw"/"away"}
        """
        if self.outcome_model is None:
            return {"prob_draw": 0.33, "prob_home": 0.34, "prob_away": 0.33,
                   "predicted_outcome": "home"}

        features = self._get_features(home, away, elo_diff, fifa_diff, form_diff, h2h_home_wins)
        features_scaled = self.scaler.transform([features])

        proba = self.outcome_model.predict_proba(features_scaled)[0]
        prediction = self.outcome_model.predict(features_scaled)[0]

        outcomes = ["away", "draw", "home"]
        return {
            "prob_away": round(proba[0], 3),
            "prob_draw": round(proba[1], 3),
            "prob_home": round(proba[2], 3),
            "predicted_outcome": outcomes[prediction],
        }

    def predict_score(self, home: str, away: str,
                     elo_diff: float, fifa_diff: float = 0,
                     form_diff: float = 0, h2h_home_wins: float = 0.5) -> Tuple[int, int]:
        """
        预测比分

        使用ML模型的概率分布进行采样
        """
        outcome = self.predict_outcome(home, away, elo_diff, fifa_diff, form_diff, h2h_home_wins)

        # 基于胜负概率和xG生成比分
        home_xg = 1.3 + elo_diff / 100 * 0.1  # 简化xG估算
        away_xg = 1.3 - elo_diff / 100 * 0.1

        # 根据预测的胜负调整xG
        if outcome["predicted_outcome"] == "home":
            home_xg *= 1.1
            away_xg *= 0.9
        elif outcome["predicted_outcome"] == "away":
            home_xg *= 0.9
            away_xg *= 1.1

        # 泊松采样
        import numpy as np
        home_goals = max(0, np.random.poisson(home_xg))
        away_goals = max(0, np.random.poisson(away_xg))

        return home_goals, away_goals


# ============ 主程序 ============
if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "core"))

    from core.team_stats import TeamRating
    from core.xg_model import xGModel

    print("=" * 60)
    print("🤖 ML预测模型测试")
    print("=" * 60)

    # 加载数据
    team_stats = TeamRating()

    # 训练
    ml = MLPredictor()
    result = ml.train(team_stats)

    # 测试预测
    test_matches = [
        ("France", "Germany"),
        ("Argentina", "France"),
        ("Brazil", "Serbia"),
    ]

    print("\n📊 测试预测:")
    for home, away in test_matches:
        elo_diff = team_stats.elo.get_rating(home) - team_stats.elo.get_rating(away)
        outcome = ml.predict_outcome(home, away, elo_diff)
        home_goals, away_goals = ml.predict_score(home, away, elo_diff)
        print(f"  {home} vs {away}:")
        print(f"    胜负: {outcome['predicted_outcome']} "
              f"(主胜{outcome['prob_home']*100:.0f}% / 平{outcome['prob_draw']*100:.0f}% / 客胜{outcome['prob_away']*100:.0f}%)")
        print(f"    比分预测: {home_goals}-{away_goals}")

    print("\n" + "=" * 60)
