#!/usr/bin/env python3
import json
import csv
import re
import argparse
import sys
from pathlib import Path
from collections import defaultdict

def parse_args():
    parser = argparse.ArgumentParser(description="Bulk Hierarchical CWE Evaluation")
    parser.add_argument("--input-dir", default="../output/kb_retrieval", help="Folder containing result JSONs")
    parser.add_argument("--cwe-csv", default="../data/1000_28052026.csv", help="Path to 1000_28052026.csv")
    parser.add_argument("--k-values", default="1,3,5", help="K values to evaluate")
    parser.add_argument("--output-json", default="../output/kb_retrieval/hierarchical_analysis_summary.json")
    return parser.parse_args()

def load_cwe_hierarchy(csv_path):
    """Builds the hierarchy graph from the official CWE-1000 CSV."""
    parents_map = defaultdict(set)
    children_map = defaultdict(set)
    
    if not Path(csv_path).exists():
        print(f"Error: CWE CSV file {csv_path} not found.")
        sys.exit(1)

    with open(csv_path, mode='r', encoding='utf-8', errors='ignore') as f:
        reader = csv.DictReader(f)
        for row in reader:
            cwe_id = f"CWE-{row['CWE-ID']}".upper()
            related_str = row.get('Related Weaknesses', '')
            # Match ChildOf relations in View 1000 (Research View)
            matches = re.findall(r"NATURE:ChildOf:CWE ID:(\d+):VIEW ID:1000", related_str)
            for m in matches:
                parent_id = f"CWE-{m}".upper()
                parents_map[cwe_id].add(parent_id)
                children_map[parent_id].add(cwe_id)
                
    return parents_map, children_map

def evaluate_json_file(file_path, parents_map, children_map, k_list):
    with open(file_path, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
        except Exception:
            return None

    # Use 'sample_details' which contains the trace of each evaluated item
    samples = data.get("sample_details", [])
    if not samples:
        return None

    #Denom logic: Original script uses total = len(results)
    #In your original script, 'sample_details' is only appended to if 'res' exists.
    #So len(samples) here should equal 'total' from your original run.
    total = len(samples)
    config = data.get("config", {})
    
    file_stats = {
        "experiment_meta": {
            "model": config.get('summary_model', 'N/A'),
            "file": file_path.name,
            "sample_size": total
        },
        "metrics": {}
    }
    
    for k in k_list:
        exact_cnt = 0
        parent_cnt = 0
        child_cnt = 0
        combined_cnt = 0
        
        for sample in samples:
            target = sample["target_cwe"].upper()
            # Items retrieved in the original experiment
            retrieved = sample.get("retrieved_items", [])
            
            # Warn if we are checking a K higher than what was actually retrieved
            if k > len(retrieved) and len(retrieved) > 0:
                # This is a silent warn to avoid log spam, but explains discrepancy
                pass

            target_parents = parents_map.get(target, set())
            target_children = children_map.get(target, set())

            found_exact = False
            found_parent = False
            found_child = False
            
            # Iterate through the retrieved items up to K
            for item in retrieved[:k]:
                # Standardize found CWEs from the document
                retrieved_cwe = str(item.get("kb_cwe_id", "")).upper()
                
                if retrieved_cwe == target: 
                    found_exact = True
                if retrieved_cwe in target_parents: 
                    found_parent = True
                if retrieved_cwe in target_children: 
                    found_child = True
            
            if found_exact: exact_cnt += 1
            if found_parent: parent_cnt += 1
            if found_child: child_cnt += 1
            if (found_exact or found_parent or found_child): 
                combined_cnt += 1

        file_stats["metrics"][f"k_{k}"] = {
            "exact_hit_rate": round(exact_cnt / total, 4),
            "hierarchical_hit_rate": round(combined_cnt / total, 4),
            "breakdown": {
                "parent_only_hit_rate": round(parent_cnt / total, 4),
                "child_only_hit_rate": round(child_cnt / total, 4)
            },
            "raw_counts": {"exact": exact_cnt, "total": total}
        }
        
    return file_stats

def main():
    args = parse_args()
    k_list = sorted([int(x.strip()) for x in args.k_values.split(",")])
    
    parents_map, children_map = load_cwe_hierarchy(args.cwe_csv)
    input_path = Path(args.input_dir)
    json_files = list(input_path.glob("*.json"))
    
    all_results = []
    for f in json_files:
        if f.name == args.output_json: continue
        res = evaluate_json_file(f, parents_map, children_map, k_list)
        if res: all_results.append(res)

    with open(args.output_json, 'w', encoding='utf-8') as out_f:
        json.dump(all_results, out_f, indent=4)

    # CLI Output
    print("\n" + "="*100)
    print(f"{'Model':<35} | {'N':<4} | {'K':<2} | {'Exact':<8} | {'Hierarchical (Any)'}")
    print("="*100)

    for entry in all_results:
        meta = entry["experiment_meta"]
        for k in k_list:
            m = entry["metrics"][f"k_{k}"]
            label = f"{meta['model']}"
            print(f"{label[:35]:<35} | {meta['sample_size']:<4} | {k:<2} | {m['exact_hit_rate']:>7.1%} | {m['hierarchical_hit_rate']:>7.1%}")
        print("-" * 100)

if __name__ == "__main__":
    main()