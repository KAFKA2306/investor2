# AlphaZeroBeta paper-reproduction execution

- Mode: **public-surrogate**
- Execution: **completed**
- Exact Table-4 reproduction: **no** — licensed paper inputs are absent and exact mode fails closed.
- Architecture smoke: CNN 32/64/64, kernels 8/4/3, strides 4/2/1, GRU/head 512, 100-step window.
- Reward state: Appendix D.4.2 previous-weight rolling 60-day sigma/correlation semantics.
- PPO smoke: 10 epochs, gamma 0.99, GAE 0.95, clip 0.20, learning rate 3e-4.
- OOS: two frozen 2024 folds, one seed, Appendix-D-style 10 iterations/fold and horizon 200.
- Costs: 15 bps/side + 30 bps/year borrow for this public surrogate.

## Primary lambda_corr=0.5

- Cumulative after-cost return: -1.7573%
- Annualized Sharpe: -0.2663
- Benchmark correlation: 0.6104
- Maximum drawdown: -7.4403%

## Lambda_corr=0 ablation

- Cumulative after-cost return: 0.6824%
- Annualized Sharpe: 0.1338
- Benchmark correlation: 0.7063
- Maximum drawdown: -7.2013%

## Claim boundary

This run verifies the disclosed 512-wide architecture and Appendix-D reward-state semantics end-to-end on the 
frozen public panel. It is not a reproduction of the paper's reported Table 4 because the licensed historical 
constituent and feature data are unavailable. See `manifest.json` and `exact_paper_readiness.json`.
