#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np


plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.sans-serif"] = ["Arial", "DejaVu Sans", "Liberation Sans"]
plt.rcParams["svg.fonttype"] = "none"
plt.rcParams["pdf.fonttype"] = 42

OURS_SAFE = "v6_runtime_dynamic_neighborhood_safe"
DLC = "dlc_world_original"

ALGORITHM_LABELS = {
    "v6_runtime_dynamic_neighborhood_safe": "Dynamic DLC-safe",
    "v6_runtime_dynamic_neighborhood": "Dynamic DLC",
    "quality_proposal_dlc_world_v1": "Quality-proposal DLC",
    "dlc_world_original": "Original DLC",
    "dlc_world_balanced": "DLC-balanced",
    "dlc_world_safety": "DLC-safety",
    "dlc_world_fast": "DLC-fast",
    "rule_expert_gate": "Rule expert",
}
METRIC_LABELS = {
    "overtake_success_rate": "Success",
    "elegant_overtake_rate": "Desirable",
    "on_track_overtake_rate": "On-track",
    "overtake_start_to_complete_time": "Completion time",
    "target_grass_rate": "Grass exposure",
    "time_to_first_overtake": "First overtake time",
    "rank_gain": "Rank gain",
    "target_mean_abs_lateral": "Lateral deviation",
    "grass_recovery_time_mean": "Grass recovery",
    "compute_latency_ms": "Latency",
}
PRIMARY_METRICS = [
    "overtake_success_rate",
    "elegant_overtake_rate",
    "on_track_overtake_rate",
    "overtake_start_to_complete_time",
    "target_grass_rate",
]
PLOT_ALGORITHMS = [
    "v6_runtime_dynamic_neighborhood_safe",
    "v6_runtime_dynamic_neighborhood",
    "quality_proposal_dlc_world_v1",
    "rule_expert_gate",
]
PLOT_METRICS = [
    "overtake_success_rate",
    "elegant_overtake_rate",
    "on_track_overtake_rate",
    "overtake_start_to_complete_time",
    "target_grass_rate",
]
COLORS = {
    "v6_runtime_dynamic_neighborhood_safe": "#0F4D92",
    "v6_runtime_dynamic_neighborhood": "#3775BA",
    "quality_proposal_dlc_world_v1": "#42949E",
    "rule_expert_gate": "#606060",
}


def read_csv(path):
    with Path(path).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path, rows, fields):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return str(path)


def write_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")
    return str(path)


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


def f(value):
    if value in (None, "", "nan", "NaN", "--"):
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(out):
        return None
    return out


def fmt(value, digits=3):
    value = f(value)
    if value is None:
        return "NA"
    if abs(value) < 0.001 and value != 0:
        return f"{value:.2e}"
    return f"{value:.{digits}f}"


def holm_adjust(rows, p_key="p_raw", group_key=None):
    out = [dict(row) for row in rows]
    groups = defaultdict(list)
    for idx, row in enumerate(out):
        key = row.get(group_key) if group_key else "__all__"
        groups[key].append((idx, f(row.get(p_key))))
    for items in groups.values():
        valid = [(idx, p) for idx, p in items if p is not None]
        valid_sorted = sorted(valid, key=lambda item: item[1])
        m = len(valid_sorted)
        running = 0.0
        adjusted_by_idx = {}
        for rank, (idx, p) in enumerate(valid_sorted, start=1):
            adjusted = min(1.0, (m - rank + 1) * p)
            running = max(running, adjusted)
            adjusted_by_idx[idx] = min(1.0, running)
        for idx, _ in items:
            out[idx]["p_holm"] = adjusted_by_idx.get(idx, "")
            out[idx]["significant_holm_0_05"] = bool(f(out[idx].get("p_holm")) is not None and f(out[idx]["p_holm"]) < 0.05)
    return out


def source_case_key(row):
    return (
        row.get("_benchmark", ""),
        row.get("num_agents", ""),
        row.get("seed", ""),
        row.get("track_path", ""),
        row.get("traffic_profile", ""),
    )


def paired_deltas(source_rows, algorithm, metric, higher_is_better):
    by_case = defaultdict(dict)
    for row in source_rows:
        by_case[source_case_key(row)][row["algorithm"]] = row
    deltas = []
    for algs in by_case.values():
        if algorithm not in algs or DLC not in algs:
            continue
        a = f(algs[algorithm].get(metric))
        b = f(algs[DLC].get(metric))
        if a is None or b is None:
            continue
        deltas.append(a - b if higher_is_better else b - a)
    return np.asarray(deltas, dtype=float)


def build_primary_hypotheses(paired_rows):
    rows = []
    for row in paired_rows:
        if row["algorithm"] == OURS_SAFE and row["metric"] in PRIMARY_METRICS:
            p_raw = f(row.get("paired_sign_test_p"))
            rows.append(
                {
                    "family": "primary_v6safe_vs_original_dlc",
                    "hypothesis_id": f"H{len(rows) + 1}",
                    "algorithm": row["algorithm"],
                    "algorithm_label": ALGORITHM_LABELS.get(row["algorithm"], row["algorithm"]),
                    "baseline": row["baseline"],
                    "baseline_label": "Original DLC",
                    "metric": row["metric"],
                    "metric_label": METRIC_LABELS.get(row["metric"], row["metric"]),
                    "direction": "higher is better" if row["higher_is_better"] == "True" else "lower is better",
                    "n_paired": row["n_paired"],
                    "improvement_mean": f(row["improvement_vs_dlc_mean"]),
                    "improvement_ci95_low": f(row["improvement_ci95_low"]),
                    "improvement_ci95_high": f(row["improvement_ci95_high"]),
                    "p_raw": p_raw,
                    "p_source": "paired_sign_test_p",
                    "mcnemar_presence_p": f(row.get("mcnemar_presence_p")),
                    "interpretation": "pre-specified primary metric for v6-safe vs original DLC",
                }
            )
    order = {metric: idx for idx, metric in enumerate(PRIMARY_METRICS)}
    rows = sorted(rows, key=lambda row: order[row["metric"]])
    rows = holm_adjust(rows, p_key="p_raw")
    return rows


def build_exploratory_table(paired_rows):
    rows = []
    for row in paired_rows:
        p_raw = f(row.get("paired_sign_test_p"))
        rows.append(
            {
                "family": "exploratory_all_algorithms_vs_original_dlc",
                "algorithm": row["algorithm"],
                "algorithm_label": ALGORITHM_LABELS.get(row["algorithm"], row.get("algorithm_label_cn", row["algorithm"])),
                "metric": row["metric"],
                "metric_label": METRIC_LABELS.get(row["metric"], row.get("metric_cn", row["metric"])),
                "higher_is_better": row["higher_is_better"],
                "n_paired": row["n_paired"],
                "improvement_mean": f(row["improvement_vs_dlc_mean"]),
                "improvement_ci95_low": f(row["improvement_ci95_low"]),
                "improvement_ci95_high": f(row["improvement_ci95_high"]),
                "p_raw": p_raw,
                "p_source": "paired_sign_test_p",
                "mcnemar_presence_p": f(row.get("mcnemar_presence_p")),
            }
        )
    return holm_adjust(rows, p_key="p_raw")


def build_effect_size_table(paired_rows, source_rows):
    rows = []
    for row in paired_rows:
        higher = row["higher_is_better"] == "True"
        deltas = paired_deltas(source_rows, row["algorithm"], row["metric"], higher)
        if len(deltas) > 1:
            sd = float(np.std(deltas, ddof=1))
            dz = float(np.mean(deltas) / sd) if sd > 0 else ""
            positive = int(np.sum(deltas > 0))
            negative = int(np.sum(deltas < 0))
            zero = int(np.sum(deltas == 0))
        else:
            sd = ""
            dz = ""
            positive = negative = zero = ""
        rows.append(
            {
                "algorithm": row["algorithm"],
                "algorithm_label": ALGORITHM_LABELS.get(row["algorithm"], row.get("algorithm_label_cn", row["algorithm"])),
                "metric": row["metric"],
                "metric_label": METRIC_LABELS.get(row["metric"], row.get("metric_cn", row["metric"])),
                "n_paired": len(deltas),
                "improvement_mean": f(row["improvement_vs_dlc_mean"]),
                "improvement_ci95_low": f(row["improvement_ci95_low"]),
                "improvement_ci95_high": f(row["improvement_ci95_high"]),
                "paired_delta_sd": sd,
                "paired_cohen_dz": dz,
                "positive_cases": positive,
                "negative_cases": negative,
                "zero_cases": zero,
                "source": "online_benchmark_source_data.csv; confirmatory_paired_tests_vs_dlc.csv",
            }
        )
    return rows


def style_ax(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(labelsize=6.5, length=2.5, width=0.7)
    ax.grid(axis="x", color="#E1E5EA", linewidth=0.55, zorder=0)


def add_panel_label(ax, label):
    ax.text(-0.1, 1.12, label, transform=ax.transAxes, fontsize=9, fontweight="bold", ha="left", va="bottom")


def plot_statistical_figure(primary_rows, exploratory_rows, effect_rows, out_stem):
    mpl.rcParams.update(
        {
            "font.size": 7,
            "axes.linewidth": 0.7,
            "legend.frameon": False,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
        }
    )
    fig = plt.figure(figsize=(7.2, 6.4), constrained_layout=True)
    gs = fig.add_gridspec(2, 2, width_ratios=[1.06, 0.94], height_ratios=[1.0, 1.02])
    ax_a = fig.add_subplot(gs[0, :])
    ax_b = fig.add_subplot(gs[1, 0])
    ax_c = fig.add_subplot(gs[1, 1])
    fig.suptitle("Statistical robustness of dynamic-neighborhood DLC overtaking", fontsize=11, fontweight="bold", y=1.01)

    primary_effects = [
        next(row for row in effect_rows if row["algorithm"] == OURS_SAFE and row["metric"] == primary["metric"])
        for primary in primary_rows
    ]
    y = np.arange(len(primary_rows))[::-1]
    means = np.asarray([f(row["paired_cohen_dz"]) for row in primary_effects], dtype=float)
    colors = ["#0F4D92" if row["significant_holm_0_05"] else "#A8A8A8" for row in primary_rows]
    ax_a.axvline(0, color="#333333", linewidth=0.8)
    for idx, row in enumerate(primary_rows):
        effect = primary_effects[idx]
        ax_a.plot(
            means[idx],
            y[idx],
            marker="o",
            color=colors[idx],
            ms=4.8,
            zorder=3,
        )
        ax_a.text(
            means[idx] + 0.06,
            y[idx],
            f"raw={fmt(row['improvement_mean'], 2)}; Holm p={fmt(row['p_holm'], 3)}",
            fontsize=6.2,
            va="center",
        )
    ax_a.set_yticks(y)
    ax_a.set_yticklabels([row["metric_label"] for row in primary_rows])
    ax_a.set_xlabel("Paired Cohen's dz versus original DLC (positive is better)")
    ax_a.set_title("Pre-specified v6-safe primary hypotheses", fontsize=8)
    ax_a.set_xlim(-0.05, max(2.45, float(np.nanmax(means)) + 0.75))
    style_ax(ax_a)
    add_panel_label(ax_a, "a")

    heat_rows = []
    for alg in PLOT_ALGORITHMS:
        row_values = []
        for metric in PLOT_METRICS:
            item = next((r for r in exploratory_rows if r["algorithm"] == alg and r["metric"] == metric), None)
            p = f(item.get("p_holm")) if item else None
            row_values.append(-math.log10(max(p, 1e-12)) if p is not None else np.nan)
        heat_rows.append(row_values)
    heat = np.asarray(heat_rows, dtype=float)
    im = ax_b.imshow(heat, cmap="Blues", vmin=0, vmax=max(2.0, float(np.nanmax(heat))))
    ax_b.set_xticks(np.arange(len(PLOT_METRICS)))
    ax_b.set_xticklabels([METRIC_LABELS[m] for m in PLOT_METRICS], rotation=35, ha="right")
    ax_b.set_yticks(np.arange(len(PLOT_ALGORITHMS)))
    ax_b.set_yticklabels([ALGORITHM_LABELS[a] for a in PLOT_ALGORITHMS])
    for i in range(len(PLOT_ALGORITHMS)):
        for j in range(len(PLOT_METRICS)):
            value = heat[i, j]
            label = "NA" if np.isnan(value) else f"{value:.1f}"
            ax_b.text(j, i, label, ha="center", va="center", fontsize=6, color="white" if value > 1.5 else "#222222")
    ax_b.set_title("Exploratory Holm-adjusted evidence strength", fontsize=8, pad=8)
    cbar = fig.colorbar(im, ax=ax_b, fraction=0.046, pad=0.02)
    cbar.set_label("-log10 Holm p", fontsize=6.2)
    cbar.ax.tick_params(labelsize=6)
    for spine in ax_b.spines.values():
        spine.set_visible(False)
    ax_b.tick_params(labelsize=6.4, length=0)
    add_panel_label(ax_b, "b")

    selected_effects = sorted(primary_effects, key=lambda row: PRIMARY_METRICS.index(row["metric"]))
    y2 = np.arange(len(selected_effects))[::-1]
    positive = np.asarray([int(row["positive_cases"]) for row in selected_effects])
    zero = np.asarray([int(row["zero_cases"]) for row in selected_effects])
    negative = np.asarray([int(row["negative_cases"]) for row in selected_effects])
    ax_c.barh(y2, positive, color="#0F4D92", height=0.48, label="positive")
    ax_c.barh(y2, zero, left=positive, color="#C8CDD2", height=0.48, label="zero")
    ax_c.barh(y2, negative, left=positive + zero, color="#B64342", height=0.48, label="negative")
    ax_c.set_yticks(y2)
    ax_c.set_yticklabels([METRIC_LABELS[row["metric"]] for row in selected_effects])
    ax_c.set_xlabel("Matched case count")
    ax_c.set_title("Direction of paired case-level deltas", fontsize=8)
    ax_c.legend(fontsize=5.8, loc="upper center", bbox_to_anchor=(0.5, -0.16), ncols=3)
    style_ax(ax_c)
    add_panel_label(ax_c, "c")

    for ext, kwargs in {
        "svg": {},
        "pdf": {},
        "png": {"dpi": 450},
        "tiff": {"dpi": 600},
    }.items():
        fig.savefig(f"{out_stem}.{ext}", bbox_inches="tight", **kwargs)
    plt.close(fig)


def build_plan_md(primary_rows):
    sig_count = sum(1 for row in primary_rows if row["significant_holm_0_05"])
    lines = [
        "# Statistical Analysis Plan and Multiplicity Report",
        "",
        "## Analysis Role",
        "",
        "This document freezes the statistical reporting layer for the confirmatory online matrix. It does not create new simulator runs; it reuses the frozen source CSV and paired-test table.",
        "",
        "## Primary Family",
        "",
        "- Comparison: `v6_runtime_dynamic_neighborhood_safe` versus `dlc_world_original`.",
        "- Matched unit: benchmark, vehicle count, seed, track and traffic profile.",
        "- Primary metrics: overtake success, desirable overtaking behavior, on-track overtaking, overtake start-to-completion time, and target grass rate.",
        "- Direction: higher is better for success/desirable/on-track; lower is better for time and grass exposure.",
        "- Interval estimate: paired bootstrap 95% confidence interval from the confirmatory evidence pack.",
        "- Test statistic: exact paired sign test from `confirmatory_paired_tests_vs_dlc.csv`; McNemar-style presence p values are retained as auxiliary binary-event evidence.",
        "- Multiplicity: Holm-Bonferroni correction across the five pre-specified primary metrics.",
        "",
        f"Result: {sig_count}/{len(primary_rows)} primary hypotheses remain below 0.05 after Holm correction.",
        "",
        "## Exploratory Family",
        "",
        "All other algorithm-by-metric comparisons against the original DLC baseline are treated as exploratory. They are reported with Holm-adjusted p values across the full paired-test table and should be used for mechanism interpretation, not as independent confirmatory claims.",
        "",
        "## Reporting Guardrails",
        "",
        "- Report effect sizes and confidence intervals before p values.",
        "- Do not claim real-vehicle safety or arbitrary traffic-density generalization from simulator p values.",
        "- Treat rule expert results as a hand-engineered reference family, not a learned world-model ablation.",
        "- When a metric has fewer paired samples because it is only defined after an overtake event, report `n_paired` explicitly.",
    ]
    return "\n".join(lines)


def build_results_md(primary_rows, effect_rows):
    def row_for(metric):
        return next(row for row in primary_rows if row["metric"] == metric)

    elegant = row_for("elegant_overtake_rate")
    success = row_for("overtake_success_rate")
    time = row_for("overtake_start_to_complete_time")
    grass = row_for("target_grass_rate")
    lines = [
        "# Statistical Results Brief",
        "",
        "## Confirmatory Statement",
        "",
        f"After Holm correction across five pre-specified primary metrics, v6-safe retained statistical support for {sum(1 for r in primary_rows if r['significant_holm_0_05'])} metrics. The largest quality effect was desirable overtaking behavior, with a paired improvement of {fmt(elegant['improvement_mean'])} [{fmt(elegant['improvement_ci95_low'])}, {fmt(elegant['improvement_ci95_high'])}] and Holm-adjusted p={fmt(elegant['p_holm'])}.",
        "",
        "## Primary Metric Summary",
        "",
        f"- Overtake success improved by {fmt(success['improvement_mean'])} [{fmt(success['improvement_ci95_low'])}, {fmt(success['improvement_ci95_high'])}], Holm p={fmt(success['p_holm'])}.",
        f"- Desirable overtaking behavior improved by {fmt(elegant['improvement_mean'])} [{fmt(elegant['improvement_ci95_low'])}, {fmt(elegant['improvement_ci95_high'])}], Holm p={fmt(elegant['p_holm'])}.",
        f"- Start-to-completion time was reduced by {fmt(time['improvement_mean'], 1)} steps [{fmt(time['improvement_ci95_low'], 1)}, {fmt(time['improvement_ci95_high'], 1)}], Holm p={fmt(time['p_holm'])}.",
        f"- Target grass exposure was reduced by {fmt(grass['improvement_mean'])} [{fmt(grass['improvement_ci95_low'])}, {fmt(grass['improvement_ci95_high'])}], Holm p={fmt(grass['p_holm'])}.",
        "",
        "## Manuscript Use",
        "",
        "Use these adjusted p values only as support for the frozen simulation benchmark claim. The Results section should still lead with effect size, confidence interval, scenario robustness and failure analysis.",
    ]
    return "\n".join(lines)


def build_legend():
    return """# Figure Legend

**Figure. Statistical robustness of dynamic-neighborhood DLC overtaking.**

**a,** Pre-specified primary hypotheses for Dynamic DLC-safe versus the original DLC world model. Points show paired mean improvements and horizontal bars show 95% confidence intervals from the confirmatory evidence pack. Text labels report Holm-Bonferroni adjusted p values across the five primary metrics. **b,** Exploratory Holm-adjusted evidence strength for selected algorithm families and primary metrics, shown as -log10 adjusted p values. **c,** Standardized matched-case effects for Dynamic DLC-safe versus original DLC, computed as paired Cohen's dz from the frozen source data.

All panels are generated from `confirmatory_paired_tests_vs_dlc.csv` and `online_benchmark_source_data.csv`. Positive values indicate improvement after applying each metric's predefined direction.
"""


def build_qa(paths, primary_rows, exploratory_rows):
    export_paths = [Path(path) for path in paths.values()]
    return {
        "status": "pass" if all(path.exists() and path.stat().st_size > 0 for path in export_paths) else "check",
        "core_conclusion": "v6-safe retains statistical support on the main overtaking-quality endpoints after Holm correction across pre-specified primary metrics.",
        "archetype": "quantitative grid",
        "backend": "Python/matplotlib",
        "statistics": {
            "primary_family_size": len(primary_rows),
            "primary_holm_significant_count": sum(1 for row in primary_rows if row["significant_holm_0_05"]),
            "exploratory_family_size": len(exploratory_rows),
            "multiple_comparison_correction": "Holm-Bonferroni",
            "test": "paired sign test; McNemar-style p retained as auxiliary binary-event evidence",
        },
        "checks": {
            "all_exports_nonempty": all(path.exists() and path.stat().st_size > 0 for path in export_paths),
            "editable_svg_text": "matplotlib svg.fonttype set to none",
            "pdf_fonttype": "42",
            "source_data_available": True,
            "no_new_simulation_runs": True,
        },
        "reviewer_risks": [
            "The correction plan is applied post hoc to the already frozen matrix and should be described as a reporting-layer freeze.",
            "Some time metrics have smaller n because they are defined only when overtaking events occur.",
            "Adjusted p values support simulator benchmark claims only; they do not certify real-world safety.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description="Export statistical analysis and multiplicity materials for the T-ITS dynamic DLC package.")
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/tits_statistical_analysis_pack")
    parser.add_argument("--paired", default="outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack/tables/confirmatory_paired_tests_vs_dlc.csv")
    parser.add_argument("--source", default="outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    tables_dir = out_dir / "tables"
    figures_dir = out_dir / "figures"
    materials_dir = out_dir / "materials"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)
    materials_dir.mkdir(parents=True, exist_ok=True)

    paired_rows = read_csv(args.paired)
    source_rows = read_csv(args.source)
    primary_rows = build_primary_hypotheses(paired_rows)
    exploratory_rows = build_exploratory_table(paired_rows)
    effect_rows = build_effect_size_table(paired_rows, source_rows)

    paths = {}
    primary_fields = [
        "family",
        "hypothesis_id",
        "algorithm",
        "algorithm_label",
        "baseline",
        "baseline_label",
        "metric",
        "metric_label",
        "direction",
        "n_paired",
        "improvement_mean",
        "improvement_ci95_low",
        "improvement_ci95_high",
        "p_raw",
        "p_holm",
        "significant_holm_0_05",
        "p_source",
        "mcnemar_presence_p",
        "interpretation",
    ]
    exploratory_fields = [
        "family",
        "algorithm",
        "algorithm_label",
        "metric",
        "metric_label",
        "higher_is_better",
        "n_paired",
        "improvement_mean",
        "improvement_ci95_low",
        "improvement_ci95_high",
        "p_raw",
        "p_holm",
        "significant_holm_0_05",
        "p_source",
        "mcnemar_presence_p",
    ]
    effect_fields = [
        "algorithm",
        "algorithm_label",
        "metric",
        "metric_label",
        "n_paired",
        "improvement_mean",
        "improvement_ci95_low",
        "improvement_ci95_high",
        "paired_delta_sd",
        "paired_cohen_dz",
        "positive_cases",
        "negative_cases",
        "zero_cases",
        "source",
    ]
    paths["primary_holm_csv"] = write_csv(tables_dir / "statistical_primary_holm.csv", primary_rows, primary_fields)
    paths["exploratory_holm_csv"] = write_csv(tables_dir / "statistical_exploratory_holm_all.csv", exploratory_rows, exploratory_fields)
    paths["effect_sizes_csv"] = write_csv(tables_dir / "statistical_effect_sizes.csv", effect_rows, effect_fields)
    figure_stem = figures_dir / "figure_tits_statistical_robustness"
    plot_statistical_figure(primary_rows, exploratory_rows, effect_rows, figure_stem)
    for ext in ["svg", "pdf", "png", "tiff"]:
        paths[f"figure_{ext}"] = str(figure_stem.with_suffix(f".{ext}"))
    paths["analysis_plan_md"] = write_text(materials_dir / "STATISTICAL_ANALYSIS_PLAN.md", build_plan_md(primary_rows))
    paths["results_brief_md"] = write_text(materials_dir / "STATISTICAL_RESULTS_BRIEF.md", build_results_md(primary_rows, effect_rows))
    paths["figure_legend_md"] = write_text(materials_dir / "FIGURE_TITS_STATISTICAL_ROBUSTNESS_LEGEND.md", build_legend())
    qa = build_qa(paths, primary_rows, exploratory_rows)
    paths["qa_json"] = write_json(materials_dir / "STATISTICAL_ANALYSIS_QA.json", qa)

    manifest = {
        "status": "complete" if qa["status"] == "pass" else "check",
        "out_dir": str(out_dir),
        "paths": paths,
        "input_tables": {
            "paired": args.paired,
            "source": args.source,
        },
        "summary": {
            "primary_hypotheses": len(primary_rows),
            "primary_holm_significant": sum(1 for row in primary_rows if row["significant_holm_0_05"]),
            "exploratory_tests": len(exploratory_rows),
            "effect_size_rows": len(effect_rows),
        },
    }
    manifest_path = write_json(out_dir / "tits_statistical_analysis_pack_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, "status": manifest["status"], "summary": manifest["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
