#!/usr/bin/env python
import argparse
import json
import subprocess
import sys
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def run_command(cmd):
    print("+ " + " ".join(str(part) for part in cmd), flush=True)
    subprocess.run(cmd, check=True)


def build_demo_command(args, config, out_dir):
    cmd = [
        sys.executable,
        "scripts/generate_multicar_overtake_gif.py",
        "--model-dir",
        args.model_dir,
        "--target-policy",
        args.target_policy,
        "--num-agents",
        str(config["num_agents"]),
        "--seed",
        str(args.seed),
        "--gap-tiles",
        str(config["gap_tiles"]),
        "--lateral-spacing",
        str(config["lateral_spacing"]),
        "--steps",
        str(config["steps"]),
        "--frame-every",
        str(args.frame_every),
        "--fps",
        str(args.fps),
        "--device",
        args.device,
        "--target-safe-base",
        config["target_safe_base"],
        "--target-base-speed",
        str(config["target_base_speed"]),
        "--baseline-policies",
        config["baseline_policies"],
        "--stop-when-target-completes",
        "--out-dir",
        str(out_dir),
    ]
    if config.get("single_file_start", False):
        cmd.append("--single-file-start")
    if config.get("safe", False):
        cmd.extend(
            [
                "--safe",
                "--safe-blend",
                str(config["safe_blend"]),
                "--unsafe-blend",
                str(config["unsafe_blend"]),
            ]
        )
    return cmd


def expected_summary_path(out_dir, config, target_policy, seed):
    stem = (
        f"multicar_{config['num_agents']}_target_{target_policy}"
        f"_seed{seed}_gap{config['gap_tiles']}"
    )
    return out_dir / f"{stem}.json"


def validate_summary(summary_path, args):
    cmd = [
        sys.executable,
        "scripts/validate_multicar_lap.py",
        str(summary_path),
        "--max-target-grass-rate",
        str(args.max_target_grass_rate),
        "--max-any-grass-rate",
        str(args.max_any_grass_rate),
        "--require-target-complete",
        "--require-target-first",
        "--require-first-ahead",
    ]
    result = subprocess.run(cmd, text=True, capture_output=True)
    validation = json.loads(result.stdout)
    validation["returncode"] = result.returncode
    return validation


def main():
    parser = argparse.ArgumentParser(description="Run saved multi-car baseline suites.")
    parser.add_argument("--config-dir", default="baselines")
    parser.add_argument("--model-dir", default="outputs/torch_dlc_full_lap_seed01/seed_1/models")
    parser.add_argument("--target-policy", default="joint_transition_observer")
    parser.add_argument("--seed", type=int, default=3)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--frame-every", type=int, default=10)
    parser.add_argument("--fps", type=int, default=12)
    parser.add_argument("--out-dir", default="outputs/baseline_suite")
    parser.add_argument("--max-target-grass-rate", type=float, default=0.05)
    parser.add_argument("--max-any-grass-rate", type=float, default=0.35)
    parser.add_argument("--only", default="")
    parser.add_argument("--skip-existing", action="store_true")
    args = parser.parse_args()

    config_dir = Path(args.config_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    selected = {item.strip() for item in args.only.split(",") if item.strip()}
    configs = []
    for path in sorted(config_dir.glob("*.json")):
        config = load_json(path)
        if selected and config["name"] not in selected:
            continue
        configs.append((path, config))
    if not configs:
        raise ValueError(f"no baseline configs found in {config_dir}")

    rows = []
    for path, config in configs:
        baseline_out = out_dir / config["name"]
        baseline_out.mkdir(parents=True, exist_ok=True)
        summary_path = expected_summary_path(
            baseline_out,
            config,
            args.target_policy,
            args.seed,
        )
        if not (args.skip_existing and summary_path.exists()):
            run_command(build_demo_command(args, config, baseline_out))
        validation = validate_summary(summary_path, args)
        summary = load_json(summary_path)
        rows.append(
            {
                "name": config["name"],
                "config": str(path),
                "summary": str(summary_path),
                "gif": summary["gif"],
                "validation_status": validation["status"],
                "target_completed_lap": summary["target_completed_lap"],
                "target_final_rank_by_tiles": summary["target_final_rank_by_tiles"],
                "target_grass_rate": summary["grass_rate"][summary["target_agent"]],
                "max_grass_rate": max(summary["grass_rate"]),
                "tile_visited_count": summary["tile_visited_count"],
                "steps_run": summary["steps_run"],
            }
        )

    output = {
        "model_dir": args.model_dir,
        "target_policy": args.target_policy,
        "seed": args.seed,
        "rows": rows,
    }
    (out_dir / "baseline_suite_summary.json").write_text(
        json.dumps(output, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
