# Implementation Spec: Phase E — Normalisation + Composite Scoring

> **Owner**: P2 (Yiming Wang)
> **Implementer**: P1 (Yucheng Tu)
> **Week**: 1–2
> **Phase**: [E — Normalization, Aggregation & Composite Scoring](../PROJECT_GAP_ANALYSIS_AND_PLAN.md#phase-e-normalization-aggregation--composite-scoring)
> **Proposal Ref**: [Group-1.pdf § 2.2](../Group-1.pdf) — "each sub-indicator is normalised to the 0–1 range...composite results are computed"
> **Status**: DRAFT — awaiting P2 completion

---

## 1. Objective

<!-- One sentence. What does this module do? -->

Normalise all evaluation sub-indicators to [0, 1] and compute per-dimension scores and a composite score for cross-pattern comparison.

---

## 2. Input

<!-- List every field P1 needs to read. Include: field name, source file, current value range, and a sample value from an actual run. -->
<!-- P2: Run `python run_evaluation.py --mode quick` and inspect the output JSON to fill this section. -->

| Field Name | Source File | Source Class/Method | Current Value Range | Sample Value |
|------------|-------------|--------------------|--------------------|-------------|
| `success_rate_strict` | `src/evaluation/metrics.py` | `SuccessMetrics` | 0–100 (%) | <!-- P2 fills --> |
| `success_rate_lenient` | `src/evaluation/metrics.py` | `SuccessMetrics` | 0–100 (%) | <!-- P2 fills --> |
| `avg_latency_ms` | `src/evaluation/metrics.py` | `EfficiencyMetrics` | 0–∞ (ms) | <!-- P2 fills --> |
| `avg_total_tokens` | `src/evaluation/metrics.py` | `EfficiencyMetrics` | 0–∞ | <!-- P2 fills --> |
| `tao_cycle_counts` | `src/evaluation/metrics.py` | `EfficiencyMetrics` | List[int] | <!-- P2 fills --> |
| `robustness_degradation` | `src/evaluation/metrics.py` | `RobustnessMetrics` | 0–1 | <!-- P2 fills --> |
| <!-- add more rows as needed --> | | | | |

---

## 3. Output

<!-- Define the exact data structures P1 should create. -->

```python
@dataclass
class NormalizedDimensionScores:
    # P2: fill in every field with name, type, range, and description
    pass

@dataclass
class CompositeScore:
    # P2: fill in fields
    pass
```

---

## 4. Computation Logic

### 4.1 Normalisation Formula

<!-- P2: choose one and explain why. -->

**Option A — Min-Max across patterns in the same evaluation run:**

```
normalised = (x - x_min) / (x_max - x_min)
```

**Option B — Fixed-range mapping (e.g. success_rate / 100):**

```
normalised = x / known_max
```

**P2 decision**: <!-- which option, or a mix? -->

**P2 justification**: <!-- why? cite Proposal if relevant -->

### 4.2 Edge Cases

<!-- P2 MUST define behaviour for each case below. P1 cannot guess. -->

| Case | Expected Behaviour |
|------|--------------------|
| All patterns have the same value for a sub-indicator | <!-- P2 fills: output 1.0? 0.5? 0.0? --> |
| Only one pattern in the run | <!-- P2 fills --> |
| A sub-indicator is missing for one pattern (e.g. no TAO cycles for Reflex) | <!-- P2 fills --> |
| Division by zero (x_max == x_min) | <!-- P2 fills --> |

### 4.3 Dimension Score Aggregation

<!-- P2: for each dimension, list which sub-indicators map to it and how they combine. -->

**Dim 4 — Success & Efficiency:**

```
sub-indicators:
  - success_rate_strict: source = SuccessMetrics, normalise via ___
  - normalised_cost: = w1 * norm(tokens) + w2 * norm(latency), w1 = ___, w2 = ___

dim4_score = ___ (formula)
```

<!-- P2: repeat for all 7 dimensions, even if some are placeholders for now -->

### 4.4 Composite Score

```
composite_score = sum(w_i * dim_i_score) for i in 1..7
```

**Default weights**: <!-- P2 fills: uniform 1/7 each? or weighted? -->

**Weight rationale**: <!-- P2 fills: cite Proposal -->

---

## 5. Integration Points

<!-- P2: list every file P1 needs to create or modify. -->

| Action | File | What to Change |
|--------|------|----------------|
| CREATE | `src/evaluation/scoring.py` | New module with normalisation + composite logic |
| MODIFY | `src/evaluation/evaluator.py` | Call scoring after all pattern runs complete |
| MODIFY | `src/evaluation/report_generator.py` | Add normalised scores and composite to JSON/Markdown output |

---

## 6. Verification Cases

<!-- P2: provide concrete input → expected output pairs that P1 can directly copy into test cases. -->

### Case 1: Basic min-max normalisation

```
Input: 3 patterns, success_rate_strict = [80, 60, 40]
Expected normalised: [___, ___, ___]
```

### Case 2: All same value

```
Input: 3 patterns, success_rate_strict = [75, 75, 75]
Expected normalised: [___, ___, ___]
```

### Case 3: Composite score with uniform weights

```
Input: dim_scores = [0.8, 0.6, 0.7, 0.9, 0.5, 0.4, 0.75]
Expected composite: ___
```

### Case 4: Missing dimension

```
Input: dim_scores = [0.8, None, 0.7, 0.9, 0.5, 0.4, 0.75]
Expected behaviour: ___
```

---

## 7. Open Questions

<!-- P2: list anything you are unsure about. P1 and the team will resolve these before implementation. -->

1. <!-- e.g. Should normalisation be per-run or across historical runs? -->
2. <!-- e.g. Should we support custom weight profiles? -->

---

## Checklist Before Handing to P1

- [ ] Every field in Section 2 has a real field name from the codebase (not a guess)
- [ ] Every formula in Section 4 is unambiguous (P1 can write `=` directly)
- [ ] Every edge case in Section 4.2 has a defined behaviour
- [ ] Every verification case in Section 6 has a concrete expected output
- [ ] Section 5 lists exact file paths to create/modify
- [ ] Document is under 5 pages
