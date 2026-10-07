#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import json
import shlex
from collections import defaultdict
from pathlib import Path


CONFIG_PATH = "configs/tits_dynamic_graph_experiments.json"
ALGORITHM_CARDS = "outputs/tits_dynamic_graph/tits_benchmark_protocol_pack/tables/algorithm_cards.csv"
SOURCE_CSV = "outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv"
CASE_COMMANDS = "outputs/tits_dynamic_graph/v6_confirmatory_preflight/tables/v6_confirmatory_case_commands.csv"

FORMAL_ALGORITHMS = [
    "v6_runtime_dynamic_neighborhood",
    "v6_runtime_dynamic_neighborhood_safe",
    "quality_proposal_dlc_world_v1",
    "dlc_world_original",
    "dlc_world_balanced",
    "dlc_world_safety",
    "dlc_world_fast",
    "rule_expert_gate",
]

CONFIG_FIELDS = [
    "kind",
    "label_cn",
    "model_path",
    "quality_proposal_path",
    "neighbor_mode",
    "neighbor_selection_mode",
    "max_neighbors",
    "overtake_aware_planner",
    "planner_horizon",
    "planner_candidates",
    "planner_risk_weight",
    "planner_progress_weight",
    "planner_uncertainty_weight",
    "quality_planner_mode",
    "quality_rollout_blend",
    "quality_overtake_weight",
    "quality_lane_weight",
    "quality_grass_weight",
    "quality_close_gap_weight",
    "learned_quality_weight",
]

SOURCE_CONFIG_FIELDS = [
    "algorithm_label_cn",
    "neighbor_selection_mode",
    "planner_horizon",
    "planner_candidates",
    "planner_risk_weight",
    "planner_progress_weight",
    "planner_uncertainty_weight",
    "overtake_aware_planner",
]

CARD_FIELDS = [
    "label_cn",
    "kind",
    "family",
    "model_path",
    "quality_proposal_path",
    "neighbor_mode",
    "neighbor_selection_mode",
    "max_neighbors",
    "overtake_aware_planner",
    "planner_horizon",
    "planner_candidates",
    "planner_risk_weight",
    "planner_uncertainty_weight",
    "description",
    "role_in_study",
]


def read_json(path):
    path = Path(path)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path):
    path = Path(path)
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


def normalize(value):
    if value is None:
        return ""
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return f"{value:.12g}"
    return str(value).strip()


def parse_flags(command):
    tokens = shlex.split(command)
    flags = {}
    idx = 0
    while idx < len(tokens):
        token = tokens[idx]
        if token.startswith("--"):
            key = token[2:]
            if idx + 1 < len(tokens) and not tokens[idx + 1].startswith("--"):
                flags[key] = tokens[idx + 1]
                idx += 2
            else:
                flags[key] = True
                idx += 1
        else:
            idx += 1
    return flags


def formal_config_algorithms(config):
    algorithms = {row.get("name"): row for row in config.get("algorithms", []) if row.get("name")}
    return {name: algorithms.get(name, {}) for name in FORMAL_ALGORITHMS}


def build_algorithm_rows(config_algorithms, cards, source_rows):
    cards_by_name = {row["algorithm"]: row for row in cards}
    source_by_algorithm = defaultdict(list)
    for row in source_rows:
        source_by_algorithm[row["algorithm"]].append(row)

    rows = []
    for name in FORMAL_ALGORITHMS:
        config_row = config_algorithms.get(name, {})
        card_row = cards_by_name.get(name, {})
        alg_source = source_by_algorithm.get(name, [])
        errors = []
        warnings = []

        if not config_row:
            errors.append("missing_in_config")
        if not card_row:
            errors.append("missing_in_algorithm_cards")
        if len(alg_source) != 30:
            errors.append(f"source_rows_expected_30_observed_{len(alg_source)}")

        for config_field, card_field in [
            ("label_cn", "label_cn"),
            ("kind", "kind"),
            ("model_path", "model_path"),
            ("quality_proposal_path", "quality_proposal_path"),
            ("neighbor_mode", "neighbor_mode"),
            ("neighbor_selection_mode", "neighbor_selection_mode"),
            ("max_neighbors", "max_neighbors"),
            ("overtake_aware_planner", "overtake_aware_planner"),
            ("planner_horizon", "planner_horizon"),
            ("planner_candidates", "planner_candidates"),
            ("planner_risk_weight", "planner_risk_weight"),
            ("planner_uncertainty_weight", "planner_uncertainty_weight"),
        ]:
            left = normalize(config_row.get(config_field, ""))
            right = normalize(card_row.get(card_field, ""))
            if left or right:
                if left != right:
                    errors.append(f"config_card_mismatch_{config_field}")

        unique_source = {
            field: sorted({normalize(row.get(field, "")) for row in alg_source})
            for field in SOURCE_CONFIG_FIELDS
        }
        if len(unique_source["algorithm_label_cn"]) == 1:
            config_label = normalize(config_row.get("label_cn", ""))
            source_label = unique_source["algorithm_label_cn"][0]
            if config_label and source_label and config_label != source_label:
                errors.append("source_label_mismatch")
        for field in SOURCE_CONFIG_FIELDS:
            if len(unique_source[field]) > 1:
                errors.append(f"source_field_not_constant_{field}")

        source_neighbor = unique_source["neighbor_selection_mode"][0] if len(unique_source["neighbor_selection_mode"]) == 1 else ""
        config_neighbor = normalize(config_row.get("neighbor_selection_mode", ""))
        if config_neighbor and source_neighbor and config_neighbor != source_neighbor:
            errors.append("source_neighbor_selection_mode_mismatch")
        if name.startswith("dlc_world") and source_neighbor != "legacy":
            errors.append("dlc_world_neighbor_mode_not_legacy")
        if name.startswith("v6_runtime") and source_neighbor != "interaction":
            errors.append("v6_neighbor_mode_not_interaction")

        for field in ["planner_horizon", "planner_candidates", "planner_risk_weight", "planner_uncertainty_weight"]:
            source_value = unique_source[field][0] if len(unique_source[field]) == 1 else ""
            config_value = normalize(config_row.get(field, ""))
            if config_value or source_value:
                if config_value != source_value:
                    errors.append(f"source_config_mismatch_{field}")

        if name == "rule_expert_gate":
            if normalize(config_row.get("model_path", "")) or normalize(card_row.get("model_path", "")):
                errors.append("rule_expert_should_not_have_model_path")
        else:
            if not normalize(card_row.get("model_path", "")):
                errors.append("learned_or_dlc_algorithm_missing_model_path")

        if name == "v6_runtime_dynamic_neighborhood_safe":
            if normalize(config_row.get("planner_horizon")) != "4" or normalize(config_row.get("planner_candidates")) != "12":
                errors.append("primary_safe_planner_budget_not_frozen_expected_4x12")
            if normalize(config_row.get("planner_risk_weight")) != "1.65":
                errors.append("primary_safe_risk_weight_not_frozen_expected_1.65")

        rows.append(
            {
                "algorithm": name,
                "status": "pass" if not errors else "error",
                "errors": ";".join(errors),
                "warnings": ";".join(warnings),
                "source_run_rows": len(alg_source),
                "config_present": bool(config_row),
                "algorithm_card_present": bool(card_row),
                **{f"config_{field}": normalize(config_row.get(field, "")) for field in CONFIG_FIELDS},
                **{f"card_{field}": normalize(card_row.get(field, "")) for field in CARD_FIELDS},
                **{f"source_{field}_values": ";".join(unique_source[field]) for field in SOURCE_CONFIG_FIELDS},
            }
        )
    return rows


def build_command_rows(case_commands):
    rows = []
    for row in case_commands:
        flags = parse_flags(row["command"])
        algorithms = [item for item in normalize(flags.get("algorithms", "")).split(",") if item]
        errors = []
        if algorithms != FORMAL_ALGORITHMS:
            errors.append("algorithm_list_or_order_mismatch")
        if normalize(flags.get("config")) != CONFIG_PATH:
            errors.append("config_path_mismatch")
        rows.append(
            {
                "case_id": row.get("case_id", ""),
                "benchmark": row.get("benchmark", ""),
                "num_agents": row.get("num_agents", ""),
                "seed": row.get("seed", ""),
                "config_path": normalize(flags.get("config")),
                "algorithm_count": len(algorithms),
                "algorithm_list": ",".join(algorithms),
                "expected_algorithm_list": ",".join(FORMAL_ALGORITHMS),
                "max_neighbors": normalize(flags.get("max-neighbors")),
                "observation_type": normalize(flags.get("observation-type")),
                "finish_mode": normalize(flags.get("finish-mode")),
                "status": "pass" if not errors else "error",
                "errors": ";".join(errors),
            }
        )
    return rows


def build_freeze_fingerprint(config_algorithms):
    payload = {
        name: {field: normalize(config_algorithms.get(name, {}).get(field, "")) for field in CONFIG_FIELDS}
        for name in FORMAL_ALGORITHMS
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def summarize(algorithm_rows, command_rows):
    algorithm_errors = [row for row in algorithm_rows if row["status"] != "pass"]
    command_errors = [row for row in command_rows if row["status"] != "pass"]
    return {
        "status": "pass" if not algorithm_errors and not command_errors else "review_required",
        "formal_algorithm_count": len(FORMAL_ALGORITHMS),
        "algorithm_rows_checked": len(algorithm_rows),
        "algorithm_error_count": len(algorithm_errors),
        "case_command_count": len(command_rows),
        "case_command_pass_count": sum(1 for row in command_rows if row["status"] == "pass"),
        "case_command_error_count": len(command_errors),
        "source_rows_expected_per_algorithm": 30,
        "formal_algorithm_list": ",".join(FORMAL_ALGORITHMS),
    }


def build_markdown(report):
    summary = report["summary"]
    lines = [
        "# T-ITS Algorithm Configuration Freeze Audit",
        "",
        "该审计面向审稿复现，检查正式 8 个算法的配置是否可从 `configs/tits_dynamic_graph_experiments.json`、algorithm cards、frozen case commands 和正式 source data 共同复原。",
        "",
        "## Summary",
        "",
    ]
    for key, value in summary.items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            f"- config_freeze_payload_sha256: {report['config_freeze_payload_sha256']}",
            "",
            "## What This Proves",
            "",
            "- 正式矩阵只使用 8 个预定义算法，并且每个 frozen case command 的算法列表和顺序一致。",
            "- 每个正式算法在 source data 中有 30 行结果，对应 30 个 matched cases。",
            "- algorithm card 与 config 中的模型路径、动态邻域模式、planner budget 和主要权重一致。",
            "- source data 中记录的邻域选择、planner horizon/candidates/risk/uncertainty 权重与冻结 config 一致。",
            "- `rule_expert_gate` 被显式标记为无模型权重的规则基线；DLC/world-model 类算法必须声明模型路径。",
            "",
            "## Formal Algorithms",
            "",
            "| Algorithm | Status | Source rows | Neighbor mode | Planner | Model path | Errors |",
            "|---|---|---:|---|---|---|---|",
        ]
    )
    for row in report["algorithm_rows"]:
        planner = f"{row['config_planner_horizon']}x{row['config_planner_candidates']}".strip("x")
        lines.append(
            f"| {row['algorithm']} | {row['status']} | {row['source_run_rows']} | {row['config_neighbor_selection_mode'] or row['source_neighbor_selection_mode_values']} | {planner} | `{row['card_model_path']}` | {row['errors']} |"
        )
    lines.extend(
        [
            "",
            "## Blocking Issues",
            "",
        ]
    )
    blocking = [row for row in report["algorithm_rows"] if row["status"] != "pass"] + [
        row for row in report["command_rows"] if row["status"] != "pass"
    ]
    if not blocking:
        lines.append("No blocking algorithm-configuration freeze issues were found.")
    else:
        lines.extend(["| Item | Errors |", "|---|---|"])
        for row in blocking:
            item = row.get("algorithm") or f"case {row.get('case_id')}"
            lines.append(f"| {item} | {row.get('errors', '')} |")
    lines.extend(
        [
            "",
            "## Regeneration Command",
            "",
            "```bash",
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_algorithm_config_freeze_audit.py --out-dir outputs/tits_dynamic_graph/tits_algorithm_config_freeze_audit",
            "```",
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Audit frozen algorithm configuration for the formal T-ITS benchmark.")
    parser.add_argument("--config", default=CONFIG_PATH)
    parser.add_argument("--algorithm-cards", default=ALGORITHM_CARDS)
    parser.add_argument("--source-csv", default=SOURCE_CSV)
    parser.add_argument("--case-commands", default=CASE_COMMANDS)
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/tits_algorithm_config_freeze_audit")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    materials = out_dir / "materials"
    tables = out_dir / "tables"
    materials.mkdir(parents=True, exist_ok=True)
    tables.mkdir(parents=True, exist_ok=True)

    config = read_json(args.config)
    config_algorithms = formal_config_algorithms(config)
    cards = read_csv(args.algorithm_cards)
    source_rows = read_csv(args.source_csv)
    case_commands = read_csv(args.case_commands)

    algorithm_rows = build_algorithm_rows(config_algorithms, cards, source_rows)
    command_rows = build_command_rows(case_commands)
    freeze_payload = build_freeze_fingerprint(config_algorithms)

    import hashlib

    report = {
        "status": "pending",
        "inputs": {
            "config": args.config,
            "algorithm_cards": args.algorithm_cards,
            "source_csv": args.source_csv,
            "case_commands": args.case_commands,
        },
        "formal_algorithms": FORMAL_ALGORITHMS,
        "config_freeze_payload_sha256": hashlib.sha256(freeze_payload.encode("utf-8")).hexdigest(),
        "algorithm_rows": algorithm_rows,
        "command_rows": command_rows,
        "note": "This audit freezes algorithm configuration and command routing. It does not evaluate driving performance.",
    }
    report["summary"] = summarize(algorithm_rows, command_rows)
    report["status"] = report["summary"]["status"]

    algorithm_fields = [
        "algorithm",
        "status",
        "errors",
        "warnings",
        "source_run_rows",
        "config_present",
        "algorithm_card_present",
    ]
    algorithm_fields += [f"config_{field}" for field in CONFIG_FIELDS]
    algorithm_fields += [f"card_{field}" for field in CARD_FIELDS]
    algorithm_fields += [f"source_{field}_values" for field in SOURCE_CONFIG_FIELDS]
    command_fields = [
        "case_id",
        "benchmark",
        "num_agents",
        "seed",
        "config_path",
        "algorithm_count",
        "algorithm_list",
        "expected_algorithm_list",
        "max_neighbors",
        "observation_type",
        "finish_mode",
        "status",
        "errors",
    ]
    paths = {
        "audit_md": write_text(materials / "ALGORITHM_CONFIG_FREEZE_AUDIT.md", build_markdown(report)),
        "audit_json": write_json(materials / "ALGORITHM_CONFIG_FREEZE_AUDIT.json", report),
        "algorithm_config_rows_csv": write_csv(tables / "algorithm_config_freeze_rows.csv", algorithm_rows, algorithm_fields),
        "case_command_algorithm_rows_csv": write_csv(tables / "case_command_algorithm_freeze_rows.csv", command_rows, command_fields),
    }
    manifest = {
        "status": report["status"],
        "out_dir": args.out_dir,
        "summary": report["summary"],
        "config_freeze_payload_sha256": report["config_freeze_payload_sha256"],
        "paths": paths,
    }
    manifest_path = write_json(out_dir / "tits_algorithm_config_freeze_audit_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, "status": report["status"], "summary": report["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
