#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Export publication-style figures for the six T-ITS overtaking experiments."""

import argparse
import csv
import json
import math
from collections import defaultdict
from types import SimpleNamespace
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch

try:
    from run_tits_dynamic_graph_evaluation import summarize_trace
except ImportError:
    from scripts.run_tits_dynamic_graph_evaluation import summarize_trace

try:
    from tits_figure_style import (
        ABLATION_ORDER,
        ALGORITHM_ORDER,
        ALGORITHM_COLORS,
        VEHICLE_COLORS_HEX,
        PROPOSED,
        PROPOSED_E6,
        color_for_algorithm,
        configure_publication_matplotlib,
        label_for_algorithm,
        sorted_algorithms,
    )
except ImportError:
    from scripts.tits_figure_style import (
        ABLATION_ORDER,
        ALGORITHM_ORDER,
        ALGORITHM_COLORS,
        VEHICLE_COLORS_HEX,
        PROPOSED,
        PROPOSED_E6,
        color_for_algorithm,
        configure_publication_matplotlib,
        label_for_algorithm,
        sorted_algorithms,
    )


PROBABILITY_METRICS = [
    ("overtake_success_rate", "Overtake success"),
    ("on_track_overtake_rate", "On-track overtake"),
    ("elegant_overtake_rate", "Desirable overtaking behavior"),
]

CONTINUOUS_METRICS = [
    ("overtake_start_to_complete_time", "Completion time", "Steps"),
    ("target_grass_rate", "Off-track excursion", "Rate"),
    ("grass_recovery_time_mean", "Off-track recovery time", "Steps"),
]

SUMMARY_METRICS = [
    *PROBABILITY_METRICS,
    ("rank_gain", "Rank gain"),
    *[(m, t) for m, t, _ in CONTINUOUS_METRICS],
    ("collision_or_contact_proxy", "Contact proxy"),
    ("compute_latency_ms", "Decision latency"),
]


def read_csv(path):
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path, rows, fields):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return str(path)


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return str(path)


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


def successful_overtake(row):
    value = fnum(row.get("overtake_success_rate"))
    if value is not None:
        return value > 0.0
    return str(row.get("overtake_success", "")).lower() == "true"


def metric_value(row, metric, conditional=False):
    if conditional and metric in {item[0] for item in CONTINUOUS_METRICS} and not successful_overtake(row):
        return None
    value = fnum(row.get(metric))
    if value is None and metric == "overtake_success_rate":
        value = 1.0 if str(row.get("overtake_success", "")).lower() == "true" else 0.0
    return value


def bootstrap_ci(values, rng, n_boot=3000):
    arr = np.asarray([v for v in values if v is not None and np.isfinite(v)], dtype=np.float64)
    if arr.size == 0:
        return None, None, None
    mean = float(arr.mean())
    if arr.size == 1:
        return mean, mean, mean
    idx = rng.integers(0, arr.size, size=(n_boot, arr.size))
    boot = arr[idx].mean(axis=1)
    lo, hi = np.quantile(boot, [0.025, 0.975])
    return mean, float(lo), float(hi)


def load_expanded(source_csv):
    rows = read_csv(source_csv)
    for row in rows:
        row["experiment_id"] = row.get("_benchmark") or row.get("experiment_id", "")
        row["algorithm_label"] = label_for_algorithm(row.get("algorithm", ""))
    return rows


def load_mixed(mixed_root):
    rows = []
    for summary_path in sorted(Path(mixed_root).glob("runs/**/summaries/*.summary.json")):
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        trace_path = Path(summary.get("trace_path") or "")
        if not trace_path.is_absolute():
            trace_path = Path.cwd() / trace_path
        if not trace_path.exists():
            fallback = summary_path.parents[1] / "traces" / summary_path.name.replace(".summary.json", ".trace.json")
            trace_path = fallback if fallback.exists() else trace_path
        if not trace_path.exists():
            continue
        trace = json.loads(trace_path.read_text(encoding="utf-8"))
        assignment = summary.get("assignment") or (trace[0].get("assignment") if trace else [])
        if not assignment:
            continue
        args = SimpleNamespace(
            seed=int(summary.get("seed", 0)),
            num_agents=int(summary.get("num_agents", len(assignment))),
            track_path="" if summary.get("track_path") in ("", "procedural", None) else summary.get("track_path"),
            traffic_profile=summary.get("traffic_profile", "mixed_traffic"),
            observation_type=summary.get("observation_type", "telemetry_dynamic"),
            contact_distance=2.0,
        )
        total_reward = summary.get("total_reward") or [0.0] * args.num_agents
        first_complete_step = summary.get("first_complete_step") or [None] * args.num_agents
        steps_run = int(summary.get("steps_run") or summary.get("finish_step") or (trace[-1]["step"] if trace else 0))
        for agent_id, algorithm_name in enumerate(assignment):
            record = summarize_trace(
                trace=trace,
                args=args,
                algorithm={"name": algorithm_name, "label_cn": label_for_algorithm(algorithm_name), "policy": f"mixed_assignment:{algorithm_name}"},
                target_agent=agent_id,
                track_tiles=int(summary.get("track_tiles") or 0),
                total_reward=total_reward,
                steps_run=steps_run,
                first_complete_step=first_complete_step,
                gif_paths={},
                render_error=None,
            )
            record["experiment_id"] = "E4_interaction_generalization"
            record["_benchmark"] = "E4_interaction_generalization"
            record["_source_summary"] = str(summary_path)
            record["_source_trace"] = str(trace_path)
            record["co_track_agent_id"] = int(agent_id)
            record["co_track_assignment"] = ",".join(assignment)
            record["algorithm_label"] = label_for_algorithm(record.get("algorithm", ""))
            rows.append(record)
    if rows:
        return rows
    for path in sorted(Path(mixed_root).glob("runs/**/tables/mixed_metrics_*.csv")):
        for row in read_csv(path):
            row["experiment_id"] = "E4_interaction_generalization"
            row["_benchmark"] = "E4_interaction_generalization"
            row["_source_csv"] = str(path)
            row["algorithm"] = row.get("algorithm", "").replace("mixed_target_", "")
            if "overtake_success_rate" not in row:
                row["overtake_success_rate"] = "1.0" if str(row.get("overtake_success", "")).lower() == "true" else "0.0"
            row["algorithm_label"] = label_for_algorithm(row.get("algorithm", ""))
            rows.append(row)
    return rows


def algorithms_present(rows, preferred_order=ALGORITHM_ORDER):
    present = {row.get("algorithm") for row in rows}
    ordered = [name for name in preferred_order if name in present]
    extras = sorted_algorithms([name for name in present if name and name not in ordered])
    return ordered + extras


def save_multi(fig, stem):
    outputs = {}
    for ext in ["svg", "pdf", "png", "tiff"]:
        path = stem.with_suffix(f".{ext}")
        fig.savefig(path, dpi=600, bbox_inches="tight")
        outputs[ext] = str(path)
    plt.close(fig)
    return outputs


def add_family_spans(ax, algorithms, y=-0.34):
    families = [
        ("Rule-based", {"rule_expert_gate", "rule_safety_gate"}),
        ("RL", {"ppo_continuous", "sac_continuous", "td3_continuous"}),
        ("DLC variants", {"dlc_individual_transition", "dlc_joint_transition", "dlc_joint_transition_observer"}),
        ("Ours", {PROPOSED, PROPOSED_E6, "mixed_target_v6_runtime_dynamic_neighborhood_safe"}),
    ]
    trans = ax.get_xaxis_transform()
    for label, names in families:
        idx = [i for i, algo in enumerate(algorithms) if algo in names]
        if not idx:
            continue
        start, end = min(idx), max(idx)
        ax.plot([start - 0.35, end + 0.35], [y, y], color="#9CA3AF", lw=0.60, transform=trans, clip_on=False)
        ax.text((start + end) / 2.0, y - 0.09, label, transform=trans, ha="center", va="top", fontsize=5.5, color="black")


def style_axis(ax, grid_axis="y"):
    ax.grid(axis=grid_axis, color="#E5E7EB", lw=0.55)
    ax.set_axisbelow(True)
    ax.tick_params(colors="black")
    for spine in ax.spines.values():
        spine.set_color("black")


def title_with_optional_low_note(ax, title):
    note = r"($\downarrow$ lower is better)"
    if "lower is better" not in title:
        ax.set_title(title, loc="left", fontsize=8.0, fontweight="bold")
        return
    base = title.split("(")[0].rstrip()
    ax.set_title(base, loc="left", fontsize=8.0, fontweight="bold")
    ax.text(
        0.44,
        1.02,
        note,
        transform=ax.transAxes,
        ha="left",
        va="baseline",
        fontsize=6.0,
        fontstyle="italic",
        fontweight="normal",
        color="black",
    )


def bar_probability_panel(ax, rows, metric, algorithms, title, rng):
    x = np.arange(len(algorithms), dtype=float)
    means, lows, highs = [], [], []
    for algo in algorithms:
        vals = [metric_value(row, metric) for row in rows if row.get("algorithm") == algo]
        mean, lo, hi = bootstrap_ci(vals, rng)
        mean = 0.0 if mean is None else 100.0 * mean
        lo = mean if lo is None else 100.0 * lo
        hi = mean if hi is None else 100.0 * hi
        means.append(mean)
        lows.append(max(mean - lo, 0.0))
        highs.append(max(hi - mean, 0.0))
    ax.bar(
        x,
        means,
        width=0.68,
        color=[color_for_algorithm(algo) for algo in algorithms],
        edgecolor=["#111827" if algo in {PROPOSED, PROPOSED_E6} else "#374151" for algo in algorithms],
        linewidth=[0.80 if algo in {PROPOSED, PROPOSED_E6} else 0.42 for algo in algorithms],
        alpha=0.88,
        zorder=3,
    )
    ax.errorbar(x, means, yerr=np.asarray([lows, highs]), fmt="none", ecolor="#111827", elinewidth=0.65, capsize=1.8, capthick=0.65, zorder=4)
    title_with_optional_low_note(ax, title)
    ax.set_ylim(0, 104)
    ax.set_ylabel("Rate (%)")
    ax.set_xticks(x)
    ax.set_xticklabels([])
    style_axis(ax)


def box_continuous_panel(ax, rows, metric, algorithms, title, ylabel, conditional=True, symlog=False):
    positions = np.arange(len(algorithms), dtype=float)
    grouped = []
    for algo in algorithms:
        vals = [metric_value(row, metric, conditional=conditional) for row in rows if row.get("algorithm") == algo]
        grouped.append(np.asarray([v for v in vals if v is not None], dtype=np.float64))
    non_empty = [(pos, algo, vals) for pos, algo, vals in zip(positions, algorithms, grouped) if vals.size > 0]
    if non_empty:
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
            flierprops={"marker": "o", "markersize": 2.0, "markerfacecolor": "#9CA3AF", "markeredgecolor": "#4B5563", "markeredgewidth": 0.25, "alpha": 0.50},
        )
        for patch, (_, algo, _) in zip(bp["boxes"], non_empty):
            patch.set_facecolor(color_for_algorithm(algo))
            patch.set_alpha(0.88 if algo in {PROPOSED, PROPOSED_E6} else 0.58)
            if algo in {PROPOSED, PROPOSED_E6}:
                patch.set_linewidth(1.05)
        all_values = np.concatenate([vals for _, _, vals in non_empty])
        y_upper = float(np.max(all_values)) * 1.10 if np.max(all_values) > 0 else 1.0
    else:
        y_upper = 1.0
    if metric == "target_grass_rate":
        y_upper = min(max(y_upper, 0.12), 1.05)
    ax.set_ylim(0.0, y_upper)
    if symlog:
        ax.set_yscale("symlog", linthresh=10.0, linscale=0.8)
    for pos, vals in zip(positions, grouped):
        if vals.size == 0:
            ax.text(pos, y_upper * 0.06, "N/A", ha="center", va="bottom", fontsize=6.1, color="black", rotation=90)
    title_with_optional_low_note(ax, title + r" ($\downarrow$ lower is better)")
    ax.set_ylabel(ylabel)
    ax.set_xticks(positions)
    ax.set_xticklabels([label_for_algorithm(algo) for algo in algorithms], rotation=32, ha="right")
    for tick, algo in zip(ax.get_xticklabels(), algorithms):
        tick.set_fontweight("bold" if algo in {PROPOSED, PROPOSED_E6} else "normal")
        tick.set_color("black")
    style_axis(ax)
    add_family_spans(ax, algorithms)


def legend_for_algorithms(fig, algorithms, y=0.99):
    handles = [Patch(facecolor=color_for_algorithm(algo), edgecolor="#374151", label=label_for_algorithm(algo)) for algo in algorithms]
    ncol = min(len(handles), 9)
    fig.legend(handles=handles, ncol=ncol, loc="upper center", bbox_to_anchor=(0.5, y), columnspacing=0.70, handlelength=0.88, handletextpad=0.26, fontsize=5.8)


def figure_direct_distribution(rows, algorithms, stem, prefix):
    rng = np.random.default_rng(2026)
    fig = plt.figure(figsize=(7.6, 3.85), constrained_layout=False)
    gs = fig.add_gridspec(2, 3, height_ratios=[1.0, 1.16], hspace=0.50, wspace=0.28)
    top_axes = [fig.add_subplot(gs[0, 0])]
    top_axes.extend(fig.add_subplot(gs[0, idx], sharey=top_axes[0]) for idx in range(1, 3))
    bottom_axes = [fig.add_subplot(gs[1, idx]) for idx in range(3)]
    for idx, (ax, (metric, label)) in enumerate(zip(top_axes, PROBABILITY_METRICS)):
        bar_probability_panel(ax, rows, metric, algorithms, f"{chr(ord('a') + idx)}  {label}", rng)
    for offset, (ax, (metric, label, ylabel)) in enumerate(zip(bottom_axes, CONTINUOUS_METRICS), start=3):
        box_continuous_panel(ax, rows, metric, algorithms, f"{chr(ord('a') + offset)}  {label}", ylabel, conditional=True, symlog=metric != "target_grass_rate")
    legend_for_algorithms(fig, algorithms, y=0.995)
    fig.subplots_adjust(left=0.072, right=0.995, top=0.895, bottom=0.270)
    return save_multi(fig, stem), caption_direct(prefix)


def caption_direct(prefix):
    return (
        f"{prefix}. Panels a-c report all evaluated episodes. Bars show means and bootstrap 95\\% confidence intervals. "
        "Panels d-f report conditional distributions over successful overtaking episodes only; algorithms without successful episodes are marked as N/A."
    )


def line_metric_panel(ax, rows, metric, algorithms, title, ylabel, percent=False, conditional=False):
    grouped = defaultdict(lambda: defaultdict(list))
    for row in rows:
        algo = row.get("algorithm")
        if algo not in algorithms:
            continue
        n = fnum(row.get("num_agents"))
        value = metric_value(row, metric, conditional=conditional)
        if n is None or value is None:
            continue
        grouped[algo][int(n)].append(value * 100.0 if percent else value)
    for algo in algorithms:
        items = sorted((n, vals) for n, vals in grouped.get(algo, {}).items())
        if not items:
            continue
        xs = np.asarray([n for n, _ in items], dtype=float)
        ys, lows, highs = [], [], []
        rng = np.random.default_rng(2026)
        for _, vals in items:
            mean, lo, hi = bootstrap_ci(vals, rng)
            ys.append(mean if mean is not None else np.nan)
            lows.append(lo if lo is not None else np.nan)
            highs.append(hi if hi is not None else np.nan)
        ys = np.asarray(ys, dtype=float)
        lows = np.asarray(lows, dtype=float)
        highs = np.asarray(highs, dtype=float)
        ax.plot(xs, ys, marker="o", lw=1.35, ms=3.2, color=color_for_algorithm(algo), label=label_for_algorithm(algo), alpha=0.92)
        ax.fill_between(xs, lows, highs, color=color_for_algorithm(algo), alpha=0.12, linewidth=0.0)
    ax.axvspan(3.5, 6.5, color="#9CA3AF", alpha=0.11, zorder=0)
    ax.text(5.0, 0.965, "Training distribution", transform=ax.get_xaxis_transform(), ha="center", va="top", fontsize=5.8, color="black")
    ax.text(10.0, 0.965, "Zero-shot extrapolation", transform=ax.get_xaxis_transform(), ha="center", va="top", fontsize=5.8, color="black")
    title_with_optional_low_note(ax, title)
    ax.set_xlabel("Number of vehicles")
    ax.set_ylabel(ylabel)
    ax.set_xticks(sorted({int(fnum(row.get("num_agents"))) for row in rows if fnum(row.get("num_agents")) is not None}))
    if percent:
        ax.set_ylim(-4, 104)
    style_axis(ax)


def make_e3_figure(rows, algorithms, stem):
    fig = plt.figure(figsize=(7.6, 3.95), constrained_layout=False)
    gs = fig.add_gridspec(2, 3, hspace=0.50, wspace=0.34)
    axes = [fig.add_subplot(gs[i, j]) for i in range(2) for j in range(3)]
    panels = [
        ("overtake_success_rate", "a  Overtake success", "Rate (%)", True, False),
        ("on_track_overtake_rate", "b  On-track overtake", "Rate (%)", True, False),
        ("elegant_overtake_rate", "c  Desirable overtaking behavior", "Rate (%)", True, False),
        ("overtake_start_to_complete_time", r"d  Completion time ($\downarrow$ lower is better)", "Steps", False, True),
        ("target_grass_rate", r"e  Off-track excursion ($\downarrow$ lower is better)", "Rate", False, True),
        ("compute_latency_ms", r"f  Decision latency ($\downarrow$ lower is better)", "ms", False, False),
    ]
    for ax, (metric, title, ylabel, percent, conditional) in zip(axes, panels):
        line_metric_panel(ax, rows, metric, algorithms, title, ylabel, percent=percent, conditional=conditional)
    legend_for_algorithms(fig, algorithms, y=0.995)
    fig.subplots_adjust(left=0.072, right=0.995, top=0.895, bottom=0.125)
    caption = (
        "Scale-extension experiment over 4, 6, 8, 10 and 12 vehicles. Points show case-level means for each vehicle count; "
        "continuous overtaking-time and off-track-excursion metrics are calculated over successful overtaking episodes."
    )
    return save_multi(fig, stem), caption


def grouped_by_track_panel(ax, rows, metric, title, ylabel, percent=False, conditional=False):
    by_track = defaultdict(list)
    for row in rows:
        track = row.get("track_path") or "procedural"
        label = Path(track).stem.replace("_scaled", "").replace("_", " ").title() if track != "procedural" else "Procedural"
        value = metric_value(row, metric, conditional=conditional)
        if value is not None:
            by_track[label].append(value * 100.0 if percent else value)
    labels = sorted(by_track)
    values = [float(np.mean(by_track[label])) for label in labels]
    errors = []
    rng = np.random.default_rng(2026)
    for label in labels:
        mean, lo, hi = bootstrap_ci(by_track[label], rng)
        errors.append((0.0 if mean is None or lo is None else max(mean - lo, 0.0), 0.0 if mean is None or hi is None else max(hi - mean, 0.0)))
    x = np.arange(len(labels))
    ax.bar(x, values, width=0.64, color=color_for_algorithm("mixed_target_v6_runtime_dynamic_neighborhood_safe"), edgecolor="#111827", linewidth=0.65, alpha=0.88, zorder=3)
    if errors:
        ax.errorbar(x, values, yerr=np.asarray(errors).T, fmt="none", ecolor="#111827", elinewidth=0.65, capsize=2, zorder=4)
    title_with_optional_low_note(ax, title)
    ax.set_ylabel(ylabel)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=25, ha="right")
    style_axis(ax)


def make_e4_figure(rows, stem):
    algorithms = algorithms_present(rows, ALGORITHM_ORDER)
    outputs, caption = figure_direct_distribution(
        rows,
        algorithms,
        stem,
        "Multi-agent co-track interaction experiment with all controllers evaluated from the same mixed-controller traces",
    )
    return outputs, caption


def metric_table(all_rows, out_dir, rng):
    rows = []
    experiments = sorted({row.get("experiment_id") for row in all_rows if row.get("experiment_id")})
    for exp_id in experiments:
        subset = [row for row in all_rows if row.get("experiment_id") == exp_id]
        preferred = ABLATION_ORDER if exp_id == "E6_ablation" else ALGORITHM_ORDER
        for algo in algorithms_present(subset, preferred):
            algo_rows = [row for row in subset if row.get("algorithm") == algo]
            for metric, label in SUMMARY_METRICS:
                conditional = metric in {item[0] for item in CONTINUOUS_METRICS}
                vals = [metric_value(row, metric, conditional=conditional) for row in algo_rows]
                vals = [v for v in vals if v is not None]
                mean, lo, hi = bootstrap_ci(vals, rng)
                arr = np.asarray(vals, dtype=np.float64)
                rows.append(
                    {
                        "experiment_id": exp_id,
                        "algorithm": algo,
                        "algorithm_label": label_for_algorithm(algo),
                        "metric": metric,
                        "metric_label": label,
                        "n": int(arr.size),
                        "mean": mean,
                        "ci95_low": lo,
                        "ci95_high": hi,
                        "median": float(np.median(arr)) if arr.size else "",
                        "q25": float(np.quantile(arr, 0.25)) if arr.size else "",
                        "q75": float(np.quantile(arr, 0.75)) if arr.size else "",
                        "continuous_metrics_conditioned_on_success": int(conditional),
                    }
                )
    fields = [
        "experiment_id",
        "algorithm",
        "algorithm_label",
        "metric",
        "metric_label",
        "n",
        "mean",
        "ci95_low",
        "ci95_high",
        "median",
        "q25",
        "q75",
        "continuous_metrics_conditioned_on_success",
    ]
    return write_csv(Path(out_dir) / "tables" / "six_experiment_metric_summary.csv", rows, fields), rows


def select_mechanism_cases(expanded, out_dir):
    by_case_algo = {}
    for row in expanded:
        by_case_algo[(row.get("experiment_id"), row.get("num_agents"), row.get("seed"), row.get("track_path"), row.get("algorithm"))] = row
    cases = []
    for row in expanded:
        if row.get("algorithm") == PROPOSED and fnum(row.get("elegant_overtake_rate")) == 1.0:
            base = by_case_algo.get((row.get("experiment_id"), row.get("num_agents"), row.get("seed"), row.get("track_path"), "dlc_joint_transition_observer"))
            if base and (fnum(base.get("overtake_success_rate")) or 0.0) <= 0.0:
                cases.append(case_record("dlc_fail_ours_success", "Original DLC fails, whereas the proposed method completes desirable overtaking behavior.", row, base))
                break
    for row in expanded:
        if row.get("algorithm") == PROPOSED and fnum(row.get("elegant_overtake_rate")) == 1.0:
            base = by_case_algo.get((row.get("experiment_id"), row.get("num_agents"), row.get("seed"), row.get("track_path"), "dlc_joint_transition_observer"))
            if base and (fnum(base.get("overtake_success_rate")) or 0.0) > 0 and (fnum(base.get("elegant_overtake_rate")) or 0.0) < 1.0:
                cases.append(case_record("dlc_non_desirable_ours_desirable", "Original DLC overtakes but violates desirable-behavior criteria; the proposed method passes the criteria.", row, base))
                break
    failures = [r for r in expanded if r.get("algorithm") == PROPOSED and (fnum(r.get("overtake_success_rate")) or 0.0) <= 0.0]
    failures.sort(key=lambda r: (-(fnum(r.get("target_grass_rate")) or 0.0), -(fnum(r.get("collision_or_contact_proxy")) or 0.0)))
    if failures:
        cases.append(case_record("ours_residual_failure", "Residual failure of the proposed method.", failures[0], None))
    high_vehicle = [r for r in expanded if r.get("algorithm") == PROPOSED and int(float(r.get("num_agents", 0))) >= 8]
    high_vehicle.sort(key=lambda r: (-(fnum(r.get("rank_gain")) or 0.0), fnum(r.get("target_grass_rate")) or 0.0))
    if high_vehicle:
        cases.append(case_record("dynamic_neighborhood_replay", "Dynamic neighborhood construction in a high-vehicle-count episode.", high_vehicle[0], None))
    safety = [r for r in expanded if r.get("algorithm") == PROPOSED and (fnum(r.get("target_grass_rate")) or 0.0) > 0.0]
    safety.sort(key=lambda r: (-(fnum(r.get("target_grass_rate")) or 0.0), -(fnum(r.get("target_mean_abs_lateral")) or 0.0)))
    if safety:
        cases.append(case_record("safety_intervention_replay", "Safety module intervention under off-track/lateral-risk exposure.", safety[0], None))
    fields = [
        "case_id",
        "claim",
        "experiment_id",
        "track_path",
        "num_agents",
        "seed",
        "primary_summary",
        "baseline_summary",
        "primary_overtake_success_rate",
        "primary_elegant_overtake_rate",
        "primary_target_grass_rate",
        "baseline_overtake_success_rate",
        "baseline_elegant_overtake_rate",
        "baseline_target_grass_rate",
    ]
    return write_csv(Path(out_dir) / "tables" / "e5_mechanism_case_selection.csv", cases, fields), cases


def case_record(case_id, claim, primary, baseline):
    return {
        "case_id": case_id,
        "claim": claim,
        "experiment_id": primary.get("experiment_id"),
        "track_path": primary.get("track_path"),
        "num_agents": primary.get("num_agents"),
        "seed": primary.get("seed"),
        "primary_summary": primary.get("_summary_file"),
        "baseline_summary": "" if baseline is None else baseline.get("_summary_file"),
        "primary_overtake_success_rate": primary.get("overtake_success_rate"),
        "primary_elegant_overtake_rate": primary.get("elegant_overtake_rate"),
        "primary_target_grass_rate": primary.get("target_grass_rate"),
        "baseline_overtake_success_rate": "" if baseline is None else baseline.get("overtake_success_rate"),
        "baseline_elegant_overtake_rate": "" if baseline is None else baseline.get("elegant_overtake_rate"),
        "baseline_target_grass_rate": "" if baseline is None else baseline.get("target_grass_rate"),
    }


def write_caption(path, captions):
    lines = [r"\begin{figure*}[t]", r"\centering", "% Insert exported SVG/PDF panels here."]
    for name, caption in captions.items():
        lines.append(f"% {name}: {caption}")
    lines.extend([r"\caption{Six-experiment online overtaking evaluation. " + " ".join(captions.values()) + r"}", r"\end{figure*}", ""])
    Path(path).write_text("\n".join(lines), encoding="utf-8")
    return str(path)


def write_style_tables(out_dir):
    algorithm_rows = [
        {
            "type": "algorithm",
            "id": name,
            "label": label_for_algorithm(name),
            "hex_color": color,
            "usage": "manuscript figures and mixed-controller top-down vehicle traces",
        }
        for name, color in sorted(ALGORITHM_COLORS.items())
    ]
    vehicle_rows = [
        {
            "type": "vehicle",
            "id": f"agent_{idx}",
            "label": f"Agent {idx}",
            "hex_color": color,
            "usage": "default vehicle body color and top-down color when no algorithm assignment is supplied",
        }
        for idx, color in enumerate(VEHICLE_COLORS_HEX)
    ]
    rows = algorithm_rows + vehicle_rows
    fields = ["type", "id", "label", "hex_color", "usage"]
    return write_csv(Path(out_dir) / "tables" / "visual_style_color_map.csv", rows, fields)


def write_co_track_agent_metrics(out_dir, rows):
    clean_rows = []
    for row in rows:
        clean_rows.append(
            {
                key: value
                for key, value in row.items()
                if not isinstance(value, (list, dict))
            }
        )
    fields = sorted({key for row in clean_rows for key in row.keys()})
    return write_csv(Path(out_dir) / "tables" / "co_track_agent_metrics.csv", clean_rows, fields)


def write_readme(out_dir, manifest, cases):
    lines = [
        "# T-ITS Six-Experiment Result Package",
        "",
        "All figures are generated from frozen online experiment artifacts. The visual style, algorithm order and colors are shared with Experiment 1.",
        "",
        "## Figures",
        "",
    ]
    for name, outputs in manifest["figures"].items():
        lines.append(f"- {name}: `{outputs['svg']}` / `{outputs['pdf']}` / `{outputs['tiff']}`")
    lines.extend(["", "## Mechanism Cases", ""])
    for case in cases:
        lines.append(f"- {case['case_id']}: {case['claim']} n={case['num_agents']}, seed={case['seed']}.")
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Probability endpoints use all evaluated cases.",
            "- Continuous physical metrics are conditioned on successful overtaking episodes.",
            "- Vehicle colors and algorithm colors are centralized in `scripts/tits_figure_style.py` for reproducible screenshots and GIFs.",
        ]
    )
    path = Path(out_dir) / "README.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(path)


def make_figures(expanded, mixed, out_dir):
    out_dir = Path(out_dir)
    fig_dir = out_dir / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    captions = {}
    figures = {}

    e2_rows = [row for row in expanded if row.get("experiment_id") == "E2_environment_generalization"]
    e2_algorithms = algorithms_present(e2_rows, ALGORITHM_ORDER)
    figures["E2_environment_generalization"], captions["E2"] = figure_direct_distribution(
        e2_rows,
        e2_algorithms,
        fig_dir / "figure_e2_environment_generalization",
        "Environment-generalization experiment on external tracks",
    )

    e3_rows = [row for row in expanded if row.get("experiment_id") == "E3_scale_extension"]
    e3_algorithms = algorithms_present(e3_rows, ALGORITHM_ORDER)
    figures["E3_scale_extension"], captions["E3"] = make_e3_figure(e3_rows, e3_algorithms, fig_dir / "figure_e3_scale_extension")

    e4_rows = [row for row in mixed if row.get("experiment_id") == "E4_interaction_generalization"]
    figures["E4_interaction_generalization"], captions["E4"] = make_e4_figure(e4_rows, fig_dir / "figure_e4_interaction_generalization")

    e6_rows = [row for row in expanded if row.get("experiment_id") == "E6_ablation"]
    e6_algorithms = algorithms_present(e6_rows, ABLATION_ORDER)
    figures["E6_ablation"], captions["E6"] = figure_direct_distribution(
        e6_rows,
        e6_algorithms,
        fig_dir / "figure_e6_ablation",
        "Ablation experiment for the proposed dynamic-graph DLC world model",
    )

    caption_path = write_caption(out_dir / "six_experiment_figure_captions.tex", captions)
    return figures, caption_path


def main():
    parser = argparse.ArgumentParser(description="Export T-ITS six-experiment paper result figures and tables.")
    parser.add_argument("--expanded-source", default="outputs/tits_dynamic_graph_expanded/six_experiment_paper_results/expanded_matrix_summary/tables/online_benchmark_source_data.csv")
    parser.add_argument("--mixed-root", default="outputs/tits_dynamic_graph_expanded/mixed_controller_tournament")
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph_expanded/six_experiment_paper_results")
    parser.add_argument("--seed", type=int, default=2026)
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    (out_dir / "tables").mkdir(parents=True, exist_ok=True)
    (out_dir / "figures").mkdir(parents=True, exist_ok=True)
    font = configure_publication_matplotlib(font_size=7.0)
    rng = np.random.default_rng(args.seed)

    expanded = load_expanded(args.expanded_source)
    mixed = load_mixed(args.mixed_root)
    all_rows = expanded + mixed
    metric_path, metric_rows = metric_table(all_rows, out_dir, rng)
    figures, caption_path = make_figures(expanded, mixed, out_dir)
    case_path, cases = select_mechanism_cases(expanded, out_dir)
    style_table = write_style_tables(out_dir)
    co_track_table = write_co_track_agent_metrics(out_dir, mixed)
    manifest = {
        "status": "pass",
        "font": font,
        "style_source": "scripts/tits_figure_style.py",
        "expanded_source": args.expanded_source,
        "mixed_root": args.mixed_root,
        "expanded_run_count": len(expanded),
        "mixed_case_count": len(mixed),
        "metric_summary": metric_path,
        "e5_case_selection": case_path,
        "caption_tex": caption_path,
        "visual_style_color_map": style_table,
        "co_track_agent_metrics": co_track_table,
        "figures": figures,
        "algorithm_color_map": {name: ALGORITHM_COLORS.get(name) for name in sorted(ALGORITHM_COLORS)},
    }
    manifest["readme"] = write_readme(out_dir, manifest, cases)
    manifest_path = write_json(out_dir / "six_experiment_paper_results_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, **manifest}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
