#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import json
from pathlib import Path


SOURCE_DATA = "outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv"
CASE_COMMANDS = "outputs/tits_dynamic_graph/v6_confirmatory_preflight/tables/v6_confirmatory_case_commands.csv"
COMPUTE_COST = "outputs/tits_dynamic_graph/tits_compute_reproducibility_cost_pack/materials/COMPUTE_REPRODUCIBILITY_COST_REPORT.json"
RUNTIME_SCALABILITY = "outputs/tits_dynamic_graph/tits_runtime_scalability_pack/materials/RUNTIME_SCALABILITY_AND_COMPLEXITY_REPORT.json"
ENVIRONMENT_AUDIT = "outputs/tits_dynamic_graph/tits_environment_reproducibility_audit/materials/ENVIRONMENT_REPRODUCIBILITY_AUDIT.json"
REPRO_TIME_BUDGET = "outputs/tits_dynamic_graph/tits_reviewer_reproduction_time_budget_audit/tables/reviewer_reproduction_time_budget_tiers.csv"


def read_csv(path):
    path = Path(path)
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


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


def to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def mean(values):
    values = [value for value in values if value is not None]
    return sum(values) / len(values) if values else None


def build_evidence_rows(source_rows, case_commands, compute, runtime, environment, repro_tiers):
    compute_summary = compute.get("summary", {})
    runtime_summary = runtime.get("summary", {})
    env_summary = environment.get("summary", {})
    latencies = [to_float(row.get("compute_latency_ms")) for row in source_rows]
    p95_latencies = [to_float(row.get("compute_latency_p95_ms")) for row in source_rows]
    finish_steps = [to_float(row.get("finish_step")) for row in source_rows]
    rows = [
        {
            "evidence_id": "timing_E01_formal_matrix_scale",
            "claim_type": "available",
            "field": "algorithm_runs",
            "observed_value": len(source_rows),
            "source": SOURCE_DATA,
            "interpretation": "正式在线矩阵包含 240 个 algorithm-runs，可用于报告实验规模。",
        },
        {
            "evidence_id": "timing_E02_case_commands",
            "claim_type": "available",
            "field": "frozen_case_commands",
            "observed_value": len(case_commands),
            "source": CASE_COMMANDS,
            "interpretation": "30 条冻结 case command 可用于 T2 完整重跑。",
        },
        {
            "evidence_id": "timing_E03_simulated_steps",
            "claim_type": "available",
            "field": "total_simulated_finish_steps",
            "observed_value": compute_summary.get("total_simulated_steps_across_algorithm_runs") or int(sum(finish_steps)),
            "source": COMPUTE_COST,
            "interpretation": "可报告仿真 finish-step 规模，但它不是 wall-clock 时间。",
        },
        {
            "evidence_id": "timing_E04_mean_decision_latency",
            "claim_type": "available",
            "field": "mean_compute_latency_ms",
            "observed_value": round(mean(latencies), 6) if mean(latencies) is not None else "",
            "source": SOURCE_DATA,
            "interpretation": "逐 run summary 中有决策延迟字段，可支持算法级在线决策开销分析。",
        },
        {
            "evidence_id": "timing_E05_p95_decision_latency",
            "claim_type": "available",
            "field": "mean_compute_latency_p95_ms",
            "observed_value": round(mean(p95_latencies), 6) if mean(p95_latencies) is not None else "",
            "source": SOURCE_DATA,
            "interpretation": "逐 run summary 中有 p95 决策延迟字段，可支持延迟尾部风险分析。",
        },
        {
            "evidence_id": "timing_E06_runtime_scalability",
            "claim_type": "available",
            "field": "safe_latency_slope_ms_per_vehicle",
            "observed_value": runtime_summary.get("safe_latency_slope_ms_per_vehicle"),
            "source": RUNTIME_SCALABILITY,
            "interpretation": "已有车辆数 4/5/6/8 下的延迟扩展性证据。",
        },
        {
            "evidence_id": "timing_E07_cuda_snapshot",
            "claim_type": "available",
            "field": "torch_cuda_device_count",
            "observed_value": env_summary.get("torch_cuda_device_count"),
            "source": ENVIRONMENT_AUDIT,
            "interpretation": "环境审计记录 PyTorch 可见 CUDA 设备数。",
        },
        {
            "evidence_id": "timing_E08_reproduction_tiers",
            "claim_type": "available",
            "field": "reproduction_tier_count",
            "observed_value": len(repro_tiers),
            "source": REPRO_TIME_BUDGET,
            "interpretation": "审稿复现成本已拆分为 T0-T3 层级。",
        },
        {
            "evidence_id": "timing_B01_wall_clock",
            "claim_type": "unavailable_boundary",
            "field": "complete_historical_wall_clock_trace",
            "observed_value": compute_summary.get("wall_clock_time_recorded"),
            "source": COMPUTE_COST,
            "interpretation": "历史完整 wall-clock trace 未归档，论文不得声称完整 elapsed-time 审计。",
        },
        {
            "evidence_id": "timing_B02_gpu_utilization",
            "claim_type": "unavailable_boundary",
            "field": "complete_gpu_utilization_trace",
            "observed_value": "not_archived",
            "source": ENVIRONMENT_AUDIT,
            "interpretation": "GPU utilization 时间序列未归档，不能声称完整 GPU 利用率审计。",
        },
        {
            "evidence_id": "timing_B03_cpu_utilization",
            "claim_type": "unavailable_boundary",
            "field": "complete_cpu_utilization_trace",
            "observed_value": "not_archived",
            "source": COMPUTE_COST,
            "interpretation": "CPU utilization 时间序列未归档，不能声称完整 CPU 利用率审计。",
        },
    ]
    return rows


def build_recommendation_rows():
    return [
        {
            "item": "future_wall_clock_logging",
            "priority": "high",
            "recommended_field": "run_start_iso; run_end_iso; elapsed_seconds; hostname; git_sha; command_sha256",
            "where_to_log": "per-run summary JSON and matrix run ledger",
            "reason": "支持未来版本报告完整 elapsed time，并可按 case/algorithm 聚合。",
        },
        {
            "item": "future_gpu_utilization_logging",
            "priority": "medium",
            "recommended_field": "gpu_index; memory_total_mb; memory_used_mb; utilization_gpu_pct; utilization_memory_pct; timestamp_iso",
            "where_to_log": "separate nvidia-smi sampling CSV per case command",
            "reason": "支持审稿人复核 GPU 利用率，但不改变当前性能结论。",
        },
        {
            "item": "future_cpu_memory_logging",
            "priority": "medium",
            "recommended_field": "cpu_percent; rss_mb; system_memory_used_mb; timestamp_iso",
            "where_to_log": "optional psutil sampling CSV per worker",
            "reason": "补足 Box2D 环境 stepping 的 CPU 侧开销记录。",
        },
        {
            "item": "future_parallel_schedule_logging",
            "priority": "medium",
            "recommended_field": "worker_id; device; case_id; algorithm_list; launch_order; completion_status",
            "where_to_log": "matrix scheduler ledger",
            "reason": "便于解释多 GPU 并行下的总 wall-clock 与逐 run 成本差异。",
        },
    ]


def build_checks(evidence_rows):
    available = [row for row in evidence_rows if row["claim_type"] == "available"]
    unavailable = [row for row in evidence_rows if row["claim_type"] == "unavailable_boundary"]
    blocking = []
    for row in available:
        if row["observed_value"] in ("", None, 0):
            blocking.append(row["evidence_id"])
    wall_clock_rows = [row for row in unavailable if row["field"] == "complete_historical_wall_clock_trace"]
    wall_clock_boundary_explicit = bool(wall_clock_rows and wall_clock_rows[0]["observed_value"] is False)
    return {
        "available_evidence_count": len(available),
        "unavailable_boundary_count": len(unavailable),
        "blocking_missing_available_evidence": blocking,
        "wall_clock_boundary_explicit": wall_clock_boundary_explicit,
        "status": "pass" if not blocking and wall_clock_boundary_explicit else "review_required",
    }


def build_markdown(report):
    summary = report["summary"]
    lines = [
        "# Compute Timing Boundary Audit",
        "",
        "该审计专门回答审稿人可能提出的算力与运行时间问题：当前证据链可以可靠报告正式矩阵规模、仿真步数、逐 run 决策延迟、CUDA/GPU 环境和 T0-T3 复现层级；但不能声称已经归档完整历史 wall-clock、GPU utilization 或 CPU utilization 时间序列。",
        "",
        "## Summary",
        "",
        f"- Status: {summary['status']}",
        f"- Available timing/resource evidence rows: {summary['available_evidence_count']}",
        f"- Explicit unavailable-boundary rows: {summary['unavailable_boundary_count']}",
        f"- Formal source rows: {summary['source_rows']}",
        f"- Frozen case commands: {summary['case_command_count']}",
        f"- Total simulated finish steps: {summary['total_simulated_steps']}",
        f"- Mean decision latency ms: {summary['mean_compute_latency_ms']}",
        f"- Wall-clock boundary explicit: {summary['wall_clock_boundary_explicit']}",
        "",
        "## What Can Be Claimed",
        "",
        "- 可以报告 240 个正式 algorithm-runs、30 个 matched cases 和 528000 个仿真 finish steps。",
        "- 可以报告逐 run 决策延迟、p95 决策延迟以及车辆数扩展性下的延迟趋势。",
        "- 可以报告当前环境审计中的 PyTorch CUDA 可用性和 GPU 设备数量。",
        "- 可以报告 T0-T3 分层复现路线及其成本边界。",
        "",
        "## What Must Not Be Claimed",
        "",
        "- 不能声称每个历史 run 的真实 wall-clock 起止时间都已归档。",
        "- 不能声称完整 GPU utilization 或 CPU utilization 时间序列已归档。",
        "- 不能把 derived planner workload proxy 当作真实 elapsed wall-clock time。",
        "- 不能把 smoke test 或 GIF 重建成本写成正式 240-run 复现实验成本。",
        "",
        "## Evidence Rows",
        "",
        "| ID | Type | Field | Observed | Source | Interpretation |",
        "|---|---|---|---|---|---|",
    ]
    for row in report["evidence_rows"]:
        lines.append(
            f"| {row['evidence_id']} | {row['claim_type']} | {row['field']} | {row['observed_value']} | `{row['source']}` | {row['interpretation']} |"
        )
    lines.extend(["", "## Future Logging Template", "", "| Item | Priority | Recommended fields | Where | Reason |", "|---|---|---|---|---|"])
    for row in report["recommendation_rows"]:
        lines.append(
            f"| {row['item']} | {row['priority']} | {row['recommended_field']} | {row['where_to_log']} | {row['reason']} |"
        )
    return "\n".join(lines)


def build_report(root):
    source_rows = read_csv(root / SOURCE_DATA)
    case_commands = read_csv(root / CASE_COMMANDS)
    compute = read_json(root / COMPUTE_COST)
    runtime = read_json(root / RUNTIME_SCALABILITY)
    environment = read_json(root / ENVIRONMENT_AUDIT)
    repro_tiers = read_csv(root / REPRO_TIME_BUDGET)
    evidence_rows = build_evidence_rows(source_rows, case_commands, compute, runtime, environment, repro_tiers)
    checks = build_checks(evidence_rows)
    latencies = [to_float(row.get("compute_latency_ms")) for row in source_rows]
    summary = {
        **checks,
        "source_rows": len(source_rows),
        "case_command_count": len(case_commands),
        "total_simulated_steps": compute.get("summary", {}).get("total_simulated_steps_across_algorithm_runs"),
        "mean_compute_latency_ms": round(mean(latencies), 6) if mean(latencies) is not None else "",
        "gpu_count": environment.get("summary", {}).get("torch_cuda_device_count"),
        "cuda_available": environment.get("summary", {}).get("torch_cuda_available"),
        "boundary": "Complete historical wall-clock, GPU-utilization and CPU-utilization traces are unavailable; use simulated steps, decision latency and tiered reproduction cost instead.",
    }
    return {
        "status": summary["status"],
        "summary": summary,
        "evidence_rows": evidence_rows,
        "recommendation_rows": build_recommendation_rows(),
    }


def main():
    parser = argparse.ArgumentParser(description="Export compute timing boundary audit for T-ITS evidence.")
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/tits_compute_timing_boundary_audit")
    args = parser.parse_args()
    root = Path.cwd()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "materials").mkdir(exist_ok=True)
    (out_dir / "tables").mkdir(exist_ok=True)
    report = build_report(root)
    paths = {
        "audit_md": write_text(out_dir / "materials" / "COMPUTE_TIMING_BOUNDARY_AUDIT.md", build_markdown(report)),
        "audit_json": write_json(out_dir / "materials" / "COMPUTE_TIMING_BOUNDARY_AUDIT.json", report),
        "evidence_csv": write_csv(
            out_dir / "tables" / "compute_timing_evidence_rows.csv",
            report["evidence_rows"],
            ["evidence_id", "claim_type", "field", "observed_value", "source", "interpretation"],
        ),
        "future_logging_csv": write_csv(
            out_dir / "tables" / "future_timing_logging_template.csv",
            report["recommendation_rows"],
            ["item", "priority", "recommended_field", "where_to_log", "reason"],
        ),
    }
    manifest = {
        "status": report["status"],
        "out_dir": str(out_dir),
        "summary": report["summary"],
        "paths": paths,
    }
    manifest_path = write_json(out_dir / "tits_compute_timing_boundary_audit_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, "status": manifest["status"], "summary": report["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
