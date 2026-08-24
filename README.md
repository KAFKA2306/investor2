# AAARTS — 投資仮説を反証可能にする研究基盤

[![Quality Gates](https://github.com/KAFKA2306/investor2/actions/workflows/quality.yml/badge.svg)](https://github.com/KAFKA2306/investor2/actions/workflows/quality.yml)
[![Validate and deploy dashboard](https://github.com/KAFKA2306/investor2/actions/workflows/pages.yml/badge.svg)](https://github.com/KAFKA2306/investor2/actions/workflows/pages.yml)
[![Verify deployed GitHub Pages](https://github.com/KAFKA2306/investor2/actions/workflows/live-pages-smoke.yml/badge.svg)](https://github.com/KAFKA2306/investor2/actions/workflows/live-pages-smoke.yml)

<!-- paper-family-frontier:start -->
## Paper-family frontier

**BEAT 0 / TIE 0 / LOSE 0 / BLOCKED 34**

全familyを同じcanonical registryから表示します。個別family専用のREADMEロジックは持ちません。直接head-to-headが未完了なら `BLOCKED` であり、CI成功や実装完了は勝利ではありません。

| Family | 強み | Benchmark | Representative | Head-to-head state | Verdict | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| [Adaptive BTC Multi-Agent Trading](docs/paper/adaptive_btc_multiagent.md) | verbal-feedback adaptive multi-agent Bitcoin trading | buy-and-hold and paper trading baselines | paper method | NOT_RUN | **BLOCKED** | [evidence](docs/paper/adaptive_btc_multiagent.md) |
| [AlphaAgent](docs/paper/AlphaAgent.md) | originality-regularized alpha discovery | untouched-OOS survivor quality under fixed compute | paper method | NOT_RUN | **BLOCKED** | [evidence](docs/paper/AlphaAgent.md) |
| [AlphaAgentEvo](docs/paper/AlphaAgentEvo.md) | self-evolving agentic reinforcement learning for alpha mining | untouched-OOS survivor quality under fixed compute | paper method | NOT_RUN | **BLOCKED** | [evidence](docs/paper/AlphaAgentEvo.md) |
| [AlphaCrafter](docs/paper/AlphaCrafter.md) | full-stack factor discovery, screening, and cross-sectional execution | paper cross-sectional backtest/live evaluation; repository head-to-head uses shared J-Quants 256 PIT contract | deterministic public-policy representative pinned to arXiv v2 / upstream commit c6dbc1b | RUNNING | **BLOCKED** | [evidence](docs/research/contracts/alphacrafter_jquants_256.json) |
| [AlphaEvolve](docs/paper/AlphaEvolve.md) | evolutionary code discovery with executable evaluation | task-native executable objective improvement under fixed evaluator | paper method | NOT_RUN | **BLOCKED** | [evidence](docs/paper/AlphaEvolve.md) |
| [AlphaForgeBench](docs/paper/AlphaForgeBench.md) | reproducible executable factor research by LLM agents | reproducible valid-strategy rate plus downstream OOS | paper benchmark | NOT_RUN | **BLOCKED** | [evidence](docs/paper/AlphaForgeBench.md) |
| [AlphaPROBE](docs/paper/AlphaPROBE.md) | principled retrieval and lineage-aware graph evolution | untouched-OOS survivor quality and compute per survivor | paper method | NOT_RUN | **BLOCKED** | [evidence](docs/paper/AlphaPROBE.md) |
| [AlphaSchema](docs/paper/AlphaSchema.md) | structured trading-semantics search | surviving untouched-OOS candidate quality | paper method | NOT_RUN | **BLOCKED** | [evidence](docs/paper/AlphaSchema.md) |
| [AlphaSharpe](docs/paper/AlphaSharpe.md) | evolved risk-adjusted metrics that select robust strategies | future-OOS quality of selected strategies | paper method | NOT_RUN | **BLOCKED** | [evidence](docs/paper/AlphaSharpe.md) |
| [CAMEF / CausalAlpha](docs/paper/causalalpha.md) | causal-augmented multimodal event-driven financial forecasting | paper-native forecasting metric on frozen split | paper method | NOT_RUN | **BLOCKED** | [evidence](docs/paper/causalalpha.md) |
| [CogAlpha](docs/paper/CogAlpha.md) | LLM-driven code-based alpha evolution | paper alpha-mining baselines | paper method | NOT_RUN | **BLOCKED** | [evidence](docs/paper/CogAlpha.md) |
| [CryptoTrade](docs/paper/cryptotrade.md) | reflective on-chain/off-chain zero-shot cryptocurrency trading | traditional trading strategies and time-series baselines | paper method | NOT_RUN | **BLOCKED** | [evidence](docs/paper/cryptotrade.md) |
| [Deep Hedging with Reinforcement Learning](docs/paper/deephedging.md) | cost-aware dynamic hedging of equity-index option exposure | no-hedge, momentum, volatility-targeting, long-SPY comparators | paper method | NOT_RUN | **BLOCKED** | [evidence](docs/paper/deephedging.md) |
| [EDINET-Bench](docs/paper/edinet_bench.md) | Japanese filing NLP benchmark for fraud, earnings forecast, and industry prediction | Fraud Detection, Earnings Forecast, Industry Prediction | paper benchmark | NOT_RUN | **BLOCKED** | [evidence](docs/paper/edinet_bench.md) |
| [FactorMiner](docs/paper/FactorMiner.md) | symbolic failure memory and self-evolving alpha discovery | untouched-OOS survivor quality and compute per survivor | paper method | NOT_RUN | **BLOCKED** | [evidence](docs/paper/FactorMiner.md) |
| [FinanceHarness](docs/paper/FinanceHarness.md) | finance-specific PIT research harness separated from the model | native rubric score with PIT/provenance hard gates | paper benchmark | NOT_RUN | **BLOCKED** | [evidence](docs/paper/FinanceHarness.md) |
| [Financial Statement Analysis with Large Language Models](docs/paper/fsa_gpt4.md) | LLM forecasting from anonymized financial statements | paper-native earnings-direction accuracy/F1 on frozen split | paper GPT-4 protocol | NOT_RUN | **BLOCKED** | [evidence](docs/paper/fsa_gpt4.md) |
| [FinDeepForecast](docs/paper/findeepforecast.md) | live evaluation of unresolved financial forecasts | paper-native live forecasting metric | paper protocol | NOT_RUN | **BLOCKED** | [evidence](docs/paper/findeepforecast.md) |
| [FinGAIA](docs/paper/fingaia.md) | end-to-end real-world financial agent benchmark | FinGAIA task suite | paper benchmark | NOT_RUN | **BLOCKED** | [evidence](docs/paper/fingaia.md) |
| [FinMCP-Bench](docs/paper/finmcp_bench.md) | MCP-based real-world financial tool-use benchmark | FinMCP-Bench | paper benchmark | NOT_RUN | **BLOCKED** | [evidence](docs/paper/finmcp_bench.md) |
| [FINSABER](docs/paper/finsaber_long_run.md) | long-horizon multi-regime evaluation of LLM trading | long-horizon after-cost OOS performance plus regime diagnostics | paper benchmark | NOT_RUN | **BLOCKED** | [evidence](docs/paper/finsaber_long_run.md) |
| [FinSphere](docs/paper/FinSphere.md) | EDGAR-grounded autonomous financial analysis | paper-native financial analysis benchmark | paper method | NOT_RUN | **BLOCKED** | [evidence](docs/paper/FinSphere.md) |
| [LongFinanceQA](docs/paper/longfinanceqa.md) | supervised chain-of-thought for long-context financial document understanding | paper long-context understanding baselines | paper method | NOT_RUN | **BLOCKED** | [evidence](docs/paper/longfinanceqa.md) |
| [MCP Multi-Agent Systems Framework](docs/paper/mcp_mas_framework.md) | standardized context sharing and coordination for multi-agent systems | paper multi-agent evaluation methodology | paper method | NOT_RUN | **BLOCKED** | [evidence](docs/paper/mcp_mas_framework.md) |
| [MCPFM](docs/paper/mcpfm.md) | multi-scale network systemic-risk early warning with MCP-mediated agents | traditional systemic-risk measures | paper method | NOT_RUN | **BLOCKED** | [evidence](docs/paper/mcpfm.md) |
| [QuantaAlpha](docs/paper/quantaalpha.md) | multi-agent trajectory recombination for alpha evolution | untouched-OOS survivor quality under fixed compute | paper method | NOT_RUN | **BLOCKED** | [evidence](docs/paper/quantaalpha.md) |
| [QuantAgent](docs/paper/quantagent.md) | price-driven multi-agent LLM high-frequency trading | paper neural and rule-based HFT baselines | paper method | NOT_RUN | **BLOCKED** | [evidence](docs/paper/quantagent.md) |
| [QuantCode-Bench](docs/paper/quantcode_bench.md) | executable semantic evaluation of generated trading code | executable and semantic pass rate | paper benchmark | NOT_RUN | **BLOCKED** | [evidence](docs/paper/quantcode_bench.md) |
| [QuantMCP](docs/paper/quantmcp.md) | verifiable financial data/tool grounding through MCP | paper tool-grounding baseline | paper method | NOT_RUN | **BLOCKED** | [evidence](docs/paper/quantmcp.md) |
| [R&D-Agent-Quant](docs/paper/rd_agent_quant.md) | joint factor/model co-optimization in automated quantitative R&D | classical factor libraries and deep time-series models | paper method | NOT_RUN | **BLOCKED** | [evidence](docs/paper/rd_agent_quant.md) |
| [TiMi](docs/paper/TiMi.md) | minute-level strategy development and deployment separation | after-cost risk-adjusted return with execution/risk gates | paper method | NOT_RUN | **BLOCKED** | [evidence](docs/paper/TiMi.md) |
| [To Trade or Not to Trade](docs/paper/to_trade_or_not_to_trade.md) | agentic stochastic-model discovery for market-risk-informed trading | standard LLM-based trading agents | paper method | NOT_RUN | **BLOCKED** | [evidence](docs/paper/to_trade_or_not_to_trade.md) |
| [Trading-R1](docs/paper/trading_r1.md) | reinforcement-learned financial reasoning for risk-sensitive trading | open/proprietary instruction-following and reasoning models | paper method | NOT_RUN | **BLOCKED** | [evidence](docs/paper/trading_r1.md) |
| [When Agents Trade](docs/paper/when_agents_trade.md) | live multi-market benchmark for LLM trading agents | Agent Market Arena agent frameworks | paper benchmark | NOT_RUN | **BLOCKED** | [evidence](docs/paper/when_agents_trade.md) |

<!-- paper-family-frontier:end -->


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
