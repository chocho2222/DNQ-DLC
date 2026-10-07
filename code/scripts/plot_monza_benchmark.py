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
    "rule_overtake": "规则超车",
    "graph_bc_shield": "图BC+护盾",
    "graph_dagger_recovery_v2": "图DAgger恢复",
    "graph_risk_world": "图风险DLC世界模型",
}
COLORS = {
    "rule_overtake": "#8172B2",
    "graph_bc_shield": "#4C72B0",
    "graph_dagger_recovery_v2": "#DD8452",
    "graph_risk_world": "#55A868",
}
GRID = "#D9E1E8"


def register_cjk_font():
    for item in [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]:
        path = Path(item)
        if path.exists():
            font_manager.fontManager.addfont(str(path))
            family = font_manager.FontProperties(fname=str(path)).get_name()
            mpl.rcParams["font.family"] = family
            mpl.rcParams["font.sans-serif"] = [family, "Arial", "DejaVu Sans", "sans-serif"]
            break


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
        gap = int(data["settings"]["gap_tiles"])
        scenario = f"gap={gap}"
        for row in data["rows"]:
            if row.get("status") == "RUN_FAIL":
                continue
            item = dict(row)
            item["gap_tiles"] = gap
            item["scenario"] = scenario
            rows.append(item)
    rows.sort(key=lambda row: (row["gap_tiles"], row["method"]))
    return rows


def write_source(rows, path):
    fields = [
        "scenario",
        "gap_tiles",
        "method",
        "method_zh",
        "status",
        "target_completed_lap",
        "target_final_rank",
        "target_complete_step",
        "first_ahead_step",
        "target_grass_rate",
        "target_tile_progress",
        "steps_run",
        "track_tiles",
        "target_tiles",
        "summary",
    ]
    with Path(path).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    **{field: row.get(field) for field in fields},
                    "method_zh": LABEL_ZH.get(row["method"], row["label"]),
                    "target_completed_lap": int(bool(row["target_completed_lap"])),
                }
            )


def row_value(rows, gap, method, key):
    for row in rows:
        if row["gap_tiles"] == gap and row["method"] == method:
            return row[key]
    return np.nan


def plot(rows, out_dir):
    setup_mpl()
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    gaps = sorted({int(row["gap_tiles"]) for row in rows})
    methods = [m for m in LABEL_ZH if any(row["method"] == m for row in rows)]
    x = np.arange(len(gaps))

    fig = plt.figure(figsize=(9.2, 6.6), constrained_layout=True)
    gs = fig.add_gridspec(2, 2)
    ax_progress = fig.add_subplot(gs[0, 0])
    ax_grass = fig.add_subplot(gs[0, 1])
    ax_rank = fig.add_subplot(gs[1, 0])
    ax_table = fig.add_subplot(gs[1, 1])

    for method in methods:
        progress = [row_value(rows, gap, method, "target_tile_progress") for gap in gaps]
        ax_progress.plot(x, progress, marker="o", lw=1.6, color=COLORS[method], label=LABEL_ZH[method])
    ax_progress.axhline(1.0, color="#4B5563", lw=0.8, ls="--")
    ax_progress.set_title("a  Monza固定赛道：目标车第一圈进度")
    ax_progress.set_ylabel("完成比例")
    ax_progress.set_xticks(x)
    ax_progress.set_xticklabels([f"起步间距{gap}" for gap in gaps])
    ax_progress.set_ylim(0, 1.05)
    ax_progress.grid(axis="y", color=GRID, lw=0.6)
    ax_progress.legend(fontsize=7)

    for method in methods:
        grass = [100 * row_value(rows, gap, method, "target_grass_rate") for gap in gaps]
        ax_grass.plot(x, grass, marker="o", lw=1.6, color=COLORS[method], label=LABEL_ZH[method])
    ax_grass.axhline(8.0, color="#C44E52", lw=0.8, ls="--")
    ax_grass.set_title("b  赛道内质量：目标车草地步占比")
    ax_grass.set_ylabel("草地步占比（%）")
    ax_grass.set_xticks(x)
    ax_grass.set_xticklabels([f"起步间距{gap}" for gap in gaps])
    ax_grass.grid(axis="y", color=GRID, lw=0.6)

    width = 0.18
    offsets = np.linspace(-width * 1.5, width * 1.5, len(methods))
    for offset, method in zip(offsets, methods):
        ranks = [row_value(rows, gap, method, "target_final_rank") for gap in gaps]
        ax_rank.bar(x + offset, ranks, width=width, color=COLORS[method], label=LABEL_ZH[method])
    ax_rank.invert_yaxis()
    ax_rank.set_yticks([1, 2, 3, 4])
    ax_rank.set_title("c  最终名次")
    ax_rank.set_ylabel("名次（1=最前）")
    ax_rank.set_xticks(x)
    ax_rank.set_xticklabels([f"起步间距{gap}" for gap in gaps])
    ax_rank.grid(axis="y", color=GRID, lw=0.6)

    ax_table.axis("off")
    best_progress = max(rows, key=lambda row: row["target_tile_progress"])
    lowest_grass = min(rows, key=lambda row: row["target_grass_rate"])
    pass_count = sum(row["status"] == "PASS" for row in rows)
    complete_count = sum(bool(row["target_completed_lap"]) for row in rows)
    rows_text = [
        ["指标", "结果"],
        ["严格通过", f"{pass_count}/{len(rows)}"],
        ["完圈", f"{complete_count}/{len(rows)}"],
        ["最高进度", f"{LABEL_ZH.get(best_progress['method'], best_progress['method'])}, gap={best_progress['gap_tiles']}, {best_progress['target_tile_progress']:.2f}"],
        ["最低草地率", f"{LABEL_ZH.get(lowest_grass['method'], lowest_grass['method'])}, gap={lowest_grass['gap_tiles']}, {lowest_grass['target_grass_rate']*100:.1f}%"],
        ["主要失败模式", "Monza分布偏移导致草地率高或停滞"],
    ]
    x0, y0, row_h = 0.03, 0.94, 0.12
    col_w = [0.30, 0.66]
    for r, row in enumerate(rows_text):
        for c, text in enumerate(row):
            x_pos = x0 + sum(col_w[:c])
            y_pos = y0 - r * row_h
            face = "#EEF2F7" if r == 0 else ("#F8FAFC" if r % 2 else "white")
            ax_table.add_patch(plt.Rectangle((x_pos, y_pos - row_h + 0.01), col_w[c], row_h, transform=ax_table.transAxes, facecolor=face, edgecolor="#D0D7DE", lw=0.6))
            ax_table.text(x_pos + col_w[c] / 2, y_pos - row_h / 2 + 0.01, text, ha="center", va="center", fontsize=7.0, transform=ax_table.transAxes, fontweight="bold" if r == 0 else "normal")
    ax_table.set_title("d  外部赛道验证摘要", loc="left")

    fig.suptitle("Monza固定赛道外部验证：当前算法与对比算法", fontsize=11, fontweight="bold")
    fig.text(
        0.01,
        0.004,
        "判据：目标车最后一位起步；通过=完成一圈、最终第1且目标车草地步占比≤8%。Monza为CSV固定赛道转换，非训练随机赛道。",
        fontsize=7,
        color="#4B5563",
    )
    stem = out_dir / "figure_monza_benchmark"
    for ext in ["svg", "pdf", "png"]:
        fig.savefig(stem.with_suffix(f".{ext}"), dpi=600, bbox_inches="tight")
    fig.savefig(stem.with_suffix(".tiff"), dpi=600, bbox_inches="tight")
    plt.close(fig)

    source_csv = stem.with_suffix(".source.csv")
    write_source(rows, source_csv)
    manifest = {
        "claim": "Monza固定赛道外部验证显示，当前随机赛道训练策略尚不能直接泛化到真实形状赛道；所有方法在严格完圈+赛道内超车端点下均未通过。",
        "track": "multi_car_racing/tracks/monza_scaled.npz",
        "source_data": str(source_csv),
        "outputs": {ext: str(stem.with_suffix(f'.{ext}')) for ext in ["svg", "pdf", "png", "tiff"]},
        "strict_pass_count": int(pass_count),
        "n": int(len(rows)),
        "best_progress": best_progress,
        "lowest_grass": lowest_grass,
    }
    stem.with_suffix(".manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Plot Monza fixed-track benchmark.")
    parser.add_argument("--summaries", required=True)
    parser.add_argument("--out-dir", default="multi_car_racing/outputs/paper_multicar_overtake_20260618/figures/monza_benchmark")
    args = parser.parse_args()
    rows = load_rows([item.strip() for item in args.summaries.split(",") if item.strip()])
    plot(rows, args.out_dir)


if __name__ == "__main__":
    main()
