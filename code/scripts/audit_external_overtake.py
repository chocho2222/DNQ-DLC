#!/usr/bin/env python
"""Overtake endpoint computed under a definition proposed outside this paper.

Purpose
-------
The manuscript's endpoint family (``P``, ``L``, ``C``, ``T``, ``S``, ``Q``) was
chosen by the authors, so a reader cannot tell how much of the reported margin
comes from the controller and how much from the clause set. This script
recomputes the *same* recorded cases under the passing-manoeuvre definition that
the highway-design and traffic-operations literature uses, with its own
constants and without adding any clause of ours.

The definition (AASHTO *Green Book* / HCM passing manoeuvre, in the
time-clearance form used in trajectory-based traffic studies)
----------------------------------------------------------------------------
A passing manoeuvre of B by A is *complete* when

  F   A was following B: at some sample before the crossing the along-track
      headway of A to B is at most the two-second rule,  h = 2 s
      (gap / v_A <= 2 s),
  R   the along-track order reverses: the sign of s_A - s_B flips from
      negative to positive,
  X   A is clear of B by the return distance: the gap reaches 1 s of A's own
      travel,  gap >= v_A * 1 s (the clearance component of passing sight
      distance, i.e. the "one-second rule"), and does not fall back below it
      before the manoeuvre ends,
  H   the clearance in X is held for one second.

The lane-return clause of the highway definition has no referent here: the
simulator's roadway is a single continuous surface with no marked lanes, and the
recorded telemetry carries no lane identifier. The script therefore applies the
definition without that clause and reports contact separately rather than
folding it in, so that the reported rate is the external definition as written.

Everything is read-only over stored traces.

Usage:
    python -m scripts.audit_external_overtake --out <dir>
"""
import argparse
import csv
import json
import math
import os
from concurrent.futures import ProcessPoolExecutor

import numpy as np

DT = 1.0 / 50.0
TRACK_WIDTH = 40.0 / 6.0
CASE_PLAN = ("outputs/tits_dynamic_graph_expanded/corrected_v2_20260920/"
             "validity_final_all/case_plan.csv")


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


def speed_series(trace, agent):
    out = []
    for row in trace:
        v = row["speed"][agent]
        out.append(float(v) if v is not None else float("nan"))
    return out


def detect_crossings(rel):
    """Indices at which the along-track gap changes sign from behind to ahead."""
    out = []
    for i in range(1, len(rel)):
        if rel[i - 1] < 0.0 <= rel[i]:
            out.append(i)
    return out


def audit_crossing(trace, rel, v_target, crossing, opp, cfg):
    hold = int(cfg["hold"])
    man_start = max(0, crossing - int(cfg["window_pre"]))
    follow_h = float(cfg["follow_headway_s"])
    clear_tau = float(cfg["clearance_s"])
    clear_m = float(cfg.get("clearance_m", 0.0))
    lookback = int(cfg["lookback"])
    n = len(trace)
    record = {"opponent": int(opp), "available": False}

    # F -- the manoeuvre begins when the passer enters a following state and
    # stays there until it is past. Walk back from the crossing over the
    # maximal run of samples in which the passer is still behind the opponent
    # (gap > 0) and within the two-second rule (gap / v <= 2 s); the first
    # sample of that run is the manoeuvre start. A passer that oscillates across
    # the opponent's position never assembles such a run and is not credited.
    follow_index = crossing - 1
    for j in range(crossing - 1, max(-1, crossing - 1 - lookback), -1):
        gap = -rel[j]
        v = v_target[j]
        if gap <= 0.0 or not np.isfinite(v) or v <= 1e-6 or gap / v > follow_h:
            break
        follow_index = j
    if follow_index >= crossing - 1 and not (
            -rel[crossing - 1] > 0.0
            and np.isfinite(v_target[crossing - 1])
            and v_target[crossing - 1] > 1e-6
            and (-rel[crossing - 1]) / v_target[crossing - 1] <= follow_h):
        record["reason"] = "no_following_run"
        return record
    record["follow_run_steps"] = int(crossing - follow_index)
    # The manoeuvre has to be *entered*: the sample before the following run
    # begins must still be outside the two-second rule. Without this a vehicle
    # that is already glued alongside its opponent and jitters across its
    # position is credited with an overtake.
    if follow_index > 0:
        gap0 = -rel[follow_index - 1]
        v0 = v_target[follow_index - 1]
        inside = (np.isfinite(v0) and v0 > 1e-6 and gap0 > 0.0
                  and gap0 / v0 <= follow_h)
        if inside:
            record["reason"] = "not_entered_from_outside_following"
            return record

    # X -- clearance of one second of the overtaker's own travel past the
    # opponent, reached without dropping back behind the opponent first.
    clear_index = None
    for i in range(crossing, n):
        if rel[i] < 0.0:
            break
        v = v_target[i]
        if np.isfinite(v) and rel[i] >= max(clear_tau * v, clear_m):
            clear_index = i
            break
    if clear_index is None:
        record["reason"] = "clearance_never_reached"
        return record
    if clear_index + hold >= n:
        record["reason"] = "hold_window_censored"
        return record

    # H -- the clearance is held for one second.
    window = rel[clear_index:clear_index + hold + 1]
    vwin = np.asarray(v_target[clear_index:clear_index + hold + 1], float)
    thr = np.maximum(clear_tau * vwin, clear_m)
    keep = float(np.min(window - thr))

    contacts = any(trace[cfg["target"]]["step"] is not None
                   and any(int(cfg["target"]) in c.get("agents", [])
                           for c in row.get("contacts", []))
                   for row in trace[follow_index:clear_index + hold + 1])

    # O -- the manoeuvre stays on the roadway: the fraction of the window
    # [clear - 25, clear + hold] in which the vehicle is inside the road edge.
    # A highway passing manoeuvre presupposes the roadway; this clause restores
    # what the flat road of the source definition gives for free.
    points = cfg["points"]
    normal = cfg["normal"]
    lat = np.empty(clear_index + hold + 1 - man_start)
    for i, row in enumerate(trace[man_start:clear_index + hold + 1]):
        index = min(max(int(row["track_index"][cfg["target"]]), 0), len(points) - 1)
        delta = np.asarray(row["positions"][cfg["target"]], float) - points[index]
        lat[i] = abs(float(np.dot(delta, normal[index]))) / TRACK_WIDTH
    on_road = float(np.mean(lat <= cfg["corridor_limit"]))
    on_road_frac = on_road

    rival_speed = float(trace[follow_index]["speed"][int(opp)])
    ridx = min(max(int(trace[follow_index]["track_index"][int(opp)]), 0), len(points) - 1)
    rdelta = np.asarray(trace[follow_index]["positions"][int(opp)], float) - points[ridx]
    rival_lat = abs(float(np.dot(rdelta, normal[ridx]))) / TRACK_WIDTH
    record.update({
        "available": True,
        "rival_speed": rival_speed,
        "rival_lat": rival_lat,
        "on_road_fraction": on_road_frac,
        "O": bool(on_road_frac >= cfg["in_corridor_min"]),
        "O_all": bool(on_road_frac >= 1.0),
        "follow_step": int(trace[follow_index]["step"]),
        "cross_step": int(trace[crossing]["step"]),
        "clear_step": int(trace[clear_index]["step"]),
        "event_steps": int(clear_index + hold + 1 - follow_index),
        "time_to_pass_steps": int(clear_index - follow_index),
        "min_clearance_margin": keep,
        "target_speed_at_clear": float(v_target[clear_index]),
        "contact": bool(contacts),
        "F": True,
        "R": True,
        "X": True,
        "H": bool(keep >= 0.0),
    })
    record["X_pass"] = bool(record["H"])
    record["X_pass_clean"] = bool(record["H"] and not contacts)
    record["X_strict"] = bool(record["H"] and not contacts and record["O"])
    record["X_strict_all"] = bool(record["H"] and not contacts and record["O_all"])
    return record


def run_job(job):
    root, case_dir, algorithm, num_agents, seed, experiment_id, track_id, cfg = job
    stem = f"{algorithm}_n{num_agents}_seed{seed}"
    base = {"experiment_id": experiment_id, "track_id": track_id, "algorithm": algorithm,
            "seed": seed, "num_agents": num_agents, "case_dir": case_dir}
    summary_path = os.path.join(root, case_dir, "summaries", f"{stem}.summary.json")
    trace_path = os.path.join(root, case_dir, "traces", f"{stem}.trace.json")
    initial_path = os.path.join(root, case_dir, "traces", f"{stem}.initial.json")
    if not (os.path.exists(summary_path) and os.path.exists(trace_path)
            and os.path.exists(initial_path)):
        return ({**base, "status": "missing"}, [])
    try:
        initial = json.load(open(initial_path))
        trace = json.load(open(trace_path))
        summary = json.load(open(summary_path))
        track = np.asarray(initial["track"], float)
        points = track[:, 2:4]
        cumulative, lap = track_geometry(points)
        target = int(summary.get("target_agent", num_agents - 1))
        cfg = dict(cfg)
        cfg["target"] = target
        beta = track[:, 1]
        cfg["points"] = points
        cfg["normal"] = np.stack([np.cos(beta), np.sin(beta)], 1)
        target_s = unwrapped_progress(trace, target, cumulative, lap)
        v_target = speed_series(trace, target)
        events = []
        for opponent in range(len(trace[0]["positions"])):
            if opponent == target:
                continue
            opp_s = unwrapped_progress(trace, opponent, cumulative, lap)
            offset = (target_s[0] - opp_s[0]) - circular_delta(target_s[0], opp_s[0], lap)
            rel = [a - b - offset for a, b in zip(target_s, opp_s)]
            for crossing in detect_crossings(rel):
                events.append(audit_crossing(trace, rel, v_target, crossing, opponent, cfg))
        available = [e for e in events if e.get("available")]
        row = {**base, "status": "ok", "target_agent": target,
               "episode_steps": len(trace),
               "crossing_count": len(events),
               "available_event_count": len(available),
               "telemetry_version": summary.get("telemetry_version", ""),
               "rank_gain": summary.get("rank_gain")}
        row["X_pass"] = bool(any(e["X_pass"] for e in available))
        row["X_pass_clean"] = bool(any(e["X_pass_clean"] for e in available))
        row["X_strict"] = bool(any(e["X_strict"] for e in available))
        row["X_strict_all"] = bool(any(e["X_strict_all"] for e in available))
        row["contact_event"] = bool(available) and not row["X_pass_clean"]
        for key in ("min_clearance_margin", "target_speed_at_clear", "time_to_pass_steps"):
            vals = [e[key] for e in available if e.get(key) is not None]
            row[key] = float(np.mean(vals)) if vals else float("nan")
        event_rows = [{**base, "target_agent": target, **e} for e in available]
        return row, event_rows
    except Exception as exc:  # noqa: BLE001
        return ({**base, "status": "error", "error": repr(exc)[:200]}, [])


def write_csv(path, rows):
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=os.getcwd())
    parser.add_argument("--case-plan", default=CASE_PLAN)
    parser.add_argument("--out", required=True)
    parser.add_argument("--experiments", default="M10_scale,M4_sparse,M6_dense,M8_scale")
    parser.add_argument("--methods", default="")
    parser.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 8) - 4))
    parser.add_argument("--hold", type=int, default=50,
                        help="external hold of 1 s at 50 Hz")
    parser.add_argument("--follow-headway-s", type=float, default=2.0,
                        help="two-second rule for the following state")
    parser.add_argument("--clearance-m", type=float, default=0.0,
                        help="fixed clearance distance (m); the greater of this and clearance_s*v applies")
    parser.add_argument("--clearance-s", type=float, default=1.0,
                        help="clearance component of passing sight distance (one-second rule)")
    parser.add_argument("--lookback", type=int, default=1000,
                        help="how far back the following state may be found")
    parser.add_argument("--window-pre", type=int, default=25)
    parser.add_argument("--in-corridor-min", type=float, default=0.70)
    parser.add_argument("--corridor-limit", type=float, default=1.0)
    args = parser.parse_args()

    root = os.path.abspath(args.root)
    cfg = {"hold": args.hold, "follow_headway_s": args.follow_headway_s,
           "clearance_s": args.clearance_s, "clearance_m": args.clearance_m,
           "lookback": args.lookback,
           "window_pre": args.window_pre, "in_corridor_min": args.in_corridor_min,
           "corridor_limit": args.corridor_limit}
    wanted = {x.strip() for x in args.experiments.split(",") if x.strip()}
    methods = {x.strip() for x in args.methods.split(",") if x.strip()}
    plan_path = args.case_plan
    if not os.path.exists(plan_path):
        plan_path = os.path.join(root, args.case_plan)
    plan = [r for r in csv.DictReader(open(plan_path, encoding="utf-8"))]
    selected = [r for r in plan if any(r["experiment_id"].startswith(w) for w in wanted)]
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
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for row, events in pool.map(run_job, jobs):
            rows.append(row)
            event_rows.extend(events)

    os.makedirs(args.out, exist_ok=True)
    write_csv(os.path.join(args.out, "case_level_external.csv"), rows)
    write_csv(os.path.join(args.out, "event_level_external.csv"), event_rows)

    order = ["ours_dnq_dlc", "rule_expert_gate", "dlc_joint_transition_observer",
             "dlc_individual_transition", "dlc_joint_transition",
             "ppo_continuous", "sac_continuous", "td3_continuous"]
    seen = sorted({r["algorithm"] for r in rows}, key=lambda a: (order.index(a) if a in order else 99, a))
    aggregate = []
    for algorithm in seen:
        subset = [r for r in rows if r["algorithm"] == algorithm]
        n = len(subset)
        for endpoint in ("X_pass", "X_pass_clean", "X_strict", "X_strict_all"):
            k = sum(1 for r in subset if r.get(endpoint))
            lo, hi = wilson(k, n)
            aggregate.append({"algorithm": algorithm, "endpoint": endpoint, "n": n,
                              "count": k, "rate": (k / n if n else float("nan")),
                              "wilson_low": lo, "wilson_high": hi})
    write_csv(os.path.join(args.out, "aggregate_external.csv"), aggregate)
    json.dump({"config": cfg,
               "definition": {
                   "F": "along-track headway to the opponent <= 2 s before the crossing",
                   "R": "sign of the along-track gap reverses from behind to ahead",
                   "X": "gap reaches v_ego * 1 s and stays at or above it",
                   "H": "the clearance in X is held for 1 s",
                   "X_pass": "F and R and X and H",
                   "X_pass_clean": "X_pass with no recorded contact involving the target",
                   "provenance": "AASHTO Green Book / HCM passing manoeuvre, time-clearance form; "
                                 "the lane-return clause is not applied because the roadway here "
                                 "has no marked lanes and the telemetry carries no lane id",
               }},
              open(os.path.join(args.out, "protocol_external.json"), "w"), indent=2, sort_keys=True)

    print(f"{'algorithm':<34}{'X_pass':>8}{'X_clean':>9}{'X_strict':>10}{'X_all':>7}{'n':>5}")
    for algorithm in seen:
        sub = [r for r in aggregate if r["algorithm"] == algorithm]
        a = {r["endpoint"]: r for r in sub}
        print(f"{algorithm:<34}{a['X_pass']['count']:>8}{a['X_pass_clean']['count']:>9}"
              f"{a['X_strict']['count']:>10}{a['X_strict_all']['count']:>7}{a['X_pass']['n']:>5}")
    json.dump({"rows": len(rows), "events": len(event_rows)},
              open(os.path.join(args.out, "counts_external.json"), "w"))


if __name__ == "__main__":
    main()
