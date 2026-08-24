# QuantCode-Bench — 生成した売買コードを本当に実行して評価する

**タイトル**: QuantCode-Bench: A Benchmark for Evaluating the Ability of Large Language Models to Generate Executable Algorithmic Trading Strategies  
**公開**: arXiv, 2026-04  
**お仕事の目的**: LLMが自然言語のstrategy specificationから、実際に実行・バックテストできるalgorithmic trading codeを生成できるか測る。  
**解決したいお悩み**: 見た目がもっともらしいcodeでも、API誤用、取引ゼロ、金融ロジックの誤解、仕様との意味的不一致が残る。

## エグゼクティブサマリー

QuantCode-Benchは、Reddit、TradingView、StackExchange、GitHubおよびsynthetic sourceから構成した400 taskを使い、LLM生成strategyをBacktrader上で実行評価する。単なるsyntax passではなく、**実行成功・実際のtrade発生・task semanticsとの一致**まで段階的に確認する。single-turn生成に加え、失敗を見て修正するagentic multi-turn設定も比較する。

---

## 論文を一緒に読みましょう

**arXiv**: https://arxiv.org/abs/2604.15151  
**Code**: https://github.com/LimexAILab/QuantCode-Bench

## パラダイムシフト

code generationの評価を「正しそうなコード」から **実行結果** へ移す。金融strategyでは構文が正しいだけでは不十分で、entry/exit条件、position sizing、indicator API、時間軸が仕様どおりに動いて初めて成功とする。

## ここがすごい。三つの特長

1. **400 Executable Tasks**: 実際のalgorithmic trading要求に近い多様なtaskで評価する。  
2. **Execution-Based Validation**: syntax、backtest成功、trade発生、semantic alignmentを段階的に測る。  
3. **Repair Loop Evaluation**: error feedbackを受けてLLMがstrategy codeを修復できるかも測定する。

## Gen 4 への効果

- strategy generatorのacceptance testを、`parse → import → execute → trade → semantic checks → performance`へ標準化できる。
- 「テストは通るが何も取引しない」strategyを明示的にrejectできる。
- LLM model比較を会話品質ではなく、実行可能strategyの成功率で行える。

## 実装で守ること

実行成功を投資成功と混同しない。QuantCode-Bench型のcode acceptanceを第一関門とし、その後にPIT、OOS、transaction cost、risk、benchmark比較を別関門として通す。