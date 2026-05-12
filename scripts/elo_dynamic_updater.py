#!/usr/bin/env python3
"""
Elo动态更新脚本
根据比赛结果自动更新球队Elo评分

使用方法:
    python3 elo_dynamic_updater.py --date 2026-04-17
    python3 elo_dynamic_updater.py --latest  # 更新到昨天
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Optional

# 路径配置
BASE_DIR = os.path.expanduser("~/hermes-world-cup/")
ELO_FILE = os.path.join(BASE_DIR, "data/elo_ratings.json")
RESULTS_DIR = os.path.join(BASE_DIR, "match-results/")
UPDATES_LOG = os.path.join(BASE_DIR, "data/elo_updates.json")

sys.path.insert(0, os.path.join(BASE_DIR, "scripts"))
try:
    from core.team_stats import EloSystem
except ModuleNotFoundError:
    from team_stats import EloSystem


class EloDynamicUpdater:
    """
    Elo动态更新器
    
    功能:
    1. 从比赛结果自动更新Elo评分
    2. 记录Elo变化历史
    3. 根据比赛阶段调整K值
    """
    
    # K值配置（根据比赛阶段）
    K_VALUES = {
        "friendly": 15,      # 友谊赛
        "qualifier": 25,     # 资格赛
        "group": 30,         # 小组赛
        "round16": 35,       # 16强
        "quarter": 40,       # 8强
        "semi": 50,          # 半决赛
        "third_place": 30,    # 三四名
        "final": 60,         # 决赛
        "premier_league": 35,  # 英超
        "la_liga": 32,
        "serie_a": 30,
        "bundesliga": 28,
        "champions_league": 45,
    }
    
    def __init__(self):
        self.elo_system = EloSystem()
        self.updates_history = self._load_updates_history()
        
    def _load_updates_history(self) -> List[Dict]:
        """加载历史更新记录"""
        if os.path.exists(UPDATES_LOG):
            with open(UPDATES_LOG) as f:
                return json.load(f).get("updates", [])
        return []
    
    def _save_updates_history(self):
        """保存更新历史"""
        with open(UPDATES_LOG, "w") as f:
            json.dump({
                "updates": self.updates_history,
                "last_update": datetime.now().isoformat()
            }, f, indent=2, ensure_ascii=False)
    
    def get_k_value(self, stage: str) -> int:
        """获取K值"""
        return self.K_VALUES.get(stage, 30)
    
    def update_from_result(
        self, 
        home_team: str, 
        away_team: str, 
        home_score: int, 
        away_score: int,
        stage: str = "group",
        is_neutral: bool = False
    ) -> Optional[Dict]:
        """
        从比赛结果更新Elo
        
        Args:
            home_team: 主队
            away_team: 客队
            home_score: 主队进球
            away_score: 客队进球
            stage: 比赛阶段
            is_neutral: 是否中立场
            
        Returns:
            更新详情或None
        """
        # 获取更新前的Elo
        home_elo_before = self.elo_system.get_rating(home_team)
        away_elo_before = self.elo_system.get_rating(away_team)
        
        # 判断胜负
        is_draw = home_score == away_score
        is_home_win = home_score > away_score
        
        # 确定主客场（如果中立场则无主场优势）
        if is_neutral:
            is_home_winner = None
        elif is_home_win:
            is_home_winner = True
        elif is_draw:
            is_home_winner = None
        else:
            is_home_winner = False
        
        # 计算进球差
        goal_diff = abs(home_score - away_score)
        
        # 执行Elo更新
        try:
            if is_draw:
                self.elo_system.update(
                    winner=home_team,  # 随便传一个，draw会特殊处理
                    loser=away_team,
                    draw=True,
                    is_home_winner=is_home_winner,
                    stage=stage,
                    goal_diff=goal_diff
                )
            elif is_home_win:
                self.elo_system.update(
                    winner=home_team,
                    loser=away_team,
                    draw=False,
                    is_home_winner=True,
                    stage=stage,
                    goal_diff=goal_diff
                )
            else:
                self.elo_system.update(
                    winner=away_team,
                    loser=home_team,
                    draw=False,
                    is_home_winner=False,
                    stage=stage,
                    goal_diff=goal_diff
                )
        except Exception as e:
            print(f"  ⚠️ 更新失败: {e}")
            return None
        
        # 获取更新后的Elo
        home_elo_after = self.elo_system.get_rating(home_team)
        away_elo_after = self.elo_system.get_rating(away_team)
        
        # 记录更新
        update_record = {
            "timestamp": datetime.now().isoformat(),
            "match": f"{home_team} {home_score}-{away_score} {away_team}",
            "stage": stage,
            "elo_changes": {
                home_team: {
                    "before": home_elo_before,
                    "after": home_elo_after,
                    "change": round(home_elo_after - home_elo_before, 1)
                },
                away_team: {
                    "before": away_elo_before,
                    "after": away_elo_after,
                    "change": round(away_elo_after - away_elo_before, 1)
                }
            }
        }
        
        self.updates_history.append(update_record)
        self._save_updates_history()
        
        return update_record
    
    def update_from_results_file(self, date_str: str) -> List[Dict]:
        """
        从比赛结果文件更新Elo
        
        Args:
            date_str: 日期字符串 (YYYY-MM-DD)
        """
        results_file = os.path.join(RESULTS_DIR, f"results_{date_str}.json")
        
        if not os.path.exists(results_file):
            print(f"⚠️ 结果文件不存在: {results_file}")
            return []
        
        with open(results_file) as f:
            data = json.load(f)
        
        matches = data.get("matches", [])
        print(f"📊 找到 {len(matches)} 场比赛")
        
        updates = []
        for match in matches:
            result = self.update_from_result(
                home_team=match.get("home"),
                away_team=match.get("away"),
                home_score=match.get("home_score"),
                away_score=match.get("away_score"),
                stage=match.get("stage", "friendly"),
                is_neutral=match.get("neutral", False)
            )
            if result:
                updates.append(result)
        
        return updates
    
    def show_recent_updates(self, limit: int = 10):
        """显示最近的Elo变化（中文球队名）"""
        if not self.updates_history:
            print("📭 暂无Elo更新记录")
            return
        
        # 中文名映射
        try:
            sys.path.insert(0, os.path.join(BASE_DIR, "scripts"))
            from team_names import TEAM_NAMES as _TN
        except:
            _TN = {}
        
        def cn(name):
            return _TN.get(name, name)
        
        print(f"\n📈 最近 {limit} 次Elo变化:")
        print("-" * 70)
        
        for update in self.updates_history[-limit:]:
            match = update["match"]
            changes = update["elo_changes"]
            
            home_team = list(changes.keys())[0]
            away_team = list(changes.keys())[1]
            home_change = changes[home_team]["change"]
            away_change = changes[away_team]["change"]
            
            home_arrow = "📈" if home_change > 0 else "📉" if home_change < 0 else "➡️"
            away_arrow = "📈" if away_change > 0 else "📉" if away_change < 0 else "➡️"
            
            print(f"{cn(home_team)} vs {cn(away_team)}")
            print(f"  {cn(home_team)}: {home_arrow} {home_change:+.0f}")
            print(f"  {cn(away_team)}: {away_arrow} {away_change:+.0f}")
            print()


def main():
    parser = argparse.ArgumentParser(description="Elo动态更新工具")
    parser.add_argument("--date", type=str, help="日期 (YYYY-MM-DD)")
    parser.add_argument("--latest", action="store_true", help="更新到昨天")
    parser.add_argument("--show", action="store_true", help="显示最近更新")
    parser.add_argument("--limit", type=int, default=10, help="显示数量")
    
    args = parser.parse_args()
    
    updater = EloDynamicUpdater()
    
    if args.show:
        updater.show_recent_updates(args.limit)
        return
    
    if args.latest:
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        date_str = yesterday
    elif args.date:
        date_str = args.date
    else:
        print("请指定日期: --date 2026-04-17 或 --latest")
        return
    
    print(f"🔄 开始更新 {date_str} 的比赛结果...")
    updates = updater.update_from_results_file(date_str)
    
    if updates:
        print(f"\n✅ 成功更新 {len(updates)} 场比赛的Elo")
    else:
        print("\n⚠️ 没有找到需要更新的比赛")


if __name__ == "__main__":
    main()
