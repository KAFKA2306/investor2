from __future__ import annotations

import unittest

from src.commands.bench_contract import (
    parse_ablation_prediction,
    parse_benchmark_prediction,
    require_benchmark_model,
)


class BenchmarkContractTest(unittest.TestCase):
    def test_requires_explicit_model(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "OPENAI_MODEL must be set explicitly"):
            require_benchmark_model({})
        self.assertEqual(require_benchmark_model({"OPENAI_MODEL": "example/model-v1"}), "example/model-v1")

    def test_missing_probability_is_not_filled(self) -> None:
        with self.assertRaisesRegex(ValueError, "missing probability"):
            parse_benchmark_prediction(
                '{"prediction": 1, "reasoning": "numbers support the result"}',
                "earnings_forecast",
            )

    def test_probability_must_be_a_valid_number(self) -> None:
        with self.assertRaisesRegex(ValueError, "within \\[0, 1\\]"):
            parse_benchmark_prediction(
                '{"prediction": 1, "probability": 1.2, "reasoning": "evidence"}',
                "fraud_detection",
            )
        with self.assertRaisesRegex(TypeError, "JSON number"):
            parse_benchmark_prediction(
                '{"prediction": 1, "probability": "0.8", "reasoning": "evidence"}',
                "fraud_detection",
            )

    def test_binary_prediction_must_be_zero_or_one(self) -> None:
        with self.assertRaisesRegex(ValueError, "must be 0 or 1"):
            parse_benchmark_prediction(
                '{"prediction": 2, "probability": 0.8, "reasoning": "evidence"}',
                "earnings_forecast",
            )

    def test_industry_prediction_must_use_frozen_label_set(self) -> None:
        with self.assertRaisesRegex(ValueError, "outside the frozen label set"):
            parse_benchmark_prediction(
                '{"prediction": "made-up-sector", "probability": 0.8, "reasoning": "evidence"}',
                "industry_prediction",
            )

    def test_ablation_requires_prediction_and_reasoning(self) -> None:
        parsed = parse_ablation_prediction('{"prediction": 0, "reasoning": "evidence"}')
        self.assertEqual(parsed["prediction"], 0)
        with self.assertRaisesRegex(ValueError, "non-empty reasoning"):
            parse_ablation_prediction('{"prediction": 0, "reasoning": ""}')


if __name__ == "__main__":
    unittest.main()
