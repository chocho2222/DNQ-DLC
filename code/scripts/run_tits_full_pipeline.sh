#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

PYTHON_BIN="${PYTHON_BIN:-/home/itrc/.conda/envs/vlm_planner/bin/python}"
CONFIG="${CONFIG:-configs/tits_dynamic_graph_experiments.json}"
DEVICES="${DEVICES:-cuda:0,cuda:1,cuda:2,cuda:3}"
JOBS="${JOBS:-8}"
TRAIN_JOBS="${TRAIN_JOBS:-2}"
COLLECTION_WORKERS="${COLLECTION_WORKERS:-8}"
CLEAN_ONLINE="${CLEAN_ONLINE:-1}"
RUN_REPRESENTATIVE_GIFS="${RUN_REPRESENTATIVE_GIFS:-1}"
SKIP_TRAIN="${SKIP_TRAIN:-0}"
MODE="${MODE:-dry-run}"

BC_EPISODES="${BC_EPISODES:-200}"
WORLD_EPISODES="${WORLD_EPISODES:-160}"
TRAIN_MAX_STEPS="${TRAIN_MAX_STEPS:-2200}"
ONLINE_MAX_STEPS="${ONLINE_MAX_STEPS:-2200}"
BOOTSTRAP="${BOOTSTRAP:-5000}"
ALGORITHMS="${ALGORITHMS:-ours_dynamic_graph_dlc_world,ours_no_overtake_aware_planner,quality_proposal_dlc_world_v1,quality_proposal_dlc_world_v2,quality_guided_dlc_world_v3,quality_aux_dlc_world_v4,graph_bc_dynamic,quality_graph_bc_v1,quality_graph_bc_v2,dlc_world_original,dlc_world_balanced,dlc_world_safety,dlc_world_fast,rule_expert_gate,rule_adaptive_gate}"

if [[ "${MODE}" == "dry-run" ]]; then
  if [[ "${SKIP_TRAIN}" == "1" ]]; then
    echo "[dry-run] skip training and reuse existing model artifacts"
  else
    echo "[dry-run] ${PYTHON_BIN} scripts/run_tits_dynamic_graph_suite.py --config ${CONFIG} --mode train --devices ${DEVICES} --jobs ${TRAIN_JOBS} --collection-workers ${COLLECTION_WORKERS} --bc-episodes ${BC_EPISODES} --world-episodes ${WORLD_EPISODES} --max-steps ${TRAIN_MAX_STEPS}"
  fi
  if [[ "${CLEAN_ONLINE}" == "1" ]]; then
    echo "[dry-run] rm -rf outputs/tits_dynamic_graph/online_evaluation_matrix outputs/tits_dynamic_graph/online_evaluation_matrix_summary outputs/tits_dynamic_graph/representative_gifs"
  fi
  echo "[dry-run] ${PYTHON_BIN} scripts/run_tits_dynamic_graph_online_suite.py --config ${CONFIG} --mode run --algorithms ${ALGORITHMS} --devices ${DEVICES} --jobs ${JOBS} --max-steps ${ONLINE_MAX_STEPS} --finish-mode any --observation-type telemetry_dynamic --traffic-profile slow_traffic --no-gif"
  if [[ "${RUN_REPRESENTATIVE_GIFS}" == "1" ]]; then
    echo "[dry-run] scripts/run_tits_representative_gifs.sh"
  fi
  echo "[dry-run] ${PYTHON_BIN} scripts/summarize_tits_dynamic_graph_online.py --bootstrap ${BOOTSTRAP}"
  echo "[dry-run] ${PYTHON_BIN} scripts/audit_tits_dynamic_graph_readiness.py"
  echo "[dry-run] ${PYTHON_BIN} scripts/export_tits_dynamic_graph_artifact_manifest.py"
  exit 0
fi

if [[ "${MODE}" != "run" ]]; then
  echo "MODE must be either dry-run or run, got: ${MODE}" >&2
  exit 2
fi

if [[ "${SKIP_TRAIN}" != "1" ]]; then
  "${PYTHON_BIN}" scripts/run_tits_dynamic_graph_suite.py \
    --config "${CONFIG}" \
    --mode train \
    --devices "${DEVICES}" \
    --jobs "${TRAIN_JOBS}" \
    --collection-workers "${COLLECTION_WORKERS}" \
    --bc-episodes "${BC_EPISODES}" \
    --world-episodes "${WORLD_EPISODES}" \
    --max-steps "${TRAIN_MAX_STEPS}"
fi

if [[ "${CLEAN_ONLINE}" == "1" ]]; then
  rm -rf \
    outputs/tits_dynamic_graph/online_evaluation_matrix \
    outputs/tits_dynamic_graph/online_evaluation_matrix_summary \
    outputs/tits_dynamic_graph/representative_gifs
fi

"${PYTHON_BIN}" scripts/run_tits_dynamic_graph_online_suite.py \
  --config "${CONFIG}" \
  --mode run \
  --algorithms "${ALGORITHMS}" \
  --devices "${DEVICES}" \
  --jobs "${JOBS}" \
  --max-steps "${ONLINE_MAX_STEPS}" \
  --finish-mode any \
  --observation-type telemetry_dynamic \
  --traffic-profile slow_traffic \
  --no-gif

if [[ "${RUN_REPRESENTATIVE_GIFS}" == "1" ]]; then
  PYTHON_BIN="${PYTHON_BIN}" \
  CONFIG="${CONFIG}" \
  DEVICES="${DEVICES}" \
  MAX_STEPS="${ONLINE_MAX_STEPS}" \
  scripts/run_tits_representative_gifs.sh
fi

"${PYTHON_BIN}" scripts/summarize_tits_dynamic_graph_online.py \
  --input-dir outputs/tits_dynamic_graph/online_evaluation_matrix \
  --out-dir outputs/tits_dynamic_graph/online_evaluation_matrix_summary \
  --bootstrap "${BOOTSTRAP}"

"${PYTHON_BIN}" scripts/audit_tits_dynamic_graph_readiness.py \
  --config "${CONFIG}" \
  --online-dir outputs/tits_dynamic_graph/online_evaluation_matrix \
  --summary-dir outputs/tits_dynamic_graph/online_evaluation_matrix_summary \
  --out outputs/tits_dynamic_graph/tits_readiness_audit.json

"${PYTHON_BIN}" scripts/export_tits_dynamic_graph_artifact_manifest.py \
  --root . \
  --out-dir outputs/tits_dynamic_graph/artifact_manifest

echo "tits_full_pipeline: completed"
