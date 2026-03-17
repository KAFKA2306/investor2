# ECC Pattern Reference for investor2

This document defines ECC (Extended Claude Code) patterns adopted by the investor project, with CDD-compliant implementation guidance.

For agent-specific pattern mappings, see `docs/AGENT_PATTERNS.md`.
For the integration strategy and decision rationale, see `docs/ECC_INTEGRATION_STRATEGY.md`.
For the ADR, see `docs/adr/004-ecc-integration.md`.

---

## 1. Tool Use Loop

An agentic loop where the model repeatedly calls tools until it reaches a terminal state.

```typescript
while (response.stop_reason !== "end_turn") {
  response = model.call(messages, tools)
  if (response.stop_reason === "tool_use") {
    const result = execute(response.tool_use) // crashes on failure -- no try-catch
    messages.push(response, result)
  }
}
```

**When to use**: Any agent that iteratively gathers data, refines results, or chains multiple tool calls before producing output.

**CDD constraint**: Tool execution failures propagate immediately. The infrastructure (Taskfile/Docker) retries the entire pipeline if needed.

**investor2 application**: LesAgent formula generation (deferred to Phase 3 due to architectural scope).

---

## 2. Subagent Delegation

A parent agent spawns focused child agents, each handling a sub-task. The parent aggregates results and makes the final decision.

```typescript
const resultA = await childAgentA.run(focusedTask1) // crashes if child fails
const resultB = await childAgentB.run(focusedTask2) // crashes if child fails
const decision = aggregate(resultA, resultB)
```

**When to use**: Complex multi-step workflows where each step has distinct domain expertise.

**CDD constraint**: If a child agent crashes, the parent MUST propagate the crash. No graceful degradation, no fallback to partial results.

**investor2 application**: LesAgent decomposition into ThemeProposer / FormulaGenerator / PlaybookFilter subagents (deferred to Phase 3).

---

## 3. Verification Loop

Execute a task, verify the result against criteria, and iterate if verification fails. Crash on exhaustion.

```typescript
for (let attempt = 1; attempt <= maxAttempts; attempt++) {
  const result = execute(task)
  const verdict = verify(result, criteria)
  if (verdict.pass) return result
  task = refine(task, verdict.feedback)
}
throw new Error("verification_exhausted") // CDD: MUST crash, never return null
```

**When to use**: Any agent producing output that must meet quantitative thresholds (Sharpe ratio, p-value, DSL validity).

**CDD constraint**: The loop is iterative refinement, NOT error suppression. On exhaustion, the agent crashes. Infrastructure handles retries.

**investor2 application**: AlphaQualityOptimizerAgent DSL generation (Phase 2 priority).

---

## 4. Memory Persistence

Persist execution state and learned patterns to durable storage. Read at cycle start to avoid repeating past mistakes.

```typescript
const history = readJSON(paths.persistenceFile) // crashes if file is corrupt
const result = executeWithContext(history, task)
writeJSON(paths.persistenceFile, { ...history, latest: result }) // crashes if write fails
```

**When to use**: Agents that run repeatedly and should build on prior outcomes.

**CDD constraint**: File I/O failures crash. No silent fallback to in-memory state.

**investor2 application**: MissionAgent pivot history, LesAgent generation statistics.

---

## 5. Context Compaction

At logical breakpoints, compact the conversation context by preserving decisions and discarding intermediate steps.

```
on_breakpoint:
  decisions = extract_decisions(context)
  context = compact(decisions)
  // intermediate tool results, reasoning chains discarded
```

**When to use**: Long-running agent sessions (multi-cycle alpha search) where token budget would otherwise be exhausted.

**Token impact**: Reduces context by 40-60% at each breakpoint. Combined with `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=50`, keeps sessions within budget.

**investor2 application**: StrategicReasonerAgent multi-cycle reasoning, pipeline orchestrator cycle boundaries.

---

## 6. Reasoning Pattern

Structured reasoning with claim-evidence-verdict triples for transparent audit of decision logic.

```typescript
const verdicts = dimensions.map(dim => ({
  claim: extractClaim(outcome, dim),
  evidence: gatherEvidence(outcome, dim),
  verdict: evaluate(claim, evidence, thresholds),
}))
const finalDecision = aggregate(verdicts) // GO / HOLD / PIVOT
```

**When to use**: Agents that make consequential decisions requiring explainable rationale.

**CDD constraint**: If evidence gathering or evaluation crashes, the crash propagates. No fallback to "default" verdicts.

**investor2 application**: StrategicReasonerAgent GO/HOLD/PIVOT logic (already partially implemented).

---

## Token Optimization Settings

Adopted from ECC with no CDD conflicts.

| Setting | Value | Rationale |
|---------|-------|-----------|
| `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` | `50` | Compact context at 50% capacity |
| Default model | Sonnet | Cost-efficient for routine tasks |
| Thinking token limit | 8000 | Prevent runaway reasoning costs |
| Subagent model | Haiku | Lightweight delegation tasks |

---

## CDD + ECC Reconciliation Summary

| Aspect | ECC Default | CDD Override | Resolution |
|--------|-------------|-------------|------------|
| try-catch | Encouraged | Prohibited in business logic | CDD wins |
| Graceful degradation | Return defaults | Crash instead | CDD wins |
| Retry logic | In-code retries | Infrastructure only | CDD wins |
| Verification loops | With fallback | Crash on exhaustion | CDD wins |
| Token optimization | Autocompact | No conflict | Adopt as-is |
| Session persistence | Hooks | No conflict | Adopt as-is |

ECC patterns apply to **infrastructure-layer** code (`src/io/`, hooks, configuration). Business logic (`src/domain/`, agents) remains strict CDD.
