#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np


OURS = "v6_runtime_dynamic_neighborhood_safe"
DLC = "dlc_world_original"
PRIMARY_METRICS = [
    ("overtake_success_rate", "超车成功率", True, "rate"),
    ("elegant_overtake_rate", "Desirable overtaking behavior rate", True, "rate"),
    ("on_track_overtake_rate", "赛道内超车率", True, "rate"),
    ("overtake_start_to_complete_time", "开始到完成超车时间", False, "steps"),
    ("target_grass_rate", "目标车草地暴露率", False, "rate"),
]
BENCHMARK_LABELS = {
    "in_distribution_procedural": "程序赛道",
    "monza_external_track": "Monza外部赛道",
    "vehicle_count_extrapolation": "8车外推",
}


def configure_matplotlib():
    font_candidates = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.otf",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for font_path in font_candidates:
        if Path(font_path).exists():
            try:
                mpl.font_manager.fontManager.addfont(font_path)
                family = mpl.font_manager.FontProperties(fname=font_path).get_name()
                mpl.rcParams["font.sans-serif"] = [family, "Arial", "DejaVu Sans", "sans-serif"]
                break
            except Exception:
                continue
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "font.size": 8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.linewidth": 0.8,
            "legend.frameon": False,
        }
    )


def read_csv(path):
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")
    return str(path)


def write_json(path, data):
    return write_text(path, json.dumps(data, ensure_ascii=False, indent=2))


def write_csv(path, rows, fields):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return str(path)


def f(value):
    if value in (None, "", "nan", "NaN", "--"):
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


def case_key(row):
    return (
        row.get("_benchmark", ""),
        row.get("num_agents", ""),
        row.get("seed", ""),
        row.get("track_path", ""),
        row.get("traffic_profile", ""),
    )


def scenario_key(row_or_key):
    if isinstance(row_or_key, tuple):
        return row_or_key[0], row_or_key[1]
    return row_or_key.get("_benchmark", ""), row_or_key.get("num_agents", "")


def scenario_label(key):
    benchmark, num_agents = key
    return f"{BENCHMARK_LABELS.get(benchmark, benchmark)} n={num_agents}"


def bootstrap_ci(values, rng, n_boot=5000):
    arr = np.asarray(values, dtype=float)
    if len(arr) == 0:
        return None, None
    if len(arr) == 1:
        return float(arr[0]), float(arr[0])
    idx = rng.integers(0, len(arr), size=(n_boot, len(arr)))
    means = arr[idx].mean(axis=1)
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def build_case_index(rows):
    by_case = defaultdict(dict)
    for row in rows:
        by_case[case_key(row)][row["algorithm"]] = row
    return by_case


def build_design_rows(by_case):
    grouped = defaultdict(list)
    for key in by_case:
        grouped[scenario_key(key)].append(key)
    rows = []
    for key, cases in sorted(grouped.items()):
        seeds = sorted({case[2] for case in cases}, key=lambda x: int(x) if str(x).isdigit() else str(x))
        alg_counts = [len(by_case[case]) for case in cases]
        rows.append(
            {
                "benchmark": key[0],
                "benchmark_label": BENCHMARK_LABELS.get(key[0], key[0]),
                "num_agents": key[1],
                "case_count": len(cases),
                "seed_count": len(seeds),
                "seeds": ",".join(seeds),
                "min_algorithms_per_case": min(alg_counts),
                "max_algorithms_per_case": max(alg_counts),
                "matched_complete": min(alg_counts) == max(alg_counts) == 8,
            }
        )
    return rows


def paired_deltas(by_case, metric, higher_is_better):
    rows = []
    for key, algorithms in sorted(by_case.items()):
        if OURS not in algorithms or DLC not in algorithms:
            continue
        ours = f(algorithms[OURS].get(metric))
        dlc = f(algorithms[DLC].get(metric))
        if ours is None or dlc is None:
            continue
        delta = ours - dlc if higher_is_better else dlc - ours
        rows.append(
            {
                "case_id": "/".join([key[0], f"n{key[1]}", f"seed{key[2]}"]),
                "benchmark": key[0],
                "num_agents": key[1],
                "seed": key[2],
                "metric": metric,
                "ours_value": ours,
                "dlc_value": dlc,
                "directional_improvement": delta,
                "win": delta > 0,
                "loss": delta < 0,
                "tie": delta == 0,
            }
        )
    return rows


def summarize_primary(by_case, rng):
    metric_rows = []
    delta_rows = []
    scenario_rows = []
    leave_rows = []
    for metric, metric_label, higher, unit in PRIMARY_METRICS:
        rows = paired_deltas(by_case, metric, higher)
        delta_rows.extend(rows)
        deltas = [row["directional_improvement"] for row in rows]
        ci_low, ci_high = bootstrap_ci(deltas, rng)
        scenario_to_values = defaultdict(list)
        for row in rows:
            scenario_to_values[(row["benchmark"], row["num_agents"])].append(row["directional_improvement"])
        scenario_means = [float(np.mean(values)) for values in scenario_to_values.values() if values]
        for key, values in sorted(scenario_to_values.items()):
            scenario_rows.append(
                {
                    "metric": metric,
                    "metric_label": metric_label,
                    "benchmark": key[0],
                    "benchmark_label": BENCHMARK_LABELS.get(key[0], key[0]),
                    "num_agents": key[1],
                    "n_paired": len(values),
                    "mean_directional_improvement": float(np.mean(values)),
                    "positive_cases": int(np.sum(np.asarray(values) > 0)),
                    "negative_cases": int(np.sum(np.asarray(values) < 0)),
                    "zero_cases": int(np.sum(np.asarray(values) == 0)),
                }
            )
        for key in sorted(scenario_to_values):
            rest = [
                value
                for other_key, values in scenario_to_values.items()
                if other_key != key
                for value in values
            ]
            leave_rows.append(
                {
                    "metric": metric,
                    "metric_label": metric_label,
                    "left_out_scenario": scenario_label(key),
                    "n_remaining": len(rest),
                    "mean_directional_improvement": float(np.mean(rest)) if rest else "",
                    "sign_preserved": bool(rest and float(np.mean(rest)) > 0),
                }
            )
        metric_rows.append(
            {
                "metric": metric,
                "metric_label": metric_label,
                "unit": unit,
                "higher_is_better": higher,
                "n_paired": len(deltas),
                "mean_directional_improvement": float(np.mean(deltas)) if deltas else "",
                "bootstrap_ci95_low": ci_low if ci_low is not None else "",
                "bootstrap_ci95_high": ci_high if ci_high is not None else "",
                "ci_width": (ci_high - ci_low) if ci_low is not None and ci_high is not None else "",
                "positive_cases": int(np.sum(np.asarray(deltas) > 0)) if deltas else 0,
                "negative_cases": int(np.sum(np.asarray(deltas) < 0)) if deltas else 0,
                "zero_cases": int(np.sum(np.asarray(deltas) == 0)) if deltas else 0,
                "scenario_positive_mean_count": int(np.sum(np.asarray(scenario_means) > 0)) if scenario_means else 0,
                "scenario_count": len(scenario_means),
                "leave_one_scenario_min": min([row["mean_directional_improvement"] for row in leave_rows if row["metric"] == metric] or [0]),
                "leave_one_scenario_max": max([row["mean_directional_improvement"] for row in leave_rows if row["metric"] == metric] or [0]),
                "interpretation": "positive values favor v6-safe over original DLC after applying the metric direction",
            }
        )
    return metric_rows, delta_rows, scenario_rows, leave_rows


def build_case_influence_rows(metric_rows, delta_rows):
    by_metric = defaultdict(list)
    for row in delta_rows:
        by_metric[row["metric"]].append(row)
    metric_mean = {row["metric"]: float(row["mean_directional_improvement"]) for row in metric_rows}
    metric_label = {row["metric"]: row["metric_label"] for row in metric_rows}
    rows = []
    for metric, values in by_metric.items():
        full_mean = metric_mean.get(metric)
        if full_mean is None:
            continue
        for row in values:
            rest = [item["directional_improvement"] for item in values if item["case_id"] != row["case_id"]]
            leave_mean = float(np.mean(rest)) if rest else None
            influence = None if leave_mean is None else leave_mean - full_mean
            rows.append(
                {
                    "case_id": row["case_id"],
                    "benchmark": row["benchmark"],
                    "num_agents": row["num_agents"],
                    "seed": row["seed"],
                    "metric": metric,
                    "metric_label": metric_label.get(metric, metric),
                    "case_directional_improvement": row["directional_improvement"],
                    "full_mean_directional_improvement": full_mean,
                    "leave_one_case_mean": leave_mean,
                    "influence_on_mean": influence,
                    "abs_influence_on_mean": abs(influence) if influence is not None else None,
                    "relative_abs_influence_on_mean": (abs(influence) / abs(full_mean)) if influence is not None and full_mean not in (None, 0) else None,
                    "sign_preserved": bool(leave_mean is not None and leave_mean > 0),
                    "case_favors": "v6-safe" if row["directional_improvement"] > 0 else ("original DLC" if row["directional_improvement"] < 0 else "tie"),
                }
            )
    rows.sort(key=lambda item: (item["metric"], -float(item["abs_influence_on_mean"] or 0), item["case_id"]))
    rank_by_metric = defaultdict(int)
    for row in rows:
        rank_by_metric[row["metric"]] += 1
        row["influence_rank_within_metric"] = rank_by_metric[row["metric"]]
    return rows


def build_case_influence_summary(influence_rows):
    grouped = defaultdict(list)
    for row in influence_rows:
        grouped[row["case_id"]].append(row)
    rows = []
    for case_id, values in sorted(grouped.items()):
        abs_values = [float(row["abs_influence_on_mean"] or 0) for row in values]
        rel_values = [float(row["relative_abs_influence_on_mean"] or 0) for row in values]
        max_row = max(values, key=lambda row: float(row["relative_abs_influence_on_mean"] or 0))
        rows.append(
            {
                "case_id": case_id,
                "benchmark": max_row["benchmark"],
                "num_agents": max_row["num_agents"],
                "seed": max_row["seed"],
                "metric_count": len(values),
                "mean_abs_influence": float(np.mean(abs_values)) if abs_values else 0.0,
                "max_abs_influence": float(max(abs_values)) if abs_values else 0.0,
                "mean_relative_abs_influence": float(np.mean(rel_values)) if rel_values else 0.0,
                "max_relative_abs_influence": float(max(rel_values)) if rel_values else 0.0,
                "max_influence_metric": max_row["metric"],
                "max_influence_metric_label": max_row["metric_label"],
                "sign_preserved_all_metrics": all(bool(row["sign_preserved"]) for row in values),
                "negative_case_count": sum(1 for row in values if row["case_favors"] == "original DLC"),
                "interpretation": (
                    "high relative influence case; report as robustness boundary"
                    if (float(max(rel_values)) >= 0.10 or not all(bool(row["sign_preserved"]) for row in values))
                    else "low or moderate relative influence under leave-one-case audit"
                ),
            }
        )
    rows.sort(key=lambda row: (-float(row["max_relative_abs_influence"]), row["case_id"]))
    for idx, row in enumerate(rows, start=1):
        row["overall_influence_rank"] = idx
    return rows


def build_review_risk_rows(metric_rows, scenario_rows):
    rows = []
    for row in metric_rows:
        if int(row["negative_cases"]) > 0:
            rows.append(
                {
                    "risk_id": f"R_{row['metric']}_negative_cases",
                    "metric": row["metric"],
                    "severity": "medium",
                    "evidence": f"{row['negative_cases']} paired cases favor original DLC for this metric.",
                    "recommended_wording": "Report mean improvement with paired win/loss counts; avoid claiming uniform improvement.",
                }
            )
        if int(row["n_paired"]) < 30:
            rows.append(
                {
                    "risk_id": f"R_{row['metric']}_conditional_n",
                    "metric": row["metric"],
                    "severity": "medium",
                    "evidence": f"Metric has n={row['n_paired']} paired cases because it is defined only when both algorithms have completion-time values.",
                    "recommended_wording": "State the conditional n explicitly for completion-time analyses.",
                }
            )
    weak_scenarios = [
        row
        for row in scenario_rows
        if row["metric"] in {"overtake_success_rate", "elegant_overtake_rate", "on_track_overtake_rate"}
        and float(row["mean_directional_improvement"]) <= 0
    ]
    for row in weak_scenarios:
        rows.append(
            {
                "risk_id": f"R_{row['metric']}_{row['benchmark']}_n{row['num_agents']}",
                "metric": row["metric"],
                "severity": "medium",
                "evidence": f"{scenario_label((row['benchmark'], row['num_agents']))} has mean directional improvement {fmt(row['mean_directional_improvement'])}.",
                "recommended_wording": "Describe scenario-level heterogeneity; do not imply every scenario improves equally.",
            }
        )
    return rows


def build_sample_size_boundary_rows(summary, metric_rows):
    completion_time_row = next((row for row in metric_rows if row["metric"] == "overtake_start_to_complete_time"), {})
    completion_n = completion_time_row.get("n_paired", "NA")
    return [
        {
            "item": "matched_case_design",
            "evidence": f"{summary['case_count']} matched cases, {summary['source_rows']} algorithm-runs, and 8 algorithms per case.",
            "reviewer_ready_wording": "The primary comparison uses matched case-level contrasts so that seed, track, vehicle count and traffic profile are held fixed across algorithms.",
            "boundary": "This supports paired inference within the frozen simulator matrix, not population-level real-road generalization.",
        },
        {
            "item": "scenario_cell_replication",
            "evidence": f"{summary['scenario_cell_count']} scenario cells with five seeds per cell in the frozen matrix.",
            "reviewer_ready_wording": "Scenario-level tables expose heterogeneity instead of pooling all cases as if they were exchangeable road scenes.",
            "boundary": "Five seeds per scenario cell are adequate for a confirmatory simulator benchmark but remain limited for rare-event claims.",
        },
        {
            "item": "conditional_completion_time",
            "evidence": f"Overtake start-to-completion time has n={completion_n} paired cases because both algorithms must complete the event.",
            "reviewer_ready_wording": "Completion-time results are reported with the conditional paired sample size and should be interpreted together with success metrics.",
            "boundary": "Do not compare completion time as if all 30 cases produced valid paired completion times.",
        },
        {
            "item": "descriptive_power_boundary",
            "evidence": "Bootstrap intervals, win/tie/loss counts, scenario heterogeneity, and leave-one-case influence are computed from the frozen 30-case matrix.",
            "reviewer_ready_wording": "The audit is a descriptive design-adequacy and stability analysis; Holm-adjusted hypothesis testing is reported in the statistical analysis pack.",
            "boundary": "It is not an a priori prospective power analysis and does not define a preregistered minimum detectable effect.",
        },
    ]


def plot_case_influence_figure(out_base, influence_rows, summary_rows):
    configure_matplotlib()
    fig, axes = plt.subplots(1, 2, figsize=(7.8, 3.7), constrained_layout=True)

    def compact_case_label(case_id):
        parts = case_id.split("/")
        if len(parts) != 3:
            return case_id
        bench, n_part, seed_part = parts
        if bench == "in_distribution_procedural":
            prefix = "proc"
        elif bench == "monza_external_track":
            prefix = "monza"
        elif bench == "vehicle_count_extrapolation":
            prefix = "n8-extra"
        else:
            prefix = bench[:8]
        return f"{prefix} {n_part} {seed_part.replace('seed', 's')}"

    ax = axes[0]
    top_cases = summary_rows[:12]
    labels = [compact_case_label(row["case_id"]) for row in top_cases]
    values = [float(row["max_relative_abs_influence"]) for row in top_cases]
    colors = ["#B45F06" if not row["sign_preserved_all_metrics"] else "#5B7FA6" for row in top_cases]
    ypos = np.arange(len(top_cases))
    ax.barh(ypos, values, color=colors)
    ax.set_yticks(ypos)
    ax.set_yticklabels(labels, fontsize=7)
    ax.invert_yaxis()
    ax.set_xlabel("最大相对影响量")
    ax.set_title("a  影响度最高的case")
    for i, value in enumerate(values):
        ax.text(value + 0.003, i, f"{value:.2f}", va="center", fontsize=6)

    ax = axes[1]
    metrics = []
    min_values = []
    max_values = []
    full_values = []
    for metric in [item[0] for item in PRIMARY_METRICS]:
        subset = [row for row in influence_rows if row["metric"] == metric]
        if not subset:
            continue
        full_mean = float(subset[0]["full_mean_directional_improvement"])
        denom = abs(full_mean) if full_mean != 0 else 1.0
        metrics.append(subset[0]["metric_label"])
        min_values.append(min(float(row["leave_one_case_mean"]) / denom for row in subset))
        max_values.append(max(float(row["leave_one_case_mean"]) / denom for row in subset))
        full_values.append(full_mean / denom)
    y = np.arange(len(metrics))
    ax.axvline(1, color="#777777", lw=0.8)
    for yi, lo, hi, full in zip(y, min_values, max_values, full_values):
        ax.plot([lo, hi], [yi, yi], color="#8BB3D9", lw=4, solid_capstyle="round")
        ax.scatter([full], [yi], color="#145DA0", s=24, zorder=3)
    ax.set_yticks(y)
    ax.set_yticklabels(metrics)
    ax.invert_yaxis()
    ax.set_xlabel("移除任一case后的主效应比例")
    ax.set_title("b  主指标 leave-one-case 稳定性")

    for suffix, kwargs in {
        "svg": {},
        "pdf": {},
        "png": {"dpi": 300},
        "tiff": {"dpi": 600},
    }.items():
        fig.savefig(f"{out_base}.{suffix}", bbox_inches="tight", **kwargs)
    plt.close(fig)


def plot_design_figure(out_base, design_rows, metric_rows, scenario_rows, delta_rows):
    configure_matplotlib()
    fig = plt.figure(figsize=(7.2, 5.6), constrained_layout=True)
    gs = fig.add_gridspec(2, 2)
    ax_a = fig.add_subplot(gs[0, 0])
    ax_b = fig.add_subplot(gs[0, 1])
    ax_c = fig.add_subplot(gs[1, 0])
    ax_d = fig.add_subplot(gs[1, 1])

    scenario_names = [f"{row['benchmark_label']} n={row['num_agents']}" for row in design_rows]
    case_counts = [int(row["case_count"]) for row in design_rows]
    ypos_a = np.arange(len(case_counts))
    ax_a.barh(ypos_a, case_counts, color="#5B7FA6", height=0.62)
    ax_a.set_yticks(ypos_a)
    ax_a.set_yticklabels(scenario_names)
    ax_a.invert_yaxis()
    ax_a.set_xlabel("case数量")
    ax_a.set_title("a  冻结benchmark覆盖")
    for i, value in enumerate(case_counts):
        ax_a.text(value + 0.08, i, str(value), ha="left", va="center", fontsize=7)
    ax_a.set_xlim(0, max(case_counts) + 1)

    metric_labels = [row["metric_label"] for row in metric_rows]
    def plot_scale(row):
        value = float(row["mean_directional_improvement"])
        low = float(row["bootstrap_ci95_low"])
        high = float(row["bootstrap_ci95_high"])
        if row["unit"] == "rate":
            return value * 100.0, low * 100.0, high * 100.0
        return value / 10.0, low / 10.0, high / 10.0

    scaled = [plot_scale(row) for row in metric_rows]
    means = np.array([item[0] for item in scaled])
    lows = np.array([item[1] for item in scaled])
    highs = np.array([item[2] for item in scaled])
    y = np.arange(len(metric_rows))
    ax_b.axvline(0, color="#777777", lw=0.8)
    ax_b.errorbar(means, y, xerr=[means - lows, highs - means], fmt="o", color="#145DA0", ecolor="#8BB3D9", capsize=2.5)
    ax_b.set_yticks(y)
    ax_b.set_yticklabels(metric_labels)
    ax_b.invert_yaxis()
    ax_b.set_xlabel("可视化改善尺度（率=百分点，时间=10步）")
    ax_b.set_title("b  主指标配对改善与95% CI")
    for x_value, y_value, row in zip(means, y, metric_rows):
        raw = float(row["mean_directional_improvement"])
        label = f"{raw * 100:.1f}pp" if row["unit"] == "rate" else f"{raw:.0f}步"
        ax_b.text(x_value + max(1.0, abs(x_value) * 0.04), y_value, label, va="center", fontsize=7)

    wins = np.array([int(row["positive_cases"]) for row in metric_rows])
    losses = np.array([int(row["negative_cases"]) for row in metric_rows])
    ties = np.array([int(row["zero_cases"]) for row in metric_rows])
    ax_c.barh(y, wins, color="#3B8E72", label="v6-safe更好")
    ax_c.barh(y, ties, left=wins, color="#C7C7C7", label="持平")
    ax_c.barh(y, losses, left=wins + ties, color="#C85C5C", label="DLC更好")
    ax_c.set_yticks(y)
    ax_c.set_yticklabels(metric_labels)
    ax_c.invert_yaxis()
    ax_c.set_xlabel("配对case数量")
    ax_c.set_title("c  case级胜/平/负")
    ax_c.legend(loc="lower right", fontsize=7)

    plot_metrics = ["overtake_success_rate", "elegant_overtake_rate", "target_grass_rate"]
    colors = {"overtake_success_rate": "#145DA0", "elegant_overtake_rate": "#3B8E72", "target_grass_rate": "#B45F06"}
    offsets = np.linspace(-0.18, 0.18, len(plot_metrics))
    scenarios = sorted({(row["benchmark"], row["num_agents"]) for row in scenario_rows})
    scenario_positions = {scenario: i for i, scenario in enumerate(scenarios)}
    for offset, metric in zip(offsets, plot_metrics):
        subset = [row for row in scenario_rows if row["metric"] == metric]
        ys = [scenario_positions[(row["benchmark"], row["num_agents"])] + offset for row in subset]
        xs = [float(row["mean_directional_improvement"]) for row in subset]
        label = next(row["metric_label"] for row in subset)
        ax_d.scatter(xs, ys, s=28, color=colors[metric], label=label)
    ax_d.axvline(0, color="#777777", lw=0.8)
    ax_d.set_yticks(range(len(scenarios)))
    ax_d.set_yticklabels([scenario_label(key) for key in scenarios])
    ax_d.invert_yaxis()
    ax_d.set_xlabel("场景内平均改善量")
    ax_d.set_title("d  场景异质性")
    ax_d.legend(fontsize=7, loc="best")

    for suffix, kwargs in {
        "svg": {},
        "pdf": {},
        "png": {"dpi": 300},
        "tiff": {"dpi": 600},
    }.items():
        fig.savefig(f"{out_base}.{suffix}", bbox_inches="tight", **kwargs)
    plt.close(fig)


def build_markdown(report):
    summary = report["summary"]
    lines = [
        "# T-ITS Experimental Design, Power and Stability Audit",
        "",
        "该审计回答审稿人可能提出的三个问题：确认性矩阵是否为完整 matched-case 设计，主指标改善是否由少数场景/seed 支撑，以及哪些统计结论需要在论文中保守表述。它复用 frozen source data，不新增仿真运行。",
        "",
        "## Summary",
        "",
    ]
    for key, value in summary.items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Primary Metric Stability",
            "",
            "| Metric | n paired | Mean directional improvement | 95% CI | Win/Tie/Loss | Scenario positive means | Leave-one-scenario range |",
            "|---|---:|---:|---|---|---|---|",
        ]
    )
    for row in report["metric_rows"]:
        lines.append(
            f"| {row['metric_label']} | {row['n_paired']} | {fmt(row['mean_directional_improvement'])} | [{fmt(row['bootstrap_ci95_low'])}, {fmt(row['bootstrap_ci95_high'])}] | {row['positive_cases']}/{row['zero_cases']}/{row['negative_cases']} | {row['scenario_positive_mean_count']}/{row['scenario_count']} | [{fmt(row['leave_one_scenario_min'])}, {fmt(row['leave_one_scenario_max'])}] |"
        )
    lines.extend(
        [
            "",
            "## Leave-One-Case Influence",
            "",
            "该部分逐个移除一个 matched case 后重算主指标平均改善，用于检查结论是否被单个 seed/case 主导。",
            "",
            "| Rank | Case | Max relative influence | Max raw influence | Metric | Sign preserved all metrics | Interpretation |",
            "|---:|---|---:|---:|---|---|---|",
        ]
    )
    for row in report["case_influence_summary_rows"][:10]:
        lines.append(
            f"| {row['overall_influence_rank']} | `{row['case_id']}` | {fmt(row['max_relative_abs_influence'])} | {fmt(row['max_abs_influence'])} | {row['max_influence_metric_label']} | {row['sign_preserved_all_metrics']} | {row['interpretation']} |"
        )
    lines.extend(["", "## Design Coverage", "", "| Benchmark | n | Cases | Seeds | Algorithms per case | Matched complete |", "|---|---:|---:|---|---|---|"])
    for row in report["design_rows"]:
        lines.append(
            f"| {row['benchmark_label']} | {row['num_agents']} | {row['case_count']} | {row['seeds']} | {row['min_algorithms_per_case']}-{row['max_algorithms_per_case']} | {row['matched_complete']} |"
        )
    lines.extend(
        [
            "",
            "## Sample-Size and Power Wording Boundary",
            "",
            "| Item | Evidence | Reviewer-ready wording | Boundary |",
            "|---|---|---|---|",
        ]
    )
    for row in report["sample_size_boundary_rows"]:
        lines.append(
            f"| {row['item']} | {row['evidence']} | {row['reviewer_ready_wording']} | {row['boundary']} |"
        )
    lines.extend(["", "## Reviewer-Risk Notes", ""])
    if not report["risk_rows"]:
        lines.append("No additional design-stability risks were found.")
    else:
        for row in report["risk_rows"]:
            lines.append(f"- **{row['risk_id']}** ({row['severity']}): {row['evidence']} {row['recommended_wording']}")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `directional_improvement` 已按指标方向归一化，正值表示 v6-safe 优于原始 DLC。",
            "- 完成耗时只在两个算法均存在超车完成时间时进入配对分析，因此 n 小于 30；该条件样本数必须在正文中显式报告。",
            "- 该 `Power` audit 的含义是 design adequacy and stability，不是事前 prospective power analysis；不能写成已预注册最小可检测效应或真实道路统计功效。",
            "- 场景异质性显示 n=4 程序赛道对成功/desirable behavior指标贡献较弱，因此论文应写成“总体 benchmark 改善且存在场景差异”，不要写成所有场景均匀提升。",
            "- leave-one-case 影响度用于识别最敏感的 seed/case；若移除任一 case 后主指标方向仍为正，可以作为“不是单个 case 驱动”的补充证据，但不能替代更多随机种子或外部赛道。",
            "- 该审计不替代新增外部赛道或更高密度交通实验；它只是证明当前 frozen matrix 的设计完整性和统计报告边界。",
            "",
            "## Regeneration Command",
            "",
            "```bash",
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_experimental_design_power_audit.py --out-dir outputs/tits_dynamic_graph/tits_experimental_design_power_audit",
            "```",
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Export experimental design, power, and stability audit for the T-ITS package.")
    parser.add_argument("--source-csv", default="outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv")
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/tits_experimental_design_power_audit")
    parser.add_argument("--bootstrap", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=20260624)
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    materials = out_dir / "materials"
    tables = out_dir / "tables"
    figures = out_dir / "figures"
    for path in (materials, tables, figures):
        path.mkdir(parents=True, exist_ok=True)

    source_rows = read_csv(args.source_csv)
    by_case = build_case_index(source_rows)
    design_rows = build_design_rows(by_case)
    rng = np.random.default_rng(args.seed)
    metric_rows, delta_rows, scenario_rows, leave_rows = summarize_primary(by_case, rng)
    influence_rows = build_case_influence_rows(metric_rows, delta_rows)
    influence_summary_rows = build_case_influence_summary(influence_rows)
    risk_rows = build_review_risk_rows(metric_rows, scenario_rows)

    all_case_alg_counts = [len(algorithms) for algorithms in by_case.values()]
    checks = {
        "source_rows_240": len(source_rows) == 240,
        "case_count_30": len(by_case) == 30,
        "all_cases_have_8_algorithms": bool(all_case_alg_counts and min(all_case_alg_counts) == max(all_case_alg_counts) == 8),
        "six_scenario_cells": len(design_rows) == 6,
        "all_primary_metrics_favor_v6safe_on_mean": all(float(row["mean_directional_improvement"]) > 0 for row in metric_rows),
        "all_primary_metrics_have_more_wins_than_losses": all(int(row["positive_cases"]) > int(row["negative_cases"]) for row in metric_rows),
        "completion_time_conditional_n_reported": any(row["metric"] == "overtake_start_to_complete_time" and int(row["n_paired"]) < 30 for row in metric_rows),
        "leave_one_case_preserves_all_primary_metric_signs": all(bool(row["sign_preserved"]) for row in influence_rows),
    }
    status = "pass" if all(value for key, value in checks.items() if key != "completion_time_conditional_n_reported") else "review_required"
    summary = {
        "status": status,
        "source_rows": len(source_rows),
        "case_count": len(by_case),
        "algorithm_count_per_case_min": min(all_case_alg_counts) if all_case_alg_counts else 0,
        "algorithm_count_per_case_max": max(all_case_alg_counts) if all_case_alg_counts else 0,
        "scenario_cell_count": len(design_rows),
        "primary_metric_count": len(metric_rows),
        "bootstrap_replicates": args.bootstrap,
        "risk_note_count": len(risk_rows),
        "leave_one_case_rows": len(influence_rows),
        "max_case_abs_influence": max([float(row["max_abs_influence"]) for row in influence_summary_rows] or [0.0]),
        "max_case_relative_abs_influence": max([float(row["max_relative_abs_influence"]) for row in influence_summary_rows] or [0.0]),
        "figure_archetype": "quantitative grid",
        "backend": "Python/matplotlib",
    }
    sample_size_boundary_rows = build_sample_size_boundary_rows(summary, metric_rows)
    report = {
        "status": status,
        "summary": summary,
        "checks": checks,
        "design_rows": design_rows,
        "metric_rows": metric_rows,
        "scenario_rows": scenario_rows,
        "leave_one_scenario_rows": leave_rows,
        "case_influence_rows": influence_rows,
        "case_influence_summary_rows": influence_summary_rows,
        "sample_size_boundary_rows": sample_size_boundary_rows,
        "risk_rows": risk_rows,
        "figure_contract": {
            "core_conclusion": "The frozen 30-case matched benchmark supports the main v6-safe versus original-DLC claim while exposing scenario-level heterogeneity that should constrain manuscript wording.",
            "evidence_logic": "coverage table + paired improvement intervals + case win/loss counts + scenario heterogeneity",
            "export_formats": ["svg", "pdf", "png", "tiff"],
            "source_data": args.source_csv,
        },
    }

    figure_base = figures / "figure_experimental_design_power_audit_cn"
    plot_design_figure(figure_base, design_rows, metric_rows, scenario_rows, delta_rows)
    influence_figure_base = figures / "figure_case_influence_audit_cn"
    plot_case_influence_figure(influence_figure_base, influence_rows, influence_summary_rows)

    paths = {
        "audit_md": write_text(materials / "EXPERIMENTAL_DESIGN_POWER_AUDIT.md", build_markdown(report)),
        "audit_json": write_json(materials / "EXPERIMENTAL_DESIGN_POWER_AUDIT.json", report),
        "design_csv": write_csv(tables / "experimental_design_coverage.csv", design_rows, ["benchmark", "benchmark_label", "num_agents", "case_count", "seed_count", "seeds", "min_algorithms_per_case", "max_algorithms_per_case", "matched_complete"]),
        "metric_csv": write_csv(tables / "primary_metric_stability.csv", metric_rows, ["metric", "metric_label", "unit", "higher_is_better", "n_paired", "mean_directional_improvement", "bootstrap_ci95_low", "bootstrap_ci95_high", "ci_width", "positive_cases", "negative_cases", "zero_cases", "scenario_positive_mean_count", "scenario_count", "leave_one_scenario_min", "leave_one_scenario_max", "interpretation"]),
        "delta_csv": write_csv(tables / "case_level_directional_deltas.csv", delta_rows, ["case_id", "benchmark", "num_agents", "seed", "metric", "ours_value", "dlc_value", "directional_improvement", "win", "loss", "tie"]),
        "scenario_csv": write_csv(tables / "scenario_level_stability.csv", scenario_rows, ["metric", "metric_label", "benchmark", "benchmark_label", "num_agents", "n_paired", "mean_directional_improvement", "positive_cases", "negative_cases", "zero_cases"]),
        "leave_one_csv": write_csv(tables / "leave_one_scenario_stability.csv", leave_rows, ["metric", "metric_label", "left_out_scenario", "n_remaining", "mean_directional_improvement", "sign_preserved"]),
        "leave_one_case_csv": write_csv(tables / "leave_one_case_influence.csv", influence_rows, ["case_id", "benchmark", "num_agents", "seed", "metric", "metric_label", "case_directional_improvement", "full_mean_directional_improvement", "leave_one_case_mean", "influence_on_mean", "abs_influence_on_mean", "relative_abs_influence_on_mean", "sign_preserved", "case_favors", "influence_rank_within_metric"]),
        "case_influence_summary_csv": write_csv(tables / "case_influence_summary.csv", influence_summary_rows, ["overall_influence_rank", "case_id", "benchmark", "num_agents", "seed", "metric_count", "mean_abs_influence", "max_abs_influence", "mean_relative_abs_influence", "max_relative_abs_influence", "max_influence_metric", "max_influence_metric_label", "sign_preserved_all_metrics", "negative_case_count", "interpretation"]),
        "sample_size_boundary_csv": write_csv(tables / "sample_size_and_power_wording_boundary.csv", sample_size_boundary_rows, ["item", "evidence", "reviewer_ready_wording", "boundary"]),
        "risk_csv": write_csv(tables / "experimental_design_reviewer_risks.csv", risk_rows, ["risk_id", "metric", "severity", "evidence", "recommended_wording"]),
        "figure_svg": str(figure_base) + ".svg",
        "figure_pdf": str(figure_base) + ".pdf",
        "figure_png": str(figure_base) + ".png",
        "figure_tiff": str(figure_base) + ".tiff",
        "case_influence_figure_svg": str(influence_figure_base) + ".svg",
        "case_influence_figure_pdf": str(influence_figure_base) + ".pdf",
        "case_influence_figure_png": str(influence_figure_base) + ".png",
        "case_influence_figure_tiff": str(influence_figure_base) + ".tiff",
    }
    qa = {
        "status": status,
        "checks": checks,
        "all_exports_nonempty": all(Path(paths[key]).exists() and Path(paths[key]).stat().st_size > 0 for key in ["figure_svg", "figure_pdf", "figure_png", "figure_tiff", "case_influence_figure_svg", "case_influence_figure_pdf", "case_influence_figure_png", "case_influence_figure_tiff"]),
        "editable_svg_text": "matplotlib svg.fonttype set to none",
        "pdf_fonttype": "42",
        "no_new_simulation_runs": True,
        "descriptive_power_boundary_written": any(row["item"] == "descriptive_power_boundary" for row in sample_size_boundary_rows),
        "statistics_note": "Bootstrap CIs are descriptive stability intervals over paired case deltas; Holm-adjusted hypothesis testing remains in the statistical analysis pack.",
    }
    paths["qa_json"] = write_json(materials / "EXPERIMENTAL_DESIGN_POWER_QA.json", qa)
    manifest = {
        "status": status,
        "out_dir": args.out_dir,
        "source_csv": args.source_csv,
        "summary": summary,
        "paths": paths,
    }
    manifest_path = write_json(out_dir / "tits_experimental_design_power_audit_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, "status": status, "summary": summary}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
