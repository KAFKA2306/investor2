# Issue #161 — session-state preregistration

Status: frozen before inspection of any post-23/5 U.S. exchange data.
Frozen cutoff for the complete pre-launch study: **2026-08-21**, the last completed U.S. regular session before this work started.

## Decision

Decide whether session decomposition is useful in investor2 as a point-in-time price-driver / participant-regime state variable. The final research decision is `USE`, `CONDITION`, or `REJECT`; a historical close-to-open premium is not sufficient evidence.

## Primary uncertainty

Observed overnight/intraday differences can mix at least four mechanisms: where economically relevant drivers are priced, participant/clientele pressure near session boundaries, inventory/liquidity-provider effects, and measurement artifacts from auctions, stale prints, spreads, fragmentation, corporate actions, or clock boundaries.

The 2026 U.S. move toward 23-hour exchange/SIP trading is treated as a market-structure intervention, not as proof that a clock anomaly must disappear.

## Frozen pre-launch data contract

Research code must consume materialized snapshots and must not fetch Yahoo directly inside the analysis path. The central Yahoo snapshot builder stores raw daily OHLC, `AdjClose`, volume, and corporate-action fields with `auto_adjust=False`, `actions=True`, and `repair=True`.

Primary U.S. baseline universe:

- broad/size proxies: `SPY`, `QQQ`, `IWM`, `DIA`;
- article case studies: `MU`, `COST`.

The reusable cache contract is **base + immutable calendar-year shards**:

1. **base:** `2004-01-01` through `2025-01-01` exclusive under `central/investor2/private/yahoo-market-cache/v1`;
2. **2025 shard:** `2025-01-01` through `2026-01-01` exclusive under `central/investor2/private/yahoo-market-cache/extensions/v1/2025`;
3. later completed years use the same `extensions/v1/YYYY` contract and are appended without rewriting prior bytes.

The baseline builder accepts repeated `--market-snapshot-dir` arguments, verifies that manifest intervals cover the requested window without gaps, and rejects overlapping `Ticker/Date` rows instead of choosing an implicit winner. The first reusable combined baseline therefore defaults to `2021-01-01` through `2025-12-31`.

The remaining partial-year pre-launch block `2026-01-01` through `2026-08-21` is a separate immutable cutoff snapshot. It must not be confused with a completed calendar-year shard or silently fetched live during analysis.

The annual cache remains a reusable frozen market-data input, not historical point-in-time membership evidence. Universe selection at collection time must not be interpreted as a survivorship-bias-free historical index universe.

Japan and cross-market extensions are separate evidence blocks because they require a frozen Japanese universe and calendar contract. They must not be silently substituted into the U.S. baseline.

## Corporate-action convention

For the primary daily-bar specification:

```text
AdjustmentFactor_t = AdjClose_t / Close_t
AdjustedOpen_t     = Open_t  * AdjustmentFactor_t
AdjustedClose_t    = Close_t * AdjustmentFactor_t = AdjClose_t
```

This removes split/dividend discontinuities encoded by the provider before close-to-open returns are calculated. Raw-price results may be reported only as an explicitly labelled robustness variant.

## Return definitions

For asset `i` and trading day `t`:

```text
r_ON(i,t) = AdjustedOpen(i,t) / AdjustedClose(i,t-1) - 1
r_ID(i,t) = AdjustedClose(i,t) / AdjustedOpen(i,t) - 1
r_CC(i,t) = AdjustedClose(i,t) / AdjustedClose(i,t-1) - 1
```

Log components are also retained. They must satisfy, up to floating-point tolerance:

```text
log_r_ON + log_r_ID = log_r_CC
```

Daily provider bars are a daily regular-session OHLC representation; they are not assumed to be auction-only official prices. Auction/quote-mid/VWAP variants belong to later microstructure robustness work when those inputs are materialized.

## SessionTilt primary specification

The article-motivated signed state variable is frozen as:

```text
spread(i,t) = r_ON(i,t) - r_ID(i,t)
num(i,t)    = EWMA(spread, half-life=126, adjust=False)
den(i,t)    = EWMA_STD(log_r_CC, half-life=126, adjust=False)
SessionTilt_126(i,t) = num(i,t) / den(i,t)
```

Both numerator and denominator use only data available through `t`. `min_periods=126`. Secondary `63` and `252` half-lives are sensitivity checks only and cannot replace the primary after outcomes are inspected.

The denominator above is an investor2 point-in-time operationalization. The Zenn article writes `sigma(r_CC)` without fixing its estimation window, so an exact article implementation is not claimed for that denominator.

## Annualization

Primary descriptive annualization for article-comparable signed components:

```text
annualized arithmetic component = mean(daily component) * 252
```

Sensitivity output:

```text
annualized log-compound component = exp(mean(log component) * 252) - 1
```

No compounding table is interpreted as a tradable strategy without explicit transaction costs and execution assumptions.

## Article claim audit

Article-reported numbers are targets to independently reproduce, not repository facts. A claim is `REPRODUCED` only after the required symbol set, time window, data convention, and estimator are fixed and the independent result is consistent with the published rounded value. If the article does not specify enough information to reconstruct the statistic, status is `NOT_REPRODUCIBLE_FROM_PUBLISHED_SPEC` rather than a guessed reconstruction.

The implementation does not use the article's numerical values as constants in feature computation.

## Evidence tests

Phase A must establish all of the following before post-launch analysis:

1. adjusted return decomposition passes deterministic tests, including a synthetic split discontinuity;
2. log-return decomposition identity passes;
3. changing future observations does not change earlier SessionTilt values;
4. the 126-valid-return warm-up is enforced;
5. missing `Open`, `AdjClose`, requested tickers, snapshot partitions, or requested date coverage fail closed;
6. multiple immutable snapshot shards compose only when coverage is gap-free and rows do not overlap;
7. the baseline output records exact universe, dates, half-life, annualization, and every source snapshot manifest;
8. actual results are produced from materialized snapshots rather than a live fetch inside the analysis script.

## Acceptance criteria for predictive use

A session feature is not accepted because it is descriptively large. Later phases must compare against simpler momentum/volatility/session baselines with walk-forward OOS evaluation. Any traded strategy must report after-cost return/P&L, Sharpe, maximum drawdown, beta/correlation, turnover/exposure, benchmark comparison, and tested capital scale.

## Capability delta

This work leaves one reusable session-state representation and one deterministic baseline builder that consume a base snapshot plus any number of immutable calendar-year shards. Do not create a parallel data lake, a second source registry, or a one-off notebook.
