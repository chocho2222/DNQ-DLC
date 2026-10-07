#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Draw the DNQ-DLC system architecture figure for the T-ITS manuscript."""

from __future__ import annotations

from pathlib import Path
import math
import textwrap

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch, Polygon, Rectangle
from matplotlib.lines import Line2D
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "outputs" / "tits_dynamic_graph_expanded" / "architecture" / "figures"
SUBMISSION_FIG_DIR = (
    ROOT
    / "paper_rewriting_output_tits_dynamic_graph_draft_20260625"
    / "tits_submission_final"
    / "figures"
)


COLORS = {
    "blue": "#235A9F",
    "blue_light": "#EAF2FA",
    "blue_mid": "#9DB7D1",
    "green": "#3F7A5C",
    "green_light": "#EEF6F0",
    "green_mid": "#8CBF9B",
    "orange": "#9A5A24",
    "orange_light": "#FBF0E6",
    "orange_mid": "#D7A574",
    "red": "#CF8A86",
    "purple": "#AFA6CF",
    "gray": "#6B7280",
    "gray_light": "#F7F8FA",
    "line": "#25313D",
    "soft_line": "#9CA3AF",
    "white": "#FFFFFF",
}


def setup_style() -> None:
    for item in [
        "/usr/share/fonts/truetype/msttcorefonts/Times_New_Roman.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSerif-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
    ]:
        path = Path(item)
        if path.exists():
            mpl.font_manager.fontManager.addfont(str(path))
    mpl.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Times New Roman", "Liberation Serif", "DejaVu Serif", "serif"],
            "font.size": 6.2,
            "pdf.fonttype": 42,
            "svg.fonttype": "none",
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "text.color": "black",
            "axes.unicode_minus": False,
        }
    )


def add_box(
    ax,
    x,
    y,
    w,
    h,
    fc=COLORS["white"],
    ec=COLORS["soft_line"],
    lw=0.65,
    radius=0.012,
    alpha=1.0,
    z=2,
):
    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle=f"round,pad=0.004,rounding_size={radius}",
        linewidth=lw,
        edgecolor=ec,
        facecolor=fc,
        alpha=alpha,
        zorder=z,
    )
    ax.add_patch(patch)
    return patch


def label(ax, x, y, text, size=6.2, weight="normal", color="black", ha="center", va="center", **kwargs):
    return ax.text(x, y, text, fontsize=size, fontweight=weight, color=color, ha=ha, va=va, **kwargs)


def wrapped_label(ax, x, y, text, width=22, size=5.8, weight="normal", color="black", ha="center", va="center", **kwargs):
    return label(
        ax,
        x,
        y,
        "\n".join(textwrap.wrap(text, width=width)),
        size=size,
        weight=weight,
        color=color,
        ha=ha,
        va=va,
        linespacing=1.05,
        **kwargs,
    )


def arrow(ax, x1, y1, x2, y2, color=COLORS["line"], lw=0.8, style="-|>", ms=7, ls="-", alpha=1.0, z=8):
    arr = FancyArrowPatch(
        (x1, y1),
        (x2, y2),
        arrowstyle=style,
        mutation_scale=ms,
        linewidth=lw,
        color=color,
        linestyle=ls,
        alpha=alpha,
        zorder=z,
        shrinkA=1.0,
        shrinkB=1.0,
    )
    ax.add_patch(arr)
    return arr


def badge(ax, x, y, text, color):
    add_box(ax, x - 0.012, y - 0.012, 0.024, 0.024, fc=color, ec="white", lw=0.5, radius=0.006, z=10)
    label(ax, x, y - 0.0002, text, size=5.1, weight="bold", color="white", zorder=11)


def stage(ax, x, y, w, h, title, color, light):
    add_box(ax, x, y, w, h, fc=light, ec="#D0D7DE", lw=0.6, radius=0.014, alpha=0.85, z=0)
    add_box(ax, x + 0.004, y + h - 0.060, w - 0.008, 0.052, fc=light, ec="none", lw=0, radius=0.012, z=1)
    label(ax, x + 0.018, y + h - 0.033, title, size=7.8, weight="bold", color=color, ha="left")


def draw_track(ax, x, y, w, h):
    t = np.linspace(0, 1, 80)
    cx = x + w * (0.24 + 0.35 * t)
    cy = y + h * (0.18 + 0.68 * t)
    curve = 0.075 * np.sin(2.2 * np.pi * t)
    left = np.column_stack([cx - w * 0.14 + curve, cy])
    right = np.column_stack([cx + w * 0.14 + curve, cy])
    center = np.column_stack([cx + curve, cy])
    ax.plot(left[:, 0], left[:, 1], color="#9CA3AF", lw=0.55)
    ax.plot(right[:, 0], right[:, 1], color="#9CA3AF", lw=0.55)
    ax.plot(center[:, 0], center[:, 1], color=COLORS["blue_mid"], lw=0.55, ls="--")
    for ti, c in [(0.22, COLORS["gray"]), (0.42, COLORS["gray"]), (0.62, COLORS["blue"])]:
        px = x + w * (0.24 + 0.35 * ti) + 0.075 * math.sin(2.2 * math.pi * ti)
        py = y + h * (0.18 + 0.68 * ti)
        draw_car(ax, px, py, 0.020, 0.040, c, angle=72)
    arrow(ax, x + w * 0.68, y + h * 0.55, x + w * 0.84, y + h * 0.55, color=COLORS["line"], lw=0.8)
    # Local frame.
    ox, oy = x + w * 0.88, y + h * 0.36
    ax.plot([ox, ox], [oy, oy + h * 0.42], color=COLORS["line"], lw=0.65)
    ax.plot([ox - w * 0.18, ox + w * 0.10], [oy + h * 0.18, oy + h * 0.18], color=COLORS["line"], lw=0.65)
    arrow(ax, ox, oy + h * 0.18, ox + w * 0.10, oy + h * 0.18, lw=0.6, ms=5)
    arrow(ax, ox, oy + h * 0.18, ox, oy + h * 0.42, lw=0.6, ms=5)
    label(ax, ox + w * 0.12, oy + h * 0.18, "$s$", size=5.8)
    label(ax, ox, oy + h * 0.45, "$n$", size=5.8)
    draw_car(ax, ox - w * 0.03, oy + h * 0.12, 0.018, 0.036, COLORS["blue"], angle=74)
    ax.plot([ox - w * 0.07, ox + w * 0.07], [oy + h * 0.12, oy + h * 0.25], color=COLORS["green_mid"], lw=0.55, ls="--")
    label(ax, x + w * 0.34, y + 0.018, "track scene", size=5.0, color=COLORS["gray"])
    label(ax, x + w * 0.84, y + 0.018, "local frame", size=5.0, color=COLORS["gray"])


def draw_car(ax, x, y, w, h, color, angle=0):
    # A compact vector car: rotated rectangle plus two dark wheels.
    theta = math.radians(angle)
    corners = np.array([[-w / 2, -h / 2], [w / 2, -h / 2], [w / 2, h / 2], [-w / 2, h / 2]])
    rot = np.array([[math.cos(theta), -math.sin(theta)], [math.sin(theta), math.cos(theta)]])
    pts = corners @ rot.T + np.array([x, y])
    ax.add_patch(Polygon(pts, closed=True, facecolor=color, edgecolor="#25313D", linewidth=0.45, zorder=5))
    ax.add_patch(Circle((x, y), min(w, h) * 0.16, facecolor="white", edgecolor="none", alpha=0.65, zorder=6))


def draw_dynamic_graph(ax, x, y, w, h):
    add_box(ax, x, y, w, h, fc="white", ec="#B7C2CC", lw=0.55, radius=0.010)
    cx, cy = x + w * 0.60, y + h * 0.52
    nodes = [
        (cx, cy, COLORS["blue"], 0.017, "ego"),
        (x + w * 0.30, y + h * 0.72, COLORS["green_mid"], 0.010, "rel"),
        (x + w * 0.78, y + h * 0.75, COLORS["green_mid"], 0.010, "rel"),
        (x + w * 0.28, y + h * 0.32, COLORS["green_mid"], 0.010, "rel"),
        (x + w * 0.83, y + h * 0.30, COLORS["gray"], 0.010, "irr"),
        (x + w * 0.46, y + h * 0.16, COLORS["gray"], 0.010, "irr"),
    ]
    for nx, ny, c, r, kind in nodes[1:]:
        ls = "--" if kind == "irr" else "-"
        alpha = 0.35 if kind == "irr" else 0.95
        ax.plot([cx, nx], [cy, ny], color=COLORS["line"], lw=0.55, ls=ls, alpha=alpha, zorder=3)
    for nx, ny, c, r, _ in nodes:
        ax.add_patch(Circle((nx, ny), r, facecolor=c, edgecolor=COLORS["line"], linewidth=0.45, zorder=4))
    label(ax, x + w * 0.18, y + h * 0.84, "$\\rho_j(t)$", size=6.0, weight="bold", color=COLORS["blue"])
    wrapped_label(ax, x + w * 0.24, y + h * 0.53, "risk-gated all relevant vehicles", width=13, size=5.2)
    label(ax, x + w * 0.54, y + h * 0.08, "$\\mathcal{G}_t=(\\mathcal{V}_t,\\mathcal{E}_t,M_t)$", size=6.0, weight="bold")


def draw_slots(ax, x, y, w, h):
    add_box(ax, x, y, w, h, fc="white", ec="#B7C2CC", lw=0.55, radius=0.010)
    # small graph
    gx, gy = x + w * 0.15, y + h * 0.60
    pts = [(gx, gy), (gx - w * 0.06, gy + h * 0.18), (gx + w * 0.08, gy + h * 0.20), (gx + w * 0.10, gy - h * 0.18)]
    for px, py in pts[1:]:
        ax.plot([gx, px], [gy, py], color=COLORS["line"], lw=0.45)
    for idx, (px, py) in enumerate(pts):
        ax.add_patch(Circle((px, py), 0.008 if idx else 0.014, facecolor=COLORS["blue"] if idx == 0 else COLORS["green_mid"], edgecolor=COLORS["line"], lw=0.4))
    arrow(ax, x + w * 0.29, y + h * 0.60, x + w * 0.38, y + h * 0.60, lw=0.7)
    for i in range(5):
        yy = y + h * (0.78 - i * 0.14)
        fc = COLORS["green_light"] if i < 3 else "#F1F3F5"
        ax.add_patch(Rectangle((x + w * 0.42, yy), w * 0.12, h * 0.065, facecolor=fc, edgecolor=COLORS["line"], lw=0.35))
        label(ax, x + w * 0.58, yy + h * 0.033, "$m_k$" if i == 3 else "", size=4.7, color=COLORS["gray"])
    arrow(ax, x + w * 0.57, y + h * 0.60, x + w * 0.66, y + h * 0.60, lw=0.7)
    add_box(ax, x + w * 0.68, y + h * 0.35, w * 0.16, h * 0.42, fc="#F8FBF8", ec="#B7C2CC", lw=0.45, radius=0.006)
    wrapped_label(ax, x + w * 0.76, y + h * 0.58, "masked aggregation sum/mean", width=12, size=4.9)
    arrow(ax, x + w * 0.86, y + h * 0.60, x + w * 0.94, y + h * 0.60, lw=0.7)
    ax.add_patch(Rectangle((x + w * 0.94, y + h * 0.40), w * 0.035, h * 0.40, facecolor=COLORS["green_mid"], edgecolor=COLORS["line"], lw=0.35, alpha=0.8))
    label(ax, x + w * 0.955, y + h * 0.34, "$z_t$", size=6.1, weight="bold")


def draw_world_model(ax, x, y, w, h):
    add_box(ax, x, y, w, h, fc="white", ec="#B7C2CC", lw=0.55, radius=0.010)
    # posterior row
    label(ax, x + w * 0.50, y + h * 0.88, "DLC latent world model", size=6.6, weight="bold", color=COLORS["green"])
    row_y = y + h * 0.67
    label(ax, x + w * 0.11, row_y, "$h_t,z_t$", size=5.5)
    draw_mlp(ax, x + w * 0.23, row_y - h * 0.10, w * 0.20, h * 0.20, COLORS["purple"])
    arrow(ax, x + w * 0.16, row_y, x + w * 0.22, row_y, lw=0.6)
    arrow(ax, x + w * 0.44, row_y, x + w * 0.54, row_y, lw=0.6)
    ax.add_patch(Rectangle((x + w * 0.55, row_y - h * 0.08), w * 0.045, h * 0.16, facecolor=COLORS["purple"], edgecolor=COLORS["line"], lw=0.35, alpha=0.75))
    label(ax, x + w * 0.575, row_y + h * 0.13, "$s_t$", size=5.8)
    label(ax, x + w * 0.38, row_y + h * 0.16, "$q_\\theta(s_t|h_t,z_t)$", size=5.2)
    # prior row
    row_y2 = y + h * 0.39
    label(ax, x + w * 0.11, row_y2, "$h_t,s_t,a_t$", size=5.5)
    draw_mlp(ax, x + w * 0.23, row_y2 - h * 0.10, w * 0.20, h * 0.20, COLORS["blue_mid"])
    arrow(ax, x + w * 0.17, row_y2, x + w * 0.22, row_y2, lw=0.6)
    arrow(ax, x + w * 0.44, row_y2, x + w * 0.54, row_y2, lw=0.6)
    ax.add_patch(Rectangle((x + w * 0.55, row_y2 - h * 0.08), w * 0.045, h * 0.16, facecolor=COLORS["blue"], edgecolor=COLORS["line"], lw=0.35, alpha=0.80))
    label(ax, x + w * 0.58, row_y2 - h * 0.14, "$s_{t+1}$", size=5.8)
    label(ax, x + w * 0.39, row_y2 + h * 0.16, "$p_\\theta(s_{t+1}|h_t,s_t,a_t)$", size=5.2)
    # heads
    head_y = y + h * 0.12
    labels = [("reward", "#D7A574"), ("risk", "#CF8A86"), ("off-track", "#9DB7D1"), ("progress", "#8CBF9B"), ("uncert.", "#AFA6CF")]
    for i, (txt, c) in enumerate(labels):
        xx = x + w * (0.12 + i * 0.17)
        add_box(ax, xx - w * 0.055, head_y - h * 0.045, w * 0.11, h * 0.09, fc="#FAFAFA", ec="#D0D7DE", lw=0.35, radius=0.006)
        ax.add_patch(Circle((xx, head_y + h * 0.010), 0.008, facecolor=c, edgecolor=COLORS["line"], lw=0.3))
        label(ax, xx, head_y - h * 0.030, txt, size=4.7)


def draw_mlp(ax, x, y, w, h, color):
    layers = [3, 4, 3]
    xs = np.linspace(x, x + w, len(layers))
    node_positions = []
    for lx, count in zip(xs, layers):
        ys = np.linspace(y + h * 0.18, y + h * 0.82, count)
        node_positions.append([(lx, yy) for yy in ys])
    for layer_a, layer_b in zip(node_positions[:-1], node_positions[1:]):
        for xa, ya in layer_a:
            for xb, yb in layer_b:
                ax.plot([xa, xb], [ya, yb], color="#CBD5E1", lw=0.25, zorder=2)
    for layer in node_positions:
        for px, py in layer:
            ax.add_patch(Circle((px, py), min(w, h) * 0.035, facecolor=color, edgecolor=COLORS["line"], lw=0.25, alpha=0.78, zorder=3))


def draw_proposals(ax, x, y, w, h):
    add_box(ax, x, y, w, h, fc="white", ec="#D2BCA9", lw=0.55, radius=0.010)
    wrapped_label(ax, x + w * 0.25, y + h * 0.84, "overtaking proposal library", width=16, size=5.5, weight="bold")
    items = [("chase", COLORS["blue_mid"]), ("lateral pass", COLORS["blue"]), ("recovery", COLORS["green_mid"]), ("brake / safety", COLORS["red"])]
    for i, (txt, c) in enumerate(items):
        yy = y + h * (0.66 - 0.13 * i)
        ax.add_patch(Circle((x + w * 0.10, yy), 0.010, facecolor=c, edgecolor=COLORS["line"], lw=0.35))
        label(ax, x + w * 0.18, yy, txt, size=4.9, ha="left")
    # action manifold
    origin = (x + w * 0.56, y + h * 0.40)
    for i, c in enumerate([COLORS["blue"], COLORS["green_mid"], COLORS["orange_mid"], COLORS["red"]]):
        xs = np.linspace(0, w * 0.34, 50)
        amp = (i - 1.5) * h * 0.055
        ys = amp * (xs / (w * 0.34)) ** 1.5
        ax.plot(origin[0] + xs, origin[1] + ys, color=c, lw=1.25)
        arrow(ax, origin[0] + xs[-2], origin[1] + ys[-2], origin[0] + xs[-1], origin[1] + ys[-1], color=c, lw=1.1, ms=6)
    wrapped_label(ax, x + w * 0.73, y + h * 0.78, "curvature-aware context", width=14, size=4.9)
    label(ax, x + w * 0.59, y + h * 0.15, "$q_\\psi(A_t|z_t,\\mathcal{G}_t,\\mathcal{F}_t)$", size=5.5, weight="bold", color=COLORS["orange"])


def draw_planning(ax, x, y, w, h):
    add_box(ax, x, y, w, h, fc="white", ec="#D2BCA9", lw=0.55, radius=0.010)
    # rollout stack
    add_box(ax, x + w * 0.04, y + h * 0.50, w * 0.39, h * 0.37, fc="#FBFCFD", ec="#D0D7DE", lw=0.35, radius=0.007)
    label(ax, x + w * 0.235, y + h * 0.825, "latent rollout", size=5.4, weight="bold")
    for i in range(5):
        xx = x + w * (0.09 + i * 0.055)
        ax.add_patch(Polygon([(xx, y + h * 0.54), (xx + w * 0.035, y + h * 0.57), (xx + w * 0.035, y + h * 0.77), (xx, y + h * 0.74)], facecolor="#F4F7FB", edgecolor="#B7C2CC", lw=0.35))
    ax.plot([x + w * 0.08, x + w * 0.37], [y + h * 0.61, y + h * 0.69], color=COLORS["blue"], lw=1.0)
    label(ax, x + w * 0.24, y + h * 0.535, "$H$ steps", size=4.9)
    # radar like objective
    add_box(ax, x + w * 0.51, y + h * 0.50, w * 0.43, h * 0.37, fc="#FBFCFD", ec="#D0D7DE", lw=0.35, radius=0.007)
    label(ax, x + w * 0.725, y + h * 0.825, "objective vector", size=5.4, weight="bold")
    radar_center = (x + w * 0.72, y + h * 0.64)
    draw_radar(ax, radar_center[0], radar_center[1], min(w, h) * 0.17)
    label(ax, x + w * 0.72, y + h * 0.520, "$J(A_t)$", size=5.9, weight="bold", color=COLORS["orange"])
    # pareto and score
    add_box(ax, x + w * 0.04, y + h * 0.07, w * 0.38, h * 0.30, fc="#FBFCFD", ec="#D0D7DE", lw=0.35, radius=0.007)
    label(ax, x + w * 0.23, y + h * 0.33, "Pareto front", size=5.3, weight="bold")
    rng_x = np.linspace(0, 1, 18)
    for i, rx in enumerate(rng_x):
        ry = 0.74 * np.exp(-2.2 * rx) + 0.10
        c = COLORS["blue"] if i in [6, 8, 10] else "#BFC5CC"
        ax.add_patch(Circle((x + w * (0.10 + 0.25 * rx), y + h * (0.11 + 0.19 * ry)), 0.0045, facecolor=c, edgecolor="none"))
    arrow(ax, x + w * 0.09, y + h * 0.11, x + w * 0.35, y + h * 0.11, lw=0.55, ms=5)
    arrow(ax, x + w * 0.09, y + h * 0.11, x + w * 0.09, y + h * 0.31, lw=0.55, ms=5)
    label(ax, x + w * 0.35, y + h * 0.08, "time", size=4.6)
    label(ax, x + w * 0.06, y + h * 0.30, "risk", size=4.6, rotation=90)
    add_box(ax, x + w * 0.50, y + h * 0.07, w * 0.44, h * 0.30, fc="#FBFCFD", ec="#D0D7DE", lw=0.35, radius=0.007)
    label(ax, x + w * 0.72, y + h * 0.33, "candidate ranking", size=5.3, weight="bold")
    vals = [0.87, 0.72, 0.58, 0.33]
    cols = [COLORS["red"], COLORS["orange_mid"], COLORS["green_mid"], COLORS["blue_mid"]]
    for i, (v, c) in enumerate(zip(vals, cols)):
        yy = y + h * (0.27 - i * 0.05)
        label(ax, x + w * 0.55, yy, f"{v:.2f}", size=4.8, color=c, ha="left")
        ax.add_patch(Rectangle((x + w * 0.64, yy - h * 0.013), w * 0.18 * v, h * 0.023, facecolor=c, edgecolor="none", alpha=0.78))
        ax.add_patch(Rectangle((x + w * 0.64, yy - h * 0.013), w * 0.18, h * 0.023, facecolor="none", edgecolor="#D0D7DE", lw=0.25))


def draw_radar(ax, cx, cy, r):
    angles = np.linspace(0, 2 * np.pi, 6, endpoint=False) + np.pi / 6
    for rr in [0.35, 0.65, 0.95]:
        pts = [(cx + r * rr * math.cos(a), cy + r * rr * math.sin(a)) for a in angles]
        ax.add_patch(Polygon(pts, closed=True, facecolor="none", edgecolor="#D0D7DE", lw=0.35))
    labels = ["prog.", "track", "gap", "unc.", "stab.", "time"]
    for a, txt in zip(angles, labels):
        ax.plot([cx, cx + r * math.cos(a)], [cy, cy + r * math.sin(a)], color="#D0D7DE", lw=0.3)
        label(ax, cx + r * 1.10 * math.cos(a), cy + r * 1.10 * math.sin(a), txt, size=2.9)
    vals = np.array([0.88, 0.82, 0.76, 0.64, 0.78, 0.85])
    pts = [(cx + r * vals[i] * math.cos(a), cy + r * vals[i] * math.sin(a)) for i, a in enumerate(angles)]
    ax.add_patch(Polygon(pts, closed=True, facecolor=COLORS["green_mid"], edgecolor=COLORS["green"], lw=0.8, alpha=0.35))


def save_all(fig, stem: Path) -> dict[str, str]:
    stem.parent.mkdir(parents=True, exist_ok=True)
    outputs = {}
    for ext in ["svg", "pdf", "png", "tiff"]:
        path = stem.with_suffix(f".{ext}")
        fig.savefig(path, dpi=600, bbox_inches="tight", facecolor="white")
        outputs[ext] = str(path)
    return outputs


def main() -> None:
    setup_style()
    fig, ax = plt.subplots(figsize=(7.6, 4.95))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    stage(ax, 0.015, 0.075, 0.310, 0.895, "A  Map-relative representation", COLORS["blue"], COLORS["blue_light"])
    stage(ax, 0.345, 0.075, 0.310, 0.895, "B  DLC latent world model", COLORS["green"], COLORS["green_light"])
    stage(ax, 0.675, 0.075, 0.310, 0.895, "C  Pareto overtaking decision", COLORS["orange"], COLORS["orange_light"])

    # Input sidebar.
    add_box(ax, 0.028, 0.180, 0.075, 0.620, fc="#F8FBFF", ec="#A7B9CC", lw=0.6, radius=0.009)
    label(ax, 0.065, 0.760, "Input", size=7.0, weight="bold", color=COLORS["blue"])
    for i, txt in enumerate(["ego state", "nearby vehicles", "track map", "progress", "off-track flag"]):
        yy = 0.690 - i * 0.096
        ax.add_patch(Circle((0.046, yy), 0.008, facecolor=[COLORS["blue"], COLORS["green_mid"], COLORS["orange_mid"], COLORS["purple"], COLORS["red"]][i], edgecolor=COLORS["line"], lw=0.3))
        wrapped_label(ax, 0.073, yy, txt, width=10, size=4.9, ha="left")

    # Representation panels.
    add_box(ax, 0.115, 0.565, 0.195, 0.275, fc="white", ec="#9DB7D1", lw=0.6, radius=0.010)
    badge(ax, 0.135, 0.812, "1", COLORS["blue"])
    label(ax, 0.225, 0.812, "Map-relative encoding", size=6.3, weight="bold", color=COLORS["blue"])
    draw_track(ax, 0.128, 0.592, 0.168, 0.195)
    label(ax, 0.213, 0.548, "$\\{s,\\ell,e_\\psi,\\kappa,o\\}$", size=6.2, weight="bold")

    add_box(ax, 0.115, 0.215, 0.195, 0.285, fc="white", ec="#9DB7D1", lw=0.6, radius=0.010)
    badge(ax, 0.135, 0.472, "2", COLORS["blue"])
    label(ax, 0.228, 0.472, "Dynamic-neighborhood graph", size=5.9, weight="bold", color=COLORS["blue"])
    draw_dynamic_graph(ax, 0.133, 0.245, 0.160, 0.185)

    ax.plot([0.104, 0.114], [0.690, 0.690], color=COLORS["blue"], lw=0.7)
    ax.plot([0.104, 0.114], [0.400, 0.360], color=COLORS["blue"], lw=0.7)
    arrow(ax, 0.212, 0.565, 0.212, 0.501, color=COLORS["blue"], lw=0.8)

    # World model panels.
    add_box(ax, 0.365, 0.650, 0.270, 0.205, fc="white", ec="#A8BFAF", lw=0.6, radius=0.010)
    badge(ax, 0.383, 0.827, "3", COLORS["green"])
    label(ax, 0.505, 0.827, "Masked graph encoder", size=6.5, weight="bold", color=COLORS["green"])
    draw_slots(ax, 0.382, 0.674, 0.235, 0.140)

    add_box(ax, 0.365, 0.235, 0.270, 0.355, fc="white", ec="#A8BFAF", lw=0.6, radius=0.010)
    badge(ax, 0.383, 0.562, "4", COLORS["green"])
    draw_world_model(ax, 0.382, 0.258, 0.235, 0.292)

    arrow(ax, 0.310, 0.357, 0.365, 0.745, color=COLORS["line"], lw=0.8)
    arrow(ax, 0.500, 0.650, 0.500, 0.590, color=COLORS["green"], lw=0.8)

    # Planning panels.
    add_box(ax, 0.695, 0.605, 0.270, 0.240, fc="white", ec="#D2BCA9", lw=0.6, radius=0.010)
    badge(ax, 0.713, 0.817, "5", COLORS["orange"])
    label(ax, 0.840, 0.817, "Quality-guided proposals", size=6.5, weight="bold", color=COLORS["orange"])
    draw_proposals(ax, 0.713, 0.628, 0.235, 0.165)

    add_box(ax, 0.695, 0.185, 0.270, 0.360, fc="white", ec="#D2BCA9", lw=0.6, radius=0.010)
    badge(ax, 0.713, 0.517, "6", COLORS["orange"])
    label(ax, 0.850, 0.517, "Pareto multi-objective decision", size=6.2, weight="bold", color=COLORS["orange"])
    draw_planning(ax, 0.713, 0.213, 0.235, 0.275)

    arrow(ax, 0.635, 0.400, 0.695, 0.400, color=COLORS["line"], lw=0.8)
    arrow(ax, 0.830, 0.605, 0.830, 0.545, color=COLORS["orange"], lw=0.8)

    # Selected action block.
    add_box(ax, 0.973, 0.390, 0.022, 0.155, fc="#F8FBFF", ec="#A7B9CC", lw=0.55, radius=0.008)
    label(ax, 0.984, 0.502, "$a_t^*$", size=7.0, weight="bold", color=COLORS["blue"])
    ax.add_patch(Circle((0.984, 0.445), 0.012, facecolor=COLORS["blue_light"], edgecolor=COLORS["blue"], lw=0.55))
    arrow(ax, 0.965, 0.467, 0.973, 0.467, color=COLORS["blue"], lw=0.8)

    # Receding horizon feedback.
    arrow(ax, 0.984, 0.390, 0.984, 0.100, color=COLORS["gray"], lw=0.75, ls="--", ms=6)
    arrow(ax, 0.984, 0.100, 0.055, 0.100, color=COLORS["gray"], lw=0.75, ls="--", ms=6)
    arrow(ax, 0.055, 0.100, 0.055, 0.180, color=COLORS["gray"], lw=0.75, ls="--", ms=6)
    label(ax, 0.505, 0.055, "Receding-horizon feedback: execute first action, update telemetry, rebuild graph at $t+1$", size=6.2, weight="bold", color=COLORS["gray"])

    # Cross-stage arrows.
    arrow(ax, 0.310, 0.745, 0.365, 0.745, color=COLORS["line"], lw=0.8)
    arrow(ax, 0.635, 0.745, 0.695, 0.725, color=COLORS["line"], lw=0.8)
    arrow(ax, 0.635, 0.335, 0.695, 0.335, color=COLORS["line"], lw=0.8)

    # Figure contract mini labels.
    label(ax, 0.018, 0.035, "DNQ-DLC: dynamic graph + latent imagination + Pareto decision", size=6.2, weight="bold", ha="left", color=COLORS["line"])

    outputs = save_all(fig, OUT_DIR / "figure_method_dnq_dlc_architecture")
    SUBMISSION_FIG_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ["pdf", "svg"]:
        src = Path(outputs[ext])
        dst = SUBMISSION_FIG_DIR / src.name
        dst.write_bytes(src.read_bytes())
    print(outputs)


if __name__ == "__main__":
    main()
