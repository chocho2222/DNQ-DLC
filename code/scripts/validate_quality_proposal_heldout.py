#!/usr/bin/env python
"""Episode-disjoint validation for the filtered quality-proposal Graph BC actor."""

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dlc.graph_policy import GraphActorBundle
from scripts.collect_elegant_overtake_dataset import collect_dataset


def collect(args, name, track, min_agents, max_agents, seed):
    namespace = argparse.Namespace(
        episodes=args.episodes,
        min_agents=min_agents,
        max_agents=max_agents,
        max_steps=args.max_steps,
        gap_tiles=args.gap_tiles,
        lateral_spacing=args.lateral_spacing,
        seed=seed,
        observation_type="telemetry_dynamic",
        max_neighbors=3,
        track_path=track,
        traffic_profile=args.traffic_profile,
        target_policies=args.target_policies,
        accept_mode=args.accept_mode,
        pre_context=args.pre_context,
        post_context=args.post_context,
        stable_samples_per_episode=0,
        stable_lateral_threshold=0.26,
        stable_heading_cos_threshold=0.92,
        stable_min_speed=6.0,
        recovery_context=0,
        contact_distance=3.0,
        finish_mode="any",
        collection_workers=args.collection_workers,
        out_dir="",
    )
    observations, actions, summaries = collect_dataset(namespace)
    return name, observations, actions, summaries


def evaluate(bundle, observations, actions, train_action_mean, device):
    if len(observations) == 0:
        return {"samples": 0}
    with torch.no_grad():
        tensor = torch.as_tensor(bundle.normalize_obs(observations), dtype=torch.float32, device=device)
        prediction = bundle.actor(tensor).cpu().numpy()
    error = prediction - actions
    baseline_error = np.broadcast_to(train_action_mean, actions.shape) - actions
    denominator = np.sum((actions - actions.mean(axis=0, keepdims=True)) ** 2, axis=0)
    r2 = 1.0 - np.sum(error ** 2, axis=0) / np.maximum(denominator, 1e-12)
    return {
        "samples": int(len(actions)),
        "action_mse": float(np.mean(error ** 2)),
        "action_mae": float(np.mean(np.abs(error))),
        "action_mae_by_dimension": np.mean(np.abs(error), axis=0).tolist(),
        "action_rmse_by_dimension": np.sqrt(np.mean(error ** 2, axis=0)).tolist(),
        "action_r2_by_dimension": r2.tolist(),
        "mean_action_baseline_mse": float(np.mean(baseline_error ** 2)),
        "mse_improvement_vs_mean_baseline": float(np.mean(baseline_error ** 2) - np.mean(error ** 2)),
        "prediction_mean": prediction.mean(axis=0).tolist(),
        "target_mean": actions.mean(axis=0).tolist(),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="outputs/tits_dynamic_graph/models/quality_graph_bc_v1/graph_bc.graph.pt")
    parser.add_argument("--training-dataset", default="outputs/tits_dynamic_graph/elegant_overtake_dataset_v1/elegant_overtake_dataset.npz")
    parser.add_argument("--output-dir", default="outputs/tits_dynamic_graph_expanded/heldout_quality_proposal_validation_20260710")
    parser.add_argument("--episodes", type=int, default=8)
    parser.add_argument("--max-steps", type=int, default=1600)
    parser.add_argument("--seed", type=int, default=8200)
    parser.add_argument("--gap-tiles", type=int, default=18)
    parser.add_argument("--lateral-spacing", type=float, default=0.0)
    parser.add_argument("--traffic-profile", choices=["slow_traffic", "mixed_traffic"], default="slow_traffic")
    parser.add_argument("--target-policies", default="telemetry_expert_gate,telemetry_expert_fast,telemetry_expert_barrier,telemetry_adaptive")
    parser.add_argument("--accept-mode", choices=["elegant", "on_track", "success"], default="on_track")
    parser.add_argument("--pre-context", type=int, default=30)
    parser.add_argument("--post-context", type=int, default=45)
    parser.add_argument("--collection-workers", type=int, default=1)
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args()
    device = torch.device(args.device)
    bundle = GraphActorBundle.load(args.model, map_location=device)
    bundle.actor.to(device).eval()
    training = np.load(args.training_dataset, allow_pickle=True)
    train_actions = np.asarray(training["actions"], dtype=np.float32)
    train_action_mean = train_actions.mean(axis=0)
    strata = [
        ("id_procedural_n4_6", "", 4, 6, args.seed),
        ("ood_hairpin_n8", "tracks/hairpin_scaled.npz", 8, 8, args.seed + 100),
        ("ood_s_curve_n8", "tracks/s_curve_scaled.npz", 8, 8, args.seed + 200),
    ]
    reports = {}
    ledger = []
    for spec in strata:
        name, observations, actions, summaries = collect(args, *spec)
        accepted = int(sum(row["accepted_event_count"] for row in summaries))
        total = int(sum(row["overtake_count"] for row in summaries))
        reports[name] = {
            "track": spec[1] or "procedural",
            "episode_count": len(summaries),
            "episodes_with_samples": int(sum(row["selected_samples"] > 0 for row in summaries)),
            "accepted_events": accepted,
            "total_events": total,
            "accepted_event_rate": accepted / max(total, 1),
            "prediction": evaluate(bundle, observations, actions, train_action_mean, device),
        }
        ledger.extend({"stratum": name, **row} for row in summaries)
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    payload = {
        "model": args.model,
        "training_dataset": args.training_dataset,
        "training_samples": int(len(train_actions)),
        "training_action_mean": train_action_mean.tolist(),
        "protocol": vars(args),
        "interpretation_boundary": "Conditional imitation accuracy on newly collected accepted-event states; not direct evidence of closed-loop safety or proposal benefit.",
        "strata": reports,
    }
    (output / "heldout_quality_proposal_validation.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    fields = ["stratum", "episode", "seed", "num_agents", "target_policy", "steps", "overtake_count", "accepted_event_count", "selected_samples", "target_grass_rate"]
    with (output / "heldout_quality_episode_ledger.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in ledger:
            writer.writerow({key: row.get(key, "") for key in fields})
    lines = ["# Held-out Quality-proposal Validation", "", "This is conditional action-imitation validation, not closed-loop safety evidence.", "", "| stratum | episodes | episodes with samples | samples | accepted events | action MSE | mean-baseline MSE |", "|---|---:|---:|---:|---:|---:|---:|"]
    for name, report in reports.items():
        pred = report["prediction"]
        mse = pred.get("action_mse")
        baseline = pred.get("mean_action_baseline_mse")
        lines.append(f"| {name} | {report['episode_count']} | {report['episodes_with_samples']} | {pred['samples']} | {report['accepted_events']} | {mse if mse is not None else 'NA'} | {baseline if baseline is not None else 'NA'} |")
    (output / "heldout_quality_proposal_validation.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(output / "heldout_quality_proposal_validation.json"), "strata": list(reports)}, indent=2))


if __name__ == "__main__":
    main()
