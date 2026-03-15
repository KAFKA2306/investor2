---
name: alpha-mining-expert
description: Specialized knowledge for discovering, validating, and optimizing quantitative trading alpha formulas using Qlib. Use this when the user asks to generate new alpha factors, review backtest results, or optimize existing mathematical formulas for trading.
---

# Alpha Mining & Qlib Optimization Skill

Qlib 形式のアルファ数式の生成、バリデーション、および最適化に関する専門知見。

## 専門知識 (Expertise)
- **Qlib Operator**: `$close`, `$open`, `Ref($close, 1)`, `Mean($close, 5)`, `Std($close, 10)` などの基本演算子。
- **アルファ式の構文要件**: 無効な演算（0除算など）の回避、正規化（Rank, CS_ZScore）の適切な配置。
- **パフォーマンス指標**: IC (Information Coefficient)、IR (Information Ratio)、ドローダウン、Sharpe Ratio の解釈。

## Council of Quants (クオンツ評議会) のレビュー基準
生成されたアルファ式は、以下の 3 つの視点で厳格にレビューされる。

- **Risk Manager Review**: 最大ドローダウン (MaxDrawdown) が許容範囲内か。シャープレシオが最低基準を満たしているか。
- **Alpha Hunter Review**: P-Value が有意水準（通常 0.05 未満）を満たしているか。偶然の産物ではないか。
- **Regime Specialist Review**: 現在の市場レジーム（Bull/Bear/Uncertain）とアルファのロジック（Momentum/Reversion）が合致しているか。

## ワークフロー (Workflows)
1. **Formula Generation**: LLM による新規アルファ式の提案。
2. **Validation**: `dsl_validator.ts` による構文チェックと、`backtest_scorer.ts` による過去データ検証。
3. **Strategic Reasoning**: 「Council of Quants」による多角的な品質評価。
4. **Refinement**: 低パフォーマンスな式を、相関の低い別の演算子と組み合わせて改善。

## ベストプラクティス
- アルファ式は必ず `Rank(Formula)` または `CS_ZScore(Formula)` で断面正規化すること。
- `Ref($close, -1)`（未来参照）が含まれていないか厳格にチェックすること。
- 生成された式は `alpha_quality_optimizer_schema.ts` で型定義され、一貫性を保つこと。
