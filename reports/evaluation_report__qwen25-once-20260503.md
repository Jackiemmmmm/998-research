# Agentic Pattern Evaluation Report

**Generated:** 2026-05-03 21:40:08
**Patterns Evaluated:** Baseline, ReAct, ReAct_Enhanced, CoT, Reflex, ToT
**Number of Runs:** 3
**Agent Model:** ollama/llama3.1
**Judge Model:** qwen2.5:7b
**Git:** main @ 41229e82
> **Note:** robustness_reused = true — perturbation suite was run **once** and replayed across all runs to bound cost. Robustness CI width therefore underestimates true variance.

> This report evaluates 6 agentic design patterns across a 3-layer, 7-dimension
> framework (Cognitive, Behavioural, Systemic). Each pattern is tested on 16 tasks
> spanning 4 categories (baseline, reasoning, tool-use, planning) with robustness
> perturbations. Scores are normalised to [0, 1] for fair cross-pattern comparison.

## Summary Comparison

| Pattern | Strict | Lenient | Gap | Avg Latency (s) | Avg Tokens | Degradation (%) | Controllability |
|---------|--------|---------|-----|-----------------|------------|-----------------|-----------------|
| Baseline     |  81.2% |   81.2% | 0.0% |            2.55 |        196 |            34.6 |           81.2% |
| ReAct        |  62.5% |   62.5% | 0.0% |            7.15 |       1076 |            45.0 |           70.8% |
| ReAct_Enhanced |  75.0% |   87.5% | 12.5% |           16.91 |       2577 |            62.5 |           89.2% |
| CoT          |  56.2% |   56.2% | 0.0% |           40.05 |       1704 |            33.3 |           56.2% |
| Reflex       |  75.0% |   75.0% | 0.0% |            4.57 |        301 |            33.3 |           83.3% |
| ToT          |  81.2% |   81.2% | 0.0% |           56.44 |        289 |            42.3 |           89.6% |

## 1. Success Dimension

> **What this measures**: Whether the agent produces correct final answers (strict
> exact match and lenient extraction). The controllability gap shows how much
> additional success is recovered by lenient parsing.

**Best Pattern:** Baseline (81.2%)

### Success Rates by Pattern
- **Baseline**: 81.2%
- **ReAct**: 62.5%
- **ReAct_Enhanced**: 75.0%
- **CoT**: 56.2%
- **Reflex**: 75.0%
- **ToT**: 81.2%

#### Baseline - By Category
  - reasoning: 100.0%
  - tool: 25.0%
  - planning: 100.0%
  - baseline: 100.0%

#### ReAct - By Category
  - reasoning: 75.0%
  - tool: 50.0%
  - planning: 75.0%
  - baseline: 50.0%

#### ReAct_Enhanced - By Category
  - reasoning: 100.0%
  - tool: 75.0%
  - planning: 75.0%
  - baseline: 50.0%

#### CoT - By Category
  - reasoning: 75.0%
  - tool: 25.0%
  - planning: 50.0%
  - baseline: 75.0%

#### Reflex - By Category
  - reasoning: 75.0%
  - tool: 50.0%
  - planning: 100.0%
  - baseline: 75.0%

#### ToT - By Category
  - reasoning: 75.0%
  - tool: 100.0%
  - planning: 75.0%
  - baseline: 75.0%

## 2. Efficiency Dimension

> **What this measures**: Computational cost of each pattern -- latency (wall-clock
> time per task) and token consumption. Lower is better. This captures the
> efficiency vs. capability trade-off central to pattern selection.

**Fastest Pattern:** Baseline (2.55s)
**Slowest Pattern:** ToT (56.44s)

### Average Latency by Pattern
- **Baseline**: 2.55s
- **ReAct**: 7.15s
- **ReAct_Enhanced**: 16.91s
- **CoT**: 40.05s
- **Reflex**: 4.57s
- **ToT**: 56.44s

#### Baseline - Detailed Efficiency
  - Median Latency: 1.22s
  - Token Usage: 196 avg
  - Avg Steps: 2.0

#### ReAct - Detailed Efficiency
  - Median Latency: 5.06s
  - Token Usage: 1076 avg
  - Avg Steps: 4.9

#### ReAct_Enhanced - Detailed Efficiency
  - Median Latency: 5.42s
  - Token Usage: 2577 avg
  - Avg Steps: 6.4

#### CoT - Detailed Efficiency
  - Median Latency: 29.10s
  - Token Usage: 1704 avg
  - Avg Steps: 4.0

#### Reflex - Detailed Efficiency
  - Median Latency: 1.22s
  - Token Usage: 301 avg
  - Avg Steps: 3.0

#### ToT - Detailed Efficiency
  - Median Latency: 37.50s
  - Token Usage: 289 avg
  - Avg Steps: 5.0

## 3. Robustness Dimension

> **What this measures**: How much performance degrades when task prompts are
> paraphrased or contain typos. Lower degradation = more robust. The D1-enhanced
> metrics also measure stability across prompt variants and performance scaling
> from simple to complex tasks.

**Most Robust:** CoT (33.3% degradation)
**Least Robust:** ReAct_Enhanced (62.5% degradation)

### Performance Degradation by Pattern
- **Baseline**: 34.6%
- **ReAct**: 45.0%
- **ReAct_Enhanced**: 62.5%
- **CoT**: 33.3%
- **Reflex**: 33.3%
- **ToT**: 42.3%

## 4. Controllability Dimension

> **What this measures**: Whether the agent operates transparently and within
> defined constraints -- schema compliance, tool policy adherence, output format
> consistency, and trace completeness (proportion of complete think-act-observe
> cycles).

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
  - Resource Efficiency: 0.630

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
  - Resource Efficiency: 0.367

#### Reflex - Detailed Controllability
  - Schema Compliance: 75.0%
  - Tool Policy Compliance: 100.0%
  - Format Compliance: 75.0%
  - Unauthorized Tool Uses: 0
  - Trace Completeness: 0.000
  - Policy Flag Rate: 0.000
  - Resource Efficiency: 0.956

#### ToT - Detailed Controllability
  - Schema Compliance: 87.5%
  - Tool Policy Compliance: 100.0%
  - Format Compliance: 81.2%
  - Unauthorized Tool Uses: 0
  - Trace Completeness: 0.000
  - Policy Flag Rate: 0.000
  - Resource Efficiency: 0.961

## 4b. Action-Decision Alignment (Dim 3)

> **What this measures**: Whether agents execute the tools they are supposed to
> according to the task plan. Coverage measures "did it call the right tools?",
> precision measures "did it avoid calling wrong tools?", and sequence match
> measures "did it call them in the right order?".
>
> **Note**: Patterns that lack tool-calling capability (e.g. Baseline, Reflex, ToT in
> this run) are marked N/A -- they cannot be evaluated on this dimension.

| Pattern | Plan Tasks | Aligned | Adherence | Coverage | Precision | Seq Match | Overall |
|---------|-----------|---------|-----------|----------|-----------|-----------|---------|
| Baseline     |         4 |     N/A |       N/A |      N/A |       N/A |       N/A | N/A (no tool use) |
| ReAct        |         4 |       4 |    100.0% |   100.0% |    100.0% |     1.000 |   1.000 |
| ReAct_Enhanced |         4 |       4 |    100.0% |   100.0% |    100.0% |     0.764 |   1.000 |
| CoT          |         4 |       4 |    100.0% |   100.0% |     85.0% |     0.850 |   0.950 |
| Reflex       |         4 |     N/A |       N/A |      N/A |       N/A |       N/A | N/A (no tool use) |
| ToT          |         4 |     N/A |       N/A |      N/A |       N/A |       N/A | N/A (no tool use) |

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
  - C3: 1.000
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
  - C3: 0.000
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
| Baseline     | 0.812       |            2.55 |        1.000 |       196 |      1.000 | 0.938 |
| ReAct        | 0.625       |            7.15 |        0.915 |      1076 |      0.630 | 0.723 |
| ReAct_Enhanced | 0.750       |           16.91 |        0.734 |      2577 |      0.000 | 0.495 |
| CoT          | 0.562       |           40.05 |        0.304 |      1704 |      0.367 | 0.411 |
| Reflex       | 0.750       |            4.57 |        0.962 |       301 |      0.956 | 0.889 |
| ToT          | 0.812       |           56.44 |        0.000 |       289 |      0.961 | 0.591 |

- Latency range: min = 2.55s, max = 56.44s
- Token range: min = 196, max = 2577

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
| Baseline     |         34.6 |     0.281 |      0.654 |    0.667 |   1.000 |       32 |   N/A |
| ReAct        |         45.0 |     0.281 |      0.550 |    0.611 |   1.000 |       32 |   N/A |
| ReAct_Enhanced |         62.5 |     0.469 |      0.375 |    0.333 |   1.000 |       32 |   N/A |
| CoT          |         33.3 |     0.188 |      0.667 |    0.722 |   0.750 |       32 |   N/A |
| Reflex       |         33.3 |     0.250 |      0.667 |    0.556 |   1.000 |       32 |   N/A |
| ToT          |         42.3 |     0.344 |      0.577 |    0.444 |   1.000 |       32 |   N/A |

**Success by complexity:**

- **Baseline**: simple: 1.000, medium: 0.625, complex: 1.000 (decline=0.000)
- **ReAct**: simple: 0.500, medium: 0.625, complex: 0.750 (decline=0.000)
- **ReAct_Enhanced**: simple: 0.500, medium: 0.875, complex: 0.750 (decline=0.000)
- **CoT**: simple: 0.750, medium: 0.500, complex: 0.500 (decline=0.250)
- **Reflex**: simple: 0.750, medium: 0.625, complex: 1.000 (decline=0.000)
- **ToT**: simple: 0.750, medium: 0.875, complex: 0.750 (decline=0.000)

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
| ReAct        |     0.556 |      1.000 |       0.630 |      0.500 |      0.625 | 0.662 |
| ReAct_Enhanced |     0.000 |      1.000 |       0.000 |      0.875 |      0.800 | 0.535 |
| CoT          |     0.000 |      0.750 |       0.367 |      0.375 |      0.562 | 0.411 |
| Reflex       |     0.000 |      1.000 |       0.956 |      0.750 |      0.750 | 0.691 |
| ToT          |     0.000 |      1.000 |       0.961 |      0.875 |      0.812 | 0.730 |

#### Composite Score

```
Composite = mean(Dim4, Dim6, Dim7)    [uniform weights, 1/N for N available dimensions]
```

#### Dim 3 -- Action-Decision Alignment

> **What this measures**: Whether agents execute the tools they are supposed to
> according to the task plan. Coverage measures "did it call the right tools?",
> precision measures "did it avoid calling wrong tools?", and sequence match
> measures "did it call them in the right order?".
>
> **Note**: Patterns that lack tool-calling capability are marked N/A -- they
> cannot be evaluated on this dimension.

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
| Baseline     |         4 |       N/A |      N/A |       N/A | N/A (no tool use) |
| ReAct        |         4 |     1.000 |    1.000 |     1.000 | 1.000 |
| ReAct_Enhanced |         4 |     1.000 |    1.000 |     1.000 | 1.000 |
| CoT          |         4 |     1.000 |    1.000 |     0.850 | 0.950 |
| Reflex       |         4 |       N/A |      N/A |       N/A | N/A (no tool use) |
| ToT          |         4 |       N/A |      N/A |       N/A | N/A (no tool use) |

#### Dim 1 -- Reasoning Quality

> **What this measures**: How coherent and well-grounded the agent's
> reasoning trace is. Combines four sub-indicators: trace_coverage (does the
> agent show its work?), coherence (does the chain hold together, judged by a
> separate local LLM), final-answer agreement (does the conclusion match the
> reasoning?), and self-consistency (do repeated runs converge on the same
> answer; only filled in when --num-runs > 1).
>
> **Note**: Patterns with zero usable THINK steps (e.g. Baseline) are still
> evaluable but score 0 on coverage and coherence; their Dim1 is dominated by
> the renormalised final-answer agreement.

```
Dim1 = 0.15*coverage + 0.40*coherence + 0.20*answer_agreement + 0.25*self_consistency
Dim1 = renorm(coverage, coherence, answer_agreement)   [single-run]
```

| Sub-indicator | Source | Normalisation |
|---------------|--------|---------------|
| `trace_coverage` | min(1, think_steps / 2) | Already in [0, 1] |
| `coherence_score` | judge LLM mean(logical_progression, internal_consistency) | Already in [0, 1] |
| `final_answer_agreement` | strict=1.0 / lenient=0.5 / fail=0.0 | Already in [0, 1] |
| `self_consistency_score` | largest equivalence class / total runs | Already in [0, 1]; None when single-run |

**Dim 1 computation detail:**

| Pattern | Tasks w/ Reason. | Coverage | Coherence | Agreement | Self-Cons. | Fallbacks | Dim 1 |
|---------|------------------|----------|-----------|-----------|------------|-----------|-------|
| Baseline     |                0 |    0.000 |     0.000 |     0.812 |      1.000 |         0 |   N/A |
| ReAct        |                0 |    0.000 |     0.000 |     0.625 |      1.000 |         0 |   N/A |
| ReAct_Enhanced |                0 |    0.000 |     0.000 |     0.812 |      1.000 |         0 |   N/A |
| CoT          |               16 |    0.594 |     0.963 |     0.562 |      1.000 |         0 | 0.782 |
| Reflex       |               16 |    0.500 |     0.975 |     0.750 |      0.979 |         0 | 0.820 |
| ToT          |               16 |    1.000 |     0.863 |     0.812 |      0.917 |         0 | 0.877 |

#### Dim 5 -- Behavioural Safety

> **What this measures**: Whether agents respect safety boundaries -- tool whitelist
> compliance (only calling authorised tools) and content safety (no dangerous
> patterns like shell commands, SQL injection, or PII exposure in outputs).
>
> **Note**: Patterns with zero tool calls have tool compliance marked as N/A
> (not evaluable). Their Dim5 score is based on domain safety only.

```
Dim5 = mean(tool_compliance_rate, domain_safety_score)  [when tool calls > 0]
Dim5 = domain_safety_score                              [when tool calls == 0]
```

| Sub-indicator | Source | Normalisation |
|---------------|--------|---------------|
| `tool_compliance_rate` | 1 - (unauthorized / total tool calls) | Already in [0, 1] |
| `domain_safety_score` | 1 - (flagged tasks / scanned tasks) | Already in [0, 1] |

**Dim 5 computation detail:**

| Pattern | Tool Tasks | Tool Calls | Violations | Compliance | Flagged | Scanned | Domain Safety | Dim 5 |
|---------|-----------|-----------|-----------|-----------|---------|---------|--------------|-------|
| Baseline     |         4 |         0 |         0 | N/A (no calls) |       0 |      16 |        1.000 | 1.000 |
| ReAct        |         4 |         5 |         0 |     1.000 |       0 |      16 |        1.000 | 1.000 |
| ReAct_Enhanced |         4 |        40 |         0 |     1.000 |       0 |      15 |        1.000 | 1.000 |
| CoT          |         4 |         8 |         3 |     0.625 |       0 |      16 |        1.000 | 0.812 |
| Reflex       |         4 |         0 |         0 | N/A (no calls) |       0 |      16 |        1.000 | 1.000 |
| ToT          |         4 |         0 |         0 | N/A (no calls) |       0 |      16 |        1.000 | 1.000 |

### Dimension Score Summary

| Pattern | Dim 1 (Reason) | Dim 3 (Align) | Dim 4 (Success) | Dim 5 (Safety) | Dim 6 (Robust) | Dim 7 (Control) | Composite |
|---------|----------------|--------------|----------------|----------------|----------------|-----------------|-----------|
| Baseline     | N/A            | N/A          | 0.938          | 1.000          | N/A            | 0.688           | 0.875     |
| ReAct        | N/A            | 1.000        | 0.723          | 1.000          | N/A            | 0.662           | 0.846     |
| ReAct_Enhanced | N/A            | 1.000        | 0.495          | 1.000          | N/A            | 0.535           | 0.757     |
| CoT          | 0.782          | 0.950        | 0.411          | 0.812          | N/A            | 0.411           | 0.673     |
| Reflex       | 0.820          | N/A          | 0.889          | 1.000          | N/A            | 0.691           | 0.850     |
| ToT          | 0.877          | N/A          | 0.591          | 1.000          | N/A            | 0.730           | 0.799     |

### Reserve Indicators (★)

| Pattern | Norm Steps | Norm Tool Calls | Norm TAO Cycles |
|---------|-----------|-----------------|-----------------|
| Baseline     | 1.000     | N/A             | 0.000           |
| ReAct        | 0.347     | 1.000           | 1.000           |
| ReAct_Enhanced | 0.000     | 0.000           | 0.000           |
| CoT          | 0.545     | 0.479           | 0.000           |
| Reflex       | 0.773     | N/A             | 0.000           |
| ToT          | 0.318     | N/A             | 0.000           |

### Composite Score Ranking

> **Interpretation**: The composite score is the uniform-weighted average of all
> available dimension scores. Patterns with more N/A dimensions are scored on
> fewer dimensions. A higher composite indicates better overall performance across
> the evaluated dimensions, but the per-dimension breakdown above reveals important
> trade-offs that a single number cannot capture.

1. **Baseline**: 0.8750 (3 dimensions)
2. **Reflex**: 0.8501 (4 dimensions)
3. **ReAct**: 0.8464 (4 dimensions)
4. **ToT**: 0.7993 (4 dimensions)
5. **ReAct_Enhanced**: 0.7574 (4 dimensions)
6. **CoT**: 0.6733 (5 dimensions)

## 6. Recommendations

### Scenario-Based Pattern Selection

- **Complex Reasoning Tasks:** Baseline (highest success rate)
- **Real-time/Low-latency Scenarios:** Baseline (fastest response)
- **Noisy/Unreliable Environments:** CoT (most robust)
- **Enterprise/Compliance-critical:** ToT (most controllable)

### Key Trade-offs Observed

- **Tool-using patterns (ReAct, ReAct_Enhanced, CoT) vs Non-tool patterns (Baseline, Reflex, ToT)**: Tool-using patterns average 64.6% success vs 79.2% for non-tool patterns. Tool-using patterns can be evaluated on Dim 3 (alignment), while non-tool patterns receive N/A for that dimension.
- **Robustness vs Complexity handling**: CoT shows the highest prompt stability (index=0.722).
  However, patterns with notable complexity decline: CoT (25.0%).

## 7. Statistical Rigor (Phase F)

Repeated runs: **N = 3**.
> Robustness perturbations were run **once** and replayed; robustness CI underestimates true variance.

### Mean ± 95 % CI by Pattern

| Pattern | Composite | Success (strict) | Latency (s) | Avg Tokens | Degradation % |
|---------|---|---|---|---|---|
| Baseline | 0.867 ± 0.036 | 0.812 ± 0.000 | 2.575 ± 1.318 | 195.500 ± 0.000 | 34.615 ± 0.000 |
| ReAct | 0.840 ± 0.034 | 0.625 ± 0.000 | 7.141 ± 1.037 | 1031.021 ± 97.187 | 45.000 ± 0.000 |
| ReAct_Enhanced | 0.745 ± 0.055 | 0.750 ± 0.000 | 16.836 ± 1.078 | 2588.378 ± 47.811 | 62.500 ± 0.000 |
| CoT | 0.677 ± 0.011 | 0.562 ± 0.000 | 39.217 ± 1.785 | 1703.875 ± 0.000 | 33.333 ± 0.000 |
| Reflex | 0.843 ± 0.029 | 0.750 ± 0.000 | 4.385 ± 0.730 | 300.625 ± 0.970 | 33.333 ± 0.000 |
| ToT | 0.784 ± 0.033 | 0.792 ± 0.090 | 56.301 ± 2.294 | 288.750 ± 1.345 | 42.308 ± 0.000 |

### Pairwise Effect Sizes — composite_score (Cohen's d)

> Cohen's d magnitudes: 0.2 small, 0.5 medium, 0.8 large.
> Zero-variance fallback uses ±999.0 to avoid infinities.

| Pattern A | Pattern B | Cohen's d |
|-----------|-----------|-----------|
| Baseline | ReAct | 1.851 |
| Baseline | ReAct_Enhanced | 6.503 |
| Baseline | CoT | 17.610 |
| Baseline | Reflex | 1.769 |
| Baseline | ToT | 5.860 |
| ReAct | ReAct_Enhanced | 5.228 |
| ReAct | CoT | 16.347 |
| ReAct | Reflex | -0.211 |
| ReAct | ToT | 4.173 |
| ReAct_Enhanced | CoT | 4.309 |
| ReAct_Enhanced | Reflex | -5.573 |
| ReAct_Enhanced | ToT | -2.157 |
| CoT | Reflex | -18.970 |
| CoT | ToT | -10.825 |
| Reflex | ToT | 4.684 |
