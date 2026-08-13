# Hypothesis Lab — 仮説をMCP実データへ落として、似たアルファを探す

## 目的

「面白そうな投資アイデア」を自然言語のまま残さない。仮説を **必要な観測量・閾値・反証条件** へ分解し、MCPから取得した実データを時点固定して、候補探索とOOS検証へ接続する。

```text
観察 / 過去の意思決定
  -> 仮説を machine-readable spec にする
  -> Stage A: 広い定量screen
  -> MCP query + result をcaptureとして固定
  -> Stage B: 候補ごとの追加証拠を取得
  -> 3 gateで candidate / reject / Decision Snapshot候補
  -> point-in-time dataset + OOS
  -> Decision Review
  -> 次の仮説version
```

現行の `PipelineOrchestrator` に残る固定 `Rank(CLOSE)` stub は、この正準探索線には使用しない。`task run:newalphasearch` は frozen MCP capture を読む Hypothesis Lab を正準入口とする。

## なぜ二段階にするか

低PER、成長率、ROEだけで候補を出すと、単なるvalue/growth screenになりやすい。今回の実runでは次のStage A条件だけで84社が通過した。

- PER <= 10x
- 3年売上CAGR >= 5%
- 3年営業利益CAGR >= 8%
- ROE >= 10%
- 自己資本比率 >= 40%
- FCF yield >= 3%
- net cash / market cap >= 0

したがって、記事で抽象化した「実体は壊れていないのに、別の事情で売られている」を探すにはStage Bが必要になる。

## Stage A — fundamentals / valuation

正準仮説は `data/hypothesis_lab/hypotheses/` に置く。閾値を結果確認後に変更する場合は同じファイルを書き換えず、新しい `hypothesis_id` を作る。

MCP呼び出しの結果は `data/hypothesis_lab/captures/` に保存する。

最低限固定するもの:

- hypothesis_id
- tool名
- query params
- captured_at
- information_cutoff
- total result count
- 保存したrows

MCPは外部入力なので、capture自体を結論にしない。captureは再現対象となる入力証跡である。

## Stage B — dislocation / seller-flow

Stage A通過後、候補ごとに以下を追加取得する。

1. 最新annual / interimの売上・営業利益・純利益・営業CF
2. 同一開示record内のcompany TSRとcomparison-index TSR
3. 大量保有報告の保有比率変化
4. earnings revision / dividend revision / corporate action
5. 必要なら別のmarket-data sourceによるevent-window price / volume / margin-balance

ここでは **seller-flow と forced liquidation を分ける**。

大量保有報告で持分低下が観測できても、それだけで追証・強制決済・投げ売りとは判定しない。直接観測できない原因は `unknown` のまま残す。

## 3 gate

### 1. underlying_reality

実体が壊れていないか。

初期版では最新年度の以下4系列を確認する。

- revenue YoY
- operating income YoY
- net income YoY
- operating CF YoY

欠損は `unknown`。必要系列の悪化は `fail`。

### 2. price_pressure_mechanism

価格低迷と業績悪化を同一視しない。

初期版は最低2種類の独立した観測signalを要求する。

- relative TSR underperformance
- large-holder reduction
- 将来追加: volume shock / margin-balance unwind / ETF-flow / forced-sale evidence

同時にnegative earnings revision等を確認する。売り手フローが存在しても、同時に実体悪化イベントがあるなら単純な需給乖離とは扱わない。

### 3. weak_case_margin

初期版はStage Aで固定した最低条件を再確認する。

- PER <= 10x
- FCF yield >= 3%
- net cash ratio >= 0

これは目標株価ではない。弱いケースでも研究を続ける価値が残るかを見る最低限の余地である。

## 2026-08-13 実践: RION 6823

Stage Aの84社からRIONをdeep-diveした。

FY2026 annual record:

- revenue: 28,501,956,000円、YoY +2.24%
- operating income: 4,361,966,000円、YoY +8.13%
- net income: 3,345,634,000円、YoY +16.99%
- operating CF: 4,165,283,000円、YoY +21.18%
- filing-date PER: 10.0x
- filing-date PBR: 約0.96x
- filing-date FCF yield: 約10.18%
- filing-date net cash ratio: 約0.54
- reported TSR: 1.004
- comparison index TSR: 2.022

大量保有報告イベントでは、Asset Management Oneの比率が5.04% -> 3.98% -> 2.13%と低下した。別の純投資主体も3.92% -> 3.36%へ低下している。

このため初期contractでは、

```text
underlying_reality       PASS
price_pressure_mechanism PASS
weak_case_margin         PASS
=> eligible_for_decision_snapshot
```

とした。

ただし意味は限定する。

- これは2026-08-13時点の売買推奨ではない
- PER/PBR等はEDINET DB annual recordのfiling-date price基準で、ライブ価格ではない
- 保有比率低下は観測された売り手フローであり、forced liquidationの証拠ではない
- TSRは開示recordのtotal-return指標であり、特定イベント日のdrawdownではない

次に実売買判断へ進む場合は、最新価格・出来高・信用/貸借・イベント時点を新しいinformation cutoffで取得し、`data/decision_ledger/` に別途Decision Snapshotを固定する。

## 実行

```bash
task run:newalphasearch
```

出力には以下だけを出す。

- hypothesis_id
- capture_id / information_cutoff
- Stage A total matches / stored rows
- deep-dive済み候補
- 3 gateの再評価
- Decision Snapshotへ進める研究候補

自動売買は行わない。

## 次の改善

今回のStage BはEDINET系だけで作ったため、次は価格・出来高・信用/貸借・ETF flowをpoint-in-timeで加える。重要なのはfeatureを増やすことではなく、**「実体」「価格圧力」「弱気余地」を別ソースで独立に観測すること**である。
