#!/usr/bin/env python
"""Aggregate the strict RL baseline audit by training seed and against the main matrix.

Reads the ``case_level.csv`` written by ``scripts/audit_validity_endpoint_v3.py``
over the strict RL evaluation root and the one over the main matrix, and reports
each RL family as a mean over its training seeds together with the per-seed
spread and the paired case counts against the proposed controller.

Usage:
    python -m scripts.aggregate_rl_strict_endpoint --rl <case_level.csv> \
        --main <case_level.csv> --out <dir>
"""
import argparse
import csv
import json
import math
import os
import re

FAMILIES = ["ppo", "sac", "td3"]
ENDPOINTS = ["P", "E_pass", "E_valid", "E_full", "E_race"]
BASELINE = "ours_dnq_dlc"
CONTINUOUS = ["ppo_continuous", "sac_continuous", "td3_continuous"]


def wilson(k, n, z=1.959963984540054):
    if n == 0:
        return (None, None)
    p = k / n
    den = 1 + z * z / n
    cen = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, cen - half), min(1.0, cen + half))


def truth(value):
    return str(value).strip() == "True"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rl", required=True)
    parser.add_argument("--main", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    rl = list(csv.DictReader(open(args.rl, encoding="utf-8")))
    main_rows = list(csv.DictReader(open(args.main, encoding="utf-8")))
    os.makedirs(args.out, exist_ok=True)

    def case_key(row):
        # The two audits live in different roots, so the pairing unit is the
        # case itself (fleet size, track seed and experiment), not its path.
        return (row["experiment_id"], str(row["seed"]), str(row["num_agents"]))

    per_seed = []
    for row in rl:
        match = re.match(r"(ppo|sac|td3)_seed(\d+)$", row["algorithm"])
        if match:
            per_seed.append({**row, "family": match.group(1).upper(),
                             "training_seed": match.group(2)})

    by_family = {family: [r for r in per_seed if r["family"] == family]
                 for family in [f.upper() for f in FAMILIES]}

    family_rows = []
    for family, rows in by_family.items():
        if not rows:
            continue
        seeds = sorted({r["training_seed"] for r in rows})
        for endpoint in ENDPOINTS:
            counts = []
            for seed in seeds:
                sub = [r for r in rows if r["training_seed"] == seed]
                counts.append(sum(1 for r in sub if truth(r[endpoint])))
            n = len([r for r in rows if r["training_seed"] == seeds[0]])
            mean = sum(counts) / len(counts)
            lo, hi = wilson(int(round(mean)), n)
            family_rows.append({"family": family, "endpoint": endpoint,
                                "seeds": len(seeds), "cases_per_seed": n,
                                "per_seed_counts": " ".join(str(c) for c in counts),
                                "mean_count": mean, "mean_rate": mean / n if n else float("nan"),
                                "best_seed": max(counts), "worst_seed": min(counts),
                                "wilson_low": lo, "wilson_high": hi})

    baseline = {case_key(r): r for r in main_rows if r["algorithm"] == BASELINE}
    paired = []
    for family, rows in by_family.items():
        for endpoint in ENDPOINTS:
            wins, losses, shared = [], [], 0
            for seed in sorted({r["training_seed"] for r in rows}):
                sub = {case_key(r): r for r in rows if r["training_seed"] == seed}
                shared_keys = sorted(set(baseline) & set(sub))
                shared = len(shared_keys)
                wins.append(sum(1 for k in shared_keys
                                if truth(baseline[k][endpoint]) and not truth(sub[k][endpoint])))
                losses.append(sum(1 for k in shared_keys
                                  if truth(sub[k][endpoint]) and not truth(baseline[k][endpoint])))
            paired.append({"family": family, "endpoint": endpoint,
                           "shared_cases": shared,
                           "proposed_wins_mean": sum(wins) / len(wins) if wins else None,
                           "proposed_loses_mean": sum(losses) / len(losses) if losses else None,
                           "per_seed_wins": " ".join(str(w) for w in wins),
                           "per_seed_loses": " ".join(str(l) for l in losses)})

    single_seed_rows = []
    for row in main_rows:
        if row["algorithm"] in CONTINUOUS:
            for endpoint in ENDPOINTS:
                single_seed_rows.append({"source": "single_seed_50k",
                                         "algorithm": row["algorithm"],
                                         "endpoint": endpoint, "value": truth(row[endpoint])})
    single = {}
    for algorithm in CONTINUOUS:
        sub = [r for r in main_rows if r["algorithm"] == algorithm]
        single[algorithm] = {endpoint: sum(1 for r in sub if truth(r[endpoint]))
                             for endpoint in ENDPOINTS}

    def write(path, records):
        if not records:
            return
        fields = []
        for rec in records:
            for k in rec:
                if k not in fields:
                    fields.append(k)
        with open(path, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=fields)
            w.writeheader()
            w.writerows(records)

    write(os.path.join(args.out, "rl_strict_by_family.csv"), family_rows)
    write(os.path.join(args.out, "rl_strict_paired.csv"), paired)
    json.dump({"baseline": BASELINE, "endpoints": ENDPOINTS,
               "single_seed_50k_reference": single,
               "by_family": family_rows, "paired": paired},
              open(os.path.join(args.out, "rl_strict_summary.json"), "w"),
              indent=2, sort_keys=True)

    print(f"{'family':<6}{'endpoint':<9}{'per-seed counts':>20}{'mean':>8}{'best':>6}{'worst':>7}")
    for rec in family_rows:
        print(f"{rec['family']:<6}{rec['endpoint']:<9}{rec['per_seed_counts']:>20}"
              f"{rec['mean_count']:>8.1f}{rec['best_seed']:>6}{rec['worst_seed']:>7}")
    print()
    for rec in paired:
        print(f"  {rec['family']:<5}{rec['endpoint']:<9} baseline wins "
              f"{rec['proposed_wins_mean']:.1f} loses {rec['proposed_loses_mean']:.1f} "
              f"of {rec['shared_cases']}")
    print()
    print("single-seed 50k reference (current manuscript rows):")
    for algorithm, values in single.items():
        print("  " + algorithm + " " + " ".join(f"{k}={v}" for k, v in values.items()))


if __name__ == "__main__":
    main()
