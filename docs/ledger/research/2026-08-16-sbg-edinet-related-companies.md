# SoftBank Group FY2026 related-company EDINET universe

## Decision

PR #103のSB Energy / AI physical infrastructure仮説を、SoftBank Groupの開示済み関係会社全体から再評価できるようにする。

## Evidence

- 基準日: 2026-03-31
- 親提出者: ソフトバンクグループ株式会社 (`E02778`, `99840`)
- EDINET提出書類: `S100YGH5`
- 関係会社: 33社（国内17、海外16）
- standalone EDINET issuer identityを今回直接確認できた国内会社: 8社
- `edinet_code: null` は「EDINET提出なし」ではなく「今回直接確認していない」を意味する。

正準データ: `docs/research/data/sbg_related_companies_edinet_2026-08-16.json`

## Capability delta

企業名、所在地、事業、議決権、国、法人番号、確認済みEDINETコード・証券コードを一つの再利用可能なスナップショットに固定し、`data/input_ledger/snapshot_catalog.ndjson` に登録した。以後、Arm / Ampere / Energy Global / Graphcore / Roze AIや国内子会社を同じ母集団から抽出できる。

## Stopping condition

この作業では開示表の33社を超えて周辺企業を推測追加しない。未確認のstandalone EDINET codeはnullのまま保持する。
