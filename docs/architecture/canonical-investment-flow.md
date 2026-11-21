# Canonical investment flow

Issue #31 の Ratchet 契約として、投資判断へ到達する正準線を次の1本に固定する。

```text
primary / version-pinned external evidence
  -> data/input_ledger (accepted / rejected / audit)
  -> data/hypothesis_lab (pre-registered hypothesis + frozen MCP capture + deep dive)
  -> point-in-time datasets + frozen manifests
  -> hypothesis evaluation / OOS / ablation
  -> reproducible evidence artifacts
  -> public Evidence & Evolution Dashboard
  -> data/decision_ledger/snapshots (immutable pre-decision state)
  -> human investment decision
  -> data/decision_ledger/reviews (post-outcome learning; original snapshot unchanged)
```

## Source of truth

- 外部入力の採否・provenance: `data/input_ledger/`
- 仮説生成と実MCP探索: `data/hypothesis_lab/`
  - `hypotheses/`: 結果を見る前に固定した machine-readable hypothesis
  - `captures/`: MCP tool / params / information cutoff / result の時点固定
  - `deep_dives/`: screening後の実体・価格圧力・event証拠
- 凍結評価条件: `data/benchmarks/*_frozen_split.json` と対応する manifest
- 研究判断: hypothesis / run / evidence の既存 domain contract
- 人間判断直前の正準記録: `data/decision_ledger/snapshots/`
- 結果判明後の学習: `data/decision_ledger/reviews/`
- 公開投影: `docs/` / Pages。公開物は正準入力ではなく、監査済み研究証拠から再生成できる projection とする。

同じ事実を Pages 用、研究用、検証用で独立した正準値として重複保持しない。取得不能・未検証の値は推測補完せず、accepted/rejected/audit または `unknown` の境界で扱う。

## Hypothesis generation rule

自然言語の投資アイデアをそのままalpha候補にしない。

```text
observation / past decision
  -> measurable hypothesis + falsifiers
  -> broad quantitative screen
  -> follow-up evidence required by mechanism
  -> candidate / reject
```

閾値、必要feature、反証条件は結果を見る前に `hypothesis_id` として固定する。結果確認後に条件を変更する場合は同じhypothesisを書き換えず、新versionを作る。

MCPは取得手段でありsource of truthそのものではない。MCP responseはtool名・params・取得時刻・information cutoffとともにcaptureし、可能な箇所では元のEDINET document ID / source URLまで辿れる形にする。

実践契約は [Hypothesis Lab](../research/hypothesis-lab.md) を参照する。

## Human decision rule

研究証拠が良好でも、人間の意思決定を後から書き換えられる状態では証拠チェーンが途切れる。

entry / add を検討するときは、次の3ゲートを別々に記録する。

1. `underlying_reality` — 実体は本当に壊れたのか
2. `price_pressure_mechanism` — 価格圧力を実体悪化だけで説明すべきか。観測可能な別の売り手フローはあるか
3. `weak_case_margin` — 弱気ケースでも研究を続ける余地があるか

3つすべて `pass` のときだけ Decision Snapshot 候補にする。欠損・未証明は `unknown` とし fail-close する。これは自動売買許可ではない。

snapshotは結果を見る前に固定し、結果判明後は元snapshotを編集せずreviewを追加する。

## Three KPIs

Issue #31 の主要KPIは次の3つだけとする。実測値が存在しない場合は数値を捏造せず未計測として扱う。

1. **update success** — 正準入力更新が audit PASS まで到達した割合。
2. **freshness** — 投資判断に使用する正準入力・公開projectionの data-as-of / generated-at の鮮度。
3. **usable evidence outputs** — frozen OOS・provenance・再現条件を満たし、判断に利用可能な evidence artifact 数。

## Non-goals

- workflow数、chart数、datasetコピー数を成果KPIにしない。
- 新しい抽象層を、実利用経路が1つしかない段階で追加しない。
- 外部の定期研究workflowから無関係な提案を自動commitして正準研究線へ混ぜない。
- 固定 `Rank(CLOSE)` や synthetic backtest stub を正準alpha探索として扱わない。
- seller-flow evidenceからmargin call / forced liquidationを推測補完しない。
- Decision Snapshotから自動で注文を発行しない。

## Repository ratchet

`tests/test_repository_ratchet.py` は、この文書・README入口・`data/input_ledger/`・`data/hypothesis_lab/`・`data/decision_ledger/` が存在することと、削除した `weekly-repo-research.yml` が再混入しないことをfail-closeで検査する。
