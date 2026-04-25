"""
比赛结果自动查询脚本
从Flashscore抓取比赛结果
"""
import re
import json
from datetime import datetime, timedelta
from typing import Optional

def scrape_flashscore_results(date_str: str, league: str = "england/premier-league") -> dict:
    """从Flashscore抓取比赛结果
    
    Args:
        date_str: 日期字符串 (YYYY-MM-DD)
        league: 联赛路径
    
    Returns:
        比赛结果字典
    """
    try:
        import urllib.request
        url = f"https://www.flashscore.com/football/{league}/results/{date_str}/"
        
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode('utf-8')
        
        # 提取比赛数据
        matches = extract_matches_from_html(html)
        
        return {
            'success': True,
            'date': date_str,
            'league': league,
            'matches': matches,
            'count': len(matches)
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'date': date_str,
            'league': league,
            'matches': []
        }


def extract_matches_from_html(html: str) -> list:
    """从HTML中提取比赛结果"""
    matches = []
    
    # 匹配模式: 球队名 + 比分
    # 格式如: Manchester City 2 - 1 Liverpool
    pattern = r'<span class="event__home".*?>([^<]+)</span>.*?<span class="event__score".*?>([^<]+)</span>.*?<span class="event__away".*?>([^<]+)</span>'
    
    # 更简单的模式：直接搜索包含比分的行
    lines = html.split('\n')
    current_match = {}
    
    for line in lines:
        # 提取时间
        time_match = re.search(r'class="event__time"[^>]*>([^<]+)</span>', line)
        if time_match:
            current_match['time'] = time_match.group(1).strip()
        
        # 提取主队
        home_match = re.search(r'class="event__home"[^>]*>([^<]+)</span>', line)
        if home_match:
            current_match['home'] = home_match.group(1).strip()
        
        # 提取客队
        away_match = re.search(r'class="event__away"[^>]*>([^<]+)</span>', line)
        if away_match:
            current_match['away'] = away_match.group(1).strip()
        
        # 提取比分 - 需要找到同一个event块里的比分
        score_match = re.search(r'class="event__score"[^>]*>([^<]+)</span>', line)
        if score_match and 'home' in current_match and 'away' in current_match:
            score = score_match.group(1).strip()
            # 比分格式可能是 "2 - 1" 或 "2:1"
            score_parts = re.split(r'[-:]\s*', score)
            if len(score_parts) >= 2:
                current_match['score'] = score
                current_match['home_score'] = int(score_parts[0])
                current_match['away_score'] = int(score_parts[1])
                
                # 计算胜平负
                if current_match['home_score'] > current_match['away_score']:
                    current_match['result'] = 'home'
                elif current_match['home_score'] < current_match['away_score']:
                    current_match['result'] = 'away'
                else:
                    current_match['result'] = 'draw'
                
                matches.append(current_match.copy())
                current_match = {}
    
    return matches


def find_match_result(matches: list, home_team: str, away_team: str) -> Optional[dict]:
    """在一组比赛结果中查找特定比赛"""
    home_lower = home_team.lower()
    away_lower = away_team.lower()
    
    for match in matches:
        match_home = match.get('home', '').lower()
        match_away = match.get('away', '').lower()
        
        # 简单匹配（可能需要更智能的匹配逻辑）
        if (home_lower in match_home or match_home in home_lower) and \
           (away_lower in match_away or match_away in away_lower):
            return match
    
    return None


def get_match_result(date: str, league: str, home: str, away: str) -> dict:
    """获取单场比赛的结果"""
    result = scrape_flashscore_results(date, league)
    
    if result['success']:
        match = find_match_result(result['matches'], home, away)
        if match:
            return {
                'success': True,
                'date': date,
                'home': home,
                'away': away,
                'result': match
            }
        else:
            return {
                'success': False,
                'error': '比赛未找到',
                'date': date,
                'home': home,
                'away': away,
                'available_matches': [f"{m.get('home')} vs {m.get('away')}" for m in result['matches'][:5]]
            }
    
    return result


# 测试代码
if __name__ == '__main__':
    # 测试抓取EPL 4月12日的比赛结果
    print("=== 测试: EPL 2026-04-12 ===")
    result = scrape_flashscore_results("2026-04-12", "england/premier-league")
    
    if result['success']:
        print(f"找到 {result['count']} 场比赛:")
        for m in result['matches'][:10]:
            print(f"  {m.get('time')} {m.get('home')} {m.get('score')} {m.get('away')}")
    else:
        print(f"失败: {result.get('error')}")
    
    print()
    print("=== 测试: 查找 Chelsea vs Manchester City ===")
    match = get_match_result("2026-04-12", "england/premier-league", "Chelsea", "Manchester City")
    if match['success']:
        print(f"找到比赛: {match['result']}")
    else:
        print(f"未找到: {match.get('error')}")
        print(f"可用的比赛: {match.get('available_matches', [])}")
