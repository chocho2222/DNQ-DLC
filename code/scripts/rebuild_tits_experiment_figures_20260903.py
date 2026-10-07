#!/usr/bin/env python
"""Rebuild the TITS Experiments figures from frozen source data.

The script creates separate evidence figures for primary completion,
completion-quality trade-off, dynamic-opponent snapshots, and component
attribution. Existing paper figures are never overwritten by this script;
the caller archives them before copying the final exports into the manuscript.
"""

from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Circle
from PIL import Image
try:
    from tits_figure_style import color_for_algorithm
except ImportError:
    from scripts.tits_figure_style import color_for_algorithm


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/tits_dynamic_graph_expanded/tits_experiments_figure_revision_20260903"
FIG = OUT / "figures"
TAB = OUT / "tables"
PAPER_FIG = ROOT / "paper_rewriting_output_tits_dynamic_graph_draft_20260625/tits_submission_final/figures"

DNQ = color_for_algorithm("DNQ-DLC")
RULE = color_for_algorithm("Rule Expert")
RULE_LIGHT = color_for_algorithm("Safety Rule")
DLC = color_for_algorithm("DLC-JTO")
RL = "#A9ADB1"
GAIN = "#2B8A6E"
TEXT = "#20252A"
MID = "#777F86"
GRID = "#D9DDE0"
OPPONENT = "#E58B2B"


def configure():
    # Times New Roman is requested by the author; Liberation Serif is the
    # metric-compatible fallback on systems without the Microsoft font.
    plt.rcParams.update({
        "font.family": "serif",
        "font.serif": ["Times New Roman", "Liberation Serif", "Nimbus Roman", "DejaVu Serif"],
        "font.size": 8.5,
        "font.weight": "normal",
        "axes.labelweight": "normal",
        "axes.titleweight": "normal",
        "figure.titleweight": "normal",
        "axes.linewidth": 1.6,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "xtick.major.width": 1.5,
        "ytick.major.width": 1.5,
        "xtick.major.size": 4,
        "ytick.major.size": 4,
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "legend.frameon": False,
        "axes.unicode_minus": False,
    })


def export(fig, stem: Path):
    stem.parent.mkdir(parents=True, exist_ok=True)
    outputs = {}
    for ext in ("svg", "pdf", "png", "tiff"):
        path = stem.with_suffix(f".{ext}")
        kw = {"bbox_inches": "tight", "facecolor": "white"}
        if ext in {"png", "tiff"}:
            kw["dpi"] = 600
        fig.savefig(path, **kw)
        outputs[ext] = str(path)
    plt.close(fig)
    return outputs


def label(ax, text):
    ax.text(-0.10, 1.04, text, transform=ax.transAxes, fontsize=11,
            fontweight="bold", ha="left", va="bottom", color=TEXT)


def source_paths():
    base = ROOT / "outputs/tits_dynamic_graph_expanded"
    return {
        "stats": base / "e1_200_summary/tables/online_benchmark_nature_direct_statistics.csv",
        "paired": base / "e1_primary_endpoint_20260716/e1_primary_paired_success.csv",
        "strata": base / "e1_primary_endpoint_20260716/e1_vehicle_count_strata.csv",
        "attr": base / "randomized_attribution_confirmatory_20260710/aggregate/randomized_attribution_report.json",
        "rows": base / "randomized_attribution_confirmatory_20260710/aggregate/randomized_attribution_rows.csv",
        "shots": base / "publication_first_person_visual_evidence_pack/E5_mechanism_dynamic_neighbor_N10_seed20000/screenshots_topdown",
        "trace": base / "publication_visual_asset_pack_raw/E3_scale_N10_seed20000/traces/v6_runtime_dynamic_neighborhood_safe_n10_seed20000.trace.json",
    }


def build_primary():
    paths = source_paths()
    stats = pd.read_csv(paths["stats"])
    paired = pd.read_csv(paths["paired"])
    strata = pd.read_csv(paths["strata"])
    rename = {
        "v6_runtime_dynamic_neighborhood_safe": "DNQ-DLC",
        "rule_expert_gate": "Rule Expert",
        "rule_safety_gate": "Safety Rule",
        "dlc_joint_transition_observer": "DLC-JTO",
        "ppo_continuous": "PPO legacy",
        "sac_continuous": "SAC legacy",
        "td3_continuous": "TD3 legacy",
    }
    colors = {"DNQ-DLC": DNQ, "Rule Expert": RULE, "Safety Rule": RULE_LIGHT,
              "DLC-JTO": DLC, "PPO legacy": color_for_algorithm("PPO"),
              "SAC legacy": color_for_algorithm("SAC"), "TD3 legacy": color_for_algorithm("TD3")}
    order = ["DNQ-DLC", "Rule Expert", "Safety Rule", "DLC-JTO", "PPO legacy", "SAC legacy", "TD3 legacy"]
    frame = stats[stats.metric == "overtake_success_rate"].copy()
    frame["method"] = frame.algorithm.map(rename)
    frame = frame.dropna(subset=["method"]).set_index("method").loc[order].reset_index()
    pairs = paired.set_index("comparator_label").loc[["Rule Expert", "Safety Rule", "DLC-JTO", "PPO legacy", "SAC legacy", "TD3 legacy"]].reset_index()

    fig = plt.figure(figsize=(7.18, 4.25))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.05, 0.95], hspace=0.52, wspace=0.36)
    ax = fig.add_subplot(gs[0, 0])
    y = np.arange(len(order))[::-1]
    for yi, row in zip(y, frame.itertuples()):
        c = colors[row.method]
        ax.plot([row.ci95_low * 100, row.ci95_high * 100], [yi, yi], color=c, lw=2.0)
        ax.scatter(row.mean * 100, yi, color=c, edgecolor=TEXT, lw=0.55, s=40 if row.method == "DNQ-DLC" else 26, zorder=3)
    ax.set_yticks(y, order)
    ax.set_xlim(0, 100)
    ax.set_xlabel("Overtaking success (%)", fontweight="normal")
    ax.set_title("Absolute primary endpoint", loc="left", fontsize=10)
    label(ax, "a")

    ax = fig.add_subplot(gs[0, 1])
    y = np.arange(len(pairs))[::-1]
    for yi, row in zip(y, pairs.itertuples()):
        lo, hi = row.paired_bootstrap_ci95_low * 100, row.paired_bootstrap_ci95_high * 100
        est = row.paired_difference * 100
        ax.plot([lo, hi], [yi, yi], color=GAIN, lw=2.1)
        ax.scatter(est, yi, color=GAIN, edgecolor=TEXT, lw=0.55, s=32, zorder=3)
    ax.axvline(0, color=MID, ls="--", lw=1.2)
    ax.set_yticks(y, pairs.comparator_label)
    ax.set_xlim(-5, 90)
    ax.set_xlabel("DNQ-DLC minus comparator (percentage points)", fontweight="normal")
    ax.set_title("Paired completion gain", loc="left", fontsize=10)
    label(ax, "b")

    ax = fig.add_subplot(gs[1, :])
    methods = ["DNQ-DLC", "Rule Expert", "DLC-JTO"]
    colors2 = {"DNQ-DLC": DNQ, "Rule Expert": RULE, "DLC-JTO": DLC}
    xlabels = ["N=4--6\ntraining range", "N=7--8\nvehicle-count extrapolation"]
    for method in methods:
        dat = strata[strata.algorithm_label == method].set_index("vehicle_count_stratum").loc[["N=4-6 training range", "N=7-8 extrapolation"]]
        x = np.arange(2) + {"DNQ-DLC": -0.13, "Rule Expert": 0, "DLC-JTO": 0.13}[method]
        mean = dat.success_rate.to_numpy() * 100
        low = dat.wilson_ci95_low.to_numpy() * 100
        high = dat.wilson_ci95_high.to_numpy() * 100
        ax.errorbar(x, mean, yerr=np.vstack([mean-low, high-mean]), marker="o", ms=5,
                    lw=1.8, capsize=3, color=colors2[method], label=method)
    ax.set_xticks(np.arange(2), xlabels)
    ax.set_ylim(0, 105)
    ax.set_ylabel("Overtaking success (%)", fontweight="normal")
    ax.set_title("Vehicle-count sensitivity", loc="left", fontsize=10)
    ax.legend(loc="upper center", ncol=3, bbox_to_anchor=(0.5, -0.22), fontsize=8)
    label(ax, "c")
    for a in fig.axes:
        a.tick_params(labelsize=8)
        a.grid(False)
    fig.subplots_adjust(left=0.19, right=0.98, top=0.94, bottom=0.18)
    TAB.mkdir(parents=True, exist_ok=True)
    pd.concat([frame.assign(panel="absolute_success"), pairs.assign(panel="paired_gain"), strata.assign(panel="vehicle_count")], ignore_index=True, sort=False).to_csv(TAB / "figure_e1_primary_completion_source.csv", index=False)
    return export(fig, FIG / "figure_e1_primary_completion")


def build_tradeoff():
    stats = pd.read_csv(source_paths()["stats"])
    rename = {"v6_runtime_dynamic_neighborhood_safe": "DNQ-DLC", "rule_expert_gate": "Rule Expert", "rule_safety_gate": "Safety Rule", "dlc_joint_transition_observer": "DLC-JTO"}
    colors = {"DNQ-DLC": DNQ, "Rule Expert": RULE, "Safety Rule": RULE_LIGHT, "DLC-JTO": DLC}
    comp = stats[stats.metric == "completion_time_capped"].copy(); grass = stats[stats.metric == "target_grass_rate"].copy()
    comp["method"] = comp.algorithm.map(rename); grass["method"] = grass.algorithm.map(rename)
    methods = ["DNQ-DLC", "Rule Expert", "Safety Rule", "DLC-JTO"]
    comp = comp.dropna(subset=["method"]).set_index("method").loc[methods]
    grass = grass.dropna(subset=["method"]).set_index("method").loc[methods]
    fig, ax = plt.subplots(figsize=(6.2, 3.85))
    for method in methods:
        x, y = comp.loc[method, "mean"], grass.loc[method, "mean"]
        ax.scatter(x, y, s=80 if method == "DNQ-DLC" else 54, color=colors[method], edgecolor=TEXT, lw=0.7, zorder=3, label=method)
        ax.annotate(method, (x, y), xytext=(6, 5), textcoords="offset points", fontsize=8)
    ax.set_xscale("log")
    ax.set_xlim(60, 2300); ax.set_ylim(0.15, 1.02)
    ax.set_xlabel("Completion time (steps; successful cases)", fontweight="normal")
    ax.set_ylabel("Target-grass exposure (successful cases)", fontweight="normal")
    ax.set_title("Completion and off-track exposure are separate outcomes", loc="left", fontsize=10)
    ax.text(0.02, 0.95, "success-conditioned summaries", transform=ax.transAxes, ha="left", va="top", fontsize=8, color=MID)
    ax.legend(loc="lower right", fontsize=8)
    ax.grid(False)
    label(ax, "a")
    fig.subplots_adjust(left=0.17, right=0.98, top=0.91, bottom=0.16)
    TAB.mkdir(parents=True, exist_ok=True)
    pd.concat([comp.reset_index().assign(panel="completion"), grass.reset_index().assign(panel="grass")], ignore_index=True, sort=False).to_csv(TAB / "figure_e2_completion_grass_tradeoff_source.csv", index=False)
    return export(fig, FIG / "figure_e2_completion_grass_tradeoff")


def build_ablation():
    report = json.loads(source_paths()["attr"].read_text(encoding="utf-8"))["paired_full_minus_ablation"]
    specs = [
        ("Dynamic selection", "dnq_w_o_dynamic_selection", "elegant_overtake_rate", 1),
        ("Quality proposal", "dnq_w_o_quality_proposal", "elegant_overtake_rate", 1),
        ("Risk + uncertainty", "dnq_w_o_risk_uncertainty", "elegant_overtake_rate", 1),
        ("Safety-quality terms", "dnq_w_o_safety_quality", "elegant_overtake_rate", 1),
        ("Quality proposal", "dnq_w_o_quality_proposal", "target_grass_rate", -1),
        ("Safety-quality terms", "dnq_w_o_safety_quality", "target_grass_rate", -1),
        ("Hard recovery", "dnq_w_o_hard_recovery", "elegant_overtake_rate", 1),
    ]
    rows = []
    for label_text, variant, metric, sign in specs:
        r = report[variant]["metrics"][metric]
        est = sign * r["full_minus_ablation_mean"]
        lo0, hi0 = r["ci95_bootstrap"]
        lo, hi = (sign * lo0, sign * hi0) if sign == 1 else (-hi0, -lo0)
        rows.append((f"{label_text}\n{'desirable rate' if metric == 'elegant_overtake_rate' else 'lower grass'}", est, lo, hi))
    fig, ax = plt.subplots(figsize=(6.8, 4.35))
    y = np.arange(len(rows))[::-1]
    for yi, (name, est, lo, hi) in zip(y, rows):
        color = DNQ if (lo > 0 or hi < 0) else MID
        ax.plot([lo, hi], [yi, yi], color=color, lw=2.0)
        ax.scatter(est, yi, s=38, color=color, edgecolor=TEXT, lw=0.6, zorder=3)
    ax.axvline(0, color=MID, ls="--", lw=1.2)
    ax.set_yticks(y, [r[0] for r in rows])
    ax.set_xlim(-0.28, 0.36)
    ax.set_xlabel("Effect favoring full controller (paired difference)", fontweight="normal")
    ax.set_title("Ablations affect maneuver quality more consistently than completion", loc="left", fontsize=10)
    ax.text(0.02, 0.02, "n=32 matched randomized cases; intervals are paired bootstrap 95% CIs", transform=ax.transAxes, fontsize=8, color=MID)
    ax.grid(False); label(ax, "a")
    fig.subplots_adjust(left=0.31, right=0.98, top=0.9, bottom=0.15)
    TAB.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows, columns=["effect", "estimate", "ci_low", "ci_high"]).to_csv(TAB / "figure_e4_ablation_forest_source.csv", index=False)
    return export(fig, FIG / "figure_e4_ablation_forest")


def build_mechanism():
    paths = source_paths()
    shots = [
        (101, "v6_runtime_dynamic_neighborhood_safe_n10_seed20000_01_approach_step101.png", "Approach", "A9 trails A4 by 1 tile"),
        (129, "v6_runtime_dynamic_neighborhood_safe_n10_seed20000_02_interaction_step129.png", "Side-by-side", "A9 reaches equal progress"),
        (157, "v6_runtime_dynamic_neighborhood_safe_n10_seed20000_03_completion_step157.png", "Pass complete", "A9 leads A4 by 2 tiles"),
    ]
    trace = json.loads(paths["trace"].read_text(encoding="utf-8"))
    trace_by_step = {int(r["step"]): r for r in trace}
    # The crop is shared across the three panels to preserve geometric scale.
    crop = (1100, 550, 1800, 1250)
    fig, axes = plt.subplots(1, 3, figsize=(7.18, 2.72), gridspec_kw={"wspace": 0.04})
    for i, (step, fname, title, note) in enumerate(shots):
        ax = axes[i]
        image = Image.open(paths["shots"] / fname).convert("RGB").crop(crop)
        ax.imshow(image, interpolation="none")
        ax.set_xticks([]); ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_visible(True); spine.set_color("#B5BBC0"); spine.set_linewidth(0.8)
        # The source trace and screenshot use the same coordinate transform in
        # the archived visual evidence pack. These fixed markers identify the
        # ego and the overtaken vehicle without changing the underlying frame.
        positions = np.asarray(trace_by_step[step]["positions"], dtype=float)
        # Convert trace coordinates to the 1800x1800 screenshot frame using the
        # fixed crop geometry used by the archived visual asset pack.
        track = np.load(ROOT / "tracks/oval_density_n10_scaled.npz")
        road = np.concatenate([track["left"], track["right"]], axis=0)
        lo = road.min(axis=0) - 30.0; hi = road.max(axis=0) + 30.0
        span = np.maximum(hi - lo, 1.0); scale = min(1799.0 / span[0], 1799.0 / span[1])
        centered_span = np.array([1800.0, 1800.0]) / scale; pad = (centered_span - span) / 2.0
        xy = (positions - (lo - pad)) * scale; xy[:, 1] = 1800.0 - xy[:, 1]
        p9, p4 = xy[9] - np.asarray(crop[:2]), xy[4] - np.asarray(crop[:2])
        for point, color in ((p9, DNQ), (p4, OPPONENT)):
            ax.add_patch(Circle(point, 31, fill=False, edgecolor="white", lw=3.2, zorder=5))
            ax.add_patch(Circle(point, 27, facecolor=color, alpha=0.20, edgecolor=color, lw=2.2, zorder=6))
        ax.annotate("A9  DNQ-DLC", xy=p9, xytext=(-52, 27), textcoords="offset points", fontsize=6.8,
                    color="white", bbox=dict(boxstyle="round,pad=0.22", fc=DNQ, ec="white", lw=0.6),
                    arrowprops=dict(arrowstyle="-|>", color="white", lw=1.0), zorder=8)
        ax.annotate("A4  opponent", xy=p4, xytext=(-54, -28), textcoords="offset points", fontsize=6.6,
                    color="white", bbox=dict(boxstyle="round,pad=0.22", fc=OPPONENT, ec="white", lw=0.6),
                    arrowprops=dict(arrowstyle="-|>", color="white", lw=1.0), zorder=8)
        ax.set_title(title, loc="left", fontsize=9, pad=3)
        ax.text(0.02, 0.025, f"step {step}\n{note}", transform=ax.transAxes, fontsize=6.6,
                color=TEXT, ha="left", va="bottom", bbox=dict(boxstyle="round,pad=0.22", fc="white", ec="#AAB1B6", lw=0.6, alpha=0.95))
        ids = trace_by_step[step].get("dynamic_neighbor_ids")
        if isinstance(ids, list) and ids and isinstance(ids[0], list):
            ids = ids[9]
        if ids:
            shown = ", ".join(f"A{int(v)}" for v in ids[:3])
            ax.text(0.98, 0.025, f"logged top-3 IDs: {shown}", transform=ax.transAxes,
                    fontsize=5.5, color=TEXT, ha="right", va="bottom",
                    bbox=dict(boxstyle="round,pad=0.20", fc="white", ec="#AAB1B6", lw=0.55, alpha=0.95))
    label(axes[0], "a")
    fig.subplots_adjust(left=0.02, right=0.99, top=0.82, bottom=0.09)
    return export(fig, FIG / "figure_e3_dynamic_neighborhood_snapshots")


def build_density():
    """Plot the archived density extension without adding or transforming cases."""
    src = ROOT / "outputs/tits_dynamic_graph_expanded/requested_experiments_20260902/archive/scale_extension/formal_scale_source_data.csv"
    dat = pd.read_csv(src)
    rename = {
        "v6_runtime_dynamic_neighborhood_safe": "DNQ-DLC",
        "dlc_joint_transition_observer": "DLC-JTO",
    }
    dat["method"] = dat.algorithm.map(rename)
    dat = dat.dropna(subset=["method"]).copy()
    counts = sorted(dat.num_agents.unique())
    summary = dat.groupby(["method", "num_agents"], as_index=False).agg(
        success=("overtake_success_rate", "mean"),
        on_track=("on_track_overtake_rate", "mean"),
    )
    out_source = TAB / "figure_e5_density_extension_source.csv"
    summary.to_csv(out_source, index=False)
    colors = {"DNQ-DLC": DNQ, "DLC-JTO": DLC}
    fig, axes = plt.subplots(1, 2, figsize=(6.6, 2.75), gridspec_kw={"wspace": 0.33})
    ax = axes[0]
    for method in ["DNQ-DLC", "DLC-JTO"]:
        q = summary[summary.method == method].sort_values("num_agents")
        ax.plot(q.num_agents, q.success * 100, marker="o", lw=2.0, ms=4.5,
                color=colors[method], label=method)
    ax.set_xlabel("Vehicles in scene, $N$")
    ax.set_ylabel("Completion (%)")
    ax.set_ylim(-2, 105)
    ax.set_xticks(counts)
    ax.set_title("Benchmark-defined completion", loc="left", fontsize=9.5)
    ax.legend(fontsize=7.5, loc="lower left")
    label(ax, "a")
    ax = axes[1]
    q = summary[summary.method == "DNQ-DLC"].sort_values("num_agents")
    # The archived aggregate explicitly marks N=4 containment as unavailable.
    # Exclude it rather than plotting a derived value.
    q = q[(q.num_agents != 4) & q.on_track.notna()]
    ax.plot(q.num_agents, q.on_track * 100, marker="o", lw=2.0, ms=4.5, color=DNQ)
    ax.set_xlabel("Vehicles in scene, $N$")
    ax.set_ylabel("On-track overtaking (%)")
    ax.set_ylim(-2, 105)
    ax.set_xticks(counts)
    ax.set_title("DNQ-DLC containment", loc="left", fontsize=9.5)
    ax.text(0.02, 0.04, "N=4 aggregate unavailable", transform=ax.transAxes,
            fontsize=7.2, color=MID, ha="left", va="bottom")
    label(ax, "b")
    for a in axes:
        a.grid(False)
        a.tick_params(labelsize=8)
    fig.subplots_adjust(left=0.12, right=0.98, top=0.88, bottom=0.20)
    return export(fig, FIG / "figure_e5_density_extension")


def copy_outputs(outputs):
    PAPER_FIG.mkdir(parents=True, exist_ok=True)
    for group in outputs.values():
        for path in group.values():
            src = Path(path)
            dst = PAPER_FIG / src.name
            shutil.copy2(src, dst)


def main():
    configure(); FIG.mkdir(parents=True, exist_ok=True); TAB.mkdir(parents=True, exist_ok=True)
    outputs = {"primary": build_primary(), "tradeoff": build_tradeoff(), "ablation": build_ablation(), "mechanism": build_mechanism(), "density": build_density()}
    report = {"status": "pass", "backend": "Python/matplotlib/Pillow", "outputs": outputs,
              "source_data": {k: str(v) for k, v in source_paths().items()},
              "color_map": {"DNQ-DLC": DNQ, "Rule Expert": RULE, "Safety Rule": RULE_LIGHT, "DLC-JTO": DLC, "ego_vehicle": DNQ, "overtaken_opponent": OPPONENT}}
    (OUT / "figure_build_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
