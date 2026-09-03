# FX overlay contract

Issue: #252

`src/decision/fx_overlay.ts` is the canonical repository-local calculation boundary for portfolio-level USD/JPY overlay decisions.

## Authority

- Existing USD exposure is calculated from position market value and each asset's USD economic exposure before any FX overlay is added.
- FX is represented only as incremental USD exposure. QQQ or other USD assets are not re-added as FX positions.
- Realized broker swap is an explicit input. Policy-rate spreads, bank target prices, and strategist forecasts are not accepted as carry substitutes or optimizer inputs.
- CFTC crowding can reduce the admissible USD-long risk budget. It does not modify expected FX return and cannot create a long/short signal by itself.
- Point-in-time availability is enforced in walk-forward evaluation. Training observations or crowding data unavailable at the decision timestamp make the result `UNVERIFIED`.
- Missing short-side realized swap makes negative overlay evaluation `UNVERIFIED`; there is no silent policy-rate fallback.
- `test_fixture` evidence can exercise deterministic logic but can produce only `TEST_ONLY`, never `VERIFIED`.

## Published API

Canonical publication path:

`api/v1/portfolio/fx-overlay.json`

This file is the public machine-readable FX overlay artifact for downstream consumers such as `KAFKA2306/finBI`. Consumers should read this artifact directly and must not maintain a second hand-authored copy of the same result.

The artifact uses the same `investor2.fx-overlay.v1` result union as `src/decision/fx_overlay.ts`:

- `VERIFIED`: publish the calculated result only when every production input and provenance/PIT gate passes.
- `TEST_ONLY`: permitted for deterministic test evidence, but never as a production recommendation.
- `UNVERIFIED`: publish only `schema_version`, `status`, and a concrete `reason`; do not publish invented numeric defaults.

When the canonical production inputs become available, update this same path from the canonical calculation output. Do not create a second portfolio/FX API path for compatibility.

## Output

Schema version: `investor2.fx-overlay.v1`

The calculation returns one of:

- `VERIFIED`: every position and observation is marked real and all provenance/PIT checks pass.
- `TEST_ONLY`: deterministic execution succeeded but at least one input is a test fixture.
- `UNVERIFIED`: required provenance, timing, swap, risk, or configuration data is missing or inconsistent.

A verified/test-only result contains:

- current USD exposure
- recommended incremental USD exposure
- recommended total USD exposure
- hedge ratio and over-hedge flag
- margin requirement and remaining configured headroom
- OOS CAGR, volatility, Sharpe, Sortino, max drawdown, expected shortfall, worst period
- annualized FX, carry, funding-cost, and transaction-cost contributions
- margin-call / forced-liquidation counts and turnover
- fixed 0x / 0.5x / 1x / 2x / 3x baselines, with infeasible baselines reported rather than clamped
- unique source references for portfolio and market/carry observations

`finBI` should consume this output contract. It must not reimplement the optimizer or rebuild a second FX/carry authority.

## Optimization

Incremental exposure is a continuous scalar. The optimizer solves the one-dimensional mean-variance optimum separately for long and short overlay legs and applies hard bounds from:

- incremental exposure limits
- total portfolio USD-exposure limits
- initial-margin usage
- overlay expected-shortfall budget
- CFTC USD-long crowding reduction

The selected exposure is therefore not restricted to fixed leverage buckets. Fixed 0x / 0.5x / 1x / 2x / 3x values are comparison baselines only.

## Production evidence

#251 owns the canonical realized Rakuten FX swap/margin evidence. #252 must consume that evidence; it must not copy a current swap value into a second ledger or backfill unavailable history with a constant/synthetic series.

Until #251 materializes a sufficiently long daily realized swap series and the actual portfolio position snapshot is supplied as canonical inputs, repository logic can be verified but a live portfolio recommendation remains `UNVERIFIED`.
