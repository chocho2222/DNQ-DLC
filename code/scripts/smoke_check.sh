#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="${1:-/tmp/torch_dlc_smoke_check}"
CONDA_ENV="${CONDA_ENV:-vlm_planner}"

rm -rf "${OUT_DIR}"
mkdir -p "${OUT_DIR}"

conda run -n "${CONDA_ENV}" python "${ROOT_DIR}/reproduce_telemetry_rollout.py" --steps 5 --seed 0 --out-dir "${OUT_DIR}/telemetry_rollout"
conda run -n "${CONDA_ENV}" python -m dlc.experiment --seeds 0 --episodes 1 --max-steps 8 --train-steps 2 --eval-at-steps 1 --batch-size 4 --imagination-horizon 2 --hidden-dim 32 --eval-episodes 1 --eval-max-steps 5 --out-dir "${OUT_DIR}/experiment"
conda run -n "${CONDA_ENV}" python -m dlc.summarize_results "${OUT_DIR}/experiment/aggregate_summary.json" --out-dir "${OUT_DIR}/experiment/exported"
conda run -n "${CONDA_ENV}" python -m dlc.plot_results "${OUT_DIR}/experiment/aggregate_summary.json" --out-dir "${OUT_DIR}/experiment/figures"
conda run -n "${CONDA_ENV}" python -m dlc.validate_results "${OUT_DIR}/experiment/aggregate_summary.json" --win-ratio-threshold 0.5 --out-dir "${OUT_DIR}/experiment/validation"
conda run -n "${CONDA_ENV}" python -m dlc.audit_experiment "${OUT_DIR}/experiment/aggregate_summary.json" --out-dir "${OUT_DIR}/experiment/audit"

echo "smoke_check: PASS"
