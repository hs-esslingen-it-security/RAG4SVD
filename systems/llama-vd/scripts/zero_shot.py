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
    load_model_tokenizer_instruct,
    predict_generative,
    evaluate_generative,
)
from config import get_config

DEBUG = False

# Fetch config
config = get_config()
db_name = config['db_name']

# Load model and tokenizer
base_model_name = "meta-llama/Meta-Llama-3.1-8B-Instruct"
model, tokenizer, peft_config = load_model_tokenizer_instruct(base_model_name)

# Load and preprocess dataset
print("\n\n*** Load and preprocess dataset ***\n")
df_train, df_eval, df_test = load_and_preprocess_dataset(db_name, balance=True, debug=DEBUG)

# Define the prompt generation functions
def generate_test_prompt(i):
    row = df_test.iloc[i]
    return f"""Classify the source code into Vulnerable or Safe, and return the answer as the corresponding label.
Code: {row['code']}
Label: """.strip()

y_true = df_test['label_text']

# Make predictions 
y_pred, y_true_pred, embeddings, nbr_weird_preds, prompt_1 = predict_generative(
    df_test, model, tokenizer, prompt_fn=generate_test_prompt
)

evaluate_generative(y_true_pred, y_pred)
print("\n nbr_weird_preds : ", nbr_weird_preds)

plot_tsne(embeddings, y_true_pred, f"plots/tSNE_zero_shot_{db_name}.png", "text")