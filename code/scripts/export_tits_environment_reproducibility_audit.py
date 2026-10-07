#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import importlib
import json
import os
import platform
import py_compile
import shutil
import subprocess
import sys
from pathlib import Path


DEFAULT_PYTHON = "/home/itrc/.conda/envs/vlm_planner/bin/python"
CASE_COMMANDS_CSV = "outputs/tits_dynamic_graph/v6_confirmatory_preflight/tables/v6_confirmatory_case_commands.csv"
ENVIRONMENT_YML = "environment.yml"

REQUIRED_MODULES = [
    "numpy",
    "torch",
    "gym",
    "Box2D",
    "pyglet",
    "shapely",
    "PIL",
    "matplotlib",
]
OPTIONAL_MODULES = [
    "imageio",
]
KEY_SCRIPTS = [
    "scripts/run_tits_dynamic_graph_evaluation.py",
    "scripts/run_tits_dynamic_graph_online_suite.py",
    "scripts/run_tits_dynamic_graph_suite.py",
    "scripts/summarize_tits_dynamic_graph_online.py",
    "scripts/audit_tits_dynamic_graph_readiness.py",
    "scripts/audit_v6_confirmatory_matrix.py",
    "scripts/export_tits_confirmatory_evidence_pack.py",
    "scripts/export_tits_reviewer_replication_packet.py",
    "scripts/export_tits_manuscript_package.py",
    "scripts/export_tits_manuscript_supplement_navigator.py",
    "scripts/export_tits_manuscript_english_figures.py",
    "scripts/export_tits_ablation_contribution_pack.py",
    "scripts/export_tits_benchmark_protocol_pack.py",
    "scripts/export_tits_statistical_analysis_pack.py",
    "scripts/export_tits_threats_validity_pack.py",
    "scripts/export_tits_cross_reference_audit.py",
    "scripts/export_tits_source_data_integrity_audit.py",
    "scripts/export_tits_dynamic_graph_artifact_manifest.py",
    "scripts/export_tits_public_release_plan.py",
    "scripts/export_tits_final_readiness_dashboard.py",
    "scripts/run_tits_full_pipeline.sh",
    "scripts/run_tits_representative_gifs.sh",
]


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


def module_version(name):
    try:
        module = importlib.import_module(name)
        return {
            "module": name,
            "present": True,
            "version": getattr(module, "__version__", "unknown"),
            "error": "",
        }
    except Exception as exc:
        return {
            "module": name,
            "present": False,
            "version": "",
            "error": repr(exc),
        }


def torch_info():
    info = {
        "present": False,
        "version": "",
        "cuda_available": False,
        "cuda_device_count": 0,
        "cuda_version": "",
        "devices": [],
        "error": "",
    }
    try:
        import torch

        info["present"] = True
        info["version"] = getattr(torch, "__version__", "unknown")
        info["cuda_available"] = bool(torch.cuda.is_available())
        info["cuda_device_count"] = int(torch.cuda.device_count())
        info["cuda_version"] = str(torch.version.cuda)
        info["devices"] = [torch.cuda.get_device_name(idx) for idx in range(torch.cuda.device_count())]
    except Exception as exc:
        info["error"] = repr(exc)
    return info


def nvidia_smi_snapshot():
    if not shutil.which("nvidia-smi"):
        return {"available": False, "gpus": [], "raw": "", "error": "nvidia-smi not found"}
    try:
        output = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=index,name,memory.total,driver_version,cuda_version",
                "--format=csv,noheader,nounits",
            ],
            text=True,
            stderr=subprocess.STDOUT,
            timeout=10,
        )
        gpus = []
        for line in output.splitlines():
            parts = [part.strip() for part in line.split(",")]
            if len(parts) >= 5:
                gpus.append(
                    {
                        "index": parts[0],
                        "name": parts[1],
                        "memory_total_mb": parts[2],
                        "driver_version": parts[3],
                        "cuda_version": parts[4],
                    }
                )
        return {"available": True, "gpus": gpus, "raw": output, "error": ""}
    except Exception as exc:
        return {"available": False, "gpus": [], "raw": "", "error": repr(exc)}


def check_scripts(root):
    rows = []
    for rel in KEY_SCRIPTS:
        path = root / rel
        exists = path.exists()
        is_python = path.suffix == ".py"
        py_compile_ok = ""
        error = ""
        if exists and is_python:
            try:
                py_compile.compile(str(path), doraise=True)
                py_compile_ok = True
            except Exception as exc:
                py_compile_ok = False
                error = repr(exc)
        rows.append(
            {
                "path": rel,
                "exists": exists,
                "type": "python" if is_python else "shell",
                "py_compile_ok": py_compile_ok,
                "error": error,
                "status": "pass" if exists and (not is_python or py_compile_ok is True) else "error",
            }
        )
    return rows


def read_case_commands(root):
    path = root / CASE_COMMANDS_CSV
    if not path.exists():
        return [], []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader), list(reader.fieldnames or [])


def check_case_commands(root):
    rows, fields = read_case_commands(root)
    devices = sorted({row.get("device", "") for row in rows if row.get("device", "")})
    commands_with_python = sum(1 for row in rows if DEFAULT_PYTHON in row.get("command", ""))
    commands_with_no_gif = sum(1 for row in rows if "--no-gif" in row.get("command", ""))
    algorithms_ok = sum(1 for row in rows if "--algorithms" in row.get("command", ""))
    return {
        "path": CASE_COMMANDS_CSV,
        "exists": bool(rows),
        "fieldnames": fields,
        "case_command_count": len(rows),
        "devices": devices,
        "commands_with_expected_python": commands_with_python,
        "commands_with_no_gif": commands_with_no_gif,
        "commands_with_algorithm_list": algorithms_ok,
        "status": "pass"
        if len(rows) == 30 and commands_with_python == len(rows) and commands_with_no_gif == len(rows) and algorithms_ok == len(rows)
        else "review_required",
    }


def environment_file_audit(root):
    path = root / ENVIRONMENT_YML
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    rows = []
    checks = [
        ("environment_yml_exists", path.exists(), "environment.yml must be present for reproducibility."),
        ("python_310_declared", "python=3.10" in text, "Python 3.10 should be declared."),
        ("torch_declared", "torch" in text, "PyTorch should be declared."),
        ("gym_pinned", "gym==0.17.2" in text, "Gym 0.17.2 should be pinned."),
        ("box2d_declared", "box2d-py=2.3.8" in text, "Box2D should be declared."),
        ("cuda_wheel_index_declared", "download.pytorch.org/whl" in text, "PyTorch CUDA wheel index should be documented."),
    ]
    for name, ok, note in checks:
        rows.append({"check": name, "status": "pass" if ok else "error", "note": note})
    if "torch\n" in text or "torch\r\n" in text:
        rows.append(
            {
                "check": "torch_version_pin",
                "status": "warning",
                "note": "environment.yml declares torch without an exact version; artifact manifest and environment audit record the installed version.",
            }
        )
    return rows


def build_report(root, python_path):
    required_rows = [module_version(name) for name in REQUIRED_MODULES]
    optional_rows = [module_version(name) for name in OPTIONAL_MODULES]
    torch = torch_info()
    nvidia = nvidia_smi_snapshot()
    script_rows = check_scripts(root)
    case_commands = check_case_commands(root)
    env_rows = environment_file_audit(root)

    hard_errors = []
    warnings = []
    for row in required_rows:
        if not row["present"]:
            hard_errors.append(f"required_module_missing:{row['module']}")
    for row in optional_rows:
        if not row["present"]:
            warnings.append(f"optional_module_missing:{row['module']}")
    if not torch["cuda_available"] or torch["cuda_device_count"] < 1:
        hard_errors.append("torch_cuda_unavailable")
    if any(row["status"] == "error" for row in script_rows):
        hard_errors.append("key_script_missing_or_uncompilable")
    if case_commands["status"] != "pass":
        hard_errors.append("case_command_preflight_failed")
    for row in env_rows:
        if row["status"] == "error":
            hard_errors.append(f"environment_file:{row['check']}")
        elif row["status"] == "warning":
            warnings.append(f"environment_file:{row['check']}")
    if not nvidia["available"]:
        warnings.append("nvidia_smi_snapshot_unavailable")

    status = "pass" if not hard_errors else "review_required"
    return {
        "status": status,
        "root": str(root),
        "python": {
            "requested_python": python_path,
            "current_executable": sys.executable,
            "version": sys.version,
            "platform": platform.platform(),
            "cwd": os.getcwd(),
        },
        "required_modules": required_rows,
        "optional_modules": optional_rows,
        "torch": torch,
        "nvidia_smi": nvidia,
        "script_rows": script_rows,
        "case_commands": case_commands,
        "environment_file_checks": env_rows,
        "summary": {
            "status": status,
            "required_module_count": len(required_rows),
            "required_module_missing_count": sum(1 for row in required_rows if not row["present"]),
            "optional_module_missing_count": sum(1 for row in optional_rows if not row["present"]),
            "torch_cuda_available": torch["cuda_available"],
            "torch_cuda_device_count": torch["cuda_device_count"],
            "nvidia_smi_gpu_count": len(nvidia["gpus"]),
            "key_script_count": len(script_rows),
            "key_script_error_count": sum(1 for row in script_rows if row["status"] == "error"),
            "case_command_count": case_commands["case_command_count"],
            "case_command_status": case_commands["status"],
            "hard_error_count": len(hard_errors),
            "warning_count": len(warnings),
            "hard_errors": hard_errors,
            "warnings": warnings,
        },
        "note": "This audit snapshots the local environment and command reproducibility prerequisites. It does not rerun the paper-scale training or online matrix.",
    }


def build_markdown(report):
    lines = [
        "# T-ITS Environment Reproducibility Audit",
        "",
        "该审计记录当前本地复现实验环境、依赖、CUDA/GPU、关键脚本可编译性、冻结 case command 覆盖和 `environment.yml` 声明情况。它用于支撑论文的 Reproducibility / Data and Code Availability，不新增实验结果。",
        "",
        "## Summary",
        "",
    ]
    for key, value in report["summary"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Python",
            "",
            f"- Requested Python: `{report['python']['requested_python']}`",
            f"- Current executable: `{report['python']['current_executable']}`",
            f"- Version: `{report['python']['version'].splitlines()[0]}`",
            f"- Platform: `{report['python']['platform']}`",
            "",
            "## Required Modules",
            "",
            "| module | present | version | error |",
            "|---|---|---|---|",
        ]
    )
    for row in report["required_modules"]:
        lines.append(f"| {row['module']} | {row['present']} | {row['version']} | {row['error']} |")
    lines.extend(["", "## Optional Modules", "", "| module | present | version | note |", "|---|---|---|---|"])
    for row in report["optional_modules"]:
        note = "Optional; not required by the current PIL-based GIF workflow." if not row["present"] else ""
        lines.append(f"| {row['module']} | {row['present']} | {row['version']} | {note or row['error']} |")
    lines.extend(
        [
            "",
            "## CUDA/GPU",
            "",
            f"- Torch version: `{report['torch']['version']}`",
            f"- Torch CUDA available: {report['torch']['cuda_available']}",
            f"- Torch CUDA version: `{report['torch']['cuda_version']}`",
            f"- Torch CUDA device count: {report['torch']['cuda_device_count']}",
            f"- Torch devices: {', '.join(report['torch']['devices'])}",
            f"- nvidia-smi GPU count: {len(report['nvidia_smi']['gpus'])}",
            "",
            "## Frozen Case Commands",
            "",
            f"- Command file: `{report['case_commands']['path']}`",
            f"- Case commands: {report['case_commands']['case_command_count']}",
            f"- Devices: {', '.join(report['case_commands']['devices'])}",
            f"- Status: `{report['case_commands']['status']}`",
            "",
            "## Boundary",
            "",
            "Box2D/Gym environment stepping is CPU-heavy; the learned world model, proposal actor and online policy inference use CUDA when `--device cuda:*` is selected. Therefore low GPU utilization during rollout would not by itself imply CPU-only evaluation.",
            "",
            "## Regeneration Command",
            "",
            "```bash",
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_environment_reproducibility_audit.py --out-dir outputs/tits_dynamic_graph/tits_environment_reproducibility_audit",
            "```",
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Export T-ITS environment and command reproducibility audit.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--python", default=DEFAULT_PYTHON)
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/tits_environment_reproducibility_audit")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    out_dir = root / args.out_dir
    materials = out_dir / "materials"
    tables = out_dir / "tables"
    materials.mkdir(parents=True, exist_ok=True)
    tables.mkdir(parents=True, exist_ok=True)

    report = build_report(root, args.python)
    paths = {
        "audit_md": write_text(materials / "ENVIRONMENT_REPRODUCIBILITY_AUDIT.md", build_markdown(report)),
        "audit_json": write_json(materials / "ENVIRONMENT_REPRODUCIBILITY_AUDIT.json", report),
        "modules_csv": write_csv(
            tables / "environment_module_versions.csv",
            report["required_modules"] + report["optional_modules"],
            ["module", "present", "version", "error"],
        ),
        "scripts_csv": write_csv(
            tables / "environment_key_scripts.csv",
            report["script_rows"],
            ["path", "exists", "type", "py_compile_ok", "error", "status"],
        ),
        "environment_file_checks_csv": write_csv(
            tables / "environment_file_checks.csv",
            report["environment_file_checks"],
            ["check", "status", "note"],
        ),
    }
    manifest = {
        "status": report["status"],
        "out_dir": args.out_dir,
        "summary": report["summary"],
        "paths": paths,
    }
    manifest_path = write_json(out_dir / "tits_environment_reproducibility_audit_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, "status": report["status"], "summary": report["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
