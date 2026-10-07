#!/usr/bin/env python3
"""Run the matched two-agent fairness matrix for the T-ITS audit."""
import argparse
import concurrent.futures
import json
import subprocess
import time
from pathlib import Path


def run_case(case):
    out_dir = Path(case["out_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    log_path = out_dir / "run.log"
    command = case["command"]
    started = time.time()
    with log_path.open("w", encoding="utf-8") as handle:
        proc = subprocess.run(command, stdout=handle, stderr=subprocess.STDOUT, check=False)
    return {
        **{k: v for k, v in case.items() if k != "command"},
        "returncode": int(proc.returncode),
        "elapsed_sec": time.time() - started,
        "log_path": str(log_path),
        "command": " ".join(command),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph_expanded/e0_two_agent_fairness_20260918")
    parser.add_argument("--python", default="/home/itrc/.conda/envs/vlm_planner/bin/python")
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--devices", default="cuda:0,cuda:1,cuda:2,cuda:3")
    parser.add_argument("--max-steps", type=int, default=2200)
    args = parser.parse_args()

    root = Path(args.out_dir)
    config = root / "e0_config.json"
    algorithms = ["v6_runtime_dynamic_neighborhood_safe", "dlc_joint_transition_observer",
                  "rule_expert_gate", "rule_safety_gate", "ppo_continuous",
                  "sac_continuous", "td3_continuous"]
    native_legacy = {"dlc_joint_transition_observer", "ppo_continuous", "sac_continuous", "td3_continuous"}
    devices = [x.strip() for x in args.devices.split(",") if x.strip()]
    cases = []
    index = 0
    for track_id, track_path, seeds in [
        ("procedural", "", [3, 7, 11, 17, 23]),
        ("monza", "tracks/monza_scaled.npz", [53, 59, 61, 67, 71]),
    ]:
        for seed in seeds:
            index += 1
            for algorithm in algorithms:
                case_dir = root / "runs" / track_id / f"seed{seed}" / algorithm
                native = algorithm in native_legacy
                command = [
                    args.python, "scripts/run_tits_dynamic_graph_evaluation.py",
                    "--config", str(config), "--out-dir", str(case_dir),
                    "--algorithms", algorithm, "--num-agents", "2", "--seed", str(seed),
                    "--max-steps", str(args.max_steps), "--finish-mode", "any",
                    "--observation-type", "telemetry" if native else "telemetry_dynamic",
                    "--telemetry-version", "legacy_v1", "--env-max-neighbors", "1" if native else "3",
                    "--max-neighbors", "3", "--neighbor-selection-mode", "identity" if native else "interaction",
                    "--neighbor-order", "identity", "--traffic-profile", "slow_traffic",
                    "--line-spacing", "5", "--lateral-spacing", "2.2",
                    "--device", devices[(index - 1) % len(devices)], "--no-gif",
                ]
                if track_path:
                    command += ["--track-path", track_path]
                cases.append({
                    "case_index": index, "track_id": track_id, "track_path": track_path,
                    "algorithm": algorithm, "num_agents": 2, "seed": seed,
                    "device": devices[(index - 1) % len(devices)], "out_dir": str(case_dir),
                    "command": command,
                })

    (root / "e0_case_plan.json").write_text(json.dumps(cases, indent=2), encoding="utf-8")
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        results = list(pool.map(run_case, cases))
    results.sort(key=lambda row: row["case_index"])
    manifest = {
        "experiment_id": "E0_two_agent_baseline_validity",
        "status": "pass" if all(row["returncode"] == 0 for row in results) else "run_failed",
        "case_count": len(cases), "completed_count": sum(row["returncode"] == 0 for row in results),
        "algorithm_count": len(algorithms), "algorithms": algorithms,
        "native_observation_protocol": "legacy_v1 checkpoint-compatible rollout; native 24-D DLC/RL input and dynamic graph input for proposed method",
        "results": results,
    }
    (root / "e0_run_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"status": manifest["status"], "case_count": len(cases), "completed_count": manifest["completed_count"]}, indent=2))
    if manifest["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
