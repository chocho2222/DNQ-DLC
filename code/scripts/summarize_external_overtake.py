#!/usr/bin/env python
"""Summarise the external passing-manoeuvre audit over several clearance settings.

Inputs are directories written by ``scripts/audit_external_overtake.py``.
Outputs a headline table with Wilson intervals, the paired case counts against
the proposed controller, and the clearance sweep.

Usage:
    python -m scripts.summarize_external_overtake --out <dir> \
        --runs c0=/tmp/a c24=/tmp/b ...
"""
import argparse
import csv
import json
import math
import os

ORDER = ["ours_dnq_dlc", "rule_expert_gate", "dlc_joint_transition_observer",
         "dlc_individual_transition", "dlc_joint_transition",
         "ppo_continuous", "sac_continuous", "td3_continuous"]
BASELINE = "ours_dnq_dlc"


def wilson(k, n, z=1.959963984540054):
    if n == 0:
        return (None, None)
    p = k / n
    den = 1 + z * z / n
    cen = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, cen - half), min(1.0, cen + half))


def load(directory):
    path = os.path.join(directory, "case_level_external.csv")
    return list(csv.DictReader(open(path, encoding="utf-8")))


def key(row):
    return (row["experiment_id"], row["case_dir"])


def paired(rows, endpoint, other):
    base = {key(r): r for r in rows if r["algorithm"] == BASELINE}
    cmp_ = {key(r): r for r in rows if r["algorithm"] == other}
    shared = sorted(set(base) & set(cmp_))
    win = lose = 0
    for k in shared:
        a = base[k][endpoint] == "True"
        b = cmp_[k][endpoint] == "True"
        if a and not b:
            win += 1
        elif b and not a:
            lose += 1
    return win, lose, len(shared)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--runs", required=True,
                        help="comma-separated NAME=DIR pairs, headline run first")
    parser.add_argument("--endpoint", default="X_strict")
    args = parser.parse_args()

    runs = []
    for item in args.runs.split(","):
        name, _, directory = item.partition("=")
        runs.append((name.strip(), directory.strip()))
    os.makedirs(args.out, exist_ok=True)

    headline_name, headline_dir = runs[0]
    rows = load(headline_dir)

    summary, paired_rows = [], []
    for algorithm in ORDER:
        subset = [r for r in rows if r["algorithm"] == algorithm]
        if not subset:
            continue
        n = len(subset)
        for endpoint in ("X_pass", "X_strict", "X_strict_all"):
            k = sum(1 for r in subset if r.get(endpoint) == "True")
            lo, hi = wilson(k, n)
            summary.append({"endpoint": endpoint, "algorithm": algorithm, "cases": n,
                            "count": k, "rate": k / n, "wilson_low": lo, "wilson_high": hi})
        if algorithm != BASELINE:
            win, lose, shared = paired(rows, args.endpoint, algorithm)
            paired_rows.append({"endpoint": args.endpoint, "algorithm": algorithm,
                                "shared_cases": shared, "proposed_wins": win,
                                "proposed_loses": lose, "net": win - lose})

    sweep = []
    for name, directory in runs:
        if not os.path.exists(os.path.join(directory, "case_level_external.csv")):
            continue
        for r in load(directory):
            if r.get("X_strict") is None:
                continue
            sweep.append({"setting": name, "algorithm": r["algorithm"],
                          "case_dir": r["case_dir"], "endpoint": args.endpoint,
                          "value": r[args.endpoint]})

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

    write(os.path.join(args.out, "external_headline.csv"), summary)
    write(os.path.join(args.out, "external_paired.csv"), paired_rows)
    write(os.path.join(args.out, "external_clearance_sweep.csv"), sweep)

    counts = {}
    for name, directory in runs:
        if not os.path.exists(os.path.join(directory, "case_level_external.csv")):
            continue
        rows_n = load(directory)
        counts[name] = {a: sum(1 for r in rows_n
                               if r["algorithm"] == a and r.get(args.endpoint) == "True")
                        for a in ORDER}
    json.dump({"headline_run": headline_name, "endpoint": args.endpoint,
               "counts_by_setting": counts,
               "paired": paired_rows},
              open(os.path.join(args.out, "external_summary.json"), "w"),
              indent=2, sort_keys=True)

    print(f"{'algorithm':<34}{'X_pass':>8}{'X_strict':>10}{'X_all':>7}")
    for algorithm in ORDER:
        sub = {r["endpoint"]: r for r in summary if r["algorithm"] == algorithm}
        if not sub:
            continue
        print(f"{algorithm:<34}{sub['X_pass']['count']:>8}{sub['X_strict']['count']:>10}"
              f"{sub['X_strict_all']['count']:>7}")
    print()
    for rec in paired_rows:
        print(f"  vs {rec['algorithm']:<32} win {rec['proposed_wins']:>2} "
              f"lose {rec['proposed_loses']:>2} of {rec['shared_cases']}")
    print()
    for name, _ in runs:
        if name in counts:
            print(f"  {name:<12}" + " ".join(f"{counts[name][a]:>4}" for a in ORDER))


if __name__ == "__main__":
    main()
