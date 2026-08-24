# AlphaAgentEvo — アルファ探索を継続進化へ変える

**タイトル**: AlphaAgentEvo: Evolution-Oriented Alpha Mining via Self-Evolving Agentic Reinforcement Learning  
**発表**: ICLR 2026  
**お仕事の目的**: LLMによるアルファ探索を、毎回ゼロからやり直す試行から、過去の探索結果を受け継いで継続的に改善する進化プロセスへ変える。  
**解決したいお悩み**: 「生成 → バックテスト → 失敗 → 再スタート」では探索履歴が蓄積されず、市場regimeの変化にも追従しにくい。

## エグゼクティブサマリー

AlphaAgentEvoは、アルファマイニングを **self-evolving Agentic Reinforcement Learning** として定式化する。階層的rewardを使い、まず正しいtool利用や実行可能性を学習し、その後に運用成績のような難しい目的へ進む。長期的な計画・反省・修正を一つの進化ループに入れ、単発のLLM生成より継続的に改善できる探索器を目指す。

---

## 論文を一緒に読みましょう

**ICLR 2026**: https://iclr.cc/virtual/2026/poster/10007685

## パラダイムシフト

従来のLLM alpha miningは、良いfactorが出なければpromptを変えて再試行することが多い。AlphaAgentEvoは探索そのものを状態を持つ学習問題として扱い、**何を試し、なぜ失敗し、次に何を変えるか**を蓄積する。

## ここがすごい。三つの特長

1. **Self-Evolving Agentic RL**: agentの行動系列そのものを強化学習し、探索方針を継続更新する。  
2. **Hierarchical Reward**: tool callの妥当性など基礎能力から、より難しい投資performanceへ段階的にrewardを与える。  
3. **Long-Horizon Evolution**: 単発factorの点数ではなく、複数回の探索・反省・修正を通した進化を最適化する。

## Gen 4 への効果

- factor探索履歴を捨てず、失敗も次の探索policyへ戻せる。
- AlphaAgentの「既存alphaとの非類似性」と組み合わせれば、**独自性 × 継続進化**を同時に最適化できる。
- rewardをSharpeだけにせず、after-cost return、最大DD、turnover、benchmark correlation、PIT違反などへ分解しやすい。

## 実装で守ること

論文のagent rewardをそのままproduction objectiveにしない。`investor2` では生成・学習系と評価系を分離し、最終判定は固定されたwalk-forward OOS、取引コスト控除後損益、risk指標で行う。