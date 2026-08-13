# Decision ledger

`data/decision_ledger/` は、研究証拠から人間の投資判断へ進む直前の状態を凍結する正準pathです。

## Why

結果を知った後に、過去の判断理由を都合よく書き換えないためです。研究のOOS・再現性が強くても、最後の人間判断が自由文だけなら hindsight bias を監査できません。

## Structure

```text
data/decision_ledger/
  snapshots/   # 結果を見る前に固定する immutable Decision Snapshot
  reviews/     # 結果判明後に別レコードとして追加する Decision Review
```

`snapshots/` の既存ファイルを結果判明後に編集しません。訂正が必要なら新しい `decision_id` のsnapshotを作り、元snapshotをGit履歴ごと残します。`reviews/` は `decision_id` と `original_snapshot_commit` を参照します。

## Entry / add gate

`src/decision/decision_snapshot.ts` の契約では、次の3ゲートを独立に記録します。

1. `underlying_reality` — 実体は本当に壊れたのか
2. `price_pressure_mechanism` — 下落は実体悪化だけで説明できるのか
3. `weak_case_margin` — 自分が間違う弱気ケースでも余地が残るか

各ゲートは `pass / fail / unknown`。3つすべて `pass` のときだけ `eligible_for_human_review=true` です。`unknown` と欠損は通過扱いにしません。

これは売買シグナルではありません。自動執行も行いません。人間が entry / add を検討する前に、最低限の反証可能性と時点整合性を満たしたかを確認するための gate です。

## Point-in-time rule

- `information_cutoff` より後に利用可能になった証拠はsnapshotに使えません。
- `analysis_target` と `execution_target` は分けて記録できます。
- observed fact / calculated value / model estimate / forecast / assumption / hypothesis を区別します。
- 各ゲートには claim、evidence、falsifiers、unknowns を残します。
- snapshotは研究commitとevidence artifactを参照します。

## Validate

```bash
bun src/commands/decision_check.ts data/decision_ledger/snapshots/<decision>.json
```

構造不正・未来情報混入は終了コード1、`buy` / `add` なのに3ゲートが揃わない場合は終了コード2でfail-closeします。

## Privacy

数量、口座残高、証券口座ID、APIキーなどはこの契約に不要です。公開リポジトリへ秘密情報を保存しません。

背景となった実例と抽象化は次の記事にあります。

- https://github.com/KAFKA2306/articles/blob/main/articles/why-i-could-buy-the-crash.md
