#!/usr/bin/env python
"""Validity-oriented overtaking endpoint (v3) for the multi-car evaluation.

Read-only with respect to stored traces. v3 supersedes v2 on three points that
the v2 re-audit exposed as defects of the *measurement*, not of the controllers:

  1. Cross-track offset. The simulator's legacy telemetry logs
     dot(pos - nearest_centreline_sample, track_tangent)/TRACK_WIDTH, which is a
     projection on the local tangent and is therefore hard-bounded by half the
     centre-line sample spacing. Every |lateral_error| ever recorded is < 0.26
     while the road half-width is exactly one TRACK_WIDTH. v2/v3 recompute

         lat_true = <pos - nearest_centreline_sample, track_normal>/TRACK_WIDTH
         track_normal = (cos beta, sin beta),  beta = track[:, 1]

     so |lat_true| <= 1.0 is "inside the road edge". This is the *same*
     quantity the simulator computes once telemetry_version='corrected_v2'.

  2. Heading agreement. The legacy telemetry stores cos(desired_angle - heading)
     with desired_angle again the *border normal*, so the recorded heading cosine
     is the sine of the true heading error (cos(th) = sin(-e_psi)). v3 rebuilds
     the true heading cosine from the recorded hull angle and the local track
     tangent.

  3. Window scope. The pass event is detected from an approach phase that may
     last hundreds of steps, so corridor compliance measured over the whole
     event window charges the controller for whatever happened while it was
     still queuing behind the target. v3 measures corridor compliance over the
     *maneuver window* [complete - pre, complete + hold], i.e. the half second
     around the crossing plus the hold window, and keeps the full-window value
     as a diagnostic.

Endpoint family (graded, reported together, never cherry-picked). A case
succeeds for an endpoint when at least one of its events satisfies the
conjunction:

    E_pass  = P and L and C            physical overtake happened
    E_valid = E_pass and T_v3          ... and it stayed on the road
    E_full  = E_valid and S_v3         ... and the car was stable afterwards

    P      approach in [-20, -4] m, then the along-track lead crosses +4 m
    L      lead >= +4 m for the whole 50-step hold window (1.0 s at 50 Hz)
    C      no recorder contact involving the target from event start to hold end
    T_v3   in-corridor fraction >= 0.70 over the maneuver window
    S_v3   hold window: speed >= 1 m/s, true heading cos >= 0.82, no backward
           flag, max per-step |delta lat_true| <= 0.10

The continuous off-road run length is *reported*, not gated: v2's hard
"no run longer than 10 steps" clause was never calibrated and is failed even by
the hand-tuned rule controllers (event-level median longest run ~90 steps), so
it discriminated nothing. v3 publishes the full run-length distribution and a
run-limit sweep instead.

Legacy predicates (T_old, S_old, strict_old) are recomputed so the frozen
aggregates remain reproducible.

Usage:
    python3 scripts/audit_validity_endpoint_v3.py --out <dir> [--experiments E1,E2]
"""
import argparse
import csv
import json
import math
import os
from concurrent.futures import ProcessPoolExecutor

import numpy as np

TRACK_WIDTH = 40.0 / 6.0
RUN_LIMITS = [10, 25, 50, 100]
PROFILE_THRESHOLDS = [0.50, 0.60, 0.70, 0.80, 0.90, 0.95, 1.00]
CASE_PLAN = ("outputs/tits_dynamic_graph_expanded/e1_200_budget_matched/tables/"
             "expanded_benchmark_case_plan.pre_resume_20260915.csv")


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
    return cumulative, sum(lengths), lengths


def track_frames(points):
    """Unit tangent at each centre-line sample (central difference)."""
    n = len(points)
    tangent = np.zeros((n, 2))
    for i in range(n):
        vec = points[(i + 1) % n] - points[(i - 1) % n]
        norm = float(np.linalg.norm(vec))
        tangent[i] = vec / norm if norm > 0 else np.array([1.0, 0.0])
    return tangent


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
        # ``target_s`` and ``opp_s`` are each unwrapped from their own first
        # sample, so their difference is the true initial displacement plus an
        # unknown integer number of laps. The cars are placed well within half a
        # lap of each other, so the circular delta *is* the true displacement
        # and the integer offset is what has to be removed. Subtracting the
        # circular delta in the other order (the earlier form) added two laps of
        # error whenever a pair straddled the start line: in the sparse layout
        # the front row sits at tile ~2 while the rear row sits at tile ~274, so
        # every pass of a front-row car was measured as a ~2019 m gap that never
        # closed and was silently dropped.
        offset = (target_s[0] - opp_s[0]) - circular_delta(target_s[0], opp_s[0], lap)
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


def _offroad_stats(lat, limit):
    off = lat > limit
    return float(1.0 - off.mean()), float(off.mean()), int(longest_run(off))


def audit_event(trace, event, target, points, normal, tangent, cfg):
    hold = cfg["hold"]
    pre = cfg["window_pre"]
    start_index = int(event["start_index"])
    complete_index = int(event["complete_index"])
    stop_index = complete_index + hold
    man_start = max(0, complete_index - pre)
    if stop_index >= len(trace):
        return {"available": False, "reason": "post_pass_window_censored"}

    rows = trace[start_index:stop_index + 1]
    man_rows = trace[man_start:stop_index + 1]
    rel = event["rel"]
    margin = cfg["pass_margin"]

    contact_steps = {int(row["step"]) for row in rows
                     if any(target in c.get("agents", []) for c in row.get("contacts", []))}
    contact_free = not contact_steps
    physical_pass = rel[start_index] <= -margin and rel[complete_index] >= margin
    sustained_lead = physical_pass and min(rel[complete_index:stop_index + 1]) >= margin

    def lat_series(window):
        out = np.empty(len(window))
        for i, row in enumerate(window):
            index = min(max(int(row["track_index"][target]), 0), len(points) - 1)
            delta = np.asarray(row["positions"][target], float) - points[index]
            out[i] = abs(float(np.dot(delta, normal[index]))) / TRACK_WIDTH
        return out

    def lat_series_for(window, agent):
        out = np.empty(len(window))
        for i, row in enumerate(window):
            index = min(max(int(row["track_index"][agent]), 0), len(points) - 1)
            delta = np.asarray(row["positions"][agent], float) - points[index]
            out[i] = abs(float(np.dot(delta, normal[index]))) / TRACK_WIDTH
        return out

    def heading_series(window):
        out = np.empty(len(window))
        for i, row in enumerate(window):
            index = min(max(int(row["track_index"][target]), 0), len(points) - 1)
            # the recorder stores the Box2D hull angle, whose sprite forward axis is
            # (-sin, cos); the simulator's own cos(desired_angle - hull) reduces to the
            # same quantity, which we assert below via heading_cos_recomputed
            angle = float(row["hull_angles"][target])
            heading_vec = np.array([-math.sin(angle), math.cos(angle)])
            out[i] = abs(float(np.dot(heading_vec, tangent[index])))
        return out

    true_lat = lat_series(rows)
    man_lat = lat_series(man_rows)
    head_true = heading_series(rows)
    head_true_man = heading_series(man_rows)

    grass = np.array([1.0 if r["telemetry"]["on_grass"][target] else 0.0 for r in rows])
    backward = np.array([1.0 if r["telemetry"]["backward"][target] else 0.0 for r in rows])
    legacy = np.abs(np.array([float(r["telemetry"]["lateral_error"][target]) for r in rows]))
    head_legacy = np.array([float(r["telemetry"]["heading_cos"][target]) for r in rows])
    speed = np.array([float(r["speed"][target]) for r in rows])
    guard = np.array([1.0 if r.get("target_policy_debug", {}).get("hard_recovery") else 0.0
                      for r in rows])

    grass_series = np.array([1.0 if r["telemetry"]["on_grass"][target] else 0.0 for r in man_rows])
    limit = cfg["corridor_limit"]
    grass_agreement = float(np.mean((man_lat > limit) == (grass_series > 0.5)))
    in_man, off_man, run_man = _offroad_stats(man_lat, limit)
    in_full, off_full, run_full = _offroad_stats(true_lat, limit)

    hold_lat = man_lat[-hold:]
    hold_step = np.abs(np.diff(hold_lat)) if len(hold_lat) > 1 else np.zeros(1)
    hold_head = head_true_man[-hold:]
    step_lat = np.abs(np.diff(true_lat)) if len(true_lat) > 1 else np.zeros(1)

    T_v3 = bool(in_man >= cfg["in_corridor_min"])
    T_v2ref = bool(in_full >= cfg["in_corridor_min"] and run_full <= cfg["max_off_run"])
    S_v3 = bool(np.isfinite(speed[-hold:]).all()
                and speed[-hold:].min() >= cfg["min_speed"]
                and hold_step.max() <= cfg["lateral_step_bound"]
                and hold_head.min() >= cfg["heading_cos_min"]
                and backward[-hold:].max() == 0)
    T_old = bool(grass.max() == 0 and backward.max() == 0
                 and legacy.max() <= cfg["legacy_lateral_limit"]
                 and head_legacy.min() >= cfg["heading_cos_min"])
    legacy_hold_step = np.abs(np.diff(legacy[-hold:])) if hold > 1 else np.zeros(1)
    S_old = bool(np.isfinite(speed[-hold:]).all()
                 and speed[-hold:].min() >= cfg["min_speed"]
                 and legacy_hold_step.max() <= cfg["legacy_step_limit"]
                 and head_legacy.min() >= cfg["heading_cos_min"]
                 and backward[-hold:].max() == 0)

    E_pass = bool(physical_pass and sustained_lead and contact_free)
    # ``Q``: the opponent has to be *racing* when the manoeuvre starts. A
    # vehicle that has already left the surface is a stranded car, and closing
    # on it is not an overtake. Without this predicate an event can be earned by
    # driving past a car that is standing 20 m off the road.
    rival_lat_start = float(lat_series_for(trace[start_index:start_index + 1], event["opponent"])[0])
    rival_grass_start = bool(trace[start_index]["telemetry"]["on_grass"][event["opponent"]])
    rival_backward_start = bool(trace[start_index]["telemetry"]["backward"][event["opponent"]])
    rival_speed_start = float(trace[start_index]["speed"][event["opponent"]])
    # Thresholds are deliberately looser than the ego's own containment
    # criterion: the opponent only has to be *on the racing surface and moving*
    # when the manoeuvre starts. ``rival_lat_limit`` is 1.5 half-widths against
    # the ego's 1.0 so that a car brushing the edge of the road at the corner
    # entry still counts as racing; ``rival_min_speed`` of 4 m/s separates a
    # moving car from one that has left the surface and stopped.
    Q = bool(rival_lat_start <= cfg["rival_lat_limit"]
             and rival_speed_start >= cfg["rival_min_speed"]
             and not rival_backward_start)
    return {
        "available": True,
        "opponent": int(event["opponent"]),
        "start_step": int(trace[start_index]["step"]),
        "complete_step": int(trace[complete_index]["step"]),
        "event_steps": int(len(rows)),
        "maneuver_steps": int(len(man_rows)),
        "time_to_pass_steps": int(complete_index - start_index),
        "P": bool(physical_pass), "L": bool(sustained_lead), "C": bool(contact_free),
        "physical_pass": bool(physical_pass),
        "sustained_lead": bool(sustained_lead),
        "contact_free": bool(contact_free),
        "contact_count": int(len(contact_steps)),
        "T_v3": T_v3, "S_v3": S_v3,
        "E_pass": E_pass,
        "E_valid": bool(E_pass and T_v3),
        "E_full": bool(E_pass and T_v3 and S_v3),
        "Q": Q,
        "E_race": bool(E_pass and T_v3 and S_v3 and Q),
        "rival_lat_start": rival_lat_start,
        "rival_grass_start": rival_grass_start,
        "rival_backward_start": rival_backward_start,
        "rival_speed_start": rival_speed_start,
        "T_v2": T_v2ref,
        "T_old": T_old, "S_old": S_old,
        "strict_old": bool(contact_free and sustained_lead and T_old and S_old),
        "in_corridor": in_man,
        "in_corridor_man": in_man,
        "in_corridor_full": in_full,
        "frac_offroad": off_man,
        "frac_offroad_full": off_full,
        "longest_off_run": run_man,
        "longest_off_run_full": run_full,
        "mean_abs_lat": float(man_lat.mean()),
        "max_abs_lat": float(man_lat.max()),
        "lateral_rmse": float(np.sqrt(np.mean(man_lat ** 2))),
        "max_step_lat": float(step_lat.max()),
        "max_step_lat_hold": float(hold_step.max()),
        "grass_fraction": float(grass.mean()),
        "grass_agreement": grass_agreement,
        "backward_fraction": float(backward.mean()),
        "min_heading_cos_true": float(head_true_man.min()),
        "mean_heading_error": float(np.arccos(np.clip(head_true_man, -1.0, 1.0)).mean()),
        "min_heading_cos_legacy": float(head_legacy.min()),
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
    if not (os.path.exists(summary_path) and os.path.exists(trace_path)
            and os.path.exists(initial_path)):
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
        tangent = track_frames(points)
        cumulative, lap, spacing = track_geometry(points)
        target = int(summary.get("target_agent", num_agents - 1))
        events = detect_events(trace, target, cumulative, lap,
                               cfg["approach_distance"], cfg["pass_margin"])
        audited = [audit_event(trace, e, target, points, normal, tangent, cfg) for e in events]
        available = [x for x in audited if x.get("available")]
        row = {**base, "status": "ok", "target_agent": target,
               "event_count": len(events), "available_event_count": len(available),
               "post_pass_censored": bool(events) and not available,
               "episode_steps": len(trace),
               "telemetry_version": summary.get("telemetry_version", ""),
               "median_centreline_spacing_m": float(np.median(spacing)),
               "latency_ms": float(summary.get("compute_latency_ms", float("nan"))),
               "latency_p95_ms": float(summary.get("compute_latency_p95_ms", float("nan"))),
               "recovery_rate": float(summary.get("hard_recovery_rate", float("nan"))),
               "rank_gain": summary.get("rank_gain"),
               "target_progress": summary.get("target_progress"),
               "overtake_success_legacy": bool(summary.get("overtake_success"))}
        for key in ["P", "L", "C", "physical_pass", "sustained_lead", "contact_free",
                    "T_v3", "S_v3", "E_pass", "E_valid", "E_full", "Q", "E_race", "T_v2",
                    "T_old", "S_old", "strict_old"]:
            row[key] = bool(any(x.get(key, False) for x in available))
        for key in ["in_corridor", "in_corridor_man", "in_corridor_full", "frac_offroad",
                    "frac_offroad_full", "longest_off_run", "longest_off_run_full",
                    "mean_abs_lat", "max_abs_lat", "lateral_rmse", "max_step_lat",
                    "max_step_lat_hold", "grass_fraction", "backward_fraction",
                    "mean_heading_error", "min_heading_cos_true", "min_heading_cos_legacy",
                    "mean_speed", "min_speed_hold", "guard_fraction", "time_to_pass_steps"]:
            values = [x[key] for x in available if x.get(key) is not None]
            row[key] = float(np.mean(values)) if values else float("nan")
        for threshold in PROFILE_THRESHOLDS:
            tag = f"profile_{int(round(threshold * 100)):03d}"
            for window in ("man", "full"):
                ok = [x for x in available if x.get("E_pass")]
                key = "in_corridor_man" if window == "man" else "in_corridor_full"
                row[f"{tag}_{window}"] = bool(any(x[key] >= threshold - 1e-9 for x in ok))
        for run_limit in RUN_LIMITS:
            row[f"run_le_{run_limit}"] = bool(any(
                x.get("E_pass") and x["in_corridor_man"] >= cfg["in_corridor_min"] - 1e-9
                and x["longest_off_run"] <= run_limit for x in available))
        event_rows = [{**base, "target_agent": target, **x} for x in available]
        return row, event_rows
    except Exception as exc:  # noqa: BLE001
        return ({**base, "status": "error", "error": repr(exc)[:200]}, [])


def _write_csv(path, rows):
    if not rows:
        open(path, "w").close()
        return
    fields = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _mean(values):
    vals = [float(v) for v in values if v is not None and np.isfinite(float(v))]
    return float(np.mean(vals)) if vals else float("nan")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=os.getcwd())
    parser.add_argument("--case-plan", default=CASE_PLAN)
    parser.add_argument("--out", required=True)
    parser.add_argument("--experiments", default="E1,E2,E3,E6")
    parser.add_argument("--methods", default="")
    parser.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 8) - 4))
    parser.add_argument("--hold", type=int, default=50)
    parser.add_argument("--window-pre", type=int, default=25)
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
    parser.add_argument("--rival-lat-limit", type=float, default=1.5,
                        help="maximum opponent lateral offset (half-widths) at the approach sample "
                             "for the manoeuvre to count as overtaking a racing car")
    parser.add_argument("--rival-min-speed", type=float, default=4.0,
                        help="minimum opponent speed (m/s) at the approach sample")
    parser.add_argument("--max-cases", type=int, default=0)
    args = parser.parse_args()

    root = os.path.abspath(args.root)
    cfg = {"hold": args.hold, "window_pre": args.window_pre,
           "approach_distance": args.approach_distance, "pass_margin": args.pass_margin,
           "in_corridor_min": args.in_corridor_min, "corridor_limit": args.corridor_limit,
           "max_off_run": args.max_off_run, "lateral_step_bound": args.lateral_step_bound,
           "min_speed": args.min_speed, "heading_cos_min": args.heading_cos_min,
           "legacy_lateral_limit": args.legacy_lateral_limit,
           "legacy_step_limit": args.legacy_step_limit,
           "rival_lat_limit": args.rival_lat_limit,
           "rival_min_speed": args.rival_min_speed}

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
    print(json.dumps({"cases": len(selected), "jobs": len(jobs), "workers": args.workers}),
          flush=True)

    rows, event_rows = [], []
    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        for done, (row, events) in enumerate(executor.map(run_job, jobs, chunksize=4), 1):
            rows.append(row)
            event_rows.extend(events)
            if done % 500 == 0:
                print(f"  {done}/{len(jobs)}", flush=True)

    out_dir = os.path.abspath(args.out)
    os.makedirs(out_dir, exist_ok=True)
    _write_csv(os.path.join(out_dir, "case_level.csv"), rows)
    _write_csv(os.path.join(out_dir, "event_level.csv"), event_rows)

    endpoints = ["P", "L", "C", "T_v3", "S_v3", "E_pass", "E_valid", "E_full",
                 "Q", "E_race", "T_v2", "T_old", "S_old", "strict_old"]
    aggregates = []
    for experiment in sorted({r["experiment_id"] for r in rows}):
        for algorithm in sorted({r["algorithm"] for r in rows if r["experiment_id"] == experiment}):
            group = [r for r in rows
                     if r["experiment_id"] == experiment and r["algorithm"] == algorithm]
            n = len(group)
            for endpoint in endpoints:
                k = sum(bool(r.get(endpoint)) for r in group)
                low, high = wilson(k, n)
                aggregates.append({
                    "experiment_id": experiment, "algorithm": algorithm, "endpoint": endpoint,
                    "n": n, "count": k, "rate": k / n if n else float("nan"),
                    "wilson_low": low, "wilson_high": high,
                    "censored_cases": sum(bool(r.get("post_pass_censored")) for r in group),
                    "mean_recovery_rate": _mean([r.get("recovery_rate") for r in group]),
                    "mean_latency_ms": _mean([r.get("latency_ms") for r in group]),
                    "mean_in_corridor_man": _mean([r.get("in_corridor_man") for r in group]),
                    "mean_in_corridor_full": _mean([r.get("in_corridor_full") for r in group]),
                    "mean_longest_off_run": _mean([r.get("longest_off_run") for r in group]),
                    "mean_abs_lat": _mean([r.get("mean_abs_lat") for r in group]),
                    "max_abs_lat": _mean([r.get("max_abs_lat") for r in group]),
                    "mean_heading_error": _mean([r.get("mean_heading_error") for r in group]),
                    "mean_guard_fraction": _mean([r.get("guard_fraction") for r in group]),
                    "mean_time_to_pass_steps": _mean([r.get("time_to_pass_steps") for r in group]),
                })
    _write_csv(os.path.join(out_dir, "aggregate.csv"), aggregates)

    # conditional rates: P(E_full | E_pass), P(E_valid | E_pass)
    conditionals = []
    for experiment in sorted({r["experiment_id"] for r in rows}):
        for algorithm in sorted({r["algorithm"] for r in rows if r["experiment_id"] == experiment}):
            group = [r for r in rows
                     if r["experiment_id"] == experiment and r["algorithm"] == algorithm]
            passing = [r for r in group if r.get("E_pass")]
            entry = {"experiment_id": experiment, "algorithm": algorithm,
                     "n": len(group), "n_E_pass": len(passing)}
            entry["P_T_v3_given_E_pass"] = (_sum(passing, "T_v3") / len(passing)) if passing else float("nan")
            entry["P_S_v3_given_E_pass"] = (_sum(passing, "S_v3") / len(passing)) if passing else float("nan")
            entry["P_E_valid_given_E_pass"] = (_sum(passing, "E_valid") / len(passing)) if passing else float("nan")
            entry["P_E_full_given_E_pass"] = (_sum(passing, "E_full") / len(passing)) if passing else float("nan")
            conditionals.append(entry)
    _write_csv(os.path.join(out_dir, "conditionals.csv"), conditionals)

    profile = []
    for experiment in sorted({r["experiment_id"] for r in rows}):
        for algorithm in sorted({r["algorithm"] for r in rows if r["experiment_id"] == experiment}):
            group = [r for r in rows
                     if r["experiment_id"] == experiment and r["algorithm"] == algorithm]
            n = len(group)
            for threshold in PROFILE_THRESHOLDS:
                tag = f"profile_{int(round(threshold * 100)):03d}"
                for window in ("man", "full"):
                    k = sum(bool(r.get(f"{tag}_{window}")) for r in group)
                    low, high = wilson(k, n)
                    profile.append({"experiment_id": experiment, "algorithm": algorithm,
                                    "window": window, "in_corridor_min": threshold,
                                    "n": n, "count": k, "rate": k / n if n else float("nan"),
                                    "wilson_low": low, "wilson_high": high})
            for run_limit in RUN_LIMITS:
                k = sum(bool(r.get(f"run_le_{run_limit}")) for r in group)
                low, high = wilson(k, n)
                profile.append({"experiment_id": experiment, "algorithm": algorithm,
                                "window": "man_run_limit", "in_corridor_min": cfg["in_corridor_min"],
                                "max_off_run": run_limit, "n": n, "count": k,
                                "rate": k / n if n else float("nan"),
                                "wilson_low": low, "wilson_high": high})
    _write_csv(os.path.join(out_dir, "profile.csv"), profile)

    protocol = {
        "endpoints": {"E_pass": "P and L and C",
                      "E_valid": "P and L and C and T_v3",
                      "E_full": "P and L and C and T_v3 and S_v3"},
        "definitions": {
            "P": f"along-track lead crosses {cfg['pass_margin']} m after an approach inside "
                 f"[-{cfg['approach_distance']}, -{cfg['pass_margin']}] m",
            "L": f"lead stays >= {cfg['pass_margin']} m for {cfg['hold']} steps after completion",
            "C": "no recorder contact involving the target from event start through hold end",
            "T_v3": f"in-corridor fraction >= {cfg['in_corridor_min']} over the maneuver window "
                    f"[complete - {cfg['window_pre']}, complete + {cfg['hold']}] with "
                    f"|lat_true| <= {cfg['corridor_limit']}",
            "S_v3": f"hold window speed >= {cfg['min_speed']} m/s, true heading cos >= "
                    f"{cfg['heading_cos_min']}, no backward flag, per-step |delta lat_true| <= "
                    f"{cfg['lateral_step_bound']}",
        },
        "lat_true": "|(position - nearest centreline sample) . (cos beta, sin beta)| / TRACK_WIDTH, "
                    "beta = track[:,1] (the simulator's border-normal angle); |lat_true| <= 1 is "
                    "inside the road edge because TRACK_WIDTH is the road half-width",
        "heading_cos_true": "|dot((cos hull_angle, sin hull_angle), local centre-line tangent)|",
        "legacy_defects": {
            "lateral_error": "recorded value is the local-tangent projection, structurally "
                             "bounded by half the centre-line sample spacing",
            "heading_cos": "recorded value is cos(border_normal - hull_angle), i.e. the sine of "
                           "the true heading error",
            "window": "legacy corridor and stability clauses were evaluated over the whole event "
                      "window, including an approach phase that can last hundreds of steps",
        },
        "off_road_run_policy": "longest continuous off-road run is reported (distribution plus "
                               f"run-limit sweep at {RUN_LIMITS}) and is not a gate: it is failed "
                               "by the hand-tuned rule controllers as well, so it discriminates "
                               "nothing between methods",
        "threshold_calibration": "in_corridor_min and lateral_step_bound are fixed before "
                                 "evaluation from the rule-controller distribution",
        "denominator_policy": "all planned case-algorithm rows retained; censored and missing rows "
                              "count as failures",
        "config": cfg,
    }
    with open(os.path.join(out_dir, "protocol.json"), "w", encoding="utf-8") as fh:
        json.dump(protocol, fh, indent=2, sort_keys=True)
    print(json.dumps({"cases": len(rows), "events": len(event_rows)}), flush=True)


def _sum(rows, key):
    return sum(bool(r.get(key)) for r in rows)


if __name__ == "__main__":
    main()
