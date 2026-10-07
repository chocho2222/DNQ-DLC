#!/usr/bin/env python
import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path


METHODS = {
    "dlc_world_model": {
        "label": "DLC world model",
        "target_policy_path": "multi_car_racing/outputs/torch_dlc_full_lap_seed01/seed_1/models/joint_transition_observer.pt",
        "safe_blend": 0.95,
        "unsafe_blend": 1.0,
        "target_safe_base": "telemetry_overtake",
        "target_base_speed": 22.0,
    },
    "rule_overtake": {
        "label": "Rule overtake baseline",
        "target_policy_path": "multi_car_racing/outputs/paper_multicar_overtake_20260618/models/graph_bc/graph_bc.graph.pt",
        "safe_blend": 1.0,
        "unsafe_blend": 1.0,
        "target_safe_base": "telemetry_overtake",
        "target_base_speed": 22.0,
    },
    "graph_bc_shield": {
        "label": "Graph BC + shield",
        "target_policy_path": "multi_car_racing/outputs/paper_multicar_overtake_20260618/models/graph_bc/graph_bc.graph.pt",
        "safe_blend": 0.25,
        "unsafe_blend": 1.0,
        "target_safe_base": "telemetry_overtake",
        "target_base_speed": 22.0,
    },
    "graph_dagger_recovery_v2": {
        "label": "Graph DAgger recovery v2",
        "target_policy_path": "multi_car_racing/outputs/paper_multicar_overtake_20260618/models/graph_dagger_recovery_v2/graph_dagger_recovery.graph.pt",
        "safe_blend": 0.25,
        "unsafe_blend": 1.0,
        "target_safe_base": "telemetry_expert_gate",
        "target_base_speed": 22.0,
    },
    "graph_risk_world": {
        "label": "Graph-Risk DLC world model",
        "target_policy_path": "multi_car_racing/outputs/paper_multicar_overtake_20260618/models/graph_risk_world_model/graph_risk_dlc_world.graphworld.pt",
        "safe_blend": 0.25,
        "unsafe_blend": 1.0,
        "target_safe_base": "telemetry_overtake",
        "target_base_speed": 22.0,
    },
    "graph_risk_world_balanced": {
        "label": "Graph-Risk DLC world model (balanced)",
        "target_policy_path": "multi_car_racing/outputs/paper_multicar_overtake_20260618/models/graph_risk_world_model_variants/graph_risk_dlc_world_balanced.graphworld.pt",
        "safe_blend": 0.25,
        "unsafe_blend": 1.0,
        "target_safe_base": "telemetry_overtake",
        "target_base_speed": 22.0,
    },
    "graph_risk_world_safety": {
        "label": "Graph-Risk DLC world model (safety)",
        "target_policy_path": "multi_car_racing/outputs/paper_multicar_overtake_20260618/models/graph_risk_world_model_variants/graph_risk_dlc_world_safety.graphworld.pt",
        "safe_blend": 0.25,
        "unsafe_blend": 1.0,
        "target_safe_base": "telemetry_overtake",
        "target_base_speed": 22.0,
    },
    "graph_risk_world_fast": {
        "label": "Graph-Risk DLC world model (fast)",
        "target_policy_path": "multi_car_racing/outputs/paper_multicar_overtake_20260618/models/graph_risk_world_model_variants/graph_risk_dlc_world_fast.graphworld.pt",
        "safe_blend": 0.25,
        "unsafe_blend": 1.0,
        "target_safe_base": "telemetry_overtake",
        "target_base_speed": 22.0,
    },
}


def parse_csv_ints(value):
    return [int(item.strip()) for item in value.split(",") if item.strip()]


def run_command(cmd, cwd):
    completed = subprocess.run(
        cmd,
        cwd=cwd,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return completed.returncode, completed.stdout


def expected_summary_path(out_dir, method, seed, args):
    stem = Path(method["target_policy_path"]).stem
    return (
        Path(out_dir)
        / f"multicar_{args.num_agents}_target_{stem}_seed{seed}_gap{args.gap_tiles}.json"
    )


def run_one(method_name, method, seed, args):
    method_dir = Path(args.out_dir) / method_name / f"seed_{seed}"
    method_dir.mkdir(parents=True, exist_ok=True)
    summary_path = expected_summary_path(method_dir, method, seed, args)
    log_path = method_dir / "run.log"
    if not (args.skip_existing and summary_path.exists()):
        cmd = [
            sys.executable,
            "multi_car_racing/scripts/generate_multicar_overtake_gif.py",
            "--target-policy-path",
            method["target_policy_path"],
            "--model-dir",
            args.baseline_model_dir,
            "--num-agents",
            str(args.num_agents),
            "--seed",
            str(seed),
            "--gap-tiles",
            str(args.gap_tiles),
            "--lateral-spacing",
            str(args.lateral_spacing),
            "--single-file-start",
            "--steps",
            str(args.steps),
            "--frame-every",
            str(args.frame_every),
            "--fps",
            str(args.fps),
            "--device",
            args.device,
            "--safe",
            "--safe-blend",
            str(method["safe_blend"]),
            "--unsafe-blend",
            str(method["unsafe_blend"]),
            "--target-safe-base",
            method["target_safe_base"],
            "--target-base-speed",
            str(method["target_base_speed"]),
            "--baseline-policies",
            args.baseline_policies,
            "--stop-when-target-completes",
            "--out-dir",
            str(method_dir),
        ]
        if args.no_gif:
            cmd.append("--no-gif")
        if args.no_trace:
            cmd.append("--no-trace")
        if args.track_path:
            cmd.extend(["--track-path", args.track_path])
        code, output = run_command(cmd, args.cwd)
        log_path.write_text(output, encoding="utf-8")
        if code != 0:
            return {
                "method": method_name,
                "label": method["label"],
                "seed": seed,
                "status": "RUN_FAIL",
                "summary": str(summary_path),
                "log": str(log_path),
                "log_tail": output[-4000:],
            }
    data = json.loads(summary_path.read_text(encoding="utf-8"))
    target = int(data["target_agent"])
    track_tiles = max(int(data["track_tiles"]), 1)
    target_progress = float(data["tile_visited_count"][target] / track_tiles)
    completed = bool(data["target_completed_lap"])
    first = int(data["target_final_rank_by_tiles"]) == 1
    grass = float(data["grass_rate"][target])
    status = "PASS" if completed and first and grass <= args.max_target_grass_rate else "FAIL"
    return {
        "method": method_name,
        "label": method["label"],
        "seed": seed,
        "status": status,
        "summary": str(summary_path),
        "gif": data.get("gif", ""),
        "target_completed_lap": completed,
        "target_final_rank": int(data["target_final_rank_by_tiles"]),
        "target_complete_step": data["target_complete_step"],
        "first_ahead_step": data["first_ahead_step"],
        "target_grass_rate": grass,
        "target_tile_progress": target_progress,
        "steps_run": int(data["steps_run"]),
        "track_tiles": track_tiles,
        "target_tiles": int(data["tile_visited_count"][target]),
        "tile_visited_count": data["tile_visited_count"],
    }


def summarize(rows):
    by_method = {}
    for method in sorted({row["method"] for row in rows}):
        items = [row for row in rows if row["method"] == method and row["status"] != "RUN_FAIL"]
        n = len(items)
        pass_count = sum(row["status"] == "PASS" for row in items)
        completed = sum(row["target_completed_lap"] for row in items)
        finish_steps = [row["target_complete_step"] for row in items if row["target_complete_step"] is not None]
        by_method[method] = {
            "label": items[0]["label"] if items else method,
            "n": n,
            "pass_count": pass_count,
            "pass_rate": pass_count / n if n else None,
            "completion_count": completed,
            "completion_rate": completed / n if n else None,
            "mean_finish_step": sum(finish_steps) / len(finish_steps) if finish_steps else None,
            "mean_target_progress": sum(row["target_tile_progress"] for row in items) / n if n else None,
            "mean_target_grass_rate": sum(row["target_grass_rate"] for row in items) / n if n else None,
            "mean_rank": sum(row["target_final_rank"] for row in items) / n if n else None,
        }
    return by_method


def write_rows_csv(rows, path):
    fields = [
        "method",
        "label",
        "seed",
        "status",
        "target_completed_lap",
        "target_final_rank",
        "target_complete_step",
        "first_ahead_step",
        "target_grass_rate",
        "target_tile_progress",
        "steps_run",
        "track_tiles",
        "target_tiles",
        "summary",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field) for field in fields})


def main():
    parser = argparse.ArgumentParser(description="Compare DLC world baselines against the Graph-Risk DLC world model online.")
    parser.add_argument("--out-dir", default="multi_car_racing/outputs/paper_multicar_overtake_20260618/evaluations/graph_risk_world_comparison")
    parser.add_argument("--methods", default="dlc_world_model,rule_overtake,graph_bc_shield,graph_risk_world")
    parser.add_argument("--seeds", default="3,7,11")
    parser.add_argument("--num-agents", type=int, default=4)
    parser.add_argument("--gap-tiles", type=int, default=18)
    parser.add_argument("--lateral-spacing", type=float, default=0.0)
    parser.add_argument("--steps", type=int, default=3200)
    parser.add_argument("--frame-every", type=int, default=20)
    parser.add_argument("--fps", type=int, default=12)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--baseline-model-dir", default="multi_car_racing/outputs/torch_dlc_full_lap_seed01/seed_1/models")
    parser.add_argument("--baseline-policies", default="telemetry_cruise,telemetry_yield,telemetry_lane")
    parser.add_argument("--track-path", default="")
    parser.add_argument("--max-target-grass-rate", type=float, default=0.08)
    parser.add_argument("--no-gif", action="store_true")
    parser.add_argument("--no-trace", action="store_true")
    parser.add_argument("--skip-existing", action="store_true")
    parser.add_argument("--cwd", default="/home/itrc/VLM/racing/overtake")
    args = parser.parse_args()

    method_names = [item.strip() for item in args.methods.split(",") if item.strip()]
    unknown = [name for name in method_names if name not in METHODS]
    if unknown:
        raise ValueError(f"unknown methods: {unknown}; choices={sorted(METHODS)}")
    seeds = parse_csv_ints(args.seeds)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for method_name in method_names:
        for seed in seeds:
            row = run_one(method_name, METHODS[method_name], seed, args)
            rows.append(row)
            print(json.dumps(row, ensure_ascii=False), flush=True)

    result = {
        "description": "Online 4-car comparison focused on DLC world-model limitations and graph-risk world-model improvements.",
        "methods": method_names,
        "seeds": seeds,
        "settings": {
            "num_agents": args.num_agents,
            "gap_tiles": args.gap_tiles,
            "lateral_spacing": args.lateral_spacing,
            "steps": args.steps,
            "baseline_policies": args.baseline_policies,
            "max_target_grass_rate": args.max_target_grass_rate,
            "track_path": args.track_path,
        },
        "by_method": summarize(rows),
        "rows": rows,
    }
    summary_path = out_dir / "graph_risk_world_comparison_summary.json"
    rows_csv = out_dir / "graph_risk_world_comparison_rows.csv"
    summary_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    write_rows_csv(rows, rows_csv)
    print(json.dumps({"summary": str(summary_path), "rows_csv": str(rows_csv)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
