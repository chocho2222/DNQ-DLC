#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import math
from collections import defaultdict
from pathlib import Path

import numpy as np


ALGORITHM_ORDER = [
    "quality_aux_dlc_world_v4",
    "quality_aux_dlc_world_v5_soft025",
    "quality_aux_dlc_world_v5_soft050",
    "quality_aux_dlc_world_v5_gate025",
    "quality_guided_dlc_world_v3",
    "quality_proposal_dlc_world_v2",
    "quality_proposal_dlc_world_v1",
    "ours_dynamic_graph_dlc_world",
    "quality_graph_bc_v2",
    "quality_graph_bc_v1",
    "graph_bc_dynamic",
    "dlc_world_original",
]

ALGORITHM_LABELS = {
    "quality_aux_dlc_world_v4": "质量辅助DLC-v4",
    "quality_aux_dlc_world_v5_soft025": "v5-soft025",
    "quality_aux_dlc_world_v5_soft050": "v5-soft050",
    "quality_aux_dlc_world_v5_gate025": "v5-gate025",
    "quality_guided_dlc_world_v3": "质量引导DLC-v3",
    "quality_proposal_dlc_world_v2": "Proposal-DLC-v2",
    "quality_proposal_dlc_world_v1": "Proposal-DLC-v1",
    "ours_dynamic_graph_dlc_world": "本文方法",
    "quality_graph_bc_v2": "质量图BC-v2",
    "quality_graph_bc_v1": "质量图BC-v1",
    "graph_bc_dynamic": "图BC",
    "dlc_world_original": "DLC世界模型",
}

METRICS = [
    ("overtake_success_rate", "超车成功率", True),
    ("overtake_count", "超车次数", True),
    ("on_track_overtake_rate", "赛道内超车率", True),
    ("elegant_overtake_rate", "Desirable overtaking behavior rate", True),
    ("overtake_window_grass_rate_mean", "超车窗口草地率", False),
    ("target_grass_rate", "全程草地率", False),
    ("grass_recovery_time_mean", "草地后恢复时间", False),
    ("rank_gain", "名次提升", True),
    ("target_progress", "目标车进度", True),
    ("overtake_start_to_complete_time", "超车耗时", False),
    ("compute_latency_ms", "决策延迟", False),
]

PLOT_METRICS = [
    ("on_track_overtake_rate", "赛道内超车率", True),
    ("elegant_overtake_rate", "Desirable overtaking behavior rate", True),
    ("overtake_window_grass_rate_mean", "超车窗口草地率", False),
    ("target_grass_rate", "全程草地率", False),
    ("grass_recovery_time_mean", "草地后恢复时间 / step", False),
    ("rank_gain", "名次提升", True),
]

COLORS = {
    "quality_aux_dlc_world_v4": "#b23a48",
    "quality_aux_dlc_world_v5_soft025": "#c76f3a",
    "quality_aux_dlc_world_v5_soft050": "#9c6ade",
    "quality_aux_dlc_world_v5_gate025": "#2f7f8f",
    "quality_guided_dlc_world_v3": "#c44e52",
    "quality_proposal_dlc_world_v2": "#3b7ddd",
    "quality_proposal_dlc_world_v1": "#4aa564",
    "ours_dynamic_graph_dlc_world": "#d95f02",
    "quality_graph_bc_v2": "#7b68ee",
    "quality_graph_bc_v1": "#8c8c8c",
    "graph_bc_dynamic": "#5ab4ac",
    "dlc_world_original": "#555555",
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


def to_float(value):
    if value is None or value == "":
        return None
    try:
        val = float(value)
    except ValueError:
        return None
    if math.isnan(val):
        return None
    return val


def load_rows(path):
    with Path(path).open("r", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def grouped_values(rows, metric):
    values = defaultdict(list)
    scenario_values = defaultdict(list)
    for row in rows:
        alg = row["algorithm"]
        if alg not in ALGORITHM_ORDER:
            continue
        value = to_float(row.get(metric))
        if value is None:
            continue
        scenario = f"{row.get('_benchmark', '')}|n{row.get('num_agents', '')}|seed{row.get('seed', '')}"
        values[alg].append(value)
        scenario_values[alg].append((scenario, value))
    return values, scenario_values


def summarize(rows):
    records = []
    for alg in ALGORITHM_ORDER:
        for metric, metric_cn, higher_is_better in METRICS:
            vals = [
                to_float(row.get(metric))
                for row in rows
                if row["algorithm"] == alg and to_float(row.get(metric)) is not None
            ]
            if vals:
                arr = np.asarray(vals, dtype=float)
                mean = float(arr.mean())
                std = float(arr.std(ddof=1)) if len(arr) > 1 else 0.0
                sem = std / math.sqrt(len(arr)) if len(arr) > 1 else 0.0
            else:
                mean = std = sem = ""
            records.append(
                {
                    "algorithm": alg,
                    "algorithm_label": ALGORITHM_LABELS.get(alg, alg),
                    "metric": metric,
                    "metric_cn": metric_cn,
                    "higher_is_better": str(bool(higher_is_better)),
                    "n": len(vals),
                    "mean": mean,
                    "std": std,
                    "sem": sem,
                }
            )
    return records


def write_csv(records, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["algorithm", "algorithm_label", "metric", "metric_cn", "higher_is_better", "n", "mean", "std", "sem"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)


def format_value(value, digits=3):
    if value == "" or value is None:
        return "--"
    return f"{float(value):.{digits}f}"


def metric_lookup(records):
    lookup = {}
    for row in records:
        lookup[(row["algorithm"], row["metric"])] = row
    return lookup


def plot_focus(rows, records, out_base):
    import matplotlib as mpl
    import matplotlib.pyplot as plt

    register_cjk_font()
    mpl.rcParams.update(
        {
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "font.size": 7,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.linewidth": 0.8,
            "legend.frameon": False,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
        }
    )

    active_algorithms = [
        alg
        for alg in ALGORITHM_ORDER
        if any(row["algorithm"] == alg for row in rows)
    ]
    fig_width = max(7.2, 0.88 * len(active_algorithms) + 1.6)
    fig, axes = plt.subplots(2, 3, figsize=(fig_width, 4.8), constrained_layout=True)
    x = np.arange(len(active_algorithms))
    for ax, (metric, title, higher_is_better) in zip(axes.ravel(), PLOT_METRICS):
        values, scenario_values = grouped_values(rows, metric)
        means = [np.mean(values[alg]) if values.get(alg) else np.nan for alg in active_algorithms]
        sems = [
            np.std(values[alg], ddof=1) / math.sqrt(len(values[alg])) if len(values.get(alg, [])) > 1 else 0.0
            for alg in active_algorithms
        ]
        bar_colors = [COLORS[alg] for alg in active_algorithms]
        ax.bar(x, means, yerr=sems, color=bar_colors, edgecolor="black", linewidth=0.35, capsize=2.0)
        for idx, alg in enumerate(active_algorithms):
            vals = [value for _, value in scenario_values.get(alg, [])]
            if not vals:
                continue
            jitter = np.linspace(-0.12, 0.12, len(vals)) if len(vals) > 1 else np.array([0.0])
            ax.scatter(
                np.full(len(vals), idx) + jitter,
                vals,
                s=9,
                color="white",
                edgecolor="black",
                linewidth=0.35,
                zorder=3,
            )
        ax.set_title(title, fontsize=8, fontweight="bold")
        ax.set_xticks(x)
        ax.set_xticklabels([ALGORITHM_LABELS[alg] for alg in active_algorithms], rotation=32, ha="right")
        ax.grid(axis="y", color="#dddddd", linewidth=0.4)
        if "rate" in metric or metric == "target_progress":
            ax.set_ylim(0, max(1.0, np.nanmax(means) * 1.18 if np.isfinite(np.nanmax(means)) else 1.0))
        if not higher_is_better:
            ax.text(0.98, 0.92, "越低越好", transform=ax.transAxes, ha="right", va="top", fontsize=6, color="#555555")
        else:
            ax.text(0.98, 0.92, "越高越好", transform=ax.transAxes, ha="right", va="top", fontsize=6, color="#555555")

    fig.suptitle("质量 proposal / 质量引导 DLC 在线超车质量对比", fontsize=10, fontweight="bold")
    out_base = Path(out_base)
    out_base.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(f"{out_base}.svg", bbox_inches="tight")
    fig.savefig(f"{out_base}.pdf", bbox_inches="tight")
    fig.savefig(f"{out_base}.png", dpi=300, bbox_inches="tight")
    fig.savefig(f"{out_base}.tiff", dpi=600, bbox_inches="tight")
    plt.close(fig)


def write_report(records, out_path):
    lookup = metric_lookup(records)

    def mean(alg, metric):
        row = lookup.get((alg, metric))
        return "" if row is None else row["mean"]

    def has_alg(alg):
        return any(row["algorithm"] == alg and row["n"] > 0 for row in records)

    lines = [
        "# 质量辅助 / 质量引导 DLC 小矩阵分析报告",
        "",
        "## 实验设置",
        "",
        "- 场景：procedural n=4/5/6 与 Monza n=6，共 4 个在线场景。",
        "- 算法：quality_aux_dlc_world_v4、quality_guided_dlc_world_v3、quality_proposal_dlc_world_v1、当前本文方法、quality_graph_bc_v2、graph_bc_dynamic、DLC world model。",
        "- 终止：任一车辆完成一圈或达到最大步数；本轮不生成 GIF，优先验证定量趋势。",
        "",
        "## 关键发现",
        "",
        (
            f"- v2 纯 proposal actor（质量图BC-v2）表现出更好的候选动作潜力：平均目标进度 "
            f"{format_value(mean('quality_graph_bc_v2', 'target_progress'))}，全程草地率 "
            f"{format_value(mean('quality_graph_bc_v2', 'target_grass_rate'))}，赛道内超车率 "
            f"{format_value(mean('quality_graph_bc_v2', 'on_track_overtake_rate'))}。"
        ),
        (
            f"- v1 仍是当前 world-model 组合里更稳的版本：目标进度 "
            f"{format_value(mean('quality_proposal_dlc_world_v1', 'target_progress'))}，名次提升 "
            f"{format_value(mean('quality_proposal_dlc_world_v1', 'rank_gain'))}，全程草地率 "
            f"{format_value(mean('quality_proposal_dlc_world_v1', 'target_grass_rate'))}。"
        ),
        (
            f"- v3 质量引导 DLC 相比当前本文方法降低草地率：全程草地率 "
            f"{format_value(mean('quality_guided_dlc_world_v3', 'target_grass_rate'))} vs "
            f"{format_value(mean('ours_dynamic_graph_dlc_world', 'target_grass_rate'))}，但目标进度和名次提升仍低于 v1。"
        ),
        (
            f"- 当前本文方法仍有明显草地问题：全程草地率 "
            f"{format_value(mean('ours_dynamic_graph_dlc_world', 'target_grass_rate'))}，超车窗口草地率 "
            f"{format_value(mean('ours_dynamic_graph_dlc_world', 'overtake_window_grass_rate_mean'))}。"
        ),
        "",
        "## 解释",
        "",
        "v2 数据集中加入稳定巡航和恢复窗口后，纯 BC actor 的赛道保持能力有所增强；v3 通过质量 actor 多步融合与最小 imitation 惩罚，说明 proposal 与 planner 的耦合方式确实会影响在线结果。v4 进一步把 on-track、grass、lane-quality 和 forward-clearance 作为 world model 辅助头训练，但当前小矩阵显示该单步辅助头会让策略更保守，未能稳定提升在线超车质量。这说明辅助预测方向是合理的，但训练标签和规划器门控还需要从“单步状态质量”升级到“多步超车事件质量”。",
        "",
        "## 下一步建议",
        "",
        "- 将 v1 作为当前最稳 world-model 主线，v3/v4 作为机制消融保留；暂不把 v4 作为最终主算法。",
        "- 将 v4 辅助头从单步标签升级为事件级/多步标签：overtake-completion、overtake-window grass、recovery-time 和 lap-progress delta。",
        "- 做 v5 门控扫描：固定 v1 proposal 与 v4 辅助模型，系统扫描 learned-quality weight、rollout blend 和 hard safety gate，选择 Pareto 最优点。",
        "- 在扩展完整 benchmark 前，至少用 5 seeds × 4/5/6/8 车 × procedural/Monza 做预筛，避免小样本偶然性。",
        "",
        "## 输出文件",
        "",
        "- 全局均值表：`tables/quality_proposal_dlc_v2_global_summary.csv`",
        "- 聚焦中文图：`figures/figure_quality_proposal_dlc_v2_focused.svg/.pdf/.png/.tiff`",
        "- 原始 source data：`tables/online_benchmark_source_data.csv`",
    ]
    if has_alg("quality_aux_dlc_world_v4"):
        lines.insert(
            13,
            (
                f"- v4 质量辅助 world model 训练闭环已跑通，但当前在线表现偏保守/不稳定：目标进度 "
                f"{format_value(mean('quality_aux_dlc_world_v4', 'target_progress'))}，超车成功率 "
                f"{format_value(mean('quality_aux_dlc_world_v4', 'overtake_success_rate'))}，全程草地率 "
                f"{format_value(mean('quality_aux_dlc_world_v4', 'target_grass_rate'))}。"
            ),
        )
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Analyze the quality proposal DLC v2 online matrix.")
    parser.add_argument(
        "--source-data",
        default="outputs/tits_dynamic_graph/quality_proposal_dlc_v2_matrix_summary/tables/online_benchmark_source_data.csv",
    )
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/quality_proposal_dlc_v2_matrix_summary")
    args = parser.parse_args()

    rows = load_rows(args.source_data)
    out_dir = Path(args.out_dir)
    records = summarize(rows)
    table_path = out_dir / "tables" / "quality_proposal_dlc_v2_global_summary.csv"
    write_csv(records, table_path)
    figure_base = out_dir / "figures" / "figure_quality_proposal_dlc_v2_focused"
    plot_focus(rows, records, figure_base)
    report_path = out_dir / "quality_proposal_dlc_v2_matrix_report.md"
    write_report(records, report_path)
    print(
        {
            "global_summary": str(table_path),
            "figure_base": str(figure_base),
            "report": str(report_path),
        }
    )


if __name__ == "__main__":
    main()
