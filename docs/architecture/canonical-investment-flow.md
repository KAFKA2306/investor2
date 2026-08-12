# Canonical investment flow

Issue #31 の Ratchet 契約として、投資判断へ到達する正準線を次の1本に固定する。

```text
primary / version-pinned external evidence
  -> data/input_ledger (accepted / rejected / audit)
  -> point-in-time datasets + frozen manifests
  -> hypothesis evaluation / OOS / ablation
  -> reproducible evidence artifacts
  -> public Evidence & Evolution Dashboard
  -> human investment decision
```

## Source of truth

- 外部入力の採否・provenance: `data/input_ledger/`
- 凍結評価条件: `data/benchmarks/*_frozen_split.json` と対応する manifest
- 研究判断: hypothesis / run / evidence の既存 domain contract
- 公開投影: `docs/` / Pages。公開物は正準入力ではなく、監査済み研究証拠から再生成できる projection とする。

同じ事実を Pages 用、研究用、検証用で独立した正準値として重複保持しない。取得不能・未検証の値は推測補完せず、accepted/rejected/audit の既存境界で扱う。

## Three KPIs

Issue #31 の主要KPIは次の3つだけとする。実測値が存在しない場合は数値を捏造せず未計測として扱う。

1. **update success** — 正準入力更新が audit PASS まで到達した割合。
2. **freshness** — 投資判断に使用する正準入力・公開projectionの data-as-of / generated-at の鮮度。
3. **usable evidence outputs** — frozen OOS・provenance・再現条件を満たし、判断に利用可能な evidence artifact 数。

## Non-goals

- workflow数、chart数、datasetコピー数を成果KPIにしない。
- 新しい抽象層を、実利用経路が1つしかない段階で追加しない。
- 外部の定期研究workflowから無関係な提案を自動commitして正準研究線へ混ぜない。

## Repository ratchet

`tests/test_repository_ratchet.py` は、この文書・README入口・正準pathが存在することと、削除した `weekly-repo-research.yml` が再混入しないことをfail-closeで検査する。
