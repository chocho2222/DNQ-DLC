#!/usr/bin/env python
"""Render a top-down snapshot panel directly from a recorded evaluation run.

The manuscript needs one qualitative panel per controller, and the panel has to
be reproducible from the released artifacts rather than from a screenshot taken
during development. A recorded run carries everything the panel needs: the
initial file holds the track and the scene parameters, the trace holds the
position of every car at every step, and the environment rebuilds the road
polygons from the same seed and the same scene arguments. Rebuilding the
environment is cheap (no policy rollout) and is checked against the recorded
initial poses before anything is drawn, so a panel that renders is a panel whose
geometry matches the trace it came from.

Per panel the script draws the road polygons, the path each car has followed up
to the chosen step, every car as a top-down icon in its recorded hull pose, and
the per-car labels. The icon is the outline of the simulated vehicle itself: the
footprint is the union of the four Box2D hull fixtures of
``gym.envs.box2d.car_dynamics`` (5.0 m long, 2.4 m wide, wheels out to 2.8 m) and
it is rotated by the hull angle the trace records, so a reader sees the car the
controller actually drove rather than a point. The evaluated car is drawn in its
controller colour, which is the same colour the figures and the recorded colour
assignment use, so the panel and the quantitative figures agree. All panels share
the same world window size, so two panels can be compared without a scale change.

Usage:
    python3 scripts/build_qualitative_snapshot.py \
        --root outputs/.../main_final_20260922 \
        --case-dir M8_scale_n8_seed23 --num-agents 8 --seed 23 \
        --panel ours_dnq_dlc:DNQ-DLC:auto --panel rule_expert_gate:Rule expert:auto \
        --out figures/figure_snapshot_sample
"""

import argparse
import csv
import json
import math
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dlc.rollout import make_env  # noqa: E402
from scripts.tits_figure_style import color_for_algorithm  # noqa: E402

BACKGROUND = (36, 113, 61)
NEUTRAL = (156, 163, 175)
LABEL_COLOUR = (255, 255, 255)
TRACK_WIDTH = 6.666666666666667

# Cars the neighbourhood selector admitted at the rendered step are lightened and
# outlined; the white outline is the same neutral stroke every car already carries,
# only thicker, so the highlight reads as "this car was selected" rather than as a
# second algorithm colour.
ADMITTED_OUTLINE = (255, 255, 255)
ADMITTED_OUTLINE_WIDTH = 3
ADMITTED_TINT = 0.45

# Font used for every annotation drawn into the raster. The panel is placed at
# one column width (about 3.4 in) in the manuscript, so a panel of this pixel
# width needs roughly 34 px of type to land near 7 pt on the page; the earlier
# build used the Pillow bitmap default and the annotations were unreadable in
# print. The file is resolved through the installed DejaVu family so that the
# figure does not depend on a font that only happens to be present.
FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
)
DEFAULT_FONT_SIZE = 34


def load_font(size):
    for candidate in FONT_CANDIDATES:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    raise SystemExit("no usable TrueType font found for the panel annotations")

# Top-down footprint of the simulated car, in metres. Local x is lateral and
# local y is longitudinal, the body frame the trace records hull angles in. The
# outline is the union boundary of the four Box2D hull fixtures of the
# environment (SIZE = 0.02 in gym.envs.box2d.car_dynamics): 5.0 m from nose to
# tail, 2.4 m across the widest panel, the bumpers slightly wider than the cabin.
HULL_SILHOUETTE = [
    (1.2, 2.6), (1.2, 2.2), (0.4, 2.2), (0.4, 0.4),
    (1.0, -0.2), (1.0, -0.8), (0.4, -1.8), (1.0, -1.8),
    (1.0, -2.4), (-1.0, -2.4), (-1.0, -1.8), (-0.4, -1.8),
    (-1.0, -0.8), (-1.0, -0.2), (-0.4, 0.4), (-0.4, 2.2),
    (-1.2, 2.2), (-1.2, 2.6),
]

# Wheel rectangles and the cabin panel that makes the nose readable, both in the
# same body frame.
WHEEL_CENTRES = [(-1.1, 1.6), (1.1, 1.6), (-1.1, -1.64), (1.1, -1.64)]
WHEEL_HALF_LATERAL = 0.28
WHEEL_HALF_LONGITUDINAL = 0.54
WHEEL_COLOUR = (44, 48, 56)
CANOPY = [(0.44, 1.15), (0.54, -0.25), (-0.54, -0.25), (-0.44, 1.15)]
CANOPY_TINT = 0.55


def hex_to_rgb(value):
    value = value.lstrip("#")
    return tuple(int(value[idx:idx + 2], 16) for idx in (0, 2, 4))


def rebuild_env(initial):
    scenario = initial["scenario"]
    return make_env(
        num_agents=initial["num_agents"],
        seed=initial["seed"],
        observation_type=initial["observation_type"],
        start_order=scenario["start_order"],
        line_spacing=scenario["line_spacing"],
        lateral_spacing=scenario["lateral_spacing"],
        track_path=None,
        max_neighbors=initial["env_max_neighbors"],
        telemetry_version=initial["telemetry_version"],
        neighbor_order=initial["neighbor_order"],
    )


def check_scene(env, initial):
    positions = [np.asarray(car.hull.position, dtype=np.float32) for car in env.unwrapped.cars]
    record = np.asarray(initial["positions"], dtype=np.float32)
    if len(positions) != len(record):
        raise SystemExit(f"scene mismatch: {len(positions)} cars against {len(record)} recorded")
    drift = max(float(np.abs(pos - ref).max()) for pos, ref in zip(positions, record))
    track = np.asarray(env.unwrapped.track, dtype=np.float32)
    if not np.allclose(track, np.asarray(initial["track"], dtype=np.float32)):
        raise SystemExit("scene mismatch: the rebuilt track differs from the recorded track")
    if drift > 1e-4:
        raise SystemExit(f"scene mismatch: initial poses differ by {drift:.6f} m")
    return drift


def lateral_offset(row, index, points, normal):
    idx = min(max(int(row["track_index"][index]), 0), len(points) - 1)
    delta = np.asarray(row["positions"][index], dtype=np.float64) - points[idx]
    return float(np.dot(delta, normal[idx])) / TRACK_WIDTH


def nearest_rival(row, index):
    pos = np.asarray(row["positions"], dtype=np.float64)
    gaps = np.linalg.norm(pos - pos[index], axis=1)
    gaps[index] = np.inf
    rival = int(np.argmin(gaps))
    return rival, float(gaps[rival])


def closest_approach_step(trace, index):
    best_step, best_gap, best_rival = None, None, None
    for row in trace:
        rival, gap = nearest_rival(row, index)
        if best_gap is None or gap < best_gap:
            best_step, best_gap, best_rival = int(row["step"]), gap, rival
    return best_step, best_gap, best_rival


def choose_step(trace, index, requested):
    if requested != "auto":
        return int(requested), None
    step, gap, rival = closest_approach_step(trace, index)
    return step, (gap, rival)


def world_window(centre, half_span, aspect):
    """Window that keeps ``half_span`` metres visible on the short side.

    The panel is wider than it is tall, so the window is widened to the panel's
    aspect ratio instead of leaving the extra pixels empty; the short side is the
    one that fixes the scale, and therefore the size of the cars on the page.
    """
    centre = np.asarray(centre, dtype=np.float64)
    half = np.array([half_span, half_span], dtype=np.float64)
    if aspect >= 1.0:
        half[0] *= aspect
    else:
        half[1] /= aspect
    return centre - half, centre + half


def projector(lo, hi, width, height):
    span = np.maximum(hi - lo, 1e-6)
    scale = min((width - 1) / span[0], (height - 1) / span[1])

    def project(points):
        xy = (np.asarray(points, dtype=np.float64) - lo) * scale
        out = np.empty_like(xy)
        out[:, 0] = xy[:, 0]
        out[:, 1] = height - 1 - xy[:, 1]
        return out

    return project, scale


def dashed_ring(draw, x, y, radius, colour, segments=16, width=2):
    for start in range(0, 360, 2 * (360 // segments)):
        draw.arc([x - radius, y - radius, x + radius, y + radius],
                 start=start, end=start + 360 // segments, fill=colour, width=width)


def body_to_world(local, origin, angle):
    """Rotate body-frame points into world coordinates about ``origin``."""
    cos_a, sin_a = math.cos(angle), math.sin(angle)
    points = np.asarray(local, dtype=np.float64)
    x = origin[0] + points[:, 0] * cos_a - points[:, 1] * sin_a
    y = origin[1] + points[:, 0] * sin_a + points[:, 1] * cos_a
    return np.stack([x, y], axis=1)


def mix(colour, other, weight):
    return tuple(int(round(c + (o - c) * weight)) for c, o in zip(colour, other))


def hull_box(project, position, angle):
    """Pixel bounding box of a car body, used to keep labels off the vehicles."""
    world = body_to_world(HULL_SILHOUETTE, np.asarray(position, dtype=np.float64), angle)
    pixels = project(world)
    return (float(pixels[:, 0].min()), float(pixels[:, 1].min()),
            float(pixels[:, 0].max()), float(pixels[:, 1].max()))


def intersects(first, second, gap=2.0):
    return not (first[2] + gap < second[0] or second[2] + gap < first[0]
                or first[3] + gap < second[1] or second[3] + gap < first[1])


def segment_hits(p0, p1, boxes, samples=24):
    for step in range(samples + 1):
        weight = step / samples
        point = (p0[0] + (p1[0] - p0[0]) * weight, p0[1] + (p1[1] - p0[1]) * weight)
        for box in boxes:
            if box[0] - 2.0 <= point[0] <= box[2] + 2.0 and box[1] - 2.0 <= point[1] <= box[3] + 2.0:
                return True
    return False


def label_candidates(push):
    """Offsets for a plaque, ordered from straight along ``push`` outwards."""
    base = math.atan2(push[1], push[0]) if (push[0] or push[1]) else -math.pi / 2.0
    offsets = (0.0, 0.7, -0.7, 1.4, -1.4, 2.1, -2.1, 2.8, -2.8, math.pi)
    return [(radius, base + delta) for radius in (3.2, 4.6, 6.2) for delta in offsets]


def place_label(draw, text, anchor, push, obstacles, width, height, scale, font, shielded=()):
    """Find a plaque position near ``anchor`` that covers no car and no label.

    The first candidate is the compact offset the earlier revision used; the
    remaining candidates fan outwards and to the other side, and the first one
    whose plaque clears every vehicle box and every plaque already placed is
    kept. A panel therefore never shows a label sitting on a car or on another
    label, which is what happens when four cars in a tight group all carry ids.
    """
    box = draw.textbbox((0, 0), text, font=font)
    text_w, text_h = box[2] - box[0], box[3] - box[1]
    pad_x, pad_y = 0.22 * font.size, 0.16 * font.size
    fallback = None
    for radius, angle in label_candidates(push):
        x = anchor[0] + radius * scale * math.cos(angle) - 0.5 * text_w
        y = anchor[1] + radius * scale * math.sin(angle) - 0.5 * text_h
        rect = (x - pad_x, y - pad_y, x + text_w + pad_x, y + text_h + pad_y)
        if rect[0] < 2.0 or rect[2] > width - 2.0 or rect[1] < 2.0 or rect[3] > height - 2.0:
            continue
        if fallback is None:
            fallback = rect
        if any(intersects(rect, obstacle) for obstacle in obstacles):
            continue
        centre = (0.5 * (rect[0] + rect[2]), 0.5 * (rect[1] + rect[3]))
        if segment_hits(centre, anchor, shielded):
            # a label whose leader would run across another car is read as
            # belonging to that car, so it is rejected even when the plaque
            # itself sits on free road
            continue
        return rect
    x = min(max(fallback[0], 2.0), width - (fallback[2] - fallback[0]) - 2.0)
    y = min(max(fallback[1], 2.0), height - (fallback[3] - fallback[1]) - 2.0)
    return (x, y, x + (fallback[2] - fallback[0]), y + (fallback[3] - fallback[1]))


def draw_car(draw, project, position, angle, colour, admitted=False):
    """Draw one vehicle as its hull footprint, wheels and cabin, in pose.

    ``admitted`` marks a car the neighbourhood selector took into the graph at
    this step: the body is tinted towards white and the hull outline is drawn
    thicker, so selection is visible without introducing a second colour code
    that could be confused with another controller's colour.
    """
    origin = np.asarray(position, dtype=np.float64)

    def shape(local, fill, outline=None, width=1):
        world = body_to_world(local, origin, angle)
        pixels = [tuple(map(float, point)) for point in project(world)]
        if outline is None:
            draw.polygon(pixels, fill=fill)
        else:
            draw.polygon(pixels, fill=fill, outline=outline, width=width)

    for centre_lateral, centre_longitudinal in WHEEL_CENTRES:
        tyre = [
            (centre_lateral - WHEEL_HALF_LATERAL, centre_longitudinal - WHEEL_HALF_LONGITUDINAL),
            (centre_lateral + WHEEL_HALF_LATERAL, centre_longitudinal - WHEEL_HALF_LONGITUDINAL),
            (centre_lateral + WHEEL_HALF_LATERAL, centre_longitudinal + WHEEL_HALF_LONGITUDINAL),
            (centre_lateral - WHEEL_HALF_LATERAL, centre_longitudinal + WHEEL_HALF_LONGITUDINAL),
        ]
        shape(tyre, WHEEL_COLOUR)
    body = mix(colour, (255, 255, 255), ADMITTED_TINT) if admitted else colour
    shape(HULL_SILHOUETTE, body, outline=ADMITTED_OUTLINE,
          width=ADMITTED_OUTLINE_WIDTH if admitted else 1)
    shape(CANOPY, mix(body, (255, 255, 255), CANOPY_TINT))


def draw_panel(env, trace, step, colour, index, lo, hi, width, height, trail_steps,
               rival, font, admitted=()):
    project, scale = projector(lo, hi, width, height)
    image = Image.new("RGB", (width, height), BACKGROUND)
    draw = ImageDraw.Draw(image)

    for vertices, rgb in env.unwrapped.road_poly:
        polygon = project(vertices)
        if (polygon[:, 0].max() < 0 or polygon[:, 0].min() > width
                or polygon[:, 1].max() < 0 or polygon[:, 1].min() > height):
            continue
        fill = tuple(int(np.clip(channel, 0.0, 1.0) * 255) for channel in rgb)
        draw.polygon([tuple(map(float, point)) for point in polygon], fill=fill)

    rows = trace[:step]
    for agent in range(len(trace[0]["positions"])):
        path = project([row["positions"][agent] for row in rows[-trail_steps:]])
        if len(path) < 2:
            continue
        points = [tuple(map(float, point)) for point in path]
        draw.line(points, fill=colour if agent == index else NEUTRAL,
                  width=max(2, int(round(scale * (0.9 if agent == index else 0.5)))))

    row = trace[step - 1]
    admitted = set(int(agent) for agent in admitted)
    drawn, obstacles, car_boxes = [], [], {}
    for agent in range(len(row["positions"])):
        x, y = project([row["positions"][agent]])[0]
        box = hull_box(project, row["positions"][agent], float(row["hull_angles"][agent]))
        if box[0] < 1.0 or box[1] < 1.0 or box[2] > width - 1.0 or box[3] > height - 1.0:
            # a car whose body straddles the window edge would be drawn as a
            # half vehicle, which reads as a rendering fault rather than as a
            # crop; the window is sized so that the pair under discussion and
            # its immediate surroundings are always fully inside
            continue
        drawn.append(agent)
        car_boxes[agent] = box
        # a plaque is kept a few pixels clear of the body, not merely off it, so
        # that it cannot be read as belonging to the neighbouring car
        obstacles.append((box[0] - 5.0, box[1] - 5.0, box[2] + 5.0, box[3] + 5.0))
        fill = colour if agent == index else NEUTRAL
        draw_car(draw, project, row["positions"][agent], float(row["hull_angles"][agent]),
                 fill, admitted=(agent in admitted))
        if agent == rival:
            # a ring around the whole 5 m hull marks the rival the distance in
            # the caption is measured to; the dark halo keeps it visible on the
            # grey road surface
            dashed_ring(draw, x, y, scale * 3.0, (30, 34, 40), width=5)
            dashed_ring(draw, x, y, scale * 3.0, (255, 255, 255), width=2)

    # the pair the caption talks about is labelled first, then the cars the
    # selector admitted, so that the ids can be matched to the bodies on the
    # track; the rest of the field stays unlabelled. Which controller the panel
    # shows, and at which step, is text in the caption rather than a plaque in
    # the raster: the manuscript names both panels there, and a filled box in
    # the corner of a journal figure reads as a debug overlay.
    pad_x, pad_y = 0.22 * font.size, 0.16 * font.size
    labelled = [index]
    if rival in drawn:
        labelled.append(rival)
    labelled += [agent for agent in sorted(admitted) if agent in drawn
                 and agent != index and agent != rival]
    anchors = {agent: tuple(project([row["positions"][agent]])[0]) for agent in labelled}
    cluster = np.mean([anchor for anchor in anchors.values()], axis=0)
    placements = []
    for agent in labelled:
        anchor = anchors[agent]
        text = f"A{agent}"
        others = [box for owner, box in car_boxes.items() if owner != agent]
        # the plaque is pushed outwards from the group, so ids never pile up in
        # the middle of the pack where they would be unreadable
        push = (anchor[0] - float(cluster[0]), anchor[1] - float(cluster[1]))
        rect = place_label(draw, text, anchor, push, obstacles, width, height, scale,
                           font, shielded=others)
        obstacles.append(rect)
        if agent == rival:
            # the dashed ring around the rival is part of its marker, so later
            # plaques are kept off it as well
            obstacles.append((anchor[0] - 3.0 * scale, anchor[1] - 3.0 * scale,
                              anchor[0] + 3.0 * scale, anchor[1] + 3.0 * scale))
        placements.append((rect, anchor, text))

    # leaders are drawn first so that the plaques cover their inner ends; a
    # leader is what tells the reader which body an id belongs to when four cars
    # pass within a few metres of one another
    for rect, anchor, _ in placements:
        start = (0.5 * (rect[0] + rect[2]), 0.5 * (rect[1] + rect[3]))
        draw.line([start, anchor], fill=(255, 255, 255), width=max(2, int(round(font.size / 12.0))))
    for rect, _, text in placements:
        draw.rectangle(rect, fill=BACKGROUND)
        draw.text((rect[0] + pad_x, rect[1] + pad_y), text, font=font, fill=LABEL_COLOUR)

    return image


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--case-dir", required=True)
    parser.add_argument("--num-agents", type=int, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--panel", action="append", required=True,
                        help="ALGORITHM:LABEL:STEP, repeatable; STEP may be 'auto'")
    parser.add_argument("--out", required=True, help="output prefix, without extension")
    parser.add_argument("--half-span", type=float, default=10.0,
                        help="metres visible on the short side of a panel")
    parser.add_argument("--width", type=int, default=1180)
    parser.add_argument("--panel-height", type=int, default=400)
    parser.add_argument("--trail-steps", type=int, default=140)
    parser.add_argument("--font-size", type=int, default=DEFAULT_FONT_SIZE,
                        help="annotation size in pixels; the panel is placed at one "
                             "column width in the manuscript, so 34 px is about 7 pt")
    parser.add_argument("--dpi", type=int, default=300)
    args = parser.parse_args()

    root = Path(args.root)
    stem = f"n{args.num_agents}_seed{args.seed}"
    records = {}
    for spec in args.panel:
        parts = spec.split(":")
        if len(parts) < 3:
            raise SystemExit(f"panel spec must be ALGORITHM:LABEL:STEP, got {spec!r}")
        algorithm, label, mode = parts[0], ":".join(parts[1:-1]), parts[-1]
        initial = json.loads((root / args.case_dir / "traces" / f"{algorithm}_{stem}.initial.json").read_text())
        trace = json.loads((root / args.case_dir / "traces" / f"{algorithm}_{stem}.trace.json").read_text())
        records[algorithm] = (label, initial, trace, mode)

    first = next(iter(records.values()))[1]
    env = rebuild_env(first)
    env.reset()
    drift = check_scene(env, first)
    points = np.asarray(first["track"], dtype=np.float64)[:, 2:4]
    normal = np.stack([np.cos(np.asarray(first["track"], dtype=np.float64)[:, 1]),
                       np.sin(np.asarray(first["track"], dtype=np.float64)[:, 1])], 1)
    index = args.num_agents - 1
    font = load_font(args.font_size)

    panels, rows = [], []
    for algorithm, (label, initial, trace, mode) in records.items():
        step, _ = choose_step(trace, index, mode)
        row = trace[step - 1]
        rival, gap = nearest_rival(row, index)
        debug = row.get("target_policy_debug") or {}
        admitted = debug.get("selected_neighbor_ids") or []
        colour = hex_to_rgb(color_for_algorithm(algorithm))
        centre = 0.5 * (np.asarray(row["positions"][index], dtype=np.float64)
                        + np.asarray(row["positions"][rival], dtype=np.float64))
        lo, hi = world_window(centre, args.half_span, args.width / args.panel_height)
        panels.append(draw_panel(env, trace, step, colour, index, lo, hi,
                                 args.width, args.panel_height, args.trail_steps, rival,
                                 font, admitted=admitted))
        rows.append({
            "algorithm": algorithm, "panel_label": label, "step": step,
            "corridor_limit_units": TRACK_WIDTH,
            "admitted_neighbor_ids": " ".join(str(agent) for agent in admitted),
            "target_lateral_offset_units": round(lateral_offset(row, index, points, normal), 4),
            "rival_agent": rival,
            "rival_lateral_offset_units": round(lateral_offset(row, rival, points, normal), 4),
            "min_pair_distance_m": round(gap, 4),
            "target_speed_mps": round(float(row["speed"][index]), 4),
            "rival_speed_mps": round(float(row["speed"][rival]), 4),
            "target_rank": int(row["rank"][index]),
        })

    gap = 8
    sheet = Image.new("RGB", (args.width, len(panels) * args.panel_height + gap * (len(panels) - 1)), (255, 255, 255))
    for order, panel in enumerate(panels):
        sheet.paste(panel, (0, order * (args.panel_height + gap)))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out.with_suffix(".png"), dpi=(args.dpi, args.dpi))
    sheet.save(out.with_suffix(".pdf"), "PDF", resolution=args.dpi)
    with open(out.with_suffix(".csv"), "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"scene drift {drift:.2e} m; wrote {out.with_suffix('.pdf')} and {out.with_suffix('.csv')}")
    for record in rows:
        print("  ", record)


if __name__ == "__main__":
    main()
