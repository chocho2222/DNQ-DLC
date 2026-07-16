import argparse
import json
from itertools import combinations
from pathlib import Path

from dlc.evaluate import evaluate_pair
from dlc.policies import ModelPlannerPolicy, make_policy


def main():
    parser = argparse.ArgumentParser(
        description="Run a DLC-style round-robin tournament between trained state models."
    )
    parser.add_argument("--model-dir", default="outputs/state_dlc")
    parser.add_argument("--episodes", type=int, default=10)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--max-steps", type=int, default=1000)
    parser.add_argument("--planner-horizon", type=int, default=3)
    parser.add_argument("--planner-candidates", type=int, default=16)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--out", default="outputs/state_dlc/round_robin.json")
    args = parser.parse_args()

    model_dir = Path(args.model_dir)
    npz_paths = {
        path.stem: path
        for path in sorted(model_dir.glob("*.npz"))
        if path.stem in {
            "joint_transition_observer",
            "joint_transition",
            "individual_transition",
        }
    }
    pt_paths = {
        path.stem: path
        for path in sorted(model_dir.glob("*.pt"))
        if path.stem in {
            "joint_transition_observer",
            "joint_transition",
            "individual_transition",
        }
    }
    model_paths = pt_paths or npz_paths
    if len(model_paths) < 3:
        raise ValueError(f"expected three trained .pt or .npz model files in {model_dir}")

    use_torch_actor = bool(pt_paths)

    results = {}
    for pair_id, (name_a, name_b) in enumerate(combinations(model_paths.keys(), 2)):
        if use_torch_actor:
            policy_a = make_policy(
                str(model_paths[name_a]),
                seed=args.seed + pair_id,
                device=args.device,
            )
            policy_b = make_policy(
                str(model_paths[name_b]),
                seed=args.seed + 10_000 + pair_id,
                device=args.device,
            )
        else:
            policy_a = ModelPlannerPolicy(
                model_paths[name_a],
                seed=args.seed + pair_id,
                horizon=args.planner_horizon,
                candidates=args.planner_candidates,
            )
            policy_b = ModelPlannerPolicy(
                model_paths[name_b],
                seed=args.seed + 10_000 + pair_id,
                horizon=args.planner_horizon,
                candidates=args.planner_candidates,
            )
        results[f"{name_a}_vs_{name_b}"] = evaluate_pair(
            policy_a,
            policy_b,
            episodes=args.episodes,
            seed=args.seed + pair_id * args.episodes,
            max_steps=args.max_steps,
        )

    output = {
        "model_dir": str(model_dir),
        "episodes_per_pairing": args.episodes,
        "seed": args.seed,
        "max_steps": args.max_steps,
        "planner_horizon": args.planner_horizon,
        "planner_candidates": args.planner_candidates,
        "device": args.device,
        "policy_execution": "torch_actor" if use_torch_actor else "numpy_model_planner",
        "pairings": results,
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
