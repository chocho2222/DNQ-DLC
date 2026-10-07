#!/usr/bin/env python
import argparse
import csv
import json
import shlex
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def split_commands(command):
    if not command or command.startswith("Use "):
        return []
    parts = []
    current = []
    tokens = shlex.split(command)
    for token in tokens:
        if token == "&&":
            if current:
                parts.append(current)
                current = []
            continue
        current.append(token)
    if current:
        parts.append(current)
    return parts


def normalize_output_paths(value):
    paths = []
    for chunk in str(value or "").replace(",", ";").split(";"):
        item = chunk.strip()
        if not item or "*" in item:
            continue
        if "/json" in item or "/csv" in item or "/md" in item:
            continue
        paths.append(item)
    return paths


def status_from_checks(checks, optional=False):
    if optional:
        return "optional_not_executed"
    return "pass" if all(checks) else "review_required"


def inspect_subcommand(root, source_kind, source_id, cost_class, command_index, tokens):
    optional = "expensive" in cost_class or "optional" in cost_class
    command_tokens = list(tokens)
    while command_tokens and "=" in command_tokens[0] and not command_tokens[0].startswith("--"):
        command_tokens.pop(0)
    python_token = command_tokens[0] if command_tokens else ""
    script_token = ""
    for token in command_tokens[1:]:
        if token.startswith("scripts/") and token.endswith(".py"):
            script_token = token
            break
    root_arg = ""
    if "--root" in command_tokens:
        idx = command_tokens.index("--root")
        if idx + 1 < len(command_tokens):
            root_arg = command_tokens[idx + 1]
    out_dir = ""
    if "--out-dir" in command_tokens:
        idx = command_tokens.index("--out-dir")
        if idx + 1 < len(command_tokens):
            out_dir = command_tokens[idx + 1]

    python_ok = python_token.endswith("python") or python_token == "python"
    script_exists = bool(script_token) and (Path(script_token).exists())
    root_ok = (not root_arg) or Path(root_arg).as_posix() == root.as_posix()
    out_parent_ok = True
    if out_dir:
        out_parent_ok = (Path(out_dir).parent).exists()
    status = status_from_checks([python_ok, script_exists, root_ok, out_parent_ok], optional=optional)
    return {
        "source_kind": source_kind,
        "source_id": source_id,
        "command_index": command_index,
        "status": status,
        "cost_class": cost_class,
        "script": script_token,
        "script_exists": script_exists,
        "python_invocation": python_token,
        "python_invocation_ok": python_ok,
        "root_arg": root_arg,
        "root_arg_ok": root_ok,
        "out_dir": out_dir,
        "out_parent_exists": out_parent_ok,
        "boundary": (
            "Optional expensive GPU rollout command is registered but not executed by preflight."
            if optional
            else "Static command preflight only; no command is executed."
        ),
    }


def inspect_route_row(root, source_kind, row):
    source_id = row.get("step_id") or row.get("route_id") or row.get("step_or_route_id")
    cost_class = row.get("cost_class") or row.get("reviewer_time") or row.get("tier", "")
    commands = split_commands(row.get("command", ""))
    command_rows = [
        inspect_subcommand(root, source_kind, source_id, cost_class, idx + 1, tokens)
        for idx, tokens in enumerate(commands)
    ]
    output_paths = normalize_output_paths(row.get("outputs") or row.get("expected_outputs"))
    output_parent_missing = []
    for item in output_paths:
        parent = (root / item).parent
        if not parent.exists():
            output_parent_missing.append(item)
    optional_route = "expensive" in cost_class or "optional" in cost_class
    route_status = "optional_not_executed" if optional_route else "pass"
    if not command_rows and not optional_route:
        route_status = "review_required"
    if any(r["status"] == "review_required" for r in command_rows) or output_parent_missing:
        route_status = "review_required"
    return {
        "source_kind": source_kind,
        "source_id": source_id,
        "status": route_status,
        "cost_class": cost_class,
        "command_count": len(command_rows),
        "output_parent_missing_count": len(output_parent_missing),
        "output_parent_missing": ";".join(output_parent_missing),
        "command": row.get("command", ""),
        "expected_outputs": row.get("outputs") or row.get("expected_outputs", ""),
        "boundary": (
            "Use provenance for selected expensive reruns; this preflight does not execute rollout commands."
            if "expensive" in cost_class or "optional" in cost_class
            else "Fast route command is syntactically and locally resolvable before execution."
        ),
    }, command_rows


def build_report(root):
    route = load_json(root / "materials" / "REVIEWER_REPLICATION_ROUTE.json")
    gpu = load_json(root / "materials" / "GPU_RERUN_READINESS.json")
    provenance = load_json(root / "tables" / "artifact_provenance.json")
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    smoke = load_json(root / "materials" / "PUBLICATION_SMOKE_TEST.json")

    route_rows = []
    command_rows = []
    for item in route.get("quickstart", []):
        inspected, commands = inspect_route_row(root, "quickstart", item)
        route_rows.append(inspected)
        command_rows.extend(commands)
    for item in route.get("rows", []):
        inspected, commands = inspect_route_row(root, "route", item)
        route_rows.append(inspected)
        command_rows.extend(commands)

    review_required = [item for item in route_rows + command_rows if item["status"] == "review_required"]
    optional = [item for item in route_rows + command_rows if item["status"] == "optional_not_executed"]
    scripts_missing = [item for item in command_rows if not item["script_exists"]]
    bad_roots = [item for item in command_rows if not item["root_arg_ok"]]
    bad_python = [item for item in command_rows if not item["python_invocation_ok"]]

    artifact_total = len(provenance.get("artifacts", []))
    artifact_complete = provenance.get("complete_count", 0)
    return {
        "root": str(root),
        "title": "Reviewer Command Preflight",
        "purpose": (
            "Statically check reviewer-facing replication commands before execution: command scripts, Python "
            "invocations, package root arguments, output parent directories, and optional GPU rerun boundaries."
        ),
        "summary": {
            "status": "pass" if not review_required else "review_required",
            "route_row_count": len(route_rows),
            "subcommand_count": len(command_rows),
            "review_required_count": len(review_required),
            "optional_not_executed_count": len(optional),
            "missing_script_count": len(scripts_missing),
            "bad_root_arg_count": len(bad_roots),
            "bad_python_invocation_count": len(bad_python),
            "artifact_provenance": f"{artifact_complete}/{artifact_total}",
            "gpu_rerun_readiness_status": gpu["summary"].get("status"),
            "publication_verification_status": verification["summary"].get("status"),
            "publication_smoke_test_reference": "materials/PUBLICATION_SMOKE_TEST.json",
        },
        "route_rows": route_rows,
        "command_rows": command_rows,
        "interpretation": (
            "This preflight is a static readiness audit. It does not execute expensive rollouts, does not create "
            "new empirical evidence, and preserves the simulator-only and no-broad-robustness claim boundaries."
        ),
    }


def write_csv(report, route_path, command_path):
    route_fields = [
        "source_kind",
        "source_id",
        "status",
        "cost_class",
        "command_count",
        "output_parent_missing_count",
        "output_parent_missing",
        "expected_outputs",
        "boundary",
    ]
    with route_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=route_fields)
        writer.writeheader()
        for row in report["route_rows"]:
            writer.writerow({field: row.get(field, "") for field in route_fields})

    command_fields = [
        "source_kind",
        "source_id",
        "command_index",
        "status",
        "cost_class",
        "script",
        "script_exists",
        "python_invocation",
        "python_invocation_ok",
        "root_arg",
        "root_arg_ok",
        "out_dir",
        "out_parent_exists",
        "boundary",
    ]
    with command_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=command_fields)
        writer.writeheader()
        for row in report["command_rows"]:
            writer.writerow({field: row.get(field, "") for field in command_fields})


def write_markdown(report, path):
    lines = [
        "# Reviewer Command Preflight",
        "",
        report["purpose"],
        "",
        report["interpretation"],
        "",
        "## Summary",
        "",
    ]
    for key, value in report["summary"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Route Checks",
            "",
            "| source | status | cost | commands | missing output parents | boundary |",
            "|---|---|---|---:|---:|---|",
        ]
    )
    for item in report["route_rows"]:
        lines.append(
            f"| {item['source_kind']}:{item['source_id']} | {item['status']} | {item['cost_class']} | "
            f"{item['command_count']} | {item['output_parent_missing_count']} | {item['boundary']} |"
        )
    lines.extend(
        [
            "",
            "## Subcommand Checks",
            "",
            "| source | index | status | script | python_ok | root_ok | out_parent_ok | boundary |",
            "|---|---:|---|---|---|---|---|---|",
        ]
    )
    for item in report["command_rows"]:
        lines.append(
            f"| {item['source_kind']}:{item['source_id']} | {item['command_index']} | {item['status']} | "
            f"`{item['script']}` | {item['python_invocation_ok']} | {item['root_arg_ok']} | "
            f"{item['out_parent_exists']} | {item['boundary']} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export reviewer command preflight audit.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_report(root)
    out_json = materials / "REVIEWER_COMMAND_PREFLIGHT.json"
    out_md = materials / "REVIEWER_COMMAND_PREFLIGHT.md"
    route_csv = materials / "REVIEWER_COMMAND_PREFLIGHT_ROUTES.csv"
    command_csv = materials / "REVIEWER_COMMAND_PREFLIGHT_COMMANDS.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, route_csv, command_csv)
    print(
        json.dumps(
            {
                "json": str(out_json),
                "markdown": str(out_md),
                "route_csv": str(route_csv),
                "command_csv": str(command_csv),
                "summary": report["summary"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
