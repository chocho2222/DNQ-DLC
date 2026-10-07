#!/usr/bin/env python
"""Build a reproducible paper-data snapshot from completed experiment artifacts."""

import csv
import hashlib
import json
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/tits_dynamic_graph_expanded/current_paper_data_20260916"
MATRIX = ROOT / "outputs/tits_dynamic_graph_expanded/e1_200_budget_matched"
PLAN = MATRIX / "tables/expanded_benchmark_case_plan.pre_resume_20260915.csv"
E6_ROOT = ROOT / "outputs/tits_dynamic_graph_expanded/e6_ablation_formal_20260916"


def read_csv(path):
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def rel(path):
    return str(path.relative_to(ROOT))


def copy_sources():
    sources = [
        MATRIX / "completeness_audit_final_20260916/manifest.json",
        MATRIX / "completeness_audit_final_20260916/experiment_level.csv",
        MATRIX / "strict_endpoint_audit_E1_final_20260916/aggregate.csv",
        MATRIX / "strict_endpoint_audit_E1_final_20260916/episode_level.csv",
        MATRIX / "strict_endpoint_audit_E1_final_20260916/manifest.json",
        MATRIX / "strict_endpoint_audit_E2_final_20260916/aggregate.csv",
        MATRIX / "strict_endpoint_audit_E2_final_20260916/episode_level.csv",
        MATRIX / "strict_endpoint_audit_E2_final_20260916/manifest.json",
        MATRIX / "strict_endpoint_audit_E3_final_20260916/aggregate.csv",
        MATRIX / "strict_endpoint_audit_E3_final_20260916/episode_level.csv",
        MATRIX / "strict_endpoint_audit_E3_final_20260916/manifest.json",
        ROOT / "outputs/tits_dynamic_graph_expanded/selector_only_strict_20260915/strict_endpoint_audit_final_20260916/aggregate.csv",
        ROOT / "outputs/tits_dynamic_graph_expanded/selector_only_strict_20260915/strict_endpoint_audit_final_20260916/episode_level.csv",
        ROOT / "outputs/tits_dynamic_graph_expanded/selector_only_strict_20260915/strict_endpoint_audit_final_20260916/manifest.json",
        ROOT / "outputs/tits_dynamic_graph_expanded/handcrafted_candidates_strict_20260915/strict_endpoint_audit_final_20260915/aggregate.csv",
        ROOT / "outputs/tits_dynamic_graph_expanded/handcrafted_candidates_strict_20260915/strict_endpoint_audit_final_20260915/episode_level.csv",
        ROOT / "outputs/tits_dynamic_graph_expanded/handcrafted_candidates_strict_20260915/strict_endpoint_audit_final_20260915/manifest.json",
        ROOT / "outputs/tits_dynamic_graph_expanded/robustness_strict_20260915/strict_endpoint_audit_final_20260916/aggregate.csv",
        ROOT / "outputs/tits_dynamic_graph_expanded/robustness_strict_20260915/strict_endpoint_audit_final_20260916/episode_level.csv",
        ROOT / "outputs/tits_dynamic_graph_expanded/robustness_strict_20260915/strict_endpoint_audit_final_20260916/manifest.json",
        ROOT / "outputs/tits_dynamic_graph_expanded/world_model_physical_oracle_strict_20260915/aggregate/candidate_outcomes.csv",
        ROOT / "outputs/tits_dynamic_graph_expanded/world_model_physical_oracle_strict_20260915/aggregate/case_metrics.csv",
        ROOT / "outputs/tits_dynamic_graph_expanded/world_model_physical_oracle_strict_20260915/aggregate/decision_metrics.csv",
        ROOT / "outputs/tits_dynamic_graph_expanded/world_model_physical_oracle_strict_20260915/aggregate/report.json",
        E6_ROOT / "completeness_audit_final_20260917/manifest.json",
        E6_ROOT / "completeness_audit_final_20260917/experiment_level.csv",
        E6_ROOT / "completeness_audit_final_20260917/case_level.csv",
        E6_ROOT / "strict_endpoint_audit_final_20260917/aggregate.csv",
        E6_ROOT / "strict_endpoint_audit_final_20260917/episode_level.csv",
        E6_ROOT / "strict_endpoint_audit_final_20260917/manifest.json",
    ]
    copied = []
    for source in sources:
        if not source.exists():
            continue
        destination = OUT / "source" / rel(source)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        copied.append(destination)
    return copied


def collect_summary_metrics():
    plans = [
        ("E1_basic_effectiveness", PLAN),
        ("E2_environment_generalization", PLAN),
        ("E3_scale_extension", PLAN),
        ("E6_ablation", E6_ROOT / "tables/expanded_benchmark_case_plan.csv"),
    ]
    rows = []
    for expected_experiment, plan_path in plans:
      if not plan_path.exists():
        continue
      for case in read_csv(plan_path):
        experiment = case["experiment_id"]
        if experiment != expected_experiment:
            continue
        case_dir = ROOT / case["out_dir"]
        for summary_path in sorted((case_dir / "summaries").glob("*.summary.json")):
            try:
                item = json.loads(summary_path.read_text(encoding="utf-8"))
            except Exception:
                continue
            rows.append({
                "experiment_id": experiment,
                "case_index": case["case_index"],
                "track_id": case["track_id"],
                "algorithm": item.get("algorithm"),
                "seed": item.get("seed"),
                "num_agents": item.get("num_agents"),
                "steps_run": item.get("steps_run"),
                "target_progress": item.get("target_progress"),
                "rank_gain": item.get("rank_gain"),
                "target_final_rank": item.get("target_final_rank"),
                "target_completed_lap": item.get("target_completed_lap"),
                "overtake_success": item.get("overtake_success"),
                "overtake_count": item.get("overtake_count"),
                "target_grass_rate": item.get("target_grass_rate"),
                "target_backward_rate": item.get("target_backward_rate"),
                "target_mean_abs_lateral": item.get("target_mean_abs_lateral"),
                "target_heading_error_mean_rad": item.get("target_heading_error_mean_rad"),
                "target_mean_speed": item.get("target_mean_speed"),
                "collision_or_contact_proxy": item.get("collision_or_contact_proxy"),
                "min_pair_distance": item.get("min_pair_distance"),
                "compute_latency_ms": item.get("compute_latency_ms"),
                "compute_latency_p95_ms": item.get("compute_latency_p95_ms"),
                "summary_path": rel(summary_path),
            })
    return rows


def e6_status():
    root = E6_ROOT
    plan = read_csv(root / "tables/expanded_benchmark_case_plan.csv")
    complete_cases = 0
    summary_count = 0
    rows = []
    for case in plan:
        case_dir = ROOT / case["out_dir"]
        count = len(list((case_dir / "summaries").glob("*.summary.json")))
        summary_count += count
        expected = len([x for x in case["algorithms"].split(",") if x.strip()])
        complete_cases += int(count == expected)
        rows.append({"case_index": case["case_index"], "track_id": case["track_id"],
                     "num_agents": case["num_agents"], "seed": case["seed"],
                     "summary_count": count, "expected_summary_count": expected,
                     "complete": count == expected})
    expected_runs = sum(int(x["expected_summary_count"]) for x in rows)
    complete = complete_cases == len(plan) and summary_count == expected_runs
    return {"status": "complete" if complete else "incomplete", "planned_cases": len(plan),
            "complete_cases": complete_cases, "summary_count": summary_count,
            "expected_summary_count": expected_runs,
            "case_rows": rows}


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    copied = copy_sources()
    summary_rows = collect_summary_metrics()
    write_csv(OUT / "standard_summary_metrics.csv", summary_rows)

    strict_rows = []
    strict_sources = {
        "E1": MATRIX / "strict_endpoint_audit_E1_final_20260916/aggregate.csv",
        "E2": MATRIX / "strict_endpoint_audit_E2_final_20260916/aggregate.csv",
        "E3": MATRIX / "strict_endpoint_audit_E3_final_20260916/aggregate.csv",
        "E6": E6_ROOT / "strict_endpoint_audit_final_20260917/aggregate.csv",
        "selector": ROOT / "outputs/tits_dynamic_graph_expanded/selector_only_strict_20260915/strict_endpoint_audit_final_20260916/aggregate.csv",
        "handcrafted": ROOT / "outputs/tits_dynamic_graph_expanded/handcrafted_candidates_strict_20260915/strict_endpoint_audit_final_20260915/aggregate.csv",
        "robustness": ROOT / "outputs/tits_dynamic_graph_expanded/robustness_strict_20260915/strict_endpoint_audit_final_20260916/aggregate.csv",
    }
    for label, source in strict_sources.items():
        if source.exists():
            for row in read_csv(source):
                row["dataset"] = label
                strict_rows.append(row)
    write_csv(OUT / "strict_endpoint_aggregate.csv", strict_rows)

    status = {
        "snapshot_status": "current_completed_data_only",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "completed_experiments": ["E1_basic_effectiveness", "E2_environment_generalization", "E3_scale_extension", "E6_ablation"],
        "excluded_from_results": [],
        "e6_status": e6_status(),
        "strict_endpoint_definition": {
            "physical_pass": "relative progress crosses the pass margin",
            "sustained_lead": "lead remains above the pass margin over the hold window",
            "post_pass_stable": "post-pass speed, lateral, heading, and backward-motion constraints hold",
            "strict_completion": "contact-free physical pass plus sustained lead, on-track, and post-pass stability",
        },
        "source_count": len(copied),
        "summary_metric_rows": len(summary_rows),
        "strict_metric_rows": len(strict_rows),
    }
    (OUT / "status.json").write_text(json.dumps(status, indent=2), encoding="utf-8")

    files = []
    for path in sorted(OUT.rglob("*")):
        if path.is_file() and path.name != "manifest.json":
            files.append({"path": str(path.relative_to(OUT)), "bytes": path.stat().st_size, "sha256": sha256(path)})
    (OUT / "manifest.json").write_text(json.dumps({"root": str(OUT), "files": files}, indent=2), encoding="utf-8")
    print(json.dumps({"out": str(OUT), "summary_metric_rows": len(summary_rows),
                      "strict_metric_rows": len(strict_rows), "source_count": len(copied),
                      "e6": status["e6_status"]}, indent=2))


if __name__ == "__main__":
    main()
