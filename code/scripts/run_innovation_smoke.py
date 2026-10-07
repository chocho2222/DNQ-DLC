#!/usr/bin/env python
import argparse
import json
from pathlib import Path

import numpy as np

from dlc.graph_policy import make_untrained_graph_bundle
from dlc.policies import make_policy
from dlc.rollout import make_env


def main():
    parser = argparse.ArgumentParser(description="Smoke-test graph policy and safety shield wiring.")
    parser.add_argument("--num-agents", type=int, default=4)
    parser.add_argument("--seed", type=int, default=3)
    parser.add_argument("--steps", type=int, default=80)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--out-dir", default="outputs/innovation_smoke")
    args = parser.parse_args()

    env = make_env(
        num_agents=args.num_agents,
        seed=args.seed,
        observation_type="telemetry_dynamic",
        start_order=[2 * agent_id for agent_id in range(args.num_agents)],
        line_spacing=22,
        lateral_spacing=0.0,
    )
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    model_path = out_dir / "untrained.graph.pt"

    try:
        obs = env.reset()
        use_slot_mask = (obs.shape[1] - 17) % 8 == 0
        bundle = make_untrained_graph_bundle(
            obs_dim=obs.shape[1],
            seed=args.seed,
            use_slot_mask=use_slot_mask,
            slot_feature_dim=7,
        )
        bundle.save(model_path)
        policy = make_policy(
            str(model_path),
            device=args.device,
            safe=True,
            safe_blend=0.75,
            unsafe_blend=1.0,
            neighbor_mode="dynamic",
            max_neighbors=(obs.shape[1] - 17) // (8 if use_slot_mask else 7),
        )
        policy.reset()
        total_reward = np.zeros(args.num_agents, dtype=np.float64)
        grass_steps = np.zeros(args.num_agents, dtype=np.float64)
        done = False
        for step in range(args.steps):
            action = policy.act(env, obs)
            obs, reward, done, _ = env.step(action)
            total_reward += reward
            grass_steps += obs[:, 15] > 0.5
            if done:
                break
        output = {
            "status": "PASS",
            "model_path": str(model_path),
            "policy": policy.name,
            "steps_run": step + 1,
            "done": bool(done),
            "tile_visited_count": list(env.unwrapped.tile_visited_count),
            "grass_rate": (grass_steps / max(step + 1, 1)).tolist(),
            "total_reward": total_reward.tolist(),
            "obs_dim": int(obs.shape[1]),
        }
    finally:
        env.close()

    (out_dir / "innovation_smoke_summary.json").write_text(
        json.dumps(output, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
