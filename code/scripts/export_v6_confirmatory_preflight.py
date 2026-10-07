#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import hashlib
import json
import shutil
from pathlib import Path


DEFAULT_ALGORITHMS = (
    "v6_runtime_dynamic_neighborhood,"
    "v6_runtime_dynamic_neighborhood_safe,"
    "quality_proposal_dlc_world_v1,"
    "dlc_world_original,"
    "dlc_world_balanced,"
    "dlc_world_safety,"
    "dlc_world_fast,"
    "rule_expert_gate"
)


def sha256_file(path):
    path = Path(path)
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def split_items(value):
    return [item.strip() for item in str(value or "").split(",") if item.strip()]


def ensure_dir(path):
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def algorithm_map(config):
    return {item["name"]: item for item in config.get("algorithms", [])}


def model_paths_for_algorithm(item):
    paths = []
    policy = item.get("policy") or item.get("model_path")
    if policy and not str(policy).startswith("telemetry_"):
        paths.append(("policy_or_model", policy))
    quality = item.get("quality_proposal_path")
    if quality:
        paths.append(("quality_proposal", quality))
    return paths


def build_case_rows(config, algorithms, matrix_name, devices, args):
    reporting_root = Path(config.get("reporting", {}).get("output_dir", "outputs/tits_dynamic_graph"))
    output_root = reporting_root / matrix_name
    python = config.get("python", "python")
    max_neighbors = config.get("dynamic_graph", {}).get("max_neighbors", args.max_neighbors)
    rows = []
    case_id = 0
    for benchmark in config.get("benchmark_matrix", []):
        track = benchmark["track"]
        track_path = "" if track == "procedural" else track
        for num_agents in benchmark.get("agent_counts", []):
            for seed in benchmark.get("seeds", []):
                case_id += 1
                device = devices[(case_id - 1) % len(devices)] if devices else args.device
                out_dir = output_root / benchmark["name"] / f"n{num_agents}" / f"seed{seed}"
                command = [
                    python,
                    "scripts/run_tits_dynamic_graph_evaluation.py",
                    "--config",
                    args.config,
                    "--out-dir",
                    str(out_dir),
                    "--num-agents",
                    str(num_agents),
                    "--seed",
                    str(seed),
                    "--max-steps",
                    str(args.max_steps),
                    "--finish-mode",
                    args.finish_mode,
                    "--observation-type",
                    args.observation_type,
                    "--max-neighbors",
                    str(max_neighbors),
                    "--device",
                    device,
                    "--traffic-profile",
                    args.traffic_profile,
                    "--frame-every",
                    str(args.frame_every),
                    "--fps",
                    str(args.fps),
                    "--algorithms",
                    ",".join(algorithms),
                ]
                if track_path:
                    command.extend(["--track-path", track_path])
                if args.no_gif:
                    command.append("--no-gif")
                if args.first_person_gif:
                    command.append("--first-person-gif")
                rows.append(
                    {
                        "case_id": case_id,
                        "benchmark": benchmark["name"],
                        "track": track,
                        "track_path": track_path or "procedural",
                        "num_agents": int(num_agents),
                        "seed": int(seed),
                        "device": device,
                        "out_dir": str(out_dir),
                        "command": " ".join(command),
                    }
                )
    return rows


def cuda_inventory():
    info = {
        "torch_importable": False,
        "cuda_available": False,
        "cuda_device_count": 0,
        "cuda_devices": [],
        "nvidia_smi_found": bool(shutil.which("nvidia-smi")),
    }
    try:
        import torch

        info["torch_importable"] = True
        info["cuda_available"] = bool(torch.cuda.is_available())
        info["cuda_device_count"] = int(torch.cuda.device_count()) if info["cuda_available"] else 0
        if info["cuda_available"]:
            info["cuda_devices"] = [
                {"index": idx, "name": torch.cuda.get_device_name(idx)}
                for idx in range(info["cuda_device_count"])
            ]
    except Exception as exc:
        info["torch_error"] = repr(exc)
    return info


def build_checks(config, algorithms, case_rows, devices, matrix_name):
    amap = algorithm_map(config)
    checks = []

    def add(name, status, detail, severity="required"):
        checks.append(
            {
                "name": name,
                "status": "pass" if status else "fail",
                "severity": severity,
                "detail": detail,
            }
        )

    add("config_exists", True, "Config was loaded.")
    add("run_evaluation_script_exists", Path("scripts/run_tits_dynamic_graph_evaluation.py").exists(), "Online evaluation script must exist.")
    add("online_suite_script_exists", Path("scripts/run_tits_dynamic_graph_online_suite.py").exists(), "Batch online suite script must exist.")
    add("summarizer_script_exists", Path("scripts/summarize_tits_dynamic_graph_online.py").exists(), "Summary script must exist.")
    add("matrix_name_not_empty", bool(matrix_name), f"matrix_name={matrix_name!r}")
    add(
        "benchmark_matrix_nonempty",
        bool(config.get("benchmark_matrix")),
        f"benchmark_count={len(config.get('benchmark_matrix', []))}",
    )
    add("case_rows_nonempty", bool(case_rows), f"case_count={len(case_rows)}")

    for name in algorithms:
        add(f"algorithm_registered::{name}", name in amap, "Algorithm must be present in config.")
        if name not in amap:
            continue
        for role, path in model_paths_for_algorithm(amap[name]):
            add(
                f"artifact_exists::{name}::{role}",
                Path(path).exists(),
                path,
            )

    for benchmark in config.get("benchmark_matrix", []):
        track = benchmark.get("track", "")
        if track != "procedural":
            add(f"track_exists::{track}", Path(track).exists(), track)

    add("device_list_nonempty", bool(devices), ",".join(devices))
    inv = cuda_inventory()
    requested_cuda = [d for d in devices if str(d).startswith("cuda")]
    add(
        "cuda_available_for_requested_devices",
        (not requested_cuda) or (inv["cuda_available"] and inv["cuda_device_count"] >= len(set(requested_cuda))),
        json.dumps(inv, ensure_ascii=False),
        severity="recommended",
    )
    return checks, inv


def write_csv(rows, path, fields):
    with Path(path).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(report, path):
    summary = report["summary"]
    lines = [
        "# v6 Confirmatory Experiment Preflight",
        "",
        "## Summary",
        "",
        f"- Status: `{summary['status']}`",
        f"- Matrix name: `{summary['matrix_name']}`",
        f"- Case commands: {summary['case_count']}",
        f"- Algorithm count: {summary['algorithm_count']}",
        f"- Planned algorithm-runs: {summary['planned_algorithm_runs']}",
        f"- Required failures: {summary['required_fail_count']}",
        f"- Recommended failures: {summary['recommended_fail_count']}",
        "",
        "## Algorithms",
        "",
    ]
    for item in report["algorithms"]:
        budget = item.get("budget") or "--"
        lines.append(f"- `{item['name']}`：{item['label_cn']}；kind={item['kind']}；budget={budget}")
    lines.extend(["", "## Checks", "", "| Check | Status | Severity | Detail |", "|---|---|---|---|"])
    for row in report["checks"]:
        detail = str(row["detail"]).replace("|", "\\|")
        lines.append(f"| {row['name']} | {row['status']} | {row['severity']} | {detail} |")
    lines.extend(
        [
            "",
            "## Run Command",
            "",
            "```bash",
            report["recommended_run_command"],
            "```",
            "",
            "## Summary Command",
            "",
            "```bash",
            report["recommended_summary_command"],
            "```",
            "",
            "## Boundary",
            "",
            "This preflight is static. It registers and audits the confirmatory run plan but does not execute expensive online rollouts.",
        ]
    )
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export v6 confirmatory experiment preflight package.")
    parser.add_argument("--config", default="configs/tits_dynamic_graph_experiments.json")
    parser.add_argument("--matrix-name", default="v6_confirmatory_matrix")
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/v6_confirmatory_preflight")
    parser.add_argument("--algorithms", default=DEFAULT_ALGORITHMS)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--devices", default="cuda:0,cuda:1,cuda:2,cuda:3")
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--max-steps", type=int, default=2200)
    parser.add_argument("--finish-mode", choices=["any", "target", "all", "env_done", "steps"], default="any")
    parser.add_argument("--observation-type", choices=["telemetry", "telemetry_dynamic"], default="telemetry_dynamic")
    parser.add_argument("--traffic-profile", choices=["slow_traffic", "mixed_traffic"], default="slow_traffic")
    parser.add_argument("--max-neighbors", type=int, default=3)
    parser.add_argument("--frame-every", type=int, default=12)
    parser.add_argument("--fps", type=int, default=12)
    parser.add_argument("--no-gif", action="store_true", default=True)
    parser.add_argument("--first-person-gif", action="store_true")
    args = parser.parse_args()

    config_path = Path(args.config)
    config = load_json(config_path)
    out_dir = ensure_dir(args.out_dir)
    tables_dir = ensure_dir(out_dir / "tables")
    materials_dir = ensure_dir(out_dir / "materials")
    algorithms = split_items(args.algorithms)
    devices = split_items(args.devices) or [args.device]
    case_rows = build_case_rows(config, algorithms, args.matrix_name, devices, args)
    checks, inv = build_checks(config, algorithms, case_rows, devices, args.matrix_name)
    amap = algorithm_map(config)

    algorithm_rows = []
    for name in algorithms:
        item = amap.get(name, {})
        budget = ""
        if item.get("planner_horizon") and item.get("planner_candidates"):
            budget = f"{item['planner_horizon']}x{item['planner_candidates']}"
        algorithm_rows.append(
            {
                "name": name,
                "label_cn": item.get("label_cn", name),
                "kind": item.get("kind", ""),
                "budget": budget,
                "neighbor_selection_mode": item.get("neighbor_selection_mode", ""),
                "model_path": item.get("model_path") or item.get("policy", ""),
                "quality_proposal_path": item.get("quality_proposal_path", ""),
            }
        )

    required_fail_count = sum(row["status"] == "fail" and row["severity"] == "required" for row in checks)
    recommended_fail_count = sum(row["status"] == "fail" and row["severity"] == "recommended" for row in checks)
    status = "pass" if required_fail_count == 0 else "fail"

    run_command = (
        f"{config.get('python', 'python')} scripts/run_tits_dynamic_graph_online_suite.py "
        f"--config {args.config} --matrix-name {args.matrix_name} --mode run "
        f"--algorithms {','.join(algorithms)} --devices {','.join(devices)} --jobs {args.jobs} "
        f"--max-steps {args.max_steps} --finish-mode {args.finish_mode} --no-gif"
    )
    summary_command = (
        f"{config.get('python', 'python')} scripts/summarize_tits_dynamic_graph_online.py "
        f"--input-dir outputs/tits_dynamic_graph/{args.matrix_name} "
        f"--out-dir outputs/tits_dynamic_graph/{args.matrix_name}_summary --bootstrap 5000 --seed 2026"
    )

    config_snapshot = materials_dir / "tits_dynamic_graph_experiments.snapshot.json"
    config_snapshot.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    report = {
        "title": "v6 confirmatory experiment preflight",
        "config": str(config_path),
        "config_sha256": sha256_file(config_path),
        "config_snapshot": str(config_snapshot),
        "summary": {
            "status": status,
            "matrix_name": args.matrix_name,
            "case_count": len(case_rows),
            "algorithm_count": len(algorithms),
            "planned_algorithm_runs": len(case_rows) * len(algorithms),
            "required_fail_count": required_fail_count,
            "recommended_fail_count": recommended_fail_count,
            "jobs": int(args.jobs),
            "devices": devices,
        },
        "cuda_inventory": inv,
        "algorithms": algorithm_rows,
        "checks": checks,
        "case_rows_csv": str(tables_dir / "v6_confirmatory_case_commands.csv"),
        "algorithm_rows_csv": str(tables_dir / "v6_confirmatory_algorithms.csv"),
        "checks_csv": str(tables_dir / "v6_confirmatory_preflight_checks.csv"),
        "recommended_run_command": run_command,
        "recommended_summary_command": summary_command,
        "boundary": "Static preflight only; no expensive online rollouts are executed.",
    }

    write_csv(case_rows, tables_dir / "v6_confirmatory_case_commands.csv", list(case_rows[0].keys()) if case_rows else [])
    write_csv(algorithm_rows, tables_dir / "v6_confirmatory_algorithms.csv", list(algorithm_rows[0].keys()) if algorithm_rows else [])
    write_csv(checks, tables_dir / "v6_confirmatory_preflight_checks.csv", ["name", "status", "severity", "detail"])
    (out_dir / "v6_confirmatory_preflight.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    write_markdown(report, out_dir / "v6_confirmatory_preflight.md")
    print(json.dumps({"preflight": str(out_dir / "v6_confirmatory_preflight.json"), "status": status}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
