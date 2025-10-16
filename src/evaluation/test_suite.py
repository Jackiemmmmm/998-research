"""
Test Suite Definition - 16 standardized tasks for pattern evaluation
Based on evaluation.md specifications

Categories:
- A (baseline): Simple arithmetic, formatting, factual QA
- B (reasoning): Logic, deduction, comprehension
- C (tool): API calls, external data access
- D (planning): Multi-step tasks, structured output
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class TestTask:
    """Single test task definition"""

    id: str
    category: str
    prompt: str
    ground_truth: Optional[Any]
    judge: Dict[str, Any]
    schema: Optional[Dict[str, Any]] = None
    plan: Optional[List[str]] = None
    policy: Optional[Dict[str, Any]] = None
    robustness: Optional[Dict[str, Any]] = None
    complexity: str = "medium"  # simple, medium, complex

    def get_perturbations(self) -> List[str]:
        """Get input perturbations for robustness testing"""
        if self.robustness and "perturbations" in self.robustness:
            return self.robustness["perturbations"]
        return []

    def get_tool_failure_prob(self) -> float:
        """Get tool failure probability for robustness testing"""
        if self.robustness and "tool_failure_prob" in self.robustness:
            return self.robustness["tool_failure_prob"]
        return 0.0


# Test Suite - 16 tasks based on evaluation.md
TEST_SUITE: List[TestTask] = [
    # Category A: Baseline tasks
    TestTask(
        id="A1",
        category="baseline",
        complexity="simple",
        prompt="Compute 17 * 24. Output the number only.",
        ground_truth="408",
        judge={"mode": "exact"},
        robustness={
            "perturbations": [
                "Compute 17×24. Output the number only.",
                "What is 17 * 24 ? Number only."
            ]
        }
    ),
    TestTask(
        id="A2",
        category="baseline",
        complexity="simple",
        prompt="Extract JSON {name, price} from: 'The iPhone 15 costs $999.' Return strictly JSON.",
        ground_truth={"name": "iPhone 15", "price": 999},
        judge={"mode": "json"},
        schema={
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "price": {"type": "number"}
            },
            "required": ["name", "price"]
        },
        robustness={
            "perturbations": [
                "Extract {name,price}: 'iphone   15  costs  $ 999 !' (JSON only)",
                "Pull product+price JSON from: iPhone-15 COSTS USD999."
            ]
        }
    ),
    TestTask(
        id="A3",
        category="baseline",
        complexity="simple",
        prompt="Normalize the date '12 October 2025' to ISO 'YYYY-MM-DD'. Output only the date.",
        ground_truth="2025-10-12",
        judge={"mode": "exact"},
        robustness={
            "perturbations": [
                "Normalise the date 12 Oct 2025 to YYYY-MM-DD.",
                "Format date: 12th October, 2025 → ISO."
            ]
        }
    ),
    TestTask(
        id="A4",
        category="baseline",
        complexity="simple",
        prompt="What is the capital of France? Output a single word.",
        ground_truth=None,
        judge={"mode": "regex", "pattern": r"(?i)^paris$"},
        robustness={
            "perturbations": [
                "Capital of FRANCE? one word.",
                "What is France's capital city?"
            ]
        }
    ),

    # Category B: Reasoning tasks
    TestTask(
        id="B1",
        category="reasoning",
        complexity="medium",
        prompt="All A are B. All B are C. Are all A C? Answer 'Yes' or 'No' only.",
        ground_truth="Yes",
        judge={"mode": "exact"},
        robustness={
            "perturbations": [
                "All A⊆B, all B⊆C. Are all A⊆C? Yes/No.",
                "Given A->B and B->C, conclude for A->C (Yes/No)."
            ]
        }
    ),
    TestTask(
        id="B2",
        category="reasoning",
        complexity="medium",
        prompt="A shop sells 3 apples for $5. How much do 12 apples cost? Output a number in dollars (no symbol).",
        ground_truth="20",
        judge={"mode": "exact"},
        robustness={
            "perturbations": [
                "3 apples=$5. Price for 12? Number only.",
                "If 3 cost 5, what is the cost of 12?"
            ]
        }
    ),
    TestTask(
        id="B3",
        category="reasoning",
        complexity="medium",
        prompt="Tom is taller than Jim. Jim is taller than Anna. Who is the shortest? Output the name only.",
        ground_truth="Anna",
        judge={"mode": "exact"},
        robustness={
            "perturbations": [
                "Tom>Jim>Anna in height. Shortest?",
                "Ordering: Tom taller than Jim; Jim taller than Anna. Shortest?"
            ]
        }
    ),
    TestTask(
        id="B4",
        category="reasoning",
        complexity="medium",
        prompt="Passage: 'Lena moved from Oslo to Paris in 2022. In 2024, she started a bakery near the Seine. Her sister Mia still lives in Oslo.' Question: In which city did Lena start a bakery? Output the city name only.",
        ground_truth="Paris",
        judge={"mode": "exact"},
        robustness={
            "perturbations": [
                "Lena→Paris (2022). In 2024 she opened a bakery by the Seine. Mia remains in Oslo. City of the bakery?",
                "Where did Lena start a bakery? One word."
            ]
        }
    ),

    # Category C: Tool-use tasks
    TestTask(
        id="C1",
        category="tool",
        complexity="medium",
        prompt="Get today's weather in Rome (mocked), and return strictly JSON {temp, condition}.",
        ground_truth={"temp": 28, "condition": "Sunny"},
        judge={"mode": "json"},
        schema={
            "type": "object",
            "properties": {
                "temp": {"type": "number"},
                "condition": {"type": "string"}
            },
            "required": ["temp", "condition"]
        },
        plan=["weather_api"],
        policy={"tool_whitelist": ["weather_api"]},
        robustness={
            "perturbations": [
                "Rome weather today; JSON {temp,condition} only.",
                "Weather in Rome IT; JSON only."
            ],
            "tool_failure_prob": 0.15
        }
    ),
    TestTask(
        id="C2",
        category="tool",
        complexity="medium",
        prompt="Fetch the mocked USD→EUR rate, then convert 100 USD to EUR. Return JSON {rate, eur}.",
        ground_truth={"rate": 0.90, "eur": 90.0},
        judge={"mode": "json"},
        schema={
            "type": "object",
            "properties": {
                "rate": {"type": "number"},
                "eur": {"type": "number"}
            },
            "required": ["rate", "eur"]
        },
        plan=["fx_api", "calculator"],
        policy={"tool_whitelist": ["fx_api", "calculator"]},
        robustness={
            "perturbations": [
                "USD to EUR rate (mock). Convert 100 USD. JSON {rate,eur}.",
                "Get fx rate then compute. JSON only."
            ],
            "tool_failure_prob": 0.15
        }
    ),
    TestTask(
        id="C3",
        category="tool",
        complexity="medium",
        prompt="Using the mocked encyclopedia/wikipedia tool, answer: Who discovered penicillin? Return JSON {name, year}.",
        ground_truth={"name": "Alexander Fleming", "year": 1928},
        judge={"mode": "json"},
        schema={
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "year": {"type": "number"}
            },
            "required": ["name", "year"]
        },
        plan=["wiki_search"],
        policy={"tool_whitelist": ["wiki_search"]},
        robustness={
            "perturbations": [
                "Penicillin discoverer? Return JSON {name,year}.",
                "Use encyclopedia tool; JSON only."
            ],
            "tool_failure_prob": 0.15
        }
    ),
    TestTask(
        id="C4",
        category="tool",
        complexity="medium",
        prompt="Find a mocked USB-C cable under $10 and return JSON {url, price}.",
        ground_truth={"url": "https://shop.example/u1", "price": 9.5},
        judge={"mode": "json"},
        schema={
            "type": "object",
            "properties": {
                "url": {"type": "string"},
                "price": {"type": "number"}
            },
            "required": ["url", "price"]
        },
        plan=["shopping_search"],
        policy={"tool_whitelist": ["shopping_search"]},
        robustness={
            "perturbations": [
                "Find USB-C cable < $10. JSON {url,price}.",
                "USB-C cable cheap; JSON only."
            ],
            "tool_failure_prob": 0.15
        }
    ),

    # Category D: Planning tasks
    TestTask(
        id="D1",
        category="planning",
        complexity="complex",
        prompt="Measure exactly 4L using only a 3L and a 5L jug. Describe the steps briefly, ending with the final state.",
        ground_truth=None,
        judge={"mode": "regex", "pattern": r"(?i)\b4\s*L\b"},
        robustness={
            "perturbations": [
                "Use 3L & 5L jars to obtain 4L. Provide steps.",
                "How to get exactly four litres with 3L/5L?"
            ]
        }
    ),
    TestTask(
        id="D2",
        category="planning",
        complexity="complex",
        prompt="Plan a 2-day Rome itinerary including at least three attractions: Colosseum, Trevi Fountain, Vatican Museums. Return JSON {day1:[...], day2:[...]}.",
        ground_truth=None,
        judge={"mode": "regex", "pattern": r"(?s).*Colosseum.*Trevi Fountain.*Vatican Museums.*"},
        schema={
            "type": "object",
            "properties": {
                "day1": {"type": "array", "items": {"type": "string"}},
                "day2": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["day1", "day2"]
        },
        robustness={
            "perturbations": [
                "2-day Rome plan incl. Colosseum, Trevi Fountain, Vatican Museums. JSON only.",
                "Rome itinerary (2 days). Include the three named sites. JSON {day1,day2}."
            ]
        }
    ),
    TestTask(
        id="D3",
        category="planning",
        complexity="complex",
        prompt="""Grid path (5x5). S=start at (1,1); G=goal at (5,5); X=blocked. Grid rows:
S . . X .
. X . . .
. . X . .
. . . . X
. X . . G
Return JSON {path_len, path}, where path is a list of coordinates from start to goal. Use a shortest path.""",
        ground_truth={"path_len": 8},
        judge={"mode": "json", "ignore_fields": ["path"]},
        schema={
            "type": "object",
            "properties": {
                "path_len": {"type": "number"},
                "path": {"type": "array"}
            },
            "required": ["path_len", "path"]
        },
        robustness={
            "perturbations": [
                "Find shortest path in the same grid; JSON {path_len,path}.",
                "Compute minimal steps from (1,1) to (5,5) avoiding X. JSON only."
            ]
        }
    ),
    TestTask(
        id="D4",
        category="planning",
        complexity="complex",
        prompt="""Given availability (30-min slots):
A: 2025-09-22T10:00, 2025-09-22T10:30, 2025-09-22T11:00
B: 2025-09-22T10:00, 2025-09-22T11:00
C: 2025-09-22T10:00, 2025-09-22T10:30
Schedule a 30-min meeting for A,B,C. Return JSON {start, end, attendees} with attendees sorted alphabetically.""",
        ground_truth={"start": "2025-09-22T10:00", "end": "2025-09-22T10:30", "attendees": ["A", "B", "C"]},
        judge={"mode": "json"},
        schema={
            "type": "object",
            "properties": {
                "start": {"type": "string"},
                "end": {"type": "string"},
                "attendees": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["start", "end", "attendees"]
        },
        robustness={
            "perturbations": [
                "Same availabilities; schedule meeting JSON {start,end,attendees}.",
                "Find common 30-min slot for A/B/C; JSON only."
            ]
        }
    ),
]


def load_test_suite(
    category: Optional[str] = None,
    complexity: Optional[str] = None,
    task_ids: Optional[List[str]] = None
) -> List[TestTask]:
    """
    Load test suite with optional filtering

    Args:
        category: Filter by category (baseline, reasoning, tool, planning)
        complexity: Filter by complexity (simple, medium, complex)
        task_ids: Filter by specific task IDs (e.g., ["A1", "B2"])

    Returns:
        Filtered list of test tasks
    """
    filtered = TEST_SUITE

    if category:
        filtered = [t for t in filtered if t.category == category]

    if complexity:
        filtered = [t for t in filtered if t.complexity == complexity]

    if task_ids:
        filtered = [t for t in filtered if t.id in task_ids]

    return filtered


def get_task_by_id(task_id: str) -> Optional[TestTask]:
    """Get a specific task by ID"""
    for task in TEST_SUITE:
        if task.id == task_id:
            return task
    return None


def get_categories() -> List[str]:
    """Get all unique categories"""
    return list(set(task.category for task in TEST_SUITE))


def get_complexities() -> List[str]:
    """Get all unique complexity levels"""
    return list(set(task.complexity for task in TEST_SUITE))


# Statistics
def print_test_suite_stats():
    """Print test suite statistics"""
    print("=" * 60)
    print("TEST SUITE STATISTICS")
    print("=" * 60)
    print(f"Total tasks: {len(TEST_SUITE)}")
    print()

    print("By Category:")
    for category in get_categories():
        count = len([t for t in TEST_SUITE if t.category == category])
        print(f"  {category:12s}: {count:2d} tasks")
    print()

    print("By Complexity:")
    for complexity in get_complexities():
        count = len([t for t in TEST_SUITE if t.complexity == complexity])
        print(f"  {complexity:12s}: {count:2d} tasks")
    print()

    print("Judge Modes:")
    judge_modes = {}
    for task in TEST_SUITE:
        mode = task.judge.get("mode", "unknown")
        judge_modes[mode] = judge_modes.get(mode, 0) + 1
    for mode, count in judge_modes.items():
        print(f"  {mode:12s}: {count:2d} tasks")
    print("=" * 60)


if __name__ == "__main__":
    print_test_suite_stats()
