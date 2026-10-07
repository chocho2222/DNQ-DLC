#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def selector_entry(name, stage, report, status):
    failed = []
    selector_misses = []
    candidate_gaps = []
    pass_seeds = []
    for row in report["decisions"]:
        seed = int(row["seed"])
        if row["selected_full_status"] == "PASS":
            pass_seeds.append(seed)
        else:
            failed.append(seed)
            if row["oracle_status"] == "PASS":
                selector_misses.append(seed)
            else:
                candidate_gaps.append(seed)
    return {
        "heldout": name,
        "stage": stage,
        "status": status,
        "n": report["n"],
        "selector_pass_count": report["pass_count"],
        "oracle_pass_count": report["oracle_pass_count"],
        "selector_pass_rate": report["pass_count"] / report["n"],
        "oracle_pass_rate": report["oracle_pass_count"] / report["n"],
        "pass_seeds": pass_seeds,
        "failed_seeds": failed,
        "selector_miss_seeds": selector_misses,
        "candidate_gap_seeds": candidate_gaps,
        "methods": report["methods"],
    }


def external_entry(name, stage, report, status):
    selector = report["selector"] if "selector" in report else report["expanded_selector"]
    oracle = report["oracle"]
    failed = selector.get("failed_seeds", selector.get("selector_failed_seeds", []))
    candidate_gaps = oracle["candidate_gap_seeds"]
    selector_misses = selector.get(
        "selector_miss_seeds",
        [seed for seed in failed if seed not in set(candidate_gaps)],
    )
    return {
        "heldout": name,
        "stage": stage,
        "status": status,
        "n": selector["n"],
        "selector_pass_count": selector["pass_count"],
        "oracle_pass_count": oracle["pass_count"],
        "selector_pass_rate": selector["pass_count"] / selector["n"],
        "oracle_pass_rate": oracle["pass_count"] / oracle["n"],
        "pass_seeds": [seed for seed in report["seeds"] if seed not in failed],
        "failed_seeds": failed,
        "selector_miss_seeds": selector_misses,
        "candidate_gap_seeds": candidate_gaps,
        "methods": sorted(report["method_summary"]),
    }


def build_report(root):
    entries = [
        selector_entry(
            "heldout1",
            "five_candidate_original",
            load_json(root / "tables" / "portfolio_probe_selector_1200_heldout_dagger_v2.json"),
            "positive_control",
        ),
        selector_entry(
            "heldout2",
            "five_candidate_original",
            load_json(root / "tables" / "portfolio_probe_selector_1200_heldout2_dagger_v2.json"),
            "negative_generalization",
        ),
        selector_entry(
            "heldout1",
            "six_candidate_expanded",
            load_json(root / "tables" / "portfolio_probe_selector_1200_heldout_expanded.json"),
            "positive_control_preserved",
        ),
        selector_entry(
            "heldout2",
            "six_candidate_expanded",
            load_json(root / "tables" / "portfolio_probe_selector_1200_heldout2_expanded.json"),
            "partial_recovery",
        ),
        external_entry(
            "heldout3",
            "six_candidate_external",
            load_json(root / "tables" / "heldout3_external_validation.json"),
            "negative_external_validation",
        ),
        selector_entry(
            "heldout3",
            "seven_candidate_targeted",
            load_json(root / "tables" / "portfolio_probe_selector_1200_heldout3_targeted_expanded.json"),
            "targeted_candidate_pool_no_selector_gain",
        ),
        external_entry(
            "heldout4",
            "seven_candidate_external_after_targeted_repair",
            load_json(root / "tables" / "heldout4_external_validation.json"),
            "partial_transfer_external_validation",
        ),
    ]

    total_n = sum(row["n"] for row in entries if "external" in row["stage"] or "targeted" in row["stage"] or "expanded" in row["stage"])
    selector_pass = sum(row["selector_pass_count"] for row in entries if "external" in row["stage"] or "targeted" in row["stage"] or "expanded" in row["stage"])
    oracle_pass = sum(row["oracle_pass_count"] for row in entries if "external" in row["stage"] or "targeted" in row["stage"] or "expanded" in row["stage"])
    return {
        "root": str(root),
        "entries": entries,
        "aggregate_expanded_or_later": {
            "n": total_n,
            "selector_pass_count": selector_pass,
            "oracle_pass_count": oracle_pass,
            "selector_oracle_gap": oracle_pass - selector_pass,
        },
        "interpretation": (
            "Across held-out validation, the online portfolio is useful but not robust. Heldout1 is preserved "
            "at 10/10, heldout2 improves after candidate expansion, heldout3 exposes a sharp external-validation "
            "drop, and heldout4 shows partial transfer after targeted repair. The remaining gap is twofold: "
            "selector misses where a passing candidate exists, and candidate gaps where the tested portfolio "
            "contains no strict PASS policy."
        ),
    }


def write_outputs(root, report, prefix):
    tables = root / "tables"
    out_json = tables / f"{prefix}.json"
    out_md = tables / f"{prefix}.md"
    out_csv = tables / f"{prefix}_rows.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")

    fields = [
        "heldout",
        "stage",
        "status",
        "n",
        "selector_pass_count",
        "oracle_pass_count",
        "selector_pass_rate",
        "oracle_pass_rate",
        "failed_seeds",
        "selector_miss_seeds",
        "candidate_gap_seeds",
    ]
    with out_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in report["entries"]:
            writer.writerow(
                {
                    **{key: row[key] for key in fields if key not in {"failed_seeds", "selector_miss_seeds", "candidate_gap_seeds"}},
                    "failed_seeds": ";".join(map(str, row["failed_seeds"])),
                    "selector_miss_seeds": ";".join(map(str, row["selector_miss_seeds"])),
                    "candidate_gap_seeds": ";".join(map(str, row["candidate_gap_seeds"])),
                }
            )

    lines = [
        "# Cross-Heldout Validation Synthesis",
        "",
        report["interpretation"],
        "",
        "## Summary Matrix",
        "",
        "| heldout | stage | selector | oracle | selector misses | candidate gaps | status |",
        "|---|---|---:|---:|---|---|---|",
    ]
    for row in report["entries"]:
        lines.append(
            f"| {row['heldout']} | {row['stage']} | {row['selector_pass_count']}/{row['n']} | "
            f"{row['oracle_pass_count']}/{row['n']} | {', '.join(map(str, row['selector_miss_seeds'])) or 'none'} | "
            f"{', '.join(map(str, row['candidate_gap_seeds'])) or 'none'} | {row['status']} |"
        )
    agg = report["aggregate_expanded_or_later"]
    lines.extend(
        [
            "",
            "## Aggregate Expanded-Or-Later Evidence",
            "",
            f"- Total evaluated rollouts: {agg['n']}",
            f"- Selector strict PASS total: {agg['selector_pass_count']}/{agg['n']}",
            f"- Oracle strict PASS total: {agg['oracle_pass_count']}/{agg['n']}",
            f"- Selector-oracle gap: {agg['selector_oracle_gap']} seeds",
            "",
            "## Reporting Boundary",
            "",
            "- Oracle results are diagnostic upper bounds and must not be described as online selector outputs.",
            "- Heldout3-targeted repair is separated from heldout3 external validation.",
            "- Heldout4 is the first external validation after targeted repair and shows partial transfer, not robustness.",
            "",
        ]
    )
    out_md.write_text("\n".join(lines), encoding="utf-8")
    return {"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv)}


def main():
    parser = argparse.ArgumentParser(description="Export cross-heldout validation synthesis.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    parser.add_argument("--prefix", default="cross_heldout_validation_synthesis")
    args = parser.parse_args()
    root = Path(args.root)
    report = build_report(root)
    print(json.dumps(write_outputs(root, report, args.prefix), indent=2))


if __name__ == "__main__":
    main()
