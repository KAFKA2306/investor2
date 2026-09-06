---
name: alpha-mining
description: Use for alpha-factor hypothesis implementation and PIT/OOS empirical validation.
origin: local-git-analysis
---

# Alpha Mining

Use this skill for reproducible alpha experiments.

Before untouched OOS evaluation, freeze the hypothesis mechanism, signal and lags, universe, PIT availability rules, train/validation/OOS periods, baseline and ablation, applicable costs/capacity assumptions, primary metric, rejection criterion, and allowed variants/seeds.

If any of those choices changes after results are observed, create a new protocol version.

## Validation

1. Implement the deterministic baseline.
2. Verify PIT alignment and signal calculation.
3. Run chronological untouched OOS.
4. Add post-publication, regime, or cross-market checks when the hypothesis requires them.
5. Measure the metrics defined by the frozen protocol, including costs and turnover where applicable.
6. Compare LLM-derived extraction or filters against the same frozen baseline when used.
7. Persist positive and negative verdicts with the protocol version and direct metrics.

LLM narratives or plausible mechanisms are not empirical alpha evidence.

## References

- `docs/specs/alpha_discovery_runbook.md`
- `docs/specs/time_tested_alpha_policy.md`
- `docs/architecture/canonical-investment-flow.md`
