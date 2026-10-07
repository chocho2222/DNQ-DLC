#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Headline results figure built from the graded-endpoint audit tables.

Panels
  (a) E_pass / E_valid / E_full with Wilson intervals, per method
  (b) corridor profile: E_pass and at least w of the manoeuvre inside the edge
  (c) safety-guard ablation (guard filter versus guard-free versus the rule baseline)
  (d) case-level endpoint matrix, so a single lucky case cannot carry the claim
"""
import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.tits_figure_style import (
    color_for_algorithm,
    configure_publication_matplotlib,
    label_for_algorithm,
    linestyle_for_algorithm,
    marker_for_algorithm,
)

ENDPOINTS = ["E_pass", "E_valid", "E_full"]
DEFAULT_PAPER_METHODS = [
    "rule_expert_gate",
    "rule_safety_gate",
    "ppo_continuous",
    "sac_continuous",
    "td3_continuous",
    "dlc_individual_transition",
    "dlc_joint_transition",
    "dlc_joint_transition_observer",
    "ours_corrected_v2_guard_filter",
    "ours_corrected_v2_guard_free",
]


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def load_tables(audit_dir):
    audit = Path(audit_dir)
    aggregate = defaultdict(dict)
    for row in read_csv(audit / "aggregate.csv"):
        aggregate[row["algorithm"]][row["endpoint"]] = row
    profile = defaultdict(dict)
    for row in read_csv(audit / "profile.csv"):
        profile[row["algorithm"]].setdefault(row["window"], {})[to_float(row["in_corridor_min"])] = row
    cases = defaultdict(lambda: defaultdict(bool))
    for row in read_csv(audit / "case_level.csv"):
        cases[row["algorithm"]][f"{row['case_dir']}|{row['num_agents']}|{row['seed']}"] = row["E_full"] == "True"
    return aggregate, profile, cases


def style_axis(axis):
    axis.tick_params(direction="out", length=3.5, width=1.0, labelsize=7.5)
    for spine in ("left", "bottom"):
        axis.spines[spine].set_linewidth(1.0)
    axis.set_axisbelow(True)
    axis.grid(axis="y", color="#E8E8E8", lw=0.6)


def panel_endpoints(axis, methods, aggregate):
    width = 0.24
    for index, endpoint in enumerate(ENDPOINTS):
        for slot, method in enumerate(methods):
            row = aggregate[method].get(endpoint)
            if not row:
                continue
            rate = 100.0 * to_float(row["rate"])
            low = 100.0 * to_float(row["wilson_low"])
            high = 100.0 * to_float(row["wilson_high"])
            position = slot + (index - 1) * width
            color = color_for_algorithm(method)
            axis.bar(position, rate, width=width, color=color,
                     edgecolor="black" if index == 2 else "white",
                     lw=0.8 if index == 2 else 0.5,
                     alpha=[0.45, 0.7, 1.0][index], zorder=3)
            axis.errorbar(position, rate, yerr=[[max(rate - low, 0.0)], [max(high - rate, 0.0)]],
                          fmt="none", ecolor="#333333", elinewidth=0.7, capsize=1.8, zorder=4)
    axis.set_xticks(range(len(methods)))
    axis.set_xticklabels([label_for_algorithm(method) for method in methods], rotation=18, ha="right", fontsize=7.5)
    axis.set_ylabel("cases (%)", fontsize=8)
    axis.set_title("(a) graded endpoints, Wilson 95% interval", fontsize=8.5, loc="left")
    handles = [plt_patch(color="black", alpha=alpha, label=name) for name, alpha in
               zip(ENDPOINTS, [0.45, 0.7, 1.0])]
    axis.legend(handles=handles, fontsize=7, loc="upper right", handlelength=1.2)
    style_axis(axis)


def plt_patch(color, alpha, label):
    from matplotlib.patches import Patch
    return Patch(facecolor=color, alpha=alpha, label=label, edgecolor="white")


def panel_profile(axis, methods, profile):
    for method in methods:
        table = profile.get(method, {}).get("man", {})
        if not table:
            continue
        keys = sorted(table)
        rates = [100.0 * to_float(table[key]["rate"]) for key in keys]
        axis.plot([100.0 * key for key in keys], rates, color=color_for_algorithm(method),
                  ls=linestyle_for_algorithm(method), lw=1.4,
                  marker=marker_for_algorithm(method) or "o", ms=4.0, mfc="white", mew=0.9,
                  label=label_for_algorithm(method))
    axis.set_xlabel("required in-corridor fraction of the manoeuvre (%)", fontsize=7.5)
    axis.set_ylabel("E_pass cases (%)", fontsize=8)
    axis.set_title("(b) corridor profile", fontsize=8.5, loc="left")
    axis.legend(fontsize=6.5, loc="upper right", handlelength=1.6)
    style_axis(axis)


def panel_guard(axis, methods, aggregate):
    rows, labels, colors = [], [], []
    for method in methods:
        row = aggregate[method].get("E_full")
        if not row:
            continue
        rows.append((100.0 * to_float(row["rate"]), to_float(row["wilson_low"]) * 100.0,
                     to_float(row["wilson_high"]) * 100.0))
        labels.append(label_for_algorithm(method))
        colors.append(color_for_algorithm(method))
    positions = range(len(rows))
    for position, (rate, low, high) in zip(positions, rows):
        axis.bar(position, rate, width=0.55, color=colors[position], zorder=3)
        axis.errorbar(position, rate, yerr=[[max(rate - low, 0.0)], [max(high - rate, 0.0)]],
                      fmt="none", ecolor="#333333", elinewidth=0.7, capsize=1.8, zorder=4)
        axis.annotate(f"{rate:.0f}%", (position, rate), textcoords="offset points", xytext=(0, 3),
                      ha="center", fontsize=7)
    axis.set_xticks(list(positions))
    axis.set_xticklabels(labels, rotation=18, ha="right", fontsize=7.5)
    axis.set_ylabel("E_full (%)", fontsize=8)
    axis.set_title("(c) safety-guard ablation", fontsize=8.5, loc="left")
    style_axis(axis)


def panel_cases(axis, methods, cases):
    key_sets = [sorted(cases[method]) for method in methods if cases[method]]
    keys = sorted(set().union(*key_sets)) if key_sets else []
    for row_index, method in enumerate(methods):
        for column_index, key in enumerate(keys):
            passed = cases[method].get(key)
            axis.plot(column_index, row_index, marker="o" if passed else "x", ms=6 if passed else 5,
                      mfc=color_for_algorithm(method) if passed else "white",
                      mec=color_for_algorithm(method) if passed else "#BBBBBB",
                      mew=1.0 if passed else 0.8, ls="none", zorder=3)
    axis.set_yticks(range(len(methods)))
    axis.set_yticklabels([label_for_algorithm(method) for method in methods], fontsize=7.5)
    short = [key.split("|")[0].rstrip("/").split("/")[-1] for key in keys]
    axis.set_xticks(range(len(keys)))
    axis.set_xticklabels(short, rotation=30, ha="right", fontsize=6.8)
    axis.set_ylim(len(methods) - 0.5, -0.5)
    axis.grid(axis="y", color="#E8E8E8", lw=0.6)
    axis.grid(axis="x", color="#F2F2F2", lw=0.6)
    axis.set_title("(d) case-level E_full (filled = passed)", fontsize=8.5, loc="left")
    axis.tick_params(direction="out", length=3.5, width=1.0)


def build(audit_dir, out_path, methods=None):
    aggregate, profile, cases = load_tables(audit_dir)
    if methods is None:
        curated = [name for name in DEFAULT_PAPER_METHODS if name in aggregate]
        methods = curated if len(curated) >= 2 else sorted(aggregate)
    methods = [name for name in methods if name in aggregate]
    configure_publication_matplotlib(font_size=8.0)
    import matplotlib.pyplot as plt

    figure = plt.figure(figsize=(7.16, 5.0))
    grid = figure.add_gridspec(2, 2, hspace=0.95, wspace=0.45)
    panel_endpoints(figure.add_subplot(grid[0, 0]), methods, aggregate)
    panel_profile(figure.add_subplot(grid[0, 1]), methods, profile)
    panel_guard(figure.add_subplot(grid[1, 0]), methods, aggregate)
    panel_cases(figure.add_subplot(grid[1, 1]), methods, cases)
    experiment = next(iter(aggregate[methods[0]]["E_pass"].get("experiment_id", "experiment")), None) \
        if isinstance(aggregate[methods[0]]["E_pass"], dict) else None
    source = json.loads((Path(audit_dir) / "protocol.json").read_text(encoding="utf-8"))
    experiment = aggregate[methods[0]]["E_pass"]["experiment_id"]
    figure.suptitle(f"{experiment}: corrected protocol, event endpoints",
                    fontsize=8.0, y=0.995)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(out, bbox_inches="tight", dpi=400)
    figure.savefig(out.with_suffix(".png"), bbox_inches="tight", dpi=400)
    plt.close(figure)
    print(f"wrote {out} and {out.with_suffix('.png')}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit-dir", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--methods", default="")
    args = parser.parse_args()
    methods = [item.strip() for item in args.methods.split(",") if item.strip()] or None
    build(args.audit_dir, args.out, methods)


if __name__ == "__main__":
    main()
