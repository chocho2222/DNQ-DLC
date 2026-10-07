#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Export revised T-ITS/Nature-style figures for Experiments 2-6.

The script is intentionally idempotent: it can be run on partial online
experiment folders and rerun after more cases finish.
"""

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

try:
    from tits_figure_style import (
        ABLATION_ORDER,
        ALGORITHM_ORDER,
        PROPOSED,
        PROPOSED_E6,
        color_for_algorithm,
        configure_publication_matplotlib,
        label_for_algorithm,
        sorted_algorithms,
    )
except ImportError:
    from scripts.tits_figure_style import (
        ABLATION_ORDER,
        ALGORITHM_ORDER,
        PROPOSED,
        PROPOSED_E6,
        color_for_algorithm,
        configure_publication_matplotlib,
        label_for_algorithm,
        sorted_algorithms,
    )


TRACK_LABELS = {
    "E2_oval": "Oval",
    "E2_s_curve": "S-Curve",
    "E2_hairpin": "Hairpin",
    "E2_monza": "Monza",
    "oval_scaled": "Oval",
    "s_curve_scaled": "S-Curve",
    "hairpin_scaled": "Hairpin",
    "monza_scaled": "Monza",
}


E2_ALGORITHMS = [
    "rule_expert_gate",
    "ppo_continuous",
    "dlc_joint_transition",
    "dlc_joint_transition_observer",
    PROPOSED,
]

E3_ALGORITHMS = [
    "rule_expert_gate",
    "ppo_continuous",
    "dlc_joint_transition",
    PROPOSED,
]

E4_ALGORITHMS = [
    "rule_expert_gate",
    "rule_safety_gate",
    "ppo_continuous",
    "sac_continuous",
    "td3_continuous",
    "dlc_individual_transition",
    "dlc_joint_transition",
    "dlc_joint_transition_observer",
    PROPOSED,
]

E6_ALGORITHMS = [
    "w_o_dynamic_neighborhood",
    "w_o_interaction_neighbor_selection",
    "w_o_quality_proposal",
    "w_o_risk_penalty",
    "w_o_safety_quality_terms",
    "w_o_overtake_aware_planner",
    "low_budget_planner",
    PROPOSED_E6,
]


def finite_float(value, default=np.nan):
    if value in (None, "", "NA", "N/A", "nan", "NaN"):
        return default
    try:
        out = float(value)
    except (TypeError, ValueError):
        return default
    if math.isnan(out) or math.isinf(out):
        return default
    return out


def bootstrap_ci(values, n_boot=3000, seed=20260627):
    arr = np.asarray([finite_float(v) for v in values], dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        return np.nan, np.nan, np.nan
    mean = float(arr.mean())
    if arr.size == 1:
        return mean, mean, mean
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, arr.size, size=(n_boot, arr.size))
    boot = arr[idx].mean(axis=1)
    lo, hi = np.quantile(boot, [0.025, 0.975])
    return mean, float(lo), float(hi)


def ensure_dirs(root):
    root = Path(root)
    for name in ["figures", "tables", "materials", "captions"]:
        (root / name).mkdir(parents=True, exist_ok=True)


def save_figure(fig, stem):
    stem = Path(stem)
    stem.parent.mkdir(parents=True, exist_ok=True)
    outputs = {}
    for ext in ["svg", "pdf", "png", "tiff"]:
        path = stem.with_suffix(f".{ext}")
        fig.savefig(path, dpi=600, bbox_inches="tight")
        outputs[ext] = str(path)
    return outputs


def load_summary_rows(experiment_root, experiment_name):
    rows = []
    root = Path(experiment_root)
    if not root.exists():
        return pd.DataFrame()
    for path in sorted(root.glob("**/summaries/*.summary.json")):
        try:
            row = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        row = flatten_summary(row)
        row["experiment"] = experiment_name
        row["summary_path"] = str(path)
        row["trace_path"] = str(path).replace("/summaries/", "/traces/").replace(".summary.json", ".trace.json")
        row["track_label"] = infer_track_label(row, path)
        rows.append(row)
    return pd.DataFrame(rows)


def flatten_summary(row):
    out = {}
    for key, value in row.items():
        if isinstance(value, (str, int, float, bool)) or value is None:
            out[key] = value
    out["target_grass_rate"] = finite_float(row.get("target_grass_rate"))
    out["completion_time_capped"] = finite_float(row.get("time_to_first_overtake"), finite_float(row.get("finish_step")))
    if not np.isfinite(out["completion_time_capped"]):
        out["completion_time_capped"] = finite_float(row.get("steps_run"))
    out["grass_excursion_rate"] = finite_float(row.get("target_grass_rate"))
    out["desirable_overtake_rate"] = finite_float(row.get("elegant_overtake_rate"))
    out["successful_overtake_episode"] = int(bool(row.get("overtake_success_rate", 0.0)))
    return out


def infer_track_label(row, path):
    for part in Path(path).parts:
        if part in TRACK_LABELS:
            return TRACK_LABELS[part]
    track_path = str(row.get("track_path", ""))
    stem = Path(track_path).stem
    return TRACK_LABELS.get(stem, stem or "Procedural")


def write_dataframe(df, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    return str(path)


def track_arrays(track_path):
    path = Path(track_path)
    if not path.exists():
        path = Path("tracks") / path.name
    if not path.exists():
        return None
    data = np.load(path, allow_pickle=True)
    return {key: data[key] for key in data.files}


def plot_track(ax, track, color="#111827", lw=0.65, alpha=0.7):
    if not track:
        return
    for key, line_alpha, line_width in [("left", alpha, lw), ("right", alpha, lw), ("center", 0.18, 0.45)]:
        if key not in track:
            continue
        arr = np.asarray(track[key])
        ax.plot(arr[:, 0], arr[:, 1], color=color, lw=line_width, alpha=line_alpha, zorder=3 if key != "center" else 1)
    if "left" in track and "right" in track:
        left = np.asarray(track["left"])
        right = np.asarray(track["right"])
        poly = np.vstack([left, right[::-1]])
        ax.fill(poly[:, 0], poly[:, 1], color="#E5E7EB", alpha=0.45, zorder=0)


def trace_target_xy(trace_path, target_agent=None, stride=1):
    path = Path(trace_path)
    if not path.exists():
        return np.empty((0, 2), dtype=float)
    try:
        trace = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return np.empty((0, 2), dtype=float)
    if not trace:
        return np.empty((0, 2), dtype=float)
    if target_agent is None:
        target_agent = len(trace[0].get("positions", [])) - 1
    pts = []
    for row in trace[:: max(1, stride)]:
        positions = row.get("positions", [])
        if target_agent < len(positions):
            pts.append(positions[target_agent])
    return np.asarray(pts, dtype=float)


def e2_trajectory_density(df, out_root):
    if df.empty:
        return {}
    candidates = ["Hairpin", "Monza", "S-Curve", "Oval"]
    chosen_track = next((t for t in candidates if (df["track_label"] == t).any()), None)
    if not chosen_track:
        return {}
    base_algo = "dlc_joint_transition" if (df["algorithm"] == "dlc_joint_transition").any() else "ppo_continuous"
    panels = [(base_algo, f"{label_for_algorithm(base_algo)} trajectories"), (PROPOSED, "Proposed trajectories")]
    track_path = df.loc[df["track_label"] == chosen_track, "track_path"].dropna().astype(str)
    track = track_arrays(track_path.iloc[0]) if not track_path.empty else None

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.2), sharex=True, sharey=True)
    source_rows = []
    for ax, (algo, title) in zip(axes, panels):
        sub = df[(df["track_label"] == chosen_track) & (df["algorithm"] == algo)].sort_values("seed").head(100)
        all_pts = []
        plot_track(ax, track)
        for _, row in sub.iterrows():
            pts = trace_target_xy(row["trace_path"], target_agent=int(row.get("target_agent", row.get("num_agents", 1) - 1)), stride=2)
            if pts.size == 0:
                continue
            all_pts.append(pts)
            ax.plot(pts[:, 0], pts[:, 1], color=color_for_algorithm(algo), alpha=0.18, lw=0.55, zorder=4)
            for step_id, xy in enumerate(pts[::20]):
                source_rows.append(
                    {
                        "panel": title,
                        "track": chosen_track,
                        "algorithm": algo,
                        "seed": row.get("seed"),
                        "sample_index": step_id,
                        "x": xy[0],
                        "y": xy[1],
                    }
                )
        if all_pts:
            pts = np.vstack(all_pts)
            ax.hist2d(pts[:, 0], pts[:, 1], bins=80, cmap="Reds" if algo != PROPOSED else "Blues", alpha=0.34, zorder=2)
        ax.set_title(title, loc="left", fontsize=8.0, fontweight="bold")
        ax.set_aspect("equal", adjustable="box")
        ax.set_xlabel("x position")
        ax.grid(False)
    axes[0].set_ylabel("y position")
    fig.subplots_adjust(left=0.075, right=0.995, top=0.9, bottom=0.13, wspace=0.08)
    stem = Path(out_root) / "figures" / "figure_e2_environment_trajectory_density"
    outputs = save_figure(fig, stem)
    plt.close(fig)
    source = write_dataframe(pd.DataFrame(source_rows), Path(out_root) / "tables" / "figure_e2_trajectory_density_source_data.csv")
    return {"figure_e2_trajectory_density": outputs, "source_e2_trajectory_density": source, "track": chosen_track}


def format_value(value, metric, best=False):
    if not np.isfinite(value):
        text = "N/A"
    elif metric.endswith("rate"):
        text = f"{100.0 * value:.1f}"
    elif metric == "completion_time_capped":
        text = f"{value:.1f}"
    else:
        text = f"{value:.3f}"
    return f"\\textbf{{{text}}}" if best and text != "N/A" else text


def e2_comprehensive_table(df, out_root):
    if df.empty:
        return {}
    metrics = [
        ("overtake_success_rate", "Success (\\%)", True),
        ("completion_time_capped", "Time (steps)", False),
        ("target_grass_rate", "Grass rate (\\%)", False),
    ]
    rows = []
    for (track, algo), sub in df.groupby(["track_label", "algorithm"], dropna=False):
        if algo not in E2_ALGORITHMS:
            continue
        row = {
            "track": track,
            "algorithm": algo,
            "algorithm_label": label_for_algorithm(algo),
            "n": int(len(sub)),
        }
        for metric, _, _ in metrics:
            vals = sub[metric].dropna().to_numpy(dtype=float)
            row[metric] = float(vals.mean()) if vals.size else np.nan
        rows.append(row)
    table = pd.DataFrame(rows)
    if table.empty:
        return {}
    table["algorithm_order"] = table["algorithm"].map({a: i for i, a in enumerate(E2_ALGORITHMS)})
    table["track_order"] = table["track"].map({"Oval": 0, "S-Curve": 1, "Hairpin": 2, "Monza": 3}).fillna(99)
    table = table.sort_values(["track_order", "algorithm_order"])
    source = write_dataframe(table.drop(columns=["algorithm_order", "track_order"]), Path(out_root) / "tables" / "e2_environment_generalization_summary.csv")

    lines = [
        "\\begin{tabular}{llrrrr}",
        "\\toprule",
        "Track & Algorithm & $n$ & Success (\\%) $\\uparrow$ & Time (steps) $\\downarrow$ & Grass rate (\\%) $\\downarrow$ \\\\",
        "\\midrule",
    ]
    for track, sub in table.groupby("track", sort=False):
        best_success = sub["overtake_success_rate"].max()
        best_time = sub["completion_time_capped"].min()
        best_grass = sub["target_grass_rate"].min()
        for idx, row in sub.iterrows():
            track_text = track if idx == sub.index[0] else ""
            lines.append(
                f"{track_text} & {row['algorithm_label']} & {int(row['n'])} & "
                f"{format_value(row['overtake_success_rate'], 'overtake_success_rate', np.isclose(row['overtake_success_rate'], best_success, equal_nan=False))} & "
                f"{format_value(row['completion_time_capped'], 'completion_time_capped', np.isclose(row['completion_time_capped'], best_time, equal_nan=False))} & "
                f"{format_value(row['target_grass_rate'], 'target_grass_rate', np.isclose(row['target_grass_rate'], best_grass, equal_nan=False))} \\\\"
            )
        lines.append("\\addlinespace")
    if lines[-1] == "\\addlinespace":
        lines.pop()
    lines += ["\\bottomrule", "\\end{tabular}"]
    tex_path = Path(out_root) / "tables" / "table_e2_environment_generalization.tex"
    tex_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"table_e2_environment_generalization": str(tex_path), "source_e2_summary": source}


def e3_scale_plot(df, out_root):
    if df.empty:
        return {}
    df = df[df["algorithm"].isin(E3_ALGORITHMS)].copy()
    if df.empty:
        return {}

    def panel(ax, metric, title, ylabel, percent=False):
        ax.axvspan(3.5, 6.5, color="#9CA3AF", alpha=0.14, lw=0)
        ax.text(5.0, 0.965, "Training Distribution", transform=ax.get_xaxis_transform(), ha="center", va="top", fontsize=6.0)
        ax.text(10.0, 0.965, "Zero-Shot Extrapolation", transform=ax.get_xaxis_transform(), ha="center", va="top", fontsize=6.0)
        for algo in E3_ALGORITHMS:
            sub = df[df["algorithm"] == algo]
            xs, means, lows, highs = [], [], [], []
            for n, group in sorted(sub.groupby("num_agents")):
                vals = group[metric].dropna().to_numpy(dtype=float)
                if percent:
                    vals = vals * 100.0
                mean, lo, hi = bootstrap_ci(vals)
                if not np.isfinite(mean):
                    continue
                xs.append(int(n))
                means.append(mean)
                lows.append(lo)
                highs.append(hi)
            if not xs:
                continue
            xs = np.asarray(xs)
            means = np.asarray(means)
            lows = np.asarray(lows)
            highs = np.asarray(highs)
            ax.plot(xs, means, marker="o", ms=3.2, lw=1.45, color=color_for_algorithm(algo), label=label_for_algorithm(algo))
            ax.fill_between(xs, lows, highs, color=color_for_algorithm(algo), alpha=0.16, lw=0)
        ax.set_title(title, loc="left", fontsize=8.0, fontweight="bold")
        ax.set_xlabel("Number of vehicles")
        ax.set_ylabel(ylabel)
        ax.set_xticks([4, 6, 8, 10, 12])
        if percent:
            ax.set_ylim(-3, 103)
        ax.grid(axis="y", color="#E5E7EB", lw=0.55)
        ax.set_axisbelow(True)

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.9))
    panel(axes[0], "overtake_success_rate", "a  Overtaking success under scale extrapolation", "Rate (%)", True)
    panel(axes[1], "compute_latency_ms", "b  Online inference latency", "Latency (ms)", False)
    handles = [Line2D([0], [0], color=color_for_algorithm(a), lw=1.6, marker="o", ms=3.2, label=label_for_algorithm(a)) for a in E3_ALGORITHMS]
    fig.legend(handles=handles, ncol=len(handles), loc="upper center", bbox_to_anchor=(0.5, 1.01), fontsize=6.2, frameon=False, columnspacing=0.9)
    fig.subplots_adjust(left=0.075, right=0.995, top=0.80, bottom=0.18, wspace=0.27)
    stem = Path(out_root) / "figures" / "figure_e3_zero_shot_scale_extrapolation"
    outputs = save_figure(fig, stem)
    plt.close(fig)
    source = write_dataframe(df, Path(out_root) / "tables" / "figure_e3_scale_extrapolation_source_data.csv")
    return {"figure_e3_scale_extrapolation": outputs, "source_e3_scale": source}


def load_e1_metric_source(path):
    path = Path(path)
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def e4_radar(e1_long, out_root):
    if e1_long.empty:
        return {}
    records = []
    for algo in E4_ALGORITHMS:
        sub = e1_long[e1_long["algorithm"] == algo]
        if sub.empty:
            continue
        def mean_metric(metric, only_included=False):
            m = sub[sub["metric"] == metric]
            if only_included and "included_in_metric" in m.columns:
                m = m[m["included_in_metric"].astype(str).isin(["1", "True", "true"])]
            vals = pd.to_numeric(m["value_raw"], errors="coerce").dropna()
            return float(vals.mean()) if len(vals) else np.nan
        completion = mean_metric("completion_time_capped", only_included=True)
        grass = mean_metric("target_grass_rate", only_included=True)
        records.append(
            {
                "algorithm": algo,
                "label": label_for_algorithm(algo),
                "Success": mean_metric("overtake_success_rate"),
                "On-track": mean_metric("on_track_overtake_rate"),
                "Desirable": mean_metric("elegant_overtake_rate"),
                "completion_time": completion,
                "Efficiency": 100.0 / completion if np.isfinite(completion) and completion > 0 else np.nan,
                "Safety": 1.0 - grass if np.isfinite(grass) else np.nan,
            }
        )
    radar = pd.DataFrame(records)
    if radar.empty:
        return {}
    for metric in ["Efficiency", "Safety"]:
        max_value = radar[metric].max(skipna=True)
        if np.isfinite(max_value) and max_value > 0:
            radar[metric] = radar[metric] / max_value
    metrics = ["Success", "On-track", "Desirable", "Efficiency", "Safety"]
    angles = np.linspace(0, 2 * np.pi, len(metrics), endpoint=False).tolist()
    angles += angles[:1]
    fig = plt.figure(figsize=(4.2, 4.0))
    ax = fig.add_subplot(111, polar=True)
    for _, row in radar.iterrows():
        vals = [finite_float(row[m], 0.0) for m in metrics]
        vals += vals[:1]
        algo = row["algorithm"]
        lw = 2.1 if algo == PROPOSED else 0.95
        alpha = 0.32 if algo == PROPOSED else 0.0
        linestyle = "-" if algo == PROPOSED else "--"
        ax.plot(angles, vals, color=color_for_algorithm(algo), lw=lw, linestyle=linestyle, label=row["label"])
        if algo == PROPOSED:
            ax.fill(angles, vals, color=color_for_algorithm(algo), alpha=alpha)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(metrics, fontsize=7.0)
    ax.set_ylim(0, 1.02)
    ax.set_yticks([0.25, 0.5, 0.75, 1.0])
    ax.set_yticklabels(["0.25", "0.50", "0.75", "1.00"], fontsize=6.0)
    ax.grid(color="#D1D5DB", lw=0.55)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.08), ncol=3, fontsize=5.8, frameon=False)
    stem = Path(out_root) / "figures" / "figure_e4_direct_comparison_radar"
    outputs = save_figure(fig, stem)
    plt.close(fig)
    source = write_dataframe(radar, Path(out_root) / "tables" / "figure_e4_radar_source_data.csv")
    return {"figure_e4_radar": outputs, "source_e4_radar": source}


def load_trace(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return []


def choose_mechanism_trace(df):
    if df.empty:
        return None, []
    sub = df[(df["algorithm"] == PROPOSED) & (df["overtake_success_rate"] > 0)]
    for track in ["Hairpin", "Monza", "S-Curve", "Oval"]:
        cand = sub[sub["track_label"] == track].sort_values(["elegant_overtake_rate", "overtake_success_rate"], ascending=False)
        for _, row in cand.iterrows():
            trace = load_trace(row["trace_path"])
            if len(trace) > 20:
                return row, trace
    for _, row in sub.iterrows():
        trace = load_trace(row["trace_path"])
        if len(trace) > 20:
            return row, trace
    return None, []


def extract_snapshot_indices(trace, summary_row):
    if not trace:
        return []
    start = finite_float(summary_row.get("overtake_start_step"), np.nan) if summary_row is not None else np.nan
    complete = finite_float(summary_row.get("time_to_first_overtake"), np.nan) if summary_row is not None else np.nan
    max_idx = len(trace) - 1
    if np.isfinite(start) and np.isfinite(complete) and complete > start:
        raw = [int(start), int((start + complete) / 2), int(complete)]
    else:
        raw = [int(0.12 * max_idx), int(0.45 * max_idx), int(0.78 * max_idx)]
    steps = [int(trace[min(max(i - 1, 0), max_idx)].get("step", i)) for i in raw]
    return steps


def nearest_trace_row(trace, step):
    return min(trace, key=lambda row: abs(int(row.get("step", 0)) - step))


def risk_proxy(row, target_agent):
    lateral = 0.0
    grass = 0.0
    try:
        lateral = abs(float(row["telemetry"]["lateral_error"][target_agent]))
        grass = float(bool(row["telemetry"]["on_grass"][target_agent]))
    except Exception:
        pass
    close = max(0.0, 5.0 - finite_float(row.get("min_pair_distance"), 5.0)) / 5.0
    debug = row.get("target_policy_debug", {}) or {}
    geom = debug.get("geometry_context", {}) if isinstance(debug, dict) else {}
    curvature = abs(finite_float(geom.get("curvature"), 0.0))
    return 0.45 * lateral + 0.35 * close + 0.80 * grass + 0.25 * curvature


def e5_mechanism_figure(df, out_root):
    summary_row, trace = choose_mechanism_trace(df)
    if summary_row is None or not trace:
        return {}
    target_agent = int(summary_row.get("target_agent", summary_row.get("num_agents", 1) - 1))
    steps = extract_snapshot_indices(trace, summary_row)
    track = track_arrays(summary_row.get("track_path", ""))
    fig = plt.figure(figsize=(7.25, 4.35))
    gs = fig.add_gridspec(2, 3, height_ratios=[1.25, 0.82], hspace=0.36, wspace=0.12)
    labels = ["Approach", "Side-by-side", "Pass completed"]
    source_rows = []
    for col, step in enumerate(steps):
        ax = fig.add_subplot(gs[0, col])
        row = nearest_trace_row(trace, step)
        positions = np.asarray(row.get("positions", []), dtype=float)
        plot_track(ax, track)
        if positions.size:
            neighbors = []
            all_neighbors = row.get("dynamic_neighbor_ids", [])
            if target_agent < len(all_neighbors):
                neighbors = list(all_neighbors[target_agent])[:3]
            for idx, xy in enumerate(positions):
                if idx == target_agent:
                    color, size, z = "#B91C1C", 28, 8
                elif idx in neighbors:
                    color, size, z = "#D97706", 22, 7
                else:
                    color, size, z = "#9CA3AF", 15, 5
                ax.scatter([xy[0]], [xy[1]], s=size, color=color, edgecolor="white", lw=0.35, zorder=z)
                source_rows.append(
                    {
                        "panel": labels[col],
                        "step": row.get("step"),
                        "agent_id": idx,
                        "x": xy[0],
                        "y": xy[1],
                        "is_ego": int(idx == target_agent),
                        "highlighted_top3_neighbor": int(idx in neighbors),
                    }
                )
            ego = positions[target_agent]
            for nid in neighbors:
                if nid < len(positions):
                    nb = positions[nid]
                    ax.plot([ego[0], nb[0]], [ego[1], nb[1]], color="#D97706", lw=0.75, ls=(0, (2, 1.8)), alpha=0.9, zorder=6)
        ax.set_title(f"{chr(97 + col)}  {labels[col]} (t={row.get('step')} steps)", loc="left", fontsize=8.0, fontweight="bold")
        ax.set_aspect("equal", adjustable="box")
        ax.set_xticks([])
        ax.set_yticks([])
    ax_ts = fig.add_subplot(gs[1, :])
    ts_steps = [int(row.get("step", i)) for i, row in enumerate(trace)]
    risks = [risk_proxy(row, target_agent) for row in trace]
    grass = []
    lateral = []
    for row in trace:
        try:
            grass.append(float(bool(row["telemetry"]["on_grass"][target_agent])))
            lateral.append(abs(float(row["telemetry"]["lateral_error"][target_agent])))
        except Exception:
            grass.append(np.nan)
            lateral.append(np.nan)
    ax_ts.plot(ts_steps, risks, color="#B91C1C", lw=1.2, label="Interaction-risk proxy")
    ax_ts.plot(ts_steps, lateral, color=color_for_algorithm(PROPOSED), lw=1.0, alpha=0.85, label="Absolute lateral error")
    for step in steps:
        ax_ts.axvline(step, color="#111827", lw=0.65, ls="--", alpha=0.5)
    ax_ts.set_title("d  Temporal decision context", loc="left", fontsize=8.0, fontweight="bold")
    ax_ts.set_xlabel("Online step")
    ax_ts.set_ylabel("Normalized proxy")
    ax_ts.grid(axis="y", color="#E5E7EB", lw=0.55)
    ax_ts.legend(ncol=2, loc="upper right", fontsize=6.2, frameon=False)
    for step, risk, lat, gr in zip(ts_steps[:: max(1, len(ts_steps) // 400)], risks[:: max(1, len(ts_steps) // 400)], lateral[:: max(1, len(ts_steps) // 400)], grass[:: max(1, len(ts_steps) // 400)]):
        source_rows.append({"panel": "time_series", "step": step, "risk_proxy": risk, "abs_lateral_error": lat, "target_on_grass": gr})
    fig.subplots_adjust(left=0.055, right=0.995, top=0.96, bottom=0.1)
    stem = Path(out_root) / "figures" / "figure_e5_mechanism_semantic_snapshots"
    outputs = save_figure(fig, stem)
    plt.close(fig)
    source = write_dataframe(pd.DataFrame(source_rows), Path(out_root) / "tables" / "figure_e5_mechanism_source_data.csv")
    return {"figure_e5_mechanism": outputs, "source_e5_mechanism": source}


def e6_ablation(df, out_root):
    if df.empty:
        return {}
    df = df[df["algorithm"].isin(E6_ALGORITHMS)].copy()
    if df.empty:
        return {}
    order = [a for a in E6_ALGORITHMS if a in set(df["algorithm"])]
    fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.05))

    means, lows, highs = [], [], []
    for algo in order:
        vals = df[df["algorithm"] == algo]["overtake_success_rate"].dropna().to_numpy(dtype=float) * 100.0
        mean, lo, hi = bootstrap_ci(vals)
        means.append(mean)
        lows.append(max(mean - lo, 0.0) if np.isfinite(mean) and np.isfinite(lo) else 0.0)
        highs.append(max(hi - mean, 0.0) if np.isfinite(mean) and np.isfinite(hi) else 0.0)
    x = np.arange(len(order))
    axes[0].bar(x, means, color=[color_for_algorithm(a) for a in order], edgecolor="#111827", lw=0.45)
    axes[0].errorbar(x, means, yerr=np.asarray([lows, highs]), fmt="none", color="#111827", lw=0.65, capsize=2.0)
    axes[0].set_title("a  High-pressure ablation success", loc="left", fontsize=8.0, fontweight="bold")
    axes[0].set_ylabel("Rate (%)")
    axes[0].set_ylim(0, 104)
    axes[0].set_xticks(x)
    axes[0].set_xticklabels([label_for_algorithm(a) for a in order], rotation=32, ha="right")
    for tick, algo in zip(axes[0].get_xticklabels(), order):
        if algo == PROPOSED_E6:
            tick.set_fontweight("bold")
    axes[0].grid(axis="y", color="#E5E7EB", lw=0.55)

    for algo in order:
        sub = df[df["algorithm"] == algo]
        axes[1].scatter(
            sub["completion_time_capped"],
            sub["target_grass_rate"],
            s=14 if algo == PROPOSED_E6 else 11,
            color=color_for_algorithm(algo),
            alpha=0.72 if algo == PROPOSED_E6 else 0.48,
            edgecolor="white",
            lw=0.25,
            label=label_for_algorithm(algo),
        )
    axes[1].set_title("b  Time-risk Pareto frontier", loc="left", fontsize=8.0, fontweight="bold")
    axes[1].set_xlabel("Completion time (steps, lower is better)")
    axes[1].set_ylabel("Grass excursion rate (lower is better)")
    axes[1].grid(axis="both", color="#E5E7EB", lw=0.55)
    axes[1].legend(ncol=2, loc="upper right", fontsize=5.6, frameon=False, handletextpad=0.2, columnspacing=0.6)
    fig.subplots_adjust(left=0.075, right=0.995, top=0.9, bottom=0.28, wspace=0.30)
    stem = Path(out_root) / "figures" / "figure_e6_high_pressure_ablation"
    outputs = save_figure(fig, stem)
    plt.close(fig)
    source = write_dataframe(df, Path(out_root) / "tables" / "figure_e6_ablation_source_data.csv")
    return {"figure_e6_ablation": outputs, "source_e6_ablation": source}


def write_captions(out_root):
    captions = {
        "figure_e2_environment_generalization_caption.tex": (
            "Environmental generalization is evaluated with six vehicles on Oval, S-Curve, Hairpin and Monza tracks. "
            "The trajectory-density panels overlay up to 100 online ego trajectories on the selected held-out track, "
            "and the accompanying table reports success rate, completion time and grass-excursion rate for all evaluated tracks."
        ),
        "figure_e3_scale_extrapolation_caption.tex": (
            "Zero-shot scale extrapolation is evaluated by varying the number of vehicles from 4 to 12 under density-controlled track scaling. "
            "The shaded 4-6 vehicle region denotes the training distribution; 8-12 vehicles denote extrapolation. "
            "Lines show means and shaded bands show bootstrap 95% confidence intervals."
        ),
        "figure_e4_direct_comparison_caption.tex": (
            "Direct comparison radar plot summarizes five normalized endpoints: success, on-track overtaking, "
            "Desirable overtaking behavior, efficiency and safety. Larger enclosed area indicates stronger all-round performance."
        ),
        "figure_e5_mechanism_caption.tex": (
            "Mechanism visualization for a representative online overtaking episode. The top panels show semantic snapshots; "
            "the red marker is the ego vehicle and orange markers/edges denote the top-3 interaction-relevant neighbors highlighted for interpretability. "
            "The deployed dynamic graph uses all in-range neighbors rather than a fixed top-k limit."
        ),
        "figure_e6_ablation_caption.tex": (
            "High-pressure ablation study on dense multi-vehicle tracks. Panel a reports overtaking success, while panel b plots "
            "completion time against grass-excursion risk; points closer to the lower-left corner are more efficient and safer."
        ),
    }
    outputs = {}
    for name, text in captions.items():
        path = Path(out_root) / "captions" / name
        path.write_text(text + "\n", encoding="utf-8")
        outputs[name] = str(path)
    return outputs


def manifest_counts(df):
    if df.empty:
        return {}
    out = {}
    for (algorithm, track, n), sub in df.groupby(["algorithm", "track_label", "num_agents"], dropna=False):
        out[f"{algorithm}|{track}|n{n}"] = int(len(sub))
    return out


def main():
    parser = argparse.ArgumentParser(description="Export revised top-journal experiment figures.")
    parser.add_argument("--root", default="outputs/tits_dynamic_graph_expanded/topjournal_revised_protocol")
    parser.add_argument("--e1-source", default="outputs/tits_dynamic_graph_expanded/geometry_generalization_six_experiments/e1_200_summary/tables/online_benchmark_nature_direct_source_data.csv")
    args = parser.parse_args()

    configure_publication_matplotlib(font_size=7.0)
    root = Path(args.root)
    ensure_dirs(root)

    e2 = load_summary_rows(root / "e2_environment_generalization", "E2_environment_generalization")
    e3 = load_summary_rows(root / "e3_scale_extrapolation", "E3_scale_extrapolation")
    e6 = load_summary_rows(root / "e6_high_pressure_ablation", "E6_high_pressure_ablation")
    e1 = load_e1_metric_source(args.e1_source)

    outputs = {}
    if not e2.empty:
        outputs.update(e2_trajectory_density(e2, root))
        outputs.update(e2_comprehensive_table(e2, root))
        outputs["source_e2_all_summaries"] = write_dataframe(e2, root / "tables" / "e2_environment_generalization_all_summaries.csv")
    if not e3.empty:
        outputs.update(e3_scale_plot(e3, root))
        outputs["source_e3_all_summaries"] = write_dataframe(e3, root / "tables" / "e3_scale_extrapolation_all_summaries.csv")
    if not e1.empty:
        outputs.update(e4_radar(e1, root))
    if not e2.empty:
        outputs.update(e5_mechanism_figure(e2, root))
    if not e6.empty:
        outputs.update(e6_ablation(e6, root))
        outputs["source_e6_all_summaries"] = write_dataframe(e6, root / "tables" / "e6_high_pressure_ablation_all_summaries.csv")
    outputs.update(write_captions(root))

    manifest = {
        "root": str(root),
        "e2_summary_rows": int(len(e2)),
        "e3_summary_rows": int(len(e3)),
        "e6_summary_rows": int(len(e6)),
        "e2_case_counts": manifest_counts(e2),
        "e3_case_counts": manifest_counts(e3),
        "e6_case_counts": manifest_counts(e6),
        "outputs": outputs,
        "notes": [
            "All figures use Python/matplotlib in the vlm_planner environment.",
            "E5 highlights top-3 neighbors only for interpretability; the online dynamic graph uses all in-range neighbors.",
            "The script can be rerun after online experiments complete to refresh the figures and source data.",
        ],
    }
    manifest_path = root / "topjournal_revised_export_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
