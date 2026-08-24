from __future__ import annotations

import json
import math
import os
from collections.abc import Mapping
from typing import Any

INDUSTRY_LABELS = (
    "銀行",
    "電機・精密",
    "自動車・輸送機",
    "運輸・物流",
    "電気・ガス・エネルギー資源",
    "不動産",
    "機械",
    "鉄鋼・非鉄",
    "素材・化学",
    "金融(除く銀行)",
    "食品",
    "建設・資材",
    "商社・卸売",
    "情報通信・サービスその他",
    "医薬品",
    "小売",
)


def require_benchmark_model(environ: Mapping[str, str] | None = None) -> str:
    source = os.environ if environ is None else environ
    model = source.get("OPENAI_MODEL", "").strip()
    if not model:
        raise RuntimeError("OPENAI_MODEL must be set explicitly for benchmark evaluation")
    return model


def _parse_object(content: str) -> dict[str, Any]:
    if not isinstance(content, str) or not content.strip():
        raise ValueError("benchmark response content must be a non-empty JSON object")
    payload = json.loads(content)
    if not isinstance(payload, dict):
        raise TypeError("benchmark response must decode to a JSON object")
    return payload


def _require_reasoning(payload: dict[str, Any]) -> str:
    reasoning = payload.get("reasoning")
    if not isinstance(reasoning, str) or not reasoning.strip():
        raise ValueError("benchmark response must include non-empty reasoning")
    return reasoning


def _binary_prediction(payload: dict[str, Any]) -> int:
    if "prediction" not in payload:
        raise ValueError("benchmark response is missing prediction")
    raw = payload["prediction"]
    if isinstance(raw, bool):
        raise ValueError("binary prediction must be 0 or 1, not boolean")
    if raw in (0, 1, "0", "1"):
        return int(raw)
    raise ValueError(f"binary prediction must be 0 or 1, got {raw!r}")


def parse_ablation_prediction(content: str) -> dict[str, Any]:
    payload = _parse_object(content)
    return {
        "prediction": _binary_prediction(payload),
        "reasoning": _require_reasoning(payload),
    }


def parse_benchmark_prediction(content: str, task: str) -> dict[str, Any]:
    payload = _parse_object(content)
    if task == "industry_prediction":
        if "prediction" not in payload:
            raise ValueError("benchmark response is missing prediction")
        prediction = payload["prediction"]
        if prediction not in INDUSTRY_LABELS:
            raise ValueError(f"industry prediction is outside the frozen label set: {prediction!r}")
    elif task in {"fraud_detection", "earnings_forecast"}:
        prediction = _binary_prediction(payload)
    else:
        raise ValueError(f"unknown benchmark task: {task}")

    if "probability" not in payload:
        raise ValueError("benchmark response is missing probability; no fallback value is permitted")
    raw_probability = payload["probability"]
    if isinstance(raw_probability, bool) or not isinstance(raw_probability, (int, float)):
        raise TypeError("benchmark probability must be a JSON number")
    probability = float(raw_probability)
    if not math.isfinite(probability) or not 0.0 <= probability <= 1.0:
        raise ValueError(f"benchmark probability must be finite and within [0, 1], got {raw_probability!r}")

    return {
        "prediction": prediction,
        "probability": probability,
        "reasoning": _require_reasoning(payload),
    }
