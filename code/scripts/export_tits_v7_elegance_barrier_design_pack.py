#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import json
import math
from pathlib import Path


CONFIG = "configs/tits_dynamic_graph_experiments.json"
CASEWISE_MANIFEST = "outputs/tits_dynamic_graph/tits_overtake_casewise_diagnostics_pack/tits_overtake_casewise_diagnostics_pack_manifest.json"
SMOKE_SUMMARY = "outputs/tits_dynamic_graph/v7_elegance_barrier_smoke/procedural_n4_seed3/summaries/v7_elegance_barrier_dlc_world_n4_seed3.summary.json"
SOURCE_CSV = "outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv"
V7 = "v7_elegance_barrier_dlc_world"
PRIMARY = "v6_runtime_dynamic_neighborhood_safe"
BASELINE = "dlc_world_original"


def read_json(path, default=None):
    path = Path(path)
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path):
    path = Path(path)
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
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


def mean(values):
    vals = [as_float(v) for v in values]
    vals = [v for v in vals if v is not None]
    return sum(vals) / len(vals) if vals else None


def find_algorithm(config, name):
    for item in config.get("algorithms", []):
        if item.get("name") == name:
            return item
    return {}


def formal_algorithm_stats(rows, algorithm):
    subset = [row for row in rows if row.get("algorithm") == algorithm]
    return {
        "algorithm": algorithm,
        "n": len(subset),
        "overtake_success_rate": mean(row.get("overtake_success_rate") for row in subset),
        "on_track_overtake_rate": mean(row.get("on_track_overtake_rate") for row in subset),
        "elegant_overtake_rate": mean(row.get("elegant_overtake_rate") for row in subset),
        "target_grass_rate": mean(row.get("target_grass_rate") for row in subset),
        "overtake_start_to_complete_time": mean(row.get("overtake_start_to_complete_time") for row in subset),
        "compute_latency_ms": mean(row.get("compute_latency_ms") for row in subset),
    }


def build_design_rows(v7_config):
    return [
        {
            "diagnosed_failure_mode": "off_track_overtake",
            "evidence_source": "casewise diagnostics: primary off-track overtake run rate remains non-zero",
            "v7_design_response": "add explicit imagined-state grass/backward penalties through elegance_barrier",
            "config_parameter": "elegance_grass_penalty; elegance_backward_penalty",
            "configured_value": f"{v7_config.get('elegance_grass_penalty')}; {v7_config.get('elegance_backward_penalty')}",
            "expected_effect": "reduce grass-exposed overtake windows without retraining the DLC world model",
        },
        {
            "diagnosed_failure_mode": "on_track_non_elegant",
            "evidence_source": "casewise diagnostics: on-track events can still violate desirable-overtaking-behavior lateral/heading thresholds",
            "v7_design_response": "soft barrier on lateral deviation and heading quality in candidate scoring",
            "config_parameter": "elegance_lateral_limit; elegance_heading_cos_min",
            "configured_value": f"{v7_config.get('elegance_lateral_limit')}; {v7_config.get('elegance_heading_cos_min')}",
            "expected_effect": "prefer smoother in-lane passing candidates over large lateral excursions",
        },
        {
            "diagnosed_failure_mode": "unsafe_close_gap",
            "evidence_source": "overtake event windows include close-gap/contact-proxy risk checks",
            "v7_design_response": "penalize imagined states with very small forward clearance during overtaking",
            "config_parameter": "elegance_close_gap_limit; quality_close_gap_weight",
            "configured_value": f"{v7_config.get('elegance_close_gap_limit')}; {v7_config.get('quality_close_gap_weight')}",
            "expected_effect": "discourage late/abrupt passes that are only successful by rank metrics",
        },
        {
            "diagnosed_failure_mode": "fixed-size graph retraining concern",
            "evidence_source": "formal dynamic-neighborhood benchmark spans 4, 5, 6 and 8 vehicles",
            "v7_design_response": "keep runtime dynamic-neighborhood graph construction and change only planner scoring",
            "config_parameter": "neighbor_selection_mode; max_neighbors",
            "configured_value": f"{v7_config.get('neighbor_selection_mode')}; {v7_config.get('max_neighbors')}",
            "expected_effect": "preserve no-retraining vehicle-count extrapolation while targeting quality failures",
        },
    ]


def build_experiment_plan_rows():
    return [
        {
            "tier": "T0",
            "purpose": "implementation smoke",
            "case_scope": "1 case, n=4, seed=3, short horizon",
            "algorithms": V7,
            "required_output": "summary JSON records elegance_barrier=True and exports trace/table/figure",
            "claim_boundary": "engineering verification only; not a paper-scale performance claim",
        },
        {
            "tier": "T1",
            "purpose": "paired pilot",
            "case_scope": "same 30 frozen cases as formal matrix, v7 plus current primary and DLC original",
            "algorithms": f"{V7},{PRIMARY},{BASELINE}",
            "required_output": "casewise event diagnostics, timing, grass-window and desirable-overtaking-behavior-rate deltas",
            "claim_boundary": "pilot estimates only unless pre-registered as an exploratory extension",
        },
        {
            "tier": "T2",
            "purpose": "confirmatory extension",
            "case_scope": "30 frozen cases plus at least one fresh seed partition on procedural and Monza tracks",
            "algorithms": f"{V7},{PRIMARY},{BASELINE},DLC variants,rule expert",
            "required_output": "bootstrap CIs, paired sign tests, ablations for barrier terms, GIF/source-data archive",
            "claim_boundary": "eligible for paper revision only after all gates and failure cases are reported",
        },
        {
            "tier": "T3",
            "purpose": "ablation and sensitivity",
            "case_scope": "barrier weight/lateral/grass thresholds swept on held-out cases",
            "algorithms": "v7 barrier variants",
            "required_output": "Pareto curve of desirable overtaking behavior rate, grass rate, overtake time and compute latency",
            "claim_boundary": "prevents cherry-picking a single threshold setting",
        },
    ]


def build_markdown(report):
    s = report["summary"]
    lines = [
        "# V7 Elegance-Barrier DLC World-Model Design Pack",
        "",
        "该包记录从 casewise 失败诊断到下一代算法候选 `v7_elegance_barrier_dlc_world` 的设计闭环。它不是新的正式 240-run 论文结果，而是一个可复现、可审计的算法优化候选与实验计划。",
        "",
        "## Summary",
        "",
        f"- Status: `{report['status']}`",
        f"- V7 configured: {s['v7_configured']}",
        f"- Smoke available: {s['smoke_available']}",
        f"- Smoke barrier recorded: {s['smoke_barrier_recorded']}",
        f"- Formal primary desirable overtaking behavior rate: {s['formal_primary_elegant_rate']}",
        f"- Formal DLC original desirable overtaking behavior rate: {s['formal_baseline_elegant_rate']}",
        f"- Casewise primary off-track run rate: {s['casewise_primary_offtrack_run_rate']}",
        f"- Casewise DLC off-track run rate: {s['casewise_baseline_offtrack_run_rate']}",
        "",
        "## Algorithmic Change",
        "",
        "- 保持 DLC world model 权重不变，不重新训练模型。",
        "- 保持 runtime dynamic-neighborhood graph 构建不变，用于不同车辆数量下的局部交互建图。",
        "- 在 imagined candidate scoring 中新增 `elegance_barrier`，对草地、倒车、大横向偏移、低航向质量和近距离超车施加 soft penalty。",
        "- 该 barrier 默认关闭；只有配置中显式 `elegance_barrier=true` 的算法使用，因此不会改变已有 baseline 或冻结主方法。",
        "",
        "## Evidence Boundary",
        "",
        "- T0 smoke 只证明实现链路可运行、参数可记录、输出可复现。",
        "- 任何“v7 优于 v6-safe”的结论必须来自后续 T1/T2 paired online benchmark，不应从单 case smoke 推断。",
        "- 正式论文主结果仍以当前 240-run frozen source data 为准，除非重新冻结扩展矩阵。",
        "",
        "## Key Files",
        "",
        "- Design table: `tables/v7_failure_to_design_map.csv`",
        "- Experiment plan: `tables/v7_confirmatory_experiment_plan.csv`",
        "- Smoke summary: `materials/V7_ELEGANCE_BARRIER_SMOKE_SUMMARY.json`",
        "",
        "## Regeneration",
        "",
        "```bash",
        "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_v7_elegance_barrier_design_pack.py --out-dir outputs/tits_dynamic_graph/tits_v7_elegance_barrier_design_pack",
        "```",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Export the V7 desirable behavior-barrier design and validation plan.")
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/tits_v7_elegance_barrier_design_pack")
    args = parser.parse_args()

    root = Path.cwd()
    out_dir = root / args.out_dir
    tables = out_dir / "tables"
    materials = out_dir / "materials"
    tables.mkdir(parents=True, exist_ok=True)
    materials.mkdir(parents=True, exist_ok=True)

    config = read_json(root / CONFIG, {})
    v7_config = find_algorithm(config, V7)
    casewise = read_json(root / CASEWISE_MANIFEST, {})
    smoke = read_json(root / SMOKE_SUMMARY, {})
    source_rows = read_csv(root / SOURCE_CSV)
    primary_stats = formal_algorithm_stats(source_rows, PRIMARY)
    baseline_stats = formal_algorithm_stats(source_rows, BASELINE)
    design_rows = build_design_rows(v7_config)
    plan_rows = build_experiment_plan_rows()
    casewise_summary = casewise.get("summary", {})
    smoke_barrier_recorded = smoke.get("elegance_barrier") is True
    status = "pass" if v7_config and smoke_barrier_recorded else "review_required"
    summary = {
        "status": status,
        "v7_configured": bool(v7_config),
        "smoke_available": bool(smoke),
        "smoke_barrier_recorded": bool(smoke_barrier_recorded),
        "smoke_overtake_count": smoke.get("overtake_count"),
        "smoke_target_grass_rate": smoke.get("target_grass_rate"),
        "smoke_compute_latency_ms": smoke.get("compute_latency_ms"),
        "formal_primary_elegant_rate": primary_stats["elegant_overtake_rate"],
        "formal_baseline_elegant_rate": baseline_stats["elegant_overtake_rate"],
        "casewise_primary_offtrack_run_rate": casewise_summary.get("primary_offtrack_run_rate"),
        "casewise_baseline_offtrack_run_rate": casewise_summary.get("baseline_offtrack_run_rate"),
        "source_rows": len(source_rows),
    }
    report = {
        "status": status,
        "summary": summary,
        "v7_config": v7_config,
        "formal_primary_stats": primary_stats,
        "formal_baseline_stats": baseline_stats,
        "smoke_summary": smoke,
        "boundary": "Design and smoke-validation pack only; formal performance claims require a paired online benchmark extension.",
    }
    paths = {
        "failure_to_design_csv": write_csv(
            tables / "v7_failure_to_design_map.csv",
            design_rows,
            ["diagnosed_failure_mode", "evidence_source", "v7_design_response", "config_parameter", "configured_value", "expected_effect"],
        ),
        "experiment_plan_csv": write_csv(
            tables / "v7_confirmatory_experiment_plan.csv",
            plan_rows,
            ["tier", "purpose", "case_scope", "algorithms", "required_output", "claim_boundary"],
        ),
        "smoke_summary_json": write_json(materials / "V7_ELEGANCE_BARRIER_SMOKE_SUMMARY.json", smoke),
    }
    report["paths"] = paths
    paths["report_json"] = write_json(materials / "V7_ELEGANCE_BARRIER_DESIGN_REPORT.json", report)
    paths["report_md"] = write_text(materials / "V7_ELEGANCE_BARRIER_DESIGN_REPORT.md", build_markdown(report))
    manifest = {
        "status": status,
        "out_dir": args.out_dir,
        "summary": summary,
        "paths": paths,
        "boundary": report["boundary"],
    }
    manifest_path = write_json(out_dir / "tits_v7_elegance_barrier_design_pack_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, "status": status, "summary": summary}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
