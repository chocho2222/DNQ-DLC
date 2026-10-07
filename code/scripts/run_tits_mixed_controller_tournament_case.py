#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
from PIL import Image

from dlc.policies import MixedPolicy, make_policy
from dlc.rollout import make_env
from scripts.run_tits_dynamic_graph_evaluation import (
    draw_topdown_frame,
    ensure_dirs,
    plot_chinese_summary,
    rank_from_tiles,
    save_gif,
    save_video,
    selected_algorithms,
    summarize_trace,
    track_indices,
    world_bounds,
    write_source_table,
)
from scripts.tits_figure_style import bind_algorithm_colors, label_for_algorithm


def make_controller(record, args, agent_id):
    policy = make_policy(
        record["policy"],
        seed=args.seed + agent_id,
        device=args.device,
        safe=bool(record.get("safe", False)),
        safe_blend=float(record.get("safe_blend", args.safe_blend)),
        unsafe_blend=float(record.get("unsafe_blend", args.unsafe_blend)),
        safe_base_policy=record.get("safe_base_policy", args.safe_base_policy),
        neighbor_mode=record.get("neighbor_mode", "dynamic"),
        max_neighbors=record.get("max_neighbors", args.max_neighbors),
        neighbor_selection_mode=record.get("neighbor_selection_mode", args.neighbor_selection_mode),
        planner_horizon=record.get("planner_horizon"),
        planner_candidates=record.get("planner_candidates"),
        planner_risk_weight=record.get("planner_risk_weight"),
        planner_progress_weight=record.get("planner_progress_weight"),
        planner_uncertainty_weight=record.get("planner_uncertainty_weight"),
        overtake_aware_planner=record.get("overtake_aware_planner"),
        quality_proposal_path=record.get("quality_proposal_path"),
        quality_planner_mode=record.get("quality_planner_mode", "proposal_only"),
        quality_rollout_blend=record.get("quality_rollout_blend"),
        quality_overtake_weight=record.get("quality_overtake_weight"),
        quality_lane_weight=record.get("quality_lane_weight"),
        quality_grass_weight=record.get("quality_grass_weight"),
        quality_close_gap_weight=record.get("quality_close_gap_weight"),
        learned_quality_weight=record.get("learned_quality_weight"),
        learned_quality_gate=record.get("learned_quality_gate", False),
        learned_quality_min_on_track=record.get("learned_quality_min_on_track", 0.45),
        learned_quality_max_grass=record.get("learned_quality_max_grass", 0.55),
        learned_quality_max_lane_error=record.get("learned_quality_max_lane_error", 0.72),
        learned_quality_gate_penalty=record.get("learned_quality_gate_penalty", 2.0),
        elegance_barrier=record.get("elegance_barrier", False),
        elegance_barrier_weight=record.get("elegance_barrier_weight", 1.0),
        elegance_lateral_limit=record.get("elegance_lateral_limit", 0.30),
        elegance_heading_cos_min=record.get("elegance_heading_cos_min", 0.82),
        elegance_grass_penalty=record.get("elegance_grass_penalty", 2.0),
        elegance_backward_penalty=record.get("elegance_backward_penalty", 1.2),
        elegance_close_gap_limit=record.get("elegance_close_gap_limit", 8.0),
        geometry_generalization=record.get("geometry_generalization", False),
        geometry_curvature_lookahead=record.get("geometry_curvature_lookahead", 8),
        geometry_curvature_speed_weight=record.get("geometry_curvature_speed_weight", 18.0),
        geometry_lateral_speed_weight=record.get("geometry_lateral_speed_weight", 4.5),
        geometry_heading_speed_weight=record.get("geometry_heading_speed_weight", 5.0),
        geometry_min_speed=record.get("geometry_min_speed", 9.5),
        geometry_anchor_blend=record.get("geometry_anchor_blend", 0.35),
        geometry_barrier_weight=record.get("geometry_barrier_weight", 0.65),
    )
    if hasattr(policy, "set_controlled_agent"):
        policy.set_controlled_agent(agent_id)
    return policy


def run_case(args, dirs):
    assignment = [item.strip() for item in args.assignment.split(",") if item.strip()]
    if len(assignment) != args.num_agents:
        raise ValueError(f"assignment length {len(assignment)} does not match num_agents={args.num_agents}")
    algorithms = {record["name"]: record for record in selected_algorithms(",".join(sorted(set(assignment))), json.loads(Path(args.config).read_text(encoding="utf-8")))}
    policies = [make_controller(algorithms[name], args, agent_id) for agent_id, name in enumerate(assignment)]
    policy = MixedPolicy(policies)
    dynamic_neighbor_settings = [
        algorithms[name].get("max_neighbors", args.max_neighbors)
        for name in assignment
        if algorithms[name].get("neighbor_mode", "fixed") == "dynamic"
    ]
    if any(item is None or int(item) <= 0 for item in dynamic_neighbor_settings):
        env_max_neighbors = None
    elif dynamic_neighbor_settings:
        env_max_neighbors = max(int(item) for item in dynamic_neighbor_settings)
    else:
        env_max_neighbors = args.max_neighbors

    env = make_env(
        num_agents=args.num_agents,
        seed=args.seed,
        observation_type=args.observation_type,
        start_order=list(range(args.num_agents)),
        line_spacing=args.line_spacing,
        lateral_spacing=args.lateral_spacing,
        track_path=args.track_path or None,
        max_neighbors=env_max_neighbors,
        telemetry_version=args.telemetry_version,
        neighbor_order=args.neighbor_order,
    )
    env.unwrapped.allow_legacy_checkpoint_migration = bool(args.legacy_checkpoint_migration)
    if hasattr(env, "_max_episode_steps"):
        env._max_episode_steps = max(int(args.max_steps) + 1, int(env._max_episode_steps))

    target_agent = int(args.target_agent)
    trace = []
    topdown_frames = []
    first_person_frames = []
    all_first_person_frames = [[] for _ in range(args.num_agents)]
    render_error = None
    all_render_errors = [None] * args.num_agents
    total_reward = np.zeros(args.num_agents, dtype=np.float64)
    histories = [[] for _ in range(args.num_agents)]
    first_complete_step = [None] * args.num_agents
    labels = [label_for_algorithm(name) for name in assignment]
    agent_colors = bind_algorithm_colors(env, assignment)
    (dirs["summaries"] / f"mixed_n{args.num_agents}_seed{args.seed}_target{target_agent}.colors.json").write_text(
        json.dumps(env.unwrapped.algorithm_color_assignment, indent=2), encoding="utf-8"
    )
    steps_run = 0

    try:
        obs = env.reset()
        policy.reset()
        lo, hi = world_bounds(env)
        track_tiles = len(env.unwrapped.track)
        for agent_id, car in enumerate(env.unwrapped.cars):
            histories[agent_id].append(np.asarray(car.hull.position, dtype=np.float32))
        want_topdown_frames = (not args.no_gif) or bool(args.video)
        want_first_person_frames = bool(args.first_person_gif) or bool(args.first_person_video)
        want_all_first_person_frames = bool(args.all_first_person_gifs) or bool(args.all_first_person_videos)
        if want_topdown_frames:
            topdown_frames.append(draw_topdown_frame(env, histories, 0, labels, target_agent, total_reward, lo, hi, args.width, args.height, agent_colors=agent_colors))
            if want_first_person_frames or want_all_first_person_frames:
                try:
                    rendered = env.render("rgb_array")
                    if want_first_person_frames:
                        first_person_frames.append(Image.fromarray(rendered[target_agent]))
                    if want_all_first_person_frames:
                        for agent_id in range(args.num_agents):
                            all_first_person_frames[agent_id].append(Image.fromarray(rendered[agent_id]))
                except Exception as exc:
                    render_error = repr(exc)

        for step in range(args.max_steps):
            started = time.perf_counter()
            action = policy.act(env, obs)
            latency_ms = (time.perf_counter() - started) * 1000.0
            obs, reward, done, _ = env.step(action)
            steps_run = step + 1
            total_reward += reward
            tile_counts = list(map(int, env.unwrapped.tile_visited_count))
            ranks = rank_from_tiles(tile_counts)
            for agent_id, count in enumerate(tile_counts):
                if first_complete_step[agent_id] is None and count >= track_tiles:
                    first_complete_step[agent_id] = steps_run
            positions = [np.asarray(car.hull.position, dtype=np.float32) for car in env.unwrapped.cars]
            for agent_id, pos in enumerate(positions):
                histories[agent_id].append(pos)
            pair_distances = [
                float(np.linalg.norm(positions[i] - positions[j]))
                for i in range(args.num_agents)
                for j in range(i + 1, args.num_agents)
            ]
            trace.append(
                {
                    "step": int(steps_run),
                    "reward": np.asarray(reward, dtype=float).tolist(),
                    "total_reward": total_reward.tolist(),
                    "tile_visited_count": tile_counts,
                    "rank": ranks,
                    "track_index": track_indices(env),
                    "action": np.asarray(action, dtype=float).tolist(),
                    "speed": [float(np.linalg.norm(car.hull.linearVelocity)) for car in env.unwrapped.cars],
                    "compute_latency_ms": float(latency_ms),
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
                    "assignment": assignment,
                }
            )
            if want_topdown_frames and steps_run % args.frame_every == 0:
                topdown_frames.append(draw_topdown_frame(env, histories, steps_run, labels, target_agent, total_reward, lo, hi, args.width, args.height, agent_colors=agent_colors))
                if (want_first_person_frames or want_all_first_person_frames) and render_error is None:
                    try:
                        rendered = env.render("rgb_array")
                        if want_first_person_frames:
                            first_person_frames.append(Image.fromarray(rendered[target_agent]))
                        if want_all_first_person_frames:
                            for agent_id in range(args.num_agents):
                                if all_render_errors[agent_id] is None:
                                    all_first_person_frames[agent_id].append(Image.fromarray(rendered[agent_id]))
                    except Exception as exc:
                        render_error = repr(exc)
            if args.finish_mode == "any" and any(count >= track_tiles for count in tile_counts):
                break
            if args.finish_mode == "target" and tile_counts[target_agent] >= track_tiles:
                break
            if args.finish_mode == "all" and all(count >= track_tiles for count in tile_counts):
                break
            if done and args.finish_mode == "env_done":
                break
    finally:
        try:
            track_tiles = len(env.unwrapped.track)
        except Exception:
            track_tiles = 0
        env.close()

    target_record = dict(algorithms[assignment[target_agent]])
    target_record["name"] = f"mixed_target_{target_record['name']}"
    target_record["label_cn"] = f"Mixed target {target_record.get('label_cn', assignment[target_agent])}"
    target_record["policy"] = "mixed_controller_assignment:" + ",".join(assignment)
    gif_paths = {}
    stem = f"mixed_n{args.num_agents}_seed{args.seed}_target{target_agent}"
    if not args.no_gif:
        gif_paths["topdown"] = save_gif(topdown_frames, dirs["gifs"] / f"{stem}.topdown.gif", args.fps)
        if args.first_person_gif and render_error is None:
            gif_paths["first_person"] = save_gif(first_person_frames, dirs["gifs"] / f"{stem}.first_person.gif", args.fps)
        else:
            gif_paths["first_person"] = None
        if args.first_person_gif and args.all_first_person_gifs:
            all_paths = {}
            for agent_id, frames in enumerate(all_first_person_frames):
                if frames and all_render_errors[agent_id] is None:
                    name = assignment[agent_id]
                    all_paths[str(agent_id)] = save_gif(
                        frames,
                        dirs["gifs"] / f"{stem}_agent{agent_id}_{name}.first_person.gif",
                        args.fps,
                    )
                else:
                    all_paths[str(agent_id)] = None
            gif_paths["first_person_by_agent"] = all_paths
    video_paths = {}
    if args.video:
        video_paths["topdown"] = save_video(topdown_frames, dirs["gifs"] / f"{stem}.topdown.mp4", args.fps)
    if args.first_person_video and render_error is None:
        video_paths["first_person"] = save_video(first_person_frames, dirs["gifs"] / f"{stem}.first_person.mp4", args.fps)
    elif args.first_person_video:
        video_paths["first_person"] = None
    if args.all_first_person_videos:
        all_video_paths = {}
        for agent_id, frames in enumerate(all_first_person_frames):
            if frames and all_render_errors[agent_id] is None:
                name = assignment[agent_id]
                all_video_paths[str(agent_id)] = save_video(
                    frames,
                    dirs["gifs"] / f"{stem}_agent{agent_id}_{name}.first_person.mp4",
                    args.fps,
                )
            else:
                all_video_paths[str(agent_id)] = None
        video_paths["first_person_by_agent"] = all_video_paths

    summary = summarize_trace(
        trace,
        args,
        target_record,
        target_agent,
        track_tiles,
        total_reward,
        steps_run,
        first_complete_step,
        gif_paths,
        video_paths,
        render_error,
    )
    summary["experiment_id"] = "E4_interaction_generalization"
    summary["assignment"] = assignment
    summary["agent_algorithm"] = {str(idx): name for idx, name in enumerate(assignment)}
    summary["background_vehicles"] = 0
    summary["competition_mode"] = "same_track_four_controller_race"
    if "first_person_by_agent" in gif_paths:
        summary["first_person_gifs_by_agent"] = gif_paths["first_person_by_agent"]
    if "first_person_by_agent" in video_paths:
        summary["first_person_videos_by_agent"] = video_paths["first_person_by_agent"]
    summary_path = dirs["summaries"] / f"{stem}.summary.json"
    trace_path = dirs["traces"] / f"{stem}.trace.json"
    summary["summary_path"] = str(summary_path)
    summary["trace_path"] = str(trace_path)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    trace_path.write_text(json.dumps(trace, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def main():
    parser = argparse.ArgumentParser(description="Run one mixed-controller tournament case.")
    parser.add_argument("--config", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--assignment", required=True)
    parser.add_argument("--target-agent", type=int, required=True)
    parser.add_argument("--num-agents", type=int, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--max-steps", type=int, default=2200)
    parser.add_argument("--finish-mode", choices=["any", "target", "all", "env_done", "steps"], default="any")
    parser.add_argument("--observation-type", choices=["telemetry", "telemetry_dynamic"], default="telemetry_dynamic")
    parser.add_argument("--telemetry-version", choices=["legacy_v1", "corrected_v2"], default="corrected_v2")
    parser.add_argument("--neighbor-order", choices=["identity", "relevance"], default="identity")
    parser.add_argument("--legacy-checkpoint-migration", action="store_true",
                        help="Explicit exploratory conversion for legacy checkpoints in corrected_v2 envs.")
    parser.add_argument("--max-neighbors", type=int, default=3)
    parser.add_argument("--neighbor-selection-mode", default="interaction")
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--track-path", default="")
    parser.add_argument("--traffic-profile", choices=["slow_traffic", "mixed_traffic", "four_controller_race_no_background"], default="mixed_traffic")
    parser.add_argument("--line-spacing", type=int, default=5)
    parser.add_argument("--lateral-spacing", type=float, default=2.2)
    parser.add_argument("--safe-blend", type=float, default=0.25)
    parser.add_argument("--unsafe-blend", type=float, default=1.0)
    parser.add_argument("--safe-base-policy", default="telemetry_expert_barrier")
    parser.add_argument("--contact-distance", type=float, default=2.0)
    parser.add_argument("--no-gif", action="store_true")
    parser.add_argument("--first-person-gif", action="store_true")
    parser.add_argument("--all-first-person-gifs", action="store_true")
    parser.add_argument("--video", action="store_true", help="Save top-down MP4 video.")
    parser.add_argument("--first-person-video", action="store_true", help="Save target-agent first-person MP4 video.")
    parser.add_argument("--all-first-person-videos", action="store_true", help="Save MP4 first-person video for every controlled agent.")
    parser.add_argument("--frame-every", type=int, default=12)
    parser.add_argument("--fps", type=int, default=12)
    parser.add_argument("--width", type=int, default=900)
    parser.add_argument("--height", type=int, default=900)
    args = parser.parse_args()

    dirs = ensure_dirs(args.out_dir)
    summary = run_case(args, dirs)
    source_csv = write_source_table([summary], dirs["tables"] / f"mixed_metrics_n{args.num_agents}_seed{args.seed}.csv")
    figures = plot_chinese_summary([summary], dirs["figures"])
    suite = {"args": vars(args), "source_csv": source_csv, "figures": figures, "summary": summary}
    suite_path = dirs["root"] / f"mixed_suite_n{args.num_agents}_seed{args.seed}.json"
    suite_path.write_text(json.dumps(suite, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"suite": str(suite_path), "summary": summary.get("summary_path"), "source_csv": source_csv}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
