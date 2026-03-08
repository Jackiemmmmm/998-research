# Phase A: Unified Telemetry Layer — Implementation Specification

> Status: **COMPLETED** (2026-03-03)
> Priority: P0 (Foundation)
> Related: [PROJECT_GAP_ANALYSIS_AND_PLAN.md](./PROJECT_GAP_ANALYSIS_AND_PLAN.md) — Phase A, Cross-Cutting Gaps (Unified Telemetry Schema, Unified Adapter API)

---

## 1. Context & Motivation

Proposal (Group-1.pdf Section 2.2) 要求所有 pattern 共享一套标准化的 think-act-observe (TAO) 遥测 schema，用于后续 7 个维度的评估计算。

### 1.1 实施前的问题

| 问题 | 影响范围 | 状态 |
|------|---------|------|
| 每个 pattern 各自管理 state，没有统一的步骤记录 | Dim 1, 3, 7 无法实现 | 已修复 |
| `evaluator.py` 的 token 计数使用粗略估算 (`len(text) // 4`) | Dim 4 效率指标不准确 | 已修复 |
| `tool_call_count` 字段始终为 0（从未被赋值） | Dim 3, 5 无法追踪工具使用 | 已修复 |
| `step_count` 仅统计 message 数量，不区分 think/act/observe | Dim 7 透明度无法衡量 | 已修复 |

### 1.2 设计策略

采用 **后置解析 (post-hoc message parsing)** 策略：

- 从 `graph.invoke()` 返回的 response 中提取结构化 trace
- **不修改任何 pattern 的内部逻辑**
- 利用 LangChain message 类型 (`HumanMessage`, `AIMessage`, `ToolMessage`) 和 pattern state keys 进行分类
- 每个 pattern 有专属的提取器方法，共享统一的输出结构

---

## 2. Architecture Overview

```
graph.invoke(input)
       │
       ▼
   response (Dict)
       │
       ▼
┌──────────────────────────┐
│    TraceExtractor        │
│  .extract(response,      │
│    pattern_name, task_id) │
│                          │
│  Dispatch by pattern:    │
│  ┌─ _extract_react()    │
│  ├─ _extract_reflex()   │
│  ├─ _extract_sequential()│
│  ├─ _extract_tot()      │
│  └─ _extract_generic()  │
└──────────┬───────────────┘
           │
           ▼
     AgentTrace
   ┌──────────────────────┐
   │ pattern_name, task_id │
   │ steps: [StepRecord]  │
   │ ── aggregates ──     │
   │ total_think_steps    │
   │ total_act_steps      │
   │ total_observe_steps  │
   │ total_tool_calls     │
   │ tao_cycles           │
   │ total_tokens         │
   └──────────────────────┘
```

---

## 3. Data Structures

### 3.1 `StepType` (Enum)

| Value | Description | TAO Mapping |
|-------|-------------|-------------|
| `INPUT` | 用户输入 | — |
| `THINK` | 推理 / 规划 | **T**hink |
| `ACT` | 工具调用 / 执行动作 | **A**ct |
| `OBSERVE` | 工具返回结果 / 观察 | **O**bserve |
| `OUTPUT` | 最终输出 | — |

### 3.2 `ToolCallRecord` (dataclass)

```python
@dataclass
class ToolCallRecord:
    tool_name: str          # 工具名称
    tool_args: Dict         # 调用参数
    tool_call_id: str       # LangChain tool call ID
    result: str = ""        # 工具返回结果 (由 _pair_tool_results 填充)
    success: bool = True    # 执行是否成功
```

### 3.3 `StepRecord` (dataclass)

```python
@dataclass
class StepRecord:
    step_index: int                         # 步骤序号
    step_type: StepType                     # TAO 类型
    content: str                            # 步骤内容
    tool_calls: List[ToolCallRecord]        # 工具调用 (ACT 步骤)
    input_tokens: int                       # 输入 token 数
    output_tokens: int                      # 输出 token 数
    total_tokens: int                       # 总 token 数
    tokens_estimated: bool                  # 是否为估算值
    message_type: str                       # "human" / "ai" / "tool" / "synthetic"
    stage_label: str                        # Pattern-specific 标注
```

### 3.4 `AgentTrace` (dataclass)

```python
@dataclass
class AgentTrace:
    pattern_name: str
    task_id: str
    steps: List[StepRecord]

    # Aggregated (由 compute_aggregates() 计算)
    total_think_steps: int
    total_act_steps: int
    total_observe_steps: int
    total_tool_calls: int
    tao_cycles: int                         # 完整 T-A-O 循环数

    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    any_tokens_estimated: bool
```

**Key Methods:**
- `compute_aggregates()` — 从 steps 重算所有聚合字段
- `_count_tao_cycles()` — 检测连续的 THINK→ACT→OBSERVE 序列
- `to_dict()` — 序列化为字典（不含 raw message）

---

## 4. Pattern-Specific Extraction Logic

### 4.1 ReAct (`_extract_react`)

| Message 类型 | 条件 | 映射 | stage_label |
|-------------|------|------|------------|
| HumanMessage | — | `INPUT` | `react_input` |
| AIMessage | has `tool_calls` + non-empty content | `THINK` | `react_reasoning` |
| AIMessage | has `tool_calls` | `ACT` | `react_action` |
| ToolMessage | — | `OBSERVE` | `{tool_call_id}` |
| AIMessage | no `tool_calls` (final) | `OUTPUT` | `react_output` |

**Tool pairing**: `_pair_tool_results()` 通过 `tool_call_id` 将 ACT 的 `ToolCallRecord.result` 与 OBSERVE content 配对。

### 4.2 Reflex (`_extract_reflex`)

| Source | 映射 | stage_label |
|--------|------|------------|
| HumanMessage | `INPUT` | `reflex_input` |
| State `matched_rule` + `action_taken` | `THINK` (synthetic) | `reflex_rule_match` |
| AIMessage | `OUTPUT` | `reflex_output` |

**Synthetic step**: 从 response state 的 `matched_rule` 和 `action_taken` 字段合成 THINK 步骤，标记 `message_type="synthetic"`。

### 4.3 Sequential/CoT (`_extract_sequential`)

| AI Message 位置 | 映射 | stage_label |
|----------------|------|------------|
| 第 1 个 AI message | `THINK` | `cot_planning` |
| 中间 AI messages (无 tool_calls) | `THINK` | `cot_execution` |
| 中间 AI messages (有 tool_calls) | `ACT` | `cot_execution_act` |
| 最后一个 AI message | `OUTPUT` | `cot_review` |
| ToolMessage | `OBSERVE` | `cot_tool_result` |

### 4.4 Tree of Thoughts (`_extract_tot`)

| Source | 映射 | stage_label |
|--------|------|------------|
| HumanMessage | `INPUT` | `tot_input` |
| State `thought_tree[]` 每个节点 | `THINK` (synthetic) | `tot_thought_d{depth}` |
| AIMessage | `OUTPUT` | `tot_output` |

**Synthetic steps**: thought_tree 中的每个 thought 节点重建为 THINK 步骤，包含 `depth`, `score`, `reasoning`, `path` 信息，标记 `tokens_estimated=True`。

### 4.5 Generic Fallback (`_extract_generic`)

| Message 类型 | 条件 | 映射 |
|-------------|------|------|
| human | — | `INPUT` |
| ai | has `tool_calls` | `ACT` |
| ai | last message | `OUTPUT` |
| ai | other | `THINK` |
| tool | — | `OBSERVE` |

---

## 5. Token Extraction Strategy

优先级链 (Priority Chain):

```
1. msg.usage_metadata                     → 精确值 (estimated=False)
     ├─ input_tokens, output_tokens, total_tokens

2. msg.response_metadata.token_usage      → 精确值 (estimated=False)
     ├─ prompt_tokens, completion_tokens, total_tokens

3. len(content) // 4                      → 估算值 (estimated=True)
     ├─ human messages → input_tokens
     └─ ai/tool messages → output_tokens
```

`tokens_estimated` 标记在 `StepRecord` 级别，聚合到 `AgentTrace.any_tokens_estimated`。

---

## 6. Files Created / Modified

### New Files

| File | Description |
|------|-------------|
| `src/evaluation/trace.py` | 核心模块: StepType, ToolCallRecord, StepRecord, AgentTrace, TraceExtractor |
| `tests/unit_tests/test_trace.py` | 28 个单元测试覆盖所有 pattern 提取器 |

### Modified Files

| File | Change | Details |
|------|--------|---------|
| `src/evaluation/evaluator.py` | `TaskResult` 新增字段 | `trace: Optional[AgentTrace]`, `tokens_estimated: bool` |
| `src/evaluation/evaluator.py` | `_run_single_task()` | 替换旧 token 估算为 `TraceExtractor.extract()` |
| `src/evaluation/evaluator.py` | `to_dict()` | 新增 `trace_summary` (think/act/observe/tao_cycles) |
| `src/evaluation/evaluator.py` | `_collect_efficiency_metrics()` | 填充 `tao_cycle_counts`, `any_tokens_estimated` |
| `src/evaluation/__init__.py` | 导出 | `AgentTrace, StepRecord, StepType, TraceExtractor` |
| `src/evaluation/metrics.py` | `EfficiencyMetrics` 新增 | `tao_cycle_counts: List[int]`, `any_tokens_estimated: bool` |

---

## 7. Test Coverage

28 个单元测试 (`tests/unit_tests/test_trace.py`):

| Test Class | Tests | Coverage |
|-----------|-------|---------|
| `TestExtractReact` | 4 | 基本流、多轮工具、无工具、空内容 |
| `TestExtractReflex` | 2 | 基本流、无规则匹配 |
| `TestExtractSequential` | 2 | 三阶段流、单消息 |
| `TestExtractToT` | 2 | thought_tree 重建、空树 |
| `TestTokenExtraction` | 6 | usage_metadata 优先、response_metadata、估算、聚合、混合 |
| `TestToolPairing` | 2 | 单工具配对、多工具配对 |
| `TestDataStructures` | 5 | to_dict、TAO 计数、不完整序列、序列化 |
| `TestExtractGeneric` | 3 | 未知 pattern、空响应、非 dict 响应 |
| `TestEdgeCases` | 2 | values wrapper、dict messages |

---

## 8. Downstream Dependencies (为后续 Phase 提供的能力)

本 Phase 为后续 Phase 提供的基础能力映射:

| 后续 Phase | 依赖的 Phase A 能力 | 具体使用方式 |
|-----------|-------------------|------------|
| **Phase B1** (Dim 1: Reasoning Quality) | `StepRecord.content` where `step_type==THINK` | 提取推理链用于 coherence scoring |
| **Phase B2** (Dim 2: Cognitive Safety) | `AgentTrace.steps` 全部内容 | 遍历所有步骤进行 toxicity/hallucination 检测 |
| **Phase C1** (Dim 3: Action-Decision Alignment) | `THINK` vs `ACT` steps, `ToolCallRecord` | 比较 stated intention 与 actual tool calls |
| **Phase C2** (Dim 4: Success & Efficiency) | `AgentTrace.total_tokens`, `tao_cycles` | 归一化 cost score, step-to-budget ratio |
| **Phase C3** (Dim 5: Behavioural Safety) | `ToolCallRecord.tool_name`, `tool_args` | 与 `TestTask.policy.tool_whitelist` 比对 |
| **Phase D2** (Dim 7: Controllability & Transparency) | `tao_cycles`, step type 分布 | `trace_completeness = steps_with_full_TAO / total_steps` |
| **Phase E** (Normalization & Composite Scoring) | 所有 trace 聚合字段 | 作为 sub-indicator 输入归一化管道 |

---

## 9. Usage Example

```python
from src.evaluation.trace import TraceExtractor

# After graph.invoke()
response = graph.invoke({
    "messages": [{"role": "user", "content": "What is 2+2?"}],
    "evaluation_mode": True
})

# Extract trace
trace = TraceExtractor.extract(response, "react", "task_001")

# Access aggregates
print(f"TAO cycles: {trace.tao_cycles}")
print(f"Tool calls: {trace.total_tool_calls}")
print(f"Total tokens: {trace.total_tokens} (estimated: {trace.any_tokens_estimated})")

# Iterate steps
for step in trace.steps:
    print(f"  [{step.step_type.value}] {step.stage_label}: {step.content[:80]}")

# Serialize
trace_dict = trace.to_dict()
```

---

## 10. Verification Results

```
$ python -m pytest tests/unit_tests/test_trace.py -v
28 passed in 0.18s

$ python -c "from src.evaluation.trace import TraceExtractor, AgentTrace, StepRecord"
Import OK

$ python -c "from src.evaluation import AgentTrace, StepRecord, StepType, TraceExtractor, PatternEvaluator"
Full import chain OK
```
