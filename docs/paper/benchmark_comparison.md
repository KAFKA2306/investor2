# Paper-family frontier

この表は `docs/research/paper_family_frontier.json` から生成する比較surfaceです。論文記載値とrepository実測値を混ぜず、直接head-to-headが完了するまで優越を主張しません。

**Global superiority:** UNPROVEN — 0/34 families are BEAT; 34 remain unresolved.

| Family | Claimed strength | Representative | Reproduction state | AAARTS head-to-head | Primary metric | Verdict | Evidence |
|---|---|---|---|---|---|---|---|
| Adaptive BTC Multi-Agent Trading | verbal-feedback adaptive multi-agent Bitcoin trading | paper method | CONTRACT_NOT_FROZEN | NOT_RUN | after-cost OOS Sharpe with drawdown/exposure gates | BLOCKED | [adaptive_btc_multiagent.md](./adaptive_btc_multiagent.md) |
| AlphaAgent | originality-regularized alpha discovery | paper method | NOT_RUN | NOT_RUN | untouched-OOS survivor quality under fixed compute | BLOCKED | [AlphaAgent.md](./AlphaAgent.md) |
| AlphaAgentEvo | self-evolving agentic reinforcement learning for alpha mining | paper method | NOT_RUN | NOT_RUN | untouched-OOS survivor quality under fixed compute | BLOCKED | [AlphaAgentEvo.md](./AlphaAgentEvo.md) |
| AlphaCrafter | full-stack factor discovery, screening, and cross-sectional execution | deterministic public-policy representative pinned to arXiv v2 / upstream commit c6dbc1b | PARTIAL | RUNNING | after-cost OOS Sharpe with return/drawdown/exposure gates | BLOCKED | [alphacrafter_jquants_256.json](../../docs/research/contracts/alphacrafter_jquants_256.json) |
| AlphaEvolve | evolutionary code discovery with executable evaluation | paper method | NOT_RUN | NOT_RUN | task-native executable objective improvement under fixed evaluator | BLOCKED | [AlphaEvolve.md](./AlphaEvolve.md) |
| AlphaForgeBench | reproducible executable factor research by LLM agents | paper benchmark | NOT_RUN | NOT_RUN | reproducible valid-strategy rate plus downstream OOS | BLOCKED | [AlphaForgeBench.md](./AlphaForgeBench.md) |
| AlphaPROBE | principled retrieval and lineage-aware graph evolution | paper method | NOT_RUN | NOT_RUN | untouched-OOS survivor quality and compute per survivor | BLOCKED | [AlphaPROBE.md](./AlphaPROBE.md) |
| AlphaSchema | structured trading-semantics search | paper method | NOT_RUN | NOT_RUN | surviving untouched-OOS candidate quality | BLOCKED | [AlphaSchema.md](./AlphaSchema.md) |
| AlphaSharpe | evolved risk-adjusted metrics that select robust strategies | paper method | NOT_RUN | NOT_RUN | future-OOS quality of selected strategies | BLOCKED | [AlphaSharpe.md](./AlphaSharpe.md) |
| CAMEF / CausalAlpha | causal-augmented multimodal event-driven financial forecasting | paper method | NOT_RUN | NOT_RUN | paper-native forecasting metric on frozen split | BLOCKED | [causalalpha.md](./causalalpha.md) |
| CogAlpha | LLM-driven code-based alpha evolution | paper method | CONTRACT_NOT_FROZEN | NOT_RUN | untouched-OOS survivor quality under fixed compute | BLOCKED | [CogAlpha.md](./CogAlpha.md) |
| CryptoTrade | reflective on-chain/off-chain zero-shot cryptocurrency trading | paper method | CONTRACT_NOT_FROZEN | NOT_RUN | after-cost OOS risk-adjusted return on the paper-native crypto task | BLOCKED | [cryptotrade.md](./cryptotrade.md) |
| Deep Hedging with Reinforcement Learning | cost-aware dynamic hedging of equity-index option exposure | paper method | CONTRACT_NOT_FROZEN | NOT_RUN | future-test risk-adjusted hedging outcome under fixed costs and limits | BLOCKED | [deephedging.md](./deephedging.md) |
| EDINET-Bench | Japanese filing NLP benchmark for fraud, earnings forecast, and industry prediction | official summary-only logistic baseline pinned to SakanaAI/EDINET-Bench commit 797fbb5 and dataset revision cf0bc74 | BASELINE_REPRODUCED | NOT_RUN | task-native Accuracy/F1/Macro-F1 on frozen split | BLOCKED | [summary.json](../../docs/research/results/edinet_bench_logistic/summary.json) |
| FactorMiner | symbolic failure memory and self-evolving alpha discovery | paper method | NOT_RUN | NOT_RUN | untouched-OOS survivor quality and compute per survivor | BLOCKED | [FactorMiner.md](./FactorMiner.md) |
| FinanceHarness | finance-specific PIT research harness separated from the model | paper benchmark | NOT_RUN | NOT_RUN | native rubric score with PIT/provenance hard gates | BLOCKED | [FinanceHarness.md](./FinanceHarness.md) |
| Financial Statement Analysis with Large Language Models | LLM forecasting from anonymized financial statements | paper GPT-4 protocol | NOT_RUN | NOT_RUN | paper-native earnings-direction accuracy/F1 on frozen split | BLOCKED | [fsa_gpt4.md](./fsa_gpt4.md) |
| FinDeepForecast | live evaluation of unresolved financial forecasts | paper protocol | NOT_RUN | NOT_RUN | paper-native live forecasting metric | BLOCKED | [findeepforecast.md](./findeepforecast.md) |
| FinGAIA | end-to-end real-world financial agent benchmark | paper benchmark | CONTRACT_NOT_FROZEN | NOT_RUN | paper-native benchmark task success | BLOCKED | [fingaia.md](./fingaia.md) |
| FinMCP-Bench | MCP-based real-world financial tool-use benchmark | paper benchmark | CONTRACT_NOT_FROZEN | NOT_RUN | paper-native tool-use task success with provenance/replay gates | BLOCKED | [finmcp_bench.md](./finmcp_bench.md) |
| FINSABER | long-horizon multi-regime evaluation of LLM trading | paper benchmark | CONTRACT_NOT_FROZEN | NOT_RUN | long-horizon after-cost OOS performance plus regime diagnostics | BLOCKED | [finsaber_long_run.md](./finsaber_long_run.md) |
| FinSphere | EDGAR-grounded autonomous financial analysis | paper method | NOT_RUN | NOT_RUN | paper-native financial analysis benchmark | BLOCKED | [FinSphere.md](./FinSphere.md) |
| LongFinanceQA | supervised chain-of-thought for long-context financial document understanding | paper method | CONTRACT_NOT_FROZEN | NOT_RUN | paper-native long-context QA metric on frozen split | BLOCKED | [longfinanceqa.md](./longfinanceqa.md) |
| MCP Multi-Agent Systems Framework | standardized context sharing and coordination for multi-agent systems | paper method | CONTRACT_NOT_FROZEN | NOT_RUN | paper-native multi-agent benchmark/task success with coordination overhead | BLOCKED | [mcp_mas_framework.md](./mcp_mas_framework.md) |
| MCPFM | multi-scale network systemic-risk early warning with MCP-mediated agents | paper method | CONTRACT_NOT_FROZEN | NOT_RUN | paper-native systemic-risk early-warning performance | BLOCKED | [mcpfm.md](./mcpfm.md) |
| QuantaAlpha | multi-agent trajectory recombination for alpha evolution | paper method | NOT_RUN | NOT_RUN | untouched-OOS survivor quality under fixed compute | BLOCKED | [quantaalpha.md](./quantaalpha.md) |
| QuantAgent | price-driven multi-agent LLM high-frequency trading | paper method | CONTRACT_NOT_FROZEN | NOT_RUN | after-cost paper-native trading performance with latency/execution hard gates | BLOCKED | [quantagent.md](./quantagent.md) |
| QuantCode-Bench | executable semantic evaluation of generated trading code | paper benchmark | NOT_RUN | NOT_RUN | executable and semantic pass rate | BLOCKED | [quantcode_bench.md](./quantcode_bench.md) |
| QuantMCP | verifiable financial data/tool grounding through MCP | paper method | CONTRACT_NOT_FROZEN | NOT_RUN | paper-native task correctness with provenance and tool-grounding gates | BLOCKED | [quantmcp.md](./quantmcp.md) |
| R&D-Agent-Quant | joint factor/model co-optimization in automated quantitative R&D | paper method | CONTRACT_NOT_FROZEN | NOT_RUN | untouched-OOS survivor quality under fixed compute | BLOCKED | [rd_agent_quant.md](./rd_agent_quant.md) |
| TiMi | minute-level strategy development and deployment separation | paper method | CONTRACT_NOT_FROZEN | NOT_RUN | after-cost risk-adjusted return with execution/risk gates | BLOCKED | [TiMi.md](./TiMi.md) |
| To Trade or Not to Trade | agentic stochastic-model discovery for market-risk-informed trading | paper method | CONTRACT_NOT_FROZEN | NOT_RUN | future-OOS after-cost risk-adjusted trading performance | BLOCKED | [to_trade_or_not_to_trade.md](./to_trade_or_not_to_trade.md) |
| Trading-R1 | reinforcement-learned financial reasoning for risk-sensitive trading | paper method | CONTRACT_NOT_FROZEN | NOT_RUN | after-cost paper-native risk-adjusted return with drawdown gates | BLOCKED | [trading_r1.md](./trading_r1.md) |
| When Agents Trade | live multi-market benchmark for LLM trading agents | paper benchmark | CONTRACT_NOT_FROZEN | NOT_RUN | live multi-market risk-adjusted trading outcome under verified inputs | BLOCKED | [when_agents_trade.md](./when_agents_trade.md) |

## 判定契約

- `BEAT` はfamily固有の事前固定primary capabilityで直接比較に勝ち、PIT/OOS/cost/risk hard gateも満たした場合だけ付与する。
- `TIE` / `LOSE` はそのまま残す。`BLOCKED` は勝利として扱わない。直接比較が未完了のfamilyは公開surfaceでは `BLOCKED` とする。
- 全familyが `BEAT` になるまで、AAARTSが全frontierを上回ったとは記載しない。
- 比較契約は Issue #51、inspection queueは #55、日本株の共通PIT benchmarkは #184を再利用し、別authorityを作らない。

生成: `python scripts/paper_family_frontier.py render --write`
