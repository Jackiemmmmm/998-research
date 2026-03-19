# Implementation Spec: Phase D1 - Robustness and Scalability

> **Owner**: P2 (Yiming Wang)
> **Implementer**: P1 (Yucheng Tu)
> **Week**: 3-4
> **Phase**: [D1 - Enhance Robustness & Scalability](../PROJECT_GAP_ANALYSIS_AND_PLAN.md#phase-d-systemic-layer-enhancement-dimensions-6--7)
> **Proposal Ref**: [Group-1.pdf § 2.2.3 Dim6](../Group-1.pdf)
> **Status**: READY

---

## 1. Objective

To extend the current perturbation-only robustness pipeline into a proposal-aligned robustness and scalability module that quantifies perturbation tolerance, stochastic stability, and complexity-sensitive performance decline.

---

## 2. Input

| Field Name | Source File | Source Class/Method | Current Value Range | Sample Value |
|------------|-------------|--------------------|--------------------|-------------|
| `robustness["perturbations"]` | `src/evaluation/test_suite.py` | `TestTask.robustness` | `List[str]`, typically length 2 | `["All A⊆B...", "Given A->B..."]` for task `B1` |
| `robustness["tool_failure_prob"]` | `src/evaluation/test_suite.py` | `TestTask.robustness` | [0, 1] | `0.15` for tool tasks `C1-C4` |
| `complexity` | `src/evaluation/test_suite.py` | `TestTask.complexity` | `{simple, medium, complex}` | `simple` for `A1`, `medium` for `B1`, `complex` for `D1` |
| `judge_success` | `src/evaluation/evaluator.py` | `TaskResult.judge_success` | `{True, False}` | Runtime-generated |
| `latency` | `src/evaluation/evaluator.py` | `TaskResult.latency` | [0, +inf) seconds | `129.0` seconds noted for pre-fix ToT runs |
| `task_robustness_scores` | `src/evaluation/metrics.py` | `RobustnessMetrics.task_robustness_scores` | task_id -> [0, 1] | Runtime-generated |
| `original_success_rate` | `src/evaluation/metrics.py` | `RobustnessMetrics.original_success_rate` | [0, 1] | `0.625` possible for CoT first-run result |
| `perturbed_success_rate` | `src/evaluation/metrics.py` | `RobustnessMetrics.perturbed_success_rate` | [0, 1] | Runtime-generated |
| `degradation_percentage` | `src/evaluation/metrics.py` | `RobustnessMetrics.degradation_percentage` | [0, 100] | Runtime-generated |

---

## 3. Output

P1 should extend the robustness module with the following structures.

```python
@dataclass
class StabilitySweepResult:
    temperatures: List[float]
    repeats_per_temperature: int
    success_rates_by_temperature: Dict[float, float]
    variance_across_temperatures: float
    stability_index: float


@dataclass
class ScalabilityResult:
    success_by_complexity: Dict[str, float]
    complexity_decline: float
    scaling_score: float
```

`RobustnessMetrics` should additionally store:

- `absolute_degradation: float`
- `stability_index: float`
- `success_by_complexity: Dict[str, float]`
- `scaling_score: float`

---

## 4. Computation Logic

### 4.1 Perturbation Protocol

For each task with perturbations:

1. evaluate the clean prompt once
2. evaluate **all available perturbations**, not only the first perturbation
3. aggregate perturbed outcomes over all perturbation variants

Clean success:

```text
S_clean = mean(judge_success over original prompts)
```

Noisy success:

```text
S_noisy = mean(judge_success over all perturbation prompts)
```

### 4.2 Degradation Metric

The proposal defines degradation as:

```text
Delta = |S_clean - S_noisy|
```

This spec therefore requires two forms:

```text
absolute_degradation = abs(S_clean - S_noisy)
degradation_percentage = 0 if S_clean == 0 else 100 * absolute_degradation / S_clean
```

This preserves proposal fidelity while remaining interpretable in reports.

### 4.3 Stability Sweep

Temperature set:

```text
[0.0, 0.3, 0.7, 1.0]
```

Repeats per temperature:

```text
3
```

If explicit model seed control is not yet supported by the provider, repeated runs at each temperature serve as the Stage 1 stochastic approximation.

For each temperature `t`:

```text
success_rate_t = mean(judge_success over all tasks and 3 repeated runs at temperature t)
```

Variance:

```text
variance_across_temperatures = population_variance(success_rate_t over all temperatures)
```

Because a success rate lies in `[0, 1]`, the maximum possible variance is `0.25`. Therefore:

```text
stability_index = 1 - min(variance_across_temperatures / 0.25, 1.0)
```

Interpretation:

- `1.0` = highly stable
- `0.0` = maximally unstable

### 4.4 Scalability Across Task Complexity

Compute success rates by complexity:

```text
success_simple  = mean(judge_success for complexity == "simple")
success_medium  = mean(judge_success for complexity == "medium")
success_complex = mean(judge_success for complexity == "complex")
```

Use the proposal's notion of performance decline under increasing task difficulty.

Define:

```text
complexity_decline = max(0.0, success_simple - success_complex)
scaling_score = 1 - complexity_decline
```

This produces:

- `1.0` when performance is complexity-invariant
- lower values when performance degrades on harder tasks

### 4.5 Recommended Dimension 6 Aggregation

Once all D1 fields are available:

```text
dim6_score = mean(
    1 - absolute_degradation,
    stability_index,
    scaling_score
)
```

If one component is unavailable, aggregate over the remaining available components.

### 4.6 Edge Cases

| Case | Expected Behaviour |
|------|--------------------|
| A task has no perturbations | Exclude it from perturbation degradation, but retain it in complexity analysis |
| `S_clean == 0` | Set `degradation_percentage = 0.0` and rely on `absolute_degradation` for interpretation |
| All temperatures yield identical success rates | `variance_across_temperatures = 0`, `stability_index = 1.0` |
| Only one complexity band is present | `scaling_score = None`; exclude from final Dim6 mean |
| A task times out under one temperature | Treat timeout as failure for success-rate calculation |

---

## 5. Integration Points

| Action | File | What to Change |
|--------|------|----------------|
| MODIFY | `src/evaluation/metrics.py` | Extend `RobustnessMetrics` with stability and scalability fields |
| MODIFY | `src/evaluation/evaluator.py` | Run all perturbations, add temperature sweep, compute success-by-complexity |
| MODIFY | `run_evaluation.py` | Expose robustness sweep configuration if needed |
| MODIFY | `src/evaluation/report_generator.py` | Report absolute degradation, stability index, and scaling score |

---

## 6. Verification Cases

### Case 1: Degradation

```text
Input:
  S_clean = 0.75
  S_noisy = 0.50
Expected:
  absolute_degradation = 0.25
  degradation_percentage = 33.333...
```

### Case 2: Stability index

```text
Input success rates by temperature = [1.00, 0.75, 0.75, 0.50]
Population variance = 0.03125
Expected stability_index = 1 - (0.03125 / 0.25) = 0.875
```

### Case 3: Complexity scaling

```text
Input:
  success_simple = 0.90
  success_medium = 0.70
  success_complex = 0.50
Expected:
  complexity_decline = 0.40
  scaling_score = 0.60
```

### Case 4: No degradation

```text
Input:
  S_clean = 0.80
  S_noisy = 0.80
Expected:
  absolute_degradation = 0.0
  degradation_percentage = 0.0
```

---

## 7. Open Questions

1. If provider-level seed support becomes available before Phase F, should the evaluator replace repeated runs with explicit seed sweeps, or retain both as complementary analyses?
2. Should the final D1 implementation log per-perturbation outcomes separately in JSON for later error taxonomy analysis?

---

## Checklist Before Handing to P1

- [x] Every field in Section 2 uses a real codebase field
- [x] Every formula in Section 4 is explicit
- [x] Edge cases are defined
- [x] Verification cases contain exact expected outputs
- [x] Integration points are exact file paths
- [x] The document is implementation-ready
