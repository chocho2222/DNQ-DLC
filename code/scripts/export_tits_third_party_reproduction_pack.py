#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import json
from pathlib import Path


SOURCE_DATA = "outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv"
CASE_COMMANDS = "outputs/tits_dynamic_graph/v6_confirmatory_preflight/tables/v6_confirmatory_case_commands.csv"
ENV_AUDIT = "outputs/tits_dynamic_graph/tits_environment_reproducibility_audit/materials/ENVIRONMENT_REPRODUCIBILITY_AUDIT.json"
REPRO_CAPSULE = "outputs/tits_dynamic_graph/tits_reproducibility_capsule/materials/REPRODUCIBILITY_CAPSULE_QA.json"
COMPUTE_PACK = "outputs/tits_dynamic_graph/tits_compute_reproducibility_cost_pack/materials/COMPUTE_REPRODUCIBILITY_COST_REPORT.json"
REVIEWER_SMOKE = "outputs/tits_dynamic_graph/reviewer_replication_packet/run_reviewer_smoke.sh"
SMOKE_EXECUTION_AUDIT_SCRIPT = "scripts/export_tits_reviewer_smoke_execution_audit.py"
SMOKE_EXECUTION_AUDIT_MD = "outputs/tits_dynamic_graph/tits_reviewer_smoke_execution_audit/materials/REVIEWER_SMOKE_EXECUTION_AUDIT.md"
ENVIRONMENT_YML = "environment.yml"


def read_json(path):
    path = Path(path)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path):
    path = Path(path)
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


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


def reproduction_tiers():
    return [
        {
            "tier": "T0",
            "name": "smoke_import_and_short_rollout",
            "purpose": "Verify imports, model loading, short online evaluation path, and the smoke execution audit route.",
            "command": "bash outputs/tits_dynamic_graph/reviewer_replication_packet/run_reviewer_smoke.sh && /home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_reviewer_smoke_execution_audit.py --out-dir outputs/tits_dynamic_graph/tits_reviewer_smoke_execution_audit",
            "expected_output": "/tmp/tits_dynamic_graph_reviewer_smoke/summaries/*.summary.json; outputs/tits_dynamic_graph/tits_reviewer_smoke_execution_audit/materials/REVIEWER_SMOKE_EXECUTION_AUDIT.md",
            "paper_result": "no",
        },
        {
            "tier": "T1",
            "name": "reporting_layer_rebuild",
            "purpose": "Rebuild reports, audits and figures from the frozen 240-run source data.",
            "command": "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_claim_evidence_completeness_audit.py --out-dir outputs/tits_dynamic_graph/tits_claim_evidence_completeness_audit",
            "expected_output": "outputs/tits_dynamic_graph/tits_claim_evidence_completeness_audit/tits_claim_evidence_completeness_audit_manifest.json",
            "paper_result": "yes, reporting layer only",
        },
        {
            "tier": "T2",
            "name": "full_confirmatory_matrix_rerun",
            "purpose": "Rerun 30 matched case commands and regenerate the 240 algorithm-run matrix.",
            "command": "Use outputs/tits_dynamic_graph/v6_confirmatory_preflight/tables/v6_confirmatory_case_commands.csv row by row.",
            "expected_output": "outputs/tits_dynamic_graph/v6_confirmatory_matrix/*/*/*/summaries/*.summary.json",
            "paper_result": "yes, if all commands finish under the declared environment",
        },
        {
            "tier": "T3",
            "name": "visual_evidence_rebuild",
            "purpose": "Regenerate representative top-down and first-person GIFs.",
            "command": "bash scripts/run_tits_representative_gifs.sh",
            "expected_output": "outputs/tits_dynamic_graph/publication_gifs/publication_gif_manifest.json",
            "paper_result": "qualitative visual evidence only",
        },
    ]


def checkpoints():
    return [
        {
            "checkpoint": "source_data_shape",
            "expected": "240 rows; 8 algorithms; 30 matched cases",
            "evidence": SOURCE_DATA,
            "failure_action": "Regenerate summaries from the confirmatory matrix before reporting results.",
        },
        {
            "checkpoint": "case_commands",
            "expected": "30 frozen case commands with CUDA devices recorded",
            "evidence": CASE_COMMANDS,
            "failure_action": "Run audit_v6_confirmatory_matrix.py and inspect missing case commands.",
        },
        {
            "checkpoint": "environment",
            "expected": "Python 3.10, gym 0.17.2, Box2D 2.3.8, torch CUDA available",
            "evidence": ENV_AUDIT,
            "failure_action": "Recreate conda environment from environment.yml or use the container draft.",
        },
        {
            "checkpoint": "gate_status",
            "expected": "Final readiness, cross-reference, release plan and source-data integrity pass",
            "evidence": "outputs/tits_dynamic_graph/final_readiness_dashboard/final_readiness_dashboard_manifest.json",
            "failure_action": "Run final readiness dashboard and inspect non-PASS gates.",
        },
        {
            "checkpoint": "formal_vs_smoke_boundary",
            "expected": "Smoke/GIF outputs are not used as formal statistical evidence",
            "evidence": "outputs/tits_dynamic_graph/tits_claim_evidence_completeness_audit/materials/CLAIM_EVIDENCE_COMPLETENESS_AUDIT.md",
            "failure_action": "Move smoke/GIF-only values out of Results and cite source data instead.",
        },
    ]


def troubleshooting_rows():
    return [
        {
            "symptom": "Box2D or gym import fails",
            "likely_cause": "System/conda environment mismatch or missing box2d-py/gym pin.",
            "diagnostic_command": "python - <<'PY'\nimport gym, Box2D\nprint(gym.__version__)\nPY",
            "recommended_fix": "Recreate environment from environment.yml; keep gym==0.17.2 and box2d-py=2.3.8.",
        },
        {
            "symptom": "CUDA is unavailable inside container",
            "likely_cause": "Container runtime not launched with GPU support.",
            "diagnostic_command": "python - <<'PY'\nimport torch\nprint(torch.cuda.is_available(), torch.cuda.device_count())\nPY",
            "recommended_fix": "Use docker run --gpus all or apptainer --nv; otherwise run smoke on CPU only for code-path checks.",
        },
        {
            "symptom": "nvidia-smi unavailable but torch sees GPUs",
            "likely_cause": "Driver query utility unavailable in sandbox while CUDA runtime is visible to PyTorch.",
            "diagnostic_command": "python - <<'PY'\nimport torch\nprint(torch.cuda.is_available(), [torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())])\nPY",
            "recommended_fix": "Report torch CUDA evidence and note nvidia-smi snapshot boundary.",
        },
        {
            "symptom": "Full matrix rerun is slow",
            "likely_cause": "Box2D environment stepping is CPU-heavy even when policy/world model inference uses CUDA.",
            "diagnostic_command": "Inspect outputs/tits_dynamic_graph/tits_compute_reproducibility_cost_pack/materials/COMPUTE_REPRODUCIBILITY_COST_REPORT.md",
            "recommended_fix": "Run case commands in parallel across available GPUs/CPU workers while preserving per-case outputs.",
        },
        {
            "symptom": "Source digest differs after rerun",
            "likely_cause": "Different dependency, driver, Box2D, seed handling, or regenerated matrix.",
            "diagnostic_command": "bash outputs/tits_dynamic_graph/tits_reproducibility_capsule/run_reproducibility_capsule_check.sh",
            "recommended_fix": "Regenerate source-data integrity, reproducibility capsule, artifact manifest and claim audits; do not mix old and new matrices.",
        },
    ]


def dockerfile_text():
    return """# Draft Dockerfile for T-ITS dynamic graph reproduction.
# This is a starting point for authors/reviewers; it is not a pre-built or certified image.
FROM nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \\
    bash git build-essential swig python3 python3-pip python3-venv \\
    libgl1 libglib2.0-0 xvfb ca-certificates \\
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace/multi_car_racing
COPY . /workspace/multi_car_racing

RUN python3 -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH
RUN pip install --upgrade pip setuptools wheel
RUN pip install numpy==1.26.* gym==0.17.2 box2d-py==2.3.8 pyglet==1.5.* shapely==1.8.* pillow matplotlib \\
    --extra-index-url https://download.pytorch.org/whl/cu124 torch

CMD ["bash", "-lc", "bash outputs/tits_dynamic_graph/reviewer_replication_packet/run_reviewer_smoke.sh && python scripts/export_tits_reviewer_smoke_execution_audit.py --out-dir outputs/tits_dynamic_graph/tits_reviewer_smoke_execution_audit"]
"""


def apptainer_text():
    return """Bootstrap: docker
From: nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04

%post
    apt-get update && apt-get install -y --no-install-recommends \\
        bash git build-essential swig python3 python3-pip python3-venv \\
        libgl1 libglib2.0-0 xvfb ca-certificates
    python3 -m venv /opt/venv
    . /opt/venv/bin/activate
    pip install --upgrade pip setuptools wheel
    pip install numpy==1.26.* gym==0.17.2 box2d-py==2.3.8 pyglet==1.5.* shapely==1.8.* pillow matplotlib \\
        --extra-index-url https://download.pytorch.org/whl/cu124 torch

%environment
    export PATH=/opt/venv/bin:$PATH

%runscript
    cd /workspace/multi_car_racing
    bash outputs/tits_dynamic_graph/reviewer_replication_packet/run_reviewer_smoke.sh
    python scripts/export_tits_reviewer_smoke_execution_audit.py --out-dir outputs/tits_dynamic_graph/tits_reviewer_smoke_execution_audit
"""


def build_report(root):
    source_rows = read_csv(root / SOURCE_DATA)
    case_rows = read_csv(root / CASE_COMMANDS)
    env = read_json(root / ENV_AUDIT)
    capsule = read_json(root / REPRO_CAPSULE)
    compute = read_json(root / COMPUTE_PACK)
    required = [
        SOURCE_DATA,
        CASE_COMMANDS,
        ENV_AUDIT,
        REPRO_CAPSULE,
        COMPUTE_PACK,
        REVIEWER_SMOKE,
        SMOKE_EXECUTION_AUDIT_SCRIPT,
        ENVIRONMENT_YML,
    ]
    missing = [path for path in required if not (root / path).exists()]
    algorithms = sorted({row.get("algorithm", "") for row in source_rows})
    cases = sorted({(row.get("_benchmark", ""), row.get("num_agents", ""), row.get("seed", "")) for row in source_rows})
    summary = {
        "status": "pass" if not missing and len(source_rows) == 240 and len(case_rows) == 30 else "review_required",
        "source_rows": len(source_rows),
        "case_command_count": len(case_rows),
        "algorithm_count": len(algorithms),
        "matched_case_count": len(cases),
        "torch_cuda_available": env.get("torch", {}).get("cuda_available"),
        "torch_cuda_device_count": env.get("torch", {}).get("cuda_device_count"),
        "environment_status": env.get("status"),
        "reproducibility_capsule_status": capsule.get("status"),
        "compute_pack_status": compute.get("status"),
        "missing_input_count": len(missing),
        "container_status": "draft_not_built",
    }
    return {
        "status": summary["status"],
        "summary": summary,
        "tiers": reproduction_tiers(),
        "checkpoints": checkpoints(),
        "troubleshooting": troubleshooting_rows(),
        "missing_inputs": missing,
        "boundary": [
            "Container definitions are drafts; no Docker/Apptainer image was built or certified locally.",
            f"T0 smoke checks and `{SMOKE_EXECUTION_AUDIT_MD}` verify code paths and execution fingerprints, not formal paper-scale performance.",
            "T2 full matrix reruns may differ across driver/Box2D/dependency versions and should trigger full audit regeneration.",
        ],
    }


def build_markdown(report):
    lines = [
        "# T-ITS Third-Party Reproduction Pack",
        "",
        "该包面向审稿人或第三方复现实操，整理容器草案、复现层级、校验点和常见失败诊断。它不新增实验，也不声称 Docker/Apptainer 镜像已经构建或认证。",
        "",
        "## Summary",
        "",
    ]
    for key, value in report["summary"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Reproduction Tiers", "", "| Tier | Name | Purpose | Paper result? | Command |", "|---|---|---|---|---|"])
    for row in report["tiers"]:
        lines.append(f"| {row['tier']} | {row['name']} | {row['purpose']} | {row['paper_result']} | `{row['command']}` |")
    lines.extend(["", "## Checkpoints", "", "| Checkpoint | Expected | Evidence | Failure action |", "|---|---|---|---|"])
    for row in report["checkpoints"]:
        lines.append(f"| {row['checkpoint']} | {row['expected']} | `{row['evidence']}` | {row['failure_action']} |")
    lines.extend(["", "## Troubleshooting", "", "| Symptom | Likely cause | Diagnostic command | Recommended fix |", "|---|---|---|---|"])
    for row in report["troubleshooting"]:
        command = row["diagnostic_command"].replace("\n", "<br>")
        lines.append(f"| {row['symptom']} | {row['likely_cause']} | `{command}` | {row['recommended_fix']} |")
    lines.extend(["", "## Boundary", ""])
    lines.extend(f"- {item}" for item in report["boundary"])
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Export third-party reproduction pack for T-ITS dynamic graph study.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/tits_third_party_reproduction_pack")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    out_dir = root / args.out_dir
    materials = out_dir / "materials"
    tables = out_dir / "tables"
    materials.mkdir(parents=True, exist_ok=True)
    tables.mkdir(parents=True, exist_ok=True)
    report = build_report(root)
    paths = {
        "pack_md": write_text(materials / "THIRD_PARTY_REPRODUCTION_PACK.md", build_markdown(report)),
        "pack_json": write_json(materials / "THIRD_PARTY_REPRODUCTION_PACK.json", report),
        "dockerfile_draft": write_text(materials / "Dockerfile.draft", dockerfile_text()),
        "apptainer_draft": write_text(materials / "apptainer.def.draft", apptainer_text()),
        "tiers_csv": write_csv(tables / "third_party_reproduction_tiers.csv", report["tiers"], ["tier", "name", "purpose", "command", "expected_output", "paper_result"]),
        "checkpoints_csv": write_csv(tables / "third_party_reproduction_checkpoints.csv", report["checkpoints"], ["checkpoint", "expected", "evidence", "failure_action"]),
        "troubleshooting_csv": write_csv(tables / "third_party_reproduction_troubleshooting.csv", report["troubleshooting"], ["symptom", "likely_cause", "diagnostic_command", "recommended_fix"]),
    }
    manifest = {
        "status": report["status"],
        "out_dir": args.out_dir,
        "summary": report["summary"],
        "paths": paths,
    }
    manifest_path = write_json(out_dir / "tits_third_party_reproduction_pack_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, "status": report["status"], "summary": report["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
