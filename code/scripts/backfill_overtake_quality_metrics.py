#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_tits_dynamic_graph_evaluation import (
    annotate_overtake_quality,
    compute_overtake_events,
    grass_recovery_stats,
)


QUALITY_FIELDS = [
    "overtake_count",
    "on_track_overtake_count",
    "on_track_overtake_rate",
    "elegant_overtake_count",
    "elegant_overtake_rate",
    "overtake_window_grass_rate_mean",
    "overtake_window_max_abs_lateral_mean",
    "grass_recovery_time_mean",
    "grass_recovery_time_max",
    "grass_excursion_count",
    "unrecovered_grass_excursion_count",
]


def mean_or_none(values):
    values = [float(item) for item in values if item is not None and np.isfinite(float(item))]
    return float(np.mean(values)) if values else None


def resolve_trace_path(summary_path, summary):
    candidates = []
    if summary.get("trace_path"):
        candidates.append(Path(summary["trace_path"]))
    candidates.append(summary_path.parent.parent / "traces" / summary_path.name.replace(".summary.json", ".trace.json"))
    for path in candidates:
        if path.exists():
            return path
    return None


def update_summary(summary_path, input_dir, output_dir, in_place, contact_distance):
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    trace_path = resolve_trace_path(summary_path, summary)
    if trace_path is None:
        return {
            "summary_path": str(summary_path),
            "trace_path": None,
            "status": "missing_trace",
        }
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    target_agent = int(summary.get("target_agent", max(int(summary.get("num_agents", 1)) - 1, 0)))
    track_tiles = int(summary.get("track_tiles", 0))
    events = compute_overtake_events(trace, target_agent, track_tiles)
    events = annotate_overtake_quality(
        trace,
        events,
        target_agent,
        contact_distance=float(contact_distance),
    )
    on_track_events = [event for event in events if event.get("on_track_overtake")]
    elegant_events = [event for event in events if event.get("elegant_overtake")]
    grace = min(20, max(len(trace) // 10, 0))
    recovery = grass_recovery_stats(trace, target_agent, grace=grace)

    summary["overtake_events"] = events
    summary["overtake_count"] = int(len(events))
    summary["overtake_success"] = bool(events)
    summary["overtake_success_rate"] = float(bool(events))
    summary["on_track_overtake_count"] = int(len(on_track_events))
    summary["on_track_overtake_rate"] = float(len(on_track_events) / len(events)) if events else 0.0
    summary["elegant_overtake_count"] = int(len(elegant_events))
    summary["elegant_overtake_rate"] = float(len(elegant_events) / len(events)) if events else 0.0
    summary["overtake_window_grass_rate_mean"] = mean_or_none(event.get("window_grass_rate") for event in events)
    summary["overtake_window_max_abs_lateral_mean"] = mean_or_none(event.get("window_max_abs_lateral") for event in events)
    summary.update(recovery)

    if in_place:
        out_path = summary_path
    else:
        if output_dir is None:
            raise ValueError("--out-dir is required unless --in-place is set")
        rel = summary_path.relative_to(input_dir)
        out_path = output_dir / rel
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "summary_path": str(summary_path),
        "output_path": str(out_path),
        "trace_path": str(trace_path),
        "status": "updated",
        "algorithm": summary.get("algorithm"),
        "seed": summary.get("seed"),
        "num_agents": summary.get("num_agents"),
        **{field: summary.get(field) for field in QUALITY_FIELDS},
    }


def main():
    parser = argparse.ArgumentParser(description="Backfill publication-grade overtake quality metrics from existing traces.")
    parser.add_argument("--input-dir", required=True, help="Root containing **/summaries/*.summary.json and matching traces.")
    parser.add_argument("--out-dir", default="", help="Output root preserving summary relative paths. Not needed with --in-place.")
    parser.add_argument("--in-place", action="store_true", help="Overwrite existing summary files.")
    parser.add_argument("--contact-distance", type=float, default=3.0)
    parser.add_argument("--report", default="", help="Optional CSV report path.")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.out_dir) if args.out_dir else None
    if not input_dir.exists():
        raise SystemExit(f"input dir not found: {input_dir}")
    if not args.in_place and output_dir is None:
        raise SystemExit("--out-dir is required unless --in-place is set")

    rows = []
    for summary_path in sorted(input_dir.glob("**/summaries/*.summary.json")):
        rows.append(update_summary(summary_path, input_dir, output_dir, args.in_place, args.contact_distance))

    updated = sum(row["status"] == "updated" for row in rows)
    missing = sum(row["status"] != "updated" for row in rows)
    report_path = Path(args.report) if args.report else (output_dir or input_dir) / "overtake_quality_backfill_report.csv"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "status",
        "algorithm",
        "seed",
        "num_agents",
        "summary_path",
        "output_path",
        "trace_path",
        *QUALITY_FIELDS,
    ]
    with report_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field) for field in fields})

    print(
        json.dumps(
            {
                "input_dir": str(input_dir),
                "out_dir": str(output_dir) if output_dir else None,
                "in_place": bool(args.in_place),
                "updated": updated,
                "missing_or_failed": missing,
                "report": str(report_path),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
