#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "core"))

from weather_analyzer import WeatherAnalyzer
from referee_database import RefereeDatabase

wa = WeatherAnalyzer()
rd = RefereeDatabase()

# Weather for Barcelona (Montjuïc/Olympic Stadium)
print("=== 巴塞罗那 天气 ===")
weather_bcn = wa.get_venue_weather("Barcelona")
print(weather_bcn)

impact_bcn = wa.analyze_weather_impact("Barcelona", "Celta Vigo", is_home=True)
print("\n=== 天气影响分析 ===")
print(impact_bcn)

# Referee data
print("\n=== 裁判数据库 ===")
try:
    refs = rd.get_referee_stats()
    print(f"数据库裁判数: {len(refs)}")
    # Try La Liga matches
    la_liga_refs = [r for r in refs if 'La Liga' in str(r)]
    print(f"La Liga裁判: {len(la_liga_refs)}")
    if la_liga_refs:
        print(la_liga_refs[0])
except Exception as e:
    print(f"Error: {e}")
    print("Referee database methods:", [m for m in dir(rd) if not m.startswith('_')])
