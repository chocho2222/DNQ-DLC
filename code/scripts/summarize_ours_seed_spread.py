#!/usr/bin/env python
"""Recompute the proposed controller's row of the main table, once per
world-model training seed.

Every quoted quantity is read from the released run summaries, and the three
strict-tier counts are read from the endpoint audit of the same run root, so
this script can be pointed at any seed set without editing the paper's numbers
by hand.

Usage:
    python -m scripts.summarize_ours_seed_spread \
        --eval-root /tmp/ours_seedfix \
        --audit <audit dir with case_level.csv> \
        --containment <episode_level.csv> \
        --out <summary.json>
"""
import argparse
import csv
import glob
import json
import math
import os
import statistics as stats
from collections import defaultdict

ENDPOINTS = ["P", "E_full", "E_race"]


def mcnemar_exact(wins, losses):
    """Two-sided exact McNemar p-value on the discordant pairs."""
    n = wins + losses
    if n == 0:
        return float("nan")
    k = min(wins, losses)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2.0 ** n
    return min(1.0, 2.0 * tail)


def case_key(row):
    return (row["experiment_id"], row["num_agents"], row["seed"], row.get("track_id", ""))


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--eval-root", required=True,
                        help="run root holding <case>/summaries/<arm>_n<n>_seed<s>.summary.json")
    parser.add_argument("--audit", required=True, help="audit directory holding case_level.csv")
    parser.add_argument("--containment", required=True, help="episode_level.csv of whole-episode containment")
    parser.add_argument("--out", required=True)
    parser.add_argument("--reference-audit", default="",
                        help="audit holding the single-run comparators; when given, each seed is "
                             "paired against the reference arm on the endpoint")
    parser.add_argument("--reference-arm", default="rule_expert_gate")
    parser.add_argument("--endpoint", default="E_full")
    args = parser.parse_args()

    summaries = defaultdict(list)
    for path in sorted(glob.glob(os.path.join(args.eval_root, "M*_seed*", "summaries", "*.summary.json"))):
        row = json.load(open(path, encoding="utf-8"))
        summaries[row["algorithm"]].append(row)

    containment = defaultdict(list)
    for row in read_csv(args.containment):
        containment[row["algorithm"]].append(row)

    case_rows = defaultdict(list)
    for row in read_csv(os.path.join(args.audit, "case_level.csv")):
        if row.get("status") != "ok":
            continue
        case_rows[row["algorithm"]].append(row)

    tiers = defaultdict(lambda: defaultdict(list))
    for algorithm, group in case_rows.items():
        for row in group:
            for endpoint in ENDPOINTS:
                tiers[algorithm][endpoint].append(1.0 if row[endpoint] == "True" else 0.0)

    arms = sorted(summaries)
    table = []
    for arm in arms:
        rows = summaries[arm]
        audit_rows = case_rows.get(arm, [])
        n = len(rows)
        grass = [float(r["episode_grass"]) for r in containment[arm]]
        lat = [float(r["episode_lat"]) for r in containment[arm]]
        # The speed and time columns of the main table are the audit's
        # whole-episode mean speed and its time to the first qualifying pass,
        # not the per-case values recorded in the summary files.
        speed = [float(r["mean_speed"]) for r in audit_rows if r["mean_speed"] not in ("", "nan")]
        t_pass = [float(r["time_to_pass_steps"]) for r in audit_rows
                  if r["time_to_pass_steps"] not in ("", "nan")]
        entry = {
            "arm": arm,
            "cases": n,
            "P": int(sum(tiers[arm]["P"])),
            "E_full": int(sum(tiers[arm]["E_full"])),
            "E_race": int(sum(tiers[arm]["E_race"])),
            "grass": stats.fmean(grass) if grass else float("nan"),
            "mean_abs_lat": stats.fmean(lat) if lat else float("nan"),
            "speed": stats.fmean(speed) if speed else float("nan"),
            "t_pass": stats.fmean(t_pass) if t_pass else float("nan"),
            "rank_gain": stats.fmean(float(r["rank_gain"]) for r in rows),
        }
        table.append(entry)

    print(f"{'arm':26s} {'P':>6s} {'Efull':>6s} {'Erace':>6s} {'grass':>7s} "
          f"{'|lat|':>6s} {'speed':>6s} {'tpass':>7s} {'rank':>6s}")
    for e in table:
        print(f"{e['arm']:26s} {e['P']:>6d} {e['E_full']:>6d} {e['E_race']:>6d} "
              f"{e['grass']:>7.3f} {e['mean_abs_lat']:>6.2f} {e['speed']:>6.1f} "
              f"{e['t_pass']:>7.0f} {e['rank_gain']:>6.2f}")

    paired = {}
    if args.reference_audit:
        reference = {}
        for row in read_csv(os.path.join(args.reference_audit, "case_level.csv")):
            if row.get("status") == "ok" and row["algorithm"] == args.reference_arm:
                reference[case_key(row)] = row
        print(f"\npaired against {args.reference_arm} on {args.endpoint}")
        for arm in arms:
            wins = losses = ties = 0
            for row in case_rows[arm]:
                other = reference.get(case_key(row))
                if other is None:
                    continue
                ours_hit = row[args.endpoint] == "True"
                other_hit = other[args.endpoint] == "True"
                if ours_hit and not other_hit:
                    wins += 1
                elif other_hit and not ours_hit:
                    losses += 1
                else:
                    ties += 1
            p = mcnemar_exact(wins, losses)
            paired[arm] = {"wins": wins, "losses": losses, "ties": ties, "p": p}
            print(f"{arm:26s} win={wins:>2d} lose={losses:>2d} tie={ties:>2d} "
                  f"discordant={wins + losses:>2d} p={p:.4f}")

    if len(table) > 1:
        print()
        for key in ["P", "E_full", "E_race", "grass", "mean_abs_lat", "speed", "t_pass", "rank_gain"]:
            values = [e[key] for e in table]
            print(f"mean {key:14s} = {stats.fmean(values):9.3f}   range "
                  f"[{min(values):.3f}, {max(values):.3f}]   spread {max(values) - min(values):.3f}")

    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump({"per_arm": table,
                   "paired": paired,
                   "case_level": os.path.relpath(os.path.join(args.audit, "case_level.csv"))},
                  handle, indent=2)
    print("\nwrote", args.out)


if __name__ == "__main__":
    main()
