# 2026年トップ論文 — LLM × Quantitative Finance

2026年に採択または公開された研究のうち、`investor2` の **アルファ探索・戦略生成・バックテスト・PIT評価・実運用** に直接つながる論文を整理する。

## 選定基準

- 2026年の主要会議採択、または2026年公開の研究
- LLM / agent を定量投資へ直接接続している
- バックテスト、live evaluation、PIT、再現性など実証を重視している
- `docs/paper` の既存論文と重複しない

## 追加した9本

| 領域 | 論文 | 2026年の位置づけ | investor2への示唆 |
|---|---|---|---|
| アルファ進化 | [AlphaAgentEvo](./AlphaAgentEvo.md) | ICLR 2026 | 探索を単発生成ではなく継続的な進化ループにする |
| 意味空間探索 | [AlphaSchema](./AlphaSchema.md) | arXiv 2026-07 | 数式そのものではなく、売買仮説の意味構造を探索する |
| クロスセクション | [AlphaCrafter](./AlphaCrafter.md) | arXiv 2026-05 | Miner → Screener → Trader を明示的なharnessで接続する |
| 短期売買 | [TiMi](./TiMi.md) | ICLR 2026 | 戦略設計と分足レベル実行を分離する |
| 再現性 | [AlphaForgeBench](./AlphaForgeBench.md) | arXiv 2026-02 | LLMの直接売買ではなく、実行可能factor生成へ役割を限定する |
| コード実行 | [QuantCode-Bench](./quantcode_bench.md) | arXiv 2026-04 | strategy codeを実際に実行し、構文・取引・意味一致まで検証する |
| 長期妥当性 | [FINSABER](./finsaber_long_run.md) | KDD 2026 | 短期成績ではなく長期・複数regimeで優位性を検証する |
| 予測評価 | [FinDeepForecast](./findeepforecast.md) | arXiv 2026-01 | 金融予測agentを未来情報なしの継続評価へ移す |
| 金融調査 | [FinanceHarness](./FinanceHarness.md) | arXiv 2026-07 | 金融向けtool/harnessとPIT benchmarkを分離して評価する |

## 既収録の2026関連

以下は同じ研究線上にあるが、すでに個別ノートがあるため重複追加しない。

- [QuantaAlpha](./quantaalpha.md)
- [FactorMiner](./FactorMiner.md)
- [Cognitive Alpha](./CogAlpha.md)
- [FinMCP-Bench](./finmcp_bench.md)

## 共通して見える設計原則

1. **LLMを直接Traderにしない** — 仮説、factor、code、research planの生成に寄せ、執行は決定論的な系へ渡す。
2. **探索と評価を分離する** — 生成器自身に合否を決めさせず、バックテスト・PIT・risk constraintを外部harnessで固定する。
3. **OOSを最終判定にする** — in-sampleのSharpeや単一期間の勝率ではなく、walk-forward、複数regime、コスト控除後で比較する。
4. **再現性を測る** — 同一promptの複数試行、factorのturnover、trial間分散まで評価する。
5. **liveで壊れる場所を測る** — データ遅延、未来情報混入、execution、regime shiftを研究系の外側ではなく評価対象に含める。

この9本を個別の実装候補として読むより、**探索 → factor/code化 → deterministic validation → OOS/PIT → live** という一本の評価系として統合するのが重要である。