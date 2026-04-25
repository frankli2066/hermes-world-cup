#!/usr/bin/env python3
"""
多博彩网站赔率获取模块 v1.0
===========================
从多个博彩网站获取赔率数据，综合分析

支持的博彩网站：
1. OddsJam - 综合赔率比较
2. Bet365 - 主流博彩
3. Pinnacle - 专业投注
4. 1xBet - 新兴博彩
5. Betway - 主流博彩

功能：
1. 从各网站获取赔率
2. 计算市场共识概率
3. 检测赔率异常
4. 识别价值投注机会
"""

import os
import json
import math
import random
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass

# ============ 路径配置 ============
BASE_DIR = os.path.expanduser("~/hermes-world-cup/")
DATA_DIR = os.path.join(BASE_DIR, "data/")


@dataclass
class BookmakerOdds:
    """单个博彩网站的赔率数据"""
    bookmaker: str
    home_odds: float
    draw_odds: float
    away_odds: float
    timestamp: str
    url: str = ""

    def to_implied_prob(self) -> Dict[str, float]:
        """转换为隐含概率"""
        try:
            home_prob = 1 / self.home_odds if self.home_odds > 0 else 0.33
            draw_prob = 1 / self.draw_odds if self.draw_odds > 0 else 0.33
            away_prob = 1 / self.away_odds if self.away_odds > 0 else 0.33
            
            total = home_prob + draw_prob + away_prob
            if total > 0:
                return {
                    "home": home_prob / total,
                    "draw": draw_prob / total,
                    "away": away_prob / total
                }
        except:
            pass
        return {"home": 0.33, "draw": 0.34, "away": 0.33}


class MultiBookmakerOdds:
    """
    多博彩网站赔率获取器
    
    从多个博彩网站获取赔率，计算市场共识
    """

    # 博彩网站列表
    BOOKMAKERS = {
        "oddsjam": {
            "name": "OddsJam",
            "weight": 0.25,  # 综合比较网站，权重较高
            "description": "赔率比较平台"
        },
        "bet365": {
            "name": "Bet365",
            "weight": 0.20,
            "description": "全球最大博彩公司"
        },
        "pinnacle": {
            "name": "Pinnacle",
            "weight": 0.20,
            "description": "专业投注公司，受高手青睐"
        },
        "1xbet": {
            "name": "1xBet",
            "weight": 0.15,
            "description": "新兴博彩，用户众多"
        },
        "betway": {
            "name": "Betway",
            "weight": 0.10,
            "description": "主流博彩公司"
        },
        "unibet": {
            "name": "Unibet",
            "weight": 0.10,
            "description": "欧洲知名博彩"
        }
    }

    def __init__(self):
        self.data_file = os.path.join(DATA_DIR, "multi_bookmaker_odds.json")
        self.odds_history = self._load_data()
        self.last_fetch = None

    def _load_data(self) -> Dict:
        """加载历史数据"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {"matches": []}

    def _save_data(self):
        """保存数据"""
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
        with open(self.data_file, 'w') as f:
            json.dump(self.odds_history, f, ensure_ascii=False, indent=2)

    def get_consensus_probabilities(self, 
                                    home_team: str, 
                                    away_team: str) -> Dict[str, float]:
        """
        计算市场共识概率（加权平均）
        
        Returns:
            市场共识概率 {"home": 0.45, "draw": 0.25, "away": 0.30}
        """
        odds_list = self.get_all_odds(home_team, away_team)
        
        if not odds_list:
            return {"home": 0.40, "draw": 0.30, "away": 0.30}
        
        total_weight = 0
        weighted_home = 0
        weighted_draw = 0
        weighted_away = 0
        
        for odds_data in odds_list:
            bookmaker = odds_data["bookmaker"]
            weight = self.BOOKMAKERS.get(bookmaker, {}).get("weight", 0.1)
            
            implied = odds_data["implied_prob"]
            
            weighted_home += implied["home"] * weight
            weighted_draw += implied["draw"] * weight
            weighted_away += implied["away"] * weight
            total_weight += weight
        
        if total_weight > 0:
            # 归一化
            total = weighted_home + weighted_draw + weighted_away
            return {
                "home": weighted_home / total,
                "draw": weighted_draw / total,
                "away": weighted_away / total
            }
        
        return {"home": 0.40, "draw": 0.30, "away": 0.30}

    def get_all_odds(self, home_team: str, away_team: str) -> List[Dict]:
        """获取所有博彩公司的赔率"""
        results = []
        
        for bookmaker_id, info in self.BOOKMAKERS.items():
            odds = self._fetch_single_bookmaker(bookmaker_id, home_team, away_team)
            if odds:
                implied = odds.to_implied_prob()
                results.append({
                    "bookmaker": bookmaker_id,
                    "name": info["name"],
                    "odds": {
                        "home": odds.home_odds,
                        "draw": odds.draw_odds,
                        "away": odds.away_odds
                    },
                    "implied_prob": implied,
                    "weight": info["weight"],
                    "timestamp": odds.timestamp
                })
        
        return results

    def _fetch_single_bookmaker(self, 
                                bookmaker_id: str, 
                                home_team: str, 
                                away_team: str) -> Optional[BookmakerOdds]:
        """
        从单个博彩网站获取赔率（模拟实现）
        
        实际使用时应该调用真实的API
        """
        # 检查缓存
        cached = self._get_cached_odds(bookmaker_id, home_team, away_team)
        if cached:
            return cached
        
        # 模拟赔率数据（实际应该从API获取）
        odds = self._simulate_odds(bookmaker_id, home_team, away_team)
        
        # 缓存
        self._cache_odds(bookmaker_id, home_team, away_team, odds)
        
        return odds

    def _simulate_odds(self, bookmaker_id: str, home_team: str, away_team: str) -> BookmakerOdds:
        """
        模拟赔率数据
        
        实际使用时应该替换为真实的API调用
        不同博彩公司有不同的赔率（vig/抽水不同）
        """
        import random
        
        # 基础概率（简化模拟）
        base_home = 0.45 + random.uniform(-0.15, 0.15)
        base_away = 0.30 + random.uniform(-0.10, 0.10)
        base_draw = max(0.20, 1 - base_home - base_away)
        
        # 归一化
        total = base_home + base_draw + base_away
        base_home /= total
        base_draw /= total
        base_away /= total
        
        # 不同博彩公司的抽水不同
        vig_map = {
            "oddsjam": 0.03,   # 低抽水
            "bet365": 0.05,    # 中等抽水
            "pinnacle": 0.02,  # 极低抽水（专业投注公司）
            "1xbet": 0.06,     # 较高抽水
            "betway": 0.05,    # 中等抽水
            "unibet": 0.05     # 中等抽水
        }
        
        vig = vig_map.get(bookmaker_id, 0.05)
        
        # 计算赔率
        home_odds = 1 / (base_home + vig * random.uniform(0.8, 1.2))
        draw_odds = 1 / (base_draw + vig * random.uniform(0.8, 1.2))
        away_odds = 1 / (base_away + vig * random.uniform(0.8, 1.2))
        
        return BookmakerOdds(
            bookmaker=bookmaker_id,
            home_odds=round(home_odds, 2),
            draw_odds=round(draw_odds, 2),
            away_odds=round(away_odds, 2),
            timestamp=datetime.now().isoformat()
        )

    def _get_cached_odds(self, bookmaker_id: str, home_team: str, away_team: str) -> Optional[BookmakerOdds]:
        """获取缓存的赔率"""
        matches = self.odds_history.get("matches", [])
        
        for match in matches:
            if (match.get("home_team") == home_team and 
                match.get("away_team") == away_team):
                
                bookmaker_data = match.get("bookmakers", {}).get(bookmaker_id)
                if bookmaker_data:
                    # 检查是否过期（1小时）
                    timestamp = datetime.fromisoformat(bookmaker_data["timestamp"])
                    if (datetime.now() - timestamp).seconds < 3600:
                        return BookmakerOdds(
                            bookmaker=bookmaker_id,
                            home_odds=bookmaker_data["home_odds"],
                            draw_odds=bookmaker_data["draw_odds"],
                            away_odds=bookmaker_data["away_odds"],
                            timestamp=bookmaker_data["timestamp"]
                        )
        
        return None

    def _cache_odds(self, bookmaker_id: str, home_team: str, away_team: str, odds: BookmakerOdds):
        """缓存赔率数据"""
        matches = self.odds_history.get("matches", [])
        
        # 查找现有记录
        for match in matches:
            if match.get("home_team") == home_team and match.get("away_team") == away_team:
                match["bookmakers"][bookmaker_id] = {
                    "home_odds": odds.home_odds,
                    "draw_odds": odds.draw_odds,
                    "away_odds": odds.away_odds,
                    "timestamp": odds.timestamp
                }
                match["last_update"] = datetime.now().isoformat()
                self._save_data()
                return
        
        # 新记录
        matches.append({
            "home_team": home_team,
            "away_team": away_team,
            "bookmakers": {
                bookmaker_id: {
                    "home_odds": odds.home_odds,
                    "draw_odds": odds.draw_odds,
                    "away_odds": odds.away_odds,
                    "timestamp": odds.timestamp
                }
            },
            "last_update": datetime.now().isoformat()
        })
        
        # 只保留最近100条
        if len(matches) > 100:
            matches = matches[-100:]
        
        self.odds_history["matches"] = matches
        self._save_data()

    def find_value_opportunities(self, 
                                  home_team: str, 
                                  away_team: str, 
                                  model_prediction: Dict[str, float],
                                  min_edge: float = 0.03) -> List[Dict]:
        """
        找出价值投注机会
        
        Args:
            model_prediction: 模型预测 {"home": 0.45, "draw": 0.25, "away": 0.30}
            min_edge: 最小优势阈值
        
        Returns:
            价值投注机会列表
        """
        market_prob = self.get_consensus_probabilities(home_team, away_team)
        
        opportunities = []
        
        for outcome in ["home", "draw", "away"]:
            model_prob = model_prediction.get(outcome, 0.33)
            market_prob_val = market_prob.get(outcome, 0.33)
            
            edge = model_prob - market_prob_val
            
            if abs(edge) >= min_edge:
                opportunities.append({
                    "outcome": outcome,
                    "model_prob": model_prob,
                    "market_prob": market_prob_val,
                    "edge": edge,
                    "edge_pct": edge * 100,
                    "type": "overvalued" if edge > 0 else "undervalued",
                    "recommendation": f"{outcome.upper()}被{'高估' if edge > 0 else '低估'}，优势{edge:.1%}"
                })
        
        # 按edge排序
        opportunities.sort(key=lambda x: -abs(x["edge"]))
        
        return opportunities

    def get_odds_anomaly_detection(self, 
                                   home_team: str, 
                                   away_team: str) -> Dict:
        """
        赔率异常检测
        
        检测各博彩公司之间的赔率差异是否异常
        """
        odds_list = self.get_all_odds(home_team, away_team)
        
        if len(odds_list) < 2:
            return {"status": "insufficient_data"}
        
        # 计算各博彩公司的赔率差距
        anomalies = []
        
        for i, odds1 in enumerate(odds_list):
            for odds2 in odds_list[i+1:]:
                home_diff = abs(odds1["odds"]["home"] - odds2["odds"]["home"])
                away_diff = abs(odds1["odds"]["away"] - odds2["odds"]["away"])
                
                # 如果差距超过10%，标记为异常
                if home_diff > 0.15 or away_diff > 0.15:
                    anomalies.append({
                        "bookmaker1": odds1["name"],
                        "bookmaker2": odds2["name"],
                        "home_diff": home_diff,
                        "away_diff": away_diff,
                        "severity": "high" if home_diff > 0.25 or away_diff > 0.25 else "medium"
                    })
        
        return {
            "has_anomalies": len(anomalies) > 0,
            "anomaly_count": len(anomalies),
            "anomalies": anomalies,
            "recommendation": "检测到赔率异常" if anomalies else "赔率一致，无明显异常"
        }

    def get_closing_line_value(self, 
                                home_team: str, 
                                away_team: str,
                                opening_odds: Dict[str, float],
                                closing_odds: Dict[str, float]) -> Dict:
        """
        计算收盘线价值（Closing Line Value）
        
        这是衡量专业投注者水平的重要指标
        """
        def odds_to_prob(odds: Dict) -> Dict:
            try:
                home = 1 / odds.get("home", 2.0)
                draw = 1 / odds.get("draw", 3.2)
                away = 1 / odds.get("away", 3.8)
                total = home + draw + away
                return {
                    "home": home / total,
                    "draw": draw / total,
                    "away": away / total
                }
            except:
                return {"home": 0.33, "draw": 0.34, "away": 0.33}
        
        open_prob = odds_to_prob(opening_odds)
        close_prob = odds_to_prob(closing_odds)
        
        # 计算收盘概率变化
        home_clv = close_prob["home"] - open_prob["home"]
        away_clv = close_prob["away"] - open_prob["away"]
        
        return {
            "home_clv": home_clv,
            "away_clv": away_clv,
            "home_assessment": "资金涌入" if home_clv > 0.02 else "资金流出" if home_clv < -0.02 else "稳定",
            "away_assessment": "资金涌入" if away_clv > 0.02 else "资金流出" if away_clv < -0.02 else "稳定",
            "is_sharp_move": abs(home_clv) > 0.05 or abs(away_clv) > 0.05
        }

    def get_full_odds_report(self, 
                              home_team: str, 
                              away_team: str,
                              model_prediction: Dict[str, float] = None) -> Dict:
        """
        生成完整的赔率报告
        """
        odds_list = self.get_all_odds(home_team, away_team)
        consensus = self.get_consensus_probabilities(home_team, away_team)
        anomaly = self.get_odds_anomaly_detection(home_team, away_team)
        
        report = {
            "home_team": home_team,
            "away_team": away_team,
            "bookmakers": odds_list,
            "consensus_probabilities": consensus,
            "anomaly_detection": anomaly,
            "timestamp": datetime.now().isoformat()
        }
        
        # 如果有模型预测，添加价值分析
        if model_prediction:
            opportunities = self.find_value_opportunities(home_team, away_team, model_prediction)
            report["value_opportunities"] = opportunities
            report["has_value"] = len(opportunities) > 0
        
        return report


# ============ 便捷函数 ============
def get_consensus_odds(home: str, away: str) -> Dict[str, float]:
    """快速获取市场共识赔率"""
    tracker = MultiBookmakerOdds()
    return tracker.get_consensus_probabilities(home, away)


def get_all_bookmaker_odds(home: str, away: str) -> List[Dict]:
    """快速获取所有博彩公司赔率"""
    tracker = MultiBookmakerOdds()
    return tracker.get_all_odds(home, away)


def find_betting_value(home: str, 
                        away: str, 
                        model_pred: Dict[str, float],
                        min_edge: float = 0.03) -> List[Dict]:
    """快速找出价值投注"""
    tracker = MultiBookmakerOdds()
    return tracker.find_value_opportunities(home, away, model_pred, min_edge)


# ============ 测试 ============
if __name__ == "__main__":
    tracker = MultiBookmakerOdds()
    
    print("=" * 60)
    print("多博彩网站赔率获取测试")
    print("=" * 60)
    
    # 测试：获取德国 vs 日本的赔率
    print("\n📍 测试：德国 vs 日本")
    report = tracker.get_full_odds_report("Germany", "Japan", {
        "home": 0.45,
        "draw": 0.25,
        "away": 0.30
    })
    
    print(f"\n🏆 德国 vs 日本 赔率报告")
    print(f"时间: {report['timestamp']}")
    
    # 各博彩公司赔率
    print(f"\n📊 各博彩公司赔率:")
    for bm in report["bookmakers"]:
        print(f"  {bm['name']}: 主{bm['odds']['home']:.2f} 平{bm['odds']['draw']:.2f} 客{bm['odds']['away']:.2f}")
    
    # 市场共识
    consensus = report["consensus_probabilities"]
    print(f"\n🎯 市场共识概率:")
    print(f"  主队(德国): {consensus['home']:.1%}")
    print(f"  平局: {consensus['draw']:.1%}")
    print(f"  客队(日本): {consensus['away']:.1%}")
    
    # 异常检测
    anomaly = report["anomaly_detection"]
    print(f"\n⚠️ 异常检测:")
    print(f"  状态: {anomaly.get('recommendation', 'N/A')}")
    if anomaly.get("anomalies"):
        for a in anomaly["anomalies"]:
            print(f"  - {a['bookmaker1']} vs {a['bookmaker2']}: {a['severity']}")
    
    # 价值机会
    if report.get("value_opportunities"):
        print(f"\n💰 价值投注机会:")
        for opp in report["value_opportunities"]:
            print(f"  - {opp['recommendation']} (优势: {opp['edge_pct']:.1f}%)")
    else:
        print(f"\n💰 无明显价值投注机会")
    
    # 赔率比较
    print("\n📈 博彩公司对比:")
    if len(report["bookmakers"]) >= 2:
        odds_1 = report["bookmakers"][0]
        odds_2 = report["bookmakers"][1]
        print(f"  {odds_1['name']}主队赔率: {odds_1['odds']['home']:.2f}")
        print(f"  {odds_2['name']}主队赔率: {odds_2['odds']['home']:.2f}")
        diff = abs(odds_1['odds']['home'] - odds_2['odds']['home'])
        print(f"  差异: {diff:.2f}")
    
    print("\n" + "=" * 60)
    print("✅ 测试完成")
    print("=" * 60)
