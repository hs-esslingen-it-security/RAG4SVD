import pandas as pd
from datasets import load_dataset
import faiss
import pickle
import numpy as np
import matplotlib.pyplot as plt
from sklearn.manifold import TSNE
import json
import os

def load_and_preprocess_dataset(dataset_name, balance=True, debug=False):
    """
    Loads and preprocesses the specified dataset ("bigvul", "primevul", or "primevul_paired").
    Returns: train_df, val_df, test_df (with columns: code, label, label_text, and optionally pair_id)
    
    For primevul_paired: pairs are read from JSONL files (vulnerable then non-vulnerable),
    assigned sequential pair_ids. balance parameter is ignored for paired data.
    """
    if dataset_name.lower() == "bigvul":
        dataset = load_dataset("DynaOuchebara/BigVul_2columns")
        col_code, col_label = "func_before", "vul"
    elif dataset_name.lower() == "primevul":
        dataset = load_dataset("colin/PrimeVul", "default")
        dataset = dataset.remove_columns([
            'idx', 'project', 'commit_id', 'project_url', 'commit_url', 'commit_message',
            'func_hash', 'file_name', 'file_hash', 'cwe', 'cve', 'cve_desc', 'nvd_url'
        ])
        col_code, col_label = "func", "target"
    elif dataset_name.lower() == "bigvul_cwe":
        dataset = load_dataset("DynaOuchebara/BigVul_cwe_types")
        col_code, col_label, col_cwe = "func_before", "vul", "CWE ID"
    elif dataset_name.lower() == "primevul_cwe":
        dataset = load_dataset("colin/PrimeVul", "default")
        dataset = dataset.remove_columns([
            'idx', 'project', 'commit_id', 'project_url', 'commit_url', 'commit_message',
            'func_hash', 'file_name', 'file_hash', 'cve', 'cve_desc', 'nvd_url'
        ])
        col_code, col_label = "func", "target"
        # Convert to pandas
        df_train = dataset['train'].to_pandas()
        df_val = dataset['validation'].to_pandas()
        df_test = dataset['test'].to_pandas()
        # Extract CWE ID for vulnerable, 'none' for safe
        def extract_cwe_id(row):
            if row[col_label] == 1:
                return row['cwe'][0] if len(row['cwe']) > 0 else 'unknown'
            else:
                return 'none'
        for df in [df_train, df_val, df_test]:
            df['cwe_id_cleaned'] = df.apply(extract_cwe_id, axis=1)
        col_cwe = "cwe_id_cleaned"
    elif dataset_name.lower() == "primevul_paired":
        # Load from JSONL files with paired vulnerable/non-vulnerable examples
        data_train = []
        data_test = []
        # Load training, validation, and test pairs from JSONL
        train_file = os.path.join(os.path.dirname(__file__), '../dataset/primevul_train_paired.jsonl')
        valid_file = os.path.join(os.path.dirname(__file__), '../dataset/primevul_valid_paired.jsonl')
        test_file = os.path.join(os.path.dirname(__file__), '../dataset/primevul_test_paired.jsonl')

        def _load_pairs_from_file(path):
            data = []
            if os.path.exists(path):
                with open(path, 'r') as f:
                    lines = f.readlines()
                for pair_id, i in enumerate(range(0, len(lines), 2)):
                    if i + 1 < len(lines):
                        vuln = json.loads(lines[i])
                        safe = json.loads(lines[i + 1])
                        # extract CWE id for vulnerable, 'none' for safe
                        try:
                            vuln_cwe = vuln.get('cwe', [])
                            cwe_id_vuln = vuln_cwe[0] if isinstance(vuln_cwe, list) and len(vuln_cwe) > 0 else 'unknown'
                        except Exception:
                            cwe_id_vuln = 'unknown'
                        data.append({'func': vuln['func'], 'target': 1, 'pair_id': pair_id, 'cwe_id': cwe_id_vuln})
                        data.append({'func': safe['func'], 'target': 0, 'pair_id': pair_id, 'cwe_id': 'none'})
            return data

        data_train = _load_pairs_from_file(train_file)
        data_test = _load_pairs_from_file(test_file)
        data_valid = _load_pairs_from_file(valid_file)

        # Convert to DataFrames
        df_train = pd.DataFrame(data_train) if data_train else pd.DataFrame()
        df_test = pd.DataFrame(data_test) if data_test else pd.DataFrame()
        df_val = pd.DataFrame(data_valid) if data_valid else pd.DataFrame()

        col_code, col_label = "func", "target"
        has_pair_id = True
    else:
        raise ValueError(f"Unknown dataset: {dataset_name}")

    if dataset_name.lower() not in ["primevul_cwe", "primevul_paired"]:
        # Convert to pandas if not already done
        df_train = dataset['train'].to_pandas()
        df_val = dataset['validation'].to_pandas()
        df_test = dataset['test'].to_pandas()

    # Add textual label
    def label_text(x):
        return "Safe" if x == 0 else "Vulnerable"
    for df in [df_train, df_val, df_test]:
        if len(df) > 0:
            df['label_text'] = df[col_label].apply(label_text)

    # Balance classes (skip for paired data to preserve pair structure)
    has_pair_id = dataset_name.lower() == "primevul_paired"
    if balance and not has_pair_id:
        def balance_df(df):
            df_0 = df[df[col_label] == 0]
            df_1 = df[df[col_label] == 1]
            n = min(len(df_0), len(df_1))
            return pd.concat([
                df_0.sample(n=n, random_state=42, replace=False),
                df_1.sample(n=n, random_state=42, replace=False)
            ]).reset_index(drop=True)
        df_train = balance_df(df_train)
        df_val = balance_df(df_val)
        df_test = balance_df(df_test)

    # Debug mode: reduce size
    if debug:
        df_train = df_train[:20]
        df_val = df_val[:20]
        df_test = df_test[:5]

    # Standardize columns
    for df in [df_train, df_val, df_test]:
        if len(df) > 0:
            df.rename(columns={col_code: "code", col_label: "label"}, inplace=True)
            if dataset_name.lower() in ["bigvul_cwe", "primevul_cwe"]:
                df.rename(columns={col_cwe: "cwe_id"}, inplace=True)

    # Only keep relevant columns
    keep_cols = ["code", "label", "label_text"]
    if dataset_name.lower() in ["bigvul_cwe", "primevul_cwe", "primevul_paired"]:
        keep_cols.append("cwe_id")
    if dataset_name.lower() == "primevul_paired":
        keep_cols.append("pair_id")
    
    df_train = df_train[keep_cols]
    df_val = df_val[keep_cols]
    df_test = df_test[keep_cols]

    return df_train, df_val, df_test 

def load_faiss_index_and_metadata(db_name):
    """
    Loads the FAISS index and metadata for the specified database.
    Args:
        db_name (str): Name of the database ('bigvul', 'primevul', or 'primevul_paired')
    Returns:
        index: FAISS index object
        metadata: dict with keys 'code', 'label', 'label_text', and 'pair_id' for paired datasets
    """
    if db_name.lower() == 'bigvul':
        index_path = 'indexes/bigvul_train_embeddings.index'
        metadata_path = 'indexes/bigvul_code_metadata.pkl'
    elif db_name.lower() == 'primevul':
        index_path = 'indexes/primevul_train_embeddings.index'
        metadata_path = 'indexes/primevul_code_metadata.pkl'
    elif db_name.lower() == 'primevul_paired':
        index_path = 'indexes/primevul_paired_train_embeddings.index'
        metadata_path = 'indexes/primevul_paired_code_metadata.pkl'
    else:
        raise ValueError(f"Unknown db_name: {db_name}")
    index = faiss.read_index(index_path)
    with open(metadata_path, 'rb') as f:
        metadata = pickle.load(f)
    return index, metadata 

def generate_faiss_index_and_metadata(df_train, db_name, get_embedding_fn):
    # Generate and store embeddings
    print("\n***Generate and store embeddings***\n", flush=True)
    print("\nGenerate embeddings...", flush=True)
    train_embeddings = np.array([get_embedding_fn(code) for code in df_train["code"].tolist()])
    print("\nCreate index...", flush=True)
    index = faiss.IndexFlatL2(train_embeddings.shape[1])
    print("\nAdd embeddings to index...", flush=True)
    index.add(train_embeddings)
    metadata = {
        "code": df_train["code"].tolist(),
        "label": df_train["label"].tolist(),
        "label_text": df_train["label_text"].tolist()
    }
    
    # keep as close to original implementation as possible
    # # Include pair_id if present (for paired datasets)
    if "pair_id" in df_train.columns:
        metadata["pair_id"] = df_train["pair_id"].tolist()
    # # Include cwe_id if present
    # if "cwe_id" in df_train.columns:
    #     metadata["cwe_id"] = df_train["cwe_id"].tolist()

    # Save FAISS index
    faiss.write_index(index, f"indexes/{db_name}_train_embeddings.index")

    # Save corresponding metadata (e.g., code snippets & labels)
    with open(f"indexes/{db_name}_code_metadata.pkl", "wb") as f:
        pickle.dump(metadata, f)
    print("FAISS index and metadata saved successfully.", flush=True)


def plot_tsne(embeddings, labels, file_name, label_type="numeric"):
    """
    Plot t-SNE for embeddings. If label_type is 'numeric', expects labels 0/1. If 'text', expects 'Safe'/'Vulnerable'.
    """
    embeddings_array = np.array(embeddings)
    embeddings_array = embeddings_array.squeeze(1)
    tsne = TSNE(n_components=2, perplexity=30, random_state=42)
    embeddings_2d = tsne.fit_transform(embeddings_array)
    if label_type == "numeric":
        class_1_indices = [i for i, lbl in enumerate(labels) if lbl == 0]
        class_2_indices = [i for i, lbl in enumerate(labels) if lbl == 1]
    elif label_type == "text":
        class_1_indices = [i for i, lbl in enumerate(labels) if lbl == "Safe"]
        class_2_indices = [i for i, lbl in enumerate(labels) if lbl == "Vulnerable"]
    class_1_marker = "x"
    class_2_marker = "o"
    class_1_label = "safe"
    class_2_label = "vulnerable"
    plt.close('all')
    fig, ax = plt.subplots()
    ax.scatter(embeddings_2d[class_1_indices, 0], embeddings_2d[class_1_indices, 1], marker=class_1_marker, color="red", label=class_1_label)
    ax.scatter(embeddings_2d[class_2_indices, 0], embeddings_2d[class_2_indices, 1], marker=class_2_marker, color="blue", label=class_2_label)
    ax.set_title("t-SNE Visualization of Sentence Embeddings")
    ax.set_xlabel("t-SNE Component 1")
    ax.set_ylabel("t-SNE Component 2")
    ax.legend()
    fig.savefig(file_name, dpi=300)
    plt.close(fig) 

