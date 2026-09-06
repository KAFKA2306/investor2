---
name: alpha-mining
description: Use for alpha-factor hypothesis implementation and empirical validation under the repository's preregistered PIT/OOS research contract.
origin: local-git-analysis
---

# Alpha Mining

Use this skill to turn an auditable alpha hypothesis into reproducible evidence. Repository-wide execution and completion rules come from `AGENTS.md`; this file contains only alpha-research-specific constraints.

## Canonical contract

Before reading untouched OOS results, freeze:

- source and economic mechanism;
- exact signal definition and data lags;
- universe and exclusions;
- point-in-time availability rules;
- train / validation / chronological OOS periods;
- baseline and ablation plan;
- transaction-cost, borrow, liquidity, and capacity assumptions where applicable;
- primary metric and rejection criterion;
- allowed parameter variants, seeds, and compute budget.

If any choice changes after observing results, create a new hypothesis/protocol version.

## Validation order

1. Implement a deterministic baseline.
2. Verify source/data provenance and PIT integrity.
3. Reproduce the intended signal calculation.
4. Run chronological untouched OOS.
5. Run post-publication and cross-market/regime checks when applicable.
6. Measure after-cost return/P&L, Sharpe, drawdown, turnover/exposure, benchmark dependence, and tested scale when applicable.
7. Inspect nearby-parameter stability and known-factor/industry exposure.
8. Add any LLM-derived extraction/filter only as a matched ablation against the same frozen OOS contract.
9. Persist positive and negative results as machine-readable evidence.

## LLM boundary

LLMs may assist with extraction, normalization, code generation, and hypothesis extension. The resulting implementation must be reproducible without conversational memory. An LLM-generated narrative, novelty score, or plausible mechanism is not evidence of alpha.

## Research rejection rules

- No future references or survivorship leakage.
- Do not substitute in-sample results when OOS data is unavailable.
- Do not relax thresholds, change metrics/splits, or change representatives after results are observed.
- Do not report only the best seed for stochastic methods.
- Fallback, stub, demo, placeholder, or synthetic results are not empirical alpha evidence unless the frozen experiment explicitly evaluates synthetic data.
- Rejected and unresolved candidates remain visible evidence.

If repeated exploration saturates a domain, move to a genuinely different mechanism under a newly frozen protocol.

## Required output

Every material run should persist enough information to reproduce and audit the verdict, including input identifiers/hashes, split dates, observation counts, signal/portfolio definition, configuration, seeds, direct metrics, cost assumptions, uncertainty, failure reasons, code revision, and verdict.

When only part of the pipeline is valid, persist the verified boundary and the missing requirement.

## Canonical references

- `AGENTS.md`
- `docs/specs/alpha_discovery_runbook.md`
- `docs/specs/time_tested_alpha_policy.md`
- `docs/architecture/canonical-investment-flow.md`
- `docs/specs/external_snapshot_store.md`
