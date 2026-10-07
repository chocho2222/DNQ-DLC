#!/usr/bin/env python
import argparse
import concurrent.futures
import json
import gzip
import hashlib
import importlib.metadata
import math
import platform
import time
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import pyglet
pyglet.options['headless'] = True
import numpy as np
import torch
import torch.nn.functional as F

from dlc.graph_policy import OPPONENT_DIM, PermutationInvariantActor, randomize_neighbor_slots
from dlc.graph_world_model import GraphTransitionModel, GraphWorldModelBundle
from dlc.policies import (
    TelemetryBarrierExpertGatePolicy,
    TelemetryCruisePolicy,
    TelemetryLanePolicy,
    TelemetryOvertakePolicy,
    TelemetryYieldPolicy,
)
from dlc.rollout import make_env
from dlc.training_packing import pack_transition_pair, promote_priority_channel
from dlc.joint_clearance_pilot import JointClearancePilot
from dlc.overtaking_endpoint import EndpointConfig, OvertakingEndpoint, TrackProgress
from scripts.tits_figure_style import bind_algorithm_colors


def make_expert_policies(num_agents, target_agent, expert_source='legacy_rule', background_profile='legacy_mixed'):
    policies = []
    for agent_id in range(num_agents):
        if agent_id == target_agent:
            if expert_source == 'joint_clearance_pilot':
                policies.append(JointClearancePilot())
                continue
            policies.append(
                TelemetryOvertakePolicy(
                    target_speed=22.0,
                    pass_speed=26.0,
                    pass_lane_offset=2.0,
                    trigger_distance=42.0,
                    name="target_overtake_expert",
                )
            )
        elif background_profile == 'lane13':
            policies.append(TelemetryLanePolicy(target_speed=13.0, name=f'lane_{agent_id}'))
        elif agent_id % 3 == 0:
            policies.append(TelemetryLanePolicy(target_speed=13.5, name=f"lane_{agent_id}"))
        elif agent_id % 3 == 1:
            policies.append(TelemetryYieldPolicy(target_speed=14.5, yield_speed=9.5, name=f"yield_{agent_id}"))
        else:
            policies.append(TelemetryCruisePolicy(target_speed=15.5, name=f"cruise_{agent_id}"))
    return policies


def policy_actions(env, obs, policies):
    action = np.zeros((env.unwrapped.num_agents, 3), dtype=np.float32)
    for agent_id, policy in enumerate(policies):
        action[agent_id] = policy.act(env, obs)[agent_id]
    return action


def sample_num_agents(args, rng):
    if args.min_agents == args.max_agents:
        return int(args.min_agents)
    return int(rng.integers(args.min_agents, args.max_agents + 1))


def collect_episode_worker(payload):
    try:
        return _collect_episode_worker(payload)
    except Exception as error:
        args, episode, num_agents = payload
        if args.get('telemetry_version') == 'corrected_v2':
            ledger = Path(args['out_dir'])/'collection_errors'
            ledger.mkdir(parents=True, exist_ok=True)
            (ledger/f'episode_{episode:05d}.json').write_text(json.dumps({
                'episode': episode, 'seed': args['seed']+episode, 'num_agents': num_agents,
                'error': repr(error), 'status': 'failed; not excluded or retried silently'}, indent=2))
        raise


def _collect_episode_worker(payload):
    args_dict, episode, num_agents = payload
    args = argparse.Namespace(**args_dict)
    transitions = []
    seed = args.seed + episode
    target_agent = num_agents - 1
    corrected = getattr(args, 'telemetry_version', 'legacy_v1') == 'corrected_v2'
    raw_dir = Path(args.out_dir)/'raw'/f'episode_{episode:05d}_n{num_agents}_seed{seed}' if corrected else None
    if raw_dir is not None:
        raw_dir.mkdir(parents=True, exist_ok=False)
    env = make_env(
        num_agents=num_agents,
        seed=seed,
        observation_type=args.observation_type,
        start_order=[agent_id*(1 if getattr(args, 'start_layout', 'single_file') == 'paired' else 2)
                     for agent_id in range(num_agents)],
        line_spacing=args.gap_tiles,
        lateral_spacing=args.lateral_spacing,
        track_path=args.track_path or None,
        max_neighbors=None if corrected else args.max_neighbors,
        telemetry_version=getattr(args, 'telemetry_version', 'legacy_v1'),
        neighbor_order='identity' if corrected else 'relevance',
    )
    if hasattr(env, "_max_episode_steps"):
        env._max_episode_steps = args.max_steps + 1
    policies = make_expert_policies(num_agents, target_agent, getattr(args, 'expert_source', 'legacy_rule'),
                                   getattr(args, 'background_profile', 'legacy_mixed'))
    for policy in policies:
        policy.reset()
    obs = env.reset()
    bind_algorithm_colors(env, ['background_lane']*target_agent + [getattr(args, 'expert_source', 'legacy_rule')])
    records = []
    progress, endpoint, stream = None, None, None
    if raw_dir is not None:
        progress = TrackProgress(np.asarray(env.unwrapped.track)[:, 2:])
        initial_progress = progress.update([list(c.hull.position) for c in env.unwrapped.cars])
        endpoint = OvertakingEndpoint(initial_progress, progress.length, target_agent,
            EndpointConfig(horizon=args.max_steps), env.unwrapped.vehicle_contacts.snapshot(env.unwrapped.world),
            obs[:, 15], obs[:, 16])
        stream = gzip.open(raw_dir/'step_records.jsonl.gz', 'xt')
        (raw_dir/'initial.json').write_text(json.dumps({
            'case_id': raw_dir.name, 'split': args.data_split, 'seed': seed, 'num_agents': num_agents,
            'track': env.unwrapped.track, 'obs': obs.tolist(),
            'positions': [list(c.hull.position) for c in env.unwrapped.cars],
            'angles': [float(c.hull.angle) for c in env.unwrapped.cars],
            'neighbor_ids': env.unwrapped.last_dynamic_neighbor_ids,
            'color_assignment': env.unwrapped.algorithm_color_assignment,
            'config': vars(args)}, indent=2))
    grass_steps = np.zeros(num_agents, dtype=np.float64)
    total_reward = np.zeros(num_agents, dtype=np.float64)
    done = False
    step = -1
    try:
        for step in range(args.max_steps):
            ids = [list(v) for v in env.unwrapped.last_dynamic_neighbor_ids] if corrected else None
            action = policy_actions(env, obs, policies)
            next_obs, reward, done, info = env.step(action)
            train_obs, train_next = obs, next_obs
            if corrected:
                progress_s = progress.update([list(c.hull.position) for c in env.unwrapped.cars])
                endpoint.update(step+1, progress_s, info['vehicle_contacts'], next_obs[:, 15], next_obs[:, 16])
                train_obs, train_next, selected_ids = pack_transition_pair(
                    obs, next_obs, ids, info['neighbor_ids'], args.max_neighbors, args.neighbor_selection)
                records.append({'step': step+1, 'neighbor_ids_before': ids,
                    'neighbor_ids_after': info['neighbor_ids'], 'selected_ids': selected_ids,
                    'full_obs': obs.tolist(), 'full_next_obs': next_obs.tolist(),
                    'action': action.tolist(), 'reward': reward.tolist(), 'progress_s': progress_s.tolist(),
                    'teacher_debug': getattr(policies[target_agent], 'last_decision_debug', None),
                    'positions': [list(c.hull.position) for c in env.unwrapped.cars],
                    'angles': [float(c.hull.angle) for c in env.unwrapped.cars],
                    'velocities': [list(c.hull.linearVelocity) for c in env.unwrapped.cars],
                    'contacts': info['vehicle_contacts'], 'done': bool(done),
                    'time_limit_truncated': bool(info.get('TimeLimit.truncated', False))})
                stream.write(json.dumps(records[-1])+'\n')
                stream.flush()
            risk = ((next_obs[:, 15] > 0.5) | (next_obs[:, 16] > 0.5) | (np.abs(next_obs[:, 12]) > args.risk_lateral)).astype(np.float32)
            transitions.append(
                {
                    "obs": train_obs.astype(np.float32),
                    "action": action.astype(np.float32),
                    "next_obs": train_next.astype(np.float32),
                    "reward": reward.astype(np.float32),
                    "risk": risk,
                    "num_agents": int(num_agents),
                    "target_agent": int(target_agent),
                }
            )
            obs = next_obs
            total_reward += reward
            grass_steps += obs[:, 15] > 0.5
            if done:
                break
        steps = step + 1
        summary = {
            "status": "completed",
            "episode": episode,
            "seed": seed,
            "num_agents": int(num_agents),
            "steps": steps,
            "done": bool(done),
            "tile_visited_count": list(env.unwrapped.tile_visited_count),
            "grass_rate": (grass_steps / max(steps, 1)).tolist(),
            "total_reward": total_reward.tolist(),
            "endpoint": endpoint.result() if endpoint is not None else None,
            "expert_source": getattr(args, 'expert_source', 'legacy_rule'),
        }
    except Exception as error:
        if raw_dir is not None:
            (raw_dir/'error.json').write_text(json.dumps({'error': repr(error), 'step': step,
                'episode': episode, 'seed': seed, 'retained_transitions': len(transitions)}))
        raise
    finally:
        if stream is not None:
            stream.close()
        if raw_dir is not None:
            with gzip.open(raw_dir/'telemetry.json.gz', 'wt') as f:
                json.dump(records, f)
            if transitions:
                np.savez_compressed(raw_dir/'transitions.npz', **{
                    key: np.stack([r[key] for r in transitions])
                    for key in ['obs', 'action', 'next_obs', 'reward', 'risk']})
        env.close()
    if raw_dir is not None:
        (raw_dir/'summary.json').write_text(json.dumps(summary, indent=2))
    print(f'Collected episode {episode}, n={num_agents}, seed={seed}, steps={len(transitions)}', flush=True)
    return {"transitions": transitions, "summary": summary}


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
    transitions = []
    for row in results:
        transitions.extend(row["transitions"])
    episodes = [row["summary"] for row in results]
    return transitions, episodes


def load_saved_dataset(args):
    source = Path(args.dataset_dir)
    provenance = json.loads((source/'provenance.json').read_text())
    for key in ['telemetry_version', 'expert_source', 'background_profile', 'start_layout',
                'episodes', 'max_steps', 'min_agents', 'max_agents', 'gap_tiles', 'lateral_spacing',
                'seed', 'neighbor_selection', 'max_neighbors']:
        if provenance['args'][key] != getattr(args, key):
            raise ValueError(f'Saved dataset configuration differs for {key}')
    summaries = json.loads((source/'collection_summary.json').read_text())
    if len(summaries) != args.episodes or {r['episode'] for r in summaries} != set(range(args.episodes)):
        raise ValueError('Missing or duplicate episode in saved dataset')
    transitions, hashes = [], {}
    for summary in sorted(summaries, key=lambda r: r['episode']):
        if summary['status'] != 'completed':
            raise ValueError('Cannot silently drop a failed collection episode')
        path = source/'raw'/f"episode_{summary['episode']:05d}_n{summary['num_agents']}_seed{summary['seed']}"/'transitions.npz'
        hashes[str(path.resolve())] = hashlib.sha256(path.read_bytes()).hexdigest()
        with np.load(path, allow_pickle=False) as arrays:
            values = {k: arrays[k] for k in ['obs', 'action', 'next_obs', 'reward', 'risk']}
            steps = values['obs'].shape[0]
            if steps != summary['steps'] or not all(np.isfinite(v).all() and len(v) == steps for v in values.values()):
                raise ValueError(f'Invalid saved transitions: {path}')
            for i in range(steps):
                transitions.append({**{k: v[i] for k, v in values.items()},
                                    'num_agents': summary['num_agents'], 'target_agent': summary['num_agents']-1})
    (Path(args.out_dir)/'dataset_inputs.json').write_text(json.dumps({
        'source': str(source.resolve()), 'source_provenance_sha256': hashlib.sha256((source/'provenance.json').read_bytes()).hexdigest(),
        'transitions_sha256': hashes, 'episodes': len(summaries), 'transitions': len(transitions),
        'selection': 'all recorded episodes and transitions retained; no outcome filtering'}, indent=2))
    return transitions, summaries


def compute_stats(transitions, use_slot_mask=False, slot_feature_dim=OPPONENT_DIM):
    opponent_dim = slot_feature_dim + 1 if use_slot_mask else OPPONENT_DIM
    obs = np.concatenate([row["obs"] for row in transitions], axis=0).astype(np.float32)
    action = np.concatenate([row["action"] for row in transitions], axis=0).astype(np.float32)
    ego = obs[:, :17]
    opponent = obs[:, 17:].reshape(-1, max((obs.shape[-1] - 17) // opponent_dim, 0), opponent_dim)
    opponent = opponent.reshape(-1, opponent_dim) if opponent.size else np.zeros((1, opponent_dim), dtype=np.float32)
    if use_slot_mask:
        feature = opponent[:, :slot_feature_dim]
        valid = opponent[:, slot_feature_dim] > 0.5 if opponent.shape[1] > slot_feature_dim else np.ones(opponent.shape[0], dtype=bool)
        opponent_for_stats = feature[valid] if np.any(valid) else np.zeros((1, slot_feature_dim), dtype=np.float32)
    else:
        opponent_for_stats = opponent
    return {
        "obs_mean": obs.mean(axis=0, keepdims=False),
        "obs_std": np.maximum(obs.std(axis=0, keepdims=False), 1e-3),
        "action_mean": np.zeros((action.shape[-1],), dtype=np.float32),
        "action_std": np.ones((action.shape[-1],), dtype=np.float32),
        "opponent_dim": opponent_dim,
        "ego_mean": ego.mean(axis=0).astype(np.float32),
        "ego_std": np.maximum(ego.std(axis=0), 1e-3).astype(np.float32),
        "opponent_mean": opponent_for_stats.mean(axis=0).astype(np.float32),
        "opponent_std": np.maximum(opponent_for_stats.std(axis=0), 1e-3).astype(np.float32),
    }


def normalize_obs(obs, stats, use_slot_mask=False, slot_feature_dim=OPPONENT_DIM):
    obs = np.asarray(obs, dtype=np.float32)
    opponent_dim = int(stats["opponent_dim"])
    norm = np.zeros_like(obs, dtype=np.float32)
    norm[..., :17] = (obs[..., :17] - stats["ego_mean"]) / stats["ego_std"]
    opponent = obs[..., 17:]
    if opponent.shape[-1] > 0:
        opponent = opponent.reshape(*opponent.shape[:-1], -1, opponent_dim)
        if use_slot_mask:
            feature = opponent[..., :slot_feature_dim]
            mask = opponent[..., slot_feature_dim:]
            feature = (feature - stats["opponent_mean"]) / stats["opponent_std"]
            opponent = np.concatenate([feature, mask], axis=-1)
        else:
            opponent = (opponent - stats["opponent_mean"]) / stats["opponent_std"]
        norm[..., 17:] = opponent.reshape(*norm[..., 17:].shape)
    return norm


def maybe_randomize_obs(args, obs, seed_offset=0):
    if args.neighbor_keep_prob >= 1.0:
        return obs
    return np.stack(
        [
            randomize_neighbor_slots(
                row,
                keep_prob=args.neighbor_keep_prob,
                max_neighbors=args.max_neighbors,
                seed=args.seed + seed_offset + idx,
            )
            for idx, row in enumerate(obs)
        ],
        axis=0,
    )


def compute_quality_targets(raw_next_obs, args):
    obs = np.asarray(raw_next_obs, dtype=np.float32)
    lateral = np.abs(obs[..., 12])
    heading_cos = np.clip(obs[..., 14], -1.0, 1.0)
    heading_error = np.arccos(heading_cos)
    on_grass = obs[..., 15] > 0.5
    backward = obs[..., 16] > 0.5
    on_track = (~on_grass) & (~backward) & (lateral <= args.quality_on_track_lateral) & (heading_cos >= args.quality_heading_cos)
    lane_error = np.clip(lateral + 0.55 * heading_error, 0.0, args.quality_lane_error_clip) / args.quality_lane_error_clip
    forward_clearance = np.ones(obs.shape[:-1], dtype=np.float32)
    opponent_dim = args.slot_feature_dim + 1 if args.use_slot_mask else OPPONENT_DIM
    if obs.shape[-1] > 17:
        rel = obs[..., 17:].reshape(*obs.shape[:-1], -1, opponent_dim)
        if args.use_slot_mask:
            mask = rel[..., args.slot_feature_dim] > 0.5
            rel = rel[..., : args.slot_feature_dim]
        else:
            mask = np.ones(rel.shape[:-1], dtype=bool)
        rel_forward = rel[..., 0] * (2000 / 6.0)
        rel_left = np.abs(rel[..., 1] * (2000 / 6.0))
        ahead = mask & (rel_forward > 0.0) & (rel_forward < args.quality_forward_clip) & (rel_left < 18.0)
        clipped = np.where(ahead, np.clip(rel_forward / args.quality_forward_clip, 0.0, 1.0), 1.0)
        forward_clearance = clipped.min(axis=-1).astype(np.float32)
    return np.stack(
        [
            on_track.astype(np.float32),
            on_grass.astype(np.float32),
            lane_error.astype(np.float32),
            forward_clearance.astype(np.float32),
        ],
        axis=-1,
    ).astype(np.float32)


def batch_to_tensors(rows, stats, args, device):
    obs = np.stack([row["obs"] for row in rows]).astype(np.float32)
    action = np.stack([row["action"] for row in rows]).astype(np.float32)
    next_obs = np.stack([row["next_obs"] for row in rows]).astype(np.float32)
    reward = np.stack([row["reward"] for row in rows]).astype(np.float32)
    risk = np.stack([row["risk"] for row in rows]).astype(np.float32)
    quality = compute_quality_targets(next_obs, args)
    obs = maybe_randomize_obs(args, obs)
    if getattr(args, 'telemetry_version', 'legacy_v1') == 'corrected_v2':
        # Same random seed and slot order remove the same identities from both sides.
        next_obs = maybe_randomize_obs(args, next_obs)
    obs = normalize_obs(obs, stats, use_slot_mask=args.use_slot_mask, slot_feature_dim=args.slot_feature_dim)
    next_obs = normalize_obs(next_obs, stats, use_slot_mask=args.use_slot_mask, slot_feature_dim=args.slot_feature_dim)
    return (
        torch.as_tensor(obs, dtype=torch.float32, device=device),
        torch.as_tensor(action, dtype=torch.float32, device=device),
        torch.as_tensor(next_obs, dtype=torch.float32, device=device),
        torch.as_tensor(reward, dtype=torch.float32, device=device),
        torch.as_tensor(risk, dtype=torch.float32, device=device),
        torch.as_tensor(quality, dtype=torch.float32, device=device),
    )


SPEED_BALANCE_EDGES = (0.0, 1.0, 3.0, 6.0, 12.0, 18.0, 21.5, float("inf"))


def speed_bin_frequencies(transitions, edges=SPEED_BALANCE_EDGES):
    """Fraction of ego steps whose speed falls in each bin."""
    speeds = np.asarray([float(row["obs"][-1, 4]) * 50.0 for row in transitions], dtype=float)
    counts = np.zeros(len(edges) - 1, dtype=float)
    for index, (low, high) in enumerate(zip(edges[:-1], edges[1:])):
        counts[index] = float(((speeds >= low) & (speeds < high)).sum())
    total = max(counts.sum(), 1.0)
    return counts / total


def speed_balance_table(edges, frequencies, alpha):
    """Tempered inverse-frequency weight per speed bin, normalised to mean one."""
    weights = np.ones(len(frequencies), dtype=float)
    for index, freq in enumerate(frequencies):
        if freq > 0:
            weights[index] = freq ** (-float(alpha))
    return weights, float(weights.max())


def speed_balance_per_step(obs, weights, edges, speed_mean, speed_std):
    """Per-step BC/dynamics weight from the ego speed recovered from normalised obs."""
    import torch

    ego_speed = (obs[..., -1, 4] * speed_std + speed_mean) * 50.0
    table = torch.as_tensor(weights, dtype=ego_speed.dtype, device=ego_speed.device)
    edges_t = torch.as_tensor(edges[:-1], dtype=ego_speed.dtype, device=ego_speed.device)
    index = (torch.bucketize(ego_speed, edges_t, right=False) - 1).clamp(0, len(weights) - 1)
    per_step = table[index]
    return per_step / per_step.mean().clamp_min(1e-6)


def weighted_mse(prediction, target, weight):
    import torch

    residual = (prediction - target) ** 2
    while weight.dim() < residual.dim():
        weight = weight.unsqueeze(-1)
    return (residual * weight).mean()


def weighted_bce(logits, target, weight):
    import torch
    import torch.nn.functional as F

    loss = F.binary_cross_entropy_with_logits(logits, target, reduction="none")
    while weight.dim() < loss.dim():
        weight = weight.unsqueeze(-1)
    return (loss * weight).mean()


def train(args, transitions, stats):
    device = torch.device(args.device)
    seed = args.seed if args.train_seed is None else args.train_seed
    args.train_seed = seed
    rng = np.random.default_rng(seed)
    torch.manual_seed(seed)
    obs_dim = transitions[0]["obs"].shape[-1]
    action_dim = transitions[0]["action"].shape[-1]
    num_agents = args.max_agents
    transition = GraphTransitionModel(
        obs_dim=obs_dim,
        action_dim=action_dim,
        num_agents=num_agents,
        hidden_dim=args.hidden_dim,
        pooling_mode=args.pooling_mode,
        use_slot_mask=args.use_slot_mask,
        slot_feature_dim=args.slot_feature_dim,
        predict_residual=args.predict_residual,
        masked_pooling="attention" if args.masked_attention else "mean",
    ).to(device)
    proposal_actor = PermutationInvariantActor(
        hidden_dim=args.proposal_hidden_dim,
        action_dim=action_dim,
        opponent_dim=stats.get("opponent_dim", OPPONENT_DIM),
        use_slot_mask=args.use_slot_mask,
        slot_feature_dim=args.slot_feature_dim,
    ).to(device)
    optimizer = torch.optim.Adam(
        list(transition.parameters()) + list(proposal_actor.parameters()),
        lr=args.lr,
    )
    by_agents = {}
    for row in transitions:
        by_agents.setdefault(int(row["num_agents"]), []).append(row)
    agent_counts = sorted(by_agents)
    balance_alpha = float(getattr(args, "speed_balance_alpha", 0.0))
    balance_scope = str(getattr(args, "speed_balance_scope", "all"))
    balance_edges = SPEED_BALANCE_EDGES
    if balance_alpha > 0:
        frequencies = speed_bin_frequencies(transitions, balance_edges)
        balance_weights, balance_max = speed_balance_table(balance_edges, frequencies, balance_alpha)
        speed_mean = float(np.asarray(stats["ego_mean"])[4])
        speed_std = float(np.asarray(stats["ego_std"])[4])
        print("speed-balanced BC: alpha=%.2f bin frequencies=%s max weight=%.1f"
              % (balance_alpha, np.round(frequencies, 4).tolist(), balance_max), flush=True)
    losses = []
    started = time.time()
    for step in range(1, args.train_steps + 1):
        num_agents_batch = int(rng.choice(agent_counts))
        pool = by_agents[num_agents_batch]
        indices = rng.integers(0, len(pool), size=args.batch_size)
        batch = [pool[int(index)] for index in indices]
        obs, action, next_obs, reward, risk, quality = batch_to_tensors(batch, stats, args, device)
        out = transition(obs, action)
        if balance_alpha > 0 and balance_scope == "all":
            # Weight the whole per-step objective, not just the imitation term. The
            # closed-loop failure at standstill is an out-of-distribution transition
            # prediction (a five-sigma normalised speed) that makes the uncertainty
            # head veto the only action able to leave the state, so the dynamics,
            # reward and risk heads all need coverage in the launch regime.
            per_step = speed_balance_per_step(obs, balance_weights, balance_edges, speed_mean, speed_std)
            weight = per_step
            next_loss = weighted_mse(out["next_mu"], next_obs, weight)
            reward_loss = weighted_mse(out["reward_mu"], reward, weight)
            risk_loss = weighted_bce(out["risk_logits"], risk, weight)
        else:
            next_loss = F.mse_loss(out["next_mu"], next_obs)
            reward_loss = F.mse_loss(out["reward_mu"], reward)
            risk_loss = F.binary_cross_entropy_with_logits(out["risk_logits"], risk)
        quality_pred = out.get("quality_pred")
        if quality_pred is None:
            quality_loss = torch.zeros((), dtype=torch.float32, device=device)
            quality_bce_loss = torch.zeros((), dtype=torch.float32, device=device)
            quality_reg_loss = torch.zeros((), dtype=torch.float32, device=device)
        else:
            quality_bce_loss = F.binary_cross_entropy_with_logits(quality_pred[..., :2], quality[..., :2])
            quality_reg_loss = F.smooth_l1_loss(torch.sigmoid(quality_pred[..., 2:]), quality[..., 2:])
            quality_loss = quality_bce_loss + quality_reg_loss
        if balance_alpha > 0:
            per_step = speed_balance_per_step(obs, balance_weights, balance_edges, speed_mean, speed_std)
        else:
            per_step = None
        if getattr(args, 'proposal_target_only', False):
            residual = (proposal_actor(obs[:, -1]) - action[:, -1]) ** 2
        else:
            residual = (proposal_actor(obs.reshape(-1, obs.shape[-1]))
                        - action.reshape(-1, action.shape[-1])) ** 2
        if per_step is not None:
            proposal_loss = (residual * per_step[:, None, None]).mean()
        else:
            proposal_loss = residual.mean()
        uncertainty_loss = out["next_logvar"].mean().abs() * 0.01 + out["reward_logvar"].mean().abs() * 0.01
        loss = (
            next_loss
            + args.reward_weight * reward_loss
            + args.risk_weight * risk_loss
            + args.proposal_weight * proposal_loss
            + args.quality_aux_weight * quality_loss
            + uncertainty_loss
        )
        if args.lr_schedule == "cosine":
            progress = (step - 1) / max(args.train_steps - 1, 1)
            lr_now = args.lr * 0.5 * (1.0 + math.cos(math.pi * progress))
            for group in optimizer.param_groups:
                group["lr"] = lr_now
        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(list(transition.parameters()) + list(proposal_actor.parameters()), 25.0)
        optimizer.step()
        losses.append(
            {
                "step": step,
                "loss": float(loss.detach().cpu()),
                "next_loss": float(next_loss.detach().cpu()),
                "reward_loss": float(reward_loss.detach().cpu()),
                "risk_loss": float(risk_loss.detach().cpu()),
                "quality_loss": float(quality_loss.detach().cpu()),
                "quality_bce_loss": float(quality_bce_loss.detach().cpu()),
                "quality_reg_loss": float(quality_reg_loss.detach().cpu()),
                "proposal_loss": float(proposal_loss.detach().cpu()),
            }
        )
        if args.log_every > 0 and (step % args.log_every == 0 or step == 1):
            print("step %6d/%d loss=%.4f next=%.4f reward=%.4f risk=%.4f lr=%.2e elapsed=%.0fs"
                  % (step, args.train_steps, losses[-1]["loss"], losses[-1]["next_loss"],
                     losses[-1]["reward_loss"], losses[-1]["risk_loss"],
                     optimizer.param_groups[0]["lr"], time.time() - started), flush=True)
    return transition.cpu(), proposal_actor.cpu(), losses


def main():
    parser = argparse.ArgumentParser(description="Train a graph-risk DLC world model for multi-car overtaking.")
    parser.add_argument("--num-agents", type=int, default=4)
    parser.add_argument("--min-agents", type=int, default=4)
    parser.add_argument("--max-agents", type=int, default=6)
    parser.add_argument("--episodes", type=int, default=18)
    parser.add_argument("--max-steps", type=int, default=2200)
    parser.add_argument("--gap-tiles", type=int, default=18)
    parser.add_argument("--lateral-spacing", type=float, default=0.0)
    parser.add_argument("--seed", type=int, default=13)
    # The collection seed is part of the saved-dataset contract, so a second
    # training run over the same data needs its own seed. When unset the two
    # coincide, which keeps every earlier recipe reproducible.
    parser.add_argument("--train-seed", type=int, default=None)
    parser.add_argument("--hidden-dim", type=int, default=192)
    parser.add_argument("--proposal-hidden-dim", type=int, default=128)
    parser.add_argument("--train-steps", type=int, default=1800)
    parser.add_argument("--batch-size", type=int, default=512)
    parser.add_argument("--lr", type=float, default=3e-4)
    parser.add_argument("--reward-weight", type=float, default=0.4)
    parser.add_argument("--risk-weight", type=float, default=1.2)
    parser.add_argument("--proposal-weight", type=float, default=0.35)
    parser.add_argument("--quality-aux-weight", type=float, default=0.0)
    parser.add_argument("--quality-on-track-lateral", type=float, default=0.46)
    parser.add_argument("--quality-heading-cos", type=float, default=0.70)
    parser.add_argument("--quality-lane-error-clip", type=float, default=2.2)
    parser.add_argument("--quality-forward-clip", type=float, default=65.0)
    parser.add_argument("--risk-lateral", type=float, default=0.45)
    parser.add_argument("--pooling-mode", default="attention", choices=["attention", "mean"])
    parser.add_argument("--masked-attention", action="store_true",
                        help="Pool the masked opponent slots with learned attention instead of a "
                             "masked mean. The mean discards which admitted vehicle carries the "
                             "interaction, so the admission rule can only act through the set mean.")
    parser.add_argument("--observation-type", default="telemetry_dynamic", choices=["telemetry", "telemetry_dynamic"])
    parser.add_argument("--track-path", default="")
    parser.add_argument('--telemetry-version', choices=['legacy_v1', 'corrected_v2'], default='legacy_v1')
    parser.add_argument('--neighbor-selection',
                        choices=['interaction', 'nearest', 'fixed', 'relevance_v2'], default='interaction')
    parser.add_argument('--slot-priority', action='store_true',
                        help="Add the admission rank as an eighth slot feature. Pooling is "
                             "permutation-invariant, so the rank only reaches the model if it "
                             "travels with the slot content.")
    parser.add_argument('--data-split', choices=['train', 'development_smoke'], default='train')
    parser.add_argument('--collect-only', action='store_true')
    parser.add_argument('--dataset-dir', default='', help='Fit all transitions from an immutable saved collection')
    parser.add_argument('--proposal-target-only', action='store_true', help='Explicit new training variant: ego action supervision only')
    parser.add_argument('--expert-source', choices=['legacy_rule', 'joint_clearance_pilot'], default='legacy_rule')
    parser.add_argument('--background-profile', choices=['legacy_mixed', 'lane13'], default='legacy_mixed')
    parser.add_argument('--start-layout', choices=['single_file', 'paired'], default='single_file')
    parser.add_argument("--max-neighbors", type=int, default=3)
    parser.add_argument("--neighbor-keep-prob", type=float, default=0.9)
    parser.add_argument("--use-slot-mask", action="store_true")
    parser.add_argument("--predict-residual", action="store_true",
                        help="next-state head predicts the increment over the current observation")
    parser.add_argument("--slot-feature-dim", type=int, default=7)
    parser.add_argument("--planner-horizon", type=int, default=4)
    parser.add_argument("--planner-candidates", type=int, default=18)
    parser.add_argument("--planner-risk-weight", type=float, default=1.6)
    parser.add_argument("--planner-uncertainty-weight", type=float, default=0.35)
    parser.add_argument("--planner-progress-weight", type=float, default=1.2)
    parser.add_argument("--planner-imitation-weight", type=float, default=0.06)
    parser.add_argument("--planner-overtake-weight", type=float, default=2.4)
    parser.add_argument("--planner-lane-quality-weight", type=float, default=0.42)
    parser.add_argument("--planner-grass-penalty-weight", type=float, default=2.0)
    parser.add_argument("--planner-close-gap-penalty-weight", type=float, default=0.65)
    parser.add_argument("--lr-schedule", default="none", choices=["none", "cosine"],
                        help="Learning-rate decay. The archived runs used a constant rate; "
                             "a cosine decay is offered because the archived budget (1800 "
                             "optimizer steps over 352k transitions, i.e. less than one epoch) "
                             "leaves the state head predicting channel means.")
    parser.add_argument("--log-every", type=int, default=500)
    parser.add_argument("--speed-balance-alpha", type=float, default=0.0,
                        help="Tempered inverse-frequency reweighting of the BC loss over ego-speed bins. "
                             "0.0 reproduces the unweighted archived recipe.")
    parser.add_argument("--speed-balance-scope", default="all", choices=["proposal", "all"],
                        help="Which terms the speed-balanced weighting applies to. The transition, "
                             "reward and risk heads need launch-regime coverage too, otherwise the "
                             "uncertainty head vetoes every action that would leave a standstill.")
    parser.add_argument("--planner-target-speed", type=float, default=22.0)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--collection-workers", type=int, default=1)
    parser.add_argument("--out-dir", default="multi_car_racing/outputs/paper_multicar_overtake_20260618/models/graph_risk_world_model")
    args = parser.parse_args()
    if args.observation_type == "telemetry_dynamic":
        args.use_slot_mask = True
    if args.min_agents > args.max_agents:
        raise ValueError("--min-agents must be <= --max-agents")
    if args.expert_source == 'joint_clearance_pilot' and args.telemetry_version != 'corrected_v2':
        raise ValueError('Joint-clearance development teacher requires corrected observations')
    if args.telemetry_version == 'corrected_v2' and (args.observation_type != 'telemetry_dynamic'
            or args.slot_feature_dim not in (7, 8) or args.max_neighbors <= 0
            or (args.slot_feature_dim == 8 and not args.slot_priority)):
        raise ValueError('Corrected training requires masked 7-feature opponents (or 8 with '
                         '--slot-priority) and positive K')

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=args.telemetry_version == 'legacy_v1')
    if args.telemetry_version == 'corrected_v2':
        snapshot = out_dir/'source'
        hashes = {}
        for path in [*sorted((ROOT/'dlc').glob('*.py')),
                     *sorted((ROOT/'gym_multi_car_racing').glob('*.py')), Path(__file__).resolve()]:
            data = path.read_bytes()
            dest = snapshot/path.relative_to(ROOT)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            hashes[str(path.relative_to(ROOT))] = hashlib.sha256(data).hexdigest()
        rng = np.random.default_rng(args.seed)
        (out_dir/'provenance.json').write_text(json.dumps({
            'args': vars(args), 'source_sha256': hashes,
            'case_plan': [{'episode': i, 'seed': args.seed+i, 'num_agents': sample_num_agents(args, rng)}
                          for i in range(args.episodes)],
            'python': sys.version, 'platform': platform.platform(),
            'git_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
            'dirty_worktree': subprocess.check_output(['git', 'status', '--short'], cwd=ROOT, text=True),
            'packages': {p: importlib.metadata.version(p) for p in ['torch', 'numpy', 'gym', 'pyglet', 'shapely']},
            'risk_label': 'telemetry boundary/reverse/lateral proxy, not physical contact probability',
            'target_semantics': 'next-state slots retain identities selected at current real step',
            'quality_head_trained': args.quality_aux_weight > 0,
            'evidence': 'pipeline smoke only' if args.data_split == 'development_smoke' else 'training data; not evaluation'
        }, indent=2))
    transitions, episode_summaries = load_saved_dataset(args) if args.dataset_dir else collect_dataset(args)
    if args.slot_priority:
        # One extra channel per slot: the rank the admission rule gave it. A
        # permutation-invariant pooling cannot see slot order, so the ranking
        # only reaches the model when it travels as a feature.
        transitions = promote_priority_channel(transitions, args.max_neighbors)
    if args.collect_only:
        (out_dir/'collection_summary.json').write_text(json.dumps(episode_summaries, indent=2))
        return
    stats = compute_stats(transitions, use_slot_mask=args.use_slot_mask, slot_feature_dim=args.slot_feature_dim)
    transition, proposal_actor, losses = train(args, transitions, stats)
    model_path = out_dir / "graph_risk_dlc_world.graphworld.pt"
    obs_dim = int(transitions[0]["obs"].shape[-1])
    opponent_dim = args.slot_feature_dim + 1 if args.use_slot_mask else OPPONENT_DIM
    bundle = GraphWorldModelBundle(
        transition=transition,
        proposal_actor=proposal_actor,
        obs_mean=stats["obs_mean"].astype(np.float32),
        obs_std=stats["obs_std"].astype(np.float32),
        action_mean=stats["action_mean"].astype(np.float32),
        action_std=stats["action_std"].astype(np.float32),
        meta={
            "telemetry_version": args.telemetry_version,
            "neighbor_order": 'identity' if args.telemetry_version == 'corrected_v2' else 'relevance',
            "neighbor_selection": args.neighbor_selection,
            "data_split": args.data_split,
            "train_seed": int(args.train_seed),
            "expert_source": args.expert_source,
            "background_profile": args.background_profile,
            "start_layout": args.start_layout,
            "proposal_target_only": args.proposal_target_only,
            "speed_balance_alpha": args.speed_balance_alpha,
            "speed_balance_scope": args.speed_balance_scope,
            "name": "graph_risk_dlc_world",
            "obs_dim": obs_dim,
            "action_dim": int(transitions[0]["action"].shape[-1]),
            "quality_dim": 4,
            "quality_aux_weight": args.quality_aux_weight,
            "quality_targets": [
                "on_track_logit",
                "grass_logit",
                "lane_error_scaled",
                "forward_clearance_scaled",
            ],
            "num_agents": args.max_agents,
            "min_agents_train": args.min_agents,
            "max_agents_train": args.max_agents,
            "target_agent": args.max_agents - 1,
            "target_agent_mode": "last",
            "hidden_dim": args.hidden_dim,
            "proposal_hidden_dim": args.proposal_hidden_dim,
            "pooling_mode": args.pooling_mode,
            "masked_pooling": "attention" if args.masked_attention else "mean",
            "planner_horizon": args.planner_horizon,
            "planner_candidates": args.planner_candidates,
            "risk_weight": args.planner_risk_weight,
            "uncertainty_weight": args.planner_uncertainty_weight,
            "progress_weight": args.planner_progress_weight,
            "imitation_weight": args.planner_imitation_weight,
            "overtake_weight": args.planner_overtake_weight,
            "lane_quality_weight": args.planner_lane_quality_weight,
            "grass_penalty_weight": args.planner_grass_penalty_weight,
            "close_gap_penalty_weight": args.planner_close_gap_penalty_weight,
            "planner_target_speed": args.planner_target_speed,
            "overtake_aware_planner": bool(args.use_slot_mask),
            "use_slot_mask": bool(args.use_slot_mask),
            "predict_residual": bool(args.predict_residual),
            "slot_feature_dim": args.slot_feature_dim,
            "slot_priority": bool(args.slot_priority),
            "relation_dim": args.slot_feature_dim + 1 if args.use_slot_mask else 7,
            "opponent_dim": opponent_dim,
            "ego_dim": 17,
            "observation_type": args.observation_type,
            "max_neighbors": args.max_neighbors,
            "neighbor_keep_prob": args.neighbor_keep_prob,
            "planner_profile": "risk_aware",
            "background_policies": 'telemetry_lane13' if args.background_profile == 'lane13' else "telemetry_cruise,telemetry_yield,telemetry_lane",
            "episodes": args.episodes,
            "train_steps": args.train_steps,
            "device": args.device,
            "collection_workers": args.collection_workers,
            "source": "graph_risk_dlc_world_model",
            "ego_mean": stats["ego_mean"].tolist(),
            "ego_std": stats["ego_std"].tolist(),
            "opponent_mean": stats["opponent_mean"].tolist(),
            "opponent_std": stats["opponent_std"].tolist(),
        },
    )
    bundle.save(model_path)
    summary = {
        "status": "PASS",
        "evidence": "pipeline smoke only" if args.data_split == 'development_smoke' else "training; not endpoint evaluation",
        "model_path": str(model_path),
        "episodes": args.episodes,
        "transitions": len(transitions),
        "agent_samples": int(sum(row["num_agents"] for row in transitions)),
        "loss_final": losses[-1],
        "loss_mean_last_100": float(np.mean([row["loss"] for row in losses[-100:]])),
        "episode_summaries": episode_summaries,
        "args": vars(args),
    }
    (out_dir / "train_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (out_dir / "loss_curve.json").write_text(json.dumps(losses, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
