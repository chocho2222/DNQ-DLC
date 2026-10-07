#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import concurrent.futures
import csv
import importlib.util
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np

from scripts.tits_experiment_registry import RL_MODEL_PATHS, split_csv_cell, write_csv, write_json

try:
    import gymnasium as gym_api
    from gymnasium import spaces

    USE_GYMNASIUM_API = True
except ImportError:
    import gym as gym_api
    from gym import spaces

    USE_GYMNASIUM_API = False


class TargetOvertakeEnv(gym_api.Env):
    metadata = {"render_modes": [], "render.modes": []}

    def __init__(
        self,
        num_agents=4,
        seed=0,
        max_steps=1200,
        observation_type="telemetry_dynamic",
        traffic_profile="slow_traffic",
        track_path="",
        line_spacing=5,
        lateral_spacing=2.2,
        max_neighbors=3,
        telemetry_version="legacy_v1",
        neighbor_order="relevance",
        fixed_layout=False,
        pack_observation=False,
        pack_slots=3,
    ):
        super().__init__()
        self.num_agents = int(num_agents)
        self.target_agent = self.num_agents - 1
        self.base_seed = int(seed)
        self.seed_value = int(seed)
        self.episode_index = -1
        self.max_steps = int(max_steps)
        self.observation_type = observation_type
        self.traffic_profile = traffic_profile
        self.track_path = track_path or None
        self.line_spacing = line_spacing
        self.lateral_spacing = lateral_spacing
        self.max_neighbors = max_neighbors
        self.telemetry_version = telemetry_version
        self.neighbor_order = neighbor_order
        self.fixed_layout = bool(fixed_layout)
        self.pack_observation = bool(pack_observation)
        self.pack_slots = int(pack_slots)
        self.env = None
        self.background = {}
        self.steps = 0
        self.last_obs = None
        self.action_space = spaces.Box(
            low=np.asarray([-1.0, 0.0, 0.0], dtype=np.float32),
            high=np.asarray([1.0, 1.0, 1.0], dtype=np.float32),
            dtype=np.float32,
        )
        probe = self._make_env()
        obs = probe.reset()
        obs = self._pack(obs)
        self.observation_space = spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=obs[self.target_agent].shape,
            dtype=np.float32,
        )
        probe.close()

    def _pack(self, obs):
        """Write the opponent slots the way the evaluator will write them.

        The evaluator exposes every vehicle and lets each policy perform its own
        packing, so an agent trained against an environment-side neighbour
        budget would be evaluated on a different observation than it trained on.
        With ``pack_observation`` the same runtime packing the evaluator applies
        is applied here, which makes the training and evaluation observations
        identical by construction.
        """
        if not self.pack_observation:
            return np.asarray(obs, dtype=np.float32)
        from dlc.graph_policy import pack_dynamic_neighbor_obs

        return pack_dynamic_neighbor_obs(
            np.asarray(obs, dtype=np.float32),
            target_obs_dim=17 + 8 * self.pack_slots,
            max_neighbors=self.pack_slots,
            selection_mode="interaction",
            telemetry_version=self.telemetry_version,
        )

    def _make_env(self):
        from dlc.rollout import make_env

        rng = np.random.default_rng(self.seed_value)
        background = list(range(self.num_agents - 1))
        rng.shuffle(background)
        start_order = background + [self.target_agent]
        if self.fixed_layout:
            line_spacing = int(self.line_spacing)
            lateral_spacing = float(self.lateral_spacing)
        else:
            line_spacing = int(rng.choice([4, 5, 6]))
            lateral_spacing = float(self.lateral_spacing * rng.uniform(0.65, 1.35))
        return make_env(
            num_agents=self.num_agents,
            seed=self.seed_value,
            observation_type=self.observation_type,
            start_order=start_order,
            line_spacing=line_spacing,
            lateral_spacing=lateral_spacing,
            track_path=self.track_path,
            max_neighbors=None if self.pack_observation else self.max_neighbors,
            telemetry_version=self.telemetry_version,
            neighbor_order=self.neighbor_order,
        )

    def reset(self, seed=None, options=None):
        del options
        from scripts.run_tits_dynamic_graph_evaluation import make_background_policy

        if seed is not None:
            self.base_seed = int(seed)
            self.episode_index = 0
        else:
            self.episode_index += 1
        self.seed_value = self.base_seed + max(self.episode_index, 0)
        if self.env is not None:
            self.env.close()
        self.env = self._make_env()
        self.background = {
            agent_id: make_background_policy(agent_id, self.traffic_profile)
            for agent_id in range(self.num_agents)
            if agent_id != self.target_agent
        }
        for policy in self.background.values():
            policy.reset()
        self.steps = 0
        obs = self._pack(self.env.reset())
        self.last_obs = np.asarray(obs, dtype=np.float32)
        target_obs = np.asarray(self.last_obs[self.target_agent], dtype=np.float32)
        if USE_GYMNASIUM_API:
            return target_obs, {}
        return target_obs

    def step(self, action):
        obs = self.last_obs
        if obs is None:
            obs = np.asarray(self.env.reset(), dtype=np.float32)
        actions = np.zeros((self.num_agents, 3), dtype=np.float32)
        for agent_id, policy in self.background.items():
            actions[agent_id] = policy.act(self.env, obs)[agent_id]
        actions[self.target_agent] = np.asarray(action, dtype=np.float32)
        actions[:, 0] = np.clip(actions[:, 0], -1.0, 1.0)
        actions[:, 1:] = np.clip(actions[:, 1:], 0.0, 1.0)
        next_obs, reward, done, info = self.env.step(actions)
        next_obs = self._pack(next_obs)
        self.steps += 1
        track_tiles = len(self.env.unwrapped.track)
        target_tiles = int(self.env.unwrapped.tile_visited_count[self.target_agent])
        completed = target_tiles >= track_tiles
        terminated = bool(done or completed)
        truncated = bool(self.steps >= self.max_steps and not terminated)
        shaped_reward = float(reward[self.target_agent])
        shaped_reward += 0.05 * float(next_obs[self.target_agent, 9])
        shaped_reward -= 0.25 * float(next_obs[self.target_agent, 15] > 0.5)
        shaped_reward -= 0.15 * abs(float(next_obs[self.target_agent, 12]))
        if completed:
            shaped_reward += 50.0
        self.last_obs = np.asarray(next_obs, dtype=np.float32)
        target_obs = np.asarray(self.last_obs[self.target_agent], dtype=np.float32)
        if USE_GYMNASIUM_API:
            return target_obs, shaped_reward, terminated, truncated, info
        return target_obs, shaped_reward, bool(terminated or truncated), info

    def close(self):
        if self.env is not None:
            self.env.close()
            self.env = None


def sb3_available():
    return importlib.util.find_spec("stable_baselines3") is not None


def parse_devices(devices, fallback):
    items = [item.strip() for item in str(devices or "").split(",") if item.strip()]
    return items or [fallback]


def build_plan(args):
    algorithms = split_csv_cell(args.algorithms)
    seeds = [int(item) for item in split_csv_cell(args.seeds)]
    devices = parse_devices(args.devices, args.device)
    rows = []
    idx = 0
    for algorithm in algorithms:
        for seed in seeds:
            idx += 1
            out_subdir = Path(args.out_dir) / algorithm / f"seed{seed}"
            rows.append(
                {
                    "job_index": idx,
                    "algorithm": algorithm,
                    "seed": seed,
                    "device": devices[(idx - 1) % len(devices)],
                    "total_timesteps": args.total_timesteps,
                    "num_agents": args.num_agents,
                    "model_path": str(out_subdir / f"{algorithm}.sb3.zip"),
                    "meta_path": str(out_subdir / f"{algorithm}.meta.json"),
                    "status": "planned",
                }
            )
    return rows


def train_job(row, args):
    from stable_baselines3 import PPO, SAC, TD3

    loaders = {
        "ppo_continuous": PPO,
        "sac_continuous": SAC,
        "td3_continuous": TD3,
    }
    algorithm = row["algorithm"]
    if algorithm not in loaders:
        raise ValueError(f"unsupported RL baseline: {algorithm}")
    env = TargetOvertakeEnv(
        num_agents=int(row["num_agents"]),
        seed=int(row["seed"]),
        max_steps=args.max_steps,
        observation_type=args.observation_type,
        traffic_profile=args.traffic_profile,
        track_path=args.track_path,
        line_spacing=args.line_spacing,
        lateral_spacing=args.lateral_spacing,
        max_neighbors=args.max_neighbors,
        telemetry_version=args.telemetry_version,
        neighbor_order=args.neighbor_order,
        fixed_layout=args.fixed_layout,
        pack_observation=args.pack_observation,
        pack_slots=args.max_neighbors,
    )
    model_cls = loaders[algorithm]
    kwargs = {"verbose": 0, "seed": int(row["seed"]), "device": row["device"]}
    if algorithm == "ppo_continuous":
        kwargs.update({"n_steps": args.ppo_n_steps, "batch_size": args.batch_size})
    model = model_cls("MlpPolicy", env, **kwargs)
    started = time.time()
    model.learn(total_timesteps=int(row["total_timesteps"]), progress_bar=False)
    elapsed = time.time() - started
    model_path = Path(row["model_path"])
    model_path.parent.mkdir(parents=True, exist_ok=True)
    model.save(str(model_path))
    meta = {
        "name": algorithm,
        "algorithm": algorithm.split("_", 1)[0],
        "seed": int(row["seed"]),
        "device": row["device"],
        "num_agents": int(row["num_agents"]),
        "target_agent": int(row["num_agents"]) - 1,
        "total_timesteps": int(row["total_timesteps"]),
        "max_steps": int(args.max_steps),
        "observation_type": args.observation_type,
        "telemetry_version": args.telemetry_version,
        "neighbor_order": args.neighbor_order,
        "line_spacing": int(args.line_spacing),
        "lateral_spacing": float(args.lateral_spacing),
        "max_neighbors": int(args.max_neighbors),
        "observation_packing": ("runtime_interaction_packing_to_%d_slots" % int(args.max_neighbors)
                                if args.pack_observation else "environment_side_budget"),
        "traffic_profile": args.traffic_profile,
        "track_path": args.track_path or "procedural",
        "elapsed_sec": elapsed,
        "boundary": "Stable-Baselines3 continuous-control baseline trained in the same simulator with target-only control and rule-controlled background traffic.",
        "episode_randomization": "Each reset increments the simulator seed and randomizes background start order, line spacing in {4,5,6}, and lateral spacing jitter while keeping the target last.",
    }
    write_json(row["meta_path"], meta)
    env.close()
    return {**row, "status": "trained", "elapsed_sec": elapsed}


def main():
    parser = argparse.ArgumentParser(description="Train Stable-Baselines3 RL baselines for the T-ITS expanded benchmark.")
    parser.add_argument("--algorithms", default="ppo_continuous,sac_continuous,td3_continuous")
    parser.add_argument("--seeds", default="2026")
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph_expanded/rl_baselines")
    parser.add_argument("--mode", choices=["dry-run", "run"], default="dry-run")
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--devices", default="")
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--executor", choices=["thread", "process"], default="thread",
                        help="thread keeps the historical behaviour; process runs one "
                             "interpreter per job, which is what the Box2D simulator needs "
                             "because its step loop holds the interpreter lock")
    parser.add_argument("--strict-dependencies", action="store_true")
    parser.add_argument("--total-timesteps", type=int, default=200000)
    parser.add_argument("--num-agents", type=int, default=4)
    parser.add_argument("--max-steps", type=int, default=1200)
    parser.add_argument("--observation-type", choices=["telemetry", "telemetry_dynamic"], default="telemetry_dynamic")
    parser.add_argument("--traffic-profile", choices=["slow_traffic", "mixed_traffic"], default="slow_traffic")
    parser.add_argument("--track-path", default="")
    parser.add_argument("--line-spacing", type=int, default=5)
    parser.add_argument("--lateral-spacing", type=float, default=2.2)
    parser.add_argument("--max-neighbors", type=int, default=3)
    parser.add_argument("--ppo-n-steps", type=int, default=1024)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--telemetry-version", choices=["legacy_v1", "corrected_v2"], default="legacy_v1")
    parser.add_argument("--neighbor-order", choices=["relevance", "identity"], default="relevance")
    parser.add_argument("--fixed-layout", action="store_true",
                        help="train on one fixed pack layout instead of the archived 4-6 tile spread")
    parser.add_argument("--pack-observation", action="store_true",
                        help="expose every vehicle and pack the slots with the runtime interaction "
                             "rule, so the training observation equals the evaluation observation")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    tables = out_dir / "tables"
    materials = out_dir / "materials"
    tables.mkdir(parents=True, exist_ok=True)
    materials.mkdir(parents=True, exist_ok=True)
    plan = build_plan(args)
    dependency_available = sb3_available()
    results = []
    status = "dry_run_ready"
    if not dependency_available:
        status = "blocked_missing_dependency"
    elif args.mode == "run":
        workers = max(1, int(args.jobs))
        if workers == 1:
            results = [train_job(row, args) for row in plan]
        else:
            pool_cls = (concurrent.futures.ThreadPoolExecutor
                        if args.executor == "thread"
                        else concurrent.futures.ProcessPoolExecutor)
            with pool_cls(max_workers=workers) as executor:
                futures = {executor.submit(train_job, row, args): row for row in plan}
                for future in concurrent.futures.as_completed(futures):
                    results.append(future.result())
            results.sort(key=lambda row: int(row["job_index"]))
        status = "pass" if len(results) == len(plan) else "run_incomplete"
    for row in plan:
        expected = RL_MODEL_PATHS.get(row["algorithm"])
        if expected and row["model_path"] != expected:
            row["registry_expected_model_path"] = expected
    plan_csv = write_csv(
        tables / "rl_baseline_training_plan.csv",
        plan,
        [
            "job_index",
            "algorithm",
            "seed",
            "device",
            "total_timesteps",
            "num_agents",
            "model_path",
            "meta_path",
            "registry_expected_model_path",
            "status",
        ],
    )
    result_csv = write_csv(
        tables / "rl_baseline_training_results.csv",
        results,
        ["job_index", "algorithm", "seed", "device", "total_timesteps", "num_agents", "model_path", "meta_path", "status", "elapsed_sec"],
    )
    manifest = {
        "status": status,
        "mode": args.mode,
        "stable_baselines3_available": dependency_available,
        "job_count": len(plan),
        "trained_count": len(results),
        "paths": {
            "training_plan": plan_csv,
            "training_results": result_csv,
        },
        "dependency_boundary": "If stable_baselines3 is unavailable, no RL result is generated or claimed. Install the RL environment and rerun mode=run before citing PPO/SAC/TD3 baselines.",
    }
    manifest_path = write_json(out_dir / "rl_baseline_training_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, "status": status, "stable_baselines3_available": dependency_available, "jobs": len(plan)}, ensure_ascii=False, indent=2))
    if args.strict_dependencies and not dependency_available:
        raise SystemExit(2)
    if args.mode == "run" and status not in {"pass"}:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
