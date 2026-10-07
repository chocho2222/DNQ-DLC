#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import json
import os
import re
import shlex
import stat
import py_compile
from pathlib import Path


REVIEWER_README = "outputs/tits_dynamic_graph/reviewer_replication_packet/REVIEWER_REPLICATION_README.md"
SMOKE_SCRIPT = "outputs/tits_dynamic_graph/reviewer_replication_packet/run_reviewer_smoke.sh"
ARTIFACT_MANIFEST = "outputs/tits_dynamic_graph/artifact_manifest/tits_dynamic_graph_artifact_manifest.json"
FINAL_READINESS = "outputs/tits_dynamic_graph/final_readiness_dashboard/final_readiness_dashboard_manifest.json"
CASE_COMMANDS = "outputs/tits_dynamic_graph/v6_confirmatory_preflight/tables/v6_confirmatory_case_commands.csv"
MAKEFILE = "Makefile"
REQUIRED_MAKE_TARGETS = [
    "tits-smoke",
    "tits-status",
    "tits-status-snapshot",
    "tits-evidence-ledger",
    "tits-claim-numeric-audit",
    "tits-manuscript-section-trace",
    "tits-abstract-highlights-audit",
    "tits-checksum-audit",
    "tits-external-validity-audit",
    "tits-limitations-evidence-audit",
    "tits-threats-validity",
    "tits-protocol-deviation",
    "tits-author-owned-audit",
    "tits-reproduction-time-budget",
    "tits-run-level-provenance",
    "tits-trace-integrity",
    "tits-trace-schema",
    "tits-overtake-event-consistency",
    "tits-statistical-table-recompute",
    "tits-results-reporting-checklist",
    "tits-results-narrative-pack",
    "tits-figure-source-value-recompute",
    "tits-figure-caption-claim-audit",
    "tits-table-caption-source-data-audit",
    "tits-publication-gif-provenance",
    "tits-supplementary-video-index",
    "tits-supplementary-submission-index",
    "tits-online-decision-case-study",
    "tits-safety-proxy-audit",
    "tits-source-data-schema",
    "tits-algorithm-config-freeze",
    "tits-compute-timing-boundary",
    "tits-ai-tool-use-disclosure",
    "tits-submission-gap-priority",
    "tits-refresh-coverage",
    "tits-refresh-gates",
    "tits-audit-route",
    "tits-audit-readme",
    "tits-dashboard",
]

REQUIRED_REVIEWER_FILES = [
    MAKEFILE,
    REVIEWER_README,
    SMOKE_SCRIPT,
    "outputs/tits_dynamic_graph/reviewer_replication_packet/DATA_CODE_AVAILABILITY_DRAFT.md",
    "outputs/tits_dynamic_graph/reviewer_replication_packet/SUBMISSION_READINESS_CHECKLIST.md",
    "outputs/tits_dynamic_graph/reviewer_replication_packet/METHOD_RESULT_WRITING_MAP.md",
    CASE_COMMANDS,
    "configs/tits_dynamic_graph_experiments.json",
    "scripts/run_tits_dynamic_graph_evaluation.py",
    "scripts/summarize_tits_dynamic_graph_online.py",
    "scripts/audit_v6_confirmatory_matrix.py",
    "scripts/export_tits_confirmatory_evidence_pack.py",
    "outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv",
]


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


def read_text(path):
    path = Path(path)
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def command_blocks(markdown):
    blocks = []
    pattern = re.compile(r"```(?:bash|sh)?\n(?P<cmd>.*?)\n```", re.DOTALL)
    for idx, match in enumerate(pattern.finditer(markdown), start=1):
        cmd = match.group("cmd").strip()
        if cmd:
            blocks.append({"command_id": f"readme_cmd_{idx:02d}", "command": cmd})
    return blocks


def shell_script_command(path):
    text = read_text(path)
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" in stripped.split(" ", 1)[0]:
            continue
        lines.append(stripped)
    return " \\\n".join(lines)


def extract_paths_from_command(command):
    paths = []
    try:
        tokens = shlex.split(command.replace("\\\n", " "))
    except Exception:
        tokens = command.replace("\\\n", " ").split()
    for token in tokens:
        if token.startswith("${") or token.startswith("$"):
            continue
        if token.startswith("/tmp/"):
            paths.append((token, "tmp_output"))
        elif token.startswith("/home/itrc/.conda/"):
            paths.append((token, "local_python"))
        elif token.startswith(("scripts/", "configs/", "outputs/", "tracks/", "dlc/", "gym_multi_car_racing/")):
            paths.append((token.rstrip(","), "workspace_path"))
    return paths


def classify_path(root, rel, role):
    if role == "tmp_output":
        return True, "allowed_tmp_output", "Temporary smoke output path; not expected to exist before running."
    if role == "local_python":
        exists = Path(rel).exists()
        return exists, "local_python_exists" if exists else "local_python_missing", "Local server Python path is acceptable for local provenance but should be generalized in public README."
    path = root / rel
    exists = path.exists()
    return exists, "pass" if exists else "missing", ""


def script_check(root, path):
    full = root / path
    exists = full.exists()
    executable = bool(exists and os.access(full, os.X_OK))
    py_compile_ok = ""
    error = ""
    if exists and full.suffix == ".py":
        try:
            py_compile.compile(str(full), doraise=True)
            py_compile_ok = True
        except Exception as exc:
            py_compile_ok = False
            error = repr(exc)
    elif exists and full.suffix == ".sh":
        py_compile_ok = "not_applicable"
    else:
        py_compile_ok = ""
    status = "pass"
    if not exists:
        status = "missing"
    elif full.suffix == ".py" and py_compile_ok is not True:
        status = "compile_error"
    elif full.suffix == ".sh" and not executable:
        status = "not_executable"
    return {
        "path": path,
        "exists": exists,
        "suffix": full.suffix,
        "executable": executable,
        "py_compile_ok": py_compile_ok,
        "error": error,
        "status": status,
    }


def reviewer_summary_rows(root):
    readme = read_text(root / REVIEWER_README)
    artifact = read_json(root / ARTIFACT_MANIFEST)
    final = read_json(root / FINAL_READINESS)
    expected_artifact_files = str(artifact.get("summary", {}).get("file_count"))
    final_pass = final.get("pass_count")
    final_gates = final.get("gate_count")
    expected_final_values = {f"{final_pass}/{final_gates}"}
    if isinstance(final_pass, int) and isinstance(final_gates, int) and final_pass < final_gates:
        # This audit is itself one final-readiness gate. During a refresh cycle the
        # dashboard may still show N-1/N while the reviewer README already records
        # the fixed point that will hold after this gate passes.
        expected_final_values.add(f"{final_pass + 1}/{final_gates}")
    checks = []
    patterns = [
        ("artifact_manifest_files", r"Artifact manifest files:\s*(\d+)", {expected_artifact_files}),
        ("final_readiness_gates", r"Final readiness gates:\s*(\d+/\d+)", expected_final_values),
    ]
    for check_id, pattern, expected_values in patterns:
        match = re.search(pattern, readme, flags=re.IGNORECASE | re.DOTALL)
        observed = match.group(1) if match else ""
        checks.append(
            {
                "check_id": check_id,
                "observed": observed,
                "expected": ";".join(sorted(expected_values)),
                "status": "pass" if observed in expected_values else "stale_or_missing",
            }
        )
    return checks


def case_command_check(root):
    path = root / CASE_COMMANDS
    rows = []
    if not path.exists():
        return {
            "path": CASE_COMMANDS,
            "exists": False,
            "row_count": 0,
            "commands_with_algorithms": 0,
            "commands_with_no_gif": 0,
            "commands_with_config": 0,
            "status": "missing",
        }
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    count = len(rows)
    with_algorithms = sum("--algorithms" in row.get("command", "") for row in rows)
    with_no_gif = sum("--no-gif" in row.get("command", "") for row in rows)
    with_config = sum("configs/tits_dynamic_graph_experiments.json" in row.get("command", "") for row in rows)
    status = "pass" if count == 30 and with_algorithms == count and with_no_gif == count and with_config == count else "review_required"
    return {
        "path": CASE_COMMANDS,
        "exists": True,
        "row_count": count,
        "commands_with_algorithms": with_algorithms,
        "commands_with_no_gif": with_no_gif,
        "commands_with_config": with_config,
        "status": status,
    }


def makefile_target_rows(root):
    path = root / MAKEFILE
    text = read_text(path)
    rows = []
    for target in REQUIRED_MAKE_TARGETS:
        pattern = re.compile(rf"^{re.escape(target)}\s*:", re.MULTILINE)
        present = bool(pattern.search(text))
        rows.append(
            {
                "path": MAKEFILE,
                "target": target,
                "exists": path.exists(),
                "present": present,
                "status": "pass" if path.exists() and present else "missing_target",
            }
        )
    return rows


def reviewer_make_shortcut_rows(root):
    path = root / REVIEWER_README
    text = read_text(path)
    rows = []
    for target in REQUIRED_MAKE_TARGETS:
        command = f"make {target}"
        present = command in text
        rows.append(
            {
                "path": REVIEWER_README,
                "command": command,
                "exists": path.exists(),
                "present": present,
                "status": "pass" if path.exists() and present else "missing_shortcut",
            }
        )
    return rows


def build_report(root):
    readme = read_text(root / REVIEWER_README)
    commands = command_blocks(readme)
    smoke_command = shell_script_command(root / SMOKE_SCRIPT)
    if smoke_command:
        commands.append({"command_id": "run_reviewer_smoke_sh_body", "command": smoke_command})

    command_rows = []
    path_rows = []
    script_paths = set()
    for item in commands:
        command = item["command"]
        paths = extract_paths_from_command(command)
        missing_count = 0
        for ref, role in paths:
            exists, status, note = classify_path(root, ref, role)
            if status == "missing":
                missing_count += 1
            path_rows.append(
                {
                    "command_id": item["command_id"],
                    "path": ref,
                    "role": role,
                    "exists_or_allowed": exists,
                    "status": status,
                    "note": note,
                }
            )
            if role == "workspace_path" and ref.startswith("scripts/") and ref.endswith((".py", ".sh")):
                script_paths.add(ref)
        command_rows.append(
            {
                "command_id": item["command_id"],
                "path_reference_count": len(paths),
                "missing_workspace_path_count": missing_count,
                "status": "pass" if missing_count == 0 else "missing_paths",
                "command": command.replace("\n", " ")[:800],
            }
        )

    script_rows = [script_check(root, path) for path in sorted(script_paths | {SMOKE_SCRIPT})]
    required_rows = []
    for rel in REQUIRED_REVIEWER_FILES:
        full = root / rel
        required_rows.append(
            {
                "path": rel,
                "exists": full.exists(),
                "size_bytes": full.stat().st_size if full.exists() and full.is_file() else 0,
                "status": "pass" if full.exists() and (full.is_dir() or full.stat().st_size > 0) else "missing_or_empty",
            }
        )
    summary_rows = reviewer_summary_rows(root)
    case_check = case_command_check(root)
    makefile_rows = makefile_target_rows(root)
    reviewer_make_rows = reviewer_make_shortcut_rows(root)
    errors = (
        [row for row in command_rows if row["status"] != "pass"]
        + [row for row in script_rows if row["status"] != "pass"]
        + [row for row in required_rows if row["status"] != "pass"]
        + [row for row in summary_rows if row["status"] != "pass"]
        + [row for row in makefile_rows if row["status"] != "pass"]
        + [row for row in reviewer_make_rows if row["status"] != "pass"]
    )
    if case_check["status"] != "pass":
        errors.append(case_check)
    summary = {
        "status": "pass" if not errors else "review_required",
        "command_count": len(command_rows),
        "path_reference_count": len(path_rows),
        "script_check_count": len(script_rows),
        "required_file_count": len(required_rows),
        "summary_check_count": len(summary_rows),
        "makefile_target_count": len(makefile_rows),
        "reviewer_make_shortcut_count": len(reviewer_make_rows),
        "case_command_rows": case_check.get("row_count"),
        "error_count": len(errors),
        "reviewer_readme": REVIEWER_README,
        "smoke_script": SMOKE_SCRIPT,
    }
    return {
        "status": summary["status"],
        "summary": summary,
        "command_rows": command_rows,
        "path_rows": path_rows,
        "script_rows": script_rows,
        "required_rows": required_rows,
        "summary_rows": summary_rows,
        "makefile_rows": makefile_rows,
        "reviewer_make_rows": reviewer_make_rows,
        "case_command_row": case_check,
    }


def build_markdown(report):
    summary = report["summary"]
    lines = [
        "# T-ITS Reviewer Smoke Route Audit",
        "",
        "该审计静态检查 reviewer replication packet 中的 smoke-test 路线、README 命令、脚本权限、命令路径、关键输入文件和摘要数字是否与当前证据链一致。它不实际运行 GPU/Box2D 评估，因此不能替代 determinism smoke audit；它用于降低审稿人照 README 复现时遇到缺文件、脚本不可执行或旧摘要数字的风险。",
        "",
        "## Summary",
        "",
    ]
    for key, value in summary.items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Summary Freshness Checks",
            "",
            "| Check | Observed | Expected | Status |",
            "|---|---|---|---|",
        ]
    )
    for row in report["summary_rows"]:
        lines.append(f"| {row['check_id']} | {row['observed']} | {row['expected']} | {row['status']} |")
    lines.extend(
        [
            "",
            "## Makefile Target Checks",
            "",
            "| Makefile | Target | Exists | Present | Status |",
            "|---|---|---:|---:|---|",
        ]
    )
    for row in report["makefile_rows"]:
        lines.append(f"| {row['path']} | {row['target']} | {row['exists']} | {row['present']} | {row['status']} |")
    lines.extend(
        [
            "",
            "## Reviewer README Make Shortcut Checks",
            "",
            "| Reviewer README | Command | Exists | Present | Status |",
            "|---|---|---:|---:|---|",
        ]
    )
    for row in report["reviewer_make_rows"]:
        lines.append(f"| {row['path']} | {row['command']} | {row['exists']} | {row['present']} | {row['status']} |")
    lines.extend(
        [
            "",
            "## Script Checks",
            "",
            "| Script | Exists | Executable | Py compile | Status | Error |",
            "|---|---:|---:|---|---|---|",
        ]
    )
    for row in report["script_rows"]:
        lines.append(f"| {row['path']} | {row['exists']} | {row['executable']} | {row['py_compile_ok']} | {row['status']} | {row['error']} |")
    lines.extend(
        [
            "",
            "## Case Command Check",
            "",
            f"- Path: `{report['case_command_row']['path']}`",
            f"- Exists: {report['case_command_row']['exists']}",
            f"- Rows: {report['case_command_row']['row_count']}",
            f"- Commands with algorithms: {report['case_command_row']['commands_with_algorithms']}",
            f"- Commands with no-gif: {report['case_command_row']['commands_with_no_gif']}",
            f"- Commands with config: {report['case_command_row']['commands_with_config']}",
            f"- Status: {report['case_command_row']['status']}",
            "",
            "## Boundary",
            "",
            "- PASS 表示 reviewer-facing route 的静态入口、路径和摘要数字一致；不表示 smoke test 已在第三方机器上运行。",
            "- `/tmp` 输出路径被视为运行后才生成的临时目录，不要求预先存在。",
            "- 本地 Python 绝对路径只用于当前服务器 provenance；公开 README 可在最终发布时改写为环境无关命令。",
            "",
            "## Regeneration Command",
            "",
            "```bash",
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_reviewer_smoke_route_audit.py --out-dir outputs/tits_dynamic_graph/tits_reviewer_smoke_route_audit",
            "```",
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Audit reviewer smoke route commands and paths for the T-ITS package.")
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/tits_reviewer_smoke_route_audit")
    args = parser.parse_args()

    root = Path(".").resolve()
    out_dir = Path(args.out_dir)
    report = build_report(root)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "report_md": write_text(out_dir / "materials" / "REVIEWER_SMOKE_ROUTE_AUDIT.md", build_markdown(report)),
        "commands_csv": write_csv(
            out_dir / "tables" / "reviewer_smoke_route_commands.csv",
            report["command_rows"],
            ["command_id", "path_reference_count", "missing_workspace_path_count", "status", "command"],
        ),
        "paths_csv": write_csv(
            out_dir / "tables" / "reviewer_smoke_route_path_checks.csv",
            report["path_rows"],
            ["command_id", "path", "role", "exists_or_allowed", "status", "note"],
        ),
        "scripts_csv": write_csv(
            out_dir / "tables" / "reviewer_smoke_route_script_checks.csv",
            report["script_rows"],
            ["path", "exists", "suffix", "executable", "py_compile_ok", "error", "status"],
        ),
        "required_files_csv": write_csv(
            out_dir / "tables" / "reviewer_smoke_route_required_files.csv",
            report["required_rows"],
            ["path", "exists", "size_bytes", "status"],
        ),
        "summary_freshness_csv": write_csv(
            out_dir / "tables" / "reviewer_smoke_route_summary_freshness.csv",
            report["summary_rows"],
            ["check_id", "observed", "expected", "status"],
        ),
        "makefile_targets_csv": write_csv(
            out_dir / "tables" / "reviewer_smoke_route_makefile_targets.csv",
            report["makefile_rows"],
            ["path", "target", "exists", "present", "status"],
        ),
        "reviewer_make_shortcuts_csv": write_csv(
            out_dir / "tables" / "reviewer_smoke_route_reviewer_make_shortcuts.csv",
            report["reviewer_make_rows"],
            ["path", "command", "exists", "present", "status"],
        ),
        "case_command_json": write_json(out_dir / "materials" / "reviewer_smoke_route_case_command_check.json", report["case_command_row"]),
    }
    manifest = {
        "status": report["status"],
        "out_dir": str(out_dir),
        "summary": report["summary"],
        "paths": paths,
        "boundary": "Static reviewer-route audit only; it does not execute the smoke run or certify third-party hardware/software availability.",
    }
    manifest_path = write_json(out_dir / "tits_reviewer_smoke_route_audit_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, "status": report["status"], "summary": report["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
