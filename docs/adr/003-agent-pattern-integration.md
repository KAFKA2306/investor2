# ADR-003: ECC Agent Pattern Integration

## Status

Accepted

## Date

2026-03-17

## Context

The investor project has 6 agents extending BaseAgent, each with distinct responsibilities in the alpha discovery pipeline. These agents currently use linear control flow without iterative refinement, systematic learning, or structured delegation.

ECC (Extended Claude Code) defines proven agent patterns (Tool Use Loop, Subagent Delegation, Verification Loop, Continuous Learning v2, Context Compaction, Reasoning Pattern) that improve agent reliability, explainability, and adaptiveness.

The agents live in the investor repository (`/home/kafka/finance/investor/src/agents_*.ts`), not investor2. investor2 is the data pipeline layer; agent orchestration is documented here for cross-project alignment.

## Decision

1. **Document pattern mappings** in `docs/AGENT_PATTERNS.md` as the canonical reference for which ECC patterns apply to which agents.

2. **Prioritize Verification Loop** for AlphaQualityOptimizerAgent as the first integration -- it has the highest impact-to-effort ratio (reduces DSL generation failures without architectural changes).

3. **Prioritize Continuous Learning v2** for MissionAgent as the second integration -- enables smarter domain pivoting based on historical success rates.

4. **Defer Tool Use Loop and Subagent Delegation** for LesAgent -- these require fundamental architecture changes and should be implemented only after the simpler patterns prove value.

5. **All implementations MUST comply with CDD** -- no try-catch in business logic, verification loops crash on exhaustion, infrastructure handles retries.

6. **Agent code stays in investor repository** -- investor2 provides data infrastructure and documentation. No agent TypeScript files are created in investor2/src/.

## Consequences

- Pattern documentation enables any team member to implement the patterns without re-analyzing the agents.
- CDD compliance is enforced at the pattern level, not per-agent.
- Deferred patterns (Tool Use Loop, Subagent Delegation) can be revisited when the pipeline's cycle time warrants the investment.
- Cross-project alignment is maintained via shared documentation in investor2/docs/.
