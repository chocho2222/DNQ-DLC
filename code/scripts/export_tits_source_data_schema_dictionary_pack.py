#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import json
import math
from collections import Counter
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib import font_manager


SOURCE_CSV = "outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv"
EXPECTED_ROWS = 240
EXPECTED_FIELDS = 42
EXPECTED_CASES = 30
EXPECTED_ALGORITHMS = 8
PLANNER_ALGORITHMS = {"v6_runtime_dynamic_neighborhood_safe"}
RULE_ALGORITHMS = {"rule_expert_gate"}


FIELD_ORDER = [
    "_benchmark",
    "algorithm",
    "algorithm_label_cn",
    "neighbor_selection_mode",
    "planner_horizon",
    "planner_candidates",
    "planner_risk_weight",
    "planner_progress_weight",
    "planner_uncertainty_weight",
    "overtake_aware_planner",
    "seed",
    "num_agents",
    "track_path",
    "traffic_profile",
    "target_final_rank",
    "rank_gain",
    "target_progress",
    "target_completed_lap",
    "overtake_success_rate",
    "overtake_count",
    "on_track_overtake_count",
    "on_track_overtake_rate",
    "elegant_overtake_count",
    "elegant_overtake_rate",
    "time_to_first_overtake",
    "overtake_start_to_complete_time",
    "overtake_window_grass_rate_mean",
    "overtake_window_max_abs_lateral_mean",
    "target_grass_rate",
    "grass_recovery_time_mean",
    "grass_recovery_time_max",
    "grass_excursion_count",
    "unrecovered_grass_excursion_count",
    "target_mean_abs_lateral",
    "target_heading_error_mean_rad",
    "collision_or_contact_proxy",
    "compute_latency_ms",
    "compute_latency_p95_ms",
    "finish_step",
    "topdown_gif",
    "first_person_gif",
    "_summary_file",
]


FIELD_META = {
    "_benchmark": ("实验场景", "benchmark family used by the formal matrix", "categorical", "NA", "required", "design"),
    "algorithm": ("算法ID", "machine-readable algorithm identifier", "categorical", "NA", "required", "algorithm config"),
    "algorithm_label_cn": ("算法中文标签", "Chinese display label used by plots and tables", "categorical", "NA", "required", "algorithm config"),
    "neighbor_selection_mode": ("邻域选择模式", "runtime graph neighbor construction mode", "categorical", "NA", "required", "algorithm config"),
    "planner_horizon": ("规划时域", "candidate-planner rollout horizon for the primary planner", "integer", "steps", "planner_only", "algorithm config"),
    "planner_candidates": ("规划候选数", "number of online candidate controls evaluated by the planner", "integer", "count", "planner_only", "algorithm config"),
    "planner_risk_weight": ("风险权重", "risk term weight in the online planner score", "float", "weight", "planner_only", "algorithm config"),
    "planner_progress_weight": ("进度权重", "reserved progress-score weight column; currently unused in the frozen matrix", "float", "weight", "reserved_blank", "algorithm config"),
    "planner_uncertainty_weight": ("不确定性权重", "world-model uncertainty penalty weight in the online planner score", "float", "weight", "planner_only", "algorithm config"),
    "overtake_aware_planner": ("超车感知规划开关", "whether the controller uses overtake-aware planning logic", "boolean", "NA", "non_rule_only", "algorithm config"),
    "seed": ("随机种子", "matched-case random seed", "integer", "NA", "required", "design"),
    "num_agents": ("车辆数", "number of vehicles in the online race", "integer", "vehicles", "required", "design"),
    "track_path": ("赛道路径", "procedural marker or external track artifact path", "path_or_label", "NA", "required", "design"),
    "traffic_profile": ("交通配置", "background traffic-speed profile", "categorical", "NA", "required", "design"),
    "target_final_rank": ("目标车最终名次", "rank of the target vehicle at termination, lower is better", "integer", "rank", "required", "outcome"),
    "rank_gain": ("名次提升", "starting rank minus final rank for the target vehicle", "integer", "rank", "required", "outcome"),
    "target_progress": ("目标车进度", "normalized track progress of the target vehicle at termination", "float", "lap fraction", "required", "outcome"),
    "target_completed_lap": ("目标车是否完赛", "whether the target completed a full lap before termination", "boolean", "NA", "required", "outcome"),
    "overtake_success_rate": ("是否发生超车", "run-level binary overtake success indicator encoded as a rate", "rate", "0-1", "required", "overtake quality"),
    "overtake_count": ("超车次数", "number of target-car overtake events", "integer", "count", "required", "overtake quality"),
    "on_track_overtake_count": ("赛道内超车次数", "number of overtake events completed on track", "integer", "count", "required", "overtake quality"),
    "on_track_overtake_rate": ("赛道内超车率", "on-track overtake count divided by total overtake count", "rate", "0-1", "required", "overtake quality"),
    "elegant_overtake_count": ("Desirable overtaking behavior次数", "number of overtake events satisfying on-track and lateral-quality criteria", "integer", "count", "required", "overtake quality"),
    "elegant_overtake_rate": ("Desirable overtaking behavior rate", "desirable overtaking behavior count divided by total overtake count", "rate", "0-1", "required", "overtake quality"),
    "time_to_first_overtake": ("首次超车时间", "simulation step index at first completed overtake", "float", "steps", "event_conditioned", "overtake quality"),
    "overtake_start_to_complete_time": ("超车完成耗时", "duration from overtake-window start to completion", "float", "steps", "event_conditioned", "overtake quality"),
    "overtake_window_grass_rate_mean": ("超车窗口草地率", "mean off-track/grass exposure during overtake windows", "rate", "0-1", "event_conditioned", "safety proxy"),
    "overtake_window_max_abs_lateral_mean": ("超车窗口最大横向偏移均值", "mean maximum absolute lateral deviation during overtake windows", "float", "normalized lateral", "event_conditioned", "safety proxy"),
    "target_grass_rate": ("目标车草地率", "fraction of target-car steps off track/on grass", "rate", "0-1", "required", "safety proxy"),
    "grass_recovery_time_mean": ("草地恢复平均时间", "mean recovery duration after grass excursions", "float", "steps", "grass_conditioned", "safety proxy"),
    "grass_recovery_time_max": ("草地恢复最长时间", "maximum recovery duration after grass excursions", "float", "steps", "grass_conditioned", "safety proxy"),
    "grass_excursion_count": ("草地偏离次数", "number of target-car grass/off-track excursions", "integer", "count", "required", "safety proxy"),
    "unrecovered_grass_excursion_count": ("未恢复草地偏离次数", "number of grass excursions not recovered before termination", "integer", "count", "required", "safety proxy"),
    "target_mean_abs_lateral": ("目标车平均横向偏移", "mean absolute lateral deviation of the target vehicle", "float", "normalized lateral", "required", "safety proxy"),
    "target_heading_error_mean_rad": ("目标车航向误差均值", "mean target heading error", "float", "radians", "required", "safety proxy"),
    "collision_or_contact_proxy": ("碰撞/接触代理", "simulation proxy for collision or contact events", "rate", "0-1", "required", "safety proxy"),
    "compute_latency_ms": ("平均计算延迟", "mean per-step decision latency", "float", "ms", "required", "compute"),
    "compute_latency_p95_ms": ("P95计算延迟", "95th percentile per-step decision latency", "float", "ms", "required", "compute"),
    "finish_step": ("终止步数", "simulation termination step", "integer", "steps", "required", "design"),
    "topdown_gif": ("俯视动图路径", "optional representative top-down GIF path; formal GIFs are indexed separately", "path", "NA", "media_external_index", "media/provenance"),
    "first_person_gif": ("第一视角动图路径", "optional representative first-person GIF path; formal GIFs are indexed separately", "path", "NA", "media_external_index", "media/provenance"),
    "_summary_file": ("summary文件路径", "linked run-level summary JSON used for provenance and recomputation", "path", "NA", "required", "media/provenance"),
}


TYPE_EXPECTATIONS = {
    "integer": "integer-valued numeric",
    "float": "finite numeric",
    "rate": "finite numeric in [0,1]",
    "boolean": "true/false",
    "categorical": "nonempty string",
    "path": "path string when present",
    "path_or_label": "path or categorical label",
}


def read_csv(path):
    path = Path(path)
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader), list(reader.fieldnames or [])


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


def is_blank(value):
    return value is None or str(value).strip() == ""


def to_float(value):
    if is_blank(value):
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(out) or math.isinf(out):
        return None
    return out


def is_int_text(value):
    number = to_float(value)
    return number is not None and abs(number - round(number)) <= 1e-9


def row_key(row):
    return f"{row.get('_benchmark')}|n{row.get('num_agents')}|seed{row.get('seed')}|{row.get('algorithm')}"


def case_key(row):
    return (
        row.get("_benchmark", ""),
        row.get("num_agents", ""),
        row.get("seed", ""),
        row.get("track_path", ""),
        row.get("traffic_profile", ""),
    )


def field_dictionary_rows():
    rows = []
    for idx, field in enumerate(FIELD_ORDER, start=1):
        cn, desc, dtype, unit, missing_policy, group = FIELD_META[field]
        rows.append(
            {
                "order": idx,
                "field": field,
                "name_cn": cn,
                "description": desc,
                "data_type": dtype,
                "unit": unit,
                "required_policy": missing_policy,
                "missing_value_policy": missing_policy_text(missing_policy),
                "field_group": group,
                "type_expectation": TYPE_EXPECTATIONS.get(dtype, "string"),
                "recompute_or_source": source_text(field, missing_policy),
            }
        )
    return rows


def missing_policy_text(policy):
    mapping = {
        "required": "所有正式 run 必须非空。",
        "planner_only": "仅规划器主算法字段非空；其它 baseline 允许为空。",
        "reserved_blank": "预留字段，当前冻结矩阵允许全空。",
        "non_rule_only": "规则专家不使用该开关可为空；学习/世界模型算法应非空。",
        "event_conditioned": "仅发生至少一次超车的 run 应非空；无超车 run 允许为空。",
        "grass_conditioned": "仅发生可恢复草地偏离时非空；无可恢复事件时允许为空。",
        "media_external_index": "正式 source CSV 允许为空；代表性 GIF 由 publication_gifs/provenance 包另行索引。",
    }
    return mapping.get(policy, "允许为空规则未定义。")


def source_text(field, policy):
    if field == "_summary_file":
        return "summary JSON provenance link"
    if field in {"topdown_gif", "first_person_gif"}:
        return "publication_gifs and GIF provenance manifests"
    if policy in {"planner_only", "reserved_blank", "non_rule_only"}:
        return "algorithm card / online planner configuration"
    if field.startswith("_") or field in {"seed", "num_agents", "track_path", "traffic_profile", "finish_step"}:
        return "frozen case command and run summary"
    if "overtake" in field or field in {"rank_gain", "target_final_rank", "target_progress", "target_completed_lap"}:
        return "run summary and overtake event recomputation audits"
    if "grass" in field or "lateral" in field or "heading" in field or "collision" in field:
        return "run summary, trace integrity, and safety proxy audit"
    if "latency" in field:
        return "run summary and trace latency profile"
    return "run summary"


def profile_field(rows, field):
    values = [row.get(field, "") for row in rows]
    nonempty_values = [value for value in values if not is_blank(value)]
    numeric = [to_float(value) for value in nonempty_values]
    numeric = [value for value in numeric if value is not None]
    unique_values = sorted({str(value) for value in nonempty_values})
    out = {
        "field": field,
        "row_count": len(rows),
        "nonempty_count": len(nonempty_values),
        "missing_count": len(values) - len(nonempty_values),
        "missing_rate": round((len(values) - len(nonempty_values)) / len(values), 6) if values else "",
        "unique_count": len(unique_values),
        "example_values": "; ".join(unique_values[:12]),
        "numeric_count": len(numeric),
        "numeric_min": "",
        "numeric_max": "",
        "numeric_mean": "",
    }
    if numeric:
        out["numeric_min"] = min(numeric)
        out["numeric_max"] = max(numeric)
        out["numeric_mean"] = sum(numeric) / len(numeric)
    return out


def allowed_missing(row, field, policy):
    algorithm = row.get("algorithm", "")
    overtake_count = int(round(to_float(row.get("overtake_count")) or 0))
    grass_count = int(round(to_float(row.get("grass_excursion_count")) or 0))
    if policy == "required":
        return False, "required field"
    if policy == "planner_only":
        return algorithm not in PLANNER_ALGORITHMS, "not a planner-primary algorithm"
    if policy == "reserved_blank":
        return True, "reserved unused column"
    if policy == "non_rule_only":
        return algorithm in RULE_ALGORITHMS, "rule baseline does not use learned planner switch"
    if policy == "event_conditioned":
        return overtake_count == 0, "no completed overtake event"
    if policy == "grass_conditioned":
        unrecovered = int(round(to_float(row.get("unrecovered_grass_excursion_count")) or 0))
        return grass_count == 0 or unrecovered > 0, "no closed/recovered grass excursion duration is defined"
    if policy == "media_external_index":
        return True, "media indexed outside the formal source CSV"
    return False, "unknown policy"


def check_type(value, dtype):
    if is_blank(value):
        return True, ""
    if dtype == "integer":
        return is_int_text(value), "not integer-valued"
    if dtype == "float":
        return to_float(value) is not None, "not finite numeric"
    if dtype == "rate":
        number = to_float(value)
        return number is not None and 0.0 <= number <= 1.0, "not a [0,1] rate"
    if dtype == "boolean":
        return str(value).strip().lower() in {"true", "false", "0", "1"}, "not boolean"
    return True, ""


def validate(rows, fields):
    validation_rows = []
    issues = []
    dictionary_fields = set(FIELD_ORDER)
    observed_fields = set(fields)
    for field in FIELD_ORDER:
        if field not in observed_fields:
            issues.append({"severity": "error", "category": "schema", "field": field, "row_id": "", "message": "字段字典字段未出现在 source CSV。"})
    for field in fields:
        if field not in dictionary_fields:
            issues.append({"severity": "error", "category": "schema", "field": field, "row_id": "", "message": "source CSV 出现字段字典未定义的额外字段。"})

    case_count = len({case_key(row) for row in rows})
    algorithm_count = len({row.get("algorithm") for row in rows})
    design_checks = [
        ("row_count", len(rows), EXPECTED_ROWS),
        ("field_count", len(fields), EXPECTED_FIELDS),
        ("case_count", case_count, EXPECTED_CASES),
        ("algorithm_count", algorithm_count, EXPECTED_ALGORITHMS),
    ]
    for check, observed, expected in design_checks:
        validation_rows.append(
            {
                "check_id": check,
                "field": "",
                "row_id": "",
                "status": "pass" if observed == expected else "fail",
                "expected": expected,
                "observed": observed,
                "message": "",
            }
        )
        if observed != expected:
            issues.append({"severity": "error", "category": "design", "field": "", "row_id": "", "message": f"{check} expected {expected}, observed {observed}."})

    meta = {row["field"]: row for row in field_dictionary_rows()}
    for row in rows:
        for field in fields:
            if field not in meta:
                continue
            policy = meta[field]["required_policy"]
            dtype = meta[field]["data_type"]
            value = row.get(field, "")
            if is_blank(value):
                allowed, reason = allowed_missing(row, field, policy)
                status = "pass" if allowed else "fail"
                if not allowed:
                    issues.append({"severity": "error", "category": "missing", "field": field, "row_id": row_key(row), "message": "必填字段为空。"})
                validation_rows.append(
                    {
                        "check_id": "missing_policy",
                        "field": field,
                        "row_id": row_key(row),
                        "status": status,
                        "expected": meta[field]["missing_value_policy"],
                        "observed": "blank",
                        "message": reason,
                    }
                )
            else:
                ok, reason = check_type(value, dtype)
                status = "pass" if ok else "fail"
                if not ok:
                    issues.append({"severity": "error", "category": "type", "field": field, "row_id": row_key(row), "message": reason})
                validation_rows.append(
                    {
                        "check_id": "type_policy",
                        "field": field,
                        "row_id": row_key(row),
                        "status": status,
                        "expected": meta[field]["type_expectation"],
                        "observed": value,
                        "message": reason,
                    }
                )

    return validation_rows, issues


def build_missingness_rows(dictionary_rows, profile_rows):
    profile = {row["field"]: row for row in profile_rows}
    out = []
    for item in dictionary_rows:
        field = item["field"]
        p = profile[field]
        out.append(
            {
                "field_group": item["field_group"],
                "field": field,
                "name_cn": item["name_cn"],
                "required_policy": item["required_policy"],
                "missing_count": p["missing_count"],
                "missing_rate": p["missing_rate"],
                "missing_interpretation": item["missing_value_policy"],
            }
        )
    return out


def write_figure(path_base, missingness_rows):
    groups = []
    values = []
    for group, group_rows in sorted(group_rows_by(missingness_rows).items()):
        groups.append(group)
        values.append(sum(float(row["missing_rate"]) for row in group_rows) / len(group_rows))
    cjk_font = find_cjk_font()
    if cjk_font:
        font_manager.fontManager.addfont(cjk_font)
        mpl.rcParams["font.sans-serif"] = [font_manager.FontProperties(fname=cjk_font).get_name(), "DejaVu Sans"]
    else:
        mpl.rcParams["font.sans-serif"] = ["DejaVu Sans"]
    mpl.rcParams["axes.unicode_minus"] = False
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    colors = ["#31688e", "#35b779", "#fde725", "#440154", "#21918c", "#b8de29", "#443983"]
    ax.barh(groups, values, color=colors[: len(groups)])
    ax.set_xlabel("平均缺失率")
    ax.set_title("正式 source data 字段分组缺失率")
    ax.set_xlim(0, max(values + [0.05]) * 1.18)
    for idx, value in enumerate(values):
        ax.text(value + 0.01, idx, f"{value:.2f}", va="center", fontsize=9)
    fig.tight_layout()
    paths = {}
    for suffix in ["svg", "pdf", "png", "tiff"]:
        path = Path(f"{path_base}.{suffix}")
        path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, dpi=300)
        paths[f"figure_{suffix}"] = str(path)
    plt.close(fig)
    return paths


def find_cjk_font():
    candidates = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
        "/usr/share/fonts/truetype/arphic/uming.ttc",
        "/usr/share/fonts/truetype/arphic/ukai.ttc",
    ]
    for item in candidates:
        if Path(item).exists():
            return item
    return ""


def group_rows_by(rows):
    out = {}
    for row in rows:
        out.setdefault(row["field_group"], []).append(row)
    return out


def build_markdown(report):
    summary = report["summary"]
    lines = [
        "# T-ITS Source Data Schema Dictionary Pack",
        "",
        "该包给出正式 `online_benchmark_source_data.csv` 的字段级数据字典、机器可读 schema、自动 profile、缺失策略和逐单元 schema 验证结果。它的作用不是新增实验，而是让第三方审稿人能够准确理解 240-run source data 中每一列的含义、类型、单位、允许缺失条件和复算来源。",
        "",
        "## Summary",
        "",
    ]
    for key, value in summary.items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Missingness Policy",
            "",
            "- `planner_only`: 只适用于本文主规划器字段；DLC 变种和规则专家允许为空。",
            "- `reserved_blank`: 预留字段，当前正式矩阵未使用，允许全空；这不是数据丢失。",
            "- `event_conditioned`: 只在发生超车时有定义；未发生超车的 run 允许为空。",
            "- `grass_conditioned`: 只在存在可恢复草地偏离时有定义；无相关事件时允许为空。",
            "- `media_external_index`: 正式 source CSV 不直接存 GIF 路径；俯视和第一视角 GIF 由 publication GIF provenance/index 包追溯。",
            "",
            "## Field Groups",
            "",
            "| group | fields | mean missing rate |",
            "|---|---:|---:|",
        ]
    )
    for group, value in report["group_summary"].items():
        lines.append(f"| {group} | {value['field_count']} | {value['mean_missing_rate']:.3f} |")
    lines.extend(
        [
            "",
            "## Validation",
            "",
            f"- Blocking schema/type/missing-policy issues: {summary['blocking_issue_count']}",
            f"- Validation cells checked: {summary['validation_row_count']}",
            f"- Dictionary fields: {summary['field_count']}",
            "",
        ]
    )
    if summary["blocking_issue_count"] == 0:
        lines.append("No blocking schema dictionary issues were found.")
    else:
        lines.extend(["| category | field | row | message |", "|---|---|---|---|"])
        for issue in report["issues"][:80]:
            lines.append(f"| {issue['category']} | `{issue['field']}` | `{issue['row_id']}` | {issue['message']} |")
    lines.extend(
        [
            "",
            "## Key Outputs",
            "",
            "- Human-readable dictionary: `tables/source_data_field_dictionary.csv`",
            "- Machine-readable schema: `materials/SOURCE_DATA_SCHEMA_DICTIONARY.json`",
            "- Field profile: `tables/source_data_field_profile.csv`",
            "- Missingness profile: `tables/source_data_missingness_profile.csv`",
            "- Validation rows: `tables/source_data_schema_validation_rows.csv`",
            "- Chinese missingness figure: `figures/figure_source_data_schema_cn.svg`",
            "",
            "## Regeneration Command",
            "",
            "```bash",
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_source_data_schema_dictionary_pack.py --out-dir outputs/tits_dynamic_graph/tits_source_data_schema_dictionary_pack",
            "```",
        ]
    )
    return "\n".join(lines)


def build_report(rows, fields, dictionary_rows, profile_rows, missingness_rows, validation_rows, issues):
    group_summary = {}
    for group, group_items in group_rows_by(missingness_rows).items():
        group_summary[group] = {
            "field_count": len(group_items),
            "mean_missing_rate": sum(float(row["missing_rate"]) for row in group_items) / len(group_items),
        }
    status = "pass" if not issues else "review_required"
    return {
        "status": status,
        "source_csv": SOURCE_CSV,
        "summary": {
            "status": status,
            "source_rows": len(rows),
            "field_count": len(fields),
            "dictionary_field_count": len(dictionary_rows),
            "case_count": len({case_key(row) for row in rows}),
            "algorithm_count": len({row.get("algorithm") for row in rows}),
            "validation_row_count": len(validation_rows),
            "blocking_issue_count": len(issues),
            "fields_with_missing_values": sum(1 for row in profile_rows if int(row["missing_count"]) > 0),
            "fully_populated_fields": sum(1 for row in profile_rows if int(row["missing_count"]) == 0),
        },
        "group_summary": group_summary,
        "issues": issues,
        "note": "This pack validates source-data schema semantics only. It does not certify real-world safety and does not replace run-level provenance, trace integrity, or statistical recomputation audits.",
    }


def main():
    parser = argparse.ArgumentParser(description="Export field-level schema dictionary and profile pack for the frozen T-ITS source data.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--source-csv", default=SOURCE_CSV)
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/tits_source_data_schema_dictionary_pack")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    out_dir = root / args.out_dir
    materials = out_dir / "materials"
    tables = out_dir / "tables"
    figures = out_dir / "figures"
    materials.mkdir(parents=True, exist_ok=True)
    tables.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)

    rows, fields = read_csv(root / args.source_csv)
    dictionary_rows = field_dictionary_rows()
    profile_rows = [profile_field(rows, field) for field in fields]
    missingness_rows = build_missingness_rows(dictionary_rows, profile_rows)
    validation_rows, issues = validate(rows, fields)
    report = build_report(rows, fields, dictionary_rows, profile_rows, missingness_rows, validation_rows, issues)
    figure_paths = write_figure(figures / "figure_source_data_schema_cn", missingness_rows)

    schema_json = {
        "source_csv": args.source_csv,
        "expected": {
            "rows": EXPECTED_ROWS,
            "fields": EXPECTED_FIELDS,
            "matched_cases": EXPECTED_CASES,
            "algorithms": EXPECTED_ALGORITHMS,
        },
        "fields": dictionary_rows,
        "missing_policy_definitions": {
            row["required_policy"]: row["missing_value_policy"] for row in dictionary_rows
        },
        "boundary": report["note"],
    }

    paths = {
        "report_md": write_text(materials / "SOURCE_DATA_SCHEMA_DICTIONARY.md", build_markdown(report)),
        "schema_json": write_json(materials / "SOURCE_DATA_SCHEMA_DICTIONARY.json", schema_json),
        "field_dictionary_csv": write_csv(
            tables / "source_data_field_dictionary.csv",
            dictionary_rows,
            [
                "order",
                "field",
                "name_cn",
                "description",
                "data_type",
                "unit",
                "required_policy",
                "missing_value_policy",
                "field_group",
                "type_expectation",
                "recompute_or_source",
            ],
        ),
        "field_profile_csv": write_csv(
            tables / "source_data_field_profile.csv",
            profile_rows,
            [
                "field",
                "row_count",
                "nonempty_count",
                "missing_count",
                "missing_rate",
                "unique_count",
                "example_values",
                "numeric_count",
                "numeric_min",
                "numeric_max",
                "numeric_mean",
            ],
        ),
        "missingness_profile_csv": write_csv(
            tables / "source_data_missingness_profile.csv",
            missingness_rows,
            [
                "field_group",
                "field",
                "name_cn",
                "required_policy",
                "missing_count",
                "missing_rate",
                "missing_interpretation",
            ],
        ),
        "validation_rows_csv": write_csv(
            tables / "source_data_schema_validation_rows.csv",
            validation_rows,
            ["check_id", "field", "row_id", "status", "expected", "observed", "message"],
        ),
        "issues_csv": write_csv(
            tables / "source_data_schema_issues.csv",
            issues,
            ["severity", "category", "field", "row_id", "message"],
        ),
        **figure_paths,
    }
    manifest = {
        "status": report["status"],
        "out_dir": args.out_dir,
        "summary": report["summary"],
        "paths": paths,
        "boundary": report["note"],
    }
    manifest_path = write_json(out_dir / "tits_source_data_schema_dictionary_pack_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, "status": report["status"], "summary": report["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
