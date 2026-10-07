#!/usr/bin/env python
"""Controller-internal signals of the proposed arm, read from the main runs.

The endpoint audit says whether a pass happened. This script reads the *same*
traces and reports the quantities behind that outcome: how many vehicles the
exposure stage offers against how many the admission stage keeps, how often the
quality-guided rollout departs from the rule anchor, which score terms dominate
the selected candidate, how far the imagined rollout drifts from the simulator,
and how often the safety shield intervenes.

No component is removed from the controller here. Every number is measured
inside the runs that produced the headline results, so the analysis carries the
same seeds, tracks and budget as the main comparison.

Usage:
    python3 scripts/analyze_controller_signals.py \
        --root /tmp/main_all --case-plan /tmp/main_all_plan.csv \
        --out <dir> [--algorithms ours_dnq_dlc] [--hold 50] [--warmup 300]
"""

import argparse
import csv
import json
import math
import os
from pathlib import Path

import numpy as np

PLAYFIELD = 2000.0 / 6.0
SCALE_ORDER = ["M4_sparse", "M6_dense", "M8_scale", "M10_scale"]

QUALITY_TERMS = ["overtake", "lane", "grass", "close_gap", "learned_quality"]
SCORE_TERMS = ["reward", "progress", "liveness", "overtake", "learned_quality",
               "risk", "uncertainty", "imitation", "lane", "grass", "close_gap",
               "guard_violation", "elegance", "total", "speed_mean"]

TERM_SUFFIXES = ["mean"] + [f"{name}_mean" for name in SCORE_TERMS]
HORIZONS = [1, 2, 3, 4]


def read_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def write_csv(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def mean(values):
    values = [v for v in values if v is not None and math.isfinite(float(v))]
    return float(np.mean(values)) if values else float("nan")


def percentile(values, q):
    values = [v for v in values if v is not None and math.isfinite(float(v))]
    return float(np.percentile(values, q)) if values else float("nan")


def rate(flags):
    flags = [bool(f) for f in flags]
    return float(np.mean(flags)) if flags else float("nan")


def bootstrap_ci(values, rng, draws=2000, alpha=0.05):
    values = np.asarray([v for v in values if v is not None and math.isfinite(float(v))], float)
    if values.size == 0:
        return float("nan"), float("nan")
    if values.size == 1:
        return float(values[0]), float(values[0])
    picks = rng.integers(0, values.size, size=(draws, values.size))
    means = values[picks].mean(axis=1)
    return float(np.percentile(means, 100 * alpha / 2)), float(np.percentile(means, 100 * (1 - alpha / 2)))


def _same_action(left, right, atol=1e-6):
    if left is None or right is None:
        return False
    return bool(np.allclose(np.asarray(left, float), np.asarray(right, float), atol=atol, rtol=0.0))


def _admitted(debug):
    ids = debug.get("selected_neighbor_ids")
    if ids is None:
        return None
    return [int(item) for item in ids]


def _exposed(debug):
    ids = debug.get("exposed_neighbor_ids")
    if ids is None:
        return None
    return [int(item) for item in ids]


def _wm_errors(trace, index, debug):
    """Imagined-versus-realised rollout error, in metres and m/s.

    ``imagined_rollout`` holds the observation channels [x, y, speed] of every
    vehicle, already divided by PLAYFIELD and by the 50 m/s speed normaliser, so
    the comparison with the simulator only needs that rescaling.
    """
    rollout = debug.get("imagined_rollout")
    if not rollout:
        return None
    rollout = np.asarray(rollout, float)
    last = min(len(rollout) - 1, len(trace) - 1 - index)
    if last < 1:
        return None
    target = int(debug.get("target_agent", 0))
    out = {}
    for horizon in range(1, last + 1):
        realised_positions = np.asarray(trace[index + horizon]["positions"], float)
        predicted_positions = rollout[horizon, :, :2] * PLAYFIELD
        error = np.linalg.norm(predicted_positions - realised_positions, axis=1)
        out[f"wm_pos_err_ego_h{horizon}"] = float(error[target])
        out[f"wm_pos_err_fleet_h{horizon}"] = float(np.mean(error))
        realised_speed = float(trace[index + horizon]["speed"][target])
        out[f"wm_speed_err_ego_h{horizon}"] = float(
            abs(rollout[horizon, target, 2] * 50.0 - realised_speed))
    return out


def analyse_trace(trace, warmup, hold):
    """Per-step signals for one case, collapsed to case-level summary values."""
    debugged = []
    for index in range(len(trace)):
        debug = trace[index].get("target_policy_debug")
        if debug:
            debugged.append((index, debug))
    window = [(i, d) for i, d in debugged if warmup <= i <= len(trace) - 1 - hold] or debugged

    override, override_possible, margins = [], [], []
    candidate_counts, admitted_sizes, exposed_sizes, pruning = [], [], [], []
    # ``guard_trigger`` is only written on the steps that stay inside the pool
    # path; the two escalation branches return before writing it. Every one of
    # those branches does write ``hard_recovery``, so that flag is the reliable
    # indicator that the shield was active on a step.
    recovery, triggers, escalation, bypass, forced, infeasible = [], [], [], [], [], []
    admitted_sets, terms = [], []
    wm = {f"wm_pos_err_ego_h{h}": [] for h in HORIZONS}
    wm.update({f"wm_pos_err_fleet_h{h}": [] for h in HORIZONS})
    wm.update({f"wm_speed_err_ego_h{h}": [] for h in HORIZONS})

    for index, debug in window:
        selected = debug.get("selected_action")
        anchor = debug.get("anchor_action") if debug.get("use_rule_anchor") else None
        records = debug.get("candidate_scores") or []
        if anchor is not None and selected is not None and records:
            override_possible.append(True)
            override.append(not _same_action(selected, anchor))
            anchor_score = None
            for record in records:
                if _same_action(record.get("action"), anchor):
                    anchor_score = record.get("score")
                    break
            best = debug.get("best_score")
            if anchor_score is not None and best is not None:
                margins.append(float(best) - float(anchor_score))
            selected_terms = None
            for record in records:
                if _same_action(record.get("action"), selected):
                    selected_terms = record.get("terms")
                    break
            if selected_terms:
                terms.append({name: float(selected_terms.get(name, float("nan")))
                              for name in SCORE_TERMS})
        if debug.get("candidate_count") is not None:
            candidate_counts.append(float(debug["candidate_count"]))
        admitted = _admitted(debug)
        exposed = _exposed(debug)
        if admitted is not None:
            admitted_sizes.append(float(len(admitted)))
            admitted_sets.append(set(admitted))
        if exposed is not None:
            exposed_sizes.append(float(len(exposed)))
            if admitted is not None:
                pruning.append(len(admitted) < len(exposed))
        recovery.append(debug.get("hard_recovery"))
        if "guard_trigger" in debug:
            triggers.append(debug.get("guard_trigger"))
        escalation.append(debug.get("shield_escalated"))
        bypass.append(debug.get("planner_bypassed"))
        forced.append(debug.get("escalation_pool_feasible") is False)
        infeasible.append(float(debug.get("infeasible_streak") or 0.0) > 0.0)
        errors = _wm_errors(trace, index, debug)
        if errors:
            for name, value in errors.items():
                if name in wm:
                    wm[name].append(value)

    switches = sum(1 for a, b in zip(admitted_sets, admitted_sets[1:]) if a != b)
    residence, run = [], 1
    for previous, current in zip(admitted_sets, admitted_sets[1:]):
        if current == previous:
            run += 1
        else:
            residence.append(run)
            run = 1
    if admitted_sets:
        residence.append(run)

    row = {
        "steps": len(trace),
        "steps_analysed": len(window),
        "candidate_count_mean": mean(candidate_counts),
        "override_rate": rate(override),
        "anchor_steps": len(override_possible),
        "anchor_margin_mean": mean(margins),
        "anchor_margin_median": percentile(margins, 50),
        "anchor_margin_p90": percentile(margins, 90),
        "override_margin_mean": mean([m for m, o in zip(margins, override) if o]),
        "admitted_mean": mean(admitted_sizes),
        "admitted_p90": percentile(admitted_sizes, 90),
        "exposed_mean": mean(exposed_sizes),
        "admitted_of_exposed": mean([a / e for a, e in zip(admitted_sizes, exposed_sizes) if e]) if exposed_sizes else float("nan"),
        "pruning_rate": rate(pruning),
        "neighbor_churn_rate": switches / max(len(admitted_sets) - 1, 1) if admitted_sets else float("nan"),
        "neighbor_residence_mean": mean(residence),
        "neighbor_distinct_total": float(len(set().union(*admitted_sets))) if admitted_sets else float("nan"),
        "planner_active_rate": rate([count > 0 for count in candidate_counts]),
        "shield_active_rate": rate(recovery),
        "guard_trigger_rate": rate(triggers),
        "escalation_rate": rate(escalation),
        "forced_recovery_rate": rate(forced),
        "bypass_rate": rate(bypass),
        "infeasible_rate": rate(infeasible),
    }
    for horizon in HORIZONS:
        row[f"wm_pos_err_ego_h{horizon}"] = mean(wm[f"wm_pos_err_ego_h{horizon}"])
        row[f"wm_pos_err_fleet_h{horizon}"] = mean(wm[f"wm_pos_err_fleet_h{horizon}"])
        row[f"wm_speed_err_ego_h{horizon}"] = mean(wm[f"wm_speed_err_ego_h{horizon}"])
        row[f"wm_pos_err_ego_p90_h{horizon}"] = percentile(wm[f"wm_pos_err_ego_h{horizon}"], 90)
    row["wm_steps"] = len(wm["wm_pos_err_ego_h1"])
    for name in SCORE_TERMS:
        row[f"term_{name}_mean"] = mean([t.get(name) for t in terms])
    quality = [sum(t.get(name, 0.0) for name in QUALITY_TERMS) for t in terms]
    magnitude = [sum(abs(t.get(name, 0.0)) for name in SCORE_TERMS if name != "total") for t in terms]
    row["term_quality_share"] = mean([q / m for q, m in zip(quality, magnitude) if m])
    return row, admitted_sizes


def run_job(job):
    root, case_dir, algorithm, num_agents, seed, experiment_id, track_id, warmup, hold = job
    stem = f"{algorithm}_n{num_agents}_seed{seed}"
    trace_path = os.path.join(root, case_dir, "traces", f"{stem}.trace.json")
    base = {"experiment_id": experiment_id, "track_id": track_id, "algorithm": algorithm,
            "seed": seed, "num_agents": num_agents, "case_dir": case_dir}
    if not os.path.exists(trace_path):
        return {**base, "status": "missing"}, []
    try:
        trace = read_json(trace_path)
        row, sizes = analyse_trace(trace, warmup, hold)
        return {**base, "status": "ok", **row}, [(experiment_id, algorithm, num_agents, seed, int(s)) for s in sizes]
    except Exception as exc:  # noqa: BLE001
        return {**base, "status": "error", "error": repr(exc)[:200]}, []


def aggregate(case_rows):
    """Per-scale table: seeds are the unit of replication."""
    rng = np.random.default_rng(20260921)
    channels = [key for key in case_rows[0]
                if key not in {"experiment_id", "track_id", "algorithm", "seed", "num_agents",
                               "case_dir", "status", "error"}]
    out = []
    for scale in SCALE_ORDER:
        for algorithm in sorted({row["algorithm"] for row in case_rows}):
            subset = [row for row in case_rows
                      if row.get("status") == "ok" and row["experiment_id"] == scale
                      and row["algorithm"] == algorithm]
            if not subset:
                continue
            record = {"experiment_id": scale, "algorithm": algorithm, "n_cases": len(subset)}
            for channel in channels:
                values = [row.get(channel) for row in subset]
                values = [float(v) for v in values
                          if v is not None and not isinstance(v, str) and math.isfinite(float(v))]
                record[f"{channel}_mean"] = float(np.mean(values)) if values else float("nan")
                low, high = bootstrap_ci(values, rng)
                record[f"{channel}_ci_low"] = low
                record[f"{channel}_ci_high"] = high
                record[f"{channel}_n"] = len(values)
            out.append(record)
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", required=True)
    parser.add_argument("--case-plan", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--algorithms", default="ours_dnq_dlc")
    parser.add_argument("--warmup", type=int, default=300)
    parser.add_argument("--hold", type=int, default=50)
    parser.add_argument("--workers", type=int, default=16)
    args = parser.parse_args()

    wanted = {name.strip() for name in args.algorithms.split(",") if name.strip()}
    os.makedirs(args.out, exist_ok=True)
    with open(args.case_plan, encoding="utf-8", newline="") as handle:
        plan = list(csv.DictReader(handle))
    jobs = []
    for row in plan:
        algorithms = [item.strip() for item in str(row.get("algorithms", "")).split(",") if item.strip()]
        for algorithm in algorithms:
            if algorithm not in wanted:
                continue
            jobs.append((args.root, row["out_dir"], algorithm, int(row["num_agents"]),
                         int(row["seed"]), row.get("experiment_id", ""), row.get("track_id", ""),
                         args.warmup, args.hold))
    from concurrent.futures import ProcessPoolExecutor

    case_rows, size_rows = [], []
    with ProcessPoolExecutor(max_workers=max(1, args.workers)) as pool:
        for case_row, sizes in pool.map(run_job, jobs):
            case_rows.append(case_row)
            size_rows.extend(sizes)

    write_csv(os.path.join(args.out, "controller_signals_case_level.csv"), case_rows)
    aggregate_rows = aggregate(case_rows)
    write_csv(os.path.join(args.out, "controller_signals_by_scale.csv"), aggregate_rows)

    size_table = []
    for scale in SCALE_ORDER:
        for algorithm in sorted({row[1] for row in size_rows}):
            sizes = [size for experiment_id, alg, num_agents, seed, size in size_rows
                     if experiment_id == scale and alg == algorithm]
            if not sizes:
                continue
            total = len(sizes)
            counts = np.bincount(np.asarray(sizes, int))
            for size, count in enumerate(counts):
                if count == 0:
                    continue
                size_table.append({"experiment_id": scale, "algorithm": algorithm,
                                   "admitted_size": size, "steps": int(count),
                                   "fraction": count / total})
    write_csv(os.path.join(args.out, "controller_admitted_size_hist.csv"), size_table)

    with open(os.path.join(args.out, "protocol.json"), "w", encoding="utf-8") as handle:
        json.dump({
            "root": args.root,
            "case_plan": args.case_plan,
            "algorithms": sorted(wanted),
            "warmup_steps": args.warmup,
            "hold_steps": args.hold,
            "playfield_scale": PLAYFIELD,
            "wm_error_definition": "imagined_rollout channel [x, y, speed] rescaled by PLAYFIELD and 50 m/s, "
                                   "differenced against the realised trace at the same offset",
            "image": "learned world model, 4-step horizon, dump_rollouts enabled in the main comparison config",
            "note": "internal signals measured inside the main runs; no component is removed or retrained here",
        }, handle, ensure_ascii=False, indent=2)

    print(f"cases={len([r for r in case_rows if r.get('status') == 'ok'])} "
          f"rows={len(case_rows)} scales={len({r['experiment_id'] for r in case_rows})}")
    header = (f'{"scale":<11}{"method":<16}{"n":>3}{"exp":>6}{"adm":>6}{"prune":>7}{"ovr":>7}'
              f'{"marg":>7}{"guard":>7}{"wm1":>7}{"wm4":>7}{"qshare":>8}')
    print(header)
    for row in aggregate_rows:
        print(f'{row["experiment_id"]:<11}{row["algorithm"]:<16}{row["n_cases"]:>3}'
              f'{row["exposed_mean_mean"]:>6.2f}{row["admitted_mean_mean"]:>6.2f}'
              f'{row["pruning_rate_mean"]:>7.3f}{row["override_rate_mean"]:>7.3f}'
              f'{row["anchor_margin_mean_mean"]:>7.2f}{row["shield_active_rate_mean"]:>7.3f}'
              f'{row["wm_pos_err_ego_h1_mean"]:>7.2f}{row["wm_pos_err_ego_h4_mean"]:>7.2f}'
              f'{row["term_quality_share_mean"]:>8.3f}')


if __name__ == "__main__":
    main()
