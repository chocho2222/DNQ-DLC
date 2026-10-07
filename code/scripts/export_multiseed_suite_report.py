#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path

import numpy as np


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def wilson_ci(k, n, z=1.96):
    if n <= 0:
        return [None, None]
    phat = k / n
    denom = 1.0 + z * z / n
    centre = (phat + z * z / (2 * n)) / denom
    half = z * np.sqrt((phat * (1.0 - phat) + z * z / (4.0 * n)) / n) / denom
    return [float(max(0.0, centre - half)), float(min(1.0, centre + half))]


def summarize(rows):
    n = len(rows)
    pass_count = sum(row["validation_status"] == "PASS" for row in rows)
    return {
        "n": n,
        "pass_count": pass_count,
        "pass_rate": pass_count / n if n else None,
        "pass_rate_ci95_wilson": wilson_ci(pass_count, n),
        "target_grass_rate_mean": float(np.mean([row["target_grass_rate"] for row in rows])) if rows else None,
        "max_grass_rate_mean": float(np.mean([row["max_grass_rate"] for row in rows])) if rows else None,
        "target_tile_progress_mean": float(np.mean([row["target_tile_progress"] for row in rows])) if rows else None,
        "target_rank_mean": float(np.mean([row["target_final_rank_by_tiles"] for row in rows])) if rows else None,
        "steps_mean": float(np.mean([row["steps_run"] for row in rows])) if rows else None,
        "failure_count": n - pass_count,
    }


def main():
    parser = argparse.ArgumentParser(description="Export method-level report for the multi-seed overtake suite.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    parser.add_argument("--suite", default="")
    parser.add_argument("--prefix", default="multiseed_suite")
    args = parser.parse_args()
    root = Path(args.root)
    suite_path = Path(args.suite) if args.suite else root / "evaluations" / "multiseed_suite" / "multiseed_suite_summary.json"
    suite = load_json(suite_path)
    rows = suite["rows"]
    methods = suite["methods"]
    method_summaries = {
        method: summarize([row for row in rows if row["method"] == method])
        for method in methods
    }
    failures = [
        {
            "method": row["method"],
            "seed": row["seed"],
            "rank": row["target_final_rank_by_tiles"],
            "target_progress": row["target_tile_progress"],
            "target_grass_rate": row["target_grass_rate"],
            "max_grass_rate": row["max_grass_rate"],
            "target_completed_lap": row["target_completed_lap"],
            "summary": row["summary"],
        }
        for row in rows
        if row["validation_status"] != "PASS"
    ]
    if any(method == "graph_adaptive_shield" for method in methods):
        interpretation = (
            "Adaptive gating improves the learned-policy line substantially over graph+soft-shield, "
            "but the best adaptive variant still does not exceed the strongest pure overtake rule "
            "baseline under the strict 10-seed protocol."
        )
    else:
        interpretation = (
            "The current graph+soft-shield model is weaker than the strongest hand-coded "
            "overtake baseline under the strict 10-seed protocol. This is a negative but "
            "publication-useful result: future innovation should distill or gate the strong "
            "overtake controller rather than rely on the current graph actor."
        )
    report = {
        "suite": str(suite_path),
        "methods": methods,
        "seeds": suite["seeds"],
        "thresholds": suite["thresholds"],
        "method_summaries": method_summaries,
        "failures": failures,
        "interpretation": interpretation,
    }
    table_dir = root / "tables"
    table_dir.mkdir(parents=True, exist_ok=True)
    out_json = table_dir / f"{args.prefix}_report.json"
    out_md = table_dir / f"{args.prefix}_report.md"
    out_csv = table_dir / f"{args.prefix}_rows.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")

    with out_csv.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "method",
            "seed",
            "validation_status",
            "target_completed_lap",
            "target_final_rank_by_tiles",
            "target_grass_rate",
            "max_grass_rate",
            "target_tile_progress",
            "mean_tile_progress",
            "steps_run",
            "summary",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name) for name in fieldnames})

    lines = [
        "# Multi-seed Suite Report",
        "",
        f"- Suite: `{suite_path}`",
        f"- Seeds: {', '.join(str(seed) for seed in suite['seeds'])}",
        "",
        "| method | n | pass | pass rate | 95% CI | target grass | max grass | target progress | rank |",
        "|---|---:|---:|---:|---|---:|---:|---:|---:|",
    ]
    for method in methods:
        item = method_summaries[method]
        ci = item["pass_rate_ci95_wilson"]
        lines.append(
            f"| {method} | {item['n']} | {item['pass_count']} | {item['pass_rate']:.3f} | "
            f"[{ci[0]:.3f}, {ci[1]:.3f}] | {item['target_grass_rate_mean']:.3f} | "
            f"{item['max_grass_rate_mean']:.3f} | {item['target_tile_progress_mean']:.3f} | "
            f"{item['target_rank_mean']:.2f} |"
        )
    lines.extend(["", "## Failure Cases", ""])
    for row in failures:
        lines.append(
            f"- {row['method']} seed {row['seed']}: rank={row['rank']}, "
            f"target_progress={row['target_progress']:.3f}, target_grass={row['target_grass_rate']:.3f}, "
            f"completed={row['target_completed_lap']}"
        )
    lines.extend(["", "## Interpretation", "", report["interpretation"], ""])
    out_md.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv)}, indent=2))


if __name__ == "__main__":
    main()
