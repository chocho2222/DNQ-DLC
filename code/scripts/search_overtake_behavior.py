#!/usr/bin/env python
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
from pathlib import Path

import numpy as np

from dlc.policies import MixedPolicy, make_policy
from dlc.rollout import make_env


def load_policy(model_dir, name, seed, device, blend, unsafe_blend, base_policy):
    return make_policy(
        str(Path(model_dir) / f"{name}.pt"),
        seed=seed,
        device=device,
        safe=True,
        safe_blend=blend,
        unsafe_blend=unsafe_blend,
        safe_base_policy=base_policy,
    )


def run_trial(args, seed, observer_agent, blend, unsafe_blend):
    model_dir = Path(args.model_dir)
    env = make_env(num_agents=2, seed=seed, observation_type="telemetry")

    observer = load_policy(
        model_dir,
        "joint_transition_observer",
        seed + 10_000 * observer_agent,
        args.device,
        blend,
        unsafe_blend,
        "overtake_track",
    )
    baseline = load_policy(
        model_dir,
        "individual_transition",
        seed + 10_000 * (1 - observer_agent),
        args.device,
        blend,
        unsafe_blend,
        "track_follow",
    )
    policies = [None, None]
    policies[observer_agent] = observer
    policies[1 - observer_agent] = baseline
    policy = MixedPolicy(policies)

    total_reward = np.zeros(2, dtype=np.float64)
    grass_steps = np.zeros(2, dtype=np.float64)
    progress_delta = []
    tiles_delta = []
    lateral = []

    try:
        obs = env.reset()
        policy.reset()
        for step in range(args.steps):
            action = policy.act(env, obs)
            obs, reward, done, _ = env.step(action)
            total_reward += reward
            grass_steps += obs[:, 15] > 0.5
            observer_progress = obs[observer_agent, 8]
            baseline_progress = obs[1 - observer_agent, 8]
            progress_delta.append(float(observer_progress - baseline_progress))
            tiles = env.unwrapped.tile_visited_count
            tiles_delta.append(int(tiles[observer_agent] - tiles[1 - observer_agent]))
            lateral.append(np.abs(obs[:, 12]).tolist())
            if done:
                break
        steps_run = step + 1
        tiles = list(env.unwrapped.tile_visited_count)
    finally:
        env.close()

    progress_delta = np.asarray(progress_delta, dtype=np.float64)
    lateral = np.asarray(lateral, dtype=np.float64)
    observer_reward = float(total_reward[observer_agent])
    baseline_reward = float(total_reward[1 - observer_agent])
    observer_tiles = int(tiles[observer_agent])
    baseline_tiles = int(tiles[1 - observer_agent])
    observer_grass = float(grass_steps[observer_agent] / max(steps_run, 1))
    baseline_grass = float(grass_steps[1 - observer_agent] / max(steps_run, 1))
    overtake_event = bool(np.any(progress_delta > args.overtake_margin))
    start_near_or_behind = bool(progress_delta[0] <= args.start_margin)
    final_ahead = bool(progress_delta[-1] > args.final_margin or observer_tiles > baseline_tiles)

    score = (
        3.0 * (observer_tiles - baseline_tiles)
        + 0.08 * (observer_reward - baseline_reward)
        + 15.0 * int(overtake_event)
        + 8.0 * int(final_ahead)
        - 20.0 * observer_grass
    )

    return {
        "seed": seed,
        "observer_agent": observer_agent,
        "blend": blend,
        "unsafe_blend": unsafe_blend,
        "steps": steps_run,
        "observer_reward": observer_reward,
        "baseline_reward": baseline_reward,
        "observer_tiles": observer_tiles,
        "baseline_tiles": baseline_tiles,
        "observer_grass_rate": observer_grass,
        "baseline_grass_rate": baseline_grass,
        "observer_lateral_mean": float(lateral[:, observer_agent].mean()),
        "baseline_lateral_mean": float(lateral[:, 1 - observer_agent].mean()),
        "progress_delta_start": float(progress_delta[0]),
        "progress_delta_min": float(progress_delta.min()),
        "progress_delta_max": float(progress_delta.max()),
        "progress_delta_final": float(progress_delta[-1]),
        "start_near_or_behind": start_near_or_behind,
        "overtake_event": overtake_event,
        "final_ahead": final_ahead,
        "score": float(score),
    }


def main():
    parser = argparse.ArgumentParser(description="Search for visible overtake behavior.")
    parser.add_argument("--model-dir", default="outputs/torch_dlc_experiment/seed_0/models")
    parser.add_argument("--seeds", default="1,2,3,4,5,7,9,11,13,15,21,34,42,55,88,115,150,175,188,233")
    parser.add_argument("--observer-agents", default="0,1")
    parser.add_argument("--blends", default="0.55:0.95,0.70:0.98,0.82:0.99")
    parser.add_argument("--steps", type=int, default=900)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--overtake-margin", type=float, default=0.03)
    parser.add_argument("--start-margin", type=float, default=0.02)
    parser.add_argument("--final-margin", type=float, default=0.02)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--out", default="outputs/torch_dlc_experiment/gifs/overtake_behavior_search.json")
    args = parser.parse_args()

    seeds = [int(item.strip()) for item in args.seeds.split(",") if item.strip()]
    observer_agents = [int(item.strip()) for item in args.observer_agents.split(",") if item.strip()]
    blends = []
    for item in args.blends.split(","):
        left, right = item.split(":")
        blends.append((float(left), float(right)))

    jobs = [
        (args, seed, observer_agent, blend, unsafe_blend)
        for blend, unsafe_blend in blends
        for observer_agent in observer_agents
        for seed in seeds
    ]
    results = []

    if args.workers > 1:
        with ProcessPoolExecutor(max_workers=args.workers) as executor:
            futures = {
                executor.submit(run_trial, *job): job
                for job in jobs
            }
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                print(json.dumps(result), flush=True)
    else:
        for job in jobs:
            result = run_trial(*job)
            results.append(result)
            print(json.dumps(result), flush=True)

    results.sort(key=lambda item: item["score"], reverse=True)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps({"best": results[:10], "out": str(out_path)}, indent=2))


if __name__ == "__main__":
    main()
