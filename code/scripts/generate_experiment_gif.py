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


def load_policy(
    model_dir,
    name,
    seed,
    device,
    safe=False,
    safe_blend=0.35,
    unsafe_blend=0.85,
    safe_base_policy="overtake_track",
):
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


def add_overlay(frame, step, total_reward, policies):
    image = Image.fromarray(frame)
    draw = ImageDraw.Draw(image)
    lines = [
        f"step {step}",
        f"agent0: {policies[0]}  reward {total_reward[0]:.1f}",
        f"agent1: {policies[1]}  reward {total_reward[1]:.1f}",
    ]
    x, y = 8, 8
    line_h = 14
    width = max(draw.textlength(line) for line in lines) + 14
    height = line_h * len(lines) + 10
    draw.rectangle([x - 4, y - 4, x + width, y + height], fill=(0, 0, 0))
    for idx, line in enumerate(lines):
        draw.text((x, y + idx * line_h), line, fill=(255, 255, 255))
    return image


def main():
    parser = argparse.ArgumentParser(
        description="Render a trained telemetry-DLC policy matchup as a GIF."
    )
    parser.add_argument("--model-dir", default="outputs/torch_dlc_experiment/seed_0/models")
    parser.add_argument("--agent0", default="joint_transition_observer", choices=sorted(MODEL_NAMES))
    parser.add_argument("--agent1", default="individual_transition", choices=sorted(MODEL_NAMES))
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--steps", type=int, default=350)
    parser.add_argument("--frame-every", type=int, default=2)
    parser.add_argument("--fps", type=int, default=12)
    parser.add_argument("--view-agent", type=int, default=0)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--safe", action="store_true")
    parser.add_argument("--safe-blend", type=float, default=0.35)
    parser.add_argument("--unsafe-blend", type=float, default=0.85)
    parser.add_argument("--agent0-safe-base", default="overtake_track", choices=["track_follow", "overtake_track"])
    parser.add_argument("--agent1-safe-base", default="overtake_track", choices=["track_follow", "overtake_track"])
    parser.add_argument("--out-dir", default="outputs/torch_dlc_experiment/gifs")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    policy0 = load_policy(
        args.model_dir,
        args.agent0,
        args.seed,
        args.device,
        safe=args.safe,
        safe_blend=args.safe_blend,
        unsafe_blend=args.unsafe_blend,
        safe_base_policy=args.agent0_safe_base,
    )
    policy1 = load_policy(
        args.model_dir,
        args.agent1,
        args.seed + 10_000,
        args.device,
        safe=args.safe,
        safe_blend=args.safe_blend,
        unsafe_blend=args.unsafe_blend,
        safe_base_policy=args.agent1_safe_base,
    )
    policy = MixedPolicy([policy0, policy1])
    policies = [args.agent0, args.agent1]

    env = make_env(num_agents=2, seed=args.seed, observation_type="telemetry")
    frames = []
    trace = []
    total_reward = np.zeros(2, dtype=np.float64)

    try:
        obs = env.reset()
        policy.reset()
        frames.append(add_overlay(env.render("rgb_array")[args.view_agent], 0, total_reward, policies))
        done = False
        steps_run = 0

        for step in range(args.steps):
            action = policy.act(env, obs)
            obs, reward, done, _ = env.step(action)
            steps_run = step + 1
            total_reward += reward
            trace.append(
                {
                    "step": steps_run,
                    "reward": reward.tolist(),
                    "total_reward": total_reward.tolist(),
                    "tile_visited_count": list(env.unwrapped.tile_visited_count),
                    "done": bool(done),
                }
            )
            if steps_run % args.frame_every == 0:
                frames.append(
                    add_overlay(
                        env.render("rgb_array")[args.view_agent],
                        steps_run,
                        total_reward,
                        policies,
                    )
                )
            if done:
                break
    finally:
        env.close()

    gif_path = out_dir / (
        f"final_{'safe_' if args.safe else ''}{args.agent0}_vs_{args.agent1}"
        f"_seed{args.seed}_view_agent{args.view_agent}.gif"
    )
    duration_ms = int(1000 / args.fps)
    frames[0].save(
        gif_path,
        save_all=True,
        append_images=frames[1:],
        duration=duration_ms,
        loop=0,
        optimize=True,
    )

    summary = {
        "description": "Rendered environment GIF; policies consume telemetry observations.",
        "model_dir": args.model_dir,
        "agent0_policy": args.agent0,
        "agent1_policy": args.agent1,
        "seed": args.seed,
        "steps_requested": args.steps,
        "steps_run": steps_run,
        "view_agent": args.view_agent,
        "device": args.device,
        "safe": args.safe,
        "safe_blend": args.safe_blend,
        "unsafe_blend": args.unsafe_blend,
        "agent0_safe_base": args.agent0_safe_base,
        "agent1_safe_base": args.agent1_safe_base,
        "total_reward": total_reward.tolist(),
        "tile_visited_count": list(env.unwrapped.tile_visited_count),
        "frames": len(frames),
        "gif": str(gif_path),
    }
    summary_path = gif_path.with_suffix(".json")
    trace_path = gif_path.with_suffix(".trace.json")
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    trace_path.write_text(json.dumps(trace, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
