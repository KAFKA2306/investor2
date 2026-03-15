# Alpha Mining & Qlib Optimization Skill

Qlib 形式のアルファ数式の生成、バリデーション、および最適化に関する専門知見。

## 専門知識 (Expertise)
- **Qlib Operator**: `$close`, `$open`, `Ref($close, 1)`, `Mean($close, 5)`, `Std($close, 10)` などの基本演算子。
- **アルファ式の構文要件**: 無効な演算（0除算など）の回避、正規化（Rank, CS_ZScore）の適切な配置。
- **パフォーマンス指標**: IC (Information Coefficient)、IR (Information Ratio)、ドローダウン、Sharpe Ratio の解釈。

## AAARTS (Alpha Authenticity & Reality-Truth System)
アルファ因子の信頼性を担保するための 3 段階バリデーション・パイプライン。

### Phase 1: Description-AST Consistency (整合性)
- **Logic**: 自然言語の説明文 (`description`) と実装コード (`AST`) の一貫性を検証。
- **Action**: 説明文に含まれる変数・関数と、AST で使用されているものが一致しない場合は即時 REJECT。
- **Principle**: 「説明と中身が違う」アルファの混入を未然に防ぐ。

### Phase 2: Calculation Execution & NaN Propagation (計算実行)
- **Logic**: データ欠損（例：`macro_cpi` が未定義）を 0 等で埋めず、`NaN` として扱う。
- **Action**: 計算過程に `NaN` が含まれる場合、最終的なパフォーマンス指標も `NaN` となり、Phase 3 で排除される。
- **Principle**: 不完全なデータによる「偽のアルファ」を許容せず、計算の真実性を優先する。

### Phase 3: Strict Backtest Validation (厳格検証)
- **Logic**: 固定またはレジーム適応型の閾値による最終判定。
- **Thresholds**: (詳細は Quality Gate セクション参照)
- **Error Behavior**: 指標が `NaN` の場合、または閾値を 1 つでも下回る場合は即時 REJECT。

## Quality Gate (品質ゲート) のレビュー基準
生成されたアルファ式は、以下の 4 つのメトリクス（各 [0, 1] に正規化）の加重平均による「Fitness Score」で評価される。

### 1. Correlation Score (相関スコア)
- **Logic**: 因子値とリターンの Pearson 相関の絶対値平均。
- **Normalization**: `avg_corr / 0.3` (上限 1.0)。0.3 以上の相関で満点。

### 2. Constraint Score (制約要件スコア)
- **Thresholds**: 
    - Sharpe Ratio >= 1.5
    - Information Coefficient (IC) >= 0.04
    - Max Drawdown <= 0.10
- **Normalization**: 合格した制約の数 / 全制約数。

### 3. Orthogonality Score (直交性/新規性スコア)
- **Logic**: 既存の Playbook (`ts-agent/data/playbook.json`) との Jaccard 距離。
- **Formula**: `Jaccard = 1 - (intersection / union)` (演算子とカラムの集合で計算)。
- **Goal**: 既存手法との重複を避け、未知のアルファ領域を探索する。

### 4. Backtest Score (バックテスト性能スコア)
- **Normalization**: 
    - Sharpe: [1.5, 2.0] を [0, 1] にスケーリング。
    - IC: [0.04, 0.08] を [0, 1] にスケーリング。
- **Final**: 両者の平均値。

## Regime-Adaptive Verification (レジーム適応型検証)
市場環境（RISK_ON / NEUTRAL / RISK_OFF）に応じて、採用閾値を動的に調整する。

### 1. Multiplier-Based Adaptation
基本閾値（Baseline）に対し、レジームごとの乗数を適用して実行閾値を算出する。
- **RISK_ON**: Sharpe × 1.1, IC × 1.0 (強気相場では基準を厳格化)
- **NEUTRAL**: Sharpe × 0.9, IC × 0.8
- **RISK_OFF**: Sharpe × 0.35, IC × 0.25 (弱気相場では基準を緩和し、有効なシグナルを拾う)

### 2. Fixed Risk Limits
レジームに関わらず、**MaxDrawdown 0.1 (10%)** の制約は常に固定で適用される。リスク管理は市場センチメントに依存しない絶対的な基準とする。

## アルファ式（DSL）の仕様と制限
- **Allowed Operators**: `rank(), scale(), abs(), sign(), log(), max(), min(), Mean(), Std(), Ref()`
- **Allowed Columns**: `$close $open $high $low $volume $vwap $macro_iip $macro_cpi $macro_leverage_trend $segment_sentiment $ai_exposure $kg_centrality`
- **Validation**:
    - `alpha = ` で始まる単一行であること。
    - 未定義のカラムや演算子の使用は即時 REJECT（自動修復を試みるが、失敗時はフォールバックなし）。

## Council of Quants (クオンツ評議会) のレビュー基準
- **Risk Manager Review**: 最大ドローダウン (MaxDrawdown) が許容範囲内か。シャープレシオが最低基準を満たしているか。
- **Alpha Hunter Review**: P-Value が有意水準（通常 0.05 未満）を満たしているか。
- **Regime Specialist Review**: 現在の市場レジーム（Bull/Bear/Uncertain）とアルファのロジックが合致しているか。

## ワークフロー (Workflows)
1. **Formula Generation**: LLM による新規アルファ式の提案。
2. **Validation**: `dsl_validator.ts` による構文チェックと、`backtest_scorer.ts` による過去データ検証。
3. **Strategic Reasoning**: 「Quality Gate」および「Council of Quants」による多角的な品質評価。
4. **Refinement**: 低パフォーマンスな式を、相関の低い別の演算子と組み合わせて改善。

## Ralph Loop Domain Pivot (ドメインピボット)
連続して探索が失敗した場合、自律的に新しい市場ドメイン（セクター、時間枠、ファクタータイプ）へ切り替えるメカニズム。
- **Trigger**: 連続失敗回数 (`consecutiveFailures`) が 2 回以上に達した場合。
- **Action**:
  1. 最近失敗したドメインを「Forbidden Zones (禁止領域)」として記録し、TTL (Time-to-Live) で管理。
  2. 現在の市場レジーム（Volatility/Momentum）を評価。
  3. 禁止領域から最も遠い（Euclidean / Cosine 距離）ドメインを選択。
  4. 一時的に Fitness Threshold を緩和（例：0.5 → 0.4、3サイクル）し、探索をブートストラップする。
- **Logging**: ピボットの理由は必ず `REASON_DESC.md` (Novelty/Orthogonality, Metric Thresholds, Hypothesis Validity) に基づいて記録する。

## ベストプラクティス
- アルファ式は必ず `Rank(Formula)` または `CS_ZScore(Formula)` で断面正規化すること。
- `Ref($close, -1)`（未来参照）が含まれていないか厳格にチェックすること。
- 生成された式は `alpha_quality_optimizer_schema.ts` で型定義され、一貫性を保つこと。
