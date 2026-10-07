#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import concurrent.futures
import json
import subprocess
from pathlib import Path


def load_config(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def parse_devices(value, fallback):
    devices = [item.strip() for item in value.split(",") if item.strip()]
    return devices or [fallback]


def algorithm_names(config):
    return [row["name"] for row in config["algorithms"]]


def expected_cases(config):
    cases = {}
    for benchmark in config["benchmark_matrix"]:
        track = "" if benchmark["track"] == "procedural" else benchmark["track"]
        for num_agents in benchmark["agent_counts"]:
            for seed in benchmark["seeds"]:
                key = f"{benchmark['name']}/n{num_agents}/seed{seed}"
                cases[key] = {
                    "benchmark": benchmark["name"],
                    "num_agents": int(num_agents),
                    "seed": int(seed),
                    "track_path": track,
                }
    return cases


def observed_algorithms(root, algos):
    root = Path(root)
    observed = {}
    for path in root.rglob("*.summary.json"):
        rel = path.relative_to(root)
        if len(rel.parts) < 3:
            continue
        case = "/".join(rel.parts[:-2])
        for algo in algos:
            if path.name.startswith(algo + "_"):
                observed.setdefault(case, set()).add(algo)
                break
    return observed


def command_record(name, command):
    return {
        "name": name,
        "command": command,
        "command_text": " ".join(str(item) for item in command),
    }


def build_commands(config, args):
    algos = algorithm_names(config)
    cases = expected_cases(config)
    observed = observed_algorithms(args.input_dir, algos)
    devices = parse_devices(args.devices, args.device)
    commands = []
    python = config["python"]
    output_root = Path(args.input_dir)
    max_neighbors = config["dynamic_graph"]["max_neighbors"]
    for idx, (case, meta) in enumerate(sorted(cases.items())):
        missing = [algo for algo in algos if algo not in observed.get(case, set())]
        if not missing:
            continue
        command = [
            python,
            "scripts/run_tits_dynamic_graph_evaluation.py",
            "--config",
            args.config,
            "--out-dir",
            str(output_root / case),
            "--num-agents",
            str(meta["num_agents"]),
            "--seed",
            str(meta["seed"]),
            "--max-steps",
            str(args.max_steps),
            "--finish-mode",
            args.finish_mode,
            "--observation-type",
            "telemetry_dynamic",
            "--max-neighbors",
            str(max_neighbors),
            "--device",
            devices[idx % len(devices)],
            "--traffic-profile",
            args.traffic_profile,
            "--frame-every",
            str(args.frame_every),
            "--fps",
            str(args.fps),
            "--algorithms",
            ",".join(missing),
        ]
        if meta["track_path"]:
            command.extend(["--track-path", meta["track_path"]])
        if args.no_gif:
            command.append("--no-gif")
        commands.append(command_record(case.replace("/", "_"), command))
    return commands


def run_command(record, log_dir):
    log_path = Path(log_dir) / f"repair_{record['name']}.log"
    with log_path.open("w", encoding="utf-8") as handle:
        process = subprocess.run(record["command"], stdout=handle, stderr=subprocess.STDOUT, check=False)
    result = dict(record)
    result["returncode"] = int(process.returncode)
    result["log_path"] = str(log_path)
    return result


def main():
    parser = argparse.ArgumentParser(description="Repair missing online benchmark case/algorithm outputs.")
    parser.add_argument("--config", default="configs/tits_dynamic_graph_experiments.json")
    parser.add_argument("--input-dir", default="outputs/tits_dynamic_graph/online_evaluation_matrix")
    parser.add_argument("--mode", choices=["dry-run", "run"], default="dry-run")
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--devices", default="cuda:0,cuda:1,cuda:2,cuda:3")
    parser.add_argument("--jobs", type=int, default=8)
    parser.add_argument("--max-steps", type=int, default=2200)
    parser.add_argument("--finish-mode", choices=["any", "target", "all", "env_done", "steps"], default="any")
    parser.add_argument("--traffic-profile", choices=["slow_traffic", "mixed_traffic"], default="slow_traffic")
    parser.add_argument("--no-gif", action="store_true")
    parser.add_argument("--frame-every", type=int, default=12)
    parser.add_argument("--fps", type=int, default=12)
    args = parser.parse_args()

    config = load_config(args.config)
    commands = build_commands(config, args)
    log_dir = Path(config["reporting"]["logs_dir"])
    log_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "config": args.config,
        "input_dir": args.input_dir,
        "mode": args.mode,
        "args": vars(args),
        "commands": commands,
        "results": [],
    }
    if args.mode == "run":
        with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, int(args.jobs))) as executor:
            future_to_record = {
                executor.submit(run_command, record, log_dir): record
                for record in commands
            }
            for future in concurrent.futures.as_completed(future_to_record):
                record = future_to_record[future]
                print(f"finished repair {record['name']}")
                summary["results"].append(future.result())
        summary["results"].sort(key=lambda row: row["name"])

    out_path = Path(config["reporting"]["output_dir"]) / "online_repair_summary.json"
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"summary": str(out_path), "commands": len(commands)}, ensure_ascii=False, indent=2))
    failed = [row for row in summary["results"] if row.get("returncode", 0) != 0]
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
