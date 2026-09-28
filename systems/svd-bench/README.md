# SVD_Bench
This repository is an **adapted copy** of the original [SVD_Bench repository](https://github.com/soarsmu/SVD-Bench).

## Setup
### Environment
The full Conda environment specification is provided in: ``environment_svd_bench.yml``.

Create the environment with: ``conda env create -f environment_svd_bench.yml`` & activate it with ``conda activate svd-bench``.

> 🚨 Encountered issues during the deployment:
> - `sentence-transformers` was required by the `accelerate` workflow and had to be installed separately: `pip install sentence-transformers`.

### Dataset
Download the original datasets here: [SVD-data](https://smu-my.sharepoint.com/:u:/g/personal/tingzhang_2019_phdcs_smu_edu_sg/EUdFAjGjhENJhh2wbAvzgT0BfpdCwZrYxQxdw7yve60bhw?e=ZOBnjf) and place the split `.json` files in the respective `datasets/` folder (`datasets/java/`, `datasets/javascript/`, `datasets/python/`)

## Run RAG Detection
SVD-Bench is executed through `main.py` using Hugging Face Accelerate. Supported model aliases are defined (and can be extended) in `utils_models.py`.

The main parameters are:
- `--dataset` evaluation dataset
- `--model` detector model
- `--few_shot_k` number of retrieved examples included in the prompt
- `--embedding_model` embedding model used for retrieval
- `--eval_only` run evaluation without training

Example (with default k & embedding model):
```
accelerate launch \
    --config_file configs/accelerate_config_1gpu.yaml \
    main.py \
    --task_type generation \
    --dataset javascript \
    --model codeqwen1.5-7b-chat \
    --prompt_version 1 \
    --eval_only \
    --few_shot_k 3 \
    --embedding_model simcse-bert-base
```

🧠 Models from the original study:
```
    codeqwen1.5-7b-chat
    deepseek-coder-6.7b-instruct
    codegemma-7b-it
    starcoder2-7b
    codellama-7b-instruct
```

📊 The raw benchmark results are stored in `benchmark_results_svdbench/`. The raw results from the reproduction are stored in `reproduced_results/reproduced_3x_<model>`.