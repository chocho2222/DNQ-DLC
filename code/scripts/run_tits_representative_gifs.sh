#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

PYTHON_BIN="${PYTHON_BIN:-/home/itrc/.conda/envs/vlm_planner/bin/python}"
CONFIG="${CONFIG:-configs/tits_dynamic_graph_experiments.json}"
DEVICES="${DEVICES:-cuda:0,cuda:1,cuda:2,cuda:3}"
MAX_STEPS="${MAX_STEPS:-2200}"
FRAME_EVERY="${FRAME_EVERY:-8}"
FPS="${FPS:-12}"
ALGORITHMS="${GIF_ALGORITHMS:-ours_dynamic_graph_dlc_world,ours_no_overtake_aware_planner,dlc_world_original,rule_expert_gate}"
OUT_ROOT="${OUT_ROOT:-outputs/tits_dynamic_graph/representative_gifs}"

IFS=',' read -r -a DEVICE_ARRAY <<< "${DEVICES}"

run_case() {
  local case_name="$1"
  local num_agents="$2"
  local seed="$3"
  local device_index="$4"
  local track_path="${5:-}"
  local device="${DEVICE_ARRAY[$((device_index % ${#DEVICE_ARRAY[@]}))]}"
  local out_dir="${OUT_ROOT}/${case_name}"
  local cmd=(
    "${PYTHON_BIN}" scripts/run_tits_dynamic_graph_evaluation.py
    --config "${CONFIG}"
    --out-dir "${out_dir}"
    --algorithms "${ALGORITHMS}"
    --num-agents "${num_agents}"
    --seed "${seed}"
    --max-steps "${MAX_STEPS}"
    --finish-mode any
    --observation-type telemetry_dynamic
    --max-neighbors 3
    --device "${device}"
    --traffic-profile slow_traffic
    --frame-every "${FRAME_EVERY}"
    --fps "${FPS}"
    --first-person-gif
  )
  if [[ -n "${track_path}" ]]; then
    cmd+=(--track-path "${track_path}")
  fi
  echo "running representative gif: ${case_name} on ${device}"
  "${cmd[@]}"
}

run_case "procedural_n4_seed3" 4 3 0
run_case "procedural_n6_seed17" 6 17 1
run_case "monza_n6_seed61" 6 61 2 "tracks/monza_scaled.npz"

echo "representative gifs completed: ${OUT_ROOT}"
