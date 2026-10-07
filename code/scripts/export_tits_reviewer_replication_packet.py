#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import json
from pathlib import Path


def load_json(path):
    path = Path(path)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")
    return str(path)


def command_block(command):
    return f"```bash\n{command}\n```"


def build_reviewer_readme(readiness, final_readiness, confirmatory_audit, evidence, artifact, protocol_deviation):
    commands = artifact.get("commands", {})
    summary = artifact.get("summary", {})
    final_gate_text = f"{final_readiness.get('pass_count', 'NA')}/{final_readiness.get('gate_count', 'NA')}"
    return f"""# Reviewer Replication Packet

This packet gives the shortest route for a reviewer to audit, smoke-test, and reproduce the dynamic-neighborhood DLC world-model overtaking experiments.

## Current Evidence Status

- Readiness audit: `{readiness.get('status')}`
- Final readiness gates: {final_gate_text}
- Confirmatory matrix status: `{confirmatory_audit.get('summary', {}).get('status')}`
- Expected algorithm-runs: {confirmatory_audit.get('summary', {}).get('expected_algorithm_runs')}
- Existing summaries: {confirmatory_audit.get('summary', {}).get('existing_summaries')}
- Missing summaries: {confirmatory_audit.get('summary', {}).get('missing_summaries')}
- Evidence pack status: `{evidence.get('status')}`
- Evidence pack runs: {evidence.get('run_count')}
- Evidence pack cases: {evidence.get('case_count')}
- Evidence pack algorithms: {evidence.get('algorithm_count')}
- Protocol/deviation readiness: `{protocol_deviation.get('status')}`; endpoints={protocol_deviation.get('summary', {}).get('endpoint_count')}; boundaries={protocol_deviation.get('summary', {}).get('protocol_boundary_count')}; missing_evidence={protocol_deviation.get('summary', {}).get('missing_evidence_count')}
- Artifact manifest files: {summary.get('file_count')}
- Artifact manifest size bytes: see `outputs/tits_dynamic_graph/artifact_manifest/tits_dynamic_graph_artifact_manifest.json`
- Git revision recorded by manifest: `{artifact.get('git_revision')}`

## Minimal Local Smoke Test

Use this only to verify that the environment, imports, and evaluation code path work. It is not a paper-scale result.

{command_block('/home/itrc/.conda/envs/vlm_planner/bin/python scripts/run_tits_dynamic_graph_evaluation.py --config configs/tits_dynamic_graph_experiments.json --out-dir /tmp/tits_dynamic_graph_reviewer_smoke --algorithms v6_runtime_dynamic_neighborhood_safe,dlc_world_original --num-agents 4 --seed 3 --max-steps 120 --finish-mode steps --observation-type telemetry_dynamic --max-neighbors 3 --device cuda:0 --traffic-profile slow_traffic --no-gif')}

Expected output: `/tmp/tits_dynamic_graph_reviewer_smoke/summaries/*.summary.json`.

After the smoke run, record an execution fingerprint without copying the full
temporary output into the formal archive:

{command_block('/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_reviewer_smoke_execution_audit.py --out-dir outputs/tits_dynamic_graph/tits_reviewer_smoke_execution_audit')}

Expected audit: `outputs/tits_dynamic_graph/tits_reviewer_smoke_execution_audit/materials/REVIEWER_SMOKE_EXECUTION_AUDIT.md`.
This audit is an observation-only reproducibility check and must not be used as
paper-scale performance evidence.

## Reproduction Depth Tiers

Use the tier that matches the review question. The tiers intentionally separate
paper-scale performance evidence from lightweight route checks and visual
inspection.

| Tier | Reviewer question | Scope | Paper-scale result? | Primary command or input | Acceptance criteria |
|---|---|---|---|---|---|
| T0 | Does the code path execute locally? | Short two-algorithm smoke rollout plus smoke execution audit | No | `bash outputs/tits_dynamic_graph/reviewer_replication_packet/run_reviewer_smoke.sh && /home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_reviewer_smoke_execution_audit.py --out-dir outputs/tits_dynamic_graph/tits_reviewer_smoke_execution_audit` | Two smoke summaries are present, execution checks pass, and no paper-scale claim is made from smoke outputs. |
| T1 | Do all reported numbers and claims still match the frozen evidence? | Reporting, audit, figure/table and claim-trace rebuild from existing source data | Yes, reporting layer only | `make tits-refresh-gates` | Final readiness remains PASS, freshness and cross-reference stay PASS, and claim/evidence paths resolve. |
| T2 | Can the full online experiment matrix be independently rerun? | 30 frozen case commands, 8 algorithms, 240 source rows | Yes, if the full matrix is rerun and all downstream audits are regenerated | `outputs/tits_dynamic_graph/v6_confirmatory_preflight/tables/v6_confirmatory_case_commands.csv` | 240 summaries regenerate, source data contains 30 matched cases and 8 algorithms, and all source-data/statistical/reproducibility audits pass. |
| T3 | Do the qualitative visual examples match the traced behavior? | Representative top-down and first-person GIF rebuild/provenance audit | Qualitative visual evidence only | `make tits-publication-gif-provenance` and `make tits-supplementary-video-index` | GIF files exist, trace to formal summaries/source rows, and warnings remain non-blocking provenance notes. |

Detailed time/cost boundaries are archived in
`outputs/tits_dynamic_graph/tits_reviewer_reproduction_time_budget_audit/materials/REVIEWER_REPRODUCTION_TIME_BUDGET_AUDIT.md`.

## Makefile Shortcuts

The repository exposes the same reviewer-facing entry points through `make`.
These shortcuts are intended for local convenience; the explicit Python
commands below remain the authoritative provenance route.

{command_block('make tits-smoke')}

{command_block('make tits-smoke-execution-audit')}

{command_block('make tits-refresh-gates')}

{command_block('make tits-status')}

{command_block('make tits-status-snapshot')}

{command_block('make tits-evidence-ledger')}

{command_block('make tits-claim-numeric-audit')}

{command_block('make tits-manuscript-section-trace')}

{command_block('make tits-abstract-highlights-audit')}

{command_block('make tits-checksum-audit')}

{command_block('make tits-external-validity-audit')}

{command_block('make tits-limitations-evidence-audit')}

{command_block('make tits-threats-validity')}

{command_block('make tits-protocol-deviation')}


{command_block('make tits-author-owned-audit')}

{command_block('make tits-reproduction-time-budget')}

{command_block('make tits-run-level-provenance')}

{command_block('make tits-trace-integrity')}

{command_block('make tits-trace-schema')}

{command_block('make tits-overtake-event-consistency')}

{command_block('make tits-statistical-table-recompute')}

{command_block('make tits-results-reporting-checklist')}

{command_block('make tits-results-narrative-pack')}

{command_block('make tits-figure-source-value-recompute')}

{command_block('make tits-figure-caption-claim-audit')}

{command_block('make tits-table-caption-source-data-audit')}

{command_block('make tits-publication-gif-provenance')}

{command_block('make tits-supplementary-video-index')}

{command_block('make tits-supplementary-submission-index')}

{command_block('make tits-online-decision-case-study')}

{command_block('make tits-safety-proxy-audit')}

{command_block('make tits-source-data-schema')}

{command_block('make tits-algorithm-config-freeze')}

{command_block('make tits-compute-timing-boundary')}

{command_block('make tits-ai-tool-use-disclosure')}

{command_block('make tits-submission-gap-priority')}

{command_block('make tits-refresh-coverage')}

{command_block('make tits-audit-route')}

{command_block('make tits-audit-readme')}

{command_block('make tits-dashboard')}

## Reproduce the Frozen Confirmatory Matrix

The frozen per-case command list is the authoritative source:

`outputs/tits_dynamic_graph/v6_confirmatory_preflight/tables/v6_confirmatory_case_commands.csv`

Each row contains the exact command used for one benchmark case. The full matrix contains 30 case commands and 8 algorithms per case.

## Regenerate Summary Tables and Figures

{command_block(commands.get('confirmatory_summarize', 'missing'))}

## Re-run the Confirmatory Audit

{command_block(commands.get('confirmatory_audit', 'missing'))}

## Regenerate the Evidence Pack

{command_block(commands.get('confirmatory_evidence_pack', 'missing'))}

## Regenerate the Manuscript/Supplement Navigator

{command_block(commands.get('manuscript_supplement_navigator', '/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_manuscript_supplement_navigator.py --out-dir outputs/tits_dynamic_graph/tits_manuscript_supplement_navigator'))}

## Regenerate the Manuscript Numeric Trace Audit

{command_block(commands.get('manuscript_numeric_trace_audit', '/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_manuscript_numeric_trace_audit.py --out-dir outputs/tits_dynamic_graph/tits_manuscript_numeric_trace_audit'))}

## Regenerate the Manuscript Section Trace Audit

{command_block(commands.get('manuscript_section_trace_audit', '/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_manuscript_section_trace_audit.py --out-dir outputs/tits_dynamic_graph/tits_manuscript_section_trace_audit'))}

## Regenerate the Abstract/Highlights Evidence Audit

{command_block(commands.get('abstract_highlights_evidence_audit', '/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_abstract_highlights_evidence_audit.py --out-dir outputs/tits_dynamic_graph/tits_abstract_highlights_evidence_audit'))}

## Regenerate the Figure Source-Data and Format Audit

{command_block(commands.get('figure_source_data_audit', '/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_figure_source_data_audit.py --out-dir outputs/tits_dynamic_graph/tits_figure_source_data_audit'))}

## Regenerate the Ablation/Contribution Pack

{command_block(commands.get('ablation_contribution_pack', 'missing'))}

## Regenerate the Casewise Diagnostic Pack

{command_block(commands.get('casewise_diagnostic_pack', '/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_casewise_diagnostic_pack.py --out-dir outputs/tits_dynamic_graph/tits_casewise_diagnostic_pack'))}

## Regenerate the Baseline Fairness Audit

{command_block(commands.get('baseline_fairness_audit', '/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_baseline_fairness_audit.py --out-dir outputs/tits_dynamic_graph/tits_baseline_fairness_audit'))}

## Regenerate the Benchmark/Metric Protocol Pack

{command_block(commands.get('benchmark_protocol_pack', 'missing'))}

## Regenerate the Statistical Analysis Pack

{command_block(commands.get('statistical_analysis_pack', 'missing'))}

## Regenerate the Confirmatory Protocol/Deviation Readiness Pack

{command_block(commands.get('protocol_deviation_readiness_pack', '/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_protocol_deviation_readiness_pack.py --out-dir outputs/tits_dynamic_graph/tits_protocol_deviation_readiness_pack'))}

## Regenerate the Experimental Design, Power and Stability Audit

{command_block(commands.get('experimental_design_power_audit', '/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_experimental_design_power_audit.py --out-dir outputs/tits_dynamic_graph/tits_experimental_design_power_audit'))}

## Regenerate the Threats-to-Validity Pack

{command_block(commands.get('threats_validity_pack', 'missing'))}

## Regenerate the Runtime Scalability Pack

{command_block(commands.get('runtime_scalability_pack', '/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_runtime_scalability_pack.py --out-dir outputs/tits_dynamic_graph/tits_runtime_scalability_pack'))}

## Regenerate the Claim-Language Audit

{command_block(commands.get('claim_language_audit', '/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_claim_language_audit.py --out-dir outputs/tits_dynamic_graph/tits_claim_language_audit'))}

## Regenerate the Formal Cross-Reference Audit

{command_block(commands.get('cross_reference_audit', '/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_cross_reference_audit.py --out-dir outputs/tits_dynamic_graph/tits_cross_reference_audit'))}

## Regenerate the Source Data Integrity Audit

{command_block(commands.get('source_data_integrity_audit', '/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_source_data_integrity_audit.py --out-dir outputs/tits_dynamic_graph/tits_source_data_integrity_audit'))}

## Regenerate the Run-Level Provenance Audit

{command_block(commands.get('run_level_provenance_audit', '/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_run_level_provenance_audit.py --out-dir outputs/tits_dynamic_graph/tits_run_level_provenance_audit'))}

## Regenerate the Trace Integrity Audit

{command_block(commands.get('trace_integrity_audit', '/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_trace_integrity_audit.py --out-dir outputs/tits_dynamic_graph/tits_trace_integrity_audit'))}

## Regenerate the Overtake Event Consistency Audit

{command_block(commands.get('overtake_event_consistency_audit', '/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_overtake_event_consistency_audit.py --out-dir outputs/tits_dynamic_graph/tits_overtake_event_consistency_audit'))}

## Regenerate the Statistical Table Recompute Audit

{command_block(commands.get('statistical_table_recompute_audit', '/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_statistical_table_recompute_audit.py --out-dir outputs/tits_dynamic_graph/tits_statistical_table_recompute_audit'))}

## Regenerate the Results Reporting Checklist

{command_block(commands.get('results_reporting_checklist', '/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_results_reporting_checklist.py --out-dir outputs/tits_dynamic_graph/tits_results_reporting_checklist'))}

## Regenerate the Results Narrative Pack

{command_block(commands.get('results_narrative_pack', '/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_results_narrative_pack.py --out-dir outputs/tits_dynamic_graph/tits_results_narrative_pack'))}

## Regenerate the Figure Source-Value Recompute Audit

{command_block(commands.get('figure_source_value_recompute_audit', '/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_figure_source_value_recompute_audit.py --out-dir outputs/tits_dynamic_graph/tits_figure_source_value_recompute_audit'))}

## Regenerate the Figure Caption-Claim Audit

{command_block(commands.get('figure_caption_claim_audit', '/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_figure_caption_claim_audit.py --out-dir outputs/tits_dynamic_graph/tits_figure_caption_claim_audit'))}

## Regenerate the Table Caption/Source-Data Audit

{command_block(commands.get('table_caption_source_data_audit', '/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_table_caption_source_data_audit.py --out-dir outputs/tits_dynamic_graph/tits_table_caption_source_data_audit'))}

## Regenerate the Table Value Recompute Audit

{command_block(commands.get('table_value_recompute_audit', '/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_table_value_recompute_audit.py --out-dir outputs/tits_dynamic_graph/tits_table_value_recompute_audit'))}

## Regenerate the Open-Source Minimal Repository Audit

{command_block(commands.get('open_source_minimal_repo_audit', '/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_open_source_minimal_repo_audit.py --out-dir outputs/tits_dynamic_graph/tits_open_source_minimal_repo_audit'))}

## Regenerate the Publication GIF Provenance Audit

{command_block(commands.get('publication_gif_provenance_audit', '/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_publication_gif_provenance_audit.py --out-dir outputs/tits_dynamic_graph/tits_publication_gif_provenance_audit'))}

## Regenerate the Supplementary Video/GIF Index Pack

{command_block(commands.get('supplementary_video_index_pack', '/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_supplementary_video_index_pack.py --out-dir outputs/tits_dynamic_graph/tits_supplementary_video_index_pack'))}

## Regenerate the Supplementary Submission Index Pack

{command_block(commands.get('supplementary_submission_index_pack', '/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_supplementary_submission_index_pack.py --out-dir outputs/tits_dynamic_graph/tits_supplementary_submission_index_pack'))}

## Regenerate the Environment Reproducibility Audit

{command_block(commands.get('environment_reproducibility_audit', '/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_environment_reproducibility_audit.py --out-dir outputs/tits_dynamic_graph/tits_environment_reproducibility_audit'))}

## Regenerate the Determinism Smoke Audit

{command_block(commands.get('determinism_smoke_audit', '/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_determinism_smoke_audit.py --out-dir outputs/tits_dynamic_graph/tits_determinism_smoke_audit'))}

## Regenerate the Reproducibility Capsule

{command_block(commands.get('reproducibility_capsule', '/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_reproducibility_capsule.py --out-dir outputs/tits_dynamic_graph/tits_reproducibility_capsule'))}

## Regenerate the Data Leakage and Tuning-Provenance Audit

{command_block(commands.get('data_leakage_tuning_audit', '/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_data_leakage_tuning_audit.py --out-dir outputs/tits_dynamic_graph/tits_data_leakage_tuning_audit'))}

## Regenerate the Innovation-to-Evidence Traceability Matrix

{command_block(commands.get('innovation_evidence_traceability', '/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_innovation_evidence_traceability.py --out-dir outputs/tits_dynamic_graph/tits_innovation_evidence_traceability'))}

## Regenerate the Metric-Threshold Sensitivity Audit

{command_block(commands.get('metric_sensitivity_audit', '/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_metric_sensitivity_audit.py --out-dir outputs/tits_dynamic_graph/tits_metric_sensitivity_audit'))}

## Regenerate the Model Artifact Integrity Audit

{command_block(commands.get('model_artifact_integrity_audit', '/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_model_artifact_integrity_audit.py --out-dir outputs/tits_dynamic_graph/tits_model_artifact_integrity_audit'))}

## Regenerate the Submission Metadata Pack

{command_block(commands.get('submission_metadata_pack', '/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_submission_metadata_pack.py --out-dir outputs/tits_dynamic_graph/tits_submission_metadata_pack'))}

## Regenerate the GitHub Release Readiness Pack

{command_block(commands.get('github_release_readiness_pack', '/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_github_release_readiness_pack.py --out-dir outputs/tits_dynamic_graph/tits_github_release_readiness_pack'))}

## Regenerate the Status Snapshot

{command_block(commands.get('status_snapshot', '/home/itrc/.conda/envs/vlm_planner/bin/python scripts/print_tits_status.py --out-dir outputs/tits_dynamic_graph/tits_status_snapshot'))}

## Regenerate the Evidence Ledger

{command_block(commands.get('evidence_ledger', '/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_evidence_ledger.py --out-dir outputs/tits_dynamic_graph/tits_evidence_ledger'))}

## Regenerate the Claim Numeric Consistency Audit

{command_block(commands.get('claim_numeric_consistency_audit', '/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_claim_numeric_consistency_audit.py --out-dir outputs/tits_dynamic_graph/tits_claim_numeric_consistency_audit'))}

## Regenerate the Checksum Verification Audit

{command_block(commands.get('checksum_verification_audit', '/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_checksum_verification_audit.py --out-dir outputs/tits_dynamic_graph/tits_checksum_verification_audit'))}

## Regenerate the External Validity Boundary Audit

{command_block(commands.get('external_validity_boundary_audit', '/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_external_validity_boundary_audit.py --out-dir outputs/tits_dynamic_graph/tits_external_validity_boundary_audit'))}

## Regenerate the Limitations Evidence Audit

{command_block(commands.get('limitations_evidence_audit', '/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_limitations_evidence_audit.py --out-dir outputs/tits_dynamic_graph/tits_limitations_evidence_audit'))}

## Regenerate the Author-Owned Submission Integrity Audit

{command_block(commands.get('author_owned_submission_integrity_audit', '/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_author_owned_submission_integrity_audit.py --out-dir outputs/tits_dynamic_graph/tits_author_owned_submission_integrity_audit'))}

## Regenerate the Submission Gap Priority Audit

{command_block(commands.get('submission_gap_priority_audit', '/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_submission_gap_priority_audit.py --out-dir outputs/tits_dynamic_graph/tits_submission_gap_priority_audit'))}

## Regenerate the Reviewer Reproduction Time-Budget Audit

{command_block(commands.get('reviewer_reproduction_time_budget_audit', '/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_reviewer_reproduction_time_budget_audit.py --out-dir outputs/tits_dynamic_graph/tits_reviewer_reproduction_time_budget_audit'))}

## Regenerate the Artifact Manifest

{command_block('/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_dynamic_graph_artifact_manifest.py --root . --out-dir outputs/tits_dynamic_graph/artifact_manifest')}

## Primary Files to Inspect

- Main report: `outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack/materials/CONFIRMATORY_EVIDENCE_REPORT.md`
- Status snapshot: `outputs/tits_dynamic_graph/tits_status_snapshot/TITS_STATUS_SNAPSHOT.md`
- Evidence ledger: `outputs/tits_dynamic_graph/tits_evidence_ledger/materials/EVIDENCE_LEDGER.md`
- Claim numeric consistency audit: `outputs/tits_dynamic_graph/tits_claim_numeric_consistency_audit/materials/CLAIM_NUMERIC_CONSISTENCY_AUDIT.md`
- Abstract/highlights evidence audit: `outputs/tits_dynamic_graph/tits_abstract_highlights_evidence_audit/materials/ABSTRACT_HIGHLIGHTS_EVIDENCE_AUDIT.md`
- Checksum verification audit: `outputs/tits_dynamic_graph/tits_checksum_verification_audit/materials/CHECKSUM_VERIFICATION_AUDIT.md`
- External validity boundary audit: `outputs/tits_dynamic_graph/tits_external_validity_boundary_audit/materials/EXTERNAL_VALIDITY_BOUNDARY_AUDIT.md`
- Limitations evidence audit: `outputs/tits_dynamic_graph/tits_limitations_evidence_audit/materials/LIMITATIONS_EVIDENCE_AUDIT.md`
- Confirmatory protocol/deviation readiness report: `outputs/tits_dynamic_graph/tits_protocol_deviation_readiness_pack/materials/PROTOCOL_DEVIATION_READINESS_REPORT.md`
- Author-owned submission integrity audit: `outputs/tits_dynamic_graph/tits_author_owned_submission_integrity_audit/materials/AUTHOR_OWNED_SUBMISSION_INTEGRITY_AUDIT.md`
- Submission gap priority audit: `outputs/tits_dynamic_graph/tits_submission_gap_priority_audit/materials/SUBMISSION_GAP_PRIORITY_AUDIT.md`
- Reviewer reproduction time-budget audit: `outputs/tits_dynamic_graph/tits_reviewer_reproduction_time_budget_audit/materials/REVIEWER_REPRODUCTION_TIME_BUDGET_AUDIT.md`
- Manuscript/supplement navigator: `outputs/tits_dynamic_graph/tits_manuscript_supplement_navigator/materials/MANUSCRIPT_SUPPLEMENT_NAVIGATOR.md`
- Manuscript numeric trace audit: `outputs/tits_dynamic_graph/tits_manuscript_numeric_trace_audit/materials/MANUSCRIPT_NUMERIC_TRACE_AUDIT.md`
- Manuscript section trace audit: `outputs/tits_dynamic_graph/tits_manuscript_section_trace_audit/materials/MANUSCRIPT_SECTION_TRACE_AUDIT.md`
- Figure/table placement plan: `outputs/tits_dynamic_graph/tits_manuscript_supplement_navigator/materials/FIGURE_TABLE_PLACEMENT_PLAN.md`
- Source-data crosswalk: `outputs/tits_dynamic_graph/tits_manuscript_supplement_navigator/tables/source_data_crosswalk.csv`
- Figure source-data and format audit: `outputs/tits_dynamic_graph/tits_figure_source_data_audit/materials/FIGURE_SOURCE_DATA_AUDIT.md`
- Failure atlas: `outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack/materials/FAILURE_ATLAS.md`
- Compute report: `outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack/materials/COMPUTE_AND_REPRODUCIBILITY_REPORT.md`
- Main result table: `outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_main_results.md`
- Source data: `outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv`
- Source data integrity audit: `outputs/tits_dynamic_graph/tits_source_data_integrity_audit/materials/SOURCE_DATA_INTEGRITY_AUDIT.md`
- Run-level provenance audit: `outputs/tits_dynamic_graph/tits_run_level_provenance_audit/materials/RUN_LEVEL_PROVENANCE_AUDIT.md`
- Trace integrity audit: `outputs/tits_dynamic_graph/tits_trace_integrity_audit/materials/TRACE_INTEGRITY_AUDIT.md`
- Overtake event consistency audit: `outputs/tits_dynamic_graph/tits_overtake_event_consistency_audit/materials/OVERTAKE_EVENT_CONSISTENCY_AUDIT.md`
- Statistical table recompute audit: `outputs/tits_dynamic_graph/tits_statistical_table_recompute_audit/materials/STATISTICAL_TABLE_RECOMPUTE_AUDIT.md`
- Results reporting checklist: `outputs/tits_dynamic_graph/tits_results_reporting_checklist/materials/RESULTS_REPORTING_CHECKLIST.md`
- Results narrative pack: `outputs/tits_dynamic_graph/tits_results_narrative_pack/materials/RESULTS_NARRATIVE_PACK.md`
- Figure source-value recompute audit: `outputs/tits_dynamic_graph/tits_figure_source_value_recompute_audit/materials/FIGURE_SOURCE_VALUE_RECOMPUTE_AUDIT.md`
- Figure caption-claim audit: `outputs/tits_dynamic_graph/tits_figure_caption_claim_audit/materials/FIGURE_CAPTION_CLAIM_AUDIT.md`
- Table caption/source-data audit: `outputs/tits_dynamic_graph/tits_table_caption_source_data_audit/materials/TABLE_CAPTION_SOURCE_DATA_AUDIT.md`
- Table value recompute audit: `outputs/tits_dynamic_graph/tits_table_value_recompute_audit/materials/TABLE_VALUE_RECOMPUTE_AUDIT.md`
- Open-source minimal repository audit: `outputs/tits_dynamic_graph/tits_open_source_minimal_repo_audit/materials/OPEN_SOURCE_MINIMAL_REPO_AUDIT.md`
- Publication GIF provenance audit: `outputs/tits_dynamic_graph/tits_publication_gif_provenance_audit/materials/PUBLICATION_GIF_PROVENANCE_AUDIT.md`
- Supplementary video index: `outputs/tits_dynamic_graph/tits_supplementary_video_index_pack/materials/SUPPLEMENTARY_VIDEO_INDEX.md`
- Supplementary submission index: `outputs/tits_dynamic_graph/tits_supplementary_submission_index_pack/materials/SUPPLEMENTARY_SUBMISSION_INDEX.md`
- Environment reproducibility audit: `outputs/tits_dynamic_graph/tits_environment_reproducibility_audit/materials/ENVIRONMENT_REPRODUCIBILITY_AUDIT.md`
- Determinism smoke audit: `outputs/tits_dynamic_graph/tits_determinism_smoke_audit/materials/DETERMINISM_SMOKE_AUDIT.md`
- Reproducibility capsule: `outputs/tits_dynamic_graph/tits_reproducibility_capsule/materials/REPRODUCIBILITY_CAPSULE.md`
- Data leakage and tuning-provenance audit: `outputs/tits_dynamic_graph/tits_data_leakage_tuning_audit/materials/DATA_LEAKAGE_AND_TUNING_PROVENANCE_AUDIT.md`
- Innovation-to-evidence traceability report: `outputs/tits_dynamic_graph/tits_innovation_evidence_traceability/materials/INNOVATION_EVIDENCE_TRACEABILITY_REPORT.md`
- Metric-threshold sensitivity audit: `outputs/tits_dynamic_graph/tits_metric_sensitivity_audit/materials/METRIC_SENSITIVITY_AUDIT.md`
- Model artifact integrity audit: `outputs/tits_dynamic_graph/tits_model_artifact_integrity_audit/materials/MODEL_ARTIFACT_INTEGRITY_AUDIT.md`
- Paired tests: `outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack/tables/confirmatory_paired_tests_vs_dlc.csv`
- Ablation/contribution report: `outputs/tits_dynamic_graph/tits_ablation_contribution_pack/materials/CONTRIBUTION_ATTRIBUTION_REPORT.md`
- Ablation/contribution figure QA: `outputs/tits_dynamic_graph/tits_ablation_contribution_pack/materials/CONTRIBUTION_ATTRIBUTION_QA.json`
- Casewise diagnostic report: `outputs/tits_dynamic_graph/tits_casewise_diagnostic_pack/materials/CASEWISE_OVERTAKING_DIAGNOSTIC_REPORT.md`
- Casewise pairwise win/loss table: `outputs/tits_dynamic_graph/tits_casewise_diagnostic_pack/tables/casewise_pairwise_win_loss_summary.csv`
- Casewise failure-mode summary: `outputs/tits_dynamic_graph/tits_casewise_diagnostic_pack/tables/casewise_failure_mode_summary.csv`
- Casewise worst-case cards: `outputs/tits_dynamic_graph/tits_casewise_diagnostic_pack/tables/casewise_worst_case_cards.csv`
- Baseline fairness audit: `outputs/tits_dynamic_graph/tits_baseline_fairness_audit/materials/BASELINE_FAIRNESS_AUDIT.md`
- Fairness command checks: `outputs/tits_dynamic_graph/tits_baseline_fairness_audit/tables/fairness_command_checks.csv`
- Fairness summary-run checks: `outputs/tits_dynamic_graph/tits_baseline_fairness_audit/tables/fairness_summary_run_checks.csv`
- Benchmark/metric protocol card: `outputs/tits_dynamic_graph/tits_benchmark_protocol_pack/materials/BENCHMARK_METRIC_PROTOCOL_CARD.md`
- Metric dictionary: `outputs/tits_dynamic_graph/tits_benchmark_protocol_pack/tables/metric_dictionary.csv`
- Statistical analysis plan: `outputs/tits_dynamic_graph/tits_statistical_analysis_pack/materials/STATISTICAL_ANALYSIS_PLAN.md`
- Holm-adjusted primary hypotheses: `outputs/tits_dynamic_graph/tits_statistical_analysis_pack/tables/statistical_primary_holm.csv`
- Endpoint hierarchy and protocol deviation register:
  - `outputs/tits_dynamic_graph/tits_protocol_deviation_readiness_pack/tables/endpoint_hierarchy.csv`
  - `outputs/tits_dynamic_graph/tits_protocol_deviation_readiness_pack/tables/protocol_deviation_register.csv`
- Experimental design and stability audit: `outputs/tits_dynamic_graph/tits_experimental_design_power_audit/materials/EXPERIMENTAL_DESIGN_POWER_AUDIT.md`
- Threats-to-validity dossier: `outputs/tits_dynamic_graph/tits_threats_validity_pack/materials/THREATS_TO_VALIDITY_DOSSIER.md`
- Reviewer risk response map: `outputs/tits_dynamic_graph/tits_threats_validity_pack/materials/REVIEWER_RISK_RESPONSE_MAP.md`
- Runtime scalability report: `outputs/tits_dynamic_graph/tits_runtime_scalability_pack/materials/RUNTIME_SCALABILITY_AND_COMPLEXITY_REPORT.md`
- Runtime scalability table: `outputs/tits_dynamic_graph/tits_runtime_scalability_pack/tables/runtime_scalability_by_vehicle_count.csv`
- Runtime complexity crosswalk: `outputs/tits_dynamic_graph/tits_runtime_scalability_pack/tables/runtime_complexity_crosswalk.csv`
- Claim-language audit: `outputs/tits_dynamic_graph/tits_claim_language_audit/materials/CLAIM_LANGUAGE_AUDIT.md`
- Formal cross-reference audit: `outputs/tits_dynamic_graph/tits_cross_reference_audit/materials/FORMAL_CROSS_REFERENCE_AUDIT.md`
- Submission metadata pack: `outputs/tits_dynamic_graph/tits_submission_metadata_pack/materials/IEEE_TITS_SUBMISSION_METADATA_PACK.md`
- GitHub release readiness pack: `outputs/tits_dynamic_graph/tits_github_release_readiness_pack/materials/GITHUB_RELEASE_READINESS_PACK.md`
- GitHub README draft: `outputs/tits_dynamic_graph/tits_github_release_readiness_pack/materials/GITHUB_README_DRAFT.md`
- Representative GIF manifest: `outputs/tits_dynamic_graph/publication_gifs/publication_gif_manifest.md`
- Artifact manifest: `outputs/tits_dynamic_graph/artifact_manifest/tits_dynamic_graph_artifact_manifest.md`

## Interpretation Boundary

The confirmatory evidence supports the benchmark claim: the optimized DLC world model with runtime dynamic neighborhoods improves online overtaking quality and efficiency over the original DLC world model under the evaluated procedural, vehicle-count extrapolation, and Monza external-track settings. It does not prove arbitrary real-world deployment or unlimited traffic-density generalization.
"""


def build_data_code_availability():
    return """# Data and Code Availability Draft

## Code Availability

The code required to reproduce the dynamic-neighborhood DLC world-model experiments is contained in this repository. The key entry points are:

- `scripts/run_tits_dynamic_graph_evaluation.py`
- `scripts/summarize_tits_dynamic_graph_online.py`
- `scripts/audit_v6_confirmatory_matrix.py`
- `scripts/export_tits_confirmatory_evidence_pack.py`
- `scripts/export_tits_dynamic_graph_artifact_manifest.py`
- `dlc/graph_world_model.py`
- `dlc/graph_policy.py`
- `dlc/policies.py`
- `gym_multi_car_racing/multi_car_racing.py`

## Data Availability

The confirmatory online benchmark source data are available at:

- `outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv`

The source data include benchmark ID, algorithm, seed, vehicle count, track path, overtake metrics, grass/off-track metrics, recovery metrics, latency metrics, and the path to each run summary file.

## Model and Track Artifacts

- Main model: `outputs/tits_dynamic_graph/models/ours_dynamic_graph_dlc_world/graph_risk_dlc_world.graphworld.pt`
- Quality proposal model: `outputs/tits_dynamic_graph/models/quality_graph_bc_v1/graph_bc.graph.pt`
- DLC world-model baseline weights: `outputs/paper_multicar_overtake_20260618/models/graph_risk_world_model/graph_risk_dlc_world.graphworld.pt`
- DLC world-model variant weights: `outputs/paper_multicar_overtake_20260618/models/graph_risk_world_model_variants/`
- Monza scaled track: `tracks/monza_scaled.npz`
- Monza track metadata: `tracks/monza_scaled.json`

## Provenance and Checksums

The artifact manifest with SHA256 checksums is:

- `outputs/tits_dynamic_graph/artifact_manifest/tits_dynamic_graph_artifact_manifest_files.csv`
- `outputs/tits_dynamic_graph/tits_reproducibility_capsule/materials/REPRODUCIBILITY_CAPSULE.md`

The human-readable manifest is:

- `outputs/tits_dynamic_graph/artifact_manifest/tits_dynamic_graph_artifact_manifest.md`

## Confirmatory Protocol Boundary

The endpoint hierarchy, analysis population rules, protocol/deviation register and claim guardrails are generated at:

- `outputs/tits_dynamic_graph/tits_protocol_deviation_readiness_pack/materials/PROTOCOL_DEVIATION_READINESS_REPORT.md`
- `outputs/tits_dynamic_graph/tits_protocol_deviation_readiness_pack/tables/endpoint_hierarchy.csv`
- `outputs/tits_dynamic_graph/tits_protocol_deviation_readiness_pack/tables/protocol_deviation_register.csv`

## Reuse Boundary

The released artifacts support reproduction of the simulation benchmark and figures. They do not by themselves certify real-vehicle safety or deployment readiness.

## Container Reproducibility Boundary

Docker/Apptainer container specifications are treated as release-preparation artifacts rather than certified archival images in the current package. The repository records dependency metadata, checksums, and smoke-test routes needed to build a container, but the final public container image, registry location, image digest, and license review must be completed by the authors before journal submission or public release.

## GitHub Release Preparation

The author-facing GitHub README, citation, contribution, model-card and data-card drafts are generated at:

- `outputs/tits_dynamic_graph/tits_github_release_readiness_pack/materials/GITHUB_RELEASE_READINESS_PACK.md`
"""


def build_submission_checklist(readiness, confirmatory_audit, evidence):
    checks = [
        ("Readiness audit PASS", readiness.get("status") == "PASS", "outputs/tits_dynamic_graph/tits_readiness_audit.json"),
        ("Confirmatory matrix complete", confirmatory_audit.get("summary", {}).get("status") == "complete", "outputs/tits_dynamic_graph/v6_confirmatory_preflight/v6_confirmatory_matrix_audit.json"),
        ("240 algorithm-runs present", confirmatory_audit.get("summary", {}).get("existing_summaries") == 240, "outputs/tits_dynamic_graph/v6_confirmatory_matrix"),
        ("Evidence pack complete", evidence.get("status") == "complete", "outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack/confirmatory_evidence_pack_manifest.json"),
        ("Source CSV available", True, "outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv"),
        ("Source data integrity audit available", True, "outputs/tits_dynamic_graph/tits_source_data_integrity_audit/materials/SOURCE_DATA_INTEGRITY_AUDIT.md"),
        ("Run-level provenance audit available", True, "outputs/tits_dynamic_graph/tits_run_level_provenance_audit/tits_run_level_provenance_audit_manifest.json"),
        ("Trace integrity audit available", True, "outputs/tits_dynamic_graph/tits_trace_integrity_audit/tits_trace_integrity_audit_manifest.json"),
        ("Overtake event consistency audit available", True, "outputs/tits_dynamic_graph/tits_overtake_event_consistency_audit/tits_overtake_event_consistency_audit_manifest.json"),
        ("Statistical table recompute audit available", True, "outputs/tits_dynamic_graph/tits_statistical_table_recompute_audit/tits_statistical_table_recompute_audit_manifest.json"),
        ("Figure source-value recompute audit available", True, "outputs/tits_dynamic_graph/tits_figure_source_value_recompute_audit/tits_figure_source_value_recompute_audit_manifest.json"),
        ("Table caption/source-data audit available", True, "outputs/tits_dynamic_graph/tits_table_caption_source_data_audit/tits_table_caption_source_data_audit_manifest.json"),
        ("Table value recompute audit available", True, "outputs/tits_dynamic_graph/tits_table_value_recompute_audit/tits_table_value_recompute_audit_manifest.json"),
        ("Open-source minimal repository audit available", True, "outputs/tits_dynamic_graph/tits_open_source_minimal_repo_audit/tits_open_source_minimal_repo_audit_manifest.json"),
        ("Publication GIF provenance audit available", True, "outputs/tits_dynamic_graph/tits_publication_gif_provenance_audit/tits_publication_gif_provenance_audit_manifest.json"),
        ("Supplementary video/GIF index pack available", True, "outputs/tits_dynamic_graph/tits_supplementary_video_index_pack/tits_supplementary_video_index_pack_manifest.json"),
        ("Supplementary submission index pack available", True, "outputs/tits_dynamic_graph/tits_supplementary_submission_index_pack/tits_supplementary_submission_index_pack_manifest.json"),
        ("Environment reproducibility audit available", True, "outputs/tits_dynamic_graph/tits_environment_reproducibility_audit/materials/ENVIRONMENT_REPRODUCIBILITY_AUDIT.md"),
        ("Determinism smoke audit available", True, "outputs/tits_dynamic_graph/tits_determinism_smoke_audit/tits_determinism_smoke_audit_manifest.json"),
        ("Reproducibility capsule available", True, "outputs/tits_dynamic_graph/tits_reproducibility_capsule/tits_reproducibility_capsule_manifest.json"),
        ("Data leakage/tuning-provenance audit available", True, "outputs/tits_dynamic_graph/tits_data_leakage_tuning_audit/tits_data_leakage_tuning_audit_manifest.json"),
        ("Innovation-to-evidence traceability matrix available", True, "outputs/tits_dynamic_graph/tits_innovation_evidence_traceability/tits_innovation_evidence_traceability_manifest.json"),
        ("Metric-threshold sensitivity audit available", True, "outputs/tits_dynamic_graph/tits_metric_sensitivity_audit/tits_metric_sensitivity_audit_manifest.json"),
        ("Model artifact integrity audit available", True, "outputs/tits_dynamic_graph/tits_model_artifact_integrity_audit/materials/MODEL_ARTIFACT_INTEGRITY_AUDIT.md"),
        ("Manuscript/supplement navigator available", True, "outputs/tits_dynamic_graph/tits_manuscript_supplement_navigator/materials/MANUSCRIPT_SUPPLEMENT_NAVIGATOR.md"),
        ("Manuscript numeric trace audit available", True, "outputs/tits_dynamic_graph/tits_manuscript_numeric_trace_audit/tits_manuscript_numeric_trace_audit_manifest.json"),
        ("Manuscript section trace audit available", True, "outputs/tits_dynamic_graph/tits_manuscript_section_trace_audit/tits_manuscript_section_trace_audit_manifest.json"),
        ("Figure source-data and format audit available", True, "outputs/tits_dynamic_graph/tits_figure_source_data_audit/tits_figure_source_data_audit_manifest.json"),
        ("Chinese analysis figure available", True, "outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack/figures/figure_confirmatory_overtake_evidence_cn.png"),
        ("Ablation/contribution pack available", True, "outputs/tits_dynamic_graph/tits_ablation_contribution_pack/tits_ablation_contribution_pack_manifest.json"),
        ("Casewise diagnostic pack available", True, "outputs/tits_dynamic_graph/tits_casewise_diagnostic_pack/tits_casewise_diagnostic_pack_manifest.json"),
        ("Baseline fairness audit available", True, "outputs/tits_dynamic_graph/tits_baseline_fairness_audit/tits_baseline_fairness_audit_manifest.json"),
        ("Benchmark/metric protocol pack available", True, "outputs/tits_dynamic_graph/tits_benchmark_protocol_pack/tits_benchmark_protocol_pack_manifest.json"),
        ("Statistical analysis pack available", True, "outputs/tits_dynamic_graph/tits_statistical_analysis_pack/tits_statistical_analysis_pack_manifest.json"),
        ("Experimental design/power/stability audit available", True, "outputs/tits_dynamic_graph/tits_experimental_design_power_audit/tits_experimental_design_power_audit_manifest.json"),
        ("Threats-to-validity pack available", True, "outputs/tits_dynamic_graph/tits_threats_validity_pack/tits_threats_validity_pack_manifest.json"),
        ("Runtime scalability pack available", True, "outputs/tits_dynamic_graph/tits_runtime_scalability_pack/tits_runtime_scalability_pack_manifest.json"),
        ("Claim-language audit available", True, "outputs/tits_dynamic_graph/tits_claim_language_audit/tits_claim_language_audit_manifest.json"),
        ("Formal cross-reference audit available", True, "outputs/tits_dynamic_graph/tits_cross_reference_audit/materials/FORMAL_CROSS_REFERENCE_AUDIT.md"),
        ("Submission metadata pack available", True, "outputs/tits_dynamic_graph/tits_submission_metadata_pack/tits_submission_metadata_pack_manifest.json"),
        ("GitHub release readiness pack available", True, "outputs/tits_dynamic_graph/tits_github_release_readiness_pack/tits_github_release_readiness_pack_manifest.json"),
        ("Top-down and first-person GIF manifest available", True, "outputs/tits_dynamic_graph/publication_gifs/publication_gif_manifest.md"),
        ("Checksum verification audit available", True, "outputs/tits_dynamic_graph/tits_checksum_verification_audit/tits_checksum_verification_audit_manifest.json"),
        ("External validity boundary audit available", True, "outputs/tits_dynamic_graph/tits_external_validity_boundary_audit/tits_external_validity_boundary_audit_manifest.json"),
        ("Limitations evidence audit available", True, "outputs/tits_dynamic_graph/tits_limitations_evidence_audit/tits_limitations_evidence_audit_manifest.json"),
        ("Confirmatory protocol/deviation readiness pack available", True, "outputs/tits_dynamic_graph/tits_protocol_deviation_readiness_pack/tits_protocol_deviation_readiness_pack_manifest.json"),
        ("Author-owned submission integrity audit available", True, "outputs/tits_dynamic_graph/tits_author_owned_submission_integrity_audit/tits_author_owned_submission_integrity_audit_manifest.json"),
        ("Reviewer reproduction time-budget audit available", True, "outputs/tits_dynamic_graph/tits_reviewer_reproduction_time_budget_audit/tits_reviewer_reproduction_time_budget_audit_manifest.json"),
        ("SHA256 artifact manifest available", True, "outputs/tits_dynamic_graph/artifact_manifest/tits_dynamic_graph_artifact_manifest_files.csv"),
    ]
    lines = [
        "# Submission Readiness Checklist",
        "",
        "| Item | Status | Evidence |",
        "|---|---|---|",
    ]
    for name, ok, evidence_path in checks:
        lines.append(f"| {name} | {'PASS' if ok else 'CHECK'} | `{evidence_path}` |")
    lines.extend(
        [
            "",
            "## Author-Side Items Still Requiring Manual Confirmation",
            "",
            "- Final manuscript numbers match the source CSV and evidence report.",
            "- Figure/table captions match the final figure numbering.",
            "- License, data repository DOI, and anonymization requirements are finalized.",
            "- AI tool disclosure, conflict-of-interest, and author contribution statements are completed.",
            "- Any claims beyond this simulator benchmark are clearly marked as future work or limitations.",
        ]
    )
    return "\n".join(lines)


def build_method_result_map():
    return """# Method and Results Writing Map

## Method Section

- Dynamic graph observation and runtime neighbor construction:
  - `configs/tits_dynamic_graph_experiments.json`
  - `dlc/graph_world_model.py`
  - `dlc/graph_policy.py`
- Online evaluation protocol:
  - `docs/tits_dynamic_graph_reproducibility_protocol.md`
  - `scripts/run_tits_dynamic_graph_evaluation.py`
- Benchmark definition:
  - procedural n=4/5/6
  - vehicle-count extrapolation n=8
  - Monza external CSV track n=4/6
- Benchmark/metric protocol card:
  - `outputs/tits_dynamic_graph/tits_benchmark_protocol_pack/materials/BENCHMARK_METRIC_PROTOCOL_CARD.md`
  - `outputs/tits_dynamic_graph/tits_benchmark_protocol_pack/tables/benchmark_cards.csv`
  - `outputs/tits_dynamic_graph/tits_benchmark_protocol_pack/tables/metric_dictionary.csv`
- Confirmatory endpoint hierarchy and protocol/deviation boundaries:
  - `outputs/tits_dynamic_graph/tits_protocol_deviation_readiness_pack/materials/PROTOCOL_DEVIATION_READINESS_REPORT.md`
  - `outputs/tits_dynamic_graph/tits_protocol_deviation_readiness_pack/tables/endpoint_hierarchy.csv`
  - `outputs/tits_dynamic_graph/tits_protocol_deviation_readiness_pack/tables/analysis_population_rules.csv`
  - `outputs/tits_dynamic_graph/tits_protocol_deviation_readiness_pack/tables/protocol_deviation_register.csv`
- Manuscript/supplement navigation:
  - `outputs/tits_dynamic_graph/tits_manuscript_supplement_navigator/materials/MANUSCRIPT_SUPPLEMENT_NAVIGATOR.md`
  - `outputs/tits_dynamic_graph/tits_manuscript_supplement_navigator/materials/FIGURE_TABLE_PLACEMENT_PLAN.md`
  - `outputs/tits_dynamic_graph/tits_manuscript_supplement_navigator/tables/source_data_crosswalk.csv`
- Figure source-data and format audit:
  - `outputs/tits_dynamic_graph/tits_figure_source_data_audit/materials/FIGURE_SOURCE_DATA_AUDIT.md`
  - `outputs/tits_dynamic_graph/tits_figure_source_data_audit/tables/figure_source_data_checks.csv`
- Figure source-value recompute audit:
  - `outputs/tits_dynamic_graph/tits_figure_source_value_recompute_audit/materials/FIGURE_SOURCE_VALUE_RECOMPUTE_AUDIT.md`
  - `outputs/tits_dynamic_graph/tits_figure_source_value_recompute_audit/tables/figure_source_value_recompute_rows.csv`
- Table value recompute audit:
  - `outputs/tits_dynamic_graph/tits_table_value_recompute_audit/materials/TABLE_VALUE_RECOMPUTE_AUDIT.md`
  - `outputs/tits_dynamic_graph/tits_table_value_recompute_audit/tables/table_value_recompute_rows.csv`
- Open-source minimal repository audit:
  - `outputs/tits_dynamic_graph/tits_open_source_minimal_repo_audit/materials/OPEN_SOURCE_MINIMAL_REPO_AUDIT.md`
  - `outputs/tits_dynamic_graph/tits_open_source_minimal_repo_audit/tables/minimal_repo_audit_checks.csv`
- Publication GIF provenance audit:
  - `outputs/tits_dynamic_graph/tits_publication_gif_provenance_audit/materials/PUBLICATION_GIF_PROVENANCE_AUDIT.md`
  - `outputs/tits_dynamic_graph/tits_publication_gif_provenance_audit/tables/publication_gif_provenance_rows.csv`
- Supplementary Video/GIF index:
  - `outputs/tits_dynamic_graph/tits_supplementary_video_index_pack/materials/SUPPLEMENTARY_VIDEO_INDEX.md`
  - `outputs/tits_dynamic_graph/tits_supplementary_video_index_pack/tables/supplementary_video_index.csv`
- Supplementary submission index:
  - `outputs/tits_dynamic_graph/tits_supplementary_submission_index_pack/materials/SUPPLEMENTARY_SUBMISSION_INDEX.md`
  - `outputs/tits_dynamic_graph/tits_supplementary_submission_index_pack/tables/supplementary_submission_items.csv`
- Metrics:
  - overtake success
  - on-track overtake rate
  - desirable overtaking behavior rate
  - start-to-completion overtake time
  - target grass rate
  - grass recovery time
  - decision latency

## Results Section

- Main table:
  - `outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_main_results.md`
- Manuscript numeric trace:
  - `outputs/tits_dynamic_graph/tits_manuscript_package/tables/manuscript_numeric_index.csv`
  - `outputs/tits_dynamic_graph/tits_manuscript_numeric_trace_audit/materials/MANUSCRIPT_NUMERIC_TRACE_AUDIT.md`
  - `outputs/tits_dynamic_graph/tits_manuscript_numeric_trace_audit/tables/manuscript_numeric_trace_rows.csv`
- Main source data:
  - `outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv`
- Source-data integrity:
  - `outputs/tits_dynamic_graph/tits_source_data_integrity_audit/materials/SOURCE_DATA_INTEGRITY_AUDIT.md`
  - `outputs/tits_dynamic_graph/tits_source_data_integrity_audit/tables/source_data_case_matrix.csv`
- Environment and command reproducibility:
  - `outputs/tits_dynamic_graph/tits_environment_reproducibility_audit/materials/ENVIRONMENT_REPRODUCIBILITY_AUDIT.md`
  - `outputs/tits_dynamic_graph/tits_environment_reproducibility_audit/tables/environment_module_versions.csv`
- Determinism smoke reproducibility:
  - `outputs/tits_dynamic_graph/tits_determinism_smoke_audit/materials/DETERMINISM_SMOKE_AUDIT.md`
  - `outputs/tits_dynamic_graph/tits_determinism_smoke_audit/tables/determinism_smoke_comparison.csv`
- Reproducibility capsule:
  - `outputs/tits_dynamic_graph/tits_reproducibility_capsule/materials/REPRODUCIBILITY_CAPSULE.md`
  - `outputs/tits_dynamic_graph/tits_reproducibility_capsule/tables/reproducibility_result_metric_fingerprints.csv`
  - `outputs/tits_dynamic_graph/tits_reproducibility_capsule/run_reproducibility_capsule_check.sh`
- Data leakage and tuning provenance:
  - `outputs/tits_dynamic_graph/tits_data_leakage_tuning_audit/materials/DATA_LEAKAGE_AND_TUNING_PROVENANCE_AUDIT.md`
  - `outputs/tits_dynamic_graph/tits_data_leakage_tuning_audit/tables/case_split_boundary.csv`
  - `outputs/tits_dynamic_graph/tits_data_leakage_tuning_audit/tables/exploratory_output_boundary.csv`
- Innovation-to-evidence traceability:
  - `outputs/tits_dynamic_graph/tits_innovation_evidence_traceability/materials/INNOVATION_EVIDENCE_TRACEABILITY_REPORT.md`
  - `outputs/tits_dynamic_graph/tits_innovation_evidence_traceability/tables/innovation_to_code_map.csv`
  - `outputs/tits_dynamic_graph/tits_innovation_evidence_traceability/tables/innovation_to_experiment_map.csv`
  - `outputs/tits_dynamic_graph/tits_innovation_evidence_traceability/tables/method_section_writing_matrix.csv`
  - `outputs/tits_dynamic_graph/tits_innovation_evidence_traceability/tables/method_algorithm_box.csv`
  - `outputs/tits_dynamic_graph/tits_innovation_evidence_traceability/tables/method_notation_table.csv`
  - `outputs/tits_dynamic_graph/tits_innovation_evidence_traceability/tables/method_complexity_boundary.csv`
- Metric-threshold sensitivity:
  - `outputs/tits_dynamic_graph/tits_metric_sensitivity_audit/materials/METRIC_SENSITIVITY_AUDIT.md`
  - `outputs/tits_dynamic_graph/tits_metric_sensitivity_audit/tables/quality_threshold_sensitivity_grid.csv`
  - `outputs/tits_dynamic_graph/tits_metric_sensitivity_audit/tables/paired_threshold_sensitivity_vs_dlc.csv`
  - `outputs/tits_dynamic_graph/tits_metric_sensitivity_audit/tables/robustness_summary_by_algorithm.csv`
- Model artifact reproducibility:
  - `outputs/tits_dynamic_graph/tits_model_artifact_integrity_audit/materials/MODEL_ARTIFACT_INTEGRITY_AUDIT.md`
  - `outputs/tits_dynamic_graph/tits_model_artifact_integrity_audit/tables/model_artifact_inventory.csv`
  - `outputs/tits_dynamic_graph/tits_model_artifact_integrity_audit/tables/model_algorithm_path_crosswalk.csv`
- Paired statistical tests:
  - `outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack/tables/confirmatory_paired_tests_vs_dlc.csv`
- Multiplicity-controlled statistical reporting:
  - `outputs/tits_dynamic_graph/tits_statistical_analysis_pack/materials/STATISTICAL_ANALYSIS_PLAN.md`
  - `outputs/tits_dynamic_graph/tits_statistical_analysis_pack/tables/statistical_primary_holm.csv`
  - `outputs/tits_dynamic_graph/tits_statistical_analysis_pack/tables/statistical_effect_sizes.csv`
- Confirmatory/exploratory endpoint boundary:
  - `outputs/tits_dynamic_graph/tits_protocol_deviation_readiness_pack/materials/PROTOCOL_DEVIATION_READINESS_REPORT.md`
  - `outputs/tits_dynamic_graph/tits_protocol_deviation_readiness_pack/tables/endpoint_hierarchy.csv`
  - `outputs/tits_dynamic_graph/tits_protocol_deviation_readiness_pack/tables/protocol_deviation_register.csv`
- Experimental-design and stability reporting:
  - `outputs/tits_dynamic_graph/tits_experimental_design_power_audit/materials/EXPERIMENTAL_DESIGN_POWER_AUDIT.md`
  - `outputs/tits_dynamic_graph/tits_experimental_design_power_audit/tables/primary_metric_stability.csv`
  - `outputs/tits_dynamic_graph/tits_experimental_design_power_audit/tables/scenario_level_stability.csv`
  - `outputs/tits_dynamic_graph/tits_experimental_design_power_audit/tables/leave_one_case_influence.csv`
  - `outputs/tits_dynamic_graph/tits_experimental_design_power_audit/tables/case_influence_summary.csv`
- Failure analysis:
  - `outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack/materials/FAILURE_ATLAS.md`
- Threats to validity and claim guardrails:
  - `outputs/tits_dynamic_graph/tits_threats_validity_pack/materials/THREATS_TO_VALIDITY_DOSSIER.md`
  - `outputs/tits_dynamic_graph/tits_threats_validity_pack/tables/claim_language_guardrails.csv`
- Claim-language audit:
  - `outputs/tits_dynamic_graph/tits_claim_language_audit/materials/CLAIM_LANGUAGE_AUDIT.md`
  - `outputs/tits_dynamic_graph/tits_claim_language_audit/tables/claim_language_scan_rows.csv`
- Runtime scalability and complexity:
  - `outputs/tits_dynamic_graph/tits_runtime_scalability_pack/materials/RUNTIME_SCALABILITY_AND_COMPLEXITY_REPORT.md`
  - `outputs/tits_dynamic_graph/tits_runtime_scalability_pack/tables/runtime_scalability_by_vehicle_count.csv`
  - `outputs/tits_dynamic_graph/tits_runtime_scalability_pack/tables/runtime_latency_vehicle_count_slopes.csv`
- Formal cross-reference and path integrity:
  - `outputs/tits_dynamic_graph/tits_cross_reference_audit/materials/FORMAL_CROSS_REFERENCE_AUDIT.md`
  - `outputs/tits_dynamic_graph/tits_cross_reference_audit/tables/formal_cross_reference_rows.csv`
- Submission metadata and declarations:
  - `outputs/tits_dynamic_graph/tits_submission_metadata_pack/materials/TITLE_ABSTRACT_KEYWORDS_DRAFT.md`
  - `outputs/tits_dynamic_graph/tits_submission_metadata_pack/materials/COVER_LETTER_DRAFT.md`
  - `outputs/tits_dynamic_graph/tits_submission_metadata_pack/materials/AUTHOR_DECLARATIONS_AND_AI_DISCLOSURE_DRAFT.md`
- GitHub release preparation:
  - `outputs/tits_dynamic_graph/tits_github_release_readiness_pack/materials/GITHUB_RELEASE_READINESS_PACK.md`
  - `outputs/tits_dynamic_graph/tits_github_release_readiness_pack/materials/GITHUB_README_DRAFT.md`
  - `outputs/tits_dynamic_graph/tits_github_release_readiness_pack/tables/github_repository_inventory.csv`
- Ablation/contribution attribution:
  - `outputs/tits_dynamic_graph/tits_ablation_contribution_pack/materials/CONTRIBUTION_ATTRIBUTION_REPORT.md`
  - `outputs/tits_dynamic_graph/tits_ablation_contribution_pack/tables/ablation_contribution_paired.csv`
- Casewise behavior diagnostics:
  - `outputs/tits_dynamic_graph/tits_casewise_diagnostic_pack/materials/CASEWISE_OVERTAKING_DIAGNOSTIC_REPORT.md`
  - `outputs/tits_dynamic_graph/tits_casewise_diagnostic_pack/tables/casewise_pairwise_overtake_deltas.csv`
  - `outputs/tits_dynamic_graph/tits_casewise_diagnostic_pack/tables/casewise_failure_mode_summary.csv`
  - `outputs/tits_dynamic_graph/tits_casewise_diagnostic_pack/tables/casewise_worst_case_cards.csv`
- Baseline fairness:
  - `outputs/tits_dynamic_graph/tits_baseline_fairness_audit/materials/BASELINE_FAIRNESS_AUDIT.md`
  - `outputs/tits_dynamic_graph/tits_baseline_fairness_audit/tables/fairness_command_checks.csv`
  - `outputs/tits_dynamic_graph/tits_baseline_fairness_audit/tables/fairness_summary_run_checks.csv`
- Visual evidence:
  - `outputs/tits_dynamic_graph/publication_gifs/publication_gif_manifest.md`
  - `outputs/tits_dynamic_graph/tits_publication_gif_provenance_audit/materials/PUBLICATION_GIF_PROVENANCE_AUDIT.md`
  - `outputs/tits_dynamic_graph/tits_supplementary_video_index_pack/materials/SUPPLEMENTARY_VIDEO_INDEX.md`
  - `outputs/tits_dynamic_graph/tits_supplementary_video_index_pack/tables/supplementary_video_index.csv`
  - `outputs/tits_dynamic_graph/tits_supplementary_submission_index_pack/materials/SUPPLEMENTARY_SUBMISSION_INDEX.md`

## Recommended Claim Wording

Use:

> The optimized DLC world model with runtime dynamic neighborhoods improves online overtaking quality and efficiency over the original DLC world-model baseline under the evaluated multi-car simulation benchmarks.

Avoid:

> The method solves autonomous overtaking for arbitrary traffic or real-world deployment.
"""


def build_smoke_script():
    return """#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-/home/itrc/.conda/envs/vlm_planner/bin/python}"
DEVICE="${DEVICE:-cuda:0}"
OUT_DIR="${OUT_DIR:-/tmp/tits_dynamic_graph_reviewer_smoke}"

"${PYTHON_BIN}" scripts/run_tits_dynamic_graph_evaluation.py \\
  --config configs/tits_dynamic_graph_experiments.json \\
  --out-dir "${OUT_DIR}" \\
  --algorithms v6_runtime_dynamic_neighborhood_safe,dlc_world_original \\
  --num-agents 4 \\
  --seed 3 \\
  --max-steps 120 \\
  --finish-mode steps \\
  --observation-type telemetry_dynamic \\
  --max-neighbors 3 \\
  --device "${DEVICE}" \\
  --traffic-profile slow_traffic \\
  --no-gif

find "${OUT_DIR}/summaries" -name '*.summary.json' -maxdepth 1 -type f -print
"""


def main():
    parser = argparse.ArgumentParser(description="Export a reviewer-facing replication packet.")
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/reviewer_replication_packet")
    parser.add_argument("--readiness", default="outputs/tits_dynamic_graph/tits_readiness_audit.json")
    parser.add_argument("--confirmatory-audit", default="outputs/tits_dynamic_graph/v6_confirmatory_preflight/v6_confirmatory_matrix_audit.json")
    parser.add_argument("--evidence", default="outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack/confirmatory_evidence_pack_manifest.json")
    parser.add_argument("--artifact", default="outputs/tits_dynamic_graph/artifact_manifest/tits_dynamic_graph_artifact_manifest.json")
    parser.add_argument("--final-readiness", default="outputs/tits_dynamic_graph/final_readiness_dashboard/final_readiness_dashboard_manifest.json")
    parser.add_argument("--protocol-deviation", default="outputs/tits_dynamic_graph/tits_protocol_deviation_readiness_pack/tits_protocol_deviation_readiness_pack_manifest.json")
    args = parser.parse_args()

    readiness = load_json(args.readiness)
    final_readiness = load_json(args.final_readiness)
    confirmatory_audit = load_json(args.confirmatory_audit)
    evidence = load_json(args.evidence)
    artifact = load_json(args.artifact)
    protocol_deviation = load_json(args.protocol_deviation)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    paths = {
        "reviewer_readme": write(out_dir / "REVIEWER_REPLICATION_README.md", build_reviewer_readme(readiness, final_readiness, confirmatory_audit, evidence, artifact, protocol_deviation)),
        "data_code_availability": write(out_dir / "DATA_CODE_AVAILABILITY_DRAFT.md", build_data_code_availability()),
        "submission_checklist": write(out_dir / "SUBMISSION_READINESS_CHECKLIST.md", build_submission_checklist(readiness, confirmatory_audit, evidence)),
        "method_result_map": write(out_dir / "METHOD_RESULT_WRITING_MAP.md", build_method_result_map()),
        "smoke_script": write(out_dir / "run_reviewer_smoke.sh", build_smoke_script()),
    }
    Path(paths["smoke_script"]).chmod(0o755)
    manifest = {
        "status": "complete",
        "out_dir": str(out_dir),
        "readiness_status": readiness.get("status"),
        "final_readiness": f"{final_readiness.get('pass_count', 'NA')}/{final_readiness.get('gate_count', 'NA')}",
        "confirmatory_status": confirmatory_audit.get("summary", {}).get("status"),
        "evidence_status": evidence.get("status"),
        "protocol_deviation_status": protocol_deviation.get("status"),
        "paths": paths,
        "note": "Reviewer packet is a documentation and command-routing layer; it does not create new empirical results.",
    }
    manifest_path = write(out_dir / "reviewer_replication_packet_manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    print(json.dumps({"manifest": manifest_path, "paths": paths}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
