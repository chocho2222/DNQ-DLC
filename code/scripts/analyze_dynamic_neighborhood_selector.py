#!/usr/bin/env python
"""Audit selector membership dynamics and critical-neighbor recall from traces."""

import argparse
import csv
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np

from audit_main_matrix_strict_endpoint import detect_events, track_arclength


PLAYFIELD = 2000.0 / 6.0


def selected_ids(row, target, mode, budget):
    positions = np.asarray(row["positions"], dtype=np.float64)
    velocities = np.asarray(row["velocities"], dtype=np.float64)
    headings = np.asarray(row["hull_angles"], dtype=np.float64)
    candidates = []
    ego_pos = positions[target]
    ego_vel = velocities[target]
    heading = headings[target]
    forward = np.array([-math.sin(heading), math.cos(heading)])
    left = np.array([math.cos(heading), math.sin(heading)])
    for other in range(len(positions)):
        if other == target:
            continue
        rel_pos = positions[other] - ego_pos
        rel_vel = velocities[other] - ego_vel
        rel_forward = float(np.dot(rel_pos, forward) / PLAYFIELD)
        rel_left = float(np.dot(rel_pos, left) / PLAYFIELD)
        distance = float(np.linalg.norm(rel_pos) / PLAYFIELD)
        rel_vx = float(rel_vel[0] / 50.0)
        rel_vy = float(rel_vel[1] / 50.0)
        if mode == "fixed":
            score = -float(other)
        elif mode == "nearest":
            score = -distance
        else:
            closing_speed = max(-rel_vx, 0.0) + max(-rel_vy, 0.0)
            heading_delta = headings[other] - heading
            heading_alignment = max(math.cos(heading_delta), 0.0) - 0.25 * abs(math.sin(heading_delta))
            forward_m = rel_forward * PLAYFIELD
            left_m = rel_left * PLAYFIELD
            distance_m = max(distance * PLAYFIELD, 1e-3)
            closing_mps = closing_speed * 50.0
            ahead = 0.0 < forward_m < 70.0 and abs(left_m) < 24.0
            alongside = abs(forward_m) < 14.0 and abs(left_m) < 18.0
            rear_pressure = -18.0 < forward_m <= 0.0 and abs(left_m) < 14.0 and closing_mps > 1.0
            if distance_m > 80.0 and not (ahead or alongside or rear_pressure):
                score = -1e6 - distance_m
            else:
                gap_score = 1.0 / max(distance_m / 12.0, 1.0)
                front_gap = max(0.0, 1.0 - abs(forward_m - 22.0) / 55.0) if ahead else 0.0
                lane_overlap = max(0.0, 1.0 - abs(left_m) / 18.0)
                score = (3.6 * float(ahead) * front_gap + 2.8 * float(alongside) * lane_overlap
                         + 1.7 * float(rear_pressure) + 1.1 * gap_score + 0.25 * closing_mps
                         + 0.18 * heading_alignment - 0.015 * distance_m)
        candidates.append((score, other))
    candidates.sort(key=lambda item: item[0], reverse=True)
    return {other for score, other in candidates[:budget] if score > -1e5}


def hazard_ids(row, target, horizon_s, distance_m):
    positions = np.asarray(row["positions"], dtype=np.float64)
    velocities = np.asarray(row["velocities"], dtype=np.float64)
    critical = set()
    for other in range(len(positions)):
        if other == target:
            continue
        rel_pos = positions[other] - positions[target]
        rel_vel = velocities[other] - velocities[target]
        denom = float(np.dot(rel_vel, rel_vel))
        closest_t = float(np.clip(-np.dot(rel_pos, rel_vel) / denom, 0.0, horizon_s)) if denom > 1e-8 else 0.0
        closest_distance = float(np.linalg.norm(rel_pos + closest_t * rel_vel))
        if min(float(np.linalg.norm(rel_pos)), closest_distance) <= distance_m:
            critical.add(other)
    return critical


def mean(values):
    clean = [value for value in values if value is not None and math.isfinite(value)]
    return float(np.mean(clean)) if clean else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--episode-csv", required=True, help="Strict audit episode ledger.")
    parser.add_argument("--out", required=True)
    parser.add_argument("--budget", type=int, default=3, help="Checkpoint packing budget; implementation parameter only.")
    parser.add_argument("--hazard-horizon", type=float, default=2.0)
    parser.add_argument("--hazard-distance", type=float, default=6.0)
    parser.add_argument("--event-hold", type=int, default=50)
    args = parser.parse_args()

    source = Path(args.episode_csv).resolve()
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    audit_rows = list(csv.DictReader(source.open(encoding="utf-8")))
    episode_rows = []
    for audit in audit_rows:
        if audit.get("status") != "ok" or not audit.get("trace_path"):
            continue
        trace_path = Path(audit["trace_path"])
        trace = json.loads(trace_path.read_text(encoding="utf-8"))
        summary_path = Path(audit["summary_path"])
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        initial_path = trace_path.with_name(trace_path.name.replace(".trace.json", ".initial.json"))
        initial = json.loads(initial_path.read_text(encoding="utf-8"))
        target = int(summary["target_agent"])
        selector_mode = str(summary.get("neighbor_selection_mode", "interaction"))
        if selector_mode in {"dynamic_interaction", "traffic"}:
            selector_mode = "interaction"
        if selector_mode in {"distance"}:
            selector_mode = "nearest"
        memberships = [selected_ids(row, target, selector_mode, args.budget) for row in trace]
        churn = []
        replacements = []
        for previous, current in zip(memberships, memberships[1:]):
            union = previous | current
            churn.append(1.0 - len(previous & current) / len(union) if union else 0.0)
            replacements.append(len(current - previous) / max(len(current), 1))

        hazard_hits = 0
        hazard_total = 0
        hazard_steps = 0
        for row, selected in zip(trace, memberships):
            critical = hazard_ids(row, target, args.hazard_horizon, args.hazard_distance)
            if critical:
                hazard_steps += 1
                hazard_hits += len(critical & selected)
                hazard_total += len(critical)

        geometry = track_arclength(initial["track"])
        events = detect_events(trace, target, geometry, approach_distance=20.0, pass_margin=4.0)
        event_hits = 0
        event_total = 0
        event_full_coverage = 0
        for event in events:
            start = int(event["start_index"])
            stop = min(int(event["complete_index"]) + args.event_hold, len(trace) - 1)
            opponent = int(event["opponent"])
            covered = [opponent in memberships[index] for index in range(start, stop + 1)]
            event_hits += sum(covered)
            event_total += len(covered)
            event_full_coverage += int(bool(covered) and all(covered))

        episode_rows.append({
            "experiment_id": audit.get("experiment_id"),
            "track_id": audit.get("track_id"),
            "num_agents": int(audit["num_agents"]),
            "seed": int(audit["seed"]),
            "algorithm": audit["algorithm"],
            "selector_mode": selector_mode,
            "steps": len(trace),
            "mean_jaccard_churn": mean(churn),
            "mean_replacement_fraction": mean(replacements),
            "membership_change_rate": mean([float(value > 0) for value in replacements]),
            "unique_neighbor_coverage": len(set().union(*memberships)) if memberships else 0,
            "hazard_step_count": hazard_steps,
            "hazard_neighbor_count": hazard_total,
            "hazard_neighbor_recall": hazard_hits / hazard_total if hazard_total else None,
            "physical_event_count": len(events),
            "event_neighbor_observations": event_total,
            "event_opponent_recall": event_hits / event_total if event_total else None,
            "event_full_coverage_rate": event_full_coverage / len(events) if events else None,
            "trace_path": str(trace_path),
        })

    fields = list(episode_rows[0]) if episode_rows else []
    with (out / "episode_selector_diagnostics.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(episode_rows)

    grouped = defaultdict(list)
    for row in episode_rows:
        grouped[row["algorithm"]].append(row)
    aggregate = []
    metric_names = [
        "mean_jaccard_churn", "mean_replacement_fraction", "membership_change_rate",
        "unique_neighbor_coverage", "hazard_neighbor_recall", "event_opponent_recall",
        "event_full_coverage_rate",
    ]
    for algorithm, rows in sorted(grouped.items()):
        record = {"algorithm": algorithm, "episode_n": len(rows)}
        for metric in metric_names:
            record[metric] = mean([row[metric] for row in rows])
        record["hazard_micro_recall"] = (
            sum((row["hazard_neighbor_recall"] or 0) * row["hazard_neighbor_count"] for row in rows)
            / sum(row["hazard_neighbor_count"] for row in rows)
            if sum(row["hazard_neighbor_count"] for row in rows) else None
        )
        record["event_micro_recall"] = (
            sum((row["event_opponent_recall"] or 0) * row["event_neighbor_observations"] for row in rows)
            / sum(row["event_neighbor_observations"] for row in rows)
            if sum(row["event_neighbor_observations"] for row in rows) else None
        )
        aggregate.append(record)
    aggregate_fields = list(aggregate[0]) if aggregate else []
    with (out / "aggregate_selector_diagnostics.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=aggregate_fields)
        writer.writeheader()
        writer.writerows(aggregate)

    manifest = {
        "source": str(source),
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "selection_reconstruction": "Recomputes the policy packing rule from saved positions, velocities, headings, and the identity-ordered environment exposure.",
        "critical_neighbor_definitions": {
            "hazard": f"Current or constant-velocity closest-approach distance <= {args.hazard_distance} m within {args.hazard_horizon} s.",
            "event": "The opponent whose centerline arc-length order reverses from at least 4 m behind to at least 4 m ahead; recall covers approach through the post-pass window.",
        },
        "checkpoint_budget": args.budget,
        "manuscript_boundary": "The budget is an implementation setting. The method is defined by a time-varying selected set and is not described as a fixed neighbor count.",
        "episode_count": len(episode_rows),
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"episodes": len(episode_rows), "algorithms": sorted(grouped), "out": str(out)}, indent=2))


if __name__ == "__main__":
    main()
