#!/bin/bash
if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <MODEL_NAME>"
  exit 1
fi
MODEL="$1"
SM="${MODEL}"

# Stop on errors and undefined variables
# set -euo pipefail

export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

DATASETS=(
  "primevul_CWE-119"
  "primevul_CWE-120"
  "primevul_CWE-122"
  "primevul_CWE-125"
  "primevul_CWE-134"
  "primevul_CWE-17"
  "primevul_CWE-189"
  "primevul_CWE-190"
  "primevul_CWE-193"
  "primevul_CWE-20"
  "primevul_CWE-200"
  "primevul_CWE-212"
  "primevul_CWE-22"
  "primevul_CWE-252"
  "primevul_CWE-264"
  "primevul_CWE-269"
  "primevul_CWE-276"
  "primevul_CWE-284"
  "primevul_CWE-287"
  "primevul_CWE-295"
  "primevul_CWE-310"
  "primevul_CWE-327"
  "primevul_CWE-345"
  "primevul_CWE-354"
  "primevul_CWE-362"
  "primevul_CWE-369"
  "primevul_CWE-399"
  "primevul_CWE-400"
  "primevul_CWE-401"
  "primevul_CWE-415"
  "primevul_CWE-416"
  "primevul_CWE-444"
  "primevul_CWE-476"
  "primevul_CWE-522"
  "primevul_CWE-59"
  "primevul_CWE-617"
  "primevul_CWE-665"
  "primevul_CWE-668"
  "primevul_CWE-672"
  "primevul_CWE-703"
  "primevul_CWE-704"
  "primevul_CWE-732"
  "primevul_CWE-754"
  "primevul_CWE-770"
  "primevul_CWE-772"
  "primevul_CWE-787"
  "primevul_CWE-79"
  "primevul_CWE-824"
  "primevul_CWE-834"
  "primevul_CWE-835"
  "primevul_CWE-843"
  "primevul_CWE-862"
  "primevul_CWE-863"
  "primevul_CWE-908"
  "primevul_CWE-909"
  "primevul_CWE-94"
)

# -----------------------------
# Log directory / Paths
# -----------------------------
OUT_ROOT="benchmark_results_vulrag"
LOG_DIR="logs"
mkdir -p "${OUT_ROOT}" "${LOG_DIR}"

resolve_knowledge_base() {
  local dataset_name="$1"

  if [[ "${dataset_name}" == primevul_* ]]; then
    echo "vulnerability_knowledge_primevul_qwen14b"
  else
    echo "vulnerability_knowledge"
  fi
}

# -----------------------------
# Iterate over datasets for this one model
# -----------------------------
MODEL_SM_DIR="${OUT_ROOT}/${MODEL}__sum-${SM}"
mkdir -p "${MODEL_SM_DIR}"

echo "============================================================"
echo "Combo: detect=${MODEL} | summary=${SM}"
echo "Output dir: ${MODEL_SM_DIR}"
echo "Started at: $(date)"
echo "Device: Dachs"
echo "============================================================"

for DATASET in "${DATASETS[@]}"; do
  BASE="${DATASET}"
  OUT_FILE="${BASE}_result_${MODEL}__sum-${SM}.json"
  OUT_PATH="${MODEL_SM_DIR}/${OUT_FILE}"
  LOG_FILE="${LOG_DIR}/detect__${MODEL}__sum-${SM}__${BASE}.log"
  KNOW_FILE="${BASE}_knowledge.json"
  KNOW_BASE_DIR="$(resolve_knowledge_base "${BASE}")"
  KNOW_SOURCE_PATH="${KNOW_BASE_DIR}/${KNOW_FILE}"

  echo "------------------------------------------------------------"
  echo "Running detect"
  echo "  detect model : ${MODEL}"
  echo "  summary model: ${SM}"
  echo "  dataset      : ${DATASET}_testset.json"
  echo "  knowledge    : ${KNOW_SOURCE_PATH}"
  echo "  out          : ${OUT_PATH}"
  echo "  log          : ${LOG_FILE}"
  echo "  Started at: $(date)"
  echo "  device       : Dachs"
  echo "------------------------------------------------------------"

  {
    echo "START detect ${MODEL} + ${SM} on ${DATASET}"
    set -x
    python src/vulnerability_detect_benchmark.py \
      --input_file_name "${BASE}_testset.json" \
      --output_file_name "${MODEL}__sum-${SM}/${OUT_FILE}" \
      --knowledge_file_name "${KNOW_FILE}" \
      --knowledge_base_dir "${KNOW_BASE_DIR}" \
      --model_name "${MODEL}" \
      --summary_model_name "${SM}" \
      --retrieval_top_k 20 \
      --thread_pool_size 1 \
      --resume \
      --early_return \
      --model_settings "temperature=0.01" \
      --max_knowledge 3
    { set +x; } 2>/dev/null
    echo "DONE  detect ${MODEL} + ${SM} on ${DATASET}"
  } |& tee "${LOG_FILE}"
done

# -----------------------------
# Evaluate this model's folder
# -----------------------------
echo "============================================================"
echo "Evaluating results for: ${MODEL_SM_DIR}"
echo "============================================================"

MODEL_SM_JSONS=()
for DATASET in "${DATASETS[@]}"; do
  CANDIDATE="${MODEL_SM_DIR}/${DATASET}_result_${MODEL}__sum-${SM}.json"
  [[ -f "${CANDIDATE}" ]] && MODEL_SM_JSONS+=("${CANDIDATE}")
done

if (( ${#MODEL_SM_JSONS[@]} == 0 )); then
  echo "No result JSONs found in ${MODEL_SM_DIR}; skipping evaluation."
else
  EVAL_LOG="${LOG_DIR}/evaluate__${MODEL}__sum-${SM}.log"
  {
    echo "START evaluation for ${MODEL}__sum-${SM}"
    set -x
    python src/evaluate_result.py --input_files "${MODEL_SM_JSONS[@]}" --output_dir "${MODEL_SM_DIR}"
    { set +x; } 2>/dev/null
    echo "DONE  evaluation for ${MODEL}__sum-${SM}"
  } |& tee "${EVAL_LOG}"
fi

echo "🎯 Completed and evaluated: ${MODEL}"
