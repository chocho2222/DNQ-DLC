#!/usr/bin/env python
"""Evaluate planner candidate rankings against replayed Box2D outcomes.

For every audited decision, the environment is rebuilt from the saved initial
record and replayed with the recorded joint actions up to the decision point.
Each planner candidate then replaces only the target action at that point.  The
remaining short horizon uses the same recorded joint actions for every branch.
This makes the comparison paired at the same physical state and keeps all
non-candidate controls fixed.
"""

import argparse
from concurrent.futures import ProcessPoolExecutor
import csv
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pyglet

pyglet.options["headless"] = True

import numpy as np
from scipy.stats import spearmanr

from dlc.rollout import make_env


_WORKER_CONTEXT = None


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def angle_error(a, b):
    delta = np.asarray(a, dtype=np.float64) - np.asarray(b, dtype=np.float64)
    return np.abs((delta + math.pi) % (2.0 * math.pi) - math.pi)


def make_replay_env(initial, max_steps):
    scenario = initial.get("scenario")
    if scenario is None:
        # Early traces predate explicit scenario serialization. Reconstruct
        # the same deterministic randomized placement used by the evaluator.
        n = int(initial["num_agents"])
        rng = np.random.default_rng(int(initial["seed"]))
        background_slots = np.arange(max(n - 1, 0), dtype=np.int32)
        rng.shuffle(background_slots)
        line_spacing = int(rng.choice([4, 5, 6]))
        lateral_spacing = 2.2 * float(rng.uniform(1.0 - 0.35, 1.0 + 0.35))
        scenario = {
            "start_order": background_slots.tolist() + [n - 1],
            "line_spacing": line_spacing,
            "lateral_spacing": lateral_spacing,
        }
    env = make_env(
        num_agents=int(initial["num_agents"]),
        seed=int(initial["seed"]),
        observation_type=initial.get("observation_type", "telemetry_dynamic"),
        start_order=scenario["start_order"],
        line_spacing=scenario["line_spacing"],
        lateral_spacing=scenario["lateral_spacing"],
        track_path=None if initial["track_path"] == "procedural" else initial["track_path"],
        max_neighbors=initial.get("env_max_neighbors"),
        telemetry_version=initial.get("telemetry_version", "legacy_v1"),
        neighbor_order=initial.get("neighbor_order", "relevance"),
    )
    if hasattr(env, "_max_episode_steps"):
        env._max_episode_steps = max(int(max_steps) + 1, int(env._max_episode_steps))
    obs = env.reset()
    return env, obs


def state_arrays(env):
    cars = env.unwrapped.cars
    return {
        "positions": np.asarray([car.hull.position for car in cars], dtype=np.float64),
        "angles": np.asarray([car.hull.angle for car in cars], dtype=np.float64),
        "velocities": np.asarray([car.hull.linearVelocity for car in cars], dtype=np.float64),
    }


def compare_state(env, expected):
    actual = state_arrays(env)
    return {
        "position_max_abs_error": float(
            np.max(np.abs(actual["positions"] - np.asarray(expected["positions"], dtype=np.float64)))
        ),
        "angle_max_abs_error": float(
            np.max(angle_error(actual["angles"], expected["hull_angles"]))
        ),
        "velocity_max_abs_error": (
            float(
                np.max(
                    np.abs(
                        actual["velocities"]
                        - np.asarray(expected["velocities"], dtype=np.float64)
                    )
                )
            )
            if "velocities" in expected
            else None
        ),
    }


def replay_prefix(initial, trace, decision_index, max_steps):
    env, obs = make_replay_env(initial, max_steps=max_steps)
    for row in trace[:decision_index]:
        obs, _, _, _ = env.step(np.asarray(row["action"], dtype=np.float32))
    expected = initial if decision_index == 0 else trace[decision_index - 1]
    errors = compare_state(env, expected)
    return env, obs, errors


def target_contact(snapshot, target_agent):
    for contact in snapshot:
        agents = contact.get("agents", [])
        if int(target_agent) in [int(item) for item in agents]:
            return True
    return False


def min_pair_distance(env):
    positions = state_arrays(env)["positions"]
    if len(positions) < 2:
        return None
    return float(
        min(
            np.linalg.norm(positions[i] - positions[j])
            for i in range(len(positions))
            for j in range(i + 1, len(positions))
        )
    )


def track_geometry(track):
    points = np.asarray(track, dtype=np.float64)[:, 2:4]
    segment_vectors = np.roll(points, -1, axis=0) - points
    segment_lengths = np.linalg.norm(segment_vectors, axis=1)
    cumulative = np.concatenate(([0.0], np.cumsum(segment_lengths[:-1])))
    return points, segment_vectors, segment_lengths, cumulative, float(np.sum(segment_lengths))


def project_track_arclength(position, geometry):
    points, vectors, lengths, cumulative, lap_length = geometry
    relative = np.asarray(position, dtype=np.float64) - points
    denominators = np.maximum(lengths * lengths, 1e-12)
    fractions = np.clip(np.einsum("ij,ij->i", relative, vectors) / denominators, 0.0, 1.0)
    projections = points + fractions[:, None] * vectors
    index = int(np.argmin(np.linalg.norm(projections - position, axis=1)))
    return float((cumulative[index] + fractions[index] * lengths[index]) % lap_length)


def circular_delta(current, previous, period):
    return float((current - previous + period / 2.0) % period - period / 2.0)


def branch_candidate(
    initial,
    trace,
    decision_index,
    candidate_action,
    target_agent,
    horizon,
    max_steps,
):
    env, obs, prefix_errors = replay_prefix(initial, trace, decision_index, max_steps)
    geometry = track_geometry(initial["track"])
    start_tiles = int(env.unwrapped.tile_visited_count[target_agent])
    start_progress = float(obs[target_agent, 9])
    previous_s = project_track_arclength(env.unwrapped.cars[target_agent].hull.position, geometry)
    longitudinal_progress = 0.0
    rewards = []
    grass = []
    backward = []
    lateral = []
    contacts = []
    distances = []
    steps = 0
    try:
        stop = min(decision_index + horizon, len(trace))
        for trace_index in range(decision_index, stop):
            action = np.asarray(trace[trace_index]["action"], dtype=np.float32).copy()
            if trace_index == decision_index:
                action[target_agent] = np.asarray(candidate_action, dtype=np.float32)
            obs, reward, done, _ = env.step(action)
            current_s = project_track_arclength(env.unwrapped.cars[target_agent].hull.position, geometry)
            longitudinal_progress += circular_delta(current_s, previous_s, geometry[-1])
            previous_s = current_s
            rewards.append(float(reward[target_agent]))
            grass.append(float(obs[target_agent, 15] > 0.5))
            backward.append(float(obs[target_agent, 16] > 0.5))
            lateral.append(abs(float(obs[target_agent, 12])))
            contacts.append(
                float(target_contact(env.unwrapped.vehicle_contacts.snapshot(env.unwrapped.world), target_agent))
            )
            distances.append(min_pair_distance(env))
            steps += 1
            if done:
                break
        end_tiles = int(env.unwrapped.tile_visited_count[target_agent])
        end_progress = float(obs[target_agent, 9])
        return {
            **prefix_errors,
            "rollout_steps": int(steps),
            "cumulative_reward": float(np.sum(rewards)),
            "tile_gain": int(end_tiles - start_tiles),
            "normalized_tile_gain": float((end_tiles - start_tiles) / len(env.unwrapped.track)),
            "telemetry_progress_delta": float(end_progress - start_progress),
            "longitudinal_progress_m": float(longitudinal_progress),
            "grass_fraction": float(np.mean(grass)) if grass else 0.0,
            "backward_fraction": float(np.mean(backward)) if backward else 0.0,
            "mean_abs_lateral_error": float(np.mean(lateral)) if lateral else 0.0,
            "max_abs_lateral_error": float(np.max(lateral)) if lateral else 0.0,
            "contact_fraction": float(np.mean(contacts)) if contacts else 0.0,
            "contact_any": bool(any(contacts)),
            "minimum_pair_distance": float(min(distances)) if distances else None,
        }
    finally:
        env.close()


def initialize_worker(initial, trace, target_agent, horizon, max_steps):
    global _WORKER_CONTEXT
    _WORKER_CONTEXT = (initial, trace, target_agent, horizon, max_steps)


def run_worker_task(task):
    decision_index, candidate_index, candidate_action = task
    initial, trace, target_agent, horizon, max_steps = _WORKER_CONTEXT
    outcome = branch_candidate(
        initial=initial,
        trace=trace,
        decision_index=decision_index,
        candidate_action=candidate_action,
        target_agent=target_agent,
        horizon=horizon,
        max_steps=max_steps,
    )
    return decision_index, candidate_index, outcome


def rankdata_desc(values):
    values = np.asarray(values, dtype=np.float64)
    order = np.argsort(-values, kind="mergesort")
    ranks = np.empty(len(values), dtype=np.float64)
    position = 0
    while position < len(order):
        end = position + 1
        while end < len(order) and values[order[end]] == values[order[position]]:
            end += 1
        ranks[order[position:end]] = 1.0 + (position + end - 1) / 2.0
        position = end
    return ranks


def physical_utility(row, weights):
    return (
        float(row["cumulative_reward"])
        + weights["progress"] * float(row["longitudinal_progress_m"])
        - weights["grass"] * float(row["grass_fraction"])
        - weights["backward"] * float(row["backward_fraction"])
        - weights["lateral"] * float(row["mean_abs_lateral_error"])
        - weights["contact"] * float(row["contact_any"])
    )


def choose_decisions(trace, max_points):
    eligible = [
        index
        for index, row in enumerate(trace)
        if len(row.get("target_policy_debug", {}).get("candidate_scores", [])) >= 2
    ]
    if max_points is None or len(eligible) <= max_points:
        return eligible
    positions = np.linspace(0, len(eligible) - 1, num=max_points)
    return sorted({eligible[int(round(position))] for position in positions})


def write_csv(path, rows):
    fields = list(rows[0]) if rows else ["decision_step"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--initial", required=True, type=Path)
    parser.add_argument("--trace", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--horizon", type=int, default=4)
    parser.add_argument("--max-decision-points", type=int, default=24)
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--replay-tolerance", type=float, default=1e-5)
    parser.add_argument("--progress-weight", type=float, default=1.0)
    parser.add_argument("--grass-weight", type=float, default=5.0)
    parser.add_argument("--backward-weight", type=float, default=5.0)
    parser.add_argument("--lateral-weight", type=float, default=2.0)
    parser.add_argument("--contact-weight", type=float, default=10.0)
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError(f"output directory already exists: {args.out}")
    if args.horizon < 1:
        raise ValueError("--horizon must be positive")

    initial = read_json(args.initial)
    trace = read_json(args.trace)
    target_agent = int(initial.get("algorithm", {}).get("target_agent", initial["num_agents"] - 1))
    decisions = choose_decisions(trace, args.max_decision_points)
    weights = {
        "progress": float(args.progress_weight),
        "grass": float(args.grass_weight),
        "backward": float(args.backward_weight),
        "lateral": float(args.lateral_weight),
        "contact": float(args.contact_weight),
    }

    args.out.mkdir(parents=True)
    candidate_rows = []
    decision_rows = []
    tasks = []
    for decision_index in decisions:
        candidates = trace[decision_index]["target_policy_debug"]["candidate_scores"]
        tasks.extend(
            (decision_index, candidate_index, candidate["action"])
            for candidate_index, candidate in enumerate(candidates)
        )
    max_steps = len(trace) + args.horizon + 1
    if args.jobs > 1:
        with ProcessPoolExecutor(
            max_workers=args.jobs,
            initializer=initialize_worker,
            initargs=(initial, trace, target_agent, args.horizon, max_steps),
        ) as executor:
            worker_results = list(executor.map(run_worker_task, tasks))
    else:
        initialize_worker(initial, trace, target_agent, args.horizon, max_steps)
        worker_results = [run_worker_task(task) for task in tasks]
    outcomes = {
        (decision_index, candidate_index): outcome
        for decision_index, candidate_index, outcome in worker_results
    }
    for decision_index in decisions:
        trace_row = trace[decision_index]
        debug = trace_row["target_policy_debug"]
        candidates = debug["candidate_scores"]
        branch_rows = []
        for candidate_index, candidate in enumerate(candidates):
            outcome = outcomes[(decision_index, candidate_index)]
            if max(
                outcome["position_max_abs_error"],
                outcome["angle_max_abs_error"],
                outcome.get("velocity_max_abs_error") or 0.0,
            ) > args.replay_tolerance:
                raise RuntimeError(
                    f"prefix replay exceeded tolerance at step {trace_row['step']}: {outcome}"
                )
            row = {
                "decision_step": int(trace_row["step"]),
                "decision_index": int(decision_index),
                "candidate_index": int(candidate_index),
                "action_steer": float(candidate["action"][0]),
                "action_gas": float(candidate["action"][1]),
                "action_brake": float(candidate["action"][2]),
                "model_score": float(candidate["score"]),
                **outcome,
            }
            row["physical_utility"] = physical_utility(row, weights)
            branch_rows.append(row)

        model_scores = np.asarray([row["model_score"] for row in branch_rows], dtype=np.float64)
        utilities = np.asarray([row["physical_utility"] for row in branch_rows], dtype=np.float64)
        rewards = np.asarray([row["cumulative_reward"] for row in branch_rows], dtype=np.float64)
        progress = np.asarray([row["longitudinal_progress_m"] for row in branch_rows], dtype=np.float64)
        model_best = int(np.argmax(model_scores))
        utility_best = float(np.max(utilities))
        reward_best = float(np.max(rewards))
        progress_best = float(np.max(progress))
        utility_rho = float(spearmanr(model_scores, utilities).statistic)
        reward_rho = float(spearmanr(model_scores, rewards).statistic)
        progress_rho = float(spearmanr(model_scores, progress).statistic)
        if not np.isfinite(utility_rho):
            utility_rho = None
        if not np.isfinite(reward_rho):
            reward_rho = None
        if not np.isfinite(progress_rho):
            progress_rho = None
        model_ranks = rankdata_desc(model_scores)
        utility_ranks = rankdata_desc(utilities)
        progress_ranks = rankdata_desc(progress)
        for row, model_rank, utility_rank, progress_rank in zip(
            branch_rows, model_ranks, utility_ranks, progress_ranks
        ):
            row["model_rank"] = float(model_rank)
            row["physical_utility_rank"] = float(utility_rank)
            row["longitudinal_progress_rank"] = float(progress_rank)
            row["model_selected"] = bool(row["candidate_index"] == model_best)
            candidate_rows.append(row)
        decision_rows.append(
            {
                "decision_step": int(trace_row["step"]),
                "candidate_count": int(len(branch_rows)),
                "model_utility_spearman": utility_rho,
                "model_reward_spearman": reward_rho,
                "model_progress_spearman": progress_rho,
                "physical_top1_hit": bool(
                    np.isclose(utilities[model_best], utility_best, rtol=0.0, atol=1e-12)
                ),
                "reward_top1_hit": bool(
                    np.isclose(rewards[model_best], reward_best, rtol=0.0, atol=1e-12)
                ),
                "progress_top1_hit": bool(
                    np.isclose(progress[model_best], progress_best, rtol=0.0, atol=1e-12)
                ),
                "physical_regret": float(utility_best - utilities[model_best]),
                "reward_regret": float(reward_best - rewards[model_best]),
                "progress_regret_m": float(progress_best - progress[model_best]),
                "selected_contact": bool(branch_rows[model_best]["contact_any"]),
                "best_available_contact": bool(
                    min(float(row["contact_any"]) for row in branch_rows) > 0.5
                ),
                "prefix_position_max_abs_error": float(
                    max(row["position_max_abs_error"] for row in branch_rows)
                ),
                "prefix_angle_max_abs_error": float(
                    max(row["angle_max_abs_error"] for row in branch_rows)
                ),
                "prefix_velocity_max_abs_error": float(
                    max((row.get("velocity_max_abs_error") or 0.0) for row in branch_rows)
                ),
            }
        )

    write_csv(args.out / "candidate_outcomes.csv", candidate_rows)
    write_csv(args.out / "decision_metrics.csv", decision_rows)
    utility_rhos = [row["model_utility_spearman"] for row in decision_rows if row["model_utility_spearman"] is not None]
    reward_rhos = [row["model_reward_spearman"] for row in decision_rows if row["model_reward_spearman"] is not None]
    progress_rhos = [row["model_progress_spearman"] for row in decision_rows if row["model_progress_spearman"] is not None]
    report = {
        "scope": "same-state short-horizon Box2D candidate counterfactual audit",
        "causal_contrast": (
            "Only the target action at the audited decision is changed; all later "
            "joint actions in the short horizon are frozen to the recorded trace."
        ),
        "target_agent": target_agent,
        "horizon": int(args.horizon),
        "eligible_decisions": int(
            sum(
                len(row.get("target_policy_debug", {}).get("candidate_scores", [])) >= 2
                for row in trace
            )
        ),
        "audited_decisions": len(decision_rows),
        "audited_candidates": len(candidate_rows),
        "physical_utility_weights": weights,
        "mean_model_utility_spearman": float(np.mean(utility_rhos)) if utility_rhos else None,
        "mean_model_reward_spearman": float(np.mean(reward_rhos)) if reward_rhos else None,
        "mean_model_progress_spearman": float(np.mean(progress_rhos)) if progress_rhos else None,
        "physical_top1_hit_rate": (
            float(np.mean([row["physical_top1_hit"] for row in decision_rows]))
            if decision_rows
            else None
        ),
        "reward_top1_hit_rate": (
            float(np.mean([row["reward_top1_hit"] for row in decision_rows]))
            if decision_rows
            else None
        ),
        "progress_top1_hit_rate": (
            float(np.mean([row["progress_top1_hit"] for row in decision_rows]))
            if decision_rows
            else None
        ),
        "mean_physical_regret": (
            float(np.mean([row["physical_regret"] for row in decision_rows]))
            if decision_rows
            else None
        ),
        "mean_reward_regret": (
            float(np.mean([row["reward_regret"] for row in decision_rows]))
            if decision_rows
            else None
        ),
        "mean_progress_regret_m": (
            float(np.mean([row["progress_regret_m"] for row in decision_rows]))
            if decision_rows
            else None
        ),
        "maximum_prefix_position_error": (
            float(max(row["prefix_position_max_abs_error"] for row in decision_rows))
            if decision_rows
            else None
        ),
        "maximum_prefix_angle_error": (
            float(max(row["prefix_angle_max_abs_error"] for row in decision_rows))
            if decision_rows
            else None
        ),
        "maximum_prefix_velocity_error": (
            float(max(row["prefix_velocity_max_abs_error"] for row in decision_rows))
            if decision_rows
            else None
        ),
        "interpretation_boundary": (
            "The audit tests local ranking fidelity under an open-loop frozen-action "
            "continuation; it does not estimate full-episode intervention effects."
        ),
    }
    manifest = {
        "initial": str(args.initial),
        "initial_sha256": sha256(args.initial),
        "trace": str(args.trace),
        "trace_sha256": sha256(args.trace),
        "script": str(Path(__file__).resolve()),
        "script_sha256": sha256(Path(__file__)),
        "arguments": vars(args) | {"initial": str(args.initial), "trace": str(args.trace), "out": str(args.out)},
    }
    (args.out / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (args.out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
