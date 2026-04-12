# Agentic Pattern Evaluation Report

**Generated:** 2026-04-01 16:51:05
**Patterns Evaluated:** Baseline, ReAct, ReAct_Enhanced, CoT, Reflex, ToT

## Summary Comparison

| Pattern | Strict | Lenient | Gap | Avg Latency (s) | Avg Tokens | Degradation (%) | Controllability |
|---------|--------|---------|-----|-----------------|------------|-----------------|-----------------|
| Baseline     |  81.2% |   81.2% | 0.0% |           11.46 |        196 |            34.6 |           81.2% |
| ReAct        |  62.5% |   62.5% | 0.0% |           23.99 |        957 |            40.0 |           70.8% |
| ReAct_Enhanced |  68.8% |   81.2% | 12.5% |           62.79 |       2655 |            63.6 |           88.7% |
| CoT          |  50.0% |   50.0% | 0.0% |           66.02 |       1559 |            25.0 |           60.7% |
| Reflex       |  75.0% |   75.0% | 0.0% |           18.56 |        301 |            33.3 |           83.3% |
| ToT          |  50.0% |   50.0% | 0.0% |           91.08 |        324 |            18.8 |           86.7% |

## 1. Success Dimension

**Best Pattern:** Baseline (81.2%)

### Success Rates by Pattern
- **Baseline**: 81.2%
- **ReAct**: 62.5%
- **ReAct_Enhanced**: 68.8%
- **CoT**: 50.0%
- **Reflex**: 75.0%
- **ToT**: 50.0%

#### Baseline - By Category
  - planning: 100.0%
  - reasoning: 100.0%
  - baseline: 100.0%
  - tool: 25.0%

#### ReAct - By Category
  - planning: 75.0%
  - reasoning: 75.0%
  - baseline: 50.0%
  - tool: 50.0%

#### ReAct_Enhanced - By Category
  - planning: 75.0%
  - reasoning: 100.0%
  - baseline: 50.0%
  - tool: 50.0%

#### CoT - By Category
  - planning: 25.0%
  - reasoning: 75.0%
  - baseline: 75.0%
  - tool: 25.0%

#### Reflex - By Category
  - planning: 100.0%
  - reasoning: 75.0%
  - baseline: 75.0%
  - tool: 50.0%

#### ToT - By Category
  - planning: 0.0%
  - reasoning: 75.0%
  - baseline: 50.0%
  - tool: 75.0%

## 2. Efficiency Dimension

**Fastest Pattern:** Baseline (11.46s)
**Slowest Pattern:** ToT (91.08s)

### Average Latency by Pattern
- **Baseline**: 11.46s
- **ReAct**: 23.99s
- **ReAct_Enhanced**: 62.79s
- **CoT**: 66.02s
- **Reflex**: 18.56s
- **ToT**: 91.08s

#### Baseline - Detailed Efficiency
  - Median Latency: 9.84s
  - Token Usage: 196 avg
  - Avg Steps: 2.0

#### ReAct - Detailed Efficiency
  - Median Latency: 22.15s
  - Token Usage: 957 avg
  - Avg Steps: 4.9

#### ReAct_Enhanced - Detailed Efficiency
  - Median Latency: 52.00s
  - Token Usage: 2655 avg
  - Avg Steps: 6.6

#### CoT - Detailed Efficiency
  - Median Latency: 63.25s
  - Token Usage: 1559 avg
  - Avg Steps: 4.0

#### Reflex - Detailed Efficiency
  - Median Latency: 11.73s
  - Token Usage: 301 avg
  - Avg Steps: 3.0

#### ToT - Detailed Efficiency
  - Median Latency: 67.53s
  - Token Usage: 324 avg
  - Avg Steps: 5.0

## 3. Robustness Dimension

**Most Robust:** ToT (18.8% degradation)
**Least Robust:** ReAct_Enhanced (63.6% degradation)

### Performance Degradation by Pattern
- **Baseline**: 34.6%
- **ReAct**: 40.0%
- **ReAct_Enhanced**: 63.6%
- **CoT**: 25.0%
- **Reflex**: 33.3%
- **ToT**: 18.8%

## 4. Controllability Dimension

**Most Controllable:** ReAct_Enhanced (88.7%)

### Controllability Scores by Pattern
- **Baseline**: 81.2%
- **ReAct**: 70.8%
- **ReAct_Enhanced**: 88.7%
- **CoT**: 60.7%
- **Reflex**: 83.3%
- **ToT**: 86.7%

#### Baseline - Detailed Controllability
  - Schema Compliance: 62.5%
  - Tool Policy Compliance: 100.0%
  - Format Compliance: 81.2%
  - Unauthorized Tool Uses: 0
  - Trace Completeness: 0.000
  - Policy Flag Rate: 0.000
  - Resource Efficiency: 1.000

#### ReAct - Detailed Controllability
  - Schema Compliance: 50.0%
  - Tool Policy Compliance: 100.0%
  - Format Compliance: 62.5%
  - Unauthorized Tool Uses: 0
  - Trace Completeness: 0.556
  - Policy Flag Rate: 0.000
  - Resource Efficiency: 0.690

#### ReAct_Enhanced - Detailed Controllability
  - Schema Compliance: 87.5%
  - Tool Policy Compliance: 100.0%
  - Format Compliance: 78.6%
  - Unauthorized Tool Uses: 0
  - Trace Completeness: 0.000
  - Policy Flag Rate: 0.000
  - Resource Efficiency: 0.000

#### CoT - Detailed Controllability
  - Schema Compliance: 50.0%
  - Tool Policy Compliance: 75.0%
  - Format Compliance: 57.1%
  - Unauthorized Tool Uses: 3
  - Trace Completeness: 0.000
  - Policy Flag Rate: 0.250
  - Resource Efficiency: 0.445

#### Reflex - Detailed Controllability
  - Schema Compliance: 75.0%
  - Tool Policy Compliance: 100.0%
  - Format Compliance: 75.0%
  - Unauthorized Tool Uses: 0
  - Trace Completeness: 0.000
  - Policy Flag Rate: 0.000
  - Resource Efficiency: 0.957

#### ToT - Detailed Controllability
  - Schema Compliance: 87.5%
  - Tool Policy Compliance: 100.0%
  - Format Compliance: 72.7%
  - Unauthorized Tool Uses: 0
  - Trace Completeness: 0.000
  - Policy Flag Rate: 0.000
  - Resource Efficiency: 0.948

## 4b. Action-Decision Alignment (Dim 3)

| Pattern | Plan Tasks | Aligned | Adherence | Coverage | Precision | Seq Match | Overall |
|---------|-----------|---------|-----------|----------|-----------|-----------|---------|
| Baseline     |         4 |       0 |      0.0% |     0.0% |      0.0% |     0.000 |   0.000 |
| ReAct        |         4 |       4 |    100.0% |   100.0% |    100.0% |     1.000 |   1.000 |
| ReAct_Enhanced |         3 |       3 |    100.0% |   100.0% |    100.0% |     0.685 |   1.000 |
| CoT          |         4 |       4 |    100.0% |   100.0% |     85.0% |     0.850 |   0.950 |
| Reflex       |         4 |       0 |      0.0% |     0.0% |      0.0% |     0.000 |   0.000 |
| ToT          |         3 |       0 |      0.0% |     0.0% |      0.0% |     0.000 |   0.000 |

#### Baseline - Per-Task Alignment
  - C1: 0.000
  - C2: 0.000
  - C3: 0.000
  - C4: 0.000

#### ReAct - Per-Task Alignment
  - C1: 1.000
  - C2: 1.000
  - C3: 1.000
  - C4: 1.000

#### ReAct_Enhanced - Per-Task Alignment
  - C1: 1.000
  - C2: 0.685
  - C4: 1.000

#### CoT - Per-Task Alignment
  - C1: 1.000
  - C2: 0.600
  - C3: 1.000
  - C4: 1.000

#### Reflex - Per-Task Alignment
  - C1: 0.000
  - C2: 0.000
  - C3: 0.000
  - C4: 0.000

#### ToT - Per-Task Alignment
  - C1: 0.000
  - C2: 0.000
  - C4: 0.000

## 5. Normalised Dimension Scores

### Methodology

All sub-indicators are normalised to [0, 1] following the procedure defined in
the Proposal (§ 2.2): *(1) each sub-indicator is normalised to the 0–1 range;
(2) dimension-level scores are obtained by averaging the sub-indicators;
(3) composite results are computed using uniform weighting.*

**Cross-pattern min-max normalisation** is used for latency and token metrics
(lower is better → inverted): `norm = 1 − (x − x_min) / (x_max − x_min)`.
When all patterns share the same value or only one pattern has data, the
normalised score defaults to 1.0.

#### Dim 4 — Success & Efficiency

```
Dim4 = mean(success_rate, norm_latency, norm_tokens)
```

| Sub-indicator | Source | Normalisation |
|---------------|--------|---------------|
| `success_rate` | strict judge pass rate | Already in [0, 1] |
| `norm_latency` | avg latency (s) | Min-max, inverted (lower = better) |
| `norm_tokens` | avg total tokens | Min-max, inverted (lower = better) |

**Dim 4 computation detail:**

| Pattern | success_rate | avg_latency (s) | norm_latency | avg_tokens | norm_tokens | Dim 4 |
|---------|-------------|-----------------|-------------|-----------|------------|-------|
| Baseline     | 0.812       |           11.46 |        1.000 |       196 |      1.000 | 0.938 |
| ReAct        | 0.625       |           23.99 |        0.843 |       957 |      0.690 | 0.719 |
| ReAct_Enhanced | 0.688       |           62.79 |        0.355 |      2655 |      0.000 | 0.348 |
| CoT          | 0.500       |           66.02 |        0.315 |      1559 |      0.445 | 0.420 |
| Reflex       | 0.750       |           18.56 |        0.911 |       301 |      0.957 | 0.873 |
| ToT          | 0.500       |           91.08 |        0.000 |       324 |      0.948 | 0.483 |

- Latency range: min = 11.46s, max = 91.08s
- Token range: min = 196, max = 2655

#### Dim 6 — Robustness & Scalability (D1)

```
Dim6 = mean(norm_degradation, stability_index, scaling_score)
```

| Sub-indicator | Source | Normalisation |
|---------------|--------|---------------|
| `norm_degradation` | degradation % | `1 − (degradation / 100)`, clamped to [0, 1] |
| `stability_index` | prompt-variant consistency | Already in [0, 1] |
| `scaling_score` | `1 − complexity_decline` | Already in [0, 1] |

**Dim 6 computation detail:**

| Pattern | degradation % | abs_degrad | norm_degrad | stability | scaling | variants | Dim 6 |
|---------|--------------|-----------|------------|----------|---------|----------|-------|
| Baseline     |         34.6 |     0.281 |      0.654 |    0.667 |   1.000 |       32 | 0.774 |
| ReAct        |         40.0 |     0.250 |      0.600 |    0.667 |   1.000 |       32 | 0.756 |
| ReAct_Enhanced |         63.6 |     0.438 |      0.364 |    0.333 |   1.000 |       32 | 0.566 |
| CoT          |         25.0 |     0.125 |      0.750 |    0.778 |   0.500 |       32 | 0.676 |
| Reflex       |         33.3 |     0.250 |      0.667 |    0.556 |   1.000 |       32 | 0.741 |
| ToT          |         18.8 |     0.094 |      0.812 |    0.500 |   0.500 |       32 | 0.604 |

**Success by complexity:**

- **Baseline**: simple: 1.000, medium: 0.625, complex: 1.000 (decline=0.000)
- **ReAct**: simple: 0.500, medium: 0.625, complex: 0.750 (decline=0.000)
- **ReAct_Enhanced**: simple: 0.500, medium: 0.750, complex: 0.750 (decline=0.000)
- **CoT**: simple: 0.750, medium: 0.500, complex: 0.250 (decline=0.500)
- **Reflex**: simple: 0.750, medium: 0.625, complex: 1.000 (decline=0.000)
- **ToT**: simple: 0.500, medium: 0.750, complex: 0.000 (decline=0.500)

#### Dim 7 — Controllability, Transparency & Resource Efficiency

```
Dim7 = mean(trace_completeness, 1 − policy_flag_rate, resource_efficiency,
            schema_compliance, format_compliance)
```

| Sub-indicator | Source | Normalisation |
|---------------|--------|---------------|
| `trace_completeness` | (TAO_cycles × 3) / total_steps | Already in [0, 1] |
| `policy_compliance` | 1 − policy_flag_rate | Already in [0, 1] |
| `resource_efficiency` | avg tokens, cross-pattern min-max inverted | Min-max, inverted |
| `schema_compliance` | JSON schema pass rate | Already in [0, 1]; None if no JSON tasks |
| `format_compliance` | judge pass / successful tasks | Already in [0, 1] |

**Dim 7 computation detail:**

| Pattern | trace_comp | policy_comp | resource_eff | schema_comp | format_comp | Dim 7 |
|---------|-----------|------------|-------------|------------|------------|-------|
| Baseline     |     0.000 |      1.000 |       1.000 |      0.625 |      0.812 | 0.688 |
| ReAct        |     0.556 |      1.000 |       0.690 |      0.500 |      0.625 | 0.674 |
| ReAct_Enhanced |     0.000 |      1.000 |       0.000 |      0.875 |      0.786 | 0.532 |
| CoT          |     0.000 |      0.750 |       0.445 |      0.500 |      0.571 | 0.453 |
| Reflex       |     0.000 |      1.000 |       0.957 |      0.750 |      0.750 | 0.691 |
| ToT          |     0.000 |      1.000 |       0.948 |      0.875 |      0.727 | 0.710 |

#### Composite Score

```
Composite = mean(Dim4, Dim6, Dim7)    [uniform weights, 1/N for N available dimensions]
```

#### Dim 3 -- Action-Decision Alignment

```
Dim3 = mean(plan_adherence_rate, avg_tool_coverage, avg_tool_precision)
```

| Sub-indicator | Source | Normalisation |
|---------------|--------|---------------|
| `plan_adherence_rate` | tasks with alignment >= 0.5 / total plan tasks | Already in [0, 1] |
| `avg_tool_coverage` | mean(|planned ∩ actual| / |planned|) | Already in [0, 1] |
| `avg_tool_precision` | mean(|planned ∩ actual| / |actual|) | Already in [0, 1] |

**Dim 3 computation detail:**

| Pattern | Plan Tasks | Adherence | Coverage | Precision | Dim 3 |
|---------|-----------|-----------|----------|-----------|-------|
| Baseline     |         4 |     0.000 |    0.000 |     0.000 | 0.000 |
| ReAct        |         4 |     1.000 |    1.000 |     1.000 | 1.000 |
| ReAct_Enhanced |         3 |     1.000 |    1.000 |     1.000 | 1.000 |
| CoT          |         4 |     1.000 |    1.000 |     0.850 | 0.950 |
| Reflex       |         4 |     0.000 |    0.000 |     0.000 | 0.000 |
| ToT          |         3 |     0.000 |    0.000 |     0.000 | 0.000 |

#### Dim 5 -- Behavioural Safety

```
Dim5 = mean(tool_compliance_rate, domain_safety_score)
```

| Sub-indicator | Source | Normalisation |
|---------------|--------|---------------|
| `tool_compliance_rate` | 1 - (unauthorized / total tool calls) | Already in [0, 1] |
| `domain_safety_score` | 1 - (flagged tasks / scanned tasks) | Already in [0, 1] |

**Dim 5 computation detail:**

| Pattern | Tool Tasks | Tool Calls | Violations | Compliance | Flagged | Scanned | Domain Safety | Dim 5 |
|---------|-----------|-----------|-----------|-----------|---------|---------|--------------|-------|
| Baseline     |         4 |         0 |         0 |     1.000 |       0 |      16 |        1.000 | 1.000 |
| ReAct        |         4 |         5 |         0 |     1.000 |       0 |      16 |        1.000 | 1.000 |
| ReAct_Enhanced |         4 |        39 |         0 |     1.000 |       0 |      14 |        1.000 | 1.000 |
| CoT          |         4 |         8 |         3 |     0.625 |       0 |      14 |        1.000 | 0.812 |
| Reflex       |         4 |         0 |         0 |     1.000 |       0 |      16 |        1.000 | 1.000 |
| ToT          |         4 |         0 |         0 |     1.000 |       0 |      11 |        1.000 | 1.000 |

### Dimension Score Summary

| Pattern | Dim 3 (Align) | Dim 4 (Success) | Dim 5 (Safety) | Dim 6 (Robust) | Dim 7 (Control) | Composite |
|---------|--------------|----------------|----------------|----------------|-----------------|-----------|
| Baseline     | 0.000        | 0.938          | 1.000          | 0.774          | 0.688           | 0.680     |
| ReAct        | 1.000        | 0.719          | 1.000          | 0.756          | 0.674           | 0.830     |
| ReAct_Enhanced | 1.000        | 0.348          | 1.000          | 0.566          | 0.532           | 0.689     |
| CoT          | 0.950        | 0.420          | 0.812          | 0.676          | 0.453           | 0.662     |
| Reflex       | 0.000        | 0.873          | 1.000          | 0.741          | 0.691           | 0.661     |
| ToT          | 0.000        | 0.483          | 1.000          | 0.604          | 0.710           | 0.559     |

### Reserve Indicators (★)

| Pattern | Norm Steps | Norm Tool Calls | Norm TAO Cycles |
|---------|-----------|-----------------|-----------------|
| Baseline     | 1.000     | N/A             | 0.000           |
| ReAct        | 0.371     | 1.000           | 1.000           |
| ReAct_Enhanced | 0.000     | 0.000           | 0.000           |
| CoT          | 0.562     | 0.500           | 0.000           |
| Reflex       | 0.781     | N/A             | 0.000           |
| ToT          | 0.344     | N/A             | 0.000           |

### Composite Score Ranking

1. **ReAct**: 0.8298
2. **ReAct_Enhanced**: 0.6891
3. **Baseline**: 0.6797
4. **CoT**: 0.6624
5. **Reflex**: 0.6610
6. **ToT**: 0.5593

## 6. Recommendations

### Scenario-Based Pattern Selection

- **Complex Reasoning Tasks:** Baseline (highest success rate)
- **Real-time/Low-latency Scenarios:** Baseline (fastest response)
- **Noisy/Unreliable Environments:** ToT (most robust)
- **Enterprise/Compliance-critical:** ToT (most controllable)
