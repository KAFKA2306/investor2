# Agent Patterns Reference: ECC Integration for investor

This document maps ECC (Extended Claude Code) agent design patterns to the investor project's existing agent implementations. The source agents live in `/home/kafka/finance/investor/src/agents_*.ts` and extend `BaseAgent` from `src/system/app_runtime_core.ts`.

## Agent Inventory

| Agent | File | Role | Primary ECC Patterns |
|-------|------|------|---------------------|
| LesAgent | `agents_latent_economic_signal_agent.ts` | Alpha factor generation (qlib DSL) | Tool Use Loop, Subagent Delegation, Memory Persistence |
| AlphaQualityOptimizerAgent | `agents_alpha_quality_optimizer_agent.ts` | DSL quality optimization via Qwen | Verification Loop, Eval Harness |
| StrategicReasonerAgent | `agents_alpha_r1_reasoner_agent.ts` | GO/HOLD/PIVOT verdict logic | Reasoning Pattern, Iterative Retrieval |
| MissionAgent | `agents_mission_agent.ts` | Context steering, domain pivot | Continuous Learning v2, Context Persistence |
| ScanAgent | `agents_polymarket_scan_agent.ts` | Polymarket signal scanning | Tool Use Loop |
| ExecuteAgent | `agents_polymarket_execute_agent.ts` | Polymarket trade execution | Verification Loop |

---

## ECC Pattern Definitions

### 1. Tool Use Loop

An agentic loop where the model repeatedly calls tools until it reaches a terminal state.

```
while (response.stop_reason !== "end_turn") {
  response = model.call(messages, tools)
  if (response.stop_reason === "tool_use") {
    result = execute(response.tool_use)
    messages.push(response, result)
  }
}
```

**When to apply**: Any agent that needs to iteratively gather data, refine results, or chain multiple tool calls before producing output.

### 2. Subagent Delegation

A parent agent spawns focused child agents, each handling a sub-task. The parent aggregates results and makes the final decision.

```
parent_agent:
  spawn child_a(focused_task_1) -> result_a
  spawn child_b(focused_task_2) -> result_b
  aggregate(result_a, result_b) -> final_decision
```

**When to apply**: Complex multi-step workflows where each step has distinct domain expertise.

### 3. Verification Loop

Execute a task, verify the result against criteria, and iterate if verification fails.

```
for attempt in 1..max_attempts:
  result = execute(task)
  verdict = verify(result, criteria)
  if verdict.pass: return result
  task = refine(task, verdict.feedback)
throw "verification_exhausted"
```

**When to apply**: Any agent producing output that must meet quantitative thresholds (Sharpe, p-value, DSL validity).

### 4. Continuous Learning v2

Extract reusable patterns from execution outcomes. Maintain an instinct registry with confidence scores that evolve over cycles.

```
on_cycle_complete(outcome):
  patterns = extract_patterns(outcome)
  for pattern in patterns:
    if pattern in instinct_registry:
      instinct_registry[pattern].confidence += delta(outcome)
    else:
      instinct_registry.add(pattern, confidence=0.5)
  prune(instinct_registry, threshold=0.1)
```

**When to apply**: Agents that run repeatedly and should avoid repeating past failures.

### 5. Context Compaction

At logical breakpoints, compact the conversation context by preserving decisions and discarding intermediate steps. Resets token budget per cycle.

```
on_breakpoint:
  decisions = extract_decisions(context)
  context = compact(decisions)
  // intermediate tool results, reasoning chains discarded
```

**When to apply**: Long-running agent sessions (e.g., multi-cycle alpha search) where token budget would otherwise be exhausted.

### 6. Reasoning Pattern

Structured reasoning with claim-evidence-verdict triples, enabling transparent audit of decision logic.

```
for each dimension:
  claim = extract_claim(outcome, dimension)
  evidence = gather_evidence(outcome, dimension)
  verdict = evaluate(claim, evidence, thresholds)
aggregate(verdicts) -> final_reasoning
```

**When to apply**: Agents that make consequential decisions (GO/HOLD/PIVOT) requiring explainable rationale.

---

## Pattern Application by Agent

### LesAgent (Alpha Factor Generation)

**Current state**: Single-pass formula generation with evolutionary crossover. Calls OpenAI for theme proposals. No iterative refinement loop.

**Pattern: Tool Use Loop**
- **Where**: `generateAlphaFactors()` currently generates candidates in a single `while` loop with random depth/bias. With Tool Use Loop, LesAgent could iteratively call an LLM tool to propose, evaluate, and refine formulas.
- **Control flow change**: Replace the `while (candidates.length < count && attempts < 50)` loop with an agentic loop where each iteration queries market data tools, evaluates candidate quality, and decides whether to continue or stop.

**Pattern: Subagent Delegation**
- **Where**: LesAgent currently handles theme selection, formula generation, and playbook filtering in one method. Delegation would split into:
  - `ThemeProposerSubagent` -- proposes themes (currently `OpenAIThemeProvider`)
  - `FormulaGeneratorSubagent` -- generates qlib DSL formulas
  - `PlaybookFilterSubagent` -- deduplicates against existing playbook
- **Benefit**: Each subagent can be tested and evolved independently.

**Pattern: Memory Persistence**
- **Where**: `loadMissionContext()` and `readNaturalLanguageInput()` already read persisted state. Enhancement: persist generation statistics (success/failure rates per theme, operator combinations that produce non-trivial factors) to a JSON file read at cycle start.

### AlphaQualityOptimizerAgent (CQO Role -- Quality Gate)

**Current state**: Linear pipeline: build prompt -> call Qwen -> validate DSL -> evaluate quality -> return. Validation has a simple repair step but no retry loop.

**Pattern: Verification Loop**
- **Where**: `evaluate()` method steps 2-2.5. Currently, if DSL validation fails and is unrepairable, it throws. A Verification Loop would:
  1. Generate DSL via Qwen
  2. Validate DSL
  3. If invalid and unrepairable: feed error back to Qwen with the validation errors
  4. Repeat up to N attempts
  5. Crash if all attempts fail (CDD compliant -- no silent fallback)
- **CDD constraint**: The loop itself is acceptable because it's a generation-verification cycle, not error suppression. The final throw on exhaustion is mandatory.

**Pattern: Eval Harness**
- **Where**: `evaluateAlpha()` from `quality_gate.ts` computes 4 scores. An Eval Harness wraps this in a standardized evaluation framework:
  - Input: formula + market context
  - Output: structured verdict with scores, pass/fail per criterion
  - Logging: every evaluation logged for post-hoc analysis
- **Current gap**: Telemetry is logged via `logIO`/`logMetric` but not in a harness-standard format. Standardize output schema for cross-agent comparison.

### StrategicReasonerAgent (Reasoning & Decision Logic)

**Current state**: Deterministic rule-based reasoning with 3 specialist "reviewers" (Risk Manager, Alpha Hunter, Regime Specialist) implemented as if-else blocks.

**Pattern: Reasoning Pattern**
- **Where**: `reasonAboutAlpha()` already uses claim-evidence-verdict triples (`logicChecks`). This is the Reasoning Pattern. Enhancement:
  - Add confidence scores per verdict (not just VALID/INVALID/UNCERTAIN)
  - Weight verdicts by historical accuracy (connect to Continuous Learning)
  - Enable dynamic addition of new specialist dimensions without code changes

**Pattern: Iterative Retrieval**
- **Where**: `screenAlpha()` currently makes a one-shot decision. Iterative Retrieval would:
  1. Retrieve similar historical outcomes from playbook
  2. Compare current outcome against historical distribution
  3. If edge case detected: retrieve additional context (regime data, sector data)
  4. Re-evaluate with enriched context
- **Benefit**: More robust HOLD decisions where marginal metrics need additional evidence.

**Pattern: Context Compaction**
- **Where**: When StrategicReasonerAgent runs in a multi-cycle pipeline, the accumulated reasoning from prior cycles should be compacted to preserve decisions but discard intermediate evidence gathering.

### MissionAgent (Context Management)

**Current state**: Generates markdown mission files. `pivotDomain()` writes a new mission based on failure history.

**Pattern: Continuous Learning v2**
- **Where**: `pivotDomain()` reacts to failures but doesn't learn from them systematically. Enhancement:
  - Maintain a `pivot_history.json` tracking: domain -> attempt_count -> outcome
  - Score each domain's historical success rate
  - When pivoting, prefer domains with highest unexplored potential (not just "avoid failed")
  - Decay confidence in domains that haven't been tested recently

**Pattern: Context Persistence**
- **Where**: Already writes to `paths.missionMd`. Enhancement:
  - Add structured JSON alongside markdown for machine-readable context
  - Include `lastCycleMetrics` snapshot for trend detection
  - Persist across sessions via a durable context store (not just file overwrite)

---

## Integration Priority

| Priority | Agent | Pattern | Effort | Impact |
|----------|-------|---------|--------|--------|
| 1 | AlphaQualityOptimizer | Verification Loop | Low | High -- reduces DSL generation failures |
| 2 | MissionAgent | Continuous Learning v2 | Medium | High -- smarter domain pivoting |
| 3 | StrategicReasoner | Reasoning Pattern (enhanced) | Low | Medium -- better explainability |
| 4 | LesAgent | Tool Use Loop | High | High -- fundamental architecture change |
| 5 | LesAgent | Subagent Delegation | High | Medium -- cleaner separation of concerns |

---

## CDD Compliance Notes

All pattern implementations MUST follow Crash-Driven Development:

- **Verification Loop**: The loop is NOT error suppression. It is iterative refinement. On exhaustion, the agent MUST crash (throw).
- **Tool Use Loop**: Tool execution failures MUST propagate. No try-catch around tool calls.
- **Continuous Learning**: Persistence failures (file write errors) MUST crash. No silent fallback to in-memory state.
- **Subagent Delegation**: If a child agent crashes, the parent MUST propagate the crash. No graceful degradation.

Infrastructure (Taskfile, Docker) handles retries of the entire pipeline, not the agent code.
