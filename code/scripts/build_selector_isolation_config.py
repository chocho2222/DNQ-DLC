#!/usr/bin/env python
"""Build the dynamic-neighbourhood selector-isolation configurations.

The reported arm observes the three opponents its interaction ranking admits,
and the transition model that consumes those slots is trained on the same
packing rule. A reviewer can therefore ask whether the ranking itself carries
the gain, or whether any three-opponent window of the field would train an
equally good model. This script derives the two control arms that answer that
question on the same budget and the same observation interface.

All three arms share one checkpoint interface (three masked seven-feature
slots), one episode set, one optimiser recipe and one planner configuration.
Only the rule that decides which opponents occupy the three slots differs:

    interaction  the submitted rule: a weighted combination of ahead,
                 alongside, rear-pressure and closing-speed terms
    nearest      the three opponents with the smallest current distance
    fixed        the first three live opponents in the environment's own
                 identity order, i.e. no dependence on geometry at all

Each arm is trained from the episodes it produced under its own packing rule,
because the observation the model sees has to match the observation the policy
will feed it at run time. The planner, shield, quality proposal and every
weight are inherited unchanged from the reported arm.

Usage:
    python3 scripts/build_selector_isolation_config.py \
        --base configs/tits_main_comparison_20260922_final.json \
        --out configs/tits_selector_isolation_20260926.json
"""
import argparse
import json
from pathlib import Path

REPORTED = "ours_dnq_dlc"
DATA_ROOT = "outputs/tits_dynamic_graph_expanded/corrected_v2_20260920"

# name -> (checkpoint directory under DATA_ROOT, selection mode, label)
ARMS = {
    "ours_dnq_dlc_int3": (
        "wm_k15_sb_all_v4matt", "interaction",
        "DNQ-DLC (dynamic, interaction)"),
    "ours_dnq_dlc_nearest3": (
        "wm_k15_nearest3", "nearest",
        "DNQ-DLC (dynamic, nearest)"),
    "ours_dnq_dlc_fixed3": (
        "wm_k15_fixed3", "fixed",
        "DNQ-DLC (fixed identity slots)"),
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--data-root", default=DATA_ROOT)
    parser.add_argument("--study", default="tits_selector_isolation_20260926")
    parser.add_argument("--note", default=None)
    args = parser.parse_args()

    base = json.loads(Path(args.base).read_text())
    template = [a for a in base["algorithms"] if a["name"] == REPORTED]
    if len(template) != 1:
        raise SystemExit(f"expected one {REPORTED} entry, found {len(template)}")
    template = template[0]

    arms = []
    for name, (checkpoint_dir, mode, label) in sorted(ARMS.items()):
        arm = json.loads(json.dumps(template))
        arm["name"] = name
        arm["label_cn"] = label
        arm["policy"] = (f"{args.data_root}/{checkpoint_dir}/"
                         "graph_risk_dlc_world.graphworld.pt")
        arm["neighbor_selection_mode"] = mode
        arms.append(arm)

    config = {
        "study": args.study,
        "note": args.note or (
            "Selector isolation. The three arms differ only in the rule that "
            "fills the three observation slots (interaction ranking, nearest "
            "distance, fixed identity order); each is trained on the episodes "
            "its own rule produced. Planner, shield, quality proposal and all "
            "weights are inherited from "
            "configs/tits_main_comparison_20260922_final.json."),
        "dynamic_graph": base["dynamic_graph"],
        "algorithms": arms,
    }
    Path(args.out).write_text(json.dumps(config, indent=2) + "\n")
    print(f"wrote {args.out} with arms: {', '.join(a['name'] for a in arms)}")


if __name__ == "__main__":
    main()
