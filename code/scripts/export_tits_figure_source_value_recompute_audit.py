#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import json
import math
from pathlib import Path


FIGURE_SOURCE = "outputs/tits_dynamic_graph/manuscript_english_figures/tables/figure_dynamic_dlc_overtaking_source_data.csv"
OVERALL = "outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack/tables/confirmatory_overall_statistics.csv"
SCENARIO = "outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack/tables/confirmatory_scenario_statistics.csv"
PAIRED = "outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack/tables/confirmatory_paired_tests_vs_dlc.csv"

SCENARIO_LABELS = {
    "Procedural, 6 cars": ("in_distribution_procedural", "6"),
    "8-car extrapolation": ("vehicle_count_extrapolation", "8"),
    "Monza, 6 cars": ("monza_external_track", "6"),
}


def read_csv(path):
    path = Path(path)
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")
    return str(path)


def write_json(path, data):
    return write_text(path, json.dumps(data, ensure_ascii=False, indent=2))


def write_csv(path, rows, fields):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return str(path)


def blank(value):
    return value is None or str(value).strip() == ""


def to_float(value):
    if blank(value):
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(out) or math.isinf(out):
        return None
    return out


def close(a, b, tol=1e-10):
    af = to_float(a)
    bf = to_float(b)
    if af is None and bf is None:
        return True
    if af is None or bf is None:
        return False
    return abs(af - bf) <= tol


def index_rows(rows, fields):
    return {tuple(str(row.get(field, "")) for field in fields): row for row in rows}


def expected_values(row, overall, scenario, paired):
    source_table = row.get("source_table", "")
    metric = row.get("metric", "")
    algorithm = row.get("algorithm", "")
    comparison = row.get("comparison", "")
    if source_table == "confirmatory_overall_statistics.csv":
        stat = overall.get((algorithm,))
        key = algorithm
        fields = (f"{metric}_mean", f"{metric}_ci95_low", f"{metric}_ci95_high")
    elif source_table == "confirmatory_scenario_statistics.csv":
        benchmark, num_agents = SCENARIO_LABELS.get(comparison, ("", ""))
        stat = scenario.get((benchmark, num_agents, algorithm))
        key = f"{benchmark}|n{num_agents}|{algorithm}"
        fields = (f"{metric}_mean", f"{metric}_ci95_low", f"{metric}_ci95_high")
    elif source_table == "confirmatory_paired_tests_vs_dlc.csv":
        stat = paired.get((algorithm, "dlc_world_original", metric))
        key = f"{algorithm}|dlc_world_original|{metric}"
        fields = ("improvement_vs_dlc_mean", "improvement_ci95_low", "improvement_ci95_high")
    else:
        return None, "", ("", "", "")
    return stat, key, fields


def build_report(root):
    figure_rows = read_csv(root / FIGURE_SOURCE)
    overall = index_rows(read_csv(root / OVERALL), ["algorithm"])
    scenario = index_rows(read_csv(root / SCENARIO), ["benchmark", "num_agents", "algorithm"])
    paired = index_rows(read_csv(root / PAIRED), ["algorithm", "baseline", "metric"])
    audit_rows = []
    issue_rows = []
    for idx, row in enumerate(figure_rows, start=1):
        stat, source_key, fields = expected_values(row, overall, scenario, paired)
        errors = []
        expected_mean = expected_low = expected_high = ""
        if stat is None:
            errors.append("missing_source_row")
            issue_rows.append(
                {
                    "figure_row": idx,
                    "panel": row.get("panel", ""),
                    "source_table": row.get("source_table", ""),
                    "source_key": source_key,
                    "field": "source_row",
                    "expected_value": "",
                    "observed_value": "",
                    "message": "Figure source row cannot be resolved in its declared statistics table.",
                }
            )
        else:
            expected_mean, expected_low, expected_high = (stat.get(fields[0], ""), stat.get(fields[1], ""), stat.get(fields[2], ""))
            for label, expected, observed in [
                ("mean", expected_mean, row.get("mean", "")),
                ("ci95_low", expected_low, row.get("ci95_low", "")),
                ("ci95_high", expected_high, row.get("ci95_high", "")),
            ]:
                if not close(expected, observed):
                    errors.append(label)
                    issue_rows.append(
                        {
                            "figure_row": idx,
                            "panel": row.get("panel", ""),
                            "source_table": row.get("source_table", ""),
                            "source_key": source_key,
                            "field": label,
                            "expected_value": expected,
                            "observed_value": observed,
                            "message": "Figure source-data value differs from declared formal statistics table.",
                        }
                    )
        audit_rows.append(
            {
                "figure_row": idx,
                "panel": row.get("panel", ""),
                "comparison": row.get("comparison", ""),
                "algorithm": row.get("algorithm", ""),
                "metric": row.get("metric", ""),
                "source_table": row.get("source_table", ""),
                "source_key": source_key,
                "observed_mean": row.get("mean", ""),
                "expected_mean": expected_mean,
                "observed_ci95_low": row.get("ci95_low", ""),
                "expected_ci95_low": expected_low,
                "observed_ci95_high": row.get("ci95_high", ""),
                "expected_ci95_high": expected_high,
                "mismatch_fields": ";".join(errors),
                "status": "pass" if not errors else "review_required",
            }
        )
    status = "pass" if not issue_rows else "review_required"
    return {
        "status": status,
        "summary": {
            "status": status,
            "figure_source_rows": len(figure_rows),
            "checked_rows": len(audit_rows),
            "pass_rows": sum(1 for row in audit_rows if row["status"] == "pass"),
            "issue_count": len(issue_rows),
            "checked_cells": len(audit_rows) * 3,
            "mismatch_count": len(issue_rows),
            "source_tables_checked": 3,
        },
        "audit_rows": audit_rows,
        "issue_rows": issue_rows,
    }


def build_markdown(report):
    summary = report["summary"]
    lines = [
        "# Figure Source Value Recompute Audit",
        "",
        "This audit verifies that the manuscript English main figure source-data table is numerically synchronized with the formal confirmatory statistics tables.",
        "",
        "## Summary",
        "",
        f"- Status: `{report['status']}`",
        f"- Figure source rows: {summary['figure_source_rows']}",
        f"- Checked cells: {summary['checked_cells']}",
        f"- Mismatches: {summary['mismatch_count']}",
        f"- Source tables checked: {summary['source_tables_checked']}",
        "",
        "## Tables",
        "",
        f"- Figure source data: `{FIGURE_SOURCE}`",
        f"- Overall statistics: `{OVERALL}`",
        f"- Scenario statistics: `{SCENARIO}`",
        f"- Paired tests: `{PAIRED}`",
        "",
        "## Outputs",
        "",
        f"- Audit rows: `{report['paths']['audit_table']}`",
        f"- Issue rows: `{report['paths']['issue_table']}`",
        f"- Machine-readable report: `{report['paths']['audit_json']}`",
        "",
        "## Regeneration",
        "",
        "```bash",
        "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_figure_source_value_recompute_audit.py --out-dir outputs/tits_dynamic_graph/tits_figure_source_value_recompute_audit",
        "```",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Audit manuscript figure source-data values against formal statistics tables.")
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/tits_figure_source_value_recompute_audit")
    args = parser.parse_args()
    root = Path.cwd()
    out_dir = Path(args.out_dir)
    tables = out_dir / "tables"
    materials = out_dir / "materials"
    report = build_report(root)
    paths = {
        "audit_table": write_csv(
            tables / "figure_source_value_recompute_rows.csv",
            report["audit_rows"],
            [
                "figure_row", "panel", "comparison", "algorithm", "metric", "source_table", "source_key",
                "observed_mean", "expected_mean", "observed_ci95_low", "expected_ci95_low",
                "observed_ci95_high", "expected_ci95_high", "mismatch_fields", "status",
            ],
        ),
        "issue_table": write_csv(
            tables / "figure_source_value_recompute_issues.csv",
            report["issue_rows"],
            ["figure_row", "panel", "source_table", "source_key", "field", "expected_value", "observed_value", "message"],
        ),
        "audit_json": write_json(materials / "FIGURE_SOURCE_VALUE_RECOMPUTE_AUDIT.json", {k: v for k, v in report.items() if not k.endswith("_rows")}),
    }
    report["paths"] = paths
    paths["audit_md"] = write_text(materials / "FIGURE_SOURCE_VALUE_RECOMPUTE_AUDIT.md", build_markdown(report))
    manifest = {
        "status": report["status"],
        "out_dir": str(out_dir),
        "summary": report["summary"],
        "paths": paths,
    }
    manifest_path = write_json(out_dir / "tits_figure_source_value_recompute_audit_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, "status": manifest["status"], "summary": manifest["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
