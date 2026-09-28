import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import os
from tqdm import tqdm
import torch
import torch.nn as nn
import transformers
from utils.data_preprocessing import load_and_preprocess_dataset, plot_tsne
from utils.modeling import (
    load_model_tokenizer_instruct_tuned,
    predict_generative,
    evaluate_generative,
)
from config import get_config

DEBUG = False

# Fetch config
config = get_config()
db_name = config['db_name']

# Load model and tokenizer
print("\n\n*** Load model and tokenizer ***\n")
model, tokenizer = load_model_tokenizer_instruct_tuned(db_name)

# Load and preprocess dataset
print("\n\n*** Load and preprocess dataset ***\n")
df_train, df_eval, df_test = load_and_preprocess_dataset(db_name, balance=True, debug=DEBUG)
y_true = df_test['label_text']

# Define the prompt generation functions
def generate_test_prompt(i):
    row = df_test.iloc[i]
    return f"""Classify the source code into Vulnerable or Safe, and return the answer as the corresponding label.
Code: {row['code']}
Label: """.strip()

# Testing
print("\n Model testing ...")

y_pred, y_true_pred, embeddings, nbr_weird_preds, prompt_1 = predict_generative(
    df_test, model, tokenizer, prompt_fn=generate_test_prompt
)

evaluate_generative(y_true_pred, y_pred)
plot_tsne(embeddings, y_true_pred, f"plots/tSNE_instruct_tuning_{db_name}.png", "text")

model.config.use_cache = True