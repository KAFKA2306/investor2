# JR西日本「うれしート」利益・EPS寄与モデル基礎台帳

更新日: 2026-08-11
対象: 西日本旅客鉄道株式会社（証券コード 9021 / EDINET E04148）

## 結論

「うれしート」単体の売上高、営業利益、純利益、EPS寄与の実績値は、2026-08-11時点で確認したJR西日本の公開一次資料では開示されていない。したがって、単体利益・EPSは**実績値として扱わず、運行本数 × 設定席数 × 実乗車率 × 指定席単価から積み上げる推計値**として管理する。

## 公式確認済みのJR西日本基準値

### 2026年3月期 実績

- 売上高: 1,845,840百万円
- 営業利益: 198,081百万円
- 親会社株主に帰属する当期純利益: 127,499百万円
- EPS: 277.73円
- ROE: 10.8%
- 有価証券報告書提出日: 2026-06-16

一次資料:
- https://www.westjr.co.jp/press/article/2026/04/30/items/20260430_00_press_kessantanshin.pdf
- https://www.westjr.co.jp/company/ir/library/securities-report/pdf/report39_01.pdf

### 2027年3月期 第1四半期

- 売上高: 424,403百万円
- 営業利益: 55,989百万円
- 親会社株主に帰属する四半期純利益: 39,046百万円
- EPS: 85.80円
- 通期会社予想 純利益: 100,000百万円
- 通期会社予想 EPS: 219.74円
- 期中平均株式数（第1四半期累計）: 455,083,782株

一次資料:
- https://www.westjr.co.jp/company/ir/financial/pdf/27/01.pdf
- https://www.westjr.co.jp/press/article/2026/08/05/page_30903.html

## 関係会社母集団の訂正

MCP抽出で得られた「21社」をJR西日本の関係会社総数として扱わない。

2026年3月期有価証券報告書の連結範囲に関する注記では、次を公式母集団とする。

- 連結子会社: 58社
- 持分法適用関連会社: 5社
- 非連結子会社: 81社
- 持分法非適用の関連会社: 18社

また「関係会社の状況」には連結子会社と持分法適用関連会社が掲載されている。MCPから得た21社は、抽出条件・ページング・重要会社フィルタ等による**取得サブセット**として provenance を保持し、公式母集団と分離する。

一次資料:
- https://www.westjr.co.jp/company/ir/library/securities-report/pdf/report39_01.pdf

## うれしートの確認済み仕様

JR西日本は「うれしート」を既存の新快速・快速・普通列車の座席を使用した有料着席サービスとして案内している。サービス対象列車の一部を有料エリアとし、その座席を指定席として販売する。

2026年2月5日更新の公式FAQで確認できる料金は以下。

- 指定席券: 通常期 530円 / 閑散期 330円
- e5489専用 チケットレス指定席券: 300円

一次資料:
- https://faq-support.westjr.co.jp/hc/ja/articles/8881269142159--%E3%81%86%E3%82%8C%E3%81%97%E3%83%BC%E3%83%88-%E3%81%A8%E3%81%AF%E3%81%A9%E3%81%AE%E3%82%88%E3%81%86%E3%81%AA%E3%82%B5%E3%83%BC%E3%83%93%E3%82%B9%E3%81%A7%E3%81%99%E3%81%8B
- https://faq-support.westjr.co.jp/hc/ja/articles/8881253459471--%E5%BF%AB%E9%80%9F-%E3%81%86%E3%82%8C%E3%81%97%E3%83%BC%E3%83%88-%E3%81%AE%E6%8C%87%E5%AE%9A%E5%B8%AD%E6%96%99%E9%87%91%E3%82%84%E8%B3%BC%E5%85%A5%E6%96%B9%E6%B3%95%E3%82%92%E7%9F%A5%E3%82%8A%E3%81%9F%E3%81%84
- https://www.westjr.co.jp/press/article/items/241213_00_press_2025harudaiyakaisei5_1.pdf

## EPS寄与モデル

単体PLがないため、以下の順序で推計する。

```text
annual_seat_capacity
  = annual_train_runs * seats_per_run

gross_incremental_revenue
  = annual_seat_capacity * load_factor * average_seat_fee

incremental_operating_profit
  = gross_incremental_revenue * contribution_margin

incremental_net_income
  = incremental_operating_profit * (1 - effective_tax_rate)

incremental_eps
  = incremental_net_income / weighted_average_shares
```

株式数は分析時点に応じて使い分ける。2027年3月期Q1の基準値としては期中平均455,083,782株を使用可能だが、通期EPS推計では当該通期の期中平均株式数が確定後に差し替える。

## データ分類ルール

| 区分 | 意味 | 例 |
| --- | --- | --- |
| observed | 一次資料で直接開示 | 会社全体売上高、営業利益、EPS、うれしート料金 |
| derived | observedから機械計算 | 営業利益率、EPS感応度 |
| assumption | 推計モデル入力 | 乗車率、限界利益率、実効税率 |
| unavailable | 一次資料に単体開示なし | うれしート単体売上・営業利益・純利益・EPS |

**禁止:** assumption / derived を「実績」と表示しない。

## 比較50社データの扱い

陸運業50社比較は、各社の会計年度が一致しないため `fiscal_year_end` と `period_type` を必須列として保持する。順位計算は同一集合内の参考比較に限定し、「同一期間の厳密比較」と表現しない。

MCPで取得した50社レコードは、会社名・EDINETコード・証券コード・会計年度・各財務指標・取得時刻・source endpointを含む機械可読データとして別途materializeする。取得レコードそのものがGitHubに存在しない限り、50社の順位や14項目の網羅取得をこの台帳の確定事実には昇格させない。
