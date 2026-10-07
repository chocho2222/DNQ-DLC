#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path

import numpy as np


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def wilson_ci(k, n, z=1.96):
    if n <= 0:
        return [None, None]
    phat = k / n
    denom = 1.0 + z * z / n
    centre = (phat + z * z / (2 * n)) / denom
    half = z * np.sqrt((phat * (1.0 - phat) + z * z / (4.0 * n)) / n) / denom
    return [float(max(0.0, centre - half)), float(min(1.0, centre + half))]


def suite_method_summary(root, rel_path):
    suite = load_json(root / rel_path)
    out = {}
    for method in suite["methods"]:
        rows = [row for row in suite["rows"] if row["method"] == method]
        n = len(rows)
        k = sum(row["validation_status"] == "PASS" for row in rows)
        out[method] = {
            "n": n,
            "pass_count": k,
            "pass_rate": k / n if n else None,
            "ci95": wilson_ci(k, n),
            "passed_seeds": [row["seed"] for row in rows if row["validation_status"] == "PASS"],
        }
    return out


def selector_summary(root, rel_path):
    report = load_json(root / rel_path)
    return {
        "n": report["n"],
        "pass_count": report["pass_count"],
        "pass_rate": report["pass_rate"],
        "ci95": wilson_ci(report["pass_count"], report["n"]),
        "oracle_pass_count": report["oracle_pass_count"],
        "oracle_pass_rate": report["oracle_pass_rate"],
        "oracle_ci95": wilson_ci(report["oracle_pass_count"], report["n"]),
        "selected_methods": [row["selected_method"] for row in report["decisions"]],
        "failed_seeds": [
            {
                "seed": row["seed"],
                "selected": row["selected_method_key"],
                "oracle": row["oracle_method"],
                "oracle_status": row["oracle_status"],
            }
            for row in report["decisions"]
            if row["selected_full_status"] != "PASS"
        ],
    }


def build_report(root):
    sets = {
        "heldout1": {
            "seeds": [47, 53, 59, 61, 67, 71, 73, 79, 83, 89],
            "suites": {
                "main": "evaluations/heldout_multiseed_suite/multiseed_suite_summary.json",
                "adaptive": "evaluations/heldout_adaptive_suite/multiseed_suite_summary.json",
                "expert": "evaluations/heldout_expert_gate_suite/multiseed_suite_summary.json",
                "dagger_v2": "evaluations/heldout_graph_dagger_recovery_v2_suite/multiseed_suite_summary.json",
            },
            "selector": "tables/portfolio_probe_selector_1200_heldout_dagger_v2.json",
        },
        "heldout2": {
            "seeds": [97, 101, 103, 107, 109, 113, 127, 131, 137, 139],
            "suites": {
                "main": "evaluations/heldout2_multiseed_suite/multiseed_suite_summary.json",
                "adaptive": "evaluations/heldout2_adaptive_suite/multiseed_suite_summary.json",
                "expert": "evaluations/heldout2_expert_gate_suite/multiseed_suite_summary.json",
                "dagger_v2": "evaluations/heldout2_graph_dagger_recovery_v2_suite/multiseed_suite_summary.json",
            },
            "selector": "tables/portfolio_probe_selector_1200_heldout2_dagger_v2.json",
        },
    }
    method_rows = []
    set_reports = {}
    for set_name, spec in sets.items():
        method_summaries = {}
        for suite_name, rel_path in spec["suites"].items():
            for method, summary in suite_method_summary(root, rel_path).items():
                key = f"{suite_name}:{method}"
                method_summaries[key] = summary
                method_rows.append(
                    {
                        "set": set_name,
                        "method": key,
                        "n": summary["n"],
                        "pass_count": summary["pass_count"],
                        "pass_rate": summary["pass_rate"],
                        "ci95_low": summary["ci95"][0],
                        "ci95_high": summary["ci95"][1],
                        "passed_seeds": ",".join(str(seed) for seed in summary["passed_seeds"]),
                    }
                )
        selector = selector_summary(root, spec["selector"])
        set_reports[set_name] = {
            "seeds": spec["seeds"],
            "method_summaries": method_summaries,
            "selector": selector,
            "interpretation": (
                "The first held-out set supports the expanded online selector result, whereas the second "
                "held-out set exposes substantial distributional sensitivity. This should be reported as "
                "an external generalization boundary rather than hidden as a failed repeat."
                if set_name == "heldout2"
                else "The expanded online selector reaches complete coverage on this held-out set."
            ),
        }
    return {
        "root": str(root),
        "sets": set_reports,
        "method_rows": method_rows,
        "overall_interpretation": (
            "Across two disjoint held-out sets, the five-candidate online selector is promising but not yet "
            "publication-grade robust: it reaches 10/10 on heldout1 and 5/10 on heldout2, while the heldout2 "
            "oracle over the same candidate pool is only 7/10. The remaining bottleneck is both candidate "
            "coverage and selector calibration."
        ),
    }


def write_outputs(report, root, prefix):
    table_dir = root / "tables"
    table_dir.mkdir(parents=True, exist_ok=True)
    out_json = table_dir / f"{prefix}.json"
    out_csv = table_dir / f"{prefix}_method_rows.csv"
    out_md = table_dir / f"{prefix}.md"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    with out_csv.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = ["set", "method", "n", "pass_count", "pass_rate", "ci95_low", "ci95_high", "passed_seeds"]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in report["method_rows"]:
            writer.writerow(row)
    lines = [
        "# Held-out Generalization Report",
        "",
        "## Selector Summary",
        "",
        "| set | n | selector pass | 95% CI | oracle pass | oracle 95% CI | failed seeds |",
        "|---|---:|---:|---|---:|---|---|",
    ]
    for set_name, item in report["sets"].items():
        selector = item["selector"]
        ci = selector["ci95"]
        oci = selector["oracle_ci95"]
        failed = ", ".join(str(row["seed"]) for row in selector["failed_seeds"]) or "none"
        lines.append(
            f"| {set_name} | {selector['n']} | {selector['pass_count']} | "
            f"[{ci[0]:.3f}, {ci[1]:.3f}] | {selector['oracle_pass_count']} | "
            f"[{oci[0]:.3f}, {oci[1]:.3f}] | {failed} |"
        )
    lines.extend(
        [
            "",
            "## Method Summary",
            "",
            "| set | method | pass | 95% CI | passed seeds |",
            "|---|---|---:|---|---|",
        ]
    )
    for row in report["method_rows"]:
        lines.append(
            f"| {row['set']} | {row['method']} | {row['pass_count']}/{row['n']} | "
            f"[{row['ci95_low']:.3f}, {row['ci95_high']:.3f}] | {row['passed_seeds'] or 'none'} |"
        )
    lines.extend(["", "## Interpretation", "", report["overall_interpretation"], ""])
    for set_name, item in report["sets"].items():
        lines.extend([f"### {set_name}", "", item["interpretation"], ""])
    out_md.write_text("\n".join(lines), encoding="utf-8")
    return {"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv)}


def main():
    parser = argparse.ArgumentParser(description="Export cross-held-out generalization summary.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    parser.add_argument("--prefix", default="heldout_generalization")
    args = parser.parse_args()
    root = Path(args.root)
    report = build_report(root)
    print(json.dumps(write_outputs(report, root, args.prefix), indent=2))


if __name__ == "__main__":
    main()
