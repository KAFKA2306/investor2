# AlphaZeroBeta empirical validation — 2024 OOS

- Verdict: **reject**
- Fold count: 2
- Scope: bounded fixed-universe independent mechanism validation; not exact paper reproduction and not a live-trading promise.
- Primary costs: 15 bps per side + 100 bps/year borrow.
- Timing: features/decision at `t` are evaluated only against realized return at `t+1`.

## Primary `lambda_corr=0.5`

- Cumulative after-cost return: -1.8897%
- Annualized Sharpe: -0.3130
- Benchmark correlation: -0.1970
- Maximum drawdown: -5.8761%
- JPY 1,000,000 -> JPY 981,103 (P/L JPY -18,897)
- JPY 10,000,000 -> JPY 9,811,033 (P/L JPY -188,967)

## Ablation `lambda_corr=0`

- Cumulative after-cost return: -1.8187%
- Annualized Sharpe: -0.2782
- Benchmark correlation: -0.2264
- Maximum drawdown: -6.3678%
- JPY 1,000,000 -> JPY 981,813 (P/L JPY -18,187)
- JPY 10,000,000 -> JPY 9,818,125 (P/L JPY -181,875)

## Gates

```json
{
  "absolute_correlation_lt_lambda_corr_zero": true,
  "absolute_correlation_lte_0_15": false,
  "dollar_neutrality": true,
  "minimum_confirmatory_folds": true,
  "sharpe_gt_lambda_corr_zero": false
}
```
