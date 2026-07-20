#!/usr/bin/env python
"""Build the revised IEEE T-ITS figure set using Python only."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Circle
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/tits_dynamic_graph_expanded/tits_submission_figure_revision_20260716"
FIG = OUT / "figures"
TAB = OUT / "tables"
PAPER_FIG = ROOT / "paper_rewriting_output_tits_dynamic_graph_draft_20260625/tits_submission_final/figures"

BLUE = "#1F5A94"
BLUE_LIGHT = "#A9C7E5"
NAVY = "#18324A"
RULE = "#B07A72"
RULE_LIGHT = "#E2C2BC"
DLC = "#75679A"
DLC_LIGHT = "#C9C2DA"
NEUTRAL = "#69737D"
NEUTRAL_LIGHT = "#D9DEE3"
GREEN = "#2B8A6E"
RED = "#B64645"
GOLD = "#C58A2C"


def configure():
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "Liberation Sans"],
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "font.size": 7.2,
        "axes.linewidth": 0.75,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "legend.frameon": False,
        "xtick.major.width": 0.65,
        "ytick.major.width": 0.65,
        "xtick.major.size": 3.0,
        "ytick.major.size": 3.0,
    })


def export(fig, stem: Path):
    stem.parent.mkdir(parents=True, exist_ok=True)
    outputs = {}
    for ext in ("svg", "pdf", "png", "tiff"):
        path = stem.with_suffix(f".{ext}")
        kwargs = {"bbox_inches": "tight", "facecolor": "white"}
        if ext in {"png", "tiff"}:
            kwargs["dpi"] = 600
        fig.savefig(path, **kwargs)
        outputs[ext] = str(path.relative_to(ROOT))
    plt.close(fig)
    return outputs


def panel_label(ax, label, x=-0.08, y=1.02):
    ax.text(x, y, label, transform=ax.transAxes, ha="left", va="bottom",
            fontsize=8.4, fontweight="bold")


def box(ax, xy, wh, title, body, edge, face="#FFFFFF", title_color=None):
    x, y = xy
    w, h = wh
    p = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.012,rounding_size=0.015",
                       linewidth=1.0, edgecolor=edge, facecolor=face)
    ax.add_patch(p)
    ax.text(x + 0.025 * w, y + h - 0.12 * h, title, ha="left", va="top",
            fontsize=8.0, fontweight="bold", color=title_color or edge)
    ax.text(x + 0.025 * w, y + h - 0.28 * h, body, ha="left", va="top",
            fontsize=6.25, color=NAVY, linespacing=1.25)
    return p


def arrow(ax, start, end, color=NEUTRAL, lw=1.1, style="-|>"):
    ax.add_patch(FancyArrowPatch(start, end, arrowstyle=style, mutation_scale=10,
                                linewidth=lw, color=color, shrinkA=4, shrinkB=4))


def plot_method():
    fig, ax = plt.subplots(figsize=(7.2, 3.65))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    box(ax, (0.02, 0.30), (0.22, 0.62), "a  Runtime graph",
        "Map-relative telemetry\nAll surrounding vehicles scored\nK=3 masked relation tensor\nVehicle identities may change",
        BLUE, "#F3F8FC")
    box(ax, (0.27, 0.30), (0.22, 0.62), "b  Graph-DLC model",
        "Self/relation encoders\nMasked invariant aggregation\nRecurrent latent transition\nState, reward, risk, uncertainty",
        GREEN, "#F1F8F5")
    box(ax, (0.52, 0.30), (0.22, 0.62), "c  Candidate rollouts",
        "Rule anchor + learned proposal\nHandcrafted racing maneuvers\nH-step latent rollouts\nSlots fixed only inside each rollout",
        DLC, "#F6F3FA")
    box(ax, (0.77, 0.30), (0.21, 0.62), "d  Quality decision",
        "Progress and overtaking\nTrack quality and proximity risk\nUncertainty penalty\nExecute first action + recovery guard",
        GOLD, "#FCF8EF")
    for x in (0.24, 0.49, 0.74):
        arrow(ax, (x, 0.61), (x + 0.03, 0.61), color=NAVY)

    # Simple graph glyph in panel a.
    center = (0.13, 0.43)
    ax.add_patch(Circle(center, 0.018, facecolor=BLUE, edgecolor="white", lw=0.7, zorder=4))
    for theta, c in zip(np.linspace(0, 2 * np.pi, 6, endpoint=False),
                        [RULE, DLC, NEUTRAL_LIGHT, RULE_LIGHT, DLC_LIGHT, NEUTRAL_LIGHT]):
        px = center[0] + 0.067 * math.cos(theta)
        py = center[1] + 0.075 * math.sin(theta)
        ax.plot([center[0], px], [center[1], py], color=BLUE_LIGHT if c != NEUTRAL_LIGHT else NEUTRAL_LIGHT,
                lw=1.2 if c != NEUTRAL_LIGHT else 0.7, ls="-" if c != NEUTRAL_LIGHT else "--", zorder=2)
        ax.add_patch(Circle((px, py), 0.014, facecolor=c, edgecolor="white", lw=0.6, zorder=3))
    ax.text(0.13, 0.325, "rebuild at every real step", ha="center", va="center",
            fontsize=6.0, color=BLUE, fontweight="bold")

    # Receding-horizon loop.
    loop = FancyBboxPatch((0.12, 0.07), 0.76, 0.13, boxstyle="round,pad=0.012,rounding_size=0.018",
                          linewidth=0.9, edgecolor=NAVY, facecolor="#F7F9FB")
    ax.add_patch(loop)
    labels = ["execute", "observe t+1", "rebuild graph", "replan"]
    xs = [0.20, 0.39, 0.59, 0.79]
    for i, (x, label) in enumerate(zip(xs, labels)):
        ax.text(x, 0.135, label, ha="center", va="center", fontsize=6.8,
                fontweight="bold" if label == "rebuild graph" else "normal",
                color=BLUE if label == "rebuild graph" else NAVY)
        if i < len(xs) - 1:
            arrow(ax, (x + 0.045, 0.135), (xs[i + 1] - 0.055, 0.135), color=NEUTRAL, lw=0.9)
    arrow(ax, (0.88, 0.10), (0.92, 0.30), color=NAVY, lw=1.0)
    arrow(ax, (0.12, 0.12), (0.06, 0.30), color=NAVY, lw=1.0)
    ax.text(0.50, 0.965, "DNQ-DLC: dynamic physical graph, bounded tensor interface, quality-guided latent planning",
            ha="center", va="top", fontsize=9.0, fontweight="bold", color=NAVY)

    fig.subplots_adjust(0.01, 0.01, 0.99, 0.99)
    return export(fig, FIG / "figure_method_dnq_dlc_runtime_graph")


def wilson(k, n, z=1.959963984540054):
    p = k / n
    den = 1 + z * z / n
    center = (p + z * z / (2 * n)) / den
    half = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n) / den
    return max(0.0, center - half), min(1.0, center + half)


def plot_core_results():
    stats_path = ROOT / "outputs/tits_dynamic_graph_expanded/e1_200_summary/tables/online_benchmark_nature_direct_statistics.csv"
    paired_path = ROOT / "outputs/tits_dynamic_graph_expanded/e1_primary_endpoint_20260716/e1_primary_paired_success.csv"
    strata_path = ROOT / "outputs/tits_dynamic_graph_expanded/e1_primary_endpoint_20260716/e1_vehicle_count_strata.csv"
    stats = pd.read_csv(stats_path)
    paired = pd.read_csv(paired_path)
    strata = pd.read_csv(strata_path)

    rename = {
        "v6_runtime_dynamic_neighborhood_safe": "DNQ-DLC",
        "rule_expert_gate": "Rule Expert",
        "rule_safety_gate": "Safety Rule",
        "dlc_joint_transition_observer": "DLC-JTO",
        "ppo_continuous": "PPO legacy",
        "sac_continuous": "SAC legacy",
        "td3_continuous": "TD3 legacy",
        "dlc_joint_transition": "DLC-JT",
    }
    colors = {
        "DNQ-DLC": BLUE,
        "Rule Expert": RULE,
        "Safety Rule": RULE_LIGHT,
        "DLC-JTO": DLC,
        "DLC-JT": DLC_LIGHT,
        "PPO legacy": "#8E99A4",
        "SAC legacy": "#C5CBD1",
        "TD3 legacy": "#657687",
    }
    methods = ["DNQ-DLC", "Rule Expert", "Safety Rule", "DLC-JTO", "PPO legacy", "SAC legacy", "TD3 legacy"]

    def metric_rows(metric, selected=methods):
        algorithms = [key for key, value in rename.items() if value in selected]
        frame = stats[(stats.metric == metric) & (stats.algorithm.isin(algorithms))].copy()
        frame["method"] = frame.algorithm.map(rename)
        return frame.set_index("method").loc[selected].reset_index()

    success = metric_rows("overtake_success_rate")
    completion = metric_rows("completion_time_capped", ["DNQ-DLC", "Rule Expert", "Safety Rule", "DLC-JTO", "DLC-JT"])
    grass = metric_rows("target_grass_rate", ["DNQ-DLC", "Rule Expert", "Safety Rule", "DLC-JTO", "DLC-JT"])

    # IEEE T-ITS double-column width (about 183 mm).  The compact two-row
    # grid keeps all text at 7--8 pt at final size without using slide-scale
    # fonts or redundant whitespace.
    fig = plt.figure(figsize=(7.16, 4.08))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.00, 0.96], hspace=0.42, wspace=0.34)
    ax_a = fig.add_subplot(gs[0, 0])
    ax_b = fig.add_subplot(gs[0, 1])
    ax_c = fig.add_subplot(gs[1, 0])
    ax_d = fig.add_subplot(gs[1, 1])

    # a: absolute success estimates show the benchmark scale.
    y = np.arange(len(methods))[::-1]
    for yi, row in zip(y, success.itertuples()):
        color = colors[row.method]
        ax_a.plot([row.ci95_low * 100, row.ci95_high * 100], [yi, yi], color=color, lw=1.65)
        ax_a.scatter(row.mean * 100, yi, s=31 if row.method == "DNQ-DLC" else 22,
                     color=color, edgecolor=NAVY, lw=0.45, zorder=3)
        ax_a.text(min(row.ci95_high * 100 + 1.8, 98.5), yi, f"{row.mean*100:.1f}",
                  va="center", fontsize=6.15)
    ax_a.set_yticks(y, methods)
    ax_a.set_xlim(-2, 104)
    ax_a.set_xlabel("Overtake success (%)")
    panel_label(ax_a, "a")
    ax_a.set_title("Primary endpoint", loc="left", fontweight="bold", fontsize=8.0)

    # b: matched-case effect sizes are the inferential hero panel.
    order = ["Rule Expert", "Safety Rule", "DLC-JTO", "PPO legacy", "SAC legacy", "TD3 legacy"]
    pair = paired.set_index("comparator_label").loc[order].reset_index()
    yb = np.arange(len(order))[::-1]
    for yi, row in zip(yb, pair.itertuples()):
        lo = row.paired_bootstrap_ci95_low * 100
        hi = row.paired_bootstrap_ci95_high * 100
        est = row.paired_difference * 100
        ax_b.plot([lo, hi], [yi, yi], color=GREEN, lw=1.75)
        ax_b.scatter(est, yi, s=27, color=GREEN, edgecolor=NAVY, lw=0.45, zorder=3)
        ax_b.text(min(hi + 1.5, 91), yi, f"+{est:.1f}", va="center", fontsize=6.15)
    ax_b.axvline(0, color=NEUTRAL, lw=0.8, ls="--")
    ax_b.set_yticks(yb, order)
    ax_b.set_xlim(-3, 94)
    ax_b.set_xlabel("DNQ-DLC minus comparator (percentage points)")
    ax_b.text(0.98, 0.97, "n=200 matched cases each", transform=ax_b.transAxes,
              ha="right", va="top", fontsize=5.9, color=NEUTRAL)
    panel_label(ax_b, "b")
    ax_b.set_title("Matched success gain", loc="left", fontweight="bold", fontsize=8.0)

    # c: prespecified training-range and vehicle-count-extrapolation strata.
    band_order = ["N=4-6 training range", "N=7-8 extrapolation"]
    stratum_methods = ["DNQ-DLC", "Rule Expert", "DLC-JTO"]
    offsets = {"DNQ-DLC": -0.10, "Rule Expert": 0.0, "DLC-JTO": 0.10}
    for method in stratum_methods:
        frame = strata[strata.algorithm_label == method].set_index("vehicle_count_stratum").loc[band_order]
        x = np.arange(2) + offsets[method]
        mean = frame.success_rate.to_numpy() * 100
        low = frame.wilson_ci95_low.to_numpy() * 100
        high = frame.wilson_ci95_high.to_numpy() * 100
        ax_c.errorbar(x, mean, yerr=np.vstack([mean-low, high-mean]), color=colors[method],
                      marker="o", ms=4.3 if method == "DNQ-DLC" else 3.7, lw=1.35,
                      capsize=2.2, label=method)
    dnq_strata = strata[strata.algorithm_label == "DNQ-DLC"].set_index("vehicle_count_stratum").loc[band_order]
    label_positions = [(0.16, 98.5), (0.94, 98.5)]
    for (label_x, label_y), row in zip(label_positions, dnq_strata.itertuples()):
        delta = row.paired_difference_vs_rule_expert * 100
        ax_c.text(
            label_x,
            label_y,
            f"{delta:+.1f} pp vs Rule",
            ha="center",
            va="top",
            fontsize=5.35,
            color=NAVY,
            bbox=dict(boxstyle="round,pad=0.18", facecolor="white",
                      edgecolor=NEUTRAL_LIGHT, linewidth=0.55, alpha=0.95),
            zorder=5,
        )
    ax_c.set_xticks([0, 1], ["N=4–6\ntraining range", "N=7–8\nextrapolation"])
    ax_c.set_ylim(0, 102)
    ax_c.set_ylabel("Overtake success (%)")
    ax_c.legend(loc="lower left", bbox_to_anchor=(0.0, 0.15), fontsize=5.65,
                handlelength=1.5, labelspacing=0.25)
    panel_label(ax_c, "c")
    ax_c.set_title("Vehicle-count strata", loc="left", fontweight="bold", fontsize=8.0)

    # d: secondary survivor-conditioned trade-off prevents a safety-dominance reading.
    trade_methods = ["DNQ-DLC", "Rule Expert", "Safety Rule", "DLC-JTO", "DLC-JT"]
    cidx = completion.set_index("method")
    gidx = grass.set_index("method")
    label_offsets = {
        "DNQ-DLC": (4, 4), "Rule Expert": (4, -10), "Safety Rule": (4, 5),
        "DLC-JTO": (4, 4), "DLC-JT": (4, -10),
    }
    for method in trade_methods:
        xv = cidx.loc[method, "mean"]
        yv = gidx.loc[method, "mean"]
        n = int(cidx.loc[method, "n"])
        ax_d.scatter(xv, yv, s=18 + 0.24 * n, color=colors[method], edgecolor=NAVY, lw=0.55, alpha=0.95)
        ax_d.annotate(method, (xv, yv), xytext=label_offsets[method], textcoords="offset points", fontsize=5.8)
    ax_d.set_xscale("log")
    ax_d.set_xlim(60, 2300)
    ax_d.set_ylim(0.18, 1.02)
    ax_d.set_xlabel("Completion time (steps; successful cases)")
    ax_d.set_ylabel("Grass exposure (successful cases)")
    ax_d.text(0.02, 0.96, "secondary, survivor-conditioned", transform=ax_d.transAxes,
              va="top", fontsize=5.8, color=NEUTRAL)
    panel_label(ax_d, "d")
    ax_d.set_title("Completion–off-track trade-off", loc="left", fontweight="bold", fontsize=8.0)

    for ax in (ax_a, ax_b, ax_c, ax_d):
        ax.tick_params(labelsize=6.25)
        ax.grid(False)
    fig.subplots_adjust(left=0.145, right=0.985, top=0.93, bottom=0.12)

    source_out = pd.concat([
        success.assign(panel="a_absolute_success"),
        pair.assign(panel="b_paired_success_gain"),
        strata.assign(panel="c_vehicle_count_strata"),
        completion.assign(panel="d_completion"),
        grass.assign(panel="d_grass"),
    ], ignore_index=True, sort=False)
    TAB.mkdir(parents=True, exist_ok=True)
    source_out.to_csv(TAB / "figure_e1_core_evidence_source.csv", index=False)
    return export(fig, FIG / "figure_e1_core_evidence")


def selected_slots(mech, step):
    row = mech.loc[mech.step == step].iloc[0]
    return [int(row.top1_neighbor), int(row.top2_neighbor), int(row.top3_neighbor)]


def aggregate_repacking():
    rows_csv = ROOT / "outputs/tits_dynamic_graph_expanded/randomized_attribution_confirmatory_20260710/aggregate/randomized_attribution_rows.csv"
    out = []
    for row in csv.DictReader(rows_csv.open(encoding="utf-8")):
        if row["algorithm"] != "dnq_dlc_full":
            continue
        summary = json.loads((ROOT / row["source_path"]).read_text(encoding="utf-8"))
        trace = json.loads((ROOT / summary["trace_path"]).read_text(encoding="utf-8"))
        target = int(summary["target_agent"])
        packed = []
        for item in trace:
            ids = item.get("dynamic_neighbor_ids") or []
            if ids and isinstance(ids[0], list):
                ids = ids[target]
            packed.append(tuple(int(x) for x in ids[:3]))
        changes = sum(a != b for a, b in zip(packed, packed[1:]))
        out.append({
            "track": Path(row["track_path"]).stem,
            "num_agents": int(row["num_agents"]),
            "seed": int(row["seed"]),
            "steps": len(packed),
            "switch_count": changes,
            "switch_rate": changes / max(len(packed)-1, 1),
            "unique_top3_configurations": len(set(packed)),
        })
    return pd.DataFrame(out)


def plot_mechanism_attribution():
    mech_path = ROOT / "outputs/tits_dynamic_graph_expanded/video_evidence_raw/e5_mechanism_from_clean_e3_n10/tables/e5_dynamic_neighborhood_mechanism_source_data.csv"
    mech = pd.read_csv(mech_path)
    attr_path = ROOT / "outputs/tits_dynamic_graph_expanded/randomized_attribution_confirmatory_20260710/aggregate/randomized_attribution_report.json"
    attr = json.loads(attr_path.read_text(encoding="utf-8"))["paired_full_minus_ablation"]
    screenshot_dir = ROOT / "outputs/tits_dynamic_graph_expanded/publication_first_person_visual_evidence_pack/E5_mechanism_dynamic_neighbor_N10_seed20000/screenshots_topdown"
    shots = [
        (101, screenshot_dir / "v6_runtime_dynamic_neighborhood_safe_n10_seed20000_01_approach_step101.png", "Approach"),
        (129, screenshot_dir / "v6_runtime_dynamic_neighborhood_safe_n10_seed20000_02_interaction_step129.png", "Interaction"),
        (157, screenshot_dir / "v6_runtime_dynamic_neighborhood_safe_n10_seed20000_03_completion_step157.png", "Pass complete"),
    ]
    repack = aggregate_repacking()

    fig = plt.figure(figsize=(7.16, 4.32))
    gs = fig.add_gridspec(2, 12, height_ratios=[0.90, 1.10], hspace=0.25, wspace=0.38)
    top_axes = [
        fig.add_subplot(gs[0, 0:4]),
        fig.add_subplot(gs[0, 4:8]),
        fig.add_subplot(gs[0, 8:12]),
    ]
    # Global crop applied identically to all three top-down frames.  It removes
    # empty track area while retaining the full local vehicle pack and graph
    # edges.  No local contrast, colour, or object-level edits are applied.
    crop_box = (800, 250, 1800, 1150)
    for i, (ax, (step, path, title)) in enumerate(zip(top_axes, shots)):
        im = Image.open(path).convert("RGB").crop(crop_box)
        ax.imshow(im)
        ax.set_xticks([]); ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_visible(True)
            spine.set_color("#D5DADE")
            spine.set_linewidth(0.55)
        ax.set_title(f"{title} (step {step})", fontsize=6.9, fontweight="bold", pad=2.5)
        slots = selected_slots(mech, step)
        ax.text(
            0.02,
            0.035,
            "ranked slots  " + " → ".join(map(str, slots)),
            transform=ax.transAxes,
            ha="left",
            va="bottom",
            fontsize=5.65,
            color="white",
            bbox=dict(boxstyle="round,pad=0.20", facecolor=NAVY,
                      edgecolor="white", linewidth=0.5, alpha=0.90),
        )
        ax.text(
            0.018,
            0.975,
            chr(ord("a") + i),
            transform=ax.transAxes,
            ha="left",
            va="top",
            fontsize=8.2,
            fontweight="bold",
            color="white",
            bbox=dict(boxstyle="round,pad=0.12", facecolor=NAVY,
                      edgecolor="none", alpha=0.82),
        )

    ax_d = fig.add_subplot(gs[1, 0:5])
    rng = np.random.default_rng(2026)
    positions = [0.0, 0.78]
    groups = [
        repack.loc[repack.num_agents == n, "unique_top3_configurations"].to_numpy()
        for n in (6, 8)
    ]
    violins = ax_d.violinplot(
        groups,
        positions=positions,
        widths=0.48,
        showmeans=False,
        showmedians=False,
        showextrema=False,
        bw_method=0.70,
        points=200,
    )
    for body, color in zip(violins["bodies"], ["#A8D85D", "#56B87A"]):
        body.set_facecolor(color)
        body.set_edgecolor("#202020")
        body.set_linewidth(0.90)
        body.set_alpha(0.24)

    ax_d.boxplot(
        groups,
        positions=positions,
        widths=0.18,
        patch_artist=True,
        showfliers=False,
        whis=(5, 95),
        boxprops=dict(facecolor="white", edgecolor="#202020", linewidth=0.95, alpha=0.95),
        whiskerprops=dict(color="#202020", linewidth=0.90),
        capprops=dict(color="#202020", linewidth=0.90),
        medianprops=dict(color="#202020", linewidth=1.35),
    )
    for x0, vals, color in zip(positions, groups, ["#91D33F", "#37B56A"]):
        jitter = rng.uniform(-0.085, 0.085, len(vals))
        ax_d.scatter(
            np.full(len(vals), x0) + jitter,
            vals,
            s=18,
            color=color,
            edgecolor="#202020",
            lw=0.45,
            alpha=0.84,
            zorder=3,
        )
        median = float(np.median(vals))
        ax_d.scatter(
            x0, median, s=22, color="#E31A1C",
            edgecolor="white", lw=0.50, zorder=5,
        )
    ax_d.set_xticks(positions, ["N=6", "N=8"])
    ax_d.set_xlim(-0.28, 1.06)
    ax_d.set_ylabel("Unique ranked top-3 sets")
    ax_d.set_ylim(0, max(repack.unique_top3_configurations) + 5)
    ax_d.text(
        0.03, 0.95,
        f"32/32 cases repacked\nmedian {repack.switch_count.median():.0f} switches/case",
        transform=ax_d.transAxes, ha="left", va="top", fontsize=5.85,
        bbox=dict(
            boxstyle="round,pad=0.24", facecolor="white",
            edgecolor="#555555", linewidth=0.55, alpha=0.94,
        ),
    )
    panel_label(ax_d, "d")
    ax_d.set_title("Runtime graph repacking", loc="left", fontsize=7.6, fontweight="bold")

    ax_e = fig.add_subplot(gs[1, 6:12])
    specs = [
        ("Risk/uncertainty\n(desirable)", "dnq_w_o_risk_uncertainty", "elegant_overtake_rate", 1),
        ("Safety-quality\n(desirable)", "dnq_w_o_safety_quality", "elegant_overtake_rate", 1),
        ("Quality proposal\n(lower grass)", "dnq_w_o_quality_proposal", "target_grass_rate", -1),
        ("Safety-quality\n(lower grass)", "dnq_w_o_safety_quality", "target_grass_rate", -1),
        ("Dynamic selector\n(desirable)", "dnq_w_o_dynamic_selection", "elegant_overtake_rate", 1),
        ("Dynamic selector\n(lower grass)", "dnq_w_o_dynamic_selection", "target_grass_rate", -1),
    ]
    forest_rows = []
    yy = np.arange(len(specs))[::-1]
    for yi, (label, variant, metric, sign) in zip(yy, specs):
        r = attr[variant]["metrics"][metric]
        est = sign * r["full_minus_ablation_mean"]
        lo0, hi0 = r["ci95_bootstrap"]
        lo, hi = (sign*lo0, sign*hi0) if sign == 1 else (-hi0, -lo0)
        sig = lo > 0 or hi < 0
        color = BLUE if sig else NEUTRAL
        ax_e.plot([lo, hi], [yi, yi], color=color, lw=1.6)
        ax_e.scatter(est, yi, s=28, color=color, edgecolor="white", lw=0.55, zorder=3)
        forest_rows.append({"label": label.replace("\n", " "), "estimate": est, "ci_low": lo, "ci_high": hi, "significant": sig})
    ax_e.axvline(0, color=NEUTRAL_LIGHT, lw=0.9, ls="--")
    ax_e.set_yticks(yy, [x[0] for x in specs], fontsize=6.0)
    ax_e.set_xlim(-0.26, 0.44)
    ax_e.set_xlabel("Paired effect (positive favors full controller)")
    panel_label(ax_e, "e")
    ax_e.set_title("Supported component effects", loc="left", fontsize=7.6, fontweight="bold")
    ax_e.text(0.98, 0.02, "n=32 matched cases", transform=ax_e.transAxes,
              ha="right", va="bottom", fontsize=5.8, color=NEUTRAL)

    for ax in (ax_d, ax_e):
        ax.tick_params(labelsize=6.15)
        ax.grid(False)
    ax_d.grid(axis="y", color="#D9D9D9", lw=0.45, alpha=0.75)
    ax_d.set_axisbelow(True)
    fig.subplots_adjust(left=0.075, right=0.99, top=0.94, bottom=0.105)
    TAB.mkdir(parents=True, exist_ok=True)
    repack.to_csv(TAB / "figure_e5_runtime_repacking_source.csv", index=False)
    pd.DataFrame(forest_rows).to_csv(TAB / "figure_e5_component_effect_source.csv", index=False)
    return export(fig, FIG / "figure_e5_mechanism_attribution")


def plot_supp_sequence():
    base = ROOT / "outputs/tits_dynamic_graph_expanded/e4_four_controller_race_no_background/visual_pack_no_background_four_algorithms/screenshots/case02_nominal_s5"
    cols = [
        ("Approach", base / "topdown_approach_step0021.png", base / "dnq_first_person_approach_step0021.png"),
        ("Side-by-side", base / "topdown_side_by_side_step0118.png", base / "dnq_first_person_side_by_side_step0118.png"),
        ("Pass complete", base / "topdown_overtake_complete_step0216.png", base / "dnq_first_person_overtake_complete_step0216.png"),
    ]
    fig, axes = plt.subplots(2, 3, figsize=(7.2, 4.0), gridspec_kw={"hspace": 0.18, "wspace": 0.06})
    for c, (title, top, fp) in enumerate(cols):
        for r, path in enumerate([top, fp]):
            axes[r, c].imshow(Image.open(path).convert("RGB"))
            axes[r, c].set_xticks([]); axes[r, c].set_yticks([])
            for spine in axes[r, c].spines.values(): spine.set_visible(False)
        axes[0, c].set_title(title, fontsize=7.4, fontweight="bold")
    axes[0, 0].text(-0.04, 0.5, "Top-down", transform=axes[0, 0].transAxes,
                    rotation=90, va="center", ha="right", fontsize=7.0, fontweight="bold")
    axes[1, 0].text(-0.04, 0.5, "Ego view", transform=axes[1, 0].transAxes,
                    rotation=90, va="center", ha="right", fontsize=7.0, fontweight="bold")
    fig.suptitle("Selected same-track four-controller diagnostic (DNQ-DLC starts from the rear)",
                 y=0.99, fontsize=8.6, fontweight="bold", color=NAVY)
    fig.subplots_adjust(left=0.08, right=0.99, top=0.91, bottom=0.02)
    return export(fig, FIG / "figure_s1_same_track_simulation_sequence")


def copy_to_paper(outputs):
    PAPER_FIG.mkdir(parents=True, exist_ok=True)
    for group in outputs.values():
        for rel in group.values():
            src = ROOT / rel
            (PAPER_FIG / src.name).write_bytes(src.read_bytes())


def main():
    configure()
    FIG.mkdir(parents=True, exist_ok=True)
    TAB.mkdir(parents=True, exist_ok=True)
    outputs = {
        "method": plot_method(),
        "core_results": plot_core_results(),
        "mechanism_attribution": plot_mechanism_attribution(),
        "supplementary_sequence": plot_supp_sequence(),
    }
    copy_to_paper(outputs)
    report = {
        "status": "pass",
        "backend": "Python/matplotlib/Pillow only",
        "outputs": outputs,
        "figure_contract": {
            "method": "Runtime graph rebuilding plus bounded tensorization and quality-guided latent planning.",
            "core_results": "Matched 200-case comparisons support a complete-framework success advantage while exposing the survivor-conditioned grass trade-off.",
            "mechanism_attribution": "Runtime repacking is active, quality terms have supported effects, and selector superiority remains unproven.",
            "supplementary_sequence": "Selected simulator frames illustrate the same-track race without serving as population evidence.",
        },
    }
    (OUT / "figure_build_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
