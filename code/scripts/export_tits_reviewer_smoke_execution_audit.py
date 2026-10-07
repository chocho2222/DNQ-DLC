#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import hashlib
import json
from pathlib import Path


EXPECTED_ALGORITHMS = ["dlc_world_original", "v6_runtime_dynamic_neighborhood_safe"]
EXPECTED_SEED = 3
EXPECTED_NUM_AGENTS = 4
EXPECTED_FINISH_STEP = 120
EXPECTED_TRAFFIC_PROFILE = "slow_traffic"


def read_json(path):
    path = Path(path)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path, chunk_size=1024 * 1024):
    path = Path(path)
    if not path.exists() or not path.is_file():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


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


def collect_summary_rows(smoke_dir):
    rows = []
    summary_dir = smoke_dir / "summaries"
    for path in sorted(summary_dir.glob("*.summary.json")):
        data = read_json(path)
        rows.append(
            {
                "summary_path": path.as_posix(),
                "algorithm": data.get("algorithm", ""),
                "seed": data.get("seed", ""),
                "num_agents": data.get("num_agents", ""),
                "finish_step": data.get("finish_step", ""),
                "steps_run": data.get("steps_run", ""),
                "traffic_profile": data.get("traffic_profile", ""),
                "observation_type": data.get("observation_type", ""),
                "target_grass_rate": data.get("target_grass_rate", ""),
                "overtake_success_rate": data.get("overtake_success_rate", ""),
                "on_track_overtake_rate": data.get("on_track_overtake_rate", ""),
                "elegant_overtake_rate": data.get("elegant_overtake_rate", ""),
                "compute_latency_ms": data.get("compute_latency_ms", ""),
                "trace_path": data.get("trace_path", ""),
                "summary_sha256": sha256_file(path),
            }
        )
    return rows


def collect_file_rows(smoke_dir):
    candidates = [
        smoke_dir / "online_suite_n4_seed3.json",
        smoke_dir / "tables" / "online_metrics_n4_seed3.csv",
        smoke_dir / "figures" / "figure_tits_dynamic_graph_online_overtake_summary.svg",
        smoke_dir / "figures" / "figure_tits_dynamic_graph_online_overtake_summary.pdf",
        smoke_dir / "figures" / "figure_tits_dynamic_graph_online_overtake_summary.png",
        smoke_dir / "figures" / "figure_tits_dynamic_graph_online_overtake_summary.tiff",
    ]
    rows = []
    for path in candidates:
        rows.append(
            {
                "path": path.as_posix(),
                "exists": path.exists() and path.is_file(),
                "size_bytes": path.stat().st_size if path.exists() and path.is_file() else 0,
                "sha256": sha256_file(path),
                "role": "reviewer_smoke_output",
            }
        )
    return rows


def build_checks(summary_rows, file_rows):
    algorithms = sorted(row["algorithm"] for row in summary_rows)
    missing_expected = sorted(set(EXPECTED_ALGORITHMS) - set(algorithms))
    unexpected = sorted(set(algorithms) - set(EXPECTED_ALGORITHMS))
    identity_ok = all(
        int(row["seed"] or -1) == EXPECTED_SEED
        and int(row["num_agents"] or -1) == EXPECTED_NUM_AGENTS
        and int(row["finish_step"] or -1) == EXPECTED_FINISH_STEP
        and row["traffic_profile"] == EXPECTED_TRAFFIC_PROFILE
        for row in summary_rows
    )
    summary_hashes_ok = all(row["summary_sha256"] for row in summary_rows)
    core_files_ok = all(row["exists"] and row["size_bytes"] > 0 for row in file_rows[:3])
    return [
        {
            "check_id": "RS01_expected_summary_count",
            "status": "pass" if len(summary_rows) == len(EXPECTED_ALGORITHMS) else "review_required",
            "expected": f"{len(EXPECTED_ALGORITHMS)} summaries",
            "observed": f"{len(summary_rows)} summaries",
            "interpretation": "Reviewer smoke should exercise both the current controller and the original DLC baseline.",
        },
        {
            "check_id": "RS02_expected_algorithms",
            "status": "pass" if not missing_expected and not unexpected else "review_required",
            "expected": ",".join(EXPECTED_ALGORITHMS),
            "observed": f"algorithms={','.join(algorithms)}; missing={','.join(missing_expected)}; unexpected={','.join(unexpected)}",
            "interpretation": "The smoke route should match the documented reviewer command.",
        },
        {
            "check_id": "RS03_identity_fields",
            "status": "pass" if summary_rows and identity_ok else "review_required",
            "expected": f"seed={EXPECTED_SEED}; num_agents={EXPECTED_NUM_AGENTS}; finish_step={EXPECTED_FINISH_STEP}; traffic={EXPECTED_TRAFFIC_PROFILE}",
            "observed": "; ".join(
                f"{row['algorithm']}: seed={row['seed']} n={row['num_agents']} finish={row['finish_step']} traffic={row['traffic_profile']}"
                for row in summary_rows
            ),
            "interpretation": "Smoke execution should remain a short environment/code-path check, not a paper-scale result.",
        },
        {
            "check_id": "RS04_summary_hashes",
            "status": "pass" if summary_rows and summary_hashes_ok else "review_required",
            "expected": "all summary JSON files have SHA256 fingerprints",
            "observed": f"fingerprinted={sum(1 for row in summary_rows if row['summary_sha256'])}/{len(summary_rows)}",
            "interpretation": "The latest smoke outputs can be independently identified without archiving large temporary files.",
        },
        {
            "check_id": "RS05_core_outputs_exist",
            "status": "pass" if core_files_ok else "review_required",
            "expected": "suite JSON, metrics CSV and SVG figure exist and are non-empty",
            "observed": "; ".join(f"{Path(row['path']).name}={row['exists']}:{row['size_bytes']}" for row in file_rows[:3]),
            "interpretation": "The reviewer smoke route produced the expected lightweight outputs.",
        },
    ]


def build_markdown(report):
    summary = report["summary"]
    lines = [
        "# T-ITS Reviewer Smoke Execution Audit",
        "",
        "该审计记录最近一次 reviewer smoke test 的真实执行结果。它只用于证明环境、导入、GPU/评估入口和短程在线评估路径能跑通，不作为论文性能结果。",
        "",
        "## Summary",
        "",
    ]
    for key, value in summary.items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Checks",
            "",
            "| Check | Status | Expected | Observed | Interpretation |",
            "|---|---|---|---|---|",
        ]
    )
    for row in report["checks"]:
        lines.append(f"| {row['check_id']} | {row['status']} | {row['expected']} | {row['observed']} | {row['interpretation']} |")
    lines.extend(
        [
            "",
            "## Summary Rows",
            "",
            "| Algorithm | Seed | Vehicles | Finish step | Grass rate | Success rate | Latency ms | Summary SHA256 |",
            "|---|---:|---:|---:|---:|---:|---:|---|",
        ]
    )
    for row in report["summary_rows"]:
        lines.append(
            f"| {row['algorithm']} | {row['seed']} | {row['num_agents']} | {row['finish_step']} | "
            f"{row['target_grass_rate']} | {row['overtake_success_rate']} | {row['compute_latency_ms']} | `{row['summary_sha256']}` |"
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- Smoke outputs live under `/tmp` by default and are not archived as formal benchmark evidence.",
            "- Formal performance claims must continue to cite the 240-run source data and confirmatory evidence pack.",
            "- Re-run `make tits-smoke` before this audit if the smoke directory has been removed or the environment changed.",
            "",
            "## Regeneration Commands",
            "",
            "```bash",
            "make tits-smoke",
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_reviewer_smoke_execution_audit.py --out-dir outputs/tits_dynamic_graph/tits_reviewer_smoke_execution_audit",
            "```",
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Audit the latest reviewer smoke execution outputs.")
    parser.add_argument("--smoke-dir", default="/tmp/tits_dynamic_graph_reviewer_smoke")
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/tits_reviewer_smoke_execution_audit")
    args = parser.parse_args()

    smoke_dir = Path(args.smoke_dir)
    out_dir = Path(args.out_dir)
    materials = out_dir / "materials"
    tables = out_dir / "tables"
    materials.mkdir(parents=True, exist_ok=True)
    tables.mkdir(parents=True, exist_ok=True)

    summary_rows = collect_summary_rows(smoke_dir)
    file_rows = collect_file_rows(smoke_dir)
    checks = build_checks(summary_rows, file_rows)
    issue_count = sum(1 for row in checks if row["status"] != "pass")
    status = "pass" if issue_count == 0 else "review_required"
    report = {
        "status": status,
        "out_dir": args.out_dir,
        "smoke_dir": smoke_dir.as_posix(),
        "summary": {
            "status": status,
            "smoke_dir": smoke_dir.as_posix(),
            "summary_count": len(summary_rows),
            "expected_summary_count": len(EXPECTED_ALGORITHMS),
            "algorithms": ",".join(sorted(row["algorithm"] for row in summary_rows)),
            "check_count": len(checks),
            "issue_count": issue_count,
            "boundary": "Smoke execution evidence only; not a paper-scale performance result.",
        },
        "checks": checks,
        "summary_rows": summary_rows,
        "file_rows": file_rows,
    }
    paths = {
        "audit_md": write_text(materials / "REVIEWER_SMOKE_EXECUTION_AUDIT.md", build_markdown(report)),
        "audit_json": write_json(materials / "REVIEWER_SMOKE_EXECUTION_AUDIT.json", report),
        "summary_rows_csv": write_csv(
            tables / "reviewer_smoke_summary_rows.csv",
            summary_rows,
            [
                "summary_path",
                "algorithm",
                "seed",
                "num_agents",
                "finish_step",
                "steps_run",
                "traffic_profile",
                "observation_type",
                "target_grass_rate",
                "overtake_success_rate",
                "on_track_overtake_rate",
                "elegant_overtake_rate",
                "compute_latency_ms",
                "trace_path",
                "summary_sha256",
            ],
        ),
        "file_rows_csv": write_csv(
            tables / "reviewer_smoke_file_rows.csv",
            file_rows,
            ["path", "exists", "size_bytes", "sha256", "role"],
        ),
        "checks_csv": write_csv(
            tables / "reviewer_smoke_execution_checks.csv",
            checks,
            ["check_id", "status", "expected", "observed", "interpretation"],
        ),
    }
    manifest = {
        "status": status,
        "out_dir": args.out_dir,
        "summary": report["summary"],
        "paths": paths,
        "note": "This audit records latest reviewer smoke execution fingerprints. It does not create or validate paper-scale results.",
    }
    manifest_path = write_json(out_dir / "tits_reviewer_smoke_execution_audit_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, "status": status, "summary": report["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
