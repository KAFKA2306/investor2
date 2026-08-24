import argparse
import json
import os

import backoff
import dotenv
import openai
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from tqdm import tqdm

from src.commands.bench_contract import parse_ablation_prediction, require_benchmark_model
from src.io.edinet_bench import load_earnings_forecast

# Load environment variables from .env file
dotenv.load_dotenv()

# AAARTS Ablation Study Evaluator

ABLATION_MODES = ("financials_only", "texts_only", "combined")


@backoff.on_exception(
    backoff.expo,
    (openai.RateLimitError, openai.APITimeoutError, openai.APIError),
    max_tries=5,
)
def system_predict_ablation(row, mode: str, model: str):
    if mode not in ABLATION_MODES:
        raise ValueError(f"unknown ablation mode: {mode}")

    client = openai.OpenAI(
        api_key=os.environ["OPENAI_API_KEY"],
        base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        timeout=60.0,
    )

    financials = (
        f"Financial Summary: {row.get('summary', '')}\n"
        f"BS: {row.get('bs', '')}\n"
        f"PL: {row.get('pl', '')}\n"
        f"CF: {row.get('cf', '')}"
    )
    texts = f"Qualitative Texts: {row.get('text', '')}"

    if mode == "financials_only":
        input_data = financials
    elif mode == "texts_only":
        input_data = texts
    elif mode == "combined":
        input_data = f"{financials}\n{texts}"
    else:  # pragma: no cover - guarded above; keep the branch explicit
        raise ValueError(f"unknown ablation mode: {mode}")

    prompt = f"""Task: earnings_forecast (1: Increase, 0: Decrease)
Data:
{input_data}

Return your answer in the following JSON format:
{{
  "prediction": 0 or 1,
  "reasoning": "detailed explanation based on the provided subset of data"
}}
"""

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a professional financial auditor."},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
    )

    content = response.choices[0].message.content
    if content is None:
        raise ValueError("ablation model returned no message content")
    return parse_ablation_prediction(content)["prediction"]


def run_ablation(samples: int = 20):
    if samples < 1:
        raise ValueError("samples must be at least 1")
    model = require_benchmark_model()
    print(f"AAARTS Ablation Study (Samples: {samples}, Model: {model})")
    frozen = load_earnings_forecast("test").sort_values("doc_id")
    df = frozen.head(samples).copy()
    if len(df) != samples:
        raise ValueError(
            f"requested {samples} ablation rows but frozen split contains only {len(df)}; "
            "partial evaluation is not accepted implicitly"
        )

    ablation_results = {
        "contract": {
            "model": model,
            "base_url": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            "source_dataset": "SakanaAI/EDINET-Bench",
            "source_config": "earnings_forecast",
            "split_name": "official_test",
            "samples": samples,
            "evaluated_doc_ids": df["doc_id"].astype(str).tolist(),
            "selection_order": "doc_id_ascending",
            "modes": list(ABLATION_MODES),
        },
        "results": {},
    }

    for mode in ABLATION_MODES:
        print(f"\nTesting Mode: {mode}")
        y_true = []
        y_pred = []

        for _, row in tqdm(df.iterrows(), total=len(df)):
            predicted = system_predict_ablation(row, mode, model)
            actual = int(row["label"])
            y_true.append(actual)
            y_pred.append(predicted)

        acc = float(accuracy_score(y_true, y_pred))
        prec = float(precision_score(y_true, y_pred, zero_division=0))
        rec = float(recall_score(y_true, y_pred, zero_division=0))
        f1 = float(f1_score(y_true, y_pred, zero_division=0))

        ablation_results["results"][mode] = {
            "accuracy": acc,
            "precision": prec,
            "recall": rec,
            "f1": f1,
        }
        print(f"   Accuracy: {acc:.2%}, Precision: {prec:.2%}, Recall: {rec:.2%}, F1: {f1:.4f}")

    os.makedirs("logs/bench", exist_ok=True)
    with open("logs/bench/ablation_study.json", "w", encoding="utf-8") as f:
        json.dump(ablation_results, f, ensure_ascii=False, indent=2)

    print("\nAblation study complete. Results saved to logs/bench/ablation_study.json")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=int, default=20)
    args = parser.parse_args()
    run_ablation(samples=args.samples)
