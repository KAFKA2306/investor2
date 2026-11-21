---
type: research
description: "ティファニー・高級コンドミニアム・高級品・所得層別カード支出から米国富裕層消費仮説を検証する観測台帳。"
tags:
  - investor2/research
  - investor2/wealth-consumption
aliases:
  - "米国富裕層消費ウォッチ"
generated:
  by: openai/chatgpt
  at: "2026-11-21"
---

# 米国富裕層消費ウォッチ：最初の観測と反証条件

Issue: https://github.com/KAFKA2306/investor2/issues/457

## 使う入口

- [GitHub Pagesで観測表を開く](https://kafka2306.github.io/investor2/?path=data%2Fwealth-consumption%2Fobservations.csv)
- [GitHubの正準観測CSV](https://github.com/KAFKA2306/investor2/blob/main/data/wealth-consumption/observations.csv)
- [Pictet Market Lounge 2026-11-10](https://podcasters.spotify.com/pod/show/pictet/episodes/Pictet-Market-Lounge-2026-11-10-e3s8l6m)

注：上記番組の音声を独立して逐語確認したものではない。仮説の起点として使用し、以下の数値は発表主体の一次資料で別途検証した。観測表はスナップショットであり、リアルタイム値ではない。

## 調査時点 2026-11-21 の確認事項

| 分野 | 観測値 | 期間・定義 | 一次資料 |
|---|---|---|---|
| LVMH / Tiffanyを含む時計・宝飾 | **+6%** | 2026 Q3 オーガニック売上高・前年比。ティファニー単独値ではない | [LVMH 2026-10-12](https://www.lvmh.com/en/publications/continued-growth-in-the-third-quarter-of-2026) |
| LVMH ファッション・革製品 | **−5%** | 2026 Q3 オーガニック売上高・前年比 | [LVMH](https://www.lvmh.com/en/publications/continued-growth-in-the-third-quarter-of-2026) |
| Richemont Jewellery Maisons | **+19%** | 2026年4〜9月期・為替一定売上高前年比。Cartier等を含む | [Richemont 2026-11-13](https://www.richemont.com/news-media/press-releases-news/richemont-posts-strong-results-for-the-six-month-period-ended-30-september-2026-driven-by-sustained-double-digit-sales-growth/) |
| マンハッタンのコンドミニアム | **386契約、−23%** | 2026年10月の契約数・前年比。成約・引渡し件数ではない | [Corcoran 2026年10月市場報告](https://inhabit.corcoran.com/wp-content/uploads/2026/11/the-corcoran-report_manhattan-market-update_october-2026.pdf) |
| マンハッタン500万ドル超住宅 | **80契約、−11%** | 2026年10月の契約数・前年比。コンドミニアム以外も含む | [Corcoran](https://inhabit.corcoran.com/wp-content/uploads/2026/11/the-corcoran-report_manhattan-market-update_october-2026.pdf) |
| BofAカード支出（全所得） | **+5.8%** | 2026年10月、世帯当たり前年比。富裕層だけの数値ではない | [BofA Institute 2026-11](https://institute.bankofamerica.com/economic-insights/consumer-checkpoint-november-2026.html) |

**暫定判定：INCONCLUSIVE（未確定）。** 高級住宅の契約数は減少しているが宝飾の売上とカード支出は増加。富裕層消費が一斉に崩れたとは言えない。単一企業の売上や不動産契約の変化をS&P500下落の原因と断定しない。

## 次回更新の判定

1. LVMH/Richemont/その他主要高級品企業は発表単位（四半期・半期・通期、オーガニック・為替一定）ごとに比較。ティファニー単独の売上高がない場合は「未開示」で止める。
2. Corcoran等の月次報告でマンハッタンの高額住宅の契約数・値引き・在庫・平方フィート当たり単価を確認。契約（フロー）と在庫（ストック）を混ぜない。
3. BofA Instituteの所得層別カード支出を確認。全所得・低所得・上位所得の母集団と集計定義が違えば別系列として扱う。
4. 直前の公表値と比較して改善／悪化／横ばい／未更新を記録。2公表期連続で複数の独立系列が悪化し、業績ガイダンス下方修正も伴う時のみ警戒候補とする。データの公開間隔が異なるため、同じカレンダー月の同時悪化を要件にしない。
5. 対立仮説は住宅ローン金利・供給不足・為替・中国需要・ブランド固有要因。これらと矛盾しない売上低下だけでは資産効果を支持しない。

## データ契約

[観測CSV](../../data/wealth-consumption/observations.csv)を唯一の今回の集約入力として、`observation_id`、`entity`、`metric`、`period`、`value`、`unit`、`yoy_change_pct`、`definition`、`source_date`、`source_url`、`verification`を保存した。資料の公表日とデータの対象期間を区別する。元資料の全文を再配布せず、原典リンクを保持する。`PRIMARY_VERIFIED`は参照した一次資料と値が一致する意味であり、将来の投資予測を検証済みとする意味ではない。

このプロジェクトのGitHub Pagesは既存の証拠ブラウザであり、CSVを表示するだけで数値を再計算しない。新しい値の取得・検証・コミットがなければ現状の値が残るため、表示日が新しくても更新済みとはみなさない。
