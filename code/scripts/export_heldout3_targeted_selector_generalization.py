#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def by_seed(report):
    return {int(row["seed"]): row for row in report["decisions"]}


def main():
    parser = argparse.ArgumentParser(description="Compare heldout3 selector behavior before/after targeted candidate integration.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    parser.add_argument("--prefix", default="heldout3_targeted_selector_generalization")
    args = parser.parse_args()

    root = Path(args.root)
    tables = root / "tables"
    original = load_json(tables / "portfolio_probe_selector_1200_heldout3_expanded.json")
    targeted = load_json(tables / "portfolio_probe_selector_1200_heldout3_targeted_expanded.json")
    traffic_suite = load_json(tables / "heldout3_traffic_adaptive_conservative_suite_report.json")
    expansion = load_json(tables / "heldout3_candidate_expansion.json")

    original_rows = by_seed(original)
    targeted_rows = by_seed(targeted)
    seeds = sorted(set(original_rows) | set(targeted_rows))
    rows = []
    for seed in seeds:
        old = original_rows[seed]
        new = targeted_rows[seed]
        rows.append(
            {
                "seed": seed,
                "original_selected": old["selected_method"],
                "original_status": old["selected_full_status"],
                "original_oracle_status": old["oracle_status"],
                "targeted_selected": new["selected_method"],
                "targeted_status": new["selected_full_status"],
                "targeted_oracle_method": new["oracle_method"],
                "targeted_oracle_status": new["oracle_status"],
                "selector_changed": old["selected_method"] != new["selected_method"],
                "selector_improved": old["selected_full_status"] != "PASS" and new["selected_full_status"] == "PASS",
                "new_oracle_gain": old["oracle_status"] != "PASS" and new["oracle_status"] == "PASS",
            }
        )

    traffic_by_method = traffic_suite["method_summaries"]["heldout3_traffic_adaptive_conservative"]
    selector_misses = [
        row["seed"]
        for row in rows
        if row["targeted_oracle_status"] == "PASS" and row["targeted_status"] != "PASS"
    ]
    report = {
        "root": str(root),
        "comparison": "heldout3 targeted candidate integration",
        "original_selector": {
            "source": "tables/portfolio_probe_selector_1200_heldout3_expanded.json",
            "methods": original["methods"],
            "pass_count": original["pass_count"],
            "oracle_pass_count": original["oracle_pass_count"],
            "n": original["n"],
        },
        "targeted_selector": {
            "source": "tables/portfolio_probe_selector_1200_heldout3_targeted_expanded.json",
            "methods": targeted["methods"],
            "pass_count": targeted["pass_count"],
            "oracle_pass_count": targeted["oracle_pass_count"],
            "n": targeted["n"],
        },
        "traffic_adaptive_conservative_suite": {
            "source": "tables/heldout3_traffic_adaptive_conservative_suite_report.json",
            "pass_count": traffic_by_method["pass_count"],
            "n": traffic_by_method["n"],
            "pass_rate": traffic_by_method["pass_rate"],
        },
        "targeted_candidate_expansion": {
            "source": "tables/heldout3_candidate_expansion.json",
            "original_oracle_pass_count": expansion["original_oracle"]["pass_count"],
            "expanded_oracle_pass_count": expansion["expanded_oracle"]["pass_count"],
            "n": expansion["expanded_oracle"]["n"],
            "newly_covered_seeds": expansion["expanded_oracle"]["newly_covered_seeds"],
        },
        "selector_miss_seeds_after_targeted_candidate": selector_misses,
        "rows": rows,
        "interpretation": (
            "Adding the traffic-adaptive conservative targeted candidate increases the locked heldout3 oracle "
            "available to the online selector, but the 1200-step probe selector does not improve its online simulator-loop "
            "strict pass count. This is evidence for candidate-policy coverage progress and for a remaining "
            "selector-integration bottleneck, not evidence of external-validation robustness."
        ),
    }

    out_json = tables / f"{args.prefix}.json"
    out_csv = tables / f"{args.prefix}_rows.csv"
    out_md = tables / f"{args.prefix}.md"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")

    with out_csv.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "seed",
            "original_selected",
            "original_status",
            "original_oracle_status",
            "targeted_selected",
            "targeted_status",
            "targeted_oracle_method",
            "targeted_oracle_status",
            "selector_changed",
            "selector_improved",
            "new_oracle_gain",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    lines = [
        "# Heldout3 Targeted Selector Generalization",
        "",
        "## Summary",
        "",
        f"- Original expanded selector: {original['pass_count']}/{original['n']} strict PASS; oracle {original['oracle_pass_count']}/{original['n']}.",
        f"- Targeted candidate selector: {targeted['pass_count']}/{targeted['n']} strict PASS; oracle {targeted['oracle_pass_count']}/{targeted['n']}.",
        (
            "- Traffic-adaptive conservative candidate alone: "
            f"{traffic_by_method['pass_count']}/{traffic_by_method['n']} strict PASS."
        ),
        (
            "- Post-hoc targeted candidate expansion oracle: "
            f"{expansion['original_oracle']['pass_count']}/{expansion['original_oracle']['n']} -> "
            f"{expansion['expanded_oracle']['pass_count']}/{expansion['expanded_oracle']['n']}."
        ),
        f"- Selector miss seeds after adding the targeted candidate: {selector_misses}.",
        "",
        "## Per-Seed Comparison",
        "",
        "| seed | old selected | old status | new selected | new status | new oracle | oracle gain |",
        "|---:|---|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['seed']} | {row['original_selected']} | {row['original_status']} | "
            f"{row['targeted_selected']} | {row['targeted_status']} | "
            f"{row['targeted_oracle_method']}:{row['targeted_oracle_status']} | {row['new_oracle_gain']} |"
        )
    lines.extend(["", "## Interpretation", "", report["interpretation"], ""])
    out_md.write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv)}, indent=2))


if __name__ == "__main__":
    main()
