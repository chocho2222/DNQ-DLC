#!/usr/bin/env python
"""Build the evaluation config for the strictly retrained RL baselines.

Takes a study config, drops its three single-seed RL entries and replaces them
with one entry per (algorithm, training seed) in the strict run, named
``<family>_seed<seed>`` so that a per-seed summary can be produced without
pseudo-replicating evaluation cases.

Usage:
    python -m scripts.build_rl_strict_config --base configs/x.json \
        --checkpoint-dir outputs/.../rl_baselines_strict_20260926 \
        --seeds 2026001..2026005 --out configs/y.json
"""
import argparse
import json
from pathlib import Path

FAMILIES = [("ppo_continuous", "ppo", "PPO"),
            ("sac_continuous", "sac", "SAC"),
            ("td3_continuous", "td3", "TD3")]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--checkpoint-dir", required=True)
    parser.add_argument("--seeds", default="2026001,2026002,2026003,2026004,2026005")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    seeds = [s.strip() for s in args.seeds.split(",") if s.strip()]
    config = json.loads(Path(args.base).read_text(encoding="utf-8"))
    kept = [a for a in config["algorithms"]
            if a.get("kind") != "rl_baseline" and a.get("name") not in
            {name for name, _, _ in FAMILIES}]
    added = []
    for name, family, label in FAMILIES:
        for seed in seeds:
            model = Path(args.checkpoint_dir) / name / f"seed{seed}" / f"{name}.sb3.zip"
            added.append({
                "name": f"{family}_seed{seed}",
                "label_cn": f"{label} (seed {seed})",
                "policy": str(model),
                "neighbor_mode": "fixed",
                "max_neighbors": None,
                "kind": "rl_baseline",
                "strict_retrain": {
                    "total_timesteps": 500000,
                    "training_seed": int(seed),
                    "observation_packing": "runtime_interaction_packing_to_3_slots",
                },
            })
    config["algorithms"] = kept + added
    config["note"] = (str(config.get("note", "")) +
                      " | RL entries replaced by the 500k-step, five-seed strict retrain "
                      "evaluated on the same 48 cases.")
    Path(args.out).write_text(json.dumps(config, indent=2, sort_keys=False), encoding="utf-8")
    missing = [a["policy"] for a in added if not Path(a["policy"]).exists()]
    print(json.dumps({"entries": len(added), "kept": len(kept),
                      "missing_checkpoints": len(missing), "out": args.out}, indent=2))


if __name__ == "__main__":
    main()
