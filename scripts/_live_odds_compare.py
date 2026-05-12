#!/usr/bin/env python3
"""Live Polymarket odds vs Elo model comparison"""
import sys, json, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'core'))

from team_stats import EloSystem

# Load Elo
elo = EloSystem()
elo_dict = elo.get_all_ratings()

# Load polymarket data
with open(os.path.expanduser('~/hermes-world-cup/polymarket/2026-04-30-14-champion-odds.json')) as f:
    pm_data = json.load(f)

# Build mapping
team_to_pm = {}
for t in pm_data.get('teams', []):
    team = t.get('team','')
    prob = t.get('prob',0) * 100
    vol = t.get('volume',0)
    liq = t.get('liquidity', 0)
    team_to_pm[team] = {'prob': prob, 'volume': vol, 'liquidity': liq}

# Team name mapping
poll_map = {
    'Uzbekistan': 'UZB', 'Curacao': 'CUW', 'USA': 'USA', 'New Zealand': 'NZL',
    'Saudi Arabia': 'KSA', 'South Africa': 'RSA', 'Jordan': 'JOR', 'France': 'FRA',
    'Qatar': 'QAT', 'Iran': 'IRN', 'Egypt': 'EGY', 'South Korea': 'KOR',
    'Canada': 'CAN', 'Cape Verde': 'CPV', 'Australia': 'AUS', 'Tunisia': 'TUN',
    'Algeria': 'ALG', 'Ivory Coast': 'CIV', 'Ecuador': 'ECU', 'Japan': 'JPN',
    'Spain': 'ESP', 'Paraguay': 'PAR', 'Morocco': 'MAR', 'Scotland': 'SCO',
    'Portugal': 'POR', 'Haiti': 'HAI', 'Brazil': 'BRA', 'Mexico': 'MEX',
    'Netherlands': 'NED', 'Ghana': 'GHA', 'Austria': 'AUT', 'Croatia': 'CRO',
    'Argentina': 'ARG', 'Senegal': 'SEN', 'Uruguay': 'URU', 'Belgium': 'BEL',
    'England': 'ENG', 'Norway': 'NOR', 'Congo DR': 'COD', 'Germany': 'GER',
    'Switzerland': 'SUI', 'Colombia': 'COL', 'Iraq': 'IRQ', 'Panama': 'PAN',
    'Bosnia-Herzegovina': 'BIH', 'Italy': 'ITA', 'Turkiye': 'TUR', 'Czechia': 'CZE',
    'Sweden': 'SWE', 'Peru': 'PER'
}

# Get elo for each team
team_elos = {}
for pm_team in team_to_pm:
    code = poll_map.get(pm_team)
    if code and code in elo_dict:
        team_elos[pm_team] = int(elo_dict[code])
    elif code:
        team_elos[pm_team] = 1500
    else:
        team_elos[pm_team] = 1200  # unknown teams

# Calculate model probabilities based on Elo
import math
total_strength = sum(math.pow(2, (v-1500)/400) for v in team_elos.values())
model_probs = {}
for team, elo_val in team_elos.items():
    strength = math.pow(2, (elo_val-1500)/400)
    model_probs[team] = (strength / total_strength) * 100

# Filter to real contenders (market > 0.5%)
contenders = {t for t in team_to_pm if team_to_pm[t]['prob'] >= 0.5}

print("# Live Polymarket vs Elo Model Comparison (April 30, 2026)")
print()
print(f"Total Polymarket Volume: ${float(pm_data.get('total_volume',0)):,.0f}")
print(f"24h Volume: ${float(pm_data.get('volume_24h',0)):,.0f}")
print()
col_hdr = f"{'Team':20s} {'Elo':>5s} {'Market%':>8s} {'Model%':>8s} {'Dev%':>8s} {'Volume':>14s}"
print(col_hdr)
print("-" * 70)

sorted_teams = sorted(team_to_pm.keys(), key=lambda t: team_to_pm[t]['prob'], reverse=True)

# Track deviations
overvalued = []  # Market > Model
undervalued = []  # Model > Market
fair_price = []

for team in sorted_teams:
    mp = team_to_pm[team]['prob']
    vol = team_to_pm[team]['volume']
    ev = team_elos.get(team, 'N/A')
    mv = model_probs.get(team, 0)
    
    if mp < 0.5:
        continue
    
    if mv > 0:
        dev = (mp - mv) / mv * 100
    else:
        dev = 999
    
    if abs(dev) < 20:
        indicator = "⚪"
        fair_price.append(team)
    elif dev < -20:
        indicator = "🟢"
        undervalued.append(team)
    else:
        indicator = "🔴"
        overvalued.append(team)
    
    line = f"{team:20s} {str(ev):>5s} {mp:7.2f}% {mv:7.2f}% {dev:+7.1f}% {indicator:2s} {format(vol,',.0f'):>14s}"
    print(line)

print()
print("## Deviation Analysis")
print(f"\n### 🔴 Overvalued by Market (n={len(overvalued)})")
for t in overvalued:
    mp = team_to_pm[t]['prob']
    mv = model_probs[t]
    dev = (mp-mv)/mv*100
    print(f"  {t}: Market={mp:.2f}% vs Elo={mv:.2f}% ({dev:+.0f}%)")

print(f"\n### 🟢 Undervalued by Market (n={len(undervalued)})")
for t in undervalued:
    mp = team_to_pm[t]['prob']
    mv = model_probs[t]
    dev = (mp-mv)/mv*100
    print(f"  {t}: Market={mp:.2f}% vs Elo={mv:.2f}% ({dev:+.0f}%)")

print(f"\n### ⚪ Fair Price Zone (n={len(fair_price)})")
for t in fair_price:
    mp = team_to_pm[t]['prob']
    mv = model_probs[t]
    dev = (mp-mv)/mv*100
    print(f"  {t}: Market={mp:.2f}% vs Elo={mv:.2f}% (dev={dev:+.0f}%)")

# Volume analysis
print("\n## Volume Analysis")
print("\n### Volume-to-Probability Ratio (higher = more speculative)")
top_by_ratio = sorted(sorted_teams, key=lambda t: team_to_pm[t]['volume']/max(team_to_pm[t]['prob'], 0.01), reverse=True)
for t in top_by_ratio[:10]:
    mp = team_to_pm[t]['prob']
    vol = team_to_pm[t]['volume']
    ratio = vol / max(mp/100, 0.0001)
    print(f"  {t:20s} prob={mp:.2f}% vol=${vol:,.0f} ratio={ratio:,.0f}x")

print("\n### Price Anchor Stability (low deviation = stable)")
for t in fair_price[:8]:
    print(f"  {t:20s} @ {team_to_pm[t]['prob']:.2f}%")
