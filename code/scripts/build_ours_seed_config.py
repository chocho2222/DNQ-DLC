#!/usr/bin/env python
"""Build the evaluation config for the proposed controller under several
world-model training seeds.

The main comparison evaluates the proposed controller from one world-model
checkpoint. The three continuous-control references are reported as means over
five training seeds, so the same treatment is applied here: the single
``ours_dnq_dlc`` entry is replaced by one entry per world-model seed, named
``ours_dnq_dlc_seed<seed>``. Every other algorithm record is copied unchanged.

Usage:
    python -m scripts.build_ours_seed_config \
        --base configs/tits_main_comparison_20260922_final.json \
        --checkpoint 13=outputs/.../wm_k15_sb_all_v4matt/graph_risk_dlc_world.graphworld.pt \
        --checkpoint 21=outputs/.../wm_k15_sb_all_v4matt_seed21/graph_risk_dlc_world.graphworld.pt \
        --out configs/tits_ours_seedspread_20260928.json
"""
import argparse
import json
from pathlib import Path

OURS = "ours_dnq_dlc"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--checkpoint", action="append", required=True,
                        metavar="SEED=PATH",
                        help="world-model training seed and its checkpoint")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    mapping = []
    for item in args.checkpoint:
        seed, _, path = item.partition("=")
        if not path:
            raise SystemExit(f"--checkpoint expects SEED=PATH, got {item!r}")
        mapping.append((int(seed), path))

    config = json.loads(Path(args.base).read_text(encoding="utf-8"))
    template = next(a for a in config["algorithms"] if a.get("name") == OURS)
    kept = [a for a in config["algorithms"] if a.get("name") != OURS]

    added = []
    for seed, path in sorted(mapping):
        entry = dict(template)
        entry["name"] = f"{OURS}_seed{seed}"
        entry["label_cn"] = f"DNQ-DLC (world-model seed {seed})"
        entry["policy"] = path
        entry["world_model_train_seed"] = seed
        added.append(entry)

    config["algorithms"] = added + kept
    config["note"] = (str(config.get("note", "")) +
                      " | The proposed controller is repeated once per world-model "
                      "training seed so that its row carries the same seed spread as "
                      "the continuous-control rows.")
    Path(args.out).write_text(json.dumps(config, indent=2, sort_keys=False),
                              encoding="utf-8")
    missing = [a["policy"] for a in added if not Path(a["policy"]).exists()]
    print(json.dumps({"entries": len(added), "kept": len(kept),
                      "missing_checkpoints": missing, "out": args.out}, indent=2))


if __name__ == "__main__":
    main()
