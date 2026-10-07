#!/usr/bin/env python
import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Validate a multi-car full-lap overtake demo summary.")
    parser.add_argument("summary_json")
    parser.add_argument("--max-target-grass-rate", type=float, default=0.20)
    parser.add_argument("--max-any-grass-rate", type=float, default=0.35)
    parser.add_argument("--require-target-complete", action="store_true")
    parser.add_argument("--require-target-first", action="store_true")
    parser.add_argument("--require-first-ahead", action="store_true")
    parser.add_argument("--require-all-complete", action="store_true")
    parser.add_argument("--min-mean-tile-progress", type=float, default=0.0)
    parser.add_argument("--min-first-ahead-step", type=int, default=0)
    parser.add_argument("--out", default="")
    args = parser.parse_args()

    data = json.loads(Path(args.summary_json).read_text(encoding="utf-8"))
    target_agent = int(data["target_agent"])
    grass = data["grass_rate"]
    tile_counts = data["tile_visited_count"]
    track_tiles = max(int(data["track_tiles"]), 1)
    tile_progress = [float(count) / track_tiles for count in tile_counts]
    checks = {
        "target_last_agent": target_agent == data["num_agents"] - 1,
        "target_grass_rate": grass[target_agent] <= args.max_target_grass_rate,
        "any_grass_rate": max(grass) <= args.max_any_grass_rate,
        "mean_tile_progress": (sum(tile_progress) / len(tile_progress)) >= args.min_mean_tile_progress,
    }
    if args.require_target_complete:
        checks["target_completed_lap"] = bool(data["target_completed_lap"])
    if args.require_target_first:
        checks["target_final_rank_by_tiles"] = int(data["target_final_rank_by_tiles"]) == 1
    if args.require_first_ahead:
        checks["first_ahead_step"] = (
            data["first_ahead_step"] is not None
            and int(data["first_ahead_step"]) >= args.min_first_ahead_step
        )
    if args.require_all_complete:
        checks["all_completed_lap"] = all(progress >= 1.0 for progress in tile_progress)

    output = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "summary_json": args.summary_json,
        "checks": checks,
        "metrics": {
            "target_grass_rate": grass[target_agent],
            "max_grass_rate": max(grass),
            "target_tile_progress": tile_progress[target_agent],
            "mean_tile_progress": sum(tile_progress) / len(tile_progress),
            "all_completed_lap": all(progress >= 1.0 for progress in tile_progress),
            "first_ahead_step": data["first_ahead_step"],
        },
        "summary": data,
    }
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(json.dumps(output, indent=2))
    raise SystemExit(0 if output["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
