#!/usr/bin/env python
import argparse
import csv
import json
import math
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def wilson_ci(successes, n, z=1.959963984540054):
    if n <= 0:
        return [None, None]
    p = successes / n
    denom = 1.0 + z * z / n
    center = (p + z * z / (2.0 * n)) / denom
    half = z * math.sqrt((p * (1.0 - p) + z * z / (4.0 * n)) / n) / denom
    return [max(0.0, center - half), min(1.0, center + half)]


def ci_width(successes, n):
    low, high = wilson_ci(successes, n)
    return high - low


def min_successes_for_lower_bound(n, target_lower):
    for successes in range(n + 1):
        if wilson_ci(successes, n)[0] >= target_lower:
            return successes
    return None


def sign_test_pvalue(successes, n, null_p=0.5):
    lower = sum(math.comb(n, k) * (null_p**k) * ((1.0 - null_p) ** (n - k)) for k in range(0, successes + 1))
    upper = sum(math.comb(n, k) * (null_p**k) * ((1.0 - null_p) ** (n - k)) for k in range(successes, n + 1))
    return min(1.0, 2.0 * min(lower, upper))


def make_stage_rows(stats):
    rows = []
    for row in stats["stage_statistics"]:
        selector_width = row["selector_ci95_high"] - row["selector_ci95_low"]
        oracle_width = row["oracle_ci95_high"] - row["oracle_ci95_low"]
        rows.append(
            {
                "id": f"{row['heldout']}_{row['stage']}",
                "heldout": row["heldout"],
                "stage": row["stage"],
                "n": row["n"],
                "selector_result": f"{row['selector_pass_count']}/{row['n']}",
                "selector_pass_rate": row["selector_pass_rate"],
                "selector_ci95_low": row["selector_ci95_low"],
                "selector_ci95_high": row["selector_ci95_high"],
                "selector_ci95_width": selector_width,
                "oracle_result": f"{row['oracle_pass_count']}/{row['n']}",
                "oracle_pass_rate": row["oracle_pass_rate"],
                "oracle_ci95_low": row["oracle_ci95_low"],
                "oracle_ci95_high": row["oracle_ci95_high"],
                "oracle_ci95_width": oracle_width,
                "selector_oracle_gap_count": row["selector_oracle_gap_count"],
                "claim_support": (
                    "descriptive_only"
                    if row["n"] <= 10 or selector_width > 0.30
                    else "stronger_estimation"
                ),
            }
        )
    return rows


def make_planning_rows():
    rows = []
    for n in [10, 20, 30, 50, 75, 100, 150, 200]:
        for assumed_rate in [0.6, 0.7, 0.8, 0.9]:
            successes = round(assumed_rate * n)
            low, high = wilson_ci(successes, n)
            rows.append(
                {
                    "n": n,
                    "assumed_pass_rate": assumed_rate,
                    "successes": successes,
                    "wilson_ci95_low": low,
                    "wilson_ci95_high": high,
                    "wilson_ci95_width": high - low,
                    "sign_test_p_vs_half": sign_test_pvalue(successes, n),
                    "interpretation": (
                        "usable_for_precision"
                        if high - low <= 0.20
                        else "wide_interval"
                    ),
                }
            )
    return rows


def make_threshold_rows():
    rows = []
    for n in [10, 20, 30, 50, 75, 100, 150, 200]:
        for target_lower in [0.60, 0.70, 0.80]:
            successes = min_successes_for_lower_bound(n, target_lower)
            rows.append(
                {
                    "n": n,
                    "target_wilson_lower_bound": target_lower,
                    "minimum_successes": successes,
                    "minimum_observed_rate": None if successes is None else successes / n,
                    "meaning": (
                        f"At least this many strict PASS seeds are needed for the Wilson lower 95% bound to reach {target_lower:.2f}."
                    ),
                }
            )
    return rows


def build_brief(root):
    stats = load_json(root / "tables" / "cross_heldout_statistical_supplement.json")
    boundary = load_json(root / "materials" / "EXTERNAL_VALIDITY_BOUNDARY_AUDIT.json")
    negative = load_json(root / "materials" / "NEGATIVE_RESULTS_FAILURE_REGISTER.json")
    stat_plan = load_json(root / "materials" / "STATISTICAL_ANALYSIS_PLAN.json")
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")

    stage_rows = make_stage_rows(stats)
    planning_rows = make_planning_rows()
    threshold_rows = make_threshold_rows()
    aggregate = stats["aggregate_expanded_or_later"]
    aggregate_width = aggregate["selector_ci95_high"] - aggregate["selector_ci95_low"]
    stage_widths = [row["selector_ci95_width"] for row in stage_rows]
    planning_80 = [row for row in planning_rows if row["assumed_pass_rate"] == 0.8]
    n_for_80pct_width = next((row["n"] for row in planning_80 if row["wilson_ci95_width"] <= 0.20), None)
    n_for_lower_70_at_80 = next(
        (
            row["n"]
            for row in threshold_rows
            if row["target_wilson_lower_bound"] == 0.70
            and row["minimum_observed_rate"] is not None
            and row["minimum_observed_rate"] <= 0.80
        ),
        None,
    )

    return {
        "root": str(root),
        "title": "Sample-size and statistical-sensitivity brief",
        "purpose": (
            "Explain what the current seed counts can and cannot support statistically, and give planning targets "
            "for larger-N validation without changing the saved experimental outcomes."
        ),
        "summary": {
            "stage_count": len(stage_rows),
            "per_stage_n": 10,
            "expanded_or_later_n": aggregate["n"],
            "expanded_or_later_selector": f"{aggregate['selector_pass_count']}/{aggregate['n']}",
            "expanded_or_later_selector_ci95_width": aggregate_width,
            "widest_stage_selector_ci95_width": max(stage_widths),
            "n_for_assumed_80pct_width_le_0_20": n_for_80pct_width,
            "n_for_wilson_lower_0_70_at_80pct_or_better": n_for_lower_70_at_80,
            "publication_verification_status": verification["summary"]["status"],
            "artifact_provenance": verification["summary"]["artifact_provenance"],
        },
        "stage_rows": stage_rows,
        "planning_rows": planning_rows,
        "threshold_rows": threshold_rows,
        "linked_evidence": {
            "statistical_supplement": "tables/cross_heldout_statistical_supplement.md",
            "statistical_plan": "materials/STATISTICAL_ANALYSIS_PLAN.md",
            "external_validity_boundary": "materials/EXTERNAL_VALIDITY_BOUNDARY_AUDIT.md",
            "negative_results_register": "materials/NEGATIVE_RESULTS_FAILURE_REGISTER.md",
        },
        "claim_boundary": (
            "Current n=10 held-out stages and the mixed 50-seed expanded-or-later aggregate are suitable for "
            "descriptive uncertainty reporting and failure decomposition, not confirmatory robustness claims."
        ),
        "next_experiment_guidance": (
            "For a future robustness-oriented claim, freeze the selector/candidate design before evaluation and "
            f"run larger held-out batches. The planning grid shows that n={n_for_80pct_width} is the first listed "
            "size where an assumed 80% pass rate has Wilson width at or below 0.20, and "
            f"n={n_for_lower_70_at_80} is the first listed size where an observed rate near 80% can give a Wilson "
            "lower bound above 0.70."
        ),
        "source_interpretations": {
            "statistical_plan": stat_plan["multiplicity_policy"],
            "external_validity_boundary": boundary["interpretation"],
            "negative_results_register": negative["interpretation"],
        },
    }


def write_csv(report, materials):
    stage_csv = materials / "SAMPLE_SIZE_SENSITIVITY_STAGE_ROWS.csv"
    planning_csv = materials / "SAMPLE_SIZE_SENSITIVITY_PLANNING_GRID.csv"
    threshold_csv = materials / "SAMPLE_SIZE_SENSITIVITY_THRESHOLD_GRID.csv"

    with stage_csv.open("w", newline="", encoding="utf-8") as handle:
        fields = [
            "id",
            "heldout",
            "stage",
            "n",
            "selector_result",
            "selector_pass_rate",
            "selector_ci95_low",
            "selector_ci95_high",
            "selector_ci95_width",
            "oracle_result",
            "oracle_pass_rate",
            "oracle_ci95_low",
            "oracle_ci95_high",
            "oracle_ci95_width",
            "selector_oracle_gap_count",
            "claim_support",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(report["stage_rows"])

    with planning_csv.open("w", newline="", encoding="utf-8") as handle:
        fields = [
            "n",
            "assumed_pass_rate",
            "successes",
            "wilson_ci95_low",
            "wilson_ci95_high",
            "wilson_ci95_width",
            "sign_test_p_vs_half",
            "interpretation",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(report["planning_rows"])

    with threshold_csv.open("w", newline="", encoding="utf-8") as handle:
        fields = ["n", "target_wilson_lower_bound", "minimum_successes", "minimum_observed_rate", "meaning"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(report["threshold_rows"])

    return stage_csv, planning_csv, threshold_csv


def write_markdown(report, path):
    lines = [
        "# Sample-size and Statistical-sensitivity Brief",
        "",
        report["purpose"],
        "",
        report["claim_boundary"],
        "",
        report["next_experiment_guidance"],
        "",
        "## Summary",
        "",
    ]
    for key, value in report["summary"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Current Stage Precision",
            "",
            "| id | selector | selector 95% CI width | oracle | oracle 95% CI width | gap | claim support |",
            "|---|---:|---:|---:|---:|---:|---|",
        ]
    )
    for row in report["stage_rows"]:
        lines.append(
            f"| {row['id']} | {row['selector_result']} | {row['selector_ci95_width']:.3f} | "
            f"{row['oracle_result']} | {row['oracle_ci95_width']:.3f} | {row['selector_oracle_gap_count']} | "
            f"{row['claim_support']} |"
        )
    lines.extend(
        [
            "",
            "## Planning Grid Excerpt",
            "",
            "| n | assumed pass rate | successes | Wilson 95% CI | width | sign-test p vs 0.5 |",
            "|---:|---:|---:|---|---:|---:|",
        ]
    )
    for row in report["planning_rows"]:
        if row["assumed_pass_rate"] != 0.8:
            continue
        lines.append(
            f"| {row['n']} | {row['assumed_pass_rate']:.2f} | {row['successes']} | "
            f"[{row['wilson_ci95_low']:.3f}, {row['wilson_ci95_high']:.3f}] | "
            f"{row['wilson_ci95_width']:.3f} | {row['sign_test_p_vs_half']:.6f} |"
        )
    lines.extend(
        [
            "",
            "## Minimum Successes for Wilson Lower Bounds",
            "",
            "| n | target lower bound | minimum successes | minimum observed rate |",
            "|---:|---:|---:|---:|",
        ]
    )
    for row in report["threshold_rows"]:
        if row["target_wilson_lower_bound"] != 0.70:
            continue
        lines.append(
            f"| {row['n']} | {row['target_wilson_lower_bound']:.2f} | {row['minimum_successes']} | "
            f"{row['minimum_observed_rate']:.3f} |"
        )
    lines.extend(["", "## Linked Evidence", ""])
    for key, value in report["linked_evidence"].items():
        lines.append(f"- {key}: `{value}`")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export sample-size and statistical-sensitivity brief.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_brief(root)
    out_json = materials / "SAMPLE_SIZE_SENSITIVITY_BRIEF.json"
    out_md = materials / "SAMPLE_SIZE_SENSITIVITY_BRIEF.md"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    stage_csv, planning_csv, threshold_csv = write_csv(report, materials)
    print(
        json.dumps(
            {
                "json": str(out_json),
                "markdown": str(out_md),
                "stage_csv": str(stage_csv),
                "planning_csv": str(planning_csv),
                "threshold_csv": str(threshold_csv),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
