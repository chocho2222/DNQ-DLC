#!/usr/bin/env python
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import subprocess
import sys
from pathlib import Path


METHODS = {
    "graph_hard_shield": {
        "target_policy_path": True,
        "safe": True,
        "safe_blend": 0.25,
        "unsafe_blend": 1.0,
        "target_safe_base": "telemetry_lane",
        "target_base_speed": 22.0,
        "hard_shield": True,
    },
    "graph_soft_shield": {
        "target_policy_path": True,
        "safe": True,
        "safe_blend": 0.25,
        "unsafe_blend": 1.0,
        "target_safe_base": "telemetry_lane",
        "target_base_speed": 22.0,
        "hard_shield": False,
    },
    "graph_no_shield": {
        "target_policy_path": True,
        "safe": False,
        "safe_blend": 0.0,
        "unsafe_blend": 0.0,
        "target_safe_base": "telemetry_lane",
        "target_base_speed": 22.0,
        "hard_shield": False,
    },
    "lane_base_only": {
        "target_policy_path": True,
        "safe": True,
        "safe_blend": 1.0,
        "unsafe_blend": 1.0,
        "target_safe_base": "telemetry_lane",
        "target_base_speed": 22.0,
        "hard_shield": False,
    },
    "overtake_base_only": {
        "target_policy_path": True,
        "safe": True,
        "safe_blend": 1.0,
        "unsafe_blend": 1.0,
        "target_safe_base": "telemetry_overtake",
        "target_base_speed": 22.0,
        "hard_shield": False,
    },
    "overtake_conservative_traffic": {
        "target_policy_path": True,
        "safe": True,
        "safe_blend": 1.0,
        "unsafe_blend": 1.0,
        "target_safe_base": "telemetry_overtake",
        "target_base_speed": 22.0,
        "hard_shield": False,
        "baseline_policies": "telemetry_cruise,telemetry_yield,telemetry_adaptive_conservative",
    },
    "adaptive_gate_only": {
        "target_policy_path": True,
        "safe": True,
        "safe_blend": 1.0,
        "unsafe_blend": 1.0,
        "target_safe_base": "telemetry_adaptive",
        "target_base_speed": 22.0,
        "hard_shield": False,
    },
    "graph_adaptive_shield": {
        "target_policy_path": True,
        "safe": True,
        "safe_blend": 0.25,
        "unsafe_blend": 1.0,
        "target_safe_base": "telemetry_adaptive",
        "target_base_speed": 22.0,
        "hard_shield": False,
    },
    "recovery_adaptive_only": {
        "target_policy_path": True,
        "safe": True,
        "safe_blend": 1.0,
        "unsafe_blend": 1.0,
        "target_safe_base": "telemetry_adaptive_recovery",
        "target_base_speed": 22.0,
        "hard_shield": False,
    },
    "graph_recovery_adaptive_shield": {
        "target_policy_path": True,
        "safe": True,
        "safe_blend": 0.25,
        "unsafe_blend": 1.0,
        "target_safe_base": "telemetry_adaptive_recovery",
        "target_base_speed": 22.0,
        "hard_shield": False,
    },
    "graph_recovery_adaptive_conservative_traffic": {
        "target_policy_path": True,
        "safe": True,
        "safe_blend": 0.25,
        "unsafe_blend": 1.0,
        "target_safe_base": "telemetry_adaptive_recovery",
        "target_base_speed": 22.0,
        "hard_shield": False,
        "baseline_policies": "telemetry_cruise,telemetry_yield,telemetry_adaptive_conservative",
    },
    "heldout3_traffic_adaptive_conservative": {
        "target_policy_path": True,
        "safe": True,
        "safe_blend": 0.75,
        "unsafe_blend": 1.0,
        "target_safe_base": "telemetry_adaptive_conservative",
        "target_base_speed": 22.0,
        "hard_shield": True,
        "baseline_policies": "telemetry_cruise,telemetry_yield,telemetry_adaptive_conservative",
    },
    "expert_gate_only": {
        "target_policy_path": True,
        "safe": True,
        "safe_blend": 1.0,
        "unsafe_blend": 1.0,
        "target_safe_base": "telemetry_expert_gate",
        "target_base_speed": 22.0,
        "hard_shield": False,
    },
    "expert_fast_only": {
        "target_policy_path": True,
        "safe": True,
        "safe_blend": 1.0,
        "unsafe_blend": 1.0,
        "target_safe_base": "telemetry_expert_fast",
        "target_base_speed": 22.0,
        "hard_shield": False,
    },
    "expert_barrier_only": {
        "target_policy_path": True,
        "safe": True,
        "safe_blend": 1.0,
        "unsafe_blend": 1.0,
        "target_safe_base": "telemetry_expert_barrier",
        "target_base_speed": 22.0,
        "hard_shield": False,
    },
    "expert_recovery_only": {
        "target_policy_path": True,
        "safe": True,
        "safe_blend": 1.0,
        "unsafe_blend": 1.0,
        "target_safe_base": "telemetry_expert_recovery",
        "target_base_speed": 22.0,
        "hard_shield": False,
    },
    "graph_expert_gate_shield": {
        "target_policy_path": True,
        "safe": True,
        "safe_blend": 0.25,
        "unsafe_blend": 1.0,
        "target_safe_base": "telemetry_expert_gate",
        "target_base_speed": 22.0,
        "hard_shield": False,
    },
    "graph_expert_gate_shield_balanced": {
        "target_policy_path": True,
        "safe": True,
        "safe_blend": 0.50,
        "unsafe_blend": 1.0,
        "target_safe_base": "telemetry_expert_gate",
        "target_base_speed": 22.0,
        "hard_shield": False,
    },
    "graph_expert_gate_shield_more_graph": {
        "target_policy_path": True,
        "safe": True,
        "safe_blend": 0.75,
        "unsafe_blend": 1.0,
        "target_safe_base": "telemetry_expert_gate",
        "target_base_speed": 22.0,
        "hard_shield": False,
    },
    "graph_expert_gate_shield_base_heavy": {
        "target_policy_path": True,
        "safe": True,
        "safe_blend": 0.0,
        "unsafe_blend": 1.0,
        "target_safe_base": "telemetry_expert_gate",
        "target_base_speed": 22.0,
        "hard_shield": False,
    },
    "graph_expert_barrier_shield": {
        "target_policy_path": True,
        "safe": True,
        "safe_blend": 0.25,
        "unsafe_blend": 1.0,
        "target_safe_base": "telemetry_expert_barrier",
        "target_base_speed": 22.0,
        "hard_shield": False,
    },
    "graph_expert_recovery_shield": {
        "target_policy_path": True,
        "safe": True,
        "safe_blend": 0.25,
        "unsafe_blend": 1.0,
        "target_safe_base": "telemetry_expert_recovery",
        "target_base_speed": 22.0,
        "hard_shield": False,
    },
}


def parse_csv_ints(value):
    return [int(item.strip()) for item in value.split(",") if item.strip()]


def parse_csv(value):
    return [item.strip() for item in value.split(",") if item.strip()]


def parse_devices(value):
    values = parse_csv(value)
    return values or ["cuda:0"]


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def run_command(cmd):
    completed = subprocess.run(
        cmd,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return completed.returncode, completed.stdout


def expected_summary_path(out_dir, num_agents, model_path, seed, gap_tiles):
    stem = f"multicar_{num_agents}_target_{Path(model_path).stem}_seed{seed}_gap{gap_tiles}"
    return out_dir / f"{stem}.json"


def validate(summary_path, out_path, args):
    cmd = [
        sys.executable,
        "scripts/validate_multicar_lap.py",
        str(summary_path),
        "--max-target-grass-rate",
        str(args.max_target_grass_rate),
        "--max-any-grass-rate",
        str(args.max_any_grass_rate),
        "--min-mean-tile-progress",
        str(args.min_mean_tile_progress),
        "--min-first-ahead-step",
        str(args.min_first_ahead_step),
        "--require-target-complete",
        "--require-target-first",
        "--require-first-ahead",
        "--out",
        str(out_path),
    ]
    code, output = run_command(cmd)
    if out_path.exists():
        return load_json(out_path), code, output
    return json.loads(output), code, output


def run_job(args, method_name, method, seed, device):
    out_dir = Path(args.out_dir) / method_name / f"seed_{seed}"
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_path = expected_summary_path(out_dir, args.num_agents, args.model_path, seed, args.gap_tiles)
    log_path = out_dir / "run.log"

    if not (args.skip_existing and summary_path.exists()):
        cmd = [
            sys.executable,
            "scripts/generate_multicar_overtake_gif.py",
            "--target-policy-path",
            args.model_path,
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
            device,
            "--target-safe-base",
            method["target_safe_base"],
            "--target-base-speed",
            str(method["target_base_speed"]),
            "--baseline-policies",
            method.get("baseline_policies", args.baseline_policies),
            "--stop-when-target-completes",
            "--out-dir",
            str(out_dir),
        ]
        if args.no_gif:
            cmd.append("--no-gif")
        if args.no_trace:
            cmd.append("--no-trace")
        if method["safe"]:
            cmd.extend(
                [
                    "--safe",
                    "--safe-blend",
                    str(method["safe_blend"]),
                    "--unsafe-blend",
                    str(method["unsafe_blend"]),
                ]
            )
        if not method["hard_shield"]:
            cmd.append("--disable-hard-shield")
        code, output = run_command(cmd)
        log_path.write_text(output, encoding="utf-8")
        if code != 0:
            return {
                "method": method_name,
                "seed": seed,
                "device": device,
                "status": "RUN_FAIL",
                "summary": str(summary_path),
                "validation_status": "RUN_FAIL",
                "log": str(log_path),
                "log_tail": output[-4000:],
            }

    validation_path = out_dir / "validation.json"
    validation, validation_code, validation_output = validate(summary_path, validation_path, args)
    summary = load_json(summary_path)
    track_tiles = max(int(summary["track_tiles"]), 1)
    target_agent = int(summary["target_agent"])
    row = {
        "method": method_name,
        "seed": seed,
        "device": device,
        "status": "PASS" if validation["status"] == "PASS" else "FAIL",
        "validation_status": validation["status"],
        "validation_returncode": validation_code,
        "summary": str(summary_path),
        "validation": str(validation_path),
        "gif": summary["gif"],
        "log": str(log_path),
        "target_completed_lap": bool(summary["target_completed_lap"]),
        "target_final_rank_by_tiles": int(summary["target_final_rank_by_tiles"]),
        "target_grass_rate": float(summary["grass_rate"][target_agent]),
        "max_grass_rate": float(max(summary["grass_rate"])),
        "target_tile_progress": float(summary["tile_visited_count"][target_agent] / track_tiles),
        "mean_tile_progress": float(sum(x / track_tiles for x in summary["tile_visited_count"]) / summary["num_agents"]),
        "first_ahead_step": summary["first_ahead_step"],
        "target_complete_step": summary["target_complete_step"],
        "steps_run": int(summary["steps_run"]),
        "track_tiles": track_tiles,
        "tile_visited_count": summary["tile_visited_count"],
    }
    if validation_code != 0:
        row["validation_log_tail"] = validation_output[-2000:]
    return row


def summarize_method(rows):
    rows = list(rows)
    n = len(rows)
    pass_count = sum(row["validation_status"] == "PASS" for row in rows)
    metric_rows = [row for row in rows if "target_grass_rate" in row]
    if n == 0:
        return {"n": 0, "pass_count": 0, "pass_rate": None}
    return {
        "n": n,
        "pass_count": pass_count,
        "pass_rate": pass_count / n,
        "target_grass_rate_mean": sum(row["target_grass_rate"] for row in metric_rows) / len(metric_rows)
        if metric_rows
        else None,
        "max_grass_rate_mean": sum(row["max_grass_rate"] for row in metric_rows) / len(metric_rows)
        if metric_rows
        else None,
        "target_tile_progress_mean": sum(row["target_tile_progress"] for row in metric_rows) / len(metric_rows)
        if metric_rows
        else None,
        "mean_tile_progress_mean": sum(row["mean_tile_progress"] for row in metric_rows) / len(metric_rows)
        if metric_rows
        else None,
        "target_rank_mean": sum(row["target_final_rank_by_tiles"] for row in metric_rows) / len(metric_rows)
        if metric_rows
        else None,
        "failures": [
            {
                "seed": row["seed"],
                "rank": row.get("target_final_rank_by_tiles"),
                "target_progress": row.get("target_tile_progress"),
                "target_grass_rate": row.get("target_grass_rate"),
                "summary": row.get("summary"),
            }
            for row in rows
            if row["validation_status"] != "PASS"
        ],
    }


def main():
    parser = argparse.ArgumentParser(description="Run a unified multi-seed multi-car overtaking evaluation suite.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    parser.add_argument("--out-dir", default="")
    parser.add_argument("--model-path", default="outputs/paper_multicar_overtake_20260618/models/graph_bc/graph_bc.graph.pt")
    parser.add_argument("--baseline-model-dir", default="outputs/torch_dlc_full_lap_seed01/seed_1/models")
    parser.add_argument("--methods", default="graph_soft_shield,graph_hard_shield,lane_base_only")
    parser.add_argument("--seeds", default="3,7,11,17,23,29,31,37,41,43")
    parser.add_argument("--devices", default="cuda:0")
    parser.add_argument("--parallel", type=int, default=1)
    parser.add_argument("--num-agents", type=int, default=4)
    parser.add_argument("--gap-tiles", type=int, default=22)
    parser.add_argument("--lateral-spacing", type=float, default=0.0)
    parser.add_argument("--steps", type=int, default=3200)
    parser.add_argument("--frame-every", type=int, default=20)
    parser.add_argument("--fps", type=int, default=12)
    parser.add_argument("--baseline-policies", default="telemetry_cruise,telemetry_yield,telemetry_lane")
    parser.add_argument("--max-target-grass-rate", type=float, default=0.08)
    parser.add_argument("--max-any-grass-rate", type=float, default=0.40)
    parser.add_argument("--min-mean-tile-progress", type=float, default=0.60)
    parser.add_argument("--min-first-ahead-step", type=int, default=10)
    parser.add_argument("--no-gif", action="store_true")
    parser.add_argument("--no-trace", action="store_true")
    parser.add_argument("--skip-existing", action="store_true")
    args = parser.parse_args()

    root = Path(args.root)
    if not args.out_dir:
        args.out_dir = str(root / "evaluations" / "multiseed_suite")
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    method_names = parse_csv(args.methods)
    unknown = [name for name in method_names if name not in METHODS]
    if unknown:
        raise ValueError(f"unknown methods: {unknown}; choices={sorted(METHODS)}")
    seeds = parse_csv_ints(args.seeds)
    devices = parse_devices(args.devices)
    jobs = []
    for method_index, method_name in enumerate(method_names):
        for seed_index, seed in enumerate(seeds):
            jobs.append(
                {
                    "method_name": method_name,
                    "method": METHODS[method_name],
                    "seed": seed,
                    "device": devices[(method_index + seed_index) % len(devices)],
                }
            )

    rows = []
    workers = max(1, min(args.parallel, len(jobs))) if jobs else 1
    if workers == 1:
        for job in jobs:
            rows.append(run_job(args, job["method_name"], job["method"], job["seed"], job["device"]))
    else:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(run_job, args, job["method_name"], job["method"], job["seed"], job["device"]): job
                for job in jobs
            }
            for future in as_completed(futures):
                rows.append(future.result())

    rows.sort(key=lambda item: (item["method"], item["seed"]))
    by_method = {
        method_name: summarize_method(row for row in rows if row["method"] == method_name)
        for method_name in method_names
    }
    output = {
        "root": str(root),
        "out_dir": str(out_dir),
        "model_path": args.model_path,
        "methods": method_names,
        "seeds": seeds,
        "thresholds": {
            "max_target_grass_rate": args.max_target_grass_rate,
            "max_any_grass_rate": args.max_any_grass_rate,
            "min_mean_tile_progress": args.min_mean_tile_progress,
            "min_first_ahead_step": args.min_first_ahead_step,
        },
        "by_method": by_method,
        "rows": rows,
    }
    summary_path = out_dir / "multiseed_suite_summary.json"
    summary_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
