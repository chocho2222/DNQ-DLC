#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np


SOURCE_CSV = "outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv"
BASELINE = "dlc_world_original"
PRIMARY = "v6_runtime_dynamic_neighborhood_safe"

PAIR_METRICS = [
    ("overtake_success_rate", "超车成功", True, "binary"),
    ("elegant_overtake_rate", "Desirable overtaking behavior", True, "binary"),
    ("on_track_overtake_rate", "赛道内超车", True, "binary"),
    ("overtake_start_to_complete_time", "超车完成耗时", False, "conditional_time"),
    ("target_grass_rate", "草地暴露", False, "continuous"),
    ("rank_gain", "名次提升", True, "continuous"),
]
FAILURE_RULES = [
    ("no_overtake", "未发生超车"),
    ("off_track_overtake", "超车不在赛道内"),
    ("non_elegant_overtake", "超车不符合 desirable overtaking behavior 标准"),
    ("high_grass_exposure", "草地暴露过高"),
    ("long_overtake_window", "超车耗时过长"),
    ("lap_not_completed", "目标车未完赛一圈"),
    ("high_latency", "决策延迟偏高"),
]
CORE_FAILURE_NAMES = {
    "no_overtake",
    "off_track_overtake",
    "non_elegant_overtake",
    "high_grass_exposure",
    "long_overtake_window",
}
ALGORITHM_ORDER = [
    "v6_runtime_dynamic_neighborhood_safe",
    "v6_runtime_dynamic_neighborhood",
    "quality_proposal_dlc_world_v1",
    "dlc_world_original",
    "dlc_world_balanced",
    "dlc_world_safety",
    "dlc_world_fast",
    "rule_expert_gate",
]
CN_LABEL_FALLBACK = {
    "v6_runtime_dynamic_neighborhood_safe": "v6动态邻域DLC-safe",
    "v6_runtime_dynamic_neighborhood": "v6动态邻域DLC",
    "quality_proposal_dlc_world_v1": "质量Proposal-DLC",
    "dlc_world_original": "DLC世界模型",
    "dlc_world_balanced": "DLC-balanced",
    "dlc_world_safety": "DLC-safety",
    "dlc_world_fast": "DLC-fast",
    "rule_expert_gate": "规则专家",
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


def as_bool(value):
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def fmt(value, digits=3):
    value = as_float(value)
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


def case_key(row):
    return (
        row.get("_benchmark", ""),
        row.get("num_agents", ""),
        row.get("seed", ""),
        row.get("track_path", ""),
        row.get("traffic_profile", ""),
    )


def case_id(key):
    benchmark, num_agents, seed, track, traffic = key
    track_name = "monza" if str(track).endswith(".npz") else str(track)
    return f"{benchmark}|n{num_agents}|seed{seed}|{track_name}|{traffic}"


def algorithm_label(row_or_rows, algorithm):
    if isinstance(row_or_rows, list):
        for row in row_or_rows:
            if row.get("algorithm") == algorithm and row.get("algorithm_label_cn"):
                return row["algorithm_label_cn"]
    elif row_or_rows and row_or_rows.get("algorithm_label_cn"):
        return row_or_rows["algorithm_label_cn"]
    return CN_LABEL_FALLBACK.get(algorithm, algorithm)


def build_index(rows):
    indexed = defaultdict(dict)
    for row in rows:
        indexed[case_key(row)][row["algorithm"]] = row
    return indexed


def compare_values(a_row, b_row, metric, higher_is_better, metric_type, eps=1e-9):
    a = as_float(a_row.get(metric))
    b = as_float(b_row.get(metric))
    a_success = as_float(a_row.get("overtake_success_rate")) == 1.0
    b_success = as_float(b_row.get("overtake_success_rate")) == 1.0

    if metric_type == "conditional_time":
        if a_success and not b_success:
            return "win", "", "", "candidate_overtook_baseline_failed"
        if b_success and not a_success:
            return "loss", "", "", "baseline_overtook_candidate_failed"
        if not a_success and not b_success:
            return "not_applicable", "", "", "neither_algorithm_overtook"
        if a is None or b is None:
            return "missing", "", "", "time_missing_after_success"

    if a is None or b is None:
        return "missing", "", "", "metric_missing"
    raw_delta = a - b
    improvement = raw_delta if higher_is_better else -raw_delta
    if improvement > eps:
        outcome = "win"
    elif improvement < -eps:
        outcome = "loss"
    else:
        outcome = "tie"
    return outcome, raw_delta, improvement, ""


def failure_flags(row):
    success = as_float(row.get("overtake_success_rate")) == 1.0
    on_track = as_float(row.get("on_track_overtake_rate")) == 1.0
    elegant = as_float(row.get("elegant_overtake_rate")) == 1.0
    grass = as_float(row.get("target_grass_rate")) or 0.0
    completion = as_float(row.get("overtake_start_to_complete_time"))
    completed_lap = as_bool(row.get("target_completed_lap"))
    latency = as_float(row.get("compute_latency_ms")) or 0.0
    flags = {
        "no_overtake": not success,
        "off_track_overtake": success and not on_track,
        "non_elegant_overtake": success and not elegant,
        "high_grass_exposure": grass > 0.50,
        "long_overtake_window": success and completion is not None and completion > 300.0,
        "lap_not_completed": not completed_lap,
        "high_latency": latency > 100.0,
    }
    active = [name for name, _ in FAILURE_RULES if flags[name] and name in CORE_FAILURE_NAMES]
    if not active:
        active = ["none"]
    return flags, active


def build_case_failure_rows(rows):
    out = []
    for row in rows:
        key = case_key(row)
        flags, active = failure_flags(row)
        out.append(
            {
                "case_id": case_id(key),
                "benchmark": key[0],
                "num_agents": key[1],
                "seed": key[2],
                "track_path": key[3],
                "traffic_profile": key[4],
                "algorithm": row["algorithm"],
                "algorithm_label_cn": algorithm_label(row, row["algorithm"]),
                "active_failure_modes": ";".join(active),
                **{name: int(flags[name]) for name, _ in FAILURE_RULES},
                "overtake_success_rate": row.get("overtake_success_rate", ""),
                "elegant_overtake_rate": row.get("elegant_overtake_rate", ""),
                "on_track_overtake_rate": row.get("on_track_overtake_rate", ""),
                "target_grass_rate": row.get("target_grass_rate", ""),
                "overtake_start_to_complete_time": row.get("overtake_start_to_complete_time", ""),
                "compute_latency_ms": row.get("compute_latency_ms", ""),
                "summary_file": row.get("_summary_file", ""),
            }
        )
    return out


def build_pair_rows(rows, baseline):
    indexed = build_index(rows)
    algorithms = sorted(
        {row["algorithm"] for row in rows if row["algorithm"] != baseline},
        key=lambda alg: ALGORITHM_ORDER.index(alg) if alg in ALGORITHM_ORDER else 999,
    )
    out = []
    for key, values in sorted(indexed.items()):
        if baseline not in values:
            continue
        b_row = values[baseline]
        for algorithm in algorithms:
            if algorithm not in values:
                continue
            a_row = values[algorithm]
            for metric, metric_cn, higher_is_better, metric_type in PAIR_METRICS:
                outcome, raw_delta, improvement, note = compare_values(
                    a_row, b_row, metric, higher_is_better, metric_type
                )
                out.append(
                    {
                        "case_id": case_id(key),
                        "benchmark": key[0],
                        "num_agents": key[1],
                        "seed": key[2],
                        "track_path": key[3],
                        "traffic_profile": key[4],
                        "algorithm": algorithm,
                        "algorithm_label_cn": algorithm_label(rows, algorithm),
                        "baseline": baseline,
                        "baseline_label_cn": algorithm_label(rows, baseline),
                        "metric": metric,
                        "metric_cn": metric_cn,
                        "higher_is_better": higher_is_better,
                        "metric_type": metric_type,
                        "candidate_value": a_row.get(metric, ""),
                        "baseline_value": b_row.get(metric, ""),
                        "raw_delta_candidate_minus_baseline": raw_delta,
                        "improvement_signed": improvement,
                        "outcome": outcome,
                        "note": note,
                        "candidate_summary_file": a_row.get("_summary_file", ""),
                        "baseline_summary_file": b_row.get("_summary_file", ""),
                    }
                )
    return out


def summarize_pairs(pair_rows):
    groups = defaultdict(list)
    for row in pair_rows:
        groups[(row["algorithm"], row["metric"])].append(row)
    out = []
    for (algorithm, metric), rows in sorted(groups.items(), key=lambda item: (ALGORITHM_ORDER.index(item[0][0]) if item[0][0] in ALGORITHM_ORDER else 999, item[0][1])):
        counts = Counter(row["outcome"] for row in rows)
        valid = [row for row in rows if row["outcome"] in {"win", "loss", "tie"}]
        improvements = [as_float(row["improvement_signed"]) for row in valid if as_float(row["improvement_signed"]) is not None]
        mean_improvement = float(np.mean(improvements)) if improvements else None
        out.append(
            {
                "algorithm": algorithm,
                "algorithm_label_cn": rows[0]["algorithm_label_cn"],
                "baseline": rows[0]["baseline"],
                "metric": metric,
                "metric_cn": rows[0]["metric_cn"],
                "n_cases": len(rows),
                "n_valid": len(valid),
                "wins": counts.get("win", 0),
                "losses": counts.get("loss", 0),
                "ties": counts.get("tie", 0),
                "not_applicable": counts.get("not_applicable", 0),
                "missing": counts.get("missing", 0),
                "win_rate_valid": counts.get("win", 0) / len(valid) if valid else "",
                "loss_rate_valid": counts.get("loss", 0) / len(valid) if valid else "",
                "mean_signed_improvement": mean_improvement if mean_improvement is not None else "",
            }
        )
    return out


def summarize_failures(case_failure_rows):
    groups = defaultdict(list)
    for row in case_failure_rows:
        groups[row["algorithm"]].append(row)
    out = []
    for algorithm, rows in sorted(groups.items(), key=lambda item: ALGORITHM_ORDER.index(item[0]) if item[0] in ALGORITHM_ORDER else 999):
        item = {
            "algorithm": algorithm,
            "algorithm_label_cn": rows[0]["algorithm_label_cn"],
            "n_cases": len(rows),
            "no_failure_count": sum(1 for row in rows if row["active_failure_modes"] == "none"),
            "no_failure_rate": sum(1 for row in rows if row["active_failure_modes"] == "none") / len(rows) if rows else "",
        }
        for name, _ in FAILURE_RULES:
            count = sum(int(row[name]) for row in rows)
            item[f"{name}_count"] = count
            item[f"{name}_rate"] = count / len(rows) if rows else ""
        out.append(item)
    return out


def representative_case_rows(pair_rows):
    wanted_metrics = {"overtake_success_rate", "elegant_overtake_rate", "on_track_overtake_rate", "target_grass_rate"}
    grouped = defaultdict(list)
    for row in pair_rows:
        if row["algorithm"] == PRIMARY and row["metric"] in wanted_metrics:
            grouped[row["case_id"]].append(row)
    out = []
    for case, rows in sorted(grouped.items()):
        wins = sum(1 for row in rows if row["outcome"] == "win")
        losses = sum(1 for row in rows if row["outcome"] == "loss")
        ties = sum(1 for row in rows if row["outcome"] == "tie")
        profile = "dominant_win" if wins >= 3 and losses == 0 else "mixed" if wins > 0 and losses > 0 else "no_clear_gain"
        first = rows[0]
        out.append(
            {
                "case_id": case,
                "benchmark": first["benchmark"],
                "num_agents": first["num_agents"],
                "seed": first["seed"],
                "track_path": first["track_path"],
                "traffic_profile": first["traffic_profile"],
                "primary_vs_dlc_wins": wins,
                "primary_vs_dlc_losses": losses,
                "primary_vs_dlc_ties": ties,
                "case_profile": profile,
            }
        )
    return out


def build_worst_case_cards(case_failure_rows, pair_rows, limit=10):
    pair_by_case_metric = {
        (row["case_id"], row["metric"]): row
        for row in pair_rows
        if row["algorithm"] == PRIMARY
    }
    rows = []
    for row in case_failure_rows:
        if row["algorithm"] != PRIMARY:
            continue
        grass = as_float(row.get("target_grass_rate")) or 0.0
        completion = as_float(row.get("overtake_start_to_complete_time"))
        active = [item for item in row["active_failure_modes"].split(";") if item and item != "none"]
        score = 0.0
        score += 5.0 if row["no_overtake"] else 0.0
        score += 4.0 if row["off_track_overtake"] else 0.0
        score += 4.0 if row["non_elegant_overtake"] else 0.0
        score += 3.0 if row["high_grass_exposure"] else 0.0
        score += 2.0 if row["long_overtake_window"] else 0.0
        score += min(grass, 1.0)
        if completion is not None and completion > 300.0:
            score += min((completion - 300.0) / 300.0, 1.0)
        outcomes = {}
        for metric, metric_cn, _, _ in PAIR_METRICS:
            item = pair_by_case_metric.get((row["case_id"], metric))
            if item:
                outcomes[metric] = f"{metric_cn}:{item['outcome']}"
        if row["no_overtake"]:
            primary_issue = "no_overtake"
            reviewer_wording = "Report as a failed overtaking case rather than hiding it inside aggregate success rates."
        elif row["off_track_overtake"] or row["non_elegant_overtake"]:
            primary_issue = "non_elegant_or_off_track_overtake"
            reviewer_wording = "Report as a successful but low-quality overtake; pair it with desirable/on-track metrics."
        elif row["high_grass_exposure"]:
            primary_issue = "high_grass_exposure"
            reviewer_wording = "Report as residual off-track exposure and avoid claiming the method always remains on track."
        elif row["long_overtake_window"]:
            primary_issue = "long_overtake_window"
            reviewer_wording = "Report as an efficiency tail case and keep completion-time n and distribution visible."
        else:
            primary_issue = "minor_or_no_core_failure"
            reviewer_wording = "Use only as supporting context; formal claims should stay tied to aggregate source data."
        rows.append(
            {
                "case_id": row["case_id"],
                "benchmark": row["benchmark"],
                "num_agents": row["num_agents"],
                "seed": row["seed"],
                "track_path": row["track_path"],
                "traffic_profile": row["traffic_profile"],
                "severity_score": score,
                "primary_issue": primary_issue,
                "active_failure_modes": row["active_failure_modes"],
                "overtake_success_rate": row["overtake_success_rate"],
                "elegant_overtake_rate": row["elegant_overtake_rate"],
                "on_track_overtake_rate": row["on_track_overtake_rate"],
                "target_grass_rate": row["target_grass_rate"],
                "overtake_start_to_complete_time": row["overtake_start_to_complete_time"],
                "paired_outcome_summary": "; ".join(outcomes.get(metric, f"{metric}:missing") for metric, _, _, _ in PAIR_METRICS),
                "reviewer_wording": reviewer_wording,
                "summary_file": row["summary_file"],
            }
        )
    rows.sort(key=lambda item: (-float(item["severity_score"]), item["case_id"]))
    return rows[:limit]


def make_figure(pair_summary, failure_summary, out_dir):
    register_cjk_font()
    mpl.rcParams.update({"svg.fonttype": "none", "pdf.fonttype": 42, "font.size": 8})
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.2), constrained_layout=True)
    fig.suptitle("逐 case 配对诊断：超车收益与失败归因", fontsize=11, fontweight="bold")

    ax = axes[0]
    metrics = ["overtake_success_rate", "elegant_overtake_rate", "on_track_overtake_rate", "overtake_start_to_complete_time", "target_grass_rate"]
    rows = [row for row in pair_summary if row["algorithm"] == PRIMARY and row["metric"] in metrics]
    rows = sorted(rows, key=lambda row: metrics.index(row["metric"]))
    labels = [row["metric_cn"] for row in rows]
    wins = np.asarray([int(row["wins"]) for row in rows], dtype=float)
    ties = np.asarray([int(row["ties"]) for row in rows], dtype=float)
    losses = np.asarray([int(row["losses"]) for row in rows], dtype=float)
    y = np.arange(len(rows))
    ax.barh(y, wins, color="#1976B9", label="胜")
    ax.barh(y, ties, left=wins, color="#B8B8B8", label="平")
    ax.barh(y, losses, left=wins + ties, color="#D45A48", label="负")
    ax.set_yticks(y, labels)
    ax.invert_yaxis()
    ax.set_xlabel("case 数")
    ax.set_title("v6-safe 相对原始 DLC 的逐 case 胜负")
    ax.legend(fontsize=7, ncols=3, loc="lower right")
    for idx, row in enumerate(rows):
        ax.text(max(wins[idx] + ties[idx] + losses[idx], 1) + 0.3, idx, f"{int(wins[idx])}/{int(ties[idx])}/{int(losses[idx])}", va="center", fontsize=6.5)

    ax = axes[1]
    failure_names = ["no_overtake", "off_track_overtake", "non_elegant_overtake", "high_grass_exposure", "long_overtake_window"]
    selected_algs = [PRIMARY, "dlc_world_original", "dlc_world_balanced", "rule_expert_gate"]
    summary_by_alg = {row["algorithm"]: row for row in failure_summary}
    x = np.arange(len(selected_algs))
    width = 0.15
    colors = ["#4C78A8", "#F58518", "#54A24B", "#B279A2", "#E45756"]
    for idx, name in enumerate(failure_names):
        rates = [as_float(summary_by_alg.get(alg, {}).get(f"{name}_rate")) or 0.0 for alg in selected_algs]
        ax.bar(x + (idx - 2) * width, rates, width=width, label=dict(FAILURE_RULES)[name], color=colors[idx])
    ax.set_xticks(x, [CN_LABEL_FALLBACK.get(alg, alg) for alg in selected_algs], rotation=18, ha="right")
    ax.set_ylim(0, 1.0)
    ax.set_ylabel("case 占比")
    ax.set_title("主要算法失败模式占比")
    ax.legend(fontsize=5.8, loc="upper right")

    paths = {}
    for suffix in ["svg", "pdf", "png", "tiff"]:
        path = out_dir / "figures" / f"figure_casewise_overtake_diagnostics_cn.{suffix}"
        path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, dpi=300 if suffix in {"png", "tiff"} else None)
        paths[suffix] = str(path)
    plt.close(fig)
    return paths


def build_markdown(report):
    summary = report["summary"]
    lines = [
        "# T-ITS Casewise Overtaking Diagnostic Pack",
        "",
        "该包把 240-run 确认性矩阵拆成同一 benchmark、车辆数、seed、赛道和 traffic profile 下的逐 case 配对比较，用于回答审稿中常见的两个问题：改进是否被少数 case 拉动，以及失败主要来自未超车、草地超车、不符合 desirable overtaking behavior 标准的超车还是耗时过长。",
        "",
        "## Summary",
        "",
    ]
    for key, value in summary.items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Primary Pairwise Diagnosis",
            "",
            "| Metric | Wins | Ties | Losses | Not applicable | Mean signed improvement |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for row in report["primary_pair_summary"]:
        lines.append(
            f"| {row['metric_cn']} | {row['wins']} | {row['ties']} | {row['losses']} | {row['not_applicable']} | {fmt(row['mean_signed_improvement'])} |"
        )
    lines.extend(
        [
            "",
            "## Failure Attribution",
            "",
            "| Algorithm | No failure | No overtake | Off-track overtake | Non-elegant | High grass | Long window |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in report["failure_summary"]:
        if row["algorithm"] not in {PRIMARY, "v6_runtime_dynamic_neighborhood", "quality_proposal_dlc_world_v1", BASELINE, "rule_expert_gate"}:
            continue
        lines.append(
            f"| {row['algorithm_label_cn']} | {fmt(row['no_failure_rate'])} | {fmt(row['no_overtake_rate'])} | {fmt(row['off_track_overtake_rate'])} | {fmt(row['non_elegant_overtake_rate'])} | {fmt(row['high_grass_exposure_rate'])} | {fmt(row['long_overtake_window_rate'])} |"
        )
    lines.extend(
        [
            "",
            "## Worst-Case Cards for Reviewer Discussion",
            "",
            "这些 case cards 只用于解释尾部失败和限制边界，不替代 240-run 统计主结果。",
            "",
            "| Rank | Case | Severity | Primary issue | Failures | Success | Desirable | On-track | Grass | Time | Reviewer wording |",
            "|---:|---|---:|---|---|---:|---:|---:|---:|---:|---|",
        ]
    )
    for idx, row in enumerate(report["worst_case_cards"], start=1):
        lines.append(
            f"| {idx} | `{row['case_id']}` | {fmt(row['severity_score'])} | {row['primary_issue']} | {row['active_failure_modes']} | "
            f"{fmt(row['overtake_success_rate'])} | {fmt(row['elegant_overtake_rate'])} | {fmt(row['on_track_overtake_rate'])} | "
            f"{fmt(row['target_grass_rate'])} | {fmt(row['overtake_start_to_complete_time'])} | {row['reviewer_wording']} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- 胜负表采用同 case 配对，不把不同赛道、seed 或车辆数混在一起比较。",
            "- 条件时间指标只在语义成立时比较：若一方未超车，记录为胜/负或 not applicable，而不是把缺失时间当成数值。",
            "- 失败归因是诊断标签，不是互斥类别；同一个 case 可以同时有“不符合 desirable overtaking behavior 标准”和“草地暴露过高”。",
            "- 该包补充均值、CI 和显著性检验，不能替代确认性统计主表。",
            "",
            "## Key Files",
            "",
            "- Pairwise rows: `outputs/tits_dynamic_graph/tits_casewise_diagnostic_pack/tables/casewise_pairwise_overtake_deltas.csv`",
            "- Pair summary: `outputs/tits_dynamic_graph/tits_casewise_diagnostic_pack/tables/casewise_pairwise_win_loss_summary.csv`",
            "- Failure rows: `outputs/tits_dynamic_graph/tits_casewise_diagnostic_pack/tables/casewise_failure_modes.csv`",
            "- Failure summary: `outputs/tits_dynamic_graph/tits_casewise_diagnostic_pack/tables/casewise_failure_mode_summary.csv`",
            "- Worst-case cards: `outputs/tits_dynamic_graph/tits_casewise_diagnostic_pack/tables/casewise_worst_case_cards.csv`",
            "- Chinese figure: `outputs/tits_dynamic_graph/tits_casewise_diagnostic_pack/figures/figure_casewise_overtake_diagnostics_cn.svg`",
            "",
            "## Regeneration Command",
            "",
            "```bash",
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_casewise_diagnostic_pack.py --out-dir outputs/tits_dynamic_graph/tits_casewise_diagnostic_pack",
            "```",
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Export casewise paired overtaking diagnostics for T-ITS evidence.")
    parser.add_argument("--source-csv", default=SOURCE_CSV)
    parser.add_argument("--baseline", default=BASELINE)
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/tits_casewise_diagnostic_pack")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    materials = out_dir / "materials"
    tables = out_dir / "tables"
    figures = out_dir / "figures"
    materials.mkdir(parents=True, exist_ok=True)
    tables.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)

    rows = read_csv(args.source_csv)
    pair_rows = build_pair_rows(rows, args.baseline)
    pair_summary = summarize_pairs(pair_rows)
    failure_rows = build_case_failure_rows(rows)
    failure_summary = summarize_failures(failure_rows)
    representative_rows = representative_case_rows(pair_rows)
    worst_case_cards = build_worst_case_cards(failure_rows, pair_rows)
    primary_pair_summary = [
        row
        for row in pair_summary
        if row["algorithm"] == PRIMARY
        and row["metric"] in {"overtake_success_rate", "elegant_overtake_rate", "on_track_overtake_rate", "overtake_start_to_complete_time", "target_grass_rate"}
    ]
    figure_paths = make_figure(pair_summary, failure_summary, out_dir)
    summary = {
        "status": "pass",
        "source_csv": args.source_csv,
        "source_rows": len(rows),
        "case_count": len({case_key(row) for row in rows}),
        "algorithm_count": len({row["algorithm"] for row in rows}),
        "pairwise_rows": len(pair_rows),
        "failure_rows": len(failure_rows),
        "primary_algorithm": PRIMARY,
        "baseline": args.baseline,
        "primary_success_wins_vs_dlc": next((row["wins"] for row in primary_pair_summary if row["metric"] == "overtake_success_rate"), None),
        "primary_elegant_wins_vs_dlc": next((row["wins"] for row in primary_pair_summary if row["metric"] == "elegant_overtake_rate"), None),
        "primary_grass_wins_vs_dlc": next((row["wins"] for row in primary_pair_summary if row["metric"] == "target_grass_rate"), None),
        "worst_case_card_count": len(worst_case_cards),
    }
    report = {
        "status": "pass",
        "summary": summary,
        "primary_pair_summary": primary_pair_summary,
        "failure_summary": failure_summary,
        "worst_case_cards": worst_case_cards,
        "figure_paths": figure_paths,
        "note": "Casewise diagnostics support interpretation and rebuttal. Confirmatory claims should still cite the frozen source data, paired statistics, and predefined primary hypotheses.",
    }
    fields_pair = [
        "case_id",
        "benchmark",
        "num_agents",
        "seed",
        "track_path",
        "traffic_profile",
        "algorithm",
        "algorithm_label_cn",
        "baseline",
        "baseline_label_cn",
        "metric",
        "metric_cn",
        "higher_is_better",
        "metric_type",
        "candidate_value",
        "baseline_value",
        "raw_delta_candidate_minus_baseline",
        "improvement_signed",
        "outcome",
        "note",
        "candidate_summary_file",
        "baseline_summary_file",
    ]
    fields_pair_summary = [
        "algorithm",
        "algorithm_label_cn",
        "baseline",
        "metric",
        "metric_cn",
        "n_cases",
        "n_valid",
        "wins",
        "losses",
        "ties",
        "not_applicable",
        "missing",
        "win_rate_valid",
        "loss_rate_valid",
        "mean_signed_improvement",
    ]
    fields_failure = [
        "case_id",
        "benchmark",
        "num_agents",
        "seed",
        "track_path",
        "traffic_profile",
        "algorithm",
        "algorithm_label_cn",
        "active_failure_modes",
        *[name for name, _ in FAILURE_RULES],
        "overtake_success_rate",
        "elegant_overtake_rate",
        "on_track_overtake_rate",
        "target_grass_rate",
        "overtake_start_to_complete_time",
        "compute_latency_ms",
        "summary_file",
    ]
    fields_failure_summary = [
        "algorithm",
        "algorithm_label_cn",
        "n_cases",
        "no_failure_count",
        "no_failure_rate",
        *[item for name, _ in FAILURE_RULES for item in (f"{name}_count", f"{name}_rate")],
    ]
    fields_representative = [
        "case_id",
        "benchmark",
        "num_agents",
        "seed",
        "track_path",
        "traffic_profile",
        "primary_vs_dlc_wins",
        "primary_vs_dlc_losses",
        "primary_vs_dlc_ties",
        "case_profile",
    ]
    fields_worst_case = [
        "case_id",
        "benchmark",
        "num_agents",
        "seed",
        "track_path",
        "traffic_profile",
        "severity_score",
        "primary_issue",
        "active_failure_modes",
        "overtake_success_rate",
        "elegant_overtake_rate",
        "on_track_overtake_rate",
        "target_grass_rate",
        "overtake_start_to_complete_time",
        "paired_outcome_summary",
        "reviewer_wording",
        "summary_file",
    ]
    paths = {
        "report_md": write_text(materials / "CASEWISE_OVERTAKING_DIAGNOSTIC_REPORT.md", build_markdown(report)),
        "report_json": write_json(materials / "CASEWISE_OVERTAKING_DIAGNOSTIC_REPORT.json", report),
        "pairwise_rows_csv": write_csv(tables / "casewise_pairwise_overtake_deltas.csv", pair_rows, fields_pair),
        "pairwise_summary_csv": write_csv(tables / "casewise_pairwise_win_loss_summary.csv", pair_summary, fields_pair_summary),
        "failure_rows_csv": write_csv(tables / "casewise_failure_modes.csv", failure_rows, fields_failure),
        "failure_summary_csv": write_csv(tables / "casewise_failure_mode_summary.csv", failure_summary, fields_failure_summary),
        "representative_cases_csv": write_csv(tables / "casewise_primary_vs_dlc_case_profiles.csv", representative_rows, fields_representative),
        "worst_case_cards_csv": write_csv(tables / "casewise_worst_case_cards.csv", worst_case_cards, fields_worst_case),
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
    manifest_path = write_json(out_dir / "tits_casewise_diagnostic_pack_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, "status": "pass", "summary": summary}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
