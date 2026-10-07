#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager


PALETTE = {
    "current": "#2F6BBD",
    "dlc": "#C44E52",
    "bg0": "#55A868",
    "bg1": "#8172B2",
    "grid": "#D9E1E8",
    "ink": "#1F2933",
}


def register_cjk_font():
    candidates = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
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


def setup_matplotlib():
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
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.unicode_minus": False,
        }
    )


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def moving_average(values, window=31):
    arr = np.asarray(values, dtype=np.float64)
    if len(arr) < window:
        return arr
    kernel = np.ones(window, dtype=np.float64) / window
    return np.convolve(arr, kernel, mode="same")


def first_step_at_or_above(series, threshold):
    for idx, value in enumerate(series):
        if value >= threshold:
            return idx + 1
    return None


def export_source_csv(trace, summary, out_path, labels):
    fields = ["step"]
    for agent_id, label in enumerate(labels):
        fields.extend(
            [
                f"{label}_tiles",
                f"{label}_progress",
                f"{label}_reward",
                f"{label}_speed",
                f"{label}_gas",
                f"{label}_brake",
            ]
        )
    with Path(out_path).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in trace:
            out = {"step": row["step"]}
            for agent_id, label in enumerate(labels):
                action = row.get("action", [[0, 0, 0]] * len(labels))[agent_id]
                out[f"{label}_tiles"] = row["tile_visited_count"][agent_id]
                out[f"{label}_progress"] = row["tile_visited_count"][agent_id] / max(summary["track_tiles"], 1)
                out[f"{label}_reward"] = row["total_reward"][agent_id]
                out[f"{label}_speed"] = row.get("speed", [0] * len(labels))[agent_id]
                out[f"{label}_gas"] = action[1]
                out[f"{label}_brake"] = action[2]
            writer.writerow(out)


def plot(summary_path, trace_path, out_dir):
    setup_matplotlib()
    summary = load_json(summary_path)
    trace = load_json(trace_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    labels = ["当前算法", "DLC世界模型", "背景车1", "背景车2"]
    colors = [PALETTE["current"], PALETTE["dlc"], PALETTE["bg0"], PALETTE["bg1"]]
    steps = np.asarray([row["step"] for row in trace], dtype=np.int32)
    track_tiles = max(int(summary["track_tiles"]), 1)
    tiles = np.asarray([row["tile_visited_count"] for row in trace], dtype=np.float64)
    progress = tiles / track_tiles
    rewards = np.asarray([row["total_reward"] for row in trace], dtype=np.float64)
    speeds = np.asarray([row.get("speed", [np.nan] * 4) for row in trace], dtype=np.float64)
    actions = np.asarray([row.get("action", [[np.nan] * 3] * 4) for row in trace], dtype=np.float64)

    first_complete = [
        summary.get("first_complete_step", [None] * 4)[agent_id]
        or first_step_at_or_above(progress[:, agent_id], 1.0)
        for agent_id in range(4)
    ]
    final_rank = np.argsort(-tiles[-1]).argsort() + 1

    fig = plt.figure(figsize=(9.0, 6.6), constrained_layout=True)
    gs = fig.add_gridspec(2, 2, height_ratios=[1.08, 0.92])
    ax_prog = fig.add_subplot(gs[0, 0])
    ax_reward = fig.add_subplot(gs[0, 1])
    ax_speed = fig.add_subplot(gs[1, 0])
    ax_bar = fig.add_subplot(gs[1, 1])

    for agent_id, (label, color) in enumerate(zip(labels, colors)):
        ax_prog.plot(steps, progress[:, agent_id], color=color, lw=1.6, label=label)
        if first_complete[agent_id] is not None:
            ax_prog.axvline(first_complete[agent_id], color=color, lw=0.8, ls="--", alpha=0.55)
            ax_prog.text(first_complete[agent_id], 1.02, f"{label}\n{first_complete[agent_id]}步", color=color, fontsize=6.5, ha="center", va="bottom")
        ax_reward.plot(steps, rewards[:, agent_id], color=color, lw=1.4, label=label)
        ax_speed.plot(steps, moving_average(speeds[:, agent_id], 41), color=color, lw=1.2, label=label)

    ax_prog.set_title("a  完整在线赛局进度")
    ax_prog.set_ylabel("赛道完成比例")
    ax_prog.set_xlabel("环境步数")
    ax_prog.set_ylim(0, max(1.08, np.nanmax(progress) + 0.05))
    ax_prog.grid(axis="y", color=PALETTE["grid"], lw=0.6)
    ax_prog.legend(loc="lower right", fontsize=7)

    ax_reward.set_title("b  累计奖励")
    ax_reward.set_ylabel("累计奖励")
    ax_reward.set_xlabel("环境步数")
    ax_reward.grid(axis="y", color=PALETTE["grid"], lw=0.6)

    ax_speed.set_title("c  速度曲线（41步滑动平均）")
    ax_speed.set_ylabel("速度")
    ax_speed.set_xlabel("环境步数")
    ax_speed.grid(axis="y", color=PALETTE["grid"], lw=0.6)

    x = np.arange(len(labels))
    final_progress = progress[-1]
    bars = ax_bar.bar(x, final_progress, color=colors, width=0.62)
    ax_bar.axhline(1.0, color="#4B5563", lw=0.8, ls="--")
    ax_bar.set_title("d  终局指标")
    ax_bar.set_ylabel("最终完成比例")
    ax_bar.set_xticks(x)
    ax_bar.set_xticklabels(labels, rotation=20, ha="right")
    ax_bar.set_ylim(0, max(1.15, np.nanmax(final_progress) + 0.12))
    ax_bar.grid(axis="y", color=PALETTE["grid"], lw=0.6)
    for agent_id, rect in enumerate(bars):
        complete_text = "完圈" if final_progress[agent_id] >= 1.0 else "未完圈"
        step_text = first_complete[agent_id] if first_complete[agent_id] is not None else "-"
        ax_bar.text(
            rect.get_x() + rect.get_width() / 2,
            rect.get_height() + 0.025,
            f"{final_progress[agent_id]:.2f}\n名次{int(final_rank[agent_id])}\n{complete_text}/{step_text}",
            ha="center",
            va="bottom",
            fontsize=6.5,
            color=PALETTE["ink"],
        )

    fig.suptitle("当前算法 vs DLC世界模型：同局在线完整赛程分析", fontsize=11, fontweight="bold")
    note = (
        f"seed={summary['seed']}，赛道砖块={track_tiles}，运行={summary['steps_run']}步；"
        f"首次当前算法领先DLC：{summary.get('first_ahead_step_current_vs_dlc')}步。"
    )
    fig.text(0.01, 0.005, note, ha="left", va="bottom", fontsize=7, color="#4B5563")

    stem = out_dir / "figure_current_vs_dlc_online_full_lap_analysis"
    for ext in ["svg", "pdf", "png"]:
        fig.savefig(stem.with_suffix(f".{ext}"), dpi=600, bbox_inches="tight")
    fig.savefig(stem.with_suffix(".tiff"), dpi=600, bbox_inches="tight")
    plt.close(fig)

    source_csv = stem.with_suffix(".source.csv")
    export_source_csv(trace, summary, source_csv, labels)

    manifest = {
        "claim": "同一在线赛局中，当前算法完成整圈并早于DLC世界模型建立领先；DLC在原始对比设置下进度显著滞后。",
        "summary": str(summary_path),
        "trace": str(trace_path),
        "source_data": str(source_csv),
        "outputs": {
            ext: str(stem.with_suffix(f".{ext}"))
            for ext in ["svg", "pdf", "png", "tiff"]
        },
        "first_complete_step": first_complete,
        "final_progress": final_progress.tolist(),
        "final_rank": final_rank.astype(int).tolist(),
    }
    stem.with_suffix(".manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Plot Chinese analysis figure for current-vs-DLC online race.")
    parser.add_argument("--summary", required=True)
    parser.add_argument("--trace", required=True)
    parser.add_argument("--out-dir", default="multi_car_racing/outputs/paper_multicar_overtake_20260618/figures/online_full_lap")
    args = parser.parse_args()
    plot(Path(args.summary), Path(args.trace), Path(args.out_dir))


if __name__ == "__main__":
    main()
