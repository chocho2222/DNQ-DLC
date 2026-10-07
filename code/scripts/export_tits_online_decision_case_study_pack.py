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


SOURCE_CSV = "outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv"
PRIMARY = "v6_runtime_dynamic_neighborhood_safe"
BASELINE = "dlc_world_original"
QUALITY = "quality_proposal_dlc_world_v1"


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


def load_json(path):
    path = Path(path)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def as_float(value):
    if value in (None, "", "nan", "NaN", "NA"):
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(out) or math.isinf(out):
        return None
    return out


def as_int(value):
    value = as_float(value)
    return int(value) if value is not None else None


def fmt(value, digits=3):
    value = as_float(value)
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


def case_id(row):
    benchmark, num_agents, seed, track, traffic = case_key(row)
    track_label = "monza" if str(track).endswith(".npz") else str(track)
    return f"{benchmark}|n{num_agents}|seed{seed}|{track_label}|{traffic}"


def trace_path_from_summary(row):
    summary_file = Path(row.get("_summary_file", ""))
    if not summary_file.exists():
        return None
    summary = load_json(summary_file)
    if not isinstance(summary, dict):
        return None
    trace_path = summary.get("trace_path")
    if trace_path and Path(trace_path).exists():
        return Path(trace_path)
    candidate = summary_file.parent.parent / "traces" / summary_file.name.replace(".summary.json", ".trace.json")
    return candidate if candidate.exists() else None


def select_cases(rows, limit):
    primary_rows = [row for row in rows if row.get("algorithm") == PRIMARY]
    eligible = []
    for row in primary_rows:
        elegant = as_float(row.get("elegant_overtake_count")) or 0.0
        on_track = as_float(row.get("on_track_overtake_count")) or 0.0
        rank_gain = as_float(row.get("rank_gain")) or 0.0
        complete_time = as_float(row.get("overtake_start_to_complete_time"))
        grass = as_float(row.get("target_grass_rate")) or 0.0
        if elegant <= 0 or on_track <= 0:
            continue
        trace_path = trace_path_from_summary(row)
        if trace_path is None:
            continue
        score = elegant * 10.0 + on_track * 5.0 + rank_gain - grass
        if row.get("_benchmark") == "monza_external_track":
            score += 5.0
        if complete_time is not None:
            score += max(0.0, 100.0 - complete_time) / 100.0
        eligible.append((score, row))
    eligible.sort(key=lambda item: item[0], reverse=True)

    selected = []
    seen_benchmarks = set()
    for _, row in eligible:
        if row.get("_benchmark") not in seen_benchmarks:
            selected.append(row)
            seen_benchmarks.add(row.get("_benchmark"))
        if len(selected) >= limit:
            return selected
    for _, row in eligible:
        if row not in selected:
            selected.append(row)
        if len(selected) >= limit:
            break
    return selected


def target_index(summary):
    target = summary.get("target_agent")
    if target is not None:
        return int(target)
    num_agents = int(summary.get("num_agents", 1))
    return max(0, num_agents - 1)


def safe_seq_get(seq, idx):
    if not isinstance(seq, list) or idx is None or idx < 0 or idx >= len(seq):
        return None
    return seq[idx]


def summarize_trace_window(trace, summary, start, complete, pad=20):
    target = target_index(summary)
    begin = max(1, int(start) - pad)
    end = min(len(trace), int(complete) + pad)
    records = []
    for item in trace:
        step = as_int(item.get("step"))
        if step is None or step < begin or step > end:
            continue
        telemetry = item.get("telemetry", {})
        lateral = safe_seq_get(telemetry.get("lateral_error"), target)
        progress = safe_seq_get(telemetry.get("progress"), target)
        on_grass = safe_seq_get(telemetry.get("on_grass"), target)
        speed = safe_seq_get(item.get("speed"), target)
        rank = safe_seq_get(item.get("rank"), target)
        track_index = safe_seq_get(item.get("track_index"), target)
        action = safe_seq_get(item.get("action"), target)
        steer = safe_seq_get(action, 0) if isinstance(action, list) else None
        throttle = safe_seq_get(action, 1) if isinstance(action, list) else None
        brake = safe_seq_get(action, 2) if isinstance(action, list) else None
        records.append(
            {
                "step": step,
                "phase": "pre_overtake" if step < start else "overtake_window" if step <= complete else "post_overtake",
                "target_rank": rank,
                "target_track_index": track_index,
                "target_progress": progress,
                "target_speed": speed,
                "target_lateral_error": lateral,
                "target_on_grass": bool(on_grass) if on_grass is not None else "",
                "target_abs_lateral_error": abs(lateral) if lateral is not None else "",
                "steer": steer,
                "throttle": throttle,
                "brake": brake,
                "compute_latency_ms": item.get("compute_latency_ms", ""),
                "min_pair_distance": item.get("min_pair_distance", ""),
            }
        )
    return records


def aggregate_window(records):
    if not records:
        return {}
    window = [row for row in records if row["phase"] == "overtake_window"]
    if not window:
        window = records
    values = {
        "window_rows": len(window),
        "mean_speed": mean(row["target_speed"] for row in window),
        "mean_abs_lateral_error": mean(row["target_abs_lateral_error"] for row in window),
        "max_abs_lateral_error": max_float(row["target_abs_lateral_error"] for row in window),
        "grass_rate": mean(1.0 if row["target_on_grass"] is True else 0.0 for row in window),
        "mean_compute_latency_ms": mean(row["compute_latency_ms"] for row in window),
        "min_pair_distance_min": min_float(row["min_pair_distance"] for row in window),
        "rank_before": next((row["target_rank"] for row in records if row["phase"] == "pre_overtake"), ""),
        "rank_after": next((row["target_rank"] for row in reversed(records) if row["phase"] == "post_overtake"), ""),
    }
    return values


def mean(values):
    vals = [as_float(v) for v in values]
    vals = [v for v in vals if v is not None]
    return float(np.mean(vals)) if vals else ""


def min_float(values):
    vals = [as_float(v) for v in values]
    vals = [v for v in vals if v is not None]
    return min(vals) if vals else ""


def max_float(values):
    vals = [as_float(v) for v in values]
    vals = [v for v in vals if v is not None]
    return max(vals) if vals else ""


def build_case_studies(rows, limit):
    by_case_alg = {}
    for row in rows:
        by_case_alg[(case_key(row), row["algorithm"])] = row

    studies = []
    timeline_rows = []
    event_rows = []
    selected = select_cases(rows, limit)
    for idx, row in enumerate(selected, start=1):
        summary_path = Path(row["_summary_file"])
        summary = load_json(summary_path)
        trace_path = trace_path_from_summary(row)
        trace = load_json(trace_path) if trace_path else []
        events = summary.get("overtake_events", []) if isinstance(summary, dict) else []
        elegant_events = [event for event in events if event.get("elegant_overtake")]
        event = elegant_events[0] if elegant_events else events[0]
        start = int(event.get("start_step", summary.get("overtake_start_step", 0)))
        complete = int(event.get("complete_step", row.get("time_to_first_overtake") or start))
        window = summarize_trace_window(trace, summary, start, complete)
        window_summary = aggregate_window(window)
        case = case_key(row)
        baseline_row = by_case_alg.get((case, BASELINE), {})
        quality_row = by_case_alg.get((case, QUALITY), {})
        study_id = f"CS{idx}"
        study = {
            "study_id": study_id,
            "case_id": case_id(row),
            "benchmark": row["_benchmark"],
            "num_agents": row["num_agents"],
            "seed": row["seed"],
            "track_path": row["track_path"],
            "traffic_profile": row["traffic_profile"],
            "algorithm": PRIMARY,
            "summary_file": row["_summary_file"],
            "trace_file": str(trace_path) if trace_path else "",
            "event_opponent": event.get("opponent", ""),
            "overtake_start_step": start,
            "overtake_complete_step": complete,
            "duration_steps": event.get("duration_steps", complete - start),
            "event_on_track": event.get("on_track_overtake", ""),
            "event_elegant": event.get("elegant_overtake", ""),
            "event_window_grass_rate": event.get("window_grass_rate", ""),
            "event_window_max_abs_lateral": event.get("window_max_abs_lateral", ""),
            "event_window_heading_error_mean_rad": event.get("window_heading_error_mean_rad", ""),
            "event_contact_proxy": event.get("window_contact_proxy", ""),
            "primary_rank_gain": row.get("rank_gain", ""),
            "primary_elegant_count": row.get("elegant_overtake_count", ""),
            "primary_target_grass_rate": row.get("target_grass_rate", ""),
            "dlc_rank_gain": baseline_row.get("rank_gain", ""),
            "dlc_elegant_count": baseline_row.get("elegant_overtake_count", ""),
            "dlc_target_grass_rate": baseline_row.get("target_grass_rate", ""),
            "quality_rank_gain": quality_row.get("rank_gain", ""),
            "quality_elegant_count": quality_row.get("elegant_overtake_count", ""),
            "quality_target_grass_rate": quality_row.get("target_grass_rate", ""),
            **{f"trace_{key}": value for key, value in window_summary.items()},
        }
        studies.append(study)
        for event_index, item in enumerate(events, start=1):
            event_rows.append(
                {
                    "study_id": study_id,
                    "event_index": event_index,
                    "opponent": item.get("opponent", ""),
                    "start_step": item.get("start_step", ""),
                    "complete_step": item.get("complete_step", ""),
                    "duration_steps": item.get("duration_steps", ""),
                    "window_grass_rate": item.get("window_grass_rate", ""),
                    "window_max_abs_lateral": item.get("window_max_abs_lateral", ""),
                    "on_track_overtake": item.get("on_track_overtake", ""),
                    "elegant_overtake": item.get("elegant_overtake", ""),
                }
            )
        for item in window:
            timeline_rows.append({"study_id": study_id, **item})
    return studies, event_rows, timeline_rows


def register_cjk_font():
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


def make_figure(studies, timeline_rows, out_dir):
    register_cjk_font()
    mpl.rcParams.update({"svg.fonttype": "none", "pdf.fonttype": 42, "font.size": 8})
    fig, axes = plt.subplots(2, 2, figsize=(7.2, 5.2), constrained_layout=True)
    fig.suptitle("在线决策透明度：代表性Desirable overtaking behavior事件", fontsize=11, fontweight="bold")

    ax = axes[0, 0]
    labels = [row["study_id"] for row in studies]
    primary = [as_float(row["primary_elegant_count"]) or 0 for row in studies]
    dlc = [as_float(row["dlc_elegant_count"]) or 0 for row in studies]
    quality = [as_float(row["quality_elegant_count"]) or 0 for row in studies]
    x = np.arange(len(studies))
    width = 0.24
    ax.bar(x - width, primary, width, label="本文算法", color="#1976B9")
    ax.bar(x, dlc, width, label="原始DLC", color="#D45A48")
    ax.bar(x + width, quality, width, label="Quality-DLC", color="#55A868")
    ax.set_xticks(x, labels)
    ax.set_ylabel("Desirable overtaking behavior次数")
    ax.set_title("同 case 对比")
    ax.legend(fontsize=7)

    ax = axes[0, 1]
    durations = [as_float(row["duration_steps"]) or 0 for row in studies]
    grass = [as_float(row["event_window_grass_rate"]) or 0 for row in studies]
    ax.bar(labels, durations, color="#4C78A8")
    ax.set_ylabel("完成耗时 step")
    ax2 = ax.twinx()
    ax2.plot(labels, grass, color="#E45756", marker="o", linewidth=1.2)
    ax2.set_ylabel("窗口草地率")
    ax.set_title("从开始超车到完成")

    selected = studies[0] if studies else None
    ax = axes[1, 0]
    if selected:
        rows = [row for row in timeline_rows if row["study_id"] == selected["study_id"]]
        steps = [as_float(row["step"]) for row in rows]
        lateral = [as_float(row["target_lateral_error"]) for row in rows]
        ax.plot(steps, lateral, color="#1976B9", linewidth=1.2)
        ax.axvspan(as_float(selected["overtake_start_step"]), as_float(selected["overtake_complete_step"]), color="#F2C14E", alpha=0.25)
        ax.set_title(f"{selected['study_id']} 横向误差窗口")
    ax.set_xlabel("step")
    ax.set_ylabel("目标车横向误差")

    ax = axes[1, 1]
    if selected:
        rows = [row for row in timeline_rows if row["study_id"] == selected["study_id"]]
        steps = [as_float(row["step"]) for row in rows]
        speed = [as_float(row["target_speed"]) for row in rows]
        rank = [as_float(row["target_rank"]) for row in rows]
        ax.plot(steps, speed, color="#55A868", linewidth=1.2, label="速度")
        ax.set_ylabel("速度")
        ax3 = ax.twinx()
        ax3.step(steps, rank, where="post", color="#7A5195", linewidth=1.0, label="名次")
        ax3.set_ylabel("目标车名次")
        ax.axvspan(as_float(selected["overtake_start_step"]), as_float(selected["overtake_complete_step"]), color="#F2C14E", alpha=0.25)
        ax.set_title(f"{selected['study_id']} 速度/名次变化")
    ax.set_xlabel("step")

    paths = {}
    for suffix in ["svg", "pdf", "png", "tiff"]:
        path = Path(out_dir) / "figures" / f"figure_online_decision_case_study_cn.{suffix}"
        path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, dpi=300 if suffix in {"png", "tiff"} else None)
        paths[suffix] = str(path)
    plt.close(fig)
    return paths


def build_markdown(summary, studies):
    lines = [
        "# Online Decision Case-Study Pack",
        "",
        "该包从正式 240-run 在线评估中抽取代表性Desirable overtaking behavior事件，用于解释本文优化后的 DLC world model 在运行时如何完成“开始超车-完成超车”的闭环。它是决策透明度与审稿解释材料，不替代确认性统计表。",
        "",
        "## Summary",
        "",
    ]
    for key, value in summary.items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Case Studies",
            "",
            "| ID | Benchmark | n | Seed | Opponent | Start | Complete | Duration | Event grass | Event lateral max | Primary/DLC/Quality elegant |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
        ]
    )
    for row in studies:
        lines.append(
            f"| {row['study_id']} | {row['benchmark']} | {row['num_agents']} | {row['seed']} | {row['event_opponent']} | {row['overtake_start_step']} | {row['overtake_complete_step']} | {row['duration_steps']} | {fmt(row['event_window_grass_rate'])} | {fmt(row['event_window_max_abs_lateral'])} | {row['primary_elegant_count']}/{row['dlc_elegant_count']}/{row['quality_elegant_count']} |"
        )
    lines.extend(
        [
            "",
            "## How To Use In A Paper",
            "",
            "- Methods 中可引用该包说明：运行时邻域、候选规划与安全评分最终体现在事件窗口内的横向误差、草地率、速度和名次变化。",
            "- Results/Discussion 中可引用它作为代表性案例，解释为什么仅报告均值不足以说明超车质量。",
            "- 不应把这些代表性 case 当作总体胜率；总体 claim 仍需引用 240-run source data、bootstrap CI、配对检验和事件一致性审计。",
            "",
            "## Key Files",
            "",
            "- Case-study table: `outputs/tits_dynamic_graph/tits_online_decision_case_study_pack/tables/online_decision_case_studies.csv`",
            "- Event table: `outputs/tits_dynamic_graph/tits_online_decision_case_study_pack/tables/online_decision_overtake_events.csv`",
            "- Timeline windows: `outputs/tits_dynamic_graph/tits_online_decision_case_study_pack/tables/online_decision_trace_windows.csv`",
            "- Chinese figure: `outputs/tits_dynamic_graph/tits_online_decision_case_study_pack/figures/figure_online_decision_case_study_cn.svg`",
            "",
            "## Regeneration Command",
            "",
            "```bash",
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_online_decision_case_study_pack.py --out-dir outputs/tits_dynamic_graph/tits_online_decision_case_study_pack",
            "```",
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Export online decision case studies from formal T-ITS traces.")
    parser.add_argument("--source-csv", default=SOURCE_CSV)
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/tits_online_decision_case_study_pack")
    parser.add_argument("--case-limit", type=int, default=4)
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    rows = read_csv(args.source_csv)
    studies, event_rows, timeline_rows = build_case_studies(rows, args.case_limit)
    figure_paths = make_figure(studies, timeline_rows, out_dir)

    summary = {
        "status": "pass" if studies else "review_required",
        "source_csv": args.source_csv,
        "source_rows": len(rows),
        "study_count": len(studies),
        "event_rows": len(event_rows),
        "timeline_rows": len(timeline_rows),
        "primary_algorithm": PRIMARY,
        "baseline_algorithm": BASELINE,
        "case_selection": "highest desirable/on-track primary cases with benchmark diversity",
        "boundary": "Representative online decision evidence only; formal performance claims remain tied to 240-run source data.",
    }
    paths = {
        "report_md": write_text(out_dir / "materials" / "ONLINE_DECISION_CASE_STUDY_PACK.md", build_markdown(summary, studies)),
        "report_json": write_json(out_dir / "materials" / "ONLINE_DECISION_CASE_STUDY_PACK.json", {"summary": summary, "studies": studies}),
        "case_studies_csv": write_csv(
            out_dir / "tables" / "online_decision_case_studies.csv",
            studies,
            list(studies[0].keys()) if studies else ["study_id"],
        ),
        "events_csv": write_csv(
            out_dir / "tables" / "online_decision_overtake_events.csv",
            event_rows,
            list(event_rows[0].keys()) if event_rows else ["study_id"],
        ),
        "trace_windows_csv": write_csv(
            out_dir / "tables" / "online_decision_trace_windows.csv",
            timeline_rows,
            list(timeline_rows[0].keys()) if timeline_rows else ["study_id"],
        ),
        "figure_svg": figure_paths["svg"],
        "figure_pdf": figure_paths["pdf"],
        "figure_png": figure_paths["png"],
        "figure_tiff": figure_paths["tiff"],
    }
    manifest = {"status": summary["status"], "out_dir": args.out_dir, "summary": summary, "paths": paths}
    manifest_path = write_json(out_dir / "tits_online_decision_case_study_pack_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, "status": summary["status"], "summary": summary}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
