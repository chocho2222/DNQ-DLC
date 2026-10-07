#!/usr/bin/env python
"""Create a four-panel manuscript figure from frozen experiment source data."""
import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np


# Times New Roman is the publication target. Liberation Serif is the local metric-compatible fallback.
plt.rcParams["font.family"] = "serif"
plt.rcParams["font.serif"] = ["Times New Roman", "Liberation Serif", "Nimbus Roman"]
plt.rcParams["svg.fonttype"] = "none"
plt.rcParams["pdf.fonttype"] = 42
plt.rcParams["font.size"] = 11
plt.rcParams["axes.labelsize"] = 12
plt.rcParams["xtick.labelsize"] = 10
plt.rcParams["ytick.labelsize"] = 10
plt.rcParams["legend.fontsize"] = 10
plt.rcParams["axes.linewidth"] = 2.0
plt.rcParams["xtick.major.width"] = 2.0
plt.rcParams["ytick.major.width"] = 2.0
plt.rcParams["axes.spines.top"] = False
plt.rcParams["axes.spines.right"] = False


COLORS = {
    "proposed": "#1F5A94",
    "baseline": "#7A7A7A",
    "accent": "#C45A56",
    "quality": "#4C956C",
    "neutral": "#B9B9B9",
}


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def read_csv(path):
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def save_publication(fig, stem):
    stem = Path(stem)
    stem.parent.mkdir(parents=True, exist_ok=True)
    outputs = {}
    for ext, kwargs in [("svg", {}), ("pdf", {}), ("png", {"dpi": 600}), ("tiff", {"dpi": 600})]:
        path = stem.with_suffix(f".{ext}")
        fig.savefig(path, bbox_inches="tight", **kwargs)
        outputs[ext] = str(path)
    return outputs


def panel_label(ax, label):
    ax.text(-0.09, 1.03, label, transform=ax.transAxes, ha="left", va="bottom", fontsize=13, fontweight="normal")


def build_figure(ablation_report, scale_csv, failure_csv, out_stem):
    report = read_json(ablation_report)
    paired = report["paired_full_minus_ablation"]
    components = [
        ("dnq_w_o_dynamic_selection", "Dynamic selection"),
        ("dnq_w_o_quality_proposal", "Quality proposal"),
        ("dnq_w_o_risk_uncertainty", "Risk + uncertainty"),
        ("dnq_w_o_hard_recovery", "Recovery"),
        ("dnq_w_o_safety_quality", "Safety-quality terms"),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(11.5, 8.2), constrained_layout=True)
    ax = axes[0, 0]
    labels = [label for _, label in components]
    elegant = [paired[key]["metrics"]["elegant_overtake_rate"]["full_minus_ablation_mean"] for key, _ in components]
    grass = [-paired[key]["metrics"]["target_grass_rate"]["full_minus_ablation_mean"] for key, _ in components]
    x = np.arange(len(labels))
    width = 0.36
    ax.bar(x - width / 2, elegant, width, color=COLORS["quality"], label="Desirable overtaking")
    ax.bar(x + width / 2, grass, width, color=COLORS["proposed"], label="Lower grass exposure")
    ax.axhline(0, color="black", linewidth=1.2)
    ax.set_ylabel("Full method minus ablation")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=25, ha="right")
    ax.set_title("Component attribution", fontweight="normal")
    ax.legend(frameon=False)
    panel_label(ax, "a")

    scale = read_csv(scale_csv)
    unique_scale = {}
    for row in scale:
        source = row.get("_summary_file") or row.get("summary_path") or ""
        key = source or (row.get("algorithm"), row.get("num_agents"), row.get("seed"))
        unique_scale[key] = row
    scale = list(unique_scale.values())
    grouped = defaultdict(lambda: defaultdict(list))
    for row in scale:
        try:
            n = int(row["num_agents"])
            alg = row["algorithm"]
            grouped[alg][n].append((float(row["overtake_success_rate"]), float(row["on_track_overtake_rate"])))
        except (KeyError, TypeError, ValueError):
            continue
    ax = axes[0, 1]
    for alg, label, color, marker in [
        ("v6_runtime_dynamic_neighborhood_safe", "Proposed", COLORS["proposed"], "o"),
        ("dlc_joint_transition_observer", "DLC-JTO", COLORS["baseline"], "s"),
        ("rule_expert_gate", "Rule expert", COLORS["accent"], "^"),
    ]:
        ns = sorted(grouped[alg])
        success = [np.mean([v[0] for v in grouped[alg][n]]) for n in ns]
        ax.plot(ns, success, marker=marker, linewidth=2.4, markersize=7, color=color, label=label)
    ax.set_xlabel("Number of vehicles")
    ax.set_ylabel("Overtake success rate")
    ax.set_ylim(-0.05, 1.05)
    ax.set_xticks([4, 6, 8, 10, 12])
    ax.set_title("Scale extension", fontweight="normal")
    ax.legend(frameon=False)
    panel_label(ax, "b")

    ax = axes[1, 0]
    for alg, label, color, marker in [
        ("v6_runtime_dynamic_neighborhood_safe", "Proposed", COLORS["proposed"], "o"),
        ("dlc_joint_transition_observer", "DLC-JTO", COLORS["baseline"], "s"),
        ("rule_expert_gate", "Rule expert", COLORS["accent"], "^"),
    ]:
        ns = sorted(grouped[alg])
        on_track = [np.mean([v[1] for v in grouped[alg][n]]) for n in ns]
        ax.plot(ns, on_track, marker=marker, linewidth=2.4, markersize=7, color=color, label=label)
    ax.set_xlabel("Number of vehicles")
    ax.set_ylabel("On-track overtake rate")
    ax.set_ylim(-0.05, 1.05)
    ax.set_xticks([4, 6, 8, 10, 12])
    ax.set_title("Quality under density", fontweight="normal")
    ax.legend(frameon=False)
    panel_label(ax, "c")

    failures = read_csv(failure_csv)
    counts = Counter()
    for row in failures:
        if row.get("algorithm") != "v6_runtime_dynamic_neighborhood_safe":
            continue
        for mode in (row.get("active_failure_modes") or "").split(";"):
            if mode:
                counts[mode] += 1
    order = ["off_track_overtake", "non_elegant_overtake", "high_grass_exposure", "long_overtake_window", "no_overtake", "lap_not_completed", "high_latency"]
    names = {"off_track_overtake": "Off-track pass", "non_elegant_overtake": "Non-elegant pass", "high_grass_exposure": "High grass exposure", "long_overtake_window": "Long overtake window", "no_overtake": "No overtake", "lap_not_completed": "Lap incomplete", "high_latency": "High latency"}
    ax = axes[1, 1]
    keys = [key for key in order if counts.get(key, 0)]
    vals = [counts[key] for key in keys]
    ax.barh(np.arange(len(keys)), vals, color=COLORS["accent"], alpha=0.88)
    ax.set_yticks(np.arange(len(keys)))
    ax.set_yticklabels([names[key] for key in keys])
    ax.set_xlabel("Number of retained case-level flags")
    ax.set_title("Failure-mode boundary", fontweight="normal")
    panel_label(ax, "d")

    fig.suptitle("Dynamic-neighborhood world-model overtaking: attribution, scale and failure boundaries", fontsize=15, fontweight="normal")
    outputs = save_publication(fig, out_stem)
    plt.close(fig)
    return outputs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ablation-report", required=True)
    parser.add_argument("--scale-source", required=True)
    parser.add_argument("--failure-source", required=True)
    parser.add_argument("--out-stem", required=True)
    args = parser.parse_args()
    outputs = build_figure(args.ablation_report, args.scale_source, args.failure_source, args.out_stem)
    print(json.dumps(outputs, indent=2))


if __name__ == "__main__":
    main()
