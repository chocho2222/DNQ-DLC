#!/usr/bin/env python
import argparse
import json
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser(
        description="Merge per-seed visible overtake validation reports."
    )
    parser.add_argument("--search-dir", default="outputs/torch_dlc_shaped_multiseed/overtake_search")
    parser.add_argument("--seeds", default="0,1,2,3,4")
    parser.add_argument("--prefer-conservative", default="0,3")
    parser.add_argument("--out", default="")
    args = parser.parse_args()

    search_dir = Path(args.search_dir)
    seeds = [int(item.strip()) for item in args.seeds.split(",") if item.strip()]
    prefer_conservative = {
        int(item.strip())
        for item in args.prefer_conservative.split(",")
        if item.strip()
    }

    results = []
    for seed in seeds:
        seed_dir = search_dir / f"seed_{seed}"
        candidates = []
        names = ["overtake_validation_conservative.json", "overtake_validation.json"]
        if seed not in prefer_conservative:
            names.reverse()
        for name in names:
            path = seed_dir / name
            if not path.exists():
                continue
            report = load_json(path)
            if report.get("status") == "PASS" and report.get("best_passing"):
                candidates.append((path, report))

        if candidates:
            path, report = candidates[0]
            results.append(
                {
                    "seed": seed,
                    "status": "PASS",
                    "validation_json": str(path),
                    "best_passing": report["best_passing"],
                }
            )
        else:
            results.append(
                {
                    "seed": seed,
                    "status": "FAIL",
                    "validation_json": "",
                    "best_passing": None,
                }
            )

    pass_count = sum(1 for item in results if item["status"] == "PASS")
    summary = {
        "status": "PASS" if pass_count == len(results) and results else "FAIL",
        "search_dir": str(search_dir),
        "seed_count": len(results),
        "pass_count": pass_count,
        "pass_rate": pass_count / len(results) if results else 0.0,
        "results": results,
    }
    out_path = Path(args.out) if args.out else search_dir / "combined_overtake_summary.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    raise SystemExit(0 if summary["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
