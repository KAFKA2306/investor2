---
name: polymarket
description: Acquire and normalize Polymarket Gamma/CLOB data for reproducible research.
origin: local
---

# Polymarket

Use the existing Polymarket evidence path:

- `src/io/providers/polymarket.py`
- `scripts/polymarket_snapshot.py`
- `data/input_ledger/source_registry.d/polymarket_market_data.json`
- `.github/workflows/polymarket-live.yml`

Gamma metadata and CLOB quotes/history must retain market identity, outcomes, token IDs, prices, liquidity, observation time, and query scope.

Distinguish unavailable quotes from valid zero values. Verify outcome/token cardinality before research use.

Define spread, liquidity, horizon, and signal thresholds in the individual frozen research protocol rather than in this skill. Trading execution is outside this skill.
