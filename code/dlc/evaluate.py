import argparse
import json
from pathlib import Path

import numpy as np

from dlc.policies import MixedPolicy, make_policy
from dlc.rollout import make_env, run_episode


def evaluate_pair(policy_a, policy_b, episodes, seed, max_steps):
    wins = np.zeros(2, dtype=np.int64)
    scores = []
    episode_summaries = []

    for episode in range(episodes):
        env = make_env(num_agents=2, seed=seed + episode, observation_type="telemetry")
        policy = MixedPolicy([policy_a, policy_b])
        try:
            result = run_episode(env, policy, max_steps=max_steps)
        finally:
            env.close()

        total_reward = result["total_reward"]
        winner = int(np.argmax(total_reward))
        wins[winner] += 1
        scores.append(total_reward.tolist())
        episode_summaries.append(
            {
                "episode": episode,
                "winner": winner,
                "steps": result["steps"],
                "done": result["done"],
                "total_reward": total_reward.tolist(),
                "tile_visited_count": result["tile_visited_count"],
            }
        )

    scores_array = np.asarray(scores, dtype=np.float64)
    return {
        "episodes": episodes,
        "wins": wins.tolist(),
        "win_ratio": (wins / max(episodes, 1)).tolist(),
        "mean_score": scores_array.mean(axis=0).tolist(),
        "episodes_detail": episode_summaries,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate telemetry policies in a DLC-style pairwise tournament."
    )
    parser.add_argument("--policy-a", default="track_follow")
    parser.add_argument("--policy-b", default="random")
    parser.add_argument("--episodes", type=int, default=10)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--max-steps", type=int, default=1000)
    parser.add_argument("--out", default="outputs/eval_pair.json")
    args = parser.parse_args()

    policy_a = make_policy(args.policy_a, seed=args.seed)
    policy_b = make_policy(args.policy_b, seed=args.seed + 10_000)
    result = evaluate_pair(policy_a, policy_b, args.episodes, args.seed, args.max_steps)
    result.update(
        {
            "policy_a": args.policy_a,
            "policy_b": args.policy_b,
            "seed": args.seed,
            "max_steps": args.max_steps,
        }
    )

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

