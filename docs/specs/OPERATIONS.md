# プロジェクト運用リファレンス

本ファイルには、特定のタスク遂行時に人間および Claude にとって有用な運用の詳細、コマンドの一覧、設定ガイドを含む。これらは恒久的な文脈に含める必要はない。

## コマンド

すべてのコマンドはリポジトリのルートから [Task](https://taskfile.dev/) により実行される。

```bash
task deps                    # Install bun + dashboard dependencies
task check                   # format + lint (alias: task qa)
task qa:fast                 # lint only
task run                     # Full run: newalphasearch + orchestrate + benchmark
task run:newalphasearch       # Autonomous alpha search loop (default 3 cycles)
task run:quick               # proof-layers + verify + discover + benchmark + verification-plot
task view                    # Start API server (:8787) + dashboard (:5173)
```

### 環境変数によるアルファ探索ループの制御
```bash
ALPHA_LOOP_MAX_CYCLES=5 task run:newalphasearch       # run N cycles
ALPHA_LOOP_SLEEP_SEC=10 task run:newalphasearch:loop  # sleep between cycles
UQTL_NL_INPUT="..." task run:newalphasearch:nl        # natural language input
```

### 個別パイプライン段階
```bash
task pipeline:orchestrate    # Full orchestrated pipeline (bun run start)
task pipeline:verify         # API/data provider verification
task pipeline:discover       # Factor discovery (alpha mining experiments)
task pipeline:benchmark      # Backtest core
task pipeline:mine           # Mining core
task pipeline:verification-plot  # Generate verification JSON + 4-panel PNG
task pipeline:edinet-daily   # EDINET daily flow (features → macro → KB → gated backtest)
```

## J-Quants キャッシュの事前ロード
```bash
task jquants:warm-all:start  # Start background cache warm job
task jquants:warm-all:status
task jquants:warm-all:log
task jquants:warm-all:stop
```

## 環境変数

- `/.env` — APIキー: `JQUANTS_API_KEY`, `ESTAT_APP_ID`, `VERIFY_TARGETS`
- `ts-agent/src/config/default.yaml` — 実行時設定の全て

## 検証成果物
正常な実行は `/mnt/d/investor_all_cached_data/` に成果物を出力する。
1. `logs/unified/alpha_discovery_*.json`
2. `outputs/standard_verification_data.json`
3. `outputs/VERIF_*.png`