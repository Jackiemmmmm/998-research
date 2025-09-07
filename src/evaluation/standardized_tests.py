"""
标准化测试框架 - 使用相同测试查询对比三种设计模式
确保公平对比，控制变量一致性
"""

import time
import json
import asyncio
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

# 标准化测试查询集合 - 按复杂度分类
STANDARDIZED_TEST_QUERIES = {
    "simple": [
        "What's today's date?",
        "Hello, how are you?",
        "What is 2+2?",
        "Tell me about Python programming language",
        "What's the weather like?",
    ],
    "medium": [
        "Compare Python and JavaScript for web development",
        "Explain the concept of machine learning and give examples",
        "Create a simple todo list application design",
        "What are the benefits and drawbacks of remote work?",
        "How does blockchain technology work?",
    ],
    "complex": [
        "Design a scalable microservices architecture for an e-commerce platform with authentication, payments, and real-time notifications",
        "Create a comprehensive business plan for a sustainable energy startup including market analysis, financial projections, and risk assessment",
        "Develop a machine learning model deployment strategy considering data privacy, model versioning, and continuous monitoring",
        "Plan a complete digital transformation strategy for a traditional manufacturing company",
        "Design a disaster recovery plan for a multinational corporation's IT infrastructure",
    ],
}


@dataclass
class TestResult:
    """单个测试结果"""

    pattern: str
    query: str
    complexity: str
    start_time: float
    end_time: float
    latency: float
    response_length: int
    success: bool
    error_message: Optional[str] = None
    steps_count: int = 0
    decision_points: int = 0
    tool_calls: int = 0


@dataclass
class PatternPerformance:
    """模式性能统计"""

    pattern: str
    total_tests: int
    success_rate: float
    avg_latency: float
    min_latency: float
    max_latency: float
    avg_response_length: float
    total_steps: int
    total_decisions: int
    total_tool_calls: int

    def score(self) -> float:
        """计算综合评分 - 重新调整权重，更重视质量"""
        # 成功率权重35% (必须能完成任务)
        success_score = self.success_rate * 35

        # 响应质量权重35% (质量最重要!)
        # 使用更合理的质量评分：基于响应长度，但设置合理区间
        if self.avg_response_length < 500:
            quality_score = (
                self.avg_response_length / 500
            ) * 20  # 500字符以下按比例给分
        elif self.avg_response_length < 2000:
            quality_score = (
                20 + ((self.avg_response_length - 500) / 1500) * 10
            )  # 500-2000字符，20-30分
        else:
            quality_score = 30 + min(
                5, (self.avg_response_length - 2000) / 1000
            )  # 2000字符以上，最高35分

        # 延迟评分权重20% (降低延迟权重)
        # 使用更宽松的延迟基准：15秒为基准
        if self.avg_latency <= 5:
            latency_score = 20  # 5秒以内满分
        elif self.avg_latency <= 15:
            latency_score = 20 - ((self.avg_latency - 5) / 10) * 15  # 5-15秒线性递减
        else:
            latency_score = max(
                0, 5 - (self.avg_latency - 15) * 0.5
            )  # 15秒以上快速递减

        # 功能完整性权重10% (工具使用、步骤完整性)
        functionality_score = min(10, (self.total_tool_calls + self.total_steps) * 0.5)

        total_score = (
            success_score + quality_score + latency_score + functionality_score
        )

        return round(total_score, 2)


class StandardizedTester:
    """标准化测试器"""

    def __init__(self):
        self.results: List[TestResult] = []

    async def test_pattern(
        self, pattern_name: str, pattern_graph, query: str, complexity: str
    ) -> TestResult:
        """测试单个模式"""
        start_time = time.time()
        success = True
        error_message = None
        response_length = 0
        steps_count = 0
        decision_points = 0
        tool_calls = 0

        try:
            # 执行测试
            response = pattern_graph.invoke(
                {"messages": [{"role": "user", "content": query}]}
            )

            end_time = time.time()

            # 分析响应
            if "messages" in response:
                last_message = response["messages"][-1]
                response_length = (
                    len(str(last_message.content))
                    if hasattr(last_message, "content")
                    else len(str(last_message))
                )

                # 计算工具调用次数
                for msg in response["messages"]:
                    if hasattr(msg, "tool_calls") and msg.tool_calls:
                        tool_calls += len(msg.tool_calls)

            # 分析特定模式的指标
            if pattern_name == "Sequential":
                # 统计阶段数
                stage_markers = ["Planning Stage", "Execution Stage", "Review Stage"]
                for msg in response.get("messages", []):
                    content = str(msg.content if hasattr(msg, "content") else msg)
                    steps_count += sum(
                        1 for marker in stage_markers if marker in content
                    )

            elif pattern_name == "State-based":
                # 统计决策点
                if "decision_history" in response:
                    decision_points = len(response["decision_history"])
                else:
                    # 通过响应内容估算决策点
                    decision_markers = ["Analysis:", "Processing:", "Validation:"]
                    for msg in response.get("messages", []):
                        content = str(msg.content if hasattr(msg, "content") else msg)
                        decision_points += sum(
                            1 for marker in decision_markers if marker in content
                        )

        except Exception as e:
            end_time = time.time()
            success = False
            error_message = str(e)

        return TestResult(
            pattern=pattern_name,
            query=query,
            complexity=complexity,
            start_time=start_time,
            end_time=end_time,
            latency=end_time - start_time,
            response_length=response_length,
            success=success,
            error_message=error_message,
            steps_count=steps_count,
            decision_points=decision_points,
            tool_calls=tool_calls,
        )

    async def run_comprehensive_test(
        self, patterns: Dict[str, Any], queries_per_complexity: int = 2
    ) -> Dict[str, Any]:
        """运行全面的对比测试"""
        print("🧪 开始标准化性能测试...")
        print("=" * 50)

        # 清空之前的结果
        self.results = []

        # 对每个复杂度级别进行测试
        for complexity, queries in STANDARDIZED_TEST_QUERIES.items():
            print(f"\n📊 测试复杂度: {complexity.upper()}")

            # 限制每个复杂度的查询数量
            test_queries = queries[:queries_per_complexity]

            for query in test_queries:
                print(f"\n📝 查询: {query[:50]}{'...' if len(query) > 50 else ''}")

                # 对每个模式测试相同的查询
                for pattern_name, pattern_graph in patterns.items():
                    print(f"   🔄 测试 {pattern_name}...", end=" ")

                    try:
                        result = await self.test_pattern(
                            pattern_name, pattern_graph, query, complexity
                        )
                        self.results.append(result)

                        if result.success:
                            print(f"✅ {result.latency:.2f}s")
                        else:
                            print(f"❌ 失败: {result.error_message}")

                    except Exception as e:
                        print(f"❌ 错误: {e}")

        return self.generate_comparison_report()

    def generate_comparison_report(self) -> Dict[str, Any]:
        """生成对比报告"""
        if not self.results:
            return {"error": "No test results available"}

        # 按模式分组统计
        pattern_stats = {}

        for pattern in set(result.pattern for result in self.results):
            pattern_results = [r for r in self.results if r.pattern == pattern]

            if pattern_results:
                successful_results = [r for r in pattern_results if r.success]

                pattern_stats[pattern] = PatternPerformance(
                    pattern=pattern,
                    total_tests=len(pattern_results),
                    success_rate=len(successful_results) / len(pattern_results),
                    avg_latency=(
                        sum(r.latency for r in successful_results)
                        / len(successful_results)
                        if successful_results
                        else 0
                    ),
                    min_latency=(
                        min(r.latency for r in successful_results)
                        if successful_results
                        else 0
                    ),
                    max_latency=(
                        max(r.latency for r in successful_results)
                        if successful_results
                        else 0
                    ),
                    avg_response_length=(
                        sum(r.response_length for r in successful_results)
                        / len(successful_results)
                        if successful_results
                        else 0
                    ),
                    total_steps=sum(r.steps_count for r in pattern_results),
                    total_decisions=sum(r.decision_points for r in pattern_results),
                    total_tool_calls=sum(r.tool_calls for r in pattern_results),
                )

        # 生成排名
        ranking = sorted(
            pattern_stats.items(), key=lambda x: x[1].score(), reverse=True
        )

        # 按复杂度分析
        complexity_analysis = {}
        for complexity in ["simple", "medium", "complex"]:
            complexity_results = [r for r in self.results if r.complexity == complexity]
            if complexity_results:
                complexity_analysis[complexity] = {
                    "avg_latency_by_pattern": {
                        pattern: sum(
                            r.latency
                            for r in complexity_results
                            if r.pattern == pattern and r.success
                        )
                        / len(
                            [
                                r
                                for r in complexity_results
                                if r.pattern == pattern and r.success
                            ]
                        )
                        for pattern in set(r.pattern for r in complexity_results)
                        if len(
                            [
                                r
                                for r in complexity_results
                                if r.pattern == pattern and r.success
                            ]
                        )
                        > 0
                    }
                }

        return {
            "timestamp": datetime.now().isoformat(),
            "total_tests": len(self.results),
            "pattern_performance": {
                name: asdict(stats) for name, stats in pattern_stats.items()
            },
            "ranking": [
                {"pattern": name, "score": stats.score()} for name, stats in ranking
            ],
            "complexity_analysis": complexity_analysis,
            "raw_results": [asdict(result) for result in self.results],
            "summary": self._generate_summary(pattern_stats, ranking),
        }

    def _generate_summary(
        self, pattern_stats: Dict[str, PatternPerformance], ranking: List
    ) -> Dict[str, str]:
        """生成测试总结"""
        if not ranking:
            return {"error": "No ranking data available"}

        best_pattern = ranking[0][0]

        return {
            "overall_winner": f"{best_pattern} (综合评分: {ranking[0][1]}分)",
            "fastest_pattern": min(
                pattern_stats.items(), key=lambda x: x[1].avg_latency
            )[0],
            "most_reliable": max(
                pattern_stats.items(), key=lambda x: x[1].success_rate
            )[0],
            "most_detailed": max(
                pattern_stats.items(), key=lambda x: x[1].avg_response_length
            )[0],
            "recommendations": {
                "simple_tasks": "ReAct - 适合快速响应的简单查询",
                "medium_tasks": "Sequential - 适合需要系统化处理的中等复杂任务",
                # "complex_tasks": "State-based - 适合需要智能决策的复杂任务",
            },
        }

    def print_detailed_report(self):
        """打印详细报告"""
        report = self.generate_comparison_report()

        print("\n" + "=" * 60)
        print("📊 标准化性能对比报告")
        print("=" * 60)

        # 总体排名
        print(f"\n🏆 综合排名:")
        for i, item in enumerate(report["ranking"], 1):
            print(f"{i}. {item['pattern']}: {item['score']:.1f}分")

        # 详细性能指标
        print(f"\n📈 详细性能指标:")
        for pattern, stats in report["pattern_performance"].items():
            print(f"\n{pattern}:")
            print(f"  ✅ 成功率: {stats['success_rate']:.1%}")
            print(f"  ⏱️  平均延迟: {stats['avg_latency']:.2f}s")
            print(f"  📏 平均响应长度: {stats['avg_response_length']:.0f} 字符")
            print(f"  🔧 总工具调用: {stats['total_tool_calls']} 次")

        # 复杂度分析
        print(f"\n🎯 按复杂度对比:")
        for complexity, analysis in report["complexity_analysis"].items():
            print(f"\n{complexity.upper()}:")
            for pattern, latency in analysis["avg_latency_by_pattern"].items():
                print(f"  {pattern}: {latency:.2f}s")

        # 使用建议
        print(f"\n💡 使用建议:")
        for task_type, recommendation in report["summary"]["recommendations"].items():
            print(f"  {task_type}: {recommendation}")

    def save_report(self, filename: str = None):
        """保存报告到文件"""
        report = self.generate_comparison_report()

        if filename is None:
            filename = f"standardized_test_report_{int(time.time())}.json"

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"📄 报告已保存至: {filename}")
        return filename


# 便利函数：快速测试
async def quick_comparison_test():
    """快速对比测试 - 仅用于演示"""
    from src.agent.pattern_react import graph_pattern_react
    from src.agent.pattern_sequential import graph_pattern_sequential

    # from src.agent.pattern_stateful import graph_pattern_stateful

    patterns = {
        "ReAct": graph_pattern_react,
        "Sequential": graph_pattern_sequential,
        # "State-based": graph_pattern_stateful
    }

    tester = StandardizedTester()
    await tester.run_comprehensive_test(patterns, queries_per_complexity=1)
    tester.print_detailed_report()
    return tester.save_report()


if __name__ == "__main__":
    # 演示用法
    print("标准化测试框架已准备就绪")
    print("使用示例:")
    print(
        "  python -c 'import asyncio; from src.evaluation.standardized_tests import quick_comparison_test; asyncio.run(quick_comparison_test())'"
    )
