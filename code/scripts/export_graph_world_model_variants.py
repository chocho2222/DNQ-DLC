#!/usr/bin/env python
import argparse
import json
from pathlib import Path

import torch


VARIANTS = {
    "balanced": {
        "risk_weight": 1.25,
        "uncertainty_weight": 0.25,
        "progress_weight": 1.75,
        "imitation_weight": 0.05,
        "planner_horizon": 3,
        "planner_candidates": 12,
        "planner_profile": "risk_progress_balanced",
    },
    "safety": {
        "risk_weight": 2.2,
        "uncertainty_weight": 0.45,
        "progress_weight": 1.35,
        "imitation_weight": 0.06,
        "planner_horizon": 4,
        "planner_candidates": 14,
        "planner_profile": "safety_heavy",
    },
    "fast": {
        "risk_weight": 1.0,
        "uncertainty_weight": 0.15,
        "progress_weight": 2.1,
        "imitation_weight": 0.035,
        "planner_horizon": 2,
        "planner_candidates": 10,
        "planner_profile": "fast_progress",
    },
}


def main():
    parser = argparse.ArgumentParser(description="Export planner-meta variants of a trained graph world model.")
    parser.add_argument("--source", default="multi_car_racing/outputs/paper_multicar_overtake_20260618/models/graph_risk_world_model/graph_risk_dlc_world.graphworld.pt")
    parser.add_argument("--out-dir", default="multi_car_racing/outputs/paper_multicar_overtake_20260618/models/graph_risk_world_model_variants")
    parser.add_argument("--variants", default="balanced,safety,fast")
    args = parser.parse_args()

    source = Path(args.source)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    data = torch.load(source, map_location="cpu", weights_only=False)
    manifest = {"source": str(source), "variants": {}}
    for name in [item.strip() for item in args.variants.split(",") if item.strip()]:
        if name not in VARIANTS:
            raise ValueError(f"unknown variant: {name}; choices={sorted(VARIANTS)}")
        variant = dict(data)
        meta = dict(data["meta"])
        meta.update(VARIANTS[name])
        meta["name"] = f"graph_risk_dlc_world_{name}"
        variant["meta"] = meta
        path = out_dir / f"graph_risk_dlc_world_{name}.graphworld.pt"
        torch.save(variant, path)
        manifest["variants"][name] = {"path": str(path), "meta_updates": VARIANTS[name]}
    manifest_path = out_dir / "variant_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
