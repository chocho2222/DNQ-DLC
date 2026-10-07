#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import json
from pathlib import Path


EXPLORATORY_KEYWORDS = [
    "smoke",
    "optimization_checks",
    "quality_aux",
    "quality_guided",
    "quality_metric_checks",
    "quality_proposal_dlc_v2",
    "v6_planner_budget",
    "online_evaluation_matrix_quality",
    "partial_summary",
]

FORMAL_SOURCE_CSV = "outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv"
CASE_COMMANDS_CSV = "outputs/tits_dynamic_graph/v6_confirmatory_preflight/tables/v6_confirmatory_case_commands.csv"
BENCHMARK_CARDS_CSV = "outputs/tits_dynamic_graph/tits_benchmark_protocol_pack/tables/benchmark_cards.csv"
ALGORITHM_CARDS_CSV = "outputs/tits_dynamic_graph/tits_benchmark_protocol_pack/tables/algorithm_cards.csv"
RELEASE_DIR_PLAN_CSV = "outputs/tits_dynamic_graph/public_release_plan/public_release_directory_plan.csv"
CROSSREF_MANIFEST = "outputs/tits_dynamic_graph/tits_cross_reference_audit/tits_cross_reference_audit_manifest.json"
BASELINE_FAIRNESS_MANIFEST = "outputs/tits_dynamic_graph/tits_baseline_fairness_audit/tits_baseline_fairness_audit_manifest.json"
CONFIG_JSON = "configs/tits_dynamic_graph_experiments.json"
TRAIN_SUMMARY_JSON = "outputs/tits_dynamic_graph/train_summary.json"


def read_json(path):
    path = Path(path)
    if not path.exists():
        return {}
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


def classify_case(row, train_range):
    n = int(row.get("num_agents", 0) or 0)
    benchmark = row.get("benchmark", "")
    track_path = row.get("track_path", "")
    in_train_vehicle_range = train_range[0] <= n <= train_range[1] if len(train_range) == 2 else False
    external_track = track_path not in {"", "procedural"} and benchmark == "monza_external_track"
    vehicle_extrapolation = n > train_range[1] if len(train_range) == 2 else benchmark == "vehicle_count_extrapolation"
    if external_track:
        split_role = "external_track_validation"
    elif vehicle_extrapolation:
        split_role = "vehicle_count_extrapolation"
    elif in_train_vehicle_range:
        split_role = "in_distribution_vehicle_count_validation"
    else:
        split_role = "other_validation"
    return split_role, in_train_vehicle_range, external_track, vehicle_extrapolation


def build_case_rows(case_rows, source_rows, train_range):
    source_case_keys = set()
    for row in source_rows:
        key = (
            row.get("_benchmark", ""),
            row.get("num_agents", ""),
            row.get("seed", ""),
            row.get("track_path", ""),
            row.get("traffic_profile", ""),
        )
        source_case_keys.add(key)
    out = []
    for row in case_rows:
        split_role, in_range, external, extrap = classify_case(row, train_range)
        key = (
            row.get("benchmark", ""),
            row.get("num_agents", ""),
            row.get("seed", ""),
            row.get("track_path", ""),
            "slow_traffic",
        )
        out.append(
            {
                "case_id": row.get("case_id", ""),
                "benchmark": row.get("benchmark", ""),
                "track_path": row.get("track_path", ""),
                "num_agents": row.get("num_agents", ""),
                "seed": row.get("seed", ""),
                "split_role": split_role,
                "in_train_vehicle_range": in_range,
                "external_track": external,
                "vehicle_count_extrapolation": extrap,
                "source_data_present": key in source_case_keys,
                "command_out_dir": row.get("out_dir", ""),
            }
        )
    return out


def build_algorithm_rows(algorithm_rows, config):
    formal_algorithms = {
        "v6_runtime_dynamic_neighborhood",
        "v6_runtime_dynamic_neighborhood_safe",
        "quality_proposal_dlc_world_v1",
        "dlc_world_original",
        "dlc_world_balanced",
        "dlc_world_safety",
        "dlc_world_fast",
        "rule_expert_gate",
    }
    config_algorithms = {item.get("name"): item for item in config.get("algorithms", [])}
    out = []
    for row in algorithm_rows:
        algorithm = row.get("algorithm", "")
        cfg = config_algorithms.get(algorithm, {})
        model_path = row.get("model_path", "")
        quality_path = row.get("quality_proposal_path", "")
        out.append(
            {
                "algorithm": algorithm,
                "family": row.get("family", ""),
                "formal_confirmatory_algorithm": algorithm in formal_algorithms,
                "model_path": model_path,
                "quality_proposal_path": quality_path,
                "uses_current_dynamic_world_model": model_path.startswith("outputs/tits_dynamic_graph/models/ours_dynamic_graph_dlc_world"),
                "uses_historical_dlc_baseline_weight": model_path.startswith("outputs/paper_multicar_overtake_20260618/models"),
                "uses_quality_proposal": bool(quality_path),
                "config_declared": bool(cfg),
                "role_in_study": row.get("role_in_study", ""),
            }
        )
    return out


def build_exploratory_rows(root, dir_plan_rows):
    rows = []
    for row in dir_plan_rows:
        path = row.get("path", "")
        if not path.startswith("outputs/tits_dynamic_graph/"):
            continue
        name = Path(path).name
        keyword_hits = [key for key in EXPLORATORY_KEYWORDS if key in path]
        if not keyword_hits:
            continue
        rows.append(
            {
                "path": path,
                "release_role": row.get("release_role", ""),
                "recommended_action": row.get("recommended_action", ""),
                "keyword_hits": ";".join(keyword_hits),
                "formal_result_allowed": row.get("release_role") in {"mandatory_data_archive"},
                "boundary_interpretation": "exploratory_or_superseded; do not cite as formal result unless explicitly marked",
            }
        )
    return rows


def build_train_rows(train_summary):
    rows = []
    for item in train_summary.get("commands", []):
        command = item.get("command", [])
        out_dir = ""
        if "--out-dir" in command:
            idx = command.index("--out-dir")
            if idx + 1 < len(command):
                out_dir = command[idx + 1]
        rows.append(
            {
                "name": item.get("name", ""),
                "out_dir": out_dir,
                "command_text": item.get("command_text", ""),
                "overlaps_confirmatory_output": out_dir.startswith("outputs/tits_dynamic_graph/v6_confirmatory_matrix"),
                "declared_training_role": "training_or_model_collection",
            }
        )
    return rows


def summarize(case_rows, source_rows, algorithm_rows, exploratory_rows, train_rows, config, crossref, baseline_fairness):
    train_range = config.get("dynamic_graph", {}).get("train_agent_range", [])
    role_counts = {}
    for row in case_rows:
        role_counts[row["split_role"]] = role_counts.get(row["split_role"], 0) + 1
    formal_summary_paths_ok = all(
        (row.get("_summary_file", "").startswith("outputs/tits_dynamic_graph/v6_confirmatory_matrix/"))
        for row in source_rows
    )
    exploratory_as_formal = [
        row for row in exploratory_rows
        if row["formal_result_allowed"] and any(key not in {"tits_runtime_scalability_pack"} for key in row["keyword_hits"].split(";"))
    ]
    train_output_overlap = [row for row in train_rows if row["overlaps_confirmatory_output"]]
    algorithm_missing_config = [
        row for row in algorithm_rows
        if row["formal_confirmatory_algorithm"] and not row["config_declared"] and row["algorithm"] != "rule_expert_gate"
    ]
    warnings = []
    if train_range:
        warnings.append(
            "Training commands record vehicle-count range but do not archive per-episode procedural training seeds; seed-level overlap with procedural validation cannot be fully disproved from local artifacts."
        )
    warnings.append(
        "Algorithm selection used exploratory sweeps and diagnostics; those outputs are routed as excluded/local/optional provenance and should not be reported as confirmatory results."
    )
    checks = {
        "source_rows_240": len(source_rows) == 240,
        "case_commands_30": len(case_rows) == 30,
        "formal_summary_paths_under_confirmatory_matrix": formal_summary_paths_ok,
        "train_outputs_do_not_overlap_confirmatory_outputs": not train_output_overlap,
        "baseline_fairness_pass": baseline_fairness.get("status") == "pass",
        "cross_reference_pass": crossref.get("status") == "pass",
        "formal_algorithms_have_config_or_rule_definition": not algorithm_missing_config,
        "external_track_cases_present": role_counts.get("external_track_validation", 0) == 10,
        "vehicle_extrapolation_cases_present": role_counts.get("vehicle_count_extrapolation", 0) == 5,
        "in_distribution_cases_present": role_counts.get("in_distribution_vehicle_count_validation", 0) == 15,
    }
    return {
        "status": "pass" if all(checks.values()) else "review_required",
        "checks": checks,
        "warning_count": len(warnings),
        "warnings": warnings,
        "train_agent_range": train_range,
        "source_rows": len(source_rows),
        "case_command_rows": len(case_rows),
        "algorithm_rows": len(algorithm_rows),
        "case_role_counts": role_counts,
        "exploratory_directory_rows": len(exploratory_rows),
        "exploratory_as_formal_count": len(exploratory_as_formal),
        "train_output_overlap_count": len(train_output_overlap),
        "algorithm_missing_config_count": len(algorithm_missing_config),
    }


def build_markdown(summary, case_rows, algorithm_rows, train_rows, exploratory_rows):
    lines = [
        "# T-ITS Data Leakage and Tuning-Provenance Audit",
        "",
        "该审计把训练命令、冻结确认性矩阵、探索性调参输出、正式算法卡和发布分流规则放在同一张 provenance 视图中。目标是防止把调参/探索结果当作正式结果，也明确哪些泛化 claim 是当前证据能支持的，哪些仍是限制。",
        "",
        "## Summary",
        "",
    ]
    for key, value in summary.items():
        if key in {"checks", "warnings"}:
            continue
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Checks", ""])
    for key, value in summary["checks"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Warnings / Boundaries", ""])
    for item in summary["warnings"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Case Split Summary",
            "",
            "| Split role | Cases | Interpretation |",
            "|---|---:|---|",
        ]
    )
    interpretations = {
        "in_distribution_vehicle_count_validation": "Procedural validation within the trained 4-6 vehicle-count range; not a claim of unseen-road generalization.",
        "vehicle_count_extrapolation": "8-vehicle online evaluation beyond the trained 4-6 vehicle-count range.",
        "external_track_validation": "Monza CSV-derived track validation; bounded external-track evidence, not arbitrary road-geometry proof.",
    }
    for role, count in sorted(summary["case_role_counts"].items()):
        lines.append(f"| {role} | {count} | {interpretations.get(role, '')} |")
    lines.extend(
        [
            "",
            "## Training Output Boundary",
            "",
            "| Training command | Output directory | Overlaps confirmatory matrix |",
            "|---|---|---:|",
        ]
    )
    for row in train_rows:
        lines.append(f"| {row['name']} | `{row['out_dir']}` | {row['overlaps_confirmatory_output']} |")
    lines.extend(
        [
            "",
            "## Formal Algorithm Boundary",
            "",
            "| Algorithm | Family | Formal | Model source | Quality proposal |",
            "|---|---|---:|---|---|",
        ]
    )
    for row in algorithm_rows:
        lines.append(
            f"| {row['algorithm']} | {row['family']} | {row['formal_confirmatory_algorithm']} | "
            f"`{row['model_path']}` | `{row['quality_proposal_path']}` |"
        )
    lines.extend(
        [
            "",
            "## Exploratory Output Boundary",
            "",
            f"- Exploratory/smoke/tuning directories detected: {len(exploratory_rows)}",
            "- These directories are retained as provenance but should not be cited as confirmatory evidence unless explicitly routed through the formal matrix, evidence pack, or a dedicated audit.",
            "- The formal source data remain `outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv`.",
            "",
            "## Recommended Manuscript Wording",
            "",
            "- Use: The confirmatory matrix evaluates 30 matched cases and 240 algorithm-runs, including procedural 4/5/6-vehicle cases, 8-vehicle extrapolation, and a Monza CSV-derived external track.",
            "- Use: Historical sweeps and smoke checks informed development but are not reported as confirmatory results.",
            "- Avoid: The training and validation sets are provably seed-disjoint at every procedural episode, because the local training logs do not archive all generated training episode seeds.",
            "- Avoid: The method generalizes to arbitrary road geometry or arbitrary traffic density.",
            "",
            "## Regeneration Command",
            "",
            "```bash",
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_data_leakage_tuning_audit.py --out-dir outputs/tits_dynamic_graph/tits_data_leakage_tuning_audit",
            "```",
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Audit data leakage and tuning provenance boundaries for the T-ITS dynamic DLC package.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/tits_data_leakage_tuning_audit")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    out_dir = root / args.out_dir
    materials = out_dir / "materials"
    tables = out_dir / "tables"
    materials.mkdir(parents=True, exist_ok=True)
    tables.mkdir(parents=True, exist_ok=True)

    config = read_json(root / CONFIG_JSON)
    train_summary = read_json(root / TRAIN_SUMMARY_JSON)
    source_rows = read_csv(root / FORMAL_SOURCE_CSV)
    case_commands = read_csv(root / CASE_COMMANDS_CSV)
    benchmark_cards = read_csv(root / BENCHMARK_CARDS_CSV)
    algorithm_cards = read_csv(root / ALGORITHM_CARDS_CSV)
    dir_plan = read_csv(root / RELEASE_DIR_PLAN_CSV)
    crossref = read_json(root / CROSSREF_MANIFEST)
    baseline_fairness = read_json(root / BASELINE_FAIRNESS_MANIFEST)

    train_range = config.get("dynamic_graph", {}).get("train_agent_range", [])
    case_rows = build_case_rows(case_commands, source_rows, train_range)
    algorithm_rows = build_algorithm_rows(algorithm_cards, config)
    exploratory_rows = build_exploratory_rows(root, dir_plan)
    train_rows = build_train_rows(train_summary)
    summary = summarize(case_rows, source_rows, algorithm_rows, exploratory_rows, train_rows, config, crossref, baseline_fairness)

    paths = {
        "audit_md": write_text(materials / "DATA_LEAKAGE_AND_TUNING_PROVENANCE_AUDIT.md", build_markdown(summary, case_rows, algorithm_rows, train_rows, exploratory_rows)),
        "audit_json": write_json(materials / "DATA_LEAKAGE_AND_TUNING_PROVENANCE_AUDIT.json", {"summary": summary}),
        "qa_json": write_json(
            materials / "DATA_LEAKAGE_TUNING_QA.json",
            {
                "status": summary["status"],
                "checks": summary["checks"],
                "warnings": summary["warnings"],
            },
        ),
        "case_split_csv": write_csv(
            tables / "case_split_boundary.csv",
            case_rows,
            [
                "case_id",
                "benchmark",
                "track_path",
                "num_agents",
                "seed",
                "split_role",
                "in_train_vehicle_range",
                "external_track",
                "vehicle_count_extrapolation",
                "source_data_present",
                "command_out_dir",
            ],
        ),
        "algorithm_boundary_csv": write_csv(
            tables / "algorithm_training_boundary.csv",
            algorithm_rows,
            [
                "algorithm",
                "family",
                "formal_confirmatory_algorithm",
                "model_path",
                "quality_proposal_path",
                "uses_current_dynamic_world_model",
                "uses_historical_dlc_baseline_weight",
                "uses_quality_proposal",
                "config_declared",
                "role_in_study",
            ],
        ),
        "train_boundary_csv": write_csv(
            tables / "training_command_boundary.csv",
            train_rows,
            ["name", "out_dir", "command_text", "overlaps_confirmatory_output", "declared_training_role"],
        ),
        "exploratory_boundary_csv": write_csv(
            tables / "exploratory_output_boundary.csv",
            exploratory_rows,
            ["path", "release_role", "recommended_action", "keyword_hits", "formal_result_allowed", "boundary_interpretation"],
        ),
        "benchmark_cards_snapshot_csv": write_csv(
            tables / "benchmark_cards_snapshot.csv",
            benchmark_cards,
            ["benchmark", "track", "track_path", "num_agents", "case_count", "seed_list", "traffic_profile", "target_start_order", "episode_max_steps", "finish_mode", "primary_purpose"],
        ),
    }
    manifest = {
        "status": summary["status"],
        "out_dir": args.out_dir,
        "summary": summary,
        "paths": paths,
        "note": "This audit documents leakage and tuning-provenance boundaries from available local artifacts; it does not prove unseen procedural seed disjointness beyond the recorded evidence.",
    }
    manifest_path = write_json(out_dir / "tits_data_leakage_tuning_audit_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, "status": summary["status"], "summary": summary}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
