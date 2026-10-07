#!/usr/bin/env python
"""Summarize RL baselines by training seed, without pseudo-replicating evaluation cases."""

import argparse
import csv
import json
import re
from collections import defaultdict
from pathlib import Path

import numpy as np


METRICS = [
    "overtake_success_rate",
    "elegant_overtake_rate",
    "target_grass_rate",
    "rank_gain",
    "target_progress",
    "collision_or_contact_proxy",
]


def identity(algorithm):
    match = re.match(r"(ppo|sac|td3)_seed(\d+)$", algorithm)
    if match:
        return match.group(1).upper(), match.group(2)
    labels = {
        "dnq_dlc_full": "DNQ-DLC",
        "rule_expert_gate": "Rule expert",
        "rule_safety_gate": "Safety rule",
    }
    return labels.get(algorithm, algorithm), "fixed"


def safe(row, metric):
    value = row.get(metric)
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return value if np.isfinite(value) else None


def metric_means(rows):
    result = {}
    for metric in METRICS:
        values = [safe(row, metric) for row in rows]
        values = [value for value in values if value is not None]
        result[metric] = float(np.mean(values)) if values else None
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default="outputs/tits_dynamic_graph_expanded/rl_multiseed_randomized_eval_20260714")
    parser.add_argument("--output-dir", default="")
    args = parser.parse_args()
    root = Path(args.root)
    output = Path(args.output_dir) if args.output_dir else root / "aggregate_rl"
    output.mkdir(parents=True, exist_ok=True)
    rows = []
    invalid = []
    for path in sorted(root.glob("**/summaries/*.summary.json")):
        try:
            row = json.loads(path.read_text(encoding="utf-8"))
            if row.get("scenario_randomized") is not True:
                invalid.append({"path": str(path), "reason": "scenario_randomized is not true"})
                continue
            family, training_seed = identity(row["algorithm"])
            row["family"] = family
            row["training_seed"] = training_seed
            row["source_path"] = str(path)
            rows.append(row)
        except (OSError, json.JSONDecodeError, KeyError) as exc:
            invalid.append({"path": str(path), "reason": str(exc)})

    checkpoints = defaultdict(list)
    for row in rows:
        checkpoints[(row["family"], row["training_seed"])].append(row)
    checkpoint_reports = {
        f"{family}|{seed}": {
            "family": family,
            "training_seed": seed,
            "evaluation_cases": len(items),
            "metrics": metric_means(items),
        }
        for (family, seed), items in sorted(checkpoints.items())
    }
    family_reports = {}
    for family in sorted({row["family"] for row in rows}):
        reports = [item for item in checkpoint_reports.values() if item["family"] == family]
        summary = {"training_seed_count": len(reports), "evaluation_cases_per_seed": sorted({item["evaluation_cases"] for item in reports}), "metrics": {}}
        for metric in METRICS:
            values = [item["metrics"][metric] for item in reports if item["metrics"][metric] is not None]
            summary["metrics"][metric] = {
                "mean_across_training_seeds": float(np.mean(values)) if values else None,
                "min_training_seed": float(np.min(values)) if values else None,
                "max_training_seed": float(np.max(values)) if values else None,
                "values": values,
            }
        family_reports[family] = summary

    dnq = {int(row["seed"]): row for row in rows if row["family"] == "DNQ-DLC"}
    paired = {}
    for key, report in checkpoint_reports.items():
        if report["family"] == "DNQ-DLC":
            continue
        family, training_seed = key.split("|", 1)
        items = checkpoints[(family, training_seed)]
        baseline = {int(row["seed"]): row for row in items}
        common = sorted(set(dnq) & set(baseline))
        metric_report = {}
        for metric in METRICS:
            deltas = []
            for seed in common:
                a, b = safe(dnq[seed], metric), safe(baseline[seed], metric)
                if a is not None and b is not None:
                    deltas.append(a - b)
            metric_report[metric] = {"paired_n": len(deltas), "dnq_minus_baseline_mean": float(np.mean(deltas)) if deltas else None}
        paired[key] = metric_report

    payload = {
        "root": str(root),
        "protocol": "Each RL family is summarized first within each independent training seed, then across three training-seed means. Evaluation cases are not treated as independent training replicates.",
        "row_count": len(rows),
        "invalid": invalid,
        "checkpoint_reports": checkpoint_reports,
        "family_reports": family_reports,
        "paired_dnq_minus_each_checkpoint": paired,
    }
    (output / "rl_multiseed_report.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    fields = ["algorithm", "family", "training_seed", "seed", "num_agents"] + METRICS + ["source_path"]
    with (output / "rl_multiseed_rows.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fields})
    lines = ["# RL Multi-seed Randomized Evaluation", "", f"- Valid summaries: {len(rows)}", f"- Invalid summaries: {len(invalid)}", "", "| family | training seeds | cases/seed | success mean [range] | desirable mean [range] | grass mean [range] | rank gain mean [range] |", "|---|---:|---|---|---|---|---|"]
    for family, report in family_reports.items():
        def cell(metric):
            item = report["metrics"][metric]
            return f"{item['mean_across_training_seeds']:.3f} [{item['min_training_seed']:.3f}, {item['max_training_seed']:.3f}]"
        lines.append(f"| {family} | {report['training_seed_count']} | {report['evaluation_cases_per_seed']} | {cell('overtake_success_rate')} | {cell('elegant_overtake_rate')} | {cell('target_grass_rate')} | {cell('rank_gain')} |")
    lines.extend(["", "Ranges are across independent training seeds, not confidence intervals.", ""])
    (output / "rl_multiseed_report.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"report": str(output / "rl_multiseed_report.json"), "rows": len(rows), "invalid": len(invalid)}, indent=2))


if __name__ == "__main__":
    main()
