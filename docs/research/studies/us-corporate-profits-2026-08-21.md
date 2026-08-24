# U.S. corporate profits: quantitative decomposition

**As of:** 2026-08-21  
**Collection workline:** https://github.com/KAFKA2306/econalert/issues/20  
**Canonical machine-readable input after merge:** `KAFKA2306/econalert/api/v1/profit-distribution/`

![U.S. corporate profit quantitative analysis](assets/us-corporate-profits-2026-08-21.svg)

Repository asset SHA-256: `8e28cc02d77464f9c3c5ee8c9469fa20ca7a3f0e1f79d3898c7fae66e7cb918f`  
The repository asset is a compact SVG generated from the verified values in this note. The earlier generative infographic is not used as canonical evidence because several labels were too compressed to preserve the exact statistical semantics.

## Question

Why is the U.S. corporate profit share unusually high, and which part of that observation can be attributed to productivity or AI?

The answer should distinguish three layers:

1. **National-account observation:** corporate profits relative to gross domestic income (GDI).
2. **Distribution mechanism:** how value-added prices, unit labor costs, and nonfinancial corporate unit profits moved.
3. **Causal interpretation:** whether AI is responsible for those movements and whether the current profit share persists.

The first two layers are directly measurable. The third is not identified by the current aggregate data.

## 1. Corporate profits / GDI

Richmond Fed reports that BEA corporate profits with inventory valuation and capital consumption adjustments reached **13.9% of GDI in 2025 Q4 and remained 13.9% in 2026 Q1**, the highest observation in data beginning in 1947:

- https://www.richmondfed.org/research/national_economy/macro_minute/2026/profits_without_peril_record_earnings_dont_necessarily_mean_overheating

The latest BEA-source levels distributed by FRED are:

| Series | 2025 Q1 | 2025 Q4 | 2026 Q1 | Unit |
|---|---:|---:|---:|---|
| Corporate profits with IVA and CCAdj (`CPROFIT`) | 3,922.871 | 4,352.096 | **4,426.485** | $bn, SAAR |
| Gross domestic income (`GDI`) | 29,895.650 | 31,199.940 | **31,574.222** | $bn, SAAR |

Sources:

- BEA Corporate Profits: https://www.bea.gov/data/income-saving/corporate-profits
- BEA GDI: https://www.bea.gov/data/income-saving/gross-domestic-income
- FRED CPROFIT metadata/data: https://fred.stlouisfed.org/series/CPROFIT
- FRED GDI metadata/data: https://fred.stlouisfed.org/series/GDI

Using those levels:

```text
corporate profits / GDI
= 4,426.485 / 31,574.222 × 100
= 14.019300%
```

The **13.9%** in the Richmond Fed article cannot be reproduced by rounding the current 14.019300% calculation to one decimal place, so the two figures reflect different data vintages (and may also differ in display precision). The repository therefore stores source values and retrieval hashes rather than treating a rounded chart label as the canonical value.

Year-over-year growth from 2025 Q1 to 2026 Q1 is:

```text
corporate profits = +12.837893%
GDI               =  +5.614770%
```

Profits therefore grew about 7.22 percentage points faster than nominal GDI over that interval. That is why the profit share rose; the result is not explained merely by a larger nominal economy.

## 2. Distribution mechanism

BLS's preliminary 2026 Q2 Productivity and Costs release reports for the nonfarm business sector:

| Metric | 2026 Q2 YoY |
|---|---:|
| Labor productivity | **+2.2%** |
| Hourly compensation | **+3.7%** |
| Unit labor costs | **+1.4%** |
| Value-added output price deflator | **+4.9%** |

BLS release:

- https://www.bls.gov/news.release/prod2.nr0.htm
- Official series metadata/data directory: https://download.bls.gov/pub/time.series/pr/

The relevant accounting relationship is:

```text
labor share ∝ unit labor cost / value-added output price
```

Using the published rounded YoY growth rates, the log-growth approximation is:

```text
Δlog(labor share)
≈ ULC growth - value-added-price growth
≈ 1.4% - 4.9%
= -3.5 percentage points
```

A rate-consistent calculation from the same rounded rates is:

```text
((1 + 0.014) / (1 + 0.049) - 1) × 100
= -3.336511%
```

BLS separately reports that the labor share was **52.9% in 2026 Q2, the lowest value in the series beginning in 1947**:

- https://www.bls.gov/news.release/archives/prod2_08062026.htm

The direct conclusion is therefore narrower than “AI raised profits”:

> Value-added prices increased materially faster than unit labor costs, reducing labor's share of value added.

That shifts income toward **nonlabor payments**. It does **not** imply that the entire difference becomes corporate profit; nonlabor payments also include depreciation, taxes on production and imports less subsidies, net interest, rental income and other items.

## 3. Direct profit evidence inside the BLS productivity accounts

BLS Table 6 provides a more direct measure for the nonfinancial corporate sector. In 2026 Q1:

- Unit profits: **+18.6% from the previous quarter at an annual rate**
- Unit profits: **+6.8% from the same quarter a year earlier**
- Unit labor costs: **+0.7% from the previous quarter at an annual rate**
- Value-added output price deflator: **+3.7% from the previous quarter at an annual rate**

Source:

- https://www.bls.gov/news.release/prod2.t06.htm
- BLS definition: unit profits include corporate profits before tax with IVA and CCAdj.

This supports the claim that profits per unit of real value added were rising quickly. It is stronger evidence than inferring profits only from the labor-share residual.

## 4. Productivity: improved, but not yet a historically unique regime

BLS reports nonfarm business productivity **+2.2% YoY in 2026 Q2**. For the current business cycle from 2019 Q4 through 2026 Q2, productivity grew at a **2.1% annualized rate**, above the **1.5%** rate in the 2007 Q4–2019 Q4 business cycle but equal to the **2.1% long-run rate since 1947**.

Source:

- https://www.bls.gov/news.release/prod2.nr0.htm

Therefore:

- “productivity has improved relative to the 2010s” is supported;
- “the United States is already in an unprecedented AI productivity boom” is not supported by the aggregate series alone.

## 5. AI hypothesis: what is observed and what is not identified

ARK's August 2026 `In The Know` states that inference costs are collapsing by **99.99% per year** and argues that this could produce an entrepreneurial/productivity expansion. It also describes productivity as accelerating toward 3%.

ARK source:

- https://www.ark-invest.com/videos/market-commentary/august-2026-in-the-know-cathie-wood

Those are ARK's interpretation and estimates. The aggregate BEA/BLS data do not identify the causal contribution of AI separately from:

- capital deepening,
- non-AI automation,
- post-pandemic reallocation,
- changes in worker/industry composition,
- fiscal and tax incentives,
- demand/price changes,
- other total factor productivity changes.

The claim **“AI is the dominant cause of the record profit share” remains unproven**.

## 6. CBO benchmark

CBO's February 2026 baseline explicitly includes generative AI diffusion. It estimates that:

- annual total factor productivity growth from 2026–2036 is **0.1 percentage point higher** than without the additional contribution from generative AI diffusion;
- this raises nonfarm-business output by **1% in 2036** relative to the no-additional-AI case;
- domestic corporate profits/GDP are projected to fall from **11.2% at the end of 2025 to 9.9% at the end of 2030**, before gradually rising to 10.1% in 2036.

Source:

- https://www.cbo.gov/publication/62105

CBO's profit/GDP measure is **not the same series** as the Richmond Fed profit/GDI measure and must not be spliced into the same time series. The useful comparison is directional: CBO can simultaneously assume a positive AI productivity contribution and a declining corporate-profit share because net interest payments and depreciation rise and competitive/distributional effects need not preserve the current margin.

## 7. Current interpretation

Evidence strength:

| Statement | Assessment |
|---|---|
| Corporate profits/GDI is at or near a post-1947 record | Directly observed |
| Profits grew faster than GDI through 2026 Q1 | Directly observed |
| Value-added price growth exceeded ULC growth in 2026 Q2 | Directly observed |
| Labor share fell to 52.9% | Directly observed |
| Nonfinancial corporate unit profits rose sharply in 2026 Q1 | Directly observed |
| Productivity is stronger than in the previous business cycle | Directly observed |
| AI contributes positively to future productivity | Plausible; CBO baseline includes a modest contribution |
| AI is the dominant cause of current record profit share | Not identified |
| A ~14% profit/GDI share is a durable new equilibrium | Not established |

The compact economic interpretation is:

```text
observed:
value-added price growth > unit labor cost growth
→ labor share falls / nonlabor share rises
+ nonfinancial corporate unit profits rise
→ unusually favorable profit environment

possible causal channel:
AI + other capital deepening / TFP changes
→ productivity growth
→ lower unit costs than otherwise
→ supports margins

not yet identified:
how much of the observed margin expansion is specifically caused by AI
```

## 8. Canonical update path

Do **not** duplicate the external time series in `investor2`.

The canonical collector is implemented in `KAFKA2306/econalert` and publishes:

```text
api/v1/profit-distribution/latest.json
api/v1/profit-distribution/summary.json
api/v1/profit-distribution/corporate-profit-share.csv
api/v1/profit-distribution/productivity-distribution.csv
api/v1/profit-distribution/manifest.json
```

Collection issue:

- https://github.com/KAFKA2306/econalert/issues/20

Collection PR:

- https://github.com/KAFKA2306/econalert/pull/21

When a new canonical snapshot arrives, refresh this analysis only from the following fields:

1. latest `corporate_profits_gdi_pct`;
2. latest `corporate_profits_yoy_pct` and `gdi_yoy_pct`;
3. nonfarm-business productivity, hourly compensation, ULC and value-added-price YoY;
4. derived labor-share change from the stored formula;
5. nonfinancial-corporation unit-profit YoY and previous-quarter annualized rate;
6. any direct BLS labor-share **level** only when it is separately verified from the current BLS release, because the collector does not infer that level from the bulk labor-share index;
7. CBO/ARK claims only when their original source changes.

This keeps release data and investment interpretation separate: `econalert` owns collection/evidence views; `investor2` owns the hypothesis, interpretation, and decision-facing artifact.
