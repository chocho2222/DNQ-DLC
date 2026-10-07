#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def rate_diff(selector_rate, oracle_rate):
    return selector_rate - oracle_rate


def relative_rate(selector_rate, oracle_rate):
    if oracle_rate == 0:
        return None
    return selector_rate / oracle_rate


def row_from_stage(item):
    selector_rate = item["selector_pass_rate"]
    oracle_rate = item["oracle_pass_rate"]
    diff = rate_diff(selector_rate, oracle_rate)
    rel = relative_rate(selector_rate, oracle_rate)
    return {
        "level": "stage",
        "label": f"{item['heldout']}::{item['stage']}",
        "heldout": item["heldout"],
        "stage": item["stage"],
        "status": item["status"],
        "n": item["n"],
        "selector_pass_count": item["selector_pass_count"],
        "oracle_pass_count": item["oracle_pass_count"],
        "selector_pass_rate": selector_rate,
        "oracle_pass_rate": oracle_rate,
        "selector_minus_oracle_rate": diff,
        "selector_to_oracle_rate_ratio": rel,
        "selector_oracle_gap_count": item["selector_oracle_gap_count"],
        "selector_oracle_gap_per_10_seeds": item["selector_oracle_gap_rate"] * 10.0,
        "selector_miss_count": item["selector_miss_count"],
        "candidate_gap_count": item["candidate_gap_count"],
        "selector_ci95_width": item["selector_ci95_high"] - item["selector_ci95_low"],
        "oracle_ci95_width": item["oracle_ci95_high"] - item["oracle_ci95_low"],
        "mcnemar_exact_p_selector_vs_oracle": item["mcnemar_exact_p_selector_vs_oracle"],
        "interpretation": interpret_effect(diff, item["selector_oracle_gap_count"], item["n"]),
    }


def row_from_aggregate(item):
    selector_rate = item["selector_pass_rate"]
    oracle_rate = item["oracle_pass_rate"]
    diff = rate_diff(selector_rate, oracle_rate)
    rel = relative_rate(selector_rate, oracle_rate)
    return {
        "level": "aggregate",
        "label": item["label"],
        "heldout": "expanded_or_later",
        "stage": item["label"],
        "status": "descriptive_aggregate",
        "n": item["n"],
        "selector_pass_count": item["selector_pass_count"],
        "oracle_pass_count": item["oracle_pass_count"],
        "selector_pass_rate": selector_rate,
        "oracle_pass_rate": oracle_rate,
        "selector_minus_oracle_rate": diff,
        "selector_to_oracle_rate_ratio": rel,
        "selector_oracle_gap_count": item["selector_oracle_gap_count"],
        "selector_oracle_gap_per_10_seeds": item["selector_oracle_gap_rate"] * 10.0,
        "selector_miss_count": None,
        "candidate_gap_count": None,
        "selector_ci95_width": item["selector_ci95_high"] - item["selector_ci95_low"],
        "oracle_ci95_width": item["oracle_ci95_high"] - item["oracle_ci95_low"],
        "mcnemar_exact_p_selector_vs_oracle": item["mcnemar_exact_p_selector_vs_oracle"],
        "interpretation": interpret_effect(diff, item["selector_oracle_gap_count"], item["n"]),
    }


def interpret_effect(diff, gap_count, n):
    if gap_count == 0:
        return "Selector matched the diagnostic oracle on strict pass count for this saved seed batch."
    gap_per_10 = gap_count / n * 10.0
    return (
        f"Selector underperformed the diagnostic oracle by {abs(diff):.2f} absolute pass-rate units, "
        f"equivalent to {gap_per_10:.1f} fewer strict passes per 10 evaluated seeds."
    )


def build_report(root):
    stats = load_json(root / "tables" / "cross_heldout_statistical_supplement.json")
    consistency = load_json(root / "materials" / "STATISTICAL_CONSISTENCY_AUDIT.json")
    seed_partition = load_json(root / "materials" / "SEED_PARTITION_AUDIT.json")
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    provenance = load_json(root / "tables" / "artifact_provenance.json")

    rows = [row_from_stage(item) for item in stats["stage_statistics"]]
    rows.append(row_from_aggregate(stats["aggregate_expanded_or_later"]))

    stage_rows = [row for row in rows if row["level"] == "stage"]
    aggregate = next(row for row in rows if row["level"] == "aggregate")
    largest_gap = max(stage_rows, key=lambda row: row["selector_oracle_gap_count"])
    no_gap_count = sum(1 for row in stage_rows if row["selector_oracle_gap_count"] == 0)
    negative_gap_count = sum(1 for row in stage_rows if row["selector_minus_oracle_rate"] < 0)

    return {
        "root": str(root),
        "title": "Effect Size and Uncertainty Summary",
        "purpose": (
            "Report magnitude-focused selector-versus-oracle effects from saved cross-heldout statistics, "
            "separating absolute pass-rate differences, relative rates, per-10-seed gaps, and interval widths."
        ),
        "scope": {
            "reruns_rollouts": False,
            "source_statistics": "tables/cross_heldout_statistical_supplement.json",
            "oracle_boundary": "Oracle rows are diagnostic upper bounds for candidate availability, not online selector outputs.",
            "claim_boundary": "Effect sizes are descriptive for fixed simulator seed batches and do not establish broad robustness.",
        },
        "rows": rows,
        "summary": {
            "status": "pass",
            "row_count": len(rows),
            "stage_row_count": len(stage_rows),
            "stage_rows_with_no_selector_oracle_gap": no_gap_count,
            "stage_rows_selector_below_oracle": negative_gap_count,
            "largest_stage_gap": largest_gap["label"],
            "largest_stage_gap_count": largest_gap["selector_oracle_gap_count"],
            "aggregate_selector_minus_oracle_rate": aggregate["selector_minus_oracle_rate"],
            "aggregate_selector_to_oracle_rate_ratio": aggregate["selector_to_oracle_rate_ratio"],
            "aggregate_gap_per_10_seeds": aggregate["selector_oracle_gap_per_10_seeds"],
            "statistical_consistency_status": consistency["summary"]["status"],
            "seed_partition_status": seed_partition["summary"]["status"],
            "publication_verification_status": verification["summary"]["status"],
            "artifact_provenance": f"{provenance['complete_count']}/{len(provenance['artifacts'])}",
        },
        "interpretation": (
            "The main magnitude finding is the selector-oracle gap: the online simulator-loop selector remains below the "
            "diagnostic candidate oracle in several held-out stages, so the evidence supports bounded partial "
            "transfer rather than broad robustness."
        ),
    }


def write_csv(report, path):
    fields = [
        "level",
        "label",
        "heldout",
        "stage",
        "status",
        "n",
        "selector_pass_count",
        "oracle_pass_count",
        "selector_pass_rate",
        "oracle_pass_rate",
        "selector_minus_oracle_rate",
        "selector_to_oracle_rate_ratio",
        "selector_oracle_gap_count",
        "selector_oracle_gap_per_10_seeds",
        "selector_miss_count",
        "candidate_gap_count",
        "selector_ci95_width",
        "oracle_ci95_width",
        "mcnemar_exact_p_selector_vs_oracle",
        "interpretation",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(report["rows"])


def write_markdown(report, path):
    lines = [
        "# Effect Size and Uncertainty Summary",
        "",
        report["purpose"],
        "",
        report["interpretation"],
        "",
        "## Scope",
        "",
    ]
    for key, value in report["scope"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Summary", ""])
    for key, value in report["summary"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(
        [
            "",
            "## Effect Rows",
            "",
            "| level | label | selector | oracle | selector-oracle rate | ratio | gap per 10 seeds | CI widths | interpretation |",
            "|---|---|---:|---:|---:|---:|---:|---|---|",
        ]
    )
    for item in report["rows"]:
        ratio = "NA" if item["selector_to_oracle_rate_ratio"] is None else f"{item['selector_to_oracle_rate_ratio']:.3f}"
        lines.append(
            f"| {item['level']} | {item['label']} | {item['selector_pass_count']}/{item['n']} | "
            f"{item['oracle_pass_count']}/{item['n']} | {item['selector_minus_oracle_rate']:.3f} | "
            f"{ratio} | {item['selector_oracle_gap_per_10_seeds']:.2f} | "
            f"selector {item['selector_ci95_width']:.3f}; oracle {item['oracle_ci95_width']:.3f} | "
            f"{item['interpretation']} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export effect-size and uncertainty summary.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_report(root)
    out_json = materials / "EFFECT_SIZE_UNCERTAINTY_SUMMARY.json"
    out_md = materials / "EFFECT_SIZE_UNCERTAINTY_SUMMARY.md"
    out_csv = materials / "EFFECT_SIZE_UNCERTAINTY_SUMMARY.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv), "summary": report["summary"]}, indent=2))


if __name__ == "__main__":
    main()
