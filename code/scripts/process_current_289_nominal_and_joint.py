#!/usr/bin/env python3
"""Recompute the legacy nominal endpoint on the frozen E1--E3 cohort.

The current cohort contains 289 episode records across E1 (164), E2 (75),
and E3 (50).  This script deliberately keeps the experiment-specific
denominators and also exports pooled descriptive statistics.  The joint plot
uses method-by-stratum means rather than episode-level binary outcomes so that
the marginal density is not an artefact of smoothing a Bernoulli variable.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import gaussian_kde, spearmanr


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "outputs/tits_dynamic_graph_expanded/current_paper_data_20260916"
ANALYSIS = DATA / "analysis"
FIGURES = ROOT / "paper_rewriting_output_tits_dynamic_graph_draft_20260625/tits_submission_final/figures"
SOURCE = DATA / "standard_summary_metrics.csv"

EXPERIMENTS = ["E1_basic_effectiveness", "E2_environment_generalization", "E3_scale_extension"]
LABELS = {
    "v6_runtime_dynamic_neighborhood_safe": "DRQ-DLC",
    "rule_expert_gate": "Rule Expert",
    "rule_safety_gate": "Safety Rule",
    "dlc_individual_transition": "DLC-IT",
    "dlc_joint_transition": "DLC-JT",
    "dlc_joint_transition_observer": "DLC-JTO",
    "ppo_continuous": "PPO",
    "sac_continuous": "SAC",
    "td3_continuous": "TD3",
}
COLORS = {
    # Muted palette shared with the endpoint, generalization, and ablation
    # figures.  The lightness ordering remains readable in grayscale.
    "DRQ-DLC": "#4C78A8",
    "Rule Expert": "#D08C55",
    "Safety Rule": "#9A9A9A",
    "DLC-IT": "#B58AA8",
    "DLC-JT": "#B36A55",
    "DLC-JTO": "#C5A36A",
    "PPO": "#77A6B6",
    "SAC": "#6D9B88",
    "TD3": "#9A9A6A",
}
PLOT_METHODS = {"DRQ-DLC", "Rule Expert", "DLC-JTO", "PPO", "SAC", "TD3"}


def wilson(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if n == 0:
        return float("nan"), float("nan")
    p = k / n
    den = 1.0 + z * z / n
    ctr = (p + z * z / (2.0 * n)) / den
    rad = z * math.sqrt(p * (1.0 - p) / n + z * z / (4.0 * n * n)) / den
    return max(0.0, ctr - rad), min(1.0, ctr + rad)


def load() -> pd.DataFrame:
    df = pd.read_csv(SOURCE)
    df = df[df["experiment_id"].isin(EXPERIMENTS)].copy()
    df["nominal_success"] = df["overtake_success"].astype(bool)
    # The archived summary endpoint and its event count must agree.
    mismatch = (df["nominal_success"] != (df["overtake_count"] > 0)).sum()
    if mismatch:
        raise RuntimeError(f"nominal/event-count mismatch in {mismatch} rows")
    df["method"] = df["algorithm"].map(LABELS).fillna(df["algorithm"])
    df["protocol"] = df["experiment_id"].map({
        "E1_basic_effectiveness": "E1",
        "E2_environment_generalization": "E2",
        "E3_scale_extension": "E3",
    })
    return df


def endpoint_table(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (experiment, algorithm), g in df.groupby(["experiment_id", "algorithm"], sort=True):
        n = len(g)
        k = int(g["nominal_success"].sum())
        lo, hi = wilson(k, n)
        rows.append({
            "experiment": g["protocol"].iloc[0],
            "experiment_id": experiment,
            "algorithm": algorithm,
            "method": g["method"].iloc[0],
            "n": n,
            "nominal_count": k,
            "nominal_rate": k / n,
            "ci95_low": lo,
            "ci95_high": hi,
            "mean_rank_gain": g["rank_gain"].mean(),
            "mean_overtake_count": g["overtake_count"].mean(),
            "mean_target_progress": g["target_progress"].mean(),
        })
    return pd.DataFrame(rows)


def pooled_table(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for algorithm, g in df.groupby("algorithm", sort=True):
        n = len(g)
        k = int(g["nominal_success"].sum())
        lo, hi = wilson(k, n)
        rows.append({
            "algorithm": algorithm,
            "method": g["method"].iloc[0],
            "n": n,
            "nominal_count": k,
            "nominal_rate": k / n,
            "ci95_low": lo,
            "ci95_high": hi,
            "mean_rank_gain": g["rank_gain"].mean(),
            "mean_overtake_count": g["overtake_count"].mean(),
            "mean_target_progress": g["target_progress"].mean(),
            "coverage_note": "pooled descriptive; method coverage is not identical across E1--E3",
        })
    return pd.DataFrame(rows)


def joint_table(df: pd.DataFrame) -> pd.DataFrame:
    # Each point is one method in one experiment/track/vehicle-count stratum.
    g = (df.groupby(["protocol", "experiment_id", "track_id", "num_agents", "algorithm", "method"], sort=True)
           .agg(n=("nominal_success", "size"),
                nominal_count=("nominal_success", "sum"),
                nominal_rate=("nominal_success", "mean"),
                mean_rank_gain=("rank_gain", "mean"),
                mean_target_progress=("target_progress", "mean"))
           .reset_index())
    g["stratum"] = g["protocol"] + " / " + g["track_id"].astype(str) + " / N=" + g["num_agents"].astype(str)
    return g


def _density(ax, values, orientation="x", color="#666666"):
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    if len(values) < 3 or np.ptp(values) <= 1e-12:
        return
    grid = np.linspace(values.min(), values.max(), 256)
    density = gaussian_kde(values)(grid)
    if orientation == "x":
        ax.plot(grid, density, color=color, lw=1.0)
        ax.fill_between(grid, density, 0, color=color, alpha=0.13)
    else:
        ax.plot(density, grid, color=color, lw=1.0)
        ax.fill_betweenx(grid, density, 0, color=color, alpha=0.13)


def make_joint(points: pd.DataFrame, outbase: Path) -> dict:
    points = points[points["method"].isin(PLOT_METHODS)].copy()
    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 7.0,
        "axes.linewidth": 0.65,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
    })
    # Compact joint-raincloud layout: the central scatter preserves the
    # two-metric relationship, while the top/right panels use the grouped
    # half-violin + box + jitter convention of the reference raincloud plot.
    fig = plt.figure(figsize=(6.85, 4.55))
    gs = fig.add_gridspec(2, 2, width_ratios=(5.0, 1.45), height_ratios=(1.45, 4.65),
                          left=0.105, right=0.965, bottom=0.145, top=0.955,
                          wspace=0.045, hspace=0.045)
    ax_top = fig.add_subplot(gs[0, 0])
    ax = fig.add_subplot(gs[1, 0], sharex=ax_top)
    ax_right = fig.add_subplot(gs[1, 1], sharey=ax)
    fig.add_subplot(gs[0, 1]).axis("off")

    order = [m for m in ["DRQ-DLC", "Rule Expert", "DLC-JTO", "PPO", "SAC", "TD3"]
             if m in set(points["method"])]
    for method in order:
        g = points[points["method"] == method]
        color = COLORS.get(method, "#333333")
        ax.scatter(g["mean_rank_gain"], g["nominal_rate"], s=22, alpha=0.68,
                   color=color, edgecolor="white", linewidth=0.35, label=method)
    # Label the proposed method and the principal DLC comparator without clutter.
    for method in ["DRQ-DLC", "DLC-JTO"]:
        g = points[points.method == method]
        if len(g):
            ax.scatter(g["mean_rank_gain"], g["nominal_rate"], s=34,
                       color=COLORS[method], edgecolor="black", linewidth=0.55, zorder=4)
            q = g.groupby(["method"], as_index=False)[["mean_rank_gain", "nominal_rate"]].mean().iloc[0]
            ax.annotate(method, (q.mean_rank_gain, q.nominal_rate), xytext=(5, 4),
                        textcoords="offset points", fontsize=7, color=COLORS[method])
    ax.set_xlabel("Mean rank gain (positions)")
    ax.set_ylabel("Nominal crossing rate")
    ax.set_ylim(-0.04, 1.04)
    ax.grid(False)
    ax.legend(loc="lower right", frameon=False, fontsize=6.2, ncol=2, handletextpad=0.25,
              columnspacing=0.8, borderaxespad=0.2)
    # Raincloud-style marginal summaries: KDE violins, compact boxplots, and
    # jittered stratum means. The central panel remains the joint comparison.
    y_pos = np.arange(len(order))
    for i, method in enumerate(order):
        vals_x = points.loc[points.method == method, "mean_rank_gain"].to_numpy()
        vals_y = points.loc[points.method == method, "nominal_rate"].to_numpy()
        color = COLORS.get(method, "#333333")
        if len(vals_x) > 1:
            vp = ax_top.violinplot(vals_x, positions=[i], vert=False, widths=0.78,
                                   showmeans=False, showmedians=False, showextrema=False)
            for body in vp["bodies"]:
                body.set_facecolor(color); body.set_edgecolor("none"); body.set_alpha(0.38)
                body.set_clip_path(plt.Rectangle((ax_top.get_xlim()[0], i),
                                                 ax_top.get_xlim()[1] - ax_top.get_xlim()[0], 0.42,
                                                 transform=ax_top.transData))
            ax_top.boxplot(vals_x, positions=[i], vert=False, widths=0.22,
                           patch_artist=True, showfliers=False,
                           boxprops={"facecolor": color, "alpha": 0.75, "edgecolor": "black", "linewidth": 0.45},
                           medianprops={"color": "black", "linewidth": 0.75},
                           whiskerprops={"color": "black", "linewidth": 0.45},
                           capprops={"color": "black", "linewidth": 0.45})
            jitter = i + np.linspace(-0.18, 0.18, len(vals_x))
            ax_top.scatter(vals_x, jitter, s=8, color=color, alpha=0.65, edgecolor="white", linewidth=0.2)
            vp = ax_right.violinplot(vals_y, positions=[i], vert=True, widths=0.78,
                                     showmeans=False, showmedians=False, showextrema=False)
            for body in vp["bodies"]:
                body.set_facecolor(color); body.set_edgecolor("none"); body.set_alpha(0.38)
                body.set_clip_path(plt.Rectangle((i, ax_right.get_ylim()[0]), 0.42,
                                                 ax_right.get_ylim()[1] - ax_right.get_ylim()[0],
                                                 transform=ax_right.transData))
            ax_right.boxplot(vals_y, positions=[i], vert=True, widths=0.22,
                             patch_artist=True, showfliers=False,
                             boxprops={"facecolor": color, "alpha": 0.75, "edgecolor": "black", "linewidth": 0.45},
                             medianprops={"color": "black", "linewidth": 0.75},
                             whiskerprops={"color": "black", "linewidth": 0.45},
                             capprops={"color": "black", "linewidth": 0.45})
            jitter_y = i + np.linspace(-0.18, 0.18, len(vals_y))
            ax_right.scatter(jitter_y, vals_y, s=8, color=color, alpha=0.65, edgecolor="white", linewidth=0.2)
    ax_top.set_yticks(y_pos, order, fontsize=6.2)
    ax_top.set_ylabel("Method", fontsize=6.8)
    ax_top.set_xlabel("")
    ax_top.tick_params(axis="x", labelbottom=False, length=0)
    ax_top.set_ylim(-0.65, len(order) - 0.35)
    ax_top.invert_yaxis()
    ax_top.spines["bottom"].set_visible(False)
    ax_top.grid(axis="x", color="#E2E2E2", linewidth=0.45)
    ax_top.set_axisbelow(True)
    ax_right.set_xticks(y_pos, order, rotation=60, ha="left", fontsize=6.0)
    ax_right.set_xlabel("Method", fontsize=6.8)
    ax_right.set_ylabel("Nominal crossing rate", fontsize=6.8, labelpad=12)
    ax_right.yaxis.set_label_position("right")
    ax_right.set_xlim(-0.65, len(order) - 0.35)
    ax_right.tick_params(axis="y", labelleft=False, length=0)
    ax_right.grid(axis="y", color="#E2E2E2", linewidth=0.45)
    ax_right.set_axisbelow(True)
    ax_right.spines["left"].set_visible(False)
    ax_top.text(0.50, 1.08, "Mean rank gain", transform=ax_top.transAxes,
                ha="center", va="bottom", fontsize=6.8)
    fig.savefig(outbase.with_suffix(".svg"), bbox_inches="tight")
    fig.savefig(outbase.with_suffix(".pdf"), bbox_inches="tight")
    fig.savefig(outbase.with_suffix(".tiff"), dpi=600, bbox_inches="tight")
    fig.savefig(outbase.with_suffix(".png"), dpi=300, bbox_inches="tight")
    plt.close(fig)
    rho, p = spearmanr(points["mean_rank_gain"], points["nominal_rate"])
    return {"n_points": int(len(points)), "spearman_rho": float(rho), "spearman_p": float(p)}


def write_report(df, endpoint, pooled, points, plot_stats):
    report = ANALYSIS / "current_289_nominal_report_20260918.md"
    lines = [
        "# Current 289-case nominal endpoint audit",
        "",
        "The legacy nominal endpoint is recomputed on the same frozen E1--E3 episodes used by the physical and strict audits. It is a crossing-based behavioral endpoint and does not require contact-free execution, on-track containment, sustained lead, or post-pass stability.",
        "",
        "## Coverage",
        "",
        f"- Unique episode cases: {df[['experiment_id', 'case_index']].drop_duplicates().shape[0]} (E1={df.loc[df.protocol == 'E1', ['experiment_id', 'case_index']].drop_duplicates().shape[0]}, E2={df.loc[df.protocol == 'E2', ['experiment_id', 'case_index']].drop_duplicates().shape[0]}, E3={df.loc[df.protocol == 'E3', ['experiment_id', 'case_index']].drop_duplicates().shape[0]}).",
        f"- Method rows: {df.groupby('algorithm').size().to_dict()}.",
        "- Pooled rates are descriptive because method coverage is not identical across all three protocols; experiment-specific rates are the primary comparison.",
        "",
        "## Endpoint interpretation",
        "",
        "Nominal completion is reported for legacy comparability and behavioral availability. Physical pass and strict completion remain the validity-oriented endpoints. The historical 200-case legacy ledger is kept separate and is not merged with this current 289-case cohort.",
        "",
        "## Joint plot",
        "",
        f"The joint plot contains {plot_stats['n_points']} method-by-stratum points. Spearman association between mean rank gain and nominal rate is rho={plot_stats['spearman_rho']:.3f} (p={plot_stats['spearman_p']:.3g}); this is descriptive and should not be presented as a causal relationship.",
        "",
        "Suggested manuscript wording: nominal completion captures whether the controller generated a benchmark-defined crossing event, whereas the physical and strict endpoints test whether that event was contact-free, on track, sustained, and stable. The same episode cohort is used for all endpoint layers.",
    ]
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    ANALYSIS.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    df = load()
    endpoint = endpoint_table(df)
    pooled = pooled_table(df)
    points = joint_table(df)
    endpoint.to_csv(ANALYSIS / "current_289_nominal_by_experiment_20260918.csv", index=False)
    pooled.to_csv(ANALYSIS / "current_289_nominal_pooled_20260918.csv", index=False)
    points.to_csv(ANALYSIS / "current_289_joint_rank_nominal_points_20260918.csv", index=False)
    df[["experiment_id", "case_index", "track_id", "algorithm", "method", "seed", "num_agents",
        "rank_gain", "overtake_count", "nominal_success", "target_progress"]].to_csv(
            ANALYSIS / "current_289_nominal_episode_level_20260918.csv", index=False)
    outbase = FIGURES / "figure_current_289_rank_nominal_joint"
    plot_stats = make_joint(points, outbase)
    write_report(df, endpoint, pooled, points, plot_stats)
    manifest = {
        "source": str(SOURCE),
        "experiments": EXPERIMENTS,
        "episode_rows": int(df[["experiment_id", "case_index"]].drop_duplicates().shape[0]),
        "method_rows": int(len(df)),
        "episode_counts": {k: int(v) for k, v in df.groupby("protocol")["case_index"].nunique().items()},
        "endpoint_definition": "summary overtake_success, verified equal to overtake_count > 0; legacy crossing-based nominal endpoint",
        "plot_definition": "method-by-stratum mean rank gain versus nominal overtake rate with marginal KDE",
        "plot_stats": plot_stats,
        "outputs": [
            "current_289_nominal_by_experiment_20260918.csv",
            "current_289_nominal_pooled_20260918.csv",
            "current_289_joint_rank_nominal_points_20260918.csv",
            "current_289_nominal_episode_level_20260918.csv",
            "current_289_nominal_report_20260918.md",
            "figure_current_289_rank_nominal_joint.svg",
            "figure_current_289_rank_nominal_joint.pdf",
            "figure_current_289_rank_nominal_joint.tiff",
            "figure_current_289_rank_nominal_joint.png",
        ],
    }
    (ANALYSIS / "current_289_nominal_manifest_20260918.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
