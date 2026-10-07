#!/usr/bin/env python
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
import json
import subprocess
import sys
from pathlib import Path


def parse_csv(value):
    return [item.strip() for item in value.split(",") if item.strip()]


def run_command(cmd):
    completed = subprocess.run(cmd, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return completed.returncode, completed.stdout


def expected_summary_path(out_dir, num_agents, model_path, seed, gap_tiles):
    stem = f"multicar_{num_agents}_target_{Path(model_path).stem}_seed{seed}_gap{gap_tiles}"
    return out_dir / f"{stem}.json"


def validate(summary_path, out_path):
    cmd = [
        sys.executable,
        "scripts/validate_multicar_lap.py",
        str(summary_path),
        "--max-target-grass-rate",
        "0.08",
        "--max-any-grass-rate",
        "0.4",
        "--require-target-complete",
        "--require-target-first",
        "--require-first-ahead",
        "--min-mean-tile-progress",
        "0.6",
        "--min-first-ahead-step",
        "10",
        "--out",
        str(out_path),
    ]
    code, output = run_command(cmd)
    return json.loads(output), code, output


def build_configs():
    baseline_sets = {
        "lane": "telemetry_cruise,telemetry_yield,telemetry_lane",
        "adaptive_conservative": "telemetry_cruise,telemetry_yield,telemetry_adaptive_conservative",
        "all_yield": "telemetry_yield,telemetry_yield,telemetry_yield",
        "all_cruise": "telemetry_cruise,telemetry_cruise,telemetry_cruise",
    }
    target_bases = ["telemetry_expert_gate", "telemetry_adaptive_recovery", "telemetry_adaptive_conservative"]
    blends = [(0.25, 1.0), (0.50, 1.0), (0.75, 1.0), (1.0, 1.0)]
    hard_shields = [False, True]
    configs = []
    for baseline_name, baseline in baseline_sets.items():
        for target_base in target_bases:
            for safe_blend, unsafe_blend in blends:
                for hard_shield in hard_shields:
                    configs.append(
                        {
                            "name": (
                                f"b_{baseline_name}__target_{target_base.replace('telemetry_', '')}"
                                f"__blend_{safe_blend:.2f}_{unsafe_blend:.2f}"
                                f"__hard_{int(hard_shield)}"
                            ),
                            "baseline_name": baseline_name,
                            "baseline_policies": baseline,
                            "target_safe_base": target_base,
                            "safe_blend": safe_blend,
                            "unsafe_blend": unsafe_blend,
                            "hard_shield": hard_shield,
                        }
                    )
    return configs


def run_config(args, config, device):
    out_dir = Path(args.out_dir) / config["name"]
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_path = expected_summary_path(out_dir, args.num_agents, args.model_path, args.seed, args.gap_tiles)
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
            str(args.seed),
            "--gap-tiles",
            str(args.gap_tiles),
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
            device,
            "--target-safe-base",
            config["target_safe_base"],
            "--target-base-speed",
            str(args.target_base_speed),
            "--baseline-policies",
            config["baseline_policies"],
            "--stop-when-target-completes",
            "--out-dir",
            str(out_dir),
            "--safe",
            "--safe-blend",
            str(config["safe_blend"]),
            "--unsafe-blend",
            str(config["unsafe_blend"]),
            "--no-gif",
            "--no-trace",
        ]
        if not config["hard_shield"]:
            cmd.append("--disable-hard-shield")
        code, output = run_command(cmd)
        log_path.write_text(output, encoding="utf-8")
        if code != 0:
            return {**config, "device": device, "status": "RUN_FAIL", "log": str(log_path), "summary": str(summary_path)}
    validation_path = out_dir / "validation.json"
    validation, validation_code, validation_output = validate(summary_path, validation_path)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    target = int(summary["target_agent"])
    track_tiles = max(int(summary["track_tiles"]), 1)
    progress = [count / track_tiles for count in summary["tile_visited_count"]]
    return {
        **config,
        "device": device,
        "status": validation["status"],
        "validation_returncode": validation_code,
        "summary": str(summary_path),
        "validation": str(validation_path),
        "target_completed_lap": bool(summary["target_completed_lap"]),
        "target_final_rank_by_tiles": int(summary["target_final_rank_by_tiles"]),
        "target_grass_rate": float(summary["grass_rate"][target]),
        "max_grass_rate": float(max(summary["grass_rate"])),
        "mean_tile_progress": float(sum(progress) / len(progress)),
        "target_tile_progress": float(progress[target]),
        "first_ahead_step": summary["first_ahead_step"],
        "target_complete_step": summary["target_complete_step"],
        "steps_run": int(summary["steps_run"]),
        "checks": validation["checks"],
    }


def write_outputs(report, root, prefix):
    table_dir = root / "tables"
    table_dir.mkdir(parents=True, exist_ok=True)
    out_json = table_dir / f"{prefix}.json"
    out_csv = table_dir / f"{prefix}_rows.csv"
    out_md = table_dir / f"{prefix}.md"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    fields = [
        "name",
        "status",
        "baseline_name",
        "target_safe_base",
        "safe_blend",
        "unsafe_blend",
        "hard_shield",
        "target_completed_lap",
        "target_final_rank_by_tiles",
        "target_grass_rate",
        "max_grass_rate",
        "mean_tile_progress",
        "target_tile_progress",
        "first_ahead_step",
        "target_complete_step",
        "steps_run",
        "summary",
    ]
    with out_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in report["rows"]:
            writer.writerow({field: row.get(field) for field in fields})
    lines = [
        "# Seed 157 Traffic-aware Ablation",
        "",
        report["interpretation"],
        "",
        "## Summary",
        "",
        f"- Configurations: {report['n']}",
        f"- Passing configurations: {report['pass_count']}",
        f"- Best non-passing target-complete rank-1 configurations: {len(report['near_misses'])}",
        "",
        "## Passing Configurations",
        "",
    ]
    if report["pass_rows"]:
        for row in report["pass_rows"]:
            lines.append(
                f"- `{row['name']}`: target grass {row['target_grass_rate']:.3f}, "
                f"max grass {row['max_grass_rate']:.3f}, mean progress {row['mean_tile_progress']:.3f}"
            )
    else:
        lines.append("- None")
    lines.extend(["", "## Top Near Misses", ""])
    for row in report["near_misses"][:10]:
        failed = [key for key, value in row.get("checks", {}).items() if not value]
        lines.append(
            f"- `{row['name']}`: failed {failed}; target grass {row['target_grass_rate']:.3f}, "
            f"max grass {row['max_grass_rate']:.3f}, mean progress {row['mean_tile_progress']:.3f}"
        )
    lines.extend(["", "## Reporting Boundary", "", "- This is a seed-targeted diagnostic ablation, not external validation.", ""])
    out_md.write_text("\n".join(lines), encoding="utf-8")
    return {"json": str(out_json), "csv": str(out_csv), "markdown": str(out_md)}


def main():
    parser = argparse.ArgumentParser(description="Run seed-157 traffic-aware targeted ablation.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    parser.add_argument("--out-dir", default="outputs/paper_multicar_overtake_20260618/evaluations/seed157_traffic_ablation")
    parser.add_argument("--model-path", default="outputs/paper_multicar_overtake_20260618/models/heldout3_targeted_recovery/graph_dagger_recovery.graph.pt")
    parser.add_argument("--baseline-model-dir", default="outputs/torch_dlc_full_lap_seed01/seed_1/models")
    parser.add_argument("--devices", default="cuda:0,cuda:1,cuda:2,cuda:3")
    parser.add_argument("--parallel", type=int, default=4)
    parser.add_argument("--seed", type=int, default=157)
    parser.add_argument("--num-agents", type=int, default=4)
    parser.add_argument("--gap-tiles", type=int, default=22)
    parser.add_argument("--steps", type=int, default=3200)
    parser.add_argument("--target-base-speed", type=float, default=22.0)
    parser.add_argument("--table-prefix", default="seed157_traffic_ablation")
    parser.add_argument("--skip-existing", action="store_true")
    args = parser.parse_args()

    configs = build_configs()
    devices = parse_csv(args.devices) or ["cuda:0"]
    rows = []
    workers = max(1, min(args.parallel, len(configs)))
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(run_config, args, config, devices[idx % len(devices)]): config
            for idx, config in enumerate(configs)
        }
        for future in as_completed(futures):
            rows.append(future.result())
    rows.sort(key=lambda row: (row["status"] != "PASS", row.get("max_grass_rate", 999), row["name"]))
    pass_rows = [row for row in rows if row["status"] == "PASS"]
    near_misses = [
        row
        for row in rows
        if row["status"] != "PASS"
        and row.get("target_completed_lap")
        and row.get("target_final_rank_by_tiles") == 1
        and row.get("target_grass_rate", 1.0) <= 0.08
    ]
    near_misses.sort(key=lambda row: (row.get("max_grass_rate", 999), -row.get("mean_tile_progress", 0)))
    report = {
        "root": args.root,
        "out_dir": args.out_dir,
        "seed": args.seed,
        "model_path": args.model_path,
        "n": len(rows),
        "pass_count": len(pass_rows),
        "pass_rows": pass_rows,
        "near_misses": near_misses,
        "rows": rows,
        "interpretation": (
            "This seed-targeted ablation tests whether the remaining heldout3 candidate gap at seed 157 is caused by "
            "target-control failure or traffic-quality failure. It varies background traffic policies, target safety base, "
            "blend strength, and hard-shielding while keeping the strict validator fixed."
        ),
    }
    outputs = write_outputs(report, Path(args.root), args.table_prefix)
    print(json.dumps(outputs, indent=2))


if __name__ == "__main__":
    main()
