# Sandisk Investor Day 2026 / EDINET半導体50社 projection note

観測時刻: 2026-08-14T10:07:00+09:00  
正準入力Issue: https://github.com/KAFKA2306/semiconductor-earnings-model/issues/106  
consumer contract: https://github.com/KAFKA2306/investor2/issues/19

## 入力境界

EDINET DBの取得主体は `KAFKA2306/semiconductor-earnings-model` とし、`investor2` はprojection-onlyを維持する。今回の50社横断データは中央repoで取得・materializeし、本repoではその証拠束を投資分析入力として参照する。独立したEDINET取得経路は追加しない。

中央データ:
https://github.com/KAFKA2306/semiconductor-earnings-model/blob/data/sandisk-investor-day-edinet50-20260814/data/financial_analysis/sandisk-investor-day-2026-edinet-semiconductor-50.json

中央レポート:
https://github.com/KAFKA2306/semiconductor-earnings-model/blob/data/sandisk-investor-day-edinet50-20260814/docs/reports/semiconductor/2026-08-14-sandisk-investor-day-edinet50.md

## 再現条件

- EDINET DB MCP `screen_companies`
- `business_tags=[semiconductor]`
- `revenue > 0`
- delisted除外
- revenue降順
- limit 50
- 最新FYの11指標を `compare_companies` で取得
- 欠損はnull保持

候補は51社、上位50社は2026-08-12版ユニバースと一致する。51位のQDレーザ（E35542）はlimit外。

## KIOXIA anchor

キオクシアホールディングス（E35948）のEDINET DB MCP最新FY2026値:

- revenue: 2,337,628,000,000 JPY
- operating income: 870,369,000,000 JPY
- net income: 554,490,000,000 JPY
- operating CF: 616,540,000,000 JPY
- capex: 283,700,000,000 JPY
- ROE: 0.519
- equity ratio: 0.379
- EPS: 1,024.07 JPY
- DPS: null

## Sandisk一次情報で固定する仮説入力

Sandiskの2026-08-13公式発表はFY2028-FY2030について、売上成長を `mid-to-high teens, consistent with bit growth`、非GAAP粗利益率約80%、営業利益率約75%、調整後FCF率約50%、事業投資後の超過キャッシュ100%還元とした。NBMは8顧客、FY2027 bit shipments約50%、FY2028約3分の2をカバーする見通し。

HBFの最初の標準仕様公開日はSK hynix公式で2026-08-04。最大512GB、最大3.0TB/s、UCIe、Google/Tenstorrent参加が一次情報で確認できる。

一次URL:
- https://investor.sandisk.com/news-releases/news-release-details/sandisk-details-growth-strategy-and-long-term-financial-model
- https://investor.sandisk.com/news-releases/news-release-details/sandisk-reports-fiscal-fourth-quarter-2026-financial-results
- https://news.skhynix.com/en/hbf-at-fms-2026/

株価・同日騰落率はこの証拠束には含めない。発行体IR/EDINET財務と市場観測を混在させないためである。
