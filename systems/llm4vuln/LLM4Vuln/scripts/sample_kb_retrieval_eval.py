import json
import os
import shutil
import random
from pathlib import Path
from collections import defaultdict

def sample_transform_and_log(input_file, output_folder, manifest_file):
    target_cwes = [
        "CWE-20", "CWE-119", "CWE-125", "CWE-200", "CWE-264", 
        "CWE-362", "CWE-401", "CWE-416", "CWE-476", "CWE-787"
    ]

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"Error: Could not find input file at {input_file}")
        return

    # 1. Group all valid pairs into CWE buckets
    cwe_buckets = defaultdict(list)
    for i in range(0, len(lines), 2):
        if i + 1 >= len(lines):
            break
            
        entry_a = json.loads(lines[i])
        entry_b = json.loads(lines[i+1])

        before, after = None, None
        if entry_a['target'] == 1 and entry_b['target'] == 0:
            before, after = entry_a, entry_b
        elif entry_b['target'] == 1 and entry_a['target'] == 0:
            before, after = entry_b, entry_a
        else:
            continue

        entry_cwes = before.get('cwe', [])
        for cwe in entry_cwes:
            if cwe in target_cwes:
                cwe_buckets[cwe].append((before, after))

    # 2. Sample 5 unique pairs per CWE
    sampled_pairs = []
    manifest_entries = [] # To store details for the TXT file
    seen_indices = set() 

    print("Sampling 5 examples per CWE...")
    for cwe_id in target_cwes:
        candidates = cwe_buckets[cwe_id]
        random.shuffle(candidates)
        
        count = 0
        for before, after in candidates:
            if count >= 5:
                break
            
            if before['idx'] not in seen_indices:
                sampled_pairs.append((before, after))
                seen_indices.add(before['idx'])
                
                # Record for manifest
                manifest_entries.append({
                    "cwe": cwe_id,
                    "cve": before.get("cve", "UNKNOWN"),
                    "idx_vulnerable": before['idx'],
                    "idx_fixed": after['idx']
                })
                count += 1
        
        if count < 5:
            print(f"Warning: Only found {count} examples for {cwe_id}")

    # 3. Transform and Save JSON files
    for before, after in sampled_pairs:
        cve_id = before.get("cve")
        filename = f"{cve_id}.json" if cve_id and str(cve_id).lower() != "none" else f"UNKNOWN_{before['idx']}.json"

        output_data = {
            "cve": cve_id,
            "repo_remote": before.get("project_url"),
            "repo_local": "NOT NEEDED",
            "cve_info": before.get("cve_desc"),
            "code_before_patch": {"code": before.get("func"), "related": []},
            "code_after_patch": {"code": after.get("func"), "related": []}
        }

        with open(os.path.join(output_folder, filename), 'w', encoding='utf-8') as out_f:
            json.dump(output_data, out_f, indent=4)

    # 4. Create the Manifest TXT file
    with open(manifest_file, 'w', encoding='utf-8') as f:
        f.write("CWE_ID | CVE_ID | VULNERABLE_IDX | FIXED_IDX\n")
        f.write("-" * 50 + "\n")
        for entry in manifest_entries:
            f.write(f"{entry['cwe']} | {entry['cve']} | {entry['idx_vulnerable']} | {entry['idx_fixed']}\n")

    print(f"Success!")
    print(f"- {len(sampled_pairs)} JSON files in '{output_folder}'")
    print(f"- Manifest saved to '{manifest_file}'")

def sample_original_using_primevul_metadata(primevul_jsonl, src_dir, output_dir, manifest_out):
    random.seed(42)
    
    target_cwes = [
        "CWE-20", "CWE-119", "CWE-125", "CWE-200", "CWE-264", 
        "CWE-362", "CWE-401", "CWE-416", "CWE-476", "CWE-787"
    ]
    quotas = {cwe: 5 for cwe in target_cwes}
    quotas["CWE-264"] = 1

    # 1. Build a Global Dictionary of CVE -> CWE from the large PrimeVul file
    # This works even if the CVE is not in the Knowledge Base
    cve_to_cwe_dictionary = {}
    print(f"Building CVE dictionary from {primevul_jsonl}...")
    with open(primevul_jsonl, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip(): continue
            entry = json.loads(line)
            cve = entry.get("cve")
            cwes = entry.get("cwe")
            if cve and cwes:
                # Use the first CWE listed for that CVE
                cve_to_cwe_dictionary[cve] = cwes[0]

    # 2. Categorize the individual LLM4Vuln JSON files using our dictionary
    pool = defaultdict(list)
    src_path = Path(src_dir)
    print(f"Categorizing files in {src_dir}...")
    
    for json_file in src_path.glob("CVE-*.json"):
        cve_id = json_file.stem # e.g. CVE-2009-3605
        if cve_id in cve_to_cwe_dictionary:
            cwe = cve_to_cwe_dictionary[cve_id]
            if cwe in target_cwes:
                pool[cwe].append(json_file)

    # 3. Balanced Sampling
    os.makedirs(output_dir, exist_ok=True)
    manifest_lines = []
    
    print("\nSampling Results:")
    for cwe in target_cwes:
        candidates = pool[cwe]
        target = quotas[cwe]
        
        if len(candidates) < target:
            print(f"!! Warning: Only found {len(candidates)} files for {cwe}")
            sampled = candidates
        else:
            sampled = random.sample(candidates, target)
            print(f"-- {cwe}: Sampled {target} files")

        for f in sampled:
            shutil.copy(f, os.path.join(output_dir, f.name))
            # Create a dummy manifest for the retrieval script
            manifest_lines.append(f"{cwe} | {f.stem} | 0 | 0")

    # 4. Save the manifest
    with open(manifest_out, "w") as f:
        f.write("CWE_ID | CVE_ID | VULNERABLE_IDX | FIXED_IDX\n")
        f.write("-" * 50 + "\n")
        f.write("\n".join(manifest_lines))
    
    print(f"\nDone! Folder: {output_dir}")
    print(f"Manifest: {manifest_out}")


if __name__ == "__main__":
    # sample_transform_and_log(
    #     input_file="../dataset/primevul_test_paired.jsonl", 
    #     output_folder="../dataset/cpp_primevul_sampled", 
    #     manifest_file="../dataset/cpp_primevul_sampled/sampled_pairs_manifest.txt"
    # )

    sample_original_using_primevul_metadata(
        primevul_jsonl="../dataset/primevul_test_paired.jsonl", # The big source file
        src_dir="../dataset/cpp",                                  # The original JSON folder
        output_dir="../dataset/cpp_original_sampled",              # Output
        manifest_out="../dataset/cpp_original_manifest.txt"        # Output manifest
    )