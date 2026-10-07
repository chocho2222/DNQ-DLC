#!/usr/bin/env python
import argparse
import json
from pathlib import Path


def load_results(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, dict) and "best" in data:
        return data["best"]
    return data


def evaluate_candidate(item, args):
    checks = {
        "tile_advantage": item["observer_tiles"] - item["baseline_tiles"] >= args.min_tile_advantage,
        "reward_advantage": item["observer_reward"] - item["baseline_reward"] >= args.min_reward_advantage,
        "grass_rate": item["observer_grass_rate"] <= args.max_observer_grass_rate,
        "overtake_event": bool(item["overtake_event"]),
        "final_progress": item["progress_delta_final"] >= args.min_final_progress,
        "final_ahead": bool(item["final_ahead"]),
    }
    return {
        "candidate": item,
        "checks": checks,
        "status": "PASS" if all(checks.values()) else "FAIL",
    }


def rank_candidate(item, args):
    hard_checks = (
        item["observer_tiles"] - item["baseline_tiles"] >= args.min_tile_advantage,
        item["observer_reward"] - item["baseline_reward"] >= args.min_reward_advantage,
        bool(item["overtake_event"]),
        item["progress_delta_final"] >= args.min_final_progress,
        bool(item["final_ahead"]),
    )
    return (
        int(item["observer_grass_rate"] <= args.max_observer_grass_rate),
        sum(int(check) for check in hard_checks),
        -item["observer_grass_rate"],
        item["score"],
    )


def main():
    parser = argparse.ArgumentParser(description="Validate visible in-track overtake behavior.")
    parser.add_argument("search_json")
    parser.add_argument("--min-tile-advantage", type=int, default=8)
    parser.add_argument("--min-reward-advantage", type=float, default=40.0)
    parser.add_argument("--max-observer-grass-rate", type=float, default=0.20)
    parser.add_argument("--min-final-progress", type=float, default=0.03)
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--out", default="")
    args = parser.parse_args()

    raw_results = load_results(args.search_json)
    ranked_results = sorted(raw_results, key=lambda item: rank_candidate(item, args), reverse=True)
    score_results = sorted(raw_results, key=lambda item: item["score"], reverse=True)
    selected = []
    seen = set()
    for item in ranked_results[: args.top_k] + score_results[: args.top_k]:
        key = (
            item["seed"],
            item["observer_agent"],
            item["blend"],
            item["unsafe_blend"],
        )
        if key in seen:
            continue
        seen.add(key)
        selected.append(item)
    evaluated = [evaluate_candidate(item, args) for item in selected]

    passing = [item for item in evaluated if item["status"] == "PASS"]
    output = {
        "status": "PASS" if passing else "FAIL",
        "search_json": args.search_json,
        "thresholds": {
            "min_tile_advantage": args.min_tile_advantage,
            "min_reward_advantage": args.min_reward_advantage,
            "max_observer_grass_rate": args.max_observer_grass_rate,
            "min_final_progress": args.min_final_progress,
            "top_k": args.top_k,
        },
        "passing_count": len(passing),
        "best_passing": passing[0] if passing else None,
        "evaluated": evaluated,
    }

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(json.dumps(output, indent=2))
    raise SystemExit(0 if passing else 1)


if __name__ == "__main__":
    main()
