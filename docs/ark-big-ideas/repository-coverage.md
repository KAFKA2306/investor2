# ARK Big Ideas 2026 × KAFKA2306 repository coverage

13テーマを、repository名やIssueの存在ではなく、実データ、一次情報provenance、再生成可能性、GitHub Actions、investor2統合で比較する。

- ARK official source: https://www.ark-invest.com/big-ideas-2026
- canonical mapping: https://github.com/KAFKA2306/investor2/issues/111
- checked_at: `2026-08-24T15:21:46+00:00`

| Theme | Canonical repository | Real data | Primary-source provenance | Reproducible | Scheduled workflow | Latest workflow passed | Public domain view | investor2 integration |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| The Great Acceleration | [KAFKA2306/investor2](https://github.com/KAFKA2306/investor2) | yes | yes | yes | yes | yes | no | yes |
| AI Infrastructure | [KAFKA2306/semiconductor-earnings-model](https://github.com/KAFKA2306/semiconductor-earnings-model) | yes | yes | yes | yes | yes | no | yes |
| The AI Consumer Operating System | [KAFKA2306/finAnalist](https://github.com/KAFKA2306/finAnalist) | yes | yes | no | yes | yes | no | yes |
| AI Productivity | [KAFKA2306/econalert](https://github.com/KAFKA2306/econalert) | yes | yes | yes | yes | yes | no | yes |
| Bitcoin | [KAFKA2306/btc_dashboard](https://github.com/KAFKA2306/btc_dashboard)<br>[KAFKA2306/mstr](https://github.com/KAFKA2306/mstr)<br>[KAFKA2306/option](https://github.com/KAFKA2306/option) | no | no | no | no | no | no | no |
| Tokenized Assets | [KAFKA2306/fx](https://github.com/KAFKA2306/fx) | yes | yes | yes | yes | no | no | yes |
| DeFi Applications | [KAFKA2306/skew](https://github.com/KAFKA2306/skew) | yes | yes | no | yes | yes | no | yes |
| Multiomics | [KAFKA2306/multiomics](https://github.com/KAFKA2306/multiomics) | yes | yes | no | yes | no | no | yes |
| Reusable Rockets | [KAFKA2306/trahist](https://github.com/KAFKA2306/trahist) | yes | yes | yes | yes | yes | no | yes |
| Robotics | [KAFKA2306/factory](https://github.com/KAFKA2306/factory) | yes | yes | yes | yes | yes | no | yes |
| Distributed Energy | [KAFKA2306/oil](https://github.com/KAFKA2306/oil)<br>[KAFKA2306/uranium](https://github.com/KAFKA2306/uranium) | yes | yes | no | yes | no | no | yes |
| Autonomous Vehicles | [KAFKA2306/autonomous-vehicles](https://github.com/KAFKA2306/autonomous-vehicles) | yes | yes | no | yes | no | no | yes |
| Autonomous Logistics | [KAFKA2306/autonomous-logistics](https://github.com/KAFKA2306/autonomous-logistics) | yes | yes | yes | yes | yes | no | yes |

## Boundaries

- The Great Acceleration は横断統合であり専用repositoryを要求しない。
- Bitcoin は network / treasury / derivatives を別componentとして判定する。
- Distributed Energy は electricity / nuclear を別componentとして判定する。
- Multiomics は canonical `KAFKA2306/multiomics` と legacy `KAFKA2306/kafin3` を同一視しない。
- non-canonical `KAFKA2306/robot` / `KAFKA2306/space` はcoverageへ加算しない。

ARK forecastとの比較は [#119](https://github.com/KAFKA2306/investor2/issues/119) の責務とする。
