#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def row(section, item, primary_file, source_summary, reviewer_use, author_action, boundary, status):
    return {
        "section": section,
        "item": item,
        "primary_file": primary_file,
        "source_summary": source_summary,
        "reviewer_use": reviewer_use,
        "author_action": author_action,
        "boundary": boundary,
        "status": status,
    }


def build_report(root):
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    provenance = load_json(root / "tables" / "artifact_provenance.json")
    smoke = load_json(root / "materials" / "PUBLICATION_SMOKE_TEST.json")
    dictionary = load_json(root / "materials" / "DATA_DICTIONARY.json")
    dashboard = load_json(root / "materials" / "SUBMISSION_READINESS_DASHBOARD.json")
    bundle = load_json(root / "materials" / "FINAL_SUBMISSION_FILE_BUNDLE.json")
    trace = load_json(root / "materials" / "REVIEWER_EVIDENCE_TRACE_PACK.json")
    response_seed = load_json(root / "materials" / "REVIEWER_RESPONSE_SEED_PACK.json")
    revision_checklist = load_json(root / "materials" / "REVISION_RESPONSE_EXECUTION_CHECKLIST.json")
    copyedit_lock = load_json(root / "materials" / "PORTAL_COPYEDIT_LOCK_AUDIT.json")
    blinded_audit = load_json(root / "materials" / "BLINDED_REVIEW_ANONYMIZATION_AUDIT.json")
    ai_disclosure = load_json(root / "materials" / "AI_TOOL_USE_DISCLOSURE_AUDIT.json")
    methods = load_json(root / "materials" / "METHODS_REPRODUCIBILITY_CAPSULE.json")
    ethics = load_json(root / "materials" / "ETHICS_DISCLOSURE_READINESS_PACK.json")
    supplement = load_json(root / "materials" / "SUPPLEMENTARY_MATERIALS_INDEX.json")
    supplement_decision = load_json(root / "materials" / "SUPPLEMENT_UPLOAD_DECISION_MATRIX.json")
    table_legends = load_json(root / "materials" / "SUPPLEMENTARY_TABLE_LEGENDS.json")
    archive = load_json(root / "materials" / "ARCHIVE_README.json")
    archive_size = load_json(root / "materials" / "ARCHIVE_SIZE_BUDGET_REPORT.json")
    slim_package = load_json(root / "materials" / "SLIM_SUBMISSION_PACKAGE_MANIFEST.json")
    figure_qc = load_json(root / "materials" / "FIGURE_TECHNICAL_QC.json")
    figure_source = load_json(root / "materials" / "FIGURE_SOURCE_DATA_AUDIT.json")
    stats = load_json(root / "materials" / "STATISTICAL_CONSISTENCY_AUDIT.json")
    statistical_appendix = load_json(root / "materials" / "STATISTICAL_REPORTING_APPENDIX.json")
    effects = load_json(root / "materials" / "EFFECT_SIZE_UNCERTAINTY_SUMMARY.json")
    seed_partition = load_json(root / "materials" / "SEED_PARTITION_AUDIT.json")
    risk = load_json(root / "materials" / "RESEARCH_RISK_AND_SAFETY.json")
    sim2real = load_json(root / "materials" / "SIMULATION_TO_REAL_APPLICABILITY.json")
    journal = load_json(root / "materials" / "TARGET_JOURNAL_COMPLIANCE_MATRIX.json")
    portal_fields = load_json(root / "materials" / "SUBMISSION_PORTAL_FIELD_COMPLETION_PACK.json")
    frontmatter = load_json(root / "materials" / "EDITORIAL_FRONTMATTER_CLAIM_AUDIT.json")
    claim_boundary = load_json(root / "materials" / "CLAIM_BOUNDARY_COMMUNICATION_PACK.json")
    blockers = load_json(root / "materials" / "REMAINING_AUTHOR_BLOCKERS_MATRIX.json")
    handoff = load_json(root / "materials" / "FINAL_AUTHOR_HANDOFF_CHECKLIST.json")
    freeze = load_json(root / "materials" / "FINAL_CHECKSUM_FREEZE_RECORD.json")
    citation = load_json(root / "materials" / "CITATION_METADATA.json")
    replication_route = load_json(root / "materials" / "REVIEWER_REPLICATION_ROUTE.json")
    command_preflight = load_json(root / "materials" / "REVIEWER_COMMAND_PREFLIGHT.json")
    upload_gap = load_json(root / "materials" / "AUTHOR_UPLOAD_GAP_CLOSURE_AUDIT.json")
    upload_dry_run = load_json(root / "materials" / "PUBLIC_ARCHIVE_JOURNAL_UPLOAD_DRY_RUN_AUDIT.json")
    self_referential_dashboard_ids = {
        "E4d_reviewer_evidence_trace",
        "E4g_reporting_supplement_navigator",
        "E4h_reviewer_replication_route",
        "E4i_manuscript_supplement_assembly",
        "E8b_author_upload_gap_closure",
        "E8c_public_archive_journal_upload_dry_run",
    }
    core_dashboard_review_required_count = sum(
        1
        for item in dashboard["dashboard_rows"]
        if item["status"] == "review_required" and item["id"] not in self_referential_dashboard_ids
    )
    trace_self_ids = {
        "DASH_E4d_reviewer_evidence_trace",
        "DASH_E4g_reporting_supplement_navigator",
        "DASH_E4h_reviewer_replication_route",
        "DASH_E4i_manuscript_supplement_assembly",
        "DASH_E8b_author_upload_gap_closure",
        "DASH_E8c_public_archive_journal_upload_dry_run",
    }
    core_trace_review_required_count = sum(
        1
        for item in trace["rows"]
        if item["status"] == "review_required" and item["trace_id"] not in trace_self_ids
    )

    rows = [
        row(
            "start_here",
            "submission_dashboard",
            "materials/SUBMISSION_READINESS_DASHBOARD.md",
            f"{dashboard['summary']['dashboard_row_count']} rows; core review_required={core_dashboard_review_required_count}",
            "Use first to inspect overall package readiness, author actions, and gate status.",
            "Resolve author-action rows before journal upload.",
            "Dashboard is a local readiness panel, not a journal receipt.",
            "pass" if core_dashboard_review_required_count == 0 else "review_required",
        ),
        row(
            "start_here",
            "reviewer_evidence_trace",
            "materials/REVIEWER_EVIDENCE_TRACE_PACK.md",
            f"{trace['summary']['trace_row_count']} trace rows; core review_required={core_trace_review_required_count}",
            "Use to jump from claims, figures, seed outcomes, and dashboard rows to source evidence.",
            "Keep trace pass after any material edits.",
            "Trace rows navigate evidence; source data remain authoritative.",
            "pass" if core_trace_review_required_count == 0 else "review_required",
        ),
        row(
            "start_here",
            "reviewer_replication_route",
            "materials/REVIEWER_REPLICATION_ROUTE.md",
            f"{replication_route['summary']['route_count']} routes; expensive optional={replication_route['summary']['expensive_route_count']}",
            "Use to choose a fast, moderate, or optional expensive replication path.",
            "Run optional GPU rollout tiers only when reviewers require end-to-end reproduction.",
            "Replication route is an audit plan and does not add new evidence.",
            "pass" if replication_route["summary"]["core_dashboard_review_required"] == 0 else "review_required",
        ),
        row(
            "start_here",
            "reviewer_command_preflight",
            "materials/REVIEWER_COMMAND_PREFLIGHT.md",
            (
                f"{command_preflight['summary']['route_row_count']} route rows; "
                f"{command_preflight['summary']['subcommand_count']} subcommands; "
                f"review_required={command_preflight['summary']['review_required_count']}"
            ),
            "Use before executing reviewer-facing commands to check scripts, Python invocation, root arguments, output parents, and optional GPU rerun boundaries.",
            "Run optional GPU rollout tiers only after reviewer selection of a registered artifact.",
            "Static preflight does not execute commands or add new empirical evidence.",
            command_preflight["summary"]["status"],
        ),
        row(
            "methods",
            "methods_reproducibility_capsule",
            "materials/METHODS_REPRODUCIBILITY_CAPSULE.md",
            f"{methods['summary']['row_count']} rows; experiments={methods['summary']['experiment_count']}",
            "Use for Methods, Reporting Summary, seed partitions, compute, environment, and reproducibility fields.",
            "Adapt wording to target journal template.",
            "Capsule does not expand empirical scope beyond saved simulator evidence.",
            methods["summary"]["status"],
        ),
        row(
            "statistics",
            "statistical_consistency",
            "materials/STATISTICAL_CONSISTENCY_AUDIT.md; materials/STATISTICAL_REPORTING_APPENDIX.md; materials/EFFECT_SIZE_UNCERTAINTY_SUMMARY.md",
            (
                f"{stats['summary']['check_count']} consistency checks; "
                f"{statistical_appendix['summary']['row_count']} reporting rows; "
                f"effect rows={effects['summary']['row_count']}; "
                f"failed={stats['summary']['failed_checks']}"
            ),
            "Use to verify reported pass counts, Wilson intervals, exact tests, endpoint sensitivity, effect sizes, and locked result summaries.",
            "Rerun after any result-table or manuscript-number edits.",
            "Descriptive seed-set statistics; no broad robustness claim.",
            "pass"
            if stats["summary"]["failed_checks"] == 0
            and statistical_appendix["summary"]["status"] == "pass"
            and effects["summary"]["status"] == "pass"
            else "review_required",
        ),
        row(
            "statistics",
            "seed_partition_audit",
            "materials/SEED_PARTITION_AUDIT.md",
            f"{seed_partition['summary']['seed_set_count']} seed sets; unexpected overlaps={seed_partition['summary']['unexpected_overlap_count']}",
            "Use to distinguish development, diagnostic reuse, and external validation partitions.",
            "Preserve targeted-repair and heldout4 boundary labels.",
            "Seed partitions support bounded simulator validation only.",
            seed_partition["summary"]["status"],
        ),
        row(
            "figures",
            "figure_source_data",
            "materials/FIGURE_SOURCE_DATA_AUDIT.md",
            f"{figure_source['summary']['complete_count']}/{figure_source['summary']['figure_count']} figures complete",
            "Use to map each figure to source-data CSVs and manifests.",
            "Upload source-data files according to journal requirements.",
            "Figures summarize simulator evidence and do not replace strict tables.",
            "pass" if figure_source["summary"]["incomplete_count"] == 0 else "review_required",
        ),
        row(
            "figures",
            "figure_technical_qc",
            "materials/FIGURE_TECHNICAL_QC.md",
            f"{figure_qc['summary']['pass_count']}/{figure_qc['summary']['figure_count']} figures pass",
            "Use to check figure export formats, TIFF DPI, and raster dimensions.",
            "Rerun after figure resizing or journal-specific export.",
            "Technical QC does not validate scientific claims.",
            figure_qc["summary"]["status"],
        ),
        row(
            "ethics_disclosure",
            "ethics_disclosure_readiness",
            "materials/ETHICS_DISCLOSURE_READINESS_PACK.md",
            f"{ethics['summary']['row_count']} rows; author_required={ethics['summary']['author_required_count']}",
            "Use for ethics, disclosure, author metadata, availability, license, and portal declaration readiness.",
            "Authors must certify conflicts, funding, affiliations, ORCID, and archive identifiers.",
            "No author-owned disclosure is completed by automation.",
            ethics["summary"]["status"],
        ),
        row(
            "ethics_disclosure",
            "research_risk_and_safety",
            "materials/RESEARCH_RISK_AND_SAFETY.md",
            f"{len(risk['risk_items'])} risk rows; required wording={len(risk['required_submission_wording'])}",
            "Use for simulator-only, oracle-boundary, overclaim, reproducibility, and archive-risk wording.",
            "Copy required boundary wording into final manuscript and portal fields.",
            "Does not certify deployment readiness.",
            "ready",
        ),
        row(
            "ethics_disclosure",
            "simulation_to_real_boundary",
            "materials/SIMULATION_TO_REAL_APPLICABILITY.md",
            f"{len(sim2real['dimensions'])} applicability dimensions",
            "Use to separate simulator evidence from real-world transfer claims.",
            "Keep no real-road, VLM, perception, and safety-certification boundaries visible.",
            "No real-world deployment or perception-stack evidence is included.",
            "ready",
        ),
        row(
            "archive",
            "archive_readme",
            "materials/ARCHIVE_README.md",
            f"{archive['summary']['entry_count']} entries; review_required={archive['summary']['review_required_count']}",
            "Use as the public-archive start-here file map.",
            "Update external DOI/URL after deposition.",
            "Local archive README is not a public accession record.",
            "pass" if archive["summary"]["review_required_count"] == 0 else "review_required",
        ),
        row(
            "archive",
            "archive_size_budget",
            "materials/ARCHIVE_SIZE_BUDGET_REPORT.md",
            (
                "release size reference=materials/ARCHIVE_SIZE_BUDGET_REPORT.json; "
                f"largest files={archive_size['summary']['largest_file_count']}; "
                f"budget flags={archive_size['summary']['budget_review_required_count']}"
            ),
            "Use before archive deposition or journal upload to route large files and decide slim versus full upload sets.",
            "Recheck after final PDF, compressed archives, or repository deposition files are added.",
            "Budget flags are conservative operational checks, not journal-specific upload rules.",
            archive_size["summary"]["status"],
        ),
        row(
            "archive",
            "slim_submission_package",
            "materials/SLIM_SUBMISSION_PACKAGE_MANIFEST.md",
            (
                f"{slim_package['summary']['slim_file_count']} files; "
                "size reference=materials/SLIM_SUBMISSION_PACKAGE_MANIFEST.json; "
                f"archive-only={slim_package['summary']['excluded_or_archive_only_count']}"
            ),
            "Use to assemble a lightweight journal-facing upload set while keeping full traces, sweeps, TIFFs, and diagnostics in the archive.",
            "Apply only after target-journal selection and final author metadata completion.",
            "Slim package planning does not replace full public archive deposition or journal-specific upload rules.",
            slim_package["summary"]["status"],
        ),
        row(
            "archive",
            "checksum_freeze",
            "materials/FINAL_CHECKSUM_FREEZE_RECORD.md",
            f"status={freeze['summary']['status']}; files={freeze['summary']['release_file_count']}",
            "Use immediately before archive upload or sharing a frozen review package.",
            "Regenerate after any file edits.",
            "External identifier remains pending until public deposition.",
            freeze["summary"]["status"],
        ),
        row(
            "archive",
            "citation_metadata",
            "materials/CITATION_METADATA.md",
            f"{citation['summary']['row_count']} rows; DOI present={citation['summary']['external_doi_present']}",
            "Use for CITATION.cff/BibTeX/archive citation metadata review.",
            "Authors must add external DOI/URL and confirm creator metadata.",
            "Citation metadata is local until public archive deposition.",
            "ready_with_author_completion",
        ),
        row(
            "submission",
            "final_submission_file_bundle",
            "materials/FINAL_SUBMISSION_FILE_BUNDLE.md",
            f"{bundle['summary']['file_row_count']} rows; missing_required={bundle['summary']['missing_required_count']}",
            "Use to map local files to journal submission, supplement, source-data, archive, and internal-preflight slots.",
            "Choose final upload subset after selecting the target journal.",
            "Bundle map is not a final submission receipt.",
            "pass" if bundle["summary"]["missing_required_count"] == 0 else "review_required",
        ),
        row(
            "submission",
            "author_upload_gap_closure",
            "materials/AUTHOR_UPLOAD_GAP_CLOSURE_AUDIT.md",
            (
                f"{upload_gap['summary']['row_count']} rows; "
                f"review_required={upload_gap['summary']['review_required_count']}; "
                f"author_action={upload_gap['summary']['author_action_required_count']}; "
                f"stale_active_entry={upload_gap['summary']['stale_active_entry_field_count']}"
            ),
            "Use as the upload-before-handoff audit that confirms local entry materials are aligned.",
            "Complete DOI/accession, author-certified metadata, and final target-journal upload choices manually.",
            "A pass confirms local gap closure only; it is not a journal receipt or author certification.",
            upload_gap["summary"]["status"],
        ),
        row(
            "submission",
            "public_archive_journal_upload_dry_run",
            "materials/PUBLIC_ARCHIVE_JOURNAL_UPLOAD_DRY_RUN_AUDIT.md",
            (
                f"{upload_dry_run['summary']['row_count']} dry-run rows; "
                f"review_required={upload_dry_run['summary']['review_required_count']}; "
                f"author_action={upload_dry_run['summary']['author_action_required_count']}; "
                f"undocumented_release_missing={upload_dry_run['summary']['undocumented_missing_from_release_count']}"
            ),
            "Use as the final no-upload rehearsal for journal files, supplement/source data, public archive materials, size routing, and author-certified fields.",
            "Complete DOI/accession, target-journal portal choices, and author-certified metadata manually.",
            "Dry run does not upload files, create public identifiers, or certify author declarations.",
            upload_dry_run["summary"]["status"],
        ),
        row(
            "submission",
            "supplementary_materials_index",
            "materials/SUPPLEMENTARY_MATERIALS_INDEX.md; materials/SUPPLEMENTARY_TABLE_LEGENDS.md; materials/SUPPLEMENT_UPLOAD_DECISION_MATRIX.md",
            (
                f"{supplement['summary']['item_count']} items; "
                f"{table_legends['summary']['legend_count']} legends; "
                f"review_required={supplement['summary']['review_required_count'] + table_legends['summary']['review_required_count']}; "
                f"author_selection={supplement_decision['summary']['author_selection_required_count']}"
            ),
            "Use as the supplement/source-data index plus draft caption and boundary pack.",
            "Adapt labels/order/captions to target journal style and decide optional reviewer-support uploads.",
            "Supplement index does not replace required journal formatting.",
            "pass"
            if supplement["summary"]["review_required_count"] == 0
            and supplement_decision["summary"]["required_missing_count"] == 0
            and table_legends["summary"]["status"] == "pass"
            else "review_required",
        ),
        row(
            "submission",
            "target_journal_compliance",
            "materials/TARGET_JOURNAL_COMPLIANCE_MATRIX.md",
            f"{journal['summary']['row_count']} rows; author_action={journal['summary']['author_action_count']}",
            "Use to map common Nature/Science/Cell-style requirements to local evidence and author actions.",
            "Recheck official target-journal instructions before upload.",
            "The matrix does not certify compliance with a specific journal portal.",
            "ready_with_author_action",
        ),
        row(
            "submission",
            "portal_field_completion",
            "materials/SUBMISSION_PORTAL_FIELD_COMPLETION_PACK.md",
            f"{portal_fields['summary']['field_count']} fields; author_required={portal_fields['summary']['author_required_count']}",
            "Use for title, abstract, availability, ethics, declarations, and upload-plan portal text.",
            "Complete author-required and archive-dependent fields.",
            "Draft portal text is not author-certified.",
            portal_fields["summary"]["status"],
        ),
        row(
            "submission",
            "editorial_frontmatter_claim_audit",
            "materials/EDITORIAL_FRONTMATTER_CLAIM_AUDIT.md",
            (
                f"{frontmatter['summary']['scanned_file_count']} front-matter files scanned; "
                f"blockers={frontmatter['summary']['blocker_count']}; "
                f"reviewed_guardrails={frontmatter['summary']['reviewed_guardrail_count']}"
            ),
            "Use before journal upload to verify abstract, highlights, cover letter, significance, narrative, and triage wording.",
            "Rerun after any edits to editor-facing short-form text.",
            "A pass confirms overclaim guardrails in saved drafts, not author approval of final portal wording.",
            frontmatter["summary"]["status"],
        ),
        row(
            "submission",
            "claim_boundary_communication_pack",
            "materials/CLAIM_DOWNGRADE_MAP.md; materials/WHAT_THIS_PAPER_DOES_NOT_CLAIM.md",
            (
                f"{claim_boundary['summary']['downgrade_row_count']} downgrade rows; "
                f"{claim_boundary['summary']['not_claim_row_count']} do-not-claim rows; "
                f"missing_support={claim_boundary['summary']['missing_downgrade_evidence_count'] + claim_boundary['summary']['missing_not_claim_support_count']}"
            ),
            "Use to downgrade risky wording and keep response/cover-letter claims inside the saved evidence boundary.",
            "Rerun after any manuscript, abstract, highlights, cover-letter, or response-letter wording edit.",
            "Communication guardrail only; it adds no empirical evidence and does not replace author approval.",
            claim_boundary["summary"]["status"],
        ),
        row(
            "submission",
            "reviewer_response_seed_pack",
            "materials/REVIEWER_RESPONSE_SEED_PACK.md",
            (
                f"{response_seed['summary']['row_count']} response seeds; "
                f"incomplete_evidence={response_seed['summary']['evidence_incomplete_count']}"
            ),
            "Use before drafting rebuttal, revision cover letters, or editor-facing clarifications.",
            "Authors must adapt tone, add manuscript line references, and certify final response wording.",
            "Response seeds are preparation aids and do not add new evidence.",
            response_seed["summary"]["status"],
        ),
        row(
            "submission",
            "revision_response_execution_checklist",
            "materials/REVISION_RESPONSE_EXECUTION_CHECKLIST.md",
            (
                f"{revision_checklist['summary']['row_count']} revision actions; "
                f"line_refs_pending={revision_checklist['summary']['line_references_pending_count']}"
            ),
            "Use after reviewer comments arrive to convert response seeds into manuscript edits and line-reference tasks.",
            "Authors must add real line references after revision and certify final response wording.",
            "Checklist is author-execution support, not completed rebuttal text.",
            revision_checklist["summary"]["status"],
        ),
        row(
            "submission",
            "portal_copyedit_lock_audit",
            "materials/PORTAL_COPYEDIT_LOCK_AUDIT.md",
            (
                f"{copyedit_lock['summary']['scanned_text_count']} text blocks scanned; "
                f"blockers={copyedit_lock['summary']['blocker_count']}; cautions={copyedit_lock['summary']['caution_count']}"
            ),
            "Use before journal upload or portal copy-paste to catch overclaim wording in short-form text.",
            "Rerun after title, abstract, highlights, cover-letter, narrative, or portal-field edits.",
            "Audit pass applies only to saved drafts and does not certify final author edits.",
            copyedit_lock["summary"]["status"],
        ),
        row(
            "submission",
            "blinded_review_anonymization_audit",
            "materials/BLINDED_REVIEW_ANONYMIZATION_AUDIT.md",
            (
                f"{blinded_audit['summary']['scanned_file_count']} files scanned; "
                f"hits={blinded_audit['summary']['scan_hit_count']}; "
                f"author_required={blinded_audit['summary']['author_required_count']}"
            ),
            "Use when the target journal or venue requires double-blind review or anonymous reviewer files.",
            "Authors must decide the blind-review policy and prepare any anonymized reviewer copy manually.",
            "Journal-neutral audit only; it does not anonymize files or certify a specific policy.",
            blinded_audit["summary"]["status"],
        ),
        row(
            "submission",
            "ai_tool_use_disclosure_audit",
            "materials/AI_TOOL_USE_DISCLOSURE_AUDIT.md",
            (
                f"{ai_disclosure['summary']['scan_file_count']} files scanned; "
                f"hits={ai_disclosure['summary']['scan_hit_count']}; "
                f"author_required={ai_disclosure['summary']['author_required_count']}"
            ),
            "Use before journal upload to separate package-supported automation facts from author-certified AI/tool-use declarations.",
            "Authors must complete any target-journal AI/tool-use declaration manually.",
            "Journal-neutral audit only; it does not certify private author tool use.",
            ai_disclosure["summary"]["status"],
        ),
        row(
            "submission",
            "remaining_author_blockers",
            "materials/REMAINING_AUTHOR_BLOCKERS_MATRIX.md",
            f"{blockers['summary']['row_count']} rows; author_required={blockers['summary']['author_required_count']}",
            "Use to separate locally completed work from author-owned blockers.",
            "Authors must complete certified metadata, archive deposition, and target-journal choices.",
            "Automation cannot complete author declarations or public archive identifiers.",
            "ready_with_author_completion",
        ),
        row(
            "submission",
            "final_author_handoff_checklist",
            "materials/FINAL_AUTHOR_HANDOFF_CHECKLIST.md",
            f"{handoff['summary']['row_count']} steps; blocking={handoff['summary']['blocking_row_count']}",
            "Use as the final author-facing upload sequence after local gates are clean.",
            "Authors must complete journal selection, metadata, disclosures, external archive deposition, and final freeze.",
            "Ready status means local handoff readiness, not certified author completion or journal acceptance.",
            handoff["summary"]["status"],
        ),
        row(
            "quality_gates",
            "publication_verification",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.md",
            f"{verification['summary']['gate_count']} gates; failed={verification['summary']['failed_gates']}",
            "Use as the main local package preflight gate.",
            "Rerun after any material or manuscript edit.",
            "Local gate pass is not journal acceptance.",
            verification["summary"]["status"],
        ),
        row(
            "quality_gates",
            "publication_smoke_test",
            "materials/PUBLICATION_SMOKE_TEST.md",
            f"{smoke['summary']['check_count']} checks; failed={smoke['summary']['failed_checks']}",
            "Use as a fast independent integrity check without rerunning expensive rollouts.",
            "Rerun immediately before sharing the package.",
            "Smoke test checks saved artifacts; it does not rerun simulations.",
            smoke["summary"]["status"],
        ),
        row(
            "quality_gates",
            "data_dictionary",
            "materials/DATA_DICTIONARY.md",
            f"{dictionary['summary']['table_count']} tables; missing definitions={dictionary['summary']['missing_definition_count']}",
            "Use to interpret source-data and supplementary CSVs.",
            "Update after adding any CSV table.",
            "Dictionary completeness does not replace journal-specific data formatting.",
            "pass" if dictionary["summary"]["complete"] else "review_required",
        ),
    ]

    review_required = [item for item in rows if item["status"] == "review_required"]
    author_completion = [item for item in rows if "author" in item["status"] or "author" in item["author_action"].lower()]
    archive_dependent = [item for item in rows if "archive" in item["author_action"].lower() or "doi" in item["author_action"].lower()]
    return {
        "root": str(root),
        "title": "Reporting and Supplement Navigator",
        "purpose": (
            "Provide a one-page navigation layer for top-journal Methods, Supplementary Information, "
            "source data, ethics/disclosure, archive, submission, and quality-gate materials."
        ),
        "rows": rows,
        "summary": {
            "status": "pass" if not review_required else "review_required",
            "row_count": len(rows),
            "review_required_count": len(review_required),
            "author_completion_count": len(author_completion),
            "archive_dependent_count": len(archive_dependent),
            "publication_verification_status": verification["summary"]["status"],
            "publication_smoke_test_reference": "materials/PUBLICATION_SMOKE_TEST.json",
            "artifact_provenance": f"{provenance['complete_count']}/{len(provenance['artifacts'])}",
            "data_dictionary_complete": dictionary["summary"]["complete"],
            "reviewer_command_preflight_status": command_preflight["summary"]["status"],
            "reviewer_command_preflight_subcommands": command_preflight["summary"]["subcommand_count"],
            "author_upload_gap_closure_status": upload_gap["summary"]["status"],
            "author_upload_gap_closure_review_required": upload_gap["summary"]["review_required_count"],
            "public_archive_journal_upload_dry_run_status": upload_dry_run["summary"]["status"],
            "public_archive_journal_upload_dry_run_review_required": upload_dry_run["summary"]["review_required_count"],
            "submission_dashboard_review_required": dashboard["summary"]["review_required_row_count"],
            "core_dashboard_review_required": core_dashboard_review_required_count,
            "core_trace_review_required": core_trace_review_required_count,
            "effect_size_uncertainty_status": effects["summary"]["status"],
            "effect_size_uncertainty_rows": effects["summary"]["row_count"],
            "archive_size_budget_status": archive_size["summary"]["status"],
            "archive_size_budget_reference": "materials/ARCHIVE_SIZE_BUDGET_REPORT.json",
            "slim_submission_package_status": slim_package["summary"]["status"],
            "slim_submission_package_size_reference": "materials/SLIM_SUBMISSION_PACKAGE_MANIFEST.json",
        },
        "interpretation": (
            "This navigator is a reviewer and author convenience layer. It points to authoritative files and preserves "
            "the simulator-only, diagnostic-oracle, author-certification, and archive-pending boundaries."
        ),
    }


def write_csv(report, path):
    fields = [
        "section",
        "item",
        "primary_file",
        "source_summary",
        "reviewer_use",
        "author_action",
        "boundary",
        "status",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(report["rows"])


def write_markdown(report, path):
    lines = [
        "# Reporting and Supplement Navigator",
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
            "## Navigator",
            "",
            "| section | item | status | primary file | source summary | reviewer use | author action | boundary |",
            "|---|---|---|---|---|---|---|---|",
        ]
    )
    for item in report["rows"]:
        lines.append(
            f"| {item['section']} | {item['item']} | {item['status']} | `{item['primary_file']}` | "
            f"{item['source_summary']} | {item['reviewer_use']} | {item['author_action']} | {item['boundary']} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export reporting and supplement navigator.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_report(root)
    out_json = materials / "REPORTING_SUPPLEMENT_NAVIGATOR.json"
    out_md = materials / "REPORTING_SUPPLEMENT_NAVIGATOR.md"
    out_csv = materials / "REPORTING_SUPPLEMENT_NAVIGATOR.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv), "summary": report["summary"]}, indent=2))


if __name__ == "__main__":
    main()
