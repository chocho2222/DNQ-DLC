#!/usr/bin/env python
import argparse
import csv
import itertools
import json
import math
from pathlib import Path

import numpy as np


FULL_SUITES = {
    "main": "evaluations/multiseed_suite/multiseed_suite_summary.json",
    "adaptive": "evaluations/adaptive_gate_suite/multiseed_suite_summary.json",
    "recovery": "evaluations/recovery_adaptive_suite/multiseed_suite_summary.json",
}


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def wilson_ci(successes, n, z=1.959963984540054):
    if n == 0:
        return [None, None]
    p = successes / n
    denom = 1.0 + z * z / n
    center = (p + z * z / (2.0 * n)) / denom
    half = z * math.sqrt((p * (1.0 - p) + z * z / (4.0 * n)) / n) / denom
    return [max(0.0, center - half), min(1.0, center + half)]


def exact_mcnemar_pvalue(b, c):
    discordant = b + c
    if discordant == 0:
        return 1.0
    tail = sum(math.comb(discordant, k) for k in range(0, min(b, c) + 1)) / (2 ** discordant)
    return min(1.0, 2.0 * tail)


def paired_bootstrap_diff(a_values, b_values, samples=20000, seed=0):
    a = np.asarray(a_values, dtype=np.float64)
    b = np.asarray(b_values, dtype=np.float64)
    rng = np.random.default_rng(seed)
    diffs = []
    for _ in range(samples):
        idx = rng.integers(0, len(a), size=len(a))
        diffs.append(float(np.mean(a[idx] - b[idx])))
    return [float(x) for x in np.quantile(diffs, [0.025, 0.5, 0.975])]


def classify_failure(row, thresholds):
    if row["validation_status"] == "PASS":
        return "pass"
    reasons = []
    if not row.get("target_completed_lap"):
        reasons.append("incomplete_lap")
    if row.get("target_final_rank_by_tiles") != 1:
        reasons.append("not_first")
    if row.get("first_ahead_step") is None:
        reasons.append("no_first_ahead")
    if float(row.get("target_grass_rate", 0.0)) > thresholds["max_target_grass_rate"]:
        reasons.append("target_grass")
    if float(row.get("max_grass_rate", 0.0)) > thresholds["max_any_grass_rate"]:
        reasons.append("traffic_grass")
    if float(row.get("mean_tile_progress", 0.0)) < thresholds["min_mean_tile_progress"]:
        reasons.append("low_traffic_progress")
    return "+".join(reasons) if reasons else "validator_fail_other"


def load_full_rows(root):
    rows = []
    thresholds = None
    suite_sources = []
    for suite_name, rel_path in FULL_SUITES.items():
        path = root / rel_path
        if not path.exists():
            continue
        suite = load_json(path)
        thresholds = thresholds or suite.get("thresholds", {})
        suite_sources.append({"suite": suite_name, "path": str(path)})
        for row in suite["rows"]:
            item = dict(row)
            item["suite"] = suite_name
            item["method_key"] = f"{suite_name}:{row['method']}"
            rows.append(item)
    return rows, thresholds, suite_sources


def summarize_method(method, rows, thresholds):
    n = len(rows)
    pass_values = np.asarray([row["validation_status"] == "PASS" for row in rows], dtype=np.float64)
    pass_count = int(pass_values.sum())
    failures = [row for row in rows if row["validation_status"] != "PASS"]
    failure_counts = {}
    for row in failures:
        label = classify_failure(row, thresholds)
        failure_counts[label] = failure_counts.get(label, 0) + 1
    return {
        "method": method,
        "n": n,
        "pass_count": pass_count,
        "pass_rate": pass_count / n if n else None,
        "pass_rate_wilson_ci95": wilson_ci(pass_count, n),
        "target_grass_mean": float(np.mean([row["target_grass_rate"] for row in rows])) if rows else None,
        "target_grass_median": float(np.median([row["target_grass_rate"] for row in rows])) if rows else None,
        "max_grass_mean": float(np.mean([row["max_grass_rate"] for row in rows])) if rows else None,
        "target_progress_mean": float(np.mean([row["target_tile_progress"] for row in rows])) if rows else None,
        "mean_progress_mean": float(np.mean([row["mean_tile_progress"] for row in rows])) if rows else None,
        "target_rank_mean": float(np.mean([row["target_final_rank_by_tiles"] for row in rows])) if rows else None,
        "steps_mean": float(np.mean([row["steps_run"] for row in rows])) if rows else None,
        "failure_counts": failure_counts,
        "failure_seeds": [row["seed"] for row in failures],
    }


def pairwise_tests(method_rows, seed=0):
    output = []
    for idx, (a_method, b_method) in enumerate(itertools.combinations(sorted(method_rows), 2)):
        a_rows = {row["seed"]: row for row in method_rows[a_method]}
        b_rows = {row["seed"]: row for row in method_rows[b_method]}
        seeds = sorted(set(a_rows) & set(b_rows))
        if not seeds:
            continue
        a_pass = np.asarray([a_rows[seed]["validation_status"] == "PASS" for seed in seeds], dtype=np.float64)
        b_pass = np.asarray([b_rows[seed]["validation_status"] == "PASS" for seed in seeds], dtype=np.float64)
        b_only = int(np.sum((a_pass == 0) & (b_pass == 1)))
        a_only = int(np.sum((a_pass == 1) & (b_pass == 0)))
        ci = paired_bootstrap_diff(a_pass, b_pass, seed=seed + idx)
        output.append(
            {
                "method_a": a_method,
                "method_b": b_method,
                "n_paired": len(seeds),
                "pass_rate_a": float(a_pass.mean()),
                "pass_rate_b": float(b_pass.mean()),
                "paired_diff_a_minus_b": float(a_pass.mean() - b_pass.mean()),
                "paired_diff_bootstrap_ci95": ci,
                "a_only_successes": a_only,
                "b_only_successes": b_only,
                "mcnemar_exact_p": exact_mcnemar_pvalue(a_only, b_only),
            }
        )
    return output


def complementarity(method_rows):
    seeds = sorted({row["seed"] for rows in method_rows.values() for row in rows})
    rows = []
    for seed in seeds:
        passing = []
        failing = []
        for method, values in method_rows.items():
            by_seed = {row["seed"]: row for row in values}
            if seed not in by_seed:
                continue
            if by_seed[seed]["validation_status"] == "PASS":
                passing.append(method)
            else:
                failing.append(method)
        rows.append({"seed": seed, "passing_methods": passing, "failing_methods": failing})
    return rows


def write_markdown(report, path):
    lines = [
        "# Full Statistical Report",
        "",
        f"- Full-suite sources: {', '.join(item['suite'] for item in report['suite_sources'])}",
        f"- Seeds: {', '.join(str(seed) for seed in report['seeds'])}",
        "",
        "## Method Summary",
        "",
        "| method | n | pass | rate | Wilson 95% CI | target grass | progress | rank | failure seeds |",
        "|---|---:|---:|---:|---|---:|---:|---:|---|",
    ]
    for item in sorted(report["method_summaries"], key=lambda x: x["pass_rate"], reverse=True):
        ci = item["pass_rate_wilson_ci95"]
        lines.append(
            f"| {item['method']} | {item['n']} | {item['pass_count']} | {item['pass_rate']:.3f} | "
            f"[{ci[0]:.3f}, {ci[1]:.3f}] | {item['target_grass_mean']:.3f} | "
            f"{item['target_progress_mean']:.3f} | {item['target_rank_mean']:.2f} | "
            f"{', '.join(str(seed) for seed in item['failure_seeds']) or 'none'} |"
        )
    lines.extend(
        [
            "",
            "## Paired Method Comparisons",
            "",
            "| method A | method B | n | A-B pass diff | bootstrap 95% CI | A-only | B-only | McNemar p |",
            "|---|---|---:|---:|---|---:|---:|---:|",
        ]
    )
    for item in sorted(report["pairwise_tests"], key=lambda x: abs(x["paired_diff_a_minus_b"]), reverse=True):
        ci = item["paired_diff_bootstrap_ci95"]
        lines.append(
            f"| {item['method_a']} | {item['method_b']} | {item['n_paired']} | "
            f"{item['paired_diff_a_minus_b']:.3f} | [{ci[0]:.3f}, {ci[2]:.3f}] | "
            f"{item['a_only_successes']} | {item['b_only_successes']} | {item['mcnemar_exact_p']:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Failure Type Counts",
            "",
            "| method | failure type | count |",
            "|---|---|---:|",
        ]
    )
    for item in sorted(report["method_summaries"], key=lambda x: x["pass_rate"], reverse=True):
        if not item["failure_counts"]:
            lines.append(f"| {item['method']} | none | 0 |")
        for label, count in sorted(item["failure_counts"].items(), key=lambda kv: (-kv[1], kv[0])):
            lines.append(f"| {item['method']} | {label} | {count} |")
    lines.extend(
        [
            "",
            "## Seed Complementarity",
            "",
            "| seed | passing methods | failing methods |",
            "|---:|---|---|",
        ]
    )
    for row in report["seed_complementarity"]:
        lines.append(
            f"| {row['seed']} | {', '.join(row['passing_methods']) or 'none'} | "
            f"{', '.join(row['failing_methods']) or 'none'} |"
        )
    lines.extend(["", "## Interpretation", "", report["interpretation"], ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export full-suite statistics for manuscript-grade reporting.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    parser.add_argument("--out-prefix", default="full_statistical_report")
    args = parser.parse_args()

    root = Path(args.root)
    rows, thresholds, suite_sources = load_full_rows(root)
    if not rows:
        raise FileNotFoundError(f"No full-suite rows found under {root}")
    thresholds = {
        "max_target_grass_rate": 0.08,
        "max_any_grass_rate": 0.40,
        "min_mean_tile_progress": 0.60,
        **(thresholds or {}),
    }
    method_rows = {}
    for row in rows:
        method_rows.setdefault(row["method_key"], []).append(row)
    seeds = sorted({row["seed"] for row in rows})
    report = {
        "root": str(root),
        "suite_sources": suite_sources,
        "thresholds": thresholds,
        "seeds": seeds,
        "method_summaries": [
            summarize_method(method, sorted(values, key=lambda row: row["seed"]), thresholds)
            for method, values in sorted(method_rows.items())
        ],
        "pairwise_tests": pairwise_tests(method_rows),
        "seed_complementarity": complementarity(method_rows),
        "interpretation": (
            "The strongest single controller remains the rule-based overtake baseline. "
            "Adaptive graph shielding narrows the gap but does not significantly exceed "
            "the baseline on the current 10 paired seeds. Seed-level complementarity "
            "supports portfolio selection as a research direction, while selector "
            "prototypes remain insufficient."
        ),
    }

    table_dir = root / "tables"
    table_dir.mkdir(parents=True, exist_ok=True)
    out_json = table_dir / f"{args.out_prefix}.json"
    out_md = table_dir / f"{args.out_prefix}.md"
    out_csv = table_dir / f"{args.out_prefix}_method_summary.csv"
    out_pair_csv = table_dir / f"{args.out_prefix}_pairwise.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)

    with out_csv.open("w", newline="", encoding="utf-8") as handle:
        fields = [
            "method",
            "n",
            "pass_count",
            "pass_rate",
            "ci95_low",
            "ci95_high",
            "target_grass_mean",
            "target_progress_mean",
            "target_rank_mean",
            "failure_seeds",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in report["method_summaries"]:
            ci = item["pass_rate_wilson_ci95"]
            writer.writerow(
                {
                    "method": item["method"],
                    "n": item["n"],
                    "pass_count": item["pass_count"],
                    "pass_rate": f"{item['pass_rate']:.6f}",
                    "ci95_low": f"{ci[0]:.6f}",
                    "ci95_high": f"{ci[1]:.6f}",
                    "target_grass_mean": f"{item['target_grass_mean']:.6f}",
                    "target_progress_mean": f"{item['target_progress_mean']:.6f}",
                    "target_rank_mean": f"{item['target_rank_mean']:.6f}",
                    "failure_seeds": ",".join(str(seed) for seed in item["failure_seeds"]),
                }
            )
    with out_pair_csv.open("w", newline="", encoding="utf-8") as handle:
        fields = [
            "method_a",
            "method_b",
            "n_paired",
            "pass_rate_a",
            "pass_rate_b",
            "paired_diff_a_minus_b",
            "ci95_low",
            "ci95_median",
            "ci95_high",
            "a_only_successes",
            "b_only_successes",
            "mcnemar_exact_p",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in report["pairwise_tests"]:
            ci = item["paired_diff_bootstrap_ci95"]
            writer.writerow(
                {
                    "method_a": item["method_a"],
                    "method_b": item["method_b"],
                    "n_paired": item["n_paired"],
                    "pass_rate_a": f"{item['pass_rate_a']:.6f}",
                    "pass_rate_b": f"{item['pass_rate_b']:.6f}",
                    "paired_diff_a_minus_b": f"{item['paired_diff_a_minus_b']:.6f}",
                    "ci95_low": f"{ci[0]:.6f}",
                    "ci95_median": f"{ci[1]:.6f}",
                    "ci95_high": f"{ci[2]:.6f}",
                    "a_only_successes": item["a_only_successes"],
                    "b_only_successes": item["b_only_successes"],
                    "mcnemar_exact_p": f"{item['mcnemar_exact_p']:.6f}",
                }
            )
    print(
        json.dumps(
            {
                "json": str(out_json),
                "markdown": str(out_md),
                "method_csv": str(out_csv),
                "pairwise_csv": str(out_pair_csv),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
