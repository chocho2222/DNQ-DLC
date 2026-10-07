#!/usr/bin/env python
"""Per-channel one-step fidelity of the world model against a persistence baseline.

Reported per corrected-telemetry channel: mean absolute one-step error of the
model against the error of assuming no change at all (persistence). A negative
skill score means the learned transition is worse than the trivial predictor for
that channel, which is the honest way to report how much of the state is
actually predicted rather than averaged.

Usage:
    python3 scripts/audit_world_model_fidelity.py --model <ckpt.pt> \
        --out-dir <dir> [--device cuda:1]
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pyglet

pyglet.options["headless"] = True

from dlc.graph_world_model import GraphWorldModelPolicy  # noqa: E402
from dlc.policies import TelemetryLanePolicy  # noqa: E402
from dlc.rollout import make_env  # noqa: E402

PLAYFIELD = 2000.0
CHANNEL_NAMES = [
    "x/PLAYFIELD", "y/PLAYFIELD", "vx/50", "vy/50", "speed/50", "sin h", "cos h",
    "omega/5", "track_index", "tile_progress", "dx/TW", "dy/TW", "lateral",
    "sin e_psi", "cos e_psi", "grass", "backward",
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--seed", type=int, default=22)
    parser.add_argument("--num-agents", type=int, default=4)
    parser.add_argument("--steps", type=int, default=200)
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
    controller = TelemetryLanePolicy(target_speed=args.target_speed, name="fidelity")
    controller.reset()
    target = args.num_agents - 1
    for _ in range(args.warmup_steps):
        obs, _, _, _ = env.step(controller.act(env, obs))

    model_error, persistence_error = [], []
    for _ in range(args.steps):
        action = controller.act(env, obs)
        predicted = np.asarray(policy._probe_one_step(env, obs, action), dtype=np.float32)
        current = np.asarray(obs, dtype=np.float32)
        nxt, _, _, _ = env.step(action)
        nxt = np.asarray(nxt, dtype=np.float32)
        model_error.append(np.abs(predicted[target] - nxt[target]))
        persistence_error.append(np.abs(current[target] - nxt[target]))
        obs = nxt

    model_error = np.asarray(model_error)
    persistence_error = np.asarray(persistence_error)
    channels = []
    print(f"{'feature':<16}{'model err':>12}{'persistence':>13}{'skill':>9}")
    for index, name in enumerate(CHANNEL_NAMES):
        if index >= model_error.shape[1]:
            break
        model_mean = float(model_error[:, index].mean())
        persistence_mean = float(persistence_error[:, index].mean())
        skill = 1.0 - model_mean / max(persistence_mean, 1e-9)
        channels.append({"feature": name, "model_mae": model_mean,
                         "persistence_mae": persistence_mean, "skill": skill})
        print(f"{name:<16}{model_mean:12.5f}{persistence_mean:13.5f}{skill * 100:8.1f}%")

    summary = {
        "model": str(args.model), "device": args.device, "seed": args.seed,
        "num_agents": args.num_agents, "steps": args.steps,
        "warmup_steps": args.warmup_steps,
        "position_error_m": float(model_error[:, 0].mean() * PLAYFIELD / 6.0),
        "position_persistence_m": float(persistence_error[:, 0].mean() * PLAYFIELD / 6.0),
        "lateral_error_half_width": float(model_error[:, 12].mean()),
        "lateral_persistence_half_width": float(persistence_error[:, 12].mean()),
        "channels": channels,
    }
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "fidelity.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    better = sum(1 for row in channels if row["skill"] > 0)
    print(f"\nchannels better than persistence: {better}/{len(channels)}")
    print(f"position error {summary['position_error_m']:.2f} m vs persistence "
          f"{summary['position_persistence_m']:.2f} m")


if __name__ == "__main__":
    main()
