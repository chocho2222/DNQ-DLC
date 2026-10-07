#!/usr/bin/env python
"""Does the size of the admitted set matter, on the submitted checkpoint?

The released policy is trained for three opponent slots, and the runtime packs
the relevance-ranked neighbours into exactly that many. The question a reviewer
asks about a rule like this is whether the number is load bearing, so the probe
re-runs the same cases with the budget reduced to one and to two slots. It is a
runtime change only: the checkpoint, the scene, the seeds and every weight are
the ones of the reported arm, and `max_neighbors` is the single edited key.

The script reads the endpoint audit's verdicts for each variant plus the
recorded selector state, and writes two tables:

    case_level.csv   one row per case and budget
    aggregate.csv    one row per budget

Usage:
    python3 scripts/analyze_admission_budget_probe.py \
        --root <matrix root> --case-plan <plan.csv> --out <dir>
"""
import argparse
import csv
import json
import math
import os
import sys
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.audit_validity_endpoint_v3 import run_job  # noqa: E402

VARIANTS = {
    "k3_released": "main_final_20260922",
    "k2": "probe_kbudget_k2_20260923",
    "k1": "probe_kbudget_k1_20260923",
}
ENDPOINTS = ["P", "L", "C", "T_v3", "S_v3", "E_pass", "E_valid", "E_full", "E_race"]


def admitted_sizes(path):
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
    case_dir = Path(root) / case
    trace_path = case_dir / "traces" / f"{algorithm}_n{num_agents}_seed{seed}.trace.json"
    row = {}
    if trace_path.exists():
        row, _ = run_job((root, case, algorithm, num_agents, seed, tag, "procedural", config))
    sizes = admitted_sizes(trace_path) if trace_path.exists() else []
    record = {"case": case, "algorithm": algorithm, "num_agents": num_agents, "seed": seed}
    for key in ENDPOINTS:
        record[key] = bool(row.get(key)) if row else False
    for key in ("grass_fraction", "rank_gain", "time_to_pass_steps", "in_corridor_fraction"):
        value = row.get(key)
        record[key] = "" if value is None else value
    record["steps_recorded"] = len(sizes)
    record["admitted_mean"] = (sum(sizes) / len(sizes)) if sizes else ""
    record["admitted_max"] = max(sizes) if sizes else ""
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--case-plan", required=True,
                        help="CSV with columns tag,num_agents,seed")
    parser.add_argument("--algorithm", default="ours_dnq_dlc")
    parser.add_argument("--out", required=True)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--protocol",
                        default="validity_final_all/protocol.json",
                        help="endpoint configuration, relative to --root")
    args = parser.parse_args()

    root = Path(args.root)
    config = json.load(open(root / args.protocol))["config"]
    plan = list(csv.DictReader(open(args.case_plan)))
    jobs = []
    for label, variant in VARIANTS.items():
        for item in plan:
            tag = item["tag"]
            num_agents = int(item["num_agents"])
            seed = int(item["seed"])
            case = f"{tag}_n{num_agents}_seed{seed}"
            jobs.append((str(root / variant), case, args.algorithm, num_agents, seed, tag, config, label))
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(analyse_case, [job[:7] for job in jobs]))
    labels = [job[7] for job in jobs]
    for record, label in zip(results, labels):
        record["budget"] = label

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "case_level.csv", "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)

    aggregate = []
    for label in VARIANTS:
        rows = [r for r in results if r["budget"] == label]
        grass = [r["grass_fraction"] for r in rows
                 if isinstance(r["grass_fraction"], float) and not math.isnan(r["grass_fraction"])]
        rank = [r["rank_gain"] for r in rows if isinstance(r["rank_gain"], (int, float))]
        admitted = [r["admitted_mean"] for r in rows if isinstance(r["admitted_mean"], float)]
        record = {"budget": label, "cases": len(rows)}
        for key in ("P", "E_full", "E_race"):
            record[key] = sum(1 for r in rows if r[key])
        # Containment exists only where an auditable pass was found, so the
        # denominator travels with the mean.
        record["grass_cases"] = len(grass)
        record["grass_mean"] = (sum(grass) / len(grass)) if grass else ""
        record["rank_gain_sum"] = sum(rank) if rank else ""
        record["admitted_mean"] = (sum(admitted) / len(admitted)) if admitted else ""
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
