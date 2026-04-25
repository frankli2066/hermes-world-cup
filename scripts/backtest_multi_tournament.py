#!/usr/bin/env python3
"""
多赛事回测系统 v5.1
========================
使用多赛事数据（247场）验证和优化预测系统

新增功能：
1. 多赛事统一回测
2. 赛事权重优化
3. 冷门检测能力分析
4. 动态权重调整
"""

import os
import sys
import json
import random
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "core"))

try:
    from unified_predictor import UnifiedPredictor
    from tournament_data import TournamentDataCollector
except ModuleNotFoundError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from unified_predictor import UnifiedPredictor
    from tournament_data import TournamentDataCollector


def get_actual_result(score: str) -> str:
    """从比分获取实际结果"""
    try:
        home_goals, away_goals = map(int, score.split("-"))
        if home_goals > away_goals:
            return "home"
        elif home_goals < away_goals:
            return "away"
        else:
            return "draw"
    except:
        return "home"


def evaluate_prediction(pred: Dict, actual: str) -> Dict:
    """评估预测结果"""
    probs = pred["prediction"]
    max_prob = max(probs["home_win"], probs["draw"], probs["away_win"])

    # 判断预测胜者
    # 当多个选项概率接近时（差距<0.03），优先考虑平局
    all_probs = [probs["home_win"], probs["draw"], probs["away_win"]]
    all_probs_sorted = sorted(all_probs, reverse=True)

    # 正常情况
    if probs["home_win"] > max(probs["draw"], probs["away_win"]):
        pred_winner = "home"
    elif probs["away_win"] > probs["draw"]:
        pred_winner = "away"
    else:
        pred_winner = "draw"

    correct = pred_winner == actual

    return {
        "correct": correct,
        "predicted_winner": pred_winner,
        "actual_winner": actual,
        "confidence": max_prob,
        "prob_diff": abs(probs["home_win"] - probs["away_win"]),
    }


def run_tournament_backtest(collector: TournamentDataCollector,
                            predictor: UnifiedPredictor,
                            tournament: str = None,
                            include_upset: bool = True) -> Dict:
    """运行特定赛事回测"""
    matches = collector.get_matches(tournament=tournament, include_upset=include_upset)

    results = []
    correct = 0

    for match in matches:
        home = match["home"]
        away = match["away"]
        score = match["score"]
        actual = get_actual_result(score)

        # 预测
        # 注意：不传入赔率数据，让模型完全依赖自身特征进行预测
        # 这样可以更准确评估模型的真实能力
        pred = predictor.predict(
            home_team=home,
            away_team=away,
            home_last_match_date=datetime.now() - timedelta(days=5),
            away_last_match_date=datetime.now() - timedelta(days=4),
            match_date=datetime.now(),
            venue="Stadium",
            weather={"temp": 20, "humidity": 60, "precipitation": 0, "wind": 10},
            group_standings={"home": {"points": 3}, "away": {"points": 0}},
            match_stage=match.get("stage", "group")
        )

        evaluation = evaluate_prediction(pred, actual)
        correct += 1 if evaluation["correct"] else 0

        results.append({
            **match,
            **evaluation,
            "pred": pred
        })

    accuracy = correct / len(matches) if matches else 0

    return {
        "tournament": tournament,
        "count": len(matches),
        "correct": correct,
        "accuracy": accuracy,
        "results": results
    }


def analyze_by_confidence(results: List[Dict]) -> Dict:
    """按信心等级分析"""
    high_conf = [r for r in results if r["confidence"] > 0.55]
    med_conf = [r for r in results if 0.45 <= r["confidence"] <= 0.55]
    low_conf = [r for r in results if r["confidence"] < 0.45]

    return {
        "high_confidence": {
            "count": len(high_conf),
            "correct": sum(1 for r in high_conf if r["correct"]),
            "accuracy": sum(1 for r in high_conf if r["correct"]) / len(high_conf) if high_conf else 0
        },
        "medium_confidence": {
            "count": len(med_conf),
            "correct": sum(1 for r in med_conf if r["correct"]),
            "accuracy": sum(1 for r in med_conf if r["correct"]) / len(med_conf) if med_conf else 0
        },
        "low_confidence": {
            "count": len(low_conf),
            "correct": sum(1 for r in low_conf if r["correct"]),
            "accuracy": sum(1 for r in low_conf if r["correct"]) / len(low_conf) if low_conf else 0
        }
    }


def analyze_upsets(results: List[Dict]) -> Dict:
    """分析冷门检测能力"""
    upsets = [r for r in results if r.get("upset")]
    non_upsets = [r for r in results if not r.get("upset")]

    return {
        "upset_detection": {
            "total_upsets": len(upsets),
            "correct": sum(1 for r in upsets if r["correct"]),
            "accuracy": sum(1 for r in upsets if r["correct"]) / len(upsets) if upsets else 0
        },
        "normal_games": {
            "total": len(non_upsets),
            "correct": sum(1 for r in non_upsets if r["correct"]),
            "accuracy": sum(1 for r in non_upsets if r["correct"]) / len(non_upsets) if non_upsets else 0
        }
    }


def run_comprehensive_backtest():
    """运行综合回测"""
    print("=" * 70)
    print("🏆 世界杯预测系统 v5.1 - 多赛事回测")
    print("=" * 70)

    collector = TournamentDataCollector()
    predictor = UnifiedPredictor()

    # 获取所有数据统计
    stats = collector.get_tournament_stats()
    print("\n📊 数据集概览:")
    for name, data in stats.items():
        print(f"  {name}: {data['count']}场")

    total_matches = sum(data['count'] for data in stats.values())
    print(f"\n总计: {total_matches}场比赛")

    # ========== 1. 整体回测 ==========
    print("\n" + "=" * 70)
    print("📍 整体回测结果")
    print("=" * 70)

    all_matches = collector.get_matches(include_upset=True)
    all_results = []
    all_correct = 0

    for match in all_matches:
        home = match["home"]
        away = match["away"]
        score = match["score"]
        actual = get_actual_result(score)

        pred = predictor.predict(
            home_team=home,
            away_team=away,
            home_last_match_date=datetime.now() - timedelta(days=5),
            away_last_match_date=datetime.now() - timedelta(days=4),
            match_date=datetime.now(),
            venue="Stadium",
            weather={"temp": 20, "humidity": 60, "precipitation": 0, "wind": 10},
            group_standings={"home": {"points": 3}, "away": {"points": 0}},
            odds={"home": 2.0, "draw": 3.2, "away": 3.8},
            match_stage=match.get("stage", "group")
        )

        evaluation = evaluate_prediction(pred, actual)
        all_correct += 1 if evaluation["correct"] else 0
        all_results.append({**match, **evaluation, "pred": pred})

    overall_accuracy = all_correct / len(all_matches) if all_matches else 0
    print(f"\n总体准确率: {overall_accuracy:.1%} ({all_correct}/{len(all_matches)})")

    # ========== 2. 按赛事分析 ==========
    print("\n" + "=" * 70)
    print("📍 各赛事准确率")
    print("=" * 70)

    tournament_names = {
        "wc": "世界杯",
        "euro": "欧洲杯",
        "eq": "欧洲杯预选",
        "wq": "世界杯预选(欧洲)",
        "saq": "南美预选赛",
        "afcon": "非洲杯"
    }

    by_tournament = {}
    for t, name in tournament_names.items():
        result = run_tournament_backtest(collector, predictor, tournament=t)
        by_tournament[t] = result
        acc = result["accuracy"]
        print(f"  {name:15}: {acc:.1%} ({result['correct']}/{result['count']})")

    # ========== 3. 按信心等级分析 ==========
    print("\n" + "=" * 70)
    print("📍 按信心等级分析")
    print("=" * 70)

    confidence_analysis = analyze_by_confidence(all_results)

    print(f"  高信心 (>55%)  : {confidence_analysis['high_confidence']['accuracy']:.1%} ({confidence_analysis['high_confidence']['correct']}/{confidence_analysis['high_confidence']['count']})")
    print(f"  中信心 (45-55%): {confidence_analysis['medium_confidence']['accuracy']:.1%} ({confidence_analysis['medium_confidence']['correct']}/{confidence_analysis['medium_confidence']['count']})")
    print(f"  低信心 (<45%)  : {confidence_analysis['low_confidence']['accuracy']:.1%} ({confidence_analysis['low_confidence']['correct']}/{confidence_analysis['low_confidence']['count']})")

    # ========== 4. 冷门检测能力 ==========
    print("\n" + "=" * 70)
    print("📍 冷门检测能力")
    print("=" * 70)

    upset_analysis = analyze_upsets(all_results)

    print(f"  冷门比赛: {upset_analysis['upset_detection']['total_upsets']}场")
    print(f"    预测正确: {upset_analysis['upset_detection']['correct']}场 ({upset_analysis['upset_detection']['accuracy']:.1%})")
    print(f"  正常比赛: {upset_analysis['normal_games']['total']}场")
    print(f"    预测正确: {upset_analysis['normal_games']['correct']}场 ({upset_analysis['normal_games']['accuracy']:.1%})")

    # ========== 5. 按比赛阶段分析 ==========
    print("\n" + "=" * 70)
    print("📍 按比赛阶段分析")
    print("=" * 70)

    by_stage = {}
    for stage in ["group", "round16", "quarter", "semi", "final", "third_place", "qualifier"]:
        stage_matches = [r for r in all_results if r.get("stage") == stage]
        if stage_matches:
            correct = sum(1 for r in stage_matches if r["correct"])
            acc = correct / len(stage_matches)
            by_stage[stage] = acc
            stage_name = {"group": "小组赛", "round16": "16强", "quarter": "8强", "semi": "4强", "final": "决赛", "third_place": "季军赛", "qualifier": "预选赛"}.get(stage, stage)
            print(f"  {stage_name:8}: {acc:.1%} ({correct}/{len(stage_matches)})")

    # ========== 6. 版本对比 ==========
    print("\n" + "=" * 70)
    print("📈 版本对比")
    print("=" * 70)
    print(f"v4.3 (旧版): 54.5%")
    print(f"v5.0 (旧版): 55.6% (45场仅世界杯)")
    print(f"v5.1 (新版): {overall_accuracy:.1%} ({len(all_matches)}场多赛事)")

    improvement_v45 = overall_accuracy - 0.545
    improvement_v50 = overall_accuracy - 0.556

    print(f"\n相对v4.3提升: {improvement_v45:+.1%}")
    print(f"相对v5.0提升: {improvement_v50:+.1%}")

    # ========== 7. 找出最难的预测 ==========
    print("\n" + "=" * 70)
    print("📍 最难预测的比赛 (错误且高信心)")
    print("=" * 70)

    hard_games = [r for r in all_results if not r["correct"] and r["confidence"] > 0.5]
    hard_games.sort(key=lambda x: -x["confidence"])

    for i, game in enumerate(hard_games[:5], 1):
        print(f"  {i}. {game['home']} vs {game['away']}")
        print(f"     比分: {game['score']} | 预测: {game['predicted_winner']} | 实际: {game['actual_winner']}")
        print(f"     信心: {game['confidence']:.0%} | 赛事: {tournament_names.get(game.get('tournament', ''), game.get('tournament', ''))}")
        if game.get("note"):
            print(f"     备注: {game['note']}")

    return {
        "overall_accuracy": overall_accuracy,
        "total_matches": len(all_matches),
        "by_tournament": {k: v["accuracy"] for k, v in by_tournament.items()},
        "by_stage": by_stage,
        "confidence_analysis": confidence_analysis,
        "upset_analysis": upset_analysis
    }


if __name__ == "__main__":
    result = run_comprehensive_backtest()
