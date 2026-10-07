#!/usr/bin/env python
"""Rewrap the main 48-case plan for the strictly retrained RL evaluation.

The evaluation root is the same grid of (fleet size, seed) cases, but the
algorithms written into it are ``<family>_seed<training seed>`` arms. This keeps
the endpoint audit, which is driven by a case plan, able to run unchanged.

Usage:
    python -m scripts.build_rl_strict_case_plan --base <plan.csv> \
        --out-dir <rl eval root> --out <plan.csv>
"""
import argparse
import csv

FAMILIES = ["ppo", "sac", "td3"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--seeds", default="2026001,2026002,2026003,2026004,2026005")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    training_seeds = [s.strip() for s in args.seeds.split(",") if s.strip()]
    arms = [f"{family}_seed{seed}" for family in FAMILIES for seed in training_seeds]
    rows = list(csv.DictReader(open(args.base, encoding="utf-8")))
    fields = list(rows[0].keys())
    for row in rows:
        row["algorithms"] = ",".join(arms)
        # One directory per case, matching the writer used by the evaluation
        # runner; the endpoint audit resolves summaries and traces from here.
        row["out_dir"] = (f"{args.out_dir}/{row['experiment_id']}"
                          f"_n{row['num_agents']}_seed{row['seed']}")
    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"{len(rows)} cases, {len(arms)} arms -> {args.out}")


if __name__ == "__main__":
    main()
