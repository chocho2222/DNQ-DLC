#!/bin/bash
# Recompute the content digest of the released snapshot tits-2026-09-29 from a
# copy of this repository. The roots below are the repository locations of the
# roots listed in release_manifest.json; build_release_manifest.py names each
# entry by the basename of the root it is given, so the recomputed digest is
# independent of where the repository is checked out.
set -eu
cd "$(dirname "$0")/.."
PY=${PYTHON:-python3}
"$PY" code/scripts/build_release_manifest.py \
 --root code/scripts --root configs --root code/dlc --root code/gym_multi_car_racing \
 --root source_data/budget_probe_all_20260923 --root source_data/containment_all_20260923 \
 --root source_data/containment_ours_ensemble_20260928 --root source_data/containment_ours_seedspread_20260928 \
 --root source_data/containment_shieldoff_20260926 --root source_data/controller_signals_final_20260922 \
 --root source_data/controller_signals_fused_20260928 \
 --root source_data/corrected_v2_20260920/selector_isolation_dataset_check.json \
 --root source_data/manoeuvre_events_20260929 --root source_data/neighborhood_events_all_20260923 \
 --root source_data/neighborhood_events_fused_20260928 --root source_data/ours_wm_ensemble_eval_20260928 \
 --root source_data/ours_wm_seedspread_eval_20260928 --root source_data/qualitative_snapshot_fix_20260929 \
 --root checkpoints/quality_actor_k15/graph_bc.graph.pt \
 --root checkpoints/rl_baselines_strict_20260926 --root source_data/rl_baselines_strict_eval_20260927 \
 --root source_data/shieldoff_final_20260926/case_plan.csv --root source_data/audit \
 --root source_data/threshold_sensitivity_all_20260926 \
 --root checkpoints/wm_k15_fixed3/graph_risk_dlc_world.graphworld.pt \
 --root checkpoints/wm_k15_nearest3/graph_risk_dlc_world.graphworld.pt \
 --root checkpoints/wm_k15_sb_all_v4matt/graph_risk_dlc_world.graphworld.pt \
 --root checkpoints/wm_k15_sb_all_v4matt_seed21/graph_risk_dlc_world.graphworld.pt \
 --root checkpoints/wm_k15_sb_all_v4matt_seed47/graph_risk_dlc_world.graphworld.pt \
 --root checkpoints/wm_k15_sb_all_v4matt_seed71/graph_risk_dlc_world.graphworld.pt \
 --root checkpoints/wm_k15_sb_all_v4matt_seed99/graph_risk_dlc_world.graphworld.pt \
 --root source_data/validity_alongside_defer_validation_20260929 \
 --root source_data/validity_capacity_probe_20260923 --root source_data/validity_final_all \
 --root source_data/validity_hold100_20260926 --root source_data/validity_i5_capacity_probe_20260925 \
 --root source_data/validity_ours_corridor_return_fix_20260929 \
 --root source_data/validity_ours_ensemble_20260928 --root source_data/validity_ours_seedspread_20260928 \
 --root source_data/validity_ours_shield_off_fix_20260929 \
 --root source_data/validity_rank_channel_probe_20260923 --root source_data/validity_rl_strict_20260927 \
 --root source_data/validity_selector_isolation_fix_20260929 --root source_data/vehicle_states_final_20260922 \
 --root source_data/vehicle_states_fused_20260928 --root source_data/wm_holdout_validation_20260928 \
 --tag tits-2026-09-29 --out /tmp/recomputed_release_manifest.json
