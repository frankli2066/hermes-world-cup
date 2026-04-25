#!/usr/bin/env python3
"""
从Flashscore获取真实赛程数据 v2
这个脚本解析Flashscore页面中的JavaScript数据格式
"""
import subprocess
import re
import json
from datetime import datetime, timezone, timedelta

def fetch_flashscore_fixtures(league_path):
    """从Flashscore获取赛程数据"""
    url = f"https://www.flashscore.com/football/{league_path}/fixtures/"

    cmd = [
        'curl', '-s', '-L', '--compressed',
        '-H', 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        '-H', 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        '-H', 'Accept-Language: en-US,en;q=0.5',
        url
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, timeout=20)
        html = result.stdout.decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"Curl error: {e}")
        return []

    matches = []
    today = datetime.now(timezone(timedelta(hours=8))).date()

    # 提取所有比赛数据块
    # 格式: ~AA÷ID¬content¬~AA÷ID2¬...
    all_blocks = re.findall(r'~AA÷([^¬]+)¬([^~]+?)(?=~AA÷|$)', html, re.DOTALL)

    for match_id, block_content in all_blocks:
        # 从块内容中提取所有字段
        fields = dict(re.findall(r'([A-Z]+)÷([^¬]+)¬', block_content))
        
        ts = fields.get('AD', '')
        home = fields.get('AE', '') or fields.get('CX', '')
        away = fields.get('AF', '')
        
        if ts and home and away:
            try:
                match_dt = datetime.fromtimestamp(int(ts), tz=timezone(timedelta(hours=8)))
                match_date = match_dt.date()
                days_diff = (match_date - today).days
                
                # 只获取最近7天的比赛
                if -1 <= days_diff <= 7:
                    matches.append({
                        'date': match_date.isoformat(),
                        'home': home.strip(),
                        'away': away.strip(),
                        'time': match_dt.strftime('%H:%M'),
                        'days_diff': days_diff,
                        'timestamp': int(ts)
                    })
            except (ValueError, TypeError):
                continue

    # 去重（基于主客队+日期组合）
    seen = set()
    unique = []
    for m in matches:
        key = (m['date'], m['home'], m['away'])
        if key not in seen:
            seen.add(key)
            unique.append(m)

    # 按日期排序
    unique.sort(key=lambda x: (x['days_diff'], x['time']))

    return unique

def fetch_all_leagues():
    """获取所有联赛的赛程"""
    leagues = {
        'EPL': 'england/premier-league',
        'La Liga': 'spain/laliga',
        'Serie A': 'italy/serie-a',
        'Bundesliga': 'germany/bundesliga',
        'Ligue 1': 'france/ligue-1',
    }

    all_matches = []
    for league_name, league_path in leagues.items():
        print(f"获取 {league_name} 赛程...")
        matches = fetch_flashscore_fixtures(league_path)
        for m in matches:
            m['league'] = league_name
        all_matches.extend(matches)
        print(f"  找到 {len(matches)} 场比赛")

    return all_matches

def save_to_cache(matches):
    """保存到缓存文件"""
    cache_file = '/Users/lifeng/hermes-world-cup/data/daily/fixtures_cache.json'
    import os
    os.makedirs(os.path.dirname(cache_file), exist_ok=True)

    with open(cache_file, 'w') as f:
        json.dump({
            'updated_at': datetime.now().isoformat(),
            'matches': matches
        }, f, indent=2, ensure_ascii=False)

    print(f"\n保存了 {len(matches)} 场比赛到缓存")

def load_from_cache():
    """从缓存加载"""
    cache_file = '/Users/lifeng/hermes-world-cup/data/daily/fixtures_cache.json'
    try:
        with open(cache_file) as f:
            data = json.load(f)
        # 检查缓存是否新鲜（1小时内）
        updated = datetime.fromisoformat(data['updated_at'])
        if (datetime.now() - updated).total_seconds() < 3600:
            return data['matches']
    except:
        pass
    return None

if __name__ == '__main__':
    print("=" * 50)
    print("从Flashscore获取真实赛程 v2")
    print("=" * 50)

    # 先尝试从缓存加载
    matches = load_from_cache()
    if matches:
        print(f"\n从缓存加载了 {len(matches)} 场比赛")
    else:
        # 获取真实数据
        matches = fetch_all_leagues()
        save_to_cache(matches)

    # 按日期排序
    matches.sort(key=lambda x: (x['days_diff'], x['time']))

    print("\n" + "=" * 50)
    print("近期比赛（按日期）:")
    print("=" * 50)
    for m in matches:
        date_label = "今天" if m['days_diff'] == 0 else "明天" if m['days_diff'] == 1 else m['date']
        print(f"{date_label} {m['time']} - {m['home']} vs {m['away']} ({m['league']})")