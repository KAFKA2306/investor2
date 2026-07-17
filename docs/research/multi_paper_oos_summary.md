# Multi-paper post-publication OOS factor suite

This suite adds four classic papers and seven paper–factor hypotheses to the
existing Jegadeesh–Titman momentum test. Proxy rows are not exact
security-level replications and are never treated as independent factor evidence.

## Results

| Test | Window | Months | Annual mean | Sharpe | CAGR | Max drawdown | NW t | 95% block CI | Late-half mean | Verdict |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| banz_1981_size_late_oos_proxy | 1992-07–2020-02 | 332 | 1.44% | 0.13 | 0.85% | -40.76% | 0.80 | -2.20% to 5.07% | -0.30% | `proxy_not_confirmed` |
| fama_french_1992_size_proxy | 1992-07–2020-02 | 332 | 1.44% | 0.13 | 0.85% | -40.76% | 0.80 | -2.20% to 5.07% | -0.30% | `proxy_not_confirmed` |
| fama_french_1992_value_proxy | 1992-07–2020-02 | 332 | 1.41% | 0.13 | 0.87% | -43.45% | 0.60 | -2.87% to 6.78% | -3.12% | `proxy_not_confirmed` |
| fama_french_1993_smb | 1993-03–2020-02 | 324 | 1.26% | 0.11 | 0.66% | -40.76% | 0.69 | -2.34% to 4.93% | 0.18% | `not_confirmed` |
| fama_french_1993_hml | 1993-03–2020-02 | 324 | 1.10% | 0.10 | 0.55% | -43.45% | 0.47 | -3.27% to 6.46% | -3.54% | `not_confirmed` |
| fama_french_2015_rmw | 2015-05–2020-02 | 58 | 1.90% | 0.40 | 1.80% | -4.98% | 1.16 | 0.15% to 4.66% | 1.82% | `not_confirmed` |
| fama_french_2015_cma | 2015-05–2020-02 | 58 | -2.79% | -0.48 | -2.91% | -16.51% | -1.21 | -6.13% to 2.29% | -3.77% | `not_confirmed` |

## Interpretation

- None of the seven new hypotheses passes the locked confirmation gate.
- SMB and HML have weak full-window means and fail the 25 bps monthly-haircut stress test.
- HML's late-half mean is negative in both its 1992 proxy and 1993 factor tests.
- RMW is positive in the short 2015–2020 window and its block-bootstrap lower bound is positive, but its Newey–West t-statistic is below 1.96 and the 25 bps monthly-haircut stress test is negative.
- CMA is negative in both the full and late windows.
- These results are factor-return tests. They do not reproduce the original papers' security-level cross-sectional regressions.

## Reproduction

```bash
python scripts/verify_paper_factor_suite.py \
  --registry docs/research/paper_factor_registry.json \
  --json-output docs/research/multi_paper_oos_results.json \
  --markdown-output docs/research/multi_paper_oos_summary.md

python -m pytest -q tests/test_paper_factor_suite.py
```

The source mirrors are frozen by commit, blob SHA, and normalized-file SHA-256.
The official Kenneth French pages remain the authority for factor definitions.

## Limitations

- The mirror snapshot ends in February 2020; this is not a through-2026 result.
- Banz (1981) is tested only through a delayed SMB proxy window beginning in July 1992.
- The Fama–French (1992) rows use SMB and HML as implementation proxies, not exact replications.
- Factor returns are not abnormal returns and may compensate systematic risk.
- The mechanical monthly haircut is not a strategy-specific transaction-cost model.
