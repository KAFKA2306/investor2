# Issue #161 — Phase A evidence outputs

The pre-launch execution produces two immutable evidence classes.

## Market input

Exact U.S. universe:

- SPY
- QQQ
- IWM
- DIA
- MU
- COST

Frozen daily-bar window: `2000-01-01..2026-08-22` exclusive.

The central authenticated publisher materializes this snapshot in the private Hugging Face Storage Bucket outside Git. `manifest.json` is the completion marker and records provider semantics, exact ticker list, source revision, storage contract, byte sizes, and SHA-256 for every object.

The analysis path must not consume the publisher's local build directory. It first performs a fresh readback from the `hf://buckets/...` cache prefix, verifies the manifest and every declared object hash, and only then runs the research code. Yahoo/yfinance is therefore a cache-fill source, not the repeated analysis input.

## Analysis outputs

The analysis path consumes only the verified HF cache readback and emits:

1. the descriptive adjusted `SessionTilt_126` baseline;
2. strict historical OOS evaluation with training through 2024-12-31 and test from 2025-01-01 through 2026-08-21;
3. 0/1/5 bp-per-side cost sensitivity;
4. direct OOS IC and MSE comparison against intercept and lagged-session-spread baselines;
5. equal-weight strategy return, Sharpe, max drawdown, beta/correlation to SPY, and turnover assumption;
6. article-claim classification and Yahoo-adjusted MU/COST analogs.

The result JSON is itself persisted to an immutable HF path keyed by the source manifest SHA-256 and the exact investor2 analysis revision. Local runner files are ephemeral and are not canonical evidence.

The pre-launch result is not the final 23/5 intervention verdict. Post-launch evidence remains `PENDING_FUTURE_DATA` until both official go-live and observed 21:00–04:00 market-data coverage are verified.
