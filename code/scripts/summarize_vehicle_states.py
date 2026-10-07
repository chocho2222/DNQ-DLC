#!/usr/bin/env python
"""State-level view of the main comparison.

The main comparison is scored at the endpoint level elsewhere. This script uses
the per-case vehicle-state records produced by analyze_vehicle_states.py to show
*how* each method drives: how much of the lap it spends out of the corridor, how
fast it is, whether it reaches a passing position at all, how much the safety
shield intervenes and how the admitted neighbour set behaves.

Rows are never pooled across track scales: a case is the unit of analysis and
per-scale tables keep the vehicle counts separate. Differences against a
reference method are paired by (scale, track, seed).

Usage:
    python3 scripts/summarize_vehicle_states.py \
        --case-level <dir>/vehicle_case_level.csv \
        --event-level <dir>/vehicle_event_level.csv \
        --out <dir> [--reference ours_dnq_dlc]
"""

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

CASE_CHANNELS = [
    "race_speed_mean",
    "race_speed_p10",
    "race_lat_mean",
    "race_lat_p90",
    "target_lat_mean",
    "target_lat_p90",
    "target_lat_max",
    "target_grass_fraction",
    "target_contact_steps",
    "episode_min_pair_gap",
    "guard_fraction_episode",
    "best_lead_any",
    "lead_margin_to_pass_gate",
    "neighbor_admitted_mean",
    "neighbor_churn_rate",
    "neighbor_distinct_total",
    "neighbor_residence_mean",
]

EVENT_CHANNELS = [
    "approach_steps",
    "alongside_steps",
    "time_to_pass_steps",
    "speed_advantage_alongside",
    "rival_speed_alongside",
    "peak_abs_lat_maneuver",
    "mean_abs_lat_maneuver",
    "min_gap_rival_maneuver",
    "min_gap_third_party_maneuver",
    "guard_fraction_window",
    "rival_admitted_fraction",
]

SCALE_LABEL = {"M4_sparse": "M4", "M6_dense": "M6", "M8_scale": "M8", "M10_scale": "M10"}
SCALE_ORDER = ["M4_sparse", "M6_dense", "M8_scale", "M10_scale"]


def load(path):
    with Path(path).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def as_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def finite(values):
    out = []
    for value in values:
        number = as_float(value)
        if np.isfinite(number):
            out.append(number)
    return out


def bootstrap_ci(values, draws=20000, seed=13):
    values = np.asarray(finite(values), dtype=float)
    if values.size == 0:
        return float("nan"), float("nan")
    if values.size == 1:
        return float(values[0]), float(values[0])
    rng = np.random.default_rng(seed)
    picks = rng.integers(0, values.size, size=(draws, values.size))
    means = values[picks].mean(axis=1)
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def write(name, out_dir, records):
    if not records:
        return None
    path = Path(out_dir) / name
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    return str(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--case-level", required=True)
    parser.add_argument("--event-level", default="")
    parser.add_argument("--out", required=True)
    parser.add_argument("--reference", default="ours_dnq_dlc")
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    cases = [row for row in load(args.case_level) if row.get("status") == "ok"]
    by_scale = defaultdict(list)
    for row in cases:
        by_scale[row["experiment_id"]].append(row)
    methods = sorted({row["algorithm"] for row in cases})

    level = []
    for scale in SCALE_ORDER:
        group = by_scale.get(scale, [])
        if not group:
            continue
        for method in methods:
            subset = [row for row in group if row["algorithm"] == method]
            if not subset:
                continue
            record = {"experiment_id": scale, "algorithm": method, "n_cases": len(subset)}
            for channel in CASE_CHANNELS:
                values = [row.get(channel) for row in subset]
                good = finite(values)
                record[f"{channel}_mean"] = float(np.mean(good)) if good else float("nan")
                # Cases with no event carry no channel value; report availability too.
                record[f"{channel}_n"] = len(good)
            level.append(record)

    paired = []
    index = {(row["experiment_id"], row["track_id"], str(row["seed"]), row["algorithm"]): row
             for row in cases}
    keys = sorted({(row["experiment_id"], row["track_id"], str(row["seed"])) for row in cases})
    for scale in SCALE_ORDER:
        for method in methods:
            if method == args.reference:
                continue
            deltas = {channel: [] for channel in CASE_CHANNELS}
            n_paired = 0
            for key in keys:
                if key[0] != scale:
                    continue
                other = index.get((*key, method))
                reference = index.get((*key, args.reference))
                if other is None or reference is None:
                    continue
                n_paired += 1
                for channel in CASE_CHANNELS:
                    a, b = as_float(other.get(channel)), as_float(reference.get(channel))
                    if np.isfinite(a) and np.isfinite(b):
                        deltas[channel].append(a - b)
            if not n_paired:
                continue
            record = {"experiment_id": scale, "algorithm": method,
                      "reference": args.reference, "n_paired": n_paired}
            for channel in CASE_CHANNELS:
                values = deltas[channel]
                low, high = bootstrap_ci(values)
                record[f"d_{channel}_mean"] = float(np.mean(values)) if values else float("nan")
                record[f"d_{channel}_ci_low"] = low
                record[f"d_{channel}_ci_high"] = high
                record[f"d_{channel}_crosses_zero"] = (
                    bool(low <= 0.0 <= high) if values else None)
            paired.append(record)

    events = []
    if args.event_level:
        # Event rows carry `available` rather than `status`; a row is usable when
        # the detector reported an event for it.
        event_rows = [row for row in load(args.event_level)
                      if str(row.get("available", "True")).lower() != "false"
                      and row.get("status", "ok") == "ok"]
        by_scale_events = defaultdict(list)
        for row in event_rows:
            by_scale_events[row["experiment_id"]].append(row)
        for scale in SCALE_ORDER:
            group = by_scale_events.get(scale, [])
            if not group:
                continue
            for method in methods:
                subset = [row for row in group if row["algorithm"] == method]
                record = {"experiment_id": scale, "algorithm": method, "n_events": len(subset)}
                for channel in EVENT_CHANNELS:
                    values = finite([row.get(channel) for row in subset])
                    record[f"{channel}_mean"] = float(np.mean(values)) if values else float("nan")
                    record[f"{channel}_median"] = (
                        float(np.median(values)) if values else float("nan"))
                    record[f"{channel}_n"] = len(values)
                events.append(record)

    tables = {"by_scale": write("vehicle_state_by_scale.csv", out_dir, level),
              "paired_vs_reference": write("vehicle_state_paired.csv", out_dir, paired),
              "events_by_scale": write("vehicle_event_by_scale.csv", out_dir, events)}
    (out_dir / "summary.json").write_text(
        json.dumps({"case_level": str(args.case_level), "event_level": str(args.event_level),
                    "reference": args.reference, "scales": SCALE_ORDER,
                    "methods": methods, "n_cases": len(cases),
                    "n_events": sum(int(record["n_events"]) for record in events),
                    "tables": tables}, indent=2),
        encoding="utf-8")

    header = (f"{'scale':<11}{'method':<32}{'n':>3}{'speed':>7}{'lat_m':>7}{'lat_p90':>8}"
              f"{'grass':>7}{'guard':>7}{'bestlead':>9}{'min_gap':>8}{'adm':>6}"
              f"{'churn':>7}{'dist':>6}{'resid':>7}")
    print(header)
    for record in level:
        def value(name):
            number = as_float(record.get(name))
            return f"{number:.3f}" if np.isfinite(number) else "  -  "
        print(f"{record['experiment_id']:<11}{record['algorithm']:<32}{record['n_cases']:>3}"
              f"{value('race_speed_mean_mean'):>7}{value('race_lat_mean_mean'):>7}"
              f"{value('race_lat_p90_mean'):>8}{value('target_grass_fraction_mean'):>7}"
              f"{value('guard_fraction_episode_mean'):>7}{value('best_lead_any_mean'):>9}"
              f"{value('episode_min_pair_gap_mean'):>8}{value('neighbor_admitted_mean_mean'):>6}"
              f"{value('neighbor_churn_rate_mean'):>7}"
              f"{value('neighbor_distinct_total_mean'):>6}"
              f"{value('neighbor_residence_mean_mean'):>7}")
    print()
    print(f"paired differences vs {args.reference} (positive favours the other method)")
    print(f"{'scale':<11}{'method':<32}{'n':>3}{'d_lat_p90':>11}{'d_grass':>9}{'d_guard':>9}"
          f"{'d_bestlead':>12}{'d_mingap':>9}{'d_churn':>9}")
    for record in paired:
        def delta(name):
            number = as_float(record.get(name))
            mark = " " if record.get(f"{name}_crosses_zero") else "*"
            return f"{number:.3f}{mark}" if np.isfinite(number) else "   -  "
        print(f"{record['experiment_id']:<11}{record['algorithm']:<32}{record['n_paired']:>3}"
              f"{delta('d_race_lat_p90_mean'):>11}{delta('d_target_grass_fraction_mean'):>9}"
              f"{delta('d_guard_fraction_episode_mean'):>9}{delta('d_best_lead_any_mean'):>12}"
              f"{delta('d_episode_min_pair_gap_mean'):>9}"
              f"{delta('d_neighbor_churn_rate_mean'):>9}")
    if events:
        print()
        print(f"{'scale':<11}{'method':<32}{'nev':>4}{'appr':>7}{'along':>7}{'ttp':>7}"
              f"{'adv':>7}{'peaklat':>8}{'mingapR':>9}{'mingap3':>9}{'guardW':>8}{'admR':>7}")
        for record in events:
            def value(name):
                number = as_float(record.get(name))
                return f"{number:.2f}" if np.isfinite(number) else "  -  "
            print(f"{record['experiment_id']:<11}{record['algorithm']:<32}{record['n_events']:>4}"
                  f"{value('approach_steps_median'):>7}{value('alongside_steps_median'):>7}"
                  f"{value('time_to_pass_steps_median'):>7}"
                  f"{value('speed_advantage_alongside_median'):>7}"
                  f"{value('peak_abs_lat_maneuver_median'):>8}"
                  f"{value('min_gap_rival_maneuver_median'):>9}"
                  f"{value('min_gap_third_party_maneuver_median'):>9}"
                  f"{value('guard_fraction_window_median'):>8}"
                  f"{value('rival_admitted_fraction_median'):>7}")


if __name__ == "__main__":
    main()
