# Agentic Pattern Evaluation Report

**Generated:** 2026-03-22 20:25:17
**Patterns Evaluated:** Baseline, ReAct, ReAct_Enhanced, CoT, Reflex, ToT

## Summary Comparison

| Pattern | Strict | Lenient | Gap | Avg Latency (s) | Avg Tokens | Degradation (%) | Controllability |
|---------|--------|---------|-----|-----------------|------------|-----------------|-----------------|
| Baseline     |  81.2% |   81.2% | 0.0% |            3.04 |        196 |            30.8 |           81.2% |
| ReAct        |  62.5% |   62.5% | 0.0% |            7.46 |       1027 |            20.0 |           70.8% |
| ReAct_Enhanced |  75.0% |   87.5% | 12.5% |           18.04 |       2610 |            41.7 |           89.2% |
| CoT          |  56.2% |   56.2% | 0.0% |           43.59 |       1704 |            22.2 |           56.2% |
| Reflex       |  75.0% |   75.0% | 0.0% |            4.41 |        300 |            16.7 |           83.3% |
| ToT          |  81.2% |   81.2% | 0.0% |           61.85 |        289 |            15.4 |           89.6% |

## 1. Success Dimension

**Best Pattern:** Baseline (81.2%)

### Success Rates by Pattern
- **Baseline**: 81.2%
- **ReAct**: 62.5%
- **ReAct_Enhanced**: 75.0%
- **CoT**: 56.2%
- **Reflex**: 75.0%
- **ToT**: 81.2%

#### Baseline - By Category
  - baseline: 100.0%
  - reasoning: 100.0%
  - tool: 25.0%
  - planning: 100.0%

#### ReAct - By Category
  - baseline: 50.0%
  - reasoning: 75.0%
  - tool: 50.0%
  - planning: 75.0%

#### ReAct_Enhanced - By Category
  - baseline: 50.0%
  - reasoning: 100.0%
  - tool: 75.0%
  - planning: 75.0%

#### CoT - By Category
  - baseline: 75.0%
  - reasoning: 75.0%
  - tool: 25.0%
  - planning: 50.0%

#### Reflex - By Category
  - baseline: 75.0%
  - reasoning: 75.0%
  - tool: 50.0%
  - planning: 100.0%

#### ToT - By Category
  - baseline: 75.0%
  - reasoning: 75.0%
  - tool: 100.0%
  - planning: 75.0%

## 2. Efficiency Dimension

**Fastest Pattern:** Baseline (3.04s)
**Slowest Pattern:** ToT (61.85s)

### Average Latency by Pattern
- **Baseline**: 3.04s
- **ReAct**: 7.46s
- **ReAct_Enhanced**: 18.04s
- **CoT**: 43.59s
- **Reflex**: 4.41s
- **ToT**: 61.85s

#### Baseline - Detailed Efficiency
  - Median Latency: 3.04s
  - Token Usage: 196 avg
  - Avg Steps: 2.0

#### ReAct - Detailed Efficiency
  - Median Latency: 7.46s
  - Token Usage: 1027 avg
  - Avg Steps: 4.9

#### ReAct_Enhanced - Detailed Efficiency
  - Median Latency: 18.04s
  - Token Usage: 2610 avg
  - Avg Steps: 6.4

#### CoT - Detailed Efficiency
  - Median Latency: 43.59s
  - Token Usage: 1704 avg
  - Avg Steps: 4.0

#### Reflex - Detailed Efficiency
  - Median Latency: 4.41s
  - Token Usage: 300 avg
  - Avg Steps: 3.0

#### ToT - Detailed Efficiency
  - Median Latency: 61.85s
  - Token Usage: 289 avg
  - Avg Steps: 5.0

## 3. Robustness Dimension

**Most Robust:** ToT (15.4% degradation)
**Least Robust:** ReAct_Enhanced (41.7% degradation)

### Performance Degradation by Pattern
- **Baseline**: 30.8%
- **ReAct**: 20.0%
- **ReAct_Enhanced**: 41.7%
- **CoT**: 22.2%
- **Reflex**: 16.7%
- **ToT**: 15.4%

## 4. Controllability Dimension

**Most Controllable:** ToT (89.6%)

### Controllability Scores by Pattern
- **Baseline**: 81.2%
- **ReAct**: 70.8%
- **ReAct_Enhanced**: 89.2%
- **CoT**: 56.2%
- **Reflex**: 83.3%
- **ToT**: 89.6%

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
  - Resource Efficiency: 0.655

#### ReAct_Enhanced - Detailed Controllability
  - Schema Compliance: 87.5%
  - Tool Policy Compliance: 100.0%
  - Format Compliance: 80.0%
  - Unauthorized Tool Uses: 0
  - Trace Completeness: 0.000
  - Policy Flag Rate: 0.000
  - Resource Efficiency: 0.000

#### CoT - Detailed Controllability
  - Schema Compliance: 37.5%
  - Tool Policy Compliance: 75.0%
  - Format Compliance: 56.2%
  - Unauthorized Tool Uses: 3
  - Trace Completeness: 0.000
  - Policy Flag Rate: 0.250
  - Resource Efficiency: 0.375

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
  - Format Compliance: 81.2%
  - Unauthorized Tool Uses: 0
  - Trace Completeness: 0.000
  - Policy Flag Rate: 0.000
  - Resource Efficiency: 0.961

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
| Baseline     | 0.812       |            3.04 |        1.000 |       196 |      1.000 | 0.938 |
| ReAct        | 0.625       |            7.46 |        0.925 |      1027 |      0.655 | 0.735 |
| ReAct_Enhanced | 0.750       |           18.04 |        0.745 |      2610 |      0.000 | 0.498 |
| CoT          | 0.562       |           43.59 |        0.310 |      1704 |      0.375 | 0.416 |
| Reflex       | 0.750       |            4.41 |        0.977 |       300 |      0.957 | 0.894 |
| ToT          | 0.812       |           61.85 |        0.000 |       289 |      0.961 | 0.591 |

- Latency range: min = 3.04s, max = 61.85s
- Token range: min = 196, max = 2610

#### Dim 6 — Robustness & Scalability

```
Dim6 = mean(norm_degradation, recovery_rate, robustness_score)
```

| Sub-indicator | Source | Normalisation |
|---------------|--------|---------------|
| `norm_degradation` | degradation % | `1 − (degradation / 100)`, clamped to [0, 1] |
| `recovery_rate` | tool failure recovery | Already in [0, 1] |
| `robustness_score` | per-task original vs perturbed agreement | Already in [0, 1]; None if no perturbation data |

**Dim 6 computation detail:**

| Pattern | degradation % | norm_degradation | recovery_rate | robustness_score | Dim 6 |
|---------|--------------|-----------------|--------------|-----------------|-------|
| Baseline     |         30.8 |           0.692 |        0.000 |           0.688 | 0.460 |
| ReAct        |         20.0 |           0.800 |        0.000 |           0.562 | 0.454 |
| ReAct_Enhanced |         41.7 |           0.583 |        0.000 |           0.562 | 0.382 |
| CoT          |         22.2 |           0.778 |        0.000 |           0.469 | 0.416 |
| Reflex       |         16.7 |           0.833 |        0.000 |           0.625 | 0.486 |
| ToT          |         15.4 |           0.846 |        0.000 |           0.719 | 0.522 |

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
| Baseline     |     0.000 |      1.000 |       1.000 |      0.625 |      0.812 | 0.687 |
| ReAct        |     0.556 |      1.000 |       0.655 |      0.500 |      0.625 | 0.667 |
| ReAct_Enhanced |     0.000 |      1.000 |       0.000 |      0.875 |      0.800 | 0.535 |
| CoT          |     0.000 |      0.750 |       0.375 |      0.375 |      0.562 | 0.412 |
| Reflex       |     0.000 |      1.000 |       0.957 |      0.750 |      0.750 | 0.691 |
| ToT          |     0.000 |      1.000 |       0.961 |      0.875 |      0.812 | 0.730 |

#### Composite Score

```
Composite = mean(Dim4, Dim6, Dim7)    [uniform weights, 1/N for N available dimensions]
```

### Dimension Score Summary

| Pattern | Dim 4 (Success) | Dim 6 (Robust) | Dim 7 (Control) | Composite |
|---------|----------------|----------------|-----------------|-----------|
| Baseline     | 0.938          | 0.460          | 0.687           | 0.695     |
| ReAct        | 0.735          | 0.454          | 0.667           | 0.619     |
| ReAct_Enhanced | 0.498          | 0.382          | 0.535           | 0.472     |
| CoT          | 0.416          | 0.416          | 0.412           | 0.415     |
| Reflex       | 0.894          | 0.486          | 0.691           | 0.691     |
| ToT          | 0.591          | 0.522          | 0.730           | 0.614     |

### Reserve Indicators (★)

| Pattern | Norm Steps | Norm Tool Calls | Norm TAO Cycles |
|---------|-----------|-----------------|-----------------|
| Baseline     | 1.000     | N/A             | 1.000           |
| ReAct        | 0.341     | 1.000           | 1.000           |
| ReAct_Enhanced | 0.000     | 0.000           | 1.000           |
| CoT          | 0.545     | 0.500           | 1.000           |
| Reflex       | 0.773     | N/A             | 1.000           |
| ToT          | 0.318     | N/A             | 1.000           |

### Composite Score Ranking

1. **Baseline**: 0.6949
2. **Reflex**: 0.6906
3. **ReAct**: 0.6189
4. **ToT**: 0.6142
5. **ReAct_Enhanced**: 0.4717
6. **CoT**: 0.4147

## 6. Recommendations

### Scenario-Based Pattern Selection

- **Complex Reasoning Tasks:** Baseline (highest success rate)
- **Real-time/Low-latency Scenarios:** Baseline (fastest response)
- **Noisy/Unreliable Environments:** ToT (most robust)
- **Enterprise/Compliance-critical:** ToT (most controllable)
