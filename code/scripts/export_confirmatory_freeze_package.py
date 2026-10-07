#!/usr/bin/env python
import argparse
import csv
import hashlib
import json
from pathlib import Path


HELDOUT5_SEEDS = [257, 263, 269, 271, 277, 281, 283, 293, 307, 311]
LARGER_N_SEEDS = list(range(257, 257 + 100))
PROHIBITED_FIELDS = [
    "selected_full_status",
    "oracle_status",
    "oracle_method",
    "validation_status",
    "pass_count",
    "oracle_pass_count",
    "candidate_gap_seeds",
    "selector_miss_seeds",
]


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def scalar(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return json.dumps(str(value))


def yaml_list(values, indent=2):
    pad = " " * indent
    return "\n".join(f"{pad}- {scalar(value)}" for value in values)


def yaml_mapping(mapping, indent=2):
    pad = " " * indent
    lines = []
    for key, value in mapping.items():
        lines.append(f"{pad}{key}: {scalar(value)}")
    return "\n".join(lines)


def build_config(root):
    selector_source = root / "tables" / "portfolio_probe_selector_1200_heldout4_targeted_expanded.json"
    selector = load_json(selector_source)
    manifest = load_json(root / "manifest.json")
    prereg = load_json(root / "materials" / "CONFIRMATORY_EXPERIMENT_PREREGISTRATION.json")
    gpu = load_json(root / "materials" / "GPU_RERUN_READINESS.json")

    used_seed_sets = {
        name: seeds
        for name, seeds in manifest["seed_sets"].items()
        if name in {"locked", "heldout1", "heldout2", "heldout3", "heldout4", "hard_smoke"}
    }
    used_seeds = sorted({seed for seeds in used_seed_sets.values() for seed in seeds})
    overlap = sorted(set(HELDOUT5_SEEDS).intersection(used_seeds))
    method_model_paths = selector["method_model_paths"]
    missing_models = [
        path for path in method_model_paths.values() if path and not Path(path).exists()
    ]

    config = {
        "schema_version": 1,
        "status": "frozen_template_not_executed",
        "root": str(root),
        "source_selector_report": selector_source.relative_to(root).as_posix(),
        "source_selector_stage": "heldout4_targeted_expanded",
        "intended_future_stage": "heldout5_external_validation",
        "candidate_methods": selector["methods"],
        "method_model_paths": method_model_paths,
        "score_weights": selector["score_weights"],
        "tie_break_priority": selector["tie_break_priority"],
        "probe_steps": selector["probe_steps"],
        "num_agents": 4,
        "gap_tiles": 22,
        "lateral_spacing": 0.0,
        "target_base_speed": 22.0,
        "baseline_policies": "telemetry_cruise,telemetry_yield,telemetry_lane",
        "target_start_rule": "target car starts last behind traffic",
        "heldout5_seeds": HELDOUT5_SEEDS,
        "larger_n_seed_template": {
            "minimum_n": 75,
            "preferred_n": 100,
            "seed_start": LARGER_N_SEEDS[0],
            "seed_end": LARGER_N_SEEDS[-1],
            "seeds": LARGER_N_SEEDS,
        },
        "traffic_density_strata": [2, 3, 4, 5],
        "opponent_mixture_strata": [
            "telemetry_cruise,telemetry_yield,telemetry_lane",
            "telemetry_cruise,telemetry_yield,telemetry_adaptive_conservative",
            "telemetry_lane,telemetry_adaptive,telemetry_expert_recovery",
        ],
        "prohibited_online_fields": PROHIBITED_FIELDS,
        "cuda_devices": "cuda:0,cuda:1,cuda:2,cuda:3",
        "parallelism_policy": "one rollout worker per GPU when supported; preserve seed order and per-seed device logs",
        "pre_run_lock_artifacts": [
            "configs/heldout5_frozen_selector.yaml",
            "materials/CONFIRMATORY_FREEZE_AUDIT.json",
            "materials/CONFIRMATORY_EXPERIMENT_PREREGISTRATION.json",
            "materials/GPU_RERUN_READINESS.json",
        ],
        "post_run_required_artifacts": [
            "tables/heldout5_external_validation.csv",
            "tables/heldout5_external_validation.md",
            "tables/larger_n_generalization_report.csv",
            "tables/traffic_density_ablation_report.csv",
            "tables/opponent_diversity_ablation_report.csv",
            "materials/SELECTOR_DECISION_AUDIT.csv",
        ],
        "command_templates": {
            "heldout5_selector": (
                "python scripts/run_portfolio_probe_selector.py --root {root} "
                "--out-dir {root}/evaluations/portfolio_probe_selector_1200_heldout5_frozen "
                "--table-prefix portfolio_probe_selector_1200_heldout5_frozen "
                "--methods {methods} --seeds {heldout5_seeds} --probe-steps 1200 "
                "--devices {cuda_devices} --parallel 4 --skip-existing"
            ),
            "larger_n_suite": (
                "python scripts/run_multiseed_overtake_suite.py --root {root} "
                "--seeds {larger_n_seeds} --devices {cuda_devices}"
            ),
        },
        "claim_boundary": (
            "This file freezes a future simulator validation template only. It is not heldout5 evidence, "
            "not a public-road claim, and not proof of broad robustness."
        ),
    }
    summary = {
        "status": "pass" if not overlap and not missing_models else "review_required",
        "source_selector_pass_count": selector.get("pass_count"),
        "source_selector_oracle_pass_count": selector.get("oracle_pass_count"),
        "candidate_method_count": len(config["candidate_methods"]),
        "heldout5_seed_count": len(HELDOUT5_SEEDS),
        "heldout5_overlap_with_used_seed_count": len(overlap),
        "missing_model_count": len(missing_models),
        "gpu_readiness_status": gpu["summary"]["status"],
        "prereg_row_count": prereg["summary"]["row_count"],
        "minimum_larger_n": config["larger_n_seed_template"]["minimum_n"],
        "preferred_larger_n": config["larger_n_seed_template"]["preferred_n"],
    }
    audit_rows = [
        {
            "check_id": "CF01_seed_disjointness",
            "status": "pass" if not overlap else "review_required",
            "evidence": "manifest.json; configs/heldout5_frozen_selector.yaml",
            "observation": f"heldout5 overlaps used seeds: {overlap}",
            "action": "Use a new disjoint seed block before any heldout5 run.",
            "boundary": "Heldout5 must not reuse locked, heldout1-4, or hard-smoke seeds.",
        },
        {
            "check_id": "CF02_candidate_models_present",
            "status": "pass" if not missing_models else "review_required",
            "evidence": "tables/portfolio_probe_selector_1200_heldout4_targeted_expanded.json",
            "observation": f"missing model paths: {missing_models}",
            "action": "Resolve missing model paths before expensive reruns.",
            "boundary": "Do not replace candidates after seeing heldout5 failures.",
        },
        {
            "check_id": "CF03_oracle_fields_excluded",
            "status": "pass",
            "evidence": "materials/SELECTOR_DECISION_AUDIT.json",
            "observation": "prohibited online fields are enumerated in the frozen config.",
            "action": "Reject future selector feature files that contain prohibited online fields.",
            "boundary": "Full-rollout labels and oracle outcomes are diagnostic only.",
        },
        {
            "check_id": "CF04_gpu_policy_recorded",
            "status": "pass" if gpu["summary"]["status"] == "pass" else "review_required",
            "evidence": "materials/GPU_RERUN_READINESS.json",
            "observation": f"gpu_readiness_status={gpu['summary']['status']}; devices={config['cuda_devices']}",
            "action": "Use all available GPUs where supported and log actual allocation.",
            "boundary": "GPU availability supports reproducibility, not claim strength.",
        },
        {
            "check_id": "CF05_not_executed_boundary",
            "status": "pass",
            "evidence": "materials/CONFIRMATORY_EXPERIMENT_PREREGISTRATION.json",
            "observation": "frozen config status is frozen_template_not_executed.",
            "action": "Keep future heldout5 outputs separate until generated and audited.",
            "boundary": "The frozen config is not evidence that heldout5/larger-N results exist.",
        },
    ]
    config["config_payload_sha256"] = sha256_text(render_yaml(config, include_hash=False))
    yaml_text = render_yaml(config, include_hash=True)
    return config, yaml_text, {
        "root": str(root),
        "title": "Confirmatory Freeze Audit",
        "purpose": "Audit the frozen heldout5/larger-N selector template before any future confirmatory run is executed.",
        "summary": summary | {"config_payload_sha256": config["config_payload_sha256"]},
        "used_seed_sets": used_seed_sets,
        "audit_rows": audit_rows,
        "interpretation": config["claim_boundary"],
    }


def render_yaml(config, include_hash=True):
    lines = [
        "# Frozen selector template for future heldout5/larger-N validation.",
        "# Generated by scripts/export_confirmatory_freeze_package.py.",
        f"schema_version: {config['schema_version']}",
        f"status: {config['status']}",
        f"root: {scalar(config['root'])}",
        f"source_selector_report: {scalar(config['source_selector_report'])}",
        f"source_selector_stage: {scalar(config['source_selector_stage'])}",
        f"intended_future_stage: {scalar(config['intended_future_stage'])}",
        "candidate_methods:",
        yaml_list(config["candidate_methods"]),
        "method_model_paths:",
        yaml_mapping(config["method_model_paths"]),
        "score_weights:",
        yaml_mapping(config["score_weights"]),
        "tie_break_priority:",
        yaml_mapping(config["tie_break_priority"]),
        f"probe_steps: {config['probe_steps']}",
        f"num_agents: {config['num_agents']}",
        f"gap_tiles: {config['gap_tiles']}",
        f"lateral_spacing: {config['lateral_spacing']}",
        f"target_base_speed: {config['target_base_speed']}",
        f"baseline_policies: {scalar(config['baseline_policies'])}",
        f"target_start_rule: {scalar(config['target_start_rule'])}",
        "heldout5_seeds:",
        yaml_list(config["heldout5_seeds"]),
        "larger_n_seed_template:",
        f"  minimum_n: {config['larger_n_seed_template']['minimum_n']}",
        f"  preferred_n: {config['larger_n_seed_template']['preferred_n']}",
        f"  seed_start: {config['larger_n_seed_template']['seed_start']}",
        f"  seed_end: {config['larger_n_seed_template']['seed_end']}",
        "  seeds:",
        yaml_list(config["larger_n_seed_template"]["seeds"], indent=4),
        "traffic_density_strata:",
        yaml_list(config["traffic_density_strata"]),
        "opponent_mixture_strata:",
        yaml_list(config["opponent_mixture_strata"]),
        "prohibited_online_fields:",
        yaml_list(config["prohibited_online_fields"]),
        f"cuda_devices: {scalar(config['cuda_devices'])}",
        f"parallelism_policy: {scalar(config['parallelism_policy'])}",
        "pre_run_lock_artifacts:",
        yaml_list(config["pre_run_lock_artifacts"]),
        "post_run_required_artifacts:",
        yaml_list(config["post_run_required_artifacts"]),
        "command_templates:",
        yaml_mapping(config["command_templates"]),
        f"claim_boundary: {scalar(config['claim_boundary'])}",
    ]
    if include_hash:
        lines.append(f"config_payload_sha256: {scalar(config.get('config_payload_sha256', ''))}")
    lines.append("")
    return "\n".join(lines)


def write_csv(report, path):
    fields = ["check_id", "status", "evidence", "observation", "action", "boundary"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(report["audit_rows"])


def write_markdown(report, path):
    lines = [
        "# Confirmatory Freeze Audit",
        "",
        report["purpose"],
        "",
        report["interpretation"],
        "",
        "## Summary",
        "",
    ]
    for key, value in report["summary"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Audit Rows",
            "",
            "| check | status | observation | action | boundary | evidence |",
            "|---|---|---|---|---|---|",
        ]
    )
    for row in report["audit_rows"]:
        lines.append(
            f"| {row['check_id']} | {row['status']} | {row['observation']} | "
            f"{row['action']} | {row['boundary']} | `{row['evidence']}` |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export frozen heldout5/larger-N confirmatory selector template.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    (root / "configs").mkdir(parents=True, exist_ok=True)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    config, yaml_text, audit = build_config(root)
    yaml_path = root / "configs" / "heldout5_frozen_selector.yaml"
    yaml_path.write_text(yaml_text, encoding="utf-8")
    json_path = materials / "CONFIRMATORY_FREEZE_AUDIT.json"
    md_path = materials / "CONFIRMATORY_FREEZE_AUDIT.md"
    csv_path = materials / "CONFIRMATORY_FREEZE_AUDIT.csv"
    config_json_path = materials / "CONFIRMATORY_FREEZE_CONFIG.json"
    config_json_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    json_path.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    write_markdown(audit, md_path)
    write_csv(audit, csv_path)
    print(
        json.dumps(
            {
                "config_yaml": str(yaml_path),
                "config_json": str(config_json_path),
                "audit_json": str(json_path),
                "audit_markdown": str(md_path),
                "audit_csv": str(csv_path),
                "summary": audit["summary"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
