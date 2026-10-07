#!/usr/bin/env python
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
import json
import subprocess
import sys
from pathlib import Path


METHODS = {
    "lane_base_only": {
        "suite": "main",
        "method_key": "main:lane_base_only",
        "target_safe_base": "telemetry_lane",
        "safe_blend": 1.0,
        "unsafe_blend": 1.0,
    },
    "overtake_base_only": {
        "suite": "main",
        "method_key": "main:overtake_base_only",
        "target_safe_base": "telemetry_overtake",
        "safe_blend": 1.0,
        "unsafe_blend": 1.0,
    },
    "graph_adaptive_shield": {
        "suite": "adaptive",
        "method_key": "adaptive:graph_adaptive_shield",
        "target_safe_base": "telemetry_adaptive",
        "safe_blend": 0.25,
        "unsafe_blend": 1.0,
    },
    "expert_gate_only": {
        "suite": "expert",
        "method_key": "expert:expert_gate_only",
        "target_safe_base": "telemetry_expert_gate",
        "safe_blend": 1.0,
        "unsafe_blend": 1.0,
    },
    "expert_barrier_only": {
        "suite": "barrier",
        "method_key": "barrier:expert_barrier_only",
        "target_safe_base": "telemetry_expert_barrier",
        "safe_blend": 1.0,
        "unsafe_blend": 1.0,
    },
    "expert_recovery_only": {
        "suite": "recovery_expert",
        "method_key": "recovery_expert:expert_recovery_only",
        "target_safe_base": "telemetry_expert_recovery",
        "safe_blend": 1.0,
        "unsafe_blend": 1.0,
    },
    "dagger_v2_graph_expert_gate_shield": {
        "suite": "dagger_v2",
        "full_method": "graph_expert_gate_shield",
        "method_key": "dagger_v2:graph_expert_gate_shield",
        "model_path": "outputs/paper_multicar_overtake_20260618/models/graph_dagger_recovery_v2/graph_dagger_recovery.graph.pt",
        "target_safe_base": "telemetry_expert_gate",
        "safe_blend": 0.25,
        "unsafe_blend": 1.0,
    },
    "dagger_v2_graph_expert_gate_more_graph": {
        "suite": "dagger_v2_more_graph",
        "full_method": "graph_expert_gate_shield_more_graph",
        "method_key": "dagger_v2:graph_expert_gate_shield_more_graph",
        "model_path": "outputs/paper_multicar_overtake_20260618/models/graph_dagger_recovery_v2/graph_dagger_recovery.graph.pt",
        "target_safe_base": "telemetry_expert_gate",
        "safe_blend": 0.75,
        "unsafe_blend": 1.0,
    },
    "heldout3_traffic_adaptive_conservative": {
        "suite": "heldout3_traffic_adaptive_conservative",
        "method_key": "heldout3_targeted:traffic_adaptive_conservative",
        "model_path": "outputs/paper_multicar_overtake_20260618/models/heldout3_targeted_recovery/graph_dagger_recovery.graph.pt",
        "target_safe_base": "telemetry_adaptive_conservative",
        "safe_blend": 0.75,
        "unsafe_blend": 1.0,
        "hard_shield": True,
        "baseline_policies": "telemetry_cruise,telemetry_yield,telemetry_adaptive_conservative",
    },
}

DEFAULT_SUITE_PATHS = {
    "main": "evaluations/multiseed_suite/multiseed_suite_summary.json",
    "adaptive": "evaluations/adaptive_gate_suite/multiseed_suite_summary.json",
    "expert": "evaluations/expert_gate_targeted/multiseed_suite_summary.json",
    "barrier": "evaluations/heldout_expert_barrier_suite/multiseed_suite_summary.json",
    "recovery_expert": "evaluations/heldout_expert_recovery_suite/multiseed_suite_summary.json",
    "dagger_v2": "evaluations/heldout_graph_dagger_recovery_v2_suite/multiseed_suite_summary.json",
    "dagger_v2_more_graph": "evaluations/heldout_graph_dagger_recovery_v2_more_graph_suite/multiseed_suite_summary.json",
    "heldout3_traffic_adaptive_conservative": (
        "evaluations/heldout3_traffic_adaptive_conservative_suite/multiseed_suite_summary.json"
    ),
}


def parse_csv(value):
    return [item.strip() for item in value.split(",") if item.strip()]


def parse_int_csv(value):
    return [int(item) for item in parse_csv(value)]


def parse_mapping_csv(value):
    mapping = {}
    for item in parse_csv(value):
        if "=" not in item:
            raise ValueError(f"expected NAME=VALUE mapping, got {item!r}")
        name, mapped_value = item.split("=", 1)
        mapping[name.strip()] = mapped_value.strip()
    return mapping


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def expected_summary_path(out_dir, num_agents, model_path, seed, gap_tiles):
    stem = f"multicar_{num_agents}_target_{Path(model_path).stem}_seed{seed}_gap{gap_tiles}"
    return out_dir / f"{stem}.json"


def run_command(cmd):
    completed = subprocess.run(
        cmd,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return completed.returncode, completed.stdout


def run_probe(args, method_name, seed, device):
    method = METHODS[method_name]
    model_path = args.method_model_paths.get(method_name) or method.get("model_path") or args.model_path
    out_dir = Path(args.out_dir) / "probes" / method_name / f"seed_{seed}"
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_path = expected_summary_path(out_dir, args.num_agents, model_path, seed, args.gap_tiles)
    log_path = out_dir / "run.log"
    if not (args.skip_existing and summary_path.exists()):
        cmd = [
            sys.executable,
            "scripts/generate_multicar_overtake_gif.py",
            "--target-policy-path",
            model_path,
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
            str(args.probe_steps),
            "--frame-every",
            str(args.frame_every),
            "--fps",
            str(args.fps),
            "--device",
            device,
            "--target-safe-base",
            method["target_safe_base"],
            "--target-base-speed",
            str(args.target_base_speed),
            "--baseline-policies",
            method.get("baseline_policies", args.baseline_policies),
            "--out-dir",
            str(out_dir),
            "--safe",
            "--safe-blend",
            str(method["safe_blend"]),
            "--unsafe-blend",
            str(method["unsafe_blend"]),
            "--no-gif",
            "--no-trace",
        ]
        if not method.get("hard_shield", False):
            cmd.append("--disable-hard-shield")
        code, output = run_command(cmd)
        log_path.write_text(output, encoding="utf-8")
        if code != 0:
            return {
                "method": method_name,
                "seed": seed,
                "status": "RUN_FAIL",
                "summary": str(summary_path),
                "log": str(log_path),
                "log_tail": output[-4000:],
            }
    summary = load_json(summary_path)
    target = int(summary["target_agent"])
    track_tiles = max(int(summary["track_tiles"]), 1)
    target_progress = float(summary["tile_visited_count"][target] / track_tiles)
    max_other_progress = max(
        float(count / track_tiles)
        for agent, count in enumerate(summary["tile_visited_count"])
        if agent != target
    )
    first_ahead = summary.get("first_ahead_step")
    score = (
        args.progress_weight * target_progress
        - args.grass_weight * float(summary["grass_rate"][target])
        - args.rank_penalty * max(0, int(summary["target_final_rank_by_tiles"]) - 1)
        + args.first_ahead_bonus * int(first_ahead is not None)
        + args.margin_weight * max(0.0, target_progress - max_other_progress)
    )
    return {
        "method": method_name,
        "method_key": method["method_key"],
        "model_path": model_path,
        "seed": seed,
        "status": "PASS",
        "summary": str(summary_path),
        "log": str(log_path),
        "probe_score": score,
        "probe_progress": target_progress,
        "probe_grass": float(summary["grass_rate"][target]),
        "probe_rank": int(summary["target_final_rank_by_tiles"]),
        "probe_first_ahead_step": first_ahead,
        "probe_steps_run": int(summary["steps_run"]),
    }


def load_full_rows(root, method_names, suite_paths):
    rows = {}
    suites = {}
    for suite_name, rel_path in suite_paths.items():
        path = root / rel_path
        if path.exists():
            suites[suite_name] = load_json(path)
    for method_name in method_names:
        method = METHODS[method_name]
        suite = suites[method["suite"]]
        full_method = method.get("full_method", method_name)
        for row in suite["rows"]:
            if row["method"] == full_method:
                rows[(method_name, row["seed"])] = row
    return rows


def priority_map(value):
    items = [item.strip() for item in value.split(",") if item.strip()]
    return {name: len(items) - idx for idx, name in enumerate(items)}


def main():
    parser = argparse.ArgumentParser(description="Run short online probes and select a portfolio method.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    parser.add_argument("--out-dir", default="")
    parser.add_argument("--model-path", default="outputs/paper_multicar_overtake_20260618/models/graph_bc/graph_bc.graph.pt")
    parser.add_argument("--baseline-model-dir", default="outputs/torch_dlc_full_lap_seed01/seed_1/models")
    parser.add_argument("--methods", default="lane_base_only,overtake_base_only,graph_adaptive_shield")
    parser.add_argument("--seeds", default="3,7,11,17,23,29,31,37,41,43")
    parser.add_argument("--full-suite-main", default="")
    parser.add_argument("--full-suite-adaptive", default="")
    parser.add_argument("--full-suite-expert", default="")
    parser.add_argument("--full-suite-barrier", default="")
    parser.add_argument("--full-suite-recovery-expert", default="")
    parser.add_argument("--full-suite-dagger-v2", default="")
    parser.add_argument("--full-suite-dagger-v2-more-graph", default="")
    parser.add_argument("--full-suite-heldout3-traffic-adaptive-conservative", default="")
    parser.add_argument(
        "--method-model-paths",
        default="",
        help="Optional comma-separated NAME=PATH overrides for methods that use different graph actors.",
    )
    parser.add_argument("--devices", default="cuda:0")
    parser.add_argument("--parallel", type=int, default=1)
    parser.add_argument("--num-agents", type=int, default=4)
    parser.add_argument("--gap-tiles", type=int, default=22)
    parser.add_argument("--lateral-spacing", type=float, default=0.0)
    parser.add_argument("--probe-steps", type=int, default=450)
    parser.add_argument("--frame-every", type=int, default=20)
    parser.add_argument("--fps", type=int, default=12)
    parser.add_argument("--target-base-speed", type=float, default=22.0)
    parser.add_argument("--baseline-policies", default="telemetry_cruise,telemetry_yield,telemetry_lane")
    parser.add_argument("--table-prefix", default="portfolio_probe_selector")
    parser.add_argument("--progress-weight", type=float, default=1.0)
    parser.add_argument("--grass-weight", type=float, default=1.75)
    parser.add_argument("--rank-penalty", type=float, default=0.45)
    parser.add_argument("--first-ahead-bonus", type=float, default=0.10)
    parser.add_argument("--margin-weight", type=float, default=0.05)
    parser.add_argument("--tie-break-priority", default="dagger_v2_graph_expert_gate_more_graph,dagger_v2_graph_expert_gate_shield,expert_recovery_only,expert_barrier_only,expert_gate_only,graph_adaptive_shield,overtake_base_only,lane_base_only")
    parser.add_argument("--skip-existing", action="store_true")
    args = parser.parse_args()

    root = Path(args.root)
    if not args.out_dir:
        args.out_dir = str(root / "evaluations" / "portfolio_probe_selector")
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    method_names = parse_csv(args.methods)
    unknown = [name for name in method_names if name not in METHODS]
    if unknown:
        raise ValueError(f"unknown methods: {unknown}; choices={sorted(METHODS)}")
    seeds = parse_int_csv(args.seeds)
    devices = parse_csv(args.devices) or ["cuda:0"]
    priority = priority_map(args.tie_break_priority)
    args.method_model_paths = parse_mapping_csv(args.method_model_paths)

    jobs = []
    for method_index, method_name in enumerate(method_names):
        for seed_index, seed in enumerate(seeds):
            jobs.append((method_name, seed, devices[(method_index + seed_index) % len(devices)]))

    probe_rows = []
    workers = max(1, min(args.parallel, len(jobs))) if jobs else 1
    if workers == 1:
        for method_name, seed, device in jobs:
            probe_rows.append(run_probe(args, method_name, seed, device))
    else:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(run_probe, args, method_name, seed, device): (method_name, seed)
                for method_name, seed, device in jobs
            }
            for future in as_completed(futures):
                probe_rows.append(future.result())

    suite_paths = dict(DEFAULT_SUITE_PATHS)
    if args.full_suite_main:
        suite_paths["main"] = args.full_suite_main
    if args.full_suite_adaptive:
        suite_paths["adaptive"] = args.full_suite_adaptive
    if args.full_suite_expert:
        suite_paths["expert"] = args.full_suite_expert
    if args.full_suite_barrier:
        suite_paths["barrier"] = args.full_suite_barrier
    if args.full_suite_recovery_expert:
        suite_paths["recovery_expert"] = args.full_suite_recovery_expert
    if args.full_suite_dagger_v2:
        suite_paths["dagger_v2"] = args.full_suite_dagger_v2
    if args.full_suite_dagger_v2_more_graph:
        suite_paths["dagger_v2_more_graph"] = args.full_suite_dagger_v2_more_graph
    if args.full_suite_heldout3_traffic_adaptive_conservative:
        suite_paths["heldout3_traffic_adaptive_conservative"] = (
            args.full_suite_heldout3_traffic_adaptive_conservative
        )
    full_rows = load_full_rows(root, method_names, suite_paths)
    decisions = []
    for seed in seeds:
        candidates = [row for row in probe_rows if row["seed"] == seed and row["status"] == "PASS"]
        selected = max(
            candidates,
            key=lambda row: (row["probe_score"], priority.get(row["method"], 0)),
        )
        full = full_rows[(selected["method"], seed)]
        oracle_method = max(
            method_names,
            key=lambda method: (
                full_rows[(method, seed)]["validation_status"] == "PASS",
                priority.get(method, 0),
            ),
        )
        oracle = full_rows[(oracle_method, seed)]
        decisions.append(
            {
                "seed": seed,
                "selected_method": selected["method"],
                "selected_method_key": selected["method_key"],
                "selected_model_path": selected["model_path"],
                "selected_full_status": full["validation_status"],
                "selected_full_progress": full["target_tile_progress"],
                "selected_full_grass": full["target_grass_rate"],
                "selected_full_rank": full["target_final_rank_by_tiles"],
                "probe_score": selected["probe_score"],
                "probe_progress": selected["probe_progress"],
                "probe_grass": selected["probe_grass"],
                "probe_rank": selected["probe_rank"],
                "oracle_method": METHODS[oracle_method]["method_key"],
                "oracle_status": oracle["validation_status"],
            }
        )

    pass_count = sum(row["selected_full_status"] == "PASS" for row in decisions)
    oracle_pass_count = sum(row["oracle_status"] == "PASS" for row in decisions)
    report = {
        "root": str(root),
        "out_dir": str(out_dir),
        "selector": "short online probe selector",
        "probe_steps": args.probe_steps,
        "suite_paths": suite_paths,
        "score_weights": {
            "progress_weight": args.progress_weight,
            "grass_weight": args.grass_weight,
            "rank_penalty": args.rank_penalty,
            "first_ahead_bonus": args.first_ahead_bonus,
            "margin_weight": args.margin_weight,
        },
        "tie_break_priority": priority,
        "methods": method_names,
        "method_model_paths": {
            method_name: args.method_model_paths.get(method_name) or METHODS[method_name].get("model_path") or args.model_path
            for method_name in method_names
        },
        "seeds": seeds,
        "n": len(decisions),
        "pass_count": pass_count,
        "pass_rate": pass_count / len(decisions) if decisions else None,
        "oracle_pass_count": oracle_pass_count,
        "oracle_pass_rate": oracle_pass_count / len(decisions) if decisions else None,
        "probe_rows": probe_rows,
        "decisions": decisions,
        "note": (
            "Each candidate method is run only for a short online probe. Selection uses early progress, grass rate, "
            "rank, and first-ahead evidence, then performance is measured against the locked full-length suite."
        ),
    }
    summary_path = out_dir / "portfolio_probe_selector_summary.json"
    summary_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    table_dir = root / "tables"
    table_dir.mkdir(parents=True, exist_ok=True)
    out_json = table_dir / f"{args.table_prefix}.json"
    out_csv = table_dir / f"{args.table_prefix}_rows.csv"
    out_md = table_dir / f"{args.table_prefix}.md"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    with out_csv.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "seed",
            "selected_method",
            "selected_full_status",
            "selected_full_progress",
            "selected_full_grass",
            "selected_full_rank",
            "probe_score",
            "probe_progress",
            "probe_grass",
            "probe_rank",
            "oracle_method",
            "oracle_status",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in decisions:
            writer.writerow({key: row[key] for key in fieldnames})

    lines = [
        "# Portfolio Probe Selector Report",
        "",
        f"- Probe steps: {args.probe_steps}",
        f"- Methods: {', '.join(method_names)}",
        f"- Pass rate against reference full rollouts: {pass_count}/{len(decisions)}",
        f"- Oracle upper bound over same methods: {oracle_pass_count}/{len(decisions)}",
        "",
        "| seed | selected | full status | probe score | oracle | oracle status |",
        "|---:|---|---|---:|---|---|",
    ]
    for row in decisions:
        lines.append(
            f"| {row['seed']} | {row['selected_method_key']} | {row['selected_full_status']} | "
            f"{row['probe_score']:.3f} | {row['oracle_method']} | {row['oracle_status']} |"
        )
    lines.extend(["", "## Note", "", report["note"], ""])
    out_md.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"summary": str(summary_path), "json": str(out_json), "markdown": str(out_md), "csv": str(out_csv)}, indent=2))


if __name__ == "__main__":
    main()
