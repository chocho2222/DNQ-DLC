#!/usr/bin/env python
import argparse
import concurrent.futures
import json
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

from dlc.graph_policy import GraphActorBundle, PermutationInvariantActor, OPPONENT_DIM, randomize_neighbor_slots
from dlc.policies import TelemetryLanePolicy, TelemetryOvertakePolicy, TelemetryYieldPolicy
from dlc.rollout import make_env


def make_expert_policies(num_agents, target_agent):
    policies = []
    for agent_id in range(num_agents):
        if agent_id == target_agent:
            policies.append(
                TelemetryOvertakePolicy(
                    target_speed=22.0,
                    pass_speed=26.0,
                    pass_lane_offset=2.4,
                    name="expert_target_overtake",
                )
            )
        elif agent_id % 3 == 0:
            policies.append(TelemetryLanePolicy(target_speed=14.0, name=f"expert_lane_{agent_id}"))
        elif agent_id % 3 == 1:
            policies.append(TelemetryYieldPolicy(target_speed=15.0, yield_speed=10.5, name=f"expert_yield_{agent_id}"))
        else:
            policies.append(TelemetryLanePolicy(target_speed=17.0, name=f"expert_fast_lane_{agent_id}"))
    return policies


def expert_action(env, obs, policies):
    actions = np.zeros((env.unwrapped.num_agents, 3), dtype=np.float32)
    for agent_id, policy in enumerate(policies):
        actions[agent_id] = policy.act(env, obs)[agent_id]
    return actions


def sample_num_agents(args, rng):
    if args.min_agents == args.max_agents:
        return args.min_agents
    return int(rng.integers(args.min_agents, args.max_agents + 1))


def collect_episode_worker(payload):
    args_dict, episode, num_agents = payload
    args = argparse.Namespace(**args_dict)
    observations = []
    actions = []
    seed = args.seed + episode
    target_agent = num_agents - 1
    env = make_env(
        num_agents=num_agents,
        seed=seed,
        observation_type=args.observation_type,
        start_order=[2 * agent_id for agent_id in range(num_agents)],
        line_spacing=args.gap_tiles,
        lateral_spacing=0.0,
        track_path=args.track_path or None,
        max_neighbors=args.max_neighbors,
    )
    if hasattr(env, "_max_episode_steps"):
        env._max_episode_steps = args.max_steps + 1
    policies = make_expert_policies(num_agents, target_agent)
    for policy in policies:
        policy.reset()
    obs = env.reset()
    total_reward = np.zeros(num_agents, dtype=np.float64)
    grass_steps = np.zeros(num_agents, dtype=np.float64)
    done = False
    step = -1
    try:
        for step in range(args.max_steps):
            action = expert_action(env, obs, policies)
            observations.extend(obs.astype(np.float32))
            actions.extend(action.astype(np.float32))
            obs, reward, done, _ = env.step(action)
            total_reward += reward
            grass_steps += obs[:, 15] > 0.5
            if done:
                break
        steps = step + 1
        summary = {
            "episode": episode,
            "seed": seed,
            "num_agents": num_agents,
            "steps": steps,
            "done": bool(done),
            "tile_visited_count": list(env.unwrapped.tile_visited_count),
            "grass_rate": (grass_steps / max(steps, 1)).tolist(),
            "total_reward": total_reward.tolist(),
        }
    finally:
        env.close()
    return {
        "observations": np.asarray(observations, dtype=np.float32),
        "actions": np.asarray(actions, dtype=np.float32),
        "summary": summary,
    }


def collect_dataset(args):
    rng = np.random.default_rng(args.seed)
    num_agents_plan = [sample_num_agents(args, rng) for _ in range(args.episodes)]
    payloads = [(vars(args).copy(), episode, num_agents_plan[episode]) for episode in range(args.episodes)]
    workers = max(1, min(int(args.collection_workers), max(args.episodes, 1)))
    if workers > 1:
        with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as executor:
            results = list(executor.map(collect_episode_worker, payloads))
    else:
        results = [collect_episode_worker(payload) for payload in payloads]
    results.sort(key=lambda row: row["summary"]["episode"])
    observations = np.concatenate([row["observations"] for row in results], axis=0)
    actions = np.concatenate([row["actions"] for row in results], axis=0)
    episode_summaries = [row["summary"] for row in results]
    return observations, actions, episode_summaries


def load_dataset_npz(path):
    data = np.load(path, allow_pickle=True)
    observations = np.asarray(data["observations"], dtype=np.float32)
    actions = np.asarray(data["actions"], dtype=np.float32)
    episode_summaries = []
    if "episode_summaries_json" in data:
        episode_summaries = json.loads(str(data["episode_summaries_json"].item()))
    elif "episode_summaries" in data:
        episode_summaries = data["episode_summaries"].tolist()
    if observations.ndim != 2:
        raise ValueError(f"observations must be rank-2, got {observations.shape}")
    if actions.ndim != 2 or actions.shape[-1] != 3:
        raise ValueError(f"actions must have shape [N, 3], got {actions.shape}")
    if observations.shape[0] != actions.shape[0]:
        raise ValueError(f"observation/action length mismatch: {observations.shape[0]} vs {actions.shape[0]}")
    return observations, actions, episode_summaries


def load_dataset_dir(path, target_agent_only=False):
    """Load a corrected_v2 collection directory written by the world-model trainer.

    Each episode directory holds ``transitions.npz`` with observations packed
    exactly the way the world model consumes them, so the quality actor trained
    here shares the observation protocol of the corrected checkpoint.
    """
    root = Path(path)
    raw = root / "raw"
    if not raw.is_dir():
        raise FileNotFoundError(f"{path} does not contain a raw/ episode directory")
    observations, actions, episode_summaries = [], [], []
    for episode_dir in sorted(raw.iterdir()):
        npz = episode_dir / "transitions.npz"
        if not npz.is_file():
            continue
        with np.load(npz) as data:
            obs = np.asarray(data["obs"], dtype=np.float32)
            act = np.asarray(data["action"], dtype=np.float32)
        if target_agent_only:
            obs = obs[:, -1]
            act = act[:, -1]
        observations.append(obs.reshape(-1, obs.shape[-1]))
        actions.append(act.reshape(-1, act.shape[-1]))
        summary_path = episode_dir / "summary.json"
        if summary_path.is_file():
            episode_summaries.append(json.loads(summary_path.read_text(encoding="utf-8")))
    if not observations:
        raise FileNotFoundError(f"no transitions.npz found under {raw}")
    observations = np.concatenate(observations, axis=0)
    actions = np.concatenate(actions, axis=0)
    if observations.ndim != 2:
        raise ValueError(f"observations must be rank-2, got {observations.shape}")
    if actions.ndim != 2 or actions.shape[-1] != 3:
        raise ValueError(f"actions must have shape [N, 3], got {actions.shape}")
    return observations, actions, episode_summaries


def compute_graph_stats(obs, ego_dim=17, opponent_dim=OPPONENT_DIM, use_slot_mask=False, slot_feature_dim=OPPONENT_DIM):
    ego = obs[..., :ego_dim].reshape(-1, ego_dim)
    opponent = obs[..., ego_dim:].reshape(-1, max((obs.shape[-1] - ego_dim) // opponent_dim, 0), opponent_dim)
    opponent = opponent.reshape(-1, opponent_dim) if opponent.size else np.zeros((1, opponent_dim), dtype=np.float32)
    if use_slot_mask:
        feature = opponent[:, :slot_feature_dim]
        valid = opponent[:, slot_feature_dim] > 0.5 if opponent.shape[1] > slot_feature_dim else np.ones(opponent.shape[0], dtype=bool)
        opponent_for_stats = feature[valid] if np.any(valid) else np.zeros((1, slot_feature_dim), dtype=np.float32)
    else:
        opponent_for_stats = opponent
    ego_std = np.maximum(ego.std(axis=0), 1e-3)
    opponent_std = np.maximum(opponent_for_stats.std(axis=0), 1e-3)
    return {
        "ego_mean": ego.mean(axis=0).astype(np.float32),
        "ego_std": ego_std.astype(np.float32),
        "opponent_mean": opponent_for_stats.mean(axis=0).astype(np.float32),
        "opponent_std": opponent_std.astype(np.float32),
    }


def normalize_obs(obs, stats, ego_dim=17, opponent_dim=OPPONENT_DIM, use_slot_mask=False, slot_feature_dim=OPPONENT_DIM):
    norm = np.zeros_like(obs, dtype=np.float32)
    norm[..., :ego_dim] = (obs[..., :ego_dim] - stats["ego_mean"]) / stats["ego_std"]
    opponent = obs[..., ego_dim:]
    if opponent.shape[-1] > 0:
        opponent = opponent.reshape(*opponent.shape[:-1], -1, opponent_dim)
        if use_slot_mask:
            feature = opponent[..., :slot_feature_dim]
            mask = opponent[..., slot_feature_dim:]
            feature = (feature - stats["opponent_mean"]) / stats["opponent_std"]
            opponent = np.concatenate([feature, mask], axis=-1)
        else:
            opponent = (opponent - stats["opponent_mean"]) / stats["opponent_std"]
        norm[..., ego_dim:] = opponent.reshape(*norm[..., ego_dim:].shape)
    return norm


def train_actor(args, obs, actions, stats):
    device = torch.device(args.device if args.device != "auto" else ("cuda:0" if torch.cuda.is_available() else "cpu"))
    torch.manual_seed(args.seed)
    actor = PermutationInvariantActor(
        hidden_dim=args.hidden_dim,
        opponent_dim=args.opponent_dim,
        use_slot_mask=args.use_slot_mask,
        slot_feature_dim=args.slot_feature_dim,
    ).to(device)
    optimizer = torch.optim.Adam(actor.parameters(), lr=args.lr)
    if args.neighbor_keep_prob < 1.0:
        obs = np.stack(
            [
                randomize_neighbor_slots(
                    row[None, :],
                    keep_prob=args.neighbor_keep_prob,
                    max_neighbors=args.max_neighbors,
                    seed=args.seed + idx,
                )[0]
                for idx, row in enumerate(obs)
            ],
            axis=0,
        )
    norm_obs = normalize_obs(
        obs,
        stats,
        args.ego_dim,
        args.opponent_dim,
        use_slot_mask=args.use_slot_mask,
        slot_feature_dim=args.slot_feature_dim,
    )
    obs_tensor = torch.as_tensor(norm_obs, dtype=torch.float32, device=device)
    action_tensor = torch.as_tensor(actions, dtype=torch.float32, device=device)
    rng = np.random.default_rng(args.seed)
    losses = []
    for step in range(1, args.train_steps + 1):
        indices = rng.integers(0, obs_tensor.shape[0], size=args.batch_size)
        batch_obs = obs_tensor[indices]
        batch_action = action_tensor[indices]
        pred = actor(batch_obs)
        loss = F.mse_loss(pred, batch_action)
        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(actor.parameters(), 10.0)
        optimizer.step()
        losses.append(float(loss.detach().cpu()))
    return actor.cpu(), losses


def main():
    parser = argparse.ArgumentParser(description="Train permutation-invariant graph actor by behavior cloning.")
    parser.add_argument("--num-agents", type=int, default=4)
    parser.add_argument("--min-agents", type=int, default=4)
    parser.add_argument("--max-agents", type=int, default=6)
    parser.add_argument("--episodes", type=int, default=24)
    parser.add_argument("--max-steps", type=int, default=2600)
    parser.add_argument("--gap-tiles", type=int, default=22)
    parser.add_argument("--seed", type=int, default=3)
    parser.add_argument("--hidden-dim", type=int, default=128)
    parser.add_argument("--train-steps", type=int, default=1500)
    parser.add_argument("--batch-size", type=int, default=1024)
    parser.add_argument("--lr", type=float, default=3e-4)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--collection-workers", type=int, default=1)
    parser.add_argument("--dataset-npz", default="", help="Optional pre-filtered expert dataset with observations/actions arrays.")
    parser.add_argument("--dataset-dir", default="", help="corrected_v2 collection directory produced by train_graph_risk_world_model.py.")
    parser.add_argument("--target-agent-only", action="store_true", help="Keep only the target-agent column of a collection directory.")
    parser.add_argument("--out-dir", default="outputs/graph_bc")
    parser.add_argument("--observation-type", default="telemetry_dynamic", choices=["telemetry", "telemetry_dynamic"])
    parser.add_argument("--ego-dim", type=int, default=17)
    parser.add_argument("--opponent-dim", type=int, default=7)
    parser.add_argument("--max-neighbors", type=int, default=3)
    parser.add_argument("--neighbor-keep-prob", type=float, default=0.85)
    parser.add_argument("--track-path", default="")
    parser.add_argument("--use-slot-mask", action="store_true")
    parser.add_argument("--slot-feature-dim", type=int, default=7)
    parser.add_argument("--telemetry-version", default="legacy_v1", choices=["legacy_v1", "corrected_v2"])
    args = parser.parse_args()
    if args.observation_type == "telemetry_dynamic":
        args.use_slot_mask = True
        args.opponent_dim = args.slot_feature_dim + 1
    if args.min_agents > args.max_agents:
        raise ValueError("--min-agents must be <= --max-agents")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    if args.dataset_dir:
        obs, actions, episode_summaries = load_dataset_dir(args.dataset_dir, args.target_agent_only)
    elif args.dataset_npz:
        obs, actions, episode_summaries = load_dataset_npz(args.dataset_npz)
    else:
        obs, actions, episode_summaries = collect_dataset(args)
    if args.telemetry_version == "corrected_v2" and not args.dataset_dir:
        raise ValueError("corrected_v2 behaviour cloning requires --dataset-dir from the corrected collection")
    stats = compute_graph_stats(
        obs,
        args.ego_dim,
        args.opponent_dim,
        use_slot_mask=args.use_slot_mask,
        slot_feature_dim=args.slot_feature_dim,
    )
    actor, losses = train_actor(args, obs, actions, stats)
    model_path = out_dir / "graph_bc.graph.pt"
    obs_dim = int(obs.shape[-1])
    opponent_dim = args.opponent_dim
    bundle = GraphActorBundle(
        actor=actor,
        obs_mean=np.zeros((obs_dim,), dtype=np.float32),
        obs_std=np.ones((obs_dim,), dtype=np.float32),
        meta={
            "name": "graph_bc",
            "ego_dim": args.ego_dim,
            "opponent_dim": opponent_dim,
            "use_slot_mask": bool(args.use_slot_mask),
            "slot_feature_dim": args.slot_feature_dim if args.use_slot_mask else args.opponent_dim,
            "obs_dim": obs_dim,
            "hidden_dim": args.hidden_dim,
            "action_dim": 3,
            "observation_type": args.observation_type,
            "max_neighbors": args.max_neighbors,
            "min_agents_train": args.min_agents,
            "max_agents_train": args.max_agents,
            "neighbor_keep_prob": args.neighbor_keep_prob,
            "num_agents_train": args.num_agents,
            "episodes": args.episodes,
            "max_steps": args.max_steps,
            "train_steps": args.train_steps,
            "batch_size": args.batch_size,
            "lr": args.lr,
            "device": args.device,
            "collection_workers": args.collection_workers,
            "dataset_npz": args.dataset_npz,
            "dataset_dir": args.dataset_dir,
            "target_agent_only": bool(args.target_agent_only),
            "telemetry_version": args.telemetry_version,
            "seed": args.seed,
            "source": "graph_behavior_cloning_filtered_dataset" if args.dataset_npz else "graph_behavior_cloning_multicar",
            "ego_mean": stats["ego_mean"].tolist(),
            "ego_std": stats["ego_std"].tolist(),
            "opponent_mean": stats["opponent_mean"].tolist(),
            "opponent_std": stats["opponent_std"].tolist(),
        },
    )
    bundle.save(model_path)
    summary = {
        "status": "PASS",
        "model_path": str(model_path),
        "episodes": args.episodes,
        "transitions": int(obs.shape[0]),
        "agent_samples": int(obs.shape[0]),
        "obs_shape": list(obs.shape),
        "action_shape": list(actions.shape),
        "loss_final": losses[-1],
        "loss_mean_last_100": float(np.mean(losses[-100:])),
        "episode_summaries": episode_summaries,
        "args": vars(args),
    }
    (out_dir / "train_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
