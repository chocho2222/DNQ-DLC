#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import json
import math
from pathlib import Path

from export_tits_confirmatory_evidence_pack import (
    paired_tests,
    scenario_rows,
    summarize_overall,
)


SOURCE_CSV = "outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv"
OVERALL_CSV = "outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack/tables/confirmatory_overall_statistics.csv"
SCENARIO_CSV = "outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack/tables/confirmatory_scenario_statistics.csv"
PAIRED_CSV = "outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack/tables/confirmatory_paired_tests_vs_dlc.csv"
EVIDENCE_MANIFEST = "outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack/confirmatory_evidence_pack_manifest.json"


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


def read_json(path):
    path = Path(path)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


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


def normalize(value):
    if isinstance(value, bool):
        return "True" if value else "False"
    if value is None:
        return ""
    return str(value)


def value_match(left, right, tol=1e-10):
    lf = to_float(left)
    rf = to_float(right)
    if lf is not None or rf is not None:
        if lf is None or rf is None:
            return False
        return abs(lf - rf) <= tol
    return normalize(left) == normalize(right)


def key_for(table, row):
    if table == "overall":
        return (row.get("algorithm", ""),)
    if table == "scenario":
        return (row.get("benchmark", ""), str(row.get("num_agents", "")), row.get("algorithm", ""))
    if table == "paired":
        return (row.get("algorithm", ""), row.get("baseline", ""), row.get("metric", ""))
    raise ValueError(table)


def compare_table(table_name, expected_rows, observed_rows, key_fields, tol=1e-10):
    observed = {key_for(table_name, row): row for row in observed_rows}
    expected = {key_for(table_name, row): {k: normalize(v) for k, v in row.items()} for row in expected_rows}
    issues = []
    compare_rows = []
    all_keys = sorted(set(expected) | set(observed))
    for key in all_keys:
        expected_row = expected.get(key)
        observed_row = observed.get(key)
        if expected_row is None:
            issues.append(make_issue(table_name, key, "unexpected_row", "", "", "observed row has no recomputed counterpart"))
            continue
        if observed_row is None:
            issues.append(make_issue(table_name, key, "missing_row", "", "", "recomputed row missing from evidence table"))
            continue
        fields = sorted(set(expected_row) | set(observed_row))
        mismatch_fields = []
        for field in fields:
            ev = expected_row.get(field, "")
            ov = observed_row.get(field, "")
            if not value_match(ev, ov, tol=tol):
                mismatch_fields.append(field)
                issues.append(make_issue(table_name, key, field, ev, ov, "observed evidence table value differs from source-data recomputation"))
        compare_rows.append(
            {
                "table": table_name,
                "key": "|".join(map(str, key)),
                "key_fields": ";".join(key_fields),
                "compared_fields": len(fields),
                "mismatch_count": len(mismatch_fields),
                "mismatch_fields": ";".join(mismatch_fields),
                "status": "pass" if not mismatch_fields else "review_required",
            }
        )
    return compare_rows, issues


def make_issue(table, key, field, expected, observed, message):
    return {
        "table": table,
        "key": "|".join(map(str, key)),
        "field": field,
        "expected_recomputed_value": expected,
        "observed_evidence_value": observed,
        "message": message,
    }


def build_markdown(report):
    summary = report["summary"]
    lines = [
        "# Statistical Table Recompute Audit",
        "",
        "This audit independently rebuilds the formal confirmatory statistics tables from the frozen 240-run source data and compares them against the evidence-pack CSV files.",
        "",
        "## Summary",
        "",
        f"- Status: `{report['status']}`",
        f"- Source rows: {summary['source_rows']}",
        f"- Overall rows checked: {summary['overall_rows_checked']}",
        f"- Scenario rows checked: {summary['scenario_rows_checked']}",
        f"- Paired-test rows checked: {summary['paired_rows_checked']}",
        f"- Compared cells: {summary['compared_cells']}",
        f"- Mismatch count: {summary['mismatch_count']}",
        "",
        "## Tables Checked",
        "",
        f"- Overall statistics: `{OVERALL_CSV}`",
        f"- Scenario statistics: `{SCENARIO_CSV}`",
        f"- Paired tests vs DLC: `{PAIRED_CSV}`",
        "",
        "## Outputs",
        "",
        f"- Table comparison rows: `{report['paths']['comparison_table']}`",
        f"- Issue table: `{report['paths']['issue_table']}`",
        f"- Machine-readable report: `{report['paths']['audit_json']}`",
        "",
        "## Regeneration",
        "",
        "```bash",
        "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_statistical_table_recompute_audit.py --out-dir outputs/tits_dynamic_graph/tits_statistical_table_recompute_audit",
        "```",
    ]
    return "\n".join(lines)


def build_report(root, bootstrap, seed):
    source = read_csv(root / SOURCE_CSV)
    expected_overall = summarize_overall(source, bootstrap, seed)
    expected_scenario = scenario_rows(source, bootstrap, seed)
    expected_paired = paired_tests(source, bootstrap, seed)
    observed_overall = read_csv(root / OVERALL_CSV)
    observed_scenario = read_csv(root / SCENARIO_CSV)
    observed_paired = read_csv(root / PAIRED_CSV)

    overall_rows, overall_issues = compare_table("overall", expected_overall, observed_overall, ["algorithm"])
    scenario_compare, scenario_issues = compare_table("scenario", expected_scenario, observed_scenario, ["benchmark", "num_agents", "algorithm"])
    paired_compare, paired_issues = compare_table("paired", expected_paired, observed_paired, ["algorithm", "baseline", "metric"])
    compare_rows = overall_rows + scenario_compare + paired_compare
    issue_rows = overall_issues + scenario_issues + paired_issues
    mismatch_count = sum(int(row["mismatch_count"]) for row in compare_rows) + sum(1 for issue in issue_rows if issue["field"] in {"missing_row", "unexpected_row"})
    status = "pass" if mismatch_count == 0 else "review_required"
    return {
        "status": status,
        "source_csv": SOURCE_CSV,
        "summary": {
            "status": status,
            "source_rows": len(source),
            "overall_rows_checked": len(overall_rows),
            "scenario_rows_checked": len(scenario_compare),
            "paired_rows_checked": len(paired_compare),
            "compared_cells": sum(int(row["compared_fields"]) for row in compare_rows),
            "mismatch_count": mismatch_count,
            "issue_count": len(issue_rows),
            "bootstrap": bootstrap,
            "seed": seed,
        },
        "compare_rows": compare_rows,
        "issue_rows": issue_rows,
    }


def main():
    parser = argparse.ArgumentParser(description="Recompute formal statistical evidence tables from source data.")
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/tits_statistical_table_recompute_audit")
    parser.add_argument("--bootstrap", type=int, default=None)
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()
    root = Path.cwd()
    manifest = read_json(root / EVIDENCE_MANIFEST)
    bootstrap = args.bootstrap if args.bootstrap is not None else int(manifest.get("bootstrap", 5000))
    seed = args.seed if args.seed is not None else int(manifest.get("seed", 20260624))
    out_dir = Path(args.out_dir)
    tables = out_dir / "tables"
    materials = out_dir / "materials"
    report = build_report(root, bootstrap, seed)
    paths = {
        "comparison_table": write_csv(
            tables / "statistical_table_recompute_rows.csv",
            report["compare_rows"],
            ["table", "key", "key_fields", "compared_fields", "mismatch_count", "mismatch_fields", "status"],
        ),
        "issue_table": write_csv(
            tables / "statistical_table_recompute_issues.csv",
            report["issue_rows"],
            ["table", "key", "field", "expected_recomputed_value", "observed_evidence_value", "message"],
        ),
        "audit_json": write_json(materials / "STATISTICAL_TABLE_RECOMPUTE_AUDIT.json", {k: v for k, v in report.items() if not k.endswith("_rows")}),
    }
    report["paths"] = paths
    paths["audit_md"] = write_text(materials / "STATISTICAL_TABLE_RECOMPUTE_AUDIT.md", build_markdown(report))
    manifest = {
        "status": report["status"],
        "out_dir": str(out_dir),
        "summary": report["summary"],
        "paths": paths,
    }
    manifest_path = write_json(out_dir / "tits_statistical_table_recompute_audit_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, "status": manifest["status"], "summary": manifest["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
