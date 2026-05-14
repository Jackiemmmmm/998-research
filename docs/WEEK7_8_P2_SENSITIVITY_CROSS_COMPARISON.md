# Week 7-8 P2 Deliverable: Sensitivity Analysis and Cross-Comparison

> Phase alignment: **Phase 3: Evaluation**  
> Owner: **P2 - Yiming Wang**  
> Source data: `reports/comparison_table.csv`, `reports/evaluation_results.json`  
> Generated against current repository state after Phase B1, Phase C1/C3, Phase D1, Phase E, and Phase F.
> Reporting basis: this appendix primarily uses the latest single-run snapshot in `reports/comparison_table.csv`; Phase F multi-run means are used in the Week 9 results chapter.

## 1. Purpose

This document completes the Week 7-8 P2 task:

> Analyse weight variation impact on composite scores; cross-dimension analysis (for example reasoning depth vs efficiency trade-off); identify strengths and weaknesses per pattern.

The current evaluation pipeline already computes normalized dimension scores in `src/evaluation/scoring.py` and reports multi-run statistics in `src/evaluation/statistics.py` / `reports/evaluation_results.json`. This analysis uses those outputs rather than introducing a separate metric system.

Important scope note: **Dimension 2 - Cognitive Safety & Constraint Adherence is not implemented yet**. The current comparison therefore covers the six implemented/evaluable dimensions:

- Dim 1: Reasoning Quality
- Dim 3: Action-Decision Alignment
- Dim 4: Success & Efficiency
- Dim 5: Behavioural Safety
- Dim 6: Robustness & Scalability
- Dim 7: Controllability, Transparency & Resource Efficiency

## 2. Repository-Aligned Scoring Assumptions

The composite score implementation in `src/evaluation/scoring.py` uses:

```text
Composite = weighted average of available non-None dimension scores
```

By default, all available dimensions are weighted uniformly. If a dimension is `None` for a pattern, it is excluded from that pattern's denominator. This is faithful to the Phase E implementation, but it creates an interpretability issue: patterns with fewer evaluable dimensions can receive high composite scores because weak or inapplicable dimensions are omitted.

For this reason, the sensitivity analysis reports two families of views:

1. **Code-aligned view**: `None` dimensions are excluded, matching `compute_composite()`.
2. **Fairness stress-test view**: missing implemented dimensions are treated as zero to show how rankings change when non-evaluability is penalized.

This distinction is already visible in `reports/evaluation_report.md`: Baseline ranks first under the evaluable-dimension mean, but falls substantially when N/A dimensions are penalized.

## 3. Baseline Dimension Snapshot

The table below is taken from the current `reports/comparison_table.csv`.

| Pattern | Dim1 Reason | Dim3 Align | Dim4 Success/Eff. | Dim5 Safety | Dim6 Robust | Dim7 Control | Composite |
|---|---:|---:|---:|---:|---:|---:|---:|
| Baseline | N/A | N/A | 0.938 | 1.000 | 0.774 | 0.688 | 0.850 |
| ReAct | N/A | 1.000 | 0.735 | 1.000 | 0.720 | 0.670 | 0.825 |
| ReAct_Enhanced | N/A | 1.000 | 0.493 | 1.000 | 0.569 | 0.535 | 0.719 |
| CoT | 0.782 | 0.950 | 0.418 | 0.812 | 0.713 | 0.413 | 0.681 |
| Reflex | 0.820 | N/A | 0.890 | 1.000 | 0.741 | 0.691 | 0.828 |
| ToT | 0.895 | N/A | 0.612 | 1.000 | 0.709 | 0.767 | 0.797 |

Key implication: the current composite score is not a single neutral "best agent" indicator. It is a weighted summary of whichever dimensions are measurable for a pattern.

## 4. Weight Sensitivity Analysis

### 4.1 Scenario Definitions

| Scenario | Weighting logic | Missing dimensions |
|---|---|---|
| S0 Current code | Equal weight across available implemented dimensions | Excluded |
| S1 Fair all-6 implemented dims | Equal weight across Dim1, Dim3, Dim4, Dim5, Dim6, Dim7 | N/A = 0 |
| S2 Cognitive-heavy | Dim1 0.35; Dim3 0.10; Dim4 0.15; Dim5 0.10; Dim6 0.15; Dim7 0.15 | Excluded |
| S3 Behavioural/tool-heavy | Dim1 0.10; Dim3 0.25; Dim4 0.25; Dim5 0.20; Dim6 0.10; Dim7 0.10 | Excluded |
| S4 Robustness/control-heavy | Dim1 0.10; Dim3 0.10; Dim4 0.10; Dim5 0.10; Dim6 0.30; Dim7 0.30 | Excluded |
| S5 Efficiency-heavy | Dim1 0.10; Dim3 0.10; Dim4 0.40; Dim5 0.10; Dim6 0.15; Dim7 0.15 | Excluded |

The custom scenarios use the same mathematical behaviour as `compute_composite()`: weights are renormalized over available dimensions only.

### 4.2 Ranking Results

#### S0 - Current Code: Evaluable-Dimension Mean

| Rank | Pattern | Score |
|---:|---|---:|
| 1 | Baseline | 0.850 |
| 2 | Reflex | 0.828 |
| 3 | ReAct | 0.825 |
| 4 | ToT | 0.797 |
| 5 | ReAct_Enhanced | 0.719 |
| 6 | CoT | 0.681 |

Interpretation: Baseline wins because it is strong on the dimensions it can be evaluated on, especially Dim4 and Dim5, while Dim1 and Dim3 are omitted.

#### S1 - Fair All-6 Implemented Dimensions, N/A = 0

| Rank | Pattern | Score |
|---:|---|---:|
| 1 | Reflex | 0.690 |
| 2 | ReAct | 0.688 |
| 3 | CoT | 0.681 |
| 4 | ToT | 0.664 |
| 5 | ReAct_Enhanced | 0.600 |
| 6 | Baseline | 0.566 |

Interpretation: once non-evaluable dimensions are penalized, Baseline drops from first to last. Reflex and ReAct become the most balanced choices across the implemented dimensions. CoT also improves relative to the default ranking because it has broad dimensional coverage even though its efficiency is weak.

If the currently missing Dim2 is also treated as zero for all patterns, every score above is scaled by `6/7` and the rank order remains the same. This matches the "all-7" caveat in the generated evaluation report.

#### S2 - Cognitive-Heavy

| Rank | Pattern | Score |
|---:|---|---:|
| 1 | Baseline | 0.836 |
| 2 | Reflex | 0.817 |
| 3 | ToT | 0.807 |
| 4 | ReAct | 0.798 |
| 5 | CoT | 0.682 |
| 6 | ReAct_Enhanced | 0.676 |

Interpretation: ToT improves because it has the strongest Dim1 score (0.895), but it still does not overtake Baseline/Reflex under the code-aligned missing-dimension rule. If the analysis requires cognitive comparability, the fair N/A treatment should be preferred because Baseline and ReAct do not expose usable reasoning traces.

#### S3 - Behavioural/Tool-Heavy

| Rank | Pattern | Score |
|---:|---|---:|
| 1 | Baseline | 0.893 |
| 2 | Reflex | 0.864 |
| 3 | ReAct | 0.859 |
| 4 | ToT | 0.787 |
| 5 | ReAct_Enhanced | 0.760 |
| 6 | CoT | 0.695 |

Interpretation: ReAct is the strongest tool-using pattern under this lens because it combines perfect Dim3 alignment with perfect Dim5 safety and moderate Dim4 efficiency. ReAct_Enhanced has perfect alignment and safety too, but its high latency/token cost depresses Dim4.

#### S4 - Robustness/Control-Heavy

| Rank | Pattern | Score |
|---:|---|---:|
| 1 | Baseline | 0.790 |
| 2 | Reflex | 0.778 |
| 3 | ToT | 0.771 |
| 4 | ReAct | 0.767 |
| 5 | ReAct_Enhanced | 0.645 |
| 6 | CoT | 0.634 |

Interpretation: ToT becomes more competitive because it has the highest Dim7 score (0.767), but its Dim6 is not the strongest. Baseline remains high because Dim6 rewards its scaling behaviour and stability despite higher raw degradation than CoT.

#### S5 - Efficiency-Heavy

| Rank | Pattern | Score |
|---:|---|---:|
| 1 | Baseline | 0.868 |
| 2 | Reflex | 0.836 |
| 3 | ReAct | 0.781 |
| 4 | ToT | 0.729 |
| 5 | ReAct_Enhanced | 0.625 |
| 6 | CoT | 0.590 |

Interpretation: Baseline and Reflex are clearly preferred when efficiency is weighted heavily. CoT and ToT both pay a reasoning-cost penalty, with CoT especially affected by high latency and low Dim4.

## 5. Cross-Dimension Trade-Off Analysis

### 5.1 Reasoning Depth vs Efficiency

The clearest trade-off is between explicit reasoning capability and runtime cost.

| Pattern | Reasoning trace tasks | Avg trace coverage | Avg coherence | Dim1 | Avg latency (s) | Avg tokens | Dim4 |
|---|---:|---:|---:|---:|---:|---:|---:|
| CoT | 16 | 0.594 | 0.963 | 0.782 | 38.74 | 1704 | 0.418 |
| Reflex | 16 | 0.500 | 0.975 | 0.820 | 3.99 | 300 | 0.890 |
| ToT | 16 | 1.000 | 0.866 | 0.895 | 55.54 | 289 | 0.612 |
| Baseline | 0 | 0.000 | 0.000 | N/A | 1.97 | 196 | 0.938 |
| ReAct | 0 | 0.000 | 0.000 | N/A | 6.73 | 999 | 0.735 |
| ReAct_Enhanced | 0 | 0.000 | 0.000 | N/A | 16.55 | 2616 | 0.493 |

Findings:

- **ToT provides the strongest reasoning-quality score** (Dim1 = 0.895) and highest trace coverage, but it is the slowest pattern at 55.54 seconds per task.
- **Reflex is the best reasoning-efficiency compromise**: it has high Dim1 (0.820), high coherence (0.975), low latency (3.99 seconds), and strong Dim4 (0.890).
- **CoT has strong coherence but weak efficiency**. Its Dim4 is lowest among reasoning-trace patterns because it combines moderate success with high latency and token cost.
- **Baseline is efficient but not cognitively inspectable**. It has the best Dim4, but Dim1 is N/A because there are no usable THINK traces.

Practical implication: if the project wants explainable reasoning, Reflex is the strongest operational compromise; if the goal is maximum reasoning exploration, ToT is stronger but expensive.

### 5.2 Tool Alignment vs Operational Cost

| Pattern | Dim3 Alignment | Tool calls profile | Avg latency (s) | Avg tokens | Dim4 | Main observation |
|---|---:|---|---:|---:|---:|---|
| ReAct | 1.000 | Tool-using | 6.73 | 999 | 0.735 | Best tool-using balance |
| ReAct_Enhanced | 1.000 | Tool-using, many calls | 16.55 | 2616 | 0.493 | Alignment is perfect but costly |
| CoT | 0.950 | Tool-using, less precise | 38.74 | 1704 | 0.418 | Broadly evaluable but inefficient |
| Baseline | N/A | No tool use | 1.97 | 196 | 0.938 | Cannot be judged on action alignment |
| Reflex | N/A | No tool use | 3.99 | 300 | 0.890 | Efficient but not a tool-orchestration pattern |
| ToT | N/A | No tool use | 55.54 | 289 | 0.612 | Reasoning-heavy, not tool-aligned |

Findings:

- ReAct and ReAct_Enhanced both score 1.000 on Dim3, but ReAct is much cheaper.
- ReAct_Enhanced appears over-instrumented for the current task suite: extra tool calls do not translate into better Dim4, Dim6, or Dim7.
- CoT has good alignment but suffers from latency, suggesting that explicit chain-of-thought plus tool use is expensive under the current LangGraph execution design.

Practical implication: for tool orchestration tasks, ReAct is the preferred implementation baseline. ReAct_Enhanced needs tool-call pruning, caching, or stricter stopping criteria before it is competitive.

### 5.3 Robustness vs Raw Success

| Pattern | Strict success | Degradation (%) | Stability index | Scaling score | Dim6 |
|---|---:|---:|---:|---:|---:|
| Baseline | 0.812 | 34.62 | 0.667 | 1.000 | 0.774 |
| ReAct | 0.625 | 45.00 | 0.611 | 1.000 | 0.720 |
| ReAct_Enhanced | 0.750 | 62.50 | 0.333 | 1.000 | 0.569 |
| CoT | 0.562 | 33.33 | 0.722 | 0.750 | 0.713 |
| Reflex | 0.750 | 33.33 | 0.556 | 1.000 | 0.741 |
| ToT | 0.875 | 42.86 | 0.556 | 1.000 | 0.709 |

Findings:

- ToT has the highest strict success rate but not the highest Dim6 because perturbation degradation is higher than CoT/Reflex.
- CoT has the best stability index, but its scaling score is lower due to complexity decline.
- ReAct_Enhanced is the least robust under Dim6 because perturbation degradation is high and stability is low.
- Baseline's high Dim6 should be interpreted carefully: it is robust in the measured output-success sense, but not necessarily robust as an agentic architecture.

Practical implication: robustness rankings depend on whether the project prioritizes raw perturbation tolerance, stability index, or complexity scaling. The current Dim6 formula intentionally combines all three.

### 5.4 Controllability and Transparency

| Pattern | Trace completeness | Policy flag rate | Resource efficiency | Dim7 |
|---|---:|---:|---:|---:|
| Baseline | 0.000 | 0.000 | 1.000 | 0.688 |
| ReAct | 0.556 | 0.000 | 0.668 | 0.670 |
| ReAct_Enhanced | 0.000 | 0.000 | 0.000 | 0.535 |
| CoT | 0.000 | 0.250 | 0.377 | 0.413 |
| Reflex | 0.000 | 0.000 | 0.957 | 0.691 |
| ToT | 0.000 | 0.000 | 0.962 | 0.767 |

Findings:

- ToT has the highest Dim7, driven by strong controllability and resource-efficiency components despite slow latency. This reflects the current Dim7 formula using resource-efficiency normalization from token usage rather than wall-clock latency alone.
- ReAct is the only pattern with substantial trace completeness in this run, which supports its use in tool-orchestration analysis.
- CoT is penalized by policy flags and lower resource efficiency.
- ReAct_Enhanced underperforms on Dim7 because its token/resource footprint is high.

Practical implication: the Dim7 result should be discussed alongside raw latency. A pattern can be token-efficient but slow, as ToT shows.

## 6. Pattern-Level Strengths and Weaknesses

### Baseline

Strengths:

- Highest current-code composite score (0.850).
- Best Dim4 success/efficiency (0.938).
- Fastest average latency (1.97 seconds).
- Strong Dim6 under the implemented formula.

Weaknesses:

- Not evaluable on Dim1 reasoning quality or Dim3 action-decision alignment.
- Drops to last under the fair N/A=0 comparison.
- Best used as a raw-LLM control, not as evidence of agentic design superiority.

Best use case: low-latency baseline comparison and non-agentic control condition.

### ReAct

Strengths:

- Perfect Dim3 alignment and Dim5 safety.
- Best tool-using pattern under behavioural/tool-heavy weighting.
- Moderate efficiency compared with ReAct_Enhanced and CoT.
- Good all-round score under fair N/A treatment.

Weaknesses:

- Dim1 is N/A because usable THINK content is absent in the current run.
- Success rate is lower than Baseline/Reflex/ToT.
- Robustness is middling under perturbation.

Best use case: practical tool-orchestration baseline where action traceability matters.

### ReAct_Enhanced

Strengths:

- Perfect Dim3 alignment and Dim5 safety.
- Lenient success is higher than strict success, indicating some recoverable/partial capability.

Weaknesses:

- Weak Dim4 due to high latency and token usage.
- Lowest Dim6 robustness score.
- Lowest Dim7 among implemented systemic dimensions.
- Extra tool calls do not currently pay off in measurable composite gains.

Best use case: diagnostic candidate for optimization work, especially tool-call pruning and stopping criteria.

### CoT

Strengths:

- Broad dimensional coverage: Dim1, Dim3, Dim4, Dim5, Dim6, Dim7 all produce scores.
- Strong reasoning coherence (0.963).
- Strong action alignment (0.950).
- Good perturbation stability index.

Weaknesses:

- Lowest current-code composite score because efficiency and controllability are weak.
- Low strict success rate in this run.
- High latency and high token usage depress Dim4.
- Policy flags reduce Dim7 and Dim5 relative to safer patterns.

Best use case: explainability-focused experiments where reasoning trace quality matters more than runtime cost.

### Reflex

Strengths:

- Strong across most implemented dimensions.
- Best reasoning-efficiency compromise: Dim1 0.820 with only 3.99 seconds average latency.
- High Dim4, Dim5, Dim6, and Dim7.
- Ranks first under fair N/A=0 treatment.

Weaknesses:

- Dim3 is N/A because it is not a tool-orchestration pattern.
- Reasoning trace coverage is lower than ToT.
- Less suitable when the task requires explicit external tool use.

Best use case: reliable autonomous execution when tool orchestration is not central.

### ToT

Strengths:

- Highest Dim1 reasoning score (0.895).
- Highest strict success rate in the latest run (0.875).
- Highest Dim7 controllability score.
- Strong candidate for complex reasoning tasks.

Weaknesses:

- Slowest pattern by a large margin (55.54 seconds average latency).
- Dim3 is N/A because it does not use tools in this setup.
- Robustness degradation is higher than CoT/Reflex.

Best use case: complex reasoning and deliberative planning where latency is acceptable.

## 7. Recommended Interpretation for the Final Report

The final report should avoid presenting the composite score as a single universal ranking. Instead, it should frame the findings as architecture-selection guidance:

| Decision context | Recommended pattern | Rationale |
|---|---|---|
| Fast raw response baseline | Baseline | Highest Dim4 and lowest latency, but non-agentic |
| Tool orchestration | ReAct | Perfect alignment/safety with manageable cost |
| Explainable reasoning with practical cost | Reflex | Strong Dim1 and Dim4 together |
| Maximum reasoning quality | ToT | Highest Dim1 and strong success, but slow |
| Broad evaluability across dimensions | CoT | Scores on all implemented dimensions but inefficient |
| Optimization target | ReAct_Enhanced | Strong alignment but poor cost/robustness |

Most important methodological insight:

> Ranking is highly sensitive to how missing dimensions are handled. Under the repository's current `compute_composite()` behaviour, missing dimensions are excluded and Baseline ranks first. Under a fair comparison that treats N/A as zero across implemented dimensions, Reflex and ReAct become the top patterns and Baseline falls to last.

This should be reported as an evaluation-design finding rather than a bug. It shows why agentic architecture evaluation needs both:

- dimension-level reporting, and
- at least one fairness stress-test for N/A dimensions.

## 8. Next Analysis Steps

1. Add Phase B2 / Dim2 once implemented, then re-run this sensitivity analysis with all seven dimensions.
2. Add an automated sensitivity script or report section that recomputes the scenario table from `comparison_table.csv`.
3. Add a heatmap for weight scenarios vs pattern ranks in `reports/figures/`.
4. Extend Dim7 interpretation by separating token efficiency from wall-clock latency, since ToT is token-efficient but slow.
5. For ReAct_Enhanced, inspect per-task traces to identify redundant tool calls and early-stop failures.
