import argparse
import json
import os
import pandas as pd
from tqdm import tqdm
from src.io.edinet_bench import load_fraud_detection, load_earnings_forecast, load_industry_prediction
import openai
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, matthews_corrcoef

import argparse
import json
import os
import pandas as pd
from tqdm import tqdm
from src.io.edinet_bench import load_fraud_detection, load_earnings_forecast, load_industry_prediction
import openai
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, matthews_corrcoef
import backoff

# System Benchmark Evaluator 🎀
# 全てのベンチマークタスクを定量評価するための最強ツールだよっ！ ✨

@backoff.on_exception(backoff.expo, (openai.RateLimitError, openai.APITimeoutError, openai.APIError), max_tries=5)
def system_predict(row, task):
    """
    OpenAI API を使って本物の推論を実行するよっ！ ✨
    """
    client = openai.OpenAI(
        api_key=os.environ["OPENAI_API_KEY"],
        base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        timeout=60.0 # 1分でタイムアウトさせるよっ！
    )
    
    if task == "industry_prediction":
        prompt_instruction = "Identify the company's industry from the following options: 銀行, 電機・精密, 自動車・輸送機, 運輸・物流, 電気・ガス・エネルギー資源, 不動産, 機械, 鉄鋼・非鉄, 素材・化学, 金融(除く銀行), 食品, 建設・資材, 商社・卸売, 情報通信・サービスその他, 医薬品, 小売."
        response_type = "string (one of the options above)"
    else:
        prompt_instruction = f"Perform the task: {task}. Binary Classification: 1 (True/Increase), 0 (False/Decrease)."
        response_type = "0 or 1"

    prompt = f"""Task: {task}
Instruction: {prompt_instruction}
Company: {row.get('meta', 'Unknown')}
Financial Summary: {row.get('summary', '')}
Balance Sheet: {row.get('bs', '')}
Profit & Loss: {row.get('pl', '')}
Cash Flow: {row.get('cf', '')}

Return your answer in the following JSON format:
{{
  "prediction": {response_type},
  "reasoning": "detailed explanation based on the evidence"
}}
"""

    response = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o"),
        messages=[
            {"role": "system", "content": "You are a professional financial auditor and quant analyst. Always base your prediction on specific numbers in the provided data."},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"}
    )
    
    content = response.choices[0].message.content
    try:
        result = json.loads(content)
        pred = result["prediction"]
        # Convert to int for binary tasks
        if task != "industry_prediction":
            pred = int(pred)
        return {
            "prediction": pred,
            "reasoning": result["reasoning"]
        }
    except Exception as e:
        print(f"Failed to parse LLM response: {content}")
        raise e

def run_benchmark(task_name, num_samples=50):
    print(f"\n🚀 Running Quantitative Benchmark: {task_name} (Samples: {num_samples})")
    
    if task_name == "fraud_detection":
        df = load_fraud_detection("test").head(num_samples)
        label_col = 'label'
    elif task_name == "earnings_forecast":
        df = load_earnings_forecast("test").head(num_samples)
        label_col = 'label'
    elif task_name == "industry_prediction":
        df = load_industry_prediction("train").head(num_samples) # Industry prediction typically uses train for eval in this bench
        label_col = 'industry'
    else:
        raise ValueError(f"Unknown task: {task_name}")

    y_true = []
    y_pred = []
    results = []
    
    for _, row in tqdm(df.iterrows(), total=len(df)):
        prediction_obj = system_predict(row, task_name)
        
        actual = row[label_col]
        predicted = prediction_obj['prediction']
        
        y_true.append(actual)
        y_pred.append(predicted)
            
        results.append({
            "doc_id": row['doc_id'],
            "actual": actual,
            "predicted": predicted,
            "reasoning": prediction_obj['reasoning']
        })

    # 定量的指標の算出
    metrics = {
        "accuracy": accuracy_score(y_true, y_pred)
    }
    
    if task_name != "industry_prediction":
        # Binary classification metrics
        metrics.update({
            "precision": precision_score(y_true, y_pred, zero_division=0),
            "recall": recall_score(y_true, y_pred, zero_division=0),
            "f1": f1_score(y_true, y_pred, zero_division=0),
            "mcc": matthews_corrcoef(y_true, y_pred)
        })

    print(f"\n✨ Quantitative Results for {task_name} ✨")
    print(f"  - Accuracy:  {metrics['accuracy']:.2%}")
    if "precision" in metrics:
        print(f"  - Precision: {metrics['precision']:.2%}")
        print(f"  - Recall:    {metrics['recall']:.2%}")
        print(f"  - F1-Score:  {metrics['f1']:.2%}")
        print(f"  - MCC:       {metrics['mcc']:.4f}")
    
    return results, metrics

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", choices=["fraud_detection", "earnings_forecast", "industry_prediction", "all"], default="all")
    parser.add_argument("--samples", type=int, default=50)
    args = parser.parse_args()

    print("🎀 Real System Benchmarking Mode (Full Quantitative) 🎀")
    
    tasks = ["fraud_detection", "earnings_forecast", "industry_prediction"] if args.task == "all" else [args.task]
    
    final_report = {}
    for task in tasks:
        results, metrics = run_benchmark(task, args.samples)
        final_report[task] = {
            "metrics": metrics,
            "details": results
        }

    os.makedirs("logs/bench", exist_ok=True)
    report_path = "logs/bench/full_quantitative_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(final_report, f, ensure_ascii=False, indent=2)
    
    print(f"\n💖 Evidence generated! Full report saved to {report_path} 🌈✨")

if __name__ == "__main__":
    main()
