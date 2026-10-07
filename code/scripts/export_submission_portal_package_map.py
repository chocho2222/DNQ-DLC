#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def portal_item(slot, file_type, status, local_files, author_action, evidence_note, boundary):
    return {
        "slot": slot,
        "file_type": file_type,
        "status": status,
        "local_files": local_files,
        "author_action": author_action,
        "evidence_note": evidence_note,
        "boundary": boundary,
    }


def build_map(root):
    manifest = load_json(root / "manifest.json")
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    provenance = load_json(root / "tables" / "artifact_provenance.json")
    submission = load_json(root / "materials" / "SUBMISSION_METADATA_DRAFT.json")
    checklist = load_json(root / "materials" / "EDITORIAL_SUBMISSION_CHECKLIST.json")
    cover = load_json(root / "materials" / "COVER_LETTER_DRAFT_PACKAGE.json")
    preflight = load_json(root / "materials" / "EXTERNAL_ARCHIVE_PREFLIGHT.json")
    release = load_json(root / "materials" / "RELEASE_ARCHIVE_MANIFEST.json")
    dictionary = load_json(root / "materials" / "DATA_DICTIONARY.json")
    claim_qa = load_json(root / "materials" / "MANUSCRIPT_CLAIM_QA.json")
    risk = load_json(root / "materials" / "RESEARCH_RISK_AND_SAFETY.json")
    archive_upload = load_json(root / "materials" / "ARCHIVE_UPLOAD_READINESS_MATRIX.json")
    provenance_ratio = f"{provenance['complete_count']}/{len(provenance['artifacts'])}"

    items = [
        portal_item(
            "main_manuscript",
            "Manuscript source/PDF",
            "needs_author_action",
            "manuscript/main.md; manuscript/manuscript_manifest.json",
            "Convert the conservative Markdown draft to the selected journal template and generate final PDF/source.",
            "Local evidence-linked draft exists.",
            "Not a final submission PDF/source package.",
        ),
        portal_item(
            "cover_letter",
            "Cover letter",
            "needs_author_action",
            "materials/COVER_LETTER_DRAFT_PACKAGE.md; materials/COVER_LETTER_DRAFT_PACKAGE.csv",
            "Insert target journal, corresponding author details, archive DOI, and author-certified declarations.",
            f"Draft package has {len(cover['paragraphs'])} paragraphs and {len(cover['editor_checklist'])} author-checklist rows.",
            "Draft only; author metadata and disclosures require confirmation.",
        ),
        portal_item(
            "figures",
            "Main and supplementary figures",
            "ready",
            "figures/figure_1_multicar_overtake_results.*; figures/figure_2_portfolio_selector_summary.*; figures/figure_3_cross_heldout_validation.*",
            "Select journal-preferred file formats and upload source-data files where required.",
            "PNG/PDF/SVG/TIFF exports and source-data tables are included.",
            "Figure 3 must remain framed as partial transfer, not broad robustness.",
        ),
        portal_item(
            "source_data",
            "Figure/source data",
            "ready",
            "figures/figure_1_source_data.csv; figures/figure_2_source_data.csv; figures/figure_3_source_data.csv; materials/FIGURE_SOURCE_DATA_AUDIT.md",
            "Upload source-data CSVs if the journal requests them separately.",
            "Figure-source-data audit is complete.",
            "Source data support saved simulator experiments only.",
        ),
        portal_item(
            "supplementary_materials",
            "Supplementary information",
            "ready_with_limitations",
            "materials/SUPPLEMENTARY_INDEX.md; tables/; materials/; evaluations/; baselines/",
            "Bundle selected supplementary tables/materials according to journal size and format limits.",
            "Supplementary index and release manifest enumerate local materials.",
            "Do not upload files as evidence for real-road deployment or VLM perception.",
        ),
        portal_item(
            "data_availability",
            "Data availability statement",
            "needs_author_action",
            "materials/DATA_CODE_AVAILABILITY.md; materials/FAIR_ARCHIVE_METADATA.md; materials/EXTERNAL_ARCHIVE_PREFLIGHT.md",
            "After public deposition, replace local-package wording with DOI/URL/accession.",
            f"External archive pending: {preflight['summary']['external_archive_pending']}.",
            "Local archive readiness is not an external DOI.",
        ),
        portal_item(
            "code_availability",
            "Code availability statement",
            "needs_author_action",
            "materials/DATA_CODE_AVAILABILITY.md; materials/scripts/; materials/dlc/; tables/artifact_provenance.md",
            "Add public repository or archive DOI after deposition.",
            f"Artifact provenance is {provenance_ratio}.",
            "Do not imply unsupported hardware, real-road, or VLM deployment support.",
        ),
        portal_item(
            "archive_files",
            "Data/code archive upload",
            "ready_with_author_action",
            "materials/RELEASE_ARCHIVE_MANIFEST.md; materials/RELEASE_ARCHIVE_MANIFEST.csv; materials/ARCHIVE_UPLOAD_READINESS_MATRIX.md",
            "Upload final archive and update checksum/DOI records after deposition.",
            f"Release manifest lists {release['summary']['file_count']} files; exact byte size is locked in RELEASE_ARCHIVE_MANIFEST.json.",
            "Regenerate checksums immediately before final upload.",
        ),
        portal_item(
            "archive_readiness",
            "Archive and upload readiness",
            "ready",
            "materials/ARCHIVE_UPLOAD_READINESS_MATRIX.md; materials/SUBMISSION_READINESS_DASHBOARD.md",
            "Use this matrix to route each local artifact to journal submission, source data, supplement, archive, reviewer support, or internal QC.",
            f"Archive/upload matrix status: {archive_upload['summary']['status']}.",
            "Local readiness mapping is not a deposition receipt or journal portal result.",
        ),
        portal_item(
            "ethics_statement",
            "Ethics / research-risk form",
            "ready",
            "materials/RESEARCH_RISK_AND_SAFETY.md; materials/SIMULATION_TO_REAL_APPLICABILITY.md",
            "Copy simulation-only ethics and deployment-boundary wording into the journal form.",
            risk["ethics_context"]["rationale"],
            "No human, animal, personal-data, public-road, or real-vehicle evidence is included.",
        ),
        portal_item(
            "author_metadata",
            "Author, affiliation, ORCID, corresponding-author fields",
            "needs_author_input",
            "materials/SUBMISSION_METADATA_DRAFT.md; materials/SUBMISSION_METADATA_AUTHORS.csv",
            "Authors must provide verified names, affiliations, ORCIDs, emails, and corresponding-author details.",
            f"Submission metadata draft has {submission['summary']['author_count']} parsed author rows.",
            "Repository AUTHORS data are not certified submission metadata.",
        ),
        portal_item(
            "contributions",
            "CRediT / author contributions",
            "needs_author_input",
            "materials/SUBMISSION_METADATA_CREDIT.csv",
            "Assign CRediT roles manually and confirm with all authors.",
            f"{submission['summary']['credit_role_count']} CRediT roles are templated.",
            "Roles are placeholders until author-confirmed.",
        ),
        portal_item(
            "disclosures",
            "Competing interests, funding, acknowledgements",
            "needs_author_input",
            "materials/SUBMISSION_METADATA_DISCLOSURES.csv",
            "Authors must certify competing interests, funder IDs, acknowledgements, and any required declarations.",
            f"{submission['summary']['disclosure_field_count']} disclosure fields are drafted.",
            "The package cannot infer personal, institutional, or funding disclosures.",
        ),
        portal_item(
            "reporting_checklists",
            "Journal reporting checklist / methods form",
            "ready_with_limitations",
            "materials/TOP_JOURNAL_REPORTING_SUMMARY.md; materials/TRANSPARENT_REPORTING_CHECKLIST.md; materials/EDITORIAL_SUBMISSION_CHECKLIST.md",
            "Transfer relevant rows into journal-specific reporting forms.",
            f"Editorial checklist status counts: {checklist['summary']['status_counts']}.",
            "Some fields remain limitation or author-input items.",
        ),
        portal_item(
            "claim_guardrails",
            "Internal final-claim review",
            "ready",
            "materials/CLAIM_EVIDENCE_MATRIX.md; materials/MANUSCRIPT_CLAIM_QA.md; materials/MANUSCRIPT_CROSS_REFERENCE_AUDIT.md",
            "Run claim QA after final manuscript formatting and before upload.",
            f"Claim QA status: {claim_qa['summary']['status']}, blockers: {claim_qa['summary']['blockers']}.",
            "Avoid oracle-as-controller, broad robustness, VLM, perception, or real-road claims.",
        ),
    ]

    author_actions = [
        {
            "action_id": "A1_target_journal",
            "owner": "authors",
            "priority": "required_before_upload",
            "action": "Choose target journal, article type, and template.",
            "evidence": "materials/COVER_LETTER_DRAFT_PACKAGE.md; manuscript/main.md",
        },
        {
            "action_id": "A2_final_manuscript",
            "owner": "authors",
            "priority": "required_before_upload",
            "action": "Convert Markdown draft to final journal source/PDF and rerun claim/cross-reference QA.",
            "evidence": "manuscript/main.md; materials/MANUSCRIPT_CLAIM_QA.md; materials/MANUSCRIPT_CROSS_REFERENCE_AUDIT.md",
        },
        {
            "action_id": "A3_external_archive",
            "owner": "authors",
            "priority": "required_before_upload_or_acceptance",
            "action": "Deposit the package in a public archive and update DOI/URL/accession fields.",
            "evidence": "materials/EXTERNAL_ARCHIVE_PREFLIGHT.md; materials/RELEASE_ARCHIVE_MANIFEST.md",
        },
        {
            "action_id": "A4_author_disclosures",
            "owner": "authors",
            "priority": "required_before_upload",
            "action": "Confirm affiliations, ORCIDs, contributions, competing interests, funding, and acknowledgements.",
            "evidence": "materials/SUBMISSION_METADATA_DRAFT.md",
        },
        {
            "action_id": "A5_reference_expansion",
            "owner": "authors",
            "priority": "recommended_before_review",
            "action": "Expand domain-specific related work before submission.",
            "evidence": "materials/REFERENCE_READINESS_AUDIT.md; manuscript/references.bib",
        },
    ]

    status_counts = {}
    for row in items:
        status_counts[row["status"]] = status_counts.get(row["status"], 0) + 1

    return {
        "root": str(root),
        "title": "Submission portal package map",
        "purpose": (
            "Map common journal submission portal upload fields to local evidence-package files, claim boundaries, "
            "and author-required completion actions."
        ),
        "portal_items": items,
        "author_actions": author_actions,
        "summary": {
            "portal_item_count": len(items),
            "status_counts": status_counts,
            "author_action_count": len(author_actions),
            "publication_verification_status": verification["summary"]["status"],
            "artifact_provenance": provenance_ratio,
            "data_dictionary_complete": dictionary["summary"]["complete"],
            "external_archive_pending": preflight["summary"]["external_archive_pending"],
            "manifest_primary_material_count": len(manifest.get("primary_materials", {})),
        },
        "interpretation": (
            "This map is a submission-portal planning aid. It does not certify final journal upload readiness, "
            "because target-journal formatting, author metadata, disclosures, and archive DOI/accession require author action."
        ),
    }


def write_portal_csv(report, path):
    fields = ["slot", "file_type", "status", "local_files", "author_action", "evidence_note", "boundary"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in report["portal_items"]:
            writer.writerow(row)


def write_actions_csv(report, path):
    fields = ["action_id", "owner", "priority", "action", "evidence"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in report["author_actions"]:
            writer.writerow(row)


def write_markdown(report, path):
    lines = [
        "# Submission Portal Package Map",
        "",
        report["purpose"],
        "",
        report["interpretation"],
        "",
        "## Summary",
        "",
        f"- Portal items: {report['summary']['portal_item_count']}",
        f"- Status counts: {report['summary']['status_counts']}",
        f"- Author actions: {report['summary']['author_action_count']}",
        f"- Publication verification: `{report['summary']['publication_verification_status']}`",
        f"- Artifact provenance: {report['summary']['artifact_provenance']}",
        f"- External archive pending: `{report['summary']['external_archive_pending']}`",
        "",
        "## Portal Items",
        "",
        "| slot | file type | status | local files | author action | boundary |",
        "|---|---|---|---|---|---|",
    ]
    for row in report["portal_items"]:
        lines.append(
            f"| {row['slot']} | {row['file_type']} | {row['status']} | `{row['local_files']}` | "
            f"{row['author_action']} | {row['boundary']} |"
        )
    lines.extend(
        [
            "",
            "## Author Actions",
            "",
            "| action | owner | priority | description | evidence |",
            "|---|---|---|---|---|",
        ]
    )
    for row in report["author_actions"]:
        lines.append(
            f"| {row['action_id']} | {row['owner']} | {row['priority']} | {row['action']} | `{row['evidence']}` |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export journal submission portal package map.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_map(root)
    out_json = materials / "SUBMISSION_PORTAL_PACKAGE_MAP.json"
    out_md = materials / "SUBMISSION_PORTAL_PACKAGE_MAP.md"
    out_csv = materials / "SUBMISSION_PORTAL_PACKAGE_MAP.csv"
    out_actions = materials / "SUBMISSION_PORTAL_AUTHOR_ACTIONS.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_portal_csv(report, out_csv)
    write_actions_csv(report, out_actions)
    print(
        json.dumps(
            {
                "json": str(out_json),
                "markdown": str(out_md),
                "portal_csv": str(out_csv),
                "actions_csv": str(out_actions),
                "status_counts": report["summary"]["status_counts"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
