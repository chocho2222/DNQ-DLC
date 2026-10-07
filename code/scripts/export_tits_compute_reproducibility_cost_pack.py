#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import json
import statistics
from pathlib import Path


SOURCE_DATA = "outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv"
ENVIRONMENT_AUDIT = "outputs/tits_dynamic_graph/tits_environment_reproducibility_audit/materials/ENVIRONMENT_REPRODUCIBILITY_AUDIT.json"
RUNTIME_REPORT = "outputs/tits_dynamic_graph/tits_runtime_scalability_pack/materials/RUNTIME_SCALABILITY_AND_COMPLEXITY_REPORT.json"
REPRO_CAPSULE = "outputs/tits_dynamic_graph/tits_reproducibility_capsule/materials/REPRODUCIBILITY_CAPSULE_QA.json"
CASE_COMMANDS = "outputs/tits_dynamic_graph/v6_confirmatory_preflight/tables/v6_confirmatory_case_commands.csv"


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


def to_float(row, key, default=0.0):
    value = row.get(key, "")
    if value in ("", None):
        return default
    try:
        return float(value)
    except ValueError:
        return default


def to_int(row, key, default=0):
    return int(round(to_float(row, key, default)))


def mean(values):
    return statistics.fmean(values) if values else 0.0


def group_by(rows, keys):
    grouped = {}
    for row in rows:
        key = tuple(row.get(item, "") for item in keys)
        grouped.setdefault(key, []).append(row)
    return grouped


def summarize_group(rows):
    finish_steps = [to_int(row, "finish_step") for row in rows]
    latency = [to_float(row, "compute_latency_ms") for row in rows]
    p95 = [to_float(row, "compute_latency_p95_ms") for row in rows]
    success = [to_float(row, "overtake_success_rate") for row in rows]
    elegant = [to_float(row, "elegant_overtake_rate") for row in rows]
    approx_planner_time_s = [
        to_float(row, "compute_latency_ms") * to_int(row, "finish_step") / 1000.0
        for row in rows
    ]
    return {
        "n_runs": len(rows),
        "total_simulated_steps": sum(finish_steps),
        "mean_finish_step": round(mean(finish_steps), 3),
        "mean_latency_ms": round(mean(latency), 3),
        "mean_latency_p95_ms": round(mean(p95), 3),
        "approx_planner_time_s": round(sum(approx_planner_time_s), 3),
        "mean_success_rate": round(mean(success), 3),
        "mean_elegant_rate": round(mean(elegant), 3),
    }


def compute_algorithm_rows(source_rows):
    rows = []
    for (algorithm, label), items in sorted(group_by(source_rows, ["algorithm", "algorithm_label_cn"]).items()):
        summary = summarize_group(items)
        rows.append(
            {
                "algorithm": algorithm,
                "algorithm_label_cn": label,
                **summary,
                "interpretation": "approx_planner_time_s is a derived workload proxy, not measured wall-clock time.",
            }
        )
    return rows


def compute_benchmark_rows(source_rows):
    rows = []
    for (benchmark, num_agents), items in sorted(group_by(source_rows, ["_benchmark", "num_agents"]).items()):
        summary = summarize_group(items)
        rows.append(
            {
                "benchmark": benchmark,
                "num_agents": num_agents,
                **summary,
                "case_count": len({(row.get("_benchmark"), row.get("num_agents"), row.get("seed")) for row in items}),
            }
        )
    return rows


def compute_environment_rows(environment):
    rows = []
    python = environment.get("python", {})
    torch = environment.get("torch", {})
    nvidia = environment.get("nvidia_smi", {})
    rows.append({"item": "python_executable", "value": python.get("current_executable", ""), "note": "recorded by environment audit"})
    rows.append({"item": "python_version", "value": python.get("version", ""), "note": "recorded by environment audit"})
    rows.append({"item": "platform", "value": python.get("platform", ""), "note": "recorded by environment audit"})
    rows.append({"item": "torch_version", "value": torch.get("version", ""), "note": "recorded by environment audit"})
    rows.append({"item": "torch_cuda_available", "value": str(torch.get("cuda_available", "")), "note": "must be true for GPU reproduction"})
    rows.append({"item": "torch_cuda_device_count", "value": str(torch.get("cuda_device_count", "")), "note": "recorded by torch"})
    rows.append({"item": "torch_cuda_version", "value": str(torch.get("cuda_version", "")), "note": "recorded by torch"})
    gpu_names = "; ".join(gpu.get("name", "") for gpu in nvidia.get("gpus", []))
    gpu_memory = "; ".join(str(gpu.get("memory_total_mb", "")) for gpu in nvidia.get("gpus", []))
    rows.append({"item": "nvidia_smi_available", "value": str(nvidia.get("available", "")), "note": "recorded by nvidia-smi"})
    rows.append({"item": "gpu_names", "value": gpu_names, "note": "recorded by nvidia-smi"})
    rows.append({"item": "gpu_memory_total_mb", "value": gpu_memory, "note": "per GPU, recorded by nvidia-smi"})
    return rows


def reproduction_tiers(case_commands):
    return [
        {
            "tier": "T0",
            "name_cn": "审稿人快速 smoke",
            "expected_scope": "短程入口检查；不作为性能结果",
            "primary_command": "bash outputs/tits_dynamic_graph/reviewer_replication_packet/run_reviewer_smoke.sh && /home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_reviewer_smoke_execution_audit.py --out-dir outputs/tits_dynamic_graph/tits_reviewer_smoke_execution_audit",
            "formal_result": "no",
            "estimated_cases_or_runs": "smoke-only",
        },
        {
            "tier": "T1",
            "name_cn": "正式 source data 复核",
            "expected_scope": "读取冻结 240-run source data，重建统计、图表和审计材料",
            "primary_command": "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_compute_reproducibility_cost_pack.py --out-dir outputs/tits_dynamic_graph/tits_compute_reproducibility_cost_pack",
            "formal_result": "yes, reporting layer only",
            "estimated_cases_or_runs": "0 new simulator runs",
        },
        {
            "tier": "T2",
            "name_cn": "确认性在线矩阵重跑",
            "expected_scope": "按冻结 case commands 重跑 30 cases；每个 case 评估 8 个算法",
            "primary_command": "see outputs/tits_dynamic_graph/v6_confirmatory_preflight/tables/v6_confirmatory_case_commands.csv",
            "formal_result": "yes, if all commands are run under the declared environment",
            "estimated_cases_or_runs": f"{len(case_commands)} case commands / 240 algorithm-runs",
        },
        {
            "tier": "T3",
            "name_cn": "视觉证据重建",
            "expected_scope": "重建代表性俯视图和第一视角 GIF；用于视觉说明，不替代统计主证据",
            "primary_command": "bash scripts/run_tits_representative_gifs.sh",
            "formal_result": "visual evidence only",
            "estimated_cases_or_runs": "representative cases only",
        },
    ]


def build_report(root):
    source_rows = read_csv(root / SOURCE_DATA)
    environment = read_json(root / ENVIRONMENT_AUDIT)
    runtime = read_json(root / RUNTIME_REPORT)
    capsule = read_json(root / REPRO_CAPSULE)
    case_commands = read_csv(root / CASE_COMMANDS)
    algorithms = sorted({row.get("algorithm", "") for row in source_rows})
    cases = sorted({(row.get("_benchmark", ""), row.get("num_agents", ""), row.get("seed", "")) for row in source_rows})
    total_steps = sum(to_int(row, "finish_step") for row in source_rows)
    approx_planner_time_s = sum(
        to_float(row, "compute_latency_ms") * to_int(row, "finish_step") / 1000.0 for row in source_rows
    )
    summary = {
        "status": "pass" if len(source_rows) == 240 and len(algorithms) == 8 and len(cases) == 30 else "review_required",
        "source_rows": len(source_rows),
        "algorithm_count": len(algorithms),
        "matched_case_count": len(cases),
        "case_command_count": len(case_commands),
        "total_simulated_steps_across_algorithm_runs": total_steps,
        "approx_planner_time_proxy_s": round(approx_planner_time_s, 3),
        "wall_clock_time_recorded": False,
        "environment_audit_status": environment.get("status", ""),
        "runtime_scalability_status": runtime.get("status", ""),
        "reproducibility_capsule_status": capsule.get("status", ""),
        "gpu_count": environment.get("torch", {}).get("cuda_device_count", 0),
        "cuda_available": environment.get("torch", {}).get("cuda_available", False),
        "safe_n8_latency_ms": runtime.get("summary", {}).get("safe_n8_latency_ms"),
        "dlc_n8_latency_ms": runtime.get("summary", {}).get("dlc_n8_latency_ms"),
        "max_neighbors": runtime.get("summary", {}).get("max_neighbors"),
    }
    return {
        "status": summary["status"],
        "summary": summary,
        "algorithm_rows": compute_algorithm_rows(source_rows),
        "benchmark_rows": compute_benchmark_rows(source_rows),
        "environment_rows": compute_environment_rows(environment),
        "reproduction_tiers": reproduction_tiers(case_commands),
        "claim_boundaries": [
            {
                "topic": "wall_clock_time",
                "allowed_claim": "当前证据链报告仿真步数、平均控制延迟和派生 workload proxy。",
                "forbidden_claim": "不能声称已记录完整 wall-clock 训练/评估耗时或 GPU 利用率曲线。",
            },
            {
                "topic": "gpu_reproduction",
                "allowed_claim": "环境审计记录了 CUDA 可用性、GPU 数量、驱动/CUDA/PyTorch 版本。",
                "forbidden_claim": "不能保证跨不同 GPU、Box2D 或 CUDA 版本 bitwise identical。",
            },
            {
                "topic": "formal_results",
                "allowed_claim": "正式性能结果来自冻结 30 matched cases × 8 algorithms 的 240 algorithm-runs。",
                "forbidden_claim": "不能把 smoke、partial、quality sweep 或 GIF-only 输出写成正式统计结果。",
            },
        ],
    }


def build_markdown(report):
    summary = report["summary"]
    lines = [
        "# T-ITS 计算资源与复现成本报告",
        "",
        "该报告面向 IEEE T-ITS 审稿与开源复现，汇总正式 240-run 在线矩阵的仿真规模、控制延迟、GPU/环境快照和分层复现路线。报告只读取已有冻结结果，不新增实验结果。",
        "",
        "## 核心结论",
        "",
        f"- 状态：`{report['status']}`",
        f"- 正式 source data 行数：{summary['source_rows']}",
        f"- 对比算法数：{summary['algorithm_count']}",
        f"- matched cases：{summary['matched_case_count']}",
        f"- 冻结 case commands：{summary['case_command_count']}",
        f"- 所有 algorithm-runs 合计仿真步数：{summary['total_simulated_steps_across_algorithm_runs']}",
        f"- 派生控制器 workload proxy：{summary['approx_planner_time_proxy_s']} s",
        f"- wall-clock time 是否完整记录：{summary['wall_clock_time_recorded']}",
        f"- CUDA 可用：{summary['cuda_available']}；GPU 数量：{summary['gpu_count']}",
        f"- n=8 v6-safe 平均延迟：{summary['safe_n8_latency_ms']} ms；原始 DLC：{summary['dlc_n8_latency_ms']} ms",
        f"- 运行时动态图最大邻居数：{summary['max_neighbors']}",
        "",
        "## 按算法的复现成本",
        "",
        "| 算法 | runs | 仿真步数 | 平均终止步 | 平均延迟(ms) | p95延迟均值(ms) | workload proxy(s) | 成功率 | Desirable overtaking behavior rate |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in report["algorithm_rows"]:
        lines.append(
            f"| {row['algorithm_label_cn']} | {row['n_runs']} | {row['total_simulated_steps']} | "
            f"{row['mean_finish_step']} | {row['mean_latency_ms']} | {row['mean_latency_p95_ms']} | "
            f"{row['approx_planner_time_s']} | {row['mean_success_rate']} | {row['mean_elegant_rate']} |"
        )
    lines.extend(
        [
            "",
            "## 分层复现路线",
            "",
            "| 层级 | 名称 | 范围 | 是否正式结果 | 命令/入口 |",
            "|---|---|---|---|---|",
        ]
    )
    for row in report["reproduction_tiers"]:
        lines.append(
            f"| {row['tier']} | {row['name_cn']} | {row['expected_scope']} | {row['formal_result']} | `{row['primary_command']}` |"
        )
    lines.extend(
        [
            "",
            "## 写作边界",
            "",
            "| 主题 | 可以写 | 不应写 |",
            "|---|---|---|",
        ]
    )
    for row in report["claim_boundaries"]:
        lines.append(f"| {row['topic']} | {row['allowed_claim']} | {row['forbidden_claim']} |")
    lines.extend(
        [
            "",
            "## 建议写入论文的位置",
            "",
            "- Methods/Reproducibility：说明正式评估为 30 matched cases × 8 algorithms，GPU 环境、Python/PyTorch/CUDA 版本由环境审计记录。",
            "- Experiments：报告仿真步数、车辆数、seed/track/traffic 控制条件，并说明 smoke/GIF 不作为统计主结果。",
            "- Limitations：明确当前没有完整 wall-clock/GPU utilization 归档；重跑完整矩阵的耗时应由后续公开服务器或数据仓库补充记录。",
            "",
            "## 主要输入",
            "",
            f"- Source data：`{SOURCE_DATA}`",
            f"- 环境审计：`{ENVIRONMENT_AUDIT}`",
            f"- 运行时扩展性报告：`{RUNTIME_REPORT}`",
            f"- 复现胶囊：`{REPRO_CAPSULE}`",
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Export a T-ITS compute and reproducibility cost pack.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/tits_compute_reproducibility_cost_pack")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    out_dir = root / args.out_dir
    materials = out_dir / "materials"
    tables = out_dir / "tables"
    materials.mkdir(parents=True, exist_ok=True)
    tables.mkdir(parents=True, exist_ok=True)

    report = build_report(root)
    paths = {
        "report_md": write_text(materials / "COMPUTE_REPRODUCIBILITY_COST_REPORT.md", build_markdown(report)),
        "report_json": write_json(materials / "COMPUTE_REPRODUCIBILITY_COST_REPORT.json", report),
        "algorithm_cost_csv": write_csv(
            tables / "compute_cost_by_algorithm.csv",
            report["algorithm_rows"],
            [
                "algorithm",
                "algorithm_label_cn",
                "n_runs",
                "total_simulated_steps",
                "mean_finish_step",
                "mean_latency_ms",
                "mean_latency_p95_ms",
                "approx_planner_time_s",
                "mean_success_rate",
                "mean_elegant_rate",
                "interpretation",
            ],
        ),
        "benchmark_cost_csv": write_csv(
            tables / "compute_cost_by_benchmark.csv",
            report["benchmark_rows"],
            [
                "benchmark",
                "num_agents",
                "n_runs",
                "total_simulated_steps",
                "mean_finish_step",
                "mean_latency_ms",
                "mean_latency_p95_ms",
                "approx_planner_time_s",
                "mean_success_rate",
                "mean_elegant_rate",
                "case_count",
            ],
        ),
        "environment_snapshot_csv": write_csv(
            tables / "compute_environment_snapshot.csv",
            report["environment_rows"],
            ["item", "value", "note"],
        ),
        "reproduction_tiers_csv": write_csv(
            tables / "compute_reproduction_tiers.csv",
            report["reproduction_tiers"],
            ["tier", "name_cn", "expected_scope", "primary_command", "formal_result", "estimated_cases_or_runs"],
        ),
        "claim_boundaries_csv": write_csv(
            tables / "compute_claim_boundaries.csv",
            report["claim_boundaries"],
            ["topic", "allowed_claim", "forbidden_claim"],
        ),
    }
    manifest = {
        "status": report["status"],
        "out_dir": args.out_dir,
        "summary": report["summary"],
        "paths": paths,
    }
    manifest_path = write_json(out_dir / "tits_compute_reproducibility_cost_pack_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, "status": report["status"], "summary": report["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
