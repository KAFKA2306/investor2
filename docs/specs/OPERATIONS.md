 📖 Project Operations Reference

This file contains operational details, command lists, and setup guides that are useful for humans and Claude during specific tasks but do not need to be in the permanent context.

## 🚀 Commands

All commands run from the repo root via [Task](https://taskfile.dev/).

```bash
task deps                    # Install bun + dashboard dependencies
task check                   # format + lint (alias: task qa)
task qa:fast                 # lint only
task run                     # Full run: newalphasearch + orchestrate + benchmark
task run:newalphasearch       # Autonomous alpha search loop (default 3 cycles)
task run:quick               # proof-layers + verify + discover + benchmark + verification-plot
task view                    # Start API server (:8787) + dashboard (:5173)
```

### ⚙️ Alpha search loop controls (env vars)
```bash
ALPHA_LOOP_MAX_CYCLES=5 task run:newalphasearch       # run N cycles
ALPHA_LOOP_SLEEP_SEC=10 task run:newalphasearch:loop  # sleep between cycles
UQTL_NL_INPUT="..." task run:newalphasearch:nl        # natural language input
```

### 🏎️ Individual pipeline stages
```bash
task pipeline:orchestrate    # Full orchestrated pipeline (bun run start)
task pipeline:verify         # API/data provider verification
task pipeline:discover       # Factor discovery (alpha mining experiments)
task pipeline:benchmark      # Backtest core
task pipeline:mine           # Mining core
task pipeline:verification-plot  # Generate verification JSON + 4-panel PNG
task pipeline:edinet-daily   # EDINET daily flow (features → macro → KB → gated backtest)
```

## 🛠️ J-Quants Cache Warming
```bash
task jquants:warm-all:start  # Start background cache warm job
task jquants:warm-all:status
task jquants:warm-all:log
task jquants:warm-all:stop
```

## 🔐 Environment Variables

- `/.env` — API keys: `JQUANTS_API_KEY`, `ESTAT_APP_ID`, `VERIFY_TARGETS`
- `ts-agent/src/config/default.yaml` — All runtime configuration

## 📈 Verification Evidence
Successful runs produce artifacts in `/mnt/d/investor_all_cached_data/`:
1. `logs/unified/alpha_discovery_*.json`
2. `outputs/standard_verification_data.json`
3. `outputs/VERIF_*.png`
