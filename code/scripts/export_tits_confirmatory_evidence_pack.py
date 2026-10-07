#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import json
import math
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np


BASELINE = "dlc_world_original"
PRIMARY_ALGORITHMS = [
    "v6_runtime_dynamic_neighborhood_safe",
    "v6_runtime_dynamic_neighborhood",
    "quality_proposal_dlc_world_v1",
    "dlc_world_original",
    "dlc_world_balanced",
    "dlc_world_safety",
    "dlc_world_fast",
    "rule_expert_gate",
]
METRICS = [
    ("overtake_success_rate", "超车成功率", True, "rate"),
    ("elegant_overtake_rate", "Desirable overtaking behavior rate", True, "rate"),
    ("on_track_overtake_rate", "赛道内超车率", True, "rate"),
    ("rank_gain", "名次提升", True, "continuous"),
    ("overtake_start_to_complete_time", "开始超车到完成耗时", False, "conditional_time"),
    ("time_to_first_overtake", "首次超车时间", False, "conditional_time"),
    ("target_grass_rate", "目标车草地率", False, "rate"),
    ("grass_recovery_time_mean", "草地后恢复时间", False, "conditional_time"),
    ("target_mean_abs_lateral", "横向偏差", False, "continuous"),
    ("compute_latency_ms", "决策延迟", False, "continuous"),
]
CLAIM_ROWS = [
    {
        "claim_id": "C1",
        "claim": "运行时动态邻域图支持不同车辆数在线构图，不需要针对 8 车重新训练。",
        "primary_evidence": "vehicle_count_extrapolation/n8 中 v6-safe 与 v6-full 相对 DLC 原始模型的Desirable overtaking behavior rate、首次超车时间、开始到完成耗时。",
        "boundary": "当前证据覆盖 4/5/6 车训练分布与 8 车外推；尚不能声称任意密度交通无限泛化。",
    },
    {
        "claim_id": "C2",
        "claim": "优化后的 DLC world model 在 Monza 外部赛道上明显优于原始 DLC world model。",
        "primary_evidence": "monza_external_track/n4,n6 中原始 DLC 成功率为 0，而 v6-safe、v6-full、quality-proposal 保持成功超车。",
        "boundary": "Monza 是单一外部 CSV 赛道；仍需更多真实赛道或闭源仿真器验证外部有效性。",
    },
    {
        "claim_id": "C3",
        "claim": "相比 DLC world model，当前方法提升的不只是速度，还包括on-track/desirable超车质量。",
        "primary_evidence": "完整 240-run 矩阵中的Desirable overtaking behavior rate、赛道内超车率、超车窗口草地率与失败模式统计。",
        "boundary": "小车队 n4 程序赛道仍存在desirable overtaking behavior quality不足，不能把结论写成所有场景均优。",
    },
    {
        "claim_id": "C4",
        "claim": "规则专家是强基线但不是主算法替代品。",
        "primary_evidence": "规则专家延迟低，部分场景Desirable overtaking behavior rate高，但 Monza n6 草地率高，且缺乏世界模型泛化机制。",
        "boundary": "规则专家应作为强手工基线和上界参照，而不是学习型 world model 的直接消融。",
    },
    {
        "claim_id": "C5",
        "claim": "当前系统已具备可复现的顶刊实验材料基础。",
        "primary_evidence": "冻结 case command、240/240 审计、source data、bootstrap 统计表、publication GIF、artifact manifest 和 SHA256。",
        "boundary": "最终投稿仍需作者确认 license、匿名化、数据仓库 DOI 和最终 manuscript 文本一致性。",
    },
]


def read_csv_rows(path):
    with Path(path).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def as_float(value):
    if value in (None, ""):
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(out) or math.isinf(out):
        return None
    return out


def as_int(value):
    out = as_float(value)
    return None if out is None else int(out)


def fmt(value, digits=3):
    if value is None:
        return "--"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def register_cjk_font():
    import matplotlib as mpl
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


def bootstrap_ci(values, rng, n_boot=5000):
    values = np.asarray([v for v in values if v is not None and np.isfinite(v)], dtype=np.float64)
    if values.size == 0:
        return None, None, None, 0
    mean = float(values.mean())
    if values.size == 1:
        return mean, mean, mean, 1
    idx = rng.integers(0, values.size, size=(n_boot, values.size))
    boot = values[idx].mean(axis=1)
    lo, hi = np.quantile(boot, [0.025, 0.975])
    return mean, float(lo), float(hi), int(values.size)


def paired_bootstrap_ci(deltas, rng, n_boot=5000):
    return bootstrap_ci(deltas, rng, n_boot=n_boot)


def exact_sign_pvalue(improvements):
    values = [v for v in improvements if v is not None and v != 0]
    n = len(values)
    if n == 0:
        return None
    positives = sum(v > 0 for v in values)
    k = min(positives, n - positives)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / (2**n)
    return min(1.0, 2.0 * tail)


def exact_mcnemar_pvalue(a_success, b_success):
    b = sum((a == 1 and b == 0) for a, b in zip(a_success, b_success))
    c = sum((a == 0 and b == 1) for a, b in zip(a_success, b_success))
    n = b + c
    if n == 0:
        return None
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / (2**n)
    return min(1.0, 2.0 * tail)


def case_key(row):
    return (row["_benchmark"], as_int(row["num_agents"]), as_int(row["seed"]))


def algorithm_label(rows, algorithm):
    for row in rows:
        if row["algorithm"] == algorithm:
            return row.get("algorithm_label_cn") or algorithm
    return algorithm


def group_by_algorithm(rows):
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["algorithm"]].append(row)
    return grouped


def summarize_overall(rows, n_boot, seed):
    rng = np.random.default_rng(seed)
    grouped = group_by_algorithm(rows)
    out = []
    for algorithm in sorted(grouped, key=lambda x: PRIMARY_ALGORITHMS.index(x) if x in PRIMARY_ALGORITHMS else 999):
        values = grouped[algorithm]
        item = {
            "algorithm": algorithm,
            "algorithm_label_cn": algorithm_label(rows, algorithm),
            "n": len(values),
        }
        for metric, _, _, _ in METRICS:
            mean, lo, hi, n = bootstrap_ci([as_float(row.get(metric)) for row in values], rng, n_boot)
            item[f"{metric}_n"] = n
            item[f"{metric}_mean"] = mean
            item[f"{metric}_ci95_low"] = lo
            item[f"{metric}_ci95_high"] = hi
        out.append(item)
    return out


def build_case_index(rows):
    indexed = defaultdict(dict)
    for row in rows:
        indexed[case_key(row)][row["algorithm"]] = row
    return indexed


def paired_tests(rows, n_boot, seed):
    rng = np.random.default_rng(seed + 19)
    indexed = build_case_index(rows)
    out = []
    algorithms = [item for item in PRIMARY_ALGORITHMS if item != BASELINE]
    for metric, metric_cn, higher_is_better, metric_type in METRICS:
        for algorithm in algorithms:
            raw_deltas = []
            improvements = []
            a_success = []
            b_success = []
            examples = []
            for key, values in indexed.items():
                if BASELINE not in values or algorithm not in values:
                    continue
                a = as_float(values[algorithm].get(metric))
                b = as_float(values[BASELINE].get(metric))
                if a is None or b is None:
                    continue
                raw_delta = a - b
                improvement = raw_delta if higher_is_better else -raw_delta
                raw_deltas.append(raw_delta)
                improvements.append(improvement)
                if metric_type == "rate":
                    a_success.append(1 if a > 0 else 0)
                    b_success.append(1 if b > 0 else 0)
                if len(examples) < 3:
                    examples.append(f"{key[0]}/n{key[1]}/seed{key[2]}:{raw_delta:.3f}")
            delta_mean, delta_lo, delta_hi, n = paired_bootstrap_ci(raw_deltas, rng, n_boot)
            imp_mean, imp_lo, imp_hi, _ = paired_bootstrap_ci(improvements, rng, n_boot)
            out.append(
                {
                    "algorithm": algorithm,
                    "algorithm_label_cn": algorithm_label(rows, algorithm),
                    "baseline": BASELINE,
                    "baseline_label_cn": algorithm_label(rows, BASELINE),
                    "metric": metric,
                    "metric_cn": metric_cn,
                    "higher_is_better": higher_is_better,
                    "n_paired": n,
                    "raw_delta_algorithm_minus_dlc_mean": delta_mean,
                    "raw_delta_ci95_low": delta_lo,
                    "raw_delta_ci95_high": delta_hi,
                    "improvement_vs_dlc_mean": imp_mean,
                    "improvement_ci95_low": imp_lo,
                    "improvement_ci95_high": imp_hi,
                    "paired_sign_test_p": exact_sign_pvalue(improvements),
                    "mcnemar_presence_p": exact_mcnemar_pvalue(a_success, b_success) if metric_type == "rate" else None,
                    "example_case_deltas": "; ".join(examples),
                }
            )
    return out


def scenario_rows(rows, n_boot, seed):
    rng = np.random.default_rng(seed + 41)
    groups = defaultdict(list)
    for row in rows:
        groups[(row["_benchmark"], as_int(row["num_agents"]), row["algorithm"])].append(row)
    out = []
    for (benchmark, n_agents, algorithm), values in sorted(groups.items()):
        item = {
            "benchmark": benchmark,
            "num_agents": n_agents,
            "algorithm": algorithm,
            "algorithm_label_cn": algorithm_label(rows, algorithm),
            "n": len(values),
        }
        for metric in [
            "overtake_success_rate",
            "elegant_overtake_rate",
            "on_track_overtake_rate",
            "rank_gain",
            "overtake_start_to_complete_time",
            "time_to_first_overtake",
            "target_grass_rate",
            "compute_latency_ms",
        ]:
            mean, lo, hi, metric_n = bootstrap_ci([as_float(row.get(metric)) for row in values], rng, n_boot)
            item[f"{metric}_mean"] = mean
            item[f"{metric}_ci95_low"] = lo
            item[f"{metric}_ci95_high"] = hi
            item[f"{metric}_n"] = metric_n
        out.append(item)
    return out


def classify_failures(row):
    success = as_float(row.get("overtake_success_rate")) or 0.0
    elegant = as_float(row.get("elegant_overtake_rate")) or 0.0
    ontrack = as_float(row.get("on_track_overtake_rate")) or 0.0
    grass = as_float(row.get("target_grass_rate")) or 0.0
    duration = as_float(row.get("overtake_start_to_complete_time"))
    latency = as_float(row.get("compute_latency_ms")) or 0.0
    tags = []
    if success <= 0:
        tags.append("no_overtake")
    if success > 0 and ontrack <= 0:
        tags.append("success_but_no_on_track_overtake")
    if success > 0 and elegant <= 0:
        tags.append("success_but_no_elegant_overtake")
    if success > 0 and 0 < elegant < 0.3:
        tags.append("low_elegance_rate")
    if grass > 0.6:
        tags.append("high_grass_rate_gt_0.60")
    if grass > 0.8:
        tags.append("severe_grass_rate_gt_0.80")
    if success > 0 and duration is not None and duration > 300:
        tags.append("slow_overtake_gt_300_steps")
    if latency > 150:
        tags.append("high_latency_gt_150ms")
    if not tags:
        tags.append("pass_or_minor_issue")
    return tags


def failure_atlas(rows):
    counters = defaultdict(Counter)
    examples = defaultdict(list)
    for row in rows:
        alg = row["algorithm"]
        for tag in classify_failures(row):
            counters[alg][tag] += 1
            key = (alg, tag)
            if len(examples[key]) < 5:
                examples[key].append(f"{row['_benchmark']}/n{row['num_agents']}/seed{row['seed']}")
    out = []
    for algorithm, counter in sorted(counters.items(), key=lambda kv: PRIMARY_ALGORITHMS.index(kv[0]) if kv[0] in PRIMARY_ALGORITHMS else 999):
        total = sum(counter.values())
        case_total = len([r for r in rows if r["algorithm"] == algorithm])
        for tag, count in counter.most_common():
            out.append(
                {
                    "algorithm": algorithm,
                    "algorithm_label_cn": algorithm_label(rows, algorithm),
                    "failure_or_quality_tag": tag,
                    "tag_count": count,
                    "case_count": case_total,
                    "tag_rate_per_case": count / case_total if case_total else None,
                    "tag_rate_among_tags": count / total if total else None,
                    "example_cases": "; ".join(examples[(algorithm, tag)]),
                }
            )
    return out


def read_optional_csv(path):
    path = Path(path)
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def gpu_snapshot():
    try:
        out = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total",
                "--format=csv,noheader",
            ],
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=10,
        )
    except Exception:
        return []
    rows = []
    for line in out.splitlines():
        if not line.strip():
            continue
        parts = [part.strip() for part in line.split(",")]
        rows.append({"name": parts[0], "memory_total": parts[1] if len(parts) > 1 else ""})
    return rows


def compute_cost(rows, case_commands_path, ledger_path):
    commands = read_optional_csv(case_commands_path)
    ledger = read_optional_csv(ledger_path)
    devices = Counter(row.get("device", "") for row in commands if row.get("device"))
    elapsed = [as_float(row.get("elapsed_sec")) for row in ledger]
    elapsed = [item for item in elapsed if item is not None]
    finish_steps = [as_float(row.get("finish_step")) for row in rows]
    finish_steps = [item for item in finish_steps if item is not None]
    unique_cases = sorted({case_key(row) for row in rows})
    out = {
        "source_algorithm_runs": len(rows),
        "unique_cases": len(unique_cases),
        "algorithms_per_case": len({row["algorithm"] for row in rows}),
        "case_command_count": len(commands),
        "case_command_devices": dict(devices),
        "recorded_ledger_cases": len(ledger),
        "recorded_elapsed_sec_sum": sum(elapsed) if elapsed else None,
        "recorded_elapsed_sec_mean": float(np.mean(elapsed)) if elapsed else None,
        "recorded_elapsed_sec_min": min(elapsed) if elapsed else None,
        "recorded_elapsed_sec_max": max(elapsed) if elapsed else None,
        "finish_step_sum_over_algorithm_runs": sum(finish_steps) if finish_steps else None,
        "finish_step_mean": float(np.mean(finish_steps)) if finish_steps else None,
        "finish_step_max": max(finish_steps) if finish_steps else None,
        "gpu_snapshot": gpu_snapshot(),
        "wall_clock_limitation": (
            "当前 ledger 从修复后的 case 开始记录，不是完整历史 wall-clock 台账；"
            "完整实验规模应以 source_algorithm_runs 和 finish_step_sum 为准。"
        ),
    }
    return out


def write_csv(path, rows, fields=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return str(path)


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


def plot_evidence(rows, out_dir):
    import matplotlib as mpl
    import matplotlib.pyplot as plt

    register_cjk_font()
    mpl.rcParams.update(
        {
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "font.size": 8,
            "axes.spines.right": False,
            "axes.spines.top": False,
            "axes.unicode_minus": False,
            "legend.frameon": False,
        }
    )
    labels = {alg: algorithm_label(rows, alg) for alg in PRIMARY_ALGORITHMS}
    algorithms = [alg for alg in PRIMARY_ALGORITHMS if any(row["algorithm"] == alg for row in rows)]
    metrics = [
        ("elegant_overtake_rate", "Desirable overtaking behavior rate", True),
        ("on_track_overtake_rate", "赛道内超车率", True),
        ("overtake_start_to_complete_time", "超车耗时", False),
        ("target_grass_rate", "目标草地率", False),
    ]
    scenarios = [
        ("overall", "全部场景"),
        ("vehicle_count_extrapolation", "8车外推"),
        ("monza_external_track", "Monza外部赛道"),
    ]
    colors = {
        "v6_runtime_dynamic_neighborhood_safe": "#2F6BBD",
        "v6_runtime_dynamic_neighborhood": "#55A868",
        "quality_proposal_dlc_world_v1": "#8172B2",
        "dlc_world_original": "#C44E52",
        "dlc_world_balanced": "#8C564B",
        "dlc_world_safety": "#CCB974",
        "dlc_world_fast": "#64B5CD",
        "rule_expert_gate": "#4C566A",
    }
    rng = np.random.default_rng(2026)
    fig, axes = plt.subplots(len(metrics), len(scenarios), figsize=(12.8, 9.2), constrained_layout=True)
    for i, (metric, metric_cn, higher) in enumerate(metrics):
        for j, (scenario, scenario_cn) in enumerate(scenarios):
            ax = axes[i][j]
            sub = rows if scenario == "overall" else [row for row in rows if row["_benchmark"] == scenario]
            means, lows, highs = [], [], []
            for alg in algorithms:
                values = [as_float(row.get(metric)) for row in sub if row["algorithm"] == alg]
                mean, lo, hi, _ = bootstrap_ci(values, rng, 2000)
                means.append(np.nan if mean is None else mean)
                lows.append(0.0 if mean is None or lo is None else max(mean - lo, 0.0))
                highs.append(0.0 if mean is None or hi is None else max(hi - mean, 0.0))
            x = np.arange(len(algorithms))
            bar_colors = [colors.get(alg, "#999999") for alg in algorithms]
            ax.bar(x, np.nan_to_num(means, nan=0.0), color=bar_colors, width=0.72)
            ax.errorbar(x, np.nan_to_num(means, nan=0.0), yerr=np.asarray([lows, highs]), fmt="none", ecolor="#1F2933", capsize=2, lw=0.8)
            if i == 0:
                ax.set_title(scenario_cn)
            if j == 0:
                ax.set_ylabel(metric_cn)
            ax.grid(axis="y", color="#D8DEE9", lw=0.6)
            ax.set_xticks(x)
            ax.set_xticklabels([labels[alg] for alg in algorithms], rotation=35, ha="right")
            if metric.endswith("_rate"):
                ax.set_ylim(0, 1.05)
            if not higher:
                ax.text(0.02, 0.92, "越低越好", transform=ax.transAxes, fontsize=7, color="#555555")
    fig.suptitle("确认性在线矩阵：超车质量、效率与草地风险", fontsize=13, fontweight="bold")
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = out_dir / "figure_confirmatory_overtake_evidence_cn"
    outputs = {}
    for ext in ["png", "svg", "pdf", "tiff"]:
        path = stem.with_suffix(f".{ext}")
        fig.savefig(path, dpi=600, bbox_inches="tight")
        outputs[ext] = str(path)
    plt.close(fig)
    return outputs


def write_failure_markdown(path, atlas_rows):
    lines = [
        "# 确认性矩阵失败模式图谱",
        "",
        "该图谱按算法统计在线运行中最常见的质量问题，用于论文 Discussion、Limitations 和审稿回复。",
        "",
        "| 算法 | 失败/质量标签 | 次数 | case数 | 每case比例 | 示例case |",
        "|---|---|---:|---:|---:|---|",
    ]
    for row in atlas_rows:
        lines.append(
            f"| {row['algorithm_label_cn']} | {row['failure_or_quality_tag']} | {row['tag_count']} | "
            f"{row['case_count']} | {fmt(row['tag_rate_per_case'])} | {row['example_cases']} |"
        )
    lines.extend(
        [
            "",
            "解释边界：一个 case 可以同时触发多个标签，因此标签次数之和不等于 case 数。"
        ]
    )
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(path)


def write_compute_markdown(path, compute):
    gpu_lines = [f"- {item['name']} ({item['memory_total']})" for item in compute["gpu_snapshot"]] or ["- unavailable"]
    lines = [
        "# 算力与复现成本报告",
        "",
        f"- 完整算法运行数：{compute['source_algorithm_runs']}",
        f"- 唯一 case 数：{compute['unique_cases']}",
        f"- 每 case 算法数：{compute['algorithms_per_case']}",
        f"- 冻结 case command 数：{compute['case_command_count']}",
        f"- 完整仿真步数合计（按 algorithm-run）：{fmt(compute['finish_step_sum_over_algorithm_runs'], 0)}",
        f"- 平均 finish step：{fmt(compute['finish_step_mean'], 1)}",
        f"- 最大 finish step：{fmt(compute['finish_step_max'], 0)}",
        f"- 已记录 ledger case 数：{compute['recorded_ledger_cases']}",
        f"- 已记录 wall-clock 合计秒数：{fmt(compute['recorded_elapsed_sec_sum'], 1)}",
        f"- 已记录单 case 平均秒数：{fmt(compute['recorded_elapsed_sec_mean'], 1)}",
        "",
        "## GPU 快照",
        "",
        *gpu_lines,
        "",
        "## 解释边界",
        "",
        compute["wall_clock_limitation"],
        "",
        "在线 rollout 的主要瓶颈来自 Box2D/Gym 环境步进和多车仿真，GPU 主要用于策略/世界模型推理。因此 GPU 利用率低不能简单解释为未使用 GPU。",
    ]
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(path)


def write_main_report(path, overall, paired, scenario, figures, manifest_refs):
    by_alg = {row["algorithm"]: row for row in overall}
    safe = by_alg.get("v6_runtime_dynamic_neighborhood_safe", {})
    dlc = by_alg.get(BASELINE, {})
    quality = by_alg.get("quality_proposal_dlc_world_v1", {})
    lines = [
        "# T-ITS 确认性证据包报告",
        "",
        "## 数据基础",
        "",
        "- 在线确认性矩阵：240 条 algorithm-run，30 个 case，8 个算法。",
        "- 评测覆盖：程序生成赛道 n=4/5/6、车辆数量外推 n=8、Monza 外部 CSV 转换赛道 n=4/6。",
        "- 目标车均从最后身位起步，核心指标围绕超车成功、Desirable overtaking behavior、赛道内超车、开始到完成耗时、草地率和延迟。",
        "",
        "## 主要总体结论",
        "",
        f"- v6-safe 超车成功率 {fmt(safe.get('overtake_success_rate_mean'))}，DLC 原始模型 {fmt(dlc.get('overtake_success_rate_mean'))}。",
        f"- v6-safe Desirable overtaking behavior rate {fmt(safe.get('elegant_overtake_rate_mean'))}，DLC 原始模型 {fmt(dlc.get('elegant_overtake_rate_mean'))}。",
        f"- v6-safe 开始到完成耗时 {fmt(safe.get('overtake_start_to_complete_time_mean'), 1)} step，DLC 原始模型 {fmt(dlc.get('overtake_start_to_complete_time_mean'), 1)} step。",
        f"- 质量 Proposal 分支超车成功率 {fmt(quality.get('overtake_success_rate_mean'))}，适合作为质量导向消融/补充分支，而非替代 v6-safe 主结论。",
        "",
        "## 关键成对检验摘要",
        "",
        "| 算法 | 指标 | n | 改进均值 | 95% CI | sign p | McNemar p |",
        "|---|---|---:|---:|---|---:|---:|",
    ]
    focus = {
        "v6_runtime_dynamic_neighborhood_safe",
        "v6_runtime_dynamic_neighborhood",
        "quality_proposal_dlc_world_v1",
    }
    focus_metrics = {"overtake_success_rate", "elegant_overtake_rate", "on_track_overtake_rate", "overtake_start_to_complete_time", "target_grass_rate"}
    for row in paired:
        if row["algorithm"] not in focus or row["metric"] not in focus_metrics:
            continue
        lines.append(
            f"| {row['algorithm_label_cn']} | {row['metric_cn']} | {row['n_paired']} | "
            f"{fmt(row['improvement_vs_dlc_mean'])} | [{fmt(row['improvement_ci95_low'])}, {fmt(row['improvement_ci95_high'])}] | "
            f"{fmt(row['paired_sign_test_p'])} | {fmt(row['mcnemar_presence_p'])} |"
        )
    lines.extend(
        [
            "",
            "## 论文写作建议",
            "",
            "- 主算法建议写成“优化后的 DLC world model with runtime dynamic neighborhood and overtake-aware risk planning”，避免只称为普通规则规划器。",
            "- 主 claim 应聚焦 n6/n8 多车与 Monza 外部赛道上的Desirable overtaking behavior和超车耗时优势；n4 程序赛道的desirable overtaking behavior quality不足应作为局限主动披露。",
            "- 规则专家应作为强手工基线保留，用来证明不是简单速度规则即可稳定解决；它的高草地率可支撑学习型 world model 的必要性。",
            "- 图中建议同时展示成功率与Desirable overtaking behavior rate，因为单看成功率会掩盖草地绕行和非赛道内超车问题。",
            "",
            "## 输出文件索引",
            "",
        ]
    )
    for key, value in manifest_refs.items():
        lines.append(f"- {key}: `{value}`")
    for ext, value in figures.items():
        lines.append(f"- figure_{ext}: `{value}`")
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(path)


def main():
    parser = argparse.ArgumentParser(description="Export T-ITS confirmatory evidence pack from the final online matrix.")
    parser.add_argument("--source-csv", default="outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv")
    parser.add_argument("--case-commands", default="outputs/tits_dynamic_graph/v6_confirmatory_preflight/tables/v6_confirmatory_case_commands.csv")
    parser.add_argument("--ledger", default="outputs/tits_dynamic_graph/v6_confirmatory_matrix_run_results_ledger.csv")
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack")
    parser.add_argument("--bootstrap", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=20260624)
    args = parser.parse_args()

    rows = read_csv_rows(args.source_csv)
    out_dir = Path(args.out_dir)
    tables_dir = out_dir / "tables"
    materials_dir = out_dir / "materials"
    figures_dir = out_dir / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    materials_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    overall = summarize_overall(rows, args.bootstrap, args.seed)
    paired = paired_tests(rows, args.bootstrap, args.seed)
    scenario = scenario_rows(rows, args.bootstrap, args.seed)
    atlas = failure_atlas(rows)
    compute = compute_cost(rows, args.case_commands, args.ledger)
    figures = plot_evidence(rows, figures_dir)

    paths = {
        "overall_statistics_csv": write_csv(tables_dir / "confirmatory_overall_statistics.csv", overall),
        "paired_tests_csv": write_csv(tables_dir / "confirmatory_paired_tests_vs_dlc.csv", paired),
        "scenario_statistics_csv": write_csv(tables_dir / "confirmatory_scenario_statistics.csv", scenario),
        "failure_atlas_csv": write_csv(tables_dir / "confirmatory_failure_atlas.csv", atlas),
        "claim_evidence_matrix_csv": write_csv(tables_dir / "confirmatory_claim_evidence_matrix.csv", CLAIM_ROWS),
        "compute_cost_json": write_json(tables_dir / "confirmatory_compute_cost.json", compute),
    }
    paths["failure_atlas_md"] = write_failure_markdown(materials_dir / "FAILURE_ATLAS.md", atlas)
    paths["compute_report_md"] = write_compute_markdown(materials_dir / "COMPUTE_AND_REPRODUCIBILITY_REPORT.md", compute)
    main_report_path = str(materials_dir / "CONFIRMATORY_EVIDENCE_REPORT.md")
    paths["main_report_md"] = main_report_path
    paths["main_report_md"] = write_main_report(
        main_report_path,
        overall,
        paired,
        scenario,
        figures,
        paths,
    )
    manifest = {
        "status": "complete",
        "source_csv": args.source_csv,
        "out_dir": str(out_dir),
        "bootstrap": args.bootstrap,
        "seed": args.seed,
        "run_count": len(rows),
        "case_count": len({case_key(row) for row in rows}),
        "algorithm_count": len({row["algorithm"] for row in rows}),
        "paths": paths,
        "figures": figures,
        "notes": [
            "All statistics are derived from the frozen confirmatory source CSV.",
            "Conditional time metrics exclude runs without a completed overtake event.",
            "Failure atlas tags are non-exclusive and should be interpreted as quality diagnostics.",
        ],
    }
    manifest_path = write_json(out_dir / "confirmatory_evidence_pack_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, "run_count": len(rows), "case_count": manifest["case_count"], "algorithm_count": manifest["algorithm_count"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
