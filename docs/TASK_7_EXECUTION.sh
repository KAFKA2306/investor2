#!/bin/bash

# Task #7: J-Quants Data Expansion (2020-2025)
# 実行スクリプト

set -e  # Exit on error

cd /home/kafka/finance/investor2

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📡 Task #7: J-Quants Historical Data Expansion (2020-2025)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo

# Verify API key is set
if [ -z "$JQUANTS_API_KEY" ]; then
    echo "❌ Error: JQUANTS_API_KEY not set"
    echo "Set it with: export JQUANTS_API_KEY='<your_key>'"
    exit 1
fi

echo "✅ JQUANTS_API_KEY is set"
echo

# Run data sync
echo "🚀 Starting J-Quants data sync (markets + fundamental, 2020-2025)..."
echo "⏱️  Expected duration: 18 minutes to 1 hour (2,191 API calls @ 500ms/call)"
echo

export GET_MODE=jquants
bun src/io/get.ts

if [ $? -eq 0 ]; then
    echo
    echo "✨ Data sync completed successfully!"
    echo
    echo "📊 Next steps:"
    echo "  1. Verify cache: cache/sector_spillover/sector_returns.db"
    echo "  2. Run backtest: bun src/commands/sector_spillover_backtest.ts"
    echo "  3. Compare results with original 3-month data"
else
    echo
    echo "❌ Data sync failed. Check error messages above."
    exit 1
fi
