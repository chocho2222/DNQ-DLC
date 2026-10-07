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


DEFAULT_PROTOCOL_JSON = "outputs/tits_dynamic_graph/tits_six_experiment_protocol_pack/materials/six_experiment_protocol.json"
DEFAULT_TRACKS = "outputs/tits_dynamic_graph/tits_six_experiment_protocol_pack/tables/external_track_manifest.csv"
DEFAULT_BASE_CONFIG = "configs/tits_dynamic_graph_experiments.json"
DEFAULT_OUT_DIR = "outputs/tits_dynamic_graph_expanded/mixed_controller_tournament"


def parse_devices(devices, fallback):
    items = [item.strip() for item in str(devices or "").split(",") if item.strip()]
    return items or [fallback]


def e4_cases(protocol_json):
    for row in protocol_json.get("experiments", []):
        if row.get("experiment_id") == "E4_interaction_generalization":
            return row
    return {}


def build_assignment(num_agents, target_algorithm, opponents):
    if not opponents:
        opponents = ["rule_expert_gate"]
    assignment = []
    for agent_id in range(num_agents):
        if agent_id == num_agents - 1:
            assignment.append(target_algorithm)
        else:
            assignment.append(opponents[agent_id % len(opponents)])
    return assignment


def expand_cases(protocol_json, track_map, args):
    row = e4_cases(protocol_json)
    if not row:
        return []
    track_ids = split_csv_cell(args.tracks) or split_csv_cell(row.get("track_ids", ""))
    vehicle_counts = [int(item) for item in (split_csv_cell(args.vehicle_counts) or split_csv_cell(row.get("vehicle_counts", "")))]
    seeds = [int(item) for item in (split_csv_cell(args.seeds) or split_csv_cell(row.get("seeds", "")))]
    target_algorithm = args.target_algorithm
    opponents = split_csv_cell(args.opponent_algorithms)
    devices = parse_devices(args.devices, args.device)
    cases = []
    index = 0
    for track_id in track_ids:
        track_path = track_map.get(track_id, track_id)
        for num_agents in vehicle_counts:
            assignment = build_assignment(num_agents, target_algorithm, opponents)
            for seed in seeds:
                index += 1
                if args.max_cases is not None and len(cases) >= args.max_cases:
                    return cases
                cases.append(
                    {
                        "case_index": index,
                        "experiment_id": "E4_interaction_generalization",
                        "track_id": track_id,
                        "track_path": "" if track_path == "procedural" else track_path,
                        "num_agents": num_agents,
                        "seed": seed,
                        "target_algorithm": target_algorithm,
                        "assignment": ",".join(assignment),
                        "device": devices[(index - 1) % len(devices)],
                        "out_dir": str(Path(args.out_dir) / "runs" / track_id / f"n{num_agents}" / f"seed{seed}"),
                    }
                )
    return cases


def build_case_config(base_config, registry, assignment, out_dir):
    records = []
    seen = set()
    for name in assignment:
        if name not in registry or name in seen:
            continue
        records.append(registry[name])
        seen.add(name)
    return make_config(base_config, records, out_dir)


def build_command(case, config_path, args):
    command = [
        args.python,
        "scripts/run_tits_mixed_controller_tournament_case.py",
        "--config",
        str(config_path),
        "--out-dir",
        case["out_dir"],
        "--assignment",
        case["assignment"],
        "--target-agent",
        str(case["num_agents"] - 1),
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
        "--traffic-profile",
        args.traffic_profile,
        "--device",
        case["device"],
        "--line-spacing",
        str(args.line_spacing),
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
    if args.legacy_checkpoint_migration:
        command.append("--legacy-checkpoint-migration")
    if args.first_person_gif:
        command.append("--first-person-gif")
    return command


def run_command(case, command, log_dir):
    log_path = Path(log_dir) / f"mixed_{case['track_id']}_n{case['num_agents']}_seed{case['seed']}.log"
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


def main():
    parser = argparse.ArgumentParser(description="Run mixed-controller interaction generalization tournaments for T-ITS E4.")
    parser.add_argument("--protocol", default=DEFAULT_PROTOCOL_JSON)
    parser.add_argument("--track-manifest", default=DEFAULT_TRACKS)
    parser.add_argument("--base-config", default=DEFAULT_BASE_CONFIG)
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR)
    parser.add_argument("--mode", choices=["dry-run", "run"], default="dry-run")
    parser.add_argument("--target-algorithm", default="v6_runtime_dynamic_neighborhood_safe")
    parser.add_argument("--opponent-algorithms", default="dlc_joint_transition_observer,dlc_joint_transition,ppo_continuous,rule_expert_gate,rule_safety_gate")
    parser.add_argument("--tracks", default="")
    parser.add_argument("--vehicle-counts", default="")
    parser.add_argument("--seeds", default="")
    parser.add_argument("--python", default="/home/itrc/.conda/envs/vlm_planner/bin/python")
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--devices", default="")
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--max-cases", type=int, default=None)
    parser.add_argument("--strict-models", action="store_true")
    parser.add_argument("--max-steps", type=int, default=2200)
    parser.add_argument("--finish-mode", choices=["any", "target", "all", "env_done", "steps"], default="any")
    parser.add_argument("--observation-type", choices=["telemetry", "telemetry_dynamic"], default="telemetry_dynamic")
    parser.add_argument("--max-neighbors", type=int, default=3)
    parser.add_argument("--traffic-profile", choices=["slow_traffic", "mixed_traffic"], default="mixed_traffic")
    parser.add_argument("--line-spacing", type=int, default=5)
    parser.add_argument("--lateral-spacing", type=float, default=3.0)
    parser.add_argument("--legacy-checkpoint-migration", action="store_true",
                        help="Explicitly migrate legacy DLC/RL checkpoints for corrected telemetry evaluation.")
    parser.add_argument("--no-gif", action="store_true", default=True)
    parser.add_argument("--with-gif", action="store_true")
    parser.add_argument("--first-person-gif", action="store_true")
    parser.add_argument("--frame-every", type=int, default=12)
    parser.add_argument("--fps", type=int, default=12)
    args = parser.parse_args()
    if args.with_gif:
        args.no_gif = False

    out_dir = Path(args.out_dir)
    tables = out_dir / "tables"
    materials = out_dir / "materials"
    logs = out_dir / "logs"
    for path in [tables, materials, logs]:
        path.mkdir(parents=True, exist_ok=True)

    protocol_json = read_json(args.protocol)
    track_map = track_manifest_by_id(read_csv(args.track_manifest))
    base_config = read_json(args.base_config)
    registry = build_algorithm_registry(base_config)
    cases = expand_cases(protocol_json, track_map, args)
    all_algorithms = sorted({name for case in cases for name in split_csv_cell(case["assignment"])})
    missing = []
    for name in all_algorithms:
        if name not in registry:
            missing.append({"algorithm": name, "policy": "", "reason": "unknown_algorithm"})
            continue
        if model_missing(registry[name]):
            missing.append({"algorithm": name, "policy": registry[name].get("policy", ""), "reason": "missing_model"})

    config = build_case_config(base_config, registry, all_algorithms, out_dir)
    config_path = materials / "mixed_controller_config.json"
    write_json(config_path, config)
    commands = [build_command(case, config_path, args) for case in cases]
    case_rows = [{**case, "command": " ".join(cmd)} for case, cmd in zip(cases, commands)]
    case_plan = write_csv(
        tables / "mixed_controller_case_plan.csv",
        case_rows,
        [
            "case_index",
            "experiment_id",
            "track_id",
            "track_path",
            "num_agents",
            "seed",
            "target_algorithm",
            "assignment",
            "device",
            "out_dir",
            "command",
        ],
    )
    missing_csv = write_csv(tables / "mixed_controller_missing_models.csv", missing, ["algorithm", "policy", "reason"])

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
        status = "dry_run_ready"

    result_csv = write_csv(
        tables / "mixed_controller_run_results.csv",
        results,
        [
            "case_index",
            "experiment_id",
            "track_id",
            "track_path",
            "num_agents",
            "seed",
            "target_algorithm",
            "assignment",
            "device",
            "returncode",
            "elapsed_sec",
            "log_path",
            "out_dir",
            "command",
        ],
    )
    manifest = {
        "status": status,
        "mode": args.mode,
        "case_count": len(cases),
        "missing_model_count": len(missing),
        "run_result_count": len(results),
        "failed_run_count": sum(1 for row in results if row.get("returncode") != 0),
        "paths": {
            "config": str(config_path),
            "case_plan": case_plan,
            "missing_models": missing_csv,
            "run_results": result_csv,
        },
        "boundary": "E4 is a supplementary mixed-controller interaction experiment. It should not replace the independent target-controller confirmatory matrix.",
    }
    manifest_path = write_json(out_dir / "mixed_controller_tournament_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, "status": status, "case_count": len(cases), "missing_model_count": len(missing)}, ensure_ascii=False, indent=2))
    if args.mode == "run" and status == "run_failed":
        raise SystemExit(1)
    if args.strict_models and missing:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
