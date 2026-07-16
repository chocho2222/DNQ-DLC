import argparse
import json
import math
import subprocess
from pathlib import Path

import gym
import gym_multi_car_racing  # noqa: F401 - registers MultiCarRacing-v0
import numpy as np


def write_ppm(path, image):
    """Write an RGB uint8 image without adding an image dependency."""
    path = Path(path)
    height, width, channels = image.shape
    if channels != 3:
        raise ValueError(f"expected RGB image with 3 channels, got {image.shape}")

    with path.open("wb") as handle:
        handle.write(f"P6\n{width} {height}\n255\n".encode("ascii"))
        handle.write(np.ascontiguousarray(image).tobytes())


def write_gif(frame_paths, gif_path, fps):
    if not frame_paths:
        return None

    frame_list = gif_path.with_suffix(".frames.txt")
    frame_duration = 1.0 / fps
    frame_list.write_text(
        "".join(
            f"file '{path.resolve()}'\nduration {frame_duration:.6f}\n"
            for path in frame_paths
        )
        + f"file '{frame_paths[-1].resolve()}'\n",
        encoding="utf-8",
    )

    palette_path = gif_path.with_suffix(".palette.png")
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(frame_list),
            "-vf",
            "palettegen",
            str(palette_path),
        ],
        check=True,
    )
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(frame_list),
            "-i",
            str(palette_path),
            "-lavfi",
            "paletteuse",
            str(gif_path),
        ],
        check=True,
    )

    return gif_path


def wrap_to_pi(angle):
    return (angle + math.pi) % (2 * math.pi) - math.pi


def random_action(rng, num_agents):
    return np.column_stack(
        [
            rng.uniform(-1.0, 1.0, size=num_agents),
            rng.uniform(0.0, 1.0, size=num_agents),
            rng.uniform(0.0, 1.0, size=num_agents),
        ]
    ).astype(np.float32)


def track_follow_action(env, num_agents, lookahead=8):
    action = np.zeros((num_agents, 3), dtype=np.float32)
    base_env = env.unwrapped
    track_xy = np.array(base_env.track)[:, 2:]

    for agent_id, car in enumerate(base_env.cars):
        car_pos = np.array(car.hull.position).reshape((1, 2))
        track_index = int(np.argmin(np.linalg.norm(car_pos - track_xy, axis=1)))
        target_index = min(track_index + lookahead, len(base_env.track) - 1)
        desired_angle = base_env.track[target_index][1]
        if base_env.episode_direction == "CW":
            desired_angle += math.pi

        angle_error = wrap_to_pi(desired_angle - car.hull.angle)
        speed = np.linalg.norm(car.hull.linearVelocity)

        action[agent_id, 0] = np.clip(-1.6 * angle_error, -1.0, 1.0)
        action[agent_id, 1] = 0.85 if speed < 35.0 else 0.25
        action[agent_id, 2] = 0.0 if speed < 45.0 else 0.2

    return action


def get_agent_frame(env, obs, agent_id, gif_mode):
    if gif_mode == "state_pixels":
        return obs[agent_id]
    return env.render("rgb_array")[agent_id]


def main():
    parser = argparse.ArgumentParser(
        description="Reproduce a deterministic random rollout in MultiCarRacing-v0."
    )
    parser.add_argument("--steps", type=int, default=200)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--num-agents", type=int, default=2)
    parser.add_argument("--out-dir", default="reproduction_outputs")
    parser.add_argument("--policy", choices=["random", "track-follow"], default="random")
    parser.add_argument("--agent-id", type=int, default=0)
    parser.add_argument("--save-gif", action="store_true")
    parser.add_argument("--gif-mode", choices=["state_pixels", "rgb_array"], default="state_pixels")
    parser.add_argument("--gif-every", type=int, default=2)
    parser.add_argument("--gif-fps", type=int, default=12)
    args = parser.parse_args()
    if not 0 <= args.agent_id < args.num_agents:
        raise ValueError("--agent-id must be between 0 and num-agents - 1")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    frame_dir = out_dir / "gif_frames"
    frame_paths = []
    if args.save_gif:
        frame_dir.mkdir(parents=True, exist_ok=True)

    np.random.seed(args.seed)
    env = gym.make(
        "MultiCarRacing-v0",
        num_agents=args.num_agents,
        direction="CCW",
        use_random_direction=False,
        backwards_flag=True,
        h_ratio=0.25,
        use_ego_color=False,
    )
    env.seed(args.seed)

    total_reward = np.zeros(args.num_agents, dtype=np.float64)
    trace = []

    try:
        obs = env.reset()
        write_ppm(out_dir / "initial_agent0.ppm", obs[0])
        if args.save_gif:
            frame_path = frame_dir / "agent0_0000.ppm"
            write_ppm(frame_path, get_agent_frame(env, obs, args.agent_id, args.gif_mode))
            frame_paths.append(frame_path)

        rng = np.random.default_rng(args.seed)
        done = False
        steps_run = 0

        for step in range(args.steps):
            if args.policy == "random":
                action = random_action(rng, args.num_agents)
            else:
                action = track_follow_action(env, args.num_agents)

            obs, reward, done, _ = env.step(action)
            steps_run = step + 1
            if args.save_gif and steps_run % args.gif_every == 0:
                frame_path = frame_dir / f"agent0_{steps_run:04d}.ppm"
                write_ppm(
                    frame_path,
                    get_agent_frame(env, obs, args.agent_id, args.gif_mode),
                )
                frame_paths.append(frame_path)

            total_reward += reward
            trace.append(
                {
                    "step": steps_run,
                    "reward": reward.tolist(),
                    "total_reward": total_reward.tolist(),
                    "done": bool(done),
                    "tile_visited_count": list(env.tile_visited_count),
                }
            )

            if done:
                break

        write_ppm(out_dir / "final_agent0.ppm", obs[0])
        gif_path = None
        if args.save_gif:
            gif_path = write_gif(
                frame_paths,
                out_dir
                / (
                    f"agent{args.agent_id}_{args.policy}_{args.gif_mode}"
                    f"_seed{args.seed}_steps{steps_run}.gif"
                ),
                args.gif_fps,
            )

        summary = {
            "environment": "MultiCarRacing-v0",
            "seed": args.seed,
            "num_agents": args.num_agents,
            "policy": args.policy,
            "requested_steps": args.steps,
            "steps_run": steps_run,
            "done": bool(done),
            "total_reward": total_reward.tolist(),
            "tile_visited_count": list(env.tile_visited_count),
            "observation_shape": list(obs.shape),
            "outputs": {
                "initial_agent0": str(out_dir / "initial_agent0.ppm"),
                "final_agent0": str(out_dir / "final_agent0.ppm"),
                "trace": str(out_dir / "rollout_trace.json"),
                "summary": str(out_dir / "summary.json"),
            },
        }
        if gif_path is not None:
            summary["outputs"]["agent0_gif"] = str(gif_path)

        (out_dir / "rollout_trace.json").write_text(
            json.dumps(trace, indent=2), encoding="utf-8"
        )
        (out_dir / "summary.json").write_text(
            json.dumps(summary, indent=2), encoding="utf-8"
        )

        print(json.dumps(summary, indent=2))
    finally:
        env.close()


if __name__ == "__main__":
    main()
