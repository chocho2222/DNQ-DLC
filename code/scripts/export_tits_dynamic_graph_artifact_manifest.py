#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import hashlib
import json
import os
import subprocess
from pathlib import Path


KEY_FILES = [
    "configs/tits_dynamic_graph_experiments.json",
    "docs/tits_dynamic_graph_reproducibility_protocol.md",
    "docs/tits_current_readiness_gap.md",
    "scripts/run_tits_dynamic_graph_suite.py",
    "scripts/run_tits_dynamic_graph_online_suite.py",
    "scripts/run_tits_dynamic_graph_evaluation.py",
    "scripts/print_tits_status.py",
    "scripts/summarize_tits_dynamic_graph_online.py",
    "scripts/export_tits_confirmatory_evidence_pack.py",
    "scripts/export_tits_reviewer_replication_packet.py",
    "scripts/export_tits_reviewer_smoke_route_audit.py",
    "scripts/export_tits_reviewer_smoke_execution_audit.py",
    "scripts/export_tits_root_readme_alignment_audit.py",
    "scripts/export_tits_evidence_ledger.py",
    "scripts/export_tits_claim_numeric_consistency_audit.py",
    "scripts/export_tits_checksum_verification_audit.py",
    "scripts/export_tits_external_validity_boundary_audit.py",
    "scripts/export_tits_limitations_evidence_audit.py",
    "scripts/export_tits_protocol_deviation_readiness_pack.py",
    "scripts/export_tits_manuscript_package.py",
    "scripts/export_tits_manuscript_numeric_trace_audit.py",
    "scripts/export_tits_manuscript_section_trace_audit.py",
    "scripts/export_tits_manuscript_supplement_navigator.py",
    "scripts/export_tits_numbering_consistency_audit.py",
    "scripts/export_tits_figure_source_data_audit.py",
    "scripts/export_tits_figure_source_value_recompute_audit.py",
    "scripts/export_tits_table_caption_source_data_audit.py",
    "scripts/export_tits_table_value_recompute_audit.py",
    "scripts/export_tits_publication_gif_provenance_audit.py",
    "scripts/export_tits_supplementary_video_index_pack.py",
    "scripts/export_tits_supplementary_submission_index_pack.py",
    "scripts/export_tits_online_decision_case_study_pack.py",
    "scripts/export_tits_safety_proxy_audit_pack.py",
    "scripts/export_tits_media_upload_quality_audit.py",
    "scripts/export_tits_manuscript_english_figures.py",
    "scripts/export_tits_ablation_contribution_pack.py",
    "scripts/export_tits_casewise_diagnostic_pack.py",
    "scripts/export_tits_baseline_fairness_audit.py",
    "scripts/export_tits_benchmark_protocol_pack.py",
    "scripts/export_tits_statistical_analysis_pack.py",
    "scripts/export_tits_experimental_design_power_audit.py",
    "scripts/export_tits_threats_validity_pack.py",
    "scripts/export_tits_reviewer_rebuttal_readiness_pack.py",
    "scripts/export_tits_runtime_scalability_pack.py",
    "scripts/export_tits_compute_reproducibility_cost_pack.py",
    "scripts/export_tits_overtake_timing_analysis_pack.py",
    "scripts/export_tits_overtake_casewise_diagnostics_pack.py",
    "scripts/export_tits_v7_elegance_barrier_design_pack.py",
    "scripts/export_tits_typical_first_person_case_pack.py",
    "scripts/export_tits_six_experiment_protocol_pack.py",
    "scripts/tits_experiment_registry.py",
    "scripts/run_tits_expanded_benchmark_matrix.py",
    "scripts/run_tits_mixed_controller_tournament.py",
    "scripts/run_tits_mixed_controller_tournament_case.py",
    "scripts/train_tits_rl_baselines.py",
    "scripts/prepare_tits_paper_dlc_baselines.py",
    "scripts/cleanup_unused_experiment_outputs.py",
    "scripts/export_tits_compute_timing_boundary_audit.py",
    "scripts/export_tits_ai_tool_use_disclosure_audit.py",
    "scripts/export_tits_claim_language_audit.py",
    "scripts/export_tits_claim_evidence_completeness_audit.py",
    "scripts/export_tits_cross_reference_audit.py",
    "scripts/export_tits_source_data_integrity_audit.py",
    "scripts/export_tits_source_data_schema_dictionary_pack.py",
    "scripts/export_tits_algorithm_config_freeze_audit.py",
    "scripts/export_tits_run_level_provenance_audit.py",
    "scripts/export_tits_trace_integrity_audit.py",
    "scripts/export_tits_trace_schema_dictionary_pack.py",
    "scripts/export_tits_overtake_event_consistency_audit.py",
    "scripts/export_tits_statistical_table_recompute_audit.py",
    "scripts/export_tits_environment_reproducibility_audit.py",
    "scripts/export_tits_determinism_smoke_audit.py",
    "scripts/export_tits_reproducibility_capsule.py",
    "scripts/export_tits_data_leakage_tuning_audit.py",
    "scripts/export_tits_innovation_evidence_traceability.py",
    "scripts/export_tits_metric_sensitivity_audit.py",
    "scripts/export_tits_model_artifact_integrity_audit.py",
    "scripts/export_tits_public_release_plan.py",
    "scripts/export_tits_final_readiness_dashboard.py",
    "scripts/export_tits_ieee_tits_compliance_matrix.py",
    "scripts/export_tits_submission_metadata_pack.py",
    "scripts/export_tits_github_release_readiness_pack.py",
    "scripts/export_tits_open_source_minimal_repo_audit.py",
    "scripts/export_tits_author_submission_closure_pack.py",
    "scripts/export_tits_author_owned_submission_integrity_audit.py",
    "scripts/export_tits_reviewer_reproduction_time_budget_audit.py",
    "scripts/export_tits_fair_archive_metadata_pack.py",
    "scripts/export_tits_third_party_reproduction_pack.py",
    "scripts/export_tits_freshness_audit.py",
    "scripts/export_tits_container_build_preflight.py",
    "scripts/export_tits_submission_upload_bundle_map.py",
    "scripts/export_tits_submission_dry_run_checklist.py",
    "scripts/export_tits_final_freeze_consistency_audit.py",
    "scripts/export_tits_anonymization_privacy_audit.py",
    "scripts/export_tits_dependency_license_audit.py",
    "scripts/audit_tits_dynamic_graph_readiness.py",
    "scripts/run_tits_full_pipeline.sh",
    "scripts/run_tits_representative_gifs.sh",
    "scripts/train_graph_risk_world_model.py",
    "scripts/train_graph_bc.py",
    "dlc/graph_world_model.py",
    "dlc/graph_policy.py",
    "dlc/policies.py",
    "dlc/rollout.py",
    "gym_multi_car_racing/multi_car_racing.py",
    "tracks/monza_scaled.npz",
    "tracks/monza_scaled.json",
    "tracks/china_gp_scaled.npz",
    "tracks/china_gp_scaled.json",
    "tracks/imola_scaled.npz",
    "tracks/imola_scaled.json",
    "tracks/indianapolis_sp_scaled.npz",
    "tracks/indianapolis_sp_scaled.json",
    "tracks/monaco_scaled.npz",
    "tracks/monaco_scaled.json",
    "environment.yml",
    "README.md",
    "LICENSE",
]

OUTPUT_PATTERNS = [
    "outputs/tits_dynamic_graph/models/**/*.pt",
    "outputs/tits_dynamic_graph/models/**/*.json",
    "outputs/tits_dynamic_graph/online_evaluation_matrix/**/*.json",
    "outputs/tits_dynamic_graph/online_evaluation_matrix/**/*.csv",
    "outputs/tits_dynamic_graph/online_evaluation_matrix_summary/**/*.csv",
    "outputs/tits_dynamic_graph/online_evaluation_matrix_summary/**/*.md",
    "outputs/tits_dynamic_graph/online_evaluation_matrix_summary/**/*.svg",
    "outputs/tits_dynamic_graph/online_evaluation_matrix_summary/**/*.pdf",
    "outputs/tits_dynamic_graph/online_evaluation_matrix_summary/**/*.png",
    "outputs/tits_dynamic_graph/online_evaluation_matrix_summary/**/*.tiff",
    "outputs/tits_dynamic_graph/v6_confirmatory_matrix/**/*.json",
    "outputs/tits_dynamic_graph/v6_confirmatory_matrix/**/*.csv",
    "outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/**/*.csv",
    "outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/**/*.md",
    "outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/**/*.json",
    "outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/**/*.svg",
    "outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/**/*.pdf",
    "outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/**/*.png",
    "outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/**/*.tiff",
    "outputs/tits_dynamic_graph/v6_confirmatory_preflight/**/*.json",
    "outputs/tits_dynamic_graph/v6_confirmatory_preflight/**/*.csv",
    "outputs/tits_dynamic_graph/v6_confirmatory_preflight/**/*.md",
    "outputs/tits_dynamic_graph/representative_gifs/**/*.gif",
    "outputs/tits_dynamic_graph/representative_gifs/**/*.json",
    "outputs/tits_dynamic_graph/representative_gifs/**/*.csv",
    "outputs/tits_dynamic_graph/representative_gifs/**/*.svg",
    "outputs/tits_dynamic_graph/representative_gifs/**/*.png",
    "outputs/tits_dynamic_graph/publication_gifs/**/*.gif",
    "outputs/tits_dynamic_graph/publication_gifs/**/*.json",
    "outputs/tits_dynamic_graph/publication_gifs/**/*.csv",
    "outputs/tits_dynamic_graph/publication_gifs/**/*.md",
    "outputs/tits_dynamic_graph/publication_gifs/**/*.svg",
    "outputs/tits_dynamic_graph/publication_gifs/**/*.pdf",
    "outputs/tits_dynamic_graph/publication_gifs/**/*.png",
    "outputs/tits_dynamic_graph/publication_gifs/**/*.tiff",
    "outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack/**/*.csv",
    "outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack/**/*.json",
    "outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack/**/*.md",
    "outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack/**/*.svg",
    "outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack/**/*.pdf",
    "outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack/**/*.png",
    "outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack/**/*.tiff",
    "outputs/tits_dynamic_graph/reviewer_replication_packet/**/*.md",
    "outputs/tits_dynamic_graph/reviewer_replication_packet/**/*.json",
    "outputs/tits_dynamic_graph/reviewer_replication_packet/**/*.sh",
    "outputs/tits_dynamic_graph/tits_reviewer_smoke_route_audit/**/*.md",
    "outputs/tits_dynamic_graph/tits_reviewer_smoke_route_audit/**/*.json",
    "outputs/tits_dynamic_graph/tits_reviewer_smoke_route_audit/**/*.csv",
    "outputs/tits_dynamic_graph/tits_reviewer_smoke_execution_audit/**/*.md",
    "outputs/tits_dynamic_graph/tits_reviewer_smoke_execution_audit/**/*.json",
    "outputs/tits_dynamic_graph/tits_reviewer_smoke_execution_audit/**/*.csv",
    "outputs/tits_dynamic_graph/tits_root_readme_alignment_audit/**/*.md",
    "outputs/tits_dynamic_graph/tits_root_readme_alignment_audit/**/*.json",
    "outputs/tits_dynamic_graph/tits_root_readme_alignment_audit/**/*.csv",
    "outputs/tits_dynamic_graph/tits_status_snapshot/**/*.md",
    "outputs/tits_dynamic_graph/tits_status_snapshot/**/*.json",
    "outputs/tits_dynamic_graph/tits_status_snapshot/**/*.csv",
    "outputs/tits_dynamic_graph/tits_evidence_ledger/**/*.md",
    "outputs/tits_dynamic_graph/tits_evidence_ledger/**/*.json",
    "outputs/tits_dynamic_graph/tits_evidence_ledger/**/*.csv",
    "outputs/tits_dynamic_graph/tits_claim_numeric_consistency_audit/**/*.md",
    "outputs/tits_dynamic_graph/tits_claim_numeric_consistency_audit/**/*.json",
    "outputs/tits_dynamic_graph/tits_claim_numeric_consistency_audit/**/*.csv",
    "outputs/tits_dynamic_graph/tits_checksum_verification_audit/**/*.md",
    "outputs/tits_dynamic_graph/tits_checksum_verification_audit/**/*.json",
    "outputs/tits_dynamic_graph/tits_checksum_verification_audit/**/*.csv",
    "outputs/tits_dynamic_graph/tits_external_validity_boundary_audit/**/*.md",
    "outputs/tits_dynamic_graph/tits_external_validity_boundary_audit/**/*.json",
    "outputs/tits_dynamic_graph/tits_external_validity_boundary_audit/**/*.csv",
    "outputs/tits_dynamic_graph/tits_limitations_evidence_audit/**/*.md",
    "outputs/tits_dynamic_graph/tits_limitations_evidence_audit/**/*.json",
    "outputs/tits_dynamic_graph/tits_limitations_evidence_audit/**/*.csv",
    "outputs/tits_dynamic_graph/tits_protocol_deviation_readiness_pack/**/*.md",
    "outputs/tits_dynamic_graph/tits_protocol_deviation_readiness_pack/**/*.json",
    "outputs/tits_dynamic_graph/tits_protocol_deviation_readiness_pack/**/*.csv",
    "outputs/tits_dynamic_graph/tits_manuscript_package/**/*.md",
    "outputs/tits_dynamic_graph/tits_manuscript_package/**/*.json",
    "outputs/tits_dynamic_graph/tits_manuscript_package/**/*.csv",
    "outputs/tits_dynamic_graph/tits_manuscript_numeric_trace_audit/**/*.md",
    "outputs/tits_dynamic_graph/tits_manuscript_numeric_trace_audit/**/*.json",
    "outputs/tits_dynamic_graph/tits_manuscript_numeric_trace_audit/**/*.csv",
    "outputs/tits_dynamic_graph/tits_manuscript_section_trace_audit/**/*.md",
    "outputs/tits_dynamic_graph/tits_manuscript_section_trace_audit/**/*.json",
    "outputs/tits_dynamic_graph/tits_manuscript_section_trace_audit/**/*.csv",
    "outputs/tits_dynamic_graph/tits_abstract_highlights_evidence_audit/**/*.md",
    "outputs/tits_dynamic_graph/tits_abstract_highlights_evidence_audit/**/*.json",
    "outputs/tits_dynamic_graph/tits_abstract_highlights_evidence_audit/**/*.csv",
    "outputs/tits_dynamic_graph/tits_manuscript_supplement_navigator/**/*.md",
    "outputs/tits_dynamic_graph/tits_manuscript_supplement_navigator/**/*.json",
    "outputs/tits_dynamic_graph/tits_manuscript_supplement_navigator/**/*.csv",
    "outputs/tits_dynamic_graph/tits_numbering_consistency_audit/**/*.md",
    "outputs/tits_dynamic_graph/tits_numbering_consistency_audit/**/*.json",
    "outputs/tits_dynamic_graph/tits_numbering_consistency_audit/**/*.csv",
    "outputs/tits_dynamic_graph/tits_figure_source_data_audit/**/*.md",
    "outputs/tits_dynamic_graph/tits_figure_source_data_audit/**/*.json",
    "outputs/tits_dynamic_graph/tits_figure_source_data_audit/**/*.csv",
    "outputs/tits_dynamic_graph/tits_figure_source_value_recompute_audit/**/*.md",
    "outputs/tits_dynamic_graph/tits_figure_source_value_recompute_audit/**/*.json",
    "outputs/tits_dynamic_graph/tits_figure_source_value_recompute_audit/**/*.csv",
    "outputs/tits_dynamic_graph/tits_figure_caption_claim_audit/**/*.md",
    "outputs/tits_dynamic_graph/tits_figure_caption_claim_audit/**/*.json",
    "outputs/tits_dynamic_graph/tits_figure_caption_claim_audit/**/*.csv",
    "outputs/tits_dynamic_graph/tits_table_caption_source_data_audit/**/*.md",
    "outputs/tits_dynamic_graph/tits_table_caption_source_data_audit/**/*.json",
    "outputs/tits_dynamic_graph/tits_table_caption_source_data_audit/**/*.csv",
    "outputs/tits_dynamic_graph/tits_table_value_recompute_audit/**/*.md",
    "outputs/tits_dynamic_graph/tits_table_value_recompute_audit/**/*.json",
    "outputs/tits_dynamic_graph/tits_table_value_recompute_audit/**/*.csv",
    "outputs/tits_dynamic_graph/tits_publication_gif_provenance_audit/**/*.md",
    "outputs/tits_dynamic_graph/tits_publication_gif_provenance_audit/**/*.json",
    "outputs/tits_dynamic_graph/tits_publication_gif_provenance_audit/**/*.csv",
    "outputs/tits_dynamic_graph/tits_supplementary_video_index_pack/**/*.md",
    "outputs/tits_dynamic_graph/tits_supplementary_video_index_pack/**/*.json",
    "outputs/tits_dynamic_graph/tits_supplementary_video_index_pack/**/*.csv",
    "outputs/tits_dynamic_graph/tits_supplementary_submission_index_pack/**/*.md",
    "outputs/tits_dynamic_graph/tits_supplementary_submission_index_pack/**/*.json",
    "outputs/tits_dynamic_graph/tits_supplementary_submission_index_pack/**/*.csv",
    "outputs/tits_dynamic_graph/tits_online_decision_case_study_pack/**/*.md",
    "outputs/tits_dynamic_graph/tits_online_decision_case_study_pack/**/*.json",
    "outputs/tits_dynamic_graph/tits_online_decision_case_study_pack/**/*.csv",
    "outputs/tits_dynamic_graph/tits_online_decision_case_study_pack/**/*.svg",
    "outputs/tits_dynamic_graph/tits_online_decision_case_study_pack/**/*.pdf",
    "outputs/tits_dynamic_graph/tits_online_decision_case_study_pack/**/*.png",
    "outputs/tits_dynamic_graph/tits_online_decision_case_study_pack/**/*.tiff",
    "outputs/tits_dynamic_graph/tits_safety_proxy_audit_pack/**/*.md",
    "outputs/tits_dynamic_graph/tits_safety_proxy_audit_pack/**/*.json",
    "outputs/tits_dynamic_graph/tits_safety_proxy_audit_pack/**/*.csv",
    "outputs/tits_dynamic_graph/tits_safety_proxy_audit_pack/**/*.svg",
    "outputs/tits_dynamic_graph/tits_safety_proxy_audit_pack/**/*.pdf",
    "outputs/tits_dynamic_graph/tits_safety_proxy_audit_pack/**/*.png",
    "outputs/tits_dynamic_graph/tits_safety_proxy_audit_pack/**/*.tiff",
    "outputs/tits_dynamic_graph/tits_media_upload_quality_audit/**/*.md",
    "outputs/tits_dynamic_graph/tits_media_upload_quality_audit/**/*.json",
    "outputs/tits_dynamic_graph/tits_media_upload_quality_audit/**/*.csv",
    "outputs/tits_dynamic_graph/manuscript_english_figures/**/*.md",
    "outputs/tits_dynamic_graph/manuscript_english_figures/**/*.json",
    "outputs/tits_dynamic_graph/manuscript_english_figures/**/*.csv",
    "outputs/tits_dynamic_graph/manuscript_english_figures/**/*.svg",
    "outputs/tits_dynamic_graph/manuscript_english_figures/**/*.pdf",
    "outputs/tits_dynamic_graph/manuscript_english_figures/**/*.png",
    "outputs/tits_dynamic_graph/manuscript_english_figures/**/*.tiff",
    "outputs/tits_dynamic_graph/tits_ablation_contribution_pack/**/*.md",
    "outputs/tits_dynamic_graph/tits_ablation_contribution_pack/**/*.json",
    "outputs/tits_dynamic_graph/tits_ablation_contribution_pack/**/*.csv",
    "outputs/tits_dynamic_graph/tits_ablation_contribution_pack/**/*.svg",
    "outputs/tits_dynamic_graph/tits_ablation_contribution_pack/**/*.pdf",
    "outputs/tits_dynamic_graph/tits_ablation_contribution_pack/**/*.png",
    "outputs/tits_dynamic_graph/tits_ablation_contribution_pack/**/*.tiff",
    "outputs/tits_dynamic_graph/tits_casewise_diagnostic_pack/**/*.md",
    "outputs/tits_dynamic_graph/tits_casewise_diagnostic_pack/**/*.json",
    "outputs/tits_dynamic_graph/tits_casewise_diagnostic_pack/**/*.csv",
    "outputs/tits_dynamic_graph/tits_casewise_diagnostic_pack/**/*.svg",
    "outputs/tits_dynamic_graph/tits_casewise_diagnostic_pack/**/*.pdf",
    "outputs/tits_dynamic_graph/tits_casewise_diagnostic_pack/**/*.png",
    "outputs/tits_dynamic_graph/tits_casewise_diagnostic_pack/**/*.tiff",
    "outputs/tits_dynamic_graph/tits_baseline_fairness_audit/**/*.md",
    "outputs/tits_dynamic_graph/tits_baseline_fairness_audit/**/*.json",
    "outputs/tits_dynamic_graph/tits_baseline_fairness_audit/**/*.csv",
    "outputs/tits_dynamic_graph/tits_benchmark_protocol_pack/**/*.md",
    "outputs/tits_dynamic_graph/tits_benchmark_protocol_pack/**/*.json",
    "outputs/tits_dynamic_graph/tits_benchmark_protocol_pack/**/*.csv",
    "outputs/tits_dynamic_graph/tits_statistical_analysis_pack/**/*.md",
    "outputs/tits_dynamic_graph/tits_statistical_analysis_pack/**/*.json",
    "outputs/tits_dynamic_graph/tits_statistical_analysis_pack/**/*.csv",
    "outputs/tits_dynamic_graph/tits_statistical_analysis_pack/**/*.svg",
    "outputs/tits_dynamic_graph/tits_statistical_analysis_pack/**/*.pdf",
    "outputs/tits_dynamic_graph/tits_statistical_analysis_pack/**/*.png",
    "outputs/tits_dynamic_graph/tits_statistical_analysis_pack/**/*.tiff",
    "outputs/tits_dynamic_graph/tits_experimental_design_power_audit/**/*.md",
    "outputs/tits_dynamic_graph/tits_experimental_design_power_audit/**/*.json",
    "outputs/tits_dynamic_graph/tits_experimental_design_power_audit/**/*.csv",
    "outputs/tits_dynamic_graph/tits_experimental_design_power_audit/**/*.svg",
    "outputs/tits_dynamic_graph/tits_experimental_design_power_audit/**/*.pdf",
    "outputs/tits_dynamic_graph/tits_experimental_design_power_audit/**/*.png",
    "outputs/tits_dynamic_graph/tits_experimental_design_power_audit/**/*.tiff",
    "outputs/tits_dynamic_graph/tits_threats_validity_pack/**/*.md",
    "outputs/tits_dynamic_graph/tits_threats_validity_pack/**/*.json",
    "outputs/tits_dynamic_graph/tits_threats_validity_pack/**/*.csv",
    "outputs/tits_dynamic_graph/tits_reviewer_rebuttal_readiness_pack/**/*.md",
    "outputs/tits_dynamic_graph/tits_reviewer_rebuttal_readiness_pack/**/*.json",
    "outputs/tits_dynamic_graph/tits_reviewer_rebuttal_readiness_pack/**/*.csv",
    "outputs/tits_dynamic_graph/tits_runtime_scalability_pack/**/*.md",
    "outputs/tits_dynamic_graph/tits_runtime_scalability_pack/**/*.json",
    "outputs/tits_dynamic_graph/tits_runtime_scalability_pack/**/*.csv",
    "outputs/tits_dynamic_graph/tits_runtime_scalability_pack/**/*.svg",
    "outputs/tits_dynamic_graph/tits_runtime_scalability_pack/**/*.pdf",
    "outputs/tits_dynamic_graph/tits_runtime_scalability_pack/**/*.png",
    "outputs/tits_dynamic_graph/tits_runtime_scalability_pack/**/*.tiff",
    "outputs/tits_dynamic_graph/tits_compute_reproducibility_cost_pack/**/*.md",
    "outputs/tits_dynamic_graph/tits_compute_reproducibility_cost_pack/**/*.json",
    "outputs/tits_dynamic_graph/tits_compute_reproducibility_cost_pack/**/*.csv",
    "outputs/tits_dynamic_graph/tits_overtake_timing_analysis_pack/**/*.md",
    "outputs/tits_dynamic_graph/tits_overtake_timing_analysis_pack/**/*.json",
    "outputs/tits_dynamic_graph/tits_overtake_timing_analysis_pack/**/*.csv",
    "outputs/tits_dynamic_graph/tits_overtake_timing_analysis_pack/**/*.svg",
    "outputs/tits_dynamic_graph/tits_overtake_timing_analysis_pack/**/*.pdf",
    "outputs/tits_dynamic_graph/tits_overtake_timing_analysis_pack/**/*.png",
    "outputs/tits_dynamic_graph/tits_overtake_timing_analysis_pack/**/*.tiff",
    "outputs/tits_dynamic_graph/tits_overtake_casewise_diagnostics_pack/**/*.md",
    "outputs/tits_dynamic_graph/tits_overtake_casewise_diagnostics_pack/**/*.json",
    "outputs/tits_dynamic_graph/tits_overtake_casewise_diagnostics_pack/**/*.csv",
    "outputs/tits_dynamic_graph/tits_overtake_casewise_diagnostics_pack/**/*.svg",
    "outputs/tits_dynamic_graph/tits_overtake_casewise_diagnostics_pack/**/*.pdf",
    "outputs/tits_dynamic_graph/tits_overtake_casewise_diagnostics_pack/**/*.png",
    "outputs/tits_dynamic_graph/tits_overtake_casewise_diagnostics_pack/**/*.tiff",
    "outputs/tits_dynamic_graph/tits_v7_elegance_barrier_design_pack/**/*.md",
    "outputs/tits_dynamic_graph/tits_v7_elegance_barrier_design_pack/**/*.json",
    "outputs/tits_dynamic_graph/tits_v7_elegance_barrier_design_pack/**/*.csv",
    "outputs/tits_dynamic_graph/tits_typical_first_person_case_pack/**/*.md",
    "outputs/tits_dynamic_graph/tits_typical_first_person_case_pack/**/*.json",
    "outputs/tits_dynamic_graph/tits_typical_first_person_case_pack/**/*.csv",
    "outputs/tits_dynamic_graph/tits_typical_first_person_case_pack/**/*.svg",
    "outputs/tits_dynamic_graph/tits_typical_first_person_case_pack/**/*.pdf",
    "outputs/tits_dynamic_graph/tits_typical_first_person_case_pack/**/*.png",
    "outputs/tits_dynamic_graph/tits_typical_first_person_case_pack/**/*.tiff",
    "outputs/tits_dynamic_graph/tits_typical_first_person_case_pack/**/*.gif",
    "outputs/tits_dynamic_graph/tits_six_experiment_protocol_pack/**/*.md",
    "outputs/tits_dynamic_graph/tits_six_experiment_protocol_pack/**/*.json",
    "outputs/tits_dynamic_graph/tits_six_experiment_protocol_pack/**/*.csv",
    "outputs/tits_dynamic_graph_cleanup/**/*.json",
    "outputs/tits_dynamic_graph_cleanup/**/*.csv",
    "outputs/tits_dynamic_graph/v7_elegance_barrier_smoke/**/*.json",
    "outputs/tits_dynamic_graph/v7_elegance_barrier_smoke/**/*.csv",
    "outputs/tits_dynamic_graph/v7_elegance_barrier_smoke/**/*.svg",
    "outputs/tits_dynamic_graph/v7_elegance_barrier_smoke/**/*.pdf",
    "outputs/tits_dynamic_graph/v7_elegance_barrier_smoke/**/*.png",
    "outputs/tits_dynamic_graph/tits_compute_timing_boundary_audit/**/*.md",
    "outputs/tits_dynamic_graph/tits_compute_timing_boundary_audit/**/*.json",
    "outputs/tits_dynamic_graph/tits_compute_timing_boundary_audit/**/*.csv",
    "outputs/tits_dynamic_graph/tits_ai_tool_use_disclosure_audit/**/*.md",
    "outputs/tits_dynamic_graph/tits_ai_tool_use_disclosure_audit/**/*.json",
    "outputs/tits_dynamic_graph/tits_ai_tool_use_disclosure_audit/**/*.csv",
    "outputs/tits_dynamic_graph/tits_claim_language_audit/**/*.md",
    "outputs/tits_dynamic_graph/tits_claim_language_audit/**/*.json",
    "outputs/tits_dynamic_graph/tits_claim_language_audit/**/*.csv",
    "outputs/tits_dynamic_graph/tits_claim_evidence_completeness_audit/**/*.md",
    "outputs/tits_dynamic_graph/tits_claim_evidence_completeness_audit/**/*.json",
    "outputs/tits_dynamic_graph/tits_claim_evidence_completeness_audit/**/*.csv",
    "outputs/tits_dynamic_graph/tits_cross_reference_audit/**/*.md",
    "outputs/tits_dynamic_graph/tits_cross_reference_audit/**/*.json",
    "outputs/tits_dynamic_graph/tits_cross_reference_audit/**/*.csv",
    "outputs/tits_dynamic_graph/tits_source_data_integrity_audit/**/*.md",
    "outputs/tits_dynamic_graph/tits_source_data_integrity_audit/**/*.json",
    "outputs/tits_dynamic_graph/tits_source_data_integrity_audit/**/*.csv",
    "outputs/tits_dynamic_graph/tits_source_data_schema_dictionary_pack/**/*.md",
    "outputs/tits_dynamic_graph/tits_source_data_schema_dictionary_pack/**/*.json",
    "outputs/tits_dynamic_graph/tits_source_data_schema_dictionary_pack/**/*.csv",
    "outputs/tits_dynamic_graph/tits_source_data_schema_dictionary_pack/**/*.svg",
    "outputs/tits_dynamic_graph/tits_source_data_schema_dictionary_pack/**/*.pdf",
    "outputs/tits_dynamic_graph/tits_source_data_schema_dictionary_pack/**/*.png",
    "outputs/tits_dynamic_graph/tits_source_data_schema_dictionary_pack/**/*.tiff",
    "outputs/tits_dynamic_graph/tits_run_level_provenance_audit/**/*.md",
    "outputs/tits_dynamic_graph/tits_run_level_provenance_audit/**/*.json",
    "outputs/tits_dynamic_graph/tits_run_level_provenance_audit/**/*.csv",
    "outputs/tits_dynamic_graph/tits_trace_integrity_audit/**/*.md",
    "outputs/tits_dynamic_graph/tits_trace_integrity_audit/**/*.json",
    "outputs/tits_dynamic_graph/tits_trace_integrity_audit/**/*.csv",
    "outputs/tits_dynamic_graph/tits_trace_schema_dictionary_pack/**/*.md",
    "outputs/tits_dynamic_graph/tits_trace_schema_dictionary_pack/**/*.json",
    "outputs/tits_dynamic_graph/tits_trace_schema_dictionary_pack/**/*.csv",
    "outputs/tits_dynamic_graph/tits_trace_schema_dictionary_pack/**/*.svg",
    "outputs/tits_dynamic_graph/tits_trace_schema_dictionary_pack/**/*.pdf",
    "outputs/tits_dynamic_graph/tits_trace_schema_dictionary_pack/**/*.png",
    "outputs/tits_dynamic_graph/tits_trace_schema_dictionary_pack/**/*.tiff",
    "outputs/tits_dynamic_graph/tits_overtake_event_consistency_audit/**/*.md",
    "outputs/tits_dynamic_graph/tits_overtake_event_consistency_audit/**/*.json",
    "outputs/tits_dynamic_graph/tits_overtake_event_consistency_audit/**/*.csv",
    "outputs/tits_dynamic_graph/tits_statistical_table_recompute_audit/**/*.md",
    "outputs/tits_dynamic_graph/tits_statistical_table_recompute_audit/**/*.json",
    "outputs/tits_dynamic_graph/tits_statistical_table_recompute_audit/**/*.csv",
    "outputs/tits_dynamic_graph/tits_results_reporting_checklist/**/*.md",
    "outputs/tits_dynamic_graph/tits_results_reporting_checklist/**/*.json",
    "outputs/tits_dynamic_graph/tits_results_reporting_checklist/**/*.csv",
    "outputs/tits_dynamic_graph/tits_results_narrative_pack/**/*.md",
    "outputs/tits_dynamic_graph/tits_results_narrative_pack/**/*.json",
    "outputs/tits_dynamic_graph/tits_results_narrative_pack/**/*.csv",
    "outputs/tits_dynamic_graph/tits_environment_reproducibility_audit/**/*.md",
    "outputs/tits_dynamic_graph/tits_environment_reproducibility_audit/**/*.json",
    "outputs/tits_dynamic_graph/tits_environment_reproducibility_audit/**/*.csv",
    "outputs/tits_dynamic_graph/tits_determinism_smoke_audit/**/*.md",
    "outputs/tits_dynamic_graph/tits_determinism_smoke_audit/**/*.json",
    "outputs/tits_dynamic_graph/tits_determinism_smoke_audit/**/*.csv",
    "outputs/tits_dynamic_graph/tits_reproducibility_capsule/**/*.md",
    "outputs/tits_dynamic_graph/tits_reproducibility_capsule/**/*.json",
    "outputs/tits_dynamic_graph/tits_reproducibility_capsule/**/*.csv",
    "outputs/tits_dynamic_graph/tits_reproducibility_capsule/**/*.sh",
    "outputs/tits_dynamic_graph/tits_data_leakage_tuning_audit/**/*.md",
    "outputs/tits_dynamic_graph/tits_data_leakage_tuning_audit/**/*.json",
    "outputs/tits_dynamic_graph/tits_data_leakage_tuning_audit/**/*.csv",
    "outputs/tits_dynamic_graph/tits_innovation_evidence_traceability/**/*.md",
    "outputs/tits_dynamic_graph/tits_innovation_evidence_traceability/**/*.json",
    "outputs/tits_dynamic_graph/tits_innovation_evidence_traceability/**/*.csv",
    "outputs/tits_dynamic_graph/tits_metric_sensitivity_audit/**/*.md",
    "outputs/tits_dynamic_graph/tits_metric_sensitivity_audit/**/*.json",
    "outputs/tits_dynamic_graph/tits_metric_sensitivity_audit/**/*.csv",
    "outputs/tits_dynamic_graph/tits_metric_sensitivity_audit/**/*.svg",
    "outputs/tits_dynamic_graph/tits_metric_sensitivity_audit/**/*.pdf",
    "outputs/tits_dynamic_graph/tits_metric_sensitivity_audit/**/*.png",
    "outputs/tits_dynamic_graph/tits_metric_sensitivity_audit/**/*.tiff",
    "outputs/tits_dynamic_graph/tits_model_artifact_integrity_audit/**/*.md",
    "outputs/tits_dynamic_graph/tits_model_artifact_integrity_audit/**/*.json",
    "outputs/tits_dynamic_graph/tits_model_artifact_integrity_audit/**/*.csv",
    "outputs/tits_dynamic_graph/tits_algorithm_config_freeze_audit/**/*.md",
    "outputs/tits_dynamic_graph/tits_algorithm_config_freeze_audit/**/*.json",
    "outputs/tits_dynamic_graph/tits_algorithm_config_freeze_audit/**/*.csv",
    "outputs/paper_multicar_overtake_20260618/models/graph_risk_world_model/*.pt",
    "outputs/paper_multicar_overtake_20260618/models/graph_risk_world_model_variants/*.pt",
    "outputs/tits_dynamic_graph/public_release_plan/**/*.md",
    "outputs/tits_dynamic_graph/public_release_plan/**/*.json",
    "outputs/tits_dynamic_graph/public_release_plan/**/*.csv",
    "outputs/tits_dynamic_graph/final_readiness_dashboard/**/*.md",
    "outputs/tits_dynamic_graph/final_readiness_dashboard/**/*.json",
    "outputs/tits_dynamic_graph/final_readiness_dashboard/**/*.csv",
    "outputs/tits_dynamic_graph/ieee_tits_compliance/**/*.md",
    "outputs/tits_dynamic_graph/ieee_tits_compliance/**/*.json",
    "outputs/tits_dynamic_graph/ieee_tits_compliance/**/*.csv",
    "outputs/tits_dynamic_graph/tits_submission_metadata_pack/**/*.md",
    "outputs/tits_dynamic_graph/tits_submission_metadata_pack/**/*.json",
    "outputs/tits_dynamic_graph/tits_submission_metadata_pack/**/*.csv",
    "outputs/tits_dynamic_graph/tits_github_release_readiness_pack/**/*.md",
    "outputs/tits_dynamic_graph/tits_github_release_readiness_pack/**/*.json",
    "outputs/tits_dynamic_graph/tits_github_release_readiness_pack/**/*.csv",
    "outputs/tits_dynamic_graph/tits_open_source_minimal_repo_audit/**/*.md",
    "outputs/tits_dynamic_graph/tits_open_source_minimal_repo_audit/**/*.json",
    "outputs/tits_dynamic_graph/tits_open_source_minimal_repo_audit/**/*.csv",
    "outputs/tits_dynamic_graph/tits_author_submission_closure_pack/**/*.md",
    "outputs/tits_dynamic_graph/tits_author_submission_closure_pack/**/*.json",
    "outputs/tits_dynamic_graph/tits_author_submission_closure_pack/**/*.csv",
    "outputs/tits_dynamic_graph/tits_author_owned_submission_integrity_audit/**/*.md",
    "outputs/tits_dynamic_graph/tits_author_owned_submission_integrity_audit/**/*.json",
    "outputs/tits_dynamic_graph/tits_author_owned_submission_integrity_audit/**/*.csv",
    "outputs/tits_dynamic_graph/tits_reviewer_reproduction_time_budget_audit/**/*.md",
    "outputs/tits_dynamic_graph/tits_reviewer_reproduction_time_budget_audit/**/*.json",
    "outputs/tits_dynamic_graph/tits_reviewer_reproduction_time_budget_audit/**/*.csv",
    "outputs/tits_dynamic_graph/tits_fair_archive_metadata_pack/**/*.md",
    "outputs/tits_dynamic_graph/tits_fair_archive_metadata_pack/**/*.json",
    "outputs/tits_dynamic_graph/tits_fair_archive_metadata_pack/**/*.csv",
    "outputs/tits_dynamic_graph/tits_third_party_reproduction_pack/**/*.md",
    "outputs/tits_dynamic_graph/tits_third_party_reproduction_pack/**/*.json",
    "outputs/tits_dynamic_graph/tits_third_party_reproduction_pack/**/*.csv",
    "outputs/tits_dynamic_graph/tits_third_party_reproduction_pack/**/*.draft",
    "outputs/tits_dynamic_graph/tits_freshness_audit/**/*.md",
    "outputs/tits_dynamic_graph/tits_freshness_audit/**/*.json",
    "outputs/tits_dynamic_graph/tits_freshness_audit/**/*.csv",
    "outputs/tits_dynamic_graph/tits_container_build_preflight/**/*.md",
    "outputs/tits_dynamic_graph/tits_container_build_preflight/**/*.json",
    "outputs/tits_dynamic_graph/tits_container_build_preflight/**/*.csv",
    "outputs/tits_dynamic_graph/tits_submission_upload_bundle_map/**/*.md",
    "outputs/tits_dynamic_graph/tits_submission_upload_bundle_map/**/*.json",
    "outputs/tits_dynamic_graph/tits_submission_upload_bundle_map/**/*.csv",
    "outputs/tits_dynamic_graph/tits_submission_dry_run_checklist/**/*.md",
    "outputs/tits_dynamic_graph/tits_submission_dry_run_checklist/**/*.json",
    "outputs/tits_dynamic_graph/tits_submission_dry_run_checklist/**/*.csv",
    "outputs/tits_dynamic_graph/tits_submission_gap_priority_audit/**/*.md",
    "outputs/tits_dynamic_graph/tits_submission_gap_priority_audit/**/*.json",
    "outputs/tits_dynamic_graph/tits_submission_gap_priority_audit/**/*.csv",
    "outputs/tits_dynamic_graph/tits_final_freeze_consistency_audit/**/*.md",
    "outputs/tits_dynamic_graph/tits_final_freeze_consistency_audit/**/*.json",
    "outputs/tits_dynamic_graph/tits_final_freeze_consistency_audit/**/*.csv",
    "outputs/tits_dynamic_graph/tits_anonymization_privacy_audit/**/*.md",
    "outputs/tits_dynamic_graph/tits_anonymization_privacy_audit/**/*.json",
    "outputs/tits_dynamic_graph/tits_anonymization_privacy_audit/**/*.csv",
    "outputs/tits_dynamic_graph/tits_dependency_license_audit/**/*.md",
    "outputs/tits_dynamic_graph/tits_dependency_license_audit/**/*.json",
    "outputs/tits_dynamic_graph/tits_dependency_license_audit/**/*.csv",
    "outputs/tits_dynamic_graph/logs/*.log",
    "outputs/tits_dynamic_graph/*summary.json",
    "outputs/tits_dynamic_graph/tits_readiness_audit.json",
]


def sha256_file(path, chunk_size=1024 * 1024):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def git_revision(root):
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    except Exception:
        return None


def git_status(root):
    try:
        return subprocess.check_output(["git", "status", "--short"], cwd=root, text=True).splitlines()
    except Exception:
        return []


def categorize(path):
    parts = Path(path).parts
    if not parts:
        return "unknown"
    if parts[0] in {"configs", "docs", "scripts", "dlc", "gym_multi_car_racing", "tracks"}:
        return parts[0]
    if parts[0] == "outputs" and len(parts) > 2:
        return "/".join(parts[:3])
    return parts[0]


def collect_files(root):
    root = Path(root)
    seen = set()
    paths = []
    for rel in KEY_FILES:
        path = root / rel
        if path.exists() and path.is_file():
            seen.add(path.resolve())
            paths.append(path)
    for pattern in OUTPUT_PATTERNS:
        for path in root.glob(pattern):
            if path.is_file() and path.resolve() not in seen:
                seen.add(path.resolve())
                paths.append(path)
    rows = []
    for path in sorted(paths):
        rel = path.relative_to(root).as_posix()
        rows.append(
            {
                "path": rel,
                "category": categorize(rel),
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    return rows


def command_manifest():
    return {
        "train": (
            "MODE=run PYTHON_BIN=/home/itrc/.conda/envs/vlm_planner/bin/python "
            "DEVICES=cuda:0,cuda:1,cuda:2,cuda:3 TRAIN_JOBS=2 COLLECTION_WORKERS=8 JOBS=8 "
            "CLEAN_ONLINE=1 RUN_REPRESENTATIVE_GIFS=1 scripts/run_tits_full_pipeline.sh"
        ),
        "resume_online_from_trained_models": (
            "MODE=run SKIP_TRAIN=1 PYTHON_BIN=/home/itrc/.conda/envs/vlm_planner/bin/python "
            "DEVICES=cuda:0,cuda:1,cuda:2,cuda:3 JOBS=8 CLEAN_ONLINE=1 "
            "RUN_REPRESENTATIVE_GIFS=1 scripts/run_tits_full_pipeline.sh"
        ),
        "online_matrix": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/run_tits_dynamic_graph_online_suite.py "
            "--mode run --devices cuda:0,cuda:1,cuda:2,cuda:3 --jobs 8 --max-steps 2200 "
            "--finish-mode any --observation-type telemetry_dynamic --traffic-profile slow_traffic --no-gif"
        ),
        "confirmatory_matrix": (
            "See outputs/tits_dynamic_graph/v6_confirmatory_preflight/tables/v6_confirmatory_case_commands.csv "
            "for the frozen per-case command list used to produce the 240-run confirmatory matrix."
        ),
        "representative_gifs": (
            "PYTHON_BIN=/home/itrc/.conda/envs/vlm_planner/bin/python "
            "DEVICES=cuda:0,cuda:1,cuda:2,cuda:3 scripts/run_tits_representative_gifs.sh"
        ),
        "publication_gifs": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/run_tits_dynamic_graph_evaluation.py "
            "--config configs/tits_dynamic_graph_experiments.json --first-person-gif "
            "--frame-every 12 --fps 12 --observation-type telemetry_dynamic --max-neighbors 3"
        ),
        "summarize": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/summarize_tits_dynamic_graph_online.py "
            "--input-dir outputs/tits_dynamic_graph/online_evaluation_matrix "
            "--out-dir outputs/tits_dynamic_graph/online_evaluation_matrix_summary --bootstrap 5000"
        ),
        "confirmatory_summarize": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/summarize_tits_dynamic_graph_online.py "
            "--input-dir outputs/tits_dynamic_graph/v6_confirmatory_matrix "
            "--out-dir outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary --bootstrap 5000"
        ),
        "audit": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/audit_tits_dynamic_graph_readiness.py "
            "--config configs/tits_dynamic_graph_experiments.json "
            "--online-dir outputs/tits_dynamic_graph/online_evaluation_matrix "
            "--summary-dir outputs/tits_dynamic_graph/online_evaluation_matrix_summary "
            "--out outputs/tits_dynamic_graph/tits_readiness_audit.json"
        ),
        "tits_status": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/print_tits_status.py"
        ),
        "status_snapshot": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/print_tits_status.py "
            "--out-dir outputs/tits_dynamic_graph/tits_status_snapshot"
        ),
        "evidence_ledger": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_evidence_ledger.py "
            "--out-dir outputs/tits_dynamic_graph/tits_evidence_ledger"
        ),
        "claim_numeric_consistency_audit": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_claim_numeric_consistency_audit.py "
            "--out-dir outputs/tits_dynamic_graph/tits_claim_numeric_consistency_audit"
        ),
        "checksum_verification_audit": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_checksum_verification_audit.py "
            "--out-dir outputs/tits_dynamic_graph/tits_checksum_verification_audit"
        ),
        "external_validity_boundary_audit": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_external_validity_boundary_audit.py "
            "--out-dir outputs/tits_dynamic_graph/tits_external_validity_boundary_audit"
        ),
        "limitations_evidence_audit": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_limitations_evidence_audit.py "
            "--out-dir outputs/tits_dynamic_graph/tits_limitations_evidence_audit"
        ),
        "protocol_deviation_readiness_pack": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_protocol_deviation_readiness_pack.py "
            "--out-dir outputs/tits_dynamic_graph/tits_protocol_deviation_readiness_pack"
        ),
        "confirmatory_audit": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/audit_v6_confirmatory_matrix.py "
            "--case-commands outputs/tits_dynamic_graph/v6_confirmatory_preflight/tables/v6_confirmatory_case_commands.csv "
            "--matrix-dir outputs/tits_dynamic_graph/v6_confirmatory_matrix "
            "--out-dir outputs/tits_dynamic_graph/v6_confirmatory_preflight"
        ),
        "confirmatory_evidence_pack": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_confirmatory_evidence_pack.py "
            "--source-csv outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv "
            "--case-commands outputs/tits_dynamic_graph/v6_confirmatory_preflight/tables/v6_confirmatory_case_commands.csv "
            "--ledger outputs/tits_dynamic_graph/v6_confirmatory_matrix_run_results_ledger.csv "
            "--out-dir outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack --bootstrap 5000"
        ),
        "reviewer_replication_packet": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_reviewer_replication_packet.py "
            "--out-dir outputs/tits_dynamic_graph/reviewer_replication_packet"
        ),
        "reviewer_smoke_route_audit": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_reviewer_smoke_route_audit.py "
            "--out-dir outputs/tits_dynamic_graph/tits_reviewer_smoke_route_audit"
        ),
        "reviewer_smoke_execution_audit": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_reviewer_smoke_execution_audit.py "
            "--out-dir outputs/tits_dynamic_graph/tits_reviewer_smoke_execution_audit"
        ),
        "root_readme_alignment_audit": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_root_readme_alignment_audit.py "
            "--out-dir outputs/tits_dynamic_graph/tits_root_readme_alignment_audit"
        ),
        "manuscript_package": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_manuscript_package.py "
            "--out-dir outputs/tits_dynamic_graph/tits_manuscript_package"
        ),
        "manuscript_numeric_trace_audit": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_manuscript_numeric_trace_audit.py "
            "--out-dir outputs/tits_dynamic_graph/tits_manuscript_numeric_trace_audit"
        ),
        "manuscript_section_trace_audit": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_manuscript_section_trace_audit.py "
            "--out-dir outputs/tits_dynamic_graph/tits_manuscript_section_trace_audit"
        ),
        "manuscript_supplement_navigator": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_manuscript_supplement_navigator.py "
            "--out-dir outputs/tits_dynamic_graph/tits_manuscript_supplement_navigator"
        ),
        "numbering_consistency_audit": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_numbering_consistency_audit.py "
            "--out-dir outputs/tits_dynamic_graph/tits_numbering_consistency_audit"
        ),
        "figure_source_data_audit": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_figure_source_data_audit.py "
            "--out-dir outputs/tits_dynamic_graph/tits_figure_source_data_audit"
        ),
        "figure_source_value_recompute_audit": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_figure_source_value_recompute_audit.py "
            "--out-dir outputs/tits_dynamic_graph/tits_figure_source_value_recompute_audit"
        ),
        "table_caption_source_data_audit": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_table_caption_source_data_audit.py "
            "--out-dir outputs/tits_dynamic_graph/tits_table_caption_source_data_audit"
        ),
        "table_value_recompute_audit": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_table_value_recompute_audit.py "
            "--out-dir outputs/tits_dynamic_graph/tits_table_value_recompute_audit"
        ),
        "publication_gif_provenance_audit": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_publication_gif_provenance_audit.py "
            "--out-dir outputs/tits_dynamic_graph/tits_publication_gif_provenance_audit"
        ),
        "supplementary_video_index_pack": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_supplementary_video_index_pack.py "
            "--out-dir outputs/tits_dynamic_graph/tits_supplementary_video_index_pack"
        ),
        "supplementary_submission_index_pack": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_supplementary_submission_index_pack.py "
            "--out-dir outputs/tits_dynamic_graph/tits_supplementary_submission_index_pack"
        ),
        "safety_proxy_audit_pack": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_safety_proxy_audit_pack.py "
            "--out-dir outputs/tits_dynamic_graph/tits_safety_proxy_audit_pack"
        ),
        "media_upload_quality_audit": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_media_upload_quality_audit.py "
            "--out-dir outputs/tits_dynamic_graph/tits_media_upload_quality_audit"
        ),
        "manuscript_english_figures": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_manuscript_english_figures.py "
            "--out-dir outputs/tits_dynamic_graph/manuscript_english_figures"
        ),
        "ablation_contribution_pack": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_ablation_contribution_pack.py "
            "--out-dir outputs/tits_dynamic_graph/tits_ablation_contribution_pack"
        ),
        "casewise_diagnostic_pack": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_casewise_diagnostic_pack.py "
            "--out-dir outputs/tits_dynamic_graph/tits_casewise_diagnostic_pack"
        ),
        "baseline_fairness_audit": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_baseline_fairness_audit.py "
            "--out-dir outputs/tits_dynamic_graph/tits_baseline_fairness_audit"
        ),
        "benchmark_protocol_pack": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_benchmark_protocol_pack.py "
            "--out-dir outputs/tits_dynamic_graph/tits_benchmark_protocol_pack"
        ),
        "statistical_analysis_pack": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_statistical_analysis_pack.py "
            "--out-dir outputs/tits_dynamic_graph/tits_statistical_analysis_pack"
        ),
        "experimental_design_power_audit": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_experimental_design_power_audit.py "
            "--out-dir outputs/tits_dynamic_graph/tits_experimental_design_power_audit"
        ),
        "threats_validity_pack": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_threats_validity_pack.py "
            "--out-dir outputs/tits_dynamic_graph/tits_threats_validity_pack"
        ),
        "reviewer_rebuttal_readiness_pack": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_reviewer_rebuttal_readiness_pack.py "
            "--out-dir outputs/tits_dynamic_graph/tits_reviewer_rebuttal_readiness_pack"
        ),
        "runtime_scalability_pack": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_runtime_scalability_pack.py "
            "--out-dir outputs/tits_dynamic_graph/tits_runtime_scalability_pack"
        ),
        "compute_reproducibility_cost_pack": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_compute_reproducibility_cost_pack.py "
            "--out-dir outputs/tits_dynamic_graph/tits_compute_reproducibility_cost_pack"
        ),
        "overtake_timing_analysis_pack": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_overtake_timing_analysis_pack.py "
            "--out-dir outputs/tits_dynamic_graph/tits_overtake_timing_analysis_pack"
        ),
        "overtake_casewise_diagnostics_pack": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_overtake_casewise_diagnostics_pack.py "
            "--out-dir outputs/tits_dynamic_graph/tits_overtake_casewise_diagnostics_pack"
        ),
        "v7_elegance_barrier_design_pack": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_v7_elegance_barrier_design_pack.py "
            "--out-dir outputs/tits_dynamic_graph/tits_v7_elegance_barrier_design_pack"
        ),
        "typical_first_person_case_pack": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_typical_first_person_case_pack.py "
            "--out-dir outputs/tits_dynamic_graph/tits_typical_first_person_case_pack"
        ),
        "six_experiment_protocol_pack": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_six_experiment_protocol_pack.py "
            "--out-dir outputs/tits_dynamic_graph/tits_six_experiment_protocol_pack"
        ),
        "unused_experiment_cleanup_dry_run": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/cleanup_unused_experiment_outputs.py "
            "--out-dir outputs/tits_dynamic_graph_cleanup"
        ),
        "compute_timing_boundary_audit": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_compute_timing_boundary_audit.py "
            "--out-dir outputs/tits_dynamic_graph/tits_compute_timing_boundary_audit"
        ),
        "ai_tool_use_disclosure_audit": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_ai_tool_use_disclosure_audit.py "
            "--out-dir outputs/tits_dynamic_graph/tits_ai_tool_use_disclosure_audit"
        ),
        "claim_language_audit": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_claim_language_audit.py "
            "--out-dir outputs/tits_dynamic_graph/tits_claim_language_audit"
        ),
        "claim_evidence_completeness_audit": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_claim_evidence_completeness_audit.py "
            "--out-dir outputs/tits_dynamic_graph/tits_claim_evidence_completeness_audit"
        ),
        "cross_reference_audit": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_cross_reference_audit.py "
            "--out-dir outputs/tits_dynamic_graph/tits_cross_reference_audit"
        ),
        "source_data_integrity_audit": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_source_data_integrity_audit.py "
            "--out-dir outputs/tits_dynamic_graph/tits_source_data_integrity_audit"
        ),
        "source_data_schema_dictionary_pack": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_source_data_schema_dictionary_pack.py "
            "--out-dir outputs/tits_dynamic_graph/tits_source_data_schema_dictionary_pack"
        ),
        "run_level_provenance_audit": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_run_level_provenance_audit.py "
            "--out-dir outputs/tits_dynamic_graph/tits_run_level_provenance_audit"
        ),
        "trace_integrity_audit": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_trace_integrity_audit.py "
            "--out-dir outputs/tits_dynamic_graph/tits_trace_integrity_audit"
        ),
        "trace_schema_dictionary_pack": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_trace_schema_dictionary_pack.py "
            "--out-dir outputs/tits_dynamic_graph/tits_trace_schema_dictionary_pack"
        ),
        "overtake_event_consistency_audit": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_overtake_event_consistency_audit.py "
            "--out-dir outputs/tits_dynamic_graph/tits_overtake_event_consistency_audit"
        ),
        "statistical_table_recompute_audit": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_statistical_table_recompute_audit.py "
            "--out-dir outputs/tits_dynamic_graph/tits_statistical_table_recompute_audit"
        ),
        "environment_reproducibility_audit": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_environment_reproducibility_audit.py "
            "--out-dir outputs/tits_dynamic_graph/tits_environment_reproducibility_audit"
        ),
        "determinism_smoke_audit": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_determinism_smoke_audit.py "
            "--out-dir outputs/tits_dynamic_graph/tits_determinism_smoke_audit"
        ),
        "reproducibility_capsule": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_reproducibility_capsule.py "
            "--out-dir outputs/tits_dynamic_graph/tits_reproducibility_capsule"
        ),
        "data_leakage_tuning_audit": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_data_leakage_tuning_audit.py "
            "--out-dir outputs/tits_dynamic_graph/tits_data_leakage_tuning_audit"
        ),
        "innovation_evidence_traceability": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_innovation_evidence_traceability.py "
            "--out-dir outputs/tits_dynamic_graph/tits_innovation_evidence_traceability"
        ),
        "metric_sensitivity_audit": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_metric_sensitivity_audit.py "
            "--out-dir outputs/tits_dynamic_graph/tits_metric_sensitivity_audit"
        ),
        "model_artifact_integrity_audit": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_model_artifact_integrity_audit.py "
            "--out-dir outputs/tits_dynamic_graph/tits_model_artifact_integrity_audit"
        ),
        "algorithm_config_freeze_audit": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_algorithm_config_freeze_audit.py "
            "--out-dir outputs/tits_dynamic_graph/tits_algorithm_config_freeze_audit"
        ),
        "public_release_plan": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_public_release_plan.py "
            "--out-dir outputs/tits_dynamic_graph/public_release_plan"
        ),
        "final_readiness_dashboard": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_final_readiness_dashboard.py "
            "--out-dir outputs/tits_dynamic_graph/final_readiness_dashboard"
        ),
        "ieee_tits_compliance_matrix": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_ieee_tits_compliance_matrix.py "
            "--out-dir outputs/tits_dynamic_graph/ieee_tits_compliance"
        ),
        "submission_metadata_pack": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_submission_metadata_pack.py "
            "--out-dir outputs/tits_dynamic_graph/tits_submission_metadata_pack"
        ),
        "github_release_readiness_pack": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_github_release_readiness_pack.py "
            "--out-dir outputs/tits_dynamic_graph/tits_github_release_readiness_pack"
        ),
        "open_source_minimal_repo_audit": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_open_source_minimal_repo_audit.py "
            "--out-dir outputs/tits_dynamic_graph/tits_open_source_minimal_repo_audit"
        ),
        "author_submission_closure_pack": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_author_submission_closure_pack.py "
            "--out-dir outputs/tits_dynamic_graph/tits_author_submission_closure_pack"
        ),
        "author_owned_submission_integrity_audit": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_author_owned_submission_integrity_audit.py "
            "--out-dir outputs/tits_dynamic_graph/tits_author_owned_submission_integrity_audit"
        ),
        "reviewer_reproduction_time_budget_audit": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_reviewer_reproduction_time_budget_audit.py "
            "--out-dir outputs/tits_dynamic_graph/tits_reviewer_reproduction_time_budget_audit"
        ),
        "fair_archive_metadata_pack": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_fair_archive_metadata_pack.py "
            "--out-dir outputs/tits_dynamic_graph/tits_fair_archive_metadata_pack"
        ),
        "third_party_reproduction_pack": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_third_party_reproduction_pack.py "
            "--out-dir outputs/tits_dynamic_graph/tits_third_party_reproduction_pack"
        ),
        "freshness_audit": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_freshness_audit.py "
            "--out-dir outputs/tits_dynamic_graph/tits_freshness_audit"
        ),
        "container_build_preflight": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_container_build_preflight.py "
            "--out-dir outputs/tits_dynamic_graph/tits_container_build_preflight"
        ),
        "submission_upload_bundle_map": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_submission_upload_bundle_map.py "
            "--out-dir outputs/tits_dynamic_graph/tits_submission_upload_bundle_map"
        ),
        "submission_dry_run_checklist": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_submission_dry_run_checklist.py "
            "--out-dir outputs/tits_dynamic_graph/tits_submission_dry_run_checklist"
        ),
        "final_freeze_consistency_audit": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_final_freeze_consistency_audit.py "
            "--out-dir outputs/tits_dynamic_graph/tits_final_freeze_consistency_audit"
        ),
        "anonymization_privacy_audit": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_anonymization_privacy_audit.py "
            "--out-dir outputs/tits_dynamic_graph/tits_anonymization_privacy_audit"
        ),
        "dependency_license_audit": (
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_dependency_license_audit.py "
            "--out-dir outputs/tits_dynamic_graph/tits_dependency_license_audit"
        ),
    }


def load_optional_json(path):
    path = Path(path)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def write_csv(rows, path):
    path = Path(path)
    fieldnames = ["path", "category", "size_bytes", "sha256"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(manifest, path):
    path = Path(path)
    lines = [
        "# TITS Dynamic Graph Artifact Manifest",
        "",
        f"- Status: `{manifest['status']}`",
        f"- Files: {manifest['summary']['file_count']}",
        f"- Size: {manifest['summary']['size_bytes']} bytes",
        f"- Git revision: `{manifest.get('git_revision')}`",
        f"- Readiness audit: `{manifest['readiness_audit'].get('status')}`",
        "",
        "## Commands",
        "",
    ]
    for name, command in manifest["commands"].items():
        lines.extend([f"### {name}", "", f"```bash\n{command}\n```", ""])
    lines.extend(["## Categories", "", "| Category | Files | Size bytes |", "|---|---:|---:|"])
    for category, item in sorted(manifest["summary"]["by_category"].items()):
        lines.append(f"| {category} | {item['file_count']} | {item['size_bytes']} |")
    lines.extend(["", "## Notes", "", manifest["note"], ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export a reproducible artifact manifest for the TITS dynamic graph study.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/artifact_manifest")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    out_dir = root / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = collect_files(root)
    by_category = {}
    for row in rows:
        item = by_category.setdefault(row["category"], {"file_count": 0, "size_bytes": 0})
        item["file_count"] += 1
        item["size_bytes"] += int(row["size_bytes"])

    readiness = load_optional_json(root / "outputs/tits_dynamic_graph/tits_readiness_audit.json") or {}
    manifest = {
        "status": "artifact_manifest_generated",
        "root": str(root),
        "git_revision": git_revision(root),
        "git_status_short": git_status(root),
        "commands": command_manifest(),
        "readiness_audit": {
            "path": "outputs/tits_dynamic_graph/tits_readiness_audit.json",
            "status": readiness.get("status"),
            "failed": len(readiness.get("failed", [])) if isinstance(readiness.get("failed", []), list) else None,
            "warnings": len(readiness.get("warnings", [])) if isinstance(readiness.get("warnings", []), list) else None,
            "note": readiness.get("note"),
        },
        "summary": {
            "file_count": len(rows),
            "size_bytes": sum(int(row["size_bytes"]) for row in rows),
            "by_category": by_category,
        },
        "files": rows,
        "note": (
            "This manifest records local artifacts and checksums. The v6_confirmatory_matrix entries are the "
            "current final 240-run confirmatory online matrix, while publication_gifs contains representative "
            "top-down and first-person visual evidence generated separately from the formal matrix."
        ),
    }
    json_path = out_dir / "tits_dynamic_graph_artifact_manifest.json"
    csv_path = out_dir / "tits_dynamic_graph_artifact_manifest_files.csv"
    md_path = out_dir / "tits_dynamic_graph_artifact_manifest.md"
    json_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    write_csv(rows, csv_path)
    write_markdown(manifest, md_path)
    print(json.dumps({"json": str(json_path), "csv": str(csv_path), "markdown": str(md_path), "files": len(rows)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
