# Issue #161 — daily market session research protocol

Status: pre-launch protocol recorded before inspection of post-23/5 U.S. exchange outcomes.

## Decision

Decide whether session decomposition is useful in investor2 as a point-in-time price-driver / participant-regime state variable. The final decision is `USE`, `CONDITION`, or `REJECT`; a historical close-to-open premium alone is not sufficient evidence.

## Design rule: no research defaults in code

The reusable implementation must not encode a preferred market, universe, date range, estimator horizon, warm-up, annualization factor, or corporate-action convention.

Every run supplies these values explicitly:

- one or more immutable market snapshot roots;
- market region(s);
- ticker universe;
- inclusive start and end dates;
- corporate-action mode: `adjusted` or `raw`;
- SessionTilt EWMA half-life;
- SessionTilt minimum observations;
- annualization trading-day factor;
- output path.

The emitted result records the exact values. Reproducibility comes from the saved experiment specification and source manifests, not from hidden CLI defaults.

## Issue #161 pre-launch experiment specification

The values below describe this experiment only. They are not reusable implementation defaults.

- cutoff: 2026-08-21, the last completed U.S. regular session before this work started;
- broad/size proxies: `SPY`, `QQQ`, `IWM`, `DIA`;
- article case studies: `MU`, `COST`;
- primary SessionTilt half-life: 126 observations;
- primary warm-up: 126 valid observations;
- sensitivity half-lives: 63 and 252 observations;
- descriptive annualization factor: 252 trading days;
- primary corporate-action convention: adjusted;
- raw-price results: separately labelled robustness variant.

Changing any of these values creates a different experiment specification and must be visible in the output.

## Data contract

Research code consumes materialized immutable snapshots and does not fetch a provider inside the analysis path. Snapshot provider, region, date coverage, storage prefix, and provenance come from the snapshot manifest rather than from assumptions in the daily-market-session code.

Repeated `--market-snapshot-dir` inputs may compose multiple immutable shards. Requested coverage must be gap-free; duplicate `Ticker/Date` rows fail closed rather than selecting an implicit winner.

A cache collected from one region or provider must not be silently substituted for another. Historical point-in-time index membership must not be inferred from a present-day collected universe.

For the pre-launch U.S. block, the immutable source window is `2000-01-01..2026-08-22` exclusive and the universe is the exact six-symbol list above. The explicit-universe builder must fail if any requested symbol is absent. This avoids silently replacing the preregistered universe with whatever a provider screener happens to return later.

## Corporate-action modes

### adjusted

```text
AdjustmentFactor_t = AdjClose_t / Close_t
AdjustedOpen_t     = Open_t * AdjustmentFactor_t
AdjustedClose_t    = AdjClose_t
```

This mode requires `AdjClose`.

### raw

```text
AdjustmentFactor_t = 1
AdjustedOpen_t     = Open_t
AdjustedClose_t    = Close_t
```

This mode does not require `AdjClose` and intentionally preserves raw-price discontinuities for robustness analysis.

## Return definitions

For asset `i` and trading day `t`:

```text
r_ON(i,t) = AdjustedOpen(i,t) / AdjustedClose(i,t-1) - 1
r_ID(i,t) = AdjustedClose(i,t) / AdjustedOpen(i,t) - 1
r_CC(i,t) = AdjustedClose(i,t) / AdjustedClose(i,t-1) - 1
```

Log components must satisfy, up to floating-point tolerance:

```text
log_r_ON + log_r_ID = log_r_CC
```

Daily provider bars are not assumed to be auction-only official prices. Auction, quote-mid, VWAP, or explicit extended-session variants require separately materialized inputs.

## SessionTilt family

For explicitly supplied half-life `h` and warm-up `m`:

```text
spread(i,t) = r_ON(i,t) - r_ID(i,t)
num(i,t)    = EWMA(spread, half-life=h, adjust=False, min_periods=m)
den(i,t)    = EWMA_STD(log_r_CC, half-life=h, adjust=False, min_periods=m)
SessionTilt_h(i,t) = num(i,t) / den(i,t)
```

Both numerator and denominator use only data available through `t`.

The denominator is an investor2 operationalization. The source article writes `sigma(r_CC)` without fully fixing its estimator, so exact article replication is not claimed from this formula alone.

## Frozen historical OOS test

The primary daily-bar predictive task is fixed before the U.S. snapshot is materialized:

```text
feature available: close(t)
target:            r_ON(t+1) - r_ID(t+1)
training window:   2021-01-01 through 2024-12-31
strict test:       2025-01-01 through 2026-08-21
primary feature:   adjusted SessionTilt_126
simple baselines:  training-mean/intercept and lagged session spread
```

No 2025–2026 target is used to fit the linear predictive coefficients. The fixed sign strategy uses `sign(SessionTilt_t)` for the next overnight leg and the opposite sign for the following regular-session leg.

Execution-cost reporting uses a conservative four one-way notional changes per active asset-day. Primary cost is 1 bp per side; 0 bp and 5 bp per side are mandatory sensitivity points. Capacity is `NOT_TESTED_DAILY_BARS`; therefore these results cannot by themselves support a capacity or institutional-tradability claim.

### Frozen pre-launch decision rule

For the primary adjusted 126-day test:

- `predictive_pass`: OOS SessionTilt information coefficient is positive and SessionTilt OLS MSE is lower than both the intercept-only and lagged-session-spread baselines;
- `breadth_pass`: at least 4 of 6 tickers have positive OOS SessionTilt information coefficient;
- `primary_cost_pass`: equal-weight sign-strategy annualized arithmetic return and Sharpe are both positive after 1 bp/side costs;
- `five_bps_pass`: the same two metrics remain positive after 5 bp/side costs.

Decision:

- `USE` only if all four tests pass;
- `CONDITION` if predictive evidence passes, or if positive IC coexists with positive 1 bp economics, but the full robustness contract does not pass;
- `REJECT` otherwise.

This decision is explicitly scoped to the **pre-launch daily-bar SessionTilt representation**. It is not the final 23/5 intervention verdict because post-2026-12-06 treatment data do not yet exist.

## Annualization

For explicitly supplied annualization factor `D`:

```text
annualized arithmetic component = mean(daily component) * D
annualized log-compound component = exp(mean(log component) * D) - 1
```

No descriptive component is interpreted as a tradable strategy without explicit costs and execution assumptions.

## Article claim audit

Article-reported numbers are targets to independently reproduce, not repository facts. A claim is `REPRODUCED` only when symbol set, dates, data convention, and estimator are sufficiently specified and the independent result matches within the published precision. Otherwise use `NOT_REPRODUCIBLE_FROM_PUBLISHED_SPEC` rather than guessing missing choices.

The U.S. 10-stock median, Japan pair-correlation, and U.S.-Japan lead-lag examples remain `NOT_REPRODUCIBLE_FROM_PUBLISHED_SPEC` unless their missing universe/provider/estimator contracts become available. MU and COST receive a separately labelled Yahoo-adjusted analog from the materialized six-symbol snapshot, but that analog does not upgrade the article claim to `REPRODUCED`.

## Evidence tests

Before predictive use, establish:

1. adjusted and raw return decomposition behave as specified;
2. log-return identity passes;
3. future observations do not change prior SessionTilt values;
4. arbitrary half-life and warm-up inputs are honored;
5. arbitrary annualization factors are honored;
6. missing required columns, symbols, partitions, or date coverage fail closed;
7. composed immutable shards are gap-free and non-overlapping;
8. the output records every runtime parameter and source manifest;
9. numerical results come from materialized evidence, not a live fetch inside analysis;
10. strict-test targets are one trading day after the feature timestamp and are never used to fit the predictive coefficients.

## Acceptance criteria for predictive use

A session feature is not accepted because it is descriptively large. Later phases compare it with simpler momentum, volatility, and session baselines under walk-forward/OOS evaluation. Any traded strategy reports after-cost return/P&L, Sharpe, maximum drawdown, beta/correlation, turnover/exposure, benchmark comparison, and tested capital scale.

## Capability delta

One generic daily-market-session implementation can evaluate different regions, symbols, horizons, adjustment modes, warm-ups, and annualization conventions without source changes. Experiment-specific choices remain explicit evidence, not hidden defaults.
