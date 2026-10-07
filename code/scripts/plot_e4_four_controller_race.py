#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Plot Experiment 4 four-controller same-track race analysis."""

import argparse
import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch

try:
    from tits_figure_style import (
        color_for_algorithm,
        configure_publication_matplotlib,
        label_for_algorithm,
    )
except ImportError:
    from scripts.tits_figure_style import (
        color_for_algorithm,
        configure_publication_matplotlib,
        label_for_algorithm,
    )


ALGORITHMS = [
    "rule_expert_gate",
    "td3_continuous",
    "dlc_joint_transition_observer",
    "v6_runtime_dynamic_neighborhood_safe",
]

LABELS = {
    "rule_expert_gate": "Rule expert",
    "td3_continuous": "TD3",
    "dlc_joint_transition_observer": "DLC-JTO",
    "v6_runtime_dynamic_neighborhood_safe": "DNQ-DLC",
}

CASE_LABELS = {
    "final_case_01_oval_dense_s4": "Dense",
    "final_case_02_oval_nominal_s5": "Nominal",
    "final_case_03_oval_wide_s8": "Wide",
}


def read_cases(root):
    root = Path(root)
    summaries = sorted(root.glob("final_case_*/summaries/*.summary.json"))
    rows = []
    ours_rows = []
    for summary_path in summaries:
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        case_key = summary_path.parents[1].name
        case_label = CASE_LABELS.get(case_key, case_key.replace("_", " "))
        assignment = summary["assignment"]
        track_tiles = float(summary["track_tiles"])
        initial_rank = {idx: idx + 1 for idx in range(len(assignment))}
        for agent_id, algorithm in enumerate(assignment):
            row = {
                "case": case_label,
                "case_key": case_key,
                "seed": int(summary["seed"]),
                "line_spacing": "",
                "agent_id": agent_id,
                "algorithm": algorithm,
                "algorithm_label": LABELS.get(algorithm, label_for_algorithm(algorithm)),
                "progress": float(summary["tile_visited_count"][agent_id]) / track_tiles,
                "off_track_rate": float(summary["grass_rate"][agent_id]),
                "backward_rate": float(summary["backward_rate"][agent_id]),
                "final_rank": int(summary["final_rank"][agent_id]),
                "initial_rank": int(initial_rank[agent_id]),
                "rank_gain": int(initial_rank[agent_id]) - int(summary["final_rank"][agent_id]),
                "total_reward": float(summary["total_reward"][agent_id]),
                "background_vehicles": int(summary.get("background_vehicles", 0)),
                "competition_mode": summary.get("competition_mode", ""),
                "summary_path": str(summary_path),
            }
            rows.append(row)
        ours_rows.append(
            {
                "case": case_label,
                "case_key": case_key,
                "seed": int(summary["seed"]),
                "target_progress": float(summary["target_progress"]),
                "target_off_track_rate": float(summary["target_grass_rate"]),
                "rank_gain": int(summary["rank_gain"]),
                "overtake_count": int(summary["overtake_count"]),
                "on_track_overtake_count": int(summary["on_track_overtake_count"]),
                "elegant_overtake_count": int(summary["elegant_overtake_count"]),
                "min_pair_distance": float(summary["min_pair_distance"]),
                "latency_mean_ms": float(summary["compute_latency_ms"]),
                "latency_p95_ms": float(summary["compute_latency_p95_ms"]),
                "background_vehicles": int(summary.get("background_vehicles", 0)),
                "competition_mode": summary.get("competition_mode", ""),
            }
        )
    case_order = [CASE_LABELS.get(p.parents[1].name, p.parents[1].name) for p in summaries]
    return rows, ours_rows, case_order


def write_csv(rows, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return str(path)


def grouped_bars(ax, rows, case_order, metric, title, ylabel, ylim=None, zero_line=False):
    x = np.arange(len(case_order), dtype=float)
    width = 0.18
    offsets = (np.arange(len(ALGORITHMS)) - (len(ALGORITHMS) - 1) / 2.0) * width
    lookup = {(row["case"], row["algorithm"]): row for row in rows}
    for idx, algorithm in enumerate(ALGORITHMS):
        vals = [lookup[(case, algorithm)][metric] for case in case_order]
        alpha = 0.96 if algorithm == "v6_runtime_dynamic_neighborhood_safe" else 0.82
        edge = "#111827" if algorithm == "v6_runtime_dynamic_neighborhood_safe" else "#4B5563"
        lw = 0.9 if algorithm == "v6_runtime_dynamic_neighborhood_safe" else 0.45
        ax.bar(
            x + offsets[idx],
            vals,
            width=width * 0.92,
            color=color_for_algorithm(algorithm),
            edgecolor=edge,
            linewidth=lw,
            alpha=alpha,
            zorder=3,
        )
    if zero_line:
        ax.axhline(0, color="#111827", lw=0.65, zorder=2)
    ax.set_title(title, loc="left", fontsize=8.1, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(case_order)
    ax.set_ylabel(ylabel)
    if ylim is not None:
        ax.set_ylim(*ylim)
    ax.grid(axis="y", color="#E5E7EB", lw=0.55)
    ax.set_axisbelow(True)


def ours_panel(ax, ours_rows, case_order):
    x = np.arange(len(case_order), dtype=float)
    lookup = {row["case"]: row for row in ours_rows}
    on_track = [lookup[case]["on_track_overtake_count"] for case in case_order]
    elegant = [lookup[case]["elegant_overtake_count"] for case in case_order]
    latency = [lookup[case]["latency_p95_ms"] for case in case_order]
    bars = ax.bar(
        x - 0.10,
        on_track,
        width=0.20,
        color="#235A9F",
        edgecolor="#111827",
        linewidth=0.65,
        label="On-track overtakes",
        zorder=3,
    )
    ax.bar(
        x + 0.10,
        elegant,
        width=0.20,
        color="#78A8D8",
        edgecolor="#111827",
        linewidth=0.55,
        label="Elegant overtakes",
        zorder=3,
    )
    for bar, value in zip(bars, on_track):
        ax.text(bar.get_x() + bar.get_width() / 2.0, value + 0.06, str(value), ha="center", va="bottom", fontsize=6.4)
    ax.set_title("d  DNQ-DLC overtaking evidence", loc="left", fontsize=8.1, fontweight="bold")
    ax.set_ylabel("Count")
    ax.set_xticks(x)
    ax.set_xticklabels(case_order)
    ax.set_ylim(0, max(on_track + elegant) + 0.8)
    ax.grid(axis="y", color="#E5E7EB", lw=0.55)
    ax.set_axisbelow(True)
    ax2 = ax.twinx()
    ax2.plot(x, latency, color="#111827", marker="o", ms=3.2, lw=1.0, label="P95 latency", zorder=4)
    ax2.set_ylabel("P95 latency (ms)")
    ax2.set_ylim(0, max(latency) * 1.35)
    ax2.spines["top"].set_visible(False)
    handles1, labels1 = ax.get_legend_handles_labels()
    handles2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(handles1 + handles2, labels1 + labels2, loc="upper left", fontsize=5.8, handlelength=1.0)


def main():
    parser = argparse.ArgumentParser(description="Plot E4 four-controller same-track race analysis.")
    parser.add_argument(
        "--root",
        default="outputs/tits_dynamic_graph_expanded/e4_four_controller_race_no_background",
    )
    parser.add_argument(
        "--out-dir",
        default="outputs/tits_dynamic_graph_expanded/e4_four_controller_race_no_background/data_analysis_figure",
    )
    args = parser.parse_args()

    configure_publication_matplotlib(font_size=7.0)
    out_dir = Path(args.out_dir)
    fig_dir = out_dir / "figures"
    table_dir = out_dir / "tables"
    fig_dir.mkdir(parents=True, exist_ok=True)
    table_dir.mkdir(parents=True, exist_ok=True)

    rows, ours_rows, case_order = read_cases(args.root)
    write_csv(rows, table_dir / "e4_four_controller_agent_metrics.csv")
    write_csv(ours_rows, table_dir / "e4_dnq_dlc_target_metrics.csv")

    fig = plt.figure(figsize=(7.55, 4.25))
    gs = fig.add_gridspec(2, 2, hspace=0.46, wspace=0.34)
    ax_a = fig.add_subplot(gs[0, 0])
    ax_b = fig.add_subplot(gs[0, 1])
    ax_c = fig.add_subplot(gs[1, 0])
    ax_d = fig.add_subplot(gs[1, 1])

    grouped_bars(
        ax_a,
        rows,
        case_order,
        "rank_gain",
        "a  Same-track race: rank gain",
        "Initial rank - final rank",
        ylim=(-3.4, 3.6),
        zero_line=True,
    )
    grouped_bars(
        ax_b,
        rows,
        case_order,
        "progress",
        "b  Forward progress within the race",
        "Track progress fraction",
        ylim=(0, 1.05),
    )
    grouped_bars(
        ax_c,
        rows,
        case_order,
        "off_track_rate",
        "c  Off-track exposure",
        "Off-track rate",
        ylim=(0, 1.0),
    )
    ours_panel(ax_d, ours_rows, case_order)

    handles = [
        Patch(facecolor=color_for_algorithm(algorithm), edgecolor="#374151", label=LABELS[algorithm])
        for algorithm in ALGORITHMS
    ]
    fig.legend(
        handles=handles,
        ncol=4,
        loc="upper center",
        bbox_to_anchor=(0.52, 1.005),
        columnspacing=1.1,
        handlelength=1.0,
        handletextpad=0.35,
        fontsize=6.3,
    )
    fig.subplots_adjust(left=0.075, right=0.965, top=0.88, bottom=0.135)

    stem = fig_dir / "figure_e4_four_controller_same_track_race_analysis"
    outputs = {}
    for ext in ["svg", "pdf", "png", "tiff"]:
        path = stem.with_suffix(f".{ext}")
        fig.savefig(path, dpi=600, bbox_inches="tight")
        outputs[ext] = str(path)
    plt.close(fig)

    caption = (
        "Experiment 4 four-controller same-track race analysis. Each case contains exactly four vehicles and no background traffic: "
        "the strongest rule-based baseline, the strongest RL baseline (TD3), DLC-JTO, and DNQ-DLC. "
        "Panels a--c report agent-level metrics from the same online race traces. DNQ-DLC starts fourth in all cases and achieves positive rank gain while maintaining low off-track exposure. "
        "Panel d reports DNQ-DLC's on-track/elegant overtaking events and P95 online decision latency for the same cases."
    )
    caption_path = out_dir / "figure_e4_caption.tex"
    caption_path.write_text(caption + "\n", encoding="utf-8")
    manifest = {
        "figure": outputs,
        "agent_metrics_csv": str(table_dir / "e4_four_controller_agent_metrics.csv"),
        "dnq_dlc_target_metrics_csv": str(table_dir / "e4_dnq_dlc_target_metrics.csv"),
        "caption": str(caption_path),
        "case_order": case_order,
        "background_vehicles": 0,
        "algorithms": ALGORITHMS,
    }
    manifest_path = out_dir / "e4_four_controller_figure_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
