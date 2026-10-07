#!/usr/bin/env python
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import subprocess
from pathlib import Path


def run_command(cmd):
    print("+ " + " ".join(str(part) for part in cmd), flush=True)
    completed = subprocess.run(
        cmd,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return completed.returncode, completed.stdout


def has_model_set(model_dir):
    model_dir = Path(model_dir)
    return all(
        (model_dir / f"{name}.pt").exists()
        for name in [
            "individual_transition",
            "joint_transition",
            "joint_transition_observer",
        ]
    )


def parse_devices(devices):
    values = [item.strip() for item in devices.split(",") if item.strip()]
    return values or ["cuda:0"]


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def seed_model_dirs(root_dir, seeds):
    root_dir = Path(root_dir)
    if seeds:
        seed_values = [int(item.strip()) for item in seeds.split(",") if item.strip()]
        return [(seed, root_dir / f"seed_{seed}" / "models") for seed in seed_values]

    dirs = []
    for path in sorted(root_dir.glob("seed_*/models")):
        try:
            seed = int(path.parent.name.split("_", 1)[1])
        except (IndexError, ValueError):
            continue
        dirs.append((seed, path))
    return dirs


def run_seed(args, seed, model_dir, device):
    out_dir = Path(args.out_dir) / f"seed_{seed}"
    out_dir.mkdir(parents=True, exist_ok=True)
    search_json = out_dir / "overtake_behavior_search.json"
    validation_json = out_dir / "overtake_validation.json"

    search_cmd = [
        args.python,
        "scripts/search_overtake_behavior.py",
        "--model-dir",
        str(model_dir),
        "--seeds",
        args.search_seeds,
        "--observer-agents",
        args.observer_agents,
        "--blends",
        args.blends,
        "--steps",
        str(args.steps),
        "--device",
        device,
        "--workers",
        str(args.search_workers),
        "--out",
        str(search_json),
    ]
    code, search_output = run_command(search_cmd)
    if code != 0:
        return {
            "seed": seed,
            "model_dir": str(model_dir),
            "device": device,
            "status": "SEARCH_FAIL",
            "search_json": str(search_json),
            "validation_json": str(validation_json),
            "log_tail": search_output[-4000:],
        }

    validate_cmd = [
        args.python,
        "scripts/validate_overtake_behavior.py",
        str(search_json),
        "--max-observer-grass-rate",
        str(args.max_observer_grass_rate),
        "--min-tile-advantage",
        str(args.min_tile_advantage),
        "--min-reward-advantage",
        str(args.min_reward_advantage),
        "--min-final-progress",
        str(args.min_final_progress),
        "--top-k",
        str(args.top_k),
        "--out",
        str(validation_json),
    ]
    code, validation_output = run_command(validate_cmd)
    validation = load_json(validation_json) if validation_json.exists() else None
    return {
        "seed": seed,
        "model_dir": str(model_dir),
        "device": device,
        "status": validation["status"] if validation else "VALIDATION_FAIL",
        "search_json": str(search_json),
        "validation_json": str(validation_json),
        "best_passing": validation.get("best_passing") if validation else None,
        "validation_log_tail": validation_output[-4000:],
        "returncode": code,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Run visible overtake search and validation for every trained seed."
    )
    parser.add_argument("--experiment-dir", default="outputs/torch_dlc_shaped_multiseed")
    parser.add_argument("--seeds", default="")
    parser.add_argument("--out-dir", default="")
    parser.add_argument("--devices", default="cuda:0")
    parser.add_argument("--parallel-seeds", type=int, default=1)
    parser.add_argument("--search-workers", type=int, default=1)
    parser.add_argument("--search-seeds", default="1,2,3,4,5,7,9,11,13,15,21,34,42,55,88,115")
    parser.add_argument("--observer-agents", default="0,1")
    parser.add_argument(
        "--blends",
        default="0.55:0.95,0.70:0.98,0.82:0.99,0.88:0.995,0.92:0.998,0.96:0.999,0.98:1.0",
    )
    parser.add_argument("--steps", type=int, default=600)
    parser.add_argument("--max-observer-grass-rate", type=float, default=0.20)
    parser.add_argument("--min-tile-advantage", type=int, default=8)
    parser.add_argument("--min-reward-advantage", type=float, default=40.0)
    parser.add_argument("--min-final-progress", type=float, default=0.03)
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--python", default="python")
    args = parser.parse_args()

    experiment_dir = Path(args.experiment_dir)
    out_dir = Path(args.out_dir) if args.out_dir else experiment_dir / "overtake_search"
    args.out_dir = str(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    model_dirs = [
        (seed, model_dir)
        for seed, model_dir in seed_model_dirs(experiment_dir, args.seeds)
        if has_model_set(model_dir)
    ]
    devices = parse_devices(args.devices)
    jobs = [
        {
            "seed": seed,
            "model_dir": model_dir,
            "device": devices[index % len(devices)],
        }
        for index, (seed, model_dir) in enumerate(model_dirs)
    ]

    results = []
    workers = max(1, min(args.parallel_seeds, len(jobs))) if jobs else 1
    if workers == 1:
        for job in jobs:
            results.append(run_seed(args, job["seed"], job["model_dir"], job["device"]))
    else:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(run_seed, args, job["seed"], job["model_dir"], job["device"]): job
                for job in jobs
            }
            for future in as_completed(futures):
                results.append(future.result())

    results.sort(key=lambda item: item["seed"])
    pass_count = sum(1 for item in results if item["status"] == "PASS")
    summary = {
        "status": "PASS" if results and pass_count == len(results) else "FAIL",
        "experiment_dir": str(experiment_dir),
        "out_dir": str(out_dir),
        "seed_count": len(results),
        "pass_count": pass_count,
        "pass_rate": pass_count / len(results) if results else 0.0,
        "thresholds": {
            "max_observer_grass_rate": args.max_observer_grass_rate,
            "min_tile_advantage": args.min_tile_advantage,
            "min_reward_advantage": args.min_reward_advantage,
            "min_final_progress": args.min_final_progress,
            "top_k": args.top_k,
        },
        "results": results,
    }
    summary_path = out_dir / "batch_overtake_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    raise SystemExit(0 if summary["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
