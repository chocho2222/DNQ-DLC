#!/usr/bin/env python
"""Top-down pictures of the admitted set during an overtake, drawn from traces.

The mechanism paragraph of the paper claims that the planner admits a small,
changing set of opponents and that the vehicle being passed is inside that set
while the pass is happening. `scripts/analyze_dynamic_neighborhood_events.py`
audits the claim numerically. This script draws the same recorded runs so the
claim can also be inspected by eye.

Everything is read from the stored trace and initial-state JSON of the released
matrix (`positions`, `hull_angles`, `target_policy_debug.selected_neighbor_ids`,
`track`). No simulation is re-run, no recorded value is modified, and the colours
come from `scripts/tits_figure_style.py`, so the controller shown as indigo here
is indigo in every other figure and frame of the submission.

Usage:
    python3 scripts/build_dynamic_neighborhood_trace_figure.py \
        --root outputs/tits_dynamic_graph_expanded/corrected_v2_20260920/main_final_20260922 \
        --case M10_scale_n10_seed21 --out-dir <dir>
"""
import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.audit_validity_endpoint_v3 import detect_events, track_geometry  # noqa: E402
from scripts.analyze_dynamic_neighborhood_events import APPROACH, MARGIN, PRE, _admitted  # noqa: E402
from scripts.tits_figure_style import (  # noqa: E402
    color_for_algorithm,
    configure_publication_matplotlib,
    label_for_algorithm,
)

HOLD = 50
TRAIL = 40
CAR_LENGTH = 5.2
CAR_WIDTH = 2.4
TRACK_HALF_WIDTH = 40.0 / 6.0


def track_points(initial):
    return [[float(v) for v in row[2:4]] for row in initial["track"]]


def road_ribbon(points, half_width=TRACK_HALF_WIDTH):
    ring = np.asarray(points, dtype=float)
    tangent = np.roll(ring, -1, axis=0) - np.roll(ring, 1, axis=0)
    norm = np.linalg.norm(tangent, axis=1, keepdims=True)
    tangent = tangent / np.where(norm == 0, 1, norm)
    normal = np.stack([-tangent[:, 1], tangent[:, 0]], axis=1)
    # Keep the offset direction continuous along the ring; without this the
    # ribbon folds back on itself at hairpins.
    for index in range(1, len(normal)):
        if np.dot(normal[index], normal[index - 1]) < 0:
            normal[index] = -normal[index]
    if np.dot(normal[0], normal[-1]) < 0:
        normal[0] = -normal[0]
    left = ring + half_width * normal
    right = ring - half_width * normal
    return np.vstack([left, right[::-1]])


def car_corners(position, hull_angle):
    forward = np.array([-np.sin(hull_angle), np.cos(hull_angle)])
    lateral = np.array([np.cos(hull_angle), np.sin(hull_angle)])
    half_length = CAR_LENGTH / 2.0
    half_width = CAR_WIDTH / 2.0
    position = np.asarray(position, dtype=float)
    return np.array([
        position + half_length * forward + half_width * lateral,
        position + half_length * forward - half_width * lateral,
        position - half_length * forward - half_width * lateral,
        position - half_length * forward + half_width * lateral,
    ])


def find_event(path):
    with open(path) as handle:
        trace = json.load(handle)
    initial_path = path.replace(".trace.json", ".initial.json")
    with open(initial_path) as handle:
        initial = json.load(handle)
    points = track_points(initial)
    cumulative, lap, _ = track_geometry(points)
    num_agents = len(initial["positions"])
    target = int((trace[0].get("target_policy_debug") or {}).get("target_agent", num_agents - 1))
    events = detect_events(trace, target, cumulative, lap, APPROACH, MARGIN)
    best = None
    for event in events:
        complete = int(event["complete_index"])
        if complete + HOLD >= len(trace) or complete - PRE < 0:
            continue
        window = [_admitted(trace[i]) for i in range(complete - PRE, complete + HOLD + 1)]
        window = [item for item in window if item is not None]
        changes = sum(1 for a, b in zip(window, window[1:]) if a != b)
        record = {
            "start_index": int(event["start_index"]),
            "complete_index": complete,
            "opponent": int(event["opponent"]),
            "target": target,
            "changes": changes,
        }
        if best is None or changes > best["changes"]:
            best = record
    return trace, initial, points, best


def draw_road(ax, ring, limits):
    """The road as a wide stroke along the centre line.

    A stroked line cannot develop the folds and gaps an offset polygon gets on
    the coarse centre-line samples of a hairpin.
    """
    ax.set_xlim(limits[0], limits[1])
    ax.set_ylim(limits[2], limits[3])
    ax.set_aspect("equal")
    ax.figure.canvas.draw()
    unit = ax.transData.transform((1.0, 0.0)) - ax.transData.transform((0.0, 0.0))
    points_per_unit = abs(unit[0]) * 72.0 / ax.figure.dpi
    closed = np.vstack([ring, ring[:1]])
    ax.plot(closed[:, 0], closed[:, 1], color="#DCE1E6",
            linewidth=2.0 * TRACK_HALF_WIDTH * points_per_unit,
            solid_capstyle="round", solid_joinstyle="round", zorder=0)


def draw_panel(ax, ring, trace, step, target, admitted, opponent, colour, limits,
               window=None):
    draw_road(ax, ring, limits)
    row = trace[step]
    if window is not None:
        ego_trail = np.asarray([trace[i]["positions"][target] for i in window], dtype=float)
        ax.plot(ego_trail[:, 0], ego_trail[:, 1], color=colour, linewidth=0.9,
                alpha=0.75, zorder=2)
        partner_trail = np.asarray([trace[i]["positions"][opponent] for i in window], dtype=float)
        ax.plot(partner_trail[:, 0], partner_trail[:, 1], color="#111827",
                linewidth=0.6, linestyle=(0, (3, 2)), zorder=2)
    for index, position in enumerate(row["positions"]):
        if index == target:
            continue
        inside = admitted is not None and index in admitted
        corners = car_corners(position, row["hull_angles"][index])
        ax.add_patch(plt.Polygon(corners, closed=True,
                                 facecolor="#AEB6BD" if inside else "#E3E7EA",
                                 edgecolor="black", linewidth=0.5, zorder=3))
    ego = car_corners(row["positions"][target], row["hull_angles"][target])
    ax.add_patch(plt.Polygon(ego, closed=True, facecolor=colour, edgecolor="black",
                             linewidth=0.6, zorder=5))
    if opponent is not None:
        corners = car_corners(row["positions"][opponent], row["hull_angles"][opponent])
        ax.add_patch(plt.Polygon(corners, closed=True, facecolor="none",
                                 edgecolor="#111827", linewidth=1.2, zorder=6))
        ax.annotate(f"vehicle being passed ({opponent})", xy=row["positions"][opponent],
                    xytext=(0, 16), textcoords="offset points", fontsize=6.5,
                    ha="center", color="#111827", zorder=7,
                    arrowprops=dict(arrowstyle="-", linewidth=0.5, color="#111827"))
    ax.set_xlim(limits[0], limits[1])
    ax.set_ylim(limits[2], limits[3])
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_title(f"step {step}", fontsize=7.5, pad=2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--cases", required=True,
                        help="comma-separated case directories, one figure row each")
    parser.add_argument("--ours", default="ours_dnq_dlc")
    parser.add_argument("--out-dir", default="figures")
    parser.add_argument("--stem", default="figure_dynamic_neighborhood_trace")
    args = parser.parse_args()

    configure_publication_matplotlib(font_size=7.5)
    global plt
    import matplotlib.pyplot as plt  # noqa: E402

    rows = []
    for case in args.cases.split(","):
        case = case.strip()
        case_dir = Path(args.root) / case
        case_suffix = "n" + case.split("_n", 1)[1]
        path = case_dir / "traces" / f"{args.ours}_{case_suffix}.trace.json"
        if not path.exists():
            raise SystemExit(f"no trace at {path}")
        trace, initial, points, event = find_event(str(path))
        if event is None:
            raise SystemExit(f"no auditable pass event for {case}")
        admitted = [_admitted(row) for row in trace]
        rows.append({"case": case, "trace": trace, "initial": initial,
                     "points": points, "event": event, "admitted": admitted})

    steps_rows = []
    for row in rows:
        complete = row["event"]["complete_index"]
        steps_rows.append([complete - PRE, complete,
                           min(complete + TRAIL, len(row["trace"]) - 1)])

    views = []
    for row, steps in zip(rows, steps_rows):
        field = np.vstack([np.asarray(row["trace"][step]["positions"], dtype=float) for step in steps])
        views.append((field.mean(axis=0), field.max(axis=0) - field.min(axis=0)))
    # One shared scale for every panel, letterboxed so that a wide field does
    # not force tall axes.
    extent = np.max(np.vstack([item[1] for item in views]), axis=0)
    half_x = max(extent[0], extent[1] / 0.62) / 2.0 + 8.0
    half_y = half_x * 0.62

    figure = plt.figure(figsize=(7.4, 3.7))
    grid = figure.add_gridspec(len(rows), 4, width_ratios=[1.0, 1.0, 1.0, 0.62],
                               wspace=0.14, hspace=0.30)
    axes = [[figure.add_subplot(grid[r, c]) for c in range(4)] for r in range(len(rows))]
    colour = color_for_algorithm(args.ours)
    for row_index, (row, steps) in enumerate(zip(rows, steps_rows)):
        centre = views[row_index][0]
        limits = [centre[0] - half_x, centre[0] + half_x,
                  centre[1] - half_y, centre[1] + half_y]
        ring = np.asarray(row["points"], dtype=float)
        complete = row["event"]["complete_index"]
        window = list(range(max(0, complete - PRE), min(len(row["trace"]), complete + TRAIL + 1)))
        for column, step in enumerate(steps):
            draw_panel(axes[row_index][column], ring, row["trace"], step,
                       row["event"]["target"], row["admitted"][step],
                       row["event"]["opponent"], colour, limits, window=window)
            debug = row["trace"][step].get("target_policy_debug") or {}
            exposed = len(debug.get("exposed_neighbor_ids") or [])
            axes[row_index][column].annotate(
                f"seen {exposed}, admitted {len(row['admitted'][step] or ())}",
                xy=(0.5, -0.02), xycoords="axes fraction", fontsize=6.0,
                ha="center", va="top", color="#374151")
            print(f"    {row['case']} step {step}: seen {exposed}, "
                  f"admitted {len(row['admitted'][step] or ())}")
        timeline = axes[row_index][3]
        span_steps = list(range(complete - PRE, complete + HOLD + 1))
        partner = row["event"]["opponent"]
        membership = [1 if partner in (row["admitted"][step] or set()) else 0
                      for step in span_steps]
        timeline.step(span_steps, membership, where="post", color=colour, linewidth=1.3)
        timeline.plot(steps, [membership[step - span_steps[0]] for step in steps], "o",
                      color=colour, markersize=3.4, markeredgecolor="black",
                      markeredgewidth=0.4, linestyle="none")
        timeline.set_ylim(-0.25, 1.25)
        timeline.set_yticks([0, 1])
        timeline.set_yticklabels(["out", "in"], fontsize=5.6)
        timeline.set_xticks(steps)
        timeline.set_xticklabels([str(step) for step in steps], fontsize=5.4, rotation=90)
        timeline.tick_params(axis="y", length=2)
        timeline.set_title("passed car in the set", fontsize=6.5, pad=2)
        for spine in ("top", "right"):
            timeline.spines[spine].set_visible(False)
        axes[row_index][0].annotate(
            f"{label_for_algorithm(args.ours)} \u00b7 "
            f"{len(row['initial']['positions'])} vehicles \u00b7 "
            f"seed {row['initial'].get('seed')} \u00b7 "
            f"{row['event']['changes']} admitted-set changes in the window",
            xy=(0.0, 1.18), xycoords="axes fraction", fontsize=7.5,
            weight="bold", ha="left", color="#111827")

    handles = [
        plt.Line2D([], [], marker="s", markersize=5, linestyle="none",
                   markerfacecolor="#AEB6BD", markeredgecolor="black", label="in the admitted set"),
        plt.Line2D([], [], marker="s", markersize=5, linestyle="none",
                   markerfacecolor="#E3E7EA", markeredgecolor="black", label="seen, not admitted"),
        plt.Line2D([], [], marker="s", markersize=5, linestyle="none",
                   markerfacecolor=colour, markeredgecolor="black", label="evaluated car"),
        plt.Line2D([], [], marker="s", markersize=5, linestyle="none",
                   markerfacecolor="none", markeredgecolor="#111827",
                   label="vehicle being passed"),
    ]
    figure.legend(handles=handles, loc="lower center", ncol=4, frameon=False,
                  fontsize=6.4, bbox_to_anchor=(0.5, -0.035), handletextpad=0.4,
                  columnspacing=1.0)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for suffix in ("pdf", "png", "svg"):
        figure.savefig(out_dir / f"{args.stem}.{suffix}", dpi=400,
                       bbox_inches="tight", facecolor="white")
    figure.savefig(out_dir / f"{args.stem}.tiff", dpi=600, bbox_inches="tight",
                   facecolor="white", pil_kwargs={"compression": "tiff_lzw"})
    print(f"wrote {out_dir / (args.stem + '.pdf')}")
    for row, steps in zip(rows, steps_rows):
        print(f"  {row['case']}: steps {steps}, target {row['event']['target']}, "
              f"passed car {row['event']['opponent']}, set changes {row['event']['changes']}")


if __name__ == "__main__":
    main()
