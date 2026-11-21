# 日本企業・開示・ニュース・市場価格の取得境界

## 目的

日本株を `業種 → 企業 → 開示 / ニュース候補 / 市場観測` で横断するための索引層を作る。人手のNotion分類を正本にはせず、取得元・取得時刻・原本hashまで逆引きできる機械可読データを正本にする。

## 一次情報と発見層

| データ | 正準経路 | 役割 |
| --- | --- | --- |
| 企業・証券・業種 | 金融庁 EDINETコードリスト | issuer/security master |
| 日本企業の法定開示 | EDINET API v2 | primary evidence |
| ニュース候補 | GDELT 2.0 GKG bulk files | discovery only |
| 米国法定開示 | SEC EDGAR | primary evidence（別repo） |
| 市場価格候補 | Alpha Vantage | provider verification後に採否決定 |

EDINETコードリストの固定URLは、EDINET API仕様書 Version 2 (2026年6月) が明示する `https://disclosure2dl.edinet-fsa.go.jp/searchdocument/codelist/Edinetcode.zip` を使用する。

EDINET API v2の書類一覧は `GET /api/v2/documents.json?date=YYYY-MM-DD&type=2&Subscription-Key=...`、書類取得は `GET /api/v2/documents/{docID}?type=1&Subscription-Key=...` を使用する。API keyは環境変数 `EDINET_API_KEY` だけから読む。対象書類は仕様書の書類種別コードを優先して識別する。`parentDocID` は訂正前書類や変更報告書の基となる書類などの関係を保持するため、そのまま `parent_doc_id` として保存する。

GDELTはGKG bulk fileをニュース候補の発見に使う。GDELTだけで企業事実を確定しない。mappingは `candidate` とし、投資判断へ利用する場合はEDINET、TDnet、SEC、企業IR等へ遡る。GDELTの公開datasetと、リンク先ニュース記事本文の権利を同一視しない。

Alpha Vantageは通常free tierとverified open-source / educational project向け条件が異なるため、`ALPHA_VANTAGE_API_KEY`を用いた実測とprovider側のqualification evidenceが揃うまでsource registry上で無効にする。日本株symbolのsuffixは推測しない。検証時はproviderで確認済みの `--symbol-template` を明示的に渡す。

## 実行

```bash
python scripts/build_edinet_issuer_master.py
EDINET_API_KEY=... python scripts/fetch_edinet_filings.py --date 2026-08-20 --download-documents
python scripts/ingest_gdelt_news.py
python scripts/query_market_news.py data/market/gdelt_company_news_latest.json --industry 電気機器
ALPHA_VANTAGE_API_KEY=... python scripts/verify_alpha_vantage.py \
  --qualification-status unresolved \
  --symbol-template '{security_code}'
```

`--symbol-template` の例はprovider表記を意味しない。実際の検証ではprovider一次情報または回答で確認したtemplateだけを指定する。

## fail-close

- EDINET masterが空、required column欠損、security/EDINET code重複なら停止
- EDINET API key欠損なら取得しない
- 既知docIDは再取得しない
- EDINETの429は成功扱いせず、十分な時間を空けて再試行する運用にする
- GDELTの曖昧mappingをverifiedへ昇格しない
- Alpha Vantageのquota response、unsupported symbol、provider informationを成功として数えない
- provider利用条件が未確認なら公開正本へ昇格しない

## 一次参照

- EDINET API仕様書 Version 2 (2026-06): https://disclosure2dl.edinet-fsa.go.jp/guide/static/disclosure/download/ESE140206.pdf
- GDELT data: https://www.gdeltproject.org/data.html
- GDELT terms: https://www.gdeltproject.org/about.html
- Alpha Vantage support: https://www.alphavantage.co/support/
- Alpha Vantage documentation: https://www.alphavantage.co/documentation/
