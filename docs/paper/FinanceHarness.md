# FinanceHarness — 金融Deep ResearchをPITで評価する

**タイトル**: FinanceHarness: Autonomous Financial Deep Research Framework  
**公開**: arXiv, 2026-07（v2: 2026-08）  
**お仕事の目的**: 汎用LLMへ金融向けtool、workflow、reward、PIT benchmarkを与え、金融調査能力そのものを再現可能に改善・評価する。  
**解決したいお悩み**: 金融agent benchmarkで未来情報が混ざる、検索の上手さと金融推論が混同される、modelとharnessの寄与が分からない。

## エグゼクティブサマリー

FinanceHarnessは、金融Deep Researchを **environment/data construction、agent loop、reward modeling、benchmark** に分解したframeworkである。FinanceGymではthesis-drivenな金融質問をPIT条件付きで作り、cutoff前に得られる証拠とcutoff後に確定する評価材料を分離する。論文では同じopen-weight backboneでもharness導入によりscoreが25.3%から32.4%へ改善し、一方で最新LLMとharnessを組み合わせても45%未満に留まると報告しており、tool設計と評価系の重要性を示す。

---

## 論文を一緒に読みましょう

**arXiv**: https://arxiv.org/abs/2607.27853  
**Code**: https://github.com/Yijia-Xiao/FinanceHarness

## パラダイムシフト

「どのLLMが最強か」ではなく、**同じbackboneにどの金融environmentとtoolを与え、どうPIT評価するか**を独立変数として扱う。model、harness、data、rewardを分離することで改善箇所を特定できる。

## ここがすごい。三つの特長

1. **Point-in-Time Benchmark**: cutoff前後の情報を明示的に分け、未来情報漏洩を評価設計の中心問題として扱う。  
2. **Finance-Specific Harness**: 検索・データ取得・推論・引用を金融task向けに統合し、汎用agentとの差を測る。  
3. **Model vs Harness Decomposition**: 同じbackboneでharnessの効果を比較し、性能向上の寄与を切り分ける。

## Gen 4 への効果

- research agentのversionとLLM model versionを別々に管理できる。
- SEC/EDINET、価格、決算、macroなどのsourceをPIT cutoff付きtoolとして統一する設計につながる。
- 「良い回答」ではなく、evidence、cutoff遵守、予測・投資判断への寄与をrewardへ分解できる。

## 実装で守ること

PITはprompt上の注意書きではなくdata access layerで強制する。取得可能日、公開時刻、revision、source snapshotをmetadataとして持ち、cutoff後の情報をtool側で返さない構造にする。