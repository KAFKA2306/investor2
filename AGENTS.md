# Repository Guidelines

## Purpose

`investor2` is the canonical workspace for investment hypotheses, point-in-time evidence, out-of-sample validation, and decision records. Optimize for better decisions and reproducible evidence, not for issue count, experiment count, or code volume.

## Canonical commands

- `task setup` — install locked Bun/Python dependencies and the local `prek` hook.
- `task setup:quality` — install only fast quality-gate dependencies.
- `task check` — non-mutating repository reliability gate.
- `task run:newalphasearch` — validate a frozen real-data hypothesis capture and deep-dive candidates.
- `task dashboard:dev` — run the evidence dashboard locally.

Use Taskfile tasks when a canonical task exists. Do not add aliases that duplicate another entry point without reducing real operational complexity.

## Execution contract

For non-trivial work, keep one bounded goal and make these explicit:

- **Decision** — what investment or research decision can improve.
- **Uncertainty** — what is not yet known.
- **Evidence test** — the smallest falsifiable observation or experiment that can reduce that uncertainty.
- **Acceptance criteria** — direct conditions that prove the requested outcome.
- **Capability delta** — what reusable data, code, validation, or process remains afterward.

Then execute the shortest valid loop:

```text
inspect current state
  -> choose the smallest falsifiable next step
  -> implement or acquire evidence
  -> run the closest verifier
  -> inspect the result
  -> repair or reject when falsified
  -> persist reusable evidence
  -> stop when the acceptance criteria are satisfied
```

Do not create a second workline, ledger, pipeline, or state store when an existing canonical surface already represents the same outcome.

## Evidence and data

- Prefer current primary data, repository state, exact code revisions, and direct measurements over summaries or memory.
- Never infer unavailable rows, values, dates, provenance, or model results.
- Reusable external data acquired through APIs, MCP, connectors, or web sources must be materialized and registered through the repository's canonical snapshot/ledger path when persistence is in scope.
- Reuse an accepted sufficiently fresh snapshot instead of fetching the same dataset again.
- Preserve source identity, retrieval time, query/scope, primary-source URLs, schema version, record count, and SHA-256 where the owning data contract requires them.
- Fail closed when source identity, provenance, schema, or required artifacts are incomplete.

Canonical external-snapshot protocol: `docs/specs/external_snapshot_store.md`.

## Research validity

A good backtest is not acceptance evidence by itself. Research claims must respect the relevant preregistration, point-in-time, OOS, baseline, ablation, cost, and reproducibility contracts.

For investment-strategy validation, report the direct decision metrics that apply, such as after-cost return/P&L, Sharpe, maximum drawdown, beta/correlation, turnover/exposure, benchmark comparison, and the tested capital scale. A failed hypothesis is a valid result; do not relabel it as success.

## Code and quality

- Prefer the smallest structure that satisfies the goal.
- Remove dead entry points, duplicate configuration, obsolete instructions, and superseded paths when they are directly verified as unused or invalid.
- Do not hide failures with fallback values or broad exception handling. Handle recoverable external-boundary failures only when the recovery policy is explicit and testable.
- TypeScript: Biome for formatting/import organization, Oxlint for lint, `tsc --noEmit` for types.
- Python: Ruff for format/lint, Pyrefly for types.
- Use Zod/Pydantic at genuine untrusted/runtime boundaries; do not duplicate trusted internal types solely to add validation ceremony.
- Relevant focused tests should run before the full gate when they provide a cheaper signal.
- `task check` is the canonical repository-level verifier for code changes unless a narrower documented contract is sufficient.

## Agent resources

- Canonical skill source: `.agent/skills/`.
- Reproduce skills with `agr sync`.
- Do not maintain tool-specific copies of repository rules. `AGENTS.md` is the single source of repository-wide agent guidance; tool-specific instruction files may only point here.

## Continuation and scope

Before changing the repository, inspect current `main`, relevant Issues/PRs, exact-head CI where applicable, and existing canonical artifacts. Continue an existing workline when it already owns the same decision and uncertainty.

If a workline cannot finish, record the last verified revision, evidence already acquired, remaining uncertainty, blocker, and exact next falsifiable action in the existing Issue/PR/artifact surface. Do not rely on chat memory as the durable continuation mechanism.

Branch deletion and orphan-branch cleanup are outside this agent's completion responsibility. Do not create cleanup-only worklines, do not treat branch deletion as an outcome blocker, and do not report repository work as incomplete solely because stale branches exist. Avoid creating unnecessary branches; code changes should still use a normal reviewable PR workline when appropriate.

## Merge and release

Repository integration and external release are separate states.

A PR may merge when the exact reviewed revision satisfies the bounded repository-local acceptance criteria and relevant deterministic checks, with no unresolved correctness or data-integrity blocker.

A product, dataset, model, dashboard, or public surface is released only after the merged `main` revision and the actual release surface/artifact are directly verified. CI success does not prove deployment; merge does not prove release.

Report `merged` and `released` independently when release is in scope.

## Completion

A workline is complete only when the requested outcome itself has been inspected. Examples:

- code change -> focused verifier plus repository gate/CI as applicable;
- reusable dataset -> persisted artifact plus canonical registration/read-back;
- research claim -> versioned inputs/code plus direct OOS/result metrics;
- publication/deployment -> live surface read-back tied to the merged revision.

Distinguish claims as verified, observed, inferred, or unverified. Never upgrade an inference or activity log into a verified result.
