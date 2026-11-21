---
title: AlphaZeroBeta paper reproduction
status: executing
paper: arXiv:2607.18001v1
issue: 154
---

# AlphaZeroBeta paper reproduction

This workline is separate from the earlier bounded 8-ETF mechanism validation. Its purpose is to reproduce the implementation disclosed in Appendix D and then reproduce the reported paper experiment only when the required data contract is actually available.

## Disclosed implementation locked here

- decision at close `t` earns realized return at `t+1`
- action mean-centering followed by an L1 gross-exposure cap of 1
- reward `(rp-rm)/sigma_p - 0.5*corr(rp,rm) - 0.001*turnover`
- 60-business-day volatility/correlation window
- 100-step daily/weekly/monthly observation channels
- Conv1d 32/64/64, kernels 8/4/3, strides 4/2/1
- GRU hidden size 512
- policy/value heads with 512 hidden units; Tanh policy output
- PPO gamma 0.99, GAE 0.95, clip 0.20, Adam 3e-4, entropy coefficient 0.01, value coefficient 0.5, 10 PPO epochs
- 36-month train, 6-month validation, non-overlapping 6-month OOS test
- 22 OOS folds from January 2014 through December 2024
- nine independent RL initializations per fold for reported dispersion
- U.S. large-cap execution costs: 5 bps/side for the monthly trailing-60-day ADV top decile, otherwise 15 bps/side; borrow 30 bps/year

## Exact-result reproduction boundary

The paper states that its complete production code and vendor integrations cannot be redistributed and that exact replication needs high-quality historical prices, volumes, corporate actions, macro variables, historical index membership and licensed Bloomberg/vendor feature blocks. The repo therefore fails closed for `exact-paper` mode when that contract is absent.

A public-data run is allowed only as an execution check and is labeled `public-surrogate`; it cannot be used to claim that Table 4 was reproduced.

## Current public execution

The public execution intentionally reuses the previously frozen Yahoo 8-ETF panel so the model/code change can be isolated. It upgrades the execution smoke to the disclosed 512-wide architecture and Appendix-D-style 10-iteration/200-step training loop, evaluates two untouched 2024 folds, and runs the `lambda_corr=0` ablation under otherwise identical settings.

The generated evidence is stored under `docs/research/results/alphazerobeta_paper_reproduction/`. Exact deviations are machine-readable in `manifest.json`; exact-data blockers are machine-readable in `exact_paper_readiness.json`.
