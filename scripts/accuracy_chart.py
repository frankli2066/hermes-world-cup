#!/usr/bin/env python3
"""
预测准确率可视化

功能：
1. 记录每次预测和结果
2. 生成准确率趋势图
3. 显示各联赛/投注类型的准确率统计
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

# 尝试导入matplotlib
try:
    import matplotlib
    matplotlib.use('Agg')  # 无头模式
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


DATA_DIR = Path(__file__).parent.parent / "data" / "daily"
ACCURACY_FILE = DATA_DIR / "accuracy_history.json"


def load_accuracy_history() -> dict:
    """加载准确率历史"""
    if not ACCURACY_FILE.exists():
        return {'predictions': [], 'stats': {}}

    with open(ACCURACY_FILE) as f:
        return json.load(f)


def save_accuracy_history(history: dict):
    """保存准确率历史"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(ACCURACY_FILE, 'w') as f:
        json.dump(history, f, indent=2)


def add_prediction_result(prediction: dict, result: dict):
    """
    添加预测结果

    prediction = {
        'date': '2026-04-15',
        'home': 'Chelsea',
        'away': 'Man City',
        'league': 'EPL',
        'recommendation': 'Away',
        'recommended_team': 'Manchester City',
        'top_scores': ['0-2', '0-1', '1-2'],
        'predicted_winner': 'Manchester City',
        'predicted_over_25': True,
    }

    result = {
        'home_goals': 0,
        'away_goals': 3,
        'actual_winner': 'Away',  # 'Home', 'Away', 'Draw'
        'actual_score': '0-3',
        'actual_over_25': True,
    }
    """
    history = load_accuracy_history()

    # 判断是否命中
    wdl_hit = prediction['predicted_winner'] == result['actual_winner']
    score_hit = result['actual_score'] in prediction.get('top_scores', [])
    over_hit = prediction.get('predicted_over_25') == result.get('actual_over_25')

    record = {
        'timestamp': datetime.now().isoformat(),
        **prediction,
        **result,
        'wdl_hit': wdl_hit,
        'score_hit': score_hit,
        'over_hit': over_hit,
    }

    history['predictions'].append(record)

    # 更新统计
    stats = history.get('stats', {})

    # 总体统计
    total = len(history['predictions'])
    wdl_correct = sum(1 for p in history['predictions'] if p['wdl_hit'])
    score_correct = sum(1 for p in history['predictions'] if p['score_hit'])
    over_correct = sum(1 for p in history['predictions'] if p['over_hit'])

    stats['total'] = total
    stats['wdl_accuracy'] = round(wdl_correct / total * 100, 1) if total > 0 else 0
    stats['score_accuracy'] = round(score_correct / total * 100, 1) if total > 0 else 0
    stats['over_accuracy'] = round(over_correct / total * 100, 1) if total > 0 else 0

    # 按联赛统计
    league = prediction.get('league', 'Unknown')
    if league not in stats:
        stats[league] = {'total': 0, 'wdl_correct': 0, 'score_correct': 0, 'over_correct': 0}

    stats[league]['total'] += 1
    if wdl_hit:
        stats[league]['wdl_correct'] += 1
    if score_hit:
        stats[league]['score_correct'] += 1
    if over_hit:
        stats[league]['over_correct'] += 1

    history['stats'] = stats
    save_accuracy_history(history)

    return {
        'wdl_hit': wdl_hit,
        'score_hit': score_hit,
        'over_hit': over_hit,
        'overall_accuracy': stats['wdl_accuracy']
    }


def generate_accuracy_chart(output_path: str = None) -> str:
    """
    生成准确率趋势图

    Returns:
        图表文件路径
    """
    if not HAS_MATPLOTLIB:
        return None

    history = load_accuracy_history()
    predictions = history.get('predictions', [])

    if len(predictions) < 2:
        return None

    # 准备数据
    dates = []
    wdl_acc = []
    score_acc = []
    over_acc = []

    for i, p in enumerate(predictions):
        try:
            ts = datetime.fromisoformat(p['timestamp'])
            dates.append(ts)

            # 计算累计准确率
            total = i + 1
            wdl = sum(1 for x in predictions[:i+1] if x['wdl_hit'])
            score = sum(1 for x in predictions[:i+1] if x['score_hit'])
            over = sum(1 for x in predictions[:i+1] if x['over_hit'])

            wdl_acc.append(wdl / total * 100)
            score_acc.append(score / total * 100)
            over_acc.append(over / total * 100)
        except:
            continue

    if len(dates) < 2:
        return None

    # 创建图表
    fig, ax = plt.subplots(figsize=(12, 6))

    wdl_label = f'胜平负 ({history["stats"].get("wdl_accuracy", 0):.1f}%)'
    score_label = f'比分 ({history["stats"].get("score_accuracy", 0):.1f}%)'
    over_label = f'大小球 ({history["stats"].get("over_accuracy", 0):.1f}%)'

    ax.plot(dates, wdl_acc, label=wdl_label,
            color='#2ecc71', linewidth=2, marker='o', markersize=4)
    ax.plot(dates, score_acc, label=score_label,
            color='#3498db', linewidth=2, marker='s', markersize=4)
    ax.plot(dates, over_acc, label=over_label,
            color='#e74c3c', linewidth=2, marker='^', markersize=4)

    ax.set_xlabel('日期', fontsize=12)
    ax.set_ylabel('准确率 (%)', fontsize=12)
    ax.set_title('📊 足球预测准确率趋势', fontsize=14, fontweight='bold')
    ax.legend(loc='lower right')
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0, 100)

    # 设置日期格式
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())

    plt.xticks(rotation=45)
    plt.tight_layout()

    # 保存
    if output_path is None:
        output_path = DATA_DIR / "accuracy_chart.png"

    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()

    return str(output_path)


def get_accuracy_report() -> str:
    """获取准确率报告文本"""
    history = load_accuracy_history()
    predictions = history.get('predictions', [])
    stats = history.get('stats', {})

    if not predictions:
        return "📊 暂无预测记录"

    lines = []
    lines.append("📊 <b>预测准确率报告</b>")
    lines.append(f"总预测场次: {stats.get('total', 0)}")
    lines.append("")

    # 总体准确率
    lines.append("🎯 <b>总体准确率</b>")
    lines.append(f"胜平负: {stats.get('wdl_accuracy', 0):.1f}%")
    lines.append(f"比分: {stats.get('score_accuracy', 0):.1f}%")
    lines.append(f"大小球: {stats.get('over_accuracy', 0):.1f}%")
    lines.append("")

    # 按联赛统计
    lines.append("🏆 <b>按联赛统计</b>")
    for league, data in stats.items():
        if isinstance(data, dict) and 'total' in data:
            wdl = data.get('wdl_correct', 0) / data['total'] * 100 if data['total'] > 0 else 0
            score = data.get('score_correct', 0) / data['total'] * 100 if data['total'] > 0 else 0
            lines.append(f"{league}: {data['total']}场 | 胜平负{wdl:.0f}% | 比分{score:.0f}%")

    return "\n".join(lines)


if __name__ == "__main__":
    # 测试
    print("=== 测试准确率可视化 ===")

    # 添加一些测试数据
    test_predictions = [
        {
            'date': '2026-04-10',
            'home': 'Arsenal',
            'away': 'Liverpool',
            'league': 'EPL',
            'predicted_winner': 'Draw',
            'recommended_team': 'Draw',
            'top_scores': ['1-1', '2-2', '0-0'],
            'predicted_over_25': True,
        },
        {
            'date': '2026-04-11',
            'home': 'Real Madrid',
            'away': 'Barcelona',
            'league': 'La Liga',
            'predicted_winner': 'Home',
            'recommended_team': 'Real Madrid',
            'top_scores': ['2-1', '3-1', '2-0'],
            'predicted_over_25': True,
        },
    ]

    test_results = [
        {'actual_winner': 'Draw', 'actual_score': '1-1', 'actual_over_25': True},
        {'actual_winner': 'Home', 'actual_score': '2-1', 'actual_over_25': True},
    ]

    print("添加测试数据...")
    for pred, result in zip(test_predictions, test_results):
        r = add_prediction_result(pred, result)
        print(f"  预测: {pred['home']} vs {pred['away']} -> {result['actual_score']} | 胜平负:{r['wdl_hit']} 比分:{r['score_hit']}")

    print()
    print(get_accuracy_report())

    # 生成图表
    chart_path = generate_accuracy_chart()
    if chart_path:
        print(f"\n图表已生成: {chart_path}")
    else:
        print("\n图表生成失败（需要至少2条预测记录）")
