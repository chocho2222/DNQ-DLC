#!/usr/bin/env python
import argparse
import concurrent.futures
import json
import subprocess
from pathlib import Path


def load_config(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def ensure_dirs(config):
    reporting = config["reporting"]
    for key in ["output_dir", "figures_dir", "tables_dir", "gifs_dir", "logs_dir"]:
        Path(reporting[key]).mkdir(parents=True, exist_ok=True)


def command_to_record(name, command):
    return {
        "name": name,
        "command": command,
        "command_text": " ".join(str(item) for item in command),
    }


def parse_devices(args):
    if args.devices:
        devices = [item.strip() for item in args.devices.split(",") if item.strip()]
        if devices:
            return devices
    return [args.device]


def set_command_device(command, device):
    command = list(command)
    for idx, item in enumerate(command):
        if item == "--device" and idx + 1 < len(command):
            command[idx + 1] = device
            return command
    command.extend(["--device", device])
    return command


def build_smoke_commands(config, args):
    python = config["python"]
    output_dir = Path(config["reporting"]["output_dir"]) / "smoke"
    max_neighbors = config["dynamic_graph"]["max_neighbors"]
    devices = parse_devices(args)
    commands = []
    for case_id, num_agents in enumerate(config["dynamic_graph"]["test_agent_counts"][: args.max_smoke_cases]):
        commands.append(
            command_to_record(
                f"dynamic_smoke_{num_agents}cars",
                [
                    python,
                    "scripts/run_innovation_smoke.py",
                    "--num-agents",
                    str(num_agents),
                    "--steps",
                    str(args.smoke_steps),
                    "--device",
                    devices[case_id % len(devices)],
                    "--out-dir",
                    str(output_dir / f"n{num_agents}"),
                ],
            )
        )
    return commands


def build_train_commands(config, args):
    python = config["python"]
    dg = config["dynamic_graph"]
    output_dir = Path(config["reporting"]["output_dir"]) / "models"
    commands = [
        command_to_record(
            "train_graph_bc_dynamic",
            [
                python,
                "scripts/train_graph_bc.py",
                "--min-agents",
                str(dg["train_agent_range"][0]),
                "--max-agents",
                str(dg["train_agent_range"][1]),
                "--episodes",
                str(args.bc_episodes),
                "--max-steps",
                str(args.max_steps),
                "--max-neighbors",
                str(dg["max_neighbors"]),
                "--neighbor-keep-prob",
                str(dg["neighbor_keep_prob"]),
                "--device",
                args.device,
                "--collection-workers",
                str(args.collection_workers),
                "--out-dir",
                str(output_dir / "graph_bc_dynamic"),
            ],
        ),
        command_to_record(
            "train_dynamic_graph_dlc_world",
            [
                python,
                "scripts/train_graph_risk_world_model.py",
                "--min-agents",
                str(dg["train_agent_range"][0]),
                "--max-agents",
                str(dg["train_agent_range"][1]),
                "--episodes",
                str(args.world_episodes),
                "--max-steps",
                str(args.max_steps),
                "--max-neighbors",
                str(dg["max_neighbors"]),
                "--neighbor-keep-prob",
                str(args.world_neighbor_keep_prob),
                "--device",
                args.device,
                "--collection-workers",
                str(args.collection_workers),
                "--out-dir",
                str(output_dir / "ours_dynamic_graph_dlc_world"),
            ],
        ),
    ]
    devices = parse_devices(args)
    for idx, record in enumerate(commands):
        record["command"] = set_command_device(record["command"], devices[idx % len(devices)])
        record["command_text"] = " ".join(str(item) for item in record["command"])
    return commands


def run_command(record, log_dir):
    log_path = Path(log_dir) / f"{record['name']}.log"
    with log_path.open("w", encoding="utf-8") as handle:
        process = subprocess.run(
            record["command"],
            stdout=handle,
            stderr=subprocess.STDOUT,
            check=False,
        )
    result = dict(record)
    result["returncode"] = int(process.returncode)
    result["log_path"] = str(log_path)
    return result


def run_commands(commands, log_dir, jobs):
    if jobs <= 1:
        return [run_command(record, log_dir) for record in commands]
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as executor:
        future_to_record = {
            executor.submit(run_command, record, log_dir): record
            for record in commands
        }
        for future in concurrent.futures.as_completed(future_to_record):
            results.append(future.result())
    results.sort(key=lambda row: row["name"])
    return results


def main():
    parser = argparse.ArgumentParser(description="Run the TITS dynamic graph experiment suite.")
    parser.add_argument("--config", default="configs/tits_dynamic_graph_experiments.json")
    parser.add_argument("--mode", default="dry-run", choices=["dry-run", "smoke", "train"])
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--devices", default="", help="Comma-separated devices for round-robin assignment, e.g. cuda:0,cuda:1,cuda:2,cuda:3.")
    parser.add_argument("--jobs", type=int, default=1, help="Number of suite commands to run concurrently.")
    parser.add_argument("--collection-workers", type=int, default=1, help="Per-training-process rollout workers for CPU-bound environment sampling.")
    parser.add_argument("--smoke-steps", type=int, default=12)
    parser.add_argument("--max-smoke-cases", type=int, default=4)
    parser.add_argument("--bc-episodes", type=int, default=24)
    parser.add_argument("--world-episodes", type=int, default=18)
    parser.add_argument("--max-steps", type=int, default=2200)
    parser.add_argument("--world-neighbor-keep-prob", type=float, default=0.9)
    args = parser.parse_args()

    config = load_config(args.config)
    ensure_dirs(config)
    log_dir = Path(config["reporting"]["logs_dir"])

    commands = []
    if args.mode in {"dry-run", "smoke"}:
        commands.extend(build_smoke_commands(config, args))
    if args.mode in {"dry-run", "train"}:
        commands.extend(build_train_commands(config, args))

    summary = {
        "config": args.config,
        "mode": args.mode,
        "devices": parse_devices(args),
        "jobs": int(args.jobs),
        "commands": commands,
        "results": [],
    }
    if args.mode != "dry-run":
        summary["results"] = run_commands(commands, log_dir, max(1, int(args.jobs)))

    summary_path = Path(config["reporting"]["output_dir"]) / f"{args.mode}_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))

    failed = [row for row in summary["results"] if row.get("returncode", 0) != 0]
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
