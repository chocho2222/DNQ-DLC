#!/usr/bin/env python
import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent


def python_prefix(args):
    if args.python_bin:
        return [args.python_bin]
    if args.conda_env:
        return ["conda", "run", "-n", args.conda_env, "python"]
    return [sys.executable]


def run_command(cmd, log_path=None):
    print("+ " + " ".join(str(part) for part in cmd), flush=True)
    env = dict(os.environ)
    py_path = str(PROJECT_ROOT)
    if env.get("PYTHONPATH"):
        env["PYTHONPATH"] = py_path + os.pathsep + env["PYTHONPATH"]
    else:
        env["PYTHONPATH"] = py_path
    if log_path is None:
        subprocess.run(cmd, check=True, cwd=PROJECT_ROOT, env=env)
        return
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as handle:
        subprocess.run(cmd, check=True, stdout=handle, stderr=subprocess.STDOUT, cwd=PROJECT_ROOT, env=env)


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def run_eval(args, model_path, method_name, seed, out_dir, log_path, method_kwargs):
    summary_path = expected_graph_summary(out_dir, model_path, seed, 22)
    if not (args.skip_training and summary_path.exists()):
        cmd = [
            *python_prefix(args),
            str(PROJECT_ROOT / "scripts" / "generate_multicar_overtake_gif.py"),
            "--target-policy-path",
            str(model_path),
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
            "3200",
            "--frame-every",
            "10",
            "--fps",
            "12",
            "--device",
            args.device,
            "--safe",
            "--safe-blend",
            str(method_kwargs["safe_blend"]),
            "--unsafe-blend",
            str(method_kwargs["unsafe_blend"]),
            "--target-safe-base",
            method_kwargs["target_safe_base"],
            "--target-base-speed",
            str(method_kwargs["target_base_speed"]),
            "--baseline-policies",
            method_kwargs["baseline_policies"],
            "--stop-when-target-completes",
            "--out-dir",
            str(out_dir),
        ]
        if not method_kwargs.get("hard_shield", True):
            cmd.append("--disable-hard-shield")
        run_command(cmd, log_path)

    validation_path = out_dir / "validation.json"
    validation = validate(summary_path, validation_path, args)
    summary = load_json(summary_path)
    target_agent = summary["target_agent"]
    track_tiles = max(int(summary["track_tiles"]), 1)
    return {
        "method": method_name,
        "summary": str(summary_path),
        "gif": summary["gif"],
        "validation_status": validation["status"],
        "target_completed_lap": summary["target_completed_lap"],
        "target_final_rank_by_tiles": summary["target_final_rank_by_tiles"],
        "target_grass_rate": summary["grass_rate"][target_agent],
        "max_grass_rate": max(summary["grass_rate"]),
        "mean_tile_progress": sum(x / track_tiles for x in summary["tile_visited_count"]) / summary["num_agents"],
        "tile_visited_count": summary["tile_visited_count"],
        "steps_run": summary["steps_run"],
        "seed": seed,
    }


def copy_materials(root):
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    for src_name in ["baselines", "configs"]:
        src = PROJECT_ROOT / src_name
        dst = materials / src_name
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
    script_dir = materials / "scripts"
    script_dir.mkdir(exist_ok=True)
    for name in [
        "run_paper_experiment.py",
        "run_baseline_suite.py",
        "run_ablation_suite.py",
        "run_multiseed_overtake_suite.py",
        "train_graph_bc.py",
        "generate_multicar_overtake_gif.py",
        "validate_multicar_lap.py",
        "export_paper_tables.py",
        "export_statistical_report.py",
        "export_paper_figures.py",
    ]:
        shutil.copy2(PROJECT_ROOT / "scripts" / name, script_dir / name)
    dlc_dir = materials / "dlc"
    dlc_dir.mkdir(exist_ok=True)
    for src in (PROJECT_ROOT / "dlc").glob("*.py"):
        shutil.copy2(src, dlc_dir / src.name)


def validate(summary_path, out_path, args):
    cmd = [
        *python_prefix(args),
        str(PROJECT_ROOT / "scripts" / "validate_multicar_lap.py"),
        str(summary_path),
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
        str(out_path),
    ]
    env = dict(os.environ)
    py_path = str(PROJECT_ROOT)
    if env.get("PYTHONPATH"):
        env["PYTHONPATH"] = py_path + os.pathsep + env["PYTHONPATH"]
    else:
        env["PYTHONPATH"] = py_path
    result = subprocess.run(cmd, text=True, capture_output=True, cwd=PROJECT_ROOT, env=env)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if not out_path.exists() and result.stdout:
        out_path.write_text(result.stdout, encoding="utf-8")
    return json.loads(result.stdout)


def expected_graph_summary(eval_dir, model_path, seed, gap_tiles):
    stem = f"multicar_4_target_{Path(model_path).stem}_seed{seed}_gap{gap_tiles}"
    return eval_dir / f"{stem}.json"


def main():
    parser = argparse.ArgumentParser(description="Run paper-style multi-car overtake experiment package.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    parser.add_argument("--baseline-model-dir", default="outputs/torch_dlc_full_lap_seed01/seed_1/models")
    parser.add_argument("--dlc-model-dir", default="outputs/torch_dlc_full_lap_seed01/seed_1/models")
    parser.add_argument("--seed", type=int, default=3)
    parser.add_argument("--eval-seeds", default="3,7,11")
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--conda-env", default="vlm_planner")
    parser.add_argument("--python-bin", default="")
    parser.add_argument("--bc-episodes", type=int, default=24)
    parser.add_argument("--bc-max-steps", type=int, default=2600)
    parser.add_argument("--bc-train-steps", type=int, default=1500)
    parser.add_argument("--skip-baselines", action="store_true")
    parser.add_argument("--skip-training", action="store_true")
    args = parser.parse_args()

    root = Path(args.root)
    for sub in ["configs", "baselines", "models", "evaluations", "figures", "tables", "materials", "logs"]:
        (root / sub).mkdir(parents=True, exist_ok=True)
    copy_materials(root)

    manifest = {
        "title": "Permutation-invariant safe multi-car full-lap overtaking",
        "root": str(root),
        "baseline_model_dir": args.baseline_model_dir,
        "seed": args.seed,
        "eval_seeds": [int(item) for item in args.eval_seeds.split(",") if item.strip()],
        "device": args.device,
        "components": {
            "baselines": "telemetry_cruise, telemetry_yield, telemetry_lane",
            "innovation": "graph/set actor behavior cloning with safety shield",
            "comparison": "DLC-style world model / state-space actors",
            "excluded": "VLM components intentionally excluded",
        },
    }
    (root / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    if not args.skip_baselines:
        run_command(
            [
                *python_prefix(args),
                str(PROJECT_ROOT / "scripts" / "run_baseline_suite.py"),
                "--config-dir",
                str(PROJECT_ROOT / "baselines"),
                "--model-dir",
                args.baseline_model_dir,
                "--out-dir",
                str(root / "baselines"),
                "--device",
                args.device,
                "--seed",
                str(args.seed),
                "--skip-existing",
            ],
            root / "logs" / "baseline_suite.log",
        )

    model_dir = root / "models" / "graph_bc"
    graph_model = model_dir / "graph_bc.graph.pt"
    if not (args.skip_training and graph_model.exists()):
        run_command(
            [
                *python_prefix(args),
                str(PROJECT_ROOT / "scripts" / "train_graph_bc.py"),
                "--episodes",
                str(args.bc_episodes),
                "--max-steps",
                str(args.bc_max_steps),
                "--train-steps",
                str(args.bc_train_steps),
                "--device",
                args.device,
                "--out-dir",
                str(model_dir),
            ],
            root / "logs" / "train_graph_bc.log",
        )

    graph_rows = []
    for seed in manifest["eval_seeds"]:
        eval_dir = root / "evaluations" / f"graph_bc_seed_{seed}"
        graph_rows.append(
            {
                **run_eval(
                    args,
                    graph_model,
                    "graph_bc",
                    seed,
                    eval_dir,
                    root / "logs" / f"eval_graph_bc_seed_{seed}.log",
                    {
                        "safe_blend": 0.25,
                        "unsafe_blend": 1.0,
                        "target_safe_base": "telemetry_lane",
                        "target_base_speed": 22.0,
                        "baseline_policies": "telemetry_cruise,telemetry_yield,telemetry_lane",
                        "hard_shield": True,
                    },
                )
            }
        )

    dlc_rows = []
    dlc_methods = [
        ("joint_transition_observer", "joint_transition_observer.pt"),
        ("joint_transition", "joint_transition.pt"),
        ("individual_transition", "individual_transition.pt"),
    ]
    for seed in manifest["eval_seeds"]:
        for method_name, filename in dlc_methods:
            model_path = Path(args.dlc_model_dir) / filename
            eval_dir = root / "evaluations" / f"dlc_{method_name}_seed_{seed}"
            dlc_rows.append(
                run_eval(
                    args,
                    model_path,
                    f"dlc:{method_name}",
                    seed,
                    eval_dir,
                    root / "logs" / f"eval_dlc_{method_name}_seed_{seed}.log",
                    {
                        "safe_blend": 0.25,
                        "unsafe_blend": 1.0,
                        "target_safe_base": "telemetry_lane",
                        "target_base_speed": 22.0,
                        "baseline_policies": "telemetry_cruise,telemetry_yield,telemetry_lane",
                        "hard_shield": True,
                    },
                )
            )

    baseline_summary_path = root / "baselines" / "baseline_suite_summary.json"
    baseline_rows = load_json(baseline_summary_path)["rows"] if baseline_summary_path.exists() else []
    table = {
        "baseline_rows": baseline_rows,
        "graph_bc_rows": graph_rows,
        "dlc_rows": dlc_rows,
        "graph_bc_pass_rate": sum(row["validation_status"] == "PASS" for row in graph_rows) / max(len(graph_rows), 1),
        "dlc_pass_rate": sum(row["validation_status"] == "PASS" for row in dlc_rows) / max(len(dlc_rows), 1),
    }
    (root / "tables" / "main_results.json").write_text(json.dumps(table, indent=2), encoding="utf-8")
    methods = f"""# Paper Experiment Package

## Objective

Strict multi-car full-lap overtaking without VLM components.

## Baselines

Saved baseline controllers: telemetry_cruise, telemetry_yield, telemetry_lane, and the mixed pool.

## Innovation Method

Permutation-invariant graph/set actor trained by behavior cloning from multi-car expert rollouts, executed with a safety shield.

## Comparison Algorithms

Telemetry-state DLC/world-model family:
`joint_transition_observer`, `joint_transition`, `individual_transition`.

## Metrics

Target full-lap completion, final rank by visited tiles, grass rate, mean tile progress, first-ahead step, and multi-seed pass rate.

## Reproducibility

All configs, scripts, logs, model checkpoints, GIFs, summaries, and validation files are stored under:

`{root}`
"""
    (root / "materials" / "METHODS.md").write_text(methods, encoding="utf-8")
    print(json.dumps({"status": "PASS", "root": str(root), "table": table}, indent=2))


if __name__ == "__main__":
    main()
