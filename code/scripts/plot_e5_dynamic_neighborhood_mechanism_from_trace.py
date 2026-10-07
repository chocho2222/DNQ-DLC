#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Plot dynamic-neighborhood mechanism evidence from a clean video trace."""

import argparse
import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def target_neighbor_ids(row, target_agent):
    ids = row.get("dynamic_neighbor_ids") or []
    if ids and isinstance(ids[0], list):
        ids = ids[target_agent]
    return [int(item) for item in ids]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--target-agent", type=int, default=-1)
    args = parser.parse_args()

    trace_path = Path(args.trace)
    summary_path = Path(args.summary)
    out_dir = Path(args.out_dir)
    fig_dir = out_dir / "figures"
    table_dir = out_dir / "tables"
    fig_dir.mkdir(parents=True, exist_ok=True)
    table_dir.mkdir(parents=True, exist_ok=True)

    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    target_agent = args.target_agent if args.target_agent >= 0 else int(summary["target_agent"])

    steps = np.asarray([int(row["step"]) for row in trace], dtype=int)
    neighbor_sets = [tuple(target_neighbor_ids(row, target_agent)) for row in trace]
    changes = np.asarray([0] + [int(a != b) for a, b in zip(neighbor_sets, neighbor_sets[1:])], dtype=int)
    set_cardinality = np.asarray([len(set(item)) for item in neighbor_sets], dtype=float)
    top1 = np.asarray([item[0] if item else -1 for item in neighbor_sets], dtype=int)
    top2 = np.asarray([item[1] if len(item) > 1 else -1 for item in neighbor_sets], dtype=int)
    top3 = np.asarray([item[2] if len(item) > 2 else -1 for item in neighbor_sets], dtype=int)

    telemetry = [row["telemetry"] for row in trace]
    lateral = np.asarray([row["lateral_error"][target_agent] for row in telemetry], dtype=float)
    off_track = np.asarray([row["on_grass"][target_agent] for row in telemetry], dtype=float)
    progress = np.asarray([row["tile_visited_count"][target_agent] for row in trace], dtype=float)
    speed = np.asarray([row["speed"][target_agent] for row in trace], dtype=float)

    events = summary.get("overtake_events") or []
    clean_events = [event for event in events if event.get("on_track_overtake") and event.get("elegant_overtake")]

    csv_path = table_dir / "e5_dynamic_neighborhood_mechanism_source_data.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "step",
                "neighbor_set",
                "changed_from_previous",
                "set_cardinality",
                "top1_neighbor",
                "top2_neighbor",
                "top3_neighbor",
                "target_lateral_error",
                "target_off_track",
                "target_progress_tiles",
                "target_speed",
            ],
        )
        writer.writeheader()
        for idx, step in enumerate(steps):
            writer.writerow(
                {
                    "step": int(step),
                    "neighbor_set": " ".join(map(str, neighbor_sets[idx])),
                    "changed_from_previous": int(changes[idx]),
                    "set_cardinality": int(set_cardinality[idx]),
                    "top1_neighbor": int(top1[idx]),
                    "top2_neighbor": int(top2[idx]),
                    "top3_neighbor": int(top3[idx]),
                    "target_lateral_error": float(lateral[idx]),
                    "target_off_track": int(off_track[idx]),
                    "target_progress_tiles": float(progress[idx]),
                    "target_speed": float(speed[idx]),
                }
            )

    fig, axes = plt.subplots(3, 1, figsize=(7.2, 6.0), sharex=True, constrained_layout=True)
    axes[0].step(steps, top1, where="post", label="top-1 neighbor", color="#235a9f", linewidth=1.6)
    axes[0].step(steps, top2, where="post", label="top-2 neighbor", color="#2aa876", linewidth=1.2, alpha=0.9)
    axes[0].step(steps, top3, where="post", label="top-3 neighbor", color="#d3832b", linewidth=1.2, alpha=0.9)
    axes[0].set_ylabel("selected ID")
    axes[0].set_title("Dynamic-neighborhood repacking during a clean 10-vehicle overtake")
    axes[0].legend(ncol=3, fontsize=8, frameon=False)

    axes[1].plot(steps, np.cumsum(changes), color="#6c4aa4", linewidth=1.8)
    axes[1].set_ylabel("cumulative\nswitches")
    axes[1].text(
        0.01,
        0.92,
        f"{int(changes.sum())} switches; {len(set(neighbor_sets))} unique sets",
        transform=axes[1].transAxes,
        fontsize=9,
        va="top",
        bbox=dict(boxstyle="round,pad=0.25", facecolor="white", edgecolor="#d5dde8"),
    )

    axes[2].plot(steps, lateral, color="#25344a", linewidth=1.4, label="lateral error")
    axes[2].fill_between(steps, 0, off_track * max(0.35, np.max(np.abs(lateral)) if len(lateral) else 0.35), color="#c43d3d", alpha=0.18, label="off-track flag")
    axes[2].set_ylabel("lateral")
    axes[2].set_xlabel("step")
    axes[2].legend(ncol=2, fontsize=8, frameon=False)

    for ax in axes:
        ax.grid(axis="y", alpha=0.22)
        ax.spines[["top", "right"]].set_visible(False)
        for event in clean_events:
            ax.axvspan(event["start_step"], event["complete_step"], color="#2aa876", alpha=0.10)

    for ext in ["png", "pdf", "svg"]:
        fig.savefig(fig_dir / f"figure_e5_dynamic_neighborhood_mechanism.{ext}", dpi=300)
    plt.close(fig)

    report = {
        "trace": trace_path.as_posix(),
        "summary": summary_path.as_posix(),
        "target_agent": target_agent,
        "steps": len(trace),
        "unique_neighbor_sets": len(set(neighbor_sets)),
        "neighbor_switch_count": int(changes.sum()),
        "clean_overtake_count": len(clean_events),
        "target_grass_rate": summary.get("target_grass_rate"),
        "elegant_overtake_count": summary.get("elegant_overtake_count"),
        "source_csv": csv_path.as_posix(),
        "figure_pdf": (fig_dir / "figure_e5_dynamic_neighborhood_mechanism.pdf").as_posix(),
    }
    report_path = out_dir / "e5_dynamic_neighborhood_mechanism_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
