# ADR 005: 外部データ源を provider / acceptance / research に分離する

- Status: Accepted
- Date: 2026-08-21
- Related: Issue #19

## Context

外部データ取得は EDINET、J-Quants、GDELT、Polymarket など provider ごとに HTTP/API 契約が異なる。一方、研究側が必要とする契約は共通で、取得時点、provenance、revision/hash、fail-closed acceptance を固定できることである。

従来の `scripts/audit_input_ledger.py` は input ledger 全体を監査する名前だったが、実装は EDINET 固有の company / fiscalYear / docID 契約を直接持っていた。provider を追加するたびに中央スクリプトへ条件分岐を足す構造では、変更影響範囲が増え、source ごとの監査責務も曖昧になる。

## Decision

外部データを次の4層へ分離する。

```text
upstream API / official source
  -> src/io/providers/<provider>.py
  -> materializer / snapshot creation
  -> data/input_ledger + source-specific validator
  -> research projection / hypothesis / decision evidence
```

### 1. Provider module

`src/io/providers/` は upstream の HTTP/API 契約だけを所有する。

- endpoint、query parameter、response schema の validation
- upstream identity の保持
- read-only acquisition
- provider 固有 pagination

provider module は次を行わない。

- accepted/rejected の判定
- canonical ledger への保存
- investment signal の計算
- hypothesis promotion
- order execution

### 2. Materializer

materializer は provider response を point-in-time artifact へ変換し、取得時刻、scope、source URL、hash を固定する。公開可能性や再配布条件が未確認の source は public repository へ raw/derived dataset を永続化しない。

### 3. Source-specific validator

`src/io/input_ledger/validators/` へ source/adapter 固有の acceptance rule を置く。中央 dispatcher は次だけを検査する。

- source が registry に存在する
- source が enabled である
- failure mode が `fail-closed` である
- accepted entry と registry の adapter が一致する
- artifact path が安全かつ実在する
- adapter に対応する validator が存在する

EDINET の fiscal-year/docID 検証は EDINET validator に限定する。他providerへ EDINET 固有fieldを要求しない。

### 4. Research projection

研究コードは upstream API を直接呼ばない。監査済みsnapshotまたは明示的な runtime observation を入力にし、market-implied probability、差分、event feature などの派生量を別層で計算する。

## Polymarket

Polymarket は `src/io/providers/polymarket.py` を read-only provider とする。Gamma API は market discovery、CLOB API は midpoint / spread / price history の取得に限定する。token ID と outcome の対応を provider boundary で検証する。

売買API、wallet、注文処理はこのsource integrationの責務外とする。

Polymarket data の public persistence / redistribution は利用条件の確認が完了するまで別Decisionとし、このADRだけでは有効化しない。

## Consequences

- provider追加時の変更範囲が局所化される。
- input ledger の中央監査からsource固有ロジックを除去できる。
- API変更はprovider module、acceptance rule変更はvalidatorで独立して検証できる。
- research layerがnetwork/API仕様へ直接依存しなくなる。
- 新しい抽象的plugin frameworkや動的import機構は導入しない。validator registryは明示的なPython mappingとし、現時点で必要な最小構造を維持する。
