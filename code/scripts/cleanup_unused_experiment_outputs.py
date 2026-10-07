#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import json
import shutil
from datetime import datetime
from pathlib import Path


DEFAULT_OUT_DIR = "outputs/tits_dynamic_graph_cleanup"

KEEP_PREFIXES = [
    "outputs/tits_dynamic_graph/models",
    "outputs/tits_dynamic_graph/v6_confirmatory_matrix",
    "outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary",
    "outputs/tits_dynamic_graph/v6_confirmatory_preflight",
    "outputs/tits_dynamic_graph/publication_gifs",
    "outputs/tits_dynamic_graph/tits_typical_first_person_case_pack",
    "outputs/tits_dynamic_graph/tits_six_experiment_protocol_pack",
    "outputs/tits_dynamic_graph/tits_overtake_timing_analysis_pack",
    "outputs/tits_dynamic_graph/tits_overtake_casewise_diagnostics_pack",
    "outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack",
    "outputs/tits_dynamic_graph/reviewer_replication_packet",
    "outputs/tits_dynamic_graph/artifact_manifest",
    "outputs/tits_dynamic_graph/public_release_plan",
    "outputs/tits_dynamic_graph/final_readiness_dashboard",
    "outputs/tits_dynamic_graph/tits_status_snapshot",
    "outputs/tits_dynamic_graph/tits_final_freeze_consistency_audit",
    "outputs/tits_dynamic_graph/tits_refresh_coverage_audit",
    "outputs/tits_dynamic_graph/tits_cross_reference_audit",
    "outputs/paper_multicar_overtake_20260618/models/graph_risk_world_model",
    "outputs/paper_multicar_overtake_20260618/models/graph_risk_world_model_variants",
]

UNUSED_CANDIDATES = [
    "outputs/dynamic_smoke_n4",
    "outputs/dynamic_smoke_n5",
    "outputs/dynamic_smoke_n6",
    "outputs/tits_dynamic_graph/config_driven_eval_smoke",
    "outputs/tits_dynamic_graph/elegant_dataset_smoke",
    "outputs/tits_dynamic_graph/elegant_dataset_v2_smoke",
    "outputs/tits_dynamic_graph/elegant_graph_bc_smoke",
    "outputs/tits_dynamic_graph/online_evaluation",
    "outputs/tits_dynamic_graph/online_evaluation_matrix",
    "outputs/tits_dynamic_graph/online_evaluation_matrix_quality_backfilled",
    "outputs/tits_dynamic_graph/online_evaluation_matrix_quality_summary",
    "outputs/tits_dynamic_graph/online_evaluation_matrix_summary",
    "outputs/tits_dynamic_graph/online_planner_patch_smoke",
    "outputs/tits_dynamic_graph/optimization_checks",
    "outputs/tits_dynamic_graph/overtake_planner_ablation_smoke",
    "outputs/tits_dynamic_graph/quality_aux_dlc_v4_matrix",
    "outputs/tits_dynamic_graph/quality_aux_dlc_v4_matrix_summary",
    "outputs/tits_dynamic_graph/quality_aux_dlc_v5_sweep_matrix",
    "outputs/tits_dynamic_graph/quality_aux_dlc_v5_sweep_matrix_summary",
    "outputs/tits_dynamic_graph/quality_graph_bc_v1_eval",
    "outputs/tits_dynamic_graph/quality_guided_dlc_v3_matrix",
    "outputs/tits_dynamic_graph/quality_guided_dlc_v3_matrix_summary",
    "outputs/tits_dynamic_graph/quality_guided_dlc_v3_representative_gifs",
    "outputs/tits_dynamic_graph/quality_metric_checks",
    "outputs/tits_dynamic_graph/quality_metric_checks_backfilled",
    "outputs/tits_dynamic_graph/quality_proposal_dlc_v1_eval",
    "outputs/tits_dynamic_graph/quality_proposal_dlc_v1_matrix",
    "outputs/tits_dynamic_graph/quality_proposal_dlc_v1_matrix_summary",
    "outputs/tits_dynamic_graph/quality_proposal_dlc_v2_matrix",
    "outputs/tits_dynamic_graph/quality_proposal_dlc_v2_matrix_summary",
    "outputs/tits_dynamic_graph/representative_gifs",
    "outputs/tits_dynamic_graph/smoke",
    "outputs/tits_dynamic_graph/smoke_eval",
    "outputs/tits_dynamic_graph/smoke_train",
    "outputs/tits_dynamic_graph/v6_planner_budget_pareto_matrix",
    "outputs/tits_dynamic_graph/v6_planner_budget_pareto_matrix_summary",
    "outputs/tits_dynamic_graph/v6_runtime_dynamic_neighborhood_matrix",
    "outputs/tits_dynamic_graph/v6_runtime_dynamic_neighborhood_matrix_summary",
    "outputs/tits_dynamic_graph/v6_runtime_dynamic_neighborhood_representative_gifs",
    "outputs/tits_dynamic_graph/v7_elegance_barrier_pilot_matrix",
    "outputs/tits_dynamic_graph/v7_elegance_barrier_pilot_matrix_summary",
    "outputs/tits_dynamic_graph/v7_elegance_barrier_pilot_matrix_run_results_ledger.csv",
    "outputs/tits_dynamic_graph/v7_elegance_barrier_pilot_matrix_run_results_20260625_101312.csv",
    "outputs/tits_dynamic_graph/v7_elegance_barrier_pilot_matrix_run_summary.json",
    "outputs/tits_dynamic_graph/v7_elegance_barrier_pilot_matrix_run_summary_20260625_101312.json",
    "outputs/tits_dynamic_graph/v7_elegance_barrier_smoke",
    "outputs/tits_dynamic_graph/tits_v7_paired_pilot_analysis_pack",
    "outputs/tits_dynamic_graph_expanded/paper_dlc_baselines_smoke",
    "outputs/tits_dynamic_graph_expanded/paper_dlc_baselines_training_smoke",
    "outputs/tits_dynamic_graph_expanded/rl_baselines_smoke",
    "outputs/paper_multicar_overtake_20260618/ablations",
    "outputs/paper_multicar_overtake_20260618/baselines",
    "outputs/paper_multicar_overtake_20260618/configs",
    "outputs/paper_multicar_overtake_20260618/evaluations",
    "outputs/paper_multicar_overtake_20260618/figures",
    "outputs/paper_multicar_overtake_20260618/logs",
    "outputs/paper_multicar_overtake_20260618/manuscript",
    "outputs/paper_multicar_overtake_20260618/materials",
    "outputs/paper_multicar_overtake_20260618/sweeps",
    "outputs/paper_multicar_overtake_20260618/tables",
    "outputs/tits_dynamic_graph/overtake_planner_ablation_smoke",
]


def rel(path):
    return str(Path(path).as_posix()).rstrip("/")


def starts_with_any(path, prefixes):
    path = rel(path)
    return any(path == rel(prefix) or path.startswith(rel(prefix) + "/") for prefix in prefixes)


def size_bytes(path):
    path = Path(path)
    if not path.exists():
        return 0
    if path.is_file():
        return path.stat().st_size
    total = 0
    for item in path.rglob("*"):
        if item.is_file():
            try:
                total += item.stat().st_size
            except OSError:
                pass
    return total


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["path", "exists", "size_bytes", "size_mb", "decision", "reason"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return str(path)


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return str(path)


def build_plan(root):
    rows = []
    seen = set()
    for item in UNUSED_CANDIDATES:
        item = rel(item)
        if item in seen:
            continue
        seen.add(item)
        path = root / item
        protected = starts_with_any(item, KEEP_PREFIXES)
        exists = path.exists()
        size = size_bytes(path) if exists else 0
        if protected:
            decision = "keep_protected"
            reason = "Matches keep-prefix list for formal evidence, models, maps, or current requested visual evidence."
        elif exists:
            decision = "delete_candidate"
            reason = "Historical smoke, optimization, superseded candidate matrix, or exploratory output not part of the new six-experiment protocol."
        else:
            decision = "missing"
            reason = "Candidate path is already absent."
        rows.append(
            {
                "path": item,
                "exists": exists,
                "size_bytes": size,
                "size_mb": round(size / 1024 / 1024, 3),
                "decision": decision,
                "reason": reason,
            }
        )
    return rows


def execute_delete(root, rows):
    deleted = []
    for row in rows:
        if row["decision"] != "delete_candidate" or not row["exists"]:
            continue
        path = root / row["path"]
        if path.exists():
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
        deleted.append(row["path"])
    return deleted


def main():
    parser = argparse.ArgumentParser(description="Remove unused historical experiment outputs with an auditable manifest.")
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR)
    parser.add_argument("--execute", action="store_true", help="Actually delete delete_candidate paths. Without this flag, only writes a dry-run plan.")
    args = parser.parse_args()

    root = Path.cwd()
    out_dir = root / args.out_dir
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    rows = build_plan(root)
    deleted = execute_delete(root, rows) if args.execute else []
    total_candidate_bytes = sum(int(row["size_bytes"]) for row in rows if row["decision"] == "delete_candidate")
    manifest = {
        "status": "executed" if args.execute else "dry_run",
        "run_id": run_id,
        "delete_candidate_count": sum(1 for row in rows if row["decision"] == "delete_candidate" and row["exists"]),
        "protected_count": sum(1 for row in rows if row["decision"] == "keep_protected"),
        "deleted_count": len(deleted),
        "candidate_size_bytes": total_candidate_bytes,
        "candidate_size_gb": round(total_candidate_bytes / 1024 / 1024 / 1024, 3),
        "deleted_paths": deleted,
        "keep_prefixes": KEEP_PREFIXES,
        "note": "Formal v6 confirmatory matrix, model weights, current typical first-person case pack, publication GIFs, and release/readiness evidence are protected.",
    }
    paths = {
        "plan_csv": write_csv(out_dir / f"cleanup_plan_{run_id}.csv", rows),
        "manifest_json": write_json(out_dir / f"cleanup_manifest_{run_id}.json", manifest),
        "latest_plan_csv": write_csv(out_dir / "cleanup_plan_latest.csv", rows),
        "latest_manifest_json": write_json(out_dir / "cleanup_manifest_latest.json", manifest),
    }
    print(json.dumps({"manifest": manifest, "paths": paths}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
