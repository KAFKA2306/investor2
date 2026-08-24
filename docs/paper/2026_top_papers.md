# 2026年トップ論文 — paper-family frontier comparison

**調査日**: 2026-08-24

2026年に主要会議で採択、または2026年に初版公開された研究のうち、`investor2 / AAARTS` の **アルファ探索・戦略生成・バックテスト・PIT評価・実運用** に直接つながるfamilyを、Issue #194と同じ比較原則で整理する。

> 論文記載値とrepository実測値を混ぜて優劣判定しない。`BEAT / TIE / LOSE / BLOCKED` は、familyごとに比較契約をfreezeし、同条件の直接実証が完了してから付与する。

## Frontier matrix

| Family | 2026年の位置づけ | #194 track | 論文が主張する強み | investor2での直接比較 | primary judgement | 現在 |
|---|---|---|---|---|---|---|
| [AlphaAgentEvo](./AlphaAgentEvo.md) | ICLR 2026 | alpha discovery / evolution | 探索履歴を保持するself-evolving agentic RL | 固定data・compute budgetで AAARTS baseline vs +evolution。生成数ではなく untouched-OOS survivor と下流成績を比較 | OOS survival + after-cost OOS performance | 未実証 |
| [AlphaSchema](./AlphaSchema.md) | arXiv 2026-07 | alpha discovery / originality | formulaではなくstructured trading semanticsを探索 | 同一生成予算で semantic coverage、重複率、valid factor率、untouched-OOS survivalを比較 | surviving OOS candidate quality | 未実証 |
| [AlphaCrafter](./AlphaCrafter.md) | arXiv 2026-05 | Japanese-equity alpha/trading | Miner → Screener → Trader のadaptive factor-to-execution pipeline | 日足cross-sectional semanticsが合うため、固定256-asset J-Quants PIT contractへ移植してAAARTSとhead-to-head | after-cost OOS Sharpe + return/DD/exposure gates | 未実証 |
| [TiMi](./TiMi.md) | ICLR 2026 | trading / execution | strategy developmentとminute-level deploymentの分離 | 日足J-Quantsへ無理に落とさず、minute-level data・slippage・latencyを固定した別trackで比較 | after-cost risk-adjusted return + execution/risk gates | contract未凍結 |
| [AlphaForgeBench](./AlphaForgeBench.md) | arXiv 2026-02 | alpha discovery / reproducibility | LLMをTraderではなくexecutable factorを作るQuant Researcherとして評価 | 同一prompt/taskの複数trialで executable率、artifact再現性、run variance、下流OOSを比較 | reproducible valid strategy rate + downstream OOS | 未実証 |
| [QuantCode-Bench](./quantcode_bench.md) | arXiv 2026-04 | data / tooling / reproducibility | trading codeを実際に実行しsyntax→backtest→trade→semanticsで評価 | paper benchmarkを再現可能なら同一taskでstrategy generatorを比較。投資成績とは別gate | executable/semantic pass rate | 未実証 |
| [FINSABER](./finsaber_long_run.md) | KDD 2026 Datasets & Benchmarks Oral（arXiv v1は2025） | trading / risk / regime evaluation | 20年・100+ symbolsで短期LLM優位性の崩壊とregime biasを検証 | 長期・複数regimeのPIT contractを別途freezeし、AAARTSのregime robustnessを直接比較 | long-horizon after-cost OOS + regime diagnostics | contract未凍結 |
| [FinDeepForecast](./findeepforecast.md) | arXiv 2026-01 | causal / event / forecasting | 答え未確定の金融forecastを継続生成してlive評価 | prediction time、source snapshot、horizon、realized valueを固定したlive protocolで比較 | paper-native forecasting metric | 未実証 |
| [FinanceHarness](./FinanceHarness.md) | arXiv 2026-07、v2 2026-08 | data / MCP / agent-tooling | finance-specific harnessとPIT benchmarkをmodelから分離 | 同一backboneで AAARTS research harness vs baseline。PIT違反・citation/provenanceもhard gate | FinanceGym/native rubric score + PIT integrity | 未実証 |

## 直接比較の優先順位

### 1. AlphaCrafter

最優先。論文自体が日足cross-sectional tradingで、CSI 300 / S&P 500をtraining・validation・backtesting・live tradingへ時系列分割している。`investor2` の256-asset J-Quants PIT/OOS contractへ最も自然に載せ替えられる。

比較時はpaper-reported Sharpeをそのまま基準にせず、同一J-Quants universe・fold・cost・seed・benchmarkで **AAARTS vs reproduced AlphaCrafter** を実測する。

### 2. AlphaAgentEvo / AlphaSchema / AlphaForgeBench

同じalpha-discovery trackで比較する。生成formula数ではなく、固定compute budgetあたりの

- unique valid candidates
- duplicate / leakage rejection
- semantic / lineage diversity
- untouched-OOS survival rate
- surviving candidateのmedian/best after-cost OOS
- compute cost per survivor

を共通指標にする。

### 3. QuantCode-Bench

市場収益ではなくstrategy-code生成器として比較する。`parse → execute → trade → semantic checks` を第一関門とし、通過strategyだけを別のPIT/OOS投資評価へ渡す。

### 4. FINSABER

「直近で勝った」ことを無効化する長期robustness gateとして使う。20年規模というclaimed capabilityを検証できる履歴とPIT条件を確保するまで、短期J-Quants結果だけでFINSABER familyをBEAT扱いしない。

### 5. FinDeepForecast / FinanceHarness

trading P&Lへ変換しない。前者はlive forecasting、後者はPIT financial research harnessとして、各native taskで比較する。

### 6. TiMi

minute-level executionが本質なので、日足benchmarkへ変形して比較しない。data、transaction cost、slippage、latency、execution semanticsをfreezeできた時点で独立trackを開始する。

## 既収録familyとの統合

以下は同じfrontierに既に存在するため重複ノートを追加しない。

- [AlphaAgent](./AlphaAgent.md)
- [QuantaAlpha](./quantaalpha.md)
- [FactorMiner](./FactorMiner.md)
- [Cognitive Alpha](./CogAlpha.md)
- [FinMCP-Bench](./finmcp_bench.md)

Issue #194 のcanonical family registryへ今回の9 familyを追加し、最終的な公開比較は以下の形式に統一する。

| Family | Claimed strength | Representative | Reproduction state | AAARTS head-to-head | Primary metric | BEAT/TIE/LOSE/BLOCKED | Evidence |
|---|---|---|---|---|---|---|---|

## 一次情報

- AlphaAgentEvo: https://iclr.cc/virtual/2026/poster/10007685
- AlphaSchema: https://arxiv.org/abs/2607.26642
- AlphaCrafter: https://arxiv.org/abs/2605.05580
- TiMi: https://openreview.net/forum?id=ROEwZAxqyS
- AlphaForgeBench: https://arxiv.org/abs/2602.18481
- QuantCode-Bench: https://arxiv.org/abs/2604.15151
- FINSABER: https://arxiv.org/abs/2505.07078
- FinDeepForecast: https://arxiv.org/abs/2601.05039
- FinanceHarness: https://arxiv.org/abs/2607.27853

## Done condition

この一覧に論文を追加しただけでは完了ではない。各familyについて #194 の契約をfreezeし、再現または代表methodを実行し、AAARTSと同条件で比較した証拠がmainに残った時点で初めてfrontier statusを更新する。