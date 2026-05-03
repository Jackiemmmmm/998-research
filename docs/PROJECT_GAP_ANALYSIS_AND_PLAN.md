# Project Gap Analysis & Implementation Plan

> Generated: 2026-03-03
> Last Updated: 2026-05-03 (Week 5-6 P1 Phase B1 Dim1 implementation)
> Based on: Group-1.pdf (Project Proposal) + CLAUDE.md + Current Codebase Review

## Phase Implementation Status

| Phase | Description | Status | Spec (P2/P3 → P1) | Implementation Doc (P1) |
|-------|-------------|--------|-------------------|------------------------|
| **A** | Unified Telemetry & Adapter Layer | **COMPLETED** | — | [PHASE_A_UNIFIED_TELEMETRY.md](./PHASE_A_UNIFIED_TELEMETRY.md) |
| **B1** | Cognitive Layer — Reasoning Quality (Dim 1) | **COMPLETED** | [week5-6_phase-b1_reasoning-quality.md](./specs/week5-6_phase-b1_reasoning-quality.md) (P1 self-authored) | — (inline in `reasoning_quality.py`, `evaluator.py`, `scoring.py`, `metrics.py`) |
| **B2** | Cognitive Layer — Cognitive Safety (Dim 2) | NOT STARTED | [week5-6_phase-b2_cognitive-safety.md](./specs/week5-6_phase-b2_cognitive-safety.md) (P3, PENDING) | — |
| **C1** | Action–Decision Alignment (Dim 3) | **COMPLETED** | — (P1 self-drives) | — (inline in evaluator.py, scoring.py) |
| **C3** | Behavioural Safety (Dim 5) | **COMPLETED** | [week3-4_phase-c3_behavioural-safety.md](./specs/week3-4_phase-c3_behavioural-safety.md) (P3) | — (inline in safety.py, evaluator.py, scoring.py) |
| **D1** | Enhanced Robustness (Dim 6) | **COMPLETED** | [week3-4_phase-d1_robustness.md](./specs/week3-4_phase-d1_robustness.md) (P2) | — (inline in evaluator.py, metrics.py, scoring.py) |
| **D2** | Controllability & Transparency (Dim 7) | NOT STARTED | [week1-2_phase-d2_controllability.md](./specs/week1-2_phase-d2_controllability.md) (P3, READY FOR IMPLEMENTATION) | — |
| **E** | Normalization & Composite Scoring | NOT STARTED | [week1-2_phase-e_normalisation.md](./specs/week1-2_phase-e_normalisation.md) (P2, READY FOR IMPLEMENTATION) | — |
| **F** | Statistical Rigor & Reproducibility | NOT STARTED | [week5-6_phase-f_statistical-rigor.md](./specs/week5-6_phase-f_statistical-rigor.md) (P2, PENDING) | — |
| **G** | Report & Visualization Polish | NOT STARTED | — | — |

---

## Part 1: Current Completion Status (Gap Analysis)

The proposal defines a **3-Layer, 7-Dimension** evaluation framework. Below is a dimension-by-dimension assessment of the current codebase against the proposal requirements.

### Summary Table

| # | Dimension | Layer | Status | Completion | Phase A Impact |
|---|-----------|-------|--------|------------|---------------|
| 1 | Reasoning Quality | Cognitive | **B1 COMPLETED** | ~70% | Phase B1 completed (2026-05-03): ReasoningExtractor + ReasoningJudge (separate local LLM via `LLMConfig.get_judge_llm()`) + 4-sub-indicator weighted scoring + self-consistency hook for Phase F |
| 2 | Cognitive Safety & Constraint Adherence | Cognitive | NOT IMPLEMENTED | 0% | Trace foundation ready |
| 3 | Action-Decision Alignment | Behavioural | **COMPLETED** | ~70% | AlignmentMetrics + verb-tool mapping + LCS sequence matching (2026-04-01) |
| 4 | Success & Efficiency | Behavioural | PARTIALLY DONE | ~75% | Token accuracy improved; Reflex token tracking fixed (2026-03-12) |
| 5 | Behavioural Safety | Behavioural | **COMPLETED** | ~70% | Phase C3 completed (2026-04-01): tool whitelist validation + domain safety regex + Dim5 scoring |
| 6 | Robustness & Scalability | Systemic | **D1 COMPLETED** | ~75% | Phase D1 completed (2026-04-01): all perturbations, stability index, complexity scaling |
| 7 | Controllability, Transparency & Resource Efficiency | Systemic | PARTIALLY DONE | ~45% | TAO cycle tracking enabled |

**Overall estimated completion: ~44% → ~52% → ~58% of the 7-dimension framework** (Phase C1 Dim3, Phase D1 Dim6, Phase C3 Dim5, Phase B1 Dim1 all completed)

---

### Detailed Gap Analysis

#### Dimension 1: Reasoning Quality (Cognitive) - 0% → ~70%

**Proposal requires:**
- Extract reasoning traces from structured logs
- Automated LLM-based coherence scoring
- Self-consistency analysis (multiple runs, embedding similarity, step-level alignment)
- Structural alignment via Levenshtein distance for step accuracy
- Final-answer agreement as proxy indicator

**Current status (DONE — Phase B1, 2026-05-03):**
- ~~No reasoning trace extraction mechanism exists~~ **RESOLVED**: `ReasoningExtractor.extract_reasoning_steps()` filters `THINK` steps from `AgentTrace`, dropping `[implicit reasoning]` placeholders and empty content
- ~~No coherence scoring implemented~~ **RESOLVED**: `ReasoningJudge.evaluate_coherence()` uses a separate local Judge-LLM (via `LLMConfig.get_judge_llm()`, env var `JUDGE_OLLAMA_MODEL`) to rate `logical_progression` and `internal_consistency` from a strict-JSON prompt; rule-based fallback (0.5) when judge fails
- ~~No self-consistency analysis (no repeated runs)~~ **INTERFACE READY**: `inject_self_consistency_scores()` and `compute_self_consistency_score()` ship as part of B1; activated when Phase F multi-run pipeline is in place
- ~~No step-level alignment evaluation~~ **PARTIALLY ADDRESSED**: `final_answer_agreement` reuses `Judge.evaluate()`'s strict + lenient outcome (`1.0 / 0.5 / 0.0`); embedding-level alignment deferred per Stage 1 plan
- ~~`LLMJudge` class only evaluates relevance/accuracy/completeness/conciseness~~ **NEW**: `ReasoningJudge` is a dedicated cognitive judge with its own structured prompt and result schema
- **Aggregation**: `reasoning_quality_score = 0.15·trace_coverage + 0.40·coherence + 0.20·answer_agreement + 0.25·self_consistency` (with single-run renormalisation when `self_consistency` is unavailable)
- **Spec**: [week5-6_phase-b1_reasoning-quality.md](./specs/week5-6_phase-b1_reasoning-quality.md) (DONE 2026-05-03)
- **Files**: `src/evaluation/reasoning_quality.py` (NEW), `src/evaluation/metrics.py` (added `CognitiveMetrics`), `src/evaluation/scoring.py` (`compute_dim1_scores`), `src/evaluation/evaluator.py` (`_collect_cognitive_metrics`), `src/llm_config.py` (`get_judge_llm`), `tests/unit_tests/test_reasoning_quality.py` (30 tests)
- **Status**: Dim1 produces scores for 3/6 patterns (CoT 0.78 / Reflex 0.82 / ToT 0.86); 3/6 patterns return `None` because their traces have zero usable THINK content (Baseline has none by design; ReAct's THINK content is filled with the synthetic placeholder under llama3.1)

---

#### Dimension 2: Cognitive Safety & Constraint Adherence (Cognitive) - 0%

**Proposal requires:**
- Automated lexical/semantic screening for toxicity or unsupported claims
- Secondary classifier or judge-LLM for factual grounding
- Hallucination detection (proportion of traces with unverifiable claims)
- Keyword-based anomaly detection as Stage 1 proxy

**Current status:**
- No toxicity/bias screening exists
- No hallucination detection mechanism
- No factual grounding verification
- No safety-related evaluation metrics collected

---

#### Dimension 3: Action-Decision Alignment (Behavioural) - 0% → 10% → ~70%

**Proposal requires:**
- Semantic comparison between planned and executed actions
- Verb-tool mappings and embedding-based similarity
- String-level matching of explicit plan strings ("Next I will...") as proxy

**Current status (DONE — Phase C1, 2026-04-01):**
- ~~`TestTask` has a `plan` field (e.g., `["weather_api"]`) but it is never used during evaluation~~ **RESOLVED**: `_collect_alignment_metrics()` now compares `TestTask.plan` against actual tool calls extracted from `AgentTrace`
- ~~No comparison between agent's stated intention and actual actions~~ **RESOLVED**: Full alignment scoring pipeline implemented
- ~~No telemetry captures the think-act-observe cycle per step~~ **RESOLVED by [Phase A](./PHASE_A_UNIFIED_TELEMETRY.md)**: `TraceExtractor` now captures `THINK` (intentions) and `ACT` (tool calls with `ToolCallRecord`) per step
- **(2026-03-12)**: Mock tools required by C1-C4 tasks (`weather_api`, `fx_api`, `calculator`, `wiki_search`, `shopping_search`) implemented and registered in `src/tool/tool.py`
- **(2026-04-01)**: Phase C1 implementation completed, including the following components:
  - `AlignmentMetrics` dataclass (metrics.py): tracks tool_coverage (recall), tool_precision (precision), sequence_match (LCS sequence match ratio), plan_adherence_rate
  - `VERB_TOOL_MAP` verb-tool mapping dictionary (evaluator.py): expands natural-language verbs (e.g. "search", "calculate") to concrete tool names, enabling plans to use high-level verbs
  - `_longest_common_subsequence()` LCS algorithm (evaluator.py): measures order fidelity between planned and actual tool calls
  - `compute_dim3_scores()` (scoring.py): Dim3 normalised scoring, integrated into `compute_all_scores()` and `NormalizedDimensionScores`
  - Report & visualisation (report_generator.py, visualization.py): Dim3 data added to Markdown/JSON/CSV reports and heatmap
  - 32 unit tests all passing (tests/unit_tests/test_alignment.py)

**Current status (REMAINING — Stage 2 future):**
- Embedding-based semantic similarity (advanced matching, not required)
- Extract natural-language intentions from THINK steps (e.g. "I will search for...") and compare against actual actions

---

#### Dimension 4: Success & Efficiency (Behavioural) - ~70% → ~75%

**Proposal requires:**
- Binary success outcome per run
- Token counts, execution time, API latency
- Normalized cost score combining token and time usage
- Step-count-to-budget ratio as proxy for efficiency

**Current status (DONE):**
- `SuccessMetrics`: task completion rates (strict + lenient)
- `EfficiencyMetrics`: latency, token usage, step counts, tool calls
- Per-category and per-complexity breakdown
- Controllability gap (lenient vs strict)
- **[Phase A](./PHASE_A_UNIFIED_TELEMETRY.md)**: Token counts now use `usage_metadata` when available (accurate), with `tokens_estimated` flag for fallback; `tool_call_count` is now accurately tracked; `tao_cycle_counts` added to `EfficiencyMetrics`
- **(2026-03-12)**: Reflex pattern token tracking fixed — `AIMessage.usage_metadata` now preserved from all LLM calls instead of being discarded when constructing the final response message

**Current status (MISSING):**
- No normalized cost score (proposal requires combining token + time into single 0-1 score)
- No step-count-to-budget ratio
- No cost-per-task estimation formula implemented

---

#### Dimension 5: Behavioural Safety (Behavioural) - 5% → ~15% → ~70%

**Proposal requires:**
- Tool invocation validated against whitelisted APIs
- Domain-restricted parameters
- Controlled execution environments (sandbox)
- Violation rates, blocked attempts, sandbox logs
- Static domain regex checks as Stage 1 proxy

**Current status (DONE — Phase C3, 2026-04-01):**
- ~~`TestTask` has a `policy` field with `tool_whitelist`, but it is **never enforced** in the evaluator~~ **RESOLVED**: `_collect_safety_metrics()` now validates tool calls against whitelist per task
- ~~`ControllabilityMetrics` has `unauthorized_tool_uses` field but is always 0 (never tracked)~~ **RESOLVED**: `BehaviouralSafetyMetrics` tracks authorized/unauthorized counts at per-call granularity
- ~~No violation tracking~~ **RESOLVED**: per-task and aggregate violation rates computed
- **(2026-03-12)**: Mock tools implemented (`weather_api`, `fx_api`, `calculator`, `wiki_search`, `shopping_search`), providing prerequisites for tool whitelist enforcement
- **(2026-04-01)**: Phase C3 implementation completed, including:
  - `src/evaluation/safety.py` (NEW): `UNSAFE_PATTERNS` (12 regex patterns across 5 categories), `check_tool_compliance()`, `check_content_safety()`, `compute_task_safety()`
  - `BehaviouralSafetyMetrics` dataclass (metrics.py): 10 fields + `overall_safety()` method
  - `_collect_safety_metrics()` (evaluator.py): per-task tool whitelist validation + content safety scanning
  - `compute_dim5_scores()` (scoring.py): integrated into `compute_all_scores()` and `NormalizedDimensionScores`
  - Report & visualisation updated with Dim5 data
  - 41 unit tests all passing (tests/unit_tests/test_safety.py)

**Current status (REMAINING — Stage 2 future):**
- No controlled execution environment / sandbox
- Domain regex is a proxy — not a full safety classifier
- No blocked-attempt enforcement (monitoring only, not blocking)

---

#### Dimension 6: Robustness & Scalability (Systemic) - ~40% → ~75%

**Proposal requires:**
- Temperature/seed sweeps for variance-based stability indices
- Perturbation tests via nlpaug/textattack (paraphrases, typos)
- Degradation measurement: Delta = |S_clean - S_noisy|
- Progressive scaling experiments (performance vs task complexity)
- Multiple runs (3-5) with mean +/- 95% CI

**Current status (DONE — Phase D1, 2026-04-01):**
- ~~Input perturbation tests exist (2 perturbations per task in test_suite.py)~~ **ENHANCED**: Now runs ALL perturbation variants per task (not just the first)
- ~~`RobustnessMetrics` with degradation calculation~~ **EXTENDED** with 6 new D1 fields:
  - `perturbation_variant_count`: total perturbed task executions
  - `absolute_degradation`: |S_clean - S_noisy|
  - `stability_index`: prompt-variant stability proxy via variance formula — `1 - min(p*(1-p)/0.25, 1.0)`
  - `success_by_complexity`: per-band success rate (simple/medium/complex)
  - `complexity_decline`: `max(0, success_simple - success_complex)`
  - `scaling_score`: `1 - complexity_decline`
- Original vs perturbed success rate comparison
- Per-task robustness scoring: 1.0 (both succeed), 0.5 (original succeeds, perturbed fails), 0.0 (otherwise)
- D1-aligned Dim6 formula: `dim6 = mean(norm_degradation, stability_index, scaling_score)`
- Report & visualisation updated with D1 sub-indicators
- 29 unit tests all passing (tests/unit_tests/test_robustness_d1.py)

**Current status (REMAINING — Stage 2 future):**
- No true temperature/seed sweep (requires refactoring pattern graphs into runtime-configurable factories)
- Perturbations are hand-written, not generated via nlpaug/textattack
- No multiple runs or confidence intervals (Phase F)
- No statistical rigor — mean +/- 95% CI (Phase F)

---

#### Dimension 7: Controllability, Transparency & Resource Efficiency (Systemic) - ~35% → ~45%

**Proposal requires:**
- Controllability: runtime override tests (stop/redo success rate)
- Transparency: trace completeness (proportion of steps with full think-act-observe)
- Transparency: human or judge-LLM clarity assessments
- Resource Efficiency: normalized token/time costs

**Current status (DONE):**
- `ControllabilityMetrics`: schema compliance, tool policy compliance, format compliance
- `LLMJudge` exists for qualitative evaluation
- Radar chart with 4-dimension comparison
- **[Phase A](./PHASE_A_UNIFIED_TELEMETRY.md)**: Unified think-act-observe log now exists — `AgentTrace.tao_cycles` and step type distribution enable `trace_completeness` calculation in Phase D2

**Current status (MISSING):**
- No runtime override tests
- ~~No trace completeness measurement (no unified think-act-observe log)~~ **PREREQUISITE RESOLVED by Phase A** — trace exists, but `trace_completeness` metric formula not yet implemented (Phase D2)
- No transparency scoring
- No resource efficiency normalization to 0-1 scale

---

### Cross-Cutting Gaps

| Gap Area | Description | Status | Resolved By |
|----------|-------------|--------|-------------|
| **Unified Adapter API** | Proposal requires a standardized think-act-observe interface across all patterns. | **RESOLVED** | [Phase A](./PHASE_A_UNIFIED_TELEMETRY.md) — `TraceExtractor` provides unified extraction across all 4 patterns via post-hoc parsing |
| **Unified Telemetry Schema** | No standardized log schema with: thought, action, observation, token_usage, latency, policy_flags, termination_state per step. | **RESOLVED** | [Phase A](./PHASE_A_UNIFIED_TELEMETRY.md) — `StepRecord` + `AgentTrace` with `StepType` enum (INPUT/THINK/ACT/OBSERVE/OUTPUT), token tracking, and TAO cycle detection |
| **0-1 Normalization** | Proposal requires all sub-indicators normalized to 0-1 range. Current metrics are raw values. | OPEN | Phase E |
| **Dimension-Level Scoring** | No averaging of sub-indicators into dimension scores. | OPEN | Phase E |
| **Composite Scoring** | No weighted/uniform combination of dimension scores into a final composite. | OPEN | Phase E |
| **Statistical Rigor** | No multiple runs (3-5), no confidence intervals, no seed fixing. | OPEN | Phase F |
| **Sensitivity Analysis** | No weight variation analysis in appendix. | OPEN | Phase F |

---

## Part 2: What's Working Well

| Area | Assessment |
|------|------------|
| **5+1 Patterns** | Baseline (raw LLM control group) + Reflex, ReAct, CoT (Sequential), ToT all implemented in LangGraph; ToT config optimized (depth=2, thoughts=2, top_k=1) to avoid timeout |
| **16 Test Tasks** | Well-structured across 4 categories (A/B/C/D) with complexity levels; C1-C4 mock tools implemented |
| **Task Timeout** | Per-task timeout (default 3min) via `asyncio.wait_for()`, configurable via `--timeout` CLI arg |
| **Parallel Execution** | Patterns run concurrently via `asyncio.gather` (default); `--sequential` flag for serial fallback; delay reduced from 5s to 1s |
| **Judge System** | 3 modes (exact, json, regex) with dual strict/lenient evaluation |
| **Metrics Collection** | 4-dimension structure mirrors the proposal's intent |
| **Visualization** | 6 plot types including radar chart |
| **Report Generation** | JSON, Markdown, CSV output formats |
| **CI/CD** | GitHub Actions with linting, type checking, tests |
| **Multi-Provider LLM** | Supports Ollama, Groq, Cerebras, Google Gemini |

---

## Part 3: Implementation Plan (Prioritized Phases)

### Phase A: Unified Telemetry & Adapter Layer (Foundation - CRITICAL) — COMPLETED

> **Status: COMPLETED** (2026-03-03)
> Full implementation details: **[PHASE_A_UNIFIED_TELEMETRY.md](./PHASE_A_UNIFIED_TELEMETRY.md)**
>
> This is the foundation for dimensions 1, 3, and 7. Without unified logging, most metrics cannot be collected.

**Implementation Summary:**

Adopted a **post-hoc message parsing** strategy instead of modifying pattern internals:

| Task | Planned | Implemented | Notes |
|------|---------|-------------|-------|
| A1. StepRecord | `telemetry.py` | `trace.py` — `StepRecord` + `StepType` enum + `ToolCallRecord` | Enhanced with TAO type system (INPUT/THINK/ACT/OBSERVE/OUTPUT) |
| A2. AgentTrace | `telemetry.py` | `trace.py` — `AgentTrace` with `compute_aggregates()`, `tao_cycles` | Includes token estimation tracking |
| A3. Pattern hooks | Modify 4 pattern files | `TraceExtractor` with 5 extractors | **Zero pattern modifications** — post-hoc parsing from response |
| A4. Evaluator integration | Modify evaluator | `evaluator.py` — `_run_single_task()` uses `TraceExtractor` | `tool_call_count`, `step_count` now accurate |

**Files created/modified:**
- `src/evaluation/trace.py` (NEW — core module)
- `tests/unit_tests/test_trace.py` (NEW — 28 tests, all passing)
- `src/evaluation/evaluator.py` (MODIFIED — trace integration)
- `src/evaluation/__init__.py` (MODIFIED — exports)
- `src/evaluation/metrics.py` (MODIFIED — `tao_cycle_counts`, `any_tokens_estimated`)

---

### Phase B: Cognitive Layer Implementation (Dimensions 1 & 2)

**B1. Reasoning Quality (Dimension 1)**
- Extract reasoning chains from `AgentTrace.steps[].thought`
- Implement coherence scoring via LLM-as-Judge (reuse/extend `LLMJudge`)
  - Prompt: "Rate the logical coherence of this reasoning chain 0-1"
- Implement self-consistency analysis:
  - Run each task N times (N=3 minimum)
  - Compare final answers across runs (majority vote agreement)
  - Use embedding similarity between reasoning traces (via sentence-transformers or LLM embeddings)
- Calculate `reasoning_quality_score` as average of sub-indicators

**B2. Cognitive Safety & Constraint Adherence (Dimension 2)**
- Stage 1 (proxy): Implement keyword-based anomaly detector
  - Toxicity keyword list
  - Contradiction detection (claims vs. known facts in ground truth)
  - Hallucination proxy: flag responses containing unsupported quantitative claims
- Implement a simple `SafetyScreener` class
  - Input: agent reasoning trace
  - Output: safety_score (0-1), flagged_segments list
- (Stage 2 future): Integrate external classifier or dedicated safety-judge LLM

**Files to create/modify:**
- `src/evaluation/reasoning_quality.py` (NEW)
- `src/evaluation/cognitive_safety.py` (NEW)
- `src/evaluation/metrics.py` (MODIFY - add CognitiveMetrics)

---

### Phase C: Behavioural Layer Completion (Dimensions 3, 4, 5)

**C1. Action-Decision Alignment (Dimension 3)**
- From `AgentTrace`, extract pairs of (stated_intention, actual_action)
  - For Sequential/CoT: compare plan steps with execution steps
  - For ReAct: compare "I will..." statements with tool calls
  - For Reflex: compare matched rule with action taken
- Implement string-level matching as Stage 1 proxy
- Calculate `alignment_score` per task

**C2. Complete Success & Efficiency (Dimension 4)**
- Implement normalized cost score: `cost = w1 * norm_tokens + w2 * norm_latency`
  - Normalize tokens to 0-1 via min-max across patterns
  - Normalize latency to 0-1 via min-max across patterns
- Implement step-to-budget ratio: `actual_steps / max_allowed_steps`
- Add cost-per-task estimation (if API pricing is known)

**C3. Behavioural Safety (Dimension 5)**
- Implement tool whitelist enforcement in evaluator:
  - Track tool calls from `AgentTrace`
  - Compare against `TestTask.policy.tool_whitelist`
  - Count violations
- Implement domain restriction validation (regex-based URL/param checking)
- Calculate `behavioural_safety_score` per task

**Files to create/modify:**
- `src/evaluation/action_alignment.py` (NEW)
- `src/evaluation/behavioural_safety.py` (NEW)
- `src/evaluation/metrics.py` (MODIFY - add alignment and safety metrics)
- `src/evaluation/evaluator.py` (MODIFY - collect alignment & safety data)

---

### Phase D: Systemic Layer Enhancement (Dimensions 6 & 7)

**D1. Enhance Robustness & Scalability (Dimension 6)**
- Add temperature/seed sweep:
  - Run each task with temperature in [0.0, 0.3, 0.7, 1.0]
  - Compute variance-based stability index
- Add automated perturbation generation (optional: use nlpaug if available, otherwise expand hand-written perturbations)
- Add progressive scaling test:
  - Measure success rate at each complexity level (simple -> medium -> complex)
  - Compute slope of performance decline
- Add multiple run support (N=3-5):
  - Compute mean, std, 95% CI for all metrics

**D2. Complete Controllability, Transparency & Resource Efficiency (Dimension 7)**

> **Spec**: [week1-2_phase-d2_controllability.md](./specs/week1-2_phase-d2_controllability.md) — READY FOR IMPLEMENTATION

- Transparency: compute trace completeness via TAO cycle proportion
  - `trace_completeness = (tao_cycles * 3) / len(steps)` — measures proportion of steps in complete THINK→ACT→OBSERVE sequences
- Policy compliance: replace stubbed tool policy check (currently hardcoded to 100%) with actual `ToolCallRecord.tool_name` vs `TestTask.policy.tool_whitelist` comparison
  - `policy_flag_rate = tasks_with_violations / total_tool_tasks`
- Resource Efficiency: `resource_efficiency = 1 - norm(total_tokens)` where norm = min-max across patterns
- D2 produces sub-indicators only; **Dim 7 aggregation is owned by Phase E** using unified 5-indicator formula
- (Optional Stage 2) Add runtime override test: measure stop/redo success rate
- (Optional Stage 2) Add judge-LLM clarity assessment for trace readability

**Files to create/modify:**
- `src/evaluation/controllability.py` (NEW — `ControllabilityResult` dataclass, trace completeness, policy violation detection, resource efficiency)
- `src/evaluation/evaluator.py` (MODIFY — replace stubbed policy check at line 479 with actual tool whitelist enforcement)
- `src/evaluation/metrics.py` (MODIFY — add `ControllabilityResult` reference to `PatternMetrics`; fix `unauthorized_tool_uses` and `tool_policy_compliant_tasks`)
- `src/evaluation/report_generator.py` (MODIFY — add trace completeness, policy flag rate, resource efficiency to output)

---

### Phase E: Normalization, Aggregation & Composite Scoring

> **Spec**: [week1-2_phase-e_normalisation.md](./specs/week1-2_phase-e_normalisation.md) — READY FOR IMPLEMENTATION

**E1. Implement 0-1 normalization for all sub-indicators**
- Hybrid strategy: Option B (use directly) for indicators already in [0, 1]; Option A (min-max) for unbounded indicators (latency, tokens, steps)
- Inversion (`1 - normalised`) for lower-is-better metrics (latency, tokens, degradation)
- Normalisation scope: per single run only, not across historical runs
- Handle edge cases: all same value → 1.0; single pattern → 1.0; x_max == x_min → 1.0; missing → None

**E2. Implement dimension-level scoring**
- Sub-indicator weights default to uniform (1/N), to be refined after first complete data run
- Dim 4 (Success & Efficiency): `(1/3) * success_rate + (1/3) * norm_latency + (1/3) * norm_tokens`
- Dim 6 (Robustness): `(1/3) * norm_degradation + (1/3) * recovery_rate + (1/3) * robustness_score`
- Dim 7 (Controllability): unified 5-indicator formula combining Phase D2 outputs with existing metrics:
  `(1/5) * trace_completeness + (1/5) * policy_compliance + (1/5) * resource_efficiency + (1/5) * schema_compliance + (1/5) * format_compliance`
- Dim 1, 2, 3, 5: output None until implemented in future phases
- Missing sub-indicators excluded from aggregation; dimension score computed from remaining indicators

**E3. Implement composite scoring**
- Uniform weighting (default): `composite = mean(available dimension scores)` — currently 1/3 across Dim 4/6/7; automatically becomes 1/7 when all dimensions are implemented
- Custom weights supported via config (`Dict[str, float]`) to override defaults
- Sensitivity analysis: vary weights and observe rank stability

**E4. Update report generation**
- Add normalized scores table
- Add dimension-level comparison
- Add composite score ranking
- Add sensitivity analysis results

**Files to create/modify:**
- `src/evaluation/scoring.py` (NEW — normalization, dimension aggregation, composite scoring, custom weight support)
- `src/evaluation/report_generator.py` (MODIFY — add normalised score tables, dimension comparison, composite ranking)
- `src/evaluation/visualization.py` (MODIFY — add 7-dimension radar chart, normalised heatmap)
- `src/evaluation/evaluator.py` (MODIFY — call `scoring.py` before `evaluate_multiple_patterns()` returns)

---

### Phase F: Statistical Rigor & Reproducibility

**F1. Fix model versions and seeds**
- Add seed configuration to LLMConfig
- Fix temperature across runs (unless doing temperature sweep)
- Document model version in evaluation metadata

**F2. Multiple runs with CI**
- Configure evaluator for N=3-5 repeated runs
- Compute mean +/- 95% confidence interval for all metrics
- Add error bars to all visualizations

**F3. Publish evaluation artifacts**
- Structured JSON logs per run
- Aggregate results with statistical measures
- Reproduction scripts

**Files to create/modify:**
- `src/llm_config.py` (MODIFY - add seed support)
- `src/evaluation/evaluator.py` (MODIFY - multi-run loop, CI calculation)
- `src/evaluation/visualization.py` (MODIFY - error bars)
- `run_evaluation.py` (MODIFY - configurable num_runs)

---

### Phase G: Final Report & Visualization Polish

**G1. Enhanced visualizations**
- 7-dimension radar chart (upgrade from current 4-dimension)
- Heatmap: patterns x dimensions
- Box plots showing distribution across multiple runs
- Progressive scaling line charts

**G2. Comparative analysis report**
- Per-dimension winner analysis
- Trade-off analysis (reasoning depth vs efficiency, robustness vs cost)
- Recommendations for architecture selection per task type

**G3. Documentation update**
- Update evaluation.md with full 7-dimension specification
- Write evaluation guide (setup, task structures, measures)
- Document proxy indicator methodology

---

## Part 4: Recommended Priority & Timeline

Given the project timeline (Figure 1 in proposal: Stage 3 Full Evaluation is ~Mar-May 2026), the recommended implementation order is:

| Priority | Phase | Description | Estimated Effort | Status |
|----------|-------|-------------|-----------------|--------|
| **P0** | A | Unified Telemetry & Adapter | High (foundation) | **COMPLETED** → [details](./PHASE_A_UNIFIED_TELEMETRY.md) |
| **P1** | E | Normalization & Composite Scoring | Medium | NOT STARTED |
| **P1** | F | Statistical Rigor (multi-run, CI) | Medium | NOT STARTED |
| **P2** | B1 | Reasoning Quality | Medium-High | **COMPLETED** (2026-05-03, P1 self-driven) |
| **P2** | C1 | Action-Decision Alignment | Medium | **COMPLETED** (2026-04-01) |
| **P2** | C2 | Complete Success & Efficiency | Low | NOT STARTED |
| **P3** | D1 | Enhance Robustness | Medium | **COMPLETED** (2026-04-01) |
| **P3** | D2 | Controllability & Transparency | Medium | NOT STARTED (prerequisite Phase A ready) |
| **P3** | C3 | Behavioural Safety | Medium | **COMPLETED** (2026-04-01) |
| **P4** | B2 | Cognitive Safety (proxy) | Medium | NOT STARTED |
| **P5** | G | Report & Visualization Polish | Medium | NOT STARTED |

**Rationale:**
- ~~Phase A is the foundation; without it, dimensions 1/3/7 cannot be properly measured~~ **Phase A COMPLETED** — foundation is now in place
- **Next priority**: Phase E/F provide the statistical framework the proposal explicitly requires
- Phase B/C fill the biggest dimensional gaps (3 out of 7 dimensions at 0%) — now **unblocked** by Phase A
- Phase D/G enhances and polishes what partially exists

---

## Part 5: Risk & Considerations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Trace collection adds overhead to pattern execution | Slight latency increase | Use lightweight callbacks, measure overhead |
| ~~ToT task timeout (>3min per task)~~ | ~~10/16 tasks timing out~~ | **MITIGATED (2026-03-12)**: Reduced ToT config (depth 3→2, thoughts 3→2, top_k 2→1); added per-task timeout with `--timeout` CLI arg |
| LLM-as-Judge reliability for reasoning quality | Scoring variance | Use multiple judge runs, average scores |
| Token budget for multi-run experiments | Cost increase ~3-5x | Start with N=3, use cheaper models (Groq) for repeat runs |
| Some proxy indicators may not correlate with proposal's intended measures | Academic rigor concern | Document assumptions clearly, cross-validate with human samples |
| Scope creep from implementing all 7 dimensions fully | Timeline risk | Strict phase boundaries, implement Stage 1 proxies first |
