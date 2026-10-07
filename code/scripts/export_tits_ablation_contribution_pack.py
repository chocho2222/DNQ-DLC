#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import json
import math
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np


plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.sans-serif"] = ["Arial", "DejaVu Sans", "Liberation Sans"]
plt.rcParams["svg.fonttype"] = "none"
plt.rcParams["pdf.fonttype"] = 42

OURS_SAFE = "v6_runtime_dynamic_neighborhood_safe"
OURS_FULL = "v6_runtime_dynamic_neighborhood"
QUALITY = "quality_proposal_dlc_world_v1"
DLC = "dlc_world_original"
RULE = "rule_expert_gate"
DLC_VARIANTS = ["dlc_world_original", "dlc_world_balanced", "dlc_world_safety", "dlc_world_fast"]

ALGORITHM_LABELS = {
    OURS_SAFE: "Dynamic DLC-safe",
    OURS_FULL: "Dynamic DLC",
    QUALITY: "Quality-proposal DLC",
    DLC: "Original DLC",
    "dlc_world_balanced": "DLC-balanced",
    "dlc_world_safety": "DLC-safety",
    "dlc_world_fast": "DLC-fast",
    RULE: "Rule expert",
}
COLORS = {
    OURS_SAFE: "#0F4D92",
    OURS_FULL: "#3775BA",
    QUALITY: "#42949E",
    DLC: "#B64342",
    "dlc_world_balanced": "#E9A6A1",
    "dlc_world_safety": "#C96D68",
    "dlc_world_fast": "#F6CFCB",
    RULE: "#606060",
}

METRICS = {
    "overtake_success_rate": ("Success", True, "proportion"),
    "elegant_overtake_rate": ("Desirable", True, "proportion"),
    "on_track_overtake_rate": ("On-track", True, "proportion"),
    "overtake_start_to_complete_time": ("Time reduction", False, "steps"),
    "target_grass_rate": ("Grass reduction", False, "proportion"),
    "compute_latency_ms": ("Latency reduction", False, "ms"),
}


def read_csv(path):
    with Path(path).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path, rows, fields):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return str(path)


def write_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")
    return str(path)


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


def f(value):
    if value in (None, "", "nan", "NaN"):
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(out):
        return None
    return out


def fmt(value, digits=3):
    value = f(value)
    if value is None:
        return "NA"
    return f"{value:.{digits}f}"


def mean_ci(row, metric):
    return (
        f(row.get(f"{metric}_mean")),
        f(row.get(f"{metric}_ci95_low")),
        f(row.get(f"{metric}_ci95_high")),
    )


def row_by_algorithm(rows, algorithm):
    for row in rows:
        if row["algorithm"] == algorithm:
            return row
    raise KeyError(algorithm)


def paired_lookup(rows, algorithm, metric):
    for row in rows:
        if row["algorithm"] == algorithm and row["metric"] == metric:
            return row
    raise KeyError((algorithm, metric))


def case_key(row):
    return (
        row.get("_benchmark", ""),
        row.get("num_agents", ""),
        row.get("seed", ""),
        row.get("track_path", ""),
        row.get("traffic_profile", ""),
    )


def paired_improvement_from_source(source_rows, algorithm, comparator, metric, higher_is_better, bootstrap=5000):
    by_case = {}
    for row in source_rows:
        key = case_key(row)
        by_case.setdefault(key, {})[row["algorithm"]] = row
    deltas = []
    for algs in by_case.values():
        if algorithm not in algs or comparator not in algs:
            continue
        a = f(algs[algorithm].get(metric))
        b = f(algs[comparator].get(metric))
        if a is None or b is None:
            continue
        deltas.append(a - b if higher_is_better else b - a)
    if not deltas:
        return None, None, None, 0
    arr = np.asarray(deltas, dtype=float)
    rng = np.random.default_rng(20260624)
    boot = rng.choice(arr, size=(bootstrap, len(arr)), replace=True).mean(axis=1)
    return float(arr.mean()), float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5)), int(len(arr))


def build_overall_table(overall_rows):
    fields = [
        "algorithm",
        "algorithm_label",
        "family",
        "n",
        "success_mean",
        "success_ci95_low",
        "success_ci95_high",
        "elegant_mean",
        "elegant_ci95_low",
        "elegant_ci95_high",
        "on_track_mean",
        "on_track_ci95_low",
        "on_track_ci95_high",
        "grass_mean",
        "grass_ci95_low",
        "grass_ci95_high",
        "completion_time_mean",
        "completion_time_ci95_low",
        "completion_time_ci95_high",
        "latency_ms_mean",
        "latency_ms_ci95_low",
        "latency_ms_ci95_high",
    ]
    order = [OURS_SAFE, OURS_FULL, QUALITY, DLC, "dlc_world_balanced", "dlc_world_safety", "dlc_world_fast", RULE]
    families = {
        OURS_SAFE: "proposed",
        OURS_FULL: "proposed",
        QUALITY: "proposed_variant",
        DLC: "dlc_baseline",
        "dlc_world_balanced": "dlc_baseline_variant",
        "dlc_world_safety": "dlc_baseline_variant",
        "dlc_world_fast": "dlc_baseline_variant",
        RULE: "rule_baseline",
    }
    rows = []
    for alg in order:
        row = row_by_algorithm(overall_rows, alg)
        success = mean_ci(row, "overtake_success_rate")
        elegant = mean_ci(row, "elegant_overtake_rate")
        on_track = mean_ci(row, "on_track_overtake_rate")
        grass = mean_ci(row, "target_grass_rate")
        time = mean_ci(row, "overtake_start_to_complete_time")
        latency = mean_ci(row, "compute_latency_ms")
        rows.append(
            {
                "algorithm": alg,
                "algorithm_label": ALGORITHM_LABELS[alg],
                "family": families[alg],
                "n": row.get("n", ""),
                "success_mean": success[0],
                "success_ci95_low": success[1],
                "success_ci95_high": success[2],
                "elegant_mean": elegant[0],
                "elegant_ci95_low": elegant[1],
                "elegant_ci95_high": elegant[2],
                "on_track_mean": on_track[0],
                "on_track_ci95_low": on_track[1],
                "on_track_ci95_high": on_track[2],
                "grass_mean": grass[0],
                "grass_ci95_low": grass[1],
                "grass_ci95_high": grass[2],
                "completion_time_mean": time[0],
                "completion_time_ci95_low": time[1],
                "completion_time_ci95_high": time[2],
                "latency_ms_mean": latency[0],
                "latency_ms_ci95_low": latency[1],
                "latency_ms_ci95_high": latency[2],
            }
        )
    return rows, fields


def build_paired_table(paired_rows, source_rows):
    fields = [
        "comparison",
        "algorithm",
        "algorithm_label",
        "comparator",
        "comparator_label",
        "metric",
        "metric_label",
        "higher_is_better",
        "improvement_mean",
        "improvement_ci95_low",
        "improvement_ci95_high",
        "n_paired",
        "source",
        "interpretation",
    ]
    comparisons = [
        ("dynamic_full_vs_original_dlc", OURS_FULL, DLC, "Runtime dynamic graph + overtake-aware planning"),
        ("dynamic_safe_vs_original_dlc", OURS_SAFE, DLC, "Safety-oriented dynamic graph planner"),
        ("quality_proposal_vs_original_dlc", QUALITY, DLC, "Quality-guided proposal policy"),
        ("rule_expert_vs_original_dlc", RULE, DLC, "Hand-engineered rule reference"),
    ]
    metric_order = [
        "overtake_success_rate",
        "elegant_overtake_rate",
        "on_track_overtake_rate",
        "overtake_start_to_complete_time",
        "target_grass_rate",
        "compute_latency_ms",
    ]
    rows = []
    for comparison, alg, comparator, interpretation in comparisons:
        for metric in metric_order:
            label, higher, unit = METRICS[metric]
            if comparator == DLC:
                row = paired_lookup(paired_rows, alg, metric)
                rows.append(
                    {
                        "comparison": comparison,
                        "algorithm": alg,
                        "algorithm_label": ALGORITHM_LABELS[alg],
                        "comparator": comparator,
                        "comparator_label": ALGORITHM_LABELS[comparator],
                        "metric": metric,
                        "metric_label": label,
                        "higher_is_better": higher,
                        "improvement_mean": f(row["improvement_vs_dlc_mean"]),
                        "improvement_ci95_low": f(row["improvement_ci95_low"]),
                        "improvement_ci95_high": f(row["improvement_ci95_high"]),
                        "n_paired": row["n_paired"],
                        "source": "confirmatory_paired_tests_vs_dlc.csv",
                        "interpretation": interpretation,
                    }
                )
    # Direct contribution of the safety planner relative to the non-safe dynamic planner.
    for metric in metric_order:
        label, higher, unit = METRICS[metric]
        mean, lo, hi, n = paired_improvement_from_source(source_rows, OURS_SAFE, OURS_FULL, metric, higher)
        rows.append(
            {
                "comparison": "safe_variant_vs_dynamic_full",
                "algorithm": OURS_SAFE,
                "algorithm_label": ALGORITHM_LABELS[OURS_SAFE],
                "comparator": OURS_FULL,
                "comparator_label": ALGORITHM_LABELS[OURS_FULL],
                "metric": metric,
                "metric_label": label,
                "higher_is_better": higher,
                "improvement_mean": mean,
                "improvement_ci95_low": lo,
                "improvement_ci95_high": hi,
                "n_paired": n,
                "source": "online_benchmark_source_data.csv",
                "interpretation": "Effect of the safety-oriented planner weights over the unconstrained dynamic-neighborhood variant.",
            }
        )
    return rows, fields


def build_scenario_table(scenario_rows):
    fields = [
        "benchmark",
        "num_agents",
        "algorithm",
        "algorithm_label",
        "success_mean",
        "success_ci95_low",
        "success_ci95_high",
        "elegant_mean",
        "elegant_ci95_low",
        "elegant_ci95_high",
        "grass_mean",
        "grass_ci95_low",
        "grass_ci95_high",
        "completion_time_mean",
        "completion_time_ci95_low",
        "completion_time_ci95_high",
        "n",
    ]
    stress = [
        ("in_distribution_procedural", 6),
        ("vehicle_count_extrapolation", 8),
        ("monza_external_track", 6),
    ]
    algs = [OURS_SAFE, QUALITY, DLC, "dlc_world_safety", RULE]
    rows = []
    for benchmark, n_agents in stress:
        for alg in algs:
            for row in scenario_rows:
                if row["benchmark"] == benchmark and int(row["num_agents"]) == n_agents and row["algorithm"] == alg:
                    success = mean_ci(row, "overtake_success_rate")
                    elegant = mean_ci(row, "elegant_overtake_rate")
                    grass = mean_ci(row, "target_grass_rate")
                    time = mean_ci(row, "overtake_start_to_complete_time")
                    rows.append(
                        {
                            "benchmark": benchmark,
                            "num_agents": n_agents,
                            "algorithm": alg,
                            "algorithm_label": ALGORITHM_LABELS[alg],
                            "success_mean": success[0],
                            "success_ci95_low": success[1],
                            "success_ci95_high": success[2],
                            "elegant_mean": elegant[0],
                            "elegant_ci95_low": elegant[1],
                            "elegant_ci95_high": elegant[2],
                            "grass_mean": grass[0],
                            "grass_ci95_low": grass[1],
                            "grass_ci95_high": grass[2],
                            "completion_time_mean": time[0],
                            "completion_time_ci95_low": time[1],
                            "completion_time_ci95_high": time[2],
                            "n": row.get("n", ""),
                        }
                    )
                    break
    return rows, fields


def err(mean, lo, hi):
    mean = f(mean)
    lo = f(lo)
    hi = f(hi)
    if mean is None or lo is None or hi is None:
        return [[0.0], [0.0]]
    return [[max(mean - lo, 0.0)], [max(hi - mean, 0.0)]]


def style_ax(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(labelsize=6.3, length=2.5, width=0.7)
    ax.grid(axis="y", color="#E2E7EC", linewidth=0.55, zorder=0)


def add_panel_label(ax, label):
    ax.text(-0.11, 1.06, label, transform=ax.transAxes, fontsize=9, fontweight="bold", ha="left", va="bottom")


def plot_contribution_figure(overall, paired, scenario, out_stem):
    mpl.rcParams.update(
        {
            "font.size": 7,
            "axes.linewidth": 0.7,
            "legend.frameon": False,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
        }
    )
    fig = plt.figure(figsize=(7.2, 6.7), constrained_layout=True)
    gs = fig.add_gridspec(2, 2, width_ratios=[1.04, 0.96], height_ratios=[1.0, 1.02])
    ax_a = fig.add_subplot(gs[0, 0])
    ax_b = fig.add_subplot(gs[0, 1])
    ax_c = fig.add_subplot(gs[1, 0])
    ax_d = fig.add_subplot(gs[1, 1])
    fig.suptitle("Contribution attribution for dynamic-neighborhood DLC world-model overtaking", fontsize=11, fontweight="bold", y=1.01)

    # a: DLC variant family vs proposed family on quality metrics.
    algs_a = [DLC, "dlc_world_balanced", "dlc_world_safety", "dlc_world_fast", OURS_SAFE, QUALITY, RULE]
    metrics_a = [
        ("success_mean", "success_ci95_low", "success_ci95_high", "Success"),
        ("elegant_mean", "elegant_ci95_low", "elegant_ci95_high", "Desirable"),
        ("on_track_mean", "on_track_ci95_low", "on_track_ci95_high", "On-track"),
    ]
    x = np.arange(len(metrics_a))
    width = 0.105
    for idx, alg in enumerate(algs_a):
        row = next(r for r in overall if r["algorithm"] == alg)
        means = [f(row[m[0]]) for m in metrics_a]
        yerr = [
            [max(f(row[m[0]]) - f(row[m[1]]), 0.0) if f(row[m[1]]) is not None else 0.0 for m in metrics_a],
            [max(f(row[m[2]]) - f(row[m[0]]), 0.0) if f(row[m[2]]) is not None else 0.0 for m in metrics_a],
        ]
        offset = (idx - (len(algs_a) - 1) / 2) * width
        ax_a.bar(x + offset, means, width, color=COLORS[alg], edgecolor="white", linewidth=0.35, zorder=3, label=ALGORITHM_LABELS[alg])
        ax_a.errorbar(x + offset, means, yerr=yerr, fmt="none", ecolor="#2F2F2F", elinewidth=0.65, capsize=1.6, zorder=4)
    ax_a.set_xticks(x)
    ax_a.set_xticklabels([m[3] for m in metrics_a])
    ax_a.set_ylim(0, 1.08)
    ax_a.set_ylabel("Rate")
    ax_a.set_title("DLC variants do not recover overtaking quality", fontsize=8)
    ax_a.legend(ncols=2, fontsize=5.6, loc="upper left", bbox_to_anchor=(0.0, 1.02), columnspacing=0.7, handlelength=1.3)
    style_ax(ax_a)
    add_panel_label(ax_a, "a")

    # b: paired improvements over the original DLC baseline.
    metrics_b = ["overtake_success_rate", "elegant_overtake_rate", "on_track_overtake_rate", "target_grass_rate"]
    algs_b = [OURS_FULL, OURS_SAFE, QUALITY]
    labels_b = ["Success", "Desirable", "On-track", "Grass reduction"]
    y = np.arange(len(metrics_b))
    offsets = [-0.22, 0.0, 0.22]
    for idx, alg in enumerate(algs_b):
        xs = []
        lo = []
        hi = []
        for metric in metrics_b:
            row = next(r for r in paired if r["comparison"].endswith("original_dlc") and r["algorithm"] == alg and r["metric"] == metric)
            mean = f(row["improvement_mean"])
            xs.append(mean)
            lo.append(max(mean - f(row["improvement_ci95_low"]), 0.0))
            hi.append(max(f(row["improvement_ci95_high"]) - mean, 0.0))
        ax_b.errorbar(xs, y + offsets[idx], xerr=[lo, hi], fmt="o", ms=4.2, color=COLORS[alg], ecolor=COLORS[alg], capsize=2.0, label=ALGORITHM_LABELS[alg])
    ax_b.axvline(0, color="#333333", linewidth=0.8)
    ax_b.set_yticks(y)
    ax_b.set_yticklabels(labels_b)
    ax_b.set_xlabel("Paired improvement over original DLC")
    ax_b.set_title("Dynamic graph and quality proposals improve different axes", fontsize=8)
    ax_b.set_xlim(-0.05, 0.58)
    style_ax(ax_b)
    add_panel_label(ax_b, "b")
    ax_b.legend(fontsize=5.8, loc="upper right")

    # c: quality-risk-efficiency tradeoff.
    for row in overall:
        alg = row["algorithm"]
        x_val = f(row["grass_mean"])
        y_val = f(row["elegant_mean"])
        latency = f(row["latency_ms_mean"])
        size = 18 + min(max(latency or 1.0, 1.0), 130.0) * 0.42
        marker = "D" if alg in {OURS_SAFE, OURS_FULL, QUALITY} else "o"
        ax_c.scatter(x_val, y_val, s=size, color=COLORS.get(alg, "#999999"), edgecolor="white", linewidth=0.6, marker=marker, zorder=3)
        dx = 0.006 if alg != RULE else -0.075
        dy = 0.012 if alg != DLC else -0.025
        ax_c.text(x_val + dx, y_val + dy, ALGORITHM_LABELS.get(alg, alg), fontsize=5.8)
    ax_c.set_xlabel("Target grass rate (lower is better)")
    ax_c.set_ylabel("Desirable overtaking behavior rate")
    ax_c.set_title("The proposed method moves toward the high-quality, lower-risk region", fontsize=8)
    ax_c.set_xlim(0.52, 0.82)
    ax_c.set_ylim(0.0, 0.60)
    style_ax(ax_c)
    add_panel_label(ax_c, "c")

    # d: scenario-level stress-test decomposition.
    scenarios = [
        ("in_distribution_procedural", 6, "Procedural\n6 cars"),
        ("vehicle_count_extrapolation", 8, "8-car\nextrapolation"),
        ("monza_external_track", 6, "Monza\n6 cars"),
    ]
    algs_d = [OURS_SAFE, QUALITY, DLC, "dlc_world_safety", RULE]
    x = np.arange(len(scenarios))
    width = 0.14
    for idx, alg in enumerate(algs_d):
        means = []
        lows = []
        highs = []
        for benchmark, n_agents, _ in scenarios:
            row = next(r for r in scenario if r["benchmark"] == benchmark and int(r["num_agents"]) == n_agents and r["algorithm"] == alg)
            mean = f(row["elegant_mean"])
            means.append(mean)
            lows.append(max(mean - f(row["elegant_ci95_low"]), 0.0) if f(row["elegant_ci95_low"]) is not None else 0.0)
            highs.append(max(f(row["elegant_ci95_high"]) - mean, 0.0) if f(row["elegant_ci95_high"]) is not None else 0.0)
        offset = (idx - (len(algs_d) - 1) / 2) * width
        ax_d.bar(x + offset, means, width, color=COLORS[alg], edgecolor="white", linewidth=0.35, zorder=3, label=ALGORITHM_LABELS[alg])
        ax_d.errorbar(x + offset, means, yerr=[lows, highs], fmt="none", ecolor="#2F2F2F", elinewidth=0.65, capsize=1.5, zorder=4)
    ax_d.set_xticks(x)
    ax_d.set_xticklabels([item[2] for item in scenarios])
    ax_d.set_ylim(0, 1.03)
    ax_d.set_ylabel("Desirable overtaking behavior rate")
    ax_d.set_title("Stress settings separate planning families", fontsize=8)
    style_ax(ax_d)
    add_panel_label(ax_d, "d")

    for ext, kwargs in {
        "svg": {},
        "pdf": {},
        "png": {"dpi": 450},
        "tiff": {"dpi": 600},
    }.items():
        fig.savefig(f"{out_stem}.{ext}", bbox_inches="tight", **kwargs)
    plt.close(fig)


def build_report(overall, paired, scenario):
    def overall_row(alg):
        return next(r for r in overall if r["algorithm"] == alg)

    def paired_row(comparison, alg, metric):
        return next(r for r in paired if r["comparison"] == comparison and r["algorithm"] == alg and r["metric"] == metric)

    safe = overall_row(OURS_SAFE)
    full = overall_row(OURS_FULL)
    quality = overall_row(QUALITY)
    dlc = overall_row(DLC)
    rule = overall_row(RULE)
    safe_elegant = f(safe["elegant_mean"])
    dlc_elegant = f(dlc["elegant_mean"])
    safe_time_gain = paired_row("dynamic_safe_vs_original_dlc", OURS_SAFE, "overtake_start_to_complete_time")
    safe_grass_gain = paired_row("dynamic_safe_vs_original_dlc", OURS_SAFE, "target_grass_rate")
    safe_vs_full_elegant = paired_row("safe_variant_vs_dynamic_full", OURS_SAFE, "elegant_overtake_rate")
    safe_vs_full_success = paired_row("safe_variant_vs_dynamic_full", OURS_SAFE, "overtake_success_rate")
    quality_success = f(quality["success_mean"])
    quality_elegant = f(quality["elegant_mean"])
    rule_elegant = f(rule["elegant_mean"])

    lines = [
        "# Contribution Attribution and Ablation Evidence",
        "",
        "## 目的",
        "",
        "本材料把冻结的 240-run 确认性在线矩阵重新组织为“创新点贡献归因”证据。它不新增仿真样本，也不替代主结果表；作用是回答审稿人可能提出的三个问题：",
        "",
        "1. 原始 DLC world model 的调参变种是否已经足够？",
        "2. 动态邻域图、超车感知规划、安全权重和质量 proposal 分别改善了哪些指标？",
        "3. 当前方法的收益是否只是速度更快，还是同时体现在on-track/desirable超车质量上？",
        "",
        "## 主要发现",
        "",
        f"- 原始 DLC world model 的Desirable overtaking behavior rate为 {fmt(dlc_elegant)}，v6-safe 动态邻域 DLC 为 {fmt(safe_elegant)}；这说明收益主要不是来自单纯加速，而是来自更好的交互建模与在线规划。",
        f"- v6-safe 相对原始 DLC 的超车开始到完成时间减少 {fmt(safe_time_gain['improvement_mean'], 1)} steps，目标车草地率降低 {fmt(safe_grass_gain['improvement_mean'])}。",
        f"- 安全型 v6-safe 相对非安全型 v6-full 的Desirable overtaking behavior rate变化为 {fmt(safe_vs_full_elegant['improvement_mean'])}，成功率变化为 {fmt(safe_vs_full_success['improvement_mean'])}。这体现了安全权重带来的质量/成功率折中，而不是一个单向支配关系。",
        f"- Quality-proposal DLC 达到 {fmt(quality_success)} 的成功率，但Desirable overtaking behavior rate为 {fmt(quality_elegant)}，低于 v6-safe；它更适合作为 proposal/辅助分支，而不是直接替代主算法。",
        f"- 规则专家的整体Desirable overtaking behavior rate为 {fmt(rule_elegant)}，可作为强手工参照，但它没有 world-model 表征、学习式泛化机制或可微/可扩展规划接口，因此不应被写作当前算法的消融版本。",
        "",
        "## 对 Method/Experiment 写作的建议",
        "",
        "- 在 Method 中把当前算法写成“DLC-style world model + runtime dynamic-neighborhood graph + overtake-aware risk/quality planner”。",
        "- 在 Ablation/Analysis 中把 DLC-balanced、DLC-safety、DLC-fast 作为“原始 DLC world model 的调参变体”，用来证明仅靠速度/风险权重调参无法恢复Desirable overtaking behavior。",
        "- 把 v6-full 与 v6-safe 的比较写成安全权重和风险约束的 trade-off，而不是绝对优劣。",
        "- 把 quality-proposal DLC 写成质量引导 proposal 分支，强调它提高成功率但不能独立解决desirable overtaking behavior quality问题。",
        "- 把规则专家写成 strong rule baseline，避免把它当成学习式 world-model 的消融项。",
        "",
        "## 边界条件",
        "",
        "- 本包只复用确认性矩阵和已有统计表；没有新增随机种子或新赛道。",
        "- 当前证据仍然是仿真证据，不能表述为真实车辆安全验证。",
        "- Monza 仍是单一外部 CSV 赛道；若要扩大 claim，需要更多外部地图或闭源仿真平台交叉验证。",
    ]
    return "\n".join(lines)


def build_legend():
    return """# Figure Legend

**Figure. Contribution attribution for dynamic-neighborhood DLC world-model overtaking.**

**a,** Overall success, desirable overtaking behavior, and on-track overtaking rates for the proposed dynamic-neighborhood DLC variants, the original DLC world model and its tuning variants, quality-proposal DLC, and a rule expert. Bars show means and bootstrap 95% confidence intervals over the frozen confirmatory online matrix. **b,** Paired improvements over the original DLC world model for dynamic DLC, dynamic DLC-safe, and quality-proposal DLC. Positive values indicate better success/quality or lower grass exposure. **c,** Quality-risk-efficiency trade-off across algorithms, plotting desirable overtaking behavior rate against target grass rate; marker area is proportional to online decision latency. **d,** Scenario-level desirable overtaking behavior rates in procedural six-car, eight-car extrapolation, and Monza six-car settings.

All panels are generated from `confirmatory_overall_statistics.csv`, `confirmatory_paired_tests_vs_dlc.csv`, `confirmatory_scenario_statistics.csv`, and `online_benchmark_source_data.csv`.
"""


def main():
    parser = argparse.ArgumentParser(description="Export contribution-attribution and ablation materials for T-ITS dynamic DLC experiments.")
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/tits_ablation_contribution_pack")
    parser.add_argument("--overall", default="outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack/tables/confirmatory_overall_statistics.csv")
    parser.add_argument("--scenario", default="outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack/tables/confirmatory_scenario_statistics.csv")
    parser.add_argument("--paired", default="outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack/tables/confirmatory_paired_tests_vs_dlc.csv")
    parser.add_argument("--source", default="outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    figures_dir = out_dir / "figures"
    tables_dir = out_dir / "tables"
    materials_dir = out_dir / "materials"
    figures_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)
    materials_dir.mkdir(parents=True, exist_ok=True)

    overall_rows = read_csv(args.overall)
    scenario_rows = read_csv(args.scenario)
    paired_rows = read_csv(args.paired)
    source_rows = read_csv(args.source)

    overall_table, overall_fields = build_overall_table(overall_rows)
    paired_table, paired_fields = build_paired_table(paired_rows, source_rows)
    scenario_table, scenario_fields = build_scenario_table(scenario_rows)

    paths = {}
    paths["overall_csv"] = write_csv(tables_dir / "ablation_contribution_overall.csv", overall_table, overall_fields)
    paths["paired_csv"] = write_csv(tables_dir / "ablation_contribution_paired.csv", paired_table, paired_fields)
    paths["scenario_csv"] = write_csv(tables_dir / "ablation_contribution_scenario.csv", scenario_table, scenario_fields)

    figure_stem = figures_dir / "figure_dynamic_dlc_contribution_attribution"
    plot_contribution_figure(overall_table, paired_table, scenario_table, figure_stem)
    for ext in ["svg", "pdf", "png", "tiff"]:
        paths[f"figure_{ext}"] = str(figure_stem.with_suffix(f".{ext}"))

    paths["report_md"] = write_text(materials_dir / "CONTRIBUTION_ATTRIBUTION_REPORT.md", build_report(overall_table, paired_table, scenario_table))
    paths["legend_md"] = write_text(materials_dir / "FIGURE_DYNAMIC_DLC_CONTRIBUTION_LEGEND.md", build_legend())

    export_paths = [Path(path) for path in paths.values()]
    qa = {
        "status": "pass" if all(path.exists() and path.stat().st_size > 0 for path in export_paths) else "check",
        "core_conclusion": "Runtime dynamic-neighborhood graph planning, safety-aware scoring, and quality proposal actions contribute complementary improvements over the original DLC world model.",
        "archetype": "quantitative grid",
        "backend": "Python/matplotlib",
        "source_tables": {
            "overall": args.overall,
            "scenario": args.scenario,
            "paired": args.paired,
            "source": args.source,
        },
        "checks": {
            "all_exports_nonempty": all(path.exists() and path.stat().st_size > 0 for path in export_paths),
            "editable_svg_text": "matplotlib svg.fonttype set to none",
            "pdf_fonttype": "42",
            "statistics_documented": "bootstrap 95% CIs from confirmatory tables plus paired bootstrap for safe-vs-dynamic-full comparisons",
            "no_new_simulation_runs": True,
        },
        "reviewer_risks": [
            "The pack is contribution attribution from existing confirmatory runs, not a new randomized ablation matrix.",
            "Rule expert should be described as a strong hand-engineered reference, not a DLC world-model ablation.",
            "Quality-proposal DLC improves success but does not dominate the safety-oriented dynamic planner on desirable overtaking behavior.",
        ],
    }
    paths["qa_json"] = write_json(materials_dir / "CONTRIBUTION_ATTRIBUTION_QA.json", qa)

    manifest = {
        "status": "complete" if qa["status"] == "pass" else "check",
        "out_dir": str(out_dir),
        "paths": paths,
        "input_tables": qa["source_tables"],
        "table_rows": {
            "overall": len(overall_table),
            "paired": len(paired_table),
            "scenario": len(scenario_table),
        },
    }
    manifest_path = write_json(out_dir / "tits_ablation_contribution_pack_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, "status": manifest["status"], "paths": paths}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
