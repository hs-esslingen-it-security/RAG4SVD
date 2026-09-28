import torch
import numpy as np
from tqdm import tqdm
from collections import defaultdict
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, roc_curve, auc
import matplotlib.pyplot as plt
from transformers import (
    AutoModelForCausalLM,
    AutoModelForSequenceClassification,
    AutoTokenizer,
    BitsAndBytesConfig,
)
from peft import LoraConfig, prepare_model_for_kbit_training, get_peft_model, PeftModel

def load_model_tokenizer_instruct(base_model_name, lora_config_kwargs=None):
    """
    Loads model and tokenizer with LoRA PEFT, as in few_shot_alternated_refactored.py.
    Returns: model, tokenizer
    """
    compute_dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=compute_dtype,
    )
    model = AutoModelForCausalLM.from_pretrained(
        base_model_name,
        device_map="auto",
        torch_dtype=compute_dtype,
        quantization_config=bnb_config,
        trust_remote_code=False,
        attn_implementation="sdpa" # <--- ADDED FOR GEMMA
    )
    if lora_config_kwargs is None:
        lora_config_kwargs = dict(
            lora_alpha=8,
            lora_dropout=0,
            r=16,
            bias="none",
            task_type="CAUSAL_LM",
            target_modules=['q_proj', 'k_proj', 'v_proj', 'o_proj'],
        )
    peft_config = LoraConfig(**lora_config_kwargs)
    model = prepare_model_for_kbit_training(model)
    model = get_peft_model(model, peft_config)

    tokenizer = AutoTokenizer.from_pretrained(
        base_model_name,
        #add_prefix_space=True,
        use_fast=True, 
        trust_remote_code=False
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.pad_token_id = tokenizer.eos_token_id

    model.generation_config.pad_token_id = tokenizer.pad_token_id
    model.config.use_cache = False
    model.config.pretraining_tp = 1
    return model, tokenizer, peft_config

def load_model_tokenizer_base(base_model_name, lora_config_kwargs=None):
    """
    Loads base model and tokenizer for sequence classification, as in classifier_tuning_refactored.py.
    Returns: model, tokenizer
    """
    compute_dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=compute_dtype,
    )
    model = AutoModelForSequenceClassification.from_pretrained(
        base_model_name,
        quantization_config=bnb_config,
        num_labels=2,
        trust_remote_code=False,
        torch_dtype=compute_dtype,
        attn_implementation="sdpa" # <--- ADDED FOR GEMMA
    )
    if lora_config_kwargs is None:
        lora_config_kwargs = dict(
            lora_alpha=8,
            lora_dropout=0,
            r=16,
            bias="none",
            task_type='SEQ_CLS',
            target_modules=['q_proj', 'k_proj', 'v_proj', 'o_proj'],
        )
    peft_config = LoraConfig(**lora_config_kwargs)
    model = prepare_model_for_kbit_training(model)
    model = get_peft_model(model, peft_config)
    tokenizer = AutoTokenizer.from_pretrained(
        base_model_name,
        #add_prefix_space=True,
        use_fast=True, 
        trust_remote_code=False
    )
    tokenizer.pad_token_id = tokenizer.eos_token_id
    tokenizer.pad_token = tokenizer.eos_token
    model.config.pad_token_id = tokenizer.pad_token_id
    model.config.use_cache = False
    model.config.pretraining_tp = 1
    return model, tokenizer

def load_model_tokenizer_classifier_tuned(db_name):
    """
    Loads a finetuned classification model and tokenizer.
    Supports: 'bigvul', 'primevul', 'primevul_paired' (primevul_paired uses primevul model)
    """
    if db_name == "bigvul":
        extract_path = "models/classifier_finetuned_bigvul"
    elif db_name == "primevul" or db_name == "primevul_paired":
        extract_path = "models/classifier_finetuned_primevul"

    tokenizer = AutoTokenizer.from_pretrained(
        extract_path,
        add_prefix_space=True,
    )

    base_model = AutoModelForSequenceClassification.from_pretrained(
        extract_path,
        device_map="auto",
        num_labels=2
    )

    model = PeftModel.from_pretrained(base_model, extract_path)
    model.eval()

    tokenizer.pad_token_id = tokenizer.eos_token_id
    tokenizer.pad_token = tokenizer.eos_token
    model.config.pad_token_id = tokenizer.pad_token_id
    model.config.use_cache = False
    model.config.pretraining_tp = 1  
    return model, tokenizer

def load_model_tokenizer_instruct_tuned(db_name):
    """
    Loads a finetuned instruct model and tokenizer.
    Supports: 'bigvul', 'primevul', 'primevul_paired' (primevul_paired uses primevul model)
    """
    if db_name == "bigvul":
        extract_path = "models/instruct_finetuned_bigvul"
    elif db_name == "primevul" or db_name == "primevul_paired":
        extract_path = "models/instruct_finetuned_primevul"

    tokenizer = AutoTokenizer.from_pretrained(
        extract_path,
        add_prefix_space=True,
    )

    base_model = AutoModelForCausalLM.from_pretrained(
        extract_path,
        torch_dtype="float16",
        device_map="auto",
    )

    model = PeftModel.from_pretrained(base_model, extract_path)
    model.eval()

    tokenizer.pad_token_id = tokenizer.eos_token_id
    tokenizer.pad_token = tokenizer.eos_token
    model.config.pad_token_id = tokenizer.pad_token_id
    model.config.use_cache = False
    model.config.pretraining_tp = 1  
    return model, tokenizer

def predict_generative(
    test_data,
    model,
    tokenizer,
    prompt_fn,
    categories=("Safe", "Vulnerable"),
    max_length=8192,
    device='cuda'
):
    """
    Generalized generative prediction for all few-shot, RAG, CWE, instruct, and zero-shot scripts.

    Args:
        test_data: DataFrame or list of dicts/rows.
        model, tokenizer: loaded model and tokenizer.
        prompt_fn: function (i) -> prompt string.
        categories: tuple/list of valid label strings.
        max_length: max token length for input.
        device: device for inference.

    Returns:
        y_pred: list of predicted labels.
        y_true: list of true labels (if available).
        embeddings: list of last hidden state mean embeddings.
        nbr_weird_pred: number of out-of-scope predictions.
        prompt_1: the first prompt (for inspection).
    """
    y_pred = []
    y_true = []
    embeddings = []
    nbr_weird_pred = 0
    prompt_1 = None

    for i in tqdm(range(len(test_data))):
        prompt = prompt_fn(i)
        if i == 0:
            prompt_1 = prompt

        row = test_data.iloc[i] if hasattr(test_data, "iloc") else test_data[i]

        inputs = tokenizer(prompt, return_tensors="pt", padding=True, truncation=True, max_length=max_length).to(device)
        with torch.no_grad():
            outputs = model(**inputs, output_hidden_states=True, return_dict=True)
            last_hidden_state = outputs.hidden_states[-1]
            last_embedding = last_hidden_state.mean(dim=1).cpu().numpy()
            output = model.generate(**inputs, max_new_tokens=10, temperature=0.1, do_sample=False)
        answer = tokenizer.decode(output[0], skip_special_tokens=True).split("Label:")[-1].strip()
        for category in categories:
            if category.lower() in answer.lower():
                weird_pred = 0
                pred_label = category
                break
        else:
            weird_pred = 1
            pred_label = "none"
            print("Out of scope prediction : ", answer)
        y_pred.append(pred_label)
        if "label_text" in row:
            y_true.append(row["label_text"])
        elif "label" in row:
            y_true.append(row["label"])
        else:
            y_true.append(None)
        embeddings.append(last_embedding)
        nbr_weird_pred += weird_pred
    return y_pred, y_true, embeddings, nbr_weird_pred, prompt_1

# def evaluate_generative(y_true, y_pred, pair_ids=None):
#     """
#     Evaluates predictions with accuracy, classification report, confusion matrix, and optional pairwise accuracy.
    
#     Args:
#         y_true: List of true labels ('Safe' or 'Vulnerable')
#         y_pred: List of predicted labels ('Safe' or 'Vulnerable')
#         pair_ids: Optional list of pair IDs for computing pairwise accuracy. 
#                   If provided, computes accuracy for paired items (both must be correct).
#     """
#     labels = ["Safe", "Vulnerable"]
#     mapping = {label: idx for idx, label in enumerate(labels)}
#     def map_func(x):
#         return mapping.get(x, -1)
#     y_true_mapped = np.vectorize(map_func)(y_true)
#     y_pred_mapped = np.vectorize(map_func)(y_pred)
#     accuracy = accuracy_score(y_true=y_true_mapped, y_pred=y_pred_mapped)
#     print(f'Accuracy: {accuracy:.4f}')
    
#     # Compute pairwise accuracy if pair_ids are provided
#     if pair_ids is not None: # and len(pair_ids) == len(y_pred):
#         pairwise_correct = 0
#         num_pairs = 0
#         unique_pairs = set(pair_ids)
#         for pair_id in unique_pairs:
#             # Find indices for this pair
#             indices = [i for i, pid in enumerate(pair_ids) if pid == pair_id]
#             if len(indices) == 2:  # Should have exactly 2 items per pair
#                 # Both predictions must match ground truth for the pair to be correct
#                 pair_correct = all(y_pred_mapped[i] == y_true_mapped[i] for i in indices)
#                 if pair_correct:
#                     pairwise_correct += 1
#                 num_pairs += 1
#         if num_pairs > 0:
#             pairwise_accuracy = pairwise_correct / num_pairs
#             print(f'Pairwise Accuracy: {pairwise_accuracy:.4f}, Number Pairs: {num_pairs}')
    
#     class_report = classification_report(y_true=y_true_mapped, y_pred=y_pred_mapped, target_names=labels, labels=list(range(len(labels))))
#     print('\nClassification Report:')
#     print(class_report)
#     conf_matrix = confusion_matrix(y_true=y_true_mapped, y_pred=y_pred_mapped, labels=list(range(len(labels))))
#     print('\nConfusion Matrix:')
#     print(conf_matrix)

def evaluate_generative(y_true, y_pred, pair_ids=None):
    """
    Evaluates predictions with accuracy, classification report, and robust pairwise accuracy.
    """
    labels = ["Safe", "Vulnerable"]
    mapping = {label: idx for idx, label in enumerate(labels)}
    
    def map_func(x):
        return mapping.get(x, -1)
    
    y_true_mapped = np.vectorize(map_func)(y_true)
    y_pred_mapped = np.vectorize(map_func)(y_pred)
    
    # Calculate basic accuracy
    accuracy = accuracy_score(y_true=y_true_mapped, y_pred=y_pred_mapped)
    print(f'Overall Accuracy: {accuracy:.4f}')
    
    # Compute pairwise accuracy if pair_ids are provided
    if pair_ids is not None:
        # Group result success by pair_id
        pair_results = defaultdict(list)

        for i in range(len(y_pred_mapped)):
            pid = pair_ids[i]

            # A prediction is only correct if it matches ground truth 
            # AND it's not -1 (the "weird" prediction flag)
            is_correct = (y_pred_mapped[i] == y_true_mapped[i]) and (y_pred_mapped[i] != -1)
            pair_results[pid].append(is_correct)
        
        pairwise_correct = 0
        num_complete_pairs = 0
        
        for pid, results in pair_results.items():
            # A pair is only valid for 'pairwise accuracy' if we have both versions (Vuln & Safe)
            if len(results) == 2:
                num_complete_pairs += 1
                if all(results):
                    pairwise_correct += 1
            else: #  only one snippet was evaluated - ignore
                continue
                    
        if num_complete_pairs > 0:
            pairwise_acc = pairwise_correct / num_complete_pairs
            print(f'Pairwise Accuracy: {pairwise_acc:.4f}')
            print(f'Pairs where both were correct: {pairwise_correct}')
            print(f'Total complete pairs evaluated: {num_complete_pairs}')

    # Standard metrics
    class_report = classification_report(
        y_true_mapped, 
        y_pred_mapped, 
        target_names=labels, 
        labels=list(range(len(labels))),
        zero_division=0
    )
    print('\nClassification Report:')
    print(class_report)
    
    conf_matrix = confusion_matrix(y_true_mapped, y_pred_mapped, labels=list(range(len(labels))))
    print('\nConfusion Matrix:')
    print(conf_matrix)

def predict_classifier(test_data, model, tokenizer):
    """
    Replicates the predict() function from classifier_tuning_refactored.py.
    Args:
        test_data: HuggingFace Dataset or list of dicts with "code"
        model, tokenizer: loaded model and tokenizer
    Returns:
        logits_list: list of logits tensors
        embeddings: list of last hidden state mean embeddings
    """
    y_pred = []
    embeddings = []
    for i in tqdm(range(len(test_data))):
        code = test_data[i]["code"] if isinstance(test_data, list) or isinstance(test_data, np.ndarray) else test_data[i]["code"]
        inputs = tokenizer(code, return_tensors="pt", padding=True, truncation=True, max_length=512).to('cuda')
        with torch.no_grad():
            outputs = model(**inputs, output_hidden_states=True, return_dict=True)
            y_pred.append(outputs['logits'])
            last_hidden_state = outputs.hidden_states[-1]
            last_embedding = last_hidden_state.mean(dim=1)
            embeddings.append(last_embedding.cpu().numpy())
    return y_pred, embeddings

def evaluate_classifier(y_true, y_pred, y_pred_proba, plot_path, pair_ids=None):
    """
    Replicates the evaluate() function from classifier_tuning_refactored.py.
    """
    labels = ["Safe", "Vulnerable"]
    accuracy = accuracy_score(y_true=y_true, y_pred=y_pred)
    print(f'Accuracy: {accuracy:.3f}')

    # --- Pairwise Accuracy Logic ---
    if pair_ids is not None:
        pair_results = defaultdict(list)
        # Match predictions to IDs
        # (Assuming y_true, y_pred, and pair_ids are already same-length lists)
        for i in range(len(y_pred)):
            pid = pair_ids[i]
            is_correct = (y_pred[i] == y_true[i])
            pair_results[pid].append(is_correct)
        
        pairwise_correct = 0
        num_complete_pairs = 0
        for pid, results in pair_results.items():
            if len(results) == 2:
                num_complete_pairs += 1
                if all(results):
                    pairwise_correct += 1
        
        if num_complete_pairs > 0:
            pairwise_acc = pairwise_correct / num_complete_pairs
            print(f'Pairwise Accuracy: {pairwise_acc:.4f}')
            print(f'Pairs where both were correct: {pairwise_correct}')
            print(f'Total complete pairs evaluated: {num_complete_pairs}')


    class_report = classification_report(
        y_true=y_true, 
        y_pred=y_pred, 
        target_names=labels, 
        labels=list(range(len(labels))))
    
    print('\nClassification Report:')
    print(class_report)

    conf_matrix = confusion_matrix(y_true=y_true, y_pred=y_pred, labels=list(range(len(labels))))
    print('\nConfusion Matrix:')
    print(conf_matrix)

    fpr, tpr, thresholds = roc_curve(y_true, y_pred_proba)
    roc_auc = auc(fpr, tpr)
    print(f'\nROC AUC: {roc_auc:.3f}')

    plt.close('all')
    fig = plt.figure(figsize=(8, 6))
    plt.plot(fpr, tpr, color='darkorange', lw=2, label=f'ROC curve (area = {roc_auc:.2f})')
    plt.plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--')
    plt.xlabel('False Positive Rate')
    plt.ylabel('True Positive Rate')
    plt.title('Receiver Operating Characteristic')
    plt.legend(loc="lower right")
    plt.show()
    fig.savefig(plot_path, dpi=300)
    plt.close(fig)