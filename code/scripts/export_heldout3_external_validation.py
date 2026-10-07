#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def method_passes(suite, method):
    return {
        int(row["seed"]): row["validation_status"] == "PASS"
        for row in suite["rows"]
        if row["method"] == method
    }


def build_report(root):
    suites = {
        "lane_base_only": method_passes(load_json(root / "evaluations/heldout3_multiseed_suite/multiseed_suite_summary.json"), "lane_base_only"),
        "overtake_base_only": method_passes(load_json(root / "evaluations/heldout3_multiseed_suite/multiseed_suite_summary.json"), "overtake_base_only"),
        "graph_adaptive_shield": method_passes(load_json(root / "evaluations/heldout3_adaptive_suite/multiseed_suite_summary.json"), "graph_adaptive_shield"),
        "expert_gate_only": method_passes(load_json(root / "evaluations/heldout3_expert_gate_suite/multiseed_suite_summary.json"), "expert_gate_only"),
        "dagger_v2_graph_expert_gate_shield": method_passes(load_json(root / "evaluations/heldout3_graph_dagger_recovery_v2_suite/multiseed_suite_summary.json"), "graph_expert_gate_shield"),
        "dagger_v2_graph_expert_gate_more_graph": method_passes(load_json(root / "evaluations/heldout3_dagger_v2_expert_more_graph_suite/multiseed_suite_summary.json"), "graph_expert_gate_shield_more_graph"),
    }
    selector = load_json(root / "tables/portfolio_probe_selector_1200_heldout3_expanded.json")
    learned = load_json(root / "tables/learned_selector_report.json")
    primary = learned["variants"][learned["primary_variant"]]["external_heldout3"]

    seeds = sorted(next(iter(suites.values())).keys())
    rows = []
    for seed in seeds:
        passing = [method for method, status_by_seed in suites.items() if status_by_seed.get(seed)]
        selector_decision = next(row for row in selector["decisions"] if int(row["seed"]) == seed)
        learned_decision = next(
            row
            for row in learned["variants"][learned["primary_variant"]]["external_heldout3_decisions"]
            if int(row["seed"]) == seed
        )
        rows.append(
            {
                "seed": seed,
                "passing_methods": passing,
                "oracle_status": "PASS" if passing else "FAIL",
                "expanded_selector_method": selector_decision["selected_method"],
                "expanded_selector_status": selector_decision["selected_full_status"],
                "learned_selector_method": learned_decision["selected_method"],
                "learned_selector_status": learned_decision["selected_status"],
            }
        )

    method_summary = {
        method: {
            "pass_count": sum(status.values()),
            "n": len(status),
            "pass_seeds": [seed for seed, ok in sorted(status.items()) if ok],
        }
        for method, status in suites.items()
    }
    return {
        "root": str(root),
        "seeds": seeds,
        "method_summary": method_summary,
        "oracle": {
            "pass_count": sum(row["oracle_status"] == "PASS" for row in rows),
            "n": len(rows),
            "candidate_gap_seeds": [row["seed"] for row in rows if row["oracle_status"] != "PASS"],
        },
        "expanded_selector": {
            "pass_count": selector["pass_count"],
            "n": selector["n"],
            "oracle_pass_count": selector["oracle_pass_count"],
            "failed_seeds": [
                int(row["seed"])
                for row in selector["decisions"]
                if row["selected_full_status"] != "PASS"
            ],
        },
        "learned_selector_primary": {
            "variant": learned["primary_variant"],
            "pass_count": primary["pass_count"],
            "n": primary["n"],
            "oracle_pass_count": primary["oracle_pass_count"],
            "failed_seeds": primary["failed_seeds"],
        },
        "rows": rows,
        "interpretation": (
            "Heldout3 is a disjoint external validation batch. It shows a substantial generalization boundary: "
            "the expanded candidate oracle is 8/10, but the expanded online selector and the exploratory "
            "feature-only learned selector both reach only 4/10. The heldout2 learned-selector improvement "
            "therefore must not be treated as robust external generalization."
        ),
    }


def write_csv(report, path):
    with path.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "seed",
            "passing_methods",
            "oracle_status",
            "expanded_selector_method",
            "expanded_selector_status",
            "learned_selector_method",
            "learned_selector_status",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in report["rows"]:
            writer.writerow({**row, "passing_methods": ";".join(row["passing_methods"])})


def write_markdown(report, path):
    lines = [
        "# Heldout3 External Validation",
        "",
        report["interpretation"],
        "",
        "## Summary",
        "",
        f"- Seeds: {', '.join(map(str, report['seeds']))}",
        f"- Candidate oracle: {report['oracle']['pass_count']}/{report['oracle']['n']}",
        f"- Candidate-gap seeds: {', '.join(map(str, report['oracle']['candidate_gap_seeds'])) or 'none'}",
        f"- Expanded online selector: {report['expanded_selector']['pass_count']}/{report['expanded_selector']['n']}",
        f"- Learned selector primary ({report['learned_selector_primary']['variant']}): {report['learned_selector_primary']['pass_count']}/{report['learned_selector_primary']['n']}",
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
            "## Seed-level External Validation",
            "",
            "| seed | passing candidates | expanded selector | expanded status | learned selector | learned status |",
            "|---:|---|---|---|---|---|",
        ]
    )
    for row in report["rows"]:
        lines.append(
            f"| {row['seed']} | {', '.join(row['passing_methods']) or 'none'} | "
            f"{row['expanded_selector_method']} | {row['expanded_selector_status']} | "
            f"{row['learned_selector_method']} | {row['learned_selector_status']} |"
        )
    lines.extend(
        [
            "",
            "## Reporting Boundary",
            "",
            "- Heldout3 was not used for candidate design, selector distillation, or learned-selector training.",
            "- The heldout3 result is negative external validation and should be reported alongside heldout2.",
            "- Do not claim broad robustness evidence from heldout1/heldout2 without this heldout3 boundary.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export heldout3 external validation report.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    report = build_report(root)
    out_json = root / "tables" / "heldout3_external_validation.json"
    out_md = root / "tables" / "heldout3_external_validation.md"
    out_csv = root / "tables" / "heldout3_external_validation_rows.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv)}, indent=2))


if __name__ == "__main__":
    main()
