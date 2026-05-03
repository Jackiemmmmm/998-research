"""Phase B1 -- Reasoning Quality (Dimension 1).

Evaluates the cognitive reasoning quality of an agent pattern by:

1. Extracting THINK steps from each task's ``AgentTrace``.
2. Asking a separate Judge-LLM (``LLMConfig.get_judge_llm``) to rate
   coherence on two axes (logical_progression / internal_consistency).
3. Reusing the existing strict / lenient judge results to score
   final-answer agreement.
4. (Phase F) Measuring self-consistency across multi-run repeats with
   the project's lenient equivalence rule.

Spec: docs/specs/week5-6_phase-b1_reasoning-quality.md
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .judge import Judge
from .trace import AgentTrace, StepType

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Spec section 4.1: a meaningful chain has at least one planning + one
# execution thought, so coverage saturates at 2 usable THINK steps.
EXPECTED_MIN_THINK_STEPS: int = 2

# Spec section 5: cap reasoning text fed to the judge so prompts stay
# bounded.  Truncate to the LAST MAX_REASONING_CHARS characters of the
# concatenated chain (later steps tend to be more informative).
MAX_REASONING_CHARS: int = 8000

# Sub-indicator weights (spec section 4.5) used by
# ``_aggregate_with_renormalisation``.
_BASE_WEIGHTS: Dict[str, float] = {
    "trace_coverage": 0.15,
    "coherence": 0.40,
    "final_answer": 0.20,
    "self_consistency": 0.25,
}

# Synthetic placeholder text inserted by ``pattern_react`` when an LLM
# produced no explicit reasoning content for a tool-call step.  These are
# excluded from the THINK-step count per spec section 4.1.
_REACT_IMPLICIT_REASONING_MARKER: str = "[implicit reasoning]"


# ---------------------------------------------------------------------------
# Reasoning trace extraction
# ---------------------------------------------------------------------------

class ReasoningExtractor:
    """Extracts the usable reasoning steps from an ``AgentTrace``."""

    @staticmethod
    def extract_reasoning_steps(trace: Optional[AgentTrace]) -> List[str]:
        """Return the cleaned, ordered list of THINK-step contents.

        Filtering rules (spec section 4.1):

        - Keep only ``StepType.THINK`` steps.
        - Drop empty / whitespace-only content.
        - Drop the literal synthetic marker ``"[implicit reasoning]"``
          inserted by ``pattern_react`` when the LLM produced no
          reasoning text alongside its tool calls.
        - Normalise inner whitespace via ``str.split`` + ``" ".join``.
        - Preserve original order.
        """
        if trace is None:
            return []

        steps: List[str] = []
        for step in trace.steps:
            if step.step_type != StepType.THINK:
                continue

            content = step.content or ""
            content_stripped = content.strip()
            if not content_stripped:
                continue
            if content_stripped == _REACT_IMPLICIT_REASONING_MARKER:
                continue

            # Normalise inner whitespace so multi-line / multi-space
            # reasoning blocks compare cleanly later on.
            normalised = " ".join(content_stripped.split())
            steps.append(normalised)

        return steps


# ---------------------------------------------------------------------------
# Reasoning-quality judge
# ---------------------------------------------------------------------------

class ReasoningJudge:
    """LLM-as-Judge for coherence scoring.

    Uses a *separate* judge LLM obtained from
    ``LLMConfig.get_judge_llm()`` so reasoning quality is not graded by
    the same model that produced the reasoning (spec section 4.2).
    """

    _PROMPT_TEMPLATE = (
        "You are an expert evaluator of agent reasoning chains.\n\n"
        "Original query:\n{query}\n\n"
        "Reasoning chain (ordered THINK steps from the agent):\n"
        "{reasoning}\n\n"
        "Final agent output:\n{final_output}\n\n"
        "Rate the reasoning chain on two axes (each in [0.0, 1.0]):\n"
        "- logical_progression: do later steps follow from earlier ones?\n"
        "- internal_consistency: are there contradictions or "
        "non-sequiturs?\n\n"
        "Return STRICT JSON with no extra text, in this exact shape:\n"
        '{{"logical_progression": <float in [0,1]>, '
        '"internal_consistency": <float in [0,1]>, '
        '"explanation": "<one short sentence>"}}\n'
    )

    def __init__(self, llm: Any = None) -> None:
        """Initialise the judge.

        Args:
            llm: An optional pre-built chat model.  If ``None``, the
                judge model is fetched lazily from
                ``LLMConfig.get_judge_llm()`` on first use; callers that
                want the model created up-front can pass one in directly
                (useful in tests and when reusing a single client across
                tasks).
        """
        self._llm = llm

    @property
    def llm(self) -> Any:
        """Lazily-initialised judge LLM (built via ``get_judge_llm``)."""
        if self._llm is None:
            # Local import to avoid pulling LangChain into test paths
            # that monkey-patch the judge.
            try:
                from src.llm_config import get_judge_llm
            except ImportError:
                from llm_config import get_judge_llm
            self._llm = get_judge_llm()
        return self._llm

    @staticmethod
    def _truncate_reasoning(reasoning_steps: List[str]) -> str:
        """Join + truncate reasoning to ``MAX_REASONING_CHARS``.

        Truncation keeps the *tail* of the chain because later steps are
        usually closer to the final answer (spec section 5).
        """
        joined = "\n".join(
            f"{i + 1}. {s}" for i, s in enumerate(reasoning_steps)
        )
        if len(joined) <= MAX_REASONING_CHARS:
            return joined
        return "...\n" + joined[-MAX_REASONING_CHARS:]

    def evaluate_coherence(
        self,
        query: str,
        reasoning_steps: List[str],
        final_output: str,
    ) -> Tuple[float, str, bool]:
        """Score coherence of a single reasoning chain.

        Returns:
            ``(coherence_score, explanation, used_fallback)`` where
            ``coherence_score`` is the mean of ``logical_progression``
            and ``internal_consistency``.  On any error
            (network / parse / out-of-range) the score falls back to
            the neutral baseline ``0.5`` and ``used_fallback`` is True.
        """
        prompt = self._PROMPT_TEMPLATE.format(
            query=query,
            reasoning=self._truncate_reasoning(reasoning_steps),
            final_output=final_output,
        )

        try:
            response = self.llm.invoke(
                [{"role": "user", "content": prompt}]
            )
            content = (
                response.content
                if hasattr(response, "content")
                else str(response)
            )
            if isinstance(content, list):
                # Some LLM wrappers return list[dict]/list[str]; coerce.
                content = "".join(
                    part if isinstance(part, str) else str(part)
                    for part in content
                )

            try:
                parsed = Judge._extract_and_parse_json(content)
            except (json.JSONDecodeError, ValueError) as exc:
                logger.warning(
                    "ReasoningJudge: malformed JSON from judge LLM "
                    "(%s); falling back to neutral 0.5.",
                    exc,
                )
                return 0.5, f"fallback: malformed judge JSON ({exc})", True

            if not isinstance(parsed, dict):
                logger.warning(
                    "ReasoningJudge: judge JSON was not an object; got "
                    "%r. Falling back to neutral 0.5.",
                    type(parsed).__name__,
                )
                return 0.5, "fallback: judge JSON was not an object", True

            try:
                lp = float(parsed.get("logical_progression", 0.0))
                ic = float(parsed.get("internal_consistency", 0.0))
            except (TypeError, ValueError) as exc:
                logger.warning(
                    "ReasoningJudge: non-numeric coherence values (%s); "
                    "falling back to neutral 0.5.", exc,
                )
                return 0.5, f"fallback: non-numeric scores ({exc})", True

            # Clamp to [0, 1] just in case the judge over/undershoots.
            lp = max(0.0, min(1.0, lp))
            ic = max(0.0, min(1.0, ic))

            coherence = (lp + ic) / 2.0
            explanation = str(parsed.get("explanation", "")).strip()
            return coherence, explanation, False

        except Exception as exc:  # noqa: BLE001 -- judge must never crash eval
            logger.warning(
                "ReasoningJudge: judge invocation failed (%s); falling "
                "back to neutral 0.5.", exc,
            )
            return 0.5, f"fallback: judge invocation error ({exc})", True


# ---------------------------------------------------------------------------
# Result + metrics dataclasses
# ---------------------------------------------------------------------------

@dataclass
class ReasoningQualityResult:
    """Per-task reasoning-quality result."""

    task_id: str
    think_step_count: int
    missing_reasoning_trace: bool

    trace_coverage: float
    coherence_score: float
    final_answer_agreement: float
    self_consistency_score: Optional[float]

    reasoning_quality_score: float
    judge_used_fallback: bool
    judge_explanation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to a JSON-serialisable dict."""
        return {
            "task_id": self.task_id,
            "think_step_count": self.think_step_count,
            "missing_reasoning_trace": self.missing_reasoning_trace,
            "trace_coverage": round(self.trace_coverage, 4),
            "coherence_score": round(self.coherence_score, 4),
            "final_answer_agreement": round(self.final_answer_agreement, 4),
            "self_consistency_score": (
                round(self.self_consistency_score, 4)
                if self.self_consistency_score is not None
                else None
            ),
            "reasoning_quality_score": round(self.reasoning_quality_score, 4),
            "judge_used_fallback": self.judge_used_fallback,
            "judge_explanation": self.judge_explanation,
        }


@dataclass
class CognitiveMetrics:
    """Per-pattern Dim1 aggregate (attached to ``PatternMetrics``)."""

    total_tasks: int = 0
    tasks_with_reasoning: int = 0
    avg_trace_coverage: float = 0.0
    avg_coherence_score: float = 0.0
    avg_final_answer_agreement: float = 0.0
    avg_self_consistency_score: Optional[float] = None
    avg_reasoning_quality: float = 0.0
    judge_fallback_count: int = 0
    task_quality_scores: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to a JSON-serialisable dict."""
        return {
            "total_tasks": self.total_tasks,
            "tasks_with_reasoning": self.tasks_with_reasoning,
            "avg_trace_coverage": round(self.avg_trace_coverage, 4),
            "avg_coherence_score": round(self.avg_coherence_score, 4),
            "avg_final_answer_agreement": round(
                self.avg_final_answer_agreement, 4
            ),
            "avg_self_consistency_score": (
                round(self.avg_self_consistency_score, 4)
                if self.avg_self_consistency_score is not None
                else None
            ),
            "avg_reasoning_quality": round(self.avg_reasoning_quality, 4),
            "judge_fallback_count": self.judge_fallback_count,
            "task_quality_scores": {
                k: round(v, 4) for k, v in self.task_quality_scores.items()
            },
        }


# ---------------------------------------------------------------------------
# Aggregation helpers
# ---------------------------------------------------------------------------

def _aggregate_with_renormalisation(
    coverage: float,
    coherence: float,
    agreement: float,
    self_consistency: Optional[float],
) -> float:
    """Weighted aggregate with single-run renormalisation (spec 4.5).

    Base weights: ``{coverage: 0.15, coherence: 0.40, agreement: 0.20,
    self_consistency: 0.25}``.  When ``self_consistency`` is ``None``
    (single-run / Phase F not active), the remaining three weights are
    renormalised to sum to 1.

    Args:
        coverage: trace_coverage in [0, 1].
        coherence: coherence_score in [0, 1].
        agreement: final_answer_agreement in [0, 1].
        self_consistency: self_consistency_score in [0, 1] or ``None``.

    Returns:
        Aggregate reasoning-quality score in [0, 1].
    """
    if self_consistency is None:
        # Renormalise over the three single-run sub-indicators.
        denom = (
            _BASE_WEIGHTS["trace_coverage"]
            + _BASE_WEIGHTS["coherence"]
            + _BASE_WEIGHTS["final_answer"]
        )
        score = (
            (_BASE_WEIGHTS["trace_coverage"] / denom) * coverage
            + (_BASE_WEIGHTS["coherence"] / denom) * coherence
            + (_BASE_WEIGHTS["final_answer"] / denom) * agreement
        )
    else:
        score = (
            _BASE_WEIGHTS["trace_coverage"] * coverage
            + _BASE_WEIGHTS["coherence"] * coherence
            + _BASE_WEIGHTS["final_answer"] * agreement
            + _BASE_WEIGHTS["self_consistency"] * self_consistency
        )
    # Numerical clamp.
    return max(0.0, min(1.0, score))


def _final_answer_agreement(result: Any) -> float:
    """Spec section 4.3 — reuse strict / lenient judge results."""
    if getattr(result, "judge_success", False):
        return 1.0
    if getattr(result, "lenient_judge_success", False):
        return 0.5
    return 0.0


# ---------------------------------------------------------------------------
# Per-task computation
# ---------------------------------------------------------------------------

def compute_task_reasoning_quality(
    task: Any,
    result: Any,
    judge: Optional[ReasoningJudge] = None,
) -> ReasoningQualityResult:
    """Compute the per-task ``ReasoningQualityResult`` for a single run.

    Args:
        task: A ``TestTask`` (only ``id`` and ``prompt`` are used here).
        result: A ``TaskResult``-like object exposing
            ``trace``, ``output``, ``judge_success`` and
            ``lenient_judge_success``.
        judge: Optional ``ReasoningJudge`` instance to reuse across many
            tasks.  If ``None`` and there are usable THINK steps, a new
            judge is built lazily.  When the trace has zero usable
            THINK steps the judge is never invoked (spec section 4.2).

    Returns:
        A ``ReasoningQualityResult`` with ``self_consistency_score`` left
        as ``None`` (Phase F injects multi-run results later).
    """
    trace = getattr(result, "trace", None)
    reasoning_steps = ReasoningExtractor.extract_reasoning_steps(trace)
    think_step_count = len(reasoning_steps)
    missing_reasoning = think_step_count == 0

    trace_coverage = min(
        1.0, think_step_count / float(EXPECTED_MIN_THINK_STEPS)
    )
    final_answer_agreement = _final_answer_agreement(result)

    if missing_reasoning:
        coherence_score = 0.0
        judge_used_fallback = False
        judge_explanation = "no THINK steps to evaluate"
    else:
        local_judge = judge if judge is not None else ReasoningJudge()
        coherence_score, judge_explanation, judge_used_fallback = (
            local_judge.evaluate_coherence(
                query=getattr(task, "prompt", "") or "",
                reasoning_steps=reasoning_steps,
                final_output=getattr(result, "output", "") or "",
            )
        )

    reasoning_quality_score = _aggregate_with_renormalisation(
        coverage=trace_coverage,
        coherence=coherence_score,
        agreement=final_answer_agreement,
        self_consistency=None,
    )

    return ReasoningQualityResult(
        task_id=getattr(task, "id", getattr(result, "task_id", "")),
        think_step_count=think_step_count,
        missing_reasoning_trace=missing_reasoning,
        trace_coverage=trace_coverage,
        coherence_score=coherence_score,
        final_answer_agreement=final_answer_agreement,
        self_consistency_score=None,
        reasoning_quality_score=reasoning_quality_score,
        judge_used_fallback=judge_used_fallback,
        judge_explanation=judge_explanation,
    )


# ---------------------------------------------------------------------------
# Pattern-level aggregation
# ---------------------------------------------------------------------------

def aggregate_cognitive_metrics(
    per_task_results: List[ReasoningQualityResult],
) -> CognitiveMetrics:
    """Build a ``CognitiveMetrics`` from a flat list of per-task results."""
    metrics = CognitiveMetrics()
    metrics.total_tasks = len(per_task_results)
    if not per_task_results:
        return metrics

    metrics.tasks_with_reasoning = sum(
        1 for r in per_task_results if r.think_step_count > 0
    )
    metrics.avg_trace_coverage = sum(
        r.trace_coverage for r in per_task_results
    ) / len(per_task_results)
    metrics.avg_coherence_score = sum(
        r.coherence_score for r in per_task_results
    ) / len(per_task_results)
    metrics.avg_final_answer_agreement = sum(
        r.final_answer_agreement for r in per_task_results
    ) / len(per_task_results)

    # Self-consistency: average over per-task values that exist.
    sc_values = [
        r.self_consistency_score
        for r in per_task_results
        if r.self_consistency_score is not None
    ]
    metrics.avg_self_consistency_score = (
        sum(sc_values) / len(sc_values) if sc_values else None
    )

    metrics.avg_reasoning_quality = sum(
        r.reasoning_quality_score for r in per_task_results
    ) / len(per_task_results)
    metrics.judge_fallback_count = sum(
        1 for r in per_task_results if r.judge_used_fallback
    )
    metrics.task_quality_scores = {
        r.task_id: r.reasoning_quality_score for r in per_task_results
    }
    return metrics


# ---------------------------------------------------------------------------
# Self-consistency (Phase F)
# ---------------------------------------------------------------------------

def _largest_equivalence_class_size(
    extracted_outputs: List[Any],
) -> int:
    """Largest class size under transitive lenient-equivalence partitioning."""
    n = len(extracted_outputs)
    if n == 0:
        return 0

    # Union-find via simple parent array — N is small (==num_runs).
    parent = list(range(n))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i: int, j: int) -> None:
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[ri] = rj

    for i in range(n):
        for j in range(i + 1, n):
            if Judge._values_match_lenient(
                extracted_outputs[i], extracted_outputs[j]
            ):
                union(i, j)

    # Count class sizes.
    sizes: Dict[int, int] = {}
    for i in range(n):
        root = find(i)
        sizes[root] = sizes.get(root, 0) + 1
    return max(sizes.values())


def _maybe_parse_json(value: Any) -> Any:
    """Try to parse ``value`` as JSON; return original on failure."""
    if not isinstance(value, str):
        return value
    try:
        return Judge._extract_and_parse_json(value)
    except (json.JSONDecodeError, ValueError):
        return value


def _normalise_for_consistency(
    extracted: Any,
    judge_config: Dict[str, Any],
) -> Any:
    """Coerce an extracted answer to the right shape for lenient matching."""
    mode = judge_config.get("mode", "exact")
    if mode == "json":
        # Lenient dict compare requires actual dicts.
        return _maybe_parse_json(extracted)
    return extracted


def compute_self_consistency_score(
    outputs: List[str],
    ground_truth: Any,
    judge_config: Dict[str, Any],
) -> Optional[float]:
    """Compute self-consistency for one ``(pattern, task)`` group.

    Spec section 4.4: extract each output via ``Judge._extract_answer``,
    then partition by the lenient equivalence rule and return
    ``size(largest_class) / total_runs``.  Returns ``None`` for fewer
    than 2 runs (spec section 5: never force false zeros).
    """
    if outputs is None or len(outputs) < 2:
        return None

    extracted: List[Any] = []
    for out in outputs:
        raw = out if isinstance(out, str) else str(out)
        x = Judge._extract_answer(raw, ground_truth, judge_config)
        x = _normalise_for_consistency(x, judge_config)
        extracted.append(x)

    largest = _largest_equivalence_class_size(extracted)
    return largest / float(len(outputs))


def inject_self_consistency_scores(
    per_pattern_runs: Dict[str, List[List[ReasoningQualityResult]]],
    task_outputs: Dict[Tuple[str, str], List[str]],
    task_specs: Dict[str, Any],
    pattern_metrics: Dict[str, Any],
) -> None:
    """Phase F hook: refresh latest-run results with self-consistency.

    Args:
        per_pattern_runs: ``{pattern_name: [run_1_results, run_2_results, ...]}``
            where each ``run_k_results`` is a list of
            ``ReasoningQualityResult`` (one per task).  Order across runs
            must be consistent.
        task_outputs: ``{(pattern_name, task_id): [output_run1, ...]}``.
        task_specs: ``{task_id: TestTask}`` so we can look up
            ``ground_truth`` and ``judge`` config per task.
        pattern_metrics: ``{pattern_name: PatternMetrics}`` whose
            ``cognitive`` field will be refreshed in place.

    Behaviour:
        - If a pattern has fewer than 2 runs recorded, this is a no-op
          for that pattern.
        - The **latest** per-task ``ReasoningQualityResult`` is mutated
          in place: ``self_consistency_score`` populated and
          ``reasoning_quality_score`` recomputed.  Earlier runs are not
          modified (spec section 4.8).
        - Each pattern's ``CognitiveMetrics`` is then rebuilt from the
          updated latest run.
    """
    for pattern_name, runs in per_pattern_runs.items():
        if not runs or len(runs) < 2:
            continue

        latest_run = runs[-1]
        n_runs = len(runs)

        for task_result in latest_run:
            task_id = task_result.task_id
            outputs = task_outputs.get((pattern_name, task_id))
            if outputs is None or len(outputs) < 2:
                continue

            task = task_specs.get(task_id)
            if task is None:
                continue

            judge_cfg = getattr(task, "judge", {}) or {}
            ground_truth = getattr(task, "ground_truth", None)

            sc = compute_self_consistency_score(
                outputs=outputs,
                ground_truth=ground_truth,
                judge_config=judge_cfg,
            )
            if sc is None:
                continue

            task_result.self_consistency_score = sc
            task_result.reasoning_quality_score = (
                _aggregate_with_renormalisation(
                    coverage=task_result.trace_coverage,
                    coherence=task_result.coherence_score,
                    agreement=task_result.final_answer_agreement,
                    self_consistency=sc,
                )
            )

        # Refresh the pattern-level CognitiveMetrics from the updated
        # latest run.
        pm = pattern_metrics.get(pattern_name)
        if pm is not None and hasattr(pm, "cognitive"):
            pm.cognitive = aggregate_cognitive_metrics(latest_run)
        # Tag the metrics object with how many runs informed self-consistency
        # (purely informational; downstream reports may surface this).
        if pm is not None:
            try:
                pm._self_consistency_runs = n_runs
            except Exception:  # noqa: BLE001 -- defensive only
                pass


__all__ = [
    "EXPECTED_MIN_THINK_STEPS",
    "MAX_REASONING_CHARS",
    "ReasoningExtractor",
    "ReasoningJudge",
    "ReasoningQualityResult",
    "CognitiveMetrics",
    "compute_task_reasoning_quality",
    "aggregate_cognitive_metrics",
    "compute_self_consistency_score",
    "inject_self_consistency_scores",
]
