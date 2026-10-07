#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import json
from pathlib import Path


SOURCE_DATA = "outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv"
FINAL_READINESS = "outputs/tits_dynamic_graph/final_readiness_dashboard/final_readiness_dashboard_manifest.json"
FRESHNESS = "outputs/tits_dynamic_graph/tits_freshness_audit/tits_freshness_audit_manifest.json"
CROSSREF = "outputs/tits_dynamic_graph/tits_cross_reference_audit/tits_cross_reference_audit_manifest.json"
ROOT_README = "outputs/tits_dynamic_graph/tits_root_readme_alignment_audit/tits_root_readme_alignment_audit_manifest.json"
SMOKE_ROUTE = "outputs/tits_dynamic_graph/tits_reviewer_smoke_route_audit/tits_reviewer_smoke_route_audit_manifest.json"
SMOKE_EXECUTION = "outputs/tits_dynamic_graph/tits_reviewer_smoke_execution_audit/tits_reviewer_smoke_execution_audit_manifest.json"
EVIDENCE_LEDGER = "outputs/tits_dynamic_graph/tits_evidence_ledger/tits_evidence_ledger_manifest.json"
CLAIM_NUMERIC = "outputs/tits_dynamic_graph/tits_claim_numeric_consistency_audit/tits_claim_numeric_consistency_audit_manifest.json"
MANUSCRIPT_SECTION_TRACE = "outputs/tits_dynamic_graph/tits_manuscript_section_trace_audit/tits_manuscript_section_trace_audit_manifest.json"
ABSTRACT_HIGHLIGHTS = "outputs/tits_dynamic_graph/tits_abstract_highlights_evidence_audit/tits_abstract_highlights_evidence_audit_manifest.json"
CHECKSUM_AUDIT = "outputs/tits_dynamic_graph/tits_checksum_verification_audit/tits_checksum_verification_audit_manifest.json"
EXTERNAL_VALIDITY = "outputs/tits_dynamic_graph/tits_external_validity_boundary_audit/tits_external_validity_boundary_audit_manifest.json"
LIMITATIONS_EVIDENCE = "outputs/tits_dynamic_graph/tits_limitations_evidence_audit/tits_limitations_evidence_audit_manifest.json"
THREATS_VALIDITY = "outputs/tits_dynamic_graph/tits_threats_validity_pack/tits_threats_validity_pack_manifest.json"
PROTOCOL_DEVIATION = "outputs/tits_dynamic_graph/tits_protocol_deviation_readiness_pack/tits_protocol_deviation_readiness_pack_manifest.json"
AUTHOR_OWNED = "outputs/tits_dynamic_graph/tits_author_owned_submission_integrity_audit/tits_author_owned_submission_integrity_audit_manifest.json"
REPRODUCTION_TIME_BUDGET = "outputs/tits_dynamic_graph/tits_reviewer_reproduction_time_budget_audit/tits_reviewer_reproduction_time_budget_audit_manifest.json"
RUN_LEVEL_PROVENANCE = "outputs/tits_dynamic_graph/tits_run_level_provenance_audit/tits_run_level_provenance_audit_manifest.json"
TRACE_INTEGRITY = "outputs/tits_dynamic_graph/tits_trace_integrity_audit/tits_trace_integrity_audit_manifest.json"
TRACE_SCHEMA = "outputs/tits_dynamic_graph/tits_trace_schema_dictionary_pack/tits_trace_schema_dictionary_pack_manifest.json"
OVERTAKE_EVENT_CONSISTENCY = "outputs/tits_dynamic_graph/tits_overtake_event_consistency_audit/tits_overtake_event_consistency_audit_manifest.json"
STATISTICAL_TABLE_RECOMPUTE = "outputs/tits_dynamic_graph/tits_statistical_table_recompute_audit/tits_statistical_table_recompute_audit_manifest.json"
RESULTS_REPORTING = "outputs/tits_dynamic_graph/tits_results_reporting_checklist/tits_results_reporting_checklist_manifest.json"
RESULTS_NARRATIVE = "outputs/tits_dynamic_graph/tits_results_narrative_pack/tits_results_narrative_pack_manifest.json"
FIGURE_SOURCE_VALUE_RECOMPUTE = "outputs/tits_dynamic_graph/tits_figure_source_value_recompute_audit/tits_figure_source_value_recompute_audit_manifest.json"
FIGURE_CAPTION_CLAIM = "outputs/tits_dynamic_graph/tits_figure_caption_claim_audit/tits_figure_caption_claim_audit_manifest.json"
TABLE_CAPTION_SOURCE_DATA = "outputs/tits_dynamic_graph/tits_table_caption_source_data_audit/tits_table_caption_source_data_audit_manifest.json"
TABLE_VALUE_RECOMPUTE = "outputs/tits_dynamic_graph/tits_table_value_recompute_audit/tits_table_value_recompute_audit_manifest.json"
PUBLICATION_GIF_PROVENANCE = "outputs/tits_dynamic_graph/tits_publication_gif_provenance_audit/tits_publication_gif_provenance_audit_manifest.json"
SUPPLEMENTARY_VIDEO_INDEX = "outputs/tits_dynamic_graph/tits_supplementary_video_index_pack/tits_supplementary_video_index_pack_manifest.json"
SUPPLEMENTARY_SUBMISSION_INDEX = "outputs/tits_dynamic_graph/tits_supplementary_submission_index_pack/tits_supplementary_submission_index_pack_manifest.json"
ONLINE_DECISION_CASE_STUDY = "outputs/tits_dynamic_graph/tits_online_decision_case_study_pack/tits_online_decision_case_study_pack_manifest.json"
SAFETY_PROXY_AUDIT = "outputs/tits_dynamic_graph/tits_safety_proxy_audit_pack/tits_safety_proxy_audit_pack_manifest.json"
SOURCE_DATA_SCHEMA = "outputs/tits_dynamic_graph/tits_source_data_schema_dictionary_pack/tits_source_data_schema_dictionary_pack_manifest.json"
ALGORITHM_CONFIG_FREEZE = "outputs/tits_dynamic_graph/tits_algorithm_config_freeze_audit/tits_algorithm_config_freeze_audit_manifest.json"
COMPUTE_TIMING_BOUNDARY = "outputs/tits_dynamic_graph/tits_compute_timing_boundary_audit/tits_compute_timing_boundary_audit_manifest.json"
AI_TOOL_USE_DISCLOSURE = "outputs/tits_dynamic_graph/tits_ai_tool_use_disclosure_audit/tits_ai_tool_use_disclosure_audit_manifest.json"
OPEN_SOURCE_MINIMAL_REPO = "outputs/tits_dynamic_graph/tits_open_source_minimal_repo_audit/tits_open_source_minimal_repo_audit_manifest.json"
SUBMISSION_GAP_PRIORITY = "outputs/tits_dynamic_graph/tits_submission_gap_priority_audit/tits_submission_gap_priority_audit_manifest.json"
FINAL_FREEZE_CONSISTENCY = "outputs/tits_dynamic_graph/tits_final_freeze_consistency_audit/tits_final_freeze_consistency_audit_manifest.json"
ARTIFACT = "outputs/tits_dynamic_graph/artifact_manifest/tits_dynamic_graph_artifact_manifest.json"
RELEASE = "outputs/tits_dynamic_graph/public_release_plan/public_release_plan_manifest.json"
FAIR = "outputs/tits_dynamic_graph/tits_fair_archive_metadata_pack/tits_fair_archive_metadata_pack_manifest.json"


def read_json(path):
    path = Path(path)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def source_facts(path):
    path = Path(path)
    if not path.exists():
        return {
            "source_rows": 0,
            "matched_case_count": 0,
            "algorithm_count": 0,
            "benchmarks": [],
            "vehicle_counts": [],
            "status": "missing",
        }
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    cases = {
        (
            row.get("_benchmark"),
            row.get("seed"),
            row.get("num_agents"),
            row.get("track_path"),
            row.get("traffic_profile"),
        )
        for row in rows
    }
    return {
        "source_rows": len(rows),
        "matched_case_count": len(cases),
        "algorithm_count": len({row.get("algorithm") for row in rows}),
        "benchmarks": sorted({row.get("_benchmark", "") for row in rows}),
        "vehicle_counts": sorted({row.get("num_agents", "") for row in rows}, key=lambda x: int(x or 0)),
        "status": "pass",
    }


def build_status():
    facts = source_facts(SOURCE_DATA)
    final = read_json(FINAL_READINESS)
    freshness = read_json(FRESHNESS)
    crossref = read_json(CROSSREF)
    root = read_json(ROOT_README)
    smoke = read_json(SMOKE_ROUTE)
    smoke_execution = read_json(SMOKE_EXECUTION)
    evidence_ledger = read_json(EVIDENCE_LEDGER)
    claim_numeric = read_json(CLAIM_NUMERIC)
    manuscript_section_trace = read_json(MANUSCRIPT_SECTION_TRACE)
    abstract_highlights = read_json(ABSTRACT_HIGHLIGHTS)
    checksum_audit = read_json(CHECKSUM_AUDIT)
    external_validity = read_json(EXTERNAL_VALIDITY)
    limitations_evidence = read_json(LIMITATIONS_EVIDENCE)
    threats_validity = read_json(THREATS_VALIDITY)
    protocol_deviation = read_json(PROTOCOL_DEVIATION)
    author_owned = read_json(AUTHOR_OWNED)
    reproduction_time_budget = read_json(REPRODUCTION_TIME_BUDGET)
    run_level_provenance = read_json(RUN_LEVEL_PROVENANCE)
    trace_integrity = read_json(TRACE_INTEGRITY)
    trace_schema = read_json(TRACE_SCHEMA)
    overtake_event_consistency = read_json(OVERTAKE_EVENT_CONSISTENCY)
    statistical_table_recompute = read_json(STATISTICAL_TABLE_RECOMPUTE)
    results_reporting = read_json(RESULTS_REPORTING)
    results_narrative = read_json(RESULTS_NARRATIVE)
    figure_source_value_recompute = read_json(FIGURE_SOURCE_VALUE_RECOMPUTE)
    figure_caption_claim = read_json(FIGURE_CAPTION_CLAIM)
    table_caption_source_data = read_json(TABLE_CAPTION_SOURCE_DATA)
    table_value_recompute = read_json(TABLE_VALUE_RECOMPUTE)
    publication_gif_provenance = read_json(PUBLICATION_GIF_PROVENANCE)
    supplementary_video_index = read_json(SUPPLEMENTARY_VIDEO_INDEX)
    supplementary_submission_index = read_json(SUPPLEMENTARY_SUBMISSION_INDEX)
    online_decision_case_study = read_json(ONLINE_DECISION_CASE_STUDY)
    safety_proxy_audit = read_json(SAFETY_PROXY_AUDIT)
    source_data_schema = read_json(SOURCE_DATA_SCHEMA)
    algorithm_config_freeze = read_json(ALGORITHM_CONFIG_FREEZE)
    compute_timing_boundary = read_json(COMPUTE_TIMING_BOUNDARY)
    ai_tool_use_disclosure = read_json(AI_TOOL_USE_DISCLOSURE)
    open_source_minimal_repo = read_json(OPEN_SOURCE_MINIMAL_REPO)
    submission_gap_priority = read_json(SUBMISSION_GAP_PRIORITY)
    final_freeze_consistency = read_json(FINAL_FREEZE_CONSISTENCY)
    artifact = read_json(ARTIFACT)
    release = read_json(RELEASE)
    fair = read_json(FAIR)
    return {
        "formal_matrix": facts,
        "final_readiness": {
            "status": final.get("status"),
            "pass_count": final.get("pass_count"),
            "gate_count": final.get("gate_count"),
        },
        "freshness": {
            "status": freshness.get("status"),
            "stale_count": freshness.get("summary", {}).get("stale_count"),
        },
        "cross_reference": {
            "status": crossref.get("status"),
            "missing_reference_count": crossref.get("summary", {}).get("missing_reference_count"),
            "risky_formal_reference_count": crossref.get("summary", {}).get("risky_formal_reference_count"),
            "unknown_prefix_count": crossref.get("summary", {}).get("unknown_prefix_count"),
        },
        "root_readme_alignment": {
            "status": root.get("status"),
            "error_count": root.get("summary", {}).get("error_count"),
        },
        "reviewer_smoke_route": {
            "status": smoke.get("status"),
            "error_count": smoke.get("summary", {}).get("error_count"),
            "command_count": smoke.get("summary", {}).get("command_count"),
            "makefile_target_count": smoke.get("summary", {}).get("makefile_target_count"),
        },
        "reviewer_smoke_execution": {
            "status": smoke_execution.get("status", "not_recorded"),
            "summary_count": smoke_execution.get("summary", {}).get("summary_count", 0),
            "expected_summary_count": smoke_execution.get("summary", {}).get("expected_summary_count", 0),
            "algorithms": smoke_execution.get("summary", {}).get("algorithms", ""),
            "check_count": smoke_execution.get("summary", {}).get("check_count", 0),
            "issue_count": smoke_execution.get("summary", {}).get("issue_count", 0),
            "smoke_dir": smoke_execution.get("summary", {}).get("smoke_dir", ""),
        },
        "evidence_ledger": {
            "status": evidence_ledger.get("status"),
            "claim_count": evidence_ledger.get("summary", {}).get("claim_count"),
            "evidence_file_count": evidence_ledger.get("summary", {}).get("evidence_file_count"),
            "missing_evidence_file_count": evidence_ledger.get("summary", {}).get("missing_evidence_file_count"),
            "visual_asset_count": evidence_ledger.get("summary", {}).get("visual_asset_count"),
            "missing_visual_asset_count": evidence_ledger.get("summary", {}).get("missing_visual_asset_count"),
            "observation_evidence_count": evidence_ledger.get("summary", {}).get("observation_evidence_count"),
            "missing_observation_evidence_count": evidence_ledger.get("summary", {}).get("missing_observation_evidence_count"),
        },
        "claim_numeric_consistency": {
            "status": claim_numeric.get("status"),
            "numeric_check_count": claim_numeric.get("summary", {}).get("numeric_check_count"),
            "mismatch_count": claim_numeric.get("summary", {}).get("mismatch_count"),
            "audited_claim_count": claim_numeric.get("summary", {}).get("audited_claim_count"),
            "extracted_number_count": claim_numeric.get("summary", {}).get("extracted_number_count"),
        },
        "manuscript_section_trace": {
            "status": manuscript_section_trace.get("status"),
            "claim_count": manuscript_section_trace.get("summary", {}).get("claim_count"),
            "section_trace_row_count": manuscript_section_trace.get("summary", {}).get("section_trace_row_count"),
            "section_gate_pass_count": manuscript_section_trace.get("summary", {}).get("section_gate_pass_count"),
            "section_gate_count": manuscript_section_trace.get("summary", {}).get("section_gate_count"),
            "missing_evidence_count": manuscript_section_trace.get("summary", {}).get("missing_evidence_count"),
        },
        "abstract_highlights_evidence": {
            "status": abstract_highlights.get("status"),
            "claim_count": abstract_highlights.get("summary", {}).get("claim_count"),
            "claim_issue_count": abstract_highlights.get("summary", {}).get("claim_issue_count"),
            "check_count": abstract_highlights.get("summary", {}).get("check_count"),
            "check_issue_count": abstract_highlights.get("summary", {}).get("check_issue_count"),
            "source_rows": abstract_highlights.get("summary", {}).get("source_rows"),
            "matched_case_count": abstract_highlights.get("summary", {}).get("matched_case_count"),
            "algorithm_count": abstract_highlights.get("summary", {}).get("algorithm_count"),
            "vehicle_counts": abstract_highlights.get("summary", {}).get("vehicle_counts"),
        },
        "checksum_verification": {
            "status": checksum_audit.get("status"),
            "mode": checksum_audit.get("summary", {}).get("mode"),
            "verified_file_count": checksum_audit.get("summary", {}).get("verified_file_count"),
            "missing_count": checksum_audit.get("summary", {}).get("missing_count"),
            "checksum_mismatch_count": checksum_audit.get("summary", {}).get("checksum_mismatch_count"),
            "size_mismatch_count": checksum_audit.get("summary", {}).get("size_mismatch_count"),
        },
        "external_validity_boundary": {
            "status": external_validity.get("status"),
            "boundary_count": external_validity.get("summary", {}).get("boundary_count"),
            "passing_boundary_count": external_validity.get("summary", {}).get("passing_boundary_count"),
            "monza_case_count": external_validity.get("summary", {}).get("monza_case_count"),
            "max_vehicle_count": external_validity.get("summary", {}).get("max_vehicle_count"),
        },
        "limitations_evidence": {
            "status": limitations_evidence.get("status"),
            "limitation_count": limitations_evidence.get("summary", {}).get("limitation_count"),
            "limitation_issue_count": limitations_evidence.get("summary", {}).get("limitation_issue_count"),
            "check_count": limitations_evidence.get("summary", {}).get("check_count"),
            "check_issue_count": limitations_evidence.get("summary", {}).get("check_issue_count"),
            "source_rows": limitations_evidence.get("summary", {}).get("source_rows"),
            "max_vehicle_count": limitations_evidence.get("summary", {}).get("max_vehicle_count"),
            "has_monza_external_track": limitations_evidence.get("summary", {}).get("has_monza_external_track"),
        },
        "threats_validity": {
            "status": threats_validity.get("status"),
            "risk_count": threats_validity.get("summary", {}).get("risk_count"),
            "validity_class_count": threats_validity.get("summary", {}).get("validity_class_count"),
            "high_risk_count": threats_validity.get("summary", {}).get("high_risk_count"),
            "response_count": threats_validity.get("summary", {}).get("response_count"),
            "claim_guardrail_count": threats_validity.get("summary", {}).get("claim_guardrail_count"),
        },
        "protocol_deviation_readiness": {
            "status": protocol_deviation.get("status"),
            "primary_endpoint_count": protocol_deviation.get("summary", {}).get("primary_endpoint_count"),
            "endpoint_count": protocol_deviation.get("summary", {}).get("endpoint_count"),
            "population_rule_count": protocol_deviation.get("summary", {}).get("population_rule_count"),
            "protocol_boundary_count": protocol_deviation.get("summary", {}).get("protocol_boundary_count"),
            "missing_evidence_count": protocol_deviation.get("summary", {}).get("missing_evidence_count"),
            "blocking_deviation_count": protocol_deviation.get("summary", {}).get("blocking_deviation_count"),
        },
        "author_owned_submission_integrity": {
            "status": author_owned.get("status"),
            "check_count": author_owned.get("summary", {}).get("check_count"),
            "failed_checks": author_owned.get("summary", {}).get("failed_checks"),
            "author_action_count": author_owned.get("summary", {}).get("author_action_count"),
            "placeholder_count": author_owned.get("summary", {}).get("placeholder_count"),
        },
        "reviewer_reproduction_time_budget": {
            "status": reproduction_time_budget.get("status"),
            "tier_count": reproduction_time_budget.get("summary", {}).get("tier_count"),
            "check_count": reproduction_time_budget.get("summary", {}).get("check_count"),
            "failed_check_count": reproduction_time_budget.get("summary", {}).get("failed_check_count"),
            "source_rows": reproduction_time_budget.get("summary", {}).get("source_rows"),
            "case_command_count": reproduction_time_budget.get("summary", {}).get("case_command_count"),
        },
        "run_level_provenance": {
            "status": run_level_provenance.get("status"),
            "source_rows": run_level_provenance.get("summary", {}).get("source_rows"),
            "run_pass_count": run_level_provenance.get("summary", {}).get("run_pass_count"),
            "run_review_required_count": run_level_provenance.get("summary", {}).get("run_review_required_count"),
            "summary_missing_count": run_level_provenance.get("summary", {}).get("summary_missing_count"),
            "trace_missing_count": run_level_provenance.get("summary", {}).get("trace_missing_count"),
            "summary_field_mismatch_count": run_level_provenance.get("summary", {}).get("summary_field_mismatch_count"),
        },
        "trace_integrity": {
            "status": trace_integrity.get("status"),
            "source_rows": trace_integrity.get("summary", {}).get("source_rows"),
            "trace_run_count": trace_integrity.get("summary", {}).get("trace_run_count"),
            "trace_pass_count": trace_integrity.get("summary", {}).get("trace_pass_count"),
            "total_trace_steps": trace_integrity.get("summary", {}).get("total_trace_steps"),
            "error_count": trace_integrity.get("summary", {}).get("error_count"),
            "warning_count": trace_integrity.get("summary", {}).get("warning_count"),
            "summary_trace_mismatch_count": trace_integrity.get("summary", {}).get("summary_trace_mismatch_count"),
            "step_sequence_failure_count": trace_integrity.get("summary", {}).get("step_sequence_failure_count"),
            "vector_failure_run_count": trace_integrity.get("summary", {}).get("vector_failure_run_count"),
        },
        "trace_schema": {
            "status": trace_schema.get("status"),
            "source_rows": trace_schema.get("summary", {}).get("source_rows"),
            "trace_run_count": trace_schema.get("summary", {}).get("trace_run_count"),
            "trace_pass_count": trace_schema.get("summary", {}).get("trace_pass_count"),
            "dictionary_field_count": trace_schema.get("summary", {}).get("dictionary_field_count"),
            "total_trace_steps": trace_schema.get("summary", {}).get("total_trace_steps"),
            "schema_issue_count": trace_schema.get("summary", {}).get("schema_issue_count"),
            "supported_vehicle_counts": trace_schema.get("summary", {}).get("supported_vehicle_counts"),
        },
        "overtake_event_consistency": {
            "status": overtake_event_consistency.get("status"),
            "source_rows": overtake_event_consistency.get("summary", {}).get("source_rows"),
            "run_count": overtake_event_consistency.get("summary", {}).get("run_count"),
            "run_pass_count": overtake_event_consistency.get("summary", {}).get("run_pass_count"),
            "total_overtake_events": overtake_event_consistency.get("summary", {}).get("total_overtake_events"),
            "total_on_track_events": overtake_event_consistency.get("summary", {}).get("total_on_track_events"),
            "total_elegant_events": overtake_event_consistency.get("summary", {}).get("total_elegant_events"),
            "error_count": overtake_event_consistency.get("summary", {}).get("error_count"),
            "warning_count": overtake_event_consistency.get("summary", {}).get("warning_count"),
        },
        "statistical_table_recompute": {
            "status": statistical_table_recompute.get("status"),
            "source_rows": statistical_table_recompute.get("summary", {}).get("source_rows"),
            "overall_rows_checked": statistical_table_recompute.get("summary", {}).get("overall_rows_checked"),
            "scenario_rows_checked": statistical_table_recompute.get("summary", {}).get("scenario_rows_checked"),
            "paired_rows_checked": statistical_table_recompute.get("summary", {}).get("paired_rows_checked"),
            "compared_cells": statistical_table_recompute.get("summary", {}).get("compared_cells"),
            "mismatch_count": statistical_table_recompute.get("summary", {}).get("mismatch_count"),
            "bootstrap": statistical_table_recompute.get("summary", {}).get("bootstrap"),
            "seed": statistical_table_recompute.get("summary", {}).get("seed"),
        },
        "results_reporting_checklist": {
            "status": results_reporting.get("status"),
            "primary_hypothesis_count": results_reporting.get("summary", {}).get("primary_hypothesis_count"),
            "primary_metric_count": results_reporting.get("summary", {}).get("primary_metric_count"),
            "primary_reporting_issue_count": results_reporting.get("summary", {}).get("primary_reporting_issue_count"),
            "checklist_issue_count": results_reporting.get("summary", {}).get("checklist_issue_count"),
            "source_rows": results_reporting.get("summary", {}).get("source_rows"),
            "effect_size_rows": results_reporting.get("summary", {}).get("effect_size_rows"),
        },
        "results_narrative_pack": {
            "status": results_narrative.get("status"),
            "primary_sentence_count": results_narrative.get("summary", {}).get("primary_sentence_count"),
            "primary_sentence_pass_count": results_narrative.get("summary", {}).get("primary_sentence_pass_count"),
            "checklist_issue_count": results_narrative.get("summary", {}).get("checklist_issue_count"),
            "source_rows": results_narrative.get("summary", {}).get("source_rows"),
            "matched_case_count": results_narrative.get("summary", {}).get("matched_case_count"),
            "algorithm_count": results_narrative.get("summary", {}).get("algorithm_count"),
            "vehicle_counts": results_narrative.get("summary", {}).get("vehicle_counts"),
        },
        "figure_source_value_recompute": {
            "status": figure_source_value_recompute.get("status"),
            "figure_source_rows": figure_source_value_recompute.get("summary", {}).get("figure_source_rows"),
            "checked_rows": figure_source_value_recompute.get("summary", {}).get("checked_rows"),
            "pass_rows": figure_source_value_recompute.get("summary", {}).get("pass_rows"),
            "checked_cells": figure_source_value_recompute.get("summary", {}).get("checked_cells"),
            "mismatch_count": figure_source_value_recompute.get("summary", {}).get("mismatch_count"),
            "source_tables_checked": figure_source_value_recompute.get("summary", {}).get("source_tables_checked"),
        },
        "figure_caption_claim": {
            "status": figure_caption_claim.get("status"),
            "check_count": figure_caption_claim.get("summary", {}).get("check_count"),
            "check_issue_count": figure_caption_claim.get("summary", {}).get("check_issue_count"),
            "panel_count": figure_caption_claim.get("summary", {}).get("panel_count"),
            "panel_issue_count": figure_caption_claim.get("summary", {}).get("panel_issue_count"),
            "source_rows": figure_caption_claim.get("summary", {}).get("source_rows"),
            "figure_archetype": figure_caption_claim.get("summary", {}).get("figure_archetype"),
            "backend": figure_caption_claim.get("summary", {}).get("backend"),
        },
        "table_caption_source_data": {
            "status": table_caption_source_data.get("status"),
            "table_count": table_caption_source_data.get("summary", {}).get("table_count"),
            "table_issue_count": table_caption_source_data.get("summary", {}).get("table_issue_count"),
            "check_count": table_caption_source_data.get("summary", {}).get("check_count"),
            "check_issue_count": table_caption_source_data.get("summary", {}).get("check_issue_count"),
            "source_rows": table_caption_source_data.get("summary", {}).get("source_rows"),
            "matched_case_count": table_caption_source_data.get("summary", {}).get("matched_case_count"),
            "algorithm_count": table_caption_source_data.get("summary", {}).get("algorithm_count"),
            "vehicle_counts": table_caption_source_data.get("summary", {}).get("vehicle_counts"),
        },
        "table_value_recompute": {
            "status": table_value_recompute.get("status"),
            "source_rows": table_value_recompute.get("summary", {}).get("source_rows"),
            "matched_case_count": table_value_recompute.get("summary", {}).get("matched_case_count"),
            "algorithm_count": table_value_recompute.get("summary", {}).get("algorithm_count"),
            "main_table_checked_rows": table_value_recompute.get("summary", {}).get("main_table_checked_rows"),
            "main_table_expected_rows": table_value_recompute.get("summary", {}).get("main_table_expected_rows"),
            "supplementary_s2_checked_rows": table_value_recompute.get("summary", {}).get("supplementary_s2_checked_rows"),
            "checked_cells": table_value_recompute.get("summary", {}).get("checked_cells"),
            "mismatch_count": table_value_recompute.get("summary", {}).get("mismatch_count"),
            "check_issue_count": table_value_recompute.get("summary", {}).get("check_issue_count"),
        },
        "publication_gif_provenance": {
            "status": publication_gif_provenance.get("status"),
            "audited_rows": publication_gif_provenance.get("summary", {}).get("audited_rows"),
            "pass_rows": publication_gif_provenance.get("summary", {}).get("pass_rows"),
            "topdown_gif_count": publication_gif_provenance.get("summary", {}).get("topdown_gif_count"),
            "first_person_gif_count": publication_gif_provenance.get("summary", {}).get("first_person_gif_count"),
            "formal_matrix_rows_found": publication_gif_provenance.get("summary", {}).get("formal_matrix_rows_found"),
            "error_count": publication_gif_provenance.get("summary", {}).get("error_count"),
            "warning_count": publication_gif_provenance.get("summary", {}).get("warning_count"),
        },
        "supplementary_video_index": {
            "status": supplementary_video_index.get("status"),
            "video_rows": supplementary_video_index.get("summary", {}).get("video_rows"),
            "pass_rows": supplementary_video_index.get("summary", {}).get("pass_rows"),
            "missing_gif_count": supplementary_video_index.get("summary", {}).get("missing_gif_count"),
            "error_count": supplementary_video_index.get("summary", {}).get("error_count"),
            "warning_count": supplementary_video_index.get("summary", {}).get("warning_count"),
            "total_size_mb": supplementary_video_index.get("summary", {}).get("total_size_mb"),
        },
        "supplementary_submission_index": {
            "status": supplementary_submission_index.get("status"),
            "supplement_entries": supplementary_submission_index.get("summary", {}).get("supplement_entries"),
            "figure_table_entries": supplementary_submission_index.get("summary", {}).get("figure_table_entries"),
            "video_entries": supplementary_submission_index.get("summary", {}).get("video_entries"),
            "claim_crosswalk_entries": supplementary_submission_index.get("summary", {}).get("claim_crosswalk_entries"),
            "error_count": supplementary_submission_index.get("summary", {}).get("error_count"),
            "warning_count": supplementary_submission_index.get("summary", {}).get("warning_count"),
        },
        "online_decision_case_study": {
            "status": online_decision_case_study.get("status"),
            "study_count": online_decision_case_study.get("summary", {}).get("study_count"),
            "event_rows": online_decision_case_study.get("summary", {}).get("event_rows"),
            "timeline_rows": online_decision_case_study.get("summary", {}).get("timeline_rows"),
            "primary_algorithm": online_decision_case_study.get("summary", {}).get("primary_algorithm"),
            "baseline_algorithm": online_decision_case_study.get("summary", {}).get("baseline_algorithm"),
        },
        "safety_proxy_audit": {
            "status": safety_proxy_audit.get("status"),
            "source_rows": safety_proxy_audit.get("summary", {}).get("source_rows"),
            "trace_sampled_runs": safety_proxy_audit.get("summary", {}).get("trace_sampled_runs"),
            "contact_proxy_positive_runs": safety_proxy_audit.get("summary", {}).get("contact_proxy_positive_runs"),
            "primary_grass_mean": safety_proxy_audit.get("summary", {}).get("primary_grass_mean"),
            "baseline_grass_mean": safety_proxy_audit.get("summary", {}).get("baseline_grass_mean"),
            "primary_high_grass_rate": safety_proxy_audit.get("summary", {}).get("primary_high_grass_rate"),
            "baseline_high_grass_rate": safety_proxy_audit.get("summary", {}).get("baseline_high_grass_rate"),
            "boundary": safety_proxy_audit.get("summary", {}).get("boundary"),
        },
        "source_data_schema": {
            "status": source_data_schema.get("status"),
            "source_rows": source_data_schema.get("summary", {}).get("source_rows"),
            "field_count": source_data_schema.get("summary", {}).get("field_count"),
            "dictionary_field_count": source_data_schema.get("summary", {}).get("dictionary_field_count"),
            "case_count": source_data_schema.get("summary", {}).get("case_count"),
            "algorithm_count": source_data_schema.get("summary", {}).get("algorithm_count"),
            "validation_row_count": source_data_schema.get("summary", {}).get("validation_row_count"),
            "blocking_issue_count": source_data_schema.get("summary", {}).get("blocking_issue_count"),
            "fields_with_missing_values": source_data_schema.get("summary", {}).get("fields_with_missing_values"),
            "fully_populated_fields": source_data_schema.get("summary", {}).get("fully_populated_fields"),
        },
        "algorithm_config_freeze": {
            "status": algorithm_config_freeze.get("status"),
            "formal_algorithm_count": algorithm_config_freeze.get("summary", {}).get("formal_algorithm_count"),
            "algorithm_rows_checked": algorithm_config_freeze.get("summary", {}).get("algorithm_rows_checked"),
            "algorithm_error_count": algorithm_config_freeze.get("summary", {}).get("algorithm_error_count"),
            "case_command_count": algorithm_config_freeze.get("summary", {}).get("case_command_count"),
            "case_command_pass_count": algorithm_config_freeze.get("summary", {}).get("case_command_pass_count"),
            "case_command_error_count": algorithm_config_freeze.get("summary", {}).get("case_command_error_count"),
            "config_freeze_payload_sha256": algorithm_config_freeze.get("config_freeze_payload_sha256"),
        },
        "compute_timing_boundary": {
            "status": compute_timing_boundary.get("status"),
            "available_evidence_count": compute_timing_boundary.get("summary", {}).get("available_evidence_count"),
            "unavailable_boundary_count": compute_timing_boundary.get("summary", {}).get("unavailable_boundary_count"),
            "source_rows": compute_timing_boundary.get("summary", {}).get("source_rows"),
            "case_command_count": compute_timing_boundary.get("summary", {}).get("case_command_count"),
            "total_simulated_steps": compute_timing_boundary.get("summary", {}).get("total_simulated_steps"),
            "mean_compute_latency_ms": compute_timing_boundary.get("summary", {}).get("mean_compute_latency_ms"),
            "gpu_count": compute_timing_boundary.get("summary", {}).get("gpu_count"),
            "cuda_available": compute_timing_boundary.get("summary", {}).get("cuda_available"),
            "wall_clock_boundary_explicit": compute_timing_boundary.get("summary", {}).get("wall_clock_boundary_explicit"),
        },
        "ai_tool_use_disclosure": {
            "status": ai_tool_use_disclosure.get("status"),
            "check_count": ai_tool_use_disclosure.get("summary", {}).get("check_count"),
            "pass_count": ai_tool_use_disclosure.get("summary", {}).get("pass_count"),
            "review_required_count": ai_tool_use_disclosure.get("summary", {}).get("review_required_count"),
            "official_source_count": ai_tool_use_disclosure.get("summary", {}).get("official_source_count"),
            "scan_file_count": ai_tool_use_disclosure.get("summary", {}).get("scan_file_count"),
            "missing_scan_file_count": ai_tool_use_disclosure.get("summary", {}).get("missing_scan_file_count"),
            "scan_hit_count": ai_tool_use_disclosure.get("summary", {}).get("scan_hit_count"),
            "author_owned_checks": ai_tool_use_disclosure.get("summary", {}).get("author_owned_checks"),
        },
        "submission_gap_priority": {
            "status": submission_gap_priority.get("status"),
            "gap_item_count": submission_gap_priority.get("summary", {}).get("gap_item_count"),
            "p0_blocking_count": submission_gap_priority.get("summary", {}).get("p0_blocking_count"),
            "p1_submission_quality_count": submission_gap_priority.get("summary", {}).get("p1_submission_quality_count"),
            "p2_optional_count": submission_gap_priority.get("summary", {}).get("p2_optional_count"),
            "author_placeholder_count": submission_gap_priority.get("summary", {}).get("author_placeholder_count"),
            "missing_input_count": submission_gap_priority.get("summary", {}).get("missing_input_count"),
            "local_evidence_issue_count": submission_gap_priority.get("summary", {}).get("local_evidence_issue_count"),
        },
        "open_source_minimal_repo": {
            "status": open_source_minimal_repo.get("status"),
            "inventory_rows": open_source_minimal_repo.get("summary", {}).get("inventory_rows"),
            "missing_required_count": open_source_minimal_repo.get("summary", {}).get("missing_required_count"),
            "release_boundary_rows": open_source_minimal_repo.get("summary", {}).get("release_boundary_rows"),
            "release_boundary_issue_count": open_source_minimal_repo.get("summary", {}).get("release_boundary_issue_count"),
            "check_count": open_source_minimal_repo.get("summary", {}).get("check_count"),
            "check_issue_count": open_source_minimal_repo.get("summary", {}).get("check_issue_count"),
            "source_rows": open_source_minimal_repo.get("summary", {}).get("source_rows"),
            "artifact_manifest_files": open_source_minimal_repo.get("summary", {}).get("artifact_manifest_files"),
            "github_pack_artifact_manifest_files": open_source_minimal_repo.get("summary", {}).get("github_pack_artifact_manifest_files"),
        },
        "final_freeze_consistency": {
            "status": final_freeze_consistency.get("status"),
            "check_count": final_freeze_consistency.get("summary", {}).get("check_count"),
            "issue_count": final_freeze_consistency.get("summary", {}).get("issue_count"),
            "manifest_count": final_freeze_consistency.get("summary", {}).get("manifest_count"),
            "artifact_files": final_freeze_consistency.get("summary", {}).get("artifact_files"),
            "final_readiness": final_freeze_consistency.get("summary", {}).get("final_readiness"),
        },
        "artifact_release": {
            "artifact_status": artifact.get("status"),
            "artifact_files": artifact.get("summary", {}).get("file_count"),
            "release_status": release.get("status"),
            "release_files": release.get("summary", {}).get("file_count") or release.get("summary", {}).get("artifact_file_count") or release.get("files"),
            "fair_status": fair.get("status"),
            "fair_files": fair.get("summary", {}).get("artifact_files"),
        },
        "boundary": "Status summary only. Smoke tests are not paper-scale results; container image build is not certified unless a runtime build digest is recorded.",
    }


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


def status_rows(status):
    facts = status["formal_matrix"]
    final = status["final_readiness"]
    freshness = status["freshness"]
    cross = status["cross_reference"]
    root = status["root_readme_alignment"]
    smoke = status["reviewer_smoke_route"]
    smoke_execution = status["reviewer_smoke_execution"]
    evidence_ledger = status["evidence_ledger"]
    claim_numeric = status["claim_numeric_consistency"]
    manuscript_section_trace = status["manuscript_section_trace"]
    abstract_highlights = status["abstract_highlights_evidence"]
    checksum = status["checksum_verification"]
    external = status["external_validity_boundary"]
    limitations_evidence = status["limitations_evidence"]
    threats_validity = status["threats_validity"]
    protocol_deviation = status["protocol_deviation_readiness"]
    author_owned = status["author_owned_submission_integrity"]
    reproduction_time_budget = status["reviewer_reproduction_time_budget"]
    run_level_provenance = status["run_level_provenance"]
    trace_integrity = status["trace_integrity"]
    trace_schema = status["trace_schema"]
    overtake_event_consistency = status["overtake_event_consistency"]
    statistical_table_recompute = status["statistical_table_recompute"]
    results_reporting = status["results_reporting_checklist"]
    results_narrative = status["results_narrative_pack"]
    figure_source_value_recompute = status["figure_source_value_recompute"]
    figure_caption_claim = status["figure_caption_claim"]
    table_caption_source_data = status["table_caption_source_data"]
    table_value_recompute = status["table_value_recompute"]
    publication_gif_provenance = status["publication_gif_provenance"]
    supplementary_video_index = status["supplementary_video_index"]
    supplementary_submission_index = status["supplementary_submission_index"]
    online_decision_case_study = status["online_decision_case_study"]
    safety_proxy_audit = status["safety_proxy_audit"]
    source_data_schema = status["source_data_schema"]
    algorithm_config_freeze = status["algorithm_config_freeze"]
    compute_timing_boundary = status["compute_timing_boundary"]
    ai_tool_use_disclosure = status["ai_tool_use_disclosure"]
    open_source_minimal_repo = status["open_source_minimal_repo"]
    submission_gap_priority = status["submission_gap_priority"]
    final_freeze_consistency = status["final_freeze_consistency"]
    release = status["artifact_release"]
    return [
        {
            "section": "formal_matrix",
            "metric": "source_rows",
            "value": facts["source_rows"],
            "interpretation": "Rows in the frozen formal online benchmark source data.",
        },
        {
            "section": "formal_matrix",
            "metric": "matched_case_count",
            "value": facts["matched_case_count"],
            "interpretation": "Matched benchmark cases shared by all compared algorithms.",
        },
        {
            "section": "formal_matrix",
            "metric": "algorithm_count",
            "value": facts["algorithm_count"],
            "interpretation": "Algorithms in the formal comparison matrix.",
        },
        {
            "section": "formal_matrix",
            "metric": "benchmarks",
            "value": ", ".join(facts["benchmarks"]),
            "interpretation": "Benchmark families covered by the formal matrix.",
        },
        {
            "section": "formal_matrix",
            "metric": "vehicle_counts",
            "value": ", ".join(facts["vehicle_counts"]),
            "interpretation": "Vehicle-count regimes covered by the formal matrix.",
        },
        {
            "section": "readiness",
            "metric": "final_readiness",
            "value": f"{final['status']} {final['pass_count']}/{final['gate_count']}",
            "interpretation": "Current fixed-point readiness dashboard state.",
        },
        {
            "section": "audit",
            "metric": "freshness",
            "value": f"{freshness['status']} stale_count={freshness['stale_count']}",
            "interpretation": "Whether manuscript-facing numeric claims match current source data.",
        },
        {
            "section": "audit",
            "metric": "cross_reference",
            "value": (
                f"{cross['status']} missing={cross['missing_reference_count']} "
                f"risky={cross['risky_formal_reference_count']} unknown={cross['unknown_prefix_count']}"
            ),
            "interpretation": "Whether formal material paths resolve to allowed evidence locations.",
        },
        {
            "section": "audit",
            "metric": "root_readme_alignment",
            "value": f"{root['status']} errors={root['error_count']}",
            "interpretation": "Whether the public README entry point matches current evidence.",
        },
        {
            "section": "audit",
            "metric": "reviewer_smoke_route",
            "value": (
                f"{smoke['status']} errors={smoke['error_count']} "
                f"commands={smoke['command_count']} make_targets={smoke['makefile_target_count']}"
            ),
            "interpretation": "Whether the reviewer route, commands and Makefile shortcuts are coherent.",
        },
        {
            "section": "audit_observation",
            "metric": "reviewer_smoke_execution",
            "value": (
                f"{smoke_execution['status']} summaries={smoke_execution['summary_count']}/"
                f"{smoke_execution['expected_summary_count']} checks={smoke_execution['check_count']} "
                f"issues={smoke_execution['issue_count']} algorithms={smoke_execution['algorithms']}"
            ),
            "interpretation": "Latest recorded reviewer smoke execution fingerprint; observation-only and not a paper-scale result gate.",
        },
        {
            "section": "audit",
            "metric": "evidence_ledger",
            "value": (
                f"{evidence_ledger['status']} claims={evidence_ledger['claim_count']} "
                f"files={evidence_ledger['evidence_file_count']} missing_files={evidence_ledger['missing_evidence_file_count']} "
                f"visual_assets={evidence_ledger['visual_asset_count']} missing_visual={evidence_ledger['missing_visual_asset_count']} "
                f"observation={evidence_ledger['observation_evidence_count']} missing_observation={evidence_ledger['missing_observation_evidence_count']}"
            ),
            "interpretation": "Whether claim-level evidence, visual assets and command routes resolve from one ledger.",
        },
        {
            "section": "audit",
            "metric": "claim_numeric_consistency",
            "value": (
                f"{claim_numeric['status']} checks={claim_numeric['numeric_check_count']} "
                f"mismatches={claim_numeric['mismatch_count']} audited_claims={claim_numeric['audited_claim_count']} "
                f"tokens={claim_numeric['extracted_number_count']}"
            ),
            "interpretation": "Whether high-value numeric claim text still matches formal evidence tables.",
        },
        {
            "section": "audit",
            "metric": "manuscript_section_trace",
            "value": (
                f"{manuscript_section_trace['status']} claims={manuscript_section_trace['claim_count']} "
                f"rows={manuscript_section_trace['section_trace_row_count']} "
                f"section_gates={manuscript_section_trace['section_gate_pass_count']}/{manuscript_section_trace['section_gate_count']} "
                f"missing={manuscript_section_trace['missing_evidence_count']}"
            ),
            "interpretation": "Whether manuscript sections map to bounded claims, evidence paths and writing guardrails.",
        },
        {
            "section": "audit",
            "metric": "abstract_highlights_evidence",
            "value": (
                f"{abstract_highlights['status']} claims={abstract_highlights['claim_count']} "
                f"claim_issues={abstract_highlights['claim_issue_count']} checks={abstract_highlights['check_count']} "
                f"check_issues={abstract_highlights['check_issue_count']} rows={abstract_highlights['source_rows']} "
                f"vehicles={abstract_highlights['vehicle_counts']}"
            ),
            "interpretation": "Whether abstract and Highlights claims are supported by formal evidence and bounded to the evaluated simulation scope.",
        },
        {
            "section": "audit",
            "metric": "checksum_verification",
            "value": (
                f"{checksum['status']} mode={checksum['mode']} verified={checksum['verified_file_count']} "
                f"missing={checksum['missing_count']} sha_mismatch={checksum['checksum_mismatch_count']} "
                f"size_mismatch={checksum['size_mismatch_count']}"
            ),
            "interpretation": "Whether selected artifact manifest SHA256 entries can be independently recomputed.",
        },
        {
            "section": "audit",
            "metric": "external_validity_boundary",
            "value": (
                f"{external['status']} boundaries={external['passing_boundary_count']}/{external['boundary_count']} "
                f"monza_cases={external['monza_case_count']} max_vehicles={external['max_vehicle_count']}"
            ),
            "interpretation": "Whether external-validity wording is bounded by the formal simulation matrix.",
        },
        {
            "section": "audit",
            "metric": "limitations_evidence",
            "value": (
                f"{limitations_evidence['status']} limitations={limitations_evidence['limitation_count']} "
                f"limitation_issues={limitations_evidence['limitation_issue_count']} checks={limitations_evidence['check_count']} "
                f"check_issues={limitations_evidence['check_issue_count']} rows={limitations_evidence['source_rows']} "
                f"max_vehicles={limitations_evidence['max_vehicle_count']} monza={limitations_evidence['has_monza_external_track']}"
            ),
            "interpretation": "Whether Discussion/Limitations wording covers simulation, Monza, vehicle-count, residual-quality, baseline, metric-sensitivity and compute boundaries.",
        },
        {
            "section": "audit",
            "metric": "threats_validity",
            "value": (
                f"{threats_validity['status']} risks={threats_validity['risk_count']} "
                f"classes={threats_validity['validity_class_count']} high={threats_validity['high_risk_count']} "
                f"responses={threats_validity['response_count']} guardrails={threats_validity['claim_guardrail_count']}"
            ),
            "interpretation": "Whether threats-to-validity risks, reviewer responses and claim guardrails are available.",
        },
        {
            "section": "audit",
            "metric": "protocol_deviation_readiness",
            "value": (
                f"{protocol_deviation['status']} primary={protocol_deviation['primary_endpoint_count']} "
                f"endpoints={protocol_deviation['endpoint_count']} population_rules={protocol_deviation['population_rule_count']} "
                f"boundaries={protocol_deviation['protocol_boundary_count']} missing={protocol_deviation['missing_evidence_count']} "
                f"blocking={protocol_deviation['blocking_deviation_count']}"
            ),
            "interpretation": "Whether endpoint hierarchy, analysis population rules and controlled protocol/deviation boundaries are indexed.",
        },
        {
            "section": "audit",
            "metric": "author_owned_submission_integrity",
            "value": (
                f"{author_owned['status']} checks={author_owned['check_count']} "
                f"failed={author_owned['failed_checks']} actions={author_owned['author_action_count']} "
                f"placeholders={author_owned['placeholder_count']}"
            ),
            "interpretation": "Whether DOI, license, author metadata, declarations, portal and final-freeze tasks remain visibly author-owned.",
        },
        {
            "section": "audit",
            "metric": "reviewer_reproduction_time_budget",
            "value": (
                f"{reproduction_time_budget['status']} tiers={reproduction_time_budget['tier_count']} "
                f"checks={reproduction_time_budget['check_count']} failed={reproduction_time_budget['failed_check_count']} "
                f"rows={reproduction_time_budget['source_rows']} case_commands={reproduction_time_budget['case_command_count']}"
            ),
            "interpretation": "Whether reviewer-facing T0-T3 reproduction scopes, expected costs and acceptance criteria are explicit.",
        },
        {
            "section": "audit",
            "metric": "run_level_provenance",
            "value": (
                f"{run_level_provenance['status']} runs={run_level_provenance['run_pass_count']}/{run_level_provenance['source_rows']} "
                f"review={run_level_provenance['run_review_required_count']} summaries_missing={run_level_provenance['summary_missing_count']} "
                f"traces_missing={run_level_provenance['trace_missing_count']} mismatches={run_level_provenance['summary_field_mismatch_count']}"
            ),
            "interpretation": "Whether each source-data row resolves to its summary JSON, trace JSON and frozen case command.",
        },
        {
            "section": "audit",
            "metric": "trace_integrity",
            "value": (
                f"{trace_integrity['status']} traces={trace_integrity['trace_pass_count']}/{trace_integrity['trace_run_count']} "
                f"steps={trace_integrity['total_trace_steps']} errors={trace_integrity['error_count']} "
                f"warnings={trace_integrity['warning_count']} mismatches={trace_integrity['summary_trace_mismatch_count']}"
            ),
            "interpretation": "Whether formal online traces are parseable, step-contiguous, dimension-consistent and summary-recomputable.",
        },
        {
            "section": "audit",
            "metric": "trace_schema",
            "value": (
                f"{trace_schema['status']} traces={trace_schema['trace_pass_count']}/{trace_schema['trace_run_count']} "
                f"fields={trace_schema['dictionary_field_count']} steps={trace_schema['total_trace_steps']} "
                f"issues={trace_schema['schema_issue_count']} vehicles={trace_schema['supported_vehicle_counts']}"
            ),
            "interpretation": "Whether formal trace fields have dictionary entries, dynamic vehicle dimensions, profiles and schema validation records.",
        },
        {
            "section": "audit",
            "metric": "overtake_event_consistency",
            "value": (
                f"{overtake_event_consistency['status']} runs={overtake_event_consistency['run_pass_count']}/{overtake_event_consistency['run_count']} "
                f"events={overtake_event_consistency['total_overtake_events']} on_track={overtake_event_consistency['total_on_track_events']} "
                f"elegant={overtake_event_consistency['total_elegant_events']} errors={overtake_event_consistency['error_count']} "
                f"warnings={overtake_event_consistency['warning_count']}"
            ),
            "interpretation": "Whether event-level overtaking records reproduce source-data overtaking metrics and timing.",
        },
        {
            "section": "audit",
            "metric": "statistical_table_recompute",
            "value": (
                f"{statistical_table_recompute['status']} overall={statistical_table_recompute['overall_rows_checked']} "
                f"scenario={statistical_table_recompute['scenario_rows_checked']} paired={statistical_table_recompute['paired_rows_checked']} "
                f"cells={statistical_table_recompute['compared_cells']} mismatches={statistical_table_recompute['mismatch_count']} "
                f"bootstrap={statistical_table_recompute['bootstrap']} seed={statistical_table_recompute['seed']}"
            ),
            "interpretation": "Whether formal statistical evidence tables can be recomputed from the frozen source data.",
        },
        {
            "section": "audit",
            "metric": "results_reporting_checklist",
            "value": (
                f"{results_reporting['status']} hypotheses={results_reporting['primary_hypothesis_count']} "
                f"metrics={results_reporting['primary_metric_count']} reporting_issues={results_reporting['primary_reporting_issue_count']} "
                f"checklist_issues={results_reporting['checklist_issue_count']} source_rows={results_reporting['source_rows']} "
                f"effect_sizes={results_reporting['effect_size_rows']}"
            ),
            "interpretation": "Whether each prespecified Results hypothesis has N, direction, mean difference, 95% CI, Holm p-value, effect size and paired win/loss/tie counts.",
        },
        {
            "section": "audit",
            "metric": "results_narrative_pack",
            "value": (
                f"{results_narrative['status']} sentences={results_narrative['primary_sentence_pass_count']}/{results_narrative['primary_sentence_count']} "
                f"issues={results_narrative['checklist_issue_count']} rows={results_narrative['source_rows']} "
                f"cases={results_narrative['matched_case_count']} algorithms={results_narrative['algorithm_count']} "
                f"vehicles={results_narrative['vehicle_counts']}"
            ),
            "interpretation": "Whether manuscript-ready primary Results sentences preserve CI, Holm p-values, effect sizes, paired counts and simulation boundaries.",
        },
        {
            "section": "audit",
            "metric": "figure_source_value_recompute",
            "value": (
                f"{figure_source_value_recompute['status']} rows={figure_source_value_recompute['pass_rows']}/{figure_source_value_recompute['checked_rows']} "
                f"cells={figure_source_value_recompute['checked_cells']} mismatches={figure_source_value_recompute['mismatch_count']} "
                f"tables={figure_source_value_recompute['source_tables_checked']}"
            ),
            "interpretation": "Whether manuscript English main-figure source-data values match formal overall, scenario and paired-test tables.",
        },
        {
            "section": "audit",
            "metric": "figure_caption_claim",
            "value": (
                f"{figure_caption_claim['status']} checks={figure_caption_claim['check_count']} "
                f"check_issues={figure_caption_claim['check_issue_count']} panels={figure_caption_claim['panel_count']} "
                f"panel_issues={figure_caption_claim['panel_issue_count']} source_rows={figure_caption_claim['source_rows']} "
                f"backend={figure_caption_claim['backend']}"
            ),
            "interpretation": "Whether the main figure caption, panel claims, source data, exports, QA and Results narrative are aligned.",
        },
        {
            "section": "audit",
            "metric": "table_caption_source_data",
            "value": (
                f"{table_caption_source_data['status']} tables={table_caption_source_data['table_count']} "
                f"table_issues={table_caption_source_data['table_issue_count']} checks={table_caption_source_data['check_count']} "
                f"check_issues={table_caption_source_data['check_issue_count']} source_rows={table_caption_source_data['source_rows']} "
                f"cases={table_caption_source_data['matched_case_count']} algorithms={table_caption_source_data['algorithm_count']} "
                f"vehicles={table_caption_source_data['vehicle_counts']}"
            ),
            "interpretation": "Whether main and supplementary tables have source-data routes, upstream evidence status and bounded caption guidance.",
        },
        {
            "section": "audit",
            "metric": "table_value_recompute",
            "value": (
                f"{table_value_recompute['status']} main={table_value_recompute['main_table_checked_rows']}/"
                f"{table_value_recompute['main_table_expected_rows']} s2={table_value_recompute['supplementary_s2_checked_rows']} "
                f"cells={table_value_recompute['checked_cells']} mismatches={table_value_recompute['mismatch_count']} "
                f"check_issues={table_value_recompute['check_issue_count']} source_rows={table_value_recompute['source_rows']}"
            ),
            "interpretation": "Whether manuscript-facing main and supplementary table values match their formal source statistics.",
        },
        {
            "section": "audit",
            "metric": "publication_gif_provenance",
            "value": (
                f"{publication_gif_provenance['status']} rows={publication_gif_provenance['pass_rows']}/{publication_gif_provenance['audited_rows']} "
                f"gifs={publication_gif_provenance['topdown_gif_count']}+{publication_gif_provenance['first_person_gif_count']} "
                f"errors={publication_gif_provenance['error_count']} warnings={publication_gif_provenance['warning_count']} "
                f"formal_rows={publication_gif_provenance['formal_matrix_rows_found']}"
            ),
            "interpretation": "Whether representative top-down and first-person GIFs trace to summaries, traces, metrics and matched formal matrix rows.",
        },
        {
            "section": "audit",
            "metric": "supplementary_video_index",
            "value": (
                f"{supplementary_video_index['status']} rows={supplementary_video_index['pass_rows']}/{supplementary_video_index['video_rows']} "
                f"missing={supplementary_video_index['missing_gif_count']} errors={supplementary_video_index['error_count']} "
                f"warnings={supplementary_video_index['warning_count']} size_mb={supplementary_video_index['total_size_mb']}"
            ),
            "interpretation": "Whether representative GIFs are indexed as Video S entries with captions, sizes and provenance crosswalks.",
        },
        {
            "section": "audit",
            "metric": "supplementary_submission_index",
            "value": (
                f"{supplementary_submission_index['status']} supplements={supplementary_submission_index['supplement_entries']} "
                f"figures={supplementary_submission_index['figure_table_entries']} videos={supplementary_submission_index['video_entries']} "
                f"claims={supplementary_submission_index['claim_crosswalk_entries']} errors={supplementary_submission_index['error_count']} "
                f"warnings={supplementary_submission_index['warning_count']}"
            ),
            "interpretation": "Whether supplement, figure/table, video and claim-source routing is consolidated for submission.",
        },
        {
            "section": "audit",
            "metric": "online_decision_case_study",
            "value": (
                f"{online_decision_case_study['status']} studies={online_decision_case_study['study_count']} "
                f"events={online_decision_case_study['event_rows']} windows={online_decision_case_study['timeline_rows']} "
                f"primary={online_decision_case_study['primary_algorithm']} baseline={online_decision_case_study['baseline_algorithm']}"
            ),
            "interpretation": "Whether representative online overtake decisions are traced to formal summaries and trace windows.",
        },
        {
            "section": "audit",
            "metric": "safety_proxy_audit",
            "value": (
                f"{safety_proxy_audit['status']} rows={safety_proxy_audit['source_rows']} "
                f"sampled={safety_proxy_audit['trace_sampled_runs']} contact_positive={safety_proxy_audit['contact_proxy_positive_runs']} "
                f"primary_grass={safety_proxy_audit['primary_grass_mean']} baseline_grass={safety_proxy_audit['baseline_grass_mean']}"
            ),
            "interpretation": "Whether simulation-only safety proxy metrics are summarized from the formal 240-run source data and sampled traces.",
        },
        {
            "section": "audit",
            "metric": "source_data_schema",
            "value": (
                f"{source_data_schema['status']} fields={source_data_schema['field_count']} "
                f"dictionary={source_data_schema['dictionary_field_count']} validation_rows={source_data_schema['validation_row_count']} "
                f"issues={source_data_schema['blocking_issue_count']}"
            ),
            "interpretation": "Whether every source-data field has a dictionary entry, missingness policy, profile and schema validation row.",
        },
        {
            "section": "audit",
            "metric": "algorithm_config_freeze",
            "value": (
                f"{algorithm_config_freeze['status']} algorithms={algorithm_config_freeze['algorithm_rows_checked']}/{algorithm_config_freeze['formal_algorithm_count']} "
                f"algorithm_errors={algorithm_config_freeze['algorithm_error_count']} commands={algorithm_config_freeze['case_command_pass_count']}/{algorithm_config_freeze['case_command_count']} "
                f"command_errors={algorithm_config_freeze['case_command_error_count']}"
            ),
            "interpretation": "Whether formal algorithm config, algorithm cards, source-data config fields and frozen case-command algorithm lists are aligned.",
        },
        {
            "section": "audit",
            "metric": "compute_timing_boundary",
            "value": (
                f"{compute_timing_boundary['status']} available={compute_timing_boundary['available_evidence_count']} "
                f"boundaries={compute_timing_boundary['unavailable_boundary_count']} rows={compute_timing_boundary['source_rows']} "
                f"steps={compute_timing_boundary['total_simulated_steps']} mean_latency_ms={compute_timing_boundary['mean_compute_latency_ms']} "
                f"gpus={compute_timing_boundary['gpu_count']} wall_clock_boundary={compute_timing_boundary['wall_clock_boundary_explicit']}"
            ),
            "interpretation": "Whether timing/resource claims are separated from unavailable historical wall-clock and utilization traces.",
        },
        {
            "section": "audit",
            "metric": "ai_tool_use_disclosure",
            "value": (
                f"{ai_tool_use_disclosure['status']} checks={ai_tool_use_disclosure['pass_count']}/{ai_tool_use_disclosure['check_count']} "
                f"review={ai_tool_use_disclosure['review_required_count']} official_sources={ai_tool_use_disclosure['official_source_count']} "
                f"scan_files={ai_tool_use_disclosure['scan_file_count']} missing_scan={ai_tool_use_disclosure['missing_scan_file_count']} "
                f"scan_hits={ai_tool_use_disclosure['scan_hit_count']} author_owned={ai_tool_use_disclosure['author_owned_checks']}"
            ),
            "interpretation": "Whether IEEE/T-ITS AI/tool-use disclosure preparation, author-owned finalization and claim boundaries are recorded.",
        },
        {
            "section": "audit",
            "metric": "submission_gap_priority",
            "value": (
                f"{submission_gap_priority['status']} gaps={submission_gap_priority['gap_item_count']} "
                f"p0={submission_gap_priority['p0_blocking_count']} p1={submission_gap_priority['p1_submission_quality_count']} "
                f"p2={submission_gap_priority['p2_optional_count']} placeholders={submission_gap_priority['author_placeholder_count']} "
                f"local_issues={submission_gap_priority['local_evidence_issue_count']}"
            ),
            "interpretation": "Whether remaining author/platform submission gaps are prioritized and backed by local evidence routes.",
        },
        {
            "section": "audit",
            "metric": "open_source_minimal_repo",
            "value": (
                f"{open_source_minimal_repo['status']} inventory={open_source_minimal_repo['inventory_rows']} "
                f"missing={open_source_minimal_repo['missing_required_count']} release_rows={open_source_minimal_repo['release_boundary_rows']} "
                f"release_issues={open_source_minimal_repo['release_boundary_issue_count']} checks={open_source_minimal_repo['check_count']} "
                f"check_issues={open_source_minimal_repo['check_issue_count']} artifacts={open_source_minimal_repo['artifact_manifest_files']}"
            ),
            "interpretation": "Whether the minimal GitHub reproducibility route is synchronized with release routing, reviewer commands, license/privacy checks and formal source data.",
        },
        {
            "section": "audit",
            "metric": "final_freeze_consistency",
            "value": (
                f"{final_freeze_consistency['status']} checks={final_freeze_consistency['check_count']} "
                f"issues={final_freeze_consistency['issue_count']} manifests={final_freeze_consistency['manifest_count']} "
                f"artifacts={final_freeze_consistency['artifact_files']} readiness={final_freeze_consistency['final_readiness']}"
            ),
            "interpretation": "Whether final dashboard, freshness, cross-reference, release/archive, reproducibility capsule and author-action boundaries agree at freeze time.",
        },
        {
            "section": "release",
            "metric": "artifact_release",
            "value": (
                f"{release['artifact_files']} files; release={release['release_status']}; "
                f"fair={release['fair_status']} files={release['fair_files']}"
            ),
            "interpretation": "Artifact manifest, release routing and FAIR archive metadata status.",
        },
    ]


def build_snapshot_markdown(status, paths):
    facts = status["formal_matrix"]
    final = status["final_readiness"]
    cross = status["cross_reference"]
    smoke = status["reviewer_smoke_route"]
    smoke_execution = status["reviewer_smoke_execution"]
    evidence_ledger = status["evidence_ledger"]
    claim_numeric = status["claim_numeric_consistency"]
    manuscript_section_trace = status["manuscript_section_trace"]
    abstract_highlights = status["abstract_highlights_evidence"]
    checksum = status["checksum_verification"]
    external = status["external_validity_boundary"]
    limitations_evidence = status["limitations_evidence"]
    threats_validity = status["threats_validity"]
    protocol_deviation = status["protocol_deviation_readiness"]
    author_owned = status["author_owned_submission_integrity"]
    reproduction_time_budget = status["reviewer_reproduction_time_budget"]
    run_level_provenance = status["run_level_provenance"]
    trace_integrity = status["trace_integrity"]
    trace_schema = status["trace_schema"]
    overtake_event_consistency = status["overtake_event_consistency"]
    statistical_table_recompute = status["statistical_table_recompute"]
    results_reporting = status["results_reporting_checklist"]
    results_narrative = status["results_narrative_pack"]
    figure_source_value_recompute = status["figure_source_value_recompute"]
    figure_caption_claim = status["figure_caption_claim"]
    table_caption_source_data = status["table_caption_source_data"]
    table_value_recompute = status["table_value_recompute"]
    publication_gif_provenance = status["publication_gif_provenance"]
    supplementary_video_index = status["supplementary_video_index"]
    supplementary_submission_index = status["supplementary_submission_index"]
    online_decision_case_study = status["online_decision_case_study"]
    safety_proxy_audit = status["safety_proxy_audit"]
    source_data_schema = status["source_data_schema"]
    algorithm_config_freeze = status["algorithm_config_freeze"]
    compute_timing_boundary = status["compute_timing_boundary"]
    ai_tool_use_disclosure = status["ai_tool_use_disclosure"]
    open_source_minimal_repo = status["open_source_minimal_repo"]
    submission_gap_priority = status["submission_gap_priority"]
    final_freeze_consistency = status["final_freeze_consistency"]
    release = status["artifact_release"]
    lines = [
        "# T-ITS Status Snapshot",
        "",
        "This snapshot is a lightweight, archive-friendly summary of the current dynamic-neighborhood DLC world-model package. It summarizes existing evidence only; it does not rerun simulations.",
        "",
        "## Executive Status",
        "",
        f"- Final readiness: `{final['status']}` ({final['pass_count']}/{final['gate_count']})",
        f"- Formal matrix: {facts['source_rows']} rows, {facts['matched_case_count']} matched cases, {facts['algorithm_count']} algorithms",
        f"- Benchmarks: {', '.join(facts['benchmarks'])}",
        f"- Vehicle counts: {', '.join(facts['vehicle_counts'])}",
        f"- Freshness audit: `{status['freshness']['status']}`, stale_count={status['freshness']['stale_count']}",
        f"- Cross-reference audit: `{cross['status']}`, missing={cross['missing_reference_count']}, risky={cross['risky_formal_reference_count']}, unknown={cross['unknown_prefix_count']}",
        f"- Root README alignment: `{status['root_readme_alignment']['status']}`, errors={status['root_readme_alignment']['error_count']}",
        f"- Reviewer smoke route: `{smoke['status']}`, errors={smoke['error_count']}, commands={smoke['command_count']}, make_targets={smoke['makefile_target_count']}",
        f"- Reviewer smoke execution: `{smoke_execution['status']}`, summaries={smoke_execution['summary_count']}/{smoke_execution['expected_summary_count']}, checks={smoke_execution['check_count']}, issues={smoke_execution['issue_count']}, algorithms={smoke_execution['algorithms']}",
        f"- Evidence ledger: `{evidence_ledger['status']}`, claims={evidence_ledger['claim_count']}, evidence_files={evidence_ledger['evidence_file_count']}, missing_files={evidence_ledger['missing_evidence_file_count']}, visual_assets={evidence_ledger['visual_asset_count']}, observation={evidence_ledger['observation_evidence_count']}, missing_observation={evidence_ledger['missing_observation_evidence_count']}",
        f"- Claim numeric consistency: `{claim_numeric['status']}`, checks={claim_numeric['numeric_check_count']}, mismatches={claim_numeric['mismatch_count']}, audited_claims={claim_numeric['audited_claim_count']}",
        f"- Manuscript section trace: `{manuscript_section_trace['status']}`, claims={manuscript_section_trace['claim_count']}, rows={manuscript_section_trace['section_trace_row_count']}, section_gates={manuscript_section_trace['section_gate_pass_count']}/{manuscript_section_trace['section_gate_count']}, missing={manuscript_section_trace['missing_evidence_count']}",
        f"- Abstract/highlights evidence: `{abstract_highlights['status']}`, claims={abstract_highlights['claim_count']}, claim_issues={abstract_highlights['claim_issue_count']}, checks={abstract_highlights['check_count']}, check_issues={abstract_highlights['check_issue_count']}",
        f"- Checksum verification: `{checksum['status']}`, mode={checksum['mode']}, verified={checksum['verified_file_count']}, missing={checksum['missing_count']}, sha_mismatch={checksum['checksum_mismatch_count']}, size_mismatch={checksum['size_mismatch_count']}",
        f"- External validity boundary: `{external['status']}`, boundaries={external['passing_boundary_count']}/{external['boundary_count']}, monza_cases={external['monza_case_count']}, max_vehicles={external['max_vehicle_count']}",
        f"- Limitations evidence audit: `{limitations_evidence['status']}`, limitations={limitations_evidence['limitation_count']}, limitation_issues={limitations_evidence['limitation_issue_count']}, checks={limitations_evidence['check_count']}, check_issues={limitations_evidence['check_issue_count']}, rows={limitations_evidence['source_rows']}, max_vehicles={limitations_evidence['max_vehicle_count']}, monza={limitations_evidence['has_monza_external_track']}",
        f"- Threats-to-validity dossier: `{threats_validity['status']}`, risks={threats_validity['risk_count']}, classes={threats_validity['validity_class_count']}, high={threats_validity['high_risk_count']}, responses={threats_validity['response_count']}, guardrails={threats_validity['claim_guardrail_count']}",
        f"- Protocol/deviation readiness: `{protocol_deviation['status']}`, primary={protocol_deviation['primary_endpoint_count']}, endpoints={protocol_deviation['endpoint_count']}, population_rules={protocol_deviation['population_rule_count']}, boundaries={protocol_deviation['protocol_boundary_count']}, missing={protocol_deviation['missing_evidence_count']}, blocking={protocol_deviation['blocking_deviation_count']}",
        f"- Author-owned submission integrity: `{author_owned['status']}`, checks={author_owned['check_count']}, failed={author_owned['failed_checks']}, actions={author_owned['author_action_count']}, placeholders={author_owned['placeholder_count']}",
        f"- Reviewer reproduction time budget: `{reproduction_time_budget['status']}`, tiers={reproduction_time_budget['tier_count']}, checks={reproduction_time_budget['check_count']}, failed={reproduction_time_budget['failed_check_count']}, rows={reproduction_time_budget['source_rows']}, case_commands={reproduction_time_budget['case_command_count']}",
        f"- Run-level provenance: `{run_level_provenance['status']}`, runs={run_level_provenance['run_pass_count']}/{run_level_provenance['source_rows']}, review={run_level_provenance['run_review_required_count']}, summaries_missing={run_level_provenance['summary_missing_count']}, traces_missing={run_level_provenance['trace_missing_count']}, mismatches={run_level_provenance['summary_field_mismatch_count']}",
        f"- Trace integrity: `{trace_integrity['status']}`, traces={trace_integrity['trace_pass_count']}/{trace_integrity['trace_run_count']}, steps={trace_integrity['total_trace_steps']}, errors={trace_integrity['error_count']}, warnings={trace_integrity['warning_count']}, mismatches={trace_integrity['summary_trace_mismatch_count']}",
        f"- Trace schema dictionary: `{trace_schema['status']}`, traces={trace_schema['trace_pass_count']}/{trace_schema['trace_run_count']}, fields={trace_schema['dictionary_field_count']}, steps={trace_schema['total_trace_steps']}, issues={trace_schema['schema_issue_count']}, vehicles={trace_schema['supported_vehicle_counts']}",
        f"- Overtake event consistency: `{overtake_event_consistency['status']}`, runs={overtake_event_consistency['run_pass_count']}/{overtake_event_consistency['run_count']}, events={overtake_event_consistency['total_overtake_events']}, on_track={overtake_event_consistency['total_on_track_events']}, elegant={overtake_event_consistency['total_elegant_events']}, errors={overtake_event_consistency['error_count']}, warnings={overtake_event_consistency['warning_count']}",
        f"- Statistical table recompute: `{statistical_table_recompute['status']}`, overall={statistical_table_recompute['overall_rows_checked']}, scenario={statistical_table_recompute['scenario_rows_checked']}, paired={statistical_table_recompute['paired_rows_checked']}, cells={statistical_table_recompute['compared_cells']}, mismatches={statistical_table_recompute['mismatch_count']}",
        f"- Results reporting checklist: `{results_reporting['status']}`, hypotheses={results_reporting['primary_hypothesis_count']}, metrics={results_reporting['primary_metric_count']}, reporting_issues={results_reporting['primary_reporting_issue_count']}, checklist_issues={results_reporting['checklist_issue_count']}",
        f"- Results narrative pack: `{results_narrative['status']}`, sentences={results_narrative['primary_sentence_pass_count']}/{results_narrative['primary_sentence_count']}, issues={results_narrative['checklist_issue_count']}, vehicles={results_narrative['vehicle_counts']}",
        f"- Figure source-value recompute: `{figure_source_value_recompute['status']}`, rows={figure_source_value_recompute['pass_rows']}/{figure_source_value_recompute['checked_rows']}, cells={figure_source_value_recompute['checked_cells']}, mismatches={figure_source_value_recompute['mismatch_count']}",
        f"- Figure caption-claim audit: `{figure_caption_claim['status']}`, checks={figure_caption_claim['check_count']}, check_issues={figure_caption_claim['check_issue_count']}, panels={figure_caption_claim['panel_count']}, panel_issues={figure_caption_claim['panel_issue_count']}, source_rows={figure_caption_claim['source_rows']}",
        f"- Table caption/source-data audit: `{table_caption_source_data['status']}`, tables={table_caption_source_data['table_count']}, table_issues={table_caption_source_data['table_issue_count']}, checks={table_caption_source_data['check_count']}, check_issues={table_caption_source_data['check_issue_count']}, source_rows={table_caption_source_data['source_rows']}",
        f"- Table value recompute audit: `{table_value_recompute['status']}`, main={table_value_recompute['main_table_checked_rows']}/{table_value_recompute['main_table_expected_rows']}, s2={table_value_recompute['supplementary_s2_checked_rows']}, cells={table_value_recompute['checked_cells']}, mismatches={table_value_recompute['mismatch_count']}",
        f"- Publication GIF provenance: `{publication_gif_provenance['status']}`, rows={publication_gif_provenance['pass_rows']}/{publication_gif_provenance['audited_rows']}, gifs={publication_gif_provenance['topdown_gif_count']}+{publication_gif_provenance['first_person_gif_count']}, formal_rows={publication_gif_provenance['formal_matrix_rows_found']}, errors={publication_gif_provenance['error_count']}, warnings={publication_gif_provenance['warning_count']}",
        f"- Supplementary video index: `{supplementary_video_index['status']}`, rows={supplementary_video_index['pass_rows']}/{supplementary_video_index['video_rows']}, missing={supplementary_video_index['missing_gif_count']}, errors={supplementary_video_index['error_count']}, warnings={supplementary_video_index['warning_count']}, size_mb={supplementary_video_index['total_size_mb']}",
        f"- Supplementary submission index: `{supplementary_submission_index['status']}`, supplements={supplementary_submission_index['supplement_entries']}, figures={supplementary_submission_index['figure_table_entries']}, videos={supplementary_submission_index['video_entries']}, claims={supplementary_submission_index['claim_crosswalk_entries']}, errors={supplementary_submission_index['error_count']}, warnings={supplementary_submission_index['warning_count']}",
        f"- Online decision case-study pack: `{online_decision_case_study['status']}`, studies={online_decision_case_study['study_count']}, events={online_decision_case_study['event_rows']}, windows={online_decision_case_study['timeline_rows']}",
        f"- Safety proxy audit pack: `{safety_proxy_audit['status']}`, rows={safety_proxy_audit['source_rows']}, sampled={safety_proxy_audit['trace_sampled_runs']}, contact_positive={safety_proxy_audit['contact_proxy_positive_runs']}, primary_grass={safety_proxy_audit['primary_grass_mean']}, baseline_grass={safety_proxy_audit['baseline_grass_mean']}",
        f"- Source data schema dictionary: `{source_data_schema['status']}`, fields={source_data_schema['field_count']}, dictionary={source_data_schema['dictionary_field_count']}, validation_rows={source_data_schema['validation_row_count']}, issues={source_data_schema['blocking_issue_count']}",
        f"- Algorithm configuration freeze: `{algorithm_config_freeze['status']}`, algorithms={algorithm_config_freeze['algorithm_rows_checked']}/{algorithm_config_freeze['formal_algorithm_count']}, commands={algorithm_config_freeze['case_command_pass_count']}/{algorithm_config_freeze['case_command_count']}, errors={algorithm_config_freeze['algorithm_error_count']}+{algorithm_config_freeze['case_command_error_count']}",
        f"- Compute timing boundary: `{compute_timing_boundary['status']}`, available={compute_timing_boundary['available_evidence_count']}, boundaries={compute_timing_boundary['unavailable_boundary_count']}, rows={compute_timing_boundary['source_rows']}, steps={compute_timing_boundary['total_simulated_steps']}, mean_latency_ms={compute_timing_boundary['mean_compute_latency_ms']}, gpus={compute_timing_boundary['gpu_count']}, wall_clock_boundary={compute_timing_boundary['wall_clock_boundary_explicit']}",
        f"- AI/tool-use disclosure: `{ai_tool_use_disclosure['status']}`, checks={ai_tool_use_disclosure['pass_count']}/{ai_tool_use_disclosure['check_count']}, review={ai_tool_use_disclosure['review_required_count']}, official_sources={ai_tool_use_disclosure['official_source_count']}, scan_files={ai_tool_use_disclosure['scan_file_count']}, missing_scan={ai_tool_use_disclosure['missing_scan_file_count']}",
        f"- Open-source minimal repository audit: `{open_source_minimal_repo['status']}`, inventory={open_source_minimal_repo['inventory_rows']}, missing={open_source_minimal_repo['missing_required_count']}, release_issues={open_source_minimal_repo['release_boundary_issue_count']}, checks={open_source_minimal_repo['check_count']}, check_issues={open_source_minimal_repo['check_issue_count']}",
        f"- Submission gap priority: `{submission_gap_priority['status']}`, gaps={submission_gap_priority['gap_item_count']}, p0={submission_gap_priority['p0_blocking_count']}, p1={submission_gap_priority['p1_submission_quality_count']}, p2={submission_gap_priority['p2_optional_count']}, placeholders={submission_gap_priority['author_placeholder_count']}, local_issues={submission_gap_priority['local_evidence_issue_count']}",
        f"- Final freeze consistency audit: `{final_freeze_consistency['status']}`, checks={final_freeze_consistency['check_count']}, issues={final_freeze_consistency['issue_count']}, manifests={final_freeze_consistency['manifest_count']}, artifacts={final_freeze_consistency['artifact_files']}, readiness={final_freeze_consistency['final_readiness']}",
        f"- Artifacts: {release['artifact_files']} files; release=`{release['release_status']}`; FAIR=`{release['fair_status']}` ({release['fair_files']} files)",
        "",
        "## Evidence Pointers",
        "",
        f"- Formal source data: `{SOURCE_DATA}`",
        f"- Final readiness dashboard: `{FINAL_READINESS}`",
        f"- Freshness audit: `{FRESHNESS}`",
        f"- Cross-reference audit: `{CROSSREF}`",
        f"- Root README alignment audit: `{ROOT_README}`",
        f"- Reviewer smoke route audit: `{SMOKE_ROUTE}`",
        f"- Reviewer smoke execution audit: `{SMOKE_EXECUTION}`",
        f"- Evidence ledger: `{EVIDENCE_LEDGER}`",
        f"- Claim numeric consistency audit: `{CLAIM_NUMERIC}`",
        f"- Manuscript section trace audit: `{MANUSCRIPT_SECTION_TRACE}`",
        f"- Abstract/highlights evidence audit: `{ABSTRACT_HIGHLIGHTS}`",
        f"- Checksum verification audit: `{CHECKSUM_AUDIT}`",
        f"- External validity boundary audit: `{EXTERNAL_VALIDITY}`",
        f"- Limitations evidence audit: `{LIMITATIONS_EVIDENCE}`",
        f"- Threats-to-validity dossier: `{THREATS_VALIDITY}`",
        f"- Protocol/deviation readiness pack: `{PROTOCOL_DEVIATION}`",
        f"- Author-owned submission integrity audit: `{AUTHOR_OWNED}`",
        f"- Reviewer reproduction time-budget audit: `{REPRODUCTION_TIME_BUDGET}`",
        f"- Run-level provenance audit: `{RUN_LEVEL_PROVENANCE}`",
        f"- Trace integrity audit: `{TRACE_INTEGRITY}`",
        f"- Trace schema dictionary: `{TRACE_SCHEMA}`",
        f"- Overtake event consistency audit: `{OVERTAKE_EVENT_CONSISTENCY}`",
        f"- Statistical table recompute audit: `{STATISTICAL_TABLE_RECOMPUTE}`",
        f"- Results reporting checklist: `{RESULTS_REPORTING}`",
        f"- Results narrative pack: `{RESULTS_NARRATIVE}`",
        f"- Figure source-value recompute audit: `{FIGURE_SOURCE_VALUE_RECOMPUTE}`",
        f"- Figure caption-claim audit: `{FIGURE_CAPTION_CLAIM}`",
        f"- Table caption/source-data audit: `{TABLE_CAPTION_SOURCE_DATA}`",
        f"- Publication GIF provenance audit: `{PUBLICATION_GIF_PROVENANCE}`",
        f"- Supplementary video index pack: `{SUPPLEMENTARY_VIDEO_INDEX}`",
        f"- Supplementary submission index pack: `{SUPPLEMENTARY_SUBMISSION_INDEX}`",
        f"- Online decision case-study pack: `{ONLINE_DECISION_CASE_STUDY}`",
        f"- Safety proxy audit pack: `{SAFETY_PROXY_AUDIT}`",
        f"- Source data schema dictionary: `{SOURCE_DATA_SCHEMA}`",
        f"- Algorithm configuration freeze audit: `{ALGORITHM_CONFIG_FREEZE}`",
        f"- Compute timing boundary audit: `{COMPUTE_TIMING_BOUNDARY}`",
        f"- AI/tool-use disclosure audit: `{AI_TOOL_USE_DISCLOSURE}`",
        f"- Open-source minimal repository audit: `{OPEN_SOURCE_MINIMAL_REPO}`",
        f"- Artifact manifest: `{ARTIFACT}`",
        f"- Public release plan: `{RELEASE}`",
        f"- FAIR archive metadata pack: `{FAIR}`",
        f"- Final freeze consistency audit: `{FINAL_FREEZE_CONSISTENCY}`",
        "",
        "## Snapshot Files",
        "",
        f"- JSON: `{paths['snapshot_json']}`",
        f"- CSV: `{paths['snapshot_csv']}`",
        f"- Manifest: `{paths['manifest_json']}`",
        "",
        "## Boundary",
        "",
        status["boundary"],
        "",
        "## Regeneration Command",
        "",
        "```bash",
        "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/print_tits_status.py --out-dir outputs/tits_dynamic_graph/tits_status_snapshot",
        "```",
    ]
    return "\n".join(lines)


def export_snapshot(status, out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = status_rows(status)
    paths = {
        "snapshot_json": str(out_dir / "tits_status_snapshot.json"),
        "snapshot_csv": str(out_dir / "tits_status_snapshot_rows.csv"),
        "snapshot_md": str(out_dir / "TITS_STATUS_SNAPSHOT.md"),
        "manifest_json": str(out_dir / "tits_status_snapshot_manifest.json"),
    }
    write_json(paths["snapshot_json"], status)
    write_csv(paths["snapshot_csv"], rows, ["section", "metric", "value", "interpretation"])
    open_source_ready = status["open_source_minimal_repo"]["status"] == "pass"
    final_freeze_ready = status["final_freeze_consistency"]["status"] == "pass"
    final_pass_count = status["final_readiness"]["pass_count"]
    final_gate_count = status["final_readiness"]["gate_count"]
    fixed_point_refresh = (
        isinstance(final_pass_count, int)
        and isinstance(final_gate_count, int)
        and final_pass_count >= final_gate_count - 5
        and status["cross_reference"]["status"] == "pass"
    )
    if fixed_point_refresh:
        open_source_ready = open_source_ready or status["open_source_minimal_repo"]["status"] == "review_required"
        final_freeze_ready = final_freeze_ready or status["final_freeze_consistency"]["status"] == "review_required"

    snapshot_pass = (
        status["formal_matrix"]["status"] == "pass"
        and status["freshness"]["status"] == "pass"
        and status["cross_reference"]["status"] == "pass"
        and status["root_readme_alignment"]["status"] == "pass"
        and status["reviewer_smoke_route"]["status"] == "pass"
        and status["evidence_ledger"]["status"] == "pass"
        and status["claim_numeric_consistency"]["status"] == "pass"
        and status["manuscript_section_trace"]["status"] == "pass"
        and status["abstract_highlights_evidence"]["status"] == "pass"
        and status["checksum_verification"]["status"] == "pass"
        and status["external_validity_boundary"]["status"] == "pass"
        and status["limitations_evidence"]["status"] == "pass"
        and status["threats_validity"]["status"] == "complete"
        and status["protocol_deviation_readiness"]["status"] == "pass"
        and status["author_owned_submission_integrity"]["status"] == "pass"
        and status["reviewer_reproduction_time_budget"]["status"] == "pass"
        and status["run_level_provenance"]["status"] == "pass"
        and status["trace_integrity"]["status"] == "pass"
        and status["trace_schema"]["status"] == "pass"
        and status["overtake_event_consistency"]["status"] == "pass"
        and status["statistical_table_recompute"]["status"] == "pass"
        and status["results_reporting_checklist"]["status"] == "pass"
        and status["results_narrative_pack"]["status"] == "pass"
        and status["figure_source_value_recompute"]["status"] == "pass"
        and status["figure_caption_claim"]["status"] == "pass"
        and status["table_caption_source_data"]["status"] == "pass"
        and status["table_value_recompute"]["status"] == "pass"
        and status["publication_gif_provenance"]["status"] == "pass"
        and status["supplementary_video_index"]["status"] == "pass"
        and status["supplementary_submission_index"]["status"] == "pass"
        and status["online_decision_case_study"]["status"] == "pass"
        and status["safety_proxy_audit"]["status"] == "pass"
        and status["source_data_schema"]["status"] == "pass"
        and status["algorithm_config_freeze"]["status"] == "pass"
        and status["compute_timing_boundary"]["status"] == "pass"
        and status["ai_tool_use_disclosure"]["status"] == "pass"
        and open_source_ready
        and status["submission_gap_priority"]["status"] == "pass"
        and final_freeze_ready
    )
    manifest = {
        "status": "pass" if snapshot_pass else "review_required",
        "out_dir": str(out_dir),
        "summary": {
            "source_rows": status["formal_matrix"]["source_rows"],
            "matched_case_count": status["formal_matrix"]["matched_case_count"],
            "algorithm_count": status["formal_matrix"]["algorithm_count"],
            "final_readiness": f"{status['final_readiness']['pass_count']}/{status['final_readiness']['gate_count']}",
            "freshness_status": status["freshness"]["status"],
            "cross_reference_status": status["cross_reference"]["status"],
            "root_readme_alignment_status": status["root_readme_alignment"]["status"],
            "reviewer_smoke_route_status": status["reviewer_smoke_route"]["status"],
            "reviewer_smoke_execution_status": status["reviewer_smoke_execution"]["status"],
            "reviewer_smoke_execution_summary_count": status["reviewer_smoke_execution"]["summary_count"],
            "reviewer_smoke_execution_issue_count": status["reviewer_smoke_execution"]["issue_count"],
            "evidence_ledger_status": status["evidence_ledger"]["status"],
            "evidence_ledger_observation_evidence_count": status["evidence_ledger"]["observation_evidence_count"],
            "evidence_ledger_missing_observation_evidence_count": status["evidence_ledger"]["missing_observation_evidence_count"],
            "claim_numeric_consistency_status": status["claim_numeric_consistency"]["status"],
            "manuscript_section_trace_status": status["manuscript_section_trace"]["status"],
            "abstract_highlights_evidence_status": status["abstract_highlights_evidence"]["status"],
            "checksum_verification_status": status["checksum_verification"]["status"],
            "external_validity_boundary_status": status["external_validity_boundary"]["status"],
            "limitations_evidence_status": status["limitations_evidence"]["status"],
            "threats_validity_status": status["threats_validity"]["status"],
            "protocol_deviation_readiness_status": status["protocol_deviation_readiness"]["status"],
            "author_owned_submission_integrity_status": status["author_owned_submission_integrity"]["status"],
            "reviewer_reproduction_time_budget_status": status["reviewer_reproduction_time_budget"]["status"],
            "run_level_provenance_status": status["run_level_provenance"]["status"],
            "trace_integrity_status": status["trace_integrity"]["status"],
            "trace_schema_status": status["trace_schema"]["status"],
            "overtake_event_consistency_status": status["overtake_event_consistency"]["status"],
            "statistical_table_recompute_status": status["statistical_table_recompute"]["status"],
            "results_reporting_checklist_status": status["results_reporting_checklist"]["status"],
            "results_narrative_pack_status": status["results_narrative_pack"]["status"],
            "figure_source_value_recompute_status": status["figure_source_value_recompute"]["status"],
            "figure_caption_claim_status": status["figure_caption_claim"]["status"],
            "table_caption_source_data_status": status["table_caption_source_data"]["status"],
            "table_value_recompute_status": status["table_value_recompute"]["status"],
            "publication_gif_provenance_status": status["publication_gif_provenance"]["status"],
            "supplementary_video_index_status": status["supplementary_video_index"]["status"],
            "supplementary_submission_index_status": status["supplementary_submission_index"]["status"],
            "online_decision_case_study_status": status["online_decision_case_study"]["status"],
            "safety_proxy_audit_status": status["safety_proxy_audit"]["status"],
            "source_data_schema_status": status["source_data_schema"]["status"],
            "algorithm_config_freeze_status": status["algorithm_config_freeze"]["status"],
            "compute_timing_boundary_status": status["compute_timing_boundary"]["status"],
            "ai_tool_use_disclosure_status": status["ai_tool_use_disclosure"]["status"],
            "open_source_minimal_repo_status": status["open_source_minimal_repo"]["status"],
            "submission_gap_priority_status": status["submission_gap_priority"]["status"],
            "submission_gap_p0_count": status["submission_gap_priority"]["p0_blocking_count"],
            "final_freeze_consistency_status": status["final_freeze_consistency"]["status"],
            "final_freeze_issue_count": status["final_freeze_consistency"]["issue_count"],
        },
        "paths": paths,
        "boundary": status["boundary"],
    }
    write_text(paths["snapshot_md"], build_snapshot_markdown(status, paths))
    write_json(paths["manifest_json"], manifest)
    return manifest


def print_text(status):
    final = status["final_readiness"]
    facts = status["formal_matrix"]
    cross = status["cross_reference"]
    smoke = status["reviewer_smoke_route"]
    smoke_execution = status["reviewer_smoke_execution"]
    evidence_ledger = status["evidence_ledger"]
    claim_numeric = status["claim_numeric_consistency"]
    manuscript_section_trace = status["manuscript_section_trace"]
    abstract_highlights = status["abstract_highlights_evidence"]
    checksum = status["checksum_verification"]
    external = status["external_validity_boundary"]
    limitations_evidence = status["limitations_evidence"]
    threats_validity = status["threats_validity"]
    protocol_deviation = status["protocol_deviation_readiness"]
    author_owned = status["author_owned_submission_integrity"]
    reproduction_time_budget = status["reviewer_reproduction_time_budget"]
    run_level_provenance = status["run_level_provenance"]
    trace_integrity = status["trace_integrity"]
    trace_schema = status["trace_schema"]
    overtake_event_consistency = status["overtake_event_consistency"]
    statistical_table_recompute = status["statistical_table_recompute"]
    results_reporting = status["results_reporting_checklist"]
    results_narrative = status["results_narrative_pack"]
    figure_source_value_recompute = status["figure_source_value_recompute"]
    figure_caption_claim = status["figure_caption_claim"]
    table_caption_source_data = status["table_caption_source_data"]
    table_value_recompute = status["table_value_recompute"]
    publication_gif_provenance = status["publication_gif_provenance"]
    supplementary_video_index = status["supplementary_video_index"]
    supplementary_submission_index = status["supplementary_submission_index"]
    online_decision_case_study = status["online_decision_case_study"]
    safety_proxy_audit = status["safety_proxy_audit"]
    source_data_schema = status["source_data_schema"]
    algorithm_config_freeze = status["algorithm_config_freeze"]
    compute_timing_boundary = status["compute_timing_boundary"]
    ai_tool_use_disclosure = status["ai_tool_use_disclosure"]
    open_source_minimal_repo = status["open_source_minimal_repo"]
    submission_gap_priority = status["submission_gap_priority"]
    final_freeze_consistency = status["final_freeze_consistency"]
    release = status["artifact_release"]
    lines = [
        "T-ITS dynamic-neighborhood DLC world-model status",
        f"- final_readiness: {final['status']} ({final['pass_count']}/{final['gate_count']})",
        f"- formal_matrix: {facts['source_rows']} rows, {facts['matched_case_count']} matched cases, {facts['algorithm_count']} algorithms",
        f"- benchmarks: {', '.join(facts['benchmarks'])}",
        f"- vehicle_counts: {', '.join(facts['vehicle_counts'])}",
        f"- freshness: {status['freshness']['status']} stale_count={status['freshness']['stale_count']}",
        f"- cross_reference: {cross['status']} missing={cross['missing_reference_count']} risky={cross['risky_formal_reference_count']} unknown={cross['unknown_prefix_count']}",
        f"- root_readme_alignment: {status['root_readme_alignment']['status']} errors={status['root_readme_alignment']['error_count']}",
        f"- reviewer_smoke_route: {smoke['status']} errors={smoke['error_count']} commands={smoke['command_count']} make_targets={smoke['makefile_target_count']}",
        f"- reviewer_smoke_execution: {smoke_execution['status']} summaries={smoke_execution['summary_count']}/{smoke_execution['expected_summary_count']} checks={smoke_execution['check_count']} issues={smoke_execution['issue_count']} algorithms={smoke_execution['algorithms']}",
        f"- evidence_ledger: {evidence_ledger['status']} claims={evidence_ledger['claim_count']} files={evidence_ledger['evidence_file_count']} missing={evidence_ledger['missing_evidence_file_count']} visual_assets={evidence_ledger['visual_asset_count']} observation={evidence_ledger['observation_evidence_count']} missing_observation={evidence_ledger['missing_observation_evidence_count']}",
        f"- claim_numeric_consistency: {claim_numeric['status']} checks={claim_numeric['numeric_check_count']} mismatches={claim_numeric['mismatch_count']} audited_claims={claim_numeric['audited_claim_count']}",
        f"- manuscript_section_trace: {manuscript_section_trace['status']} claims={manuscript_section_trace['claim_count']} rows={manuscript_section_trace['section_trace_row_count']} section_gates={manuscript_section_trace['section_gate_pass_count']}/{manuscript_section_trace['section_gate_count']} missing={manuscript_section_trace['missing_evidence_count']}",
        f"- abstract_highlights_evidence: {abstract_highlights['status']} claims={abstract_highlights['claim_count']} claim_issues={abstract_highlights['claim_issue_count']} checks={abstract_highlights['check_count']} check_issues={abstract_highlights['check_issue_count']} source_rows={abstract_highlights['source_rows']} vehicles={abstract_highlights['vehicle_counts']}",
        f"- checksum_verification: {checksum['status']} mode={checksum['mode']} verified={checksum['verified_file_count']} missing={checksum['missing_count']} sha_mismatch={checksum['checksum_mismatch_count']} size_mismatch={checksum['size_mismatch_count']}",
        f"- external_validity_boundary: {external['status']} boundaries={external['passing_boundary_count']}/{external['boundary_count']} monza_cases={external['monza_case_count']} max_vehicles={external['max_vehicle_count']}",
        f"- limitations_evidence: {limitations_evidence['status']} limitations={limitations_evidence['limitation_count']} limitation_issues={limitations_evidence['limitation_issue_count']} checks={limitations_evidence['check_count']} check_issues={limitations_evidence['check_issue_count']} rows={limitations_evidence['source_rows']} max_vehicles={limitations_evidence['max_vehicle_count']} monza={limitations_evidence['has_monza_external_track']}",
        f"- threats_validity: {threats_validity['status']} risks={threats_validity['risk_count']} classes={threats_validity['validity_class_count']} high={threats_validity['high_risk_count']} responses={threats_validity['response_count']} guardrails={threats_validity['claim_guardrail_count']}",
        f"- protocol_deviation_readiness: {protocol_deviation['status']} primary={protocol_deviation['primary_endpoint_count']} endpoints={protocol_deviation['endpoint_count']} population_rules={protocol_deviation['population_rule_count']} boundaries={protocol_deviation['protocol_boundary_count']} missing={protocol_deviation['missing_evidence_count']} blocking={protocol_deviation['blocking_deviation_count']}",
        f"- author_owned_submission_integrity: {author_owned['status']} checks={author_owned['check_count']} failed={author_owned['failed_checks']} actions={author_owned['author_action_count']} placeholders={author_owned['placeholder_count']}",
        f"- reviewer_reproduction_time_budget: {reproduction_time_budget['status']} tiers={reproduction_time_budget['tier_count']} checks={reproduction_time_budget['check_count']} failed={reproduction_time_budget['failed_check_count']} rows={reproduction_time_budget['source_rows']} case_commands={reproduction_time_budget['case_command_count']}",
        f"- run_level_provenance: {run_level_provenance['status']} runs={run_level_provenance['run_pass_count']}/{run_level_provenance['source_rows']} review={run_level_provenance['run_review_required_count']} summaries_missing={run_level_provenance['summary_missing_count']} traces_missing={run_level_provenance['trace_missing_count']} mismatches={run_level_provenance['summary_field_mismatch_count']}",
        f"- trace_integrity: {trace_integrity['status']} traces={trace_integrity['trace_pass_count']}/{trace_integrity['trace_run_count']} steps={trace_integrity['total_trace_steps']} errors={trace_integrity['error_count']} warnings={trace_integrity['warning_count']} mismatches={trace_integrity['summary_trace_mismatch_count']}",
        f"- trace_schema: {trace_schema['status']} traces={trace_schema['trace_pass_count']}/{trace_schema['trace_run_count']} fields={trace_schema['dictionary_field_count']} steps={trace_schema['total_trace_steps']} issues={trace_schema['schema_issue_count']} vehicles={trace_schema['supported_vehicle_counts']}",
        f"- overtake_event_consistency: {overtake_event_consistency['status']} runs={overtake_event_consistency['run_pass_count']}/{overtake_event_consistency['run_count']} events={overtake_event_consistency['total_overtake_events']} on_track={overtake_event_consistency['total_on_track_events']} elegant={overtake_event_consistency['total_elegant_events']} errors={overtake_event_consistency['error_count']} warnings={overtake_event_consistency['warning_count']}",
        f"- statistical_table_recompute: {statistical_table_recompute['status']} overall={statistical_table_recompute['overall_rows_checked']} scenario={statistical_table_recompute['scenario_rows_checked']} paired={statistical_table_recompute['paired_rows_checked']} cells={statistical_table_recompute['compared_cells']} mismatches={statistical_table_recompute['mismatch_count']}",
        f"- results_reporting_checklist: {results_reporting['status']} hypotheses={results_reporting['primary_hypothesis_count']} metrics={results_reporting['primary_metric_count']} reporting_issues={results_reporting['primary_reporting_issue_count']} checklist_issues={results_reporting['checklist_issue_count']} source_rows={results_reporting['source_rows']} effect_sizes={results_reporting['effect_size_rows']}",
        f"- results_narrative_pack: {results_narrative['status']} sentences={results_narrative['primary_sentence_pass_count']}/{results_narrative['primary_sentence_count']} issues={results_narrative['checklist_issue_count']} source_rows={results_narrative['source_rows']} vehicles={results_narrative['vehicle_counts']}",
        f"- figure_source_value_recompute: {figure_source_value_recompute['status']} rows={figure_source_value_recompute['pass_rows']}/{figure_source_value_recompute['checked_rows']} cells={figure_source_value_recompute['checked_cells']} mismatches={figure_source_value_recompute['mismatch_count']}",
        f"- figure_caption_claim: {figure_caption_claim['status']} checks={figure_caption_claim['check_count']} check_issues={figure_caption_claim['check_issue_count']} panels={figure_caption_claim['panel_count']} panel_issues={figure_caption_claim['panel_issue_count']} source_rows={figure_caption_claim['source_rows']}",
        f"- table_caption_source_data: {table_caption_source_data['status']} tables={table_caption_source_data['table_count']} table_issues={table_caption_source_data['table_issue_count']} checks={table_caption_source_data['check_count']} check_issues={table_caption_source_data['check_issue_count']} source_rows={table_caption_source_data['source_rows']}",
        f"- table_value_recompute: {table_value_recompute['status']} main={table_value_recompute['main_table_checked_rows']}/{table_value_recompute['main_table_expected_rows']} s2={table_value_recompute['supplementary_s2_checked_rows']} cells={table_value_recompute['checked_cells']} mismatches={table_value_recompute['mismatch_count']} source_rows={table_value_recompute['source_rows']}",
        f"- publication_gif_provenance: {publication_gif_provenance['status']} rows={publication_gif_provenance['pass_rows']}/{publication_gif_provenance['audited_rows']} formal_rows={publication_gif_provenance['formal_matrix_rows_found']} errors={publication_gif_provenance['error_count']} warnings={publication_gif_provenance['warning_count']}",
        f"- supplementary_video_index: {supplementary_video_index['status']} rows={supplementary_video_index['pass_rows']}/{supplementary_video_index['video_rows']} missing={supplementary_video_index['missing_gif_count']} errors={supplementary_video_index['error_count']} warnings={supplementary_video_index['warning_count']} size_mb={supplementary_video_index['total_size_mb']}",
        f"- supplementary_submission_index: {supplementary_submission_index['status']} supplements={supplementary_submission_index['supplement_entries']} figures={supplementary_submission_index['figure_table_entries']} videos={supplementary_submission_index['video_entries']} claims={supplementary_submission_index['claim_crosswalk_entries']} errors={supplementary_submission_index['error_count']} warnings={supplementary_submission_index['warning_count']}",
        f"- online_decision_case_study: {online_decision_case_study['status']} studies={online_decision_case_study['study_count']} events={online_decision_case_study['event_rows']} windows={online_decision_case_study['timeline_rows']}",
        f"- safety_proxy_audit: {safety_proxy_audit['status']} rows={safety_proxy_audit['source_rows']} sampled={safety_proxy_audit['trace_sampled_runs']} contact_positive={safety_proxy_audit['contact_proxy_positive_runs']} primary_grass={safety_proxy_audit['primary_grass_mean']} baseline_grass={safety_proxy_audit['baseline_grass_mean']}",
        f"- source_data_schema: {source_data_schema['status']} fields={source_data_schema['field_count']} dictionary={source_data_schema['dictionary_field_count']} validation_rows={source_data_schema['validation_row_count']} issues={source_data_schema['blocking_issue_count']}",
        f"- algorithm_config_freeze: {algorithm_config_freeze['status']} algorithms={algorithm_config_freeze['algorithm_rows_checked']}/{algorithm_config_freeze['formal_algorithm_count']} commands={algorithm_config_freeze['case_command_pass_count']}/{algorithm_config_freeze['case_command_count']} errors={algorithm_config_freeze['algorithm_error_count']}+{algorithm_config_freeze['case_command_error_count']}",
        f"- compute_timing_boundary: {compute_timing_boundary['status']} available={compute_timing_boundary['available_evidence_count']} boundaries={compute_timing_boundary['unavailable_boundary_count']} rows={compute_timing_boundary['source_rows']} steps={compute_timing_boundary['total_simulated_steps']} mean_latency_ms={compute_timing_boundary['mean_compute_latency_ms']} gpus={compute_timing_boundary['gpu_count']} wall_clock_boundary={compute_timing_boundary['wall_clock_boundary_explicit']}",
        f"- ai_tool_use_disclosure: {ai_tool_use_disclosure['status']} checks={ai_tool_use_disclosure['pass_count']}/{ai_tool_use_disclosure['check_count']} review={ai_tool_use_disclosure['review_required_count']} official_sources={ai_tool_use_disclosure['official_source_count']} scan_files={ai_tool_use_disclosure['scan_file_count']} missing_scan={ai_tool_use_disclosure['missing_scan_file_count']}",
        f"- open_source_minimal_repo: {open_source_minimal_repo['status']} inventory={open_source_minimal_repo['inventory_rows']} missing={open_source_minimal_repo['missing_required_count']} release_issues={open_source_minimal_repo['release_boundary_issue_count']} checks={open_source_minimal_repo['check_count']} check_issues={open_source_minimal_repo['check_issue_count']}",
        f"- submission_gap_priority: {submission_gap_priority['status']} gaps={submission_gap_priority['gap_item_count']} p0={submission_gap_priority['p0_blocking_count']} p1={submission_gap_priority['p1_submission_quality_count']} p2={submission_gap_priority['p2_optional_count']} placeholders={submission_gap_priority['author_placeholder_count']} local_issues={submission_gap_priority['local_evidence_issue_count']}",
        f"- final_freeze_consistency: {final_freeze_consistency['status']} checks={final_freeze_consistency['check_count']} issues={final_freeze_consistency['issue_count']} manifests={final_freeze_consistency['manifest_count']} artifacts={final_freeze_consistency['artifact_files']} readiness={final_freeze_consistency['final_readiness']}",
        f"- artifacts: {release['artifact_files']} files; release={release['release_status']}; fair={release['fair_status']} files={release['fair_files']}",
        f"- boundary: {status['boundary']}",
    ]
    print("\n".join(lines))


def main():
    parser = argparse.ArgumentParser(description="Print a concise status summary for the T-ITS dynamic graph package.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    parser.add_argument("--out-dir", help="Also export an archive-friendly status snapshot to this directory.")
    args = parser.parse_args()
    status = build_status()
    manifest = None
    if args.out_dir:
        manifest = export_snapshot(status, args.out_dir)
    if args.json:
        payload = {"status": status, "snapshot_manifest": manifest} if manifest else status
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print_text(status)
        if manifest:
            print(f"- status_snapshot: {manifest['status']} manifest={manifest['paths']['manifest_json']}")


if __name__ == "__main__":
    main()
