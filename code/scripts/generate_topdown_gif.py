#!/usr/bin/env python
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from dlc.policies import MixedPolicy, make_policy
from dlc.rollout import make_env


MODEL_NAMES = {
    "individual_transition",
    "joint_transition",
    "joint_transition_observer",
}
COLORS = [(220, 50, 47), (38, 139, 210)]


def make_model_policy(model_dir, name, seed, device, safe, safe_blend, unsafe_blend, safe_base_policy):
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
    )


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


def draw_frame(env, histories, step, total_reward, policies, lo, hi, width, height):
    image = Image.new("RGB", (width, height), (36, 113, 61))
    draw = ImageDraw.Draw(image)

    for vertices, color in env.unwrapped.road_poly:
        rgb = tuple(int(np.clip(c, 0.0, 1.0) * 255) for c in color)
        draw.polygon(transform_points(vertices, lo, hi, width, height), fill=rgb)

    for agent_id, history in enumerate(histories):
        if len(history) > 1:
            draw.line(
                transform_points(history, lo, hi, width, height),
                fill=COLORS[agent_id],
                width=3,
            )

    positions = [np.asarray(car.hull.position, dtype=np.float32) for car in env.unwrapped.cars]
    for agent_id, pos in enumerate(positions):
        x, y = transform_points([pos], lo, hi, width, height)[0]
        r = 5
        draw.ellipse([x - r, y - r, x + r, y + r], fill=COLORS[agent_id], outline=(255, 255, 255))
        draw.text((x + 7, y - 7), f"A{agent_id}", fill=(255, 255, 255))

    tiles = env.unwrapped.tile_visited_count
    lines = [
        f"step {step}",
        f"A0 {policies[0]}  tiles {tiles[0]}  reward {total_reward[0]:.1f}",
        f"A1 {policies[1]}  tiles {tiles[1]}  reward {total_reward[1]:.1f}",
    ]
    x, y = 10, 10
    box_w = max(draw.textlength(line) for line in lines) + 16
    box_h = 18 * len(lines) + 10
    draw.rectangle([x - 5, y - 5, x + box_w, y + box_h], fill=(0, 0, 0))
    for idx, line in enumerate(lines):
        draw.text((x, y + 18 * idx), line, fill=(255, 255, 255))
    return image


def main():
    parser = argparse.ArgumentParser(description="Render a top-down trained policy matchup GIF.")
    parser.add_argument("--model-dir", default="outputs/torch_dlc_experiment/seed_0/models")
    parser.add_argument("--agent0", default="individual_transition", choices=sorted(MODEL_NAMES))
    parser.add_argument("--agent1", default="joint_transition_observer", choices=sorted(MODEL_NAMES))
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--steps", type=int, default=700)
    parser.add_argument("--frame-every", type=int, default=3)
    parser.add_argument("--fps", type=int, default=12)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--safe", action="store_true")
    parser.add_argument("--safe-blend", type=float, default=0.75)
    parser.add_argument("--unsafe-blend", type=float, default=0.98)
    parser.add_argument("--agent0-safe-base", default="overtake_track", choices=["track_follow", "overtake_track"])
    parser.add_argument("--agent1-safe-base", default="overtake_track", choices=["track_follow", "overtake_track"])
    parser.add_argument("--width", type=int, default=720)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--out-dir", default="outputs/torch_dlc_experiment/gifs")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    policy0 = make_model_policy(
        args.model_dir,
        args.agent0,
        args.seed,
        args.device,
        args.safe,
        args.safe_blend,
        args.unsafe_blend,
        args.agent0_safe_base,
    )
    policy1 = make_model_policy(
        args.model_dir,
        args.agent1,
        args.seed + 10_000,
        args.device,
        args.safe,
        args.safe_blend,
        args.unsafe_blend,
        args.agent1_safe_base,
    )
    policy = MixedPolicy([policy0, policy1])
    policies = [args.agent0, args.agent1]

    env = make_env(num_agents=2, seed=args.seed, observation_type="telemetry")
    frames = []
    trace = []
    total_reward = np.zeros(2, dtype=np.float64)
    histories = [[], []]

    try:
        obs = env.reset()
        lo, hi = world_bounds(env)
        policy.reset()
        for agent_id, car in enumerate(env.unwrapped.cars):
            histories[agent_id].append(np.asarray(car.hull.position, dtype=np.float32))
        frames.append(draw_frame(env, histories, 0, total_reward, policies, lo, hi, args.width, args.height))

        done = False
        steps_run = 0
        for step in range(args.steps):
            action = policy.act(env, obs)
            obs, reward, done, _ = env.step(action)
            total_reward += reward
            steps_run = step + 1
            for agent_id, car in enumerate(env.unwrapped.cars):
                histories[agent_id].append(np.asarray(car.hull.position, dtype=np.float32))
            trace.append(
                {
                    "step": steps_run,
                    "reward": reward.tolist(),
                    "total_reward": total_reward.tolist(),
                    "tile_visited_count": list(env.unwrapped.tile_visited_count),
                    "agent0_track_index": float(obs[0, 8]),
                    "agent1_track_index": float(obs[1, 8]),
                    "agent0_on_grass": float(obs[0, 15]),
                    "agent1_on_grass": float(obs[1, 15]),
                }
            )
            if steps_run % args.frame_every == 0:
                frames.append(
                    draw_frame(env, histories, steps_run, total_reward, policies, lo, hi, args.width, args.height)
                )
            if done:
                break
    finally:
        env.close()

    stem = (
        f"topdown_{'safe_' if args.safe else ''}{args.agent0}_vs_{args.agent1}"
        f"_seed{args.seed}"
    )
    gif_path = out_dir / f"{stem}.gif"
    frames[0].save(
        gif_path,
        save_all=True,
        append_images=frames[1:],
        duration=int(1000 / args.fps),
        loop=0,
        optimize=True,
    )
    summary = {
        "description": "Top-down environment GIF; policies consume telemetry observations.",
        "gif": str(gif_path),
        "model_dir": args.model_dir,
        "agent0_policy": args.agent0,
        "agent1_policy": args.agent1,
        "seed": args.seed,
        "steps_run": steps_run,
        "safe": args.safe,
        "safe_blend": args.safe_blend,
        "unsafe_blend": args.unsafe_blend,
        "agent0_safe_base": args.agent0_safe_base,
        "agent1_safe_base": args.agent1_safe_base,
        "total_reward": total_reward.tolist(),
        "tile_visited_count": list(env.unwrapped.tile_visited_count),
    }
    gif_path.with_suffix(".json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    gif_path.with_suffix(".trace.json").write_text(json.dumps(trace, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
