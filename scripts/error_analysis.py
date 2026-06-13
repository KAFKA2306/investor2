import json
import os
import pandas as pd
import numpy as np

def run_error_analysis():
    print("Running Systematic Error Analysis on AAARTS Predictions...")
    
    report_path = "logs/bench/full_quantitative_report.json"
    if not os.path.exists(report_path):
        print(f"Error: {report_path} not found.")
        return
        
    with open(report_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    details = data["earnings_forecast"]["details"]
    
    false_positives = []
    false_negatives = []
    true_positives = []
    true_negatives = []
    
    for item in details:
        actual = item["actual"]
        predicted = item["predicted"]
        doc_id = item["doc_id"]
        reasoning = item.get("reasoning", "")
        
        entry = {
            "doc_id": doc_id,
            "actual": actual,
            "predicted": predicted,
            "reasoning_snippet": reasoning[:300] + "..." if len(reasoning) > 300 else reasoning
        }
        
        if actual == 1 and predicted == 1:
            true_positives.append(entry)
        elif actual == 0 and predicted == 0:
            true_negatives.append(entry)
        elif actual == 0 and predicted == 1:
            false_positives.append(entry)
        elif actual == 1 and predicted == 0:
            false_negatives.append(entry)
            
    total = len(details)
    fp_rate = len(false_positives) / total
    fn_rate = len(false_negatives) / total
    tp_rate = len(true_positives) / total
    tn_rate = len(true_negatives) / total
    
    print(f"\nError Rate Breakdown (Total Samples: {total}):")
    print(f"  - True Positives (TP):  {len(true_positives)} ({tp_rate:.2%})")
    print(f"  - True Negatives (TN):  {len(true_negatives)} ({tn_rate:.2%})")
    print(f"  - False Positives (FP): {len(false_positives)} ({fp_rate:.2%}) -> Crucial for Risk Management")
    print(f"  - False Negatives (FN): {len(false_negatives)} ({fn_rate:.2%})")
    
    # Analyze reasoning in False Positives (Why did the agent fail?)
    print("\n--- FALSE POSITIVE ANALYSIS ---")
    print(f"Analyzing {len(false_positives)} instances where AAARTS predicted earnings INCREASE but actual was DECREASE:")
    for i, fp in enumerate(false_positives[:3]):
        print(f"\n[{i+1}] Doc ID: {fp['doc_id']}")
        print(f"Reasoning snippet: {fp['reasoning_snippet']}")
        
    # Analyze reasoning in False Negatives
    print("\n--- FALSE NEGATIVE ANALYSIS ---")
    print(f"Analyzing {len(false_negatives)} instances where AAARTS predicted earnings DECREASE but actual was INCREASE:")
    for i, fn in enumerate(false_negatives[:3]):
        print(f"\n[{i+1}] Doc ID: {fn['doc_id']}")
        print(f"Reasoning snippet: {fn['reasoning_snippet']}")
        
    # Save the error analysis report
    analysis_report = {
        "summary": {
            "total_samples": total,
            "true_positives": len(true_positives),
            "true_negatives": len(true_negatives),
            "false_positives": len(false_positives),
            "false_negatives": len(false_negatives),
            "false_positive_rate": fp_rate,
            "false_negative_rate": fn_rate
        },
        "false_positives": false_positives,
        "false_negatives": false_negatives
    }
    
    os.makedirs("logs/bench", exist_ok=True)
    out_path = "logs/bench/error_analysis_report.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(analysis_report, f, ensure_ascii=False, indent=2)
        
    print(f"\nError analysis report successfully saved to {out_path}")

if __name__ == "__main__":
    run_error_analysis()
