#!/usr/bin/env python
"""Write main-comparison configs that vary the DLC baseline's world-model draw.

The matched retrain keeps two training seeds per model class and field size and
selects one by held-out one-step error plus a closed-loop drive check. The
published main comparison loads the selected seed at every field size, which is
one draw of a recipe that has two. This script rewrites the ``policy_by_agents``
field of the three DLC arms for a named draw so that the endpoint comparison can
be reported over draws on the same footing as the proposed controller, whose
five world-model draws are already released.

Draws
  A  the published selection (identity, written for completeness)
  B  the complement of the published selection at every field size
  C  seeds (4, 6, 8, 10) = (0, 0, 1, 1) for every model class
  D  seeds (4, 6, 8, 10) = (1, 1, 0, 0) for every model class

Across A to D each field size sees each candidate seed twice.

Usage:
    python3 scripts/build_dlc_draw_config.py \
        --matched-config configs/tits_main_comparison_20260922_final.json \
        --manifest-dir outputs/.../dlc_matched_stable_20260922 \
        --draw B --out configs/tits_main_comparison_20260922_drawB.json
"""

import argparse
import json
from pathlib import Path

ARM_MODEL_TYPES = {
    "dlc_individual_transition": "individual_transition",
    "dlc_joint_transition": "joint_transition",
    "dlc_joint_transition_observer": "joint_transition_observer",
}
SCALES = ("4", "6", "8", "10")
FIXED_PATTERNS = {
    "C": {"4": 0, "6": 0, "8": 1, "10": 1},
    "D": {"4": 1, "6": 1, "8": 0, "10": 0},
}


def candidate_path(manifest_dir, scale, model_type, seed):
    return str(manifest_dir / f"{model_type}_n{scale}_seed{seed}.pt")


def seed_choices(manifest_dir):
    """Seeds kept by the retrain, per scale and model class."""
    choices = {}
    for scale in SCALES:
        path = manifest_dir / f"retrain_manifest_n{scale}.json"
        if not path.exists():
            raise SystemExit(f"missing retrain manifest {path}")
        record = json.loads(path.read_text(encoding="utf-8"))["scales"][scale]
        for model_type, entry in record["variants"].items():
            seeds = sorted(candidate.get("seed") for candidate in entry.get("candidates", []))
            choices.setdefault(model_type, {})[scale] = {
                "seeds": seeds,
                "selected": entry["selected_seed"],
            }
    return choices


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matched-config", required=True)
    parser.add_argument("--manifest-dir", required=True)
    parser.add_argument("--draw", required=True, choices=("A", "B", "C", "D"))
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    config = json.loads(Path(args.matched_config).read_text(encoding="utf-8"))
    manifest_dir = Path(args.manifest_dir)
    choices = seed_choices(manifest_dir)

    assignment = {}
    for model_type, per_scale in choices.items():
        assignment[model_type] = {}
        for scale in SCALES:
            seeds = per_scale[scale]["seeds"]
            selected = per_scale[scale]["selected"]
            if len(seeds) != 2:
                raise SystemExit(f"{model_type} n{scale}: expected two candidates, got {seeds}")
            if args.draw == "A":
                seed = selected
            elif args.draw == "B":
                seed = next(s for s in seeds if s != selected)
            else:
                seed = FIXED_PATTERNS[args.draw][scale]
            if seed not in seeds:
                raise SystemExit(f"{model_type} n{scale}: seed {seed} not among {seeds}")
            assignment[model_type][scale] = seed

    for item in config["algorithms"]:
        model_type = ARM_MODEL_TYPES.get(item["name"])
        if not model_type:
            continue
        item["policy_by_agents"] = {
            scale: candidate_path(manifest_dir, scale, model_type, assignment[model_type][scale])
            for scale in SCALES
        }
        item["matched_retrain_seed"] = dict(assignment[model_type])
        item["matched_retrain_draw"] = args.draw

    config["dlc_arm_draw"] = {
        "draw": args.draw,
        "seeds_by_model_type": assignment,
        "note": "DLC baseline world-model draws; A is the published selection.",
    }
    config["study"] = config.get("study", "tits_main_comparison") + f"_draw{args.draw}"
    config["note"] = (
        "Main-comparison replica with the DLC baseline world-model draw set to "
        f"{args.draw}. Identical to the published configuration in every other respect."
    )
    Path(args.out).write_text(json.dumps(config, indent=1), encoding="utf-8")
    print(json.dumps({"out": args.out, "draw": args.draw,
                      "seeds": assignment}, indent=1))


if __name__ == "__main__":
    main()
