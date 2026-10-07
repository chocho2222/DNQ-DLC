#!/usr/bin/env python
"""Does the admitted neighbourhood contain the vehicle being passed?

The dynamic-neighbourhood claim needs one piece of evidence that the
controller-internal tables do not provide: the opponent that the manoeuvre is
actually about has to be inside the set the planner admits, at the time it
matters. Every run of the main matrix records that set at every step
(``target_policy_debug.selected_neighbor_ids``), and the pass events are
detected with the same routine the endpoint audit uses, so the two can be
joined without a new run.

Usage:
    python3 scripts/analyze_dynamic_neighborhood_events.py --root <matrix dir> \
        --out <dir> [--algorithms ours_dnq_dlc] [--workers 16]
"""
import argparse
import csv
import glob
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.audit_validity_endpoint_v3 import detect_events, track_geometry, wilson  # noqa: E402

APPROACH = 20.0
MARGIN = 4.0
HOLD = 50
PRE = 25


def _admitted(row):
    debug = row.get("target_policy_debug") or {}
    ids = debug.get("selected_neighbor_ids")
    if ids is None:
        return None
    return {int(item) for item in ids}


def analyse_case(path, algorithm, num_agents, seed, case):
    initial_path = path.replace(".trace.json", ".initial.json")
    with open(path) as handle:
        trace = json.load(handle)
    with open(initial_path) as handle:
        initial = json.load(handle)
    points = [[float(v) for v in row[2:4]] for row in initial["track"]]
    cumulative, lap, _ = track_geometry(points)

    first_debug = trace[0].get("target_policy_debug") or {}
    target = int(first_debug.get("target_agent", num_agents - 1))

    sets = [_admitted(row) for row in trace]
    events = detect_events(trace, target, cumulative, lap, APPROACH, MARGIN)

    rows = []
    for event in events:
        start = int(event["start_index"])
        complete = int(event["complete_index"])
        stop = complete + HOLD
        man_start = max(0, complete - PRE)
        if stop >= len(trace):
            continue
        opponent = int(event["opponent"])
        approach_sets = [sets[i] for i in range(start, complete + 1) if sets[i] is not None]
        window_sets = [sets[i] for i in range(man_start, stop + 1) if sets[i] is not None]
        if not window_sets:
            continue
        resident = [opponent in item for item in window_sets]
        approach_resident = [opponent in item for item in approach_sets]
        changes = sum(1 for a, b in zip(window_sets, window_sets[1:]) if a != b)
        sizes = [len(item) for item in window_sets]
        rows.append({
            "case": case, "algorithm": algorithm, "num_agents": num_agents,
            "seed": seed, "target_agent": target, "opponent": opponent,
            "start_index": start, "complete_index": complete,
            "man_start_index": man_start, "stop_index": stop,
            "window_steps": len(window_sets),
            "set_changes_in_window": changes,
            "admitted_mean_in_window": sum(sizes) / len(sizes),
            "admitted_empty_share": sum(1 for s in sizes if s == 0) / len(sizes),
            "partner_in_window_any": bool(any(resident)),
            "partner_in_window_share": sum(resident) / len(resident),
            "partner_at_complete": bool(resident[-1]),
            "partner_at_window_start": bool(resident[0]),
            "partner_in_approach_any": bool(any(approach_resident)) if approach_resident else False,
        })
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--algorithms", default="ours_dnq_dlc")
    parser.add_argument("--workers", type=int, default=16)
    args = parser.parse_args()

    wanted = {item.strip() for item in args.algorithms.split(",") if item.strip()}
    jobs = []
    for case_dir in sorted(glob.glob(os.path.join(args.root, "M*_seed*"))):
        case = os.path.basename(case_dir)
        parts = case.rsplit("_n", 1)
        num_agents = int(parts[1].split("_")[0])
        seed = int(case.rsplit("_seed", 1)[1])
        experiment = parts[0]
        for trace_path in sorted(glob.glob(os.path.join(case_dir, "traces", "*.trace.json"))):
            algorithm = os.path.basename(trace_path).rsplit(".trace.json", 1)[0]
            algorithm = algorithm.rsplit(f"_n{num_agents}_seed{seed}", 1)[0]
            if algorithm not in wanted:
                continue
            jobs.append((trace_path, algorithm, num_agents, seed, case, experiment))

    rows = []
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(analyse_case, job[0], job[1], job[2], job[3], job[4])
                   for job in jobs]
        for job, future in zip(jobs, futures):
            try:
                result = future.result()
            except Exception as exc:  # noqa: BLE001
                print(f"  failed {job[4]}: {exc!r}", file=sys.stderr)
                continue
            for row in result:
                row["experiment_id"] = job[5]
            rows.extend(result)

    os.makedirs(args.out, exist_ok=True)
    fields = ["experiment_id", "case", "algorithm", "num_agents", "seed", "target_agent",
              "opponent", "start_index", "complete_index", "man_start_index", "stop_index",
              "window_steps", "set_changes_in_window", "admitted_mean_in_window",
              "admitted_empty_share", "partner_in_window_any", "partner_in_window_share",
              "partner_at_complete", "partner_at_window_start", "partner_in_approach_any"]
    with open(os.path.join(args.out, "neighborhood_event_level.csv"), "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    print(f"{len(rows)} events over {len({r['case'] for r in rows})} cases")
    experiments = ["ALL"] + sorted({r["experiment_id"] for r in rows})
    summary = []
    for experiment in experiments:
        subset = rows if experiment == "ALL" else [r for r in rows if r["experiment_id"] == experiment]
        if not subset:
            continue
        count = len(subset)
        def mean(key, items=subset):
            return sum(float(r[key]) for r in items) / len(items)
        low, high = wilson(sum(1 for r in subset if r["partner_in_window_any"]), count)
        low_complete, high_complete = wilson(sum(1 for r in subset if r["partner_at_complete"]), count)
        summary.append({
            "experiment_id": experiment,
            "cases": len({r["case"] for r in subset}),
            "events": count,
            "partner_in_window_count": sum(1 for r in subset if r["partner_in_window_any"]),
            "partner_in_window_rate": sum(1 for r in subset if r["partner_in_window_any"]) / count,
            "partner_in_window_wilson_low": low,
            "partner_in_window_wilson_high": high,
            "partner_at_complete_count": sum(1 for r in subset if r["partner_at_complete"]),
            "partner_at_complete_rate": sum(1 for r in subset if r["partner_at_complete"]) / count,
            "partner_at_complete_wilson_low": low_complete,
            "partner_at_complete_wilson_high": high_complete,
            "partner_window_share_mean": mean("partner_in_window_share"),
            "set_changes_in_window_mean": mean("set_changes_in_window"),
            "admitted_mean_in_window": mean("admitted_mean_in_window"),
            "window_steps_mean": mean("window_steps"),
        })
    with open(os.path.join(args.out, "neighborhood_summary.csv"), "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary[0].keys()))
        writer.writeheader()
        writer.writerows(summary)

    print(f"{'scale':12s} {'events':>6s} {'cases':>5s} {'partner_any':>11s} "
          f"{'at_complete':>11s} {'share_mean':>10s} {'changes':>8s} {'empty_share':>11s}")
    for entry in summary:
        experiment = entry["experiment_id"]
        print(f"{experiment:12s} {entry['events']:6d} {entry['cases']:5d} "
              f"{entry['partner_in_window_rate']:11.3f} {entry['partner_at_complete_rate']:11.3f} "
              f"{entry['partner_window_share_mean']:10.3f} {entry['set_changes_in_window_mean']:8.2f}")


if __name__ == "__main__":
    main()
