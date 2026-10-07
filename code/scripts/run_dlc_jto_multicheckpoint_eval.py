#!/usr/bin/env python
"""Run matched online evaluation for four independently trained DLC-JTO checkpoints."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import subprocess
import time
from pathlib import Path


ALGORITHMS = ",".join([
    "v6_runtime_dynamic_neighborhood_safe",
    "rule_expert_gate",
    "dlc_jto_train_seed0",
    "dlc_jto_train_seed1",
    "dlc_jto_train_seed2",
    "dlc_jto_train_seed3",
])


def run_case(seed: int, device: str, args: argparse.Namespace) -> dict:
    case_dir = Path(args.out_dir) / f"seed{seed}"
    suite = case_dir / f"online_suite_n4_seed{seed}.json"
    log = Path(args.out_dir) / "logs" / f"seed{seed}.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    if args.skip_existing and suite.exists():
        return {"seed": seed, "device": device, "returncode": 0, "status": "existing", "suite": str(suite)}
    command = [
        args.python,
        "scripts/run_tits_dynamic_graph_evaluation.py",
        "--config", args.config,
        "--out-dir", str(case_dir),
        "--algorithms", ALGORITHMS,
        "--num-agents", "4",
        "--seed", str(seed),
        "--max-steps", str(args.max_steps),
        "--finish-mode", "any",
        "--observation-type", "telemetry_dynamic",
        "--env-max-neighbors", "0",
        "--neighbor-selection-mode", "interaction",
        "--traffic-profile", "slow_traffic",
        "--randomize-scenario",
        "--no-gif",
        "--device", device,
    ]
    started = time.time()
    with log.open("w", encoding="utf-8") as handle:
        process = subprocess.run(command, stdout=handle, stderr=subprocess.STDOUT, check=False)
    return {
        "seed": seed,
        "device": device,
        "returncode": int(process.returncode),
        "status": "pass" if process.returncode == 0 else "failed",
        "elapsed_seconds": time.time() - started,
        "suite": str(suite),
        "log": str(log),
        "command": command,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="outputs/tits_dynamic_graph_expanded/dlc_jto_checkpoint_generalization_20260716/materials/dlc_jto_multicheckpoint_config.json")
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph_expanded/dlc_jto_checkpoint_generalization_20260716/matched_eval")
    parser.add_argument("--seeds", default="9801,9802,9803,9804,9805,9806,9807,9808")
    parser.add_argument("--devices", default="cuda:0,cuda:1,cuda:2,cuda:3")
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--max-steps", type=int, default=2200)
    parser.add_argument("--python", default="/home/itrc/.conda/envs/vlm_planner/bin/python")
    parser.add_argument("--skip-existing", action="store_true")
    args = parser.parse_args()

    seeds = [int(item) for item in args.seeds.split(",") if item.strip()]
    devices = [item.strip() for item in args.devices.split(",") if item.strip()]
    Path(args.out_dir).mkdir(parents=True, exist_ok=True)
    rows = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.jobs)) as executor:
        futures = {
            executor.submit(run_case, seed, devices[index % len(devices)], args): seed
            for index, seed in enumerate(seeds)
        }
        for future in concurrent.futures.as_completed(futures):
            row = future.result()
            rows.append(row)
            print(json.dumps({key: row.get(key) for key in ["seed", "status", "elapsed_seconds", "suite"]}))
    rows.sort(key=lambda row: row["seed"])
    manifest = {
        "status": "pass" if all(row["returncode"] == 0 for row in rows) else "failed",
        "algorithms": ALGORITHMS.split(","),
        "seeds": seeds,
        "devices": devices,
        "max_steps": args.max_steps,
        "rows": rows,
    }
    path = Path(args.out_dir) / "run_manifest.json"
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(path)
    if manifest["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
