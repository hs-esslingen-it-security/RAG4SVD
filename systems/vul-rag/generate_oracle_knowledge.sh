#!/bin/bash

# -----------------------------
# Configuration
# -----------------------------
MODEL="$1"
#DATA_DIR="data/test"
#DATA_DIR="data/test_primevul_subset"
DATA_DIR="data/test_primevul_oracle_subset"

# -----------------------------
# Iterate over combinations
# -----------------------------
echo "============================================================"
echo "Starting Oracle Knowledge Extraction for Model: ${MODEL}"
echo "============================================================"

for INPUT_FILE in "$DATA_DIR"/*.json; do
  FILENAME=$(basename "$INPUT_FILE")
  echo "------------------------------------------------------------"
  echo "Processing File:  ${INPUT_FILE}"
  echo "Model:            ${MODEL}"
  echo "------------------------------------------------------------"

  python src/extract_knowledge.py \
    --input_file_name "${INPUT_FILE}" \
    --model_name "${MODEL}" \
    --thread_pool_size 1 \
    --model_settings "temperature=0.01" \
    --resume \
    --output_kb_name "primevul-oracle-${MODEL}"

  echo "Finished processing ${FILENAME}"
done

echo "🎯 Knowledge generation finished for all files in ${DATA_DIR}."