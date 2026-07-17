# Post-publication OOS verification: momentum

## Question

Does a well-known pre-LLM stock-return signal still survive after it became public?

This document applies a fixed, untuned post-publication test to the momentum strategy documented by Narasimhan Jegadeesh and Sheridan Titman in March 1993.

Primary paper:

- Jegadeesh, N. and Titman, S. (1993), *Returns to Buying Winners and Selling Losers: Implications for Stock Market Efficiency*. https://doi.org/10.1111/j.1540-6261.1993.tb04702.x

Factor definition:

- Kenneth R. French Data Library, Monthly Momentum Factor. https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/det_mom_factor.html
- The factor is the average return of the two high prior-return portfolios minus the average return of the two low prior-return portfolios. The official definition uses prior 2–12 month returns.

## Locked protocol

No parameter search was performed.

- Publication month: March 1993.
- OOS start: January 1994, excluding the partial publication year.
- OOS end in the frozen snapshot: December 2017.
- Full OOS: 1994–2017.
- Stability split fixed at the midpoint:
  - early holdout: 1994–2005;
  - late holdout: 2006–2017.
- Returns are monthly long-short factor returns.
- Statistical checks:
  - IID t-statistic;
  - Newey-West t-statistic with six lags;
  - 20,000-repetition moving-block bootstrap with 12-month blocks.
- Cost sensitivity is a mechanical monthly haircut, not an estimate of realized trading costs.

## Results

| Period | Months | Annual mean | Annual volatility | Sharpe | CAGR | Max drawdown | Newey-West t |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1994–2017 | 288 | 4.94% | 17.32% | 0.29 | 3.40% | -57.42% | 1.33 |
| 1994–2005 | 144 | 10.11% | 18.29% | 0.55 | 8.74% | -31.31% | 2.29 |
| 2006–2017 | 144 | -0.23% | 16.22% | -0.01 | -1.68% | -57.42% | -0.04 |

The 95% moving-block bootstrap interval for the full-period annualized arithmetic mean is **-3.00% to 12.01%**. It contains zero.

### Monthly cost sensitivity, full OOS

| Monthly haircut | Annual mean | CAGR | Sharpe |
|---:|---:|---:|---:|
| 0 bps | 4.94% | 3.40% | 0.29 |
| 10 bps | 3.74% | 2.17% | 0.22 |
| 25 bps | 1.94% | 0.35% | 0.11 |
| 50 bps | -1.06% | -2.63% | -0.06 |

## Verdict

**Not confirmed as a robust persistent edge in this frozen post-publication sample.**

The early holdout is positive, but the later 2006–2017 holdout has a slightly negative mean and a -57.42% maximum drawdown. The full-period mean is not statistically distinguishable from zero under the specified Newey-West and block-bootstrap checks.

This is the intended behavior of the research gate: an old and economically plausible signal is not accepted merely because it survived in an earlier subperiod.

## Reproduction

```bash
python scripts/verify_post_publication_momentum.py \
  --input docs/research/data/ff_momentum_1994_2017.csv \
  --output docs/research/post_publication_momentum_oos.json

python -m pytest -q tests/test_post_publication_momentum.py
```

The machine-readable output is committed at `docs/research/post_publication_momentum_oos.json`.

## Data provenance

The frozen input contains the January 1994–December 2017 rows extracted from:

- Repository snapshot: https://github.com/lukaskoerber/Replication-Shrinking-the-Cross-Section/blob/main/Data/F-F_Momentum_Factor.csv
- Source Git blob SHA: `1541a5e303f7d1fdd76247c6a02a8a62130276c7`
- Repository Git blob SHA: `4a8f6bb198d088689db4c94b39db6fa04b7b912c`

The primary factor definition is the Kenneth French Data Library. The current official data library extends beyond this frozen snapshot, so this report must not be represented as a through-2026 result.

## Limitations

- This is a U.S. momentum-factor verification, not an EDINET/J-Quants production strategy.
- The factor series is a constructed long-short portfolio and does not include strategy-specific borrow, market-impact, tax, or execution costs.
- It is a post-publication OOS test, but not a security-level reconstruction from raw point-in-time CRSP records.
- The frozen data ends in December 2017. A production decision requires an independently frozen and audited newer sample.
