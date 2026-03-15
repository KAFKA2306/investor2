# System Operations & Runtime Skill

金融分析システムの実行時設定、テレメトリ、品質管理に関する専門知見。

## 専門知識 (Expertise)
- **Runtime Config**: `default.yaml` と環境変数による多層的な設定管理。
- **Telemetry**: `telemetry_logger.ts` を用いた IO ログ記録と `CanonicalLog` 形式による成果物保存。
- **Quality Gate**: バックテストスコアや相関、直交性に基づくアルファ因子の品質審査基準。

## ワークフロー (Workflows)
1. **Startup**: `app_runtime_core.ts` による環境初期化、DB 接続、キャッシュウォームアップ。
2. **Execution Gate**: `quality_gate.ts` による実行前後の品質チェック。
3. **Persistance**: 分析結果の `investor.log-envelope.v2` 形式での永続化。

## 知見の継承プロセス (Knowledge Inheritance Process)
このプロジェクトでは、以下のサイクルで知見をコードから `SKILL.md` へ移管し、コードをクリーンに保つ。

1. **Discovery**: `src/experiments/` で新しいロジックやプロトタイプを試行する。
2. **Standardization**: 成功したロジックを `BaseAgent` や `UnifiedProvider` に統合する。
3. **Extraction**: 実装時に得られた「ドメイン固有の癖」「パラメータ調整のコツ」「失敗パターン」を `.agent/skills/*/SKILL.md` に文章化して残す。
4. **Pruning**: `SKILL.md` への移行が完了した、古い実験コードや重複したエージェント実装を削除する。
5. **Inheritance**: LLM はタスク実行前に `loadSkillKnowledge()` を通じてこれらの `SKILL.md` を読み込み、過去の知見を前提知識として活用する。

## ベストプラクティス
- 環境変数は `UQTL_` プレフィックスで統一し、`runtime_config.ts` で一元管理すること。
- テストデータやキャッシュは `/root/.gemini/tmp/` もしくはプロジェクトの `.cache/` に逃がし、ソースコードを汚さないこと。
- 実験的なロジックは `BaseAgent` を継承して実装し、成功したものは `SKILL.md` に知見として追加、不要なコードは削除すること。
