import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
import multiprocessing as mp
from pathlib import Path

import numpy as np
import torch

from dlc.policies import make_policy
from dlc.rollout import make_env, run_episode
from dlc.torch_models import (
    MODEL_TYPES,
    Actor,
    TelemetryWorldModel,
    TorchDLCBundle,
    Value,
    make_tensor_batch,
    train_actor_value_step,
    train_world_step,
    write_json,
)


def collect_episode(episode, seed, max_steps, behavior_policy):
    episode_seed = seed + episode
    env = make_env(num_agents=2, seed=episode_seed, observation_type="telemetry")
    policy = make_policy(behavior_policy, seed=episode_seed)
    try:
        result = run_episode(env, policy, max_steps=max_steps)
    finally:
        env.close()
    return episode, result["trajectory"]


def write_collect_progress(out_dir, seed, episodes, completed, transitions, max_steps, behavior_policy, collect_workers):
    if out_dir is None:
        return
    write_progress(
        out_dir,
        {
            "seed": seed,
            "phase": "collecting_transitions",
            "episodes_complete": completed,
            "episodes": episodes,
            "transitions": transitions,
            "max_steps": max_steps,
            "behavior_policy": behavior_policy,
            "collect_workers": collect_workers,
        },
    )


def collect_transitions(episodes, seed, max_steps, behavior_policy, out_dir=None, collect_workers=1):
    collect_workers = max(1, int(collect_workers))
    if collect_workers > 1:
        return collect_transitions_parallel(
            episodes,
            seed,
            max_steps,
            behavior_policy,
            out_dir=out_dir,
            collect_workers=collect_workers,
        )

    collected = []
    for episode in range(episodes):
        _, trajectory = collect_episode(episode, seed, max_steps, behavior_policy)
        collected.extend(trajectory)
        completed = episode + 1
        if out_dir is not None and (
            completed == 1 or completed == episodes or completed % 10 == 0
        ):
            write_collect_progress(
                out_dir,
                seed,
                episodes,
                completed,
                len(collected),
                max_steps,
                behavior_policy,
                collect_workers,
            )
    return collected


def collect_transitions_parallel(episodes, seed, max_steps, behavior_policy, out_dir=None, collect_workers=1):
    trajectories_by_episode = {}
    completed = 0
    transitions = 0
    context = mp.get_context("spawn")
    with ProcessPoolExecutor(max_workers=collect_workers, mp_context=context) as executor:
        futures = [
            executor.submit(collect_episode, episode, seed, max_steps, behavior_policy)
            for episode in range(episodes)
        ]
        for future in as_completed(futures):
            episode, trajectory = future.result()
            trajectories_by_episode[episode] = trajectory
            completed += 1
            transitions += len(trajectory)
            if completed == 1 or completed == episodes or completed % 10 == 0:
                write_collect_progress(
                    out_dir,
                    seed,
                    episodes,
                    completed,
                    transitions,
                    max_steps,
                    behavior_policy,
                    collect_workers,
                )

    collected = []
    for episode in range(episodes):
        collected.extend(trajectories_by_episode[episode])
    return collected


def shape_reward(reward, next_obs, args):
    shaped = np.asarray(reward, dtype=np.float32).copy()
    if not (
        args.grass_penalty
        or args.backward_penalty
        or args.lateral_penalty
        or args.progress_delta_weight
        or args.tile_progress_weight
        or args.lap_completion_bonus
    ):
        return shaped

    lateral = np.abs(next_obs[:, 12])
    on_grass = next_obs[:, 15]
    backward = next_obs[:, 16]
    tile_progress = next_obs[:, 9]
    shaped -= args.lateral_penalty * np.square(lateral)
    shaped -= args.grass_penalty * on_grass
    shaped -= args.backward_penalty * backward
    shaped += args.tile_progress_weight * tile_progress
    shaped += args.lap_completion_bonus * (tile_progress >= 0.995)

    if args.progress_delta_weight and next_obs.shape[0] == 2:
        progress_delta = next_obs[0, 8] - next_obs[1, 8]
        shaped[0] += args.progress_delta_weight * progress_delta
        shaped[1] -= args.progress_delta_weight * progress_delta
    return shaped.astype(np.float32)


def normalize_transitions(transitions, obs_mean, obs_std, args):
    normalized = []
    for transition in transitions:
        shaped_reward = shape_reward(transition["reward"], transition["next_obs"], args)
        normalized.append(
            {
                "obs": (transition["obs"] - obs_mean) / obs_std,
                "action": transition["action"],
                "reward": shaped_reward,
                "next_obs": (transition["next_obs"] - obs_mean) / obs_std,
            }
        )
    return normalized


def sample_batch(rng, transitions, batch_size):
    indices = rng.integers(0, len(transitions), size=batch_size)
    return [transitions[int(index)] for index in indices]


def write_progress(out_dir, payload):
    write_json(Path(out_dir) / "progress.json", payload)


def resolve_device(device):
    if device == "auto":
        return torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    resolved = torch.device(device)
    if resolved.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError(
            f"requested CUDA device {device}, but this PyTorch build cannot use CUDA"
        )
    return resolved


def build_bundle(args, model_type, world_model, actor, value, stats, obs_dim, action_dim, num_agents, train_step):
    meta = {
        "model_type": model_type,
        "obs_dim": obs_dim,
        "action_dim": action_dim,
        "num_agents": num_agents,
        "hidden_dim": args.hidden_dim,
        "train_steps": train_step,
        "batch_size": args.batch_size,
        "imagination_horizon": args.imagination_horizon,
        "discount": args.discount,
        "lambda": args.lambda_,
        "behavior_clone_weight": args.behavior_clone_weight,
        "safety_weight": args.safety_weight,
        "grass_penalty": args.grass_penalty,
        "backward_penalty": args.backward_penalty,
        "lateral_penalty": args.lateral_penalty,
        "progress_delta_weight": args.progress_delta_weight,
        "tile_progress_weight": args.tile_progress_weight,
        "lap_completion_bonus": args.lap_completion_bonus,
        "source": "telemetry_state_dlc",
    }
    return TorchDLCBundle(
        world_model=world_model.cpu(),
        actor=actor.cpu(),
        value=value.cpu(),
        obs_mean=stats["obs_mean"],
        obs_std=stats["obs_std"],
        action_mean=stats["action_mean"],
        action_std=stats["action_std"],
        meta=meta,
    )


def train_variant(args, model_type, transitions, stats, device, stage_dirs=None):
    rng = np.random.default_rng(args.seed)
    obs_dim = transitions[0]["obs"].shape[-1]
    action_dim = transitions[0]["action"].shape[-1]
    num_agents = transitions[0]["obs"].shape[0]

    world_model = TelemetryWorldModel(
        obs_dim=obs_dim,
        action_dim=action_dim,
        num_agents=num_agents,
        model_type=model_type,
        hidden_dim=args.hidden_dim,
    ).to(device)
    actor = Actor(obs_dim, action_dim, args.hidden_dim).to(device)
    value = Value(obs_dim, args.hidden_dim).to(device)

    world_optimizer = torch.optim.Adam(world_model.parameters(), lr=args.model_lr)
    actor_optimizer = torch.optim.Adam(actor.parameters(), lr=args.actor_lr)
    value_optimizer = torch.optim.Adam(value.parameters(), lr=args.value_lr)

    world_losses = []
    actor_losses = []
    value_losses = []
    stage_metrics = {}
    stage_dirs = stage_dirs or {}

    for step in range(args.train_steps):
        train_step = step + 1
        batch_transitions = sample_batch(rng, transitions, args.batch_size)
        batch = make_tensor_batch(batch_transitions, device)
        world_loss = train_world_step(world_model, world_optimizer, batch, model_type)
        world_losses.append(world_loss)

        if step % args.actor_every == 0:
            obs, behavior_action, _, _ = batch
            actor_loss, value_loss = train_actor_value_step(
                world_model,
                actor,
                value,
                actor_optimizer,
                value_optimizer,
                obs,
                behavior_action=behavior_action,
                horizon=args.imagination_horizon,
                discount=args.discount,
                lambda_=args.lambda_,
                behavior_clone_weight=args.behavior_clone_weight,
                safety_weight=args.safety_weight,
            )
            actor_losses.append(actor_loss)
            value_losses.append(value_loss)

        if train_step in stage_dirs:
            bundle = build_bundle(
                args,
                model_type,
                world_model,
                actor,
                value,
                stats,
                obs_dim,
                action_dim,
                num_agents,
                train_step,
            )
            bundle.save(stage_dirs[train_step] / f"{model_type}.pt")
            world_model.to(device)
            actor.to(device)
            value.to(device)
            stage_metrics[str(train_step)] = {
                "world_loss_final": world_losses[-1],
                "actor_loss_final": actor_losses[-1] if actor_losses else None,
                "value_loss_final": value_losses[-1] if value_losses else None,
                "actor_updates": len(actor_losses),
            }

        if train_step == 1 or train_step in stage_dirs or train_step == args.train_steps:
            write_progress(
                args.out_dir,
                {
                    "seed": args.seed,
                    "phase": "training",
                    "model_type": model_type,
                    "train_step": train_step,
                    "train_steps": args.train_steps,
                    "latest_world_loss": world_losses[-1],
                    "actor_updates": len(actor_losses),
                },
            )

    bundle = build_bundle(
        args,
        model_type,
        world_model,
        actor,
        value,
        stats,
        obs_dim,
        action_dim,
        num_agents,
        args.train_steps,
    )
    return bundle, {
        "world_loss_final": world_losses[-1],
        "world_loss_mean": float(np.mean(world_losses)),
        "actor_loss_final": actor_losses[-1] if actor_losses else None,
        "value_loss_final": value_losses[-1] if value_losses else None,
        "actor_updates": len(actor_losses),
        "stages": stage_metrics,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Train PyTorch telemetry-state DLC variants with imagined self-play."
    )
    parser.add_argument("--episodes", type=int, default=5)
    parser.add_argument("--max-steps", type=int, default=200)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument(
        "--behavior-policy",
        default="track_follow",
    )
    parser.add_argument("--out-dir", default="outputs/torch_dlc")
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--train-steps", type=int, default=200)
    parser.add_argument("--actor-every", type=int, default=1)
    parser.add_argument("--imagination-horizon", type=int, default=15)
    parser.add_argument("--hidden-dim", type=int, default=256)
    parser.add_argument("--model-lr", type=float, default=6e-4)
    parser.add_argument("--value-lr", type=float, default=6e-4)
    parser.add_argument("--actor-lr", type=float, default=8e-5)
    parser.add_argument("--discount", type=float, default=0.99)
    parser.add_argument("--lambda", dest="lambda_", type=float, default=0.95)
    parser.add_argument("--behavior-clone-weight", type=float, default=0.0)
    parser.add_argument("--safety-weight", type=float, default=0.0)
    parser.add_argument("--grass-penalty", type=float, default=0.0)
    parser.add_argument("--backward-penalty", type=float, default=0.0)
    parser.add_argument("--lateral-penalty", type=float, default=0.0)
    parser.add_argument("--progress-delta-weight", type=float, default=0.0)
    parser.add_argument("--tile-progress-weight", type=float, default=0.0)
    parser.add_argument("--lap-completion-bonus", type=float, default=0.0)
    parser.add_argument("--eval-at-steps", default="")
    parser.add_argument("--device", default="auto")
    parser.add_argument("--collect-workers", type=int, default=1)
    args = parser.parse_args()

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    device = resolve_device(args.device)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    write_progress(
        out_dir,
        {
            "seed": args.seed,
            "phase": "collecting_transitions",
            "episodes": args.episodes,
            "max_steps": args.max_steps,
            "behavior_policy": args.behavior_policy,
            "collect_workers": args.collect_workers,
        },
    )
    eval_at_steps = sorted(
        {
            int(step.strip())
            for step in args.eval_at_steps.split(",")
            if step.strip()
        }
    )
    stage_dirs = {
        step: out_dir / f"step_{step}"
        for step in eval_at_steps
        if 0 < step <= args.train_steps
    }
    for stage_dir in stage_dirs.values():
        stage_dir.mkdir(parents=True, exist_ok=True)

    raw_transitions = collect_transitions(
        episodes=args.episodes,
        seed=args.seed,
        max_steps=args.max_steps,
        behavior_policy=args.behavior_policy,
        out_dir=out_dir,
        collect_workers=args.collect_workers,
    )
    obs = np.stack([t["obs"] for t in raw_transitions]).astype(np.float32)
    action = np.stack([t["action"] for t in raw_transitions]).astype(np.float32)
    obs_std = np.maximum(obs.std(axis=0), 1e-2)
    stats = {
        "obs_mean": obs.mean(axis=0),
        "obs_std": obs_std,
        "action_mean": np.zeros_like(action.mean(axis=0)),
        "action_std": np.ones_like(action.std(axis=0)),
    }
    transitions = normalize_transitions(
        raw_transitions,
        stats["obs_mean"],
        stats["obs_std"],
        args,
    )
    write_progress(
        out_dir,
        {
            "seed": args.seed,
            "phase": "collected_transitions",
            "episodes": args.episodes,
            "max_steps": args.max_steps,
            "transitions": len(transitions),
        },
    )

    summary = {
        "seed": args.seed,
        "episodes": args.episodes,
        "max_steps": args.max_steps,
        "behavior_policy": args.behavior_policy,
        "transitions": len(transitions),
        "model_paths": {},
        "metrics": {},
        "stage_model_dirs": {
            str(step): str(stage_dir)
            for step, stage_dir in stage_dirs.items()
        },
    }

    for model_type in sorted(MODEL_TYPES):
        write_progress(
            out_dir,
            {
                "seed": args.seed,
                "phase": "starting_model",
                "model_type": model_type,
                "train_steps": args.train_steps,
                "transitions": len(transitions),
            },
        )
        bundle, metrics = train_variant(
            args,
            model_type,
            transitions,
            stats,
            device,
            stage_dirs=stage_dirs,
        )
        model_path = out_dir / f"{model_type}.pt"
        bundle.save(model_path)
        summary["model_paths"][model_type] = str(model_path)
        summary["metrics"][model_type] = metrics

    write_json(out_dir / "train_summary.json", summary)
    write_progress(
        out_dir,
        {
            "seed": args.seed,
            "phase": "complete",
            "transitions": len(transitions),
            "model_paths": summary["model_paths"],
        },
    )
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
