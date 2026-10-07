#!/usr/bin/env python
"""Endpoint counts of every learned arm over the draws of its training recipe.

The main comparison reports one trained instance per arm. Both the proposed
controller and the retrained DLC family are trained by stochastic recipes, so
one instance is one draw. This script re-reads every draw that has been
released for those arms and prints, per arm, the per-draw endpoint counts, the
draw mean and range, the whole-episode containment, and the paired comparison
against the rule expert at the draw level.

Sources
  --ours-draws        validity_ours_seedspread_20260928 /case_level.csv
  --dlc-draws-root    dlc_arm_draws_20260928 (draw_A .. draw_D)
  --reference         validity_final_all /case_level.csv (rule expert, RL arms,
                      and the single published DLC draw)
  --ours-containment  containment_ours_seedspread_20260928 /episode_level.csv

Usage:
    python3 scripts/report_draw_level_endpoints.py --out /tmp/draw_level.json
"""

import argparse
import csv
import json
import statistics as stats
from pathlib import Path

DLC_ARMS = ("dlc_individual_transition", "dlc_joint_transition",
            "dlc_joint_transition_observer")
OURS_PREFIX = "ours_dnq_dlc_seed"


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def counts(rows):
    return {
        "n": len(rows),
        "P": sum(1 for r in rows if r["P"] == "True"),
        "E_pass": sum(1 for r in rows if r["E_pass"] == "True"),
        "E_valid": sum(1 for r in rows if r["E_valid"] == "True"),
        "E_full": sum(1 for r in rows if r["E_full"] == "True"),
        "E_race": sum(1 for r in rows if r["E_race"] == "True"),
        "rank_gain": stats.mean(float(r["rank_gain"]) for r in rows),
        "target_progress": stats.mean(float(r["target_progress"]) for r in rows),
    }


def group(rows, algorithm):
    return [r for r in rows if r["algorithm"] == algorithm]


def containment(path):
    if not path or not Path(path).exists():
        return {}
    out = {}
    for row in read_csv(path):
        out.setdefault(row["algorithm"], []).append(row)
    summary = {}
    for algorithm, rows in out.items():
        summary[algorithm] = {
            "n": len(rows),
            "grass": stats.mean(float(r["episode_grass"]) for r in rows),
            "lat": stats.mean(float(r["episode_lat"]) for r in rows),
        }
    return summary


def paired_against(rows, algorithm, reference_algorithm, reference_rows, endpoint):
    key = lambda r: (r["experiment_id"], r["seed"])
    ref = {key(r): r[endpoint] == "True"
           for r in reference_rows if r["algorithm"] == reference_algorithm}
    win = lose = 0
    for row in group(rows, algorithm):
        other = ref.get(key(row))
        if other is None:
            continue
        mine = row[endpoint] == "True"
        if mine and not other:
            win += 1
        elif other and not mine:
            lose += 1
    return {"win": win, "lose": lose}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ours-draws", required=True)
    parser.add_argument("--dlc-draws-root", required=True)
    parser.add_argument("--reference", required=True)
    parser.add_argument("--ours-containment", default="")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    ours_rows = read_csv(Path(args.ours_draws) / "case_level.csv")
    reference_rows = read_csv(Path(args.reference) / "case_level.csv")
    keep = ("status", "ok")

    report = {"arms": {}, "paired_against_rule": {}}

    ours_draws = {}
    for algorithm in sorted({r["algorithm"] for r in ours_rows}):
        if not algorithm.startswith(OURS_PREFIX):
            continue
        rows = [r for r in group(ours_rows, algorithm) if r.get(keep[0]) == keep[1]]
        ours_draws[algorithm] = counts(rows)
        report["paired_against_rule"][algorithm] = paired_against(
            ours_rows, algorithm, "rule_expert_gate", reference_rows, "E_full")
    report["arms"]["proposed"] = {
        "draws": ours_draws,
        "E_full_mean": stats.mean(v["E_full"] for v in ours_draws.values()),
        "E_full_range": [min(v["E_full"] for v in ours_draws.values()),
                         max(v["E_full"] for v in ours_draws.values())],
        "P_range": [min(v["P"] for v in ours_draws.values()),
                    max(v["P"] for v in ours_draws.values())],
    }

    dlc_root = Path(args.dlc_draws_root)
    for arm in DLC_ARMS:
        draws = {}
        for draw_dir in sorted(dlc_root.glob("draw_*")):
            rows = [r for r in read_csv(draw_dir / "case_level.csv")
                    if r.get("status") == "ok"]
            draws[draw_dir.name] = counts(group(rows, arm))
            report["paired_against_rule"][f"{arm}:{draw_dir.name}"] = paired_against(
                rows, arm, "rule_expert_gate", reference_rows, "E_full")
        report["arms"][arm] = {
            "draws": draws,
            "E_full_mean": stats.mean(v["E_full"] for v in draws.values()),
            "E_full_range": [min(v["E_full"] for v in draws.values()),
                             max(v["E_full"] for v in draws.values())],
        }

    published = {}
    for algorithm in ("rule_expert_gate", "dlc_individual_transition",
                      "dlc_joint_transition", "dlc_joint_transition_observer",
                      "ppo_continuous", "sac_continuous", "td3_continuous"):
        rows = group(reference_rows, algorithm)
        if rows:
            published[algorithm] = counts(rows)
    report["arms"]["published_single_draw"] = published

    report["containment"] = {
        "proposed": containment(args.ours_containment),
        "dlc": {draw_dir.name: containment(draw_dir / "containment_episode_level.csv")
                for draw_dir in sorted(dlc_root.glob("draw_*"))},
        "rule_expert_gate": {"grass": 0.299, "lat": 1.23},
    }

    Path(args.out).write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    print(f"{'arm':<18}{'E_full per draw':<30}{'mean':>6}{'range':>10}")
    for name, block in report["arms"].items():
        if "draws" not in block:
            continue
        values = [v["E_full"] for v in block["draws"].values()]
        print(f"{name:<18}{str(values):<30}{stats.mean(values):>6.1f}"
              f"{str(block['E_full_range']):>10}")
    print()
    print("paired against the rule expert on E_full:")
    for name, block in report["paired_against_rule"].items():
        print(f"  {name:<46} win {block['win']:2d}  lose {block['lose']:2d}")


if __name__ == "__main__":
    main()
