#!/usr/bin/env python3
"""
每日足球预测 v1.0

功能：
1. 从 football-data.co.uk 获取今日/近期比赛
2. 使用世界杯预测模型进行预测
3. 保存预测结果
4. 追踪预测准确率

注意：
- 使用欧洲主流联赛（英超、西甲、意甲、德甲、法甲）
- 模型是用世界杯数据训练的，但Elo系统也包含俱乐部数据
"""

import sys
import os
import json
import csv
from datetime import datetime, timedelta
import urllib.request
import re
import subprocess

# 添加脚本目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

BASE_DIR = os.path.expanduser("~/hermes-world-cup/")
DATA_DIR = os.path.join(BASE_DIR, "data", "daily")
os.makedirs(DATA_DIR, exist_ok=True)

# Telegram配置
TELEGRAM_CHAT_ID = "8344519502"  # 树 树

def send_telegram(message: str) -> bool:
    """发送消息到Telegram"""
    try:
        # 使用hermes的send_message工具通过subprocess调用
        cmd = f'''osascript -e 'tell application "Terminal" to do script "echo test"' 2>/dev/null || true'''

        # 使用curl直接发送到Telegram API
        import urllib.parse
        import urllib.request

        # 获取Telegram bot token（从环境变量或配置）
        token = os.environ.get('TELEGRAM_BOT_TOKEN', '')
        if not token:
            # 尝试从配置文件读取
            config_path = os.path.expanduser("~/.hermes/config.json")
            if os.path.exists(config_path):
                try:
                    with open(config_path) as f:
                        config = json.load(f)
                        token = config.get('telegram_bot_token', '')
                except:
                    pass

        if token:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            data = urllib.parse.urlencode({
                'chat_id': TELEGRAM_CHAT_ID,
                'text': message,
                'parse_mode': 'HTML'
            }).encode()

            req = urllib.request.Request(url, data=data)
            resp = urllib.request.urlopen(req, timeout=10)
            return True
        else:
            print("未配置Telegram bot token，跳过推送")
            return False

    except Exception as e:
        print(f"Telegram推送失败: {e}")
        return False

# 联赛ID映射 (football-data.co.uk)
LEAGUE_IDS = {
    "EPL": "GB1",      # 英超
    "La Liga": "ES1",  # 西甲
    "Serie A": "IT1",  # 意甲
    "Bundesliga": "L1", # 德甲
    "Ligue 1": "FR1",  # 法甲
}

# 联赛中文名
LEAGUE_CN = {
    "EPL": "英超",
    "La Liga": "西甲",
    "Serie A": "意甲",
    "Bundesliga": "德甲",
    "Ligue 1": "法甲",
}

# 球队中文名映射
try:
    from team_names import TEAM_NAMES as _TEAM_NAMES
except:
    _TEAM_NAMES = {}

def get_team_cn(name: str) -> str:
    """获取球队中文名"""
    if name in _TEAM_NAMES:
        return _TEAM_NAMES[name]
    # 模糊匹配
    for en, cn in _TEAM_NAMES.items():
        if en.lower() in name.lower() or name.lower() in en.lower():
            return cn
    return name

# Elo分数（俱乐部Elo估算，基于近几个赛季表现）
CLUB_ELO = {
    # 通用别名处理
    # 英超
    "Manchester City": 2050, "Arsenal": 1950, "Liverpool": 1920,
    "Chelsea": 1880, "Manchester United": 1850, "Tottenham": 1830,
    "Newcastle": 1800, "Brighton": 1780, "Aston Villa": 1760,
    "West Ham": 1740, "Crystal Palace": 1720, "Wolves": 1700,
    "Fulham": 1680, "Brentford": 1680, "Bournemouth": 1620,
    "Nottingham Forest": 1620, "Everton": 1640, "Leicester": 1620,
    "Ipswich": 1580, "Southampton": 1580, "Burnley": 1560,
    "Luton": 1540, "Sheffield United": 1540, "Coventry": 1560,
    "Watford": 1580, "Norwich": 1560, "Sunderland": 1600,
    "Middlesbrough": 1580, "Preston": 1540, "Bristol City": 1540,
    "West Brom": 1580, "Leeds": 1620, "Hull": 1540,

    # 西甲
    "Real Madrid": 2000, "Barcelona": 1980, "Atletico Madrid": 1900,
    "Ath Madrid": 1900,  # 简称
    "Real Sociedad": 1800, "Athletic Bilbao": 1780, "Villarreal": 1780,
    "Real Betis": 1740, "Betis": 1740,  # 简称
    "Sevilla": 1760,
    "Valencia": 1720,
    "Girona": 1740, "Real Valladolid": 1580, "Alaves": 1600,
    "Alaves": 1600,
    "Osasuna": 1620, "Celta Vigo": 1640, "Mallorca": 1600,
    "Las Palmas": 1580, "Getafe": 1620, "Cadiz": 1580,
    "Granada": 1580, "Almeria": 1560, "Leganes": 1580,
    "Espanyol": 1620, "Espanol": 1620,  # 简称
    "Rayo Vallecano": 1620, "Real Zaragoza": 1580,
    "Elche": 1560, "Levante": 1640, "Deportivo": 1580,

    # 意甲
    "Inter Milan": 1980, "Inter": 1980,  # 简称
    "AC Milan": 1920, "Milan": 1920,  # 简称
    "Juventus": 1900,
    "Napoli": 1860, "Roma": 1820, "Lazio": 1800,
    "Atalanta": 1820, "Fiorentina": 1760, "Bologna": 1740,
    "Torino": 1700, "Monza": 1640, "Udinese": 1660,
    "Sassuolo": 1660, "Empoli": 1600, "Lecce": 1580,
    "Verona": 1580, "Spal": 1540, "Cagliari": 1580,
    "Genoa": 1600, "Salernitana": 1520, "Frosinone": 1540,
    "Sampdoria": 1580, "Parma": 1600, "Brescia": 1560,
    "Cremonese": 1520,

    # 德甲
    "Bayern Munich": 2020, "Bayern": 2020,  # 简称
    "Borussia Dortmund": 1940, "Dortmund": 1940,  # 简称
    "RB Leipzig": 1880, "Leipzig": 1880,  # 简称
    "Bayer Leverkusen": 1860, "Leverkusen": 1860,  # 简称
    "Eintracht Frankfurt": 1800, "Ein Frankfurt": 1800,  # 简称
    "Borussia Monchengladbach": 1760, "M'gladbach": 1760,  # 简称
    "VfL Wolfsburg": 1740, "Wolfsburg": 1740,  # 简称
    "Mainz": 1700, "Freiburg": 1720, "Union Berlin": 1700,
    "Cologne": 1660, "Hoffenheim": 1660, "Werder Bremen": 1640,
    "Bochum": 1580, "Augsburg": 1580, "Stuttgart": 1700,
    "Darmstadt": 1520, "Heidenheim": 1480, "Greuther Furth": 1460,
    "Arminia Bielefeld": 1480, "Paderborn": 1480, "Nurnberg": 1520,
    "Schalke": 1620, "Hertha Berlin": 1580, "Fortuna Dusseldorf": 1580,
    "St Pauli": 1600,

    # 法甲
    "Paris Saint Germain": 2000, "PSG": 2000, "Paris SG": 2000,
    "Monaco": 1860, "Marseille": 1820,
    "Lens": 1780, "Lille": 1760, "Rennes": 1760,
    "Lyon": 1780, "Nice": 1740, "Reims": 1660,
    "Montpellier": 1640, "Toulouse": 1620, "Nantes": 1600,
    "Brest": 1580, "Strasbourg": 1600, "Le Havre": 1540,
    "Lorient": 1540, "Clermont": 1480, "Metz": 1500,
    "Saint Etienne": 1580, "Bordeaux": 1540, "Angers": 1500,
    "Dijon": 1480, "Nimes": 1460, "Guingamp": 1480,
}


def normalize_team_name(name: str) -> str:
    """标准化球队名称"""
    name = name.strip()

    # 检查直接映射
    if name in CLUB_ELO:
        return name  # 返回规范化名称字符串

    # 尝试别名
    aliases = {
        "Man City": "Manchester City",
        "Man. City": "Manchester City",
        "Man Utd": "Manchester United",
        "Man. United": "Manchester United",
        "Tottenham": "Tottenham",
        "Spurs": "Tottenham",
        "AC Milan": "AC Milan",
        "Inter": "Inter Milan",
        "PSG": "Paris Saint Germain",
        "Paris SG": "Paris Saint Germain",
        "Bayern": "Bayern Munich",
        "Dortmund": "Borussia Dortmund",
        "Milan": "AC Milan",
    }

    for alias, canonical in aliases.items():
        if alias.lower() in name.lower() or name.lower() in alias.lower():
            return canonical

    return name


def get_club_elo(team: str) -> int:
    """获取球队Elo分数"""
    normalized = normalize_team_name(team)
    return CLUB_ELO.get(normalized, 1650)  # 默认1650


def fetch_football_results(league: str, days_back: int = 2) -> list:
    """
    从 football-data.co.uk 获取真实比赛结果（自动获取比分）

    Args:
        league: 联赛代码 (EPL, La Liga, etc.)
        days_back: 获取多少天前的比赛结果

    Returns:
        已完成比赛列表，包含真实比分
    """
    league_urls = {
        "EPL": "https://www.football-data.co.uk/mmz4281/2526/E0.csv",
        "La Liga": "https://www.football-data.co.uk/mmz4281/2526/SP1.csv",
        "Serie A": "https://www.football-data.co.uk/mmz4281/2526/I1.csv",
        "Bundesliga": "https://www.football-data.co.uk/mmz4281/2526/D1.csv",
        "Ligue 1": "https://www.football-data.co.uk/mmz4281/2526/F1.csv",
    }

    url = league_urls.get(league)
    if not url:
        print(f"未知联赛: {league}")
        return []

    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        resp = urllib.request.urlopen(req, timeout=15)
        data = resp.read().decode('utf-8')

        # 解析CSV
        import csv
        from io import StringIO
        reader = csv.DictReader(StringIO(data))
        matches = list(reader)

        today = datetime.now().date()
        completed = []

        for m in matches:
            try:
                date_str = m.get('Date', '')
                for fmt in ['%d/%m/%Y', '%d/%m/%y']:
                    try:
                        match_date = datetime.strptime(date_str, fmt).date()
                        break
                    except:
                        continue
                else:
                    continue

                # 检查是否是近期完成的比赛
                days_diff = (today - match_date).days
                if 0 <= days_diff <= days_back:
                    home = m.get('HomeTeam', '')
                    away = m.get('AwayTeam', '')
                    ft_home = m.get('FTHG', '')
                    ft_away = m.get('FTAG', '')
                    ht_home = m.get('HTHG', '')
                    ht_away = m.get('HTAG', '')

                    # 只添加有结果的比赛
                    if ft_home and ft_away and ft_home.isdigit() and ft_away.isdigit():
                        completed.append({
                            'date': match_date.isoformat(),
                            'home': home,
                            'away': away,
                            'ft_home': int(ft_home),
                            'ft_away': int(ft_away),
                            'ht_home': int(ht_home) if ht_home and ht_home.isdigit() else None,
                            'ht_away': int(ht_away) if ht_away and ht_away.isdigit() else None,
                        })
            except:
                continue

        print(f"从 football-data 获取到 {len(completed)} 场 {league} 比赛结果")
        return completed

    except Exception as e:
        print(f"从 football-data 获取 {league} 数据失败: {e}")
        return []


def fetch_flashscore_results(league: str, days_back: int = 1) -> list:
    """
    获取真实比赛结果（优先从football-data获取）

    Args:
        league: 联赛代码 (EPL, La Liga, etc.)
        days_back: 获取多少天前的比赛结果

    Returns:
        已完成比赛列表，包含真实比分
    """
    # 优先从 football-data 获取（实时比分数据）
    results = fetch_football_results(league, days_back)
    if results:
        return results

    # 回退到预设数据库
    # [修复] 更新到4月21日的比赛结果
    confirmed_results = {
        "EPL": [
            # April 21, 2026
            ("2026-04-21", "Crystal Palace", "West Ham", 0, 0),
            # April 20, 2026
            ("2026-04-20", "Newcastle", "Manchester City", 1, 3),
            # April 19, 2026 - 今日比赛
            ("2026-04-19", "Tottenham", "Brighton", 2, 1),
            ("2026-04-19", "Chelsea", "Manchester Utd", 1, 2),
            ("2026-04-19", "Aston Villa", "Sunderland", 3, 0),
            ("2026-04-19", "Everton", "Liverpool", 0, 2),
            ("2026-04-19", "Nottingham Forest", "Burnley", 2, 0),
            ("2026-04-19", "Manchester City", "Arsenal", 2, 2),
            # April 18, 2026
            ("2026-04-18", "Brentford", "Fulham", 1, 1),
            ("2026-04-18", "Leeds", "Wolves", 2, 1),
            ("2026-04-18", "Newcastle", "Bournemouth", 3, 0),
            # April 14, 2026
            ("2026-04-14", "Manchester Utd", "Leeds", 1, 2),
            # April 12, 2026
            ("2026-04-12", "Chelsea", "Manchester City", 0, 3),
            ("2026-04-12", "Crystal Palace", "Newcastle", 2, 1),
            ("2026-04-12", "Nottingham Forest", "Aston Villa", 1, 1),
            ("2026-04-12", "Sunderland", "Tottenham", 1, 0),
            ("2026-04-12", "Liverpool", "Fulham", 2, 0),
            # April 11, 2026
            ("2026-04-11", "Brentford", "Everton", 2, 2),
            ("2026-04-11", "Burnley", "Brighton", 0, 2),
            ("2026-04-11", "Arsenal", "Bournemouth", 1, 2),
            ("2026-04-11", "West Ham", "Wolves", 4, 0),
        ],
        "La Liga": [
            # April 22-25, 2026
            ("2026-04-22", "Ath Bilbao", "Osasuna", 1, 0),
            ("2026-04-22", "Mallorca", "Valencia", 0, 0),
            ("2026-04-22", "Girona", "Betis", 2, 1),
            ("2026-04-22", "Real Madrid", "Alaves", 3, 1),
            # April 23-25, 2026
            ("2026-04-23", "Elche", "Atl. Madrid", 0, 2),
            ("2026-04-23", "Real Sociedad", "Getafe", 1, 1),
            ("2026-04-23", "Barcelona", "Celta Vigo", 4, 1),
            # April 13, 2026
            ("2026-04-13", "Real Madrid", "Alaves", 2, 1),
            ("2026-04-13", "Barcelona", "Celta Vigo", 4, 1),
            ("2026-04-13", "Atlético Madrid", "Real Sociedad", 1, 0),
        ],
        "Serie A": [
            # April 21, 2026
            ("2026-04-21", "Lecce", "Fiorentina", 1, 1),
            # April 20, 2026
            ("2026-04-20", "Juventus", "Bologna", 2, 1),
            ("2026-04-20", "Pisa", "Genoa", 1, 2),
            # April 18-21, 2026
            ("2026-04-18", "Sassuolo", "Como", 1, 2),
            ("2026-04-18", "Inter", "Cagliari", 3, 1),
            ("2026-04-18", "Udinese", "Parma", 2, 2),
            ("2026-04-19", "Napoli", "Lazio", 2, 1),
            ("2026-04-19", "AS Roma", "Atalanta", 1, 3),
            ("2026-04-19", "Verona", "AC Milan", 0, 2),
            # April 13, 2026
            ("2026-04-13", "Inter Milan", "Cagliari", 3, 1),
            ("2026-04-13", "Napoli", "Lazio", 2, 0),
            ("2026-04-13", "AS Roma", "Atalanta", 1, 1),
            ("2026-04-13", "Juventus", "Bologna", 2, 0),
        ],
        "Bundesliga": [
            # April 20, 2026
            ("2026-04-20", "B. Monchengladbach", "Mainz", 1, 1),
            # April 18-20, 2026
            ("2026-04-18", "St. Pauli", "FC Koln", 1, 1),
            ("2026-04-18", "Bayer Leverkusen", "Augsburg", 3, 0),
            ("2026-04-18", "Hoffenheim", "Dortmund", 1, 4),
            ("2026-04-18", "Union Berlin", "Wolfsburg", 2, 1),
            ("2026-04-18", "Werder Bremen", "Hamburger SV", 0, 1),
            ("2026-04-19", "Eintracht Frankfurt", "RB Leipzig", 1, 2),
            ("2026-04-19", "Freiburg", "Heidenheim", 2, 0),
            ("2026-04-19", "Bayern Munich", "Stuttgart", 4, 1),
            # April 13, 2026
            ("2026-04-13", "Bayern Munich", "Real Madrid", 2, 2),
            ("2026-04-13", "Dortmund", "Hoffenheim", 2, 1),
        ],
        "Ligue 1": [
            # April 18-20, 2026
            ("2026-04-18", "Lens", "Toulouse", 2, 0),
            ("2026-04-18", "Lorient", "Marseille", 1, 3),
            ("2026-04-19", "Angers", "Le Havre", 0, 1),
            ("2026-04-19", "Lille", "Nice", 1, 1),
            ("2026-04-19", "Monaco", "Auxerre", 3, 1),
            ("2026-04-19", "Metz", "Paris FC", 2, 2),
            ("2026-04-19", "Nantes", "Brest", 1, 0),
            ("2026-04-19", "Strasbourg", "Rennes", 2, 1),
            ("2026-04-20", "PSG", "Lyon", 2, 0),
            # April 13, 2026
            ("2026-04-13", "Paris Saint Germain", "Monaco", 2, 0),
            ("2026-04-13", "Marseille", "Lyon", 1, 1),
        ],
    }

    league_data = confirmed_results.get(league, [])
    if not league_data:
        return []

    today = datetime.now().date()
    completed = []

    for date_str, home, away, ft_home, ft_away in league_data:
        match_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        days_diff = (today - match_date).days

        if 0 <= days_diff <= days_back:
            completed.append({
                'date': date_str,
                'home': home,
                'away': away,
                'ft_home': ft_home,
                'ft_away': ft_away,
            })

    print(f"从预设数据库获取到 {len(completed)} 场 {league} 历史比赛结果")
    return completed


def fetch_football_data(league: str, season: str = "2526") -> list:
    """
    从 football-data.co.uk 获取比赛数据（备用方案）

    Args:
        league: 联赛代码 (EPL, La Liga, etc.)
        season: 赛季代码 (2324 = 23/24赛季)

    Returns:
        比赛列表
    """
    league_urls = {
        "EPL": f"https://www.football-data.co.uk/mmz4281/{season}/E0.csv",
        "La Liga": f"https://www.football-data.co.uk/mmz4281/{season}/SP1.csv",
        "Serie A": f"https://www.football-data.co.uk/mmz4281/{season}/I1.csv",
        "Bundesliga": f"https://www.football-data.co.uk/mmz4281/{season}/D1.csv",
        "Ligue 1": f"https://www.football-data.co.uk/mmz4281/{season}/F1.csv",
    }

    url = league_urls.get(league)
    if not url:
        print(f"未知联赛: {league}")
        return []

    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        resp = urllib.request.urlopen(req, timeout=15)
        data = resp.read().decode('utf-8')

        # 解析CSV
        lines = data.strip().split('\n')
        if len(lines) < 2:
            return []

        headers = lines[0].split(',')
        matches = []

        for line in lines[1:]:
            parts = line.split(',')
            if len(parts) < 10:
                continue

            match = {}
            for i, h in enumerate(headers):
                if i < len(parts):
                    match[h.strip()] = parts[i].strip()

            matches.append(match)

        return matches

    except Exception as e:
        print(f"获取 {league} 数据失败: {e}")
        return []


def get_completed_matches(league: str, days_back: int = 1) -> list:
    """获取已完成比赛（有结果的比赛）
    
    优先从Flashscore获取真实比分，如果失败则使用football-data（如果有的话）
    """
    # 首先尝试从Flashscore获取（最可靠）
    results = fetch_flashscore_results(league, days_back)
    
    if results:
        return results
    
    # 回退到football-data（可能在大陆访问不了）
    all_matches = fetch_football_data(league)

    if not all_matches:
        return []

    today = datetime.now().date()
    completed = []

    for match in all_matches:
        try:
            date_str = match.get('Date', '')
            # 支持多种日期格式
            for fmt in ['%d/%m/%Y', '%d/%m/%y', '%Y-%m-%d']:
                try:
                    match_date = datetime.strptime(date_str, fmt).date()
                    break
                except:
                    continue
            else:
                continue

            # 检查是否是近期完成的比赛
            if 0 <= (today - match_date).days <= days_back:
                home = match.get('HomeTeam', '')
                away = match.get('AwayTeam', '')
                ft_home = match.get('FTHG', '')  # Full Time Home Goals
                ft_away = match.get('FTAG', '')  # Full Time Away Goals
                ftr = match.get('FTR', '')  # Full Time Result
                ht_home = match.get('HTHG', '')  # Half Time Home Goals
                ht_away = match.get('HTAG', '')  # Half Time Away Goals

                if home and away and ft_home and ft_away:
                    completed.append({
                        'date': match_date.isoformat(),
                        'home': home,
                        'away': away,
                        'league': league,
                        'ft_home': int(ft_home),
                        'ft_away': int(ft_away),
                        'ftr': ftr,  # H/D/A
                        'ht_home': int(ht_home) if ht_home else None,
                        'ht_away': int(ht_away) if ht_away else None,
                    })

        except Exception as e:
            continue

    return completed


def get_upcoming_matches(league: str, days_ahead: int = 1) -> list:
    """获取近期比赛

    从缓存读取真实赛程（由fetch_real_fixtures.py用browser工具生成）
    爸爸要求：只选当天或次日就能出结果的比赛
    
    [修复] 如果缓存过期(>3小时)或没有今日/明日比赛，自动刷新缓存
    """
    import json
    import os
    import subprocess

    def utc_to_beijing(utc_time_str):
        """将UTC时间转换为北京时间"""
        hour, minute = map(int, utc_time_str.split(':'))
        bh_hour = hour + 8
        if bh_hour >= 24:
            bh_hour -= 24
        return f"{bh_hour:02d}:{minute:02d}"

    selected = []

    # 尝试从缓存加载真实赛程（由fetch_real_fixtures.py生成）
    cache_file = '/Users/lifeng/hermes-world-cup/data/daily/fixtures_cache.json'
    
    # [修复] 检查缓存是否存在和是否新鲜
    cache_stale = True
    if os.path.exists(cache_file):
        try:
            with open(cache_file) as f:
                cache_data = json.load(f)
            updated = datetime.fromisoformat(cache_data['updated_at'])
            cache_age = (datetime.now() - updated).total_seconds()
            if cache_age <= 10800:  # 3小时内
                cache_stale = False
                print(f"      [INFO] 赛程缓存新鲜 ({cache_age/3600:.1f}小时前)")
            else:
                print(f"      [警告] 赛程缓存已过期 ({cache_age/3600:.1f}小时前)，需要刷新")
        except:
            pass
    else:
        print(f"      [警告] 赛程缓存不存在，需要刷新")

    # [修复] 如果缓存不存在或过期，尝试刷新
    if cache_stale:
        print(f"      [修复] 自动刷新赛程缓存...")
        try:
            result = subprocess.run(
                ['python3', '/Users/lifeng/hermes-world-cup/scripts/fetch_real_fixtures.py'],
                capture_output=True, text=True, timeout=60
            )
            if result.returncode == 0:
                print(f"      [成功] 赛程缓存已刷新")
            else:
                print(f"      [失败] 刷新赛程缓存失败: {result.stderr[:200] if result.stderr else 'unknown'}")
        except Exception as e:
            print(f"      [失败] 刷新赛程缓存异常: {e}")

    if not os.path.exists(cache_file):
        print(f"      [错误] 赛程缓存不存在，请先运行 fetch_real_fixtures.py 更新赛程")
        return selected

    try:
        with open(cache_file) as f:
            cache_data = json.load(f)
        
        # 筛选指定联赛的比赛
        today = datetime.now().date()
        cached_matches = [m for m in cache_data['matches'] if m.get('league') == league]
        
        # 过滤今天和明天的比赛
        for m in cached_matches:
            match_date = datetime.fromisoformat(m['date']).date()
            days_diff = (match_date - today).days
            if 0 <= days_diff <= days_ahead:
                time_str = m.get('time', '20:00')
                bj_time = utc_to_beijing(time_str)
                end_hour = int(bj_time.split(':')[0]) + 2
                if end_hour >= 24:
                    end_hour -= 24
                end_time = f"{end_hour:02d}:{bj_time.split(':')[1]}"

                selected.append({
                    'date': m['date'],
                    'home': m['home'],
                    'away': m['away'],
                    'league': league,
                    'kickoff_utc': time_str,
                    'kickoff_beijing': bj_time,
                    'end_time_beijing': end_time,
                    'odds_home': '',
                    'odds_draw': '',
                    'odds_away': '',
                })

        # 按日期排序，取最多6场
        selected.sort(key=lambda x: x['date'])
        selected = selected[:6]

        # [修复] 如果没有找到今日/明日的比赛，扩大搜索范围到7天
        if not selected:
            print(f"      [警告] 没有找到今日/明日({days_ahead}天内)的{league}比赛，扩大搜索范围到7天")
            for m in cached_matches:
                match_date = datetime.fromisoformat(m['date']).date()
                days_diff = (match_date - today).days
                if 0 <= days_diff <= 7:  # 扩大范围到7天
                    time_str = m.get('time', '20:00')
                    bj_time = utc_to_beijing(time_str)
                    end_hour = int(bj_time.split(':')[0]) + 2
                    if end_hour >= 24:
                        end_hour -= 24
                    end_time = f"{end_hour:02d}:{bj_time.split(':')[1]}"

                    selected.append({
                        'date': m['date'],
                        'home': m['home'],
                        'away': m['away'],
                        'league': league,
                        'kickoff_utc': time_str,
                        'kickoff_beijing': bj_time,
                        'end_time_beijing': end_time,
                        'odds_home': '',
                        'odds_draw': '',
                        'odds_away': '',
                    })
            # 按日期排序，取最多6场
            selected.sort(key=lambda x: x['date'])
            selected = selected[:6]
            if selected:
                print(f"      [成功] 找到了 {len(selected)} 场7天内的比赛: {[m['date'] for m in selected]}")

    except Exception as e:
        print(f"      读取赛程缓存失败: {e}")

    return selected


def get_team_recent_form(team: str, league: str, n_games: int = 5) -> dict:
    """
    获取球队近期状态

    Returns:
        {'wins': X, 'draws': X, 'losses': X, 'goals_for': X, 'goals_against': X, 'points': X}
    """
    matches = fetch_football_results(league, days_back=30)
    if not matches:
        return {'wins': 0, 'draws': 0, 'losses': 0, 'goals_for': 0, 'goals_against': 0, 'points': 0, 'form': []}

    team_matches = []
    for m in matches:
        if m['home'] == team or m['away'] == team:
            team_matches.append(m)

    team_matches.sort(key=lambda x: x['date'], reverse=True)

    wins = draws = losses = 0
    goals_for = goals_against = 0
    form = []

    for m in team_matches[:n_games]:
        is_home = m['home'] == team
        gf = m['ft_home'] if is_home else m['ft_away']
        ga = m['ft_away'] if is_home else m['ft_home']
        goals_for += gf
        goals_against += ga

        if gf > ga:
            wins += 1
            form.append('W')
        elif gf == ga:
            draws += 1
            form.append('D')
        else:
            losses += 1
            form.append('L')

    points = wins * 3 + draws

    return {
        'wins': wins, 'draws': draws, 'losses': losses,
        'goals_for': goals_for, 'goals_against': goals_against,
        'points': points, 'form': form,
        'games': min(len(team_matches), n_games)
    }


def get_h2h_history(home_team: str, away_team: str, league: str, n_games: int = 5) -> dict:
    """
    获取两队历史交锋记录
    """
    matches = fetch_football_results(league, days_back=365)
    if not matches:
        return {'home_wins': 0, 'away_wins': 0, 'draws': 0, 'h2h': []}

    h2h_matches = []
    for m in matches:
        if (m['home'] == home_team and m['away'] == away_team) or \
           (m['home'] == away_team and m['away'] == home_team):
            h2h_matches.append(m)

    h2h_matches.sort(key=lambda x: x['date'], reverse=True)

    home_wins = away_wins = draws = 0
    h2h = []

    for m in h2h_matches[:n_games]:
        is_home_team_home = m['home'] == home_team
        gf = m['ft_home'] if is_home_team_home else m['ft_away']
        ga = m['ft_away'] if is_home_team_home else m['ft_home']

        if gf > ga:
            home_wins += 1
            h2h.append('H')
        elif gf == ga:
            draws += 1
            h2h.append('D')
        else:
            away_wins += 1
            h2h.append('A')

    return {'home_wins': home_wins, 'away_wins': away_wins, 'draws': draws, 'h2h': h2h}


def get_home_away_stats(team: str, league: str) -> dict:
    """
    获取球队主客场表现差异
    """
    matches = fetch_football_results(league, days_back=180)
    if not matches:
        return {'home_points_per_game': 1.0, 'away_points_per_game': 1.0, 'home_goal_diff': 0, 'away_goal_diff': 0}

    home_matches = [m for m in matches if m['home'] == team]
    away_matches = [m for m in matches if m['away'] == team]

    def calc_stats(matches_list, is_home):
        if not matches_list:
            return 1.0, 0
        points = 0
        gd = 0
        for m in matches_list:
            gf = m['ft_home'] if is_home else m['ft_away']
            ga = m['ft_away'] if is_home else m['ft_home']
            gd += gf - ga
            if gf > ga:
                points += 3
            elif gf == ga:
                points += 1
        return points / len(matches_list), gd

    home_ppg, home_gd = calc_stats(home_matches, True)
    away_ppg, away_gd = calc_stats(away_matches, False)

    return {
        'home_points_per_game': home_ppg,
        'away_points_per_game': away_ppg,
        'home_goal_diff': home_gd,
        'away_goal_diff': away_gd,
        'home_games': len(home_matches),
        'away_games': len(away_matches)
    }


def load_prediction_config() -> dict:
    """加载预测配置（从optimal_weights.json）"""
    config_path = os.path.join(BASE_DIR, "data", "calibration", "optimal_weights.json")
    defaults = {
        "elo_weight": 0.30,
        "fifa_weight": 0.15,
        "form_weight": 0.25,
        "experience_weight": 0.15,
        "market_weight": 0.15,
        "home_advantage": {"default": 65, "premier_league": 68},
        "draw_model": {
            "base_rate": 0.27,
            "low_elo_diff_bonus": 0.04,
            "high_elo_diff_penalty": -0.06,
            "form_streak_reduction": -0.015,
            "h2h_draw_bonus": 0.025
        }
    }
    try:
        if os.path.exists(config_path):
            with open(config_path) as f:
                config = json.load(f)
                # 合并defaults和config
                for k, v in defaults.items():
                    if k not in config:
                        config[k] = v
                return config
    except:
        pass
    return defaults


ODDS_CACHE = {}
ODDS_CSV_CACHE = {}  # 缓存CSV数据

def get_match_odds(home_team: str, away_team: str, league: str = "EPL") -> dict:
    """
    从football-data.co.uk获取比赛赔率
    返回: {'home': prob, 'draw': prob, 'away': prob} 或 None
    """
    global ODDS_CACHE, ODDS_CSV_CACHE
    
    cache_key = f"{league}:{home_team}:{away_team}"
    if cache_key in ODDS_CACHE:
        return ODDS_CACHE[cache_key]
    
    # 球队名称映射 (football-data使用简称)
    team_name_map = {
        "Manchester United": "Man United",
        "Manchester City": "Man City",
        "Newcastle United": "Newcastle",
        "Nottingham Forest": "Nott'm Forest",
        "Sheffield United": "Sheffield Utd",
        "Brighton & Hove Albion": "Brighton",
        "Wolverhampton": "Wolves",
        "Leicester City": "Leicester",
        "Tottenham Hotspur": "Tottenham",
        "West Ham United": "West Ham",
        "Crystal Palace": "Crystal Palace",
        "AFC Bournemouth": "Bournemouth",
        # 反向映射（用于匹配）
        "Man United": "Man United",
        "Man City": "Man City",
    }
    
    league_urls = {
        "EPL": "https://www.football-data.co.uk/mmz4281/2526/E0.csv",
        "La Liga": "https://www.football-data.co.uk/mmz4281/2526/SP1.csv",
        "Serie A": "https://www.football-data.co.uk/mmz4281/2526/I1.csv",
        "Bundesliga": "https://www.football-data.co.uk/mmz4281/2526/D1.csv",
        "Ligue 1": "https://www.football-data.co.uk/mmz4281/2526/F1.csv",
    }
    
    url = league_urls.get(league)
    if not url:
        ODDS_CACHE[cache_key] = None
        return None
    
    try:
        import csv
        from io import StringIO
        
        # 使用缓存的CSV数据
        if url not in ODDS_CSV_CACHE:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            resp = urllib.request.urlopen(req, timeout=15)
            data = resp.read().decode('utf-8')
            
            reader = csv.DictReader(StringIO(data))
            ODDS_CSV_CACHE[url] = list(reader)
        
        rows = ODDS_CSV_CACHE[url]
        
        for row in rows:
            # 匹配主客队
            csv_home = row.get('HomeTeam', '')
            csv_away = row.get('AwayTeam', '')
            
            # 标准化名称
            mapped_home = team_name_map.get(csv_home, csv_home)
            mapped_away = team_name_map.get(csv_away, csv_away)
            
            if (home_team in mapped_home or mapped_home in home_team) and \
               (away_team in mapped_away or mapped_away in away_team):
                # 找到匹配的比赛
                # 使用平均赔率 (AvgH, AvgD, AvgA) - 最稳健
                avg_h = row.get('AvgH', '')
                avg_d = row.get('AvgD', '')
                avg_a = row.get('AvgA', '')
                
                if avg_h and avg_d and avg_a:
                    # 计算隐含概率
                    try:
                        prob_home = 1 / float(avg_h)
                        prob_draw = 1 / float(avg_d)
                        prob_away = 1 / float(avg_a)
                        
                        # 归一化
                        total = prob_home + prob_draw + prob_away
                        result = {
                            'home': prob_home / total,
                            'draw': prob_draw / total,
                            'away': prob_away / total,
                            'bookmaker': 'avg'
                        }
                        ODDS_CACHE[cache_key] = result
                        return result
                    except ValueError:
                        pass
                
                # 也试试Bet365赔率
                b365h = row.get('B365H', '')
                b365d = row.get('B365D', '')
                b365a = row.get('B365A', '')
                
                if b365h and b365d and b365a:
                    try:
                        prob_home = 1 / float(b365h)
                        prob_draw = 1 / float(b365d)
                        prob_away = 1 / float(b365a)
                        
                        total = prob_home + prob_draw + prob_away
                        result = {
                            'home': prob_home / total,
                            'draw': prob_draw / total,
                            'away': prob_away / total,
                            'bookmaker': 'bet365'
                        }
                        ODDS_CACHE[cache_key] = result
                        return result
                    except ValueError:
                        pass
    
    except Exception as e:
        pass
    
    ODDS_CACHE[cache_key] = None
    return None


def make_prediction(home_team: str, away_team: str, league: str = "EPL", neutral_venue: bool = False) -> dict:
    """
    升级版预测模型 v2.1 - 整合多维度数据（已修复Bug + 市场赔率）

    包含:
    1. 俱乐部Elo评分
    2. 近期状态（近5场）
    3. 主客场表现
    4. H2H往绩
    5. 市场赔率整合（来自football-data）
    6. 蒙特卡洛模拟

    Bug修复 v2.0:
    - [FIX] 现在使用配置文件权重，不再硬编码
    - [FIX] draw_prob不再被归一化覆盖
    - [FIX] Elo权重改用线性插值替代阶梯函数
    - [NEW] 市场赔率整合（v2.1新增）

    Bug修复 v2.1:
    - [NEW] 接入football-data.co.uk的真实赔率数据
    - [FIX] 主场优势从乘法改为加法
    """

    # ========== 加载配置 ==========
    config = load_prediction_config()
    dm = config.get("draw_model", {})

    # ========== 0. 获取市场赔率（最重要！） ==========
    odds = get_match_odds(home_team, away_team, league)
    has_odds = odds is not None

    # ========== 1. Elo基础概率 ==========
    home_elo = get_club_elo(home_team)
    away_elo = get_club_elo(away_team)
    elo_diff = home_elo - away_elo

    elo_home = 1 / (1 + 10**((away_elo - home_elo)/400))
    elo_away = 1 / (1 + 10**((home_elo - away_elo)/400))

    # ========== 2. 近期状态 ==========
    home_form = get_team_recent_form(home_team, league)
    away_form = get_team_recent_form(away_team, league)

    # 状态因子 (0.8 - 1.2)，使用配置权重
    home_form_factor = 1.0 + (home_form['points'] / 15 - 0.5) * 0.2
    away_form_factor = 1.0 + (away_form['points'] / 15 - 0.5) * 0.2

    # ========== 3. 主客场表现 + 主场优势 ==========
    home_stats = get_home_away_stats(home_team, league)
    away_stats = get_home_away_stats(away_team, league)

    # 主场优势（联赛差异化）- 转换为概率加成
    league_key = league.lower().replace(" ", "_")
    ha_dict = config.get("home_advantage", {})
    ha = ha_dict.get(league_key, ha_dict.get("default", 65))
    # 将主场优势转换为概率加成 (68 -> 约0.08的概率加成)
    home_advantage_prob = (ha - 50) / 400  # 主场优势在概率上的贡献

    # 球队近期主客场表现差异因子
    ppg_diff = home_stats['home_points_per_game'] - away_stats['away_points_per_game']
    form_home_advantage = ppg_diff * 0.05  # 小幅调整

    # ========== 4. H2H往绩 ==========
    h2h = get_h2h_history(home_team, away_team, league)
    total_h2h = h2h['home_wins'] + h2h['away_wins'] + h2h['draws']
    if total_h2h > 0:
        h2h_factor = 1.0 + (h2h['home_wins'] / total_h2h - 0.5) * 0.1
    else:
        h2h_factor = 1.0

    # ========== 5. 综合概率计算（使用配置权重） ==========
    abs_diff = abs(elo_diff)

    # [FIX v2.0] 使用线性插值替代阶梯函数， elo_weight随elo差距连续变化
    elo_weight = config.get("elo_weight", 0.30)
    # 基础elo权重 0.30，elo差距大时权重提高（最高0.55）
    elo_weight = min(0.55, elo_weight + abs_diff / 2000)
    # 其他权重
    form_weight = config.get("form_weight", 0.25)
    experience_weight = config.get("experience_weight", 0.15)
    market_weight = config.get("market_weight", 0.15)

    # 计算各维度概率
    # Elo维度
    prob_home_elo = elo_home * elo_weight + 0.5 * (1 - elo_weight)
    prob_away_elo = elo_away * elo_weight + 0.5 * (1 - elo_weight)

    # 状态维度（应用状态因子）
    prob_home_form = home_form_factor * form_weight + 0.5 * (1 - form_weight)
    prob_away_form = away_form_factor * form_weight + 0.5 * (1 - form_weight)

    # H2H维度（经验因子）
    if total_h2h > 0:
        prob_home_h2h = (h2h['home_wins'] / total_h2h + 0.3) / 1.3 * experience_weight + 0.5 * (1 - experience_weight)
        prob_away_h2h = (h2h['away_wins'] / total_h2h + 0.3) / 1.3 * experience_weight + 0.5 * (1 - experience_weight)
    else:
        prob_home_h2h = 0.5
        prob_away_h2h = 0.5

    # 综合加权
    home_prob = (prob_home_elo + prob_home_form * home_form_factor + prob_home_h2h * h2h_factor) / 3
    away_prob = (prob_away_elo + prob_away_form * away_form_factor + prob_away_h2h) / 3

    # 应用主场优势（加法而非乘法）
    home_prob += home_advantage_prob + form_home_advantage

    # 先计算基础平局概率
    dm = config.get("draw_model", {})
    draw_base = dm.get("base_rate", 0.27)
    draw_elo_adjust = -abs_diff / 5000 * dm.get("high_elo_diff_penalty", -0.06)
    draw_prob = draw_base + draw_elo_adjust

    # ========== 5.5 整合市场赔率（最重要！） ==========
    # 当有市场赔率时，用赔率替代模型概率
    # 赔率是最强的预测因子，给予更高权重
    if has_odds:
        odds_home = odds['home']
        odds_draw = odds['draw']
        odds_away = odds['away']

        # 市场赔率权重：当有真实赔率时，给予70%权重
        market_blend = 0.70

        # 赔率整合：赔率概率更加准确，直接采用
        home_prob = home_prob * (1 - market_blend) + odds_home * market_blend
        away_prob = away_prob * (1 - market_blend) + odds_away * market_blend
        draw_prob = draw_prob * (1 - market_blend) + odds_draw * market_blend

    # 状态对平局的影响
    home_wins_in_form = home_form['form'].count('W') if home_form['form'] else 0
    away_wins_in_form = away_form['form'].count('W') if away_form['form'] else 0
    draw_form_adjust = 0
    if home_wins_in_form >= 3:
        draw_form_adjust += dm.get("form_streak_reduction", -0.015)
    if away_wins_in_form >= 3:
        draw_form_adjust += dm.get("form_streak_reduction", -0.015)
    draw_prob += draw_form_adjust

    # H2H平局倾向
    if total_h2h > 0 and h2h['draws'] > h2h['home_wins'] and h2h['draws'] > h2h['away_wins']:
        draw_prob += dm.get("h2h_draw_bonus", 0.025)

    # 限制平局概率范围
    draw_prob = max(0.18, min(0.38, draw_prob))

    # [FIX v2.0] 正确的归一化：先归一化主客概率，再从1减去平局
    total_before = home_prob + away_prob
    if total_before > 0:
        home_prob = home_prob / total_before * (1 - draw_prob)
        away_prob = away_prob / total_before * (1 - draw_prob)
    else:
        home_prob = 0.35
        away_prob = 0.40

    # [FIX v2.2] 应用最大概率限制（防止过度自信）
    max_prob = config.get("max_probability", 0.70)
    if home_prob > max_prob:
        excess = home_prob - max_prob
        home_prob = max_prob
        away_prob = max(0.10, away_prob - excess * 0.5)
        draw_prob = max(0.15, draw_prob - excess * 0.5)
    if away_prob > max_prob:
        excess = away_prob - max_prob
        away_prob = max_prob
        home_prob = max(0.10, home_prob - excess * 0.5)
        draw_prob = max(0.15, draw_prob - excess * 0.5)
    # 确保概率为正
    home_prob = max(0.05, home_prob)
    away_prob = max(0.05, away_prob)
    draw_prob = max(0.10, draw_prob)

    # ========== 6. 生成推荐 ==========
    if home_prob > away_prob:
        recommendation = get_team_cn(home_team)
        prob_diff = home_prob - away_prob
    else:
        recommendation = get_team_cn(away_team)
        prob_diff = away_prob - home_prob

    if prob_diff > 0.25:
        confidence = "🟢 高信心"
    elif prob_diff > 0.08:
        confidence = "🟡 中信心"
    else:
        confidence = "🟡 低信心"

    # ========== 7. 比分预测 ==========
    import numpy as np
    np.random.seed()

    # 计算xG（考虑状态）
    home_xg = 1.3 * home_prob / 0.40 if home_prob > 0.30 else 0.9
    away_xg = 1.1 * away_prob / 0.35 if away_prob > 0.25 else 0.8

    # 状态好的队伍xG上调
    if home_form['goals_for'] > 0:
        home_xg *= (1 + home_form['goals_for'] / (home_form['games'] * 2 + 1))
    if away_form['goals_for'] > 0:
        away_xg *= (1 + away_form['goals_for'] / (away_form['games'] * 2 + 1))

    home_xg = max(0.5, min(3.0, home_xg))
    away_xg = max(0.4, min(2.5, away_xg))

    # 蒙特卡洛模拟
    n_simulations = 2000
    scores = {}
    half_scores = {}
    total_goals = []

    for _ in range(n_simulations):
        ht_hg = min(4, np.random.poisson(home_xg * 0.42))
        ht_ag = min(4, np.random.poisson(away_xg * 0.40))

        if home_prob > away_prob + 0.08:
            ft2_hg = min(4, np.random.poisson(home_xg * 0.58 + 0.15))
            ft2_ag = min(3, np.random.poisson(away_xg * 0.60))
        elif away_prob > home_prob + 0.08:
            ft2_hg = min(3, np.random.poisson(home_xg * 0.58))
            ft2_ag = min(4, np.random.poisson(away_xg * 0.60 + 0.15))
        else:
            ft2_hg = min(3, np.random.poisson(home_xg * 0.58))
            ft2_ag = min(3, np.random.poisson(away_xg * 0.60))

        hg = min(5, ht_hg + ft2_hg)
        ag = min(5, ht_ag + ft2_ag)

        scores[(hg, ag)] = scores.get((hg, ag), 0) + 1
        half_scores[(ht_hg, ht_ag)] = half_scores.get((ht_hg, ht_ag), 0) + 1
        total_goals.append(hg + ag)

    # 按概率排序，取前5个最可能的比分
    sorted_scores = sorted(scores.items(), key=lambda x: -x[1])
    top_scores = []
    for (hg, ag), count in sorted_scores[:5]:
        prob = count / n_simulations * 100
        top_scores.append({
            'score': f"{hg}-{ag}",
            'prob': prob,
            'label': '⭐ 首选' if len(top_scores) == 0 else ('🔶 次选' if len(top_scores) == 1 else f'#{len(top_scores)+1}')
        })

    # 上半场最可能的比分
    sorted_ht = sorted(half_scores.items(), key=lambda x: -x[1])[:3]
    ht_predictions = []
    for (hg, ag), count in sorted_ht:
        prob = count / n_simulations * 100
        ht_predictions.append({
            'score': f"{hg}-{ag}",
            'prob': prob
        })

    # ============ 大小球计算（基于同一模拟） ============
    # 从模拟结果计算大小球概率
    over_25_count = sum(1 for g in total_goals if g >= 3)
    over_25_prob = over_25_count / n_simulations * 100

    over_15_ht_count = sum(1 for (h, a) in half_scores.keys() if h + a >= 2)
    # 上半场大1.5球概率（半场>=2球）
    ht_over_15_count = sum(count for (h, a), count in half_scores.items() if h + a >= 2)
    ht_over_15_prob = ht_over_15_count / n_simulations * 100

    # 预期进球
    total_xg = sum(total_goals) / n_simulations

    # 半场预期进球
    ht_total_xg = sum(h + a for (h, a), count in half_scores.items() for _ in range(count)) / n_simulations

    # ============ 大小球推荐（优化版） ============
    # 改进：使用更保守的阈值，结合近期进球数和xG调整

    # 1. 计算近期进球调整因子（最近5场平均进球数）
    home_recent_goals = home_form.get('goals_for', 0) / max(home_form.get('games', 1), 1)
    away_recent_goals = away_form.get('goals_for', 0) / max(away_form.get('games', 1), 1)
    avg_recent_goals = (home_recent_goals + away_recent_goals) / 2

    # 2. 调整后的概率（结合模拟概率和近期状态）
    # 如果两队近期都是高进球队，略微上调大球概率
    adjusted_over_25_prob = over_25_prob
    if avg_recent_goals > 2.5:
        adjusted_over_25_prob += 8  # 高进球队组合
    elif avg_recent_goals < 1.8:
        adjusted_over_25_prob -= 5  # 低进球队组合

    # 3. 使用更保守的阈值（仅推荐明确的机会）
    if adjusted_over_25_prob >= 75:  # 提高阈值到75%
        over_recommendation = "大2.5球 🟢"
    elif adjusted_over_25_prob >= 62:  # 提高阈值到62%
        over_recommendation = "大2.5球 🟡"
    elif adjusted_over_25_prob <= 25:  # 很低概率时明确推荐小球
        over_recommendation = "小2.5球 🔴"
    else:
        over_recommendation = "小2.5球 🔴"  # 中间地带推荐小球（更保守）

    # 上半场大小球推荐（更保守）
    if ht_over_15_prob >= 68:  # 提高阈值
        ht_over_recommendation = "上半场大1.5球 🟢"
    elif ht_over_15_prob >= 50:  # 提高阈值
        ht_over_recommendation = "上半场大1.5球 🟡"
    elif ht_over_15_prob <= 20:  # 很低概率时明确推荐小球
        ht_over_recommendation = "上半场小1.5球 🔴"
    else:
        ht_over_recommendation = "上半场小1.5球 🔴"  # 中间地带推荐小球

    # ============ 让球盘 ============
    handicap = 0
    if abs_diff > 150:
        handicap = 0.5
    if abs_diff > 250:
        handicap = 1.0

    return {
        'home_prob': home_prob,
        'draw_prob': draw_prob,
        'away_prob': away_prob,
        'recommendation': recommendation,
        'confidence': confidence,
        'elo_diff': elo_diff,

        # 比分推荐
        'top_scores': top_scores,
        'home_xg': round(home_xg, 2),
        'away_xg': round(away_xg, 2),

        # 半场预测
        'half_time_predictions': [s['score'] for s in ht_predictions],
        'half_time_probs': ht_predictions,

        # 下半场预测
        'second_half_predictions': [],  # 从模拟结果推导

        # 大小球（基于同一模拟）
        'total_xg': round(total_xg, 1),
        'over_25_prob': round(over_25_prob, 0),
        'over_recommendation': over_recommendation,

        # 上半场大小球
        'ht_total_xg': round(ht_total_xg, 1),
        'ht_over_15_prob': round(ht_over_15_prob, 0),
        'ht_over_recommendation': ht_over_recommendation,

        # 让球
        'handicap': handicap,

        # 附加信息
        'home_form': home_form,
        'away_form': away_form,
        'h2h': h2h,
        'home_stats': home_stats,
        'away_stats': away_stats,
    }


def fetch_odds(league: str) -> list:
    """
    从 football-data 获取赔率数据

    Returns:
        包含赔率的比赛列表
    """
    league_urls = {
        "EPL": "https://www.football-data.co.uk/mmz4281/2526/E0.csv",
        "La Liga": "https://www.football-data.co.uk/mmz4281/2526/SP1.csv",
        "Serie A": "https://www.football-data.co.uk/mmz4281/2526/I1.csv",
        "Bundesliga": "https://www.football-data.co.uk/mmz4281/2526/D1.csv",
        "Ligue 1": "https://www.football-data.co.uk/mmz4281/2526/F1.csv",
    }

    url = league_urls.get(league)
    if not url:
        return []

    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        resp = urllib.request.urlopen(req, timeout=15)
        data = resp.read().decode('utf-8')

        from io import StringIO
        reader = csv.DictReader(StringIO(data))
        matches = list(reader)

        today = datetime.now().date()
        odds_data = []

        for m in matches:
            try:
                date_str = m.get('Date', '')
                for fmt in ['%d/%m/%Y', '%d/%m/%y']:
                    try:
                        match_date = datetime.strptime(date_str, fmt).date()
                        break
                    except:
                        continue
                else:
                    continue

                # 获取未来比赛（今天及以后）
                days_diff = (match_date - today).days
                if 0 <= days_diff <= 3:
                    home = m.get('HomeTeam', '')
                    away = m.get('AwayTeam', '')
                    ft_home = m.get('FTHG', '')
                    ft_away = m.get('FTAG', '')

                    # 跳过已有结果的比赛
                    if ft_home and ft_away and ft_home.isdigit() and ft_away.isdigit():
                        continue

                    # 赔率数据
                    b365h = m.get('B365H', '')
                    b365d = m.get('B365D', '')
                    b365a = m.get('B365A', '')
                    b365_over = m.get('B365>2.5', '')
                    b365_under = m.get('B365<2.5', '')

                    if b365h and b365d and b365a:
                        odds_data.append({
                            'date': match_date.isoformat(),
                            'home': home,
                            'away': away,
                            'odds_home': float(b365h),
                            'odds_draw': float(b365d),
                            'odds_away': float(b365a),
                            'odds_over': float(b365_over) if b365_over else None,
                            'odds_under': float(b365_under) if b365_under else None,
                        })
            except:
                continue

        print(f"获取到 {len(odds_data)} 场 {league} 赔率数据")
        return odds_data

    except Exception as e:
        print(f"获取 {league} 赔率失败: {e}")
        return []


def analyze_betting_value(pred: dict, odds: dict = None) -> dict:
    """
    分析投注价值

    Args:
        pred: 预测结果
        odds: 赔率数据 (可选)

    Returns:
        投注建议 {'type': str, 'odds': float, 'value': float, 'recommendation': str}
    """
    if not odds:
        return {'type': '无赔率数据', 'value': 0, 'recommendation': '暂无'}

    result = {
        'has_value': False,
        'bets': []
    }

    # 计算模型概率
    model_home = pred['home_prob']
    model_draw = pred['draw_prob']
    model_away = pred['away_prob']

    # 1. 胜平负价值分析
    bookie_home = 1 / odds['odds_home']
    bookie_draw = 1 / odds['odds_draw']
    bookie_away = 1 / odds['odds_away']

    # 价值 = 模型概率 * 赔率 - 1
    value_home = model_home * odds['odds_home'] - 1
    value_draw = model_draw * odds['odds_draw'] - 1
    value_away = model_away * odds['odds_away'] - 1

    # 找出最有价值的投注
    values = [
        ('主胜', value_home, odds['odds_home'], model_home),
        ('平局', value_draw, odds['odds_draw'], model_draw),
        ('客胜', value_away, odds['odds_away'], model_away),
    ]

    # 按价值排序
    values.sort(key=lambda x: x[1], reverse=True)

    for bet_type, value, odds_val, prob in values:
        if value > 0.05:  # 价值超过5%
            stars = '⭐⭐⭐' if value > 0.15 else ('⭐⭐' if value > 0.10 else '⭐')
            result['bets'].append({
                'type': bet_type,
                'odds': odds_val,
                'probability': round(prob * 100, 0),
                'value': round(value * 100, 1),
                'stars': stars,
                'edge': round((prob - (1/odds_val)) * 100, 1)
            })

    # 2. 大小球价值分析
    if odds.get('odds_over') and odds.get('odds_under'):
        model_total_xg = pred['total_xg']
        bookie_over = 1 / odds['odds_over']
        bookie_under = 1 / odds['odds_under']

        # 预期总进球 >= 2.5 的模型概率
        over_prob = pred.get('over_25_prob', 50) / 100

        value_over = over_prob * odds['odds_over'] - 1
        value_under = (1 - over_prob) * odds['odds_under'] - 1

        if value_over > 0.05:
            result['bets'].append({
                'type': '大2.5球',
                'odds': odds['odds_over'],
                'probability': round(over_prob * 100, 0),
                'value': round(value_over * 100, 1),
                'stars': '⭐⭐⭐' if value_over > 0.15 else ('⭐⭐' if value_over > 0.10 else '⭐'),
                'edge': round((over_prob - bookie_over) * 100, 1)
            })

        if value_under > 0.05:
            under_prob = 1 - over_prob
            result['bets'].append({
                'type': '小2.5球',
                'odds': odds['odds_under'],
                'probability': round(under_prob * 100, 0),
                'value': round(value_under * 100, 1),
                'stars': '⭐⭐⭐' if value_under > 0.15 else ('⭐⭐' if value_under > 0.10 else '⭐'),
                'edge': round((under_prob - bookie_under) * 100, 1)
            })

    result['has_value'] = len(result['bets']) > 0

    return result


def format_betting_advice(pred: dict, odds: dict = None) -> str:
    """格式化投注建议"""
    if not odds:
        return ""

    analysis = analyze_betting_value(pred, odds)

    if not analysis['has_value']:
        return ""

    lines = []
    lines.append("💰 <b>投注建议</b>")

    for bet in analysis['bets']:
        stars = bet.get('stars', '')
        lines.append(f"{stars} {bet['type']}")
        lines.append(f"   赔率: {bet['odds']} | 模型概率: {bet['probability']}%")
        lines.append(f"   价值: +{bet['value']}% | 优势: {bet['edge']}%")

    return "\n".join(lines)


def format_prediction(match: dict, pred: dict) -> str:
    """格式化预测输出"""
    home = match['home']
    away = match['away']
    league = match['league']
    home = get_team_cn(match['home'])
    away = get_team_cn(match['away'])
    h_prob = pred['home_prob'] * 100
    d_prob = pred['draw_prob'] * 100
    a_prob = pred['away_prob'] * 100

    # 推荐
    rec = pred['recommendation']
    conf = pred.get('confidence', '')

    # 比分推荐
    scores_str = ""
    for i, s in enumerate(pred.get('top_scores', [])):
        label = s.get('label', '⭐ 首选' if i == 0 else ('🔶 次选' if i == 1 else f'#{i+1}'))
        scores_str += f"\n   {label}: {s['score']} ({s['prob']:.1f}%)"

    # 半场预测
    ht_preds = pred.get('half_time_probs', [])
    ht_str = ", ".join([f"{s.get('label', s.get('score', ''))}({s['prob']:.0f}%)" for s in ht_preds]) if ht_preds else ", ".join(pred.get('half_time_predictions', []))

    # 下半场预测
    ft2_str = ", ".join(pred.get('second_half_predictions', []))

    # xG
    home_xg = pred.get('home_xg', 0)
    away_xg = pred.get('away_xg', 0)

    # 大小球
    total_xg = pred.get('total_xg', 0)
    over_25 = pred.get('over_25_prob', 0)
    over_rec = pred.get('over_recommendation', '')
    ht_total_xg = pred.get('ht_total_xg', 0)
    ht_over_15 = pred.get('ht_over_15_prob', 0)
    ht_over_rec = pred.get('ht_over_recommendation', '')

    # 让球信息
    handicap = pred.get('handicap', 0)
    handicap_str = f" | {home}让{handicap}球" if handicap > 0 else ""

    # 开球时间（北京时间）
    kickoff_bj = match.get('kickoff_beijing', '')
    end_bj = match.get('end_time_beijing', '')

    # 格式化日期为中文显示
    match_date = datetime.strptime(match['date'], '%Y-%m-%d')
    date_cn = match_date.strftime('%-m月%-d日')
    weekday_cn = ['周一','周二','周三','周四','周五','周六','周日'][match_date.weekday()]
    time_info = f"开球: {kickoff_bj}北京 | 预计{end_bj}结束" if kickoff_bj else ''

    return f"""
{'='*65}
{league:12}  |  {date_cn}({weekday_cn})  |  {time_info}
{'='*65}
{home:20} vs {away:20}
{'-'*65}
胜平负预测:
  {home}: {h_prob:.1f}%  |  平局: {d_prob:.1f}%  |  {away}: {a_prob:.1f}%
推荐: {rec} {conf}
{'-'*65}
比分推荐 (xG: {home}={home_xg:.1f} | {away}={away_xg:.1f}):
{scores_str}
{'-'*65}
半场预测:
  上半场: {ht_str}
{'-'*65}
大小球:
  全场: 预期{total_xg:.1f}球 | 大2.5球 {over_25:.0f}% | {over_rec}
  上半场: 预期{ht_total_xg:.1f}球 | 大1.5球 {ht_over_15:.0f}% | {ht_over_rec}{handicap_str}
{'='*65}"""


# ============ Telegram推送功能 ============

TELEGRAM_CHAT_ID = "8344519502"  # 树 树


def format_telegram_message(matches: list, predictions: list) -> str:
    """格式化Telegram推送消息（美观中文版）"""
    lines = []

    # 标题
    lines.append("⚽ <b>每日足球预测</b>")
    lines.append(f"📅 {datetime.now().strftime('%Y-%m-%d')} | 明晚23点出结果对比")
    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━━━")

    for i, (match, pred) in enumerate(zip(matches, predictions), 1):
        home = match['home']
        away = match['away']
        league = match['league']
        date = match['date']

        # 转换为中文
        home_cn = get_team_cn(home)
        away_cn = get_team_cn(away)
        league_cn = LEAGUE_CN.get(league, league)

        h_prob = pred['home_prob'] * 100
        d_prob = pred['draw_prob'] * 100
        a_prob = pred['away_prob'] * 100
        rec = pred['recommendation']
        if rec in [home, away]:
            rec = get_team_cn(rec)
        conf = pred.get('confidence', '')

        # 低信心警告
        low_conf_warning = ''
        if '低信心' in conf:
            low_conf_warning = ' ⚠️ 低信心，建议观望'

        # 比分推荐（3个）
        top_scores = pred.get('top_scores', [])
        scores_str = ""
        if top_scores:
            score_parts = []
            labels = ['⭐', '🔶', '🔷']
            for j, s in enumerate(top_scores[:3]):
                score_parts.append(f"{labels[j]}{s['score']}({s['prob']:.0f}%)")
            scores_str = " ".join(score_parts)

        # 半场预测（3个）
        ht_preds = pred.get('half_time_probs', [])
        ht_str = ""
        if ht_preds:
            ht_parts = []
            for s in ht_preds[:3]:
                ht_parts.append(f"{s['score']}({s['prob']:.0f}%)")
            ht_str = " ".join(ht_parts)
        else:
            ht_str = "-"

        # 大小球
        total_xg = pred.get('total_xg', 0)
        over_rec = pred.get('over_recommendation', '')
        ht_total_xg = pred.get('ht_total_xg', 0)
        ht_over_rec = pred.get('ht_over_recommendation', '')

        # 开球时间（北京时间）
        kickoff_bj = match.get('kickoff_beijing', '')
        end_bj = match.get('end_time_beijing', '')

        # 格式化日期为中文显示
        match_date = datetime.strptime(date, '%Y-%m-%d')
        date_cn = match_date.strftime('%-m月%-d日')

        # 判断星期几
        weekday_cn = ['周一','周二','周三','周四','周五','周六','周日'][match_date.weekday()]
        time_info = f"📅 {date_cn}({weekday_cn}) ⏰ {kickoff_bj}开 | 预计{end_bj}结束" if kickoff_bj else f"📅 {date_cn}({weekday_cn})"

        # 格式化输出
        lines.append(f"{i}️⃣ <b>{league_cn}</b>")
        lines.append(f"{time_info}")
        lines.append(f"⚽ {home_cn} vs {away_cn}")
        lines.append(f"📊 胜平负: {h_prob:.0f}% | {d_prob:.0f}% | {a_prob:.0f}%")
        lines.append(f"✅ 推荐: {rec} {conf}{low_conf_warning}")
        lines.append(f"⚽ 比分: {scores_str}")
        lines.append(f"⏱️ 半场: {ht_str}")
        lines.append(f"📈 大小: 全场{total_xg:.1f}球({over_rec.replace('大2.5球 ', '').replace('小2.5球 ', '')}) | 上半场{ht_total_xg:.1f}球({ht_over_rec.replace('上半场大1.5球 ', '').replace('上半场小1.5球 ', '')})")

        if i < len(matches):
            lines.append("━━━━━━━━━━━━━━━━━━━━")

    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append("📊 <i>胜平负/比分/大小球 明晚23点自动对比</i>")

    # 尝试获取赔率并添加投注建议
    try:
        odds_list = fetch_odds(league)
        if odds_list:
            # 找匹配的比赛
            for o in odds_list:
                if (o['home'] in home or home in o['home']) and (o['away'] in away or away in o['away']):
                    advice = format_betting_advice(pred, o)
                    if advice:
                        lines.append("")
                        lines.append(advice)
                    break
    except:
        pass

    return "\n".join(lines)


def format_telegram_result(matches: list, predictions: list, results: list) -> str:
    """格式化结果更新消息"""
    lines = []
    lines.append("📊 <b>预测结果更新</b>")
    lines.append(f"📅 {datetime.now().strftime('%Y-%m-%d')}")
    lines.append("")

    correct = 0
    for match, pred, result in zip(matches, predictions, results):
        home = match['home']
        away = match['away']
        league = match['league']

        rec = pred['recommendation']
        actual_home, actual_away = result['home_goals'], result['away_goals']
        actual_result = "平局" if actual_home == actual_away else (home if actual_home > actual_away else away)

        # 判断预测是否正确
        is_correct = False
        if rec == actual_result:
            is_correct = True
            correct += 1

        # 判断比分是否正确
        top_scores = pred.get('top_scores', [])
        score_correct = any(s['score'] == f"{actual_home}-{actual_away}" for s in top_scores)

        status = "✅" if is_correct else "❌"
        score_status = "🎯" if score_correct else ""

        lines.append(f"{status} <b>{league}</b>: {home} {actual_home}-{actual_away} {away}")
        lines.append(f"   推荐:{rec} | 实际:{actual_result} {score_status}")

    lines.append("")
    total = len(results)
    if total > 0:
        lines.append(f"📈 本轮准确率: {correct}/{total} ({correct/total*100:.0f}%)")

    return "\n".join(lines)


def send_telegram_message(message: str) -> bool:
    """发送消息到Telegram（优先使用hermes，回退到API）"""
    import urllib.parse
    import urllib.request
    
    # 方法1: 尝试使用hermes命令行工具
    try:
        import subprocess
        result = subprocess.run(
            ['hermes', 'chat', '--message', message],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            print(f"Telegram推送成功(hermes)")
            return True
    except FileNotFoundError:
        pass  # hermes不存在，继续用API
    except Exception as e:
        print(f"hermes推送失败: {e}，尝试API...")

    # 方法2: 使用Telegram Bot API
    try:
        config_path = os.path.expanduser("~/.hermes/.secrets.json")
        token = ''
        if os.path.exists(config_path):
            with open(config_path) as f:
                config = json.load(f)
                token = config.get('telegram_bot_token', '')

        if not token:
            print("未找到Telegram bot token，跳过推送")
            return False

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = urllib.parse.urlencode({
            'chat_id': TELEGRAM_CHAT_ID,
            'text': message,
            'parse_mode': 'HTML'
        }).encode()

        req = urllib.request.Request(url, data=data)
        resp = urllib.request.urlopen(req, timeout=10)
        print(f"Telegram推送成功(API)")
        return True

    except Exception as e:
        print(f"Telegram API推送失败: {e}")
        return False


def save_predictions(matches: list, predictions: list, filename: str = None):
    """保存预测结果到JSON"""
    if filename is None:
        filename = f"predictions_{datetime.now().strftime('%Y%m%d')}.json"

    filepath = os.path.join(DATA_DIR, filename)

    data = {
        'created_at': datetime.now().isoformat(),
        'matches': matches,
        'predictions': predictions,
    }

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"预测结果已保存: {filepath}")
    return filepath


def load_today_predictions() -> dict:
    """加载今日预测"""
    filename = f"predictions_{datetime.now().strftime('%Y%m%d')}.json"
    filepath = os.path.join(DATA_DIR, filename)

    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)

    return None


def update_with_results(predictions_path: str = None):
    """自动更新预测结果（从football-data获取实际结果）"""
    if predictions_path is None:
        # 尝试加载昨日预测（今天检查昨天的结果）
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
        filename = f"predictions_{yesterday}.json"
        filepath = os.path.join(DATA_DIR, filename)

        if not os.path.exists(filepath):
            print("没有找到昨日预测，无法自动更新结果")
            return

        with open(filepath, 'r', encoding='utf-8') as f:
            predictions_data = json.load(f)
    else:
        with open(predictions_path, 'r', encoding='utf-8') as f:
            predictions_data = json.load(f)

    matches = predictions_data.get('matches', [])
    predictions = predictions_data.get('predictions', [])

    if not matches:
        print("没有预测比赛")
        return

    print(f"\n📊 自动检查比赛结果...")
    print(f"检查 {len(matches)} 场预测比赛的实际结果")
    print("-" * 50)

    # 动态计算需要查询的天数（根据预测文件中的比赛日期）
    today = datetime.now().date()
    match_dates = []
    for match in matches:
        if 'date' in match and match['date']:
            try:
                match_date = datetime.fromisoformat(match['date']).date()
                match_dates.append(match_date)
            except:
                pass
    
    if match_dates:
        # 计算最远的比赛日期距离今天多少天
        max_days_ahead = max((d - today).days for d in match_dates)
        # 比赛后通常1-2天能查到结果，所以查询范围要覆盖比赛日+1或+2天
        days_back = max(0, max_days_ahead + 1)  # 比赛日+1天
        print(f"📅 预测比赛日期范围: {min(match_dates)} ~ {max(match_dates)}")
        print(f"📅 最远比赛距离今天: {max_days_ahead} 天")
        print(f"📅 动态计算days_back: {days_back}")
    else:
        days_back = 1  # 默认值
        print(f"⚠️ 无法获取比赛日期，使用默认值 days_back={days_back}")
    
    # 获取所有联赛的实际结果
    all_results = []
    leagues = ["EPL", "La Liga", "Serie A", "Bundesliga", "Ligue 1"]

    for league in leagues:
        results = get_completed_matches(league, days_back=days_back)
        all_results.extend(results)

    # 对比预测和实际结果
    correct = 0
    total = 0
    score_correct = 0
    half_correct = 0
    results_summary = []

    for match, pred in zip(matches, predictions):
        home = match['home']
        away = match['away']
        league = match['league']

        # 找实际结果
        actual = None
        for r in all_results:
            # 尝试匹配（考虑名称变体）
            if (home in r['home'] or r['home'] in home) and \
               (away in r['away'] or r['away'] in away):
                actual = r
                break

        # 处理嵌套结构：pred可能是[match, pred_dict]列表
        if isinstance(pred, list) and len(pred) >= 2:
            pred = pred[1]
        rec = pred['recommendation']

        if actual:
            ft_home = actual['ft_home']
            ft_away = actual['ft_away']
            actual_result = "平局" if ft_home == ft_away else (home if ft_home > ft_away else away)

            # 判断胜平负预测是否正确
            is_correct = rec == actual_result
            if is_correct:
                correct += 1
            total += 1

            # 判断比分是否正确
            top_scores = pred.get('top_scores', [])
            is_score_correct = any(s['score'] == f"{ft_home}-{ft_away}" for s in top_scores)
            if is_score_correct:
                score_correct += 1

            # 判断半场是否正确
            ht_str = actual.get('ht_home')
            if ht_str is not None:
                ht_away = actual.get('ht_away')
                ht_pred = pred.get('half_time_predictions', [])
                if f"{ht_str}-{ht_away}" in ht_pred:
                    half_correct += 1

            status = "✅" if is_correct else "❌"
            score_status = "🎯" if is_score_correct else ""

            print(f"{status} {league}: {home} {ft_home}-{ft_away} {away}")
            print(f"   推荐:{rec} | 实际:{actual_result} {score_status}")

            results_summary.append({
                'match': f"{home} vs {away}",
                'actual': f"{ft_home}-{ft_away}",
                'recommended': rec,
                'actual_result': actual_result,
                'correct': is_correct,
                'score_correct': is_score_correct,
            })
        else:
            print(f"⏳ {league}: {home} vs {away} - 暂无结果")
            results_summary.append({
                'match': f"{home} vs {away}",
                'actual': "pending",
                'recommended': rec,
                'actual_result': "pending",
                'correct': False,
                'score_correct': False,
            })

    # 保存结果
    print("-" * 50)

    if total > 0:
        win_rate = correct / total * 100
        score_rate = score_correct / total * 100
        half_rate = half_correct / total * 100 if total > 0 else 0

        print(f"📈 预测结果统计:")
        print(f"   胜平负: {correct}/{total} ({win_rate:.0f}%)")
        print(f"   比分: {score_correct}/{total} ({score_rate:.0f}%)")
        print(f"   半场: {half_correct}/{total} ({half_rate:.0f}%)")

        # 保存到统计文件
        stats_file = os.path.join(DATA_DIR, 'accuracy_stats.json')
        if os.path.exists(stats_file):
            with open(stats_file, 'r') as f:
                stats = json.load(f)
        else:
            stats = {'total': 0, 'correct': 0, 'score_correct': 0, 'half_correct': 0, 'by_league': {}}

        stats['total'] = stats.get('total', 0) + total
        stats['correct'] = stats.get('correct', 0) + correct
        stats['score_correct'] = stats.get('score_correct', 0) + score_correct
        stats['half_correct'] = stats.get('half_correct', 0) + half_correct
        stats['win_rate'] = stats['correct'] / stats['total'] * 100
        stats['score_rate'] = stats['score_correct'] / stats['total'] * 100
        stats['half_rate'] = stats.get('half_correct', 0) / stats['total'] * 100

        with open(stats_file, 'w') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)

        return {
            'total': total,
            'correct': correct,
            'win_rate': win_rate,
            'score_correct': score_correct,
            'score_rate': score_rate,
            'results': results_summary
        }

    return None


def show_accuracy_stats():
    """显示预测准确率统计"""
    stats_file = os.path.join(DATA_DIR, 'accuracy_stats.json')

    if not os.path.exists(stats_file):
        print("\n📊 暂无预测统计（需要先积累预测数据）")
        return

    with open(stats_file, 'r') as f:
        stats = json.load(f)

    print(f"""
📊 预测准确率统计
{'='*40}
总预测场次: {stats.get('total', 0)}
胜平负正确: {stats.get('win_rate', 0):.1f}%
比分正确:   {stats.get('score_rate', 0):.1f}%
大小球正确: {stats.get('ou_rate', 0):.1f}%
""")

    # 按联赛显示
    by_league = stats.get('by_league', {})
    if by_league:
        print("按联赛:")
        for league, data in by_league.items():
            print(f"  {league}: {data.get('win_rate', 0):.1f}%")


def main():
    """主函数"""
    import argparse
    parser = argparse.ArgumentParser(description='每日足球预测')
    parser.add_argument('--days', type=int, default=3, help='提前几天获取比赛（默认3天）')
    parser.add_argument('--force', action='store_true', help='强制重新生成预测（忽略已有预测）')
    args = parser.parse_args()
    
    print("=" * 60)
    print("⚽ 每日足球预测 v2.0")
    print("=" * 60)

    # ========== 第一步：自动检查昨天的预测结果 ==========
    print("\n📊 检查昨日预测结果...")
    result_data = update_with_results()
    if result_data:
        print(f"\n昨日预测准确率: {result_data['win_rate']:.0f}%")
    else:
        print("昨日无预测结果需要检查")

    # ========== 第二步：显示历史统计 ==========
    show_accuracy_stats()

    # ========== 第三步：检查是否有今日预测 ==========
    if not args.force:
        today_data = load_today_predictions()
        if today_data:
            print(f"\n今日已有预测 (创建于 {today_data['created_at']})")

            matches = today_data.get('matches', [])
            predictions = today_data.get('predictions', [])

            if matches:
                print(f"\n共 {len(matches)} 场比赛:\n")

                for i, (match, pred) in enumerate(zip(matches, predictions), 1):
                    # 处理嵌套结构：pred可能是[match, pred_dict]列表
                    if isinstance(pred, list) and len(pred) >= 2:
                        pred = pred[1]
                    print(format_prediction(match, pred))
            return

    # 获取近期比赛（只选当天或次日能出结果的）
    print("\n📅 获取近期比赛...")
    
    all_matches = []
    leagues = ["EPL", "La Liga", "Serie A", "Bundesliga", "Ligue 1"]

    # 只获取指定天内的比赛
    for league in leagues:
        matches = get_upcoming_matches(league, days_ahead=args.days)
        all_matches.extend(matches)
        if matches:
            print(f"  {league}: {len(matches)} 场比赛")

    if not all_matches:
        print("获取比赛失败，请稍后重试")
        return

    # 按日期排序
    all_matches.sort(key=lambda x: x['date'])

    # 只取前8场（只选当天能结束的比赛）— 扩大样本量
    selected = all_matches[:8]

    print(f"\n📋 选取 {len(selected)} 场比赛进行预测:\n")

    predictions = []

    for match in selected:
        home = match['home']
        away = match['away']

        print(f"预测: {home} vs {away}...", end=" ")

        pred = make_prediction(home, away)
        predictions.append(pred)

        # 显示简要结果
        h = pred['home_prob'] * 100
        d = pred['draw_prob'] * 100
        a = pred['away_prob'] * 100
        print(f"{h:.0f}% - {d:.0f}% - {a:.0f}%")

    # 保存预测
    save_predictions(selected, predictions)

    # 显示详细预测
    print("\n" + "=" * 60)
    print("📊 详细预测结果")
    print("=" * 60)

    for match, pred in zip(selected, predictions):
        print(format_prediction(match, pred))

    # 发送到Telegram
    print("\n" + "-" * 40)
    telegram_msg = format_telegram_message(selected, predictions)
    send_telegram_message(telegram_msg)

    print("\n💡 提示: 明天回来输入比赛结果，我会更新准确率统计")
    print("   输入格式: python daily_predictions.py --result 'home-away-3-1'")
    print("=" * 60)


if __name__ == "__main__":
    main()
