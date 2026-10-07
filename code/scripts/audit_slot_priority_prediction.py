#!/usr/bin/env python
"""Does the rank feature change one-step prediction of the *shared* channels?

A null closed-loop result is hard to read on its own: it could mean the planner
compensates for the ranking, or that the feature never reached the transition
head at all. This probe separates the two by scoring both checkpoints on the
same episodes and on exactly the same physical channels: the self block, the
seven relation features and the occupancy mask. The rank column exists in one
layout only, so it can change a prediction only through what the pooling carries.

Episodes are evaluated with their own agent axis, which is how the transition
model is trained. The split is by episode, and every episode was also used to
fit these checkpoints, so this is a fit check (a necessary condition), not a
generalization measurement.

Usage:
    python3 scripts/audit_slot_priority_prediction.py --checkpoint 8:name=path \
        --dataset <dir> --out <dir> [--holdout-mod 5]
"""

import argparse
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
EGO_DIM = 17


def promoted(obs, k):
    """Stored eight-dimension slots with the admission rank inserted."""
    obs = np.asarray(obs, dtype=np.float32)
    out = np.zeros(obs.shape[:-1] + (EGO_DIM + 9 * k,), dtype=np.float32)
    out[..., :EGO_DIM] = obs[..., :EGO_DIM]
    slots = obs[..., EGO_DIM:].reshape(obs.shape[:-1] + (k, 8))
    block = out[..., EGO_DIM:].reshape(obs.shape[:-1] + (k, 9))
    block[..., :7] = slots[..., :7]
    block[..., 7] = np.where(slots[..., 7] > 0.5,
                             1.0 - np.arange(k, dtype=np.float32) / max(k - 1, 1), 0.0)
    block[..., 8] = slots[..., 7]
    return out


def channel_map(k):
    """Channel names, plus their index in the eight- and nine-slot layouts."""
    names, plain, ranked = [], [], []
    for index in range(EGO_DIM):
        names.append(f"ego_{index}")
        plain.append(index)
        ranked.append(index)
    for slot in range(k):
        for feature in range(7):
            names.append(f"slot{slot}_feature{feature}")
            plain.append(EGO_DIM + 8 * slot + feature)
            ranked.append(EGO_DIM + 9 * slot + feature)
        names.append(f"slot{slot}_mask")
        plain.append(EGO_DIM + 8 * slot + 7)
        ranked.append(EGO_DIM + 9 * slot + 8)
    return names, np.asarray(plain), np.asarray(ranked)


def episodes(dataset):
    return sorted((dataset / "raw").glob("episode_*/transitions.npz"))


def predict(checkpoint, obs, action, device):
    import torch
    from dlc.graph_world_model import GraphWorldModelBundle

    bundle = GraphWorldModelBundle.load(checkpoint, map_location=device)
    bundle.transition.to(device).eval()
    chunks = []
    with torch.no_grad():
        for start in range(0, len(obs), 512):
            current = obs[start:start + 512]
            out = bundle.transition(
                torch.as_tensor(bundle.normalize_obs(current), dtype=torch.float32, device=device),
                torch.as_tensor(bundle.normalize_action(action[start:start + 512]),
                                dtype=torch.float32, device=device))
            chunks.append(bundle.denormalize_obs(out["next_mu"].cpu().numpy()))
    return np.concatenate(chunks, axis=0)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", action="append", required=True,
                        help="legs:name=path, repeated once per arm; legs is 8 or 9")
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--holdout-mod", type=int, default=5)
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args()

    dataset = ROOT / args.dataset
    out_dir = ROOT / args.out
    out_dir.mkdir(parents=True, exist_ok=True)

    arms = {}
    for spec in args.checkpoint:
        legs_text, _, rest = spec.partition(":")
        name, _, path = rest.partition("=")
        legs = int(legs_text)
        if legs not in (8, 9):
            raise ValueError(f"slot legs must be 8 or 9, got {legs_text}")
        arms[name] = {"legs": legs,
                      "path": str(ROOT / path if not Path(path).is_absolute() else path),
                      "abs_error": None}

    totals = {name: None for name in arms}
    persistence_total = None
    transitions = 0
    evaluated = 0
    k = None
    for index, path in enumerate(episodes(dataset)):
        if index % args.holdout_mod:
            continue
        with np.load(path, allow_pickle=False) as arrays:
            obs, next_obs, action = arrays["obs"], arrays["next_obs"], arrays["action"]
        if k is None:
            k = (obs.shape[-1] - EGO_DIM) // 8
        names, plain, ranked = channel_map(k)
        reference = next_obs[..., plain]
        raise_obs = promoted(obs, k)
        persistence = np.abs(obs[..., plain] - reference)
        persistence_total = persistence.sum(axis=(0, 1)) if persistence_total is None \
            else persistence_total + persistence.sum(axis=(0, 1))
        for name, arm in arms.items():
            source = raise_obs if arm["legs"] == 9 else obs
            prediction = predict(Path(arm["path"]), source, action, args.device)
            index_map = ranked if arm["legs"] == 9 else plain
            error = np.abs(prediction[..., index_map] - reference)
            totals[name] = error.sum(axis=(0, 1)) if totals[name] is None \
                else totals[name] + error.sum(axis=(0, 1))
        transitions += int(obs.shape[0] * obs.shape[1])
        evaluated += 1
        print(f"episode {index}: agents={obs.shape[1]} steps={obs.shape[0]}", flush=True)

    if not evaluated:
        raise SystemExit("no episodes selected")
    report = {"episodes": evaluated, "slots": int(k), "transitions": transitions,
              "note": "fit check on episodes that also trained these checkpoints",
              "channels": {}, "summary": {}}
    persistence_mae = persistence_total / transitions
    for name, arm in arms.items():
        mae = totals[name] / transitions
        report["channels"][name] = {channel: float(value) for channel, value in zip(names, mae)}
        report["summary"][name] = {
            "legs": arm["legs"],
            "mean_mae": float(mae.mean()),
            "mean_mae_opponent": float(mae[EGO_DIM:].mean()),
            "mean_mae_ego": float(mae[:EGO_DIM].mean()),
        }
    report["summary"]["persistence"] = {
        "mean_mae": float(persistence_mae.mean()),
        "mean_mae_opponent": float(persistence_mae[EGO_DIM:].mean()),
        "mean_mae_ego": float(persistence_mae[:EGO_DIM].mean()),
    }
    report["channels"]["persistence"] = {channel: float(value)
                                         for channel, value in zip(names, persistence_mae)}
    (out_dir / "slot_priority_prediction.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report["summary"], indent=2), flush=True)


if __name__ == "__main__":
    main()
