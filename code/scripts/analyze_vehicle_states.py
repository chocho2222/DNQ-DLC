#!/usr/bin/env python
"""Vehicle-state analysis of the multi-car overtaking traces.

This is a descriptive analysis of the *state* of every vehicle in a case, not a
component ablation. It answers "how does the manoeuvre actually happen" with
recorded quantities only:

  * the three-phase structure of every pass (approach -> alongside -> clear),
    in steps, for the target and the vehicle it passes;
  * the longitudinal speed of the target and of the rival in each phase, so the
    speed advantage that makes the pass possible is visible instead of assumed;
  * the lateral excursion of the target during the manoeuvre and the smallest
    distance it keeps to the rival and to every other vehicle, which is what
    separates a pass from a squeeze;
  * how long the manoeuvre spent inside the road, how often the stability clause
    held, how much of it was spent under the safety guard;
  * for the dynamic-neighbourhood claim: how often the admitted set changes,
    how long an admitted vehicle stays admitted, and whether the vehicle that is
    actually being passed was in the admitted set while the pass happened.

Every pass event is detected with the same routine the endpoint audit uses, so
the events here are the events the paper's endpoints are computed on.

Usage:
    python3 scripts/analyze_vehicle_states.py --root <case root> --case-plan <csv> \
        --out <dir> [--hold 50]
"""
import argparse
import csv
import json
import math
import os
import sys
from collections import Counter, defaultdict

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from scripts.audit_validity_endpoint_v3 import (  # noqa: E402
    detect_events,
    track_frames,
    track_geometry,
    wilson,
)

TRACK_WIDTH = 40.0 / 6.0
HOLD_DEFAULT = 50


def read_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def mean(values):
    values = [float(v) for v in values if v is not None and np.isfinite(float(v))]
    return float(np.mean(values)) if values else float("nan")


def percentile(values, q):
    values = [float(v) for v in values if v is not None and np.isfinite(float(v))]
    return float(np.percentile(values, q)) if values else float("nan")


def ci95(values):
    """Normal-approximation 95% interval of the mean, or (nan, nan)."""
    values = [float(v) for v in values if v is not None and np.isfinite(float(v))]
    if len(values) < 2:
        return float("nan"), float("nan")
    arr = np.asarray(values, dtype=float)
    half = 1.959963984540054 * float(arr.std(ddof=1)) / math.sqrt(len(arr))
    return float(arr.mean() - half), float(arr.mean() + half)


def admitted_set(row):
    """Vehicles the admission rule kept for this step, or None if unrecorded."""
    debug = row.get("target_policy_debug") or {}
    selected = debug.get("selected_neighbor_ids")
    if selected is None:
        return None
    return [int(item) for item in selected]


def neighborhood_stats(trace):
    """How dynamic the admitted neighbourhood actually is."""
    sets = []
    for row in trace:
        selected = admitted_set(row)
        if selected is not None:
            sets.append(selected)
    if not sets:
        return {
            "neighbor_steps": 0,
            "neighbor_admitted_mean": float("nan"),
            "neighbor_churn_rate": float("nan"),
            "neighbor_distinct_total": float("nan"),
            "neighbor_residence_mean": float("nan"),
        }
    switches = sum(1 for a, b in zip(sets, sets[1:]) if set(a) != set(b))
    residence = []
    prev, run = set(sets[0]), 1
    for current in sets[1:]:
        current = set(current)
        if current == prev:
            run += 1
        else:
            residence.append(run)
            prev, run = current, 1
    residence.append(run)
    return {
        "neighbor_steps": len(sets),
        "neighbor_admitted_mean": mean([len(s) for s in sets]),
        "neighbor_churn_rate": switches / max(len(sets) - 1, 1),
        "neighbor_distinct_total": float(len(set().union(*[set(s) for s in sets]))),
        "neighbor_residence_mean": mean(residence),
    }


def pairwise_rel(trace, index, target):
    """Longitudinal/lateral offset of every other vehicle in the target frame."""
    positions = np.asarray(trace[index]["positions"], dtype=float)
    angles = np.asarray(trace[index]["hull_angles"], dtype=float)
    heading = np.array([math.cos(float(angles[target])), math.sin(float(angles[target]))])
    left = np.array([-heading[1], heading[0]])
    delta = positions - positions[target]
    return delta @ heading, delta @ left


def distance(positions, a, b):
    return float(np.linalg.norm(np.asarray(positions[a], float) - np.asarray(positions[b], float)))


def event_state(trace, event, target, hold):
    """Vehicle-state descriptors of one pass event."""
    start = int(event["start_index"])
    complete = int(event["complete_index"])
    rival = int(event["opponent"])
    end = min(len(trace) - 1, complete + hold)
    window = list(range(start, end + 1))
    maneuver = list(range(start, complete + 1)) or [complete]
    alongside = [i for i in maneuver if abs(float(event["rel"][i])) < 4.0]
    approach = [i for i in range(start, complete) if float(event["rel"][i]) <= -4.0] or [start]
    hold_window = list(range(complete, end + 1))

    def speeds(steps, agent):
        return mean([trace[i]["speed"][agent] for i in steps])

    def gap_to_rival(i):
        return distance(trace[i]["positions"], target, rival)

    def min_gap_to_other(i):
        others = [a for a in range(len(trace[i]["positions"])) if a not in (target, rival)]
        return min((distance(trace[i]["positions"], target, a) for a in others), default=float("nan"))

    lateral = [abs(float(trace[i]["telemetry"]["lateral_error"][target])) for i in maneuver]
    admitted_hits = 0
    admitted_steps = 0
    guard_steps = 0
    bypass_steps = 0
    for i in maneuver:
        selected = admitted_set(trace[i])
        if selected is not None:
            admitted_steps += 1
            if rival in selected:
                admitted_hits += 1
    for i in window:
        debug = trace[i].get("target_policy_debug") or {}
        if debug.get("guard_trigger"):
            guard_steps += 1
        if debug.get("planner_bypassed"):
            bypass_steps += 1

    target_approach = speeds(approach, target)
    rival_approach = speeds(approach, rival)
    target_alongside = speeds(alongside or maneuver, target)
    rival_alongside = speeds(alongside or maneuver, rival)

    return {
        "available": True,
        "opponent": rival,
        "start_step": int(trace[start]["step"]),
        "complete_step": int(trace[complete]["step"]),
        "approach_steps": len(approach),
        "alongside_steps": len(alongside),
        "maneuver_steps": len(maneuver),
        "time_to_pass_steps": complete - start,
        "lead_max_maneuver": max(float(event["rel"][i]) for i in maneuver),
        "lead_min_maneuver": min(float(event["rel"][i]) for i in maneuver),
        "clear_steps": end - complete,
        "target_speed_approach": target_approach,
        "rival_speed_approach": rival_approach,
        "speed_advantage_approach": target_approach - rival_approach,
        "target_speed_alongside": target_alongside,
        "rival_speed_alongside": rival_alongside,
        "speed_advantage_alongside": target_alongside - rival_alongside,
        "rival_speed_drop": rival_approach - rival_alongside,
        "target_speed_hold": speeds(hold_window, target),
        "peak_abs_lat_maneuver": float(np.max(lateral)) if lateral else float("nan"),
        "mean_abs_lat_maneuver": mean(lateral),
        "lateral_excursion_range": float(np.max(lateral) - np.min(lateral)) if lateral else float("nan"),
        "min_gap_rival_maneuver": min(gap_to_rival(i) for i in maneuver),
        "min_gap_rival_window": min(gap_to_rival(i) for i in window),
        "min_gap_third_party_maneuver": min(min_gap_to_other(i) for i in maneuver),
        "guard_steps_window": guard_steps,
        "guard_fraction_window": guard_steps / max(len(window), 1),
        "planner_bypassed_window": bypass_steps,
        "rival_admitted_fraction": (admitted_hits / admitted_steps) if admitted_steps else float("nan"),
        "rival_admitted_at_approach_start": bool(
            rival in (admitted_set(trace[start]) or [])
        ) if admitted_set(trace[start]) is not None else None,
        "grass_steps_maneuver": sum(
            1 for i in maneuver if bool(trace[i]["telemetry"]["on_grass"][target])
        ),
        "backward_steps_maneuver": sum(
            1 for i in maneuver if bool(trace[i]["telemetry"]["backward"][target])
        ),
        "heading_cos_min_maneuver": min(
            float(trace[i]["telemetry"]["heading_cos"][target]) for i in maneuver
        ),
    }


def case_state(trace, target, hold, warmup=300):
    """Episode-level state summary for one case and one algorithm.

    The race starts from a standing start, so whole-episode speed means are
    dominated by the launch. The ``race_`` variants drop the first ``warmup``
    steps and describe the racing phase.
    """
    speeds = [float(row["speed"][target]) for row in trace]
    lateral = [abs(float(row["telemetry"]["lateral_error"][target])) for row in trace]
    warm = min(int(warmup), max(len(trace) - 1, 0))
    race_speeds = [float(row["speed"][target]) for row in trace[warm:]] or speeds
    race_lateral = [abs(float(row["telemetry"]["lateral_error"][target])) for row in trace[warm:]] or lateral
    contacts = sum(
        1 for row in trace
        if any(target in pair.get("agents", []) for pair in (row.get("contacts") or []))
    )
    min_gap = float("nan")
    if len(trace[0]["positions"]) > 1:
        per_step = []
        for row in trace:
            others = [a for a in range(len(row["positions"])) if a != target]
            per_step.append(min(distance(row["positions"], target, a) for a in others))
        min_gap = float(np.min(per_step))
    guard = [bool((row.get("target_policy_debug") or {}).get("guard_trigger")) for row in trace]
    stats = {
        "episode_steps": len(trace),
        "warmup_steps": warm,
        "race_speed_mean": mean(race_speeds),
        "race_speed_p10": percentile(race_speeds, 10),
        "race_speed_p50": percentile(race_speeds, 50),
        "race_speed_p90": percentile(race_speeds, 90),
        "race_lat_mean": mean(race_lateral),
        "race_lat_p90": percentile(race_lateral, 90),
        "target_speed_mean": mean(speeds),
        "target_speed_p10": percentile(speeds, 10),
        "target_speed_p50": percentile(speeds, 50),
        "target_speed_p90": percentile(speeds, 90),
        "target_speed_std": float(np.std(speeds)) if speeds else float("nan"),
        "target_lat_mean": mean(lateral),
        "target_lat_p90": percentile(lateral, 90),
        "target_lat_max": float(np.max(lateral)) if lateral else float("nan"),
        "target_grass_fraction": mean([1.0 if row["telemetry"]["on_grass"][target] else 0.0 for row in trace]),
        "target_backward_fraction": mean([1.0 if row["telemetry"]["backward"][target] else 0.0 for row in trace]),
        "episode_min_pair_gap": min_gap,
        "target_contact_steps": contacts,
        "guard_fraction_episode": mean([1.0 if flag else 0.0 for flag in guard]),
    }
    stats.update(neighborhood_stats(trace))
    return stats


def near_miss_stats(trace, target, cumulative, lap):
    """Best and worst along-track lead the target reached against any rival.

    ``P`` needs a +4 m lead, so a case whose best lead is +3.5 m is a near miss
    rather than a different kind of failure; keeping the raw number means the
    near misses stay visible instead of disappearing into a boolean.
    """
    from scripts.audit_validity_endpoint_v3 import circular_delta, unwrapped_progress

    target_s = unwrapped_progress(trace, target, cumulative, lap)
    best = float("-inf")
    worst = float("inf")
    for opponent in range(len(trace[0]["positions"])):
        if opponent == target:
            continue
        opp_s = unwrapped_progress(trace, opponent, cumulative, lap)
        offset = (target_s[0] - opp_s[0]) - circular_delta(target_s[0], opp_s[0], lap)
        rel = [a - b - offset for a, b in zip(target_s, opp_s)]
        best = max(best, max(rel))
        worst = min(worst, min(rel))
    return {"best_lead_any": best, "worst_lead_any": worst,
            "lead_margin_to_pass_gate": best - 4.0}


def run_job(job):
    root, case_dir, algorithm, num_agents, seed, experiment_id, track_id, hold = job
    stem = f"{algorithm}_n{num_agents}_seed{seed}"
    base = {"experiment_id": experiment_id, "track_id": track_id, "algorithm": algorithm,
            "seed": seed, "num_agents": num_agents, "case_dir": case_dir}
    summary_path = os.path.join(root, case_dir, "summaries", f"{stem}.summary.json")
    trace_path = os.path.join(root, case_dir, "traces", f"{stem}.trace.json")
    initial_path = os.path.join(root, case_dir, "traces", f"{stem}.initial.json")
    for path in (summary_path, trace_path, initial_path):
        if not os.path.exists(path):
            return {**base, "status": "missing"}, []
    try:
        trace = read_json(trace_path)
        summary = read_json(summary_path)
        initial = read_json(initial_path)
        track = np.asarray(initial["track"], float)
        points = track[:, 2:4]
        cumulative, lap, _ = track_geometry(points)
        target = int(summary.get("target_agent", num_agents - 1))
        case_row = {**base, "status": "ok", "target_agent": target}
        case_row.update(case_state(trace, target, hold))
        case_row.update(near_miss_stats(trace, target, cumulative, lap))
        events = detect_events(trace, target, cumulative, lap, 20.0, 4.0)
        event_rows = []
        for event in events:
            row = event_state(trace, event, target, hold)
            event_rows.append({**base, "target_agent": target, **row})
        return case_row, event_rows
    except Exception as exc:  # noqa: BLE001
        return {**base, "status": "error", "error": repr(exc)[:200]}, []


def read_case_plan(path):
    with open(path, encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path, rows):
    if not rows:
        open(path, "w", encoding="utf-8").close()
        return
    fields = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


CASE_METRICS = [
    "race_speed_mean", "race_speed_p10", "race_speed_p50", "race_speed_p90",
    "race_lat_mean", "race_lat_p90",
    "best_lead_any", "lead_margin_to_pass_gate",
    "target_speed_mean", "target_speed_p10", "target_speed_p50", "target_speed_p90",
    "target_speed_std", "target_lat_mean", "target_lat_p90", "target_lat_max",
    "target_grass_fraction", "episode_min_pair_gap", "target_contact_steps",
    "guard_fraction_episode", "neighbor_admitted_mean", "neighbor_churn_rate",
    "neighbor_distinct_total", "neighbor_residence_mean",
]

EVENT_METRICS = [
    "lead_max_maneuver", "lead_min_maneuver",
    "approach_steps", "alongside_steps", "maneuver_steps", "time_to_pass_steps",
    "target_speed_approach", "rival_speed_approach", "speed_advantage_approach",
    "target_speed_alongside", "rival_speed_alongside", "speed_advantage_alongside",
    "rival_speed_drop", "peak_abs_lat_maneuver", "mean_abs_lat_maneuver",
    "min_gap_rival_maneuver", "min_gap_rival_window", "min_gap_third_party_maneuver",
    "guard_fraction_window", "rival_admitted_fraction", "heading_cos_min_maneuver",
]


def aggregate(case_rows, event_rows):
    by_algorithm = defaultdict(list)
    for row in case_rows:
        if row.get("status") == "ok":
            by_algorithm[row["algorithm"]].append(row)
    events_by_algorithm = defaultdict(list)
    for row in event_rows:
        events_by_algorithm[row["algorithm"]].append(row)
    out = []
    for algorithm, rows in sorted(by_algorithm.items()):
        record = {"algorithm": algorithm, "n_cases": len(rows),
                  "n_events": len(events_by_algorithm.get(algorithm, []))}
        for key in CASE_METRICS:
            values = [row.get(key) for row in rows]
            record[f"{key}_mean"] = mean(values)
            low, high = ci95(values)
            record[f"{key}_ci_low"] = low
            record[f"{key}_ci_high"] = high
        events = events_by_algorithm.get(algorithm, [])
        for key in EVENT_METRICS:
            values = [row.get(key) for row in events]
            record[f"{key}_median"] = percentile(values, 50)
            record[f"{key}_mean"] = mean(values)
        admitted = [row.get("rival_admitted_fraction") for row in events]
        hits = sum(1 for v in admitted if v is not None and np.isfinite(float(v)) and float(v) > 0.0)
        if hits:
            low, high = wilson(hits, len(admitted))
            record["rival_admitted_rate"] = hits / len(admitted)
            record["rival_admitted_rate_ci_low"] = low
            record["rival_admitted_rate_ci_high"] = high
        out.append(record)
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", required=True)
    parser.add_argument("--case-plan", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--hold", type=int, default=HOLD_DEFAULT)
    parser.add_argument("--workers", type=int, default=16)
    args = parser.parse_args()

    os.makedirs(args.out, exist_ok=True)
    plan = read_case_plan(args.case_plan)
    jobs = []
    for row in plan:
        algorithms = [item.strip() for item in str(row.get("algorithms", "")).split(",") if item.strip()]
        for algorithm in algorithms:
            jobs.append((args.root, row["out_dir"], algorithm, int(row["num_agents"]),
                         int(row["seed"]), row.get("experiment_id", ""),
                         row.get("track_id", ""), args.hold))
    from concurrent.futures import ProcessPoolExecutor

    case_rows, event_rows = [], []
    with ProcessPoolExecutor(max_workers=max(1, args.workers)) as pool:
        for case_row, ev_rows in pool.map(run_job, jobs):
            case_rows.append(case_row)
            event_rows.extend(ev_rows)

    write_csv(os.path.join(args.out, "vehicle_case_level.csv"), case_rows)
    write_csv(os.path.join(args.out, "vehicle_event_level.csv"), event_rows)
    aggregate_rows = aggregate(case_rows, event_rows)
    write_csv(os.path.join(args.out, "vehicle_aggregate.csv"), aggregate_rows)
    with open(os.path.join(args.out, "protocol.json"), "w", encoding="utf-8") as handle:
        json.dump({
            "root": args.root,
            "case_plan": args.case_plan,
            "hold": args.hold,
            "event_definition": "same detector as the endpoint audit: approach in [-20, -4] m, lead crosses +4 m",
            "alongside_definition": "|along-track lead| < 4.0 m",
            "lateral_source": "environment telemetry lateral_error for the target",
            "note": "descriptive vehicle-state analysis; no component is ablated here",
        }, handle, ensure_ascii=False, indent=2)
    print(f"cases={len(case_rows)} events={len(event_rows)} algorithms={len(aggregate_rows)}")
    header = f'{"algorithm":32s} {"n":>3s} {"evt":>4s} {"v_mean":>7s} {"churn":>6s} {"along":>6s} {"dspd":>7s} {"gap":>6s} {"minGap":>7s} {"latPk":>6s} {"adm":>5s}'
    print(header)
    for row in aggregate_rows:
        print(f'{row["algorithm"]:32s} {row["n_cases"]:3d} {row["n_events"]:4d} '
              f'{row["target_speed_mean_mean"]:7.2f} {row["neighbor_churn_rate_mean"]:6.3f} '
              f'{row["alongside_steps_median"]:6.1f} {row["speed_advantage_alongside_median"]:7.2f} '
              f'{row["min_gap_rival_maneuver_median"]:6.2f} {row["min_gap_third_party_maneuver_median"]:7.2f} '
              f'{row["peak_abs_lat_maneuver_median"]:6.3f} '
              + (f'{row["rival_admitted_rate"]:5.2f}' if row.get("rival_admitted_rate") is not None else f'{"-":>5s}'))


if __name__ == "__main__":
    main()
