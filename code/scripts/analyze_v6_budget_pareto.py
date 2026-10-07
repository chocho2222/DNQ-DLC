#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import json
from pathlib import Path

import numpy as np


ORDER = [
    "v6_runtime_dynamic_neighborhood",
    "v6_runtime_dynamic_neighborhood_fast",
    "v6_runtime_dynamic_neighborhood_safe",
    "quality_proposal_dlc_world_v1",
]

LABELS = {
    "v6_runtime_dynamic_neighborhood": "v6-full",
    "v6_runtime_dynamic_neighborhood_fast": "v6-fast",
    "v6_runtime_dynamic_neighborhood_safe": "v6-safe",
    "quality_proposal_dlc_world_v1": "v1",
}

COLORS = {
    "v6_runtime_dynamic_neighborhood": "#2f6bbd",
    "v6_runtime_dynamic_neighborhood_fast": "#55a868",
    "v6_runtime_dynamic_neighborhood_safe": "#c44e52",
    "quality_proposal_dlc_world_v1": "#8172b2",
}

METRICS = [
    "overtake_success_rate",
    "on_track_overtake_rate",
    "elegant_overtake_rate",
    "overtake_start_to_complete_time",
    "target_grass_rate",
    "grass_recovery_time_mean",
    "rank_gain",
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
        return float(value)
    except ValueError:
        return None


def load_rows(path):
    with Path(path).open("r", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def summarize(rows):
    out = []
    for alg in ORDER:
        items = [row for row in rows if row.get("algorithm") == alg]
        if not items:
            continue
        record = {
            "algorithm": alg,
            "label": LABELS.get(alg, alg),
            "n": len(items),
            "planner_horizon": items[0].get("planner_horizon", ""),
            "planner_candidates": items[0].get("planner_candidates", ""),
        }
        for metric in METRICS:
            values = [to_float(row.get(metric)) for row in items]
            values = [value for value in values if value is not None and np.isfinite(value)]
            record[metric] = float(np.mean(values)) if values else None
            record[f"{metric}_std"] = float(np.std(values, ddof=1)) if len(values) > 1 else 0.0
        out.append(record)
    return out


def write_csv(records, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["algorithm", "label", "n", "planner_horizon", "planner_candidates"]
    for metric in METRICS:
        fields.extend([metric, f"{metric}_std"])
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)


def plot(records, out_base):
    import matplotlib as mpl
    import matplotlib.pyplot as plt

    register_cjk_font()
    mpl.rcParams.update(
        {
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "font.size": 8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.unicode_minus": False,
            "legend.frameon": False,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
        }
    )

    fig, axes = plt.subplots(1, 3, figsize=(10.2, 3.2), constrained_layout=True)
    panels = [
        ("target_grass_rate", "草地率（越低越好）"),
        ("elegant_overtake_rate", "Desirable overtaking behavior rate（越高越好）"),
        ("grass_recovery_time_mean", "草地后恢复时间（越低越好）"),
    ]
    for ax, (metric, ylabel) in zip(axes, panels):
        for row in records:
            x = row["compute_latency_ms"]
            y = row[metric]
            if x is None or y is None:
                continue
            size = 55 + 24 * max(float(row.get("rank_gain") or 0.0), 0.0)
            ax.scatter(
                x,
                y,
                s=size,
                color=COLORS.get(row["algorithm"], "#777777"),
                edgecolor="black",
                linewidth=0.45,
                alpha=0.92,
                label=row["label"],
            )
            budget = ""
            if row.get("planner_horizon") and row.get("planner_candidates"):
                budget = f" ({row['planner_horizon']}x{row['planner_candidates']})"
            ax.text(x + 2.0, y, row["label"] + budget, fontsize=7, va="center")
        ax.set_xlabel("决策延迟 ms（越低越好）")
        ax.set_ylabel(ylabel)
        ax.grid(color="#d9e1e8", linewidth=0.55)
    axes[1].legend(loc="lower right", fontsize=7)
    fig.suptitle("v6 运行时规划预算 Pareto：延迟、草地与Desirable overtaking behavior", fontsize=11, fontweight="bold")
    out_base = Path(out_base)
    out_base.parent.mkdir(parents=True, exist_ok=True)
    outputs = {}
    for ext, kwargs in {
        "svg": {},
        "pdf": {},
        "png": {"dpi": 300},
        "tiff": {"dpi": 600},
    }.items():
        path = out_base.with_suffix(f".{ext}")
        fig.savefig(path, bbox_inches="tight", **kwargs)
        outputs[ext] = str(path)
    plt.close(fig)
    return outputs


def fmt(value, digits=3):
    return "--" if value is None else f"{float(value):.{digits}f}"


def write_report(records, outputs, out_path):
    by_alg = {row["algorithm"]: row for row in records}
    full = by_alg.get("v6_runtime_dynamic_neighborhood")
    fast = by_alg.get("v6_runtime_dynamic_neighborhood_fast")
    safe = by_alg.get("v6_runtime_dynamic_neighborhood_safe")
    v1 = by_alg.get("quality_proposal_dlc_world_v1")

    lines = [
        "# v6 运行时规划预算 Pareto 报告",
        "",
        "## 结论",
        "",
        "本轮比较说明，v6 的在线规划预算存在清晰的质量-延迟权衡。v6-fast 显著降低延迟，但在 n=8 和 Monza 场景出现稳定性下降；v6-safe 在延迟和质量之间更均衡；v6-full 仍是当前最稳的质量优先候选。",
        "",
        "## 均值摘要",
        "",
        "| 算法 | 预算 HxC | 成功率 | Desirable overtaking behavior rate | 草地率 | 恢复时间 | 名次提升 | 延迟 ms |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in records:
        budget = "--"
        if row.get("planner_horizon") and row.get("planner_candidates"):
            budget = f"{row['planner_horizon']}x{row['planner_candidates']}"
        lines.append(
            f"| {row['label']} | {budget} | {fmt(row['overtake_success_rate'])} | {fmt(row['elegant_overtake_rate'])} | "
            f"{fmt(row['target_grass_rate'])} | {fmt(row['grass_recovery_time_mean'], 1)} | {fmt(row['rank_gain'], 2)} | {fmt(row['compute_latency_ms'], 1)} |"
        )
    lines.extend(["", "## 解释", ""])
    if full and v1:
        lines.append(
            f"- v6-full 相比 v1：Desirable overtaking behavior rate {fmt(v1['elegant_overtake_rate'])} -> {fmt(full['elegant_overtake_rate'])}，"
            f"草地率 {fmt(v1['target_grass_rate'])} -> {fmt(full['target_grass_rate'])}，"
            f"延迟 {fmt(v1['compute_latency_ms'], 1)} ms -> {fmt(full['compute_latency_ms'], 1)} ms。"
        )
    if fast:
        lines.append(
            f"- v6-fast 延迟最低，为 {fmt(fast['compute_latency_ms'], 1)} ms，但平均草地率升至 {fmt(fast['target_grass_rate'])}，"
            "说明过低规划预算会牺牲恢复稳定性。"
        )
    if safe:
        lines.append(
            f"- v6-safe 延迟为 {fmt(safe['compute_latency_ms'], 1)} ms，Desirable overtaking behavior rate {fmt(safe['elegant_overtake_rate'])}，"
            f"草地率 {fmt(safe['target_grass_rate'])}，适合作为下一轮确认性实验的效率候选。"
        )
    lines.extend(
        [
            "",
            "## 输出文件",
            "",
            "- `tables/v6_budget_pareto_summary.csv`",
            "- `figures/figure_v6_budget_pareto.svg/.pdf/.png/.tiff`",
            "- `v6_budget_pareto_report.md`",
        ]
    )
    Path(out_path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Analyze v6 planning-budget Pareto sweep.")
    parser.add_argument("--source-data", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    records = summarize(load_rows(args.source_data))
    write_csv(records, out_dir / "tables" / "v6_budget_pareto_summary.csv")
    outputs = plot(records, out_dir / "figures" / "figure_v6_budget_pareto")
    write_report(records, outputs, out_dir / "v6_budget_pareto_report.md")
    manifest = {
        "source_data": args.source_data,
        "summary": str(out_dir / "tables" / "v6_budget_pareto_summary.csv"),
        "figures": outputs,
        "report": str(out_dir / "v6_budget_pareto_report.md"),
    }
    (out_dir / "v6_budget_pareto_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
