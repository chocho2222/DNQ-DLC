#!/usr/bin/env python
"""Check that the selector-isolation datasets differ only in the packed slots.

The control reported for the dynamic-neighbourhood module compares three
transition models that see the same expert episodes under three different
admission rules. For the comparison to isolate the packing rule, the episodes
themselves have to be identical: same episode plan, same expert actions, same
reward, same risk. Only ``obs`` and ``next_obs`` may differ, and they have to
differ, otherwise the rule changed nothing.

This script asserts both directions and writes a JSON report. It is the
machine-checkable form of the claim the manuscript makes about the control.

Usage:
    python3 scripts/verify_selector_isolation_datasets.py \
        --source outputs/.../dataset_k15 \
        --arm fixed=outputs/.../dataset_k15_fixed3 \
        --arm nearest=outputs/.../dataset_k15_nearest3 \
        --out outputs/.../selector_isolation_dataset_check.json
"""
import argparse
import json
from pathlib import Path

import numpy as np

KEYS = ("action", "reward", "risk")


def episode_names(root):
    return sorted(p.name for p in (root / "raw").iterdir() if p.is_dir())


def load(root, name):
    return np.load(root / "raw" / name / "transitions.npz", allow_pickle=False)


def compare(a_root, b_root):
    names_a, names_b = episode_names(a_root), episode_names(b_root)
    same_plan = names_a == names_b
    episodes = min(len(names_a), len(names_b))
    identical_behaviour = 0
    identical_observations = 0
    max_obs_delta = 0.0
    max_behaviour_delta = 0.0
    for name in names_a[:episodes]:
        a, b = load(a_root, name), load(b_root, name)
        behaves = all(np.array_equal(a[k], b[k]) for k in KEYS)
        identical_behaviour += int(behaves)
        if behaves:
            for k in KEYS:
                max_behaviour_delta = max(max_behaviour_delta,
                                          float(np.abs(a[k].astype(np.float64)
                                                       - b[k].astype(np.float64)).max()))
        if np.array_equal(a["obs"], b["obs"]) and np.array_equal(a["next_obs"], b["next_obs"]):
            identical_observations += 1
        else:
            max_obs_delta = max(max_obs_delta,
                                float(np.abs(a["obs"] - b["obs"]).max()))
    return {
        "episodes": episodes,
        "episode_plan_identical": same_plan,
        "behaviour_identical_episodes": identical_behaviour,
        "max_behaviour_delta": max_behaviour_delta,
        "observation_identical_episodes": identical_observations,
        "max_observation_delta": max_obs_delta,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True,
                        help="dataset the episodes were recorded with")
    parser.add_argument("--arm", action="append", required=True,
                        help="NAME=DIR, repeatable")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    source = Path(args.source)
    arms = dict(spec.split("=", 1) for spec in args.arm)

    report = {"source": str(source.resolve()), "arms": {}, "pairs": {}}
    for name, path in arms.items():
        report["arms"][name] = str(Path(path).resolve())
    for name, path in arms.items():
        report["pairs"][f"source_vs_{name}"] = compare(source, Path(path))
    names = sorted(arms)
    for i, first in enumerate(names):
        for second in names[i + 1:]:
            report["pairs"][f"{first}_vs_{second}"] = compare(Path(arms[first]), Path(arms[second]))

    failures = []
    for key, row in report["pairs"].items():
        if not row["episode_plan_identical"]:
            failures.append(f"{key}: episode plan differs")
        if row["behaviour_identical_episodes"] != row["episodes"]:
            failures.append(f"{key}: expert behaviour differs on "
                            f"{row['episodes'] - row['behaviour_identical_episodes']} episodes")
    for name in names:
        row = report["pairs"][f"source_vs_{name}"]
        if row["observation_identical_episodes"] == row["episodes"]:
            failures.append(f"{name}: observation is identical to the source, the rule changed nothing")
    for key, row in report["pairs"].items():
        if key.startswith(tuple(names)) and row["observation_identical_episodes"] == row["episodes"]:
            failures.append(f"{key}: the two packings produce identical observations")

    report["status"] = "PASS" if not failures else "FAIL"
    report["failures"] = failures
    Path(args.out).write_text(json.dumps(report, indent=2) + "\n")
    print(f"{report['status']}: {len(report['pairs'])} comparisons, "
          f"{len(failures)} failure(s) -> {args.out}")
    for failure in failures:
        print("  " + failure)


if __name__ == "__main__":
    main()
