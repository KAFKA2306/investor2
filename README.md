# AAARTS: 自律進化型アルファ探索システム 🚀

## 🌸 はじめにっ！ (Introduction)

AAARTS (Autonomous Agentic Alpha Trade System) は、研究から執行までを一つの「知能」として統合したクオンツスタックだよっ！このファイルはエージェントちゃんのための「ポインタ」として設計されてるから、詳しい設計図は下のリンクを見てねっ！

## 🗺️ だいじなポインタ (Key Pointers)

- **設計図（シーケンス）**: [sequence.md](file:///home/kafka/finance/investor/docs/diagrams/sequence.md)
- **設計図（フロー）**: [simpleflowchart.md](file:///home/kafka/finance/investor/docs/diagrams/simpleflowchart.md)
- **運用ルール**: [AGENTS.md](file:///home/kafka/finance/investor/AGENTS.md)
- **決定の履歴**: [ADR一覧](file:///home/kafka/finance/investor/docs/adr/)
- **過去のREADME**: [ARCHIVE.md](file:///home/kafka/finance/investor/docs/archive/README_LEGACY.md)

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