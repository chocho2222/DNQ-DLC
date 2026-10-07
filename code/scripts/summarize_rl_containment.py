#!/usr/bin/env python
"""Containment numbers quoted for the continuous-control families.

The strict endpoint audit reports each RL family as a mean over its five
training seeds. The containment paragraphs of the manuscript quote the same
families on two further quantities that the endpoint aggregation does not carry,
and this script recomputes them from the released tables so that no sentence in
the paper rests on a number that cannot be reproduced:

  * whole-episode containment, read from ``episode_level.csv`` written by
    ``scripts/measure_episode_containment.py``: the fraction of steps on grass
    and the mean absolute lateral offset in road half widths, pooled over the
    five training seeds and reported per seed as well, so the spread between
    seeds is visible;
  * manoeuvre-window containment, read from the strict audit's
    ``case_level.csv``: the fraction of the window beyond one road half-width
    (``frac_offroad``) and the mean absolute lateral offset over the window
    (``mean_abs_lat``), restricted to the cases that complete a physical pass,
    which is the denominator the paper states;
  * the number of completed physical passes, which is the denominator behind
    both the window means and the pass-level figure caption.

The same two episode quantities are reported for the structured controllers
from the main-matrix episode table, so the "narrowest of the eight" statement
about the lateral interquartile range is checked in one place.

Usage:
    python -m scripts.summarize_rl_containment \
        --rl-episode <episode_level.csv> --rl-case <case_level.csv> \
        --main-episode <episode_level.csv> --out <dir>
"""
import argparse
import csv
import json
import os
from collections import defaultdict

import numpy as np

FAMILY = {"ppo": "PPO", "sac": "SAC", "td3": "TD3"}
MAIN_ORDER = ["ours_dnq_dlc", "rule_expert_gate", "dlc_joint_transition_observer",
              "dlc_individual_transition", "dlc_joint_transition"]
LABEL = {"ours_dnq_dlc": "DNQ-DLC (ours)", "rule_expert_gate": "rule expert",
         "dlc_joint_transition_observer": "DLC-JTO", "dlc_individual_transition": "DLC-IT",
         "dlc_joint_transition": "DLC-JT"}


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def family_of(algorithm):
    return FAMILY.get(algorithm.split("_seed")[0])


def training_seed(algorithm):
    return algorithm.split("_seed")[1] if "_seed" in algorithm else ""


def value(row, key):
    raw = row.get(key, "")
    return float("nan") if raw in ("", "nan", None) else float(raw)


def iqr(values):
    q1, _median, q3 = np.percentile(np.asarray(values, float), [25, 50, 75])
    return float(q1), float(q3)


def episode_containment(rows):
    """Whole-episode grass fraction and mean |lat| per family, pooled and per seed."""
    pooled = defaultdict(lambda: {"grass": [], "lat": []})
    per_seed = defaultdict(lambda: defaultdict(lambda: {"grass": [], "lat": []}))
    for row in rows:
        family = family_of(row["algorithm"])
        if family is None:
            continue
        grass, lat = value(row, "episode_grass"), value(row, "episode_lat")
        if grass != grass or lat != lat:
            continue
        pooled[family]["grass"].append(grass)
        pooled[family]["lat"].append(lat)
        seed = per_seed[family][training_seed(row["algorithm"])]
        seed["grass"].append(grass)
        seed["lat"].append(lat)
    out = {}
    for family, data in pooled.items():
        seeds = {seed: {"grass": float(np.mean(v["grass"])),
                        "lat": float(np.mean(v["lat"]))}
                 for seed, v in sorted(per_seed[family].items())}
        out[family] = {
            "grass_mean": float(np.mean(data["grass"])),
            "grass_seed_range": [min(s["grass"] for s in seeds.values()),
                                 max(s["grass"] for s in seeds.values())],
            "lat_mean": float(np.mean(data["lat"])),
            "lat_seed_range": [min(s["lat"] for s in seeds.values()),
                               max(s["lat"] for s in seeds.values())],
            "lat_iqr": iqr(data["lat"]),
            "case_runs": len(data["grass"]),
            "per_seed": seeds,
        }
    return out


def window_containment(rows):
    """Window off-surface share and mean |lat| over the cases with a physical pass."""
    per_family = defaultdict(lambda: defaultdict(list))
    for row in rows:
        family = family_of(row["algorithm"])
        if family is None or row.get("status") != "ok" or row.get("P") != "True":
            continue
        off, lat = value(row, "frac_offroad"), value(row, "mean_abs_lat")
        if off != off or lat != lat:
            continue
        per_family[family][training_seed(row["algorithm"])].append((off, lat))
    out = {}
    for family, seeds in per_family.items():
        flat = [item for items in seeds.values() for item in items]
        out[family] = {
            "passes": len(flat),
            "frac_offroad": float(np.mean([item[0] for item in flat])),
            "mean_abs_lat": float(np.mean([item[1] for item in flat])),
            "per_seed_frac_offroad": {seed: float(np.mean([i[0] for i in items]))
                                      for seed, items in sorted(seeds.items())},
        }
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--rl-episode", required=True)
    parser.add_argument("--rl-case", required=True)
    parser.add_argument("--main-episode", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    episode = episode_containment(read_csv(args.rl_episode))
    window = window_containment(read_csv(args.rl_case))
    main_episode = defaultdict(lambda: {"grass": [], "lat": []})
    for row in read_csv(args.main_episode):
        main_episode[row["algorithm"]]["grass"].append(value(row, "episode_grass"))
        main_episode[row["algorithm"]]["lat"].append(value(row, "episode_lat"))
    structured = {algorithm: {"grass_mean": float(np.mean(main_episode[algorithm]["grass"])),
                              "lat_mean": float(np.mean(main_episode[algorithm]["lat"])),
                              "lat_iqr": iqr(main_episode[algorithm]["lat"]),
                              "cases": len(main_episode[algorithm]["grass"])}
                  for algorithm in MAIN_ORDER if main_episode[algorithm]["grass"]}

    os.makedirs(args.out, exist_ok=True)
    report = {"episode": episode, "window": window, "structured": structured}
    with open(os.path.join(args.out, "rl_containment_summary.json"), "w",
              encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, sort_keys=True)

    widths = {name: data["lat_iqr"][1] - data["lat_iqr"][0]
              for name, data in structured.items()}
    widths.update({family: data["lat_iqr"][1] - data["lat_iqr"][0]
                   for family, data in episode.items()})
    print(f"{'arm':22s}{'grass':>8}{'|lat|':>8}{'lat IQR':>18}{'window off':>12}"
          f"{'window lat':>12}{'passes':>8}")
    for name, data in structured.items():
        print(f"{LABEL[name]:22s}{data['grass_mean']:8.3f}{data['lat_mean']:8.2f}"
              f"{data['lat_iqr'][0]:8.2f}-{data['lat_iqr'][1]:<8.2f}"
              f"{'-':>12}{'-':>12}{data['cases']:8d}")
    for family in ("PPO", "SAC", "TD3"):
        data, win = episode[family], window.get(family, {})
        print(f"{family:22s}{data['grass_mean']:8.3f}{data['lat_mean']:8.2f}"
              f"{data['lat_iqr'][0]:8.2f}-{data['lat_iqr'][1]:<8.2f}"
              f"{win.get('frac_offroad', float('nan')):12.3f}"
              f"{win.get('mean_abs_lat', float('nan')):12.2f}{win.get('passes', 0):8d}")
    narrowest = min(widths, key=widths.get)
    print(f"narrowest lateral interquartile width: {narrowest} "
          f"({widths[narrowest]:.3f} half widths)")


if __name__ == "__main__":
    main()
