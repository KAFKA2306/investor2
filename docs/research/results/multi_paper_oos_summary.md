# Official Kenneth French current factor snapshot — 2026-06

## Authority

Current-use factor evidence is pinned from the official Kenneth R. French Data Library, retrieved on 2026-08-16 and truncated deterministically at the latest verified observation, 2026-06.

- Data Library: https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library.html
- FF3 definition: https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/f-f_factors.html
- FF3 historical archive: https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/f-f_factors_archive.html
- FF5 definition: https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/f-f_5_factors_2x3.html
- FF5 historical archive: https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/f-f_5_factors_2x3_archive.html

The Data Library states that CRSP Legacy FIZ inputs were discontinued after the December 2024 data release and that US research returns use CRSP CIZ inputs beginning with the January 2025 release. The pinned snapshot therefore records the CIZ regime explicitly and does not treat an unlabeled FIZ/CIZ mixture as reproducible evidence.

## Verified data delta

| Dataset | Previous current-use window | Previous rows | Pinned official window | Current rows | Delta |
|---|---|---:|---|---:|---:|
| FF3 SMB/HML input | 1992-07–2020-02 | 332 | 1992-07–2026-06 | 408 | +76 |
| FF5 RMW/CMA input | 2015-05–2020-02 | 58 | 2015-05–2026-06 | 134 | +76 |
| **Total factor-month records** |  | **390** |  | **542** | **+152** |

Canonical integrity is stored in `kenneth_french_current_snapshot_2026-06.json`, including the upstream ZIP SHA-256, extracted CSV SHA-256, normalized-file SHA-256, row count, and first/last observation for each factor family. The machine-readable research result is `official_current_paper_factor_suite.json`.

## Post-publication OOS result

The locked seven-study suite was rerun through 2026-06 using the pinned official snapshot. None of the seven hypotheses passes the existing confirmation gate.

| Test | Window | Months | Annual mean | Newey-West t | Verdict |
|---|---|---:|---:|---:|---|
| Banz 1981 size proxy | 1992-07–2026-06 | 408 | 0.73% | 0.44 | `proxy_not_confirmed` |
| Fama-French 1992 size proxy | 1992-07–2026-06 | 408 | 0.73% | 0.44 | `proxy_not_confirmed` |
| Fama-French 1992 value proxy | 1992-07–2026-06 | 408 | 2.13% | 0.91 | `proxy_not_confirmed` |
| Fama-French 1993 SMB | 1993-03–2026-06 | 400 | 0.57% | 0.34 | `not_confirmed` |
| Fama-French 1993 HML | 1993-03–2026-06 | 400 | 1.88% | 0.80 | `not_confirmed` |
| Fama-French 2015 RMW | 2015-05–2026-06 | 134 | 1.73% | 0.68 | `not_confirmed` |
| Fama-French 2015 CMA | 2015-05–2026-06 | 134 | -0.49% | -0.19 | `not_confirmed` |

The gate remains: Newey-West t >= 1.96, positive lower bound of the moving-block-bootstrap mean interval, positive late-half annual arithmetic mean, and positive full-window annual arithmetic mean after a mechanical 25 bps monthly haircut. The haircut is a sensitivity test, not a realized transaction-cost estimate.

## Reproduction

```bash
python scripts/verify_paper_factor_suite.py \
  --registry docs/research/frontier/paper_factor_registry.json \
  --json-output /tmp/official-current-paper-factor-suite.json
```

The `Research PIT vintage audit` workflow validates the pinned current result and separately reconstructs the July 2020 official historical vintage from archived portfolio legs. Current CIZ data and historical FIZ vintages remain explicitly labeled rather than silently combined.

## Interpretation boundary

These are factor-return persistence tests. The Banz and Fama-French 1992 rows are implementation proxies, not security-level replications of the original cross-sectional studies. Factor returns are not abnormal returns after a complete risk model. The July 2020 official historical archive audit remains a separate point-in-time vintage check.
