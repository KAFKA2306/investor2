# AAARTS — 投資仮説を反証可能にする研究基盤

[![Quality Gates](https://github.com/KAFKA2306/investor2/actions/workflows/quality.yml/badge.svg)](https://github.com/KAFKA2306/investor2/actions/workflows/quality.yml)
[![Validate and deploy dashboard](https://github.com/KAFKA2306/investor2/actions/workflows/pages.yml/badge.svg)](https://github.com/KAFKA2306/investor2/actions/workflows/pages.yml)
[![Verify deployed GitHub Pages](https://github.com/KAFKA2306/investor2/actions/workflows/live-pages-smoke.yml/badge.svg)](https://github.com/KAFKA2306/investor2/actions/workflows/live-pages-smoke.yml)

<!-- frontier:start -->
## Empirical frontier

**BEAT 0 / TIE 0 / LOSE 1 / BLOCKED 34**

この表は `data/research/paper_family_frontier.json` から生成します。 `BLOCKED`、CI成功、実装完了は勝利として扱いません。 論文側の代表結果とrepositoryの再現・head-to-head結果は混ぜません。

| Family | 強み | Benchmark | Paper / 代表結果 | AAARTS | Verdict | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| [AlphaZeroBeta](docs/research/alphazerobeta_validation.md) | market-neutral portfolio construction | J-Quants Free, 64 assets, 2 OOS folds | Paper exact reproduction blocked by licensed Bloomberg-dependent data. | return -5.7240%; Sharpe -2.1285; corr 0.05284; max DD -8.0761% | **LOSE** | [result](docs/research/results/alphazerobeta_jquants_free/summary.json) |
| [Adaptive BTC Multi-Agent](docs/paper/adaptive_btc_multiagent.md) | adaptive multi-agent crypto trading | contract not frozen | — | — | **BLOCKED** | — |
| [AlphaAgent](docs/paper/AlphaAgent.md) | originality / low-similarity alpha discovery | contract not frozen | — | — | **BLOCKED** | — |
| [AlphaAgentEvo](docs/paper/AlphaAgentEvo.md) | evolutionary alpha discovery | contract not frozen | — | — | **BLOCKED** | — |
| [AlphaCrafter](docs/paper/AlphaCrafter.md) | LLM-driven alpha construction | contract not frozen | — | — | **BLOCKED** | — |
| [AlphaEvolve](docs/paper/AlphaEvolve.md) | evolutionary alpha search | contract not frozen | — | — | **BLOCKED** | — |
| [AlphaForgeBench](docs/paper/AlphaForgeBench.md) | alpha-generation benchmark quality | contract not frozen | — | — | **BLOCKED** | — |
| [AlphaPROBE](docs/paper/AlphaPROBE.md) | alpha exploration / evaluation | contract not frozen | — | — | **BLOCKED** | — |
| [AlphaSchema](docs/paper/AlphaSchema.md) | structured alpha representation | contract not frozen | — | — | **BLOCKED** | — |
| [AlphaSharpe](docs/paper/AlphaSharpe.md) | risk-adjusted strategy selection | contract not frozen | — | — | **BLOCKED** | — |
| [CausalAlpha / CAMEF](docs/paper/CausalAlpha.md) | causal multimodal event forecasting | contract not frozen | — | — | **BLOCKED** | — |
| [CogAlpha](docs/paper/CogAlpha.md) | reasoning-driven alpha discovery | contract not frozen | — | — | **BLOCKED** | — |
| [Context7](docs/paper/context7.md) | live documentation grounding | contract not frozen | — | — | **BLOCKED** | — |
| [Deep Hedging](docs/paper/deephedging.md) | learned hedging under risk constraints | contract not frozen | — | — | **BLOCKED** | — |
| [EDINET-Bench](docs/paper/edinet_bench.md) | Japanese financial-document reasoning | contract not frozen | — | — | **BLOCKED** | — |
| [FactorMiner](docs/paper/FactorMiner.md) | self-evolving discovery efficiency | contract not frozen | — | — | **BLOCKED** | — |
| [FinanceHarness](docs/paper/FinanceHarness.md) | agent evaluation / reproducibility | contract not frozen | — | — | **BLOCKED** | — |
| [Financial Statement Analysis with Large Language Models](docs/paper/fsa_gpt4.md) | financial-statement earnings-direction prediction | contract not frozen | — | — | **BLOCKED** | — |
| [FinDeepForecast](docs/paper/findeepforecast.md) | deep financial forecasting | contract not frozen | — | — | **BLOCKED** | — |
| [FinGAIA](docs/paper/fingaia.md) | financial agent intelligence | contract not frozen | — | — | **BLOCKED** | — |
| [FinMCP-Bench](docs/paper/finmcp_bench.md) | financial MCP/tool-use benchmark | contract not frozen | — | — | **BLOCKED** | — |
| [FinSABER Long Run](docs/paper/finsaber_long_run.md) | long-horizon agent trading | contract not frozen | — | — | **BLOCKED** | — |
| [FinSphere](docs/paper/FinSphere.md) | SEC/EDGAR-grounded equity analysis | contract not frozen | — | — | **BLOCKED** | — |
| [MCP MAS Framework](docs/paper/mcp_mas_framework.md) | multi-agent MCP orchestration | contract not frozen | — | — | **BLOCKED** | — |
| [MCPFM](docs/paper/mcpfm.md) | financial MCP execution | contract not frozen | — | — | **BLOCKED** | — |
| [NeuroSymbolic Finance](docs/paper/neurosymbolic.md) | neuro-symbolic financial reasoning | contract not frozen | — | — | **BLOCKED** | — |
| [QuantaAlpha](docs/paper/quantaalpha.md) | evolutionary alpha mining | contract not frozen | — | — | **BLOCKED** | — |
| [QuantAgent](docs/paper/quantagent.md) | LLM/agent quantitative research | contract not frozen | — | — | **BLOCKED** | — |
| [QuantCode-Bench](docs/paper/quantcode_bench.md) | quantitative code-generation benchmark | contract not frozen | — | — | **BLOCKED** | — |
| [QuantMCP](docs/paper/quantmcp.md) | quantitative MCP/tool use | contract not frozen | — | — | **BLOCKED** | — |
| [R&D-Agent-Quant](docs/paper/rd_agent_quant.md) | autonomous quantitative research | contract not frozen | — | — | **BLOCKED** | — |
| [TiMi](docs/paper/TiMi.md) | financial reasoning / trading | contract not frozen | — | — | **BLOCKED** | — |
| [Trading-R1](docs/paper/trading_r1.md) | trading reasoning | contract not frozen | — | — | **BLOCKED** | — |
| [When Agents Trade](docs/paper/when_agents_trade.md) | multi-agent trading behavior | contract not frozen | — | — | **BLOCKED** | — |
| [World Models On-Chain](docs/paper/worldmodels_onchain.md) | on-chain world-model forecasting | contract not frozen | — | — | **BLOCKED** | — |

`LOSE` は完了した否定的比較です。`BLOCKED` は未勝利です。 次の研究対象は、まず `LOSE`、次に価値の高い `BLOCKED` を解消します。
<!-- frontier:end -->

`investor2` は、投資仮説・point-in-time evidence・OOS検証・判断記録を一つの追跡可能な流れで扱う研究repositoryです。

**バックテストの好成績だけでは採用しません。** 仮説と反証条件を先に固定し、その時点で利用可能だったデータ、比較対象、取引コスト、OOS結果、判断理由まで再実行可能な証拠として残します。

公開ダッシュボード: https://kafka2306.github.io/investor2/

## Canonical flow

```text
一次情報 / revision固定データ
  -> input ledger / snapshot
  -> hypothesis + falsifiers
  -> point-in-time dataset
  -> OOS / baseline / ablation / costs
  -> reproducible evidence
  -> Decision Snapshot
  -> 人間の投資判断
  -> Decision Review
```

正準仕様: [Canonical investment flow](docs/architecture/canonical-investment-flow.md)

## Commands

```bash
task setup               # locked dependencies + prek
task check               # canonical non-mutating quality gate
task run:newalphasearch  # frozen real-data hypothesis validation
task dashboard:dev       # local evidence dashboard
```

実行入口は `Taskfile.yml` を正準とします。別名CLIや並行pipelineは、実際の運用コストを下げる場合を除いて追加しません。

## Research rules

- future informationを混ぜない。
- 結果を見る前に仮説・比較対象・失敗条件を固定する。
- source revision / query / period / unit / hash を追跡可能にする。
- OOS、baseline、ablation、取引コストを直接検証する。
- 良い結果だけでなく、棄却された仮説も結果として保存する。
- `candidate` やDecision Snapshot eligibilityを売買推奨とみなさない。

投資戦略では、該当する場合に after-cost return/P&L、Sharpe、maximum drawdown、beta/correlation、turnover/exposure、benchmark comparison、tested capital scale を直接評価します。

## Main surfaces

| 目的 | 正準入口 |
| --- | --- |
| 研究全体を見る | [Evidence & Evolution Dashboard](https://kafka2306.github.io/investor2/) |
| 仮説探索 | [Hypothesis Lab](docs/research/hypothesis-lab.md) |
| 入力→検証→判断 | [Canonical investment flow](docs/architecture/canonical-investment-flow.md) |
| 判断時点の固定 | [Decision ledger](data/decision_ledger/README.md) |
| Alpha探索手順 | [Alpha discovery runbook](docs/specs/alpha_discovery_runbook.md) |
| OOS判定 | [Time-tested alpha policy](docs/specs/time_tested_alpha_policy.md) |
| 外部snapshot | [External snapshot store](docs/specs/external_snapshot_store.md) |
| repository運用 | [AGENTS.md](AGENTS.md) |

## EDINET-Bench

`industry_prediction` は公式test splitを持たないため、正式評価では固定manifestを使用します。

- manifest: `data/benchmarks/industry_prediction_frozen_split.json`
- source revision / Parquet SHA-256 / row countを固定
- developmentとfrozen evaluationを決定論的に分離
- source driftやmanifest不整合ではfail closed

## Positioning

このrepositoryは研究・検証基盤です。未実証のalpha性能や将来収益を主張しません。価値は、研究結果を疑い、再実行し、どの証拠からどの判断に至ったかを後から反証できる状態にあります。
