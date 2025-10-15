# Evaluation Framework for Agentic Design Patterns

This evaluation framework provides a systematic, multi-dimensional assessment of agentic design patterns based on the specifications in `evaluation.md`.

## Overview

### Evaluated Patterns
- **ReAct**: Reasoning + Acting loop
- **Chain of Thought (CoT)**: Sequential step-by-step reasoning
- **Reflex**: Rule-based fast response
- **Tree of Thoughts (ToT)**: Parallel exploration

### Evaluation Dimensions
1. **Success**: Task completion rate, accuracy
2. **Efficiency**: Latency, token usage, steps
3. **Robustness**: Performance under perturbations
4. **Controllability**: Schema compliance, tool policy adherence

### Test Suite
16 standardized tasks across 4 categories:
- **A (baseline)**: Simple arithmetic, formatting, factual QA
- **B (reasoning)**: Logic, deduction, comprehension
- **C (tool)**: API calls, external data access
- **D (planning)**: Multi-step tasks, structured output

## Quick Start

### Run Full Evaluation
```bash
python run_evaluation.py
```

This will:
1. Evaluate all 4 patterns on all 16 tasks
2. Run robustness tests with perturbations
3. Generate comprehensive reports (JSON, Markdown, CSV)
4. Create visualization plots

### Run Quick Test
```bash
python run_evaluation.py --mode quick
```

Evaluates only baseline tasks on 2 patterns (faster for testing).

### Evaluate Specific Category
```bash
python run_evaluation.py --mode category --category reasoning
```

Categories: `baseline`, `reasoning`, `tool`, `planning`

## Output

### Reports
- `reports/evaluation_results.json` - Complete results in JSON
- `reports/evaluation_report.md` - Human-readable Markdown report
- `reports/comparison_table.csv` - Summary comparison table

### Visualizations
- `reports/figures/success_rate_comparison.png`
- `reports/figures/efficiency_comparison.png`
- `reports/figures/robustness_comparison.png`
- `reports/figures/controllability_comparison.png`
- `reports/figures/radar_comparison.png`
- `reports/figures/success_by_category.png`

## Framework Structure

```
src/evaluation/
├── __init__.py                # Package exports
├── test_suite.py              # 16 test task definitions
├── judge.py                   # Output validation (exact/json/regex)
├── metrics.py                 # 4-dimension metrics calculation
├── evaluator.py               # Main evaluation engine
├── report_generator.py        # Report generation (JSON/MD/CSV)
└── visualization.py           # Plot generation
```

## Key Features

### Independent Dimension Analysis
- **No mixed weighting** - Each dimension reported separately
- Supports comparative analysis without artificial overall scores
- Enables scenario-based pattern selection

### Automated Evaluation
- Exact match for numeric/string answers
- JSON schema validation for structured outputs
- Regex pattern matching for flexible answers
- Robustness testing with input perturbations

### Comprehensive Metrics
```python
# Success
- Overall success rate
- Success by category/complexity
- Partial success tracking

# Efficiency
- Average/median latency
- Token usage (input/output/total)
- Step count, tool call count

# Robustness
- Performance degradation under perturbations
- Tool failure recovery
- Per-task robustness scores

# Controllability
- Schema compliance rate
- Tool policy adherence
- Format compliance
```

## Usage Examples

### Programmatic Usage

```python
import asyncio
from src.evaluation import load_test_suite, PatternEvaluator, ReportGenerator
from src.agent.pattern_react import graph_pattern_react

async def evaluate_single_pattern():
    # Load test suite
    tasks = load_test_suite(category="reasoning")

    # Create evaluator
    evaluator = PatternEvaluator()

    # Evaluate pattern
    metrics = await evaluator.evaluate_pattern(
        pattern_name="ReAct",
        graph=graph_pattern_react,
        test_tasks=tasks,
        include_robustness=True
    )

    # Print results
    print(f"Success Rate: {metrics.success.success_rate():.1%}")
    print(f"Avg Latency: {metrics.efficiency.avg_latency():.2f}s")

    return metrics

asyncio.run(evaluate_single_pattern())
```

### Compare Multiple Patterns

```python
from src.evaluation.evaluator import evaluate_multiple_patterns

async def compare():
    patterns = {
        "ReAct": graph_pattern_react,
        "CoT": graph_pattern_sequential,
    }

    results = await evaluate_multiple_patterns(
        patterns=patterns,
        include_robustness=True
    )

    # Generate reports
    ReportGenerator.print_console_report(results)

asyncio.run(compare())
```

## Design Principles

1. **Single-Dimension Analysis**: No artificial weighting, each dimension independent
2. **Reproducibility**: Standardized test suite, consistent metrics
3. **Extensibility**: Easy to add new patterns, tasks, or metrics
4. **Transparency**: All results traceable, no black-box scoring

## Customization

### Add New Test Tasks

Edit `src/evaluation/test_suite.py`:

```python
TEST_SUITE.append(
    TestTask(
        id="E1",
        category="custom",
        complexity="medium",
        prompt="Your test prompt",
        ground_truth="Expected answer",
        judge={"mode": "exact"},
    )
)
```

### Add New Metrics

Extend metric classes in `src/evaluation/metrics.py`:

```python
@dataclass
class CustomMetrics:
    custom_score: float = 0.0

    def calculate(self, results):
        # Your calculation logic
        pass
```

## Troubleshooting

### Common Issues

1. **Import errors**: Ensure `PYTHONPATH` includes project root
2. **Missing dependencies**: Run `pip install -e .`
3. **LLM API errors**: Check `.env` file has valid API keys
4. **Visualization errors**: Install matplotlib: `pip install matplotlib`

### Debug Mode

Set environment variable for verbose logging:
```bash
export DEBUG=1
python run_evaluation.py
```

## Contributing

To extend the framework:
1. Add new test tasks to `test_suite.py`
2. Implement new judge modes in `judge.py`
3. Add metrics to `metrics.py`
4. Create visualizations in `visualization.py`

## References

- Evaluation specifications: `/evaluation.md`
- Project instructions: `/CLAUDE.md`
- Pattern implementations: `/src/agent/pattern_*.py`
