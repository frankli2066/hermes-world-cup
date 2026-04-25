#!/usr/bin/env python3
"""
球队数据管理器 v1.0
====================
统一管理48支球队的完整信息

功能：
1. 加载球队基础数据（Elo、风格、地理位置等）
2. 提供球队信息查询接口
3. 支持球队数据导出给预测引擎
"""

import os
import json
from typing import Dict, List, Optional

# ============ 路径配置 ============
BASE_DIR = os.path.expanduser("~/hermes-world-cup/")
DATA_DIR = os.path.join(BASE_DIR, "data/")


class TeamDataManager:
    """
    球队数据管理器

    统一管理48支球队的完整信息
    """

    def __init__(self):
        self.data_file = os.path.join(DATA_DIR, "teams", "teams_48.json")
        self.teams_data = self._load_data()

    def _load_data(self) -> Dict:
        """加载球队数据"""
        if os.path.exists(self.data_file):
            with open(self.data_file, 'r') as f:
                return json.load(f)
        return {}

    def get_team(self, team_name: str) -> Optional[Dict]:
        """获取球队完整信息"""
        teams = self.teams_data.get("teams", {})
        # 模糊匹配
        for name, data in teams.items():
            if name.lower() == team_name.lower():
                return data
            if team_name.lower() in name.lower():
                return data
        return None

    def get_elo(self, team_name: str) -> int:
        """获取球队Elo评分"""
        team = self.get_team(team_name)
        if team:
            return team.get("elo", 1800)  # 默认1800
        return 1800

    def get_style(self, team_name: str) -> str:
        """获取球队风格"""
        team = self.get_team(team_name)
        if team:
            return team.get("style", "balanced")
        return "balanced"

    def get_all_elos(self) -> Dict[str, int]:
        """获取所有球队的Elo评分"""
        elos = {}
        teams = self.teams_data.get("teams", {})
        for name, data in teams.items():
            elos[name] = data.get("elo", 1800)
        return elos

    def get_all_styles(self) -> Dict[str, str]:
        """获取所有球队的风格"""
        styles = {}
        teams = self.teams_data.get("teams", {})
        for name, data in teams.items():
            styles[name] = data.get("style", "balanced")
        return styles

    def get_teams_by_style(self, style: str) -> List[str]:
        """获取特定风格的所有球队"""
        teams = []
        for name, data in self.teams_data.get("teams", {}).items():
            if data.get("style") == style or data.get("secondary_style") == style:
                teams.append(name)
        return teams

    def get_teams_by_region(self, region: str) -> List[str]:
        """获取特定地区的球队"""
        teams = []
        for name, data in self.teams_data.get("teams", {}).items():
            if data.get("region") == region:
                teams.append(name)
        return teams

    def get_top_teams(self, n: int = 10) -> List[Dict]:
        """获取排名前N的球队"""
        teams = self.teams_data.get("teams", {})
        sorted_teams = sorted(
            [(name, data) for name, data in teams.items()],
            key=lambda x: x[1].get("elo", 1800),
            reverse=True
        )
        result = []
        for name, data in sorted_teams[:n]:
            result.append({
                "name": name,
                "elo": data.get("elo", 1800),
                "style": data.get("style", "balanced"),
                "strength": self.get_team_strength(name),
                "region": data.get("region", "Unknown")
            })
        return result

    def get_team_strength(self, team_name: str) -> str:
        """获取球队实力等级"""
        elo = self.get_elo(team_name)
        if elo >= 2000:
            return "顶级强队"
        elif elo >= 1900:
            return "强队"
        elif elo >= 1850:
            return "中上"
        elif elo >= 1800:
            return "中等"
        elif elo >= 1750:
            return "中下"
        else:
            return "弱旅"

    def search_teams(self, keyword: str) -> List[str]:
        """搜索球队"""
        keyword = keyword.lower()
        results = []
        for name in self.teams_data.get("teams", {}).keys():
            if keyword in name.lower():
                results.append(name)
        return results

    def get_matchup_info(self, home: str, away: str) -> Dict:
        """获取对阵信息"""
        home_team = self.get_team(home)
        away_team = self.get_team(away)

        if not home_team or not away_team:
            return {"error": "球队未找到"}

        return {
            "home": {
                "name": home,
                "elo": home_team.get("elo", 1800),
                "style": home_team.get("style", "balanced"),
                "region": home_team.get("region", "Unknown"),
                "strength": self.get_team_strength(home),
                "play_style": home_team.get("play_style_desc", "")
            },
            "away": {
                "name": away,
                "elo": away_team.get("elo", 1800),
                "style": away_team.get("style", "balanced"),
                "region": away_team.get("region", "Unknown"),
                "strength": self.get_team_strength(away),
                "play_style": away_team.get("play_style_desc", "")
            },
            "elo_diff": home_team.get("elo", 1800) - away_team.get("elo", 1800),
            "style_matchup": f"{home_team.get('style', 'balanced')} vs {away_team.get('style', 'balanced')}"
        }

    def export_for_predictor(self) -> Dict:
        """导出预测引擎需要的数据格式"""
        teams = self.teams_data.get("teams", {})

        return {
            "elo_ratings": {name: data.get("elo", 1800) for name, data in teams.items()},
            "styles": {name: data.get("style", "balanced") for name, data in teams.items()},
            "regions": {name: data.get("region", "Unknown") for name, data in teams.items()},
            "home_advantage_boost": {name: data.get("home_advantage_boost", 1.0) for name, data in teams.items()}
        }

    def save_to_file(self, filepath: str = None):
        """保存数据到文件"""
        if filepath is None:
            filepath = self.data_file

        with open(filepath, 'w') as f:
            json.dump(self.teams_data, f, ensure_ascii=False, indent=2)

        print(f"✅ 球队数据已保存: {filepath}")

    def get_stats(self) -> Dict:
        """获取数据统计"""
        teams = self.teams_data.get("teams", {})

        styles_count = {}
        regions_count = {}
        elo_sum = 0

        for name, data in teams.items():
            style = data.get("style", "unknown")
            styles_count[style] = styles_count.get(style, 0) + 1

            region = data.get("region", "unknown")
            regions_count[region] = regions_count.get(region, 0) + 1

            elo_sum += data.get("elo", 1800)

        return {
            "total_teams": len(teams),
            "styles_distribution": styles_count,
            "regions_distribution": regions_count,
            "average_elo": elo_sum / len(teams) if teams else 0,
            "elo_range": {
                "max": max((d.get("elo", 1800) for d in teams.values()), default=0),
                "min": min((d.get("elo", 1800) for d in teams.values()), default=0)
            }
        }


# ============ 测试 ============
if __name__ == "__main__":
    manager = TeamDataManager()

    print("=" * 60)
    print("📊 48支球队数据管理器")
    print("=" * 60)

    # 统计信息
    stats = manager.get_stats()
    print(f"\n总计: {stats['total_teams']} 支球队")
    print(f"平均Elo: {stats['average_elo']:.0f}")
    print(f"Elo范围: {stats['elo_range']['min']} - {stats['elo_range']['max']}")

    print("\n风格分布:")
    for style, count in stats["styles_distribution"].items():
        print(f"  {style}: {count}队")

    print("\n地区分布:")
    for region, count in stats["regions_distribution"].items():
        print(f"  {region}: {count}队")

    # Top 10
    print("\n🏆 Top 10 球队:")
    top_teams = manager.get_top_teams(10)
    for i, team in enumerate(top_teams, 1):
        print(f"  {i}. {team['name']}: Elo {team['elo']} ({team['strength']})")

    # 对阵信息测试
    print("\n📍 对阵信息测试: 阿根廷 vs 巴西")
    info = manager.get_matchup_info("Argentina", "Brazil")
    if "error" not in info:
        print(f"  Elo差距: {info['elo_diff']}")
        print(f"  风格对阵: {info['style_matchup']}")
        print(f"  主队描述: {info['home']['play_style']}")
        print(f"  客队描述: {info['away']['play_style']}")

    # 导出给预测引擎
    print("\n📤 导出数据给预测引擎...")
    predictor_data = manager.export_for_predictor()
    print(f"  Elo球队数: {len(predictor_data['elo_ratings'])}")
    print(f"  风格球队数: {len(predictor_data['styles'])}")
