#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import json
import math
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
try:
    import imageio.v2 as imageio
except Exception:  # pragma: no cover - optional dependency for video export
    imageio = None

from dlc.policies import (
    TelemetryCruisePolicy,
    TelemetryLanePolicy,
    TelemetryYieldPolicy,
    make_policy,
)
from dlc.rollout import make_env
try:
    from tits_figure_style import VEHICLE_COLORS_RGB, label_for_algorithm
except ImportError:
    from scripts.tits_figure_style import VEHICLE_COLORS_RGB, label_for_algorithm


COLORS = VEHICLE_COLORS_RGB

DEFAULT_ALGORITHMS = [
    {
        "name": "v6_runtime_dynamic_neighborhood",
        "label_cn": "v6动态邻域DLC",
        "policy": "outputs/tits_dynamic_graph/models/ours_dynamic_graph_dlc_world/graph_risk_dlc_world.graphworld.pt",
        "neighbor_mode": "dynamic",
        "neighbor_selection_mode": "interaction",
        "max_neighbors": None,
        "overtake_aware_planner": True,
        "quality_proposal_path": "outputs/tits_dynamic_graph/models/quality_graph_bc_v1/graph_bc.graph.pt",
        "quality_planner_mode": "quality_guided_rollout",
        "quality_rollout_blend": 0.25,
        "quality_overtake_weight": 0.20,
        "quality_lane_weight": 0.25,
        "quality_grass_weight": 0.65,
        "quality_close_gap_weight": 0.20,
        "kind": "runtime_dynamic_neighborhood_graph_dlc_world",
    },
    {
        "name": "v6_runtime_dynamic_neighborhood_fast",
        "label_cn": "v6动态邻域DLC-fast",
        "policy": "outputs/tits_dynamic_graph/models/ours_dynamic_graph_dlc_world/graph_risk_dlc_world.graphworld.pt",
        "neighbor_mode": "dynamic",
        "neighbor_selection_mode": "interaction",
        "max_neighbors": None,
        "planner_horizon": 3,
        "planner_candidates": 10,
        "overtake_aware_planner": True,
        "quality_proposal_path": "outputs/tits_dynamic_graph/models/quality_graph_bc_v1/graph_bc.graph.pt",
        "quality_planner_mode": "quality_guided_rollout",
        "quality_rollout_blend": 0.20,
        "quality_overtake_weight": 0.18,
        "quality_lane_weight": 0.22,
        "quality_grass_weight": 0.60,
        "quality_close_gap_weight": 0.18,
        "kind": "runtime_dynamic_neighborhood_graph_dlc_world_fast",
    },
    {
        "name": "v6_runtime_dynamic_neighborhood_safe",
        "label_cn": "v6动态邻域DLC-safe",
        "policy": "outputs/tits_dynamic_graph/models/ours_dynamic_graph_dlc_world/graph_risk_dlc_world.graphworld.pt",
        "neighbor_mode": "dynamic",
        "neighbor_selection_mode": "interaction",
        "max_neighbors": None,
        "planner_horizon": 4,
        "planner_candidates": 12,
        "planner_risk_weight": 1.65,
        "planner_uncertainty_weight": 0.40,
        "overtake_aware_planner": True,
        "quality_proposal_path": "outputs/tits_dynamic_graph/models/quality_graph_bc_v1/graph_bc.graph.pt",
        "quality_planner_mode": "quality_guided_rollout",
        "quality_rollout_blend": 0.25,
        "quality_overtake_weight": 0.18,
        "quality_lane_weight": 0.35,
        "quality_grass_weight": 0.90,
        "quality_close_gap_weight": 0.25,
        "geometry_generalization": True,
        "geometry_curvature_lookahead": 10,
        "geometry_curvature_speed_weight": 20.0,
        "geometry_lateral_speed_weight": 5.0,
        "geometry_heading_speed_weight": 5.5,
        "geometry_min_speed": 9.5,
        "geometry_anchor_blend": 0.38,
        "geometry_barrier_weight": 0.75,
        "kind": "runtime_dynamic_neighborhood_graph_dlc_world_safe",
    },
    {
        "name": "v7_elegance_barrier_dlc_world",
        "label_cn": "v7desirable behavior约束DLC",
        "policy": "outputs/tits_dynamic_graph/models/ours_dynamic_graph_dlc_world/graph_risk_dlc_world.graphworld.pt",
        "neighbor_mode": "dynamic",
        "neighbor_selection_mode": "interaction",
        "max_neighbors": None,
        "planner_horizon": 4,
        "planner_candidates": 14,
        "planner_risk_weight": 1.75,
        "planner_uncertainty_weight": 0.42,
        "overtake_aware_planner": True,
        "quality_proposal_path": "outputs/tits_dynamic_graph/models/quality_graph_bc_v1/graph_bc.graph.pt",
        "quality_planner_mode": "quality_guided_rollout",
        "quality_rollout_blend": 0.24,
        "quality_overtake_weight": 0.16,
        "quality_lane_weight": 0.38,
        "quality_grass_weight": 1.05,
        "quality_close_gap_weight": 0.32,
        "elegance_barrier": True,
        "elegance_barrier_weight": 1.15,
        "elegance_lateral_limit": 0.30,
        "elegance_heading_cos_min": 0.82,
        "elegance_grass_penalty": 2.25,
        "elegance_backward_penalty": 1.25,
        "elegance_close_gap_limit": 8.0,
        "kind": "diagnostic_driven_elegance_barrier_graph_dlc_world",
    },
    {
        "name": "ours_dynamic_graph_dlc_world",
        "label_cn": "本文方法",
        "policy": "outputs/tits_dynamic_graph/models/ours_dynamic_graph_dlc_world/graph_risk_dlc_world.graphworld.pt",
        "neighbor_mode": "dynamic",
        "max_neighbors": None,
        "overtake_aware_planner": True,
        "kind": "optimized_dynamic_graph_dlc_world",
    },
    {
        "name": "ours_no_overtake_aware_planner",
        "label_cn": "本文-无超车规划",
        "policy": "outputs/tits_dynamic_graph/models/ours_dynamic_graph_dlc_world/graph_risk_dlc_world.graphworld.pt",
        "neighbor_mode": "dynamic",
        "max_neighbors": None,
        "overtake_aware_planner": False,
        "kind": "ablation_without_overtake_aware_planner",
    },
    {
        "name": "quality_proposal_dlc_world_v1",
        "label_cn": "质量Proposal-DLC",
        "policy": "outputs/tits_dynamic_graph/models/ours_dynamic_graph_dlc_world/graph_risk_dlc_world.graphworld.pt",
        "neighbor_mode": "dynamic",
        "max_neighbors": None,
        "overtake_aware_planner": True,
        "quality_proposal_path": "outputs/tits_dynamic_graph/models/quality_graph_bc_v1/graph_bc.graph.pt",
        "kind": "quality_proposal_graph_dlc_world",
    },
    {
        "name": "quality_proposal_dlc_world_v2",
        "label_cn": "质量Proposal-DLC-v2",
        "policy": "outputs/tits_dynamic_graph/models/ours_dynamic_graph_dlc_world/graph_risk_dlc_world.graphworld.pt",
        "neighbor_mode": "dynamic",
        "max_neighbors": None,
        "overtake_aware_planner": True,
        "quality_proposal_path": "outputs/tits_dynamic_graph/models/quality_graph_bc_v2/graph_bc.graph.pt",
        "kind": "quality_proposal_graph_dlc_world",
    },
    {
        "name": "quality_guided_dlc_world_v3",
        "label_cn": "质量引导DLC-v3",
        "policy": "outputs/tits_dynamic_graph/models/ours_dynamic_graph_dlc_world/graph_risk_dlc_world.graphworld.pt",
        "neighbor_mode": "dynamic",
        "max_neighbors": None,
        "overtake_aware_planner": True,
        "quality_proposal_path": "outputs/tits_dynamic_graph/models/quality_graph_bc_v2/graph_bc.graph.pt",
        "quality_planner_mode": "quality_guided_rollout",
        "quality_rollout_blend": 0.65,
        "quality_overtake_weight": 0.35,
        "quality_lane_weight": 0.35,
        "quality_grass_weight": 1.15,
        "quality_close_gap_weight": 0.25,
        "kind": "quality_guided_graph_dlc_world",
    },
    {
        "name": "quality_aux_dlc_world_v4",
        "label_cn": "质量辅助DLC-v4",
        "policy": "outputs/tits_dynamic_graph/models/quality_aux_dlc_world_v4/graph_risk_dlc_world.graphworld.pt",
        "neighbor_mode": "dynamic",
        "max_neighbors": None,
        "overtake_aware_planner": True,
        "quality_proposal_path": "outputs/tits_dynamic_graph/models/quality_graph_bc_v2/graph_bc.graph.pt",
        "quality_planner_mode": "quality_guided_rollout",
        "quality_rollout_blend": 0.45,
        "quality_overtake_weight": 0.25,
        "quality_lane_weight": 0.25,
        "quality_grass_weight": 0.80,
        "quality_close_gap_weight": 0.20,
        "learned_quality_weight": 1.00,
        "kind": "quality_auxiliary_graph_dlc_world",
    },
    {
        "name": "quality_aux_dlc_world_v5_soft025",
        "label_cn": "质量辅助DLC-v5-soft025",
        "policy": "outputs/tits_dynamic_graph/models/quality_aux_dlc_world_v4/graph_risk_dlc_world.graphworld.pt",
        "neighbor_mode": "dynamic",
        "max_neighbors": None,
        "overtake_aware_planner": True,
        "quality_proposal_path": "outputs/tits_dynamic_graph/models/quality_graph_bc_v1/graph_bc.graph.pt",
        "quality_planner_mode": "quality_guided_rollout",
        "quality_rollout_blend": 0.25,
        "quality_overtake_weight": 0.15,
        "quality_lane_weight": 0.20,
        "quality_grass_weight": 0.45,
        "quality_close_gap_weight": 0.15,
        "learned_quality_weight": 0.25,
        "kind": "quality_auxiliary_graph_dlc_world_sweep",
    },
    {
        "name": "quality_aux_dlc_world_v5_soft050",
        "label_cn": "质量辅助DLC-v5-soft050",
        "policy": "outputs/tits_dynamic_graph/models/quality_aux_dlc_world_v4/graph_risk_dlc_world.graphworld.pt",
        "neighbor_mode": "dynamic",
        "max_neighbors": None,
        "overtake_aware_planner": True,
        "quality_proposal_path": "outputs/tits_dynamic_graph/models/quality_graph_bc_v1/graph_bc.graph.pt",
        "quality_planner_mode": "quality_guided_rollout",
        "quality_rollout_blend": 0.30,
        "quality_overtake_weight": 0.20,
        "quality_lane_weight": 0.25,
        "quality_grass_weight": 0.60,
        "quality_close_gap_weight": 0.20,
        "learned_quality_weight": 0.50,
        "kind": "quality_auxiliary_graph_dlc_world_sweep",
    },
    {
        "name": "quality_aux_dlc_world_v5_gate025",
        "label_cn": "质量辅助DLC-v5-gate025",
        "policy": "outputs/tits_dynamic_graph/models/quality_aux_dlc_world_v4/graph_risk_dlc_world.graphworld.pt",
        "neighbor_mode": "dynamic",
        "max_neighbors": None,
        "overtake_aware_planner": True,
        "quality_proposal_path": "outputs/tits_dynamic_graph/models/quality_graph_bc_v1/graph_bc.graph.pt",
        "quality_planner_mode": "quality_guided_rollout",
        "quality_rollout_blend": 0.25,
        "quality_overtake_weight": 0.15,
        "quality_lane_weight": 0.20,
        "quality_grass_weight": 0.45,
        "quality_close_gap_weight": 0.15,
        "learned_quality_weight": 0.25,
        "learned_quality_gate": True,
        "learned_quality_min_on_track": 0.45,
        "learned_quality_max_grass": 0.55,
        "learned_quality_max_lane_error": 0.72,
        "learned_quality_gate_penalty": 1.50,
        "kind": "quality_auxiliary_graph_dlc_world_sweep",
    },
    {
        "name": "graph_bc_dynamic",
        "label_cn": "图BC",
        "policy": "outputs/tits_dynamic_graph/models/graph_bc_dynamic/graph_bc.graph.pt",
        "neighbor_mode": "dynamic",
        "max_neighbors": None,
        "kind": "graph_behavior_cloning",
    },
    {
        "name": "quality_graph_bc_v1",
        "label_cn": "质量图BC-v1",
        "policy": "outputs/tits_dynamic_graph/models/quality_graph_bc_v1/graph_bc.graph.pt",
        "neighbor_mode": "dynamic",
        "max_neighbors": None,
        "kind": "quality_filtered_graph_behavior_cloning",
    },
    {
        "name": "quality_graph_bc_v2",
        "label_cn": "质量图BC-v2",
        "policy": "outputs/tits_dynamic_graph/models/quality_graph_bc_v2/graph_bc.graph.pt",
        "neighbor_mode": "dynamic",
        "max_neighbors": None,
        "kind": "quality_filtered_graph_behavior_cloning",
    },
    {
        "name": "dlc_world_original",
        "label_cn": "DLC世界模型",
        "policy": "outputs/paper_multicar_overtake_20260618/models/graph_risk_world_model/graph_risk_dlc_world.graphworld.pt",
        "neighbor_mode": "dynamic",
        "max_neighbors": None,
        "overtake_aware_planner": False,
        "kind": "dlc_world_model_baseline",
    },
    {
        "name": "dlc_world_balanced",
        "label_cn": "DLC-balanced",
        "policy": "outputs/paper_multicar_overtake_20260618/models/graph_risk_world_model_variants/graph_risk_dlc_world_balanced.graphworld.pt",
        "neighbor_mode": "dynamic",
        "max_neighbors": None,
        "overtake_aware_planner": False,
        "kind": "dlc_world_model_variant",
    },
    {
        "name": "dlc_world_safety",
        "label_cn": "DLC-safety",
        "policy": "outputs/paper_multicar_overtake_20260618/models/graph_risk_world_model_variants/graph_risk_dlc_world_safety.graphworld.pt",
        "neighbor_mode": "dynamic",
        "max_neighbors": None,
        "overtake_aware_planner": False,
        "kind": "dlc_world_model_variant",
    },
    {
        "name": "dlc_world_fast",
        "label_cn": "DLC-fast",
        "policy": "outputs/paper_multicar_overtake_20260618/models/graph_risk_world_model_variants/graph_risk_dlc_world_fast.graphworld.pt",
        "neighbor_mode": "dynamic",
        "max_neighbors": None,
        "overtake_aware_planner": False,
        "kind": "dlc_world_model_variant",
    },
    {
        "name": "rule_expert_gate",
        "label_cn": "规则专家",
        "policy": "telemetry_expert_gate",
        "neighbor_mode": "fixed",
        "max_neighbors": None,
        "kind": "rule_baseline",
    },
    {
        "name": "rule_adaptive_gate",
        "label_cn": "规则自适应",
        "policy": "telemetry_adaptive",
        "neighbor_mode": "fixed",
        "max_neighbors": None,
        "kind": "rule_baseline",
    },
]


def load_config(path):
    if not path:
        return {}
    config_path = Path(path)
    if not config_path.exists():
        return {}
    return json.loads(config_path.read_text(encoding="utf-8"))


def ensure_dirs(root):
    root = Path(root)
    dirs = {
        "root": root,
        "summaries": root / "summaries",
        "traces": root / "traces",
        "gifs": root / "gifs",
        "tables": root / "tables",
        "figures": root / "figures",
        "logs": root / "logs",
    }
    for path in dirs.values():
        path.mkdir(parents=True, exist_ok=True)
    return dirs


def world_bounds(env, margin=30.0):
    points = []
    for vertices, _ in env.unwrapped.road_poly:
        points.extend(vertices)
    points = np.asarray(points, dtype=np.float32)
    lo = points.min(axis=0) - margin
    hi = points.max(axis=0) + margin
    return lo, hi


def transform_points(points, lo, hi, width, height):
    points = np.asarray(points, dtype=np.float32)
    span = np.maximum(hi - lo, 1.0)
    scale = min((width - 1) / span[0], (height - 1) / span[1])
    centered_span = np.array([width, height], dtype=np.float32) / scale
    pad = (centered_span - span) / 2.0
    xy = (points - (lo - pad)) * scale
    xy[:, 1] = height - xy[:, 1]
    return [tuple(map(float, item)) for item in xy]


def draw_topdown_frame(env, histories, step, labels, target_agent, total_reward, lo, hi, width, height, agent_colors=None):
    image = Image.new("RGB", (width, height), (36, 113, 61))
    draw = ImageDraw.Draw(image)
    palette = agent_colors or COLORS

    for vertices, color in env.unwrapped.road_poly:
        rgb = tuple(int(np.clip(c, 0.0, 1.0) * 255) for c in color)
        draw.polygon(transform_points(vertices, lo, hi, width, height), fill=rgb)

    for agent_id, history in enumerate(histories):
        if len(history) > 1:
            draw.line(
                transform_points(history, lo, hi, width, height),
                fill=palette[agent_id % len(palette)],
                width=4 if agent_id == target_agent else 2,
            )

    positions = [np.asarray(car.hull.position, dtype=np.float32) for car in env.unwrapped.cars]
    for agent_id, pos in enumerate(positions):
        x, y = transform_points([pos], lo, hi, width, height)[0]
        radius = 7 if agent_id == target_agent else 5
        color = palette[agent_id % len(palette)]
        draw.ellipse([x - radius, y - radius, x + radius, y + radius], fill=color, outline=(255, 255, 255))
        draw.text((x + 8, y - 8), f"A{agent_id}", fill=(255, 255, 255))

    lines = [f"step {step}", f"target A{target_agent}: {labels[target_agent]}"]
    for agent_id, label in enumerate(labels):
        lines.append(f"A{agent_id} {label} tiles {env.unwrapped.tile_visited_count[agent_id]} R {total_reward[agent_id]:.1f}")
    x, y = 10, 10
    box_w = max(draw.textlength(line) for line in lines) + 16
    box_h = 18 * len(lines) + 10
    draw.rectangle([x - 5, y - 5, x + box_w, y + box_h], fill=(0, 0, 0))
    for idx, line in enumerate(lines):
        draw.text((x, y + 18 * idx), line, fill=(255, 255, 255))
    return image


def make_background_policy(agent_id, profile):
    if profile == "slow_traffic":
        speeds = [11.0, 11.8, 12.6, 13.4, 14.2, 15.0, 15.8]
        speed = speeds[agent_id % len(speeds)]
        if agent_id % 3 == 0:
            return TelemetryLanePolicy(target_speed=speed, gas=0.40, brake=0.55, name=f"bg_lane_{agent_id}")
        if agent_id % 3 == 1:
            return TelemetryCruisePolicy(target_speed=speed, gas=0.38, brake=0.55, name=f"bg_cruise_{agent_id}")
        return TelemetryYieldPolicy(target_speed=speed, yield_speed=max(speed - 2.0, 8.0), gas=0.38, brake=0.55, name=f"bg_yield_{agent_id}")
    if profile == "mixed_traffic":
        speeds = [12.5, 13.5, 14.5, 15.5, 16.5, 17.5, 18.0]
        speed = speeds[agent_id % len(speeds)]
        if agent_id % 3 == 0:
            return TelemetryCruisePolicy(target_speed=speed, gas=0.44, brake=0.48, name=f"bg_cruise_{agent_id}")
        if agent_id % 3 == 1:
            return TelemetryYieldPolicy(target_speed=speed, yield_speed=max(speed - 3.0, 9.0), gas=0.42, brake=0.50, name=f"bg_yield_{agent_id}")
        return TelemetryLanePolicy(target_speed=speed, gas=0.46, brake=0.46, name=f"bg_lane_{agent_id}")
    raise ValueError(f"unknown traffic profile: {profile}")


class TargetOnlyPolicy:
    def __init__(self, target_policy, target_agent, background_policies):
        self.target_policy = target_policy
        self.target_agent = int(target_agent)
        self.background_policies = background_policies
        self.name = getattr(target_policy, "name", "target_policy")

    def reset(self):
        self.target_policy.reset()
        if hasattr(self.target_policy, "set_controlled_agent"):
            self.target_policy.set_controlled_agent(self.target_agent)
        for policy in self.background_policies.values():
            policy.reset()

    def act(self, env, obs):
        num_agents = env.unwrapped.num_agents
        actions = np.zeros((num_agents, 3), dtype=np.float32)
        for agent_id, policy in self.background_policies.items():
            actions[agent_id] = policy.act(env, obs)[agent_id]
        if hasattr(self.target_policy, "set_controlled_agent"):
            self.target_policy.set_controlled_agent(self.target_agent)
        target_actions = self.target_policy.act(env, obs)
        target_actions = np.asarray(target_actions, dtype=np.float32)
        if target_actions.shape == (3,):
            actions[self.target_agent] = target_actions
        else:
            actions[self.target_agent] = target_actions[self.target_agent]
        actions[:, 0] = np.clip(actions[:, 0], -1.0, 1.0)
        actions[:, 1:] = np.clip(actions[:, 1:], 0.0, 1.0)
        return actions


def rank_from_tiles(tile_counts):
    tile_counts = np.asarray(tile_counts, dtype=np.float32)
    return (np.argsort(-tile_counts).argsort() + 1).astype(int).tolist()


def track_indices(env):
    track_xy = np.asarray(env.unwrapped.track, dtype=np.float32)[:, 2:]
    out = []
    for car in env.unwrapped.cars:
        pos = np.asarray(car.hull.position, dtype=np.float32).reshape(1, 2)
        out.append(int(np.argmin(np.linalg.norm(pos - track_xy, axis=1))))
    return out


def compute_overtake_events(trace, target_agent, track_tiles, start_gap_frac=0.18, pass_margin=2):
    if not trace:
        return []
    target_agent = int(target_agent)
    num_agents = len(trace[0]["tile_visited_count"])
    start_gap = max(4, int(round(float(track_tiles) * start_gap_frac)))
    states = {}
    events = []
    for row in trace:
        step = int(row["step"])
        tiles = row["tile_visited_count"]
        target_tiles = int(tiles[target_agent])
        for other in range(num_agents):
            if other == target_agent:
                continue
            other_tiles = int(tiles[other])
            gap = other_tiles - target_tiles
            state = states.get(other)
            if state is None and 1 <= gap <= start_gap:
                states[other] = {
                    "opponent": other,
                    "start_step": step,
                    "start_gap_tiles": gap,
                }
            elif state is not None and target_tiles >= other_tiles + pass_margin:
                state = dict(state)
                state["complete_step"] = step
                state["duration_steps"] = step - int(state["start_step"])
                state["complete_gap_tiles"] = target_tiles - other_tiles
                events.append(state)
                states[other] = None
    return events


def _trace_window(trace, start_step, complete_step):
    start_step = int(start_step)
    complete_step = int(complete_step)
    return [row for row in trace if start_step <= int(row["step"]) <= complete_step]


def annotate_overtake_quality(
    trace,
    events,
    target_agent,
    on_track_grass_threshold=0.10,
    on_track_lateral_threshold=0.45,
    elegant_lateral_threshold=0.30,
    contact_distance=3.0,
):
    """Attach event-level quality indicators used for publication-grade overtake analysis."""
    annotated = []
    for event in events:
        window = _trace_window(trace, event["start_step"], event["complete_step"])
        item = dict(event)
        if not window:
            item.update(
                {
                    "window_steps": 0,
                    "window_grass_rate": None,
                    "window_backward_rate": None,
                    "window_mean_abs_lateral": None,
                    "window_max_abs_lateral": None,
                    "window_heading_error_mean_rad": None,
                    "window_contact_proxy": None,
                    "on_track_overtake": False,
                    "elegant_overtake": False,
                }
            )
            annotated.append(item)
            continue

        grass = np.asarray([row["telemetry"]["on_grass"][target_agent] for row in window], dtype=np.float32)
        backward = np.asarray([row["telemetry"]["backward"][target_agent] for row in window], dtype=np.float32)
        lateral = np.asarray([row["telemetry"]["lateral_error"][target_agent] for row in window], dtype=np.float32)
        heading_cos = np.asarray([row["telemetry"]["heading_cos"][target_agent] for row in window], dtype=np.float32)
        min_pair = np.asarray(
            [row["min_pair_distance"] for row in window if row.get("min_pair_distance") is not None],
            dtype=np.float32,
        )
        grass_rate = float(grass.mean()) if grass.size else None
        backward_rate = float(backward.mean()) if backward.size else None
        mean_abs_lateral = float(np.abs(lateral).mean()) if lateral.size else None
        max_abs_lateral = float(np.abs(lateral).max()) if lateral.size else None
        heading_error_mean = float(np.arccos(np.clip(heading_cos, -1.0, 1.0)).mean()) if heading_cos.size else None
        contact_proxy = float(np.mean(min_pair < contact_distance)) if min_pair.size else 0.0
        on_track = bool(
            (grass_rate is not None and grass_rate <= on_track_grass_threshold)
            and (backward_rate is not None and backward_rate <= 0.0)
            and (max_abs_lateral is not None and max_abs_lateral <= on_track_lateral_threshold)
        )
        elegant = bool(
            on_track
            and (mean_abs_lateral is not None and mean_abs_lateral <= elegant_lateral_threshold)
            and contact_proxy <= 0.0
        )
        item.update(
            {
                "window_steps": len(window),
                "window_grass_rate": grass_rate,
                "window_backward_rate": backward_rate,
                "window_mean_abs_lateral": mean_abs_lateral,
                "window_max_abs_lateral": max_abs_lateral,
                "window_heading_error_mean_rad": heading_error_mean,
                "window_contact_proxy": contact_proxy,
                "on_track_overtake": on_track,
                "elegant_overtake": elegant,
            }
        )
        annotated.append(item)
    return annotated


def grass_recovery_stats(trace, target_agent, grace=0):
    if not trace:
        return {
            "grass_recovery_time_mean": None,
            "grass_recovery_time_max": None,
            "grass_excursion_count": 0,
            "unrecovered_grass_excursion_count": 0,
        }
    grass = [bool(row["telemetry"]["on_grass"][target_agent]) for row in trace]
    recoveries = []
    excursions = 0
    unrecovered = 0
    in_grass = False
    start = None
    for idx, value in enumerate(grass):
        if idx < grace:
            continue
        if value and not in_grass:
            in_grass = True
            start = idx
            excursions += 1
        elif not value and in_grass:
            recoveries.append(idx - start)
            in_grass = False
            start = None
    if in_grass:
        unrecovered += 1
    return {
        "grass_recovery_time_mean": float(np.mean(recoveries)) if recoveries else None,
        "grass_recovery_time_max": int(max(recoveries)) if recoveries else None,
        "grass_excursion_count": int(excursions),
        "unrecovered_grass_excursion_count": int(unrecovered),
    }


def summarize_trace(trace, args, algorithm, target_agent, track_tiles, total_reward, steps_run, first_complete_step, gif_paths, video_paths, render_error):
    if trace:
        telemetry = [row["telemetry"] for row in trace]
        on_grass = np.asarray([row["on_grass"] for row in telemetry], dtype=np.float32)
        backward = np.asarray([row["backward"] for row in telemetry], dtype=np.float32)
        lateral = np.asarray([row["lateral_error"] for row in telemetry], dtype=np.float32)
        heading_cos = np.asarray([row["heading_cos"] for row in telemetry], dtype=np.float32)
        speed = np.asarray([row["speed"] for row in trace], dtype=np.float32)
        latency = np.asarray([row["compute_latency_ms"] for row in trace], dtype=np.float32)
        min_pair_distance = np.asarray([row["min_pair_distance"] for row in trace], dtype=np.float32)
        final_tiles = trace[-1]["tile_visited_count"]
        final_rank = trace[-1]["rank"]
    else:
        n = args.num_agents
        on_grass = backward = lateral = heading_cos = speed = np.zeros((0, n), dtype=np.float32)
        latency = min_pair_distance = np.zeros((0,), dtype=np.float32)
        final_tiles = [0] * n
        final_rank = list(range(1, n + 1))

    grace = min(20, max(len(trace) // 10, 0))
    eval_slice = slice(grace, None)
    events = compute_overtake_events(trace, target_agent, track_tiles)
    events = annotate_overtake_quality(
        trace,
        events,
        target_agent,
        contact_distance=args.contact_distance,
    )
    durations = [event["duration_steps"] for event in events]
    on_track_events = [event for event in events if event.get("on_track_overtake")]
    elegant_events = [event for event in events if event.get("elegant_overtake")]
    recovery_stats = grass_recovery_stats(trace, target_agent, grace=grace)
    target_final_rank = int(final_rank[target_agent]) if final_rank else args.num_agents
    initial_rank = args.num_agents
    target_progress = float(final_tiles[target_agent] / max(track_tiles, 1))
    target_completed = bool(final_tiles[target_agent] >= track_tiles)
    any_completed = bool(any(item >= track_tiles for item in final_tiles))
    completed_lap = [bool(item >= track_tiles) for item in final_tiles]
    first_overtake_complete = min((event["complete_step"] for event in events), default=None)
    first_overtake_start = min((event["start_step"] for event in events), default=None)
    overtake_duration = None
    if events:
        first_event = min(events, key=lambda item: item["complete_step"])
        overtake_duration = int(first_event["duration_steps"])
    debug_rows = [row.get("target_policy_debug", {}) for row in trace]
    hard_recovery_flags = [bool(row.get("hard_recovery", False)) for row in debug_rows]
    anchor_deviations = []
    anchor_matches = []
    for row in debug_rows:
        selected = row.get("selected_action")
        anchor = row.get("anchor_action")
        if selected is None or anchor is None:
            continue
        deviation = float(np.linalg.norm(np.asarray(selected, dtype=np.float32) - np.asarray(anchor, dtype=np.float32)))
        anchor_deviations.append(deviation)
        anchor_matches.append(deviation <= 1e-4)

    return {
        "algorithm": algorithm["name"],
        "algorithm_label_cn": algorithm.get("label_cn", algorithm["name"]),
        "algorithm_kind": algorithm.get("kind", ""),
        "neighbor_selection_mode": algorithm.get("neighbor_selection_mode", "legacy"),
        "planner_horizon": algorithm.get("planner_horizon"),
        "planner_candidates": algorithm.get("planner_candidates"),
        "planner_risk_weight": algorithm.get("planner_risk_weight"),
        "planner_progress_weight": algorithm.get("planner_progress_weight"),
        "planner_uncertainty_weight": algorithm.get("planner_uncertainty_weight"),
        "planner_overtake_weight": algorithm.get("planner_overtake_weight"),
        "planner_lane_weight": algorithm.get("planner_lane_weight"),
        "planner_grass_weight": algorithm.get("planner_grass_weight"),
        "planner_close_gap_weight": algorithm.get("planner_close_gap_weight"),
        "overtake_aware_planner": algorithm.get("overtake_aware_planner"),
        "elegance_barrier": algorithm.get("elegance_barrier", False),
        "elegance_barrier_weight": algorithm.get("elegance_barrier_weight"),
        "elegance_lateral_limit": algorithm.get("elegance_lateral_limit"),
        "elegance_heading_cos_min": algorithm.get("elegance_heading_cos_min"),
        "elegance_grass_penalty": algorithm.get("elegance_grass_penalty"),
        "elegance_backward_penalty": algorithm.get("elegance_backward_penalty"),
        "elegance_close_gap_limit": algorithm.get("elegance_close_gap_limit"),
        "geometry_generalization": algorithm.get("geometry_generalization", False),
        "geometry_curvature_lookahead": algorithm.get("geometry_curvature_lookahead"),
        "geometry_curvature_speed_weight": algorithm.get("geometry_curvature_speed_weight"),
        "geometry_lateral_speed_weight": algorithm.get("geometry_lateral_speed_weight"),
        "geometry_heading_speed_weight": algorithm.get("geometry_heading_speed_weight"),
        "geometry_min_speed": algorithm.get("geometry_min_speed"),
        "geometry_anchor_blend": algorithm.get("geometry_anchor_blend"),
        "geometry_barrier_weight": algorithm.get("geometry_barrier_weight"),
        "quality_planner_mode": algorithm.get("quality_planner_mode"),
        "quality_rollout_blend": algorithm.get("quality_rollout_blend"),
        "quality_overtake_weight": algorithm.get("quality_overtake_weight"),
        "quality_lane_weight": algorithm.get("quality_lane_weight"),
        "quality_grass_weight": algorithm.get("quality_grass_weight"),
        "quality_close_gap_weight": algorithm.get("quality_close_gap_weight"),
        "hard_safety_shield": algorithm.get("hard_safety_shield"),
        "use_rule_anchor": algorithm.get("use_rule_anchor", True),
        "use_handcrafted_candidates": algorithm.get("use_handcrafted_candidates", True),
        "use_geometry_recovery": algorithm.get("use_geometry_recovery", True),
        "policy": algorithm["policy"],
        "seed": int(args.seed),
        "num_agents": int(args.num_agents),
        "target_agent": int(target_agent),
        "track_path": args.track_path or "procedural",
        "traffic_profile": args.traffic_profile,
        "observation_type": args.observation_type,
        "start_order": list(range(args.num_agents)),
        "steps_run": int(steps_run),
        "track_tiles": int(track_tiles),
        "total_reward": np.asarray(total_reward, dtype=float).tolist(),
        "tile_visited_count": list(map(int, final_tiles)),
        "final_rank": list(map(int, final_rank)),
        "target_initial_rank": int(initial_rank),
        "target_final_rank": int(target_final_rank),
        "rank_gain": int(initial_rank - target_final_rank),
        "lap_completion_rate": float(target_completed),
        "target_completed_lap": target_completed,
        "any_completed_lap": any_completed,
        "completed_lap": completed_lap,
        "first_complete_step": first_complete_step,
        "finish_step": int(steps_run),
        "target_progress": target_progress,
        "overtake_success": bool(len(events) > 0),
        "overtake_success_rate": float(len(events) > 0),
        "overtake_count": int(len(events)),
        "overtake_events": events,
        "on_track_overtake_count": int(len(on_track_events)),
        "on_track_overtake_rate": float(len(on_track_events) / len(events)) if events else 0.0,
        "elegant_overtake_count": int(len(elegant_events)),
        "elegant_overtake_rate": float(len(elegant_events) / len(events)) if events else 0.0,
        "overtake_window_grass_rate_mean": float(np.mean([event["window_grass_rate"] for event in events if event.get("window_grass_rate") is not None])) if events else None,
        "overtake_window_max_abs_lateral_mean": float(np.mean([event["window_max_abs_lateral"] for event in events if event.get("window_max_abs_lateral") is not None])) if events else None,
        "time_to_first_overtake": first_overtake_complete,
        "overtake_start_step": first_overtake_start,
        "overtake_start_to_complete_time": overtake_duration,
        "grass_rate": on_grass[eval_slice].mean(axis=0).tolist() if len(trace) > grace else on_grass.mean(axis=0).tolist() if len(trace) else [],
        "backward_rate": backward[eval_slice].mean(axis=0).tolist() if len(trace) > grace else backward.mean(axis=0).tolist() if len(trace) else [],
        "target_grass_rate": float(on_grass[eval_slice, target_agent].mean()) if len(trace) > grace else float(on_grass[:, target_agent].mean()) if len(trace) else None,
        "target_backward_rate": float(backward[eval_slice, target_agent].mean()) if len(trace) > grace else float(backward[:, target_agent].mean()) if len(trace) else None,
        "target_mean_abs_lateral": float(np.abs(lateral[eval_slice, target_agent]).mean()) if len(trace) > grace else float(np.abs(lateral[:, target_agent]).mean()) if len(trace) else None,
        "target_heading_error_mean_rad": float(np.arccos(np.clip(heading_cos[eval_slice, target_agent], -1.0, 1.0)).mean()) if len(trace) > grace else float(np.arccos(np.clip(heading_cos[:, target_agent], -1.0, 1.0)).mean()) if len(trace) else None,
        "target_mean_speed": float(speed[eval_slice, target_agent].mean()) if len(trace) > grace else float(speed[:, target_agent].mean()) if len(trace) else None,
        "collision_or_contact_proxy": float(np.mean(min_pair_distance[eval_slice] < args.contact_distance)) if len(trace) > grace else float(np.mean(min_pair_distance < args.contact_distance)) if len(trace) else None,
        "min_pair_distance": float(min_pair_distance[eval_slice].min()) if len(trace) > grace else float(min_pair_distance.min()) if len(trace) else None,
        **recovery_stats,
        "compute_latency_ms": float(latency.mean()) if len(trace) else None,
        "compute_latency_p95_ms": float(np.percentile(latency, 95)) if len(trace) else None,
        "hard_recovery_step_count": int(sum(hard_recovery_flags)),
        "hard_recovery_rate": float(np.mean(hard_recovery_flags)) if hard_recovery_flags else 0.0,
        "anchor_action_deviation_mean": float(np.mean(anchor_deviations)) if anchor_deviations else None,
        "anchor_action_match_rate": float(np.mean(anchor_matches)) if anchor_matches else None,
        "topdown_gif": gif_paths.get("topdown"),
        "first_person_gif": gif_paths.get("first_person"),
        "topdown_video": video_paths.get("topdown"),
        "first_person_video": video_paths.get("first_person"),
        "first_person_render_error": render_error,
    }


def save_gif(frames, path, fps):
    if not frames:
        return None
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        path,
        save_all=True,
        append_images=frames[1:],
        duration=int(1000 / max(int(fps), 1)),
        loop=0,
        optimize=True,
    )
    return str(path)


def save_video(frames, path, fps):
    if not frames:
        return None
    if imageio is None:
        raise RuntimeError("imageio is required for MP4 export. Install imageio and imageio-ffmpeg.")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with imageio.get_writer(
        path,
        fps=max(int(fps), 1),
        codec="libx264",
        quality=8,
        macro_block_size=16,
    ) as writer:
        for frame in frames:
            writer.append_data(np.asarray(frame.convert("RGB")))
    return str(path)


def scenario_parameters(args):
    """Derive matched, reproducible scenario variation from the run seed."""
    target_agent = int(args.num_agents) - 1
    if not args.randomize_scenario:
        return {
            "scenario_randomized": False,
            "scenario_seed": int(args.seed),
            "start_order": list(range(args.num_agents)),
            "line_spacing": int(args.line_spacing),
            "lateral_spacing": float(args.lateral_spacing),
        }

    scenario_seed = int(args.seed) + int(args.scenario_seed_offset)
    rng = np.random.default_rng(scenario_seed)
    background_slots = np.arange(max(args.num_agents - 1, 0), dtype=np.int32)
    rng.shuffle(background_slots)
    start_order = background_slots.tolist() + [target_agent]
    spacing_values = [
        int(item.strip())
        for item in str(args.line_spacing_values).split(",")
        if item.strip()
    ]
    if not spacing_values:
        spacing_values = [int(args.line_spacing)]
    line_spacing = int(rng.choice(spacing_values))
    jitter = max(float(args.lateral_spacing_jitter), 0.0)
    lateral_spacing = float(args.lateral_spacing) * float(rng.uniform(1.0 - jitter, 1.0 + jitter))
    return {
        "scenario_randomized": True,
        "scenario_seed": scenario_seed,
        "start_order": start_order,
        "line_spacing": line_spacing,
        "lateral_spacing": lateral_spacing,
    }


def run_one_algorithm(args, dirs, algorithm):
    target_agent = args.num_agents - 1
    scenario = scenario_parameters(args)
    target_policy = make_policy(
        algorithm["policy"],
        seed=args.seed,
        device=args.device,
        safe=bool(algorithm.get("safe", False)),
        safe_blend=float(algorithm.get("safe_blend", args.safe_blend)),
        unsafe_blend=float(algorithm.get("unsafe_blend", args.unsafe_blend)),
        safe_base_policy=algorithm.get("safe_base_policy", args.safe_base_policy),
        neighbor_mode=algorithm.get("neighbor_mode", "dynamic"),
        max_neighbors=algorithm.get("max_neighbors", args.max_neighbors),
        neighbor_selection_mode=algorithm.get("neighbor_selection_mode", args.neighbor_selection_mode),
        planner_horizon=algorithm.get("planner_horizon"),
        planner_candidates=algorithm.get("planner_candidates"),
        planner_risk_weight=algorithm.get("planner_risk_weight"),
        planner_progress_weight=algorithm.get("planner_progress_weight"),
        planner_uncertainty_weight=algorithm.get("planner_uncertainty_weight"),
        planner_overtake_weight=algorithm.get("planner_overtake_weight"),
        planner_lane_weight=algorithm.get("planner_lane_weight"),
        planner_grass_weight=algorithm.get("planner_grass_weight"),
        planner_close_gap_weight=algorithm.get("planner_close_gap_weight"),
        overtake_aware_planner=algorithm.get("overtake_aware_planner"),
        quality_proposal_path=algorithm.get("quality_proposal_path"),
        quality_planner_mode=algorithm.get("quality_planner_mode", "proposal_only"),
        quality_rollout_blend=algorithm.get("quality_rollout_blend"),
        quality_overtake_weight=algorithm.get("quality_overtake_weight"),
        quality_lane_weight=algorithm.get("quality_lane_weight"),
        quality_grass_weight=algorithm.get("quality_grass_weight"),
        quality_close_gap_weight=algorithm.get("quality_close_gap_weight"),
        learned_quality_weight=algorithm.get("learned_quality_weight"),
        learned_quality_gate=algorithm.get("learned_quality_gate", False),
        learned_quality_min_on_track=algorithm.get("learned_quality_min_on_track", 0.45),
        learned_quality_max_grass=algorithm.get("learned_quality_max_grass", 0.55),
        learned_quality_max_lane_error=algorithm.get("learned_quality_max_lane_error", 0.72),
        learned_quality_gate_penalty=algorithm.get("learned_quality_gate_penalty", 2.0),
        elegance_barrier=algorithm.get("elegance_barrier", False),
        elegance_barrier_weight=algorithm.get("elegance_barrier_weight", 1.0),
        elegance_lateral_limit=algorithm.get("elegance_lateral_limit", 0.30),
        elegance_heading_cos_min=algorithm.get("elegance_heading_cos_min", 0.82),
        elegance_grass_penalty=algorithm.get("elegance_grass_penalty", 2.0),
        elegance_backward_penalty=algorithm.get("elegance_backward_penalty", 1.2),
        elegance_close_gap_limit=algorithm.get("elegance_close_gap_limit", 8.0),
        geometry_generalization=algorithm.get("geometry_generalization", False),
        geometry_curvature_lookahead=algorithm.get("geometry_curvature_lookahead", 8),
        geometry_curvature_speed_weight=algorithm.get("geometry_curvature_speed_weight", 18.0),
        geometry_lateral_speed_weight=algorithm.get("geometry_lateral_speed_weight", 4.5),
        geometry_heading_speed_weight=algorithm.get("geometry_heading_speed_weight", 5.0),
        geometry_min_speed=algorithm.get("geometry_min_speed", 9.5),
        geometry_anchor_blend=algorithm.get("geometry_anchor_blend", 0.35),
        geometry_barrier_weight=algorithm.get("geometry_barrier_weight", 0.65),
        hard_safety_shield=algorithm.get("hard_safety_shield"),
        use_rule_anchor=algorithm.get("use_rule_anchor", True),
        use_handcrafted_candidates=algorithm.get("use_handcrafted_candidates", True),
        use_geometry_recovery=algorithm.get("use_geometry_recovery", True),
    )
    background_policies = {
        agent_id: make_background_policy(agent_id, args.traffic_profile)
        for agent_id in range(args.num_agents)
        if agent_id != target_agent
    }
    policy = TargetOnlyPolicy(target_policy, target_agent, background_policies)
    env_max_neighbors = (
        algorithm.get("max_neighbors", args.max_neighbors)
        if args.env_max_neighbors is None
        else args.env_max_neighbors
    )
    env = make_env(
        num_agents=args.num_agents,
        seed=args.seed,
        observation_type=args.observation_type,
        start_order=scenario["start_order"],
        line_spacing=scenario["line_spacing"],
        lateral_spacing=scenario["lateral_spacing"],
        track_path=args.track_path or None,
        max_neighbors=env_max_neighbors,
    )
    if hasattr(env, "_max_episode_steps"):
        env._max_episode_steps = max(int(args.max_steps) + 1, int(env._max_episode_steps))

    stem = f"{algorithm['name']}_n{args.num_agents}_seed{args.seed}"
    topdown_frames = []
    first_person_frames = []
    render_error = None
    trace = []
    total_reward = np.zeros(args.num_agents, dtype=np.float64)
    histories = [[] for _ in range(args.num_agents)]
    first_complete_step = [None] * args.num_agents
    labels = [f"BG-{idx}" for idx in range(args.num_agents)]
    labels[target_agent] = label_for_algorithm(algorithm["name"])
    steps_run = 0

    try:
        obs = env.reset()
        policy.reset()
        lo, hi = world_bounds(env)
        track_tiles = len(env.unwrapped.track)
        for agent_id, car in enumerate(env.unwrapped.cars):
            histories[agent_id].append(np.asarray(car.hull.position, dtype=np.float32))
        want_topdown_frames = (not args.no_gif) or bool(args.video)
        want_first_person_frames = bool(args.first_person_gif) or bool(args.first_person_video)
        if want_topdown_frames:
            topdown_frames.append(draw_topdown_frame(env, histories, 0, labels, target_agent, total_reward, lo, hi, args.width, args.height))
            if want_first_person_frames:
                try:
                    fp = env.render("rgb_array")[target_agent]
                    first_person_frames.append(Image.fromarray(fp))
                except Exception as exc:
                    render_error = repr(exc)

        for step in range(args.max_steps):
            start = time.perf_counter()
            action = policy.act(env, obs)
            latency_ms = (time.perf_counter() - start) * 1000.0
            obs, reward, done, _ = env.step(action)
            steps_run = step + 1
            total_reward += reward
            tile_counts = list(map(int, env.unwrapped.tile_visited_count))
            ranks = rank_from_tiles(tile_counts)
            for agent_id, count in enumerate(tile_counts):
                if first_complete_step[agent_id] is None and count >= track_tiles:
                    first_complete_step[agent_id] = steps_run
            positions = [np.asarray(car.hull.position, dtype=np.float32) for car in env.unwrapped.cars]
            for agent_id, pos in enumerate(positions):
                histories[agent_id].append(pos)
            pair_distances = [
                float(np.linalg.norm(positions[i] - positions[j]))
                for i in range(args.num_agents)
                for j in range(i + 1, args.num_agents)
            ]
            trace.append(
                {
                    "step": int(steps_run),
                    "reward": np.asarray(reward, dtype=float).tolist(),
                    "total_reward": total_reward.tolist(),
                    "tile_visited_count": tile_counts,
                    "rank": ranks,
                    "track_index": track_indices(env),
                    "dynamic_neighbor_ids": getattr(env.unwrapped, "last_dynamic_neighbor_ids", []),
                    "target_policy_debug": getattr(target_policy, "last_decision_debug", {}),
                    "action": np.asarray(action, dtype=float).tolist(),
                    "speed": [float(np.linalg.norm(car.hull.linearVelocity)) for car in env.unwrapped.cars],
                    "compute_latency_ms": float(latency_ms),
                    "min_pair_distance": min(pair_distances) if pair_distances else None,
                    "telemetry": {
                        "progress": [float(item) for item in obs[:, 9]],
                        "lateral_error": [float(item) for item in obs[:, 12]],
                        "heading_cos": [float(item) for item in obs[:, 14]],
                        "on_grass": [bool(item > 0.5) for item in obs[:, 15]],
                        "backward": [bool(item > 0.5) for item in obs[:, 16]],
                    },
                    "positions": [pos.tolist() for pos in positions],
                    "done": bool(done),
                }
            )
            if want_topdown_frames and steps_run % args.frame_every == 0:
                topdown_frames.append(draw_topdown_frame(env, histories, steps_run, labels, target_agent, total_reward, lo, hi, args.width, args.height))
                if want_first_person_frames and render_error is None:
                    try:
                        fp = env.render("rgb_array")[target_agent]
                        first_person_frames.append(Image.fromarray(fp))
                    except Exception as exc:
                        render_error = repr(exc)
            if args.finish_mode == "any" and any(count >= track_tiles for count in tile_counts):
                break
            if args.finish_mode == "target" and tile_counts[target_agent] >= track_tiles:
                break
            if args.finish_mode == "all" and all(count >= track_tiles for count in tile_counts):
                break
            if done and args.finish_mode == "env_done":
                break
    finally:
        try:
            track_tiles = len(env.unwrapped.track)
        except Exception:
            track_tiles = 0
        env.close()

    gif_paths = {}
    if not args.no_gif:
        gif_paths["topdown"] = save_gif(topdown_frames, dirs["gifs"] / f"{stem}.topdown.gif", args.fps)
        if args.first_person_gif and render_error is None:
            gif_paths["first_person"] = save_gif(first_person_frames, dirs["gifs"] / f"{stem}.first_person.gif", args.fps)
        else:
            gif_paths["first_person"] = None
    video_paths = {}
    if args.video:
        video_paths["topdown"] = save_video(topdown_frames, dirs["gifs"] / f"{stem}.topdown.mp4", args.fps)
    if args.first_person_video and render_error is None:
        video_paths["first_person"] = save_video(first_person_frames, dirs["gifs"] / f"{stem}.first_person.mp4", args.fps)
    elif args.first_person_video:
        video_paths["first_person"] = None

    summary = summarize_trace(
        trace,
        args,
        algorithm,
        target_agent,
        track_tiles,
        total_reward,
        steps_run,
        first_complete_step,
        gif_paths,
        video_paths,
        render_error,
    )
    summary.update(scenario)
    summary["policy_max_neighbors"] = algorithm.get("max_neighbors", args.max_neighbors)
    summary["env_max_neighbors"] = env_max_neighbors
    summary_path = dirs["summaries"] / f"{stem}.summary.json"
    trace_path = dirs["traces"] / f"{stem}.trace.json"
    summary["summary_path"] = str(summary_path)
    summary["trace_path"] = str(trace_path)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    trace_path.write_text(json.dumps(trace, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def register_cjk_font():
    import matplotlib as mpl
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


def write_source_table(summaries, path):
    fields = [
        "algorithm",
        "algorithm_label_cn",
        "neighbor_selection_mode",
        "planner_horizon",
        "planner_candidates",
        "planner_risk_weight",
        "planner_progress_weight",
        "planner_uncertainty_weight",
        "overtake_aware_planner",
        "elegance_barrier",
        "elegance_barrier_weight",
        "elegance_lateral_limit",
        "elegance_heading_cos_min",
        "elegance_grass_penalty",
        "elegance_backward_penalty",
        "elegance_close_gap_limit",
        "geometry_generalization",
        "geometry_curvature_lookahead",
        "geometry_curvature_speed_weight",
        "geometry_lateral_speed_weight",
        "geometry_heading_speed_weight",
        "geometry_min_speed",
        "geometry_anchor_blend",
        "geometry_barrier_weight",
        "quality_planner_mode",
        "quality_rollout_blend",
        "quality_overtake_weight",
        "quality_lane_weight",
        "quality_grass_weight",
        "quality_close_gap_weight",
        "seed",
        "num_agents",
        "track_path",
        "rank_gain",
        "target_final_rank",
        "target_progress",
        "target_completed_lap",
        "overtake_success",
        "overtake_count",
        "on_track_overtake_count",
        "on_track_overtake_rate",
        "elegant_overtake_count",
        "elegant_overtake_rate",
        "time_to_first_overtake",
        "overtake_start_to_complete_time",
        "overtake_window_grass_rate_mean",
        "overtake_window_max_abs_lateral_mean",
        "target_grass_rate",
        "target_mean_abs_lateral",
        "target_heading_error_mean_rad",
        "grass_recovery_time_mean",
        "grass_recovery_time_max",
        "grass_excursion_count",
        "unrecovered_grass_excursion_count",
        "target_mean_speed",
        "collision_or_contact_proxy",
        "compute_latency_ms",
        "compute_latency_p95_ms",
        "finish_step",
        "topdown_gif",
        "first_person_gif",
        "topdown_video",
        "first_person_video",
    ]
    path = Path(path)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in summaries:
            writer.writerow({field: row.get(field) for field in fields})
    return str(path)


def aggregate_for_plot(summaries):
    grouped = {}
    for row in summaries:
        key = (row["algorithm"], row.get("algorithm_label_cn", row["algorithm"]))
        grouped.setdefault(key, []).append(row)
    rows = []
    for (name, label), items in grouped.items():
        def mean_metric(metric):
            values = [item.get(metric) for item in items if item.get(metric) is not None]
            return float(np.mean(values)) if values else np.nan
        rows.append(
            {
                "algorithm": name,
                "label": label,
                "n": len(items),
                "overtake_success_rate": mean_metric("overtake_success_rate"),
                "on_track_overtake_rate": mean_metric("on_track_overtake_rate"),
                "elegant_overtake_rate": mean_metric("elegant_overtake_rate"),
                "rank_gain": mean_metric("rank_gain"),
                "overtake_duration": mean_metric("overtake_start_to_complete_time"),
                "grass_rate": mean_metric("target_grass_rate"),
                "recovery_time": mean_metric("grass_recovery_time_mean"),
                "lateral": mean_metric("target_mean_abs_lateral"),
                "latency": mean_metric("compute_latency_ms"),
                "progress": mean_metric("target_progress"),
            }
        )
    preferred = {item["name"]: idx for idx, item in enumerate(DEFAULT_ALGORITHMS)}
    rows.sort(key=lambda item: preferred.get(item["algorithm"], 999))
    return rows


def plot_chinese_summary(summaries, out_dir):
    import matplotlib as mpl
    import matplotlib.pyplot as plt

    register_cjk_font()
    mpl.rcParams.update(
        {
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "font.size": 8,
            "axes.spines.right": False,
            "axes.spines.top": False,
            "axes.unicode_minus": False,
            "legend.frameon": False,
        }
    )
    rows = aggregate_for_plot(summaries)
    if not rows:
        return {}

    labels = [row["label"] for row in rows]
    x = np.arange(len(rows))
    colors = ["#2F6BBD", "#55A868", "#C44E52", "#8172B2", "#CCB974", "#64B5CD", "#4C566A", "#8FBC8F"][: len(rows)]

    fig = plt.figure(figsize=(10.2, 6.6), constrained_layout=True)
    gs = fig.add_gridspec(2, 3)
    axes = [
        fig.add_subplot(gs[0, 0]),
        fig.add_subplot(gs[0, 1]),
        fig.add_subplot(gs[0, 2]),
        fig.add_subplot(gs[1, 0]),
        fig.add_subplot(gs[1, 1]),
        fig.add_subplot(gs[1, 2]),
    ]
    metrics = [
        ("overtake_success_rate", "a  超车成功率", "成功率"),
        ("on_track_overtake_rate", "b  赛道内超车率", "比例"),
        ("elegant_overtake_rate", "c  Desirable overtaking behavior rate", "比例"),
        ("overtake_duration", "d  超车开始到完成时间", "环境步数"),
        ("grass_rate", "e  目标车草地率", "比例"),
        ("recovery_time", "f  草地后恢复时间", "环境步数"),
    ]
    for ax, (metric, title, ylabel) in zip(axes, metrics):
        values = [row[metric] for row in rows]
        clean = [0.0 if (isinstance(v, float) and np.isnan(v)) else v for v in values]
        bars = ax.bar(x, clean, color=colors, width=0.68)
        ax.set_title(title)
        ax.set_ylabel(ylabel)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=28, ha="right")
        ax.grid(axis="y", color="#D9E1E8", lw=0.6)
        for rect, value in zip(bars, values):
            text = "NA" if isinstance(value, float) and np.isnan(value) else f"{value:.2f}"
            ax.text(rect.get_x() + rect.get_width() / 2, rect.get_height(), text, ha="center", va="bottom", fontsize=6.5)
    fig.suptitle("动态图DLC世界模型在线超车评估：中文指标汇总", fontsize=12, fontweight="bold")

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = out_dir / "figure_tits_dynamic_graph_online_overtake_summary"
    outputs = {}
    for ext in ["svg", "pdf", "png", "tiff"]:
        path = stem.with_suffix(f".{ext}")
        fig.savefig(path, dpi=600, bbox_inches="tight")
        outputs[ext] = str(path)
    plt.close(fig)
    manifest = {
        "claim": "所有算法在同一在线多车超车任务中评估；核心指标聚焦超车成功率、on-track/desirable超车率、超车耗时、草地率和草地后恢复时间。",
        "outputs": outputs,
    }
    stem.with_suffix(".manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return outputs


def algorithm_records_from_config(config):
    if not config or "algorithms" not in config:
        return []
    dynamic_graph = config.get("dynamic_graph", {})
    default_max_neighbors = dynamic_graph.get("max_neighbors", 3)
    records = []
    for item in config.get("algorithms", []):
        policy = item.get("policy") or item.get("model_path")
        if not policy:
            continue
        is_rule_policy = str(policy).startswith("telemetry_")
        record = {
            "name": item["name"],
            "label_cn": item.get("label_cn", item["name"]),
            "policy": policy,
            "neighbor_mode": item.get("neighbor_mode", "fixed" if is_rule_policy else "dynamic"),
            "max_neighbors": item.get("max_neighbors", None if is_rule_policy else default_max_neighbors),
            "neighbor_selection_mode": item.get("neighbor_selection_mode", dynamic_graph.get("neighbor_selection_mode", "legacy")),
            "kind": item.get("kind", ""),
        }
        for key in [
            "overtake_aware_planner",
            "planner_horizon",
            "planner_candidates",
            "planner_risk_weight",
            "planner_progress_weight",
            "planner_uncertainty_weight",
            "planner_overtake_weight",
            "planner_lane_weight",
            "planner_grass_weight",
            "planner_close_gap_weight",
            "quality_proposal_path",
            "quality_planner_mode",
            "quality_rollout_blend",
            "quality_overtake_weight",
            "quality_lane_weight",
            "quality_grass_weight",
            "quality_close_gap_weight",
            "learned_quality_weight",
            "learned_quality_gate",
            "learned_quality_min_on_track",
            "learned_quality_max_grass",
            "learned_quality_max_lane_error",
            "learned_quality_gate_penalty",
            "elegance_barrier",
            "elegance_barrier_weight",
            "elegance_lateral_limit",
            "elegance_heading_cos_min",
            "elegance_grass_penalty",
            "elegance_backward_penalty",
            "elegance_close_gap_limit",
            "geometry_generalization",
            "geometry_curvature_lookahead",
            "geometry_curvature_speed_weight",
            "geometry_lateral_speed_weight",
            "geometry_heading_speed_weight",
            "geometry_min_speed",
            "geometry_anchor_blend",
            "geometry_barrier_weight",
            "hard_safety_shield",
            "use_rule_anchor",
            "use_handcrafted_candidates",
            "use_geometry_recovery",
            "safe",
            "safe_blend",
            "unsafe_blend",
            "safe_base_policy",
        ]:
            if key in item:
                record[key] = item[key]
        records.append(record)
    return records


def selected_algorithms(names, config=None):
    available = algorithm_records_from_config(config)
    if not available:
        available = DEFAULT_ALGORITHMS
    if not names:
        return available
    wanted = {item.strip() for item in names.split(",") if item.strip()}
    algorithms = [item for item in available if item["name"] in wanted]
    missing = wanted - {item["name"] for item in algorithms}
    if missing:
        raise ValueError(f"unknown algorithms: {sorted(missing)}")
    return algorithms


def main():
    parser = argparse.ArgumentParser(description="Run online TITS-style dynamic graph DLC world-model overtake evaluation.")
    parser.add_argument("--config", default="configs/tits_dynamic_graph_experiments.json")
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/online_evaluation")
    parser.add_argument("--algorithms", default="", help="Comma-separated algorithm names. Empty means all defaults.")
    parser.add_argument("--num-agents", type=int, default=4)
    parser.add_argument("--seed", type=int, default=3)
    parser.add_argument("--max-steps", type=int, default=2200)
    parser.add_argument("--finish-mode", choices=["any", "target", "all", "env_done", "steps"], default="any")
    parser.add_argument("--observation-type", choices=["telemetry", "telemetry_dynamic"], default="telemetry_dynamic")
    parser.add_argument("--max-neighbors", type=int, default=3)
    parser.add_argument("--env-max-neighbors", type=int, default=None, help="Environment-side neighbor budget. Use 0 to expose all vehicles and let each policy perform its own packing.")
    parser.add_argument("--neighbor-selection-mode", default="legacy", choices=["legacy", "interaction", "traffic", "dynamic_interaction", "nearest", "distance", "front", "ahead", "fixed", "identity"])
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--track-path", default="")
    parser.add_argument("--traffic-profile", choices=["slow_traffic", "mixed_traffic"], default="slow_traffic")
    parser.add_argument("--line-spacing", type=int, default=5)
    parser.add_argument("--lateral-spacing", type=float, default=2.2)
    parser.add_argument("--randomize-scenario", action="store_true", help="Use the seed to vary background grid slots and start spacing while keeping the target last.")
    parser.add_argument("--scenario-seed-offset", type=int, default=0)
    parser.add_argument("--line-spacing-values", default="4,5,6", help="Comma-separated integer track-tile spacings used by randomized scenarios.")
    parser.add_argument("--lateral-spacing-jitter", type=float, default=0.35, help="Relative uniform jitter applied to lateral spacing in randomized scenarios.")
    parser.add_argument("--safe-blend", type=float, default=0.25)
    parser.add_argument("--unsafe-blend", type=float, default=1.0)
    parser.add_argument("--safe-base-policy", default="telemetry_expert_barrier")
    parser.add_argument("--contact-distance", type=float, default=2.0)
    parser.add_argument("--no-gif", action="store_true")
    parser.add_argument("--first-person-gif", action="store_true")
    parser.add_argument("--video", action="store_true", help="Save top-down MP4 video.")
    parser.add_argument("--first-person-video", action="store_true", help="Save target-agent first-person MP4 video.")
    parser.add_argument("--frame-every", type=int, default=8)
    parser.add_argument("--fps", type=int, default=12)
    parser.add_argument("--width", type=int, default=900)
    parser.add_argument("--height", type=int, default=900)
    args = parser.parse_args()

    config = load_config(args.config)
    if config and args.out_dir == parser.get_default("out_dir"):
        args.out_dir = str(Path(config.get("reporting", {}).get("output_dir", "outputs/tits_dynamic_graph")) / "online_evaluation")
    dirs = ensure_dirs(args.out_dir)
    algorithms = selected_algorithms(args.algorithms, config)

    summaries = []
    for algorithm in algorithms:
        policy_path = Path(algorithm["policy"])
        if not policy_path.exists() and not str(algorithm["policy"]).startswith("telemetry_"):
            print(f"skip missing model: {algorithm['name']} -> {algorithm['policy']}")
            continue
        print(f"running {algorithm['name']} seed={args.seed} n={args.num_agents}")
        summaries.append(run_one_algorithm(args, dirs, algorithm))

    source_csv = write_source_table(summaries, dirs["tables"] / f"online_metrics_n{args.num_agents}_seed{args.seed}.csv")
    figure_outputs = plot_chinese_summary(summaries, dirs["figures"])
    suite_summary = {
        "config": args.config,
        "args": vars(args),
        "source_csv": source_csv,
        "figure_outputs": figure_outputs,
        "summaries": summaries,
    }
    suite_path = dirs["root"] / f"online_suite_n{args.num_agents}_seed{args.seed}.json"
    suite_path.write_text(json.dumps(suite_summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"suite": str(suite_path), "source_csv": source_csv, "figures": figure_outputs}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
