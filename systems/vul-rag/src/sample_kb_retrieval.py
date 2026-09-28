import json
import os
import random
import re
from pathlib import Path
from collections import defaultdict

def align_and_backfill(manifest_path, original_test_dir, output_dir):
    random.seed(42)  # For reproducibility
    
    # Define Quotas
    quotas = {
        "CWE-20": 5, "CWE-119": 5, "CWE-125": 5, "CWE-200": 5,
        "CWE-264": 1, "CWE-362": 5, "CWE-401": 5, "CWE-416": 5,
        "CWE-476": 5, "CWE-787": 5
    }

    # 1. Parse Manifest to get priority CVEs
    priority_cve_by_cwe = defaultdict(set)
    print(f"Reading manifest: {manifest_path}")
    with open(manifest_path, 'r', encoding='utf-8') as f:
        lines = [l for l in f.readlines() if "|" in l and "VULNERABLE_IDX" not in l and "---" not in l]
        for line in lines:
            parts = [p.strip() for p in line.split('|')]
            if len(parts) >= 2:
                priority_cve_by_cwe[parts[0]].add(parts[1])

    # 2. Scan Original Test Set and build a pool of candidates
    original_pool = defaultdict(list)
    print(f"Scanning original test directory: {original_test_dir}")
    for json_file in Path(original_test_dir).glob("*_testset.json"):
        # Heuristic to detect CWE from filename (e.g., linux_kernel_CWE-20_testset.json)
        cwe_match = re.search(r"CWE-\d+", json_file.name)
        if not cwe_match: continue
        file_cwe = cwe_match.group(0)

        with open(json_file, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
                entries = data if isinstance(data, list) else [data]
                original_pool[file_cwe].extend(entries)
            except: continue

    # 3. Sample
    final_samples = defaultdict(list)
    sampling_log = []

    for cwe, target_count in quotas.items():
        candidates = original_pool.get(cwe, [])
        if not candidates:
            print(f"Warning: No candidates found for {cwe} in original test set.")
            continue

        # Split candidates into "Priority" (in manifest) and "Others"
        priority_matches = [e for e in candidates if e.get("cve_id") in priority_cve_by_cwe[cwe]]
        others = [e for e in candidates if e.get("cve_id") not in priority_cve_by_cwe[cwe]]
        
        # Shuffle others for random backfilling
        random.shuffle(others)

        # Build the final set for this CWE
        selected = []
        for e in priority_matches:
            if len(selected) < target_count:
                selected.append(e)
                sampling_log.append(f"{cwe} | {e.get('cve_id')} | MATCHED")

        # Backfill if necessary
        while len(selected) < target_count and others:
            e = others.pop()
            selected.append(e)
            sampling_log.append(f"{cwe} | {e.get('cve_id')} | SUBSTITUTED")

        final_samples[cwe] = selected
        print(f"Finalized {cwe}: {len(selected)} samples ({len(priority_matches)} matched, {target_count - len(priority_matches)} backfilled)")

    # 4. Save
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    
    for cwe, entries in final_samples.items():
        with open(out_path / f"original_sampled_{cwe}_testset.json", "w") as f:
            json.dump(entries, f, indent=4)

    # 5. Save Log
    with open("original_test_sampling_log.txt", "w") as f:
        f.write("CWE | CVE_ID | STATUS\n" + "-"*30 + "\n")
        f.write("\n".join(sampling_log))


def process_vul_rag_minimal(dataset_path, manifest_path, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 1. Parse Manifest to identify the specific sampled pairs
    # Expected format: CWE_ID | CVE_ID | VULNERABLE_IDX | FIXED_IDX
    targets = {} 
    needed_ids = set()
    
    print(f"Reading manifest: {manifest_path}")
    with open(manifest_path, 'r', encoding='utf-8') as f:
        # filter lines to ensure we only get data lines
        lines = [l for l in f.readlines() if "|" in l and "VULNERABLE_IDX" not in l and "---" not in l]
        for line in lines:
            parts = [p.strip() for p in line.split('|')]
            cwe_id, _, v_idx, f_idx = parts
            v_idx, f_idx = int(v_idx), int(f_idx)
            targets[v_idx] = {"cwe": cwe_id, "fixed_idx": f_idx}
            needed_ids.add(v_idx)
            needed_ids.add(f_idx)

    # 2. Read Dataset to grab the code for those specific IDs
    data_store = {}
    print(f"Searching dataset: {dataset_path}")
    with open(dataset_path, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip(): continue
            entry = json.loads(line)
            idx = int(entry['idx'])
            if idx in needed_ids:
                data_store[idx] = entry

    # 3. Process pairs and group by CWE
    cwe_files_content = defaultdict(list)
    global_id_counter = 1

    for v_idx, info in targets.items():
        v_entry = data_store.get(v_idx)
        f_entry = data_store.get(info['fixed_idx'])
        
        if not v_entry or not f_entry:
            print(f"Warning: Missing code for IDX {v_idx}")
            continue

        cwe_label = info['cwe']

        # Construct the minimal entry
        rag_entry = {
            "cve_id": v_entry.get("cve", "UNKNOWN"),
            "code_before_change": v_entry.get("func", ""),
            "code_after_change": f_entry.get("func", ""),
            "cwe": [cwe_label],
            "cve_description": v_entry.get("cve_desc", ""),
            "id": global_id_counter
        }
        
        cwe_files_content[cwe_label].append(rag_entry)
        global_id_counter += 1

    # 4. Save individual CWE files
    for cwe_label, entries in cwe_files_content.items():
        filename = f"primevul_paired-{cwe_label}_testset.json"
        filepath = os.path.join(output_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as out_f:
            json.dump(entries, out_f, indent=4)
        print(f"Successfully created: {filepath} ({len(entries)} entries)")
