from __future__ import annotations

import unittest
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from scripts import japan_equity_monitor as module


class JapanEquityMonitorTest(unittest.TestCase):
    def test_ticker_requires_dot_t(self):
        self.assertEqual(module.ensure_yahoo_ticker("9843.T"), "9843.T")
        with self.assertRaises(ValueError):
            module.ensure_yahoo_ticker("TYO:9843")
        with self.assertRaises(ValueError):
            module.ensure_yahoo_ticker("9843")

    def test_subtract_months_clamps_month_end(self):
        self.assertEqual(module.subtract_months(date(2026, 3, 31), 1), date(2026, 2, 28))
        self.assertEqual(module.subtract_months(date(2026, 1, 31), 3), date(2025, 10, 31))

    def test_yahoo_parser_and_returns_use_real_observations(self):
        start = datetime(2026, 6, 1, tzinfo=UTC)
        timestamps = [int((start.replace(day=1) + timedelta(days=i)).timestamp()) for i in range(100)]
        closes = [100.0 + i for i in range(100)]
        volumes = [1000 + i for i in range(100)]
        payload = {
            "chart": {
                "error": None,
                "result": [
                    {
                        "timestamp": timestamps,
                        "indicators": {"quote": [{"close": closes, "volume": volumes}]},
                    }
                ],
            }
        }
        observations = module.parse_yahoo_chart(payload)
        summary = module.summarize_observations(observations)
        self.assertEqual(summary["close"], 199.0)
        self.assertEqual(summary["volume"], 1099)
        self.assertEqual(summary["anchors"]["five_sessions_prior"], "2026-09-03")
        self.assertEqual(summary["anchors"]["one_month_prior"], "2026-08-08")
        self.assertEqual(summary["anchors"]["three_month_prior"], "2026-06-08")

    def test_yahoo_missing_result_fails_closed(self):
        with self.assertRaises(ValueError):
            module.parse_yahoo_chart({"chart": {"error": None, "result": []}})

    def test_shashi_parser(self):
        text = """
ROE
2026年3月期 15.3%
期間平均（10期） 11.8%
PER
2026年3月期 18.2倍
期間平均（10期） 21.4倍
PBR
2026年3月期 2.3倍
期間平均（10期） 2.1倍
営業利益率
2026年3月期 12.5%
期間平均（10期） 9.6%
当期純利益率
2026年3月期 8.4%
期間平均（10期） 6.9%
売上高
10期 CAGR 7.2%
当期純利益
10期 CAGR 9.1%
"""
        metrics = module.parse_shashi_text(text)
        self.assertEqual(metrics["roe_pct"], 15.3)
        self.assertEqual(metrics["roe_period_avg_pct"], 11.8)
        self.assertEqual(metrics["per_x"], 18.2)
        self.assertEqual(metrics["pbr_period_avg_x"], 2.1)
        self.assertEqual(metrics["sales_cagr_pct"], 7.2)
        self.assertEqual(metrics["net_income_cagr_pct"], 9.1)

    def test_watchlist_has_exact_15_unique_dot_t_tickers(self):
        path = Path(__file__).resolve().parents[1] / "config/japan_yen_watchlist.json"
        records = module.load_watchlist(path)
        self.assertEqual(len(records), 15)
        self.assertEqual(len({row["ticker"] for row in records}), 15)
        self.assertTrue(all(row["ticker"].endswith(".T") for row in records))


if __name__ == "__main__":
    unittest.main()
