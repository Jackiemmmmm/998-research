"""Phase F -- Statistical Rigor & Reproducibility.

Multi-run aggregation layer that sits **above** ``PatternMetrics``.

Provides:

- ``PatternRunRecord``: flattened per-pattern output of one full run.
- ``StatisticalSummary``: mean / sample-std / 95 % CI (t-distribution) for
  a single metric series.
- ``PairwiseEffectSize``: Cohen's d between two patterns for one metric.
- ``PatternStatistics``: per-pattern container of run records + summaries.
- ``StatisticalReport``: top-level report with per-pattern stats and
  pairwise effect sizes for ``composite_score`` and ``success_rate_strict``.

The module is **pure**: it does not run agents, call LLMs or touch the
filesystem.  The orchestrator (``run_evaluation.py``) is responsible for
producing ``PatternMetrics`` for each repeated run, then handing the
flattened ``PatternRunRecord`` lists to :func:`aggregate_runs` here.

Spec: ``docs/specs/week5-6_phase-f_statistical-rigor.md``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .metrics import PatternMetrics
from .scoring import CompositeScore, NormalizedDimensionScores

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: t critical values for two-sided 95 % CI, indexed by sample size ``n``
#: (degrees of freedom ``n - 1``).  Spec section 5.3.  Project supports
#: ``num_runs in [1, 5]``; ``n in [3, 5]`` is the documented working range,
#: ``n == 2`` is included for defensive use.
T_CRITICAL_95: Dict[int, float] = {
    2: 12.706,  # df = 1
    3: 4.303,   # df = 2
    4: 3.182,   # df = 3
    5: 2.776,   # df = 4
}

#: Names of the seven raw / dimension metrics that ``PatternRunRecord``
#: tracks.  Used by :func:`aggregate_runs` to drive the per-metric
#: summary loop, so the spec's ordering is preserved in the JSON output.
_METRIC_FIELDS_ORDERED: List[str] = [
    "success_rate_strict",
    "success_rate_lenient",
    "avg_latency_sec",
    "avg_total_tokens",
    "degradation_percentage",
    "overall_controllability",
    "dim1_reasoning_quality",
    "dim2_cognitive_safety",
    "dim3_action_decision_alignment",
    "dim4_success_efficiency",
    "dim5_behavioural_safety",
    "dim6_robustness_scalability",
    "dim7_controllability",
    "composite_score",
]

#: Metrics that must always emit a pairwise effect-size table per
#: spec section 5.4.  ``composite_score`` is the headline cross-pattern
#: comparison; ``success_rate_strict`` is the sanity-check companion.
PAIRWISE_EFFECT_SIZE_METRICS: List[str] = [
    "composite_score",
    "success_rate_strict",
]


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class StatisticalSummary:
    """One metric aggregated across the repeated runs of a pattern."""

    mean: float
    std: float
    ci95_low: float
    ci95_high: float
    n: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "mean": round(self.mean, 4),
            "std": round(self.std, 4),
            "ci95_low": round(self.ci95_low, 4),
            "ci95_high": round(self.ci95_high, 4),
            "n": self.n,
        }


@dataclass
class PairwiseEffectSize:
    """Cohen's d for one metric, comparing pattern_a vs pattern_b."""

    pattern_a: str
    pattern_b: str
    metric_name: str
    cohens_d: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "pattern_a": self.pattern_a,
            "pattern_b": self.pattern_b,
            "metric_name": self.metric_name,
            "cohens_d": round(self.cohens_d, 4),
        }


@dataclass
class PatternRunRecord:
    """Flattened per-pattern output of one full evaluation run.

    Field signatures pinned by spec section 4.  ``dim*`` fields are
    optional because the matching dimension may not be evaluable for
    a given pattern (e.g. ``dim1_reasoning_quality`` is ``None`` for
    ReAct when the trace has no THINK steps).
    """

    run_index: int
    pattern_name: str
    success_rate_strict: float
    success_rate_lenient: float
    avg_latency_sec: float
    avg_total_tokens: float
    degradation_percentage: float
    overall_controllability: float
    dim1_reasoning_quality: Optional[float] = None
    dim3_action_decision_alignment: Optional[float] = None
    dim4_success_efficiency: Optional[float] = None
    dim5_behavioural_safety: Optional[float] = None
    dim6_robustness_scalability: Optional[float] = None
    dim7_controllability: Optional[float] = None
    composite_score: Optional[float] = None
    # Forward-compatible: Phase B2 may add ``dim2_cognitive_safety``.
    # We accept it via :func:`flatten_pattern_metrics` using ``getattr``
    # so this record stays resilient to the new field landing later.
    dim2_cognitive_safety: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary preserving ``None``."""
        out: Dict[str, Any] = {
            "run_index": self.run_index,
            "pattern_name": self.pattern_name,
            "success_rate_strict": round(self.success_rate_strict, 4),
            "success_rate_lenient": round(self.success_rate_lenient, 4),
            "avg_latency_sec": round(self.avg_latency_sec, 4),
            "avg_total_tokens": round(self.avg_total_tokens, 2),
            "degradation_percentage": round(self.degradation_percentage, 2),
            "overall_controllability": round(self.overall_controllability, 4),
        }
        for k in (
            "dim1_reasoning_quality",
            "dim2_cognitive_safety",
            "dim3_action_decision_alignment",
            "dim4_success_efficiency",
            "dim5_behavioural_safety",
            "dim6_robustness_scalability",
            "dim7_controllability",
            "composite_score",
        ):
            v = getattr(self, k)
            out[k] = round(v, 4) if v is not None else None
        return out


@dataclass
class PatternStatistics:
    """Per-pattern container: run records + per-metric summaries."""

    pattern_name: str
    num_runs: int
    run_records: List[PatternRunRecord]
    summaries: Dict[str, StatisticalSummary] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "pattern_name": self.pattern_name,
            "num_runs": self.num_runs,
            "run_records": [r.to_dict() for r in self.run_records],
            "summaries": {k: v.to_dict() for k, v in self.summaries.items()},
        }


@dataclass
class StatisticalReport:
    """Top-level Phase F output.

    ``pairwise_effect_sizes`` is keyed by metric name (see
    :data:`PAIRWISE_EFFECT_SIZE_METRICS`); each value is a list of
    :class:`PairwiseEffectSize` covering every unordered pattern pair.
    """

    num_runs: int
    per_pattern: Dict[str, PatternStatistics] = field(default_factory=dict)
    pairwise_effect_sizes: Dict[str, List[PairwiseEffectSize]] = field(
        default_factory=dict
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary suitable for JSON serialisation."""
        return {
            "num_runs": self.num_runs,
            "per_pattern": {k: v.to_dict() for k, v in self.per_pattern.items()},
            "pairwise_effect_sizes": {
                metric: [e.to_dict() for e in pairs]
                for metric, pairs in self.pairwise_effect_sizes.items()
            },
        }


# ---------------------------------------------------------------------------
# Statistical helpers
# ---------------------------------------------------------------------------

def compute_mean(values: List[float]) -> float:
    """Arithmetic mean.  ``ValueError`` if the input is empty."""
    if not values:
        raise ValueError("compute_mean: empty input")
    return sum(values) / len(values)


def compute_sample_std(values: List[float], mean: Optional[float] = None) -> float:
    """Sample standard deviation (Bessel-corrected, ``n - 1``).

    Returns ``0.0`` for ``n < 2`` per spec section 5.2.
    """
    n = len(values)
    if n < 2:
        return 0.0
    m = compute_mean(values) if mean is None else mean
    sq_diff = sum((x - m) ** 2 for x in values)
    return math.sqrt(sq_diff / (n - 1))


def compute_ci95(values: List[float]) -> StatisticalSummary:
    """Compute mean / std / 95 % CI for a metric series.

    Uses the t-distribution lookup table :data:`T_CRITICAL_95`
    (spec section 5.3) because ``n`` is small in this project.
    For ``n < 2`` the CI collapses to the mean.
    """
    n = len(values)
    if n == 0:
        # Caller should have filtered None / empty before reaching here;
        # be defensive anyway and surface a zero-summary that downstream
        # code can detect by ``n == 0``.
        return StatisticalSummary(0.0, 0.0, 0.0, 0.0, 0)

    mean = compute_mean(values)
    std = compute_sample_std(values, mean=mean)

    if n < 2:
        return StatisticalSummary(mean, std, mean, mean, n)

    # Look up t critical; fall back to the closest tabulated value when
    # the caller exceeds the documented ``num_runs`` range.
    t = T_CRITICAL_95.get(n)
    if t is None:
        # Largest tabulated n still keeps the CI from blowing up; the
        # spec only mandates n in [3, 5] so this is purely defensive.
        t = T_CRITICAL_95[max(T_CRITICAL_95)]

    margin = t * (std / math.sqrt(n))
    return StatisticalSummary(mean, std, mean - margin, mean + margin, n)


#: Floating-point epsilon below which ``pooled_std`` is treated as zero
#: for the spec section 5.4 fallback.  Without this guard, identical
#: input series like ``[0.8, 0.8, 0.8]`` produce a ``pooled_std`` of
#: ~1e-16 (FP noise) and Cohen's d explodes to a meaningless ~2e15.
_POOLED_STD_EPSILON: float = 1e-12


def compute_cohens_d(values_a: List[float], values_b: List[float]) -> float:
    """Cohen's d with the spec section 5.4 zero-variance fallback.

    ``pooled_std == 0`` returns ``0.0`` if the means are equal,
    otherwise ``±999.0`` (sign of ``mean_a - mean_b``).  Never returns
    ``±inf`` -- that would break JSON / CSV serialisation.

    A small epsilon (:data:`_POOLED_STD_EPSILON`) treats FP-noise-only
    variance as zero so that two identical series produce the
    documented ``±999.0`` / ``0.0`` fallback rather than a meaningless
    near-infinite value.
    """
    na, nb = len(values_a), len(values_b)
    if na < 1 or nb < 1:
        return 0.0

    mean_a = compute_mean(values_a)
    mean_b = compute_mean(values_b)
    diff = mean_a - mean_b

    std_a = compute_sample_std(values_a, mean=mean_a)
    std_b = compute_sample_std(values_b, mean=mean_b)

    # When either sample has only one observation, treat its sample
    # variance as 0 (Bessel correction undefined for n=1).  Guard
    # against the n=2 denominator becoming zero.
    if na + nb - 2 <= 0:
        # Fall back to the zero-variance handling below.
        pooled_std = 0.0
    else:
        pooled_var = (
            (na - 1) * std_a ** 2 + (nb - 1) * std_b ** 2
        ) / (na + nb - 2)
        pooled_std = math.sqrt(pooled_var)

    if pooled_std <= _POOLED_STD_EPSILON:
        # FP noise on identical series collapses to the documented
        # zero-variance fallback.  The diff comparison uses the same
        # epsilon so means equal up to FP noise also collapse.
        if abs(diff) <= _POOLED_STD_EPSILON:
            return 0.0
        return 999.0 if diff > 0 else -999.0

    return diff / pooled_std


# ---------------------------------------------------------------------------
# Run-record flattening
# ---------------------------------------------------------------------------

def flatten_pattern_metrics(
    pattern_metrics: PatternMetrics,
    normalised_scores: Optional[NormalizedDimensionScores],
    composite_score: Optional[CompositeScore],
    run_index: int,
) -> PatternRunRecord:
    """Flatten one run's ``PatternMetrics`` into a ``PatternRunRecord``.

    Defensive ``getattr`` on ``dim*`` fields keeps the record resilient
    to Phase B2 (or future phases) adding new fields to
    :class:`NormalizedDimensionScores`.

    Args:
        pattern_metrics: Source for the raw run-level fields.
        normalised_scores: Phase E output (may be ``None`` if Phase E
            failed; all dim fields will then be ``None``).
        composite_score: Phase E output (may be ``None``).
        run_index: 1-based run number.

    Returns:
        A populated :class:`PatternRunRecord`.
    """
    success = pattern_metrics.success
    efficiency = pattern_metrics.efficiency
    robustness = pattern_metrics.robustness
    controllability = pattern_metrics.controllability

    record = PatternRunRecord(
        run_index=run_index,
        pattern_name=pattern_metrics.pattern_name,
        success_rate_strict=success.success_rate(),
        success_rate_lenient=success.lenient_success_rate(),
        avg_latency_sec=efficiency.avg_latency(),
        avg_total_tokens=efficiency.avg_total_tokens(),
        degradation_percentage=robustness.degradation_percentage,
        overall_controllability=controllability.overall_controllability(),
        dim1_reasoning_quality=getattr(normalised_scores, "dim1_reasoning_quality", None) if normalised_scores else None,
        dim2_cognitive_safety=getattr(normalised_scores, "dim2_cognitive_safety", None) if normalised_scores else None,
        dim3_action_decision_alignment=getattr(normalised_scores, "dim3_action_decision_alignment", None) if normalised_scores else None,
        dim4_success_efficiency=getattr(normalised_scores, "dim4_success_efficiency", None) if normalised_scores else None,
        dim5_behavioural_safety=getattr(normalised_scores, "dim5_behavioural_safety", None) if normalised_scores else None,
        dim6_robustness_scalability=getattr(normalised_scores, "dim6_robustness_scalability", None) if normalised_scores else None,
        dim7_controllability=getattr(normalised_scores, "dim7_controllability", None) if normalised_scores else None,
        composite_score=getattr(composite_score, "composite", None) if composite_score is not None else None,
    )
    return record


# ---------------------------------------------------------------------------
# Aggregation orchestrator
# ---------------------------------------------------------------------------

def _filter_non_none(values: List[Optional[float]]) -> List[float]:
    """Drop ``None`` from a list while preserving order."""
    return [v for v in values if v is not None]


def _build_pattern_statistics(
    pattern_name: str,
    records: List[PatternRunRecord],
) -> PatternStatistics:
    """Build :class:`PatternStatistics` for one pattern.

    A summary is created for every metric in :data:`_METRIC_FIELDS_ORDERED`
    that has at least one non-``None`` observation.  Spec section 6 +
    verification case 8: when **every** value is ``None``, the metric is
    omitted from ``summaries``.  Run records are kept verbatim, including
    their ``None`` values, so reviewers can see which runs missed which
    dimensions.
    """
    summaries: Dict[str, StatisticalSummary] = {}

    for metric in _METRIC_FIELDS_ORDERED:
        raw_values = [getattr(r, metric, None) for r in records]
        valid = _filter_non_none(raw_values)
        if not valid:
            # Spec section 6 + Case 8: omit summary entirely.
            continue
        summaries[metric] = compute_ci95(valid)

    return PatternStatistics(
        pattern_name=pattern_name,
        num_runs=len(records),
        run_records=list(records),
        summaries=summaries,
    )


def _compute_pairwise_effect_sizes(
    per_pattern: Dict[str, PatternStatistics],
    metric: str,
) -> List[PairwiseEffectSize]:
    """Compute pairwise Cohen's d for one metric across all pattern pairs.

    Iterates every unordered pair (a, b) with a != b; emits one
    :class:`PairwiseEffectSize` per directed pair (a vs b) so reviewers
    can read effect direction without flipping signs.  The spec example
    in §5.7 shows directed entries like
    ``{"pattern_a": "ReAct", "pattern_b": "Baseline", ...}``.
    """
    pairs: List[PairwiseEffectSize] = []
    pattern_names = list(per_pattern.keys())

    for i, name_a in enumerate(pattern_names):
        for j in range(i + 1, len(pattern_names)):
            name_b = pattern_names[j]
            stats_a = per_pattern[name_a]
            stats_b = per_pattern[name_b]

            values_a = _filter_non_none(
                [getattr(r, metric, None) for r in stats_a.run_records]
            )
            values_b = _filter_non_none(
                [getattr(r, metric, None) for r in stats_b.run_records]
            )
            if not values_a or not values_b:
                # Skip pairs where either side has no data for this metric.
                continue

            d = compute_cohens_d(values_a, values_b)
            pairs.append(
                PairwiseEffectSize(
                    pattern_a=name_a,
                    pattern_b=name_b,
                    metric_name=metric,
                    cohens_d=d,
                )
            )

    return pairs


def aggregate_runs(
    records_by_pattern: Dict[str, List[PatternRunRecord]],
) -> StatisticalReport:
    """Aggregate per-pattern run records into a :class:`StatisticalReport`.

    Defensive checks (spec section 5.1):

    - Every pattern must have the **same** number of runs.  Otherwise
      we refuse to aggregate (concurrency / model identifiers must be
      held constant across runs; an uneven count is the strongest
      signal that something diverged).

    Args:
        records_by_pattern: ``{pattern_name: [PatternRunRecord, ...]}``.

    Returns:
        A populated :class:`StatisticalReport`.
    """
    if not records_by_pattern:
        return StatisticalReport(num_runs=0)

    run_counts = {p: len(rs) for p, rs in records_by_pattern.items()}
    distinct_counts = set(run_counts.values())
    if len(distinct_counts) != 1:
        raise ValueError(
            "aggregate_runs: per-pattern run counts must be identical "
            f"to aggregate honestly; got {run_counts}"
        )
    num_runs = distinct_counts.pop()

    per_pattern: Dict[str, PatternStatistics] = {}
    for name, records in records_by_pattern.items():
        per_pattern[name] = _build_pattern_statistics(name, records)

    pairwise: Dict[str, List[PairwiseEffectSize]] = {}
    for metric in PAIRWISE_EFFECT_SIZE_METRICS:
        pairwise[metric] = _compute_pairwise_effect_sizes(per_pattern, metric)

    return StatisticalReport(
        num_runs=num_runs,
        per_pattern=per_pattern,
        pairwise_effect_sizes=pairwise,
    )


__all__ = [
    "T_CRITICAL_95",
    "PAIRWISE_EFFECT_SIZE_METRICS",
    "StatisticalSummary",
    "PairwiseEffectSize",
    "PatternRunRecord",
    "PatternStatistics",
    "StatisticalReport",
    "compute_mean",
    "compute_sample_std",
    "compute_ci95",
    "compute_cohens_d",
    "flatten_pattern_metrics",
    "aggregate_runs",
]
