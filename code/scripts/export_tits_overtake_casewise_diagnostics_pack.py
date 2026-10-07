#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib import font_manager


SOURCE_CSV = "outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv"
PRIMARY = "v6_runtime_dynamic_neighborhood_safe"
BASELINE = "dlc_world_original"
ALGORITHM_ORDER = [
    "v6_runtime_dynamic_neighborhood_safe",
    "v6_runtime_dynamic_neighborhood",
    "quality_proposal_dlc_world_v1",
    "rule_expert_gate",
    "dlc_world_original",
    "dlc_world_balanced",
    "dlc_world_safety",
    "dlc_world_fast",
]
ALGORITHM_SHORT = {
    "v6_runtime_dynamic_neighborhood_safe": "本文方法-safe",
    "v6_runtime_dynamic_neighborhood": "本文方法",
    "quality_proposal_dlc_world_v1": "DLC-quality",
    "rule_expert_gate": "规则专家",
    "dlc_world_original": "DLC原始",
    "dlc_world_balanced": "DLC-balanced",
    "dlc_world_safety": "DLC-safety",
    "dlc_world_fast": "DLC-fast",
}


def configure_chinese_matplotlib():
    font_candidates = [
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.otf"),
        Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"),
        Path("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"),
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
            "font.size": 7.5,
            "axes.unicode_minus": False,
            "axes.spines.right": False,
            "axes.spines.top": False,
            "legend.frameon": False,
        }
    )
    return font_name


def read_csv(path):
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


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


def as_int(value):
    value = as_float(value)
    return None if value is None else int(round(value))


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
    vals = [as_float(v) for v in values]
    vals = [v for v in vals if v is not None]
    return statistics.median(vals) if vals else None


def ratio(numer, denom):
    return float(numer) / float(denom) if denom else None


def case_id(row):
    return f"{row['_benchmark']}|n{row['num_agents']}|seed{row['seed']}"


def run_id(row):
    return f"{case_id(row)}|{row['algorithm']}"


def event_quality(event):
    if bool(event.get("elegant_overtake")):
        return "elegant"
    if bool(event.get("on_track_overtake")):
        return "on_track_non_elegant"
    return "off_track"


def run_outcome(events):
    if not events:
        return "no_overtake"
    if any(bool(event.get("elegant_overtake")) for event in events):
        return "elegant_overtake"
    if any(bool(event.get("on_track_overtake")) for event in events):
        return "on_track_non_elegant"
    return "off_track_overtake"


def first_completed_event(events):
    completed = [event for event in events if as_int(event.get("complete_step")) is not None]
    if not completed:
        return None
    return min(completed, key=lambda event: as_int(event.get("complete_step")))


def load_runs(root, source_rows):
    run_rows = []
    event_rows = []
    for row in source_rows:
        summary_path = root / row.get("_summary_file", "")
        summary = read_json(summary_path) if summary_path.exists() else {}
        events = summary.get("overtake_events", [])
        if not isinstance(events, list):
            events = []
        first = first_completed_event(events)
        qualities = Counter(event_quality(event) for event in events)
        outcome = run_outcome(events)
        rid = run_id(row)
        cid = case_id(row)
        first_start = as_int(first.get("start_step")) if first else None
        first_complete = as_int(first.get("complete_step")) if first else None
        first_duration = as_int(first.get("duration_steps")) if first else None
        event_grass_values = [as_float(event.get("window_grass_rate")) for event in events]
        event_lateral_values = [as_float(event.get("window_max_abs_lateral")) for event in events]
        run_rows.append(
            {
                "run_id": rid,
                "case_id": cid,
                "benchmark": row["_benchmark"],
                "algorithm": row["algorithm"],
                "algorithm_label_cn": row.get("algorithm_label_cn", ""),
                "num_agents": row["num_agents"],
                "seed": row["seed"],
                "track_path": row.get("track_path", ""),
                "traffic_profile": row.get("traffic_profile", ""),
                "outcome_class": outcome,
                "event_count": len(events),
                "elegant_event_count": qualities["elegant"],
                "on_track_non_elegant_event_count": qualities["on_track_non_elegant"],
                "off_track_event_count": qualities["off_track"],
                "first_start_step": "" if first_start is None else first_start,
                "first_complete_step": "" if first_complete is None else first_complete,
                "first_duration_steps": "" if first_duration is None else first_duration,
                "first_window_grass_rate": "" if not first else first.get("window_grass_rate", ""),
                "first_window_max_abs_lateral": "" if not first else first.get("window_max_abs_lateral", ""),
                "window_grass_rate_mean": "" if mean(event_grass_values) is None else mean(event_grass_values),
                "window_max_abs_lateral_mean": "" if mean(event_lateral_values) is None else mean(event_lateral_values),
                "target_grass_rate": row.get("target_grass_rate", ""),
                "target_mean_abs_lateral": row.get("target_mean_abs_lateral", ""),
                "target_progress": row.get("target_progress", ""),
                "rank_gain": row.get("rank_gain", ""),
                "finish_step": row.get("finish_step", ""),
                "summary_file": row.get("_summary_file", ""),
            }
        )
        for index, event in enumerate(events):
            grass = as_float(event.get("window_grass_rate"))
            lateral = as_float(event.get("window_max_abs_lateral"))
            event_rows.append(
                {
                    "run_id": rid,
                    "case_id": cid,
                    "benchmark": row["_benchmark"],
                    "algorithm": row["algorithm"],
                    "num_agents": row["num_agents"],
                    "seed": row["seed"],
                    "event_index": index,
                    "opponent": event.get("opponent", ""),
                    "quality_class": event_quality(event),
                    "start_step": event.get("start_step", ""),
                    "complete_step": event.get("complete_step", ""),
                    "duration_steps": event.get("duration_steps", ""),
                    "window_steps": event.get("window_steps", ""),
                    "window_grass_rate": "" if grass is None else grass,
                    "window_backward_rate": event.get("window_backward_rate", ""),
                    "window_mean_abs_lateral": event.get("window_mean_abs_lateral", ""),
                    "window_max_abs_lateral": "" if lateral is None else lateral,
                    "window_heading_error_mean_rad": event.get("window_heading_error_mean_rad", ""),
                    "window_contact_proxy": event.get("window_contact_proxy", ""),
                    "on_track_overtake": bool(event.get("on_track_overtake")),
                    "elegant_overtake": bool(event.get("elegant_overtake")),
                    "diagnostic_reason": event_reason(event),
                }
            )
    return run_rows, event_rows


def event_reason(event):
    if bool(event.get("elegant_overtake")):
        return "elegant"
    reasons = []
    if not bool(event.get("on_track_overtake")):
        reasons.append("off_track_window")
    if (as_float(event.get("window_grass_rate")) or 0.0) > 0.05:
        reasons.append("grass_exposure")
    if (as_float(event.get("window_backward_rate")) or 0.0) > 0.0:
        reasons.append("backward_motion")
    if (as_float(event.get("window_contact_proxy")) or 0.0) > 0.0:
        reasons.append("contact_proxy")
    if (as_float(event.get("window_max_abs_lateral")) or 0.0) > 0.45:
        reasons.append("large_lateral_offset")
    return ";".join(reasons) if reasons else "on_track_but_non_elegant"


def build_algorithm_rows(run_rows, event_rows):
    by_algorithm = defaultdict(list)
    events_by_algorithm = defaultdict(list)
    for row in run_rows:
        by_algorithm[row["algorithm"]].append(row)
    for row in event_rows:
        events_by_algorithm[row["algorithm"]].append(row)
    out = []
    for algorithm in sorted(by_algorithm, key=lambda x: ALGORITHM_ORDER.index(x) if x in ALGORITHM_ORDER else 99):
        runs = by_algorithm[algorithm]
        events = events_by_algorithm[algorithm]
        event_count = len(events)
        outcomes = Counter(row["outcome_class"] for row in runs)
        qualities = Counter(row["quality_class"] for row in events)
        out.append(
            {
                "algorithm": algorithm,
                "algorithm_short_cn": ALGORITHM_SHORT.get(algorithm, algorithm),
                "run_count": len(runs),
                "event_count": event_count,
                "no_overtake_run_rate": ratio(outcomes["no_overtake"], len(runs)),
                "off_track_overtake_run_rate": ratio(outcomes["off_track_overtake"], len(runs)),
                "on_track_non_elegant_run_rate": ratio(outcomes["on_track_non_elegant"], len(runs)),
                "elegant_overtake_run_rate": ratio(outcomes["elegant_overtake"], len(runs)),
                "event_elegant_rate": ratio(qualities["elegant"], event_count),
                "event_on_track_non_elegant_rate": ratio(qualities["on_track_non_elegant"], event_count),
                "event_off_track_rate": ratio(qualities["off_track"], event_count),
                "first_start_step_median": median(row["first_start_step"] for row in runs),
                "first_duration_steps_median": median(row["first_duration_steps"] for row in runs),
                "window_grass_rate_mean": mean(row["window_grass_rate_mean"] for row in runs),
                "window_max_abs_lateral_mean": mean(row["window_max_abs_lateral_mean"] for row in runs),
                "target_grass_rate_mean": mean(row["target_grass_rate"] for row in runs),
            }
        )
    return out


def build_pair_rows(run_rows):
    index = defaultdict(dict)
    for row in run_rows:
        index[(row["benchmark"], row["num_agents"], row["seed"])][row["algorithm"]] = row
    out = []
    for key, rows in sorted(index.items()):
        if PRIMARY not in rows or BASELINE not in rows:
            continue
        primary = rows[PRIMARY]
        baseline = rows[BASELINE]
        p_duration = as_float(primary["first_duration_steps"])
        b_duration = as_float(baseline["first_duration_steps"])
        p_grass = as_float(primary["window_grass_rate_mean"])
        b_grass = as_float(baseline["window_grass_rate_mean"])
        p_lateral = as_float(primary["window_max_abs_lateral_mean"])
        b_lateral = as_float(baseline["window_max_abs_lateral_mean"])
        out.append(
            {
                "benchmark": key[0],
                "num_agents": key[1],
                "seed": key[2],
                "primary_outcome": primary["outcome_class"],
                "baseline_outcome": baseline["outcome_class"],
                "primary_first_duration_steps": "" if p_duration is None else p_duration,
                "baseline_first_duration_steps": "" if b_duration is None else b_duration,
                "duration_delta_primary_minus_baseline": "" if p_duration is None or b_duration is None else p_duration - b_duration,
                "primary_window_grass_rate_mean": "" if p_grass is None else p_grass,
                "baseline_window_grass_rate_mean": "" if b_grass is None else b_grass,
                "grass_delta_primary_minus_baseline": "" if p_grass is None or b_grass is None else p_grass - b_grass,
                "primary_window_max_abs_lateral_mean": "" if p_lateral is None else p_lateral,
                "baseline_window_max_abs_lateral_mean": "" if b_lateral is None else b_lateral,
                "lateral_delta_primary_minus_baseline": "" if p_lateral is None or b_lateral is None else p_lateral - b_lateral,
                "primary_target_grass_rate": primary["target_grass_rate"],
                "baseline_target_grass_rate": baseline["target_grass_rate"],
                "target_grass_delta_primary_minus_baseline": (
                    "" if as_float(primary["target_grass_rate"]) is None or as_float(baseline["target_grass_rate"]) is None
                    else as_float(primary["target_grass_rate"]) - as_float(baseline["target_grass_rate"])
                ),
                "primary_rank_gain": primary["rank_gain"],
                "baseline_rank_gain": baseline["rank_gain"],
            }
        )
    return out


def make_figure(algorithm_rows, pair_rows, out_dir):
    font_name = configure_chinese_matplotlib()
    rows = [row for row in algorithm_rows if row["algorithm"] in ALGORITHM_ORDER]
    labels = [row["algorithm_short_cn"] for row in rows]
    x = list(range(len(rows)))
    fig, axes = plt.subplots(2, 2, figsize=(9.4, 6.2), constrained_layout=True)
    fig.suptitle("超车行为诊断：成功率之外的可解释证据", fontsize=12, fontweight="bold")

    ax = axes[0][0]
    bottom = [0.0] * len(rows)
    stacks = [
        ("elegant_overtake_run_rate", "Desirable overtaking behavior", "#4C78A8"),
        ("on_track_non_elegant_run_rate", "赛道内但不符合 desirable overtaking behavior 标准", "#72B7B2"),
        ("off_track_overtake_run_rate", "越界/草地超车", "#F58518"),
        ("no_overtake_run_rate", "未超车", "#B8B8B8"),
    ]
    for key, label, color in stacks:
        values = [as_float(row[key]) or 0.0 for row in rows]
        ax.bar(x, values, bottom=bottom, label=label, color=color)
        bottom = [a + b for a, b in zip(bottom, values)]
    ax.set_ylim(0, 1.0)
    ax.set_ylabel("运行占比")
    ax.set_title("A 运行结局构成")
    ax.set_xticks(x, labels, rotation=25, ha="right")
    ax.legend(ncol=2, fontsize=6.4)

    ax = axes[0][1]
    width = 0.26
    event_keys = [
        ("event_elegant_rate", "desirable behavior事件", "#4C78A8", -width),
        ("event_on_track_non_elegant_rate", "赛道内但不符合 desirable overtaking behavior 标准", "#72B7B2", 0),
        ("event_off_track_rate", "越界事件", "#F58518", width),
    ]
    for key, label, color, offset in event_keys:
        ax.bar([i + offset for i in x], [as_float(row[key]) or 0.0 for row in rows], width=width, label=label, color=color)
    ax.set_ylim(0, 1.0)
    ax.set_ylabel("事件占比")
    ax.set_title("B 超车事件质量")
    ax.set_xticks(x, labels, rotation=25, ha="right")
    ax.legend(fontsize=6.4)

    ax = axes[1][0]
    ax.scatter(
        [as_float(row["duration_delta_primary_minus_baseline"]) for row in pair_rows if as_float(row["duration_delta_primary_minus_baseline"]) is not None],
        [as_float(row["grass_delta_primary_minus_baseline"]) for row in pair_rows if as_float(row["duration_delta_primary_minus_baseline"]) is not None and as_float(row["grass_delta_primary_minus_baseline"]) is not None],
        s=22,
        color="#4C78A8",
        alpha=0.78,
    )
    ax.axhline(0, color="#555555", linewidth=0.8, linestyle="--")
    ax.axvline(0, color="#555555", linewidth=0.8, linestyle="--")
    ax.set_xlabel("完成耗时差值：本文方法 - DLC原始")
    ax.set_ylabel("窗口草地率差值")
    ax.set_title("C 逐 case 配对差异")

    ax = axes[1][1]
    reasons = Counter()
    for row in pair_rows:
        if row["primary_outcome"] != "elegant_overtake":
            reasons[f"本文:{row['primary_outcome']}"] += 1
        if row["baseline_outcome"] != "elegant_overtake":
            reasons[f"DLC:{row['baseline_outcome']}"] += 1
    reason_items = reasons.most_common(8)
    ax.barh([item[0] for item in reason_items], [item[1] for item in reason_items], color="#54A24B")
    ax.invert_yaxis()
    ax.set_xlabel("case 数")
    ax.set_title("D 不符合 desirable overtaking behavior 标准/未超车主要结局")

    paths = {}
    for suffix in ["svg", "pdf", "png", "tiff"]:
        path = out_dir / "figures" / f"figure_overtake_casewise_diagnostics_cn.{suffix}"
        fig.savefig(path, dpi=450 if suffix in {"png", "tiff"} else None)
        paths[suffix] = str(path)
    plt.close(fig)
    paths["font"] = font_name
    return paths


def build_markdown(report):
    s = report["summary"]
    lines = [
        "# T-ITS Overtake Casewise Diagnostics Pack",
        "",
        "该包从 240 次正式在线运行的 summary JSON 与 source CSV 中派生事件级、运行级和逐 case 配对诊断，用于解释“为什么成功超车不等于Desirable overtaking behavior”。",
        "",
        "## Figure Contract",
        "",
        "- Core conclusion: 主方法相对 DLC 原始世界模型不仅更快完成超车，还需要用事件窗口解释超车是否在赛道内、是否desirable behavior、是否存在草地暴露。",
        "- Archetype: quantitative grid。",
        "- Source data: `outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv` 与每个运行的 `_summary_file`。",
        "- Export: SVG/PDF/PNG/TIFF，中文图中文字通过 Noto CJK 字体显式嵌入/注册。",
        "",
        "## Summary",
        "",
        f"- Status: `{report['status']}`",
        f"- Source rows: {s['source_rows']}",
        f"- Run diagnostics: {s['run_rows']}",
        f"- Event diagnostics: {s['event_rows']}",
        f"- Algorithms: {s['algorithm_count']}",
        f"- Matched primary-vs-DLC cases: {s['pair_rows']}",
        f"- Primary desirable overtaking behavior run rate: {fmt(s['primary_elegant_run_rate'])}",
        f"- DLC original desirable overtaking behavior run rate: {fmt(s['baseline_elegant_run_rate'])}",
        f"- Primary off-track overtake run rate: {fmt(s['primary_offtrack_run_rate'])}",
        f"- DLC original off-track overtake run rate: {fmt(s['baseline_offtrack_run_rate'])}",
        f"- Pairwise median duration delta: {fmt(s['pair_median_duration_delta'], 2)} steps",
        f"- Pairwise mean grass-window delta: {fmt(s['pair_mean_grass_delta'], 3)}",
        "",
        "## Interpretation",
        "",
        "- `outcome_class` 将每次运行分为 `no_overtake`、`off_track_overtake`、`on_track_non_elegant`、`elegant_overtake`，比单一成功率更适合定位超车质量瓶颈。",
        "- `duration_delta_primary_minus_baseline < 0` 表示主方法在同一 case 中比 DLC 原始模型更快完成首次超车。",
        "- `grass_delta_primary_minus_baseline < 0` 表示主方法在超车窗口内草地暴露更低，是“Desirable overtaking behavior”的关键证据之一。",
        "- 该包是解释性诊断，不替代正式统计表、事件一致性审计或在线基准主结果。",
        "",
        "## Key Files",
        "",
        "- Event-level table: `tables/overtake_event_diagnostics.csv`",
        "- Run-level table: `tables/overtake_run_diagnostics.csv`",
        "- Algorithm table: `tables/overtake_algorithm_diagnostics.csv`",
        "- Pairwise table: `tables/overtake_primary_vs_dlc_pairwise_diagnostics.csv`",
        "- 中文 figure: `figures/figure_overtake_casewise_diagnostics_cn.svg`",
        "",
        "## Regeneration",
        "",
        "```bash",
        "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_overtake_casewise_diagnostics_pack.py --out-dir outputs/tits_dynamic_graph/tits_overtake_casewise_diagnostics_pack",
        "```",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Export casewise overtaking diagnostics for T-ITS evidence.")
    parser.add_argument("--source-csv", default=SOURCE_CSV)
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/tits_overtake_casewise_diagnostics_pack")
    args = parser.parse_args()

    root = Path.cwd()
    out_dir = root / args.out_dir
    (out_dir / "tables").mkdir(parents=True, exist_ok=True)
    (out_dir / "figures").mkdir(parents=True, exist_ok=True)
    (out_dir / "materials").mkdir(parents=True, exist_ok=True)

    source_rows = read_csv(root / args.source_csv)
    run_rows, event_rows = load_runs(root, source_rows)
    algorithm_rows = build_algorithm_rows(run_rows, event_rows)
    pair_rows = build_pair_rows(run_rows)
    figure_paths = make_figure(algorithm_rows, pair_rows, out_dir)
    algo_index = {row["algorithm"]: row for row in algorithm_rows}
    summary = {
        "status": "pass",
        "source_rows": len(source_rows),
        "run_rows": len(run_rows),
        "event_rows": len(event_rows),
        "algorithm_count": len(algorithm_rows),
        "pair_rows": len(pair_rows),
        "primary_elegant_run_rate": algo_index.get(PRIMARY, {}).get("elegant_overtake_run_rate"),
        "baseline_elegant_run_rate": algo_index.get(BASELINE, {}).get("elegant_overtake_run_rate"),
        "primary_offtrack_run_rate": algo_index.get(PRIMARY, {}).get("off_track_overtake_run_rate"),
        "baseline_offtrack_run_rate": algo_index.get(BASELINE, {}).get("off_track_overtake_run_rate"),
        "pair_median_duration_delta": median(row["duration_delta_primary_minus_baseline"] for row in pair_rows),
        "pair_mean_grass_delta": mean(row["grass_delta_primary_minus_baseline"] for row in pair_rows),
        "figure_font": figure_paths["font"],
    }
    status = "pass" if len(run_rows) == len(source_rows) and len(pair_rows) == 30 else "review_required"
    summary["status"] = status
    report = {
        "status": status,
        "summary": summary,
        "figure_paths": figure_paths,
        "note": "Casewise diagnostics are derived from frozen online-run summaries and are intended for mechanism interpretation.",
    }
    paths = {
        "run_table": write_csv(
            out_dir / "tables" / "overtake_run_diagnostics.csv",
            run_rows,
            [
                "run_id", "case_id", "benchmark", "algorithm", "algorithm_label_cn", "num_agents", "seed", "track_path", "traffic_profile",
                "outcome_class", "event_count", "elegant_event_count", "on_track_non_elegant_event_count", "off_track_event_count",
                "first_start_step", "first_complete_step", "first_duration_steps", "first_window_grass_rate", "first_window_max_abs_lateral",
                "window_grass_rate_mean", "window_max_abs_lateral_mean", "target_grass_rate", "target_mean_abs_lateral", "target_progress",
                "rank_gain", "finish_step", "summary_file",
            ],
        ),
        "event_table": write_csv(
            out_dir / "tables" / "overtake_event_diagnostics.csv",
            event_rows,
            [
                "run_id", "case_id", "benchmark", "algorithm", "num_agents", "seed", "event_index", "opponent", "quality_class",
                "start_step", "complete_step", "duration_steps", "window_steps", "window_grass_rate", "window_backward_rate",
                "window_mean_abs_lateral", "window_max_abs_lateral", "window_heading_error_mean_rad", "window_contact_proxy",
                "on_track_overtake", "elegant_overtake", "diagnostic_reason",
            ],
        ),
        "algorithm_table": write_csv(
            out_dir / "tables" / "overtake_algorithm_diagnostics.csv",
            algorithm_rows,
            [
                "algorithm", "algorithm_short_cn", "run_count", "event_count", "no_overtake_run_rate", "off_track_overtake_run_rate",
                "on_track_non_elegant_run_rate", "elegant_overtake_run_rate", "event_elegant_rate", "event_on_track_non_elegant_rate",
                "event_off_track_rate", "first_start_step_median", "first_duration_steps_median", "window_grass_rate_mean",
                "window_max_abs_lateral_mean", "target_grass_rate_mean",
            ],
        ),
        "pairwise_table": write_csv(
            out_dir / "tables" / "overtake_primary_vs_dlc_pairwise_diagnostics.csv",
            pair_rows,
            [
                "benchmark", "num_agents", "seed", "primary_outcome", "baseline_outcome", "primary_first_duration_steps",
                "baseline_first_duration_steps", "duration_delta_primary_minus_baseline", "primary_window_grass_rate_mean",
                "baseline_window_grass_rate_mean", "grass_delta_primary_minus_baseline", "primary_window_max_abs_lateral_mean",
                "baseline_window_max_abs_lateral_mean", "lateral_delta_primary_minus_baseline", "primary_target_grass_rate",
                "baseline_target_grass_rate", "target_grass_delta_primary_minus_baseline", "primary_rank_gain", "baseline_rank_gain",
            ],
        ),
        "figure_svg": figure_paths["svg"],
        "figure_pdf": figure_paths["pdf"],
        "figure_png": figure_paths["png"],
        "figure_tiff": figure_paths["tiff"],
    }
    report["paths"] = paths
    paths["report_json"] = write_json(out_dir / "materials" / "OVERTAKE_CASEWISE_DIAGNOSTICS_REPORT.json", report)
    paths["report_md"] = write_text(out_dir / "materials" / "OVERTAKE_CASEWISE_DIAGNOSTICS_REPORT.md", build_markdown(report))
    manifest = {
        "status": status,
        "out_dir": args.out_dir,
        "summary": summary,
        "paths": paths,
        "note": report["note"],
    }
    manifest_path = write_json(out_dir / "tits_overtake_casewise_diagnostics_pack_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, "status": status, "summary": summary}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
