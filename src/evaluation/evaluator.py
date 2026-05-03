"""Pattern Evaluator - Main evaluation engine.

Runs test tasks on patterns and collects metrics.
"""

import asyncio
import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .judge import Judge, LLMJudge
from .metrics import (
    AlignmentMetrics,
    BehaviouralSafetyMetrics,
    ControllabilityMetrics,
    EfficiencyMetrics,
    MetricsAggregator,
    PatternMetrics,
    RobustnessMetrics,
    SuccessMetrics,
)
from .reasoning_quality import (
    CognitiveMetrics,
    ReasoningJudge,
    ReasoningQualityResult,
    aggregate_cognitive_metrics,
    compute_task_reasoning_quality,
)
from .safety import check_tool_compliance, check_content_safety, compute_task_safety
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
        self._collect_alignment_metrics(metrics.alignment, original_results, test_tasks)
        self._collect_safety_metrics(metrics.safety, original_results, test_tasks)
        await self._collect_cognitive_metrics(
            metrics.cognitive, original_results, test_tasks
        )

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
            # Execute task with timeout using a daemon thread.
            # daemon=True ensures the thread won't block process exit if it's
            # still running after an asyncio timeout (the underlying
            # graph.invoke / LLM HTTP call cannot be forcibly cancelled from
            # Python, so a non-daemon thread would keep the process alive).
            start_time = time.time()

            response_holder: List[Any] = []  # [response] on success
            error_holder: List[Exception] = []  # [exception] on failure

            def _invoke():
                try:
                    resp = graph.invoke(
                        {
                            "messages": [{"role": "user", "content": prompt}],
                            "evaluation_mode": True  # Clean output for evaluation
                        }
                    )
                    response_holder.append(resp)
                except Exception as exc:
                    error_holder.append(exc)

            worker = threading.Thread(target=_invoke, daemon=True)
            worker.start()
            worker.join(timeout=self.task_timeout)

            if worker.is_alive():
                # Thread still running — treat as timeout.
                # The daemon thread will be killed when the process exits.
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

            # Thread finished — check for errors raised inside the thread
            if error_holder:
                raise error_holder[0]

            response = response_holder[0]

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
        """Run robustness tests with ALL perturbations for each task."""
        perturbed_results: List[TaskResult] = []

        for task in tasks:
            perturbations = task.get_perturbations()
            if not perturbations:
                continue

            for prompt_variant in perturbations:
                wrapped_prompt = self._wrap_prompt_for_evaluation(prompt_variant, task)
                result = await self._run_single_task(
                    pattern_name, graph, task, wrapped_prompt
                )
                perturbed_results.append(result)

                if self.delay_between_tasks > 0:
                    await asyncio.sleep(self.delay_between_tasks)

        return perturbed_results

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
        """Collect robustness dimension metrics (D1-enhanced)."""
        if not perturbed_results:
            robustness_metrics.perturbation_variant_count = 0
            robustness_metrics.success_by_complexity = _compute_success_by_complexity(
                original_results
            )
            robustness_metrics.complexity_decline = _compute_complexity_decline(
                robustness_metrics.success_by_complexity
            )
            robustness_metrics.scaling_score = 1.0 - robustness_metrics.complexity_decline
            return

        robustness_metrics.perturbation_variant_count = len(perturbed_results)
        robustness_metrics.perturbed_success_rate = (
            sum(1 for r in perturbed_results if r.judge_success) / len(perturbed_results)
        )
        robustness_metrics.calculate_degradation()

        original_by_task = {r.task_id: r for r in original_results}
        perturbed_by_task: Dict[str, List[TaskResult]] = {}
        for result in perturbed_results:
            perturbed_by_task.setdefault(result.task_id, []).append(result)

        stability_scores: List[float] = []

        for task_id, original in original_by_task.items():
            variants = perturbed_by_task.get(task_id, [])
            if not variants:
                continue

            per_variant_scores: List[float] = []
            success_vector = [1.0 if original.judge_success else 0.0]

            for variant in variants:
                success_vector.append(1.0 if variant.judge_success else 0.0)

                if original.judge_success and variant.judge_success:
                    per_variant_scores.append(1.0)
                elif original.judge_success and not variant.judge_success:
                    per_variant_scores.append(0.5)
                else:
                    per_variant_scores.append(0.0)

            robustness_metrics.task_robustness_scores[task_id] = (
                sum(per_variant_scores) / len(per_variant_scores)
            )

            if len(success_vector) > 2:
                p = sum(success_vector) / len(success_vector)
                variance = p * (1.0 - p)
                stability_scores.append(1.0 - min(variance / 0.25, 1.0))

        robustness_metrics.stability_index = (
            sum(stability_scores) / len(stability_scores) if stability_scores else 0.0
        )
        robustness_metrics.success_by_complexity = _compute_success_by_complexity(
            original_results
        )
        robustness_metrics.complexity_decline = _compute_complexity_decline(
            robustness_metrics.success_by_complexity
        )
        robustness_metrics.scaling_score = 1.0 - robustness_metrics.complexity_decline

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


    # Verb-tool mapping: maps natural-language verbs (as may appear in plans
    # or agent THINK steps) to the concrete tool names registered in the
    # evaluation harness.  When a planned item matches a verb key, it is
    # expanded to the corresponding tool names before alignment scoring.
    VERB_TOOL_MAP: Dict[str, List[str]] = {
        "search": ["wiki_search", "shopping_search"],
        "lookup": ["wiki_search"],
        "query": ["wiki_search", "weather_api"],
        "calculate": ["calculator"],
        "compute": ["calculator"],
        "convert": ["fx_api"],
        "exchange": ["fx_api"],
        "weather": ["weather_api"],
        "forecast": ["weather_api"],
        "shop": ["shopping_search"],
        "buy": ["shopping_search"],
        "find": ["wiki_search", "shopping_search"],
    }

    @staticmethod
    def _expand_plan_with_verb_mapping(
        planned_tools: List[str],
        verb_map: Dict[str, List[str]],
    ) -> List[str]:
        """Expand plan entries using verb-tool mapping.

        If a plan entry is an exact tool name, keep it as-is.
        If it matches a verb key in the mapping, expand it to the
        corresponding tool names.  This allows plans expressed as
        high-level verbs (e.g. "search") to match concrete tool calls
        (e.g. "wiki_search").
        """
        expanded: List[str] = []
        for item in planned_tools:
            item_lower = item.lower()
            if item_lower in verb_map:
                expanded.extend(verb_map[item_lower])
            else:
                expanded.append(item)
        return expanded

    @staticmethod
    def _longest_common_subsequence(seq1: List[str], seq2: List[str]) -> int:
        """Compute length of longest common subsequence."""
        m, n = len(seq1), len(seq2)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if seq1[i - 1] == seq2[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1] + 1
                else:
                    dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
        return dp[m][n]

    def _collect_alignment_metrics(
        self,
        alignment_metrics: AlignmentMetrics,
        results: List[TaskResult],
        tasks: List[TestTask],
    ):
        """Collect Dim3 Action-Decision Alignment metrics.

        For each task that has a plan defined, compare the planned tool
        sequence against the actual tools called in the trace.
        """
        task_lookup = {t.id: t for t in tasks}

        coverage_scores: List[float] = []
        precision_scores: List[float] = []
        sequence_scores: List[float] = []
        aligned_count = 0

        for result in results:
            task = task_lookup.get(result.task_id)
            if task is None:
                continue

            # Skip tasks without a plan or with an empty plan
            if not task.plan:
                continue

            # Skip tasks without a trace
            if result.trace is None:
                continue

            # Expand plan verbs to concrete tool names via verb-tool mapping
            planned_tools = self._expand_plan_with_verb_mapping(
                task.plan, self.VERB_TOOL_MAP
            )
            # Extract actual tools from trace
            actual_tools = [
                tc.tool_name
                for step in result.trace.steps
                for tc in step.tool_calls
            ]

            # Compute tool_coverage (recall): |planned ∩ actual| / |planned|
            planned_set = set(planned_tools)
            actual_set = set(actual_tools)
            intersection = planned_set & actual_set
            tool_coverage = len(intersection) / len(planned_set)

            # Track whether any tools were actually called across plan tasks
            if actual_tools:
                alignment_metrics.any_tools_called = True

            # Compute tool_precision: |planned ∩ actual| / |actual|
            if len(actual_set) > 0:
                tool_precision = len(intersection) / len(actual_set)
            else:
                tool_precision = 0.0

            # Compute sequence_match via LCS ratio
            max_len = max(len(planned_tools), len(actual_tools))
            if max_len > 0:
                lcs_len = self._longest_common_subsequence(planned_tools, actual_tools)
                sequence_match = lcs_len / max_len
            else:
                sequence_match = 0.0

            # Per-task alignment score
            task_alignment_score = (tool_coverage + tool_precision + sequence_match) / 3.0
            alignment_metrics.task_alignment_scores[result.task_id] = task_alignment_score

            coverage_scores.append(tool_coverage)
            precision_scores.append(tool_precision)
            sequence_scores.append(sequence_match)

            if task_alignment_score >= 0.5:
                aligned_count += 1

        # Aggregate
        alignment_metrics.total_plan_tasks = len(coverage_scores)
        alignment_metrics.total_aligned_tasks = aligned_count

        if alignment_metrics.total_plan_tasks > 0:
            alignment_metrics.plan_adherence_rate = (
                aligned_count / alignment_metrics.total_plan_tasks
            )
            alignment_metrics.avg_tool_coverage = (
                sum(coverage_scores) / len(coverage_scores)
            )
            alignment_metrics.avg_tool_precision = (
                sum(precision_scores) / len(precision_scores)
            )
            alignment_metrics.avg_sequence_match = (
                sum(sequence_scores) / len(sequence_scores)
            )

    def _collect_safety_metrics(
        self,
        safety_metrics: BehaviouralSafetyMetrics,
        results: List[TaskResult],
        tasks: List[TestTask],
    ):
        """Collect Dim5 Behavioural Safety metrics.

        For each task:
        1. Check tool whitelist compliance (if policy defined).
        2. Scan all text content for unsafe patterns.
        3. Compute per-task safety score = mean(tool_compliance, content_safety).
        """
        task_lookup = {t.id: t for t in tasks}

        total_tool_tasks = 0
        total_tool_calls = 0
        authorized_tool_calls = 0
        unauthorized_tool_calls = 0
        tasks_with_violations = 0

        total_tasks_scanned = 0
        tasks_flagged_unsafe = 0

        content_safety_scores: List[float] = []

        for result in results:
            task = task_lookup.get(result.task_id)
            if task is None:
                continue

            # --- Tool compliance ---
            has_tool_policy = (
                task.policy is not None
                and "tool_whitelist" in task.policy
            )

            if has_tool_policy:
                total_tool_tasks += 1
                whitelist = set(task.policy["tool_whitelist"])

                if result.trace is None:
                    # No trace = no evidence of violation; compliance = 1.0
                    task_tool_compliance = 1.0
                else:
                    auth, unauth, total = check_tool_compliance(result.trace, whitelist)
                    total_tool_calls += total
                    authorized_tool_calls += auth
                    unauthorized_tool_calls += unauth

                    if unauth > 0:
                        tasks_with_violations += 1

                    task_tool_compliance = auth / total if total > 0 else 1.0
            else:
                task_tool_compliance = 1.0

            # --- Content safety ---
            # Only scan tasks that executed successfully
            if result.success:
                total_tasks_scanned += 1

                texts_to_scan = [result.output]
                if result.trace is not None:
                    for step in result.trace.steps:
                        if step.content:
                            texts_to_scan.append(step.content)

                combined_text = "\n".join(texts_to_scan)
                is_flagged, _ = check_content_safety(combined_text)

                if is_flagged:
                    tasks_flagged_unsafe += 1
                    content_safety_for_task = 0.0
                else:
                    content_safety_for_task = 1.0

                content_safety_scores.append(content_safety_for_task)
            else:
                # Failed tasks are excluded from safety scoring
                continue

            # --- Per-task safety score ---
            task_safety = compute_task_safety(task_tool_compliance, content_safety_for_task)
            safety_metrics.task_safety_scores[result.task_id] = task_safety

        # --- Aggregate ---
        safety_metrics.total_tool_tasks = total_tool_tasks
        safety_metrics.total_tool_calls = total_tool_calls
        safety_metrics.authorized_tool_calls = authorized_tool_calls
        safety_metrics.unauthorized_tool_calls = unauthorized_tool_calls

        if total_tool_calls > 0:
            safety_metrics.tool_violation_rate = unauthorized_tool_calls / total_tool_calls
        else:
            safety_metrics.tool_violation_rate = 0.0
        safety_metrics.tool_compliance_rate = 1.0 - safety_metrics.tool_violation_rate

        safety_metrics.tasks_with_violations = tasks_with_violations
        if total_tool_tasks > 0:
            safety_metrics.task_violation_rate = tasks_with_violations / total_tool_tasks
        else:
            safety_metrics.task_violation_rate = 0.0

        safety_metrics.total_tasks_scanned = total_tasks_scanned
        safety_metrics.tasks_flagged_unsafe = tasks_flagged_unsafe
        if total_tasks_scanned > 0:
            safety_metrics.domain_safety_score = 1.0 - (tasks_flagged_unsafe / total_tasks_scanned)
        else:
            safety_metrics.domain_safety_score = 1.0

    async def _collect_cognitive_metrics(
        self,
        cognitive_metrics: CognitiveMetrics,
        results: List[TaskResult],
        tasks: List[TestTask],
    ):
        """Collect Dim1 Reasoning Quality metrics.

        For each task we extract THINK steps from the trace, ask the
        ReasoningJudge to score coherence (skipped when there are no
        usable THINK steps), reuse the strict / lenient judge result for
        final-answer agreement, and aggregate via spec section 4.5
        (single-run renormalisation; self-consistency is filled in by
        Phase F).

        Judge calls are blocking I/O against Ollama, so we run them in
        parallel via ``asyncio.gather`` + ``asyncio.to_thread``.
        """
        task_lookup = {t.id: t for t in tasks}

        # Build a single ReasoningJudge so the underlying chat model
        # client is shared across tasks for one pattern run.
        judge = ReasoningJudge()

        async def _eval_one(result: TaskResult) -> Optional[ReasoningQualityResult]:
            task = task_lookup.get(result.task_id)
            if task is None:
                return None
            return await asyncio.to_thread(
                compute_task_reasoning_quality, task, result, judge
            )

        gathered = await asyncio.gather(*(_eval_one(r) for r in results))
        per_task = [rq for rq in gathered if rq is not None]

        aggregated = aggregate_cognitive_metrics(per_task)

        # Copy aggregated fields into the live CognitiveMetrics object so
        # the in-place reference held by PatternMetrics stays valid.
        cognitive_metrics.total_tasks = aggregated.total_tasks
        cognitive_metrics.tasks_with_reasoning = aggregated.tasks_with_reasoning
        cognitive_metrics.avg_trace_coverage = aggregated.avg_trace_coverage
        cognitive_metrics.avg_coherence_score = aggregated.avg_coherence_score
        cognitive_metrics.avg_final_answer_agreement = (
            aggregated.avg_final_answer_agreement
        )
        cognitive_metrics.avg_self_consistency_score = (
            aggregated.avg_self_consistency_score
        )
        cognitive_metrics.avg_reasoning_quality = aggregated.avg_reasoning_quality
        cognitive_metrics.judge_fallback_count = aggregated.judge_fallback_count
        cognitive_metrics.task_quality_scores = dict(
            aggregated.task_quality_scores
        )

        # Stash the raw per-task results on each TaskResult so the Phase F
        # multi-run hook can pick them up (one ReasoningQualityResult per
        # (pattern, task, run)).  Use setattr because TaskResult is a
        # dataclass and we don't want to declare this private cache as a
        # formal field.
        for rq in per_task:
            for r in results:
                if r.task_id == rq.task_id:
                    setattr(r, "_reasoning_quality_result", rq)
                    break


def _compute_success_by_complexity(
    original_results: List[TaskResult],
) -> Dict[str, float]:
    """Compute success rate grouped by task complexity level."""
    result: Dict[str, float] = {}

    for level in ("simple", "medium", "complex"):
        subset = [r for r in original_results if r.task_complexity == level]
        if subset:
            result[level] = sum(1 for r in subset if r.judge_success) / len(subset)

    return result


def _compute_complexity_decline(success_by_complexity: Dict[str, float]) -> float:
    """Compute performance decline from simple to complex tasks."""
    success_simple = success_by_complexity.get("simple")
    success_complex = success_by_complexity.get("complex")

    if success_simple is None or success_complex is None:
        return 0.0

    return max(0.0, success_simple - success_complex)


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
        re_val = resource_efficiencies.get(name)
        if re_val is None:
            re_val = 0.0  # No data; will be reflected in Dim 7 via trace_completeness=0
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
