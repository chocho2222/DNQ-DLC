#!/usr/bin/env python
"""Re-pack a collected dataset with a different admission rule or capacity.

Collection stores the full exposure of every step (``full_obs``,
``neighbor_ids_before``) next to the packed slots the admission rule produced.
That makes the packing reversible offline: the same
``pack_transition_pair`` the collection used can be re-run with another rule or
another capacity, on the same episodes, the same expert behaviour and the same
transitions. No simulation is repeated, and the reward, risk, action and episode
boundaries are copied from the source.

The purpose is to train a transition model whose slot count matches a wider
admission budget without re-collecting the expert episodes with a different
engine setting.

Usage:
    python3 scripts/repack_interaction_slots.py \
        --source outputs/.../dataset_k15 \
        --out outputs/.../dataset_k15_i5 \
        --k 5 --selection interaction --workers 24
"""
import argparse
import gzip
import json
import os
import shutil
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dlc.training_packing import pack_transition_pair  # noqa: E402


def repack_episode(job):
    source, out, k, selection, name = job
    steps = []
    with gzip.open(source / "step_records.jsonl.gz", "rt") as handle:
        for line in handle:
            record = json.loads(line)
            obs = np.asarray(record["full_obs"], dtype=np.float32)
            next_obs = np.asarray(record["full_next_obs"], dtype=np.float32)
            packed, successor, selected = pack_transition_pair(
                obs, next_obs, record["neighbor_ids_before"],
                record["neighbor_ids_after"], k=k, selection=selection)
            steps.append((packed, successor, selected))
    arrays = np.load(source / "transitions.npz", allow_pickle=False)
    for key in ("action", "reward", "risk"):
        if len(arrays[key]) != len(steps):
            raise ValueError(f"{name}: {key} has {len(arrays[key])} rows for {len(steps)} steps")
    target = out / "raw" / name
    target.mkdir(parents=True, exist_ok=False)
    np.savez_compressed(
        target / "transitions.npz",
        obs=np.stack([step[0] for step in steps]).astype(np.float32),
        action=arrays["action"], reward=arrays["reward"], risk=arrays["risk"],
        next_obs=np.stack([step[1] for step in steps]).astype(np.float32))
    with open(target / "selected_neighbor_ids.json", "w") as handle:
        json.dump([step[2] for step in steps], handle)
    return name


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--k", type=int, required=True)
    parser.add_argument("--selection", default="interaction")
    parser.add_argument("--workers", type=int, default=16)
    args = parser.parse_args()

    source, out = Path(args.source), Path(args.out)
    provenance = json.loads((source / "provenance.json").read_text())
    summaries = json.loads((source / "collection_summary.json").read_text())
    out.mkdir(parents=True, exist_ok=True)
    (out / "raw").mkdir(exist_ok=True)

    jobs = []
    for summary in sorted(summaries, key=lambda row: row["episode"]):
        name = f"episode_{summary['episode']:05d}_n{summary['num_agents']}_seed{summary['seed']}"
        jobs.append((source / "raw" / name, out, int(args.k), args.selection, name))
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        names = list(pool.map(repack_episode, jobs))

    updated = json.loads(json.dumps(provenance))
    updated["args"]["max_neighbors"] = int(args.k)
    updated["args"]["neighbor_selection"] = args.selection
    updated["repack"] = {
        "source": str(source.resolve()),
        "source_provenance_sha256": __import__("hashlib").sha256(
            (source / "provenance.json").read_bytes()).hexdigest(),
        "k": int(args.k), "selection": args.selection,
        "note": ("slots re-packed offline from the recorded full exposure with "
                 "dlc.training_packing.pack_transition_pair; reward, risk, action "
                 "and episode boundaries copied from the source"),
    }
    (out / "provenance.json").write_text(json.dumps(updated, indent=2))
    shutil.copy(source / "collection_summary.json", out / "collection_summary.json")
    print(f"repacked {len(names)} episodes into {out} with k={args.k} rule={args.selection}")


if __name__ == "__main__":
    main()
