from utils.data_preprocessing import load_and_preprocess_dataset, generate_faiss_index_and_metadata
from transformers import AutoModel, AutoTokenizer
import torch

# """
# Convert primevul_paired JSONL dataset to FAISS index and metadata files.
# """

# Embedding model (CodeBERT)
emb_model = AutoModel.from_pretrained("microsoft/codebert-base").to("cuda" if torch.cuda.is_available() else "cpu")
emb_tok = AutoTokenizer.from_pretrained("microsoft/codebert-base")

def get_embedding(code):
    inputs = emb_tok(code, return_tensors="pt", truncation=True, padding="max_length", max_length=512).to(next(emb_model.parameters()).device)
    with torch.no_grad():
        out = emb_model(**inputs)
    return out.last_hidden_state[:,0,:].squeeze().cpu().numpy()

df_train, df_val, df_test = load_and_preprocess_dataset("primevul_paired", balance=False)
generate_faiss_index_and_metadata(df_train, "primevul_paired", get_embedding)