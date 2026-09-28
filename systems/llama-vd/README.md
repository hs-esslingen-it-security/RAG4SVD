# Llama-VD 🦙

This repository contains an adapted copy of the [replication package](https://github.com/DynaSoumhaneOuchebara/Llama-based-vulnerability-detection) of the paper "Llama-Based Source Code Vulnerability Detection: Prompt Engineering vs Fine Tuning" by Ouchebara and Dupont.


```bibtex
@inproceedings{ouchebaraLlamabasedSourceCode2025,
    author="Ouchebara, Dyna Soumhane and Dupont, St{\'e}phane",
    title="Llama-Based Source Code Vulnerability Detection: Prompt Engineering vs Fine Tuning",
    booktitle="Computer Security -- ESORICS 2025",
    year="2026",
    publisher="Springer Nature Switzerland",
    pages="289--308"
}
```

## Setup
1. Clone the repository
2. Install requirements with command : `pip install -r req.txt` -> conda environment `llama-vd` with python version `3.10`!
	```bash
	conda create -y -n llama-vd python=3.10
	conda activate llama-vd
	pip install -r req.txt --extra-index-url https://download.pytorch.org/whl/cu121
	```
3. Download the models/ and indexes/ folders from the original google drive link :  https://drive.google.com/drive/folders/1GtJNU1yXD0l4BdMSQ9YOtVgjhnac5tQM?usp=sharing as zip files, then unzip them into the main folder of the repository.
4. Download the PrimeVul Paired test & train split jsonl, see `docs/DATASETS.md` in the main RAG4SVD repository. Load them into the `dataset/` folder.
5. Go to  [meta-llama/Llama-3.1-8B · Hugging Face](https://huggingface.co/meta-llama/Llama-3.1-8B) , open section *You need to agree to share your contact information to access this model*, and follow the steps to get your huggingface token in order to access the models. Once you have your token, go to the terminal and write the following command : `huggingface-cli login` followed by your token.


## Repository Structure
- `req.txt` : contains the necessary libraries to install.
> 📝 ***Note***: Update in ``requirements.yml`` / ``requirements_updated_torch_v.yml``
- `utils/` :
	- `data_processing.py` : contains functions to load and preprocess data as well as generate/save/load RAG indexes.
	- `modeling.py` : contains functions to load models and tokenizers, make predictions and evaluate model predictions.
- `config.json` and `config.py` : define parameters which are expected to be given by the user when running the scripts (alternative: pass by command line, which overrides config).
* The list of scripts corresponding to all experiments presented in the paper:
	- `codebert_tuning_training.py` : Fine-tuning of baseline model CodeBERT.
	- `unixcoder_tuning_training.py` : Fine-tuning of baseline model Unixcoder.
	- `zero_shot.py` : Zero shot prompting strategy.
	- `few_shot_random.py` : Few shot prompting strategy with random selection of examples.
	- `few_shot_CWE_types.py` : Few shot prompting strategy with a selection of examples from the same CWE type as the test code.
	- `few_shot_RAG.py` : Few shot prompting strategy with a selection of examples using RAG. ⭐️⭐️⭐️
	- `test_time_tuning.py` : Test time fine-tuning. ⭐️
	- `instruct_tuning_test_only.py` : Fine-tuning of the instruct model using QLoRA strategy. This script does not do the training phase, it directly loads the trained model and evaluates it.
	- `instruct_tuning_training.py` : Fine-tuning of the instruct model using QLoRA strategy. This script does the training of the model, which takes quite some time (6 hours on BigVul and 3 hours on PrimeVul with our setup) so be mindful if you want to run this script.
	- `classifier_tuning_test_only.py` : Fine-tuning of the base model with a classification head using QLoRA strategy. This script does not do the training phase, it directly loads the trained model and evaluates it.
	- `classifier_tuning_training.py` : Fine-tuning of the base model with a classification head using QLoRA strategy. This script does the training of the model, which takes quite some time (28 hours on BigVul and 14 hours on PrimeVul with our setup) so be mindful if you want to run this script.
	- `double_tuning.py` : Double fine-tuning strategy. ⭐️

<br>

> 📝 ***Note***: logic slightly adjusted in ``few_shot_RAG_.py``, ``test_time_tuning_.py``, and ``double_tuning_.py`` to use command line arguments to vary model and dataset; original scripts in `scripts/`


Focus on highlighted (⭐️) scripts (adapted versions). The original scripts were moved to `scripts/`. (need to be run from main `llama-vd/`)



## Run Detection
> 📝 ***Note***: We extend the original dataset options (`bigvul`, `primevul`) with `primevul_paired`.

To run the RAG configuration:

```bash
python3 few_shot_RAG_.py \
  --model <model identifier> \
  --db_name primevul_paired
```

- ``--model`` supports short model names (DICT -> `config.py`) or full HF identifier
- ``--dataset`` either "bigvul", "primevul" or added: "primevul_paired"


<br>
______
<br>

### PrimeVul Paired Dataset Integration
- **Train file**: `dataset/primevul_train_paired.jsonl` (7,578 lines = 3,789 pairs)
- **Valid file**: `dataset/primevul_valid_paired.jsonl`
- **Test file**: `dataset/primevul_test_paired.jsonl` (870 lines = 435 pairs)

Changes to Implementation:

(1) Data Preprocessing (`utils/data_preprocessing.py`)
  - Automatically detects pair structure (pairs on consecutive lines)
  - Assigns sequential `pair_id` (0, 1, 2, ...) to each pair
  - Returns DataFrames with columns: `code`, `label`, `label_text`, `pair_id`, `cwe_id`
  - Skips class balancing for paired data to preserve pair structure


(2) Data Preprocessing (`utils/convert_primevul_paired_to_index.py`)
  - Loads paired training examples from `dataset/primevul_train_paired.jsonl`
  - Generates embeddings using CodeBERT
  - Creates FAISS index with L2 distance metric
  - Saves:
	- `indexes/primevul_paired_train_embeddings.index`
	- `indexes/primevul_paired_code_metadata.pkl`


(3) Model Loading (`utils/modeling.py`)
- `load_model_tokenizer_classifier_tuned("primevul_paired")` - Maps to primevul model
- `load_model_tokenizer_instruct_tuned("primevul_paired")` - Maps to primevul model
- Enhanced evaluate_generative() + evaluate_classifier()
	```python
	def evaluate_generative(y_true, y_pred, pair_ids=None):
	```
	- `pair_ids` (optional): List of pair IDs aligned with predictions
	- **Pairwise Accuracy**: Percentage of pairs where BOTH vulnerable and non-vulnerable examples are correctly classified


(4) Add in evaluation scripts (e.g., `few_shot_RAG_.py`):

```python
# ... load dataset ...
# ... load FAISS index and metadata
# ... generate predictions y_true, y_pred ...

# Evaluate with pairwise accuracy
if db_name == "primevul_paired":
    evaluate_generative(y_true, y_pred, pair_ids=test_pair_ids)
else:
    evaluate_generative(y_true, y_pred)
```

#### Command-line Usage:

```bash
# With config file
python few_shot_RAG_.py --config config.json --db_name primevul_paired

# With explicit model
python few_shot_RAG_.py --model <model identifier> --db_name primevul_paired
```


📊 The raw benchmark results are stored in `benchmark_results_llamavd/`. The raw reproduced results are stored in `reproduced_results/`. 
