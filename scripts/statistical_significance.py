import json
import numpy as np
from sklearn.utils import resample
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, matthews_corrcoef

def run_significance_test():
    print("Running Statistical Significance & Bootstrap Analysis on AAARTS Results...")
    
    # Load the full quantitative report
    try:
        with open("logs/bench/full_quantitative_report.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print("Error: logs/bench/full_quantitative_report.json not found.")
        return
        
    details = data["earnings_forecast"]["details"]
    y_true = np.array([item["actual"] for item in details])
    y_pred = np.array([item["predicted"] for item in details])
    
    n_samples = len(y_true)
    print(f"Total evaluated samples: {n_samples}")
    
    # Calculate point estimates
    point_accuracy = accuracy_score(y_true, y_pred)
    point_precision = precision_score(y_true, y_pred, zero_division=0)
    point_recall = recall_score(y_true, y_pred, zero_division=0)
    point_f1 = f1_score(y_true, y_pred, zero_division=0)
    point_mcc = matthews_corrcoef(y_true, y_pred)
    
    print("\nPoint Estimates:")
    print(f"  - Accuracy:  {point_accuracy:.2%}")
    print(f"  - Precision: {point_precision:.2%}")
    print(f"  - Recall:    {point_recall:.2%}")
    print(f"  - F1-Score:  {point_f1:.2%}")
    print(f"  - MCC:       {point_mcc:.4f}")
    
    # Bootstrap resampling
    n_bootstraps = 2000
    boot_acc = []
    boot_prec = []
    boot_rec = []
    boot_f1 = []
    boot_mcc = []
    
    np.random.seed(42)
    for _ in range(n_bootstraps):
        indices = resample(np.arange(n_samples))
        y_true_b = y_true[indices]
        y_pred_b = y_pred[indices]
        
        boot_acc.append(accuracy_score(y_true_b, y_pred_b))
        boot_prec.append(precision_score(y_true_b, y_pred_b, zero_division=0))
        boot_rec.append(recall_score(y_true_b, y_pred_b, zero_division=0))
        boot_f1.append(f1_score(y_true_b, y_pred_b, zero_division=0))
        boot_mcc.append(matthews_corrcoef(y_true_b, y_pred_b))
        
    # Calculate 95% Confidence Intervals
    ci_acc = (np.percentile(boot_acc, 2.5), np.percentile(boot_acc, 97.5))
    ci_prec = (np.percentile(boot_prec, 2.5), np.percentile(boot_prec, 97.5))
    ci_rec = (np.percentile(boot_rec, 2.5), np.percentile(boot_rec, 97.5))
    ci_f1 = (np.percentile(boot_f1, 2.5), np.percentile(boot_f1, 97.5))
    ci_mcc = (np.percentile(boot_mcc, 2.5), np.percentile(boot_mcc, 97.5))
    
    print("\n95% Confidence Intervals (Bootstrap, N=2000):")
    print(f"  - Accuracy:  [{ci_acc[0]:.2%}, {ci_acc[1]:.2%}]")
    print(f"  - Precision: [{ci_prec[0]:.2%}, {ci_prec[1]:.2%}]")
    print(f"  - Recall:    [{ci_rec[0]:.2%}, {ci_rec[1]:.2%}]")
    print(f"  - F1-Score:  [{ci_f1[0]:.2%}, {ci_f1[1]:.2%}]")
    print(f"  - MCC:       [{ci_mcc[0]:.4f}, {ci_mcc[1]:.4f}]")
    
    # Naive baseline comparison (always predicting 1, which represents majority class)
    majority_class = 1 if np.sum(y_true) > n_samples / 2 else 0
    y_naive = np.full(n_samples, majority_class)
    
    naive_accuracy = accuracy_score(y_true, y_naive)
    naive_f1 = f1_score(y_true, y_naive, zero_division=0)
    
    print(f"\nNaive Majority Baseline (Class {majority_class}):")
    print(f"  - Accuracy:  {naive_accuracy:.2%}")
    print(f"  - F1-Score:  {naive_f1:.2%}")
    
    # Calculate p-value via Permutation Test for Accuracy
    n_permutations = 10000
    p_hits = 0
    for _ in range(n_permutations):
        y_pred_permuted = np.random.permutation(y_pred)
        permuted_acc = accuracy_score(y_true, y_pred_permuted)
        if permuted_acc >= point_accuracy:
            p_hits += 1
    p_val_acc = (p_hits + 1) / (n_permutations + 1)
    
    print(f"\nPermutation Test (N={n_permutations}):")
    print(f"  - p-value (Accuracy vs Random Guess): {p_val_acc:.5f}")
    
    # Write statistical report
    report = {
        "samples": n_samples,
        "metrics": {
            "accuracy": {"value": point_accuracy, "ci": list(ci_acc)},
            "precision": {"value": point_precision, "ci": list(ci_prec)},
            "recall": {"value": point_recall, "ci": list(ci_rec)},
            "f1": {"value": point_f1, "ci": list(ci_f1)},
            "mcc": {"value": point_mcc, "ci": list(ci_mcc)}
        },
        "permutation_test": {
            "p_value_accuracy": p_val_acc
        },
        "baselines": {
            "naive_majority": {
                "class": int(majority_class),
                "accuracy": naive_accuracy,
                "f1": naive_f1
            }
        }
    }
    
    with open("logs/bench/statistical_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print("\nStatistical report saved to logs/bench/statistical_report.json")

if __name__ == "__main__":
    run_significance_test()
