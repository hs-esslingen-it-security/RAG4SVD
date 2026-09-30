# RQ3: Component Analysis

This directory contains the experiments and full results for RQ3.
The evaluation is organized around the main components of the vulnerability-detection pipeline:

1. **Input abstraction** — quality of the generated source-code summaries;
2. **Knowledge retrieval** — effectiveness of retrieving relevant vulnerability knowledge;
3. **Detection** — effect of the available knowledge on downstream vulnerability-detection performance.


Where applicable, complete per-configuration results are provided as CSV files to support reproduction and additional analysis.

## 📁 Directory Structure

```text
rq3_components/
├── summary_judge_evaluation/
│   ├── llm4vuln/
│   │   ├── eval_gpt-oss-120b/
│   │   ├── eval_qwen2.5-32b-instruct/
│   │   ├── eval_qwq-32b/
│   │   └── summaries_to_evaluate/
│   │
│   ├── vul-rag/
│   │   ├── eval_gpt-oss-120b/
│   │   ├── eval_qwen2.5-32b-instruct/
│   │   ├── eval_qwq-32b/
│   │   └── summaries_to_evaluate/
│   │
│   ├── judge_ablation.ipynb
│   ├── llm4vuln_judge_score_summary_quality_debug.py
│   └── vulrag_judge_score_summary_quality_debug.py
│
├── knowledge_retrieval_results.csv
├── detection_knowledge_sensitivity_results.csv
├── detection_oracle_results.csv
└── README.md
```



---

<br>

## 1. Input Abstraction

Both LLM4Vuln and Vul-RAG use an LLM-generated natural-language abstraction of the source code as an intermediate representation.
RQ3 evaluates the quality of these summaries using an LLM-as-a-Judge setup.

### Summary Quality Evaluation

Each generated summary is evaluated with respect to its corresponding source code along five dimensions:

- **Faithfulness** — whether statements in the summary are supported by the source code.
- **Functional Coverage** — whether the summary captures the primary purpose and functionally important behavior.
- **Retrieval Utility** — whether the summary preserves semantic information useful for retrieving similar or vulnerability-relevant code.
- **Conciseness** — whether the summary avoids unnecessary detail and redundancy.
- **Clarity** — whether the summary is readable and unambiguous.

Each dimension is assigned an integer score from **1 to 5**, together with a short rationale.

The summaries to be evaluated are stored under `summary_judge_evaluation/<llm4vuln|vul-rag>/summaries_to_evaluate/`

Detailed judge outputs are stored separately for each judge model in `summary_judge_evaluation/<llm4vuln|vul-rag>/eval_gpt-oss-120b/`, `summary_judge_evaluation/<llm4vuln|vul-rag>/eval_qwen2.5-32b-instruct/`, and `summary_judge_evaluation/<llm4vuln|vul-rag>/eval_qwq-32b/`.


### Judge Prompt

The following prompt is used to evaluate each source-code/summary pair:

```text
You are an expert in C/C++ program analysis. The provided summary is not intended as developer documentation. It will be embedded and used to retrieve semantically similar code from a vulnerability knowledge base. Evaluate the quality of the summary with respect to the source code.
Every criterion must receive an integer score from 1 to 5 and one concise rationale. Never output "N/A", "Not applicable", or leave a score blank. If a criterion cannot reasonably be assessed, assign the lowest appropriate score (1) and explain why.

Faithfulness (1–5)
Every statement must be supported by the source code. Penalize unsupported or incorrect claims.

Functional Coverage (1–5)
Does the summary capture the primary purpose and functionally important behavior of the code? Penalize omission of major functionality or emphasis on minor implementation details.

Retrieval Utility (1–5)
If this summary were used for semantic retrieval, how well would it retrieve semantically similar implementations or vulnerability-relevant code? Reward summaries that preserve discriminative semantic information and penalize summaries that are overly generic.

Conciseness (1–5)
Does the summary remain informative while avoiding unnecessary details or redundancy?

Clarity (1–5)
Is the summary grammatically correct, easy to read, and unambiguous?

### Source Code
{code}

### Summary
{summary}

Evaluate only the quality of the summary with respect to the source code. Do not reward or penalize the summary for failing to identify a vulnerability unless that behavior is explicitly evident from the code itself.
Output exactly in this format:

Faithfulness: <score> | <rationale>
Functional Coverage: <score> | <rationale>
Retrieval Utility: <score> | <rationale>
Conciseness: <score> | <rationale>
Clarity: <score> | <rationale>
```


### BlaBlador API Evaluation

The following scripts run the summary-quality evaluation through the BlaBlador API for the GPT-oss-120B judge:

```text
llm4vuln_judge_score_summary_quality_debug.py
vulrag_judge_score_summary_quality_debug.py
```

Example for LLM4Vuln (The corresponding Vul-RAG script is invoked analogously):

```bash
python llm4vuln_judge_score_summary_quality_debug.py \
  --input-dir <summaries_to_evaluate> \
  --output-dir <summaries_evaluation> \
  --judge-model "01 - GPT-OSS-120b - an open model released by OpenAI in August 2025" \
  --sleep-between 10 \
  --api-key <API-key> \
  2>&1 | tee llm4vuln_judge.out
```

Replace `<summaries_to_evaluate>`, `<summaries_evaluation>`, and `<API-key>` with the corresponding paths and API credentials.
(For locally executed judge models, the evaluation script is provided as part of the system's source code.)


### Judge Ablation

To test whether the summary-quality results depend strongly on the selected judge model (GPT-oss-120B), the evaluation is repeated with two other judges:
- Qwen2.5-32B-Instruct
- QwQ-32B

The judge-ablation analysis is contained in `judge_ablation.ipynb`.
The notebook compares the judges using **Krippendorff's alpha** for inter-rater agreement and **mean pairwise absolute deviation** between judge scores.


---
<br>

## 2. Knowledge Retrieval

We evaluate the **knowledge-retrieval component** of Vul-RAG under different knowledge-base configurations.
The complete retrieval results are provided in `knowledge_retrieval_results.csv`.
The result table contains the retrieval configuration together with the corresponding retrieval metrics for the evaluated test sets and models.

Load via:

```python
import pandas as pd

df = pd.read_csv("knowledge_retrieval_results.csv", sep=";", decimal=",")
df.head()
```

---

<br>

## 3. Detection
We evaluate how changes to the knowledge component affect the final vulnerability-detection performance of Vul-RAG.

### Knowledge Sensitivity

`detection_knowledge_sensitivity_results.csv` contains the results of varying the knowledge base to analyze how sensitive the final detection performance is to changes in the provided knowledge.

### Oracle Knowledge

`detection_oracle_results.csv` contains the results of the oracle-knowledge experiment to provide a controlled comparison in which the detection stage is supplied with oracle knowledge, allowing the influence of detection capability to be examined separately from retrieval errors.

Load via:

```python
import pandas as pd

df_oracle = pd.read_csv("detection_oracle_results.csv", sep=";", decimal=",")
df_kb = pd.read_csv("detection_knowledge_sensitivity_results.csv", sep=";", decimal=",")
```
