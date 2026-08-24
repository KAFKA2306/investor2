# FINSABER — LLM投資戦略は長期でも市場に勝てるのか

**タイトル**: Can LLM-based Financial Investing Strategies Outperform the Market in Long Run?  
**発表**: KDD 2026  
**お仕事の目的**: LLM投資戦略の優位性が、短い評価期間や限定銘柄だけでなく長期・広範な市場でも持続するか検証する。  
**解決したいお悩み**: 数か月や特定regimeの好成績だけで「LLMが市場に勝った」と結論すると、bull/bear biasや期間選択の影響を見落とす。

## エグゼクティブサマリー

本研究はFINSABERという長期・bias-awareな評価枠組みを用い、20年規模・100超symbolのsystematic backtestでLLMベース投資戦略を検証する。報告では、短期評価で見えた優位性の多くが長期・広範な条件では弱まり、LLM戦略はbull marketでは保守的すぎ、bear marketでは攻撃的すぎる傾向を示す。重要な結論は、agent frameworkの複雑さより **regime detectionとrisk control** が長期成績を左右するという点にある。

---

## 論文を一緒に読みましょう

**arXiv**: https://arxiv.org/abs/2505.07078

## パラダイムシフト

「一度勝ったか」ではなく、**いつ、どのregimeで、どれだけ再現して勝ったか**を問う。LLM投資のbenchmarkを短期PnLから長期・複数regime・多数銘柄へ拡張する。

## ここがすごい。三つの特長

1. **Long-Horizon Backtesting**: 二十年規模の履歴を使い、短期sample dependencyを減らす。  
2. **Broad Asset Coverage**: 100超のsymbolへ広げ、特定銘柄への過適合を検出する。  
3. **Regime-Aware Diagnosis**: 平均returnだけでなく、bull/bear regimeごとの行動biasを分析する。

## Gen 4 への効果

- 新しいagentを追加したら、直近一年だけでなく複数regimeの固定benchmarkを必須にできる。
- 「複雑なagentほど強い」という仮説を捨て、単純baselineとの長期差分で判断できる。
- regime別return、beta、drawdown、turnoverを標準reportに追加する根拠になる。

## 実装で守ること

長期historyでもlook-ahead biasがあれば意味がない。各時点で利用可能だったdata/model情報だけを使うPIT条件を固定し、walk-forward OOSとafter-cost performanceで最終判断する。