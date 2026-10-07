#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np


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
    "adaptive": "#3B7EA1",
    "shield": "#4C9F70",
    "oracle": "#E0A458",
    "fail": "#C44E52",
    "pass": "#4C9F70",
    "text": "#1F2933",
    "grid": "#D8DEE6",
}


SHORT_LABELS = {
    "main:overtake_base_only": "Overtake",
    "adaptive:graph_adaptive_shield": "Graph+adaptive",
    "adaptive:adaptive_gate_only": "Adaptive",
    "main:lane_base_only": "Lane",
    "recovery:graph_recovery_adaptive_shield": "Recovery",
    "main:graph_soft_shield": "Graph+soft",
    "geometry_loso": "Geometry\nLOSO",
    "online_probe": "450-step\nprobe",
    "online_probe_1200": "1200\nlocked",
    "online_probe_1200_heldout": "1200\nheld-out",
    "online_probe_1200_heldout_expert": "1200\nheld-out+\nexpert",
    "online_probe_1200_heldout_dagger_v2": "1200\nheld-out+\nDAgger",
    "online_probe_1200_heldout2_dagger_v2": "1200\nheld-out2+\nDAgger",
    "calibrated_heldout2": "Calibrated\nheld-out2",
    "oracle": "Oracle\nlocked",
    "oracle_heldout": "Oracle\nheld-out",
    "oracle_heldout_expert": "Oracle\nheld-out+\nexpert",
    "oracle_heldout_dagger_v2": "Oracle\nheld-out+\nDAgger",
    "oracle_heldout2_dagger_v2": "Oracle\nheld-out2+\nDAgger",
}


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def wilson_ci(k, n, z=1.96):
    if n <= 0:
        return 0.0, 0.0
    phat = k / n
    denom = 1.0 + z * z / n
    centre = (phat + z * z / (2 * n)) / denom
    half = z * np.sqrt((phat * (1 - phat) + z * z / (4 * n)) / n) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def save_pub(fig, out_stem):
    fig.savefig(f"{out_stem}.svg", bbox_inches="tight")
    fig.savefig(f"{out_stem}.pdf", bbox_inches="tight")
    fig.savefig(f"{out_stem}.tiff", dpi=600, bbox_inches="tight")
    fig.savefig(f"{out_stem}.png", dpi=300, bbox_inches="tight")


def load_sources(root):
    stats = load_json(root / "tables" / "full_statistical_report.json")
    oracle = load_json(root / "tables" / "portfolio_oracle.json")
    loso = load_json(root / "tables" / "portfolio_selector_loso.json")
    probe = load_json(root / "tables" / "portfolio_probe_selector.json")
    probe_1200_path = root / "tables" / "portfolio_probe_selector_1200.json"
    probe_1200 = load_json(probe_1200_path) if probe_1200_path.exists() else None
    probe_1200_heldout_path = root / "tables" / "portfolio_probe_selector_1200_heldout.json"
    probe_1200_heldout = load_json(probe_1200_heldout_path) if probe_1200_heldout_path.exists() else None
    probe_1200_heldout_expert_path = root / "tables" / "portfolio_probe_selector_1200_heldout_expert.json"
    probe_1200_heldout_expert = load_json(probe_1200_heldout_expert_path) if probe_1200_heldout_expert_path.exists() else None
    probe_1200_heldout_dagger_v2_path = root / "tables" / "portfolio_probe_selector_1200_heldout_dagger_v2.json"
    probe_1200_heldout_dagger_v2 = load_json(probe_1200_heldout_dagger_v2_path) if probe_1200_heldout_dagger_v2_path.exists() else None
    probe_1200_heldout2_dagger_v2_path = root / "tables" / "portfolio_probe_selector_1200_heldout2_dagger_v2.json"
    probe_1200_heldout2_dagger_v2 = load_json(probe_1200_heldout2_dagger_v2_path) if probe_1200_heldout2_dagger_v2_path.exists() else None
    selector_calibration_path = root / "tables" / "selector_calibration.json"
    selector_calibration = load_json(selector_calibration_path) if selector_calibration_path.exists() else None
    heldout_generalization_path = root / "tables" / "heldout_generalization.json"
    heldout_generalization = load_json(heldout_generalization_path) if heldout_generalization_path.exists() else None
    negative_controls = []
    for name in [
        "heldout_expert_fast_smoke",
        "heldout_expert_barrier_smoke",
        "heldout_expert_recovery_smoke",
    ]:
        path = root / "tables" / f"{name}_report.json"
        if path.exists():
            negative_controls.append({"name": name, "report": load_json(path)})
    return (
        stats,
        oracle,
        loso,
        probe,
        probe_1200,
        probe_1200_heldout,
        probe_1200_heldout_expert,
        probe_1200_heldout_dagger_v2,
        probe_1200_heldout2_dagger_v2,
        selector_calibration,
        heldout_generalization,
        negative_controls,
    )


def make_source_rows(
    stats,
    oracle,
    loso,
    probe,
    probe_1200,
    probe_1200_heldout,
    probe_1200_heldout_expert,
    probe_1200_heldout_dagger_v2,
    probe_1200_heldout2_dagger_v2,
    selector_calibration,
    heldout_generalization,
    negative_controls,
):
    rows = []
    for item in stats["method_summaries"]:
        rows.append(
            {
                "panel": "a",
                "kind": "single_method",
                "label": item["method"],
                "pass_count": item["pass_count"],
                "n": item["n"],
                "pass_rate": item["pass_rate"],
                "ci_low": item["pass_rate_wilson_ci95"][0],
                "ci_high": item["pass_rate_wilson_ci95"][1],
            }
        )
    rows.append(
        {
            "panel": "b",
            "kind": "oracle",
            "label": "oracle_top1",
            "pass_count": oracle["oracle"]["pass_count"],
            "n": oracle["oracle"]["n"],
            "pass_rate": oracle["oracle"]["pass_rate"],
            "ci_low": None,
            "ci_high": None,
        }
    )
    for size, portfolios in oracle["best_portfolios"].items():
        best = portfolios[0] if portfolios else None
        if best:
            rows.append(
                {
                    "panel": "b",
                    "kind": "oracle",
                    "label": f"best_{size}",
                    "pass_count": best["pass_count"],
                    "n": best["n"],
                    "pass_rate": best["pass_rate"],
                    "ci_low": None,
                    "ci_high": None,
                }
            )
    rows.append(
        {
            "panel": "c",
            "kind": "selector",
            "label": "geometry_loso",
            "pass_count": loso["pass_count"],
            "n": loso["n"],
            "pass_rate": loso["pass_rate"],
            "ci_low": None,
            "ci_high": None,
        }
    )
    rows.append(
        {
            "panel": "c",
            "kind": "selector",
            "label": "online_probe",
            "pass_count": probe["pass_count"],
            "n": probe["n"],
            "pass_rate": probe["pass_rate"],
            "ci_low": None,
            "ci_high": None,
        }
    )
    if probe_1200:
        rows.append(
            {
                "panel": "c",
                "kind": "selector",
                "label": "online_probe_1200",
                "pass_count": probe_1200["pass_count"],
                "n": probe_1200["n"],
                "pass_rate": probe_1200["pass_rate"],
                "ci_low": None,
                "ci_high": None,
            }
        )
    if probe_1200_heldout:
        rows.append(
            {
                "panel": "c",
                "kind": "selector",
                "label": "online_probe_1200_heldout",
                "pass_count": probe_1200_heldout["pass_count"],
                "n": probe_1200_heldout["n"],
                "pass_rate": probe_1200_heldout["pass_rate"],
                "ci_low": None,
                "ci_high": None,
            }
        )
    if probe_1200_heldout_expert:
        rows.append(
            {
                "panel": "c",
                "kind": "selector",
                "label": "online_probe_1200_heldout_expert",
                "pass_count": probe_1200_heldout_expert["pass_count"],
                "n": probe_1200_heldout_expert["n"],
                "pass_rate": probe_1200_heldout_expert["pass_rate"],
                "ci_low": None,
                "ci_high": None,
            }
        )
    if probe_1200_heldout_dagger_v2:
        rows.append(
            {
                "panel": "c",
                "kind": "selector",
                "label": "online_probe_1200_heldout_dagger_v2",
                "pass_count": probe_1200_heldout_dagger_v2["pass_count"],
                "n": probe_1200_heldout_dagger_v2["n"],
                "pass_rate": probe_1200_heldout_dagger_v2["pass_rate"],
                "ci_low": None,
                "ci_high": None,
            }
        )
        rows.append(
            {
                "panel": "c",
                "kind": "selector",
                "label": "oracle_heldout_dagger_v2",
                "pass_count": probe_1200_heldout_dagger_v2["oracle_pass_count"],
                "n": probe_1200_heldout_dagger_v2["n"],
                "pass_rate": probe_1200_heldout_dagger_v2["oracle_pass_rate"],
                "ci_low": None,
                "ci_high": None,
            }
        )
    if probe_1200_heldout2_dagger_v2:
        rows.append(
            {
                "panel": "c",
                "kind": "selector",
                "label": "online_probe_1200_heldout2_dagger_v2",
                "pass_count": probe_1200_heldout2_dagger_v2["pass_count"],
                "n": probe_1200_heldout2_dagger_v2["n"],
                "pass_rate": probe_1200_heldout2_dagger_v2["pass_rate"],
                "ci_low": None,
                "ci_high": None,
            }
        )
        rows.append(
            {
                "panel": "c",
                "kind": "selector",
                "label": "oracle_heldout2_dagger_v2",
                "pass_count": probe_1200_heldout2_dagger_v2["oracle_pass_count"],
                "n": probe_1200_heldout2_dagger_v2["n"],
                "pass_rate": probe_1200_heldout2_dagger_v2["oracle_pass_rate"],
                "ci_low": None,
                "ci_high": None,
            }
        )
    if selector_calibration:
        calibrated = selector_calibration["test_heldout2"]
        rows.append(
            {
                "panel": "source_selector_calibration",
                "kind": "selector_calibration",
                "label": "calibrated_heldout2",
                "pass_count": calibrated["pass_count"],
                "n": calibrated["n"],
                "pass_rate": calibrated["pass_rate"],
                "oracle_pass_count": calibrated["oracle_pass_count"],
                "selector_miss_count": calibrated["selector_miss_count"],
                "candidate_gap_count": calibrated["candidate_gap_count"],
            }
        )
    if heldout_generalization:
        for set_name, item in heldout_generalization["sets"].items():
            selector = item["selector"]
            rows.append(
                {
                    "panel": "source_heldout_generalization",
                    "kind": "heldout_generalization",
                    "label": set_name,
                    "pass_count": selector["pass_count"],
                    "n": selector["n"],
                    "pass_rate": selector["pass_rate"],
                    "oracle_pass_count": selector["oracle_pass_count"],
                    "oracle_pass_rate": selector["oracle_pass_rate"],
                }
            )
        rows.append(
            {
                "panel": "c",
                "kind": "selector",
                "label": "oracle_heldout_expert",
                "pass_count": probe_1200_heldout_expert["oracle_pass_count"],
                "n": probe_1200_heldout_expert["n"],
                "pass_rate": probe_1200_heldout_expert["oracle_pass_rate"],
                "ci_low": None,
                "ci_high": None,
            }
        )
        rows.append(
            {
                "panel": "c",
                "kind": "selector",
                "label": "oracle_heldout",
                "pass_count": probe_1200_heldout["oracle_pass_count"],
                "n": probe_1200_heldout["n"],
                "pass_rate": probe_1200_heldout["oracle_pass_rate"],
                "ci_low": None,
                "ci_high": None,
            }
        )
    rows.append(
        {
            "panel": "c",
            "kind": "selector",
            "label": "oracle",
            "pass_count": oracle["oracle"]["pass_count"],
            "n": oracle["oracle"]["n"],
            "pass_rate": oracle["oracle"]["pass_rate"],
            "ci_low": None,
            "ci_high": None,
        }
    )
    heatmap_methods = [
        "main:overtake_base_only",
        "adaptive:graph_adaptive_shield",
        "main:lane_base_only",
    ]
    seeds = oracle["seeds"]
    by_seed = {}
    for item in stats["method_summaries"]:
        pass
    # rebuild from seed rows in stats report
    rows_by_method = {}
    for row in stats.get("seed_complementarity", []):
        by_seed[row["seed"]] = row
    for seed in seeds:
        row = by_seed[seed]
        for method in heatmap_methods:
            rows.append(
                {
                    "panel": "d",
                    "kind": "heatmap",
                    "label": method,
                    "seed": seed,
                    "value": int(method in row["passing_methods"]),
                }
            )
    for control in negative_controls:
        for method, summary in control["report"].get("method_summaries", {}).items():
            rows.append(
                {
                    "panel": "source_negative_controls",
                    "kind": "hard_heldout_negative_control",
                    "label": control["name"],
                    "method": method,
                    "pass_count": summary["pass_count"],
                    "n": summary["n"],
                    "pass_rate": summary["pass_rate"],
                    "target_grass_rate_mean": summary["target_grass_rate_mean"],
                    "target_tile_progress_mean": summary["target_tile_progress_mean"],
                    "target_rank_mean": summary["target_rank_mean"],
                }
            )
    return rows


def main():
    parser = argparse.ArgumentParser(description="Export a supplementary figure for the multi-car overtaking paper package.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    out_dir = root / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)

    (
        stats,
        oracle,
        loso,
        probe,
        probe_1200,
        probe_1200_heldout,
        probe_1200_heldout_expert,
        probe_1200_heldout_dagger_v2,
        probe_1200_heldout2_dagger_v2,
        selector_calibration,
        heldout_generalization,
        negative_controls,
    ) = load_sources(root)
    source_rows = make_source_rows(
        stats,
        oracle,
        loso,
        probe,
        probe_1200,
        probe_1200_heldout,
        probe_1200_heldout_expert,
        probe_1200_heldout_dagger_v2,
        probe_1200_heldout2_dagger_v2,
        selector_calibration,
        heldout_generalization,
        negative_controls,
    )

    with (out_dir / "figure_2_source_data.csv").open("w", newline="", encoding="utf-8") as handle:
        fieldnames = sorted({key for row in source_rows for key in row})
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(source_rows)

    fig = plt.figure(figsize=(8.2, 5.8), constrained_layout=True)
    gs = fig.add_gridspec(2, 2, height_ratios=[1.0, 0.95])
    ax_a = fig.add_subplot(gs[0, 0])
    ax_b = fig.add_subplot(gs[0, 1])
    ax_c = fig.add_subplot(gs[1, 0])
    ax_d = fig.add_subplot(gs[1, 1])

    method_order = [
        "main:overtake_base_only",
        "adaptive:graph_adaptive_shield",
        "adaptive:adaptive_gate_only",
        "main:lane_base_only",
        "recovery:graph_recovery_adaptive_shield",
        "main:graph_soft_shield",
    ]
    method_summary = {item["method"]: item for item in stats["method_summaries"]}
    x = np.arange(len(method_order))
    rates = [method_summary[m]["pass_rate"] for m in method_order]
    ci = [method_summary[m]["pass_rate_wilson_ci95"] for m in method_order]
    yerr = np.asarray([[rates[i] - ci[i][0] for i in range(len(ci))], [ci[i][1] - rates[i] for i in range(len(ci))]])
    colors = [PALETTE["shield"] if m == "main:overtake_base_only" else PALETTE["adaptive"] if "adaptive" in m else PALETTE["baseline"] for m in method_order]
    ax_a.bar(x, rates, color=colors, width=0.68)
    ax_a.errorbar(x, rates, yerr=yerr, fmt="none", ecolor=PALETTE["text"], lw=0.8, capsize=2)
    for i, m in enumerate(method_order):
        item = method_summary[m]
        ax_a.text(i, min(rates[i] + 0.05, 1.02), f"{item['pass_count']}/{item['n']}", ha="center", va="bottom")
    ax_a.set_xticks(x, [SHORT_LABELS.get(m, m.split(":")[-1]) for m in method_order], rotation=28, ha="right")
    ax_a.set_ylim(0, 1.08)
    ax_a.set_ylabel("strict pass rate")
    ax_a.set_title("a  Full-suite methods")

    oracle_sizes = [1, 2, 3]
    oracle_rates = []
    oracle_counts = []
    oracle_totals = []
    for size in oracle_sizes:
        if size == 1:
            best_single = max(stats["method_summaries"], key=lambda item: item["pass_rate"])
            oracle_rates.append(best_single["pass_rate"])
            oracle_counts.append(best_single["pass_count"])
            oracle_totals.append(best_single["n"])
        else:
            best = oracle["best_portfolios"][str(size)][0]
            oracle_rates.append(best["pass_rate"])
            oracle_counts.append(best["pass_count"])
            oracle_totals.append(best["n"])
    ax_b.bar([str(s) for s in oracle_sizes], oracle_rates, color=PALETTE["oracle"], width=0.6)
    for i, size in enumerate(oracle_sizes):
        ax_b.text(i, min(oracle_rates[i] + 0.05, 1.02), f"{oracle_counts[i]}/{oracle_totals[i]}", ha="center", va="bottom")
    ax_b.set_ylim(0, 1.08)
    ax_b.set_xlabel("portfolio size")
    ax_b.set_ylabel("oracle pass rate")
    ax_b.set_title("b  Oracle upper bound")

    selector_labels = ["geometry_loso", "online_probe"]
    selector_rates = [loso["pass_rate"], probe["pass_rate"]]
    selector_counts = [loso["pass_count"], probe["pass_count"]]
    selector_totals = [loso["n"], probe["n"]]
    selector_colors = [PALETTE["baseline"], PALETTE["adaptive"]]
    if probe_1200:
        selector_labels.append("online_probe_1200")
        selector_rates.append(probe_1200["pass_rate"])
        selector_counts.append(probe_1200["pass_count"])
        selector_totals.append(probe_1200["n"])
        selector_colors.append(PALETTE["shield"])
    if probe_1200_heldout:
        selector_labels.append("online_probe_1200_heldout")
        selector_rates.append(probe_1200_heldout["pass_rate"])
        selector_counts.append(probe_1200_heldout["pass_count"])
        selector_totals.append(probe_1200_heldout["n"])
        selector_colors.append("#6B8E23")
    if probe_1200_heldout_expert:
        selector_labels.append("online_probe_1200_heldout_expert")
        selector_rates.append(probe_1200_heldout_expert["pass_rate"])
        selector_counts.append(probe_1200_heldout_expert["pass_count"])
        selector_totals.append(probe_1200_heldout_expert["n"])
        selector_colors.append("#8F5B1C")
    if probe_1200_heldout_dagger_v2:
        selector_labels.append("online_probe_1200_heldout_dagger_v2")
        selector_rates.append(probe_1200_heldout_dagger_v2["pass_rate"])
        selector_counts.append(probe_1200_heldout_dagger_v2["pass_count"])
        selector_totals.append(probe_1200_heldout_dagger_v2["n"])
        selector_colors.append("#2F7F6F")
    if probe_1200_heldout2_dagger_v2:
        selector_labels.append("online_probe_1200_heldout2_dagger_v2")
        selector_rates.append(probe_1200_heldout2_dagger_v2["pass_rate"])
        selector_counts.append(probe_1200_heldout2_dagger_v2["pass_count"])
        selector_totals.append(probe_1200_heldout2_dagger_v2["n"])
        selector_colors.append(PALETTE["fail"])
    selector_labels.append("oracle")
    selector_rates.append(oracle["oracle"]["pass_rate"])
    selector_counts.append(oracle["oracle"]["pass_count"])
    selector_totals.append(oracle["oracle"]["n"])
    selector_colors.append(PALETTE["oracle"])
    if probe_1200_heldout:
        selector_labels.append("oracle_heldout")
        selector_rates.append(probe_1200_heldout["oracle_pass_rate"])
        selector_counts.append(probe_1200_heldout["oracle_pass_count"])
        selector_totals.append(probe_1200_heldout["n"])
        selector_colors.append("#C58B36")
    if probe_1200_heldout_expert:
        selector_labels.append("oracle_heldout_expert")
        selector_rates.append(probe_1200_heldout_expert["oracle_pass_rate"])
        selector_counts.append(probe_1200_heldout_expert["oracle_pass_count"])
        selector_totals.append(probe_1200_heldout_expert["n"])
        selector_colors.append("#B56A1E")
    if probe_1200_heldout_dagger_v2:
        selector_labels.append("oracle_heldout_dagger_v2")
        selector_rates.append(probe_1200_heldout_dagger_v2["oracle_pass_rate"])
        selector_counts.append(probe_1200_heldout_dagger_v2["oracle_pass_count"])
        selector_totals.append(probe_1200_heldout_dagger_v2["n"])
        selector_colors.append("#1F6E60")
    if probe_1200_heldout2_dagger_v2:
        selector_labels.append("oracle_heldout2_dagger_v2")
        selector_rates.append(probe_1200_heldout2_dagger_v2["oracle_pass_rate"])
        selector_counts.append(probe_1200_heldout2_dagger_v2["oracle_pass_count"])
        selector_totals.append(probe_1200_heldout2_dagger_v2["n"])
        selector_colors.append("#9B2F3A")
    ax_c.bar([SHORT_LABELS[label] for label in selector_labels], selector_rates, color=selector_colors, width=0.65)
    for i, rate in enumerate(selector_rates):
        ax_c.text(i, min(rate + 0.05, 1.02), f"{selector_counts[i]}/{selector_totals[i]}", ha="center", va="bottom")
    ax_c.set_ylim(0, 1.08)
    ax_c.set_ylabel("pass rate")
    ax_c.set_title("c  Selector prototypes")
    ax_c.tick_params(axis="x", labelrotation=18)
    for label in ax_c.get_xticklabels():
        label.set_ha("right")

    heatmap_methods = [
        "main:overtake_base_only",
        "adaptive:graph_adaptive_shield",
        "main:lane_base_only",
    ]
    seed_rows = {row["seed"]: row for row in stats["seed_complementarity"]}
    matrix = np.zeros((len(heatmap_methods), len(oracle["seeds"])), dtype=float)
    for j, seed in enumerate(oracle["seeds"]):
        passing = set(seed_rows[seed]["passing_methods"])
        for i, method in enumerate(heatmap_methods):
            matrix[i, j] = 1.0 if method in passing else 0.0
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            facecolor = PALETTE["pass"] if matrix[i, j] > 0.5 else "#F3F4F6"
            ax_d.add_patch(
                mpl.patches.Rectangle(
                    (j - 0.5, i - 0.5),
                    1.0,
                    1.0,
                    facecolor=facecolor,
                    edgecolor="white",
                    linewidth=0.6,
                )
            )
    ax_d.set_yticks(np.arange(len(heatmap_methods)), [SHORT_LABELS.get(m, m.split(":")[-1]) for m in heatmap_methods])
    ax_d.set_xticks(np.arange(len(oracle["seeds"])), [str(seed) for seed in oracle["seeds"]])
    ax_d.set_xlim(-0.5, len(oracle["seeds"]) - 0.5)
    ax_d.set_ylim(len(heatmap_methods) - 0.5, -0.5)
    ax_d.set_xlabel("seed")
    ax_d.set_title("d  Seed complementarity")
    ax_d.set_ylabel("method")
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            txt = "P" if matrix[i, j] > 0.5 else "F"
            ax_d.text(j, i, txt, ha="center", va="center", fontsize=6, color=PALETTE["text"])

    for ax in [ax_a, ax_b, ax_c, ax_d]:
        ax.tick_params(length=3, width=0.7)

    out_stem = out_dir / "figure_2_portfolio_selector_summary"
    save_pub(fig, out_stem)
    plt.close(fig)

    manifest = {
        "figure": "figure_2_portfolio_selector_summary",
        "claim": (
            "The current package exposes strong seed-level complementarity and an online simulator-loop selector, "
            "but a second held-out batch reveals a generalization boundary: DAgger-v2 raises coverage on the "
            "first held-out set, whereas heldout2 remains limited by both candidate gaps and selector misses."
        ),
        "panels": {
            "a": "Strict pass rates for full-suite methods.",
            "b": "Oracle portfolio upper bounds for size-1/2/3 portfolios.",
            "c": "Performance of selector prototypes versus oracle, including the second held-out stress batch.",
            "d": "Pass/fail complementarity across key methods and seeds.",
        },
        "source_data": str(out_dir / "figure_2_source_data.csv"),
        "exports": [str(out_stem) + ext for ext in [".svg", ".pdf", ".tiff", ".png"]],
        "review_risks": [
            "The expert-gate expansion is needed to recover the held-out 7/10 oracle.",
            "The DAgger-v2 expansion reaches 10/10 on the first held-out batch but drops to 5/10 on the second held-out batch.",
            "Offline selector calibration is included in source data and shows that score-only tuning does not close the heldout2 gap.",
            "The 450-step, geometry, faster-expert, barrier-expert, and recovery-expert controls are retained as negative controls.",
            "The seed complementarity panel only shows key methods, not every candidate.",
        ],
        "source_negative_controls": [item["name"] for item in negative_controls],
    }
    (out_dir / "figure_2_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"status": "PASS", "manifest": manifest}, indent=2))


if __name__ == "__main__":
    main()
