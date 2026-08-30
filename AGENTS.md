# Repository Guidelines

## Short-context start

Read this file once, then read only the files that own the current task. Do not preload all docs, Issues, PR history, datasets, or research notes.

For non-trivial work, keep one bounded workline with five fields:

- **Decision** — what decision can improve.
- **Uncertainty** — what is not known.
- **Evidence test** — the smallest falsifiable next check.
- **Acceptance criteria** — direct conditions that prove the outcome.
- **Next action** — exactly one bounded action when the work must continue.

If an existing Issue/PR already owns the same decision and uncertainty, continue it. Durable state belongs in the repository/Issue/PR, not chat memory.

## Purpose and authority

`investor2` is the canonical workspace for investment hypotheses, point-in-time evidence, out-of-sample validation, and decision records. Optimize for decision quality and reproducible evidence, not activity volume.

Prefer current primary data, canonical repository state, exact revisions, and direct measurements over summaries or historical prose. Never infer unavailable values, dates, provenance, or model results.

## Canonical entry points

```text
task setup
task setup:quality
task check
task run:newalphasearch
task dashboard:dev
```

Use an existing Taskfile task instead of adding an alias or wrapper. For persisted external data, read `docs/specs/external_snapshot_store.md` only when that boundary is in scope.

## Evidence and research

- Reuse a sufficiently fresh accepted snapshot instead of fetching the same dataset again.
- Preserve source identity, retrieval time, query/scope, primary-source URL, schema/version, record count, and hash when the owning contract requires them.
- Fail closed when required provenance, schema, or artifacts are incomplete.
- A good backtest is not acceptance evidence by itself. Respect the applicable point-in-time, OOS, baseline, ablation, cost, and reproducibility contract.
- Report direct decision metrics that apply: after-cost return/P&L, Sharpe, drawdown, beta/correlation, turnover/exposure, benchmark comparison, and tested capital scale.
- A failed hypothesis is a valid result. Do not relabel it as success.

## Change rules

- Prefer the smallest structure that satisfies the goal. Do not create a second ledger, pipeline, state store, config authority, or workline for the same outcome.
- `DELETE > MERGE > REPLACE > ADD`; remove dead/obsolete paths only after current references prove them unused or invalid.
- Do not hide failures with broad exceptions, permissive defaults, silent fallback, stubs, mocks, dummy responses, cached examples, synthetic substitutes, or placeholders in production/runtime or acceptance-critical evaluation.
- A fallback is valid only when it is intentional behavior with an explicit trigger, observable state, bounded effect, and deterministic test. If an acceptance-critical run uses degraded/substitute behavior, it is not evidence of the requested outcome.
- Use Zod/Pydantic only at genuine runtime/untrusted boundaries; do not duplicate trusted internal types for ceremony.
- Comments should explain non-obvious rationale or external constraints, not narrate the code.

## Verification

Run the narrowest relevant verifier first. `task check` is the canonical repository-level gate unless a narrower documented contract fully owns the change.

A PR may merge when the exact reviewed revision satisfies the bounded repository-local acceptance criteria and deterministic checks with no unresolved correctness/data-integrity blocker.

Release is separate. A dataset/model/dashboard/public surface is released only after the merged revision and the actual external artifact/surface are directly verified. CI success does not prove deployment; merge does not prove release.

Classify claims as verified, observed, inferred, or unverified. Never upgrade inference or activity logs into verified results.

## Agent resources and continuation

Canonical skill source is `.agent/skills/`; reproduce with `agr sync`. `AGENTS.md` is the only repository-wide agent rule source.

If work cannot finish, update the existing Issue/PR/artifact with the last verified revision, evidence already obtained, remaining uncertainty, blocker, and one exact next falsifiable action. Branch cleanup is not a completion criterion.
