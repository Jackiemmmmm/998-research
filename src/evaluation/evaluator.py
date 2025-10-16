"""
Pattern Evaluator - Main evaluation engine
Runs test tasks on patterns and collects metrics
"""

import time
import asyncio
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

from .test_suite import TestTask, TEST_SUITE
from .judge import Judge, LLMJudge
from .metrics import (
    PatternMetrics,
    SuccessMetrics,
    EfficiencyMetrics,
    RobustnessMetrics,
    ControllabilityMetrics,
    MetricsAggregator,
)


@dataclass
class TaskResult:
    """Result of running a single task"""

    task_id: str
    task_category: str
    task_complexity: str
    pattern_name: str

    # Execution info
    success: bool = False
    output: str = ""
    error: Optional[str] = None

    # Timing
    start_time: float = 0.0
    end_time: float = 0.0
    latency: float = 0.0

    # Resource usage
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    step_count: int = 0
    tool_call_count: int = 0

    # Validation
    judge_success: bool = False  # Strict evaluation
    judge_message: str = ""
    lenient_judge_success: bool = False  # Lenient evaluation (with answer extraction)
    lenient_judge_message: str = ""
    schema_compliant: bool = True
    tool_policy_compliant: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "task_id": self.task_id,
            "pattern": self.pattern_name,
            "success": self.success,
            "judge_success": self.judge_success,
            "latency": round(self.latency, 3),
            "total_tokens": self.total_tokens,
            "step_count": self.step_count,
            "output": self.output[:200] + "..." if len(self.output) > 200 else self.output,
            "error": self.error,
            "judge_message": self.judge_message,
        }


class PatternEvaluator:
    """Main evaluator for agentic patterns"""

    def __init__(self, use_llm_judge: bool = False, delay_between_tasks: float = 2.0):
        """
        Initialize evaluator

        Args:
            use_llm_judge: Whether to use LLM-as-Judge for quality evaluation
            delay_between_tasks: Delay in seconds between tasks to avoid rate limits
        """
        self.use_llm_judge = use_llm_judge
        self.llm_judge = LLMJudge() if use_llm_judge else None
        self.results: List[TaskResult] = []
        self.delay_between_tasks = delay_between_tasks

    async def evaluate_pattern(
        self,
        pattern_name: str,
        graph,
        test_tasks: Optional[List[TestTask]] = None,
        include_robustness: bool = True,
    ) -> PatternMetrics:
        """
        Evaluate a single pattern on test suite

        Args:
            pattern_name: Name of the pattern (e.g., "ReAct", "CoT")
            graph: LangGraph compiled graph
            test_tasks: Test tasks to run (default: all tasks)
            include_robustness: Whether to run robustness tests

        Returns:
            PatternMetrics with all dimension scores
        """
        if test_tasks is None:
            test_tasks = TEST_SUITE

        print(f"\n{'='*60}")
        print(f"Evaluating Pattern: {pattern_name}")
        print(f"{'='*60}")
        print(f"Total tasks: {len(test_tasks)}")

        # Initialize metrics
        metrics = PatternMetrics(pattern_name=pattern_name)

        # Run original tasks
        print(f"\n[1/2] Running original tasks...")
        original_results = await self._run_tasks(
            pattern_name, graph, test_tasks, variant="original"
        )

        # Collect metrics from original results
        self._collect_success_metrics(metrics.success, original_results, test_tasks)
        self._collect_efficiency_metrics(metrics.efficiency, original_results)
        self._collect_controllability_metrics(metrics.controllability, original_results, test_tasks)

        # Calculate original success rate for robustness
        metrics.robustness.original_success_rate = metrics.success.success_rate()

        # Run robustness tests
        if include_robustness:
            print(f"\n[2/2] Running robustness tests (perturbations)...")
            perturbed_results = await self._run_robustness_tests(
                pattern_name, graph, test_tasks
            )

            # Collect robustness metrics
            self._collect_robustness_metrics(
                metrics.robustness, original_results, perturbed_results
            )
        else:
            print(f"\n[2/2] Skipping robustness tests")

        print(f"\n{'='*60}")
        print(f"Evaluation Complete: {pattern_name}")
        print(f"{'='*60}")
        print(f"Success Rate (Strict): {metrics.success.success_rate():.1%}")
        print(f"Success Rate (Lenient): {metrics.success.lenient_success_rate():.1%}")
        print(f"Controllability Gap: {metrics.success.controllability_gap():.1%}")
        print(f"Avg Latency: {metrics.efficiency.avg_latency():.2f}s")
        print(f"Avg Tokens: {metrics.efficiency.avg_total_tokens():.0f}")
        print(f"Controllability: {metrics.controllability.overall_controllability():.1%}")

        return metrics

    async def _run_tasks(
        self,
        pattern_name: str,
        graph,
        tasks: List[TestTask],
        variant: str = "original",
    ) -> List[TaskResult]:
        """Run a list of tasks on a pattern"""
        results = []

        for i, task in enumerate(tasks, 1):
            prompt = task.prompt
            if variant == "perturbed" and task.get_perturbations():
                # Use first perturbation
                prompt = task.get_perturbations()[0]

            print(f"  [{i}/{len(tasks)}] Task {task.id}: {prompt[:50]}...")

            result = await self._run_single_task(pattern_name, graph, task, prompt)
            results.append(result)

            # Display strict evaluation result
            strict_status = "✓" if result.judge_success else "✗"
            print(f"           Strict:  {strict_status} {result.judge_message[:50]}")

            # If lenient result differs, show it as well
            if result.lenient_judge_success != result.judge_success:
                lenient_status = "✓" if result.lenient_judge_success else "✗"
                print(f"           Lenient: {lenient_status} {result.lenient_judge_message[:50]}")

            # Add delay between tasks to avoid rate limits
            if i < len(tasks) and self.delay_between_tasks > 0:
                await asyncio.sleep(self.delay_between_tasks)

        return results

    async def _run_single_task(
        self,
        pattern_name: str,
        graph,
        task: TestTask,
        prompt: str,
    ) -> TaskResult:
        """Run a single task and collect metrics"""
        result = TaskResult(
            task_id=task.id,
            task_category=task.category,
            task_complexity=task.complexity,
            pattern_name=pattern_name,
        )

        try:
            # Execute task
            start_time = time.time()

            # Invoke graph with evaluation_mode enabled
            # This tells patterns (Reflex, ToT) to output clean results without decorative formatting
            response = await asyncio.to_thread(
                graph.invoke,
                {
                    "messages": [{"role": "user", "content": prompt}],
                    "evaluation_mode": True  # Clean output for evaluation
                }
            )

            end_time = time.time()

            # Extract output
            result.start_time = start_time
            result.end_time = end_time
            result.latency = end_time - start_time

            # Parse response
            if isinstance(response, dict):
                messages = response.get("values", {}).get("messages", response.get("messages", []))
                if messages:
                    last_message = messages[-1]
                    if hasattr(last_message, "content"):
                        result.output = last_message.content
                    elif isinstance(last_message, dict):
                        result.output = last_message.get("content", "")
                else:
                    result.output = str(response.get("values", {}).get("output", ""))
            else:
                result.output = str(response)

            result.success = True

            # Count steps (approximate from message length)
            if isinstance(response, dict) and "values" in response:
                messages = response["values"].get("messages", [])
                result.step_count = len(messages)

            # Estimate tokens (rough approximation: 1 token ≈ 4 chars)
            result.input_tokens = len(prompt) // 4
            result.output_tokens = len(result.output) // 4
            result.total_tokens = result.input_tokens + result.output_tokens

            # Judge output - Strict evaluation (exact match)
            judge_success, judge_msg = Judge.evaluate(
                result.output,
                task.ground_truth,
                task.judge,
                task.schema,
                lenient=False  # Strict mode
            )

            result.judge_success = judge_success
            result.judge_message = judge_msg

            # Judge output - Lenient evaluation (with answer extraction)
            lenient_judge_success, lenient_judge_msg = Judge.evaluate(
                result.output,
                task.ground_truth,
                task.judge,
                task.schema,
                lenient=True  # Lenient mode with answer extraction
            )

            result.lenient_judge_success = lenient_judge_success
            result.lenient_judge_message = lenient_judge_msg

            # Check schema compliance
            if task.schema:
                result.schema_compliant = judge_success

        except Exception as e:
            result.success = False
            result.error = str(e)
            result.judge_success = False
            result.judge_message = f"Execution error: {str(e)[:100]}"

        return result

    async def _run_robustness_tests(
        self,
        pattern_name: str,
        graph,
        tasks: List[TestTask],
    ) -> List[TaskResult]:
        """Run robustness tests with perturbations"""
        perturbed_tasks = []

        # Collect tasks with perturbations
        for task in tasks:
            if task.get_perturbations():
                perturbed_tasks.append(task)

        if not perturbed_tasks:
            return []

        return await self._run_tasks(
            pattern_name, graph, perturbed_tasks, variant="perturbed"
        )

    def _collect_success_metrics(
        self,
        success_metrics: SuccessMetrics,
        results: List[TaskResult],
        tasks: List[TestTask],
    ):
        """Collect success dimension metrics (both strict and lenient)"""
        success_metrics.total_tasks = len(results)
        success_metrics.successful_tasks = sum(1 for r in results if r.judge_success)
        success_metrics.lenient_successful_tasks = sum(1 for r in results if r.lenient_judge_success)
        success_metrics.failed_tasks = sum(1 for r in results if not r.judge_success)

        # By category
        categories = set(task.category for task in tasks)
        for category in categories:
            cat_results = [r for r in results if r.task_category == category]
            if cat_results:
                success_rate = sum(1 for r in cat_results if r.judge_success) / len(cat_results)
                success_metrics.success_by_category[category] = success_rate

        # By complexity
        complexities = set(task.complexity for task in tasks)
        for complexity in complexities:
            comp_results = [r for r in results if r.task_complexity == complexity]
            if comp_results:
                success_rate = sum(1 for r in comp_results if r.judge_success) / len(comp_results)
                success_metrics.success_by_complexity[complexity] = success_rate

    def _collect_efficiency_metrics(
        self,
        efficiency_metrics: EfficiencyMetrics,
        results: List[TaskResult],
    ):
        """Collect efficiency dimension metrics"""
        for result in results:
            if result.success:
                efficiency_metrics.latencies.append(result.latency)
                efficiency_metrics.input_tokens.append(result.input_tokens)
                efficiency_metrics.output_tokens.append(result.output_tokens)
                efficiency_metrics.step_counts.append(result.step_count)
                efficiency_metrics.tool_call_counts.append(result.tool_call_count)

    def _collect_robustness_metrics(
        self,
        robustness_metrics: RobustnessMetrics,
        original_results: List[TaskResult],
        perturbed_results: List[TaskResult],
    ):
        """Collect robustness dimension metrics"""
        if not perturbed_results:
            return

        # Calculate perturbed success rate
        perturbed_success = sum(1 for r in perturbed_results if r.judge_success)
        robustness_metrics.perturbed_success_rate = perturbed_success / len(perturbed_results)

        # Calculate degradation
        robustness_metrics.calculate_degradation()

        # Per-task robustness
        task_pairs = {}
        for orig in original_results:
            task_pairs[orig.task_id] = {"original": orig}

        for pert in perturbed_results:
            if pert.task_id in task_pairs:
                task_pairs[pert.task_id]["perturbed"] = pert

        for task_id, pair in task_pairs.items():
            if "original" in pair and "perturbed" in pair:
                orig = pair["original"]
                pert = pair["perturbed"]

                # Robustness score: 1.0 if both succeed, 0.5 if only original succeeds, 0.0 otherwise
                if orig.judge_success and pert.judge_success:
                    score = 1.0
                elif orig.judge_success and not pert.judge_success:
                    score = 0.5
                else:
                    score = 0.0

                robustness_metrics.task_robustness_scores[task_id] = score

    def _collect_controllability_metrics(
        self,
        controllability_metrics: ControllabilityMetrics,
        results: List[TaskResult],
        tasks: List[TestTask],
    ):
        """Collect controllability dimension metrics"""
        # Schema compliance
        json_tasks = [t for t in tasks if t.schema is not None]
        controllability_metrics.total_json_tasks = len(json_tasks)

        for result in results:
            task = next((t for t in tasks if t.id == result.task_id), None)
            if task and task.schema:
                if result.schema_compliant:
                    controllability_metrics.schema_compliant_tasks += 1

        # Tool policy compliance (simplified - would need actual tool tracking)
        tool_tasks = [t for t in tasks if t.plan is not None]
        controllability_metrics.total_tool_tasks = len(tool_tasks)
        # Assume compliant unless we detect violations (would need instrumentation)
        controllability_metrics.tool_policy_compliant_tasks = len(tool_tasks)

        # Format compliance
        successful_results = [r for r in results if r.success]
        if successful_results:
            controllability_metrics.format_compliance_rate = (
                sum(1 for r in successful_results if r.judge_success) / len(successful_results)
            )


async def evaluate_multiple_patterns(
    patterns: Dict[str, Any],
    test_tasks: Optional[List[TestTask]] = None,
    include_robustness: bool = True,
    delay_between_tasks: float = 3.0,
) -> Dict[str, PatternMetrics]:
    """
    Evaluate multiple patterns and compare

    Args:
        patterns: Dict of {pattern_name: graph}
        test_tasks: Test tasks to run (default: all)
        include_robustness: Whether to run robustness tests
        delay_between_tasks: Delay in seconds between tasks (default: 3.0)

    Returns:
        Dict of {pattern_name: PatternMetrics}
    """
    evaluator = PatternEvaluator(delay_between_tasks=delay_between_tasks)
    results = {}

    for pattern_name, graph in patterns.items():
        metrics = await evaluator.evaluate_pattern(
            pattern_name, graph, test_tasks, include_robustness
        )
        results[pattern_name] = metrics

    # Print comparison
    print(f"\n\n{'='*60}")
    print("PATTERN COMPARISON")
    print(f"{'='*60}")

    comparison = MetricsAggregator.compare_patterns(results)

    print("\nSuccess Dimension:")
    print(f"  Best: {comparison['success_dimension']['best_pattern']} "
          f"({comparison['success_dimension']['best_score']:.1%})")

    print("\nEfficiency Dimension:")
    print(f"  Fastest: {comparison['efficiency_dimension']['fastest_pattern']} "
          f"({comparison['efficiency_dimension']['fastest_latency']:.2f}s)")

    if include_robustness:
        print("\nRobustness Dimension:")
        print(f"  Most Robust: {comparison['robustness_dimension']['most_robust_pattern']} "
              f"({comparison['robustness_dimension']['lowest_degradation']:.1f}% degradation)")

    print("\nControllability Dimension:")
    print(f"  Most Controllable: {comparison['controllability_dimension']['most_controllable_pattern']} "
          f"({comparison['controllability_dimension']['best_score']:.1%})")

    return results
