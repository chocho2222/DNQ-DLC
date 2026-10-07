#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path


METRIC_DEFINITIONS = [
    {
        "field": "overtake_success_rate",
        "display_name": "Overtake success",
        "category": "overtaking",
        "unit": "binary/proportion",
        "higher_is_better": "true",
        "definition": "Whether the target vehicle completes at least one valid pass from a trailing position.",
        "reporting": "Mean over runs with bootstrap 95% confidence intervals; paired sign/McNemar tests where applicable.",
    },
    {
        "field": "overtake_count",
        "display_name": "Overtake count",
        "category": "overtaking",
        "unit": "count",
        "higher_is_better": "context-dependent",
        "definition": "Number of valid overtaking events completed by the target vehicle.",
        "reporting": "Used as event-level support for success, on-track and desirable overtaking behavior rates.",
    },
    {
        "field": "on_track_overtake_rate",
        "display_name": "On-track overtaking",
        "category": "overtaking quality",
        "unit": "proportion",
        "higher_is_better": "true",
        "definition": "Fraction of overtaking events completed while satisfying the on-track quality condition.",
        "reporting": "Primary quality metric reported with bootstrap 95% confidence intervals.",
    },
    {
        "field": "elegant_overtake_rate",
        "display_name": "Desirable overtaking behavior",
        "category": "overtaking quality",
        "unit": "proportion",
        "higher_is_better": "true",
        "definition": "Fraction of overtaking events that are both valid and satisfy the stricter smooth/on-track/lateral-quality criteria used by the benchmark.",
        "reporting": "Primary quality metric reported with bootstrap 95% confidence intervals.",
    },
    {
        "field": "time_to_first_overtake",
        "display_name": "Time to first overtake",
        "category": "efficiency",
        "unit": "simulator steps",
        "higher_is_better": "false",
        "definition": "Environment step at which the first valid overtake is completed by the target vehicle.",
        "reporting": "Computed only for runs with a completed overtake; lower is better.",
    },
    {
        "field": "overtake_start_to_complete_time",
        "display_name": "Overtake start-to-completion time",
        "category": "efficiency",
        "unit": "simulator steps",
        "higher_is_better": "false",
        "definition": "Number of steps between entering an overtaking opportunity window and completing the pass.",
        "reporting": "Computed for runs with an overtake window and completed pass; lower is better.",
    },
    {
        "field": "target_grass_rate",
        "display_name": "Target grass rate",
        "category": "off-track risk",
        "unit": "proportion",
        "higher_is_better": "false",
        "definition": "Fraction of post-start-buffer steps in which the target vehicle is outside the track surface.",
        "reporting": "Primary off-track risk metric; lower is better.",
    },
    {
        "field": "grass_recovery_time_mean",
        "display_name": "Mean grass recovery time",
        "category": "off-track recovery",
        "unit": "simulator steps",
        "higher_is_better": "false",
        "definition": "Mean duration required to return to the track after grass/off-track excursions.",
        "reporting": "Reported with bootstrap 95% confidence intervals when excursions occur.",
    },
    {
        "field": "target_mean_abs_lateral",
        "display_name": "Mean absolute lateral deviation",
        "category": "trajectory quality",
        "unit": "track-relative distance",
        "higher_is_better": "false",
        "definition": "Mean absolute lateral deviation of the target vehicle from the local track centerline.",
        "reporting": "Lower values indicate more centered driving.",
    },
    {
        "field": "target_heading_error_mean_rad",
        "display_name": "Mean heading error",
        "category": "trajectory quality",
        "unit": "radians",
        "higher_is_better": "false",
        "definition": "Mean absolute heading mismatch between the target vehicle and the local track direction.",
        "reporting": "Used as supporting trajectory-quality evidence.",
    },
    {
        "field": "collision_or_contact_proxy",
        "display_name": "Close-contact proxy",
        "category": "safety proxy",
        "unit": "proportion",
        "higher_is_better": "false",
        "definition": "Fraction or indicator derived from close vehicle spacing after the start buffer, used as a lightweight contact-risk proxy.",
        "reporting": "Supplementary safety proxy, not a certified collision metric.",
    },
    {
        "field": "rank_gain",
        "display_name": "Rank gain",
        "category": "race outcome",
        "unit": "rank positions",
        "higher_is_better": "true",
        "definition": "Improvement from the target vehicle's initial last-grid position to its final rank.",
        "reporting": "Used to distinguish overtaking performance from launch advantage.",
    },
    {
        "field": "target_completed_lap",
        "display_name": "Target completed lap",
        "category": "race outcome",
        "unit": "boolean",
        "higher_is_better": "true",
        "definition": "Whether the target vehicle completed a full lap before the episode termination condition.",
        "reporting": "Supporting completion metric; benchmark termination is controlled by the evaluation command.",
    },
    {
        "field": "compute_latency_ms",
        "display_name": "Mean online decision latency",
        "category": "runtime",
        "unit": "milliseconds",
        "higher_is_better": "false",
        "definition": "Mean wall-clock time spent by the evaluated algorithm to select an action online.",
        "reporting": "Reported as a runtime cost metric; lower is better.",
    },
    {
        "field": "compute_latency_p95_ms",
        "display_name": "95th-percentile decision latency",
        "category": "runtime",
        "unit": "milliseconds",
        "higher_is_better": "false",
        "definition": "95th percentile of online action-selection latency across the episode.",
        "reporting": "Reported as a tail-latency metric for real-time feasibility discussion.",
    },
]


SOURCE_FIELD_NOTES = {
    "_benchmark": "Benchmark family identifier.",
    "algorithm": "Algorithm identifier used in commands and source data.",
    "algorithm_label_cn": "Chinese display label.",
    "neighbor_selection_mode": "Runtime neighbor selection mode recorded by the evaluator.",
    "planner_horizon": "Planner rollout horizon where applicable.",
    "planner_candidates": "Number of candidate sequences evaluated where applicable.",
    "planner_risk_weight": "Risk penalty weight where applicable.",
    "planner_progress_weight": "Progress reward weight where applicable.",
    "planner_uncertainty_weight": "Uncertainty penalty weight where applicable.",
    "overtake_aware_planner": "Whether overtaking-aware candidate generation/scoring is enabled.",
    "seed": "Evaluation seed.",
    "num_agents": "Total vehicles in the episode, including the target vehicle.",
    "track_path": "Procedural or external track artifact used by the case.",
    "traffic_profile": "Background traffic policy/profile.",
    "target_final_rank": "Final rank of the target vehicle.",
    "target_progress": "Final normalized/track progress of the target vehicle.",
    "finish_step": "Episode termination step.",
    "topdown_gif": "Path to top-down GIF if generated.",
    "first_person_gif": "Path to first-person GIF if generated.",
    "_summary_file": "Per-run summary JSON used to build the source row.",
}


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


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


def write_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")
    return str(path)


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def algorithm_cards(config, confirmatory_algorithms):
    config_by_name = {item["name"]: item for item in config.get("algorithms", [])}
    rows = []
    for alg in confirmatory_algorithms:
        item = config_by_name.get(alg, {})
        rows.append(
            {
                "algorithm": alg,
                "label_cn": item.get("label_cn", ""),
                "kind": item.get("kind", ""),
                "family": classify_algorithm(alg, item),
                "model_path": item.get("model_path", ""),
                "quality_proposal_path": item.get("quality_proposal_path", ""),
                "neighbor_mode": item.get("neighbor_mode", ""),
                "neighbor_selection_mode": item.get("neighbor_selection_mode", ""),
                "max_neighbors": item.get("max_neighbors", ""),
                "overtake_aware_planner": item.get("overtake_aware_planner", ""),
                "planner_horizon": item.get("planner_horizon", ""),
                "planner_candidates": item.get("planner_candidates", ""),
                "planner_risk_weight": item.get("planner_risk_weight", ""),
                "planner_uncertainty_weight": item.get("planner_uncertainty_weight", ""),
                "description": item.get("description", ""),
                "role_in_study": role_in_study(alg),
            }
        )
    return rows


def classify_algorithm(name, item):
    kind = item.get("kind", "")
    if name.startswith("v6_runtime_dynamic_neighborhood"):
        return "proposed_dynamic_dlc"
    if name.startswith("quality_proposal"):
        return "proposed_variant"
    if name.startswith("dlc_world"):
        return "dlc_world_model_baseline"
    if name.startswith("rule"):
        return "rule_baseline"
    return kind or "other"


def role_in_study(name):
    roles = {
        "v6_runtime_dynamic_neighborhood": "Main dynamic-neighborhood DLC variant.",
        "v6_runtime_dynamic_neighborhood_safe": "Primary safety-oriented method for confirmatory evidence.",
        "quality_proposal_dlc_world_v1": "Quality-guided proposal variant.",
        "dlc_world_original": "Original DLC world-model baseline.",
        "dlc_world_balanced": "DLC world-model tuning variant.",
        "dlc_world_safety": "DLC world-model safety-weight variant.",
        "dlc_world_fast": "DLC world-model progress/latency variant.",
        "rule_expert_gate": "Strong hand-engineered rule baseline.",
    }
    return roles.get(name, "")


def benchmark_cards(case_rows):
    groups = defaultdict(list)
    for row in case_rows:
        groups[(row["benchmark"], row["track"], row["track_path"], row["num_agents"])].append(row)
    cards = []
    for (benchmark, track, track_path, num_agents), rows in sorted(groups.items()):
        seeds = sorted({int(row["seed"]) for row in rows})
        cards.append(
            {
                "benchmark": benchmark,
                "track": track,
                "track_path": track_path,
                "num_agents": int(num_agents),
                "case_count": len(rows),
                "seed_list": ",".join(str(seed) for seed in seeds),
                "traffic_profile": "slow_traffic",
                "target_start_order": "last grid position",
                "episode_max_steps": 2200,
                "finish_mode": "any",
                "primary_purpose": benchmark_purpose(benchmark, int(num_agents)),
            }
        )
    return cards


def benchmark_purpose(benchmark, num_agents):
    if benchmark == "in_distribution_procedural":
        return "In-distribution procedural-track validation within the 4-6 vehicle training/evaluation range."
    if benchmark == "vehicle_count_extrapolation":
        return "Vehicle-count extrapolation test beyond the 4-6 vehicle range."
    if benchmark == "monza_external_track":
        return "External CSV-derived track validation on the scaled Monza layout."
    return f"{benchmark} with {num_agents} vehicles."


def metric_dictionary(source_csv):
    with Path(source_csv).open(encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader)
    definition_by_field = {row["field"]: row for row in METRIC_DEFINITIONS}
    rows = []
    for field in header:
        definition = definition_by_field.get(field)
        if definition:
            rows.append(definition)
        else:
            rows.append(
                {
                    "field": field,
                    "display_name": field,
                    "category": "metadata/supporting",
                    "unit": "",
                    "higher_is_better": "",
                    "definition": SOURCE_FIELD_NOTES.get(field, "Source-data field emitted by the online evaluator."),
                    "reporting": "Recorded in source data; used for filtering, grouping, provenance, or supplementary analysis.",
                }
            )
    return rows


def benchmark_summary(case_rows):
    benchmarks = Counter(row["benchmark"] for row in case_rows)
    agents = Counter(row["num_agents"] for row in case_rows)
    tracks = Counter(row["track_path"] for row in case_rows)
    devices = Counter(row["device"] for row in case_rows)
    return {
        "case_count": len(case_rows),
        "benchmark_counts": dict(sorted(benchmarks.items())),
        "num_agent_counts": {str(k): v for k, v in sorted(agents.items(), key=lambda kv: int(kv[0]))},
        "track_counts": dict(sorted(tracks.items())),
        "device_counts": dict(sorted(devices.items())),
    }


def build_protocol_json(config, case_rows, algorithm_rows, benchmark_rows, metric_rows):
    summary = benchmark_summary(case_rows)
    return {
        "study": config.get("study"),
        "python": config.get("python"),
        "hardware": config.get("hardware", {}),
        "dynamic_graph_contract": config.get("dynamic_graph", {}),
        "confirmatory_matrix": {
            "case_count": summary["case_count"],
            "algorithm_count": len(algorithm_rows),
            "planned_algorithm_runs": summary["case_count"] * len(algorithm_rows),
            "benchmarks": summary["benchmark_counts"],
            "vehicle_counts": summary["num_agent_counts"],
            "tracks": summary["track_counts"],
            "devices": summary["device_counts"],
        },
        "fairness_controls": {
            "target_vehicle": "Only the target vehicle is controlled by the evaluated algorithm.",
            "target_start_order": "The target vehicle starts from the last grid position.",
            "background_traffic": "All algorithms use the same background traffic profile within each matched case.",
            "matched_cases": "Seed, vehicle count, track, traffic profile and command options are matched across algorithms.",
            "visual_outputs": "GIFs are generated only for representative evidence unless explicitly requested; numeric matrices use --no-gif.",
        },
        "benchmark_cards": benchmark_rows,
        "algorithm_cards": algorithm_rows,
        "metric_dictionary": metric_rows,
        "claim_boundaries": [
            "Evidence covers simulation benchmarks, not real-vehicle deployment.",
            "Vehicle-count generalization is demonstrated up to the 8-vehicle extrapolation setting included in the matrix.",
            "External-track validation currently uses one CSV-derived Monza track.",
            "Rule expert is a strong hand-engineered baseline, not a DLC world-model ablation.",
        ],
    }


def build_markdown(protocol, paths):
    lines = [
        "# Benchmark and Metric Protocol Card",
        "",
        "该材料把确认性在线矩阵的 benchmark、算法、指标和复现边界整理成独立 protocol card。它由配置文件、冻结 case commands 和 source data 表头生成，用于论文 Method、Experiment、Data Availability 和 reviewer replication。",
        "",
        "## Matrix Summary",
        "",
        f"- Study: `{protocol.get('study')}`",
        f"- Python: `{protocol.get('python')}`",
        f"- Case count: {protocol['confirmatory_matrix']['case_count']}",
        f"- Algorithm count: {protocol['confirmatory_matrix']['algorithm_count']}",
        f"- Planned algorithm-runs: {protocol['confirmatory_matrix']['planned_algorithm_runs']}",
        f"- Vehicle counts: {protocol['confirmatory_matrix']['vehicle_counts']}",
        f"- Benchmarks: {protocol['confirmatory_matrix']['benchmarks']}",
        "",
        "## Fairness Controls",
        "",
    ]
    for key, value in protocol["fairness_controls"].items():
        lines.append(f"- **{key}**: {value}")
    lines.extend(
        [
            "",
            "## Benchmark Cards",
            "",
            "| Benchmark | Track | Vehicles | Cases | Seeds | Purpose |",
            "|---|---|---:|---:|---|---|",
        ]
    )
    for row in protocol["benchmark_cards"]:
        lines.append(
            f"| {row['benchmark']} | {row['track_path']} | {row['num_agents']} | {row['case_count']} | {row['seed_list']} | {row['primary_purpose']} |"
        )
    lines.extend(
        [
            "",
            "## Algorithm Cards",
            "",
            "| Algorithm | Family | Role | Model/proposal | Key planner settings |",
            "|---|---|---|---|---|",
        ]
    )
    for row in protocol["algorithm_cards"]:
        model = row["model_path"] or "rule/no learned model"
        proposal = f"; proposal={row['quality_proposal_path']}" if row["quality_proposal_path"] else ""
        settings = f"neighbors={row['max_neighbors']}; overtake-aware={row['overtake_aware_planner']}; horizon={row['planner_horizon']}; candidates={row['planner_candidates']}"
        lines.append(f"| `{row['algorithm']}` | {row['family']} | {row['role_in_study']} | {model}{proposal} | {settings} |")
    lines.extend(
        [
            "",
            "## Primary Metric Families",
            "",
            "| Category | Fields | Direction |",
            "|---|---|---|",
        ]
    )
    category_map = defaultdict(list)
    for metric in protocol["metric_dictionary"]:
        if metric["field"] in {item["field"] for item in METRIC_DEFINITIONS}:
            category_map[metric["category"]].append(metric)
    for category, rows in sorted(category_map.items()):
        fields = ", ".join(f"`{row['field']}`" for row in rows)
        directions = sorted({row["higher_is_better"] for row in rows})
        lines.append(f"| {category} | {fields} | {', '.join(directions)} |")
    lines.extend(
        [
            "",
            "## Claim Boundaries",
            "",
        ]
    )
    for boundary in protocol["claim_boundaries"]:
        lines.append(f"- {boundary}")
    lines.extend(
        [
            "",
            "## Generated Files",
            "",
        ]
    )
    for key, path in paths.items():
        lines.append(f"- {key}: `{path}`")
    return "\n".join(lines)


def build_qa(paths, protocol, case_rows):
    required_paths = [Path(path) for path in paths.values()]
    cases_per_benchmark = protocol["confirmatory_matrix"]["benchmarks"]
    ok = (
        all(path.exists() and path.stat().st_size > 0 for path in required_paths)
        and protocol["confirmatory_matrix"]["case_count"] == len(case_rows)
        and protocol["confirmatory_matrix"]["planned_algorithm_runs"] == len(case_rows) * protocol["confirmatory_matrix"]["algorithm_count"]
        and bool(cases_per_benchmark)
    )
    return {
        "status": "pass" if ok else "check",
        "checks": {
            "all_exports_nonempty": all(path.exists() and path.stat().st_size > 0 for path in required_paths),
            "case_count_matches_case_commands": protocol["confirmatory_matrix"]["case_count"] == len(case_rows),
            "algorithm_count": protocol["confirmatory_matrix"]["algorithm_count"],
            "planned_algorithm_runs": protocol["confirmatory_matrix"]["planned_algorithm_runs"],
            "benchmark_counts": cases_per_benchmark,
            "source_metric_fields": len(protocol["metric_dictionary"]),
        },
        "reviewer_risks": [
            "Metric thresholds are implemented in evaluator code and summarized here at the field-definition level.",
            "The protocol card documents the frozen confirmatory matrix; exploratory smoke and tuning runs remain outside the formal claim.",
            "External validity remains bounded by the available procedural and Monza simulation settings.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description="Export benchmark and metric protocol cards for the T-ITS dynamic DLC package.")
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/tits_benchmark_protocol_pack")
    parser.add_argument("--config", default="configs/tits_dynamic_graph_experiments.json")
    parser.add_argument("--case-commands", default="outputs/tits_dynamic_graph/v6_confirmatory_preflight/tables/v6_confirmatory_case_commands.csv")
    parser.add_argument("--algorithm-table", default="outputs/tits_dynamic_graph/v6_confirmatory_preflight/tables/v6_confirmatory_algorithms.csv")
    parser.add_argument("--source-csv", default="outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    tables_dir = out_dir / "tables"
    materials_dir = out_dir / "materials"
    tables_dir.mkdir(parents=True, exist_ok=True)
    materials_dir.mkdir(parents=True, exist_ok=True)

    config = load_json(args.config)
    case_rows = read_csv(args.case_commands)
    algorithm_rows_raw = read_csv(args.algorithm_table)
    confirmatory_algorithms = [row.get("algorithm") or row.get("name") for row in algorithm_rows_raw]

    algorithm_rows = algorithm_cards(config, confirmatory_algorithms)
    benchmark_rows = benchmark_cards(case_rows)
    metric_rows = metric_dictionary(args.source_csv)
    protocol = build_protocol_json(config, case_rows, algorithm_rows, benchmark_rows, metric_rows)

    paths = {}
    paths["benchmark_cards_csv"] = write_csv(
        tables_dir / "benchmark_cards.csv",
        benchmark_rows,
        ["benchmark", "track", "track_path", "num_agents", "case_count", "seed_list", "traffic_profile", "target_start_order", "episode_max_steps", "finish_mode", "primary_purpose"],
    )
    paths["algorithm_cards_csv"] = write_csv(
        tables_dir / "algorithm_cards.csv",
        algorithm_rows,
        ["algorithm", "label_cn", "kind", "family", "model_path", "quality_proposal_path", "neighbor_mode", "neighbor_selection_mode", "max_neighbors", "overtake_aware_planner", "planner_horizon", "planner_candidates", "planner_risk_weight", "planner_uncertainty_weight", "description", "role_in_study"],
    )
    paths["metric_dictionary_csv"] = write_csv(
        tables_dir / "metric_dictionary.csv",
        metric_rows,
        ["field", "display_name", "category", "unit", "higher_is_better", "definition", "reporting"],
    )
    paths["protocol_json"] = write_json(materials_dir / "benchmark_metric_protocol.json", protocol)
    paths["protocol_md"] = write_text(materials_dir / "BENCHMARK_METRIC_PROTOCOL_CARD.md", build_markdown(protocol, paths))
    qa = build_qa(paths, protocol, case_rows)
    paths["qa_json"] = write_json(materials_dir / "BENCHMARK_METRIC_PROTOCOL_QA.json", qa)

    manifest = {
        "status": "complete" if qa["status"] == "pass" else "check",
        "out_dir": str(out_dir),
        "paths": paths,
        "summary": {
            "case_count": protocol["confirmatory_matrix"]["case_count"],
            "algorithm_count": protocol["confirmatory_matrix"]["algorithm_count"],
            "planned_algorithm_runs": protocol["confirmatory_matrix"]["planned_algorithm_runs"],
            "metric_field_count": len(metric_rows),
            "benchmark_card_count": len(benchmark_rows),
        },
    }
    manifest_path = write_json(out_dir / "tits_benchmark_protocol_pack_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, "status": manifest["status"], "summary": manifest["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
