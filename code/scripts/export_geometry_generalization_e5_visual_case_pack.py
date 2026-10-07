#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Regenerate E5 first-person visual cases for the geometry-generalization study."""

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageSequence

try:
    from tits_figure_style import VEHICLE_COLORS_RGB, label_for_algorithm
except ImportError:
    from scripts.tits_figure_style import VEHICLE_COLORS_RGB, label_for_algorithm


PROPOSED = "v6_runtime_dynamic_neighborhood_safe"


def read_csv(path):
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path, rows, fields):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return str(path)


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return str(path)


def algorithm_from_summary(path, num_agents, seed):
    if not path:
        return None
    name = Path(path).name
    suffix = f"_n{int(float(num_agents))}_seed{int(float(seed))}.summary.json"
    if name.endswith(suffix):
        return name[: -len(suffix)]
    return name.replace(".summary.json", "")


def unique(items):
    out = []
    for item in items:
        if item and item not in out:
            out.append(item)
    return out


def run_case(case, args):
    case_id = case["case_id"]
    num_agents = int(float(case["num_agents"]))
    seed = int(float(case["seed"]))
    algorithms = unique(
        [
            algorithm_from_summary(case.get("baseline_summary", ""), num_agents, seed),
            algorithm_from_summary(case.get("primary_summary", ""), num_agents, seed),
        ]
    )
    if not algorithms:
        algorithms = [PROPOSED]
    out_dir = Path(args.out_dir) / "e5_visual_cases" / case_id
    expected = [out_dir / "summaries" / f"{algo}_n{num_agents}_seed{seed}.summary.json" for algo in algorithms]
    if (not args.force) and all(path.exists() for path in expected):
        return {
            "case_id": case_id,
            "out_dir": str(out_dir),
            "algorithms": algorithms,
            "status": "skipped_existing",
            "command": "",
        }

    cmd = [
        sys.executable,
        "scripts/run_tits_dynamic_graph_evaluation.py",
        "--config",
        args.config,
        "--out-dir",
        str(out_dir),
        "--algorithms",
        ",".join(algorithms),
        "--num-agents",
        str(num_agents),
        "--seed",
        str(seed),
        "--max-steps",
        str(args.max_steps),
        "--finish-mode",
        args.finish_mode,
        "--observation-type",
        "telemetry_dynamic",
        "--traffic-profile",
        args.traffic_profile,
        "--device",
        args.device,
        "--first-person-gif",
        "--frame-every",
        str(args.frame_every),
        "--fps",
        str(args.fps),
        "--width",
        str(args.width),
        "--height",
        str(args.height),
    ]
    track_path = case.get("track_path", "")
    if track_path and track_path != "procedural":
        cmd.extend(["--track-path", track_path])

    log_dir = Path(args.out_dir) / "e5_visual_cases" / "_logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{case_id}.log"
    with log_path.open("w", encoding="utf-8") as log:
        result = subprocess.run(cmd, cwd=Path.cwd(), stdout=log, stderr=subprocess.STDOUT, text=True)
    return {
        "case_id": case_id,
        "out_dir": str(out_dir),
        "algorithms": algorithms,
        "status": "pass" if result.returncode == 0 else "fail",
        "returncode": result.returncode,
        "command": " ".join(cmd),
        "log": str(log_path),
    }


def load_frames(path):
    with Image.open(path) as image:
        return [frame.convert("RGB") for frame in ImageSequence.Iterator(image)]


def estimated_frame_every(summary, frame_count):
    finish_step = int(float(summary.get("finish_step") or summary.get("steps_run") or 0))
    if frame_count <= 1 or finish_step <= 0:
        return 1
    return max(1, int(round(finish_step / float(frame_count - 1))))


def frame_at_step(frames, step, frame_every):
    index = int(round(max(0, int(step)) / max(1, int(frame_every))))
    index = min(max(index, 0), len(frames) - 1)
    return index, frames[index].copy()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def trace_row_at(trace, step):
    if not trace:
        return {}
    idx = min(max(int(step) - 1, 0), len(trace) - 1)
    return trace[idx]


def risk_score(row, target):
    telemetry = row.get("telemetry", {})
    grass = 1.0 if bool((telemetry.get("on_grass") or [False])[target]) else 0.0
    lateral = abs(float((telemetry.get("lateral_error") or [0.0])[target]))
    heading = float((telemetry.get("heading_cos") or [1.0])[target])
    debug = row.get("target_policy_debug") or {}
    context = debug.get("geometry_context") or {}
    curvature = float(context.get("curvature") or 0.0)
    hard = 1.0 if debug.get("hard_recovery") else 0.0
    return 3.0 * hard + 2.0 * grass + lateral + max(0.0, 0.85 - heading) + 3.0 * curvature


def key_steps(case_id, summary, trace):
    finish = int(float(summary.get("finish_step") or summary.get("steps_run") or 0))
    events = summary.get("overtake_events") or []
    if case_id == "safety_intervention_replay" and trace:
        target = int(summary.get("target_agent", summary.get("num_agents", 1) - 1))
        best = max(trace, key=lambda row: risk_score(row, target))
        step = int(best.get("step", max(finish // 2, 0)))
        return [("start", 0), ("safety_pressure", step), ("finish", finish)]
    if case_id == "dynamic_neighborhood_replay" and trace:
        target = int(summary.get("target_agent", summary.get("num_agents", 1) - 1))
        best = max(
            trace,
            key=lambda row: len((row.get("dynamic_neighbor_ids") or [[]])[target])
            if row.get("dynamic_neighbor_ids")
            else 0,
        )
        step = int(best.get("step", max(finish // 2, 0)))
        return [("start", 0), ("neighborhood", step), ("finish", finish)]
    if events:
        first = min(events, key=lambda item: int(item.get("complete_step", 10**9)))
        start = int(first.get("start_step") or summary.get("overtake_start_step") or 0)
        complete = int(first.get("complete_step") or summary.get("time_to_first_overtake") or start)
        mid = int(round((start + complete) / 2.0))
        return [("start", 0), ("overtake_start", start), ("overtake_mid", mid), ("overtake_complete", complete)]
    return [("start", 0), ("mid_episode", finish // 2 if finish > 0 else 0), ("finish", finish)]


def safe_get_list(row, name, target, default=None):
    telemetry = row.get("telemetry", {})
    values = telemetry.get(name) or []
    if target < len(values):
        return values[target]
    return default


def debug_terms(row):
    debug = row.get("target_policy_debug") or {}
    context = debug.get("geometry_context") or {}
    action = debug.get("selected_action") or []
    return {
        "hard_recovery": bool(debug.get("hard_recovery", False)),
        "candidate_count": debug.get("candidate_count", ""),
        "best_score": debug.get("best_score", ""),
        "curvature": context.get("curvature", ""),
        "target_speed": context.get("target_speed", ""),
        "sharp_turn": context.get("sharp_turn", ""),
        "selected_action": action,
    }


def annotate(image, title, subtitle, color=(35, 90, 159)):
    font = ImageFont.load_default()
    pad = 56
    canvas = Image.new("RGB", (image.width, image.height + pad), "white")
    canvas.paste(image, (0, pad))
    draw = ImageDraw.Draw(canvas)
    draw.rectangle([0, 0, canvas.width, pad], fill="white")
    draw.rectangle([0, 0, 7, pad], fill=color)
    draw.text((14, 8), title[:150], fill=(0, 0, 0), font=font)
    draw.text((14, 31), subtitle[:180], fill=(35, 35, 35), font=font)
    return canvas


def make_contact_sheet(images, out_path, columns=3):
    if not images:
        return ""
    w = max(image.width for image in images)
    h = max(image.height for image in images)
    rows = int(np.ceil(len(images) / float(columns)))
    sheet = Image.new("RGB", (columns * w, rows * h), "white")
    for idx, image in enumerate(images):
        x = (idx % columns) * w
        y = (idx // columns) * h
        sheet.paste(image, (x, y))
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path)
    return str(out_path)


def extract_keyframes(case_rows, run_records, args):
    rows = []
    case_by_id = {row["case_id"]: row for row in case_rows}
    contact_sheets = []
    image_root = Path(args.out_dir) / "e5_keyframes" / "images"
    for record in run_records:
        case_id = record["case_id"]
        if record["status"] not in {"pass", "skipped_existing"}:
            continue
        case = case_by_id[case_id]
        contact_images = []
        for summary_path in sorted((Path(record["out_dir"]) / "summaries").glob("*.summary.json")):
            summary = read_json(summary_path)
            trace_path = Path(summary.get("trace_path") or "")
            if not trace_path.is_absolute():
                trace_path = Path.cwd() / trace_path
            trace = read_json(trace_path) if trace_path.exists() else []
            algorithm = summary.get("algorithm", summary_path.name.split("_n")[0])
            algorithm_label = label_for_algorithm(algorithm)
            target = int(summary.get("target_agent", int(summary.get("num_agents", 1)) - 1))
            color = VEHICLE_COLORS_RGB[target % len(VEHICLE_COLORS_RGB)]
            for view, field in [("first_person", "first_person_gif"), ("topdown", "topdown_gif")]:
                gif_value = summary.get(field)
                if not gif_value:
                    continue
                gif_path = Path(gif_value)
                if not gif_path.is_absolute():
                    gif_path = Path.cwd() / gif_path
                if not gif_path.exists():
                    continue
                frames = load_frames(gif_path)
                frame_every = estimated_frame_every(summary, len(frames))
                for tag, step in key_steps(case_id, summary, trace):
                    frame_index, frame = frame_at_step(frames, step, frame_every)
                    trow = trace_row_at(trace, step)
                    neighbors = []
                    if trow.get("dynamic_neighbor_ids"):
                        neighbor_lists = trow.get("dynamic_neighbor_ids") or []
                        if target < len(neighbor_lists):
                            neighbors = neighbor_lists[target]
                    terms = debug_terms(trow)
                    rank = (trow.get("rank") or [""] * (target + 1))[target] if trow else ""
                    lateral = safe_get_list(trow, "lateral_error", target, "")
                    grass = safe_get_list(trow, "on_grass", target, "")
                    title = f"{case_id} | {algorithm_label} | {view} | {tag}"
                    subtitle = (
                        f"step={int(step)}, rank={rank}, graph_neighbors={neighbors}, "
                        f"grass={grass}, lateral={lateral}, hard_recovery={terms['hard_recovery']}"
                    )
                    annotated = annotate(frame, title, subtitle, color=color)
                    out_dir = image_root / case_id / algorithm
                    out_dir.mkdir(parents=True, exist_ok=True)
                    image_path = out_dir / f"{view}_{tag}_step{int(step):04d}_frame{frame_index:04d}.png"
                    annotated.save(image_path)
                    if view == "first_person":
                        contact_images.append(annotated)
                    rows.append(
                        {
                            "case_id": case_id,
                            "claim": case.get("claim", ""),
                            "algorithm": algorithm,
                            "algorithm_label": algorithm_label,
                            "view": view,
                            "tag": tag,
                            "step": int(step),
                            "frame_index": int(frame_index),
                            "target_agent": target,
                            "included_graph_neighbors": json.dumps(neighbors),
                            "rank": rank,
                            "target_on_grass": grass,
                            "target_lateral_error": lateral,
                            "hard_recovery": terms["hard_recovery"],
                            "geometry_curvature": terms["curvature"],
                            "geometry_target_speed": terms["target_speed"],
                            "sharp_turn": terms["sharp_turn"],
                            "candidate_count": terms["candidate_count"],
                            "best_score": terms["best_score"],
                            "selected_action": json.dumps(terms["selected_action"]),
                            "source_gif": str(gif_path),
                            "source_summary": str(summary_path),
                            "source_trace": str(trace_path),
                            "image_path": str(image_path),
                        }
                    )
        sheet_path = Path(args.out_dir) / "e5_keyframes" / "contact_sheets" / f"{case_id}_first_person_sheet.png"
        sheet = make_contact_sheet(contact_images, sheet_path, columns=3)
        if sheet:
            contact_sheets.append({"case_id": case_id, "contact_sheet": sheet})
    fields = [
        "case_id",
        "claim",
        "algorithm",
        "algorithm_label",
        "view",
        "tag",
        "step",
        "frame_index",
        "target_agent",
        "included_graph_neighbors",
        "rank",
        "target_on_grass",
        "target_lateral_error",
        "hard_recovery",
        "geometry_curvature",
        "geometry_target_speed",
        "sharp_turn",
        "candidate_count",
        "best_score",
        "selected_action",
        "source_gif",
        "source_summary",
        "source_trace",
        "image_path",
    ]
    index_path = Path(args.out_dir) / "e5_keyframes" / "e5_visual_keyframe_index.csv"
    write_csv(index_path, rows, fields)
    write_csv(
        Path(args.out_dir) / "e5_keyframes" / "e5_contact_sheets.csv",
        contact_sheets,
        ["case_id", "contact_sheet"],
    )
    return str(index_path), rows, contact_sheets


def main():
    parser = argparse.ArgumentParser(description="Export E5 visual cases with first-person keyframes.")
    parser.add_argument(
        "--case-selection",
        default="outputs/tits_dynamic_graph_expanded/geometry_generalization_six_experiments/six_experiment_paper_results/tables/e5_mechanism_case_selection.csv",
    )
    parser.add_argument(
        "--config",
        default="outputs/tits_dynamic_graph_expanded/geometry_generalization_six_experiments/expanded_matrix/materials/expanded_benchmark_config.json",
    )
    parser.add_argument(
        "--out-dir",
        default="outputs/tits_dynamic_graph_expanded/geometry_generalization_six_experiments",
    )
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--max-steps", type=int, default=2200)
    parser.add_argument("--finish-mode", choices=["any", "target", "all", "env_done", "steps"], default="any")
    parser.add_argument("--traffic-profile", choices=["slow_traffic", "mixed_traffic"], default="slow_traffic")
    parser.add_argument("--frame-every", type=int, default=8)
    parser.add_argument("--fps", type=int, default=12)
    parser.add_argument("--width", type=int, default=900)
    parser.add_argument("--height", type=int, default=900)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    case_rows = read_csv(args.case_selection)
    run_records = [run_case(case, args) for case in case_rows]
    index_path, keyframe_rows, contact_sheets = extract_keyframes(case_rows, run_records, args)
    manifest = {
        "status": "pass" if all(row["status"] in {"pass", "skipped_existing"} for row in run_records) else "fail",
        "case_selection": args.case_selection,
        "config": args.config,
        "out_dir": args.out_dir,
        "run_records": run_records,
        "keyframe_index": index_path,
        "keyframe_count": len(keyframe_rows),
        "contact_sheets": contact_sheets,
        "note": "First-person and top-down keyframes are regenerated from the geometry-generalization policy. Dynamic graph neighbors and safety/geometry debug fields are recorded in trace rows.",
    }
    manifest_path = write_json(Path(args.out_dir) / "e5_keyframes" / "e5_visual_case_pack_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, **manifest}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
