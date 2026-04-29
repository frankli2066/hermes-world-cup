#!/usr/bin/env python3
"""
混合集成模型 - 结合规则模型和ML模型
策略：
1. ML模型预测平局时 → 优先信任（100%准确率）
2. ML模型预测非平局，规则模型预测平局 → 降低信心
3. 其他情况 → 跟随规则模型
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "core"))

import pickle
import numpy as np
from backtest_unified import HISTORICAL_MATCHES
from core.unified_predictor import UnifiedPredictor


def load_tournament_models():
    """加载分赛事ML模型"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(script_dir, "..", "models", "xgboost_tournament_models.pkl")
    
    if os.path.exists(model_path):
        with open(model_path, "rb") as f:
            return pickle.load(f)
    return None


def get_ml_prediction(home, away, match_stage, model_data, predictor, tournament="all"):
    """获取ML模型预测
    
    Args:
        tournament: "worldcup", "euro", 或 "all"
    """
    # 提取特征
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
    
    # 选择模型
    if isinstance(model_data, dict) and "all" in model_data:
        # 分赛事模型格式
        if tournament == "euro" and "euro" in model_data:
            selected_model = model_data["euro"]
        elif tournament == "worldcup" and "worldcup" in model_data:
            selected_model = model_data["worldcup"]
        else:
            selected_model = model_data["all"]
        model = selected_model["model"]
        le_result = selected_model["le"]
    else:
        # 旧格式
        model = model_data["model"]
        le_result = model_data["le_result"]
    
    ml_pred_idx = model.predict(ml_features)[0]
    ml_pred = le_result.inverse_transform([ml_pred_idx])[0]
    ml_proba = model.predict_proba(ml_features)[0]
    
    return ml_pred, ml_proba, {
        "away": ml_proba[0],
        "draw": ml_proba[1],
        "home": ml_proba[2],
    }


def get_elo_features(home_team, away_team, predictor):
    home_elo = predictor.get_elo(home_team)
    away_elo = predictor.get_elo(away_team)
    return {
        "home_elo": home_elo,
        "away_elo": away_elo,
        "elo_diff": home_elo - away_elo,
        "elo_diff_abs": abs(home_elo - away_elo),
        "elo_ratio": home_elo / away_elo if away_elo > 0 else 1.0,
    }


def get_h2h_features(home_team, away_team, predictor):
    h2h_db = predictor.h2h
    stats = h2h_db.get_h2h_stats(home_team, away_team)
    if not stats:
        return {
            "h2h_games": 0,
            "h2h_home_win_rate": 0.33,
            "h2h_draw_rate": 0.33,
            "h2h_goal_diff": 0,
        }
    total = stats.get("total_games", 0)
    return {
        "h2h_games": total,
        "h2h_home_win_rate": stats.get("home_wins", 0) / total if total > 0 else 0.33,
        "h2h_draw_rate": stats.get("draws", 0) / total if total > 0 else 0.33,
        "h2h_goal_diff": stats.get("avg_goal_diff", 0),
    }


def get_team_features(home_team, away_team, predictor):
    team_data = predictor.team_data
    home_stats = team_data.get_team(home_team)
    away_stats = team_data.get_team(away_team)
    
    home_elo = home_stats.get("elo", 1800) if home_stats else 1800
    away_elo = away_stats.get("elo", 1800) if away_stats else 1800
    
    elo_gap = abs(home_elo - away_elo)
    expected_draw_rate = max(0, 0.35 - elo_gap * 0.0005)
    
    return {
        "elo_gap": elo_gap,
        "expected_draw_rate": expected_draw_rate,
        "home_boost": home_stats.get("home_advantage_boost", 1.0) if home_stats else 1.0,
        "home_has_players": 1 if home_stats and home_stats.get("famous_players") else 0,
        "away_has_players": 1 if away_stats and away_stats.get("famous_players") else 0,
    }


def ensemble_predict(home, away, match_stage, model_data, predictor, tournament="all"):
    """混合集成预测 - ML完全替代策略（当前最优）"""
    # 1. 获取规则模型预测
    rule_result = predictor.predict(home, away, match_stage=match_stage)
    rule_pred = rule_result["prediction"]["recommended_team"]
    rule_probs = {
        "home": rule_result["prediction"]["home_win"],
        "draw": rule_result["prediction"]["draw"],
        "away": rule_result["prediction"]["away_win"],
    }
    
    # 2. 获取ML模型预测
    ml_pred, ml_proba, ml_probs = get_ml_prediction(home, away, match_stage, model_data, predictor, tournament)
    
    # 3. 集成决策 - ML完全替代胜负预测
    # ML预测平局 → ML（100%准确）
    # ML预测非平局 → 完全用ML的胜负预测
    if ml_pred == "draw":
        final_pred = "平局"
        confidence = "ML平局"
    elif ml_pred == "home":
        final_pred = home
        confidence = "ML主胜"
    else:
        final_pred = away
        confidence = "ML客胜"
    
    return {
        "home": home,
        "away": away,
        "rule_prediction": rule_pred,
        "rule_probs": rule_probs,
        "ml_prediction": ml_pred,
        "ml_probs": ml_probs,
        "final_prediction": final_pred,
        "confidence": confidence,
    }


def get_actual_result(score, home_team, away_team):
    """从比分判断实际结果，返回主队名/客队名/平局"""
    home_goals, away_goals = map(int, score.split("-"))
    if home_goals == away_goals:
        return "平局"
    elif home_goals > away_goals:
        return home_team  # 主队获胜
    return away_team  # 客队获胜


def backtest_ensemble():
    """回测混合集成模型"""
    # 加载分赛事ML模型
    model_data = load_tournament_models()
    if model_data is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        model_path = os.path.join(script_dir, "..", "models", "xgboost_model.pkl")
        with open(model_path, "rb") as f:
            model_data = pickle.load(f)
        print("使用旧版模型进行回测")
    else:
        print("使用分赛事ML模型进行回测")
    
    predictor = UnifiedPredictor()
    
    # 确定label encoder - 旧格式用le_result，新格式用all模型的le
    if isinstance(model_data, dict) and "all" in model_data:
        le_result = model_data["all"]["le"]
    else:
        le_result = model_data["le_result"]
    
    # 统计
    total = 0
    correct = 0
    by_year = {}
    
    # 平局预测统计
    draw_total = 0
    draw_correct = 0
    draw_predicted = 0
    
    for year, year_matches in HISTORICAL_MATCHES.items():
        year_correct = 0
        year_total = 0
        year_draw_total = 0
        year_draw_correct = 0
        year_draw_predicted = 0
        
        # 根据年份判断赛事类型
        # 世界杯用worldcup模型，欧洲杯数据少用all模型
        if "Euro" in year:
            tournament = "all"  # 欧洲杯用全量模型（包含世界杯数据，更稳定）
        else:
            tournament = "worldcup"
        
        for m in year_matches:
            home = m["home"]
            away = m["away"]
            score = m.get("score", "0-0")
            stage = m.get("stage", "group")
            
            # 获取实际结果
            actual = get_actual_result(score, home, away)
            is_draw = actual == "平局"
            
            # 集成预测 - 根据赛事选择模型
            result = ensemble_predict(home, away, stage, model_data, predictor, tournament)
            predicted = result["final_prediction"]
            
            # 判断是否正确
            is_correct = (predicted == actual)
            
            total += 1
            year_total += 1
            if is_correct:
                correct += 1
                year_correct += 1
            
            if is_draw:
                draw_total += 1
                year_draw_total += 1
                if is_correct:
                    draw_correct += 1
                    year_draw_correct += 1
                if predicted == "平局":
                    draw_predicted += 1
                    year_draw_predicted += 1
        
        by_year[year] = {
            "total": year_total,
            "correct": year_correct,
            "accuracy": year_correct / year_total if year_total > 0 else 0,
            "draw_total": year_draw_total,
            "draw_correct": year_draw_correct,
            "draw_accuracy": year_draw_correct / year_draw_total if year_draw_total > 0 else 0,
            "draw_predicted": year_draw_predicted,
        }
    
    # 打印结果
    print("=" * 60)
    print("🏆 混合集成模型回测结果")
    print("=" * 60)
    print(f"\n总体准确率: {correct}/{total} = {correct/total*100:.1f}%")
    print(f"平局预测: {draw_correct}/{draw_total} = {draw_correct/draw_total*100:.1f}% (预测{draw_predicted}场)")
    
    print("\n各年份准确率:")
    print("-" * 60)
    for year in sorted(by_year.keys()):
        stats = by_year[year]
        print(f"{year}: {stats['accuracy']*100:.1f}% ({stats['correct']}/{stats['total']}) | 平局: {stats['draw_accuracy']*100:.1f}% ({stats['draw_correct']}/{stats['draw_total']})")
    
    return by_year


def main():
    print("=" * 60)
    print("🔗 混合集成模型 - 规则 + ML (分赛事模型)")
    print("=" * 60)
    
    backtest_ensemble()
    
    print("\n" + "=" * 60)
    print("测试预测:")
    print("=" * 60)
    
    # 尝试加载分赛事模型，否则使用旧模型
    model_data = load_tournament_models()
    if model_data is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        model_path = os.path.join(script_dir, "..", "models", "xgboost_model.pkl")
        with open(model_path, "rb") as f:
            model_data = pickle.load(f)
        print("使用旧版模型")
    else:
        print("使用分赛事ML模型")
    
    predictor = UnifiedPredictor()
    
    test_matches = [
        ("Germany", "Scotland"),
        ("Spain", "Italy"),
        ("Netherlands", "France"),
    ]
    
    for home, away in test_matches:
        result = ensemble_predict(home, away, "group", model_data, predictor)
        print(f"\n{home} vs {away}:")
        print(f"  规则: {result['rule_prediction']} (主胜={result['rule_probs']['home']:.2f}, 平局={result['rule_probs']['draw']:.2f}, 客胜={result['rule_probs']['away']:.2f})")
        print(f"  ML: {result['ml_prediction']} (主胜={result['ml_probs']['home']:.2f}, 平局={result['ml_probs']['draw']:.2f}, 客胜={result['ml_probs']['away']:.2f})")
        print(f"  最终: {result['final_prediction']} ({result['confidence']})")


if __name__ == "__main__":
    main()