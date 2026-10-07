#!/usr/bin/env python
"""Counterfactual action-response audit of the action-conditioned world model.

The planner ranks candidates by the *imagined* consequence of an action. If the
learned transition does not reproduce the sign of the true response (for
example, if commanding throttle reduces the predicted speed), the ranking is
driven by an artefact of the fitted model rather than by the environment.

The audit therefore puts the simulator in one representative on-track state and
applies a grid of ego actions to that *same* state, once through the model and
once through the simulator. Box2D hull state is saved and restored between
trials so the comparison is genuinely counterfactual.

Usage:
    python3 scripts/audit_world_model_action_response.py --model <ckpt.pt> \
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

FEATURE_NAMES = {
    "speed": 4,
    "lateral": 12,
    "heading_cos": 14,
    "grass": 15,
    "backward": 16,
}


def snapshot(env):
    return [
        (tuple(map(float, car.hull.position)), tuple(map(float, car.hull.linearVelocity)),
         float(car.hull.angle), float(car.hull.angularVelocity))
        for car in env.unwrapped.cars
    ]


def restore(env, snap):
    for car, (position, velocity, angle, angular) in zip(env.unwrapped.cars, snap):
        car.hull.position = position
        car.hull.linearVelocity = velocity
        car.hull.angle = angle
        car.hull.angularVelocity = angular
        car.hull.awake = True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--seed", type=int, default=22)
    parser.add_argument("--num-agents", type=int, default=4)
    parser.add_argument("--warmup-steps", type=int, default=140)
    parser.add_argument("--gas-grid", default="0.0,0.2,0.4,0.64")
    parser.add_argument("--steer-grid", default="0.0,-0.25,0.25")
    args = parser.parse_args()

    env = make_env(num_agents=args.num_agents, seed=args.seed,
                   observation_type="telemetry_dynamic", start_order=None,
                   line_spacing=30, lateral_spacing=2.2, track_path=None,
                   max_neighbors=0, telemetry_version="corrected_v2",
                   neighbor_order="identity")
    obs = env.reset()
    obs = obs[0] if isinstance(obs, tuple) else obs
    lane = TelemetryLanePolicy(target_speed=21.0, name="action_response")
    lane.reset()
    for _ in range(args.warmup_steps):
        obs, _, _, _ = env.step(lane.act(env, obs))

    policy = GraphWorldModelPolicy(args.model, device=args.device, neighbor_mode="dynamic",
                                   neighbor_selection_mode="interaction", max_neighbors=None)
    target = args.num_agents - 1
    state = snapshot(env)
    base = np.asarray(obs, dtype=np.float32)

    rows = []
    for gas in [float(x) for x in args.gas_grid.split(",") if x.strip()]:
        for steer in [float(x) for x in args.steer_grid.split(",") if x.strip()]:
            action = np.zeros((args.num_agents, 3), dtype=np.float32)
            action[:, 0] = 0.0
            action[target, 0] = steer
            action[:, 1] = 0.0
            action[target, 1] = gas
            restore(env, state)
            predicted = np.asarray(policy._probe_one_step(env, base, action), dtype=np.float32)
            restore(env, state)
            nxt, _, _, _ = env.step(action)
            true = np.asarray(nxt, dtype=np.float32)
            row = {"gas": gas, "steer": steer}
            for name, index in FEATURE_NAMES.items():
                row[f"true_d_{name}"] = float(true[target, index] - base[target, index])
                row[f"model_d_{name}"] = float(predicted[target, index] - base[target, index])
            rows.append(row)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "action_response.json").write_text(
        json.dumps({"model": str(args.model), "device": args.device, "seed": args.seed,
                    "num_agents": args.num_agents, "warmup_steps": args.warmup_steps,
                    "steer_for_gas_sweep": 0.25, "rows": rows}, indent=2),
        encoding="utf-8")

    print(f"{'gas':>6}{'steer':>7} | {'true d(speed)':>14}{'model d(speed)':>16} | "
          f"{'true d(lat)':>13}{'model d(lat)':>14} | {'true d(headcos)':>16}{'model d(headcos)':>17}")
    for row in rows:
        print(f"{row['gas']:6.2f}{row['steer']:7.2f} | "
              f"{row['true_d_speed']:14.4f}{row['model_d_speed']:16.4f} | "
              f"{row['true_d_lateral']:13.4f}{row['model_d_lateral']:14.4f} | "
              f"{row['true_d_heading_cos']:16.5f}{row['model_d_heading_cos']:17.5f}")

    heat = {(row["gas"], row["steer"]): row for row in rows}
    if (0.0, 0.0) in heat:
        sign_agree = []
        for row in rows:
            if abs(row["true_d_speed"]) < 1e-4 and abs(row["model_d_speed"]) < 1e-4:
                continue
            sign_agree.append(np.sign(row["true_d_speed"]) == np.sign(row["model_d_speed"]))
        print(f"\nthrottle-to-speed sign agreement: {int(np.sum(sign_agree))}/{len(sign_agree)}")


if __name__ == "__main__":
    main()
