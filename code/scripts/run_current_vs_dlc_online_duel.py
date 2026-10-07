#!/usr/bin/env python
import argparse
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from dlc.policies import TelemetryCruisePolicy, TelemetryLanePolicy, TelemetryYieldPolicy, make_policy
from dlc.rollout import make_env


COLORS = [
    (220, 50, 47),
    (38, 139, 210),
    (133, 153, 0),
    (203, 75, 22),
    (108, 113, 196),
    (42, 161, 152),
]


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


def nearest_track_index(env, position):
    track_xy = np.asarray(env.unwrapped.track, dtype=np.float32)[:, 2:]
    return int(np.argmin(np.linalg.norm(np.asarray(position, dtype=np.float32).reshape(1, 2) - track_xy, axis=1)))


def wrap_to_pi(angle):
    return (angle + math.pi) % (2 * math.pi) - math.pi


def choose_reference_ahead(env, obs, target_agent):
    base_env = env.unwrapped
    track_len = len(base_env.track)
    target_idx = nearest_track_index(env, base_env.cars[target_agent].hull.position)
    best_agent = None
    best_delta = float("inf")
    for agent_id, car in enumerate(base_env.cars):
        if agent_id == target_agent:
            continue
        idx = nearest_track_index(env, car.hull.position)
        delta = (idx - target_idx) % track_len
        if 0 < delta < best_delta:
            best_delta = delta
            best_agent = agent_id
    if best_agent is None:
        best_agent = 0 if target_agent != 0 else 1
    return best_agent


def local_pair_obs(env, obs, target_agent, reference_agent):
    local = np.zeros((2, 24), dtype=np.float32)
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
                float(np.dot(rel_pos, heading_vec) / (2000 / 6.0)),
                float(np.dot(rel_pos, left_vec) / (2000 / 6.0)),
                rel_vel[0] / 50.0,
                rel_vel[1] / 50.0,
                float(np.linalg.norm(rel_pos) / (2000 / 6.0)),
                math.sin(rel_heading),
                math.cos(rel_heading),
            ],
            dtype=np.float32,
        )

    local[0, 17:] = rel_features(target_agent, reference_agent)
    local[1, 17:] = rel_features(reference_agent, target_agent)
    return local


class OnlineCurrentVsDLC:
    def __init__(
        self,
        current_policy,
        dlc_policy,
        dlc_base_policy,
        background_policies,
        current_agent=0,
        dlc_agent=1,
        target_agent=3,
        dlc_safe_blend=0.55,
        dlc_unsafe_blend=0.95,
    ):
        self.current_policy = current_policy
        self.dlc_policy = dlc_policy
        self.dlc_base_policy = dlc_base_policy
        self.background_policies = background_policies
        self.current_agent = int(current_agent)
        self.dlc_agent = int(dlc_agent)
        self.target_agent = int(target_agent)
        self.dlc_safe_blend = float(dlc_safe_blend)
        self.dlc_unsafe_blend = float(dlc_unsafe_blend)
        self.name = "current_vs_dlc_online"
        self.last_info = {}

    def reset(self):
        self.current_policy.reset()
        self.dlc_policy.reset()
        self.dlc_base_policy.reset()
        for policy in self.background_policies.values():
            policy.reset()
        self.last_info = {}

    def _background_actions(self, env, obs):
        actions = np.zeros((env.unwrapped.num_agents, 3), dtype=np.float32)
        for agent_id, policy in self.background_policies.items():
            if agent_id in {self.current_agent, self.dlc_agent}:
                continue
            actions[agent_id] = policy.act(env, obs)[agent_id]
        return actions

    def _blend_dlc_action(self, pair_obs, learned, base):
        target_obs = pair_obs[0]
        lateral = abs(float(target_obs[12]))
        heading_cos = float(target_obs[14])
        on_grass = float(target_obs[15]) > 0.5
        backward = float(target_obs[16]) > 0.5
        unsafe = lateral > 1.2 or heading_cos < 0.1 or on_grass or backward
        blend = self.dlc_unsafe_blend if unsafe else self.dlc_safe_blend
        action = blend * base + (1.0 - blend) * learned
        action[0] = np.clip(action[0], -1.0, 1.0)
        action[1:] = np.clip(action[1:], 0.0, 1.0)
        return action.astype(np.float32), unsafe, blend

    def act(self, env, obs):
        actions = self._background_actions(env, obs)
        current_action = self.current_policy.act(env, obs)[self.current_agent]
        actions[self.current_agent] = current_action

        reference_agent = choose_reference_ahead(env, obs, self.dlc_agent)
        pair_obs = local_pair_obs(env, obs, self.dlc_agent, reference_agent)
        dlc_learned_action = self.dlc_policy.act(env, pair_obs)[0]
        dlc_base_action = self.dlc_base_policy.act(env, pair_obs)[0]
        dlc_action, dlc_unsafe, dlc_blend = self._blend_dlc_action(pair_obs, dlc_learned_action, dlc_base_action)
        actions[self.dlc_agent] = dlc_action
        self.last_info = {
            "dlc_reference_agent": int(reference_agent),
            "dlc_unsafe": bool(dlc_unsafe),
            "dlc_blend": float(dlc_blend),
            "dlc_learned_action": dlc_learned_action.tolist(),
            "dlc_base_action": dlc_base_action.tolist(),
            "dlc_action": dlc_action.tolist(),
            "current_action": current_action.tolist(),
            "background_actions": {
                str(agent_id): actions[agent_id].tolist()
                for agent_id in self.background_policies
            },
        }
        return actions.astype(np.float32)


def draw_frame(env, histories, step, total_reward, labels, lo, hi, width, height):
    image = Image.new("RGB", (width, height), (36, 113, 61))
    draw = ImageDraw.Draw(image)

    for vertices, color in env.unwrapped.road_poly:
        rgb = tuple(int(np.clip(c, 0.0, 1.0) * 255) for c in color)
        draw.polygon(transform_points(vertices, lo, hi, width, height), fill=rgb)

    for agent_id, history in enumerate(histories):
        if len(history) > 1:
            draw.line(transform_points(history, lo, hi, width, height), fill=COLORS[agent_id % len(COLORS)], width=3)

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


def make_background_policy(name, seed, device, agent_id, speed):
    if name == "slow_lane":
        return TelemetryLanePolicy(target_speed=speed, gas=0.38, brake=0.55, name=f"slow_lane_{agent_id}")
    if name == "slow_cruise":
        return TelemetryCruisePolicy(target_speed=speed, gas=0.36, brake=0.55, name=f"slow_cruise_{agent_id}")
    if name == "slow_yield":
        return TelemetryYieldPolicy(target_speed=speed, yield_speed=max(speed - 4.0, 5.0), gas=0.36, brake=0.55, name=f"slow_yield_{agent_id}")
    return make_policy(name, seed=seed, device=device, safe=False)


def main():
    parser = argparse.ArgumentParser(description="Run current algorithm and DLC world model online in the same 4-car race.")
    parser.add_argument("--current-model", default="multi_car_racing/outputs/paper_multicar_overtake_20260618/models/graph_bc/graph_bc.graph.pt")
    parser.add_argument("--dlc-model", default="multi_car_racing/outputs/torch_dlc_full_lap_seed01/seed_1/models/joint_transition_observer.pt")
    parser.add_argument("--seed", type=int, default=3)
    parser.add_argument("--steps", type=int, default=6000)
    parser.add_argument("--frame-every", type=int, default=5)
    parser.add_argument("--fps", type=int, default=12)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--out-dir", default="multi_car_racing/outputs/paper_multicar_overtake_20260618/evaluations/current_vs_dlc_online_duel")
    parser.add_argument("--background-policies", default="telemetry_cruise,telemetry_yield")
    parser.add_argument("--background-speeds", default="12.0,11.0")
    parser.add_argument("--width", type=int, default=900)
    parser.add_argument("--height", type=int, default=900)
    parser.add_argument("--safe", action="store_true")
    parser.add_argument("--safe-blend", type=float, default=0.25)
    parser.add_argument("--unsafe-blend", type=float, default=1.0)
    parser.add_argument("--safe-base-policy", default="telemetry_overtake")
    parser.add_argument("--current-hard-shield", action="store_true")
    parser.add_argument("--current-neighbor-mode", choices=["fixed", "dynamic"], default="fixed")
    parser.add_argument("--current-max-neighbors", type=int, default=None)
    parser.add_argument("--dlc-neighbor-mode", choices=["fixed", "dynamic"], default="fixed")
    parser.add_argument("--dlc-max-neighbors", type=int, default=None)
    parser.add_argument("--hard-shield-base-policy", default="telemetry_expert_barrier")
    parser.add_argument("--hard-shield-safe-blend", type=float, default=0.15)
    parser.add_argument("--hard-shield-unsafe-blend", type=float, default=1.0)
    parser.add_argument("--dlc-safe-blend", type=float, default=0.55)
    parser.add_argument("--dlc-unsafe-blend", type=float, default=0.95)
    parser.add_argument("--line-spacing", type=int, default=5)
    parser.add_argument("--lateral-spacing", type=float, default=2.2)
    parser.add_argument("--track-path", default="")
    parser.add_argument("--no-gif", action="store_true")
    parser.add_argument(
        "--start-order",
        default="0,2,4,6",
        help="Comma-separated starting slots for A0,A1,A2,A3. Larger slot means farther behind.",
    )
    parser.add_argument(
        "--finish-mode",
        default="all",
        choices=["all", "duel", "any", "steps"],
        help="Stop condition based on completed laps: all cars, current+DLC, any car, or fixed step budget.",
    )
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    start_order = [int(item.strip()) for item in args.start_order.split(",") if item.strip()]
    if len(start_order) != 4:
        raise ValueError("--start-order must contain four comma-separated slots for the four agents")

    current_policy = make_policy(
        args.current_model,
        seed=args.seed,
        device=args.device,
        safe=args.safe,
        safe_blend=args.safe_blend,
        unsafe_blend=args.unsafe_blend,
        safe_base_policy=args.safe_base_policy,
        neighbor_mode=args.current_neighbor_mode,
        max_neighbors=args.current_max_neighbors,
    )
    if args.current_hard_shield:
        from dlc.graph_policy import SafetyShieldPolicy

        current_policy = SafetyShieldPolicy(
            current_policy,
            fallback_policy=make_policy(args.hard_shield_base_policy, seed=args.seed + 77, device=args.device, safe=False),
            safe_blend=args.hard_shield_safe_blend,
            unsafe_blend=args.hard_shield_unsafe_blend,
            lateral_threshold=0.34,
            heading_cos_threshold=0.70,
            emergency_lateral_threshold=0.50,
            hard_intervention=True,
            stall_patience=90,
            close_forward_gap=0.035,
            close_lateral_gap=0.030,
        )
    dlc_policy = make_policy(
        args.dlc_model,
        seed=args.seed + 999,
        device=args.device,
        safe=False,
        neighbor_mode=args.dlc_neighbor_mode,
        max_neighbors=args.dlc_max_neighbors,
    )
    dlc_base_policy = make_policy("telemetry_overtake", seed=args.seed + 1000, device=args.device, safe=False)
    background_names = [item.strip() for item in args.background_policies.split(",") if item.strip()]
    if len(background_names) < 2:
        background_names = (background_names * 2)[:2]
    background_speeds = [float(item.strip()) for item in args.background_speeds.split(",") if item.strip()]
    if len(background_speeds) < 2:
        background_speeds = (background_speeds * 2)[:2]
    bg0 = make_background_policy(background_names[0], args.seed + 100, args.device, 2, background_speeds[0])
    bg1 = make_background_policy(background_names[1], args.seed + 200, args.device, 3, background_speeds[1])
    background_policies = {2: bg0, 3: bg1}

    policy = OnlineCurrentVsDLC(
        current_policy=current_policy,
        dlc_policy=dlc_policy,
        dlc_base_policy=dlc_base_policy,
        background_policies=background_policies,
        current_agent=0,
        dlc_agent=1,
        target_agent=3,
        dlc_safe_blend=args.dlc_safe_blend,
        dlc_unsafe_blend=args.dlc_unsafe_blend,
    )

    env = make_env(
        num_agents=4,
        seed=args.seed,
        observation_type="telemetry",
        start_order=start_order,
        line_spacing=args.line_spacing,
        lateral_spacing=args.lateral_spacing,
        track_path=args.track_path or None,
    )
    if hasattr(env, "_max_episode_steps"):
        env._max_episode_steps = max(int(args.steps) + 1, int(env._max_episode_steps))

    frames = []
    record_frames = not args.no_gif
    trace = []
    total_reward = np.zeros(4, dtype=np.float64)
    histories = [[] for _ in range(4)]
    labels = [
        "当前算法",
        "DLC world",
        background_names[0],
        background_names[1],
    ]
    try:
        obs = env.reset()
        policy.reset()
        lo, hi = world_bounds(env)
        for agent_id, car in enumerate(env.unwrapped.cars):
            histories[agent_id].append(np.asarray(car.hull.position, dtype=np.float32))
        if record_frames:
            frames.append(draw_frame(env, histories, 0, total_reward, labels, lo, hi, args.width, args.height))

        steps_run = 0
        done = False
        first_complete_step = [None] * 4
        first_ahead_step = None
        for step in range(args.steps):
            action = policy.act(env, obs)
            obs, reward, done, _ = env.step(action)
            steps_run = step + 1
            total_reward += reward
            tile_counts = list(env.unwrapped.tile_visited_count)
            track_tiles_now = len(env.unwrapped.track)
            for agent_id, count in enumerate(tile_counts):
                if first_complete_step[agent_id] is None and count >= track_tiles_now:
                    first_complete_step[agent_id] = steps_run
            if first_ahead_step is None and tile_counts[0] > tile_counts[1]:
                first_ahead_step = steps_run
            for agent_id, car in enumerate(env.unwrapped.cars):
                histories[agent_id].append(np.asarray(car.hull.position, dtype=np.float32))
            if record_frames and steps_run % args.frame_every == 0:
                frames.append(draw_frame(env, histories, steps_run, total_reward, labels, lo, hi, args.width, args.height))
            trace.append(
                {
                    "step": steps_run,
                    "reward": reward.tolist(),
                    "total_reward": total_reward.tolist(),
                    "tile_visited_count": tile_counts,
                    "first_complete_step": first_complete_step,
                    "first_ahead_step": first_ahead_step,
                    "done": bool(done),
                    "action": action.tolist(),
                    "policy_info": policy.last_info,
                    "speed": [float(np.linalg.norm(car.hull.linearVelocity)) for car in env.unwrapped.cars],
                    "telemetry": {
                        "progress": [float(item) for item in obs[:, 9]],
                        "lateral_error": [float(item) for item in obs[:, 12]],
                        "heading_cos": [float(item) for item in obs[:, 14]],
                        "on_grass": [bool(item > 0.5) for item in obs[:, 15]],
                        "backward": [bool(item > 0.5) for item in obs[:, 16]],
                    },
                    "positions": [np.asarray(car.hull.position, dtype=np.float32).tolist() for car in env.unwrapped.cars],
                }
            )
            if args.finish_mode == "all" and all(count >= track_tiles_now for count in tile_counts):
                break
            if args.finish_mode == "duel" and tile_counts[0] >= track_tiles_now and tile_counts[1] >= track_tiles_now:
                break
            if args.finish_mode == "any" and any(count >= track_tiles_now for count in tile_counts):
                break
    finally:
        tile_visited_count = list(env.unwrapped.tile_visited_count)
        track_tiles = len(env.unwrapped.track)
        env.close()

    stem = f"current_vs_dlc_online_seed{args.seed}"
    gif_path = out_dir / f"{stem}.gif"
    if args.no_gif:
        gif_path = None
    else:
        frames[0].save(
            gif_path,
            save_all=True,
            append_images=frames[1:],
            duration=int(1000 / args.fps),
            loop=0,
            optimize=True,
        )

    if trace:
        on_grass = np.asarray([row["telemetry"]["on_grass"] for row in trace], dtype=np.float32)
        lateral = np.asarray([row["telemetry"]["lateral_error"] for row in trace], dtype=np.float32)
        backward = np.asarray([row["telemetry"]["backward"] for row in trace], dtype=np.float32)
        grace_steps = min(20, len(trace))
        eval_slice = slice(grace_steps, None)
        grass_rate = on_grass[eval_slice].mean(axis=0).tolist() if len(trace) > grace_steps else on_grass.mean(axis=0).tolist()
        backward_rate = backward[eval_slice].mean(axis=0).tolist() if len(trace) > grace_steps else backward.mean(axis=0).tolist()
        mean_abs_lateral = np.abs(lateral[eval_slice]).mean(axis=0).tolist() if len(trace) > grace_steps else np.abs(lateral).mean(axis=0).tolist()
        max_abs_lateral = np.abs(lateral[eval_slice]).max(axis=0).tolist() if len(trace) > grace_steps else np.abs(lateral).max(axis=0).tolist()
    else:
        grass_rate = [None] * 4
        backward_rate = [None] * 4
        mean_abs_lateral = [None] * 4
        max_abs_lateral = [None] * 4

    summary = {
        "description": "Current algorithm and DLC world model running online in the same 4-car environment.",
        "seed": args.seed,
        "steps_run": steps_run,
        "gif": str(gif_path) if gif_path is not None else None,
        "total_reward": total_reward.tolist(),
        "tile_visited_count": tile_visited_count,
        "track_tiles": track_tiles,
        "start_order": start_order,
        "current_completed_lap": bool(tile_visited_count[0] >= track_tiles),
        "dlc_completed_lap": bool(tile_visited_count[1] >= track_tiles),
        "completed_lap": [bool(count >= track_tiles) for count in tile_visited_count],
        "first_complete_step": first_complete_step,
        "first_ahead_step_current_vs_dlc": first_ahead_step,
        "finish_mode": args.finish_mode,
        "line_spacing": int(args.line_spacing),
        "lateral_spacing": float(args.lateral_spacing),
        "track_path": args.track_path,
        "current_safe": bool(args.safe),
        "current_safe_blend": float(args.safe_blend),
        "current_unsafe_blend": float(args.unsafe_blend),
        "current_safe_base_policy": args.safe_base_policy,
        "grass_rate": grass_rate,
        "backward_rate": backward_rate,
        "mean_abs_lateral": mean_abs_lateral,
        "max_abs_lateral": max_abs_lateral,
        "current_rank": int(1 + sum(t > tile_visited_count[0] for t in tile_visited_count[1:])),
        "dlc_rank": int(1 + sum(t > tile_visited_count[1] for i, t in enumerate(tile_visited_count) if i != 1)),
        "current_policy": Path(args.current_model).name,
        "dlc_policy": Path(args.dlc_model).name,
        "background_policies": background_names,
        "background_speeds": background_speeds,
    }
    (out_dir / f"{stem}.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / f"{stem}.trace.json").write_text(json.dumps(trace, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
