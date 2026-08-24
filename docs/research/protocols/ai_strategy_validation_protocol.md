# AI Strategy Validation Protocol

## Purpose

This protocol governs AI-assisted discovery and validation of trading rules in
`KAFKA2306/investor2`. The objective is not to maximize the best historical
Sharpe ratio. The objective is to prevent false promotion caused by data
snooping, time leakage, stale universes, non-tradable securities, and incomplete
cost models.

A result is promoted only when every material gate is supported by a committed,
machine-readable artifact. Missing evidence fails closed.

## Claim states

| State | Meaning |
|---|---|
| `CONFIRMED` | Every locked statistical, temporal, universe, execution, and cost gate passed. |
| `NOT_CONFIRMED` | A required gate failed or the evidence is insufficient for promotion. |
| `UNVERIFIED` | The claim is external or lacks the original data/code/result artifact. |
| `NOT_RUN` | The gate is defined but has not been executed. |

`NOT_CONFIRMED` does not mean that the opposite proposition is universally true.
`UNVERIFIED` is not converted to `FAIL` without a reproduction.

## Locked research flow

1. **Register the hypothesis before final testing.** Record the economic
   mechanism, signal timestamp, holding period, direction, universe, parameter
   grid, and all variants that will be tried.
2. **Freeze the complete search family.** Trial count includes failed,
   discarded, AI-generated, and manually adjusted variants. Deleting weak trials
   from the ledger is prohibited.
3. **Separate selection and test time.** The final test period must be later
   than all training, prompt iteration, parameter selection, and debugging
   periods. Boundaries cannot move after the results are seen.
4. **Use point-in-time market data.** Constituents, listings, delistings,
   corporate actions, price limits, and security classifications are evaluated
   as known at the signal date.
5. **Apply eligibility before calculating returns.** Long and short legs include
   only securities executable at the signal date. A short trade additionally
   requires date-indexed shortability, borrow availability, and borrow cost.
6. **Adjust for multiple testing.** New return predictors use a research hurdle
   of Newey–West `t >= 3.0`. A family of technical rules also requires a
   family-wise data-snooping test such as White's Reality Check or Hansen's SPA.
7. **Preserve serial dependence.** Confidence intervals use a moving-block
   bootstrap. The current factor suite uses 12-month blocks and 20,000
   repetitions.
8. **Require temporal stability.** The late part of the frozen OOS period must
   retain a positive mean. A positive full-period average cannot hide a negative
   late regime.
9. **Charge implementation costs.** The early screen applies a mechanical
   25-basis-point monthly haircut. Promotion additionally requires
   strategy-specific turnover, spread, market-impact, tax, and borrow-cost
   estimates.
10. **Publish negative artifacts.** Failed and unverified claims remain in the
    evidence registry to prevent repeated rediscovery.

## Current repository evidence

The public dashboard regenerates its manifest from:

- `docs/research/post_publication_momentum_oos.json`
- `docs/research/paper_factor_registry.json`
- `scripts/verify_paper_factor_suite.py`
- `docs/research/2010s_paper_validation_repeated.json`

The current manifest contains eight hypotheses: one momentum test and seven
paper–factor tests. None is promoted. The latest factor data ends in February
2020, and the momentum result ends in December 2017. These results therefore do
not constitute a through-July-2026 test of Tokyo Stock Exchange chart patterns.

The X discussion about twenty years of TSE data and the short-side false
positive is stored as `UNVERIFIED`. The original point-in-time universe, exact
rules, complete trial ledger, shortability history, trades, and frozen OOS
artifact are not present in this repository.

## Method sources

- Sullivan, Timmermann, and White, “Data-Snooping, Technical Trading Rule
  Performance, and the Bootstrap,” *The Journal of Finance* 54(5), 1999.
  DOI: `10.1111/0022-1082.00163`.
- Harvey, Liu, and Zhu, “… and the Cross-Section of Expected Returns,”
  *The Review of Financial Studies* 29(1), 2016. DOI:
  `10.1093/rfs/hhv059`.
- Hansen, “A Test for Superior Predictive Ability,” *Journal of Business &
  Economic Statistics* 23(4), 2005. DOI:
  `10.1198/073500105000000063`.
- Bailey, Borwein, López de Prado, and Zhu, “The Probability of Backtest
  Overfitting,” *The Journal of Computational Finance*. DOI:
  `10.21314/JCF.2016.322`.
- Japan Exchange Group, “Short Selling Restrictions,” for current TSE
  short-sale classification and price-restriction rules.
