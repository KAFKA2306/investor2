#!/usr/bin/env python3
"""
Backtest Stub - Minimal qlib-compatible backtest runner
Returns StandardOutcome JSON format on stdout
"""

import argparse
import json
import random
import sys


def run_backtest(factor_id: str, formula: str) -> dict:
    """
    Run minimal backtest (stub implementation)
    Future: replace with real qlib backtest
    """
    # Seed for reproducibility within a run
    random.seed(hash(factor_id + formula) % (2**32))

    # Simulate realistic backtest results
    sharpe = random.uniform(0.1, 1.5)
    ic = random.uniform(0.01, 0.08)
    max_drawdown = random.uniform(0.05, 0.50)
    p_value = random.uniform(0.01, 0.30)
    backtest_days = 252

    return {
        "sharpe": round(sharpe, 4),
        "ic": round(ic, 4),
        "max_drawdown": round(max_drawdown, 4),
        "p_value": round(p_value, 4),
        "factor_id": factor_id,
        "backtest_days": backtest_days,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backtest stub")
    parser.add_argument("--factor_id", required=True, help="Factor ID")
    parser.add_argument("--formula", required=True, help="Factor formula")

    args = parser.parse_args()

    result = run_backtest(args.factor_id, args.formula)
    json.dump(result, sys.stdout)
    sys.stdout.write("\n")
