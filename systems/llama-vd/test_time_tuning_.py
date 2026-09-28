import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import os
import argparse
from tqdm import tqdm
import torch
import torch.nn as nn
import torch.nn.functional as F
import transformers
from datasets import Dataset, DatasetDict
from transformers import (AutoModel,
                          AutoTokenizer)
from copy import deepcopy
import gc
import sys
sys.path.append(os.path.dirname(__file__))
from utils.data_preprocessing import (load_and_preprocess_dataset, 
                                plot_tsne, 
                                load_faiss_index_and_metadata,
                                generate_faiss_index_and_metadata)
from utils.modeling import (
    load_model_tokenizer_base,
    evaluate_classifier,
    evaluate_generative
)
from config import get_config

DEBUG = False

def parse_args():
    parser = argparse.ArgumentParser(description="Test-time tuning for vulnerability detection.")
    parser.add_argument(
        "--model", 
        type=str,
        default='meta-llama/Llama-3.1-8B',
        help="The base model name to use"
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


def fine_tune_model_on_examples(model, train_codes, train_labels, tokenizer, epochs=1, lr=2e-4):
    model.train()
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr)
    loss_fn = nn.CrossEntropyLoss()
    for _ in range(epochs):
        for i in range(len(train_codes)):
            train_code = train_codes[i]
            train_label = train_labels[i]
            optimizer.zero_grad()
            input = tokenizer(train_code, padding=True, truncation=True, return_tensors="pt", max_length=8192).to(model.device)
            logits = model(**input)['logits']
            label_tensor = torch.tensor([train_label], dtype=torch.long, device=model.device)
            loss = loss_fn(logits, label_tensor)
            loss.backward()
            optimizer.step()

def predict_single(model, test_code, tokenizer):
    input = tokenizer(test_code, return_tensors="pt", padding=True, truncation=True, max_length=8192).to('cuda')
    with torch.no_grad():
        output = model(**input, output_hidden_states=True, return_dict=True)
        y_pred = output['logits']
        last_hidden_state = output.hidden_states[-1]
        last_embedding = last_hidden_state.mean(dim=1)
        embedding = last_embedding.cpu().numpy()
    return y_pred, embedding


def main():
    args = parse_args()
    config = get_config(args) # overrides config file if args are provided

    base_model_name = config['model']
    db_name = config['db_name']

    print(f"--- Running Test-Time Tuning | Model: {args.model} {base_model_name} | Dataset: {db_name} ---")

    # Load model and tokenizer
    print(f"\n*** Load base model and tokenizer ***\n")
    model, tokenizer = load_model_tokenizer_base(base_model_name)

    # Load and preprocess dataset
    print("\n*** Load and preprocess dataset ***\n")
    df_train, df_eval, df_test = load_and_preprocess_dataset(db_name, balance=True, debug=DEBUG)

    # Convert to datasets
    train_data = Dataset.from_pandas(df_train[["code", "label"]])
    eval_data = Dataset.from_pandas(df_eval[["code", "label"]])
    test_data = Dataset.from_pandas(df_test[["code", "label"]])

    # Combine them into a single DatasetDict
    dataset = DatasetDict({
        'train': train_data,
        'val': eval_data,
        'test': test_data
    })
    # Load CodeBERT model for embeddings (Retrieval)
    print("\n*** Load embedding model (CodeBERT) ***\n")
    embedding_model_name = "microsoft/codebert-base"
    embedding_model = AutoModel.from_pretrained(embedding_model_name)
    embedding_tokenizer = AutoTokenizer.from_pretrained(embedding_model_name)
    embedding_model.eval()

    def get_embedding(code_snippet):
        inputs = embedding_tokenizer(code_snippet, return_tensors="pt", truncation=True, padding="max_length", max_length=512)
        with torch.no_grad():
            outputs = embedding_model(**inputs)
        return outputs.last_hidden_state[:, 0, :].squeeze().numpy()


    # Load FAISS index
    print("\n*** Load FAISS index and metadata ***\n")
    index, metadata = load_faiss_index_and_metadata(db_name)
    print("FAISS index and metadata loaded successfully.", flush=True)


    def retrieve_similar_examples(test_code, k=6):
        test_embedding = np.array([get_embedding(test_code)])
        _, indices = index.search(test_embedding, k)
        examples = [df_train.iloc[idx] for idx in indices[0]]
        return examples

    print("\n\n*** Starting Test-Time Tuning Loop ***\n")
    y_pred = []
    y_true = []
    y_pred_probas = []
    embeddings = []

    for i in tqdm(range(len(df_test))):
        test_code = df_test.iloc[i]['code']
        
        # retrieve
        examples = retrieve_similar_examples(test_code)
        
        # setup Test-Time Model (Deep copy)
        test_model = deepcopy(model)
        train_codes = [ex['code'] for ex in examples]
        train_labels = [ex["label"] for ex in examples]
        
        # fine-tune on retrieved examples
        fine_tune_model_on_examples(test_model, train_codes, train_labels, tokenizer) 
        logits, embedding = predict_single(test_model, test_code, tokenizer)
        probs = F.softmax(logits, dim=1)
        pred_label = logits.argmax(axis=1).cpu().numpy()[0]
        y_pred_proba = probs[:, 1].cpu().numpy()[0]
        
        y_true.append(df_test.iloc[i]['label'])
        y_pred.append(pred_label)
        y_pred_probas.append(y_pred_proba)
        embeddings.append(embedding)
        
        # cleanup memory
        del test_model
        torch.cuda.empty_cache()
        gc.collect()

    # evaluation
    print("\n\n*** Evaluate model ***\n")
    p_ids = None
    if db_name == "primevul_paired":
        p_ids = df_test["pair_id"].tolist()

    evaluate_classifier(
        y_true, 
        y_pred, 
        y_pred_probas, 
        f"plots/ROC_test_time_tuning_{args.model}_{db_name}.png",
        p_ids)
    
    plot_tsne(embeddings, y_true, f"plots/tSNE_test_time_tuning_{args.model}_{db_name}.png", "numeric")
    print("\n (See plots in 'plots' folder)\n")

if __name__ == "__main__":
    main()
