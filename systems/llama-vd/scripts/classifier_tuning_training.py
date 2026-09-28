# Import libraries
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import os
from tqdm import tqdm
import torch
import torch.nn as nn
import torch.nn.functional as F
import transformers
from datasets import Dataset, DatasetDict
from sklearn.metrics import (accuracy_score, 
                             classification_report)
from transformers import (
    TrainingArguments,
    Trainer,
    DataCollatorWithPadding
)
import sys
sys.path.append(os.path.dirname(__file__))
from utils.data_preprocessing import load_and_preprocess_dataset, plot_tsne
from utils.modeling import (
    load_model_tokenizer_base,
    predict_classifier,
    evaluate_classifier,
)
from config import get_config

DEBUG = False

# Fetch config
config = get_config()
db_name = config['db_name']

# Load model and tokenizer
print("\n\n*** Load model and tokenizer ***\n")
base_model_name = "meta-llama/Llama-3.1-8B"
model, tokenizer = load_model_tokenizer_base(base_model_name)

# Load dataset using the new preprocessing function
# Choose dataset: "bigvul" or "primevul"
print("\n*** Load and preprocess dataset ***\n")
df_train, df_eval, df_test = load_and_preprocess_dataset(db_name, balance=True, debug=DEBUG)
y_true = df_test['label'].values

print("\n Label distribution in Train set : \n", df_train.label_text.value_counts())
print("\n Label distribution in Eval set : \n", df_eval.label_text.value_counts())
print("\n Label distribution in Test set : \n", df_test.label_text.value_counts())

print("\n Example data points in Train set : \n")
print(df_train.head())

# Convert to HuggingFace Datasets
from datasets import Dataset, DatasetDict
train_data = Dataset.from_pandas(df_train)
eval_data = Dataset.from_pandas(df_eval)
test_data = Dataset.from_pandas(df_test)

dataset = DatasetDict({
    'train': train_data,
    'val': eval_data,
    'test': test_data
})


# Training
output_dir="llama-3.1-fine-tuned-model"

def compute_metrics(eval_pred):
    labels = ["Safe", "Vulnerable"]
    mapping = {label: idx for idx, label in enumerate(labels)}
    def map_func(x):
        return mapping.get(x, -1)
    y_true = eval_pred.label_ids
    y_pred = np.argmax(eval_pred.predictions, axis=1)
    y_true_mapped = np.vectorize(map_func)(y_true)
    y_pred_mapped = np.vectorize(map_func)(y_pred)
    class_report = classification_report(y_true=y_true_mapped, y_pred=y_pred_mapped, target_names=labels, labels=list(range(len(labels))), output_dict=True)
    accuracy = accuracy_score(y_true=y_true_mapped, y_pred=y_pred_mapped)
    metrics_output = {}
    for label_idx, label in enumerate(labels):
        label_indices = [i for i in range(len(y_true_mapped)) if y_true_mapped[i] == label]
        label_y_true = [y_true_mapped[i] for i in label_indices]
        label_y_pred = [y_pred_mapped[i] for i in label_indices]
        metrics_output[f'{label}_accuracy'] = accuracy_score(label_y_true, label_y_pred)
    for label, scores in class_report.items():
        if label not in ["accuracy", "macro avg", "weighted avg"]:
            metrics_output[f'{label}_precision'] = scores['precision']
            metrics_output[f'{label}_recall'] = scores['recall']
            metrics_output[f'{label}_f1-score'] = scores['f1-score']
    metrics_output['accuracy'] = accuracy
    metrics_output['weighted_avg_precision'] = class_report['weighted avg']['precision']
    metrics_output['weighted_avg_recall'] = class_report['weighted avg']['recall']
    metrics_output['weighted_avg_f1'] = class_report['weighted avg']['f1-score']
    return metrics_output

from transformers import TrainerCallback
from copy import deepcopy

class CustomCallback(TrainerCallback):
    def __init__(self, trainer) -> None:
        super().__init__()
        self._trainer = trainer
    def on_epoch_end(self, args, state, control, **kwargs):
        if control.should_evaluate:
            control_copy = deepcopy(control)
            self._trainer.evaluate(eval_dataset=self._trainer.train_dataset, metric_key_prefix="train")
            return control_copy

MAX_LEN = 512

def llama_preprocessing_function(examples):
    return tokenizer(examples['code'], truncation=True, max_length=MAX_LEN)

tokenized_datasets = dataset.map(llama_preprocessing_function, batched=True)
tokenized_datasets.set_format("torch")

collate_fn = DataCollatorWithPadding(tokenizer=tokenizer)

training_arguments = TrainingArguments(
    output_dir=output_dir,
    num_train_epochs=4 if not DEBUG else 2,
    per_device_train_batch_size=16 if not DEBUG else 4,
    per_device_eval_batch_size=16 if not DEBUG else 4,
    optim="paged_adamw_32bit",
    learning_rate=2e-4,
    weight_decay=0.001,
    max_steps=-1,
    warmup_ratio=0.03,
    group_by_length=False,
    lr_scheduler_type="cosine",
    eval_strategy="steps",
    eval_steps=0.2,
    save_steps=0.2,
    load_best_model_at_end=True,
    save_total_limit=1,
)

trainer = Trainer(
    model=model,
    args=training_arguments,
    train_dataset=tokenized_datasets['train'],
    eval_dataset=tokenized_datasets['val'],
    tokenizer=tokenizer,
    data_collator=collate_fn,
    compute_metrics=compute_metrics,
)

trainer.add_callback(CustomCallback(trainer))

# Training
print("\n*** Training model ***\n")
train_result = trainer.train()

print("\n*** Saving model ***\n")
model.save_pretrained(f"classifier_finetuned_{db_name}")
tokenizer.save_pretrained(f"classifier_finetuned_{db_name}")

# Testing
print("\n*** Testing model ***\n")
print("\n*** Predict ***\n")
logits_list, embeddings = predict_classifier(test_data, model, tokenizer)
logits = torch.cat(logits_list, dim=0)
probs = F.softmax(logits, dim=1)
y_pred = logits.argmax(axis=1).cpu().numpy()
y_pred_proba = probs[:, 1].cpu().numpy()

print("\n*** Evaluate model ***\n")
evaluate_classifier(y_true, y_pred, y_pred_proba, f"plots/ROC_classifier_tuning_{db_name}.png")
plot_tsne(embeddings, y_true, f"plots/tSNE_classifier_tuning_{db_name}.png", label_type="numeric")
print("\n (See plots in 'plots' folder)\n")
