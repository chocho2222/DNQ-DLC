#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


METHOD_SUITES = {
    "lane_base_only": ("heldout4_multiseed_suite", "lane_base_only"),
    "overtake_base_only": ("heldout4_multiseed_suite", "overtake_base_only"),
    "graph_adaptive_shield": ("heldout4_adaptive_suite", "graph_adaptive_shield"),
    "expert_gate_only": ("heldout4_expert_gate_suite", "expert_gate_only"),
    "dagger_v2_graph_expert_gate_shield": ("heldout4_graph_dagger_recovery_v2_suite", "graph_expert_gate_shield"),
    "dagger_v2_graph_expert_gate_more_graph": (
        "heldout4_dagger_v2_expert_more_graph_suite",
        "graph_expert_gate_shield_more_graph",
    ),
    "heldout3_traffic_adaptive_conservative": (
        "heldout4_traffic_adaptive_conservative_suite",
        "heldout3_traffic_adaptive_conservative",
    ),
}


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def suite_path(root, suite):
    return root / "evaluations" / suite / "multiseed_suite_summary.json"


def method_rows(summary, method):
    return [row for row in summary["rows"] if row["method"] == method]


def build_report(root):
    selector = load_json(root / "tables" / "portfolio_probe_selector_1200_heldout4_targeted_expanded.json")
    suites = {}
    for method, (suite, full_method) in METHOD_SUITES.items():
        suites[method] = method_rows(load_json(suite_path(root, suite)), full_method)

    seeds = sorted({int(row["seed"]) for rows in suites.values() for row in rows})
    method_summary = {}
    for method, rows in suites.items():
        pass_seeds = [int(row["seed"]) for row in rows if row["validation_status"] == "PASS"]
        method_summary[method] = {
            "pass_count": len(pass_seeds),
            "n": len(rows),
            "pass_seeds": sorted(pass_seeds),
        }

    selector_by_seed = {int(row["seed"]): row for row in selector["decisions"]}
    rows = []
    for seed in seeds:
        passing = [
            method
            for method, method_rows_ in suites.items()
            for row in method_rows_
            if int(row["seed"]) == seed and row["validation_status"] == "PASS"
        ]
        selected = selector_by_seed[seed]
        oracle_status = "PASS" if passing else "FAIL"
        selected_status = selected["selected_full_status"]
        rows.append(
            {
                "seed": seed,
                "passing_methods": passing,
                "oracle_status": oracle_status,
                "selected_method": selected["selected_method"],
                "selected_status": selected_status,
                "selector_miss": oracle_status == "PASS" and selected_status != "PASS",
                "candidate_gap": oracle_status != "PASS",
                "oracle_method": selected["oracle_method"],
            }
        )

    oracle_pass_count = sum(row["oracle_status"] == "PASS" for row in rows)
    selector_pass_count = sum(row["selected_status"] == "PASS" for row in rows)
    return {
        "root": str(root),
        "validation_set": "heldout4",
        "seed_policy": "pre-registered unused prime seeds after heldout3: 197,199,211,223,227,229,233,239,241,251",
        "seeds": seeds,
        "method_summary": method_summary,
        "selector": {
            "source": "tables/portfolio_probe_selector_1200_heldout4_targeted_expanded.json",
            "pass_count": selector_pass_count,
            "n": len(rows),
            "oracle_pass_count": selector["oracle_pass_count"],
            "selector_failed_seeds": [row["seed"] for row in rows if row["selected_status"] != "PASS"],
            "selector_miss_seeds": [row["seed"] for row in rows if row["selector_miss"]],
            "candidate_gap_seeds": [row["seed"] for row in rows if row["candidate_gap"]],
        },
        "oracle": {
            "pass_count": oracle_pass_count,
            "n": len(rows),
            "candidate_gap_seeds": [row["seed"] for row in rows if row["candidate_gap"]],
        },
        "rows": rows,
        "interpretation": (
            "Heldout4 is a new external-validation batch selected after heldout3-targeted repair but not used "
            "to design the candidate policies or tune the online selector. The targeted seven-candidate online "
            "selector recovers to 6/10, while the candidate oracle is 8/10. This supports partial transfer of "
            "the expanded portfolio but still rejects a broad robustness claim: seeds 197 and 211 are selector "
            "misses, and seeds 233 and 239 remain candidate-coverage gaps under the tested pool."
        ),
    }


def write_csv(report, path):
    fields = [
        "seed",
        "passing_methods",
        "oracle_status",
        "selected_method",
        "selected_status",
        "selector_miss",
        "candidate_gap",
        "oracle_method",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in report["rows"]:
            writer.writerow({**row, "passing_methods": ";".join(row["passing_methods"])})


def write_markdown(report, path):
    selector = report["selector"]
    oracle = report["oracle"]
    lines = [
        "# Heldout4 External Validation",
        "",
        report["interpretation"],
        "",
        "## Summary",
        "",
        f"- Seeds: {', '.join(map(str, report['seeds']))}",
        f"- Candidate oracle: {oracle['pass_count']}/{oracle['n']}",
        f"- Targeted seven-candidate online selector: {selector['pass_count']}/{selector['n']}",
        f"- Selector miss seeds: {', '.join(map(str, selector['selector_miss_seeds'])) or 'none'}",
        f"- Candidate-gap seeds: {', '.join(map(str, oracle['candidate_gap_seeds'])) or 'none'}",
        "",
        "## Method Summary",
        "",
        "| method | pass | pass seeds |",
        "|---|---:|---|",
    ]
    for method, item in report["method_summary"].items():
        lines.append(f"| {method} | {item['pass_count']}/{item['n']} | {', '.join(map(str, item['pass_seeds'])) or 'none'} |")
    lines.extend(
        [
            "",
            "## Seed-Level Results",
            "",
            "| seed | passing methods | selected method | selected status | oracle method | error type |",
            "|---:|---|---|---|---|---|",
        ]
    )
    for row in report["rows"]:
        if row["candidate_gap"]:
            error = "candidate_gap"
        elif row["selector_miss"]:
            error = "selector_miss"
        elif row["selected_status"] == "PASS":
            error = "pass"
        else:
            error = "strict_fail"
        lines.append(
            f"| {row['seed']} | {', '.join(row['passing_methods']) or 'none'} | "
            f"{row['selected_method']} | {row['selected_status']} | {row['oracle_method']} | {error} |"
        )
    lines.extend(
        [
            "",
            "## Reporting Boundary",
            "",
            "- Heldout4 was not used to design candidate policies or tune the selector.",
            "- Heldout4 should be reported as external validation after heldout3-targeted repair.",
            "- Do not make a broad robustness claim: the selector remains below oracle and the oracle remains below 10/10.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export heldout4 external validation report.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    report = build_report(root)
    out_json = root / "tables" / "heldout4_external_validation.json"
    out_md = root / "tables" / "heldout4_external_validation.md"
    out_csv = root / "tables" / "heldout4_external_validation_rows.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv)}, indent=2))


if __name__ == "__main__":
    main()
