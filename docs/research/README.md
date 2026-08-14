# Research evidence

This directory stores reproducible empirical evidence and explicit non-reproduction states for research papers tracked by `investor2`.

## Warin arXiv:2101.02044 v4

Primary source:

- https://arxiv.org/abs/2101.02044v4
- https://arxiv.org/pdf/2101.02044v4

Canonical machine-readable scope is `warin_2101_02044_v4_experiment_matrix.json`.

The current evidence is intentionally **partial**, not a paper-wide reproduction:

- Section 3.2 Table 1, dimension 4, direct point-by-point formulation:
  - beta=0.05: `FAILED`
  - beta=0.2: `FAILED`
  - beta=2.0: `REPRODUCED`
- Section 4.3.1 selected constrained comparison, Tables 9-10, dimension 4, beta=0.959, Models 1 and 4: `REPRODUCED`
- Tables 11-14 and other sufficiently specified dimension-4 families remain `NOT_RUN` until separately executed.
- Higher-dimensional cases whose exact random correlation/parameter realization is not published remain `BLOCKED`; they are not recreated with invented parameters and labeled exact reproductions.

Table 9/10 evidence is stored under `runs/warin_2101_02044_v4_table9_beta0959_seed2306/`. Every generated report, training trace, and model state is SHA-256 bound within its own evidence bundle. CI re-executes the four predeclared seeds for each selected model and verifies the seed-level pass/fail and constraint-regime distribution, selected restart, selected numerical outcome, runtime/training contract, artifact structure, and model-level empirical verdict.

The trained parameter arrays and intermediate optimization metrics are retained as immutable evidence for each individual run, but cross-run equality is not used as the reproduction criterion. Hosted CPU executions can reach different local parameter states for the same predeclared seed while preserving the seed-level verdict distribution and selected scientific outcome. CI therefore requires exact per-bundle hash integrity and evidence structure, then evaluates cross-run reproduction at the predeclared scientific outcome boundary rather than asserting bitwise-identical optimizer trajectories.
