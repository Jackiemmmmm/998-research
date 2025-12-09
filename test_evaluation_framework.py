#!/usr/bin/env python3
"""Quick test to verify the evaluation framework is working."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv

load_dotenv()


def test_test_suite():
    """Test that test suite loads correctly."""
    from src.evaluation import load_test_suite
    from src.evaluation.test_suite import print_test_suite_stats


    # Print stats
    print_test_suite_stats()

    # Test filtering
    load_test_suite(category="baseline")

    load_test_suite(category="reasoning")

    load_test_suite(complexity="simple")



def test_judge():
    """Test judge functionality."""
    from src.evaluation.judge import Judge


    # Test exact match
    success, msg = Judge.evaluate("408", "408", {"mode": "exact"})
    assert success, "Exact match should succeed"

    # Test JSON
    json_output = '{"name": "iPhone 15", "price": 999}'
    ground_truth = {"name": "iPhone 15", "price": 999}
    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "price": {"type": "number"}
        },
        "required": ["name", "price"]
    }
    success, msg = Judge.evaluate(json_output, ground_truth, {"mode": "json"}, schema)
    assert success, "JSON match should succeed"

    # Test regex
    success, msg = Judge.evaluate("Paris", None, {"mode": "regex", "pattern": r"(?i)^paris$"})
    assert success, "Regex match should succeed"



def test_metrics():
    """Test metrics classes."""
    from src.evaluation.metrics import (
        ControllabilityMetrics,
        EfficiencyMetrics,
        RobustnessMetrics,
        SuccessMetrics,
    )


    # Test Success metrics
    success = SuccessMetrics(total_tasks=10, successful_tasks=8, failed_tasks=2)
    assert success.success_rate() == 0.8

    # Test Efficiency metrics
    efficiency = EfficiencyMetrics(
        latencies=[1.0, 2.0, 3.0],
        input_tokens=[100, 150, 200],
        output_tokens=[50, 75, 100]
    )
    assert efficiency.avg_latency() == 2.0

    # Test Robustness metrics
    robustness = RobustnessMetrics(
        original_success_rate=0.9,
        perturbed_success_rate=0.7
    )
    robustness.calculate_degradation()
    assert abs(robustness.degradation_percentage - 22.22) < 0.1

    # Test Controllability metrics
    controllability = ControllabilityMetrics(
        total_json_tasks=5,
        schema_compliant_tasks=4
    )
    assert controllability.schema_compliance_rate() == 0.8



def test_imports():
    """Test all imports work."""
    import importlib.util

    try:
        # Test that all modules can be imported
        assert importlib.util.find_spec("src.evaluation") is not None
        assert importlib.util.find_spec("src.evaluation.judge") is not None
        assert importlib.util.find_spec("src.evaluation.visualization") is not None
    except AssertionError:
        raise


def main():
    """Run all tests."""
    try:
        test_imports()
        test_test_suite()
        test_judge()
        test_metrics()


    except AssertionError:
        sys.exit(1)
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
