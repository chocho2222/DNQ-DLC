#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def plan_row(
    row_id,
    category,
    priority,
    owner,
    action,
    evidence,
    acceptance_criteria,
    rerun_after_completion,
    blocker_if_missing,
    source,
):
    return {
        "id": row_id,
        "category": category,
        "priority": priority,
        "owner": owner,
        "action": action,
        "evidence": evidence,
        "acceptance_criteria": acceptance_criteria,
        "rerun_after_completion": rerun_after_completion,
        "blocker_if_missing": blocker_if_missing,
        "source": source,
    }


def build_plan(root):
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    provenance = load_json(root / "tables" / "artifact_provenance.json")
    portal = load_json(root / "materials" / "SUBMISSION_PORTAL_PACKAGE_MAP.json")
    metadata = load_json(root / "materials" / "SUBMISSION_METADATA_DRAFT.json")
    archive = load_json(root / "materials" / "EXTERNAL_ARCHIVE_PREFLIGHT.json")
    journal = load_json(root / "materials" / "TARGET_JOURNAL_COMPLIANCE_MATRIX.json")
    dashboard = load_json(root / "materials" / "SUBMISSION_READINESS_DASHBOARD.json")
    references = load_json(root / "materials" / "REFERENCE_READINESS_AUDIT.json")

    provenance_label = f"{provenance['complete_count']}/{len(provenance['artifacts'])}"
    reference_gap_count = references["summary"]["topic_needs_author_completion_count"]
    reference_action = (
        "Final-author review of related-work breadth and target-journal citation style."
        if reference_gap_count == 0
        else "Expand recent domain-specific related work and update manuscript/references.bib."
    )
    reference_priority = "recommended_before_upload_author_review" if reference_gap_count == 0 else "required_before_upload"
    reference_blocker = reference_gap_count > 0

    rows = [
        plan_row(
            "AF1_target_journal_template",
            "journal_format",
            "required_before_upload",
            "authors",
            "Choose target journal, article type, and official template; convert manuscript/main.md into final source/PDF.",
            "materials/SUBMISSION_PORTAL_PACKAGE_MAP.md; materials/TARGET_JOURNAL_COMPLIANCE_MATRIX.md; manuscript/main.md",
            "Target journal, article type, template, manuscript source, and PDF are fixed and stored in the package or external submission workspace.",
            "scripts/export_manuscript_cross_reference_audit.py; scripts/export_manuscript_claim_qa.py; scripts/export_submission_readiness_dashboard.py",
            True,
            "submission_portal; target_journal_compliance",
        ),
        plan_row(
            "AF2_external_archive_doi",
            "archive",
            "required_before_upload_or_revision",
            "authors",
            "Deposit the package in an approved repository and update DOI/URL/accession fields.",
            "materials/EXTERNAL_ARCHIVE_PREFLIGHT.md; materials/FAIR_ARCHIVE_METADATA.md; materials/RELEASE_ARCHIVE_MANIFEST.md",
            "External DOI/URL/accession is present in availability, FAIR metadata, and journal data-availability text.",
            "scripts/export_release_archive_manifest.py; scripts/export_fair_archive_metadata.py; scripts/export_data_code_availability.py; scripts/export_target_journal_compliance_matrix.py",
            True,
            "external_archive_preflight; target_journal_compliance",
        ),
        plan_row(
            "AF3_author_identity_orcid",
            "author_metadata",
            "required_before_upload",
            "authors",
            "Complete author names, affiliations, ORCID IDs, emails, and corresponding-author designation.",
            "materials/SUBMISSION_METADATA_DRAFT.md; materials/SUBMISSION_METADATA_AUTHORS.csv",
            "All author rows have non-empty affiliation/contact fields where required by the target journal.",
            "scripts/export_submission_metadata_draft.py; scripts/export_submission_portal_package_map.py; scripts/export_submission_readiness_dashboard.py",
            True,
            "submission_metadata",
        ),
        plan_row(
            "AF4_credit_contributions",
            "author_metadata",
            "required_before_upload",
            "authors",
            "Assign CRediT roles and author contributions.",
            "materials/SUBMISSION_METADATA_DRAFT.md; materials/SUBMISSION_METADATA_CREDIT.csv",
            "All relevant CRediT rows are author-certified and consistent with the manuscript contribution statement.",
            "scripts/export_submission_metadata_draft.py; scripts/export_editorial_submission_checklist.py",
            True,
            "submission_metadata",
        ),
        plan_row(
            "AF5_disclosures_funding_ethics",
            "declarations",
            "required_before_upload",
            "authors",
            "Confirm competing interests, funding, acknowledgements, ethics/safety wording, and institutional declarations.",
            "materials/SUBMISSION_METADATA_DRAFT.md; materials/RESEARCH_RISK_AND_SAFETY.md; materials/SIMULATION_TO_REAL_APPLICABILITY.md",
            "All disclosure rows are author-certified and target-journal form fields are complete.",
            "scripts/export_submission_metadata_draft.py; scripts/export_research_risk_and_safety_statement.py; scripts/export_submission_readiness_dashboard.py",
            True,
            "submission_metadata; research_risk",
        ),
        plan_row(
            "AF6_related_work_expansion",
            "manuscript_content",
            reference_priority,
            "authors",
            reference_action,
            "materials/REFERENCE_READINESS_AUDIT.md; materials/RELATED_WORK_POSITIONING_MATRIX.md; manuscript/references.bib; materials/TARGET_JOURNAL_COMPLIANCE_MATRIX.md",
            "Reference readiness topics have no author-completion gaps and final manuscript citations match references.bib.",
            "scripts/export_reference_readiness_audit.py; scripts/export_manuscript_cross_reference_audit.py; scripts/export_reviewer_risk_response_dossier.py",
            reference_blocker,
            "reference_readiness; target_journal_compliance",
        ),
        plan_row(
            "AF7_source_data_upload_pack",
            "source_data",
            "required_before_upload_if_requested",
            "authors",
            "Prepare figure source-data files and supplementary table uploads in target-journal naming conventions.",
            "materials/FIGURE_SOURCE_DATA_AUDIT.md; figures/*_source_data.csv; materials/DATA_DICTIONARY.md",
            "All requested figure source-data and supplementary tables are named for the target journal and traceable to local evidence.",
            "scripts/export_figure_source_data_audit.py; scripts/export_data_dictionary.py; scripts/export_submission_readiness_dashboard.py",
            False,
            "figure_source_data; data_dictionary",
        ),
        plan_row(
            "AF8_claim_and_boundary_final_pass",
            "claim_control",
            "required_after_final_text",
            "authors",
            "Rerun claim QA after final manuscript, abstract, cover letter, and highlights are edited.",
            "materials/MANUSCRIPT_CLAIM_QA.md; materials/CLAIM_EVIDENCE_MATRIX.md; materials/TITLE_ABSTRACT_HIGHLIGHTS_PACKAGE.md",
            "Claim QA remains pass; no final text claims real-road, VLM, safety certification, oracle-as-controller, or broad robustness.",
            "scripts/export_manuscript_claim_qa.py; scripts/export_title_abstract_highlights_package.py; scripts/export_publication_package_verification.py",
            True,
            "claim_qa",
        ),
        plan_row(
            "AF9_final_checksum_freeze",
            "release_freeze",
            "required_after_all_edits",
            "authors",
            "Freeze the package after final edits and regenerate checksums, manifest, verification, and dashboard.",
            "materials/RELEASE_ARCHIVE_MANIFEST.md; materials/PUBLICATION_PACKAGE_VERIFICATION.md; materials/SUBMISSION_READINESS_DASHBOARD.md",
            "Release manifest, publication verification, statistical consistency, dependency map, and dashboard are pass with no stale status scan hits.",
            "scripts/export_release_archive_manifest.py; scripts/export_publication_package_verification.py; scripts/export_statistical_consistency_audit.py; scripts/export_artifact_dependency_map.py; scripts/export_submission_readiness_dashboard.py",
            True,
            "release_manifest; publication_verification",
        ),
        plan_row(
            "AF10_cover_letter_and_portal_copy",
            "submission_text",
            "required_before_upload",
            "authors",
            "Adapt cover letter, significance wording, title, abstract, highlights, and portal fields to the selected journal.",
            "materials/COVER_LETTER_DRAFT_PACKAGE.md; materials/SIGNIFICANCE_BRIEFING.md; materials/TITLE_ABSTRACT_HIGHLIGHTS_PACKAGE.md; materials/SUBMISSION_PORTAL_PACKAGE_MAP.md",
            "All journal portal fields are complete and wording remains evidence-bound.",
            "scripts/export_cover_letter_draft_package.py; scripts/export_title_abstract_highlights_package.py; scripts/export_submission_portal_package_map.py",
            True,
            "cover_letter; submission_portal",
        ),
    ]

    source_counts = {
        "portal_author_actions": len(portal["author_actions"]),
        "metadata_author_required": metadata["summary"]["author_required_count"],
        "archive_author_required": archive["summary"]["author_required_count"],
        "journal_author_action": journal["summary"]["author_action_count"],
        "reference_topics_needing_author_completion": references["summary"]["topic_needs_author_completion_count"],
        "dashboard_author_action_rows": dashboard["summary"]["author_action_row_count"],
    }
    priority_counts = {}
    for item in rows:
        priority_counts[item["priority"]] = priority_counts.get(item["priority"], 0) + 1

    return {
        "root": str(root),
        "title": "Author action and submission freeze plan",
        "purpose": (
            "Consolidate author-owned tasks required to move the local evidence package from preflight-ready "
            "to target-journal upload-ready."
        ),
        "rows": rows,
        "summary": {
            "row_count": len(rows),
            "blocker_count": sum(1 for item in rows if item["blocker_if_missing"]),
            "priority_counts": priority_counts,
            "source_counts": source_counts,
            "publication_verification_status": verification["summary"]["status"],
            "artifact_provenance": provenance_label,
            "external_archive_pending": archive["summary"]["external_archive_pending"],
        },
        "interpretation": (
            "This plan distinguishes local package readiness from author-certified submission readiness. "
            "Rows marked as blockers require author action outside local automation."
        ),
    }


def write_csv(report, path):
    fields = [
        "id",
        "category",
        "priority",
        "owner",
        "action",
        "evidence",
        "acceptance_criteria",
        "rerun_after_completion",
        "blocker_if_missing",
        "source",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in report["rows"]:
            writer.writerow(item)


def write_markdown(report, path):
    lines = [
        "# Author Action And Submission Freeze Plan",
        "",
        report["purpose"],
        "",
        report["interpretation"],
        "",
        "## Summary",
        "",
        f"- Rows: {report['summary']['row_count']}",
        f"- Blockers if missing: {report['summary']['blocker_count']}",
        f"- Publication verification: `{report['summary']['publication_verification_status']}`",
        f"- Artifact provenance: {report['summary']['artifact_provenance']}",
        f"- External archive pending: `{report['summary']['external_archive_pending']}`",
        "",
        "## Source Counts",
        "",
        "| source | count |",
        "|---|---:|",
    ]
    for key, value in report["summary"]["source_counts"].items():
        lines.append(f"| {key} | {value} |")
    lines.extend(
        [
            "",
            "## Action Rows",
            "",
            "| id | category | priority | owner | blocker | action | evidence | acceptance criteria | rerun after completion |",
            "|---|---|---|---|---|---|---|---|---|",
        ]
    )
    for item in report["rows"]:
        lines.append(
            f"| {item['id']} | {item['category']} | {item['priority']} | {item['owner']} | "
            f"{item['blocker_if_missing']} | {item['action']} | `{item['evidence']}` | "
            f"{item['acceptance_criteria']} | `{item['rerun_after_completion']}` |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export author action and submission freeze plan.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_plan(root)
    out_json = materials / "AUTHOR_ACTION_FREEZE_PLAN.json"
    out_md = materials / "AUTHOR_ACTION_FREEZE_PLAN.md"
    out_csv = materials / "AUTHOR_ACTION_FREEZE_PLAN.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv), "summary": report["summary"]}, indent=2))


if __name__ == "__main__":
    main()
