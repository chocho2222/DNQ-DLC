#!/usr/bin/env python
"""Summarize speed-capped online runs without selecting on outcomes."""
import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

import numpy as np


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("root", help="Directory containing per-case summaries")
    parser.add_argument("--speed-tolerance", type=float, default=1.0)
    parser.add_argument("--output", default="")
    args = parser.parse_args()
    rows = []
    for path in sorted(Path(args.root).glob("**/summaries/*.summary.json")):
        try:
            row = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if row.get("target_mean_speed") is None:
            continue
        row["source_path"] = str(path)
        rows.append(row)
    by_case = defaultdict(list)
    for row in rows:
        by_case[(row.get("track_path"), int(row.get("num_agents", 0)), int(row.get("seed", 0)))].append(row)
    reference = {}
    for key, items in by_case.items():
        cap_values = [float(item["speed_cap"]) for item in items if item.get("speed_cap") is not None]
        if not cap_values:
            continue
        target = float(np.median(cap_values))
        eligible = [item for item in items if abs(float(item["target_mean_speed"]) - target) <= args.speed_tolerance]
        reference[key] = {item["algorithm"]: item for item in eligible}
    out_rows = []
    algorithms = sorted({row["algorithm"] for rows in rows})
    for algorithm in algorithms:
        matched = []
        for key, items in reference.items():
            if algorithm in items:
                matched.append(items[algorithm])
        speeds = np.asarray([float(item["target_mean_speed"]) for item in matched], dtype=float)
        out_rows.append({
            "algorithm": algorithm,
            "n_total": sum(1 for row in rows if row["algorithm"] == algorithm),
            "n_speed_matched": len(matched),
            "match_rate": len(matched) / max(sum(1 for row in rows if row["algorithm"] == algorithm), 1),
            "mean_speed_matched": float(speeds.mean()) if len(speeds) else None,
            "mean_speed_abs_delta_to_cap": float(np.abs(speeds - np.median([float(item["speed_cap"]) for item in matched])).mean()) if len(speeds) else None,
            "success_rate_matched": float(np.mean([float(item["overtake_success_rate"]) for item in matched])) if matched else None,
            "grass_rate_matched": float(np.mean([float(item["target_grass_rate"]) for item in matched])) if matched else None,
            "elegant_rate_matched": float(np.mean([float(item["elegant_overtake_rate"]) for item in matched])) if matched else None,
        })
    output = Path(args.output) if args.output else Path(args.root) / "speed_matched_summary.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    fields = list(out_rows[0]) if out_rows else ["algorithm"]
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(out_rows)
    print(json.dumps({"output": str(output), "summary_rows": len(out_rows), "case_count": len(reference), "speed_tolerance": args.speed_tolerance}, indent=2))


if __name__ == "__main__":
    main()
