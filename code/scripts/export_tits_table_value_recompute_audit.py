#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import json
import math
from pathlib import Path


MAIN_TABLE = "outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_main_results.md"
AGGREGATE = "outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_aggregate_statistics.csv"
SOURCE_DATA = "outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv"
PRIMARY_HOLM = "outputs/tits_dynamic_graph/tits_statistical_analysis_pack/tables/statistical_primary_holm.csv"
EFFECT_SIZES = "outputs/tits_dynamic_graph/tits_statistical_analysis_pack/tables/statistical_effect_sizes.csv"

MAIN_TABLE_METRIC_PRECISION = {
    "overtake_success_rate": 2,
    "on_track_overtake_rate": 2,
    "elegant_overtake_rate": 2,
    "rank_gain": 2,
    "overtake_start_to_complete_time": 1,
    "target_grass_rate": 3,
    "grass_recovery_time_mean": 1,
    "compute_latency_ms": 1,
}


def read_csv(path):
    path = Path(path)
    if not path.exists():
        return []
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
    return value is None or str(value).strip() in {"", "nan", "NaN", "None"}


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


def value_with_ci(mean, low, high, precision):
    mean = to_float(mean)
    low = to_float(low)
    high = to_float(high)
    if mean is None:
        return "--"
    if low is None or high is None:
        return f"{mean:.{precision}f}"
    return f"{mean:.{precision}f} [{low:.{precision}f}, {high:.{precision}f}]"


def p_value(value):
    value = to_float(value)
    if value is None:
        return "--"
    return f"{value:.3g}"


def parse_main_table(path):
    rows = []
    path = Path(path)
    if not path.exists():
        return rows
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if not cells or cells[0] in {"Benchmark", "---"} or cells[0].startswith("---"):
            continue
        if len(cells) != 7:
            rows.append({"line_no": line_no, "parse_status": "bad_column_count", "raw_line": line})
            continue
        rows.append(
            {
                "line_no": line_no,
                "benchmark": cells[0],
                "num_agents": cells[1],
                "algorithm_label_cn": cells[2],
                "metric_cn": cells[3],
                "value": cells[4],
                "delta": cells[5],
                "p": cells[6],
                "parse_status": "pass",
                "raw_line": line,
            }
        )
    return rows


def main_expected_rows(aggregate_rows):
    expected = {}
    for row in aggregate_rows:
        metric = row.get("metric", "")
        if metric not in MAIN_TABLE_METRIC_PRECISION:
            continue
        precision = MAIN_TABLE_METRIC_PRECISION[metric]
        key = (
            row.get("benchmark", ""),
            str(row.get("num_agents", "")),
            row.get("algorithm_label_cn", ""),
            row.get("metric_cn", ""),
        )
        expected[key] = {
            "benchmark": key[0],
            "num_agents": key[1],
            "algorithm": row.get("algorithm", ""),
            "algorithm_label_cn": key[2],
            "metric": metric,
            "metric_cn": key[3],
            "value": value_with_ci(row.get("mean"), row.get("ci95_low"), row.get("ci95_high"), precision),
            "delta": value_with_ci(
                row.get("paired_delta_vs_dlc_mean"),
                row.get("paired_delta_vs_dlc_ci95_low"),
                row.get("paired_delta_vs_dlc_ci95_high"),
                precision,
            ),
            "p": p_value(row.get("paired_sign_test_p")),
            "n": row.get("n", ""),
        }
    return expected


def add_issue(issues, table_id, row_key, field, expected, observed, message):
    issues.append(
        {
            "table_id": table_id,
            "row_key": row_key,
            "field": field,
            "expected_value": expected,
            "observed_value": observed,
            "message": message,
        }
    )


def compare_main_table(root):
    aggregate_rows = read_csv(root / AGGREGATE)
    expected = main_expected_rows(aggregate_rows)
    observed_rows = parse_main_table(root / MAIN_TABLE)
    observed = {}
    compare_rows = []
    issues = []
    for row in observed_rows:
        if row.get("parse_status") != "pass":
            key = f"line:{row.get('line_no')}"
            add_issue(issues, "Main Table 1", key, "parse", "7 markdown columns", row.get("raw_line", ""), "main table row cannot be parsed")
            continue
        key = (
            row.get("benchmark", ""),
            str(row.get("num_agents", "")),
            row.get("algorithm_label_cn", ""),
            row.get("metric_cn", ""),
        )
        observed[key] = row
    for key in sorted(set(expected) | set(observed)):
        expected_row = expected.get(key)
        observed_row = observed.get(key)
        row_key = "|".join(key)
        if expected_row is None:
            add_issue(issues, "Main Table 1", row_key, "unexpected_row", "", observed_row.get("raw_line", ""), "main table contains a row not present in aggregate statistics")
            continue
        if observed_row is None:
            add_issue(issues, "Main Table 1", row_key, "missing_row", expected_row.get("value", ""), "", "aggregate statistics row is missing from main markdown table")
            continue
        mismatch_fields = []
        for field in ("value", "delta", "p"):
            if expected_row.get(field, "") != observed_row.get(field, ""):
                mismatch_fields.append(field)
                add_issue(
                    issues,
                    "Main Table 1",
                    row_key,
                    field,
                    expected_row.get(field, ""),
                    observed_row.get(field, ""),
                    "main table formatted value differs from aggregate statistics",
                )
        compare_rows.append(
            {
                "table_id": "Main Table 1",
                "row_key": row_key,
                "source_table": AGGREGATE,
                "observed_value": observed_row.get("value", ""),
                "expected_value": expected_row.get("value", ""),
                "observed_delta": observed_row.get("delta", ""),
                "expected_delta": expected_row.get("delta", ""),
                "observed_p": observed_row.get("p", ""),
                "expected_p": expected_row.get("p", ""),
                "mismatch_fields": ";".join(mismatch_fields),
                "status": "pass" if not mismatch_fields else "review_required",
            }
        )
    return compare_rows, issues, len(expected), len(observed)


def close(left, right, tol=1e-10):
    left = to_float(left)
    right = to_float(right)
    if left is None and right is None:
        return True
    if left is None or right is None:
        return False
    return abs(left - right) <= tol


def compare_s2_tables(root):
    holm_rows = read_csv(root / PRIMARY_HOLM)
    effect_rows = read_csv(root / EFFECT_SIZES)
    effects = {
        (row.get("algorithm", ""), row.get("metric", "")): row
        for row in effect_rows
    }
    compare_rows = []
    issues = []
    field_pairs = [
        ("n_paired", "n_paired"),
        ("improvement_mean", "improvement_mean"),
        ("improvement_ci95_low", "improvement_ci95_low"),
        ("improvement_ci95_high", "improvement_ci95_high"),
    ]
    for row in holm_rows:
        key = (row.get("algorithm", ""), row.get("metric", ""))
        row_key = "|".join(key)
        effect = effects.get(key)
        mismatch_fields = []
        if effect is None:
            add_issue(issues, "Supplementary Table S2", row_key, "effect_size_row", "", "", "primary Holm row has no matching effect-size row")
        else:
            for holm_field, effect_field in field_pairs:
                if not close(row.get(holm_field), effect.get(effect_field)):
                    mismatch_fields.append(holm_field)
                    add_issue(
                        issues,
                        "Supplementary Table S2",
                        row_key,
                        holm_field,
                        row.get(holm_field, ""),
                        effect.get(effect_field, ""),
                        "primary Holm value differs from matching effect-size table value",
                    )
        compare_rows.append(
            {
                "table_id": "Supplementary Table S2",
                "row_key": row_key,
                "source_table": f"{PRIMARY_HOLM}; {EFFECT_SIZES}",
                "observed_value": row.get("improvement_mean", ""),
                "expected_value": "" if effect is None else effect.get("improvement_mean", ""),
                "observed_delta": row.get("improvement_ci95_low", ""),
                "expected_delta": "" if effect is None else effect.get("improvement_ci95_low", ""),
                "observed_p": row.get("p_holm", ""),
                "expected_p": row.get("p_holm", ""),
                "mismatch_fields": ";".join(mismatch_fields),
                "status": "pass" if not mismatch_fields and effect is not None else "review_required",
            }
        )
    return compare_rows, issues, len(holm_rows)


def source_facts(root):
    rows = read_csv(root / SOURCE_DATA)
    cases = {
        (
            row.get("_benchmark", ""),
            row.get("seed", ""),
            row.get("num_agents", ""),
            row.get("track_path", ""),
            row.get("traffic_profile", ""),
        )
        for row in rows
    }
    return {
        "source_rows": len(rows),
        "matched_case_count": len(cases),
        "algorithm_count": len({row.get("algorithm", "") for row in rows if row.get("algorithm", "")}),
    }


def build_report(root):
    main_rows, main_issues, expected_main_rows, observed_main_rows = compare_main_table(root)
    s2_rows, s2_issues, s2_primary_rows = compare_s2_tables(root)
    issues = main_issues + s2_issues
    compare_rows = main_rows + s2_rows
    facts = source_facts(root)
    mismatch_count = len(issues)
    status = "pass" if mismatch_count == 0 else "review_required"
    checks = [
        {
            "check_id": "TV01_source_data_shape",
            "status": "pass" if facts["source_rows"] == 240 and facts["matched_case_count"] == 30 and facts["algorithm_count"] == 8 else "review_required",
            "observed": f"rows={facts['source_rows']}; cases={facts['matched_case_count']}; algorithms={facts['algorithm_count']}",
            "expected": "rows=240; cases=30; algorithms=8",
            "interpretation": "The table-value audit uses the frozen confirmatory source data shape.",
        },
        {
            "check_id": "TV02_main_table_row_coverage",
            "status": "pass" if expected_main_rows == observed_main_rows and expected_main_rows > 0 else "review_required",
            "observed": f"observed_main_rows={observed_main_rows}",
            "expected": f"expected_main_rows={expected_main_rows}",
            "interpretation": "Every selected aggregate-statistics row should appear once in Main Table 1.",
        },
        {
            "check_id": "TV03_supplementary_s2_primary_rows",
            "status": "pass" if s2_primary_rows == 5 else "review_required",
            "observed": f"primary_holm_rows={s2_primary_rows}",
            "expected": "primary_holm_rows=5",
            "interpretation": "Supplementary Table S2 should cover the five pre-specified primary hypotheses.",
        },
        {
            "check_id": "TV04_value_mismatch_count",
            "status": "pass" if mismatch_count == 0 else "review_required",
            "observed": f"mismatches={mismatch_count}",
            "expected": "mismatches=0",
            "interpretation": "Displayed table values should match their source statistics after the same rounding/formatting rules.",
        },
    ]
    if any(row["status"] != "pass" for row in checks):
        status = "review_required"
    return {
        "status": status,
        "summary": {
            "status": status,
            "source_rows": facts["source_rows"],
            "matched_case_count": facts["matched_case_count"],
            "algorithm_count": facts["algorithm_count"],
            "main_table_expected_rows": expected_main_rows,
            "main_table_observed_rows": observed_main_rows,
            "main_table_checked_rows": len(main_rows),
            "supplementary_s2_checked_rows": len(s2_rows),
            "checked_rows": len(compare_rows),
            "checked_cells": len(main_rows) * 3 + len(s2_rows) * 4,
            "mismatch_count": mismatch_count,
            "check_count": len(checks),
            "check_issue_count": sum(1 for row in checks if row["status"] != "pass"),
        },
        "compare_rows": compare_rows,
        "issue_rows": issues,
        "check_rows": checks,
    }


def build_markdown(report):
    summary = report["summary"]
    lines = [
        "# Table Value Recompute Audit",
        "",
        "This audit checks whether manuscript-facing table values are numerically synchronized with the frozen formal source tables. It verifies Main Table 1 against the aggregate statistics table after the same rounding rules, and cross-checks Supplementary Table S2 primary Holm rows against the matching effect-size rows.",
        "",
        "## Summary",
        "",
        f"- Status: `{report['status']}`",
        f"- Formal source data: {summary['source_rows']} rows, {summary['matched_case_count']} matched cases, {summary['algorithm_count']} algorithms",
        f"- Main Table 1 rows: {summary['main_table_checked_rows']} checked / {summary['main_table_expected_rows']} expected",
        f"- Supplementary Table S2 rows: {summary['supplementary_s2_checked_rows']} checked",
        f"- Checked cells: {summary['checked_cells']}",
        f"- Mismatches: {summary['mismatch_count']}",
        "",
        "## Source Tables",
        "",
        f"- Main Table 1 markdown: `{MAIN_TABLE}`",
        f"- Aggregate statistics: `{AGGREGATE}`",
        f"- Primary Holm table: `{PRIMARY_HOLM}`",
        f"- Effect-size table: `{EFFECT_SIZES}`",
        "",
        "## Interpretation",
        "",
        "- A pass means the displayed table values are reproducible from the formal CSV tables with the same precision rules used by the table generator.",
        "- This audit complements the statistical-table recompute audit: that audit checks statistics from source data, while this one checks the manuscript-facing table values derived from those statistics.",
        "- It does not create new simulation evidence and should not be cited as an additional experiment.",
        "",
        "## Outputs",
        "",
        f"- Value comparison rows: `{report['paths']['comparison_table']}`",
        f"- Issue rows: `{report['paths']['issue_table']}`",
        f"- Check rows: `{report['paths']['check_table']}`",
        f"- Machine-readable report: `{report['paths']['audit_json']}`",
        "",
        "## Regeneration",
        "",
        "```bash",
        "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_table_value_recompute_audit.py --out-dir outputs/tits_dynamic_graph/tits_table_value_recompute_audit",
        "```",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Audit manuscript table values against formal source statistics.")
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/tits_table_value_recompute_audit")
    args = parser.parse_args()
    root = Path.cwd()
    out_dir = Path(args.out_dir)
    tables = out_dir / "tables"
    materials = out_dir / "materials"
    report = build_report(root)
    paths = {
        "comparison_table": write_csv(
            tables / "table_value_recompute_rows.csv",
            report["compare_rows"],
            [
                "table_id", "row_key", "source_table", "observed_value", "expected_value",
                "observed_delta", "expected_delta", "observed_p", "expected_p", "mismatch_fields", "status",
            ],
        ),
        "issue_table": write_csv(
            tables / "table_value_recompute_issues.csv",
            report["issue_rows"],
            ["table_id", "row_key", "field", "expected_value", "observed_value", "message"],
        ),
        "check_table": write_csv(
            tables / "table_value_recompute_checks.csv",
            report["check_rows"],
            ["check_id", "status", "observed", "expected", "interpretation"],
        ),
        "audit_json": write_json(materials / "TABLE_VALUE_RECOMPUTE_AUDIT.json", {k: v for k, v in report.items() if not k.endswith("_rows")}),
    }
    report["paths"] = paths
    paths["audit_md"] = write_text(materials / "TABLE_VALUE_RECOMPUTE_AUDIT.md", build_markdown(report))
    manifest = {
        "status": report["status"],
        "out_dir": str(out_dir),
        "summary": report["summary"],
        "paths": paths,
        "source_inputs": [SOURCE_DATA, MAIN_TABLE, AGGREGATE, PRIMARY_HOLM, EFFECT_SIZES],
    }
    manifest_path = write_json(out_dir / "tits_table_value_recompute_audit_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, "status": manifest["status"], "summary": manifest["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
