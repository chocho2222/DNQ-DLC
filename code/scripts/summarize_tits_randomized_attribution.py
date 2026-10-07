#!/usr/bin/env python
"""Aggregate randomized attribution runs without dropping failed episodes."""

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path

import numpy as np


BINARY_METRICS = ["overtake_success_rate"]
CONTINUOUS_METRICS = [
    "elegant_overtake_rate",
    "on_track_overtake_rate",
    "target_grass_rate",
    "collision_or_contact_proxy",
    "rank_gain",
    "target_progress",
    "overtake_count",
    "hard_recovery_rate",
    "anchor_action_deviation_mean",
]
LOWER_IS_BETTER = {"target_grass_rate", "collision_or_contact_proxy", "hard_recovery_rate"}
EXPECTED_CONTROLS = {
    "dnq_dlc_full": {"neighbor_selection_mode": "interaction"},
    "dnq_nearest_neighbor": {"neighbor_selection_mode": "nearest"},
    "dnq_w_o_dynamic_selection": {"neighbor_selection_mode": "fixed"},
    "dnq_w_o_quality_proposal": {"quality_planner_mode": "off"},
    "dnq_w_o_risk_uncertainty": {"planner_risk_weight": 0, "planner_uncertainty_weight": 0},
    "dnq_w_o_safety_quality": {"planner_risk_weight": 0, "planner_uncertainty_weight": 0, "planner_lane_weight": 0, "planner_grass_weight": 0, "planner_close_gap_weight": 0, "hard_safety_shield": False},
    "dnq_w_o_rule_anchor": {"use_rule_anchor": False},
    "dnq_w_o_handcrafted_candidates": {"use_handcrafted_candidates": False},
    "dnq_w_o_hard_recovery": {"hard_safety_shield": False},
}


def wilson(k, n, z=1.96):
    if n == 0:
        return [None, None]
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * np.sqrt((p * (1 - p) + z * z / (4 * n)) / n) / d
    return [float(max(0, centre - half)), float(min(1, centre + half))]


def bootstrap_mean(values, rng, repeats=10000):
    values = np.asarray(values, dtype=float)
    if len(values) == 0:
        return [None, None]
    if len(values) == 1:
        return [float(values[0]), float(values[0])]
    indices = rng.integers(0, len(values), size=(repeats, len(values)))
    samples = values[indices].mean(axis=1)
    return [float(np.quantile(samples, 0.025)), float(np.quantile(samples, 0.975))]


def safe_number(row, key):
    value = row.get(key)
    if value is None or isinstance(value, (list, dict)):
        return None
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return value if np.isfinite(value) else None


def case_key(row):
    return (row.get("track_path"), int(row["num_agents"]), int(row["seed"]))


def metric_signature(row):
    payload = {
        key: row.get(key)
        for key in [
            "overtake_success_rate", "elegant_overtake_rate", "target_grass_rate",
            "collision_or_contact_proxy", "rank_gain", "target_progress", "overtake_count",
        ]
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def control_issues(row):
    issues = []
    for key, expected in EXPECTED_CONTROLS.get(row.get("algorithm"), {}).items():
        observed = row.get(key)
        if observed != expected:
            issues.append({"algorithm": row.get("algorithm"), "seed": row.get("seed"), "track_path": row.get("track_path"), "num_agents": row.get("num_agents"), "field": key, "expected": expected, "observed": observed})
    return issues


def summarize(rows, rng):
    result = {"n": len(rows), "unique_metric_signature_count": len({metric_signature(row) for row in rows})}
    for metric in BINARY_METRICS:
        values = [safe_number(row, metric) for row in rows]
        values = [value for value in values if value is not None]
        k = int(sum(value >= 0.5 for value in values))
        result[metric] = {"n": len(values), "count": k, "mean": k / len(values) if values else None, "ci95_wilson": wilson(k, len(values))}
    for metric in CONTINUOUS_METRICS:
        values = [safe_number(row, metric) for row in rows]
        values = [value for value in values if value is not None]
        result[metric] = {
            "n": len(values),
            "mean": float(np.mean(values)) if values else None,
            "sd": float(np.std(values, ddof=1)) if len(values) > 1 else None,
            "median": float(np.median(values)) if values else None,
            "ci95_bootstrap_mean": bootstrap_mean(values, rng),
        }
    return result


def paired_deltas(full_rows, other_rows, rng):
    full = {case_key(row): row for row in full_rows}
    other = {case_key(row): row for row in other_rows}
    keys = sorted(set(full) & set(other))
    result = {"paired_n": len(keys), "missing_from_full": len(set(other) - set(full)), "missing_from_ablation": len(set(full) - set(other)), "metrics": {}}
    for metric in BINARY_METRICS + CONTINUOUS_METRICS:
        deltas = []
        for key in keys:
            a = safe_number(full[key], metric)
            b = safe_number(other[key], metric)
            if a is not None and b is not None:
                deltas.append(a - b)
        benefits = [-value if metric in LOWER_IS_BETTER else value for value in deltas]
        result["metrics"][metric] = {
            "n": len(deltas),
            "full_minus_ablation_mean": float(np.mean(deltas)) if deltas else None,
            "ci95_bootstrap": bootstrap_mean(deltas, rng),
            "full_better": int(sum(value > 0 for value in benefits)),
            "ties": int(sum(value == 0 for value in benefits)),
            "full_worse": int(sum(value < 0 for value in benefits)),
            "higher_is_better": metric not in LOWER_IS_BETTER,
        }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default="outputs/tits_dynamic_graph_expanded/randomized_attribution_20260710")
    parser.add_argument("--full", default="dnq_dlc_full")
    parser.add_argument("--output-dir", default="")
    args = parser.parse_args()
    root = Path(args.root)
    out = Path(args.output_dir) if args.output_dir else root / "aggregate"
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    invalid = []
    for path in sorted(root.glob("**/summaries/*.summary.json")):
        try:
            row = json.loads(path.read_text(encoding="utf-8"))
            row["source_path"] = str(path)
            if row.get("scenario_randomized") is not True:
                invalid.append({"path": str(path), "reason": "scenario_randomized is not true"})
            else:
                rows.append(row)
        except (OSError, json.JSONDecodeError) as exc:
            invalid.append({"path": str(path), "reason": str(exc)})
    grouped = defaultdict(list)
    stratified = defaultdict(list)
    for row in rows:
        grouped[row["algorithm"]].append(row)
        stratum = f"{Path(str(row.get('track_path', 'unknown'))).stem}|N={int(row['num_agents'])}"
        stratified[(row["algorithm"], stratum)].append(row)
    rng = np.random.default_rng(20260710)
    algorithm_summaries = {name: summarize(items, rng) for name, items in sorted(grouped.items())}
    stratified_summaries = {
        f"{algorithm}|{stratum}": summarize(items, rng)
        for (algorithm, stratum), items in sorted(stratified.items())
    }
    full_rows = grouped.get(args.full, [])
    paired = {
        name: paired_deltas(full_rows, items, rng)
        for name, items in sorted(grouped.items())
        if name != args.full
    }
    integrity_issues = [issue for row in rows for issue in control_issues(row)]
    report = {
        "root": str(root),
        "protocol": "all randomized summaries included; paired by track, N, and seed",
        "row_count": len(rows),
        "invalid_count": len(invalid),
        "invalid": invalid,
        "control_integrity_issue_count": len(integrity_issues),
        "control_integrity_issues": integrity_issues,
        "full_algorithm": args.full,
        "algorithm_summaries": algorithm_summaries,
        "stratified_summaries": stratified_summaries,
        "paired_full_minus_ablation": paired,
    }
    (out / "randomized_attribution_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    fields = ["algorithm", "track_path", "num_agents", "seed"] + BINARY_METRICS + CONTINUOUS_METRICS + ["source_path"]
    with (out / "randomized_attribution_rows.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fields})

    lines = [
        "# Randomized Attribution Report",
        "",
        f"- Included summaries: {len(rows)}",
        f"- Invalid summaries: {len(invalid)}",
        f"- Full method: `{args.full}`",
        "",
        "| algorithm | n | unique signatures | success (95% Wilson CI) | elegant | grass | contact | rank gain |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for name, item in algorithm_summaries.items():
        success = item["overtake_success_rate"]
        ci = success["ci95_wilson"]
        ci_text = "NA" if ci[0] is None else f"{success['mean']:.3f} [{ci[0]:.3f}, {ci[1]:.3f}]"
        lines.append(
            f"| {name} | {item['n']} | {item['unique_metric_signature_count']} | {ci_text} | "
            f"{item['elegant_overtake_rate']['mean']:.3f} | {item['target_grass_rate']['mean']:.3f} | "
            f"{item['collision_or_contact_proxy']['mean']:.3f} | {item['rank_gain']['mean']:.3f} |"
        )
    lines.extend(["", "Paired effects are defined as full minus ablation and are stored in the JSON report.", ""])
    (out / "randomized_attribution_report.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"report": str(out / "randomized_attribution_report.json"), "rows": len(rows), "invalid": len(invalid)}, indent=2))


if __name__ == "__main__":
    main()
