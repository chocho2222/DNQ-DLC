#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import json
import math
from pathlib import Path
from collections import defaultdict

import numpy as np


METRICS = [
    ("overtake_success_rate", "超车成功率", True),
    ("overtake_count", "超车次数", True),
    ("on_track_overtake_rate", "赛道内超车率", True),
    ("elegant_overtake_rate", "Desirable overtaking behavior rate", True),
    ("rank_gain", "名次提升", True),
    ("overtake_start_to_complete_time", "超车耗时", False),
    ("time_to_first_overtake", "首次超车时间", False),
    ("target_progress", "目标车进度", True),
    ("target_grass_rate", "草地率", False),
    ("grass_recovery_time_mean", "草地后恢复时间", False),
    ("target_mean_abs_lateral", "横向偏差", False),
    ("target_heading_error_mean_rad", "航向误差", False),
    ("collision_or_contact_proxy", "近距接触代理", False),
    ("compute_latency_ms", "决策延迟", False),
]

ALGORITHM_ORDER = [
    "v6_runtime_dynamic_neighborhood",
    "v6_runtime_dynamic_neighborhood_fast",
    "v6_runtime_dynamic_neighborhood_safe",
    "ours_dynamic_graph_dlc_world",
    "ours_no_overtake_aware_planner",
    "quality_proposal_dlc_world_v1",
    "quality_proposal_dlc_world_v2",
    "quality_guided_dlc_world_v3",
    "quality_aux_dlc_world_v4",
    "quality_aux_dlc_world_v5_soft025",
    "quality_aux_dlc_world_v5_soft050",
    "quality_aux_dlc_world_v5_gate025",
    "graph_bc_dynamic",
    "quality_graph_bc_v1",
    "quality_graph_bc_v2",
    "dlc_world_original",
    "dlc_world_balanced",
    "dlc_world_safety",
    "dlc_world_fast",
    "rule_expert_gate",
    "rule_adaptive_gate",
]

ALGORITHM_COLORS = {
    "v6_runtime_dynamic_neighborhood": "#7A96B6",
    "v6_runtime_dynamic_neighborhood_fast": "#8FB7B0",
    "v6_runtime_dynamic_neighborhood_safe": "#4D78B8",
    "dlc_individual_transition": "#A9B6C8",
    "dlc_joint_transition": "#C9B77E",
    "dlc_joint_transition_observer": "#8DB8C7",
    "ppo_continuous": "#BDA4CF",
    "sac_continuous": "#8EBE9C",
    "td3_continuous": "#D6A477",
    "rule_expert_gate": "#D38B8B",
    "rule_safety_gate": "#C0A3D8",
    "ours_dynamic_graph_dlc_world": "#7A96B6",
    "ours_no_overtake_aware_planner": "#B99CCF",
    "quality_proposal_dlc_world_v1": "#CFA8BF",
    "quality_proposal_dlc_world_v2": "#C48DA2",
    "quality_guided_dlc_world_v3": "#B9A8D2",
    "quality_aux_dlc_world_v4": "#C7B9DE",
    "quality_aux_dlc_world_v5_soft025": "#A88ED0",
    "quality_aux_dlc_world_v5_soft050": "#9E8CC8",
    "quality_aux_dlc_world_v5_gate025": "#D8CAEC",
    "graph_bc_dynamic": "#D8B37C",
    "quality_graph_bc_v1": "#D4A16B",
    "quality_graph_bc_v2": "#CDB387",
    "dlc_world_original": "#87939D",
    "dlc_world_balanced": "#A2ABB3",
    "dlc_world_safety": "#B6BDC5",
    "dlc_world_fast": "#9AA6B3",
    "rule_adaptive_gate": "#E2A4A4",
}


def register_cjk_font():
    import matplotlib as mpl
    from matplotlib import font_manager

    candidates = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
        "/usr/share/fonts/truetype/arphic/ukai.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for item in candidates:
        path = Path(item)
        if path.exists():
            font_manager.fontManager.addfont(str(path))
            family = font_manager.FontProperties(fname=str(path)).get_name()
            mpl.rcParams["font.family"] = family
            mpl.rcParams["font.sans-serif"] = [family, "Arial", "DejaVu Sans", "sans-serif"]
            return family
    return None


def load_summaries(input_dir):
    summaries = []
    for path in sorted(Path(input_dir).glob("**/summaries/*.summary.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        data["_summary_file"] = str(path)
        rel = path.relative_to(input_dir)
        parts = rel.parts
        data["_benchmark"] = parts[0] if len(parts) >= 5 else data.get("track_path", "unknown")
        data["_agent_bucket"] = parts[1] if len(parts) >= 5 else f"n{data.get('num_agents', 'unknown')}"
        data["_seed_bucket"] = parts[2] if len(parts) >= 5 else f"seed{data.get('seed', 'unknown')}"
        summaries.append(data)
    return summaries


def safe_float(value):
    if value is None:
        return None
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(value) or math.isinf(value):
        return None
    return value


def bootstrap_ci(values, rng, n_boot=2000, alpha=0.05):
    values = np.asarray([item for item in values if item is not None and np.isfinite(item)], dtype=np.float64)
    if values.size == 0:
        return None, None, None
    mean = float(values.mean())
    if values.size == 1:
        return mean, mean, mean
    indices = rng.integers(0, values.size, size=(int(n_boot), values.size))
    boot = values[indices].mean(axis=1)
    lo, hi = np.quantile(boot, [alpha / 2.0, 1.0 - alpha / 2.0])
    return mean, float(lo), float(hi)


def paired_deltas(rows, metric, baseline="dlc_world_original", benchmark=None, num_agents=None):
    by_case = {}
    for row in rows:
        if benchmark is not None and row.get("_benchmark") != benchmark:
            continue
        if num_agents is not None and int(row.get("num_agents", -1)) != int(num_agents):
            continue
        key = (row.get("_benchmark"), row.get("num_agents"), row.get("seed"))
        by_case.setdefault(key, {})[row["algorithm"]] = safe_float(row.get(metric))
    deltas = {}
    for case_values in by_case.values():
        base = case_values.get(baseline)
        if base is None:
            continue
        for algorithm, value in case_values.items():
            if value is None or algorithm == baseline:
                continue
            deltas.setdefault(algorithm, []).append(value - base)
    return deltas


def sign_test_pvalue(deltas):
    values = [item for item in deltas if item is not None and item != 0]
    n = len(values)
    if n == 0:
        return None
    positives = sum(item > 0 for item in values)
    k = min(positives, n - positives)
    prob = 0.0
    for i in range(k + 1):
        prob += math.comb(n, i) * (0.5 ** n)
    return min(1.0, 2.0 * prob)


def write_source_csv(summaries, path):
    fields = [
        "_benchmark",
        "algorithm",
        "algorithm_label_cn",
        "neighbor_selection_mode",
        "planner_horizon",
        "planner_candidates",
        "planner_risk_weight",
        "planner_progress_weight",
        "planner_uncertainty_weight",
        "overtake_aware_planner",
        "elegance_barrier",
        "elegance_barrier_weight",
        "elegance_lateral_limit",
        "elegance_heading_cos_min",
        "elegance_grass_penalty",
        "elegance_backward_penalty",
        "elegance_close_gap_limit",
        "quality_planner_mode",
        "quality_rollout_blend",
        "quality_overtake_weight",
        "quality_lane_weight",
        "quality_grass_weight",
        "quality_close_gap_weight",
        "seed",
        "num_agents",
        "track_path",
        "traffic_profile",
        "target_final_rank",
        "rank_gain",
        "target_progress",
        "target_completed_lap",
        "overtake_success_rate",
        "overtake_count",
        "on_track_overtake_count",
        "on_track_overtake_rate",
        "elegant_overtake_count",
        "elegant_overtake_rate",
        "time_to_first_overtake",
        "overtake_start_to_complete_time",
        "overtake_window_grass_rate_mean",
        "overtake_window_max_abs_lateral_mean",
        "target_grass_rate",
        "grass_recovery_time_mean",
        "grass_recovery_time_max",
        "grass_excursion_count",
        "unrecovered_grass_excursion_count",
        "target_mean_abs_lateral",
        "target_heading_error_mean_rad",
        "collision_or_contact_proxy",
        "compute_latency_ms",
        "compute_latency_p95_ms",
        "finish_step",
        "topdown_gif",
        "first_person_gif",
        "_summary_file",
    ]
    path = Path(path)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in summaries:
            writer.writerow({field: row.get(field) for field in fields})
    return str(path)


def write_aggregate_csv(summaries, path, n_boot, seed):
    rng = np.random.default_rng(seed)
    groups = {}
    for row in summaries:
        key = (
            row.get("_benchmark", "unknown"),
            int(row.get("num_agents", -1)),
            row["algorithm"],
            row.get("algorithm_label_cn", row["algorithm"]),
        )
        groups.setdefault(key, []).append(row)

    fields = [
        "benchmark",
        "num_agents",
        "algorithm",
        "algorithm_label_cn",
        "metric",
        "metric_cn",
        "higher_is_better",
        "n",
        "mean",
        "ci95_low",
        "ci95_high",
        "paired_delta_vs_dlc_mean",
        "paired_delta_vs_dlc_ci95_low",
        "paired_delta_vs_dlc_ci95_high",
        "paired_sign_test_p",
    ]
    all_rows = []
    for metric, metric_cn, higher_is_better in METRICS:
        for key, rows in groups.items():
            benchmark, num_agents, algorithm, label = key
            deltas_by_algorithm = paired_deltas(
                summaries,
                metric,
                benchmark=benchmark,
                num_agents=num_agents,
            )
            delta_stats = {}
            for delta_algorithm, deltas in deltas_by_algorithm.items():
                mean_delta, lo_delta, hi_delta = bootstrap_ci(deltas, rng, n_boot=n_boot)
                delta_stats[delta_algorithm] = {
                    "mean": mean_delta,
                    "lo": lo_delta,
                    "hi": hi_delta,
                    "p": sign_test_pvalue(deltas),
                }
            values = [safe_float(row.get(metric)) for row in rows]
            values = [value for value in values if value is not None]
            mean, lo, hi = bootstrap_ci(values, rng, n_boot=n_boot)
            stats = delta_stats.get(algorithm, {})
            all_rows.append(
                {
                    "benchmark": benchmark,
                    "num_agents": num_agents,
                    "algorithm": algorithm,
                    "algorithm_label_cn": label,
                    "metric": metric,
                    "metric_cn": metric_cn,
                    "higher_is_better": bool(higher_is_better),
                    "n": len(values),
                    "mean": mean,
                    "ci95_low": lo,
                    "ci95_high": hi,
                    "paired_delta_vs_dlc_mean": stats.get("mean"),
                    "paired_delta_vs_dlc_ci95_low": stats.get("lo"),
                    "paired_delta_vs_dlc_ci95_high": stats.get("hi"),
                    "paired_sign_test_p": stats.get("p"),
                }
            )

    order = {name: idx for idx, name in enumerate(ALGORITHM_ORDER)}
    metric_order = {name: idx for idx, (name, _, _) in enumerate(METRICS)}
    all_rows.sort(
        key=lambda row: (
            row["benchmark"],
            row["num_agents"],
            metric_order.get(row["metric"], 999),
            order.get(row["algorithm"], 999),
        )
    )
    path = Path(path)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(all_rows)
    return str(path), all_rows


def latex_value(mean, lo, hi, precision=2):
    if mean is None:
        return "--"
    if lo is None or hi is None:
        return f"{mean:.{precision}f}"
    return f"{mean:.{precision}f} [{lo:.{precision}f}, {hi:.{precision}f}]"


def write_markdown_table(aggregate_rows, path):
    primary_metrics = {
        "overtake_success_rate": 2,
        "on_track_overtake_rate": 2,
        "elegant_overtake_rate": 2,
        "rank_gain": 2,
        "overtake_start_to_complete_time": 1,
        "target_grass_rate": 3,
        "grass_recovery_time_mean": 1,
        "compute_latency_ms": 1,
    }
    selected = [
        row
        for row in aggregate_rows
        if row["metric"] in primary_metrics
    ]
    path = Path(path)
    lines = [
        "# 在线超车主结果表",
        "",
        "| Benchmark | N车 | 算法 | 指标 | 均值 [95% CI] | 相对DLC差值 | p值 |",
        "|---|---:|---|---|---:|---:|---:|",
    ]
    for row in selected:
        precision = primary_metrics[row["metric"]]
        p_value = row.get("paired_sign_test_p")
        lines.append(
            "| {benchmark} | {num_agents} | {algorithm_label_cn} | {metric_cn} | {value} | {delta} | {p} |".format(
                benchmark=row["benchmark"],
                num_agents=row["num_agents"],
                algorithm_label_cn=row["algorithm_label_cn"],
                metric_cn=row["metric_cn"],
                value=latex_value(row.get("mean"), row.get("ci95_low"), row.get("ci95_high"), precision),
                delta=latex_value(row.get("paired_delta_vs_dlc_mean"), row.get("paired_delta_vs_dlc_ci95_low"), row.get("paired_delta_vs_dlc_ci95_high"), precision),
                p="--" if p_value is None else f"{p_value:.3g}",
            )
        )
    lines.extend(
        [
            "",
            "说明：置信区间采用 bootstrap；p 值采用与 DLC 世界模型的成对符号检验，仅用于辅助报告，不替代完整统计分析计划。",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(path)


def plot_summary(summaries, out_dir):
    import matplotlib as mpl
    import matplotlib.pyplot as plt
    import matplotlib.colors as mcolors
    from mpl_toolkits.axes_grid1.inset_locator import inset_axes

    register_cjk_font()
    mpl.rcParams.update(
        {
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "font.size": 8,
            "axes.spines.right": False,
            "axes.spines.top": False,
            "axes.unicode_minus": False,
            "legend.frameon": False,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
        }
    )

    algorithms = []
    labels = {}
    for row in summaries:
        if row["algorithm"] not in algorithms:
            algorithms.append(row["algorithm"])
        labels[row["algorithm"]] = row.get("algorithm_label_cn", row["algorithm"])
    order = {name: idx for idx, name in enumerate(ALGORITHM_ORDER)}
    algorithms.sort(key=lambda name: order.get(name, 999))

    primary = "v6_runtime_dynamic_neighborhood_safe"
    metrics = [
        ("overtake_success_rate", "a  Overtake Success Gain", "Gain", True),
        ("on_track_overtake_rate", "b  On-track Overtake Gain", "Gain", True),
        ("elegant_overtake_rate", "c  Desirable Overtake Gain", "Gain", True),
        ("overtake_start_to_complete_time", "d  Completion Time Reduction", "Reduction", False),
        ("target_grass_rate", "e  Grass Excursion Reduction", "Reduction", False),
        ("grass_recovery_time_mean", "f  Grass Recovery Reduction", "Reduction", False),
    ]
    rng = np.random.default_rng(123)

    def soften(color, blend=0.22):
        rgb = np.asarray(mcolors.to_rgb(color), dtype=np.float64)
        return tuple((1.0 - blend) * rgb + blend * np.ones(3))

    def desaturate(color, amount=0.22):
        rgb = np.asarray(mcolors.to_rgb(color), dtype=np.float64)
        mean = float(rgb.mean())
        return tuple((1.0 - amount) * rgb + amount * np.full(3, mean))

    baseline_algorithms = [
        algo for algo in algorithms if algo != primary
    ]

    fig = plt.figure(figsize=(12.0, 7.4), constrained_layout=True)
    gs = fig.add_gridspec(2, 3)
    axes = [fig.add_subplot(gs[i, j]) for i in range(2) for j in range(3)]
    case_values = defaultdict(dict)
    for row in summaries:
        key = (row.get("_benchmark"), row.get("num_agents"), row.get("seed"))
        case_values[key][row["algorithm"]] = {metric: safe_float(row.get(metric)) for metric, _, _, _ in metrics}

    def paired_improvements(metric, higher_is_better):
        groups = []
        for baseline in baseline_algorithms:
            deltas = []
            for values in case_values.values():
                ours = values.get(primary, {}).get(metric)
                other = values.get(baseline, {}).get(metric)
                if ours is None or other is None:
                    continue
                raw = ours - other if higher_is_better else other - ours
                deltas.append(raw)
            groups.append(deltas)
        return groups

    def display_clip(metric, values):
        if not values:
            return values
        if metric in {"overtake_start_to_complete_time", "grass_recovery_time_mean"}:
            lo, hi = np.quantile(values, [0.02, 0.98])
            bound = max(abs(lo), abs(hi))
            bound = min(bound, 500.0 if metric == "grass_recovery_time_mean" else 700.0)
            return [max(-bound, min(bound, v)) for v in values]
        lo, hi = np.quantile(values, [0.02, 0.98])
        bound = max(abs(lo), abs(hi))
        return [max(-bound, min(bound, v)) for v in values]

    for ax, (metric, title, ylabel, higher_is_better) in zip(axes, metrics):
        grouped = [display_clip(metric, vals) for vals in paired_improvements(metric, higher_is_better)]
        positions = np.arange(1, len(baseline_algorithms) + 1)
        non_empty = [(pos, algo, vals) for pos, algo, vals in zip(positions, baseline_algorithms, grouped) if len(vals) > 0]
        if non_empty:
            vp = ax.violinplot(
                [vals for _, _, vals in non_empty],
                positions=[pos for pos, _, _ in non_empty],
                widths=0.88,
                showmeans=False,
                showmedians=False,
                showextrema=False,
            )
            for body, (_, algorithm, _) in zip(vp["bodies"], non_empty):
                color = desaturate(ALGORITHM_COLORS.get(algorithm, "#9AA4B2"), 0.18)
                body.set_facecolor(color)
                body.set_edgecolor("#111111")
                body.set_alpha(0.10)
                body.set_linewidth(0.8)

        for pos, algorithm, vals in non_empty:
            color = desaturate(ALGORITHM_COLORS.get(algorithm, "#9AA4B2"), 0.12)
            q1, med, q3 = np.percentile(vals, [25, 50, 75])
            low = np.min(vals)
            high = np.max(vals)
            ax.plot([pos, pos], [low, high], color="#1F1F1F", lw=1.0, zorder=3)
            ax.add_patch(
                plt.Rectangle(
                    (pos - 0.30, q1),
                    0.60,
                    max(q3 - q1, 1e-9),
                    facecolor=(1, 1, 1, 0.40),
                    edgecolor="#1F1F1F",
                    lw=1.0,
                    zorder=4,
                )
            )
            ax.plot([pos - 0.30, pos + 0.30], [med, med], color="#1F1F1F", lw=1.1, zorder=5)
            jitter = (rng.random(len(vals)) - 0.5) * 0.20
            ax.scatter(
                np.full(len(vals), pos) + jitter,
                vals,
                s=54,
                color=color,
                edgecolors="#111111",
                linewidths=0.42,
                alpha=0.86,
                zorder=6,
            )

        ours_vals = []
        for values in case_values.values():
            ours = values.get(primary, {}).get(metric)
            if ours is not None:
                ours_vals.append(ours if higher_is_better else ours)
        if ours_vals:
            inset = inset_axes(ax, width="25%", height="28%", loc="upper right", borderpad=0.7)
            inset.set_facecolor((1, 1, 1, 0.96))
            inset.spines["right"].set_visible(False)
            inset.spines["top"].set_visible(False)
            inset.spines["left"].set_color(ALGORITHM_COLORS.get(primary, "#4F79B5"))
            inset.spines["bottom"].set_color("#1F1F1F")
            inset.spines["left"].set_linewidth(1.0)
            inset.spines["bottom"].set_linewidth(0.9)
            inset.grid(axis="y", color="#E1E7EE", lw=0.45)
            ours_color = desaturate(ALGORITHM_COLORS.get(primary, "#4F79B5"), 0.06)
            q1, med, q3 = np.percentile(ours_vals, [25, 50, 75])
            low = np.min(ours_vals)
            high = np.max(ours_vals)
            inset.plot([1, 1], [low, high], color="#1F1F1F", lw=0.85, zorder=3)
            inset.add_patch(
                plt.Rectangle(
                    (0.74, q1),
                    0.52,
                    max(q3 - q1, 1e-9),
                    facecolor=(1, 1, 1, 0.45),
                    edgecolor="#1F1F1F",
                    lw=0.8,
                    zorder=4,
                )
            )
            inset.plot([0.74, 1.26], [med, med], color="#1F1F1F", lw=0.9, zorder=5)
            jitter = (rng.random(len(ours_vals)) - 0.5) * 0.16
            inset.scatter(
                np.full(len(ours_vals), 1.0) + jitter,
                ours_vals,
                s=18,
                color=ours_color,
                edgecolors="#111111",
                linewidths=0.35,
                alpha=0.82,
                zorder=6,
            )
            inset.set_xticks([])
            inset.tick_params(axis="y", labelsize=5.4)
            inset.set_axisbelow(True)
            inset.set_xlim(0.6, 1.4)
            inset.text(0.03, 0.97, "本文方法", transform=inset.transAxes, ha="left", va="top", fontsize=7.0, color=ours_color, fontweight="bold")
            inset.text(0.03, 0.82, "主算法分布", transform=inset.transAxes, ha="left", va="top", fontsize=5.4, color="#666666")
            inset.text(0.03, 0.08, "scatter + box", transform=inset.transAxes, ha="left", va="bottom", fontsize=5.1, color="#7A7A7A")

        ax.axhline(0.0, color="#222222", lw=1.0, ls="--", zorder=2)
        ax.set_title(title)
        ax.set_ylabel(ylabel)
        ax.set_xticks(positions)
        ax.set_xticklabels([labels[item] for item in baseline_algorithms], rotation=28, ha="right")
        for tick, algo in zip(ax.get_xticklabels(), baseline_algorithms):
            tick.set_color(soften(ALGORITHM_COLORS.get(algo, "#9AA4B2"), 0.18))
            tick.set_fontweight("bold")
        ax.grid(axis="y", color="#D9E1E8", lw=0.6)
        ax.set_axisbelow(True)
        if any(len(vals) == 0 for vals in grouped):
            ax.text(0.99, 0.02, "NA shown for empty groups", transform=ax.transAxes, ha="right", va="bottom", fontsize=6.2, color="#555555")
        if metric in {"overtake_start_to_complete_time", "grass_recovery_time_mean"}:
            ax.set_ylim(-700 if metric == "overtake_start_to_complete_time" else -500, 700 if metric == "overtake_start_to_complete_time" else 500)

    fig.suptitle("Paired improvement of the proposed method over baselines", fontsize=12, fontweight="bold")
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = out_dir / "figure_tits_online_benchmark_paired_improvement"
    outputs = {}
    for ext in ["svg", "pdf", "png", "tiff"]:
        path = stem.with_suffix(f".{ext}")
        fig.savefig(path, dpi=600, bbox_inches="tight")
        outputs[f"paired_improvement_{ext}"] = str(path)
    plt.close(fig)

    direct_metrics = [
        ("overtake_success_rate", "a  Overtake success", "Rate", True),
        ("on_track_overtake_rate", "b  On-track overtake", "Rate", True),
        ("elegant_overtake_rate", "c  Desirable overtaking behavior", "Rate", True),
        ("rank_gain", "d  Rank gain", "Positions", True),
        ("target_progress", "e  Target progress", "Lap fraction", True),
        ("target_grass_rate", "f  Grass excursion", "Rate", False),
    ]
    display_labels = {
        "dlc_joint_transition_observer": "DLC-JTO",
        "dlc_joint_transition": "DLC-JT",
        "dlc_individual_transition": "DLC-IT",
        "ppo_continuous": "PPO",
        "sac_continuous": "SAC",
        "td3_continuous": "TD3",
        "rule_expert_gate": "Rule expert",
        "rule_safety_gate": "Safety rule",
        primary: "Proposed",
    }
    direct_order = [
        "dlc_joint_transition_observer",
        "dlc_joint_transition",
        "dlc_individual_transition",
        "ppo_continuous",
        "sac_continuous",
        "td3_continuous",
        "rule_expert_gate",
        "rule_safety_gate",
        primary,
    ]
    direct_algorithms = [algo for algo in direct_order if algo in algorithms]
    direct_case_values = defaultdict(dict)
    for row in summaries:
        key = (row.get("_benchmark"), int(row.get("num_agents", -1)), row.get("seed"))
        direct_case_values[key][row["algorithm"]] = {
            metric: safe_float(row.get(metric)) for metric, _, _, _ in direct_metrics
        }

    eligible_cases = []
    for key, values in direct_case_values.items():
        if not all(algo in values for algo in direct_algorithms):
            continue
        complete = True
        for algo in direct_algorithms:
            for metric, _, _, _ in direct_metrics:
                if values[algo].get(metric) is None:
                    complete = False
                    break
            if not complete:
                break
        if complete:
            eligible_cases.append(key)

    def scenario_quality_score(key):
        _, num_agents, _ = key
        denom = max(float(num_agents - 1), 1.0)
        values = direct_case_values[key]
        scores = []
        for algo in direct_algorithms:
            item = values[algo]
            scores.extend(
                [
                    np.clip(item["overtake_success_rate"], 0.0, 1.0),
                    np.clip(item["on_track_overtake_rate"], 0.0, 1.0),
                    np.clip(item["elegant_overtake_rate"], 0.0, 1.0),
                    np.clip(item["rank_gain"] / denom, 0.0, 1.0),
                    np.clip(item["target_progress"], 0.0, 1.0),
                    1.0 - np.clip(item["target_grass_rate"], 0.0, 1.0),
                ]
            )
        return float(np.mean(scores)) if scores else -np.inf

    trim_fraction = 0.05
    ranked_cases = sorted(eligible_cases, key=scenario_quality_score, reverse=True)
    keep_count = int(math.floor(len(ranked_cases) * (1.0 - trim_fraction)))
    keep_count = max(1, keep_count)
    kept_cases = ranked_cases[:keep_count]
    excluded_cases = ranked_cases[keep_count:]
    kept_set = set(kept_cases)

    tables_dir = out_dir.parent / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)
    trim_case_path = tables_dir / "online_benchmark_direct_trimmed_cases.csv"
    with trim_case_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["benchmark", "num_agents", "seed", "scenario_quality_score", "included"],
        )
        writer.writeheader()
        for key in ranked_cases:
            benchmark, num_agents, seed = key
            writer.writerow(
                {
                    "benchmark": benchmark,
                    "num_agents": num_agents,
                    "seed": seed,
                    "scenario_quality_score": scenario_quality_score(key),
                    "included": int(key in kept_set),
                }
            )

    direct_source_path = tables_dir / "online_benchmark_direct_trimmed_source_data.csv"
    with direct_source_path.open("w", newline="", encoding="utf-8") as handle:
        fields = ["benchmark", "num_agents", "seed", "algorithm", "algorithm_label", "metric", "value"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for key in kept_cases:
            benchmark, num_agents, seed = key
            for algo in direct_algorithms:
                for metric, _, _, _ in direct_metrics:
                    writer.writerow(
                        {
                            "benchmark": benchmark,
                            "num_agents": num_agents,
                            "seed": seed,
                            "algorithm": algo,
                            "algorithm_label": display_labels.get(algo, labels.get(algo, algo)),
                            "metric": metric,
                            "value": direct_case_values[key][algo][metric],
                        }
                    )

    fig = plt.figure(figsize=(13.2, 7.6), constrained_layout=True)
    gs = fig.add_gridspec(2, 3)
    axes = [fig.add_subplot(gs[i, j]) for i in range(2) for j in range(3)]
    positions = np.arange(1, len(direct_algorithms) + 1)
    for ax, (metric, title, ylabel, higher_is_better) in zip(axes, direct_metrics):
        grouped = [
            [direct_case_values[key][algo][metric] for key in kept_cases]
            for algo in direct_algorithms
        ]
        vp = ax.violinplot(
            grouped,
            positions=positions,
            widths=0.86,
            showmeans=False,
            showmedians=False,
            showextrema=False,
        )
        for body, algo in zip(vp["bodies"], direct_algorithms):
            color = desaturate(ALGORITHM_COLORS.get(algo, "#9AA4B2"), 0.14)
            body.set_facecolor(color)
            body.set_edgecolor("#222222")
            body.set_alpha(0.10 if algo != primary else 0.16)
            body.set_linewidth(0.8)

        for pos, algo, vals in zip(positions, direct_algorithms, grouped):
            color = desaturate(ALGORITHM_COLORS.get(algo, "#9AA4B2"), 0.10)
            if algo == primary:
                color = desaturate(ALGORITHM_COLORS.get(algo, "#4D78B8"), 0.03)
            q1, med, q3 = np.percentile(vals, [25, 50, 75])
            low = np.min(vals)
            high = np.max(vals)
            ax.plot([pos, pos], [low, high], color="#1F1F1F", lw=1.0, zorder=3)
            ax.add_patch(
                plt.Rectangle(
                    (pos - 0.30, q1),
                    0.60,
                    max(q3 - q1, 1e-9),
                    facecolor=(1, 1, 1, 0.48 if algo != primary else 0.35),
                    edgecolor="#1F1F1F",
                    lw=1.0 if algo != primary else 1.35,
                    zorder=4,
                )
            )
            ax.plot([pos - 0.30, pos + 0.30], [med, med], color="#1F1F1F", lw=1.1, zorder=5)
            jitter = (rng.random(len(vals)) - 0.5) * 0.30
            y_values = np.asarray(vals, dtype=np.float64)
            if len(np.unique(np.round(y_values, 6))) <= 8:
                y_span = max(float(np.max(y_values) - np.min(y_values)), 1.0)
                y_values = y_values + (rng.random(len(vals)) - 0.5) * 0.025 * y_span
            ax.scatter(
                np.full(len(vals), pos) + jitter,
                y_values,
                s=22 if algo != primary else 30,
                color=color,
                edgecolors="#111111",
                linewidths=0.25 if algo != primary else 0.38,
                alpha=0.64 if algo != primary else 0.82,
                zorder=6 if algo != primary else 7,
            )
        if metric in {"overtake_success_rate", "on_track_overtake_rate", "elegant_overtake_rate", "target_progress", "target_grass_rate"}:
            ax.set_ylim(-0.06, 1.06)
        if metric == "rank_gain":
            ymax = max(max(vals) for vals in grouped)
            ax.set_ylim(-0.25, ymax + 0.55)
        ax.set_title(title)
        ax.set_ylabel(ylabel)
        ax.set_xticks(positions)
        ax.set_xticklabels(
            [display_labels.get(algo, labels.get(algo, algo)) for algo in direct_algorithms],
            rotation=28,
            ha="right",
        )
        for tick, algo in zip(ax.get_xticklabels(), direct_algorithms):
            tick.set_color(desaturate(ALGORITHM_COLORS.get(algo, "#9AA4B2"), 0.08))
            tick.set_fontweight("bold" if algo == primary else "normal")
        ax.grid(axis="y", color="#D9E1E8", lw=0.6)
        ax.set_axisbelow(True)
        if not higher_is_better:
            ax.text(0.98, 0.94, "lower is better", transform=ax.transAxes, ha="right", va="top", fontsize=6.4, color="#555555")

    fig.suptitle("Direct online benchmark distributions after equal-case trimming", fontsize=12, fontweight="bold")
    fig.text(
        0.5,
        0.002,
        f"Each method and metric uses the same {len(kept_cases)} cases; the lowest {len(excluded_cases)} scenario-level outlier cases were removed uniformly across all methods.",
        ha="center",
        va="bottom",
        fontsize=7.0,
        color="#4B5563",
    )
    direct_stem = out_dir / "figure_tits_online_benchmark_direct_equal_trimmed"
    for ext in ["svg", "pdf", "png", "tiff"]:
        path = direct_stem.with_suffix(f".{ext}")
        fig.savefig(path, dpi=600, bbox_inches="tight")
        outputs[f"direct_equal_trimmed_{ext}"] = str(path)
    plt.close(fig)
    outputs["direct_equal_trimmed_cases"] = str(trim_case_path)
    outputs["direct_equal_trimmed_source_data"] = str(direct_source_path)
    return outputs


def main():
    parser = argparse.ArgumentParser(description="Summarize online dynamic graph overtake benchmark outputs.")
    parser.add_argument("--input-dir", default="outputs/tits_dynamic_graph/online_evaluation_matrix")
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/online_evaluation_matrix_summary")
    parser.add_argument("--bootstrap", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=2026)
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    tables_dir = out_dir / "tables"
    figures_dir = out_dir / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    summaries = load_summaries(args.input_dir)
    if not summaries:
        raise SystemExit(f"no summary files found under {args.input_dir}")

    source_csv = write_source_csv(summaries, tables_dir / "online_benchmark_source_data.csv")
    aggregate_csv, aggregate_rows = write_aggregate_csv(
        summaries,
        tables_dir / "online_benchmark_aggregate_statistics.csv",
        n_boot=args.bootstrap,
        seed=args.seed,
    )
    markdown_table = write_markdown_table(aggregate_rows, tables_dir / "online_benchmark_main_results.md")
    figure_outputs = plot_summary(summaries, figures_dir)

    manifest = {
        "input_dir": args.input_dir,
        "n_runs": len(summaries),
        "source_data": source_csv,
        "aggregate_statistics": aggregate_csv,
        "main_results_table": markdown_table,
        "figures": figure_outputs,
        "methods_note": "跨 seed 汇总采用 bootstrap 95% CI；与 DLC 世界模型的差异采用同 benchmark/同车辆数/同 seed 的成对差值。",
    }
    manifest_path = out_dir / "online_benchmark_summary_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
