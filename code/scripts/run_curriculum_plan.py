#!/usr/bin/env python
import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Print the saved multi-car curriculum plan.")
    parser.add_argument("--config", default="configs/curriculum_multicar.json")
    parser.add_argument("--out", default="outputs/curriculum_plan/plan_summary.json")
    args = parser.parse_args()

    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    rows = []
    for index, stage in enumerate(config["stages"], start=1):
        rows.append(
            {
                "stage": index,
                "name": stage["name"],
                "num_agents": stage["num_agents"],
                "episodes": stage.get("episodes"),
                "max_steps": stage["max_steps"],
                "behavior_policy": stage.get("behavior_policy"),
                "baseline_policies": stage.get("baseline_policies"),
                "success": stage["success"],
            }
        )
    output = {
        "name": config["name"],
        "description": config["description"],
        "stages": rows,
        "note": "This file is an executable experiment plan; heavy training is launched separately after baseline locking.",
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
