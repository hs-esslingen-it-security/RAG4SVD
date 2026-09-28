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

# Load dataset using the new preprocessing function
print("\n\n*** Load dataset ***\n")
df_train, df_eval, df_test = load_and_preprocess_dataset(db_name, balance=True, debug=DEBUG)

# FEW SHOT LEARNING EXPERIMENT

# Separate the dataset into vulnerable and non-vulnerable
print("\n Separating the dataset into vulnerable and non-vulnerable functions ...")
vulnerable_df = df_train[df_train['label_text'] == 'Vulnerable']
non_vulnerable_df = df_train[df_train['label_text'] == 'Safe']

# Shuffle the Datasets
vulnerable_df = vulnerable_df.sample(frac=1, random_state=1).reset_index(drop=True)
non_vulnerable_df = non_vulnerable_df.sample(frac=1, random_state=1).reset_index(drop=True)

# Group by CWE ID and count the number of snippets in each group
grouped = vulnerable_df.groupby('cwe_id').size()

# Plot the histogram
plt.figure(figsize=(12, 8))
grouped.plot(kind='bar', color='skyblue', edgecolor='black')
plt.xlabel('CWE ID')
plt.ylabel('Number of Code Snippets')
plt.title('Number of Code Snippets per CWE ID')
plt.xticks(rotation=90)
plt.grid(axis='y', linestyle='--', alpha=0.7)
plt.savefig('code_snippets_per_cwe_id.png')

# Filter CWE IDs with at least 3 code snippets
cwe_ids_with_min_size = grouped[grouped >= 3].index

# Create subsets for each CWE ID with at least 3 code snippets
filtered_subsets = {cwe_id: vulnerable_df[vulnerable_df['cwe_id'] == cwe_id] for cwe_id in cwe_ids_with_min_size}
print(f"Number of subsets with at least 3 code snippets: {len(filtered_subsets)}")

# Split each training dataset into as much subsets as there are testing examples, each containing 3 samples
print(" Splitting the training datasets into as much subsets as there are testing samples, each containing 3 functions")
num_dataframes = len(df_test)
elements_per_dataframe = 3

filtered_subsets = {cwe_id: filtered_subsets[cwe_id].iloc[0:elements_per_dataframe] for cwe_id in cwe_ids_with_min_size}

# Create the smaller DataFrames
vulnerable_dataframes = []
for i in range(num_dataframes):
    cwe_id = df_test.iloc[i]['cwe_id']
    if cwe_id in filtered_subsets:
        df_small = filtered_subsets[cwe_id]
    else:
        start_idx = i * elements_per_dataframe
        end_idx = start_idx + elements_per_dataframe
        df_small = vulnerable_df.iloc[start_idx:end_idx]
    vulnerable_dataframes.append(df_small)
non_vulnerable_dataframes = []
for i in range(num_dataframes):
    start_idx = i * elements_per_dataframe
    end_idx = start_idx + elements_per_dataframe
    df_small = non_vulnerable_df.iloc[start_idx:end_idx]
    non_vulnerable_dataframes.append(df_small)

print("\n vulnerable_dataframe 0 : \n")
print(vulnerable_dataframes[0].info())
print(vulnerable_dataframes[0].head(2))   

from utils.modeling import predict_generative
# FEW SHOT PROMPTING #
def generate_few_shot_prompt(i):
    vulnerable_examples = vulnerable_dataframes[i]
    non_vulnerable_examples = non_vulnerable_dataframes[i]
    test_sample = df_test.iloc[i]
    return f"""Classify the source code into Vulnerable/Safe. Here are some examples:
Code: {non_vulnerable_examples.iloc[0]['code']}
Label: {non_vulnerable_examples.iloc[0]['label_text']}
Code: {vulnerable_examples.iloc[0]['code']}
Label: {vulnerable_examples.iloc[0]['label_text']}
Code: {non_vulnerable_examples.iloc[1]['code']}
Label: {non_vulnerable_examples.iloc[1]['label_text']}
Code: {vulnerable_examples.iloc[1]['code']}
Label: {vulnerable_examples.iloc[1]['label_text']}
Code: {non_vulnerable_examples.iloc[2]['code']}
Label: {non_vulnerable_examples.iloc[2]['label_text']}
Code: {vulnerable_examples.iloc[2]['code']}
Label: {vulnerable_examples.iloc[2]['label_text']}
Code: {test_sample['code']}
Label: """.strip()

y_pred, y_true, embeddings, nbr_weird_pred, prompt_1 = predict_generative(
    df_test, model, tokenizer, prompt_fn=generate_few_shot_prompt
)

print('Nbr out of scope predictions : ', nbr_weird_pred)
print("\n *** Example of results : prompt_1 results ***")
print("\n Prompt : \n", prompt_1)
print("\n\n Llama response :", y_pred[0],"; True label : ", y_true[0])

print("\n\n*** Evaluate model : ****\n")
evaluate_generative(y_true, y_pred)
plot_tsne(embeddings, y_true, f"plots/tSNE_few_shot_CWE_types_{db_name}.png", "text")