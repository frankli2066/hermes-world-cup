#!/usr/bin/env python3
"""
Polymarket市场赔率分析器 v3.4

功能：
1. 显示所有球队的夺冠赔率
2. 对比模型预测 vs 市场赔率
3. 找出被高估/低估的球队
4. 生成市场共识报告

使用方法：
    python3 polymarket-analyzer.py
"""

import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "core"))

from core.team_stats import EloSystem
from core.elo_calibrator import EloCalibrator, simulate_champion_probs
from core.data_pipeline import DataPipeline


def load_latest_polymarket():
    """加载最新的Polymarket数据"""
    base_dir = os.path.expanduser("~/hermes-world-cup/polymarket")
    files = sorted(os.listdir(base_dir))
    
    champion_files = [f for f in files if "champion-odds" in f]
    if not champion_files:
        return None
    
    latest = champion_files[-1]
    with open(os.path.join(base_dir, latest)) as f:
        return json.load(f), latest


def analyze_market_vs_model():
    """分析市场赔率 vs 模型预测"""
    print("=" * 70)
    print("📊 Polymarket 市场赔率 vs 模型预测分析")
    print("=" * 70)
    
    # 加载Polymarket数据
    pm_data, filename = load_latest_polymarket()
    if not pm_data:
        print("❌ 没有找到Polymarket数据")
        return
    
    print(f"\n📅 数据来源: {filename}")
    
    # 提取数据
    teams_data = pm_data.get("teams", [])
    # 支持新旧两种格式：yes_price(小数) 或 prob(百分比)
    teams_pm = {}
    for t in teams_data:
        team = t["team"]
        if "yes_price" in t:
            # yes_price是小数(如0.1715)，转为小数概率
            teams_pm[team] = t["yes_price"]
        elif "price" in t:
            teams_pm[team] = t["price"]
        elif "prob" in t:
            # prob是百分比(如17.15)，转为小数
            teams_pm[team] = t["prob"] / 100.0
    
    # 加载Elo
    elo_system = EloSystem()
    
    # 校准Elo
    calibrator = EloCalibrator(elo_system, pm_data)
    calibrator.calibrate(learning_rate=0.3)
    calibrator.apply_calibration()
    
    # 模拟夺冠概率
    elo_dict = elo_system.ratings.copy()
    sim_probs = simulate_champion_probs(elo_dict, monte_carlo=5000)
    
    # 整理数据
    analysis = []
    for team, pm_prob in teams_pm.items():
        elo = elo_dict.get(team, 1500)
        sim_prob = sim_probs.get(team, 0)
        
        # 计算偏差
        if pm_prob > 0:
            bias = (sim_prob / pm_prob - 1) * 100  # 正数=模型比市场更高估
        else:
            bias = 0
        
        analysis.append({
            "team": team,
            "elo": elo,
            "pm_prob": pm_prob,
            "sim_prob": sim_prob,
            "bias": bias,
        })
    
    # 按Polymarket概率排序
    analysis.sort(key=lambda x: x["pm_prob"], reverse=True)
    
    # 打印Top 20
    print(f"\n{'排名':>4} {'球队':<18} {'Elo':>8} {'市场概率':>10} {'模型模拟':>10} {'偏差':>8}")
    print("-" * 70)
    
    for i, item in enumerate(analysis[:20], 1):
        bias_str = f"+{item['bias']:.1f}%" if item['bias'] > 0 else f"{item['bias']:.1f}%"
        
        # 标记高估/低估
        if item['bias'] > 30:
            flag = "🔴"
        elif item['bias'] < -30:
            flag = "🟢"
        else:
            flag = "⚪"
        
        print(f"{i:>4} {item['team']:<18} {item['elo']:>8.0f} "
              f"{item['pm_prob']*100:>9.2f}% {item['sim_prob']*100:>9.2f}% "
              f"{flag}{bias_str:>8}")
    
    # 找出被高估和低估的球队
    print("\n" + "=" * 70)
    print("🔴 被市场高估的球队（模型不看好）:")
    print("-" * 70)
    
    overvalued = [x for x in analysis if x["bias"] < -30]
    overvalued.sort(key=lambda x: x["bias"])
    for item in overvalued[:5]:
        print(f"   {item['team']:<18} 市场={item['pm_prob']*100:>5.2f}%  模型={item['sim_prob']*100:>5.2f}%  偏差={item['bias']:.1f}%")
    
    print("\n🟢 被市场低估的球队（模型更看好）:")
    print("-" * 70)
    
    undervalued = [x for x in analysis if x["bias"] > 30]
    undervalued.sort(key=lambda x: x["bias"], reverse=True)
    for item in undervalued[:5]:
        print(f"   {item['team']:<18} 市场={item['pm_prob']*100:>5.2f}%  模型={item['sim_prob']*100:>5.2f}%  偏差={item['bias']:.1f}%")
    
    # 打印完整表格
    print("\n" + "=" * 70)
    print("📋 完整数据表（按市场概率排序）")
    print("=" * 70)
    
    print(f"\n{'球队':<18} {'Elo':>8} {'市场%':>8} {'模型%':>8} {'偏差':>8} {'评估':>6}")
    print("-" * 70)
    
    for item in analysis:
        bias = item["bias"]
        if bias > 50:
            assessment = "极度高估"
        elif bias > 20:
            assessment = "高估"
        elif bias < -50:
            assessment = "极度低估"
        elif bias < -20:
            assessment = "低估"
        else:
            assessment = "正常"
        
        bias_str = f"+{bias:.1f}%" if bias > 0 else f"{bias:.1f}%"
        print(f"{item['team']:<18} {item['elo']:>8.0f} "
              f"{item['pm_prob']*100:>7.2f}% {item['sim_prob']*100:>7.2f}% "
              f"{bias_str:>9} {assessment:>8}")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    analyze_market_vs_model()
