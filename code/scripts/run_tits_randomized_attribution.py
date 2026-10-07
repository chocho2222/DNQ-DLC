#!/usr/bin/env python
"""Run matched, randomized DNQ-DLC attribution cases with a failure ledger."""

import argparse
import csv
import json
import subprocess
import time
from pathlib import Path


def parse_ints(text):
    values = []
    for token in text.split(","):
        token = token.strip()
        if not token:
            continue
        if ":" in token:
            start, stop = (int(item) for item in token.split(":", 1))
            values.extend(range(start, stop + 1))
        else:
            values.append(int(token))
    return values


def parse_tracks(text):
    tracks = []
    for token in text.split(","):
        path = token.strip()
        if path:
            tracks.append(("procedural", "") if path.lower() == "procedural" else (Path(path).stem, path))
    return tracks


def algorithm_names(config_path):
    config = json.loads(Path(config_path).read_text(encoding="utf-8"))
    return [item["name"] for item in config.get("algorithms", [])]


def expected_summaries(case_dir, algorithms, num_agents, seed):
    return [
        case_dir / "summaries" / f"{name}_n{num_agents}_seed{seed}.summary.json"
        for name in algorithms
    ]


def summaries_valid(paths):
    if not paths:
        return False
    try:
        for path in paths:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if payload.get("algorithm") is None or payload.get("scenario_randomized") is not True:
                return False
    except (OSError, json.JSONDecodeError):
        return False
    return True


def write_csv(rows, path):
    fields = [
        "case_id", "track", "num_agents", "seed", "status", "returncode",
        "elapsed_sec", "case_dir", "log_path", "missing_summaries", "command",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fields})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/tits_dnq_attribution_ablation_20260710.json")
    parser.add_argument("--output-dir", default="outputs/tits_dynamic_graph_expanded/randomized_attribution_20260710")
    parser.add_argument("--python", default="/home/itrc/.conda/envs/vlm_planner/bin/python")
    parser.add_argument("--tracks", default="tracks/hairpin_scaled.npz,tracks/s_curve_scaled.npz")
    parser.add_argument("--agent-counts", default="6,8")
    parser.add_argument("--seeds", default="5101:5108")
    parser.add_argument("--algorithms", default="")
    parser.add_argument("--max-steps", type=int, default=600)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--traffic-profile", choices=["slow_traffic", "mixed_traffic"], default="slow_traffic")
    parser.add_argument("--neighbor-order", choices=["relevance", "nearest", "identity"], default="relevance")
    parser.add_argument("--telemetry-version", choices=["legacy_v1", "corrected_v2"], default="legacy_v1")
    parser.add_argument("--legacy-checkpoint-migration", action="store_true")
    parser.add_argument("--observation-noise-std", type=float, default=0.0)
    parser.add_argument("--observation-noise-seed-offset", type=int, default=200000)
    parser.add_argument("--actuation-delay-steps", type=int, default=0)
    parser.add_argument("--jobs", type=int, default=1, help="Reserved for explicit multi-GPU scheduling; sequential is the reproducible default.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-existing", action="store_true")
    args = parser.parse_args()

    if args.jobs != 1:
        raise ValueError("Use jobs=1 unless cases are explicitly assigned to independent GPUs.")
    root = Path(args.output_dir)
    logs = root / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    algorithms = [item.strip() for item in args.algorithms.split(",") if item.strip()]
    if not algorithms:
        algorithms = algorithm_names(args.config)

    rows = []
    for track_name, track_path in parse_tracks(args.tracks):
        for num_agents in parse_ints(args.agent_counts):
            for seed in parse_ints(args.seeds):
                case_id = f"{track_name}_n{num_agents}_seed{seed}"
                case_dir = root / track_name / f"n{num_agents}" / f"seed{seed}"
                expected = expected_summaries(case_dir, algorithms, num_agents, seed)
                command = [
                    args.python,
                    "scripts/run_tits_dynamic_graph_evaluation.py",
                    "--config", args.config,
                    "--algorithms", ",".join(algorithms),
                    "--out-dir", str(case_dir),
                    "--num-agents", str(num_agents),
                    "--seed", str(seed),
                    "--max-steps", str(args.max_steps),
                    "--finish-mode", "steps",
                    "--observation-type", "telemetry_dynamic",
                    "--env-max-neighbors", "0",
                    "--traffic-profile", args.traffic_profile,
                    "--neighbor-order", args.neighbor_order,
                    "--telemetry-version", args.telemetry_version,
                    "--observation-noise-std", str(args.observation_noise_std),
                    "--observation-noise-seed-offset", str(args.observation_noise_seed_offset),
                    "--actuation-delay-steps", str(args.actuation_delay_steps),
                    "--randomize-scenario",
                    "--no-gif",
                    "--device", args.device,
                ]
                if args.legacy_checkpoint_migration:
                    command.append("--legacy-checkpoint-migration")
                if track_path:
                    command.extend(["--track-path", track_path])
                base = {
                    "case_id": case_id,
                    "track": track_path,
                    "num_agents": num_agents,
                    "seed": seed,
                    "case_dir": str(case_dir),
                    "log_path": str(logs / f"{case_id}.log"),
                    "command": " ".join(command),
                }
                if args.skip_existing and summaries_valid(expected):
                    rows.append({**base, "status": "SKIPPED_VALID", "returncode": 0, "elapsed_sec": 0.0, "missing_summaries": ""})
                    continue
                if args.dry_run:
                    rows.append({**base, "status": "DRY_RUN", "returncode": "", "elapsed_sec": 0.0, "missing_summaries": ""})
                    continue
                case_dir.mkdir(parents=True, exist_ok=True)
                started = time.time()
                with Path(base["log_path"]).open("w", encoding="utf-8") as handle:
                    process = subprocess.run(command, stdout=handle, stderr=subprocess.STDOUT, check=False)
                missing = [str(path) for path in expected if not path.exists()]
                valid = process.returncode == 0 and not missing and summaries_valid(expected)
                rows.append(
                    {
                        **base,
                        "status": "PASS" if valid else "FAIL",
                        "returncode": process.returncode,
                        "elapsed_sec": time.time() - started,
                        "missing_summaries": ";".join(missing),
                    }
                )
                write_csv(rows, root / "case_ledger.csv")
                print(f"{case_id}: {rows[-1]['status']} ({rows[-1]['elapsed_sec']:.1f}s)", flush=True)

    failures = [row for row in rows if row["status"] == "FAIL"]
    manifest = {
        "protocol": "matched seeds; randomized start order and spacing; all failures retained",
        "config": args.config,
        "arguments": vars(args),
        "algorithms": algorithms,
        "case_count": len(rows),
        "failure_count": len(failures),
        "rows": rows,
        "failures": failures,
    }
    write_csv(rows, root / "case_ledger.csv")
    (root / "run_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"manifest": str(root / "run_manifest.json"), "cases": len(rows), "failures": len(failures)}, indent=2))
    raise SystemExit(1 if failures else 0)


if __name__ == "__main__":
    main()
