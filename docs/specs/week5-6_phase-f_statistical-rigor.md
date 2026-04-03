# Implementation Spec: Phase F - Statistical Rigor & Reproducibility

> **Owner**: P2 (Yiming Wang)
> **Implementer**: P1 (Yucheng Tu)
> **Week**: 5-6
> **Phase**: [F - Statistical Rigor & Reproducibility](../PROJECT_GAP_ANALYSIS_AND_PLAN.md#phase-f-statistical-rigor--reproducibility)
> **Proposal Ref**: [Group-1.pdf Section 2.3 Table 2 C4](../Group-1.pdf)
> **Status**: READY FOR IMPLEMENTATION

---

## 1. Objective

Add a multi-run evaluation and reporting layer that computes mean, standard deviation, 95% confidence interval, and pairwise effect size over repeated pattern runs, while staying compatible with the current `run_evaluation.py -> evaluate_multiple_patterns() -> PatternMetrics` pipeline.

---

## 2. Implementation Principle

This Phase F specification should follow the project plan's original Week 5-6 scope for statistical rigor and reproducibility.

### 2.1 What Phase F must deliver in Week 5-6

Week 5-6 Phase F should cover all of the following:

1. repeated evaluation runs (`N = 3-5`)
2. statistical summaries (mean, standard deviation, 95% confidence interval)
3. reproducibility controls for model configuration
4. reporting-ready outputs for downstream analysis and visualization

### 2.2 Planning assumption for implementation

Phase F should be designed so that P1 can implement the required statistical layer across the current evaluation pipeline while also adding the reproducibility controls promised in the project plan.

This means Week 5-6 Phase F is expected to include:

- configurable repeated runs
- model/version metadata capture
- seed-related configuration support in `LLMConfig` where the active provider/backend supports it
- report outputs suitable for later visualisation with error bars

---

## 3. Input

| Field Name | Source File | Source Class/Method | Current Value Range | Sample Value | Usage |
|------------|-------------|--------------------|--------------------|--------------|-------|
| `pattern_metrics` | `src/evaluation/evaluator.py` | `evaluate_multiple_patterns()` return | `Dict[str, PatternMetrics]` | `{"ReAct": PatternMetrics(...), ...}` | Base unit for per-run aggregation |
| `success.success_rate()` | `src/evaluation/metrics.py` | `SuccessMetrics.success_rate()` | `[0, 1]` | `0.625` | Run-level strict success summary |
| `success.lenient_success_rate()` | `src/evaluation/metrics.py` | `SuccessMetrics.lenient_success_rate()` | `[0, 1]` | `0.750` | Optional supplementary success summary |
| `efficiency.avg_latency()` | `src/evaluation/metrics.py` | `EfficiencyMetrics.avg_latency()` | `>= 0` | `4.83` | Mean/CI for runtime cost |
| `efficiency.avg_total_tokens()` | `src/evaluation/metrics.py` | `EfficiencyMetrics.avg_total_tokens()` | `>= 0` | `1325.5` | Mean/CI for token cost |
| `robustness.degradation_percentage` | `src/evaluation/metrics.py` | `RobustnessMetrics.degradation_percentage` | `[0, 100]` | `25.0` | Mean/CI for robustness loss |
| `controllability.overall_controllability()` | `src/evaluation/metrics.py` | `ControllabilityMetrics.overall_controllability()` | `[0, 1]` | `0.83` | Mean/CI for base controllability |
| `_normalised_scores.dim4_success_efficiency` | `src/evaluation/scoring.py` | `NormalizedDimensionScores` | `[0, 1]` or `None` | `0.741` | Phase E dimension-level aggregation |
| `_normalised_scores.dim6_robustness_scalability` | `src/evaluation/scoring.py` | `NormalizedDimensionScores` | `[0, 1]` or `None` | `0.618` | Phase E dimension-level aggregation |
| `_normalised_scores.dim7_controllability` | `src/evaluation/scoring.py` | `NormalizedDimensionScores` | `[0, 1]` or `None` | `0.801` | Phase E dimension-level aggregation |
| `_composite_score.composite` | `src/evaluation/scoring.py` | `CompositeScore.composite` | `[0, 1]` | `0.720` | Main pairwise comparison target |
| `provider/model info` | `src/llm_config.py` | `LLMConfig.get_model_info()` | dict | `{"provider": "ollama", "model": "llama3.2"}` | Reproducibility metadata |
| `delay`, `timeout`, `parallel`, `max_concurrency` | `run_evaluation.py` / `evaluator.py` | CLI args / function args | runtime-set | `delay=1.0`, `timeout=180.0` | Experimental configuration metadata |

---

## 4. Output

Phase F should introduce **run-level storage + statistical summary**, without replacing the existing `PatternMetrics`.

```python
@dataclass
class StatisticalSummary:
    mean: float
    std: float
    ci95_low: float
    ci95_high: float
    n: int


@dataclass
class PairwiseEffectSize:
    pattern_a: str
    pattern_b: str
    metric_name: str
    cohens_d: float


@dataclass
class PatternRunRecord:
    run_index: int
    pattern_name: str
    success_rate_strict: float
    success_rate_lenient: float
    avg_latency_sec: float
    avg_total_tokens: float
    degradation_percentage: float
    overall_controllability: float
    dim4_success_efficiency: float | None
    dim6_robustness_scalability: float | None
    dim7_controllability: float | None
    composite_score: float | None


@dataclass
class PatternStatistics:
    pattern_name: str
    num_runs: int
    run_records: list[PatternRunRecord]
    summaries: dict[str, StatisticalSummary]


@dataclass
class StatisticalReport:
    num_runs: int
    per_pattern: dict[str, PatternStatistics]
    pairwise_effect_sizes: dict[str, list[PairwiseEffectSize]]
```

### Required meaning

- `PatternRunRecord`
  - the flattened per-pattern output of **one full run**
- `StatisticalSummary`
  - one metric aggregated across all repeated runs of the same pattern
- `PairwiseEffectSize`
  - pairwise comparison for one metric, initially required only for `composite_score`
- `PatternStatistics`
  - per-pattern Phase F object used by report generation
- `StatisticalReport`
  - top-level Phase F report object containing per-pattern statistics and global pairwise comparisons

---

## 5. Computation Logic

### 5.1 Multi-run Protocol

Week 5-6 Phase F must repeat the full evaluation pipeline and provide the statistical layer required by the project plan.

Required default:

```text
num_runs = 3
```

Supported range:

```text
num_runs in [3, 5]
```

Protocol:

1. run `evaluate_multiple_patterns()` once
2. flatten each returned `PatternMetrics` into one `PatternRunRecord`
3. repeat until `num_runs` records exist for every pattern
4. aggregate run records into `PatternStatistics`

Important:

- Phase F should preserve the existing task prompts, task order, and scoring formulas
- Phase F must preserve the existing `PatternMetrics` outputs for each run
- Phase F must keep a complete list of run-level records; do not aggregate too early
- Phase F should support repeated execution under controlled model settings suitable for reproducibility

### 5.2 Mean and Standard Deviation

For any metric values:

```text
x1, x2, ..., xn
```

compute:

```text
mean = (1/n) * sum(xi)
std  = sample standard deviation
```

Sample standard deviation:

```text
std = sqrt( sum((xi - mean)^2) / (n - 1) )     if n >= 2
std = 0.0                                      if n == 1
```

### 5.3 95% Confidence Interval

Because `n` is small in this project, use the **t-distribution** rather than normal `1.96`.

Formula:

```text
CI95 = mean ± t_(0.975, df=n-1) * (std / sqrt(n))
```

Required critical values for Week 5-6:

| n | df | t_(0.975, df) |
|---|----|---------------|
| 3 | 2 | 4.303 |
| 4 | 3 | 3.182 |
| 5 | 4 | 2.776 |

Implementation rule:

- use a small lookup table for `n in [3, 5]`
- if `n < 2`, set `ci95_low = mean`, `ci95_high = mean`

### 5.4 Cohen's d

Required pairwise effect size metric:

```text
Cohen's d = (mean_a - mean_b) / pooled_std
```

where:

```text
pooled_std = sqrt(((na - 1) * std_a^2 + (nb - 1) * std_b^2) / (na + nb - 2))
```

Edge case:

- if `pooled_std == 0`, then:
  - `cohens_d = 0.0` when `mean_a == mean_b`
  - `cohens_d = +inf` or `-inf` is **not allowed**
  - instead use:
    ```text
    cohens_d = 0.0 if means equal else 999.0 with sign of (mean_a - mean_b)
    ```

Required Week 5-6 scope:

- compute pairwise Cohen's d for `composite_score`
- optional but recommended: also compute for `success_rate_strict`

### 5.5 Primary Aggregation Targets

Phase F must aggregate at least the following metrics:

1. `success_rate_strict`
2. `success_rate_lenient`
3. `avg_latency_sec`
4. `avg_total_tokens`
5. `degradation_percentage`
6. `overall_controllability`
7. `dim4_success_efficiency`
8. `dim6_robustness_scalability`
9. `dim7_controllability`
10. `composite_score`

### 5.6 Reproducibility Metadata

Every statistical report must record:

- `num_runs`
- execution timestamp
- provider/model from `LLMConfig.get_model_info()`
- `delay_between_tasks`
- `task_timeout`
- `parallel`
- `max_concurrency`

- git branch
- git commit hash

In addition, Phase F should support:

- explicit seed-related configuration in `LLMConfig` where supported by the active provider/backend
- fixed temperature across repeated runs unless a temperature sweep is intentionally being evaluated

If the active provider/backend does not support explicit seed control, the report should record that limitation in metadata rather than treating the whole Phase F implementation as failed.

### 5.7 Phase F Interface to Reports

Phase F should not replace the current single-run report schema. It should extend it with:

1. `run_records`
2. `statistical_summaries`
3. `pairwise_effect_sizes`

Recommended JSON structure:

```json
{
  "metadata": {
    "generated_at": "2026-03-28T15:30:00",
    "num_runs": 3,
    "provider_model": {
      "provider": "ollama",
      "model": "llama3.2"
    },
    "delay_between_tasks": 1.0,
    "task_timeout": 180.0,
    "parallel": true,
    "max_concurrency": 1,
    "git_branch": "codex/updated-phase-d1",
    "git_commit": "abc1234"
  },
  "single_run_latest": {
    "Baseline": {...},
    "ReAct": {...},
    "ReAct_Enhanced": {...},
    "CoT": {...},
    "Reflex": {...},
    "ToT": {...}
  },
  "run_records": {
    "Baseline": [{...}, {...}, {...}],
    "ReAct": [{...}, {...}, {...}],
    "ReAct_Enhanced": [{...}, {...}, {...}],
    "CoT": [{...}, {...}, {...}],
    "Reflex": [{...}, {...}, {...}],
    "ToT": [{...}, {...}, {...}]
  },
  "statistical_summaries": {
    "Baseline": {
      "success_rate_strict": {...},
      "avg_latency_sec": {...},
      "composite_score": {...}
    },
    "ReAct": {
      "success_rate_strict": {...},
      "avg_latency_sec": {...},
      "composite_score": {...}
    }
  },
  "pairwise_effect_sizes": {
    "composite_score": [
      {
        "pattern_a": "ReAct",
        "pattern_b": "Baseline",
        "metric_name": "composite_score",
        "cohens_d": 0.84
      },
      {
        "pattern_a": "CoT",
        "pattern_b": "ReAct",
        "metric_name": "composite_score",
        "cohens_d": -0.31
      }
    ],
    "success_rate_strict": [
      {
        "pattern_a": "ReAct",
        "pattern_b": "Baseline",
        "metric_name": "success_rate_strict",
        "cohens_d": 0.52
      }
    ]
  }
}
```

Implementation rule:

- `single_run_latest` should remain keyed by pattern name, matching the current report style
- `run_records` should be keyed by pattern name, each value a list of `PatternRunRecord`
- `statistical_summaries` should be keyed first by pattern name, then by metric name
- `pairwise_effect_sizes` should be keyed by metric name, each value a list of `PairwiseEffectSize`
- pairwise effect sizes are **global report-level outputs**, not fields nested inside one pattern's `PatternStatistics`

Markdown should include:

1. one summary table of `mean ± 95% CI`
2. one pairwise effect-size table for composite score

Visualization outputs should be able to consume the statistical layer for later addition of error bars.

---

## 6. Edge Cases

| Case | Expected Behaviour |
|------|--------------------|
| `num_runs = 1` | Supported defensively but not valid for the project target; CI collapses to mean and report should mark `insufficient_runs = true` |
| A metric is `None` in some runs | Exclude `None` values from that metric's summary; if all are `None`, summary should be omitted |
| A pattern run fails completely | Keep the run record with available fields; do not silently drop the run |
| `std = 0` and means equal | `cohens_d = 0.0` |
| `std = 0` and means differ | `cohens_d = 999.0` or `-999.0` by sign, to avoid infinite values in JSON/CSV |
| `n < 2` | `std = 0.0`, `ci95_low = ci95_high = mean` |
| deterministic model/backend yields identical scores every run | valid result; CI width becomes 0 |

---

## 7. Integration Points

| Action | File | What to Change |
|--------|------|----------------|
| MODIFY | `run_evaluation.py` | Add `--num-runs` CLI arg; implement the top-level multi-run orchestration that repeats `evaluate_multiple_patterns()` |
| CREATE | `src/evaluation/statistics.py` | New module: `PatternRunRecord`, `StatisticalSummary`, `PairwiseEffectSize`, `PatternStatistics`, CI/effect-size helpers |
| MODIFY | `src/evaluation/evaluator.py` | Keep single-run evaluation intact; add only flattening/helper logic needed to support repeated execution and statistical aggregation |
| MODIFY | `src/evaluation/report_generator.py` | Emit run-level records, `mean ± CI`, and effect-size tables in JSON/Markdown/CSV |
| MODIFY | `src/evaluation/visualization.py` | Add error bars for multi-run metrics and optional composite-score CI plot |
| MODIFY | `src/evaluation/__init__.py` | Export Phase F dataclasses/helpers |
| MODIFY | `src/llm_config.py` | Add `get_model_info()` usage in report metadata and seed-related reproducibility support where provider/backend support exists |
| CREATE | `tests/unit_tests/test_statistics.py` | Cover mean/std/CI/Cohen's d/None handling |

---

## 8. Verification Cases

### Case 1: Mean and sample standard deviation

```text
Input:
  values = [0.60, 0.80, 1.00]
Expected:
  mean = 0.80
  std = 0.20
```

### Case 2: 95% CI with n = 3

```text
Input:
  values = [0.60, 0.80, 1.00]
Step 1:
  mean = 0.80
  std = 0.20
  se = 0.20 / sqrt(3) = 0.11547
Step 2:
  margin = 4.303 * 0.11547 = 0.496
Expected:
  ci95_low  = 0.304
  ci95_high = 1.296
```

### Case 3: Zero-variance CI

```text
Input:
  values = [0.75, 0.75, 0.75]
Expected:
  mean = 0.75
  std = 0.0
  ci95_low = 0.75
  ci95_high = 0.75
```

### Case 4: Cohen's d normal case

```text
Input:
  pattern_a = [0.80, 0.90, 1.00]
  pattern_b = [0.50, 0.60, 0.70]
Step 1:
  mean_a = 0.90
  mean_b = 0.60
  std_a = 0.10
  std_b = 0.10
  pooled_std = 0.10
Expected:
  cohens_d = 3.0
```

### Case 5: Cohen's d zero-variance fallback

```text
Input:
  pattern_a = [0.80, 0.80, 0.80]
  pattern_b = [0.60, 0.60, 0.60]
Expected:
  cohens_d = 999.0
```

### Case 6: Metric with None values

```text
Input:
  dim6 scores = [0.70, None, 0.90]
Expected:
  valid values used = [0.70, 0.90]
  mean = 0.80
  n = 2
```

### Case 7: Run record flattening

```text
Input:
  PatternMetrics for ReAct where:
    success_rate_strict = 0.625
    avg_latency_sec = 4.8
    composite_score = 0.712
Expected:
  PatternRunRecord(
    run_index=1,
    pattern_name="ReAct",
    success_rate_strict=0.625,
    avg_latency_sec=4.8,
    composite_score=0.712,
    ...
  )
```

---

## 9. Open Questions (Resolved for Week 5-6)

1. **Should Phase F require seed control before implementation is considered complete?**
   - Yes, where the active provider/backend supports seed control. If a provider does not expose seed control, Phase F should record that limitation in metadata and continue to provide repeated-run statistics.

2. **Should repeated runs be implemented inside `PatternEvaluator` or above it?**
   - Above it. `run_evaluation.py` should own repeated-run orchestration, while `PatternEvaluator` should remain the unit for one full evaluation pass.

3. **Which metric should be the required effect-size target?**
   - `composite_score`, because it is the final cross-pattern comparison metric promised in the proposal.

---

## Checklist Before Handing to P1

- [x] Every input field in Section 3 exists in the current codebase or is a clearly defined flattened derivative
- [x] Every formula in Section 5 is implementation-ready
- [x] Edge cases are explicitly defined
- [x] Integration points are exact file paths
- [x] Verification cases can be copied into unit tests directly
- [x] The design stays compatible with the current static graph architecture
