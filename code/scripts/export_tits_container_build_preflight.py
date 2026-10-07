#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import json
import shutil
import subprocess
from pathlib import Path


DOCKERFILE_DRAFT = "outputs/tits_dynamic_graph/tits_third_party_reproduction_pack/materials/Dockerfile.draft"
APPTAINER_DRAFT = "outputs/tits_dynamic_graph/tits_third_party_reproduction_pack/materials/apptainer.def.draft"
THIRD_PARTY_PACK = "outputs/tits_dynamic_graph/tits_third_party_reproduction_pack/tits_third_party_reproduction_pack_manifest.json"
REVIEWER_SMOKE = "outputs/tits_dynamic_graph/reviewer_replication_packet/run_reviewer_smoke.sh"
SMOKE_EXECUTION_AUDIT_SCRIPT = "scripts/export_tits_reviewer_smoke_execution_audit.py"
SOURCE_DATA = "outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv"
FINAL_READINESS = "outputs/tits_dynamic_graph/final_readiness_dashboard/final_readiness_dashboard_manifest.json"


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


def run_command(command, timeout=8):
    try:
        proc = subprocess.run(command, text=True, capture_output=True, timeout=timeout)
        output = (proc.stdout + proc.stderr).strip()
        return proc.returncode, output[:2000]
    except FileNotFoundError:
        return 127, "command_not_found"
    except subprocess.TimeoutExpired:
        return 124, "timeout"
    except Exception as exc:
        return 1, f"{type(exc).__name__}: {exc}"


def tool_row(name, command, version_args, gpu_args=None):
    path = shutil.which(command)
    row = {
        "tool": name,
        "command": command,
        "path": path or "",
        "installed": bool(path),
        "version_status": "not_installed",
        "version_output": "",
        "gpu_probe_status": "not_applicable",
        "gpu_probe_output": "",
        "interpretation": "",
    }
    if path:
        code, output = run_command([command] + version_args)
        row["version_status"] = "pass" if code == 0 else f"exit_{code}"
        row["version_output"] = output.replace("\n", " | ")
        if gpu_args:
            code, output = run_command([command] + gpu_args)
            row["gpu_probe_status"] = "pass" if code == 0 else f"exit_{code}"
            row["gpu_probe_output"] = output.replace("\n", " | ")
    if name == "nvidia_smi":
        row["interpretation"] = "GPU driver query is available." if row["installed"] else "GPU driver query command is unavailable."
    else:
        row["interpretation"] = "Container runtime is locally available." if row["installed"] else "Container runtime is not installed on this server."
    return row


def count_csv_rows(path):
    path = Path(path)
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8", newline="") as handle:
        return max(sum(1 for _ in handle) - 1, 0)


def inspect_draft(path, expected_terms):
    path = Path(path)
    text = path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""
    rows = []
    for term in expected_terms:
        rows.append(
            {
                "draft": path.as_posix(),
                "check": term,
                "status": "pass" if term in text else "missing",
                "detail": f"term '{term}' present" if term in text else f"term '{term}' not found",
            }
        )
    rows.append(
        {
            "draft": path.as_posix(),
            "check": "file_exists",
            "status": "pass" if path.exists() and path.stat().st_size > 0 else "missing",
            "detail": f"{path.stat().st_size if path.exists() else 0} bytes",
        }
    )
    return rows


def build_command_rows():
    image = "tits-dynamic-graph-overtaking:reviewer-draft"
    sif = "tits_dynamic_graph_overtaking_reviewer_draft.sif"
    return [
        {
            "runtime": "docker",
            "stage": "build",
            "command": f"docker build -f {DOCKERFILE_DRAFT} -t {image} .",
            "executed_by_preflight": "no",
            "expected": "Build image from draft Dockerfile if Docker daemon and network are available.",
        },
        {
            "runtime": "docker",
            "stage": "smoke",
            "command": f"docker run --rm --gpus all {image}",
            "executed_by_preflight": "no",
            "expected": "Run reviewer smoke test and smoke execution audit with GPU access.",
        },
        {
            "runtime": "apptainer",
            "stage": "build",
            "command": f"apptainer build {sif} {APPTAINER_DRAFT}",
            "executed_by_preflight": "no",
            "expected": "Build SIF image from draft definition if Apptainer and network are available.",
        },
        {
            "runtime": "apptainer",
            "stage": "smoke",
            "command": f"apptainer run --nv {sif}",
            "executed_by_preflight": "no",
            "expected": "Run reviewer smoke test and smoke execution audit with NVIDIA GPU passthrough.",
        },
    ]


def build_report(root):
    dockerfile = root / DOCKERFILE_DRAFT
    apptainer = root / APPTAINER_DRAFT
    final = read_json(root / FINAL_READINESS)
    third_party = read_json(root / THIRD_PARTY_PACK)
    tool_rows = [
        tool_row("docker", "docker", ["--version"]),
        tool_row("apptainer", "apptainer", ["--version"]),
        tool_row("singularity", "singularity", ["--version"]),
        tool_row("nvidia_smi", "nvidia-smi", ["--query-gpu=name", "--format=csv,noheader"], ["--query-gpu=name,memory.total", "--format=csv,noheader"]),
    ]
    draft_rows = []
    draft_rows.extend(
        inspect_draft(
            dockerfile,
            [
                "FROM nvidia/cuda",
                "box2d-py==2.3.8",
                "run_reviewer_smoke.sh",
                "export_tits_reviewer_smoke_execution_audit.py",
                "--extra-index-url https://download.pytorch.org/whl/cu124",
            ],
        )
    )
    draft_rows.extend(
        inspect_draft(
            apptainer,
            [
                "Bootstrap: docker",
                "From: nvidia/cuda",
                "box2d-py==2.3.8",
                "run_reviewer_smoke.sh",
                "export_tits_reviewer_smoke_execution_audit.py",
                "%runscript",
            ],
        )
    )
    command_rows = build_command_rows()
    docker_available = any(row["tool"] == "docker" and row["installed"] for row in tool_rows)
    apptainer_available = any(row["tool"] in {"apptainer", "singularity"} and row["installed"] for row in tool_rows)
    gpu_probe_available = any(row["tool"] == "nvidia_smi" and row["installed"] for row in tool_rows)
    missing_inputs = [
        rel
        for rel in [
            DOCKERFILE_DRAFT,
            APPTAINER_DRAFT,
            THIRD_PARTY_PACK,
            REVIEWER_SMOKE,
            SMOKE_EXECUTION_AUDIT_SCRIPT,
            SOURCE_DATA,
            FINAL_READINESS,
        ]
        if not (root / rel).exists()
    ]
    draft_missing = [row for row in draft_rows if row["status"] != "pass"]
    build_feasibility = "runtime_available_not_built" if docker_available or apptainer_available else "blocked_no_container_runtime"
    summary = {
        "status": "pass" if not missing_inputs and not draft_missing else "review_required",
        "source_rows": count_csv_rows(root / SOURCE_DATA),
        "final_readiness": f"{final.get('pass_count', 'NA')}/{final.get('gate_count', 'NA')}",
        "third_party_pack_status": third_party.get("status"),
        "docker_available": docker_available,
        "apptainer_or_singularity_available": apptainer_available,
        "nvidia_smi_available": gpu_probe_available,
        "build_attempted": False,
        "image_built": False,
        "build_feasibility": build_feasibility,
        "missing_input_count": len(missing_inputs),
        "draft_missing_check_count": len(draft_missing),
    }
    return {
        "status": summary["status"],
        "summary": summary,
        "tool_rows": tool_rows,
        "draft_rows": draft_rows,
        "command_rows": command_rows,
        "missing_inputs": missing_inputs,
        "boundary": [
            "This preflight records local tool availability and draft integrity; it does not build or certify a container image.",
            "The current server may have GPUs even when Docker/Apptainer are not installed.",
            "A future container build must record image digest, CUDA runtime, smoke-test output, smoke execution audit output and artifact manifest updates before being claimed in the manuscript.",
        ],
    }


def build_markdown(report):
    lines = [
        "# T-ITS Container Build Preflight",
        "",
        "该预检记录当前服务器是否具备 Docker/Apptainer 构建条件，并检查容器草案文件是否包含复现所需的关键依赖和 smoke test 入口。",
        "它不执行容器构建，因此不能被写成“已发布/已认证镜像”。",
        "",
        "## Summary",
        "",
    ]
    for key, value in report["summary"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Local Tool Probe", "", "| Tool | Installed | Version status | Path | Interpretation |", "|---|---:|---|---|---|"])
    for row in report["tool_rows"]:
        lines.append(f"| {row['tool']} | {row['installed']} | {row['version_status']} | `{row['path']}` | {row['interpretation']} |")
    lines.extend(["", "## Draft Integrity", "", "| Draft | Check | Status | Detail |", "|---|---|---|---|"])
    for row in report["draft_rows"]:
        lines.append(f"| `{row['draft']}` | {row['check']} | {row['status']} | {row['detail']} |")
    lines.extend(["", "## Commands Not Executed By Preflight", "", "| Runtime | Stage | Command | Expected |", "|---|---|---|---|"])
    for row in report["command_rows"]:
        lines.append(f"| {row['runtime']} | {row['stage']} | `{row['command']}` | {row['expected']} |")
    lines.extend(["", "## Boundary", ""])
    lines.extend(f"- {item}" for item in report["boundary"])
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Export local container build preflight for the T-ITS dynamic graph package.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/tits_container_build_preflight")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    out_dir = root / args.out_dir
    materials = out_dir / "materials"
    tables = out_dir / "tables"
    materials.mkdir(parents=True, exist_ok=True)
    tables.mkdir(parents=True, exist_ok=True)
    report = build_report(root)
    paths = {
        "preflight_md": write_text(materials / "CONTAINER_BUILD_PREFLIGHT.md", build_markdown(report)),
        "preflight_json": write_json(materials / "CONTAINER_BUILD_PREFLIGHT.json", report),
        "tool_probe_csv": write_csv(
            tables / "container_tool_probe.csv",
            report["tool_rows"],
            ["tool", "command", "path", "installed", "version_status", "version_output", "gpu_probe_status", "gpu_probe_output", "interpretation"],
        ),
        "draft_integrity_csv": write_csv(
            tables / "container_draft_integrity.csv",
            report["draft_rows"],
            ["draft", "check", "status", "detail"],
        ),
        "build_commands_csv": write_csv(
            tables / "container_build_commands.csv",
            report["command_rows"],
            ["runtime", "stage", "command", "executed_by_preflight", "expected"],
        ),
    }
    manifest = {
        "status": report["status"],
        "out_dir": args.out_dir,
        "summary": report["summary"],
        "paths": paths,
    }
    manifest_path = write_json(out_dir / "tits_container_build_preflight_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, "status": report["status"], "summary": report["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
