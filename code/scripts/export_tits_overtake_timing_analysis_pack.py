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


SOURCE_CSV = "outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv"
PRIMARY = "v6_runtime_dynamic_neighborhood_safe"
BASELINE = "dlc_world_original"
QUALITY = "quality_proposal_dlc_world_v1"
RULE = "rule_expert_gate"
FAST = "dlc_world_fast"
SAFE = "dlc_world_safety"
BALANCED = "dlc_world_balanced"


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
    mpl.rcParams.update({
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "font.family": "sans-serif",
        "font.sans-serif": [font_name, "Noto Sans CJK SC", "DejaVu Sans"],
        "axes.unicode_minus": False,
    })
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


def write_csv(path, rows, fields):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
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


def fmt(value, digits=2):
    value = as_float(value)
    if value is None:
        return "NA"
    if abs(value) < 0.001 and value != 0:
        return f"{value:.2e}"
    return f"{value:.{digits}f}"


def mean(values):
    vals = [as_float(v) for v in values]
    vals = [v for v in vals if v is not None]
    return statistics.fmean(vals) if vals else None


def median(values):
    vals = [as_float(v) for v in values]
    vals = [v for v in vals if v is not None]
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


def build_index(rows):
    index = defaultdict(dict)
    for row in rows:
        index[(row["_benchmark"], row["num_agents"], row["seed"])][row["algorithm"]] = row
    return index


def collect(values, metric):
    out = []
    for row in values:
        item = as_float(row.get(metric))
        if item is not None:
            out.append(item)
    return out


def group_stats(rows, group_key):
    grouped = defaultdict(list)
    for row in rows:
        grouped[row[group_key]].append(row)
    out = []
    for key, items in sorted(grouped.items()):
        vals = collect(items, "overtake_start_to_complete_time")
        success = collect(items, "overtake_success_rate")
        on_track = collect(items, "on_track_overtake_rate")
        elegant = collect(items, "elegant_overtake_rate")
        out.append(
            {
                group_key: key,
                "n_runs": len(items),
                "n_success": sum(1 for v in success if v == 1.0),
                "success_rate_mean": mean(success),
                "on_track_rate_mean": mean(on_track),
                "elegant_rate_mean": mean(elegant),
                "timing_n": len(vals),
                "timing_mean": mean(vals),
                "timing_median": median(vals),
                "timing_q25": quantile(vals, 0.25),
                "timing_q75": quantile(vals, 0.75),
                "timing_min": min(vals) if vals else None,
                "timing_max": max(vals) if vals else None,
            }
        )
    return out


def algorithm_stats(rows):
    return group_stats(rows, "algorithm")


def benchmark_stats(rows):
    return group_stats(rows, "_benchmark")


def vehicle_stats(rows):
    return group_stats(rows, "num_agents")


def pairwise_success_time(rows):
    index = build_index(rows)
    pairs = []
    for key, items in sorted(index.items()):
        if BASELINE not in items or PRIMARY not in items:
            continue
        base = items[BASELINE]
        cand = items[PRIMARY]
        base_t = as_float(base.get("overtake_start_to_complete_time"))
        cand_t = as_float(cand.get("overtake_start_to_complete_time"))
        base_s = as_float(base.get("overtake_success_rate"))
        cand_s = as_float(cand.get("overtake_success_rate"))
        if base_s is not None and cand_s is not None and base_s == 1.0 and cand_s == 1.0 and base_t is not None and cand_t is not None:
            delta = cand_t - base_t
        else:
            delta = None
        pairs.append(
            {
                "benchmark": key[0],
                "num_agents": key[1],
                "seed": key[2],
                "baseline_time": base_t,
                "primary_time": cand_t,
                "time_delta_primary_minus_baseline": delta,
                "baseline_success": base_s,
                "primary_success": cand_s,
            }
        )
    return pairs


def make_figure(algorithm_rows, benchmark_rows, vehicle_rows, pair_rows, out_dir):
    font_name = configure_chinese_matplotlib()
    mpl.rcParams.update({"font.size": 8})
    fig, axes = plt.subplots(1, 3, figsize=(10.5, 3.4), constrained_layout=True)
    fig.suptitle("超车完成耗时分析", fontsize=12, fontweight="bold")

    ax = axes[0]
    rows = [row for row in algorithm_rows if row["algorithm"] in [PRIMARY, BASELINE, QUALITY, RULE, FAST, SAFE, BALANCED]]
    order = [PRIMARY, QUALITY, RULE, BASELINE, BALANCED, SAFE, FAST]
    rows = sorted(rows, key=lambda r: order.index(r["algorithm"]) if r["algorithm"] in order else 99)
    labels = [row["algorithm"] for row in rows]
    means = [as_float(row["timing_mean"]) or 0.0 for row in rows]
    medians = [as_float(row["timing_median"]) or 0.0 for row in rows]
    x = range(len(rows))
    ax.bar(x, means, color="#4C78A8", label="均值")
    ax.plot(x, medians, color="#F58518", marker="o", label="中位数")
    ax.set_xticks(list(x), labels, rotation=20, ha="right")
    ax.set_ylabel("仿真步")
    ax.set_title("按算法汇总")
    ax.legend(fontsize=7)

    ax = axes[1]
    labels = [str(row["_benchmark"]) for row in benchmark_rows]
    means = [as_float(row["timing_mean"]) or 0.0 for row in benchmark_rows]
    q25 = [as_float(row["timing_q25"]) or 0.0 for row in benchmark_rows]
    q75 = [as_float(row["timing_q75"]) or 0.0 for row in benchmark_rows]
    y = range(len(benchmark_rows))
    ax.barh(list(y), means, color="#72B7B2")
    ax.errorbar(means, list(y), xerr=[[m - l for m, l in zip(means, q25)], [h - m for h, m in zip(q75, means)]], fmt="none", ecolor="#2F4B7C", capsize=3)
    ax.set_yticks(list(y), labels)
    ax.invert_yaxis()
    ax.set_xlabel("仿真步")
    ax.set_title("按 benchmark 汇总")

    ax = axes[2]
    labels = [str(row["num_agents"]) for row in vehicle_rows]
    medians = [as_float(row["timing_median"]) or 0.0 for row in vehicle_rows]
    ax.plot(labels, medians, marker="o", color="#54A24B")
    ax.set_xlabel("车辆数")
    ax.set_ylabel("中位超车完成耗时")
    ax.set_title("按车数变化")

    paths = {}
    for suffix in ["svg", "pdf", "png", "tiff"]:
        path = out_dir / "figures" / f"figure_overtake_completion_time_cn.{suffix}"
        fig.savefig(path, dpi=300 if suffix in {"png", "tiff"} else None)
        paths[suffix] = str(path)
    plt.close(fig)
    paths["font"] = font_name
    return paths


def build_markdown(report):
    s = report["summary"]
    lines = [
        "# T-ITS Overtake Timing Analysis Pack",
        "",
        "该包专门分析超车开始到完成的时间指标 `overtake_start_to_complete_time`，用于补充顶刊式超车效率讨论。",
        "",
        "## Summary",
        "",
        f"- Status: `{report['status']}`",
        f"- Source rows: {s['source_rows']}",
        f"- Algorithms: {s['algorithm_count']}",
        f"- Benchmarks: {s['benchmarks']}",
        f"- Vehicle counts: {s['vehicle_counts']}",
        f"- Timing observations: {s['timing_observation_count']}",
        f"- Success observations: {s['success_observation_count']}",
        f"- Primary mean timing vs DLC: {fmt(s['primary_mean_timing'])} vs {fmt(s['baseline_mean_timing'])}",
        f"- Primary median timing vs DLC: {fmt(s['primary_median_timing'])} vs {fmt(s['baseline_median_timing'])}",
        "",
        "## Interpretation",
        "",
        "- 时间指标只在成功超车语义成立时统计；未超车样本不被混入耗时均值。",
        "- 更低的完成耗时意味着更快完成有效超车。",
        "- 主方法在成功样本中应同时关注成功率、赛道内比例、desirable overtaking behavior proportion和完成时间，不能只看单一时间值。",
        "",
        "## Key Files",
        "",
        "- Algorithm stats: `tables/overtake_timing_by_algorithm.csv`",
        "- Benchmark stats: `tables/overtake_timing_by_benchmark.csv`",
        "- Vehicle stats: `tables/overtake_timing_by_vehicle_count.csv`",
        "- Pairwise success-time rows: `tables/overtake_timing_pairwise_success_rows.csv`",
        "- 中文 figure: `figures/figure_overtake_completion_time_cn.svg`",
        "",
        "## Regeneration Command",
        "",
        "```bash",
        "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_overtake_timing_analysis_pack.py --out-dir outputs/tits_dynamic_graph/tits_overtake_timing_analysis_pack",
        "```",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Export an overtake timing analysis pack.")
    parser.add_argument("--source-csv", default=SOURCE_CSV)
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/tits_overtake_timing_analysis_pack")
    args = parser.parse_args()

    root = Path(".").resolve()
    out_dir = root / args.out_dir
    materials = out_dir / "materials"
    tables = out_dir / "tables"
    figures = out_dir / "figures"
    materials.mkdir(parents=True, exist_ok=True)
    tables.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)

    rows = read_csv(root / args.source_csv)
    algorithm_rows = algorithm_stats(rows)
    benchmark_rows = benchmark_stats(rows)
    vehicle_rows = vehicle_stats(rows)
    pair_rows = pairwise_success_time(rows)
    figure_paths = make_figure(algorithm_rows, benchmark_rows, vehicle_rows, pair_rows, out_dir)

    baseline_values = [r["baseline_time"] for r in pair_rows if r["baseline_time"] is not None]
    primary_values = [r["primary_time"] for r in pair_rows if r["primary_time"] is not None]
    summary = {
        "status": "pass",
        "source_rows": len(rows),
        "algorithm_count": len({row["algorithm"] for row in rows}),
        "timing_observation_count": len([r for r in rows if as_float(r.get("overtake_start_to_complete_time")) is not None]),
        "success_observation_count": len([r for r in rows if as_float(r.get("overtake_success_rate")) == 1.0]),
        "benchmarks": ",".join(sorted({row["_benchmark"] for row in rows})),
        "vehicle_counts": ",".join(sorted({row["num_agents"] for row in rows}, key=lambda x: int(x))),
        "primary_mean_timing": mean(primary_values),
        "baseline_mean_timing": mean(baseline_values),
        "primary_median_timing": median(primary_values),
        "baseline_median_timing": median(baseline_values),
        "pairwise_success_time_rows": len(pair_rows),
    }
    report = {
        "status": "pass",
        "summary": summary,
        "algorithm_rows": algorithm_rows,
        "benchmark_rows": benchmark_rows,
        "vehicle_rows": vehicle_rows,
        "pairwise_success_time_rows": pair_rows,
        "figure_paths": figure_paths,
        "note": "This pack isolates overtake completion time. It does not replace the full confirmatory statistics or the casewise diagnostic pack.",
    }

    paths = {
        "report_md": write_text(materials / "OVERTAKE_TIMING_ANALYSIS_REPORT.md", build_markdown(report)),
        "report_json": write_json(materials / "OVERTAKE_TIMING_ANALYSIS_REPORT.json", report),
        "algorithm_stats_csv": write_csv(
            tables / "overtake_timing_by_algorithm.csv",
            algorithm_rows,
            ["algorithm", "n_runs", "n_success", "success_rate_mean", "on_track_rate_mean", "elegant_rate_mean", "timing_n", "timing_mean", "timing_median", "timing_q25", "timing_q75", "timing_min", "timing_max"],
        ),
        "benchmark_stats_csv": write_csv(
            tables / "overtake_timing_by_benchmark.csv",
            benchmark_rows,
            ["_benchmark", "num_agents", "n_runs", "n_success", "success_rate_mean", "on_track_rate_mean", "elegant_rate_mean", "timing_n", "timing_mean", "timing_median", "timing_q25", "timing_q75", "timing_min", "timing_max"],
        ),
        "vehicle_stats_csv": write_csv(
            tables / "overtake_timing_by_vehicle_count.csv",
            vehicle_rows,
            ["num_agents", "n_runs", "n_success", "success_rate_mean", "on_track_rate_mean", "elegant_rate_mean", "timing_n", "timing_mean", "timing_median", "timing_q25", "timing_q75", "timing_min", "timing_max"],
        ),
        "pairwise_success_time_csv": write_csv(
            tables / "overtake_timing_pairwise_success_rows.csv",
            pair_rows,
            ["benchmark", "num_agents", "seed", "baseline_time", "primary_time", "time_delta_primary_minus_baseline", "baseline_success", "primary_success"],
        ),
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
        "note": report["note"],
    }
    manifest_path = write_json(out_dir / "tits_overtake_timing_analysis_pack_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, "status": "pass", "summary": summary}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
