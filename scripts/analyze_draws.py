#!/usr/bin/env python3
"""分析平局规律"""

import os
import sys

# 设置路径
script_dir = os.path.dirname(os.path.abspath(__file__))
core_dir = os.path.join(script_dir, "core")
sys.path.insert(0, core_dir)
sys.path.insert(0, script_dir)

from unified_predictor import UnifiedPredictor
from tournament_data import TournamentDataCollector
from team_data import TeamDataManager

def analyze_draws():
    collector = TournamentDataCollector()
    team_data = TeamDataManager()

    # 使用get_matches获取所有比赛
    all_matches = collector.get_matches(include_upset=True)

    # 分析平局比赛
    draws = []
    non_draws = []
    for m in all_matches:
        score = m.get('score', '0-0')
        parts = score.split('-')
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            if int(parts[0]) == int(parts[1]):
                draws.append(m)
            else:
                non_draws.append(m)

    print(f'总比赛数: {len(all_matches)}')
    print(f'平局比赛: {len(draws)} ({len(draws)/len(all_matches):.1%})')
    print(f'非平局比赛: {len(non_draws)}')
    print()

    # 分析平局的Elo差距
    draw_elo_diffs = []
    non_draw_elo_diffs = []

    for m in draws:
        h_elo = team_data.get_elo(m['home'])
        a_elo = team_data.get_elo(m['away'])
        draw_elo_diffs.append(abs(h_elo - a_elo))

    for m in non_draws:
        h_elo = team_data.get_elo(m['home'])
        a_elo = team_data.get_elo(m['away'])
        non_draw_elo_diffs.append(abs(h_elo - a_elo))

    print('=== Elo差距分析 ===')
    print(f'平局比赛平均Elo差距: {sum(draw_elo_diffs)/len(draw_elo_diffs):.0f}')
    print(f'非平局比赛平均Elo差距: {sum(non_draw_elo_diffs)/len(non_draw_elo_diffs):.0f}')
    print()

    # Elo差距分段分析
    def categorize_elo_diff(diff):
        if diff < 80:
            return '极小(<80)'
        elif diff < 120:
            return '较小(80-120)'
        elif diff < 180:
            return '中等(120-180)'
        else:
            return '较大(>180)'

    draw_cats = {}
    non_draw_cats = {}
    for d in draw_elo_diffs:
        cat = categorize_elo_diff(d)
        draw_cats[cat] = draw_cats.get(cat, 0) + 1
    for d in non_draw_elo_diffs:
        cat = categorize_elo_diff(d)
        non_draw_cats[cat] = non_draw_cats.get(cat, 0) + 1

    print('=== Elo差距 vs 平局率 ===')
    for cat in ['极小(<80)', '较小(80-120)', '中等(120-180)', '较大(>180)']:
        d = draw_cats.get(cat, 0)
        nd = non_draw_cats.get(cat, 0)
        total = d + nd
        if total > 0:
            draw_rate = d / total
            print(f'{cat}: 平局{d}场/总计{total}场 (平局率{draw_rate:.1%})')
    print()

    # 比分分布
    score_counts = {}
    for m in all_matches:
        score = m.get('score', '0-0')
        score_counts[score] = score_counts.get(score, 0) + 1

    sorted_scores = sorted(score_counts.items(), key=lambda x: -x[1])[:20]
    print('=== 常见比分 Top 20 ===')
    for score, count in sorted_scores:
        pct = count / len(all_matches)
        is_draw = score.count('-') == 1 and score.split('-')[0] == score.split('-')[1]
        marker = ' ← 平局' if is_draw else ''
        print(f'  {score}: {count}场 ({pct:.1%}){marker}')
    print()

    # 分析具体平局案例
    print('=== 具体平局案例 ===')
    for m in draws[:10]:
        h_elo = team_data.get_elo(m['home'])
        a_elo = team_data.get_elo(m['away'])
        diff = abs(h_elo - a_elo)
        home_name = m['home']
        away_name = m['away']
        score = m['score']
        print(f'{home_name} vs {away_name}: {score} (Elo差距: {diff})')

if __name__ == '__main__':
    analyze_draws()
