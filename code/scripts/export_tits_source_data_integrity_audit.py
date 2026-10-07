#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path


SOURCE_CSV = "outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv"
METRIC_DICTIONARY_CSV = "outputs/tits_dynamic_graph/tits_benchmark_protocol_pack/tables/metric_dictionary.csv"
BENCHMARK_CARDS_CSV = "outputs/tits_dynamic_graph/tits_benchmark_protocol_pack/tables/benchmark_cards.csv"
ALGORITHM_CARDS_CSV = "outputs/tits_dynamic_graph/tits_benchmark_protocol_pack/tables/algorithm_cards.csv"

EXPECTED_ROW_COUNT = 240
EXPECTED_CASE_COUNT = 30
EXPECTED_ALGORITHM_COUNT = 8
EXPECTED_COLUMN_COUNT = 42

KEY_FIELDS = ["_benchmark", "num_agents", "seed", "algorithm"]
CASE_FIELDS = ["_benchmark", "num_agents", "seed"]
REQUIRED_METADATA_FIELDS = [
    "_benchmark",
    "algorithm",
    "seed",
    "num_agents",
    "track_path",
    "traffic_profile",
    "_summary_file",
]

RATE_FIELDS = [
    "overtake_success_rate",
    "on_track_overtake_rate",
    "elegant_overtake_rate",
    "overtake_window_grass_rate_mean",
    "target_grass_rate",
    "collision_or_contact_proxy",
]
NONNEGATIVE_FIELDS = [
    "target_progress",
    "rank_gain",
    "overtake_count",
    "on_track_overtake_count",
    "elegant_overtake_count",
    "time_to_first_overtake",
    "overtake_start_to_complete_time",
    "overtake_window_max_abs_lateral_mean",
    "grass_recovery_time_mean",
    "grass_recovery_time_max",
    "grass_excursion_count",
    "unrecovered_grass_excursion_count",
    "target_mean_abs_lateral",
    "target_heading_error_mean_rad",
    "compute_latency_ms",
    "compute_latency_p95_ms",
    "finish_step",
]
INTEGER_FIELDS = [
    "seed",
    "num_agents",
    "target_final_rank",
    "rank_gain",
    "overtake_count",
    "on_track_overtake_count",
    "elegant_overtake_count",
    "grass_excursion_count",
    "unrecovered_grass_excursion_count",
    "finish_step",
]
BOOLEAN_FIELDS = ["target_completed_lap", "overtake_aware_planner"]
SUMMARY_COMPARE_FIELDS = [
    "algorithm",
    "seed",
    "num_agents",
    "track_path",
    "traffic_profile",
    "target_final_rank",
    "rank_gain",
    "target_progress",
    "target_completed_lap",
    "overtake_success_rate",
    "overtake_count",
    "on_track_overtake_count",
    "on_track_overtake_rate",
    "elegant_overtake_count",
    "elegant_overtake_rate",
    "time_to_first_overtake",
    "overtake_start_to_complete_time",
    "overtake_window_grass_rate_mean",
    "overtake_window_max_abs_lateral_mean",
    "target_grass_rate",
    "grass_recovery_time_mean",
    "grass_recovery_time_max",
    "grass_excursion_count",
    "unrecovered_grass_excursion_count",
    "target_mean_abs_lateral",
    "target_heading_error_mean_rad",
    "collision_or_contact_proxy",
    "compute_latency_ms",
    "compute_latency_p95_ms",
    "finish_step",
]


def read_csv(path):
    path = Path(path)
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader), list(reader.fieldnames or [])


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


def is_blank(value):
    return value is None or str(value).strip() == ""


def to_float(value):
    if is_blank(value):
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(out) or math.isinf(out):
        return None
    return out


def to_int(value):
    number = to_float(value)
    if number is None:
        return None
    if abs(number - round(number)) > 1e-9:
        return None
    return int(round(number))


def row_id(row):
    return f"{row.get('_benchmark')}|n{row.get('num_agents')}|seed{row.get('seed')}|{row.get('algorithm')}"


def case_id(row):
    return f"{row.get('_benchmark')}|n{row.get('num_agents')}|seed{row.get('seed')}"


def add_issue(issues, severity, category, message, row=None, field="", expected="", observed=""):
    issues.append(
        {
            "severity": severity,
            "category": category,
            "row_id": row_id(row) if row else "",
            "case_id": case_id(row) if row else "",
            "field": field,
            "expected": expected,
            "observed": observed,
            "message": message,
        }
    )


def numeric_equal(csv_value, summary_value, tol=1e-6):
    a = to_float(csv_value)
    b = to_float(summary_value)
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    return abs(a - b) <= tol


def string_equal(csv_value, summary_value):
    if is_blank(csv_value) and summary_value in (None, ""):
        return True
    return str(csv_value) == str(summary_value)


def bool_equal(csv_value, summary_value):
    if is_blank(csv_value) and summary_value in (None, ""):
        return True
    csv_text = str(csv_value).strip().lower()
    if isinstance(summary_value, bool):
        summary_text = "true" if summary_value else "false"
    else:
        summary_text = str(summary_value).strip().lower()
    return csv_text == summary_text


def load_protocol(root):
    metric_rows, metric_fields = read_csv(root / METRIC_DICTIONARY_CSV)
    benchmark_rows, _ = read_csv(root / BENCHMARK_CARDS_CSV)
    algorithm_rows, _ = read_csv(root / ALGORITHM_CARDS_CSV)
    return {
        "metric_rows": metric_rows,
        "metric_fields": metric_fields,
        "benchmark_rows": benchmark_rows,
        "algorithm_rows": algorithm_rows,
        "expected_columns": [row["field"] for row in metric_rows if row.get("field")],
        "expected_algorithms": [row["algorithm"] for row in algorithm_rows if row.get("algorithm")],
        "expected_cases": [
            {
                "benchmark": row["benchmark"],
                "num_agents": row["num_agents"],
                "seeds": [item.strip() for item in row["seed_list"].split(",") if item.strip()],
                "track_path": row["track_path"],
                "traffic_profile": row["traffic_profile"],
            }
            for row in benchmark_rows
        ],
    }


def validate_schema(rows, fields, protocol, issues):
    expected_columns = protocol["expected_columns"]
    if len(fields) != EXPECTED_COLUMN_COUNT:
        add_issue(issues, "error", "schema", "Unexpected source-data column count.", expected=EXPECTED_COLUMN_COUNT, observed=len(fields))
    if len(rows) != EXPECTED_ROW_COUNT:
        add_issue(issues, "error", "schema", "Unexpected source-data row count.", expected=EXPECTED_ROW_COUNT, observed=len(rows))
    missing = [field for field in expected_columns if field not in fields]
    extra = [field for field in fields if field not in expected_columns]
    for field in missing:
        add_issue(issues, "error", "schema", "Metric dictionary field missing from source CSV.", field=field)
    for field in extra:
        add_issue(issues, "warning", "schema", "Source CSV field not listed in metric dictionary.", field=field)
    for field in REQUIRED_METADATA_FIELDS:
        if field not in fields:
            add_issue(issues, "error", "schema", "Required metadata field missing.", field=field)


def validate_design(rows, protocol, issues):
    algorithms = sorted({row["algorithm"] for row in rows})
    expected_algorithms = sorted(protocol["expected_algorithms"])
    if algorithms != expected_algorithms:
        add_issue(issues, "error", "design", "Algorithm set does not match protocol card.", expected=";".join(expected_algorithms), observed=";".join(algorithms))

    duplicate_counter = Counter(tuple(row.get(field, "") for field in KEY_FIELDS) for row in rows)
    for key, count in duplicate_counter.items():
        if count != 1:
            add_issue(issues, "error", "design", "Duplicate or missing unique algorithm-run key.", expected="1", observed=str(count), field="|".join(key))

    expected_case_keys = set()
    for item in protocol["expected_cases"]:
        for seed in item["seeds"]:
            expected_case_keys.add((item["benchmark"], item["num_agents"], seed))
    observed_case_keys = {(row["_benchmark"], row["num_agents"], row["seed"]) for row in rows}
    if len(observed_case_keys) != EXPECTED_CASE_COUNT:
        add_issue(issues, "error", "design", "Unexpected matched-case count.", expected=EXPECTED_CASE_COUNT, observed=len(observed_case_keys))
    for key in sorted(expected_case_keys - observed_case_keys):
        add_issue(issues, "error", "design", "Protocol case missing from source data.", field="|".join(key))
    for key in sorted(observed_case_keys - expected_case_keys):
        add_issue(issues, "error", "design", "Source-data case not listed in protocol.", field="|".join(key))

    by_case = defaultdict(list)
    for row in rows:
        by_case[(row["_benchmark"], row["num_agents"], row["seed"])].append(row)
    for key, case_rows in by_case.items():
        case_algorithms = sorted(row["algorithm"] for row in case_rows)
        if case_algorithms != expected_algorithms:
            add_issue(issues, "error", "design", "Matched case does not contain exactly the expected algorithms.", field="|".join(key), expected=";".join(expected_algorithms), observed=";".join(case_algorithms))
        for field in ["track_path", "traffic_profile", "finish_step"]:
            values = sorted({row.get(field, "") for row in case_rows})
            if len(values) != 1:
                add_issue(issues, "error", "design", "Matched case has inconsistent control field across algorithms.", field=field, expected="one shared value", observed=";".join(values), row=case_rows[0])


def validate_values(rows, issues):
    for row in rows:
        for field in REQUIRED_METADATA_FIELDS:
            if is_blank(row.get(field)):
                add_issue(issues, "error", "missing_value", "Required metadata value is blank.", row=row, field=field)
        for field in RATE_FIELDS:
            value = to_float(row.get(field))
            if value is not None and not (0.0 <= value <= 1.0):
                add_issue(issues, "error", "range", "Rate/proportion field outside [0, 1].", row=row, field=field, expected="[0,1]", observed=row.get(field))
        for field in NONNEGATIVE_FIELDS:
            value = to_float(row.get(field))
            if value is not None and value < -1e-9:
                add_issue(issues, "error", "range", "Nonnegative field is negative.", row=row, field=field, expected=">=0", observed=row.get(field))
        for field in INTEGER_FIELDS:
            if not is_blank(row.get(field)) and to_int(row.get(field)) is None:
                add_issue(issues, "error", "type", "Integer field is not integer-valued.", row=row, field=field, expected="integer", observed=row.get(field))
        for field in BOOLEAN_FIELDS:
            if field in row and not is_blank(row.get(field)) and str(row.get(field)).strip().lower() not in {"true", "false", "0", "1"}:
                add_issue(issues, "error", "type", "Boolean field is not boolean-valued.", row=row, field=field, expected="true/false", observed=row.get(field))

        num_agents = to_int(row.get("num_agents"))
        target_rank = to_int(row.get("target_final_rank"))
        if num_agents is not None and target_rank is not None and not (1 <= target_rank <= num_agents):
            add_issue(issues, "error", "range", "Target final rank outside vehicle-count range.", row=row, field="target_final_rank", expected=f"1..{num_agents}", observed=row.get("target_final_rank"))

        overtake_count = to_int(row.get("overtake_count")) or 0
        on_track_count = to_int(row.get("on_track_overtake_count")) or 0
        elegant_count = to_int(row.get("elegant_overtake_count")) or 0
        if on_track_count > overtake_count:
            add_issue(issues, "error", "count_invariant", "On-track overtake count exceeds total overtake count.", row=row, field="on_track_overtake_count")
        if elegant_count > on_track_count:
            add_issue(issues, "error", "count_invariant", "Desirable overtaking behavior count exceeds on-track overtake count.", row=row, field="elegant_overtake_count")

        if overtake_count == 0:
            for field in ["time_to_first_overtake", "overtake_start_to_complete_time", "overtake_window_grass_rate_mean", "overtake_window_max_abs_lateral_mean"]:
                if not is_blank(row.get(field)):
                    add_issue(issues, "warning", "event_conditioned_metric", "Event-conditioned metric is populated despite zero overtakes.", row=row, field=field, observed=row.get(field))
        else:
            for field in ["time_to_first_overtake", "overtake_start_to_complete_time"]:
                if is_blank(row.get(field)):
                    add_issue(issues, "error", "event_conditioned_metric", "Overtake timing metric is blank despite at least one overtake.", row=row, field=field)

        for count_field, rate_field in [
            ("on_track_overtake_count", "on_track_overtake_rate"),
            ("elegant_overtake_count", "elegant_overtake_rate"),
        ]:
            count_value = to_float(row.get(count_field))
            rate_value = to_float(row.get(rate_field))
            if overtake_count > 0 and count_value is not None and rate_value is not None:
                expected = count_value / float(overtake_count)
                if abs(rate_value - expected) > 1e-6:
                    add_issue(issues, "error", "rate_count_consistency", "Overtake quality rate does not match count/total.", row=row, field=rate_field, expected=f"{expected:.8f}", observed=row.get(rate_field))


def validate_summary_links(root, rows, issues):
    compared = 0
    missing = 0
    mismatches = 0
    for row in rows:
        summary_rel = row.get("_summary_file", "")
        summary_path = root / summary_rel
        if not summary_path.exists():
            missing += 1
            add_issue(issues, "error", "summary_link", "Referenced summary JSON does not exist.", row=row, field="_summary_file", observed=summary_rel)
            continue
        try:
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
        except Exception as exc:
            add_issue(issues, "error", "summary_link", "Referenced summary JSON could not be parsed.", row=row, field="_summary_file", observed=str(exc))
            continue
        compared += 1
        for field in SUMMARY_COMPARE_FIELDS:
            if field not in row:
                continue
            csv_value = row.get(field)
            summary_value = summary.get(field)
            if field in BOOLEAN_FIELDS:
                ok = bool_equal(csv_value, summary_value)
            elif field in {"algorithm", "track_path", "traffic_profile"}:
                ok = string_equal(csv_value, summary_value)
            else:
                ok = numeric_equal(csv_value, summary_value)
            if not ok:
                mismatches += 1
                add_issue(issues, "error", "summary_consistency", "Source CSV value differs from linked summary JSON.", row=row, field=field, expected=str(summary_value), observed=str(csv_value))
    return {"summary_files_compared": compared, "summary_files_missing": missing, "summary_field_mismatches": mismatches}


def build_case_rows(rows):
    by_case = defaultdict(list)
    for row in rows:
        by_case[(row["_benchmark"], row["num_agents"], row["seed"])].append(row)
    case_rows = []
    for key, case_rows_raw in sorted(by_case.items()):
        benchmark, num_agents, seed = key
        algorithms = sorted(row["algorithm"] for row in case_rows_raw)
        case_rows.append(
            {
                "case_id": f"{benchmark}|n{num_agents}|seed{seed}",
                "benchmark": benchmark,
                "num_agents": num_agents,
                "seed": seed,
                "algorithm_count": len(algorithms),
                "algorithms": ";".join(algorithms),
                "track_path_values": ";".join(sorted({row.get("track_path", "") for row in case_rows_raw})),
                "traffic_profile_values": ";".join(sorted({row.get("traffic_profile", "") for row in case_rows_raw})),
                "finish_step_values": ";".join(sorted({row.get("finish_step", "") for row in case_rows_raw})),
            }
        )
    return case_rows


def build_report(root):
    rows, fields = read_csv(root / SOURCE_CSV)
    protocol = load_protocol(root)
    issues = []
    validate_schema(rows, fields, protocol, issues)
    validate_design(rows, protocol, issues)
    validate_values(rows, issues)
    summary_link_stats = validate_summary_links(root, rows, issues)
    severity_counts = Counter(issue["severity"] for issue in issues)
    category_counts = Counter(issue["category"] for issue in issues)
    algorithms = sorted({row.get("algorithm", "") for row in rows})
    cases = sorted({case_id(row) for row in rows})
    status = "pass" if severity_counts.get("error", 0) == 0 else "review_required"
    return {
        "status": status,
        "source_csv": SOURCE_CSV,
        "summary": {
            "status": status,
            "row_count": len(rows),
            "column_count": len(fields),
            "case_count": len(cases),
            "algorithm_count": len(algorithms),
            "issue_count": len(issues),
            "error_count": severity_counts.get("error", 0),
            "warning_count": severity_counts.get("warning", 0),
            "severity_counts": dict(sorted(severity_counts.items())),
            "category_counts": dict(sorted(category_counts.items())),
            "summary_files_compared": summary_link_stats["summary_files_compared"],
            "summary_files_missing": summary_link_stats["summary_files_missing"],
            "summary_field_mismatches": summary_link_stats["summary_field_mismatches"],
        },
        "observed": {
            "algorithms": algorithms,
            "benchmarks": sorted({row.get("_benchmark", "") for row in rows}),
            "num_agents": sorted({row.get("num_agents", "") for row in rows}, key=lambda x: int(x) if str(x).isdigit() else x),
            "columns": fields,
        },
        "expected": {
            "row_count": EXPECTED_ROW_COUNT,
            "case_count": EXPECTED_CASE_COUNT,
            "algorithm_count": EXPECTED_ALGORITHM_COUNT,
            "column_count": EXPECTED_COLUMN_COUNT,
            "algorithms": protocol["expected_algorithms"],
            "columns": protocol["expected_columns"],
        },
        "issues": issues,
        "case_rows": build_case_rows(rows),
        "note": "This audit checks the frozen confirmatory source-data table, matched-case completeness, metric ranges, event-conditioned fields, and summary JSON back-links. It does not add new empirical runs.",
    }


def build_markdown(report):
    summary = report["summary"]
    lines = [
        "# T-ITS Source Data Integrity Audit",
        "",
        "该审计检查冻结确认性在线矩阵的 source CSV 是否满足顶刊投稿所需的数据完整性：schema、240-run 规模、30 个 matched cases、每 case 8 个算法、指标取值范围、事件条件字段、summary JSON 回链和关键字段一致性。",
        "",
        "## Summary",
        "",
    ]
    for key, value in summary.items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Observed Design",
            "",
            f"- Algorithms: {', '.join(report['observed']['algorithms'])}",
            f"- Benchmarks: {', '.join(report['observed']['benchmarks'])}",
            f"- Vehicle counts: {', '.join(report['observed']['num_agents'])}",
            "",
            "## Blocking Issues",
            "",
        ]
    )
    errors = [issue for issue in report["issues"] if issue["severity"] == "error"]
    if not errors:
        lines.append("No blocking source-data integrity errors were found.")
    else:
        lines.extend(["| category | row | field | expected | observed | message |", "|---|---|---|---|---|---|"])
        for issue in errors[:80]:
            lines.append(
                f"| {issue['category']} | `{issue['row_id']}` | `{issue['field']}` | {issue['expected']} | {issue['observed']} | {issue['message']} |"
            )
        if len(errors) > 80:
            lines.append(f"| ... | ... | ... | ... | ... | {len(errors) - 80} additional errors omitted; see CSV. |")
    warnings = [issue for issue in report["issues"] if issue["severity"] == "warning"]
    lines.extend(["", "## Warnings", ""])
    if not warnings:
        lines.append("No source-data warnings were found.")
    else:
        lines.extend(["| category | row | field | message |", "|---|---|---|---|"])
        for issue in warnings[:80]:
            lines.append(f"| {issue['category']} | `{issue['row_id']}` | `{issue['field']}` | {issue['message']} |")
        if len(warnings) > 80:
            lines.append(f"| ... | ... | ... | {len(warnings) - 80} additional warnings omitted; see CSV. |")
    lines.extend(
        [
            "",
            "## Regeneration Command",
            "",
            "```bash",
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_source_data_integrity_audit.py --out-dir outputs/tits_dynamic_graph/tits_source_data_integrity_audit",
            "```",
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Audit the frozen T-ITS confirmatory source-data table.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/tits_source_data_integrity_audit")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    out_dir = root / args.out_dir
    materials = out_dir / "materials"
    tables = out_dir / "tables"
    materials.mkdir(parents=True, exist_ok=True)
    tables.mkdir(parents=True, exist_ok=True)

    report = build_report(root)
    paths = {
        "audit_md": write_text(materials / "SOURCE_DATA_INTEGRITY_AUDIT.md", build_markdown(report)),
        "audit_json": write_json(materials / "SOURCE_DATA_INTEGRITY_AUDIT.json", report),
        "issues_csv": write_csv(
            tables / "source_data_integrity_issues.csv",
            report["issues"],
            ["severity", "category", "row_id", "case_id", "field", "expected", "observed", "message"],
        ),
        "case_matrix_csv": write_csv(
            tables / "source_data_case_matrix.csv",
            report["case_rows"],
            ["case_id", "benchmark", "num_agents", "seed", "algorithm_count", "algorithms", "track_path_values", "traffic_profile_values", "finish_step_values"],
        ),
    }
    manifest = {
        "status": report["status"],
        "out_dir": args.out_dir,
        "summary": report["summary"],
        "paths": paths,
    }
    manifest_path = write_json(out_dir / "tits_source_data_integrity_audit_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, "status": report["status"], "summary": report["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
