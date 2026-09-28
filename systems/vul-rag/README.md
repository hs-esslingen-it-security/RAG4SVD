# Vul-RAG

This repository is an adapted copy of the original [Vul-RAG implementation](https://github.com/KnowledgeRAG4LLMVulD/KnowledgeRAG4LLMVulD/tree/main/VUL-RAG).


```bibtex
@article{10.1145/3797277,
    author = {Du, Xueying and Zheng, Geng and Wang, Kaixin and Zou, Yi and Wang, Yujia and Deng, Wentai and Feng, Jiayi and Liu, Mingwei and Chen, Bihuan and Peng, Xin and Ma, Tao and Lou, Yiling},
    title = {Vul-RAG: Enhancing LLM-based Vulnerability Detection via Knowledge-level RAG},
    year = {2026},
    publisher = {Association for Computing Machinery},
    volume = {35},
    number = {10},
    doi = {10.1145/3797277},
    journal = {ACM Trans. Softw. Eng. Methodol.},
    articleno = {312},
    numpages = {25}
}
```

**Vul-RAG**: is a vulnerability detection tool based on LLMs that incorporates RAG to improve detection accuracy. It mainly consists of three core components: knowledge extraction, vulnerability detection, and result evaluation.

## 📁 Directory Structure

```
/
├── README.md                   # Project description document
├── vul-rag-rep.yml             # ✨ Updated project dependencies
├── data/                       # Dataset directory
│   ├── test/                   # Test dataset
│   └── train/                  # Training dataset
├── vulnerability_knowledge/    # Vulnerability knowledge
├── output/                     # Output directory
│   ├── detect/                 # Detection results
│   │   ├── metrics/            # Evaluation metrics
│   │   └── ...                 # Detection result files
├── src/                        # Source code directory
│   ├── baseline_detect.py      # Baseline vulnerability detection script
│   ├── evaluate_result.py      # Result evaluation script
│   ├── extract_knowledge.py    # Knowledge extraction/generation script
│   └── vulnerability_detect.py # Main vulnerability detection script
└── utils/                      # Utility scripts directory
|   ├── bm25_retriever.py       # BM25 retrieval module
|   └── llm_client.py           # ✨ Updated LLM client interface (huggingface)
├── eval_vulrag_detect.sh       # ✨ Script to automate detection
├── generate_knowledge.sh       # ✨ Script to automate knowledge generation
```


## Dependencies
> **_NOTE:_** initial dependencies updated; can be found in ``vul-rag-rep.yml``

Python version 3.12 <br>
CUDA 12.4

You can install the dependencies via conda using the following command:
```bash
conda env create --file vul-rag-rep.yml
```

All experiments were conducted on a high-performance computing cluster. 
Experiments were executed on NVIDIA L40S 48GB (for experiments with models with up to 16B parameters) or up to eight NVIDIA H100 80GB SXM5 GPUs.

## Operational Notes 
### Data, file, and directory naming conventions
The code assumes JSON files follow a strict naming pattern:
- training / knowledge-generation files: `*_data.json`
- benchmark/testset files: `*_testset.json`
- generated knowledge files: `*_knowledge.json`
- result files: `<DATASET>_result_<MODEL>__sum-<SUMMARY_MODEL>.json`

The extraction pipeline also normalizes filenames by stripping `_data` or `_testset` before writing knowledge files, so the expected output name is derived automatically from the input file.

### Model registration and environment options
Model names must be present in `_MODEL_DICT_LLM` in `utils/llm_client.py`. The scripts do not validate the model name before launching generation; they assume this registry is up to date.

### Knowledge base locations
There are several knowledge-base conventions:
- default knowledge directory: `vulnerability_knowledge`
- model-specific knowledge directory: `add_vulnerability_knowledge/<MODEL_NAME>/`
- PrimeVul benchmark knowledge directory: `vulnerability_knowledge_primevul_qwen14b`

Knowledge generation and detection are decoupled. A generated knowledge base can be reused across multiple evaluation runs, but the script must be pointed to the correct directory and file name.

### Script differences and when to use each one
The project includes multiple detection entry points and they are not interchangeable:
- `src/vulnerability_detect.py`: standard detection pipeline for Linux-kernel-style runs
- `src/vulnerability_detect_dynamic_testset.py`: dynamic testset flow with `--input_dir` and `--knowledge_dir`
- `src/vulnerability_detect_benchmark.py`: benchmark-oriented flow with `--knowledge_base_dir` and PrimeVul dataset handling
- `eval_vulrag_detect.sh`: wrapper for the standard detection pipeline
- `eval_vulrag_detect_dynamic_testset.sh`: wrapper for dynamic testset evaluation
- `detect_benchmark.sh`: wrapper for benchmark-style PrimeVul datasets



## Running Evaluations
Run commands from the `systems/vul-rag` directory with the project environment activated. Model names must be registered in `_MODEL_DICT_LLM` in `utils/llm_client.py`.


### Detection
We re-implemented parts of the `llm_client.py` to use HuggingFace Transformers (instead of OPENAI/Replicate API keys). In addition, we separated model use: you can use different models for detection, summarization, and knowledge generation. 
To add models, update `_MODEL_DICT_LLM` in `utils/llm_client.py`. Otherwise, choose a model from the dictionary (`<_MODEL_DICT_LLM model name>`, e.g., qwq-32b).

Start vulnerability detection as follows:

```bash
python src/vulnerability_detect.py \
      --input_file_name linux_kernel_CWE-401_testset.json \
      --output_file_name linux_kernel_CWE-401_result.json \
      --knowledge_file_name linux_kernel_CWE-401_knowledge.json \
      --model_name qwq-32b \
      --summary_model_name qwq-32b \
      --resume \
      --retrieval_top_k 20 \
      --thread_pool_size 1 \
      --early_return \
      --model_settings "temperature=0.01" \
      --max_knowledge 3
```


This command uses the extracted knowledge base to detect vulnerabilities in the test dataset and saves the detection results to the specified output file. Parameter descriptions:
- `--input_file_name`: Input test dataset file name.
- `--output_file_name`: Output detection result file name.
- `--knowledge_file_name`: Knowledge base file name used.
- `--knowledge_dir`: Directory containing knowledge JSONs (default: `vulnerability_knowledge`). PrimeVul Paired in `vulnerability_knowledge_primevul_qwen14b`.
- `--model_name`: LLM model name used for detection.
- `--summary_model_name`: LLM model name used for generating summary function information for retrieval.
- `--retrieval_top_k`: Number of Top-K retrieval results.
- `--thread_pool_size`: Thread pool size for parallel processing.
- `--resume`: If an existing detection result file exists, resume processing from it.
- `--model_settings`: LLM model setting parameters.
- `--early_return`: Return early if a clear solution behavior is found.
- `--max_knowledge`: Maximum number of knowledge entries to use.
- `--retrieve_by_code`: Whether to use only code for knowledge retrieval and detection.


To run several datasets sequentially, use a shell loop. Each invocation starts after the previous one finishes:
```bash
for DATASET in primevul_CWE-119 primevul_CWE-120; do
  python src/vulnerability_detect.py \
    --input_file_name "${DATASET}_testset.json" \
    --output_file_name "${DATASET}_result.json" \
    --knowledge_file_name "${DATASET}_knowledge.json" \
    --knowledge_base_dir vulnerability_knowledge_primevul_qwen14b \
    --model_name qwen2.5-coder-14b-instruct \
    --summary_model_name qwen2.5-coder-14b-instruct \
    --retrieval_top_k 20 \
    --thread_pool_size 1 \
    --resume \
    --early_return \
    --model_settings "temperature=0.01" \
    --max_knowledge 3
done
```

Alternatively, start with the default values via command line using the `eval_vulrag_detect.sh` script:
```bash
bash eval_vulrag_detect.sh <MODEL_NAME> <SUMMARY_MODEL_NAME> [KNOWLEDGE_MODEL]
```

The use of `[KNOWLEDGE_MODEL]` requires that a knowledge base using this model has been generated prior (see Knowledge Extraction).


### Calculate Evaluation Metrics
To calculate evaluation metrics for the detection results and save the evaluation results to the output directory, run (this is already implemented within `eval_vulrag_detect.sh`):

```bash
python src/evaluate_result.py --input_files $(ls -F output/detect | grep -v '/$')
```
Parameter descriptions:
- `--input_files`: List of input detection result files.
- `--baseline`: Whether to calculate baseline evaluation metrics.


### Knowledge Extraction
The original Vul-RAG implementation leveraged GPT-3.5-turbo-0125 to extract high-level vulnerability knowledge from the top-10 CVEs in the benchmark's training set. The extracted knowledge for each CWE is stored in ``./vulnerability knowledge``.

```bash
python src/extract_knowledge.py \
    --input_file_name linux_kernel_CWE-20_data.json \
    --model_name qwq-32b \
    --thread_pool_size 1 \
    --model_settings "temperature=0.01" \
    --resume
```

This command extracts vulnerability-related knowledge from the training dataset and saves it to the specified output file. Parameter descriptions:
- `--input_file_name`: Input training dataset file name.
- `--model_name`: Name of the LLM model used.
- `--thread_pool_size`: Thread pool size for parallel processing.
- `--resume`: If an existing knowledge base file exists, resume processing from it.
- `--model_settings`: LLM model setting parameters.


> **_NOTE:_** when re-generating knowledge, it is stored in `add_vulnerability_knowledge/{args.model_name}/{args.input_file_name}`. To use this model-specific knowledge in detection, pass the model name as a third argument to the evaluation scripts (e.g., `bash eval_vulrag_detect.sh <MODEL> <SUMMARY_MODEL> <KNOWLEDGE_MODEL>`).


📊 The raw benchmark results are stored in `benchmark_results_vulrag/`.


_____

## Evaluating Knowledge Retrieval Quality
This analysis evaluates how effectively Vul-RAG retrieves vulnerability knowledge that is aligned with the vulnerability type of the query.
For each query, the source function is first transformed into a high-level functional summary by the selected summary model. Retrieval then follows the Vul-RAG pipeline using three parallel BM25 retrievers over **Purpose**, **Function**, and **Code**, followed by rank-based fusion.

### Sampled Probes
- PairVul — the original Vul-RAG test distribution
- PrimeVul — a PrimeVul probe restricted to the CWE categories covered by the Vul-RAG knowledge base

The sampling scripts are:
```text
src/sample_kb.py
src/sample_kb_retrieval.py
```

### Retrieval Metrics
Retrieval relevance is defined through CWE agreement between the query and the retrieved knowledge item.

- *CWE-Hit@k*: Percentage of queries where at least one of the top-k retrieved documents belongs to the same CWE as the query.
- *CWE-MRR* (Mean Reciprocal Rank): The average of the reciprocal ranks of the first relevant CWE match.

### Retrieval Configurations

| Configuration | Query probe | Knowledge base | Knowledge generator / variant | Knowledge directory |
|---|---|---|---|---|
| `pairvul` | PairVul | Original PairVul KB | Original Vul-RAG KB | `vulnerability_knowledge/` |
| `primevul` | PrimeVul | PrimeVul KB | Qwen2.5-Coder-14B | `add_vulnerability_knowledge/primevul-qwen2.5-coder-14b-instruct/` |
| `primevul_pairvul` | PrimeVul | Original PairVul KB | Original Vul-RAG KB | `vulnerability_knowledge/` |
| `pairvul_primevul` | PairVul | PrimeVul KB | Qwen2.5-Coder-14B | `add_vulnerability_knowledge/primevul-qwen2.5-coder-14b-instruct/` |
| `pairvul_oracle` | PairVul | Oracle PairVul KB | Qwen2.5-Coder-14B | `add_vulnerability_knowledge/oracle-qwen2.5-coder-14b-instruct/` |
| `primevul_primevul_oracle` | PrimeVul | Oracle PrimeVul KB | Qwen2.5-Coder-14B | `add_vulnerability_knowledge/primevul-oracle-qwen2.5-coder-14b-instruct/` |
| `primevul_qcoder3b` | PrimeVul | PairVul-derived KB | Qwen2.5-Coder-3B | `add_vulnerability_knowledge/qwen2.5-coder-3b-instruct/` |
| `pairvul_qcoder3b` | PairVul | PairVul-derived KB | Qwen2.5-Coder-3B | `add_vulnerability_knowledge/qwen2.5-coder-3b-instruct/` |
| `primevul_qcoder14b` | PrimeVul | PairVul-derived KB | Qwen2.5-Coder-14B | `add_vulnerability_knowledge/qwen2.5-coder-14b-instruct/` |
| `pairvul_qcoder14b` | PairVul | PairVul-derived KB | Qwen2.5-Coder-14B | `add_vulnerability_knowledge/qwen2.5-coder-14b-instruct/` |
| `primevul_qcoder32b` | PrimeVul | PairVul-derived KB | Qwen2.5-Coder-32B | `add_vulnerability_knowledge/qwen2.5-coder-32b-instruct/` |
| `pairvul_qcoder32b` | PairVul | PairVul-derived KB | Qwen2.5-Coder-32B | `add_vulnerability_knowledge/qwen2.5-coder-32b-instruct/` |

```text
PairVul probe
  input:     data/test_original_sampled
  manifest:  data/original_test_sampling_log.txt

PrimeVul probe
  input:     data/test_primevul_sampled
  manifest:  data/primevul_sampled_pairs_manifest.txt
```


The main entry point is `src/evaluate_retrieval_quality.py`. A retrieval evaluation can be run directly as follows:

```bash
python src/evaluate_retrieval_quality.py \
  --summary-model <SUMMARY_MODEL> \
  --knowledge-dir <KNOWLEDGE_DIR> \
  --input-dir <INPUT_DIR> \
  --manifest <MANIFEST> \
  --summary-output <SUMMARY_OUTPUT> \
  --output-json <METRICS_OUTPUT>
```

Each run produces two primary artifacts:
- Detailed Metrics (metrics_*.json): A full audit trail containing the ground truth, exact KB items retrieved at each rank, and granular hit/miss flags.
- Judge Summaries (summaries_*.json): A collection of source code paired with generated summaries, formatted for "LLM-as-a-Judge" quality assessment.



_____


## Dataset / Benchmark 
Vul-RAG uses a custom benchmark based on Linux Kernel CVEs, enriched with more vulnerability information. The full dataset encompasses 4667 vulnerable and patched code function pairs across 2174 CVEs. For Vul-RAG, the authors focused on the top-10 CWEs within the dataset. The specific data fields in the benchmark contain the following information for each vulnerability:

- **CVE ID**: The unique identifier assigned to a reported vulnerability in the Common Vulnerabilities and Exposures (CVE).
- **CVE Description**: A detailed description of the vulnerability provided by the CVE system, including the manifestation of the vulnerability, potential impact, and the environment in which the vulnerability may occur.
- **CWE ID**: The Common Weakness Enumeration identifier that categorizes the type of vulnerability exploits.
- **Vulnerable Code**: The source code snippet containing the vulnerability that requires patching, which will be modified in the commit.
- **Patched Code**: The source code snippet that has been committed to fix the vulnerability in the vulnerable code.
- **Patch Diff**: A detailed line-level difference between the vulnerable and patched code, consisting of added and deleted lines.

The vulnerable and patched code pairs from the top-10 CWE categories were divided into a training set and a test set. The training set was utilized to construct the vulnerability knowledge base, while the test set was for experimental evaluation. The training set contains 1154 CVEs with 2317 pairs of vulnerable and patched code snippets, while the test set includes 420 CVEs with 586 pairs.
