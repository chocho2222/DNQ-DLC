#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import json
import shlex
from collections import defaultdict
from pathlib import Path


CASE_COMMANDS = "outputs/tits_dynamic_graph/v6_confirmatory_preflight/tables/v6_confirmatory_case_commands.csv"
SOURCE_CSV = "outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv"
ALGORITHM_CARDS = "outputs/tits_dynamic_graph/tits_benchmark_protocol_pack/tables/algorithm_cards.csv"

EXPECTED_ALGORITHMS = [
    "v6_runtime_dynamic_neighborhood",
    "v6_runtime_dynamic_neighborhood_safe",
    "quality_proposal_dlc_world_v1",
    "dlc_world_original",
    "dlc_world_balanced",
    "dlc_world_safety",
    "dlc_world_fast",
    "rule_expert_gate",
]
EXPECTED_FIXED_FLAGS = {
    "max-steps": "2200",
    "finish-mode": "any",
    "observation-type": "telemetry_dynamic",
    "max-neighbors": "3",
    "traffic-profile": "slow_traffic",
}


def read_csv(path):
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path, rows, fields):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return str(path)


def write_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")
    return str(path)


def write_json(path, data):
    return write_text(path, json.dumps(data, ensure_ascii=False, indent=2))


def parse_flags(command):
    tokens = shlex.split(command)
    flags = {}
    idx = 0
    while idx < len(tokens):
        tok = tokens[idx]
        if tok.startswith("--"):
            name = tok[2:]
            if idx + 1 < len(tokens) and not tokens[idx + 1].startswith("--"):
                flags[name] = tokens[idx + 1]
                idx += 2
            else:
                flags[name] = True
                idx += 1
        else:
            idx += 1
    return flags


def case_key(row):
    return (row.get("_benchmark", ""), str(row.get("num_agents", "")), str(row.get("seed", "")))


def command_case_key(row):
    return (row.get("benchmark", ""), str(row.get("num_agents", "")), str(row.get("seed", "")))


def load_json(path):
    path = Path(path)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"_load_error": repr(exc)}


def normalize_track_path(value):
    if not value or value == "None":
        return "procedural"
    return value


def build_command_rows(case_commands, expected_algorithms):
    rows = []
    for row in case_commands:
        flags = parse_flags(row["command"])
        algorithms = flags.get("algorithms", "")
        algorithm_list = [item for item in algorithms.split(",") if item]
        errors = []
        warnings = []
        if algorithm_list != expected_algorithms:
            errors.append("algorithm_list_differs_from_protocol_order")
        for flag, expected in EXPECTED_FIXED_FLAGS.items():
            if str(flags.get(flag, "")) != expected:
                errors.append(f"{flag}_expected_{expected}_observed_{flags.get(flag, '')}")
        if str(flags.get("num-agents", "")) != str(row["num_agents"]):
            errors.append("num_agents_flag_mismatch")
        if str(flags.get("seed", "")) != str(row["seed"]):
            errors.append("seed_flag_mismatch")
        expected_track = row["track_path"]
        observed_track = normalize_track_path(flags.get("track-path", "procedural"))
        if expected_track != observed_track:
            errors.append(f"track_path_mismatch_expected_{expected_track}_observed_{observed_track}")
        if flags.get("no-gif") is not True:
            warnings.append("no_gif_flag_missing")
        rows.append(
            {
                "case_id": row["case_id"],
                "benchmark": row["benchmark"],
                "num_agents": row["num_agents"],
                "seed": row["seed"],
                "track_path": row["track_path"],
                "device": row["device"],
                "algorithm_count": len(algorithm_list),
                "algorithm_list": ",".join(algorithm_list),
                "max_steps": flags.get("max-steps", ""),
                "finish_mode": flags.get("finish-mode", ""),
                "observation_type": flags.get("observation-type", ""),
                "max_neighbors": flags.get("max-neighbors", ""),
                "traffic_profile": flags.get("traffic-profile", ""),
                "track_path_flag": observed_track,
                "no_gif": flags.get("no-gif") is True,
                "status": "pass" if not errors else "error",
                "errors": ";".join(errors),
                "warnings": ";".join(warnings),
            }
        )
    return rows


def build_source_case_rows(source_rows, expected_algorithms):
    grouped = defaultdict(list)
    for row in source_rows:
        grouped[case_key(row)].append(row)
    out = []
    for key, rows in sorted(grouped.items()):
        benchmark, num_agents, seed = key
        algorithms = sorted(row["algorithm"] for row in rows)
        errors = []
        if sorted(expected_algorithms) != algorithms:
            errors.append("algorithm_set_mismatch")
        track_values = sorted({row.get("track_path", "") for row in rows})
        traffic_values = sorted({row.get("traffic_profile", "") for row in rows})
        finish_values = sorted({row.get("finish_step", "") for row in rows})
        if len(track_values) != 1:
            errors.append("track_path_not_shared")
        if len(traffic_values) != 1:
            errors.append("traffic_profile_not_shared")
        out.append(
            {
                "case_id": f"{benchmark}|n{num_agents}|seed{seed}",
                "benchmark": benchmark,
                "num_agents": num_agents,
                "seed": seed,
                "algorithm_count": len(algorithms),
                "algorithms": ",".join(algorithms),
                "track_path_values": ";".join(track_values),
                "traffic_profile_values": ";".join(traffic_values),
                "finish_step_values": ";".join(finish_values),
                "status": "pass" if not errors else "error",
                "errors": ";".join(errors),
            }
        )
    return out


def build_summary_rows(source_rows):
    out = []
    for row in source_rows:
        summary_path = row.get("_summary_file", "")
        data = load_json(summary_path)
        errors = []
        warnings = []
        num_agents = int(row["num_agents"])
        expected_target_agent = num_agents - 1
        if data.get("_load_error"):
            errors.append("summary_json_load_failed")
        if data.get("num_agents") != num_agents:
            errors.append("num_agents_mismatch")
        if data.get("seed") != int(row["seed"]):
            errors.append("seed_mismatch")
        if data.get("target_agent") != expected_target_agent:
            errors.append("target_agent_not_last_index")
        if data.get("target_initial_rank") != num_agents:
            errors.append("target_initial_rank_not_last")
        if data.get("observation_type") != "telemetry_dynamic":
            errors.append("observation_type_mismatch")
        if data.get("traffic_profile") != "slow_traffic":
            errors.append("traffic_profile_mismatch")
        if normalize_track_path(data.get("track_path")) != normalize_track_path(row.get("track_path")):
            errors.append("track_path_mismatch")
        start_order = data.get("start_order")
        if not isinstance(start_order, list) or len(start_order) != num_agents:
            warnings.append("start_order_missing_or_wrong_length")
        out.append(
            {
                "case_id": f"{row['_benchmark']}|n{row['num_agents']}|seed{row['seed']}",
                "algorithm": row["algorithm"],
                "summary_file": summary_path,
                "num_agents": row["num_agents"],
                "seed": row["seed"],
                "target_agent": data.get("target_agent", ""),
                "expected_target_agent": expected_target_agent,
                "target_initial_rank": data.get("target_initial_rank", ""),
                "expected_target_initial_rank": num_agents,
                "observation_type": data.get("observation_type", ""),
                "traffic_profile": data.get("traffic_profile", ""),
                "track_path": data.get("track_path", ""),
                "start_order_len": len(start_order) if isinstance(start_order, list) else "",
                "status": "pass" if not errors else "error",
                "errors": ";".join(errors),
                "warnings": ";".join(warnings),
            }
        )
    return out


def algorithm_fairness_rows(algorithm_cards):
    rows = []
    for row in algorithm_cards:
        algorithm = row["algorithm"]
        family = row.get("family", "")
        is_rule = family == "rule_baseline"
        rows.append(
            {
                "algorithm": algorithm,
                "label_cn": row.get("label_cn", ""),
                "family": family,
                "shared_case_commands": True,
                "shared_seed_track_traffic": True,
                "model_path": row.get("model_path", ""),
                "quality_proposal_path": row.get("quality_proposal_path", ""),
                "overtake_aware_planner": row.get("overtake_aware_planner", ""),
                "planner_horizon": row.get("planner_horizon", ""),
                "planner_candidates": row.get("planner_candidates", ""),
                "allowed_difference": "hand-engineered policy without learned model" if is_rule else "algorithm/model/planner design difference declared in algorithm card",
                "fairness_note": "All algorithms are evaluated inside the same frozen case command for each seed/track/vehicle-count condition.",
            }
        )
    return rows


def summarize(command_rows, source_case_rows, summary_rows, algorithm_rows):
    command_errors = [row for row in command_rows if row["status"] != "pass"]
    source_errors = [row for row in source_case_rows if row["status"] != "pass"]
    summary_errors = [row for row in summary_rows if row["status"] != "pass"]
    target_last_pass = sum(1 for row in summary_rows if row["target_initial_rank"] == row["expected_target_initial_rank"] and row["target_agent"] == row["expected_target_agent"])
    return {
        "status": "pass" if not command_errors and not source_errors and not summary_errors else "review_required",
        "case_command_count": len(command_rows),
        "source_case_count": len(source_case_rows),
        "algorithm_count": len(algorithm_rows),
        "summary_run_count": len(summary_rows),
        "command_error_count": len(command_errors),
        "source_case_error_count": len(source_errors),
        "summary_error_count": len(summary_errors),
        "target_last_start_verified_runs": target_last_pass,
        "target_last_start_expected_runs": len(summary_rows),
        "shared_algorithm_command_rows": sum(1 for row in command_rows if row["algorithm_count"] == len(EXPECTED_ALGORITHMS)),
    }


def build_markdown(report):
    summary = report["summary"]
    lines = [
        "# T-ITS Baseline Fairness Audit",
        "",
        "该审计检查确认性在线矩阵是否满足公平对比要求：同一 case 下所有算法共享 seed、车辆数、赛道、交通配置、最大步数、终止条件、观测类型和邻居预算；算法差异仅来自 algorithm card 中声明的模型、规划器或规则策略差异。",
        "",
        "## Summary",
        "",
    ]
    for key, value in summary.items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## What Is Shared",
            "",
            "- 每个 frozen case command 同时运行 8 个正式算法，避免按算法单独改变 seed/track/traffic。",
            "- 固定命令参数：`--max-steps 2200`、`--finish-mode any`、`--observation-type telemetry_dynamic`、`--max-neighbors 3`、`--traffic-profile slow_traffic`。",
            "- Source data 中每个 matched case 均包含 8 个算法结果，且 track path 和 traffic profile 在 case 内一致。",
            "- Summary JSON 验证目标车 `target_agent=num_agents-1` 且 `target_initial_rank=num_agents`，即目标车最后身位起步。",
            "",
            "## What Is Allowed To Differ",
            "",
            "- 模型权重、DLC 变种参数、quality proposal、planner horizon/candidates/risk weights 和规则专家策略按 algorithm card 声明不同。",
            "- case 间 GPU device 可以不同；同一 case 内 8 个算法由同一个 command 在相同配置下生成。",
            "- GIF 是否生成不作为性能条件；确认性矩阵使用 `--no-gif`，publication GIF 是单独代表性可视化。",
            "",
            "## Blocking Issues",
            "",
        ]
    )
    blocking = []
    for key in ["command_rows", "source_case_rows", "summary_rows"]:
        blocking.extend([row for row in report[key] if row.get("status") != "pass"])
    if not blocking:
        lines.append("No blocking baseline-fairness issues were found.")
    else:
        lines.extend(["| source | status | errors |", "|---|---|---|"])
        for row in blocking[:80]:
            lines.append(f"| {row.get('case_id', row.get('algorithm', ''))} | {row.get('status')} | {row.get('errors')} |")
    lines.extend(
        [
            "",
            "## Regeneration Command",
            "",
            "```bash",
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_baseline_fairness_audit.py --out-dir outputs/tits_dynamic_graph/tits_baseline_fairness_audit",
            "```",
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Audit fairness of baseline comparisons in the T-ITS confirmatory matrix.")
    parser.add_argument("--case-commands", default=CASE_COMMANDS)
    parser.add_argument("--source-csv", default=SOURCE_CSV)
    parser.add_argument("--algorithm-cards", default=ALGORITHM_CARDS)
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/tits_baseline_fairness_audit")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    materials = out_dir / "materials"
    tables = out_dir / "tables"
    materials.mkdir(parents=True, exist_ok=True)
    tables.mkdir(parents=True, exist_ok=True)

    case_commands = read_csv(args.case_commands)
    source_rows = read_csv(args.source_csv)
    algorithm_cards = read_csv(args.algorithm_cards)
    command_rows = build_command_rows(case_commands, EXPECTED_ALGORITHMS)
    source_case_rows = build_source_case_rows(source_rows, EXPECTED_ALGORITHMS)
    summary_rows = build_summary_rows(source_rows)
    algorithm_rows = algorithm_fairness_rows(algorithm_cards)
    report = {
        "status": "pending",
        "inputs": {
            "case_commands": args.case_commands,
            "source_csv": args.source_csv,
            "algorithm_cards": args.algorithm_cards,
        },
        "summary": {},
        "command_rows": command_rows,
        "source_case_rows": source_case_rows,
        "summary_rows": summary_rows,
        "algorithm_rows": algorithm_rows,
        "note": "This audit validates benchmark-condition fairness. It does not claim equal compute budgets across algorithm families; compute and latency are reported separately.",
    }
    report["summary"] = summarize(command_rows, source_case_rows, summary_rows, algorithm_rows)
    report["status"] = report["summary"]["status"]
    paths = {
        "audit_md": write_text(materials / "BASELINE_FAIRNESS_AUDIT.md", build_markdown(report)),
        "audit_json": write_json(materials / "BASELINE_FAIRNESS_AUDIT.json", report),
        "command_checks_csv": write_csv(
            tables / "fairness_command_checks.csv",
            command_rows,
            [
                "case_id",
                "benchmark",
                "num_agents",
                "seed",
                "track_path",
                "device",
                "algorithm_count",
                "algorithm_list",
                "max_steps",
                "finish_mode",
                "observation_type",
                "max_neighbors",
                "traffic_profile",
                "track_path_flag",
                "no_gif",
                "status",
                "errors",
                "warnings",
            ],
        ),
        "source_case_checks_csv": write_csv(
            tables / "fairness_source_case_checks.csv",
            source_case_rows,
            [
                "case_id",
                "benchmark",
                "num_agents",
                "seed",
                "algorithm_count",
                "algorithms",
                "track_path_values",
                "traffic_profile_values",
                "finish_step_values",
                "status",
                "errors",
            ],
        ),
        "summary_checks_csv": write_csv(
            tables / "fairness_summary_run_checks.csv",
            summary_rows,
            [
                "case_id",
                "algorithm",
                "summary_file",
                "num_agents",
                "seed",
                "target_agent",
                "expected_target_agent",
                "target_initial_rank",
                "expected_target_initial_rank",
                "observation_type",
                "traffic_profile",
                "track_path",
                "start_order_len",
                "status",
                "errors",
                "warnings",
            ],
        ),
        "algorithm_fairness_csv": write_csv(
            tables / "fairness_algorithm_declared_differences.csv",
            algorithm_rows,
            [
                "algorithm",
                "label_cn",
                "family",
                "shared_case_commands",
                "shared_seed_track_traffic",
                "model_path",
                "quality_proposal_path",
                "overtake_aware_planner",
                "planner_horizon",
                "planner_candidates",
                "allowed_difference",
                "fairness_note",
            ],
        ),
    }
    manifest = {
        "status": report["status"],
        "out_dir": args.out_dir,
        "summary": report["summary"],
        "paths": paths,
    }
    manifest_path = write_json(out_dir / "tits_baseline_fairness_audit_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, "status": report["status"], "summary": report["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
