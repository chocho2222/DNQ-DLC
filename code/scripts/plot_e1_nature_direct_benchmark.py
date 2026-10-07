#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Create a direct-comparison E1 benchmark figure for manuscript use."""

import argparse
import csv
import math
from collections import defaultdict
from pathlib import Path

import numpy as np

try:
    from tits_figure_style import (
        ALGORITHM_COLORS as COLORS,
        ALGORITHM_LABELS as LABELS,
        ALGORITHM_ORDER,
        group_for_algorithm,
        configure_publication_matplotlib,
    )
except ImportError:
    from scripts.tits_figure_style import (
        ALGORITHM_COLORS as COLORS,
        ALGORITHM_LABELS as LABELS,
        ALGORITHM_ORDER,
        group_for_algorithm,
        configure_publication_matplotlib,
    )

GROUPS = {algorithm: group_for_algorithm(algorithm) for algorithm in ALGORITHM_ORDER}

PROBABILITY_METRICS = [
    ("overtake_success_rate", "Overtake\nsuccess"),
    ("on_track_overtake_rate", "On-track\novertake"),
    ("elegant_overtake_rate", "Desirable\novertaking behavior"),
]

PHYSICAL_METRICS = [
    ("completion_time_capped", "d  Completion time", "Steps"),
    ("target_grass_rate", "e  Off-track excursion", "Rate"),
    ("grass_recovery_time_capped", "f  Off-track recovery time", "Steps"),
]


def safe_float(value):
    if value is None:
        return None
    text = str(value).strip()
    if text == "":
        return None
    try:
        out = float(text)
    except (TypeError, ValueError):
        return None
    if math.isnan(out) or math.isinf(out):
        return None
    return out


def safe_int(value, default=0):
    out = safe_float(value)
    return default if out is None else int(round(out))


def bootstrap_ci(values, rng, n_boot=4000):
    arr = np.asarray([item for item in values if item is not None and np.isfinite(item)], dtype=np.float64)
    if arr.size == 0:
        return None, None, None
    mean = float(arr.mean())
    if arr.size == 1:
        return mean, mean, mean
    indices = rng.integers(0, arr.size, size=(n_boot, arr.size))
    boot = arr[indices].mean(axis=1)
    lo, hi = np.quantile(boot, [0.025, 0.975])
    return mean, float(lo), float(hi)


def wilson_ci(success_count, n, z=1.959963984540054):
    if n <= 0:
        return None, None, None
    p = success_count / n
    den = 1.0 + z * z / n
    center = (p + z * z / (2.0 * n)) / den
    half = z * math.sqrt((p * (1.0 - p) + z * z / (4.0 * n)) / n) / den
    return p, max(0.0, center - half), min(1.0, center + half)


def load_rows(path):
    with Path(path).open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def load_included_cases(trim_cases_path):
    included = set()
    with Path(trim_cases_path).open("r", newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if str(row.get("included", "")).strip() not in {"1", "True", "true"}:
                continue
            included.add((row["benchmark"], int(row["num_agents"]), str(row["seed"])))
    return included


def load_all_cases(rows):
    return {row_case_key(row) for row in rows if row.get("algorithm") in ALGORITHM_ORDER}


def row_case_key(row):
    return (row.get("_benchmark", row.get("benchmark", "")), int(row.get("num_agents", -1)), str(row.get("seed", "")))


def build_case_matrix(rows, included_cases):
    matrix = defaultdict(dict)
    for row in rows:
        algo = row.get("algorithm")
        if algo not in ALGORITHM_ORDER:
            continue
        key = row_case_key(row)
        if key not in included_cases:
            continue
        matrix[key][algo] = row
    return {
        key: values
        for key, values in matrix.items()
        if all(algo in values for algo in ALGORITHM_ORDER)
    }


def derived_value(row, metric):
    finish_step = safe_float(row.get("finish_step")) or 2200.0
    if metric == "completion_time_capped":
        value = safe_float(row.get("overtake_start_to_complete_time"))
        if value is None:
            return finish_step
        return min(max(value, 0.0), finish_step)
    if metric == "grass_recovery_time_capped":
        value = safe_float(row.get("grass_recovery_time_mean"))
        if value is not None:
            return min(max(value, 0.0), finish_step)
        if safe_int(row.get("grass_excursion_count"), 0) <= 0:
            return 0.0
        return finish_step
    value = safe_float(row.get(metric))
    return value


def successful_overtake(row):
    return (safe_float(row.get("overtake_success_rate")) or 0.0) > 0.0


def conditional_value(row, metric):
    if metric not in {item[0] for item in PHYSICAL_METRICS}:
        return derived_value(row, metric)
    if not successful_overtake(row):
        return None
    finish_step = safe_float(row.get("finish_step")) or 2200.0
    if metric == "completion_time_capped":
        value = safe_float(row.get("overtake_start_to_complete_time"))
        return None if value is None else min(max(value, 0.0), finish_step)
    if metric == "grass_recovery_time_capped":
        value = safe_float(row.get("grass_recovery_time_mean"))
        if value is not None:
            return min(max(value, 0.0), finish_step)
        if safe_int(row.get("grass_excursion_count"), 0) <= 0:
            return 0.0
        return finish_step
    return safe_float(row.get(metric))


def collect_values(matrix, metric):
    values = {algo: [] for algo in ALGORITHM_ORDER}
    for case_values in matrix.values():
        for algo in ALGORITHM_ORDER:
            value = conditional_value(case_values[algo], metric)
            if value is not None:
                values[algo].append(value)
    return values


def write_source_data(matrix, out_path):
    fields = [
        "benchmark",
        "num_agents",
        "seed",
        "algorithm",
        "algorithm_label",
        "algorithm_family",
        "metric",
        "value_raw",
        "value_display",
        "display_note",
        "successful_overtake_episode",
        "included_in_metric",
    ]
    metric_names = [item[0] for item in PROBABILITY_METRICS] + [item[0] for item in PHYSICAL_METRICS]
    rows = []
    for key, case_values in matrix.items():
        benchmark, num_agents, seed = key
        for algo in ALGORITHM_ORDER:
            for metric in metric_names:
                raw = derived_value(case_values[algo], metric)
                display = conditional_value(case_values[algo], metric)
                rows.append(
                    {
                        "benchmark": benchmark,
                        "num_agents": num_agents,
                        "seed": seed,
                        "algorithm": algo,
                        "algorithm_label": LABELS[algo],
                        "algorithm_family": GROUPS[algo],
                        "metric": metric,
                        "value_raw": raw,
                        "value_display": display,
                        "display_note": "probability metrics use all episodes; continuous metrics use successful overtaking episodes only",
                        "successful_overtake_episode": int(successful_overtake(case_values[algo])),
                        "included_in_metric": int(display is not None),
                    }
                )
    with Path(out_path).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_statistics(matrix, out_path, seed):
    rng = np.random.default_rng(seed)
    fields = [
        "metric",
        "algorithm",
        "algorithm_label",
        "algorithm_family",
        "n",
        "mean",
        "ci95_low",
        "ci95_high",
        "median",
        "q25",
        "q75",
    ]
    metric_names = [item[0] for item in PROBABILITY_METRICS] + [item[0] for item in PHYSICAL_METRICS]
    rows = []
    for metric in metric_names:
        values = collect_values(matrix, metric)
        for algo in ALGORITHM_ORDER:
            arr = np.asarray(values[algo], dtype=np.float64)
            if metric == "overtake_success_rate":
                bootstrap_ci(arr, rng)  # Preserve the fixed RNG stream used by the archived nonbinary intervals.
                mean, lo, hi = wilson_ci(int(np.count_nonzero(arr > 0.0)), int(arr.size))
            else:
                mean, lo, hi = bootstrap_ci(arr, rng)
            rows.append(
                {
                    "metric": metric,
                    "algorithm": algo,
                    "algorithm_label": LABELS[algo],
                    "algorithm_family": GROUPS[algo],
                    "n": int(arr.size),
                    "mean": mean,
                    "ci95_low": lo,
                    "ci95_high": hi,
                    "median": float(np.median(arr)) if arr.size else "",
                    "q25": float(np.quantile(arr, 0.25)) if arr.size else "",
                    "q75": float(np.quantile(arr, 0.75)) if arr.size else "",
                }
            )
    with Path(out_path).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def configure_matplotlib():
    configure_publication_matplotlib(font_size=7.0)


def add_family_spans(ax, y=-0.36):
    spans = [
        ("Rule", 0, 1),
        ("RL", 2, 4),
        ("DLC variants", 5, 7),
        ("Ours", 8, 8),
    ]
    trans = ax.get_xaxis_transform()
    for label, start, end in spans:
        ax.plot([start - 0.35, end + 0.35], [y, y], color="#9CA3AF", lw=0.60, transform=trans, clip_on=False)
        ax.text((start + end) / 2.0, y - 0.09, label, transform=trans, ha="center", va="top", fontsize=5.5, color="black")


def plot_figure(matrix, out_stem, seed):
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    configure_matplotlib()
    rng = np.random.default_rng(seed)
    fig = plt.figure(figsize=(7.6, 3.85), constrained_layout=False)
    gs = fig.add_gridspec(2, 3, height_ratios=[1.0, 1.16], hspace=0.50, wspace=0.28)
    prob_axes = [fig.add_subplot(gs[0, 0])]
    prob_axes.extend(fig.add_subplot(gs[0, idx], sharey=prob_axes[0]) for idx in range(1, 3))
    box_axes = [fig.add_subplot(gs[1, idx]) for idx in range(3)]

    x = np.arange(len(ALGORITHM_ORDER), dtype=np.float64)
    for panel_idx, (ax, (metric, label)) in enumerate(zip(prob_axes, PROBABILITY_METRICS)):
        means = []
        low_err = []
        high_err = []
        for algo in ALGORITHM_ORDER:
            vals = collect_values(matrix, metric)[algo]
            if metric == "overtake_success_rate":
                arr = np.asarray(vals, dtype=np.float64)
                bootstrap_ci(arr, rng)  # Preserve the fixed RNG stream used by the archived nonbinary intervals.
                mean, lo, hi = wilson_ci(int(np.count_nonzero(arr > 0.0)), int(arr.size))
            else:
                mean, lo, hi = bootstrap_ci(vals, rng)
            mean = 0.0 if mean is None else 100.0 * mean
            lo = mean if lo is None else 100.0 * lo
            hi = mean if hi is None else 100.0 * hi
            means.append(mean)
            low_err.append(max(mean - lo, 0.0))
            high_err.append(max(hi - mean, 0.0))
        edge_colors = ["#111827" if algo == "v6_runtime_dynamic_neighborhood_safe" else "#374151" for algo in ALGORITHM_ORDER]
        ax.bar(
            x,
            means,
            width=0.68,
            color=[COLORS[algo] for algo in ALGORITHM_ORDER],
            edgecolor=edge_colors,
            linewidth=[0.75 if algo == "v6_runtime_dynamic_neighborhood_safe" else 0.42 for algo in ALGORITHM_ORDER],
            alpha=0.86,
            zorder=3,
        )
        ax.errorbar(
            x,
            means,
            yerr=np.vstack([low_err, high_err]),
            fmt="none",
            ecolor="#111827",
            elinewidth=0.65,
            capsize=1.8,
            capthick=0.65,
            zorder=4,
        )
        letter = chr(ord("a") + panel_idx)
        ax.set_title(f"{letter}  {label.replace(chr(10), ' ')}", loc="left", fontsize=8.0, fontweight="bold")
        ax.set_ylim(0, 104)
        ax.set_xticks(x)
        ax.set_xticklabels([])
        ax.set_ylabel("Rate (%)")
        ax.grid(axis="y", color="#E5E7EB", lw=0.55)
        ax.set_axisbelow(True)

    legend_handles = [Patch(facecolor=COLORS[algo], edgecolor="#374151", label=LABELS[algo]) for algo in ALGORITHM_ORDER]
    fig.legend(
        handles=legend_handles,
        ncol=9,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.995),
        columnspacing=0.62,
        handlelength=0.88,
        handletextpad=0.26,
        fontsize=5.8,
    )

    positions = np.arange(len(ALGORITHM_ORDER), dtype=np.float64)
    for ax, (metric, title, ylabel) in zip(box_axes, PHYSICAL_METRICS):
        values = collect_values(matrix, metric)
        grouped = [np.asarray(values[algo], dtype=np.float64) for algo in ALGORITHM_ORDER]
        non_empty = [(pos, algo, vals) for pos, algo, vals in zip(positions, ALGORITHM_ORDER, grouped) if vals.size > 0]
        bp = ax.boxplot(
            [vals for _, _, vals in non_empty],
            positions=[pos for pos, _, _ in non_empty],
            widths=0.58,
            patch_artist=True,
            whis=1.5,
            showfliers=True,
            medianprops={"color": "#111827", "linewidth": 1.05},
            boxprops={"edgecolor": "#111827", "linewidth": 0.72},
            whiskerprops={"color": "#374151", "linewidth": 0.65},
            capprops={"color": "#374151", "linewidth": 0.65},
            flierprops={
                "marker": "o",
                "markersize": 2.2,
                "markerfacecolor": "#9CA3AF",
                "markeredgecolor": "#4B5563",
                "markeredgewidth": 0.25,
                "alpha": 0.50,
            },
        )
        for patch, (_, algo, _) in zip(bp["boxes"], non_empty):
            patch.set_facecolor(COLORS[algo])
            patch.set_alpha(0.88 if algo == "v6_runtime_dynamic_neighborhood_safe" else 0.58)
            if algo == "v6_runtime_dynamic_neighborhood_safe":
                patch.set_linewidth(1.05)
        all_values = np.concatenate([vals for _, _, vals in non_empty]) if non_empty else np.asarray([1.0])
        y_upper = float(np.max(all_values)) * 1.10 if np.max(all_values) > 0 else 1.0
        if metric == "target_grass_rate":
            y_upper = min(max(y_upper, 0.12), 1.05)
        ax.set_ylim(0.0, y_upper)
        for pos, algo, vals in zip(positions, ALGORITHM_ORDER, grouped):
            if vals.size == 0:
                ax.text(
                    pos,
                    y_upper * 0.06,
                    "N/A",
                    ha="center",
                    va="bottom",
                    fontsize=6.1,
                    color="black",
                    rotation=90,
                )
        if metric in {"completion_time_capped", "grass_recovery_time_capped"}:
            ax.set_yscale("symlog", linthresh=10.0, linscale=0.8)
        ax.set_title(title, loc="left", fontsize=8.0, fontweight="bold", y=1.12, pad=0)
        note_x = {
            "completion_time_capped": 0.50,
            "target_grass_rate": 0.48,
            "grass_recovery_time_capped": 0.65,
        }.get(metric, 0.45)
        ax.text(
            note_x,
            1.12,
            r"($\downarrow$ lower is better)",
            transform=ax.transAxes,
            ha="left",
            va="baseline",
            fontsize=6.0,
            fontstyle="italic",
            fontweight="normal",
            color="black",
        )
        ax.set_ylabel(ylabel)
        ax.set_xticks(positions)
        ax.set_xticklabels([LABELS[algo] for algo in ALGORITHM_ORDER], rotation=32, ha="right")
        for tick, algo in zip(ax.get_xticklabels(), ALGORITHM_ORDER):
            tick.set_color("black")
            tick.set_fontweight("bold" if algo == "v6_runtime_dynamic_neighborhood_safe" else "normal")
        ax.grid(axis="y", color="#E5E7EB", lw=0.55)
        ax.set_axisbelow(True)
        add_family_spans(ax)

    fig.subplots_adjust(left=0.072, right=0.995, top=0.895, bottom=0.270)
    outputs = {}
    for ext in ["svg", "pdf", "png", "tiff"]:
        path = Path(f"{out_stem}.{ext}")
        fig.savefig(path, dpi=600, bbox_inches="tight")
        outputs[ext] = str(path)
    plt.close(fig)
    return outputs


def main():
    parser = argparse.ArgumentParser(description="Plot the E1 direct benchmark in a manuscript-style layout.")
    parser.add_argument("--source-csv", default="outputs/tits_dynamic_graph_expanded/e1_200_summary/tables/online_benchmark_source_data.csv")
    parser.add_argument("--trim-cases", default="outputs/tits_dynamic_graph_expanded/e1_200_summary/tables/online_benchmark_direct_trimmed_cases.csv")
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph_expanded/e1_200_summary")
    parser.add_argument("--use-all-cases", action="store_true", help="Use all complete cases instead of the historical trimmed-case list.")
    parser.add_argument("--seed", type=int, default=2026)
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    figures_dir = out_dir / "figures"
    tables_dir = out_dir / "tables"
    figures_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)

    rows = load_rows(args.source_csv)
    included_cases = load_all_cases(rows) if args.use_all_cases else load_included_cases(args.trim_cases)
    matrix = build_case_matrix(rows, included_cases)
    if not matrix:
        raise SystemExit("No complete included cases found for the requested algorithms.")

    source_path = tables_dir / "online_benchmark_nature_direct_source_data.csv"
    stats_path = tables_dir / "online_benchmark_nature_direct_statistics.csv"
    write_source_data(matrix, source_path)
    write_statistics(matrix, stats_path, args.seed)
    figure_stem = figures_dir / "figure_e1_nature_direct_benchmark"
    figure_outputs = plot_figure(matrix, figure_stem, args.seed)

    print(
        {
            "n_cases": len(matrix),
            "figure": figure_outputs,
            "source_data": str(source_path),
            "statistics": str(stats_path),
        }
    )


if __name__ == "__main__":
    main()
