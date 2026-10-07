#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Mechanism figure for the corrected-protocol overtaking runs.

Panels
  (a) scene overview with the road corridor and the passing geometry
  (b) dynamic relevance neighbourhood: which vehicles were admitted
  (c) candidate scoring at the decision step
  (d) imagined rollout versus what the simulator actually did
  (e) cross-track / speed / control timeline of the manoeuvre
  (f) control authority: planner decisions versus safety-guard takeovers

Every series keeps the algorithm's fixed colour from scripts.tits_figure_style.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np

from dlc.overtaking_endpoint import TrackProgress
from scripts.tits_figure_style import (
    ALGORITHM_LABELS,
    canonical_algorithm,
    color_for_algorithm,
    configure_publication_matplotlib,
    label_for_algorithm,
)

TRACK_WIDTH = 40.0 / 6.0
CAR_LENGTH = 2.2          # wheel-body extent along the chassis
CAR_WIDTH = 3.24          # wheel-body extent across the chassis


def load_case(case_dir, algorithm):
    case = Path(case_dir)
    stem = None
    for candidate in sorted((case / "traces").glob("*.trace.json")):
        if candidate.name.startswith(f"{algorithm}_"):
            stem = candidate.name[: -len(".trace.json")]
            break
    if stem is None:
        raise FileNotFoundError(f"no trace for {algorithm} in {case/'traces'}")
    trace = json.loads((case / "traces" / f"{stem}.trace.json").read_text(encoding="utf-8"))
    initial = json.loads((case / "traces" / f"{stem}.initial.json").read_text(encoding="utf-8"))
    summary = json.loads((case / "summaries" / f"{stem}.summary.json").read_text(encoding="utf-8"))
    return trace, initial, summary


def track_frame(track):
    points = np.asarray(track, dtype=float)
    centre = points[:, 2:]
    angle = points[:, 1]
    tangent = np.stack([-np.sin(angle), np.cos(angle)], axis=1)
    left = np.stack([-np.cos(angle), -np.sin(angle)], axis=1)
    return centre, tangent, left


def car_polygon(position, angle, scale=1.0):
    forward = np.array([-np.sin(angle), np.cos(angle)])
    left = np.array([-np.cos(angle), -np.sin(angle)])
    half_length = 0.5 * CAR_LENGTH * scale
    half_width = 0.5 * CAR_WIDTH * scale
    return np.array([
        position + half_length * forward + half_width * left,
        position + half_length * forward - half_width * left,
        position - half_length * forward - half_width * left,
        position - half_length * forward + half_width * left,
    ])


def find_maneuver_window(trace, num_agents, pre=40, post=90, approach=(-20.0, -4.0),
                         margin=4.0, hold=50):
    """Locate the overtake the endpoint audit would score.

    The event is the first crossing of a +margin lead over a vehicle that was
    previously approached from [-20, -4] m behind it, which is the P/L
    definition recorded in outputs/.../validity_endpoint_v3_20260920.
    """
    track = np.asarray(trace["track"], dtype=float)
    progress = TrackProgress(track[:, 2:])
    total = progress.length
    target = int(trace["summary_target_agent"])
    gaps = np.zeros((len(trace["steps"]), num_agents))
    for index, row in enumerate(trace["steps"]):
        current = progress.update([row["positions"][agent] for agent in range(num_agents)])
        delta = (current - current[target] + total / 2.0) % total - total / 2.0
        gaps[index] = -delta
    others = [agent for agent in range(num_agents) if agent != target]
    event = None
    for agent in others:
        series = gaps[:, agent]
        approached = np.where((series >= approach[0]) & (series <= approach[1]))[0]
        for anchor in approached:
            crossing = np.where(series[anchor:] >= margin)[0]
            if not len(crossing):
                continue
            complete = int(anchor + crossing[0])
            retained = bool(np.all(series[complete:complete + hold + 1] >= margin))
            event = dict(complete=complete, rival=agent, retained=retained)
            break
        if event is not None:
            break
    if event is None:
        # No scored pass: centre the window on the closest approach instead so
        # that the figure still documents what the controller did.
        closest = int(np.argmin(np.abs(gaps[:, others]).min(axis=1)))
        event = dict(complete=closest, rival=int(others[int(np.argmin(np.abs(gaps[closest, others])))]),
                     retained=False)
    complete = event["complete"]
    rival = event["rival"]
    window = {
        "start": max(0, complete - pre),
        "end": min(len(trace["steps"]) - 1, complete + post),
        "complete": complete,
        "rival": rival,
        "passed": event["retained"],
        "gaps": gaps,
        "others": others,
        "target": target,
        "lead": gaps[:, others].min(axis=1),
    }
    window["alongside"] = int(np.argmin(np.abs(gaps[window["start"]:window["end"] + 1, rival]))) + window["start"]
    return window


def style_axis(axis):
    axis.tick_params(direction="out", length=3.5, width=1.0)
    for spine in ("left", "bottom"):
        axis.spines[spine].set_linewidth(1.0)


def panel_scene(axis, trace, window, colors, target_agent, scene_step, half_span=26.0):
    track = np.asarray(trace["track"], dtype=float)
    centre, tangent, left = track_frame(track)
    axis.plot(centre[:, 0], centre[:, 1], color="#B0B0B0", lw=0.8, ls=(0, (4, 3)), zorder=1)
    for sign in (+1.0, -1.0):
        edge = centre + sign * TRACK_WIDTH * left
        axis.plot(edge[:, 0], edge[:, 1], color="#8A8A8A", lw=0.9, zorder=1)
    axis.fill(
        np.concatenate([centre + TRACK_WIDTH * left, (centre - TRACK_WIDTH * left)[::-1]])[:, 0],
        np.concatenate([centre + TRACK_WIDTH * left, (centre - TRACK_WIDTH * left)[::-1]])[:, 1],
        color="#F2F2F2", zorder=0,
    )
    for agent in range(len(colors)):
        history = np.asarray([row["positions"][agent] for row in trace["steps"][max(0, scene_step - 45):scene_step + 1]], dtype=float)
        axis.plot(history[:, 0], history[:, 1], color=colors[agent], lw=2.2 if agent == target_agent else 1.1,
                  alpha=0.95 if agent == target_agent else 0.7, zorder=3, solid_capstyle="round")
    row = trace["steps"][scene_step]
    for agent in range(len(colors)):
        position = np.asarray(row["positions"][agent], dtype=float)
        polygon = car_polygon(position, row["hull_angles"][agent])
        axis.fill(polygon[:, 0], polygon[:, 1], color=colors[agent],
                  edgecolor="black" if agent == target_agent else "white",
                  lw=1.1 if agent == target_agent else 0.6, zorder=4)
        axis.annotate(f"A{agent}", position, textcoords="offset points", xytext=(7, 7),
                      fontsize=6.8, color="black", zorder=5)
    scale = 10.0
    origin = np.asarray(trace["steps"][scene_step]["positions"][target_agent], dtype=float)
    axis.plot([origin[0] + half_span - 14, origin[0] + half_span - 14 + scale], [origin[1] - half_span + 6] * 2,
              color="black", lw=1.6, zorder=6)
    axis.annotate(f"{scale:.0f} m", (origin[0] + half_span - 14 + scale / 2, origin[1] - half_span + 7.5),
                  fontsize=6.5, ha="center", zorder=6)
    focus = np.asarray(trace["steps"][scene_step]["positions"][target_agent], dtype=float)
    axis.set_xlim(focus[0] - half_span, focus[0] + half_span)
    axis.set_ylim(focus[1] - half_span, focus[1] + half_span)
    axis.set_aspect("equal")
    axis.set_xticks([])
    axis.set_yticks([])
    for spine in axis.spines.values():
        spine.set_visible(False)
    axis.set_title(f"(a) step {scene_step}, corridor $\\pm${TRACK_WIDTH:.1f} m", fontsize=8.5, loc="left")


def panel_neighbours(axis, trace, window, target_agent, color):
    steps = range(window["start"], window["end"] + 1)
    num_agents = len(trace["steps"][0]["positions"])
    others = [agent for agent in range(num_agents) if agent != target_agent]
    ranker_recorded = any(trace["steps"][step].get("target_policy_debug", {}).get("selected_neighbor_ids")
                          for step in steps)
    for row_index, agent in enumerate(others):
        selected, exposed = [], []
        for step in steps:
            debug = trace["steps"][step].get("target_policy_debug", {})
            exposed_ids = debug.get("exposed_neighbor_ids")
            if exposed_ids is None:
                exposed_ids = trace["steps"][step].get("dynamic_neighbor_ids", [None] * num_agents)[target_agent]
            selected_ids = debug.get("selected_neighbor_ids")
            if exposed_ids is not None and agent in exposed_ids:
                exposed.append(step)
            if selected_ids is not None and agent in selected_ids:
                selected.append(step)
        if exposed:
            axis.plot(exposed, [row_index] * len(exposed), ls="none", marker="o", ms=2.6,
                      mfc="white", mec="#9CA3AF", mew=0.7)
        if selected:
            axis.plot(selected, [row_index] * len(selected), ls="none", marker="s", ms=3.0,
                      mfc=color, mec="none")
    axis.set_yticks(range(len(others)))
    axis.set_yticklabels([f"A{agent}" for agent in others], fontsize=7.5)
    axis.set_xlim(window["start"], window["end"])
    axis.set_ylim(-0.6, len(others) - 0.4)
    axis.invert_yaxis()
    axis.set_xlabel("step", fontsize=8)
    axis.grid(axis="x", color="#E5E5E5", lw=0.6)
    axis.set_axisbelow(True)
    axis.set_title("(b) relevance neighbourhood" + ("" if ranker_recorded else ", exposure"),
                   fontsize=8.5, loc="left")
    style_axis(axis)


def panel_candidates(axis, trace, window, color_to_use):
    step = window["alongside"]
    debug = trace["steps"][step].get("target_policy_debug", {})
    records = debug.get("candidate_scores") or []
    if not records:
        axis.text(0.5, 0.5, "no candidate record", ha="center", va="center", fontsize=8)
        axis.set_axis_off()
        return
    actions = np.asarray([item["action"] for item in records], dtype=float)
    scores = np.asarray([item["score"] for item in records], dtype=float)
    selected = np.asarray(debug.get("selected_action", actions[0]), dtype=float)
    best = np.argmax(scores)
    axis.scatter(actions[:, 1], actions[:, 0], s=22 + 60 * (scores - scores.min()) / max(scores.ptp(), 1e-9),
                 facecolor=color_to_use, edgecolor="none", alpha=0.55, zorder=2)
    axis.scatter(actions[best, 1], actions[best, 0], marker="*", s=110, facecolor=color_to_use,
                 edgecolor="black", lw=0.6, zorder=3)
    axis.scatter(np.nan, np.nan, marker="*", s=60, facecolor="white", edgecolor="black",
                 lw=0.6, label="selected")
    axis.set_xlabel("throttle", fontsize=8)
    axis.set_ylabel("steer", fontsize=8)
    axis.set_title(f"(c) {len(records)} candidates scored, step {step}", fontsize=8.5, loc="left")
    style_axis(axis)
    axis.legend(fontsize=7, loc="best", handletextpad=0.4)


def panel_rollout(axis, trace, window, color_to_use, target_agent, horizon_scale=1.0):
    step = window["alongside"]
    debug = trace["steps"][step].get("target_policy_debug", {})
    rollout = debug.get("imagined_rollout")
    if not rollout:
        axis.text(0.5, 0.5, "imagined rollout not recorded\n(run with dump_rollouts)", ha="center",
                  va="center", fontsize=8)
        axis.set_axis_off()
        return
    predicted = np.asarray([state[target_agent][:2] for state in rollout], dtype=float)
    realised = np.asarray([trace["steps"][step + offset]["positions"][target_agent]
                           for offset in range(len(rollout))], dtype=float)
    axis.plot(predicted[:, 0], predicted[:, 1], color=color_to_use, lw=1.7, marker="o", ms=3.6,
              mfc="white", mec=color_to_use, label="world model, imagined")
    axis.plot(realised[:, 0], realised[:, 1], color="black", lw=1.2, ls=(0, (3, 2)), marker="s",
              ms=3.0, mfc="black", label="simulator, realised")
    error = np.linalg.norm(predicted - realised, axis=1)
    axis.set_xlabel("x (m)", fontsize=8)
    axis.set_ylabel("y (m)", fontsize=8)
    axis.set_title(f"(d) {len(rollout) - 1}-step rollout, terminal error {error[-1]:.2f} m",
                   fontsize=8.5, loc="left")
    axis.legend(fontsize=7, loc="best", handletextpad=0.4)
    axis.set_aspect("equal")
    style_axis(axis)


def panel_timeline(axis, trace, window, guard_color):
    steps = list(range(window["start"], window["end"] + 1))
    lateral = np.asarray([abs(trace["steps"][step]["telemetry"]["lateral_error"][trace["summary_target_agent"]])
                          for step in steps], dtype=float)
    speed = np.asarray([trace["steps"][step]["speed"][trace["summary_target_agent"]] for step in steps], dtype=float)
    grass = np.asarray([trace["steps"][step]["telemetry"]["on_grass"][trace["summary_target_agent"]] for step in steps],
                       dtype=bool)
    guard = np.asarray([bool(trace["steps"][step].get("target_policy_debug", {}).get("hard_recovery")) for step in steps])
    for index, step in enumerate(steps):
        if grass[index]:
            axis.axvspan(step - 0.5, step + 0.5, color="#F0E6D2", lw=0, zorder=0)
    axis.plot(steps, lateral, color="#000000", lw=1.3, label="|cross-track| (half-widths)")
    axis.axhline(1.0, color="#8A8A8A", lw=1.0, ls=(0, (4, 3)))
    axis.axhline(0.88, color=guard_color, lw=0.9, ls=(0, (1, 2)))
    axis.set_ylim(0, max(1.1, float(lateral.max()) * 1.05))
    axis.set_ylabel("|lat| (half-widths)", fontsize=7.5)
    twin = axis.twinx()
    twin.plot(steps, speed, color=guard_color, lw=1.1, ls=(0, (5, 2)), label="speed (m/s)")
    twin.set_ylabel("v (m/s)", fontsize=7.5)
    twin.spines["right"].set_visible(True)
    twin.tick_params(direction="out", length=3.5, width=1.0, labelsize=7.5)
    axis.set_xlabel("step", fontsize=8)
    axis.set_title("(e) manoeuvre window: corridor, speed, grass", fontsize=8.5, loc="left")
    style_axis(axis)
    return twin


def panel_gaps(axis, trace, window, own_color):
    steps = np.arange(window["start"], window["end"] + 1)
    gaps = window["gaps"][window["start"]:window["end"] + 1]
    target = window["target"]
    opponents = window["others"]
    for agent in opponents:
        axis.plot(steps, gaps[:, agent], color="#C7C7C7", lw=0.9, zorder=1)
    critical = window["rival"]
    axis.plot(steps, gaps[:, critical], color=own_color, lw=1.6, zorder=3,
              label=f"vehicle passed (A{critical})")
    axis.plot(steps, gaps[:, opponents].min(axis=1), color="black", lw=1.0, ls=(0, (4, 2)),
              zorder=2, label="closest rival ahead")
    axis.axhline(0.0, color="#8A8A8A", lw=0.8)
    axis.axhline(4.0, color="#8A8A8A", lw=0.8, ls=(0, (2, 2)))
    axis.text(steps[0], 4.0, " 4 m lead", fontsize=6.5, va="bottom", color="#555555")
    axis.axvline(window["complete"], color="#555555", lw=0.8, ls=(0, (1, 2)))
    axis.set_xlabel("step", fontsize=8)
    axis.set_ylabel("along-track gap (m)", fontsize=8)
    axis.set_title("(f) passing geometry: gap to rivals", fontsize=8.5, loc="left")
    axis.legend(fontsize=6.5, loc="upper left", handletextpad=0.4)
    style_axis(axis)


def build(case_dir, algorithm, out_path, target_agent=None, scene_step=None):
    steps, initial, summary = load_case(case_dir, algorithm)
    num_agents = int(initial["num_agents"])
    data = {
        "steps": steps,
        "track": np.asarray(initial["track"], dtype=float),
        "summary_target_agent": int(summary.get("target_agent", target_agent if target_agent is not None
                                                else num_agents - 1)),
    }
    stem = summary.get("trace_path")
    stem = Path(stem).name[: -len(".trace.json")] if stem else None
    assignment = []
    colors_path = Path(case_dir) / "summaries" / f"{stem}.colors.json"
    if colors_path.is_file():
        assignment = json.loads(colors_path.read_text(encoding="utf-8"))
    target_agent = data["summary_target_agent"]
    colors = []
    for agent_id in range(num_agents):
        if agent_id < len(assignment):
            colors.append(assignment[agent_id]["color"])
        else:
            colors.append(color_for_algorithm(algorithm) if agent_id == target_agent else "#9CA3AF")
    own_color = color_for_algorithm(algorithm)
    window = find_maneuver_window(data, num_agents)
    if scene_step is None:
        scene_step = window["alongside"]

    configure_publication_matplotlib(font_size=8.5)
    import matplotlib.pyplot as plt

    figure = plt.figure(figsize=(7.16, 5.4))
    grid = figure.add_gridspec(2, 3, height_ratios=[1.2, 1.0], hspace=0.6, wspace=0.55)
    panel_scene(figure.add_subplot(grid[0, 0]), data, window, colors, target_agent, scene_step)
    panel_neighbours(figure.add_subplot(grid[0, 1]), data, window, target_agent, own_color)
    panel_candidates(figure.add_subplot(grid[0, 2]), data, window, own_color)
    panel_rollout(figure.add_subplot(grid[1, 0]), data, window, own_color, target_agent)
    panel_timeline(figure.add_subplot(grid[1, 1]), data, window, own_color)
    panel_gaps(figure.add_subplot(grid[1, 2]), data, window, own_color)
    case_name = Path(case_dir).name
    outcome = (f"pass of A{window['rival']} retained" if window["passed"]
               else f"no retained pass of A{window['rival']}")
    figure.suptitle(
        f"{label_for_algorithm(algorithm)} on {case_name} (seed {summary.get('seed')}, "
        f"n={summary.get('num_agents')}): {outcome}, crossing at step {window['complete']}",
        fontsize=9, y=0.99,
    )
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(out, bbox_inches="tight", dpi=400)
    figure.savefig(out.with_suffix(".png"), bbox_inches="tight", dpi=400)
    plt.close(figure)
    print(f"wrote {out} and {out.with_suffix('.png')}")
    return window


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-dir", required=True)
    parser.add_argument("--algorithm", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--scene-step", type=int, default=None)
    args = parser.parse_args()
    build(args.case_dir, args.algorithm, args.out, scene_step=args.scene_step)


if __name__ == "__main__":
    main()
