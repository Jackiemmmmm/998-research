# Implementation Spec: Phase E — Normalisation + Composite Scoring

> **Owner**: P2 (Yiming Wang)
> **Implementer**: P1 (Yucheng Tu)
> **Week**: 1–2
> **Phase**: [E — Normalization, Aggregation & Composite Scoring](../PROJECT_GAP_ANALYSIS_AND_PLAN.md#phase-e-normalization-aggregation--composite-scoring)
> **Proposal Ref**: [Group-1.pdf § 2.2](../Group-1.pdf) — "each sub-indicator is normalised to the 0–1 range...composite results are computed"
> **Status**: READY FOR IMPLEMENTATION

---

## 1. Objective

<!-- One sentence. What does this module do? -->

Normalise all evaluation sub-indicators to [0, 1] and compute per-dimension scores and a composite score for cross-pattern comparison.

---

## 2. Input

| Field Name | Source File | Source Class/Method | Current Value Range | Sample Value | Norm Strategy |
|------------|-------------|--------------------|--------------------|--------------|---------------|
| `success_rate()` | `src/evaluation/metrics.py` | `SuccessMetrics.success_rate` | 0.0–1.0 (float) | 0.75 | Option B (use directly) |
| `lenient_success_rate()` | `src/evaluation/metrics.py` | `SuccessMetrics.lenient_success_rate` | 0.0–1.0 (float) | 0.85 | Option B (use directly) ★ |
| `avg_latency()` | `src/evaluation/metrics.py` | `EfficiencyMetrics.avg_latency` | 0–∞ (seconds) | 12.4 | Option A (min-max, inverted) |
| `avg_total_tokens()` | `src/evaluation/metrics.py` | `EfficiencyMetrics.avg_total_tokens` | 0–∞ | 1523.0 | Option A (min-max, inverted) |
| `avg_steps()` | `src/evaluation/metrics.py` | `EfficiencyMetrics.avg_steps` | 0–∞ | 8.5 | Option A (min-max, inverted) ★ |
| `avg_tool_calls()` | `src/evaluation/metrics.py` | `EfficiencyMetrics.avg_tool_calls` | 0–∞ | 3.2 | Option A (min-max, inverted) ★ |
| `tao_cycle_counts` | `src/evaluation/metrics.py` | `EfficiencyMetrics.tao_cycle_counts` | List[int], mean then 0–∞ | [3, 2, 4] → mean 3.0 | Option A (min-max) ★ |
| `degradation_percentage` | `src/evaluation/metrics.py` | `RobustnessMetrics.degradation_percentage` | 0–100 (float) | 15.0 | Option B (÷100, inverted) |
| `tool_failure_recovery_rate` | `src/evaluation/metrics.py` | `RobustnessMetrics.tool_failure_recovery_rate` | 0.0–1.0 | 0.6 | Option B (use directly) |
| `avg_robustness_score()` | `src/evaluation/metrics.py` | `RobustnessMetrics.avg_robustness_score` | 0.0–1.0 | 0.72 | Option B (use directly) |
| `schema_compliance_rate()` | `src/evaluation/metrics.py` | `ControllabilityMetrics.schema_compliance_rate` | 0.0–1.0 | 0.80 | Option B (use directly) |
| `format_compliance_rate` | `src/evaluation/metrics.py` | `ControllabilityMetrics.format_compliance_rate` | 0.0–1.0 | 0.90 | Option B (use directly) |
| `trace_completeness` | `src/evaluation/controllability.py` | `ControllabilityResult.trace_completeness` | 0.0–1.0 | 0.60 | Option B (use directly, computed by Phase D2) |
| `policy_flag_rate` | `src/evaluation/controllability.py` | `ControllabilityResult.policy_flag_rate` | 0.0–1.0 | 0.25 | Option B (inverted: `1 - policy_flag_rate`, computed by Phase D2) |
| `resource_efficiency` | `src/evaluation/controllability.py` | `ControllabilityResult.resource_efficiency` | 0.0–1.0 | 0.72 | Option B (use directly, min-max + inversion already applied by Phase D2) |

> **★ Note**: Fields marked with ★ (`avg_steps`, `avg_tool_calls`) are normalised and stored for future use (e.g., weight sensitivity analysis or dimension formula refinement after the first complete data run) but are **not assigned to any dimension formula** in the current aggregation.

---

## 3. Output

<!-- Define the exact data structures P1 should create. -->

```python
@dataclass
class NormalizedDimensionScores:
    """Per-pattern normalised scores, grouped by dimension."""
    pattern_name: str                              # Pattern identifier
    dim4_success_efficiency: Optional[float]       # [0, 1] — Success & Efficiency
    dim6_robustness_scalability: Optional[float]   # [0, 1] — Robustness & Scalability
    dim7_controllability: Optional[float]          # [0, 1] — Controllability, Transparency & Resource Efficiency
    # Dimensions 1, 2, 3, 5 — placeholder for future phases
    dim1_reasoning_quality: Optional[float] = None
    dim2_cognitive_safety: Optional[float] = None
    dim3_action_decision_alignment: Optional[float] = None
    dim5_behavioural_safety: Optional[float] = None

    def available_scores(self) -> Dict[str, float]:
        """Return only non-None dimension scores."""
        ...

@dataclass
class CompositeScore:
    """Composite score computed from available dimension scores."""
    pattern_name: str                              # Pattern identifier
    dimension_scores: Dict[str, Optional[float]]   # dim name → score or None
    weights: Dict[str, float]                      # dim name → weight (uniform 1/N by default)
    composite: float                               # Weighted average of available dimensions
    available_dimensions: int                      # Number of non-None dimensions used
```

---

## 4. Computation Logic

### 4.1 Normalisation Formula

**Option A — Min-Max across patterns in the same evaluation run:**

```
normalised = (x - x_min) / (x_max - x_min)
```

**Option B — Fixed-range mapping (e.g. success_rate / 100):**

```
normalised = x / known_max
```

**P2 decision**: Hybrid strategy — select the normalisation approach based on indicator type.

- **Option B** for indicators with a known fixed range (success_rate, compliance_rate, etc. already in 0–1; degradation_percentage divided by 100)
- **Option A** for unbounded indicators (latency, tokens, steps, tool_calls), using min-max across patterns within a **single run**

For efficiency-type "lower-is-better" indicators (latency, tokens, steps, degradation), apply **inversion** after normalisation: `1 - normalised`, so that all indicators are unified as "higher-is-better".

**P2 justification**: The GAP_ANALYSIS document explicitly requires min-max normalisation for tokens and latency (see Phase E1). Indicators already in the 0–1 range need no further processing — using them directly preserves their absolute meaning (e.g., 0.8 = 80% success rate). Normalisation scope is limited to a single run, not across historical runs, ensuring each evaluation is independently reproducible.

### 4.2 Edge Cases

| Case | Expected Behaviour |
|------|--------------------|
| All patterns have the same value for a sub-indicator | Output **1.0** — no variance is treated as optimal, no penalty |
| Only one pattern in the run | Output **1.0** — no comparison baseline, treated as optimal |
| A sub-indicator is missing for one pattern (e.g. no TAO cycles for Reflex) | Output **None** — excluded from that pattern's dimension aggregation; dimension score is computed from remaining indicators with equal weights |
| Division by zero (x_max == x_min) | Output **1.0** — equivalent to the "all same value" case |

### 4.3 Dimension Score Aggregation

Sub-indicator weights default to uniform (1/N). To be refined after the first complete data run produces conclusions.

**Dim 1 — Reasoning Quality** (Cognitive Layer):

```
Not yet implemented, output None. Sub-indicators to be added in a future Phase.
```

**Dim 2 — Cognitive Safety & Constraint Adherence** (Cognitive Layer):

```
Not yet implemented, output None. Sub-indicators to be added in a future Phase.
```

**Dim 3 — Action-Decision Alignment** (Behavioural Layer):

```
Not yet implemented, output None. Sub-indicators to be added in a future Phase.
```

**Dim 4 — Success & Efficiency** (Behavioural Layer):

```
sub-indicators:
  - success_rate:      source = SuccessMetrics.success_rate(),          Option B (use directly)
  - norm_latency:      source = EfficiencyMetrics.avg_latency(),       Option A (min-max, inverted)
  - norm_tokens:       source = EfficiencyMetrics.avg_total_tokens(),   Option A (min-max, inverted)

dim4_score = (1/3) * success_rate + (1/3) * norm_latency + (1/3) * norm_tokens
```

**Dim 5 — Behavioural Safety** (Behavioural Layer):

```
Not yet implemented, output None. Sub-indicators to be added in a future Phase.
```

**Dim 6 — Robustness & Scalability** (Systemic Layer):

```
sub-indicators:
  - norm_degradation:  source = RobustnessMetrics.degradation_percentage, Option B (÷100, inverted)
  - recovery_rate:     source = RobustnessMetrics.tool_failure_recovery_rate, Option B (use directly)
  - robustness_score:  source = RobustnessMetrics.avg_robustness_score(),    Option B (use directly)

dim6_score = (1/3) * norm_degradation + (1/3) * recovery_rate + (1/3) * robustness_score
```

**Dim 7 — Controllability, Transparency & Resource Efficiency** (Systemic Layer):

> **Cross-ref**: Sub-indicators 1–3 are computed by [Phase D2](week1-2_phase-d2_controllability.md). Sub-indicators 4–5 come from existing `ControllabilityMetrics`.

```
sub-indicators:
  - trace_completeness:    source = ControllabilityResult.trace_completeness,          Option B (use directly)
  - policy_compliance:     source = 1 - ControllabilityResult.policy_flag_rate,        Option B (use directly)
  - resource_efficiency:   source = ControllabilityResult.resource_efficiency,          Option A (min-max, inverted) — computed in Phase D2
  - schema_compliance:     source = ControllabilityMetrics.schema_compliance_rate(),    Option B (use directly)
  - format_compliance:     source = ControllabilityMetrics.format_compliance_rate,      Option B (use directly)

dim7_score = (1/5) * trace_completeness + (1/5) * policy_compliance + (1/5) * resource_efficiency
           + (1/5) * schema_compliance  + (1/5) * format_compliance
```

Note: `ControllabilityMetrics.overall_controllability()` and `tool_policy_compliance_rate()` are **superseded** by this unified formula. `overall_controllability()` previously averaged schema + tool_policy + format, but tool_policy is now replaced by the trace-based `policy_compliance` from Phase D2, and the aggregation is handled here at the dimension level.

### 4.4 Composite Score

```
composite_score = sum(w_i * dim_i_score) / N  for all non-None dimensions
```

Where `N = available_dimensions` (number of non-None dimensions), and all `w_i` equal 1.

**Default weights**: Uniform distribution — currently only Dim 4/6/7 are available, so each weighs 1/3; automatically becomes 1/7 when all 7 dimensions are implemented.

**Weight rationale**: The Proposal does not specify differentiated weights. Uniform distribution is the fairest, most reproducible, and avoids subjective bias. Weights will be refined after the first complete data run produces experimental conclusions.

**Custom weights**: Supported via config by passing a custom weight dictionary `Dict[str, float]` to override the default uniform distribution.

---

## 5. Integration Points

| Action | File | What to Change |
|--------|------|----------------|
| CREATE | `src/evaluation/scoring.py` | New module: normalisation functions, dimension aggregation, composite scoring, custom weight support |
| MODIFY | `src/evaluation/evaluator.py` | Call `scoring.py` before `evaluate_multiple_patterns()` returns to compute normalised scores and composite scores |
| MODIFY | `src/evaluation/report_generator.py` | Add normalised score tables, dimension comparison, and composite ranking to JSON/Markdown/CSV output |
| MODIFY | `src/evaluation/visualization.py` | Add 7-dimension radar chart and normalised heatmap (as required by GAP_ANALYSIS) |

---

## 6. Verification Cases

<!-- P2: provide concrete input → expected output pairs that P1 can directly copy into test cases. -->

### Case 1: Min-max normalisation (unbounded indicator)

```
Input:  3 patterns, avg_latency (seconds) = [5.0, 10.0, 15.0]
Step 1: min=5.0, max=15.0
Step 2: min-max → [0.0, 0.5, 1.0]
Step 3: invert (lower-is-better) → [1.0, 0.5, 0.0]
Expected normalised: [1.0, 0.5, 0.0]
```

### Case 2: All same value

```
Input:  3 patterns, avg_latency (seconds) = [8.0, 8.0, 8.0]
Step 1: min=8.0, max=8.0, x_max == x_min → division by zero
Step 2: edge case → output 1.0
Expected normalised: [1.0, 1.0, 1.0]
```

### Case 3: Composite score with uniform weights (3 available dimensions)

```
Input:  dim_scores = {dim4: 0.8, dim6: 0.6, dim7: 0.7}
        (dim1–dim3, dim5 = None)
Step 1: available_dimensions = 3
Step 2: composite = (0.8 + 0.6 + 0.7) / 3 = 0.7
Expected composite: 0.7
```

### Case 4: Missing dimension (partial availability)

```
Input:  dim_scores = {dim4: 0.8, dim6: None, dim7: 0.7}
Step 1: skip None → available_dimensions = 2
Step 2: composite = (0.8 + 0.7) / 2 = 0.75
Expected composite: 0.75
```

### Case 5: Dimension aggregation with missing sub-indicator

```
Input:  Dim 6 sub-indicators: norm_degradation=0.9, recovery_rate=None, robustness_score=0.6
Step 1: skip None → 2 valid indicators
Step 2: dim6_score = (0.9 + 0.6) / 2 = 0.75
Expected dim6_score: 0.75
```

---

## 7. Open Questions (Resolved)

1. **Normalisation scope**: Per single run only, not across historical runs. Each evaluation is independently reproducible.
2. **Custom weights**: Supported via config by passing `Dict[str, float]` to override default uniform weights.
3. **Sub-indicator weights within dimensions**: Default to uniform (1/N). To be refined after the first complete data run produces conclusions for detailed adjustment and evaluation.

---

## Checklist Before Handing to P1

- [x] Every field in Section 2 has a real field name from the codebase (not a guess)
- [x] Every formula in Section 4 is unambiguous (P1 can write `=` directly)
- [x] Every edge case in Section 4.2 has a defined behaviour
- [x] Every verification case in Section 6 has a concrete expected output
- [x] Section 5 lists exact file paths to create/modify
- [x] Document is under 5 pages
