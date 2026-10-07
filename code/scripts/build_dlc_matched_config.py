#!/usr/bin/env python
"""Write the main-comparison config that points the DLC arms at matched checkpoints.

The matched retrain produces one checkpoint per model class and field size, and
records the seed chosen by held-out one-step error plus a closed-loop drive
check. This script copies a base comparison config and fills the
``policy_by_agents`` field of each DLC arm from those records, so a run at field
size n loads the checkpoint trained for n.

Usage:
    python3 scripts/build_dlc_matched_config.py \
        --base configs/tits_main_comparison_20260921.json \
        --manifest-dir outputs/.../dlc_matched_20260921 \
        --out configs/tits_main_comparison_20260921_dlcmatched.json
"""

import argparse
import json
from pathlib import Path

ARM_MODEL_TYPES = {
    "dlc_individual_transition": "individual_transition",
    "dlc_joint_transition": "joint_transition",
    "dlc_joint_transition_observer": "joint_transition_observer",
}


def selected_mse(variant_record):
    """Held-out error of the seed that was actually selected, not of the first."""
    seed = variant_record.get("selected_seed")
    for candidate in variant_record.get("candidates", []):
        if candidate.get("seed") == seed:
            return candidate.get("held_out_next_obs_mse")
    return variant_record.get("candidates", [{}])[0].get("held_out_next_obs_mse")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True)
    parser.add_argument("--manifest-dir", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--pack-neighbors", type=int, default=3)
    args = parser.parse_args()

    base = json.loads(Path(args.base).read_text(encoding="utf-8"))
    manifest_dir = Path(args.manifest_dir)
    by_scale = {}
    drive = {}
    for scale in ("4", "6", "8", "10"):
        path = manifest_dir / f"retrain_manifest_n{scale}.json"
        if not path.exists():
            continue
        record = json.loads(path.read_text(encoding="utf-8"))["scales"][scale]
        by_scale[scale] = record
        drive[scale] = {variant: entry["drive_check"]
                        for variant, entry in record["variants"].items()}

    missing = [scale for scale in ("4", "6", "8", "10") if scale not in by_scale]
    if missing:
        raise SystemExit(f"no retrain manifest for scales {missing}")

    for item in base["algorithms"]:
        model_type = ARM_MODEL_TYPES.get(item["name"])
        if not model_type:
            continue
        item["policy_by_agents"] = {
            scale: by_scale[scale]["variants"][model_type]["selected_path"] for scale in by_scale
        }
        item["pack_neighbors"] = int(args.pack_neighbors)
        item["matched_retrain_seed"] = {
            scale: by_scale[scale]["variants"][model_type]["selected_seed"] for scale in by_scale
        }
        item["matched_retrain_held_out_mse"] = {
            scale: selected_mse(by_scale[scale]["variants"][model_type])
            for scale in by_scale
        }
        item["matched_retrain_drive_check"] = {
            scale: by_scale[scale]["variants"][model_type]["drive_check"] for scale in by_scale
        }

    base["study"] = base.get("study", "tits_main_comparison") + "_dlcmatched"
    base["note"] = (
        "Main comparison with the three DLC world-model baselines retrained under the "
        "proposed protocol (same packed dynamic-neighbour observation, same expert episodes, "
        "same 40000 world-model steps at batch size 512, actor scored on the controlled row "
        "only) instead of the archived two-agent 200-update checkpoints, whose actors brake "
        "continuously. Each DLC arm loads the checkpoint trained for the field size of the run."
    )
    base["dlc_matched_drive_check"] = drive
    Path(args.out).write_text(json.dumps(base, indent=1), encoding="utf-8")
    print(json.dumps({"out": args.out, "scales": sorted(by_scale),
                      "drive_check": drive}, indent=2))


if __name__ == "__main__":
    main()
