#!/usr/bin/env python
"""Does the admitted-set size have to grow with the field?

The submitted policy reads three opponent slots, and the recorded budget probe
can only shrink that number because the transition model has a fixed input
width. The five-slot checkpoint (``wm_k15_v5att``) lifts that constraint, so the
same scene can be run at a runtime capacity of three and of five neighbours.
Every planner weight, the shield, the quality terms and the case plan are the
ones of the reported evaluation; only the checkpoint, the slot budget and the
ranking rule change.

The script re-audits each arm with the frozen endpoint protocol and writes:

    case_level.csv   one row per case and arm
    aggregate.csv    one row per arm

Usage:
    python3 scripts/analyze_capacity_probe.py --root <matrix root> \
        --case-plan <plan.csv> --out <dir>
"""
import argparse
import csv
import json
import math
import os
import sys
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.audit_validity_endpoint_v3 import run_job  # noqa: E402

# label -> (root directory under --root, algorithm name)
ARMS = {
    "released_k3": ("main_final_20260922", "ours_dnq_dlc"),
    "five_near_k3": ("capacity_probe_20260923", "cap_five_near_k3"),
    "five_near_k5": ("capacity_probe_20260923", "cap_five_near_k5"),
    "five_inter_k3": ("capacity_probe_20260923", "cap_five_inter_k3"),
    "five_inter_k5": ("capacity_probe_20260923", "cap_five_inter_k5"),
}
ENDPOINTS = ["P", "L", "C", "T_v3", "S_v3", "E_pass", "E_valid", "E_full", "E_race"]


def admitted_sizes(path):
    if not path.exists():
        return []
    with open(path) as handle:
        trace = json.load(handle)
    sizes = []
    for row in trace:
        debug = row.get("target_policy_debug") or {}
        ids = debug.get("selected_neighbor_ids")
        if ids is not None:
            sizes.append(len(ids))
    return sizes


def analyse_case(job):
    root, case, algorithm, num_agents, seed, tag, config = job
    trace_path = Path(root) / case / "traces" / f"{algorithm}_n{num_agents}_seed{seed}.trace.json"
    row = {}
    if trace_path.exists():
        row, _ = run_job((root, case, algorithm, num_agents, seed, tag, "procedural", config))
    sizes = admitted_sizes(trace_path)
    record = {"case": case, "algorithm": algorithm, "num_agents": num_agents, "seed": seed}
    for key in ENDPOINTS:
        record[key] = bool(row.get(key)) if row else False
    for key in ("grass_fraction", "rank_gain", "time_to_pass_steps", "in_corridor_fraction",
                "mean_abs_lat"):
        value = row.get(key)
        record[key] = "" if value is None else value
    record["steps_recorded"] = len(sizes)
    record["admitted_mean"] = (sum(sizes) / len(sizes)) if sizes else ""
    record["admitted_max"] = max(sizes) if sizes else ""
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--case-plan", required=True, help="CSV with columns tag,num_agents,seed")
    parser.add_argument("--out", required=True)
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--protocol", default="validity_final_all/protocol.json")
    parser.add_argument("--arm", action="append", default=[],
                        help="LABEL:ROOTDIR:ALGORITHM, repeatable; overrides the built-in map")
    args = parser.parse_args()

    root = Path(args.root)
    config = json.load(open(root / args.protocol))["config"]
    arms_map = dict(ARMS)
    if args.arm:
        arms_map = {}
        for spec in args.arm:
            label, variant, algorithm = spec.split(":")
            arms_map[label] = (variant, algorithm)
    plan = list(csv.DictReader(open(args.case_plan)))
    jobs, labels = [], []
    for label, (variant, algorithm) in arms_map.items():
        for item in plan:
            tag = item.get("tag") or item["experiment_id"]
            num_agents = int(item["num_agents"])
            seed = int(item["seed"])
            case = f"{tag}_n{num_agents}_seed{seed}"
            jobs.append((str(root / variant), case, algorithm, num_agents, seed, tag, config))
            labels.append(label)
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(analyse_case, jobs))
    for record, label in zip(results, labels):
        record["arm"] = label
    missing = [r["case"] for r in results if not r["steps_recorded"]]
    if missing:
        print(f"WARNING: {len(missing)} runs have no recorded trace, starting with {missing[:3]}")

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    fields = ["arm"] + [k for k in results[0] if k != "arm"]
    with open(out_dir / "case_level.csv", "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(results)

    aggregate = []
    for label in arms_map:
        rows = [r for r in results if r["arm"] == label]
        grass = [r["grass_fraction"] for r in rows
                 if isinstance(r["grass_fraction"], float) and not math.isnan(r["grass_fraction"])]
        rank = [r["rank_gain"] for r in rows if isinstance(r["rank_gain"], (int, float))]
        admitted = [r["admitted_mean"] for r in rows if isinstance(r["admitted_mean"], float)]
        record = {"arm": label, "cases": len(rows)}
        for key in ("P", "E_pass", "E_valid", "E_full", "E_race"):
            record[key] = sum(1 for r in rows if r[key])
        record["grass_cases"] = len(grass)
        record["grass_mean"] = (sum(grass) / len(grass)) if grass else ""
        record["rank_gain_sum"] = sum(rank) if rank else ""
        record["admitted_mean"] = (sum(admitted) / len(admitted)) if admitted else ""
        for size in (6, 8, 10):
            sub = [r for r in rows if r["num_agents"] == size]
            record[f"P_n{size}"] = sum(1 for r in sub if r["P"])
            record[f"E_full_n{size}"] = sum(1 for r in sub if r["E_full"])
            record[f"cases_n{size}"] = len(sub)
        aggregate.append(record)
    with open(out_dir / "aggregate.csv", "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(aggregate[0].keys()))
        writer.writeheader()
        writer.writerows(aggregate)

    for record in aggregate:
        print(record)
    print(f"wrote {out_dir / 'case_level.csv'} and {out_dir / 'aggregate.csv'}")


if __name__ == "__main__":
    main()
