#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def compact(values):
    return "; ".join(str(value) for value in values if value)


def artifact_by_name(provenance):
    return {item["name"]: item for item in provenance["artifacts"]}


def artifact_row(artifacts, name):
    item = artifacts.get(name, {})
    return {
        "name": name,
        "command": item.get("command", ""),
        "scripts": item.get("scripts", []),
        "inputs": item.get("inputs", []),
        "outputs": item.get("outputs", []),
        "complete": item.get("complete", False),
    }


def row(section, item, source, artifacts, artifact_names, evidence, reviewer_check, boundary, status=None):
    selected = [artifact_row(artifacts, name) for name in artifact_names]
    missing = [entry["name"] for entry in selected if not entry["complete"]]
    commands = [entry["command"] for entry in selected if entry["command"]]
    scripts = sorted({script for entry in selected for script in entry["scripts"]})
    inputs = sorted({path for entry in selected for path in entry["inputs"]})
    outputs = sorted({path for entry in selected for path in entry["outputs"]})
    return {
        "section": section,
        "item": item,
        "source": source,
        "artifact": compact(artifact_names),
        "command": compact(commands),
        "files": compact(scripts + inputs),
        "expected_outputs": compact(outputs),
        "evidence": evidence,
        "reviewer_check": reviewer_check,
        "boundary": boundary,
        "status": status or ("ready" if not missing else "review_required"),
        "note": "Missing or incomplete artifacts: " + compact(missing) if missing else "",
    }


def build_report(root):
    provenance = load_json(root / "tables" / "artifact_provenance.json")
    methods = load_json(root / "materials" / "METHODS_REPRODUCIBILITY_CAPSULE.json")
    registry = load_json(root / "materials" / "EXPERIMENT_REGISTRY.json")
    dependency = load_json(root / "materials" / "ARTIFACT_DEPENDENCY_MAP.json")
    replication = load_json(root / "materials" / "REVIEWER_REPLICATION_ROUTE.json")
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    smoke = load_json(root / "materials" / "PUBLICATION_SMOKE_TEST.json")
    dictionary = load_json(root / "materials" / "DATA_DICTIONARY.json")
    artifacts = artifact_by_name(provenance)

    rows = [
        row(
            "task_and_endpoint",
            "strict_full_lap_overtaking_endpoint",
            "materials/METHODS_REPRODUCIBILITY_CAPSULE.md; materials/STATISTICAL_ANALYSIS_PLAN.md",
            artifacts,
            ["statistical_analysis_plan_audit", "endpoint_sensitivity_audit"],
            "materials/STATISTICAL_ANALYSIS_PLAN_AUDIT.md; materials/ENDPOINT_SENSITIVITY_AUDIT.md",
            "Confirm the primary endpoint, secondary endpoints, and sensitivity checks are explicitly separated.",
            "Do not reinterpret GIFs, rank, or partial progress as strict full-lap PASS outcomes.",
        ),
        row(
            "simulator_and_environment",
            "multi_car_racing_environment_and_dependencies",
            "gym_multi_car_racing/multi_car_racing.py; environment.yml; setup.py",
            artifacts,
            ["environment_reproducibility_audit", "software_dependency_license_audit"],
            "materials/ENVIRONMENT_REPRODUCIBILITY_AUDIT.md; materials/SOFTWARE_DEPENDENCY_LICENSE_AUDIT.md",
            "Check environment.yml, setup.py, local package metadata, and simulator source paths.",
            "Local environment metadata documents this package and is not a cross-platform performance guarantee.",
        ),
        row(
            "training_and_policy_components",
            "graph_policy_training_and_model_card",
            "scripts/train_graph_bc.py; dlc/graph_policy.py; dlc/torch_models.py",
            artifacts,
            ["graph_dagger_recovery_v2_training", "policy_model_card"],
            "models/graph_bc/graph_bc.graph.pt; materials/POLICY_MODEL_CARD.md",
            "Confirm saved model path, training source, component role, and non-VLM telemetry/state scope.",
            "Saved model and model card support simulator methods only, not real-world deployment readiness.",
        ),
        row(
            "rollout_evaluation",
            "locked_and_heldout_multiseed_rollouts",
            "scripts/run_multiseed_overtake_suite.py; dlc/rollout.py; dlc/policies.py",
            artifacts,
            [
                "main_multiseed_suite",
                "adaptive_gate_suite",
                "recovery_adaptive_suite",
                "heldout_multiseed_suite",
                "heldout_adaptive_suite",
            ],
            "tables/full_statistical_report.md; materials/EXPERIMENT_REGISTRY.md; tables/seed_outcome_ledger.md",
            "Trace each reported seed set to its registered rollout command, saved summary JSON, and seed ledger.",
            "Locked and held-out seed sets support bounded simulator claims, not broad robustness.",
        ),
        row(
            "selector_and_oracle",
            "portfolio_probe_selector_and_diagnostic_oracle",
            "scripts/run_portfolio_probe_selector.py; scripts/export_portfolio_oracle_report.py",
            artifacts,
            [
                "portfolio_oracle",
                "online_probe_selector_1200",
                "heldout2_candidate_expansion",
                "heldout3_candidate_expansion",
                "heldout4_external_validation",
            ],
            "tables/seed_outcome_ledger.md; materials/SELECTOR_DECISION_AUDIT.md; tables/cross_heldout_validation_synthesis.md",
            "Verify selector decisions from probe rows and keep oracle rows labelled diagnostic upper bound.",
            "Oracle is not an online selector output; heldout3 targeted repair is diagnostic reuse, heldout4 is post-repair external validation with partial transfer.",
        ),
        row(
            "statistics",
            "uncertainty_effect_size_and_consistency_reporting",
            "scripts/export_statistical_reporting_appendix.py; scripts/export_effect_size_uncertainty_summary.py",
            artifacts,
            [
                "statistical_reporting_appendix",
                "effect_size_uncertainty_summary",
                "statistical_consistency_audit",
                "cross_heldout_statistical_supplement",
            ],
            "materials/STATISTICAL_REPORTING_APPENDIX.md; materials/EFFECT_SIZE_UNCERTAINTY_SUMMARY.md; materials/STATISTICAL_CONSISTENCY_AUDIT.md",
            "Check Wilson intervals, exact tests, effect summaries, and static numeric consistency before manuscript edits.",
            "Statistics are descriptive for saved seed sets and do not prove broad robustness.",
        ),
        row(
            "figures_and_source_data",
            "figure_generation_source_data_and_production_handoff",
            "scripts/export_paper_figures.py; scripts/export_cross_heldout_validation_figure.py; scripts/export_figure_production_handoff.py",
            artifacts,
            [
                "main_figure",
                "cross_heldout_validation_figure",
                "figure_source_data_audit",
                "figure_technical_qc",
                "figure_production_handoff",
            ],
            "materials/FIGURE_SOURCE_DATA_AUDIT.md; materials/FIGURE_TECHNICAL_QC.md; materials/FIGURE_PRODUCTION_HANDOFF.md",
            "Confirm each main figure has source data, PDF/SVG/TIFF/PNG exports, technical QC, and production notes.",
            "Figure production notes are packaging guidance and do not add empirical validation.",
        ),
        row(
            "package_integrity",
            "publication_gates_manifest_and_reviewer_replication",
            "scripts/run_publication_smoke_test.py; scripts/export_publication_package_verification.py; scripts/export_release_archive_manifest.py",
            artifacts,
            [
                "publication_package_verification",
                "publication_smoke_test",
                "release_archive_manifest",
                "final_checksum_freeze_record",
                "reviewer_replication_route",
            ],
            "materials/PUBLICATION_PACKAGE_VERIFICATION.md; materials/PUBLICATION_SMOKE_TEST.md; materials/RELEASE_ARCHIVE_MANIFEST.md; materials/REVIEWER_REPLICATION_ROUTE.md",
            "Run fast package gates first; use registered GPU rollout reruns only if reviewers request end-to-end reproduction.",
            "Integrity gates verify saved artifacts and checksums; they do not certify public deposition or journal acceptance.",
        ),
        row(
            "submission_and_archive",
            "journal_upload_archive_and_author_owned_fields",
            "materials/SUBMISSION_UPLOAD_SELECTION_PLAN.md; materials/TARGET_JOURNAL_UPLOAD_DECISION_CHECKLIST.md",
            artifacts,
            [
                "slim_submission_package_manifest",
                "target_journal_upload_decision_checklist",
                "archive_size_budget_report",
                "local_author_readiness_separation_audit",
            ],
            "materials/SLIM_SUBMISSION_PACKAGE_MANIFEST.md; materials/TARGET_JOURNAL_UPLOAD_DECISION_CHECKLIST.md; materials/ARCHIVE_SIZE_BUDGET_REPORT.md",
            "Check which files belong in journal upload, source-data upload, full archive, or author-completed portal fields.",
            "The package must not invent DOI, ORCID, funding, conflicts, target journal, or author-certified declarations.",
        ),
    ]

    review_required = [item for item in rows if item["status"] == "review_required"]
    return {
        "root": str(root),
        "title": "Methods-to-Code Traceability Matrix",
        "purpose": (
            "Map Methods-level claims and procedures to registered scripts, configuration/input files, "
            "saved outputs, reviewer checks, and claim boundaries."
        ),
        "summary": {
            "status": "pass" if not review_required else "review_required",
            "row_count": len(rows),
            "review_required_count": len(review_required),
            "methods_capsule_status": methods["summary"]["status"],
            "experiment_registry_count": registry["summary"]["experiment_count"],
            "artifact_dependency_count": dependency["summary"]["artifact_count"],
            "reviewer_replication_route_status": replication["summary"]["status"],
            "publication_verification_status": verification["summary"]["status"],
            "publication_smoke_test_reference": "materials/PUBLICATION_SMOKE_TEST.json",
            "artifact_provenance": f"{provenance['complete_count']}/{len(provenance['artifacts'])}",
            "data_dictionary_complete": dictionary["summary"]["complete"],
        },
        "rows": rows,
        "interpretation": (
            "This matrix is a reviewer navigation aid. It does not replace the registered commands in "
            "artifact_provenance.md or the underlying scripts and saved result files."
        ),
    }


def write_csv(report, path):
    fields = [
        "section",
        "item",
        "source",
        "artifact",
        "command",
        "files",
        "expected_outputs",
        "evidence",
        "reviewer_check",
        "boundary",
        "status",
        "note",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in report["rows"]:
            writer.writerow({field: item.get(field, "") for field in fields})


def write_markdown(report, path):
    lines = [
        "# Methods-to-Code Traceability Matrix",
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
            "## Trace Rows",
            "",
            "| section | item | status | source | artifacts | evidence | reviewer check | boundary |",
            "|---|---|---|---|---|---|---|---|",
        ]
    )
    for item in report["rows"]:
        lines.append(
            f"| {item['section']} | {item['item']} | {item['status']} | `{item['source']}` | "
            f"`{item['artifact']}` | `{item['evidence']}` | {item['reviewer_check']} | {item['boundary']} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export methods-to-code traceability matrix.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_report(root)
    out_json = materials / "METHODS_TO_CODE_TRACEABILITY.json"
    out_md = materials / "METHODS_TO_CODE_TRACEABILITY.md"
    out_csv = materials / "METHODS_TO_CODE_TRACEABILITY.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv), "summary": report["summary"]}, indent=2))


if __name__ == "__main__":
    main()
