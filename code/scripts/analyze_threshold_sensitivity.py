#!/usr/bin/env python
"""Does the strict tier depend on the thresholds it was defined with?

The strict endpoint is a conjunction of conditions with explicit thresholds
(chapter 4 of the protocol), so the first question a reader can ask is whether
the comparison survives a change of those numbers. This script re-runs the frozen
audit over the reported matrix once per perturbation, moving one threshold at a
time in both directions, and reports the endpoint counts per arm.

Only the perturbed threshold changes; the traces, the case plan and every other
threshold stay at the reported value.

Usage:
    python3 scripts/analyze_threshold_sensitivity.py \
        --root outputs/.../corrected_v2_20260920 \
        --out outputs/.../corrected_v2_20260920/threshold_sensitivity_all_20260926
"""

import argparse
import csv
import json
import math
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.audit_validity_endpoint_v3 import run_job  # noqa: E402

AXES = {
    "pass_margin": [(3.0, "looser"), (5.0, "stricter")],
    "hold": [(40, "looser"), (60, "stricter")],
    "in_corridor_min": [(0.60, "looser"), (0.80, "stricter")],
    "corridor_limit": [(0.90, "stricter"), (1.10, "looser")],
    "lateral_step_bound": [(0.07, "stricter"), (0.15, "looser")],
    "heading_cos_min": [(0.75, "looser"), (0.88, "stricter")],
    "approach_distance": [(15.0, "stricter"), (25.0, "looser")],
}
ARMS = ["ours_dnq_dlc", "rule_expert_gate", "dlc_individual_transition",
        "dlc_joint_transition", "dlc_joint_transition_observer"]
ENDPOINTS = ["E_pass", "E_full"]


def variants(base):
    yield "baseline", "baseline", base
    for axis, entries in AXES.items():
        for value, direction in entries:
            cfg = dict(base)
            cfg[axis] = value
            yield f"{axis}_{value}", f"{axis} {value} ({direction})", cfg


def run_variant(job):
    label, description, cfg, plan, root = job
    rows = []
    with ProcessPoolExecutor(max_workers=os.cpu_count()) as pool:
        jobs = [(root, case["out_dir"], algorithm, int(case["num_agents"]), int(case["seed"]),
                 case["experiment_id"], case.get("track_id", ""), cfg)
                for case in plan
                for algorithm in (item.strip() for item in case["algorithms"].split(","))
                if algorithm in ARMS]
        for row, _ in pool.map(run_job, jobs, chunksize=4):
            rows.append(row)
    records = []
    for algorithm in ARMS:
        group = [r for r in rows if r["algorithm"] == algorithm]
        record = {"variant": label, "description": description, "algorithm": algorithm,
                  "cases": len(group),
                  "censored": sum(bool(r.get("post_pass_censored")) for r in group)}
        for endpoint in ENDPOINTS:
            record[endpoint] = sum(bool(r.get(endpoint)) for r in group)
        grass = [r["grass_fraction"] for r in group
                 if isinstance(r.get("grass_fraction"), float) and not math.isnan(r["grass_fraction"])]
        record["grass_fraction"] = round(sum(grass) / len(grass), 4) if grass else ""
        record["in_corridor_man"] = round(sum(r["in_corridor_man"] for r in group
                                              if isinstance(r.get("in_corridor_man"), float)) / len(group), 4)
        records.append(record)
    return records


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--case-plan", default="validity_final_all/case_plan.csv")
    parser.add_argument("--protocol", default="validity_final_all/protocol.json")
    parser.add_argument("--out", required=True)
    parser.add_argument("--variants", default="", help="comma separated variant labels, default all")
    parser.add_argument("--arms", default="",
                        help="comma separated arm names to audit; default is the published set")
    args = parser.parse_args()

    global ARMS
    if args.arms:
        ARMS = [item.strip() for item in args.arms.split(",") if item.strip()]

    root = Path(args.root)
    base = json.loads((root / args.protocol).read_text())["config"]
    plan = list(csv.DictReader(open(root / args.case_plan)))
    wanted = {item for item in args.variants.split(",") if item}
    jobs = [entry for entry in variants(base) if not wanted or entry[0] in wanted
            or entry[0] == "baseline"]
    records = []
    for label, description, cfg in jobs:
        part = run_variant((label, description, cfg, plan, str(root)))
        records.extend(part)
        print(f"{label}: " + ", ".join(
            f"{r['algorithm'].split('_')[0]} E_full {r['E_full']}/{r['cases']}" for r in part), flush=True)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "threshold_sensitivity.csv", "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)

    baseline = {r["algorithm"]: r for r in records if r["variant"] == "baseline"}
    flips = []
    for record in records:
        if record["variant"] == "baseline":
            continue
        if record["E_full"] > baseline[record["algorithm"]]["E_full"]:
            flips.append(record)
    print(f"wrote {out / 'threshold_sensitivity.csv'}")
    print(f"variants {len({r['variant'] for r in records})}, arms {len(ARMS)}")
    if flips:
        print("arms that improve on their baseline:")
        for record in flips:
            print("  ", record["variant"], record["algorithm"],
                  baseline[record["algorithm"]]["E_full"], "->", record["E_full"])


if __name__ == "__main__":
    main()
