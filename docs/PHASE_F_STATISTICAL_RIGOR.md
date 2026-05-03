# Phase F: Statistical Rigor & Reproducibility — Implementation

> Status: **COMPLETED** (2026-05-03)
> Owner: P2 (Yiming Wang) — Spec author
> Implementer: P1 (Yucheng Tu)
> Spec: [`docs/specs/week5-6_phase-f_statistical-rigor.md`](./specs/week5-6_phase-f_statistical-rigor.md)
> Project plan row: [Week 5–6 § Statistical Rigor](./10_WEEK_PROJECT_PLAN_EN.md#week-56-cognitive-layer--statistical-rigor)
> Gap analysis row: [Phase F](./PROJECT_GAP_ANALYSIS_AND_PLAN.md#phase-f-statistical-rigor--reproducibility)
> Proposal reference: [Group-1.pdf § 2.3 Table 2 C4](../Group-1.pdf)

---

## 1. What Phase F adds

The single-run pipeline (Phase A → Phase E) measures every pattern once and
emits a `PatternMetrics` for it. Phase F sits **above** that:

```
                                    ┌──────────────────────────────┐
                                    │  evaluate_multiple_patterns  │
                                    │  (Phase A → Phase E unchanged)│
                                    └──────────────┬───────────────┘
                                                   │
   --num-runs=N                                    ▼
   --robustness-{every-run|once}        Dict[str, PatternMetrics]
   --output-dir=...                                │
        │                                           ▼
        │                       flatten_pattern_metrics()  ← Phase F
        │                                           │
        ▼                                           ▼
  ┌─────────────────────┐               Dict[str, List[PatternRunRecord]]
  │   _run_multi loop    │── repeat N ──►            │
  │  (run_evaluation.py) │                           ▼
  └─────────────────────┘               aggregate_runs()  ← Phase F
                                                    │
                                                    ▼
                                       StatisticalReport
                                                    │
                                                    ▼
                              JSON / Markdown / CSV / matplotlib
                              (extended ReportGenerator + Visualizer)
```

The contract: **`PatternMetrics` is never modified**, the existing single-run
JSON/Markdown/CSV outputs are preserved verbatim, and Phase F adds new keys
on top (`run_records`, `statistical_summaries`, `pairwise_effect_sizes`,
`single_run_latest`).

---

## 2. New module: `src/evaluation/statistics.py`

### 2.1 Dataclasses

| Class | Spec § | Fields | Purpose |
|-------|--------|--------|---------|
| `StatisticalSummary` | 4 | `mean`, `std`, `ci95_low`, `ci95_high`, `n` | One metric × one pattern, aggregated across N runs |
| `PairwiseEffectSize` | 4 | `pattern_a`, `pattern_b`, `metric_name`, `cohens_d` | Cross-pattern effect size for one metric |
| `PatternRunRecord` | 4 + 5.5 | `run_index`, `pattern_name` + 6 raw + 7 dim + composite + `dim2_cognitive_safety` (forward-compat) | Flattened per-run, per-pattern view |
| `PatternStatistics` | 4 | `pattern_name`, `num_runs`, `run_records`, `summaries: dict[metric, StatisticalSummary]` | Per-pattern aggregate |
| `StatisticalReport` | 4 | `num_runs`, `per_pattern: dict[name, PatternStatistics]`, `pairwise_effect_sizes: dict[metric, list]` | Top-level Phase F output |

### 2.2 Statistical helpers

| Function | Formula (spec §) | Notes |
|----------|------------------|-------|
| `compute_mean(values)` | `(1/n) Σ xᵢ` | Raises on empty input. |
| `compute_sample_std(values, mean)` | `sqrt( Σ(xᵢ - μ)² / (n-1) )` (§ 5.2) | Returns 0.0 for n < 2. |
| `compute_ci95(values)` | `μ ± t_{0.975, n-1} · σ / √n` (§ 5.3) | Lookup table for n ∈ {2, 3, 4, 5}. CI collapses to mean for n < 2. |
| `compute_cohens_d(a, b)` | `(μ_a - μ_b) / σ_pooled` (§ 5.4) | Returns ±999.0 (sign of `μ_a - μ_b`) when pooled σ ≤ 1e-12 and means differ; 0.0 when means also equal. **Never returns ±inf**. |

The pooled-std epsilon (`_POOLED_STD_EPSILON = 1e-12`) is the difference
between the spec wording ("pooled_std == 0") and floating-point reality:
the sample std of `[0.8, 0.8, 0.8]` is ~1e-16, which would otherwise blow
the d statistic up to ~2 × 10¹⁵.

### 2.3 t-distribution lookup table

```python
T_CRITICAL_95 = {
    2: 12.706,  # df=1
    3: 4.303,   # df=2
    4: 3.182,   # df=3
    5: 2.776,   # df=4
}
```

n outside [2, 5] falls back to the largest tabulated value (defensive
only; the spec mandates 3 ≤ N ≤ 5 and the CLI clamps to that range).

### 2.4 Run-record flattening

`flatten_pattern_metrics(pattern_metrics, normalised_scores, composite_score, run_index)`
maps a single run's `PatternMetrics` + Phase E outputs to one
`PatternRunRecord`. Defensive `getattr` is used on every `dim*` field so
that Phase B2 (or any future phase) adding `dim2_cognitive_safety` to
`NormalizedDimensionScores` is automatically picked up without touching
the flattener.

### 2.5 Aggregation orchestrator

`aggregate_runs(records_by_pattern)` is the single entry point used by
the orchestrator in `run_evaluation.py`:

1. **Defensive check (§ 5.1)**: every pattern must have the same number
   of runs; otherwise `ValueError` (concurrency / model identifiers must
   stay constant; an uneven count is the strongest signal something
   diverged).
2. For each pattern, build `PatternStatistics`:
   - For every metric in `_METRIC_FIELDS_ORDERED` (success_rate_strict,
     success_rate_lenient, latency, tokens, degradation, controllability,
     dim1, dim2, dim3, dim4, dim5, dim6, dim7, composite): collect
     non-`None` values, then call `compute_ci95`.
   - **Per § 6 + Case 8**: when **every** value is `None` for a metric,
     omit the metric from `summaries` entirely. Run records keep `None`
     verbatim so reviewers can see which runs missed which dimensions.
3. For each metric in `PAIRWISE_EFFECT_SIZE_METRICS`
   (`composite_score`, `success_rate_strict` — spec § 5.4 + § 5.7):
   compute Cohen's d for every unordered pair `(a, b)`, emitted as a
   directed entry so reviewers can read effect direction without
   flipping signs.

---

## 3. Modified files

| File | What changed |
|------|--------------|
| `src/evaluation/__init__.py` | Export the Phase F dataclasses + helpers. |
| `src/evaluation/report_generator.py` | New module-level helpers `_git_rev()`, `_build_phase_f_metadata()`, `_render_statistical_section()`. `generate_json_report()` and `generate_markdown_report()` accept optional `statistical_report` + `run_metadata` kwargs and **extend** (never replace) the legacy outputs with `single_run_latest`, `run_records`, `statistical_summaries`, `pairwise_effect_sizes`. |
| `src/evaluation/visualization.py` | `generate_all_plots()` accepts `statistical_report`; `plot_success_rates` and `plot_efficiency_comparison` overlay 95 % CI error bars when multi-run data is available; new `plot_composite_ci()` method emits an additional bar plot with mean composite ± CI. All gracefully no-op for single-run. |
| `src/llm_config.py` | New `_ollama_supports_seed()` probe + `_resolve_seed()` helper. `LLMConfig.get_model()` accepts a `seed` kwarg; only wires it into `ChatOllama` when the installed `langchain_ollama` exposes it. `LLMConfig.get_model_info()` extends with `seed_supported: bool` and `seed: int | None` so the report metadata is honest. |
| `run_evaluation.py` | New `--num-runs` (default 3, accepts 1–5; 1 warns + sets `insufficient_runs=true`), `--robustness-every-run` / `--robustness-once` mutually-exclusive switch (default `every-run`), `--output-dir`. New `_run_multi()` orchestrator owns the loop; per-run `PatternMetrics` are flattened, optionally rebased on the first run's `RobustnessMetrics`, and aggregated; the existing Phase B1 self-consistency hook is invoked between aggregation and reporting. |

`PatternMetrics`, `NormalizedDimensionScores`, `CompositeScore` and
`evaluator.py` were **not** modified — they are consumed, not changed.
The flattening helper lives in `statistics.py` rather than `evaluator.py`
per spec § 7's "Keep single-run evaluation intact" rule and Open
Question 2's "above PatternEvaluator, not inside it".

---

## 4. Reproducibility metadata

The Phase F metadata block (spec § 5.6 + § 5.7) is built by
`_build_phase_f_metadata()` and emitted as the JSON `metadata` block + the
markdown header banner:

| Field | Source | Notes |
|-------|--------|-------|
| `generated_at` | `datetime.now().isoformat()` | |
| `num_runs` | CLI arg | |
| `provider_model.{provider, model}` | `LLMConfig.get_model_info()` | |
| `judge_model` | `JUDGE_OLLAMA_MODEL` env var | Falls back to `"unknown"` (matches Phase B1 runtime fallback). |
| `delay_between_tasks` | CLI arg | |
| `task_timeout` | CLI arg | |
| `parallel` | derived from `--sequential` | |
| `max_concurrency` | CLI arg | |
| `robustness_reused` | runtime flag | `True` when `--robustness-once` and N > 1. |
| `seed_supported` | `LLMConfig.get_model_info()` | Honest probe of installed `langchain_ollama`. |
| `seed` | resolved seed value | Only set when `seed_supported`. |
| `git_branch` | `git rev-parse --abbrev-ref HEAD` | `"unknown"` on failure. |
| `git_commit` | `git rev-parse HEAD` | `"unknown"` on failure. |
| `insufficient_runs` | `bool` | Only present when `num_runs == 1`. |

### Seed support honesty

`langchain_ollama >= 0.3.x` (the version pinned in `pyproject.toml`)
exposes `seed` as a top-level `ChatOllama` field, so on this machine
`seed_supported` reports **`True`**. Older versions silently dropped
unknown kwargs, which is why we probe `ChatOllama.model_fields`
explicitly rather than just passing the kwarg blindly. Other providers
(`groq`, `cerebras`, `google_genai`) do not expose seed control through
their langchain wrappers today, so they correctly report
`seed_supported = False`.

To use a fixed seed, set `EVAL_SEED=12345` in the environment (or
extend the CLI later to pass `--seed`).

---

## 5. Cost-control: `--robustness-every-run` vs `--robustness-once`

The robustness perturbation suite (Phase D1) doubles or triples the
wall-clock for any pattern that has perturbation variants. With N = 3
repeated runs, the cost compounds. Spec § 5.1 mandates the explicit
control:

- **`--robustness-every-run`** (default): the perturbation suite runs
  inside every one of the N runs. The robustness mean / CI is then
  fully honest; this is the right setting for the final paper.
- **`--robustness-once`**: the perturbation suite runs once on the
  first pass; subsequent passes copy that pass's `RobustnessMetrics`
  onto their own `PatternMetrics` before flattening, so all N records
  carry identical degradation / stability fields. The metadata block
  is marked `robustness_reused: true` so the report cannot be misread.

The implementation lives in `_reuse_robustness_metrics()` in
`run_evaluation.py`; it overwrites `pattern_metrics[name].robustness`
with the first run's object, leaving everything else (success,
efficiency, controllability, alignment, safety, cognitive) per-run.

---

## 6. Verification

### 6.1 Unit tests — 16 pass (all 8 spec verification cases)

`tests/unit_tests/test_statistics.py` mirrors the spec § 8 cases:

| Case | Test class | Notes |
|------|-----------|-------|
| 1 | `TestCase1MeanStd` | mean = 0.80, sample std = 0.20 |
| 2 | `TestCase2CI95` | n = 3 → CI ≈ [0.304, 1.296] (`abs=2e-3` to absorb the spec's intermediate rounding) |
| 3 | `TestCase3ZeroVarianceCI` | identical values → CI collapses; n < 2 also collapses |
| 4 | `TestCase4CohensD` | normal case → d = 3.0 |
| 5 | `TestCase5CohensDZeroVariance` | zero-variance fallback → ±999.0 (with the FP-noise epsilon guard); never returns ±inf |
| 6 | `TestCase6NoneHandling` | `[0.70, None, 0.90]` → mean=0.80, n=2 |
| 7 | `TestCase7Flattening` | ReAct flatten → `dim1_reasoning_quality=None` preserved |
| 8 | `TestCase8AllNoneOmitted` | all-`None` metric → omitted from summaries; `run_records` keep the `None` |

Plus two defensive companions (`TestPairwiseEffectSizes`,
`TestUnequalRunCountsRefused`) that exercise the orchestrator's invariants.

```text
$ python -m pytest tests/unit_tests/test_statistics.py -v
================================== 16 passed in 0.08s ===================================

$ python -m pytest tests/unit_tests/ --ignore=tests/unit_tests/test_configuration.py
================================== 203 passed in 0.15s ==================================
```

(`test_configuration.py` fails with `ModuleNotFoundError: No module
named 'agent'` even on `main` before this change — pre-existing import
path issue unrelated to Phase F.)

### 6.2 End-to-end smoke run (mocked)

A real `run_evaluation.py --mode quick --num-runs 2` would still take
several minutes because each run hits Ollama. To verify the end-to-end
schema in seconds, the smoke test mocks `evaluate_multiple_patterns()`
to return synthetic `PatternMetrics`. The mocked run produces:

```text
JSON top-level keys: ['comparison', 'composite_ranking', 'composite_scores',
                       'individual_metrics', 'metadata',
                       'normalised_dimension_scores',
                       'pairwise_effect_sizes', 'run_records',
                       'single_run_latest', 'statistical_summaries']

metadata keys: ['delay_between_tasks', 'generated_at', 'git_branch',
                'git_commit', 'judge_model', 'max_concurrency', 'num_runs',
                'parallel', 'patterns_evaluated', 'provider_model',
                'robustness_reused', 'seed', 'seed_supported',
                'task_timeout', 'total_patterns']

Summary for ReAct (N = 3):
  composite_score: mean=0.720, ci=[0.670, 0.770], n=3
  success_rate_strict: mean=0.500, ci=[0.500, 0.500], n=3
  avg_latency_sec: mean=1.520, ci=[1.470, 1.570], n=3
  ...

Pairwise effect sizes (composite_score):
  Baseline vs ReAct: cohens_d=0.0
```

Two further smoke tests confirm:

- `--num-runs 1` sets `insufficient_runs: true` and CIs collapse to mean.
- `--robustness-once` sets `robustness_reused: true` and all N
  per-pattern records carry identical `degradation_percentage`.

The smoke runs also confirm that:

- `evaluation_report.md` contains a "Statistical Rigor (Phase F)"
  section with the mean ± 95 % CI table and the pairwise composite
  effect-size table.
- `reports/figures/composite_ci.png` is emitted alongside the existing
  plots; `success_rate_comparison.png` and `efficiency_comparison.png`
  carry CI error bars and the title is suffixed `(95 % CI, N = …)`.

To run the live smoke test against Ollama on this machine:

```bash
JUDGE_OLLAMA_MODEL=qwen2.5:7b python run_evaluation.py \
    --mode quick --num-runs 2 --concurrency 1
```

(quick mode runs 4 baseline tasks across 3 patterns; the run takes
roughly `2 × ~3 min` end-to-end.)

---

## 7. Deviations from the spec

None of substance. The two minor calls were:

1. **Floating-point epsilon for Cohen's d zero-variance fallback.**
   Spec § 5.4 says "if pooled_std == 0". A naive equality check fails
   on identical input series because sample std picks up ~1e-16 of FP
   noise. We compare against `1e-12` instead, documented inline. Spec
   intent is preserved (no ±inf, returns ±999.0 / 0.0 as required); we
   are simply more defensive against FP behaviour the spec did not
   model.

2. **CI test tolerance.** Spec § 5.7 Case 2 publishes the CI as
   `[0.304, 1.296]`, which is the result of rounding the t margin
   intermediate (`4.303 × 0.11547 = 0.496`, then `0.80 - 0.496 = 0.304`).
   The unrounded margin is `0.4969`, so the unrounded CI is
   `[0.3031, 1.2969]`. We assert with `pytest.approx(0.304, abs=2e-3)`
   so the test reads the spec's published value rather than carrying
   the spec's rounding artefact into the production code. Spec
   compliance otherwise requires `rel=1e-3` and we honour it
   everywhere else.

---

## 8. Open questions / future work

- The Phase B1 `inject_self_consistency_scores()` hook fires from the
  multi-run loop, but it depends on per-task agent outputs being
  surfaced from `PatternMetrics` (`pm._task_outputs_for_run`). The
  current evaluator does not yet attach that cache, so on this
  implementation self-consistency only activates when a future patch
  surfaces those outputs. Phase F infrastructure is in place; the
  Dim1 self-consistency value remains `None` in single-run mode and
  through this multi-run path until the cache lands.
- `dim2_cognitive_safety` is already in `PatternRunRecord` so when
  P3's Phase B2 lands, no Phase F change is needed.
- Sensitivity analysis (Week 7-8 P2 task) consumes the
  `statistical_summaries` and `pairwise_effect_sizes` blocks directly.
