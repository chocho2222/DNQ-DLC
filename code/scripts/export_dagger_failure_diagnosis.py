#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def classify(row, thresholds):
    reasons = []
    if not row.get("target_completed_lap"):
        reasons.append("incomplete_lap")
    if row.get("target_final_rank_by_tiles") != 1:
        reasons.append("not_first")
    if row.get("first_ahead_step") is None:
        reasons.append("no_overtake")
    if row.get("target_grass_rate", 0.0) > thresholds["max_target_grass_rate"]:
        reasons.append("target_grass")
    if row.get("max_grass_rate", 0.0) > thresholds["max_any_grass_rate"]:
        reasons.append("traffic_grass")
    if row.get("mean_tile_progress", 0.0) < thresholds["min_mean_tile_progress"]:
        reasons.append("low_traffic_progress")
    return reasons


def main():
    parser = argparse.ArgumentParser(description="Diagnose near misses in the DAgger recovery smoke suite.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    parser.add_argument(
        "--suite",
        default="outputs/paper_multicar_overtake_20260618/evaluations/heldout_graph_dagger_recovery_smoke/multiseed_suite_summary.json",
    )
    parser.add_argument("--prefix", default="dagger_failure_diagnosis")
    args = parser.parse_args()
    root = Path(args.root)
    suite = load_json(args.suite)
    thresholds = suite["thresholds"]
    rows = []
    for row in suite["rows"]:
        reasons = classify(row, thresholds)
        near_completion = row["target_tile_progress"] >= 0.90
        near_safe = row["target_grass_rate"] <= thresholds["max_target_grass_rate"] * 1.5
        rows.append(
            {
                "method": row["method"],
                "seed": row["seed"],
                "status": row["validation_status"],
                "near_completion": near_completion,
                "near_safe": near_safe,
                "target_progress": row["target_tile_progress"],
                "target_grass_rate": row["target_grass_rate"],
                "max_grass_rate": row["max_grass_rate"],
                "rank": row["target_final_rank_by_tiles"],
                "first_ahead_step": row["first_ahead_step"],
                "target_complete_step": row["target_complete_step"],
                "failure_reasons": "+".join(reasons) if reasons else "pass",
                "summary": row["summary"],
            }
        )
    near_misses = [
        row
        for row in rows
        if row["status"] != "PASS" and (row["near_completion"] or row["near_safe"])
    ]
    report = {
        "suite": args.suite,
        "thresholds": thresholds,
        "n": len(rows),
        "near_miss_count": len(near_misses),
        "near_misses": near_misses,
        "rows": rows,
        "interpretation": (
            "The first DAgger recovery actor produces several near misses, especially under expert-gate fallback, "
            "but strict validation remains unmet because lap completion, target grass, and traffic grass constraints "
            "are not jointly satisfied."
        ),
    }
    out_dir = root / "tables"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_json = out_dir / f"{args.prefix}.json"
    out_md = out_dir / f"{args.prefix}.md"
    out_csv = out_dir / f"{args.prefix}_rows.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    with out_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    lines = [
        "# DAgger Failure Diagnosis",
        "",
        f"- Suite: `{args.suite}`",
        f"- Near misses: {len(near_misses)}/{len(rows)}",
        "",
        "| method | seed | progress | grass | rank | near completion | near safe | reasons |",
        "|---|---:|---:|---:|---:|---|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['method']} | {row['seed']} | {row['target_progress']:.3f} | "
            f"{row['target_grass_rate']:.3f} | {row['rank']} | {row['near_completion']} | "
            f"{row['near_safe']} | {row['failure_reasons']} |"
        )
    lines.extend(["", "## Interpretation", "", report["interpretation"], ""])
    out_md.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv)}, indent=2))


if __name__ == "__main__":
    main()
