#!/usr/bin/env python
"""Every number the manuscript quotes for the proposed controller, recomputed.

The submitted policy fuses five world models, so the proposed arm of the main
comparison is the fused run: the endpoint audit, the whole-episode containment
and the vehicle-state tables of the fused run root replace the single-model
ones. This script prints that arm's row of the main table, its clause-failure
profile, its interaction-graph and planner statistics, the manoeuvre numbers
quoted in the text, and the five single-model draws the fused policy replaces.
Nothing is hard-coded: each figure below is read from the released table it
belongs to.

Usage:
    python3 scripts/report_fused_paper_numbers.py \
        --data-root outputs/tits_dynamic_graph_expanded/corrected_v2_20260920 \
        --fused-root outputs/tits_dynamic_graph_expanded \
        --seedspread outputs/tits_dynamic_graph_expanded/validity_ours_seedspread_20260928 \
        --out /tmp/fused_paper_numbers.json
"""

import argparse
import csv
import json
import math
import random
import statistics as stats
from pathlib import Path

OURS = "ours_dnq_dlc"
FUSED_ARM = "ours_dnq_dlc_ensemble"
CLAUSES = [("no lead", "sustained_lead"), ("contact", "contact_free"),
           ("off track", "T_v3"), ("stability", "S_v3"), ("non-racing rival", "Q")]
ENDPOINTS = ("P", "E_full", "E_race")
SCALES = ("M4_sparse", "M6_dense", "M8_scale", "M10_scale")


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def ok_rows(path):
    return [row for row in read_csv(path) if row.get("status") == "ok"]


def wilson(k, n, z=1.96):
    if n == 0:
        return float("nan"), float("nan")
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return centre - half, centre + half


def endpoint_block(rows):
    n = len(rows)
    out = {"n": n}
    for key in ENDPOINTS:
        k = sum(1 for row in rows if row[key] == "True")
        low, high = wilson(k, n)
        out[key] = {"k": k, "rate": k / n, "ci": [low, high]}
    return out


def clause_block(rows):
    return {label: sum(1 for row in rows if row[key] != "True") for label, key in CLAUSES}


def is_true(row, key):
    return row.get(key) == "True"


def ladder_block(rows):
    """The nested pass tiers of Section IV-A, in the order the text reads them."""
    return {
        "P": sum(1 for r in rows if is_true(r, "P")),
        "P&L&C": sum(1 for r in rows if is_true(r, "P")
                     and is_true(r, "sustained_lead") and is_true(r, "contact_free")),
        "E_pass": sum(1 for r in rows if is_true(r, "E_pass")),
        "E_valid": sum(1 for r in rows if is_true(r, "E_valid")),
        "E_full": sum(1 for r in rows if is_true(r, "E_full")),
        "E_race": sum(1 for r in rows if is_true(r, "E_race")),
    }


def case_block(rows):
    """Per-case summaries of the case-level columns the text quotes for one arm."""
    def values(key):
        # An audit row can carry "nan" for a quantity that the run never
        # produced, and a single such cell would poison a mean over 48 cases.
        out = []
        for row in rows:
            cell = row.get(key)
            if cell in (None, ""):
                continue
            number = float(cell)
            if math.isfinite(number):
                out.append(number)
        return out

    def mean(key):
        got = values(key)
        return stats.fmean(got) if got else float("nan")

    def median(key):
        got = values(key)
        return stats.median(got) if got else float("nan")

    return {
        "cases": len(rows),
        "rank_gain_mean": mean("rank_gain"),
        "rank_gain_median": median("rank_gain"),
        "passes": sum(int(r["event_count"]) for r in rows),
        "passes_per_case": mean("event_count"),
        "speed": mean("mean_speed"),
        "t_pass_mean": mean("time_to_pass_steps"),
        "t_pass_median": median("time_to_pass_steps"),
        "latency": mean("latency_ms"),
        "latency_p95": mean("latency_p95_ms"),
        "shield_rate": mean("recovery_rate"),
        "window_offroad": mean("frac_offroad"),
        "window_lat": mean("mean_abs_lat"),
        "ladder": ladder_block(rows),
        "per_scale": {
            scale: {
                "P": sum(1 for r in rows if r["experiment_id"] == scale and is_true(r, "P")),
                "E_full": sum(1 for r in rows if r["experiment_id"] == scale
                              and is_true(r, "E_full")),
                "E_race": sum(1 for r in rows if r["experiment_id"] == scale
                              and is_true(r, "E_race")),
                "rank_gain_mean": stats.fmean(float(r["rank_gain"]) for r in rows
                                              if r["experiment_id"] == scale),
                "cases": sum(1 for r in rows if r["experiment_id"] == scale),
            }
            for scale in SCALES
        },
    }


def _mcnemar_exact(b, c):
    """Two-sided exact McNemar p over the discordant pairs."""
    n = b + c
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, i) for i in range(min(b, c) + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def _bootstrap_ci(diffs, draws=20000, seed=20260928):
    rng = random.Random(seed)
    n = len(diffs)
    means = sorted(stats.fmean(rng.choices(diffs, k=n)) for _ in range(draws))
    return means[int(0.025 * draws)], means[int(0.975 * draws) - 1]


def paired_block(rows, reference, numeric):
    """Paired comparison of one arm against the rule expert over the 48 cases."""
    # The submitted audit records the run directory of a case, the released
    # matrix records the case id, so the join goes through the directory name.
    case_id = lambda r: Path(r["case_dir"]).name
    ref = {case_id(r): r for r in reference}
    out = {}
    for key, column in numeric.items():
        diffs = []
        for row in rows:
            other = ref.get(case_id(row))
            if other is None:
                continue
            mine, theirs = float(row[column]), float(other[column])
            if not (math.isfinite(mine) and math.isfinite(theirs)):
                continue
            diffs.append(mine - theirs)
        low, high = _bootstrap_ci(diffs)
        out[key] = {
            "mean_difference": stats.fmean(diffs),
            "ci": [low, high],
            "wins": sum(1 for d in diffs if d > 0),
            "losses": sum(1 for d in diffs if d < 0),
            "ties": sum(1 for d in diffs if d == 0),
        }
    discordant = [(is_true(r, "E_full"), is_true(ref[case_id(r)], "E_full"))
                  for r in rows if case_id(r) in ref]
    win = sum(1 for mine, theirs in discordant if mine and not theirs)
    lose = sum(1 for mine, theirs in discordant if theirs and not mine)
    out["E_full_mcnemar"] = {"ours_only": win, "reference_only": lose,
                             "p": _mcnemar_exact(win, lose)}
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data-root", required=True,
                        help="released table root of the main matrix")
    parser.add_argument("--fused-root", required=True,
                        help="root holding the fused-arm audits and derived tables")
    parser.add_argument("--seedspread", required=True,
                        help="directory of the five single-model arms")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    data = Path(args.data_root)
    fused = Path(args.fused_root)
    report = {}

    main_rows = ok_rows(data / "validity_final_all" / "case_level.csv")
    fused_rows = ok_rows(fused / "validity_ours_ensemble_20260928" / "case_level.csv")

    report["endpoints"] = {
        "fused": endpoint_block(fused_rows),
        "nominal": endpoint_block([r for r in main_rows if r["algorithm"] == OURS]),
        "comparators": {algo: endpoint_block([r for r in main_rows if r["algorithm"] == algo])
                        for algo in sorted({r["algorithm"] for r in main_rows}) if algo != OURS},
    }

    containment = {}
    for path, label in ((data / "containment_all_20260923" / "episode_level.csv", "main"),
                        (fused / "containment_ours_ensemble_20260928" / "episode_level.csv", "fused")):
        for row in read_csv(path):
            # The fused run names its arm after the ensemble; the manuscript
            # pools it onto the single proposed-controller label.
            arm = OURS if row["algorithm"] in (OURS, FUSED_ARM) else row["algorithm"]
            containment.setdefault((arm, label), []).append(row)
    report["containment"] = {}
    for (algo, source), rows in containment.items():
        if algo != OURS and source == "fused":
            continue
        report["containment"].setdefault(algo, {})[source] = {
            "grass": stats.fmean(float(r["episode_grass"]) for r in rows),
            "lat": stats.fmean(float(r["episode_lat"]) for r in rows),
        }

    report["clauses"] = {
        "fused": clause_block(fused_rows),
        "nominal": clause_block([r for r in main_rows if r["algorithm"] == OURS]),
        "comparators": {algo: clause_block([r for r in main_rows if r["algorithm"] == algo])
                        for algo in ("rule_expert_gate", "dlc_individual_transition",
                                     "dlc_joint_transition", "dlc_joint_transition_observer")},
    }

    report["ours"] = case_block(fused_rows)
    report["nominal_case_block"] = case_block([r for r in main_rows if r["algorithm"] == OURS])
    report["comparator_case_blocks"] = {
        algo: case_block([r for r in main_rows if r["algorithm"] == algo])
        for algo in sorted({r["algorithm"] for r in main_rows}) if algo != OURS
    }
    report["paired"] = paired_block(
        fused_rows, [r for r in main_rows if r["algorithm"] == "rule_expert_gate"],
        {"rank_gain": "rank_gain", "window_offroad": "frac_offroad",
         "window_lat": "mean_abs_lat", "speed": "mean_speed"})

    summary = fused / "validity_ours_ensemble_20260928" / "ours_ensemble_summary.json"
    if summary.exists():
        report["ensemble_summary"] = json.loads(summary.read_text(encoding="utf-8"))

    windows = read_csv(data / "neighborhood_events_fused_20260928"
                       / "neighborhood_event_level.csv")
    # The fused pass windows carry the pooled arm name used in the manuscript.
    windows = [r for r in windows if r["algorithm"] == OURS]
    report["membership"] = {
        "events": len(windows),
        "cases": len({r["case"] for r in windows}),
        "partner_in_window_any": stats.fmean(1.0 if r["partner_in_window_any"] == "True" else 0.0
                                             for r in windows),
        "partner_at_complete": stats.fmean(1.0 if r["partner_at_complete"] == "True" else 0.0
                                           for r in windows),
        "set_changes_mean": stats.fmean(float(r["set_changes_in_window"]) for r in windows),
        "per_scale": {
            scale: {
                "events": sum(1 for r in windows if r["experiment_id"] == scale),
                "partner_in_window_any": sum(1 for r in windows if r["experiment_id"] == scale
                                             and r["partner_in_window_any"] == "True"),
                "partner_at_complete_rate": stats.fmean(
                    [1.0 if r["partner_at_complete"] == "True" else 0.0
                     for r in windows if r["experiment_id"] == scale] or [float("nan")]),
                "set_changes_mean": stats.fmean(
                    [float(r["set_changes_in_window"]) for r in windows
                     if r["experiment_id"] == scale] or [float("nan")]),
            }
            for scale in SCALES
        },
    }

    signals = read_csv(data / "controller_signals_fused_20260928" / "controller_signals_by_scale.csv")
    report["mechanism"] = {}
    for row in signals:
        report["mechanism"][row["experiment_id"]] = {
            "exposed": float(row["exposed_mean_mean"]),
            "admitted": float(row["admitted_mean_mean"]),
            "pruning": float(row["pruning_rate_mean"]),
            "churn": float(row["neighbor_churn_rate_mean"]),
            "distinct": float(row["neighbor_distinct_total_mean"]),
            "err1": float(row["wm_pos_err_ego_h1_mean"]),
            "err4": float(row["wm_pos_err_ego_h4_mean"]),
            "planner_active": float(row["planner_active_rate_mean"]),
            "shield_active": float(row["shield_active_rate_mean"]),
            "override": float(row["override_rate_mean"]),
        }

    events = read_csv(data / "vehicle_states_fused_20260928" / "vehicle_event_level.csv")
    report["manoeuvre"] = {}
    for algo in ("ours_dnq_dlc", "rule_expert_gate", "dlc_individual_transition"):
        rows = [r for r in events if r["algorithm"] == algo and r.get("available") == "True"]
        if not rows:
            continue
        report["manoeuvre"][algo] = {
            "passes": len(rows),
            "approach_steps": stats.fmean(float(r["approach_steps"]) for r in rows),
            "alongside_steps": stats.fmean(float(r["alongside_steps"]) for r in rows),
            "grass_steps": stats.fmean(float(r["grass_steps_maneuver"]) for r in rows)
            if "grass_steps_maneuver" in rows[0] else None,
            "min_gap": stats.fmean(float(r["min_gap_rival_maneuver"]) for r in rows)
            if "min_gap_rival_maneuver" in rows[0] else None,
        }
        report["manoeuvre"][algo]["per_scale"] = {
            scale: {
                "passes": sum(1 for r in rows if r["experiment_id"] == scale),
                "approach_steps": stats.fmean(
                    [float(r["approach_steps"]) for r in rows
                     if r["experiment_id"] == scale] or [float("nan")]),
                "alongside_steps": stats.fmean(
                    [float(r["alongside_steps"]) for r in rows
                     if r["experiment_id"] == scale] or [float("nan")]),
                "grass_steps": stats.fmean(
                    [float(r["grass_steps_maneuver"]) for r in rows
                     if r["experiment_id"] == scale] or [float("nan")]),
                "rival_slows_2ms": stats.fmean(
                    [1.0 if float(r["rival_speed_drop"]) >= 2.0 else 0.0 for r in rows
                     if r["experiment_id"] == scale] or [float("nan")]),
            }
            for scale in SCALES
        }

    spread = []
    for row in ok_rows(Path(args.seedspread) / "case_level.csv"):
        spread.append({"arm": row["algorithm"], "scale": row["experiment_id"],
                       "P": row["P"], "E_full": row["E_full"], "E_race": row["E_race"]})
    report["seedspread_case_level"] = spread

    print("== endpoints (fused / nominal) ==")
    for label in ("fused", "nominal"):
        block = report["endpoints"][label]
        print(f"{label:8s} n={block['n']} " + "  ".join(
            f"{key}={block[key]['k']} [{block[key]['ci'][0]:.3f},{block[key]['ci'][1]:.3f}]"
            for key in ENDPOINTS))
    print("== containment grass / |lat| ==")
    for algo, per_source in report["containment"].items():
        parts = " | ".join(f"{source}: {v['grass']:.3f}/{v['lat']:.2f}"
                           for source, v in per_source.items())
        print(f"  {algo:32s} {parts}")
    print("== clause failures ==")
    for label in ("fused", "nominal"):
        print(f"  {label:8s} {report['clauses'][label]}")
    print("== mechanism ==")
    for scale in SCALES:
        row = report["mechanism"].get(scale)
        if row:
            print(f"  {scale:10s} exp={row['exposed']:.2f} adm={row['admitted']:.2f} "
                  f"prune={row['pruning']:.2f} churn={row['churn']:.2f} D={row['distinct']:.1f} "
                  f"e1={row['err1']:.2f} e4={row['err4']:.2f} feasible={row['planner_active']:.2f} "
                  f"shield={row['shield_active']:.2f} override={row['override']:.2f}")
    print("== manoeuvre ==")
    for algo, row in report["manoeuvre"].items():
        print(f"  {algo:32s} {row}")
    print("== ours (fused) case block ==")
    block = report["ours"]
    for key in ("cases", "rank_gain_mean", "rank_gain_median", "passes", "passes_per_case",
                "speed", "t_pass_mean", "t_pass_median", "latency", "latency_p95",
                "shield_rate", "window_offroad", "window_lat"):
        print(f"  {key:18s} {block[key]}")
    print("  ladder             ", block["ladder"])
    print("  per scale          ",
          {s: v for s, v in block["per_scale"].items()})
    print("== nominal case block ==")
    nominal = report["nominal_case_block"]
    print("  rank_gain", nominal["rank_gain_mean"], "median", nominal["rank_gain_median"],
          "passes/case", nominal["passes_per_case"], "speed", nominal["speed"],
          "latency", nominal["latency"], "shield", nominal["shield_rate"],
          "window", nominal["window_offroad"], nominal["window_lat"])
    print("  ladder             ", nominal["ladder"])
    print("  per scale          ", {s: v for s, v in nominal["per_scale"].items()})
    print("== pairs (fused vs rule expert) ==")
    print(" ", report["paired"])
    print("== membership (fused) ==")
    print(" ", {k: v for k, v in report["membership"].items() if k != "per_scale"})
    print("  per scale", report["membership"]["per_scale"])
    print("== ensemble summary ==")
    print(" ", json.dumps(report.get("ensemble_summary", {}), indent=1)[:1500])
    Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("wrote", args.out)


if __name__ == "__main__":
    main()
