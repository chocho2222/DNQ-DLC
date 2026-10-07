#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager


LABEL_ZH = {
    "dlc_world_model": "DLC世界模型",
    "rule_overtake": "规则超车",
    "graph_bc_shield": "图BC+护盾",
    "graph_risk_world": "图风险DLC世界模型",
    "graph_risk_world_balanced": "图风险DLC-均衡",
    "graph_risk_world_fast": "图风险DLC-快速",
}
COLORS = {
    "dlc_world_model": "#C44E52",
    "rule_overtake": "#8172B2",
    "graph_bc_shield": "#4C72B0",
    "graph_risk_world": "#55A868",
    "graph_risk_world_balanced": "#64B5CD",
    "graph_risk_world_fast": "#DD8452",
}
GRID = "#D9E1E8"
INK = "#1F2933"


def register_cjk_font():
    for item in [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/arphic/ukai.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]:
        path = Path(item)
        if path.exists():
            font_manager.fontManager.addfont(str(path))
            family = font_manager.FontProperties(fname=str(path)).get_name()
            mpl.rcParams["font.family"] = family
            mpl.rcParams["font.sans-serif"] = [family, "Arial", "DejaVu Sans", "sans-serif"]
            return


def setup_mpl():
    register_cjk_font()
    mpl.rcParams.update(
        {
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "font.size": 8,
            "axes.spines.right": False,
            "axes.spines.top": False,
            "axes.linewidth": 0.8,
            "legend.frameon": False,
            "axes.unicode_minus": False,
        }
    )


def load_rows(summary_paths):
    rows = []
    for path in summary_paths:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        for row in data["rows"]:
            if row.get("status") == "RUN_FAIL":
                continue
            rows.append(row)
    dedup = {}
    for row in rows:
        dedup[(row["method"], int(row["seed"]))] = row
    return list(dedup.values())


def write_source(rows, path):
    fields = [
        "method",
        "method_zh",
        "seed",
        "status",
        "target_completed_lap",
        "target_final_rank",
        "target_complete_step",
        "first_ahead_step",
        "target_grass_rate",
        "target_tile_progress",
        "steps_run",
    ]
    with Path(path).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "method": row["method"],
                    "method_zh": LABEL_ZH.get(row["method"], row["label"]),
                    "seed": int(row["seed"]),
                    "status": row["status"],
                    "target_completed_lap": int(bool(row["target_completed_lap"])),
                    "target_final_rank": int(row["target_final_rank"]),
                    "target_complete_step": row["target_complete_step"],
                    "first_ahead_step": row["first_ahead_step"],
                    "target_grass_rate": float(row["target_grass_rate"]),
                    "target_tile_progress": float(row["target_tile_progress"]),
                    "steps_run": int(row["steps_run"]),
                }
            )


def method_stats(rows, methods):
    stats = {}
    for method in methods:
        items = [row for row in rows if row["method"] == method]
        if not items:
            continue
        finish = [row["target_complete_step"] for row in items if row["target_complete_step"] is not None]
        stats[method] = {
            "n": len(items),
            "pass_rate": np.mean([row["status"] == "PASS" for row in items]),
            "completion_rate": np.mean([row["target_completed_lap"] for row in items]),
            "progress_mean": np.mean([row["target_tile_progress"] for row in items]),
            "grass_mean": np.mean([row["target_grass_rate"] for row in items]),
            "rank_mean": np.mean([row["target_final_rank"] for row in items]),
            "finish_mean": np.mean(finish) if finish else np.nan,
        }
    return stats


def plot(rows, out_dir, methods):
    setup_mpl()
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    methods = [method for method in methods if any(row["method"] == method for row in rows)]
    stats = method_stats(rows, methods)
    x = np.arange(len(methods))
    labels = [LABEL_ZH.get(method, method) for method in methods]
    colors = [COLORS.get(method, "#4B5563") for method in methods]

    fig = plt.figure(figsize=(9.2, 6.6), constrained_layout=True)
    gs = fig.add_gridspec(2, 3, height_ratios=[1.0, 1.05])
    ax_rate = fig.add_subplot(gs[0, 0])
    ax_progress = fig.add_subplot(gs[0, 1])
    ax_grass = fig.add_subplot(gs[0, 2])
    ax_finish = fig.add_subplot(gs[1, 0])
    ax_rank = fig.add_subplot(gs[1, 1])
    ax_table = fig.add_subplot(gs[1, 2])

    pass_rate = [stats[m]["pass_rate"] for m in methods]
    completion_rate = [stats[m]["completion_rate"] for m in methods]
    ax_rate.bar(x - 0.17, pass_rate, width=0.34, color=colors, alpha=0.95, label="通过率")
    ax_rate.bar(x + 0.17, completion_rate, width=0.34, color=colors, alpha=0.35, label="完圈率")
    ax_rate.set_title("a  在线任务成功率")
    ax_rate.set_ylim(0, 1.05)
    ax_rate.set_ylabel("比例")
    ax_rate.set_xticks(x)
    ax_rate.set_xticklabels(labels, rotation=35, ha="right")
    ax_rate.grid(axis="y", color=GRID, lw=0.6)
    ax_rate.legend(fontsize=7)

    rng = np.random.default_rng(7)
    for i, method in enumerate(methods):
        vals = [row["target_tile_progress"] for row in rows if row["method"] == method]
        jitter = rng.normal(0, 0.035, len(vals))
        ax_progress.scatter(np.full(len(vals), i) + jitter, vals, s=18, color=COLORS.get(method, "#4B5563"), edgecolor="white", lw=0.4, zorder=3)
        ax_progress.plot([i - 0.2, i + 0.2], [np.mean(vals), np.mean(vals)], color=COLORS.get(method, "#4B5563"), lw=2)
    ax_progress.axhline(1.0, color="#4B5563", lw=0.8, ls="--")
    ax_progress.set_title("b  目标车第一圈进度")
    ax_progress.set_ylabel("完成比例")
    ax_progress.set_xticks(x)
    ax_progress.set_xticklabels(labels, rotation=35, ha="right")
    ax_progress.set_ylim(0, 1.08)
    ax_progress.grid(axis="y", color=GRID, lw=0.6)

    for i, method in enumerate(methods):
        vals = [row["target_grass_rate"] * 100 for row in rows if row["method"] == method]
        jitter = rng.normal(0, 0.035, len(vals))
        ax_grass.scatter(np.full(len(vals), i) + jitter, vals, s=18, color=COLORS.get(method, "#4B5563"), edgecolor="white", lw=0.4)
        ax_grass.plot([i - 0.2, i + 0.2], [np.mean(vals), np.mean(vals)], color=COLORS.get(method, "#4B5563"), lw=2)
    ax_grass.axhline(8.0, color="#C44E52", lw=0.8, ls="--")
    ax_grass.set_title("c  赛道内质量：草地步占比")
    ax_grass.set_ylabel("草地步占比（%）")
    ax_grass.set_xticks(x)
    ax_grass.set_xticklabels(labels, rotation=35, ha="right")
    ax_grass.grid(axis="y", color=GRID, lw=0.6)

    finish_means = [stats[m]["finish_mean"] for m in methods]
    ax_finish.bar(x, [0 if np.isnan(v) else v for v in finish_means], color=colors)
    for i, v in enumerate(finish_means):
        if np.isnan(v):
            ax_finish.text(i, 40, "未完圈", ha="center", va="bottom", fontsize=7, color="#6B7280", rotation=90)
    ax_finish.set_title("d  完圈步数（越低越快）")
    ax_finish.set_ylabel("环境步数")
    ax_finish.set_xticks(x)
    ax_finish.set_xticklabels(labels, rotation=35, ha="right")
    ax_finish.grid(axis="y", color=GRID, lw=0.6)

    rank_mean = [stats[m]["rank_mean"] for m in methods]
    ax_rank.bar(x, rank_mean, color=colors)
    ax_rank.invert_yaxis()
    ax_rank.set_yticks([1, 2, 3, 4])
    ax_rank.set_title("e  最终平均名次")
    ax_rank.set_ylabel("名次（1=最前）")
    ax_rank.set_xticks(x)
    ax_rank.set_xticklabels(labels, rotation=35, ha="right")
    ax_rank.grid(axis="y", color=GRID, lw=0.6)

    ax_table.axis("off")
    table_rows = [["方法", "通过", "进度", "草地"]]
    for method in methods:
        item = stats[method]
        table_rows.append(
            [
                LABEL_ZH.get(method, method),
                f"{int(round(item['pass_rate'] * item['n']))}/{item['n']}",
                f"{item['progress_mean']:.2f}",
                f"{item['grass_mean'] * 100:.1f}%",
            ]
        )
    col_w = [0.42, 0.18, 0.18, 0.20]
    x0, y0, row_h = 0.02, 0.94, 0.115
    for r, row in enumerate(table_rows):
        for c, text in enumerate(row):
            x_pos = x0 + sum(col_w[:c])
            y_pos = y0 - r * row_h
            face = "#EEF2F7" if r == 0 else ("#F8FAFC" if r % 2 else "white")
            ax_table.add_patch(plt.Rectangle((x_pos, y_pos - row_h + 0.01), col_w[c], row_h, transform=ax_table.transAxes, facecolor=face, edgecolor="#D0D7DE", lw=0.6))
            ax_table.text(x_pos + col_w[c] / 2, y_pos - row_h / 2 + 0.01, text, ha="center", va="center", fontsize=6.7, transform=ax_table.transAxes, color=INK, fontweight="bold" if r == 0 else "normal")
    ax_table.set_title("f  多seed摘要", loc="left")

    fig.suptitle("Graph-Risk DLC世界模型：针对DLC世界模型多车超车不足的在线验证", fontsize=11, fontweight="bold")
    fig.text(
        0.01,
        0.004,
        "判据：目标车最后一位起步；通过=目标车完成一圈、最终第1且草地步占比≤8%。点为独立seed，横线为均值。",
        fontsize=7,
        color="#4B5563",
    )
    stem = out_dir / "figure_graph_risk_world_comparison"
    for ext in ["svg", "pdf", "png"]:
        fig.savefig(stem.with_suffix(f".{ext}"), dpi=600, bbox_inches="tight")
    fig.savefig(stem.with_suffix(".tiff"), dpi=600, bbox_inches="tight")
    plt.close(fig)

    source_csv = stem.with_suffix(".source.csv")
    write_source(rows, source_csv)
    manifest = {
        "claim": "Graph-Risk DLC世界模型在代表性seed上可实现赛道内完圈超车，但3-seed筛选显示鲁棒性仍受proposal保守性和风险估计偏置限制。",
        "methods": methods,
        "source_data": str(source_csv),
        "outputs": {ext: str(stem.with_suffix(f'.{ext}')) for ext in ["svg", "pdf", "png", "tiff"]},
        "stats": stats,
    }
    stem.with_suffix(".manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Plot Graph-Risk world-model comparison as Chinese paper figure.")
    parser.add_argument("--summaries", required=True, help="Comma-separated comparison summary JSON files.")
    parser.add_argument("--methods", default="dlc_world_model,rule_overtake,graph_bc_shield,graph_risk_world,graph_risk_world_balanced,graph_risk_world_fast")
    parser.add_argument("--out-dir", default="multi_car_racing/outputs/paper_multicar_overtake_20260618/figures/graph_risk_world_model")
    args = parser.parse_args()
    rows = load_rows([item.strip() for item in args.summaries.split(",") if item.strip()])
    methods = [item.strip() for item in args.methods.split(",") if item.strip()]
    plot(rows, args.out_dir, methods)


if __name__ == "__main__":
    main()
