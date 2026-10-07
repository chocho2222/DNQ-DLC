#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def pass_seeds(summary):
    by_method = {}
    for row in summary["rows"]:
        by_method.setdefault(row["method"], set())
        if row["validation_status"] == "PASS":
            by_method[row["method"]].add(int(row["seed"]))
    return {method: sorted(seeds) for method, seeds in by_method.items()}


def method_summary(report, method):
    summaries = report["method_summaries"]
    if isinstance(summaries, dict):
        return summaries[method]
    for item in summaries:
        if item["method"] == method:
            return item
    raise KeyError(method)


def build_report(root):
    external = load_json(root / "tables" / "heldout3_external_validation.json")
    targeted_report = load_json(root / "tables" / "heldout3_targeted_recovery_suite_report.json")
    conservative_report = load_json(root / "tables" / "heldout3_targeted_recovery_conservative_traffic_suite_report.json")
    seed157_ablation = load_json(root / "tables" / "seed157_traffic_ablation.json")
    targeted_suite = load_json(root / "evaluations" / "heldout3_targeted_recovery_suite" / "multiseed_suite_summary.json")
    conservative_suite = load_json(
        root / "evaluations" / "heldout3_targeted_recovery_conservative_traffic_suite" / "multiseed_suite_summary.json"
    )

    base_pass = {int(seed): set() for seed in external["seeds"]}
    for method, summary in external["method_summary"].items():
        for seed in summary["pass_seeds"]:
            base_pass[int(seed)].add(method)

    targeted_pass = pass_seeds(targeted_suite)
    conservative_pass = pass_seeds(conservative_suite)
    expanded_pass = {seed: set(methods) for seed, methods in base_pass.items()}
    for method, seeds in targeted_pass.items():
        for seed in seeds:
            expanded_pass[seed].add(f"targeted:{method}")
    for method, seeds in conservative_pass.items():
        for seed in seeds:
            expanded_pass[seed].add(f"targeted_conservative_traffic:{method}")
    seed157 = int(seed157_ablation["seed"])
    for row in seed157_ablation["pass_rows"]:
        expanded_pass[seed157].add(f"seed157_traffic_ablation:{row['name']}")

    original_pass_seeds = sorted(seed for seed, methods in base_pass.items() if methods)
    expanded_pass_seeds = sorted(seed for seed, methods in expanded_pass.items() if methods)
    newly_covered = sorted(seed for seed in expanded_pass if not base_pass[seed] and expanded_pass[seed])
    remaining_gaps = sorted(seed for seed in expanded_pass if not expanded_pass[seed])

    targeted_rows = {(int(row["seed"]), row["method"]): row for row in targeted_suite["rows"]}
    conservative_rows = {(int(row["seed"]), row["method"]): row for row in conservative_suite["rows"]}
    methods = sorted(set(targeted_pass) | set(conservative_pass))
    rows = []
    for seed in external["seeds"]:
        for method in methods:
            targeted_row = targeted_rows.get((int(seed), method))
            conservative_row = conservative_rows.get((int(seed), method))
            rows.append(
                {
                    "seed": int(seed),
                    "method": method,
                    "original_passing_methods": ", ".join(sorted(base_pass[int(seed)])),
                    "targeted_status": targeted_row["validation_status"] if targeted_row else "not_run",
                    "targeted_progress": targeted_row.get("target_tile_progress") if targeted_row else None,
                    "targeted_grass": targeted_row.get("target_grass_rate") if targeted_row else None,
                    "targeted_rank": targeted_row.get("target_final_rank_by_tiles") if targeted_row else None,
                    "targeted_conservative_status": conservative_row["validation_status"] if conservative_row else "not_run",
                    "targeted_conservative_progress": conservative_row.get("target_tile_progress") if conservative_row else None,
                    "targeted_conservative_grass": conservative_row.get("target_grass_rate") if conservative_row else None,
                    "targeted_conservative_rank": conservative_row.get("target_final_rank_by_tiles") if conservative_row else None,
                    "expanded_oracle_status": "PASS" if expanded_pass[int(seed)] else "FAIL",
                }
            )

    return {
        "root": str(root),
        "original_oracle": {
            "pass_count": external["oracle"]["pass_count"],
            "n": external["oracle"]["n"],
            "pass_seeds": original_pass_seeds,
            "candidate_gap_seeds": external["oracle"]["candidate_gap_seeds"],
        },
        "new_candidates": {
            "heldout3_targeted_recovery": {
                "suite": "evaluations/heldout3_targeted_recovery_suite/multiseed_suite_summary.json",
                "methods": {
                    method: {
                        "pass_count": method_summary(targeted_report, method)["pass_count"],
                        "n": method_summary(targeted_report, method)["n"],
                        "pass_seeds": targeted_pass.get(method, []),
                    }
                    for method in methods
                },
            },
            "heldout3_targeted_recovery_conservative_traffic": {
                "suite": "evaluations/heldout3_targeted_recovery_conservative_traffic_suite/multiseed_suite_summary.json",
                "methods": {
                    method: {
                        "pass_count": method_summary(conservative_report, method)["pass_count"],
                        "n": method_summary(conservative_report, method)["n"],
                        "pass_seeds": conservative_pass.get(method, []),
                    }
                    for method in methods
                },
            },
            "seed157_traffic_ablation": {
                "suite": "evaluations/seed157_traffic_ablation",
                "pass_count": seed157_ablation["pass_count"],
                "n": seed157_ablation["n"],
                "best_pass_config": seed157_ablation["pass_rows"][0]["name"] if seed157_ablation["pass_rows"] else None,
                "pass_configs": [row["name"] for row in seed157_ablation["pass_rows"]],
            },
        },
        "expanded_oracle": {
            "pass_count": len(expanded_pass_seeds),
            "n": len(expanded_pass),
            "pass_seeds": expanded_pass_seeds,
            "newly_covered_seeds": newly_covered,
            "remaining_candidate_gap_seeds": remaining_gaps,
        },
        "rows": rows,
        "interpretation": (
            "Heldout3-targeted recovery candidates first raise the heldout3 candidate oracle from 8/10 to 9/10 "
            "by newly covering seed 173. A seed-157 traffic-aware ablation then identifies strict PASS "
            "configurations for the remaining candidate gap, yielding a targeted candidate oracle of 10/10. "
            "This is targeted candidate-policy coverage progress, not an external generalization or deployed-selector result."
        ),
    }


def fmt(value):
    if isinstance(value, (float, int)):
        return f"{float(value):.3f}"
    if value is None:
        return ""
    return str(value)


def write_csv(report, path):
    fields = [
        "seed",
        "method",
        "original_passing_methods",
        "targeted_status",
        "targeted_progress",
        "targeted_grass",
        "targeted_rank",
        "targeted_conservative_status",
        "targeted_conservative_progress",
        "targeted_conservative_grass",
        "targeted_conservative_rank",
        "expanded_oracle_status",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in report["rows"]:
            writer.writerow(row)


def write_markdown(report, path):
    original = report["original_oracle"]
    expanded = report["expanded_oracle"]
    lines = [
        "# Heldout3 Targeted Candidate Expansion",
        "",
        report["interpretation"],
        "",
        "## Summary",
        "",
        f"- Original heldout3 candidate oracle: {original['pass_count']}/{original['n']}",
        f"- Expanded heldout3 candidate oracle: {expanded['pass_count']}/{expanded['n']}",
        f"- Newly covered seeds: {', '.join(str(seed) for seed in expanded['newly_covered_seeds']) or 'none'}",
        f"- Remaining candidate-gap seeds: {', '.join(str(seed) for seed in expanded['remaining_candidate_gap_seeds']) or 'none'}",
        "",
        "## Candidate Results",
        "",
    ]
    for group_name, group in report["new_candidates"].items():
        lines.append(f"### {group_name}")
        lines.append("")
        if "methods" not in group:
            lines.append(f"- pass configurations: {group['pass_count']}/{group['n']}")
            lines.append(f"- best pass configuration: `{group['best_pass_config']}`")
            lines.append("")
            continue
        for method, summary in group["methods"].items():
            lines.append(
                f"- {method}: {summary['pass_count']}/{summary['n']} "
                f"(pass seeds: {', '.join(str(seed) for seed in summary['pass_seeds']) or 'none'})"
            )
        lines.append("")
    lines.extend(
        [
            "### seed157_traffic_ablation",
            "",
            f"- pass configurations: {report['new_candidates']['seed157_traffic_ablation']['pass_count']}/"
            f"{report['new_candidates']['seed157_traffic_ablation']['n']}",
            f"- best pass configuration: `{report['new_candidates']['seed157_traffic_ablation']['best_pass_config']}`",
            "",
            "## Seed-level Matrix",
            "",
            "| seed | method | original passing methods | targeted | progress | grass | rank | targeted conservative | progress | grass | rank | expanded oracle |",
            "|---:|---|---|---|---:|---:|---:|---|---:|---:|---:|---|",
        ]
    )
    for row in report["rows"]:
        lines.append(
            f"| {row['seed']} | {row['method']} | {row['original_passing_methods'] or 'none'} | "
            f"{row['targeted_status']} | {fmt(row['targeted_progress'])} | {fmt(row['targeted_grass'])} | "
            f"{fmt(row['targeted_rank'])} | {row['targeted_conservative_status']} | "
            f"{fmt(row['targeted_conservative_progress'])} | {fmt(row['targeted_conservative_grass'])} | "
            f"{fmt(row['targeted_conservative_rank'])} | {row['expanded_oracle_status']} |"
        )
    lines.extend(
        [
            "",
            "## Reporting Boundary",
            "",
            "- This report is a targeted repair diagnostic using heldout3 failure seeds.",
            "- Do not present the 9/10 expanded oracle as external validation or as online selector performance.",
            "- The seed157 ablation closes the candidate-policy gap only as a seed-targeted diagnostic.",
            "- Selector training/evaluation with this targeted candidate pool remains a separate step.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export heldout3 targeted candidate expansion report.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    report = build_report(root)
    out_json = root / "tables" / "heldout3_candidate_expansion.json"
    out_md = root / "tables" / "heldout3_candidate_expansion.md"
    out_csv = root / "tables" / "heldout3_candidate_expansion_rows.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv)}, indent=2))


if __name__ == "__main__":
    main()
