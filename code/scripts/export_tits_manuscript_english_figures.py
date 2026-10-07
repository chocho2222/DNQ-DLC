#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import json
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np


plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.sans-serif"] = ["Arial", "DejaVu Sans", "Liberation Sans"]
plt.rcParams["svg.fonttype"] = "none"
plt.rcParams["pdf.fonttype"] = 42

ALGORITHM_LABELS = {
    "v6_runtime_dynamic_neighborhood_safe": "Dynamic DLC-safe",
    "v6_runtime_dynamic_neighborhood": "Dynamic DLC",
    "quality_proposal_dlc_world_v1": "Quality-proposal DLC",
    "dlc_world_original": "Original DLC",
    "rule_expert_gate": "Rule expert",
}
COLORS = {
    "v6_runtime_dynamic_neighborhood_safe": "#0F4D92",
    "v6_runtime_dynamic_neighborhood": "#3775BA",
    "quality_proposal_dlc_world_v1": "#42949E",
    "dlc_world_original": "#B64342",
    "rule_expert_gate": "#606060",
}


def read_csv(path):
    with Path(path).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def f(value):
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def row_by_algorithm(rows, algorithm):
    for row in rows:
        if row["algorithm"] == algorithm:
            return row
    raise KeyError(algorithm)


def row_by_scenario(rows, benchmark, num_agents, algorithm):
    for row in rows:
        if row["benchmark"] == benchmark and int(row["num_agents"]) == int(num_agents) and row["algorithm"] == algorithm:
            return row
    raise KeyError((benchmark, num_agents, algorithm))


def paired_row(rows, algorithm, metric):
    for row in rows:
        if row["algorithm"] == algorithm and row["metric"] == metric:
            return row
    raise KeyError((algorithm, metric))


def stat(row, metric):
    return (
        f(row.get(f"{metric}_mean")),
        f(row.get(f"{metric}_ci95_low")),
        f(row.get(f"{metric}_ci95_high")),
    )


def add_panel_label(ax, label):
    ax.text(-0.12, 1.08, label, transform=ax.transAxes, fontsize=9, fontweight="bold", va="top")


def style_axis(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(labelsize=6.6, width=0.7, length=2.5)
    ax.grid(axis="y", color="#E1E5EA", linewidth=0.6, zorder=0)


def safe_error(mean, lo, hi):
    if mean is None or lo is None or hi is None:
        return [0], [0]
    return [max(mean - lo, 0.0)], [max(hi - mean, 0.0)]


def write_source_data(path, rows):
    fields = [
        "panel",
        "comparison",
        "algorithm",
        "algorithm_label",
        "metric",
        "metric_label",
        "mean",
        "ci95_low",
        "ci95_high",
        "unit",
        "source_table",
        "note",
    ]
    with Path(path).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return str(path)


def build_source_rows(overall, scenario, paired):
    source = []
    algorithms = [
        "v6_runtime_dynamic_neighborhood_safe",
        "quality_proposal_dlc_world_v1",
        "dlc_world_original",
        "rule_expert_gate",
    ]
    metrics_a = [
        ("overtake_success_rate", "Overtake success", "proportion"),
        ("elegant_overtake_rate", "Desirable overtaking behavior", "proportion"),
        ("on_track_overtake_rate", "On-track overtaking", "proportion"),
    ]
    for alg in algorithms:
        row = row_by_algorithm(overall, alg)
        for metric, label, unit in metrics_a:
            mean, lo, hi = stat(row, metric)
            source.append(
                {
                    "panel": "a",
                    "comparison": "overall",
                    "algorithm": alg,
                    "algorithm_label": ALGORITHM_LABELS[alg],
                    "metric": metric,
                    "metric_label": label,
                    "mean": mean,
                    "ci95_low": lo,
                    "ci95_high": hi,
                    "unit": unit,
                    "source_table": "confirmatory_overall_statistics.csv",
                    "note": "Mean and bootstrap 95% CI over confirmatory online runs.",
                }
            )

    metrics_b = [
        ("overtake_start_to_complete_time", "Completion time", "simulator steps"),
        ("target_grass_rate", "Target grass rate", "proportion"),
    ]
    for alg in algorithms:
        row = row_by_algorithm(overall, alg)
        for metric, label, unit in metrics_b:
            mean, lo, hi = stat(row, metric)
            source.append(
                {
                    "panel": "b",
                    "comparison": "overall",
                    "algorithm": alg,
                    "algorithm_label": ALGORITHM_LABELS[alg],
                    "metric": metric,
                    "metric_label": label,
                    "mean": mean,
                    "ci95_low": lo,
                    "ci95_high": hi,
                    "unit": unit,
                    "source_table": "confirmatory_overall_statistics.csv",
                    "note": "Lower values are better.",
                }
            )

    scenarios = [
        ("in_distribution_procedural", 6, "Procedural, 6 cars"),
        ("vehicle_count_extrapolation", 8, "8-car extrapolation"),
        ("monza_external_track", 6, "Monza, 6 cars"),
    ]
    for benchmark, n, comparison in scenarios:
        for alg in ["v6_runtime_dynamic_neighborhood_safe", "dlc_world_original"]:
            row = row_by_scenario(scenario, benchmark, n, alg)
            mean, lo, hi = stat(row, "elegant_overtake_rate")
            source.append(
                {
                    "panel": "c",
                    "comparison": comparison,
                    "algorithm": alg,
                    "algorithm_label": ALGORITHM_LABELS[alg],
                    "metric": "elegant_overtake_rate",
                    "metric_label": "Desirable overtaking behavior",
                    "mean": mean,
                    "ci95_low": lo,
                    "ci95_high": hi,
                    "unit": "proportion",
                    "source_table": "confirmatory_scenario_statistics.csv",
                    "note": "Scenario-level bootstrap 95% CI.",
                }
            )

    metrics_d = [
        ("overtake_success_rate", "Success", "proportion"),
        ("elegant_overtake_rate", "Desirable", "proportion"),
        ("on_track_overtake_rate", "On-track", "proportion"),
        ("overtake_start_to_complete_time", "Time reduction", "steps"),
        ("target_grass_rate", "Grass reduction", "proportion"),
    ]
    for metric, label, unit in metrics_d:
        row = paired_row(paired, "v6_runtime_dynamic_neighborhood_safe", metric)
        source.append(
            {
                "panel": "d",
                "comparison": "Dynamic DLC-safe vs original DLC",
                "algorithm": "v6_runtime_dynamic_neighborhood_safe",
                "algorithm_label": ALGORITHM_LABELS["v6_runtime_dynamic_neighborhood_safe"],
                "metric": metric,
                "metric_label": label,
                "mean": f(row.get("improvement_vs_dlc_mean")),
                "ci95_low": f(row.get("improvement_ci95_low")),
                "ci95_high": f(row.get("improvement_ci95_high")),
                "unit": unit,
                "source_table": "confirmatory_paired_tests_vs_dlc.csv",
                "note": "Positive values indicate improvement over original DLC.",
            }
        )
    return source


def plot_figure(source_rows, out_stem):
    mpl.rcParams.update(
        {
            "font.size": 7,
            "axes.linewidth": 0.7,
            "legend.frameon": False,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
        }
    )
    fig = plt.figure(figsize=(7.2, 6.6), constrained_layout=True)
    gs = fig.add_gridspec(2, 2, height_ratios=[1.0, 1.0], width_ratios=[1.08, 0.92])
    ax_a = fig.add_subplot(gs[0, 0])
    ax_b = fig.add_subplot(gs[0, 1])
    ax_c = fig.add_subplot(gs[1, 0])
    ax_d = fig.add_subplot(gs[1, 1])

    # Panel a
    panel_a = [r for r in source_rows if r["panel"] == "a"]
    metrics = ["Overtake success", "Desirable overtaking behavior", "On-track overtaking"]
    algorithms = [
        "v6_runtime_dynamic_neighborhood_safe",
        "quality_proposal_dlc_world_v1",
        "dlc_world_original",
        "rule_expert_gate",
    ]
    x = np.arange(len(metrics))
    width = 0.18
    for i, alg in enumerate(algorithms):
        means, lows, highs = [], [], []
        for metric_label in metrics:
            r = next(item for item in panel_a if item["algorithm"] == alg and item["metric_label"] == metric_label)
            mean, lo, hi = f(r["mean"]), f(r["ci95_low"]), f(r["ci95_high"])
            means.append(mean)
            lows.append(max(mean - lo, 0.0))
            highs.append(max(hi - mean, 0.0))
        offset = (i - (len(algorithms) - 1) / 2.0) * width
        ax_a.bar(x + offset, means, width=width, color=COLORS[alg], label=ALGORITHM_LABELS[alg], zorder=3)
        ax_a.errorbar(x + offset, means, yerr=np.asarray([lows, highs]), fmt="none", ecolor="#303030", elinewidth=0.7, capsize=1.8, zorder=4)
    ax_a.set_xticks(x)
    ax_a.set_xticklabels(["Success", "Desirable", "On-track"])
    ax_a.set_ylim(0, 1.05)
    ax_a.set_ylabel("Proportion")
    ax_a.set_title("Overall overtaking quality", fontsize=8, pad=4)
    ax_a.legend(fontsize=5.7, ncol=2, loc="upper left", bbox_to_anchor=(0.0, 1.02), handlelength=1.1, columnspacing=0.8)
    style_axis(ax_a)
    add_panel_label(ax_a, "a")

    # Panel b
    panel_b = [r for r in source_rows if r["panel"] == "b"]
    time_rows = [r for r in panel_b if r["metric"] == "overtake_start_to_complete_time"]
    grass_rows = [r for r in panel_b if r["metric"] == "target_grass_rate"]
    xb = np.arange(len(algorithms))
    time_means = [f(next(r for r in time_rows if r["algorithm"] == alg)["mean"]) for alg in algorithms]
    time_lo = [f(next(r for r in time_rows if r["algorithm"] == alg)["ci95_low"]) for alg in algorithms]
    time_hi = [f(next(r for r in time_rows if r["algorithm"] == alg)["ci95_high"]) for alg in algorithms]
    ax_b.bar(xb, time_means, color=[COLORS[alg] for alg in algorithms], width=0.62, zorder=3)
    ax_b.errorbar(xb, time_means, yerr=np.asarray([[max(m - l, 0.0) for m, l in zip(time_means, time_lo)], [max(h - m, 0.0) for m, h in zip(time_means, time_hi)]]), fmt="none", ecolor="#303030", elinewidth=0.7, capsize=1.8, zorder=4)
    ax_b.set_xticks(xb)
    ax_b.set_xticklabels([ALGORITHM_LABELS[alg].replace(" ", "\n") for alg in algorithms], fontsize=5.8)
    ax_b.set_ylabel("Overtake completion time\n(steps; lower is better)")
    ax_b.set_title("Efficiency and off-track risk", fontsize=8, pad=4)
    style_axis(ax_b)
    ax_b2 = ax_b.twinx()
    grass_means = [f(next(r for r in grass_rows if r["algorithm"] == alg)["mean"]) for alg in algorithms]
    ax_b2.plot(xb, grass_means, color="#272727", marker="o", markersize=3.5, linewidth=1.1, zorder=5)
    ax_b2.set_ylim(0, 1.0)
    ax_b2.set_ylabel("Target grass rate", fontsize=6.5)
    ax_b2.tick_params(labelsize=6.2, width=0.7, length=2.5)
    ax_b2.spines["top"].set_visible(False)
    ax_b2.text(0.02, 0.92, "● grass rate", transform=ax_b.transAxes, fontsize=6.1, color="#272727")
    add_panel_label(ax_b, "b")

    # Panel c
    panel_c = [r for r in source_rows if r["panel"] == "c"]
    comparisons = ["Procedural, 6 cars", "8-car extrapolation", "Monza, 6 cars"]
    x = np.arange(len(comparisons))
    width = 0.34
    for i, alg in enumerate(["v6_runtime_dynamic_neighborhood_safe", "dlc_world_original"]):
        means, lows, highs = [], [], []
        for comp in comparisons:
            r = next(item for item in panel_c if item["algorithm"] == alg and item["comparison"] == comp)
            mean, lo, hi = f(r["mean"]), f(r["ci95_low"]), f(r["ci95_high"])
            means.append(mean)
            lows.append(max(mean - lo, 0.0))
            highs.append(max(hi - mean, 0.0))
        offset = (i - 0.5) * width
        ax_c.bar(x + offset, means, width=width, color=COLORS[alg], label=ALGORITHM_LABELS[alg], zorder=3)
        ax_c.errorbar(x + offset, means, yerr=np.asarray([lows, highs]), fmt="none", ecolor="#303030", elinewidth=0.7, capsize=1.8, zorder=4)
    ax_c.set_xticks(x)
    ax_c.set_xticklabels(["Procedural\n6 cars", "8-car\nextrapolation", "Monza\n6 cars"])
    ax_c.set_ylim(0, 1.05)
    ax_c.set_ylabel("Desirable overtaking behavior rate")
    ax_c.set_title("Generalization across traffic and track settings", fontsize=8, pad=4)
    ax_c.legend(fontsize=6.1, loc="upper left")
    style_axis(ax_c)
    add_panel_label(ax_c, "c")

    # Panel d
    panel_d = [r for r in source_rows if r["panel"] == "d"]
    metric_order = ["Success", "Desirable", "On-track", "Grass reduction", "Time reduction"]
    # Put time on separate top axis by normalizing to a visual scale and writing values.
    rate_metrics = ["Success", "Desirable", "On-track", "Grass reduction"]
    yd = np.arange(len(rate_metrics))[::-1]
    for y, label in zip(yd, rate_metrics):
        r = next(item for item in panel_d if item["metric_label"] == label)
        mean, lo, hi = f(r["mean"]), f(r["ci95_low"]), f(r["ci95_high"])
        ax_d.errorbar(mean, y, xerr=np.asarray([[max(mean - lo, 0.0)], [max(hi - mean, 0.0)]]), fmt="o", color="#0F4D92", ecolor="#0F4D92", elinewidth=1.0, capsize=2.0)
        ax_d.text(mean + 0.03, y, f"{mean:.2f}", fontsize=6.0, va="center")
    ax_d.axvline(0, color="#272727", linewidth=0.8)
    ax_d.set_yticks(yd)
    ax_d.set_yticklabels(rate_metrics)
    ax_d.set_xlim(-0.05, 0.62)
    ax_d.set_xlabel("Paired improvement over original DLC")
    ax_d.set_title("Matched-case gains for Dynamic DLC-safe", fontsize=8, pad=4)
    style_axis(ax_d)
    time_r = next(item for item in panel_d if item["metric_label"] == "Time reduction")
    ax_d.text(0.02, -0.28, f"Time reduction: {f(time_r['mean']):.1f} steps\n95% CI [{f(time_r['ci95_low']):.1f}, {f(time_r['ci95_high']):.1f}]", transform=ax_d.transAxes, fontsize=6.2, va="top")
    add_panel_label(ax_d, "d")

    fig.suptitle("Dynamic-neighborhood DLC world model improves online overtaking", fontsize=9, fontweight="bold", y=1.01)
    out_stem = Path(out_stem)
    out_stem.parent.mkdir(parents=True, exist_ok=True)
    outputs = {}
    for ext, kwargs in {
        "svg": {},
        "pdf": {},
        "png": {"dpi": 600},
        "tiff": {"dpi": 600},
    }.items():
        out = out_stem.with_suffix(f".{ext}")
        fig.savefig(out, bbox_inches="tight", **kwargs)
        outputs[ext] = str(out)
    plt.close(fig)
    return outputs


def write_legend(path):
    text = """# Figure Legend

**Figure. Dynamic-neighborhood DLC world-model planning improves online multi-car overtaking.**

**a,** Overall overtake success, desirable overtaking behavior rate, and on-track overtake rate across the 240-run confirmatory online matrix. Bars show means and error bars show bootstrap 95% confidence intervals. **b,** Overtake start-to-completion time (bars; lower is better) and target grass rate (black line) for the same algorithms. **c,** Desirable overtaking behavior rate in procedural six-car, eight-car extrapolation, and Monza six-car settings for Dynamic DLC-safe and the original DLC world model. **d,** Matched-case improvement of Dynamic DLC-safe over the original DLC world model. Positive values indicate improved success/quality or reduced grass/time, computed from paired benchmark, vehicle-count and seed matches.

All panels are generated from the frozen confirmatory evidence tables. Quantitative source data are provided in `figure_dynamic_dlc_overtaking_source_data.csv`.
"""
    Path(path).write_text(text, encoding="utf-8")
    return str(path)


def write_qa(path, outputs, source_data):
    qa = {
        "status": "pass",
        "core_conclusion": "Dynamic-neighborhood DLC world-model planning improves online overtaking quality and efficiency over the original DLC world model.",
        "archetype": "quantitative grid",
        "backend": "Python/matplotlib",
        "exports": outputs,
        "source_data": source_data,
        "checks": {
            "editable_svg_text": "matplotlib svg.fonttype set to none",
            "pdf_fonttype": "42",
            "source_data_available": Path(source_data).exists(),
            "all_exports_nonempty": all(Path(p).exists() and Path(p).stat().st_size > 0 for p in outputs.values()),
            "statistics_documented": "means and bootstrap 95% CIs, paired improvements for panel d",
            "image_integrity": "no raster image manipulation; quantitative plots only",
        },
        "reviewer_risks": [
            "This is a simulator benchmark figure and should not be phrased as real-vehicle validation.",
            "Representative GIF evidence should remain supplementary to quantitative statistics.",
            "Final journal figure language and dimensions should be checked against the target IEEE production requirements.",
        ],
    }
    Path(path).write_text(json.dumps(qa, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


def main():
    parser = argparse.ArgumentParser(description="Export English manuscript figures for the T-ITS dynamic DLC study.")
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/manuscript_english_figures")
    parser.add_argument("--overall", default="outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack/tables/confirmatory_overall_statistics.csv")
    parser.add_argument("--scenario", default="outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack/tables/confirmatory_scenario_statistics.csv")
    parser.add_argument("--paired", default="outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack/tables/confirmatory_paired_tests_vs_dlc.csv")
    args = parser.parse_args()
    out_dir = Path(args.out_dir)
    figures = out_dir / "figures"
    tables = out_dir / "tables"
    materials = out_dir / "materials"
    figures.mkdir(parents=True, exist_ok=True)
    tables.mkdir(parents=True, exist_ok=True)
    materials.mkdir(parents=True, exist_ok=True)

    overall = read_csv(args.overall)
    scenario = read_csv(args.scenario)
    paired = read_csv(args.paired)
    source_rows = build_source_rows(overall, scenario, paired)
    source_data = write_source_data(tables / "figure_dynamic_dlc_overtaking_source_data.csv", source_rows)
    outputs = plot_figure(source_rows, figures / "figure_dynamic_dlc_overtaking_english")
    legend = write_legend(materials / "FIGURE_DYNAMIC_DLC_OVERTAKING_LEGEND.md")
    qa = write_qa(materials / "FIGURE_DYNAMIC_DLC_OVERTAKING_QA.json", outputs, source_data)
    manifest = {
        "status": "complete",
        "out_dir": str(out_dir),
        "figure_contract": {
            "core_conclusion": "Dynamic-neighborhood DLC world-model planning improves online overtaking quality and efficiency over original DLC.",
            "archetype": "quantitative grid",
            "backend": "Python/matplotlib",
            "panel_count": 4,
        },
        "paths": {
            "source_data": source_data,
            "legend": legend,
            "qa": qa,
            **{f"figure_{k}": v for k, v in outputs.items()},
        },
    }
    manifest_path = out_dir / "manuscript_english_figures_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"manifest": str(manifest_path), "status": manifest["status"], "exports": outputs}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
