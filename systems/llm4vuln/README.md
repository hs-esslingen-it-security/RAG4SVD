# LLM4Vuln

This repository is an adapted copy of the  [artifacts](https://anonymous.4open.science/r/LLM4Vuln) available for "LLM4Vuln: A Unified Evaluation Framework for Decoupling and Enhancing LLMs' Vulnerability Reasoning"

```bibtex
@preprint{sunLLM4VulnUnifiedEvaluation2024,
    title={LLM4Vuln: A Unified Evaluation Framework for Decoupling and Enhancing LLMs' Vulnerability Reasoning}, 
    author={Yuqiang Sun and Daoyuan Wu and Yue Xue and Han Liu and Wei Ma and Lyuye Zhang and Yang Liu and Yingjiu Li},
    year={2025},
    eprint={2401.16185},
    archivePrefix={arXiv},
    primaryClass={cs.CR},
    url={https://arxiv.org/abs/2401.16185}
}
```

## 📁 Project Structure
```
|- LLM4Vuln         // Source code of the artifact
| |- dataloader         // Data loader for different language dataset
| |- dataset            // Dataset for different language
| |- evaluator          // Evaluator for different language
| | |- prompt           // Prompt schemes
| |- ext                // External tools to build call graph for Java source code
| |- knowledge          // Knowledge retrieval for different language
| |- knowledge_db       // Knowledge base for different language
| |- models             // Usage of different LLMs
| |- reported_results   // Original Output of the evaluation
| |- private_types      // Definition of data types used in LLM4Vuln
| |- scripts            // Scripts to generate dataset and evaluate the model
| |- config.py          // Configuration file, contains API keys (deprecated)
| |- main.py            // Entry point of the artifact
|- poetry.lock     // Lock file of the Python dependencies
|- pyproject.toml  // Project configuration file
```

### Evaluation Data
All the original output of the experiments were moved to the `LLM4Vuln/reported_results` directory.
`<language>.json` contains the evaluation results for different LLMs on different prompt schemes.
`<language>.complex.json` contains the intermediate results of the evaluation, including the prompt and raw answer from LLMs.
`<language>.tex` contains the LaTeX table for the evaluation results (Table 3 and Table 4 in the paper).

_____
_____


## Setup and Dependencies
> **_NOTE:_** Updated dependencies (conda environment) in ``requirements.yml``

From the original study:
#### **Runtime Environment**

- Ubuntu 20.04
- Python 3.10
- Java 17

The hardware configuration:
- Intel Xeon Gold 6248 (80)
- 200GB RAM

#### **Python Dependency**
All the Python dependencies are listed in `pyproject.toml` and `poetry.lock`.
To install the dependencies, you first need to install [`poetry`](https://python-poetry.org/), and then run the following command inside a created conda environment:

```bash
poetry install
```

> **_NOTE:_** Problems at setup with ``falcon-analyzer = {git = "XXXX-5"}``; removed the following lines in `pyproject.toml` and `poetry.lock`:
```
[[package]]
name = "falcon-analyzer"
version = "0.2.28"
description = "Falcon is a Solidity static analysis framework written in Python 3."
optional = false
python-versions = ">=3.8"
files = []
develop = false

  
[package.dependencies]
crytic-compile = "0.3.3"
networkx = ">=2.5.1"
openai = ">=0.27.8"
prettytable = ">=0.7.2"
pysha3 = ">=1.0.2"
z3-solver = "4.11.2.0"

  
[package.extras]
dev = ["black (==22.3.0)", "deepdiff", "numpy", "pylint (>=2.13.4)", "pytest", "pytest-cov", "solc-select (>=v1.0.0b1)"]


[package.source]
type = "git"
url = "XXXX-5"
reference = "HEAD"
resolved_reference = "5fe4a4a9c5ada4aaa7ad72aaf63ab4654dd0da36"
```

> **_NOTE:_** ``LangChainDeprecationWarning: As of langchain-core 0.3.0, LangChain uses pydantic v2 internally. The langchain_core.pydantic_v1 module was a compatibility shim for pydantic v1, and should no longer be used. Please update the code to import from Pydantic directly.
For example, replace imports like: `from langchain_core.pydantic_v1 import BaseModel` with: `from pydantic import BaseModel` or the v1 compatibility namespace if you are working in a code base that has not been fully upgraded to pydantic 2 yet: `from pydantic.v1 import BaseModel` ``


#### **Java Dependency**
⚠️ This step is not necessary if you only want to reproduce the results.
These dependencies are only needed if you want to generate the dataset from the source code, by running `LLM4Vuln/scripts/generate_java_dataset_from_csv.py`.

- Java 17
- Gradle 8.8
- Kotlin 1.9.22

Run the following command inside `LLM4Vuln/ext/cg_llm4vuln` to build the tool, and the jar file will be generated in `LLM4Vuln/ext/cg_llm4vuln/build/libs/cg_llm4vuln-1.0-SNAPSHOT.jar`:

```bash
./gradrew jar
```


## Usage
### Datasets 💾
Testing: <br>
**Java**: 46 pairs (working through 2576 possible items/prompt combinations) <br> 
**C/C++**: 50 pairs (working through 2800 possible items/prompt combinations)

Knowledge Base: <br>
**Java**: 770 entries <br>
**C/C++**: 860 entries

### Configurations ⚙️

> 🚨 **Implementation Notes**
>
> - We re-implemented parts of the repo to use Hugging Face Transformers instead of OpenAI/Replicate API keys.
> - We only evaluate on Java and C/C++ (smart contracts/solidity out of scope) in the **<CoT, without context & summarizes RAG setting>** (commented out the other schemes etc. in `scheme.supported, knowledge_type.supported, context.supported` in the `init` files in `evaluator/prompt/` to fasten prompt builder)


### Run the script
To run the script, you should first activate the virtual environment 
> **_NOTE:_** conda environment llm4vuln: ``conda activate llm4vuln``

Then, change to the `LLM4Vuln` directory.
> **_NOTE:_** the new huggingface-version requires up to 4 different models! (i) the main `detection LLM`, (ii) a `summary LLM`, which summarizes the code under detection for knowledge retrieval (e.g., use detection LLM), (iii) the `embedding model` used with the knowledge retrieval (DEFAULT given, codebert-base), and (iv) the `ground-truth LLM` used for evaluating model responses. Each model is intatiated only once (by name)

> **_NOTE:_** The original implementation used OPENAI embeddings for the knowlegde database (faiss). Therefore, we had to extract the contents of the original knowledge bases (`/knowledge_db/parse_pkl.py`) and rebuild the database with open-source embeddings. We support the building-process with different embedding models (see script `/knowledge_db/rebuild_faiss_from_pkl.py`). As a result, the knowledge base needs to be loaded for the specific embedding model (and pre-build for new embedding models) -- adjusted path to knowledge base in data loaders, respectively.


##### Model defaults:
- embedding: codebert-base


#### Run LLM4Vuln Vulnerability Detection

For this study, LLM4Vuln is evaluated both on its original Java & C/C++ dataset and on PrimeVul Paired.
The main pipeline supports configurable detection, summarization, embedding, and ground-truth/judge models (see `models/utils_model.py` for the model identifier).

##### Detection
The main entry point is `main.py`.
For the PrimeVul Paired C/C++ evaluation, run:

```bash
python main.py \
  --model <vulnerability detection model> \
  --summary <summary model> \
  --embedding <embedding model> \
  --gt <ground-truth / judge model> \
  --output <filename> \
  --primevul
```

##### Retrieval
How well does knowledge "match" the query/ Does the generated knowledge enable effective retrieval?

- We sampled 50 vulnerability pairs from PrimeVul that mirror the exact CWE distribution of the UniVul (original LLM4Vuln) test set. Since original test files lacked CWE labels, we performed a canonical mapping using the NVD API (v2.0) and PrimeVul metadata to bridge every CVE to its corresponding CWE category.
- Code snippets are first summarized into high-level functional descriptions via the summary LLM
- Retrieval uses CodeBERT embeddings and FAISS similarity search


We evaluate retrieval quality based on CWE-Agreement:

> *CWE-Hit@k*: Percentage of queries where at least one of the top-k retrieved documents belongs to the same CWE as the query.

> *CWE-MRR* (Mean Reciprocal Rank): The average of the reciprocal ranks of the first relevant CWE match.


The evaluation generates two primary artifacts:

- Detailed Metrics (metrics_*.json): A full audit trail containing the ground truth, exact KB items retrieved at each rank, and granular hit/miss flags.
- Judge Summaries (summaries_*.json): A collection of source code paired with generated summaries, formatted for "LLM-as-a-Judge" quality assessment.

Retrieval quality is evaluated with:
```bash
python scripts/evaluate_retrieval_quality.py \
  --query-mode function \
  --summary-model <summary model> \
  --embedding <embedding model> \
  --input-dir <input dir> \
  --manifest <manifest files> \
  --summary-output <"outputs/summary/....json"> \
  --output-json <"outputs/kb_retrieval/....json">
```

Original (UniVul) input directory and manifest paths:
```bash
INPUT_DIR="dataset/cpp"
MANIFEST="dataset/original_cpp_cwe_map.json"
```

PrimeVul input directory and manifest paths:
```bash
INPUT_DIR="dataset/cpp_primevul_sampled_univul_dist"
MANIFEST="dataset/primevul_sampled_univul_dist_manifest.txt"
```

##### Summary
Generated summaries are evaluated separately with the LLM-as-a-Judge pipeline:

```bash
python scripts/judge_score_summary_quality.py \
  --input-dir "outputs/summary/to_evaluate" \
  --output-dir "outputs/summary/eval_<model>" \
  --judge-model <model>
```

_____


## Extending LLM4Vuln to other languages or LLMs
### ➕ Add a new language
To add a new language, you need to implement the following classes:
- `LLM4Vuln/dataloader/<your language>/loader.py`: Data loader for the dataset of the new language.
- `LLM4Vuln/dataset/<your language>`: Dataset for the new language.
- `LLM4Vuln/knowledge/<your language>/loader.py`: Knowledge retrieval for the new language.
- `LLM4Vuln/knowledge_db/<your language>`: Knowledge base for the new language.

Do remember to add them to the corresponding `__init__.py` files.

### ➕ Add a new LLM
To add a new LLM, you need to adjust the following files:
- `LLM4Vuln/models/utils_model.py`: Huggingface specifications of the new LLM.
- `LLM4Vuln/models/__init__.py`: Add your LLM to the list.

