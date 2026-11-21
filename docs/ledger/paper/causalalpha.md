# CAMEF / CausalAlpha — 因果拡張マルチモーダル金融予測

**タイトル**: CAMEF: Causal-Augmented Multi-Modality Event-Driven Financial Forecasting  
**公開**: 2025  
**目的**: ニュースと市場情報から因果構造を明示し、イベント駆動の金融予測を改善する。  

## エグゼクティブサマリー

CAMEFは、相関だけに依存する金融予測ではなく、イベントと価格変動の間にある因果的な経路を扱うためのフレームワークである。LLMを用いた反実仮想データ拡張と因果学習を組み合わせ、ニュース・イベント・市場状態をより説明可能な形で予測へ接続する。

## 一次情報

- arXiv: https://arxiv.org/abs/2502.04592
- alphaXiv: https://www.alphaxiv.org/abs/2502.04592?lang=ja

## 比較で見る能力

1. **Causal learning**: イベントと市場反応の因果的な関係を学習する。
2. **Counterfactual augmentation**: 重要イベントが存在しなかった場合などの反実仮想を生成し、予測学習へ利用する。
3. **Evidence-grounded forecasting**: 予測だけでなく、根拠となるイベント経路を扱う。

## investor2での比較契約

単純なJ-Quants trading P&Lへ変換して比較しない。論文のforecasting task、split、horizon、primary metricをIssue #51のcontractとして固定し、同一入力・同一評価条件でCAMEF系representativeとAAARTSを直接比較する。直接再現が完了するまでは優越判定を付けない。
