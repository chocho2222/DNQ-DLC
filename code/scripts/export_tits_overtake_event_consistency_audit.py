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


def to_int(value):
    value = to_float(value)
    if value is None:
        return None
    return int(round(value))


def close(left, right, tol=1e-6):
    if left is None and right is None:
        return True
    if left is None or right is None:
        return False
    return abs(float(left) - float(right)) <= tol


def run_id(row):
    return f"{row.get('_benchmark')}|n{row.get('num_agents')}|seed{row.get('seed')}|{row.get('algorithm')}"


def case_id(row):
    return f"{row.get('_benchmark')}|n{row.get('num_agents')}|seed{row.get('seed')}"


def mean(values):
    values = [value for value in values if value is not None]
    return sum(values) / len(values) if values else None


def event_value(event, field):
    value = event.get(field)
    if isinstance(value, bool):
        return float(value)
    return to_float(value)


def derived_event_metrics(events):
    event_count = len(events)
    on_track_count = sum(1 for event in events if bool(event.get("on_track_overtake")))
    elegant_count = sum(1 for event in events if bool(event.get("elegant_overtake")))
    first_complete = min((to_int(event.get("complete_step")) for event in events if to_int(event.get("complete_step")) is not None), default=None)
    first_start = min((to_int(event.get("start_step")) for event in events if to_int(event.get("start_step")) is not None), default=None)
    first_event = min(
        (event for event in events if to_int(event.get("complete_step")) is not None),
        key=lambda event: to_int(event.get("complete_step")),
        default=None,
    )
    window_grass = [event_value(event, "window_grass_rate") for event in events]
    window_lateral = [event_value(event, "window_max_abs_lateral") for event in events]
    return {
        "event_count": event_count,
        "on_track_count": on_track_count,
        "elegant_count": elegant_count,
        "on_track_rate": on_track_count / event_count if event_count else 0.0,
        "elegant_rate": elegant_count / event_count if event_count else 0.0,
        "time_to_first_overtake": first_complete,
        "overtake_start_step": first_start,
        "overtake_start_to_complete_time": event_value(first_event, "duration_steps") if first_event else None,
        "window_grass_rate_mean": mean(window_grass),
        "window_max_abs_lateral_mean": mean(window_lateral),
    }


def compare_metric(issues, rid, field, derived, summary, source, tol=1e-6, allow_blank=False):
    summary_value = to_float(summary.get(field))
    source_value = to_float(source.get(field))
    if allow_blank and derived is None and summary_value is None and source_value is None:
        return True
    ok_summary = close(derived, summary_value, tol=tol)
    ok_source = close(derived, source_value, tol=tol)
    if not ok_summary or not ok_source:
        issues.append(
            {
                "run_id": rid,
                "severity": "error",
                "category": "event_metric_mismatch",
                "field": field,
                "derived_value": "" if derived is None else derived,
                "summary_value": "" if summary_value is None else summary_value,
                "source_csv_value": "" if source_value is None else source_value,
                "message": "event-derived metric does not match summary/source data",
            }
        )
    return ok_summary and ok_source


def validate_event_schema(issues, rid, events, finish_step):
    required = [
        "opponent",
        "start_step",
        "complete_step",
        "duration_steps",
        "window_steps",
        "window_grass_rate",
        "window_backward_rate",
        "window_max_abs_lateral",
        "on_track_overtake",
        "elegant_overtake",
    ]
    event_pass_count = 0
    for index, event in enumerate(events):
        if not isinstance(event, dict):
            issues.append(
                {
                    "run_id": rid,
                    "severity": "error",
                    "category": "event_shape",
                    "field": "overtake_events",
                    "derived_value": "",
                    "summary_value": "",
                    "source_csv_value": "",
                    "message": f"event {index} is not an object",
                }
            )
            continue
        missing = [field for field in required if field not in event]
        if missing:
            issues.append(
                {
                    "run_id": rid,
                    "severity": "error",
                    "category": "event_schema",
                    "field": ";".join(missing),
                    "derived_value": "",
                    "summary_value": "",
                    "source_csv_value": "",
                    "message": f"event {index} missing required fields",
                }
            )
        start = to_int(event.get("start_step"))
        complete = to_int(event.get("complete_step"))
        duration = to_int(event.get("duration_steps"))
        window_steps = to_int(event.get("window_steps"))
        if start is None or complete is None or duration is None:
            issues.append(
                {
                    "run_id": rid,
                    "severity": "error",
                    "category": "event_timing",
                    "field": "start_step;complete_step;duration_steps",
                    "derived_value": "",
                    "summary_value": "",
                    "source_csv_value": "",
                    "message": f"event {index} has incomplete timing",
                }
            )
        else:
            if complete < start:
                issues.append({"run_id": rid, "severity": "error", "category": "event_timing", "field": "complete_step", "derived_value": complete, "summary_value": "", "source_csv_value": "", "message": f"event {index} completes before it starts"})
            if duration != complete - start:
                issues.append({"run_id": rid, "severity": "error", "category": "event_timing", "field": "duration_steps", "derived_value": duration, "summary_value": complete - start, "source_csv_value": "", "message": f"event {index} duration does not equal complete-start"})
            if finish_step is not None and complete > finish_step:
                issues.append({"run_id": rid, "severity": "error", "category": "event_timing", "field": "complete_step", "derived_value": complete, "summary_value": finish_step, "source_csv_value": "", "message": f"event {index} completes after finish_step"})
        if window_steps is not None and duration is not None and window_steps != duration + 1:
            issues.append({"run_id": rid, "severity": "error", "category": "event_window", "field": "window_steps", "derived_value": window_steps, "summary_value": (duration + 1), "source_csv_value": "", "message": f"event {index} window_steps does not equal duration+1"})
        for field in ["window_grass_rate", "window_backward_rate", "window_contact_proxy"]:
            value = to_float(event.get(field))
            if value is not None and not (0.0 <= value <= 1.0):
                issues.append({"run_id": rid, "severity": "error", "category": "event_range", "field": field, "derived_value": value, "summary_value": "", "source_csv_value": "", "message": f"event {index} rate outside [0,1]"})
        if bool(event.get("elegant_overtake")) and not bool(event.get("on_track_overtake")):
            issues.append({"run_id": rid, "severity": "error", "category": "event_invariant", "field": "elegant_overtake", "derived_value": True, "summary_value": "", "source_csv_value": "", "message": f"event {index} satisfies desirable overtaking behavior without on-track flag"})
        event_pass_count += 1
    return event_pass_count


def validate_run(row, root):
    rid = run_id(row)
    issues = []
    summary_path = root / row.get("_summary_file", "")
    if not summary_path.exists():
        return None, [{"run_id": rid, "severity": "error", "category": "summary_missing", "field": "_summary_file", "derived_value": "", "summary_value": "", "source_csv_value": row.get("_summary_file", ""), "message": "summary JSON is missing"}]
    summary = read_json(summary_path)
    events = summary.get("overtake_events", [])
    if not isinstance(events, list):
        events = []
        issues.append({"run_id": rid, "severity": "error", "category": "event_shape", "field": "overtake_events", "derived_value": "", "summary_value": "", "source_csv_value": "", "message": "overtake_events is not a list"})
    finish_step = to_int(summary.get("finish_step"))
    event_pass_count = validate_event_schema(issues, rid, events, finish_step)
    derived = derived_event_metrics(events)

    compare_metric(issues, rid, "overtake_count", derived["event_count"], summary, row, tol=0.0)
    compare_metric(issues, rid, "on_track_overtake_count", derived["on_track_count"], summary, row, tol=0.0)
    compare_metric(issues, rid, "elegant_overtake_count", derived["elegant_count"], summary, row, tol=0.0)
    compare_metric(issues, rid, "on_track_overtake_rate", derived["on_track_rate"], summary, row, tol=1e-6)
    compare_metric(issues, rid, "elegant_overtake_rate", derived["elegant_rate"], summary, row, tol=1e-6)
    compare_metric(issues, rid, "time_to_first_overtake", derived["time_to_first_overtake"], summary, row, tol=0.0, allow_blank=True)
    compare_metric(issues, rid, "overtake_start_to_complete_time", derived["overtake_start_to_complete_time"], summary, row, tol=0.0, allow_blank=True)
    compare_metric(issues, rid, "overtake_window_grass_rate_mean", derived["window_grass_rate_mean"], summary, row, tol=1e-6, allow_blank=True)
    compare_metric(issues, rid, "overtake_window_max_abs_lateral_mean", derived["window_max_abs_lateral_mean"], summary, row, tol=1e-6, allow_blank=True)

    error_count = sum(1 for issue in issues if issue["severity"] == "error")
    run = {
        "run_id": rid,
        "benchmark": row.get("_benchmark", ""),
        "algorithm": row.get("algorithm", ""),
        "num_agents": row.get("num_agents", ""),
        "seed": row.get("seed", ""),
        "summary_file": row.get("_summary_file", ""),
        "event_count": derived["event_count"],
        "event_schema_pass_count": event_pass_count,
        "on_track_overtake_count": derived["on_track_count"],
        "elegant_overtake_count": derived["elegant_count"],
        "time_to_first_overtake": "" if derived["time_to_first_overtake"] is None else derived["time_to_first_overtake"],
        "overtake_start_to_complete_time": "" if derived["overtake_start_to_complete_time"] is None else derived["overtake_start_to_complete_time"],
        "window_grass_rate_mean": "" if derived["window_grass_rate_mean"] is None else derived["window_grass_rate_mean"],
        "window_max_abs_lateral_mean": "" if derived["window_max_abs_lateral_mean"] is None else derived["window_max_abs_lateral_mean"],
        "error_count": error_count,
        "warning_count": sum(1 for issue in issues if issue["severity"] == "warning"),
        "status": "pass" if error_count == 0 else "review_required",
    }
    return run, issues


def build_algorithm_rows(run_rows):
    by_algorithm = defaultdict(list)
    for row in run_rows:
        by_algorithm[row["algorithm"]].append(row)
    rows = []
    for algorithm, items in sorted(by_algorithm.items()):
        rows.append(
            {
                "algorithm": algorithm,
                "run_count": len(items),
                "pass_count": sum(1 for row in items if row["status"] == "pass"),
                "total_overtake_events": sum(int(row["event_count"]) for row in items),
                "total_on_track_events": sum(int(row["on_track_overtake_count"]) for row in items),
                "total_elegant_events": sum(int(row["elegant_overtake_count"]) for row in items),
                "runs_with_overtake": sum(1 for row in items if int(row["event_count"]) > 0),
                "status": "pass" if all(row["status"] == "pass" for row in items) else "review_required",
            }
        )
    return rows


def build_case_rows(run_rows):
    by_case = defaultdict(list)
    for row in run_rows:
        by_case[(row["benchmark"], row["num_agents"], row["seed"])].append(row)
    rows = []
    for (benchmark, num_agents, seed), items in sorted(by_case.items()):
        rows.append(
            {
                "case_id": f"{benchmark}|n{num_agents}|seed{seed}",
                "benchmark": benchmark,
                "num_agents": num_agents,
                "seed": seed,
                "run_count": len(items),
                "pass_count": sum(1 for row in items if row["status"] == "pass"),
                "total_overtake_events": sum(int(row["event_count"]) for row in items),
                "status": "pass" if all(row["status"] == "pass" for row in items) else "review_required",
            }
        )
    return rows


def build_markdown(report):
    summary = report["summary"]
    lines = [
        "# Overtake Event Consistency Audit",
        "",
        "This audit checks the event-level source of the paper's overtaking metrics. It verifies that each summary/source-data metric can be derived from the stored `overtake_events` records.",
        "",
        "## Summary",
        "",
        f"- Status: `{report['status']}`",
        f"- Source rows: {summary['source_rows']}",
        f"- Runs checked: {summary['run_count']}",
        f"- Passing runs: {summary['run_pass_count']}",
        f"- Matched cases: {summary['matched_case_count']}",
        f"- Algorithms: {summary['algorithm_count']}",
        f"- Total overtake events: {summary['total_overtake_events']}",
        f"- On-track events: {summary['total_on_track_events']}",
        f"- Desirable events: {summary['total_elegant_events']}",
        f"- Error issues: {summary['error_count']}",
        f"- Warning issues: {summary['warning_count']}",
        "",
        "## What Is Checked",
        "",
        "- `overtake_count` equals the number of stored overtake events.",
        "- `on_track_overtake_count/rate` and `elegant_overtake_count/rate` match event flags.",
        "- `time_to_first_overtake` and `overtake_start_to_complete_time` match the earliest completed event, which is the metric definition used by the online evaluator.",
        "- Overtake-window grass and lateral metrics match the mean over event windows.",
        "- Event timing invariants hold: completion follows start, duration equals complete-start, and window length equals duration+1.",
        "- An event cannot be marked as satisfying desirable overtaking behavior unless it is also an on-track overtake.",
        "",
        "## Outputs",
        "",
        f"- Run table: `{report['paths']['run_table']}`",
        f"- Algorithm table: `{report['paths']['algorithm_table']}`",
        f"- Case table: `{report['paths']['case_table']}`",
        f"- Issue table: `{report['paths']['issue_table']}`",
        f"- Machine-readable report: `{report['paths']['audit_json']}`",
        "",
        "## Regeneration",
        "",
        "```bash",
        "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_overtake_event_consistency_audit.py --out-dir outputs/tits_dynamic_graph/tits_overtake_event_consistency_audit",
        "```",
    ]
    return "\n".join(lines)


def build_report(root):
    source_rows = read_csv(root / SOURCE_CSV)
    run_rows = []
    issue_rows = []
    for row in source_rows:
        run_row, issues = validate_run(row, root)
        if run_row:
            run_rows.append(run_row)
        issue_rows.extend(issues)
    algorithm_rows = build_algorithm_rows(run_rows)
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
            "run_count": len(run_rows),
            "run_pass_count": sum(1 for row in run_rows if row["status"] == "pass"),
            "matched_case_count": len(case_rows),
            "algorithm_count": len(algorithm_rows),
            "total_overtake_events": sum(int(row["event_count"]) for row in run_rows),
            "total_on_track_events": sum(int(row["on_track_overtake_count"]) for row in run_rows),
            "total_elegant_events": sum(int(row["elegant_overtake_count"]) for row in run_rows),
            "error_count": severity_counts.get("error", 0),
            "warning_count": severity_counts.get("warning", 0),
            "issue_count": len(issue_rows),
            "expected_rows": EXPECTED_ROWS,
            "expected_cases": EXPECTED_CASES,
            "expected_algorithms": EXPECTED_ALGORITHMS,
            "severity_counts": dict(sorted(severity_counts.items())),
            "category_counts": dict(sorted(category_counts.items())),
        },
        "run_rows": run_rows,
        "algorithm_rows": algorithm_rows,
        "case_rows": case_rows,
        "issue_rows": issue_rows,
    }


def main():
    parser = argparse.ArgumentParser(description="Audit overtake-event consistency for the T-ITS formal benchmark.")
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/tits_overtake_event_consistency_audit")
    args = parser.parse_args()
    root = Path.cwd()
    out_dir = Path(args.out_dir)
    tables = out_dir / "tables"
    materials = out_dir / "materials"
    report = build_report(root)
    run_fields = [
        "run_id", "benchmark", "algorithm", "num_agents", "seed", "summary_file", "event_count",
        "event_schema_pass_count", "on_track_overtake_count", "elegant_overtake_count",
        "time_to_first_overtake", "overtake_start_to_complete_time", "window_grass_rate_mean",
        "window_max_abs_lateral_mean", "error_count", "warning_count", "status",
    ]
    algorithm_fields = ["algorithm", "run_count", "pass_count", "total_overtake_events", "total_on_track_events", "total_elegant_events", "runs_with_overtake", "status"]
    case_fields = ["case_id", "benchmark", "num_agents", "seed", "run_count", "pass_count", "total_overtake_events", "status"]
    issue_fields = ["run_id", "severity", "category", "field", "derived_value", "summary_value", "source_csv_value", "message"]
    paths = {
        "run_table": write_csv(tables / "overtake_event_consistency_run_rows.csv", report["run_rows"], run_fields),
        "algorithm_table": write_csv(tables / "overtake_event_consistency_algorithm_rows.csv", report["algorithm_rows"], algorithm_fields),
        "case_table": write_csv(tables / "overtake_event_consistency_case_rows.csv", report["case_rows"], case_fields),
        "issue_table": write_csv(tables / "overtake_event_consistency_issue_rows.csv", report["issue_rows"], issue_fields),
        "audit_json": write_json(materials / "OVERTAKE_EVENT_CONSISTENCY_AUDIT.json", {k: v for k, v in report.items() if not k.endswith("_rows")}),
    }
    report["paths"] = paths
    paths["audit_md"] = write_text(materials / "OVERTAKE_EVENT_CONSISTENCY_AUDIT.md", build_markdown(report))
    manifest = {
        "status": report["status"],
        "out_dir": str(out_dir),
        "summary": report["summary"],
        "paths": paths,
    }
    manifest_path = write_json(out_dir / "tits_overtake_event_consistency_audit_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, "status": manifest["status"], "summary": manifest["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
