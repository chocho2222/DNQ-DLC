#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path

import numpy as np

import matplotlib as mpl
import matplotlib.pyplot as plt


mpl.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "font.size": 7,
        "axes.spines.right": False,
        "axes.spines.top": False,
        "axes.linewidth": 0.8,
        "legend.frameon": False,
        "xtick.major.width": 0.7,
        "ytick.major.width": 0.7,
    }
)


PALETTE = {
    "baseline": "#7A869A",
    "graph": "#3B7EA1",
    "shield": "#4C9F70",
    "fail": "#C44E52",
    "text": "#1F2933",
    "grid": "#D8DEE6",
}


def load_json(path):
    path = Path(path)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def wilson_ci(k, n, z=1.96):
    if n <= 0:
        return 0.0, 0.0
    phat = k / n
    denom = 1.0 + z * z / n
    centre = (phat + z * z / (2 * n)) / denom
    half = z * np.sqrt((phat * (1 - phat) + z * z / (4 * n)) / n) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def collect_main_rows(root):
    suite = load_json(root / "evaluations" / "multiseed_suite" / "multiseed_suite_summary.json")
    if suite:
        rows = []
        for item in suite.get("rows", []):
            rows.append(
                {
                    "method": item["method"],
                    "family": "innovation" if item["method"].startswith("graph") else "control_ablation",
                    "seed": item["seed"],
                    "status": item["validation_status"],
                    "target_progress": item["target_tile_progress"],
                    "target_grass_rate": float(item["target_grass_rate"]),
                    "max_grass_rate": float(item["max_grass_rate"]),
                    "rank": int(item["target_final_rank_by_tiles"]),
                    "steps": int(item["steps_run"]),
                }
            )
        return rows
    table = load_json(root / "tables" / "main_results.json")
    rows = []
    if not table:
        return rows
    for item in table.get("baseline_rows", []):
        rows.append(
            {
                "method": item["name"],
                "family": "locked_baseline",
                "seed": item.get("seed", 3),
                "status": item["validation_status"],
                "target_progress": item["tile_visited_count"][-1] / max(item.get("track_tiles", 1), 1)
                if "track_tiles" in item
                else float(item["target_completed_lap"]),
                "target_grass_rate": float(item["target_grass_rate"]),
                "max_grass_rate": float(item["max_grass_rate"]),
                "rank": int(item["target_final_rank_by_tiles"]),
                "steps": int(item["steps_run"]),
            }
        )
    for item in table.get("graph_bc_rows", []):
        track_tiles = max(max(item["tile_visited_count"]), 1)
        rows.append(
            {
                "method": "graph_bc_safety_shield",
                "family": "innovation",
                "seed": item["seed"],
                "status": item["validation_status"],
                "target_progress": item["tile_visited_count"][-1] / track_tiles,
                "target_grass_rate": float(item["target_grass_rate"]),
                "max_grass_rate": float(item["max_grass_rate"]),
                "rank": int(item["target_final_rank_by_tiles"]),
                "steps": int(item["steps_run"]),
            }
        )
    return rows


def collect_ablation_rows(root):
    data = load_json(root / "ablations" / "ablation_summary.json")
    if not data:
        data = load_json(root / "tables" / "ablation_summary.json")
    if not data:
        return []
    rows = []
    for item in data.get("rows", []):
        track_tiles = max(max(item["tile_visited_count"]), 1)
        rows.append(
            {
                "method": item["ablation"],
                "seed": item["seed"],
                "status": item["validation_status"],
                "target_progress": item["tile_visited_count"][-1] / track_tiles,
                "target_grass_rate": float(item["target_grass_rate"]),
                "max_grass_rate": float(item["max_grass_rate"]),
                "rank": int(item["target_final_rank_by_tiles"]),
                "steps": int(item["steps_run"]),
            }
        )
    return rows


def write_source_data(rows, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def save_pub(fig, out_stem):
    fig.savefig(f"{out_stem}.svg", bbox_inches="tight")
    fig.savefig(f"{out_stem}.pdf", bbox_inches="tight")
    fig.savefig(f"{out_stem}.tiff", dpi=600, bbox_inches="tight")
    fig.savefig(f"{out_stem}.png", dpi=300, bbox_inches="tight")


def plot_main_figure(root, out_dir):
    main_rows = collect_main_rows(root)
    ablation_rows = collect_ablation_rows(root)
    source_rows = []
    for row in main_rows:
        source_rows.append({"panel": "a-c", **row})
    for row in ablation_rows:
        source_rows.append({"panel": "d", **row})
    write_source_data(source_rows, out_dir / "figure_1_source_data.csv")

    graph_rows = [row for row in main_rows if row["method"] in {"graph_bc_safety_shield", "graph_soft_shield"}]
    baseline_rows = [row for row in main_rows if row["family"] == "locked_baseline"]
    if not baseline_rows:
        baseline_rows = [row for row in main_rows if row["method"] in {"lane_base_only", "overtake_base_only"}]

    fig = plt.figure(figsize=(7.2, 4.6), constrained_layout=True)
    gs = fig.add_gridspec(2, 3, width_ratios=[1.0, 1.0, 1.25])
    ax_a = fig.add_subplot(gs[0, 0])
    ax_b = fig.add_subplot(gs[0, 1])
    ax_c = fig.add_subplot(gs[0, 2])
    ax_d = fig.add_subplot(gs[1, :])

    methods = ["rule baselines", "graph+soft shield"]
    pass_counts = [
        sum(row["status"] == "PASS" for row in baseline_rows),
        sum(row["status"] == "PASS" for row in graph_rows),
    ]
    totals = [len(baseline_rows), len(graph_rows)]
    rates = [pass_counts[i] / totals[i] if totals[i] else 0.0 for i in range(2)]
    cis = [wilson_ci(pass_counts[i], totals[i]) for i in range(2)]
    yerr = np.asarray([[rates[i] - cis[i][0] for i in range(2)], [cis[i][1] - rates[i] for i in range(2)]])
    ax_a.bar(methods, rates, color=[PALETTE["baseline"], PALETTE["graph"]], width=0.62)
    ax_a.errorbar(methods, rates, yerr=yerr, fmt="none", ecolor=PALETTE["text"], lw=0.8, capsize=2)
    for i, (rate, k, n) in enumerate(zip(rates, pass_counts, totals)):
        ax_a.text(i, min(rate + 0.07, 1.02), f"{k}/{n}", ha="center", va="bottom", color=PALETTE["text"])
    ax_a.set_ylim(0, 1.08)
    ax_a.set_ylabel("strict pass rate")
    ax_a.set_title("a  Multi-seed success")
    ax_a.tick_params(axis="x", rotation=18)

    if graph_rows:
        seeds = [row["seed"] for row in graph_rows]
        progress = [row["target_progress"] for row in graph_rows]
        colors = [PALETTE["graph"] if row["status"] == "PASS" else PALETTE["fail"] for row in graph_rows]
        ax_b.bar([str(seed) for seed in seeds], progress, color=colors, width=0.65)
    ax_b.axhline(1.0, color=PALETTE["text"], lw=0.7, ls="--")
    ax_b.set_ylim(0, 1.08)
    ax_b.set_xlabel("seed")
    ax_b.set_ylabel("target lap progress")
    ax_b.set_title("b  Completion by seed")

    if graph_rows:
        x = np.arange(len(graph_rows))
        ax_c.scatter(
            [row["target_grass_rate"] for row in graph_rows],
            [row["rank"] for row in graph_rows],
            c=[PALETTE["graph"] if row["status"] == "PASS" else PALETTE["fail"] for row in graph_rows],
            s=34,
            edgecolor="white",
            linewidth=0.6,
        )
        for _, row in enumerate(graph_rows):
            ax_c.text(row["target_grass_rate"] + 0.002, row["rank"] + 0.02, str(row["seed"]), fontsize=6)
    ax_c.invert_yaxis()
    ax_c.set_xlabel("target grass rate")
    ax_c.set_ylabel("final rank")
    ax_c.set_title("c  Failure mode map")
    ax_c.grid(axis="x", color=PALETTE["grid"], lw=0.5)

    if ablation_rows:
        grouped = {}
        for row in ablation_rows:
            grouped.setdefault(row["method"], []).append(row)
        names = list(grouped)
        pass_rate = [sum(r["status"] == "PASS" for r in grouped[name]) / len(grouped[name]) for name in names]
        mean_progress = [np.mean([r["target_progress"] for r in grouped[name]]) for name in names]
        x = np.arange(len(names))
        ax_d.bar(x - 0.18, pass_rate, width=0.36, color=PALETTE["shield"], label="pass rate")
        ax_d.bar(x + 0.18, mean_progress, width=0.36, color=PALETTE["graph"], label="mean target progress")
        ax_d.set_xticks(x, names, rotation=22, ha="right")
        ax_d.legend(ncols=2, loc="upper right")
    ax_d.set_ylim(0, 1.08)
    ax_d.set_ylabel("fraction")
    ax_d.set_title("d  Safety and controller ablations")

    for ax in [ax_a, ax_b, ax_c, ax_d]:
        ax.tick_params(length=3, width=0.7)

    out_stem = out_dir / "figure_1_multicar_overtake_results"
    save_pub(fig, out_stem)
    plt.close(fig)

    manifest = {
        "figure": "figure_1_multicar_overtake_results",
        "claim": "The current innovation package demonstrates strict multi-car full-lap overtaking in selected seeds, but robustness is limited and safety constraints explain a large share of the observed performance.",
        "archetype": "quantitative grid",
        "panels": {
            "a": "Pass rate with Wilson confidence intervals for locked baselines and graph+shield evaluations.",
            "b": "Per-seed target lap completion for graph+shield.",
            "c": "Failure mode map using target grass rate and final rank.",
            "d": "Ablation comparison of learned actor, fallback controllers, and safety shields.",
        },
        "source_data": str(out_dir / "figure_1_source_data.csv"),
        "exports": [str(out_stem) + ext for ext in [".svg", ".pdf", ".tiff", ".png"]],
        "review_risks": [
            "Current graph+shield evaluation has only three seeds; confidence intervals are wide.",
            "Locked baseline rows are not yet matched to the same multi-seed protocol as graph+shield.",
            "Ablation rows are currently dominated by the seed-7 hard case unless a larger sweep is run.",
        ],
    }
    (out_dir / "figure_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main():
    parser = argparse.ArgumentParser(description="Export manuscript-style figures for the multi-car overtaking package.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    out_dir = root / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = plot_main_figure(root, out_dir)
    print(json.dumps({"status": "PASS", "manifest": manifest}, indent=2))


if __name__ == "__main__":
    main()
