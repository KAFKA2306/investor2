---
type: research
description: "AI資金吸収・信用スプレッド・半導体評価・機関投資家・金ヘッジの5仮説を反証可能にする研究方針。"
tags:
  - investor2/research
  - investor2/market-liquidity
aliases:
  - "AI資金吸収と流動性の反証研究"
generated:
  by: openai/chatgpt
  at: "2026-11-21"
sources:
  - id: anth
    resource: https://www.anthropic.com/news/ipo-close
    title: Anthropic IPO close
  - id: qts
    resource: https://www.bloomberg.com/news/articles/2026-11-13/blackstone-s-qts-is-cutting-ai-debt-sale-by-more-than-half
    title: QTS募集縮小の報道（一次資料ではない）
  - id: bofa
    resource: https://www.reuters.com/business/global-markets/bofa-survey-2026-11-17/
    title: BofA調査の報道（一次原票ではない）
---

# AI資金吸収と市場流動性：5仮説の採否契約

2026-11-21、[Issue #456](https://github.com/KAFKA2306/investor2/issues/456)で開始。正式な投資研究経路は[Canonical investment flow](../architecture/canonical-investment-flow.md)。市場解説やユーザー提示の再現値を、そのまま確認済みの市場事実へ昇格しない。

## 採用基準

出典の原文、対象日時、取得時刻、単位、母集団、データ改訂、取得時点で利用可能だった情報、原入力のhashを残す。値の状態は少なくとも `PRIMARY_VERIFIED`、`SECONDARY_REPORTED`、`USER_SUPPLIED_UNREPRODUCED`、`MODEL_DERIVED`、`UNVERIFIED` を区別する。一次情報と価格・損益の再計算が揃わなければシグナルを採用しない。疑問は `unknown`、欠損をゼロ補完しない。

## 仮説と競合する説明

| ID | 反証する仮説 | 必要な観測 | 反例・交絡 | 現時点 |
| --- | --- | --- | --- | --- |
| H1 | AI債券市場はスプレッドではなく買い手保有枠の限界で調達不能 | 募集予定額、実際の成立額、提示スプレッド、撤回数、信用格付、資金使途 | 特定債券の担保・条項・価格設定・需要層の問題でも縮小する。QTS一例から市場全体を断定しない | QTSは報道のみ |
| H2 | 信用OAS縮小は資金改善でなく起債供給・建設の停止 | IG/HY OASと発行額/件数、規制の一次公文書、許認可、稼働容量 | 起債件数を維持して調達条件・実物需要も改善すれば供給停止説は弱い。OASだけでヘッジ解除しない | 未確認 |
| H3 | 半導体の予想PER低下は利益予想の下方修正を織り込む | 同一対象・同一年度の株価、EPS予想、改定履歴、指数構成、FCF | 金利・割引率・リスクプレミアム・構成変更でもPERは変わる。適正PER16倍は仮定 | 算式・原表未確認 |
| H4 | テックOW削減は市場全体の現金化でなくセクター間移転 | BofA FMSの調査原票、sample、テック/株式OW、現金、債券、他セクター | 現金化以外もリスク縮小。過去3例の反発・下落だけでは一般化不可 | Reuters二次報道 |
| H5 | L50:S50のプラスはGLDではなくMSFT/GOOGLの相対底堅さ | 実際の構成・weight・調整後価格・各leg寄与・コスト | GLDが当日下げても条件付き分散効果は別問題。FCF銘柄を除いたablationが必要 | ユーザー提示のみ |

## 再計算で止めるべき誤推論

### 信用価格と発行数量は別

現行の[公式流動性スナップショット](https://github.com/KAFKA2306/econalert/blob/main/api/v1/liquidity/latest.json)はSOFR、政策金利、投資適格/ハイイールドOAS、準備預金、ストレス系列の正本である。これは公募/私募債の**募集数量・応募倍率・発行撤回**を収録していない。後者は発行体、規制当局、一次発行統計の資料が必要。新しいマクロcollectorは作らず、原資料取得後に`investor2`のinput ledgerに参照を登録する。

QTSの2026-11-13報道は8億ドルから3億ドルへの募集縮小を示すが、募集原票と245bpの一次確認は未了。これを「全AI企業が量的飽和」と解釈しない。OAS縮小＋起債減少＋規制による建設停止を確認した場合だけ`SUPPLY_CONTRACTION_CANDIDATE`とし、改善の証拠にはしない。

### PER11倍とPER16倍は「-6%減益」を自動的には示さない

同年度の予想利益 `E_forecast` に対し `P/E_forecast = 11` なら、比較倍率16倍での価格織り込み利益は `E_implied = P/16 = (11/16)*E_forecast`、**予想利益比 -31.25%** になる。仮に現在EPS比で予想EPSが+31%なら、`(11/16)*1.31 = 0.900625`、**現在EPS比 -9.94%**。提示された「-6%」を再現するにはEPSの期間・成長率・株価と対象銘柄の元表が必要。算式と評価倍率を固定するまでは`UNVERIFIED`。

### 投資家の売却と現金化は別

2026-11-17のReuters記事はBofA調査のテックネットOWが37%→12%、景気後退予想3%、現金比率が低いと報じる。ユーザー提示の現金3.9%→3.6%は調査原票の独立確認が未了。サンプル・定義・債券/セクター配分の変化も含めて確認する。「現金不足なら必ず下落」「200日線割れの後は必ず戻り売り」はルール化しない。

### L50:S50は資本への寄与かleg単独リターンかを特定する

ユーザー提示の数値（独立検証なし）：SPY -3.64%、GLD -3.67%、AMZN -4.10%、MSFT -2.77%、GOOGL -2.70%、ロング -1.655%、ショート +1.82%、総計 +0.165%。

- -1.655%、+1.82%が**資本に対する寄与**なら単純和で+0.165ポイントになる。
- それぞれの**leg単独の収益率**なら、long50%/short50%についてweight換算が必要。ショート側の+1.82%が利益か原資産収益かも固定する。
- 原台帳の銘柄、weight、cutoff、価格・配当、短期借株コスト、リバランスと比較期間が確認できなければ実測合格とはしない。

Anthropic IPOは同時期イベントでありGLD換金売りの**原因と確定できない**。当初の調達規模1,073億ドルと、2026-11-20公式発表のIPO総額935億ドル＋同時私募260億ドル＝**1,195億ドル**は異なる時点の値である。IPOの調達総額、会社の手取額、資金の他資産からの流出額は別で扱う。[Anthropic公式](https://www.anthropic.com/news/ipo-close)。

## OOS評価契約（データ取得前に固定）

1. 原台帳の `current_model / L50:S50` を探し、モデルのhash、日付、構成比、売買時刻、約定・配当・借株費用を確定。存在しなければ`BLOCKED`。提供値から捏造しない。
2. 情報cutoffを確定した翌米国取引日から**20営業日**を評価窓とし、NYSE/Nasdaqの取引日で数える。未到来なら`OOS_PENDING`と記録。
3. 現行L50:S50、SPY対照、GLD→短期現金同等物、GLDを除き他longへ比例配分、MSFT/GOOGL等のFCF群を除外した版を同一cutoff・同一初期資本・費用条件で比較する。gross/net exposureの違いも別表示。
4. 指標はafter-cost return、SPY超過、銘柄寄与、最大ドローダウン、beta/correlation、turnover、借株・取引費用。感応度と相関の条件付き評価を行う。
5. 各Hを`SUPPORTED / REJECTED / INCONCLUSIVE`で判定し、再現可能な入力・手順・反例を[Hypothesis Lab](hypothesis-lab.md)と既存research artifactに保存する。未測定は合格としない。
6. 個別株は研究素材であり売買対象にしない。投資判断は指数商品に限定し、Decision Snapshotは人間の判断の前段階とする。**自動売買・ヘッジ変更を実行しない**。

この文書のmain反映は「方針の改訂」であり、まだ「2026-11-20の主張が実証された」「20営業日OOSが完了した」を意味しない。
