# Implementation Spec: Phase D2 — Controllability, Transparency & Resource Efficiency

> **Owner**: plan to be P3 (Kapila Wijetunge) -> but write by P1 (Yucheng Tu)
> **Implementer**: P1 (Yucheng Tu)
> **Week**: 1–2
> **Phase**: [D — Systemic Layer Enhancement (Dim 7)](../PROJECT_GAP_ANALYSIS_AND_PLAN.md#phase-d-systemic-layer-enhancement-dimensions-6--7)
> **Proposal Ref**: [Group-1.pdf § 2.2.3 Dim7](../Group-1.pdf)
> **Status**: DRAFT — awaiting P3 completion

---

## 1. Objective

<!-- One sentence. What does this module do? -->

Compute trace completeness, policy-flag frequency, and resource efficiency scores for Dimension 7 evaluation.

---

## 2. Input

<!-- List every field P1 needs to read. Include: field name, source file, current value range, and a sample value from an actual run. -->
<!-- P3: read `src/evaluation/trace.py` and `src/evaluation/metrics.py` to fill this section. -->

| Field Name | Source File | Source Class/Method | Current Value Range | Sample Value |
|------------|-------------|--------------------|--------------------|-------------|
| `steps` | `src/evaluation/trace.py` | `AgentTrace.steps` | List[StepRecord] | <!-- P3 fills --> |
| `tao_cycles` | `src/evaluation/trace.py` | `AgentTrace.tao_cycles` | 0–∞ (int) | <!-- P3 fills --> |
| `total_think_steps` | `src/evaluation/trace.py` | `AgentTrace.total_think_steps` | 0–∞ (int) | <!-- P3 fills --> |
| `total_act_steps` | `src/evaluation/trace.py` | `AgentTrace.total_act_steps` | 0–∞ (int) | <!-- P3 fills --> |
| `total_observe_steps` | `src/evaluation/trace.py` | `AgentTrace.total_observe_steps` | 0–∞ (int) | <!-- P3 fills --> |
| `total_tokens` | `src/evaluation/trace.py` | `AgentTrace.total_tokens` | 0–∞ (int) | <!-- P3 fills --> |
| <!-- add more rows as needed --> | | | | |

---

## 3. Output

<!-- Define the exact data structures P1 should create. -->

```python
@dataclass
class ControllabilityResult:
    trace_completeness: float          # [0, 1] — proportion of steps in complete TAO cycles
    policy_flag_rate: float            # [0, 1] — proportion of tasks with policy violations
    resource_efficiency: float         # [0, 1] — normalised token/time cost
    controllability_score: float       # [0, 1] — weighted combination
    # P3: add or adjust fields as needed
```

---

## 4. Computation Logic

### 4.1 Trace Completeness

<!-- P3 MUST choose one definition and explain why. -->

**Option A — TAO cycle proportion:**

```
trace_completeness = (tao_cycles * 3) / len(steps)
```

**Option B — TAO step type coverage:**

```
trace_completeness = (total_think_steps + total_act_steps + total_observe_steps) / len(steps)
```

**P3 decision**: <!-- which option? -->

**P3 justification**: <!-- why? how does it relate to the Proposal's definition? -->

### 4.2 Policy Flag Rate

<!-- P3: define exactly how to compute this. -->

```
policy_flag_rate = ___
```

**Data source**: <!-- where do policy violations come from? `ControllabilityMetrics.unauthorized_tool_uses`? Or computed from `ToolCallRecord` vs `TestTask.policy.tool_whitelist`? -->

### 4.3 Resource Efficiency

<!-- P3 MUST choose one definition. -->

**Option A — Token inverse:**

```
resource_efficiency = 1 - norm(total_tokens)
  where norm = min-max across patterns
```

**Option B — Success-per-token:**

```
resource_efficiency = success_rate / norm(total_tokens)
```

**P3 decision**: <!-- which option? -->

**P3 justification**: <!-- cite Proposal -->

### 4.4 Dimension 7 Aggregation

```
controllability_score =
  w1 * trace_completeness +
  w2 * (1 - policy_flag_rate) +
  w3 * resource_efficiency
```

**Weights**: w1 = ___, w2 = ___, w3 = ___

**Weight rationale**: <!-- P3 fills -->

### 4.5 Edge Cases

| Case | Expected Behaviour |
|------|--------------------|
| Reflex pattern: 0 TAO cycles, 3 steps | <!-- P3 fills --> |
| All patterns have the same total_tokens | <!-- P3 fills --> |
| No policy violations for any pattern | <!-- P3 fills --> |
| Task failed (no trace available) | <!-- P3 fills --> |

---

## 5. Integration Points

| Action | File | What to Change |
|--------|------|----------------|
| MODIFY | `src/evaluation/metrics.py` | Update `ControllabilityMetrics` with new fields |
| MODIFY | `src/evaluation/evaluator.py` | Compute controllability after trace extraction |
| MODIFY | `src/evaluation/report_generator.py` | Add Dim7 metrics to output |

---

## 6. Verification Cases

### Case 1: ReAct trace with complete TAO cycles

```
Input: 10 steps, 3 complete TAO cycles
Expected trace_completeness: ___
```

### Case 2: Reflex trace with no TAO cycles

```
Input: 3 steps (INPUT, THINK-synthetic, OUTPUT), 0 TAO cycles
Expected trace_completeness: ___
```

### Case 3: Resource efficiency normalisation

```
Input: 4 patterns, total_tokens = [500, 1200, 3000, 800]
Expected resource_efficiency: [___, ___, ___, ___]
```

### Case 4: No policy violations

```
Input: all patterns have 0 unauthorized_tool_uses
Expected policy_flag_rate: ___
Expected contribution to controllability_score: ___
```

---

## 7. Open Questions

1. <!-- e.g. Should trace_completeness count INPUT and OUTPUT steps in the denominator? -->
2. <!-- e.g. How should we handle patterns that don't use tools (no ACT/OBSERVE)? -->

---

## Checklist Before Handing to P1

- [ ] Every field in Section 2 has a real field name from the codebase (not a guess)
- [ ] Every formula in Section 4 is unambiguous (P1 can write `=` directly)
- [ ] Every edge case in Section 4.5 has a defined behaviour
- [ ] Every verification case in Section 6 has a concrete expected output
- [ ] Section 5 lists exact file paths to create/modify
- [ ] Document is under 5 pages
