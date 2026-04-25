#!/usr/bin/env python3
"""
从browser快照中提取赛程数据
这个脚本读取browser_navigate的输出，解析出比赛数据
"""
import json
import re
import os
from datetime import datetime, timedelta

def parse_flashscore_snapshot(snapshot_text):
    """从browser_snapshot输出中解析比赛数据"""
    matches = []
    today = datetime.now().date()
    
    # 匹配格式: "18.04. 19:30" 后跟球队名
    # 模式: 日期 时间 球队1 球队2
    pattern = r'(\d{2}\.\d{2}\.)\s*(\d{2}:\d{2})\s*\n\s*([A-Za-z][A-Za-z\s\'\-]+?)\s*\n\s*([A-Za-z][A-Za-z\s\'\-]+?)(?:\s*-|$)'
    
    # 更宽松的匹配
    lines = snapshot_text.split('\n')
    current_date = None
    current_time = None
    
    for i, line in enumerate(lines):
        line = line.strip()
        
        # 匹配日期时间: "18.04. 19:30"
        date_time_match = re.match(r'(\d{2}\.\d{2}\.)\s*(\d{2}:\d{2})', line)
        if date_time_match:
            current_date = date_time_match.group(1)
            current_time = date_time_match.group(2)
            continue
        
        # 如果有当前日期时间，尝试匹配主队
        if current_date and current_time:
            # 匹配 "Brentford" 或 "Brentford " 后面跟其他内容
            if re.match(r'^[A-Za-z][A-Za-z\s\'\-]{2,20}$', line):
                home = line.strip()
                # 查找下一行是否是客队
                if i + 1 < len(lines):
                    away_line = lines[i + 1].strip()
                    # 客队后面可能有 " - -" 或比分
                    away_match = re.match(r'([A-Za-z][A-Za-z\s\'\-]+?)(?:\s*-|$)', away_line)
                    if away_match:
                        away = away_match.group(1).strip()
                        if home and away and home != away:
                            # 解析日期
                            day, month = map(int, current_date[:-1].split('.'))
                            year = today.year
                            if month < today.month or (month == today.month and day < today.day):
                                year += 1
                            match_date = datetime(year, month, day).date()
                            days_diff = (match_date - today).days
                            
                            matches.append({
                                'date': match_date.isoformat(),
                                'home': home,
                                'away': away,
                                'time': current_time,
                                'days_diff': days_diff
                            })
                            current_date = None
                            current_time = None
    
    # 去重
    seen = set()
    unique = []
    for m in matches:
        key = (m['home'], m['away'])
        if key not in seen:
            seen.add(key)
            unique.append(m)
    
    return unique

def save_fixtures(matches, league):
    """保存到缓存文件"""
    cache_file = '/Users/lifeng/hermes-world-cup/data/daily/fixtures_cache.json'
    os.makedirs(os.path.dirname(cache_file), exist_ok=True)
    
    # 读取现有缓存
    if os.path.exists(cache_file):
        with open(cache_file) as f:
            cache_data = json.load(f)
    else:
        cache_data = {'updated_at': datetime.now().isoformat(), 'matches': []}
    
    # 更新指定联赛的数据
    existing_matches = [m for m in cache_data['matches'] if m.get('league') != league]
    existing_matches.extend(matches)
    cache_data['matches'] = existing_matches
    cache_data['updated_at'] = datetime.now().isoformat()
    
    with open(cache_file, 'w') as f:
        json.dump(cache_data, f, indent=2)
    
    print(f"保存了 {len(matches)} 场 {league} 比赛到缓存")

if __name__ == '__main__':
    print("请使用browser工具获取Flashscore赛程页面，然后调用此脚本解析数据")
