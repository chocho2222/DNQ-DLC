#!/usr/bin/env python
"""Run and aggregate the frozen Box2D world-model candidate oracle study."""

import argparse
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_csv(path, rows, fields=None):
    fields = fields or (list(rows[0]) if rows else ["case_id"])
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def source_paths(source_root, case, algorithm):
    case_dir = (
        source_root
        / case["shard"]
        / case["track"]
        / f"n{case['num_agents']}"
        / f"seed{case['seed']}"
    )
    stem = f"{algorithm}_n{case['num_agents']}_seed{case['seed']}"
    return (
        case_dir / "traces" / f"{stem}.initial.json",
        case_dir / "traces" / f"{stem}.trace.json",
    )


def scalar(value):
    if value in {None, "", "None"}:
        return None
    return float(value)


def boolean(value):
    return str(value).lower() in {"1", "true", "yes"}


def bootstrap_by_case(case_decisions, metric, repeats, rng):
    case_ids = sorted(case_decisions)
    if not case_ids:
        return None, None
    estimates = []
    for _ in range(repeats):
        sampled = rng.choice(case_ids, size=len(case_ids), replace=True)
        values = []
        for case_id in sampled:
            for row in case_decisions[case_id]:
                value = row.get(metric)
                if value is not None:
                    values.append(value)
        if values:
            estimates.append(float(np.mean(values)))
    if not estimates:
        return None, None
    return tuple(float(item) for item in np.quantile(estimates, [0.025, 0.975]))


def aggregate(config, out, bootstrap_repeats):
    ledger_path = out / "case_ledger.csv"
    ledger = list(csv.DictReader(ledger_path.open(encoding="utf-8"))) if ledger_path.exists() else []
    case_rows = []
    all_decisions = []
    all_candidates = []
    case_decisions = {}
    for planned_index, case in enumerate(config["cases"]):
        case_id = f"{case['track']}_n{case['num_agents']}_seed{case['seed']}"
        case_out = out / "cases" / case_id
        report_path = case_out / "report.json"
        decision_path = case_out / "decision_metrics.csv"
        candidate_path = case_out / "candidate_outcomes.csv"
        base = {"case_id": case_id, "planned_index": planned_index, **case}
        if not report_path.exists() or not decision_path.exists() or not candidate_path.exists():
            case_rows.append({**base, "status": "missing", "audited_decisions": 0})
            continue
        report = read_json(report_path)
        case_rows.append({**base, "status": "ok", **report})
        decisions = []
        for row in csv.DictReader(decision_path.open(encoding="utf-8")):
            parsed = {**base}
            for key, value in row.items():
                if key in {"physical_top1_hit", "reward_top1_hit", "progress_top1_hit", "selected_contact", "best_available_contact"}:
                    parsed[key] = float(boolean(value))
                else:
                    parsed[key] = scalar(value)
            decisions.append(parsed)
            all_decisions.append(parsed)
        case_decisions[case_id] = decisions
        for row in csv.DictReader(candidate_path.open(encoding="utf-8")):
            all_candidates.append({**base, **row})

    write_csv(out / "aggregate" / "case_metrics.csv", case_rows)
    write_csv(out / "aggregate" / "decision_metrics.csv", all_decisions)
    write_csv(out / "aggregate" / "candidate_outcomes.csv", all_candidates)

    metrics = [
        "model_progress_spearman",
        "progress_top1_hit",
        "progress_regret_m",
        "model_reward_spearman",
        "reward_top1_hit",
        "reward_regret",
        "model_utility_spearman",
        "physical_top1_hit",
        "physical_regret",
    ]
    rng = np.random.default_rng(20260915)
    summary = {}
    for metric in metrics:
        values = [row[metric] for row in all_decisions if row.get(metric) is not None]
        low, high = bootstrap_by_case(case_decisions, metric, bootstrap_repeats, rng)
        summary[metric] = {
            "observed_n": len(values),
            "estimate": float(np.mean(values)) if values else None,
            "case_cluster_bootstrap_95ci": [low, high],
        }
    planned_decisions = len(config["cases"]) * int(config["decisions_per_case"])
    for metric in ["progress_top1_hit", "reward_top1_hit", "physical_top1_hit"]:
        hits = sum(row.get(metric, 0.0) for row in all_decisions)
        summary[metric]["conservative_rate_missing_as_failure"] = (
            float(hits / planned_decisions) if planned_decisions else None
        )
    payload = {
        "study": config["study"],
        "planned_cases": len(config["cases"]),
        "complete_cases": sum(row["status"] == "ok" for row in case_rows),
        "planned_decisions": planned_decisions,
        "audited_decisions": len(all_decisions),
        "bootstrap_repeats": bootstrap_repeats,
        "metrics": summary,
        "denominator_policy": config["denominator_policy"],
        "interpretation_boundary": config["interpretation_boundary"],
    }
    aggregate_dir = out / "aggregate"
    aggregate_dir.mkdir(parents=True, exist_ok=True)
    (aggregate_dir / "report.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/world_model_physical_oracle_strict_20260915.json"))
    parser.add_argument("--source-root", type=Path, default=Path("outputs/tits_dynamic_graph_expanded/handcrafted_candidates_strict_20260915"))
    parser.add_argument("--out", type=Path, default=Path("outputs/tits_dynamic_graph_expanded/world_model_physical_oracle_strict_20260915"))
    parser.add_argument("--mode", choices=["run", "aggregate", "all"], default="all")
    parser.add_argument("--jobs-per-case", type=int, default=12)
    parser.add_argument("--bootstrap-repeats", type=int, default=20000)
    parser.add_argument("--skip-existing", action="store_true")
    args = parser.parse_args()
    config = read_json(args.config)
    args.out.mkdir(parents=True, exist_ok=True)
    ledger = []

    if args.mode in {"run", "all"}:
        logs = args.out / "logs"
        logs.mkdir(exist_ok=True)
        for planned_index, case in enumerate(config["cases"]):
            case_id = f"{case['track']}_n{case['num_agents']}_seed{case['seed']}"
            initial, trace = source_paths(args.source_root, case, config["source_algorithm"])
            case_out = args.out / "cases" / case_id
            base = {
                "planned_index": planned_index,
                "case_id": case_id,
                "initial": str(initial),
                "trace": str(trace),
                "out": str(case_out),
            }
            if not initial.exists() or not trace.exists():
                ledger.append({**base, "status": "MISSING_SOURCE", "returncode": ""})
                write_csv(args.out / "case_ledger.csv", ledger)
                continue
            if args.skip_existing and (case_out / "report.json").exists():
                ledger.append({**base, "status": "SKIPPED_VALID", "returncode": 0})
                write_csv(args.out / "case_ledger.csv", ledger)
                continue
            command = [
                sys.executable,
                "scripts/audit_world_model_physical_counterfactual.py",
                "--initial", str(initial),
                "--trace", str(trace),
                "--out", str(case_out),
                "--horizon", str(config["horizon_steps"]),
                "--max-decision-points", str(config["decisions_per_case"]),
                "--replay-tolerance", str(config["replay_tolerance"]),
                "--jobs", str(args.jobs_per_case),
                "--progress-weight", str(config["physical_utility_weights"]["progress"]),
                "--grass-weight", str(config["physical_utility_weights"]["grass"]),
                "--backward-weight", str(config["physical_utility_weights"]["backward"]),
                "--lateral-weight", str(config["physical_utility_weights"]["lateral"]),
                "--contact-weight", str(config["physical_utility_weights"]["contact"]),
            ]
            with (logs / f"{case_id}.log").open("w", encoding="utf-8") as handle:
                completed = subprocess.run(command, stdout=handle, stderr=subprocess.STDOUT, check=False)
            ledger.append({**base, "status": "PASS" if completed.returncode == 0 else "FAIL", "returncode": completed.returncode})
            write_csv(args.out / "case_ledger.csv", ledger)
            print(f"{case_id}: {ledger[-1]['status']}", flush=True)

    payload = None
    if args.mode in {"aggregate", "all"}:
        payload = aggregate(config, args.out, args.bootstrap_repeats)
        print(json.dumps(payload, indent=2))
    manifest = {
        "config": str(args.config),
        "config_sha256": sha256(args.config),
        "source_root": str(args.source_root),
        "arguments": {key: str(value) if isinstance(value, Path) else value for key, value in vars(args).items()},
        "script": str(Path(__file__).resolve()),
        "script_sha256": sha256(Path(__file__)),
    }
    (args.out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
