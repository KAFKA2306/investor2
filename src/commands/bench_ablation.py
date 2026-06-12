import argparse
import json
import os
import pandas as pd
from tqdm import tqdm
from src.io.edinet_bench import load_earnings_forecast
import openai
from sklearn.metrics import accuracy_score, f1_score
import backoff

# AAARTS Ablation Study Evaluator 🧪
# どのデータが「予測」に効いているかを切り分けるよっ！ ✨

@backoff.on_exception(backoff.expo, (openai.RateLimitError, openai.APITimeoutError, openai.APIError), max_tries=5)
def system_predict_ablation(row, mode):
    """
    モードに応じて入力データを制限して推論するよっ！ ✨
    """
    client = openai.OpenAI(
        api_key=os.environ["OPENAI_API_KEY"],
        base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        timeout=60.0
    )
    
    # モードに応じた情報のフィルタリング ✂️
    financials = f"Financial Summary: {row.get('summary', '')}\nBS: {row.get('bs', '')}\nPL: {row.get('pl', '')}\nCF: {row.get('cf', '')}"
    texts = f"Qualitative Texts: {row.get('text', '')}"
    
    if mode == "financials_only":
        input_data = financials
    elif mode == "texts_only":
        input_data = texts
    else: # combined (standard)
        input_data = f"{financials}\n{texts}"

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
        model=os.getenv("OPENAI_MODEL", "gpt-4o"),
        messages=[
            {"role": "system", "content": "You are a professional financial auditor."},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"}
    )
    
    result = json.loads(response.choices[0].message.content)
    return int(result["prediction"])

def run_ablation(samples=20):
    print(f"🎀 AAARTS Ablation Study (Samples: {samples}) 🎀")
    df = load_earnings_forecast("test").head(samples)
    
    modes = ["financials_only", "texts_only", "combined"]
    ablation_results = {}

    for mode in modes:
        print(f"\n🧪 Testing Mode: {mode}")
        y_true = []
        y_pred = []
        
        for _, row in tqdm(df.iterrows(), total=len(df)):
            predicted = system_predict_ablation(row, mode)
            actual = int(row['label'])
            y_true.append(actual)
            y_pred.append(predicted)
        
        acc = accuracy_score(y_true, y_pred)
        f1 = f1_score(y_true, y_pred, zero_division=0)
        ablation_results[mode] = {"accuracy": acc, "f1": f1}
        print(f"   Accuracy: {acc:.2%}, F1: {f1:.2f}")

    # 結果の保存 📥
    os.makedirs("logs/bench", exist_ok=True)
    with open("logs/bench/ablation_study.json", "w", encoding="utf-8") as f:
        json.dump(ablation_results, f, ensure_ascii=False, indent=2)
    
    print(f"\n💖 Ablation study complete! Results saved to logs/bench/ablation_study.json 🌈✨")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=int, default=20)
    args = parser.parse_args()
    run_ablation(samples=args.samples)
