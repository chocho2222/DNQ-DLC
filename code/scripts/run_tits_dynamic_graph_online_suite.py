#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import concurrent.futures
import csv
import json
import subprocess
import time
from pathlib import Path


def load_config(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def ensure_dirs(config):
    reporting = config["reporting"]
    for key in ["output_dir", "figures_dir", "tables_dir", "gifs_dir", "logs_dir"]:
        Path(reporting[key]).mkdir(parents=True, exist_ok=True)


def command_record(name, command, **metadata):
    return {
        "name": name,
        "command": command,
        "command_text": " ".join(str(item) for item in command),
        **metadata,
    }


def parse_devices(args):
    if args.devices:
        devices = [item.strip() for item in args.devices.split(",") if item.strip()]
        if devices:
            return devices
    return [args.device]


def parse_algorithm_names(config, args):
    if args.algorithms:
        return [item.strip() for item in args.algorithms.split(",") if item.strip()]
    names = []
    for item in config.get("algorithms", []):
        policy = item.get("policy") or item.get("model_path")
        if policy:
            names.append(item["name"])
    return names


def case_complete(out_dir, num_agents, seed, algorithms):
    summaries = Path(out_dir) / "summaries"
    if not algorithms:
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


def build_commands(config, args):
    python = config["python"]
    output_dir = Path(config["reporting"]["output_dir"]) / args.matrix_name
    max_neighbors = config["dynamic_graph"].get("max_neighbors")
    max_neighbors_arg = "0" if max_neighbors is None else str(max_neighbors)
    devices = parse_devices(args)
    algorithms = parse_algorithm_names(config, args)
    commands = []
    count = 0
    kept = 0
    for benchmark in config["benchmark_matrix"]:
        track = benchmark["track"]
        track_path = "" if track == "procedural" else track
        for num_agents in benchmark["agent_counts"]:
            for seed in benchmark["seeds"]:
                count += 1
                if args.case_start is not None and count < args.case_start:
                    continue
                if args.case_end is not None and count > args.case_end:
                    continue
                out_dir = output_dir / benchmark["name"] / f"n{num_agents}" / f"seed{seed}"
                if args.skip_existing and case_complete(out_dir, num_agents, seed, algorithms):
                    continue
                kept += 1
                if args.max_cases is not None and kept > args.max_cases:
                    return commands
                command = [
                    python,
                    "scripts/run_tits_dynamic_graph_evaluation.py",
                    "--config",
                    args.config,
                    "--out-dir",
                    str(out_dir),
                    "--num-agents",
                    str(num_agents),
                    "--seed",
                    str(seed),
                    "--max-steps",
                    str(args.max_steps),
                    "--finish-mode",
                    args.finish_mode,
                    "--observation-type",
                    args.observation_type,
                    "--max-neighbors",
                    max_neighbors_arg,
                    "--device",
                    devices[(count - 1) % len(devices)],
                    "--traffic-profile",
                    args.traffic_profile,
                    "--frame-every",
                    str(args.frame_every),
                    "--fps",
                    str(args.fps),
                ]
                if args.telemetry_version == "corrected_v2":
                    command.extend(["--telemetry-version", "corrected_v2"])
                if args.legacy_checkpoint_migration:
                    command.append("--legacy-checkpoint-migration")
                if track_path:
                    command.extend(["--track-path", track_path])
                if args.algorithms:
                    command.extend(["--algorithms", args.algorithms])
                if args.no_gif:
                    command.append("--no-gif")
                if args.first_person_gif:
                    command.append("--first-person-gif")
                commands.append(
                    command_record(
                        f"{benchmark['name']}_n{num_agents}_seed{seed}",
                        command,
                        case_index=count,
                        benchmark=benchmark["name"],
                        track=track,
                        num_agents=int(num_agents),
                        seed=int(seed),
                        device=devices[(count - 1) % len(devices)],
                        out_dir=str(out_dir),
                    )
                )
    return commands


def run_command(record, log_dir):
    log_path = Path(log_dir) / f"online_{record['name']}.log"
    started = time.time()
    with log_path.open("w", encoding="utf-8") as handle:
        process = subprocess.run(record["command"], stdout=handle, stderr=subprocess.STDOUT, check=False)
    ended = time.time()
    result = dict(record)
    result["returncode"] = int(process.returncode)
    result["log_path"] = str(log_path)
    result["started_at_unix"] = started
    result["ended_at_unix"] = ended
    result["elapsed_sec"] = ended - started
    return result


def write_results_csv(results, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "name",
        "case_index",
        "benchmark",
        "track",
        "num_agents",
        "seed",
        "device",
        "returncode",
        "elapsed_sec",
        "log_path",
        "out_dir",
        "command_text",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in results:
            writer.writerow({field: row.get(field, "") for field in fields})


def append_results_csv(results, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "name",
        "case_index",
        "benchmark",
        "track",
        "num_agents",
        "seed",
        "device",
        "returncode",
        "elapsed_sec",
        "log_path",
        "out_dir",
        "command_text",
    ]
    existing_keys = set()
    if path.exists():
        with path.open("r", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                existing_keys.add((row.get("name"), row.get("case_index"), row.get("command_text")))
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        if path.stat().st_size == 0:
            writer.writeheader()
        for row in results:
            key = (str(row.get("name", "")), str(row.get("case_index", "")), str(row.get("command_text", "")))
            if key in existing_keys:
                continue
            writer.writerow({field: row.get(field, "") for field in fields})
            existing_keys.add(key)


def main():
    parser = argparse.ArgumentParser(description="Run the online dynamic graph overtake benchmark matrix.")
    parser.add_argument("--config", default="configs/tits_dynamic_graph_experiments.json")
    parser.add_argument("--mode", choices=["dry-run", "run"], default="dry-run")
    parser.add_argument("--algorithms", default="")
    parser.add_argument("--matrix-name", default="online_evaluation_matrix", help="Subdirectory under reporting.output_dir for this benchmark run.")
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--devices", default="", help="Comma-separated devices for round-robin assignment, e.g. cuda:0,cuda:1,cuda:2,cuda:3.")
    parser.add_argument("--jobs", type=int, default=1, help="Number of online evaluation cases to run concurrently.")
    parser.add_argument("--max-steps", type=int, default=2200)
    parser.add_argument("--finish-mode", choices=["any", "target", "all", "env_done", "steps"], default="any")
    parser.add_argument("--observation-type", choices=["telemetry", "telemetry_dynamic"], default="telemetry_dynamic")
    parser.add_argument("--telemetry-version", choices=["legacy_v1", "corrected_v2"], default="legacy_v1")
    parser.add_argument("--legacy-checkpoint-migration", action="store_true")
    parser.add_argument("--traffic-profile", choices=["slow_traffic", "mixed_traffic"], default="slow_traffic")
    parser.add_argument("--max-cases", type=int, default=None)
    parser.add_argument("--case-start", type=int, default=None, help="1-based inclusive case index from the configured benchmark matrix.")
    parser.add_argument("--case-end", type=int, default=None, help="1-based inclusive case index from the configured benchmark matrix.")
    parser.add_argument("--skip-existing", action="store_true", help="Skip cases whose expected algorithm summary JSON files already exist and parse.")
    parser.add_argument("--no-gif", action="store_true")
    parser.add_argument("--first-person-gif", action="store_true")
    parser.add_argument("--frame-every", type=int, default=12)
    parser.add_argument("--fps", type=int, default=12)
    args = parser.parse_args()

    config = load_config(args.config)
    ensure_dirs(config)
    commands = build_commands(config, args)
    matrix_log_dir = Path(config["reporting"]["logs_dir"]) / args.matrix_name
    matrix_log_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "config": args.config,
        "mode": args.mode,
        "args": vars(args),
        "devices": parse_devices(args),
        "jobs": int(args.jobs),
        "commands": commands,
        "results": [],
    }
    log_dir = matrix_log_dir
    if args.mode == "run":
        workers = max(1, int(args.jobs))
        if workers == 1:
            for record in commands:
                print(f"running {record['name']}")
                summary["results"].append(run_command(record, log_dir))
        else:
            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
                future_to_record = {
                    executor.submit(run_command, record, log_dir): record
                    for record in commands
                }
                for future in concurrent.futures.as_completed(future_to_record):
                    record = future_to_record[future]
                    print(f"finished {record['name']}")
                    summary["results"].append(future.result())
            summary["results"].sort(key=lambda row: row["name"])

    suffix = "dry_run" if args.mode == "dry-run" else "run"
    batch_id = time.strftime("%Y%m%d_%H%M%S")
    summary_path = Path(config["reporting"]["output_dir"]) / f"{args.matrix_name}_{suffix}_summary.json"
    batch_summary_path = Path(config["reporting"]["output_dir"]) / f"{args.matrix_name}_{suffix}_summary_{batch_id}.json"
    if summary["results"]:
        batch_results_csv = Path(config["reporting"]["output_dir"]) / f"{args.matrix_name}_{suffix}_results_{batch_id}.csv"
        ledger_csv = Path(config["reporting"]["output_dir"]) / f"{args.matrix_name}_{suffix}_results_ledger.csv"
        write_results_csv(summary["results"], batch_results_csv)
        append_results_csv(summary["results"], ledger_csv)
        summary["batch_id"] = batch_id
        summary["batch_results_csv"] = str(batch_results_csv)
        summary["results_ledger_csv"] = str(ledger_csv)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    batch_summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"summary": str(summary_path), "commands": len(commands)}, ensure_ascii=False, indent=2))

    failed = [row for row in summary["results"] if row.get("returncode", 0) != 0]
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
