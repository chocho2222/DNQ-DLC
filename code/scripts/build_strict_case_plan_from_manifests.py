#!/usr/bin/env python
"""Merge frozen randomized-run manifests into a strict-audit case plan."""

import argparse
import csv
import hashlib
import json
from pathlib import Path


FIELDS = [
    "case_index", "experiment_id", "track_id", "track_path", "num_agents",
    "seed", "algorithms", "device", "out_dir", "command",
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, help="Experiment root containing shard manifests.")
    parser.add_argument("--manifest-name", default="pre_run_manifest.json")
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--out", default="", help="Defaults to <root>/frozen_case_plan.csv.")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    output = Path(args.out).resolve() if args.out else root / "frozen_case_plan.csv"
    manifests = sorted(root.glob(f"*/{args.manifest_name}"))
    if not manifests:
        raise FileNotFoundError(f"no {args.manifest_name} files under {root}")

    rows = []
    seen = set()
    source_hashes = {}
    for manifest_path in manifests:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        source_hashes[str(manifest_path)] = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
        algorithms = payload.get("algorithms", [])
        if not algorithms:
            raise ValueError(f"manifest has no algorithms: {manifest_path}")
        device = str(payload.get("arguments", {}).get("device", ""))
        for source in payload.get("rows", []):
            key = (str(source["case_dir"]), int(source["num_agents"]), int(source["seed"]))
            if key in seen:
                raise ValueError(f"duplicate case in manifests: {key}")
            seen.add(key)
            track_path = str(source.get("track", ""))
            rows.append({
                "case_index": len(rows),
                "experiment_id": args.experiment_id,
                "track_id": Path(track_path).stem if track_path else "procedural",
                "track_path": track_path,
                "num_agents": int(source["num_agents"]),
                "seed": int(source["seed"]),
                "algorithms": ",".join(algorithms),
                "device": device,
                "out_dir": str(source["case_dir"]),
                "command": str(source.get("command", "")),
            })

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    manifest = {
        "experiment_id": args.experiment_id,
        "case_count": len(rows),
        "algorithm_count": len({name for row in rows for name in row["algorithms"].split(",")}),
        "source_manifests": source_hashes,
        "case_plan": str(output),
        "case_plan_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "policy": "The case plan is frozen from pre-run manifests; failed or missing outputs remain in the denominator.",
    }
    manifest_path = output.with_suffix(".manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
