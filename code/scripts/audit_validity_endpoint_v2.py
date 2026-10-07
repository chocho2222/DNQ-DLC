#!/usr/bin/env python
"""Validity-oriented overtaking endpoint (v2) for the frozen multi-car evaluation.

Read-only with respect to simulator outputs. It re-audits stored traces and adds
the corrected cross-track semantics that the frozen legacy protocol never logged:

    lat_true = <position - nearest centre-line sample, track normal>/TRACK_WIDTH

so that |lat_true| <= 1.0 means "inside the road edge" (half-width = TRACK_WIDTH).

Endpoint family (pre-registered, reported together, never cherry-picked):

    E_pass  = P and L and C                      valid pass, no geometry clause
    E_valid = E_pass and T_v2                    + stays on the road
    E_full  = E_valid and S_v2                   + post-pass stability

    P      physical pass (approach -20 m .. -4 m, then +4 m along-track lead)
    L      lead >= +4 m for the 50-step hold window
    C      no recorder contact involving the target from event start to hold end
    T_v2   in-corridor fraction >= 0.70 of the window steps with |lat_true| <= 1.0
           and no continuous off-road run longer than 10 steps
    S_v2   hold window: speed >= 1 m/s, heading cos >= 0.82, no backward flag,
           max per-step |delta lat_true| <= 0.10 (calibrated so that competent
           rule controllers pass ~99% of windows; non-binding for them)

Threshold sensitivity is reported as a profile over in-corridor fractions.
The legacy predicates (T_old, S_old, strict_old) are recomputed for validation
against the frozen aggregates.

Usage:
    python3 scripts/audit_validity_endpoint_v2.py --out <dir> [--experiments E1,E2,E3]
"""
import argparse
import csv
import hashlib
import json
import math
import os
from concurrent.futures import ProcessPoolExecutor

import numpy as np

TRACK_WIDTH = 40.0 / 6.0
TARGET_AGENT_FALLBACK = -1

CASE_PLAN = "outputs/tits_dynamic_graph_expanded/e1_200_budget_matched/tables/expanded_benchmark_case_plan.pre_resume_20260915.csv"
PROFILE_THRESHOLDS = [0.50, 0.60, 0.70, 0.80, 0.90, 0.95, 1.00]


def wilson(k, n, z=1.959963984540054):
    if n == 0:
        return (None, None)
    p = k / n
    den = 1 + z * z / n
    cen = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, cen - half), min(1.0, cen + half))


def circular_delta(cur, prev, period):
    d = float(cur) - float(prev)
    return (d + period / 2.0) % period - period / 2.0


def track_geometry(points):
    n = len(points)
    lengths = [math.hypot(points[(i + 1) % n][0] - points[i][0],
                          points[(i + 1) % n][1] - points[i][1]) for i in range(n)]
    cumulative = [0.0]
    for length in lengths[:-1]:
        cumulative.append(cumulative[-1] + length)
    return cumulative, sum(lengths)


def unwrapped_progress(trace, agent, cumulative, lap):
    wrapped = [float(cumulative[int(row["track_index"][agent])]) for row in trace]
    out = [wrapped[0]]
    for prev, cur in zip(wrapped, wrapped[1:]):
        out.append(out[-1] + circular_delta(cur, prev, lap))
    return out


def detect_events(trace, target, cumulative, lap, approach, margin):
    target_s = unwrapped_progress(trace, target, cumulative, lap)
    events = []
    for opponent in range(len(trace[0]["positions"])):
        if opponent == target:
            continue
        opp_s = unwrapped_progress(trace, opponent, cumulative, lap)
        offset = circular_delta(target_s[0], opp_s[0], lap) - (target_s[0] - opp_s[0])
        rel = [a - b - offset for a, b in zip(target_s, opp_s)]
        start = None
        for idx, gap in enumerate(rel):
            if start is None and -approach <= gap <= -margin:
                start = idx
            elif start is not None and gap >= margin:
                events.append({"opponent": opponent, "start_index": start,
                               "complete_index": idx, "rel": rel})
                start = None
            elif start is not None and gap < -approach:
                start = None
    return events


def longest_run(mask):
    best = run = 0
    for flag in mask:
        run = run + 1 if flag else 0
        best = max(best, run)
    return best


def audit_event(trace, event, target, points, normal, cfg):
    hold = cfg["hold"]
    start_index = int(event["start_index"])
    complete_index = int(event["complete_index"])
    stop_index = complete_index + hold
    if stop_index >= len(trace):
        return {"available": False, "reason": "post_pass_window_censored"}
    rows = trace[start_index:stop_index + 1]
    rel = event["rel"]
    margin = cfg["pass_margin"]
    contact_steps = {int(row["step"]) for row in rows
                     if any(target in c.get("agents", []) for c in row.get("contacts", []))}
    contact_free = not contact_steps
    physical_pass = rel[start_index] <= -margin and rel[complete_index] >= margin
    sustained_lead = physical_pass and min(rel[complete_index:stop_index + 1]) >= margin

    grass = np.array([1.0 if r["telemetry"]["on_grass"][target] else 0.0 for r in rows])
    backward = np.array([1.0 if r["telemetry"]["backward"][target] else 0.0 for r in rows])
    heading_cos = np.array([float(r["telemetry"]["heading_cos"][target]) for r in rows])
    speed = np.array([float(r["speed"][target]) for r in rows])
    legacy = np.abs(np.array([float(r["telemetry"]["lateral_error"][target]) for r in rows]))
    true_lat = np.empty(len(rows))
    guard = np.zeros(len(rows))
    for i, row in enumerate(rows):
        index = int(row["track_index"][target])
        index = min(max(index, 0), len(points) - 1)
        delta = np.asarray(row["positions"][target], float) - points[index]
        true_lat[i] = abs(float(np.dot(delta, normal[index]))) / TRACK_WIDTH
        guard[i] = 1.0 if row.get("target_policy_debug", {}).get("hard_recovery") else 0.0

    off = true_lat > cfg["corridor_limit"]
    in_corridor = float(1.0 - off.mean())
    longest_off = longest_run(off)
    step_lat = np.abs(np.diff(true_lat)) if len(true_lat) > 1 else np.zeros(1)

    hold_lat = true_lat[-hold:]
    hold_step = np.abs(np.diff(hold_lat)) if len(hold_lat) > 1 else np.zeros(1)
    T_v2 = bool(in_corridor >= cfg["in_corridor_min"] and longest_off <= cfg["max_off_run"])
    S_v2 = bool(np.isfinite(speed[-hold:]).all()
                and speed[-hold:].min() >= cfg["min_speed"]
                and hold_step.max() <= cfg["lateral_step_bound"]
                and heading_cos[-hold:].min() >= cfg["heading_cos_min"]
                and backward[-hold:].max() == 0)
    T_old = bool(grass.max() == 0 and backward.max() == 0
                 and legacy.max() <= cfg["legacy_lateral_limit"]
                 and heading_cos.min() >= cfg["heading_cos_min"])
    legacy_hold_step = np.abs(np.diff(legacy[-hold:])) if hold > 1 else np.zeros(1)
    S_old = bool(np.isfinite(speed[-hold:]).all()
                 and speed[-hold:].min() >= cfg["min_speed"]
                 and legacy_hold_step.max() <= cfg["legacy_step_limit"]
                 and heading_cos[-hold:].min() >= cfg["heading_cos_min"]
                 and backward[-hold:].max() == 0)

    E_pass = bool(physical_pass and sustained_lead and contact_free)
    return {
        "available": True,
        "opponent": int(event["opponent"]),
        "start_step": int(trace[start_index]["step"]),
        "complete_step": int(trace[complete_index]["step"]),
        "event_steps": int(len(rows)),
        "physical_pass": bool(physical_pass),
        "sustained_lead": bool(sustained_lead),
        "contact_free": bool(contact_free),
        "contact_count": int(len(contact_steps)),
        "T_v2": T_v2,
        "S_v2": S_v2,
        "E_pass": E_pass,
        "E_valid": bool(E_pass and T_v2),
        "E_full": bool(E_pass and T_v2 and S_v2),
        "T_old": T_old,
        "S_old": S_old,
        "strict_old": bool(contact_free and sustained_lead and T_old and S_old),
        "in_corridor": in_corridor,
        "frac_offroad": float(off.mean()),
        "longest_off_run": int(longest_off),
        "mean_abs_lat": float(true_lat.mean()),
        "max_abs_lat": float(true_lat.max()),
        "lateral_rmse": float(np.sqrt(np.mean(true_lat ** 2))),
        "max_step_lat": float(step_lat.max()),
        "max_step_lat_hold": float(hold_step.max()),
        "grass_fraction": float(grass.mean()),
        "backward_fraction": float(backward.mean()),
        "mean_heading_error": float(np.arccos(np.clip(heading_cos, -1.0, 1.0)).mean()),
        "min_heading_cos": float(heading_cos.min()),
        "mean_speed": float(speed.mean()),
        "min_speed_hold": float(speed[-hold:].min()),
        "max_abs_lat_legacy": float(legacy.max()),
        "guard_fraction": float(guard.mean()),
    }


def run_job(job):
    root, case_dir, algorithm, num_agents, seed, experiment_id, track_id, cfg = job
    stem = f"{algorithm}_n{num_agents}_seed{seed}"
    summary_path = os.path.join(root, case_dir, "summaries", f"{stem}.summary.json")
    trace_path = os.path.join(root, case_dir, "traces", f"{stem}.trace.json")
    initial_path = os.path.join(root, case_dir, "traces", f"{stem}.initial.json")
    base = {"experiment_id": experiment_id, "track_id": track_id, "algorithm": algorithm,
            "seed": seed, "num_agents": num_agents, "case_dir": case_dir}
    if not (os.path.exists(summary_path) and os.path.exists(trace_path) and os.path.exists(initial_path)):
        return ({**base, "status": "missing"}, [])
    try:
        with open(initial_path) as fh:
            initial = json.load(fh)
        with open(trace_path) as fh:
            trace = json.load(fh)
        with open(summary_path) as fh:
            summary = json.load(fh)
        track = np.asarray(initial["track"], float)
        points = track[:, 2:4]
        beta = track[:, 1]
        normal = np.stack([np.cos(beta), np.sin(beta)], 1)
        cumulative, lap = track_geometry(points)
        target = int(summary.get("target_agent", TARGET_AGENT_FALLBACK if TARGET_AGENT_FALLBACK > 0 else num_agents - 1))
        events = detect_events(trace, target, cumulative, lap, cfg["approach_distance"], cfg["pass_margin"])
        audited = [audit_event(trace, e, target, points, normal, cfg) for e in events]
        available = [x for x in audited if x.get("available")]
        row = {**base, "status": "ok", "target_agent": target,
               "event_count": len(events), "available_event_count": len(available),
               "post_pass_censored": bool(events) and not available,
               "episode_steps": len(trace),
               "latency_ms": float(summary.get("compute_latency_ms", float("nan"))),
               "latency_p95_ms": float(summary.get("compute_latency_p95_ms", float("nan"))),
               "recovery_rate": float(summary.get("hard_recovery_rate", float("nan"))),
               "rank_gain": summary.get("rank_gain"),
               "target_progress": summary.get("target_progress"),
               "overtake_success_legacy": bool(summary.get("overtake_success"))}
        for key in ["physical_pass", "sustained_lead", "contact_free", "T_v2", "S_v2",
                    "E_pass", "E_valid", "E_full", "T_old", "S_old", "strict_old"]:
            row[key] = bool(any(x.get(key, False) for x in available))
        for key in ["in_corridor", "frac_offroad", "longest_off_run", "mean_abs_lat", "max_abs_lat",
                    "lateral_rmse", "max_step_lat", "max_step_lat_hold", "grass_fraction",
                    "backward_fraction", "mean_heading_error", "mean_speed", "guard_fraction"]:
            values = [x[key] for x in available if x.get(key) is not None]
            row[key] = float(np.mean(values)) if values else float("nan")
        for threshold in PROFILE_THRESHOLDS:
            tag = f"profile_{int(round(threshold * 100)):03d}"
            row[tag] = bool(any(x.get("E_pass") and x.get("in_corridor", 0) >= threshold - 1e-9
                                for x in available))
            row[f"{tag}_notrun"] = bool(any(x.get("E_pass") and x.get("in_corridor", 0) >= threshold - 1e-9
                                            and x.get("longest_off_run", 10 ** 9) <= cfg["max_off_run"]
                                            for x in available))
        event_rows = [{**base, "target_agent": target, **x} for x in available]
        return row, event_rows
    except Exception as exc:  # noqa: BLE001
        return ({**base, "status": "error", "error": repr(exc)[:200]}, [])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=os.getcwd())
    parser.add_argument("--case-plan", default=CASE_PLAN)
    parser.add_argument("--out", required=True)
    parser.add_argument("--experiments", default="E1,E2,E3,E6")
    parser.add_argument("--methods", default="")
    parser.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 8) - 4))
    parser.add_argument("--hold", type=int, default=50)
    parser.add_argument("--approach-distance", type=float, default=20.0)
    parser.add_argument("--pass-margin", type=float, default=4.0)
    parser.add_argument("--in-corridor-min", type=float, default=0.70)
    parser.add_argument("--corridor-limit", type=float, default=1.0)
    parser.add_argument("--max-off-run", type=int, default=10)
    parser.add_argument("--lateral-step-bound", type=float, default=0.10)
    parser.add_argument("--min-speed", type=float, default=1.0)
    parser.add_argument("--heading-cos-min", type=float, default=0.82)
    parser.add_argument("--legacy-lateral-limit", type=float, default=0.45)
    parser.add_argument("--legacy-step-limit", type=float, default=0.25)
    parser.add_argument("--max-cases", type=int, default=0)
    args = parser.parse_args()

    root = os.path.abspath(args.root)
    cfg = {"hold": args.hold, "approach_distance": args.approach_distance,
           "pass_margin": args.pass_margin, "in_corridor_min": args.in_corridor_min,
           "corridor_limit": args.corridor_limit, "max_off_run": args.max_off_run,
           "lateral_step_bound": args.lateral_step_bound, "min_speed": args.min_speed,
           "heading_cos_min": args.heading_cos_min,
           "legacy_lateral_limit": args.legacy_lateral_limit,
           "legacy_step_limit": args.legacy_step_limit}

    wanted = {x.strip() for x in args.experiments.split(",") if x.strip()}
    methods = {x.strip() for x in args.methods.split(",") if x.strip()}
    plan_path = os.path.join(root, args.case_plan)
    plan = [r for r in csv.DictReader(open(plan_path, encoding="utf-8"))]
    selected = [r for r in plan if any(r["experiment_id"].startswith(w) for w in wanted)]
    if args.max_cases:
        selected = selected[:args.max_cases]
    jobs = []
    for case in selected:
        for algorithm in [a.strip() for a in case["algorithms"].split(",") if a.strip()]:
            if methods and algorithm not in methods:
                continue
            jobs.append((root, case["out_dir"], algorithm, int(case["num_agents"]),
                         int(case["seed"]), case["experiment_id"], case.get("track_id", ""), cfg))
    print(json.dumps({"cases": len(selected), "jobs": len(jobs), "workers": args.workers}), flush=True)

    rows, event_rows = [], []
    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        for done, (row, events) in enumerate(executor.map(run_job, jobs, chunksize=4), 1):
            rows.append(row)
            event_rows.extend(events)
            if done % 250 == 0:
                print(f"  {done}/{len(jobs)}", flush=True)

    out_dir = os.path.abspath(args.out)
    os.makedirs(out_dir, exist_ok=True)
    _write_csv(os.path.join(out_dir, "case_level.csv"), rows)
    _write_csv(os.path.join(out_dir, "event_level.csv"), event_rows)

    endpoints = ["physical_pass", "sustained_lead", "contact_free", "T_v2", "S_v2",
                 "E_pass", "E_valid", "E_full", "T_old", "S_old", "strict_old"]
    aggregates = []
    for experiment in sorted({r["experiment_id"] for r in rows}):
        for algorithm in sorted({r["algorithm"] for r in rows if r["experiment_id"] == experiment}):
            group = [r for r in rows if r["experiment_id"] == experiment and r["algorithm"] == algorithm]
            n = len(group)
            for endpoint in endpoints:
                k = sum(bool(r.get(endpoint)) for r in group)
                low, high = wilson(k, n)
                aggregates.append({"experiment_id": experiment, "algorithm": algorithm, "endpoint": endpoint,
                                   "n": n, "count": k, "rate": k / n if n else float("nan"),
                                   "wilson_low": low, "wilson_high": high,
                                   "censored_cases": sum(bool(r.get("post_pass_censored")) for r in group),
                                   "mean_recovery_rate": _mean([r.get("recovery_rate") for r in group]),
                                   "mean_latency_ms": _mean([r.get("latency_ms") for r in group]),
                                   "mean_in_corridor": _mean([r.get("in_corridor") for r in group]),
                                   "mean_frac_offroad": _mean([r.get("frac_offroad") for r in group]),
                                   "mean_lateral_rmse": _mean([r.get("lateral_rmse") for r in group]),
                                   "mean_abs_lat": _mean([r.get("mean_abs_lat") for r in group]),
                                   "max_abs_lat": _max([r.get("max_abs_lat") for r in group]),
                                   "mean_grass_fraction": _mean([r.get("grass_fraction") for r in group]),
                                   "mean_backward_fraction": _mean([r.get("backward_fraction") for r in group]),
                                   "mean_heading_error": _mean([r.get("mean_heading_error") for r in group])})
    _write_csv(os.path.join(out_dir, "aggregate.csv"), aggregates)

    profile_rows = []
    for experiment in sorted({r["experiment_id"] for r in rows}):
        for algorithm in sorted({r["algorithm"] for r in rows if r["experiment_id"] == experiment}):
            group = [r for r in rows if r["experiment_id"] == experiment and r["algorithm"] == algorithm]
            n = len(group)
            for threshold in PROFILE_THRESHOLDS:
                tag = f"profile_{int(round(threshold * 100)):03d}"
                k = sum(bool(r.get(tag)) for r in group)
                k_run = sum(bool(r.get(f"{tag}_notrun")) for r in group)
                low, high = wilson(k, n)
                profile_rows.append({"experiment_id": experiment, "algorithm": algorithm,
                                     "in_corridor_min": threshold, "n": n,
                                     "count_Epass_and_corridor": k, "rate": k / n if n else float("nan"),
                                     "wilson_low": low, "wilson_high": high,
                                     "count_with_run_limit": k_run,
                                     "rate_with_run_limit": k_run / n if n else float("nan")})
    _write_csv(os.path.join(out_dir, "profile.csv"), profile_rows)

    protocol = {"endpoints": {
        "E_pass": "P and L and C",
        "E_valid": "P and L and C and T_v2",
        "E_full": "P and L and C and T_v2 and S_v2"},
        "definitions": {
            "P": f"along-track lead crosses {args.pass_margin} m after an approach inside "
                 f"[-{args.approach_distance}, -{args.pass_margin}] m",
            "L": f"lead stays >= {args.pass_margin} m for {args.hold} steps after completion",
            "C": "no recorder contact involving the target from event start through hold end",
            "T_v2": f"in-corridor fraction >= {args.in_corridor_min} with |lat_true| <= {args.corridor_limit} "
                    f"and no off-road run longer than {args.max_off_run} steps",
            "S_v2": f"hold window speed >= {args.min_speed} m/s, heading cos >= {args.heading_cos_min}, "
                    f"no backward flag, per-step |delta lat_true| <= {args.lateral_step_bound}"},
        "lat_true": "|(position - nearest centreline sample) . (cos beta, sin beta)| / TRACK_WIDTH, "
                    "beta = track[:,1] (the simulator's border-normal angle)",
        "legacy_note": "telemetry lateral_error is the local-tangent projection and is structurally bounded "
                       "by half the centreline sample spacing; it is recomputed here only for validation",
        "threshold_calibration": "lateral_step_bound and in_corridor_min were fixed before evaluation: the "
                                 "step bound is placed above the 99th percentile of rule-controller hold windows",
        "denominator_policy": "all planned case-algorithm rows retained; censored and missing rows count as failures"}
    (open(os.path.join(out_dir, "protocol.json"), "w")).write(json.dumps(protocol, indent=2))
    manifest = {"case_plan": plan_path,
                "case_plan_sha256": hashlib.sha256(open(plan_path, "rb").read()).hexdigest(),
                "script_sha256": hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest(),
                "cases": len(selected), "jobs": len(jobs), "rows": len(rows), "events": len(event_rows),
                "config": cfg}
    (open(os.path.join(out_dir, "manifest.json"), "w")).write(json.dumps(manifest, indent=2))
    print(json.dumps({"out": out_dir, "rows": len(rows), "events": len(event_rows)}, indent=2))


def _mean(values):
    vals = [float(v) for v in values if v is not None and not math.isnan(float(v))]
    return float(np.mean(vals)) if vals else float("nan")


def _max(values):
    vals = [float(v) for v in values if v is not None and not math.isnan(float(v))]
    return float(max(vals)) if vals else float("nan")


def _write_csv(path, rows):
    fields = sorted({k for row in rows for k in row})
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
