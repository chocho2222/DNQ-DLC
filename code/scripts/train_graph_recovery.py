#!/usr/bin/env python
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dlc.graph_policy import GraphActorBundle, PermutationInvariantActor
from dlc.policies import TelemetryLanePolicy
from dlc.rollout import make_env
from scripts.generate_multicar_overtake_gif import make_background_policies
from scripts.train_graph_bc import compute_graph_stats, normalize_obs


def make_recovery_policies(num_agents, target_agent, target_speed):
    policies = make_background_policies(
        num_agents,
        target_agent,
        "telemetry_cruise,telemetry_yield,telemetry_lane",
    )
    policies[target_agent] = TelemetryLanePolicy(target_speed=target_speed, name="recovery_target_lane")
    return policies


def policy_actions(env, obs, policies):
    actions = np.zeros((env.unwrapped.num_agents, 3), dtype=np.float32)
    for agent_id, policy in enumerate(policies):
        actions[agent_id] = policy.act(env, obs)[agent_id]
    return actions


def collect_recovery(args):
    observations = []
    actions = []
    weights = []
    summaries = []
    target_agent = args.num_agents - 1
    recovery_seeds = {int(item) for item in args.recovery_seeds.split(",") if item.strip()}
    support_seeds = {int(item) for item in args.support_seeds.split(",") if item.strip()}
    seeds = sorted(recovery_seeds | support_seeds)
    for seed in seeds:
        for repeat in range(args.recovery_repeats):
            env = make_env(
                num_agents=args.num_agents,
                seed=seed + repeat * 1000,
                observation_type=args.observation_type,
                start_order=[2 * agent_id for agent_id in range(args.num_agents)],
                line_spacing=args.gap_tiles,
                lateral_spacing=0.0,
                max_neighbors=args.max_neighbors,
            )
            env._max_episode_steps = args.max_steps + 1
            policies = make_recovery_policies(args.num_agents, target_agent, args.target_speed)
            for policy in policies:
                policy.reset()
            obs = env.reset()
            grass_steps = np.zeros(args.num_agents, dtype=np.float64)
            ep_obs = []
            ep_actions = []
            ep_weights = []
            try:
                for step in range(args.max_steps):
                    action = policy_actions(env, obs, policies)
                    ep_obs.append(obs.astype(np.float32))
                    ep_actions.append(action.astype(np.float32))
                    state_weight = np.ones(args.num_agents, dtype=np.float32)
                    state_weight[target_agent] = args.target_weight
                    if seed in support_seeds:
                        state_weight[target_agent] *= args.support_weight
                    if obs[target_agent, 15] > 0.5 or abs(float(obs[target_agent, 12])) > 0.45:
                        state_weight[target_agent] *= args.recovery_weight
                    ep_weights.append(state_weight)
                    obs, _, done, _ = env.step(action)
                    grass_steps += obs[:, 15] > 0.5
                    if done:
                        break
                target_done = env.unwrapped.tile_visited_count[target_agent] >= len(env.unwrapped.track)
                target_grass = float(grass_steps[target_agent] / max(step + 1, 1))
                keep_episode = (
                    not args.filter_success
                    or (target_done and target_grass <= args.max_target_grass_rate)
                )
                if keep_episode:
                    observations.extend(ep_obs)
                    actions.extend(ep_actions)
                    weights.extend(ep_weights)
                summaries.append(
                    {
                        "seed": seed,
                        "repeat": repeat,
                        "steps": step + 1,
                        "done": bool(done),
                        "target_done": bool(target_done),
                        "target_grass_rate": target_grass,
                        "kept": bool(keep_episode),
                        "tile_visited_count": list(env.unwrapped.tile_visited_count),
                        "grass_rate": (grass_steps / max(step + 1, 1)).tolist(),
                    }
                )
            finally:
                env.close()
    return (
        np.asarray(observations, dtype=np.float32),
        np.asarray(actions, dtype=np.float32),
        np.asarray(weights, dtype=np.float32),
        summaries,
    )


def train(args, obs, actions, weights, stats):
    device = torch.device(args.device if args.device != "auto" else ("cuda:0" if torch.cuda.is_available() else "cpu"))
    torch.manual_seed(args.seed)
    init_meta = {}
    if args.init_model:
        bundle = GraphActorBundle.load(args.init_model, map_location=device)
        init_meta = bundle.meta
    actor = PermutationInvariantActor(
        hidden_dim=int(init_meta.get("hidden_dim", args.hidden_dim)),
        opponent_dim=int(init_meta.get("opponent_dim", 7)),
        use_slot_mask=bool(init_meta.get("use_slot_mask", False)),
        slot_feature_dim=init_meta.get("slot_feature_dim"),
    ).to(device)
    if args.init_model:
        actor.load_state_dict(bundle.actor.state_dict())
    optimizer = torch.optim.Adam(actor.parameters(), lr=args.lr)
    norm_obs = normalize_obs(
        obs,
        stats,
        opponent_dim=int(init_meta.get("opponent_dim", 7)),
        use_slot_mask=bool(init_meta.get("use_slot_mask", False)),
        slot_feature_dim=int(init_meta.get("slot_feature_dim", 7)),
    )
    flat_obs = norm_obs.reshape(-1, norm_obs.shape[-1])
    flat_actions = actions.reshape(-1, actions.shape[-1])
    flat_weights = weights.reshape(-1)
    obs_tensor = torch.as_tensor(flat_obs, dtype=torch.float32, device=device)
    action_tensor = torch.as_tensor(flat_actions, dtype=torch.float32, device=device)
    weight_tensor = torch.as_tensor(flat_weights, dtype=torch.float32, device=device)
    rng = np.random.default_rng(args.seed)
    losses = []
    for _ in range(args.train_steps):
        idx = rng.integers(0, obs_tensor.shape[0], size=args.batch_size)
        pred = actor(obs_tensor[idx])
        per = F.mse_loss(pred, action_tensor[idx], reduction="none").mean(dim=-1)
        loss = (per * weight_tensor[idx]).mean() / torch.clamp(weight_tensor[idx].mean(), min=1e-6)
        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(actor.parameters(), 10.0)
        optimizer.step()
        losses.append(float(loss.detach().cpu()))
    return actor.cpu(), losses


def main():
    parser = argparse.ArgumentParser(description="Train graph actor with hard-case recovery data.")
    parser.add_argument("--num-agents", type=int, default=4)
    parser.add_argument("--recovery-seeds", default="7")
    parser.add_argument("--support-seeds", default="")
    parser.add_argument("--recovery-repeats", type=int, default=1)
    parser.add_argument("--max-steps", type=int, default=3200)
    parser.add_argument("--gap-tiles", type=int, default=22)
    parser.add_argument("--target-speed", type=float, default=22.0)
    parser.add_argument("--observation-type", default="telemetry_dynamic", choices=["telemetry", "telemetry_dynamic"])
    parser.add_argument("--max-neighbors", type=int, default=3)
    parser.add_argument("--target-weight", type=float, default=3.0)
    parser.add_argument("--support-weight", type=float, default=1.0)
    parser.add_argument("--recovery-weight", type=float, default=4.0)
    parser.add_argument("--filter-success", action="store_true")
    parser.add_argument("--max-target-grass-rate", type=float, default=0.08)
    parser.add_argument("--hidden-dim", type=int, default=128)
    parser.add_argument("--train-steps", type=int, default=1200)
    parser.add_argument("--batch-size", type=int, default=1024)
    parser.add_argument("--lr", type=float, default=2e-4)
    parser.add_argument("--seed", type=int, default=31)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--init-model", default="outputs/paper_multicar_overtake_20260618/models/graph_bc/graph_bc.graph.pt")
    parser.add_argument("--out-dir", default="outputs/paper_multicar_overtake_20260618/models/graph_recovery")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    obs, actions, weights, summaries = collect_recovery(args)
    if obs.size == 0:
        raise RuntimeError("no recovery episodes passed the quality filter")
    if args.init_model:
        init = GraphActorBundle.load(args.init_model, map_location="cpu")
        stats = {
            "ego_mean": np.asarray(init.meta["ego_mean"], dtype=np.float32),
            "ego_std": np.asarray(init.meta["ego_std"], dtype=np.float32),
            "opponent_mean": np.asarray(init.meta["opponent_mean"], dtype=np.float32),
            "opponent_std": np.asarray(init.meta["opponent_std"], dtype=np.float32),
        }
    else:
        stats = compute_graph_stats(obs)
    actor, losses = train(args, obs, actions, weights, stats)
    model_path = out_dir / "graph_recovery.graph.pt"
    bundle = GraphActorBundle(
        actor=actor,
        obs_mean=np.zeros((obs.shape[-1],), dtype=np.float32),
        obs_std=np.ones((obs.shape[-1],), dtype=np.float32),
        meta={
            "name": "graph_recovery",
            "ego_dim": 17,
            "opponent_dim": 7,
            "use_slot_mask": bool(getattr(actor, "use_slot_mask", False)),
            "slot_feature_dim": int(getattr(actor, "slot_feature_dim", 7)),
            "hidden_dim": args.hidden_dim,
            "action_dim": 3,
            "obs_dim": int(obs.shape[-1]),
            "source": "graph_recovery_weighted_behavior_cloning",
            "init_model": args.init_model,
            "recovery_seeds": args.recovery_seeds,
            "observation_type": args.observation_type,
            "max_neighbors": args.max_neighbors,
            "train_steps": args.train_steps,
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
        "transitions": int(obs.shape[0]),
        "agent_samples": int(obs.shape[0] * obs.shape[1]),
        "loss_final": losses[-1],
        "loss_mean_last_100": float(np.mean(losses[-100:])),
        "recovery_summaries": summaries,
    }
    (out_dir / "train_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
