#!/usr/bin/env python
import argparse
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from dlc.policies import (
    OvertakeTrackPolicy,
    TelemetryAdaptiveGatePolicy,
    TelemetryConservativeAdaptivePolicy,
    TelemetryCruisePolicy,
    TelemetryBarrierExpertGatePolicy,
    TelemetryRecoveryExpertGatePolicy,
    TelemetryLanePolicy,
    TelemetryExpertGatePolicy,
    TelemetryFastExpertGatePolicy,
    TelemetryOvertakePolicy,
    TelemetryRecoveryAdaptivePolicy,
    TelemetryYieldPolicy,
    TrackFollowPolicy,
    make_policy,
)
from dlc.rollout import make_env


PLAYFIELD = 2000 / 6.0
TRACK_WIDTH = 40 / 6.0


MODEL_NAMES = {
    "individual_transition",
    "joint_transition",
    "joint_transition_observer",
}


def wrap_to_pi(angle):
    return (angle + math.pi) % (2 * math.pi) - math.pi


COLORS = [(220, 50, 47), (38, 139, 210), (133, 153, 0), (203, 75, 22), (108, 113, 196), (42, 161, 152)]


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


def draw_frame(env, histories, step, total_reward, labels, lo, hi, width, height):
    image = Image.new("RGB", (width, height), (36, 113, 61))
    draw = ImageDraw.Draw(image)

    for vertices, color in env.unwrapped.road_poly:
        rgb = tuple(int(np.clip(c, 0.0, 1.0) * 255) for c in color)
        draw.polygon(transform_points(vertices, lo, hi, width, height), fill=rgb)

    for agent_id, history in enumerate(histories):
        if len(history) > 1:
            draw.line(
                transform_points(history, lo, hi, width, height),
                fill=COLORS[agent_id % len(COLORS)],
                width=3,
            )

    positions = [np.asarray(car.hull.position, dtype=np.float32) for car in env.unwrapped.cars]
    for agent_id, pos in enumerate(positions):
        x, y = transform_points([pos], lo, hi, width, height)[0]
        r = 5
        color = COLORS[agent_id % len(COLORS)]
        draw.ellipse([x - r, y - r, x + r, y + r], fill=color, outline=(255, 255, 255))
        draw.text((x + 7, y - 7), f"A{agent_id}", fill=(255, 255, 255))

    tiles = env.unwrapped.tile_visited_count
    lines = [f"step {step}"]
    for agent_id, label in enumerate(labels):
        lines.append(f"A{agent_id} {label} tiles {tiles[agent_id]} reward {total_reward[agent_id]:.1f}")
    x, y = 10, 10
    box_w = max(draw.textlength(line) for line in lines) + 16
    box_h = 18 * len(lines) + 10
    draw.rectangle([x - 5, y - 5, x + box_w, y + box_h], fill=(0, 0, 0))
    for idx, line in enumerate(lines):
        draw.text((x, y + 18 * idx), line, fill=(255, 255, 255))
    return image


def make_model_policy(
    model_dir,
    name,
    seed,
    device,
    safe,
    safe_blend,
    unsafe_blend,
    safe_base_policy,
    policy_path="",
    neighbor_mode="fixed",
    max_neighbors=None,
):
    if policy_path:
        return make_policy(
            policy_path,
            seed=seed,
            device=device,
            safe=safe,
            safe_blend=safe_blend,
            unsafe_blend=unsafe_blend,
            safe_base_policy=safe_base_policy,
            neighbor_mode=neighbor_mode,
            max_neighbors=max_neighbors,
        )
    if name not in MODEL_NAMES:
        raise ValueError(f"unknown model policy: {name}")
    return make_policy(
        str(Path(model_dir) / f"{name}.pt"),
        seed=seed,
        device=device,
        safe=safe,
        safe_blend=safe_blend,
        unsafe_blend=unsafe_blend,
        safe_base_policy=safe_base_policy,
        neighbor_mode=neighbor_mode,
        max_neighbors=max_neighbors,
    )


def nearest_track_index(env, position):
    track_xy = np.asarray(env.unwrapped.track, dtype=np.float32)[:, 2:]
    return int(np.argmin(np.linalg.norm(np.asarray(position, dtype=np.float32).reshape(1, 2) - track_xy, axis=1)))


def local_pair_obs(env, obs, target_agent, reference_agent):
    local = np.zeros((2, obs.shape[1]), dtype=np.float32)
    local = local[:, :24]
    local[0, :17] = obs[target_agent, :17]
    local[1, :17] = obs[reference_agent, :17]

    def rel_features(ego_agent, other_agent):
        ego_car = env.unwrapped.cars[ego_agent]
        other_car = env.unwrapped.cars[other_agent]
        ego_pos = np.asarray(ego_car.hull.position, dtype=np.float32)
        other_pos = np.asarray(other_car.hull.position, dtype=np.float32)
        ego_vel = np.asarray(ego_car.hull.linearVelocity, dtype=np.float32)
        other_vel = np.asarray(other_car.hull.linearVelocity, dtype=np.float32)
        heading = float(ego_car.hull.angle)
        heading_vec = np.array([math.cos(heading), math.sin(heading)], dtype=np.float32)
        left_vec = np.array([-math.sin(heading), math.cos(heading)], dtype=np.float32)
        rel_pos = other_pos - ego_pos
        rel_vel = other_vel - ego_vel
        rel_heading = wrap_to_pi(float(other_car.hull.angle) - heading)
        return np.asarray(
            [
                float(np.dot(rel_pos, heading_vec) / PLAYFIELD),
                float(np.dot(rel_pos, left_vec) / PLAYFIELD),
                rel_vel[0] / 50.0,
                rel_vel[1] / 50.0,
                float(np.linalg.norm(rel_pos) / PLAYFIELD),
                math.sin(rel_heading),
                math.cos(rel_heading),
            ],
            dtype=np.float32,
        )

    local[0, 17:] = rel_features(target_agent, reference_agent)
    local[1, 17:] = rel_features(reference_agent, target_agent)
    return local


def choose_reference_ahead(env, obs, target_agent):
    base_env = env.unwrapped
    target_pos = np.asarray(base_env.cars[target_agent].hull.position, dtype=np.float32)
    target_index = nearest_track_index(env, target_pos)
    best_agent = 0 if target_agent != 0 else 1
    best_delta = float("inf")
    track_len = len(base_env.track)
    for agent_id, car in enumerate(base_env.cars):
        if agent_id == target_agent:
            continue
        idx = nearest_track_index(env, car.hull.position)
        delta = (idx - target_index) % track_len
        if delta == 0:
            delta = abs(float(obs[target_agent, 17])) * track_len
        if 0 <= delta < best_delta:
            best_delta = delta
            best_agent = agent_id
    return best_agent


class TargetLocalModelPolicy:
    def __init__(
        self,
        model_policy,
        target_agent,
        base_policy,
        safe=False,
        safe_blend=0.55,
        unsafe_blend=0.95,
        lateral_threshold=1.2,
        heading_cos_threshold=0.1,
        hard_shield=True,
        emergency_lateral_threshold=0.78,
        stall_patience=160,
        stall_progress_epsilon=0.002,
        stall_min_speed=4.0,
        close_forward_gap=0.025,
        close_lateral_gap=0.025,
    ):
        self.model_policy = model_policy
        self.target_agent = int(target_agent)
        self.base_policy = base_policy
        self.safe = bool(safe)
        self.safe_blend = float(safe_blend)
        self.unsafe_blend = float(unsafe_blend)
        self.lateral_threshold = float(lateral_threshold)
        self.heading_cos_threshold = float(heading_cos_threshold)
        self.hard_shield = bool(hard_shield)
        self.emergency_lateral_threshold = float(emergency_lateral_threshold)
        self.stall_patience = int(stall_patience)
        self.stall_progress_epsilon = float(stall_progress_epsilon)
        self.stall_min_speed = float(stall_min_speed)
        self.close_forward_gap = float(close_forward_gap)
        self.close_lateral_gap = float(close_lateral_gap)
        self.last_progress = None
        self.stall_steps = 0
        self.name = f"local_{model_policy.name}"

    def reset(self):
        self.model_policy.reset()
        self.base_policy.reset()
        self.last_progress = None
        self.stall_steps = 0
        if hasattr(self.model_policy, "set_controlled_agent"):
            self.model_policy.set_controlled_agent(0)

    def _update_stall_state(self, target_obs):
        progress = float(target_obs[9])
        speed = float(target_obs[4]) * 50.0
        if self.last_progress is None:
            self.last_progress = progress
            self.stall_steps = 0
            return False
        if progress > self.last_progress + self.stall_progress_epsilon:
            self.stall_steps = 0
            self.last_progress = max(self.last_progress, progress)
        elif speed < self.stall_min_speed:
            self.stall_steps += 1
        else:
            self.stall_steps = max(self.stall_steps - 1, 0)
        return self.stall_steps >= self.stall_patience

    def _close_ahead(self, target_obs):
        for start in range(17, len(target_obs), 7):
            rel_forward = float(target_obs[start])
            rel_left = float(target_obs[start + 1])
            if 0.0 < rel_forward < self.close_forward_gap and abs(rel_left) < self.close_lateral_gap:
                return True
        return False

    def _project_action(self, target_obs, action, base_action, stall=False, close_ahead=False):
        projected = np.asarray(action, dtype=np.float32).copy()
        lateral = float(target_obs[12])
        heading_error = math.atan2(float(target_obs[13]), float(target_obs[14]))
        heading_cos = float(target_obs[14])
        on_grass = float(target_obs[15]) > 0.5
        backward = float(target_obs[16]) > 0.5
        emergency = abs(lateral) > self.emergency_lateral_threshold or on_grass or backward
        corrective_steer = -np.clip(1.7 * heading_error + 0.85 * lateral, -1.0, 1.0)

        if abs(lateral) > self.lateral_threshold or heading_cos < self.heading_cos_threshold:
            if abs(corrective_steer) > abs(projected[0]) or np.sign(corrective_steer) != np.sign(projected[0]):
                projected[0] = corrective_steer

        if emergency:
            projected = np.asarray(base_action, dtype=np.float32).copy()
            projected[0] = corrective_steer
            if backward or heading_cos < 0.25:
                projected[1] = min(float(projected[1]), 0.12)
                projected[2] = max(float(projected[2]), 0.45)
            else:
                projected[1] = max(float(projected[1]), 0.45)
                projected[2] = min(float(projected[2]), 0.05)

        if heading_cos < 0.25 or backward:
            projected[1] = min(float(projected[1]), 0.12)
            projected[2] = max(float(projected[2]), 0.45)

        if close_ahead:
            projected[1] = min(float(projected[1]), 0.12)
            projected[2] = max(float(projected[2]), 0.35)

        if stall:
            projected = np.asarray(base_action, dtype=np.float32).copy()
            projected[0] = corrective_steer if abs(lateral) > 0.25 else projected[0]
            projected[1] = max(float(projected[1]), 0.55)
            projected[2] = min(float(projected[2]), 0.05)

        projected[0] = np.clip(projected[0], -1.0, 1.0)
        projected[1:] = np.clip(projected[1:], 0.0, 1.0)
        return projected

    def act_one(self, env, obs):
        reference_agent = choose_reference_ahead(env, obs, self.target_agent)
        if obs.shape[1] != 24 and not getattr(self.model_policy, "name", "").startswith(("individual", "joint")):
            learned = self.model_policy.act(env, obs)[self.target_agent]
        else:
            pair_obs = local_pair_obs(env, obs, self.target_agent, reference_agent)
            pair_action = self.model_policy.act(env, pair_obs)
            learned = pair_action[0]
        if not self.safe:
            return learned, reference_agent

        base_action = self.base_policy.act(env, obs)[self.target_agent]
        target_obs = np.asarray(obs[self.target_agent], dtype=np.float32)
        stall = self._update_stall_state(target_obs)
        close_ahead = self._close_ahead(target_obs) if self.hard_shield else False
        unsafe = (
            abs(float(target_obs[12])) > self.lateral_threshold
            or float(target_obs[14]) < self.heading_cos_threshold
            or float(target_obs[15]) > 0.5
            or float(target_obs[16]) > 0.5
            or (self.hard_shield and close_ahead)
        )
        blend = self.unsafe_blend if unsafe else self.safe_blend
        action = blend * base_action + (1.0 - blend) * learned
        if self.hard_shield and (unsafe or stall):
            action = self._project_action(target_obs, action, base_action, stall=stall, close_ahead=close_ahead)
        action[0] = np.clip(action[0], -1.0, 1.0)
        action[1:] = np.clip(action[1:], 0.0, 1.0)
        return action.astype(np.float32), reference_agent


class StableLanePolicy:
    def __init__(
        self,
        target_speed=13.5,
        lookahead=7,
        lane_offset=0.0,
        lateral_gain=1.15,
        heading_gain=1.55,
        name="stable_lane",
    ):
        self.target_speed = float(target_speed)
        self.lookahead = int(lookahead)
        self.lane_offset = float(lane_offset)
        self.lateral_gain = float(lateral_gain)
        self.heading_gain = float(heading_gain)
        self.name = name

    def reset(self):
        pass

    def act(self, env, obs):
        del obs
        base_env = env.unwrapped
        action = np.zeros((base_env.num_agents, 3), dtype=np.float32)
        track = np.asarray(base_env.track, dtype=np.float32)
        track_xy = track[:, 2:]

        for agent_id, car in enumerate(base_env.cars):
            car_pos = np.asarray(car.hull.position, dtype=np.float32)
            track_index = int(np.argmin(np.linalg.norm(car_pos.reshape(1, 2) - track_xy, axis=1)))
            target_index = (track_index + self.lookahead) % len(base_env.track)
            desired_angle = float(base_env.track[target_index][1])
            local_angle = float(base_env.track[track_index][1])
            if base_env.episode_direction == "CW":
                desired_angle += math.pi
                local_angle += math.pi

            center = np.asarray(base_env.track[track_index][2:], dtype=np.float32)
            normal = np.asarray([-math.sin(local_angle), math.cos(local_angle)], dtype=np.float32)
            lateral_error = float(np.dot(car_pos - center, normal))
            corrected_angle = desired_angle - self.lateral_gain * (lateral_error - self.lane_offset) / TRACK_WIDTH
            velocity = np.asarray(car.hull.linearVelocity, dtype=np.float32)
            heading = float(car.hull.angle)
            if np.linalg.norm(velocity) > 0.5:
                heading = -math.atan2(float(velocity[0]), float(velocity[1]))
            angle_error = wrap_to_pi(corrected_angle - heading)
            speed = float(np.linalg.norm(car.hull.linearVelocity))
            corner_slowdown = min(abs(angle_error) * 10.0, 7.0)
            lateral_slowdown = min(abs(lateral_error - self.lane_offset) / 3.0, 6.0)
            target_speed = max(8.5, self.target_speed - corner_slowdown - lateral_slowdown)

            action[agent_id, 0] = np.clip(-self.heading_gain * angle_error, -1.0, 1.0)
            action[agent_id, 1] = 0.42 if speed < target_speed else 0.04
            action[agent_id, 2] = 0.0 if speed < target_speed + 2.0 else 0.55
        return action


def make_background_policy(name, agent_id):
    if name == "telemetry_lane":
        speeds = [14.0, 15.5, 17.0, 18.0]
        return TelemetryLanePolicy(
            target_speed=speeds[agent_id % len(speeds)],
            lane_offset=0.0,
            name=f"telemetry_lane_{agent_id}",
        )
    if name == "telemetry_cruise":
        speeds = [13.0, 14.5, 16.0, 17.0]
        return TelemetryCruisePolicy(
            target_speed=speeds[agent_id % len(speeds)],
            lane_offset=0.0,
            name=f"telemetry_cruise_{agent_id}",
        )
    if name == "telemetry_yield":
        speeds = [14.0, 15.0, 16.0, 17.0]
        return TelemetryYieldPolicy(
            target_speed=speeds[agent_id % len(speeds)],
            lane_offset=0.0,
            yield_speed=10.5,
            name=f"telemetry_yield_{agent_id}",
        )
    if name == "telemetry_overtake":
        speeds = [14.0, 15.0, 16.0, 17.0]
        speed = speeds[agent_id % len(speeds)]
        return TelemetryOvertakePolicy(
            target_speed=speed,
            pass_speed=speed + 3.0,
            lane_offset=0.0,
            pass_lane_offset=1.0,
            name=f"telemetry_overtake_{agent_id}",
        )
    if name == "telemetry_adaptive":
        speeds = [14.0, 15.0, 16.0, 17.0]
        speed = speeds[agent_id % len(speeds)]
        return TelemetryAdaptiveGatePolicy(
            target_speed=speed,
            pass_speed=speed + 3.0,
            lane_offset=0.0,
            pass_lane_offset=1.0,
            name=f"telemetry_adaptive_{agent_id}",
        )
    if name == "telemetry_adaptive_conservative":
        speeds = [12.5, 13.5, 14.5, 15.5]
        speed = speeds[agent_id % len(speeds)]
        return TelemetryConservativeAdaptivePolicy(
            target_speed=speed,
            pass_speed=speed + 2.0,
            lane_offset=0.0,
            name=f"telemetry_adaptive_conservative_{agent_id}",
        )
    if name == "telemetry_expert_gate":
        return TelemetryExpertGatePolicy(name=f"telemetry_expert_gate_{agent_id}")
    if name == "telemetry_expert_fast":
        return TelemetryFastExpertGatePolicy(name=f"telemetry_expert_fast_{agent_id}")
    if name == "telemetry_expert_barrier":
        return TelemetryBarrierExpertGatePolicy(name=f"telemetry_expert_barrier_{agent_id}")
    if name == "telemetry_expert_recovery":
        return TelemetryRecoveryExpertGatePolicy(name=f"telemetry_expert_recovery_{agent_id}")
    if name == "track_follow":
        return TrackFollowPolicy(target_speed=12.0 + agent_id, name=f"track_follow_{agent_id}")
    if name == "overtake_track":
        return OvertakeTrackPolicy(
            target_speed=13.0 + agent_id,
            pass_speed=15.0 + agent_id,
            lane_offset=2.0,
            name=f"overtake_track_{agent_id}",
        )
    raise ValueError(f"unknown baseline policy: {name}")


def make_background_policies(num_agents, target_agent, baseline_policies):
    policies = []
    names = [name.strip() for name in baseline_policies.split(",") if name.strip()]
    if not names:
        raise ValueError("--baseline-policies must contain at least one policy name")
    for agent_id in range(num_agents):
        if agent_id == target_agent:
            policies.append(None)
        else:
            policies.append(make_background_policy(names[agent_id % len(names)], agent_id))
    return policies


def run(args):
    target_agent = args.num_agents - 1
    if args.single_file_start:
        start_order = [2 * agent_id for agent_id in range(args.num_agents)]
    else:
        target_slot = 2 * math.ceil((args.num_agents - 1) / 2)
        start_order = [agent_id for agent_id in range(args.num_agents - 1)] + [target_slot]
    env = make_env(
        num_agents=args.num_agents,
        seed=args.seed,
        observation_type="telemetry",
        start_order=start_order,
        line_spacing=args.gap_tiles,
        lateral_spacing=args.lateral_spacing,
        track_path=args.track_path or None,
    )
    if hasattr(env, "_max_episode_steps"):
        env._max_episode_steps = max(int(args.steps) + 1, int(env._max_episode_steps))
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    model_policy = make_model_policy(
        args.model_dir,
        args.target_policy,
        args.seed + 50_000,
        args.device,
        False,
        args.safe_blend,
        args.unsafe_blend,
        args.target_safe_base,
        args.target_policy_path,
        neighbor_mode=args.neighbor_mode,
        max_neighbors=args.max_neighbors,
    )
    target_base_policy = (
        StableLanePolicy(target_speed=args.target_base_speed, lane_offset=0.0, name="stable_target")
        if args.target_safe_base == "stable_lane"
        else TelemetryLanePolicy(target_speed=args.target_base_speed, lane_offset=0.0, name="telemetry_target")
        if args.target_safe_base == "telemetry_lane"
        else TelemetryOvertakePolicy(
            target_speed=args.target_base_speed,
            pass_speed=args.target_base_speed + 4.0,
            name="telemetry_target_overtake",
        )
        if args.target_safe_base == "telemetry_overtake"
        else TelemetryAdaptiveGatePolicy(
            target_speed=args.target_base_speed,
            pass_speed=args.target_base_speed + 4.0,
            name="telemetry_target_adaptive",
        )
        if args.target_safe_base == "telemetry_adaptive"
        else TelemetryRecoveryAdaptivePolicy(
            target_speed=args.target_base_speed,
            pass_speed=args.target_base_speed + 3.0,
            name="telemetry_target_recovery_adaptive",
        )
        if args.target_safe_base == "telemetry_adaptive_recovery"
        else TelemetryConservativeAdaptivePolicy(
            target_speed=args.target_base_speed,
            pass_speed=args.target_base_speed + 2.0,
            name="telemetry_target_conservative_adaptive",
        )
        if args.target_safe_base == "telemetry_adaptive_conservative"
        else TelemetryExpertGatePolicy(name="telemetry_target_expert_gate")
        if args.target_safe_base == "telemetry_expert_gate"
        else TelemetryFastExpertGatePolicy(name="telemetry_target_expert_fast")
        if args.target_safe_base == "telemetry_expert_fast"
        else TelemetryBarrierExpertGatePolicy(name="telemetry_target_expert_barrier")
        if args.target_safe_base == "telemetry_expert_barrier"
        else TelemetryRecoveryExpertGatePolicy(name="telemetry_target_expert_recovery")
        if args.target_safe_base == "telemetry_expert_recovery"
        else OvertakeTrackPolicy(target_speed=args.target_base_speed, pass_speed=args.target_base_speed + 4.0)
        if args.target_safe_base == "overtake_track"
        else TrackFollowPolicy()
    )
    target_policy = TargetLocalModelPolicy(
        model_policy,
        target_agent,
        target_base_policy,
        safe=args.safe,
        safe_blend=args.safe_blend,
        unsafe_blend=args.unsafe_blend,
        hard_shield=not args.disable_hard_shield,
        emergency_lateral_threshold=args.emergency_lateral_threshold,
        stall_patience=args.stall_patience,
    )
    background_policies = make_background_policies(args.num_agents, target_agent, args.baseline_policies)

    total_reward = np.zeros(args.num_agents, dtype=np.float64)
    grass_steps = np.zeros(args.num_agents, dtype=np.float64)
    histories = [[] for _ in range(args.num_agents)]
    frames = []
    trace = []
    first_ahead_step = None
    target_complete_step = None
    target_references = []

    try:
        obs = env.reset()
        target_policy.reset()
        for policy in background_policies:
            if policy is not None:
                policy.reset()
        lo, hi = world_bounds(env) if not args.no_gif else (None, None)

        for agent_id, car in enumerate(env.unwrapped.cars):
            histories[agent_id].append(np.asarray(car.hull.position, dtype=np.float32))
        target_label = Path(args.target_policy_path).stem if args.target_policy_path else args.target_policy
        labels = [
            f"A{agent_id}:{'target_' + target_label if agent_id == target_agent else background_policies[agent_id].name}"
            for agent_id in range(args.num_agents)
        ]
        if not args.no_gif:
            frames.append(draw_frame(env, histories, 0, total_reward, labels, lo, hi, args.width, args.height))

        steps_run = 0
        done = False
        for step in range(args.steps):
            actions = np.zeros((args.num_agents, 3), dtype=np.float32)
            for agent_id, policy in enumerate(background_policies):
                if agent_id == target_agent:
                    continue
                policy_action = policy.act(env, obs)
                actions[agent_id] = policy_action[agent_id]

            target_action, reference_agent = target_policy.act_one(env, obs)
            actions[target_agent] = target_action
            target_references.append(int(reference_agent))

            obs, reward, done, _ = env.step(actions)
            steps_run = step + 1
            total_reward += reward
            grass_steps += obs[:, 15] > 0.5

            target_tiles = env.unwrapped.tile_visited_count[target_agent]
            max_other_tiles = max(
                env.unwrapped.tile_visited_count[agent_id]
                for agent_id in range(args.num_agents)
                if agent_id != target_agent
            )
            if first_ahead_step is None and target_tiles > max_other_tiles:
                first_ahead_step = steps_run
            if target_complete_step is None and target_tiles >= len(env.unwrapped.track):
                target_complete_step = steps_run

            if not args.no_gif:
                for agent_id, car in enumerate(env.unwrapped.cars):
                    histories[agent_id].append(np.asarray(car.hull.position, dtype=np.float32))
            if not args.no_gif and steps_run % args.frame_every == 0:
                frames.append(
                    draw_frame(env, histories, steps_run, total_reward, labels, lo, hi, args.width, args.height)
                )

            if not args.no_trace:
                trace.append(
                    {
                        "step": steps_run,
                        "reward": reward.tolist(),
                        "total_reward": total_reward.tolist(),
                        "tile_visited_count": list(env.unwrapped.tile_visited_count),
                        "target_reference_agent": int(reference_agent),
                        "on_grass": obs[:, 15].tolist(),
                        "done": bool(done),
                    }
                )

            if args.stop_when_target_completes and target_complete_step is not None:
                break
            if done and not args.ignore_env_done:
                break
    finally:
        env.close()

    target_name = Path(args.target_policy_path).stem if args.target_policy_path else args.target_policy
    stem = (
        f"multicar_{args.num_agents}_target_{target_name}"
        f"_seed{args.seed}_gap{args.gap_tiles}"
    )
    gif_path = out_dir / f"{stem}.gif"
    if not args.no_gif:
        frames[0].save(
            gif_path,
            save_all=True,
            append_images=frames[1:],
            duration=int(1000 / args.fps),
            loop=0,
            optimize=True,
        )
    summary = {
        "gif": "" if args.no_gif else str(gif_path),
        "model_dir": args.model_dir,
        "num_agents": args.num_agents,
        "target_agent": target_agent,
        "target_policy": args.target_policy_path or args.target_policy,
        "baseline_policies": [
            None if policy is None else policy.name
            for policy in background_policies
        ],
        "seed": args.seed,
        "gap_tiles": args.gap_tiles,
        "start_order": start_order,
        "single_file_start": args.single_file_start,
        "steps_run": steps_run,
        "track_tiles": len(env.unwrapped.track),
        "target_complete_step": target_complete_step,
        "first_ahead_step": first_ahead_step,
        "target_reference_counts": {
            str(agent_id): target_references.count(agent_id)
            for agent_id in range(args.num_agents)
            if agent_id != target_agent
        },
        "safe": args.safe,
        "safe_blend": args.safe_blend,
        "unsafe_blend": args.unsafe_blend,
        "hard_shield": not args.disable_hard_shield,
        "emergency_lateral_threshold": args.emergency_lateral_threshold,
        "stall_patience": args.stall_patience,
        "total_reward": total_reward.tolist(),
        "tile_visited_count": list(env.unwrapped.tile_visited_count),
        "grass_rate": (grass_steps / max(steps_run, 1)).tolist(),
        "target_completed_lap": target_complete_step is not None,
        "target_final_rank_by_tiles": int(
            1
            + sum(
                tiles > env.unwrapped.tile_visited_count[target_agent]
                for agent_id, tiles in enumerate(env.unwrapped.tile_visited_count)
                if agent_id != target_agent
            )
        ),
    }
    gif_path.with_suffix(".json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    if not args.no_trace:
        gif_path.with_suffix(".trace.json").write_text(json.dumps(trace, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


def main():
    parser = argparse.ArgumentParser(
        description="Render a stricter multi-car overtake demo with the target starting last."
    )
    parser.add_argument("--model-dir", default="outputs/torch_dlc_shaped_multiseed/seed_1/models")
    parser.add_argument("--target-policy", default="joint_transition_observer", choices=sorted(MODEL_NAMES))
    parser.add_argument("--target-policy-path", default="")
    parser.add_argument("--num-agents", type=int, default=4)
    parser.add_argument("--seed", type=int, default=3)
    parser.add_argument("--gap-tiles", type=int, default=12)
    parser.add_argument("--lateral-spacing", type=float, default=2.2)
    parser.add_argument("--track-path", default="")
    parser.add_argument("--single-file-start", action="store_true")
    parser.add_argument("--steps", type=int, default=2500)
    parser.add_argument("--frame-every", type=int, default=5)
    parser.add_argument("--fps", type=int, default=12)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--safe", action="store_true")
    parser.add_argument("--safe-blend", type=float, default=0.55)
    parser.add_argument("--unsafe-blend", type=float, default=0.95)
    parser.add_argument("--disable-hard-shield", action="store_true")
    parser.add_argument("--emergency-lateral-threshold", type=float, default=0.78)
    parser.add_argument("--stall-patience", type=int, default=160)
    parser.add_argument(
        "--target-safe-base",
        default="telemetry_overtake",
        choices=[
            "track_follow",
            "overtake_track",
            "stable_lane",
            "telemetry_lane",
            "telemetry_overtake",
            "telemetry_adaptive",
            "telemetry_adaptive_recovery",
            "telemetry_adaptive_conservative",
            "telemetry_expert_gate",
            "telemetry_expert_fast",
            "telemetry_expert_barrier",
            "telemetry_expert_recovery",
        ],
    )
    parser.add_argument("--target-base-speed", type=float, default=17.0)
    parser.add_argument("--neighbor-mode", choices=["fixed", "dynamic"], default="fixed")
    parser.add_argument("--max-neighbors", type=int, default=None)
    parser.add_argument(
        "--baseline-policies",
        default="telemetry_cruise,telemetry_yield,telemetry_lane",
        help=(
            "Comma-separated background policy cycle. Options: telemetry_lane, "
            "telemetry_cruise, telemetry_yield, telemetry_overtake, telemetry_adaptive, "
            "telemetry_adaptive_conservative, telemetry_expert_gate, telemetry_expert_fast, "
            "telemetry_expert_barrier, telemetry_expert_recovery, track_follow, overtake_track."
        ),
    )
    parser.add_argument("--ignore-env-done", action="store_true")
    parser.add_argument("--stop-when-target-completes", action="store_true")
    parser.add_argument("--width", type=int, default=800)
    parser.add_argument("--height", type=int, default=800)
    parser.add_argument("--no-gif", action="store_true")
    parser.add_argument("--no-trace", action="store_true")
    parser.add_argument("--out-dir", default="outputs/torch_dlc_shaped_multiseed/gifs")
    args = parser.parse_args()
    if args.num_agents < 3:
        raise ValueError("--num-agents must be at least 3 for the multi-car demo")
    run(args)


if __name__ == "__main__":
    main()
