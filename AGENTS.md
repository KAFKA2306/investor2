# Investor2 Agent Contract

`AGENTS.md` is the repository-wide instruction source. Canonical task-specific skills live in `.agent/skills/`.

## Scope

This repository owns investment hypotheses, point-in-time evidence, out-of-sample validation, and decision records. Optimize decision quality and reproducibility rather than activity volume.

Use current primary data, exact source identity and timestamps, canonical repository state, and direct measurements. Do not infer unavailable values, dates, provenance, model results, or success.

For persisted external data, preserve the provenance fields required by the owning snapshot contract, including source, retrieval time, query/scope, primary URL, schema/version, record count, and hash.

## Research invariants

- A backtest alone is not acceptance evidence. Respect point-in-time data, untouched OOS evaluation, baseline, ablation, costs, reproducibility, and applicable portfolio metrics.
- A failed hypothesis is a valid result.
- Fail closed on missing acceptance-critical provenance, schema, or artifacts.
- Do not substitute mocks, dummy values, cached examples, or silent fallback for acceptance-critical production data.

## Market-narrative falsification

For AI funding, credit, semiconductor valuation, investor positioning and hedges, use [the 2026-11-21 five-hypothesis decision contract](docs/research/ai-capital-capacity-20261121.md). Do not promote videos, news reports, or user-supplied model summaries to primary observations or reproduced results.

Treat spread level and issuance quantity as different measurements; do not infer risk-on from narrowing OAS without issuance and real-activity evidence. Derive earnings implied by a forward P/E using consistent EPS periods and index membership. Separate sector rotation from cash liquidation. Recompute each long/short leg's capital contribution, costs, GLD ablation, and a pre-fixed forward OOS window before accepting hedge or alpha claims. Missing underlying portfolio records are `UNVERIFIED`, not a positive performance result.

Reuse `econalert` as the official liquidity-series owner and this repository's existing input, hypothesis, evidence and decision ledgers. Do not create another liquidity collector or hosted workflow. Individual companies are research components; this study does not authorize individual-stock purchases or automated trades.

## Canonical execution

Reuse the existing `Taskfile.yml` surface and canonical ledger/pipeline/config for the outcome. `task check` is the repository-level gate unless a narrower documented verifier fully proves the changed contract.

## Release boundary

Repository checks prove only the exact revision they executed. Dataset, model, dashboard, or public release requires direct verification of the actual merged artifact or surface. CI success does not prove deployment, and merge does not prove release.

## Outcome-first task interpretation (Altitude / Depth / Range / Speed)

- **Altitude:** Interpret a task as a verifiable user outcome, not only the named intermediate step. Infer the smallest justified acceptance criteria from the request and current repository state; do not silently expand scope or override explicit instructions.
- **Depth:** Use primary/current evidence and real domain tools and methods. Verify the actual postcondition independently of agent self-report, preferably on the exact changed revision or target runtime.
- **Range:** Combine code, data, tests, runtime/UI, and domain expertise when that materially improves the outcome, while respecting canonical owners and avoiding duplicate systems.
- **Speed:** Complete authorized read-only and reversible work through implementation, focused checks, and read-back without unnecessary approval loops. Bound retries and stop at the proven outcome.
- These principles never bypass repository-specific security, privacy, permission, publication, spending, destructive-action, or release boundaries. State verified results and any remaining `UNVERIFIED` layers.
