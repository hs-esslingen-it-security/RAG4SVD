#!/usr/bin/env python3
import argparse
import os
import pickle
import gc, torch
from tqdm import tqdm
from pathlib import Path
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

def main():
    parser = argparse.ArgumentParser(
        description="Rebuild FAISS indices from index.pkl using one or more Hugging Face embedding models.",
        epilog='Example: python rebuild_faiss_from_pkl.py --models microsoft/codebert-base BAAI/bge-base-en-v1.5'
    )
    parser.add_argument(
        "--models",
        nargs="+",
        required=True,
        help='One or more Hugging Face model ids (space-separated), e.g. --models "microsoft/codebert-base" "BAAI/bge-base-en-v1.5"'
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip building if target faiss_<model> folder already exists"
    )
    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parent  # knowledge_db/
    subdirs = [
        ("cpp", "code"),
        ("cpp", "function"),
        ("java", "code"),
        ("java", "function"),
    ]

    for model_name in args.models:
        model_safe_name = model_name.split("/")[-1]
        print(f"Using embedding model: {model_name}")

        emb = HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs={"trust_remote_code": True},
            encode_kwargs={"normalize_embeddings": True},
        )

        for lang, sub in subdirs:
            folder = base_dir / lang / sub
            pkl_path = folder / "index.pkl"
            out_dir = folder / f"faiss_{model_safe_name}"

            if not pkl_path.exists():
                print(f"⚠️  Skipping (missing): {pkl_path}")
                continue

            if args.skip_existing and out_dir.exists():
                print(f"⏭️  Skipping existing: {out_dir}")
                continue

            print(f"Loading: {pkl_path}")
            with open(pkl_path, "rb") as f:
                data = pickle.load(f)

            docstore_obj = data[0]  # InMemoryDocstore
            docs_dict = getattr(docstore_obj, "_dict")  # Internal docstore dict
            docs = list(docs_dict.values())
            print(f"✅ Loaded {len(docs)} Document objects")

            # === Build new FAISS index ===
            #db = FAISS.from_documents(docs, emb)
            batch_size = 100
            total_docs = len(docs)

            db = FAISS.from_documents(docs[:batch_size], emb)
            for i in tqdm(range(batch_size, total_docs, batch_size), desc="Building FAISS index"):
                batch = docs[i : i + batch_size]
                db.add_documents(batch)

            out_dir.mkdir(parents=True, exist_ok=True)
            db.save_local(out_dir)
            print(f"✅ New FAISS DB created and saved at: {out_dir}\n")

        # # Free memory after each model
        # del emb
        # gc.collect()
        # torch.cuda.empty_cache()

    print("All done.")

if __name__ == "__main__":
    main()
