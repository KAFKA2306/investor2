import argparse
import json
import os
from typing import Any

import backoff
import dotenv
import openai
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    matthews_corrcoef,
    precision_score,
    recall_score,
    roc_auc_score,
)
from tqdm import tqdm

from src.commands.bench_contract import (
    INDUSTRY_LABELS,
    parse_benchmark_prediction,
    require_benchmark_model,
)
from src.io.edinet_bench import (
    load_earnings_forecast,
    load_fraud_detection,
    load_industry_prediction_frozen,
)

# Load environment variables from .env file
dotenv.load_dotenv()

# System Benchmark Evaluator (NeurIPS Rebuttal Edition)
# Focuses on probability outputs and Japanese-market-specific contexts (PBR reforms, etc.).


@backoff.on_exception(
    backoff.expo,
    (openai.RateLimitError, openai.APITimeoutError, openai.APIError),
    max_tries=5,
)
def system_predict(row, task: str, model: str):
    client = openai.OpenAI(
        api_key=os.environ["OPENAI_API_KEY"],
        base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        timeout=60.0,
    )

    if task == "industry_prediction":
        prompt_instruction = (
            "Identify the company's industry from the following options: " + ", ".join(INDUSTRY_LABELS) + "."
        )
        response_type = "string (one of the options above)"
        prob_desc = "Confidence score (0.0 to 1.0)"
    else:
        prompt_instruction = f"""Perform the task: {task}.
        Binary Classification: 1 (True/Increase), 0 (False/Decrease).
        Focus on Japanese-specific narratives:
        1. PBR reforms and Tokyo Stock Exchange (TSE) capital efficiency directives.
        2. Shareholder return plans (buybacks, dividends).
        3. Labor shortages and logistics bottlenecks unique to Japan.
        4. Cross-shareholding divestments."""
        response_type = "0 or 1"
        prob_desc = "Probability of the positive class (1) being correct (0.0 to 1.0)"

    prompt = f"""Task: {task}
Instruction: {prompt_instruction}
Company: {row.get("meta", "Unknown")}
Financial Summary: {row.get("summary", "")}
Balance Sheet: {row.get("bs", "")}
Profit & Loss: {row.get("pl", "")}
Cash Flow: {row.get("cf", "")}

Return your answer in the following JSON format:
{{
  "prediction": {response_type},
  "probability": {prob_desc},
  "reasoning": "detailed explanation based on numerical evidence and Japanese-market-specific narratives"
}}
"""

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a professional financial auditor and quant analyst specializing in the Japanese "
                    "equity market. Always provide numeric evidence from the data."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
    )

    content = response.choices[0].message.content
    if content is None:
        raise ValueError("benchmark model returned no message content")
    return parse_benchmark_prediction(content, task)


def load_evaluation_frame(task_name: str, num_samples: int):
    if num_samples < 1:
        raise ValueError("num_samples must be at least 1")

    if task_name == "fraud_detection":
        frame = load_fraud_detection("test").sort_values("doc_id")
        label_col = "label"
        evidence: dict[str, Any] = {
            "split_name": "official_test",
            "source_dataset": "SakanaAI/EDINET-Bench",
            "source_config": "fraud_detection",
        }
    elif task_name == "earnings_forecast":
        frame = load_earnings_forecast("test").sort_values("doc_id")
        label_col = "label"
        evidence = {
            "split_name": "official_test",
            "source_dataset": "SakanaAI/EDINET-Bench",
            "source_config": "earnings_forecast",
        }
    elif task_name == "industry_prediction":
        frame, frozen_evidence = load_industry_prediction_frozen("frozen_evaluation")
        label_col = "industry"
        evidence = dict(frozen_evidence)
    else:
        raise ValueError(f"Unknown task: {task_name}")

    selected = frame.head(num_samples).copy()
    if len(selected) != num_samples:
        raise ValueError(
            f"requested {num_samples} benchmark rows but frozen split contains only {len(selected)}; "
            "partial evaluation is not accepted implicitly"
        )
    evidence.update(
        {
            "available_count": len(frame),
            "requested_samples": num_samples,
            "evaluated_count": len(selected),
            "evaluated_doc_ids": selected["doc_id"].astype(str).tolist(),
            "selection_order": "frozen_manifest_order" if task_name == "industry_prediction" else "doc_id_ascending",
        }
    )
    return selected, label_col, evidence


def run_benchmark(task_name: str, num_samples: int = 50):
    model = require_benchmark_model()
    print(f"\nRunning Enhanced Quantitative Benchmark: {task_name} (Samples: {num_samples}, Model: {model})")
    frame, label_col, evaluation = load_evaluation_frame(task_name, num_samples)
    evaluation["model"] = model
    evaluation["base_url"] = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

    y_true = []
    y_pred = []
    y_prob = []
    results = []

    for _, row in tqdm(frame.iterrows(), total=len(frame)):
        prediction_obj = system_predict(row, task_name, model)

        actual = row[label_col]
        predicted = prediction_obj["prediction"]
        probability = prediction_obj["probability"]

        y_true.append(actual)
        y_pred.append(predicted)
        y_prob.append(probability)

        results.append(
            {
                "doc_id": row["doc_id"],
                "actual": actual,
                "predicted": predicted,
                "probability": probability,
                "reasoning": prediction_obj["reasoning"],
            }
        )

    metrics: dict[str, float] = {"accuracy": float(accuracy_score(y_true, y_pred))}

    if task_name != "industry_prediction":
        metrics.update(
            {
                "precision": float(precision_score(y_true, y_pred, zero_division=0)),
                "recall": float(recall_score(y_true, y_pred, zero_division=0)),
                "f1": float(f1_score(y_true, y_pred, zero_division=0)),
                "mcc": float(matthews_corrcoef(y_true, y_pred)),
            }
        )
        if len(set(y_true)) > 1:
            metrics["roc_auc"] = float(roc_auc_score(y_true, y_prob))

    print(f"\nQuantitative Results for {task_name}")
    print(f"  - Evaluation split: {evaluation['split_name']}")
    print(f"  - Model: {evaluation['model']}")
    print(f"  - Accuracy:  {metrics['accuracy']:.2%}")
    if "precision" in metrics:
        print(f"  - Precision: {metrics['precision']:.2%}")
        print(f"  - Recall:    {metrics['recall']:.2%}")
        print(f"  - F1-Score:  {metrics['f1']:.2%}")
        print(f"  - MCC:       {metrics['mcc']:.4f}")
        if "roc_auc" in metrics:
            print(f"  - ROC-AUC:   {metrics['roc_auc']:.4f}")

    return results, metrics, evaluation


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--task",
        choices=["fraud_detection", "earnings_forecast", "industry_prediction", "all"],
        default="all",
    )
    parser.add_argument("--samples", type=int, default=50)
    args = parser.parse_args()

    print("Real System Benchmarking Mode (NeurIPS Rebuttal)")

    tasks = ["fraud_detection", "earnings_forecast", "industry_prediction"] if args.task == "all" else [args.task]

    final_report = {}
    for task in tasks:
        results, metrics, evaluation = run_benchmark(task, args.samples)
        final_report[task] = {
            "evaluation": evaluation,
            "metrics": metrics,
            "details": results,
        }

    os.makedirs("logs/bench", exist_ok=True)
    report_path = f"logs/bench/enhanced_report_{args.task}.json"
    with open(report_path, "w", encoding="utf-8") as output:
        json.dump(final_report, output, ensure_ascii=False, indent=2)

    print(f"\nEvidence generated. Full report saved to {report_path}")


if __name__ == "__main__":
    main()
