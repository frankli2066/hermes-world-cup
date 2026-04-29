#!/usr/bin/env python3
"""
分赛事ML模型训练
为世界杯和欧洲杯分别训练专门的ML模型

因为两个赛事的特征不同：
- 世界杯淘汰赛更少，决赛前强队容易大胜
- 欧洲杯队伍实力更接近，平局率更高
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "core"))

import numpy as np
import xgboost as xgb
from sklearn.model_selection import cross_val_score
from sklearn.preprocessing import LabelEncoder
import pickle

from backtest_unified import HISTORICAL_MATCHES
from core.unified_predictor import UnifiedPredictor


def get_actual_result(score):
    """从比分判断实际结果"""
    home_goals, away_goals = map(int, score.split("-"))
    if home_goals == away_goals:
        return "draw"
    elif home_goals > away_goals:
        return "home"
    return "away"


def get_features(home_team, away_team, predictor, stage):
    """获取ML特征"""
    elo_feats = {
        "home_elo": predictor.get_elo(home_team),
        "away_elo": predictor.get_elo(away_team),
    }
    elo_feats["elo_diff"] = elo_feats["home_elo"] - elo_feats["away_elo"]
    elo_feats["elo_diff_abs"] = abs(elo_feats["elo_diff"])
    elo_feats["elo_ratio"] = elo_feats["home_elo"] / elo_feats["away_elo"] if elo_feats["away_elo"] > 0 else 1.0
    
    # H2H
    h2h_db = predictor.h2h
    stats = h2h_db.get_h2h_stats(home_team, away_team)
    if not stats:
        h2h_feats = {
            "h2h_games": 0,
            "h2h_home_win_rate": 0.33,
            "h2h_draw_rate": 0.33,
            "h2h_goal_diff": 0,
        }
    else:
        total = stats.get("total_games", 0)
        h2h_feats = {
            "h2h_games": total,
            "h2h_home_win_rate": stats.get("home_wins", 0) / total if total > 0 else 0.33,
            "h2h_draw_rate": stats.get("draws", 0) / total if total > 0 else 0.33,
            "h2h_goal_diff": stats.get("avg_goal_diff", 0),
        }
    
    # 球队特征
    team_data = predictor.team_data
    home_stats = team_data.get_team(home_team)
    away_stats = team_data.get_team(away_team)
    
    home_elo = home_stats.get("elo", 1800) if home_stats else 1800
    away_elo = away_stats.get("elo", 1800) if away_stats else 1800
    
    elo_gap = abs(home_elo - away_elo)
    expected_draw_rate = max(0, 0.35 - elo_gap * 0.0005)
    home_boost = home_stats.get("home_advantage_boost", 1.0) if home_stats else 1.0
    
    # 淘汰赛标识
    is_knockout = 1 if stage in ["knockout", "16强", "8强", "半决赛", "决赛", "quarter", "semi", "final"] else 0
    
    return [
        elo_feats["home_elo"],
        elo_feats["away_elo"],
        elo_feats["elo_diff"],
        elo_feats["elo_diff_abs"],
        elo_feats["elo_ratio"],
        h2h_feats["h2h_games"],
        h2h_feats["h2h_home_win_rate"],
        h2h_feats["h2h_draw_rate"],
        h2h_feats["h2h_goal_diff"],
        elo_gap,
        expected_draw_rate,
        home_boost,
        1 if home_stats and home_stats.get("famous_players") else 0,
        1 if away_stats and away_stats.get("famous_players") else 0,
        is_knockout,
    ]


FEATURE_NAMES = [
    "home_elo", "away_elo", "elo_diff", "elo_diff_abs", "elo_ratio",
    "h2h_games", "h2h_home_win_rate", "h2h_draw_rate", "h2h_goal_diff",
    "elo_gap", "expected_draw_rate", "home_boost",
    "home_has_players", "away_has_players", "is_knockout"
]


def build_dataset(tournament=None):
    """构建数据集
    
    Args:
        tournament: None=全部, "worldcup"=世界杯, "euro"=欧洲杯
    """
    predictor = UnifiedPredictor()
    le_result = LabelEncoder()
    le_result.fit(["away", "draw", "home"])
    
    X = []
    y = []
    match_info = []
    
    for year, matches in HISTORICAL_MATCHES.items():
        # 过滤赛事
        if tournament == "worldcup" and "Euro" in year:
            continue
        if tournament == "euro" and "Euro" not in year:
            continue
        
        for m in matches:
            home = m["home"]
            away = m["away"]
            score = m["score"]
            stage = m["stage"]
            
            features = get_features(home, away, predictor, stage)
            result = get_actual_result(score)
            label = le_result.transform([result])[0]
            
            X.append(features)
            y.append(label)
            match_info.append({
                "year": year,
                "home": home,
                "away": away,
                "score": score,
                "stage": stage,
                "result": result,
            })
    
    return np.array(X), np.array(y), le_result, match_info


def train_model(X, y, feature_names, model_name="模型"):
    """训练XGBoost模型"""
    unique, counts = np.unique(y, return_counts=True)
    class_weight = {c: len(y) / (len(unique) * count) for c, count in zip(unique, counts)}
    sample_weights = np.array([class_weight[yi] for yi in y])
    
    print(f"\n{model_name} - 类别分布: away={counts[0]}, draw={counts[1]}, home={counts[2]}")
    
    # 保守参数
    params = {
        "objective": "multi:softprob",
        "num_class": 3,
        "max_depth": 2,
        "learning_rate": 0.03,
        "n_estimators": 50,
        "min_child_weight": 10,
        "subsample": 0.6,
        "colsample_bytree": 0.6,
        "reg_alpha": 0.5,
        "reg_lambda": 2.0,
        "random_state": 42,
        "verbosity": 0,
    }
    
    model = xgb.XGBClassifier(**params)
    
    # 5折交叉验证
    cv_scores = cross_val_score(model, X, y, cv=5, scoring="accuracy")
    print(f"{model_name} - 5折CV准确率: {cv_scores.mean()*100:.1f}% (+/- {cv_scores.std()*2*100:.1f}%)")
    
    model.fit(X, y, sample_weight=sample_weights)
    return model


def evaluate_model(model, X, y, le_result, match_info, model_name="模型"):
    """评估模型"""
    y_pred = model.predict(X)
    
    total = len(y)
    correct = (y_pred == y).sum()
    acc = correct / total * 100
    
    draw_label = le_result.transform(["draw"])[0]
    
    print(f"\n{model_name} - 总体: {acc:.1f}% ({correct}/{total})")
    
    # 按年份
    years = sorted(set(m["year"] for m in match_info))
    for year in years:
        year_match_indices = [i for i, m in enumerate(match_info) if m["year"] == year]
        y_year = y[year_match_indices]
        y_pred_year = y_pred[year_match_indices]
        correct_year = (y_pred_year == y_year).sum()
        acc_year = correct_year / len(year_match_indices) * 100
        
        # 平局统计
        draw_mask = y_year == draw_label
        draw_count = draw_mask.sum()
        if draw_count > 0:
            draw_correct = (y_pred_year[draw_mask] == y_year[draw_mask]).sum()
            draw_acc = draw_correct / draw_count * 100
            print(f"  {year}: {acc_year:.1f}% ({correct_year}/{len(year_match_indices)}) | 平局: {draw_acc:.1f}% ({draw_correct}/{draw_count})")
        else:
            print(f"  {year}: {acc_year:.1f}% ({correct_year}/{len(year_match_indices)})")
    
    return acc


def main():
    print("=" * 60)
    print("🏆 分赛事ML模型训练")
    print("=" * 60)
    
    predictor = UnifiedPredictor()
    
    # 1. 训练世界杯模型
    print("\n📊 步骤1: 训练世界杯模型...")
    X_wc, y_wc, le_wc, info_wc = build_dataset("worldcup")
    print(f"世界杯数据集: {len(X_wc)}场比赛")
    model_wc = train_model(X_wc, y_wc, FEATURE_NAMES, "世界杯")
    evaluate_model(model_wc, X_wc, y_wc, le_wc, info_wc, "世界杯")
    
    # 2. 训练欧洲杯模型
    print("\n📊 步骤2: 训练欧洲杯模型...")
    X_euro, y_euro, le_euro, info_euro = build_dataset("euro")
    print(f"欧洲杯数据集: {len(X_euro)}场比赛")
    model_euro = train_model(X_euro, y_euro, FEATURE_NAMES, "欧洲杯")
    evaluate_model(model_euro, X_euro, y_euro, le_euro, info_euro, "欧洲杯")
    
    # 3. 训练全量模型
    print("\n📊 步骤3: 训练全量模型...")
    X_all, y_all, le_all, info_all = build_dataset(None)
    print(f"全量数据集: {len(X_all)}场比赛")
    model_all = train_model(X_all, y_all, FEATURE_NAMES, "全量")
    evaluate_model(model_all, X_all, y_all, le_all, info_all, "全量")
    
    # 4. 保存模型
    print("\n💾 保存模型...")
    model_data = {
        "worldcup": {"model": model_wc, "le": le_wc},
        "euro": {"model": model_euro, "le": le_euro},
        "all": {"model": model_all, "le": le_all},
        "feature_names": FEATURE_NAMES,
    }
    
    output_path = "../models/xgboost_tournament_models.pkl"
    with open(output_path, "wb") as f:
        pickle.dump(model_data, f)
    print(f"已保存到: {output_path}")
    
    # 5. 交叉验证 - 世界杯模型预测欧洲杯
    print("\n📊 步骤5: 交叉验证...")
    print("世界杯模型预测欧洲杯数据:")
    evaluate_model(model_wc, X_euro, y_euro, le_euro, info_euro, "WC→Euro")
    print("欧洲杯模型预测世界杯数据:")
    evaluate_model(model_euro, X_wc, y_wc, le_wc, info_wc, "Euro→WC")
    
    print("\n" + "=" * 60)
    print("✅ 分赛事模型训练完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
