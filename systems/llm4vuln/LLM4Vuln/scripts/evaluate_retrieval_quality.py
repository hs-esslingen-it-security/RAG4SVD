#!/usr/bin/env python3
import argparse
import json
import re
import sys
import os
from pathlib import Path
from typing import Any, Dict, List, Tuple
import time
from tqdm import tqdm

# Setup Paths for LLM4Vuln internal imports
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))

# LLM4Vuln Internal Imports
import models.utils_model as MODELS_UTILS
import registry

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="LLM4Vuln CWE-Agreement Retrieval Evaluation")
    parser.add_argument("--input-dir", default="dataset/cpp_primevul_sampled")
    parser.add_argument("--manifest", default="dataset/primevul_sampled_pairs_manifest.txt")
    parser.add_argument("--query-mode", choices=["code", "function"], default="function")
    parser.add_argument("--embedding", default="codebert-base")
    parser.add_argument("--summary-model", default="qwen2.5-7b-instruct")
    parser.add_argument("--k-values", default="1,3,5")
    parser.add_argument("--summary-output", default="llm4vuln_summary_quality.json", help="Path to store summaries for later evaluation")
    parser.add_argument("--output-json", default="llm4vuln_retrieval_details.json", help="Path to save detailed retrieval results and metrics")
    return parser.parse_args()

def load_ground_truth_map(path: str) -> Dict[str, str]:
    """Universal loader for PrimeVul manifest (.txt) or Original map (.json)."""
    p = Path(path)
    if not p.exists():
        print(f"Error: Metadata file {path} not found.")
        sys.exit(1)

    if p.suffix == ".json":
        with open(p, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Normalize to uppercase
            return {k.upper(): v.upper() for k, v in data.items()}

    mapping = {}
    with open(p, 'r', encoding='utf-8') as f:
        for line in f:
            if "|" in line and "CWE_ID" not in line and "---" not in line:
                parts = [p.strip() for p in line.split('|')]
                if len(parts) >= 2:
                    # parts[1] is CVE_ID, parts[0] is CWE_ID
                    mapping[parts[1].upper()] = parts[0].upper()
    return mapping

def extract_cwes(text: str) -> List[str]:
    """Extracts all CWE IDs from text and standardizes to uppercase."""
    found = re.findall(r"CWE-\d+", text, flags=re.IGNORECASE)
    return sorted(set(f.upper() for f in found))

def extract_doc_labels(doc: Any) -> List[str]:
    """Aggressively extracts CWEs from document content and all metadata."""
    text_parts = [str(doc.page_content)]
    if hasattr(doc, 'metadata') and isinstance(doc.metadata, dict):
        text_parts.extend([str(val) for val in doc.metadata.values()])
    return extract_cwes("\n".join(text_parts))

def load_query_samples(input_dir: str) -> List[Dict[str, Any]]:
    """Loads samples, robust to both PrimeVul and Original folder formats."""
    samples = []
    path = Path(input_dir)
    for json_file in path.glob("*.json"):
        with open(json_file, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
                entries = data if isinstance(data, list) else [data]
                for entry in entries:
                    # Resolve code snippet
                    func = entry.get("code_before_change") or \
                           (entry.get("code_before_patch", {}) if isinstance(entry.get("code_before_patch"), dict) else {}).get("code")
                    
                    # Resolve CVE ID
                    cve = entry.get("cve_id") or entry.get("cve", "")
                    
                    if func:
                        samples.append({
                            "id": entry.get("id", "N/A"),
                            "filename": json_file.name,
                            "func": func,
                            "cve": cve.upper(),
                        })
            except Exception as e:
                print(f"Warning: Skipping file {json_file.name} due to error: {e}")
    return samples

def evaluate_sample(sample, loader, query_mode, k_vals, manifest_gt):
    """Performs retrieval and calculates hits/mrr for a single sample."""
    query_text = sample["func"]
    target_cwe = manifest_gt.get(sample["cve"])
    if not target_cwe:
        return None

    # 1. Retrieval Logic (FAISS)
    search_query = query_text
    if query_mode == "function":
        # Use private name-mangling to access the loader's internal summarizer
        generate_fn = getattr(loader, f"_{loader.__class__.__name__}__generate_functionality", None)
        search_query = generate_fn(query_text) if callable(generate_fn) else query_text

    # Search FAISS (using max k requested)
    retrieved_docs = loader.db.similarity_search(search_query, k=max(k_vals))

    # 2. Scoring & Metadata Tracking
    mrr = 0.0
    hits = {str(k): 0 for k in k_vals}
    retrieval_details = []
    
    for rank, doc in enumerate(retrieved_docs, start=1):
        found_cwes = extract_doc_labels(doc)
        is_hit = (target_cwe in found_cwes)
        
        if is_hit and mrr == 0:
            mrr = 1.0 / rank
        
        for k in k_vals:
            if is_hit and rank <= k:
                hits[str(k)] = 1

        # Track results for audit trail
        retrieval_details.append({
            "rank": rank,
            "doc_cwes": found_cwes,
            "is_hit": is_hit,
            "doc_snippet": doc.page_content[:200].replace("\n", " ")
        })

    return {
        "mrr": mrr, 
        "hits": hits,
        "generated_summary": search_query if query_mode == "function" else None,
        "retrieval_details": retrieval_details
    }

def main():
    start_time = time.time()
    args = parse_args()
    
    # 1. Initialize Registry and Models
    print(f"[{time.strftime('%H:%M:%S')}] Initializing Registry and Models...")
    registry._init()
    import knowledge 

    MODELS_UTILS.EMBEDDING_MODEL = MODELS_UTILS.create_embedding_client(args.embedding)
    if args.query_mode == "function":
        print(f"[{time.strftime('%H:%M:%S')}] Loading Summary Model: {args.summary_model}")
        MODELS_UTILS.SUMMARY_MODEL = MODELS_UTILS.get_llm_client(args.summary_model)

    # 2. Setup Data
    manifest_gt = load_ground_truth_map(args.manifest)
    samples = load_query_samples(args.input_dir)
    loader = registry.get_knowledgeloader("cpp", args.query_mode)() 

    k_vals = sorted([int(x) for x in args.k_values.split(",")])
    
    results = []
    summary_eval_store = []
    detailed_trace = []
    skipped_count = 0
    
    print(f"[{time.strftime('%H:%M:%S')}] Starting Evaluation on {len(samples)} items...")
    
    # 3. Evaluation Loop
    for s in tqdm(samples, desc="Evaluating Retrieval"):
        target_cwe = manifest_gt.get(s["cve"])
        
        if not target_cwe:
            skipped_count += 1
            continue

        try:
            res = evaluate_sample(s, loader, args.query_mode, k_vals, manifest_gt)
            
            if res:
                results.append(res)
                
                # Store for judge evaluation if using function mode
                if args.query_mode == "function":
                    summary_eval_store.append({
                        "test_id": s["id"],
                        "cve_id": s["cve"],
                        "target_cwe": target_cwe,
                        "source_code": s["func"],
                        "generated_summary": res["generated_summary"],
                        "summary_model": args.summary_model,
                        "system": "llm4vuln"
                    })

                # Store for audit trace
                detailed_trace.append({
                    "query_cve": s["cve"],
                    "target_cwe": target_cwe,
                    "mrr": res["mrr"],
                    "hits": res["hits"],
                    "retrieved_items": res["retrieval_details"]
                })
        except Exception as e:
            print(f"\n[ERROR] Failed to evaluate {s['cve']}: {e}")

    # 4. Aggregation
    total = len(results)
    if total == 0:
        print(f"\n[!] No samples were successfully matched. Skipped: {skipped_count}")
        return

    # Calculate final metrics
    metrics = {"mrr": round(sum(r["mrr"] for r in results) / total, 4)}
    for k in k_vals:
        metrics[f"hit@{k}"] = round(sum(r["hits"][str(k)] for r in results) / total, 4)

    final_stats = {
        "metrics": metrics,
        "config": {
            "summary_model": args.summary_model,
            "embedding": args.embedding,
            "dataset": args.input_dir,
            "manifest": args.manifest,
            "system": "llm4vuln"
        },
        "sample_details": detailed_trace
    }

    # 5. File Output
    os.makedirs(os.path.dirname(args.output_json), exist_ok=True)
    with open(args.output_json, "w", encoding="utf-8") as f:
        json.dump(final_stats, f, indent=4)

    if summary_eval_store:
        os.makedirs(os.path.dirname(args.summary_output), exist_ok=True)
        with open(args.summary_output, "w", encoding="utf-8") as f:
            json.dump(summary_eval_store, f, indent=4)

    # 6. Final Report
    print("\n" + "="*45)
    print(f"      LLM4VULN RETRIEVAL RESULTS")
    print("="*45)
    print(json.dumps(metrics, indent=4))
    print(f"\nSamples Processed: {total} | Skipped: {skipped_count}")
    print(f"Detailed matching log saved to: {args.output_json}")
    print(f"Judge-ready summaries:    {args.summary_output}")
    print(f"Total time: {(time.time()-start_time)/60:.2f} mins")

if __name__ == "__main__":
    main()