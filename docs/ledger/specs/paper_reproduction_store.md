# Paper Reproduction Store

論文を「読んだ記録」ではなく、後から ChatGPT / agent が検索し、実装し、再検証できる再現資産として扱うための正準契約。

## 役割分離

### GitHub

GitHub は **軽量で versioned な正準索引**を持つ。

- bibliographic metadata
- 一次 URL
- 論文の主張と、その主張から切り出した実装対象
- public code / public data の discovery state
- provenance
- artifact SHA-256
- 実装 commit
- 検証 verdict
- Pages 向け manifest

論文 PDF、本体 dataset、checkpoint、大量の派生 feature / prediction / trade log は原則として Git に置かない。

### Hugging Face Storage Bucket

Hugging Face Storage Bucket は **大容量・可変な収集／計算 artifact** を置く。

```text
hf://buckets/${HF_RESEARCH_BUCKET}/investor2/research/papers/{year}/{arxiv_id}/{sha256}/{filename}
```

想定 artifact:

- upstream の公開 metadata / source snapshot
- upstream の公開 code snapshot
- upstream の公開 dataset snapshot
- normalized inputs
- derived features
- model checkpoints
- predictions
- trades / portfolio states
- evaluation reports

Bucket は mutable / non-versioned なので、**bucket path 単独では証拠にしない**。検証に採用した artifact は SHA-256 と provenance を GitHub 側 registry に commit して初めて正準 evidence になる。

## 2021 正準索引

- `docs/research/2021_arxiv_finance_registry.json`

この registry は bibliography と storage contract の双方を持つ。`materialized_artifacts` は空配列から開始し、artifact を永続化した時だけ append する。

artifact record の最小契約:

```json
{
  "paper_id": "pigorsch_schaefer_2112_04755",
  "kind": "public_data",
  "filename": "us_stock_panel.parquet",
  "sha256": "...",
  "bytes": 123,
  "observed_at": "2026-08-13T18:00:00+09:00",
  "source_url": "https://...",
  "source_revision": "...",
  "license": "...",
  "hf_uri": "hf://buckets/.../2112.04755/<sha256>/us_stock_panel.parquet"
}
```

`license` や redistribution right を確認できない artifact は HF に再配布しない。代わりに source URL、取得手順、hash、必要なら local-only state を registry へ残す。

## 状態機械

```text
INDEXED
  -> SOURCE_DISCOVERED
  -> MATERIALIZED
  -> METHOD_IMPLEMENTED
  -> EMPIRICALLY_TESTED
  -> VERIFIED | NOT_CONFIRMED
```

各遷移は fail-closed。

- `INDEXED`: arXiv 一次 metadata が確定
- `SOURCE_DISCOVERED`: 公開 code/data の一次 URL と利用条件が確定
- `MATERIALIZED`: 再配布可能 artifact が HF へ保存され、Git 側に SHA-256 が固定済み
- `METHOD_IMPLEMENTED`: 論文から切り出した方法契約がコード化され unit test PASS
- `EMPIRICALLY_TESTED`: 元論文の評価対象に十分近い data / split / benchmark で再実行済み
- `VERIFIED`: 事前に固定した検証 gate を通過
- `NOT_CONFIRMED`: 実行したが gate を満たさない

`METHOD_IMPLEMENTED` を `VERIFIED` と呼ばない。

## ChatGPT / agent の標準手順

```text
search paper from canonical index
  -> verify arXiv primary metadata
  -> discover public code/data from primary project/paper links
  -> check license / redistribution right
  -> materialize reproducible artifact when allowed
  -> hash + provenance commit to GitHub registry
  -> implement paper method
  -> deterministic method-contract test
  -> reconstruct empirical protocol
  -> run frozen validation
  -> publish only the public-safe manifest summary to Pages
```

再取得前には GitHub registry の `materialized_artifacts` を先に見る。同一 upstream revision + SHA-256 の artifact が既に存在すれば再取得しない。

## CI

CI は最低限次を監査する。

- arXiv ID / source URL / first-submitted year の整合
- paper ID の一意性
- method contract の実装有無
- method-contract unit test
- `VERIFIED` / `NOT_CONFIRMED` を empirical test 未実施の paper に付けない
- materialized artifact の SHA-256 が64桁hex
- HF URI が content-addressed path を含む
- provenance 必須 field

Pages は内部 manifest を直接読まず、public-safe manifest のみを読む。Storage Bucket をブラウザから直接列挙しない。
