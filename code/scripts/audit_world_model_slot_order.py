#!/usr/bin/env python
"""Does the world model read the *order* of the neighbour slots?

The admission rule decides both which opponents enter the interaction slots and
which of them lands in slot 0. If the transition head pools the slots
symmetrically, that ordering decision is discarded and the per-slot successor
that training supplies (identity-matched at the source step) cannot be learned
per slot.

The audit feeds the same set of admitted opponents in two different slot orders
by overriding the packer's ranking, and separately compares the model's per-slot
neighbour prediction with the identity-matched successor recorded by the same
packing used for training.

Usage:
    python3 scripts/audit_world_model_slot_order.py --model <ckpt> --out-dir <dir> \
        [--num-agents 6] [--device cpu]
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pyglet

pyglet.options["headless"] = True

from dlc.graph_policy import (  # noqa: E402
    EGO_DIM,
    _infer_source_layout,
    _opponent_fill_vector,
    _rank_opponent_slot_entries,
    pack_dynamic_neighbor_obs,
)
from dlc.graph_world_model import GraphWorldModelPolicy  # noqa: E402
from dlc.policies import TelemetryLanePolicy  # noqa: E402
from dlc.rollout import make_env  # noqa: E402
from dlc.training_packing import pack_transition_pair  # noqa: E402

CHANNELS = [
    "x/PLAYFIELD", "y/PLAYFIELD", "vx/50", "vy/50", "speed/50", "sin h", "cos h",
    "omega/5", "track_index", "tile_progress", "dx/TW", "dy/TW", "lateral",
    "sin e_psi", "cos e_psi", "grass", "backward",
]


def predict(policy, packed, action, target):
    import torch

    with torch.no_grad():
        out = policy.bundle.transition(
            torch.as_tensor(policy.bundle.normalize_obs(packed)[None, ...],
                            dtype=torch.float32, device=policy.device),
            torch.as_tensor(policy.bundle.normalize_action(np.asarray(action, dtype=np.float32))[None, ...],
                            dtype=torch.float32, device=policy.device),
        )
        next_obs = policy.bundle.denormalize_obs(out["next_mu"].cpu().numpy()[0])
    return policy._preserve_rollout_masks(packed, next_obs)[target]


def pack_with_order(policy, raw, target, order, budget):
    fill = _opponent_fill_vector(policy.bundle)
    return pack_dynamic_neighbor_obs(
        raw,
        fill=fill,
        target_obs_dim=policy.bundle.meta.get("obs_dim"),
        max_neighbors=budget,
        selection_mode="relevance_v2",
        telemetry_version="corrected_v2",
        slot_order=[None] * target + [list(order)],
    )


def neighbour_dispersion(row, budget, slot_dim=8):
    """Mean absolute difference between the neighbour slots of one packed row."""
    slots = np.asarray(row, dtype=np.float32)[EGO_DIM:].reshape(-1, slot_dim)[:budget, :7]
    if len(slots) < 2:
        return float("nan"), float("nan")
    diffs = [np.abs(slots[i] - slots[j]).mean() for i in range(len(slots)) for j in range(i + 1, len(slots))]
    return float(np.mean(diffs)), float(np.abs(slots).mean())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--seed", type=int, default=22)
    parser.add_argument("--num-agents", type=int, default=6)
    parser.add_argument("--steps", type=int, default=120)
    parser.add_argument("--warmup-steps", type=int, default=40)
    parser.add_argument("--target-speed", type=float, default=21.0)
    parser.add_argument("--selection", default="relevance_v2")
    args = parser.parse_args()

    env = make_env(num_agents=args.num_agents, seed=args.seed,
                   observation_type="telemetry_dynamic", start_order=None,
                   line_spacing=15, lateral_spacing=2.2, track_path=None,
                   max_neighbors=0, telemetry_version="corrected_v2",
                   neighbor_order="identity")
    obs = env.reset()
    obs = obs[0] if isinstance(obs, tuple) else obs
    policy = GraphWorldModelPolicy(args.model, device=args.device, neighbor_mode="dynamic",
                                   neighbor_selection_mode=args.selection, max_neighbors=None)
    controller = TelemetryLanePolicy(target_speed=args.target_speed, name="slot-order-probe")
    controller.reset()
    target = args.num_agents - 1
    for _ in range(args.warmup_steps):
        obs, _, _, _ = env.step(controller.act(env, obs))

    budget = int(policy.slot_budget or 3)
    order_delta, slot_gap, true_gap, per_slot_err, copy_err = [], [], [], [], []
    scale_ref = []
    for _ in range(args.steps):
        action = controller.act(env, obs)
        raw = np.asarray(obs, dtype=np.float32)
        ids = [list(v) for v in env.unwrapped.last_dynamic_neighbor_ids]
        slot_dim, _, use_mask = _infer_source_layout(raw.shape[-1])
        entries = _rank_opponent_slot_entries(
            raw[target], slot_dim=slot_dim, use_slot_mask=use_mask,
            selection_mode=args.selection, telemetry_version="corrected_v2",
        )
        indices = [index for index, _ in entries]
        top = indices[:budget]
        if len(top) == budget and budget >= 2:
            rotated = top[1:] + top[:1]
            base = predict(policy, pack_with_order(policy, raw, target, top, budget), action, target)
            moved = predict(policy, pack_with_order(policy, raw, target, rotated, budget), action, target)
            order_delta.append(np.abs(base - moved))
            gap, level = neighbour_dispersion(base, budget)
            slot_gap.append(gap)
            scale_ref.append(np.abs(raw[target]).mean())
            next_obs, _, _, info = env.step(action)
            next_ids = [list(v) for v in info["neighbor_ids"]]
            try:
                packed, successor, _ = pack_transition_pair(
                    raw, np.asarray(next_obs, dtype=np.float32), ids, next_ids,
                    k=budget, selection=args.selection)
            except (ValueError, StopIteration):
                obs = next_obs
                continue
            true_gap.append(neighbour_dispersion(successor[target], budget)[0])
            per_slot_err.append(np.abs(base[EGO_DIM:] - successor[target][EGO_DIM:]))
            copy_err.append(np.abs(packed[target][EGO_DIM:] - successor[target][EGO_DIM:]))
            obs = next_obs
            continue
        obs, _, _, _ = env.step(action)

    order_delta = np.asarray(order_delta, dtype=np.float32)
    summary = {
        "model": str(args.model),
        "num_agents": args.num_agents,
        "selection": args.selection,
        "budget": budget,
        "paired_steps": int(len(order_delta)),
        "state_scale_mean_abs": float(np.mean(scale_ref)) if scale_ref else float("nan"),
        "order_mean_abs": float(order_delta.mean()) if len(order_delta) else float("nan"),
        "order_mean_abs_relative": (float(order_delta.mean()) / float(np.mean(scale_ref))
                                    if len(order_delta) and np.mean(scale_ref) else float("nan")),
        "order_max_abs": float(order_delta.max()) if len(order_delta) else float("nan"),
        "predicted_slot_dispersion": float(np.nanmean(slot_gap)) if slot_gap else float("nan"),
        "true_slot_dispersion": float(np.nanmean(true_gap)) if true_gap else float("nan"),
    }
    if per_slot_err:
        err = np.concatenate(per_slot_err, axis=0)
        summary["per_slot_neighbour_mae"] = float(err.mean())
    if copy_err:
        summary["copy_baseline_neighbour_mae"] = float(np.concatenate(copy_err, axis=0).mean())
    print(json.dumps(summary, indent=2))
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "slot_order_sensitivity.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
