---
title: AlphaZeroBeta implementation surface
status: active
---

# AlphaZeroBeta implementation surface

AlphaZeroBeta uses one fold trainer: `scripts/alphazerobeta_train.py`.

- default `--reward-semantics bounded`: prior bounded mechanism validation semantics
- `--reward-semantics paper`: Appendix D.4.2 rolling reward-state semantics with deterministic CPU execution
- `scripts/alphazerobeta_paper_reproduce.py`: exact-data readiness gate and public-surrogate orchestration only
- reproduction CI is read-only; measured evidence is verified in a temporary directory rather than committed by the workflow

The paper-data contract remains in `src/research/alphazerobeta_paper.py`; exact Table-4 reproduction still fails closed without the required licensed historical data.
