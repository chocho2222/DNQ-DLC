#!/usr/bin/env python
"""Does the graph input change what the world model predicts?

The admission rule can only influence the plan if the transition model responds
to which opponents occupy the neighbour slots. This audit measures that
directly: it predicts the next state from the real observation, then from
observations whose neighbour slots have been permuted, emptied, or reduced to
the single nearest opponent. For scale, it also reports what a 0.35 throttle
change does to the same prediction.

A model whose permutation response is near zero cannot express a relevance
judgement at all, because the actor and the transition model both pool the
slots permutation-invariantly.

Usage:
    python3 scripts/audit_world_model_neighbor_sensitivity.py --model <ckpt> \
        --out-dir <dir> [--device cpu]
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pyglet

pyglet.options["headless"] = True

from dlc.graph_world_model import GraphWorldModelPolicy, EGO_DIM  # noqa: E402
from dlc.graph_policy import _infer_source_layout, _rank_opponent_slot_entries, pack_dynamic_neighbor_obs  # noqa: E402
from dlc.policies import TelemetryLanePolicy  # noqa: E402
from dlc.rollout import make_env  # noqa: E402

CHANNELS = [
    "x/PLAYFIELD", "y/PLAYFIELD", "vx/50", "vy/50", "speed/50", "sin h", "cos h",
    "omega/5", "track_index", "tile_progress", "dx/TW", "dy/TW", "lateral",
    "sin e_psi", "cos e_psi", "grass", "backward",
]


def predict(policy, packed, action, target):
    """Next-state prediction from an already packed observation."""
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


def which_three_matters(obs, policy, action, target):
    """Prediction change when the slot budget is filled by a different three.

    Unlike emptying the graph, this keeps the number of admitted vehicles fixed
    and only changes which vehicles they are, which is the decision the
    admission rule actually makes.
    """
    raw = np.asarray(obs, dtype=np.float32)
    slot_dim, _, use_slot_mask = _infer_source_layout(raw.shape[-1])
    entries = _rank_opponent_slot_entries(
        raw[target], slot_dim=slot_dim, use_slot_mask=use_slot_mask,
        selection_mode="relevance_v2", telemetry_version="corrected_v2",
    )
    indices = [index for index, _ in entries]
    budget = policy.slot_budget or len(indices)
    top = indices[:budget]
    bottom = indices[-budget:][::-1]
    if len(top) < budget or top == bottom:
        return None
    common = dict(fill=None, target_obs_dim=policy.bundle.meta.get("obs_dim"),
                  max_neighbors=budget, selection_mode="relevance_v2",
                  telemetry_version="corrected_v2")
    common["fill"] = None
    from dlc.graph_policy import _opponent_fill_vector
    fill = _opponent_fill_vector(policy.bundle)
    packed_top = pack_dynamic_neighbor_obs(raw, fill=fill, slot_order=[None] * target + [top],
                                           **{k: v for k, v in common.items() if k != "fill"})
    packed_bottom = pack_dynamic_neighbor_obs(raw, fill=fill, slot_order=[None] * target + [bottom],
                                              **{k: v for k, v in common.items() if k != "fill"})
    a = predict(policy, packed_top, action, target)
    b = predict(policy, packed_bottom, action, target)
    return np.abs(a - b)


def scramble(row, mode, keep=None, rng=None):
    """Return a copy of one agent row with its neighbour slots altered."""
    out = np.array(row, dtype=np.float32, copy=True)
    slot_dim, feat_dim, use_mask = _infer_source_layout(out.shape[-1])
    slots = out[EGO_DIM:].reshape(-1, slot_dim).copy()
    if slots.shape[0] == 0:
        return out
    if mode == "permute":
        order = list(range(slots.shape[0]))[::-1]
        slots = slots[order]
    elif mode == "empty":
        slots[:] = 0.0
    elif mode == "nearest_only":
        slots[keep + 1 :] = 0.0
        if use_mask:
            slots[keep + 1 :, feat_dim] = 0.0
    else:
        raise ValueError(mode)
    out[EGO_DIM:] = slots.reshape(-1)
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--seed", type=int, default=22)
    parser.add_argument("--num-agents", type=int, default=4)
    parser.add_argument("--steps", type=int, default=120)
    parser.add_argument("--warmup-steps", type=int, default=40)
    parser.add_argument("--target-speed", type=float, default=21.0)
    args = parser.parse_args()

    env = make_env(num_agents=args.num_agents, seed=args.seed,
                   observation_type="telemetry_dynamic", start_order=None,
                   line_spacing=30, lateral_spacing=2.2, track_path=None,
                   max_neighbors=0, telemetry_version="corrected_v2",
                   neighbor_order="identity")
    obs = env.reset()
    obs = obs[0] if isinstance(obs, tuple) else obs
    policy = GraphWorldModelPolicy(args.model, device=args.device, neighbor_mode="dynamic",
                                   neighbor_selection_mode="interaction", max_neighbors=None)
    controller = TelemetryLanePolicy(target_speed=args.target_speed, name="neighbor-sensitivity")
    controller.reset()
    target = args.num_agents - 1
    for _ in range(args.warmup_steps):
        obs, _, _, _ = env.step(controller.act(env, obs))

    rng = np.random.default_rng(args.seed)
    deltas = {key: [] for key in ("permute", "empty", "nearest_only", "throttle")}
    swap_deltas = []
    for _ in range(args.steps):
        action = controller.act(env, obs)
        base = np.asarray(policy._probe_one_step(env, obs, action), dtype=np.float32)[target]
        for mode in ("permute", "empty", "nearest_only"):
            altered = np.array(obs, copy=True)
            altered[target] = scramble(obs[target], mode, keep=0, rng=rng)
            predicted = np.asarray(policy._probe_one_step(env, altered, action), dtype=np.float32)[target]
            deltas[mode].append(np.abs(predicted - base))
        shifted = np.asarray(action, dtype=np.float32).copy()
        shifted[target, 1] = float(np.clip(shifted[target, 1] + 0.35, 0.0, 1.0))
        throttled = np.asarray(policy._probe_one_step(env, obs, shifted), dtype=np.float32)[target]
        deltas["throttle"].append(np.abs(throttled - base))
        obs, _, _, _ = env.step(action)
        swapped = which_three_matters(np.asarray(obs, dtype=np.float32), policy, action, target)
        if swapped is not None:
            swap_deltas.append(swapped)

    summary = {"model": str(args.model), "steps": len(deltas["permute"]), "channels": {}}
    swapped = np.asarray(swap_deltas) if swap_deltas else np.zeros((1, len(CHANNELS)))
    print(f"{'feature':<16}{'permute':>10}{'empty':>10}{'near-only':>11}{'swap-3':>10}{'throttle':>10}")
    for index, name in enumerate(CHANNELS):
        row = {key: float(np.mean([d[index] for d in deltas[key]])) for key in deltas}
        row["swap_set"] = float(swapped[:, index].mean())
        row["throttle_over_permute"] = (
            row["throttle"] / row["permute"] if row["permute"] > 1e-9 else float("inf")
        )
        summary["channels"][name] = row
        print(f"{name:<16}{row['permute']:>10.5f}{row['empty']:>10.5f}"
              f"{row['nearest_only']:>11.5f}{row['swap_set']:>10.5f}{row['throttle']:>10.5f}")

    state = np.asarray(obs, dtype=np.float32)[target]
    scale = max(float(np.abs(state).mean()), 1e-6)
    for key in deltas:
        summary[f"mean_abs_{key}"] = float(np.mean([d.mean() for d in deltas[key]]))
        summary[f"mean_abs_{key}_relative"] = summary[f"mean_abs_{key}"] / scale
    summary["mean_abs_swap_set"] = float(swapped.mean())
    summary["mean_abs_swap_set_relative"] = summary["mean_abs_swap_set"] / scale
    summary["swap_set_steps"] = int(len(swap_deltas))
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "neighbor_sensitivity.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print()
    print(f"mean |delta| relative to state scale: "
          f"permute {summary['mean_abs_permute_relative']:.4f}  "
          f"empty {summary['mean_abs_empty_relative']:.4f}  "
          f"nearest-only {summary['mean_abs_nearest_only_relative']:.4f}  "
          f"swap-3 {summary['mean_abs_swap_set_relative']:.4f}  "
          f"throttle {summary['mean_abs_throttle_relative']:.4f}")


if __name__ == "__main__":
    main()
