# TiMi — 戦略設計と分足実行を分離する

**調査日**: 2026-08-24

**タイトル**: Trade in Minutes! Rationality-Driven Agentic System for Quantitative Financial Trading  
**発表**: ICLR 2026  
**お仕事の目的**: LLMの高水準な市場分析能力を、分足レベルの定量売買へ接続する。  
**解決したいお悩み**: LLMに市場分析から注文判断までを一度に任せると、推論コスト・遅延・判断の揺らぎが短期売買の実行条件と衝突する。

## エグゼクティブサマリー

TiMiは、**strategy development と minute-level deploymentを戦略的に分離**するagentic trading systemである。複数agentが市場分析、コード生成、数理的な反省を担当し、上位の戦略を下位の実行ロジックへ落とす。論文では200超の株式・暗号資産pairを対象に評価し、収益性・効率・risk controlを検証している。

---

## 論文を一緒に読みましょう

**arXiv**: https://arxiv.org/abs/2510.04787  
**OpenReview**: https://openreview.net/forum?id=ROEwZAxqyS

## パラダイムシフト

LLMを毎分呼び出して売買方向を決めるのではなく、**遅いが高度な戦略推論**と**速く決定論的なexecution**を別レイヤーにする。LLMは高次の意味理解・code/math reasoningへ集中し、minute-level executionは事前に生成・検証したルールへ委譲する。

## ここがすごい。三つの特長

1. **Policy → Optimization → Deployment**: 戦略立案、最適化、実行を役割分担したmulti-agent chainとして構成する。  
2. **Macro-to-Micro Reasoning**: 上位の市場状況から個別の短期売買条件へ段階的に落とす。  
3. **Closed-Loop Reflection**: 生成したcodeと数理条件を評価し、実行前に修正するfeedback loopを持つ。

## Gen 4 への効果

- LLMの推論速度をexecution latencyから切り離せる。
- strategy artifactをcodeとして固定できるため、バックテストとproduction executionの差を小さくできる。
- 高頻度側へ進む場合も、LLMを注文ループへ直接置かず、**研究器 → 検証済みstrategy → executor**という責務分離を維持できる。

## 実装で守ること

短期売買ではtransaction cost、slippage、latencyが結果を支配しやすい。paper上のgross performanceではなく、実際の取引頻度に対応したcost modelとexecution assumptionを固定して再評価する。