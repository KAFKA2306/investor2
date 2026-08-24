# Issue #161 — session-state research protocol

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

Research code consumes materialized immutable snapshots and does not fetch a provider inside the analysis path. Snapshot provider, region, date coverage, storage prefix, and provenance come from the snapshot manifest rather than from assumptions in the session-state code.

Repeated `--market-snapshot-dir` inputs may compose multiple immutable shards. Requested coverage must be gap-free; duplicate `Ticker/Date` rows fail closed rather than selecting an implicit winner.

A cache collected from one region or provider must not be silently substituted for another. Historical point-in-time index membership must not be inferred from a present-day collected universe.

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

## Annualization

For explicitly supplied annualization factor `D`:

```text
annualized arithmetic component = mean(daily component) * D
annualized log-compound component = exp(mean(log component) * D) - 1
```

No descriptive component is interpreted as a tradable strategy without explicit costs and execution assumptions.

## Article claim audit

Article-reported numbers are targets to independently reproduce, not repository facts. A claim is `REPRODUCED` only when symbol set, dates, data convention, and estimator are sufficiently specified and the independent result matches within the published precision. Otherwise use `NOT_REPRODUCIBLE_FROM_PUBLISHED_SPEC` rather than guessing missing choices.

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
9. numerical results come from materialized evidence, not a live fetch inside analysis.

## Acceptance criteria for predictive use

A session feature is not accepted because it is descriptively large. Later phases compare it with simpler momentum, volatility, and session baselines under walk-forward OOS evaluation. Any traded strategy reports after-cost return/P&L, Sharpe, maximum drawdown, beta/correlation, turnover/exposure, benchmark comparison, and tested capital scale.

## Capability delta

One generic session-state implementation can evaluate different regions, symbols, horizons, adjustment modes, warm-ups, and annualization conventions without source changes. Experiment-specific choices remain explicit evidence, not hidden defaults.
