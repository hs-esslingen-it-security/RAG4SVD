#!/usr/bin/env python3
import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple
import time
from tqdm import tqdm

# Setup Paths for Vul-RAG internal imports
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))

# Vul-RAG Internal Imports
import utils.llm_client as llm_client
import utils.bm25_retriever as bm25_retriever
import vulnerability_detect
from vulnerability_detect import (
    generate_extraction_prompt_for_vulrag, 
    retrieve_knowledge_by_cve
)

# Global map to store KB CVE -> CWE relationship
KB_CVE_TO_CWE = {}

def parse_args():
    parser = argparse.ArgumentParser(description="Vul-RAG CWE-Agreement Retrieval Evaluation")
    parser.add_argument("--input-dir", default="..data/test_original_sampled")
    parser.add_argument("--manifest", default="..data/original_test_sampling_log.txt")
    parser.add_argument("--knowledge-dir", default="../vulnerability_knowledge")
    parser.add_argument("--summary-model", default="qwen2.5-7b-instruct")
    parser.add_argument("--k-values", default="1,3,5")
    parser.add_argument("--retrieval_top_k", type=int, default=20)
    parser.add_argument("--summary-output", default="../output/summary/summary_quality_eval.json")
    parser.add_argument("--output-json", default="../output/kb_retrieval/retrieval_details_vulrag.json", help="Path to save detailed retrieval results and metrics")
    return parser.parse_args()

def load_ground_truth_map(manifest_path: str) -> Dict[str, str]:
    mapping = {}
    p = Path(manifest_path)
    if not p.exists():
        print(f"Error: Manifest {manifest_path} not found.")
        sys.exit(1)
        
    with open(p, 'r', encoding='utf-8') as f:
        for line in f:
            if "|" in line and "CWE_ID" not in line and "---" not in line and "CWE |" not in line:
                parts = [p.strip() for p in line.split('|')]
                mapping[parts[1]] = parts[0]
    return mapping

def prepare_global_knowledge(args):
    global KB_CVE_TO_CWE
    all_kb = []
    path = Path(args.knowledge_dir).resolve()
    
    print(f"[{time.strftime('%H:%M:%S')}] Building Knowledge Base from {args.knowledge_dir}...")
    for json_file in path.glob("*_knowledge.json"):
        cwe_match = re.search(r"CWE-\d+", json_file.name, re.IGNORECASE)
        file_cwe = cwe_match.group(0).upper() if cwe_match else "UNKNOWN"
        
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            entries = data if isinstance(data, list) else [data]
            for item in entries:
                all_kb.append(item)
                KB_CVE_TO_CWE[item["CVE_id"].upper()] = file_cwe

    temp_kb_path = os.path.join(str(path), "temp_eval_kb.json")
    os.makedirs(os.path.dirname(temp_kb_path), exist_ok=True)

    with open(temp_kb_path, "w") as f:
        json.dump(all_kb, f)
    args.knowledge_file_name = "temp_eval_kb.json"

    vulnerability_detect.GLOBAL_CVE_KNOWLEDGE_DICT = {
        cid: [i for i in all_kb if i["CVE_id"] == cid] 
        for cid in set(i["CVE_id"] for i in all_kb)
    }

    vulnerability_detect.GLOBAL_KNOWLEDGE_LIST = all_kb

    vulnerability_detect.GLOBAL_PURPOSE_RETRIEVER = bm25_retriever.BM25Retriever()
    vulnerability_detect.GLOBAL_PURPOSE_RETRIEVER.set_corpus([i["GPT_purpose"] for i in all_kb])
    vulnerability_detect.GLOBAL_FUNCTION_RETRIEVER = bm25_retriever.BM25Retriever()
    vulnerability_detect.GLOBAL_FUNCTION_RETRIEVER.set_corpus([i["GPT_function"] for i in all_kb])
    vulnerability_detect.GLOBAL_CODE_RETRIEVER = bm25_retriever.BM25Retriever()
    vulnerability_detect.GLOBAL_CODE_RETRIEVER.set_corpus([i["code_before_change"] for i in all_kb])
    
    return temp_kb_path

def get_summary_data(model, code):
    p_prompt, f_prompt = generate_extraction_prompt_for_vulrag(code)
    p_out = model.generate_text(llm_client.generate_simple_prompt(p_prompt))
    purpose = llm_client.extract_LLM_response_by_prefix(p_out, "Function purpose:")
    f_out = model.generate_text(llm_client.generate_simple_prompt(f_prompt))
    function = llm_client.extract_LLM_response_by_prefix(f_out, "The functions of the code snippet are:")
    return purpose, function

def main():
    start_time = time.time()
    args = parse_args()

    args.knowledge_dir = str(Path(args.knowledge_dir).resolve())
    args.input_dir = str(Path(args.input_dir).resolve())
    
    # 1. Setup Models & Metadata
    print(f"[{time.strftime('%H:%M:%S')}] Loading Model: {args.summary_model}")
    vulnerability_detect.SUMMARY_LLM_CLIENT = llm_client.get_llm_client(args.summary_model)


    manifest_path = str(Path(args.manifest).resolve())
    gt_map = load_ground_truth_map(manifest_path)
    temp_file = prepare_global_knowledge(args)
    
    # 2. Load Samples (Handles single objects or lists)
    samples = []
    for json_file in Path(args.input_dir).glob("*.json"):
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            entries = data if isinstance(data, list) else [data]
            for entry in entries:
                func = entry.get("code_before_change") or \
                       (entry.get("code_before_patch", {}) if isinstance(entry.get("code_before_patch"), dict) else {}).get("code")
                if func:
                    samples.append({
                        "id": entry.get("id", "N/A"),
                        "func": func,
                        "cve": (entry.get("cve_id") or entry.get("cve") or "").upper(),
                    })

    k_vals = sorted([int(x) for x in args.k_values.split(",")])
    args.max_knowledge = max(k_vals) 
    
    results = []
    summary_eval_store = []
    detailed_trace = []

    print(f"[{time.strftime('%H:%M:%S')}] Starting Evaluation on {len(samples)} samples...")

    for s in tqdm(samples, desc="Evaluating Retrieval"):
        target_cwe = gt_map.get(s["cve"])
        if not target_cwe:
            continue

        try:
            # A. Generate Summaries
            purpose, function = get_summary_data(vulnerability_detect.SUMMARY_LLM_CLIENT, s["func"])
            
            summary_eval_store.append({
                "test_id": s["id"],
                "cve_id": s["cve"],
                "target_cwe": target_cwe,
                "source_code": s["func"],
                "generated_purpose": purpose,
                "generated_function": function,
                "summary_model": args.summary_model,
                "system": "vulrag"
            })

            # B. Run Production Retrieval
            retrieved_items = retrieve_knowledge_by_cve(args, s["func"], purpose, function)
            
            mrr = 0.0
            hits = {str(k): 0 for k in k_vals}
            retrieval_metadata = []
            
            for rank, item in enumerate(retrieved_items, start=1):
                kb_cve = item["cve_id"].upper()
                kb_cwe = KB_CVE_TO_CWE.get(kb_cve, "UNKNOWN")
                
                is_hit = bool(kb_cwe == target_cwe)

                if is_hit:
                    if mrr == 0: mrr = 1.0 / rank
                    for k in k_vals:
                        if rank <= k: hits[str(k)] = 1
                
                retrieval_metadata.append({
                    "rank": rank,
                    "kb_cve_id": kb_cve,
                    "kb_cwe_id": kb_cwe,
                    "is_hit": is_hit
                })
            
            results.append({"mrr": mrr, "hits": hits})
            detailed_trace.append({
                "test_id": s["id"],
                "query_cve": s["cve"],
                "target_cwe": target_cwe,
                "mrr": mrr,
                "hits": hits,
                "retrieved_items": retrieval_metadata
            })

        except Exception as e:
            print(f"\n[ERROR] Failed processing {s['cve']}: {e}")

    # 3. Final Aggregation
    total = len(results)
    if total == 0:
        print("\n[!] No samples were successfully matched. Check manifest alignment.")
        if os.path.exists(temp_file): os.remove(temp_file)
        return

    # Dynamic metrics based on k-values
    final_metrics = {"mrr": round(sum(r["mrr"] for r in results) / total, 4)}
    for k in k_vals:
        final_metrics[f"hit@{k}"] = round(sum(r["hits"][str(k)] for r in results) / total, 4)

    final_stats = {
        "metrics": final_metrics,
        "config": {
            "summary_model": args.summary_model,
            "dataset": args.input_dir,
            "manifest": args.manifest,
            "k_values": k_vals,
            "system": "vulrag"
        },
        "sample_details": detailed_trace 
    }

    # 4. Save and Print Results
    os.makedirs(os.path.dirname(args.output_json), exist_ok=True)
    with open(args.output_json, "w", encoding="utf-8") as f:
        json.dump(final_stats, f, indent=4)
        
    os.makedirs(os.path.dirname(args.summary_output), exist_ok=True)
    with open(args.summary_output, "w", encoding="utf-8") as f:
        json.dump(summary_eval_store, f, indent=4)

    print("\n" + "="*45)
    print(f"      VUL-RAG RETRIEVAL RESULTS")
    print("="*45)
    print(json.dumps(final_metrics, indent=4))
    print(f"\nDetailed metrics & trace: {args.output_json}")
    print(f"Judge-ready summaries:    {args.summary_output}")
    print(f"Total time: {(time.time()-start_time)/60:.2f} mins")
    
    if os.path.exists(temp_file):
        os.remove(temp_file)

if __name__ == "__main__":
    main()