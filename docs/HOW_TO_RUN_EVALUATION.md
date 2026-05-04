# How to Run the Evaluation — Complete Guide

> **Audience**: Anyone who needs to run the evaluation pipeline and read results.
> No code-reading required. If you can copy-paste a command, you can run this.
>
> **What this guide covers**:
> 1. Prerequisites (one-time setup)
> 2. The 4 commands you'll actually use day-to-day
> 3. What files come out, where they go
> 4. How to read the results
> 5. Troubleshooting common failures
> 6. Quick command reference at the end

---

## 📋 TL;DR — Just want to run it?

```bash
# Make sure Ollama is running and models are pulled (one-time, see § 1)
ollama serve &                       # in a separate terminal
ollama pull llama3.1                 # agent model (~5 GB)
ollama pull qwen2.5:7b               # judge model (~5 GB)

# Run the canonical full evaluation (≈ 5h 30m on Apple Silicon)
JUDGE_OLLAMA_MODEL=qwen2.5:7b \
  python run_evaluation.py \
    --mode full \
    --num-runs 3 \
    --robustness-every-run \
    --concurrency 1 \
    --delay 1.0 \
    --timeout 180

# When done, open the result
open reports/evaluation_report.md
```

Read the rest of this guide if any of the above doesn't make sense.

---

## 1. Prerequisites — one-time setup

You need three things on the machine:

### 1.1 Python 3.12 + project dependencies

```bash
# From the project root
pip install -e . "langgraph-cli[inmem]"
```

(If you've already done this for development, skip.)

### 1.2 Ollama installed and running

We use **local Ollama** as the LLM backend — no API keys, no cloud costs.

```bash
# Install (one-time, macOS via Homebrew)
brew install ollama

# Start the daemon (leave it running in the background)
ollama serve &
```

Verify it's up:
```bash
curl http://localhost:11434/api/version
# → {"version":"0.12.x"}
```

### 1.3 Two models pulled

The evaluation uses two distinct models — agent and judge — to avoid self-evaluation bias:

```bash
# Agent model (the one being evaluated; ~5 GB download)
ollama pull llama3.1

# Judge model (rates the agent's reasoning; ~5 GB download)
ollama pull qwen2.5:7b
```

Verify:
```bash
ollama list
# Should show llama3.1 and qwen2.5:7b
```

> **Why two models?** The Phase B1 spec (`docs/PHASE_B_COGNITIVE_LAYER_PLAN.md`) explicitly warns about self-evaluation bias if the agent and judge are the same model. Using qwen2.5:7b as judge gives an independent grader from a different model family.

---

## 2. The 4 commands you'll actually use

### 2.1 ⭐ The canonical full evaluation (what to run for the final report)

```bash
JUDGE_OLLAMA_MODEL=qwen2.5:7b \
  python run_evaluation.py \
    --mode full \
    --num-runs 3 \
    --robustness-every-run \
    --concurrency 1 \
    --delay 1.0 \
    --timeout 180
```

**What it does**:
- Evaluates **6 patterns** (`Baseline`, `ReAct`, `ReAct_Enhanced`, `CoT`, `Reflex`, `ToT`) on **16 tasks** spanning 4 categories (baseline / reasoning / tool / planning).
- Repeats the full pipeline **N = 3 times** for statistical rigour (mean ± 95 % CI).
- Runs the **robustness perturbation suite inside every one of the 3 runs** — gives honest CI for `degradation_percentage`.
- Wraps each task with a **3-minute timeout**; tasks exceeding it are marked failed (not stuck).
- Uses **qwen2.5:7b** as the reasoning-quality judge.

**Wall-clock**: about **5h 27m on Apple Silicon (M-series) + Ollama local backend** (last measured 2026-05-04). Plan to launch in the evening.

**Output**: overwrites the canonical files in `reports/` (see § 3 below).

### 2.2 Quick mode (for development iteration)

```bash
JUDGE_OLLAMA_MODEL=qwen2.5:7b \
  python run_evaluation.py \
    --mode quick \
    --num-runs 1 \
    --robustness-once
```

**What it does**: subset of tasks, single run, perturbation only on run 1. Useful for verifying nothing crashes after a code change. Takes 5–15 minutes.

> ⚠ **Quick mode produces a "single-run" report** — no Executive Summary, no statistical CIs. The headline `insufficient_runs: true` flag is set in metadata. Use it for sanity checks, not for any reporting.

### 2.3 Category mode (focus on one task type)

```bash
python run_evaluation.py \
  --mode category --category reasoning \
  --num-runs 3 --robustness-every-run
```

Categories: `baseline`, `reasoning`, `tool`, `planning`. Useful when debugging a specific dimension (e.g. CoT failing on tool tasks).

### 2.4 Cost-controlled multi-run (when you don't want to wait 5 hours)

```bash
JUDGE_OLLAMA_MODEL=qwen2.5:7b \
  python run_evaluation.py \
    --mode full \
    --num-runs 3 \
    --robustness-once
```

`--robustness-once` runs the perturbation suite on run 1 only and reuses the data on runs 2 & 3. Saves ~1.5 hours but **underestimates the true robustness CI** (the report flags this with `robustness_reused: true` in metadata).

> Use this for development; **always use `--robustness-every-run` for the final supervisor-facing data**.

---

## 3. What outputs are produced

When the run finishes, `reports/` contains:

```
reports/
├── README.md                                ← index of files (read first)
├── TALKING_POINTS.md                        ← supervisor-presentation cheat sheet
│
├── evaluation_report.md                     ⭐ MAIN REPORT (markdown)
├── evaluation_results.json                  ← raw machine-readable data
├── comparison_table.csv                     ← spreadsheet view
│
├── figures/                                  (8 PNGs, regenerated on every run)
│   ├── radar_comparison.png                 ← 7-dimension radar chart
│   ├── normalised_heatmap.png               ← per-pattern × per-dim heatmap
│   ├── composite_ci.png                     ← composite score with CIs
│   ├── success_rate_comparison.png          ← Dim 4 with error bars
│   ├── robustness_comparison.png            ← Dim 6 with error bars
│   ├── controllability_comparison.png       ← Dim 7
│   ├── efficiency_comparison.png
│   └── success_by_category.png
│
└── _archive_pre_phase_f.tar.gz              ← historical pre-Phase F runs (compressed)
```

### Old runs from previous evaluations

If you want to keep a previous run for comparison **before launching a new one**, rename its files with a suffix:

```bash
cd reports
SUFFIX="qwen25-once-$(date +%Y%m%d)"
for f in evaluation_report.md evaluation_results.json comparison_table.csv; do
  mv "$f" "${f%.*}__${SUFFIX}.${f##*.}"
done
cd ..
# Now safely launch the new run; canonical filenames will be re-created
```

This keeps the folder flat (no nested directories) and self-documenting (filename tells you what it is). See `reports/README.md` for the naming convention.

---

## 4. How to read the results

### 4.1 Where to look first

| If you want to... | Open |
|---|---|
| Brief the supervisor in 5 min | `reports/TALKING_POINTS.md` |
| Read the full report | `reports/evaluation_report.md` ← **start here** |
| See numbers in a spreadsheet | `reports/comparison_table.csv` |
| Programmatically inspect data | `reports/evaluation_results.json` |
| Show a chart | `reports/figures/*.png` |

### 4.2 The headline numbers explained

The main report's **Executive Summary** at the top auto-generates 5 sections. The most important table is the **dual-view composite ranking**:

| View | What it does | When to use |
|---|---|---|
| **A — Evaluable-dim mean** (spec §5.7) | Average over the dimensions a pattern *can* be scored on; N/A excluded | Spec-compliant default. Rewards patterns with narrower capability surfaces. |
| **B — All-7-dim mean** (N/A → 0) | Treat unmeasurable dimensions as 0 | Fairer cross-pattern comparison when patterns differ in measurable surface. Penalises raw-LLM controls. |

A pattern's relative rank can flip dramatically between views — that flip is the report's main methodological insight, not a bug.

### 4.3 What each "Dim" means

| Dim | Name | Layer | Source |
|---|---|---|---|
| 1 | Reasoning Quality | Cognitive | Phase B1 — judge LLM coherence + self-consistency |
| 2 | Cognitive Safety | Cognitive | Phase B2 (P3 owner, in progress — placeholder) |
| 3 | Action–Decision Alignment | Behavioural | Phase C1 — plan vs actual tool-call match |
| 4 | Success & Efficiency | Behavioural | Phase E — strict success rate + normalised latency + tokens |
| 5 | Behavioural Safety | Behavioural | Phase C3 — tool whitelist + content regex |
| 6 | Robustness & Scalability | Systemic | Phase D1 — degradation under prompt perturbation |
| 7 | Controllability, Transparency, Resource Efficiency | Systemic | Phase D2 — trace completeness + policy compliance |

### 4.4 Where the numbers come from (reproducibility)

Open `reports/evaluation_results.json` → `metadata` block for:
- `generated_at` — timestamp
- `num_runs` — N (3 in canonical)
- `provider_model` — agent LLM (e.g. `{"provider": "ollama", "model": "llama3.1"}`)
- `judge_model` — Dim 1 judge (e.g. `qwen2.5:7b`)
- `git_branch` + `git_commit` — exact code state
- `seed_supported` — whether deterministic execution was active
- `robustness_reused` — whether `--robustness-once` was used (false = honest)

Anyone with the same Ollama models + same git commit can re-run and get the same numbers (modulo ToT's stochastic search).

---

## 5. Running unit tests

The whole codebase has **219 unit tests** that should pass on every commit:

```bash
python -m pytest tests/unit_tests/ --ignore=tests/unit_tests/test_configuration.py
```

> The `--ignore` flag skips one pre-existing import-path test that's unrelated to the evaluation pipeline. CI runs the full suite.

If you change anything in `src/evaluation/`, run the tests **before** launching a new full evaluation — saves you 5 hours if there's a bug.

---

## 6. Troubleshooting

### Ollama not responding / "connection refused"

```bash
# Check daemon
curl http://localhost:11434/api/version
# If it fails:
ollama serve &
```

### "Model 'llama3.1' not found"

```bash
ollama list
# If missing:
ollama pull llama3.1
ollama pull qwen2.5:7b
```

### `JUDGE_OLLAMA_MODEL` not set warning

You'll see this in the log:

```
WARNING: JUDGE_OLLAMA_MODEL is not set; reasoning-quality judge will fall back to the agent model.
```

This means **Dim 1 will be biased** (agent grades itself). Always set the env var:

```bash
export JUDGE_OLLAMA_MODEL=qwen2.5:7b
# or inline: JUDGE_OLLAMA_MODEL=qwen2.5:7b python run_evaluation.py ...
```

### Run is taking forever / hung

The default per-task timeout is 180 s (3 minutes). If a single task exceeds that, it's marked failed and the run continues.

If the **whole run** seems hung:
```bash
# Find the python PID
ps aux | grep run_evaluation | grep -v grep
# Check Ollama runner CPU usage
ps aux | grep "ollama runner" | grep -v grep
```
Low CPU on both → likely waiting on Ollama HTTP. High CPU on Ollama runner → it's actually working, just slow. Token counts and step counts in the log lines tell you which task it's on.

### Ollama OOM on parallel mode

`--concurrency 2` or higher can OOM Ollama with multiple model runners. **The canonical config uses `--concurrency 1`** — patterns evaluated serially, but tasks within a pattern run in async parallel. This is the reliable setting.

If you really want pattern-level parallelism, ensure ≥ 32 GB RAM and try `--concurrency 2`.

### "insufficient_runs: true" in metadata

You ran with `--num-runs 1` (or 2). The Phase F spec requires N ∈ [3, 5] for valid CIs; the report still generates but the executive summary is suppressed and a warning is printed. Re-run with `--num-runs 3` for any final-report data.

### Different judge model = different Dim 1 numbers

Setting `JUDGE_OLLAMA_MODEL` to a different model (e.g. `llama3.2` instead of `qwen2.5:7b`) **will produce different Dim 1 scores**. This is by design — Dim 1 is judge-LLM-dependent. To compare across judge models, archive the previous run with a suffix (see § 3) before re-running.

---

## 7. Command Cheat Sheet

```bash
# ===== One-time setup =====
brew install ollama
ollama serve &
ollama pull llama3.1
ollama pull qwen2.5:7b
pip install -e . "langgraph-cli[inmem]"

# ===== Canonical full evaluation (final report data) =====
JUDGE_OLLAMA_MODEL=qwen2.5:7b python run_evaluation.py \
  --mode full --num-runs 3 --robustness-every-run \
  --concurrency 1 --delay 1.0 --timeout 180

# ===== Quick smoke (5-15 min) =====
JUDGE_OLLAMA_MODEL=qwen2.5:7b python run_evaluation.py \
  --mode quick --num-runs 1 --robustness-once

# ===== Cheaper full run (skip robustness reruns) =====
JUDGE_OLLAMA_MODEL=qwen2.5:7b python run_evaluation.py \
  --mode full --num-runs 3 --robustness-once

# ===== Single category =====
JUDGE_OLLAMA_MODEL=qwen2.5:7b python run_evaluation.py \
  --mode category --category reasoning --num-runs 3 --robustness-every-run

# ===== Background run (long evaluation, untie from terminal) =====
JUDGE_OLLAMA_MODEL=qwen2.5:7b nohup python run_evaluation.py \
  --mode full --num-runs 3 --robustness-every-run \
  --concurrency 1 --delay 1.0 --timeout 180 \
  > /tmp/eval_$(date +%Y%m%d_%H%M%S).log 2>&1 &

# ===== Archive current canonical before re-running =====
cd reports
SUFFIX="qwen25-everyrun-$(date +%Y%m%d)"
for f in evaluation_report.md evaluation_results.json comparison_table.csv; do
  mv "$f" "${f%.*}__${SUFFIX}.${f##*.}"
done
cd ..

# ===== Run unit tests =====
python -m pytest tests/unit_tests/ --ignore=tests/unit_tests/test_configuration.py

# ===== Open the result =====
open reports/evaluation_report.md          # main report
open reports/figures/radar_comparison.png  # 7-dim radar
open reports/TALKING_POINTS.md             # supervisor cheat sheet
```

---

## 8. CLI flag reference (full)

| Flag | Default | Purpose |
|---|---|---|
| `--mode {full,quick,category}` | `full` | `full` = all 16 tasks; `quick` = subset; `category` = one task type |
| `--category {baseline,reasoning,tool,planning}` | — | Required when `--mode category` |
| `--num-runs N` | `3` | Phase F repeated runs (spec: 3–5; 1–2 accepted with `insufficient_runs=true`) |
| `--robustness-every-run` | ✅ default | Re-run perturbation suite in every of the N runs (honest CI) |
| `--robustness-once` | — | Run perturbations on run 1 only, replay onto 2..N (cheaper, sets `robustness_reused=true`) |
| `--concurrency N` | `1` | Max patterns running in parallel. Higher = faster but risks Ollama OOM. |
| `--sequential` | — | Force pattern-level sequential (overrides `--concurrency`) |
| `--delay D` | `1.0` | Seconds between tasks within a pattern (rate-limit guard) |
| `--timeout T` | `180.0` | Per-task timeout in seconds |
| `--output-dir DIR` | `reports/` | Where to write reports + figures |

| Env var | Purpose |
|---|---|
| `JUDGE_OLLAMA_MODEL` | Reasoning-quality judge model name (e.g. `qwen2.5:7b`). **Always set this for final-report runs.** |

---

## 9. Where to learn more

| Topic | File |
|---|---|
| What was built and why (Phase F design doc) | `docs/PHASE_F_STATISTICAL_RIGOR.md` |
| Per-phase implementation history | `docs/PHASE_A_*.md`, `PHASE_B_*.md`, `PHASE_D2_*.md` |
| 7-dimension framework definition | `docs/10_WEEK_PROJECT_PLAN_EN.md` § 1.2 |
| Project gap analysis + status | `docs/PROJECT_GAP_ANALYSIS_AND_PLAN.md` |
| Implementation specs (Week 1–6) | `docs/specs/` |
| Reports folder index | `reports/README.md` |
| Supervisor-presentation cheat sheet | `reports/TALKING_POINTS.md` |
