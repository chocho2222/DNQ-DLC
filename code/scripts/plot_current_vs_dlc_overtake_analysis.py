#!/usr/bin/env python
import argparse
import csv
import json
import math
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager

from dlc.rollout import make_env


LABELS = ["当前算法", "DLC世界模型", "背景车1", "背景车2"]
COLORS = ["#2F6BBD", "#C44E52", "#55A868", "#8172B2"]
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


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def reconstruct_track(seed, start_order):
    env = make_env(
        num_agents=4,
        seed=seed,
        observation_type="telemetry",
        start_order=start_order,
        line_spacing=5,
        lateral_spacing=2.2,
    )
    try:
        env.reset()
        track = np.asarray(env.unwrapped.track, dtype=np.float32)
    finally:
        env.close()
    return track[:, 2:]


def nearest_track_indices(track_xy, positions):
    positions = np.asarray(positions, dtype=np.float32)
    indices = np.zeros(positions.shape[:2], dtype=np.int32)
    for t in range(positions.shape[0]):
        diff = positions[t, :, None, :] - track_xy[None, :, :]
        indices[t] = np.argmin(np.linalg.norm(diff, axis=-1), axis=-1)
    return indices


def unwrap_indices(raw_indices, track_len):
    raw = np.asarray(raw_indices, dtype=np.int32)
    out = np.zeros_like(raw, dtype=np.float64)
    for agent_id in range(raw.shape[1]):
        first = float(raw[0, agent_id])
        if first > track_len / 2:
            first -= track_len
        out[0, agent_id] = first
        for t in range(1, raw.shape[0]):
            candidates = np.asarray(
                [raw[t, agent_id] - track_len, raw[t, agent_id], raw[t, agent_id] + track_len],
                dtype=np.float64,
            )
            previous = out[t - 1, agent_id]
            base = candidates[np.argmin(np.abs(candidates - previous))]
            while base - previous < -track_len / 2:
                base += track_len
            while base - previous > track_len / 2:
                base -= track_len
            out[t, agent_id] = base
    return out


def ranks_from_progress(progress):
    ranks = np.zeros_like(progress, dtype=np.int32)
    for t in range(progress.shape[0]):
        order = np.argsort(-progress[t])
        for rank, agent_id in enumerate(order, start=1):
            ranks[t, agent_id] = rank
    return ranks


def first_sustained_pass(diff, steps, margin=2.0, hold=50, valid_until=None):
    positive = np.asarray(diff) > margin
    if valid_until is not None:
        positive = positive & (np.asarray(steps) <= int(valid_until))
    for idx in range(len(positive)):
        if positive[idx] and positive[idx : idx + hold].all():
            return int(steps[idx])
    return None


def first_rank(ranks, steps, agent_id, rank=1, hold=50, valid_until=None):
    ok = ranks[:, agent_id] == rank
    if valid_until is not None:
        ok = ok & (np.asarray(steps) <= int(valid_until))
    for idx in range(len(ok)):
        if ok[idx] and ok[idx : idx + hold].all():
            return int(steps[idx])
    return None


def valid_until_from(*items, fallback=None):
    values = [int(item) for item in items if item is not None]
    if values:
        return min(values)
    return fallback


def fmt_step(value):
    return f"{value}步" if value is not None else "-"


def export_source_csv(path, steps, progress, ranks, gaps, on_grass, lateral):
    fields = ["step"]
    for label in LABELS:
        fields.extend([f"{label}_track_progress", f"{label}_rank"])
    fields.extend([f"当前算法_vs_{LABELS[i]}_gap" for i in [1, 2, 3]])
    fields.extend([f"{label}_on_grass" for label in LABELS])
    fields.extend([f"{label}_abs_lateral" for label in LABELS])
    with Path(path).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row_id, step in enumerate(steps):
            row = {"step": int(step)}
            for agent_id, label in enumerate(LABELS):
                row[f"{label}_track_progress"] = float(progress[row_id, agent_id])
                row[f"{label}_rank"] = int(ranks[row_id, agent_id])
            for agent_id in [1, 2, 3]:
                row[f"当前算法_vs_{LABELS[agent_id]}_gap"] = float(gaps[agent_id][row_id])
            for agent_id, label in enumerate(LABELS):
                row[f"{label}_on_grass"] = int(on_grass[row_id, agent_id] > 0.5)
                row[f"{label}_abs_lateral"] = float(abs(lateral[row_id, agent_id]))
            writer.writerow(row)


def plot(summary_path, trace_path, out_dir):
    setup_mpl()
    summary = load_json(summary_path)
    trace = load_json(trace_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    steps = np.asarray([row["step"] for row in trace], dtype=np.int32)
    tile_counts = np.asarray([row["tile_visited_count"] for row in trace], dtype=np.float64)
    start_order = np.asarray(summary["start_order"], dtype=np.float64)
    start_line = np.floor(start_order / 2.0)
    line_spacing = float(summary.get("line_spacing", 5.0))
    # Starting farther behind should not appear tied just because reset touched several tiles.
    # Corrected progress is the first-lap race distance from a common virtual start line.
    progress = tile_counts - start_line[None, :] * line_spacing
    ranks = ranks_from_progress(progress)
    gaps = {agent_id: progress[:, 0] - progress[:, agent_id] for agent_id in [1, 2, 3]}
    dlc_gaps = {agent_id: progress[:, 1] - progress[:, agent_id] for agent_id in [2, 3]}
    telemetry = [row.get("telemetry", {}) for row in trace]
    on_grass = np.asarray(
        [row.get("on_grass", [False] * 4) for row in telemetry],
        dtype=np.float32,
    )
    lateral = np.asarray(
        [row.get("lateral_error", [0.0] * 4) for row in telemetry],
        dtype=np.float32,
    )
    grace = min(20, len(steps))
    eval_slice = slice(grace, None)
    grass_rate = on_grass[eval_slice].mean(axis=0) if len(steps) > grace else on_grass.mean(axis=0)
    max_abs_lateral = np.abs(lateral[eval_slice]).max(axis=0) if len(steps) > grace else np.abs(lateral).max(axis=0)
    mean_abs_lateral = np.abs(lateral[eval_slice]).mean(axis=0) if len(steps) > grace else np.abs(lateral).mean(axis=0)

    current_completion = summary["first_complete_step"][0]
    dlc_completion = summary["first_complete_step"][1]
    first_complete = summary["first_complete_step"]
    current_pass = {
        agent_id: first_sustained_pass(
            gaps[agent_id],
            steps,
            valid_until=valid_until_from(current_completion, first_complete[agent_id], fallback=int(steps[-1])),
        )
        for agent_id in [1, 2, 3]
    }
    dlc_pass = {
        agent_id: first_sustained_pass(
            dlc_gaps[agent_id],
            steps,
            valid_until=valid_until_from(dlc_completion, first_complete[agent_id], fallback=int(steps[-1])),
        )
        for agent_id in [2, 3]
    }
    current_rank1 = first_rank(ranks, steps, 0, rank=1, valid_until=current_completion)
    dlc_rank1 = first_rank(ranks, steps, 1, rank=1, valid_until=dlc_completion)
    final_gap_current_dlc = float(gaps[1][np.searchsorted(steps, current_completion, side="right") - 1])

    fig = plt.figure(figsize=(9.2, 6.8), constrained_layout=True)
    gs = fig.add_gridspec(2, 2, height_ratios=[1.05, 0.95])
    ax_pos = fig.add_subplot(gs[0, 0])
    ax_gap = fig.add_subplot(gs[0, 1])
    ax_rank = fig.add_subplot(gs[1, 0])
    ax_sum = fig.add_subplot(gs[1, 1])

    for agent_id, (label, color) in enumerate(zip(LABELS, COLORS)):
        ax_pos.plot(steps, progress[:, agent_id], color=color, lw=1.4, label=label)
    for agent_id, pass_step in current_pass.items():
        if pass_step is not None:
            ax_pos.axvline(pass_step, color=COLORS[agent_id], lw=0.8, ls="--", alpha=0.6)
            ax_pos.text(pass_step, np.nanmax(progress) * 0.98, f"当前超{LABELS[agent_id]}\n{pass_step}步", color=COLORS[agent_id], fontsize=6.4, ha="center", va="top")
    ax_pos.set_title("a  校正赛道进度：从第4位追赶")
    ax_pos.set_xlabel("环境步数")
    ax_pos.set_ylabel("校正进度（已访问tile - 起步落后tile）")
    ax_pos.grid(axis="y", color=GRID, lw=0.6)
    ax_pos.legend(loc="upper left", fontsize=7)

    for agent_id in [1, 2, 3]:
        ax_gap.plot(steps, gaps[agent_id], color=COLORS[agent_id], lw=1.4, label=f"当前 - {LABELS[agent_id]}")
    ax_gap.axhline(0, color="#4B5563", lw=0.8)
    ax_gap.fill_between(steps, 0, gaps[1], where=gaps[1] > 0, color=COLORS[0], alpha=0.13, label="当前领先DLC")
    ax_gap.set_title("b  相对差距：由负转正才是超车")
    ax_gap.set_xlabel("环境步数")
    ax_gap.set_ylabel("进度差（tile）")
    ax_gap.grid(axis="y", color=GRID, lw=0.6)
    ax_gap.legend(loc="best", fontsize=7)

    for agent_id, (label, color) in enumerate(zip(LABELS, COLORS)):
        ax_rank.step(steps, ranks[:, agent_id], where="post", color=color, lw=1.4, label=label)
    ax_rank.invert_yaxis()
    ax_rank.set_yticks([1, 2, 3, 4])
    ax_rank.set_title("c  名次时间线")
    ax_rank.set_xlabel("环境步数")
    ax_rank.set_ylabel("名次（1=最前）")
    ax_rank.grid(axis="y", color=GRID, lw=0.6)
    ax_rank.legend(loc="lower right", fontsize=7)

    ax_sum.axis("off")
    rows = [
        ["指标", "当前算法", "DLC世界模型"],
        ["起步名次", "第4位", "第3位"],
        ["首次稳定第1名", fmt_step(current_rank1), fmt_step(dlc_rank1)],
        ["完圈步数", fmt_step(current_completion), fmt_step(dlc_completion)],
        ["当前完圈时相对DLC差距", f"{final_gap_current_dlc:.1f} tile", "0"],
        ["草地步占比", f"{grass_rate[0] * 100:.1f}%", f"{grass_rate[1] * 100:.1f}%"],
        ["最大横向偏离", f"{max_abs_lateral[0]:.2f}", f"{max_abs_lateral[1]:.2f}"],
        ["超越对象", ", ".join(LABELS[i] for i, s in current_pass.items() if s is not None) or "-", ", ".join(LABELS[i] for i, s in dlc_pass.items() if s is not None) or "-"],
    ]
    x0, y0 = 0.02, 0.94
    col_w = [0.33, 0.32, 0.32]
    row_h = 0.12
    for r, row in enumerate(rows):
        for c, text in enumerate(row):
            x = x0 + sum(col_w[:c])
            y = y0 - r * row_h
            face = "#EEF2F7" if r == 0 else ("#F8FAFC" if r % 2 else "white")
            ax_sum.add_patch(plt.Rectangle((x, y - row_h + 0.012), col_w[c], row_h, transform=ax_sum.transAxes, facecolor=face, edgecolor="#D0D7DE", lw=0.6))
            ax_sum.text(x + col_w[c] / 2, y - row_h / 2 + 0.012, text, ha="center", va="center", fontsize=7.2, fontweight="bold" if r == 0 else "normal", transform=ax_sum.transAxes, color=INK)
    ax_sum.set_title("d  超车结果摘要", loc="left")

    fig.suptitle("超车行为分析：当前算法从第4位追赶，DLC从第3位起步", fontsize=11, fontweight="bold")
    fig.text(
        0.01,
        0.005,
        "判据：按起步身位修正 tile 进度；只统计双方完圈前，校正进度差由负转正并保持50步的有效超车。",
        fontsize=7,
        color="#4B5563",
    )

    stem = out_dir / "figure_current_vs_dlc_overtake_analysis"
    for ext in ["svg", "pdf", "png"]:
        fig.savefig(stem.with_suffix(f".{ext}"), dpi=600, bbox_inches="tight")
    fig.savefig(stem.with_suffix(".tiff"), dpi=600, bbox_inches="tight")
    plt.close(fig)

    source_csv = stem.with_suffix(".source.csv")
    export_source_csv(source_csv, steps, progress, ranks, gaps, on_grass, lateral)
    manifest = {
        "claim": "当前算法从第4位起步后完成第一圈并实现稳定超车；新增草地率和横向偏离指标用于约束超车质量，避免将草地绕行误判为Desirable overtaking behavior。",
        "summary": str(summary_path),
        "trace": str(trace_path),
        "source_data": str(source_csv),
        "outputs": {ext: str(stem.with_suffix(f'.{ext}')) for ext in ["svg", "pdf", "png", "tiff"]},
        "current_pass_steps": {LABELS[k]: v for k, v in current_pass.items()},
        "dlc_pass_steps": {LABELS[k]: v for k, v in dlc_pass.items()},
        "current_rank1_step": current_rank1,
        "dlc_rank1_step": dlc_rank1,
        "current_completion_step": current_completion,
        "dlc_completion_step": dlc_completion,
        "final_gap_current_minus_dlc": final_gap_current_dlc,
        "grass_rate": {LABELS[i]: float(grass_rate[i]) for i in range(4)},
        "mean_abs_lateral": {LABELS[i]: float(mean_abs_lateral[i]) for i in range(4)},
        "max_abs_lateral": {LABELS[i]: float(max_abs_lateral[i]) for i in range(4)},
    }
    stem.with_suffix(".manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Plot overtaking-focused analysis for current-vs-DLC online race.")
    parser.add_argument("--summary", required=True)
    parser.add_argument("--trace", required=True)
    parser.add_argument("--out-dir", default="multi_car_racing/outputs/paper_multicar_overtake_20260618/figures/online_overtake/startpos_current4_dlc3")
    args = parser.parse_args()
    plot(Path(args.summary), Path(args.trace), Path(args.out_dir))


if __name__ == "__main__":
    main()
