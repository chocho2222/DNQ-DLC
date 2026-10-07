#!/usr/bin/env python
import argparse
import csv
import json
import math
from pathlib import Path

import numpy as np


def load_csv(path):
    rows = []
    with Path(path).open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        required = {"left_border_x", "left_border_y", "right_border_x", "right_border_y", "pos_x", "pos_y"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"missing columns in {path}: {sorted(missing)}")
        for row in reader:
            rows.append(
                [
                    float(row["left_border_x"]),
                    float(row["left_border_y"]),
                    float(row["right_border_x"]),
                    float(row["right_border_y"]),
                    float(row["pos_x"]),
                    float(row["pos_y"]),
                ]
            )
    data = np.asarray(rows, dtype=np.float64)
    return data[:, 0:2], data[:, 2:4], data[:, 4:6]


def close_loop(points):
    if np.linalg.norm(points[0] - points[-1]) > 1e-6:
        return np.vstack([points, points[0]])
    return points


def cumulative_distance(points):
    points = close_loop(points)
    segment = np.linalg.norm(np.diff(points, axis=0), axis=1)
    return np.concatenate([[0.0], np.cumsum(segment)]), points


def resample_closed(points, spacing):
    dist, closed = cumulative_distance(points)
    total = float(dist[-1])
    count = max(16, int(round(total / spacing)))
    samples = np.linspace(0.0, total, count, endpoint=False)
    x = np.interp(samples, dist, closed[:, 0])
    y = np.interp(samples, dist, closed[:, 1])
    return np.column_stack([x, y])


def smooth_closed(points, window):
    if window <= 1:
        return points
    if window % 2 == 0:
        window += 1
    pad = window // 2
    extended = np.vstack([points[-pad:], points, points[:pad]])
    kernel = np.ones(window, dtype=np.float64) / window
    x = np.convolve(extended[:, 0], kernel, mode="valid")
    y = np.convolve(extended[:, 1], kernel, mode="valid")
    return np.column_stack([x, y])


def track_normals(center):
    normals = []
    n = len(center)
    for i in range(n):
        tangent = center[(i + 1) % n] - center[(i - 1) % n]
        norm = np.linalg.norm(tangent)
        if norm < 1e-9:
            tangent = np.array([1.0, 0.0])
        else:
            tangent = tangent / norm
        normals.append(np.array([-tangent[1], tangent[0]], dtype=np.float64))
    return np.asarray(normals)


def save_preview(path, center, left, right):
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7, 4.5), constrained_layout=True)
    ax.plot(center[:, 0], center[:, 1], color="#222222", lw=1.2, label="center")
    ax.plot(left[:, 0], left[:, 1], color="#C44E52", lw=0.8, label="left")
    ax.plot(right[:, 0], right[:, 1], color="#4C72B0", lw=0.8, label="right")
    ax.set_aspect("equal", adjustable="box")
    ax.set_title("Converted Monza track")
    ax.legend(frameon=False, fontsize=8)
    ax.grid(color="#D9E1E8", lw=0.5)
    fig.savefig(path, dpi=220)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description="Convert a racing-line CSV into a fixed MultiCarRacing track file.")
    parser.add_argument("--csv", default="multi_car_racing/monza.csv")
    parser.add_argument("--out", default="multi_car_racing/tracks/monza_scaled.npz")
    parser.add_argument("--target-span", type=float, default=280.0, help="Maximum centerline x/y span after scaling in simulator units.")
    parser.add_argument("--resample-spacing", type=float, default=3.5, help="Approximate spacing between generated track tiles.")
    parser.add_argument("--smooth-window", type=int, default=5)
    parser.add_argument("--road-half-width", type=float, default=40.0 / 6.0)
    parser.add_argument("--use-file-borders", action="store_true", help="Use scaled CSV borders directly instead of simulator-width borders.")
    args = parser.parse_args()

    left_raw, right_raw, center_raw = load_csv(args.csv)
    center_mean = center_raw.mean(axis=0)
    centered = center_raw - center_mean
    raw_span = centered.max(axis=0) - centered.min(axis=0)
    scale = float(args.target_span / max(raw_span))
    center = centered * scale
    center = resample_closed(center, args.resample_spacing)
    center = smooth_closed(center, args.smooth_window)
    normals = track_normals(center)
    left = center - args.road_half_width * normals
    right = center + args.road_half_width * normals

    if args.use_file_borders:
        left_centered = (left_raw - center_mean) * scale
        right_centered = (right_raw - center_mean) * scale
        left = smooth_closed(resample_closed(left_centered, args.resample_spacing), args.smooth_window)
        right = smooth_closed(resample_closed(right_centered, args.resample_spacing), args.smooth_window)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        out_path,
        center=center.astype(np.float32),
        left=left.astype(np.float32),
        right=right.astype(np.float32),
        scale=np.float32(scale),
        center_mean=center_mean.astype(np.float32),
        road_half_width=np.float32(args.road_half_width),
        use_file_borders=np.asarray(bool(args.use_file_borders)),
        source=str(Path(args.csv)),
    )
    preview = out_path.with_suffix(".png")
    save_preview(preview, center, left, right)
    summary = {
        "source_csv": str(Path(args.csv)),
        "track_file": str(out_path),
        "preview": str(preview),
        "raw_points": int(len(center_raw)),
        "tiles": int(len(center)),
        "scale": scale,
        "target_span": args.target_span,
        "resample_spacing": args.resample_spacing,
        "road_half_width": args.road_half_width,
        "use_file_borders": bool(args.use_file_borders),
        "scaled_center_bounds": {
            "x": [float(center[:, 0].min()), float(center[:, 0].max())],
            "y": [float(center[:, 1].min()), float(center[:, 1].max())],
        },
    }
    out_path.with_suffix(".json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
