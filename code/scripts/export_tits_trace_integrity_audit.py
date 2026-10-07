#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path


SOURCE_CSV = "outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv"

EXPECTED_ROWS = 240
EXPECTED_CASES = 30
EXPECTED_ALGORITHMS = 8
REQUIRED_STEP_FIELDS = ["step", "rank", "track_index", "action", "speed", "telemetry", "positions", "done"]
REQUIRED_TELEMETRY_FIELDS = ["progress", "lateral_error", "heading_cos", "on_grass", "backward"]
SUMMARY_TOL = 1e-5


def read_csv(path):
    path = Path(path)
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


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


def run_id(row):
    return f"{row.get('_benchmark')}|n{row.get('num_agents')}|seed{row.get('seed')}|{row.get('algorithm')}"


def case_id(row):
    return f"{row.get('_benchmark')}|n{row.get('num_agents')}|seed{row.get('seed')}"


def close(a, b, tol=SUMMARY_TOL):
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    return abs(float(a) - float(b)) <= tol


def vector_length_ok(value, num_agents):
    return isinstance(value, list) and len(value) == num_agents


def check_vector_lengths(step, num_agents):
    failures = []
    for field in ["rank", "track_index", "action", "speed", "positions"]:
        if not vector_length_ok(step.get(field), num_agents):
            failures.append(field)
    telemetry = step.get("telemetry", {})
    if not isinstance(telemetry, dict):
        failures.append("telemetry")
        return failures
    for field in REQUIRED_TELEMETRY_FIELDS:
        if not vector_length_ok(telemetry.get(field), num_agents):
            failures.append(f"telemetry.{field}")
    return failures


def trace_metrics(trace, target_agent):
    if not trace:
        return {}
    grass_values = []
    backward_values = []
    lateral_values = []
    heading_values = []
    progress_values = []
    latency_values = []
    min_pair_values = []
    for step in trace:
        telemetry = step.get("telemetry", {})
        on_grass = telemetry.get("on_grass", [])
        backward = telemetry.get("backward", [])
        lateral = telemetry.get("lateral_error", [])
        heading = telemetry.get("heading_cos", [])
        progress = telemetry.get("progress", [])
        if len(on_grass) > target_agent:
            grass_values.append(bool(on_grass[target_agent]))
        if len(backward) > target_agent:
            backward_values.append(bool(backward[target_agent]))
        if len(lateral) > target_agent and to_float(lateral[target_agent]) is not None:
            lateral_values.append(abs(float(lateral[target_agent])))
        if len(heading) > target_agent and to_float(heading[target_agent]) is not None:
            heading_values.append(float(heading[target_agent]))
        if len(progress) > target_agent and to_float(progress[target_agent]) is not None:
            progress_values.append(float(progress[target_agent]))
        if to_float(step.get("compute_latency_ms")) is not None:
            latency_values.append(float(step.get("compute_latency_ms")))
        if to_float(step.get("min_pair_distance")) is not None:
            min_pair_values.append(float(step.get("min_pair_distance")))
    last = trace[-1]
    return {
        "trace_length": len(trace),
        "first_step": trace[0].get("step"),
        "last_step": last.get("step"),
        "last_done": bool(last.get("done")),
        "target_progress_last": progress_values[-1] if progress_values else None,
        "target_grass_rate_raw": sum(grass_values) / len(grass_values) if grass_values else None,
        "target_backward_rate_raw": sum(backward_values) / len(backward_values) if backward_values else None,
        "target_mean_abs_lateral_raw": sum(lateral_values) / len(lateral_values) if lateral_values else None,
        "target_heading_error_mean_rad_proxy": (
            sum(math.acos(max(-1.0, min(1.0, value))) for value in heading_values) / len(heading_values)
            if heading_values else None
        ),
        "compute_latency_mean_raw": sum(latency_values) / len(latency_values) if latency_values else None,
        "compute_latency_p95_raw": sorted(latency_values)[int(math.ceil(0.95 * len(latency_values))) - 1] if latency_values else None,
        "min_pair_distance_min_raw": min(min_pair_values) if min_pair_values else None,
    }


def validate_trace(row, root):
    rid = run_id(row)
    summary_path = root / row.get("_summary_file", "")
    issues = []
    if not summary_path.exists():
        return None, [{"run_id": rid, "severity": "error", "category": "summary_missing", "field": "_summary_file", "message": "summary JSON is missing"}]
    try:
        summary = read_json(summary_path)
    except Exception as exc:
        return None, [{"run_id": rid, "severity": "error", "category": "summary_parse", "field": "_summary_file", "message": str(exc)}]
    trace_rel = summary.get("trace_path", "")
    trace_path = root / trace_rel if trace_rel else None
    if not trace_path or not trace_path.exists():
        return None, [{"run_id": rid, "severity": "error", "category": "trace_missing", "field": "trace_path", "message": "trace JSON is missing"}]
    try:
        trace = read_json(trace_path)
    except Exception as exc:
        return None, [{"run_id": rid, "severity": "error", "category": "trace_parse", "field": "trace_path", "message": str(exc)}]
    if not isinstance(trace, list) or not trace:
        return None, [{"run_id": rid, "severity": "error", "category": "trace_shape", "field": "trace", "message": "trace JSON must be a nonempty list"}]

    num_agents = int(summary.get("num_agents", row.get("num_agents", 0)))
    target_agent = int(summary.get("target_agent", num_agents - 1))
    steps = [step.get("step") for step in trace if isinstance(step, dict)]
    expected_steps = list(range(1, len(trace) + 1))
    step_sequence_ok = steps == expected_steps
    if not step_sequence_ok:
        issues.append({"run_id": rid, "severity": "error", "category": "step_sequence", "field": "step", "message": "trace steps are not contiguous from 1"})

    missing_required_count = 0
    vector_failure_count = 0
    for index, step in enumerate(trace):
        if not isinstance(step, dict):
            issues.append({"run_id": rid, "severity": "error", "category": "step_shape", "field": "trace", "message": f"step {index} is not an object"})
            continue
        missing = [field for field in REQUIRED_STEP_FIELDS if field not in step]
        if missing:
            missing_required_count += len(missing)
            issues.append({"run_id": rid, "severity": "error", "category": "missing_step_field", "field": ";".join(missing), "message": f"step {index + 1} missing required fields"})
        vector_failures = check_vector_lengths(step, num_agents)
        if vector_failures:
            vector_failure_count += len(vector_failures)
            issues.append({"run_id": rid, "severity": "error", "category": "vector_length", "field": ";".join(vector_failures), "message": f"step {index + 1} has vehicle-dimension mismatch"})

    metrics = trace_metrics(trace, target_agent)
    summary_checks = [
        ("steps_run", metrics.get("trace_length"), summary.get("steps_run"), 0.0),
        ("finish_step", metrics.get("last_step"), summary.get("finish_step"), 0.0),
        ("target_progress", metrics.get("target_progress_last"), summary.get("target_progress"), 1e-5),
        ("target_mean_abs_lateral", metrics.get("target_mean_abs_lateral_raw"), summary.get("target_mean_abs_lateral"), 1.5e-2),
        ("compute_latency_ms", metrics.get("compute_latency_mean_raw"), summary.get("compute_latency_ms"), 2e-5),
    ]
    summary_mismatch_fields = []
    for field, observed, expected, tol in summary_checks:
        if not close(observed, to_float(expected), tol=tol):
            summary_mismatch_fields.append(field)
            issues.append(
                {
                    "run_id": rid,
                    "severity": "error",
                    "category": "summary_trace_consistency",
                    "field": field,
                    "message": f"trace-derived {field} does not match summary",
                }
            )

    # The environment updates some grass counters before recording the first trace frame.
    # Keep this as a warning-level drift diagnostic rather than a blocking equality check.
    grass_drift = None
    if metrics.get("target_grass_rate_raw") is not None and to_float(summary.get("target_grass_rate")) is not None:
        grass_drift = abs(metrics["target_grass_rate_raw"] - float(summary["target_grass_rate"]))
        if grass_drift > 0.02:
            issues.append(
                {
                    "run_id": rid,
                    "severity": "warning",
                    "category": "grass_rate_drift",
                    "field": "target_grass_rate",
                    "message": "raw trace grass rate differs from summary by more than 0.02",
                }
            )

    pass_errors = sum(1 for issue in issues if issue["severity"] == "error")
    row_out = {
        "run_id": rid,
        "benchmark": row.get("_benchmark", ""),
        "algorithm": row.get("algorithm", ""),
        "num_agents": num_agents,
        "seed": row.get("seed", ""),
        "summary_file": row.get("_summary_file", ""),
        "trace_file": trace_rel,
        "trace_length": metrics.get("trace_length"),
        "steps_run_summary": summary.get("steps_run"),
        "finish_step_summary": summary.get("finish_step"),
        "step_sequence_ok": step_sequence_ok,
        "missing_required_count": missing_required_count,
        "vector_failure_count": vector_failure_count,
        "target_progress_trace": metrics.get("target_progress_last"),
        "target_progress_summary": summary.get("target_progress"),
        "target_grass_rate_trace_raw": metrics.get("target_grass_rate_raw"),
        "target_grass_rate_summary": summary.get("target_grass_rate"),
        "target_grass_rate_abs_drift": grass_drift,
        "target_mean_abs_lateral_trace_raw": metrics.get("target_mean_abs_lateral_raw"),
        "target_mean_abs_lateral_summary": summary.get("target_mean_abs_lateral"),
        "compute_latency_ms_trace_raw": metrics.get("compute_latency_mean_raw"),
        "compute_latency_ms_summary": summary.get("compute_latency_ms"),
        "summary_mismatch_fields": ";".join(summary_mismatch_fields),
        "error_count": pass_errors,
        "warning_count": sum(1 for issue in issues if issue["severity"] == "warning"),
        "status": "pass" if pass_errors == 0 else "review_required",
    }
    return row_out, issues


def build_case_rows(run_rows):
    by_case = defaultdict(list)
    for row in run_rows:
        by_case[(row["benchmark"], str(row["num_agents"]), row["seed"])].append(row)
    case_rows = []
    for (benchmark, num_agents, seed), rows in sorted(by_case.items()):
        case_rows.append(
            {
                "case_id": f"{benchmark}|n{num_agents}|seed{seed}",
                "benchmark": benchmark,
                "num_agents": num_agents,
                "seed": seed,
                "run_count": len(rows),
                "pass_count": sum(1 for row in rows if row["status"] == "pass"),
                "total_trace_steps": sum(int(row["trace_length"] or 0) for row in rows),
                "algorithms": ";".join(sorted(row["algorithm"] for row in rows)),
                "status": "pass" if all(row["status"] == "pass" for row in rows) else "review_required",
            }
        )
    return case_rows


def build_markdown(report):
    summary = report["summary"]
    lines = [
        "# Trace Integrity Audit",
        "",
        "This audit checks that the formal online source-data rows are backed by usable step-level traces rather than summary-only records.",
        "",
        "## Summary",
        "",
        f"- Status: `{report['status']}`",
        f"- Source rows: {summary['source_rows']}",
        f"- Trace runs checked: {summary['trace_run_count']}",
        f"- Passing trace runs: {summary['trace_pass_count']}",
        f"- Matched cases: {summary['matched_case_count']}",
        f"- Algorithms: {summary['algorithm_count']}",
        f"- Total trace steps: {summary['total_trace_steps']}",
        f"- Error issues: {summary['error_count']}",
        f"- Warning issues: {summary['warning_count']}",
        f"- Summary/trace mismatch count: {summary['summary_trace_mismatch_count']}",
        f"- Step sequence failures: {summary['step_sequence_failure_count']}",
        f"- Vehicle-dimension failures: {summary['vector_failure_run_count']}",
        "",
        "## What Is Checked",
        "",
        "- Every linked trace JSON exists and is parseable.",
        "- Every trace is a nonempty step list with contiguous step indices.",
        "- Per-step rank, action, speed, position and telemetry arrays match the declared vehicle count.",
        "- Target progress, mean absolute lateral error, compute latency, step count and finish step can be recomputed from trace-level records and match the linked summary within explicit floating-point/update-order tolerances.",
        "- Raw trace grass rate is reported as a diagnostic drift because the environment-level counter includes update timing outside the stored first trace frame.",
        "",
        "## Outputs",
        "",
        f"- Run table: `{report['paths']['run_table']}`",
        f"- Case table: `{report['paths']['case_table']}`",
        f"- Issue table: `{report['paths']['issue_table']}`",
        f"- Machine-readable report: `{report['paths']['audit_json']}`",
        "",
        "## Regeneration",
        "",
        "```bash",
        "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_trace_integrity_audit.py --out-dir outputs/tits_dynamic_graph/tits_trace_integrity_audit",
        "```",
    ]
    return "\n".join(lines)


def build_report(root):
    source_rows = read_csv(root / SOURCE_CSV)
    run_rows = []
    issue_rows = []
    for row in source_rows:
        run_row, issues = validate_trace(row, root)
        if run_row:
            run_rows.append(run_row)
        issue_rows.extend(issues)
    case_rows = build_case_rows(run_rows)
    severity_counts = Counter(issue["severity"] for issue in issue_rows)
    category_counts = Counter(issue["category"] for issue in issue_rows)
    status = "pass" if severity_counts.get("error", 0) == 0 and len(run_rows) == len(source_rows) else "review_required"
    return {
        "status": status,
        "source_csv": SOURCE_CSV,
        "summary": {
            "status": status,
            "source_rows": len(source_rows),
            "trace_run_count": len(run_rows),
            "trace_pass_count": sum(1 for row in run_rows if row["status"] == "pass"),
            "matched_case_count": len(case_rows),
            "algorithm_count": len({row.get("algorithm", "") for row in source_rows}),
            "total_trace_steps": sum(int(row["trace_length"] or 0) for row in run_rows),
            "error_count": severity_counts.get("error", 0),
            "warning_count": severity_counts.get("warning", 0),
            "issue_count": len(issue_rows),
            "summary_trace_mismatch_count": category_counts.get("summary_trace_consistency", 0),
            "step_sequence_failure_count": category_counts.get("step_sequence", 0),
            "vector_failure_run_count": sum(1 for row in run_rows if int(row["vector_failure_count"] or 0) > 0),
            "expected_rows": EXPECTED_ROWS,
            "expected_cases": EXPECTED_CASES,
            "expected_algorithms": EXPECTED_ALGORITHMS,
            "severity_counts": dict(sorted(severity_counts.items())),
            "category_counts": dict(sorted(category_counts.items())),
        },
        "run_rows": run_rows,
        "case_rows": case_rows,
        "issue_rows": issue_rows,
    }


def main():
    parser = argparse.ArgumentParser(description="Audit step-level trace integrity for the T-ITS formal online benchmark.")
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/tits_trace_integrity_audit")
    args = parser.parse_args()
    root = Path.cwd()
    out_dir = Path(args.out_dir)
    tables = out_dir / "tables"
    materials = out_dir / "materials"
    report = build_report(root)
    run_fields = [
        "run_id", "benchmark", "algorithm", "num_agents", "seed", "summary_file", "trace_file",
        "trace_length", "steps_run_summary", "finish_step_summary", "step_sequence_ok",
        "missing_required_count", "vector_failure_count", "target_progress_trace",
        "target_progress_summary", "target_grass_rate_trace_raw", "target_grass_rate_summary",
        "target_grass_rate_abs_drift", "target_mean_abs_lateral_trace_raw",
        "target_mean_abs_lateral_summary", "compute_latency_ms_trace_raw",
        "compute_latency_ms_summary", "summary_mismatch_fields", "error_count", "warning_count", "status",
    ]
    case_fields = ["case_id", "benchmark", "num_agents", "seed", "run_count", "pass_count", "total_trace_steps", "algorithms", "status"]
    issue_fields = ["run_id", "severity", "category", "field", "message"]
    paths = {
        "run_table": write_csv(tables / "trace_integrity_run_rows.csv", report["run_rows"], run_fields),
        "case_table": write_csv(tables / "trace_integrity_case_rows.csv", report["case_rows"], case_fields),
        "issue_table": write_csv(tables / "trace_integrity_issue_rows.csv", report["issue_rows"], issue_fields),
        "audit_json": write_json(materials / "TRACE_INTEGRITY_AUDIT.json", {k: v for k, v in report.items() if not k.endswith("_rows")}),
    }
    report["paths"] = paths
    paths["audit_md"] = write_text(materials / "TRACE_INTEGRITY_AUDIT.md", build_markdown(report))
    manifest = {
        "status": report["status"],
        "out_dir": str(out_dir),
        "summary": report["summary"],
        "paths": paths,
    }
    manifest_path = write_json(out_dir / "tits_trace_integrity_audit_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, "status": manifest["status"], "summary": manifest["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
