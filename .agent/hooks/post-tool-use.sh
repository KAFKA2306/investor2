#!/bin/bash

# ==============================================================================
# PostToolUseHook: Full Quality Pipeline (Format → Lint → Architecture)
# ==============================================================================
# Pipeline:
# 1. Auto-format with Biome (fixes 40-50% of issues)
# 2. Lint with Biome (detects style/logic violations)
# 3. Architecture check with ast-grep (enforces layer boundaries)
# 4. CDD check (prevents defensive code patterns)

HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENHANCED_HOOK="$HOOK_DIR/post-tool-use-enhanced.mjs"

if [ ! -f "$ENHANCED_HOOK" ]; then
  echo "❌ ERROR: post-tool-use-enhanced.mjs not found at $ENHANCED_HOOK"
  exit 1
fi

node "$ENHANCED_HOOK"
exit $?
