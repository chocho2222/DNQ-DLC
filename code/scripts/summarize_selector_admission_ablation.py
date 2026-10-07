#!/usr/bin/env python
"""Paired view of the neighbour-admission ablation.

Every variant in the ablation shares the same planner, shield and quality terms
and differs only in the rule that decides which opponents enter the interaction
slots. Cases are paired by (experiment, track, seed) against a reference rule, so
the table reports within-case differences rather than two independent rates.

Usage:
    python3 scripts/summarize_selector_admission_ablation.py \
        --case-level <audit>/case_level.csv --out <dir> [--reference sel_dyn_k3]
"""

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

ENDPOINTS = ["P", "E_pass", "E_valid", "E_full", "Q", "E_race", "C", "L"]
CONTINUOUS = [
    "in_corridor_man",
    "mean_abs_lat",
    "guard_fraction",
    "time_to_pass_steps",
    "grass_fraction",
    "mean_speed",
]


def as_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def as_bool(value):
    return str(value).strip().lower() in {"true", "1", "yes"}


def load(path):
    with Path(path).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def wilson(count, total, z=1.96):
    if total <= 0:
        return (float("nan"), float("nan"))
    phat = count / total
    denom = 1.0 + z * z / total
    centre = (phat + z * z / (2 * total)) / denom
    half = z * np.sqrt(phat * (1 - phat) / total + z * z / (4 * total * total)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def bootstrap_ci(values, draws=20000, seed=11):
    values = np.asarray([v for v in values if not np.isnan(v)], dtype=float)
    if values.size == 0:
        return (float("nan"), float("nan"))
    if values.size == 1:
        return (float(values[0]), float(values[0]))
    rng = np.random.default_rng(seed)
    picks = rng.integers(0, values.size, size=(draws, values.size))
    means = values[picks].mean(axis=1)
    return (float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5)))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-level", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--reference", default="sel_dyn_k3")
    args = parser.parse_args()

    rows = [row for row in load(args.case_level) if row.get("status") == "ok"]
    by_experiment = defaultdict(list)
    for row in rows:
        by_experiment[row["experiment_id"]].append(row)
    variants = sorted({row["algorithm"] for row in rows})

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    rates = []
    for experiment, group in sorted(by_experiment.items()):
        for variant in variants:
            subset = [row for row in group if row["algorithm"] == variant]
            if not subset:
                continue
            record = {"experiment_id": experiment, "algorithm": variant, "n_cases": len(subset)}
            for endpoint in ENDPOINTS:
                count = sum(1 for row in subset if as_bool(row.get(endpoint)))
                low, high = wilson(count, len(subset))
                record[f"{endpoint}_count"] = count
                record[f"{endpoint}_rate"] = count / len(subset)
                record[f"{endpoint}_wilson_low"] = low
                record[f"{endpoint}_wilson_high"] = high
            for metric in CONTINUOUS:
                values = [as_float(row.get(metric)) for row in subset]
                record[f"{metric}_mean"] = float(np.nanmean(values)) if values else float("nan")
            rates.append(record)

    paired = []
    index = {(row["experiment_id"], row["track_id"], str(row["seed"]), row["algorithm"]): row for row in rows}
    keys = sorted({(row["experiment_id"], row["track_id"], str(row["seed"])) for row in rows})
    for experiment in sorted(by_experiment):
        for variant in variants:
            if variant == args.reference:
                continue
            differences = {endpoint: [] for endpoint in ENDPOINTS}
            continuous = {metric: [] for metric in CONTINUOUS}
            for key in keys:
                if key[0] != experiment:
                    continue
                a = index.get((*key, variant))
                b = index.get((*key, args.reference))
                if a is None or b is None:
                    continue
                for endpoint in ENDPOINTS:
                    differences[endpoint].append(float(as_bool(a.get(endpoint))) - float(as_bool(b.get(endpoint))))
                for metric in CONTINUOUS:
                    continuous[metric].append(as_float(a.get(metric)) - as_float(b.get(metric)))
            record = {
                "experiment_id": experiment,
                "algorithm": variant,
                "reference": args.reference,
                "n_paired": len(differences["P"]),
            }
            for endpoint in ENDPOINTS:
                values = differences[endpoint]
                low, high = bootstrap_ci(values)
                record[f"d_{endpoint}_mean"] = float(np.mean(values)) if values else float("nan")
                record[f"d_{endpoint}_ci_low"] = low
                record[f"d_{endpoint}_ci_high"] = high
                record[f"d_{endpoint}_crosses_zero"] = bool(low <= 0.0 <= high) if values else None
            for metric in CONTINUOUS:
                low, high = bootstrap_ci(continuous[metric])
                record[f"d_{metric}_mean"] = float(np.nanmean(continuous[metric])) if continuous[metric] else float("nan")
                record[f"d_{metric}_ci_low"] = low
                record[f"d_{metric}_ci_high"] = high
            paired.append(record)

    def write(name, records):
        if not records:
            return None
        path = out_dir / name
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(records[0]))
            writer.writeheader()
            writer.writerows(records)
        return str(path)

    rates_path = write("selector_rate_by_variant.csv", rates)
    paired_path = write("selector_paired_vs_reference.csv", paired)
    (out_dir / "summary.json").write_text(
        json.dumps(
            {
                "case_level": str(args.case_level),
                "reference": args.reference,
                "variants": variants,
                "n_cases": len(rows),
                "tables": {"rates": rates_path, "paired": paired_path},
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"{'experiment':<11}{'variant':<22}{'n':>3} {'P':>6} {'E_full':>7} {'E_race':>7} {'corr':>6} {'guard':>6}")
    for record in rates:
        print(
            f"{record['experiment_id']:<11}{record['algorithm']:<22}{record['n_cases']:>3} "
            f"{record['P_rate']:>6.3f} {record['E_full_rate']:>7.3f} {record['E_race_rate']:>7.3f} "
            f"{record['in_corridor_man_mean']:>6.3f} {record['guard_fraction_mean']:>6.3f}"
        )
    print()
    print(f"paired difference vs {args.reference} (positive favours the variant)")
    print(f"{'experiment':<11}{'variant':<22}{'n':>3} {'dP':>7} {'95% CI':>17} {'dE_full':>8} {'95% CI':>17}")
    for record in paired:
        lp, hp = record["d_P_ci_low"], record["d_P_ci_high"]
        lf, hf = record["d_E_full_ci_low"], record["d_E_full_ci_high"]
        print(
            f"{record['experiment_id']:<11}{record['algorithm']:<22}{record['n_paired']:>3} "
            f"{record['d_P_mean']:>7.3f} [{lp:>6.3f},{hp:>6.3f}] "
            f"{record['d_E_full_mean']:>8.3f} [{lf:>6.3f},{hf:>6.3f}]"
        )


if __name__ == "__main__":
    main()
