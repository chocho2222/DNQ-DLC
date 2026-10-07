#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import concurrent.futures
import csv
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dlc.policies import (
    TelemetryAdaptiveGatePolicy,
    TelemetryBarrierExpertGatePolicy,
    TelemetryCruisePolicy,
    TelemetryExpertGatePolicy,
    TelemetryFastExpertGatePolicy,
    TelemetryLanePolicy,
    TelemetryOvertakePolicy,
    TelemetryRecoveryExpertGatePolicy,
    TelemetryYieldPolicy,
)
from dlc.rollout import make_env
from scripts.run_tits_dynamic_graph_evaluation import (
    annotate_overtake_quality,
    compute_overtake_events,
    rank_from_tiles,
    track_indices,
)


def make_target_policy(name):
    if name == "telemetry_expert_gate":
        return TelemetryExpertGatePolicy()
    if name == "telemetry_expert_fast":
        return TelemetryFastExpertGatePolicy()
    if name == "telemetry_expert_barrier":
        return TelemetryBarrierExpertGatePolicy()
    if name == "telemetry_expert_recovery":
        return TelemetryRecoveryExpertGatePolicy()
    if name == "telemetry_adaptive":
        return TelemetryAdaptiveGatePolicy(target_speed=22.0, pass_speed=25.0, pass_lane_offset=1.6)
    if name == "telemetry_overtake":
        return TelemetryOvertakePolicy(target_speed=22.0, pass_speed=26.0, pass_lane_offset=2.0)
    raise ValueError(f"unknown target policy: {name}")


def make_background_policy(agent_id, profile):
    if profile == "slow_traffic":
        speeds = [11.0, 11.8, 12.6, 13.4, 14.2, 15.0, 15.8, 16.2]
    elif profile == "mixed_traffic":
        speeds = [12.5, 13.5, 14.5, 15.5, 16.5, 17.5, 18.0, 18.5]
    else:
        raise ValueError(f"unknown traffic profile: {profile}")
    speed = speeds[agent_id % len(speeds)]
    if agent_id % 3 == 0:
        return TelemetryLanePolicy(target_speed=speed, gas=0.42, brake=0.52, name=f"bg_lane_{agent_id}")
    if agent_id % 3 == 1:
        return TelemetryYieldPolicy(target_speed=speed, yield_speed=max(speed - 3.0, 8.0), gas=0.40, brake=0.54, name=f"bg_yield_{agent_id}")
    return TelemetryCruisePolicy(target_speed=speed, gas=0.42, brake=0.52, name=f"bg_cruise_{agent_id}")


def policy_action(env, obs, target_policy, target_agent, background_policies):
    actions = np.zeros((env.unwrapped.num_agents, 3), dtype=np.float32)
    for agent_id, policy in background_policies.items():
        actions[agent_id] = policy.act(env, obs)[agent_id]
    target_actions = target_policy.act(env, obs)
    target_actions = np.asarray(target_actions, dtype=np.float32)
    actions[target_agent] = target_actions[target_agent] if target_actions.ndim == 2 else target_actions
    actions[:, 0] = np.clip(actions[:, 0], -1.0, 1.0)
    actions[:, 1:] = np.clip(actions[:, 1:], 0.0, 1.0)
    return actions


def sample_num_agents(args, rng):
    if args.min_agents == args.max_agents:
        return int(args.min_agents)
    return int(rng.integers(args.min_agents, args.max_agents + 1))


def select_event_indices(trace, events, pre_context, post_context, accept_mode):
    selected = set()
    accepted_events = []
    for event in events:
        accept = False
        if accept_mode == "elegant":
            accept = bool(event.get("elegant_overtake"))
        elif accept_mode == "on_track":
            accept = bool(event.get("on_track_overtake"))
        elif accept_mode == "success":
            accept = True
        else:
            raise ValueError(f"unknown accept mode: {accept_mode}")
        if not accept:
            continue
        accepted_events.append(event)
        start = max(1, int(event["start_step"]) - int(pre_context))
        end = int(event["complete_step"]) + int(post_context)
        for idx, row in enumerate(trace):
            step = int(row["step"])
            if start <= step <= end:
                selected.add(idx)
    return sorted(selected), accepted_events


def select_stable_indices(trace, target_agent, max_samples, seed, lateral_threshold=0.26, heading_cos_threshold=0.92, min_speed=6.0):
    if max_samples <= 0:
        return []
    candidates = []
    for idx, row in enumerate(trace):
        telemetry = row["telemetry"]
        if bool(telemetry["on_grass"][target_agent]) or bool(telemetry["backward"][target_agent]):
            continue
        lateral = abs(float(telemetry["lateral_error"][target_agent]))
        heading_cos = float(telemetry["heading_cos"][target_agent])
        speed = float(row["speed"][target_agent])
        if lateral <= lateral_threshold and heading_cos >= heading_cos_threshold and speed >= min_speed:
            candidates.append(idx)
    if len(candidates) <= max_samples:
        return candidates
    rng = np.random.default_rng(seed)
    return sorted(rng.choice(candidates, size=max_samples, replace=False).tolist())


def select_recovery_indices(trace, target_agent, context):
    if context <= 0:
        return []
    selected = set()
    was_grass = False
    for idx, row in enumerate(trace):
        on_grass = bool(row["telemetry"]["on_grass"][target_agent])
        if was_grass and not on_grass:
            start = max(0, idx - context)
            end = min(len(trace) - 1, idx + context)
            selected.update(range(start, end + 1))
        was_grass = on_grass
    return sorted(selected)


def collect_episode_worker(payload):
    args_dict, episode, num_agents, target_policy_name = payload
    args = argparse.Namespace(**args_dict)
    seed = int(args.seed + episode)
    target_agent = int(num_agents - 1)
    env = make_env(
        num_agents=num_agents,
        seed=seed,
        observation_type=args.observation_type,
        start_order=[2 * agent_id for agent_id in range(num_agents)],
        line_spacing=args.gap_tiles,
        lateral_spacing=args.lateral_spacing,
        track_path=args.track_path or None,
        max_neighbors=args.max_neighbors,
    )
    if hasattr(env, "_max_episode_steps"):
        env._max_episode_steps = int(args.max_steps) + 1

    target_policy = make_target_policy(target_policy_name)
    background_policies = {
        agent_id: make_background_policy(agent_id, args.traffic_profile)
        for agent_id in range(num_agents)
        if agent_id != target_agent
    }
    target_policy.reset()
    for policy in background_policies.values():
        policy.reset()

    per_step_obs = []
    per_step_action = []
    trace = []
    total_reward = np.zeros(num_agents, dtype=np.float64)
    obs = env.reset()
    steps_run = 0
    try:
        track_tiles = len(env.unwrapped.track)
        for step in range(args.max_steps):
            action = policy_action(env, obs, target_policy, target_agent, background_policies)
            per_step_obs.append(obs[target_agent].astype(np.float32))
            per_step_action.append(action[target_agent].astype(np.float32))
            obs, reward, done, _ = env.step(action)
            steps_run = step + 1
            total_reward += reward
            positions = [np.asarray(car.hull.position, dtype=np.float32) for car in env.unwrapped.cars]
            pair_distances = [
                float(np.linalg.norm(positions[i] - positions[j]))
                for i in range(num_agents)
                for j in range(i + 1, num_agents)
            ]
            tile_counts = list(map(int, env.unwrapped.tile_visited_count))
            trace.append(
                {
                    "step": int(steps_run),
                    "reward": np.asarray(reward, dtype=float).tolist(),
                    "total_reward": total_reward.tolist(),
                    "tile_visited_count": tile_counts,
                    "rank": rank_from_tiles(tile_counts),
                    "track_index": track_indices(env),
                    "action": np.asarray(action, dtype=float).tolist(),
                    "speed": [float(np.linalg.norm(car.hull.linearVelocity)) for car in env.unwrapped.cars],
                    "compute_latency_ms": 0.0,
                    "min_pair_distance": min(pair_distances) if pair_distances else None,
                    "telemetry": {
                        "progress": [float(item) for item in obs[:, 9]],
                        "lateral_error": [float(item) for item in obs[:, 12]],
                        "heading_cos": [float(item) for item in obs[:, 14]],
                        "on_grass": [bool(item > 0.5) for item in obs[:, 15]],
                        "backward": [bool(item > 0.5) for item in obs[:, 16]],
                    },
                    "positions": [pos.tolist() for pos in positions],
                    "done": bool(done),
                }
            )
            if args.finish_mode == "any" and any(count >= track_tiles for count in tile_counts):
                break
            if args.finish_mode == "target" and tile_counts[target_agent] >= track_tiles:
                break
            if done and args.finish_mode == "env_done":
                break
    finally:
        try:
            track_tiles = len(env.unwrapped.track)
            final_tiles = list(map(int, env.unwrapped.tile_visited_count))
        except Exception:
            track_tiles = 0
            final_tiles = [0] * num_agents
        env.close()

    events = compute_overtake_events(trace, target_agent, track_tiles)
    events = annotate_overtake_quality(
        trace,
        events,
        target_agent,
        contact_distance=args.contact_distance,
    )
    selected_indices, accepted_events = select_event_indices(
        trace,
        events,
        args.pre_context,
        args.post_context,
        args.accept_mode,
    )
    event_indices = set(selected_indices)
    stable_indices = set(
        select_stable_indices(
            trace,
            target_agent,
            args.stable_samples_per_episode,
            seed=args.seed + episode * 9973,
            lateral_threshold=args.stable_lateral_threshold,
            heading_cos_threshold=args.stable_heading_cos_threshold,
            min_speed=args.stable_min_speed,
        )
    )
    recovery_indices = set(select_recovery_indices(trace, target_agent, args.recovery_context))
    selected_indices = sorted(event_indices | stable_indices | recovery_indices)
    observations = np.asarray([per_step_obs[idx] for idx in selected_indices], dtype=np.float32)
    actions = np.asarray([per_step_action[idx] for idx in selected_indices], dtype=np.float32)
    target_grass = [row["telemetry"]["on_grass"][target_agent] for row in trace]
    target_lateral = [abs(row["telemetry"]["lateral_error"][target_agent]) for row in trace]
    summary = {
        "episode": int(episode),
        "seed": int(seed),
        "num_agents": int(num_agents),
        "target_agent": int(target_agent),
        "target_policy": target_policy_name,
        "steps": int(steps_run),
        "track_tiles": int(track_tiles),
        "tile_visited_count": final_tiles,
        "target_progress": float(final_tiles[target_agent] / max(track_tiles, 1)),
        "overtake_count": int(len(events)),
        "accepted_event_count": int(len(accepted_events)),
        "on_track_overtake_count": int(sum(event.get("on_track_overtake", False) for event in events)),
        "elegant_overtake_count": int(sum(event.get("elegant_overtake", False) for event in events)),
        "selected_samples": int(len(selected_indices)),
        "selected_event_samples": int(len(event_indices)),
        "selected_stable_samples": int(len(stable_indices)),
        "selected_recovery_samples": int(len(recovery_indices)),
        "target_grass_rate": float(np.mean(target_grass)) if target_grass else None,
        "target_mean_abs_lateral": float(np.mean(target_lateral)) if target_lateral else None,
        "events": events,
    }
    return {
        "observations": observations,
        "actions": actions,
        "summary": summary,
    }


def collect_dataset(args):
    rng = np.random.default_rng(args.seed)
    target_policies = [item.strip() for item in args.target_policies.split(",") if item.strip()]
    if not target_policies:
        raise ValueError("--target-policies cannot be empty")
    payloads = []
    for episode in range(args.episodes):
        num_agents = sample_num_agents(args, rng)
        policy_name = target_policies[episode % len(target_policies)]
        payloads.append((vars(args).copy(), episode, num_agents, policy_name))
    workers = max(1, min(int(args.collection_workers), max(len(payloads), 1)))
    if workers > 1:
        with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as executor:
            results = list(executor.map(collect_episode_worker, payloads))
    else:
        results = [collect_episode_worker(payload) for payload in payloads]
    results.sort(key=lambda item: item["summary"]["episode"])
    observations = [row["observations"] for row in results if row["observations"].size]
    actions = [row["actions"] for row in results if row["actions"].size]
    if observations:
        observations = np.concatenate(observations, axis=0).astype(np.float32)
        actions = np.concatenate(actions, axis=0).astype(np.float32)
    else:
        observations = np.zeros((0, 17 + args.max_neighbors * (7 + (1 if args.observation_type == "telemetry_dynamic" else 0))), dtype=np.float32)
        actions = np.zeros((0, 3), dtype=np.float32)
    summaries = [row["summary"] for row in results]
    return observations, actions, summaries


def write_summary_tables(out_dir, episode_summaries):
    out_dir = Path(out_dir)
    rows_path = out_dir / "episode_summary.csv"
    fields = [
        "episode",
        "seed",
        "num_agents",
        "target_policy",
        "steps",
        "target_progress",
        "overtake_count",
        "accepted_event_count",
        "on_track_overtake_count",
        "elegant_overtake_count",
        "selected_samples",
        "selected_event_samples",
        "selected_stable_samples",
        "selected_recovery_samples",
        "target_grass_rate",
        "target_mean_abs_lateral",
    ]
    with rows_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in episode_summaries:
            writer.writerow({field: row.get(field) for field in fields})
    return str(rows_path)


def main():
    parser = argparse.ArgumentParser(description="Collect filtered on-track/desirable overtaking expert samples for graph policy training.")
    parser.add_argument("--episodes", type=int, default=24)
    parser.add_argument("--min-agents", type=int, default=4)
    parser.add_argument("--max-agents", type=int, default=6)
    parser.add_argument("--max-steps", type=int, default=2200)
    parser.add_argument("--gap-tiles", type=int, default=18)
    parser.add_argument("--lateral-spacing", type=float, default=0.0)
    parser.add_argument("--seed", type=int, default=3100)
    parser.add_argument("--observation-type", default="telemetry_dynamic", choices=["telemetry", "telemetry_dynamic"])
    parser.add_argument("--max-neighbors", type=int, default=3)
    parser.add_argument("--track-path", default="")
    parser.add_argument("--traffic-profile", default="slow_traffic", choices=["slow_traffic", "mixed_traffic"])
    parser.add_argument("--target-policies", default="telemetry_expert_gate,telemetry_expert_fast,telemetry_expert_barrier")
    parser.add_argument("--accept-mode", default="elegant", choices=["elegant", "on_track", "success"])
    parser.add_argument("--pre-context", type=int, default=30)
    parser.add_argument("--post-context", type=int, default=45)
    parser.add_argument("--stable-samples-per-episode", type=int, default=0)
    parser.add_argument("--stable-lateral-threshold", type=float, default=0.26)
    parser.add_argument("--stable-heading-cos-threshold", type=float, default=0.92)
    parser.add_argument("--stable-min-speed", type=float, default=6.0)
    parser.add_argument("--recovery-context", type=int, default=0)
    parser.add_argument("--contact-distance", type=float, default=3.0)
    parser.add_argument("--finish-mode", default="any", choices=["any", "target", "env_done", "steps"])
    parser.add_argument("--collection-workers", type=int, default=1)
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/elegant_overtake_dataset")
    args = parser.parse_args()
    if args.min_agents > args.max_agents:
        raise ValueError("--min-agents must be <= --max-agents")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    observations, actions, episode_summaries = collect_dataset(args)
    dataset_path = out_dir / "elegant_overtake_dataset.npz"
    np.savez_compressed(
        dataset_path,
        observations=observations,
        actions=actions,
        episode_summaries_json=json.dumps(episode_summaries, ensure_ascii=False),
        args_json=json.dumps(vars(args), ensure_ascii=False),
    )
    rows_path = write_summary_tables(out_dir, episode_summaries)
    accepted = sum(row["accepted_event_count"] for row in episode_summaries)
    total_events = sum(row["overtake_count"] for row in episode_summaries)
    summary = {
        "status": "PASS" if observations.shape[0] > 0 else "NO_ACCEPTED_SAMPLES",
        "dataset_path": str(dataset_path),
        "episode_summary_csv": rows_path,
        "episodes": int(args.episodes),
        "samples": int(observations.shape[0]),
        "obs_shape": list(observations.shape),
        "action_shape": list(actions.shape),
        "total_overtake_events": int(total_events),
        "accepted_events": int(accepted),
        "accept_rate": float(accepted / max(total_events, 1)),
        "mean_selected_samples_per_episode": float(np.mean([row["selected_samples"] for row in episode_summaries])) if episode_summaries else 0.0,
        "args": vars(args),
    }
    (out_dir / "dataset_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
