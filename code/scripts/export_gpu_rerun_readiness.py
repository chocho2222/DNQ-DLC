#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def row(check_id, category, status, evidence, observation, action, boundary):
    return {
        "check_id": check_id,
        "category": category,
        "status": status,
        "evidence": evidence,
        "observation": observation,
        "action": action,
        "boundary": boundary,
    }


def build_report(root):
    env = load_json(root / "materials" / "ENVIRONMENT_REPRODUCIBILITY_AUDIT.json")
    compute = load_json(root / "tables" / "compute_cost_report.json")
    route = load_json(root / "materials" / "REVIEWER_REPLICATION_ROUTE.json")
    provenance = load_json(root / "tables" / "artifact_provenance.json")
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    smoke = load_json(root / "materials" / "PUBLICATION_SMOKE_TEST.json")

    gpu_rows = env.get("gpu", {}).get("gpus", [])
    gpu_names = sorted({gpu.get("name", "") for gpu in gpu_rows if gpu.get("name")})
    total_gpu_memory = sum(gpu.get("memory_total_mb", 0) for gpu in gpu_rows)
    artifact_total = len(provenance.get("artifacts", []))
    artifact_complete = provenance.get("complete_count", 0)
    expensive_routes = [
        item for item in route.get("rows", []) if "expensive" in item.get("cost_class", "")
    ]
    optional_routes = [item for item in route.get("rows", []) if item.get("status") == "optional"]

    checks = [
        row(
            "GR01_cuda_available",
            "hardware",
            "pass" if env["summary"].get("torch_cuda_available") else "review_required",
            "materials/ENVIRONMENT_REPRODUCIBILITY_AUDIT.md",
            (
                f"torch_cuda_available={env['summary'].get('torch_cuda_available')}; "
                f"torch_cuda_version={env.get('torch_cuda', {}).get('torch_cuda_version')}"
            ),
            "Use CUDA devices for optional end-to-end rollout reruns.",
            "This documents local GPU availability, not guaranteed cross-platform timing.",
        ),
        row(
            "GR02_gpu_capacity_recorded",
            "hardware",
            "pass" if env["summary"].get("nvidia_smi_gpu_count", 0) >= 1 else "review_required",
            "materials/ENVIRONMENT_REPRODUCIBILITY_AUDIT.md",
            (
                f"gpu_count={env['summary'].get('nvidia_smi_gpu_count')}; "
                f"gpu_names={';'.join(gpu_names)}; total_memory_mb={total_gpu_memory}"
            ),
            "Use recorded GPU count and memory as the local rerun capacity statement.",
            "GPU count does not imply full deterministic equivalence across machines.",
        ),
        row(
            "GR03_registered_devices_match_compute",
            "compute",
            "pass"
            if len(compute["summary"].get("devices_from_suites", [])) >= 1
            and compute["summary"].get("environment_gpu_count", 0) >= len(compute["summary"].get("devices_from_suites", []))
            else "review_required",
            "tables/compute_cost_report.md; materials/ENVIRONMENT_REPRODUCIBILITY_AUDIT.md",
            (
                f"suite_devices={';'.join(compute['summary'].get('devices_from_suites', []))}; "
                f"environment_gpu_count={compute['summary'].get('environment_gpu_count')}"
            ),
            "Preserve registered device allocation when rerunning full suites where feasible.",
            "Saved results remain the archival evidence; reruns may differ if software or hardware changes.",
        ),
        row(
            "GR04_artifact_commands_complete",
            "provenance",
            "pass" if artifact_total and artifact_complete == artifact_total else "review_required",
            "tables/artifact_provenance.md",
            f"artifact_provenance={artifact_complete}/{artifact_total}",
            "Use artifact provenance as the command source of truth for selected expensive reruns.",
            "Do not invent commands from prose summaries when provenance has registered commands.",
        ),
        row(
            "GR05_fast_before_expensive",
            "reviewer_route",
            "pass" if route["summary"].get("quickstart_count", 0) >= 5 else "review_required",
            "materials/REVIEWER_REPLICATION_ROUTE.md",
            (
                f"quickstart_count={route['summary'].get('quickstart_count')}; "
                f"smoke_status={smoke['summary'].get('status')}; verification_status={verification['summary'].get('status')}"
            ),
            "Run saved-artifact smoke, statistics, seed, selector, and figure checks before optional GPU reruns.",
            "Fast checks verify saved artifacts only; they do not create new rollout evidence.",
        ),
        row(
            "GR06_expensive_rerun_scope_bounded",
            "reviewer_route",
            "pass" if expensive_routes and optional_routes else "review_required",
            "materials/REVIEWER_REPLICATION_ROUTE.md; tables/compute_cost_report.md",
            (
                f"expensive_route_count={len(expensive_routes)}; optional_route_count={len(optional_routes)}; "
                f"full_rollout_steps={compute['summary'].get('full_rollout_simulated_steps')}; "
                f"selector_probe_steps={compute['summary'].get('selector_probe_simulated_steps')}"
            ),
            "Treat GPU reruns as optional, selected, and provenance-driven rather than mandatory full-package regeneration.",
            "Optional reruns do not broaden claims beyond registered seeds and simulator-only evidence.",
        ),
        row(
            "GR07_wall_clock_boundary",
            "compute",
            "pass" if compute["summary"].get("wall_clock_available") is False else "review_required",
            "tables/compute_cost_report.md",
            f"wall_clock_available={compute['summary'].get('wall_clock_available')}",
            "Report simulated steps and probe counts; do not report unsupported wall-clock cost.",
            "Wall-clock timing and utilization histories are unavailable for all completed rollouts.",
        ),
    ]

    failed = [item for item in checks if item["status"] != "pass"]
    return {
        "root": str(root),
        "title": "GPU Rerun Readiness",
        "purpose": (
            "Summarize local CUDA capacity, registered command provenance, optional rerun scope, and compute "
            "reporting boundaries for reviewer-requested end-to-end reproduction."
        ),
        "summary": {
            "status": "pass" if not failed else "review_required",
            "check_count": len(checks),
            "review_required_count": len(failed),
            "gpu_count": env["summary"].get("nvidia_smi_gpu_count"),
            "gpu_names": ";".join(gpu_names),
            "total_gpu_memory_mb": total_gpu_memory,
            "artifact_provenance": f"{artifact_complete}/{artifact_total}",
            "full_rollout_simulated_steps": compute["summary"].get("full_rollout_simulated_steps"),
            "selector_probe_simulated_steps": compute["summary"].get("selector_probe_simulated_steps"),
            "publication_verification_status": verification["summary"].get("status"),
            "publication_smoke_test_reference": "materials/PUBLICATION_SMOKE_TEST.json",
        },
        "checks": checks,
        "interpretation": (
            "This is a rerun-readiness screen, not a new experiment. It supports selected GPU reruns from "
            "registered provenance while preserving simulator-only, diagnostic-oracle, and no-broad-robustness boundaries."
        ),
    }


def write_csv(report, path):
    fields = ["check_id", "category", "status", "evidence", "observation", "action", "boundary"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(report["checks"])


def write_markdown(report, path):
    lines = [
        "# GPU Rerun Readiness",
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
            "## Checks",
            "",
            "| check | category | status | observation | action | boundary | evidence |",
            "|---|---|---|---|---|---|---|",
        ]
    )
    for item in report["checks"]:
        lines.append(
            f"| {item['check_id']} | {item['category']} | {item['status']} | "
            f"{item['observation']} | {item['action']} | {item['boundary']} | `{item['evidence']}` |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export GPU rerun readiness report.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_report(root)
    out_json = materials / "GPU_RERUN_READINESS.json"
    out_md = materials / "GPU_RERUN_READINESS.md"
    out_csv = materials / "GPU_RERUN_READINESS.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    print(
        json.dumps(
            {
                "json": str(out_json),
                "markdown": str(out_md),
                "csv": str(out_csv),
                "summary": report["summary"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
