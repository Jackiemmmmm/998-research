# Implementation Plan: Phase D2 + Phase E (Week 1–2)

> **Author**: P1 (Yucheng Tu)
> **Date**: 2026-03-19
> **Specs**: [Phase D2 Controllability](./specs/week1-2_phase-d2_controllability.md) | [Phase E Normalisation](./specs/week1-2_phase-e_normalisation.md)
> **Status**: IN PROGRESS

---

## 1. Implementation Order & Dependencies

```
Step 1:  CREATE  src/evaluation/controllability.py       (Phase D2 core)
Step 2:  MODIFY  src/evaluation/evaluator.py             (Integrate D2, replace stub)
Step 3:  MODIFY  src/evaluation/metrics.py               (Fix unauthorized_tool_uses)
Step 4:  MODIFY  src/evaluation/report_generator.py      (D2 sub-indicator output)
Step 5:  CREATE  src/evaluation/scoring.py               (Phase E core + ★ reserve indicators)
Step 6:  MODIFY  src/evaluation/evaluator.py             (Integrate E)
Step 7:  MODIFY  src/evaluation/report_generator.py      (E normalised + composite output)
Step 8:  MODIFY  src/evaluation/visualization.py         (7-dim radar + normalised heatmap)
Step 9:  MODIFY  src/evaluation/__init__.py              (Export new modules)
Step 10: CREATE  tests/unit_tests/test_controllability.py (D2 Cases 1–5)
Step 11: CREATE  tests/unit_tests/test_scoring.py        (E Cases 1–5 + D2 Case 6 cross-validation)
Step 12: End-to-end verification: run_evaluation.py --mode full
```

---

## 2. Phase D2 — Controllability (Steps 1–4)

### 2.1 CREATE `src/evaluation/controllability.py`

**Dataclass**: `ControllabilityResult`
- `pattern_name: str`
- `trace_completeness: float` — `(tao_cycles * 3) / len(steps)`, 0.0 if no steps
- `tao_cycles: int` — raw count
- `total_steps: int`
- `policy_flag_rate: float` — `tasks_with_violations / total_tool_tasks`, 0.0 if no tool tasks
- `total_violations: int`
- `tasks_with_violations: int`
- `resource_efficiency: float` — `1 - min_max_norm(total_tokens)` across patterns

**Functions**:
- `compute_trace_completeness(trace: AgentTrace) -> Tuple[float, int, int]`
- `compute_policy_violations(results: List[TaskResult], tasks: List[TestTask]) -> Tuple[float, int, int]`
- `compute_resource_efficiency(all_pattern_tokens: Dict[str, float]) -> Dict[str, float]`
- `compute_controllability_result(pattern_name, results, tasks, all_pattern_tokens) -> ControllabilityResult`

**Edge Cases**:
| Case | Behaviour |
|------|-----------|
| Reflex: 0 TAO cycles, 3 steps | `trace_completeness = 0.0` |
| All patterns same total_tokens | `resource_efficiency = 1.0` for all |
| No policy violations | `policy_flag_rate = 0.0` |
| Task failed (no trace) | Exclude from aggregation |
| Task has no `policy.tool_whitelist` | Skip policy check |
| Only one pattern | `resource_efficiency = 1.0` |

### 2.2 MODIFY `src/evaluation/evaluator.py`

- Replace stub at `_collect_controllability_metrics()` line 475–479: actually check `ToolCallRecord.tool_name` against `TestTask.policy["tool_whitelist"]`
- After `evaluate_multiple_patterns()` collects all pattern metrics, call `compute_resource_efficiency()` across patterns
- Store `ControllabilityResult` in `PatternMetrics`

### 2.3 MODIFY `src/evaluation/metrics.py`

- Add `controllability_result: Optional[ControllabilityResult] = None` field to `PatternMetrics`
- Include `ControllabilityResult` data in `PatternMetrics.to_dict()` and `summary()`

### 2.4 MODIFY `src/evaluation/report_generator.py`

- Add D2 sub-indicators (trace_completeness, policy_flag_rate, resource_efficiency) to:
  - JSON report: under `individual_metrics`
  - Markdown report: new "Controllability Extended" subsection
  - CSV: additional columns

---

## 3. Phase E — Normalisation + Composite Scoring (Steps 5–8)

### 3.1 CREATE `src/evaluation/scoring.py`

**Normalisation Functions**:
- `normalize_min_max(values: List[float], invert: bool = False) -> List[float]`
  - Edge case: all same value → return `[1.0, ...]`
  - Edge case: single value → return `[1.0]`
- `normalize_fixed_range(value: float, invert: bool = False) -> float`
  - For values already in [0, 1]: use directly
  - For `degradation_percentage`: divide by 100 then invert

**Dataclass**: `NormalizedDimensionScores`
- `pattern_name: str`
- `dim4_success_efficiency: Optional[float]` — `(1/3) * success_rate + (1/3) * norm_latency + (1/3) * norm_tokens`
- `dim6_robustness_scalability: Optional[float]` — `(1/3) * norm_degradation + (1/3) * recovery_rate + (1/3) * robustness_score`
- `dim7_controllability: Optional[float]` — `(1/5) * 5 sub-indicators`
- `dim1_reasoning_quality: Optional[float] = None` (future)
- `dim2_cognitive_safety: Optional[float] = None` (future)
- `dim3_action_decision_alignment: Optional[float] = None` (future)
- `dim5_behavioural_safety: Optional[float] = None` (future)
- **★ Reserve indicators** (normalised but not in any dimension):
  - `norm_avg_steps: Optional[float] = None` — Option A (min-max, inverted)
  - `norm_avg_tool_calls: Optional[float] = None` — Option A (min-max, inverted)
  - `norm_tao_cycles: Optional[float] = None` — Option A (min-max, NOT inverted)
- `available_scores() -> Dict[str, float]`

**Dataclass**: `CompositeScore`
- `pattern_name: str`
- `dimension_scores: Dict[str, Optional[float]]`
- `weights: Dict[str, float]` — default uniform 1/N
- `composite: float` — weighted average of available dimensions
- `available_dimensions: int`

**Aggregation Functions**:
- `compute_dim4(pattern_metrics_list) -> Dict[str, Optional[float]]`
- `compute_dim6(pattern_metrics_list) -> Dict[str, Optional[float]]`
- `compute_dim7(pattern_metrics_list, controllability_results) -> Dict[str, Optional[float]]`
- `compute_composite(dim_scores, weights=None) -> CompositeScore`
- `compute_all_scores(pattern_metrics_dict, controllability_results) -> Tuple[Dict[str, NormalizedDimensionScores], Dict[str, CompositeScore]]`

**Edge Cases**:
| Case | Behaviour |
|------|-----------|
| All patterns same value for sub-indicator | Output `1.0` |
| Only one pattern | Output `1.0` |
| Sub-indicator missing for a pattern | `None`, excluded from dimension avg |
| Division by zero (x_max == x_min) | Output `1.0` |

### 3.2 MODIFY `src/evaluation/evaluator.py`

- In `evaluate_multiple_patterns()`: after collecting all PatternMetrics, call `compute_all_scores()` and attach results

### 3.3 MODIFY `src/evaluation/report_generator.py`

- Add normalised dimension score table to JSON/Markdown/CSV
- Add composite score ranking

### 3.4 MODIFY `src/evaluation/visualization.py`

- Upgrade `plot_radar_comparison()` to use 7-dimension radar (with available dims)
- Add `plot_normalised_heatmap()` for normalised dimension scores

---

## 4. Unit Tests (Steps 10–11)

### 4.1 `tests/unit_tests/test_controllability.py`

| Test | Input | Expected |
|------|-------|----------|
| Case 1: ReAct trace completeness | 10 steps, 2 TAO cycles | `0.6` |
| Case 2: Reflex trace completeness | 3 steps, 0 TAO cycles | `0.0` |
| Case 3: Resource efficiency | tokens [500, 1200, 3000, 800] | `[1.0, 0.72, 0.0, 0.88]` |
| Case 4: No policy violations | 0 violations, 4 tool tasks | `flag_rate = 0.0` |
| Case 5: Policy violation detected | C1 has 1 violation, C2 has 0 | `flag_rate = 0.5` |

### 4.2 `tests/unit_tests/test_scoring.py`

| Test | Input | Expected |
|------|-------|----------|
| Case 1: Min-max normalisation | latency [5, 10, 15] | `[1.0, 0.5, 0.0]` |
| Case 2: All same value | latency [8, 8, 8] | `[1.0, 1.0, 1.0]` |
| Case 3: Composite (3 dims) | dim4=0.8, dim6=0.6, dim7=0.7 | `composite = 0.7` |
| Case 4: Partial availability | dim4=0.8, dim6=None, dim7=0.7 | `composite = 0.75` |
| Case 5: Missing sub-indicator | norm_deg=0.9, recovery=None, robust=0.6 | `dim6 = 0.75` |
| Case 6: D2↔E cross-validation | tc=0.6, pfr=0.0, re=0.8, sc=0.9, fc=0.7 | `dim7 = 0.80` |

---

## 5. End-to-End Verification (Step 12)

**Command**: `python run_evaluation.py --mode full`

**Expected Outputs**:
- All patterns run successfully with scores
- JSON/Markdown/CSV reports include:
  - D2 sub-indicators: `trace_completeness`, `policy_flag_rate`, `resource_efficiency`
  - E normalised dimension scores: `dim4`, `dim6`, `dim7`
  - E composite score and ranking
  - ★ Reserve indicators: `norm_avg_steps`, `norm_avg_tool_calls`, `norm_tao_cycles`
- Visualisation: updated radar chart (7-dim capable), normalised heatmap
- Unit tests: all pass (`pytest tests/unit_tests/test_controllability.py tests/unit_tests/test_scoring.py -v`)

---

## 6. Files Changed Summary

| Action | File | Phase |
|--------|------|-------|
| CREATE | `src/evaluation/controllability.py` | D2 |
| CREATE | `src/evaluation/scoring.py` | E |
| CREATE | `tests/unit_tests/test_controllability.py` | D2 |
| CREATE | `tests/unit_tests/test_scoring.py` | E |
| MODIFY | `src/evaluation/evaluator.py` | D2 + E |
| MODIFY | `src/evaluation/metrics.py` | D2 |
| MODIFY | `src/evaluation/report_generator.py` | D2 + E |
| MODIFY | `src/evaluation/visualization.py` | E |
| MODIFY | `src/evaluation/__init__.py` | D2 + E |
