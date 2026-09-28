# Import libraries
import transformers
import datasets
from transformers import AutoTokenizer, AutoModelForSequenceClassification 
from datasets import load_dataset, Dataset, DatasetDict
import numpy as np
import pandas as pd
import wandb
import os
import torch
import torch.nn as nn
import torch.nn.functional as F
from sklearn.metrics import (accuracy_score, 
                             classification_report)
from tqdm import tqdm
import sys
sys.path.append(os.path.dirname(__file__))
from utils.data_preprocessing import load_and_preprocess_dataset, plot_tsne
from utils.modeling import (
    predict_classifier,
    evaluate_classifier,
)
from config import get_config

DEBUG= False

# Fetch config
config = get_config()
db_name = config['db_name']

# Load the model and tokenizer
model = AutoModelForSequenceClassification.from_pretrained("microsoft/unixcoder-base-nine", num_labels=2)

tokenizer = AutoTokenizer.from_pretrained("microsoft/unixcoder-base-nine")

# # 3. Load the dataset
df_train, df_eval, df_test = load_and_preprocess_dataset(db_name, balance=True, debug=DEBUG)
# Generate test prompts and extract true labels
y_true = df_test['label'].values

print("\n train_data : \n")
print(df_train)

# Combine them into a single DatasetDict
from datasets import Dataset, DatasetDict
train_data = Dataset.from_pandas(df_train)
eval_data = Dataset.from_pandas(df_eval)
test_data = Dataset.from_pandas(df_test)

dataset = DatasetDict({
    'train': train_data,
    'val': eval_data,
    'test': test_data
})

# # 4. Tokenize data
max_length = 512
def tokenize(batch):
   # Tokenize the inputs
   tokenized_inputs = tokenizer(batch["code"], padding='max_length', truncation=True, max_length=max_length) 
   return tokenized_inputs

# Apply the tokenize function to the dataset
train_dataset = dataset["train"].map(tokenize, batched=True, batch_size=16)
valid_dataset = dataset["val"].map(tokenize, batched=True, batch_size=16)
test_dataset = dataset["test"].map(tokenize, batched=True, batch_size=16)

if DEBUG:
    train_dataset = train_dataset.shuffle(seed=42).select(range(20))
    val_dataset = valid_dataset.shuffle(seed=42).select(range(10))
    test_dataset = test_dataset.shuffle(seed=42).select(range(10))

from sklearn.metrics import precision_score, recall_score, f1_score
from transformers import TrainingArguments, Trainer
import numpy as np

def compute_metrics(eval_pred):
    logits, labels = eval_pred
    predictions = np.argmax(logits, axis=-1)

    textual_labels = ["Safe", "Vulnerable"]

    # Compute metrics using sklearn
    precision = precision_score(labels, predictions)
    recall = recall_score(labels, predictions)
    f1 = f1_score(labels, predictions)
    acc = accuracy_score(labels, predictions)

    # Prepare the output dictionary to include detailed metrics
    metrics_output = {
        "precision": precision,  # Precision for the last batch
        "recall": recall,        # Recall for the last batch
        "f1": f1,                # F1-score for the last batch
        "acc": acc,              # Accuracy for the last batch
    }

    # Generate detailed classification report
    report = classification_report(labels, predictions, output_dict=True)

    # Generate accuracy report  
    mapping = {idx: label for idx, label in enumerate(textual_labels)}  
    
    for lable_idx, label in enumerate(textual_labels):
        label_indices = [i for i in range(len(labels)) if mapping[labels[i]] == label]
        label_y_true = [labels[i] for i in label_indices]
        label_y_pred = [predictions[i] for i in label_indices]
        metrics_output[f'{lable_idx}_accuracy'] = accuracy_score(label_y_true, label_y_pred)
        
    # Add detailed class-specific metrics from the classification report
    for label, scores in report.items():
        if label not in ["accuracy", "macro avg", "weighted avg"]:
            # Add precision, recall, f1-score for each class
            metrics_output[f'{label}_precision'] = scores['precision']
            metrics_output[f'{label}_recall'] = scores['recall']
            metrics_output[f'{label}_f1-score'] = scores['f1-score']
            #metrics_output[f'{label}_support'] = scores['support']
    
    # Add overall system-level scores
    metrics_output['weighted_avg_precision'] = report['weighted avg']['precision']
    metrics_output['weighted_avg_recall'] = report['weighted avg']['recall']
    metrics_output['weighted_avg_f1'] = report['weighted avg']['f1-score']
    
    return metrics_output

training_args = TrainingArguments(output_dir="test_trainer", 
        evaluation_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="acc",
        save_total_limit=1,
        learning_rate=2e-5,
        num_train_epochs=10,
        )

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


trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=valid_dataset,
    compute_metrics=compute_metrics,
)
trainer.add_callback(CustomCallback(trainer))

trainer.train()

results=trainer.evaluate(eval_dataset=test_dataset)
results

print("\n*** Saving model ***\n")
model.save_pretrained(f"unixcoder_finetuned_{db_name}")
tokenizer.save_pretrained(f"unixcoder_finetuned_{db_name}")


# Testing
print("\n Model testing ...")
# Make predictions and get logits
logits_list, embeddings = predict_classifier(test_data, model, tokenizer)

# Concatenate logits from all predictions
logits = torch.cat(logits_list, dim=0)
# Convert logits to probabilities
probs = F.softmax(logits, dim=1)
# Get discrete predictions and probability scores for the "Vulnerable" class (index 1)
y_pred = logits.argmax(axis=1).cpu().numpy()
y_pred_proba = probs[:, 1].cpu().numpy()  # For ROC and AUC

evaluate_classifier(y_true, y_pred, y_pred_proba, f"plots/ROC_unixcoder_tuning_{db_name}.png")
plot_tsne(embeddings, y_true, f"plots/tSNE_unixcoder_tuning_{db_name}.png", label_type="numeric")
print("\n (See plots in 'plots' folder)\n")