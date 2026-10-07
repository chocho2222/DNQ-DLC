#!/usr/bin/env python
import argparse
import csv
import json
import math
from pathlib import Path

import numpy as np

from dlc.rollout import make_env


DEFAULT_METHODS = [
    "main:lane_base_only",
    "main:overtake_base_only",
    "adaptive:graph_adaptive_shield",
]

DEFAULT_SUITES = {
    "main": "evaluations/multiseed_suite/multiseed_suite_summary.json",
    "adaptive": "evaluations/adaptive_gate_suite/multiseed_suite_summary.json",
}


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def row_score(row):
    return (
        int(row["validation_status"] == "PASS"),
        int(row["target_completed_lap"]),
        -int(row["target_final_rank_by_tiles"]),
        -float(row["target_grass_rate"]),
        float(row["target_tile_progress"]),
    )


def wrap_pi(angle):
    return (angle + math.pi) % (2.0 * math.pi) - math.pi


def track_features(seed, num_agents=4, gap_tiles=22, lateral_spacing=0.0):
    start_order = list(range(num_agents))
    env = make_env(
        num_agents=num_agents,
        seed=seed,
        observation_type="telemetry",
        start_order=start_order,
        line_spacing=gap_tiles,
        lateral_spacing=lateral_spacing,
    )
    try:
        env.reset()
        track = np.asarray(env.unwrapped.track, dtype=np.float64)
        xy = track[:, 2:4]
        deltas = np.diff(np.vstack([xy, xy[:1]]), axis=0)
        segment_lengths = np.linalg.norm(deltas, axis=1)
        headings = np.arctan2(deltas[:, 1], deltas[:, 0])
        heading_delta = np.asarray(
            [wrap_pi(headings[(i + 1) % len(headings)] - headings[i]) for i in range(len(headings))],
            dtype=np.float64,
        )
        abs_turn = np.abs(heading_delta)
        span = np.maximum(xy.max(axis=0) - xy.min(axis=0), 1e-6)
        return {
            "seed": int(seed),
            "n_tiles": float(len(track)),
            "total_length": float(segment_lengths.sum()),
            "mean_segment": float(segment_lengths.mean()),
            "std_segment": float(segment_lengths.std()),
            "mean_abs_turn": float(abs_turn.mean()),
            "std_abs_turn": float(abs_turn.std()),
            "p90_abs_turn": float(np.percentile(abs_turn, 90)),
            "max_abs_turn": float(abs_turn.max()),
            "straight_fraction": float(np.mean(abs_turn < 0.025)),
            "sharp_fraction": float(np.mean(abs_turn > 0.10)),
            "bbox_aspect": float(span[0] / span[1]),
            "bbox_area": float(span[0] * span[1]),
        }
    finally:
        env.close()


def load_rows(root):
    rows = {}
    for suite_name, rel_path in DEFAULT_SUITES.items():
        path = root / rel_path
        if not path.exists():
            continue
        suite = load_json(path)
        for row in suite["rows"]:
            item = dict(row)
            item["suite"] = suite_name
            item["method_key"] = f"{suite_name}:{row['method']}"
            rows[(item["method_key"], item["seed"])] = item
    return rows


def normalize_features(feature_rows, keys):
    matrix = np.asarray([[row[key] for key in keys] for row in feature_rows], dtype=np.float64)
    mean = matrix.mean(axis=0)
    std = matrix.std(axis=0)
    std[std < 1e-9] = 1.0
    return (matrix - mean) / std


def choose_method_for_seed(seed_index, seeds, methods, rows, feature_matrix, k):
    test_vector = feature_matrix[seed_index]
    train_indices = [idx for idx in range(len(seeds)) if idx != seed_index]
    distances = [(idx, float(np.linalg.norm(feature_matrix[idx] - test_vector))) for idx in train_indices]
    neighbors = sorted(distances, key=lambda item: item[1])[:k]

    method_scores = []
    for method in methods:
        pass_values = []
        quality_values = []
        for neighbor_idx, distance in neighbors:
            neighbor_seed = seeds[neighbor_idx]
            row = rows[(method, neighbor_seed)]
            weight = 1.0 / (distance + 1e-6)
            pass_values.append(weight * int(row["validation_status"] == "PASS"))
            quality_values.append((weight, row_score(row)))
        pass_score = sum(pass_values) / sum(1.0 / (distance + 1e-6) for _, distance in neighbors)
        quality_score = max(score for _, score in quality_values)
        method_scores.append((pass_score, quality_score, method))
    method_scores.sort(reverse=True)
    return method_scores[0][2], neighbors, method_scores


def main():
    parser = argparse.ArgumentParser(description="Evaluate a small leave-one-seed-out geometry portfolio selector.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    parser.add_argument("--out-prefix", default="portfolio_selector_loso")
    parser.add_argument("--methods", default=",".join(DEFAULT_METHODS))
    parser.add_argument("--k", type=int, default=3)
    parser.add_argument("--num-agents", type=int, default=4)
    parser.add_argument("--gap-tiles", type=int, default=22)
    parser.add_argument("--lateral-spacing", type=float, default=0.0)
    args = parser.parse_args()

    root = Path(args.root)
    methods = [item.strip() for item in args.methods.split(",") if item.strip()]
    rows = load_rows(root)
    seeds = sorted({seed for method, seed in rows if method in methods})
    missing = [(method, seed) for method in methods for seed in seeds if (method, seed) not in rows]
    if missing:
        raise ValueError(f"missing method/seed rows: {missing[:10]}")

    feature_rows = [
        track_features(seed, num_agents=args.num_agents, gap_tiles=args.gap_tiles, lateral_spacing=args.lateral_spacing)
        for seed in seeds
    ]
    feature_keys = [key for key in feature_rows[0] if key != "seed"]
    feature_matrix = normalize_features(feature_rows, feature_keys)

    selector_rows = []
    for seed_index, seed in enumerate(seeds):
        selected, neighbors, method_scores = choose_method_for_seed(
            seed_index, seeds, methods, rows, feature_matrix, max(1, min(args.k, len(seeds) - 1))
        )
        selected_row = rows[(selected, seed)]
        oracle_row = max((rows[(method, seed)] for method in methods), key=row_score)
        selector_rows.append(
            {
                "seed": seed,
                "selected_method": selected,
                "selected_status": selected_row["validation_status"],
                "selected_progress": selected_row["target_tile_progress"],
                "selected_grass": selected_row["target_grass_rate"],
                "selected_rank": selected_row["target_final_rank_by_tiles"],
                "oracle_method": oracle_row["method_key"],
                "oracle_status": oracle_row["validation_status"],
                "neighbor_seeds": [seeds[idx] for idx, _ in neighbors],
                "method_scores": [
                    {"method": method, "pass_score": score, "quality_score": list(quality)}
                    for score, quality, method in method_scores
                ],
            }
        )

    pass_count = sum(row["selected_status"] == "PASS" for row in selector_rows)
    oracle_pass_count = sum(row["oracle_status"] == "PASS" for row in selector_rows)
    report = {
        "root": str(root),
        "selector": "leave-one-seed-out k-nearest-neighbor over initial track geometry",
        "note": (
            "This is a small-sample selector prototype. It does not use seed identity or final test outcomes "
            "for the held-out seed, but it is not yet a publication-grade learned controller."
        ),
        "methods": methods,
        "k": max(1, min(args.k, len(seeds) - 1)),
        "feature_keys": feature_keys,
        "features": feature_rows,
        "n": len(selector_rows),
        "pass_count": pass_count,
        "pass_rate": pass_count / len(selector_rows) if selector_rows else None,
        "oracle_pass_count": oracle_pass_count,
        "oracle_pass_rate": oracle_pass_count / len(selector_rows) if selector_rows else None,
        "rows": selector_rows,
    }

    table_dir = root / "tables"
    table_dir.mkdir(parents=True, exist_ok=True)
    out_json = table_dir / f"{args.out_prefix}.json"
    out_csv = table_dir / f"{args.out_prefix}_rows.csv"
    out_md = table_dir / f"{args.out_prefix}.md"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    with out_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "seed",
                "selected_method",
                "selected_status",
                "selected_progress",
                "selected_grass",
                "selected_rank",
                "oracle_method",
                "oracle_status",
                "neighbor_seeds",
            ],
        )
        writer.writeheader()
        for row in selector_rows:
            item = dict(row)
            item["neighbor_seeds"] = ",".join(str(seed) for seed in item["neighbor_seeds"])
            item.pop("method_scores")
            writer.writerow(item)

    lines = [
        "# Portfolio Selector LOSO Report",
        "",
        f"- Selector: {report['selector']}",
        f"- Methods: {', '.join(methods)}",
        f"- k: {report['k']}",
        f"- Pass rate: {pass_count}/{len(selector_rows)}",
        f"- Oracle upper bound over same methods: {oracle_pass_count}/{len(selector_rows)}",
        "",
        "## Held-out Seed Decisions",
        "",
        "| seed | selected | status | oracle | oracle status | neighbors |",
        "|---:|---|---|---|---|---|",
    ]
    for row in selector_rows:
        lines.append(
            f"| {row['seed']} | {row['selected_method']} | {row['selected_status']} | "
            f"{row['oracle_method']} | {row['oracle_status']} | "
            f"{', '.join(str(seed) for seed in row['neighbor_seeds'])} |"
        )
    lines.extend(["", "## Note", "", report["note"], ""])
    out_md.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv)}, indent=2))


if __name__ == "__main__":
    main()
