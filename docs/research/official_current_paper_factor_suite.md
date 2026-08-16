# Multi-paper post-publication OOS factor suite

This suite adds four classic papers and seven paper–factor hypotheses to the
existing Jegadeesh–Titman momentum test. Proxy rows are not exact
security-level replications and are never treated as independent factor evidence.

## Results

| Test | Window | Months | Annual mean | Sharpe | CAGR | Max drawdown | NW t | 95% block CI | Late-half mean | Verdict |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| banz_1981_size_late_oos_proxy | 1992-07–2026-06 | 408 | 0.73% | 0.07 | 0.16% | -41.28% | 0.44 | -2.74% to 3.91% | -0.64% | `proxy_not_confirmed` |
| fama_french_1992_size_proxy | 1992-07–2026-06 | 408 | 0.73% | 0.07 | 0.16% | -41.28% | 0.44 | -2.74% to 3.91% | -0.64% | `proxy_not_confirmed` |
| fama_french_1992_value_proxy | 1992-07–2026-06 | 408 | 2.13% | 0.19 | 1.50% | -57.79% | 0.91 | -2.84% to 6.67% | 0.08% | `proxy_not_confirmed` |
| fama_french_1993_smb | 1993-03–2026-06 | 400 | 0.57% | 0.05 | -0.01% | -41.28% | 0.34 | -2.90% to 3.77% | -0.58% | `not_confirmed` |
| fama_french_1993_hml | 1993-03–2026-06 | 400 | 1.88% | 0.17 | 1.25% | -57.79% | 0.80 | -3.10% to 6.44% | -0.48% | `not_confirmed` |
| fama_french_2015_rmw | 2015-05–2026-06 | 134 | 1.73% | 0.21 | 1.42% | -26.15% | 0.68 | -1.30% to 7.95% | 1.98% | `not_confirmed` |
| fama_french_2015_cma | 2015-05–2026-06 | 134 | -0.49% | -0.06 | -0.83% | -27.21% | -0.19 | -5.35% to 5.43% | 2.15% | `not_confirmed` |

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
