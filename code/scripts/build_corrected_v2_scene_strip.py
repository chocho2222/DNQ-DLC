#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Zoomed top-down snapshot strip of one overtaking manoeuvre.

Panels are drawn from the recorded trace (positions, hull angles, road
centre line), not from a video frame, so the geometry is exact, the road edge
is the same one the endpoint audit uses, and every vehicle keeps the colour the
algorithm owns in `scripts/tits_figure_style`. The strip is meant to sit next to
the mechanism figure as the "what the manoeuvre looks like" panel.

Usage:
    python3 scripts/build_corrected_v2_scene_strip.py --case-dir <run> \
        --algorithm ours_corrected_v2_best --out <png> [--steps 120,150,180,210]
"""
import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.tits_figure_style import (
    PALETTE,
    color_for_algorithm,
    configure_publication_matplotlib,
    label_for_algorithm,
)
from scripts.audit_validity_endpoint_v3 import (
    circular_delta,
    detect_events,
    track_frames,
    track_geometry,
    unwrapped_progress,
)

TRACK_WIDTH = 40.0 / 6.0
CAR_LENGTH = 5.0
CAR_WIDTH = 2.76
PANEL_WINDOW_M = 46.0
# One colour per controller: every background vehicle is driven by the same
# lane-keeping profile, so it carries the neutral traffic colour rather than a
# positional ramp that would collide with an algorithm's own colour.
TRAFFIC_COLOR = PALETTE["neutral_mid"]


def load_case(case_dir, algorithm):
    case_dir = Path(case_dir)
    stem = None
    for path in (case_dir / "traces").glob(f"{algorithm}_*.trace.json"):
        stem = path.name[: -len(".trace.json")]
        break
    if stem is None:
        raise SystemExit(f"no trace for {algorithm} in {case_dir}")
    trace = json.load(open(case_dir / "traces" / f"{stem}.trace.json"))
    initial = json.load(open(case_dir / "traces" / f"{stem}.initial.json"))
    summary = json.load(open(case_dir / "summaries" / f"{stem}.summary.json"))
    return trace, initial, summary


def road_polygon(track):
    centre = np.asarray(track, float)[:, 2:4]
    beta = np.asarray(track, float)[:, 1]
    normal = np.stack([np.cos(beta), np.sin(beta)], axis=1)
    left = centre + TRACK_WIDTH * normal
    right = centre - TRACK_WIDTH * normal
    return centre, left, right


def car_polygon(x, y, angle):
    forward = np.array([-math.sin(angle), math.cos(angle)])
    side = np.array([math.cos(angle), math.sin(angle)])
    centre = np.array([x, y])
    corners = []
    for along, across in ((0.5, 0.5), (0.5, -0.5), (-0.5, -0.5), (-0.5, 0.5)):
        corners.append(centre + along * CAR_LENGTH * forward + across * CAR_WIDTH * side)
    return np.array(corners)


def audit_series(trace, points, ego, approach=20.0, margin=4.0, opponent=None, event_index=0):
    """Audit-defined event indices and the along-track gap series.

    Panels are cut at the very indices the strict-endpoint audit uses, so the
    strip cannot disagree with the table it illustrates.
    """
    cumulative, lap, _ = track_geometry(points)
    events = detect_events(trace, ego, cumulative, lap, approach, margin)
    if not events:
        return None
    if opponent is not None:
        selected = [item for item in events if int(item["opponent"]) == int(opponent)]
        if selected:
            events = selected
    event = events[min(max(event_index, 0), len(events) - 1)]
    rival = int(event["opponent"])
    target_s = unwrapped_progress(trace, ego, cumulative, lap)
    rival_s = unwrapped_progress(trace, rival, cumulative, lap)
    offset = (target_s[0] - rival_s[0]) - circular_delta(target_s[0], rival_s[0], lap)
    rel = [a - b - offset for a, b in zip(target_s, rival_s)]
    return {"event": event, "opponent": rival, "rel": rel,
            "start_index": int(event["start_index"]),
            "complete_index": int(event["complete_index"]),
            "event_count": len(events)}


def choose_steps(series, trace, ego, summary):
    if series is not None:
        start = series["start_index"]
        complete = series["complete_index"]
        span = max(complete - start, 40)
        picks = [start, start + int(0.45 * span), start + int(0.8 * span), complete + 12]
        return [min(max(p, 0), len(trace) - 1) for p in picks]
    events = summary.get("overtake_events") or []
    if events:
        first = events[0]
        start = int(first.get("start_step", 0))
        complete = int(first.get("complete_step", start))
        span = max(complete - start, 40)
        return [min(max(p, 0), len(trace) - 1)
                for p in (start, start + int(0.45 * span), start + int(0.8 * span), complete + 12)]
    return [int(len(trace) * f) for f in (0.2, 0.35, 0.5, 0.65)]


def build(case_dir, algorithm, out_path, steps=None, event_index=0, opponent=None,
          approach=20.0, margin=4.0, timeline=False):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon

    configure_publication_matplotlib(font_size=9.0)
    trace, initial, summary = load_case(case_dir, algorithm)
    centre, left, right = road_polygon(initial["track"])
    ego = int(summary.get("target_agent", len(trace[0]["positions"]) - 1))
    points = np.asarray(initial["track"], float)[:, 2:4]
    series = audit_series(trace, points, ego, approach=approach, margin=margin,
                          opponent=opponent, event_index=event_index)
    steps = steps or choose_steps(series, trace, ego, summary)
    color = color_for_algorithm(algorithm)
    margin = margin

    if timeline:
        figure = plt.figure(figsize=(3.1 * len(steps), 4.6))
        grid = figure.add_gridspec(2, len(steps), height_ratios=[1.0, 0.42], hspace=0.32)
        axes = [figure.add_subplot(grid[0, index]) for index in range(len(steps))]
        timeline_axis = figure.add_subplot(grid[1, :])
    else:
        figure, axes = plt.subplots(1, len(steps), figsize=(3.1 * len(steps), 3.5))
        if len(steps) == 1:
            axes = [axes]
        timeline_axis = None
    half = PANEL_WINDOW_M / 2.0
    for axis, step in zip(axes, steps):
        row = trace[int(step)]
        positions = row["positions"]
        angles = row["hull_angles"]
        ego_xy = np.asarray(positions[ego], float)
        axis.add_patch(Polygon(np.vstack([left, right[::-1]]), closed=True,
                               facecolor="#EDEDED", edgecolor="#9CA3AF", linewidth=1.0, zorder=1))
        axis.plot(centre[:, 0], centre[:, 1], linestyle=(0, (4, 3)), color="#9CA3AF",
                  linewidth=0.8, zorder=2)
        for index, (xy, angle) in enumerate(zip(positions, angles)):
            offset_xy = np.asarray(xy, float) - ego_xy
            if max(abs(offset_xy[0]), abs(offset_xy[1])) > half - 0.6 * CAR_LENGTH:
                # A vehicle whose centre leaves the panel window would be drawn
                # as a clipped wedge; the identity is carried by the panels
                # where it is fully visible instead.
                continue
            is_ego = index == ego
            axis.add_patch(Polygon(car_polygon(*xy, angle), closed=True, zorder=4 if is_ego else 3,
                                   facecolor=color if is_ego else TRAFFIC_COLOR,
                                   edgecolor="black" if is_ego else "#374151",
                                   linewidth=1.2 if is_ego else 0.6, alpha=1.0 if is_ego else 0.85))
            axis.annotate(f"A{index}", xy, xytext=(4, 4), textcoords="offset points",
                          fontsize=7.5, zorder=5,
                          color="black" if is_ego else "#4B5563")
        axis.plot(np.asarray([r["positions"][ego] for r in trace[: int(step) + 1]])[:, 0],
                  np.asarray([r["positions"][ego] for r in trace[: int(step) + 1]])[:, 1],
                  color=color, linewidth=1.4, alpha=0.55, zorder=3)
        axis.set_xlim(ego_xy[0] - half, ego_xy[0] + half)
        axis.set_ylim(ego_xy[1] - half, ego_xy[1] + half)
        axis.set_aspect("equal")
        speed = float(row["speed"][ego])
        annotation = f"v={speed:.1f} m/s"
        if series is not None:
            gap = float(series["rel"][int(step)])
            state = "ahead of A%d" % series["opponent"] if gap >= margin else (
                "alongside A%d" % series["opponent"] if gap > -margin else "behind A%d" % series["opponent"])
            annotation += "\n$\\Delta s_{A%d}$=%+.1f m (%s)" % (series["opponent"], gap, state)
        axis.set_title(f"step {int(step)}", fontsize=9)
        axis.text(0.02, 0.02, annotation, transform=axis.transAxes, fontsize=7.2,
                  va="bottom", ha="left", color="#1F2937")
        axis.set_xticks([])
        axis.set_yticks([])
        for spine in axis.spines.values():
            spine.set_visible(False)
    if timeline_axis is not None and series is not None:
        rel = np.asarray(series["rel"], float)
        steps_axis = np.arange(len(rel))
        timeline_axis.axhspan(-margin, margin, color=PALETTE["neutral_light"], alpha=0.55,
                              label="alongside band ($\\pm$%.0f m)" % margin)
        timeline_axis.plot(steps_axis, rel, color=color, linewidth=1.4,
                           label="$\\Delta s$ to A%d" % series["opponent"])
        for step in steps:
            timeline_axis.axvline(int(step), color=PALETTE["neutral_dark"], linewidth=0.7,
                                  linestyle=(0, (2, 2)))
        timeline_axis.axvline(series["start_index"], color=PALETTE["neutral_dark"], linewidth=1.0)
        timeline_axis.axvline(series["complete_index"], color=PALETTE["neutral_dark"], linewidth=1.0)
        timeline_axis.annotate("approach", (series["start_index"], rel.min()),
                               textcoords="offset points", xytext=(3, 2), fontsize=7)
        timeline_axis.annotate("pass", (series["complete_index"], rel.max()),
                               textcoords="offset points", xytext=(3, -10), fontsize=7)
        timeline_axis.set_xlim(0, len(rel) - 1)
        timeline_axis.set_xlabel("simulation step", fontsize=8)
        timeline_axis.set_ylabel("$\\Delta s$ (m)", fontsize=8)
        timeline_axis.tick_params(labelsize=7.5)
        timeline_axis.grid(color="#E5E7EB", linewidth=0.6)
        timeline_axis.legend(fontsize=7, loc="upper left", frameon=False)
        for side in ("top", "right"):
            timeline_axis.spines[side].set_visible(False)
    heading = f"{label_for_algorithm(algorithm)}: {Path(case_dir).name}"
    if series is not None:
        heading += ("  (audit event %d/%d vs A%d: approach step %d, pass step %d)"
                    % (event_index + 1, series["event_count"], series["opponent"],
                       series["start_index"], series["complete_index"]))
    figure.suptitle(heading, fontsize=10, y=0.99)
    figure.tight_layout(rect=(0, 0, 1, 0.94))
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(out_path, dpi=300)
    figure.savefig(str(out_path).replace(".png", ".pdf"))
    print(f"wrote {out_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-dir", required=True)
    parser.add_argument("--algorithm", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--steps", default="")
    parser.add_argument("--event-index", type=int, default=0,
                        help="which audited overtaking event to cut panels around")
    parser.add_argument("--opponent", type=int, default=None)
    parser.add_argument("--pass-margin", type=float, default=4.0)
    parser.add_argument("--approach-distance", type=float, default=20.0)
    parser.add_argument("--timeline", action="store_true",
                        help="add the audit gap trace below the panels")
    args = parser.parse_args()
    steps = [int(x) for x in args.steps.split(",") if x.strip()] or None
    build(args.case_dir, args.algorithm, args.out, steps,
          event_index=args.event_index, opponent=args.opponent,
          approach=args.approach_distance, margin=args.pass_margin,
          timeline=args.timeline)


if __name__ == "__main__":
    main()
