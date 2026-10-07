#!/usr/bin/env python
import csv
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageSequence

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.colors import LinearSegmentedColormap


mpl.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Noto Sans CJK SC", "Source Han Sans SC", "Arial", "DejaVu Sans", "sans-serif"],
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


def register_cjk_font():
    candidates = [
        "/usr/share/fonts/truetype/arphic/ukai.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    ]
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            font_manager.fontManager.addfont(str(path))
            family = font_manager.FontProperties(fname=str(path)).get_name()
            mpl.rcParams["font.family"] = family
            mpl.rcParams["font.sans-serif"] = [family, "Arial", "DejaVu Sans", "sans-serif"]
            return path
    return None


PALETTE = {
    "current": "#2F6EA6",
    "dlc": "#C65D4A",
    "current_light": "#DCE9F5",
    "dlc_light": "#F6DFDA",
    "ink": "#1F2933",
    "grid": "#D9E1E8",
    "muted": "#6B7280",
}


def load_json(path):
    path = Path(path)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_local_path(path_str):
    path = Path(path_str)
    if path.is_absolute():
        return path
    if path.parts and path.parts[0] == "multi_car_racing":
        return Path.cwd() / path
    return Path.cwd() / "multi_car_racing" / path


def save_pub(fig, stem):
    fig.savefig(f"{stem}.svg", bbox_inches="tight")
    fig.savefig(f"{stem}.pdf", bbox_inches="tight")
    fig.savefig(f"{stem}.tiff", dpi=600, bbox_inches="tight")
    fig.savefig(f"{stem}.png", dpi=300, bbox_inches="tight")


def safe_num(value, default=np.nan):
    if value is None:
        return default
    if isinstance(value, bool):
        return float(value)
    try:
        if isinstance(value, (list, tuple)):
            return float(value[-1]) if value else default
        return float(value)
    except Exception:
        return default


def read_validation(path, family, variant):
    data = load_json(path)
    if not data:
        return None
    summary = data.get("summary", {}) or {}
    metrics = data.get("metrics", {}) or {}
    tile_progress = safe_num(metrics.get("target_tile_progress"))
    if math.isnan(tile_progress):
        tiles = summary.get("tile_visited_count", [])
        track_tiles = safe_num(summary.get("track_tiles"), default=np.nan)
        if tiles and not math.isnan(track_tiles) and track_tiles > 0:
            tile_progress = float(tiles[-1]) / float(track_tiles)
    grass_rate = summary.get("grass_rate")
    if isinstance(grass_rate, list) and grass_rate:
        grass_rate = float(grass_rate[-1])
    else:
        grass_rate = safe_num(summary.get("target_grass_rate"), default=safe_num(metrics.get("target_grass_rate")))
    first_ahead = summary.get("first_ahead_step")
    if first_ahead is None:
        first_ahead = metrics.get("first_ahead_step")
    if first_ahead is not None:
        first_ahead = int(first_ahead)
    return {
        "family": family,
        "variant": variant,
        "seed": int(summary.get("seed", -1)),
        "track_tiles": int(summary.get("track_tiles", 267)),
        "status": data.get("status", "UNKNOWN"),
        "strict_pass": 1 if data.get("status") == "PASS" else 0,
        "completed_lap": 1 if summary.get("target_completed_lap") else 0,
        "final_rank": int(summary.get("target_final_rank_by_tiles")) if summary.get("target_final_rank_by_tiles") is not None else None,
        "first_ahead_step": first_ahead,
        "grass_rate": grass_rate,
        "target_progress": tile_progress,
        "steps_run": int(summary.get("steps_run", 0)),
        "gif": summary.get("gif") or path.with_suffix(".gif").as_posix(),
        "trace": str(resolve_local_path(summary.get("gif") or path.with_suffix(".gif").as_posix()).with_suffix(".trace.json")),
        "summary_path": str(path),
    }


def collect_records(root):
    records = []
    for path in sorted((root / "evaluations").glob("graph_bc_seed_*/validation.json")):
        rec = read_validation(path, "当前算法", "graph_bc")
        if rec:
            records.append(rec)
    for path in sorted((root / "evaluations").glob("dlc_*_seed_*/validation.json")):
        variant = path.parent.name.replace("dlc_", "").replace("_seed_3", "")
        rec = read_validation(path, "DLC world model", variant)
        if rec:
            records.append(rec)
    return records


def family_summary(records):
    grouped = {}
    for rec in records:
        grouped.setdefault(rec["family"], []).append(rec)
    rows = []
    for family, items in grouped.items():
        rows.append(
            {
                "family": family,
                "n": len(items),
                "strict_pass_rate": float(np.mean([r["strict_pass"] for r in items])),
                "completed_lap_rate": float(np.mean([r["completed_lap"] for r in items])),
                "first_ahead_rate": float(np.mean([1 if r["first_ahead_step"] is not None else 0 for r in items])),
                "mean_target_progress": float(np.mean([r["target_progress"] for r in items if not math.isnan(r["target_progress"]) ])),
                "mean_final_rank": float(np.mean([r["final_rank"] for r in items if r["final_rank"] is not None])),
                "mean_grass_rate": float(np.mean([r["grass_rate"] for r in items if not math.isnan(r["grass_rate"]) ])),
                "mean_steps": float(np.mean([r["steps_run"] for r in items])),
            }
        )
    order = ["当前算法", "DLC world model"]
    rows.sort(key=lambda x: order.index(x["family"]) if x["family"] in order else 99)
    return rows


def write_source_csv(records, family_rows, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "kind",
        "family",
        "variant",
        "seed",
        "status",
        "track_tiles",
        "strict_pass",
        "completed_lap",
        "final_rank",
        "first_ahead_step",
        "grass_rate",
        "target_progress",
        "steps_run",
        "n",
        "strict_pass_rate",
        "completed_lap_rate",
        "first_ahead_rate",
        "mean_target_progress",
        "mean_final_rank",
        "mean_grass_rate",
        "mean_steps",
        "gif",
        "trace",
        "summary_path",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for rec in records:
            row = {k: "" for k in fieldnames}
            row.update(rec)
            row["kind"] = "run"
            writer.writerow(row)
        for rec in family_rows:
            row = {k: "" for k in fieldnames}
            row.update(rec)
            row["kind"] = "family"
            writer.writerow(row)


def chinese_font(size=24):
    candidates = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/arphic/ukai.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for cand in candidates:
        if Path(cand).exists():
            return ImageFont.truetype(cand, size=size)
    return ImageFont.load_default()


def draw_family_bars(ax, family_rows):
    metrics = [
        ("strict_pass_rate", "严格通过率"),
        ("completed_lap_rate", "完成一圈率"),
        ("first_ahead_rate", "首次超车率"),
        ("mean_target_progress", "平均目标进度"),
    ]
    x = np.arange(len(metrics))
    width = 0.32
    current = next(row for row in family_rows if row["family"] == "当前算法")
    dlc = next(row for row in family_rows if row["family"] == "DLC world model")
    current_vals = [current[k] for k, _ in metrics]
    dlc_vals = [dlc[k] for k, _ in metrics]
    ax.bar(x - width / 2, current_vals, width=width, color=PALETTE["current"], label=f"当前算法 (n={current['n']})")
    ax.bar(x + width / 2, dlc_vals, width=width, color=PALETTE["dlc"], label=f"DLC world model (n={dlc['n']})")
    for xi, val in zip(x - width / 2, current_vals):
        ax.text(xi, min(val + 0.03, 1.03), f"{val:.2f}", ha="center", va="bottom", fontsize=7)
    for xi, val in zip(x + width / 2, dlc_vals):
        ax.text(xi, min(val + 0.03, 1.03), f"{val:.2f}", ha="center", va="bottom", fontsize=7)
    ax.set_ylim(0, 1.08)
    ax.set_xticks(x, [m[1] for m in metrics], rotation=0)
    ax.set_ylabel("比例 / 得分")
    ax.set_title("a  家族级对比")
    ax.grid(axis="y", color=PALETTE["grid"], linewidth=0.6)
    ax.legend(loc="upper right", ncols=1, fontsize=7)


def draw_failure_scatter(ax, records):
    colors = {"当前算法": PALETTE["current"], "DLC world model": PALETTE["dlc"]}
    for family in ["当前算法", "DLC world model"]:
        subset = [r for r in records if r["family"] == family]
        xs = [r["grass_rate"] for r in subset]
        ys = [r["final_rank"] for r in subset]
        ax.scatter(xs, ys, s=46, color=colors[family], edgecolor="white", linewidth=0.7, label=family, zorder=3)
        for r in subset:
            label = f"seed{r['seed']}" if family == "当前算法" else r["variant"].replace("_", " ")
            ax.text(r["grass_rate"] + 0.01, r["final_rank"] + 0.03, label, fontsize=6.5, color=PALETTE["ink"])
    ax.invert_yaxis()
    ax.set_xlabel("目标车草地率（越低越好）")
    ax.set_ylabel("最终名次（越小越好）")
    ax.set_title("b  失败模式散点")
    ax.grid(color=PALETTE["grid"], linewidth=0.6)
    ax.legend(loc="lower right", fontsize=7)


def draw_metric_table(ax, records):
    cols = [
        ("family", "方法族"),
        ("seed", "种子"),
        ("status", "结果"),
        ("final_rank", "最终名次"),
        ("first_ahead_step", "首次超车步"),
        ("grass_rate", "草地率"),
        ("target_progress", "目标进度"),
        ("steps_run", "总步数"),
    ]
    rows = records
    ax.set_axis_off()
    header_color = "#F2F4F7"
    nrows = len(rows) + 1
    ncols = len(cols)
    widths = [0.18, 0.08, 0.10, 0.10, 0.12, 0.10, 0.10, 0.10]
    widths = [w / sum(widths) for w in widths]
    heights = [0.12] + [0.11] * len(rows)
    x0, y0, wtot, htot = 0.02, 0.03, 0.96, 0.92
    y = y0 + htot
    # header
    x = x0
    for j, (_, label) in enumerate(cols):
        cw = wtot * widths[j]
        ch = htot * heights[0]
        cell = ax.add_patch(plt.Rectangle((x, y - ch), cw, ch, transform=ax.transAxes, facecolor=header_color, edgecolor="#D0D7DE", linewidth=0.6))
        ax.text(x + cw / 2, y - ch / 2, label, ha="center", va="center", fontsize=7, fontweight="bold", transform=ax.transAxes)
        x += cw
    y -= htot * heights[0]
    # body
    for i, row in enumerate(rows):
        x = x0
        family = row["family"]
        row_face = "#EEF5FB" if family == "当前算法" else "#FAECE8"
        values = [
            "当前算法" if family == "当前算法" else "DLC world model",
            f"{row['seed']}",
            "通过" if row["status"] == "PASS" else "失败",
            f"{row['final_rank']}" if row["final_rank"] is not None else "NA",
            f"{row['first_ahead_step']}" if row["first_ahead_step"] is not None else "未超车",
            f"{row['grass_rate']:.3f}" if not math.isnan(row["grass_rate"]) else "NA",
            f"{row['target_progress']:.3f}" if not math.isnan(row["target_progress"]) else "NA",
            f"{row['steps_run']}",
        ]
        for j, val in enumerate(values):
            cw = wtot * widths[j]
            ch = htot * heights[min(i + 1, len(heights) - 1)]
            face = row_face if j in {0, 1, 2} else "white"
            if j == 2:
                face = "#DFF0E0" if row["status"] == "PASS" else "#FBE3DF"
            elif j == 3 and row["final_rank"] is not None:
                face = "#E8F2FB" if row["final_rank"] == 1 else "#F6F0F0"
            elif j == 4:
                face = "#E8F7EE" if row["first_ahead_step"] is not None else "#F7F7F7"
            elif j == 5:
                face = "#F7FBFF" if row["grass_rate"] <= 0.05 else "#FDEDEA"
            elif j == 6:
                face = "#EDF7F2" if row["target_progress"] >= 0.95 else "#FDEDEA"
            cell = ax.add_patch(plt.Rectangle((x, y - ch), cw, ch, transform=ax.transAxes, facecolor=face, edgecolor="#D0D7DE", linewidth=0.6))
            ax.text(x + cw / 2, y - ch / 2, val, ha="center", va="center", fontsize=6.8, transform=ax.transAxes)
            x += cw
        y -= htot * heights[min(i + 1, len(heights) - 1)]
    ax.text(0.0, 1.02, "c  逐条运行明细", transform=ax.transAxes, fontsize=10, fontweight="bold", ha="left")


def plot_figure(root, records, family_rows, out_dir):
    fig = plt.figure(figsize=(9.2, 6.8), constrained_layout=True)
    gs = fig.add_gridspec(2, 2, height_ratios=[1.0, 1.22], width_ratios=[1.0, 1.0])
    ax_a = fig.add_subplot(gs[0, 0])
    ax_b = fig.add_subplot(gs[0, 1])
    ax_c = fig.add_subplot(gs[1, :])
    draw_family_bars(ax_a, family_rows)
    draw_failure_scatter(ax_b, records)
    draw_metric_table(ax_c, records)
    fig.suptitle("当前算法 vs DLC world model 中文对比", fontsize=11, fontweight="bold", y=1.01)
    out_stem = out_dir / "figure_compare_current_vs_dlc_world"
    save_pub(fig, out_stem)
    plt.close(fig)
    manifest = {
        "figure": "figure_compare_current_vs_dlc_world",
        "claim": "当前算法在严格完整圈和首次超车上明显优于 DLC world model，但仍存在 seed 敏感性；DLC world model 在当前评测条件下未完成完整圈。",
        "archetype": "quantitative grid",
        "panels": {
            "a": "家族级严格通过率、完成一圈率、首次超车率和平均目标进度对比。",
            "b": "目标车草地率与最终名次的失败模式散点。",
            "c": "逐条运行明细表，保留 seed、结果、超车步、草地率、进度和总步数。",
        },
        "source_data": str(out_dir / "figure_compare_current_vs_dlc_world_source.csv"),
        "exports": [str(out_stem) + ext for ext in [".svg", ".pdf", ".tiff", ".png"]],
        "review_risks": [
            "DLC world model 仅包含三个代表性变体，不是多 seed 重复实验。",
            "当前算法仅包含当前论文包里可用的三个 seed。",
            "figure 中的 family 汇总是基于现有保存结果的描述性比较，不应被解释为新的统计显著性结论。",
        ],
    }
    (out_dir / "figure_compare_current_vs_dlc_world_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def load_trace(path):
    data = load_json(path)
    if not isinstance(data, list):
        return []
    return data


def compute_step_metrics(trace, track_tiles, target_agent=3):
    steps = []
    progress = []
    ranks = []
    grass = []
    ahead_step = None
    grass_count = 0
    for item in trace:
        step = int(item.get("step", len(steps) + 1))
        tiles = item.get("tile_visited_count", [])
        on_grass = item.get("on_grass", [])
        if len(tiles) <= target_agent:
            continue
        target_tiles = float(tiles[target_agent])
        step_progress = target_tiles / max(float(track_tiles), 1.0)
        sorted_tiles = sorted([(float(t), idx) for idx, t in enumerate(tiles)], key=lambda x: (-x[0], x[1]))
        rank = next((idx + 1 for idx, (_, agent) in enumerate(sorted_tiles) if agent == target_agent), len(tiles))
        grass_count += float(on_grass[target_agent]) if len(on_grass) > target_agent else 0.0
        grass_rate = grass_count / max(step, 1)
        if ahead_step is None and rank == 1:
            ahead_step = step
        steps.append(step)
        progress.append(step_progress)
        ranks.append(rank)
        grass.append(grass_rate)
    return {
        "steps": np.asarray(steps, dtype=np.float64),
        "progress": np.asarray(progress, dtype=np.float64),
        "rank": np.asarray(ranks, dtype=np.float64),
        "grass": np.asarray(grass, dtype=np.float64),
        "ahead_step": ahead_step,
    }


def load_gif_frames(path):
    frames = []
    with Image.open(path) as im:
        for frame in ImageSequence.Iterator(im):
            frames.append(frame.convert("RGBA"))
    return frames


def draw_label_band(draw, box, title, lines, fill, title_font, body_font):
    x1, y1, x2, y2 = box
    draw.rounded_rectangle(box, radius=12, fill=fill, outline=(220, 226, 233, 255), width=2)
    draw.text((x1 + 16, y1 + 10), title, fill=(31, 41, 55, 255), font=title_font)
    y = y1 + 44
    for line in lines:
        draw.text((x1 + 16, y), line, fill=(31, 41, 55, 255), font=body_font)
        y += 24


def render_synced_online_gif(left_record, right_record, out_path, left_label, right_label):
    left_frames = load_gif_frames(resolve_local_path(left_record["gif"]))
    right_frames = load_gif_frames(resolve_local_path(right_record["gif"]))
    left_trace = load_trace(resolve_local_path(left_record["trace"]))
    right_trace = load_trace(resolve_local_path(right_record["trace"]))
    if not left_frames or not right_frames:
        raise RuntimeError("GIF frames not found")

    left_track = int(left_record.get("track_tiles", 267))
    right_track = int(right_record.get("track_tiles", 267))
    left_metrics = compute_step_metrics(left_trace, track_tiles=left_track, target_agent=3)
    right_metrics = compute_step_metrics(right_trace, track_tiles=right_track, target_agent=3)

    target_size = (
        min(min(im.width for im in left_frames), min(im.width for im in right_frames)),
        min(min(im.height for im in left_frames), min(im.height for im in right_frames)),
    )
    left_frames = [im.resize(target_size, Image.Resampling.LANCZOS) for im in left_frames]
    right_frames = [im.resize(target_size, Image.Resampling.LANCZOS) for im in right_frames]

    n_out = max(len(left_frames), len(right_frames))
    title_font = chinese_font(24)
    body_font = chinese_font(18)
    small_font = chinese_font(16)
    frame_w, frame_h = target_size
    top_h = 118
    bottom_h = 62
    gap = 18
    canvas_w = frame_w * 2 + gap
    canvas_h = top_h + frame_h + bottom_h
    out_frames = []

    def sample(seq, idx, total):
        if not seq:
            return None
        if total <= 1:
            return seq[-1]
        t = idx / (total - 1)
        j = int(round(t * (len(seq) - 1)))
        return seq[min(max(j, 0), len(seq) - 1)]

    def sample_metrics(metrics, idx, total):
        if total <= 1 or len(metrics["steps"]) == 0:
            return 0, 0.0, 0.0, 0.0
        t = idx / (total - 1)
        j = int(round(t * (len(metrics["steps"]) - 1)))
        j = min(max(j, 0), len(metrics["steps"]) - 1)
        return (
            int(metrics["steps"][j]),
            float(metrics["progress"][j]),
            float(metrics["rank"][j]),
            float(metrics["grass"][j]),
        )

    for i in range(n_out):
        lf = sample(left_frames, i, n_out)
        rf = sample(right_frames, i, n_out)
        l_step, l_prog, l_rank, l_grass = sample_metrics(left_metrics, i, n_out)
        r_step, r_prog, r_rank, r_grass = sample_metrics(right_metrics, i, n_out)
        canvas = Image.new("RGBA", (canvas_w, canvas_h), (255, 255, 255, 255))
        draw = ImageDraw.Draw(canvas)
        draw.rectangle([0, 0, canvas_w, top_h], fill=(244, 247, 250, 255))
        draw.text((18, 14), "在线运行对比", fill=(31, 41, 55, 255), font=title_font)
        draw.text((18, 52), f"左：{left_label}   右：{right_label}", fill=(75, 85, 99, 255), font=body_font)
        draw.line([canvas_w / 2, top_h + 8, canvas_w / 2, top_h + frame_h + 4], fill=(210, 215, 220, 255), width=2)

        draw_label_band(
            draw,
            (14, 78, frame_w - 14, 202),
            "当前算法",
            [
                f"step {l_step}/{len(left_trace)}",
                f"目标进度 {l_prog:.3f}  名次 {int(l_rank)}  草地率 {l_grass:.3f}",
                "已完成一圈" if l_prog >= 1.0 else "运行中",
            ],
            (220, 232, 245, 255),
            body_font,
            small_font,
        )
        draw_label_band(
            draw,
            (frame_w + gap + 14, 78, canvas_w - 14, 202),
            "DLC world model",
            [
                f"step {r_step}/{len(right_trace)}",
                f"目标进度 {r_prog:.3f}  名次 {int(r_rank)}  草地率 {r_grass:.3f}",
                "已完成一圈" if r_prog >= 1.0 else "运行中",
            ],
            (247, 229, 225, 255),
            body_font,
            small_font,
        )

        canvas.alpha_composite(lf, (0, top_h))
        canvas.alpha_composite(rf, (frame_w + gap, top_h))

        draw.rounded_rectangle((18, top_h + frame_h + 12, canvas_w - 18, canvas_h - 14), radius=14, fill=(248, 250, 252, 255), outline=(218, 223, 230, 255), width=2)
        draw.text((34, top_h + frame_h + 24), f"同步帧 {i+1}/{n_out}", fill=(31, 41, 55, 255), font=body_font)
        draw.text((34, top_h + frame_h + 48), "左侧在 2093 步完成全圈，右侧持续到 3200 步仍未完成；这是在线轨迹层面的差距，不是终点统计。", fill=(75, 85, 99, 255), font=small_font)

        out_frames.append(canvas.convert("P", palette=Image.Palette.ADAPTIVE))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_frames[0].save(
        out_path,
        save_all=True,
        append_images=out_frames[1:],
        duration=110,
        loop=0,
        optimize=True,
    )
    return {
        "left": str(resolve_local_path(left_record["gif"])),
        "right": str(resolve_local_path(right_record["gif"])),
        "out": str(out_path),
        "left_frames": len(left_frames),
        "right_frames": len(right_frames),
        "output_frames": n_out,
        "left_track_tiles": left_track,
        "right_track_tiles": right_track,
    }


def plot_online_timeline(root, current_record, dlc_record, out_dir):
    import matplotlib.pyplot as plt
    current_trace = load_trace(resolve_local_path(current_record["trace"]))
    dlc_trace = load_trace(resolve_local_path(dlc_record["trace"]))
    current_metrics = compute_step_metrics(current_trace, 267, 3)
    dlc_metrics = compute_step_metrics(dlc_trace, 267, 3)

    fig, axes = plt.subplots(3, 1, figsize=(8.0, 6.6), sharex=True, constrained_layout=True)
    colors = {"当前算法": PALETTE["current"], "DLC world model": PALETTE["dlc"]}
    series = [("当前算法", current_metrics), ("DLC world model", dlc_metrics)]

    for name, metrics in series:
        axes[0].plot(metrics["steps"], metrics["progress"], lw=2.0, color=colors[name], label=name)
        axes[1].plot(metrics["steps"], metrics["rank"], lw=2.0, color=colors[name], label=name)
        axes[2].plot(metrics["steps"], metrics["grass"], lw=2.0, color=colors[name], label=name)

    axes[0].axhline(1.0, color=PALETTE["muted"], lw=1.0, ls="--")
    axes[0].set_ylabel("目标进度")
    axes[0].set_title("a  目标进度随在线运行推进")
    axes[1].invert_yaxis()
    axes[1].set_ylabel("名次")
    axes[1].set_title("b  目标车名次变化")
    axes[2].set_ylabel("累计草地率")
    axes[2].set_xlabel("在线步数")
    axes[2].set_title("c  累计草地率变化")
    for ax in axes:
        ax.grid(axis="y", color=PALETTE["grid"], lw=0.6)
        ax.legend(loc="best", fontsize=7)
        ax.tick_params(labelsize=7)
    axes[0].text(
        0.01,
        0.05,
        "当前算法首次超车更早，随后稳定逼近并完成全圈；DLC world model 早期进度偏低且名次长期滞后。",
        transform=axes[0].transAxes,
        fontsize=7.5,
        color=PALETTE["ink"],
    )

    out_stem = out_dir / "figure_compare_current_vs_dlc_world_timeline"
    save_pub(fig, out_stem)
    plt.close(fig)


def render_comparison_gif(left_path, right_path, out_path, left_label, right_label):
    left_frames = load_gif_frames(left_path)
    right_frames = load_gif_frames(right_path)
    if not left_frames or not right_frames:
        raise RuntimeError("GIF frames not found")
    target_h = min(min(im.height for im in left_frames), min(im.height for im in right_frames))
    target_w = min(min(im.width for im in left_frames), min(im.width for im in right_frames))
    target_size = (target_w, target_h)
    left_frames = [im.resize(target_size, Image.Resampling.LANCZOS) for im in left_frames]
    right_frames = [im.resize(target_size, Image.Resampling.LANCZOS) for im in right_frames]
    max_len = max(len(left_frames), len(right_frames))
    font = chinese_font(24)
    small = chinese_font(18)
    out_frames = []
    top_h = 56
    gap = 14
    canvas_w = target_w * 2 + gap
    canvas_h = target_h + top_h
    for i in range(max_len):
        lf = left_frames[min(i, len(left_frames) - 1)]
        rf = right_frames[min(i, len(right_frames) - 1)]
        canvas = Image.new("RGBA", (canvas_w, canvas_h), (255, 255, 255, 255))
        draw = ImageDraw.Draw(canvas)
        draw.rectangle([0, 0, canvas_w, top_h], fill=(245, 247, 250, 255))
        draw.text((20, 12), left_label, fill=(31, 41, 55, 255), font=font)
        right_text_w = draw.textlength(right_label, font=font)
        draw.text((canvas_w - right_text_w - 20, 12), right_label, fill=(31, 41, 55, 255), font=font)
        draw.line([target_w + gap / 2, top_h, target_w + gap / 2, canvas_h], fill=(210, 215, 220, 255), width=2)
        canvas.alpha_composite(lf, (0, top_h))
        canvas.alpha_composite(rf, (target_w + gap, top_h))
        draw.text((canvas_w / 2 - 70, canvas_h - 28), f"帧 {i+1}/{max_len}", fill=(107, 114, 128, 255), font=small)
        out_frames.append(canvas.convert("P", palette=Image.Palette.ADAPTIVE))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_frames[0].save(
        out_path,
        save_all=True,
        append_images=out_frames[1:],
        duration=110,
        loop=0,
        optimize=True,
    )
    return {
        "left": str(left_path),
        "right": str(right_path),
        "out": str(out_path),
        "left_label": left_label,
        "right_label": right_label,
        "left_frames": len(left_frames),
        "right_frames": len(right_frames),
    }


def main():
    register_cjk_font()
    root = Path("multi_car_racing/outputs/paper_multicar_overtake_20260618")
    out_dir = root / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)
    records = collect_records(root)
    current = [r for r in records if r["family"] == "当前算法"]
    dlc = [r for r in records if r["family"] == "DLC world model"]
    family_rows = family_summary(records)
    write_source_csv(records, family_rows, out_dir / "figure_compare_current_vs_dlc_world_source.csv")
    plot_figure(root, records, family_rows, out_dir)
    current_record = next(r for r in current if r["seed"] == 3)
    dlc_record = next(r for r in dlc if r["variant"] == "joint_transition_observer")
    plot_online_timeline(root, current_record, dlc_record, out_dir)
    # pick the clearest success-vs-failure pair for the GIF
    gif_summary = render_synced_online_gif(
        current_record,
        dlc_record,
        root / "evaluations" / "compare_current_vs_dlc_world" / "current_vs_dlc_world.gif",
        "当前算法 seed3",
        "DLC world model seed3",
    )
    (root / "evaluations" / "compare_current_vs_dlc_world" / "current_vs_dlc_world.json").write_text(
        json.dumps(gif_summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(
        {
            "figure": str(out_dir / "figure_compare_current_vs_dlc_world.svg"),
            "gif": gif_summary["out"],
            "source_csv": str(out_dir / "figure_compare_current_vs_dlc_world_source.csv"),
        },
        ensure_ascii=False,
        indent=2,
    ))


if __name__ == "__main__":
    main()
