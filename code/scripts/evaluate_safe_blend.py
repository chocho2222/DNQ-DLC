#!/usr/bin/env python
import argparse
import json
from pathlib import Path

import numpy as np

from dlc.policies import MixedPolicy, make_policy
from dlc.rollout import make_env


def run_match(model_dir, seed, blend, unsafe_blend, steps, device):
    env = make_env(num_agents=2, seed=seed, observation_type="telemetry")
    policy0 = make_policy(
        str(model_dir / "joint_transition_observer.pt"),
        seed=seed,
        device=device,
        safe=True,
        safe_blend=blend,
        unsafe_blend=unsafe_blend,
    )
    policy1 = make_policy(
        str(model_dir / "individual_transition.pt"),
        seed=seed + 10_000,
        device=device,
        safe=True,
        safe_blend=blend,
        unsafe_blend=unsafe_blend,
    )
    policy = MixedPolicy([policy0, policy1])
    total = np.zeros(2, dtype=np.float64)
    grass_steps = np.zeros(2, dtype=np.float64)
    lateral = []
    progress_delta = []

    try:
        obs = env.reset()
        policy.reset()
        for step in range(steps):
            action = policy.act(env, obs)
            obs, reward, done, _ = env.step(action)
            total += reward
            grass_steps += obs[:, 15] > 0.5
            lateral.append(np.abs(obs[:, 12]))
            progress_delta.append(obs[0, 8] - obs[1, 8])
            if done:
                break
        steps_run = step + 1
        tile_visited_count = list(env.unwrapped.tile_visited_count)
    finally:
        env.close()

    lateral = np.asarray(lateral, dtype=np.float64)
    progress_delta = np.asarray(progress_delta, dtype=np.float64)
    return {
        "blend": blend,
        "unsafe_blend": unsafe_blend,
        "seed": seed,
        "steps": steps_run,
        "reward": total.tolist(),
        "tile_visited_count": tile_visited_count,
        "grass_rate": (grass_steps / max(steps_run, 1)).tolist(),
        "lateral_mean": lateral.mean(axis=0).tolist(),
        "progress_delta_start": float(progress_delta[0]),
        "progress_delta_end": float(progress_delta[-1]),
        "observer_ahead_gain": float(progress_delta[-1] - progress_delta[0]),
    }


def main():
    parser = argparse.ArgumentParser(description="Evaluate safe track blend settings.")
    parser.add_argument("--model-dir", default="outputs/torch_dlc_experiment/seed_0/models")
    parser.add_argument("--seeds", default="7,15,42,88,115,150,175")
    parser.add_argument("--blends", default="0.25:0.75,0.35:0.85,0.50:0.90,0.65:0.95")
    parser.add_argument("--steps", type=int, default=500)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--out", default="outputs/torch_dlc_experiment/gifs/safe_blend_sweep.json")
    args = parser.parse_args()

    model_dir = Path(args.model_dir)
    seeds = [int(item.strip()) for item in args.seeds.split(",") if item.strip()]
    blends = []
    for item in args.blends.split(","):
        left, right = item.split(":")
        blends.append((float(left), float(right)))

    results = []
    for blend, unsafe_blend in blends:
        for seed in seeds:
            result = run_match(model_dir, seed, blend, unsafe_blend, args.steps, args.device)
            results.append(result)
            print(json.dumps(result), flush=True)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
