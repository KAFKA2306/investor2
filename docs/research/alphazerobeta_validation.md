# AlphaZeroBeta — AAARTS independent validation contract

## Decision

`AlphaZeroBeta: Deep Reinforcement Learning for Market-Neutral Portfolios` (Belyakov, arXiv:2607.18001v1) is accepted into AAARTS as a **pre-registered hypothesis**, not as an accepted alpha strategy.

The first question is narrower than “does the paper reproduce?”: **does the paper's central mechanism survive an independent, point-in-time, after-cost test on locally available data?**

## Verified source facts

The paper defines a dollar-neutral action projection (`sum(w)=0`, gross exposure `<=1`), a reward combining risk-adjusted benchmark-relative return, rolling benchmark correlation, and L1 turnover, and a CNN-GRU policy trained with Recurrent PPO. The main hyperparameters are `lambda_corr=0.5`, `lambda_turnover=0.001`, `gamma=0.99`, `GAE=0.95`, PPO clip `0.20`, learning rate `3e-4`, 10 PPO epochs, a 100-observation agent window, and a 60-business-day volatility/correlation window.

Its reported protocol uses 36 months of training, 6 months of validation, and a non-overlapping 6-month test window, advancing six months at a time and resetting network weights each fold. The paper evaluates 22 test folds spanning 2014–2024 and nine RL initializations per fold.

The paper also states that its complete code and licensed Bloomberg-dependent data cannot be redistributed. Therefore AAARTS must distinguish **independent mechanism replication** from **exact paper replication**.

The checked source boundary is materialized at `docs/research/data/alphazerobeta_arxiv_2607_18001_2026-08-22.json` so the hypothesis does not depend on chat memory.

## AAARTS implementation

Canonical hypothesis: `data/hypothesis_lab/hypotheses/alphazerobeta_market_neutral_v1.json`.

The implementation is split at the actual compute boundary:

```text
local frozen prices + benchmark
  -> scripts/alphazerobeta_prepare.py              # CPU
  -> prepared .npz + manifest                      # frozen input
  -> walk-forward contract / model construction    # CPU
  -> scripts/alphazerobeta_train.py --device cuda  # GPU-only optimization
  -> weight artifact + fold result
  -> scripts/alphazerobeta_evaluate.py             # CPU audit
  -> scripts/alphazerobeta_compare.py              # CPU confirmation gate
  -> compare lambda_corr=0.5 vs lambda_corr=0
  -> confirm / reject / remain feasibility-only
```

`src/research/alphazerobeta.py` owns the reusable projection, reward, walk-forward, model, and evaluation primitives. The code intentionally uses only dependencies already present in the repository (`numpy`, `pandas`, `torch`) rather than adding a second RL framework.

## Evidence boundary

A one-fold GPU run is **only a feasibility gate**. It proves that the local RTX-class execution path can construct, optimize, and evaluate the model without leaving the approved worker boundary. It does not confirm the hypothesis.

A confirmatory result requires at least two untouched 6-month test folds, an identical `lambda_corr=0` ablation, frozen input hashes, and the pre-registered cost sensitivity. If point-in-time constituent membership cannot be established, the result must remain explicitly caveated or feasibility-only.

`alphazerobeta_compare.py` fails closed on mismatched dates or overlapping test folds and recomputes after-cost returns from the frozen dataset and weight artifacts. A `confirm` verdict requires all pre-registered gates; fewer than two fold pairs can only produce `feasibility_only`.

## Local commands

Prepare a frozen dataset from existing local CSVs:

```bash
PYTHONPATH=. uv run python scripts/alphazerobeta_prepare.py \
  --prices-csv /path/to/prices.csv \
  --benchmark-csv /path/to/benchmark.csv \
  --universe-cutoff YYYY-MM-DD \
  --max-assets 32 \
  --output cache/alphazerobeta/jp32.npz
```

GPU fold (delegated to the bounded OpenClaw worker):

```bash
PYTHONPATH=. uv run python scripts/alphazerobeta_train.py \
  --dataset cache/alphazerobeta/jp32.npz \
  --test-start YYYY-MM-DD \
  --test-end YYYY-MM-DD \
  --fold-index 0 \
  --device cuda \
  --output docs/research/results/alphazerobeta_gpu_fold0.json
```

The required ablation uses the identical command with `--lambda-corr 0` and a separate output path.

CPU readback/audit:

```bash
PYTHONPATH=. uv run python scripts/alphazerobeta_evaluate.py \
  --dataset cache/alphazerobeta/jp32.npz \
  --weights docs/research/results/alphazerobeta_gpu_fold0.weights.npz \
  --output docs/research/results/alphazerobeta_gpu_fold0.audit.json
```

After at least two untouched primary/ablation fold pairs exist, run the locked comparison:

```bash
PYTHONPATH=. uv run python scripts/alphazerobeta_compare.py \
  --dataset cache/alphazerobeta/jp32.npz \
  --primary-weights primary_fold0.weights.npz primary_fold1.weights.npz \
  --ablation-weights ablation_fold0.weights.npz ablation_fold1.weights.npz \
  --output docs/research/results/alphazerobeta_comparison.json
```

## OpenClaw boundary

The local worker contract in `KAFKA2306/agent-resources/docs/docs/openclaw-local-worker.md` is authoritative for the GPU step. The GPU Issue must already exist; the worker receives that Issue as the task specification. It may edit and execute only inside the approved local repository root, may use CUDA, and must not create commits, push, create/switch branches, or open PRs.

Therefore the prepared `.npz` must already be inside the local `investor2` repository before dispatch. Existing market caches outside the approved OpenClaw root are not passed directly to the worker. If the prepared dataset is absent, the worker must report the blocker rather than fetching data or bypassing path/network restrictions.

No command above fetches external data. The GPU worker operates only on already-local frozen inputs.
