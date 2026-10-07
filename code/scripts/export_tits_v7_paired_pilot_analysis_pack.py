#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib import font_manager


FORMAL_SOURCE = "outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv"
V7_SOURCE = "outputs/tits_dynamic_graph/v7_elegance_barrier_pilot_matrix_summary/tables/online_benchmark_source_data.csv"
OUT_DIR = "outputs/tits_dynamic_graph/tits_v7_paired_pilot_analysis_pack"

V7 = "v7_elegance_barrier_dlc_world"
PRIMARY = "v6_runtime_dynamic_neighborhood_safe"
BASELINE = "dlc_world_original"
ALGORITHMS = [V7, PRIMARY, BASELINE]
LABELS_CN = {
    V7: "v7desirable behavior约束DLC",
    PRIMARY: "当前主方法",
    BASELINE: "DLC原始",
}
PAIRS = [
    (V7, PRIMARY, "v7_minus_current_safe"),
    (V7, BASELINE, "v7_minus_dlc_original"),
    (PRIMARY, BASELINE, "current_safe_minus_dlc_original"),
]


def configure_chinese_matplotlib():
    font_candidates = [
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.otf"),
        Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"),
        Path("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"),
        Path("/usr/share/fonts/truetype/arphic/uming.ttc"),
    ]
    font_name = "Noto Sans CJK SC"
    for font_path in font_candidates:
        if font_path.exists():
            font_manager.fontManager.addfont(str(font_path))
            font_name = font_manager.FontProperties(fname=str(font_path)).get_name()
            break
    mpl.rcParams.update(
        {
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "font.family": "sans-serif",
            "font.sans-serif": [font_name, "Noto Sans CJK SC", "DejaVu Sans"],
            "font.size": 7.3,
            "axes.unicode_minus": False,
            "axes.spines.right": False,
            "axes.spines.top": False,
            "axes.linewidth": 0.75,
            "legend.frameon": False,
        }
    )
    return font_name


def read_csv(path):
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")
    return str(path)


def write_json(path, data):
    return write_text(path, json.dumps(data, ensure_ascii=False, indent=2))


def write_csv(path, rows, fields=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = sorted({key for row in rows for key in row.keys()})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return str(path)


def as_float(value):
    if value in (None, "", "nan", "NaN", "NA", "--"):
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(out) or math.isinf(out):
        return None
    return out


def fmt(value, digits=3):
    value = as_float(value)
    if value is None:
        return "NA"
    return f"{value:.{digits}f}"


def mean(values):
    vals = [as_float(v) for v in values]
    vals = [v for v in vals if v is not None]
    return statistics.fmean(vals) if vals else None


def median(values):
    vals = sorted(v for v in (as_float(x) for x in values) if v is not None)
    return statistics.median(vals) if vals else None


def quantile(values, q):
    vals = sorted(v for v in (as_float(x) for x in values) if v is not None)
    if not vals:
        return None
    if len(vals) == 1:
        return vals[0]
    pos = (len(vals) - 1) * q
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return vals[lo]
    frac = pos - lo
    return vals[lo] * (1 - frac) + vals[hi] * frac


def safe_delta(left, right):
    left = as_float(left)
    right = as_float(right)
    return None if left is None or right is None else left - right


def case_key(row):
    return (row["_benchmark"], str(row["num_agents"]), str(row["seed"]))


def enrich_row(row, source_matrix):
    out = dict(row)
    out["source_matrix"] = source_matrix
    out["case_id"] = f"{row['_benchmark']}|n{row['num_agents']}|seed{row['seed']}"
    out["algorithm_label_cn_final"] = LABELS_CN.get(row["algorithm"], row.get("algorithm_label_cn", row["algorithm"]))
    success = as_float(row.get("overtake_success_rate")) or 0.0
    on_track = as_float(row.get("on_track_overtake_rate")) or 0.0
    elegant = as_float(row.get("elegant_overtake_rate")) or 0.0
    off_track = max(0.0, success - on_track)
    on_track_non_elegant = max(0.0, on_track - elegant)
    no_overtake = max(0.0, 1.0 - success)
    out["off_track_overtake_rate_derived"] = off_track
    out["on_track_non_elegant_rate_derived"] = on_track_non_elegant
    out["no_overtake_rate_derived"] = no_overtake
    return out


def load_rows(formal_source, v7_source):
    formal_rows = [enrich_row(row, "v6_frozen_confirmatory_matrix") for row in read_csv(formal_source) if row.get("algorithm") in {PRIMARY, BASELINE}]
    v7_rows = [enrich_row(row, "v7_pilot_matrix") for row in read_csv(v7_source) if row.get("algorithm") == V7]
    return formal_rows + v7_rows


def aggregate(rows, group_fields):
    groups = defaultdict(list)
    for row in rows:
        groups[tuple(row[field] for field in group_fields)].append(row)
    out = []
    metrics = [
        "overtake_success_rate",
        "on_track_overtake_rate",
        "elegant_overtake_rate",
        "off_track_overtake_rate_derived",
        "on_track_non_elegant_rate_derived",
        "overtake_start_to_complete_time",
        "time_to_first_overtake",
        "overtake_window_grass_rate_mean",
        "overtake_window_max_abs_lateral_mean",
        "target_grass_rate",
        "target_mean_abs_lateral",
        "rank_gain",
        "target_progress",
        "compute_latency_ms",
        "compute_latency_p95_ms",
        "finish_step",
    ]
    for key, items in sorted(groups.items()):
        row = {field: value for field, value in zip(group_fields, key)}
        row["n_runs"] = len(items)
        for metric in metrics:
            vals = [item.get(metric) for item in items]
            row[f"{metric}_mean"] = mean(vals)
            row[f"{metric}_median"] = median(vals)
            row[f"{metric}_q25"] = quantile(vals, 0.25)
            row[f"{metric}_q75"] = quantile(vals, 0.75)
            row[f"{metric}_n"] = len([v for v in vals if as_float(v) is not None])
        out.append(row)
    return out


def build_case_matrix(rows):
    matrix = defaultdict(dict)
    for row in rows:
        matrix[case_key(row)][row["algorithm"]] = row
    return matrix


def build_pair_rows(rows):
    matrix = build_case_matrix(rows)
    pair_rows = []
    metrics = [
        "overtake_success_rate",
        "on_track_overtake_rate",
        "elegant_overtake_rate",
        "off_track_overtake_rate_derived",
        "overtake_start_to_complete_time",
        "overtake_window_grass_rate_mean",
        "target_grass_rate",
        "rank_gain",
        "compute_latency_ms",
    ]
    for key, by_algorithm in sorted(matrix.items()):
        benchmark, num_agents, seed = key
        for left, right, pair_name in PAIRS:
            if left not in by_algorithm or right not in by_algorithm:
                continue
            row = {
                "pair": pair_name,
                "left_algorithm": left,
                "right_algorithm": right,
                "left_label_cn": LABELS_CN[left],
                "right_label_cn": LABELS_CN[right],
                "benchmark": benchmark,
                "num_agents": num_agents,
                "seed": seed,
                "case_id": f"{benchmark}|n{num_agents}|seed{seed}",
            }
            for metric in metrics:
                left_value = as_float(by_algorithm[left].get(metric))
                right_value = as_float(by_algorithm[right].get(metric))
                row[f"left_{metric}"] = "" if left_value is None else left_value
                row[f"right_{metric}"] = "" if right_value is None else right_value
                delta = safe_delta(left_value, right_value)
                row[f"delta_{metric}"] = "" if delta is None else delta
            pair_rows.append(row)
    return pair_rows


def pair_summary(pair_rows):
    groups = defaultdict(list)
    for row in pair_rows:
        groups[row["pair"]].append(row)
    out = []
    delta_metrics = [key for key in pair_rows[0].keys() if key.startswith("delta_")] if pair_rows else []
    for pair, items in sorted(groups.items()):
        row = {"pair": pair, "n_pairs": len(items)}
        for metric in delta_metrics:
            vals = [item.get(metric) for item in items]
            row[f"{metric}_mean"] = mean(vals)
            row[f"{metric}_median"] = median(vals)
            row[f"{metric}_q25"] = quantile(vals, 0.25)
            row[f"{metric}_q75"] = quantile(vals, 0.75)
            row[f"{metric}_n"] = len([v for v in vals if as_float(v) is not None])
        out.append(row)
    return out


def get_algo(algorithm_rows, algorithm):
    for row in algorithm_rows:
        if row["algorithm"] == algorithm:
            return row
    return {}


def make_figure(rows, algorithm_rows, benchmark_rows, pair_rows, pair_rows_summary, out_dir):
    font_name = configure_chinese_matplotlib()
    out_fig = out_dir / "figures"
    out_fig.mkdir(parents=True, exist_ok=True)
    colors = {
        V7: "#4C78A8",
        PRIMARY: "#54A24B",
        BASELINE: "#F58518",
    }
    labels = [LABELS_CN[algorithm] for algorithm in ALGORITHMS]
    fig, axes = plt.subplots(2, 3, figsize=(11.4, 6.5), constrained_layout=True)
    fig.suptitle("v7desirable behavior约束 DLC world model：30-case 在线 pilot 配对分析", fontsize=12, fontweight="bold")

    ax = axes[0][0]
    x = list(range(len(ALGORITHMS)))
    width = 0.24
    bars = [
        ("overtake_success_rate_mean", "完成超车", "#A6A6A6", -width),
        ("on_track_overtake_rate_mean", "赛道内超车", "#72B7B2", 0.0),
        ("elegant_overtake_rate_mean", "Desirable overtaking behavior", "#4C78A8", width),
    ]
    for metric, label, color, offset in bars:
        values = [as_float(get_algo(algorithm_rows, alg).get(metric)) or 0.0 for alg in ALGORITHMS]
        ax.bar([i + offset for i in x], values, width=width, label=label, color=color)
    ax.set_xticks(x, labels, rotation=18, ha="right")
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("运行占比")
    ax.set_title("A 超车质量分层")
    ax.legend(fontsize=6.5)

    ax = axes[0][1]
    width = 0.34
    target_grass = [as_float(get_algo(algorithm_rows, alg).get("target_grass_rate_mean")) or 0.0 for alg in ALGORITHMS]
    window_grass = [as_float(get_algo(algorithm_rows, alg).get("overtake_window_grass_rate_mean_mean")) or 0.0 for alg in ALGORITHMS]
    ax.bar([i - width / 2 for i in x], target_grass, width=width, color="#E45756", label="目标车全程草地率")
    ax.bar([i + width / 2 for i in x], window_grass, width=width, color="#F2B701", label="超车窗口草地率")
    ax.set_xticks(x, labels, rotation=18, ha="right")
    ax.set_ylabel("比例")
    ax.set_title("B 草地暴露")
    ax.legend(fontsize=6.5)

    ax = axes[0][2]
    timing_mean = [as_float(get_algo(algorithm_rows, alg).get("overtake_start_to_complete_time_mean")) for alg in ALGORITHMS]
    timing_median = [as_float(get_algo(algorithm_rows, alg).get("overtake_start_to_complete_time_median")) for alg in ALGORITHMS]
    ax.bar(x, [v or 0.0 for v in timing_mean], color=[colors[alg] for alg in ALGORITHMS], alpha=0.82, label="均值")
    ax.plot(x, [v or 0.0 for v in timing_median], color="#222222", marker="o", linewidth=1.2, label="中位数")
    ax.set_xticks(x, labels, rotation=18, ha="right")
    ax.set_ylabel("仿真步")
    ax.set_title("C 开始超车到完成耗时")
    ax.legend(fontsize=6.5)

    ax = axes[1][0]
    selected = [row for row in pair_rows if row["pair"] in {"v7_minus_current_safe", "v7_minus_dlc_original"}]
    pair_order = ["v7_minus_current_safe", "v7_minus_dlc_original"]
    box_data = [
        [as_float(row.get("delta_overtake_start_to_complete_time")) for row in selected if row["pair"] == pair]
        for pair in pair_order
    ]
    box_data = [[v for v in values if v is not None] for values in box_data]
    boxplot_kwargs = {
        "showfliers": False,
        "patch_artist": True,
        "boxprops": {"facecolor": "#D8DEE9", "edgecolor": "#555555"},
        "medianprops": {"color": "#111111", "linewidth": 1.2},
    }
    try:
        ax.boxplot(box_data, tick_labels=["v7-当前主方法", "v7-DLC原始"], **boxplot_kwargs)
    except TypeError:
        ax.boxplot(box_data, labels=["v7-当前主方法", "v7-DLC原始"], **boxplot_kwargs)
    ax.axhline(0, color="#666666", linestyle="--", linewidth=0.8)
    ax.set_ylabel("耗时差值（步）")
    ax.set_title("D 逐 case 配对耗时差")

    ax = axes[1][1]
    bench_alg = defaultdict(dict)
    for row in benchmark_rows:
        bench_alg[row["_benchmark"]][row["algorithm"]] = row
    bench_order = sorted(bench_alg)
    xx = list(range(len(bench_order)))
    for idx, alg in enumerate(ALGORITHMS):
        vals = [as_float(bench_alg[bench].get(alg, {}).get("elegant_overtake_rate_mean")) or 0.0 for bench in bench_order]
        ax.plot(xx, vals, marker="o", color=colors[alg], label=LABELS_CN[alg], linewidth=1.4)
    ax.set_xticks(xx, bench_order, rotation=18, ha="right")
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Desirable overtaking behavior rate")
    ax.set_title("E 按 benchmark 子组")
    ax.legend(fontsize=6.5)

    ax = axes[1][2]
    latency = [as_float(get_algo(algorithm_rows, alg).get("compute_latency_ms_mean")) or 0.0 for alg in ALGORITHMS]
    latency_p95 = [as_float(get_algo(algorithm_rows, alg).get("compute_latency_p95_ms_mean")) or 0.0 for alg in ALGORITHMS]
    ax.bar(x, latency, color=[colors[alg] for alg in ALGORITHMS], alpha=0.82, label="平均延迟")
    ax.plot(x, latency_p95, color="#222222", marker="s", linewidth=1.2, label="p95延迟")
    ax.set_xticks(x, labels, rotation=18, ha="right")
    ax.set_ylabel("毫秒/步")
    ax.set_title("F 在线计算代价")
    ax.legend(fontsize=6.5)

    paths = {}
    for suffix in ["svg", "pdf", "png", "tiff"]:
        path = out_fig / f"figure_v7_paired_pilot_overtake_quality_cn.{suffix}"
        fig.savefig(path, dpi=500 if suffix in {"png", "tiff"} else None, bbox_inches="tight")
        paths[suffix] = str(path)
    plt.close(fig)
    paths["font"] = font_name
    return paths


def build_markdown(report):
    s = report["summary"]
    lines = [
        "# v7 desirable behavior约束 DLC World Model 在线 Pilot 配对分析",
        "",
        "该分析包把 `v7_elegance_barrier_dlc_world` 的 30-case 在线 pilot 与已冻结 240-run 正式矩阵中的 `v6_runtime_dynamic_neighborhood_safe`、`dlc_world_original` 合并。所有比较均按同一 benchmark、同一车辆数、同一 seed 配对，避免把 case 难度差异误当成算法差异。",
        "",
        "## 结论边界",
        "",
        "- 这是探索性 pilot，不替代已冻结的 8 算法、30 case、240 run 主结果。",
        "- v7 用于检验“desirable behavior约束”是否值得进入下一轮重新冻结的扩展矩阵。",
        "- 若将 v7 写入论文主结论，需要预注册扩展矩阵并重跑所有对比算法，不能只用本 pilot 替代确认性实验。",
        "",
        "## 核心数值",
        "",
        f"- v7 run 数: {s['v7_runs']}/30",
        f"- 配对 case 数: {s['complete_three_algorithm_cases']}/30",
        f"- v7 完成超车率: {fmt(s['v7_success_rate'])}",
        f"- v7 赛道内超车率: {fmt(s['v7_on_track_rate'])}",
        f"- v7 Desirable overtaking behavior rate: {fmt(s['v7_elegant_rate'])}",
        f"- v7 全程目标车草地率: {fmt(s['v7_target_grass_rate'])}",
        f"- v7 超车窗口草地率: {fmt(s['v7_window_grass_rate'])}",
        f"- v7 平均超车耗时: {fmt(s['v7_timing_mean'], 2)} steps",
        f"- v7 平均在线延迟: {fmt(s['v7_latency_mean'], 2)} ms/step",
        f"- v7 - 当前主方法：Desirable overtaking behavior rate差值 {fmt(s['v7_minus_current_elegant_delta'])}，草地率差值 {fmt(s['v7_minus_current_target_grass_delta'])}",
        f"- v7 - DLC原始：Desirable overtaking behavior rate差值 {fmt(s['v7_minus_dlc_elegant_delta'])}，草地率差值 {fmt(s['v7_minus_dlc_target_grass_delta'])}",
        "",
        "## 生成文件",
        "",
        "- 合并 source data: `tables/v7_current_dlc_combined_source_data.csv`",
        "- 算法聚合表: `tables/v7_pilot_algorithm_summary.csv`",
        "- benchmark 子组表: `tables/v7_pilot_benchmark_summary.csv`",
        "- 逐 case 配对表: `tables/v7_pilot_pairwise_case_deltas.csv`",
        "- 配对汇总表: `tables/v7_pilot_pairwise_delta_summary.csv`",
        "- 中文主图: `figures/figure_v7_paired_pilot_overtake_quality_cn.svg`",
        "",
        "## 复现命令",
        "",
        "```bash",
        "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_v7_paired_pilot_analysis_pack.py --out-dir outputs/tits_dynamic_graph/tits_v7_paired_pilot_analysis_pack",
        "```",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Export paired pilot analysis for v7 desirable behavior-barrier DLC world model.")
    parser.add_argument("--formal-source", default=FORMAL_SOURCE)
    parser.add_argument("--v7-source", default=V7_SOURCE)
    parser.add_argument("--out-dir", default=OUT_DIR)
    args = parser.parse_args()

    root = Path.cwd()
    out_dir = root / args.out_dir
    (out_dir / "tables").mkdir(parents=True, exist_ok=True)
    (out_dir / "figures").mkdir(parents=True, exist_ok=True)
    (out_dir / "materials").mkdir(parents=True, exist_ok=True)

    rows = load_rows(root / args.formal_source, root / args.v7_source)
    algorithm_rows = aggregate(rows, ["algorithm", "algorithm_label_cn_final", "source_matrix"])
    benchmark_rows = aggregate(rows, ["_benchmark", "algorithm", "algorithm_label_cn_final"])
    vehicle_rows = aggregate(rows, ["num_agents", "algorithm", "algorithm_label_cn_final"])
    pair_rows = build_pair_rows(rows)
    pair_rows_summary = pair_summary(pair_rows)
    figure_paths = make_figure(rows, algorithm_rows, benchmark_rows, pair_rows, pair_rows_summary, out_dir)

    matrix = build_case_matrix(rows)
    complete_three = sum(1 for by_algorithm in matrix.values() if all(alg in by_algorithm for alg in ALGORITHMS))
    algo = {row["algorithm"]: row for row in algorithm_rows}
    v7 = algo.get(V7, {})
    current = algo.get(PRIMARY, {})
    dlc = algo.get(BASELINE, {})
    summary = {
        "status": "pass" if len([r for r in rows if r["algorithm"] == V7]) == 30 and complete_three == 30 else "review_required",
        "formal_source": args.formal_source,
        "v7_source": args.v7_source,
        "combined_rows": len(rows),
        "v7_runs": len([r for r in rows if r["algorithm"] == V7]),
        "complete_three_algorithm_cases": complete_three,
        "pair_rows": len(pair_rows),
        "v7_success_rate": v7.get("overtake_success_rate_mean"),
        "v7_on_track_rate": v7.get("on_track_overtake_rate_mean"),
        "v7_elegant_rate": v7.get("elegant_overtake_rate_mean"),
        "v7_target_grass_rate": v7.get("target_grass_rate_mean"),
        "v7_window_grass_rate": v7.get("overtake_window_grass_rate_mean_mean"),
        "v7_timing_mean": v7.get("overtake_start_to_complete_time_mean"),
        "v7_timing_median": v7.get("overtake_start_to_complete_time_median"),
        "v7_latency_mean": v7.get("compute_latency_ms_mean"),
        "current_elegant_rate": current.get("elegant_overtake_rate_mean"),
        "dlc_elegant_rate": dlc.get("elegant_overtake_rate_mean"),
        "v7_minus_current_elegant_delta": safe_delta(v7.get("elegant_overtake_rate_mean"), current.get("elegant_overtake_rate_mean")),
        "v7_minus_dlc_elegant_delta": safe_delta(v7.get("elegant_overtake_rate_mean"), dlc.get("elegant_overtake_rate_mean")),
        "v7_minus_current_target_grass_delta": safe_delta(v7.get("target_grass_rate_mean"), current.get("target_grass_rate_mean")),
        "v7_minus_dlc_target_grass_delta": safe_delta(v7.get("target_grass_rate_mean"), dlc.get("target_grass_rate_mean")),
        "figure_font": figure_paths["font"],
        "claim_boundary": "exploratory_pilot_not_confirmatory_freeze",
    }
    paths = {
        "combined_source_data": write_csv(out_dir / "tables" / "v7_current_dlc_combined_source_data.csv", rows),
        "algorithm_summary": write_csv(out_dir / "tables" / "v7_pilot_algorithm_summary.csv", algorithm_rows),
        "benchmark_summary": write_csv(out_dir / "tables" / "v7_pilot_benchmark_summary.csv", benchmark_rows),
        "vehicle_summary": write_csv(out_dir / "tables" / "v7_pilot_vehicle_count_summary.csv", vehicle_rows),
        "pairwise_case_deltas": write_csv(out_dir / "tables" / "v7_pilot_pairwise_case_deltas.csv", pair_rows),
        "pairwise_delta_summary": write_csv(out_dir / "tables" / "v7_pilot_pairwise_delta_summary.csv", pair_rows_summary),
        "figure_svg": figure_paths["svg"],
        "figure_pdf": figure_paths["pdf"],
        "figure_png": figure_paths["png"],
        "figure_tiff": figure_paths["tiff"],
    }
    report = {
        "status": summary["status"],
        "summary": summary,
        "paths": paths,
        "figure_contract": {
            "core_conclusion": "v7 desirable behavior约束 DLC world model 的收益必须同时由超车率、Desirable overtaking behavior rate、草地暴露、耗时和在线延迟解释。",
            "archetype": "quantitative grid",
            "backend": "Python/matplotlib",
            "claim_boundary": "pilot evidence only; not a replacement for the frozen confirmatory matrix.",
        },
    }
    paths["report_json"] = write_json(out_dir / "materials" / "V7_PAIRED_PILOT_ANALYSIS_REPORT.json", report)
    paths["report_md"] = write_text(out_dir / "materials" / "V7_PAIRED_PILOT_ANALYSIS_REPORT.md", build_markdown(report))
    manifest = {
        "status": summary["status"],
        "out_dir": args.out_dir,
        "summary": summary,
        "paths": paths,
        "claim_boundary": "exploratory pilot; formal claims remain tied to the frozen 240-run matrix unless an expanded matrix is frozen and rerun.",
    }
    manifest_path = write_json(out_dir / "tits_v7_paired_pilot_analysis_pack_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, "status": summary["status"], "summary": summary}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
