#!/usr/bin/env python
"""Resume selector-only strict shards with an explicit CUDA environment.

The launcher reads the frozen case plan and reruns only cases whose three
algorithm summaries are not all present. Each shard is independent and can
therefore be assigned to one visible GPU.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import time
from pathlib import Path


ALGORITHMS = (
    "dnq_dynamic_interaction",
    "dnq_fixed_identity",
    "dnq_nearest_distance",
)


def complete(case_dir: Path) -> bool:
    summary_dir = case_dir / "summaries"
    if not summary_dir.exists():
        return False
    return all(
        (summary_dir / f"{name}_n{case_dir.parent.name[1:]}_seed{case_dir.name[4:]}.summary.json").exists()
        for name in ALGORITHMS
    )


def expected_summary_paths(case_dir: Path, num_agents: int, seed: int):
    return [
        case_dir / "summaries" / f"{name}_n{num_agents}_seed{seed}.summary.json"
        for name in ALGORITHMS
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--shard", type=Path, required=True)
    parser.add_argument("--gpu", required=True, help="Physical GPU index exposed through CUDA_VISIBLE_DEVICES.")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--python", default="/home/itrc/.conda/envs/vlm_planner/bin/python")
    parser.add_argument("--max-steps", type=int, default=2200)
    args = parser.parse_args()

    args.shard.mkdir(parents=True, exist_ok=True)
    log_dir = args.shard / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    with args.plan.open(newline="", encoding="utf-8") as handle:
        all_rows = list(csv.DictReader(handle))
    # The frozen plan predates the shard label. Shards are fixed seed blocks.
    shard_seeds = {
        "s1": set(range(6401, 6405)),
        "s2": set(range(6405, 6409)),
        "s3": set(range(6409, 6413)),
        "s4": set(range(6413, 6417)),
    }
    rows = [row for row in all_rows if row.get("shard") == args.shard.name
            or int(row["seed"]) in shard_seeds.get(args.shard.name, set())]

    ledger_path = args.shard / "resume_gpu_ledger.csv"
    fields = ["case_id", "status", "returncode", "elapsed_sec", "command", "log_path"]
    with ledger_path.open("w", newline="", encoding="utf-8") as ledger_handle:
        writer = csv.DictWriter(ledger_handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            track = row.get("track") or row.get("track_path") or row.get("track_id")
            num_agents = int(row["num_agents"])
            seed = int(row["seed"])
            track_id = row.get("track_id") or Path(track).stem
            case_id = row.get("case_id") or f"{track_id}_n{num_agents}_seed{seed}"
            case_dir = args.shard / Path(track).stem / f"n{num_agents}" / f"seed{seed}"
            summaries = expected_summary_paths(case_dir, num_agents, seed)
            if all(path.exists() for path in summaries):
                record = {"case_id": case_id, "status": "SKIP_COMPLETE", "returncode": 0,
                          "elapsed_sec": 0.0, "command": "", "log_path": ""}
                writer.writerow(record)
                ledger_handle.flush()
                continue

            case_dir.mkdir(parents=True, exist_ok=True)
            log_path = log_dir / f"{case_id}.gpu.log"
            command = [
                args.python,
                "scripts/run_tits_dynamic_graph_evaluation.py",
                "--config", str(args.config),
                "--algorithms", ",".join(ALGORITHMS),
                "--out-dir", str(case_dir),
                "--num-agents", str(num_agents),
                "--seed", str(seed),
                "--max-steps", str(args.max_steps),
                "--finish-mode", "steps",
                "--observation-type", "telemetry_dynamic",
                "--env-max-neighbors", "0",
                "--traffic-profile", "mixed_traffic",
                "--neighbor-order", "identity",
                "--telemetry-version", "legacy_v1",
                "--observation-noise-std", "0.0",
                "--observation-noise-seed-offset", "200000",
                "--actuation-delay-steps", "0",
                "--randomize-scenario",
                "--no-gif",
                "--device", "cuda:0",
                "--track-path", track,
            ]
            env = dict(os.environ)
            env["CUDA_VISIBLE_DEVICES"] = str(args.gpu)
            started = time.time()
            with log_path.open("w", encoding="utf-8") as log_handle:
                result = subprocess.run(command, stdout=log_handle, stderr=subprocess.STDOUT,
                                        check=False, env=env)
            elapsed = time.time() - started
            status = "PASS" if result.returncode == 0 and all(path.exists() for path in summaries) else "FAIL"
            record = {"case_id": case_id, "status": status, "returncode": int(result.returncode),
                      "elapsed_sec": elapsed, "command": " ".join(command), "log_path": str(log_path)}
            writer.writerow(record)
            ledger_handle.flush()
            if status != "PASS":
                print(json.dumps(record, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
