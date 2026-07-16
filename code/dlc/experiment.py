import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import subprocess
from pathlib import Path

import numpy as np


PAIRINGS = [
    "individual_transition_vs_joint_transition",
    "individual_transition_vs_joint_transition_observer",
    "joint_transition_vs_joint_transition_observer",
]


def run_command(cmd):
    print("+ " + " ".join(str(part) for part in cmd), flush=True)
    subprocess.run(cmd, check=True)


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


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


def parse_devices(device, devices):
    if devices:
        return [item.strip() for item in devices.split(",") if item.strip()]
    return [device]


def train_command(args, seed, model_dir, device):
    cmd = [
        args.python,
        "-u",
        "-m",
        "dlc.train_torch_dlc",
        "--episodes",
        str(args.episodes),
        "--max-steps",
        str(args.max_steps),
        "--train-steps",
        str(args.train_steps),
        "--eval-at-steps",
        args.eval_at_steps,
        "--batch-size",
        str(args.batch_size),
        "--imagination-horizon",
        str(args.imagination_horizon),
        "--hidden-dim",
        str(args.hidden_dim),
        "--collect-workers",
        str(args.collect_workers),
        "--behavior-policy",
        args.behavior_policy,
        "--device",
        device,
        "--seed",
        str(seed),
        "--out-dir",
        str(model_dir),
    ]
    optional_args = {
        "--behavior-clone-weight": args.behavior_clone_weight,
        "--safety-weight": args.safety_weight,
        "--grass-penalty": args.grass_penalty,
        "--backward-penalty": args.backward_penalty,
        "--lateral-penalty": args.lateral_penalty,
        "--progress-delta-weight": args.progress_delta_weight,
        "--tile-progress-weight": args.tile_progress_weight,
        "--lap-completion-bonus": args.lap_completion_bonus,
        "--model-lr": args.model_lr,
        "--value-lr": args.value_lr,
        "--actor-lr": args.actor_lr,
        "--discount": args.discount,
        "--lambda": args.lambda_,
        "--actor-every": args.actor_every,
    }
    for name, value in optional_args.items():
        cmd.extend([name, str(value)])
    return cmd


def run_training_jobs(train_jobs, workers, devices):
    if not train_jobs:
        return
    workers = max(1, min(workers, len(train_jobs)))
    if workers == 1:
        for job in train_jobs:
            run_command(job["cmd"])
        return

    print(
        f"training {len(train_jobs)} seeds with {workers} workers on devices {devices}",
        flush=True,
    )
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(run_command, job["cmd"]): job
            for job in train_jobs
        }
        for future in as_completed(futures):
            job = futures[future]
            try:
                future.result()
            except Exception as exc:
                raise RuntimeError(
                    f"training failed for seed {job['seed']} on {job['device']}"
                ) from exc


def round_robin_command(args, stage_model_dir, seed, round_robin_path, device):
    return [
        args.python,
        "-u",
        "-m",
        "dlc.round_robin",
        "--model-dir",
        str(stage_model_dir),
        "--episodes",
        str(args.eval_episodes),
        "--max-steps",
        str(args.eval_max_steps),
        "--seed",
        str(seed),
        "--device",
        device,
        "--out",
        str(round_robin_path),
    ]


def run_round_robin_jobs(jobs, workers):
    if not jobs:
        return
    workers = max(1, min(workers, len(jobs)))
    if workers == 1:
        for job in jobs:
            run_command(job["cmd"])
        return

    print(f"running {len(jobs)} round-robins with {workers} workers", flush=True)
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(run_command, job["cmd"]): job
            for job in jobs
        }
        for future in as_completed(futures):
            job = futures[future]
            try:
                future.result()
            except Exception as exc:
                raise RuntimeError(
                    f"round-robin failed for seed {job['seed']} stage {job['stage']}"
                ) from exc


def aggregate_round_robins(round_robin_paths):
    per_pair = {pairing: {"win_ratio": [], "mean_score": []} for pairing in PAIRINGS}
    for path in round_robin_paths:
        result = load_json(path)
        for pairing in PAIRINGS:
            pair_result = result["pairings"][pairing]
            per_pair[pairing]["win_ratio"].append(pair_result["win_ratio"])
            per_pair[pairing]["mean_score"].append(pair_result["mean_score"])

    summary = {}
    for pairing, metrics in per_pair.items():
        win_ratio = np.asarray(metrics["win_ratio"], dtype=np.float64)
        mean_score = np.asarray(metrics["mean_score"], dtype=np.float64)
        summary[pairing] = {
            "win_ratio_mean": win_ratio.mean(axis=0).tolist(),
            "win_ratio_std": win_ratio.std(axis=0).tolist(),
            "mean_score_mean": mean_score.mean(axis=0).tolist(),
            "mean_score_std": mean_score.std(axis=0).tolist(),
        }
    return summary


def main():
    parser = argparse.ArgumentParser(
        description="Run multi-seed telemetry-state DLC training and round-robin evaluation."
    )
    parser.add_argument("--seeds", default="0,1,2,3,4")
    parser.add_argument("--out-dir", default="outputs/torch_dlc_experiment")
    parser.add_argument("--episodes", type=int, default=500)
    parser.add_argument("--max-steps", type=int, default=1000)
    parser.add_argument("--train-steps", type=int, default=200)
    parser.add_argument("--eval-at-steps", default="")
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--imagination-horizon", type=int, default=15)
    parser.add_argument("--hidden-dim", type=int, default=256)
    parser.add_argument("--collect-workers", type=int, default=1)
    parser.add_argument("--eval-episodes", type=int, default=100)
    parser.add_argument("--eval-max-steps", type=int, default=1000)
    parser.add_argument("--behavior-policy", default="track_follow")
    parser.add_argument("--behavior-clone-weight", type=float, default=0.0)
    parser.add_argument("--safety-weight", type=float, default=0.0)
    parser.add_argument("--grass-penalty", type=float, default=0.0)
    parser.add_argument("--backward-penalty", type=float, default=0.0)
    parser.add_argument("--lateral-penalty", type=float, default=0.0)
    parser.add_argument("--progress-delta-weight", type=float, default=0.0)
    parser.add_argument("--tile-progress-weight", type=float, default=0.0)
    parser.add_argument("--lap-completion-bonus", type=float, default=0.0)
    parser.add_argument("--model-lr", type=float, default=6e-4)
    parser.add_argument("--value-lr", type=float, default=6e-4)
    parser.add_argument("--actor-lr", type=float, default=8e-5)
    parser.add_argument("--discount", type=float, default=0.99)
    parser.add_argument("--lambda", dest="lambda_", type=float, default=0.95)
    parser.add_argument("--actor-every", type=int, default=1)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--devices", default="")
    parser.add_argument("--parallel-seeds", type=int, default=1)
    parser.add_argument("--parallel-evals", type=int, default=1)
    parser.add_argument("--eval-device", default="")
    parser.add_argument("--python", default="python")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    seeds = [int(seed.strip()) for seed in args.seeds.split(",") if seed.strip()]
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    eval_at_steps = [
        int(step.strip())
        for step in args.eval_at_steps.split(",")
        if step.strip()
    ]
    stage_names = [f"step_{step}" for step in eval_at_steps if 0 < step <= args.train_steps]
    stage_names.append("final")
    round_robin_paths_by_stage = {stage_name: [] for stage_name in stage_names}
    devices = parse_devices(args.device, args.devices)
    train_jobs = []

    for seed in seeds:
        seed_dir = out_dir / f"seed_{seed}"
        model_dir = seed_dir / "models"
        required_model_dirs = [
            model_dir if stage_name == "final" else model_dir / stage_name
            for stage_name in stage_names
        ]
        train_done = all(has_model_set(path) for path in required_model_dirs)
        if not (args.resume and train_done):
            device = devices[len(train_jobs) % len(devices)]
            train_jobs.append(
                {
                    "seed": seed,
                    "device": device,
                    "cmd": train_command(args, seed, model_dir, device),
                }
            )

    run_training_jobs(train_jobs, args.parallel_seeds, devices)

    round_robin_jobs = []
    for seed in seeds:
        seed_dir = out_dir / f"seed_{seed}"
        model_dir = seed_dir / "models"
        for stage_name in stage_names:
            stage_model_dir = model_dir if stage_name == "final" else model_dir / stage_name
            round_robin_path = seed_dir / f"round_robin_{stage_name}.json"
            if not (args.resume and round_robin_path.exists()):
                round_robin_jobs.append(
                    {
                        "seed": seed,
                        "stage": stage_name,
                        "stage_model_dir": stage_model_dir,
                        "round_robin_path": round_robin_path,
                    }
                )
            round_robin_paths_by_stage[stage_name].append(round_robin_path)

    if args.eval_device:
        eval_devices = [args.eval_device]
    elif devices and devices[0] != "auto":
        eval_devices = devices
    else:
        eval_devices = ["cpu"]

    for index, job in enumerate(round_robin_jobs):
        job["cmd"] = round_robin_command(
            args,
            job["stage_model_dir"],
            job["seed"],
            job["round_robin_path"],
            eval_devices[index % len(eval_devices)],
        )

    run_round_robin_jobs(round_robin_jobs, args.parallel_evals)

    output = {
        "seeds": seeds,
        "train_episodes": args.episodes,
        "train_max_steps": args.max_steps,
        "train_steps": args.train_steps,
        "behavior_policy": args.behavior_policy,
        "behavior_clone_weight": args.behavior_clone_weight,
        "safety_weight": args.safety_weight,
        "grass_penalty": args.grass_penalty,
        "backward_penalty": args.backward_penalty,
        "lateral_penalty": args.lateral_penalty,
        "progress_delta_weight": args.progress_delta_weight,
        "tile_progress_weight": args.tile_progress_weight,
        "lap_completion_bonus": args.lap_completion_bonus,
        "eval_episodes": args.eval_episodes,
        "eval_max_steps": args.eval_max_steps,
        "eval_at_steps": eval_at_steps,
        "resume": args.resume,
        "round_robin_paths": {
            stage_name: [str(path) for path in paths]
            for stage_name, paths in round_robin_paths_by_stage.items()
        },
        "aggregate": {
            stage_name: aggregate_round_robins(paths)
            for stage_name, paths in round_robin_paths_by_stage.items()
        },
    }
    summary_path = out_dir / "aggregate_summary.json"
    summary_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
