# AlphaSchema — 数式ではなく売買仮説の意味空間を探索する

**タイトル**: AlphaSchema: Exploring the Space of Trading Semantics for LLM-Based Alpha Mining  
**公開**: arXiv, 2026-07  
**お仕事の目的**: LLM alpha miningの探索対象を、表面的な数式やprompt variationから、構造化されたtrading semanticsへ移す。  
**解決したいお悩み**: 数式を直接大量生成すると、見た目だけ違うfactorが増えやすく、探索空間の被り・意味的重複・LLM依存が大きくなる。

## エグゼクティブサマリー

AlphaSchemaは、売買仮説を **Event / Context / Qualities / Direction / Output** という構造化schemaで表現し、その意味空間を探索する。探索と実装を分離し、まず「どの意味の仮説を試すか」を選び、その後LLMが実行可能factorへ変換する。過去の評価結果からsurrogate modelを学習し、global exploration、surrogate-guided exploitation、local mutationを組み合わせて次のschemaを選ぶ。

---

## 論文を一緒に読みましょう

**arXiv**: https://arxiv.org/abs/2607.26642

## パラダイムシフト

探索の単位を **formula** から **trading hypothesis** へ上げる。これにより「移動平均の窓だけ違う」といった局所的な式探索ではなく、イベント、文脈、方向性、出力形式の組合せとして仮説の多様性を管理できる。

## ここがすごい。三つの特長

1. **Structured Semantic Space**: factorの意味を固定されたschemaで表し、探索範囲を観測可能にする。  
2. **Surrogate-Guided Search**: 実際のfactor評価を学習したsurrogateで、有望な意味領域へ探索資源を寄せる。  
3. **LLM-Decoupled Hypothesis**: schema planとfactor implementationを分けるため、LLMそのものを交換しても仮説を保持できる。論文では同一schemaを異なるLLMが実装しても予測品質が近いことを報告している。

## Gen 4 への効果

- AlphaAgentのASTによる数式重複排除を、意味レベルの重複排除へ拡張できる。
- factor provenanceを「schema → code → backtest result」として追跡できる。
- schema単位でcoverageを可視化すれば、探索していない仮説領域が明確になる。

## 実装で守ること

surrogate scoreを最終目的にしない。surrogateは探索順序の決定だけに使い、factor採否は固定されたPIT/OOS評価で判定する。