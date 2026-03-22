# Implementation Spec: Phase D1 - Robustness & Scalability

> **Owner**: P2 (Yiming Wang)
> **Implementer**: P1 (Yucheng Tu)
> **Week**: 3-4
> **Phase**: [D - Systemic Layer Enhancement (Dim 6)](../PROJECT_GAP_ANALYSIS_AND_PLAN.md#phase-d-systemic-layer-enhancement-dimensions-6--7)
> **Proposal Ref**: [Group-1.pdf Section 2.2.3 Dim6](../Group-1.pdf)
> **Status**: READY FOR IMPLEMENTATION

---

## 1. Objective

Extend the current perturbation-only robustness evaluation into a proposal-aligned Dimension 6 module that measures perturbation tolerance, cross-variant stability, and complexity-sensitive performance decline, while remaining fully compatible with the current pattern and evaluator architecture.

---

## 2. Implementation Principle

This Phase D1 specification must remain aligned with the repository's current execution model.

### 2.1 What the current codebase already supports

- `src/evaluation/test_suite.py` already defines task-level perturbations via `TestTask.robustness["perturbations"]`
- `src/evaluation/metrics.py` already contains `RobustnessMetrics`
- `src/evaluation/evaluator.py` already runs an original-task pass plus a robustness pass
- all evaluated patterns (`Baseline`, `ReAct`, `ReAct_Enhanced`, `CoT`, `Reflex`, `ToT`) are pre-built graphs imported in `run_evaluation.py`

### 2.2 What this implies for D1

The proposal mentions temperature or seed sweeps. However, in the current codebase, the pattern graphs are instantiated at import time and are not yet parameterised as reusable graph factories. Therefore:

1. **Stage 1 for Week 3-4** should be implemented using the current architecture:
   - run all available prompt perturbations
   - compute degradation
   - compute a stability proxy from prompt-variant consistency
   - compute scalability from success-by-complexity

2. **Stage 2 for later work** may add true temperature or seed sweeps:
   - only after `llm_config.py` and pattern construction are refactored to support runtime-configurable model parameters

This specification therefore prioritises methodological correctness **within the current repository design**, rather than introducing incompatible abstractions.

---

## 3. Input

| Field Name | Source File | Source Class/Method | Current Value Range | Sample Value | Usage |
|------------|-------------|--------------------|--------------------|--------------|-------|
| `robustness["perturbations"]` | `src/evaluation/test_suite.py` | `TestTask.robustness` | `List[str]`, usually length 2 | `["Compute 17x24...", "What is 17 * 24?"]` | Prompt-variant robustness testing |
| `complexity` | `src/evaluation/test_suite.py` | `TestTask.complexity` | `simple`, `medium`, `complex` | `simple` for `A1`, `complex` for `D1` | Scalability computation |
| `judge_success` | `src/evaluation/evaluator.py` | `TaskResult.judge_success` | `True/False` | runtime-generated | Core success signal |
| `task_id` | `src/evaluation/evaluator.py` | `TaskResult.task_id` | task label | `A1`, `B3`, `D2` | Pairing original and perturbed runs |
| `task_complexity` | `src/evaluation/evaluator.py` | `TaskResult.task_complexity` | `simple`, `medium`, `complex` | `medium` | Complexity grouping |
| `original_success_rate` | `src/evaluation/metrics.py` | `RobustnessMetrics.original_success_rate` | `[0, 1]` | `0.625` | Clean-input baseline |
| `perturbed_success_rate` | `src/evaluation/metrics.py` | `RobustnessMetrics.perturbed_success_rate` | `[0, 1]` | runtime-generated | Perturbed-input baseline |
| `degradation_percentage` | `src/evaluation/metrics.py` | `RobustnessMetrics.degradation_percentage` | `[0, 100]` | runtime-generated | Existing D1-compatible field |
| `task_robustness_scores` | `src/evaluation/metrics.py` | `RobustnessMetrics.task_robustness_scores` | `task_id -> float` | runtime-generated | Per-task robustness summary |

---

## 4. Output

P1 should extend the existing `RobustnessMetrics` structure rather than creating a separate disconnected robustness module.

```python
@dataclass
class RobustnessMetrics:
    # Existing fields retained
    original_success_rate: float
    perturbed_success_rate: float
    degradation_percentage: float
    tool_failure_recovery_rate: float
    tool_failure_graceful_degradation: float
    task_robustness_scores: Dict[str, float]

    # New D1 fields
    perturbation_variant_count: int
    absolute_degradation: float
    stability_index: float
    success_by_complexity: Dict[str, float]
    complexity_decline: float
    scaling_score: float
```

### Required meaning of each new field

- `perturbation_variant_count`
  - total number of perturbed task executions actually run
- `absolute_degradation`
  - `abs(S_clean - S_noisy)` in `[0, 1]`
- `stability_index`
  - prompt-variant stability proxy in `[0, 1]`, higher is better
- `success_by_complexity`
  - per-band success rate dictionary, e.g. `{"simple": 0.75, "medium": 0.50, "complex": 0.25}`
- `complexity_decline`
  - `max(0, success_simple - success_complex)`
- `scaling_score`
  - `1 - complexity_decline`

---

## 5. Computation Logic

### 5.1 Perturbation Protocol

The current evaluator only has a single robustness pass. For Phase D1, this pass must be upgraded from "use the first perturbation only" to "run all available perturbations for each task".

#### Current limitation to fix

In `src/evaluation/evaluator.py`, `_run_robustness_tests()` currently uses only the first perturbation of each task. This under-samples robustness and is inconsistent with the proposal's comparative design.

#### Required D1 behavior

For every task:

1. run the original prompt once
2. if perturbations exist, run **every perturbation string** defined in `TestTask.robustness["perturbations"]`
3. keep all perturbed runs, not just the first one

This ensures that:

- all patterns are tested on the same perturbation set
- robustness is measured over a small but meaningful variant family
- the implementation remains compatible with the current static graph architecture

### 5.2 Original vs Perturbed Success

Let:

```text
S_clean = mean(judge_success over original task runs)
S_noisy = mean(judge_success over all perturbation runs)
```

Then:

```text
absolute_degradation = abs(S_clean - S_noisy)
```

and the existing percentage degradation remains:

```text
degradation_percentage = 0                    if S_clean == 0
degradation_percentage = 100 * (S_clean - S_noisy) / S_clean   otherwise
```

clamped to `[0, 100]`.

### 5.3 Per-Task Robustness Score

For each task:

- compare the original run with **all** of its perturbation runs
- compute a per-variant score
- average those per-variant scores into one task-level robustness score

Recommended scoring rule:

```text
1.0  if original succeeds and perturbed variant succeeds
0.5  if original succeeds and perturbed variant fails
0.0  otherwise
```

Then:

```text
task_robustness_score(task) = mean(all variant scores for that task)
```

### 5.4 Stability Index

The proposal refers to variance-based stability. Since the current codebase does not yet support true runtime temperature sweep over re-instantiated graphs, D1 should use a **prompt-variant stability proxy**.

For each task, collect:

```text
[original_success, perturbation_success_1, perturbation_success_2, ...]
```

where each item is `1.0` for success and `0.0` for failure.

For a task with success mean `p`, compute variance:

```text
variance = p * (1 - p)
```

This variance is bounded by `0.25`, so define:

```text
stability(task) = 1 - min(variance / 0.25, 1.0)
```

Then:

```text
stability_index = mean(stability(task) over all tasks with at least one perturbation)
```

Interpretation:

- `1.0` means fully stable across prompt variants
- values closer to `0.0` mean high sensitivity to perturbation

### 5.5 Success by Complexity

Using the original-task results only:

```text
success_simple  = mean(judge_success where task_complexity == "simple")
success_medium  = mean(judge_success where task_complexity == "medium")
success_complex = mean(judge_success where task_complexity == "complex")
```

Store these in:

```python
success_by_complexity = {
    "simple": ...,
    "medium": ...,
    "complex": ...,
}
```

### 5.6 Complexity Decline and Scaling Score

The proposal's Dim6 requires scalability under increasing task difficulty. In the current task suite, the cleanest operationalisation is performance retention from `simple` to `complex`.

Define:

```text
complexity_decline = max(0.0, success_simple - success_complex)
scaling_score = 1.0 - complexity_decline
```

Interpretation:

- `1.0` means no performance loss from simple to complex tasks
- lower values indicate poorer scalability

### 5.7 Phase E Interface for Dim 6

Phase D1 does **not** own the final dimension-level normalisation policy, but it must expose sub-indicators that Phase E can aggregate.

For the current repository, the recommended Phase E Dim6 formula is:

```text
dim6_score = mean(
    1 - degradation_percentage / 100,
    stability_index,
    scaling_score
)
```

This is preferable to the older placeholder formula using `tool_failure_recovery_rate`, because:

- it is aligned with the proposal's Dim6 language
- it is supported by the current task suite
- it does not depend on a tool-failure simulation pipeline that is not yet meaningfully implemented

---

## 6. Edge Cases

| Case | Expected Behaviour |
|------|--------------------|
| A task has no perturbations | Exclude it from perturbation-based D1 metrics; keep it in `success_by_complexity` |
| `S_clean == 0` | `degradation_percentage = 0.0`; rely on `absolute_degradation` for interpretation |
| No perturbed runs exist at all | `perturbation_variant_count = 0`; `dim6_score` should later be treated as unavailable by Phase E |
| Only one prompt variant exists for a task | Exclude that task from stability variance computation |
| No `simple` or no `complex` tasks are present | `complexity_decline = 0.0`, `scaling_score = 1.0` |
| All variants succeed or all variants fail | variance = 0, therefore task-level stability = 1.0 |

---

## 7. Integration Points

| Action | File | What to Change |
|--------|------|----------------|
| MODIFY | `src/evaluation/metrics.py` | Extend `RobustnessMetrics` with D1 fields |
| MODIFY | `src/evaluation/evaluator.py` | Run all perturbations and compute new D1 statistics |
| MODIFY | `src/evaluation/scoring.py` | Replace old Dim6 placeholder aggregation with D1-aligned formula |
| MODIFY | `src/evaluation/report_generator.py` | Add D1 statistics to JSON, Markdown, and CSV outputs |
| MODIFY | `src/evaluation/visualization.py` | Extend robustness plot to show stability and scaling alongside degradation |
| OPTIONAL | `src/evaluation/__init__.py` | Export any D1 helper functions if a separate helper module is created |

### Recommended implementation order

1. update `RobustnessMetrics` in `metrics.py`
2. update `_run_robustness_tests()` in `evaluator.py` so all perturbations are executed
3. update `_collect_robustness_metrics()` in `evaluator.py`
4. update `scoring.py` so Dim6 uses the new D1 sub-indicators
5. update `report_generator.py`
6. update `visualization.py`
7. add unit tests

---

## 8. Reference Implementation Sketch

The following code snippets are **reference-only** and are included to help P1 implement D1 later.

- They are designed to fit the **current repository architecture**
- They do **not** imply that the repository has already implemented D1
- They should be treated as a safe blueprint, not as the source of truth over Sections 4-7

### 8.1 `src/evaluation/metrics.py`

```python
@dataclass
class RobustnessMetrics:
    # Existing fields retained
    original_success_rate: float = 0.0
    perturbed_success_rate: float = 0.0
    degradation_percentage: float = 0.0
    tool_failure_recovery_rate: float = 0.0
    tool_failure_graceful_degradation: float = 0.0
    task_robustness_scores: Dict[str, float] = field(default_factory=dict)

    # New D1 fields
    perturbation_variant_count: int = 0
    absolute_degradation: float = 0.0
    stability_index: float = 0.0
    success_by_complexity: Dict[str, float] = field(default_factory=dict)
    complexity_decline: float = 0.0
    scaling_score: float = 1.0

    def calculate_degradation(self):
        if self.original_success_rate == 0:
            self.degradation_percentage = 0.0
        else:
            degradation = (
                self.original_success_rate - self.perturbed_success_rate
            ) / self.original_success_rate
            self.degradation_percentage = max(0.0, min(100.0, degradation * 100))

        self.absolute_degradation = abs(
            self.original_success_rate - self.perturbed_success_rate
        )
```

### 8.2 `src/evaluation/evaluator.py` - run all perturbations

```python
async def _run_robustness_tests(
    self,
    pattern_name: str,
    graph,
    tasks: List[TestTask],
) -> List[TaskResult]:
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
```

### 8.3 `src/evaluation/evaluator.py` - compute D1 metrics

```python
def _collect_robustness_metrics(
    self,
    robustness_metrics: RobustnessMetrics,
    original_results: List[TaskResult],
    perturbed_results: List[TaskResult],
):
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
```

### 8.4 helper sketch for complexity-based scaling

```python
def _compute_success_by_complexity(
    original_results: List[TaskResult],
) -> Dict[str, float]:
    result: Dict[str, float] = {}

    for level in ("simple", "medium", "complex"):
        subset = [r for r in original_results if r.task_complexity == level]
        if subset:
            result[level] = sum(1 for r in subset if r.judge_success) / len(subset)

    return result


def _compute_complexity_decline(success_by_complexity: Dict[str, float]) -> float:
    success_simple = success_by_complexity.get("simple")
    success_complex = success_by_complexity.get("complex")

    if success_simple is None or success_complex is None:
        return 0.0

    return max(0.0, success_simple - success_complex)
```

### 8.5 `src/evaluation/scoring.py` - D1-aligned Dim 6 formula

```python
def compute_dim6_scores(
    pattern_metrics: Dict[str, PatternMetrics],
) -> Dict[str, Optional[float]]:
    result = {}

    for pattern_name, metrics in pattern_metrics.items():
        robustness = metrics.robustness

        if robustness.perturbation_variant_count == 0:
            result[pattern_name] = None
            continue

        norm_degradation = 1.0 - (robustness.degradation_percentage / 100.0)
        norm_degradation = max(0.0, min(1.0, norm_degradation))

        sub_indicators = [
            norm_degradation,
            robustness.stability_index,
            robustness.scaling_score,
        ]
        result[pattern_name] = sum(sub_indicators) / len(sub_indicators)

    return result
```

### 8.6 `src/evaluation/report_generator.py` - D1 output example

```python
"robustness": {
    "original_success_rate": ...,
    "perturbed_success_rate": ...,
    "degradation_percentage": ...,
    "absolute_degradation": ...,
    "perturbation_variant_count": ...,
    "stability_index": ...,
    "success_by_complexity": ...,
    "complexity_decline": ...,
    "scaling_score": ...,
    "avg_robustness_score": ...,
}
```

### 8.7 Recommended unit-test targets

At minimum, P1 should later add tests covering:

1. all perturbations are executed, not only the first variant
2. `absolute_degradation` matches `abs(S_clean - S_noisy)`
3. `stability_index` matches the variance-based proxy in Section 5.4
4. `complexity_decline` and `scaling_score` match Section 5.6
5. `compute_dim6_scores()` returns `None` when `perturbation_variant_count == 0`

---

## 9. Verification Cases

### Case 1: Absolute degradation

```text
Input:
  S_clean = 0.75
  S_noisy = 0.50
Expected:
  absolute_degradation = 0.25
```

### Case 2: Percentage degradation

```text
Input:
  S_clean = 0.75
  S_noisy = 0.50
Expected:
  degradation_percentage = 33.333...
```

### Case 3: Stability index for one unstable task

```text
Input:
  task variants = [1, 0, 1]
  p = 2/3
  variance = p * (1-p) = 2/9
  stability = 1 - (2/9) / (1/4) = 1 - 8/9 = 1/9
Expected:
  task-level stability = 0.111...
```

### Case 4: Complexity scaling

```text
Input:
  success_simple = 0.90
  success_medium = 0.70
  success_complex = 0.50
Expected:
  complexity_decline = 0.40
  scaling_score = 0.60
```

### Case 5: Dim6 aggregation

```text
Input:
  degradation_percentage = 25.0
  stability_index = 0.875
  scaling_score = 0.60
Step 1:
  norm_degradation = 1 - 25/100 = 0.75
Step 2:
  dim6_score = (0.75 + 0.875 + 0.60) / 3
Expected:
  dim6_score = 0.741666...
```

### Case 6: No perturbation run

```text
Input:
  perturbation_variant_count = 0
Expected:
  Phase E should treat Dim6 as unavailable rather than as a valid score
```

---

## 10. Open Questions (Resolved for Week 3-4)

1. **Should D1 implement true temperature sweep now?**
   - No. Not in Week 3-4, because the current pattern graphs are not yet runtime-parameterised.

2. **Should D1 still mention temperature sweep in the report?**
   - Yes, but as a later methodological extension rather than as a Week 3-4 deliverable.

3. **Should `tool_failure_recovery_rate` remain in the Dim6 formula?**
   - No. It may remain in `RobustnessMetrics` for backward compatibility, but the D1-aligned formula should prioritise degradation, stability, and scaling.

---

## Checklist Before Handing to P1

- [x] Every field in Section 3 exists in the current codebase or is a clearly defined extension of an existing D1 structure
- [x] Every formula in Section 5 is implementation-ready
- [x] Edge cases are explicitly defined
- [x] Integration points are exact file paths
- [x] Verification cases can be copied into unit tests directly
- [x] The plan remains aligned with the current pattern architecture
