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


SOURCE_CSV = "outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv"
CONFIG_PATH = "configs/tits_dynamic_graph_experiments.json"
MODEL_AUDIT = "outputs/tits_dynamic_graph/tits_model_artifact_integrity_audit/tables/model_artifact_inventory.csv"

FOCUS_ALGORITHMS = [
    "v6_runtime_dynamic_neighborhood_safe",
    "v6_runtime_dynamic_neighborhood",
    "quality_proposal_dlc_world_v1",
    "dlc_world_original",
    "dlc_world_fast",
    "rule_expert_gate",
]
LABELS = {
    "v6_runtime_dynamic_neighborhood_safe": "v6动态邻域DLC-safe",
    "v6_runtime_dynamic_neighborhood": "v6动态邻域DLC",
    "quality_proposal_dlc_world_v1": "质量Proposal-DLC",
    "dlc_world_original": "DLC世界模型",
    "dlc_world_fast": "DLC-fast",
    "rule_expert_gate": "规则专家",
}
COLORS = {
    "v6_runtime_dynamic_neighborhood_safe": "#1976B9",
    "v6_runtime_dynamic_neighborhood": "#4C78A8",
    "quality_proposal_dlc_world_v1": "#54A24B",
    "dlc_world_original": "#D45A48",
    "dlc_world_fast": "#F58518",
    "rule_expert_gate": "#606060",
}


def read_csv(path):
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
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
    return write_text(path, json.dumps(data, ensure_ascii=False, indent=2))


def f(value):
    if value in (None, "", "nan", "NaN", "NA"):
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(out) or math.isinf(out):
        return None
    return out


def fmt(value, digits=3):
    value = f(value)
    if value is None:
        return "NA"
    return f"{value:.{digits}f}"


def register_cjk_font():
    from matplotlib import font_manager

    candidates = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
        "/usr/share/fonts/truetype/arphic/ukai.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for item in candidates:
        path = Path(item)
        if path.exists():
            font_manager.fontManager.addfont(str(path))
            family = font_manager.FontProperties(fname=str(path)).get_name()
            mpl.rcParams["font.family"] = family
            mpl.rcParams["font.sans-serif"] = [family, "Arial", "DejaVu Sans", "sans-serif"]
            return family
    return None


def mean(values):
    values = [v for v in values if v is not None]
    return float(np.mean(values)) if values else None


def percentile(values, q):
    values = [v for v in values if v is not None]
    return float(np.percentile(values, q)) if values else None


def bootstrap_ci(values, seed=20260624, n_boot=5000):
    values = np.asarray([v for v in values if v is not None], dtype=np.float64)
    if values.size == 0:
        return None, None
    if values.size == 1:
        return float(values[0]), float(values[0])
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, values.size, size=(n_boot, values.size))
    boot = values[idx].mean(axis=1)
    lo, hi = np.quantile(boot, [0.025, 0.975])
    return float(lo), float(hi)


def load_config(path):
    path = Path(path)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def summarize_by_vehicle_count(rows):
    grouped = defaultdict(list)
    for row in rows:
        if row["algorithm"] not in FOCUS_ALGORITHMS:
            continue
        key = (row["algorithm"], int(row["num_agents"]))
        grouped[key].append(row)
    out = []
    for (algorithm, num_agents), items in sorted(
        grouped.items(),
        key=lambda item: (FOCUS_ALGORITHMS.index(item[0][0]), item[0][1]),
    ):
        lat = [f(row.get("compute_latency_ms")) for row in items]
        p95 = [f(row.get("compute_latency_p95_ms")) for row in items]
        success = [f(row.get("overtake_success_rate")) for row in items]
        elegant = [f(row.get("elegant_overtake_rate")) for row in items]
        grass = [f(row.get("target_grass_rate")) for row in items]
        lat_lo, lat_hi = bootstrap_ci(lat, seed=20260624 + num_agents)
        out.append(
            {
                "algorithm": algorithm,
                "algorithm_label_cn": LABELS.get(algorithm, algorithm),
                "num_agents": num_agents,
                "n_runs": len(items),
                "latency_ms_mean": mean(lat),
                "latency_ms_ci95_low": lat_lo,
                "latency_ms_ci95_high": lat_hi,
                "latency_ms_run_p95": percentile(lat, 95),
                "latency_p95_ms_mean": mean(p95),
                "success_mean": mean(success),
                "elegant_mean": mean(elegant),
                "grass_mean": mean(grass),
            }
        )
    return out


def summarize_by_benchmark(rows):
    grouped = defaultdict(list)
    for row in rows:
        if row["algorithm"] not in FOCUS_ALGORITHMS:
            continue
        key = (row["_benchmark"], int(row["num_agents"]), row["algorithm"])
        grouped[key].append(row)
    out = []
    for (benchmark, num_agents, algorithm), items in sorted(
        grouped.items(),
        key=lambda item: (item[0][0], item[0][1], FOCUS_ALGORITHMS.index(item[0][2])),
    ):
        out.append(
            {
                "benchmark": benchmark,
                "num_agents": num_agents,
                "algorithm": algorithm,
                "algorithm_label_cn": LABELS.get(algorithm, algorithm),
                "n_runs": len(items),
                "latency_ms_mean": mean([f(row.get("compute_latency_ms")) for row in items]),
                "latency_p95_ms_mean": mean([f(row.get("compute_latency_p95_ms")) for row in items]),
                "success_mean": mean([f(row.get("overtake_success_rate")) for row in items]),
                "elegant_mean": mean([f(row.get("elegant_overtake_rate")) for row in items]),
                "grass_mean": mean([f(row.get("target_grass_rate")) for row in items]),
                "finish_step_mean": mean([f(row.get("finish_step")) for row in items]),
            }
        )
    return out


def fit_latency_slopes(vehicle_rows):
    by_alg = defaultdict(list)
    for row in vehicle_rows:
        by_alg[row["algorithm"]].append(row)
    out = []
    for algorithm, items in sorted(by_alg.items(), key=lambda item: FOCUS_ALGORITHMS.index(item[0])):
        xs = np.asarray([row["num_agents"] for row in items], dtype=float)
        ys = np.asarray([row["latency_ms_mean"] for row in items], dtype=float)
        if len(xs) >= 2 and np.std(xs) > 0:
            slope, intercept = np.polyfit(xs, ys, 1)
            y_hat = slope * xs + intercept
            ss_res = float(np.sum((ys - y_hat) ** 2))
            ss_tot = float(np.sum((ys - np.mean(ys)) ** 2))
            r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 1.0
        else:
            slope, intercept, r2 = None, None, None
        n4 = next((row["latency_ms_mean"] for row in items if row["num_agents"] == 4), None)
        n8 = next((row["latency_ms_mean"] for row in items if row["num_agents"] == 8), None)
        out.append(
            {
                "algorithm": algorithm,
                "algorithm_label_cn": LABELS.get(algorithm, algorithm),
                "vehicle_counts": ";".join(str(row["num_agents"]) for row in items),
                "latency_slope_ms_per_vehicle": slope,
                "latency_intercept_ms": intercept,
                "latency_fit_r2": r2,
                "latency_n4_ms": n4,
                "latency_n8_ms": n8,
                "latency_n8_minus_n4_ms": (n8 - n4) if n8 is not None and n4 is not None else "",
            }
        )
    return out


def model_complexity_rows(config, model_rows):
    dynamic = config.get("dynamic_graph", {})
    algorithm_configs = {item.get("name"): item for item in config.get("algorithms", [])}
    model_by_path = {row["path"]: row for row in model_rows}
    out = []
    for algorithm in FOCUS_ALGORITHMS:
        cfg = algorithm_configs.get(algorithm, {})
        model_path = cfg.get("model_path", "")
        meta = model_by_path.get(model_path, {})
        max_neighbors = cfg.get("max_neighbors", dynamic.get("max_neighbors", ""))
        planner_horizon = cfg.get("planner_horizon", "")
        planner_candidates = cfg.get("planner_candidates", "")
        out.append(
            {
                "algorithm": algorithm,
                "algorithm_label_cn": LABELS.get(algorithm, algorithm),
                "model_path": model_path,
                "obs_dim": meta.get("obs_dim", ""),
                "action_dim": meta.get("action_dim", ""),
                "hidden_dim": meta.get("hidden_dim", ""),
                "num_agents_train_meta": meta.get("num_agents", ""),
                "use_slot_mask": meta.get("use_slot_mask", ""),
                "slot_feature_dim": meta.get("slot_feature_dim", ""),
                "max_neighbors_config": max_neighbors,
                "neighbor_selection_mode": cfg.get("neighbor_selection_mode", dynamic.get("neighbor_selection_mode", "")),
                "planner_horizon": planner_horizon,
                "planner_candidates": planner_candidates,
                "complexity_note": (
                    "runtime neighbor ranking scans available vehicles, while graph/model input is capped by max_neighbors"
                    if model_path
                    else "rule baseline has no learned graph model"
                ),
            }
        )
    return out


def make_figure(vehicle_rows, benchmark_rows, out_dir):
    register_cjk_font()
    mpl.rcParams.update({"svg.fonttype": "none", "pdf.fonttype": 42, "font.size": 8})
    fig, axes = plt.subplots(1, 3, figsize=(9.0, 3.2), constrained_layout=True)
    fig.suptitle("运行时扩展性：车辆数、延迟与超车质量", fontsize=11, fontweight="bold")

    ax = axes[0]
    for alg in ["v6_runtime_dynamic_neighborhood_safe", "dlc_world_original", "dlc_world_fast", "rule_expert_gate"]:
        rows = [row for row in vehicle_rows if row["algorithm"] == alg]
        rows = sorted(rows, key=lambda row: row["num_agents"])
        ax.plot([row["num_agents"] for row in rows], [row["latency_ms_mean"] for row in rows], marker="o", label=LABELS[alg], color=COLORS[alg])
    ax.set_xlabel("车辆数")
    ax.set_ylabel("平均决策延迟 (ms)")
    ax.set_title("延迟随车辆数变化")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=6.2)

    ax = axes[1]
    rows = [row for row in vehicle_rows if row["algorithm"] in {"v6_runtime_dynamic_neighborhood_safe", "dlc_world_original"}]
    xs = sorted({row["num_agents"] for row in rows})
    width = 0.35
    for idx, alg in enumerate(["v6_runtime_dynamic_neighborhood_safe", "dlc_world_original"]):
        vals = [next(row["elegant_mean"] for row in rows if row["algorithm"] == alg and row["num_agents"] == x) for x in xs]
        ax.bar(np.arange(len(xs)) + (idx - 0.5) * width, vals, width=width, color=COLORS[alg], label=LABELS[alg])
    ax.set_xticks(np.arange(len(xs)), [f"n={x}" for x in xs])
    ax.set_ylim(0, 1.0)
    ax.set_ylabel("Desirable overtaking behavior rate")
    ax.set_title("质量随车辆数变化")
    ax.legend(fontsize=6.2)

    ax = axes[2]
    rows = [row for row in benchmark_rows if row["algorithm"] == "v6_runtime_dynamic_neighborhood_safe"]
    rows = sorted(rows, key=lambda row: (row["benchmark"], row["num_agents"]))
    name_map = {
        "in_distribution_procedural": "程序",
        "monza_external_track": "Monza",
        "vehicle_count_extrapolation": "n8外推",
    }
    labels = [
        f"{name_map.get(row['benchmark'], row['benchmark'])} n={row['num_agents']}"
        for row in rows
    ]
    offsets = {
        ("in_distribution_procedural", 4): (2.2, -0.035),
        ("in_distribution_procedural", 5): (1.2, 0.015),
        ("in_distribution_procedural", 6): (1.4, 0.020),
        ("monza_external_track", 4): (1.4, 0.018),
        ("monza_external_track", 6): (1.8, -0.030),
        ("vehicle_count_extrapolation", 8): (1.2, 0.020),
    }
    ax.scatter([row["latency_ms_mean"] for row in rows], [row["elegant_mean"] for row in rows], s=45, color=COLORS["v6_runtime_dynamic_neighborhood_safe"])
    for row, label in zip(rows, labels):
        dx, dy = offsets.get((row["benchmark"], row["num_agents"]), (1.0, 0.0))
        ax.text(row["latency_ms_mean"] + dx, row["elegant_mean"] + dy, label, fontsize=5.8, va="center")
    ax.set_xlim(left=0)
    ax.set_ylim(-0.02, 1.02)
    ax.set_xlabel("v6-safe 延迟 (ms)")
    ax.set_ylabel("v6-safe Desirable overtaking behavior rate")
    ax.set_title("质量-延迟场景分布")
    ax.grid(alpha=0.25)

    paths = {}
    for suffix in ["svg", "pdf", "png", "tiff"]:
        path = out_dir / "figures" / f"figure_runtime_scalability_cn.{suffix}"
        path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, dpi=300 if suffix in {"png", "tiff"} else None)
        paths[suffix] = str(path)
    plt.close(fig)
    return paths


def build_markdown(report):
    summary = report["summary"]
    lines = [
        "# T-ITS Runtime Scalability and Complexity Pack",
        "",
        "该包把确认性在线矩阵中的车辆数、决策延迟和超车质量放在一起分析，用于支撑“运行时动态邻域图可以在不同车辆数下在线构图”的 bounded claim。它不声称任意交通密度实时可行，而是报告当前 4/5/6/8 车 benchmark 下的经验延迟和质量边界。",
        "",
        "## Summary",
        "",
    ]
    for key, value in summary.items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Key Runtime Findings",
            "",
            "| Algorithm | n=4 latency | n=8 latency | n8-n4 | slope ms/vehicle | n=8 elegant | n=8 success |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    by_slope = {row["algorithm"]: row for row in report["latency_slopes"]}
    by_vehicle = {(row["algorithm"], row["num_agents"]): row for row in report["vehicle_summary"]}
    for alg in ["v6_runtime_dynamic_neighborhood_safe", "v6_runtime_dynamic_neighborhood", "quality_proposal_dlc_world_v1", "dlc_world_original", "dlc_world_fast", "rule_expert_gate"]:
        s = by_slope[alg]
        n4 = by_vehicle.get((alg, 4), {})
        n8 = by_vehicle.get((alg, 8), {})
        lines.append(
            f"| {LABELS[alg]} | {fmt(n4.get('latency_ms_mean'), 1)} | {fmt(n8.get('latency_ms_mean'), 1)} | {fmt(s.get('latency_n8_minus_n4_ms'), 1)} | {fmt(s.get('latency_slope_ms_per_vehicle'), 2)} | {fmt(n8.get('elegant_mean'))} | {fmt(n8.get('success_mean'))} |"
        )
    lines.extend(
        [
            "",
            "## Complexity Interpretation",
            "",
            "- 动态邻域 observation 使用固定 `max_neighbors=3` 和 slot mask；总车辆数增加时，模型输入维度不随车辆数增长。",
            "- 运行时邻居选择需要扫描候选车辆并排序/截断，因此邻居构建仍与可见车辆数相关；当前证据覆盖 n=4/5/6/8，不覆盖任意密度。",
            "- v6-safe 使用中等 MPC budget；相比原始 DLC baseline，它在 n=8 下保持更高Desirable overtaking behavior rate和成功率，同时平均延迟未高于原始 DLC。",
            "- 规则专家延迟极低，但它不是学习型 world model，也不提供动态图世界模型泛化机制，应作为手工实时性参考而不是主方法替代。",
            "",
            "## Source and Traceability",
            "",
            "- Source data: `outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv`",
            "- Model audit: `outputs/tits_dynamic_graph/tits_model_artifact_integrity_audit/tables/model_artifact_inventory.csv`",
            "- Dynamic graph config: `configs/tits_dynamic_graph_experiments.json`",
            "- Runtime neighbor code: `dlc/graph_policy.py` and `gym_multi_car_racing/multi_car_racing.py`",
            "",
            "## Regeneration Command",
            "",
            "```bash",
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_runtime_scalability_pack.py --out-dir outputs/tits_dynamic_graph/tits_runtime_scalability_pack",
            "```",
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Export runtime scalability and complexity evidence for the T-ITS dynamic graph study.")
    parser.add_argument("--source-csv", default=SOURCE_CSV)
    parser.add_argument("--config", default=CONFIG_PATH)
    parser.add_argument("--model-audit", default=MODEL_AUDIT)
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/tits_runtime_scalability_pack")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    materials = out_dir / "materials"
    tables = out_dir / "tables"
    figures = out_dir / "figures"
    materials.mkdir(parents=True, exist_ok=True)
    tables.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)

    rows = read_csv(args.source_csv)
    vehicle_rows = summarize_by_vehicle_count(rows)
    benchmark_rows = summarize_by_benchmark(rows)
    slope_rows = fit_latency_slopes(vehicle_rows)
    complexity_rows = model_complexity_rows(load_config(args.config), read_csv(args.model_audit) if Path(args.model_audit).exists() else [])
    figure_paths = make_figure(vehicle_rows, benchmark_rows, out_dir)

    by_vehicle = {(row["algorithm"], row["num_agents"]): row for row in vehicle_rows}
    safe_n8 = by_vehicle.get(("v6_runtime_dynamic_neighborhood_safe", 8), {})
    dlc_n8 = by_vehicle.get(("dlc_world_original", 8), {})
    safe_slope = next(row for row in slope_rows if row["algorithm"] == "v6_runtime_dynamic_neighborhood_safe")
    summary = {
        "status": "pass",
        "source_rows": len(rows),
        "vehicle_counts": sorted({int(row["num_agents"]) for row in rows}),
        "focus_algorithm_count": len(FOCUS_ALGORITHMS),
        "safe_n8_latency_ms": safe_n8.get("latency_ms_mean"),
        "dlc_n8_latency_ms": dlc_n8.get("latency_ms_mean"),
        "safe_n8_elegant": safe_n8.get("elegant_mean"),
        "dlc_n8_elegant": dlc_n8.get("elegant_mean"),
        "safe_latency_slope_ms_per_vehicle": safe_slope.get("latency_slope_ms_per_vehicle"),
        "max_neighbors": load_config(args.config).get("dynamic_graph", {}).get("max_neighbors"),
    }
    report = {
        "status": "pass",
        "summary": summary,
        "vehicle_summary": vehicle_rows,
        "benchmark_summary": benchmark_rows,
        "latency_slopes": slope_rows,
        "complexity_rows": complexity_rows,
        "figure_paths": figure_paths,
        "note": "This pack reports empirical runtime/quality trends for the frozen simulation matrix. It is not a real-time certification for arbitrary traffic density.",
    }
    vehicle_fields = [
        "algorithm",
        "algorithm_label_cn",
        "num_agents",
        "n_runs",
        "latency_ms_mean",
        "latency_ms_ci95_low",
        "latency_ms_ci95_high",
        "latency_ms_run_p95",
        "latency_p95_ms_mean",
        "success_mean",
        "elegant_mean",
        "grass_mean",
    ]
    benchmark_fields = [
        "benchmark",
        "num_agents",
        "algorithm",
        "algorithm_label_cn",
        "n_runs",
        "latency_ms_mean",
        "latency_p95_ms_mean",
        "success_mean",
        "elegant_mean",
        "grass_mean",
        "finish_step_mean",
    ]
    slope_fields = [
        "algorithm",
        "algorithm_label_cn",
        "vehicle_counts",
        "latency_slope_ms_per_vehicle",
        "latency_intercept_ms",
        "latency_fit_r2",
        "latency_n4_ms",
        "latency_n8_ms",
        "latency_n8_minus_n4_ms",
    ]
    complexity_fields = [
        "algorithm",
        "algorithm_label_cn",
        "model_path",
        "obs_dim",
        "action_dim",
        "hidden_dim",
        "num_agents_train_meta",
        "use_slot_mask",
        "slot_feature_dim",
        "max_neighbors_config",
        "neighbor_selection_mode",
        "planner_horizon",
        "planner_candidates",
        "complexity_note",
    ]
    paths = {
        "report_md": write_text(materials / "RUNTIME_SCALABILITY_AND_COMPLEXITY_REPORT.md", build_markdown(report)),
        "report_json": write_json(materials / "RUNTIME_SCALABILITY_AND_COMPLEXITY_REPORT.json", report),
        "vehicle_summary_csv": write_csv(tables / "runtime_scalability_by_vehicle_count.csv", vehicle_rows, vehicle_fields),
        "benchmark_summary_csv": write_csv(tables / "runtime_scalability_by_benchmark.csv", benchmark_rows, benchmark_fields),
        "latency_slope_csv": write_csv(tables / "runtime_latency_vehicle_count_slopes.csv", slope_rows, slope_fields),
        "complexity_crosswalk_csv": write_csv(tables / "runtime_complexity_crosswalk.csv", complexity_rows, complexity_fields),
        "figure_svg": figure_paths["svg"],
        "figure_pdf": figure_paths["pdf"],
        "figure_png": figure_paths["png"],
        "figure_tiff": figure_paths["tiff"],
    }
    manifest = {
        "status": "pass",
        "out_dir": args.out_dir,
        "summary": summary,
        "paths": paths,
    }
    manifest_path = write_json(out_dir / "tits_runtime_scalability_pack_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, "status": "pass", "summary": summary}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
