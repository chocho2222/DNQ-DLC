#!/usr/bin/env python
"""Rewrap the main 48-case plan for the proposed controller's seed spread.

The case grid (fleet size, seed, track) is the same one the main comparison
uses; only the algorithm column and the per-case output directory change, so
that each of the world-model seeds is evaluated on the same cases and the
endpoint audit can consume the run root unchanged.

Usage:
    python -m scripts.build_ours_seed_case_plan --base <plan.csv> \
        --out-dir <eval root> --seeds 13,21,47,71,99 --out <plan.csv>
"""
import argparse
import csv

ALGORITHM = "ours_dnq_dlc"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--seeds", default="",
                        help="world-model training seeds; one arm per seed")
    parser.add_argument("--arms", default="",
                        help="explicit comma-separated arm names; overrides --seeds, "
                             "which is how the fused single-arm plan is built")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    if args.arms:
        arms = [arm.strip() for arm in args.arms.split(",") if arm.strip()]
    else:
        seeds = [s.strip() for s in args.seeds.split(",") if s.strip()]
        if not seeds:
            raise SystemExit("give either --seeds or --arms")
        arms = [f"{ALGORITHM}_seed{seed}" for seed in seeds]
    rows = list(csv.DictReader(open(args.base, encoding="utf-8")))
    fields = list(rows[0].keys())
    for row in rows:
        row["algorithms"] = ",".join(arms)
        row["out_dir"] = (f"{args.out_dir}/{row['experiment_id']}"
                          f"_n{row['num_agents']}_seed{row['seed']}")
    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"{len(rows)} cases, {len(arms)} arms -> {args.out}")


if __name__ == "__main__":
    main()
