# Implementation Spec: Phase F - Statistical Rigor and Reproducibility

> **Owner**: P2 (Yiming Wang)
> **Implementer**: P1 (Yucheng Tu)
> **Week**: 5-6
> **Phase**: [F - Statistical Rigor & Reproducibility](../PROJECT_GAP_ANALYSIS_AND_PLAN.md#phase-f-statistical-rigor--reproducibility)
> **Proposal Ref**: [Group-1.pdf § 2.2](../Group-1.pdf), [Group-1.pdf § 2.3 Table 2 C4](../Group-1.pdf)
> **Status**: READY

---

## 1. Objective

To provide a statistically defensible multi-run evaluation protocol that supports repeated trials, confidence intervals, and effect-size reporting, thereby transforming one-off benchmark outputs into reproducible experimental evidence.

---

## 2. Input

| Field Name | Source File | Source Class/Method | Current Value Range | Sample Value |
|------------|-------------|--------------------|--------------------|-------------|
| `task_id` | `src/evaluation/evaluator.py` | `TaskResult.task_id` | string | `"A1"` |
| `pattern_name` | `src/evaluation/evaluator.py` | `TaskResult.pattern_name` | string | `"CoT"` |
| `judge_success` | `src/evaluation/evaluator.py` | `TaskResult.judge_success` | `{True, False}` | Runtime-generated |
| `latency` | `src/evaluation/evaluator.py` | `TaskResult.latency` | [0, +inf) seconds | `129.0` seconds reported for pre-fix ToT runs |
| `total_tokens` | `src/evaluation/evaluator.py` | `TaskResult.total_tokens` | [0, +inf) | `41` reported for Reflex anomaly |
| `pattern_metrics[name].summary()` | `src/evaluation/metrics.py` | `PatternMetrics.summary()` | dict of scalar metrics | includes `success_rate_strict`, `avg_latency_sec`, `avg_tokens`, `degradation_pct`, `controllability` |
| `task_timeout` | `src/evaluation/evaluator.py` | `PatternEvaluator.task_timeout` | [0, +inf) seconds | `180.0` default |

---

## 3. Output

P1 should create a new statistics module with the following structures.

```python
@dataclass
class ConfidenceInterval:
    mean: float
    std: float
    ci95_low: float
    ci95_high: float
    n: int


@dataclass
class EffectSizeResult:
    metric_name: str
    pattern_a: str
    pattern_b: str
    cohens_d: Optional[float]
    interpretation: str


@dataclass
class StatisticalSummary:
    metric_intervals: Dict[str, Dict[str, ConfidenceInterval]]
    effect_sizes: List[EffectSizeResult]
    num_runs: int
    seeds_used: List[Optional[int]]
```

---

## 4. Computation Logic

### 4.1 Repeated-Run Protocol

Default number of runs:

```text
N = 3
```

Recommended extended configuration:

```text
N = 5 when budget and runtime permit
```

Default seed sequence:

- for `N = 3`: `[11, 23, 37]`
- for `N = 5`: `[11, 23, 37, 47, 59]`

If an underlying provider does not support fixed seed control:

- record `seed = None`
- still execute `N` repeated runs
- report that stochasticity is controlled operationally by repetition rather than explicit provider seeding

### 4.2 Point Estimates

For any scalar metric vector `x_1, ..., x_n`:

```text
mean = (1/n) * Σ x_i
```

Use the **sample standard deviation**:

```text
std = sqrt( Σ (x_i - mean)^2 / (n - 1) ), for n > 1
std = 0.0, for n = 1
```

### 4.3 95% Confidence Intervals

Use the Student-t interval, not the normal approximation, because the proposal explicitly anticipates only `3-5` repeated runs.

Formula:

```text
CI_95 = mean ± t_(0.975, n-1) * std / sqrt(n)
```

Use the following exact lookup table:

| n | df | t_(0.975, df) |
|---|----|---------------|
| 2 | 1 | 12.706 |
| 3 | 2 | 4.303 |
| 4 | 3 | 3.182 |
| 5 | 4 | 2.776 |

For Phase F, `n` is expected to be 3 or 5, so this table is sufficient.

### 4.4 Bounded Metric Handling

For metrics theoretically bounded in `[0, 1]`, such as success rates:

- compute the CI on the raw scale using the formula above
- clip only for presentation in end-user reports

Implementation rule:

- internal stored CI values remain unclipped
- report display values may be clipped to `[0, 1]`

### 4.5 Effect Size (Cohen's d)

For a pairwise comparison between pattern A and pattern B on the same scalar metric:

```text
d = (mean_A - mean_B) / s_pooled

s_pooled = sqrt(
    ((n_A - 1) * std_A^2 + (n_B - 1) * std_B^2) / (n_A + n_B - 2)
)
```

Edge rule:

- if `s_pooled == 0` and `mean_A == mean_B`, return `cohens_d = 0.0`
- if `s_pooled == 0` and `mean_A != mean_B`, return `cohens_d = None` and `interpretation = "undefined_due_to_zero_variance"`

Interpretation bands:

- `< 0.2`: negligible
- `< 0.5`: small
- `< 0.8`: medium
- `>= 0.8`: large

### 4.6 Minimum Reporting Set

The statistical module must at minimum produce intervals for:

- `success_rate_strict`
- `avg_latency_sec`
- `avg_total_tokens` or `avg_tokens`
- `degradation_percentage`
- `overall_controllability`

When additional dimension scores become available, the same machinery should apply without redesign.

### 4.7 Edge Cases

| Case | Expected Behaviour |
|------|--------------------|
| `n = 1` | `std = 0.0`, CI lower = CI upper = mean |
| One run times out | Keep the run; represent success-based metrics as failure and latency as observed timeout latency |
| Missing metric for one run | Exclude that run from the metric-specific interval, but record reduced `n` |
| All run values are identical | `std = 0.0`; CI collapses to the point estimate |

---

## 5. Integration Points

| Action | File | What to Change |
|--------|------|----------------|
| CREATE | `src/evaluation/statistics.py` | Implement interval and effect-size computation |
| MODIFY | `src/evaluation/evaluator.py` | Add repeated-run execution mode and preserve per-run outputs |
| MODIFY | `run_evaluation.py` | Add `--num-runs` and, if feasible, `--seed-mode` CLI options |
| MODIFY | `src/evaluation/report_generator.py` | Export mean, std, and 95% CI tables |
| MODIFY | `src/evaluation/visualization.py` | Support error bars where appropriate |
| MODIFY | `src/llm_config.py` | Add seed propagation if provider supports it |

---

## 6. Verification Cases

### Case 1: Success-rate CI with N = 3

```text
Input runs = [0.70, 0.75, 0.80]
mean = 0.75
sample std = 0.05
margin = 4.303 * 0.05 / sqrt(3) = 0.1242
Expected CI = [0.6258, 0.8742]
```

### Case 2: Latency CI with N = 3

```text
Input runs = [10.0, 11.0, 12.0]
mean = 11.0
sample std = 1.0
margin = 4.303 * 1.0 / sqrt(3) = 2.4843
Expected CI = [8.5157, 13.4843]
```

### Case 3: Cohen's d

```text
Pattern A runs = [0.8, 0.9, 0.7]
Pattern B runs = [0.5, 0.6, 0.4]
mean_A = 0.8, std_A = 0.1
mean_B = 0.5, std_B = 0.1
s_pooled = 0.1
Expected d = 3.0
Interpretation = "large"
```

### Case 4: Zero variance

```text
Pattern A runs = [0.7, 0.7, 0.7]
Pattern B runs = [0.7, 0.7, 0.7]
Expected d = 0.0
Interpretation = "negligible"
```

---

## 7. Open Questions

1. Should Phase F compute pairwise effect sizes for every metric-pattern pair by default, or only for the final set of dimension scores and composite scores?
2. If some providers do not support deterministic seeds, should the final report separate "seed-controlled" and "repeat-only" runs in the reproducibility appendix?

---

## Checklist Before Handing to P1

- [x] Every field in Section 2 exists in the current codebase or runtime pipeline
- [x] Every formula in Section 4 is explicit
- [x] All required edge cases are defined
- [x] Verification cases contain exact numerical outputs
- [x] Integration points list exact file paths
- [x] The document is implementation-ready
