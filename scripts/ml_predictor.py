#!/usr/bin/env python3
"""
机器学习预测器 - XGBoost模型
用于发现规则模型难以捕捉的非线性规律
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "core"))

import numpy as np
import xgboost as xgb
from sklearn.model_selection import cross_val_score
from sklearn.preprocessing import LabelEncoder

# 导入现有数据
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


def get_elo_features(home_team, away_team, predictor):
    """获取Elo相关特征"""
    home_elo = predictor.get_elo(home_team)
    away_elo = predictor.get_elo(away_team)
    
    elo_diff = home_elo - away_elo
    elo_sum = home_elo + away_elo
    elo_ratio = home_elo / away_elo if away_elo > 0 else 1.0
    
    return {
        "home_elo": home_elo,
        "away_elo": away_elo,
        "elo_diff": elo_diff,
        "elo_diff_abs": abs(elo_diff),
        "elo_sum": elo_sum,
        "elo_ratio": elo_ratio,
    }


def get_h2h_features(home_team, away_team, predictor):
    """获取历史交锋特征"""
    h2h_db = predictor.h2h
    
    # 获取历史交锋统计
    stats = h2h_db.get_h2h_stats(home_team, away_team)
    
    if not stats:
        return {
            "h2h_games": 0,
            "h2h_home_wins": 0,
            "h2h_away_wins": 0,
            "h2h_draws": 0,
            "h2h_home_win_rate": 0.33,
            "h2h_draw_rate": 0.33,
            "h2h_goal_diff": 0,
        }
    
    total = stats.get("total_games", 0)
    home_wins = stats.get("home_wins", 0)
    away_wins = stats.get("away_wins", 0)
    draws = stats.get("draws", 0)
    goal_diff = stats.get("avg_goal_diff", 0)
    
    return {
        "h2h_games": total,
        "h2h_home_wins": home_wins / total if total > 0 else 0,
        "h2h_away_wins": away_wins / total if total > 0 else 0,
        "h2h_draws": draws / total if total > 0 else 0,
        "h2h_home_win_rate": home_wins / total if total > 0 else 0.33,
        "h2h_draw_rate": draws / total if total > 0 else 0.33,
        "h2h_goal_diff": goal_diff,
    }


def get_team_features(home_team, away_team, predictor):
    """获取球队特征"""
    team_data = predictor.team_data
    h2h_db = predictor.h2h
    
    home_stats = team_data.get_team(home_team)
    away_stats = team_data.get_team(away_team)
    
    # 从球队数据提取特征
    home_elo = home_stats.get("elo", 1800) if home_stats else 1800
    away_elo = away_stats.get("elo", 1800) if away_stats else 1800
    
    # 计算Elo差异带来的平局概率影响
    # Elo越接近，平局概率越高
    elo_gap = abs(home_elo - away_elo)
    expected_draw_rate = max(0, 0.35 - elo_gap * 0.0005)  # Elo差距越大，平局概率越低
    
    # 主场优势
    home_boost = home_stats.get("home_advantage_boost", 1.0) if home_stats else 1.0
    
    return {
        "elo_gap": elo_gap,
        "expected_draw_rate": expected_draw_rate,
        "home_boost": home_boost,
        "home_has_players": 1 if home_stats and home_stats.get("famous_players") else 0,
        "away_has_players": 1 if away_stats and away_stats.get("famous_players") else 0,
    }


def build_dataset():
    """构建机器学习数据集"""
    predictor = UnifiedPredictor()
    
    # 标签编码器 - away=0, draw=1, home=2
    le_result = LabelEncoder()
    le_result.fit(["away", "draw", "home"])
    
    # 特征名称 - 移除year以减少过拟合
    feature_names = [
        "home_elo", "away_elo", "elo_diff", "elo_diff_abs", "elo_ratio",
        "h2h_games", "h2h_home_win_rate", "h2h_draw_rate", "h2h_goal_diff",
        "elo_gap", "expected_draw_rate", "home_boost",
        "home_has_players", "away_has_players",
        "is_knockout",
    ]
    
    X = []
    y = []
    match_info = []
    
    for year, year_matches in HISTORICAL_MATCHES.items():
        for m in year_matches:
            home = m["home"]
            away = m["away"]
            score = m.get("score", "0-0")
            stage = m.get("stage", "group")
            
            # 获取特征
            elo_feats = get_elo_features(home, away, predictor)
            h2h_feats = get_h2h_features(home, away, predictor)
            team_feats = get_team_features(home, away, predictor)
            
            is_knockout = 1 if stage in ["knockout", "16强", "8强", "半决赛", "决赛", "quarter", "semi", "final"] else 0
            
            features = [
                elo_feats["home_elo"],
                elo_feats["away_elo"],
                elo_feats["elo_diff"],
                elo_feats["elo_diff_abs"],
                elo_feats["elo_ratio"],
                h2h_feats["h2h_games"],
                h2h_feats["h2h_home_win_rate"],
                h2h_feats["h2h_draw_rate"],
                h2h_feats["h2h_goal_diff"],
                team_feats["elo_gap"],
                team_feats["expected_draw_rate"],
                team_feats["home_boost"],
                team_feats["home_has_players"],
                team_feats["away_has_players"],
                is_knockout,
            ]
            
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
                "features": {k: v for k, v in zip(feature_names, features)}
            })
    
    return np.array(X), np.array(y), feature_names, le_result, match_info


def train_xgboost_model(X, y, feature_names):
    """训练XGBoost模型"""
    # 计算类别权重（平局样本较少）
    unique, counts = np.unique(y, return_counts=True)
    class_weight = {c: len(y) / (len(unique) * count) for c, count in zip(unique, counts)}
    sample_weights = np.array([class_weight[yi] for yi in y])
    
    print(f"\n类别分布: away={counts[0]}, draw={counts[1]}, home={counts[2]}")
    print(f"类别权重: away={class_weight[0]:.2f}, draw={class_weight[1]:.2f}, home={class_weight[2]:.2f}")
    
    # XGBoost参数 - 极度保守，减少过拟合
    params = {
        "objective": "multi:softprob",
        "num_class": 3,
        "max_depth": 2,  # 极度减少深度
        "learning_rate": 0.03,  # 更低学习率
        "n_estimators": 50,  # 更少树
        "min_child_weight": 10,  # 更大最小样本
        "subsample": 0.6,
        "colsample_bytree": 0.6,
        "reg_alpha": 0.5,  # 更强L1正则化
        "reg_lambda": 2.0,  # 更强L2正则化
        "random_state": 42,
        "verbosity": 0,
    }
    
    model = xgb.XGBClassifier(**params)
    
    # 5折交叉验证
    cv_scores = cross_val_score(model, X, y, cv=5, scoring="accuracy")
    print(f"\n5折交叉验证准确率: {cv_scores.mean()*100:.1f}% (+/- {cv_scores.std()*2*100:.1f}%)")
    
    # 训练最终模型
    model.fit(X, y, sample_weight=sample_weights)
    
    return model


def analyze_feature_importance(model, feature_names):
    """分析特征重要性"""
    importances = model.feature_importances_
    indices = np.argsort(importances)[::-1]
    
    print("\n特征重要性排名:")
    print("=" * 50)
    for i, idx in enumerate(indices[:12]):
        print(f"{i+1}. {feature_names[idx]}: {importances[idx]:.4f}")
    
    return {feature_names[idx]: importances[idx] for idx in indices}


def evaluate_by_year(model, X, y, le_result, match_info):
    """按年份评估模型"""
    print("\n各年份准确率 (ML模型):")
    print("=" * 50)
    
    years = sorted(set(m["year"] for m in match_info))
    results = {}
    
    for year in years:
        year_indices = [i for i, m in enumerate(match_info) if m["year"] == year]
        X_year = X[year_indices]
        y_year = y[year_indices]
        
        y_pred = model.predict(X_year)
        accuracy = (y_pred == y_year).mean()
        
        # 平局准确率
        draw_mask = y_year == le_result.transform(["draw"])[0]
        if draw_mask.sum() > 0:
            draw_acc = (y_pred[draw_mask] == y_year[draw_mask]).mean()
            print(f"{year}: {accuracy*100:.1f}% (平局: {draw_acc*100:.1f}%)")
        else:
            print(f"{year}: {accuracy*100:.1f}%")
        
        results[year] = accuracy
    
    return results


def compare_with_rule_model(model, X, y, le_result, match_info, predictor):
    """对比ML模型和规则模型"""
    print("\nML模型 vs 规则模型 对比:")
    print("=" * 50)
    
    ml_correct = 0
    rule_correct = 0
    both_correct = 0
    both_wrong = 0
    
    for i, m in enumerate(match_info):
        home = m["home"]
        away = m["away"]
        stage = m["stage"]
        actual = m["result"]  # home, away, draw
        
        # ML预测
        ml_pred_idx = model.predict([X[i]])[0]
        ml_pred = le_result.inverse_transform([ml_pred_idx])[0]
        ml_is_correct = (ml_pred == actual)
        
        # 规则预测
        try:
            rule_result = predictor.predict(home, away, match_stage=stage)
            rule_pred = rule_result["prediction"]["recommended_team"]
            # 转换规则模型输出为统一格式
            if rule_pred == "平局":
                rule_pred = "draw"
            elif rule_pred == home:
                rule_pred = "home"
            else:
                rule_pred = "away"
            rule_is_correct = (rule_pred == actual)
        except Exception as e:
            print(f"规则预测错误 {home} vs {away}: {e}")
            rule_is_correct = False
        
        if ml_is_correct:
            ml_correct += 1
        if rule_is_correct:
            rule_correct += 1
        if ml_is_correct and rule_is_correct:
            both_correct += 1
        if not ml_is_correct and not rule_is_correct:
            both_wrong += 1
    
    total = len(match_info)
    print(f"ML模型: {ml_correct}/{total} = {ml_correct/total*100:.1f}%")
    print(f"规则模型: {rule_correct}/{total} = {rule_correct/total*100:.1f}%")
    print(f"两者都正确: {both_correct}")
    print(f"两者都错误: {both_wrong}")
    print(f"ML单独正确: {ml_correct - both_correct}")
    print(f"规则单独正确: {rule_correct - both_correct}")
    
    return ml_correct / total, rule_correct / total


def analyze_draw_predictions(model, X, y, le_result, match_info):
    """分析平局预测"""
    print("\n平局预测分析:")
    print("=" * 50)
    
    draw_indices = [i for i, m in enumerate(match_info) if m["result"] == "draw"]
    draw_label = le_result.transform(["draw"])[0]
    
    y_pred = model.predict(X)
    y_proba = model.predict_proba(X)
    
    # 预测为平局
    predicted_draw = [i for i in draw_indices if y_pred[i] == draw_label]
    # 实际是平局但没预测到
    missed_draw = [i for i in draw_indices if y_pred[i] != draw_label]
    
    print(f"实际平局: {len(draw_indices)}场")
    print(f"预测平局: {len(predicted_draw)}场")
    
    if predicted_draw:
        draw_correct = sum(1 for i in predicted_draw if y[i] == y_pred[i])
        print(f"预测平局准确: {draw_correct}/{len(predicted_draw)} = {draw_correct/len(predicted_draw)*100:.1f}%")
    
    if missed_draw:
        print(f"\n漏掉的平局 ({len(missed_draw)}场):")
        for i in missed_draw[:5]:
            m = match_info[i]
            proba = y_proba[i]
            print(f"  {m['home']} vs {m['away']} ({m['year']}): prob_draw={proba[1]:.2f}, 实际={m['result']}")
    
    # 找出预测为平局但实际不是的
    false_draw = [i for i in range(len(match_info)) if y_pred[i] == draw_label and y[i] != draw_label]
    if false_draw:
        print(f"\n错误预测平局 ({len(false_draw)}场):")
        for i in false_draw[:5]:
            m = match_info[i]
            print(f"  {m['home']} vs {m['away']} ({m['year']}): 预测=平局, 实际={m['result']}")


def create_ensemble_predictor(model, predictor, feature_names, le_result):
    """创建集成预测器"""
    
    def predict(home, away, match_stage="group", **kwargs):
        # 1. 规则模型预测
        rule_result = predictor.predict(home, away, match_stage=match_stage, **kwargs)
        rule_pred = rule_result["prediction"]["recommended_team"]
        rule_probs = [
            rule_result["prediction"]["away_win"],
            rule_result["prediction"]["draw"],
            rule_result["prediction"]["home_win"],
        ]
        
        # 2. ML特征
        elo_feats = get_elo_features(home, away, predictor)
        h2h_feats = get_h2h_features(home, away, predictor)
        team_feats = get_team_features(home, away, predictor)
        
        is_knockout = 1 if match_stage in ["knockout", "16强", "8强", "半决赛", "决赛", "quarter", "semi", "final"] else 0
        
        ml_features = [[
            elo_feats["home_elo"],
            elo_feats["away_elo"],
            elo_feats["elo_diff"],
            elo_feats["elo_diff_abs"],
            elo_feats["elo_ratio"],
            h2h_feats["h2h_games"],
            h2h_feats["h2h_home_win_rate"],
            h2h_feats["h2h_draw_rate"],
            h2h_feats["h2h_goal_diff"],
            team_feats["elo_gap"],
            team_feats["expected_draw_rate"],
            team_feats["home_boost"],
            team_feats["home_has_players"],
            team_feats["away_has_players"],
            is_knockout,
        ]]
        
        # 3. ML预测
        ml_pred_idx = model.predict(ml_features)[0]
        ml_pred = le_result.inverse_transform([ml_pred_idx])[0]
        ml_proba = model.predict_proba(ml_features)[0]
        
        # 4. 集成决策
        # 规则: away=0, draw=1, home=2
        # ML: away=0, draw=1, home=2
        rule_probs_ordered = [rule_probs[0], rule_probs[1], rule_probs[2]]  # away, draw, home
        
        # 加权平均
        combined = [0.4 * r + 0.6 * m for r, m in zip(rule_probs_ordered, ml_proba)]
        
        best_idx = np.argmax(combined)
        options = ["away", "draw", "home"]
        final_pred = options[best_idx]
        
        # 判断一致性
        rule_pred_norm = "draw" if rule_pred == "平局" else ("home" if "主" in rule_pred else "away")
        
        if rule_pred_norm == final_pred:
            confidence = "🟢 一致"
        else:
            confidence = "🟡 不一致"
        
        return {
            "home": home,
            "away": away,
            "rule_prediction": rule_pred,
            "rule_probs": {"away": rule_probs[0], "draw": rule_probs[1], "home": rule_probs[2]},
            "ml_prediction": ml_pred,
            "ml_probs": {"away": ml_proba[0], "draw": ml_proba[1], "home": ml_proba[2]},
            "final_prediction": final_pred,
            "confidence": confidence,
            "combined_probs": {"away": combined[0], "draw": combined[1], "home": combined[2]},
        }
    
    return predict


def main():
    print("=" * 60)
    print("🏆 世界杯预测 - XGBoost机器学习模型")
    print("=" * 60)
    
    # 1. 构建数据集
    print("\n📊 步骤1: 构建数据集...")
    X, y, feature_names, le_result, match_info = build_dataset()
    print(f"数据集大小: {len(X)}场比赛, {len(feature_names)}个特征")
    
    # 2. 训练模型
    print("\n🧠 步骤2: 训练XGBoost模型...")
    model = train_xgboost_model(X, y, feature_names)
    
    # 3. 特征重要性
    print("\n📈 步骤3: 分析特征重要性...")
    analyze_feature_importance(model, feature_names)
    
    # 4. 按年份评估
    print("\n📅 步骤4: 按年份评估...")
    evaluate_by_year(model, X, y, le_result, match_info)
    
    # 5. 对比规则模型
    print("\n🔄 步骤5: 对比ML模型和规则模型...")
    predictor = UnifiedPredictor()
    ml_acc, rule_acc = compare_with_rule_model(model, X, y, le_result, match_info, predictor)
    
    # 6. 分析平局预测
    print("\n🔍 步骤6: 分析平局预测...")
    analyze_draw_predictions(model, X, y, le_result, match_info)
    
    # 7. 创建集成预测器
    print("\n🔗 步骤7: 创建集成预测器...")
    ensemble_predict = create_ensemble_predictor(model, predictor, feature_names, le_result)
    
    # 测试
    print("\n测试集成预测器:")
    print("-" * 50)
    test_matches = [
        ("Germany", "Scotland"),
        ("Spain", "Italy"),
        ("Netherlands", "France"),
    ]
    
    for home, away in test_matches:
        result = ensemble_predict(home, away, match_stage="group")
        print(f"\n{home} vs {away}:")
        print(f"  规则: {result['rule_prediction']}")
        print(f"  ML: {result['ml_prediction']}")
        print(f"  最终: {result['final_prediction']} ({result['confidence']})")
    
    # 保存模型
    import pickle
    import os
    os.makedirs(os.path.dirname(__file__) + "/../models", exist_ok=True)
    model_path = os.path.dirname(__file__) + "/../models/xgboost_model.pkl"
    model_data = {
        "model": model,
        "feature_names": feature_names,
        "le_result": le_result,
    }
    with open(model_path, "wb") as f:
        pickle.dump(model_data, f)
    print(f"\n✅ 模型已保存到 {model_path}")
    
    return model, predictor, feature_names, le_result


if __name__ == "__main__":
    main()