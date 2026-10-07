#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def item(section, row_id, status, evidence, action, boundary, note=""):
    return {
        "section": section,
        "id": row_id,
        "status": status,
        "evidence": evidence,
        "action": action,
        "boundary": boundary,
        "note": note,
    }


def build_dashboard(root):
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    provenance = load_json(root / "tables" / "artifact_provenance.json")
    release = load_json(root / "materials" / "RELEASE_ARCHIVE_MANIFEST.json")
    dictionary = load_json(root / "materials" / "DATA_DICTIONARY.json")
    stats = load_json(root / "materials" / "STATISTICAL_CONSISTENCY_AUDIT.json")
    triage = load_json(root / "materials" / "EDITORIAL_TRIAGE_AND_REVIEWER_CHECKLIST.json")
    shortform = load_json(root / "materials" / "TITLE_ABSTRACT_HIGHLIGHTS_PACKAGE.json")
    portal = load_json(root / "materials" / "SUBMISSION_PORTAL_PACKAGE_MAP.json")
    portal_fields = load_json(root / "materials" / "SUBMISSION_PORTAL_FIELD_COMPLETION_PACK.json")
    decision = load_json(root / "materials" / "EDITORIAL_DECISION_BRIEF.json")
    archive = load_json(root / "materials" / "EXTERNAL_ARCHIVE_PREFLIGHT.json")
    references = load_json(root / "materials" / "REFERENCE_READINESS_AUDIT.json")
    claim_qa = load_json(root / "materials" / "MANUSCRIPT_CLAIM_QA.json")
    cross_ref = load_json(root / "materials" / "MANUSCRIPT_CROSS_REFERENCE_AUDIT.json")
    source_data = load_json(root / "materials" / "FIGURE_SOURCE_DATA_AUDIT.json")
    figure_qc = load_json(root / "materials" / "FIGURE_TECHNICAL_QC.json")
    visual = load_json(root / "materials" / "VISUAL_EVIDENCE_AUDIT.json")
    license_audit = load_json(root / "materials" / "SOFTWARE_DEPENDENCY_LICENSE_AUDIT.json")
    risk = load_json(root / "materials" / "RESEARCH_RISK_AND_SAFETY.json")
    reviewer_dossier = load_json(root / "materials" / "REVIEWER_RISK_RESPONSE_DOSSIER.json")
    reviewer_trace = load_json(root / "materials" / "REVIEWER_EVIDENCE_TRACE_PACK.json")
    smoke = load_json(root / "materials" / "PUBLICATION_SMOKE_TEST.json")
    methods_capsule = load_json(root / "materials" / "METHODS_REPRODUCIBILITY_CAPSULE.json")
    ethics_disclosure = load_json(root / "materials" / "ETHICS_DISCLOSURE_READINESS_PACK.json")
    navigator = load_json(root / "materials" / "REPORTING_SUPPLEMENT_NAVIGATOR.json")
    replication_route = load_json(root / "materials" / "REVIEWER_REPLICATION_ROUTE.json")
    command_preflight = load_json(root / "materials" / "REVIEWER_COMMAND_PREFLIGHT.json")
    assembly_map = load_json(root / "materials" / "MANUSCRIPT_SUPPLEMENT_ASSEMBLY_MAP.json")
    supplement_decision = load_json(root / "materials" / "SUPPLEMENT_UPLOAD_DECISION_MATRIX.json")
    archive_upload = load_json(root / "materials" / "ARCHIVE_UPLOAD_READINESS_MATRIX.json")
    archive_size = load_json(root / "materials" / "ARCHIVE_SIZE_BUDGET_REPORT.json")
    slim_package = load_json(root / "materials" / "SLIM_SUBMISSION_PACKAGE_MANIFEST.json")
    table_legends = load_json(root / "materials" / "SUPPLEMENTARY_TABLE_LEGENDS.json")
    statistical_appendix = load_json(root / "materials" / "STATISTICAL_REPORTING_APPENDIX.json")
    threats = load_json(root / "materials" / "THREATS_TO_VALIDITY_AUDIT.json")
    limitation_integration = load_json(root / "materials" / "MANUSCRIPT_LIMITATION_INTEGRATION_AUDIT.json")
    journal_compliance = load_json(root / "materials" / "TARGET_JOURNAL_COMPLIANCE_MATRIX.json")
    freeze_plan = load_json(root / "materials" / "AUTHOR_ACTION_FREEZE_PLAN.json")
    file_bundle = load_json(root / "materials" / "FINAL_SUBMISSION_FILE_BUNDLE.json")
    upload_plan = load_json(root / "materials" / "SUBMISSION_UPLOAD_SELECTION_PLAN.json")
    upload_gap = load_json(root / "materials" / "AUTHOR_UPLOAD_GAP_CLOSURE_AUDIT.json")
    upload_dry_run = load_json(root / "materials" / "PUBLIC_ARCHIVE_JOURNAL_UPLOAD_DRY_RUN_AUDIT.json")

    portal_counts = portal["summary"]["status_counts"]
    author_actions = portal["author_actions"]
    reference_gap_count = references["summary"]["topic_needs_author_completion_count"]
    reference_action = (
        "Author-review related-work breadth and target-journal citation style before final submission."
        if reference_gap_count == 0
        else "Expand related work before final submission."
    )
    reference_boundary = (
        "Starter related-work coverage is present, but final literature balance remains author-curated."
        if reference_gap_count == 0
        else "Starter bibliography is not a polished top-journal literature review."
    )

    dashboard_rows = [
        item(
            "package_integrity",
            "P1_publication_preflight",
            verification["summary"]["status"],
            "materials/PUBLICATION_PACKAGE_VERIFICATION.md",
            "Keep verification pass after any future file change.",
            "Preflight pass is local package readiness, not journal acceptance.",
            f"{verification['summary']['gate_count']} gates; failed gates: {verification['summary']['failed_gates']}.",
        ),
        item(
            "package_integrity",
            "P2_artifact_provenance",
            "ready",
            "tables/artifact_provenance.md",
            "Use as the reviewer-facing command/provenance map.",
            "Expensive rollout commands should be rerun only when needed.",
            f"{provenance['complete_count']}/{len(provenance['artifacts'])} artifacts complete.",
        ),
        item(
            "package_integrity",
            "P3_release_manifest",
            "ready",
            "materials/RELEASE_ARCHIVE_MANIFEST.md",
            "Regenerate immediately before public archive upload.",
            "Checksum readiness is local until DOI/accession is assigned.",
            f"{release['summary']['file_count']} files; exact byte size is locked in RELEASE_ARCHIVE_MANIFEST.json.",
        ),
        item(
            "package_integrity",
            "P4_publication_smoke_test",
            smoke["summary"]["status"],
            "materials/PUBLICATION_SMOKE_TEST.md",
            "Use as the fast independent integrity check before sending the package to reviewers or an archive.",
            "Smoke test verifies saved artifacts and gates; it does not rerun expensive rollout experiments.",
            f"{smoke['summary']['check_count']} checks; failed: {smoke['summary']['failed_checks']}.",
        ),
        item(
            "data_and_source",
            "D1_data_dictionary",
            "ready" if dictionary["summary"]["complete"] else "review_required",
            "materials/DATA_DICTIONARY.md",
            "Use with source-data uploads and supplementary tables.",
            "Dictionary completeness does not replace journal-specific source-data formatting.",
            f"{dictionary['summary']['table_count']} tables; {dictionary['summary']['field_count']} fields.",
        ),
        item(
            "data_and_source",
            "D2_figure_source_data",
            "ready" if source_data["summary"]["incomplete_count"] == 0 else "review_required",
            "materials/FIGURE_SOURCE_DATA_AUDIT.md; figures/*_source_data.csv",
            "Upload source-data CSVs if requested by journal.",
            "Figures summarize simulator evidence only.",
            f"{source_data['summary']['complete_count']}/{source_data['summary']['figure_count']} figures complete.",
        ),
        item(
            "data_and_source",
            "D3_figure_technical_qc",
            "ready" if figure_qc["summary"]["status"] == "pass" else "review_required",
            "materials/FIGURE_TECHNICAL_QC.md; figures/*.tiff; figures/*.pdf; figures/*.svg",
            "Rerun after any figure resizing, color conversion, or journal-specific export.",
            "Technical figure QC does not validate scientific claims or replace journal-specific production checks.",
            (
                f"{figure_qc['summary']['pass_count']}/{figure_qc['summary']['figure_count']} figures pass; "
                f"minimum TIFF dpi: {figure_qc['summary']['minimum_tiff_dpi']}."
            ),
        ),
        item(
            "statistics",
            "S1_statistical_consistency",
            stats["summary"]["status"],
            "materials/STATISTICAL_CONSISTENCY_AUDIT.md",
            "Rerun after final manuscript edits.",
            "Descriptive seed-set statistics; no broad robustness claim.",
            f"{stats['summary']['check_count']} checks; failed: {stats['summary']['failed_checks']}.",
        ),
        item(
            "statistics",
            "S2_statistical_reporting_appendix",
            statistical_appendix["summary"]["status"],
            "materials/STATISTICAL_REPORTING_APPENDIX.md",
            "Use as the consolidated statistical-reporting appendix for reviewer inspection.",
            "The appendix reports saved simulator statistics and does not create confirmatory robustness evidence.",
            (
                f"{statistical_appendix['summary']['row_count']} rows; "
                f"endpoint-sensitive stage-methods: "
                f"{statistical_appendix['summary']['endpoint_sensitive_stage_methods']}/"
                f"{statistical_appendix['summary']['endpoint_stage_method_count']}; "
                f"review-required: {statistical_appendix['summary']['review_required_count']}."
            ),
        ),
        item(
            "claims",
            "C1_claim_qa",
            claim_qa["summary"]["status"],
            "materials/MANUSCRIPT_CLAIM_QA.md; materials/CLAIM_EVIDENCE_MATRIX.md",
            "Rerun after final journal formatting.",
            "Do not claim real-road, VLM, oracle-as-controller, or broad robustness support.",
            f"Blockers: {claim_qa['summary']['blockers']}; warnings: {claim_qa['summary']['warnings']}.",
        ),
        item(
            "claims",
            "C2_cross_reference",
            cross_ref["summary"]["status"],
            "materials/MANUSCRIPT_CROSS_REFERENCE_AUDIT.md",
            "Rerun after final manuscript path/table edits.",
            "Local paths need conversion to journal supplement references.",
            f"References: {cross_ref['summary']['reference_count']}; numeric checks: {cross_ref['summary']['numeric_check_count']}.",
        ),
        item(
            "editorial_materials",
            "E1_editorial_triage",
            "ready",
            "materials/EDITORIAL_TRIAGE_AND_REVIEWER_CHECKLIST.md",
            "Use as internal editor/reviewer navigation.",
            "Author actions and archive DOI remain outside local automation.",
            f"{triage['summary']['checklist_count']} triage rows.",
        ),
        item(
            "editorial_materials",
            "E2_shortform_text",
            "ready_with_author_adaptation",
            "materials/TITLE_ABSTRACT_HIGHLIGHTS_PACKAGE.md",
            "Adapt to target journal word limits and style.",
            "Short text is evidence-bound draft text, not final journal copy.",
            f"Abstract words: {shortform['summary']['abstract_word_count']}; highlights: {shortform['summary']['highlight_count']}.",
        ),
        item(
            "editorial_materials",
            "E3_decision_brief",
            decision["decision"]["recommendation"],
            "materials/EDITORIAL_DECISION_BRIEF.md",
            "Use for PI/editor go-no-go discussion.",
            "Proceeding requires author completion, not just package pass.",
            f"Risks: {decision['summary']['risk_count']}; gates: {decision['summary']['gate_count']}.",
        ),
        item(
            "editorial_materials",
            "E4_reviewer_risk_response",
            "ready_with_author_adaptation",
            "materials/REVIEWER_RISK_RESPONSE_DOSSIER.md",
            "Use as a pre-submission reviewer-risk and rebuttal-preparation map.",
            "Dossier text is a preparation aid, not final author-certified reviewer response.",
            (
                f"{reviewer_dossier['summary']['row_count']} rows; "
                f"{reviewer_dossier['summary']['high_priority_count']} high-priority; "
                f"author-action rows: {reviewer_dossier['summary']['author_action_count']}."
            ),
        ),
        item(
            "editorial_materials",
            "E4d_reviewer_evidence_trace",
            reviewer_trace["summary"]["status"],
            "materials/REVIEWER_EVIDENCE_TRACE_PACK.md",
            "Use as the reviewer-facing navigation map from claims, figures, seed outcomes, statistics, and limitations to evidence files.",
            "Trace rows aid review but do not replace the underlying source data, claim QA, or author-certified fields.",
            (
                f"{reviewer_trace['summary']['trace_row_count']} trace rows; "
                f"review-required: {reviewer_trace['summary']['review_required_count']}."
            ),
        ),
        item(
            "editorial_materials",
            "E4e_methods_reproducibility_capsule",
            methods_capsule["summary"]["status"],
            "materials/METHODS_REPRODUCIBILITY_CAPSULE.md",
            "Use as the Methods and Reporting Summary evidence capsule when adapting the manuscript to a target journal.",
            "The capsule is a reporting aid; it does not expand simulator evidence or certify journal-specific wording.",
            (
                f"{methods_capsule['summary']['row_count']} rows; "
                f"artifact provenance: {methods_capsule['summary']['artifact_provenance']}."
            ),
        ),
        item(
            "editorial_materials",
            "E4f_ethics_disclosure_readiness",
            ethics_disclosure["summary"]["status"],
            "materials/ETHICS_DISCLOSURE_READINESS_PACK.md",
            "Use as the ethics, disclosure, availability, license, and author-certification checklist before portal upload.",
            "The pack is not an author-certified disclosure form and does not invent conflicts, funding, ORCID, affiliations, or archive identifiers.",
            (
                f"{ethics_disclosure['summary']['row_count']} rows; "
                f"author-required: {ethics_disclosure['summary']['author_required_count']}; "
                f"archive-dependent: {ethics_disclosure['summary']['archive_dependent_count']}."
            ),
        ),
        item(
            "editorial_materials",
            "E4g_reporting_supplement_navigator",
            navigator["summary"]["status"],
            "materials/REPORTING_SUPPLEMENT_NAVIGATOR.md",
            "Use as the one-page navigation layer for Methods, supplement, source data, ethics/disclosure, archive, submission, and quality-gate materials.",
            "The navigator points to authoritative files and does not replace journal-specific formatting or author-certified declarations.",
            (
                f"{navigator['summary']['row_count']} rows; "
                f"review-required: {navigator['summary']['review_required_count']}; "
                f"author-completion: {navigator['summary']['author_completion_count']}."
            ),
        ),
        item(
            "editorial_materials",
            "E4h_reviewer_replication_route",
            replication_route["summary"]["status"],
            "materials/REVIEWER_REPLICATION_ROUTE.md",
            "Use as the tiered replication plan from fast saved-artifact checks to optional GPU rollout reruns.",
            "The route is an audit plan and does not create new empirical evidence or broaden simulator-only claims.",
            (
                f"{replication_route['summary']['route_count']} routes; "
                f"review-required: {replication_route['summary']['review_required_count']}; "
                f"optional expensive routes: {replication_route['summary']['expensive_route_count']}."
            ),
        ),
        item(
            "editorial_materials",
            "E4h2_reviewer_command_preflight",
            command_preflight["summary"]["status"],
            "materials/REVIEWER_COMMAND_PREFLIGHT.md",
            "Use before executing reviewer-facing replication commands to confirm scripts, Python invocation, root arguments, output parents, and optional GPU rerun boundaries.",
            "The preflight is static and does not execute commands, generate new rollouts, or broaden simulator-only claims.",
            (
                f"{command_preflight['summary']['route_row_count']} route rows; "
                f"{command_preflight['summary']['subcommand_count']} subcommands; "
                f"review-required: {command_preflight['summary']['review_required_count']}; "
                f"optional not executed: {command_preflight['summary']['optional_not_executed_count']}."
            ),
        ),
        item(
            "editorial_materials",
            "E4i_manuscript_supplement_assembly",
            assembly_map["summary"]["status"],
            "materials/MANUSCRIPT_SUPPLEMENT_ASSEMBLY_MAP.md",
            "Use as the manuscript-to-supplement placement map when adapting the draft to a target journal and assembling upload files.",
            "The map coordinates existing evidence and author actions; it is not a final journal upload receipt or additional empirical validation.",
            (
                f"{assembly_map['summary']['row_count']} rows; "
                f"journal-upload related: {assembly_map['summary']['journal_upload_related_count']}; "
                f"review-required: {assembly_map['summary']['review_required_count']}."
            ),
        ),
        item(
            "editorial_materials",
            "E4k_supplement_upload_decision",
            supplement_decision["summary"]["status"],
            "materials/SUPPLEMENT_UPLOAD_DECISION_MATRIX.md",
            "Use to separate required supplement/source-data uploads from optional reviewer-support analyses.",
            "Author must decide optional supplement versus reviewer-response/archive placement after target-journal choice.",
            (
                f"{supplement_decision['summary']['row_count']} rows; "
                f"required missing: {supplement_decision['summary']['required_missing_count']}; "
                f"author-selection: {supplement_decision['summary']['author_selection_required_count']}."
            ),
        ),
        item(
            "editorial_materials",
            "E4j_supplementary_table_legends",
            table_legends["summary"]["status"],
            "materials/SUPPLEMENTARY_TABLE_LEGENDS.md",
            "Use as the draft caption and interpretation-boundary source for supplementary tables and source-data CSVs.",
            "Legends are journal-adaptable reviewer aids and do not add results or broaden claims.",
            (
                f"{table_legends['summary']['legend_count']} legends; "
                f"dictionary-covered: {table_legends['summary']['dictionary_covered_count']}; "
                f"review-required: {table_legends['summary']['review_required_count']}."
            ),
        ),
        item(
            "editorial_materials",
            "E4b_threats_to_validity",
            "ready_with_limitations",
            "materials/THREATS_TO_VALIDITY_AUDIT.md",
            "Use as the Discussion limitations and reviewer-risk source map.",
            "Threats-to-validity audit controls claims but does not add new empirical evidence.",
            (
                f"{threats['summary']['row_count']} threats; "
                f"{threats['summary']['high_severity_count']} high-severity; "
                f"author-action rows: {threats['summary']['author_action_required_count']}."
            ),
        ),
        item(
            "editorial_materials",
            "E4c_manuscript_limitation_integration",
            limitation_integration["summary"]["status"],
            "materials/MANUSCRIPT_LIMITATION_INTEGRATION_AUDIT.md; manuscript/main.md",
            "Preserve visible limitation wording when converting the draft into the target journal template.",
            "Static text coverage does not prove semantic adequacy; authors must keep the boundaries in final prose.",
            (
                f"{limitation_integration['summary']['covered_count']}/"
                f"{limitation_integration['summary']['threat_count']} threats covered; "
                f"high-severity uncovered: {limitation_integration['summary']['high_uncovered_count']}."
            ),
        ),
        item(
            "editorial_materials",
            "E5_target_journal_compliance",
            "ready_with_author_action",
            "materials/TARGET_JOURNAL_COMPLIANCE_MATRIX.md",
            "Use as a target-journal pre-submission compliance map and recheck official instructions before upload.",
            "The matrix is local preflight support and does not certify compliance with a specific journal portal.",
            (
                f"{journal_compliance['summary']['row_count']} rows; "
                f"{journal_compliance['summary']['high_priority_count']} high-priority; "
                f"author-action rows: {journal_compliance['summary']['author_action_count']}."
            ),
        ),
        item(
            "editorial_materials",
            "E6_author_action_freeze",
            "author_action_required",
            "materials/AUTHOR_ACTION_FREEZE_PLAN.md",
            "Complete blockers and rerun the listed validation scripts before journal upload.",
            "The freeze plan records author-owned tasks; local automation cannot certify them as complete.",
            (
                f"{freeze_plan['summary']['row_count']} rows; "
                f"blockers: {freeze_plan['summary']['blocker_count']}."
            ),
        ),
        item(
            "editorial_materials",
            "E7_final_file_bundle",
            "ready_with_author_selection",
            "materials/FINAL_SUBMISSION_FILE_BUNDLE.md",
            "Use as the final local-to-upload file map after choosing the target journal.",
            "The bundle map is local upload preparation, not a final journal submission receipt.",
            (
                f"{file_bundle['summary']['file_row_count']} file rows; "
                f"missing required: {file_bundle['summary']['missing_required_count']}."
            ),
        ),
        item(
            "editorial_materials",
            "E8_upload_selection_plan",
            upload_plan["summary"]["status"],
            "materials/SUBMISSION_UPLOAD_SELECTION_PLAN.md",
            "Use after target-journal choice to decide portal upload, source-data upload, supplement, archive, and internal-only files.",
            "The upload plan is operational guidance, not a journal receipt or author-certified metadata form.",
            (
                f"{upload_plan['summary']['row_count']} rows; "
                f"journal candidates: {upload_plan['summary']['journal_portal_candidate_count']}; "
                f"author-selection rows: {upload_plan['summary']['author_selection_required_count']}."
            ),
        ),
        item(
            "editorial_materials",
            "E8b_author_upload_gap_closure",
            upload_gap["summary"]["status"],
            "materials/AUTHOR_UPLOAD_GAP_CLOSURE_AUDIT.md",
            "Use before author handoff to confirm local upload-entry materials are aligned and only author-owned gaps remain.",
            "A pass still leaves DOI/accession, author-certified metadata, and target-journal upload choices to the authors.",
            (
                f"{upload_gap['summary']['row_count']} rows; "
                f"review-required: {upload_gap['summary']['review_required_count']}; "
                f"author-action: {upload_gap['summary']['author_action_required_count']}; "
                f"stale active-entry fields: {upload_gap['summary']['stale_active_entry_field_count']}."
            ),
        ),
        item(
            "editorial_materials",
            "E8c_public_archive_journal_upload_dry_run",
            upload_dry_run["summary"]["status"],
            "materials/PUBLIC_ARCHIVE_JOURNAL_UPLOAD_DRY_RUN_AUDIT.md",
            "Use as a no-upload dry run for journal files, source data, supplement files, public archive files, size routing, and author-certified fields.",
            "A pass means local pre-upload checks pass; DOI/accession, target-journal portal choices, and author-certified metadata remain author-owned.",
            (
                f"{upload_dry_run['summary']['row_count']} rows; "
                f"review-required: {upload_dry_run['summary']['review_required_count']}; "
                f"author-action: {upload_dry_run['summary']['author_action_required_count']}; "
                f"undocumented release-missing: {upload_dry_run['summary']['undocumented_missing_from_release_count']}."
            ),
        ),
        item(
            "editorial_materials",
            "E9_archive_upload_readiness",
            archive_upload["summary"]["status"],
            "materials/ARCHIVE_UPLOAD_READINESS_MATRIX.md",
            "Use as the high-level destination map for journal submission, source data, supplement, public archive, reviewer support, internal QC, and author-certified metadata.",
            "The matrix is a local readiness map; DOI/accession, final portal choices, and certified author metadata remain author-owned.",
            (
                f"{archive_upload['summary']['row_count']} rows; "
                f"review-required: {archive_upload['summary']['review_required_count']}; "
                f"author-action: {archive_upload['summary']['author_action_required_count']}."
            ),
        ),
        item(
            "editorial_materials",
            "E10_archive_size_budget",
            archive_size["summary"]["status"],
            "materials/ARCHIVE_SIZE_BUDGET_REPORT.md",
            "Use before archive deposition or journal upload to route large files and decide slim versus full upload sets.",
            "Budget flags are conservative operational checks, not journal-specific upload rules.",
            (
                "release size reference: materials/ARCHIVE_SIZE_BUDGET_REPORT.json; "
                f"single files >50 MiB: {archive_size['summary']['single_file_over_50mb_count']}; "
                f"budget review flags: {archive_size['summary']['budget_review_required_count']}."
            ),
        ),
        item(
            "editorial_materials",
            "E11_slim_submission_package",
            slim_package["summary"]["status"],
            "materials/SLIM_SUBMISSION_PACKAGE_MANIFEST.md",
            "Use to assemble a lightweight journal-facing upload set while keeping full traces, sweeps, TIFFs, and diagnostics in the archive.",
            "This is a planning manifest, not a final journal receipt or substitute for full public archive deposition.",
            (
                f"{slim_package['summary']['slim_file_count']} slim files; "
                "size reference: materials/SLIM_SUBMISSION_PACKAGE_MANIFEST.json; "
                f"archive-only rows: {slim_package['summary']['excluded_or_archive_only_count']}."
            ),
        ),
        item(
            "portal",
            "P5_portal_field_completion_pack",
            portal_fields["summary"]["status"],
            "materials/SUBMISSION_PORTAL_FIELD_COMPLETION_PACK.md",
            "Use for portal entry after target journal choice; complete author-required and archive-dependent fields before upload.",
            "The field pack provides draft text and placeholders, not author-certified declarations or an archive DOI.",
            (
                f"{portal_fields['summary']['field_count']} fields; "
                f"copy-ready: {portal_fields['summary']['copy_ready_count']}; "
                f"after-archive: {portal_fields['summary']['copy_after_archive_count']}; "
                f"author-required: {portal_fields['summary']['author_required_count']}."
            ),
        ),
        item(
            "visual_evidence",
            "V1_gif_catalog",
            "ready",
            "materials/VISUAL_EVIDENCE_AUDIT.md",
            "Use GIFs as qualitative support only.",
            "GIFs cannot substitute for strict validation tables.",
            f"{visual['summary']['gif_count']} GIFs; {visual['summary']['primary_table_linked_gif_count']} linked to primary tables.",
        ),
        item(
            "archive_and_compliance",
            "A1_external_archive",
            "author_action_required" if archive["summary"]["external_archive_pending"] else "ready",
            "materials/EXTERNAL_ARCHIVE_PREFLIGHT.md; materials/FAIR_ARCHIVE_METADATA.md",
            "Deposit package and update DOI/URL/accession fields.",
            "Local archive preflight is not a public archive record.",
            f"Preflight status: {archive['summary']['status']}; author-required rows: {archive['summary']['author_required_count']}.",
        ),
        item(
            "archive_and_compliance",
            "A2_license_dependencies",
            "ready_with_author_review",
            "materials/SOFTWARE_DEPENDENCY_LICENSE_AUDIT.md",
            "Author/institution should confirm final third-party license handling.",
            "Local dependency audit is not legal advice.",
            f"Audit rows: {license_audit['summary']['audit_item_count']}; dependency rows: {license_audit['summary']['dependency_count']}.",
        ),
        item(
            "ethics_and_risk",
            "R1_research_risk",
            "ready",
            "materials/RESEARCH_RISK_AND_SAFETY.md; materials/SIMULATION_TO_REAL_APPLICABILITY.md",
            "Copy simulator-only and no-deployment wording into journal forms.",
            "No real vehicle, human subject, public road, VLM, or safety-certification evidence.",
            f"Risk rows: {len(risk['risk_items'])}.",
        ),
        item(
            "references",
            "R2_reference_readiness",
            references["summary"]["status"],
            "materials/REFERENCE_READINESS_AUDIT.md; materials/RELATED_WORK_POSITIONING_MATRIX.md; manuscript/references.bib",
            reference_action,
            reference_boundary,
            f"Topics needing author completion: {reference_gap_count}.",
        ),
        item(
            "portal",
            "P4_submission_portal",
            "author_action_required",
            "materials/SUBMISSION_PORTAL_PACKAGE_MAP.md; materials/SUBMISSION_PORTAL_AUTHOR_ACTIONS.csv",
            "Complete target-journal formatting, metadata, disclosures, and archive fields.",
            "The package cannot infer certified author information or declarations.",
            f"Portal status counts: {portal_counts}.",
        ),
    ]

    ready_like = {
        "ready",
        "pass",
        "ready_with_author_review",
        "ready_with_author_adaptation",
        "ready_with_author_selection",
        "ready_with_author_completion",
        "ready_with_author_action",
        "ready_with_limitations",
        "ready_with_size_review",
    }
    action_required = [row for row in dashboard_rows if "author_action" in row["status"] or row["status"].startswith("author")]
    review_required = [row for row in dashboard_rows if row["status"] not in ready_like and row not in action_required and row["status"] != "proceed_after_author_completion"]

    return {
        "root": str(root),
        "title": "Submission readiness dashboard",
        "purpose": "Provide a compact go/no-go dashboard for final journal-submission preparation.",
        "overall_recommendation": decision["decision"]["recommendation"],
        "dashboard_rows": dashboard_rows,
        "author_actions": author_actions,
        "summary": {
            "dashboard_row_count": len(dashboard_rows),
            "ready_or_pass_count": sum(1 for row in dashboard_rows if row["status"] in ready_like),
            "author_action_row_count": len(action_required),
            "review_required_row_count": len(review_required),
            "portal_author_action_count": portal["summary"]["author_action_count"],
            "publication_verification_status": verification["summary"]["status"],
            "artifact_provenance": f"{provenance['complete_count']}/{len(provenance['artifacts'])}",
            "data_dictionary_complete": dictionary["summary"]["complete"],
            "statistical_consistency_status": stats["summary"]["status"],
            "claim_qa_status": claim_qa["summary"]["status"],
            "external_archive_pending": archive["summary"]["external_archive_pending"],
            "release_file_count": release["summary"]["file_count"],
            "reviewer_dossier_rows": reviewer_dossier["summary"]["row_count"],
            "reviewer_evidence_trace_rows": reviewer_trace["summary"]["trace_row_count"],
            "reviewer_evidence_trace_review_required": reviewer_trace["summary"]["review_required_count"],
            "publication_smoke_test_reference": "materials/PUBLICATION_SMOKE_TEST.json",
            "methods_reproducibility_capsule_status": methods_capsule["summary"]["status"],
            "methods_reproducibility_capsule_rows": methods_capsule["summary"]["row_count"],
            "ethics_disclosure_readiness_status": ethics_disclosure["summary"]["status"],
            "ethics_disclosure_author_required": ethics_disclosure["summary"]["author_required_count"],
            "reporting_supplement_navigator_status": navigator["summary"]["status"],
            "reporting_supplement_navigator_rows": navigator["summary"]["row_count"],
            "reviewer_replication_route_status": replication_route["summary"]["status"],
            "reviewer_replication_route_rows": replication_route["summary"]["route_count"],
            "reviewer_command_preflight_status": command_preflight["summary"]["status"],
            "reviewer_command_preflight_subcommands": command_preflight["summary"]["subcommand_count"],
            "manuscript_supplement_assembly_status": assembly_map["summary"]["status"],
            "manuscript_supplement_assembly_rows": assembly_map["summary"]["row_count"],
            "supplementary_table_legends_status": table_legends["summary"]["status"],
            "supplementary_table_legend_count": table_legends["summary"]["legend_count"],
            "statistical_reporting_appendix_status": statistical_appendix["summary"]["status"],
            "statistical_reporting_appendix_rows": statistical_appendix["summary"]["row_count"],
            "manuscript_limitation_integration_status": limitation_integration["summary"]["status"],
            "manuscript_limitation_high_uncovered": limitation_integration["summary"]["high_uncovered_count"],
            "target_journal_compliance_rows": journal_compliance["summary"]["row_count"],
            "author_freeze_plan_rows": freeze_plan["summary"]["row_count"],
            "author_freeze_blockers": freeze_plan["summary"]["blocker_count"],
            "final_bundle_file_rows": file_bundle["summary"]["file_row_count"],
            "final_bundle_missing_required": file_bundle["summary"]["missing_required_count"],
            "upload_selection_plan_rows": upload_plan["summary"]["row_count"],
            "upload_selection_author_selection_required": upload_plan["summary"]["author_selection_required_count"],
            "author_upload_gap_closure_status": upload_gap["summary"]["status"],
            "author_upload_gap_closure_review_required": upload_gap["summary"]["review_required_count"],
            "author_upload_gap_closure_author_action_required": upload_gap["summary"]["author_action_required_count"],
            "public_archive_journal_upload_dry_run_status": upload_dry_run["summary"]["status"],
            "public_archive_journal_upload_dry_run_review_required": upload_dry_run["summary"]["review_required_count"],
            "public_archive_journal_upload_dry_run_author_action_required": upload_dry_run["summary"]["author_action_required_count"],
            "archive_upload_readiness_status": archive_upload["summary"]["status"],
            "archive_upload_readiness_rows": archive_upload["summary"]["row_count"],
            "archive_upload_author_action_required": archive_upload["summary"]["author_action_required_count"],
            "archive_size_budget_status": archive_size["summary"]["status"],
            "archive_size_budget_reference": "materials/ARCHIVE_SIZE_BUDGET_REPORT.json",
            "archive_size_budget_flags": archive_size["summary"]["budget_review_required_count"],
            "slim_submission_package_status": slim_package["summary"]["status"],
            "slim_submission_package_size_reference": "materials/SLIM_SUBMISSION_PACKAGE_MANIFEST.json",
            "slim_submission_package_files": slim_package["summary"]["slim_file_count"],
            "portal_field_completion_fields": portal_fields["summary"]["field_count"],
            "portal_field_completion_author_required": portal_fields["summary"]["author_required_count"],
        },
        "interpretation": (
            "This dashboard is a local submission-readiness control panel. It documents what is ready, what requires "
            "author certification, and which claims remain prohibited; it is not a final journal submission receipt."
        ),
    }


def write_csv(report, path):
    fields = ["section", "id", "status", "evidence", "action", "boundary", "note"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in report["dashboard_rows"]:
            writer.writerow(row)


def write_markdown(report, path):
    lines = [
        "# Submission Readiness Dashboard",
        "",
        report["purpose"],
        "",
        report["interpretation"],
        "",
        "## Overall Status",
        "",
        f"- Recommendation: `{report['overall_recommendation']}`",
        f"- Publication verification: `{report['summary']['publication_verification_status']}`",
        f"- Artifact provenance: {report['summary']['artifact_provenance']}",
        f"- Statistical consistency: `{report['summary']['statistical_consistency_status']}`",
        f"- Claim QA: `{report['summary']['claim_qa_status']}`",
        f"- External archive pending: `{report['summary']['external_archive_pending']}`",
        f"- Dashboard rows: {report['summary']['dashboard_row_count']}",
        "",
        "## Dashboard",
        "",
        "| section | id | status | evidence | action | boundary | note |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in report["dashboard_rows"]:
        lines.append(
            f"| {row['section']} | {row['id']} | {row['status']} | `{row['evidence']}` | "
            f"{row['action']} | {row['boundary']} | {row['note']} |"
        )
    lines.extend(["", "## Author Actions", "", "| action id | priority | action | evidence |", "|---|---|---|---|"])
    for row in report["author_actions"]:
        lines.append(f"| {row['action_id']} | {row['priority']} | {row['action']} | `{row['evidence']}` |")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export submission readiness dashboard.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    report = build_dashboard(root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    out_json = materials / "SUBMISSION_READINESS_DASHBOARD.json"
    out_md = materials / "SUBMISSION_READINESS_DASHBOARD.md"
    out_csv = materials / "SUBMISSION_READINESS_DASHBOARD.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv), "summary": report["summary"]}, indent=2))


if __name__ == "__main__":
    main()
