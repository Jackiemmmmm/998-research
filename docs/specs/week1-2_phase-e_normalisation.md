# Implementation Spec: Phase E - Normalisation and Composite Scoring

> **Owner**: P2 (Yiming Wang)
> **Implementer**: P1 (Yucheng Tu)
> **Week**: 1-2
> **Phase**: [E - Normalization, Aggregation & Composite Scoring](../PROJECT_GAP_ANALYSIS_AND_PLAN.md#phase-e-normalization-aggregation--composite-scoring)
> **Proposal Ref**: [Group-1.pdf § 2.2](../Group-1.pdf)
> **Status**: READY
> **Companion Docs**:
> - [10_WEEK_PROJECT_PLAN_EN.md](../10_WEEK_PROJECT_PLAN_EN.md)
> - [PHASE_A_UNIFIED_TELEMETRY.md](../PHASE_A_UNIFIED_TELEMETRY.md)
> - [week3-4_phase-d1_robustness.md](./week3-4_phase-d1_robustness.md)
> - [week5-6_phase-f_statistical-rigor.md](./week5-6_phase-f_statistical-rigor.md)

---

## 1. Objective

To operationalise the proposal's requirement that all evaluation sub-indicators be mapped to a common 0-1 scale and aggregated into dimension-level and composite scores suitable for rigorous cross-pattern comparison.

---

## 2. Input

The implementation must read the following already-existing metric fields from the current codebase. Sample values are drawn either from versioned documents in `docs/` or, where no version-controlled runtime artifact exists, from the task suite and current runtime semantics.

| Field Name | Source File | Source Class/Method | Current Value Range | Sample Value |
|------------|-------------|--------------------|--------------------|-------------|
| `success.success_rate()` | `src/evaluation/metrics.py` | `SuccessMetrics.success_rate()` | [0, 1] | `0.625` (CoT, first-run result recorded in `docs/10_WEEK_PROJECT_PLAN_EN.md`) |
| `success.lenient_success_rate()` | `src/evaluation/metrics.py` | `SuccessMetrics.lenient_success_rate()` | [0, 1] | Runtime-generated; no version-controlled sample currently stored |
| `success.controllability_gap()` | `src/evaluation/metrics.py` | `SuccessMetrics.controllability_gap()` | [0, 1] | Runtime-generated; no version-controlled sample currently stored |
| `efficiency.avg_latency()` | `src/evaluation/metrics.py` | `EfficiencyMetrics.avg_latency()` | [0, +inf) seconds | `129.0` seconds (ToT timeout-related average recorded in `docs/10_WEEK_PROJECT_PLAN_EN.md`) |
| `efficiency.avg_total_tokens()` | `src/evaluation/metrics.py` | `EfficiencyMetrics.avg_total_tokens()` | [0, +inf) | `41.0` (Reflex anomaly recorded in `docs/10_WEEK_PROJECT_PLAN_EN.md`) |
| `efficiency.avg_steps()` | `src/evaluation/metrics.py` | `EfficiencyMetrics.avg_steps()` | [0, +inf) | Runtime-generated; no version-controlled sample currently stored |
| `efficiency.avg_tool_calls()` | `src/evaluation/metrics.py` | `EfficiencyMetrics.avg_tool_calls()` | [0, +inf) | Runtime-generated; no version-controlled sample currently stored |
| `robustness.original_success_rate` | `src/evaluation/metrics.py` | `RobustnessMetrics.original_success_rate` | [0, 1] | Equals the corresponding strict success rate, e.g. `0.625` for CoT |
| `robustness.perturbed_success_rate` | `src/evaluation/metrics.py` | `RobustnessMetrics.perturbed_success_rate` | [0, 1] | Runtime-generated; no version-controlled sample currently stored |
| `robustness.degradation_percentage` | `src/evaluation/metrics.py` | `RobustnessMetrics.degradation_percentage` | [0, 100] | Runtime-generated; no version-controlled sample currently stored |
| `robustness.avg_robustness_score()` | `src/evaluation/metrics.py` | `RobustnessMetrics.avg_robustness_score()` | [0, 1] | Runtime-generated; no version-controlled sample currently stored |
| `controllability.schema_compliance_rate()` | `src/evaluation/metrics.py` | `ControllabilityMetrics.schema_compliance_rate()` | [0, 1] | Runtime-generated; no version-controlled sample currently stored |
| `controllability.tool_policy_compliance_rate()` | `src/evaluation/metrics.py` | `ControllabilityMetrics.tool_policy_compliance_rate()` | [0, 1] | Runtime-generated; no version-controlled sample currently stored |
| `controllability.format_compliance_rate` | `src/evaluation/metrics.py` | `ControllabilityMetrics.format_compliance_rate` | [0, 1] | Runtime-generated; no version-controlled sample currently stored |
| `controllability.overall_controllability()` | `src/evaluation/metrics.py` | `ControllabilityMetrics.overall_controllability()` | [0, 1] | Runtime-generated; no version-controlled sample currently stored |

**Important implementation note**:

- The scoring module must read metric values from `PatternMetrics`, not from console strings or Markdown output.
- The scoring module must be capable of handling future fields for Dimensions 1, 2, 3, and 5 once those phases are implemented.

---

## 3. Output

P1 should create the following exact data structures in `src/evaluation/scoring.py`.

```python
@dataclass
class NormalizedDimensionScores:
    pattern_name: str
    dimension_scores: Dict[str, Optional[float]]
    sub_indicator_scores: Dict[str, Dict[str, Optional[float]]]
    available_dimensions: List[str]


@dataclass
class CompositeScore:
    pattern_name: str
    default_composite: Optional[float]
    weighted_composite: Optional[float]
    weights_used: Dict[str, float]
    available_dimensions: List[str]
```

Required dimension keys:

- `"dim1_reasoning_quality"`
- `"dim2_cognitive_safety"`
- `"dim3_action_decision_alignment"`
- `"dim4_success_efficiency"`
- `"dim5_behavioural_safety"`
- `"dim6_robustness_scalability"`
- `"dim7_controllability_transparency_resource"`

---

## 4. Computation Logic

### 4.1 Normalisation Strategy

The implementation shall use a **hybrid normalisation strategy**, because the current codebase contains both bounded proportions and unbounded cost variables.

#### Rule A: Identity normalisation for already bounded quality metrics

For any metric already defined on `[0, 1]`, use:

```text
norm(x) = clip(x, 0.0, 1.0)
```

This applies to:

- `success_rate_strict`
- `success_rate_lenient`
- `avg_robustness_score`
- `schema_compliance_rate`
- `tool_policy_compliance_rate`
- `format_compliance_rate`
- `overall_controllability`
- any future dimension scores already expressed in `[0, 1]`

#### Rule B: Inverse min-max normalisation for cost metrics

For any metric where lower is better:

```text
norm_cost(x) = 1 - ((x - x_min) / (x_max - x_min))
```

This applies to:

- `avg_latency`
- `avg_total_tokens`
- `avg_steps`
- `avg_tool_calls`

#### Rule C: Fixed-range inverse normalisation for degradation

Since `degradation_percentage` is already bounded on `[0, 100]`, use:

```text
norm_degradation = 1 - (degradation_percentage / 100)
```

### 4.2 Edge Cases

| Case | Expected Behaviour |
|------|--------------------|
| `x_max == x_min` for a cost metric | Return `0.5` for all patterns on that metric, representing neutral non-discrimination rather than false superiority |
| Only one pattern is available in the scoring run | Use bounded metrics directly; assign `0.5` to all min-max cost metrics |
| A sub-indicator is missing for one pattern | Store `None`; exclude it from the dimension average for that pattern |
| A dimension has no available sub-indicators | Store dimension score as `None`; exclude it from composite aggregation |
| All seven dimensions are missing | Raise a scoring error rather than returning a meaningless composite |

### 4.3 Dimension Score Aggregation

Dimension scores are arithmetic means over available normalised sub-indicators.

### 4.3.0 Cross-Document Mapping Rule

Phase E is the scoring bridge across the entire documentation set. Its role is not to invent new substantive metrics; rather, it standardises, aggregates, and exposes the outputs generated by:

- Phase B (Cognitive metrics)
- Phase C (Behavioural metrics)
- Phase D (Systemic metrics)
- Phase F (statistical wrappers applied to the resulting scores)

Accordingly, the scoring engine must support **all seven dimensions from the outset**, even when some dimensions are temporarily unavailable in the current codebase.

Dimension-to-source mapping:

| Dimension | Primary Source Document | Runtime Source in Code | Phase E Handling Rule |
|-----------|-------------------------|------------------------|-----------------------|
| Dim1 Reasoning Quality | Proposal § 2.2.1; Gap Analysis Phase B1 | future `reasoning_quality_score` | accept as bounded quality score in `[0,1]` |
| Dim2 Cognitive Safety | Proposal § 2.2.1; Gap Analysis Phase B2 | future `cognitive_safety_score` | accept as bounded quality score in `[0,1]` |
| Dim3 Action-Decision Alignment | Proposal § 2.2.2; Gap Analysis Phase C1 | future `alignment_score` | accept as bounded quality score in `[0,1]` |
| Dim4 Success & Efficiency | current `SuccessMetrics` + `EfficiencyMetrics` | available now | compute directly in Phase E |
| Dim5 Behavioural Safety | Proposal § 2.2.2; Gap Analysis Phase C3 | future `behavioural_safety_score` | accept as bounded quality score in `[0,1]` |
| Dim6 Robustness & Scalability | current `RobustnessMetrics` + future D1 outputs | partially available now | compute now, extend later |
| Dim7 Controllability, Transparency & Resource Efficiency | current `ControllabilityMetrics` + future D2 outputs | partially available now | compute now, extend later |

This mapping rule is mandatory, because the proposal defines the framework at the seven-dimension level, not merely at the currently implemented four-metric level.

#### Dimension 4 - Success and Efficiency

Sub-indicators:

- `success_rate_strict_norm = clip(success.success_rate(), 0, 1)`
- `latency_efficiency = norm_cost(efficiency.avg_latency())`
- `token_efficiency = norm_cost(efficiency.avg_total_tokens())`
- `cost_score = 0.5 * latency_efficiency + 0.5 * token_efficiency`

Dimension score:

```text
dim4_score = mean(success_rate_strict_norm, cost_score)
```

#### Dimension 6 - Robustness and Scalability

Stage 1 sub-indicators:

- `perturbation_robustness = 1 - (degradation_percentage / 100)`
- `avg_robustness_score_norm = clip(robustness.avg_robustness_score(), 0, 1)`

Dimension score:

```text
dim6_score = mean(perturbation_robustness, avg_robustness_score_norm)
```

Future extension:

- once `stability_index` and `scaling_score` exist, extend this mean over the full available set

#### Dimension 7 - Controllability, Transparency and Resource Efficiency

Stage 1 sub-indicators:

- `overall_controllability_norm = clip(controllability.overall_controllability(), 0, 1)`

Dimension score:

```text
dim7_score = overall_controllability_norm
```

Future extension:

- when `trace_completeness` and `resource_efficiency` are implemented, define:

```text
dim7_score = mean(overall_controllability_norm, trace_completeness, resource_efficiency)
```

#### Dimensions 1, 2, 3, and 5

Until their dedicated modules exist, store these dimensions as `None`.

Once implemented, the scoring module must accept externally supplied values already mapped to `[0, 1]` and aggregate them by arithmetic mean over available sub-indicators.

Required future hooks:

```text
dim1_score = mean(available Dim1 sub-indicators)
dim2_score = mean(available Dim2 sub-indicators)
dim3_score = mean(available Dim3 sub-indicators)
dim5_score = mean(available Dim5 sub-indicators)
```

This explicit placeholder contract ensures that Phase E does not need structural redesign when P1 later completes Phases B and C.

### 4.4 Composite Score

#### Default composite

The default composite score should average all **available** dimension scores:

```text
default_composite = mean(all non-None dim_i scores)
```

#### Weighted composite

The weighted composite must support a user-supplied weight dictionary.

Default weights:

```text
uniform weighting over available dimensions
```

This is consistent with the proposal's position that either uniform or weighted combinations may be used, with sensitivity analysis performed later in Phase F.

If custom weights are supplied:

1. drop weights for unavailable dimensions
2. renormalise the remaining weights to sum to `1.0`
3. compute the weighted mean

### 4.5 Sensitivity-Analysis Hook

Although the full sensitivity analysis belongs to Phase F, Phase E must expose a stable weighting interface so that Phase F can vary weights without refactoring the scoring layer.

Therefore, the scoring module must support:

```python
compute_composite(
    dimension_scores: Dict[str, Optional[float]],
    weights: Optional[Dict[str, float]] = None,
)
```

Required default behavior:

- if `weights is None`, use uniform weighting over available dimensions
- if `weights` is provided, renormalise over available dimensions
- always return the final `weights_used`

This design directly supports the proposal's appendix-level sensitivity analysis requirement.

---

## 5. Integration Points

| Action | File | What to Change |
|--------|------|----------------|
| CREATE | `src/evaluation/scoring.py` | Implement normalisation helpers, dimension aggregation, and composite scoring |
| MODIFY | `src/evaluation/__init__.py` | Export scoring objects |
| MODIFY | `src/evaluation/metrics.py` | Ensure `PatternMetrics` outputs remain compatible with dimension-to-sub-indicator mapping |
| MODIFY | `src/evaluation/report_generator.py` | Add normalised sub-indicators, dimension scores, and composite scores to JSON/Markdown/CSV outputs |
| MODIFY | `src/evaluation/visualization.py` | Add support for plotting seven-dimension scores and composite rankings |
| MODIFY | `run_evaluation.py` | Invoke scoring after all pattern metrics have been collected |

---

## 6. Verification Cases

### Case 1: Basic inverse min-max on latency

```text
Input latencies = [10, 20, 40]
Expected latency_efficiency = [1.0, 0.667, 0.0]
```

### Case 2: All same value on a cost metric

```text
Input avg_total_tokens = [800, 800, 800]
Expected token_efficiency = [0.5, 0.5, 0.5]
```

### Case 3: Dimension 4 aggregation

```text
Input:
  success_rate_strict = 0.625
  latency_efficiency = 0.75
  token_efficiency = 0.25
Then:
  cost_score = 0.5 * 0.75 + 0.5 * 0.25 = 0.5
Expected dim4_score = mean(0.625, 0.5) = 0.5625
```

### Case 4: Composite over available dimensions only

```text
Input:
  dim1 = None
  dim2 = None
  dim3 = None
  dim4 = 0.5625
  dim5 = None
  dim6 = 0.7000
  dim7 = 0.8000
Expected default_composite = mean(0.5625, 0.7000, 0.8000) = 0.6875
```

### Case 5: Weighted composite with one missing dimension

```text
Input dimensions:
  dim4 = 0.60
  dim6 = 0.40
  dim7 = 0.80
Input weights:
  dim4 = 0.5, dim6 = 0.3, dim7 = 0.2
Expected weighted_composite = 0.5*0.60 + 0.3*0.40 + 0.2*0.80 = 0.58
```

---

## 7. Open Questions

No blocking open questions remain for Phase E implementation.

Deferred, non-blocking design choices:

1. A CLI switch for custom weight profiles may be added later, but is not required for Week 1-2 delivery.
2. `success_rate_lenient` should remain a supporting diagnostic indicator in Stage 1 and should not enter the default Dim4 score until the team explicitly redefines its theoretical role.

---

## Checklist Before Handing to P1

- [x] Every field in Section 2 uses a real field or method from the current codebase
- [x] Every formula in Section 4 is implementation-ready
- [x] Every edge case in Section 4.2 has a defined behaviour
- [x] Every verification case in Section 6 has a concrete expected output
- [x] Section 5 lists exact file paths
- [x] The document is concise enough to serve as an implementation spec
