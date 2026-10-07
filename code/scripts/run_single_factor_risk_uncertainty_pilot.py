#!/usr/bin/env python
"""Run a fixed-protocol risk/uncertainty single-factor pilot across four GPUs."""
import argparse
import csv
import json
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON = "/home/itrc/.conda/envs/vlm_planner/bin/python"
TRACKS = ["tracks/hairpin_scaled.npz", "tracks/s_curve_scaled.npz"]
COUNTS = [6, 8]
SEEDS = list(range(6201, 6209))
ALGORITHMS = "dnq_dlc_full,no_risk_uncertainty"


def cases_for_gpu(gpu):
    cases = [(track, count, seed) for track in TRACKS for count in COUNTS for seed in SEEDS]
    return [case for i, case in enumerate(cases) if i % 4 == gpu]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="outputs/single_factor_risk_uncertainty_pilot_20260912")
    ap.add_argument("--gpu", type=int, required=True)
    ap.add_argument("--max-steps", type=int, default=600)
    ap.add_argument("--device", default="cpu")
    args = ap.parse_args()

    base = ROOT / args.out_dir
    shard = base / f"gpu{args.gpu}"
    logs = shard / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    config = ROOT / "configs/single_factor_risk_uncertainty_pilot_20260912.json"
    rows = []
    for track, count, seed in cases_for_gpu(args.gpu):
        stem = f"{Path(track).stem}_n{count}_seed{seed}"
        case_dir = shard / Path(track).stem / f"n{count}" / f"seed{seed}"
        command = [
            PYTHON, "scripts/run_tits_dynamic_graph_evaluation.py",
            "--config", str(config), "--algorithms", ALGORITHMS,
            "--out-dir", str(case_dir), "--num-agents", str(count),
            "--seed", str(seed), "--max-steps", str(args.max_steps),
            "--finish-mode", "steps", "--observation-type", "telemetry_dynamic",
            "--telemetry-version", "corrected_v2", "--env-max-neighbors", "0",
            "--traffic-profile", "slow_traffic", "--randomize-scenario",
            "--no-gif", "--device", args.device if args.device != "auto" else f"cuda:{args.gpu}", "--track-path", track,
        ]
        started = time.time()
        result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
        log = logs / f"{stem}.log"
        log.write_text(result.stdout + "\n--- STDERR ---\n" + result.stderr, encoding="utf-8")
        summaries = list((case_dir / "summaries").glob("*.summary.json"))
        status = "PASS" if result.returncode == 0 and len(summaries) == 2 else "FAIL"
        rows.append({
            "case_id": stem, "track": track, "num_agents": count, "seed": seed,
            "case_dir": str(case_dir), "log_path": str(log), "command": " ".join(command),
            "status": status, "returncode": result.returncode, "elapsed_sec": time.time() - started,
            "summary_count": len(summaries),
        })
    with (shard / "case_ledger.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else [])
        writer.writeheader(); writer.writerows(rows)
    manifest = {
        "study": "single_factor_risk_uncertainty_pilot_20260912",
        "protocol": "matched randomized cases; all outcomes retained; the sole planned difference is risk and uncertainty score weights",
        "config": str(config.relative_to(ROOT)), "gpu": args.gpu, "max_steps": args.max_steps,
        "algorithms": ALGORITHMS.split(","), "case_count": len(rows),
        "failure_count": sum(r["status"] != "PASS" for r in rows), "rows": rows,
    }
    (shard / "run_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    if manifest["failure_count"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
