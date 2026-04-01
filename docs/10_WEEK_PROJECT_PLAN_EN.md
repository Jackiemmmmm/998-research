# 10-Week Project Plan: 3-Person Team

> **Date**: 2026-03-09
> **Team**: Yiming Wang (P2), Yucheng Tu (P1), Kapila Wijetunge (P3)
> **Final Goal**: Demonstrate different agent workflows via LangGraph execution and present comparative evaluation results across agent patterns to the supervisor

### Related Documents

| Document | Description |
|----------|-------------|
| [Group-1.pdf](../Group-1.pdf) | Project Proposal — defines the 3-layer, 7-dimension evaluation framework, methodology, and timeline |
| [PROJECT_GAP_ANALYSIS_AND_PLAN.md](./PROJECT_GAP_ANALYSIS_AND_PLAN.md) | Gap Analysis — defines Phase A–G implementation plan and per-dimension completion status |
| [PHASE_A_UNIFIED_TELEMETRY.md](./PHASE_A_UNIFIED_TELEMETRY.md) | Phase A Implementation Doc — technical details of the unified telemetry layer |

---

## 1. Current Status (~44% Complete)

> Completion assessment source: [PROJECT_GAP_ANALYSIS_AND_PLAN.md § Summary Table](./PROJECT_GAP_ANALYSIS_AND_PLAN.md#part-1-current-completion-status-gap-analysis)

### 1.1 Completed

| Module | Details | Files |
|--------|---------|-------|
| Agent Patterns | Five patterns implemented: Baseline (raw LLM control group), Reflex, ReAct, CoT, ToT | `src/agent/pattern_*.py` |
| Unified Telemetry | [Phase A](./PHASE_A_UNIFIED_TELEMETRY.md) — StepType, ToolCallRecord, StepRecord, AgentTrace, TraceExtractor | `src/evaluation/trace.py` |
| Base Evaluation Framework | Judge (3 modes), TestSuite (16 tasks), ReportGenerator, Visualization | `src/evaluation/` |
| Test Coverage | 28 unit tests (Phase A trace extraction) | `tests/unit_tests/test_trace.py` |
| CI/CD | GitHub Actions (unit tests, integration tests, lint, type check) | `.github/` |

### 1.2 Evaluation Framework Completion (7 Dimensions)

> Framework definition source: [Group-1.pdf § 2.1 Table 1](../Group-1.pdf) | Completion assessment source: [Gap Analysis § Summary Table](./PROJECT_GAP_ANALYSIS_AND_PLAN.md#part-1-current-completion-status-gap-analysis)

| # | Dimension | Layer | Completion | Notes | Gap Details |
|---|-----------|-------|------------|-------|-------------|
| 1 | Reasoning Quality | Cognitive | 0% | Not implemented | [Dim1 Gap](./PROJECT_GAP_ANALYSIS_AND_PLAN.md#dimension-1-reasoning-quality-cognitive---0) |
| 2 | Cognitive Safety & Constraint Adherence | Cognitive | 0% | Not implemented | [Dim2 Gap](./PROJECT_GAP_ANALYSIS_AND_PLAN.md#dimension-2-cognitive-safety--constraint-adherence-cognitive---0) |
| 3 | Action–Decision Alignment | Behavioural | ~70% | **Phase C1 COMPLETED** (2026-04-01): AlignmentMetrics + verb-tool mapping + LCS sequence matching + Dim3 scoring | [Dim3 Gap](./PROJECT_GAP_ANALYSIS_AND_PLAN.md#dimension-3-actiondecision-alignment-behavioural---0--10--70) |
| 4 | Success & Efficiency | Behavioural | ~75% | Basic judge + metrics exist; missing normalised cost score | [Dim4 Gap](./PROJECT_GAP_ANALYSIS_AND_PLAN.md#dimension-4-success--efficiency-behavioural---70--75) |
| 5 | Behavioural Safety | Behavioural | ~15% | Implementation spec completed (2026-04-01); awaiting P1 implementation | [Dim5 Gap](./PROJECT_GAP_ANALYSIS_AND_PLAN.md#dimension-5-behavioural-safety-behavioural---5--15) |
| 6 | Robustness & Scalability | Systemic | ~75% | **Phase D1 COMPLETED** (2026-04-01): all perturbations, stability index, complexity scaling, D1-aligned Dim6 formula | [Dim6 Gap](./PROJECT_GAP_ANALYSIS_AND_PLAN.md#dimension-6-robustness--scalability-systemic---40--75) |
| 7 | Controllability, Transparency & Resource Efficiency | Systemic | ~45% | Trace completeness foundation exists; missing policy-flag / override tests | [Dim7 Gap](./PROJECT_GAP_ANALYSIS_AND_PLAN.md#dimension-7-controllability-transparency--resource-efficiency-systemic---35--45) |

### 1.3 Missing Key Modules

> Each item below is explicitly promised in the Proposal but not yet implemented in the codebase

| Missing Module | Proposal Source | Corresponding Phase |
|----------------|----------------|---------------------|
| Normalisation (0–1) + Composite Scoring | [Group-1.pdf § 2.2](../Group-1.pdf) p5: "each sub-indicator is normalised to the 0–1 range...composite results are computed" | [Phase E](./PROJECT_GAP_ANALYSIS_AND_PLAN.md#phase-e-normalization-aggregation--composite-scoring) |
| Statistical Rigor (3–5 repeats, mean ± 95% CI) | [Group-1.pdf § 2.3 Table 2 C4](../Group-1.pdf) p8: "3–5 repeats; report mean ± 95% CI" | [Phase F](./PROJECT_GAP_ANALYSIS_AND_PLAN.md#phase-f-statistical-rigor--reproducibility) |
| Sensitivity Analysis (weight variation impact on conclusions) | [Group-1.pdf § 2.2](../Group-1.pdf) p5: "sensitivity analysis of weight variation...in the appendix" | [Phase F](./PROJECT_GAP_ANALYSIS_AND_PLAN.md#phase-f-statistical-rigor--reproducibility) |
| Complete Visualisation Suite (7-dim radar, trade-off scatter) | [Group-1.pdf § 3.3](../Group-1.pdf) p10: "Reusable scripts or tools that automate data collection and analysis" | [Phase G](./PROJECT_GAP_ANALYSIS_AND_PLAN.md#phase-g-final-report--visualization-polish) |
| Final Report | [Group-1.pdf § 3.4](../Group-1.pdf) p10: "comprehensive comparison report...quantitative results and qualitative observations" | [Phase G](./PROJECT_GAP_ANALYSIS_AND_PLAN.md#phase-g-final-report--visualization-polish) |

---

## 2. Team Roles

| Role | Member | Primary Responsibilities | Rationale |
|------|--------|--------------------------|-----------|
| **P1** | Yucheng Tu | Agent implementation + system integration + Demo | Most familiar with the codebase and LangGraph |
| **P2** | Yiming Wang | Evaluation metric development + data analysis + statistics | Strengths in data analysis and methodology |
| **P3** | Kapila Wijetunge | Report writing + visualisation + Safety dimensions | Strengths in documentation and quality assurance |

### 2.1 Collaboration Model: Spec → Implement → Document

Since P1 handles all code implementation, P2 and P3 contribute by writing **Implementation Specs** — short, precise documents that tell P1 exactly what to build.

**Workflow per task:**

```
Step 1: P2/P3 writes an Implementation Spec       (docs/specs/)
Step 2: P1 reviews the spec, asks questions        (GitHub PR or sync meeting)
Step 3: P1 implements the code                     (src/)
Step 4: P1 writes the Implementation Doc           (docs/PHASE_X_*.md, like Phase A)
Step 5: Update Gap Analysis status table           (docs/PROJECT_GAP_ANALYSIS_AND_PLAN.md)
```

**Document roles:**

| Document | Owner | Purpose | When |
|----------|-------|---------|------|
| Implementation Spec (`docs/specs/`) | P2 or P3 | Tell P1 what to build — inputs, outputs, formulas, edge cases, test cases | Before implementation |
| Implementation Doc (`docs/PHASE_X_*.md`) | P1 | Record what was actually built — architecture, data structures, verification results | After implementation |
| Gap Analysis (`docs/PROJECT_GAP_ANALYSIS_AND_PLAN.md`) | Anyone | Track phase status + link to specs and implementation docs | Updated at each milestone |

### 2.2 Implementation Spec Format

Every spec follows a fixed 7-section structure. Templates are available in `docs/specs/`.

```
1. Objective          — one sentence
2. Input              — exact field names, source files, value ranges, sample values
3. Output             — exact dataclass definitions P1 should create
4. Computation Logic  — formulas, edge cases, aggregation weights with justification
5. Integration Points — which files to create/modify
6. Verification Cases — concrete input → expected output pairs (become test cases)
7. Open Questions     — anything unresolved (team decides before P1 starts coding)
```

**Spec naming convention:** `{week}_{phase}_{short-name}.md`
Example: `week1-2_phase-e_normalisation.md`

### 2.3 Spec Quality Checklist

P2/P3 must verify all items before handing a spec to P1:

| # | Check | Why It Matters |
|---|-------|----------------|
| 1 | Every field name matches the actual codebase (`metrics.py`, `trace.py`, etc.) | P1 should not have to guess or search |
| 2 | Every formula is unambiguous — P1 can write `=` directly | Prevents back-and-forth |
| 3 | Every edge case has a defined behaviour (division by zero, missing data, all-same values) | Prevents P1 from making arbitrary decisions |
| 4 | Every verification case has concrete expected output | P1 can copy directly into a unit test |
| 5 | Integration points list exact file paths | P1 knows which files to touch |
| 6 | Document is under 5 pages | Forces precision, prevents spec drift |

**Core principle**: After reading the spec, P1's only job is to write code. No further questions should be needed.

### 2.4 Spec Lifecycle

```
DRAFT  →  P2/P3 writing, not yet ready for P1
READY  →  Spec complete, all checklist items verified, handed to P1
IN PROGRESS → P1 is implementing
DONE   →  Code merged, implementation doc written, Gap Analysis updated
```

Update the `Status` field in the spec header as it progresses.

### 2.5 Current Specs

| Spec | Owner | Phase | Status |
|------|-------|-------|--------|
| [week1-2_phase-e_normalisation.md](./specs/week1-2_phase-e_normalisation.md) | P2 | Phase E | READY FOR IMPLEMENTATION |
| [week1-2_phase-d2_controllability.md](./specs/week1-2_phase-d2_controllability.md) | P3 | Phase D2 | READY FOR IMPLEMENTATION |
| [week3-4_phase-d1_robustness.md](./specs/week3-4_phase-d1_robustness.md) | P2 | Phase D1 | READY FOR IMPLEMENTATION |
| [week3-4_phase-c3_behavioural-safety.md](./specs/week3-4_phase-c3_behavioural-safety.md) | P3 | Phase C3 | READY FOR IMPLEMENTATION |

---

## 3. Weekly Plan

### Week 1–2: Core Evaluation Completion + Agent Stabilisation

**Objective**: Ensure all 4 agents run end-to-end; fill critical gaps in the evaluation framework

| Member | Task | Details | Deliverable |
|--------|------|---------|-------------|
| P1 | Agent end-to-end stabilisation | Fix all 4 agents to run successfully under `run_evaluation.py`; ensure every pattern passes all 16 tasks; unify error handling | Run logs showing all 4 patterns passing |
| P2 | [Phase E](./PROJECT_GAP_ANALYSIS_AND_PLAN.md#phase-e-normalization-aggregation--composite-scoring): Normalisation + Composite Scoring | Write [Implementation Spec](./specs/week1-2_phase-e_normalisation.md) defining normalisation formula, dimension-to-sub-indicator mapping, composite scoring formula, edge cases, and verification cases. P1 implements after spec is READY. | Completed spec → P1 delivers new modules in `src/evaluation/scoring.py` |
| P3 | [Phase D2](./PROJECT_GAP_ANALYSIS_AND_PLAN.md#phase-d-systemic-layer-enhancement-dimensions-6--7): Controllability Completion | Write [Implementation Spec](./specs/week1-2_phase-d2_controllability.md) defining trace completeness formula, policy-flag rate calculation, resource efficiency normalisation, edge cases, and verification cases. P1 implements after spec is READY. | Completed spec → P1 delivers new `ControllabilityResult` in `src/evaluation/controllability.py`; fixes stubbed policy check in `evaluator.py`; Dim 7 aggregation owned by Phase E |

**Acceptance Criteria**: `python run_evaluation.py --mode full` succeeds for all 4 patterns and outputs scores

#### P1 Progress Log (2026-03-12)

**Completed Fixes:**

| # | Issue | Root Cause | Fix | Modified Files |
|---|-------|-----------|-----|----------------|
| 1 | ToT 10/16 tasks timed out (avg 129s, close to 3min timeout) | `TOT_CONFIG` parameters too large (depth=3, thoughts=3, top_k=2), ~22 LLM calls per task | Reduced parameters: `max_depth: 3→2`, `thoughts_per_level: 3→2`, `top_k_selection: 2→1`, LLM calls per task reduced from ~22 to ~7 | `src/agent/pattern_tree_of_thoughts.py` |
| 2 | Tool-class tasks C1–C4: all patterns achieved only 0–25% success | C1–C4 require `weather_api`/`fx_api`/`wiki_search`/`shopping_search`, but these tools were not implemented; agents could only hallucinate outputs | Added 5 mock tools (`weather_api`, `fx_api`, `calculator`, `wiki_search`, `shopping_search`) with return values matching `test_suite.py` ground_truth | `src/tool/tool.py` |
| 3 | Reflex token data anomaly (avg 41 tokens, far below actual) | In evaluation mode, LLM response was discarded and replaced with `AIMessage(content=...)`, losing `usage_metadata` | Accumulated token usage across all LLM calls; manually set on final `AIMessage.usage_metadata` | `src/agent/pattern_reflex.py` |
| 4 | No per-task timeout protection; long-running tasks cannot be terminated | `graph.invoke()` had no timeout mechanism | Wrapped with `asyncio.wait_for()`, default 3-minute timeout (`--timeout` flag configurable); timeout marks task as failed | `src/evaluation/evaluator.py`, `run_evaluation.py` |
| 5 | Overall success rate too low (max 62.5%); agent output format did not match judge expectations | Evaluator did not guide prompt formatting; Judge lenient mode had insufficient answer extraction | Evaluator layer added `_wrap_prompt_for_evaluation()` to wrap prompts (does not affect agents themselves); enhanced Judge lenient mode: case-insensitive matching, numeric equivalence, stronger answer extraction, JSON numeric tolerance | `src/evaluation/evaluator.py`, `src/evaluation/judge.py` |
| 6 | Missing raw LLM control group; cannot quantify improvement from agent frameworks | No baseline comparison | Added Baseline pattern (single LLM call, no tools/reasoning/iteration) as control group in all evaluation modes | `src/agent/pattern_baseline.py`, `run_evaluation.py` |
| 7 | Full evaluation took 3h20m (local Ollama), far exceeding expectations | 6 patterns executed sequentially + 5s delay between tasks (unnecessary for local) | Patterns executed in parallel (`asyncio.gather`); delay reduced from 5s to 1s; added `--sequential` flag to fall back to sequential mode | `src/evaluation/evaluator.py`, `run_evaluation.py` |

**First Run Results (Before Fixes):**

| Pattern | Strict Success Rate | Efficiency Data | Issue |
|---------|-------------------|-----------------|-------|
| ReAct | 43.8% | 16/16 normal | — |
| ReAct_Enhanced | 37.5% | 16/16 normal | — |
| CoT | 62.5% | 16/16 normal | — |
| Reflex | 43.8% | Token data anomaly (avg 41) | Fix #3 |
| ToT | 25.0% | Only 6/16 had efficiency data | Fix #1 |

---

### Week 3–4: Behavioural Layer — Three Dimensions

**Objective**: Complete all 3 Behavioural layer dimensions (Dim3, Dim4, Dim5)

| Member | Task | Details | Deliverable |
|--------|------|---------|-------------|
| P1 | [Phase C1](./PROJECT_GAP_ANALYSIS_AND_PLAN.md#phase-c-behavioural-layer-completion-dimensions-3-4-5): Action–Decision Alignment (Dim3) | Extract plan string vs actual action from traces; implement string-level matching; verb–tool mapping (e.g. "search" → `tavily_search`); compute alignment score. Ref: [Proposal § 2.2.2 Dim3](../Group-1.pdf) | Alignment scoring logic |
| P2 | [Phase D1](./PROJECT_GAP_ANALYSIS_AND_PLAN.md#phase-d-systemic-layer-enhancement-dimensions-6--7): Enhanced Robustness (Dim6) | Write Implementation Spec (`docs/specs/week3-4_phase-d1_robustness.md`) defining perturbation strategy, temperature sweep parameters, variance calculation formula, degradation metric, and verification cases. P1 implements after spec is READY. Ref: [Proposal § 2.2.3 Dim6](../Group-1.pdf) | Completed spec → P1 delivers perturbation test pipeline + stability index |
| P3 | [Phase C3](./PROJECT_GAP_ANALYSIS_AND_PLAN.md#phase-c-behavioural-layer-completion-dimensions-3-4-5): Behavioural Safety (Dim5) | Write Implementation Spec (`docs/specs/week3-4_phase-c3_behavioural-safety.md`) defining tool whitelist validation logic, domain regex rules, violation rate formula, and verification cases. P1 implements after spec is READY. Ref: [Proposal § 2.2.2 Dim5](../Group-1.pdf) | Completed spec → P1 delivers safety scoring module |

**Acceptance Criteria**: Dim3, 4, 5 all produce numerical output; robustness perturbation tests operational

#### P1 Progress Log (2026-04-01)

**Completed: Phase C1 — Action-Decision Alignment (Dim3)**

| # | Component | Details | Modified Files |
|---|-----------|---------|----------------|
| 1 | `AlignmentMetrics` dataclass | 7 fields: `total_plan_tasks`, `total_aligned_tasks`, `plan_adherence_rate`, `avg_sequence_match`, `avg_tool_coverage`, `avg_tool_precision`, `task_alignment_scores` + `overall_alignment()` method | `src/evaluation/metrics.py` |
| 2 | `VERB_TOOL_MAP` verb-tool mapping | Maps 12 natural-language verbs to concrete tool names (e.g. `"search"` → `["wiki_search", "shopping_search"]`, `"calculate"` → `["calculator"]`); case-insensitive lookup | `src/evaluation/evaluator.py` |
| 3 | `_expand_plan_with_verb_mapping()` | Expands plan entries using verb mapping before alignment scoring; exact tool names pass through unchanged | `src/evaluation/evaluator.py` |
| 4 | `_longest_common_subsequence()` | LCS dynamic programming algorithm for measuring plan-action sequence order fidelity | `src/evaluation/evaluator.py` |
| 5 | `_collect_alignment_metrics()` | Per-task: tool_coverage (recall), tool_precision, sequence_match (LCS ratio); aggregate: plan_adherence_rate (threshold ≥ 0.5) | `src/evaluation/evaluator.py` |
| 6 | `compute_dim3_scores()` | Dim3 normalised scoring integrated into `compute_all_scores()` + `NormalizedDimensionScores` | `src/evaluation/scoring.py` |
| 7 | Report & visualisation | Dim3 section in Markdown/JSON/CSV reports; Dim3 in normalised heatmap; radar chart picks up Dim3 dynamically | `src/evaluation/report_generator.py`, `src/evaluation/visualization.py` |
| 8 | Unit tests | 32 tests covering: AlignmentMetrics, LCS helper, _collect_alignment_metrics, verb-tool mapping, compute_dim3_scores, PatternMetrics integration | `tests/unit_tests/test_alignment.py` |

**Alignment Scoring Formula:**
- **tool_coverage** (recall) = |planned ∩ actual| / |planned|
- **tool_precision** = |planned ∩ actual| / |actual|
- **sequence_match** = LCS(planned, actual) / max(len(planned), len(actual))
- **task_alignment_score** = mean(coverage, precision, sequence_match)
- **overall_alignment** = mean(plan_adherence_rate, avg_coverage, avg_precision)

**Completed: Phase C3 Spec — Behavioural Safety (Dim5)**

| # | Spec Section | Details |
|---|-------------|---------|
| 1 | Output | `BehaviouralSafetyMetrics` dataclass (11 fields + `overall_safety()`) |
| 2 | Tool whitelist validation | Per-call authorized/unauthorized tracking; per-task compliance rate |
| 3 | Domain safety regex | 11 regex patterns across 5 categories (shell danger, code execution, injection, PII) |
| 4 | Phase E interface | `dim5_score = mean(tool_compliance_rate, domain_safety_score)` |
| 5 | Verification cases | 5 concrete test cases with expected numerical outputs |
| 6 | Integration points | CREATE `safety.py`, MODIFY `metrics.py`, `evaluator.py`, `scoring.py`, `report_generator.py` |

**Completed: Phase D1 — Enhanced Robustness & Scalability (Dim6)**

| # | Component | Details | Modified Files |
|---|-----------|---------|----------------|
| 1 | `RobustnessMetrics` D1 extension | 6 new fields: `perturbation_variant_count`, `absolute_degradation`, `stability_index`, `success_by_complexity`, `complexity_decline`, `scaling_score`; updated `calculate_degradation()` and `to_dict()` | `src/evaluation/metrics.py` |
| 2 | `_run_robustness_tests()` upgrade | Now iterates over ALL perturbation variants per task (previously only used the first) | `src/evaluation/evaluator.py` |
| 3 | `_collect_robustness_metrics()` D1 logic | Per-task robustness scoring (1.0/0.5/0.0); stability index via variance proxy; success-by-complexity grouping; complexity decline & scaling score | `src/evaluation/evaluator.py` |
| 4 | `_compute_success_by_complexity()` helper | Groups original results by complexity level (simple/medium/complex) and computes per-band success rate | `src/evaluation/evaluator.py` |
| 5 | `_compute_complexity_decline()` helper | `max(0, success_simple - success_complex)`; returns 0.0 if either level is missing | `src/evaluation/evaluator.py` |
| 6 | `compute_dim6_scores()` D1-aligned | New formula: `dim6 = mean(norm_degradation, stability_index, scaling_score)`; returns None when no perturbations | `src/evaluation/scoring.py` |
| 7 | Report & visualisation | D1 sub-indicators in Markdown/CSV; extended robustness plot with stability & scaling panels | `src/evaluation/report_generator.py`, `src/evaluation/visualization.py` |
| 8 | Unit tests | 29 tests covering all 6 spec verification cases + edge cases (no perturbations, S_clean==0, single variant, missing complexity levels, all same result) | `tests/unit_tests/test_robustness_d1.py` |

**D1 Scoring Formulas:**
- **absolute_degradation** = |S_clean - S_noisy|
- **degradation_percentage** = 100 × (S_clean - S_noisy) / S_clean (clamped to [0, 100])
- **per-task robustness** = mean(1.0 if both succeed, 0.5 if original succeeds & perturbed fails, 0.0 otherwise)
- **stability_index** = mean(1 - min(p×(1-p)/0.25, 1.0)) over tasks with ≥2 variants
- **complexity_decline** = max(0, success_simple - success_complex)
- **scaling_score** = 1 - complexity_decline
- **dim6_score** = mean(1 - degradation%/100, stability_index, scaling_score)

**Remaining Week 3-4 Work:**
- [ ] P1 implements Phase C3 (Behavioural Safety, Dim5) from P3's spec

---

### Week 5–6: Cognitive Layer + Statistical Rigor

**Objective**: Complete all 7 dimensions; establish multi-run + statistical analysis pipeline

| Member | Task | Details | Deliverable |
|--------|------|---------|-------------|
| P1 | [Phase B1](./PROJECT_GAP_ANALYSIS_AND_PLAN.md#phase-b-cognitive-layer-implementation-dimensions-1--2): Reasoning Quality (Dim1) | Use Judge-LLM for coherence scoring on reasoning traces (extract THINK steps, have external LLM score 1–5); self-consistency: run each task multiple times, compare final answer agreement. Ref: [Proposal § 2.2.1 Dim1](../Group-1.pdf) | Reasoning quality scoring pipeline |
| P2 | [Phase F](./PROJECT_GAP_ANALYSIS_AND_PLAN.md#phase-f-statistical-rigor--reproducibility): Statistical Rigor | Write Implementation Spec (`docs/specs/week5-6_phase-f_statistical-rigor.md`) defining multi-run pipeline parameters (N=3–5), mean/CI calculation formulas, effect size (Cohen's d) formula, output table schema, and verification cases. P1 implements after spec is READY. Ref: [Proposal § 2.3 Table 2 C4](../Group-1.pdf) | Completed spec → P1 delivers statistical analysis module |
| P3 | [Phase B2](./PROJECT_GAP_ANALYSIS_AND_PLAN.md#phase-b-cognitive-layer-implementation-dimensions-1--2): Cognitive Safety (Dim2) | Write Implementation Spec (`docs/specs/week5-6_phase-b2_cognitive-safety.md`) defining toxicity keyword list, unsupported claim detection rules, constraint adherence checks, hallucination proxy formula, and verification cases. P1 implements after spec is READY. Ref: [Proposal § 2.2.1 Dim2](../Group-1.pdf) | Completed spec → P1 delivers cognitive safety scoring module |

**Acceptance Criteria**: All 7 dimensions produce scores; multi-run and CI calculation supported

---

### Week 7–8: Full Experiment Execution + Data Collection

**Objective**: Collect complete experimental data; finalise all visualisations

| Member | Task | Details | Deliverable |
|--------|------|---------|-------------|
| P1 | Full experiment execution | Run 4 patterns × 16 tasks × 3–5 repeats; handle runtime bugs and edge cases; collect raw data; ensure reproducibility | Complete raw result dataset (JSON) |
| P2 | Sensitivity analysis + cross-comparison | Analyse weight variation impact on composite scores; cross-dimension analysis (e.g. reasoning depth vs efficiency trade-off); identify strengths/weaknesses per pattern | Sensitivity analysis results + trade-off analysis |
| P3 | [Phase G](./PROJECT_GAP_ANALYSIS_AND_PLAN.md#phase-g-final-report--visualization-polish): Visualisation upgrade | 7-dimension radar chart; per-pattern success heatmap; trade-off scatter plot; robustness degradation bar chart; statistical significance annotations; export all figures | Complete figure set in `reports/figures/` |

**Acceptance Criteria**: Complete dataset collected; all visualisation figures generated

---

### Week 9: Demo Preparation + Report Writing

**Objective**: Prepare supervisor demonstration; complete report body

| Member | Task | Details | Deliverable |
|--------|------|---------|-------------|
| P1 | Demo preparation | Prepare LangGraph Studio demonstration — show each agent's think→act→observe workflow; prepare comparison demo script (same task across 4 patterns); record/screenshot key workflows | Demo script + presentation materials |
| P2 | Report: Results & Analysis | Write experimental results chapter; comparative analysis of all patterns across 7 dimensions; trade-off discussion (corresponding to [Proposal § 3.1](../Group-1.pdf) and [§ 3.4](../Group-1.pdf)); statistical data tables | Report core chapter |
| P3 | Report: Methodology + Visualisation | Write methodology chapter (evaluation framework description, corresponding to [Proposal § 2](../Group-1.pdf)); embed visualisation results; compile evaluation guide (corresponding to [Proposal § 3.3](../Group-1.pdf)) | Report methodology chapter |

---

### Week 10: Buffer + Final Integration

**Objective**: Integrate all components; ensure quality

| Member | Task | Details | Deliverable |
|--------|------|---------|-------------|
| All | Report integration & review | Merge all chapters; unify formatting and terminology; cross-review | Final report |
| P1 | Code cleanup + reproducibility | Ensure `run_evaluation.py` reproduces all results end-to-end; clean up code; update README | Clean repository |
| P2 | Appendix + data | Supplement appendix (sensitivity analysis tables, raw data, confidence intervals) | Complete appendix |
| P3 | Final proofreading + formatting | Final report formatting; reference verification; ensure consistent figure numbering | Submission-ready report |

---

## 4. Key Milestones

| Deadline | Milestone | Acceptance Criteria |
|----------|-----------|---------------------|
| **End of Week 2** | Agent + Evaluation Pipeline runs end-to-end | `run_evaluation.py --mode full` succeeds for all 4 patterns |
| **End of Week 4** | Behavioural layer — all 3 dimensions computable | Dim3, 4, 5 all produce numerical output |
| **End of Week 6** | All 7 dimensions computable + statistical framework ready | All 7 dimensions produce scores; multi-run supported |
| **End of Week 8** | Full experimental data collected | Complete dataset + all visualisation figures |
| **End of Week 9** | Demo ready + report body complete | Demonstrable + report draft |
| **End of Week 10** | Final delivery | Report + code + Demo all ready |

---

## 5. Prioritisation Strategy

### 5.1 Must Have

| Item | Rationale |
|------|-----------|
| Dim4 Success & Efficiency | Core comparison metric; highest supervisor interest. Ref: [Proposal § 2.2.2 Dim4](../Group-1.pdf) |
| Dim6 Robustness (perturbation) | Explicitly promised in Proposal; a key differentiator. Ref: [Proposal § 2.2.3 Dim6](../Group-1.pdf) |
| Dim7 Controllability & Transparency | Trace completeness foundation already exists; easy to complete. Ref: [Proposal § 2.2.3 Dim7](../Group-1.pdf) |
| Normalisation + Composite Scoring | Without this, fair cross-pattern comparison is impossible. Ref: [Phase E](./PROJECT_GAP_ANALYSIS_AND_PLAN.md#phase-e-normalization-aggregation--composite-scoring) |
| Statistical Rigor (3–5 repeats + CI) | Explicitly promised in Proposal. Ref: [Proposal Table 2 C4](../Group-1.pdf) / [Phase F](./PROJECT_GAP_ANALYSIS_AND_PLAN.md#phase-f-statistical-rigor--reproducibility) |
| LangGraph Workflow Demo | Core requirement of the final goal. Ref: [Proposal § 3.4](../Group-1.pdf) |

### 5.2 Nice to Have (Can Use Proxy Substitutes)

| Item | Simplified Approach |
|------|---------------------|
| Dim2 Cognitive Safety | Simple keyword filter as proxy; no need for full retrieval verification |
| Dim5 Behavioural Safety | Static regex check as proxy |
| Dim1 Reasoning Quality | Self-consistency (multi-run comparison) is easier to implement than Judge-LLM |
| Dim3 Action–Decision Alignment | String-level matching is sufficient; no need for embedding-based similarity |

### 5.3 Minimum Viable Plan (If Time Is Severely Limited)

Focus on the following to present effective results to the supervisor:

1. All 4 agents running end-to-end + Demo
2. Dim4 (Success & Efficiency) + Dim6 (Robustness) + Dim7 (Controllability) — full comparison across 3 dimensions
3. Normalisation + Composite Score
4. 3 repeated runs + basic statistics
5. Radar chart + comparison table + report

---

## 6. Risks & Mitigation

> Challenges and mitigation strategies defined in the Proposal: [Group-1.pdf § 2.3 Table 2](../Group-1.pdf)

| Risk | Proposal Challenge | Impact | Mitigation Strategy |
|------|-------------------|--------|---------------------|
| Unstable agent execution / frequent errors | C7 (Slow runs) | Blocks full experiments | Prioritise in Week 1–2; set token/time budgets and early-stop |
| LLM API cost overrun | C3 (Cost & latency) | Cannot complete enough repeated runs | Use free/low-cost providers (Ollama local, Groq); cache tool results |
| A dimension is too complex to implement | C2 (Metric availability) | Delays overall progress | Downgrade to proxy indicator; document in report |
| Uneven team progress | C6 (Scope & timeline) | Integration difficulties | Weekly sync meetings; hard checkpoints at Week 2, 4, 6 |
| ~~ToT runs too slowly~~ | C7 (Slow runs) | ~~Limits repeated experiment efficiency~~ | **Mitigated (2026-03-12)**: Reduced ToT parameters (depth=2, thoughts=2, top_k=1); added per-task timeout (default 3min, `--timeout` configurable) |
| ~~Full evaluation takes too long (3h20m)~~ | C7 (Slow runs) | ~~Blocks iteration efficiency~~ | **Mitigated (2026-03-13)**: 6 patterns executed in parallel (`asyncio.gather`); delay reduced from 5s to 1s; estimated reduction to 40–50min |

---

## 7. Weekly Sync Mechanism

- **Weekly team meeting** (30 min): progress sync + blocker discussion
- **End of Week 2, 4, 6**: Hard checkpoint reviews (against milestone acceptance criteria)
- **Shared board**: Use GitHub Issues/Projects to track each Phase's status
- **Code standards**: All code merged to main via PR review only
