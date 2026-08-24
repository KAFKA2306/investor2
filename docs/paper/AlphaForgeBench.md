# AlphaForgeBench — LLMをTraderではなくQuant Researcherとして評価する

**タイトル**: AlphaForgeBench: Benchmarking End-to-End Trading Strategy Design with Large Language Models  
**公開**: arXiv, 2026-02  
**お仕事の目的**: LLMの金融推論を、曖昧な売買アクションではなく、再現可能な定量戦略設計能力として評価する。  
**解決したいお悩み**: LLMへ直接Buy/Sellを出させる方式は、同じ条件でも試行ごとの判断が大きく変わり、決定論的decodeでもaction flippingが起こり得る。

## エグゼクティブサマリー

AlphaForgeBenchは、LLMを直接market actorとして扱う設計を見直し、**executable alpha factorを作るquantitative researcher**として評価する。LLMのreasoningと市場executionを切り離し、生成したfactorを決定論的なbacktest engineへ渡すことで、strategy qualityを再現可能に比較できるようにする。

---

## 論文を一緒に読みましょう

**arXiv**: https://arxiv.org/abs/2602.18481

## パラダイムシフト

「このニュースなら買うか？」をLLMへ何度も聞くのではなく、**どんなalphaを定義し、どう計算し、どんなportfolio ruleへ落とすか**を書かせる。推論は確率的でも、生成されたartifact以降の評価を決定論的にできる。

## ここがすごい。三つの特長

1. **Researcher Framing**: LLMの役割をaction emissionからfactor・strategy designへ変更する。  
2. **Executable Artifact**: 自然言語の投資意見ではなく、実行して検証できるalpha factorを評価対象にする。  
3. **Reproducibility Focus**: run-to-run varianceやaction inconsistencyそのものを問題として扱い、reasoningとexecutionを分離する。

## Gen 4 への効果

- agentの出力を「売買命令」ではなく「versioned strategy artifact」に統一できる。
- 同じartifactを同じdata/backtesterで再実行でき、LLM model更新の影響とstrategyの影響を分離できる。
- benchmarkには平均成績だけでなく、複数trialの分散と再現率を入れるべきだと分かる。

## 実装で守ること

再現性は固定seedだけでは足りない。LLMの複数trialを保存し、生成artifactのhash、data snapshot、backtester version、cost assumptionまでprovenanceとして残す。