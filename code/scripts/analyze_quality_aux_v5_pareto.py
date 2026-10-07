#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import math
from collections import defaultdict
from pathlib import Path

import numpy as np


ALGORITHM_ORDER = [
    "quality_aux_dlc_world_v5_soft025",
    "quality_aux_dlc_world_v5_soft050",
    "quality_aux_dlc_world_v5_gate025",
    "quality_aux_dlc_world_v4",
    "quality_guided_dlc_world_v3",
    "quality_proposal_dlc_world_v1",
    "dlc_world_original",
]

LABELS = {
    "quality_aux_dlc_world_v5_soft025": "v5-soft025",
    "quality_aux_dlc_world_v5_soft050": "v5-soft050",
    "quality_aux_dlc_world_v5_gate025": "v5-gate025",
    "quality_aux_dlc_world_v4": "v4",
    "quality_guided_dlc_world_v3": "v3",
    "quality_proposal_dlc_world_v1": "v1",
    "dlc_world_original": "DLC原始",
}

COLORS = {
    "quality_aux_dlc_world_v5_soft025": "#c76f3a",
    "quality_aux_dlc_world_v5_soft050": "#9c6ade",
    "quality_aux_dlc_world_v5_gate025": "#2f7f8f",
    "quality_aux_dlc_world_v4": "#b23a48",
    "quality_guided_dlc_world_v3": "#c44e52",
    "quality_proposal_dlc_world_v1": "#4aa564",
    "dlc_world_original": "#555555",
}

METRICS = [
    "overtake_success_rate",
    "overtake_count",
    "on_track_overtake_rate",
    "elegant_overtake_rate",
    "overtake_window_grass_rate_mean",
    "target_grass_rate",
    "grass_recovery_time_mean",
    "target_progress",
    "rank_gain",
    "overtake_start_to_complete_time",
    "compute_latency_ms",
]


def register_cjk_font():
    import matplotlib as mpl
    from matplotlib import font_manager

    candidates = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
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
        value = float(value)
    except ValueError:
        return None
    return None if math.isnan(value) else value


def load_rows(path):
    with Path(path).open("r", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def summarize(rows):
    records = []
    for alg in ALGORITHM_ORDER:
        sub = [row for row in rows if row["algorithm"] == alg]
        if not sub:
            continue
        record = {"algorithm": alg, "label": LABELS.get(alg, alg), "n_runs": len(sub)}
        for metric in METRICS:
            vals = [to_float(row.get(metric)) for row in sub]
            vals = [val for val in vals if val is not None]
            record[metric] = float(np.mean(vals)) if vals else ""
            record[f"{metric}_n"] = len(vals)
            record[f"{metric}_sem"] = float(np.std(vals, ddof=1) / math.sqrt(len(vals))) if len(vals) > 1 else 0.0
        records.append(record)
    return records


def pareto_flags(records):
    flags = {}
    for a in records:
        dominated = False
        for b in records:
            if a is b:
                continue
            better_or_equal = (
                b["target_grass_rate"] <= a["target_grass_rate"]
                and b["target_progress"] >= a["target_progress"]
                and b["rank_gain"] >= a["rank_gain"]
            )
            strictly_better = (
                b["target_grass_rate"] < a["target_grass_rate"]
                or b["target_progress"] > a["target_progress"]
                or b["rank_gain"] > a["rank_gain"]
            )
            if better_or_equal and strictly_better:
                dominated = True
                break
        flags[a["algorithm"]] = not dominated
    return flags


def write_csv(records, out_path):
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["algorithm", "label", "n_runs"]
    for metric in METRICS:
        fieldnames.extend([metric, f"{metric}_n", f"{metric}_sem"])
    with out_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)


def plot_pareto(records, out_base):
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
    flags = pareto_flags(records)
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.2), constrained_layout=True)

    ax = axes[0]
    for row in records:
        x = row["target_grass_rate"]
        y = row["target_progress"]
        size = 36 + 28 * max(float(row["rank_gain"]), 0.0)
        marker = "o" if flags[row["algorithm"]] else "s"
        ax.scatter(x, y, s=size, color=COLORS.get(row["algorithm"], "#777777"), edgecolor="black", linewidth=0.45, marker=marker)
        ax.text(x + 0.012, y + 0.008, row["label"], fontsize=6.5)
    ax.set_xlabel("全程草地率（越低越好）")
    ax.set_ylabel("目标车进度（越高越好）")
    ax.set_title("安全-进度 Pareto")
    ax.grid(color="#dddddd", linewidth=0.4)

    ax = axes[1]
    labels = [row["label"] for row in records]
    x = np.arange(len(records))
    progress = [row["target_progress"] for row in records]
    grass = [row["target_grass_rate"] for row in records]
    width = 0.36
    ax.bar(x - width / 2, progress, width, color="#4c78a8", edgecolor="black", linewidth=0.35, label="目标进度")
    ax.bar(x + width / 2, grass, width, color="#e45756", edgecolor="black", linewidth=0.35, label="草地率")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=35, ha="right")
    ax.set_ylim(0, max(1.0, max(progress + grass) * 1.15))
    ax.set_title("进度与草地率对照")
    ax.grid(axis="y", color="#dddddd", linewidth=0.4)
    ax.legend(loc="upper left", fontsize=6.5)

    fig.suptitle("v5 质量辅助 world model 权重/门控扫描", fontsize=10, fontweight="bold")
    out_base = Path(out_base)
    out_base.parent.mkdir(parents=True, exist_ok=True)
    for ext, kwargs in {
        "svg": {},
        "pdf": {},
        "png": {"dpi": 300},
        "tiff": {"dpi": 600},
    }.items():
        fig.savefig(out_base.with_suffix(f".{ext}"), bbox_inches="tight", **kwargs)
    plt.close(fig)


def fmt(value):
    return "--" if value == "" or value is None else f"{float(value):.3f}"


def write_report(records, out_path):
    flags = pareto_flags(records)
    by_alg = {row["algorithm"]: row for row in records}
    best_progress = max(records, key=lambda row: row["target_progress"])
    best_grass = min(records, key=lambda row: row["target_grass_rate"])
    best_rank = max(records, key=lambda row: row["rank_gain"])
    lines = [
        "# v5 质量辅助 world model Pareto 扫描报告",
        "",
        "## 设置",
        "",
        "- 场景：procedural n=4/5/6 与 Monza n=6，共 4 个在线场景。",
        "- 扫描对象：质量辅助 DLC world model 在不同 learned-quality 权重、proposal actor 与 gate 设置下的在线规划表现。",
        "- 评价重点：全程草地率、目标车进度、名次提升、on-track/desirable超车率和决策延迟。",
        "",
        "## 关键结果",
        "",
        f"- 目标进度最高：{best_progress['label']}，目标进度 {fmt(best_progress['target_progress'])}，草地率 {fmt(best_progress['target_grass_rate'])}。",
        f"- 草地率最低：{best_grass['label']}，草地率 {fmt(best_grass['target_grass_rate'])}，目标进度 {fmt(best_grass['target_progress'])}。",
        f"- 名次提升最高：{best_rank['label']}，名次提升 {fmt(best_rank['rank_gain'])}，草地率 {fmt(best_rank['target_grass_rate'])}。",
    ]
    if "quality_aux_dlc_world_v5_soft025" in by_alg and "quality_aux_dlc_world_v4" in by_alg:
        v5 = by_alg["quality_aux_dlc_world_v5_soft025"]
        v4 = by_alg["quality_aux_dlc_world_v4"]
        lines.append(
            f"- v5-soft025 相比 v4 明显恢复在线可用性：目标进度 {fmt(v4['target_progress'])} -> {fmt(v5['target_progress'])}，"
            f"草地率 {fmt(v4['target_grass_rate'])} -> {fmt(v5['target_grass_rate'])}。"
        )
    if "quality_proposal_dlc_world_v1" in by_alg:
        v1 = by_alg["quality_proposal_dlc_world_v1"]
        lines.append(
            f"- v1 仍是当前最稳 world-model 对照：目标进度 {fmt(v1['target_progress'])}，草地率 {fmt(v1['target_grass_rate'])}，"
            f"名次提升 {fmt(v1['rank_gain'])}。"
        )
    lines.extend(
        [
            "",
            "## Pareto 状态",
            "",
        ]
    )
    for row in records:
        status = "非支配" if flags[row["algorithm"]] else "被支配"
        lines.append(
            f"- {row['label']}：{status}；进度 {fmt(row['target_progress'])}，草地率 {fmt(row['target_grass_rate'])}，"
            f"名次提升 {fmt(row['rank_gain'])}，延迟 {fmt(row['compute_latency_ms'])} ms。"
        )
    lines.extend(
        [
            "",
            "## 结论",
            "",
            "v5 扫描说明，v4 的失败主要来自 learned-quality 权重和 proposal/score 耦合过强；降低权重后可显著恢复进度并降低草地率。然而 v1 仍是当前最稳的 world-model 主线。下一步若要形成 T-ITS 级主张，应将 v5-soft025 作为校准后辅助头候选，并在更大 benchmark 上与 v1、v3、规则基线和 DLC 原始模型进行统计检验。",
            "",
            "## 输出文件",
            "",
            "- `tables/quality_aux_v5_pareto_summary.csv`",
            "- `figures/figure_quality_aux_v5_pareto.svg/.pdf/.png/.tiff`",
            "- `quality_aux_v5_pareto_report.md`",
        ]
    )
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Analyze v5 auxiliary-quality DLC world-model Pareto sweep.")
    parser.add_argument("--source-data", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()
    rows = load_rows(args.source_data)
    records = summarize(rows)
    out_dir = Path(args.out_dir)
    write_csv(records, out_dir / "tables" / "quality_aux_v5_pareto_summary.csv")
    plot_pareto(records, out_dir / "figures" / "figure_quality_aux_v5_pareto")
    write_report(records, out_dir / "quality_aux_v5_pareto_report.md")
    print(
        {
            "summary": str(out_dir / "tables" / "quality_aux_v5_pareto_summary.csv"),
            "figure": str(out_dir / "figures" / "figure_quality_aux_v5_pareto"),
            "report": str(out_dir / "quality_aux_v5_pareto_report.md"),
        }
    )


if __name__ == "__main__":
    main()
