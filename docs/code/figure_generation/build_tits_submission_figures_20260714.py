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
OUT = ROOT / "outputs/tits_dynamic_graph_expanded/tits_submission_figure_revision_20260714"
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
    source_path = ROOT / "outputs/tits_dynamic_graph_expanded/e1_200_summary/tables/online_benchmark_nature_direct_source_data.csv"
    stats = pd.read_csv(stats_path)
    source = pd.read_csv(source_path)
    rename = {
        "v6_runtime_dynamic_neighborhood_safe": "DNQ-DLC",
        "rule_expert_gate": "Rule expert",
        "rule_safety_gate": "Safety rule",
        "dlc_joint_transition_observer": "DLC-JTO",
        "dlc_joint_transition": "DLC-JT",
        "dlc_individual_transition": "DLC-IT",
    }
    colors = {"DNQ-DLC": BLUE, "Rule expert": RULE, "Safety rule": RULE_LIGHT,
              "DLC-JTO": DLC, "DLC-JT": DLC_LIGHT, "DLC-IT": NEUTRAL_LIGHT}
    methods = list(rename.values())

    def metric_rows(metric):
        x = stats[(stats.metric == metric) & (stats.algorithm.isin(rename))].copy()
        x["method"] = x.algorithm.map(rename)
        return x.set_index("method").loc[methods].reset_index()

    success = metric_rows("overtake_success_rate")
    desirable = metric_rows("elegant_overtake_rate")
    completion = metric_rows("completion_time_capped")
    grass = metric_rows("target_grass_rate")

    fig = plt.figure(figsize=(7.25, 5.05))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.0, 1.04], hspace=0.48, wspace=0.42)
    ax_a = fig.add_subplot(gs[0, 0])
    ax_b = fig.add_subplot(gs[0, 1])
    ax_c = fig.add_subplot(gs[1, 0])
    ax_d = fig.add_subplot(gs[1, 1])

    # a: success forest.
    y = np.arange(len(methods))[::-1]
    for yi, row in zip(y, success.itertuples()):
        ax_a.plot([row.ci95_low * 100, row.ci95_high * 100], [yi, yi], color=colors[row.method], lw=1.7)
        ax_a.scatter(row.mean * 100, yi, s=30 if row.method == "DNQ-DLC" else 22,
                     color=colors[row.method], edgecolor=NAVY, lw=0.45, zorder=3)
        ax_a.text(min(row.ci95_high * 100 + 2.0, 98), yi, f"{row.mean*100:.1f}", va="center", fontsize=6.2)
    ax_a.set_yticks(y, methods)
    ax_a.set_xlim(-1, 104)
    ax_a.set_xlabel("Overtake success (%)")
    ax_a.axvline(0, color=NEUTRAL_LIGHT, lw=0.7)
    panel_label(ax_a, "a")
    ax_a.set_title("Framework-level completion", loc="left", fontweight="bold", fontsize=8.0)

    # b: desirable behavior.
    for yi, row in zip(y, desirable.itertuples()):
        lo = 0.0 if pd.isna(row.ci95_low) else row.ci95_low * 100
        hi = 0.0 if pd.isna(row.ci95_high) else row.ci95_high * 100
        ax_b.plot([lo, hi], [yi, yi], color=colors[row.method], lw=1.7)
        ax_b.scatter(row.mean * 100, yi, s=30 if row.method == "DNQ-DLC" else 22,
                     color=colors[row.method], edgecolor=NAVY, lw=0.45, zorder=3)
        text_x = 2.0 if row.mean == 0 else min(hi + 1.2, 96)
        ax_b.text(text_x, yi, f"{row.mean*100:.1f}", va="center", fontsize=6.2)
    ax_b.set_yticks(y, ["" for _ in methods])
    ax_b.set_xlim(-1, 63)
    ax_b.set_xlabel("Desirable overtaking (%)")
    panel_label(ax_b, "b")
    ax_b.set_title("Behavior quality (all cases)", loc="left", fontweight="bold", fontsize=8.0)

    # c: survivor-conditioned trade-off.
    trade_methods = ["DNQ-DLC", "Rule expert", "Safety rule", "DLC-JTO", "DLC-JT"]
    cidx = completion.set_index("method")
    gidx = grass.set_index("method")
    for method in trade_methods:
        xv = cidx.loc[method, "mean"]
        yv = gidx.loc[method, "mean"]
        n = int(cidx.loc[method, "n"])
        ax_c.scatter(xv, yv, s=18 + 0.26 * n, color=colors[method], edgecolor=NAVY, lw=0.55, alpha=0.95)
        ax_c.annotate(method, (xv, yv), xytext=(4, 4), textcoords="offset points", fontsize=6.0)
    ax_c.set_xscale("log")
    ax_c.set_xlim(60, 2300)
    ax_c.set_ylim(0.18, 1.02)
    ax_c.set_xlabel("Completion time (steps, successful episodes)")
    ax_c.set_ylabel("Grass exposure (successful episodes)")
    ax_c.text(0.02, 0.96, "lower-left is preferable", transform=ax_c.transAxes,
              va="top", fontsize=6.1, color=NEUTRAL)
    panel_label(ax_c, "c")
    ax_c.set_title("Completion–off-track trade-off", loc="left", fontweight="bold", fontsize=8.0)

    # d: vehicle-count bands.
    suc = source[source.metric == "overtake_success_rate"].copy()
    suc["band"] = np.where(suc.num_agents <= 6, "N=4–6", "N=7–8")
    rows = []
    for algo in ["v6_runtime_dynamic_neighborhood_safe", "rule_expert_gate", "dlc_joint_transition_observer"]:
        for band in ["N=4–6", "N=7–8"]:
            arr = suc[(suc.algorithm == algo) & (suc.band == band)].value_display.astype(float).to_numpy()
            k = int(np.sum(arr > 0.0)); n = int(len(arr)); lo, hi = wilson(k, n)
            rows.append({"method": rename[algo], "band": band, "n": n, "k": k, "mean": k/n, "low": lo, "high": hi})
    band_df = pd.DataFrame(rows)
    offsets = {"DNQ-DLC": -0.08, "Rule expert": 0.0, "DLC-JTO": 0.08}
    for method in offsets:
        z = band_df[band_df.method == method]
        x = np.arange(2) + offsets[method]
        mean = z["mean"].to_numpy() * 100
        low = z["low"].to_numpy() * 100
        high = z["high"].to_numpy() * 100
        ax_d.errorbar(x, mean, yerr=np.vstack([mean-low, high-mean]), color=colors[method],
                      marker="o", ms=4.2 if method == "DNQ-DLC" else 3.6, lw=1.35,
                      capsize=2.2, label=method)
    ax_d.set_xticks([0, 1], ["N=4–6\ntraining range", "N=7–8\nvehicle-count extrapolation"])
    ax_d.set_ylim(-2, 105)
    ax_d.set_ylabel("Overtake success (%)")
    ax_d.legend(loc="lower left", fontsize=6.1)
    panel_label(ax_d, "d")
    ax_d.set_title("Changing vehicle count", loc="left", fontweight="bold", fontsize=8.0)

    for ax in (ax_a, ax_b, ax_c, ax_d):
        ax.tick_params(labelsize=6.4)
        ax.grid(False)
    fig.subplots_adjust(left=0.16, right=0.98, top=0.94, bottom=0.11)

    source_out = pd.concat([
        success.assign(panel="a_success"), desirable.assign(panel="b_desirable"),
        completion.assign(panel="c_completion"), grass.assign(panel="c_grass"),
        band_df.assign(panel="d_vehicle_band")
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
    screenshot_dir = ROOT / "outputs/tits_dynamic_graph_expanded/publication_first_person_visual_evidence_pack/E5_mechanism_dynamic_neighbor_N10_seed20000/screenshots_first_person"
    shots = [
        (101, screenshot_dir / "v6_runtime_dynamic_neighborhood_safe_n10_seed20000_01_approach_step101.png", "Approach"),
        (129, screenshot_dir / "v6_runtime_dynamic_neighborhood_safe_n10_seed20000_02_interaction_step129.png", "Interaction"),
        (157, screenshot_dir / "v6_runtime_dynamic_neighborhood_safe_n10_seed20000_03_completion_step157.png", "Pass complete"),
    ]
    repack = aggregate_repacking()

    fig = plt.figure(figsize=(7.25, 5.15))
    gs = fig.add_gridspec(2, 13, height_ratios=[1.02, 1.12], hspace=0.34, wspace=0.55)
    top_axes = [fig.add_subplot(gs[0, 0:4]), fig.add_subplot(gs[0, 4:8]), fig.add_subplot(gs[0, 8:12])]
    for i, (ax, (step, path, title)) in enumerate(zip(top_axes, shots)):
        im = Image.open(path).convert("RGB")
        ax.imshow(im)
        ax.set_xticks([]); ax.set_yticks([])
        for spine in ax.spines.values(): spine.set_visible(False)
        ax.set_title(f"{title} · step {step}", fontsize=7.1, fontweight="bold", pad=3)
        slots = selected_slots(mech, step)
        ax.text(0.02, 0.04, "ranked slots: " + " → ".join(map(str, slots)), transform=ax.transAxes,
                ha="left", va="bottom", fontsize=6.0, color="white",
                bbox=dict(boxstyle="round,pad=0.22", facecolor=NAVY, edgecolor="white", alpha=0.88))
        panel_label(ax, chr(ord('a') + i), x=-0.02, y=1.03)

    ax_d = fig.add_subplot(gs[1, 0:6])
    rng = np.random.default_rng(2026)
    for x0, n, color in [(0, 6, BLUE_LIGHT), (1, 8, BLUE)]:
        vals = repack.loc[repack.num_agents == n, "unique_top3_configurations"].to_numpy()
        jitter = rng.uniform(-0.10, 0.10, len(vals))
        ax_d.scatter(np.full(len(vals), x0) + jitter, vals, s=18, color=color, edgecolor=NAVY, lw=0.35, alpha=0.85)
        ax_d.plot([x0-0.16, x0+0.16], [np.mean(vals), np.mean(vals)], color=NAVY, lw=1.6)
    ax_d.set_xticks([0, 1], ["N=6", "N=8"])
    ax_d.set_ylabel("Unique ranked top-3 configurations")
    ax_d.set_ylim(0, max(repack.unique_top3_configurations) + 5)
    ax_d.text(0.03, 0.95,
              f"32/32 cases repacked\nmedian {repack.switch_count.median():.0f} switches per case",
              transform=ax_d.transAxes, ha="left", va="top", fontsize=6.2,
              bbox=dict(boxstyle="round,pad=0.25", facecolor="white", edgecolor=NEUTRAL_LIGHT))
    panel_label(ax_d, "d")
    ax_d.set_title("Runtime graph membership is not fixed", loc="left", fontsize=8.0, fontweight="bold")

    ax_e = fig.add_subplot(gs[1, 7:13])
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
    ax_e.set_title("Which innovation claims are supported?", loc="left", fontsize=8.0, fontweight="bold")
    ax_e.text(0.98, 0.02, "n=32 matched cases", transform=ax_e.transAxes,
              ha="right", va="bottom", fontsize=5.8, color=NEUTRAL)

    fig.subplots_adjust(left=0.08, right=0.985, top=0.94, bottom=0.10)
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
            "core_results": "The complete framework improves completion versus retrained DLC while exposing the grass trade-off.",
            "mechanism_attribution": "Runtime repacking is active, quality terms have supported effects, and selector superiority remains unproven.",
            "supplementary_sequence": "Selected simulator frames illustrate the same-track race without serving as population evidence.",
        },
    }
    (OUT / "figure_build_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
