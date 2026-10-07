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
PRIMARY = "v6_runtime_dynamic_neighborhood_safe"
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
CN_LABEL = {
    "v6_runtime_dynamic_neighborhood_safe": "本文算法-safe",
    "v6_runtime_dynamic_neighborhood": "动态邻域DLC",
    "quality_proposal_dlc_world_v1": "Quality-DLC",
    "dlc_world_original": "原始DLC",
    "dlc_world_balanced": "DLC-balanced",
    "dlc_world_safety": "DLC-safety",
    "dlc_world_fast": "DLC-fast",
    "rule_expert_gate": "规则专家",
}


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


def case_key(row):
    return (
        row.get("_benchmark", ""),
        row.get("num_agents", ""),
        row.get("seed", ""),
        row.get("track_path", ""),
        row.get("traffic_profile", ""),
    )


def case_id(row):
    benchmark, num_agents, seed, track, traffic = case_key(row)
    track_label = "monza" if str(track).endswith(".npz") else str(track)
    return f"{benchmark}|n{num_agents}|seed{seed}|{track_label}|{traffic}"


def mean(values):
    vals = [f(v) for v in values]
    vals = [v for v in vals if v is not None]
    return float(np.mean(vals)) if vals else ""


def bootstrap_ci(values, seed=20260625, n_boot=3000):
    vals = [f(v) for v in values]
    vals = np.asarray([v for v in vals if v is not None], dtype=float)
    if vals.size == 0:
        return "", "", ""
    center = float(vals.mean())
    if vals.size == 1:
        return center, center, center
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, vals.size, size=(n_boot, vals.size))
    boot = vals[idx].mean(axis=1)
    lo, hi = np.quantile(boot, [0.025, 0.975])
    return center, float(lo), float(hi)


def load_trace_min_pair(summary_path):
    summary_path = Path(summary_path)
    if not summary_path.exists():
        return "", "", ""
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    trace_path = Path(summary.get("trace_path", ""))
    if not trace_path.exists():
        trace_path = summary_path.parent.parent / "traces" / summary_path.name.replace(".summary.json", ".trace.json")
    if not trace_path.exists():
        return "", "", ""
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    vals = [f(row.get("min_pair_distance")) for row in trace if isinstance(row, dict)]
    vals = [v for v in vals if v is not None]
    if not vals:
        return "", "", ""
    low = sum(1 for v in vals if v < 2.0) / len(vals)
    return min(vals), float(np.mean(vals)), low


def build_run_rows(rows, trace_sample_limit):
    out = []
    sampled = 0
    for row in rows:
        min_pair_trace = mean_pair_trace = low_distance_rate = ""
        if sampled < trace_sample_limit and row.get("algorithm") in {PRIMARY, BASELINE, "rule_expert_gate", "quality_proposal_dlc_world_v1"}:
            min_pair_trace, mean_pair_trace, low_distance_rate = load_trace_min_pair(row.get("_summary_file", ""))
            sampled += 1
        grass = f(row.get("target_grass_rate")) or 0.0
        lateral = f(row.get("target_mean_abs_lateral")) or 0.0
        collision = f(row.get("collision_or_contact_proxy")) or 0.0
        unrecovered = f(row.get("unrecovered_grass_excursion_count")) or 0.0
        offtrack_overtake = (f(row.get("overtake_success_rate")) or 0.0) > 0 and (f(row.get("on_track_overtake_rate")) or 0.0) < 1.0
        risk_flags = []
        if collision > 0:
            risk_flags.append("contact_proxy")
        if grass > 0.5:
            risk_flags.append("high_grass")
        if lateral > 0.25:
            risk_flags.append("high_lateral")
        if unrecovered > 0:
            risk_flags.append("unrecovered_grass")
        if offtrack_overtake:
            risk_flags.append("offtrack_overtake")
        if not risk_flags:
            risk_flags.append("none")
        out.append(
            {
                "case_id": case_id(row),
                "benchmark": row.get("_benchmark", ""),
                "num_agents": row.get("num_agents", ""),
                "seed": row.get("seed", ""),
                "track_path": row.get("track_path", ""),
                "traffic_profile": row.get("traffic_profile", ""),
                "algorithm": row.get("algorithm", ""),
                "algorithm_label_cn": row.get("algorithm_label_cn") or CN_LABEL.get(row.get("algorithm", ""), row.get("algorithm", "")),
                "target_grass_rate": row.get("target_grass_rate", ""),
                "target_mean_abs_lateral": row.get("target_mean_abs_lateral", ""),
                "overtake_window_grass_rate_mean": row.get("overtake_window_grass_rate_mean", ""),
                "overtake_window_max_abs_lateral_mean": row.get("overtake_window_max_abs_lateral_mean", ""),
                "grass_excursion_count": row.get("grass_excursion_count", ""),
                "unrecovered_grass_excursion_count": row.get("unrecovered_grass_excursion_count", ""),
                "grass_recovery_time_mean": row.get("grass_recovery_time_mean", ""),
                "collision_or_contact_proxy": row.get("collision_or_contact_proxy", ""),
                "on_track_overtake_rate": row.get("on_track_overtake_rate", ""),
                "elegant_overtake_rate": row.get("elegant_overtake_rate", ""),
                "min_pair_distance_trace": min_pair_trace,
                "mean_pair_distance_trace": mean_pair_trace,
                "low_distance_rate_trace_lt2": low_distance_rate,
                "risk_flags": ";".join(risk_flags),
                "summary_file": row.get("_summary_file", ""),
            }
        )
    return out


def summarize_by_algorithm(run_rows):
    out = []
    for algorithm in ALGORITHMS:
        rows = [row for row in run_rows if row["algorithm"] == algorithm]
        if not rows:
            continue
        item = {
            "algorithm": algorithm,
            "algorithm_label_cn": rows[0]["algorithm_label_cn"],
            "n": len(rows),
            "contact_proxy_rate": mean(1.0 if (f(row["collision_or_contact_proxy"]) or 0.0) > 0 else 0.0 for row in rows),
            "high_grass_rate": mean(1.0 if (f(row["target_grass_rate"]) or 0.0) > 0.5 else 0.0 for row in rows),
            "high_lateral_rate": mean(1.0 if (f(row["target_mean_abs_lateral"]) or 0.0) > 0.25 else 0.0 for row in rows),
            "offtrack_overtake_rate": mean(1.0 if "offtrack_overtake" in row["risk_flags"] else 0.0 for row in rows),
            "unrecovered_grass_rate": mean(1.0 if (f(row["unrecovered_grass_excursion_count"]) or 0.0) > 0 else 0.0 for row in rows),
            "target_grass_mean": mean(row["target_grass_rate"] for row in rows),
            "target_lateral_mean": mean(row["target_mean_abs_lateral"] for row in rows),
            "recovery_time_mean": mean(row["grass_recovery_time_mean"] for row in rows),
            "trace_min_pair_distance_min": min([f(row["min_pair_distance_trace"]) for row in rows if f(row["min_pair_distance_trace"]) is not None], default=""),
            "trace_low_distance_rate_mean": mean(row["low_distance_rate_trace_lt2"] for row in rows),
        }
        out.append(item)
    return out


def build_pair_rows(run_rows):
    indexed = defaultdict(dict)
    for row in run_rows:
        indexed[row["case_id"]][row["algorithm"]] = row
    metrics = [
        ("target_grass_rate", False, "目标车草地率"),
        ("target_mean_abs_lateral", False, "平均横向偏移"),
        ("grass_recovery_time_mean", False, "草地恢复时间"),
        ("unrecovered_grass_excursion_count", False, "未恢复草地次数"),
        ("on_track_overtake_rate", True, "赛道内超车率"),
        ("elegant_overtake_rate", True, "Desirable overtaking behavior rate"),
    ]
    out = []
    for case, by_alg in sorted(indexed.items()):
        if PRIMARY not in by_alg or BASELINE not in by_alg:
            continue
        ours = by_alg[PRIMARY]
        base = by_alg[BASELINE]
        for metric, higher_better, metric_cn in metrics:
            a = f(ours.get(metric))
            b = f(base.get(metric))
            if a is None or b is None:
                outcome = "missing"
                raw_delta = ""
                improvement = ""
            else:
                raw_delta = a - b
                improvement = raw_delta if higher_better else -raw_delta
                outcome = "win" if improvement > 1e-9 else "loss" if improvement < -1e-9 else "tie"
            out.append(
                {
                    "case_id": case,
                    "metric": metric,
                    "metric_cn": metric_cn,
                    "higher_is_better": higher_better,
                    "primary_value": ours.get(metric, ""),
                    "baseline_value": base.get(metric, ""),
                    "raw_delta_primary_minus_baseline": raw_delta,
                    "improvement_signed": improvement,
                    "outcome": outcome,
                    "primary_summary_file": ours.get("summary_file", ""),
                    "baseline_summary_file": base.get("summary_file", ""),
                }
            )
    return out


def summarize_pairs(pair_rows):
    out = []
    by_metric = defaultdict(list)
    for row in pair_rows:
        by_metric[row["metric"]].append(row)
    for metric, rows in by_metric.items():
        valid = [row for row in rows if row["outcome"] in {"win", "loss", "tie"}]
        out.append(
            {
                "metric": metric,
                "metric_cn": rows[0]["metric_cn"],
                "n_cases": len(rows),
                "n_valid": len(valid),
                "wins": sum(1 for row in valid if row["outcome"] == "win"),
                "ties": sum(1 for row in valid if row["outcome"] == "tie"),
                "losses": sum(1 for row in valid if row["outcome"] == "loss"),
                "mean_signed_improvement": mean(row["improvement_signed"] for row in valid),
            }
        )
    return out


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


def make_figure(summary_rows, pair_summary, out_dir):
    register_cjk_font()
    mpl.rcParams.update({"svg.fonttype": "none", "pdf.fonttype": 42, "font.size": 8})
    selected = [row for row in summary_rows if row["algorithm"] in {PRIMARY, "v6_runtime_dynamic_neighborhood", "quality_proposal_dlc_world_v1", BASELINE, "rule_expert_gate"}]
    labels = [row["algorithm_label_cn"] for row in selected]
    x = np.arange(len(selected))

    fig, axes = plt.subplots(2, 2, figsize=(7.2, 5.0), constrained_layout=True)
    fig.suptitle("安全代理指标审计：草地、横向偏移、接触代理与恢复", fontsize=11, fontweight="bold")

    ax = axes[0, 0]
    ax.bar(x - 0.18, [f(row["target_grass_mean"]) or 0 for row in selected], width=0.36, label="目标草地率", color="#E45756")
    ax.bar(x + 0.18, [f(row["target_lateral_mean"]) or 0 for row in selected], width=0.36, label="平均横向偏移", color="#4C78A8")
    ax.set_xticks(x, labels, rotation=18, ha="right")
    ax.set_ylim(0, 1.0)
    ax.set_title("风险暴露均值")
    ax.legend(fontsize=7)

    ax = axes[0, 1]
    ax.bar(x - 0.2, [f(row["high_grass_rate"]) or 0 for row in selected], width=0.2, label="高草地")
    ax.bar(x, [f(row["offtrack_overtake_rate"]) or 0 for row in selected], width=0.2, label="草地/非赛道超车")
    ax.bar(x + 0.2, [f(row["unrecovered_grass_rate"]) or 0 for row in selected], width=0.2, label="未恢复草地")
    ax.set_xticks(x, labels, rotation=18, ha="right")
    ax.set_ylim(0, 1.0)
    ax.set_title("风险 case 占比")
    ax.legend(fontsize=6)

    ax = axes[1, 0]
    metrics = ["target_grass_rate", "target_mean_abs_lateral", "grass_recovery_time_mean", "on_track_overtake_rate", "elegant_overtake_rate"]
    rows = [row for row in pair_summary if row["metric"] in metrics]
    rows = sorted(rows, key=lambda row: metrics.index(row["metric"]))
    y = np.arange(len(rows))
    wins = np.asarray([int(row["wins"]) for row in rows], dtype=float)
    ties = np.asarray([int(row["ties"]) for row in rows], dtype=float)
    losses = np.asarray([int(row["losses"]) for row in rows], dtype=float)
    ax.barh(y, wins, color="#1976B9", label="胜")
    ax.barh(y, ties, left=wins, color="#B8B8B8", label="平")
    ax.barh(y, losses, left=wins + ties, color="#D45A48", label="负")
    ax.set_yticks(y, [row["metric_cn"] for row in rows])
    ax.invert_yaxis()
    ax.set_xlabel("case 数")
    ax.set_title("本文算法相对原始DLC逐 case 安全代理胜负")
    ax.legend(fontsize=7, ncols=3)

    ax = axes[1, 1]
    ax.bar(x, [f(row["trace_low_distance_rate_mean"]) or 0 for row in selected], color="#72B7B2")
    ax.set_xticks(x, labels, rotation=18, ha="right")
    ax.set_ylim(0, 1.0)
    ax.set_title("trace 抽样：低车距率(<2m proxy)")
    ax.set_ylabel("窗口均值")

    paths = {}
    for suffix in ["svg", "pdf", "png", "tiff"]:
        path = Path(out_dir) / "figures" / f"figure_safety_proxy_audit_cn.{suffix}"
        path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, dpi=300 if suffix in {"png", "tiff"} else None)
        paths[suffix] = str(path)
    plt.close(fig)
    return paths


def build_markdown(summary, summary_rows, pair_summary):
    lines = [
        "# T-ITS Safety Proxy Audit Pack",
        "",
        "该包集中审计正式 240-run 在线评估中的安全代理指标，包括目标车草地暴露、横向偏移、草地恢复、非赛道超车、接触/碰撞代理以及 trace 抽样的最小车距。它用于约束论文中的安全表述：支持“仿真安全代理指标改善/边界透明”，不支持真实道路安全认证或保证无碰撞。",
        "",
        "## Summary",
        "",
    ]
    for key, value in summary.items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Algorithm-Level Safety Proxy Summary",
            "",
            "| Algorithm | n | Grass mean | Lateral mean | High-grass rate | Off-track overtake rate | Contact proxy rate |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in summary_rows:
        lines.append(
            f"| {row['algorithm_label_cn']} | {row['n']} | {fmt(row['target_grass_mean'])} | {fmt(row['target_lateral_mean'])} | {fmt(row['high_grass_rate'])} | {fmt(row['offtrack_overtake_rate'])} | {fmt(row['contact_proxy_rate'])} |"
        )
    lines.extend(
        [
            "",
            "## Paired Primary-vs-DLC Safety Proxy Deltas",
            "",
            "| Metric | Wins | Ties | Losses | Mean signed improvement |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for row in pair_summary:
        lines.append(
            f"| {row['metric_cn']} | {row['wins']} | {row['ties']} | {row['losses']} | {fmt(row['mean_signed_improvement'])} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation Boundary",
            "",
            "- 接触/碰撞字段是仿真代理指标；当前正式矩阵中该代理为 0，并不等价于真实车辆安全认证。",
            "- 草地率和横向偏移应与成功率、Desirable overtaking behavior rate、完成耗时共同报告，避免把高速越界超车误读为安全改进。",
            "- trace 低车距率只对抽样运行提供过程诊断，正式总体结论仍以 source data、paired statistics、casewise diagnostic 和 event consistency audit 为主。",
            "",
            "## Key Files",
            "",
            "- Run-level safety proxies: `outputs/tits_dynamic_graph/tits_safety_proxy_audit_pack/tables/safety_proxy_run_rows.csv`",
            "- Algorithm summary: `outputs/tits_dynamic_graph/tits_safety_proxy_audit_pack/tables/safety_proxy_algorithm_summary.csv`",
            "- Paired deltas: `outputs/tits_dynamic_graph/tits_safety_proxy_audit_pack/tables/safety_proxy_primary_vs_dlc_pairs.csv`",
            "- Chinese figure: `outputs/tits_dynamic_graph/tits_safety_proxy_audit_pack/figures/figure_safety_proxy_audit_cn.svg`",
            "",
            "## Regeneration Command",
            "",
            "```bash",
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_safety_proxy_audit_pack.py --out-dir outputs/tits_dynamic_graph/tits_safety_proxy_audit_pack",
            "```",
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Export safety-proxy audit materials for the T-ITS dynamic graph study.")
    parser.add_argument("--source-csv", default=SOURCE_CSV)
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/tits_safety_proxy_audit_pack")
    parser.add_argument("--trace-sample-limit", type=int, default=80)
    args = parser.parse_args()

    rows = read_csv(args.source_csv)
    out_dir = Path(args.out_dir)
    run_rows = build_run_rows(rows, args.trace_sample_limit)
    summary_rows = summarize_by_algorithm(run_rows)
    pair_rows = build_pair_rows(run_rows)
    pair_summary = summarize_pairs(pair_rows)
    figure_paths = make_figure(summary_rows, pair_summary, out_dir)

    primary_summary = next((row for row in summary_rows if row["algorithm"] == PRIMARY), {})
    baseline_summary = next((row for row in summary_rows if row["algorithm"] == BASELINE), {})
    summary = {
        "status": "pass",
        "source_csv": args.source_csv,
        "source_rows": len(rows),
        "algorithm_count": len({row["algorithm"] for row in rows}),
        "matched_case_count": len({case_key(row) for row in rows}),
        "primary_algorithm": PRIMARY,
        "baseline_algorithm": BASELINE,
        "primary_grass_mean": fmt(primary_summary.get("target_grass_mean")),
        "baseline_grass_mean": fmt(baseline_summary.get("target_grass_mean")),
        "primary_high_grass_rate": fmt(primary_summary.get("high_grass_rate")),
        "baseline_high_grass_rate": fmt(baseline_summary.get("high_grass_rate")),
        "contact_proxy_positive_runs": sum(1 for row in run_rows if (f(row["collision_or_contact_proxy"]) or 0.0) > 0),
        "trace_sampled_runs": sum(1 for row in run_rows if f(row["min_pair_distance_trace"]) is not None),
        "boundary": "Simulation-only safety proxies; not a real-road safety certificate.",
    }
    paths = {
        "report_md": write_text(out_dir / "materials" / "SAFETY_PROXY_AUDIT_PACK.md", build_markdown(summary, summary_rows, pair_summary)),
        "report_json": write_json(out_dir / "materials" / "SAFETY_PROXY_AUDIT_PACK.json", {"summary": summary, "algorithm_summary": summary_rows, "pair_summary": pair_summary}),
        "run_rows_csv": write_csv(out_dir / "tables" / "safety_proxy_run_rows.csv", run_rows, list(run_rows[0].keys()) if run_rows else ["case_id"]),
        "algorithm_summary_csv": write_csv(out_dir / "tables" / "safety_proxy_algorithm_summary.csv", summary_rows, list(summary_rows[0].keys()) if summary_rows else ["algorithm"]),
        "pairs_csv": write_csv(out_dir / "tables" / "safety_proxy_primary_vs_dlc_pairs.csv", pair_rows, list(pair_rows[0].keys()) if pair_rows else ["case_id"]),
        "pair_summary_csv": write_csv(out_dir / "tables" / "safety_proxy_primary_vs_dlc_pair_summary.csv", pair_summary, list(pair_summary[0].keys()) if pair_summary else ["metric"]),
        "figure_svg": figure_paths["svg"],
        "figure_pdf": figure_paths["pdf"],
        "figure_png": figure_paths["png"],
        "figure_tiff": figure_paths["tiff"],
    }
    manifest = {"status": summary["status"], "out_dir": args.out_dir, "summary": summary, "paths": paths}
    manifest_path = write_json(out_dir / "tits_safety_proxy_audit_pack_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, "status": summary["status"], "summary": summary}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
