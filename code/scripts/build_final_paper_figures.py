#!/usr/bin/env python
"""Figures for the main comparison, the fleet-size sweep and the mechanism panel.

Every number is read from the audit and controller-signal tables produced by the
final matrix; nothing is recomputed here beyond means and Wilson intervals, so a
figure cannot drift away from the table it illustrates. Colours come from the
fixed per-algorithm vocabulary, so an algorithm keeps one colour across all
figures, screenshots and video frames of the submission.
"""

import argparse
import csv
import math
from collections import defaultdict
from pathlib import Path

import numpy as np

import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.tits_figure_style import (
    color_for_algorithm,
    configure_publication_matplotlib,
    label_for_algorithm,
    marker_for_algorithm,
)

ORDER = [
    "ours_dnq_dlc",
    "rule_expert_gate",
    "dlc_joint_transition_observer",
    "dlc_individual_transition",
    "dlc_joint_transition",
    "ppo_continuous",
    "sac_continuous",
    "td3_continuous",
]
# The methods that complete enough passes for a pass-level average to mean
# anything. PPO, SAC and TD3 find 15, 1 and 2 passes over the 48 cases, so they
# are reported in the tables but not averaged here.
PASS_ORDER = [
    "ours_dnq_dlc",
    "rule_expert_gate",
    "dlc_individual_transition",
    "dlc_joint_transition",
    "dlc_joint_transition_observer",
]
# Compact axis names for Fig. 2, where the eight methods share a panel of
# column width. The caption gives the full names; the colours are the fixed
# per-algorithm colours shared by every figure of the manuscript.
SHORT_LABELS = {
    "ours_dnq_dlc": "Ours",
    "rule_expert_gate": "Rule",
    "dlc_joint_transition_observer": "JTO",
    "dlc_individual_transition": "IT",
    "dlc_joint_transition": "JT",
    "ppo_continuous": "PPO",
    "sac_continuous": "SAC",
    "td3_continuous": "TD3",
}
SCALES = ["M4_sparse", "M6_dense", "M8_scale", "M10_scale"]
SCALE_LABELS = {"M4_sparse": "4", "M6_dense": "6", "M8_scale": "8", "M10_scale": "10"}

# Every figure is laid out at the width it prints at: the text block of the
# IEEEtran journal layout is 517 pt and a column is 252 pt, so the canvases
# below are 7.17 in, 5.02 in and 3.50 in and the font sizes are the printed
# point sizes. Drawing at a larger canvas and shrinking it at \includegraphics
# time would scale the type down with it.
WIDE = 7.17
HALF = 5.02
COLUMN = 3.50
PUBLICATION_FONTS = {
    "font.size": 7.0,
    "axes.labelsize": 7.4,
    "xtick.labelsize": 6.9,
    "ytick.labelsize": 6.9,
    "legend.fontsize": 6.4,
}


def wilson(k, n, z=1.96):
    if n == 0:
        return 0.0, 0.0
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(centre - half, 0.0), min(centre + half, 1.0)


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def num(row, key):
    value = row.get(key, "")
    return float("nan") if value in ("", "nan", None) else float(value)


# Whole-episode containment, keyed by (algorithm, case directory). The audit's
# grass_fraction is defined on the manoeuvre window and therefore exists only
# for cases that complete a pass, which gives every arm a different denominator.
# The episode measure is defined for all 48 cases of every arm and is the one
# the figures plot.
EPISODE = {}
EPISODE_LAT = {}


def load_episode_containment(path):
    with open(path) as handle:
        for row in csv.DictReader(handle):
            EPISODE[(row["algorithm"], row["case"])] = float(row["episode_grass"])
            EPISODE_LAT[(row["algorithm"], row["case"])] = float(row["episode_lat"])


def episode_grass(row):
    return EPISODE.get((row["algorithm"], row.get("case_dir", "")), float("nan"))


def episode_lat(row):
    return EPISODE_LAT.get((row["algorithm"], row.get("case_dir", "")), float("nan"))


# The three continuous-control baselines are re-evaluated over five training
# seeds under the same protocol. Their runs are pooled into the continuous
# panels, so a family is 240 case-runs rather than 48, and the tier panels
# report the mean rate with the range the five seeds span.
RL_FAMILY = {"ppo": "ppo_continuous", "sac": "sac_continuous", "td3": "td3_continuous"}
RL_ROWS = []

# The proposed controller is likewise evaluated once per world-model training
# seed on the same 48 cases. It keeps its own label, but its runs are pooled
# under the same key scheme so the tier panels treat it like the other arms
# that have a seed spread.
OURS = "ours_dnq_dlc"
OURS_ROWS = []
DLC_VARIANTS = ("dlc_individual_transition", "dlc_joint_transition",
                "dlc_joint_transition_observer")
DLC_ROWS = []
RESAMPLED = {OURS} | set(RL_FAMILY.values()) | set(DLC_VARIANTS)
RESAMPLED_ROWS = []


def canonical_algorithm(name):
    """One label per submitted controller, whatever seed the run carries.

    The proposed controller is re-evaluated once per world-model draw and the
    three continuous-control families once per training seed, so the audit
    tables name the runs ``ours_dnq_dlc_seed13`` and ``ppo_seed2026001``. The
    figures plot one row per submitted method, and the seed spread is carried
    by ``training_seed`` rather than by the label.
    """
    if name.startswith("ours_dnq_dlc_seed") or name == "ours_dnq_dlc":
        return OURS
    head = name.split("_seed")[0]
    return RL_FAMILY.get(head, name)


def load_dlc_draws(root):
    """The four retraining draws of the three world-model variants.

    Each variant keeps its own label and is pooled over the draws, so the
    figure reports the same recipe means as the main table instead of the
    single draw that was submitted first.
    """
    DLC_ROWS.clear()
    for draw_dir in sorted(Path(root).glob("draw_*")):
        draw = draw_dir.name.split("_", 1)[1]
        for row in read_csv(draw_dir / "case_level.csv"):
            if row.get("status") != "ok" or row["algorithm"] not in DLC_VARIANTS:
                continue
            DLC_ROWS.append({**row,
                             "case_dir": f"{row['experiment_id']}_n{row['num_agents']}"
                                         f"_seed{row['seed']}__ts{draw}",
                             "training_seed": draw})


def load_dlc_containment(root):
    for draw_dir in sorted(Path(root).glob("draw_*")):
        draw = draw_dir.name.split("_", 1)[1]
        with open(draw_dir / "containment_episode_level.csv") as handle:
            for row in csv.DictReader(handle):
                if row["algorithm"] not in DLC_VARIANTS:
                    continue
                key = f"{row['case']}__ts{draw}"
                EPISODE[(row["algorithm"], key)] = float(row["episode_grass"])
                EPISODE_LAT[(row["algorithm"], key)] = float(row["episode_lat"])


def load_rl_strict(path):
    """Read the strict RL audit and relabel each arm as its algorithm family."""
    RL_ROWS.clear()
    for row in read_csv(path):
        if row.get("status") != "ok":
            continue
        family = RL_FAMILY.get(row["algorithm"].split("_seed")[0])
        if family is None:
            continue
        training_seed = row["algorithm"].split("_seed")[1]
        RL_ROWS.append({**row, "algorithm": family,
                        # The containment lookup has to keep the five training
                        # seeds of one family apart, so the case key carries it.
                        "case_dir": f"{row['experiment_id']}_n{row['num_agents']}"
                                    f"_seed{row['seed']}__ts{training_seed}",
                        "training_seed": training_seed})


def ours_train_tag(algorithm):
    """Training-run tag of a proposed-controller arm.

    The arm is either one world-model checkpoint (``ours_dnq_dlc_seed13``) or a
    fused policy that carries no seed of its own (``ours_dnq_dlc_ensemble``).
    Both are pooled onto the single ``ours_dnq_dlc`` label, and the tag keeps
    the per-run episode lookup of the fused arm separate from the per-seed one.
    """
    head, _, tail = algorithm.partition("_seed")
    return tail if tail else "fused"


def load_ours_seedspread(path):
    """Read the proposed controller's per-run audit and pool it onto one label."""
    path = Path(path)
    if path.is_dir():
        path = path / "case_level.csv"
    OURS_ROWS.clear()
    for row in read_csv(path):
        if row.get("status") != "ok" or not row["algorithm"].startswith(OURS):
            continue
        training_seed = ours_train_tag(row["algorithm"])
        OURS_ROWS.append({**row, "algorithm": OURS,
                          "case_dir": f"{row['experiment_id']}_n{row['num_agents']}"
                                      f"_seed{row['seed']}__ts{training_seed}",
                          "training_seed": training_seed})


def seed_rates(algorithm, key):
    """Per-training-run rate of one resampled arm on the 48 shared cases."""
    per_seed = defaultdict(list)
    for row in RESAMPLED_ROWS:
        if row["algorithm"] == algorithm:
            per_seed[row["training_seed"]].append(1.0 if row[key] == "True" else 0.0)
    return [float(np.mean(v)) for v in per_seed.values()]


def load_ours_containment(path):
    """Whole-episode containment of the proposed controller's seeds."""
    path = Path(path)
    if path.is_dir():
        path = path / "episode_level.csv"
    with open(path) as handle:
        for row in csv.DictReader(handle):
            if not row["algorithm"].startswith(OURS):
                continue
            training_seed = ours_train_tag(row["algorithm"])
            EPISODE[(OURS, f"{row['case']}__ts{training_seed}")] = float(row["episode_grass"])
            EPISODE_LAT[(OURS, f"{row['case']}__ts{training_seed}")] = float(row["episode_lat"])


def load_rl_containment(path):
    """Whole-episode containment of the strict RL arms, relabelled by family."""
    with open(path) as handle:
        for row in csv.DictReader(handle):
            family = RL_FAMILY.get(row["algorithm"].split("_seed")[0])
            if family is None:
                continue
            training_seed = row["algorithm"].split("_seed")[1]
            key = f"{row['case']}__ts{training_seed}"
            EPISODE[(family, key)] = float(row["episode_grass"])
            EPISODE_LAT[(family, key)] = float(row["episode_lat"])


def mean(values):
    values = [v for v in values if v == v]
    return float(np.mean(values)) if values else float("nan")


def collapse_draws(rows):
    """One row per method and fleet size, averaged over the training draws.

    The controller-signal and admitted-size tables carry a row for every
    (fleet size, draw) pair. The mechanism figure reads one profile per fleet
    size, so a numeric column is averaged over the draws of its recipe and a
    column that is not numeric, such as the method label, is carried over.
    """
    groups, order = {}, []
    for row in rows:
        key = (row["algorithm"], row["experiment_id"], row.get("admitted_size"))
        if key not in groups:
            groups[key], _ = [], order.append(key)
        groups[key].append(row)
    out = []
    for key in order:
        group = groups[key]
        if len(group) == 1:
            out.append(group[0])
            continue
        merged = dict(group[0])
        for name in list(group[0]):
            values = []
            for row in group:
                try:
                    values.append(num(row, name))
                except ValueError:
                    break
            else:
                averages = [v for v in values if v == v]
                if len(averages) == len(group):
                    merged[name] = float(np.mean(averages))
        out.append(merged)
    return out


def rate_ci(rows, key):
    k = sum(1 for r in rows if r[key] == "True")
    low, high = wilson(k, len(rows))
    return k / len(rows), k, len(rows), low, high


def mean_ci(values, z=1.96):
    """Mean and the normal-approximation 95 % interval of the mean."""
    values = [v for v in values if v == v]
    if not values:
        return float("nan"), float("nan"), float("nan")
    centre = float(np.mean(values))
    if len(values) < 2:
        return centre, centre, centre
    half = z * float(np.std(values, ddof=1)) / (len(values) ** 0.5)
    return centre, centre - half, centre + half


def _kde_curve(values, grid, bandwidth=0.55):
    """Gaussian KDE of one method's values on a fixed grid.

    A method whose cases all land on the same value (SAC and TD3 sit on one
    grass fraction for long stretches) has no sample standard deviation for a
    kernel density, so that case is drawn as a narrow spike rather than
    raising.
    """
    from scipy.stats import gaussian_kde

    if values.size == 0:
        return np.zeros_like(grid)
    if values.size < 3 or float(np.std(values)) < 1e-9:
        curve = np.zeros_like(grid)
        centre = int(np.argmin(np.abs(grid - float(np.mean(values)))))
        curve[max(centre - 1, 0):centre + 2] = 1.0
        return curve
    return gaussian_kde(values, bw_method=bandwidth)(grid)


def panel_letter(ax, letter):
    """A bare panel letter above the axes, the way the journal sets subpanels.

    The panels carry no descriptive titles: every one of them is named in the
    caption, and a title inside the axes competes with the axis labels and eats
    the vertical space the data needs. The letter is tagged so that the overlap
    checker can tell it apart from an annotation that has to clear the marks.
    """
    from matplotlib import rcParams

    ax._panel_letter = letter
    artist = ax.text(0.005, 1.035, f"({letter})", transform=ax.transAxes,
                     fontsize=rcParams["font.size"] + 1.6, fontweight="bold",
                     ha="left", va="bottom")
    artist.set_gid("panel-letter")
    return artist


def raincloud_row(ax, values, x, colour, span, cloud=0.30, rain=0.30, scale="linear"):
    """One horizontal raincloud, read from left to right.

    The 48 cases of a method are drawn as jittered dots to the left of the
    method position, the interquartile box with its median and mean sits at the
    position, and the kernel density of the same cases extends to the right.
    The three marks therefore read as one distribution in the order the eye
    moves: the individual cases, their quartiles, and their shape. Nothing is
    drawn far enough from the position to reach a neighbouring method, so the
    eight distributions stay separable at column width.
    """
    from matplotlib.patches import Rectangle

    values = np.asarray([v for v in values if v == v], dtype=float)
    if values.size == 0:
        return
    # The density grid runs past the plotted span, so the band closes inside
    # the axes instead of being cut off by the top or bottom limit.
    if scale == "log":
        grid = np.logspace(np.log10(span[0]) - 0.25, np.log10(span[1]) + 0.25, 260)
    else:
        pad = 0.22 * (span[1] - span[0])
        grid = np.linspace(span[0] - pad, span[1] + pad, 260)
    density = _kde_curve(values, grid)
    peak = float(density.max())
    if peak > 0:
        density = density / peak
    # The fill is drawn without an outline: the lower edge of the band is the
    # zero-density line, and an outline there would print as a vertical rule
    # through every method. The density profile itself is stroked instead.
    ax.fill_betweenx(grid, x + 0.045, x + 0.045 + cloud * density, color=colour,
                     alpha=0.45, linewidth=0.0, edgecolor="none", zorder=2)
    visible = density >= 0.02
    ax.plot(x + 0.045 + cloud * density[visible], grid[visible], color="black",
            linewidth=0.35, zorder=2.1)
    q1, median, q3 = np.percentile(values, [25, 50, 75])
    room = 0.012 * (span[1] - span[0])
    height = max(q3 - q1, room)
    ax.add_patch(Rectangle((x - 0.075, q1), 0.10, height,
                           facecolor=colour, edgecolor="black", linewidth=0.5, zorder=3))
    ax.plot([x - 0.075, x + 0.025], [median, median], color="black", linewidth=1.0,
            solid_capstyle="butt", zorder=4)
    ax.plot([x - 0.025], [float(np.mean(values))], marker="o", markersize=2.4,
            markerfacecolor="white", markeredgecolor="black", markeredgewidth=0.45,
            linestyle="none", zorder=5)
    rng = np.random.default_rng(7 + int(x))
    jitter = rng.uniform(0.0, rain, size=values.size)
    ax.scatter(x - 0.40 + jitter, values, s=2.4, color=colour, alpha=0.85,
               linewidths=0, zorder=1)


TIERS = (
    ("P", "o", "physical pass"),
    ("E_full", "s", "strict tier"),
    ("E_race", "^", "racing-rival tier"),
)


def figure_endpoints(cases, out_dir):
    """Primary outcome on top, containment below, the trade-off at the corner.

    The eight controllers keep the same order along the horizontal axis in
    every panel, so a method is read in the same place six times. Panels (a),
    (b), (d) and (e) are rainclouds over the 48 cases of each method, drawn
    left to right as the individual cases, the interquartile box and the kernel
    density. Panel (c) gives the share of cases reaching each endpoint tier with
    Wilson intervals on the same eight positions, and panel (f) places every
    method on the completion-against-containment plane. No panel carries a
    title; the caption names them.
    """
    import matplotlib.pyplot as plt

    with plt.rc_context(PUBLICATION_FONTS):
        return _figure_endpoints(cases, out_dir, plt)


def _figure_endpoints(cases, out_dir, plt):
    fig, grid = plt.subplots(2, 3, figsize=(HALF * 1.15, 3.42),
                             gridspec_kw={"hspace": 0.46, "wspace": 0.42})
    x = np.arange(len(ORDER))

    rain = (
        (grid[0][0], "a", "rank_gain", (0.0, 11.0), "positions gained per case", "linear"),
        (grid[0][1], "b", "event_count", (0.0, 17.0), "physical passes per case", "linear"),
        (grid[1][0], "d", episode_grass, (0.0, 1.0), "grass fraction over the episode", "linear"),
        # The continuous-control agents run to 15 half widths here, so the
        # lateral panel is logarithmic rather than a linear axis that would cut
        # their distributions off in the middle.
        (grid[1][1], "e", episode_lat, (0.1, 20.0), "mean $|\\ell|$ (half widths)", "log"),
    )
    for ax, letter, key, span, ylabel, scale in rain:
        for index, algo in enumerate(ORDER):
            rows = [r for r in cases if r["algorithm"] == algo]
            values = np.array([num(r, key) if isinstance(key, str) else key(r) for r in rows])
            raincloud_row(ax, values, index, color_for_algorithm(algo), span, scale=scale)
        if scale == "log":
            ax.set_yscale("log")
            ax.set_ylim(span[0] * 0.7, span[1] * 1.5)
            ax.set_yticks([0.1, 1.0, 10.0])
            ax.set_yticklabels(["0.1", "1", "10"])
            ax.minorticks_off()
        else:
            pad = 0.03 * (span[1] - span[0])
            ax.set_ylim(span[0] - pad, span[1] + pad)
        ax.set_xlim(-0.62, len(ORDER) - 0.55)
        ax.set_ylabel(ylabel)
        panel_letter(ax, letter)
        ax.grid(axis="y", color="0.88", linewidth=0.5, zorder=0)
        ax.set_axisbelow(True)

    ax = grid[0][2]
    for index, algo in enumerate(ORDER):
        rows = [r for r in cases if r["algorithm"] == algo]
        # A retrained RL family has five runs per case, so its rate is the mean
        # over training seeds and the bar spans the seeds rather than a Wilson
        # interval over cases that are not independent of one another.
        # An arm carries a seed spread only once its per-seed rows have been
        # pooled in; the flag is read off the rows rather than the label so the
        # script also works when a pooled audit is not supplied.
        resampled = len({r.get("training_seed") for r in rows}) > 1
        for offset, (key, marker, _label) in zip((-0.22, 0.0, 0.22), TIERS):
            if resampled:
                per_seed = seed_rates(algo, key)
                rate, low, high = mean(per_seed), min(per_seed), max(per_seed)
            else:
                rate, _k, _n, low, high = rate_ci(rows, key)
            ax.errorbar(index + offset, rate, yerr=[[rate - low], [high - rate]],
                        marker=marker, markersize=3.3, color=color_for_algorithm(algo),
                        markeredgecolor="black", markeredgewidth=0.4, linewidth=0,
                        elinewidth=0.9, capsize=1.3)
    # The three tiers are told apart by their marker, which the caption names;
    # a legend inside this narrow panel would either sit on the intervals of
    # the methods that pass often or push them into the lower half.
    ax.set_ylim(-0.07, 1.12)
    ax.set_xlim(-0.62, len(ORDER) - 0.55)
    ax.set_ylabel("share of cases")
    panel_letter(ax, "c")
    ax.grid(axis="y", color="0.88", linewidth=0.5, zorder=0)
    ax.set_axisbelow(True)

    ax = grid[1][2]
    points = []
    for algo in ORDER:
        rows = [r for r in cases if r["algorithm"] == algo]
        grass = mean([episode_grass(r) for r in rows])
        if len({r.get("training_seed") for r in rows}) > 1:
            per_seed = seed_rates(algo, "P")
            rate, low, high = mean(per_seed), min(per_seed), max(per_seed)
        else:
            rate, _k, _n, low, high = rate_ci(rows, "P")
        ax.errorbar(grass, rate, yerr=[[rate - low], [high - rate]],
                    marker=marker_for_algorithm(algo), color=color_for_algorithm(algo),
                    markersize=4.4, linewidth=0, elinewidth=1.0, capsize=1.8,
                    markeredgecolor="black", markeredgewidth=0.5)
        points.append((algo, grass, rate, low, high))
    ax.set_xlim(-0.07, 1.07)
    ax.set_ylim(-0.10, 1.22)
    ax.set_xlabel("grass fraction over the episode")
    ax.set_ylabel("physical-pass rate")
    panel_letter(ax, "f")
    ax.grid(color="0.88", linewidth=0.5, zorder=0)
    ax.set_axisbelow(True)
    for ax in (grid[0][0], grid[0][1], grid[0][2], grid[1][0], grid[1][1]):
        ax.set_xticks(x)
    for ax in (grid[0][0], grid[0][1], grid[1][0], grid[1][1]):
        ax.set_xticklabels([SHORT_LABELS[a] for a in ORDER], rotation=38, ha="right")
    grid[0][2].set_xticklabels([])
    # Panel (f) is labelled with a legend rather than with leaders. Eight
    # methods inside a half-column panel need five crossing leaders to reach
    # their marks, and the crossing is what a reader follows to the wrong
    # method; the free lower-right corner holds the legend without touching a
    # mark. The empty region is checked by ``scripts/check_figure_annotations.py``
    # like every other annotation.
    fig.tight_layout()
    # The labels are placed after the layout is final: an offset that clears
    # every mark in a provisional geometry can land on one once the axes move.
    # The panel is named explicitly here: the tick loops above rebind ``ax``.
    _place_labels_without_overlap(grid[1][2], points)
    return _save(fig, out_dir / "figure_main_endpoints")


def _overlap_area(a, b):
    """Area shared by two display boxes, zero when they are disjoint."""
    dx = min(a.x1, b.x1) - max(a.x0, b.x0)
    dy = min(a.y1, b.y1) - max(a.y0, b.y0)
    return dx * dy if dx > 0 and dy > 0 else 0.0


def _box_entry(marker, anchor, box):
    """Where the segment from ``marker`` to ``anchor`` first meets ``box``.

    The label carries a partly transparent background, so a leader line drawn
    all the way to the text anchor would show through it as a ghost. Stopping
    the line at the box edge keeps the callout clean.
    """
    dx, dy = anchor[0] - marker[0], anchor[1] - marker[1]
    crossings = []
    if dx:
        crossings += [(box.x0 - marker[0]) / dx, (box.x1 - marker[0]) / dx]
    if dy:
        crossings += [(box.y0 - marker[1]) / dy, (box.y1 - marker[1]) / dy]
    best = 1.0
    for t in crossings:
        if 0.0 < t <= best:
            px, py = marker[0] + dx * t, marker[1] + dy * t
            if (box.x0 - 0.6 <= px <= box.x1 + 0.6
                    and box.y0 - 0.6 <= py <= box.y1 + 0.6):
                best = t
    return (marker[0] + dx * best, marker[1] + dy * best)


def _place_labels_without_overlap(ax, points):
    """Place the method labels so that nothing collides.

    The panel packs eight controllers into a narrow strip, so a fixed offset
    puts labels on top of the markers and on top of each other. Each label is
    tried at a ring of offsets and the first one that clears the markers already
    drawn, the labels already placed and the panel bounds is used.
    """
    from matplotlib.transforms import Bbox

    fig = ax.figure
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    panel = ax.get_window_extent(renderer=renderer)

    from matplotlib import rcParams

    size = rcParams["font.size"] - 0.2
    candidates = []
    for dx in (4, -30, -8, 9, -37, 15, -44, 21, -52, 27, -59, 34, -66,
               41, -73, 48, -80, 55, -87, 62, -94, 70, -102, 86, -118):
        for dy in (3, -8, 9, -14, 15, -19, 21, -25, 28, -31, 34, -38, 42, -46):
            candidates.append((dx, dy))
    # try the placements closest to the marker first, so a label stays beside
    # the point it names whenever that is possible
    candidates.sort(key=lambda offset: offset[0] ** 2 + offset[1] ** 2)
    obstacles = []
    for _algo, grass, _rate, low, high in points:
        x, y0 = ax.transData.transform((grass, low))
        _x, y1 = ax.transData.transform((grass, high))
        obstacles.append(Bbox.from_bounds(x - 9, min(y0, y1) - 9, 18, abs(y1 - y0) + 18))
    placed = []
    for algo, grass, rate, _low, _high in sorted(points, key=lambda item: (-item[2], item[1])):
        # Every candidate offset is scored by the area it shares with a mark or
        # with a label already placed; the smallest is kept, so a crowded panel
        # degrades to the least-bad placement instead of to a fixed offset that
        # may sit on a marker.
        best = None
        best_offset = None
        for offset in candidates:
            artist = ax.annotate(SHORT_LABELS[algo], (grass, rate),
                                 textcoords="offset points", xytext=offset,
                                 fontsize=size, annotation_clip=False,
                                 bbox=dict(boxstyle="round,pad=0.12", facecolor="white",
                                           edgecolor="none", alpha=0.85))
            box = artist.get_window_extent(renderer=renderer)
            penalty = sum(_overlap_area(box, other) for other in placed)
            penalty += sum(_overlap_area(box, obstacle) for obstacle in obstacles)
            outside = (box.x0 < panel.x0 - 2 or box.x1 > panel.x1 + 2 or
                       box.y0 < panel.y0 - 2 or box.y1 > panel.y1 + 2)
            if outside:
                penalty += 1e6
            if best is None or penalty < best[0]:
                if best is not None:
                    best[1].remove()
                best = (penalty, artist, box)
                best_offset = offset
                if penalty == 0.0:
                    break
            else:
                artist.remove()
        placed.append(best[2])
        # A hairline from the mark to its name keeps the mapping readable where
        # the crowded corner of the panel forces a label away from its point.
        # The line is drawn under the label's white box, so only the stretch
        # between the mark and the box is visible.
        marker_xy = ax.transData.transform((grass, rate))
        anchor_xy = marker_xy + np.asarray(best_offset, dtype=float)
        end_xy = _box_entry(marker_xy, anchor_xy, best[2])
        inverted = ax.transData.inverted()
        (x0, y0), (x1, y1) = inverted.transform(marker_xy), inverted.transform(end_xy)
        ax.plot([x0, x1], [y0, y1], color="0.45", linewidth=0.35, zorder=1.5,
                solid_capstyle="butt")


def _hex_to_rgb(value):
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) / 255 for i in (0, 2, 4))


def figure_scale(cases, out_dir):
    import matplotlib.pyplot as plt

    with plt.rc_context(PUBLICATION_FONTS):
        return _figure_scale(cases, out_dir, plt)


def _figure_scale(cases, out_dir, plt):
    fig, axes = plt.subplots(1, 2, figsize=(HALF, 2.55), sharex=True)
    focus = ["ours_dnq_dlc", "rule_expert_gate", "dlc_joint_transition_observer", "dlc_individual_transition"]
    for algo in focus:
        for ax, key, name in [
            (axes[0], "E_full", "strict pass rate"),
            (axes[1], "episode_grass", "grass fraction"),
        ]:
            values = []
            for scale in SCALES:
                rows = [r for r in cases if r["algorithm"] == algo and r["experiment_id"] == scale]
                values.append(rate_ci(rows, key)[0] if key == "E_full"
                              else mean([episode_grass(r) for r in rows]))
            ax.plot(range(len(SCALES)), values, marker=marker_for_algorithm(algo),
                    color=color_for_algorithm(algo), label=SHORT_LABELS[algo],
                    linewidth=1.2, markersize=4.2, markeredgecolor="black", markeredgewidth=0.45)
    axes[0].set_ylabel("strict-tier rate")
    axes[0].set_ylim(0, 1.0)
    axes[1].set_ylabel("grass fraction")
    for ax in axes:
        ax.set_xticks(range(len(SCALES)))
        ax.set_xticklabels([SCALE_LABELS[s] for s in SCALES])
        ax.set_xlabel("vehicles in the field")
    axes[0].legend(loc="upper left", handlelength=1.3, borderpad=0.2, labelspacing=0.25)
    panel_letter(axes[0], "a")
    panel_letter(axes[1], "b")
    fig.tight_layout()
    return _save(fig, out_dir / "figure_scale_corridor")


def figure_scale_membership(cases, windows, out_dir):
    """Fleet-size dependence and the membership of the vehicle being passed.

    Panels (a) and (b) are the fleet-size profile of the four methods that
    complete most cases; panels (c) and (d) follow the vehicle being passed
    inside the admitted set of the proposed controller. Both questions are read
    at the same four fleet sizes, so they share one float.
    """
    import matplotlib.pyplot as plt

    with plt.rc_context(PUBLICATION_FONTS):
        return _figure_scale_membership(cases, windows, out_dir, plt)


def _figure_scale_membership(cases, windows, out_dir, plt):
    fig, axes = plt.subplots(1, 4, figsize=(WIDE, 1.85))
    focus = ["ours_dnq_dlc", "rule_expert_gate", "dlc_joint_transition_observer",
             "dlc_joint_transition"]
    for algo in focus:
        for ax, key in ((axes[0], "E_full"), (axes[1], "episode_grass")):
            values = []
            for scale in SCALES:
                rows = [r for r in cases if r["algorithm"] == algo and r["experiment_id"] == scale]
                values.append(rate_ci(rows, key)[0] if key == "E_full"
                              else mean([episode_grass(r) for r in rows]))
            ax.plot(range(len(SCALES)), values, marker=marker_for_algorithm(algo),
                    color=color_for_algorithm(algo), label=SHORT_LABELS[algo],
                    linewidth=1.2, markersize=4.2, markeredgecolor="black", markeredgewidth=0.45)
    axes[0].set_ylabel("strict pass rate")
    axes[0].set_ylim(0, 1.0)
    axes[1].set_ylabel("grass fraction")
    for ax in axes[:2]:
        ax.set_xticks(range(len(SCALES)))
        ax.set_xticklabels([SCALE_LABELS[s] for s in SCALES])
        ax.set_xlabel("vehicles in the field")
    axes[0].legend(loc="upper left", handlelength=1.3, borderpad=0.2, labelspacing=0.25)
    panel_letter(axes[0], "a")
    panel_letter(axes[1], "b")

    ours = [r for r in windows if r["algorithm"] == "ours_dnq_dlc"]
    scales = [s for s in SCALES if any(r["experiment_id"] == s for r in ours)]
    x = np.arange(len(scales))
    colour = color_for_algorithm("ours_dnq_dlc")
    for ax, key, letter in ((axes[2], "partner_in_window_any", "c"),
                            (axes[3], "partner_at_complete", "d")):
        rates, lows, highs, counts = [], [], [], []
        for scale in scales:
            rows = [r for r in ours if r["experiment_id"] == scale]
            rate, k, total, low, high = rate_ci(rows, key)
            rates.append(rate)
            lows.append(rate - low)
            highs.append(high - rate)
            counts.append(f"{k}/{total}")
        ax.bar(x, rates, width=0.6, color=colour, edgecolor="black", linewidth=0.5,
               yerr=[lows, highs], error_kw=dict(ecolor="black", elinewidth=0.8, capsize=1.6))
        ax.set_ylim(0, 1.12)
        ax.set_xticks(x)
        ax.set_xticklabels([f"{SCALE_LABELS[s]}\n{label}"
                            for s, label in zip(scales, counts)], fontsize=6.2)
        ax.set_xlabel("vehicles in the field")
        panel_letter(ax, letter)
    axes[2].set_ylabel("share of passes", fontsize=8)
    fig.tight_layout()
    return _save(fig, out_dir / "figure_scale_membership")


def figure_mechanism(signals, histogram, out_dir):
    import matplotlib.pyplot as plt

    with plt.rc_context(PUBLICATION_FONTS):
        return _figure_mechanism(signals, histogram, out_dir, plt)


def _figure_mechanism(signals, histogram, out_dir, plt):
    fig, axes = plt.subplots(1, 4, figsize=(WIDE, 1.85))
    ours = [r for r in signals if r["algorithm"] == "ours_dnq_dlc"]
    ours.sort(key=lambda r: SCALES.index(r["experiment_id"]))
    colour = color_for_algorithm("ours_dnq_dlc")
    x = np.arange(len(ours))

    ax = axes[0]
    ax.plot(x, [num(r, "exposed_mean_mean") for r in ours], marker="o", color=colour,
            linewidth=1.1, markersize=3.8, label="exposed")
    ax.plot(x, [num(r, "admitted_mean_mean") for r in ours], marker="s", color=colour,
            linewidth=1.1, markersize=3.8, linestyle="--", label="admitted")
    ax.set_ylim(0, 9.6)
    ax.set_ylabel("vehicles")
    panel_letter(ax, "a")
    ax.legend(loc="upper left", handlelength=1.4, borderpad=0.2, labelspacing=0.25)

    ax = axes[1]
    width = 0.38
    for offset, scale, alpha in [(-width / 2, "M4_sparse", 0.55), (width / 2, "M10_scale", 0.95)]:
        rows = {int(r["admitted_size"]): num(r, "fraction") for r in histogram if r["experiment_id"] == scale}
        sizes = sorted(rows)
        ax.bar([s + offset for s in sizes], [rows[s] for s in sizes], width=width,
               color=colour, alpha=alpha, edgecolor="black", linewidth=0.5,
               label=f"{SCALE_LABELS[scale]} vehicles")
    ax.set_xlabel("admitted neighbours")
    ax.set_ylabel("fraction of steps")
    panel_letter(ax, "b")
    ax.legend(handlelength=1.2, borderpad=0.2, labelspacing=0.25)

    ax = axes[2]
    horizons = [1, 2, 3, 4]
    values = [mean([num(r, f"wm_pos_err_ego_h{h}_mean") for r in ours]) for h in horizons]
    lows = [v - mean([num(r, f"wm_pos_err_ego_h{h}_ci_low") for r in ours]) for h, v in zip(horizons, values)]
    highs = [mean([num(r, f"wm_pos_err_ego_h{h}_ci_high") for r in ours]) - v for h, v in zip(horizons, values)]
    vehicle = 4.5
    ax.errorbar(horizons, values, yerr=[lows, highs], marker="o", color=colour,
                linewidth=1.1, markersize=3.8, capsize=1.6, elinewidth=0.9)
    ax.axhline(vehicle / 4.0, color="black", linestyle=":", linewidth=1.0)
    ax.annotate("quarter car length", (4, vehicle / 4.0), textcoords="offset points",
                xytext=(-3, 3), ha="right")
    ax.set_xlabel("imagined horizon (steps)")
    ax.set_ylabel("position error (m)")
    panel_letter(ax, "c")

    ax = axes[3]
    override = [num(r, "override_rate_mean") for r in ours]
    margins = [num(r, "anchor_margin_mean_mean") for r in ours]
    ax.bar(x - 0.2, override, width=0.4, color=colour, edgecolor="black", linewidth=0.5)
    ax.set_ylim(0, 1.05)
    # The twin axis makes this the narrowest gap in the figure. A four-word
    # left label is drawn over the last interval of panel (c) when the panels
    # are packed at their default spacing, so the label is kept to two words
    # and the gap is widened below.
    ax.set_ylabel("override rate", color=colour)
    panel_letter(ax, "d")
    twin = ax.twinx()
    twin.plot(x + 0.2, margins, marker="D", color="black", linewidth=1.0, markersize=3.2)
    twin.set_ylabel("score margin", color="black")
    twin.spines["top"].set_visible(False)

    for ax in (axes[0], axes[3]):
        ax.set_xticks(x)
        ax.set_xticklabels([SCALE_LABELS[r["experiment_id"]] for r in ours])
        ax.set_xlabel("vehicles in the field")
    axes[1].set_xticks(range(4))
    axes[1].set_xticklabels(["0", "1", "2", "3"])
    axes[2].set_xticks(horizons)
    axes[2].set_xticklabels([str(h) for h in horizons])
    fig.tight_layout(w_pad=2.0)
    return _save(fig, out_dir / "figure_mechanism_panel")


def figure_manoeuvre(events, out_dir):
    """How a pass is executed, and what it costs in containment.

    One row per completed pass, averaged per method with the 95 % interval of
    the mean. The durations and the speed advantage say how the pass is driven;
    the minimum gap and the grass steps say what that costs inside the
    manoeuvre, which is where the contact and off-track clauses of the strict
    tier fail.
    """
    import matplotlib.pyplot as plt

    with plt.rc_context(PUBLICATION_FONTS):
        return _figure_manoeuvre(events, out_dir, plt)


def _figure_manoeuvre(events, out_dir, plt):
    fig, axes = plt.subplots(1, 4, figsize=(WIDE, 1.85))
    x = np.arange(len(PASS_ORDER))
    labels = [SHORT_LABELS[a] for a in PASS_ORDER]
    colours = [color_for_algorithm(a) for a in PASS_ORDER]
    rows_for = lambda algo: [r for r in events if r["algorithm"] == algo]

    ax = axes[0]
    width = 0.38
    for offset, key, hatch in ((-width / 2, "approach_steps", None), (width / 2, "alongside_steps", "//")):
        values, lows, highs = [], [], []
        for algo in PASS_ORDER:
            centre, low, high = mean_ci([num(r, key) for r in rows_for(algo)])
            values.append(centre)
            lows.append(centre - low)
            highs.append(high - centre)
        ax.bar(x + offset, values, width=width, color=colours, hatch=hatch,
               edgecolor="black", linewidth=0.5,
               yerr=[lows, highs], error_kw=dict(ecolor="black", elinewidth=0.8, capsize=1.6))
    ax.set_ylim(0, 215)
    ax.set_ylabel("steps")
    panel_letter(ax, "a")

    ax = axes[1]
    values, lows, highs = [], [], []
    for algo in PASS_ORDER:
        centre, low, high = mean_ci([num(r, "speed_advantage_alongside") for r in rows_for(algo)])
        values.append(centre)
        lows.append(centre - low)
        highs.append(high - centre)
    ax.bar(x, values, width=0.6, color=colours, edgecolor="black", linewidth=0.5,
           yerr=[lows, highs], error_kw=dict(ecolor="black", elinewidth=0.8, capsize=1.6))
    ax.set_ylim(0, 10.5)
    ax.set_ylabel("m/s")
    panel_letter(ax, "b")

    ax = axes[2]
    values, lows, highs = [], [], []
    for algo in PASS_ORDER:
        centre, low, high = mean_ci([num(r, "min_gap_rival_maneuver") for r in rows_for(algo)])
        values.append(centre)
        lows.append(centre - low)
        highs.append(high - centre)
    ax.bar(x, values, width=0.6, color=colours, edgecolor="black", linewidth=0.5,
           yerr=[lows, highs], error_kw=dict(ecolor="black", elinewidth=0.8, capsize=1.6))
    ax.set_ylim(0, 14.5)
    ax.set_ylabel("m")
    panel_letter(ax, "c")

    ax = axes[3]
    values, lows, highs = [], [], []
    for algo in PASS_ORDER:
        centre, low, high = mean_ci([num(r, "grass_steps_maneuver") for r in rows_for(algo)])
        values.append(centre)
        lows.append(centre - low)
        highs.append(high - centre)
    ax.bar(x, values, width=0.6, color=colours, edgecolor="black", linewidth=0.5,
           yerr=[lows, highs], error_kw=dict(ecolor="black", elinewidth=0.8, capsize=1.6))
    ax.set_ylim(0, 82)
    ax.set_ylabel("steps")
    panel_letter(ax, "d")

    for ax in axes:
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=40, ha="right")
    fig.tight_layout()
    return _save(fig, out_dir / "figure_manoeuvre_profile")


def figure_partner_tracking(event_rows, out_dir):
    """Whether the admitted set keeps the vehicle the ego is passing.

    The window of every pass of the proposed controller, split by fleet size.
    Panel (a) asks whether the opponent being passed entered the admitted set at
    any point of the manoeuvre; panel (b) asks whether it was still there when
    the pass completed. The gap between the two is the selector working: in a
    dense field the partner is admitted but does not stay admitted, because once
    the ego has crossed, the partner stops constraining the pass.
    """
    import matplotlib.pyplot as plt

    with plt.rc_context(PUBLICATION_FONTS):
        return _figure_partner_tracking(event_rows, out_dir, plt)


def _figure_partner_tracking(event_rows, out_dir, plt):
    ours = [r for r in event_rows if r["algorithm"] == "ours_dnq_dlc"]
    scales = [s for s in SCALES if any(r["experiment_id"] == s for r in ours)]
    x = np.arange(len(scales))
    colour = color_for_algorithm("ours_dnq_dlc")
    fig, axes = plt.subplots(1, 2, figsize=(COLUMN, 1.9))

    for ax, key, letter in (
        (axes[0], "partner_in_window_any", "a"),
        (axes[1], "partner_at_complete", "b"),
    ):
        rates, lows, highs, counts = [], [], [], []
        for scale in scales:
            rows = [r for r in ours if r["experiment_id"] == scale]
            rate, k, total, low, high = rate_ci(rows, key)
            rates.append(rate)
            lows.append(rate - low)
            highs.append(high - rate)
            counts.append(f"{k}/{total}")
        ax.bar(x, rates, width=0.6, color=colour, edgecolor="black", linewidth=0.5,
               yerr=[lows, highs], error_kw=dict(ecolor="black", elinewidth=0.8, capsize=1.6))
        ax.set_ylim(0, 1.12)
        ax.set_xticks(x)
        ax.set_xticklabels([f"{SCALE_LABELS[s]}\n{label}"
                            for s, label in zip(scales, counts)], fontsize=6.2)
        ax.set_xlabel("vehicles")
        panel_letter(ax, letter)
    axes[0].set_ylabel("share of passes", fontsize=8)
    fig.tight_layout()
    return _save(fig, out_dir / "figure_partner_tracking")


def _save(fig, stem):
    written = []
    # The submission figures are supplied as vector PDF plus a 600 dpi LZW
    # raster, matching the other figures in the manuscript directory.
    for suffix, kwargs in (("pdf", {}),
                           ("png", {"dpi": 400}),
                           ("tiff", {"dpi": 600,
                                     "pil_kwargs": {"compression": "tiff_lzw"}})):
        path = stem.with_suffix("." + suffix)
        fig.savefig(path, bbox_inches="tight", **kwargs)
        written.append(str(path))
    return written


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validity", required=True, help="Directory holding case_level.csv")
    parser.add_argument("--signals", required=True, help="Directory holding controller_signals_by_scale.csv")
    parser.add_argument("--containment", required=True,
                        help="episode_level.csv of whole-episode containment, one row per case and arm")
    parser.add_argument("--events", required=True,
                        help="Directory holding vehicle_event_level.csv, one row per completed pass")
    parser.add_argument("--admission", required=True,
                        help="Directory holding neighborhood_event_level.csv, one row per pass window")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--rl-validity", default=str(ROOT / "outputs" / "tits_dynamic_graph_expanded"
                                                    / "validity_rl_strict_20260927" / "case_level.csv"),
                        help="strict RL audit; its arms are pooled into the three families")
    parser.add_argument("--rl-containment", default=str(ROOT / "outputs" / "tits_dynamic_graph_expanded"
                                                        / "validity_rl_strict_20260927" / "episode_level.csv"),
                        help="whole-episode containment of the strict RL arms")
    parser.add_argument("--ours-validity", default=str(ROOT / "outputs" / "tits_dynamic_graph_expanded"
                                                       / "validity_ours_seedspread_20260928" / "case_level.csv"),
                        help="world-model seed-spread audit of the proposed controller")
    parser.add_argument("--ours-containment", default="",
                        help="whole-episode containment of the proposed controller's seeds; "
                             "when empty the seed-spread arms are drawn without episode containment")
    parser.add_argument("--dlc-draws", default="",
                        help="directory of draw_*/ trees for the three world-model variants; "
                             "each needs case_level.csv and containment_episode_level.csv")
    args = parser.parse_args()

    configure_publication_matplotlib()
    load_episode_containment(args.containment)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    cases = [r for r in read_csv(Path(args.validity) / "case_level.csv") if r["status"] == "ok"]
    signals = [dict(r, algorithm=canonical_algorithm(r["algorithm"]))
               for r in read_csv(Path(args.signals) / "controller_signals_by_scale.csv")]
    histogram = [dict(r, algorithm=canonical_algorithm(r["algorithm"]))
                 for r in read_csv(Path(args.signals) / "controller_admitted_size_hist.csv")]
    events = [dict(r, algorithm=canonical_algorithm(r["algorithm"]))
              for r in read_csv(Path(args.events) / "vehicle_event_level.csv")]
    windows = [dict(r, algorithm=canonical_algorithm(r["algorithm"]))
               for r in read_csv(Path(args.admission) / "neighborhood_event_level.csv")]
    load_rl_strict(args.rl_validity)
    load_rl_containment(args.rl_containment)
    if args.dlc_draws:
        load_dlc_draws(args.dlc_draws)
        load_dlc_containment(args.dlc_draws)
    if args.ours_validity:
        load_ours_seedspread(args.ours_validity)
    if args.ours_containment:
        load_ours_containment(args.ours_containment)
    RESAMPLED_ROWS[:] = list(OURS_ROWS) + list(RL_ROWS) + list(DLC_ROWS)
    signals = collapse_draws(signals)
    histogram = collapse_draws(histogram)
    # The submitted table replaces the earlier single-seed, 50k-step agents with
    # the five-seed strict retrain, and repeats the proposed controller once per
    # world-model seed, so those single-run rows leave the pooled comparison.
    pooled = set(RL_FAMILY.values()) | set(DLC_VARIANTS) | ({OURS} if OURS_ROWS else set())
    cases = [r for r in cases if r["algorithm"] not in pooled] + RESAMPLED_ROWS
    for builder, payload in [
        (figure_endpoints, (cases, out_dir)),
        (figure_scale_membership, (cases, windows, out_dir)),
        (figure_manoeuvre, (events, out_dir)),
        (figure_mechanism, (signals, histogram, out_dir)),
    ]:
        for path in builder(*payload):
            print("wrote", path)


if __name__ == "__main__":
    main()
