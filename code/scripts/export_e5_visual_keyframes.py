#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Extract first-person and top-down keyframes from E5 visual-case GIFs."""

import argparse
import csv
import json
from pathlib import Path

from PIL import Image, ImageSequence

try:
    from tits_figure_style import label_for_algorithm
except ImportError:
    from scripts.tits_figure_style import label_for_algorithm


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
    return index, frames[index]


def key_steps(summary):
    finish = int(float(summary.get("finish_step") or summary.get("steps_run") or 0))
    events = summary.get("overtake_events") or []
    if events:
        first = events[0]
        start = int(first.get("start_step") or summary.get("overtake_start_step") or 0)
        complete = int(first.get("complete_step") or summary.get("time_to_first_overtake") or start)
        return [
            ("start", 0),
            ("overtake_start", start),
            ("overtake_complete", complete),
            ("finish", finish),
        ]
    mid = finish // 2 if finish > 0 else 0
    return [
        ("start", 0),
        ("mid_episode", mid),
        ("finish", finish),
    ]


def extract_keyframes(root, out_dir):
    root = Path(root)
    out_dir = Path(out_dir)
    image_dir = out_dir / "images"
    image_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for summary_path in sorted(root.glob("*/summaries/*.summary.json")):
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        case_id = summary_path.parents[1].name
        algorithm = summary.get("algorithm", summary_path.stem.replace(".summary", ""))
        algorithm_label = label_for_algorithm(algorithm)
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
            for tag, step in key_steps(summary):
                frame_index, frame = frame_at_step(frames, step, frame_every)
                subdir = image_dir / case_id / algorithm
                subdir.mkdir(parents=True, exist_ok=True)
                image_path = subdir / f"{view}_{tag}_step{int(step):04d}_frame{frame_index:04d}.png"
                frame.save(image_path)
                rows.append(
                    {
                        "case_id": case_id,
                        "algorithm": algorithm,
                        "algorithm_label": algorithm_label,
                        "view": view,
                        "tag": tag,
                        "step": int(step),
                        "frame_index": int(frame_index),
                        "frame_every_estimate": int(frame_every),
                        "source_gif": str(gif_path),
                        "image_path": str(image_path),
                    }
                )
    fields = [
        "case_id",
        "algorithm",
        "algorithm_label",
        "view",
        "tag",
        "step",
        "frame_index",
        "frame_every_estimate",
        "source_gif",
        "image_path",
    ]
    index_path = out_dir / "e5_visual_keyframe_index.csv"
    with index_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    manifest = {
        "source_root": str(root),
        "out_dir": str(out_dir),
        "keyframe_count": len(rows),
        "index_csv": str(index_path),
        "note": "Frame indices are reconstructed from GIF length and finish_step; step values remain the primary semantic anchors.",
    }
    manifest_path = out_dir / "e5_visual_keyframe_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main():
    parser = argparse.ArgumentParser(description="Extract E5 first-person/top-down keyframes.")
    parser.add_argument("--root", default="outputs/tits_dynamic_graph_expanded/six_experiment_paper_results/e5_visual_cases")
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph_expanded/six_experiment_paper_results/e5_keyframes")
    args = parser.parse_args()
    manifest = extract_keyframes(args.root, args.out_dir)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
