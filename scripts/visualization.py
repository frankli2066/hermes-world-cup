#!/usr/bin/env python3
"""
2026世界杯 - 可视化图表生成 v2.0
从最新数据文件读取，替代硬编码
"""

import json
import os
import glob
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')

plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'DejaVu Sans', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False

BASE_DIR = os.path.expanduser("~/hermes-world-cup/")
POLYMARKET_DIR = os.path.join(BASE_DIR, "polymarket/")
KNOCKOUT_DIR = os.path.join(BASE_DIR, "knockout/")


def get_latest_polymarket() -> dict:
    """从polymarket目录读取最新的冠军赔率数据"""
    files = glob.glob(os.path.join(POLYMARKET_DIR, "*-champion-odds.json"))
    if not files:
        return _default_champion_probs()
    latest = max(files, key=os.path.getmtime)
    try:
        with open(latest) as f:
            data = json.load(f)
            teams = data.get("teams", [])
            if teams:
                return {t["team"]: t["prob"] for t in teams}
    except Exception as e:
        print(f"⚠️ 读取Polymarket失败: {e}")
    return _default_champion_probs()


def get_latest_simulation() -> dict:
    """从knockout目录读取最新的模拟结果"""
    files = glob.glob(os.path.join(KNOCKOUT_DIR, "simulation-*.json"))
    if not files:
        return {}
    latest = max(files, key=os.path.getmtime)
    try:
        with open(latest) as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ 读取模拟结果失败: {e}")
        return {}


def _default_champion_probs() -> dict:
    """默认冠军概率（兜底）"""
    return {
        "Spain": 17.45, "France": 16.05, "England": 11.15,
        "Argentina": 8.90, "Brazil": 8.65, "Portugal": 6.90,
        "Germany": 5.30, "Netherlands": 3.25, "Norway": 2.30,
        "Japan": 1.95, "Italy": 1.80, "Belgium": 1.75,
        "Mexico": 1.50, "Uruguay": 1.30, "Morocco": 1.20,
    }


def _default_group_probs() -> dict:
    """默认小组赛概率（兜底）"""
    return {
        "Mexico": 70.0, "Chile": 56.5, "Italy": 79.7, "Brazil": 78.8,
        "USA": 66.1, "Germany": 75.2, "Netherlands": 74.8, "Belgium": 72.1,
        "Spain": 80.0, "France": 83.0, "Portugal": 86.0, "England": 76.0,
    }


def generate_champion_chart():
    """生成冠军概率图"""
    probs = get_latest_polymarket()
    if not probs:
        probs = _default_champion_probs()

    sorted_data = sorted(probs.items(), key=lambda x: x[1], reverse=True)[:15]
    teams = [t for t, _ in sorted_data]
    values = [v for _, v in sorted_data]

    fig, ax = plt.subplots(figsize=(12, 7))
    colors = plt.cm.RdYlGn([max(0.1, min(1.0, p/20)) for p in values])
    bars = ax.barh(teams[::-1], values[::-1], color=colors[::-1])

    ax.set_xlabel('Probability (%)', fontsize=12)
    title = f'2026 World Cup Champion Probability\n(Updated: {datetime.now().strftime("%Y-%m-%d %H:%M")})'
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.set_xlim(0, max(values) * 1.2)

    for bar, prob in zip(bars, values[::-1]):
        ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height()/2,
                f'{prob:.2f}%', va='center', fontsize=10)

    plt.tight_layout()
    save_path = os.path.join(BASE_DIR, "visualization/champion-probability.png")
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"✅ 冠军概率图已保存: {save_path}")
    return save_path


def generate_group_charts():
    """生成各组小组赛概率图"""
    sim = get_latest_simulation()
    group_results = sim.get("group_results", {}) if sim else {}

    if not group_results:
        print("⚠️ 无小组赛数据，跳过小组赛图表")
        return

    n_groups = len(group_results)
    cols = 3
    rows = (n_groups + cols - 1) // cols

    fig, axes = plt.subplots(rows, cols, figsize=(18, 5 * rows))
    axes = axes.flatten() if n_groups > 1 else [axes]

    for idx, (group_name, result) in enumerate(group_results.items()):
        ax = axes[idx]
        adv = result.get("advancement", {})
        if not adv:
            continue

        sorted_teams = sorted(adv.items(), key=lambda x: x[1]["qualify_prob"], reverse=True)
        teams = [t for t, _ in sorted_teams]
        quals = [s["qualify_prob"] for _, s in sorted_teams]

        colors = ["#2ecc71" if q > 50 else "#e74c3c" for q in quals]
        bars = ax.barh(teams, quals, color=colors)

        ax.set_xlim(0, 100)
        ax.set_xlabel('Qualification Probability (%)', fontsize=10)
        ax.set_title(f'Group {group_name}', fontsize=12, fontweight='bold')
        ax.axvline(x=50, color='orange', linestyle='--', alpha=0.7, label='50% threshold')

        for bar, q in zip(bars, quals):
            ax.text(bar.get_width() + 2, bar.get_y() + bar.get_height()/2,
                    f'{q:.0f}%', va='center', fontsize=9)

    for idx in range(len(group_results), len(axes)):
        axes[idx].axis('off')

    plt.tight_layout()
    save_path = os.path.join(BASE_DIR, "visualization/group-stage-probs.png")
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"✅ 小组赛概率图已保存: {save_path}")
    return save_path


def generate_knockout_bracket():
    """生成淘汰赛对阵图（文字版）"""
    sim = get_latest_simulation()
    knockout = sim.get("knockout_results", {}) if sim else {}
    champion_probs = knockout.get("champion_probs", {}) if knockout else {}

    if not champion_probs:
        print("⚠️ 无淘汰赛数据，跳过")
        return None

    sorted_champs = sorted(champion_probs.items(), key=lambda x: x[1], reverse=True)[:10]

    text = f"""
╔══════════════════════════════════════════════════════════════╗
║           2026 世界杯淘汰赛阶段 - 冠军概率 Top 10            ║
║                      生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}                      ║
╠══════════════════════════════════════════════════════════════╣
"""
    for i, (team, prob) in enumerate(sorted_champs, 1):
        bar = "█" * max(1, int(prob))
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "  "
        text += f"║  {medal} {i:>2}. {team:<20} {prob:>5.2f}% {bar:<15} ║\n"

    text += """╚══════════════════════════════════════════════════════════════╝"""

    save_path = os.path.join(BASE_DIR, "visualization/knockout-summary.txt")
    with open(save_path, "w", encoding="utf-8") as f:
        f.write(text)

    print(f"✅ 淘汰赛摘要已保存: {save_path}")
    return save_path


def generate_full_report():
    """生成完整可视化报告"""
    print(f"\n{'='*60}")
    print(f"📊 生成可视化报告")
    print(f"{'='*60}")

    # 1. 冠军概率图
    generate_champion_chart()

    # 2. 小组赛图
    generate_group_charts()

    # 3. 淘汰赛摘要
    generate_knockout_bracket()

    print(f"\n✅ 报告生成完成")


if __name__ == "__main__":
    generate_full_report()
