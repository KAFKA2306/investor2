# FinDeepForecast — 金融予測Agentを継続live評価する

**調査日**: 2026-08-24

**タイトル**: FinDeepForecast: A Live Multi-Agent System for Benchmarking Deep Research Agents in Financial Forecasting  
**公開**: arXiv, 2026-01  
**お仕事の目的**: Deep Research agentの金融予測能力を、静的QAではなく、未来が順次確定するlive forecasting taskとして継続評価する。  
**解決したいお悩み**: 過去データで作ったbenchmarkは、学習データ混入や未来情報の記憶によって、本当のforward-looking能力を測れない可能性がある。

## エグゼクティブサマリー

FinDeepForecastは、金融forecasting taskを自動生成・追跡・採点するlive multi-agent systemである。企業・macro、recurrent・non-recurrentを含むtask taxonomyを持ち、FinDeepForecastBenchでは週次更新、10週間の評価horizon、8つの主要economy、1,314 listed company、13 methodを対象に比較する。Deep Research agentは強いbaselineを上回る一方、真のforward-looking reasoningにはなお大きな余地があると報告する。

---

## 論文を一緒に読みましょう

**arXiv**: https://arxiv.org/abs/2601.05039

## パラダイムシフト

過去問を解くbenchmarkから、**予測時点では答えが存在しないtaskを作り、将来に答え合わせするbenchmark**へ移る。これによりmemorizationとforecasting skillを分けやすくなる。

## ここがすごい。三つの特長

1. **Live Evaluation**: task生成時点で未来の正解が存在しないため、data contaminationを抑えられる。  
2. **Broad Financial Taxonomy**: corporateとmacro、反復型と一回型の予測を同一frameworkで扱う。  
3. **Continuous Benchmarking**: 一度きりのleaderboardではなく、時間経過とともに予測を確定・採点する。

## Gen 4 への効果

- earnings、macro、industry KPI予測を`prediction_time → evidence_snapshot → horizon → realized_value`として保存できる。
- model upgrade前後を、同じ過去問ではなく同じlive protocolで比較できる。
- directional accuracyだけでなく、calibration、absolute error、portfolio impactまで後から接続できる。

## 実装で守ること

予測値と同時に、その時点でagentが参照したsource snapshotを固定する。後日更新されたWebページや修正版データで当時の予測を再構築しない。