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
from matplotlib import font_manager


SOURCE_CSV = "outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv"
EXPECTED_RUNS = 240
EXPECTED_CASES = 30
EXPECTED_ALGORITHMS = 8
EXPECTED_TRACE_LENGTH = 2200

TRACE_FIELDS = [
    ("step", "步号", "1-based simulation step index", "integer", "scalar", "required", "index"),
    ("reward", "单步奖励", "per-agent instantaneous reward at this step", "float", "num_agents", "required", "environment reward"),
    ("total_reward", "累计奖励", "per-agent cumulative reward up to this step", "float", "num_agents", "required", "environment reward"),
    ("tile_visited_count", "已访问赛道块数", "per-agent visited track-tile count", "integer", "num_agents", "required", "environment state"),
    ("rank", "实时名次", "per-agent rank at this step, lower is better", "integer", "num_agents", "required", "race state"),
    ("track_index", "赛道索引", "per-agent nearest/visited track tile index", "integer", "num_agents", "required", "race state"),
    ("action", "控制动作", "per-agent continuous control vector [steer, gas, brake]", "float", "num_agents x 3", "required", "control"),
    ("speed", "速度", "per-agent speed proxy recorded by the simulator", "float", "num_agents", "required", "kinematics"),
    ("compute_latency_ms", "决策延迟", "online decision latency for this environment step", "float", "ms scalar", "required", "compute"),
    ("min_pair_distance", "最小车距", "minimum pairwise vehicle distance at this step", "float", "world units scalar", "required", "safety proxy"),
    ("telemetry.progress", "进度", "per-agent normalized lap progress", "float", "num_agents", "required", "telemetry"),
    ("telemetry.lateral_error", "横向误差", "per-agent signed lateral deviation from track centerline", "float", "num_agents", "required", "telemetry"),
    ("telemetry.heading_cos", "航向余弦", "per-agent cosine of heading alignment with local track tangent", "float", "num_agents", "required", "telemetry"),
    ("telemetry.on_grass", "是否在草地", "per-agent off-track/grass indicator", "boolean", "num_agents", "required", "telemetry"),
    ("telemetry.backward", "是否逆行", "per-agent backward-driving indicator", "boolean", "num_agents", "required", "telemetry"),
    ("positions", "二维位置", "per-agent world-frame position [x, y]", "float", "num_agents x 2", "required", "kinematics"),
    ("done", "终止标记", "environment done flag recorded at the step", "boolean", "scalar", "required", "termination"),
]


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


def f(value):
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(out) or math.isinf(out):
        return None
    return out


def run_id(row):
    return f"{row.get('_benchmark')}|n{row.get('num_agents')}|seed{row.get('seed')}|{row.get('algorithm')}"


def case_key(row):
    return (
        row.get("_benchmark", ""),
        row.get("num_agents", ""),
        row.get("seed", ""),
        row.get("track_path", ""),
        row.get("traffic_profile", ""),
    )


def dictionary_rows():
    rows = []
    for order, (field, cn, desc, dtype, shape, policy, group) in enumerate(TRACE_FIELDS, start=1):
        rows.append(
            {
                "order": order,
                "field": field,
                "name_cn": cn,
                "description": desc,
                "data_type": dtype,
                "shape": shape,
                "required_policy": policy,
                "field_group": group,
                "dimension_rule": dimension_rule(shape),
                "source_or_recompute_use": source_or_recompute_use(field),
            }
        )
    return rows


def dimension_rule(shape):
    if shape == "scalar":
        return "Exactly one scalar value per trace step."
    if shape == "ms scalar" or shape == "world units scalar":
        return "Exactly one scalar value per trace step."
    if shape == "num_agents":
        return "List length must equal the run-level num_agents value; supports 4, 5, 6, and 8 vehicles without changing schema."
    if shape == "num_agents x 3":
        return "Outer list length must equal num_agents; each action vector is [steer, gas, brake]."
    if shape == "num_agents x 2":
        return "Outer list length must equal num_agents; each position vector is [x, y]."
    return ""


def source_or_recompute_use(field):
    mapping = {
        "step": "trace integrity and finish-step recomputation",
        "reward": "environment reward provenance; not used as the primary paper endpoint",
        "total_reward": "environment reward provenance; not used as the primary paper endpoint",
        "tile_visited_count": "track progress diagnostics",
        "rank": "rank-gain and overtaking event reconstruction",
        "track_index": "progress diagnostics and event reconstruction",
        "action": "online controller behavior and case-study explanation",
        "speed": "motion diagnostics and case-study explanation",
        "compute_latency_ms": "runtime latency summary and p95 recomputation",
        "min_pair_distance": "simulation-only safety proxy audit",
        "telemetry.progress": "target progress, lap completion and overtake-event recomputation",
        "telemetry.lateral_error": "lateral quality, desirable overtaking behavior and safety proxy metrics",
        "telemetry.heading_cos": "heading-error proxy recomputation",
        "telemetry.on_grass": "grass-rate, on-track/desirable overtake and safety proxy metrics",
        "telemetry.backward": "backward-driving diagnostic",
        "positions": "GIF/case-study provenance and pair-distance diagnostics",
        "done": "termination diagnostics",
    }
    return mapping.get(field, "trace provenance")


def get_field(step, field):
    if field.startswith("telemetry."):
        telemetry = step.get("telemetry", {})
        if not isinstance(telemetry, dict):
            return None
        return telemetry.get(field.split(".", 1)[1])
    return step.get(field)


def flatten_numeric(value):
    out = []
    if isinstance(value, bool):
        return []
    if isinstance(value, (int, float)):
        number = f(value)
        return [number] if number is not None else []
    if isinstance(value, list):
        for item in value:
            out.extend(flatten_numeric(item))
    return out


def validate_value(value, dtype, shape, num_agents):
    if value is None:
        return False, "missing"
    if dtype == "boolean":
        if shape == "scalar":
            return isinstance(value, bool), "not boolean scalar"
        return isinstance(value, list) and len(value) == num_agents and all(isinstance(item, bool) for item in value), "not boolean vector"
    if dtype == "integer":
        if shape == "scalar":
            number = f(value)
            return number is not None and abs(number - round(number)) <= 1e-9, "not integer scalar"
        return isinstance(value, list) and len(value) == num_agents and all(f(item) is not None and abs(f(item) - round(f(item))) <= 1e-9 for item in value), "not integer vector"
    if dtype == "float":
        if shape in {"scalar", "ms scalar", "world units scalar"}:
            return f(value) is not None, "not numeric scalar"
        if shape == "num_agents":
            return isinstance(value, list) and len(value) == num_agents and all(f(item) is not None for item in value), "not numeric vector"
        if shape == "num_agents x 3":
            return isinstance(value, list) and len(value) == num_agents and all(isinstance(item, list) and len(item) == 3 and all(f(x) is not None for x in item) for item in value), "not num_agents x 3 numeric array"
        if shape == "num_agents x 2":
            return isinstance(value, list) and len(value) == num_agents and all(isinstance(item, list) and len(item) == 2 and all(f(x) is not None for x in item) for item in value), "not num_agents x 2 numeric array"
    return True, ""


def profile_traces(root, source_rows):
    dictionary = dictionary_rows()
    meta = {row["field"]: row for row in dictionary}
    field_stats = {
        row["field"]: {
            "field": row["field"],
            "observed_step_count": 0,
            "missing_count": 0,
            "type_or_shape_issue_count": 0,
            "numeric_count": 0,
            "numeric_min": "",
            "numeric_max": "",
            "numeric_mean": "",
            "_numeric_values": [],
        }
        for row in dictionary
    }
    run_rows = []
    issue_rows = []
    trace_lengths = Counter()
    for source_row in source_rows:
        summary_path = root / source_row["_summary_file"]
        summary = read_json(summary_path)
        trace_path = root / summary["trace_path"]
        trace = read_json(trace_path)
        num_agents = int(source_row["num_agents"])
        trace_lengths[len(trace)] += 1
        run_status = "pass"
        run_issue_count = 0
        for step_index, step in enumerate(trace, start=1):
            for field, info in meta.items():
                value = get_field(step, field)
                stat = field_stats[field]
                stat["observed_step_count"] += 1
                if value is None:
                    stat["missing_count"] += 1
                    run_status = "review_required"
                    run_issue_count += 1
                    issue_rows.append(issue(source_row, step_index, field, "missing", "Trace field is missing."))
                    continue
                ok, reason = validate_value(value, info["data_type"], info["shape"], num_agents)
                if not ok:
                    stat["type_or_shape_issue_count"] += 1
                    run_status = "review_required"
                    run_issue_count += 1
                    issue_rows.append(issue(source_row, step_index, field, "type_or_shape", reason))
                nums = flatten_numeric(value)
                stat["_numeric_values"].extend(nums)
        run_rows.append(
            {
                "run_id": run_id(source_row),
                "benchmark": source_row["_benchmark"],
                "algorithm": source_row["algorithm"],
                "num_agents": source_row["num_agents"],
                "seed": source_row["seed"],
                "trace_file": summary["trace_path"],
                "trace_length": len(trace),
                "expected_trace_length": EXPECTED_TRACE_LENGTH,
                "field_count": len(dictionary),
                "schema_issue_count": run_issue_count,
                "status": run_status,
            }
        )
    for stat in field_stats.values():
        values = stat.pop("_numeric_values")
        stat["numeric_count"] = len(values)
        if values:
            stat["numeric_min"] = min(values)
            stat["numeric_max"] = max(values)
            stat["numeric_mean"] = sum(values) / len(values)
    return dictionary, list(field_stats.values()), run_rows, issue_rows, trace_lengths


def issue(source_row, step, field, category, message):
    return {
        "run_id": run_id(source_row),
        "benchmark": source_row["_benchmark"],
        "algorithm": source_row["algorithm"],
        "num_agents": source_row["num_agents"],
        "seed": source_row["seed"],
        "step": step,
        "field": field,
        "category": category,
        "message": message,
    }


def write_figure(path_base, field_profile):
    groups = defaultdict(list)
    for row in field_profile:
        group = next(item[6] for item in TRACE_FIELDS if item[0] == row["field"])
        total = int(row["observed_step_count"] or 0)
        issues = int(row["missing_count"] or 0) + int(row["type_or_shape_issue_count"] or 0)
        groups[group].append(issues / total if total else 0.0)
    cjk = find_cjk_font()
    if cjk:
        font_manager.fontManager.addfont(cjk)
        mpl.rcParams["font.sans-serif"] = [font_manager.FontProperties(fname=cjk).get_name(), "DejaVu Sans"]
    mpl.rcParams["axes.unicode_minus"] = False
    labels = sorted(groups)
    values = [sum(groups[label]) / len(groups[label]) for label in labels]
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.barh(labels, values, color="#2a9d8f")
    ax.set_xlabel("字段缺失/类型维度问题率")
    ax.set_title("正式 trace 字段分组 schema 问题率")
    ax.set_xlim(0, max(values + [0.02]) * 1.2)
    for idx, value in enumerate(values):
        ax.text(value + 0.001, idx, f"{value:.3f}", va="center", fontsize=9)
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
    for item in [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
        "/usr/share/fonts/truetype/arphic/uming.ttc",
    ]:
        if Path(item).exists():
            return item
    return ""


def build_markdown(report):
    summary = report["summary"]
    lines = [
        "# T-ITS Trace Schema Dictionary Pack",
        "",
        "该包给出正式 240-run 在线评估 trace JSON 的字段级字典、动态车辆维度规则、字段 profile 和 schema 验证结果。它补充 run-level source data 字典，说明逐步轨迹如何支持超车事件复算、在线决策案例、GIF provenance、trace integrity 和安全代理指标审计。",
        "",
        "## Summary",
        "",
    ]
    for key, value in summary.items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Dynamic Vehicle Dimension",
            "",
            "`num_agents` 是车辆维度的唯一来源。所有 `num_agents` 字段的向量列必须在每一步等长，因此同一 schema 可以覆盖 4、5、6 和 8 车，不需要为不同车辆数重新定义 trace 结构。",
            "",
            "## Boundary",
            "",
            "该包是仿真 trace schema 与数据解释材料，不是额外在线实验，也不构成真实道路安全认证。",
            "",
            "## Key Outputs",
            "",
            "- Field dictionary: `tables/trace_field_dictionary.csv`",
            "- Field profile: `tables/trace_field_profile.csv`",
            "- Run validation rows: `tables/trace_schema_run_rows.csv`",
            "- Issue rows: `tables/trace_schema_issue_rows.csv`",
            "- Machine-readable schema: `materials/TRACE_SCHEMA_DICTIONARY.json`",
            "- Chinese figure: `figures/figure_trace_schema_cn.svg`",
            "",
            "## Regeneration Command",
            "",
            "```bash",
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_trace_schema_dictionary_pack.py --out-dir outputs/tits_dynamic_graph/tits_trace_schema_dictionary_pack",
            "```",
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Export field-level trace schema dictionary for formal T-ITS traces.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--source-csv", default=SOURCE_CSV)
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/tits_trace_schema_dictionary_pack")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    out_dir = root / args.out_dir
    materials = out_dir / "materials"
    tables = out_dir / "tables"
    figures = out_dir / "figures"
    materials.mkdir(parents=True, exist_ok=True)
    tables.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)

    source_rows = read_csv(root / args.source_csv)
    dictionary, field_profile, run_rows, issue_rows, trace_lengths = profile_traces(root, source_rows)
    cases = {case_key(row) for row in source_rows}
    status = "pass" if not issue_rows and len(source_rows) == EXPECTED_RUNS and len(cases) == EXPECTED_CASES else "review_required"
    summary = {
        "status": status,
        "source_rows": len(source_rows),
        "trace_run_count": len(run_rows),
        "trace_pass_count": sum(1 for row in run_rows if row["status"] == "pass"),
        "dictionary_field_count": len(dictionary),
        "case_count": len(cases),
        "algorithm_count": len({row["algorithm"] for row in source_rows}),
        "total_trace_steps": sum(int(row["trace_length"]) for row in run_rows),
        "trace_length_values": ";".join(f"{k}:{v}" for k, v in sorted(trace_lengths.items())),
        "schema_issue_count": len(issue_rows),
        "expected_trace_length": EXPECTED_TRACE_LENGTH,
        "supported_vehicle_counts": ";".join(sorted({row["num_agents"] for row in source_rows}, key=int)),
    }
    figure_paths = write_figure(figures / "figure_trace_schema_cn", field_profile)
    schema_json = {
        "source_csv": args.source_csv,
        "expected": {
            "runs": EXPECTED_RUNS,
            "cases": EXPECTED_CASES,
            "algorithms": EXPECTED_ALGORITHMS,
            "trace_length": EXPECTED_TRACE_LENGTH,
        },
        "fields": dictionary,
        "dynamic_dimension_rule": "Vector and matrix fields use num_agents as the runtime vehicle dimension.",
        "boundary": "Simulation trace schema only; not a real-road safety certificate.",
    }
    paths = {
        "report_md": write_text(materials / "TRACE_SCHEMA_DICTIONARY.md", build_markdown({"summary": summary})),
        "schema_json": write_json(materials / "TRACE_SCHEMA_DICTIONARY.json", schema_json),
        "field_dictionary_csv": write_csv(
            tables / "trace_field_dictionary.csv",
            dictionary,
            ["order", "field", "name_cn", "description", "data_type", "shape", "required_policy", "field_group", "dimension_rule", "source_or_recompute_use"],
        ),
        "field_profile_csv": write_csv(
            tables / "trace_field_profile.csv",
            field_profile,
            ["field", "observed_step_count", "missing_count", "type_or_shape_issue_count", "numeric_count", "numeric_min", "numeric_max", "numeric_mean"],
        ),
        "run_rows_csv": write_csv(
            tables / "trace_schema_run_rows.csv",
            run_rows,
            ["run_id", "benchmark", "algorithm", "num_agents", "seed", "trace_file", "trace_length", "expected_trace_length", "field_count", "schema_issue_count", "status"],
        ),
        "issue_rows_csv": write_csv(
            tables / "trace_schema_issue_rows.csv",
            issue_rows,
            ["run_id", "benchmark", "algorithm", "num_agents", "seed", "step", "field", "category", "message"],
        ),
        **figure_paths,
    }
    manifest = {
        "status": status,
        "out_dir": args.out_dir,
        "summary": summary,
        "paths": paths,
        "boundary": "Simulation trace schema only; not a real-road safety certificate.",
    }
    manifest_path = write_json(out_dir / "tits_trace_schema_dictionary_pack_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, "status": status, "summary": summary}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
