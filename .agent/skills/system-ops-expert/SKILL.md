# Knowledge Consolidation Guidelines

To keep the workspace clean and maximize agent trigger rates, implemented design knowledge must be extracted from temporary planning files into permanent `SKILL.md` files.

## Consolidation Workflow

1. **Trigger**: A feature described in a `docs/plans/` or `docs/adr/` file is fully implemented and verified.
2. **Extraction**: Identify key architectural decisions, complex logic, constraints, and "lessons learned" (e.g., specific error patterns or edge cases).
3. **Integration**: Append or update the relevant `.agent/skills/<skill-name>/SKILL.md` with the extracted knowledge. Keep it concise and focused on *operational guidance* for the agent.
4. **Verification**: Confirm that the agent can retrieve this knowledge via `skills`.
5. **Pruning**: Delete the original source file (e.g., `rm docs/plans/old-plan.md`).

## Extraction Targets

- **Core Logic**: Mathematical formulas (e.g., Alpha Quality Gate dimensions), algorithmic steps.
- **Constraints**: API limits, data schema requirements, safety rules.
- **Heuristics**: Specific threshold values (e.g., IC > 0.02, t-stat > 2.0) that were decided during research.
- **Failures**: Known failure modes and how to avoid them (e.g., "Do not use $close without Ref in momentum calc").

## Deletion Policy

- Documentation that has been superseded by code + `SKILL.md` should be deleted to reduce "stale context" noise.
- Diaries (`docs/nikki/`) and raw papers (`docs/paper/`) are kept as archival history unless specifically asked to prune.
