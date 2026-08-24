# To Trade or Not to Trade — agentic market-risk model discovery

**タイトル**: To Trade or Not to Trade: An Agentic Approach to Estimating Market Risk Improves Trading Decisions  
**公開**: arXiv, 2025  
**目的**: LLM agentが金融時系列に対するstochastic differential equationを反復的に発見し、そのrisk metricを日次売買判断へ接続する。

## 一次情報

- arXiv: https://arxiv.org/abs/2507.08584

## 代表能力

論文は、sentiment/trendだけに依存するagentではなく、明示的なmodel-building stepを導入する。発見した確率微分方程式からrisk metricを生成し、traditional backtestとcausally plausibleなmarket simulatorの双方で売買判断を評価する。

## investor2での比較契約

同じ市場・入力・baseline・評価期間・cost/risk semanticsをIssue #51で固定し、model-informed agentとAAARTS側representativeを直接比較する。primary judgementはfuture-OOSのafter-cost risk-adjusted trading performanceとし、risk estimateの妥当性を補助指標にする。直接比較完了までは優越判定を付けない。
