# Pattern Instruction Guide

> Status: Guidance Only
> Scope: Reflex, ReAct, CoT/Sequential, ToT
> Important: This document is design guidance only. It does not require any code change by itself.

---

## 1. Purpose

This document explains how instructions should be designed for the four evaluated patterns without directly changing pattern code.

The goal is to support fair evaluation under the proposal while preserving the defining behavior of each pattern.

The four patterns are:

1. Reflex
2. ReAct
3. CoT / Sequential
4. ToT

This guide should be read before implementing or revising prompts, system messages, or evaluation-time task wrappers.

---

## 2. Core Principle

Do not give every pattern exactly the same instruction text.

Also do not give every pattern a completely different full prompt.

The correct approach is:

- one shared core instruction for fairness
- one minimal pattern-specific instruction block for behavior fidelity

This is the most defensible setup because it separates:

- common experimental constraints
- pattern-defining behavioral guidance

---

## 3. Why a Shared Core Instruction Is Necessary

All patterns should receive the same experimental baseline requirements. Otherwise, performance differences may come from prompt engineering rather than from the pattern itself.

The shared core instruction should define:

- the task should be solved accurately
- output format requirements must be followed exactly
- tools may be used only when necessary
- fabricated facts or unsupported claims are not allowed
- task constraints and safety limits must be respected
- the agent should stop once enough evidence is collected

This shared core is important for:

- fair comparison
- unified telemetry interpretation
- later scoring of cognitive safety and constraint adherence

---

## 4. Why Pattern-Specific Guidance Is Also Necessary

The four patterns do not behave the same way internally.

If they receive only a shared instruction and nothing more, two problems appear:

1. some patterns will not express their intended design behavior
2. the evaluation may measure prompt mismatch rather than architectural difference

Pattern-specific guidance is acceptable only when it is necessary to preserve the pattern's definition.

It should not be used to "make one pattern stronger" than another.

---

## 5. Recommended Instruction Structure

Every pattern instruction should be split into two layers.

### Layer A: Shared Core Instruction

This part should be identical across all four patterns.

Recommended content:

- solve the user's task correctly
- follow requested output format exactly
- use only provided tools
- do not fabricate facts, tool results, or evidence
- avoid unnecessary tool use
- respect task constraints and policy boundaries
- keep the final answer concise in evaluation mode

### Layer B: Pattern-Specific Instruction

This part should differ across patterns, but only slightly.

Its only job is to preserve the defining behavior of the pattern.

---

## 6. Pattern-by-Pattern Guidance

### 6.1 Reflex

The Reflex pattern is meant to prioritize quick rule-based response.

Instruction emphasis should be:

- use the fastest matching rule or direct action
- prefer minimal deliberation
- do not expand reasoning unnecessarily
- fall back to open-ended reasoning only when rule matching is insufficient

Do not tell Reflex to explore multiple alternatives or produce long chain reasoning. That would change the pattern into something else.

### 6.2 ReAct

The ReAct pattern is defined by the reasoning-action-observation loop.

Instruction emphasis should be:

- identify the immediate next step before acting
- use one action at a time when possible
- inspect observations before deciding what to do next
- continue looping until enough evidence is available

Do not overload ReAct with full planning-pipeline requirements or branch-comparison requirements. That would blur the distinction between ReAct, Sequential, and ToT.

### 6.3 CoT / Sequential

The Sequential pattern in this project acts as the CoT-style pipeline.

Instruction emphasis should be:

- produce an explicit plan first
- execute according to the plan
- review and synthesize before final answer
- maintain step order unless new evidence requires revision

Do not force it into a dynamic action loop like ReAct, and do not require exploration of multiple branches like ToT.

### 6.4 ToT

The ToT pattern is defined by branch exploration and pruning.

Instruction emphasis should be:

- generate multiple candidate solution paths
- compare branches for relevance and feasibility
- prune weaker branches
- choose the strongest branch before answering

Do not reduce ToT to a single linear plan. If the instruction makes ToT behave linearly, the pattern is no longer meaningfully ToT.

---

## 7. What Should Not Be Pattern-Specific

The following should remain shared across patterns:

- output format rules
- JSON-only or number-only constraints
- anti-hallucination requirements
- tool boundary rules
- safety and policy constraints
- stop conditions once enough evidence is available

These belong to evaluation fairness, not to pattern identity.

---

## 8. What Should Not Be Added at All

Do not add instructions that artificially strengthen one pattern beyond its definition.

Examples of problematic additions:

- "always double-check every answer three times"
- "always use tools first"
- "always be extremely detailed"
- "always produce long reasoning traces"

These are not pattern-preserving instructions. They are prompt-optimization choices and would contaminate the comparison.

---

## 9. Recommended Experimental Use

This guide should be applied in one of two ways.

### Option A: Documentation-first

Keep this document as the methodological rulebook and only update prompts later when the experiment protocol is frozen.

This is the safest choice if the team is still deciding how to implement prompt control.

### Option B: Prompt revision after protocol freeze

Once the evaluation protocol is frozen, use this document to revise:

- system prompts
- stage prompts
- evaluation-mode prompts

This should be done uniformly and documented in the report.

---

## 10. Documentation Requirement

If the team later implements these instructions in code, the report should clearly state:

- which part was shared across all patterns
- which part was pattern-specific
- why each pattern-specific clause was necessary
- why no extra prompt optimization was added beyond pattern identity

This explanation is important because it defends the fairness of the comparison.

---

## 11. Recommended Next Step

Before changing any code, the team should do this:

1. freeze one shared core instruction
2. write one minimal pattern-specific block for each of the four patterns
3. review the four blocks side by side
4. remove any instruction that strengthens one pattern in a non-essential way
5. only then decide whether to implement them in code

This makes the instruction design auditable and easier to justify in the final report.
