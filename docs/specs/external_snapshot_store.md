# External Snapshot Store

外部API・MCP・公式Webから取得した分析データを、会話や一時実行だけで消費せず、再利用可能な正準snapshotとして保存する。

## 原則

1. **materialize first**: 再利用する外部データはJSON/NDJSONとしてrepo内へ保存する。
2. **content address**: 保存物はSHA-256で固定し、後から内容が変われば監査を失敗させる。
3. **provenance required**: 取得元、operation/endpoint、query/scope、取得日時、一次URLをsourceごとの必須項目として残す。
4. **observed != derived != assumption**: 推計値を取得実績へ昇格させない。
5. **reuse before refetch**: 同じ目的の取得前に `reuse_key` で最新accepted snapshotを確認する。
6. **fail closed**: source未登録、artifact欠落、hash不一致、provenance欠落は再利用不可とする。

## 正準ファイル

- source定義: `data/input_ledger/source_registry.json`
- snapshot catalog: `data/input_ledger/snapshot_catalog.ndjson`
- materialized data: datasetに応じて `data/**` または `docs/research/data/**`
- CLI / audit: `scripts/snapshot_store.py`

snapshot catalogはappend-onlyを基本とする。同じデータの新しい取得は古い行を上書きせず、新しい `observed_at` とhashで新規行を追加する。

## 保存単位

1回のMCP/API取得結果を、再利用上意味のあるdataset単位で保存する。

例:

- `transport_peer_50_financials`
- `jr_west_related_companies`
- `jr_west_ureshito_eps_baseline`

`reuse_key` は「次回、何を取り直す前に検索するか」を表す安定キーにする。

例:

```text
transport/japan-listed/50-financials
jr_west/group/related-companies
jr_west/ureshito/eps-baseline
```

## 登録

データ本体を先に保存し、その後catalogへ登録する。

```bash
python scripts/snapshot_store.py register \
  --dataset-id transport_peer_50_financials \
  --reuse-key transport/japan-listed/50-financials \
  --artifact-path data/snapshots/transport_peer_50_financials_2026-08-11.json \
  --source external_mcp_snapshot \
  --source-kind mcp \
  --observed-at 2026-08-11T11:00:00+09:00 \
  --schema-version investor2.transport-peer-financials.v1 \
  --provenance-json '{"tool":"EDINET DB MCP","operation":"company comparison","query_or_scope":"50 active listed land-transport peers; 14 financial fields","retrieved_at":"2026-08-11T11:00:00+09:00","source_urls":["https://disclosure2.edinet-fsa.go.jp/"]}'
```

登録処理はartifactのSHA-256とrecord countを機械計算し、`snapshot_id` を決定論的に生成する。

## 再利用

再取得する前に最新accepted snapshotを解決する。

```bash
python scripts/snapshot_store.py latest --reuse-key transport/japan-listed/50-financials
```

返された `artifact_path` と `observed_at` が目的に対して十分新しければ、そのsnapshotを利用する。古い場合のみ外部取得を再実行して新snapshotを追加する。

## 監査

```bash
python scripts/snapshot_store.py audit
```

CIでも同じ監査を実行する。以下のいずれかでFAILする。

- artifactが存在しない
- SHA-256がcatalogと一致しない
- record countが一致しない
- sourceがregistryにない / disabled
- sourceがfail-closedでない
- sourceごとの必須provenanceが欠けている
- `snapshot_id` が内容から再計算した値と一致しない
- 同じ `reuse_key + observed_at` が重複している

## ChatGPT / agent運用

外部データを取得して分析に使ったターンでは、再利用価値がある場合は同じ作業線で次まで完了する。

```text
fetch via API/MCP
  -> normalize without inventing missing values
  -> materialize JSON/NDJSON
  -> register snapshot catalog
  -> audit
  -> analysis consumes registered artifact
```

「MCPで取得済み」だけでは永続成果とみなさない。catalogに登録されたartifact、または別の正準データストアへの永続化が確認できて初めて再利用可能とする。
