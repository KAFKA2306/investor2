---
name: polymarket
description: Acquire and validate Polymarket Gamma/CLOB market data for reproducible research. Use for market discovery, quote/history snapshots, source-health checks, normalization, provenance, and prediction-market hypothesis evaluation.
origin: local
---

# Polymarket

Use the repository's existing Polymarket provider, snapshot script, input ledger, and live source-health workflow. Do not create a second market-data path or claim trade execution when the current workline only establishes evidence acquisition.

## Contract

- Treat Gamma metadata and CLOB quotes/history as external observations with retrieval time and source identity.
- Normalize market identity, outcomes, token IDs, prices, liquidity, and timestamps before research use.
- Reject incomplete identity or outcome/token cardinality mismatches rather than guessing values.
- Distinguish unavailable CLOB quotes from valid zero values.
- Preserve the exact query scope and observation time in persisted snapshots.
- Define liquidity, spread, horizon, and anomaly thresholds in the specific research protocol; do not hard-code universal promotion thresholds in this skill.
- Evaluate prediction-market signals with frozen OOS, costs, liquidity, and reproducibility rules before making an alpha claim.

## Current surfaces

- `src/io/providers/polymarket.py` — Gamma/CLOB provider and normalization.
- `scripts/polymarket_snapshot.py` — snapshot and health entry point.
- `data/input_ledger/source_registry.d/polymarket_market_data.json` — registered source.
- `.github/workflows/polymarket-live.yml` — live source-health verification.
