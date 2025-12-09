#!/usr/bin/env python3
"""Agentic Pattern Evaluation Runner.

Evaluates ReAct, CoT, Reflex, and Tree of Thoughts patterns
Based on evaluation.md specifications.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))
sys.path.insert(0, str(Path(__file__).parent / "src" / "agent"))

from dotenv import load_dotenv
from pattern_react import enhanced_graph_pattern_react, graph_pattern_react
from pattern_reflex import graph_pattern_reflex
from pattern_sequential import graph_pattern_sequential
from pattern_tree_of_thoughts import graph_pattern_tree_of_thoughts

from src.evaluation import (
    ReportGenerator,
    load_test_suite,
)
from src.evaluation.evaluator import evaluate_multiple_patterns
from src.evaluation.visualization import EvaluationVisualizer

# Load environment variables
load_dotenv()

async def run_full_evaluation(delay: float = 3.0):
    """Run complete evaluation on all 5 patterns."""
    # Define patterns to evaluate
    patterns = {
        "ReAct": graph_pattern_react,
        "ReAct_Enhanced": enhanced_graph_pattern_react,
        "CoT": graph_pattern_sequential,
        "Reflex": graph_pattern_reflex,
        "ToT": graph_pattern_tree_of_thoughts,
    }

    # Load test suite
    test_tasks = load_test_suite()

    # Run evaluation
    pattern_metrics = await evaluate_multiple_patterns(
        patterns=patterns,
        test_tasks=test_tasks,
        include_robustness=True,
        delay_between_tasks=delay,
    )

    # Generate reports

    # JSON report
    ReportGenerator.generate_json_report(
        pattern_metrics,
        output_path="reports/evaluation_results.json"
    )

    # Markdown report
    ReportGenerator.generate_markdown_report(
        pattern_metrics,
        output_path="reports/evaluation_report.md"
    )

    # CSV comparison
    ReportGenerator.generate_csv_comparison(
        pattern_metrics,
        output_path="reports/comparison_table.csv"
    )

    # Console summary
    ReportGenerator.print_console_report(pattern_metrics)

    # Generate visualizations
    visualizer = EvaluationVisualizer(output_dir="reports/figures")
    visualizer.generate_all_plots(pattern_metrics)



async def run_quick_test(delay: float = 3.0):
    """Run quick test on subset of tasks."""
    patterns = {
        "ReAct": graph_pattern_react,
        "ReAct_Enhanced": enhanced_graph_pattern_react,
        # "CoT": graph_pattern_sequential,
    }

    # Use only baseline tasks
    test_tasks = load_test_suite(category="baseline")


    pattern_metrics = await evaluate_multiple_patterns(
        patterns=patterns,
        test_tasks=test_tasks,
        include_robustness=False,
        delay_between_tasks=delay,
    )

    ReportGenerator.print_console_report(pattern_metrics)


async def run_category_test(category: str, delay: float = 3.0):
    """Run evaluation on specific category."""
    patterns = {
        "ReAct": graph_pattern_react,
        "ReAct_Enhanced": enhanced_graph_pattern_react,
        "CoT": graph_pattern_sequential,
        "Reflex": graph_pattern_reflex,
        "ToT": graph_pattern_tree_of_thoughts,
    }

    test_tasks = load_test_suite(category=category)

    if not test_tasks:
        return


    pattern_metrics = await evaluate_multiple_patterns(
        patterns=patterns,
        test_tasks=test_tasks,
        include_robustness=True,
        delay_between_tasks=delay,
    )

    ReportGenerator.print_console_report(pattern_metrics)


def main():
    """Run the evaluation as main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Evaluate agentic design patterns"
    )
    parser.add_argument(
        "--mode",
        choices=["full", "quick", "category"],
        default="full",
        help="Evaluation mode (default: full)"
    )
    parser.add_argument(
        "--category",
        choices=["baseline", "reasoning", "tool", "planning"],
        help="Category to evaluate (for category mode)"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=5.0,
        help="Delay in seconds between tasks to avoid rate limits (default: 5.0)"
    )

    args = parser.parse_args()

    if args.mode == "full":
        asyncio.run(run_full_evaluation(delay=args.delay))
    elif args.mode == "quick":
        asyncio.run(run_quick_test(delay=args.delay))
    elif args.mode == "category":
        if not args.category:
            parser.print_help()
            return
        asyncio.run(run_category_test(args.category, delay=args.delay))


if __name__ == "__main__":
    main()
