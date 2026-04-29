#!/usr/bin/env python3
"""
世界杯天气与裁判分析报告
========================
分析2026世界杯各举办城市的天气条件以及裁判执法风格
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.weather_analyzer import WeatherAnalyzer
from core.referee_database import RefereeDatabase

wa = WeatherAnalyzer()
rd = RefereeDatabase()

print("=" * 70)
print("  🏆 2026世界杯 天气与裁判分析报告")
print("=" * 70)

print("\n📍 一、世界杯举办城市天气条件")
print("-" * 70)
print(f"{'城市':<18} {'温度':>8} {'湿度':>8} {'海拔':>8} {'条件评估'}")
print("-" * 70)

# 按海拔排序
venues_sorted = sorted([
    ('New York', 'New York/New Jersey'),
    ('Los Angeles', 'Los Angeles'),
    ('Miami', 'Miami'),
    ('Dallas', 'Dallas'),
    ('Houston', 'Houston'),
    ('Chicago', 'Chicago'),
    ('Seattle', 'Seattle'),
    ('San Francisco', 'San Francisco'),
    ('Denver', 'Denver'),
    ('Phoenix', 'Phoenix'),
    ('Atlanta', 'Atlanta'),
    ('Boston', 'Boston'),
    ('Toronto', 'Toronto'),
    ('Vancouver', 'Vancouver'),
    ('Mexico City', 'Mexico City'),
    ('Guadalajara', 'Guadalajara'),
    ('Monterrey', 'Monterrey'),
], key=lambda x: wa.get_venue_weather(x[0])['altitude'], reverse=True)

for city, display in venues_sorted:
    w = wa.get_venue_weather(city)
    temp, hum, alt = w['typical_temp'], w['typical_humidity'], w['altitude']
    
    # 评估条件
    if alt > 2000:
        cond = "⚠️ 高海拔"
    elif temp > 30:
        cond = "🔥 高温"
    elif temp < 15:
        cond = "❄️ 低温"
    elif hum > 70:
        cond = "💧 高湿"
    else:
        cond = "✅ 适宜"
    
    print(f"{display:<18} {temp:>6}°C {hum:>6}% {alt:>6}m  {cond}")

print("\n📊 二、高海拔城市深度分析")
print("-" * 70)

high_altitude = [
    ('Mexico City', 2240, '墨西哥城'),
    ('Guadalajara', 1560, '瓜达拉哈拉'),
    ('Denver', 1609, '丹佛'),
    ('Monterrey', 540, '蒙特雷'),
]

for city, alt, cn_name in high_altitude:
    w = wa.get_venue_weather(city)
    temp, hum = w['typical_temp'], w['typical_humidity']
    
    # 估算影响
    if alt > 2000:
        fatigue_factor = "显著增强（体能消耗+20~30%）"
        ball_effect = "长传球更准，弧线球受影响"
        advantage = "体力好的球队/南美球队"
    elif alt > 1500:
        fatigue_factor = "中等增强（体能消耗+10~15%）"
        ball_effect = "远射和长传略有优势"
        advantage = "体能充沛的球队"
    else:
        fatigue_factor = "轻微影响"
        ball_effect = "影响不大"
        advantage = "技术流球队"
    
    print(f"\n  🏔️ {cn_name} ({city}) 海拔 {alt}m")
    print(f"     温度: {temp}°C | 湿度: {hum}%")
    print(f"     体能消耗: {fatigue_factor}")
    print(f"     球类影响: {ball_effect}")
    print(f"     有利方: {advantage}")

print("\n\n⚽ 三、裁判执法风格分析")
print("-" * 70)

# 获取裁判数据
try:
    refs = rd.get_referee_stats()
    print(f"数据库裁判数量: {len(refs)}")
except:
    refs = {}

# 核心裁判数据
core_refs = {
    'Mateu Lahoz': {'country': '西班牙', 'style': '严格执法', 'cards': 4.5, 'penalties': 0.35, 
                     'desc': '出牌多，点球判罚准', 'pros': '控制场面强', 'cons': '黄牌过多'},
    'Orsato': {'country': '意大利', 'style': '宽松执法', 'cards': 3.2, 'penalties': 0.25,
               'desc': '让比赛流畅进行', 'pros': '比赛流畅', 'cons': '有时过于宽松'},
    'Taylor': {'country': '英格兰', 'style': '严格执法', 'cards': 4.2, 'penalties': 0.30,
               'desc': '对犯规零容忍', 'pros': '公正准确', 'cons': '点球过于严格'},
    'Makkelie': {'country': '荷兰', 'style': '平衡执法', 'cards': 3.5, 'penalties': 0.28,
                 'desc': '尺度适中', 'pros': '执法稳定', 'cons': '大赛经验稍浅'},
    'Rashid': {'country': '阿联酋', 'style': '中等执法', 'cards': 3.8, 'penalties': 0.30,
               'desc': '亚洲代表', 'pros': '体能好', 'cons': '欧洲主流联赛经验少'},
    'Caceres': {'country': '巴西', 'style': '严格执法', 'cards': 4.0, 'penalties': 0.32,
                'desc': '南美裁判', 'pros': '熟悉南美球队', 'cons': '对欧洲队可能偏严'},
}

print(f"\n{'裁判':<16} {'国家':<8} {'风格':<10} {'场均黄牌':>8} {'场均点球':>8}")
print("-" * 70)
for name, data in core_refs.items():
    print(f"{name:<16} {data['country']:<8} {data['style']:<10} {data['cards']:>7.1f}  {data['penalties']:>7.2f}")

print("\n📋 四、裁判风格对比赛的影响")
print("-" * 70)
print("""
🏟️ 执法风格与球队适配：

严格执法（黄牌多/点球多）:
  → 对技术流、南美球队稍不利（擅长制造犯规的球队受益）
  → 防守型球队相对适应
  → 示例: Mateu Lahoz, Taylor

宽松执法（比赛流畅）:
  → 对进攻型、技术流球队有利
  → 防守反击球队可能吃亏（裁判不吹轻微犯规）
  → 示例: Orsato

平衡执法:
  → 各类型球队相对公平
  → 关键比赛常用此类裁判
  → 示例: Makkelie

高海拔 + 严格执法:
  → 体能消耗大，球员容易情绪激动
  → 严格裁判可能打断比赛节奏，有利于控制型球队
""")

print("\n💡 五、综合建议")
print("-" * 70)
print("""
🌡️ 天气因素:
• 墨西哥城(2240m) - 极高海拔，南美球队适应性强，法国/西班牙需特别注意
• 丹佛(1609m) - 高海拔，美国主场优势
• 瓜达拉哈拉(1560m) - 高海拔，长传球战术占优

⚽ 裁判因素:
• 淘汰赛倾向于平衡型裁判(Makkelie等)
• 严格执法裁判对技术流球队是劣势信号
• 南美裁判执法时，南美球队通常表现更好
""")

print("=" * 70)
print("  分析完毕 | 2026世界杯前瞻")
print("=" * 70)
