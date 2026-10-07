#!/usr/bin/env python
"""Validate a frozen graph world model on episode-disjoint simulator rollouts."""

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

from dlc.graph_world_model import GraphWorldModelBundle
from scripts.train_graph_risk_world_model import collect_dataset


def roc_auc(y, score):
    y = np.asarray(y, dtype=int)
    score = np.asarray(score, dtype=float)
    pos = y == 1
    neg = y == 0
    if not np.any(pos) or not np.any(neg):
        return None
    order = np.argsort(score)
    ranks = np.empty(len(score), dtype=float)
    ranks[order] = np.arange(1, len(score) + 1)
    return float((ranks[pos].sum() - pos.sum() * (pos.sum() + 1) / 2) / (pos.sum() * neg.sum()))


def average_precision(y, score):
    y = np.asarray(y, dtype=int)
    if y.sum() == 0:
        return None
    order = np.argsort(-np.asarray(score, dtype=float))
    ranked = y[order]
    precision = np.cumsum(ranked) / np.arange(1, len(ranked) + 1)
    return float((precision * ranked).sum() / ranked.sum())


def ece(y, probability, bins=10):
    y = np.asarray(y, dtype=float)
    probability = np.asarray(probability, dtype=float)
    total = len(y)
    value = 0.0
    rows = []
    for idx in range(bins):
        lo, hi = idx / bins, (idx + 1) / bins
        mask = (probability >= lo) & (probability < hi if idx < bins - 1 else probability <= hi)
        if not np.any(mask):
            continue
        confidence = float(probability[mask].mean())
        frequency = float(y[mask].mean())
        value += mask.sum() / total * abs(confidence - frequency)
        rows.append({"bin_lower": lo, "bin_upper": hi, "n": int(mask.sum()), "confidence": confidence, "risk_frequency": frequency})
    return float(value), rows


def collect(args, track_path, min_agents, max_agents, seed, protocol=None, out_dir=None):
    """Collect held-out episodes under the *checkpoint's* own observation protocol.

    The archived invocation left ``telemetry_version`` unset, so the held-out
    episodes were rolled out with the legacy observation channel while the
    validated checkpoint consumed the corrected one. The protocol is now taken
    from the checkpoint metadata so a mismatch is impossible.
    """
    meta = protocol or {}
    namespace = argparse.Namespace(
        episodes=args.episodes,
        min_agents=min_agents,
        max_agents=max_agents,
        seed=seed,
        observation_type="telemetry_dynamic",
        max_steps=args.max_steps,
        gap_tiles=args.gap_tiles,
        lateral_spacing=args.lateral_spacing,
        track_path=track_path,
        max_neighbors=args.max_neighbors,
        risk_lateral=args.risk_lateral,
        collection_workers=args.collection_workers,
        telemetry_version=meta.get("telemetry_version", "legacy_v1"),
        neighbor_selection=meta.get("neighbor_selection", "interaction"),
        neighbor_keep_prob=float(meta.get("neighbor_keep_prob", 0.9)),
        use_slot_mask=bool(meta.get("use_slot_mask", False)),
        slot_feature_dim=int(meta.get("slot_feature_dim", 7)),
        expert_source=meta.get("expert_source", "legacy_rule"),
        background_profile=meta.get("background_profile", "legacy_mixed"),
        start_layout=meta.get("start_layout", "single_file"),
        data_split=str(meta.get("data_split", "heldout")),
        out_dir=str(out_dir if out_dir is not None else Path(args.output_dir) / "heldout_collection"),
    )
    return collect_dataset(namespace)


def one_step(bundle, transitions, device, batch_size):
    by_agents = {}
    for row in transitions:
        by_agents.setdefault(int(row["num_agents"]), []).append(row)
    state_sq = []
    state_abs = []
    reward_abs = []
    risk_y = []
    risk_p = []
    target_state_sq = []
    with torch.no_grad():
        for rows in by_agents.values():
            for start in range(0, len(rows), batch_size):
                batch = rows[start : start + batch_size]
                obs_raw = np.stack([row["obs"] for row in batch]).astype(np.float32)
                action = np.stack([row["action"] for row in batch]).astype(np.float32)
                next_raw = np.stack([row["next_obs"] for row in batch]).astype(np.float32)
                reward = np.stack([row["reward"] for row in batch]).astype(np.float32)
                risk = np.stack([row["risk"] for row in batch]).astype(np.float32)
                obs = torch.as_tensor(bundle.normalize_obs(obs_raw), dtype=torch.float32, device=device)
                action_tensor = torch.as_tensor(action, dtype=torch.float32, device=device)
                out = bundle.transition(obs, action_tensor)
                pred_raw = bundle.denormalize_obs(out["next_mu"].cpu().numpy())
                reward_pred = out["reward_mu"].cpu().numpy()
                probability = torch.sigmoid(out["risk_logits"]).cpu().numpy()
                error = pred_raw - next_raw
                state_sq.append(error.reshape(-1, error.shape[-1]) ** 2)
                state_abs.append(np.abs(error.reshape(-1, error.shape[-1])))
                target_indices = [int(row["target_agent"]) for row in batch]
                target_state_sq.extend(error[idx, target_indices[idx]] ** 2 for idx in range(len(batch)))
                reward_abs.append(np.abs(reward_pred - reward).ravel())
                risk_y.append(risk.ravel())
                risk_p.append(probability.ravel())
    state_sq = np.concatenate(state_sq)
    state_abs = np.concatenate(state_abs)
    reward_abs = np.concatenate(reward_abs)
    risk_y = np.concatenate(risk_y)
    risk_p = np.concatenate(risk_p)
    calibration_error, calibration_bins = ece(risk_y, risk_p)
    return {
        "agent_transition_count": int(len(risk_y)),
        "state_rmse_all": float(np.sqrt(state_sq.mean())),
        "state_mae_all": float(state_abs.mean()),
        "state_rmse_by_feature": np.sqrt(state_sq.mean(axis=0)).tolist(),
        "target_state_rmse": float(np.sqrt(np.asarray(target_state_sq).mean())),
        "reward_mae": float(reward_abs.mean()),
        "risk_prevalence": float(risk_y.mean()),
        "risk_auroc": roc_auc(risk_y, risk_p),
        "risk_auprc": average_precision(risk_y, risk_p),
        "risk_brier": float(np.mean((risk_p - risk_y) ** 2)),
        "risk_ece_10bin": calibration_error,
        "risk_calibration_bins": calibration_bins,
    }


def episode_slices(transitions, summaries):
    offset = 0
    episodes = []
    for summary in summaries:
        steps = int(summary["steps"])
        episodes.append(transitions[offset : offset + steps])
        offset += steps
    if offset != len(transitions):
        raise ValueError(f"episode accounting mismatch: {offset} vs {len(transitions)}")
    return episodes


def multistep(bundle, transitions, summaries, horizons, stride, max_windows, device):
    episodes = episode_slices(transitions, summaries)
    rng = np.random.default_rng(20260710)
    result = {}
    with torch.no_grad():
        for horizon in horizons:
            candidates = []
            for episode_id, rows in enumerate(episodes):
                for start in range(0, max(0, len(rows) - horizon + 1), stride):
                    candidates.append((episode_id, start))
            if len(candidates) > max_windows:
                indices = rng.choice(len(candidates), max_windows, replace=False)
                candidates = [candidates[int(index)] for index in indices]
            squared = []
            target_squared = []
            for episode_id, start in candidates:
                rows = episodes[episode_id]
                predicted = bundle.normalize_obs(rows[start]["obs"])
                for step in range(horizon):
                    action = rows[start + step]["action"]
                    obs_tensor = torch.as_tensor(predicted[None], dtype=torch.float32, device=device)
                    action_tensor = torch.as_tensor(action[None], dtype=torch.float32, device=device)
                    predicted = bundle.transition(obs_tensor, action_tensor)["next_mu"][0].cpu().numpy()
                predicted_raw = bundle.denormalize_obs(predicted)
                target_raw = rows[start + horizon - 1]["next_obs"]
                error = predicted_raw - target_raw
                squared.append(float(np.mean(error ** 2)))
                target_squared.append(float(np.mean(error[int(rows[start]["target_agent"])] ** 2)))
            sq = np.asarray(squared, dtype=float)
            target_sq = np.asarray(target_squared, dtype=float)
            result[str(horizon)] = {
                "windows": len(candidates),
                "state_rmse_all": float(np.sqrt(sq.mean())) if len(sq) else None,
                "target_state_rmse": float(np.sqrt(target_sq.mean())) if len(target_sq) else None,
            }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="outputs/tits_dynamic_graph/models/ours_dynamic_graph_dlc_world/graph_risk_dlc_world.graphworld.pt")
    parser.add_argument("--output-dir", default="outputs/tits_dynamic_graph_expanded/heldout_world_model_validation_20260710")
    parser.add_argument("--episodes", type=int, default=8)
    parser.add_argument("--max-steps", type=int, default=600)
    parser.add_argument("--seed", type=int, default=7300)
    parser.add_argument("--gap-tiles", type=int, default=18)
    parser.add_argument("--lateral-spacing", type=float, default=0.0)
    parser.add_argument("--max-neighbors", type=int, default=3)
    parser.add_argument("--risk-lateral", type=float, default=0.45)
    parser.add_argument("--collection-workers", type=int, default=1)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--horizons", default="1,3,5,10")
    parser.add_argument("--rollout-stride", type=int, default=10)
    parser.add_argument("--max-rollout-windows", type=int, default=200)
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args()
    device = torch.device(args.device)
    bundle = GraphWorldModelBundle.load(args.model, map_location=device)
    bundle.transition.to(device).eval()
    strata = [
        ("id_procedural_n4_6", "", 4, 6, args.seed),
        ("ood_hairpin_n8", "tracks/hairpin_scaled.npz", 8, 8, args.seed + 100),
        ("ood_s_curve_n8", "tracks/s_curve_scaled.npz", 8, 8, args.seed + 200),
    ]
    horizons = [int(value) for value in args.horizons.split(",") if value.strip()]
    output_root = Path(args.output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    reports = {}
    episode_rows = []
    for name, track, min_agents, max_agents, seed in strata:
        transitions, summaries = collect(args, track, min_agents, max_agents, seed,
                                        protocol=bundle.meta,
                                        out_dir=output_root / f"heldout_collection_{name}")
        reports[name] = {
            "track": track or "procedural",
            "min_agents": min_agents,
            "max_agents": max_agents,
            "seed_start": seed,
            "episode_count": len(summaries),
            "transition_count": len(transitions),
            "one_step": one_step(bundle, transitions, device, args.batch_size),
            "multi_step": multistep(bundle, transitions, summaries, horizons, args.rollout_stride, args.max_rollout_windows, device),
        }
        for row in summaries:
            episode_rows.append({"stratum": name, **row})
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    payload = {"model": args.model, "model_meta": bundle.meta, "protocol": vars(args), "strata": reports}
    (output / "heldout_world_model_validation.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    with (output / "heldout_episode_ledger.csv").open("w", newline="", encoding="utf-8") as handle:
        fields = ["stratum", "episode", "seed", "num_agents", "steps", "done", "tile_visited_count", "grass_rate", "total_reward"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in episode_rows:
            writer.writerow({key: row.get(key, "") for key in fields})
    lines = ["# Held-out World-model Validation", "", "| stratum | episodes | transitions | state RMSE | reward MAE | risk AUROC | risk AUPRC | risk ECE | H=10 RMSE |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for name, report in reports.items():
        one = report["one_step"]
        h10 = report["multi_step"].get("10", {}).get("state_rmse_all")
        lines.append(f"| {name} | {report['episode_count']} | {report['transition_count']} | {one['state_rmse_all']:.4f} | {one['reward_mae']:.4f} | {one['risk_auroc'] if one['risk_auroc'] is not None else 'NA'} | {one['risk_auprc'] if one['risk_auprc'] is not None else 'NA'} | {one['risk_ece_10bin']:.4f} | {h10 if h10 is not None else 'NA'} |")
    (output / "heldout_world_model_validation.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(output / "heldout_world_model_validation.json"), "strata": list(reports)}, indent=2))


if __name__ == "__main__":
    main()
