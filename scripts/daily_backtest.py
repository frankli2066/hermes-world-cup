#!/usr/bin/env python3
"""
每日自动回测闭环
第二天对比昨天的预测 vs 实际结果 → 自动调整权重 → 更新准确率

用法：每天由Cron自动调用
"""

import sys
import os
import json
import csv
import urllib.request
from datetime import datetime, timedelta

BASE_DIR = os.path.expanduser("~/hermes-world-cup/")
DATA_DIR = os.path.join(BASE_DIR, "data", "daily")
RESULTS_DIR = os.path.join(BASE_DIR, "match-results")
WEIGHTS_FILE = os.path.join(BASE_DIR, "data/calibration/optimal_weights.json")
ACCURACY_FILE = os.path.join(BASE_DIR, "data/accuracy_tracking.json")

LEAGUE_CSV = {
    "EPL": ("https://www.football-data.co.uk/mmz4281/2526/E0.csv", "premier_league"),
    "La Liga": ("https://www.football-data.co.uk/mmz4281/2526/SP1.csv", "la_liga"),
    "Serie A": ("https://www.football-data.co.uk/mmz4281/2526/I1.csv", "serie_a"),
    "Bundesliga": ("https://www.football-data.co.uk/mmz4281/2526/D1.csv", "bundesliga"),
    "Ligue 1": ("https://www.football-data.co.uk/mmz4281/2526/F1.csv", "ligue_1"),
}

try:
    from scripts.team_names import TEAM_NAMES as TN
except:
    TN = {}


def load_predictions(filepath):
    """读取昨天的预测"""
    with open(filepath) as f:
        data = json.load(f)
    return data.get("predictions", data.get("matches", []))


def fetch_actual_results(date_str):
    """从football-data获取某天的实际比赛结果"""
    actuals = {}
    for league_name, (url, _) in LEAGUE_CSV.items():
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        try:
            resp = urllib.request.urlopen(req, timeout=15)
            content = resp.read().decode('utf-8-sig')
            reader = csv.DictReader(content.splitlines())
            for row in reader:
                row_date = row.get('Date', '').strip()
                if not row_date:
                    continue
                try:
                    parts = row_date.split('/')
                    iso_date = f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
                except:
                    continue
                if iso_date != date_str:
                    continue
                home = row.get('HomeTeam', '').strip()
                away = row.get('AwayTeam', '').strip()
                fthg = row.get('FTHG', '').strip()
                ftag = row.get('FTAG', '').strip()
                ftr = row.get('FTR', '').strip()
                if home and away and fthg and ftag:
                    key = f"{home}|{away}"
                    actuals[key] = {
                        "home": home, "away": away,
                        "home_score": int(fthg), "away_score": int(ftag),
                        "result": ftr
                    }
        except:
            continue
    return actuals


def compare_prediction(pred, actual):
    """对比单场预测与实际"""
    home_team = pred.get("home", pred.get("home_team", ""))
    away_team = pred.get("away", pred.get("away_team", ""))
    
    # 尝试多种key格式匹配
    keys_to_try = [
        f"{home_team}|{away_team}",
        f"{pred.get('home_name', home_team)}|{pred.get('away_name', away_team)}"
    ]
    
    matched = None
    for k in keys_to_try:
        if k in actual:
            matched = actual[k]
            break
    
    # 模糊匹配
    if not matched:
        for k, v in actual.items():
            if home_team.lower() in v["home"].lower() and away_team.lower() in v["away"].lower():
                matched = v
                break
    
    if not matched:
        return None
    
    # 解析预测结果
    hp = float(pred.get("home_prob", pred.get("home_win_prob", 0)))
    dp = float(pred.get("draw_prob", pred.get("draw_probability", 0)))
    ap = float(pred.get("away_prob", pred.get("away_win_prob", 0)))
    
    total = hp + dp + ap
    if total > 0:
        hp, dp, ap = hp/total, dp/total, ap/total
    
    # 最大概率的选项
    if hp > dp and hp > ap:
        predicted_outcome = "H"
    elif ap > hp and ap > dp:
        predicted_outcome = "A"
    else:
        predicted_outcome = "D"
    
    actual_outcome = matched["result"]
    
    # 置信度标记
    prob_diff = abs(hp - ap) if predicted_outcome != "D" else abs(dp - max(hp, ap))
    
    correct = predicted_outcome == actual_outcome
    
    return {
        "match": f"{home_team} vs {away_team}",
        "home_cn": TN.get(home_team, home_team),
        "away_cn": TN.get(away_team, away_team),
        "predicted": predicted_outcome,
        "actual": actual_outcome,
        "correct": correct,
        "home_prob": round(hp * 100, 1),
        "draw_prob": round(dp * 100, 1),
        "away_prob": round(ap * 100, 1),
        "prob_diff": round(prob_diff, 2),
        "actual_score": f"{matched['home_score']}-{matched['away_score']}",
        "confidence": "🟢高" if prob_diff > 0.25 else "🟡中" if prob_diff > 0.08 else "🔴低",
    }


def auto_adjust_weights(results, current_weights):
    """根据预测结果自动微调权重"""
    from copy import deepcopy
    
    if not results:
        return current_weights, "无结果，权重不变"
    
    correct = sum(1 for r in results if r["correct"])
    total = len(results)
    accuracy = correct / total if total > 0 else 0
    
    # 按置信度分析
    high_conf = [r for r in results if r["confidence"] == "🟢高"]
    med_conf = [r for r in results if r["confidence"] == "🟡中"]
    
    high_acc = sum(1 for r in high_conf if r["correct"]) / len(high_conf) if high_conf else 0
    med_acc = sum(1 for r in med_conf if r["correct"]) / len(med_conf) if med_conf else 0
    
    changes = []
    weights = deepcopy(current_weights) if isinstance(current_weights, dict) else {}
    
    # 如果高置信度 < 中置信度 → 抬高threshold
    current_threshold = 0.25
    if high_conf and med_conf and high_acc < med_acc and len(high_conf) >= 2:
        new_threshold = current_threshold + 0.03
        changes.append(f"高置信阈值: {current_threshold}→{new_threshold}")
        weights["high_confidence_threshold"] = new_threshold
    
    # 如果低准确率 → 降低market_weight，提高elo_weight
    if accuracy < 0.45 and total >= 3:
        old_mw = weights.get("market_weight", 0.60)
        new_mw = max(0.40, old_mw - 0.05)
        changes.append(f"市场权重: {old_mw}→{new_mw}")
        weights["market_weight"] = new_mw
        
        old_ew = weights.get("elo_weight", 0.20)
        new_ew = min(0.30, old_ew + 0.03)
        changes.append(f"Elo权重: {old_ew}→{new_ew}")
        weights["elo_weight"] = new_ew
    
    # 更新准确率记录
    weights["last_backtest"] = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "matches": total,
        "correct": correct,
        "accuracy": round(accuracy * 100, 1),
        "high_conf_accuracy": round(high_acc * 100, 1) if high_conf else 0,
        "med_conf_accuracy": round(med_acc * 100, 1) if med_conf else 0,
        "adjustments": changes
    }
    
    return weights, changes


def update_accuracy_tracking(results):
    """更新累计准确率统计"""
    with open(ACCURACY_FILE) as f:
        tracking = json.load(f)
    
    cumulative = tracking.get("cumulative", {})
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    correct = sum(1 for r in results if r["correct"])
    total = len(results)
    
    if total > 0:
        # 更新累计
        cumulative["total_predictions"] = cumulative.get("total_predictions", 0) + total
        cumulative["total_correct"] = cumulative.get("total_correct", 0) + correct
        cumulative["overall_accuracy"] = round(
            cumulative["total_correct"] / cumulative["total_predictions"] * 100, 1
        )
        
        # 按置信度统计
        for r in results:
            if r["confidence"] == "🟢高":
                cumulative["high_confidence_total"] = cumulative.get("high_confidence_total", 0) + 1
                if r["correct"]:
                    cumulative["high_confidence_correct"] = cumulative.get("high_confidence_correct", 0) + 1
            elif r["confidence"] == "🟡中":
                cumulative["medium_confidence_total"] = cumulative.get("medium_confidence_total", 0) + 1
                if r["correct"]:
                    cumulative["medium_confidence_correct"] = cumulative.get("medium_confidence_correct", 0) + 1
        
        # 高/中置信准确率
        hc = cumulative.get("high_confidence_total", 0)
        cumulative["high_confidence_accuracy"] = round(
            cumulative.get("high_confidence_correct", 0) / hc * 100, 1
        ) if hc > 0 else 0
        
        mc = cumulative.get("medium_confidence_total", 0)
        cumulative["medium_confidence_accuracy"] = round(
            cumulative.get("medium_confidence_correct", 0) / mc * 100, 1
        ) if mc > 0 else 0
        
        # 新增每日记录
        daily = tracking.get("daily_accuracy", [])
        daily.append({
            "date": today_str,
            "predictions": total,
            "correct": correct,
            "accuracy": round(correct / total * 100, 1) if total > 0 else 0
        })
        tracking["daily_accuracy"] = daily[-30:]  # 只保留30天
        tracking["cumulative"] = cumulative
        tracking["last_updated"] = datetime.now().isoformat()
        
        with open(ACCURACY_FILE, 'w') as f:
            json.dump(tracking, f, indent=2, ensure_ascii=False)
    
    return cumulative.get("overall_accuracy", 0)


def main():
    print("🔄 每日自动回测闭环\n")
    
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    # 寻找昨天的预测文件
    pred_files = [f for f in os.listdir(DATA_DIR) if f.startswith("predictions_")]
    today_pred = f"predictions_{datetime.now().strftime('%Y%m%d')}.json"
    yesterday_pred = f"predictions_{yesterday}.json"
    
    target_file = None
    if yesterday_pred in pred_files:
        target_file = os.path.join(DATA_DIR, yesterday_pred)
    elif today_pred in os.listdir(DATA_DIR):
        target_file = os.path.join(DATA_DIR, today_pred)
        yesterday = datetime.now().strftime("%Y-%m-%d")
    
    if not target_file:
        print(f"⚠️ 未找到昨日预测文件，尝试搜索最近3天的...")
        for i in range(1, 4):
            d = (datetime.now() - timedelta(days=i)).strftime("%Y%m%d")
            fname = f"predictions_{d}.json"
            if fname in pred_files:
                target_file = os.path.join(DATA_DIR, fname)
                yesterday = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
                print(f"   找到 {fname}")
                break
    
    if not target_file:
        print("📭 无预测文件可回测")
        return
    
    print(f"📂 读取预测: {os.path.basename(target_file)}")
    
    try:
        predictions = load_predictions(target_file)
    except:
        # 可能是不同格式
        import glob
        files = sorted(glob.glob(os.path.join(DATA_DIR, "predictions_*.json")), reverse=True)
        if files:
            target_file = files[0]
            predictions = load_predictions(target_file)
            print(f"   改用最新: {os.path.basename(target_file)}")
        else:
            print("❌ 读取失败")
            return
    
    print(f"📊 预测数: {len(predictions)}")
    print(f"\n📥 获取 {yesterday} 实际结果...")
    actuals = fetch_actual_results(yesterday)
    print(f"   实际比赛数: {len(actuals)}")
    
    if not actuals:
        print("⚠️ 没有实际结果数据，明天再试")
        return
    
    # 对比
    results = []
    for pred in predictions:
        r = compare_prediction(pred, actuals)
        if r:
            results.append(r)
    
    if not results:
        print("❌ 没有可对比的预测（比赛可能还没踢完）")
        return
    
    # 输出结果
    correct = sum(1 for r in results if r["correct"])
    print(f"\n{'='*50}")
    print(f"🎯 回测结果 ({yesterday})")
    print(f"{'='*50}")
    print(f"正确: {correct}/{len(results)} = {correct/len(results)*100:.1f}%")
    print()
    
    for r in results:
        mark = "✅" if r["correct"] else "❌"
        hcn = r["home_cn"]
        acn = r["away_cn"]
        print(f"  {mark} {hcn} vs {acn}")
        print(f"      预测: {r['home_prob']}%-{r['draw_prob']}%-{r['away_prob']}% ({r['confidence']})")
        print(f"      实际: {r['actual_score']} → {r['actual']}")
        print()
    
    # 置信度指标
    high = [r for r in results if r["confidence"] == "🟢高"]
    med = [r for r in results if r["confidence"] == "🟡中"]
    low = [r for r in results if r["confidence"] == "🔴低"]
    
    for label, group in [("🟢高信心", high), ("🟡中信心", med), ("🔴低信心", low)]:
        if group:
            c = sum(1 for r in group if r["correct"])
            print(f"  {label}: {c}/{len(group)} = {c/len(group)*100:.1f}%")
    
    # 自动调整权重
    with open(WEIGHTS_FILE) as f:
        current_weights = json.load(f)
    
    new_weights, changes = auto_adjust_weights(results, current_weights)
    
    if changes:
        print(f"\n⚙️ 自动调整:")
        for c in changes:
            print(f"  • {c}")
        
        with open(WEIGHTS_FILE, 'w') as f:
            json.dump(new_weights, f, indent=2, ensure_ascii=False)
        print("  ✅ 权重已更新")
    else:
        print("\n⚙️ 无需调整，权重保留")
    
    # 更新准确率统计
    overall = update_accuracy_tracking(results)
    print(f"\n📈 累计准确率: {overall}%")
    
    return results


if __name__ == "__main__":
    main()
