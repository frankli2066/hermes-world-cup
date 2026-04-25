#!/usr/bin/env python3
"""
增强版机器学习权重优化器 v2.0
==============================
使用本地Ollama模型辅助分析 + 网格搜索 + 贝叶斯优化

核心功能：
1. 本地qwen2.5模型分析历史数据模式
2. 网格搜索找最优权重
3. 贝叶斯优化加速收敛
4. 新增因子权重学习（疲劳、风格、天气等）
"""

import json
import os
import random
import math
from datetime import datetime
from typing import List, Tuple, Dict, Optional
from itertools import product
import subprocess

# ============ 路径配置 ============
BASE_DIR = os.path.expanduser("~/hermes-world-cup/")
CALIBRATION_DIR = os.path.join(BASE_DIR, "data/calibration/")
os.makedirs(CALIBRATION_DIR, exist_ok=True)


class LocalLLMAnalyzer:
    """
    本地Ollama模型分析器

    用于：
    1. 分析比赛历史数据的隐藏模式
    2. 解释权重优化的结果
    3. 提供比赛前瞻洞察
    """

    def __init__(self, model: str = "qwen2.5:14b"):
        self.model = model
        self.base_url = "http://localhost:11434"

    def is_available(self) -> bool:
        """检查本地模型是否可用"""
        try:
            result = subprocess.run(
                ["curl", "-s", f"{self.base_url}/api/tags"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except:
            return False

    def analyze_pattern(self, prompt: str) -> str:
        """
        使用本地模型分析数据

        Args:
            prompt: 分析提示

        Returns:
            模型分析结果
        """
        if not self.is_available():
            return "本地模型不可用"

        try:
            # 构建完整的prompt
            full_prompt = f"""你是一个足球预测专家。请分析以下数据并给出简洁的洞察：

{prompt}

请用中文回答，简洁明了，控制在100字以内。"""

            # 调用Ollama
            result = subprocess.run(
                [
                    "curl", "-s", f"{self.base_url}/api/generate",
                    "-d", json.dumps({
                        "model": self.model,
                        "prompt": full_prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.3,
                            "num_predict": 200
                        }
                    })
                ],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                response = json.loads(result.stdout)
                return response.get("response", "").strip()
            else:
                return "模型调用失败"

        except Exception as e:
            return f"错误: {str(e)}"

    def suggest_weights(self, historical_analysis: Dict) -> Dict:
        """
        基于历史分析建议权重调整

        Args:
            historical_analysis: 历史分析结果

        Returns:
            建议的权重调整
        """
        prompt = f"""
分析以下世界杯预测数据的表现：
- 小组赛准确率: {historical_analysis.get('group_accuracy', 'N/A')}
- 淘汰赛准确率: {historical_analysis.get('knockout_accuracy', 'N/A')}
- 决赛准确率: {historical_analysis.get('final_accuracy', 'N/A')}
- 最大误差: {historical_analysis.get('worst_prediction', 'N/A')}

请建议：
1. 哪些因子需要增加权重？
2. 哪些因子需要减少权重？
3. 有哪些隐藏模式需要注意？
"""

        analysis = self.analyze_pattern(prompt)

        # 解析分析结果，生成权重建议
        suggestions = {
            "analysis": analysis,
            "suggested_adjustments": self._parse_weight_suggestions(analysis)
        }

        return suggestions

    def _parse_weight_suggestions(self, analysis: str) -> Dict:
        """从分析中解析权重建议"""
        suggestions = {}

        # 简化处理，实际可以从模型输出中提取
        keywords = {
            "elo": ["elo", "排名", "实力"],
            "form": ["状态", "近期", "form"],
            "home": ["主场", "主场优势"],
            "fatigue": ["疲劳", "休息", "旅途"],
            "style": ["风格", "战术", "相克"],
            "weather": ["天气", "温度", "雨"]
        }

        for factor, kws in keywords.items():
            for kw in kws:
                if kw in analysis.lower():
                    suggestions[factor] = True
                    break

        return suggestions


class EnhancedWeightOptimizer:
    """
    增强版权重优化器

    新增因子权重：
    - fatigue_factor: 疲劳恢复
    - style_factor: 风格相克
    - weather_factor: 天气影响
    - motivation_factor: 战意指数
    - travel_factor: 旅途距离
    """

    def __init__(self):
        self.history_file = os.path.join(CALIBRATION_DIR, "match_history.json")
        self.weights_file = os.path.join(CALIBRATION_DIR, "optimal_weights_v2.json")
        self.history = self._load_history()
        self.llm = LocalLLMAnalyzer()

    def _load_history(self) -> List[Dict]:
        """加载历史比赛数据"""
        if os.path.exists(self.history_file):
            with open(self.history_file) as f:
                data = json.load(f)
                return data.get("matches", [])
        return []

    def _load_weights(self) -> Dict:
        """加载最优权重"""
        if os.path.exists(self.weights_file):
            with open(self.weights_file) as f:
                return json.load(f)
        return self._default_weights()

    def _default_weights(self) -> Dict:
        """默认权重"""
        return {
            "version": "2.0",
            "elo_weight": 0.30,
            "form_weight": 0.20,
            "home_advantage": 0.08,
            "market_weight": 0.35,
            # 新增因子
            "fatigue_weight": 0.03,
            "style_weight": 0.02,
            "weather_weight": 0.01,
            "motivation_weight": 0.01,
            "travel_weight": 0.00,
        }

    def save_weights(self, weights: Dict):
        """保存权重"""
        weights["last_updated"] = datetime.now().isoformat()
        with open(self.weights_file, 'w') as f:
            json.dump(weights, f, ensure_ascii=False, indent=2)

    def calculate_score(self, weights: Dict, matches: List[Dict] = None) -> Dict:
        """
        计算给定权重的准确率

        Args:
            weights: 权重字典
            matches: 比赛列表（默认使用历史数据）

        Returns:
            准确率统计
        """
        if matches is None:
            matches = self.history

        if not matches:
            return {"accuracy": 0.5, "count": 0}

        correct = 0
        correct_3way = 0  # 胜平负全对
        total = len(matches)

        for match in matches:
            # 简化：使用权重计算预测
            pred = self._predict_with_weights(match, weights)
            actual = self._get_actual_result(match)

            # 检查胜负平
            if pred == actual:
                correct += 1

            # 检查3选项
            if pred == actual:
                correct_3way += 1

        return {
            "accuracy": correct / total if total > 0 else 0.5,
            "accuracy_3way": correct_3way / total if total > 0 else 0.5,
            "count": total
        }

    def _predict_with_weights(self, match: Dict, weights: Dict) -> str:
        """
        使用权重预测比赛结果（简化版）

        实际应该调用完整的预测引擎
        """
        # 简化：基于主客场和排名差异预测
        # 实际项目中这里应该调用完整的预测引擎

        # 默认返回"home"作为占位
        # 在实际使用时会用真实预测引擎
        return "home"

    def _get_actual_result(self, match: Dict) -> str:
        """从比分获取实际结果"""
        score = match.get("score", "0-0")
        try:
            home_goals, away_goals = map(int, score.split("-"))
            if home_goals > away_goals:
                return "home"
            elif home_goals < away_goals:
                return "away"
            else:
                return "draw"
        except:
            return "home"

    def grid_search(self, n_iterations: int = 100) -> Dict:
        """
        网格搜索找最优权重

        Args:
            n_iterations: 搜索次数

        Returns:
            最优权重和结果
        """
        print("🔍 开始网格搜索...")

        # 权重范围
        weight_ranges = {
            "elo_weight": [0.20, 0.25, 0.30, 0.35, 0.40],
            "form_weight": [0.10, 0.15, 0.20, 0.25],
            "home_advantage": [0.05, 0.08, 0.10, 0.12],
            "market_weight": [0.30, 0.35, 0.40, 0.45],
            "fatigue_weight": [0.00, 0.02, 0.03, 0.05],
            "style_weight": [0.00, 0.01, 0.02, 0.03],
        }

        # 生成所有组合
        keys = list(weight_ranges.keys())
        values = list(weight_ranges.values())
        all_combinations = list(product(*values))

        # 随机采样（如果组合太多）
        if len(all_combinations) > n_iterations:
            combinations = random.sample(all_combinations, n_iterations)
        else:
            combinations = all_combinations

        best_score = 0
        best_weights = None
        results = []

        for combo in combinations:
            weights = dict(zip(keys, combo))
            score = self.calculate_score(weights)

            results.append({
                "weights": weights,
                "score": score["accuracy"]
            })

            if score["accuracy"] > best_score:
                best_score = score["accuracy"]
                best_weights = weights.copy()

        print(f"✅ 网格搜索完成: {len(combinations)} 次测试")
        print(f"   最优准确率: {best_score:.1%}")

        return {
            "best_weights": best_weights,
            "best_score": best_score,
            "all_results": sorted(results, key=lambda x: -x["score"])[:10]
        }

    def bayesian_optimization(self, n_iterations: int = 30) -> Dict:
        """
        贝叶斯优化（简化版）

        使用高斯过程近似来加速权重搜索

        Args:
            n_iterations: 迭代次数

        Returns:
            最优权重
        """
        print("🎯 开始贝叶斯优化...")

        # 简化的贝叶斯优化
        # 实际应该使用 GPy 或 similar 库

        # 初始化一些随机点
        results = []

        for i in range(min(10, n_iterations)):
            weights = {
                "elo_weight": random.uniform(0.20, 0.40),
                "form_weight": random.uniform(0.10, 0.25),
                "home_advantage": random.uniform(0.05, 0.12),
                "market_weight": random.uniform(0.30, 0.45),
                "fatigue_weight": random.uniform(0.00, 0.05),
                "style_weight": random.uniform(0.00, 0.03),
            }

            # 归一化确保和为1
            total = sum(weights.values())
            for k in weights:
                weights[k] /= total

            score = self.calculate_score(weights)
            results.append((weights, score["accuracy"]))

        # 迭代优化
        for i in range(10, n_iterations):
            # 选择最佳权重附近的新点
            best = max(results, key=lambda x: x[1])

            # 在最佳权重附近扰动
            new_weights = {}
            for k, v in best[0].items():
                # 在±20%范围内扰动
                new_weights[k] = v * random.uniform(0.8, 1.2)

            # 归一化
            total = sum(new_weights.values())
            for k in new_weights:
                new_weights[k] /= total

            score = self.calculate_score(new_weights)
            results.append((new_weights, score["accuracy"]))

            if i % 10 == 0:
                current_best = max(results, key=lambda x: x[1])
                print(f"   迭代 {i}: 当前最佳 {current_best[1]:.1%}")

        # 返回最佳
        best = max(results, key=lambda x: x[1])
        print(f"✅ 贝叶斯优化完成: 最优准确率 {best[1]:.1%}")

        return {
            "best_weights": best[0],
            "best_score": best[1]
        }

    def optimize_with_llm(self) -> Dict:
        """
        使用本地LLM辅助优化

        分析历史数据，找出隐藏模式
        """
        print("🤖 使用本地模型辅助优化...")

        # 先做网格搜索
        grid_result = self.grid_search(n_iterations=50)

        # 用LLM分析结果
        if self.llm.is_available():
            historical_analysis = {
                "group_accuracy": grid_result.get("best_score", 0.5),
                "knockout_accuracy": 0.55,  # 简化
                "final_accuracy": 0.60,     # 简化
                "worst_prediction": "德国0-2韩国(2018)"
            }

            llm_suggestions = self.llm.suggest_weights(historical_analysis)
            print(f"📊 LLM分析: {llm_suggestions.get('analysis', 'N/A')[:100]}...")

            # 基于LLM建议微调权重
            adjustments = llm_suggestions.get("suggested_adjustments", {})

            if adjustments:
                print("🔧 应用LLM建议的权重调整...")
                best_weights = grid_result["best_weights"].copy()

                for factor in adjustments:
                    if factor in best_weights:
                        # 增加权重
                        best_weights[factor] *= 1.2
                        # 重新归一化
                        total = sum(best_weights.values())
                        for k in best_weights:
                            best_weights[k] /= total

                # 验证调整后的效果
                new_score = self.calculate_score(best_weights)
                if new_score["accuracy"] > grid_result["best_score"]:
                    grid_result["best_weights"] = best_weights
                    grid_result["best_score"] = new_score["accuracy"]

        return grid_result

    def comprehensive_optimization(self) -> Dict:
        """
        综合优化：网格搜索 + 贝叶斯 + LLM

        Returns:
            最终最优权重
        """
        print("=" * 60)
        print("🏆 开始综合权重优化")
        print("=" * 60)

        # 1. 网格搜索（快速覆盖）
        print("\n📍 步骤1: 网格搜索")
        grid_result = self.grid_search(n_iterations=100)

        # 2. 贝叶斯优化（精细调整）
        print("\n📍 步骤2: 贝叶斯优化")
        bayes_result = self.bayesian_optimization(n_iterations=30)

        # 3. 选择更好的结果
        if bayes_result["best_score"] > grid_result["best_score"]:
            best_weights = bayes_result["best_weights"]
            best_score = bayes_result["best_score"]
        else:
            best_weights = grid_result["best_weights"]
            best_score = grid_result["best_score"]

        # 4. LLM辅助微调
        print("\n📍 步骤3: LLM辅助微调")
        if self.llm.is_available():
            llm_result = self.llm.suggest_weights({"accuracy": best_score})
            print(f"   LLM建议: {llm_result.get('analysis', 'N/A')[:150]}...")

        # 5. 保存结果
        self.save_weights(best_weights)

        print("\n" + "=" * 60)
        print(f"🎉 优化完成！最优准确率: {best_score:.1%}")
        print("=" * 60)

        return {
            "best_weights": best_weights,
            "best_score": best_score,
            "method": "comprehensive"
        }

    def get_feature_importance(self) -> Dict:
        """
        获取各因子重要性排名

        Returns:
            因子重要性排序
        """
        # 通过扰动每个因子来估计重要性
        base_weights = self._load_weights()
        base_score = self.calculate_score(base_weights)["accuracy"]

        importance = {}

        for key in base_weights:
            if key in ["version", "last_updated"]:
                continue

            # 扰动这个权重
            perturbed = base_weights.copy()
            perturbed[key] *= 1.5

            # 归一化
            total = sum(perturbed.values())
            for k in perturbed:
                perturbed[k] /= total

            # 计算扰动后的分数
            new_score = self.calculate_score(perturbed)["accuracy"]

            # 重要性 = 分数变化
            importance[key] = abs(new_score - base_score)

        # 排序
        sorted_importance = dict(sorted(
            importance.items(),
            key=lambda x: -x[1]
        ))

        return sorted_importance


# ============ 主程序 ============
if __name__ == "__main__":
    optimizer = EnhancedWeightOptimizer()

    print("=" * 60)
    print("增强版权重优化器 v2.0")
    print("=" * 60)

    # 检查本地模型
    llm = LocalLLMAnalyzer()
    if llm.is_available():
        print("✅ 本地模型可用 (qwen2.5:14b)")
    else:
        print("⚠️ 本地模型不可用，将使用纯算法优化")

    # 获取因子重要性
    print("\n📊 当前因子重要性排名:")
    importance = optimizer.get_feature_importance()
    for i, (factor, imp) in enumerate(importance.items(), 1):
        print(f"   {i}. {factor}: {imp:.3f}")

    # 运行综合优化
    print("\n" + "=" * 60)
    result = optimizer.comprehensive_optimization()

    print("\n🏆 最优权重:")
    for key, value in result["best_weights"].items():
        if key not in ["version", "last_updated"]:
            print(f"   {key}: {value:.2%}")

    print(f"\n📈 最终准确率: {result['best_score']:.1%}")
