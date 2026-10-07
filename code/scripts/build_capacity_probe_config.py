#!/usr/bin/env python
"""Build the admission-capacity probe configuration from the reported arm.

The submitted arm reads three opponent slots. The recorded probe that answers
"would two do?" on the submitted checkpoint can only move downward, because the
transition model has a fixed slot count baked into its input width. The
symmetric question ("is three enough when the field is dense?") needs a model
trained for more slots, and ``wm_k15_v5att`` is one: same episodes, same
optimiser, same attention pooling, five slots instead of three.

This script derives the probe by editing ``policy``, ``max_neighbors`` and
``neighbor_selection_mode`` on the reported arm and touching nothing else, so
every planner weight, shield setting and quality term is the one of the
submitted evaluation. The reported arm itself is not duplicated here; it is
already recorded as ``main_final_20260922``.

Usage:
    python3 scripts/build_capacity_probe_config.py \
        --base configs/tits_main_comparison_20260922_final.json \
        --out configs/tits_capacity_probe_20260923.json

    python3 scripts/build_capacity_probe_config.py \
        --base configs/tits_main_comparison_20260922_final.json \
        --policy <checkpoint.pt> --arm prio_k5:5:nearest --prefix rank_prio \
        --study tits_rank_channel_probe_20260923 \
        --out configs/tits_rank_channel_probe_20260923.json
"""
import argparse
import json
from pathlib import Path

REPORTED = "ours_dnq_dlc"
FIVE_SLOT = ("outputs/tits_dynamic_graph_expanded/corrected_v2_20260920/"
             "wm_k15_v5att/graph_risk_dlc_world.graphworld.pt")

# name -> (max_neighbors, neighbor_selection_mode)
ARMS = {
    "cap_five_near_k3": (3, "nearest"),
    "cap_five_near_k5": (5, "nearest"),
    "cap_five_inter_k3": (3, "interaction"),
    "cap_five_inter_k5": (5, "interaction"),
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--policy", default=FIVE_SLOT,
                        help="checkpoint the probe arms load")
    parser.add_argument("--study", default="tits_capacity_probe_20260923")
    parser.add_argument("--note", default=None)
    parser.add_argument("--arm", action="append", default=[],
                        help="NAME:SLOTS:MODE, repeatable; overrides the built-in grid")
    args = parser.parse_args()

    base = json.loads(Path(args.base).read_text())
    template = [a for a in base["algorithms"] if a["name"] == REPORTED]
    if len(template) != 1:
        raise SystemExit(f"expected one {REPORTED} entry, found {len(template)}")
    template = template[0]

    grid = dict(ARMS)
    if args.arm:
        grid = {}
        for spec in args.arm:
            name, slots, mode = spec.split(":")
            grid[name] = (int(slots), mode)
    arms = []
    for name, (slots, mode) in sorted(grid.items()):
        arm = json.loads(json.dumps(template))
        arm["name"] = name
        arm["label_cn"] = f"DNQ-DLC five-slot ({mode}, k={slots})"
        arm["policy"] = args.policy
        arm["max_neighbors"] = slots
        arm["neighbor_selection_mode"] = mode
        arms.append(arm)

    config = {
        "study": args.study,
        "note": args.note or (
            "Admission-capacity probe on a five-slot world model. Only the "
            "checkpoint, the runtime slot budget and the ranking rule differ "
            "from the reported arm; every planner weight is inherited from "
            "configs/tits_main_comparison_20260922_final.json."),
        "dynamic_graph": base["dynamic_graph"],
        "algorithms": arms,
    }
    Path(args.out).write_text(json.dumps(config, indent=2) + "\n")
    print(f"wrote {args.out} with arms: {', '.join(a['name'] for a in arms)}")


if __name__ == "__main__":
    main()
