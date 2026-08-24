# AlphaCrafter — Multi-Agentでクロスセクション戦略を組み立てる

**タイトル**: AlphaCrafter: Harnessing Multi-Agent Workflows for Cross-Sectional Quantitative Trading  
**公開**: arXiv, 2026-05  
**お仕事の目的**: factor発見から選別、portfolio構築までを一つの制御可能なmulti-agent workflowへまとめる。  
**解決したいお悩み**: agentを増やすだけでは、生成factorの品質、重複、再現性、risk constraint、実運用との整合性を管理できない。

## エグゼクティブサマリー

AlphaCrafterは **Miner Cluster → Screener → Trader** の3段階で、factor生成・検証・戦略化を分離する。重要なのはagent数ではなく、各段階を明示的なpolicy、constraint、verificationを持つharnessで接続している点である。論文ではCSI 300とS&P 500を対象に、factor指標、backtestに加えて2026年のlive trading期間まで評価している。

---

## 論文を一緒に読みましょう

**arXiv**: https://arxiv.org/abs/2605.05580  
**Code**: https://github.com/NJU-LINK/AlphaCrafter

## パラダイムシフト

「LLM agentが全部やる」のではなく、**生成する役、落とす役、portfolioへ変換する役**を分離し、その間の入出力契約を固定する。LLMの創造性はMinerへ寄せ、ScreenerとTraderで定量的制約を強くする。

## ここがすごい。三つの特長

1. **Factor Screening**: IC、RankIC、ICIR、RankICIR、hit ratio、coverage、turnoverなど複数指標でfactorを定期的に再評価・除外する。  
2. **Semantic Diversity**: 成績だけでなくfactor間の意味的多様性を考慮し、似たsignalへの集中を抑える。  
3. **Backtest + Live Evaluation**: CSI 300とS&P 500で学習・validation・backtestを時系列分割し、さらに2026年のlive trading期間を設けてtrial間の安定性も評価する。

## Gen 4 への効果

- `generate → validate → select → portfolio` を独立moduleとして固定できる。
- factor registryにIC系指標、turnover、semantic cluster、検証期間を持たせる設計に直結する。
- 研究時のfactor codeと実運用時のportfolio logicを分けることで、LLMの揺らぎをproductionへ持ち込まない。

## 実装で守ること

論文のlive期間は有力な追加証拠だが、長期OOSの代替ではない。`investor2` ではwalk-forward、transaction cost、benchmark exposure、最大DDを同じ評価表へ残す。