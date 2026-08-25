# Issue #222 — Alpha-discovery landscape

調査日: 2026-08-26

## 結論

alpha-discovery frontier を 1 本の論文で組織しない。

`docs/research/paper_family_frontier.json` の `alpha_discovery` 9 family と、直近に調査した AgonAlpha を同一面へ並べると、競争軸は paper 名ではなく主に次の 6 mechanism group に分かれる。

1. originality / semantic control
2. memory / lineage reuse
3. executable artifacts / verification
4. evolution / recombination
5. learned or adaptive search policy
6. joint factor-model search

AgonAlpha は現時点で Issue #194 canonical registry に未登録であり、`REGISTRY_GAP` として扱う。直近に深く調査したことを理由に frontier authority へ昇格させない。

## Family landscape

| Family | 主な探索単位 | 主 mechanism | current investor2 state |
|---|---|---|---|
| AlphaAgent | formula / hypothesis-factor | AST originality, alignment, complexity control | BLOCKED |
| AlphaAgentEvo | multi-turn trajectory | hierarchical reward, self-evolving policy | BLOCKED |
| AlphaForgeBench | executable strategy artifact | reasoning/execution separation, deterministic replay | BLOCKED |
| AlphaPROBE | factor node in DAG | principled retrieval, lineage DAG, biased evolution | BLOCKED |
| AlphaSchema | trading-semantic schema | semantic space, surrogate-guided allocation | BLOCKED |
| CogAlpha | program/code alpha | code-based evolution | BLOCKED |
| FactorMiner | factor + retrieved experience | symbolic failure memory, skill modules | BLOCKED |
| QuantaAlpha | mining trajectory | mutation/crossover, semantic consistency | BLOCKED |
| R&D-Agent-Quant | factor/model experiment | factor-model co-optimization, bandit scheduler | BLOCKED |
| AgonAlpha | evidence-bearing artifact | artifact lineage, re-execution verifier, adaptive allocation | BLOCKED / registry gap |

`BLOCKED` here means direct investor2 matched head-to-head is not complete. Paper-native OOS or external-platform results are provenance, not a substitute for the shared experiment.

## Mechanism-first ablation order

### Priority 1 — originality + semantic control

Compare:

- AAARTS baseline
- baseline + AST originality gate
- baseline + semantic-schema gate

Question: duplicate reduction itselfではなく、同じ evaluator-call budget で **unique untouched-OOS survivor が増えるか**。

Relevant families: AlphaAgent, AlphaSchema, QuantaAlpha.

### Priority 2 — memory + lineage reuse

Compare:

- baseline
- baseline + failure memory
- baseline + principled lineage retrieval

Question: 過去を覚えることで context を増やすだけではなく、**同じ失敗・重複の再試行を減らし、survivor 1件あたり evaluator calls を下げられるか**。

Relevant families: FactorMiner, AlphaPROBE, AgonAlpha.

### Priority 3 — executable evidence + independent verifier

市場成績の前に seeded fault test を行う。

- fabricated metric
- result / expression mismatch
- PIT leakage
- missing raw evidence

Question: fresh-context verifier + re-execution/veto が baseline verification より高い precision / recall で異常を検出できるか。

Relevant families: AlphaForgeBench, AgonAlpha.

### Priority 4 — evolution + recombination

Compare fresh independent generation against code/trajectory/graph evolution under the exact same evaluator-call budget.

Relevant families: CogAlpha, QuantaAlpha, AlphaPROBE.

### Priority 5 — learned policy + factor-model co-optimization

AlphaAgentEvo の RL、R&D-Agent-Quant の factor-model joint optimization、各種 adaptive allocator は compute と confound が大きい。

先に単純な mechanism で frontier gap が確認された後に試す。

## Frozen comparison outputs

Primary:

- untouched-OOS surviving candidates per fixed evaluator-call budget

Secondary:

- median selected-candidate after-cost OOS Sharpe
- best selected-candidate after-cost OOS Sharpe
- duplicate / invalid / leakage rejection rate
- evaluator calls per surviving OOS candidate
- wall-clock per surviving OOS candidate

## Source authority

- canonical family identity: `docs/research/paper_family_frontier.json`
- machine-readable landscape: `alpha_discovery_landscape.json`
- visual landscape: `alpha_discovery_landscape.svg`
- AgonAlpha audit: `../issue194/agonalpha_external_frontier_summary.json`

Primary papers:

- AlphaAgent: https://arxiv.org/abs/2502.16789
- AlphaAgentEvo: https://iclr.cc/virtual/2026/poster/10007685
- AlphaForgeBench: https://arxiv.org/abs/2602.18481
- AlphaPROBE: https://arxiv.org/abs/2602.11917
- AlphaSchema: https://arxiv.org/abs/2607.26642
- CogAlpha: https://arxiv.org/abs/2511.18850
- FactorMiner: https://arxiv.org/abs/2602.14670
- QuantaAlpha: https://arxiv.org/abs/2602.07085
- R&D-Agent-Quant: https://arxiv.org/abs/2505.15155
- AgonAlpha: https://arxiv.org/abs/2608.11250

## Next falsifiable action

Do not implement a full paper stack.

Freeze one small alpha-discovery experiment and run Priority 1 first: `baseline vs AST originality vs semantic-schema control`, with identical generator/evaluator-call budget and one untouched-OOS holdout. Persist all generated candidates, duplicate decisions, rejection reasons, evaluator calls and OOS survivors.
