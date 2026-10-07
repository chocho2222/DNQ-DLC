#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import json
from pathlib import Path


PUBLIC_CODE_PREFIXES = (
    "configs/",
    "dlc/",
    "docs/",
    "gym_multi_car_racing/",
    "scripts/",
    "tracks/",
)
PUBLIC_CODE_FILES = {
    "README.md",
    "LICENSE",
    "environment.yml",
    "Makefile",
    "setup.py",
}
MANDATORY_ARCHIVE_PREFIXES = (
    "outputs/tits_dynamic_graph/models/",
    "outputs/tits_dynamic_graph/v6_confirmatory_matrix/",
    "outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/",
    "outputs/tits_dynamic_graph/v6_confirmatory_preflight/",
    "outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack/",
    "outputs/tits_dynamic_graph/publication_gifs/",
    "outputs/tits_dynamic_graph/reviewer_replication_packet/",
    "outputs/tits_dynamic_graph/tits_reviewer_smoke_route_audit/",
    "outputs/tits_dynamic_graph/tits_reviewer_smoke_execution_audit/",
    "outputs/tits_dynamic_graph/tits_root_readme_alignment_audit/",
    "outputs/tits_dynamic_graph/tits_refresh_coverage_audit/",
    "outputs/tits_dynamic_graph/tits_status_snapshot/",
    "outputs/tits_dynamic_graph/tits_evidence_ledger/",
    "outputs/tits_dynamic_graph/tits_claim_numeric_consistency_audit/",
    "outputs/tits_dynamic_graph/tits_checksum_verification_audit/",
    "outputs/tits_dynamic_graph/tits_external_validity_boundary_audit/",
    "outputs/tits_dynamic_graph/tits_limitations_evidence_audit/",
    "outputs/tits_dynamic_graph/tits_protocol_deviation_readiness_pack/",
    "outputs/tits_dynamic_graph/tits_manuscript_package/",
    "outputs/tits_dynamic_graph/tits_manuscript_numeric_trace_audit/",
    "outputs/tits_dynamic_graph/tits_manuscript_section_trace_audit/",
    "outputs/tits_dynamic_graph/tits_abstract_highlights_evidence_audit/",
    "outputs/tits_dynamic_graph/tits_manuscript_supplement_navigator/",
    "outputs/tits_dynamic_graph/tits_numbering_consistency_audit/",
    "outputs/tits_dynamic_graph/tits_figure_source_data_audit/",
    "outputs/tits_dynamic_graph/tits_figure_source_value_recompute_audit/",
    "outputs/tits_dynamic_graph/tits_publication_gif_provenance_audit/",
    "outputs/tits_dynamic_graph/tits_supplementary_video_index_pack/",
    "outputs/tits_dynamic_graph/tits_supplementary_submission_index_pack/",
    "outputs/tits_dynamic_graph/tits_online_decision_case_study_pack/",
    "outputs/tits_dynamic_graph/tits_safety_proxy_audit_pack/",
    "outputs/tits_dynamic_graph/tits_media_upload_quality_audit/",
    "outputs/tits_dynamic_graph/manuscript_english_figures/",
    "outputs/tits_dynamic_graph/tits_ablation_contribution_pack/",
    "outputs/tits_dynamic_graph/tits_casewise_diagnostic_pack/",
    "outputs/tits_dynamic_graph/tits_baseline_fairness_audit/",
    "outputs/tits_dynamic_graph/tits_benchmark_protocol_pack/",
    "outputs/tits_dynamic_graph/tits_statistical_analysis_pack/",
    "outputs/tits_dynamic_graph/tits_experimental_design_power_audit/",
    "outputs/tits_dynamic_graph/tits_threats_validity_pack/",
    "outputs/tits_dynamic_graph/tits_reviewer_rebuttal_readiness_pack/",
    "outputs/tits_dynamic_graph/tits_runtime_scalability_pack/",
    "outputs/tits_dynamic_graph/tits_compute_reproducibility_cost_pack/",
    "outputs/tits_dynamic_graph/tits_overtake_timing_analysis_pack/",
    "outputs/tits_dynamic_graph/tits_overtake_casewise_diagnostics_pack/",
    "outputs/tits_dynamic_graph/tits_typical_first_person_case_pack/",
    "outputs/tits_dynamic_graph/tits_six_experiment_protocol_pack/",
    "outputs/tits_dynamic_graph/tits_v7_elegance_barrier_design_pack/",
    "outputs/tits_dynamic_graph/v7_elegance_barrier_smoke/",
    "outputs/tits_dynamic_graph/tits_compute_timing_boundary_audit/",
    "outputs/tits_dynamic_graph/tits_ai_tool_use_disclosure_audit/",
    "outputs/tits_dynamic_graph/tits_claim_language_audit/",
    "outputs/tits_dynamic_graph/tits_claim_evidence_completeness_audit/",
    "outputs/tits_dynamic_graph/tits_cross_reference_audit/",
    "outputs/tits_dynamic_graph/tits_source_data_integrity_audit/",
    "outputs/tits_dynamic_graph/tits_source_data_schema_dictionary_pack/",
    "outputs/tits_dynamic_graph/tits_run_level_provenance_audit/",
    "outputs/tits_dynamic_graph/tits_trace_integrity_audit/",
    "outputs/tits_dynamic_graph/tits_trace_schema_dictionary_pack/",
    "outputs/tits_dynamic_graph/tits_overtake_event_consistency_audit/",
    "outputs/tits_dynamic_graph/tits_statistical_table_recompute_audit/",
    "outputs/tits_dynamic_graph/tits_results_reporting_checklist/",
    "outputs/tits_dynamic_graph/tits_results_narrative_pack/",
    "outputs/tits_dynamic_graph/tits_figure_caption_claim_audit/",
    "outputs/tits_dynamic_graph/tits_table_caption_source_data_audit/",
    "outputs/tits_dynamic_graph/tits_table_value_recompute_audit/",
    "outputs/tits_dynamic_graph/tits_environment_reproducibility_audit/",
    "outputs/tits_dynamic_graph/tits_determinism_smoke_audit/",
    "outputs/tits_dynamic_graph/tits_reproducibility_capsule/",
    "outputs/tits_dynamic_graph/tits_data_leakage_tuning_audit/",
    "outputs/tits_dynamic_graph/tits_innovation_evidence_traceability/",
    "outputs/tits_dynamic_graph/tits_metric_sensitivity_audit/",
    "outputs/tits_dynamic_graph/tits_model_artifact_integrity_audit/",
    "outputs/tits_dynamic_graph/tits_algorithm_config_freeze_audit/",
    "outputs/paper_multicar_overtake_20260618/models/graph_risk_world_model/",
    "outputs/paper_multicar_overtake_20260618/models/graph_risk_world_model_variants/",
    "outputs/tits_dynamic_graph/public_release_plan/",
    "outputs/tits_dynamic_graph/final_readiness_dashboard/",
    "outputs/tits_dynamic_graph/ieee_tits_compliance/",
    "outputs/tits_dynamic_graph/tits_submission_metadata_pack/",
    "outputs/tits_dynamic_graph/tits_github_release_readiness_pack/",
    "outputs/tits_dynamic_graph/tits_open_source_minimal_repo_audit/",
    "outputs/tits_dynamic_graph/tits_author_submission_closure_pack/",
    "outputs/tits_dynamic_graph/tits_author_owned_submission_integrity_audit/",
    "outputs/tits_dynamic_graph/tits_reviewer_reproduction_time_budget_audit/",
    "outputs/tits_dynamic_graph/tits_fair_archive_metadata_pack/",
    "outputs/tits_dynamic_graph/tits_third_party_reproduction_pack/",
    "outputs/tits_dynamic_graph/tits_freshness_audit/",
    "outputs/tits_dynamic_graph/tits_container_build_preflight/",
    "outputs/tits_dynamic_graph/tits_submission_upload_bundle_map/",
    "outputs/tits_dynamic_graph/tits_submission_dry_run_checklist/",
    "outputs/tits_dynamic_graph/tits_submission_gap_priority_audit/",
    "outputs/tits_dynamic_graph/tits_final_freeze_consistency_audit/",
    "outputs/tits_dynamic_graph/tits_anonymization_privacy_audit/",
    "outputs/tits_dynamic_graph/tits_dependency_license_audit/",
    "outputs/tits_dynamic_graph/artifact_manifest/",
    "outputs/tits_dynamic_graph_cleanup/",
)
MANDATORY_ARCHIVE_FILES = {
    "outputs/tits_dynamic_graph/tits_readiness_audit.json",
    "outputs/tits_dynamic_graph/v6_confirmatory_matrix_run_summary.json",
    "outputs/tits_dynamic_graph/v6_confirmatory_matrix_run_results_ledger.csv",
}
OPTIONAL_ARCHIVE_PREFIXES = (
    "outputs/tits_dynamic_graph/logs/",
    "outputs/tits_dynamic_graph/online_evaluation_matrix/",
    "outputs/tits_dynamic_graph/online_evaluation_matrix_summary/",
    "outputs/tits_dynamic_graph/representative_gifs/",
    "outputs/tits_dynamic_graph/v6_runtime_dynamic_neighborhood_representative_gifs/",
)
OPTIONAL_ARCHIVE_FILES = {
    "outputs/tits_dynamic_graph/online_matrix_run_summary.json",
    "outputs/tits_dynamic_graph/online_repair_summary.json",
    "outputs/tits_dynamic_graph/v6_confirmatory_matrix_dry_run_summary.json",
    "outputs/tits_dynamic_graph/v6_confirmatory_matrix_drycheck_dry_run_summary.json",
}
LOCAL_ONLY_FILES = {
    "outputs/tits_dynamic_graph/dry-run_summary.json",
    "outputs/tits_dynamic_graph/online_matrix_dry_run_summary.json",
    "outputs/tits_dynamic_graph/smoke_summary.json",
}
EXCLUDE_DIR_KEYWORDS = (
    "smoke",
    "optimization_checks",
    "elegant_overtake",
    "elegant_dataset",
    "elegant_graph_bc",
    "quality_aux",
    "quality_guided",
    "quality_graph_bc",
    "quality_metric_checks",
    "quality_proposal",
    "online_evaluation_matrix_quality",
    "v6_planner_budget",
    "v6_runtime_dynamic_neighborhood_matrix",
    "online_planner_patch_smoke",
    "overtake_planner_ablation_smoke",
    "config_driven_eval_smoke",
)


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def size_of(path):
    path = Path(path)
    if not path.exists():
        return 0
    if path.is_file():
        return path.stat().st_size
    total = 0
    for item in path.rglob("*"):
        if item.is_file():
            total += item.stat().st_size
    return total


def mb(size_bytes):
    return round(size_bytes / (1024 * 1024), 3)


def classify_artifact_file(path):
    if path in PUBLIC_CODE_FILES or path.startswith(PUBLIC_CODE_PREFIXES):
        return "public_code_repository"
    if path in MANDATORY_ARCHIVE_FILES or path.startswith(MANDATORY_ARCHIVE_PREFIXES):
        return "mandatory_data_archive"
    if path == "outputs/tits_dynamic_graph/train_summary.json":
        return "mandatory_data_archive"
    if path in OPTIONAL_ARCHIVE_FILES or path.startswith(OPTIONAL_ARCHIVE_PREFIXES):
        return "optional_full_archive"
    if path in LOCAL_ONLY_FILES:
        return "local_only_not_for_release"
    return "review_required"


def classify_output_dir(rel_path):
    name = Path(rel_path).name
    if rel_path in {
        "outputs/tits_dynamic_graph/artifact_manifest",
        "outputs/tits_dynamic_graph/models",
        "outputs/tits_dynamic_graph/v6_confirmatory_matrix",
        "outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary",
        "outputs/tits_dynamic_graph/v6_confirmatory_preflight",
        "outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack",
        "outputs/tits_dynamic_graph/publication_gifs",
        "outputs/tits_dynamic_graph/reviewer_replication_packet",
        "outputs/tits_dynamic_graph/tits_reviewer_smoke_route_audit",
        "outputs/tits_dynamic_graph/tits_reviewer_smoke_execution_audit",
        "outputs/tits_dynamic_graph/tits_root_readme_alignment_audit",
        "outputs/tits_dynamic_graph/tits_refresh_coverage_audit",
        "outputs/tits_dynamic_graph/tits_status_snapshot",
        "outputs/tits_dynamic_graph/tits_evidence_ledger",
        "outputs/tits_dynamic_graph/tits_claim_numeric_consistency_audit",
        "outputs/tits_dynamic_graph/tits_checksum_verification_audit",
        "outputs/tits_dynamic_graph/tits_external_validity_boundary_audit",
        "outputs/tits_dynamic_graph/tits_protocol_deviation_readiness_pack",
        "outputs/tits_dynamic_graph/tits_manuscript_package",
        "outputs/tits_dynamic_graph/tits_manuscript_numeric_trace_audit",
        "outputs/tits_dynamic_graph/tits_manuscript_section_trace_audit",
        "outputs/tits_dynamic_graph/tits_abstract_highlights_evidence_audit",
        "outputs/tits_dynamic_graph/tits_manuscript_supplement_navigator",
        "outputs/tits_dynamic_graph/tits_numbering_consistency_audit",
        "outputs/tits_dynamic_graph/tits_figure_source_data_audit",
        "outputs/tits_dynamic_graph/tits_figure_source_value_recompute_audit",
        "outputs/tits_dynamic_graph/tits_publication_gif_provenance_audit",
        "outputs/tits_dynamic_graph/tits_supplementary_video_index_pack",
        "outputs/tits_dynamic_graph/tits_supplementary_submission_index_pack",
        "outputs/tits_dynamic_graph/tits_online_decision_case_study_pack",
        "outputs/tits_dynamic_graph/tits_safety_proxy_audit_pack",
        "outputs/tits_dynamic_graph/tits_media_upload_quality_audit",
        "outputs/tits_dynamic_graph/manuscript_english_figures",
        "outputs/tits_dynamic_graph/tits_ablation_contribution_pack",
        "outputs/tits_dynamic_graph/tits_casewise_diagnostic_pack",
        "outputs/tits_dynamic_graph/tits_baseline_fairness_audit",
        "outputs/tits_dynamic_graph/tits_benchmark_protocol_pack",
        "outputs/tits_dynamic_graph/tits_statistical_analysis_pack",
        "outputs/tits_dynamic_graph/tits_experimental_design_power_audit",
        "outputs/tits_dynamic_graph/tits_threats_validity_pack",
        "outputs/tits_dynamic_graph/tits_reviewer_rebuttal_readiness_pack",
        "outputs/tits_dynamic_graph/tits_runtime_scalability_pack",
        "outputs/tits_dynamic_graph/tits_compute_reproducibility_cost_pack",
        "outputs/tits_dynamic_graph/tits_overtake_timing_analysis_pack",
        "outputs/tits_dynamic_graph/tits_overtake_casewise_diagnostics_pack",
        "outputs/tits_dynamic_graph/tits_typical_first_person_case_pack",
        "outputs/tits_dynamic_graph/tits_six_experiment_protocol_pack",
        "outputs/tits_dynamic_graph/tits_v7_elegance_barrier_design_pack",
        "outputs/tits_dynamic_graph/v7_elegance_barrier_smoke",
        "outputs/tits_dynamic_graph/tits_compute_timing_boundary_audit",
        "outputs/tits_dynamic_graph/tits_ai_tool_use_disclosure_audit",
        "outputs/tits_dynamic_graph/tits_claim_language_audit",
        "outputs/tits_dynamic_graph/tits_claim_evidence_completeness_audit",
        "outputs/tits_dynamic_graph/tits_cross_reference_audit",
        "outputs/tits_dynamic_graph/tits_source_data_integrity_audit",
        "outputs/tits_dynamic_graph/tits_source_data_schema_dictionary_pack",
        "outputs/tits_dynamic_graph/tits_run_level_provenance_audit",
        "outputs/tits_dynamic_graph/tits_trace_integrity_audit",
        "outputs/tits_dynamic_graph/tits_trace_schema_dictionary_pack",
        "outputs/tits_dynamic_graph/tits_overtake_event_consistency_audit",
        "outputs/tits_dynamic_graph/tits_statistical_table_recompute_audit",
        "outputs/tits_dynamic_graph/tits_results_reporting_checklist",
        "outputs/tits_dynamic_graph/tits_results_narrative_pack",
        "outputs/tits_dynamic_graph/tits_figure_caption_claim_audit",
        "outputs/tits_dynamic_graph/tits_table_caption_source_data_audit",
        "outputs/tits_dynamic_graph/tits_table_value_recompute_audit",
        "outputs/tits_dynamic_graph/tits_environment_reproducibility_audit",
        "outputs/tits_dynamic_graph/tits_determinism_smoke_audit",
        "outputs/tits_dynamic_graph/tits_reproducibility_capsule",
        "outputs/tits_dynamic_graph/tits_data_leakage_tuning_audit",
        "outputs/tits_dynamic_graph/tits_innovation_evidence_traceability",
        "outputs/tits_dynamic_graph/tits_metric_sensitivity_audit",
        "outputs/tits_dynamic_graph/tits_model_artifact_integrity_audit",
        "outputs/tits_dynamic_graph/tits_algorithm_config_freeze_audit",
        "outputs/tits_dynamic_graph/public_release_plan",
        "outputs/tits_dynamic_graph/final_readiness_dashboard",
        "outputs/tits_dynamic_graph/ieee_tits_compliance",
        "outputs/tits_dynamic_graph/tits_submission_metadata_pack",
        "outputs/tits_dynamic_graph/tits_github_release_readiness_pack",
        "outputs/tits_dynamic_graph/tits_open_source_minimal_repo_audit",
        "outputs/tits_dynamic_graph/tits_author_submission_closure_pack",
        "outputs/tits_dynamic_graph/tits_author_owned_submission_integrity_audit",
        "outputs/tits_dynamic_graph/tits_reviewer_reproduction_time_budget_audit",
        "outputs/tits_dynamic_graph/tits_fair_archive_metadata_pack",
        "outputs/tits_dynamic_graph/tits_third_party_reproduction_pack",
        "outputs/tits_dynamic_graph/tits_freshness_audit",
        "outputs/tits_dynamic_graph/tits_container_build_preflight",
        "outputs/tits_dynamic_graph/tits_submission_upload_bundle_map",
        "outputs/tits_dynamic_graph/tits_submission_dry_run_checklist",
        "outputs/tits_dynamic_graph/tits_submission_gap_priority_audit",
        "outputs/tits_dynamic_graph/tits_final_freeze_consistency_audit",
        "outputs/tits_dynamic_graph/tits_anonymization_privacy_audit",
        "outputs/tits_dynamic_graph/tits_dependency_license_audit",
        "outputs/tits_dynamic_graph/tits_checksum_verification_audit",
        "outputs/tits_dynamic_graph/tits_external_validity_boundary_audit",
        "outputs/tits_dynamic_graph/tits_limitations_evidence_audit",
    }:
        return "mandatory_data_archive"
    if rel_path in {
        "outputs/tits_dynamic_graph/logs",
        "outputs/tits_dynamic_graph/online_evaluation_matrix",
        "outputs/tits_dynamic_graph/online_evaluation_matrix_summary",
        "outputs/tits_dynamic_graph/representative_gifs",
        "outputs/tits_dynamic_graph/v6_runtime_dynamic_neighborhood_representative_gifs",
    }:
        return "optional_full_archive"
    if any(keyword in name for keyword in EXCLUDE_DIR_KEYWORDS):
        return "exclude_from_public_release"
    if name in {"figures", "gifs", "tables", "online_evaluation", "v6_confirmatory_matrix_partial_summary"}:
        return "legacy_or_superseded_output"
    return "review_required"


def build_file_plan(root, artifact_manifest):
    rows = []
    for item in artifact_manifest["files"]:
        path = item["path"]
        role = classify_artifact_file(path)
        if role == "public_code_repository":
            destination = "GitHub/public code repository"
            rationale = "Source/config/documentation required to run and inspect the method."
        elif role == "mandatory_data_archive":
            destination = "Data repository or release asset"
            rationale = "Formal evidence, model, source data, visual evidence, checksum, or reviewer-facing material."
        elif role == "optional_full_archive":
            destination = "Optional full archive"
            rationale = "Useful for deeper debugging or historical traceability, but not required for the minimal reviewer package."
        else:
            destination = "Manual review"
            rationale = "Not covered by the current release-routing rules."
        rows.append(
            {
                "path": path,
                "release_role": role,
                "destination": destination,
                "size_bytes": item.get("size_bytes", 0),
                "size_mb": mb(item.get("size_bytes", 0)),
                "sha256": item.get("sha256", ""),
                "rationale": rationale,
            }
        )
    return rows


def build_directory_plan(root):
    output_root = root / "outputs" / "tits_dynamic_graph"
    rows = []
    if not output_root.exists():
        return rows
    for path in sorted(output_root.iterdir()):
        if not path.is_dir():
            continue
        rel = path.relative_to(root).as_posix()
        role = classify_output_dir(rel)
        if role == "mandatory_data_archive":
            action = "archive_and_manifest"
        elif role == "optional_full_archive":
            action = "archive_if_size_budget_allows"
        elif role == "exclude_from_public_release":
            action = "exclude_from_public_release; keep local provenance only"
        elif role == "legacy_or_superseded_output":
            action = "exclude unless specifically cited"
        else:
            action = "manual_review"
        rows.append(
            {
                "path": rel,
                "release_role": role,
                "recommended_action": action,
                "size_bytes": size_of(path),
                "size_mb": mb(size_of(path)),
            }
        )
    return rows


def summarize(rows, key):
    out = {}
    for row in rows:
        role = row[key]
        item = out.setdefault(role, {"file_count": 0, "size_bytes": 0})
        item["file_count"] += 1
        item["size_bytes"] += int(row.get("size_bytes", 0) or 0)
    return {
        role: {**value, "size_mb": mb(value["size_bytes"])}
        for role, value in sorted(out.items())
    }


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


def write_markdown(path, manifest, file_rows, dir_rows):
    lines = [
        "# T-ITS Public Release Plan",
        "",
        "This plan separates the current workspace into a public code repository, a mandatory data/archive package, optional full-archive material, and local-only exploratory outputs.",
        "",
        "## Summary",
        "",
        f"- Status: `{manifest['status']}`",
        f"- Artifact files inspected: {manifest['summary']['artifact_file_count']}",
        f"- Top-level output directories inspected: {manifest['summary']['output_directory_count']}",
        f"- Review-required artifact files: {manifest['summary']['review_required_file_count']}",
        f"- Review-required output directories: {manifest['summary']['review_required_directory_count']}",
        "",
        "## Artifact File Roles",
        "",
        "| Role | Files | Size MB |",
        "|---|---:|---:|",
    ]
    for role, value in manifest["file_role_summary"].items():
        lines.append(f"| {role} | {value['file_count']} | {value['size_mb']} |")
    lines.extend(
        [
            "",
            "## Output Directory Roles",
            "",
            "| Role | Directories | Size MB |",
            "|---|---:|---:|",
        ]
    )
    for role, value in manifest["directory_role_summary"].items():
        lines.append(f"| {role} | {value['file_count']} | {value['size_mb']} |")
    lines.extend(
        [
            "",
            "## Recommended Public Repository Contents",
            "",
            "- Core source: `dlc/`, `gym_multi_car_racing/`, selected `scripts/`, `configs/`, `tracks/`.",
            "- Documentation: `README.md`, `docs/tits_dynamic_graph_reproducibility_protocol.md`, `docs/tits_current_readiness_gap.md`.",
            "- Environment and setup files: `environment.yml`, `setup.py`, `Makefile`, `LICENSE`.",
            "- Lightweight reviewer pointers: reviewer packet and manuscript package may be mirrored as release documentation.",
            "- Model artifacts: current T-ITS weights plus original DLC world-model baseline weights referenced by the formal algorithm cards.",
            "",
            "## Recommended Data Repository Contents",
            "",
            "- Confirmatory matrix and summaries: `v6_confirmatory_matrix`, `v6_confirmatory_matrix_full_summary`, `v6_confirmatory_preflight`.",
            "- Formal evidence and author-facing checks: `tits_confirmatory_evidence_pack`, `publication_gifs`, `tits_publication_gif_provenance_audit`, `tits_supplementary_video_index_pack`, `tits_supplementary_submission_index_pack`, `tits_online_decision_case_study_pack`, `tits_safety_proxy_audit_pack`, `tits_typical_first_person_case_pack`, `tits_six_experiment_protocol_pack`, `reviewer_replication_packet`, `tits_reviewer_smoke_route_audit`, `tits_reviewer_smoke_execution_audit`, `tits_root_readme_alignment_audit`, `tits_status_snapshot`, `tits_evidence_ledger`, `tits_claim_numeric_consistency_audit`, `tits_checksum_verification_audit`, `tits_external_validity_boundary_audit`, `tits_manuscript_package`, `tits_manuscript_numeric_trace_audit`, `tits_manuscript_section_trace_audit`, `tits_abstract_highlights_evidence_audit`, `tits_manuscript_supplement_navigator`, `tits_figure_source_data_audit`, `tits_figure_source_value_recompute_audit`, `tits_figure_caption_claim_audit`, `tits_table_value_recompute_audit`, `tits_media_upload_quality_audit`, `manuscript_english_figures`, `tits_ablation_contribution_pack`, `tits_benchmark_protocol_pack`, `tits_statistical_analysis_pack`, `tits_experimental_design_power_audit`, `tits_threats_validity_pack`, `tits_reviewer_rebuttal_readiness_pack`, `tits_runtime_scalability_pack`, `tits_compute_reproducibility_cost_pack`, `tits_overtake_timing_analysis_pack`, `tits_overtake_casewise_diagnostics_pack`, `tits_v7_elegance_barrier_design_pack`, `tits_ai_tool_use_disclosure_audit`, `tits_reviewer_reproduction_time_budget_audit`, `tits_claim_language_audit`, `tits_claim_evidence_completeness_audit`, `tits_cross_reference_audit`, `tits_source_data_integrity_audit`, `tits_source_data_schema_dictionary_pack`, `tits_run_level_provenance_audit`, `tits_trace_integrity_audit`, `tits_trace_schema_dictionary_pack`, `tits_overtake_event_consistency_audit`, `tits_statistical_table_recompute_audit`, `tits_results_reporting_checklist`, `tits_results_narrative_pack`, `tits_environment_reproducibility_audit`, `tits_determinism_smoke_audit`, `tits_reproducibility_capsule`, `tits_data_leakage_tuning_audit`, `tits_innovation_evidence_traceability`, `tits_metric_sensitivity_audit`, `tits_freshness_audit`, `tits_container_build_preflight`, `tits_submission_upload_bundle_map`, `tits_submission_dry_run_checklist`, `tits_submission_gap_priority_audit`, `tits_anonymization_privacy_audit`, `tits_dependency_license_audit`, `final_readiness_dashboard`, `ieee_tits_compliance`, `tits_submission_metadata_pack`, `tits_github_release_readiness_pack`, `tits_open_source_minimal_repo_audit`, `tits_author_submission_closure_pack`, `tits_author_owned_submission_integrity_audit`, `tits_fair_archive_metadata_pack`, `tits_third_party_reproduction_pack`.",
            "- Models and track artifacts: `models`, `tracks/monza_scaled.*`.",
            "- Checksums: `artifact_manifest`.",
            "",
            "## Reviewer Reproduction and Observation-Only Evidence",
            "",
            "- The reviewer packet defines four reproduction depths: T0 smoke execution, T1 reporting-layer rebuild, T2 full confirmatory matrix rerun, and T3 representative visual-evidence rebuild.",
            "- `tits_reviewer_smoke_execution_audit` and `tits_reviewer_smoke_route_audit` should be archived as observation-only reproducibility evidence. They verify route health and local execution fingerprints, but they are not paper-scale performance results.",
            "- Formal numeric claims remain tied to `v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv`, the 30 frozen case commands, and the downstream statistical, figure, table, trace and claim audits.",
            "- The evidence ledger indexes the observation-only reproduction evidence separately from formal claim evidence, so release users can audit smoke-route health without confusing it with the 240-run benchmark matrix.",
            "- The reviewer time-budget audit records expected T0-T3 scope and cost boundaries; include it with the release materials whenever the reviewer packet is shared.",
            "",
            "## Local-Only or Excluded Outputs",
            "",
            "Exploratory smoke tests, optimization checks, historical quality sweeps, and superseded online matrices should not be presented as formal evidence unless explicitly cited. They may be kept locally for provenance but should not inflate the public release package.",
            "",
            "## Author Actions Before Upload",
            "",
            "- Choose a public archive and assign DOI/accession.",
            "- Decide whether full traces should be uploaded or made available on request because the complete `outputs/tits_dynamic_graph` tree is much larger than the formal evidence package.",
            "- Confirm license compatibility for code, model weights, generated GIFs, and the Monza-derived track.",
            "- Re-run the artifact manifest after any file movement or deletion.",
            "",
            "## Key CSV Files",
            "",
            f"- File-level plan: `{manifest['paths']['file_plan_csv']}`",
            f"- Directory-level plan: `{manifest['paths']['directory_plan_csv']}`",
        ]
    )
    path = Path(path)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(path)


def build_audit(file_rows, dir_rows):
    missing_mandatory_dirs = [
        path
        for path in [
            "outputs/tits_dynamic_graph/models",
            "outputs/tits_dynamic_graph/v6_confirmatory_matrix",
            "outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary",
            "outputs/tits_dynamic_graph/v6_confirmatory_preflight",
            "outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack",
            "outputs/tits_dynamic_graph/publication_gifs",
            "outputs/tits_dynamic_graph/tits_status_snapshot",
            "outputs/tits_dynamic_graph/tits_evidence_ledger",
            "outputs/tits_dynamic_graph/tits_claim_numeric_consistency_audit",
            "outputs/tits_dynamic_graph/tits_checksum_verification_audit",
            "outputs/tits_dynamic_graph/tits_external_validity_boundary_audit",
            "outputs/tits_dynamic_graph/manuscript_english_figures",
            "outputs/tits_dynamic_graph/tits_figure_source_data_audit",
            "outputs/tits_dynamic_graph/tits_figure_source_value_recompute_audit",
            "outputs/tits_dynamic_graph/tits_publication_gif_provenance_audit",
            "outputs/tits_dynamic_graph/tits_supplementary_video_index_pack",
            "outputs/tits_dynamic_graph/tits_supplementary_submission_index_pack",
            "outputs/tits_dynamic_graph/tits_online_decision_case_study_pack",
            "outputs/tits_dynamic_graph/tits_safety_proxy_audit_pack",
            "outputs/tits_dynamic_graph/tits_manuscript_section_trace_audit",
            "outputs/tits_dynamic_graph/tits_manuscript_supplement_navigator",
            "outputs/tits_dynamic_graph/tits_ablation_contribution_pack",
            "outputs/tits_dynamic_graph/tits_benchmark_protocol_pack",
            "outputs/tits_dynamic_graph/tits_statistical_analysis_pack",
            "outputs/tits_dynamic_graph/tits_experimental_design_power_audit",
            "outputs/tits_dynamic_graph/tits_threats_validity_pack",
            "outputs/tits_dynamic_graph/tits_reviewer_rebuttal_readiness_pack",
            "outputs/tits_dynamic_graph/tits_reviewer_smoke_execution_audit",
            "outputs/tits_dynamic_graph/tits_claim_language_audit",
            "outputs/tits_dynamic_graph/tits_claim_evidence_completeness_audit",
            "outputs/tits_dynamic_graph/tits_compute_reproducibility_cost_pack",
            "outputs/tits_dynamic_graph/tits_compute_timing_boundary_audit",
            "outputs/tits_dynamic_graph/tits_ai_tool_use_disclosure_audit",
            "outputs/tits_dynamic_graph/tits_cross_reference_audit",
            "outputs/tits_dynamic_graph/tits_source_data_integrity_audit",
            "outputs/tits_dynamic_graph/tits_source_data_schema_dictionary_pack",
            "outputs/tits_dynamic_graph/tits_run_level_provenance_audit",
            "outputs/tits_dynamic_graph/tits_trace_integrity_audit",
            "outputs/tits_dynamic_graph/tits_trace_schema_dictionary_pack",
            "outputs/tits_dynamic_graph/tits_overtake_event_consistency_audit",
            "outputs/tits_dynamic_graph/tits_statistical_table_recompute_audit",
            "outputs/tits_dynamic_graph/tits_table_value_recompute_audit",
            "outputs/tits_dynamic_graph/tits_environment_reproducibility_audit",
            "outputs/tits_dynamic_graph/tits_determinism_smoke_audit",
            "outputs/tits_dynamic_graph/tits_reproducibility_capsule",
            "outputs/tits_dynamic_graph/tits_data_leakage_tuning_audit",
            "outputs/tits_dynamic_graph/tits_innovation_evidence_traceability",
            "outputs/tits_dynamic_graph/tits_metric_sensitivity_audit",
            "outputs/tits_dynamic_graph/tits_open_source_minimal_repo_audit",
            "outputs/tits_dynamic_graph/tits_typical_first_person_case_pack",
            "outputs/tits_dynamic_graph/tits_six_experiment_protocol_pack",
            "outputs/tits_dynamic_graph/final_readiness_dashboard",
            "outputs/tits_dynamic_graph/ieee_tits_compliance",
        "outputs/tits_dynamic_graph/tits_submission_metadata_pack",
        "outputs/tits_dynamic_graph/tits_github_release_readiness_pack",
        "outputs/tits_dynamic_graph/tits_author_submission_closure_pack",
        "outputs/tits_dynamic_graph/tits_author_owned_submission_integrity_audit",
        "outputs/tits_dynamic_graph/tits_reviewer_reproduction_time_budget_audit",
        "outputs/tits_dynamic_graph/tits_fair_archive_metadata_pack",
            "outputs/tits_dynamic_graph/tits_third_party_reproduction_pack",
            "outputs/tits_dynamic_graph/artifact_manifest",
        ]
        if not any(row["path"] == path for row in dir_rows)
    ]
    review_required_files = [row for row in file_rows if row["release_role"] == "review_required"]
    review_required_dirs = [row for row in dir_rows if row["release_role"] == "review_required"]
    return {
        "status": "pass" if not missing_mandatory_dirs and not review_required_files else "review_required",
        "missing_mandatory_directories": missing_mandatory_dirs,
        "review_required_file_count": len(review_required_files),
        "review_required_directory_count": len(review_required_dirs),
        "review_required_files_sample": [row["path"] for row in review_required_files[:20]],
        "review_required_directories": [row["path"] for row in review_required_dirs],
        "note": "Directory-level review-required entries may be harmless local-only outputs; file-level review-required entries should be resolved before public upload.",
    }


def main():
    parser = argparse.ArgumentParser(description="Export a public release and archive routing plan for the T-ITS package.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--artifact-manifest", default="outputs/tits_dynamic_graph/artifact_manifest/tits_dynamic_graph_artifact_manifest.json")
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/public_release_plan")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    artifact = load_json(root / args.artifact_manifest)
    out_dir = root / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    file_rows = build_file_plan(root, artifact)
    dir_rows = build_directory_plan(root)
    audit = build_audit(file_rows, dir_rows)
    paths = {
        "file_plan_csv": write_csv(
            out_dir / "public_release_file_plan.csv",
            file_rows,
            ["path", "release_role", "destination", "size_bytes", "size_mb", "sha256", "rationale"],
        ),
        "directory_plan_csv": write_csv(
            out_dir / "public_release_directory_plan.csv",
            dir_rows,
            ["path", "release_role", "recommended_action", "size_bytes", "size_mb"],
        ),
        "audit_json": "",
        "readme_md": "",
    }
    manifest = {
        "status": audit["status"],
        "root": str(root),
        "artifact_manifest": args.artifact_manifest,
        "summary": {
            "artifact_file_count": len(file_rows),
            "output_directory_count": len(dir_rows),
            "review_required_file_count": audit["review_required_file_count"],
            "review_required_directory_count": audit["review_required_directory_count"],
            "mandatory_archive_file_count": sum(1 for row in file_rows if row["release_role"] == "mandatory_data_archive"),
            "public_code_file_count": sum(1 for row in file_rows if row["release_role"] == "public_code_repository"),
        },
        "file_role_summary": summarize(file_rows, "release_role"),
        "directory_role_summary": summarize(dir_rows, "release_role"),
        "audit": audit,
        "paths": paths,
    }
    paths["audit_json"] = write_json(out_dir / "public_release_audit.json", audit)
    paths["readme_md"] = write_markdown(out_dir / "PUBLIC_RELEASE_PLAN.md", manifest, file_rows, dir_rows)
    manifest["paths"] = paths
    manifest_path = write_json(out_dir / "public_release_plan_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, "status": manifest["status"], "files": len(file_rows), "dirs": len(dir_rows)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
