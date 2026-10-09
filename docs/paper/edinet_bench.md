# EDINET-Bench

**Paper:** *EDINET-Bench: Evaluating LLMs on Complex Financial Tasks using Japanese Financial Statements*  
**arXiv:** https://arxiv.org/abs/2506.08762  
**OpenReview:** https://openreview.net/forum?id=Dxns0cj15A  
**Official repository:** https://github.com/SakanaAI/EDINET-Bench  
**Official dataset:** https://huggingface.co/datasets/SakanaAI/EDINET-Bench

EDINET-Bench is an open Japanese financial benchmark built from EDINET annual reports. It evaluates three distinct tasks: Accounting Fraud Detection, Earnings Forecast, and Industry Prediction. The paper constructs the benchmark from annual reports covering the preceding ten years and publishes the dataset, construction code, and evaluation code.

## Released benchmark

The current public Hugging Face release contains 2,585 rows across the three task configurations.

| Task | Public train | Public test | Target |
| --- | ---: | ---: | --- |
| Fraud Detection | 865 | 224 | Binary fraud / non-fraud classification |
| Earnings Forecast | 549 | 451 | Binary next-year earnings increase / not-increase classification |
| Industry Prediction | 496 | — | 16-class industry classification |

The public Industry Prediction configuration currently exposes only a `train` split. A repository-defined split may be useful for experiments, but it is a surrogate and must not be presented as the benchmark's official test split.

The dataset notice states that the release was relicensed to Public Domain License (PDL) 1.0 on June 9, 2025 for consistency with the source-data licensing terms.

## Official logistic baseline

The upstream `src/edinet_bench/logistic.py` provides a deterministic non-LLM baseline for `fraud_detection` and `earnings_forecast` using the `summary` field:

1. Parse the JSON `summary` and flatten each metric/year pair into a numeric feature.
2. Convert `－` and null values to missing values.
3. Fill train and test missing values with the training-set numeric mean.
4. Drop training columns with at most one unique value and align test columns to training columns.
5. Standardize with `sklearn.preprocessing.StandardScaler`.
6. Fit `sklearn.linear_model.LogisticRegression()` with its default constructor arguments.
7. Report Accuracy, Precision, Recall, F1 and ROC-AUC for the binary task.

Canonical upstream code pin used by this repository:

- EDINET-Bench repository commit: `797fbb50051c14b97ee2fd88595b0a3c12432058`
- `src/edinet_bench/logistic.py` blob: `37184505cd88d4bacdfa8576778da59dd32e434c`
- Hugging Face dataset revision: `cf0bc74fb85cce99878f15426f8cf3ba750d0cba`

Repository reproduction entry point: `scripts/edinet_bench_logistic.py`.

## Reproduced result

The pinned reproduction completed against the public benchmark with the official summary-only preprocessing and default logistic model.

| Task | Accuracy | F1 | ROC-AUC | Features after preprocessing |
| --- | ---: | ---: | ---: | ---: |
| Fraud Detection | 0.5848 | 0.5939 | 0.6761 | 110 |
| Earnings Forecast | 0.5676 | 0.6678 | 0.5612 | 105 |

Canonical evidence: `docs/research/results/edinet_bench_logistic/summary.json`.

These values are the repository's reproduction of the official logistic reference under the pinned code/data/environment contract. They are not AAARTS performance.

## Frontier boundary

Reproducing the official logistic baseline establishes a benchmark reference only. It is not an AAARTS candidate and is not a paper-family `BEAT`, `TIE`, or `LOSE` result. A direct frontier verdict requires an AAARTS method evaluated on the same frozen task contract and compared against the preregistered EDINET-Bench capability metric.

For Industry Prediction, direct comparison remains blocked until the evaluation split used for the claim is frozen explicitly and distinguished from the public release, which currently has no official test split.