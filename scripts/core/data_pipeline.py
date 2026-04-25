#!/usr/bin/env python3
"""
实时数据管道模块
从多个数据源自动采集球队数据
- Polymarket赔率
- FIFA排名
- 球队近期战绩
- 球员伤病信息
"""

import json
import os
import time
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional

# ============ 路径配置 ============
BASE_DIR = os.path.expanduser("~/hermes-world-cup/")
DATA_DIR = os.path.join(BASE_DIR, "data/")
os.makedirs(DATA_DIR, exist_ok=True)

PIPELINE_CACHE = os.path.join(DATA_DIR, "pipeline_cache.json")


class DataPipeline:
    """
    实时数据管道

    数据源优先级：
    1. Polymarket API（赔率/概率）
    2. 配置文件（本地缓存）
    3. 默认值（兜底）
    """

    def __init__(self, use_cache: bool = True):
        self.cache = self._load_cache() if use_cache else {}
        self.use_cache = use_cache
        self.cache_ttl = 6 * 3600  # 6小时缓存

    def _load_cache(self) -> dict:
        if os.path.exists(PIPELINE_CACHE):
            with open(PIPELINE_CACHE) as f:
                return json.load(f)
        return {}

    def _save_cache(self):
        with open(PIPELINE_CACHE, "w") as f:
            json.dump(self.cache, f, indent=2)

    def _is_cache_valid(self, key: str) -> bool:
        if key not in self.cache:
            return False
        timestamp = self.cache[key].get("timestamp", 0)
        return (time.time() - timestamp) < self.cache_ttl

    def _get_cached(self, key: str) -> Optional[dict]:
        if self._is_cache_valid(key):
            return self.cache[key].get("data")
        return None

    def _set_cached(self, key: str, data: dict):
        self.cache[key] = {
            "data": data,
            "timestamp": time.time(),
        }
        if self.use_cache:
            self._save_cache()

    # ============ Polymarket 数据 ============

    def fetch_polymarket_champion_odds(self) -> dict:
        """
        获取Polymarket世界杯冠军赔率

        优先级：
        1. 内存缓存（6小时TTL）
        2. 已保存的最新polymarket文件
        3. Polymarket API
        """
        cache_key = "polymarket_champion"
        cached = self._get_cached(cache_key)
        if cached:
            print("📦 使用内存缓存: Polymarket冠军赔率")
            return cached

        # 尝试读取已保存的最新文件
        saved_data = self._load_saved_polymarket()
        if saved_data:
            print("📦 使用已保存文件: Polymarket冠军赔率")
            self._set_cached(cache_key, saved_data)
            return saved_data

        print("🌐 获取 Polymarket 冠军赔率...")
        try:
            url = "https://gamma-api.polymarket.com/public-search?q=2026%20FIFA%20World%20Cup%20Winner"
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            # 解析数据
            events = data.get("events", [])
            winner_event = next((e for e in events if e.get("id") == "30615"), None)

            if not winner_event:
                print("⚠️ 未找到冠军市场，使用缓存或默认值")
                return self._get_cached(cache_key) or self._default_polymarket()

            markets = winner_event.get("markets", [])
            teams = []

            for m in markets:
                title = m.get("groupItemTitle", "")
                prices_raw = m.get("outcomePrices")
                active = m.get("active", False)
                closed = m.get("closed", False)

                if prices_raw:
                    try:
                        if isinstance(prices_raw, str):
                            prices = json.loads(prices_raw)
                        else:
                            prices = prices_raw
                        if len(prices) >= 2 and active and not closed:
                            yes_price = float(prices[0])
                            if 0 < yes_price < 1:
                                teams.append({
                                    "team": title,
                                    "yes_price": yes_price,
                                    "prob": round(yes_price * 100, 2),
                                    "volume": float(m.get("volume", 0)),
                                    "liquidity": float(m.get("liquidity", 0)),
                                    "one_day_change": m.get("oneDayPriceChange"),
                                    "one_week_change": m.get("oneWeekPriceChange"),
                                    "one_month_change": m.get("oneMonthPriceChange"),
                                })
                    except (json.JSONDecodeError, ValueError, TypeError):
                        continue

            teams.sort(key=lambda x: x["yes_price"], reverse=True)

            result = {
                "timestamp": datetime.now().isoformat(),
                "market": {
                    "title": winner_event.get("title", "").strip(),
                    "total_volume": sum(t["volume"] for t in teams),
                },
                "teams": teams[:20],
            }

            # 保存到文件
            self._save_polymarket(result)

            self._set_cached(cache_key, result)
            print(f"✅ 获取到 {len(teams)} 支球队赔率")
            return result

        except Exception as e:
            print(f"❌ Polymarket API 失败: {e}")
            return self._get_cached(cache_key) or self._default_polymarket()

    def _load_saved_polymarket(self) -> Optional[dict]:
        """从polymarket目录读取最新保存的数据"""
        import glob
        polymarket_dir = os.path.join(BASE_DIR, "polymarket/")
        if not os.path.exists(polymarket_dir):
            return None

        files = glob.glob(os.path.join(polymarket_dir, "*-champion-odds.json"))
        if not files:
            return None

        latest = max(files, key=os.path.getmtime)
        try:
            with open(latest) as f:
                data = json.load(f)
                # 验证数据完整性
                if "teams" in data and "market" in data:
                    # 检查是否在6小时内
                    timestamp = data.get("timestamp", "")
                    if timestamp:
                        try:
                            file_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                            age_hours = (datetime.now() - file_time.replace(tzinfo=None)).total_seconds() / 3600
                            if age_hours < 6:
                                return data
                        except:
                            pass
        except Exception:
            pass
        return None

    def _save_polymarket(self, data: dict):
        """保存Polymarket数据到文件"""
        import glob
        polymarket_dir = os.path.join(BASE_DIR, "polymarket/")
        os.makedirs(polymarket_dir, exist_ok=True)

        # 清理旧文件（只保留最近10个）
        files = sorted(glob.glob(os.path.join(polymarket_dir, "*-champion-odds.json")),
                      key=os.path.getmtime, reverse=True)
        for old_file in files[10:]:
            try:
                os.remove(old_file)
            except:
                pass

        # 保存新文件
        timestamp = datetime.now().strftime("%Y-%m-%d-%H")
        save_path = os.path.join(polymarket_dir, f"{timestamp}-champion-odds.json")
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _default_polymarket(self) -> dict:
        """默认Polymarket数据（兜底）"""
        return {
            "timestamp": datetime.now().isoformat(),
            "market": {
                "title": "2026 FIFA World Cup Winner",
                "total_volume": 600000000,
            },
            "teams": [
                {"team": "Spain", "yes_price": 0.174, "prob": 17.4, "volume": 12500000},
                {"team": "France", "yes_price": 0.161, "prob": 16.1, "volume": 11000000},
                {"team": "England", "yes_price": 0.112, "prob": 11.2, "volume": 8500000},
                {"team": "Argentina", "yes_price": 0.089, "prob": 8.9, "volume": 7200000},
                {"team": "Brazil", "yes_price": 0.087, "prob": 8.7, "volume": 6800000},
                {"team": "Portugal", "yes_price": 0.069, "prob": 6.9, "volume": 5500000},
                {"team": "Germany", "yes_price": 0.053, "prob": 5.3, "volume": 4200000},
                {"team": "Netherlands", "yes_price": 0.032, "prob": 3.2, "volume": 2800000},
                {"team": "Italy", "yes_price": 0.025, "prob": 2.5, "volume": 2100000},
                {"team": "Belgium", "yes_price": 0.019, "prob": 1.9, "volume": 1800000},
            ]
        }

    # ============ FIFA排名数据 ============

    def fetch_fifa_rankings(self) -> dict:
        """
        获取FIFA排名

        注：FIFA官方API需要认证，这里使用模拟数据
        实际使用时可接入 RapidAPI 等第三方FIFA数据
        """
        cache_key = "fifa_rankings"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        print("🌐 获取 FIFA排名（使用缓存数据）...")

        # 基于2026预选赛的模拟排名
        rankings = {
            "Spain": 1, "France": 2, "Brazil": 3, "Argentina": 4,
            "England": 5, "Germany": 6, "Portugal": 7, "Netherlands": 8,
            "Italy": 9, "Belgium": 10, "Croatia": 11, "Uruguay": 12,
            "Morocco": 13, "USA": 14, "Mexico": 15, "Colombia": 16,
            "Japan": 17, "Senegal": 18, "Poland": 19, "Switzerland": 20,
            "Chile": 21, "Austria": 22, "Ukraine": 23, "Australia": 24,
            "Serbia": 25, "Egypt": 26, "Paraguay": 27, "Nigeria": 28,
            "Ecuador": 29, "Ivory Coast": 30, "Algeria": 31, "Ghana": 32,
            "Qatar": 33, "Iraq": 34, "Jordan": 35, "Panama": 36,
            "Saudi Arabia": 37, "Cameroon": 38, "Tunisia": 39, "Bosnia": 40,
            "Scotland": 41, "Iran": 42, "Norway": 43, "New Zealand": 44,
            "Uzbekistan": 45, "South Africa": 46, "South Korea": 47,
            "Canada": 48, "Turkey": 49, "Hungary": 50, "Denmark": 22,
        }

        result = {
            "timestamp": datetime.now().isoformat(),
            "source": "simulated_fifa_2026",
            "rankings": rankings,
        }

        self._set_cached(cache_key, result)
        return result

    # ============ 球队近期战绩 ============

    def fetch_team_recent_form(self, team: str) -> dict:
        """
        获取球队近期战绩

        实际应用中应接入 FBref 或 Transfermarkt API
        这里使用模拟数据
        """
        cache_key = f"form_{team}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        print(f"🌐 获取 {team} 近期战绩...")

        # 模拟数据
        result = {
            "team": team,
            "timestamp": datetime.now().isoformat(),
            "matches": [
                {"date": "2026-03-25", "opponent": "TBD", "gf": 2, "ga": 1, "result": "W", "competition": "Friendly"},
                {"date": "2026-03-20", "opponent": "TBD", "gf": 1, "ga": 1, "result": "D", "competition": "Friendly"},
            ]
        }

        self._set_cached(cache_key, result)
        return result

    # ============ 伤病信息 ============

    def fetch_injuries(self, team: str) -> List[str]:
        """
        获取球队伤病名单

        返回关键球员列表
        """
        cache_key = f"injuries_{team}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        # 模拟伤病数据
        injuries_db = {
            "France": ["Camavinga"],
            "England": ["Kane"],  # 假设
            "Germany": [],
            "Spain": [],
            "Brazil": ["Neymar"],
            "Argentina": ["Di Maria"],
            "Portugal": ["Pepe"],
            "Netherlands": ["de Ligt"],
            "Belgium": ["De Bruyne"],  # 假设
            "Italy": [],
        }

        injuries = injuries_db.get(team, [])
        self._set_cached(cache_key, injuries)
        return injuries

    # ============ 天气数据 ============

    def fetch_weather(self, city: str = "Los Angeles") -> dict:
        """
        获取比赛地天气

        使用免费天气API（Open-Meteo）
        """
        cache_key = f"weather_{city}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        print(f"🌐 获取 {city} 天气...")

        try:
            # 洛杉矶坐标
            coords = {
                "Los Angeles": (34.05, -118.24),
                "Mexico City": (19.43, -99.13),
                "New York": (40.71, -74.01),
                "Miami": (25.76, -80.19),
                "Dallas": (32.78, -96.80),
            }

            if city not in coords:
                city = "Los Angeles"

            lat, lon = coords[city]
            url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"

            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            cw = data.get("current_weather", {})
            result = {
                "city": city,
                "timestamp": datetime.now().isoformat(),
                "temperature": cw.get("temperature", 25),
                "windspeed": cw.get("windspeed", 10),
                "weathercode": cw.get("weathercode", 0),
                "description": self._weather_code_to_desc(cw.get("weathercode", 0)),
            }

        except Exception as e:
            print(f"⚠️ 天气API失败: {e}")
            result = {
                "city": city,
                "timestamp": datetime.now().isoformat(),
                "temperature": 25,
                "windspeed": 10,
                "weathercode": 0,
                "description": "Clear",
            }

        self._set_cached(cache_key, result)
        return result

    def _weather_code_to_desc(self, code: int) -> str:
        """天气代码转描述"""
        codes = {
            0: "Clear", 1: "Mainly Clear", 2: "Partly Cloudy", 3: "Overcast",
            45: "Fog", 48: "Rime Fog",
            51: "Light Drizzle", 53: "Moderate Drizzle", 55: "Dense Drizzle",
            61: "Light Rain", 63: "Moderate Rain", 65: "Heavy Rain",
            71: "Light Snow", 73: "Moderate Snow", 75: "Heavy Snow",
            80: "Rain Showers", 81: "Moderate Showers", 82: "Violent Showers",
        }
        return codes.get(code, "Unknown")

    # ============ 综合数据获取 ============

    def fetch_all_team_data(self, team: str) -> dict:
        """获取球队所有相关数据"""
        return {
            "team": team,
            "timestamp": datetime.now().isoformat(),
            "polymarket": self._get_polymarket_for_team(team),
            "fifa_rank": self.fetch_fifa_rankings()["rankings"].get(team, 100),
            "recent_form": self.fetch_team_recent_form(team),
            "injuries": self.fetch_injuries(team),
        }

    def _get_polymarket_for_team(self, team: str) -> Optional[dict]:
        """从Polymarket数据中获取特定球队"""
        pm_data = self.fetch_polymarket_champion_odds()
        for t in pm_data.get("teams", []):
            if t["team"] == team:
                return t
        return None

    # ============ 数据导出 ============

    def export_team_stats_json(self, output_path: str = None):
        """导出球队统计数据为JSON"""
        if output_path is None:
            output_path = os.path.join(DATA_DIR, "team_stats.json")

        teams = [
            "France", "Spain", "Brazil", "Argentina", "England", "Germany",
            "Portugal", "Netherlands", "Italy", "Belgium", "Croatia", "Uruguay",
            "Morocco", "USA", "Mexico", "Colombia", "Japan", "Senegal", "Poland",
            "Switzerland", "Chile", "Austria", "Ukraine", "Australia", "Serbia",
        ]

        all_data = {}
        for team in teams:
            all_data[team] = self.fetch_all_team_data(team)

        with open(output_path, "w") as f:
            json.dump(all_data, f, indent=2, ensure_ascii=False)

        print(f"💾 球队数据已导出: {output_path}")
        return output_path


# ============ 数据验证 ============

class DataValidator:
    """数据验证器"""

    @staticmethod
    def validate_elo_rating(rating: float) -> bool:
        """验证Elo评分范围"""
        return 1000 <= rating <= 2200

    @staticmethod
    def validate_probability(prob: float) -> bool:
        """验证概率范围"""
        return 0 <= prob <= 1

    @staticmethod
    def validate_score(home_goals: int, away_goals: int) -> bool:
        """验证比分范围"""
        return 0 <= home_goals <= 15 and 0 <= away_goals <= 15

    @staticmethod
    def check_data_consistency(team_data: dict) -> List[str]:
        """检查数据一致性，返回问题列表"""
        issues = []

        elo = team_data.get("elo_rating", 1500)
        if not DataValidator.validate_elo_rating(elo):
            issues.append(f"Elo评分异常: {elo}")

        prob = team_data.get("polymarket_prob", 0)
        if not DataValidator.validate_probability(prob):
            issues.append(f"概率异常: {prob}")

        return issues


# ============ 主程序 ============

if __name__ == "__main__":
    print("=" * 60)
    print("📡 实时数据管道测试")
    print("=" * 60)

    pipeline = DataPipeline()

    # 测试Polymarket
    print("\n1. Polymarket冠军赔率:")
    pm_data = pipeline.fetch_polymarket_champion_odds()
    print(f"   市场: {pm_data['market']['title']}")
    print(f"   总成交量: ${pm_data['market']['total_volume']:,.0f}")
    print(f"   Top 5球队:")
    for t in pm_data["teams"][:5]:
        print(f"     {t['team']}: {t['prob']:.1f}%")

    # 测试FIFA排名
    print("\n2. FIFA排名:")
    fifa = pipeline.fetch_fifa_rankings()
    top5 = sorted(fifa["rankings"].items(), key=lambda x: x[1])[:5]
    for team, rank in top5:
        print(f"     {rank}. {team}")

    # 测试天气
    print("\n3. 天气数据:")
    weather = pipeline.fetch_weather("Los Angeles")
    print(f"     {weather['city']}: {weather['temperature']}°C, {weather['description']}")

    # 导出数据
    print("\n4. 导出球队数据:")
    output = pipeline.export_team_stats_json()

    print("\n" + "=" * 60)
    print("✅ 数据管道测试完成")
