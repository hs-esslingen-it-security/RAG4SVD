# VulTriage: Triple-Path Context Augmentation for  LLM-Based Vulnerability Detection

This repository is an **adapted copy** of the original [VulTriage repository](https://github.com/vinsontang1/VulTriage).

    ```bibtex
    @preprint{tang2026vultriagetriplepathcontextaugmentation,
        title={VulTriage: Triple-Path Context Augmentation for LLM-Based Vulnerability Detection}, 
        author={Wenxin Tang and Xiang Zhang and Junliang Liu and Jingyu Xiao and Xi Xiao and Jinlong Yang and Yuehe Ma and Zhenyu Liu and Zhengheng Li and Zicheng Wang and Wang Luo and Qing Li and Lei Wang and Peng Xiangli},
        year={2026},
        eprint={2605.09461},
        archivePrefix={arXiv},
        primaryClass={cs.AI},
        url={https://arxiv.org/abs/2605.09461}, 
    }
    ```

VulTriage is an intelligent vulnerability detection framework based on GPT-4o and BGE-M3 models, combining:
- **Static Structure Analysis**: Control Flow Graphs (CFG), Data Flow Graphs (DFG), Abstract Syntax Trees (AST)
- **Retrieval-Augmented Generation (RAG)**: Vulnerability pattern matching based on CWE knowledge base
- **Code Understanding**: Semantic analysis using Large Language Models
- **Paired/Single-sample Detection**: Support for multiple evaluation modes





## System Requirements

- Python >= 3.9
- CUDA (optional, for GPU acceleration)

### Install Dependencies
> 🚨 Updated dependencies in `environment.yml` and `requirements.txt`
```bash
conda create -y -n vultriage python=3.10
conda activate vultriage

conda install pytorch torchvision torchaudio pytorch-cuda=12.4 -c pytorch -c nvidia
pip install -r requirements.txt
```


## Run Vulnerability Detection

For this study, we adapted the original VulTriage implementation to support fully local inference with Hugging Face Transformers.

> 🚨 **Implementation notes**
>
> - We translated all comments to English.
> - We re-implemented the logic of `main.py` and `hyperparam_exp.py` to use Hugging Face Transformers instead of OpenAI API keys.
> - For this study, we evaluate the standard VulTriage pipeline with its full functionality enabled (`--wotask all --jsonl_file primevul_test_paired.jsonl`).
> - We added `main_resume.py` to support checkpointing and resuming interrupted runs.

The recommended entry point is: `main_resume.py`

Two model configurations are supported:
- **single-model** (same model used for all pipeline component: `--model`)
- Separate models for detection (`--detection_model`), summarization (`--summary_model`), and retrieval (`--rag_model`)

Example: 
```bash
python main_resume.py \
  --model qwen2.5-coder-14b-instruct \
  --checkpoint_file output/checkpoint_qwen2.5-coder-14b-instruct.jsonl \
  --metrics_file output/metrics_qwen2.5-coder-14b-instruct.txt
```

Runs can be resumed from an existing checkpoint by adding `--resume`. The same checkpoint file must be reused when resuming a run.

Supported models are listed (and can be extended) in `llm_client.py`.



## Results
Detection results are saved in real-time to `metrics_log.txt` and final evaluation summaries are output to the terminal:
- Evaluation metrics include accuracy, recall, false positive rate, etc.
- Ablation study results compare performance differences across different modes to analyze the contribution of each module.

📊 The raw benchmark results are stored in `benchmark_results_vultriage/`.


____

<br>


## Repo Overview

| Script | Purpose |
|--------|---------|
| `main.py` | Main vulnerability detection script with ablation study support |
| `hyperparam_exp.py` | Hyperparameter experiments and multi-mode evaluation |
| `retrieval.py` | CWE knowledge base retrieval module (hybrid retrieval based on BGE-M3 model) |
| `metrics_tracker.py` | Real-time metrics tracker with log saving and visualization support |

### Parameter Description

#### main.py Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--wotask` | `all` | Ablation mode: `all` (full functionality), `wo_ctrl_info_pth` (no static structure info), `wo_rag_pth` (no RAG knowledge), `wo_exp_pth` (no code understanding), `nan` (no auxiliary information) |
| `--jsonl_file` | `primevul_test_paired.jsonl` | JSONL dataset path |
| `--metrics_file` | `metrics_log.txt` | Metrics output file |

#### hyperparam_exp.py Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--mode` | `pairwise` | Evaluation mode: `pairwise` or `single` |
| `--input_file` | Required | Input file path (JSONL or CSV format) |
| `--detail_level` | `C` | Code analysis detail level: `C` (complete), `B` (standard), `A` (brief) |
| `--info_comb` | `all` | Information combination: `all`, `no_ast`, `no_cfg`, `no_dfg` |
| `--desc_level` | `concise` | Description level: `concise`, `normal`, `detailed` |
| `--max_vuln` | `2` | Maximum number of vulnerabilities: `2` or `4` |


### Datasets

#### PrimeVul Dataset
- **Citation**: Yangruibo Ding, Yanjun Fu, Omniyyah Ibrahim, Chawin Sitawarin, Xinyun Chen, Basel Alomair, David Wagner, Baishakhi Ray, and Yizheng Chen. 2025. Vulnerability detection with code language models: How far are we? ISSTA 2025 (2025).
- **Purpose**: Paired vulnerability detection benchmark
- **Format**: JSONL (contains `func` and `target` fields)
- **Source**: ISSTA 2025 Conference ([ISSTA Official Website](https://issta.org/)). Please refer to the original paper for dataset access permissions.

#### CWE Database
- **Version**: CWE v4.19.1
- **Source**: [MITRE CWE](https://cwe.mitre.org/)
- **Purpose**: Vulnerability pattern knowledge base and retrieval augmentation
- **Note**: CWE can be freely used for research, development, and commercial purposes. Copyright attribution to MITRE must be retained.



