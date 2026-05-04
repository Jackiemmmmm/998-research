# `reports/` — Evaluation Output Index

This folder is the **single source of truth** for evaluation outputs.
Different experiment configurations are distinguished by **filename suffix**, not by separate folders. Read this index first if you don't know which file to open.

---

## 🎯 What to read first

| If you want to... | Open this file |
|---|---|
| **Brief the supervisor in 5 minutes** | [`TALKING_POINTS.md`](./TALKING_POINTS.md) |
| **Read the full evaluation result** | [`evaluation_report.md`](./evaluation_report.md) |
| **See the headline numbers in spreadsheet form** | [`comparison_table.csv`](./comparison_table.csv) |
| **Programmatically inspect the raw data** | [`evaluation_results.json`](./evaluation_results.json) |
| **Show a chart** | [`figures/`](./figures/) (8 PNGs) |

---

## 📂 File layout & naming convention

### Canonical (the current best run — what to read by default)

The unsuffixed files **always** point to the **most recent canonical run**:

```
evaluation_report.md          ← canonical Markdown report
evaluation_results.json       ← canonical raw JSON
comparison_table.csv          ← canonical CSV table
figures/*.png                 ← canonical figures (8 of them)
TALKING_POINTS.md             ← supervisor-presentation cheat sheet
README.md                     ← this file
```

### Variant runs (archived comparisons)

When we run a different experiment configuration (different judge model,
different `--robustness-*` flag, etc.), we keep its outputs **in the same
folder** with a descriptive suffix `__<variant-id>-<YYYYMMDD>`. Format:

```
evaluation_report__<variant-id>-<date>.md
evaluation_results__<variant-id>-<date>.json
comparison_table__<variant-id>-<date>.csv
```

We do **not** archive variant figures by default (figures are easily
regenerated from the JSON).

#### Currently archived variants

| Suffix | Date | Difference vs canonical | Why kept |
|---|---|---|---|
| `__qwen25-once-20260503` | 2026-05-03 21:40 | Same judge (`qwen2.5:7b`), same N=3, but used `--robustness-once` (perturbation suite ran on run 1 only and was replayed). Has the pre-fix Dim 6 rendering bug. | Lets the supervisor see the *before* state and compare against the post-fix `--robustness-every-run` canonical. Useful when the supervisor asks "why did the ranking change?" |

### Archived obsolete data

Pre-Phase F runs (March / April 2026) used a **different JSON schema** —
no `run_records`, no `statistical_summaries`, no `pairwise_effect_sizes`
— so they cannot be apples-to-apples compared against current runs.
They are kept in compressed form for traceability only:

```
_archive_pre_phase_f.tar.gz   ← contains 3 historical pre-Phase F directories (~3 MB)
```

To inspect: `tar -tzf reports/_archive_pre_phase_f.tar.gz` (list contents)
or `tar -xzf reports/_archive_pre_phase_f.tar.gz -C /tmp/` (extract).

---

## 🧪 Canonical run reproducibility

Open [`evaluation_results.json`](./evaluation_results.json) → `metadata` block:

```json
{
  "generated_at": "2026-05-04T03:45:24",
  "num_runs": 3,
  "provider_model": { "provider": "ollama", "model": "llama3.1" },
  "judge_model": "qwen2.5:7b",
  "delay_between_tasks": 1.0,
  "task_timeout": 180.0,
  "parallel": true,
  "max_concurrency": 1,
  "robustness_reused": false,
  "seed_supported": true,
  "git_branch": "main",
  "git_commit": "41229e82..."
}
```

To reproduce on the same machine:

```bash
JUDGE_OLLAMA_MODEL=qwen2.5:7b python run_evaluation.py \
  --mode full --num-runs 3 --robustness-every-run \
  --concurrency 1 --delay 1.0 --timeout 180
```

Wall-clock ≈ 5 h 27 m on Apple Silicon + Ollama local backend.

---

## 🆕 How to re-run the evaluation

> **For the complete step-by-step guide** (prerequisites, troubleshooting, every CLI flag), open:
> 📖 **[`docs/HOW_TO_RUN_EVALUATION.md`](../docs/HOW_TO_RUN_EVALUATION.md)**
>
> The summary below is enough for someone who has already run the pipeline once before.

### 0. One-time setup (skip if already done)

```bash
brew install ollama          # if not installed
ollama serve &               # leave running
ollama pull llama3.1         # agent model (~5 GB)
ollama pull qwen2.5:7b       # judge model (~5 GB)
pip install -e . "langgraph-cli[inmem]"
```

### 1. Archive the current canonical (so it's not overwritten)

If the **current** `evaluation_report.md` etc. are worth keeping for
comparison after the new run, rename them with a descriptive suffix
**before** launching:

```bash
cd reports
SUFFIX="qwen25-everyrun-$(date +%Y%m%d)"   # e.g. qwen25-everyrun-20260504
for f in evaluation_report.md evaluation_results.json comparison_table.csv; do
  mv "$f" "${f%.*}__${SUFFIX}.${f##*.}"
done
cd ..
```

Then update the **"Currently archived variants"** table above with a
one-line entry describing what's different about this snapshot.

### 2. Launch the evaluation

The canonical configuration (~5 h 30 m on Apple Silicon):

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

For long runs, untie from the terminal so the process survives logout:

```bash
JUDGE_OLLAMA_MODEL=qwen2.5:7b nohup \
  python run_evaluation.py \
    --mode full --num-runs 3 --robustness-every-run \
    --concurrency 1 --delay 1.0 --timeout 180 \
  > /tmp/eval_$(date +%Y%m%d_%H%M%S).log 2>&1 &
echo "PID=$!"
```

Watch progress: `tail -f /tmp/eval_*.log`

### 3. When it finishes

The same canonical filenames in this folder are **overwritten** with
fresh data. Open the report:

```bash
open reports/evaluation_report.md          # main markdown report
open reports/figures/radar_comparison.png  # 7-dim radar
open reports/TALKING_POINTS.md             # supervisor-presentation cheat sheet
```

The new report will contain (auto-generated, no manual editing required):
- 🎯 Executive Summary at the top with dual composite ranking
- Multi-run mean ± 95 % CI on every headline metric
- "Deterministic across N=K" annotation for patterns with std=0
- § 3 vs § 5 robustness ranking divergence note (data-aware)
- 🚧 Dim 2 placeholder section with one row per pattern
- § 7 Cohen's d auto-caveat when small std is detected

### 4. Quick-iteration alternatives (when you don't have 5 hours)

| When | Command | Time |
|---|---|---|
| Sanity-check after code change | `python run_evaluation.py --mode quick --num-runs 1 --robustness-once` | 5–15 min |
| Same data, skip robustness reruns | Add `--robustness-once` instead of `--robustness-every-run` | ~ 4 h |
| Single category | `--mode category --category reasoning` | varies |

⚠ **Quick / once modes are NOT acceptable for final-report data.** They produce reports flagged with `insufficient_runs: true` or `robustness_reused: true` in metadata.

### 5. If something goes wrong

Open **[`docs/HOW_TO_RUN_EVALUATION.md`](../docs/HOW_TO_RUN_EVALUATION.md) § 6 Troubleshooting** — covers:
- Ollama daemon not responding
- Model not pulled
- `JUDGE_OLLAMA_MODEL` not set warning
- Run hung / OOM
- "insufficient_runs" warning explained

---

## 🧪 Run the unit tests

Before launching a long evaluation after any code change:

```bash
python -m pytest tests/unit_tests/ --ignore=tests/unit_tests/test_configuration.py
# Should report: 219 passed
```

Saves you 5 hours of wall-clock if you've broken something.
