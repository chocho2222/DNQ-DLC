import argparse
import json
import math
from pathlib import Path

import gym
import gym_multi_car_racing  # noqa: F401 - registers MultiCarRacing-v0
import numpy as np


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


def main():
    parser = argparse.ArgumentParser(
        description="Run a deterministic privileged-telemetry rollout."
    )
    parser.add_argument("--steps", type=int, default=200)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--num-agents", type=int, default=2)
    parser.add_argument("--out-dir", default="telemetry_outputs")
    parser.add_argument("--policy", choices=["random", "track-follow"], default="track-follow")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    np.random.seed(args.seed)
    rng = np.random.default_rng(args.seed)
    env = gym.make(
        "MultiCarRacing-v0",
        num_agents=args.num_agents,
        direction="CCW",
        use_random_direction=False,
        backwards_flag=True,
        h_ratio=0.25,
        use_ego_color=False,
        observation_type="telemetry",
    )
    env.seed(args.seed)

    total_reward = np.zeros(args.num_agents, dtype=np.float64)
    trace = []

    try:
        obs = env.reset()
        done = False
        steps_run = 0

        for step in range(args.steps):
            if args.policy == "random":
                action = random_action(rng, args.num_agents)
            else:
                action = track_follow_action(env, args.num_agents)

            obs, reward, done, _ = env.step(action)
            steps_run = step + 1
            total_reward += reward
            trace.append(
                {
                    "step": steps_run,
                    "reward": reward.tolist(),
                    "total_reward": total_reward.tolist(),
                    "done": bool(done),
                    "tile_visited_count": list(env.unwrapped.tile_visited_count),
                    "agent0_telemetry": obs[0].tolist(),
                }
            )
            if done:
                break

        summary = {
            "environment": "MultiCarRacing-v0",
            "observation_type": "telemetry",
            "seed": args.seed,
            "num_agents": args.num_agents,
            "policy": args.policy,
            "requested_steps": args.steps,
            "steps_run": steps_run,
            "done": bool(done),
            "total_reward": total_reward.tolist(),
            "tile_visited_count": list(env.unwrapped.tile_visited_count),
            "observation_shape": list(obs.shape),
            "telemetry_feature_names": env.unwrapped.telemetry_feature_names,
            "outputs": {
                "trace": str(out_dir / "rollout_trace.json"),
                "summary": str(out_dir / "summary.json"),
            },
        }

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
