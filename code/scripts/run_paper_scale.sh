#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="${1:-${ROOT_DIR}/outputs/torch_dlc_experiment}"
CONDA_ENV="${CONDA_ENV:-vlm_planner}"
SEEDS="${SEEDS:-0,1,2,3,4}"
EPISODES="${EPISODES:-500}"
MAX_STEPS="${MAX_STEPS:-1000}"
TRAIN_STEPS="${TRAIN_STEPS:-200}"
EVAL_AT_STEPS="${EVAL_AT_STEPS:-50,100,150,200}"
EVAL_EPISODES="${EVAL_EPISODES:-100}"
EVAL_MAX_STEPS="${EVAL_MAX_STEPS:-1000}"
BEHAVIOR_POLICY="${BEHAVIOR_POLICY:-track_follow}"
BEHAVIOR_CLONE_WEIGHT="${BEHAVIOR_CLONE_WEIGHT:-0.0}"
SAFETY_WEIGHT="${SAFETY_WEIGHT:-0.0}"
GRASS_PENALTY="${GRASS_PENALTY:-0.0}"
BACKWARD_PENALTY="${BACKWARD_PENALTY:-0.0}"
LATERAL_PENALTY="${LATERAL_PENALTY:-0.0}"
PROGRESS_DELTA_WEIGHT="${PROGRESS_DELTA_WEIGHT:-0.0}"
TILE_PROGRESS_WEIGHT="${TILE_PROGRESS_WEIGHT:-0.0}"
LAP_COMPLETION_BONUS="${LAP_COMPLETION_BONUS:-0.0}"
BATCH_SIZE="${BATCH_SIZE:-50}"
IMAGINATION_HORIZON="${IMAGINATION_HORIZON:-15}"
HIDDEN_DIM="${HIDDEN_DIM:-256}"
ACTOR_EVERY="${ACTOR_EVERY:-1}"
MODEL_LR="${MODEL_LR:-6e-4}"
VALUE_LR="${VALUE_LR:-6e-4}"
ACTOR_LR="${ACTOR_LR:-8e-5}"
CPU_COUNT="$(nproc)"
if command -v nvidia-smi >/dev/null 2>&1; then
  GPU_COUNT="$(nvidia-smi --query-gpu=index --format=csv,noheader | wc -l)"
else
  GPU_COUNT="0"
fi
if [[ "${GPU_COUNT}" -gt 0 ]]; then
  DEFAULT_DEVICES="$(seq 0 "$((GPU_COUNT - 1))" | sed 's/^/cuda:/' | paste -sd, -)"
else
  DEFAULT_DEVICES="auto"
fi
DEVICES="${DEVICES:-${DEFAULT_DEVICES}}"
PARALLEL_SEEDS="${PARALLEL_SEEDS:-${GPU_COUNT}}"
if [[ "${PARALLEL_SEEDS}" -lt 1 ]]; then
  PARALLEL_SEEDS="1"
fi
DEFAULT_COLLECT_WORKERS="$((CPU_COUNT / PARALLEL_SEEDS))"
if [[ "${DEFAULT_COLLECT_WORKERS}" -lt 1 ]]; then
  DEFAULT_COLLECT_WORKERS="1"
fi
COLLECT_WORKERS="${COLLECT_WORKERS:-${DEFAULT_COLLECT_WORKERS}}"
DEFAULT_PARALLEL_EVALS="$((CPU_COUNT / 6))"
if [[ "${DEFAULT_PARALLEL_EVALS}" -lt 1 ]]; then
  DEFAULT_PARALLEL_EVALS="1"
fi
if [[ "${DEFAULT_PARALLEL_EVALS}" -gt 4 ]]; then
  DEFAULT_PARALLEL_EVALS="24"
fi
PARALLEL_EVALS="${PARALLEL_EVALS:-${DEFAULT_PARALLEL_EVALS}}"

mkdir -p "${OUT_DIR}"

conda run -n "${CONDA_ENV}" python -u -m dlc.experiment \
  --seeds "${SEEDS}" \
  --episodes "${EPISODES}" \
  --max-steps "${MAX_STEPS}" \
  --train-steps "${TRAIN_STEPS}" \
  --eval-at-steps "${EVAL_AT_STEPS}" \
  --batch-size "${BATCH_SIZE}" \
  --imagination-horizon "${IMAGINATION_HORIZON}" \
  --hidden-dim "${HIDDEN_DIM}" \
  --collect-workers "${COLLECT_WORKERS}" \
  --behavior-policy "${BEHAVIOR_POLICY}" \
  --behavior-clone-weight "${BEHAVIOR_CLONE_WEIGHT}" \
  --safety-weight "${SAFETY_WEIGHT}" \
  --grass-penalty "${GRASS_PENALTY}" \
  --backward-penalty "${BACKWARD_PENALTY}" \
  --lateral-penalty "${LATERAL_PENALTY}" \
  --progress-delta-weight "${PROGRESS_DELTA_WEIGHT}" \
  --tile-progress-weight "${TILE_PROGRESS_WEIGHT}" \
  --lap-completion-bonus "${LAP_COMPLETION_BONUS}" \
  --actor-every "${ACTOR_EVERY}" \
  --model-lr "${MODEL_LR}" \
  --value-lr "${VALUE_LR}" \
  --actor-lr "${ACTOR_LR}" \
  --eval-episodes "${EVAL_EPISODES}" \
  --eval-max-steps "${EVAL_MAX_STEPS}" \
  --devices "${DEVICES}" \
  --parallel-seeds "${PARALLEL_SEEDS}" \
  --parallel-evals "${PARALLEL_EVALS}" \
  --out-dir "${OUT_DIR}" \
  --resume

conda run -n "${CONDA_ENV}" python -u -m dlc.summarize_results \
  "${OUT_DIR}/aggregate_summary.json" \
  --out-dir "${OUT_DIR}/exported"

conda run -n "${CONDA_ENV}" python -u -m dlc.plot_results \
  "${OUT_DIR}/aggregate_summary.json" \
  --out-dir "${OUT_DIR}/figures"

conda run -n "${CONDA_ENV}" python -u -m dlc.validate_results \
  "${OUT_DIR}/aggregate_summary.json" \
  --win-ratio-threshold 0.5 \
  --out-dir "${OUT_DIR}/validation"

conda run -n "${CONDA_ENV}" python -u -m dlc.audit_experiment \
  "${OUT_DIR}/aggregate_summary.json" \
  --out-dir "${OUT_DIR}/audit"

echo "paper_scale_run: PASS"
