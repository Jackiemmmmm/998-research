#!/usr/bin/env python3
"""
Quick test to verify the evaluation framework is working
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv
load_dotenv()


def test_test_suite():
    """Test that test suite loads correctly"""
    from src.evaluation import load_test_suite, TEST_SUITE
    from src.evaluation.test_suite import print_test_suite_stats

    print("=" * 60)
    print("TEST 1: Test Suite Loading")
    print("=" * 60)

    # Print stats
    print_test_suite_stats()

    # Test filtering
    baseline_tasks = load_test_suite(category="baseline")
    print(f"\nBaseline tasks: {len(baseline_tasks)}")

    reasoning_tasks = load_test_suite(category="reasoning")
    print(f"Reasoning tasks: {len(reasoning_tasks)}")

    simple_tasks = load_test_suite(complexity="simple")
    print(f"Simple tasks: {len(simple_tasks)}")

    print("✅ Test Suite OK\n")


def test_judge():
    """Test judge functionality"""
    from src.evaluation.judge import Judge

    print("=" * 60)
    print("TEST 2: Judge Evaluation")
    print("=" * 60)

    # Test exact match
    success, msg = Judge.evaluate("408", "408", {"mode": "exact"})
    print(f"Exact match test: {success} - {msg}")
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
    print(f"JSON test: {success} - {msg}")
    assert success, "JSON match should succeed"

    # Test regex
    success, msg = Judge.evaluate("Paris", None, {"mode": "regex", "pattern": r"(?i)^paris$"})
    print(f"Regex test: {success} - {msg}")
    assert success, "Regex match should succeed"

    print("✅ Judge OK\n")


def test_metrics():
    """Test metrics classes"""
    from src.evaluation.metrics import (
        SuccessMetrics,
        EfficiencyMetrics,
        RobustnessMetrics,
        ControllabilityMetrics,
        PatternMetrics,
    )

    print("=" * 60)
    print("TEST 3: Metrics Calculation")
    print("=" * 60)

    # Test Success metrics
    success = SuccessMetrics(total_tasks=10, successful_tasks=8, failed_tasks=2)
    print(f"Success rate: {success.success_rate():.1%}")
    assert success.success_rate() == 0.8

    # Test Efficiency metrics
    efficiency = EfficiencyMetrics(
        latencies=[1.0, 2.0, 3.0],
        input_tokens=[100, 150, 200],
        output_tokens=[50, 75, 100]
    )
    print(f"Avg latency: {efficiency.avg_latency():.2f}s")
    print(f"Avg tokens: {efficiency.avg_total_tokens():.0f}")
    assert efficiency.avg_latency() == 2.0

    # Test Robustness metrics
    robustness = RobustnessMetrics(
        original_success_rate=0.9,
        perturbed_success_rate=0.7
    )
    robustness.calculate_degradation()
    print(f"Degradation: {robustness.degradation_percentage:.1f}%")
    assert abs(robustness.degradation_percentage - 22.22) < 0.1

    # Test Controllability metrics
    controllability = ControllabilityMetrics(
        total_json_tasks=5,
        schema_compliant_tasks=4
    )
    print(f"Schema compliance: {controllability.schema_compliance_rate():.1%}")
    assert controllability.schema_compliance_rate() == 0.8

    print("✅ Metrics OK\n")


def test_imports():
    """Test all imports work"""
    print("=" * 60)
    print("TEST 4: Module Imports")
    print("=" * 60)

    try:
        from src.evaluation import (
            load_test_suite,
            PatternEvaluator,
            ReportGenerator,
        )
        from src.evaluation.judge import Judge, LLMJudge
        from src.evaluation.visualization import EvaluationVisualizer
        print("✅ All imports successful\n")
    except ImportError as e:
        print(f"❌ Import failed: {e}\n")
        raise


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print(" " * 15 + "EVALUATION FRAMEWORK TEST")
    print("=" * 60 + "\n")

    try:
        test_imports()
        test_test_suite()
        test_judge()
        test_metrics()

        print("=" * 60)
        print(" " * 20 + "ALL TESTS PASSED ✅")
        print("=" * 60)
        print("\nThe evaluation framework is ready to use!")
        print("\nNext steps:")
        print("  1. Run full evaluation: python run_evaluation.py")
        print("  2. Run quick test: python run_evaluation.py --mode quick")
        print("  3. Check README: src/evaluation/README.md")
        print()

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
