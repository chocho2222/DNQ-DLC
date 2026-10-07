#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import json
import re
from pathlib import Path


OURS_SAFE = "v6_runtime_dynamic_neighborhood_safe"
QUALITY = "quality_proposal_dlc_world_v1"
DLC = "dlc_world_original"
RULE = "rule_expert_gate"

DEFAULT_INDEX = "outputs/tits_dynamic_graph/tits_manuscript_package/tables/manuscript_numeric_index.csv"
DEFAULT_RESULTS = "outputs/tits_dynamic_graph/tits_manuscript_package/materials/RESULTS_DRAFT.md"
DEFAULT_OVERALL = "outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack/tables/confirmatory_overall_statistics.csv"
DEFAULT_SCENARIO = "outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack/tables/confirmatory_scenario_statistics.csv"
DEFAULT_PAIRED = "outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack/tables/confirmatory_paired_tests_vs_dlc.csv"


def read_csv(path):
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path, rows, fields):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return str(path)


def write_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")
    return str(path)


def write_json(path, data):
    return write_text(path, json.dumps(data, ensure_ascii=False, indent=2))


def f(value):
    if value in (None, "", "nan", "NaN", "NA"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def fmt(value, digits=3):
    value = f(value)
    if value is None:
        return "NA"
    return f"{value:.{digits}f}"


def mean_ci(row, metric, digits=3):
    mean = f(row.get(f"{metric}_mean"))
    low = f(row.get(f"{metric}_ci95_low"))
    high = f(row.get(f"{metric}_ci95_high"))
    if mean is None:
        return "NA"
    if low is None or high is None:
        return fmt(mean, digits)
    return f"{fmt(mean, digits)} [{fmt(low, digits)}, {fmt(high, digits)}]"


def find_overall(rows, algorithm):
    for row in rows:
        if row.get("algorithm") == algorithm:
            return row
    raise KeyError(algorithm)


def find_scenario(rows, benchmark, num_agents, algorithm):
    for row in rows:
        if row.get("benchmark") == benchmark and int(row.get("num_agents", -1)) == int(num_agents) and row.get("algorithm") == algorithm:
            return row
    raise KeyError((benchmark, num_agents, algorithm))


def find_paired(rows, algorithm, metric):
    for row in rows:
        if row.get("algorithm") == algorithm and row.get("metric") == metric:
            return row
    raise KeyError((algorithm, metric))


def build_expected(overall, scenario, paired):
    safe = find_overall(overall, OURS_SAFE)
    quality = find_overall(overall, QUALITY)
    dlc = find_overall(overall, DLC)
    rule = find_overall(overall, RULE)
    n8_safe = find_scenario(scenario, "vehicle_count_extrapolation", 8, OURS_SAFE)
    n8_dlc = find_scenario(scenario, "vehicle_count_extrapolation", 8, DLC)
    monza6_safe = find_scenario(scenario, "monza_external_track", 6, OURS_SAFE)
    monza6_dlc = find_scenario(scenario, "monza_external_track", 6, DLC)
    monza4_quality = find_scenario(scenario, "monza_external_track", 4, QUALITY)
    monza4_dlc = find_scenario(scenario, "monza_external_track", 4, DLC)
    return [
        ("overall_safe_success", mean_ci(safe, "overtake_success_rate"), "confirmatory_overall_statistics.csv"),
        ("overall_dlc_success", mean_ci(dlc, "overtake_success_rate"), "confirmatory_overall_statistics.csv"),
        ("overall_safe_elegant", mean_ci(safe, "elegant_overtake_rate"), "confirmatory_overall_statistics.csv"),
        ("overall_dlc_elegant", mean_ci(dlc, "elegant_overtake_rate"), "confirmatory_overall_statistics.csv"),
        ("overall_safe_overtake_time", mean_ci(safe, "overtake_start_to_complete_time", 1), "confirmatory_overall_statistics.csv"),
        ("overall_dlc_overtake_time", mean_ci(dlc, "overtake_start_to_complete_time", 1), "confirmatory_overall_statistics.csv"),
        ("overall_quality_success", mean_ci(quality, "overtake_success_rate"), "confirmatory_overall_statistics.csv"),
        ("overall_rule_elegant", mean_ci(rule, "elegant_overtake_rate"), "confirmatory_overall_statistics.csv"),
        ("n8_safe_elegant", mean_ci(n8_safe, "elegant_overtake_rate"), "confirmatory_scenario_statistics.csv"),
        ("n8_dlc_elegant", mean_ci(n8_dlc, "elegant_overtake_rate"), "confirmatory_scenario_statistics.csv"),
        ("n8_safe_overtake_time", mean_ci(n8_safe, "overtake_start_to_complete_time", 1), "confirmatory_scenario_statistics.csv"),
        ("n8_dlc_overtake_time", mean_ci(n8_dlc, "overtake_start_to_complete_time", 1), "confirmatory_scenario_statistics.csv"),
        ("monza6_safe_success", mean_ci(monza6_safe, "overtake_success_rate"), "confirmatory_scenario_statistics.csv"),
        ("monza6_dlc_success", mean_ci(monza6_dlc, "overtake_success_rate"), "confirmatory_scenario_statistics.csv"),
        ("monza6_safe_elegant", mean_ci(monza6_safe, "elegant_overtake_rate"), "confirmatory_scenario_statistics.csv"),
        ("monza6_dlc_elegant", mean_ci(monza6_dlc, "elegant_overtake_rate"), "confirmatory_scenario_statistics.csv"),
        ("monza4_quality_elegant", mean_ci(monza4_quality, "elegant_overtake_rate"), "confirmatory_scenario_statistics.csv"),
        ("monza4_dlc_elegant", mean_ci(monza4_dlc, "elegant_overtake_rate"), "confirmatory_scenario_statistics.csv"),
        ("paired_safe_success_improvement", fmt(find_paired(paired, OURS_SAFE, "overtake_success_rate")["improvement_vs_dlc_mean"]), "confirmatory_paired_tests_vs_dlc.csv"),
        ("paired_safe_elegant_improvement", fmt(find_paired(paired, OURS_SAFE, "elegant_overtake_rate")["improvement_vs_dlc_mean"]), "confirmatory_paired_tests_vs_dlc.csv"),
        ("paired_safe_time_improvement_steps", fmt(find_paired(paired, OURS_SAFE, "overtake_start_to_complete_time")["improvement_vs_dlc_mean"], 1), "confirmatory_paired_tests_vs_dlc.csv"),
    ]


def compare_index(index_rows, expected_rows, results_text):
    actual = {row["claim_key"]: row for row in index_rows}
    rows = []
    for key, expected_value, expected_source in expected_rows:
        actual_row = actual.get(key, {})
        actual_value = actual_row.get("value", "")
        actual_source = actual_row.get("source", "")
        value_match = actual_value == expected_value
        source_match = actual_source == expected_source
        appears_in_results = expected_value in results_text
        rows.append(
            {
                "claim_key": key,
                "expected_value": expected_value,
                "actual_value": actual_value,
                "expected_source": expected_source,
                "actual_source": actual_source,
                "value_match": value_match,
                "source_match": source_match,
                "appears_in_results_draft": appears_in_results,
                "status": "pass" if value_match and source_match else "mismatch",
            }
        )
    extra_keys = sorted(set(actual) - {key for key, _, _ in expected_rows})
    for key in extra_keys:
        rows.append(
            {
                "claim_key": key,
                "expected_value": "",
                "actual_value": actual[key].get("value", ""),
                "expected_source": "",
                "actual_source": actual[key].get("source", ""),
                "value_match": False,
                "source_match": False,
                "appears_in_results_draft": actual[key].get("value", "") in results_text,
                "status": "unexpected_extra_key",
            }
        )
    return rows


def scan_result_numbers(results_text, index_rows):
    indexed_values = {row["value"] for row in index_rows}
    indexed_atomic = set()
    for value in indexed_values:
        indexed_atomic.update(re.findall(r"\d+\.\d+|\b\d+\b", value))
    allowed_context_numbers = {"240", "8", "4", "5", "6"}
    rows = []
    seen = set()
    for match in re.finditer(r"\d+\.\d+|\b\d+\b", results_text):
        token = match.group(0)
        line_no = results_text.count("\n", 0, match.start()) + 1
        line_start = results_text.rfind("\n", 0, match.start()) + 1
        line_end = results_text.find("\n", match.start())
        if line_end == -1:
            line_end = len(results_text)
        line = results_text[line_start:line_end].strip()
        key = (line_no, token, line)
        if key in seen:
            continue
        seen.add(key)
        if token in indexed_atomic:
            status = "covered_by_numeric_index"
        elif token in allowed_context_numbers:
            status = "allowed_protocol_context"
        else:
            status = "review_required"
        rows.append({"line": line_no, "number": token, "status": status, "line_text": line})
    return rows


def build_markdown(report):
    summary = report["summary"]
    lines = [
        "# T-ITS Manuscript Numeric Trace Audit",
        "",
        "该审计从正式 confirmatory evidence tables 重新计算 manuscript numeric index 中的投稿数值，并检查 Results 草稿中的数字是否能被 numeric index 覆盖。它用于降低论文写作中手工改数、复制错误或图表版本错配的风险。",
        "",
        "## Summary",
        "",
    ]
    for key, value in summary.items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Numeric Index Checks",
            "",
            "| Claim key | Status | Expected | Actual | Source | In Results |",
            "|---|---|---|---|---|---|",
        ]
    )
    for row in report["index_checks"]:
        lines.append(
            f"| {row['claim_key']} | {row['status']} | {row['expected_value']} | {row['actual_value']} | {row['actual_source']} | {row['appears_in_results_draft']} |"
        )
    review = [row for row in report["result_number_scan"] if row["status"] == "review_required"]
    lines.extend(["", "## Result-Draft Number Scan", ""])
    if not review:
        lines.append("No untraced numeric tokens were found in RESULTS_DRAFT.md beyond allowed protocol context numbers.")
    else:
        lines.extend(["| Line | Number | Context |", "|---:|---:|---|"])
        for row in review:
            lines.append(f"| {row['line']} | {row['number']} | {row['line_text']} |")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `pass` means the numeric index value and source table name exactly match independently recomputed values from formal evidence tables.",
            "- `appears_in_results_draft=False` is not automatically blocking because some numeric keys may be retained for later manuscript editing, but it is reported for author awareness.",
            "- Result-draft numbers `240`, `8`, `4`, `5`, and `6` are treated as protocol context rather than statistical values.",
            "- After editing Results, regenerating evidence tables, or changing rounding precision, rerun this audit before final manuscript submission.",
            "",
            "## Regeneration Command",
            "",
            "```bash",
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_manuscript_numeric_trace_audit.py --out-dir outputs/tits_dynamic_graph/tits_manuscript_numeric_trace_audit",
            "```",
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Audit manuscript numeric values against formal T-ITS evidence tables.")
    parser.add_argument("--index", default=DEFAULT_INDEX)
    parser.add_argument("--results", default=DEFAULT_RESULTS)
    parser.add_argument("--overall", default=DEFAULT_OVERALL)
    parser.add_argument("--scenario", default=DEFAULT_SCENARIO)
    parser.add_argument("--paired", default=DEFAULT_PAIRED)
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/tits_manuscript_numeric_trace_audit")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    materials = out_dir / "materials"
    tables = out_dir / "tables"
    materials.mkdir(parents=True, exist_ok=True)
    tables.mkdir(parents=True, exist_ok=True)

    index_rows = read_csv(args.index)
    expected_rows = build_expected(read_csv(args.overall), read_csv(args.scenario), read_csv(args.paired))
    results_text = Path(args.results).read_text(encoding="utf-8")
    index_checks = compare_index(index_rows, expected_rows, results_text)
    number_scan = scan_result_numbers(results_text, index_rows)
    blocking = [row for row in index_checks if row["status"] != "pass"]
    review_numbers = [row for row in number_scan if row["status"] == "review_required"]
    summary = {
        "status": "pass" if not blocking and not review_numbers else "review_required",
        "numeric_index_rows": len(index_rows),
        "expected_numeric_keys": len(expected_rows),
        "index_mismatch_count": len(blocking),
        "result_number_tokens": len(number_scan),
        "untraced_result_number_count": len(review_numbers),
        "results_draft": args.results,
    }
    report = {
        "status": summary["status"],
        "summary": summary,
        "inputs": {
            "index": args.index,
            "results": args.results,
            "overall": args.overall,
            "scenario": args.scenario,
            "paired": args.paired,
        },
        "index_checks": index_checks,
        "result_number_scan": number_scan,
        "note": "This audit checks manuscript-facing numeric traceability. It does not judge scientific novelty or final IEEE formatting.",
    }
    index_fields = [
        "claim_key",
        "expected_value",
        "actual_value",
        "expected_source",
        "actual_source",
        "value_match",
        "source_match",
        "appears_in_results_draft",
        "status",
    ]
    number_fields = ["line", "number", "status", "line_text"]
    paths = {
        "audit_md": write_text(materials / "MANUSCRIPT_NUMERIC_TRACE_AUDIT.md", build_markdown(report)),
        "audit_json": write_json(materials / "MANUSCRIPT_NUMERIC_TRACE_AUDIT.json", report),
        "numeric_trace_csv": write_csv(tables / "manuscript_numeric_trace_rows.csv", index_checks, index_fields),
        "result_number_scan_csv": write_csv(tables / "results_draft_number_scan.csv", number_scan, number_fields),
    }
    manifest = {
        "status": report["status"],
        "out_dir": args.out_dir,
        "summary": summary,
        "paths": paths,
    }
    manifest_path = write_json(out_dir / "tits_manuscript_numeric_trace_audit_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, "status": report["status"], "summary": summary}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
