#!/usr/bin/env python
import argparse
import json
from pathlib import Path

import numpy as np


def bootstrap_ci(values, fn=np.mean, samples=10000, seed=0, alpha=0.05):
    values = np.asarray(values, dtype=np.float64)
    if values.size == 0:
        return [None, None]
    rng = np.random.default_rng(seed)
    draws = []
    for _ in range(samples):
        sample = values[rng.integers(0, values.size, size=values.size)]
        draws.append(float(fn(sample)))
    lo, hi = np.quantile(draws, [alpha / 2.0, 1.0 - alpha / 2.0])
    return [float(lo), float(hi)]


def summarize_rows(rows, seed=0):
    pass_values = np.asarray([row["validation_status"] == "PASS" for row in rows], dtype=np.float64)
    target_grass = np.asarray([row["target_grass_rate"] for row in rows], dtype=np.float64)
    max_grass = np.asarray([row["max_grass_rate"] for row in rows], dtype=np.float64)
    rank = np.asarray([row["target_final_rank_by_tiles"] for row in rows], dtype=np.float64)
    steps = np.asarray([row["steps_run"] for row in rows], dtype=np.float64)
    target_progress = []
    mean_progress = []
    for row in rows:
        # Track length differs by seed. The summary rows do not store it, so use
        # completion flag plus final rank/tile counts for conservative reporting.
        tiles = np.asarray(row["tile_visited_count"], dtype=np.float64)
        target_progress.append(float(tiles[-1] / max(tiles.max(), 1.0)))
        mean_progress.append(float(np.mean(tiles / max(tiles.max(), 1.0))))
    target_progress = np.asarray(target_progress, dtype=np.float64)
    mean_progress = np.asarray(mean_progress, dtype=np.float64)
    return {
        "n": int(len(rows)),
        "pass_rate": float(pass_values.mean()) if len(rows) else None,
        "pass_rate_ci95": bootstrap_ci(pass_values, seed=seed),
        "target_grass_rate_mean": float(target_grass.mean()) if len(rows) else None,
        "target_grass_rate_ci95": bootstrap_ci(target_grass, seed=seed + 1),
        "max_grass_rate_mean": float(max_grass.mean()) if len(rows) else None,
        "target_rank_mean": float(rank.mean()) if len(rows) else None,
        "steps_mean": float(steps.mean()) if len(rows) else None,
        "target_relative_progress_mean": float(target_progress.mean()) if len(rows) else None,
        "mean_relative_progress_mean": float(mean_progress.mean()) if len(rows) else None,
    }


def load_graph_rows(root):
    suite_path = root / "evaluations" / "multiseed_suite" / "multiseed_suite_summary.json"
    if suite_path.exists():
        suite = json.loads(suite_path.read_text(encoding="utf-8"))
        rows = [
            row for row in suite.get("rows", [])
            if row.get("method") == "graph_soft_shield"
        ]
        if rows:
            return rows, str(suite_path), "graph_soft_shield"
    table = json.loads((root / "tables" / "main_results.json").read_text(encoding="utf-8"))
    return table["graph_bc_rows"], str(root / "tables" / "main_results.json"), "graph_bc_safety_shield"


def main():
    parser = argparse.ArgumentParser(description="Export seed-level statistical report.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    graph_rows, source, method = load_graph_rows(root)
    report = {
        "method": method,
        "source": source,
        "summary": summarize_rows(graph_rows),
        "seed_rows": graph_rows,
        "failure_cases": [
            row for row in graph_rows
            if row["validation_status"] != "PASS"
        ],
        "interpretation": (
            "Current graph/set policy with safety shield is promising but not yet "
            "publication-strong: the strict pass rate is below the 0.8 target and "
            "requires recovery-data or stronger constrained control."
        ),
    }
    out_json = root / "tables" / "statistical_report.json"
    out_md = root / "tables" / "statistical_report.md"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    summary = report["summary"]
    lines = [
        "# Statistical Report",
        "",
        f"- Method: `{report['method']}`",
        f"- Evaluation seeds: {summary['n']}",
        f"- Strict pass rate: {summary['pass_rate']:.3f}",
        f"- Bootstrap 95% CI for pass rate: [{summary['pass_rate_ci95'][0]:.3f}, {summary['pass_rate_ci95'][1]:.3f}]",
        f"- Mean target grass rate: {summary['target_grass_rate_mean']:.3f}",
        f"- Mean max grass rate: {summary['max_grass_rate_mean']:.3f}",
        f"- Mean target rank: {summary['target_rank_mean']:.3f}",
        f"- Mean steps: {summary['steps_mean']:.1f}",
        "",
        "## Failure Cases",
        "",
    ]
    if report["failure_cases"]:
        for row in report["failure_cases"]:
            lines.append(
                f"- seed {row['seed']}: status={row['validation_status']}, "
                f"lap={row['target_completed_lap']}, rank={row['target_final_rank_by_tiles']}, "
                f"target_grass={row['target_grass_rate']:.3f}, tiles={row['tile_visited_count']}"
            )
    else:
        lines.append("- None")
    lines.extend(["", "## Interpretation", "", report["interpretation"], ""])
    out_md.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"json": str(out_json), "markdown": str(out_md)}, indent=2))


if __name__ == "__main__":
    main()
