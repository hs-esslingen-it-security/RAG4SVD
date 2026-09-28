import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import os
from tqdm import tqdm
import bitsandbytes as bnb
import torch
import torch.nn as nn
import torch.nn.functional as F
import transformers
from transformers import (AutoModel,
                          AutoTokenizer)
import sys
sys.path.append(os.path.dirname(__file__))
from utils.data_preprocessing import (load_and_preprocess_dataset, 
                                plot_tsne, 
                                load_faiss_index_and_metadata,
                                generate_faiss_index_and_metadata)
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
print("\n\n*** Load model and tokenizer ***\n")
base_model_name = "meta-llama/Meta-Llama-3.1-8B-Instruct"
model, tokenizer, peft_config = load_model_tokenizer_instruct(base_model_name)

# Load and preprocess dataset
print("\n*** Load and preprocess dataset ***\n")
df_train, df_eval, df_test = load_and_preprocess_dataset(db_name, balance=True, debug=DEBUG)
y_true = df_test['label_text']

print("\n Label distribution in Train set : \n", df_train.label_text.value_counts())
print("\n Label distribution in Eval set : \n", df_eval.label_text.value_counts())
print("\n Label distribution in Test set : \n", df_test.label_text.value_counts())

print("\n Example data points in Train set : \n")
print(df_train.head())

# Load CodeBERT model and tokenizer to generate embeddings
print("\n*** Load embedding model and tokenizer ***\n")
embedding_model_name = "microsoft/codebert-base"
embedding_model = AutoModel.from_pretrained(embedding_model_name)
embedding_tokenizer = AutoTokenizer.from_pretrained(embedding_model_name)
embedding_model.eval()

def get_embedding(code_snippet):
    inputs = embedding_tokenizer(code_snippet, return_tensors="pt", truncation=True, padding="max_length", max_length=512)
    with torch.no_grad():
        outputs = embedding_model(**inputs)
    return outputs.last_hidden_state[:, 0, :].squeeze().numpy()

# Generate and store embeddings
# print("\n***Generate and store embeddings***\n", flush=True)
# generate_faiss_index_and_metadata(df_train, db_name, get_embedding)

# Load FAISS index and metadata using the new function
print("\n*** Load index ***\n")
index, metadata = load_faiss_index_and_metadata(db_name)
code_snippets = metadata["code"]
train_labels = metadata["target"]
print("FAISS index and metadata loaded successfully.", flush=True)


# Retrieval function using standardized columns
def retrieve_similar_examples(test_code, k=6):
    test_embedding = np.array([get_embedding(test_code)])
    _, indices = index.search(test_embedding, k)
    examples = [df_train.iloc[idx] for idx in indices[0]]
    return examples

# FEW SHOT PROMPTING #
# Define the few shot prompt generation function
def generate_few_shot_prompt(i):
    test_code = df_test.iloc[i]['code']
    examples = retrieve_similar_examples(test_code)
    return f"""Classify the source code into Vulnerable/Safe. Here are some examples:
Code: {examples[0]['code']}
Label: {examples[0]["label_text"]}
Code: {examples[1]['code']}
Label: {examples[1]["label_text"]}
Code: {examples[2]['code']}
Label: {examples[2]["label_text"]}
Code: {examples[3]['code']}
Label: {examples[3]["label_text"]}
Code: {examples[4]['code']}
Label: {examples[4]["label_text"]}
Code: {examples[5]['code']}
Label: {examples[5]["label_text"]}
Code: {test_code}
Label: """.strip()

# Predict and evaluate
print("\n\n*** Generate prompts and Predict ***\n")
y_pred, y_true, embeddings, nbr_weird_pred, prompt_1 = predict_generative(
    df_test, model, tokenizer, prompt_fn=generate_few_shot_prompt
)

print("\n\n*** Evaluate model ****\n")
# if db_name == "primevul_paired":
#     evaluate_generative(y_true, y_pred, pair_ids=metadata["pair_id"])
# else:
#     evaluate_generative(y_true, y_pred)
evaluate_generative(y_true, y_pred)
print("\n (See plots in 'plots' folder)\n")
plot_tsne(embeddings, y_true, f"plots/tSNE_few_shot_RAG_{db_name}.png", "text")