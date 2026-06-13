import argparse
import json
import os

import backoff
import dotenv
import openai
from sklearn.metrics import accuracy_score, f1_score, matthews_corrcoef, precision_score, recall_score, roc_auc_score
from tqdm import tqdm

from src.io.edinet_bench import load_earnings_forecast, load_fraud_detection, load_industry_prediction

# Load environment variables from .env file
dotenv.load_dotenv()

# System Benchmark Evaluator (NeurIPS Rebuttal Edition)
# Focuses on probability outputs and Japanese-market-specific contexts (PBR reforms, etc.).


@backoff.on_exception(backoff.expo, (openai.RateLimitError, openai.APITimeoutError, openai.APIError), max_tries=5)
def system_predict(row, task):
    client = openai.OpenAI(
        api_key=os.environ["OPENAI_API_KEY"],
        base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        timeout=60.0,
    )

    if task == "industry_prediction":
        prompt_instruction = "Identify the company's industry from the following options: 銀行, 電機・精密, 自動車・輸送機, 運輸・物流, 電気・ガス・エネルギー資源, 不動産, 機械, 鉄鋼・非鉄, 素材・化学, 金融(除く銀行), 食品, 建設・資材, 商社・卸売, 情報通信・サービスその他, 医薬品, 小売."
        response_type = "string (one of the options above)"
        prob_desc = "Confidence score (0.0 to 1.0)"
    else:
        # Add Japanese market-specific context to the prompt
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
        model=os.getenv("OPENAI_MODEL", "gpt-4o"),
        messages=[
            {
                "role": "system",
                "content": "You are a professional financial auditor and quant analyst specializing in the Japanese equity market. Always provide numeric evidence from the data.",
            },
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
    )

    content = response.choices[0].message.content
    try:
        result = json.loads(content)
        pred = result["prediction"]
        prob = float(result.get("probability", 0.5))
        if task != "industry_prediction":
            pred = int(pred)
        return {"prediction": pred, "probability": prob, "reasoning": result["reasoning"]}
    except Exception as e:
        print(f"Failed to parse LLM response: {content}")
        raise e


def run_benchmark(task_name, num_samples=50):
    print(f"\nRunning Enhanced Quantitative Benchmark: {task_name} (Samples: {num_samples})")

    if task_name == "fraud_detection":
        df = load_fraud_detection("test").head(num_samples)
        label_col = "label"
    elif task_name == "earnings_forecast":
        df = load_earnings_forecast("test").head(num_samples)
        label_col = "label"
    elif task_name == "industry_prediction":
        df = load_industry_prediction("train").head(num_samples)
        label_col = "industry"
    else:
        raise ValueError(f"Unknown task: {task_name}")

    y_true = []
    y_pred = []
    y_prob = []
    results = []

    for _, row in tqdm(df.iterrows(), total=len(df)):
        prediction_obj = system_predict(row, task_name)

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

    # 定量的指標の算出
    metrics = {"accuracy": accuracy_score(y_true, y_pred)}

    if task_name != "industry_prediction":
        # Binary classification metrics
        metrics.update(
            {
                "precision": precision_score(y_true, y_pred, zero_division=0),
                "recall": recall_score(y_true, y_pred, zero_division=0),
                "f1": f1_score(y_true, y_pred, zero_division=0),
                "mcc": matthews_corrcoef(y_true, y_pred),
            }
        )
        # Calculate ROC-AUC if possible (requires both classes to be present)
        if len(set(y_true)) > 1:
            metrics["roc_auc"] = roc_auc_score(y_true, y_prob)

    print(f"\nQuantitative Results for {task_name}")
    print(f"  - Accuracy:  {metrics['accuracy']:.2%}")
    if "precision" in metrics:
        print(f"  - Precision: {metrics['precision']:.2%}")
        print(f"  - Recall:    {metrics['recall']:.2%}")
        print(f"  - F1-Score:  {metrics['f1']:.2%}")
        print(f"  - MCC:       {metrics['mcc']:.4f}")
        if "roc_auc" in metrics:
            print(f"  - ROC-AUC:   {metrics['roc_auc']:.4f}")

    return results, metrics


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--task", choices=["fraud_detection", "earnings_forecast", "industry_prediction", "all"], default="all"
    )
    parser.add_argument("--samples", type=int, default=50)
    args = parser.parse_args()

    print("Real System Benchmarking Mode (NeurIPS Rebuttal)")

    tasks = ["fraud_detection", "earnings_forecast", "industry_prediction"] if args.task == "all" else [args.task]

    final_report = {}
    for task in tasks:
        results, metrics = run_benchmark(task, args.samples)
        final_report[task] = {"metrics": metrics, "details": results}

    os.makedirs("logs/bench", exist_ok=True)
    report_path = f"logs/bench/enhanced_report_{args.task}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(final_report, f, ensure_ascii=False, indent=2)

    print(f"\nEvidence generated. Full report saved to {report_path}")


if __name__ == "__main__":
    main()
