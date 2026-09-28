import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import os
import argparse
from tqdm import tqdm
import bitsandbytes as bnb
import torch
import torch.nn as nn
import torch.nn.functional as F
import transformers
from transformers import (AutoModel, AutoTokenizer)
import sys

# path append for local utils
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

def parse_args():
    parser = argparse.ArgumentParser(description="Evaluate a specific model for vulnerability detection.")
    parser.add_argument(
        "--model", 
        type=str,
        help="The base model name to use (e.g., meta-llama/Meta-Llama-3.1-8B-Instruct)"
    )
    parser.add_argument(
        '--config', 
        type=str, 
        default='config.json', 
        help='Path to JSON config file'
    )
    parser.add_argument(
        '--db_name', 
        type=str, 
        help='Database name (overrides config file)'
    )
    return parser.parse_args()

def main():
    args = parse_args()
    config = get_config(args) # overrides config file if args are provided

    base_model_name = config['model']
    db_name = config['db_name']

    print(f"--- Running with Model: {args.model} {base_model_name} | Dataset: {db_name} ---")

    # Load model and tokenizer
    print(f"\n\n*** Load model and tokenizer ***\n")
    model, tokenizer, peft_config = load_model_tokenizer_instruct(base_model_name)

    # Load and preprocess dataset
    print("\n*** Load and preprocess dataset ***\n")
    df_train, df_eval, df_test = load_and_preprocess_dataset(db_name, balance=True, debug=DEBUG) # if paired balance=False
    
    print("\n Label distribution in Train set : \n", df_train.label_text.value_counts())
    print("\n Label distribution in Eval set : \n", df_eval.label_text.value_counts())
    print("\n Label distribution in Test set : \n", df_test.label_text.value_counts())

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

    # Load FAISS index and metadata
    print("\n*** Load index ***\n")
    index, metadata = load_faiss_index_and_metadata(db_name)
    print("FAISS index and metadata loaded successfully.", flush=True)

    # Retrieval function 
    def retrieve_similar_examples(test_code, k=6):
        test_embedding = np.array([get_embedding(test_code)])
        _, indices = index.search(test_embedding, k)
        # Using df_train from the outer scope
        examples = [df_train.iloc[idx] for idx in indices[0]]
        return examples

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
    if db_name == "primevul_paired":
        test_pair_ids = df_test["pair_id"].tolist()
        print(f"y_true: {len(y_true)}, y_pred: {len(y_pred)}, pair_ids: {len(test_pair_ids)}")
        evaluate_generative(y_true, y_pred, pair_ids=test_pair_ids)
    else:
        evaluate_generative(y_true, y_pred)
    
    # print("\n (See plots in 'plots' folder)\n")
    # if not os.path.exists('plots'):
    #     os.makedirs('plots')
        
    # plot_tsne(embeddings, y_true, f"plots/tSNE_few_shot_RAG_{db_name}.png", "text")

if __name__ == "__main__":
    main()