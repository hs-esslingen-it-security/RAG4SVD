# Import libraries
import numpy as np
import pandas as pd
import os
from tqdm import tqdm
import torch
import torch.nn as nn
import torch.nn.functional as F
import transformers
from datasets import Dataset, DatasetDict
import sys
sys.path.append(os.path.dirname(__file__))
from utils.data_preprocessing import load_and_preprocess_dataset, plot_tsne
from utils.modeling import (
    load_model_tokenizer_classifier_tuned,
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
model, tokenizer = load_model_tokenizer_classifier_tuned(db_name)

# Load dataset using the new preprocessing function
print("\n*** Load and preprocess dataset ***\n")
df_train, df_eval, df_test = load_and_preprocess_dataset(db_name, balance=True, debug=DEBUG)
y_true = df_test['label'].values
test_data = Dataset.from_pandas(df_test)

# Testing model
print("\n*** Testing model ***\n")
print("\n*** Predict ***\n")
logits_list, embeddings = predict_classifier(test_data, model, tokenizer)
logits = torch.cat(logits_list, dim=0)
probs = F.softmax(logits, dim=1)
y_pred = logits.argmax(axis=1).cpu().numpy()
y_pred_proba = probs[:, 1].cpu().numpy()

print("\n*** Evaluate model ***\n")
evaluate_classifier(y_true, y_pred, y_pred_proba, f"plots/ROC_classifier_tuning_test_only_{db_name}.png")
plot_tsne(embeddings, y_true, f"plots/tSNE_classifier_tuning_{db_name}.png", label_type="numeric")
print("\n (See plots in 'plots' folder)\n")
