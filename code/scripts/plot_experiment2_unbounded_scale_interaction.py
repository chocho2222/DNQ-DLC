#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Plot the optimized Experiment 2 scale/co-track interaction figure."""

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch

try:
    from tits_figure_style import (
        ALGORITHM_ORDER,
        PROPOSED,
        color_for_algorithm,
        configure_publication_matplotlib,
        label_for_algorithm,
    )
except ImportError:
    from scripts.tits_figure_style import (
        ALGORITHM_ORDER,
        PROPOSED,
        color_for_algorithm,
        configure_publication_matplotlib,
        label_for_algorithm,
    )


def fnum(value):
    if value in (None, "", "nan", "NaN", "NA", "--"):
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(out) or math.isinf(out):
        return None
    return out


def bootstrap_ci(values, seed=2026, n_boot=3000):
    arr = np.asarray([v for v in values if v is not None and np.isfinite(v)], dtype=np.float64)
    if arr.size == 0:
        return None, None, None
    mean = float(arr.mean())
    if arr.size == 1:
        return mean, mean, mean
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, arr.size, size=(n_boot, arr.size))
    boot = arr[idx].mean(axis=1)
    lo, hi = np.quantile(boot, [0.025, 0.975])
    return mean, float(lo), float(hi)


def load_scale_rows(root):
    rows = []
    for path in sorted(Path(root).glob("runs/**/summaries/*.summary.json")):
        row = json.loads(path.read_text(encoding="utf-8"))
        row["_summary_file"] = str(path)
        row["experiment_id"] = "E3_scale_extension"
        row["algorithm_label"] = label_for_algorithm(row.get("algorithm", ""))
        rows.append(row)
    return rows


def load_interaction_rows(path):
    path = Path(path)
    if path.is_dir():
        candidates = [
            path / "tables" / "six_experiment_metric_summary.csv",
            path / "tables" / "co_track_agent_metrics.csv",
        ]
        path = next((item for item in candidates if item.exists()), None)
    if not path or not Path(path).exists():
        return []
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if rows and "metric" in rows[0] and "mean" in rows[0]:
        return []
    for row in rows:
        row["experiment_id"] = "E4_interaction_generalization"
        row["algorithm_label"] = label_for_algorithm(row.get("algorithm", ""))
    return rows


def algorithm_order(rows):
    present = {row.get("algorithm") for row in rows if row.get("algorithm")}
    return [item for item in ALGORITHM_ORDER if item in present]


def metric_value(row, metric, percent=False, conditional=False):
    if conditional and not bool(fnum(row.get("overtake_success_rate")) or 0.0):
        return None
    value = fnum(row.get(metric))
    if value is not None and percent:
        value *= 100.0
    return value


def line_panel(ax, rows, metric, algorithms, title, ylabel, percent=False, conditional=False):
    grouped = defaultdict(lambda: defaultdict(list))
    for row in rows:
        n = fnum(row.get("num_agents"))
        value = metric_value(row, metric, percent=percent, conditional=conditional)
        algo = row.get("algorithm")
        if algo not in algorithms or n is None or value is None:
            continue
        grouped[algo][int(n)].append(value)
    ax.axvspan(3.5, 6.5, color="#9CA3AF", alpha=0.12, zorder=0)
    ax.text(5.0, 0.965, "Training distribution", transform=ax.get_xaxis_transform(), ha="center", va="top", fontsize=5.8)
    ax.text(10.0, 0.965, "Zero-shot extrapolation", transform=ax.get_xaxis_transform(), ha="center", va="top", fontsize=5.8)
    for algo in algorithms:
        items = sorted(grouped.get(algo, {}).items())
        if not items:
            continue
        xs, means, lows, highs = [], [], [], []
        for n, values in items:
            mean, lo, hi = bootstrap_ci(values)
            xs.append(n)
            means.append(mean)
            lows.append(lo)
            highs.append(hi)
        xs = np.asarray(xs, dtype=float)
        means = np.asarray(means, dtype=float)
        lows = np.asarray(lows, dtype=float)
        highs = np.asarray(highs, dtype=float)
        ax.plot(xs, means, marker="o", lw=1.45, ms=3.5, color=color_for_algorithm(algo), label=label_for_algorithm(algo), zorder=3)
        ax.fill_between(xs, lows, highs, color=color_for_algorithm(algo), alpha=0.14, linewidth=0.0, zorder=2)
    ax.set_title(title, loc="left", fontsize=8.0, fontweight="bold")
    ax.set_xlabel("Number of vehicles")
    ax.set_ylabel(ylabel)
    if percent:
        ax.set_ylim(-4, 104)
    ax.set_xticks(sorted({int(fnum(row.get("num_agents"))) for row in rows if fnum(row.get("num_agents")) is not None}))
    ax.grid(axis="y", color="#E5E7EB", lw=0.55)
    ax.set_axisbelow(True)


def bar_panel(ax, rows, metric, algorithms, title, ylabel, percent=False, conditional=False):
    x = np.arange(len(algorithms))
    means, lows, highs, ns = [], [], [], []
    for algo in algorithms:
        vals = [metric_value(row, metric, percent=percent, conditional=conditional) for row in rows if row.get("algorithm") == algo]
        vals = [v for v in vals if v is not None]
        mean, lo, hi = bootstrap_ci(vals)
        means.append(0.0 if mean is None else mean)
        lows.append(0.0 if mean is None or lo is None else max(mean - lo, 0.0))
        highs.append(0.0 if mean is None or hi is None else max(hi - mean, 0.0))
        ns.append(len(vals))
    ax.bar(x, means, color=[color_for_algorithm(a) for a in algorithms], edgecolor="#111827", linewidth=0.5, alpha=0.88, zorder=3)
    ax.errorbar(x, means, yerr=np.asarray([lows, highs]), fmt="none", ecolor="#111827", elinewidth=0.65, capsize=2.0, zorder=4)
    for idx, n in enumerate(ns):
        if n == 0:
            ax.text(idx, 0.04, "N/A", ha="center", va="bottom", rotation=90, fontsize=6.0, transform=ax.get_xaxis_transform())
    ax.set_title(title, loc="left", fontsize=8.0, fontweight="bold")
    ax.set_ylabel(ylabel)
    if percent:
        ax.set_ylim(0, 104)
    ax.set_xticks(x)
    ax.set_xticklabels([label_for_algorithm(a) for a in algorithms], rotation=28, ha="right")
    for tick, algo in zip(ax.get_xticklabels(), algorithms):
        if algo == PROPOSED:
            tick.set_fontweight("bold")
    ax.grid(axis="y", color="#E5E7EB", lw=0.55)
    ax.set_axisbelow(True)


def write_source(rows, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row.keys() if not isinstance(row.get(key), (list, dict))})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows([{key: row.get(key, "") for key in fields} for row in rows])
    return str(path)


def main():
    parser = argparse.ArgumentParser(description="Plot optimized Experiment 2.")
    parser.add_argument("--scale-root", default="outputs/tits_dynamic_graph_expanded/experiment2_unbounded_scale_interaction/scale_runs")
    parser.add_argument("--interaction-source", default="outputs/tits_dynamic_graph_expanded/six_experiment_paper_results/tables/co_track_agent_metrics.csv")
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph_expanded/experiment2_unbounded_scale_interaction/summary")
    args = parser.parse_args()

    configure_publication_matplotlib(font_size=7.0)
    out_dir = Path(args.out_dir)
    fig_dir = out_dir / "figures"
    tab_dir = out_dir / "tables"
    fig_dir.mkdir(parents=True, exist_ok=True)
    tab_dir.mkdir(parents=True, exist_ok=True)

    scale_rows = load_scale_rows(args.scale_root)
    interaction_rows = load_interaction_rows(args.interaction_source)
    scale_algorithms = algorithm_order(scale_rows)
    interaction_algorithms = algorithm_order(interaction_rows)

    fig = plt.figure(figsize=(7.6, 3.75), constrained_layout=False)
    gs = fig.add_gridspec(2, 2, hspace=0.56, wspace=0.32)
    ax_a = fig.add_subplot(gs[0, 0])
    ax_b = fig.add_subplot(gs[0, 1])
    ax_c = fig.add_subplot(gs[1, 0])
    ax_d = fig.add_subplot(gs[1, 1])
    line_panel(ax_a, scale_rows, "overtake_success_rate", scale_algorithms, "a  Scale extrapolation: overtake success", "Rate (%)", percent=True)
    line_panel(ax_b, scale_rows, "on_track_overtake_rate", scale_algorithms, "b  Scale extrapolation: on-track overtaking", "Rate (%)", percent=True)
    if interaction_rows and interaction_algorithms:
        bar_panel(ax_c, interaction_rows, "overtake_success_rate", interaction_algorithms, "c  Multi-agent co-track interaction", "Rate (%)", percent=True)
        bar_panel(ax_d, interaction_rows, "target_grass_rate", interaction_algorithms, r"d  Grass excursion ($\downarrow$ lower is better)", "Rate", conditional=True)
        present_for_legend = set(scale_algorithms + interaction_algorithms)
        legend_algorithms = [item for item in ALGORITHM_ORDER if item in present_for_legend]
    else:
        bar_panel(ax_c, scale_rows, "elegant_overtake_rate", scale_algorithms, "c  Desirable overtaking behavior", "Rate (%)", percent=True)
        bar_panel(ax_d, scale_rows, "target_grass_rate", scale_algorithms, r"d  Grass excursion ($\downarrow$ lower is better)", "Rate", conditional=True)
        legend_algorithms = scale_algorithms
    handles = [Patch(facecolor=color_for_algorithm(a), edgecolor="#374151", label=label_for_algorithm(a)) for a in legend_algorithms]
    fig.legend(handles=handles, ncol=len(handles), loc="upper center", bbox_to_anchor=(0.5, 0.99), columnspacing=0.72, handlelength=0.88, handletextpad=0.26, fontsize=5.8)
    fig.subplots_adjust(left=0.078, right=0.995, top=0.865, bottom=0.185)
    stem = fig_dir / "figure_experiment2_unbounded_scale_interaction"
    outputs = {}
    for ext in ["svg", "pdf", "png", "tiff"]:
        path = stem.with_suffix(f".{ext}")
        fig.savefig(path, dpi=600, bbox_inches="tight")
        outputs[ext] = str(path)
    plt.close(fig)
    source = write_source(scale_rows + interaction_rows, tab_dir / "experiment2_unbounded_source_data.csv")
    caption = (
        "Optimized Experiment 2. Panels a and b show density-controlled scale extrapolation on the procedural track with 4, 6, 8, 10, and 12 vehicles "
        "(10 random seeds per vehicle count and algorithm). The shaded 4-6 vehicle region denotes the training distribution; 8-12 vehicles denote zero-shot extrapolation. "
        "Lines show means and bands show bootstrap 95% confidence intervals. Panels c and d summarize online multi-agent co-track interaction over 30 mixed-controller cases "
        "on procedural, Monza, and Monaco tracks; each bar is computed from the agent-level metrics recovered from the same online traces."
    )
    caption_path = out_dir / "figure_experiment2_unbounded_caption.tex"
    caption_path.write_text(caption + "\n", encoding="utf-8")
    manifest = {
        "scale_row_count": len(scale_rows),
        "interaction_row_count": len(interaction_rows),
        "scale_algorithms": scale_algorithms,
        "interaction_algorithms": interaction_algorithms,
        "figure": outputs,
        "source_data": source,
        "caption_tex": str(caption_path),
    }
    manifest_path = out_dir / "experiment2_unbounded_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
