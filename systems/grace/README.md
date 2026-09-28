# GRACE: Empowering LLM-based Software Vulnerability Detection with Graph Structure and In-context Learning

This repository is an **adapted copy** of the original [GRACE repository](https://github.com/P-E-Vul/GRACE).
It contains the source code to the paper Lu et al., "GRACE: Empowering LLM-based software vulnerability detection with graph structure and in-context learning".

```bibtex
@article{luGRACEEmpoweringLLMbased2024,
    title={{GRACE: Empowering LLM-based Software Vulnerability Detection with Graph Structure and In-Context Learning}},
    author={Lu, Guilong and Ju, Xiaolin and Chen, Xiang and Pei, Wenlong and Cai, Zhilong},
    journal={Journal of Systems and Software (JSS)},
    volume={212},
    number = {C},
    pages={112031},
    numpages = {13},
    year={2024},
    doi = {10.1016/j.jss.2024.112031}
}
```

# Approach
Please refer to the paper for the experimental details.

## Datasets

GRACE uses the following datasets:

- BigVul [1]: [https://drive.google.com/file/d/1-0VhnHBp9IGh90s2wCNjeCMuy70HPl8X/view?usp=sharing](https://drive.google.com/file/d/1-0VhnHBp9IGh90s2wCNjeCMuy70HPl8X/view?usp=sharing)
- Reveal [2]: [https://drive.google.com/drive/folders/1KuIYgFcvWUXheDhT--cBALsfy1I4utOyF](https://drive.google.com/drive/folders/1KuIYgFcvWUXheDhT--cBALsfy1I4utOyF)
- Devign [3]: https://drive.google.com/file/d/1x6hoF7G-tSYxg8AFybggypLZgMGDNHfF

We added the processed PrimeVul Paired json files. Unzip the trainig set first.

## Preprocessing
GRACE uses Joern to construct code structure graphs. The original authors provide a compiled Joern version [here](https://drive.google.com/drive/folders/1ZktZFTbSR0NoPyFRuJDXmDsJYChoVwhF?usp=share_link). Different Joern versions may generate different graph representations, which can affect downstream performance. For this reason, reproducing the original preprocessing setup as closely as possible is recommended.

## Environment Setup
We set up a dedicated Conda environment. The provided environment is based on Python 3.12 and includes the dependencies required for local Hugging Face inference, including PyTorch, Transformers, Accelerate, and FAISS.
Create the environment from the provided specification:

```bash
conda env create -f environment.yml
```

Then activate it via `conda activate grace`.


## Run Detection

> 🚨 **Implementation notes**
> - We replaced the original OpenAI-based model interface with a local Hugging Face Transformers client in `llm_client.py`.
> - Additional open-weight models were added through model aliases in llm_client.py.
> - PrimeVul Paired support was added through the preprocessed file data/primevul_test_paired_grace_joern_id.json.


### Configure the model
Set `GRACE_LLM_NAME` to one of the supported model aliases defined in `llm_client.py`.

Optionally, configure generation parameters through `GRACE_MODEL_SETTINGS`.

Example:

```bash
export GRACE_LLM_NAME="qwen2.5-coder-14b-instruct"
export GRACE_MODEL_SETTINGS="temperature=0;max_new_tokens=4096"
```

### Configure the evaluation dataset
For the PrimeVul Paired benchmark used in this study:

```bash
export GRACE_DEVIGN_TEST_PATH="data/primevul_test_paired_grace_joern_id.json"
```
The preprocessed input must follow the graph representation expected by GRACE.


### Configure the output path
Set the result file explicitly with:

```bash
export GRACE_RESULTS_PATH="benchmark_results_grace/results_primevul_test_paired_grace_joern_id_qwen2.5-coder-14b-instruct.csv"
```



GRACE can then be executed through 
```bash
python llmpre.py
```

📊 The raw benchmark results are stored in `benchmark_results_grace/`.

> To run the GRACE variant using the basic prompt configuration, use: `python basep.py`.

## References

[1] Jiahao Fan, Yi Li, Shaohua Wang, and Tien Nguyen. 2020. A C/C++ Code Vulnerability Dataset with Code Changes and CVE Summaries. In The 2020 International Conference on Mining Software Repositories (MSR). IEEE.

[2] Saikat Chakraborty, Rahul Krishna, Yangruibo Ding, and Baishakhi Ray. 2020. Deep Learning based Vulnerability Detection: Are We There Yet? arXiv preprint arXiv:2009.07235 (2020).

[3] Yaqin Zhou, Shangqing Liu, Jingkai Siow, Xiaoning Du, and Yang Liu. 2019. Devign: Effective vulnerability identification by learning comprehensive program semantics via graph neural networks. In Advances in Neural Information Processing Systems. 10197–10207.

