#!/usr/bin/env python
"""Audit strict overtaking endpoints directly from the expanded benchmark traces.

The audit is post-hoc and never modifies source traces or summaries. Every case in
the frozen case plan remains in the denominator; missing summaries/traces and
post-pass censoring are reported explicitly.
"""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

def wilson(k, n, z=1.959963984540054):
    if n == 0:
        return None, None
    p = k / n
    den = 1 + z * z / n
    cen = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return cen - half, cen + half


def resolve_path(root, value):
    p = Path(value)
    return p if p.is_absolute() else root / p


def circular_delta(current, previous, period):
    delta = float(current) - float(previous)
    return (delta + period / 2.0) % period - period / 2.0


def track_arclength(track):
    xy = [(float(row[2]), float(row[3])) for row in track]
    lengths = [math.hypot(xy[(i + 1) % len(xy)][0] - xy[i][0],
                          xy[(i + 1) % len(xy)][1] - xy[i][1]) for i in range(len(xy))]
    cumulative = [0.0]
    for length in lengths[:-1]:
        cumulative.append(cumulative[-1] + length)
    return xy, lengths, cumulative, sum(lengths)


def unwrapped_progress(trace, agent, geometry):
    lap_length = geometry[-1]
    cumulative = geometry[2]
    # `track_index` is already the simulator's nearest center-line index. Using
    # its cumulative arc length avoids an expensive per-step geometric search.
    wrapped = [float(cumulative[int(row["track_index"][agent])]) for row in trace]
    out = [wrapped[0]]
    for previous, current in zip(wrapped, wrapped[1:]):
        out.append(out[-1] + circular_delta(current, previous, lap_length))
    return out


def detect_events(trace, target, geometry, approach_distance, pass_margin):
    target_s = unwrapped_progress(trace, target, geometry)
    events = []
    for opponent in range(len(trace[0]["positions"])):
        if opponent == target:
            continue
        opponent_s = unwrapped_progress(trace, opponent, geometry)
        lap_length = geometry[-1]
        offset = circular_delta(target_s[0], opponent_s[0], lap_length) - (target_s[0] - opponent_s[0])
        rel = [a - b - offset for a, b in zip(target_s, opponent_s)]
        start = None
        for idx, gap in enumerate(rel):
            if start is None and -approach_distance <= gap <= -pass_margin:
                start = idx
            elif start is not None and gap >= pass_margin:
                events.append({"opponent": opponent, "start_index": start,
                               "complete_index": idx, "relative_progress": rel})
                start = None
            elif start is not None and gap < -approach_distance:
                start = None
    return events


def strict_event(trace, event, target, hold, pass_margin, lateral_limit,
                 heading_cos_min, lateral_step_limit, minimum_speed):
    start_index = int(event["start_index"])
    complete_index = int(event["complete_index"])
    stop_index = complete_index + hold
    if stop_index >= len(trace):
        return {"available": False, "reason": "post_pass_window_censored"}
    rows = trace[start_index : stop_index + 1]
    opponent = int(event["opponent"])
    contact_steps = {
        int(row["step"])
        for row in rows
        if any(target in c.get("agents", []) for c in row.get("contacts", []))
    }
    contact_free = not contact_steps
    relative_progress = event["relative_progress"]
    physical_pass = relative_progress[start_index] <= -pass_margin and relative_progress[complete_index] >= pass_margin
    sustained_lead = physical_pass and min(relative_progress[complete_index : stop_index + 1]) >= pass_margin
    grass = [bool(row["telemetry"]["on_grass"][target]) for row in rows]
    backward = [bool(row["telemetry"]["backward"][target]) for row in rows]
    lateral = [abs(float(row["telemetry"]["lateral_error"][target])) for row in rows]
    heading = [float(row["telemetry"]["heading_cos"][target]) for row in rows]
    speed = [float(row["speed"][target]) for row in rows]
    on_track = (
        not any(grass)
        and not any(backward)
        and max(lateral, default=float("inf")) <= lateral_limit
        and min(heading, default=-1.0) >= heading_cos_min
    )
    hold_lateral = lateral[-hold:]
    post_pass_stable = (
        all(math.isfinite(v) for v in speed[-hold:] + hold_lateral + heading[-hold:])
        and min(speed[-hold:], default=-float("inf")) >= minimum_speed
        and max((abs(b - a) for a, b in zip(hold_lateral, hold_lateral[1:])), default=0.0) <= lateral_step_limit
        and min(heading[-hold:], default=-1.0) >= heading_cos_min
        and not any(backward[-hold:])
    )
    return {
        "available": True,
        "contact_free": contact_free,
        "physical_pass": physical_pass,
        "sustained_lead": sustained_lead,
        "on_track": on_track,
        "post_pass_stable": post_pass_stable,
        "strict_completion": bool(contact_free and sustained_lead and on_track and post_pass_stable),
        "contact_steps": sorted(contact_steps),
        "max_abs_lateral": max(lateral, default=float("nan")),
        "min_heading_cos": min(heading, default=float("nan")),
        "grass_fraction": sum(grass) / len(grass) if grass else float("nan"),
        "opponent": opponent,
        "start_step": int(trace[start_index]["step"]),
        "complete_step": int(trace[complete_index]["step"]),
        "relative_progress_start_m": relative_progress[start_index],
        "relative_progress_complete_m": relative_progress[complete_index],
        "relative_progress_hold_min_m": min(relative_progress[complete_index : stop_index + 1]),
        "hold_steps": hold,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--matrix", default="outputs/tits_dynamic_graph_expanded/e1_200_budget_matched")
    ap.add_argument("--out", default="outputs/tits_dynamic_graph_expanded/e1_200_strict_endpoint_audit_20260915")
    ap.add_argument("--case-plan", default="",
                    help="Optional frozen case-plan CSV. Relative paths are resolved from --root.")
    ap.add_argument("--hold", type=int, default=50)
    ap.add_argument("--approach-distance", type=float, default=20.0)
    ap.add_argument("--pass-margin", type=float, default=4.0)
    ap.add_argument("--lateral-limit", type=float, default=0.45)
    ap.add_argument("--heading-cos-min", type=float, default=0.82)
    ap.add_argument("--lateral-step-limit", type=float, default=0.25)
    ap.add_argument("--minimum-speed", type=float, default=1.0)
    ap.add_argument("--experiments", default="",
                    help="Comma-separated experiment IDs to audit; empty audits the full frozen plan.")
    args = ap.parse_args()
    root = Path(args.root).resolve()
    matrix = resolve_path(root, args.matrix)
    out = resolve_path(root, args.out)
    out.mkdir(parents=True, exist_ok=True)
    if args.case_plan:
        plan_path = resolve_path(root, args.case_plan)
    else:
        plan_path = matrix / "tables/expanded_benchmark_case_plan.pre_resume_20260915.csv"
        if not plan_path.exists():
            plan_path = matrix / "tables/expanded_benchmark_case_plan.csv"
    plan = list(csv.DictReader(plan_path.open(encoding="utf-8")))
    wanted_experiments = {x.strip() for x in args.experiments.split(",") if x.strip()}
    if wanted_experiments:
        plan = [case for case in plan if case.get("experiment_id") in wanted_experiments]
    records = []
    for case in plan:
        case_dir = resolve_path(root, case["out_dir"])
        algs = [a.strip() for a in case["algorithms"].split(",") if a.strip()]
        n = int(case["num_agents"])
        seed = int(case["seed"])
        for alg in algs:
            stem = f"{alg}_n{n}_seed{seed}"
            summary_path = case_dir / "summaries" / f"{stem}.summary.json"
            trace_path = case_dir / "traces" / f"{stem}.trace.json"
            initial_path = case_dir / "traces" / f"{stem}.initial.json"
            base = {"case_index": int(case.get("case_index", len(records))),
                    "experiment_id": case.get("experiment_id", "unspecified"),
                    "track_id": case.get("track_id", Path(case.get("track_path", "procedural") or "procedural").stem),
                    "num_agents": n, "seed": seed,
                    "algorithm": alg, "case_dir": str(case_dir)}
            if not summary_path.exists() or not trace_path.exists() or not initial_path.exists():
                records.append({**base, "status": "missing_trace_or_summary", "strict_completion": False})
                continue
            try:
                summary = json.loads(summary_path.read_text(encoding="utf-8"))
                trace = json.loads(trace_path.read_text(encoding="utf-8"))
                initial = json.loads(initial_path.read_text(encoding="utf-8"))
                target = int(summary.get("target_agent", n - 1))
                geometry = track_arclength(initial["track"])
                events = detect_events(trace, target, geometry, args.approach_distance, args.pass_margin)
                audited = [strict_event(trace, e, target, args.hold, args.pass_margin,
                                        args.lateral_limit, args.heading_cos_min,
                                        args.lateral_step_limit, args.minimum_speed)
                            for e in events]
                available = [x for x in audited if x.get("available")]
                strict = any(x.get("strict_completion", False) for x in available)
                records.append({**base, "status": "ok", "event_count": len(events),
                                "available_event_count": len(available),
                                "post_pass_censored": bool(events) and not bool(available),
                                "strict_completion": strict,
                                "event_contact_free": any(x.get("contact_free", False) for x in available),
                                "physical_pass": any(x.get("physical_pass", False) for x in available),
                                "event_on_track": any(x.get("on_track", False) for x in available),
                                "sustained_lead": any(x.get("sustained_lead", False) for x in available),
                                "post_pass_stable": any(x.get("post_pass_stable", False) for x in available),
                                "target_final_rank": summary.get("target_final_rank"),
                                "rank_gain": summary.get("rank_gain"),
                                "target_progress": summary.get("target_progress"),
                                "summary_path": str(summary_path), "trace_path": str(trace_path)})
            except Exception as exc:
                records.append({**base, "status": "parse_error", "error": repr(exc), "strict_completion": False})
    fields = sorted({k for row in records for k in row})
    with (out / "episode_level.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields); writer.writeheader(); writer.writerows(records)
    aggregates = []
    for alg in sorted({r["algorithm"] for r in records}):
        rr = [r for r in records if r["algorithm"] == alg]
        for endpoint in ["strict_completion", "physical_pass", "event_contact_free", "event_on_track",
                         "sustained_lead", "post_pass_stable"]:
            k = sum(bool(r.get(endpoint, False)) for r in rr); n = len(rr); lo, hi = wilson(k, n)
            aggregates.append({"algorithm": alg, "endpoint": endpoint, "n": n, "count": k,
                               "rate": k / n if n else float("nan"), "wilson_low": lo,
                               "wilson_high": hi, "ok_rows": sum(r.get("status") == "ok" for r in rr),
                               "censored_rows": sum(bool(r.get("post_pass_censored")) for r in rr)})
    with (out / "aggregate.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=aggregates[0].keys()); writer.writeheader(); writer.writerows(aggregates)
    manifest = {"source_case_plan": str(plan_path), "source_sha256": hashlib.sha256(plan_path.read_bytes()).hexdigest(),
                "records": len(records), "cases": len(plan), "hold_steps": args.hold,
                "approach_distance_m": args.approach_distance, "pass_margin_m": args.pass_margin,
                "lateral_limit": args.lateral_limit, "heading_cos_min": args.heading_cos_min,
                "lateral_step_limit": args.lateral_step_limit, "minimum_speed": args.minimum_speed,
                "denominator_policy": "all planned case-algorithm rows retained; missing and censored rows are failures",
                "note": "post-hoc strict endpoint audit from stored traces; no source artifacts modified"}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"cases": len(plan), "episode_rows": len(records), "out": str(out)}, indent=2))


if __name__ == "__main__":
    main()
