import argparse
import json
from pathlib import Path

from dlc.policies import make_policy
from dlc.rollout import make_env, run_episode
from dlc.state_models import fit_state_models


MODEL_TYPES = [
    "joint_transition_observer",
    "joint_transition",
    "individual_transition",
]


def collect_episodes(episodes, seed, max_steps, behavior_policy):
    collected = []
    for episode in range(episodes):
        env = make_env(num_agents=2, seed=seed + episode, observation_type="telemetry")
        policy = make_policy(behavior_policy, seed=seed + episode)
        try:
            result = run_episode(env, policy, max_steps=max_steps)
        finally:
            env.close()
        collected.append(result)
    return collected


def main():
    parser = argparse.ArgumentParser(
        description="Train telemetry-state DLC model variants from rollout data."
    )
    parser.add_argument("--episodes", type=int, default=5)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--max-steps", type=int, default=200)
    parser.add_argument("--behavior-policy", choices=["random", "track_follow"], default="track_follow")
    parser.add_argument("--out-dir", default="outputs/state_dlc")
    parser.add_argument("--l2", type=float, default=1e-3)
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    episodes = collect_episodes(
        episodes=args.episodes,
        seed=args.seed,
        max_steps=args.max_steps,
        behavior_policy=args.behavior_policy,
    )
    first_obs = episodes[0]["trajectory"][0]["obs"]
    num_agents, feature_dim = first_obs.shape

    model_paths = {}
    for model_type in MODEL_TYPES:
        bundle = fit_state_models(
            episodes,
            model_type=model_type,
            num_agents=num_agents,
            feature_dim=feature_dim,
            l2=args.l2,
        )
        model_path = out_dir / f"{model_type}.npz"
        bundle.save(model_path)
        model_paths[model_type] = str(model_path)

    summary = {
        "seed": args.seed,
        "episodes": args.episodes,
        "max_steps": args.max_steps,
        "behavior_policy": args.behavior_policy,
        "num_agents": num_agents,
        "feature_dim": feature_dim,
        "transitions": sum(len(ep["trajectory"]) for ep in episodes),
        "model_paths": model_paths,
    }
    summary_path = out_dir / "train_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

