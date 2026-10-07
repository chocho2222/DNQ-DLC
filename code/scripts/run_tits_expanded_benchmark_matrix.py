#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import concurrent.futures
import csv
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.tits_experiment_registry import (
    build_algorithm_registry,
    make_config,
    model_missing,
    read_csv,
    read_json,
    split_csv_cell,
    track_manifest_by_id,
    write_csv,
    write_json,
)


DEFAULT_PROTOCOL = "outputs/tits_dynamic_graph/tits_six_experiment_protocol_pack/tables/six_experiment_matrix.csv"
DEFAULT_TRACKS = "outputs/tits_dynamic_graph/tits_six_experiment_protocol_pack/tables/external_track_manifest.csv"
DEFAULT_BASE_CONFIG = "configs/tits_dynamic_graph_experiments.json"
DEFAULT_OUT_DIR = "outputs/tits_dynamic_graph_expanded/expanded_benchmark_matrix"


def parse_devices(devices, fallback):
    items = [item.strip() for item in str(devices or "").split(",") if item.strip()]
    return items or [fallback]


def selected_experiment_rows(rows, experiments):
    wanted = set(split_csv_cell(experiments))
    if not wanted:
        return rows
    return [row for row in rows if row.get("experiment_id") in wanted]


def case_complete(out_dir, algorithms, num_agents, seed):
    summaries = Path(out_dir) / "summaries"
    if not summaries.exists():
        return False
    for algorithm in algorithms:
        path = summaries / f"{algorithm}_n{num_agents}_seed{seed}.summary.json"
        if not path.exists():
            return False
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return False
    return True


def expand_cases(protocol_rows, track_map, registry, args):
    devices = parse_devices(args.devices, args.device)
    cases = []
    missing = []
    case_index = 0
    for row in selected_experiment_rows(protocol_rows, args.experiments):
        experiment_id = row["experiment_id"]
        if experiment_id not in {"E1_basic_effectiveness", "E2_environment_generalization", "E3_scale_extension", "E6_ablation"}:
            continue
        track_ids = split_csv_cell(row["track_ids"])
        vehicle_counts = [int(item) for item in split_csv_cell(row["vehicle_counts"])]
        seeds = [int(item) for item in split_csv_cell(row["seeds"])]
        algorithms = split_csv_cell(args.algorithms) or split_csv_cell(row["algorithms"])
        if args.algorithm_limit:
            allowed = set(split_csv_cell(args.algorithm_limit))
            algorithms = [name for name in algorithms if name in allowed]
        records = []
        for name in algorithms:
            if name not in registry:
                missing.append({"experiment_id": experiment_id, "algorithm": name, "reason": "unknown_algorithm"})
                continue
            record = registry[name]
            records.append(record)
            if model_missing(record):
                missing.append(
                    {
                        "experiment_id": experiment_id,
                        "algorithm": name,
                        "policy": record.get("policy", ""),
                        "reason": "missing_model",
                    }
                )
        if not records:
            continue
        for track_id in track_ids:
            track_path = track_map.get(track_id, track_id)
            for num_agents in vehicle_counts:
                for seed in seeds:
                    case_index += 1
                    if args.max_cases is not None and len(cases) >= args.max_cases:
                        return cases, missing
                    if args.case_start is not None and case_index < args.case_start:
                        continue
                    if args.case_end is not None and case_index > args.case_end:
                        continue
                    out_dir = Path(args.out_dir) / "runs" / experiment_id / track_id / f"n{num_agents}" / f"seed{seed}"
                    if args.skip_existing and case_complete(out_dir, [r["name"] for r in records], num_agents, seed):
                        continue
                    cases.append(
                        {
                            "case_index": case_index,
                            "experiment_id": experiment_id,
                            "track_id": track_id,
                            "track_path": "" if track_path == "procedural" else track_path,
                            "num_agents": num_agents,
                            "seed": seed,
                            "algorithms": ",".join(record["name"] for record in records),
                            "device": devices[(case_index - 1) % len(devices)],
                            "out_dir": str(out_dir),
                        }
                    )
    return cases, missing


def build_command(case, config_path, args):
    line_spacing = int(args.line_spacing)
    if args.density_controlled_spacing:
        scale = max(float(case["num_agents"]) / max(float(args.density_reference_agents), 1.0), 1.0)
        line_spacing = max(line_spacing, int(round(float(args.line_spacing) * scale)))
    command = [
        args.python,
        "scripts/run_tits_dynamic_graph_evaluation.py",
        "--config",
        str(config_path),
        "--out-dir",
        case["out_dir"],
        "--algorithms",
        case["algorithms"],
        "--num-agents",
        str(case["num_agents"]),
        "--seed",
        str(case["seed"]),
        "--max-steps",
        str(args.max_steps),
        "--finish-mode",
        args.finish_mode,
        "--observation-type",
        args.observation_type,
        "--max-neighbors",
        str(args.max_neighbors),
        "--neighbor-selection-mode",
        args.neighbor_selection_mode,
        "--traffic-profile",
        args.traffic_profile,
        "--device",
        case["device"],
        "--line-spacing",
        str(line_spacing),
        "--lateral-spacing",
        str(args.lateral_spacing),
        "--frame-every",
        str(args.frame_every),
        "--fps",
        str(args.fps),
    ]
    if case["track_path"]:
        command.extend(["--track-path", case["track_path"]])
    if args.no_gif:
        command.append("--no-gif")
    if args.first_person_gif:
        command.append("--first-person-gif")
    return command


def run_command(case, command, log_dir):
    log_path = Path(log_dir) / f"{case['experiment_id']}_{case['track_id']}_n{case['num_agents']}_seed{case['seed']}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    started = time.time()
    with log_path.open("w", encoding="utf-8") as handle:
        process = subprocess.run(command, stdout=handle, stderr=subprocess.STDOUT, check=False)
    ended = time.time()
    return {
        **case,
        "returncode": int(process.returncode),
        "elapsed_sec": ended - started,
        "log_path": str(log_path),
        "command": " ".join(command),
    }


def write_case_plan(path, cases, commands):
    rows = []
    for case, command in zip(cases, commands):
        rows.append({**case, "command": " ".join(command)})
    return write_csv(
        path,
        rows,
        [
            "case_index",
            "experiment_id",
            "track_id",
            "track_path",
            "num_agents",
            "seed",
            "algorithms",
            "device",
            "out_dir",
            "command",
        ],
    )


def write_run_results(path, rows):
    return write_csv(
        path,
        rows,
        [
            "case_index",
            "experiment_id",
            "track_id",
            "track_path",
            "num_agents",
            "seed",
            "algorithms",
            "device",
            "returncode",
            "elapsed_sec",
            "log_path",
            "out_dir",
            "command",
        ],
    )


def main():
    parser = argparse.ArgumentParser(description="Protocol-driven runner for the expanded T-ITS benchmark matrix.")
    parser.add_argument("--protocol", default=DEFAULT_PROTOCOL)
    parser.add_argument("--track-manifest", default=DEFAULT_TRACKS)
    parser.add_argument("--base-config", default=DEFAULT_BASE_CONFIG)
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR)
    parser.add_argument("--mode", choices=["dry-run", "run"], default="dry-run")
    parser.add_argument("--experiments", default="E1_basic_effectiveness,E2_environment_generalization,E3_scale_extension,E6_ablation")
    parser.add_argument("--algorithms", default="", help="Override protocol algorithms for all selected experiments.")
    parser.add_argument("--algorithm-limit", default="", help="Keep only these algorithms from protocol rows.")
    parser.add_argument("--python", default="/home/itrc/.conda/envs/vlm_planner/bin/python")
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--devices", default="")
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--max-cases", type=int, default=None)
    parser.add_argument("--case-start", type=int, default=None)
    parser.add_argument("--case-end", type=int, default=None)
    parser.add_argument("--skip-existing", action="store_true")
    parser.add_argument("--strict-models", action="store_true")
    parser.add_argument("--max-steps", type=int, default=2200)
    parser.add_argument("--finish-mode", choices=["any", "target", "all", "env_done", "steps"], default="any")
    parser.add_argument("--observation-type", choices=["telemetry", "telemetry_dynamic"], default="telemetry_dynamic")
    parser.add_argument("--max-neighbors", type=int, default=3)
    parser.add_argument("--neighbor-selection-mode", default="interaction")
    parser.add_argument("--traffic-profile", choices=["slow_traffic", "mixed_traffic"], default="slow_traffic")
    parser.add_argument("--line-spacing", type=int, default=5)
    parser.add_argument("--lateral-spacing", type=float, default=2.2)
    parser.add_argument("--density-controlled-spacing", action="store_true", help="Scale longitudinal start spacing with vehicle count to reduce density confounds in scale extrapolation.")
    parser.add_argument("--density-reference-agents", type=int, default=6)
    parser.add_argument("--no-gif", action="store_true", default=True)
    parser.add_argument("--with-gif", action="store_true", help="Enable top-down GIF generation.")
    parser.add_argument("--first-person-gif", action="store_true")
    parser.add_argument("--frame-every", type=int, default=12)
    parser.add_argument("--fps", type=int, default=12)
    parser.add_argument("--include-td3", action="store_true", help="Include TD3 in protocol overrides when available.")
    args = parser.parse_args()
    if args.with_gif:
        args.no_gif = False

    if args.include_td3 and not args.algorithms:
        args.algorithms = "v6_runtime_dynamic_neighborhood_safe,dlc_joint_transition_observer,dlc_joint_transition,dlc_individual_transition,ppo_continuous,sac_continuous,td3_continuous,rule_expert_gate,rule_safety_gate"

    out_dir = Path(args.out_dir)
    tables = out_dir / "tables"
    materials = out_dir / "materials"
    logs = out_dir / "logs"
    for path in [tables, materials, logs]:
        path.mkdir(parents=True, exist_ok=True)

    base_config = read_json(args.base_config)
    registry = build_algorithm_registry(base_config)
    protocol_rows = read_csv(args.protocol)
    track_rows = read_csv(args.track_manifest)
    track_map = track_manifest_by_id(track_rows)
    cases, missing = expand_cases(protocol_rows, track_map, registry, args)
    selected_names = sorted({name for case in cases for name in split_csv_cell(case["algorithms"])})
    config_records = [registry[name] for name in selected_names if name in registry]
    generated_config = make_config(base_config, config_records, out_dir)
    config_path = materials / "expanded_benchmark_config.json"
    write_json(config_path, generated_config)
    commands = [build_command(case, config_path, args) for case in cases]
    case_plan = write_case_plan(tables / "expanded_benchmark_case_plan.csv", cases, commands)
    missing_csv = write_csv(
        tables / "expanded_benchmark_missing_models.csv",
        missing,
        ["experiment_id", "algorithm", "policy", "reason"],
    )

    if args.strict_models and missing:
        status = "blocked_missing_models"
        results = []
    elif args.mode == "run":
        workers = max(1, int(args.jobs))
        if workers == 1:
            results = [run_command(case, command, logs) for case, command in zip(cases, commands)]
        else:
            results = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
                futures = {
                    executor.submit(run_command, case, command, logs): case
                    for case, command in zip(cases, commands)
                }
                for future in concurrent.futures.as_completed(futures):
                    results.append(future.result())
            results.sort(key=lambda row: int(row["case_index"]))
        status = "pass" if all(row["returncode"] == 0 for row in results) else "run_failed"
    else:
        results = []
        status = "dry_run_ready" if not (args.strict_models and missing) else "blocked_missing_models"

    result_csv = write_run_results(tables / "expanded_benchmark_run_results.csv", results)
    manifest = {
        "status": status,
        "mode": args.mode,
        "out_dir": args.out_dir,
        "case_count": len(cases),
        "command_count": len(commands),
        "missing_model_count": len(missing),
        "strict_models": bool(args.strict_models),
        "run_result_count": len(results),
        "failed_run_count": sum(1 for row in results if row.get("returncode") != 0),
        "paths": {
            "generated_config": str(config_path),
            "case_plan": case_plan,
            "missing_models": missing_csv,
            "run_results": result_csv,
        },
        "boundary": "Dry-run mode freezes the protocol-expanded command matrix only. Formal claims require mode=run, complete model availability, and downstream summary/statistical audits.",
    }
    manifest_path = write_json(out_dir / "expanded_benchmark_matrix_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, "status": status, "case_count": len(cases), "missing_model_count": len(missing)}, ensure_ascii=False, indent=2))
    if args.mode == "run" and status == "run_failed":
        raise SystemExit(1)
    if args.strict_models and missing:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
