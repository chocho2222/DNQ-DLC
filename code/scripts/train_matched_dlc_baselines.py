#!/usr/bin/env python
"""Retrain the three DLC world-model baselines under the proposed protocol.

The archived paper-DLC checkpoints were collected from two agents with the
legacy ``telemetry`` observation and trained for 200 actor updates with no
expert-action term, and their actors brake continuously: in the trainer's own
round-robin they cover about two tiles of a 304-tile lap in 800 steps. Comparing
them against a checkpoint trained for 40 000 steps on 160 expert episodes over
four to six agents measures the training budget, not the method.

This script therefore retrains the same three model classes
(individual transition, joint transition, joint transition with observer) on the
proposed arm's data, observation, and optimisation budget:

* observation: the same packed ``telemetry_dynamic`` rows the proposed model
  consumes, three dynamically selected relation slots per vehicle;
* data: the same expert episodes (``joint_clearance_pilot`` driving the target,
  lane-13 rule traffic behind it);
* budget: the same 40 000 world-model gradient steps at batch size 512, with the
  actor and value updated every fourth step;
* control: only the target row is scored by the actor, because only that row is
  controlled in closed loop; the other rows keep the recorded background actions
  inside the imagined rollout.

Pretraining or evaluating these baselines for the paper requires that they are
verified to drive, which is what ``--verify-steps`` records.

Usage:
    python3 scripts/train_matched_dlc_baselines.py \
        --scales 4,6 --dataset outputs/.../dataset_k15 \
        --out-dir outputs/.../dlc_matched_20260921 --device cuda:0
"""

import argparse
import glob
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dlc.graph_policy import pack_dynamic_neighbor_obs
from dlc.rollout import make_env
from dlc.torch_models import (
    MODEL_TYPES,
    Actor,
    TelemetryWorldModel,
    TorchDLCBundle,
    Value,
    make_tensor_batch,
    train_target_actor_value_step,
    train_world_step,
)

DEFAULT_DATASET = "outputs/tits_dynamic_graph_expanded/corrected_v2_20260920/dataset_k15"
PROPOSED_TRAIN_STEPS = 40000
PROPOSED_BATCH_SIZE = 512
PROPOSED_ACTOR_EVERY = 4
SLOT_TARGET_DIM = 41


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def dataset_paths(dataset_dirs, num_agents):
    paths = []
    for directory in dataset_dirs:
        paths.extend(glob.glob(f"{directory}/raw/*_n{num_agents}_seed*/transitions.npz"))
    return sorted(set(paths))


def load_episodes(paths):
    obs = np.concatenate([np.load(path)["obs"] for path in paths])
    action = np.concatenate([np.load(path)["action"] for path in paths])
    reward = np.concatenate([np.load(path)["reward"] for path in paths])
    next_obs = np.concatenate([np.load(path)["next_obs"] for path in paths])
    return obs, action, reward, next_obs


def observation_stats(obs):
    flat = obs.reshape(-1, obs.shape[-1]).astype(np.float64)
    return flat.mean(axis=0), flat.std(axis=0) + 1e-3


def build_transitions(obs, action, reward, next_obs, mean, std):
    return [
        {
            "obs": ((obs[index] - mean) / std).astype(np.float32),
            "action": action[index].astype(np.float32),
            "reward": reward[index].astype(np.float32),
            "next_obs": ((next_obs[index] - mean) / std).astype(np.float32),
        }
        for index in range(len(obs))
    ]


def reward_range(transitions, low=1.0, high=99.0):
    """Percentile range of the expert rewards, used to bound imagined rewards."""
    values = np.concatenate([np.asarray(item["reward"], dtype=np.float64) for item in transitions])
    return (float(np.percentile(values, low)), float(np.percentile(values, high)))


def observation_range(transitions, low=0.5, high=99.5):
    """Per-channel percentile range of the expert observations."""
    values = np.concatenate([np.asarray(item["obs"], dtype=np.float64) for item in transitions])
    flat = values.reshape(-1, values.shape[-1])
    return (np.percentile(flat, low, axis=0).astype(np.float32),
            np.percentile(flat, high, axis=0).astype(np.float32))


def return_bound(reward_clip, horizon, discount):
    """Largest discounted horizon sum the clipped reward range allows.

    Used to bound the TD(lambda) targets of the imagined rollout. The archived
    recipe has no such bound and its targets reach tens of thousands within a
    few thousand gradient steps, at which point the expert term in the actor
    loss is numerically irrelevant and the actor collapses onto a constant
    brake command (measured: action correlation with the expert ~0, mean brake
    0.42-0.74, closed-loop speed 0.0-0.44 m/s over 3-21 tiles).
    """
    if reward_clip is None:
        return None
    high = max(abs(float(reward_clip[0])), abs(float(reward_clip[1])))
    return float(high * sum(discount ** step for step in range(int(horizon))))


def train_variant(args, model_type, transitions, valid, mean, std, num_agents, obs_dim, device,
                  reward_clip=None, observation_clip=None):
    torch.manual_seed(args.seed)
    rng = np.random.default_rng(args.seed)
    world_model = TelemetryWorldModel(obs_dim, 3, num_agents, model_type, args.hidden_dim).to(device)
    actor = Actor(obs_dim, 3, args.hidden_dim).to(device)
    value = Value(obs_dim, args.hidden_dim).to(device)
    world_optimizer = torch.optim.Adam(world_model.parameters(), lr=args.model_lr)
    actor_optimizer = torch.optim.Adam(actor.parameters(), lr=args.actor_lr)
    value_optimizer = torch.optim.Adam(value.parameters(), lr=args.value_lr)

    losses, actor_losses = [], []
    started = time.time()
    for step in range(args.train_steps):
        batch = make_tensor_batch(
            [transitions[i] for i in rng.integers(0, len(transitions), args.batch_size)], device
        )
        losses.append(train_world_step(world_model, world_optimizer, batch, model_type))
        if step % args.actor_every == 0:
            actor_loss, _ = train_target_actor_value_step(
                world_model, actor, value, actor_optimizer, value_optimizer, batch,
                num_agents - 1, horizon=args.imagination_horizon,
                discount=args.discount, lambda_=args.lambda_,
                behavior_clone_weight=args.behavior_clone_weight,
                reward_clip=reward_clip,
                observation_clip=observation_clip,
                return_bound=return_bound(reward_clip, args.imagination_horizon,
                                          args.discount) if args.bound_returns else None,
                normalize_returns=args.normalize_returns,
                actor_grad_clip=args.actor_grad_clip,
            )
            actor_losses.append(actor_loss)
        if (step + 1) % 10000 == 0:
            print(f"    {model_type} step {step+1}/{args.train_steps} "
                  f"world {np.mean(losses[-500:]):.4f} actor {np.mean(actor_losses[-200:]):.3f} "
                  f"{time.time()-started:.0f}s", flush=True)

    held_out = measure_prediction(world_model, valid, device, model_type)
    bundle = TorchDLCBundle(
        world_model=world_model.cpu(), actor=actor.cpu(), value=value.cpu(),
        obs_mean=mean, obs_std=std,
        action_mean=np.zeros(3, dtype=np.float32), action_std=np.ones(3, dtype=np.float32),
        meta={
            "model_type": model_type,
            "obs_dim": int(obs_dim),
            "action_dim": 3,
            "num_agents": int(num_agents),
            "hidden_dim": int(args.hidden_dim),
            "train_steps": int(args.train_steps),
            "batch_size": int(args.batch_size),
            "actor_updates": len(actor_losses),
            "behavior_clone_weight": float(args.behavior_clone_weight),
            "imagined_reward_clip": list(reward_clip) if reward_clip else None,
            "imagined_observation_clip": bool(observation_clip is not None),
            "imagination_horizon": int(args.imagination_horizon),
            "discount": float(args.discount),
            "lambda": float(args.lambda_),
            "telemetry_version": "corrected_v2",
            "observation_type": "telemetry_dynamic",
            "slot_feature_dim": 7,
            "use_slot_mask": True,
            "pack_neighbors": 3,
            "actor_scope": "target_row_only",
            "target_agent": int(num_agents - 1),
            "expert_source": "joint_clearance_pilot",
            "background_profile": "lane13",
            "dataset": args.dataset,
            "source": "matched_protocol_dlc_retrain",
            "seed": int(args.seed),
        },
    )
    metrics = {
        "world_loss_mean": float(np.mean(losses)),
        "world_loss_last_1000": float(np.mean(losses[-1000:])),
        "actor_loss_last_200": float(np.mean(actor_losses[-200:])) if actor_losses else None,
        "actor_updates": len(actor_losses),
        "held_out_next_obs_mse": held_out,
        "train_seconds": time.time() - started,
    }
    return bundle, metrics


def measure_prediction(world_model, valid, device, model_type, batch_size=256):
    """One-step MSE on held-out expert transitions."""
    world_model.eval()
    errors = []
    with torch.no_grad():
        for start in range(0, min(len(valid), batch_size * 8), batch_size):
            chunk = valid[start:start + batch_size]
            if not chunk:
                continue
            batch = make_tensor_batch(chunk, device)
            pred_next, _ = world_model(batch[0], batch[1], ego_agent=0)
            errors.append(float(torch.mean((pred_next - batch[3]) ** 2).cpu()))
    world_model.train()
    return float(np.mean(errors)) if errors else None


def agent_observation_stats(bundle, target):
    """Per-agent normalisation constants, whether the bundle stores one row per
    agent or a single row pooled over the field.

    ``observation_stats`` returns the pooled statistics for the retrained
    checkpoints, so indexing them by agent - as the first version of this drive
    check did - picks a single channel and normalises the whole observation with
    it. That made every retrained actor look stationary: the actor was fine, the
    drive check was feeding it a rescaled observation.
    """
    mean = np.asarray(bundle.obs_mean, dtype=np.float32)
    std = np.asarray(bundle.obs_std, dtype=np.float32)
    if mean.ndim == 1:
        return mean, std
    return mean[target], std[target]


def verify_closed_loop(bundle, num_agents, steps, seed, device, out_dir, model_type,
                       line_spacing=15, lateral_spacing=3.6, traffic_profile="slow_traffic"):
    """Drive the target under the same scenario the main comparison runs.

    The first version of this check packed the whole field into the first
    eighteen tiles on a 2.2 m lateral grid and drove the opponents with the
    clearance expert. That is not the evaluation scenario: the comparison
    starts the field one car per row fifteen tiles apart on a 3.6 m grid and
    drives the opponents with the slow-traffic profile. A checkpoint judged on
    the wrong scene carries no information about how it behaves in the table,
    so the check now mirrors the run it is meant to predict.
    """
    actor = bundle.actor.to(device).eval()
    target = num_agents - 1
    mean, std = agent_observation_stats(bundle, target)
    from scripts.run_tits_dynamic_graph_evaluation import make_background_policy

    env = make_env(
        num_agents=num_agents, seed=seed, observation_type="telemetry_dynamic",
        start_order=list(range(num_agents)),
        line_spacing=line_spacing, lateral_spacing=lateral_spacing, max_neighbors=0,
        telemetry_version="corrected_v2", neighbor_order="identity",
    )
    if hasattr(env, "_max_episode_steps"):
        env._max_episode_steps = steps + 1
    background = {
        agent: make_background_policy(agent, traffic_profile)
        for agent in range(num_agents)
        if agent != target
    }
    assert len(background) == num_agents - 1, "every opponent row needs a driver"
    obs = env.reset()
    speeds, laterals = [], []
    try:
        for step in range(steps):
            actions = np.zeros((num_agents, 3), dtype=np.float32)
            for agent, policy in background.items():
                actions[agent] = np.asarray(policy.act(env, obs), dtype=np.float32)[agent]
            packed = pack_dynamic_neighbor_obs(
                np.asarray(obs, dtype=np.float32), target_obs_dim=SLOT_TARGET_DIM,
                max_neighbors=3, selection_mode="interaction", telemetry_version="corrected_v2",
            )
            row = torch.as_tensor((packed[target] - mean) / std, dtype=torch.float32, device=device)
            with torch.no_grad():
                actions[target] = actor(row).cpu().numpy()
            obs, _, done, _ = env.step(actions)
            speeds.append(float(obs[target, 4]))
            laterals.append(abs(float(obs[target, 12])))
            if done:
                break
        result = {
            "model_type": model_type, "seed": seed, "steps": step + 1,
            "speed_mean": float(np.mean(speeds)) if speeds else 0.0,
            "speed_max": float(np.max(speeds)) if speeds else 0.0,
            "mean_abs_lateral": float(np.mean(laterals)) if laterals else 0.0,
            "tiles": int(env.unwrapped.tile_visited_count[target]),
            "line_spacing": float(line_spacing),
            "lateral_spacing": float(lateral_spacing),
            "traffic_profile": traffic_profile,
        }
    finally:
        env.close()
    (Path(out_dir) / f"drive_check_{model_type}_n{num_agents}_seed{seed}.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--scales", default="4,6")
    parser.add_argument("--dataset", default=DEFAULT_DATASET,
                        help="Comma separated expert dataset roots")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--variants", default=",".join(sorted(MODEL_TYPES)))
    parser.add_argument("--train-steps", type=int, default=PROPOSED_TRAIN_STEPS)
    parser.add_argument("--batch-size", type=int, default=PROPOSED_BATCH_SIZE)
    parser.add_argument("--actor-every", type=int, default=PROPOSED_ACTOR_EVERY)
    parser.add_argument("--hidden-dim", type=int, default=256)
    parser.add_argument("--model-lr", type=float, default=6e-4)
    parser.add_argument("--actor-lr", type=float, default=8e-5)
    parser.add_argument("--value-lr", type=float, default=6e-4)
    parser.add_argument("--behavior-clone-weight", type=float, default=1.0)
    parser.add_argument("--no-observation-clip", dest="clip_imagined_observation",
                        action="store_false",
                        help="Disable the per-channel bound on imagined telemetry.")
    parser.add_argument("--no-reward-clip", dest="clip_imagined_reward", action="store_false",
                        help="Disable the bound on imagined rewards (the archived setting, for "
                             "the diagnostic that shows the open-loop reward head diverging).")
    parser.set_defaults(clip_imagined_reward=True, clip_imagined_observation=True)
    parser.add_argument("--imagination-horizon", type=int, default=15)
    parser.add_argument("--discount", type=float, default=0.99)
    parser.add_argument("--lambda", dest="lambda_", type=float, default=0.95)
    parser.add_argument("--no-bound-returns", dest="bound_returns", action="store_false",
                        help="Keep the archived, unbounded TD(lambda) imagined targets.")
    parser.add_argument("--no-normalize-returns", dest="normalize_returns", action="store_false",
                        help="Use raw imagined returns in the actor objective (archived setting).")
    parser.add_argument("--actor-grad-clip", type=float, default=10.0)
    parser.set_defaults(bound_returns=True, normalize_returns=True)
    parser.add_argument("--seeds", default="0,1,2")
    parser.add_argument("--episodes", type=int, default=0, help="0 keeps every available episode")
    parser.add_argument("--val-episodes", type=int, default=12)
    parser.add_argument("--verify-steps", type=int, default=1200)
    parser.add_argument("--verify-seed", type=int, default=401)
    parser.add_argument("--verify-line-spacing", type=int, default=15,
                        help="Row spacing of the drive check; matches the main comparison.")
    parser.add_argument("--verify-lateral-spacing", type=float, default=3.6,
                        help="Lateral grid of the drive check; matches the main comparison.")
    parser.add_argument("--verify-traffic-profile", default="slow_traffic",
                        help="Opponent policy profile of the drive check.")
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--select-only", action="store_true",
                        help="Rebuild the seed selection and manifest from checkpoints that "
                             "already exist instead of training again. Used because several "
                             "scales share one output directory.")
    args = parser.parse_args()

    device = torch.device(args.device)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    datasets = [item.strip() for item in args.dataset.split(",") if item.strip()]
    scales = [int(item) for item in args.scales.split(",") if item.strip()]
    variants = [item.strip() for item in args.variants.split(",") if item.strip()]
    seeds = [int(item) for item in args.seeds.split(",") if item.strip()]
    for variant in variants:
        if variant not in MODEL_TYPES:
            raise ValueError(f"unknown model type: {variant}")

    manifest = {"protocol": {
        "observation": "telemetry_dynamic, 3 packed relation slots",
        "slot_target_dim": SLOT_TARGET_DIM,
        "dataset": datasets,
        "train_steps": args.train_steps,
        "batch_size": args.batch_size,
        "actor_every": args.actor_every,
        "behavior_clone_weight": args.behavior_clone_weight,
        "imagined_reward_clip_percentiles": [1.0, 99.0] if args.clip_imagined_reward else None,
        "imagined_observation_clip_percentiles": [0.5, 99.5] if args.clip_imagined_observation else None,
        "imagined_returns_bounded": bool(args.bound_returns),
        "imagined_returns_normalized": bool(args.normalize_returns),
        "actor_grad_clip": float(args.actor_grad_clip),
        "actor_scope": "target_row_only",
        "seeds": seeds,
        "selection_rule": "lowest held-out one-step next-observation MSE, then verified to drive",
        "proposed_arm_budget": {"train_steps": PROPOSED_TRAIN_STEPS,
                                "batch_size": PROPOSED_BATCH_SIZE,
                                "episode_expert": "joint_clearance_pilot, 160 episodes"},
    }, "scales": {}}

    for num_agents in scales:
        paths = dataset_paths(datasets, num_agents)
        if args.episodes:
            paths = paths[:args.episodes]
        if not paths:
            print(f"[n{num_agents}] no episodes found, skipping", flush=True)
            continue
        split = max(1, len(paths) - args.val_episodes)
        train_paths, val_paths = paths[:split], paths[split:] or paths[-1:]
        print(f"[n{num_agents}] {len(train_paths)} train / {len(val_paths)} held-out episodes", flush=True)
        obs, action, reward, next_obs = load_episodes(train_paths)
        mean, std = observation_stats(obs)
        transitions = build_transitions(obs, action, reward, next_obs, mean, std)
        del obs, next_obs
        vobs, vaction, vreward, vnext = load_episodes(val_paths)
        valid = build_transitions(vobs, vaction, vreward, vnext, mean, std)
        del vobs, vnext
        num_agents_obs, obs_dim = transitions[0]["obs"].shape
        scale_record = {"n_agents": num_agents, "train_episodes": len(train_paths),
                        "val_episodes": len(val_paths), "transitions": len(transitions),
                        "episode_sha256": {Path(p).parts[-2]: sha256(p) for p in paths},
                        "variants": {}}
        if args.select_only:
            for model_type in variants:
                candidates = []
                for seed in seeds:
                    path = out_dir / f"{model_type}_n{num_agents}_seed{seed}.pt"
                    if not path.exists():
                        continue
                    bundle = TorchDLCBundle.load(str(path), map_location="cpu")
                    world = bundle.world_model.to(device)
                    mse = measure_prediction(world, valid, device, model_type)
                    candidates.append({"seed": seed, "path": str(path), "sha256": sha256(path),
                                       "held_out_next_obs_mse": mse})
                if not candidates:
                    print(f"  [n{num_agents}] {model_type}: no checkpoints", flush=True)
                    continue
                chosen = min(candidates, key=lambda item: item["held_out_next_obs_mse"])
                bundle = TorchDLCBundle.load(chosen["path"], map_location="cpu")
                drive = verify_closed_loop(
                    bundle, num_agents, args.verify_steps, args.verify_seed, device, out_dir,
                    model_type, line_spacing=args.verify_line_spacing,
                    lateral_spacing=args.verify_lateral_spacing,
                    traffic_profile=args.verify_traffic_profile)
                print(f"  [n{num_agents}] {model_type}: seed {chosen['seed']} "
                      f"MSE {chosen['held_out_next_obs_mse']:.5f} "
                      f"speed {drive['speed_mean']:.3f} tiles {drive['tiles']}", flush=True)
                scale_record["variants"][model_type] = {
                    "candidates": candidates,
                    "selected_seed": chosen["seed"],
                    "selected_path": chosen["path"],
                    "selected_sha256": chosen["sha256"],
                    "drive_check": drive,
                }
            manifest["scales"][str(num_agents)] = scale_record
            (out_dir / f"retrain_manifest_n{num_agents}.json").write_text(
                json.dumps({"protocol": manifest["protocol"], "scales": {str(num_agents): scale_record}},
                           indent=2), encoding="utf-8")
            continue
        for model_type in variants:
            records = []
            for seed in seeds:
                args.seed = seed
                print(f"  training {model_type} n{num_agents} seed{seed}", flush=True)
                clip = reward_range(transitions) if args.clip_imagined_reward else None
                obs_clip = observation_range(transitions) if args.clip_imagined_observation else None
                bundle, metrics = train_variant(
                    args, model_type, transitions, valid, mean, std, num_agents_obs, obs_dim,
                    device, reward_clip=clip, observation_clip=obs_clip)
                path = out_dir / f"{model_type}_n{num_agents}_seed{seed}.pt"
                bundle.save(path)
                metrics.update({"seed": seed, "path": str(path),
                                "sha256": sha256(path)})
                records.append({"metrics": metrics, "bundle": bundle})
            chosen = min(records, key=lambda item: (item["metrics"]["held_out_next_obs_mse"] is None,
                                                    item["metrics"]["held_out_next_obs_mse"]))
            print(f"  selected seed {chosen['metrics']['seed']} "
                  f"(held-out MSE {chosen['metrics']['held_out_next_obs_mse']:.5f})", flush=True)
            drive = verify_closed_loop(
                chosen["bundle"], num_agents, args.verify_steps, args.verify_seed, device,
                out_dir, model_type, line_spacing=args.verify_line_spacing,
                lateral_spacing=args.verify_lateral_spacing,
                traffic_profile=args.verify_traffic_profile)
            print(f"  drive check {model_type} n{num_agents}: speed {drive['speed_mean']:.3f} "
                  f"tiles {drive['tiles']}", flush=True)
            scale_record["variants"][model_type] = {
                "candidates": [item["metrics"] for item in records],
                "selected_seed": chosen["metrics"]["seed"],
                "selected_path": chosen["metrics"]["path"],
                "selected_sha256": chosen["metrics"]["sha256"],
                "drive_check": drive,
            }
        manifest["scales"][str(num_agents)] = scale_record
        (out_dir / f"retrain_manifest_n{num_agents}.json").write_text(
            json.dumps({"protocol": manifest["protocol"], "scales": {str(num_agents): scale_record}},
                       indent=2), encoding="utf-8")
    (out_dir / "retrain_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print("MATCHED_DLC_RETRAIN_DONE")


if __name__ == "__main__":
    main()
