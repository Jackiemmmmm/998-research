# Implementation Spec: Phase B1 — Reasoning Quality (Dimension 1)

> **Owner**: P1 (Yucheng Tu) — self-authored
> **Implementer**: P1 (Yucheng Tu)
> **Week**: 5–6
> **Phase**: [B1 — Reasoning Quality (Dim 1)](../PROJECT_GAP_ANALYSIS_AND_PLAN.md#dimension-1-reasoning-quality-cognitive---0)
> **Proposal Ref**: [Group-1.pdf § 2.2.1 Dim1](../Group-1.pdf) — "trace coverage, internal coherence, final-answer alignment, self-consistency across repeats"
> **Status**: READY FOR IMPLEMENTATION

---

## 1. Objective

Score the cognitive reasoning quality of each agent pattern by extracting `THINK` steps from `AgentTrace`, asking a Judge-LLM to rate coherence, checking that the final answer matches what the reasoning concluded, and (when multi-run data is available from Phase F) measuring answer consistency across repeats — all aggregated into a single `[0, 1]` Dim1 score.

---

## 2. Input

| Field | Source | Type | Sample | Usage |
|-------|--------|------|--------|-------|
| `trace.steps[*].step_type == THINK` | `src/evaluation/trace.py` `StepRecord` | `StepType` | `THINK` | Filter for reasoning steps |
| `trace.steps[*].content` | `StepRecord` | `str` | `"Let's compute 17×24 step by step..."` | Coherence judging input |
| `task.prompt` | `TestTask` | `str` | `"Compute 17 * 24..."` | Judge prompt context |
| `task.ground_truth` | `TestTask` | `Any` | `"408"` | Final-answer agreement reference |
| `task.judge` | `TestTask` | `Dict` | `{"mode": "exact"}` | Tells which extraction style to use |
| `result.output` | `TaskResult` | `str` | `"408"` | Agent's final answer |
| `result.judge_success` | `TaskResult` | `bool` | `True` | Reuse strict judge result for agreement |
| `result.lenient_judge_success` | `TaskResult` | `bool` | `True` | Reuse lenient judge result for partial agreement |
| Multi-run outputs (Phase F) | `PatternRunRecord` per task | `List[str]` | `["408", "408", "20"]` | Self-consistency input |

All fields exist today except for the multi-run aggregation, which is provided by Phase F.

---

## 3. Output

```python
# src/evaluation/reasoning_quality.py

@dataclass
class ReasoningQualityResult:
    """Per-task reasoning quality result."""

    task_id: str
    think_step_count: int
    missing_reasoning_trace: bool          # True when zero usable THINK steps

    trace_coverage: float                  # [0, 1]
    coherence_score: float                 # [0, 1] — from judge or fallback
    final_answer_agreement: float          # [0, 1] — 1.0 / 0.5 / 0.0
    self_consistency_score: Optional[float] # None when only one run available

    reasoning_quality_score: float         # weighted aggregate, [0, 1]
    judge_used_fallback: bool              # True when judge invocation failed
    judge_explanation: str = ""

    def to_dict(self) -> Dict[str, Any]: ...


@dataclass
class CognitiveMetrics:
    """Per-pattern Dim1 aggregate (attached to PatternMetrics)."""

    total_tasks: int = 0
    tasks_with_reasoning: int = 0          # think_step_count > 0
    avg_trace_coverage: float = 0.0
    avg_coherence_score: float = 0.0
    avg_final_answer_agreement: float = 0.0
    avg_self_consistency_score: Optional[float] = None  # None if no multi-run data
    avg_reasoning_quality: float = 0.0
    judge_fallback_count: int = 0
    task_quality_scores: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]: ...
```

---

## 4. Computation Logic

### 4.1 Sub-indicator: `trace_coverage`

```
trace_coverage = min(1.0, think_steps / EXPECTED_MIN_THINK_STEPS)
```

- **`EXPECTED_MIN_THINK_STEPS = 2`** (global constant; rationale: a meaningful chain has at least one planning + one execution thought).
- A pattern with 0 THINK steps (e.g. Baseline) → `trace_coverage = 0.0` and `missing_reasoning_trace = True`.
- THINK steps with empty / placeholder content (e.g. `"[implicit reasoning]"` synthetic markers from `pattern_react`) **are excluded from the count**.

### 4.2 Sub-indicator: `coherence_score`

A new `ReasoningJudge` (in `reasoning_quality.py`) uses a **separate local judge model** distinct from the agent's own LLM, obtained from a new `LLMConfig.get_judge_llm()` factory. This removes the self-evaluation bias inherent in using the same model the agents run on.

**Judge model selection**:
- Default: read env var `JUDGE_OLLAMA_MODEL` (recommended: `qwen2.5:7b` or `mistral:7b`).
- If unset: fall back to `LLMConfig.get_model()` (same model as agents) and emit a one-time warning. This keeps the implementation usable on machines without a second model pulled.
- Always uses the same Ollama base URL — no API/network dependency added.
- `temperature=0` for deterministic judging.

**Prompt**:

```
Rate the following reasoning chain on two axes (0.0–1.0 each):
- logical_progression: do later steps follow from earlier ones?
- internal_consistency: are there contradictions or non-sequiturs?
Return STRICT JSON: {"logical_progression": x, "internal_consistency": y, "explanation": "..."}.
```

```
coherence_score = (logical_progression + internal_consistency) / 2
```

**Fallback when judge fails or returns malformed JSON**:

```
coherence_score = 0.5      # neutral baseline
judge_used_fallback = True
```

**Empty trace** (`missing_reasoning_trace = True`):

```
coherence_score = 0.0      # nothing to evaluate
judge_explanation = "no THINK steps to evaluate"
# do NOT call the judge (saves cost)
```

**Concurrency**: judge calls across tasks are wrapped in `asyncio.gather()` so all per-task coherence evaluations for one pattern run in parallel (limited only by Ollama's local concurrency).

### 4.3 Sub-indicator: `final_answer_agreement`

Reuse existing judge results to avoid duplicate work:

| Condition | Score |
|-----------|-------|
| `result.judge_success == True` (strict match) | `1.0` |
| `result.lenient_judge_success == True` only | `0.5` |
| Both `False` | `0.0` |
| `ground_truth is None` (e.g. regex tasks) | use `judge_success` only: `1.0` / `0.0` |

Rationale: Stage 1 from the Phase B plan (§6.5 step B3) calls for "exact / lenient extracted / numeric / keyword overlap" — all of those are already encoded in the existing `Judge.evaluate()` strict + lenient pipeline. No new comparison code is needed.

### 4.4 Sub-indicator: `self_consistency_score`

Available only when Phase F multi-run data exists. Uses the same lenient-matching pipeline already accepted by the project for success-rate judgement, so that two runs the evaluator already calls "equivalent answers" are also counted as agreeing here.

```
self_consistency_score = largest_equivalence_class(answers) / total_runs
```

**Equivalence partitioning of `answers`** (the N final outputs of the same `(pattern, task_id)`):

1. **Pre-extract** each output with `Judge._extract_answer(output, ground_truth, judge_config)` to obtain a canonical surface form.
2. **Pairwise compare** extracted outputs using `Judge._values_match_lenient(...)`, which already implements:
   - case-insensitive string comparison,
   - numeric tolerance (`abs(a-b) < 1e-6`),
   - element-wise list comparison,
   - key-wise dict comparison (handles JSON field reordering and nested values).
3. Group outputs into equivalence classes by transitive closure of pairwise matches.
4. `self_consistency_score = size(largest_class) / total_runs`.

**Mode-specific notes**:
- exact-mode: `_extract_answer` already strips boilerplate ("The answer is …"), then lenient compare handles case + numeric.
- json-mode: `_extract_answer` is a no-op; lenient dict compare handles reordering and nested case differences.
- regex-mode: `_extract_answer` is a no-op; fall back to case-insensitive string comparison via `_values_match_lenient`.

If `total_runs < 2`: `self_consistency_score = None` (do **not** force `0.0` or `1.0` — Phase B plan §11 explicitly warns against false zeros).

**Consistency invariant**: under this rule, if all N runs' lenient judge says the answer is correct, `self_consistency_score = 1.0`. This avoids the contradictory situation where the evaluator says all runs answered correctly but Dim1 reports them as inconsistent.

### 4.5 Aggregation: `reasoning_quality_score`

Weights from Phase B plan §6.3:

```
W = {trace_coverage: 0.15, coherence: 0.40, final_answer: 0.20, self_consistency: 0.25}
```

When `self_consistency_score is None`, renormalise over the remaining three:

```
W' = {trace_coverage: 0.15/0.75, coherence: 0.40/0.75, final_answer: 0.20/0.75}
   = {0.20, 0.5333, 0.2667}
```

Output is always in `[0, 1]`.

### 4.6 Pattern-level aggregation

`CognitiveMetrics` averages each sub-indicator over the per-task results. `avg_self_consistency_score` is the mean of non-None per-task self-consistency values, or `None` if every task only had one run.

### 4.7 Phase E integration: `compute_dim1_scores()`

```python
# src/evaluation/scoring.py

def compute_dim1_scores(
    pattern_metrics: Dict[str, PatternMetrics],
) -> Dict[str, Optional[float]]:
    result = {}
    for name, m in pattern_metrics.items():
        cog = m.cognitive
        if cog.total_tasks == 0 or cog.tasks_with_reasoning == 0:
            result[name] = None     # not evaluable
        else:
            result[name] = cog.avg_reasoning_quality
    return result
```

Wired into `compute_all_scores()` and `NormalizedDimensionScores.dim1_reasoning_quality` (the field already exists as a placeholder).

### 4.8 Phase F integration

`run_evaluation.py` multi-run loop (Phase F) calls a new helper after collecting all run records:

```python
inject_self_consistency_scores(pattern_run_records, pattern_metrics)
```

This helper:
1. Groups outputs by `(pattern_name, task_id)` across runs.
2. Computes normalised majority count per group.
3. Updates the latest single-run `ReasoningQualityResult.self_consistency_score`.
4. Recomputes `reasoning_quality_score` for that task and refreshes `CognitiveMetrics` aggregates.

When Phase F is run with `--num-runs 1`, this helper is a no-op.

---

## 5. Edge Cases

| Case | Behaviour |
|------|-----------|
| Pattern produces 0 THINK steps (Baseline) | `trace_coverage = 0`, skip judge, `coherence_score = 0`, `reasoning_quality_score` reflects only `final_answer_agreement` proportionally |
| Only synthetic `[implicit reasoning]` THINK steps | Treated as 0 usable THINK steps; same as above |
| Judge LLM call raises / times out | Catch, set `coherence_score = 0.5`, `judge_used_fallback = True`, log; never propagate exception |
| Judge returns invalid JSON | Same fallback as above |
| Reasoning chain longer than ~8 KB | Truncate to last 8 KB before judging (caps prompt cost; LLM judge prompt budget configurable as `MAX_REASONING_CHARS = 8000`) |
| `ground_truth is None` (regex-mode tasks) | `final_answer_agreement = judge_success ? 1.0 : 0.0` |
| `total_runs == 1` | `self_consistency_score = None`; aggregation renormalises |
| Every per-task `self_consistency_score is None` | `CognitiveMetrics.avg_self_consistency_score = None`; Phase E formula uses single-run weights |
| All patterns have `cognitive.tasks_with_reasoning == 0` | `compute_dim1_scores` returns `{p: None}`; `NormalizedDimensionScores.dim1_reasoning_quality` stays `None`; composite score skips Dim1 |

---

## 6. Integration Points

| Action | File | What to do |
|--------|------|------------|
| CREATE | `src/evaluation/reasoning_quality.py` | `ReasoningQualityResult`, `CognitiveMetrics`, `ReasoningExtractor.extract(trace)`, `ReasoningJudge.evaluate(...)`, `compute_task_reasoning_quality(task, result, runs=None)` |
| MODIFY | `src/evaluation/metrics.py` | Add `cognitive: CognitiveMetrics` field to `PatternMetrics`; include in `to_dict()` and `summary()` |
| MODIFY | `src/evaluation/evaluator.py` | Add `_collect_cognitive_metrics()` called inside `evaluate_pattern()` after existing collectors; runs per-task reasoning quality computation |
| MODIFY | `src/evaluation/scoring.py` | Add `compute_dim1_scores()`; wire into `compute_all_scores()` so `NormalizedDimensionScores.dim1_reasoning_quality` is populated |
| MODIFY | `src/evaluation/report_generator.py` | New "Dim1 — Reasoning Quality" section in Markdown/JSON; new column in summary CSV |
| MODIFY | `src/evaluation/visualization.py` | Dim1 row in normalised heatmap (no new chart needed for B1) |
| MODIFY | `src/evaluation/judge.py` | Expose `Judge._extract_answer` and `Judge._values_match_lenient` as module-level helpers (or keep them as classmethods but ensure they are callable from `reasoning_quality.py`) |
| MODIFY | `src/llm_config.py` | Add `LLMConfig.get_judge_llm()` factory: reads `JUDGE_OLLAMA_MODEL` env var, returns a separate `ChatOllama` for judge use; falls back to `get_model()` with a one-time warning if the env var is unset |
| MODIFY | `run_evaluation.py` | Call `inject_self_consistency_scores()` in the Phase F multi-run aggregation step |
| CREATE | `tests/unit_tests/test_reasoning_quality.py` | Cover all six verification cases below |
| MODIFY | `src/evaluation/__init__.py` | Export `ReasoningQualityResult`, `CognitiveMetrics`, `compute_dim1_scores` |

---

## 7. Verification Cases

### Case 1 — Baseline pattern (no reasoning trace)

```
Input:
  trace.steps with 0 THINK steps
  result.judge_success = True (correct answer "408")
Expected:
  think_step_count = 0
  missing_reasoning_trace = True
  trace_coverage = 0.0
  coherence_score = 0.0  (judge skipped)
  final_answer_agreement = 1.0
  self_consistency_score = None
  weights renormalised: 0.20 + 0.5333 + 0.2667
  reasoning_quality_score = 0.20*0 + 0.5333*0 + 0.2667*1.0 = 0.2667
```

### Case 2 — CoT pattern, healthy single run, judge succeeds

```
Input:
  3 valid THINK steps
  judge returns {"logical_progression": 0.8, "internal_consistency": 0.9}
  result.judge_success = True
Expected:
  trace_coverage = min(1.0, 3/2) = 1.0
  coherence_score = (0.8 + 0.9) / 2 = 0.85
  final_answer_agreement = 1.0
  self_consistency_score = None (single run)
  reasoning_quality_score = 0.20*1.0 + 0.5333*0.85 + 0.2667*1.0
                          = 0.20 + 0.4533 + 0.2667
                          ≈ 0.9200
```

### Case 3 — Judge LLM fails (network error)

```
Input:
  2 valid THINK steps
  ReasoningJudge.evaluate() raises RuntimeError
  result.judge_success = False
  result.lenient_judge_success = True
Expected:
  trace_coverage = 1.0
  coherence_score = 0.5  (fallback)
  judge_used_fallback = True
  final_answer_agreement = 0.5
  self_consistency_score = None
  reasoning_quality_score = 0.20*1.0 + 0.5333*0.5 + 0.2667*0.5
                          = 0.20 + 0.2667 + 0.1333
                          = 0.6000
```

### Case 4 — Multi-run with full agreement

```
Input (3 runs of same task):
  outputs = ["408", "408", "408"]
  per-run trace_coverage = 1.0, coherence = 0.85, final_answer_agreement = 1.0
Expected (latest run after injection):
  self_consistency_score = 3/3 = 1.0
  reasoning_quality_score = 0.15*1.0 + 0.40*0.85 + 0.20*1.0 + 0.25*1.0
                          = 0.15 + 0.34 + 0.20 + 0.25
                          = 0.94
```

### Case 5 — Multi-run with disagreement

```
Input (3 runs):
  outputs = ["408", "408", "412"]
  normalised majority count = 2
Expected:
  self_consistency_score = 2/3 ≈ 0.6667
```

### Case 6 — Mixed-mode self-consistency normalisation (lenient)

```
Input (3 runs of A2 — JSON task, ground_truth = {"name": "iPhone 15", "price": 999}):
  outputs = [
    '{"name": "iPhone 15", "price": 999}',
    '{ "price": 999, "name": "iPhone 15" }',     # different ordering
    '{"name": "iphone 15", "price": 999}'        # different casing
  ]
Expected:
  After Judge._extract_answer (no-op for json mode) + parse + Judge._values_match_lenient:
    - run 1 vs run 2: dict compare ignores key order → match
    - run 1 vs run 3: case-insensitive string compare on "name" → match
    - run 2 vs run 3: same → match
  largest equivalence class = {1, 2, 3}, size 3
  self_consistency_score = 3/3 = 1.0
```

### Case 7 — Self-consistency with one outlier (numeric)

```
Input (3 runs of A1 — exact-mode, ground_truth = "408"):
  outputs = [
    "408",
    "The answer is 408.",     # verbose form, extracts to "408"
    "412",                    # genuinely different answer
  ]
Expected:
  After _extract_answer: ["408", "408", "412"]
  Lenient pairwise:
    - run 1 vs run 2: numeric match → same
    - run 1 vs run 3: 408 != 412 → different
  largest equivalence class = {1, 2}, size 2
  self_consistency_score = 2/3 ≈ 0.6667
```

---

## 8. Open Questions — Resolved

1. **`EXPECTED_MIN_THINK_STEPS` (Q1) — Resolved as `2`.**
   Rationale: this is a balanced threshold. Baseline (0 THINK) scores `0.0` correctly; Reflex (1 synthesised THINK) scores `0.5`, reflecting that it produces a reaction without a developed chain; CoT/ReAct/ToT (≥2 THINK) saturate at `1.0`. The setting differentiates "no usable trace" from "minimum-effort trace" from "developed reasoning chain" without hardcoding pattern-specific thresholds. Revisit after the first full evaluation if Reflex's 0.5 looks unfair in practice.

2. **Judge model (Q2) — Resolved: separate local model via `LLMConfig.get_judge_llm()`.**
   Rationale: avoids the self-evaluation bias inherent in re-using the same model the agents run on, while keeping the implementation fully local (no API/network dependency). Default judge model is `qwen2.5:7b` (via `JUDGE_OLLAMA_MODEL` env var); `mistral:7b` is an acceptable substitute. Falls back to `get_model()` with a one-time warning when no second model has been pulled, so the code remains usable on minimal setups. No external API cost is introduced.

3. **Self-consistency normalisation (Q3) — Resolved: lenient match via `Judge._extract_answer` + `Judge._values_match_lenient`.**
   Rationale: the existing success-rate pipeline already accepts `_values_match_lenient` as the project's official "equivalent answer" definition. Reusing it for self-consistency keeps the dimension internally consistent: if all N runs are judged as correct under the lenient rule, `self_consistency_score = 1.0`. A stricter comparison would create the contradictory case where the evaluator says all runs answered correctly but Dim1 reports them as inconsistent.

4. **Per-task judge call cost (Q4) — Resolved: full 1-call-per-task with `asyncio.gather()` parallelism.**
   Rationale: this is an experimental research demo run on local Ollama; there is no API budget concern. Parallel judging across tasks within a pattern run keeps wall-clock cost low. No `--reasoning-judge-sample-rate` flag is required at Stage 1; coverage is `1.0` for every task, every pattern, every repeat.

---

## 9. Checklist Before Coding

- [x] Aggregation weights `(0.15 / 0.40 / 0.20 / 0.25)` and renormalisation rule confirmed.
- [x] `EXPECTED_MIN_THINK_STEPS = 2` confirmed.
- [x] Judge fallback value `0.5` (vs `0.0`) confirmed.
- [x] Judge model strategy confirmed (Q2 → separate local model).
- [x] Self-consistency strictness confirmed (Q3 → lenient).
- [x] Judge call coverage confirmed (Q4 → full 1-call-per-task with parallel execution).
- [x] All file paths in §6 exist or are clearly new files.
- [x] All seven verification cases include concrete numerical expected outputs.

---

## 10. Local Setup Notes (Judge Model Deployment)

The Phase B1 implementation does **not** require a second Ollama model to be present in order for the code to run. `LLMConfig.get_judge_llm()` is designed with a graceful fallback path:

| Setup state | Behaviour |
|-------------|-----------|
| `JUDGE_OLLAMA_MODEL` env var unset | Falls back to `LLMConfig.get_model()` (same model as agents) and emits a one-time warning. Code runs end-to-end; Dim1 self-eval bias is reintroduced and should be noted in any report generated from this run. |
| `JUDGE_OLLAMA_MODEL` set, model not pulled | `ChatOllama` raises a clear error at first judge call; users follow the error message to run `ollama pull <model>`. |
| `JUDGE_OLLAMA_MODEL` set, model pulled | Normal path. Judge runs on the second model. No self-eval bias. |

**Recommended deployment (Stage 1 final evaluation):**

```bash
# Pull a non-Llama-family judge model (Alibaba's Qwen series is the default choice).
ollama pull qwen2.5:7b

# In project .env:
JUDGE_OLLAMA_MODEL=qwen2.5:7b
```

Approximate footprint: 4.7 GB on disk, 5–6 GB unified memory at runtime. Comfortable on 16 GB Apple Silicon machines alongside the agent model.

**Resource-constrained alternatives** (acceptable substitutes — all from non-Llama families, so self-eval bias is still removed):

- `qwen2.5:3b` (~1.9 GB)
- `phi3:mini` (~2.3 GB, Microsoft)
- `mistral:7b` (~4.1 GB, Mistral AI)

**Suggested timing:**

- During implementation and unit tests → run with the fallback (no second model needed).
- Before producing data for the final report (Phase F multi-run evaluation) → pull `qwen2.5:7b` and set the env var.
