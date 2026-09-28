### CURRENTLY NOT SUPPORTED IN FULL!! no primevul_paired-tuned model
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
    load_model_tokenizer_classifier_tuned,
    evaluate_classifier,
    evaluate_generative
) # the script uses already fine-tuned classifier!
from config import get_config

DEBUG = False
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

def parse_args():
    parser = argparse.ArgumentParser(description="Double tuning: Pre-tuned + Test-time tuning.")
    parser.add_argument(
        '--config', 
        type=str, 
        default='config.json', 
        help='Path to JSON config file'
    )
    parser.add_argument(
        '--db_name', 
        type=str, 
        help='Database name (determines both the dataset and the pre-tuned checkpoint)'
    )
    return parser.parse_args()

def fine_tune_model_on_examples(model, train_codes, train_labels, tokenizer, optimizer, epochs=2):
    model.train()
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
    db_name = config['db_name']

    print(f"--- Running Double Tuning | Mode: Pre-Tuned + TTT | Dataset/Checkpoint: {db_name} ---")

    # Load model and tokenizer
    print("\n\n*** Load model and tokenizer ***\n")
    model, tokenizer = load_model_tokenizer_classifier_tuned(db_name)

    # Load and preprocess dataset  # Change to 'primevul' to use PrimeVul database
    print("\n*** Load and preprocess dataset ***\n")
    df_train, df_eval, df_test = load_and_preprocess_dataset(db_name, balance=True, debug=DEBUG)
    y_true = df_test['label'].values

    # Convert to HuggingFace Datasets if needed
    train_data = Dataset.from_pandas(df_train)
    eval_data = Dataset.from_pandas(df_eval)
    test_data = Dataset.from_pandas(df_test)
    dataset = DatasetDict({'train': train_data, 'val': eval_data, 'test': test_data})

    # Load CodeBERT model and tokenizer to generate embeddings
    print("\n***Load embedding model and tokenizer***\n", flush=True)
    embedding_model_name = "microsoft/codebert-base"
    embedding_model = AutoModel.from_pretrained(embedding_model_name)
    embedding_tokenizer = AutoTokenizer.from_pretrained(embedding_model_name)
    embedding_model.eval()

    def get_embedding(code_snippet):
        inputs = embedding_tokenizer(code_snippet, return_tensors="pt", truncation=True, padding="max_length", max_length=512)
        with torch.no_grad():
            outputs = embedding_model(**inputs)
        return outputs.last_hidden_state[:, 0, :].squeeze().numpy()  # CLS token embedding


    # Load FAISS index and metadata using the new function
    print("\n***Load FAISS index and metadata***\n")
    index, metadata = load_faiss_index_and_metadata(db_name)


    def retrieve_similar_examples(test_code, k=6):
        test_embedding = np.array([get_embedding(test_code)])
        _, indices = index.search(test_embedding, k)
        examples = [df_train.iloc[idx] for idx in indices[0]]
        return examples


    print("\n***Test-time tune and predict***\n")
    # Apply RAG-based few-shot prompting with per-test finetuning
    y_pred = []
    y_true_list = []
    y_pred_probas = []
    embeddings = []

    for i in tqdm(range(len(df_test))):
        test_code = df_test.iloc[i]['code']

        examples = retrieve_similar_examples(test_code)

        test_model = deepcopy(model)
        optimizer = torch.optim.AdamW(test_model.parameters(), lr=2e-4)
        train_codes = [ex['code'] for ex in examples]
        train_labels = [ex["label"] for ex in examples]

        fine_tune_model_on_examples(test_model, train_codes, train_labels, tokenizer, optimizer)

        logits, embedding = predict_single(test_model, test_code, tokenizer)
        probs = F.softmax(logits, dim=1)

        pred_label = logits.argmax(axis=1).cpu().numpy()
        y_pred_proba = probs[:, 1].cpu().numpy()
        y_true_list.append(df_test.iloc[i]['label'])
        y_pred.append(pred_label)
        y_pred_probas.append(y_pred_proba)
        embeddings.append(embedding)

        del test_model
        torch.cuda.empty_cache()
        gc.collect()

    # Evaluate model predictions
    print("\n\n*** Evaluate model : ****\n")
    p_ids = None
    if db_name == "primevul_paired":
        p_ids = df_test["pair_id"].tolist()

    evaluate_classifier(
        y_true_list, 
        y_pred, 
        y_pred_probas, 
        f"plots/ROC_double_tuning_{args.model}_{db_name}.png",
        p_ids)
    
    plot_tsne(embeddings, y_true_list, f"plots/tSNE_double_tuning_{args.model}_{db_name}.png", "numeric")
    print("\n (See plots in 'plots' folder)\n")


if __name__ == "__main__":
    main()