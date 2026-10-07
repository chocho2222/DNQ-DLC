#!/usr/bin/env python
import argparse
import csv
import hashlib
import importlib.metadata
import json
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


PACKAGES = [
    ("numpy", "numpy"),
    ("torch", "torch"),
    ("gym", "gym"),
    ("Box2D", "box2d-py"),
    ("matplotlib", "matplotlib"),
    ("PIL", "Pillow"),
    ("pyglet", "pyglet"),
]


def sha256_file(path, chunk_size=1024 * 1024):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def run_capture(command, timeout=10):
    try:
        result = subprocess.run(command, text=True, capture_output=True, timeout=timeout, check=False)
    except FileNotFoundError:
        return {"available": False, "returncode": None, "stdout": "", "stderr": "command not found"}
    except subprocess.TimeoutExpired:
        return {"available": True, "returncode": None, "stdout": "", "stderr": "timeout"}
    return {
        "available": True,
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def package_versions():
    rows = []
    for import_name, distribution_name in PACKAGES:
        row = {"import_name": import_name, "distribution_name": distribution_name}
        try:
            row["version"] = importlib.metadata.version(distribution_name)
            row["status"] = "available"
        except importlib.metadata.PackageNotFoundError:
            row["version"] = None
            row["status"] = "missing"
        rows.append(row)
    return rows


def torch_cuda_probe():
    try:
        import torch
    except Exception as exc:
        return {
            "torch_importable": False,
            "torch_import_error": repr(exc),
            "cuda_available": False,
            "torch_cuda_version": None,
            "device_count": 0,
            "devices": [],
        }
    devices = []
    if torch.cuda.is_available():
        for idx in range(torch.cuda.device_count()):
            props = torch.cuda.get_device_properties(idx)
            devices.append(
                {
                    "index": idx,
                    "name": props.name,
                    "total_memory_mb": int(props.total_memory / (1024 * 1024)),
                    "major": props.major,
                    "minor": props.minor,
                }
            )
    return {
        "torch_importable": True,
        "torch_import_error": None,
        "cuda_available": bool(torch.cuda.is_available()),
        "torch_cuda_version": torch.version.cuda,
        "device_count": len(devices),
        "devices": devices,
    }


def nvidia_smi_probe():
    command = [
        "nvidia-smi",
        "--query-gpu=index,name,memory.total,memory.used,utilization.gpu,driver_version",
        "--format=csv,noheader,nounits",
    ]
    result = run_capture(command, timeout=10)
    gpus = []
    if result["returncode"] == 0 and result["stdout"]:
        for line in result["stdout"].splitlines():
            parts = [item.strip() for item in line.split(",")]
            if len(parts) != 6:
                continue
            index, name, memory_total, memory_used, utilization_gpu, driver_version = parts
            gpus.append(
                {
                    "index": int(index),
                    "name": name,
                    "memory_total_mb": int(memory_total),
                    "memory_used_mb": int(memory_used),
                    "utilization_gpu_percent": int(utilization_gpu),
                    "driver_version": driver_version,
                }
            )
    return {
        "command": " ".join(command),
        "available": result["available"],
        "returncode": result["returncode"],
        "count": len(gpus),
        "gpus": gpus,
        "stderr": result["stderr"],
    }


def build_report(root):
    repo_root = Path.cwd()
    env_path = repo_root / "environment.yml"
    reproduction_guide = root / "materials" / "REPRODUCTION_GUIDE.md"
    release_manifest = root / "materials" / "RELEASE_ARCHIVE_MANIFEST.json"
    package_manifest = root / "manifest.json"

    environment_yml = {
        "path": "environment.yml",
        "exists": env_path.exists(),
        "sha256": sha256_file(env_path) if env_path.exists() else None,
        "size_bytes": env_path.stat().st_size if env_path.exists() else None,
    }
    package_manifest_record = {
        "path": "manifest.json",
        "exists": package_manifest.exists(),
        "sha256": sha256_file(package_manifest) if package_manifest.exists() else None,
    }
    release_manifest_record = {
        "path": "materials/RELEASE_ARCHIVE_MANIFEST.json",
        "exists": release_manifest.exists(),
        "note": "Existence is recorded here; final package checksums are owned by RELEASE_ARCHIVE_MANIFEST.",
    }

    report = {
        "root": str(root),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "python": {
            "executable": sys.executable,
            "version": sys.version.replace("\n", " "),
            "prefix": sys.prefix,
            "base_prefix": sys.base_prefix,
            "conda_prefix": os.environ.get("CONDA_PREFIX"),
            "conda_default_env": os.environ.get("CONDA_DEFAULT_ENV"),
        },
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python_implementation": platform.python_implementation(),
        },
        "environment_yml": environment_yml,
        "packages": package_versions(),
        "torch_cuda": torch_cuda_probe(),
        "gpu": nvidia_smi_probe(),
        "reproduction_entrypoints": [
            "materials/REPRODUCTION_GUIDE.md",
            "materials/ENVIRONMENT_REPRODUCIBILITY_AUDIT.md",
            "materials/RELEASE_ARCHIVE_MANIFEST.md",
            "tables/artifact_provenance.md",
            "tables/reproducibility_audit.md",
            "manifest.json",
        ],
        "fast_audit_commands": [
            "PYTHONPATH=. conda run -n vlm_planner python scripts/export_environment_reproducibility_audit.py --root outputs/paper_multicar_overtake_20260618",
            "PYTHONPATH=. conda run -n vlm_planner python scripts/export_artifact_provenance.py --root outputs/paper_multicar_overtake_20260618",
            "PYTHONPATH=. conda run -n vlm_planner python scripts/export_reproducibility_audit.py --root outputs/paper_multicar_overtake_20260618",
            "PYTHONPATH=. conda run -n vlm_planner python scripts/export_package_manifest.py --root outputs/paper_multicar_overtake_20260618",
            "PYTHONPATH=. conda run -n vlm_planner python scripts/export_manuscript_claim_qa.py --root outputs/paper_multicar_overtake_20260618",
            "PYTHONPATH=. conda run -n vlm_planner python scripts/export_release_archive_manifest.py --root outputs/paper_multicar_overtake_20260618",
        ],
        "gpu_full_rerun_note": (
            "Full rollout reproduction should use the recorded CUDA device list and parallel workers "
            "shown in artifact_provenance.md. The saved reports can be regenerated without rerunning rollouts."
        ),
        "integrity_inputs": {
            "environment_yml": environment_yml,
            "package_manifest": package_manifest_record,
            "release_manifest": release_manifest_record,
            "reproduction_guide_exists": reproduction_guide.exists(),
            "nvidia_smi_path": shutil.which("nvidia-smi"),
        },
        "limitations": [
            "This audit records the current local execution environment, not a container image.",
            "Wall-clock GPU utilization histories are not available for all completed rollouts.",
            "A public DOI or repository accession has not yet been assigned.",
            "Expensive rollout reruns require CUDA devices and substantially more time than metadata regeneration.",
        ],
    }
    report["summary"] = {
        "environment_yml_present": environment_yml["exists"],
        "torch_cuda_available": report["torch_cuda"]["cuda_available"],
        "nvidia_smi_gpu_count": report["gpu"]["count"],
        "package_versions_missing": [row["distribution_name"] for row in report["packages"] if row["status"] != "available"],
        "ready_for_fast_audit": environment_yml["exists"] and reproduction_guide.exists(),
    }
    return report


def write_csv(report, path):
    rows = []
    rows.append({"section": "python", "key": "executable", "value": report["python"]["executable"]})
    rows.append({"section": "python", "key": "version", "value": report["python"]["version"]})
    rows.append({"section": "python", "key": "conda_prefix", "value": report["python"]["conda_prefix"]})
    rows.append({"section": "environment_yml", "key": "exists", "value": report["environment_yml"]["exists"]})
    rows.append({"section": "environment_yml", "key": "sha256", "value": report["environment_yml"]["sha256"]})
    rows.append({"section": "torch_cuda", "key": "cuda_available", "value": report["torch_cuda"]["cuda_available"]})
    rows.append({"section": "torch_cuda", "key": "torch_cuda_version", "value": report["torch_cuda"]["torch_cuda_version"]})
    rows.append({"section": "gpu", "key": "nvidia_smi_gpu_count", "value": report["gpu"]["count"]})
    for row in report["packages"]:
        rows.append({"section": "package", "key": row["distribution_name"], "value": row["version"]})
    for gpu in report["gpu"]["gpus"]:
        rows.append({"section": "gpu", "key": f"gpu_{gpu['index']}_name", "value": gpu["name"]})
        rows.append({"section": "gpu", "key": f"gpu_{gpu['index']}_memory_total_mb", "value": gpu["memory_total_mb"]})
        rows.append({"section": "gpu", "key": f"gpu_{gpu['index']}_driver", "value": gpu["driver_version"]})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["section", "key", "value"])
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(report, path):
    lines = [
        "# Environment Reproducibility Audit",
        "",
        f"- Root: `{report['root']}`",
        f"- Timestamp (UTC): {report['timestamp_utc']}",
        f"- Python executable: `{report['python']['executable']}`",
        f"- Python version: `{report['python']['version']}`",
        f"- Conda prefix: `{report['python']['conda_prefix']}`",
        f"- Platform: {report['platform']['system']} {report['platform']['release']} ({report['platform']['machine']})",
        "",
        "## Environment Lockfile",
        "",
        f"- Path: `{report['environment_yml']['path']}`",
        f"- Exists: {report['environment_yml']['exists']}",
        f"- SHA256: `{report['environment_yml']['sha256']}`",
        "",
        "## Package Versions",
        "",
        "| import | distribution | status | version |",
        "|---|---|---|---|",
    ]
    for row in report["packages"]:
        lines.append(
            f"| `{row['import_name']}` | `{row['distribution_name']}` | {row['status']} | `{row['version']}` |"
        )
    lines.extend(
        [
            "",
            "## CUDA And GPU",
            "",
            f"- Torch importable: {report['torch_cuda']['torch_importable']}",
            f"- Torch CUDA available: {report['torch_cuda']['cuda_available']}",
            f"- Torch CUDA version: `{report['torch_cuda']['torch_cuda_version']}`",
            f"- `nvidia-smi` GPU count: {report['gpu']['count']}",
            "",
            "| index | name | memory total MB | memory used MB | utilization % | driver |",
            "|---:|---|---:|---:|---:|---|",
        ]
    )
    for gpu in report["gpu"]["gpus"]:
        lines.append(
            f"| {gpu['index']} | {gpu['name']} | {gpu['memory_total_mb']} | "
            f"{gpu['memory_used_mb']} | {gpu['utilization_gpu_percent']} | {gpu['driver_version']} |"
        )
    if not report["gpu"]["gpus"]:
        lines.append("| NA | no GPU reported by nvidia-smi | NA | NA | NA | NA |")
    lines.extend(["", "## Reproduction Entry Points", ""])
    lines.extend(f"- `{item}`" for item in report["reproduction_entrypoints"])
    lines.extend(["", "## Fast Audit Commands", ""])
    for command in report["fast_audit_commands"]:
        lines.extend(["```bash", command, "```"])
    lines.extend(
        [
            "",
            "## Full-rerun Compute Note",
            "",
            report["gpu_full_rerun_note"],
            "",
            "## Limitations",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in report["limitations"])
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export environment and reproducibility audit.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_report(root)
    out_json = materials / "ENVIRONMENT_REPRODUCIBILITY_AUDIT.json"
    out_md = materials / "ENVIRONMENT_REPRODUCIBILITY_AUDIT.md"
    out_csv = materials / "ENVIRONMENT_REPRODUCIBILITY_AUDIT.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv)}, indent=2))


if __name__ == "__main__":
    main()
