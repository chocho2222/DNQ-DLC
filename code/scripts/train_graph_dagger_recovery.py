#!/usr/bin/env python
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dlc.graph_policy import GraphActorBundle, GraphActorPolicy, PermutationInvariantActor
from dlc.policies import (
    TelemetryAdaptiveGatePolicy,
    TelemetryExpertGatePolicy,
    TelemetryLanePolicy,
    TelemetryOvertakePolicy,
)
from dlc.rollout import make_env
from scripts.generate_multicar_overtake_gif import make_background_policies
from scripts.train_graph_bc import compute_graph_stats, normalize_obs


def parse_ints(value):
    return [int(item.strip()) for item in value.split(",") if item.strip()]


def make_oracle(name, target_speed):
    if name == "lane":
        return TelemetryLanePolicy(target_speed=target_speed, name="dagger_oracle_lane")
    if name == "overtake":
        return TelemetryOvertakePolicy(
            target_speed=target_speed,
            pass_speed=target_speed + 3.0,
            pass_lane_offset=1.8,
            name="dagger_oracle_overtake",
        )
    if name == "adaptive":
        return TelemetryAdaptiveGatePolicy(
            target_speed=target_speed,
            pass_speed=target_speed + 2.5,
            pass_lane_offset=1.2,
            recovery_lateral=0.36,
            recovery_heading_cos=0.64,
            recovery_hold=48,
            pass_hold=10,
            clear_hold=6,
            heading_gain=1.80,
            lateral_gain=0.62,
            gas=0.56,
            brake=0.45,
            name="dagger_oracle_adaptive",
        )
    if name == "expert_gate":
        return TelemetryExpertGatePolicy(name="dagger_oracle_expert_gate")
    raise ValueError(f"unknown oracle policy: {name}")


def mixed_actions(env, obs, background_policies, target_agent, target_action):
    actions = np.zeros((env.unwrapped.num_agents, 3), dtype=np.float32)
    for agent_id, policy in enumerate(background_policies):
        if agent_id == target_agent:
            actions[agent_id] = target_action
        else:
            policy_action = policy.act(env, obs)
            actions[agent_id] = policy_action[agent_id]
    return actions


def hard_state_reason(obs_row, args):
    reasons = []
    if float(obs_row[15]) > 0.5:
        reasons.append("grass")
    if abs(float(obs_row[12])) > args.hard_lateral:
        reasons.append("lateral")
    if float(obs_row[14]) < args.hard_heading_cos:
        reasons.append("heading")
    if float(obs_row[16]) > 0.5:
        reasons.append("backward")
    if float(obs_row[4]) * 50.0 < args.hard_min_speed:
        reasons.append("slow")
    return reasons


def collect_rollout_states(args, seeds, model_path, hard):
    observations = []
    actions = []
    weights = []
    summaries = []
    target_agent = args.num_agents - 1
    model_policy = GraphActorPolicy(
        model_path,
        device=args.device,
        neighbor_mode=args.neighbor_mode,
        max_neighbors=args.max_neighbors,
    )
    oracle = make_oracle(args.oracle_policy, args.target_speed)

    for seed in seeds:
        for repeat in range(args.repeats):
            env_seed = seed + repeat * 1000
            env = make_env(
                num_agents=args.num_agents,
                seed=env_seed,
                observation_type=args.observation_type,
                start_order=[2 * agent_id for agent_id in range(args.num_agents)],
                line_spacing=args.gap_tiles,
                lateral_spacing=0.0,
                max_neighbors=args.max_neighbors,
            )
            env._max_episode_steps = args.max_steps + 1
            background = make_background_policies(
                args.num_agents,
                target_agent,
                args.baseline_policies,
            )
            for policy in background:
                if policy is not None:
                    policy.reset()
            model_policy.reset()
            oracle.reset()
            obs = env.reset()
            grass_steps = np.zeros(args.num_agents, dtype=np.float64)
            kept = 0
            reason_counts = {}
            try:
                for step in range(args.max_steps):
                    learned = model_policy.act(env, obs)[target_agent]
                    oracle_action = oracle.act(env, obs)[target_agent]
                    reasons = hard_state_reason(obs[target_agent], args)
                    keep = bool(reasons) if hard else (step % args.support_stride == 0)
                    if keep:
                        observations.append(obs.astype(np.float32))
                        label = np.zeros((args.num_agents, 3), dtype=np.float32)
                        label[:] = mixed_actions(env, obs, background, target_agent, oracle_action)
                        actions.append(label)
                        sample_weight = np.ones(args.num_agents, dtype=np.float32)
                        sample_weight[target_agent] = args.hard_target_weight if hard else args.support_target_weight
                        if reasons:
                            sample_weight[target_agent] *= args.reason_weight
                        weights.append(sample_weight)
                        kept += 1
                        for reason in reasons or ["support"]:
                            reason_counts[reason] = reason_counts.get(reason, 0) + 1
                    env_action = mixed_actions(env, obs, background, target_agent, learned)
                    obs, _, done, _ = env.step(env_action)
                    grass_steps += obs[:, 15] > 0.5
                    if done:
                        break
                summaries.append(
                    {
                        "seed": seed,
                        "env_seed": env_seed,
                        "repeat": repeat,
                        "hard": hard,
                        "steps": step + 1,
                        "kept_states": kept,
                        "reason_counts": reason_counts,
                        "tile_visited_count": list(env.unwrapped.tile_visited_count),
                        "grass_rate": (grass_steps / max(step + 1, 1)).tolist(),
                    }
                )
            finally:
                env.close()
    return observations, actions, weights, summaries


def collect_dataset(args):
    hard_seeds = parse_ints(args.hard_seeds)
    support_seeds = parse_ints(args.support_seeds)
    observations = []
    actions = []
    weights = []
    summaries = []

    hard_obs, hard_actions, hard_weights, hard_summaries = collect_rollout_states(
        args,
        hard_seeds,
        args.init_model,
        hard=True,
    )
    observations.extend(hard_obs)
    actions.extend(hard_actions)
    weights.extend(hard_weights)
    summaries.extend(hard_summaries)

    if support_seeds:
        support_obs, support_actions, support_weights, support_summaries = collect_rollout_states(
            args,
            support_seeds,
            args.init_model,
            hard=False,
        )
        observations.extend(support_obs)
        actions.extend(support_actions)
        weights.extend(support_weights)
        summaries.extend(support_summaries)

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
    optimizer = torch.optim.Adam(actor.parameters(), lr=args.lr, weight_decay=args.weight_decay)
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
        torch.nn.utils.clip_grad_norm_(actor.parameters(), args.grad_clip)
        optimizer.step()
        losses.append(float(loss.detach().cpu()))
    return actor.cpu(), losses


def main():
    parser = argparse.ArgumentParser(description="Train graph actor with DAgger-style hard-state recovery labels.")
    parser.add_argument("--num-agents", type=int, default=4)
    parser.add_argument("--hard-seeds", default="61,71,89")
    parser.add_argument("--support-seeds", default="3,7,11,17,23,29,31,37,41,43")
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--max-steps", type=int, default=1800)
    parser.add_argument("--gap-tiles", type=int, default=22)
    parser.add_argument("--target-speed", type=float, default=20.0)
    parser.add_argument("--baseline-policies", default="telemetry_cruise,telemetry_yield,telemetry_lane")
    parser.add_argument("--observation-type", default="telemetry_dynamic", choices=["telemetry", "telemetry_dynamic"])
    parser.add_argument("--neighbor-mode", default="dynamic", choices=["fixed", "dynamic"])
    parser.add_argument("--max-neighbors", type=int, default=3)
    parser.add_argument("--oracle-policy", default="adaptive", choices=["lane", "overtake", "adaptive", "expert_gate"])
    parser.add_argument("--hard-lateral", type=float, default=0.34)
    parser.add_argument("--hard-heading-cos", type=float, default=0.68)
    parser.add_argument("--hard-min-speed", type=float, default=3.0)
    parser.add_argument("--hard-target-weight", type=float, default=8.0)
    parser.add_argument("--support-target-weight", type=float, default=1.5)
    parser.add_argument("--reason-weight", type=float, default=2.0)
    parser.add_argument("--support-stride", type=int, default=8)
    parser.add_argument("--hidden-dim", type=int, default=128)
    parser.add_argument("--train-steps", type=int, default=2000)
    parser.add_argument("--batch-size", type=int, default=2048)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--weight-decay", type=float, default=1e-5)
    parser.add_argument("--grad-clip", type=float, default=10.0)
    parser.add_argument("--seed", type=int, default=47)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--init-model", default="outputs/paper_multicar_overtake_20260618/models/graph_bc/graph_bc.graph.pt")
    parser.add_argument("--out-dir", default="outputs/paper_multicar_overtake_20260618/models/graph_dagger_recovery")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    obs, actions, weights, summaries = collect_dataset(args)
    if obs.size == 0:
        raise RuntimeError("no DAgger states were collected")
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
    model_path = out_dir / "graph_dagger_recovery.graph.pt"
    bundle = GraphActorBundle(
        actor=actor,
        obs_mean=np.zeros((obs.shape[-1],), dtype=np.float32),
        obs_std=np.ones((obs.shape[-1],), dtype=np.float32),
        meta={
            "name": "graph_dagger_recovery",
            "ego_dim": 17,
            "opponent_dim": 7,
            "use_slot_mask": bool(getattr(actor, "use_slot_mask", False)),
            "slot_feature_dim": int(getattr(actor, "slot_feature_dim", 7)),
            "hidden_dim": args.hidden_dim,
            "action_dim": 3,
            "obs_dim": int(obs.shape[-1]),
            "source": "dagger_hard_state_recovery",
            "init_model": args.init_model,
            "hard_seeds": args.hard_seeds,
            "support_seeds": args.support_seeds,
            "oracle_policy": args.oracle_policy,
            "observation_type": args.observation_type,
            "neighbor_mode": args.neighbor_mode,
            "max_neighbors": args.max_neighbors,
            "train_steps": args.train_steps,
            "ego_mean": stats["ego_mean"].tolist(),
            "ego_std": stats["ego_std"].tolist(),
            "opponent_mean": stats["opponent_mean"].tolist(),
            "opponent_std": stats["opponent_std"].tolist(),
        },
    )
    bundle.save(model_path)
    reason_totals = {}
    for item in summaries:
        for reason, count in item["reason_counts"].items():
            reason_totals[reason] = reason_totals.get(reason, 0) + count
    summary = {
        "status": "PASS",
        "model_path": str(model_path),
        "transitions": int(obs.shape[0]),
        "agent_samples": int(obs.shape[0] * obs.shape[1]),
        "obs_shape": list(obs.shape),
        "action_shape": list(actions.shape),
        "weight_mean": float(weights.mean()),
        "weight_max": float(weights.max()),
        "reason_totals": reason_totals,
        "loss_final": losses[-1],
        "loss_mean_last_100": float(np.mean(losses[-100:])),
        "dagger_summaries": summaries,
        "args": vars(args),
    }
    (out_dir / "train_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
