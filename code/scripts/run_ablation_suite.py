#!/usr/bin/env python
import argparse
import json
import subprocess
import sys
from pathlib import Path


ABLATIONS = [
    {
        "name": "graph_lane_shield",
        "safe": True,
        "safe_blend": 0.25,
        "unsafe_blend": 1.0,
        "target_safe_base": "telemetry_lane",
        "target_base_speed": 22.0,
        "hard_shield": True,
    },
    {
        "name": "graph_overtake_shield",
        "safe": True,
        "safe_blend": 0.25,
        "unsafe_blend": 1.0,
        "target_safe_base": "telemetry_overtake",
        "target_base_speed": 22.0,
        "hard_shield": True,
    },
    {
        "name": "graph_soft_lane_shield",
        "safe": True,
        "safe_blend": 0.25,
        "unsafe_blend": 1.0,
        "target_safe_base": "telemetry_lane",
        "target_base_speed": 22.0,
        "hard_shield": False,
    },
    {
        "name": "lane_base_only",
        "safe": True,
        "safe_blend": 1.0,
        "unsafe_blend": 1.0,
        "target_safe_base": "telemetry_lane",
        "target_base_speed": 22.0,
        "hard_shield": True,
    },
    {
        "name": "overtake_base_only",
        "safe": True,
        "safe_blend": 1.0,
        "unsafe_blend": 1.0,
        "target_safe_base": "telemetry_overtake",
        "target_base_speed": 22.0,
        "hard_shield": True,
    },
    {
        "name": "graph_no_shield",
        "safe": False,
        "safe_blend": 0.0,
        "unsafe_blend": 0.0,
        "target_safe_base": "telemetry_lane",
        "target_base_speed": 22.0,
        "hard_shield": False,
    },
]


def run_command(cmd):
    print("+ " + " ".join(str(part) for part in cmd), flush=True)
    subprocess.run(cmd, check=True)


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def summary_path(out_dir, seed):
    return out_dir / f"multicar_4_target_graph_bc.graph_seed{seed}_gap22.json"


def validate(path, root, name, seed):
    out = root / f"{name}_seed{seed}_validation.json"
    cmd = [
        sys.executable,
        "scripts/validate_multicar_lap.py",
        str(path),
        "--max-target-grass-rate",
        "0.08",
        "--max-any-grass-rate",
        "0.40",
        "--min-mean-tile-progress",
        "0.60",
        "--min-first-ahead-step",
        "10",
        "--require-target-complete",
        "--require-target-first",
        "--require-first-ahead",
        "--out",
        str(out),
    ]
    result = subprocess.run(cmd, text=True, capture_output=True)
    return json.loads(result.stdout)


def main():
    parser = argparse.ArgumentParser(description="Run safety/graph ablations.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    parser.add_argument("--model-path", default="outputs/paper_multicar_overtake_20260618/models/graph_bc/graph_bc.graph.pt")
    parser.add_argument("--baseline-model-dir", default="outputs/torch_dlc_full_lap_seed01/seed_1/models")
    parser.add_argument("--seeds", default="7")
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--steps", type=int, default=3200)
    parser.add_argument("--skip-existing", action="store_true")
    args = parser.parse_args()
    root = Path(args.root) / "ablations"
    root.mkdir(parents=True, exist_ok=True)
    seeds = [int(item) for item in args.seeds.split(",") if item.strip()]
    rows = []
    for ablation in ABLATIONS:
        for seed in seeds:
            out_dir = root / ablation["name"] / f"seed_{seed}"
            out_dir.mkdir(parents=True, exist_ok=True)
            path = summary_path(out_dir, seed)
            if not (args.skip_existing and path.exists()):
                cmd = [
                    sys.executable,
                    "scripts/generate_multicar_overtake_gif.py",
                    "--target-policy-path",
                    args.model_path,
                    "--model-dir",
                    args.baseline_model_dir,
                    "--num-agents",
                    "4",
                    "--seed",
                    str(seed),
                    "--gap-tiles",
                    "22",
                    "--lateral-spacing",
                    "0.0",
                    "--single-file-start",
                    "--steps",
                    str(args.steps),
                    "--frame-every",
                    "20",
                    "--fps",
                    "12",
                    "--device",
                    args.device,
                    "--target-safe-base",
                    ablation["target_safe_base"],
                    "--target-base-speed",
                    str(ablation["target_base_speed"]),
                    "--baseline-policies",
                    "telemetry_cruise,telemetry_yield,telemetry_lane",
                    "--stop-when-target-completes",
                    "--out-dir",
                    str(out_dir),
                ]
                if ablation["safe"]:
                    cmd.extend(
                        [
                            "--safe",
                            "--safe-blend",
                            str(ablation["safe_blend"]),
                            "--unsafe-blend",
                            str(ablation["unsafe_blend"]),
                        ]
                    )
                if not ablation["hard_shield"]:
                    cmd.append("--disable-hard-shield")
                run_command(cmd)
            validation = validate(path, root, ablation["name"], seed)
            summary = load_json(path)
            rows.append(
                {
                    "ablation": ablation["name"],
                    "seed": seed,
                    "validation_status": validation["status"],
                    "target_completed_lap": summary["target_completed_lap"],
                    "target_final_rank_by_tiles": summary["target_final_rank_by_tiles"],
                    "target_grass_rate": summary["grass_rate"][summary["target_agent"]],
                    "max_grass_rate": max(summary["grass_rate"]),
                    "tile_visited_count": summary["tile_visited_count"],
                    "steps_run": summary["steps_run"],
                    "summary": str(path),
                    "gif": summary["gif"],
                }
            )
    output = {"seeds": seeds, "rows": rows}
    (root / "ablation_summary.json").write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
