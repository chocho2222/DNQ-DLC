#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path


SOURCE_CSV = "outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv"
CASE_COMMANDS = "outputs/tits_dynamic_graph/v6_confirmatory_preflight/tables/v6_confirmatory_case_commands.csv"

EXPECTED_ROWS = 240
EXPECTED_CASES = 30
EXPECTED_ALGORITHMS = 8

IDENTITY_FIELDS = ["_benchmark", "algorithm", "seed", "num_agents", "track_path", "traffic_profile"]
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
BOOL_FIELDS = {"target_completed_lap", "overtake_aware_planner"}
STRING_FIELDS = {"algorithm", "track_path", "traffic_profile"}


def read_csv(path):
    path = Path(path)
    if not path.exists():
        return [], []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader), list(reader.fieldnames or [])


def read_json(path):
    path = Path(path)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


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


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def blank(value):
    return value is None or str(value).strip() == ""


def to_float(value):
    if blank(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def values_match(csv_value, summary_value, field):
    if field in BOOL_FIELDS:
        if blank(csv_value) and summary_value in (None, ""):
            return True
        left = str(csv_value).strip().lower()
        if isinstance(summary_value, bool):
            right = "true" if summary_value else "false"
        else:
            right = str(summary_value).strip().lower()
        return left == right
    if field in STRING_FIELDS:
        if blank(csv_value) and summary_value in (None, ""):
            return True
        return str(csv_value) == str(summary_value)
    left = to_float(csv_value)
    if summary_value is None and left is None:
        return True
    right = to_float(summary_value)
    if left is None or right is None:
        return False
    return abs(left - right) <= 1e-6


def run_id(row):
    return f"{row.get('_benchmark')}|n{row.get('num_agents')}|seed{row.get('seed')}|{row.get('algorithm')}"


def case_key(row):
    return (row.get("_benchmark", ""), row.get("num_agents", ""), row.get("seed", ""))


def command_key(row):
    return (row.get("benchmark", ""), row.get("num_agents", ""), row.get("seed", ""))


def case_command_index(case_commands):
    return {command_key(row): row for row in case_commands}


def build_run_rows(root, source_rows, case_commands):
    commands = case_command_index(case_commands)
    rows = []
    mismatch_rows = []
    for row in source_rows:
        summary_rel = row.get("_summary_file", "")
        summary_path = root / summary_rel
        summary_exists = summary_path.exists()
        summary = read_json(summary_path) if summary_exists else {}
        trace_rel = summary.get("trace_path", "")
        trace_path = root / trace_rel if trace_rel else None
        trace_exists = bool(trace_rel and trace_path.exists())
        command = commands.get(case_key(row), {})
        command_exists = bool(command)
        compare_count = 0
        mismatch_count = 0
        mismatch_fields = []
        if summary_exists:
            for field in SUMMARY_COMPARE_FIELDS:
                if field not in row:
                    continue
                compare_count += 1
                if not values_match(row.get(field), summary.get(field), field):
                    mismatch_count += 1
                    mismatch_fields.append(field)
                    mismatch_rows.append(
                        {
                            "run_id": run_id(row),
                            "field": field,
                            "source_csv_value": row.get(field, ""),
                            "summary_json_value": summary.get(field, ""),
                            "summary_file": summary_rel,
                        }
                    )
        identity_ok = (
            summary_exists
            and str(summary.get("summary_path", "")) == summary_rel
            and all(values_match(row.get(field), summary.get(field), field) for field in IDENTITY_FIELDS if field in row)
        )
        command_out_dir_match = bool(command_exists and summary_rel.startswith(command.get("out_dir", "")))
        rows.append(
            {
                "run_id": run_id(row),
                "benchmark": row.get("_benchmark", ""),
                "algorithm": row.get("algorithm", ""),
                "num_agents": row.get("num_agents", ""),
                "seed": row.get("seed", ""),
                "track_path": row.get("track_path", ""),
                "traffic_profile": row.get("traffic_profile", ""),
                "summary_file": summary_rel,
                "summary_exists": summary_exists,
                "summary_sha256": sha256_file(summary_path) if summary_exists else "",
                "trace_file": trace_rel,
                "trace_exists": trace_exists,
                "trace_sha256": sha256_file(trace_path) if trace_exists else "",
                "case_command_exists": command_exists,
                "case_command_out_dir": command.get("out_dir", ""),
                "case_command_out_dir_match": command_out_dir_match,
                "identity_ok": identity_ok,
                "compared_fields": compare_count,
                "mismatch_count": mismatch_count,
                "mismatch_fields": ";".join(mismatch_fields),
                "status": "pass" if summary_exists and trace_exists and command_exists and command_out_dir_match and identity_ok and mismatch_count == 0 else "review_required",
            }
        )
    return rows, mismatch_rows


def build_case_rows(source_rows, run_rows):
    by_case = defaultdict(list)
    run_by_key = defaultdict(list)
    for row in source_rows:
        by_case[case_key(row)].append(row)
    for row in run_rows:
        run_by_key[(row["benchmark"], row["num_agents"], row["seed"])].append(row)
    cases = []
    for key, rows in sorted(by_case.items()):
        benchmark, num_agents, seed = key
        run_checks = run_by_key[key]
        algorithms = sorted(row.get("algorithm", "") for row in rows)
        pass_count = sum(1 for row in run_checks if row["status"] == "pass")
        cases.append(
            {
                "case_id": f"{benchmark}|n{num_agents}|seed{seed}",
                "benchmark": benchmark,
                "num_agents": num_agents,
                "seed": seed,
                "algorithm_count": len(algorithms),
                "algorithms": ";".join(algorithms),
                "run_pass_count": pass_count,
                "run_count": len(run_checks),
                "status": "pass" if len(algorithms) == EXPECTED_ALGORITHMS and pass_count == len(run_checks) else "review_required",
            }
        )
    return cases


def build_report(root):
    source_rows, _ = read_csv(root / SOURCE_CSV)
    case_commands, _ = read_csv(root / CASE_COMMANDS)
    run_rows, mismatch_rows = build_run_rows(root, source_rows, case_commands)
    case_rows = build_case_rows(source_rows, run_rows)
    counts = Counter(row["status"] for row in run_rows)
    algorithms = sorted({row.get("algorithm", "") for row in source_rows if row.get("algorithm", "")})
    cases = {case_key(row) for row in source_rows}
    failed_runs = [row for row in run_rows if row["status"] != "pass"]
    summary = {
        "status": "pass" if not failed_runs and len(source_rows) == EXPECTED_ROWS and len(cases) == EXPECTED_CASES and len(algorithms) == EXPECTED_ALGORITHMS else "review_required",
        "source_rows": len(source_rows),
        "case_command_rows": len(case_commands),
        "matched_case_count": len(cases),
        "algorithm_count": len(algorithms),
        "run_pass_count": counts.get("pass", 0),
        "run_review_required_count": len(failed_runs),
        "summary_missing_count": sum(1 for row in run_rows if not row["summary_exists"]),
        "trace_missing_count": sum(1 for row in run_rows if not row["trace_exists"]),
        "case_command_missing_count": sum(1 for row in run_rows if not row["case_command_exists"]),
        "case_command_out_dir_mismatch_count": sum(1 for row in run_rows if not row["case_command_out_dir_match"]),
        "identity_mismatch_count": sum(1 for row in run_rows if not row["identity_ok"]),
        "summary_field_mismatch_count": len(mismatch_rows),
    }
    return {
        "status": summary["status"],
        "summary": summary,
        "run_rows": run_rows,
        "case_rows": case_rows,
        "mismatch_rows": mismatch_rows,
        "boundary": "This audit verifies existing source-data provenance to per-run summary JSON, trace JSON and frozen case commands. It does not rerun simulations or validate physical realism.",
    }


def build_markdown(report):
    summary = report["summary"]
    lines = [
        "# T-ITS Run-Level Provenance Audit",
        "",
        "该审计把正式 240-run source data 的每一行追溯到对应的 summary JSON、trace JSON 和 frozen case command，用于回答审稿人“每个论文数据点从哪里来、是否能逐 run 复核”的问题。它只验证现有证据链，不新增仿真实验。",
        "",
        "## Summary",
        "",
    ]
    for key, value in summary.items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Blocking Run Rows", ""])
    failed = [row for row in report["run_rows"] if row["status"] != "pass"]
    if not failed:
        lines.append("No blocking run-level provenance issues were found.")
    else:
        lines.extend(["| run | summary | trace | command | mismatches |", "|---|---|---|---|---|"])
        for row in failed[:80]:
            lines.append(
                f"| `{row['run_id']}` | {row['summary_exists']} | {row['trace_exists']} | {row['case_command_exists']} | {row['mismatch_fields']} |"
            )
        if len(failed) > 80:
            lines.append(f"| ... | ... | ... | ... | {len(failed) - 80} additional rows omitted; see CSV. |")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `summary_exists` 证明 source CSV 的 `_summary_file` 可以打开。",
            "- `trace_exists` 证明 summary JSON 记录的逐步 trace 仍可追溯。",
            "- `case_command_out_dir_match` 证明该 run 位于 frozen case command 声明的输出目录下。",
            "- `identity_ok` 和 `mismatch_count=0` 证明 source CSV 的关键指标与 summary JSON 一致。",
            "",
            "## Regeneration Command",
            "",
            "```bash",
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_run_level_provenance_audit.py --out-dir outputs/tits_dynamic_graph/tits_run_level_provenance_audit",
            "```",
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Export run-level provenance audit for T-ITS source data.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/tits_run_level_provenance_audit")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    out_dir = root / args.out_dir
    materials = out_dir / "materials"
    tables = out_dir / "tables"
    report = build_report(root)
    paths = {
        "audit_md": write_text(materials / "RUN_LEVEL_PROVENANCE_AUDIT.md", build_markdown(report)),
        "audit_json": write_json(materials / "RUN_LEVEL_PROVENANCE_AUDIT.json", report),
        "run_rows_csv": write_csv(
            tables / "run_level_provenance_rows.csv",
            report["run_rows"],
            [
                "run_id",
                "benchmark",
                "algorithm",
                "num_agents",
                "seed",
                "track_path",
                "traffic_profile",
                "summary_file",
                "summary_exists",
                "summary_sha256",
                "trace_file",
                "trace_exists",
                "trace_sha256",
                "case_command_exists",
                "case_command_out_dir",
                "case_command_out_dir_match",
                "identity_ok",
                "compared_fields",
                "mismatch_count",
                "mismatch_fields",
                "status",
            ],
        ),
        "case_rows_csv": write_csv(
            tables / "run_level_case_provenance.csv",
            report["case_rows"],
            ["case_id", "benchmark", "num_agents", "seed", "algorithm_count", "algorithms", "run_pass_count", "run_count", "status"],
        ),
        "mismatches_csv": write_csv(
            tables / "run_level_summary_mismatches.csv",
            report["mismatch_rows"],
            ["run_id", "field", "source_csv_value", "summary_json_value", "summary_file"],
        ),
    }
    manifest = {
        "status": report["status"],
        "out_dir": args.out_dir,
        "summary": report["summary"],
        "paths": paths,
        "boundary": report["boundary"],
    }
    manifest_path = write_json(out_dir / "tits_run_level_provenance_audit_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, "status": report["status"], "summary": report["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
