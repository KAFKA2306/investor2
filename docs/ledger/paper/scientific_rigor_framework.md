# AAARTS: Scientific Rigor & Narrative-to-Financial Verification Framework

This document outlines the architectural and methodological blueprint to transition **AAARTS** from a "Success Report Generation" paradigm to a rigorous "Truth-Seeking" scientific paradigm, addressing key structural issues in machine learning evaluation, agent validation, and empirical reproducibility.

---

## 1. Paradigm Shift: Truth-Seeking vs. Success-Reporting

AI coding and research agents are traditionally aligned to maximize user satisfaction, which introduces a severe cognitive bias: optimizing for "positive success reports" rather than "discovering empirical truth." In scientific research, this manifests as:
* **Confirmation Bias**: Actively selecting baselines and data slices that show performance improvements.
* **Benchmark Leakage**: Iteratively tuning prompt parameters or hyperparameters against the test set to hit a target metric (e.g., F1 = 0.9).
* **Falsification Absence**: Omitting detailed error analyses and standard statistical significance tests.

To establish a **Truth-Seeking Protocol**, AAARTS enforces:
1. **Separation of Concerns**: The model writing the paper draft, the agent generating trading signals, and the code evaluating performance must operate in isolated runtime contexts with zero shared memory.
2. **Explicit Falsification Objectives**: The primary objective of the verification agent is to find reasons to *reject* the generated alpha hypotheses (Null Hypothesis testing).
3. **Data Lock (Anti-Leakage Guard)**: Test splits are locked in read-only directories, and all prompt tuning must be executed strictly on the Training/Validation splits.

---

## 2. Narrative-to-Financial Consistency Verification (NFCV)

Rather than using unstructured LLM prompts to "read and evaluate" texts, AAARTS formalizes qualitative analysis through a structured accounting graph mapping textual claims to hard financial constraints.

### 2.1 Mathematical Formulation of Claims
Let a qualitative disclosure claim $C_k$ extracted from the Management's Discussion and Analysis (MD&A) section be represented as:
$$C_k = \langle \text{Type}, \text{Direction}, \delta, \tau \rangle$$
Where:
* $\text{Type} \in \{\text{Growth}, \text{Efficiency}, \text{Investment}, \text{Restructuring}, \text{Risk}\}$
* $\text{Direction} \in \{+1, -1\}$ (Positive expansion vs. contraction)
* $\delta \in (0, 1]$ (Claimed magnitude or intensity)
* $\tau \in \{T+1, T+2\}$ (Forecast horizon in fiscal years)

### 2.2 The Accounting Constraint Graph (ACG)
We define the Accounting Constraint Graph as a directed graph $G = (V, E)$ where vertices $V$ represent financial statements metrics (from Balance Sheet $BS$, Income Statement $PL$, and Cash Flow Statement $CF$), and edges $E$ represent double-entry bookkeeping and accounting relations.

For any claim $C_k$, we define a validation vector of accounting metrics $V(C_k) \subset V$. The consistency of the claim is audited against the temporal changes of these metrics:

$$\Delta M_i = M_i(T) - M_i(T-1)$$

#### Constraint Rules (Examples)
1. **Growth Claim Verification ($\text{Type} = \text{Growth}$)**:
   * If a firm claims aggressive sales growth ($\text{Direction} = +1$), we define the consistency score $S_{\text{growth}}$ as a function of the change in Accounts Receivable ($AR$) and Operating Cash Flow ($OCF$):
   * If $\Delta \text{Revenue} > 0$ but $\Delta OCF \le 0$ and $\Delta AR > \Delta \text{Revenue}$, the claim is flagged as **Speculative Noise** (Accounting Contradiction), and the hypothesis is penalized.
2. **Investment/CapEx Claim Verification ($\text{Type} = \text{Investment}$)**:
   * If a firm claims capacity expansion through equipment purchase:
   * We verify whether:
     $$\Delta \text{Property, Plant, and Equipment (PP\&E)} + \Delta \text{Capital Expenditures (CapEx)} > 0$$
   * If CapEx is declining while PP&E is flat, the qualitative claim is rejected.

### 2.3 The Consistency Score
The overall Narrative-to-Financial Consistency Score ($S_{\text{NFCV}}$) for a report is computed as:

$$S_{\text{NFCV}} = \frac{1}{|C|} \sum_{C_k \in C} \Phi(C_k, G(T))$$

Where $\Phi$ is a step function returning $1$ if the accounting constraints are satisfied, and $-1$ if a contradiction is detected. Signals with $S_{\text{NFCV}} < 0.2$ are automatically discarded from the portfolio.

---

## 3. Strict Evaluation Protocol & Statistical Significance

To prevent random benchmarking fluctuations from being interpreted as "SOTA improvements," AAARTS enforces the following mathematical gates:

### 3.1 Bootstrap Confidence Intervals
All reported metrics (Accuracy, Precision, Recall, F1) must be computed alongside their 95% Bootstrap Confidence Intervals ($CI_{95\%}$) over $B = 2000$ resamples:

$$CI_{95\%} = \left[ q_{2.5\%}(\Theta^*), q_{97.5\%}(\Theta^*) \right]$$

If the confidence intervals of the Combined model and the Numerical Baseline overlap by more than 50% of their width, the claim of "qualitative text utility" must be downgraded to "statistically marginal."

### 3.2 Hypothesis Refutation via Permutation Testing
To verify if the model has learned genuine predictive signals or is merely exploiting class imbalances, we perform a Permutation Test:
1. Shuffle the target labels $Y$ randomly $10,000$ times to generate $Y^{(p)}$.
2. Calculate the baseline accuracy distribution.
3. Compute the empirical $p$-value:
   $$p = \frac{1 + \sum_{p=1}^{N_p} \mathbb{I}(\text{Acc}(Y^{(p)}, \hat{Y}) \ge \text{Acc}(Y, \hat{Y}))}{1 + N_p}$$
4. We only accept the model's validity if $p < 0.05$.

---

## 4. Systematic Error Analysis Protocol

Every evaluation run must output a detailed breakdown of failure modes across different dimensions to identify systemic weaknesses.

| Error Type | Financial Context | Underlying Cause | Mitigation Strategy |
| :--- | :--- | :--- | :--- |
| **False Positive (Type I)** | High-growth narrative with decaying operating cash flows. | Blind acceptance of MD&A optimism without checking working capital metrics. | Tighten $S_{\text{NFCV}}$ threshold for cash-flow constraints. |
| **False Negative (Type II)** | Conservative/hedged Japanese narrative masking high core R&D yields. | Over-sensitivity to agglutinative sentence-final hedges (*"検討を進める"*). | Calibrate sentiment weightings specifically for Keigo and polite hedging structures. |
| **Industry Bias** | High error rates in financial services/banks. | Standard accounting constraints (e.g., CapEx, Inventories) do not apply to financials. | Implement industry-specific ACG templates (e.g., Net Interest Margin for banks). |
