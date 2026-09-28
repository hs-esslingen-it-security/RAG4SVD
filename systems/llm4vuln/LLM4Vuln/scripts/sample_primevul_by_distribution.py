import json
import os
import shutil
import random
from pathlib import Path
from collections import defaultdict, Counter

def sample_primevul_by_distribution(distribution_file, primevul_source_file, output_folder, manifest_file):
    """
    Samples pairs from the PrimeVul dataset to match the CWE distribution
    of another dataset.
    """
    random.seed(42)  # For reproducibility

    # 1. Determine the target CWE distribution from the UniVul map
    print(f"Reading target distribution from: {distribution_file}")
    with open(distribution_file, 'r', encoding='utf-8') as f:
        cve_to_cwe_map = json.load(f)
    
    # Count how many times each CWE appears in the UniVul set
    target_distribution = Counter(cve_to_cwe_map.values())
    print("Target CWE Distribution:")
    for cwe, count in target_distribution.items():
        print(f"- {cwe}: {count} examples")

    # 2. Group all available PrimeVul pairs by their CWE
    print(f"\nGrouping PrimeVul data from: {primevul_source_file}")
    cwe_buckets = defaultdict(list)
    with open(primevul_source_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for i in range(0, len(lines), 2):
        if i + 1 >= len(lines): break
        
        entry_a = json.loads(lines[i])
        entry_b = json.loads(lines[i+1])

        # Ensure we have a valid before/after pair
        before, after = (entry_a, entry_b) if entry_a['target'] == 1 else (entry_b, entry_a)
        if not (before.get('target') == 1 and after.get('target') == 0): continue

        # Add the pair to every CWE bucket it belongs to
        entry_cwes = before.get('cwe', [])
        for cwe in entry_cwes:
            cwe_buckets[cwe].append((before, after))
    
    # 3. Sample from PrimeVul buckets to match the target distribution
    sampled_pairs = []
    manifest_entries = []
    seen_indices = set()  # To prevent sampling the same item for different CWEs

    print("\nSampling from PrimeVul to match distribution...")
    for cwe, required_count in target_distribution.items():
        candidates = cwe_buckets.get(cwe, [])
        random.shuffle(candidates)
        
        if len(candidates) < required_count:
            print(f"Warning: Not enough samples for {cwe}. Required: {required_count}, Found: {len(candidates)}. Taking all available.")
        
        count = 0
        for before, after in candidates:
            if count >= required_count: break
            
            # Ensure we don't pick the same pair twice
            if before['idx'] not in seen_indices:
                sampled_pairs.append((before, after))
                seen_indices.add(before['idx'])
                
                manifest_entries.append({
                    "cwe": cwe,
                    "cve": before.get("cve", "UNKNOWN"),
                    "idx_vulnerable": before['idx'],
                    "idx_fixed": after['idx']
                })
                count += 1
        
        if count < required_count:
            print(f"Could only fulfill {count}/{required_count} for {cwe}")

    # 4. Save the sampled data in the LLM4Vuln format
    os.makedirs(output_folder, exist_ok=True)
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

    # 5. Save the manifest file for reproducibility
    with open(manifest_file, 'w', encoding='utf-8') as f:
        f.write("CWE_ID | CVE_ID | VULNERABLE_IDX | FIXED_IDX\n")
        f.write("-" * 50 + "\n")
        for entry in sorted(manifest_entries, key=lambda x: (x['cwe'], x['cve'])):
            f.write(f"{entry['cwe']} | {entry['cve']} | {entry['idx_vulnerable']} | {entry['idx_fixed']}\n")

    print(f"\nSuccess! Sampled {len(sampled_pairs)} pairs.")
    print(f"- JSON files created in: '{output_folder}'")
    print(f"- Manifest saved to: '{manifest_file}'")


if __name__ == "__main__":
    sample_primevul_by_distribution(
        distribution_file="../dataset/original_cpp_cwe_map.json",
        primevul_source_file="../dataset/primevul_test_paired.jsonl", 
        output_folder="../dataset/cpp_primevul_sampled_univul_dist", 
        manifest_file="../dataset/primevul_sampled_univul_dist_manifest.txt"
    )

# Target CWE Distribution:
# - CWE-189: 2 examples
# - CWE-532: 1 examples
# - CWE-20: 8 examples
# - CWE-119: 8 examples
# - CWE-399: 2 examples
# - CWE-190: 3 examples
# - CWE-310: 1 examples
# - CWE-264: 3 examples
# - CWE-200: 2 examples
# - CWE-17: 1 examples
# - CWE-269: 1 examples
# - CWE-125: 3 examples
# - CWE-354: 1 examples
# - CWE-347: 2 examples
# - CWE-416: 1 examples
# - CWE-184: 1 examples
# - CWE-209: 1 examples
# - CWE-704: 2 examples
# - CWE-362: 1 examples
# - CWE-835: 2 examples
# - CWE-59: 1 examples
# - CWE-787: 2 examples
# - CWE-78: 1 examples

# Grouping PrimeVul data from: ../dataset/primevul_test_paired.jsonl

# Sampling from PrimeVul to match distribution...
# Warning: Not enough samples for CWE-532. Required: 1, Found: 0. Taking all available.
# Could only fulfill 0/1 for CWE-532
# Warning: Not enough samples for CWE-264. Required: 3, Found: 1. Taking all available.
# Could only fulfill 1/3 for CWE-264
# Warning: Not enough samples for CWE-347. Required: 2, Found: 0. Taking all available.
# Could only fulfill 0/2 for CWE-347
# Warning: Not enough samples for CWE-184. Required: 1, Found: 0. Taking all available.
# Could only fulfill 0/1 for CWE-184
# Warning: Not enough samples for CWE-209. Required: 1, Found: 0. Taking all available.
# Could only fulfill 0/1 for CWE-209
# Warning: Not enough samples for CWE-78. Required: 1, Found: 0. Taking all available.
# Could only fulfill 0/1 for CWE-78

# Success! Sampled 42 pairs.
# - JSON files created in: '../dataset/cpp_primevul_sampled_univul_dist'