# Autonomous Quant Logic Sequence (Operational Ideal)

**Objective**: アルファ生成からオーダー実行までのエージェント間の相互作用の構造設計図を確立する。  
**Context**: 運用上の曖昧さを排除し、完全に自律的で自己改善可能なパイプラインを構築する。

## Executive Summary
本稿は、Gemini 3.0 Proと専門エージェント間の相互作用サイクルを概説する。アイデア創出、Point-In-Time（PIT）データのキュレーション、ASTベースの戦略設計、Net-of-Costsバックテストといったエンドツーエンドのプロセスを網羅する。本手法は、計算のすべての秒を有効なアルファの発見と展開へ向けて活用することを保証する。

---

## Autonomous Quant Logic Sequence (Ideal Architecture)

このダイアグラムは、高度な自律運用を達成するための局所標準を表す。

```mermaid
sequenceDiagram
    autonumber
    participant User as 人間オペレーター
    participant Orch as オーケストレーター
    participant Mem as メモリコア
    participant Data as データエンジニア
    participant Res as 量的研究者
    participant Exec as 実行エージェント

    Note left of Orch: Phase 1: Discovery & Contextualization
    User->>Orch: 要件を入力
    Orch->>Mem: 過去の文脈を取得
    Mem-->>Orch: シードおよび除外ゾーン（失敗履歴）を提供
    Orch->>Orch: 初期コンテキストを生成（任務/制約/メモリ/データ/評価）
    Orch->>Orch: 仮説および因子案を生成
    Orch->>Mem: 候補アイデアを保存
    Orch->>Data: PIT一貫データセットを要求
    Data-->>Orch: 学習データセットと文脈を提供
    Orch->>Orch: データ品質を検証
    alt データ品質不良
        Orch->>Data: データ再生成を要求
        Data-->>Orch: 修正データセットを提供
        Orch->>Orch: データを再検証
    else データ品質良好
        Orch->>Orch: 評価へ進む
    end
    Orch->>Mem: データバージョンと前処理パラメータを確定
    
    Note left of Orch: Phase 2: Evaluation & Verification
    Orch->>Res: 候補式とデータセットを送付
    Res->>Res: 取引ロジック/アルファAST/割当戦略を設計
    Res->>Res: 基盤モデルと適応ポリシーを選択
    Res->>Res: 因子を探索し式を検証
    Res->>Res: Net-of-Costsバックテストを実行
    Res-->>Orch: 戦略パック（AST/取引ルール/割当/KPIs）を返却
    Orch->>Orch: 成功基準に対して評価
    alt ロジックエラー（データソース）
        Orch->>Data: 修正を加えたデータセットを再要求
        Data-->>Orch: 修正データセット
        Orch->>Res: 再評価
    else ロジックエラー（モデル設定）
        Orch->>Res: モデル再構成を要求
        Res-->>Orch: 新しいモデル設定
        Orch->>Res: 再評価
    else 基準達成
        Orch->>Orch: 最終審査へ進む
    end
    Orch->>Mem: 検証結果とモデル設定を保存
    
    Note right of Orch: Final Vetting & Execution
    alt Strategy Accepted
        Orch->>Orch: 最終プレトレード検査（制約/有効期限/容量）
        alt Execution GO
            Orch->>Exec: 注文を生成
            Exec->>Exec: 約定を取得して実行
            Exec-->>Orch: 実行結果を報告
            Orch->>Mem: 注文計画/実行/監査/ドリフトを記録
        else Execution HOLD
            Orch->>Mem: HOLD理由を記録（容量制限等）
        end
    else Strategy Rejected (PIVOT)
        Orch->>Mem: 拒否理由および性能指標を記録
    end
```

## Structural Enhancements
1. **Pre-emptive Context**: 実行前に要件と履歴を整合させ、冗長な計算を最小化する。  
2. **Knowledge Archival**: 候補を早期に保存し、後の取得およびアイデア間の相互参照を容易にする。  
3. **Reproducibility**: データと前処理パラメータをバージョン管理し、バックテスト結果の一貫性を保証する。  
4. **Integrated Design**: 取引ロジック、アルファ、アロケーションは、全体システムの性能を最大化するよう相互依存的に設計される。  
5. **Value in Rejection**: 拒否の理由は、次の探索反復における高価値データとして扱われる。  

---

## 🎯 Core Alpha Discovery Loop (Operational Minimum)
> 詳細は、`docs/specs/alpha_discovery_runbook.md` および `docs/specs/autonomous.md` を参照のこと。

```mermaid
sequenceDiagram
    autonumber
    participant A as 反重力/コデックス
    participant T as タスクファイル
    participant L as ループ監視者
    participant O as Gemini/Qwen（アイデア生成）
    participant V as 検証/バックテスト
    participant M as 記憶/ACE
    participant U as 統合ログ
    participant P as プロット作成

    A->>T: UQTL_INPUT_CHANNEL + UQTL_NL_INPUT を用いて起動
    T->>L: run:newalphasearch:loop
    L->>O: 次の発見テーマを生成
    O-->>L: テーマ + 特徴署名 + アイデアハッシュ
    L->>V: 検証を実行しスコアを生成
    V-->>L: 適合性/新規性/安定性/適応
    L->>L: 独立性チェック（新規性+ハッシュ+署名）
    alt 新規性なし
        L->>O: テーマを再生成
    else 新規性あり
        L->>M: テーマ/進捗/方針を更新
        L->>U: アルファディスカバリログを追記
        L->>P: サイクルプロットを保存
        P-->>L: プロット更新完了
    end
    L->>L: 失敗閾値をチェック（Ralphループ）
```