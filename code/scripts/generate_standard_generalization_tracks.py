#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Generate standard closed tracks for environment-generalization experiments."""

import argparse
import json
import math
from pathlib import Path

import numpy as np


def track_normals(center):
    normals = []
    n = len(center)
    for i in range(n):
        tangent = center[(i + 1) % n] - center[(i - 1) % n]
        norm = float(np.linalg.norm(tangent))
        if norm < 1e-9:
            tangent = np.array([1.0, 0.0])
        else:
            tangent = tangent / norm
        normals.append(np.array([-tangent[1], tangent[0]], dtype=np.float64))
    return np.asarray(normals)


def resample_closed(points, count):
    points = np.asarray(points, dtype=np.float64)
    if np.linalg.norm(points[0] - points[-1]) > 1e-6:
        closed = np.vstack([points, points[0]])
    else:
        closed = points
    seg = np.linalg.norm(np.diff(closed, axis=0), axis=1)
    dist = np.concatenate([[0.0], np.cumsum(seg)])
    total = float(dist[-1])
    samples = np.linspace(0.0, total, int(count), endpoint=False)
    x = np.interp(samples, dist, closed[:, 0])
    y = np.interp(samples, dist, closed[:, 1])
    return np.column_stack([x, y])


def smooth_closed(points, window=5):
    points = np.asarray(points, dtype=np.float64)
    if window <= 1:
        return points
    if window % 2 == 0:
        window += 1
    pad = window // 2
    ext = np.vstack([points[-pad:], points, points[:pad]])
    kernel = np.ones(window, dtype=np.float64) / float(window)
    return np.column_stack(
        [
            np.convolve(ext[:, 0], kernel, mode="valid"),
            np.convolve(ext[:, 1], kernel, mode="valid"),
        ]
    )


def oval(count):
    t = np.linspace(0.0, 2.0 * math.pi, count, endpoint=False)
    return np.column_stack([125.0 * np.cos(t), 64.0 * np.sin(t)])


def s_curve(count):
    t = np.linspace(0.0, 2.0 * math.pi, count, endpoint=False)
    radius = 92.0 + 20.0 * np.sin(2.0 * t)
    x = radius * np.cos(t) + 22.0 * np.sin(3.0 * t)
    y = 0.72 * radius * np.sin(t) + 32.0 * np.sin(2.0 * t)
    return np.column_stack([x, y])


def hairpin(count):
    # A closed loop with one tight bulb and one long return arc.
    t = np.linspace(0.0, 2.0 * math.pi, count, endpoint=False)
    x = 112.0 * np.cos(t) + 25.0 * np.cos(2.0 * t) - 18.0 * np.sin(3.0 * t)
    y = 58.0 * np.sin(t) - 48.0 * np.sin(2.0 * t)
    pinch = np.exp(-((t - math.pi) ** 2) / 0.18)
    x -= 42.0 * pinch
    y += 18.0 * pinch * np.sin(6.0 * t)
    return np.column_stack([x, y])


def save_preview(path, center, left, right, title):
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(5.2, 3.5), constrained_layout=True)
    ax.fill(
        np.r_[left[:, 0], right[::-1, 0]],
        np.r_[left[:, 1], right[::-1, 1]],
        color="#D1D5DB",
        alpha=0.65,
        linewidth=0,
    )
    ax.plot(center[:, 0], center[:, 1], color="#111827", lw=1.1)
    ax.plot(left[:, 0], left[:, 1], color="#6B7280", lw=0.7)
    ax.plot(right[:, 0], right[:, 1], color="#6B7280", lw=0.7)
    ax.set_aspect("equal", adjustable="box")
    ax.set_title(title)
    ax.axis("off")
    fig.savefig(path, dpi=260)
    plt.close(fig)


def save_track(name, center, out_dir, road_half_width):
    center = smooth_closed(resample_closed(center, len(center)), window=5)
    normals = track_normals(center)
    left = center - road_half_width * normals
    right = center + road_half_width * normals
    out_path = Path(out_dir) / f"{name}_scaled.npz"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        out_path,
        center=center.astype(np.float32),
        left=left.astype(np.float32),
        right=right.astype(np.float32),
        scale=np.float32(1.0),
        center_mean=np.zeros(2, dtype=np.float32),
        road_half_width=np.float32(road_half_width),
        use_file_borders=np.asarray(False),
        source=f"procedural_standard:{name}",
    )
    preview = out_path.with_suffix(".png")
    save_preview(preview, center, left, right, name.replace("_", " ").title())
    meta = {
        "track_file": str(out_path),
        "preview": str(preview),
        "track_type": name,
        "tiles": int(len(center)),
        "road_half_width": float(road_half_width),
        "source": f"procedural_standard:{name}",
        "bounds": {
            "x": [float(center[:, 0].min()), float(center[:, 0].max())],
            "y": [float(center[:, 1].min()), float(center[:, 1].max())],
        },
    }
    out_path.with_suffix(".json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return meta


def main():
    parser = argparse.ArgumentParser(description="Generate Oval/S-Curve/Hairpin standard tracks.")
    parser.add_argument("--out-dir", default="tracks")
    parser.add_argument("--tiles", type=int, default=240)
    parser.add_argument("--road-half-width", type=float, default=40.0 / 6.0)
    args = parser.parse_args()
    specs = {
        "oval": oval(args.tiles),
        "s_curve": s_curve(args.tiles),
        "hairpin": hairpin(args.tiles),
    }
    manifest = {
        "out_dir": args.out_dir,
        "tracks": [save_track(name, center, args.out_dir, args.road_half_width) for name, center in specs.items()],
    }
    manifest_path = Path(args.out_dir) / "standard_generalization_tracks_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"manifest": str(manifest_path), **manifest}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
