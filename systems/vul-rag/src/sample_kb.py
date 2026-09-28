import json
import random
import os
from pathlib import Path

# --- Configuration ---
SEED = 42
INPUT_DIR = "../vulnerability_knowledge"
OUTPUT_BASE_DIR = "../add_vulnerability_knowledge"

DATASETS = [
    "linux_kernel_CWE-20",
    "linux_kernel_CWE-119",
    "linux_kernel_CWE-125",
    "linux_kernel_CWE-200",
    "linux_kernel_CWE-264",
    "linux_kernel_CWE-362",
    "linux_kernel_CWE-401",
    "linux_kernel_CWE-416",
    "linux_kernel_CWE-476",
    "linux_kernel_CWE-787"
]

def main():
    random.seed(SEED)

    # Trace dictionary to store which IDs are in which sample for later analysis
    sampling_log = {p: {} for p in [25, 50, 75]}
    
    for p in [25, 50, 75]:
        # Path logic: add_vulnerability_knowledge/vulrag_25, etc.
        out_dir = Path(OUTPUT_BASE_DIR) / f"vulrag_{p}"
        out_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"--- Sampling {p}% into {out_dir} ---")
        
        for dataset in DATASETS:
            filename = f"{dataset}_knowledge.json"
            input_path = Path(INPUT_DIR) / filename
            output_path = out_dir / filename
            
            if not input_path.exists():
                print(f"Skipping: {filename} (not found)")
                continue
                
            with open(input_path, "r") as f:
                data = json.load(f)
            
            # Calculate sample size
            sample_size = int(len(data) * (p / 100))
            if len(data) > 0 and sample_size == 0:
                sample_size = 1
                
            sampled_data = random.sample(data, sample_size)
            sampling_log[p][dataset] = [item["CVE_id"] for item in sampled_data]
            
            with open(output_path, "w") as f:
                json.dump(sampled_data, f, indent=4)
            
            print(f"  {dataset}: {len(data)} -> {len(sampled_data)}")

        log_path = Path(OUTPUT_BASE_DIR) / "sampling_log.json"
        with open(log_path, "w") as f:
            json.dump(sampling_log, f, indent=4)
        print(f"Log saved to {log_path}.")

if __name__ == "__main__":
    main()