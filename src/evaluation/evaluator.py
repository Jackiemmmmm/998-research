"""Pattern Evaluator - Main evaluation engine.

Runs test tasks on patterns and collects metrics.
"""

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .judge import Judge, LLMJudge
from .metrics import (
    ControllabilityMetrics,
    EfficiencyMetrics,
    MetricsAggregator,
    PatternMetrics,
    RobustnessMetrics,
    SuccessMetrics,
)
from .trace import AgentTrace, TraceExtractor
from .test_suite import TEST_SUITE, TestTask
from .controllability import (
    compute_controllability_result,
    compute_resource_efficiency,
)
from .scoring import compute_all_scores, NormalizedDimensionScores, CompositeScore


@dataclass
class TaskResult:
    """Result of running a single task."""

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

    # Trace
    trace: Optional[AgentTrace] = None
    tokens_estimated: bool = False

    # Validation
    judge_success: bool = False  # Strict evaluation
    judge_message: str = ""
    lenient_judge_success: bool = False  # Lenient evaluation (with answer extraction)
    lenient_judge_message: str = ""
    schema_compliant: bool = True
    tool_policy_compliant: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "task_id": self.task_id,
            "pattern": self.pattern_name,
            "success": self.success,
            "judge_success": self.judge_success,
            "latency": round(self.latency, 3),
            "total_tokens": self.total_tokens,
            "step_count": self.step_count,
            "tool_call_count": self.tool_call_count,
            "output": self.output[:200] + "..." if len(self.output) > 200 else self.output,
            "error": self.error,
            "judge_message": self.judge_message,
            "tokens_estimated": self.tokens_estimated,
        }
        if self.trace:
            result["trace_summary"] = {
                "think_steps": self.trace.total_think_steps,
                "act_steps": self.trace.total_act_steps,
                "observe_steps": self.trace.total_observe_steps,
                "tao_cycles": self.trace.tao_cycles,
                "total_tool_calls": self.trace.total_tool_calls,
            }
        return result


class PatternEvaluator:
    """Main evaluator for agentic patterns."""

    # Default timeout per task in seconds (3 minutes)
    DEFAULT_TASK_TIMEOUT = 180

    def __init__(self, use_llm_judge: bool = False, delay_between_tasks: float = 2.0, task_timeout: float = DEFAULT_TASK_TIMEOUT):
        """Initialize evaluator.

        Args:
            use_llm_judge: Whether to use LLM-as-Judge for quality evaluation
            delay_between_tasks: Delay in seconds between tasks to avoid rate limits
            task_timeout: Timeout in seconds per task (default: 180s / 3 minutes)
        """
        self.use_llm_judge = use_llm_judge
        self.llm_judge = LLMJudge() if use_llm_judge else None
        self.results: List[TaskResult] = []
        self.delay_between_tasks = delay_between_tasks
        self.task_timeout = task_timeout

    async def evaluate_pattern(
        self,
        pattern_name: str,
        graph,
        test_tasks: Optional[List[TestTask]] = None,
        include_robustness: bool = True,
    ) -> PatternMetrics:
        """Evaluate a single pattern on test suite.

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


        # Initialize metrics
        metrics = PatternMetrics(pattern_name=pattern_name)

        # Run original tasks
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
            perturbed_results = await self._run_robustness_tests(
                pattern_name, graph, test_tasks
            )

            # Collect robustness metrics
            self._collect_robustness_metrics(
                metrics.robustness, original_results, perturbed_results
            )
        else:
            pass


        # Phase D2: Pre-compute controllability data (without resource_efficiency,
        # which requires cross-pattern normalisation done in evaluate_multiple_patterns)
        from .controllability import compute_trace_completeness, compute_policy_violations
        traces = [r.trace for r in original_results if r.trace is not None and r.success]
        avg_tc, total_tao, total_steps = compute_trace_completeness(traces)
        flag_rate, total_violations, tasks_with_v = compute_policy_violations(
            original_results, test_tasks
        )
        from .controllability import ControllabilityResult
        metrics._controllability_result_data = ControllabilityResult(
            pattern_name=pattern_name,
            trace_completeness=avg_tc,
            tao_cycles=total_tao,
            total_steps=total_steps,
            policy_flag_rate=flag_rate,
            total_violations=total_violations,
            tasks_with_violations=tasks_with_v,
            resource_efficiency=0.0,  # Placeholder, set in evaluate_multiple_patterns
        )

        return metrics

    @staticmethod
    def _wrap_prompt_for_evaluation(prompt: str, task: TestTask) -> str:
        """Wrap task prompt with output format instructions for evaluation.

        This only affects the evaluation pipeline, not the agent's own behavior.
        Adds explicit formatting guidance so agent output is easier to judge.
        """
        mode = task.judge.get("mode", "exact")

        if mode == "json":
            # For JSON tasks, emphasize strict JSON-only output
            return (
                f"{prompt}\n\n"
                "CRITICAL: Your response must contain ONLY a valid JSON object. "
                "No explanations, no markdown formatting, no code blocks, no extra text. "
                "Output the raw JSON object directly."
            )
        elif mode == "exact":
            # For exact match tasks, emphasize concise output
            return (
                f"{prompt}\n\n"
                "CRITICAL: Output ONLY the direct answer with no extra words, explanations, or formatting. "
                "For numbers, output only the number. For names, output only the name. "
                "For Yes/No questions, output only 'Yes' or 'No'."
            )
        else:
            # For regex and other modes, return as-is
            return prompt

    async def _run_tasks(
        self,
        pattern_name: str,
        graph,
        tasks: List[TestTask],
        variant: str = "original",
    ) -> List[TaskResult]:
        """Run a list of tasks on a pattern."""
        results = []

        for i, task in enumerate(tasks, 1):
            prompt = task.prompt
            if variant == "perturbed" and task.get_perturbations():
                # Use first perturbation
                prompt = task.get_perturbations()[0]

            # Wrap prompt with evaluation format instructions
            prompt = self._wrap_prompt_for_evaluation(prompt, task)

            result = await self._run_single_task(pattern_name, graph, task, prompt)
            results.append(result)

            # Display strict evaluation result

            # If lenient result differs, show it as well
            if result.lenient_judge_success != result.judge_success:
                pass

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
        """Run a single task and collect metrics."""
        result = TaskResult(
            task_id=task.id,
            task_category=task.category,
            task_complexity=task.complexity,
            pattern_name=pattern_name,
        )

        try:
            # Execute task with timeout
            start_time = time.time()

            try:
                # Invoke graph with evaluation_mode enabled
                # This tells patterns (Reflex, ToT) to output clean results without decorative formatting
                response = await asyncio.wait_for(
                    asyncio.to_thread(
                        graph.invoke,
                        {
                            "messages": [{"role": "user", "content": prompt}],
                            "evaluation_mode": True  # Clean output for evaluation
                        }
                    ),
                    timeout=self.task_timeout,
                )
            except asyncio.TimeoutError:
                end_time = time.time()
                result.start_time = start_time
                result.end_time = end_time
                result.latency = end_time - start_time
                result.success = False
                result.error = f"Task timed out after {self.task_timeout}s (>{self.task_timeout/60:.0f} min)"
                result.output = ""
                result.judge_success = False
                result.judge_message = f"Timeout: task did not complete within {self.task_timeout/60:.0f} minutes"
                result.lenient_judge_success = False
                result.lenient_judge_message = f"Timeout: task did not complete within {self.task_timeout/60:.0f} minutes"
                return result

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

            # Extract structured trace
            trace = TraceExtractor.extract(response, pattern_name, task.id)
            result.trace = trace

            # Populate metrics from trace
            result.step_count = len(trace.steps)
            result.tool_call_count = trace.total_tool_calls
            result.input_tokens = trace.total_input_tokens
            result.output_tokens = trace.total_output_tokens
            result.total_tokens = trace.total_tokens
            result.tokens_estimated = trace.any_tokens_estimated

            # Fallback: if trace tokens are all zero, use old estimation
            if result.total_tokens == 0:
                result.input_tokens = len(prompt) // 4
                result.output_tokens = len(result.output) // 4
                result.total_tokens = result.input_tokens + result.output_tokens
                result.tokens_estimated = True

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
        """Run robustness tests with perturbations."""
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
        """Collect success dimension metrics (both strict and lenient)."""
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
        """Collect efficiency dimension metrics."""
        for result in results:
            if result.success:
                efficiency_metrics.latencies.append(result.latency)
                efficiency_metrics.input_tokens.append(result.input_tokens)
                efficiency_metrics.output_tokens.append(result.output_tokens)
                efficiency_metrics.step_counts.append(result.step_count)
                efficiency_metrics.tool_call_counts.append(result.tool_call_count)
                if result.trace:
                    efficiency_metrics.tao_cycle_counts.append(result.trace.tao_cycles)
                    if result.tokens_estimated:
                        efficiency_metrics.any_tokens_estimated = True

    def _collect_robustness_metrics(
        self,
        robustness_metrics: RobustnessMetrics,
        original_results: List[TaskResult],
        perturbed_results: List[TaskResult],
    ):
        """Collect robustness dimension metrics."""
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
        """Collect controllability dimension metrics."""
        # Schema compliance
        json_tasks = [t for t in tasks if t.schema is not None]
        controllability_metrics.total_json_tasks = len(json_tasks)

        for result in results:
            task = next((t for t in tasks if t.id == result.task_id), None)
            if task and task.schema:
                if result.schema_compliant:
                    controllability_metrics.schema_compliant_tasks += 1

        # Tool policy compliance — actual violation detection via trace data
        tool_tasks = [t for t in tasks if t.policy and "tool_whitelist" in t.policy]
        controllability_metrics.total_tool_tasks = len(tool_tasks)

        # Build task lookup for whitelist checking
        task_lookup = {t.id: t for t in tasks}
        compliant_count = 0
        total_unauthorized = 0

        for task_def in tool_tasks:
            whitelist = set(task_def.policy["tool_whitelist"])
            result = next((r for r in results if r.task_id == task_def.id), None)
            if result is None or result.trace is None:
                compliant_count += 1  # No trace = no evidence of violation
                continue

            task_violated = False
            for step in result.trace.steps:
                for tc in step.tool_calls:
                    if tc.tool_name not in whitelist:
                        total_unauthorized += 1
                        task_violated = True

            if not task_violated:
                compliant_count += 1

        controllability_metrics.tool_policy_compliant_tasks = compliant_count
        controllability_metrics.unauthorized_tool_uses = total_unauthorized

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
    task_timeout: float = PatternEvaluator.DEFAULT_TASK_TIMEOUT,
    parallel: bool = True,
    max_concurrency: int = 2,
) -> Dict[str, PatternMetrics]:
    """Evaluate multiple patterns and compare.

    Args:
        patterns: Dict of {pattern_name: graph}
        test_tasks: Test tasks to run (default: all)
        include_robustness: Whether to run robustness tests
        delay_between_tasks: Delay in seconds between tasks (default: 3.0)
        task_timeout: Timeout in seconds per task (default: 180s / 3 minutes)
        parallel: Whether to run patterns in parallel (default: True)
        max_concurrency: Max number of patterns to run concurrently (default: 2).
            Prevents resource contention on local LLM backends like Ollama.

    Returns:
        Dict of {pattern_name: PatternMetrics}
    """
    results = {}

    if parallel:
        # Use semaphore to limit concurrency — prevents Ollama resource contention
        semaphore = asyncio.Semaphore(max_concurrency)

        async def _eval_one(name: str, graph) -> tuple:
            async with semaphore:
                print(f"  [Parallel] Starting evaluation: {name}")
                evaluator = PatternEvaluator(
                    delay_between_tasks=delay_between_tasks, task_timeout=task_timeout
                )
                metrics = await evaluator.evaluate_pattern(
                    name, graph, test_tasks, include_robustness
                )
                print(f"  [Parallel] Completed evaluation: {name}")
                return name, metrics

        tasks = [_eval_one(name, graph) for name, graph in patterns.items()]
        completed = await asyncio.gather(*tasks)
        for name, metrics in completed:
            results[name] = metrics
    else:
        # Sequential fallback
        evaluator = PatternEvaluator(
            delay_between_tasks=delay_between_tasks, task_timeout=task_timeout
        )
        for pattern_name, graph in patterns.items():
            metrics = await evaluator.evaluate_pattern(
                pattern_name, graph, test_tasks, include_robustness
            )
            results[pattern_name] = metrics

    # Print comparison
    MetricsAggregator.compare_patterns(results)

    # --- Phase D2: Compute controllability results (cross-pattern) ---
    # Collect avg tokens per pattern for resource efficiency normalisation
    all_pattern_tokens = {
        name: metrics.efficiency.avg_total_tokens()
        for name, metrics in results.items()
    }
    resource_efficiencies = compute_resource_efficiency(all_pattern_tokens)

    # Compute ControllabilityResult for each pattern
    # We need TaskResult lists — re-evaluate from stored evaluator data
    # Since evaluators are local, we compute from PatternMetrics + stored results
    # For now, compute from the metrics we have; trace-based metrics require
    # the evaluator to store results, which we handle via a callback approach.
    controllability_results = {}
    for name, metrics in results.items():
        re_val = resource_efficiencies.get(name, 1.0)
        # Trace completeness and policy violations are collected per-evaluator
        # and stored on PatternMetrics via the evaluator callback below
        cr = getattr(metrics, '_controllability_result_data', None)
        if cr is not None:
            cr.resource_efficiency = re_val
            controllability_results[name] = cr
            metrics.controllability_result = cr

    # --- Phase E: Compute normalised scores and composite scores ---
    normalised_scores, composite_scores = compute_all_scores(
        results, controllability_results
    )

    # Attach to results for downstream report generation
    for name in results:
        results[name]._normalised_scores = normalised_scores.get(name)
        results[name]._composite_score = composite_scores.get(name)

    return results
