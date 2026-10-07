#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path


DEFAULT_ALGORITHMS = "v6_runtime_dynamic_neighborhood_safe,dlc_world_original"

FINGERPRINT_FIELDS = [
    "algorithm",
    "seed",
    "num_agents",
    "target_agent",
    "track_path",
    "traffic_profile",
    "observation_type",
    "steps_run",
    "finish_step",
    "target_final_rank",
    "rank_gain",
    "target_completed_lap",
    "any_completed_lap",
    "target_progress",
    "overtake_success",
    "overtake_count",
    "on_track_overtake_count",
    "elegant_overtake_count",
    "time_to_first_overtake",
    "overtake_start_to_complete_time",
    "target_grass_rate",
    "target_backward_rate",
    "collision_or_contact_proxy",
    "grass_excursion_count",
    "unrecovered_grass_excursion_count",
]

FLOAT_FIELDS = {
    "target_progress",
    "target_grass_rate",
    "target_backward_rate",
    "collision_or_contact_proxy",
}


def write_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")
    return str(path)


def write_json(path, data):
    return write_text(path, json.dumps(data, ensure_ascii=False, indent=2))


def write_csv(path, rows, fields):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return str(path)


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def normalize_value(key, value):
    if key in FLOAT_FIELDS and value is not None:
        try:
            return round(float(value), 8)
        except Exception:
            return value
    if isinstance(value, list):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return value


def fingerprint(summary):
    data = {key: normalize_value(key, summary.get(key)) for key in FINGERPRINT_FIELDS}
    payload = json.dumps(data, ensure_ascii=False, sort_keys=True)
    return data, hashlib.sha256(payload.encode("utf-8")).hexdigest()


def run_eval(args, repeat_dir):
    command = [
        args.python,
        "scripts/run_tits_dynamic_graph_evaluation.py",
        "--config",
        args.config,
        "--out-dir",
        str(repeat_dir),
        "--algorithms",
        args.algorithms,
        "--num-agents",
        str(args.num_agents),
        "--seed",
        str(args.seed),
        "--max-steps",
        str(args.max_steps),
        "--finish-mode",
        "steps",
        "--observation-type",
        "telemetry_dynamic",
        "--max-neighbors",
        str(args.max_neighbors),
        "--device",
        args.device,
        "--traffic-profile",
        args.traffic_profile,
        "--no-gif",
    ]
    if args.track_path:
        command.extend(["--track-path", args.track_path])
    proc = subprocess.run(command, cwd=args.root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return {
        "command": " ".join(command),
        "returncode": proc.returncode,
        "stdout_tail": proc.stdout[-4000:],
        "stderr_tail": proc.stderr[-4000:],
    }


def collect_summaries(repeat_dir):
    rows = {}
    summary_dir = repeat_dir / "summaries"
    for path in sorted(summary_dir.glob("*.summary.json")):
        data = load_json(path)
        rows[data.get("algorithm")] = {"path": path, "summary": data}
    return rows


def build_compare_rows(rep_a, rep_b):
    algorithms = sorted(set(rep_a) | set(rep_b))
    rows = []
    detail_rows = []
    for algorithm in algorithms:
        a = rep_a.get(algorithm)
        b = rep_b.get(algorithm)
        if not a or not b:
            rows.append(
                {
                    "algorithm": algorithm,
                    "repeat_1_summary": str(a["path"]) if a else "",
                    "repeat_2_summary": str(b["path"]) if b else "",
                    "fingerprint_1": "",
                    "fingerprint_2": "",
                    "match": False,
                    "mismatch_fields": "missing_summary",
                }
            )
            continue
        fp_data_a, fp_a = fingerprint(a["summary"])
        fp_data_b, fp_b = fingerprint(b["summary"])
        mismatches = [key for key in FINGERPRINT_FIELDS if fp_data_a.get(key) != fp_data_b.get(key)]
        rows.append(
            {
                "algorithm": algorithm,
                "repeat_1_summary": str(a["path"]),
                "repeat_2_summary": str(b["path"]),
                "fingerprint_1": fp_a,
                "fingerprint_2": fp_b,
                "match": not mismatches,
                "mismatch_fields": ";".join(mismatches),
            }
        )
        for key in FINGERPRINT_FIELDS:
            detail_rows.append(
                {
                    "algorithm": algorithm,
                    "field": key,
                    "repeat_1_value": fp_data_a.get(key),
                    "repeat_2_value": fp_data_b.get(key),
                    "match": fp_data_a.get(key) == fp_data_b.get(key),
                }
            )
    return rows, detail_rows


def build_markdown(report):
    summary = report["summary"]
    lines = [
        "# T-ITS Determinism Smoke Audit",
        "",
        "该审计用同一 seed、同一配置短程运行两次在线评估，并比较关键 summary 指纹。它只验证当前环境下的评估入口和确定性 smoke 行为，不作为论文性能结果，也不替代 240-run confirmatory matrix。",
        "",
        "## Summary",
        "",
    ]
    for key, value in summary.items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Compared Fields",
            "",
            ", ".join(f"`{field}`" for field in FINGERPRINT_FIELDS),
            "",
            "## Result",
            "",
            "| Algorithm | Match | Mismatch fields |",
            "|---|---:|---|",
        ]
    )
    for row in report["comparison_rows"]:
        lines.append(f"| {row['algorithm']} | {row['match']} | {row['mismatch_fields']} |")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- 该审计使用短程 `finish-mode steps` smoke run，不用于报告算法性能。",
            "- `compute_latency_ms`、GIF 路径、trace 路径、stdout/stderr 等非确定性或路径相关字段不进入 fingerprint。",
            "- 若 CUDA、Box2D、依赖版本或环境发生变化，应重新运行该审计。",
            "",
            "## Regeneration Command",
            "",
            "```bash",
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_determinism_smoke_audit.py --out-dir outputs/tits_dynamic_graph/tits_determinism_smoke_audit",
            "```",
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Run a short deterministic smoke audit for T-ITS online evaluation.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/tits_determinism_smoke_audit")
    parser.add_argument("--python", default="/home/itrc/.conda/envs/vlm_planner/bin/python")
    parser.add_argument("--config", default="configs/tits_dynamic_graph_experiments.json")
    parser.add_argument("--algorithms", default=DEFAULT_ALGORITHMS)
    parser.add_argument("--num-agents", type=int, default=4)
    parser.add_argument("--seed", type=int, default=3)
    parser.add_argument("--max-steps", type=int, default=80)
    parser.add_argument("--max-neighbors", type=int, default=3)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--traffic-profile", default="slow_traffic")
    parser.add_argument("--track-path", default="")
    args = parser.parse_args()

    args.root = Path(args.root).resolve()
    out_dir = args.root / args.out_dir
    materials = out_dir / "materials"
    tables = out_dir / "tables"
    runs = out_dir / "runs"
    if runs.exists():
        shutil.rmtree(runs)
    materials.mkdir(parents=True, exist_ok=True)
    tables.mkdir(parents=True, exist_ok=True)
    runs.mkdir(parents=True, exist_ok=True)

    run_logs = []
    for idx in [1, 2]:
        repeat_dir = runs / f"repeat_{idx}"
        repeat_dir.mkdir(parents=True, exist_ok=True)
        log = run_eval(args, repeat_dir)
        log["repeat"] = idx
        log["out_dir"] = str(repeat_dir)
        run_logs.append(log)
    hard_errors = [log for log in run_logs if log["returncode"] != 0]
    rep_a = collect_summaries(runs / "repeat_1") if not hard_errors else {}
    rep_b = collect_summaries(runs / "repeat_2") if not hard_errors else {}
    comparison_rows, detail_rows = build_compare_rows(rep_a, rep_b) if not hard_errors else ([], [])
    all_match = bool(comparison_rows) and all(row["match"] for row in comparison_rows)
    expected_algorithms = [item.strip() for item in args.algorithms.split(",") if item.strip()]
    summary = {
        "status": "pass" if not hard_errors and all_match and len(comparison_rows) == len(expected_algorithms) else "review_required",
        "expected_algorithms": expected_algorithms,
        "compared_algorithms": len(comparison_rows),
        "all_fingerprints_match": all_match,
        "hard_error_count": len(hard_errors),
        "num_agents": args.num_agents,
        "seed": args.seed,
        "max_steps": args.max_steps,
        "device": args.device,
        "traffic_profile": args.traffic_profile,
        "note": "Short smoke-only determinism check; not a paper-scale result.",
    }
    report = {
        "status": summary["status"],
        "summary": summary,
        "run_logs": run_logs,
        "comparison_rows": comparison_rows,
        "detail_rows": detail_rows,
    }
    paths = {
        "audit_md": write_text(materials / "DETERMINISM_SMOKE_AUDIT.md", build_markdown(report)),
        "audit_json": write_json(materials / "DETERMINISM_SMOKE_AUDIT.json", report),
        "qa_json": write_json(
            materials / "DETERMINISM_SMOKE_QA.json",
            {
                "status": summary["status"],
                "checks": {
                    "runs_completed": len(hard_errors) == 0,
                    "all_fingerprints_match": all_match,
                    "expected_algorithm_count": len(comparison_rows) == len(expected_algorithms),
                },
                "summary": summary,
            },
        ),
        "comparison_csv": write_csv(
            tables / "determinism_smoke_comparison.csv",
            comparison_rows,
            ["algorithm", "repeat_1_summary", "repeat_2_summary", "fingerprint_1", "fingerprint_2", "match", "mismatch_fields"],
        ),
        "field_detail_csv": write_csv(
            tables / "determinism_smoke_field_details.csv",
            detail_rows,
            ["algorithm", "field", "repeat_1_value", "repeat_2_value", "match"],
        ),
        "run_log_csv": write_csv(
            tables / "determinism_smoke_run_log.csv",
            run_logs,
            ["repeat", "out_dir", "command", "returncode", "stdout_tail", "stderr_tail"],
        ),
    }
    manifest = {
        "status": summary["status"],
        "out_dir": args.out_dir,
        "summary": summary,
        "paths": paths,
    }
    manifest_path = write_json(out_dir / "tits_determinism_smoke_audit_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, "status": summary["status"], "summary": summary}, ensure_ascii=False, indent=2))
    if summary["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
