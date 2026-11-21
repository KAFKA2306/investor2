---
type: "index"
description: "investor2の研究・仕様・論文・データソースに関する文書の唯一の台帳。"
tags:
  - investor2/ledger
generated:
  by: openai/chatgpt
  at: "2026-11-21"
---

# 文書台帳

文書の正本はこのフォルダに集約する。研究用JSON・CSV・凍結済み証拠は既存の場所に残し、文書と実データを混同しない。

- [投資判断の正準フロー](architecture/canonical-investment-flow.md)
- [研究の入口](research/README.md)
- [論文の比較](paper/benchmark_comparison.md)
- [データの来歴と再利用](specs/external_snapshot_store.md)
- [外部データソース](data-sources/market-universe.md)
- [分析用Spark/Iceberg投影](analytics/README.md)
- [判断スナップショットの契約](decision-ledger/README.md)
- [構造上の判断記録](adr/005-modular-external-data-sources.md)

標準の操作入口としてリポジトリ直下の `README.md`・`AGENTS.md`、スキル定義の `SKILL.md` は残す。文書の新規作成・更新は `docs/ledger/` に置く。[移設記録 #460](https://github.com/KAFKA2306/investor2/issues/460)。
