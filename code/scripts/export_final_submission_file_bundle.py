#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def split_paths(value):
    if isinstance(value, list):
        return value
    if not value:
        return []
    return [item.strip() for item in str(value).split(";") if item.strip()]


def file_row(slot, file_type, rel_path, required, upload_package, source, note):
    return {
        "slot": slot,
        "file_type": file_type,
        "path": rel_path,
        "required": required,
        "upload_package": upload_package,
        "source": source,
        "note": note,
    }


def build_bundle(root):
    manifest = load_json(root / "manifest.json")
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    provenance = load_json(root / "tables" / "artifact_provenance.json")
    release = load_json(root / "materials" / "RELEASE_ARCHIVE_MANIFEST.json")
    portal = load_json(root / "materials" / "SUBMISSION_PORTAL_PACKAGE_MAP.json")
    portal_fields = load_json(root / "materials" / "SUBMISSION_PORTAL_FIELD_COMPLETION_PACK.json")
    reviewer_trace = load_json(root / "materials" / "REVIEWER_EVIDENCE_TRACE_PACK.json")
    response_seed = load_json(root / "materials" / "REVIEWER_RESPONSE_SEED_PACK.json")
    revision_checklist = load_json(root / "materials" / "REVISION_RESPONSE_EXECUTION_CHECKLIST.json")
    copyedit_lock = load_json(root / "materials" / "PORTAL_COPYEDIT_LOCK_AUDIT.json")
    blinded_audit = load_json(root / "materials" / "BLINDED_REVIEW_ANONYMIZATION_AUDIT.json")
    ai_disclosure = load_json(root / "materials" / "AI_TOOL_USE_DISCLOSURE_AUDIT.json")
    smoke = load_json(root / "materials" / "PUBLICATION_SMOKE_TEST.json")
    methods_capsule = load_json(root / "materials" / "METHODS_REPRODUCIBILITY_CAPSULE.json")
    ethics_disclosure = load_json(root / "materials" / "ETHICS_DISCLOSURE_READINESS_PACK.json")
    navigator = load_json(root / "materials" / "REPORTING_SUPPLEMENT_NAVIGATOR.json")
    replication_route = load_json(root / "materials" / "REVIEWER_REPLICATION_ROUTE.json")
    assembly_map = load_json(root / "materials" / "MANUSCRIPT_SUPPLEMENT_ASSEMBLY_MAP.json")
    table_legends = load_json(root / "materials" / "SUPPLEMENTARY_TABLE_LEGENDS.json")
    statistical_appendix = load_json(root / "materials" / "STATISTICAL_REPORTING_APPENDIX.json")
    source_audit = load_json(root / "materials" / "FIGURE_SOURCE_DATA_AUDIT.json")
    figure_qc = load_json(root / "materials" / "FIGURE_TECHNICAL_QC.json")
    limitation_audit = load_json(root / "materials" / "MANUSCRIPT_LIMITATION_INTEGRATION_AUDIT.json")
    frontmatter_audit = load_json(root / "materials" / "EDITORIAL_FRONTMATTER_CLAIM_AUDIT.json")
    freeze = load_json(root / "materials" / "AUTHOR_ACTION_FREEZE_PLAN.json")
    handoff = load_json(root / "materials" / "FINAL_AUTHOR_HANDOFF_CHECKLIST.json")
    journal = load_json(root / "materials" / "TARGET_JOURNAL_COMPLIANCE_MATRIX.json")

    release_paths = {item["path"] for item in release["files"]}
    rows = [
        file_row(
            "main_manuscript",
            "manuscript_markdown_source",
            "manuscript/main.md",
            True,
            "journal_submission",
            "manuscript/manuscript_manifest.json",
            "Local conservative manuscript draft; must be converted to the selected journal template.",
        ),
        file_row(
            "main_manuscript",
            "manuscript_manifest",
            "manuscript/manuscript_manifest.json",
            True,
            "journal_submission",
            "manuscript/README.md",
            "Local manuscript file map.",
        ),
        file_row(
            "main_manuscript",
            "journal_neutral_latex_source",
            "manuscript/main.tex",
            True,
            "journal_submission",
            "materials/MANUSCRIPT_SOURCE_PACKAGE_AUDIT.md",
            "Generated journal-neutral LaTeX scaffold; must be moved into the selected journal template before submission.",
        ),
        file_row(
            "main_manuscript",
            "manuscript_source_package_readme",
            "manuscript/SOURCE_PACKAGE_README.md",
            True,
            "journal_submission",
            "materials/MANUSCRIPT_SOURCE_PACKAGE_AUDIT.md",
            "Source package scope, boundaries, and final author actions.",
        ),
        file_row(
            "main_manuscript",
            "manuscript_source_package_audit",
            "materials/MANUSCRIPT_SOURCE_PACKAGE_AUDIT.md",
            True,
            "internal_pre_submission",
            "materials/MANUSCRIPT_SOURCE_PACKAGE_AUDIT.json",
            "Audit for manuscript source package readiness.",
        ),
        file_row(
            "main_manuscript",
            "manuscript_compile_preflight",
            "materials/MANUSCRIPT_COMPILE_PREFLIGHT.md",
            True,
            "internal_pre_submission",
            "materials/MANUSCRIPT_COMPILE_PREFLIGHT.json",
            "Static LaTeX source, citation, bibliography, and compile-tool preflight.",
        ),
        file_row(
            "references",
            "bibliography",
            "manuscript/references.bib",
            True,
            "journal_submission",
            "materials/REFERENCE_READINESS_AUDIT.md",
            "Starter bibliography; related work expansion remains author-owned.",
        ),
        file_row(
            "cover_letter",
            "cover_letter_source",
            "materials/COVER_LETTER_DRAFT_PACKAGE.md",
            True,
            "journal_submission",
            "materials/COVER_LETTER_DRAFT_PACKAGE.json",
            "Evidence-bound draft; requires target-journal adaptation.",
        ),
        file_row(
            "short_text",
            "title_abstract_highlights",
            "materials/TITLE_ABSTRACT_HIGHLIGHTS_PACKAGE.md",
            True,
            "journal_submission",
            "materials/TITLE_ABSTRACT_HIGHLIGHTS_PACKAGE.json",
            "Evidence-bound short-form text for portal fields.",
        ),
        file_row(
            "short_text",
            "editorial_frontmatter_claim_audit",
            "materials/EDITORIAL_FRONTMATTER_CLAIM_AUDIT.md",
            True,
            "internal_pre_submission",
            "materials/EDITORIAL_FRONTMATTER_CLAIM_AUDIT.json",
            (
                "Overclaim audit for title, abstract, highlights, cover letter, significance, narrative, and triage text; "
                f"status: {frontmatter_audit['summary']['status']}."
            ),
        ),
        file_row(
            "portal_fields",
            "portal_field_completion_pack",
            "materials/SUBMISSION_PORTAL_FIELD_COMPLETION_PACK.md",
            True,
            "journal_submission",
            "materials/SUBMISSION_PORTAL_FIELD_COMPLETION_PACK.json",
            (
                "Field-by-field portal copy package separating copy-ready, archive-dependent, and author-required fields; "
                f"status: {portal_fields['summary']['status']}."
            ),
        ),
        file_row(
            "supplement",
            "supplementary_index",
            "materials/SUPPLEMENTARY_INDEX.md",
            True,
            "supplement",
            "materials/README.md",
            "Reviewer navigation for all supplementary artifacts.",
        ),
        file_row(
            "supplement",
            "supplementary_table_legends",
            "materials/SUPPLEMENTARY_TABLE_LEGENDS.md",
            True,
            "supplement",
            "materials/SUPPLEMENTARY_TABLE_LEGENDS.json",
            (
                "Journal-adaptable captions, key columns, dictionary links, and claim boundaries for supplementary "
                f"tables and source data; status: {table_legends['summary']['status']}."
            ),
        ),
        file_row(
            "supplement",
            "reporting_supplement_navigator",
            "materials/REPORTING_SUPPLEMENT_NAVIGATOR.md",
            True,
            "supplement",
            "materials/REPORTING_SUPPLEMENT_NAVIGATOR.json",
            (
                "One-page Methods, supplement, source-data, ethics/disclosure, archive, submission, and quality-gate navigator; "
                f"status: {navigator['summary']['status']}."
            ),
        ),
        file_row(
            "supplement",
            "reviewer_replication_route",
            "materials/REVIEWER_REPLICATION_ROUTE.md",
            True,
            "supplement",
            "materials/REVIEWER_REPLICATION_ROUTE.json",
            (
                "Tiered reviewer replication route from fast saved-artifact checks to optional GPU rollout reruns; "
                f"status: {replication_route['summary']['status']}."
            ),
        ),
        file_row(
            "supplement",
            "manuscript_supplement_assembly_map",
            "materials/MANUSCRIPT_SUPPLEMENT_ASSEMBLY_MAP.md",
            True,
            "supplement",
            "materials/MANUSCRIPT_SUPPLEMENT_ASSEMBLY_MAP.json",
            (
                "Map from manuscript claims and sections to figures, source data, supplement files, archive materials, "
                f"and author-action boundaries; status: {assembly_map['summary']['status']}."
            ),
        ),
        file_row(
            "supplement",
            "methods",
            "materials/METHODS.md",
            True,
            "supplement",
            "materials/MANUSCRIPT_OUTLINE.md",
            "Methods scaffold for supplement or final manuscript adaptation.",
        ),
        file_row(
            "supplement",
            "methods_reproducibility_capsule",
            "materials/METHODS_REPRODUCIBILITY_CAPSULE.md",
            True,
            "supplement",
            "materials/METHODS_REPRODUCIBILITY_CAPSULE.json",
            (
                "Structured Methods/Reporting Summary-ready capsule linking endpoints, seeds, statistics, compute, "
                f"environment, reproducibility gates, and claim boundaries; status: {methods_capsule['summary']['status']}."
            ),
        ),
        file_row(
            "supplement",
            "statistical_reporting_appendix",
            "materials/STATISTICAL_REPORTING_APPENDIX.md",
            True,
            "supplement",
            "materials/STATISTICAL_REPORTING_APPENDIX.json",
            (
                "Consolidated statistical reporting appendix for uncertainty intervals, exact tests, sample-size "
                f"limitations, endpoint sensitivity, and claim boundaries; status: {statistical_appendix['summary']['status']}."
            ),
        ),
        file_row(
            "supplement",
            "statistics_plan",
            "materials/STATISTICAL_ANALYSIS_PLAN.md",
            True,
            "supplement",
            "materials/STATISTICAL_CONSISTENCY_AUDIT.md",
            "Statistical methods and seed-set boundaries.",
        ),
        file_row(
            "supplement",
            "claim_evidence",
            "materials/CLAIM_EVIDENCE_MATRIX.md",
            True,
            "supplement",
            "materials/MANUSCRIPT_CLAIM_QA.md",
            "Claim-to-evidence map and prohibited wording.",
        ),
        file_row(
            "supplement",
            "threats_to_validity_audit",
            "materials/THREATS_TO_VALIDITY_AUDIT.md",
            True,
            "internal_pre_submission",
            "materials/THREATS_TO_VALIDITY_AUDIT.json",
            "Reviewer-facing validity-threat map for Discussion limitations and claim boundaries.",
        ),
        file_row(
            "archive",
            "data_code_availability",
            "materials/DATA_CODE_AVAILABILITY.md",
            True,
            "archive_and_submission",
            "materials/FAIR_ARCHIVE_METADATA.md",
            "Local data/code statement; DOI/URL must be inserted after deposition.",
        ),
        file_row(
            "archive",
            "data_code_availability_rows",
            "materials/DATA_CODE_AVAILABILITY.csv",
            True,
            "archive_and_submission",
            "materials/DATA_CODE_AVAILABILITY.json",
            "Machine-readable data/code availability rows for archive and source-data review.",
        ),
        file_row(
            "archive",
            "release_manifest",
            "materials/RELEASE_ARCHIVE_MANIFEST.md",
            True,
            "archive",
            "materials/RELEASE_ARCHIVE_MANIFEST.json",
            "Checksum and file-count manifest for public archive.",
        ),
        file_row(
            "archive",
            "fair_metadata",
            "materials/FAIR_ARCHIVE_METADATA.md",
            True,
            "archive",
            "materials/FAIR_ARCHIVE_METADATA.json",
            "DataCite/Zenodo-oriented metadata draft.",
        ),
        file_row(
            "pre_submission",
            "target_journal_compliance",
            "materials/TARGET_JOURNAL_COMPLIANCE_MATRIX.md",
            True,
            "internal_pre_submission",
            "materials/TARGET_JOURNAL_COMPLIANCE_MATRIX.json",
            "Target-journal requirement mapping; not uploaded unless useful as internal checklist.",
        ),
        file_row(
            "pre_submission",
            "ethics_disclosure_readiness",
            "materials/ETHICS_DISCLOSURE_READINESS_PACK.md",
            True,
            "internal_pre_submission",
            "materials/ETHICS_DISCLOSURE_READINESS_PACK.json",
            (
                "Ethics, disclosure, author-metadata, availability, license, portal, and claim-boundary readiness pack; "
                f"status: {ethics_disclosure['summary']['status']}."
            ),
        ),
        file_row(
            "pre_submission",
            "author_freeze_plan",
            "materials/AUTHOR_ACTION_FREEZE_PLAN.md",
            True,
            "internal_pre_submission",
            "materials/AUTHOR_ACTION_FREEZE_PLAN.json",
            "Author-owned blocker list and final rerun plan.",
        ),
        file_row(
            "pre_submission",
            "final_author_handoff_checklist",
            "materials/FINAL_AUTHOR_HANDOFF_CHECKLIST.md",
            True,
            "internal_pre_submission",
            "materials/FINAL_AUTHOR_HANDOFF_CHECKLIST.json",
            (
                "Final author-facing upload sequence after local gates are clean; "
                f"status: {handoff['summary']['status']}."
            ),
        ),
        file_row(
            "pre_submission",
            "figure_technical_qc",
            "materials/FIGURE_TECHNICAL_QC.md",
            True,
            "internal_pre_submission",
            "materials/FIGURE_TECHNICAL_QC.json",
            (
                "Technical figure-readiness audit for export formats, TIFF DPI, raster dimensions, "
                f"and source-data linkage; status: {figure_qc['summary']['status']}."
            ),
        ),
        file_row(
            "pre_submission",
            "manuscript_limitation_integration",
            "materials/MANUSCRIPT_LIMITATION_INTEGRATION_AUDIT.md",
            True,
            "internal_pre_submission",
            "materials/MANUSCRIPT_LIMITATION_INTEGRATION_AUDIT.json",
            (
                "Static audit that the manuscript draft carries threats-to-validity boundaries; "
                f"status: {limitation_audit['summary']['status']}."
            ),
        ),
        file_row(
            "pre_submission",
            "reviewer_evidence_trace_pack",
            "materials/REVIEWER_EVIDENCE_TRACE_PACK.md",
            True,
            "internal_pre_submission",
            "materials/REVIEWER_EVIDENCE_TRACE_PACK.json",
            (
                "Reviewer-facing trace from claims, figures, seed outcomes, statistics, limitations, "
                f"and package gates; status: {reviewer_trace['summary']['status']}."
            ),
        ),
        file_row(
            "pre_submission",
            "reviewer_response_seed_pack",
            "materials/REVIEWER_RESPONSE_SEED_PACK.md",
            True,
            "internal_pre_submission",
            "materials/REVIEWER_RESPONSE_SEED_PACK.json",
            (
                "Journal-neutral reviewer-response seed pack with evidence routes and claim boundaries; "
                f"status: {response_seed['summary']['status']}."
            ),
        ),
        file_row(
            "pre_submission",
            "revision_response_execution_checklist",
            "materials/REVISION_RESPONSE_EXECUTION_CHECKLIST.md",
            True,
            "internal_pre_submission",
            "materials/REVISION_RESPONSE_EXECUTION_CHECKLIST.json",
            (
                "Author-facing revision execution checklist with line-reference placeholders and evidence routes; "
                f"status: {revision_checklist['summary']['status']}."
            ),
        ),
        file_row(
            "pre_submission",
            "portal_copyedit_lock_audit",
            "materials/PORTAL_COPYEDIT_LOCK_AUDIT.md",
            True,
            "internal_pre_submission",
            "materials/PORTAL_COPYEDIT_LOCK_AUDIT.json",
            (
                "Claim-boundary copyedit audit for journal-facing short text and portal fields; "
                f"status: {copyedit_lock['summary']['status']}."
            ),
        ),
        file_row(
            "pre_submission",
            "blinded_review_anonymization_audit",
            "materials/BLINDED_REVIEW_ANONYMIZATION_AUDIT.md",
            True,
            "internal_pre_submission",
            "materials/BLINDED_REVIEW_ANONYMIZATION_AUDIT.json",
            (
                "Double-blind/single-blind readiness audit for reviewer-facing files, editor-only files, "
                f"metadata, archive identifiers, and local paths; status: {blinded_audit['summary']['status']}."
            ),
        ),
        file_row(
            "pre_submission",
            "ai_tool_use_disclosure_audit",
            "materials/AI_TOOL_USE_DISCLOSURE_AUDIT.md",
            True,
            "internal_pre_submission",
            "materials/AI_TOOL_USE_DISCLOSURE_AUDIT.json",
            (
                "Journal-neutral AI/tool-use disclosure audit separating package-supported automation facts "
                f"from author-certified declarations; status: {ai_disclosure['summary']['status']}."
            ),
        ),
        file_row(
            "pre_submission",
            "publication_smoke_test",
            "materials/PUBLICATION_SMOKE_TEST.md",
            True,
            "internal_pre_submission",
            "materials/PUBLICATION_SMOKE_TEST.json",
            (
                "Fast reviewer-facing integrity smoke test that avoids expensive rollout reruns; "
                f"status: {smoke['summary']['status']}."
            ),
        ),
    ]

    figure_bases = [
        ("figure_1", "figures/figure_1_multicar_overtake_results"),
        ("figure_2", "figures/figure_2_portfolio_selector_summary"),
        ("figure_3", "figures/figure_3_cross_heldout_validation"),
    ]
    for fig_id, base in figure_bases:
        for ext in ["pdf", "tiff", "png", "svg"]:
            rows.append(
                file_row(
                    fig_id,
                    f"figure_{ext}",
                    f"{base}.{ext}",
                    ext in {"pdf", "tiff"},
                    "journal_submission",
                    "materials/FIGURE_SOURCE_DATA_AUDIT.md; materials/FIGURE_TECHNICAL_QC.md",
                    "Exported figure format with technical QC; final journal may prefer a subset.",
                )
            )
    for source_path in ["figures/figure_1_source_data.csv", "figures/figure_2_source_data.csv", "figures/figure_3_source_data.csv", "figures/figure_3_source_data_dictionary.csv"]:
        rows.append(
            file_row(
                "source_data",
                "figure_source_data",
                source_path,
                True,
                "source_data_upload",
                "materials/FIGURE_SOURCE_DATA_AUDIT.md",
                "Figure source-data upload candidate.",
            )
        )

    for item in portal["portal_items"]:
        for local_path in split_paths(item.get("local_files")):
            if "*" in local_path:
                continue
            rows.append(
                file_row(
                    f"portal_{item['slot']}",
                    item["file_type"],
                    local_path,
                    item["status"] in {"ready", "ready_with_limitations", "ready_with_author_action"},
                    "portal_reference",
                    "materials/SUBMISSION_PORTAL_PACKAGE_MAP.md",
                    item["author_action"],
                )
            )

    enriched = []
    seen = set()
    for item in rows:
        key = (item["slot"], item["path"], item["file_type"])
        if key in seen:
            continue
        seen.add(key)
        path = root / item["path"]
        is_directory_reference = item["path"].endswith("/")
        is_metadata_self = (
            item["path"].startswith("materials/RELEASE_ARCHIVE_MANIFEST.")
            or item["path"].startswith("materials/PUBLICATION_PACKAGE_VERIFICATION.")
            or item["path"].startswith("materials/PUBLICATION_SMOKE_TEST.")
            or item["path"].startswith("materials/FINAL_CHECKSUM_FREEZE_RECORD.")
            or item["path"].startswith("materials/FINAL_CHECKSUM_FREEZE_FILE_SNAPSHOTS.")
            or item["path"].startswith("materials/FAIR_ARCHIVE_METADATA.")
            or item["path"].startswith("materials/ARCHIVE_MANIFEST_EXCLUSION_AUDIT.")
            or item["path"].startswith("materials/EXTERNAL_ARCHIVE_PREFLIGHT.")
            or item["path"].startswith("materials/EXTERNAL_ARCHIVE_KEY_FILES.")
            or item["path"].startswith("materials/ARCHIVE_README.")
            or item["path"].startswith("materials/ARCHIVE_SIZE_BUDGET_")
            or item["path"].startswith("materials/SLIM_SUBMISSION_PACKAGE_")
            or item["path"].startswith("materials/FINAL_SUBMISSION_FILE_BUNDLE.")
            or item["path"].startswith("materials/CITATION_METADATA.")
            or item["path"].startswith("materials/CITATION.")
            or item["path"].startswith("materials/SUBMISSION_READINESS_DASHBOARD.")
            or item["path"].startswith("materials/REPORTING_SUPPLEMENT_NAVIGATOR.")
            or item["path"].startswith("materials/FINAL_AUTHOR_HANDOFF_CHECKLIST.")
            or item["path"].startswith("materials/SUBMISSION_UPLOAD_SELECTION_PLAN.")
            or item["path"].startswith("materials/ARCHIVE_UPLOAD_READINESS_MATRIX.")
            or item["path"].startswith("materials/TOP_JOURNAL_REPORTING_SUMMARY.")
            or item["path"].startswith("materials/SUBMISSION_PORTAL_PACKAGE_MAP.")
            or item["path"].startswith("materials/EDITORIAL_SUBMISSION_CHECKLIST.")
            or item["path"].startswith("materials/EDITORIAL_FRONTMATTER_CLAIM_AUDIT.")
            or item["path"].startswith("materials/EDITORIAL_TRIAGE_AND_REVIEWER_CHECKLIST.")
            or item["path"].startswith("materials/TARGET_JOURNAL_COMPLIANCE_MATRIX.")
            or item["path"].startswith("materials/REVIEWER_RISK_RESPONSE_DOSSIER.")
            or item["path"].startswith("materials/REVIEWER_RESPONSE_SEED_PACK.")
            or item["path"].startswith("materials/REVISION_RESPONSE_EXECUTION_CHECKLIST.")
            or item["path"].startswith("materials/PORTAL_COPYEDIT_LOCK_AUDIT.")
            or item["path"].startswith("materials/BLINDED_REVIEW_ANONYMIZATION_AUDIT.")
            or item["path"].startswith("materials/BLINDED_REVIEW_ANONYMIZATION_SCAN_HITS.")
            or item["path"].startswith("materials/AI_TOOL_USE_DISCLOSURE_AUDIT.")
            or item["path"].startswith("materials/AI_TOOL_USE_DISCLOSURE_SCAN_HITS.")
            or item["path"].startswith("materials/SOFTWARE_DEPENDENCY_LICENSE_AUDIT.")
            or item["path"].startswith("materials/SOFTWARE_DEPENDENCY_LICENSE_METADATA.")
            or item["path"].startswith("materials/ARTIFACT_DEPENDENCY_MAP.")
        )
        exists = path.exists()
        in_release = item["path"] in release_paths
        if is_directory_reference:
            status = "author_selection_required" if exists else "review_required"
        elif is_metadata_self:
            status = "ready" if exists else "review_required"
        else:
            status = "ready" if exists and in_release else "review_required"
        enriched.append(
            {
                **item,
                "exists": exists,
                "in_release_manifest": in_release,
                "size_bytes": path.stat().st_size if exists and path.is_file() else None,
                "status": status,
            }
        )

    missing_required = [item for item in enriched if item["required"] and item["status"] == "review_required"]
    author_action_rows = [
        {
            "action_id": "FS1_target_template_conversion",
            "action": "Convert local Markdown manuscript and evidence-bound text into target-journal source/PDF and portal fields.",
            "evidence": "materials/AUTHOR_ACTION_FREEZE_PLAN.md; materials/SUBMISSION_PORTAL_PACKAGE_MAP.md",
        },
        {
            "action_id": "FS2_archive_doi_update",
            "action": "After public deposition, update DOI/URL/accession in availability, FAIR metadata, cover letter, and portal fields.",
            "evidence": "materials/EXTERNAL_ARCHIVE_PREFLIGHT.md; materials/FAIR_ARCHIVE_METADATA.md",
        },
        {
            "action_id": "FS3_final_upload_selection",
            "action": "Select the final subset of figure formats, source data, supplement, and archive files required by the chosen journal.",
            "evidence": "materials/TARGET_JOURNAL_COMPLIANCE_MATRIX.md; materials/AUTHOR_ACTION_FREEZE_PLAN.md",
        },
    ]

    return {
        "root": str(root),
        "title": "Final submission file bundle map",
        "purpose": "Map local manuscript, figure, source-data, supplement, and archive files to final journal-upload slots.",
        "scope": {
            "package_title": manifest["title"],
            "not_final_submission_pdf": True,
            "author_action_boundary": "Target-journal upload files require author template conversion, archive DOI insertion, and final portal choices.",
        },
        "files": enriched,
        "author_actions": author_action_rows,
        "summary": {
            "file_row_count": len(enriched),
            "required_file_count": sum(1 for item in enriched if item["required"]),
            "ready_file_count": sum(1 for item in enriched if item["status"] == "ready"),
            "author_selection_required_count": sum(1 for item in enriched if item["status"] == "author_selection_required"),
            "missing_required_count": len(missing_required),
            "author_action_count": len(author_action_rows),
            "figure_count": source_audit["summary"]["figure_count"],
            "figure_source_complete": source_audit["summary"]["incomplete_count"] == 0,
            "manuscript_limitation_integration_status": limitation_audit["summary"]["status"],
            "publication_verification_status": verification["summary"]["status"],
            "artifact_provenance": f"{provenance['complete_count']}/{len(provenance['artifacts'])}",
            "release_file_count": release["summary"]["file_count"],
            "freeze_plan_blockers": freeze["summary"]["blocker_count"],
            "journal_compliance_rows": journal["summary"]["row_count"],
            "portal_field_completion_status": portal_fields["summary"]["status"],
            "reviewer_evidence_trace_status": reviewer_trace["summary"]["status"],
            "publication_smoke_test_reference": "materials/PUBLICATION_SMOKE_TEST.json",
            "methods_reproducibility_capsule_status": methods_capsule["summary"]["status"],
            "ethics_disclosure_readiness_status": ethics_disclosure["summary"]["status"],
            "reporting_supplement_navigator_status": navigator["summary"]["status"],
            "reviewer_replication_route_status": replication_route["summary"]["status"],
            "manuscript_supplement_assembly_status": assembly_map["summary"]["status"],
            "manuscript_supplement_assembly_rows": assembly_map["summary"]["row_count"],
            "supplementary_table_legends_status": table_legends["summary"]["status"],
            "supplementary_table_legend_count": table_legends["summary"]["legend_count"],
            "statistical_reporting_appendix_status": statistical_appendix["summary"]["status"],
            "statistical_reporting_appendix_rows": statistical_appendix["summary"]["row_count"],
        },
        "interpretation": (
            "This is a local upload-bundle map, not a final journal-submission receipt. "
            "Rows marked internal_pre_submission support author decisions and may not be uploaded."
        ),
    }


def write_csv(report, path):
    fields = [
        "slot",
        "file_type",
        "path",
        "required",
        "upload_package",
        "source",
        "exists",
        "in_release_manifest",
        "size_bytes",
        "status",
        "note",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in report["files"]:
            writer.writerow({key: item[key] for key in fields})


def write_markdown(report, path):
    lines = [
        "# Final Submission File Bundle Map",
        "",
        report["purpose"],
        "",
        report["interpretation"],
        "",
        "## Summary",
        "",
        f"- File rows: {report['summary']['file_row_count']}",
        f"- Required files: {report['summary']['required_file_count']}",
        f"- Ready files: {report['summary']['ready_file_count']}",
        f"- Author-selection rows: {report['summary']['author_selection_required_count']}",
        f"- Missing required files: {report['summary']['missing_required_count']}",
        f"- Publication verification: `{report['summary']['publication_verification_status']}`",
        f"- Artifact provenance: {report['summary']['artifact_provenance']}",
        f"- Freeze-plan blockers: {report['summary']['freeze_plan_blockers']}",
        "",
        "## File Rows",
        "",
        "| slot | file type | required | status | upload package | path | source | note |",
        "|---|---|---:|---|---|---|---|---|",
    ]
    for item in report["files"]:
        lines.append(
            f"| {item['slot']} | {item['file_type']} | {item['required']} | {item['status']} | "
            f"{item['upload_package']} | `{item['path']}` | `{item['source']}` | {item['note']} |"
        )
    lines.extend(["", "## Author Actions", "", "| action id | action | evidence |", "|---|---|---|"])
    for item in report["author_actions"]:
        lines.append(f"| {item['action_id']} | {item['action']} | `{item['evidence']}` |")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export final submission file bundle map.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_bundle(root)
    out_json = materials / "FINAL_SUBMISSION_FILE_BUNDLE.json"
    out_md = materials / "FINAL_SUBMISSION_FILE_BUNDLE.md"
    out_csv = materials / "FINAL_SUBMISSION_FILE_BUNDLE.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv), "summary": report["summary"]}, indent=2))


if __name__ == "__main__":
    main()
