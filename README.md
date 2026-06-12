# 🎀 AAARTS: Autonomous Agentic Alpha Trade System 🚀✨

## 🌸 はじめにっ！ (Introduction)

AAARTS は、研究から執行までを一つの「知能」として統合した、世界一お利口さんなクオンツスタックだよっ！✨
今は **NeurIPS 2026** に向けて、EDINET（有価証券報告書）を使った「業績予想（Earnings Forecast）」の最先端研究に全力投球中なんだもんっ！論文の準備もバッチリだよっ 📝💎

## 📊 研究のステータス (Research Status)

- **EDINET-Bench 攻略中！**: 不正検知（Precision 100%!）、業績予想（全件バックテスト中）をガチ評価してるよっ 📈
- **Ablation Study**: 「財務数値」と「定性テキスト」のどっちが未来を当てるのに大事か、徹底的に切り分けてるんだからっ 🧪✨

## 🗺️ だいじなポインタ (Key Pointers)

- **NeurIPS 論文アウトライン**: [docs/paper/neurips_earnings_forecast_outline.md](docs/paper/neurips_earnings_forecast_outline.md)
- **設計図（フロー）**: [docs/diagrams/simpleflowchart.md](docs/diagrams/simpleflowchart.md)
- **運用ルール**: [AGENTS.md](AGENTS.md)
- **決定の履歴**: [docs/adr/](docs/adr/)

## ⚙️ セットアップ (Setup)

```bash
task setup
cp .env.example .env
uv sync
```

## 📊 実行 (Execution)

```bash
task run:newalphasearch  # アルファ探索開始っ！
task view                # ダッシュボードを見るっ！
```

---

*ハーネスエンジニアリングに基づき、このREADMEは最小限に保たれています。詳細は[ADR-001](file:///home/kafka/finance/investor/docs/adr/001-harness-engineering-adoption.md)を見てねっ！✨*