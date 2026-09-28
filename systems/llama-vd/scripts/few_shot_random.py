import numpy as np
import pandas as pd
import os
from tqdm import tqdm
import torch
import sys
sys.path.append(os.path.dirname(__file__))
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

# Load dataset
df_train, df_eval, df_test = load_and_preprocess_dataset(db_name, balance=True, debug=DEBUG)

# FEW SHOT PROMPTING #
vulnerable_df = df_train[df_train['label_text'] == 'Vulnerable']
non_vulnerable_df = df_train[df_train['label_text'] == 'Safe']

num_dataframes = len(df_test)
elements_per_dataframe = 3
total_elements = num_dataframes * elements_per_dataframe
if len(vulnerable_df) <= total_elements or len(non_vulnerable_df) <= total_elements:
    raise ValueError("Not enough rows to split into the desired number of DataFrames.")
vulnerable_df_shuffled = vulnerable_df.sample(frac=1, random_state=1).reset_index(drop=True)
non_vulnerable_df_shuffled = non_vulnerable_df.sample(frac=1, random_state=1).reset_index(drop=True)
vulnerable_dataframes = [vulnerable_df_shuffled.iloc[i*elements_per_dataframe:(i+1)*elements_per_dataframe] for i in range(num_dataframes)]
non_vulnerable_dataframes = [non_vulnerable_df_shuffled.iloc[i*elements_per_dataframe:(i+1)*elements_per_dataframe] for i in range(num_dataframes)]

def generate_few_shot_prompt(i):
    vulnerable_examples = vulnerable_dataframes[i]
    non_vulnerable_examples = non_vulnerable_dataframes[i]
    test_sample = df_test.iloc[i]
    return f"""Classify the source code into Vulnerable/Safe. Here are some examples:
Code: {non_vulnerable_examples.iloc[0]["code"]}
Label: {non_vulnerable_examples.iloc[0]["label_text"]}
Code: {vulnerable_examples.iloc[0]["code"]}
Label: {vulnerable_examples.iloc[0]["label_text"]}
Code: {non_vulnerable_examples.iloc[1]["code"]}
Label: {non_vulnerable_examples.iloc[1]["label_text"]}
Code: {vulnerable_examples.iloc[1]["code"]}
Label: {vulnerable_examples.iloc[1]["label_text"]}
Code: {non_vulnerable_examples.iloc[2]["code"]}
Label: {non_vulnerable_examples.iloc[2]["label_text"]}
Code: {vulnerable_examples.iloc[2]["code"]}
Label: {vulnerable_examples.iloc[2]["label_text"]}
Code: {test_sample["code"]}
Label: """.strip()

# Predict and evaluate using modeling.py
y_pred, y_true, embeddings, nbr_weird_pred, prompt_1 = predict_generative(
    df_test, model, tokenizer, generate_few_shot_prompt
)

print('Nbr out of scope predictions : ', nbr_weird_pred)
print("\n *** Example of results : prompt_1 results ***")
print("\n Prompt : \n", prompt_1)
print("\n\n Llama response :", y_pred[0],"; True label : ", y_true[0])
print("\n\n*** Evaluate model : ****\n")
evaluate_generative(y_true, y_pred)
plot_tsne(embeddings, y_true, f"plots/tSNE_few_shot_random_{db_name}.png", "text")