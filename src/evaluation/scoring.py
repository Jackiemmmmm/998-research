"""Phase E — Normalisation + Composite Scoring.

Normalises all evaluation sub-indicators to [0, 1], computes per-dimension
scores and a composite score for cross-pattern comparison.

Spec: docs/specs/week1-2_phase-e_normalisation.md
"""

import statistics
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .controllability import ControllabilityResult
from .metrics import PatternMetrics


# ---------------------------------------------------------------------------
# Normalisation helpers
# ---------------------------------------------------------------------------

def normalize_min_max(
    values: List[Optional[float]],
    invert: bool = False,
) -> List[Optional[float]]:
    """Min-max normalisation across values (Option A).

    Edge cases:
        - All same value → 1.0
        - Single value → 1.0
        - None values → preserved as None

    Args:
        values: Raw values (may contain None).
        invert: If True, apply 1 - norm (for lower-is-better metrics).

    Returns:
        Normalised values in [0, 1], preserving None positions.
    """
    valid = [v for v in values if v is not None]

    if len(valid) <= 1:
        return [1.0 if v is not None else None for v in values]

    x_min = min(valid)
    x_max = max(valid)

    result: List[Optional[float]] = []
    for v in values:
        if v is None:
            result.append(None)
        elif x_max == x_min:
            result.append(1.0)
        else:
            normed = (v - x_min) / (x_max - x_min)
            result.append(1.0 - normed if invert else normed)
    return result


def _safe_mean(values: List[Optional[float]]) -> Optional[float]:
    """Compute mean of non-None values. Returns None if all None."""
    valid = [v for v in values if v is not None]
    if not valid:
        return None
    return statistics.mean(valid)


# ---------------------------------------------------------------------------
# Dimension score computation
# ---------------------------------------------------------------------------

def compute_dim4_scores(
    pattern_metrics: Dict[str, PatternMetrics],
) -> Dict[str, Optional[float]]:
    """Compute Dim 4 — Success & Efficiency for each pattern.

    Formula: (1/3) * success_rate + (1/3) * norm_latency + (1/3) * norm_tokens
    """
    patterns = list(pattern_metrics.keys())
    if not patterns:
        return {}

    # Collect raw values
    success_rates = [pm.success.success_rate() for pm in pattern_metrics.values()]
    latencies = [pm.efficiency.avg_latency() for pm in pattern_metrics.values()]
    tokens = [pm.efficiency.avg_total_tokens() for pm in pattern_metrics.values()]

    # Replace zero values that indicate no data with None
    latencies_opt: List[Optional[float]] = [
        v if v > 0 else None for v in latencies
    ]
    tokens_opt: List[Optional[float]] = [
        v if v > 0 else None for v in tokens
    ]

    # Normalise
    norm_latency = normalize_min_max(latencies_opt, invert=True)
    norm_tokens = normalize_min_max(tokens_opt, invert=True)

    result = {}
    for i, pname in enumerate(patterns):
        sub_indicators = [success_rates[i], norm_latency[i], norm_tokens[i]]
        score = _safe_mean(sub_indicators)
        result[pname] = score

    return result


def compute_dim6_scores(
    pattern_metrics: Dict[str, PatternMetrics],
) -> Dict[str, Optional[float]]:
    """Compute Dim 6 — Robustness & Scalability for each pattern.

    Formula: (1/3) * norm_degradation + (1/3) * recovery_rate + (1/3) * robustness_score
    """
    patterns = list(pattern_metrics.keys())
    if not patterns:
        return {}

    result = {}
    for pname in patterns:
        rm = pattern_metrics[pname].robustness

        # norm_degradation: Option B (÷100, inverted)
        norm_degradation = 1.0 - (rm.degradation_percentage / 100.0)
        norm_degradation = max(0.0, min(1.0, norm_degradation))

        # recovery_rate: Option B (use directly)
        recovery = rm.tool_failure_recovery_rate

        # robustness_score: Option B (use directly)
        robustness = rm.avg_robustness_score()

        sub_indicators: List[Optional[float]] = [norm_degradation, recovery, robustness]

        # Handle None-like values: if robustness has no task scores, treat as None
        if not rm.task_robustness_scores:
            sub_indicators[2] = None
        if recovery == 0.0 and rm.tool_failure_recovery_rate == 0.0:
            # Could be genuinely 0 or missing; keep as-is (0.0 is valid)
            pass

        score = _safe_mean(sub_indicators)
        result[pname] = score

    return result


def compute_dim7_scores(
    pattern_metrics: Dict[str, PatternMetrics],
    controllability_results: Dict[str, ControllabilityResult],
) -> Dict[str, Optional[float]]:
    """Compute Dim 7 — Controllability, Transparency & Resource Efficiency.

    Formula: (1/5) * trace_completeness + (1/5) * (1 - policy_flag_rate)
           + (1/5) * resource_efficiency + (1/5) * schema_compliance
           + (1/5) * format_compliance
    """
    patterns = list(pattern_metrics.keys())
    if not patterns:
        return {}

    result = {}
    for pname in patterns:
        cm = pattern_metrics[pname].controllability
        cr = controllability_results.get(pname)

        sub_indicators: List[Optional[float]] = []

        # Sub-indicators from Phase D2
        if cr is not None:
            sub_indicators.append(cr.trace_completeness)
            sub_indicators.append(1.0 - cr.policy_flag_rate)  # policy_compliance
            sub_indicators.append(cr.resource_efficiency)
        else:
            sub_indicators.extend([None, None, None])

        # Sub-indicators from existing ControllabilityMetrics
        schema_comp = cm.schema_compliance_rate() if cm.total_json_tasks > 0 else None
        sub_indicators.append(schema_comp)
        sub_indicators.append(cm.format_compliance_rate if cm.format_compliance_rate > 0 else None)

        score = _safe_mean(sub_indicators)
        result[pname] = score

    return result


def compute_reserve_indicators(
    pattern_metrics: Dict[str, PatternMetrics],
) -> Dict[str, Dict[str, Optional[float]]]:
    """Compute ★ reserve indicators: normalised but not in any dimension.

    - norm_avg_steps: Option A (min-max, inverted)
    - norm_avg_tool_calls: Option A (min-max, inverted)
    - norm_tao_cycles: Option A (min-max, NOT inverted — higher is better)
    """
    patterns = list(pattern_metrics.keys())
    if not patterns:
        return {}

    steps = [pm.efficiency.avg_steps() for pm in pattern_metrics.values()]
    tool_calls = [pm.efficiency.avg_tool_calls() for pm in pattern_metrics.values()]
    tao_raw = [
        statistics.mean(pm.efficiency.tao_cycle_counts) if pm.efficiency.tao_cycle_counts else None
        for pm in pattern_metrics.values()
    ]

    steps_opt: List[Optional[float]] = [v if v > 0 else None for v in steps]
    tools_opt: List[Optional[float]] = [v if v > 0 else None for v in tool_calls]

    norm_steps = normalize_min_max(steps_opt, invert=True)
    norm_tools = normalize_min_max(tools_opt, invert=True)
    norm_tao = normalize_min_max(tao_raw, invert=False)

    result = {}
    for i, pname in enumerate(patterns):
        result[pname] = {
            "norm_avg_steps": norm_steps[i],
            "norm_avg_tool_calls": norm_tools[i],
            "norm_tao_cycles": norm_tao[i],
        }
    return result


# ---------------------------------------------------------------------------
# Output dataclasses
# ---------------------------------------------------------------------------

@dataclass
class NormalizedDimensionScores:
    """Per-pattern normalised scores, grouped by dimension."""

    pattern_name: str
    dim4_success_efficiency: Optional[float] = None
    dim6_robustness_scalability: Optional[float] = None
    dim7_controllability: Optional[float] = None

    # Dimensions 1, 2, 3, 5 — placeholder for future phases
    dim1_reasoning_quality: Optional[float] = None
    dim2_cognitive_safety: Optional[float] = None
    dim3_action_decision_alignment: Optional[float] = None
    dim5_behavioural_safety: Optional[float] = None

    # ★ Reserve indicators: normalised but not in any dimension formula
    norm_avg_steps: Optional[float] = None
    norm_avg_tool_calls: Optional[float] = None
    norm_tao_cycles: Optional[float] = None

    def available_scores(self) -> Dict[str, float]:
        """Return only non-None dimension scores."""
        dim_fields = {
            "dim1_reasoning_quality": self.dim1_reasoning_quality,
            "dim2_cognitive_safety": self.dim2_cognitive_safety,
            "dim3_action_decision_alignment": self.dim3_action_decision_alignment,
            "dim4_success_efficiency": self.dim4_success_efficiency,
            "dim5_behavioural_safety": self.dim5_behavioural_safety,
            "dim6_robustness_scalability": self.dim6_robustness_scalability,
            "dim7_controllability": self.dim7_controllability,
        }
        return {k: v for k, v in dim_fields.items() if v is not None}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "pattern_name": self.pattern_name,
            "dimensions": {
                "dim1_reasoning_quality": self.dim1_reasoning_quality,
                "dim2_cognitive_safety": self.dim2_cognitive_safety,
                "dim3_action_decision_alignment": self.dim3_action_decision_alignment,
                "dim4_success_efficiency": _round_opt(self.dim4_success_efficiency),
                "dim5_behavioural_safety": self.dim5_behavioural_safety,
                "dim6_robustness_scalability": _round_opt(self.dim6_robustness_scalability),
                "dim7_controllability": _round_opt(self.dim7_controllability),
            },
            "reserve_indicators": {
                "norm_avg_steps": _round_opt(self.norm_avg_steps),
                "norm_avg_tool_calls": _round_opt(self.norm_avg_tool_calls),
                "norm_tao_cycles": _round_opt(self.norm_tao_cycles),
            },
        }


@dataclass
class CompositeScore:
    """Composite score computed from available dimension scores."""

    pattern_name: str
    dimension_scores: Dict[str, Optional[float]] = field(default_factory=dict)
    weights: Dict[str, float] = field(default_factory=dict)
    composite: float = 0.0
    available_dimensions: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "pattern_name": self.pattern_name,
            "dimension_scores": {k: _round_opt(v) for k, v in self.dimension_scores.items()},
            "weights": {k: round(v, 4) for k, v in self.weights.items()},
            "composite": round(self.composite, 4),
            "available_dimensions": self.available_dimensions,
        }


def _round_opt(v: Optional[float], digits: int = 4) -> Optional[float]:
    """Round a float or return None."""
    return round(v, digits) if v is not None else None


# ---------------------------------------------------------------------------
# Composite score computation
# ---------------------------------------------------------------------------

def compute_composite(
    dim_scores: NormalizedDimensionScores,
    custom_weights: Optional[Dict[str, float]] = None,
) -> CompositeScore:
    """Compute composite score from available dimension scores.

    Default: uniform weights (1/N for N available dimensions).
    Custom weights: Dict[str, float] overrides default.

    Args:
        dim_scores: NormalizedDimensionScores for one pattern.
        custom_weights: Optional custom weight dict {dim_name: weight}.

    Returns:
        CompositeScore with weighted average.
    """
    available = dim_scores.available_scores()

    if not available:
        return CompositeScore(
            pattern_name=dim_scores.pattern_name,
            dimension_scores={},
            weights={},
            composite=0.0,
            available_dimensions=0,
        )

    # Determine weights
    if custom_weights:
        weights = {k: custom_weights.get(k, 0.0) for k in available}
    else:
        # Uniform weights
        w = 1.0  # Each gets weight 1, divided by N later
        weights = {k: w for k in available}

    # Compute weighted average
    total_weight = sum(weights.values())
    if total_weight == 0:
        composite = 0.0
    else:
        weighted_sum = sum(weights[k] * available[k] for k in available)
        composite = weighted_sum / total_weight

    return CompositeScore(
        pattern_name=dim_scores.pattern_name,
        dimension_scores=dict(available),
        weights=weights,
        composite=composite,
        available_dimensions=len(available),
    )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def compute_all_scores(
    pattern_metrics: Dict[str, PatternMetrics],
    controllability_results: Dict[str, ControllabilityResult],
    custom_weights: Optional[Dict[str, float]] = None,
) -> Tuple[Dict[str, NormalizedDimensionScores], Dict[str, CompositeScore]]:
    """Compute normalised dimension scores and composite scores for all patterns.

    Args:
        pattern_metrics: Dict of {pattern_name: PatternMetrics}.
        controllability_results: Dict of {pattern_name: ControllabilityResult}.
        custom_weights: Optional custom weights for composite scoring.

    Returns:
        (normalised_scores, composite_scores) dicts keyed by pattern_name.
    """
    # Compute dimension scores across all patterns
    dim4 = compute_dim4_scores(pattern_metrics)
    dim6 = compute_dim6_scores(pattern_metrics)
    dim7 = compute_dim7_scores(pattern_metrics, controllability_results)
    reserves = compute_reserve_indicators(pattern_metrics)

    normalised: Dict[str, NormalizedDimensionScores] = {}
    composites: Dict[str, CompositeScore] = {}

    for pname in pattern_metrics:
        reserve = reserves.get(pname, {})
        nds = NormalizedDimensionScores(
            pattern_name=pname,
            dim4_success_efficiency=dim4.get(pname),
            dim6_robustness_scalability=dim6.get(pname),
            dim7_controllability=dim7.get(pname),
            norm_avg_steps=reserve.get("norm_avg_steps"),
            norm_avg_tool_calls=reserve.get("norm_avg_tool_calls"),
            norm_tao_cycles=reserve.get("norm_tao_cycles"),
        )
        normalised[pname] = nds
        composites[pname] = compute_composite(nds, custom_weights)

    return normalised, composites
