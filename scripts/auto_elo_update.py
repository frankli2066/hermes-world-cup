#!/usr/bin/env python3
"""
自动Elo更新脚本
从 football-data.co.uk 获取最新比赛结果，自动更新Elo评分
每日由Cron调用

用法: python3 auto_elo_update.py
"""

import sys
import os
import json
import csv
import urllib.request
from datetime import datetime, timedelta

BASE_DIR = os.path.expanduser("~/hermes-world-cup/")
RESULTS_DIR = os.path.join(BASE_DIR, "match-results/")
os.makedirs(RESULTS_DIR, exist_ok=True)

# football-data联赛映射
LEAGUE_CSV = {
    "EPL": ("https://www.football-data.co.uk/mmz4281/2526/E0.csv", "premier_league"),
    "La Liga": ("https://www.football-data.co.uk/mmz4281/2526/SP1.csv", "la_liga"),
    "Serie A": ("https://www.football-data.co.uk/mmz4281/2526/I1.csv", "serie_a"),
    "Bundesliga": ("https://www.football-data.co.uk/mmz4281/2526/D1.csv", "bundesliga"),
    "Ligue 1": ("https://www.football-data.co.uk/mmz4281/2526/F1.csv", "ligue_1"),
}


def fetch_results_from_csv(url: str, league: str) -> list:
    """从football-data CSV获取比赛结果"""
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        content = resp.read().decode('utf-8-sig')
        reader = csv.DictReader(content.splitlines())
        matches = []
        for row in reader:
            date_str = row.get('Date', '').strip()
            home = row.get('HomeTeam', '').strip()
            away = row.get('AwayTeam', '').strip()
            fthg = row.get('FTHG', '').strip()
            ftag = row.get('FTAG', '').strip()
            ftr = row.get('FTR', '').strip()

            if not date_str or not home or not away or not fthg or not ftag:
                continue

            # 日期转换 DD/MM/YYYY → YYYY-MM-DD
            try:
                parts = date_str.split('/')
                if len(parts) == 3:
                    iso_date = f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
                else:
                    continue
            except:
                continue

            matches.append({
                "date": iso_date,
                "home": home,
                "away": away,
                "home_score": int(fthg),
                "away_score": int(ftag),
                "stage": league,
                "neutral": False
            })
        return matches
    except Exception as e:
        print(f"  ⚠️ 获取{league}数据失败: {e}")
        return []


def save_results_to_file(date_str: str, matches: list):
    """将比赛结果保存为本地JSON文件"""
    if not matches:
        return 0
    
    result_file = os.path.join(RESULTS_DIR, f"results_{date_str}.json")
    existing = []
    if os.path.exists(result_file):
        with open(result_file) as f:
            existing = json.load(f).get("matches", [])
    
    # 去重
    existing_keys = {(m["home"], m["away"]) for m in existing}
    new_matches = [m for m in matches if (m["home"], m["away"]) not in existing_keys]
    
    if not new_matches:
        return 0
    
    all_matches = existing + new_matches
    with open(result_file, 'w') as f:
        json.dump({"date": date_str, "matches": all_matches, "source": "football-data.co.uk"}, f, indent=2)
    
    return len(new_matches)


def run_elo_update():
    """主流程"""
    sys.path.insert(0, os.path.join(BASE_DIR, "scripts"))
    from elo_dynamic_updater import EloDynamicUpdater
    
    print("🔍 从 football-data.co.uk 获取最新比赛结果...")
    
    today = datetime.now()
    total_new = 0
    all_new_matches = []

    for league_name, (url, stage) in LEAGUE_CSV.items():
        matches = fetch_results_from_csv(url, stage)
        if not matches:
            continue
        
        # 取最近7天的比赛
        recent = [m for m in matches if m["date"] >= (today - timedelta(days=7)).strftime("%Y-%m-%d")]
        if not recent:
            continue
        
        print(f"  {league_name}: {len(matches)} 场总赛, {len(recent)} 场近7天")
        
        # 按日期分组保存
        by_date = {}
        for m in recent:
            by_date.setdefault(m["date"], []).append(m)
        
        for date_str, day_matches in sorted(by_date.items()):
            saved = save_results_to_file(date_str, day_matches)
            if saved > 0:
                total_new += saved
                all_new_matches.extend(day_matches)
                print(f"    ✅ 新增 {saved} 场 ({date_str})")
    
    if total_new == 0:
        print("\n📭 无新比赛结果，Elo无需更新")
        return
    
    print(f"\n📊 共新增 {total_new} 场比赛，开始更新Elo...")
    
    updater = EloDynamicUpdater()
    
    # 按日期逐日更新Elo
    by_date = {}
    for m in all_new_matches:
        by_date.setdefault(m["date"], []).append(m)
    
    total_updates = 0
    for date_str in sorted(by_date.keys()):
        updates = updater.update_from_results_file(date_str)
        if updates:
            total_updates += len(updates)
            print(f"  ✅ {date_str}: {len(updates)} 场Elo更新")
    
    print(f"\n🎯 Elo更新完成: {total_updates} 场比赛, {total_new} 条新记录")
    
    # 显示Top 10
    updater.show_recent_updates(10)


if __name__ == "__main__":
    run_elo_update()
