#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import json
from pathlib import Path


REQUIRED_ALGORITHMS = [
    "ours_dynamic_graph_dlc_world",
    "ours_no_overtake_aware_planner",
    "dlc_world_original",
    "dlc_world_balanced",
    "dlc_world_safety",
    "dlc_world_fast",
    "graph_bc_dynamic",
    "rule_expert_gate",
    "rule_adaptive_gate",
]

REQUIRED_SUMMARY_FIELDS = [
    "algorithm",
    "algorithm_label_cn",
    "algorithm_kind",
    "overtake_aware_planner",
    "seed",
    "num_agents",
    "target_agent",
    "track_path",
    "rank_gain",
    "overtake_success_rate",
    "overtake_count",
    "overtake_start_to_complete_time",
    "target_grass_rate",
    "target_mean_abs_lateral",
    "compute_latency_ms",
    "trace_path",
]

REQUIRED_SUMMARY_OUTPUTS = [
    "online_benchmark_source_data.csv",
    "online_benchmark_aggregate_statistics.csv",
    "online_benchmark_main_results.md",
]

REQUIRED_FIGURE_EXTS = ["svg", "pdf", "png", "tiff"]


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def add_check(checks, name, passed, detail):
    checks.append(
        {
            "name": name,
            "status": "PASS" if passed else "FAIL",
            "detail": detail,
        }
    )


def add_warning(checks, name, condition, detail):
    checks.append(
        {
            "name": name,
            "status": "PASS" if condition else "WARN",
            "detail": detail,
        }
    )


def existing_algorithm_names_from_eval(eval_script):
    text = Path(eval_script).read_text(encoding="utf-8")
    names = []
    for name in REQUIRED_ALGORITHMS:
        if f'"name": "{name}"' in text:
            names.append(name)
    return names


def config_algorithm_names(config):
    cfg = load_json(config)
    return [item.get("name") for item in cfg.get("algorithms", []) if item.get("name")]


def audit_config(config, checks):
    cfg = load_json(config)
    add_check(checks, "config_json_parse", True, str(config))
    reporting = cfg.get("reporting", {})
    for key in ["output_dir", "figures_dir", "tables_dir", "gifs_dir", "logs_dir"]:
        add_check(checks, f"config_reporting_{key}", key in reporting, reporting.get(key))
    matrix = cfg.get("benchmark_matrix", [])
    add_check(checks, "benchmark_matrix_nonempty", len(matrix) > 0, f"{len(matrix)} benchmark groups")
    total_cases = 0
    for item in matrix:
        total_cases += len(item.get("agent_counts", [])) * len(item.get("seeds", []))
    add_check(checks, "benchmark_case_count", total_cases >= 20, f"{total_cases} cases configured")

    algorithms = {item.get("name"): item for item in cfg.get("algorithms", [])}
    missing_config_algorithms = [name for name in REQUIRED_ALGORITHMS if name not in algorithms]
    add_check(
        checks,
        "config_algorithm_coverage",
        not missing_config_algorithms,
        {"observed": sorted(str(name) for name in algorithms), "missing": missing_config_algorithms},
    )
    for name in ["ours_dynamic_graph_dlc_world", "ours_no_overtake_aware_planner"]:
        add_check(checks, f"config_has_{name}", name in algorithms, algorithms.get(name, {}))
    if "ours_dynamic_graph_dlc_world" in algorithms:
        add_check(
            checks,
            "ours_overtake_planner_enabled",
            algorithms["ours_dynamic_graph_dlc_world"].get("overtake_aware_planner") is True,
            algorithms["ours_dynamic_graph_dlc_world"].get("overtake_aware_planner"),
        )
    if "ours_no_overtake_aware_planner" in algorithms:
        add_check(
            checks,
            "ablation_overtake_planner_disabled",
            algorithms["ours_no_overtake_aware_planner"].get("overtake_aware_planner") is False,
            algorithms["ours_no_overtake_aware_planner"].get("overtake_aware_planner"),
        )
    return cfg


def audit_models(checks):
    model_paths = {
        "ours_dynamic_graph_dlc_world": "outputs/tits_dynamic_graph/models/ours_dynamic_graph_dlc_world/graph_risk_dlc_world.graphworld.pt",
        "graph_bc_dynamic": "outputs/tits_dynamic_graph/models/graph_bc_dynamic/graph_bc.graph.pt",
        "dlc_world_original": "outputs/paper_multicar_overtake_20260618/models/graph_risk_world_model/graph_risk_dlc_world.graphworld.pt",
        "dlc_world_balanced": "outputs/paper_multicar_overtake_20260618/models/graph_risk_world_model_variants/graph_risk_dlc_world_balanced.graphworld.pt",
        "dlc_world_safety": "outputs/paper_multicar_overtake_20260618/models/graph_risk_world_model_variants/graph_risk_dlc_world_safety.graphworld.pt",
        "dlc_world_fast": "outputs/paper_multicar_overtake_20260618/models/graph_risk_world_model_variants/graph_risk_dlc_world_fast.graphworld.pt",
    }
    for name, path in model_paths.items():
        add_check(checks, f"model_exists_{name}", Path(path).exists(), path)


def audit_eval_script(eval_script, config, checks):
    names = existing_algorithm_names_from_eval(eval_script)
    config_names = config_algorithm_names(config)
    for name in REQUIRED_ALGORITHMS:
        add_check(
            checks,
            f"eval_algorithm_{name}",
            name in names or name in config_names,
            {"eval_script": str(eval_script), "in_default_list": name in names, "in_config": name in config_names},
        )


def audit_online_outputs(input_dir, checks):
    input_dir = Path(input_dir)
    summaries = sorted(input_dir.glob("**/summaries/*.summary.json"))
    add_check(checks, "online_summary_files_exist", len(summaries) > 0, f"{len(summaries)} files under {input_dir}")
    missing_by_file = {}
    smoke_like = 0
    formal_like = 0
    planner_values = {}
    algorithms = set()
    cases = set()
    formal_cases = set()
    for path in summaries:
        data = load_json(path)
        algorithm = data.get("algorithm")
        algorithms.add(algorithm)
        case = (data.get("_benchmark"), data.get("track_path"), data.get("num_agents"), data.get("seed"))
        cases.add(case)
        missing = [field for field in REQUIRED_SUMMARY_FIELDS if field not in data]
        if missing:
            missing_by_file[str(path)] = missing
        if int(data.get("steps_run", 0)) < 500:
            smoke_like += 1
        else:
            formal_like += 1
            formal_cases.add(case)
        planner_values.setdefault(algorithm, set()).add(data.get("overtake_aware_planner"))
    add_check(checks, "summary_required_fields", not missing_by_file, missing_by_file)
    add_check(checks, "smoke_formal_boundary_recorded", True, f"smoke_like={smoke_like}, formal_like={formal_like}")
    add_warning(
        checks,
        "formal_length_outputs_present",
        formal_like > 0,
        f"formal_like={formal_like}; outputs with steps_run < 500 are smoke/pipeline checks only",
    )
    add_warning(
        checks,
        "formal_case_coverage",
        len(formal_cases) >= 20,
        f"formal_cases={len(formal_cases)}; configured TITS benchmark expects broad multi-seed/multi-track coverage",
    )
    missing_algorithms = [name for name in REQUIRED_ALGORITHMS if name not in algorithms]
    add_warning(
        checks,
        "online_algorithm_coverage",
        not missing_algorithms,
        {"observed": sorted(str(item) for item in algorithms), "missing": missing_algorithms},
    )
    if "ours_dynamic_graph_dlc_world" in planner_values:
        add_check(checks, "summary_ours_planner_true", True in planner_values["ours_dynamic_graph_dlc_world"], sorted(map(str, planner_values["ours_dynamic_graph_dlc_world"])))
    if "ours_no_overtake_aware_planner" in planner_values:
        add_check(checks, "summary_ablation_planner_false", False in planner_values["ours_no_overtake_aware_planner"], sorted(map(str, planner_values["ours_no_overtake_aware_planner"])))
    if "dlc_world_original" in planner_values:
        add_check(checks, "summary_dlc_planner_false", planner_values["dlc_world_original"] <= {False, None}, sorted(map(str, planner_values["dlc_world_original"])))


def audit_summary_outputs(summary_dir, checks):
    summary_dir = Path(summary_dir)
    tables_dir = summary_dir / "tables"
    figures_dir = summary_dir / "figures"
    for filename in REQUIRED_SUMMARY_OUTPUTS:
        add_check(checks, f"summary_output_{filename}", (tables_dir / filename).exists(), str(tables_dir / filename))
    source_csv = tables_dir / "online_benchmark_source_data.csv"
    if source_csv.exists():
        with source_csv.open(encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            fields = reader.fieldnames or []
        add_check(checks, "source_data_has_planner_field", "overtake_aware_planner" in fields, fields)
    for ext in REQUIRED_FIGURE_EXTS:
        path = figures_dir / f"figure_tits_online_benchmark_summary.{ext}"
        add_check(checks, f"summary_figure_{ext}", path.exists(), str(path))


def main():
    parser = argparse.ArgumentParser(description="Audit readiness of dynamic graph DLC world-model experiments.")
    parser.add_argument("--config", default="configs/tits_dynamic_graph_experiments.json")
    parser.add_argument("--eval-script", default="scripts/run_tits_dynamic_graph_evaluation.py")
    parser.add_argument("--online-dir", default="outputs/tits_dynamic_graph/online_evaluation_matrix")
    parser.add_argument("--summary-dir", default="outputs/tits_dynamic_graph/online_evaluation_matrix_summary")
    parser.add_argument("--out", default="outputs/tits_dynamic_graph/tits_readiness_audit.json")
    args = parser.parse_args()

    checks = []
    audit_config(Path(args.config), checks)
    audit_models(checks)
    audit_eval_script(Path(args.eval_script), Path(args.config), checks)
    audit_online_outputs(args.online_dir, checks)
    audit_summary_outputs(args.summary_dir, checks)
    failed = [item for item in checks if item["status"] == "FAIL"]
    warnings = [item for item in checks if item["status"] == "WARN"]
    result = {
        "status": "FAIL" if failed else "WARN" if warnings else "PASS",
        "checks": checks,
        "failed": failed,
        "warnings": warnings,
        "note": "短步数 smoke 只能验证链路；正式论文结论必须使用完整训练和完整 benchmark 输出。",
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": result["status"], "out": str(out), "failed": len(failed), "warnings": len(warnings)}, ensure_ascii=False, indent=2))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
