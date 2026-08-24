# Paper-family frontier

この表は `docs/research/frontier/paper_family_frontier.json` から生成する比較surfaceです。論文記載値とrepository実測値を混ぜず、直接head-to-headが完了するまで優越を主張しません。

**Global superiority:** UNPROVEN — 0/34 families are BEAT; 34 remain unresolved.

| Family | Claimed strength | Representative | Reproduction state | Primary metric | Verdict | Evidence |
|---|---|---|---|---|---|---|
| Adaptive BTC Multi-Agent Trading | adaptive multi-agent cryptocurrency trading | paper method | NEEDS_INSPECTION | after-cost OOS Sharpe with drawdown/exposure gates | BLOCKED | [adaptive_btc_multiagent.md](./adaptive_btc_multiagent.md) |
| AlphaAgent | originality-regularized alpha discovery | paper method | NOT_RUN | untouched-OOS survivor quality under fixed compute | BLOCKED | [AlphaAgent.md](./AlphaAgent.md) |
| AlphaAgentEvo | self-evolving agentic reinforcement learning for alpha mining | paper method | NOT_RUN | untouched-OOS survivor quality under fixed compute | BLOCKED | [AlphaAgentEvo.md](./AlphaAgentEvo.md) |
| AlphaCrafter | full-stack factor discovery, screening, and cross-sectional execution | paper method | NOT_RUN | after-cost OOS Sharpe with return/drawdown/exposure gates | BLOCKED | [AlphaCrafter.md](./AlphaCrafter.md) |
| AlphaEvolve | evolutionary code discovery with executable evaluation | paper method | NOT_RUN | task-native executable objective improvement under fixed evaluator | BLOCKED | [AlphaEvolve.md](./AlphaEvolve.md) |
| AlphaForgeBench | reproducible executable factor research by LLM agents | paper benchmark | NOT_RUN | reproducible valid-strategy rate plus downstream OOS | BLOCKED | [AlphaForgeBench.md](./AlphaForgeBench.md) |
| AlphaPROBE | principled retrieval and lineage-aware graph evolution | paper method | NOT_RUN | untouched-OOS survivor quality and compute per survivor | BLOCKED | [AlphaPROBE.md](./AlphaPROBE.md) |
| AlphaSchema | structured trading-semantics search | paper method | NOT_RUN | surviving untouched-OOS candidate quality | BLOCKED | [AlphaSchema.md](./AlphaSchema.md) |
| AlphaSharpe | evolved risk-adjusted metrics that select robust strategies | paper method | NOT_RUN | future-OOS quality of selected strategies | BLOCKED | [AlphaSharpe.md](./AlphaSharpe.md) |
| CAMEF / CausalAlpha | causal-augmented multimodal event-driven financial forecasting | paper method | NOT_RUN | paper-native forecasting metric on frozen split | BLOCKED | [causalalpha.md](./causalalpha.md) |
| Cognitive Alpha / CogAlpha | code-structured alpha evolution | paper method | NEEDS_INSPECTION | untouched-OOS survivor quality under fixed compute | BLOCKED | [CogAlpha.md](./CogAlpha.md) |
| Context7 finance tooling | tool-grounded context retrieval for financial agents | documented method | NEEDS_INSPECTION | provenance completeness and deterministic replay | BLOCKED | [context7.md](./context7.md) |
| Deep Hedging | learned hedging under market frictions | paper method | NEEDS_INSPECTION | frozen hedging loss/risk objective on future OOS | BLOCKED | [deephedging.md](./deephedging.md) |
| EDINET-Bench | Japanese filing NLP benchmark | paper benchmark | NEEDS_INSPECTION | task-native Accuracy/F1/Macro-F1 on frozen split | BLOCKED | [edinet_bench.md](./edinet_bench.md) |
| FactorMiner | symbolic failure memory and self-evolving alpha discovery | paper method | NOT_RUN | untouched-OOS survivor quality and compute per survivor | BLOCKED | [FactorMiner.md](./FactorMiner.md) |
| FinanceHarness | finance-specific PIT research harness separated from the model | paper benchmark | NOT_RUN | native rubric score with PIT/provenance hard gates | BLOCKED | [FinanceHarness.md](./FinanceHarness.md) |
| Financial Statement Analysis with Large Language Models | LLM forecasting from anonymized financial statements | paper GPT-4 protocol | NOT_RUN | paper-native earnings-direction accuracy/F1 on frozen split | BLOCKED | [fsa_gpt4.md](./fsa_gpt4.md) |
| FinDeepForecast | live evaluation of unresolved financial forecasts | paper protocol | NOT_RUN | paper-native live forecasting metric | BLOCKED | [findeepforecast.md](./findeepforecast.md) |
| FinGAIA | agentic financial reasoning | paper method | NEEDS_INSPECTION | paper-native financial reasoning metric | BLOCKED | [fingaia.md](./fingaia.md) |
| FinMCP-Bench | MCP-based financial tool-use benchmark | paper benchmark | NEEDS_INSPECTION | task success with provenance/replay gates | BLOCKED | [finmcp_bench.md](./finmcp_bench.md) |
| FINSABER | long-horizon multi-regime evaluation of LLM trading | paper benchmark | CONTRACT_NOT_FROZEN | long-horizon after-cost OOS performance plus regime diagnostics | BLOCKED | [finsaber_long_run.md](./finsaber_long_run.md) |
| FinSphere | EDGAR-grounded autonomous financial analysis | paper method | NOT_RUN | paper-native financial analysis benchmark | BLOCKED | [FinSphere.md](./FinSphere.md) |
| MCP multi-agent financial framework | MCP-mediated multi-agent financial workflow | paper method | NEEDS_INSPECTION | task success, provenance, deterministic replay, and API efficiency | BLOCKED | [mcp_mas_framework.md](./mcp_mas_framework.md) |
| MCPFM | financial-market MCP tooling | paper method | NEEDS_INSPECTION | task success, provenance, deterministic replay, and API efficiency | BLOCKED | [mcpfm.md](./mcpfm.md) |
| Neuro-symbolic finance agent | neuro-symbolic financial reasoning and strategy generation | paper method | NEEDS_INSPECTION | task-native OOS performance with validity gates | BLOCKED | [neurosymbolic.md](./neurosymbolic.md) |
| QuantaAlpha | multi-agent trajectory recombination for alpha evolution | paper method | NOT_RUN | untouched-OOS survivor quality under fixed compute | BLOCKED | [quantaalpha.md](./quantaalpha.md) |
| QuantAgent | agentic quantitative research and trading | paper method | NEEDS_INSPECTION | after-cost OOS risk-adjusted performance | BLOCKED | [quantagent.md](./quantagent.md) |
| QuantCode-Bench | executable semantic evaluation of generated trading code | paper benchmark | NOT_RUN | executable and semantic pass rate | BLOCKED | [quantcode_bench.md](./quantcode_bench.md) |
| QuantMCP | MCP-based quantitative research tooling | paper method | NEEDS_INSPECTION | task success, provenance, deterministic replay, and API efficiency | BLOCKED | [quantmcp.md](./quantmcp.md) |
| R&D-Agent-Quant | automated quantitative research iteration | paper method | NEEDS_INSPECTION | untouched-OOS survivor quality under fixed compute | BLOCKED | [rd_agent_quant.md](./rd_agent_quant.md) |
| TiMi | minute-level strategy development and deployment separation | paper method | CONTRACT_NOT_FROZEN | after-cost risk-adjusted return with execution/risk gates | BLOCKED | [TiMi.md](./TiMi.md) |
| Trading-R1 | reasoning-centric autonomous trading | paper method | NEEDS_INSPECTION | after-cost OOS risk-adjusted performance | BLOCKED | [trading_r1.md](./trading_r1.md) |
| When Agents Trade | multi-agent market interaction and trading evaluation | paper method | NEEDS_INSPECTION | paper-native trading outcome under frozen market protocol | BLOCKED | [when_agents_trade.md](./when_agents_trade.md) |
| World Models for On-chain Finance | world-model-based on-chain forecasting and decision support | paper method | NEEDS_INSPECTION | paper-native future-OOS forecasting/trading metric | BLOCKED | [worldmodels_onchain.md](./worldmodels_onchain.md) |

## 判定契約

- `BEAT` はfamily固有の事前固定primary capabilityで直接比較に勝ち、PIT/OOS/cost/risk hard gateも満たした場合だけ付与する。
- `TIE` / `LOSE` はそのまま残す。直接比較が未完了のfamilyは公開surfaceでは `BLOCKED` とする。
- 全familyが `BEAT` になるまで、AAARTSが全frontierを上回ったとは記載しない。
- 比較契約は Issue #51、inspection queueは #55、日本株の共通PIT benchmarkは #184を再利用し、別authorityを作らない。

生成: `python scripts/paper_family_frontier.py render --write`
