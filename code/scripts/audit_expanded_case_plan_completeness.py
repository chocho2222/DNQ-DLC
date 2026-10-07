#!/usr/bin/env python
"""Audit benchmark artifacts against an immutable expanded-case plan."""

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path


ARTIFACT_KINDS = ("summary", "trace", "initial")


def resolve_path(root, value):
    path = Path(value)
    return path if path.is_absolute() else root / path


def artifact_paths(case_dir, algorithm, num_agents, seed):
    stem = f"{algorithm}_n{num_agents}_seed{seed}"
    return {
        "summary": case_dir / "summaries" / f"{stem}.summary.json",
        "trace": case_dir / "traces" / f"{stem}.trace.json",
        "initial": case_dir / "traces" / f"{stem}.initial.json",
    }


def inspect_json(path):
    if not path.is_file():
        return "missing", ""
    if path.stat().st_size == 0:
        return "empty", ""
    try:
        json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return "invalid_json", repr(exc)
    return "ok", ""


def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument(
        "--plan",
        default=(
            "outputs/tits_dynamic_graph_expanded/e1_200_budget_matched/tables/"
            "expanded_benchmark_case_plan.pre_resume_20260915.csv"
        ),
    )
    parser.add_argument(
        "--out",
        default="outputs/tits_dynamic_graph_expanded/e1_200_budget_matched/completeness_audit",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    plan_path = resolve_path(root, args.plan)
    out_dir = resolve_path(root, args.out)
    plan = list(csv.DictReader(plan_path.open(encoding="utf-8")))

    artifact_rows = []
    case_rows = []
    experiment_totals = defaultdict(
        lambda: {
            "planned_cases": 0,
            "complete_cases": 0,
            "partial_cases": 0,
            "empty_cases": 0,
            "planned_algorithm_runs": 0,
            "complete_algorithm_runs": 0,
            "missing_algorithm_runs": 0,
        }
    )

    for case in plan:
        experiment = case["experiment_id"]
        case_dir = resolve_path(root, case["out_dir"])
        algorithms = [item.strip() for item in case["algorithms"].split(",") if item.strip()]
        num_agents = int(case["num_agents"])
        seed = int(case["seed"])
        complete_runs = 0

        for algorithm in algorithms:
            paths = artifact_paths(case_dir, algorithm, num_agents, seed)
            statuses = {}
            errors = {}
            for kind, path in paths.items():
                statuses[kind], errors[kind] = inspect_json(path)
            complete = all(statuses[kind] == "ok" for kind in ARTIFACT_KINDS)
            complete_runs += int(complete)
            artifact_rows.append(
                {
                    "case_index": int(case["case_index"]),
                    "experiment_id": experiment,
                    "track_id": case["track_id"],
                    "num_agents": num_agents,
                    "seed": seed,
                    "algorithm": algorithm,
                    "complete": complete,
                    **{f"{kind}_status": statuses[kind] for kind in ARTIFACT_KINDS},
                    "error": "; ".join(error for error in errors.values() if error),
                    "case_dir": str(case_dir),
                }
            )

        planned_runs = len(algorithms)
        case_status = (
            "complete" if complete_runs == planned_runs else "partial" if complete_runs else "empty"
        )
        case_rows.append(
            {
                "case_index": int(case["case_index"]),
                "experiment_id": experiment,
                "track_id": case["track_id"],
                "num_agents": num_agents,
                "seed": seed,
                "planned_algorithm_runs": planned_runs,
                "complete_algorithm_runs": complete_runs,
                "missing_algorithm_runs": planned_runs - complete_runs,
                "case_status": case_status,
                "case_dir": str(case_dir),
            }
        )

        totals = experiment_totals[experiment]
        totals["planned_cases"] += 1
        totals[f"{case_status}_cases"] += 1
        totals["planned_algorithm_runs"] += planned_runs
        totals["complete_algorithm_runs"] += complete_runs
        totals["missing_algorithm_runs"] += planned_runs - complete_runs

    experiment_rows = []
    for experiment, totals in sorted(experiment_totals.items()):
        experiment_rows.append({"experiment_id": experiment, **totals})

    write_csv(
        out_dir / "artifact_level.csv",
        artifact_rows,
        [
            "case_index",
            "experiment_id",
            "track_id",
            "num_agents",
            "seed",
            "algorithm",
            "complete",
            "summary_status",
            "trace_status",
            "initial_status",
            "error",
            "case_dir",
        ],
    )
    write_csv(
        out_dir / "case_level.csv",
        case_rows,
        [
            "case_index",
            "experiment_id",
            "track_id",
            "num_agents",
            "seed",
            "planned_algorithm_runs",
            "complete_algorithm_runs",
            "missing_algorithm_runs",
            "case_status",
            "case_dir",
        ],
    )
    write_csv(
        out_dir / "experiment_level.csv",
        experiment_rows,
        list(experiment_rows[0].keys()),
    )

    manifest = {
        "source_case_plan": str(plan_path),
        "source_sha256": hashlib.sha256(plan_path.read_bytes()).hexdigest(),
        "planned_cases": len(case_rows),
        "planned_algorithm_runs": len(artifact_rows),
        "complete_cases": sum(row["case_status"] == "complete" for row in case_rows),
        "complete_algorithm_runs": sum(bool(row["complete"]) for row in artifact_rows),
        "validation": "summary, trace, and initial artifacts must exist and parse as JSON",
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"manifest": manifest, "experiments": experiment_rows}, indent=2))


if __name__ == "__main__":
    main()
