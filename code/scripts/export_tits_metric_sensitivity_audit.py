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


OURS = "v6_runtime_dynamic_neighborhood_safe"
BASELINE = "dlc_world_original"
ALGORITHMS = [
    "v6_runtime_dynamic_neighborhood_safe",
    "v6_runtime_dynamic_neighborhood",
    "quality_proposal_dlc_world_v1",
    "dlc_world_original",
    "dlc_world_balanced",
    "dlc_world_safety",
    "dlc_world_fast",
    "rule_expert_gate",
]
GRASS_THRESHOLDS = [0.0, 0.05, 0.10, 0.20, 0.30]
LATERAL_THRESHOLDS = [0.25, 0.35, 0.50, 0.65]
TIME_THRESHOLDS = [120, 200, 400]


def register_cjk_font():
    candidates = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
        "/usr/share/fonts/truetype/arphic/ukai.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for item in candidates:
        path = Path(item)
        if path.exists():
            from matplotlib import font_manager

            font_manager.fontManager.addfont(str(path))
            family = font_manager.FontProperties(fname=str(path)).get_name()
            mpl.rcParams["font.family"] = family
            mpl.rcParams["font.sans-serif"] = [family, "Arial", "DejaVu Sans", "sans-serif"]
            return family
    return None


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
    return write_text(path, json.dumps(data, ensure_ascii=False, indent=2))


def f(value):
    if value in (None, "", "nan", "NaN"):
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


def case_key(row):
    return (
        row.get("_benchmark", ""),
        row.get("num_agents", ""),
        row.get("seed", ""),
        row.get("track_path", ""),
        row.get("traffic_profile", ""),
    )


def alg_label(rows, algorithm):
    for row in rows:
        if row.get("algorithm") == algorithm:
            return row.get("algorithm_label_cn") or algorithm
    return algorithm


def completed_overtake(row):
    return (f(row.get("overtake_count")) or 0.0) > 0.0 or (f(row.get("overtake_success_rate")) or 0.0) > 0.0


def threshold_pass(row, grass_threshold, lateral_threshold, time_threshold=None):
    if not completed_overtake(row):
        return 0
    grass = f(row.get("overtake_window_grass_rate_mean"))
    lateral = f(row.get("overtake_window_max_abs_lateral_mean"))
    duration = f(row.get("overtake_start_to_complete_time"))
    if grass is None or lateral is None:
        return 0
    if grass > grass_threshold or lateral > lateral_threshold:
        return 0
    if time_threshold is not None and (duration is None or duration > time_threshold):
        return 0
    return 1


def build_case_index(rows):
    indexed = defaultdict(dict)
    for row in rows:
        indexed[case_key(row)][row["algorithm"]] = row
    return indexed


def mean(values):
    values = [float(v) for v in values if v is not None]
    if not values:
        return None
    return float(np.mean(values))


def bootstrap_ci(values, seed=20260624, n_boot=3000):
    values = np.asarray([float(v) for v in values if v is not None], dtype=float)
    if values.size == 0:
        return None, None, None
    center = float(values.mean())
    if values.size == 1:
        return center, center, center
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, values.size, size=(n_boot, values.size))
    boot = values[idx].mean(axis=1)
    lo, hi = np.quantile(boot, [0.025, 0.975])
    return center, float(lo), float(hi)


def grid_rows(rows):
    out = []
    by_alg = defaultdict(list)
    for row in rows:
        by_alg[row["algorithm"]].append(row)
    threshold_id = 0
    for grass in GRASS_THRESHOLDS:
        for lateral in LATERAL_THRESHOLDS:
            threshold_id += 1
            for algorithm in ALGORITHMS:
                values = [threshold_pass(row, grass, lateral) for row in by_alg.get(algorithm, [])]
                rate, lo, hi = bootstrap_ci(values, seed=20260624 + threshold_id)
                out.append(
                    {
                        "threshold_id": f"Q{threshold_id:02d}",
                        "definition": "quality_overtake",
                        "grass_threshold": grass,
                        "lateral_threshold": lateral,
                        "time_threshold": "",
                        "algorithm": algorithm,
                        "algorithm_label_cn": alg_label(rows, algorithm),
                        "n": len(values),
                        "rate": rate,
                        "ci95_low": lo,
                        "ci95_high": hi,
                    }
                )
    for grass in [0.10, 0.20, 0.30]:
        for lateral in [0.35, 0.50, 0.65]:
            for time_threshold in TIME_THRESHOLDS:
                threshold_id += 1
                for algorithm in ALGORITHMS:
                    values = [threshold_pass(row, grass, lateral, time_threshold) for row in by_alg.get(algorithm, [])]
                    rate, lo, hi = bootstrap_ci(values, seed=20260701 + threshold_id)
                    out.append(
                        {
                            "threshold_id": f"T{threshold_id:02d}",
                            "definition": "quality_and_time_bounded_overtake",
                            "grass_threshold": grass,
                            "lateral_threshold": lateral,
                            "time_threshold": time_threshold,
                            "algorithm": algorithm,
                            "algorithm_label_cn": alg_label(rows, algorithm),
                            "n": len(values),
                            "rate": rate,
                            "ci95_low": lo,
                            "ci95_high": hi,
                        }
                    )
    return out


def paired_rows(rows, sensitivity_rows):
    indexed = build_case_index(rows)
    out = []
    settings = []
    seen = set()
    for row in sensitivity_rows:
        key = (
            row["threshold_id"],
            row["definition"],
            row["grass_threshold"],
            row["lateral_threshold"],
            row["time_threshold"],
        )
        if key not in seen:
            seen.add(key)
            settings.append(row)
    for setting in settings:
        grass = float(setting["grass_threshold"])
        lateral = float(setting["lateral_threshold"])
        time_threshold = setting["time_threshold"]
        time_threshold = None if time_threshold in ("", None) else float(time_threshold)
        for algorithm in [item for item in ALGORITHMS if item != BASELINE]:
            deltas = []
            alg_values = []
            base_values = []
            for algs in indexed.values():
                if algorithm not in algs or BASELINE not in algs:
                    continue
                a = threshold_pass(algs[algorithm], grass, lateral, time_threshold)
                b = threshold_pass(algs[BASELINE], grass, lateral, time_threshold)
                alg_values.append(a)
                base_values.append(b)
                deltas.append(a - b)
            delta, lo, hi = bootstrap_ci(deltas, seed=20260801 + len(out))
            out.append(
                {
                    "threshold_id": setting["threshold_id"],
                    "definition": setting["definition"],
                    "grass_threshold": grass,
                    "lateral_threshold": lateral,
                    "time_threshold": "" if time_threshold is None else int(time_threshold),
                    "algorithm": algorithm,
                    "algorithm_label_cn": alg_label(rows, algorithm),
                    "baseline": BASELINE,
                    "baseline_label_cn": alg_label(rows, BASELINE),
                    "n_paired": len(deltas),
                    "algorithm_rate": mean(alg_values),
                    "baseline_rate": mean(base_values),
                    "paired_delta": delta,
                    "paired_delta_ci95_low": lo,
                    "paired_delta_ci95_high": hi,
                    "positive_cases": sum(1 for d in deltas if d > 0),
                    "negative_cases": sum(1 for d in deltas if d < 0),
                    "equal_cases": sum(1 for d in deltas if d == 0),
                }
            )
    return out


def robustness_summary(paired):
    grouped = defaultdict(list)
    for row in paired:
        grouped[row["algorithm"]].append(row)
    out = []
    for algorithm in [item for item in ALGORITHMS if item != BASELINE]:
        rows = grouped.get(algorithm, [])
        deltas = [f(row["paired_delta"]) for row in rows if f(row["paired_delta"]) is not None]
        positive = [d for d in deltas if d > 0]
        nonnegative = [d for d in deltas if d >= 0]
        quality_only = [row for row in rows if row["definition"] == "quality_overtake"]
        time_bounded = [row for row in rows if row["definition"] == "quality_and_time_bounded_overtake"]
        out.append(
            {
                "algorithm": algorithm,
                "algorithm_label_cn": rows[0]["algorithm_label_cn"] if rows else algorithm,
                "threshold_settings": len(rows),
                "positive_delta_settings": len(positive),
                "nonnegative_delta_settings": len(nonnegative),
                "positive_delta_fraction": len(positive) / len(rows) if rows else None,
                "nonnegative_delta_fraction": len(nonnegative) / len(rows) if rows else None,
                "min_delta": min(deltas) if deltas else None,
                "median_delta": float(np.median(deltas)) if deltas else None,
                "max_delta": max(deltas) if deltas else None,
                "quality_only_min_delta": min(f(row["paired_delta"]) for row in quality_only) if quality_only else None,
                "time_bounded_min_delta": min(f(row["paired_delta"]) for row in time_bounded) if time_bounded else None,
                "interpretation_cn": (
                    "跨全部敏感性阈值均优于原始 DLC"
                    if rows and len(positive) == len(rows)
                    else "部分阈值下优势减弱或不成立，需要作为边界解释"
                ),
            }
        )
    return out


def claim_boundaries(summary):
    ours = next((row for row in summary if row["algorithm"] == OURS), {})
    return [
        {
            "claim_id": "MS1",
            "safe_claim_cn": (
                "在当前后验阈值网格内，v6-safe 相对原始 DLC 的质量超车率优势可以作为主结果的稳健性补充。"
                if f(ours.get("positive_delta_fraction")) == 1.0
                else "在当前后验阈值网格内，v6-safe 的优势随阈值变化，需要保守表述为对预定义主指标成立。"
            ),
            "evidence": "tables/paired_threshold_sensitivity_vs_dlc.csv; tables/robustness_summary_by_algorithm.csv",
            "boundary_cn": "敏感性审计是后验稳健性分析，不替代预定义主指标和确认性矩阵。",
            "forbidden_claim_cn": "不能写成所有可能的desirable overtaking behavior quality定义下都必然最优。",
        },
        {
            "claim_id": "MS2",
            "safe_claim_cn": "质量阈值敏感性可帮助解释规则专家、quality proposal 与 v6-safe 的差异。",
            "evidence": "tables/quality_threshold_sensitivity_grid.csv",
            "boundary_cn": "该分析只使用 source CSV 中的窗口聚合指标，不能恢复每个超车事件的完整轨迹细节。",
            "forbidden_claim_cn": "不能把后验阈值网格写成训练时优化目标或预注册实验。",
        },
    ]


def build_figure(paired, summary, out_base):
    register_cjk_font()
    plt.rcParams["axes.unicode_minus"] = False
    quality = [
        row
        for row in paired
        if row["algorithm"] == OURS and row["definition"] == "quality_overtake"
    ]
    heat = np.zeros((len(GRASS_THRESHOLDS), len(LATERAL_THRESHOLDS)))
    for row in quality:
        gi = GRASS_THRESHOLDS.index(float(row["grass_threshold"]))
        li = LATERAL_THRESHOLDS.index(float(row["lateral_threshold"]))
        heat[gi, li] = float(row["paired_delta"])
    fig, axes = plt.subplots(2, 2, figsize=(11.2, 8.2))
    ax = axes[0, 0]
    im = ax.imshow(heat, cmap="RdYlGn", vmin=-0.1, vmax=max(0.7, float(np.max(heat))))
    ax.set_xticks(range(len(LATERAL_THRESHOLDS)), [str(x) for x in LATERAL_THRESHOLDS])
    ax.set_yticks(range(len(GRASS_THRESHOLDS)), [str(x) for x in GRASS_THRESHOLDS])
    ax.set_xlabel("横向偏移阈值")
    ax.set_ylabel("超车窗口草地率阈值")
    ax.set_title("v6-safe 相对原始DLC的质量超车率增益")
    for i in range(heat.shape[0]):
        for j in range(heat.shape[1]):
            ax.text(j, i, f"{heat[i, j]:.2f}", ha="center", va="center", fontsize=9)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

    ax = axes[0, 1]
    algs = [row["algorithm"] for row in summary]
    labels = [row["algorithm_label_cn"] for row in summary]
    frac = [float(row["positive_delta_fraction"]) for row in summary]
    colors = ["#0F4D92" if alg == OURS else "#7A8A99" for alg in algs]
    ax.barh(labels, frac, color=colors)
    ax.set_xlim(0, 1.05)
    ax.set_xlabel("阈值设置中优于原始DLC的比例")
    ax.set_title("跨质量/耗时阈值的稳健性")
    for y, value in enumerate(frac):
        ax.text(value + 0.02, y, f"{value:.2f}", va="center", fontsize=9)

    ax = axes[1, 0]
    for lateral in [0.35, 0.50, 0.65]:
        values = [
            next(
                float(row["paired_delta"])
                for row in quality
                if float(row["grass_threshold"]) == grass and float(row["lateral_threshold"]) == lateral
            )
            for grass in GRASS_THRESHOLDS
        ]
        ax.plot(GRASS_THRESHOLDS, values, marker="o", label=f"横向≤{lateral}")
    ax.axhline(0, color="#333333", linewidth=0.8)
    ax.set_xlabel("超车窗口草地率阈值")
    ax.set_ylabel("paired delta")
    ax.set_title("阈值放宽时的增益曲线")
    ax.legend(frameon=False)

    ax = axes[1, 1]
    time_rows = [
        row
        for row in paired
        if row["algorithm"] == OURS
        and row["definition"] == "quality_and_time_bounded_overtake"
        and float(row["grass_threshold"]) == 0.2
        and float(row["lateral_threshold"]) == 0.5
    ]
    ax.bar(
        [str(int(float(row["time_threshold"]))) for row in time_rows],
        [float(row["paired_delta"]) for row in time_rows],
        color="#2F6BBD",
    )
    ax.axhline(0, color="#333333", linewidth=0.8)
    ax.set_xlabel("完成耗时阈值 step")
    ax.set_ylabel("paired delta")
    ax.set_title("加入完成耗时约束后的增益")
    fig.suptitle("指标阈值敏感性审计（中文图）", fontsize=15, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    paths = {}
    for ext in ["png", "pdf", "svg", "tiff"]:
        path = f"{out_base}.{ext}"
        fig.savefig(path, dpi=300 if ext in {"png", "tiff"} else None, bbox_inches="tight")
        paths[ext] = path
    plt.close(fig)
    return paths


def report_md(manifest, summary, boundaries):
    ours = next((row for row in summary if row["algorithm"] == OURS), {})
    lines = [
        "# 指标阈值敏感性审计",
        "",
        "该审计使用冻结的 240-run source data，后验改变“质量超车/Desirable overtaking behavior”的草地率、横向偏移和完成耗时阈值，检查当前算法相对原始 DLC world model 的结论是否依赖单一阈值设定。它不新增仿真样本，也不替代预定义主指标。",
        "",
        "## Summary",
        "",
        f"- Status: `{manifest['status']}`",
        f"- Source rows: {manifest['summary']['source_rows']}",
        f"- Algorithms: {manifest['summary']['algorithm_count']}",
        f"- Threshold settings: {manifest['summary']['threshold_settings']}",
        f"- Paired rows: {manifest['summary']['paired_rows']}",
        f"- v6-safe positive delta fraction: {fmt(ours.get('positive_delta_fraction'))}",
        f"- v6-safe minimum delta: {fmt(ours.get('min_delta'))}",
        f"- v6-safe median delta: {fmt(ours.get('median_delta'))}",
        "",
        "## Interpretation",
        "",
        "- 若 `paired_delta > 0`，表示在该阈值定义下目标算法的质量超车率高于原始 DLC world model。",
        "- `quality_overtake` 只约束完成超车、超车窗口草地率和横向偏移。",
        "- `quality_and_time_bounded_overtake` 进一步要求开始超车到完成超车时间低于给定阈值。",
        "- 该分析用于稳健性和写作边界，不应替代主文预定义的 desirable/on-track overtake 指标。",
        "",
        "## Robustness Summary",
        "",
        "| Algorithm | Positive fraction | Min delta | Median delta | Interpretation |",
        "|---|---:|---:|---:|---|",
    ]
    for row in summary:
        lines.append(
            f"| {row['algorithm_label_cn']} | {fmt(row['positive_delta_fraction'])} | {fmt(row['min_delta'])} | {fmt(row['median_delta'])} | {row['interpretation_cn']} |"
        )
    lines.extend(
        [
            "",
            "## Claim Boundaries",
            "",
            "| Claim | Evidence | Boundary | Forbidden wording |",
            "|---|---|---|---|",
        ]
    )
    for row in boundaries:
        lines.append(
            f"| {row['safe_claim_cn']} | `{row['evidence']}` | {row['boundary_cn']} | {row['forbidden_claim_cn']} |"
        )
    lines.extend(
        [
            "",
            "## Regeneration Command",
            "",
            "```bash",
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_metric_sensitivity_audit.py --out-dir outputs/tits_dynamic_graph/tits_metric_sensitivity_audit",
            "```",
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Export metric-threshold sensitivity audit for the T-ITS dynamic DLC study.")
    parser.add_argument("--source-csv", default="outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv")
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/tits_metric_sensitivity_audit")
    args = parser.parse_args()

    rows = read_csv(args.source_csv)
    out_dir = Path(args.out_dir)
    materials = out_dir / "materials"
    tables = out_dir / "tables"
    figures = out_dir / "figures"
    materials.mkdir(parents=True, exist_ok=True)
    tables.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)

    sensitivity = grid_rows(rows)
    paired = paired_rows(rows, sensitivity)
    summary = robustness_summary(paired)
    boundaries = claim_boundaries(summary)
    figure_paths = build_figure(paired, summary, figures / "figure_metric_sensitivity_cn")

    algorithm_count = len({row["algorithm"] for row in rows})
    threshold_settings = len({row["threshold_id"] for row in sensitivity})
    qa = {
        "status": "pass" if len(rows) == 240 and algorithm_count == 8 and threshold_settings == 47 else "review_required",
        "source_csv": args.source_csv,
        "source_rows": len(rows),
        "algorithm_count": algorithm_count,
        "threshold_settings": threshold_settings,
        "paired_rows": len(paired),
        "ours_positive_delta_fraction": next((row["positive_delta_fraction"] for row in summary if row["algorithm"] == OURS), None),
        "note": "Post-hoc metric-threshold sensitivity audit over frozen source data; not a new simulation matrix.",
    }
    manifest = {
        "status": qa["status"],
        "out_dir": args.out_dir,
        "summary": {
            "source_rows": len(rows),
            "algorithm_count": algorithm_count,
            "threshold_settings": threshold_settings,
            "sensitivity_rows": len(sensitivity),
            "paired_rows": len(paired),
            "summary_rows": len(summary),
        },
        "paths": {},
        "figures": figure_paths,
    }
    manifest["paths"] = {
        "report_md": write_text(materials / "METRIC_SENSITIVITY_AUDIT.md", report_md(manifest, summary, boundaries)),
        "qa_json": write_json(materials / "METRIC_SENSITIVITY_QA.json", qa),
        "threshold_grid_csv": write_csv(
            tables / "quality_threshold_sensitivity_grid.csv",
            sensitivity,
            [
                "threshold_id",
                "definition",
                "grass_threshold",
                "lateral_threshold",
                "time_threshold",
                "algorithm",
                "algorithm_label_cn",
                "n",
                "rate",
                "ci95_low",
                "ci95_high",
            ],
        ),
        "paired_vs_dlc_csv": write_csv(
            tables / "paired_threshold_sensitivity_vs_dlc.csv",
            paired,
            [
                "threshold_id",
                "definition",
                "grass_threshold",
                "lateral_threshold",
                "time_threshold",
                "algorithm",
                "algorithm_label_cn",
                "baseline",
                "baseline_label_cn",
                "n_paired",
                "algorithm_rate",
                "baseline_rate",
                "paired_delta",
                "paired_delta_ci95_low",
                "paired_delta_ci95_high",
                "positive_cases",
                "negative_cases",
                "equal_cases",
            ],
        ),
        "robustness_summary_csv": write_csv(
            tables / "robustness_summary_by_algorithm.csv",
            summary,
            [
                "algorithm",
                "algorithm_label_cn",
                "threshold_settings",
                "positive_delta_settings",
                "nonnegative_delta_settings",
                "positive_delta_fraction",
                "nonnegative_delta_fraction",
                "min_delta",
                "median_delta",
                "max_delta",
                "quality_only_min_delta",
                "time_bounded_min_delta",
                "interpretation_cn",
            ],
        ),
        "claim_boundaries_csv": write_csv(
            tables / "metric_sensitivity_claim_boundaries.csv",
            boundaries,
            ["claim_id", "safe_claim_cn", "evidence", "boundary_cn", "forbidden_claim_cn"],
        ),
    }
    manifest["paths"]["manifest_json"] = write_json(out_dir / "tits_metric_sensitivity_audit_manifest.json", manifest)
    print(json.dumps({"manifest": manifest["paths"]["manifest_json"], "status": manifest["status"], "summary": manifest["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
