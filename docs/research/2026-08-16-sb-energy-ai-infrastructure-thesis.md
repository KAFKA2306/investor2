# SB Energy AIインフラ投資仮説 — evidence update 2026-08-16

観測時刻: 2026-08-16T09:28:30+09:00  
正準証拠: `docs/research/data/sb_energy_ai_infrastructure_evidence_2026-08-16.json`

## Decision

SoftBank Groupの企業価値を考える際、SB Energyを単なる再生可能エネルギー事業ではなく、Arm・OpenAI投資と接続するAI物理インフラ資産として評価に組み込むべきかを判断する。

## Uncertainty

今回の論点は次の3点に限定する。

1. NVIDIAはSB EnergyのGPU供給者を超えて株主になるのか。
2. SB EnergyのIPO評価額について、公開情報からどの水準まで置けるのか。
3. IPO後のSoftBank Group持分を具体的な比率で企業価値計算に使用できるのか。

## Evidence test

一次情報を `VERIFIED`、信頼できる報道で確認できるが当事者発表のない交渉・IPO観測を `OBSERVED`、証拠から導く評価上の含意を `INFERRED`、公開根拠を確認できない数値を `UNVERIFIED` とする。

## 結論

### 1. NVIDIAの最大30億ドル出資協議 — OBSERVED

2026-08-15、ReutersはThe Informationを引用し、NVIDIAがSB Energyへ最大30億ドルを投資する方向で協議していると報じた。これはNVIDIAがSB Energyの資本側に入る可能性を示すが、現時点では交渉であり、完了した出資や確定した持分として扱わない。

したがって投資仮説では、

- 「NVIDIAがSB Energyへ最大30億ドル出資を協議中」: **OBSERVED**
- 「NVIDIAがSB Energyの株主になった」: **未成立として扱う**
- 「NVIDIAの株主参加がSBG価値を押し上げる」: **出資成立を条件とするINFERRED**

Source:
https://www.reuters.com/business/nvidia-talks-invest-3-billion-sb-energy-part-openai-data-center-deal-information-2026-08-15/

### 2. SB EnergyのAI物理インフラ化 — VERIFIED + INFERRED

SB EnergyとOpenAIの2026-01-09公式発表で、以下は一次情報として固定できる。

- SoftBank Group: SB Energyへ5億ドル投資
- OpenAI: SB Energyへ5億ドル投資
- 合計: 10億ドル
- OpenAI: Milam Countyの初期データセンターについて1.2 GWのリース
- SB Energy: 同拠点をbuild and operate
- SB Energy: 複数のmulti-gigawatt data center campusesを開発中
- Ares: 2025年に8億ドルのredeemable preferred equityを投資

さらにSB Energy自身が現在のmissionを、AI economyのcritical physical infrastructureをdevelop/build/ownすることと明示している。

ここから、SB Energyを「再エネ企業」だけでなく、**電力・土地・データセンター開発・建設・保有を束ねるAI物理インフラプラットフォームへ拡張している**と評価することは妥当な `INFERRED` とする。

Primary sources:
- https://sbenergy.com/openai-and-softbank-group-partner-with-sb-energy/
- https://openai.com/index/stargate-sb-energy-partnership/
- https://sbenergy.com/who-we-are/

### 3. IPO評価額 — 「500億ドル超」までOBSERVED、1000億ドルは不採用

Reutersは2026-05-26、SB Energyが米国IPOで**500億ドル超**の評価額を求める可能性があると報じた。

同じ報道で言及される約1000億ドルはSoftBankの別事業 `Roze` に関する数字であり、SB Energyの上限評価額として使用しない。

よって、

- 「SB Energy IPOで500億ドル超を目指す可能性」: **OBSERVED**
- 「SB EnergyのIPO評価額は500億〜1000億ドル」: **削除**
- issuer/regulatory filingによる評価額: **まだUNVERIFIED**

Source:
https://www.reuters.com/world/softbank-hires-banks-us-ipos-sb-energy-ai-robotics-spinoff-roze-sources-say-2026-05-26/

### 4. IPO後SoftBank持分83% — UNVERIFIED、valuation modelから除外

今回確認したSB Energy/OpenAIの公式資料では、SoftBank GroupとOpenAIによる各5億ドルの投資、Aresによる8億ドルの優先株投資までは確認できる。一方、完全希薄化後の現在持分やIPO後のSoftBank Group持分が約83%になることを裏付ける一次情報は確認できない。

したがって **83%をSBGのlook-through value計算に使用しない**。IPO目論見書等で株式数・売出し・新株発行・転換条件が確認できた時点で再計算する。

### 5. SBGへの企業価値含意 — INFERRED

現時点で証拠に耐える投資仮説は次の形になる。

```text
Arm
  = compute IP layer

OpenAI investment / Stargate relationship
  = model + AI demand layer

SB Energy
  = power + data-center development / ownership layer
```

SB EnergyがSBGのAIスタック下層を担う資産になりつつあるという評価は、公式に確認できる事業転換とOpenAIとの資本・需要関係から導ける。ただし、SBGのNAVへ具体的な金額を加算するには、少なくともIPO時のequity value、SoftBankのfully diluted ownership、SB Energyのnet debt / preferred equity / IPO proceedsの用途が必要である。

## 投資判断への変更

従来の強い表現から次へ修正する。

| 項目 | 従来仮説 | 更新後 |
|---|---|---|
| NVIDIA | 最大30億ドル出資 | **最大30億ドルを協議中** |
| SB Energy事業像 | 再エネ→AIインフラ | **一次情報を根拠にAI物理インフラ化を採用** |
| IPO valuation | 500億〜1000億ドル | **500億ドル超の報道のみ採用** |
| 約1000億ドル | SB Energy候補値 | **Rozeの数字として除外** |
| SBG post-IPO ownership | 約83% | **根拠不足で除外** |
| SBG valuation impact | 上昇 | **方向性はINFERRED、金額算定は保留** |

## Stopping condition

現時点では、未確定情報をSBGの定量NAVへ投入しない。次回更新条件は以下のいずれか。

- NVIDIAまたはSB Energyが資本参加を正式発表
- SB Energyの公開registration statement / prospectusでIPO条件・株主構成が確認可能になる
- SoftBank GroupがSB Energy持分・投資簿価・公正価値を公式開示

このいずれかが起きるまでは、「83%」「1000億ドル」「NVIDIA出資済み」を前提としたvaluationを作らない。
