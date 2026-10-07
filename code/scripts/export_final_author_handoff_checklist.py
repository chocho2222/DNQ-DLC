#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def row(
    step,
    phase,
    owner,
    priority,
    action,
    acceptance_criteria,
    evidence,
    rerun_after_completion,
    blocks_upload,
):
    return {
        "step": step,
        "phase": phase,
        "owner": owner,
        "priority": priority,
        "action": action,
        "acceptance_criteria": acceptance_criteria,
        "evidence": evidence,
        "rerun_after_completion": rerun_after_completion,
        "blocks_upload": blocks_upload,
    }


def build_report(root):
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    smoke = load_json(root / "materials" / "PUBLICATION_SMOKE_TEST.json")
    dashboard = load_json(root / "materials" / "SUBMISSION_READINESS_DASHBOARD.json")
    blockers = load_json(root / "materials" / "REMAINING_AUTHOR_BLOCKERS_MATRIX.json")
    freeze = load_json(root / "materials" / "AUTHOR_ACTION_FREEZE_PLAN.json")
    portal = load_json(root / "materials" / "SUBMISSION_PORTAL_FIELD_COMPLETION_PACK.json")
    metadata = load_json(root / "materials" / "SUBMISSION_METADATA_DRAFT.json")
    archive = load_json(root / "materials" / "EXTERNAL_ARCHIVE_PREFLIGHT.json")
    ai = load_json(root / "materials" / "AI_TOOL_USE_DISCLOSURE_AUDIT.json")
    blinded = load_json(root / "materials" / "BLINDED_REVIEW_ANONYMIZATION_AUDIT.json")

    verification_status = verification["summary"]["status"]
    smoke_status = smoke["summary"]["status"]
    dashboard_review = dashboard["summary"]["review_required_row_count"]
    blocker_count = blockers["summary"]["author_required_count"]

    rows = [
        row(
            1,
            "journal_selection",
            "authors",
            "required_before_upload",
            "Select the target journal, article type, template, word/figure limits, and double-blind or single-blind route.",
            "Journal route is fixed; manuscript source/PDF and portal fields follow the selected journal's current instructions.",
            "materials/TARGET_JOURNAL_COMPLIANCE_MATRIX.md; materials/SUBMISSION_PORTAL_PACKAGE_MAP.md; materials/BLINDED_REVIEW_ANONYMIZATION_AUDIT.md",
            "scripts/export_target_journal_compliance_matrix.py; scripts/export_submission_portal_package_map.py; scripts/export_blinded_review_anonymization_audit.py",
            True,
        ),
        row(
            2,
            "author_metadata",
            "authors",
            "required_before_upload",
            "Complete author identities, affiliations, ORCID IDs, corresponding-author details, CRediT roles, and contribution wording.",
            "All author-owned metadata rows are author-certified and match the manuscript/frontmatter and portal entries.",
            "materials/SUBMISSION_METADATA_DRAFT.md; materials/SUBMISSION_METADATA_AUTHORS.csv; materials/SUBMISSION_METADATA_CREDIT.csv",
            "scripts/export_submission_metadata_draft.py; scripts/export_author_owned_submission_integrity_audit.py; scripts/export_submission_readiness_dashboard.py",
            True,
        ),
        row(
            3,
            "declarations",
            "authors",
            "required_before_upload",
            "Confirm competing interests, funding, acknowledgements, ethics/safety declarations, and AI/tool-use disclosure required by the selected journal.",
            "Disclosure text is author-certified; package-supported automation claims remain separate from any author-specific AI/writing/code-assistance disclosure.",
            "materials/ETHICS_DISCLOSURE_READINESS_PACK.md; materials/AI_TOOL_USE_DISCLOSURE_AUDIT.md; materials/SUBMISSION_METADATA_DECLARATIONS.csv",
            "scripts/export_ethics_disclosure_readiness_pack.py; scripts/export_ai_tool_use_disclosure_audit.py; scripts/export_submission_metadata_draft.py",
            True,
        ),
        row(
            4,
            "external_archive",
            "authors",
            "required_before_upload_or_revision",
            "Deposit the final package in a public repository and replace pending DOI/URL/accession placeholders.",
            "Data/code availability, FAIR metadata, archive preflight, and citation metadata all point to real external identifiers.",
            "materials/EXTERNAL_ARCHIVE_PREFLIGHT.md; materials/FAIR_ARCHIVE_METADATA.md; materials/DATA_CODE_AVAILABILITY.md; materials/CITATION_METADATA.md",
            "scripts/export_external_archive_preflight.py; scripts/export_fair_archive_metadata.py; scripts/export_data_code_availability.py; scripts/export_citation_metadata.py",
            True,
        ),
        row(
            5,
            "manuscript_lock",
            "authors",
            "required_after_final_text",
            "Lock final title, abstract, highlights, main text, cover letter, and limitations wording.",
            "Claim QA, narrative numeric consistency, limitation integration, and frontmatter claim audit remain pass after final text edits.",
            "materials/MANUSCRIPT_CLAIM_QA.md; materials/NARRATIVE_NUMERIC_CONSISTENCY_AUDIT.md; materials/MANUSCRIPT_LIMITATION_INTEGRATION_AUDIT.md; materials/EDITORIAL_FRONTMATTER_CLAIM_AUDIT.md",
            "scripts/export_manuscript_claim_qa.py; scripts/export_narrative_numeric_consistency_audit.py; scripts/export_manuscript_limitation_integration_audit.py; scripts/export_editorial_frontmatter_claim_audit.py",
            True,
        ),
        row(
            6,
            "upload_selection",
            "authors",
            "required_before_upload",
            "Choose which optional reviewer-support and archive-only files will be uploaded, withheld, or reserved for response.",
            "Final submission file bundle and upload selection plan have no missing required files and author-selected optional files are named consistently.",
            "materials/FINAL_SUBMISSION_FILE_BUNDLE.md; materials/SUBMISSION_UPLOAD_SELECTION_PLAN.md; materials/ARCHIVE_UPLOAD_READINESS_MATRIX.md",
            "scripts/export_final_submission_file_bundle.py; scripts/export_submission_upload_selection_plan.py; scripts/export_archive_upload_readiness_matrix.py",
            True,
        ),
        row(
            7,
            "size_and_source_data",
            "authors",
            "required_before_upload_if_requested",
            "Check target-journal source-data naming, figure export settings, supplement size limits, and repository upload limits.",
            "Figure/source-data audit and technical QC remain pass; size budget is accepted or upload partitions are chosen.",
            "materials/FIGURE_SOURCE_DATA_AUDIT.md; materials/FIGURE_TECHNICAL_QC.md; materials/ARCHIVE_SIZE_BUDGET_REPORT.md; figures/*_source_data.csv",
            "scripts/export_figure_source_data_audit.py; scripts/export_figure_technical_qc.py; scripts/export_archive_size_budget_report.py",
            False,
        ),
        row(
            8,
            "final_freeze",
            "authors",
            "required_after_all_edits",
            "Regenerate release manifest, checksum freeze record, verification gates, dashboard, and smoke test after all author edits.",
            "Publication verification and smoke test are pass; release manifest has zero missing, size-mismatch, or SHA-mismatch files.",
            "materials/RELEASE_ARCHIVE_MANIFEST.md; materials/FINAL_CHECKSUM_FREEZE_RECORD.md; materials/PUBLICATION_PACKAGE_VERIFICATION.md; materials/PUBLICATION_SMOKE_TEST.md",
            "scripts/export_release_archive_manifest.py; scripts/export_final_checksum_freeze_record.py; scripts/export_publication_package_verification.py; scripts/run_publication_smoke_test.py",
            True,
        ),
    ]

    priority_counts = {}
    for item in rows:
        priority_counts[item["priority"]] = priority_counts.get(item["priority"], 0) + 1

    return {
        "root": str(root),
        "title": "Final Author Handoff Checklist",
        "purpose": (
            "Provide a submission-facing, author-owned handoff checklist that turns the local evidence package "
            "into a target-journal upload sequence without fabricating author identities, disclosures, or external identifiers."
        ),
        "rows": rows,
        "summary": {
            "status": "ready_for_author_handoff" if verification_status == "pass" and smoke_status == "pass" else "local_gate_review_required",
            "row_count": len(rows),
            "blocking_row_count": sum(1 for item in rows if item["blocks_upload"]),
            "priority_counts": priority_counts,
            "publication_verification_status": verification_status,
            "publication_smoke_test_reference": "materials/PUBLICATION_SMOKE_TEST.json",
            "submission_dashboard_review_required": dashboard_review,
            "remaining_author_required_count": blocker_count,
            "freeze_plan_blockers": freeze["summary"]["blocker_count"],
            "portal_author_required_fields": portal["summary"]["author_required_count"],
            "metadata_author_required_count": metadata["summary"]["author_required_count"],
            "archive_author_required_count": archive["summary"]["author_required_count"],
            "ai_disclosure_author_required_count": ai["summary"]["author_required_count"],
            "blinded_review_scan_hit_count": blinded["summary"]["scan_hit_count"],
        },
        "interpretation": (
            "A ready_for_author_handoff status means the local package gates are clean enough for author completion. "
            "It does not certify author metadata, disclosures, journal-specific formatting, or public archive deposition."
        ),
    }


def write_csv(report, path):
    fields = [
        "step",
        "phase",
        "owner",
        "priority",
        "action",
        "acceptance_criteria",
        "evidence",
        "rerun_after_completion",
        "blocks_upload",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in report["rows"]:
            writer.writerow({key: item[key] for key in fields})


def write_markdown(report, path):
    lines = [
        "# Final Author Handoff Checklist",
        "",
        report["purpose"],
        "",
        report["interpretation"],
        "",
        "## Summary",
        "",
        f"- Status: `{report['summary']['status']}`",
        f"- Rows: {report['summary']['row_count']}",
        f"- Blocking rows: {report['summary']['blocking_row_count']}",
        f"- Publication verification: `{report['summary']['publication_verification_status']}`",
        f"- Publication smoke test reference: `{report['summary']['publication_smoke_test_reference']}`",
        f"- Remaining author-required rows: {report['summary']['remaining_author_required_count']}",
        f"- Portal author-required fields: {report['summary']['portal_author_required_fields']}",
        f"- Metadata author-required rows: {report['summary']['metadata_author_required_count']}",
        f"- Archive author-required rows: {report['summary']['archive_author_required_count']}",
        f"- AI/tool disclosure author-required rows: {report['summary']['ai_disclosure_author_required_count']}",
        "",
        "## Checklist",
        "",
        "| step | phase | priority | blocks upload | action | acceptance criteria | evidence | rerun after completion |",
        "|---:|---|---|---|---|---|---|---|",
    ]
    for item in report["rows"]:
        lines.append(
            f"| {item['step']} | {item['phase']} | {item['priority']} | {item['blocks_upload']} | "
            f"{item['action']} | {item['acceptance_criteria']} | `{item['evidence']}` | `{item['rerun_after_completion']}` |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export final author handoff checklist.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_report(root)
    out_json = materials / "FINAL_AUTHOR_HANDOFF_CHECKLIST.json"
    out_md = materials / "FINAL_AUTHOR_HANDOFF_CHECKLIST.md"
    out_csv = materials / "FINAL_AUTHOR_HANDOFF_CHECKLIST.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv), "summary": report["summary"]}, indent=2))


if __name__ == "__main__":
    main()
