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

- Cumulative after-cost return: -1.7713%
- Annualized Sharpe: -0.2666
- Benchmark correlation: 0.6083
- Maximum drawdown: -7.5389%

## Lambda_corr=0 ablation

- Cumulative after-cost return: 0.4186%
- Annualized Sharpe: 0.0962
- Benchmark correlation: 0.6926
- Maximum drawdown: -7.1397%

## Claim boundary

This run verifies the disclosed 512-wide architecture and Appendix-D reward-state semantics end-to-end on the 
frozen public panel. It is not a reproduction of the paper's reported Table 4 because the licensed historical 
constituent and feature data are unavailable. See `manifest.json` and `exact_paper_readiness.json`.
