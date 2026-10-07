#!/usr/bin/env python
"""Generate the E6 ablation configs as single-variable edits of a base config.

Each ablation removes exactly one component of the frozen method configuration
and keeps every other field byte-identical, so a difference between two arms is
attributable to the component that was removed. The previous set was written by
hand and drifted: two arms silently changed the neighbour mode and the corridor
mode as well.

Usage:
    python3 scripts/build_e6_ablation_configs.py --base configs/final.json
"""
import argparse
import copy
import json
from pathlib import Path

ABLATIONS = {
    "no_dynamic_graph": {
        "label": "w/o dynamic relevance neighbourhood",
        "note": "the ego sees a fixed neighbour set instead of the interaction-ranked one",
        "overrides": {"neighbor_selection_mode": "fixed"},
    },
    "no_world_model": {
        "label": "w/o action-conditioned world model",
        "note": "candidate scoring uses the one-step proxy instead of an imagined rollout",
        "overrides": {"world_model_mode": "no_world_model"},
    },
    "no_quality_proposal": {
        "label": "w/o quality proposal actor",
        "note": "the candidate pool loses the quality actor's proposal",
        "overrides": {"quality_proposal_path": None, "quality_planner_mode": "proposal_only"},
    },
    "no_risk_head": {
        "label": "w/o risk head in the score",
        "note": "predicted risk no longer enters the candidate score",
        "overrides": {"planner_risk_weight": 0.0},
    },
    "no_safety_shield": {
        "label": "w/o safety shield and corridor feasibility",
        "note": "guard penalty, corridor feasibility and their feasibility ordering are removed",
        "overrides": {"guard_penalty_weight": 0.0, "hard_safety_shield": False,
                      "shield_mode": "off", "corridor_feasibility": False},
    },
    "no_liveness": {
        "label": "w/o dynamic-feasibility liveness term",
        "note": "nothing stops the planner from settling on a standstill",
        "overrides": {"planner_liveness_weight": 0.0},
    },
    "no_clearance": {
        "label": "w/o lateral-clearance feasibility",
        "note": "candidates that squeeze past within one vehicle width are not marked infeasible",
        "overrides": {"clearance_feasibility": False},
    },
    "no_overtake_candidates": {
        "label": "w/o overtaking-aware candidates",
        "note": "the overtaking score and the hand-crafted lateral candidates are removed",
        "overrides": {"overtake_aware_planner": False, "use_handcrafted_candidates": False},
    },
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--out-dir", default="configs")
    parser.add_argument("--prefix", default="e6_")
    args = parser.parse_args()

    base = json.load(open(args.base))
    template = None
    for algorithm in base["algorithms"]:
        if algorithm.get("kind", "").startswith(("runtime", "graph")) or "quality_proposal_path" in algorithm:
            template = algorithm
    if template is None:
        raise SystemExit("no method entry found in the base config")

    written = []
    for name, spec in ABLATIONS.items():
        config = copy.deepcopy(base)
        entry = copy.deepcopy(template)
        for field, value in spec["overrides"].items():
            if value is None and field not in entry:
                continue
            entry[field] = value
        entry["name"] = name
        entry["label_cn"] = spec["label"]
        entry["ablation_note"] = spec["note"]
        config["study"] = f"{base.get('study', 'base')}::{name}"
        config["note"] = f"Ablation of {base.get('study', 'base')}: {spec['note']}."
        config["algorithms"] = [a for a in config["algorithms"] if a is not entry]
        config["algorithms"] = [a for a in config["algorithms"]
                                if a.get("name") != template["name"]] + [entry]
        path = Path(args.out_dir) / f"{args.prefix}{name}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        json.dump(config, open(path, "w"), indent=2, ensure_ascii=False)
        written.append(path)
    for path in written:
        print(path)


if __name__ == "__main__":
    main()
