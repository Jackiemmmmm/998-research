# Week 9 P2 Report Chapter: Results and Analysis

> Phase alignment: **Phase 3: Evaluation**  
> Owner: **P2 - Yiming Wang**  
> Week 9 task: **Report: Results & Analysis**  
> Proposal alignment: **Section 3.1 Experimental Deliverables** and **Section 3.4 Technical Analytical Synthesis and Final Deliverables**  
> Source data: `reports/comparison_table.csv`, `reports/evaluation_report.md`, `reports/evaluation_results.json`, and `docs/WEEK7_8_P2_SENSITIVITY_CROSS_COMPARISON.md`

## 1. Chapter Purpose

This chapter reports the experimental results from the current LangGraph-based agent evaluation pipeline and interprets the results against the project's seven-dimension evaluation framework. It fulfils the Proposal Section 3.1 expectation of a data-backed comparison of agentic design patterns and the Proposal Section 3.4 expectation of a final analytical synthesis combining quantitative results with qualitative observations.

The evaluated patterns are:

- Baseline
- ReAct
- ReAct_Enhanced
- Chain-of-Thought (CoT)
- Reflex
- Tree-of-Thoughts (ToT)

The current repository implements six of the seven proposed dimensions. Dimension 2, Cognitive Safety and Constraint Adherence, remains a Phase B2 placeholder and is therefore reported as a transparent limitation rather than silently converted into zero. This means the current chapter can compare all patterns across the seven-dimension framework, but only six dimensions currently have computed experimental values.

## 2. Experimental Setup Summary

The evaluation uses the repository's current `run_evaluation.py` pipeline. The latest report metadata records:

| Item | Current value |
|---|---|
| Agent model provider | Ollama |
| Agent model | `llama3.1` |
| Judge model | `qwen2.5:7b` |
| Number of repeated runs | 3 |
| Confidence interval method | t-distribution 95% CI |
| Pattern count | 6 |
| Task count per pattern | 16 |
| Perturbation variants | 32 per pattern |
| Parallel execution | Enabled |
| Max concurrency | 1 |
| Robustness data | Recomputed every run |

The evaluation produces:

- per-pattern success, efficiency, robustness, controllability, alignment, safety, and reasoning-quality metrics;
- normalized dimension-level scores;
- composite scores using the repository's Phase E scoring implementation;
- mean, standard deviation, and 95% confidence intervals from the Phase F multi-run statistical layer;
- pairwise effect sizes for composite score and strict success rate.

## 3. Headline Results

The main result is that there is no universally dominant agentic pattern. Different architectures lead under different evaluation priorities:

- **Baseline** has the highest current-code composite score and best success/efficiency score, but it is not agentically inspectable on reasoning or action-decision alignment.
- **Reflex** is the strongest practical compromise: it combines strong reasoning quality, high efficiency, high safety, and good robustness.
- **ReAct** is the strongest tool-orchestration baseline: it has perfect action-decision alignment and behavioural safety with moderate cost.
- **ToT** has the strongest Phase F mean reasoning quality and ties Baseline for the highest mean strict success, but it is the slowest pattern.
- **CoT** is broadly evaluable across all implemented dimensions, but its latency and efficiency are weak.
- **ReAct_Enhanced** improves some partial-task behaviour but is currently too costly and fragile to justify its added complexity.

The central methodological finding is that composite rankings are highly sensitive to how non-evaluable dimensions are handled. Under the repository's current scoring rule, missing dimensions are excluded from the denominator. Under the report's all-seven-dimension fairness stress test, where N/A dimensions are treated as zero, the ranking changes substantially.

## 4. Statistical Results Table

The following table reports Phase F multi-run results from the generated evaluation report. Values are mean +/- 95% CI across three runs.

| Pattern | Composite | Strict success | Avg latency (s) | Avg tokens | Robustness degradation (%) |
|---|---:|---:|---:|---:|---:|
| Baseline | 0.850 +/- 0.000 | 0.812 +/- 0.000 | 2.235 +/- 1.086 | 195.500 +/- 0.000 | 34.615 +/- 0.000 |
| ReAct | 0.824 +/- 0.002 | 0.625 +/- 0.000 | 6.776 +/- 0.141 | 1013.750 +/- 34.156 | 45.000 +/- 0.000 |
| ReAct_Enhanced | 0.720 +/- 0.001 | 0.750 +/- 0.000 | 16.490 +/- 0.391 | 2588.689 +/- 59.021 | 62.500 +/- 0.000 |
| CoT | 0.681 +/- 0.002 | 0.562 +/- 0.000 | 38.696 +/- 0.149 | 1703.875 +/- 0.000 | 33.333 +/- 0.000 |
| Reflex | 0.829 +/- 0.001 | 0.750 +/- 0.000 | 3.971 +/- 0.060 | 300.438 +/- 0.944 | 33.333 +/- 0.000 |
| ToT | 0.776 +/- 0.059 | 0.812 +/- 0.155 | 55.213 +/- 0.734 | 288.521 +/- 0.090 | 40.995 +/- 5.648 |

The low confidence interval width for several patterns reflects deterministic or near-deterministic behaviour under the current model and execution settings. For this reason, the report should use mean +/- CI as the primary statistical summary and treat Cohen's d cautiously when pooled variance is near zero.

## 5. Dimension-Level Results

The following dimension-level scores use the Phase F multi-run mean values reported in `reports/evaluation_report.md` under "Dimension Score Summary". This keeps the formal Week 9 results chapter aligned with the statistical table above. Latest single-run values are reserved for the Week 7-8 sensitivity appendix.

| Pattern | Dim1 Reasoning | Dim2 Cognitive Safety | Dim3 Alignment | Dim4 Success/Efficiency | Dim5 Behavioural Safety | Dim6 Robustness | Dim7 Control | Phase F composite |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Baseline | N/A | Pending | N/A | 0.938 | 1.000 | 0.774 | 0.688 | 0.850 |
| ReAct | N/A | Pending | 1.000 | 0.732 | 1.000 | 0.720 | 0.668 | 0.824 |
| ReAct_Enhanced | N/A | Pending | 1.000 | 0.494 | 1.000 | 0.569 | 0.535 | 0.720 |
| CoT | 0.782 | Pending | 0.950 | 0.415 | 0.812 | 0.713 | 0.411 | 0.681 |
| Reflex | 0.820 | Pending | N/A | 0.891 | 1.000 | 0.741 | 0.691 | 0.829 |
| ToT | 0.877 | Pending | N/A | 0.591 | 1.000 | 0.681 | 0.730 | 0.776 |

### 5.1 Dim1: Reasoning Quality

Only CoT, Reflex, and ToT expose usable reasoning traces in the current evaluation. ToT achieves the highest Phase F mean reasoning quality score (0.877), followed by Reflex (0.820) and CoT (0.782). The difference reflects ToT's strong trace coverage and answer agreement, while Reflex benefits from high coherence and much lower operational cost.

Baseline, ReAct, and ReAct_Enhanced are marked N/A on this dimension because the current trace extraction found no usable THINK content. This does not mean their reasoning is necessarily poor; it means the repository's current cognitive metric cannot inspect it.

### 5.2 Dim2: Cognitive Safety and Constraint Adherence

Dim2 is not implemented in the current repository. The report should explicitly state this limitation. Planned Phase B2 scope includes toxicity keyword filtering, unsupported-claim or hallucination detection, and constraint-adherence scoring. Until this dimension is implemented, any claim of "all seven dimensions completed" would be inaccurate.

### 5.3 Dim3: Action-Decision Alignment

ReAct and ReAct_Enhanced both score 1.000 on Dim3, while CoT scores 0.950. This confirms that the tool-using patterns can be evaluated on whether their executed tool calls match task plans. Baseline, Reflex, and ToT are N/A because they do not operate as tool-orchestration patterns in this setup.

The key finding is that ReAct achieves perfect alignment at far lower cost than ReAct_Enhanced. This makes ReAct the stronger practical tool-orchestration baseline.

### 5.4 Dim4: Success and Efficiency

Baseline has the strongest Dim4 score (0.938), reflecting fast execution and low token use. Reflex is second (0.891), combining strong task success with efficient execution. ReAct remains moderate (0.732). ToT (0.591), ReAct_Enhanced (0.494), and CoT (0.415) are penalized for high runtime cost, high token cost, or both.

This dimension exposes the main cost-performance trade-off: more explicit reasoning and more intensive tool orchestration can improve inspectability or task-specific capability, but often reduce operational efficiency.

### 5.5 Dim5: Behavioural Safety

Baseline, ReAct, ReAct_Enhanced, Reflex, and ToT score 1.000 on Dim5. CoT scores lower at 0.812 due to tool compliance and policy-related issues. Patterns with no tool calls are judged mainly on domain/content safety, so high Dim5 values for non-tool patterns should not be overinterpreted as strong tool-safety evidence.

### 5.6 Dim6: Robustness and Scalability

Baseline has the highest Dim6 score (0.774), followed by Reflex (0.741), ReAct (0.720), CoT (0.713), ToT (0.681), and ReAct_Enhanced (0.569). This ranking differs from raw degradation ranking because Dim6 combines normalized degradation, stability index, and complexity scaling.

ReAct_Enhanced is the weakest robustness performer because it has the highest degradation percentage (62.5%) and lowest stability index. CoT has good stability but is affected by complexity decline. ToT has high success but still degrades under perturbations.

### 5.7 Dim7: Controllability, Transparency, and Resource Efficiency

ToT has the highest Dim7 score (0.730), followed by Reflex (0.691), Baseline (0.688), ReAct (0.668), ReAct_Enhanced (0.535), and CoT (0.411). This result should be interpreted carefully because Dim7 includes resource-efficiency components that are not identical to wall-clock latency. ToT is slow, but its token profile is efficient relative to some tool-using patterns.

ReAct has the clearest trace completeness among tool-using patterns, while ReAct_Enhanced is weakened by resource cost.

## 6. Comparative Pattern Analysis

### 6.1 Baseline

Baseline is the fastest and most efficient control pattern. It ranks first under the Phase E evaluable-dimension composite because only its available dimensions are averaged. However, its missing Dim1 and Dim3 scores mean it cannot be treated as the best autonomous agent architecture. It is best understood as a raw-LLM control that sets a speed and simplicity benchmark.

### 6.2 ReAct

ReAct provides the best tool-use balance. It achieves perfect action-decision alignment and behavioural safety while keeping latency and token costs much lower than ReAct_Enhanced and CoT. Its main limitation is that the current evaluation does not produce usable reasoning traces for Dim1, so its cognitive process is less inspectable than CoT, Reflex, or ToT.

### 6.3 ReAct_Enhanced

ReAct_Enhanced achieves perfect alignment and safety, but these benefits do not translate into better composite performance. Its high token use, high latency, weak robustness, and low Dim7 score suggest that the enhanced design currently overuses tools or fails to stop efficiently. It should be treated as an optimization target rather than a recommended pattern.

### 6.4 CoT

CoT is the most broadly evaluable pattern because it has non-N/A values for all six implemented dimensions. It offers strong reasoning coherence and strong action alignment. However, it performs poorly on success/efficiency and controllability, making it less practical for production-like workflows unless interpretability is more important than runtime cost.

### 6.5 Reflex

Reflex is the most balanced practical pattern. It scores strongly on reasoning quality, success/efficiency, behavioural safety, robustness, and controllability. Although it lacks Dim3 action-alignment evaluation because it does not use tools in this setup, it is the strongest compromise when tasks do not require explicit external tool orchestration.

### 6.6 ToT

ToT is the strongest reasoning architecture. It has the highest Phase F mean Dim1 score and ties Baseline for the highest mean strict success, making it suitable for complex reasoning and deliberative planning. Its main drawback is latency: it is the slowest pattern by a large margin. ToT is therefore appropriate when answer quality and reasoning exploration matter more than response time.

## 7. Trade-Off Discussion

### 7.1 Reasoning Depth vs Operational Efficiency

The strongest reasoning patterns are ToT, Reflex, and CoT. ToT has the highest reasoning score but the slowest average latency. CoT has strong coherence but weak Dim4 due to high latency and token cost. Reflex provides the best reasoning-efficiency compromise: it achieves high Dim1 while remaining close to Baseline in latency and token usage.

This supports the proposal's expectation that reasoning depth and operational efficiency must be evaluated together rather than independently.

### 7.2 Tool Orchestration vs Cost

ReAct, ReAct_Enhanced, and CoT are the tool-using patterns. ReAct is the strongest practical tool pattern because it achieves perfect alignment with moderate overhead. ReAct_Enhanced demonstrates that adding more tool-oriented behaviour can increase cost without improving final performance. CoT also performs well on alignment but is too slow under the current setup.

### 7.3 Robustness vs Raw Success

Raw success and robustness are not equivalent. ToT has high success but still degrades under perturbation. CoT has good stability but lower success and complexity scaling. Baseline ranks highest on Dim6, but this should be interpreted as robustness of output behaviour rather than evidence of agentic resilience.

### 7.4 Composite Score vs Dimension Coverage

The Phase E composite score is sensitive to missing dimensions. Under the repository's default evaluable-dimension mean, Baseline ranks first. Under the main report's all-seven-dimension fairness stress test treating N/A dimensions as zero, Reflex and ReAct become the strongest patterns and Baseline falls substantially. Therefore, the final report should present both dimension-level scores and composite scores, with a clear explanation of missing-dimension handling.

## 8. Scenario-Based Recommendations

| Scenario | Recommended pattern | Reason |
|---|---|---|
| Fast baseline or low-cost response | Baseline | Highest Dim4 and lowest latency, but non-agentic |
| Practical tool orchestration | ReAct | Perfect Dim3 and Dim5 with manageable cost |
| Balanced autonomous execution | Reflex | Strong reasoning, efficiency, robustness, and control |
| Complex reasoning | ToT | Highest Phase F mean Dim1 and joint-highest mean strict success |
| Explainability-first research | CoT | Broad dimensional coverage and strong reasoning coherence |
| Future optimization study | ReAct_Enhanced | Clear case where added complexity harms efficiency and robustness |

## 9. Threats to Validity

The main limitations are:

- **Dim2 is not implemented**, so cognitive safety and hallucination-related claims remain incomplete.
- **N/A dimensions affect rankings**, especially for Baseline and non-tool patterns.
- **Only three repeated runs are used**, which satisfies the current Phase F plan but remains a small sample.
- **Local model behaviour may not generalize** to other providers or larger LLMs.
- **Task suite size is limited**, with 16 tasks per pattern.
- **Some patterns are not directly comparable on tool alignment**, because not all patterns use tools.
- **Cohen's d is unstable when variance is near zero**, so effect-size interpretation should be cautious.

## 10. Chapter Conclusion

The experimental results support the project's core argument: agentic design patterns should be selected according to task context rather than ranked by a single universal score. Baseline is fastest, ReAct is best for tool orchestration, Reflex is the best all-round practical compromise, ToT is best for deep reasoning, CoT is most broadly inspectable but inefficient, and ReAct_Enhanced currently shows the cost of over-complexity.

The most important contribution of this analysis is methodological. The project demonstrates that a normalized multi-dimensional evaluation framework can reveal trade-offs that a single task success metric would hide. In particular, the contrast between current-code composite ranking and fair N/A-penalized ranking shows why dimension coverage, missingness, and sensitivity analysis must be reported alongside aggregate scores.

## 11. Tables for Final Report Appendix

### 11.1 Current-Code Composite Ranking

| Rank | Pattern | Composite |
|---:|---|---:|
| 1 | Baseline | 0.850 |
| 2 | Reflex | 0.829 |
| 3 | ReAct | 0.824 |
| 4 | ToT | 0.776 |
| 5 | ReAct_Enhanced | 0.720 |
| 6 | CoT | 0.681 |

### 11.2 Fair All-Seven-Dimension Ranking, N/A = 0

This table uses the same fairness stress-test basis as the generated main report: all seven proposal dimensions are included and any N/A or pending dimension, including Dim2, is treated as zero. The Week 7-8 appendix also reports an implemented-six stress test; the rank order is the same, but the scores are higher because Dim2 is omitted from the denominator.

| Rank | Pattern | Score |
|---:|---|---:|
| 1 | Reflex | 0.592 |
| 2 | ReAct | 0.589 |
| 3 | CoT | 0.583 |
| 4 | ToT | 0.554 |
| 5 | ReAct_Enhanced | 0.514 |
| 6 | Baseline | 0.486 |

### 11.3 Pattern Strength Summary

| Pattern | Strongest evidence | Main weakness |
|---|---|---|
| Baseline | Fastest and most efficient | Not inspectable on reasoning or tool alignment |
| ReAct | Best practical tool orchestration | No usable reasoning trace |
| ReAct_Enhanced | Perfect alignment and safety | High cost and weak robustness |
| CoT | Broad evaluability and strong coherence | Low efficiency |
| Reflex | Best balanced practical pattern | No tool-alignment evaluation |
| ToT | Highest reasoning quality | Slowest execution |
