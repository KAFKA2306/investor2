---
name: alpha-mining
description: Use only when implementing or evaluating an alpha hypothesis under investor2's preregistered PIT/OOS contract.
origin: local-git-analysis
---

# Alpha Mining

Follow the canonical alpha runbook rather than duplicating its full procedure here.

Before reading untouched OOS results, freeze the source/mechanism, signal and lags, universe and PIT rules, chronological splits, baseline/ablation plan, applicable cost assumptions, primary metric/rejection criterion, and allowed variants/seeds. If any of those choices changes after results are observed, create a new protocol version.

Validate provenance and PIT integrity before the signal result. Use untouched chronological OOS for the verdict, then apply the robustness/cost checks required by the canonical policy. Persist both positive and negative results as reproducible evidence.

LLMs may assist extraction, normalization, code generation, and hypothesis extension, but an LLM narrative or plausible mechanism is not alpha evidence and must not replace the frozen empirical contract.

## References

- `docs/specs/alpha_discovery_runbook.md`
- `docs/specs/time_tested_alpha_policy.md`
- `docs/architecture/canonical-investment-flow.md`
- `.agent/skills/cache/SKILL.md`
- `AGENTS.md`
