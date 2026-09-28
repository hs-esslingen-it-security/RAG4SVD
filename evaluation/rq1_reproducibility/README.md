# RQ1 — Reproducibility

This directory contains the artifacts for **RQ1: To what extent are published open-source RAG4SVD systems reproducible?**

We reproduce the reported open-weight configurations of **SVD-Bench, Llama-VD, LLM4Vuln, and Vul-RAG** under the original system-specific datasets and evaluation settings.
Each experiment is repeated three times where applicable. We compare the reproduced mean against the originally reported result using the absolute relative deviation:

$$
\mathrm{Deviation} =
\frac{|\mathrm{Reproduced} - \mathrm{Reported}|}
     {|\mathrm{Reported}|}
\times 100
$$

Deviations are interpreted as:
- **< 1%:** reproducible
- **1–5%:** weakly reproducible
- **> 5%:** not reproducible


## LLM4Vuln Open-Weight Model Substitution

The original LLM4Vuln pipeline relies on proprietary models for intermediate pipeline components (summary generation, ground-truth check). To enable reproduction in an open-weight setting, we replace these components with open-weight alternatives.
We select the substitutes through a dedicated model ablation, evaluating the most capable candidate models (*summary: qwen2.5-coder-3b-instruct, qwen3-4b-instruct; gt: qwen2.5-14b-instruct, gemma-3-27b-it*) with respect to their ability to reliably complete the corresponding pipeline stage and produce correctly parseable outputs. 

The ablation considers generation failures, parsing failures, and downstream output validity rather than selecting substitutes solely based on final detection performance.

| Language | Detect Model | Summary Model | GT Model | Generation Errors | Parsing Errors | GT Errors |
|---|---|---|---|---:|---:|---:|
| **C/C++** | phi-3-mini-128k | qwen2.5-coder-3b-instruct | qwen2.5-14b-instruct | 35 | 5 | 1 |
|  | phi-3-mini-128k | qwen2.5-coder-3b-instruct | gemma-3-27b-it | 1 | 0 | 0 |
|  | phi-3-mini-128k | qwen3-4b-instruct | qwen2.5-14b-instruct | 33 | 1 | 0 |
|  | phi-3-mini-128k | qwen2.5-14b-instruct | qwen2.5-14b-instruct | 36 | 5 | 1 |
|  | phi-3-mini-128k | qwen3-4b-instruct | gemma-3-27b-it | 2 | 0 | 0 |
| **Java** | phi-3-mini-128k | qwen2.5-coder-3b-instruct | qwen2.5-14b-instruct | 6 | 5 | 0 |
|  | phi-3-mini-128k | qwen2.5-coder-3b-instruct | gemma-3-27b-it | 4 | 10 | 0 |
|  | phi-3-mini-128k | qwen3-4b-instruct | qwen2.5-14b-instruct | 6 | 2 | 0 |
|  | phi-3-mini-128k | qwen2.5-14b-instruct | qwen2.5-14b-instruct | 1 | 5 | 2 |
|  | phi-3-mini-128k | qwen3-4b-instruct | gemma-3-27b-it | 8 | 11 | 0 |


Based on this analysis, we use:

- **Summary model:** `Qwen3-4B`
- **LLM-as-a-Judge / ground-truth model:** `Gemma-3-27B`


## Results / Files
- [`full_results.pdf`](./full_results.pdf) — full RQ1 results, including individual runs, mean values, and standard deviations.
- [`results_rep.csv`](./results_rep.csv) — machine-readable reported and reproduced mean results used to compute deviations and generate the reproducibility figure.

<br>

> **Note:** LLM4Vuln results should be interpreted as a reproduction under open-weight model substitution rather than an exact rerun of the original proprietary-model configuration.