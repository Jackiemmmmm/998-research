# Project Gap Analysis & Implementation Plan

> Generated: 2026-03-03
> Last Updated: 2026-03-12 (Week 1-2 P1 Agent 稳定化修复)
> Based on: Group-1.pdf (Project Proposal) + CLAUDE.md + Current Codebase Review

## Phase Implementation Status

| Phase | Description | Status | Implementation Doc |
|-------|-------------|--------|-------------------|
| **A** | Unified Telemetry & Adapter Layer | **COMPLETED** | [PHASE_A_UNIFIED_TELEMETRY.md](./PHASE_A_UNIFIED_TELEMETRY.md) |
| **B** | Cognitive Layer (Dim 1 & 2) | NOT STARTED | [PHASE_B_COGNITIVE_LAYER_PLAN.md](./PHASE_B_COGNITIVE_LAYER_PLAN.md) |
| **C** | Behavioural Layer (Dim 3, 4, 5) | NOT STARTED | — |
| **D** | Systemic Layer (Dim 6 & 7) | NOT STARTED | — |
| **E** | Normalization & Composite Scoring | NOT STARTED | — |
| **F** | Statistical Rigor & Reproducibility | NOT STARTED | — |
| **G** | Report & Visualization Polish | NOT STARTED | — |

---

## Part 1: Current Completion Status (Gap Analysis)

The proposal defines a **3-Layer, 7-Dimension** evaluation framework. Below is a dimension-by-dimension assessment of the current codebase against the proposal requirements.

### Summary Table

| # | Dimension | Layer | Status | Completion | Phase A Impact |
|---|-----------|-------|--------|------------|---------------|
| 1 | Reasoning Quality | Cognitive | NOT IMPLEMENTED | 0% | Trace foundation ready |
| 2 | Cognitive Safety & Constraint Adherence | Cognitive | NOT IMPLEMENTED | 0% | Trace foundation ready |
| 3 | Action-Decision Alignment | Behavioural | PREREQUISITE READY | 10% | THINK/ACT steps now captured |
| 4 | Success & Efficiency | Behavioural | PARTIALLY DONE | ~75% | Token accuracy improved; Reflex token tracking fixed (2026-03-12) |
| 5 | Behavioural Safety | Behavioural | NOT IMPLEMENTED | 5% | ToolCallRecord enables enforcement; mock tools added for C1-C4 (2026-03-12) |
| 6 | Robustness & Scalability | Systemic | PARTIALLY DONE | ~40% | — |
| 7 | Controllability, Transparency & Resource Efficiency | Systemic | PARTIALLY DONE | ~45% | TAO cycle tracking enabled |

**Overall estimated completion: ~25% → ~28% of the 7-dimension framework** (Phase A provides foundation for Dim 1, 3, 5, 7)

---

### Detailed Gap Analysis

#### Dimension 1: Reasoning Quality (Cognitive) - 0%

**Proposal requires:**
- Extract reasoning traces from structured logs
- Automated LLM-based coherence scoring
- Self-consistency analysis (multiple runs, embedding similarity, step-level alignment)
- Structural alignment via Levenshtein distance for step accuracy
- Final-answer agreement as proxy indicator

**Current status:**
- No reasoning trace extraction mechanism exists
- No coherence scoring implemented
- No self-consistency analysis (no repeated runs)
- No step-level alignment evaluation
- `LLMJudge` class exists in `judge.py` but only evaluates relevance/accuracy/completeness/conciseness, not reasoning coherence

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

#### Dimension 3: Action-Decision Alignment (Behavioural) - 0% → 10%

**Proposal requires:**
- Semantic comparison between planned and executed actions
- Verb-tool mappings and embedding-based similarity
- String-level matching of explicit plan strings ("Next I will...") as proxy

**Current status:**
- `TestTask` has a `plan` field (e.g., `["weather_api"]`) but it is never used during evaluation
- No comparison between agent's stated intention and actual actions
- ~~No telemetry captures the think-act-observe cycle per step~~ **RESOLVED by [Phase A](./PHASE_A_UNIFIED_TELEMETRY.md)**: `TraceExtractor` now captures `THINK` (intentions) and `ACT` (tool calls with `ToolCallRecord`) per step, enabling alignment comparison in Phase C1
- **(2026-03-12)**: C1-C4 任务所需的 mock 工具（`weather_api`, `fx_api`, `calculator`, `wiki_search`, `shopping_search`）已实现并注册到 `src/tool/tool.py`，agent 现在可以正确调用这些工具完成 tool 类任务

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

#### Dimension 5: Behavioural Safety (Behavioural) - 5%

**Proposal requires:**
- Tool invocation validated against whitelisted APIs
- Domain-restricted parameters
- Controlled execution environments (sandbox)
- Violation rates, blocked attempts, sandbox logs
- Static domain regex checks as Stage 1 proxy

**Current status:**
- `TestTask` has a `policy` field with `tool_whitelist`, but it is **never enforced** in the evaluator
- `ControllabilityMetrics` has `unauthorized_tool_uses` field but is always 0 (never tracked)
- No sandbox or controlled execution environment
- No violation tracking
- **(2026-03-12)**: Mock 工具已实现（`weather_api`, `fx_api`, `calculator`, `wiki_search`, `shopping_search`），为后续 tool whitelist 执行验证提供了前置条件

---

#### Dimension 6: Robustness & Scalability (Systemic) - ~40%

**Proposal requires:**
- Temperature/seed sweeps for variance-based stability indices
- Perturbation tests via nlpaug/textattack (paraphrases, typos)
- Degradation measurement: Delta = |S_clean - S_noisy|
- Progressive scaling experiments (performance vs task complexity)
- Multiple runs (3-5) with mean +/- 95% CI

**Current status (DONE):**
- Input perturbation tests exist (2 perturbations per task in test_suite.py)
- `RobustnessMetrics` with degradation calculation
- Original vs perturbed success rate comparison

**Current status (MISSING):**
- No temperature/seed sweep (variance-based stability)
- Perturbations are hand-written, not generated via nlpaug/textattack
- No progressive scaling experiments
- No multiple runs or confidence intervals
- No statistical rigor (mean +/- 95% CI)

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
- Transparency: compute trace completeness
  - `trace_completeness = steps_with_full_TAO / total_steps` (TAO = think-act-observe)
- Resource Efficiency: normalize token/time costs to 0-1
- (Optional Stage 2) Add runtime override test: measure stop/redo success rate
- (Optional Stage 2) Add judge-LLM clarity assessment for trace readability

**Files to create/modify:**
- `src/evaluation/evaluator.py` (MODIFY - add multi-run, temperature sweep)
- `src/evaluation/metrics.py` (MODIFY - add transparency metrics, normalization)
- `src/evaluation/robustness.py` (NEW - perturbation generation, scaling tests)

---

### Phase E: Normalization, Aggregation & Composite Scoring

**E1. Implement 0-1 normalization for all sub-indicators**
- Min-max normalization across patterns for each sub-indicator
- Handle edge cases (all same value, missing data)

**E2. Implement dimension-level scoring**
- Average sub-indicators within each dimension
- 7 dimension scores, each in [0, 1]

**E3. Implement composite scoring**
- Uniform weighting (default): `composite = mean(7 dimension scores)`
- Weighted option: configurable weights per dimension
- Sensitivity analysis: vary weights and observe rank stability

**E4. Update report generation**
- Add normalized scores table
- Add dimension-level comparison
- Add composite score ranking
- Add sensitivity analysis results

**Files to create/modify:**
- `src/evaluation/scoring.py` (NEW - normalization, aggregation, composite)
- `src/evaluation/report_generator.py` (MODIFY)
- `src/evaluation/visualization.py` (MODIFY - add 7-dimension radar, heatmap)

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
| **P2** | B1 | Reasoning Quality | Medium-High | NOT STARTED |
| **P2** | C1 | Action-Decision Alignment | Medium | NOT STARTED (prerequisite Phase A ready) |
| **P2** | C2 | Complete Success & Efficiency | Low | NOT STARTED |
| **P3** | D1 | Enhance Robustness | Medium | NOT STARTED |
| **P3** | D2 | Controllability & Transparency | Medium | NOT STARTED (prerequisite Phase A ready) |
| **P3** | C3 | Behavioural Safety | Medium | NOT STARTED (prerequisite Phase A ready) |
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
