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
from PIL import Image, ImageSequence, ImageDraw, ImageFont
from matplotlib import font_manager


SOURCE_CSV = "outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv"
OUT_DIR = "outputs/tits_dynamic_graph/tits_typical_first_person_case_pack"
V6_SAFE = "v6_runtime_dynamic_neighborhood_safe"
DLC = "dlc_world_original"

CASE_SPECS = [
    {
        "case_id": "case1_dlc_fail_v6safe_success",
        "claim_cn": "原始DLC失败，V6-safe完成超车",
        "benchmark": "monza_external_track",
        "num_agents": "6",
        "seed": "53",
        "run_dir": "outputs/tits_dynamic_graph/publication_gifs/monza_n6_seed53_v6safe_vs_dlc",
        "algorithms": [DLC, V6_SAFE],
        "selection": "DLC overtake_success=0, V6-safe overtake_success=1 in frozen source data.",
    },
    {
        "case_id": "case2_dlc_nonelegant_v6safe_elegant",
        "claim_cn": "原始 DLC 发生不符合 desirable overtaking behavior 标准的超车，V6-safe 达成 desirable overtaking behavior",
        "benchmark": "in_distribution_procedural",
        "num_agents": "5",
        "seed": "17",
        "run_dir": "outputs/tits_dynamic_graph/tits_typical_first_person_case_pack/rerun/procedural_n5_seed17",
        "algorithms": [DLC, V6_SAFE],
        "selection": "DLC overtake_success=1 and elegant_overtake=0; V6-safe elegant_overtake=1 in frozen source data.",
    },
    {
        "case_id": "case3_v6safe_failure_residual",
        "claim_cn": "V6-safe失败案例，展示残余问题",
        "benchmark": "in_distribution_procedural",
        "num_agents": "4",
        "seed": "17",
        "run_dir": "outputs/tits_dynamic_graph/tits_typical_first_person_case_pack/rerun/procedural_n4_seed17",
        "algorithms": [V6_SAFE],
        "selection": "V6-safe overtake_success=0 in frozen source data.",
    },
    {
        "case_id": "case4_dynamic_neighborhood_process",
        "claim_cn": "动态邻域选择过程，显示被纳入局部图的车辆",
        "benchmark": "vehicle_count_extrapolation",
        "num_agents": "8",
        "seed": "43",
        "run_dir": "outputs/tits_dynamic_graph/publication_gifs/n8_seed43_v6safe_vs_dlc",
        "algorithms": [V6_SAFE],
        "selection": "8-car extrapolation case with V6-safe dynamic-neighborhood planner and stored first-person GIF.",
    },
    {
        "case_id": "case5_safety_intervention_process",
        "claim_cn": "安全模块介入时刻，说明其如何改变执行动作",
        "benchmark": "in_distribution_procedural",
        "num_agents": "4",
        "seed": "17",
        "run_dir": "outputs/tits_dynamic_graph/tits_typical_first_person_case_pack/rerun/procedural_n4_seed17",
        "algorithms": [V6_SAFE],
        "selection": "Residual-failure case with high grass/lateral exposure, used to locate safety-pressure or hard-recovery moments.",
    },
]


def configure_chinese_matplotlib():
    font_candidates = [
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.otf"),
        Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"),
        Path("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"),
        Path("/usr/share/fonts/truetype/arphic/uming.ttc"),
    ]
    font_name = "Noto Sans CJK SC"
    font_path_used = None
    for font_path in font_candidates:
        if font_path.exists():
            font_manager.fontManager.addfont(str(font_path))
            font_name = font_manager.FontProperties(fname=str(font_path)).get_name()
            font_path_used = font_path
            break
    mpl.rcParams.update(
        {
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "font.family": "sans-serif",
            "font.sans-serif": [font_name, "Noto Sans CJK SC", "DejaVu Sans"],
            "font.size": 8,
            "axes.unicode_minus": False,
            "axes.spines.right": False,
            "axes.spines.top": False,
            "legend.frameon": False,
        }
    )
    pil_font = None
    if font_path_used is not None:
        try:
            pil_font = ImageFont.truetype(str(font_path_used), 18)
        except Exception:
            pil_font = None
    return font_name, pil_font


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


def as_float(value):
    if value in (None, "", "nan", "NaN", "NA", "--"):
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(out) or math.isinf(out):
        return None
    return out


def fmt(value, digits=3):
    value = as_float(value)
    if value is None:
        return "NA"
    return f"{value:.{digits}f}"


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def algo_stem(algorithm, num_agents, seed):
    return f"{algorithm}_n{num_agents}_seed{seed}"


def paths_for(spec, algorithm):
    root = Path(spec["run_dir"])
    stem = algo_stem(algorithm, spec["num_agents"], spec["seed"])
    return {
        "summary": root / "summaries" / f"{stem}.summary.json",
        "trace": root / "traces" / f"{stem}.trace.json",
        "first_person_gif": root / "gifs" / f"{stem}.first_person.gif",
        "topdown_gif": root / "gifs" / f"{stem}.topdown.gif",
    }


def load_gif_frames(path):
    image = Image.open(path)
    return [frame.convert("RGB") for frame in ImageSequence.Iterator(image)]


def estimate_frame_every(summary, frame_count):
    steps = int(summary.get("steps_run") or summary.get("finish_step") or 0)
    if frame_count <= 1 or steps <= 0:
        return 1
    return max(1, int(round(steps / float(frame_count - 1))))


def frame_for_step(frames, step, frame_every):
    if not frames:
        raise ValueError("empty GIF frame list")
    idx = int(round(max(0, int(step)) / max(1, int(frame_every))))
    idx = min(max(idx, 0), len(frames) - 1)
    return idx, frames[idx].copy()


def annotate_image(image, title, subtitle, pil_font=None):
    image = image.convert("RGB")
    pad = 54
    canvas = Image.new("RGB", (image.width, image.height + pad), "white")
    canvas.paste(image, (0, pad))
    draw = ImageDraw.Draw(canvas)
    font = pil_font or ImageFont.load_default()
    small = font
    draw.rectangle([0, 0, canvas.width, pad], fill=(255, 255, 255))
    draw.text((10, 7), title, fill=(20, 20, 20), font=font)
    draw.text((10, 31), subtitle, fill=(70, 70, 70), font=small)
    return canvas


def key_steps(summary, trace, mode="event"):
    events = summary.get("overtake_events") or []
    if events:
        event = min(events, key=lambda item: int(item.get("complete_step", 10**9)))
        start = int(event.get("start_step", 0))
        complete = int(event.get("complete_step", start))
        mid = int(round((start + complete) / 2))
        return [("开始", start), ("中段", mid), ("完成", complete)]
    steps_run = int(summary.get("steps_run") or len(trace) or 0)
    return [("起步", 0), ("中段", max(1, steps_run // 2)), ("末端", max(1, steps_run - 1))]


def extract_case_frames(spec, out_dir, pil_font):
    rows = []
    panel_images = []
    for algorithm in spec["algorithms"]:
        paths = paths_for(spec, algorithm)
        summary = load_json(paths["summary"])
        trace = load_json(paths["trace"])
        frames = load_gif_frames(paths["first_person_gif"])
        frame_every = estimate_frame_every(summary, len(frames))
        step_items = key_steps(summary, trace)
        alg_label = "V6-safe" if algorithm == V6_SAFE else "DLC原始"
        for label, step in step_items:
            frame_idx, image = frame_for_step(frames, step, frame_every)
            trace_idx = min(max(int(step) - 1, 0), len(trace) - 1) if trace else 0
            trow = trace[trace_idx] if trace else {}
            target = int(summary.get("target_agent", int(spec["num_agents"]) - 1))
            on_grass = ""
            lateral = ""
            heading = ""
            rank = ""
            if trow:
                telem = trow.get("telemetry", {})
                on_grass = str(bool(telem.get("on_grass", [False])[target]))
                lateral = fmt(telem.get("lateral_error", [None])[target], 3)
                heading = fmt(telem.get("heading_cos", [None])[target], 3)
                rank = str(trow.get("rank", [""])[target])
            title = f"{spec['claim_cn']} | {alg_label} | {label}"
            subtitle = f"step={step}, rank={rank}, grass={on_grass}, lateral={lateral}, heading_cos={heading}"
            annotated = annotate_image(image, title, subtitle, pil_font)
            screenshot_path = out_dir / "screenshots" / spec["case_id"] / f"{algorithm}_{label}_step{step}.png"
            screenshot_path.parent.mkdir(parents=True, exist_ok=True)
            annotated.save(screenshot_path)
            panel_images.append((alg_label, label, step, annotated))
            rows.append(
                {
                    "case_id": spec["case_id"],
                    "claim_cn": spec["claim_cn"],
                    "benchmark": spec["benchmark"],
                    "num_agents": spec["num_agents"],
                    "seed": spec["seed"],
                    "algorithm": algorithm,
                    "algorithm_label": alg_label,
                    "stage_label": label,
                    "step": step,
                    "gif_frame_index": frame_idx,
                    "estimated_frame_every": frame_every,
                    "rank": rank,
                    "target_on_grass": on_grass,
                    "target_lateral_error": lateral,
                    "target_heading_cos": heading,
                    "screenshot": str(screenshot_path),
                    "source_first_person_gif": str(paths["first_person_gif"]),
                    "source_summary": str(paths["summary"]),
                    "source_trace": str(paths["trace"]),
                }
            )
    make_contact_sheet(spec, panel_images, out_dir)
    return rows


def make_contact_sheet(spec, panel_images, out_dir):
    if not panel_images:
        return None
    thumb_w = max(img.width for _, _, _, img in panel_images)
    thumb_h = max(img.height for _, _, _, img in panel_images)
    cols = 3
    rows = int(math.ceil(len(panel_images) / cols))
    canvas = Image.new("RGB", (cols * thumb_w, rows * thumb_h), "white")
    for idx, (_, _, _, img) in enumerate(panel_images):
        x = (idx % cols) * thumb_w
        y = (idx // cols) * thumb_h
        canvas.paste(img.resize((thumb_w, thumb_h)), (x, y))
    path = out_dir / "figures" / f"figure_{spec['case_id']}_first_person_contact_sheet.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(path)
    canvas.save(path.with_suffix(".tiff"))
    return str(path)


def target_agent_from_summary(summary, spec):
    return int(summary.get("target_agent", int(spec["num_agents"]) - 1))


def interaction_neighbor_scores(trace_row, target_agent, max_neighbors=3):
    positions = np.asarray(trace_row.get("positions", []), dtype=np.float32)
    tiles = trace_row.get("tile_visited_count", [])
    ranks = trace_row.get("rank", [])
    if len(positions) == 0 or target_agent >= len(positions):
        return []
    target_pos = positions[target_agent]
    target_tile = float(tiles[target_agent]) if target_agent < len(tiles) else 0.0
    scores = []
    for agent_id, pos in enumerate(positions):
        if agent_id == target_agent:
            continue
        dist = float(np.linalg.norm(pos - target_pos))
        gap = float(tiles[agent_id]) - target_tile if agent_id < len(tiles) else 0.0
        ahead = 0.0 < gap < 35.0 and dist < 80.0
        alongside = abs(gap) <= 8.0 and dist < 32.0
        rear_pressure = -12.0 <= gap <= 0.0 and dist < 28.0
        gap_score = 1.0 / max(dist / 12.0, 1.0)
        score = 3.6 * ahead + 2.8 * alongside + 1.7 * rear_pressure + 1.1 * gap_score - 0.015 * dist
        scores.append(
            {
                "agent_id": agent_id,
                "score": float(score),
                "distance": dist,
                "tile_gap": gap,
                "rank": ranks[agent_id] if agent_id < len(ranks) else "",
                "selected": False,
            }
        )
    scores.sort(key=lambda row: row["score"], reverse=True)
    for row in scores[:max_neighbors]:
        row["selected"] = True
    return scores


def make_neighbor_figure(spec, out_dir):
    paths = paths_for(spec, V6_SAFE)
    summary = load_json(paths["summary"])
    trace = load_json(paths["trace"])
    target = target_agent_from_summary(summary, spec)
    event = (summary.get("overtake_events") or [{}])[0]
    steps = [
        int(event.get("start_step", max(1, len(trace) // 4))),
        int(round((int(event.get("start_step", 1)) + int(event.get("complete_step", max(1, len(trace) // 2)))) / 2)),
        int(event.get("complete_step", max(1, len(trace) // 2))),
    ]
    rows = []
    fig, axes = plt.subplots(1, len(steps), figsize=(10.8, 3.2), constrained_layout=True)
    fig.suptitle("动态邻域选择过程：每步只将交互优先级最高的车辆纳入局部图", fontsize=11, fontweight="bold")
    if len(steps) == 1:
        axes = [axes]
    for ax, step in zip(axes, steps):
        idx = min(max(step - 1, 0), len(trace) - 1)
        row = trace[idx]
        positions = np.asarray(row["positions"], dtype=np.float32)
        scores = interaction_neighbor_scores(row, target, max_neighbors=3)
        selected_ids = {item["agent_id"] for item in scores if item["selected"]}
        for agent_id, pos in enumerate(positions):
            if agent_id == target:
                color = "#D62728"
                size = 95
                label = "目标车"
            elif agent_id in selected_ids:
                color = "#1F77B4"
                size = 80
                label = "纳入邻域"
            else:
                color = "#B8B8B8"
                size = 45
                label = "未纳入"
            ax.scatter(pos[0], pos[1], s=size, color=color, edgecolor="black", linewidth=0.4)
            ax.text(pos[0] + 1.5, pos[1] + 1.5, str(agent_id), fontsize=8)
        ax.set_title(f"step {step}\nselected={sorted(selected_ids)}")
        ax.set_aspect("equal", adjustable="box")
        ax.set_xlabel("x")
        ax.set_ylabel("y")
        ax.grid(alpha=0.18)
        for item in scores:
            item_row = dict(item)
            item_row.update({"case_id": spec["case_id"], "step": step, "target_agent": target})
            rows.append(item_row)
    paths_out = {}
    for suffix in ["svg", "pdf", "png", "tiff"]:
        path = out_dir / "figures" / f"figure_{spec['case_id']}_dynamic_neighbor_selection.{suffix}"
        fig.savefig(path, dpi=450 if suffix in {"png", "tiff"} else None, bbox_inches="tight")
        paths_out[suffix] = str(path)
    plt.close(fig)
    return rows, paths_out


def safety_score(row, target):
    telem = row.get("telemetry", {})
    lateral = abs(float(telem.get("lateral_error", [0.0])[target]))
    heading = float(telem.get("heading_cos", [1.0])[target])
    grass = bool(telem.get("on_grass", [False])[target])
    backward = bool(telem.get("backward", [False])[target])
    speed = float(row.get("speed", [0.0])[target])
    action = row.get("action", [[0.0, 0.0, 0.0]])[target]
    throttle = float(action[1])
    brake = float(action[2])
    hard = backward or (grass and (lateral > 0.48 or heading < 0.70)) or lateral > 0.62 or heading < 0.55
    soft = grass or lateral > 0.30 or heading < 0.85 or brake > 0.20 or throttle < 0.10
    score = 3.0 * hard + 1.5 * grass + lateral + max(0.0, 0.85 - heading) + 0.4 * brake + 0.02 * speed
    return score, hard, soft


def make_safety_figure(spec, out_dir, pil_font):
    paths = paths_for(spec, V6_SAFE)
    summary = load_json(paths["summary"])
    trace = load_json(paths["trace"])
    frames = load_gif_frames(paths["first_person_gif"])
    frame_every = estimate_frame_every(summary, len(frames))
    target = target_agent_from_summary(summary, spec)
    scored = []
    for row in trace:
        score, hard, soft = safety_score(row, target)
        if hard or soft:
            scored.append((score, hard, int(row["step"]), row))
    if not scored:
        scored = [(safety_score(row, target)[0], False, int(row["step"]), row) for row in trace]
    scored.sort(key=lambda item: (item[1], item[0]), reverse=True)
    center = scored[0][2]
    steps = [max(0, center - 24), center, min(int(summary.get("steps_run", len(trace))), center + 24)]
    images = []
    rows = []
    for label, step in zip(["介入前", "介入时刻", "介入后"], steps):
        frame_idx, image = frame_for_step(frames, step, frame_every)
        idx = min(max(step - 1, 0), len(trace) - 1)
        row = trace[idx]
        telem = row.get("telemetry", {})
        action = row.get("action", [[0, 0, 0]])[target]
        score, hard, soft = safety_score(row, target)
        lateral = float(telem.get("lateral_error", [0.0])[target])
        heading = float(telem.get("heading_cos", [1.0])[target])
        grass = bool(telem.get("on_grass", [False])[target])
        subtitle = (
            f"step={step}, hard={hard}, soft={soft}, grass={grass}, "
            f"lat={lateral:.3f}, heading={heading:.3f}, action=[{action[0]:.2f},{action[1]:.2f},{action[2]:.2f}]"
        )
        annotated = annotate_image(image, f"{spec['claim_cn']} | {label}", subtitle, pil_font)
        path = out_dir / "screenshots" / spec["case_id"] / f"v6safe_{label}_step{step}.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        annotated.save(path)
        images.append(annotated)
        rows.append(
            {
                "case_id": spec["case_id"],
                "stage_label": label,
                "step": step,
                "gif_frame_index": frame_idx,
                "target_agent": target,
                "safety_score": score,
                "hard_recovery_condition": hard,
                "soft_safety_pressure": soft,
                "target_on_grass": grass,
                "target_lateral_error": lateral,
                "target_heading_cos": heading,
                "steer": float(action[0]),
                "throttle": float(action[1]),
                "brake": float(action[2]),
                "screenshot": str(path),
            }
        )
    if images:
        canvas = Image.new("RGB", (sum(img.width for img in images), max(img.height for img in images)), "white")
        x = 0
        for img in images:
            canvas.paste(img, (x, 0))
            x += img.width
        panel = out_dir / "figures" / f"figure_{spec['case_id']}_safety_intervention_first_person.png"
        panel.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(panel)
        canvas.save(panel.with_suffix(".tiff"))
    return rows


def formal_metric_rows(source_rows, spec):
    out = []
    for row in source_rows:
        if row["_benchmark"] == spec["benchmark"] and row["num_agents"] == spec["num_agents"] and row["seed"] == spec["seed"]:
            if row["algorithm"] in set(spec["algorithms"]):
                out.append(
                    {
                        "case_id": spec["case_id"],
                        "benchmark": spec["benchmark"],
                        "num_agents": spec["num_agents"],
                        "seed": spec["seed"],
                        "algorithm": row["algorithm"],
                        "overtake_success_rate": row.get("overtake_success_rate", ""),
                        "on_track_overtake_rate": row.get("on_track_overtake_rate", ""),
                        "elegant_overtake_rate": row.get("elegant_overtake_rate", ""),
                        "overtake_start_to_complete_time": row.get("overtake_start_to_complete_time", ""),
                        "overtake_window_grass_rate_mean": row.get("overtake_window_grass_rate_mean", ""),
                        "target_grass_rate": row.get("target_grass_rate", ""),
                        "target_progress": row.get("target_progress", ""),
                        "rank_gain": row.get("rank_gain", ""),
                        "summary_file": row.get("_summary_file", ""),
                    }
                )
    return out


def build_markdown(report):
    lines = [
        "# 典型 Case 第一视角截图与机制诊断包",
        "",
        "该材料包为 T-ITS 论文结果分析补充可视化证据。它不改变 frozen 240-run 主矩阵结论，而是从已冻结 source data 选择代表 case，并用第一视角截图解释算法差异、残余失败、动态邻域选择和安全模块介入。",
        "",
        "## 包含的典型过程",
        "",
    ]
    for case in report["cases"]:
        lines.append(f"- {case['case_id']}: {case['claim_cn']}。选择依据：{case['selection']}")
    lines.extend(
        [
            "",
            "## 关键输出",
            "",
            "- 第一视角截图索引：`tables/typical_first_person_screenshot_index.csv`",
            "- frozen 指标摘录：`tables/typical_case_frozen_metrics.csv`",
            "- 动态邻域选择诊断：`tables/dynamic_neighborhood_selection_replay.csv`",
            "- 安全介入诊断：`tables/safety_intervention_replay.csv`",
            "- 截图目录：`screenshots/`",
            "- 组合图目录：`figures/`",
            "",
            "## 解释边界",
            "",
            "- 第一视角 GIF 和截图用于过程说明，不替代正式统计检验。",
            "- 动态邻域选择表根据 trace 中位置、进度和交互优先级规则重建，用于解释局部图选择机制。",
            "- 安全介入表根据 V6-safe 的 hard-recovery 条件和执行动作中的 throttle/brake/steer 变化做 replay diagnostic。",
            "- 若主文引用这些图，应同时引用 frozen source data 与 case selection table，避免 cherry-picking 风险。",
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Export typical first-person case screenshots for T-ITS result analysis.")
    parser.add_argument("--source-csv", default=SOURCE_CSV)
    parser.add_argument("--out-dir", default=OUT_DIR)
    args = parser.parse_args()

    root = Path.cwd()
    out_dir = root / args.out_dir
    (out_dir / "tables").mkdir(parents=True, exist_ok=True)
    (out_dir / "figures").mkdir(parents=True, exist_ok=True)
    (out_dir / "screenshots").mkdir(parents=True, exist_ok=True)
    (out_dir / "materials").mkdir(parents=True, exist_ok=True)
    font_name, pil_font = configure_chinese_matplotlib()

    source_rows = read_csv(root / args.source_csv)
    screenshot_rows = []
    metric_rows = []
    neighbor_rows = []
    safety_rows = []
    missing = []
    for spec in CASE_SPECS:
        for algorithm in spec["algorithms"]:
            paths = paths_for(spec, algorithm)
            for key in ["summary", "trace", "first_person_gif"]:
                if not (root / paths[key]).exists() if not paths[key].is_absolute() else not paths[key].exists():
                    missing.append(str(paths[key]))
        if missing:
            continue
        screenshot_rows.extend(extract_case_frames(spec, out_dir, pil_font))
        metric_rows.extend(formal_metric_rows(source_rows, spec))
        if spec["case_id"] == "case4_dynamic_neighborhood_process":
            rows, _ = make_neighbor_figure(spec, out_dir)
            neighbor_rows.extend(rows)
        if spec["case_id"] == "case5_safety_intervention_process":
            safety_rows.extend(make_safety_figure(spec, out_dir, pil_font))

    status = "pass" if not missing and len(screenshot_rows) >= 21 and len(metric_rows) >= 7 else "review_required"
    paths = {
        "screenshot_index": write_csv(
            out_dir / "tables" / "typical_first_person_screenshot_index.csv",
            screenshot_rows,
            [
                "case_id", "claim_cn", "benchmark", "num_agents", "seed", "algorithm", "algorithm_label", "stage_label",
                "step", "gif_frame_index", "estimated_frame_every", "rank", "target_on_grass", "target_lateral_error",
                "target_heading_cos", "screenshot", "source_first_person_gif", "source_summary", "source_trace",
            ],
        ),
        "frozen_metrics": write_csv(
            out_dir / "tables" / "typical_case_frozen_metrics.csv",
            metric_rows,
            [
                "case_id", "benchmark", "num_agents", "seed", "algorithm", "overtake_success_rate", "on_track_overtake_rate",
                "elegant_overtake_rate", "overtake_start_to_complete_time", "overtake_window_grass_rate_mean",
                "target_grass_rate", "target_progress", "rank_gain", "summary_file",
            ],
        ),
        "dynamic_neighborhood": write_csv(
            out_dir / "tables" / "dynamic_neighborhood_selection_replay.csv",
            neighbor_rows,
            ["case_id", "step", "target_agent", "agent_id", "score", "distance", "tile_gap", "rank", "selected"],
        ),
        "safety_intervention": write_csv(
            out_dir / "tables" / "safety_intervention_replay.csv",
            safety_rows,
            [
                "case_id", "stage_label", "step", "gif_frame_index", "target_agent", "safety_score",
                "hard_recovery_condition", "soft_safety_pressure", "target_on_grass", "target_lateral_error",
                "target_heading_cos", "steer", "throttle", "brake", "screenshot",
            ],
        ),
    }
    report = {
        "status": status,
        "font": font_name,
        "source_csv": args.source_csv,
        "cases": CASE_SPECS,
        "summary": {
            "case_count": len(CASE_SPECS),
            "screenshot_rows": len(screenshot_rows),
            "frozen_metric_rows": len(metric_rows),
            "dynamic_neighbor_rows": len(neighbor_rows),
            "safety_rows": len(safety_rows),
            "missing_files": missing,
        },
        "paths": paths,
        "claim_boundary": "qualitative process evidence; formal performance claims remain tied to the frozen 240-run source data.",
    }
    paths["report_json"] = write_json(out_dir / "materials" / "TYPICAL_FIRST_PERSON_CASE_PACK_REPORT.json", report)
    paths["report_md"] = write_text(out_dir / "materials" / "TYPICAL_FIRST_PERSON_CASE_PACK_REPORT.md", build_markdown(report))
    manifest = {
        "status": status,
        "out_dir": args.out_dir,
        "summary": report["summary"],
        "paths": paths,
        "claim_boundary": report["claim_boundary"],
    }
    manifest_path = write_json(out_dir / "tits_typical_first_person_case_pack_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, "status": status, "summary": report["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
