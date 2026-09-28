#!/usr/bin/env python3
import argparse
import json
import pickle
from pathlib import Path
from langchain_core.documents import Document

def _sanitize(obj):
    if isinstance(obj, dict):
        return {str(k): _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_sanitize(v) for v in obj]
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    return str(obj)

def export_pickle_to_json(pkl_path: Path, out_dir: Path) -> None:
    with pkl_path.open("rb") as f:
        data = pickle.load(f)

    if not (isinstance(data, tuple) and len(data) >= 2):
        raise RuntimeError("Unexpected pickle layout. Expected tuple(len>=2).")

    docstore_obj = data[0]  # InMemoryDocstore
    index_to_docstore_id = data[1]  # dict: int_index -> uuid

    if not hasattr(docstore_obj, "_dict"):
        raise RuntimeError("Docstore object has no _dict attribute.")

    docs_dict = getattr(docstore_obj, "_dict")  # uuid -> Document
    out_dir.mkdir(parents=True, exist_ok=True)

    # docs.jsonl
    docs_path = out_dir / "docs.jsonl"
    with docs_path.open("w", encoding="utf-8") as fw:
        for doc_id, doc in docs_dict.items():
            if not isinstance(doc, Document):
                # Skip unexpected entries
                continue
            fw.write(json.dumps({
                "id": doc_id,
                "page_content": doc.page_content,
                "metadata": _sanitize(doc.metadata),
            }, ensure_ascii=False) + "\n")

    # mapping.json (preserve FAISS order)
    try:
        ordered = [doc_id for _, doc_id in sorted(index_to_docstore_id.items(), key=lambda kv: int(kv[0]))]
    except Exception:
        # Fallback: plain iteration order
        ordered = list(index_to_docstore_id.values())

    mapping_path = out_dir / "mapping.json"
    mapping_path.write_text(json.dumps({"order": ordered}, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"✅ Exported {len(docs_dict)} docs to {docs_path}")
    print(f"✅ Wrote id order to {mapping_path}")

def main():
    parser = argparse.ArgumentParser(
        description="Export LangChain FAISS pickle (index.pkl) to JSONL + mapping.json"
    )
    parser.add_argument(
        "pkl",
        nargs="+",
        help="Path(s) to index.pkl file(s) to export"
    )
    parser.add_argument(
        "--out",
        help="Output directory (if a single PKL). If omitted, uses <pkl_dir>/export_json"
    )
    args = parser.parse_args()

    if len(args.pkl) > 1 and args.out:
        raise SystemExit("When exporting multiple PKLs, omit --out (each will get its own export_json folder).")

    for p in args.pkl:
        pkl_path = Path(p).resolve()
        if not pkl_path.exists():
            print(f"⚠️  Skipping (missing): {pkl_path}")
            continue

        if args.out and len(args.pkl) == 1:
            out_dir = Path(args.out).resolve()
        else:
            out_dir = pkl_path.parent / "export_json"

        print(f"📦 Exporting: {pkl_path}")
        export_pickle_to_json(pkl_path, out_dir)

if __name__ == "__main__":
    main()
