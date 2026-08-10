# EDINETDB shared projection

## Contract

`investor2`はEDINETDBへ直接アクセスしません。

金融庁EDINET API v2を使う既存`src/io/sync_edinet.ts`は一次XBRL/提出書類のBronze取得として維持します。EDINETDBは、`KAFKA2306/semiconductor-earnings-model`のquota-ownerが一度取得し、`investor2`に必要なfieldだけへ縮小したprojectionを、正規化検証用のread modelとして利用します。

共有projection:

```text
https://raw.githubusercontent.com/KAFKA2306/semiconductor-earnings-model/main/
data/edinetdb_projections/KAFKA2306__investor2/investor2-kioxia-financials.json
```

## Quota

KIOXIA Holdings (`E35948`) の年次financialsは、`semiconductor-earnings-model`自身も同じmethod/path/paramsを使います。quota-ownerはrequest fingerprintで同一requestをdedupeするため、consumerが増えてもEDINETDBへのKIOXIA financials callは1回です。

初期quota plan全体は次の3 unique requestsです。

1. Toyota + KIOXIA company master batch
2. Toyota annual financials
3. KIOXIA annual financials

`investor2`追加後も3のままです。

## Provenance

consumerは以下を必須検証します。

- `schema_version = edinetdb.consumer-projection.v1`
- `consumer = KAFKA2306/investor2`
- `provider = EDINET DB`
- `attribution = Powered by EDINET DB`
- `request_fingerprint`
- provider response SHA-256
- projection transport SHA-256
- `fetched_at`

raw/full EDINETDB response、API key、公開bulk mirrorは保持しません。

## Source hierarchy

```text
FSA EDINET API v2 raw/XBRL
  -> research Bronze / point-in-time evidence

EDINETDB shared projection
  -> normalized cross-check / read model

model prediction / research decision
  -> derived layer
```

EDINETDB projectionが存在しない場合に、`investor2`からEDINETDBへ直接fallbackしてquotaを消費してはいけません。

## Primary references

- https://edinetdb.jp/docs/mcp-guide
- https://edinetdb.jp/docs/api
- https://edinetdb.jp/legal/terms
- https://disclosure2.edinet-fsa.go.jp/
