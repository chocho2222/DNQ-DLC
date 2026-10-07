#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


EXCLUDED_OUTPUTS = [
    ("release_manifest", "materials/RELEASE_ARCHIVE_MANIFEST.md", "self_referential_manifest", "Markdown summary of the checksum manifest; excluded to avoid checksum recursion."),
    ("release_manifest", "materials/RELEASE_ARCHIVE_MANIFEST.json", "self_referential_manifest", "Machine-readable checksum manifest; excluded to avoid checksum recursion."),
    ("release_manifest", "materials/RELEASE_ARCHIVE_MANIFEST.csv", "self_referential_manifest", "Spreadsheet checksum manifest; excluded to avoid checksum recursion."),
    ("publication_verification", "materials/PUBLICATION_PACKAGE_VERIFICATION.md", "gate_report_updates_after_manifest", "Preflight gate report generated after release-manifest export."),
    ("publication_verification", "materials/PUBLICATION_PACKAGE_VERIFICATION.json", "gate_report_updates_after_manifest", "Machine-readable preflight gate report generated after release-manifest export."),
    ("publication_verification", "materials/PUBLICATION_PACKAGE_VERIFICATION.csv", "gate_report_updates_after_manifest", "CSV preflight gate report generated after release-manifest export."),
    ("publication_smoke_test", "materials/PUBLICATION_SMOKE_TEST.md", "gate_report_updates_after_manifest", "Smoke-test report generated after release-manifest export."),
    ("publication_smoke_test", "materials/PUBLICATION_SMOKE_TEST.json", "gate_report_updates_after_manifest", "Machine-readable smoke-test report generated after release-manifest export."),
    ("publication_smoke_test", "materials/PUBLICATION_SMOKE_TEST.csv", "gate_report_updates_after_manifest", "CSV smoke-test report generated after release-manifest export."),
    ("cross_material_consistency", "materials/CROSS_MATERIAL_CONSISTENCY_AUDIT.md", "audit_summarizes_manifest", "Cross-material consistency audit summarizes release-manifest counts and package gate statuses."),
    ("cross_material_consistency", "materials/CROSS_MATERIAL_CONSISTENCY_AUDIT.json", "audit_summarizes_manifest", "Machine-readable cross-material consistency audit summarizes release-manifest counts and package gate statuses."),
    ("cross_material_consistency", "materials/CROSS_MATERIAL_CONSISTENCY_AUDIT.csv", "audit_summarizes_manifest", "CSV cross-material consistency audit summarizes release-manifest counts and package gate statuses."),
    ("cross_report_freshness", "materials/CROSS_REPORT_FRESHNESS_AUDIT.md", "audit_summarizes_manifest", "Cross-report freshness audit summarizes release-manifest counts and package gate statuses."),
    ("cross_report_freshness", "materials/CROSS_REPORT_FRESHNESS_AUDIT.json", "audit_summarizes_manifest", "Machine-readable cross-report freshness audit summarizes release-manifest counts and package gate statuses."),
    ("cross_report_freshness", "materials/CROSS_REPORT_FRESHNESS_AUDIT.csv", "audit_summarizes_manifest", "CSV cross-report freshness audit summarizes release-manifest counts and package gate statuses."),
    ("submission_text_freshness", "materials/SUBMISSION_TEXT_FRESHNESS_AUDIT.md", "audit_summarizes_manifest", "Submission text freshness audit summarizes current provenance and gate snapshots after journal-facing text generation."),
    ("submission_text_freshness", "materials/SUBMISSION_TEXT_FRESHNESS_AUDIT.json", "audit_summarizes_manifest", "Machine-readable submission text freshness audit summarizes current provenance and gate snapshots after journal-facing text generation."),
    ("submission_text_freshness", "materials/SUBMISSION_TEXT_FRESHNESS_AUDIT.csv", "audit_summarizes_manifest", "CSV submission text freshness audit generated after journal-facing text generation."),
    ("local_author_readiness_separation", "materials/LOCAL_AUTHOR_READINESS_SEPARATION_AUDIT.md", "audit_summarizes_manifest", "Local author readiness separation audit summarizes local-vs-author readiness, gate status, smoke/freeze/provenance snapshots after package verification."),
    ("local_author_readiness_separation", "materials/LOCAL_AUTHOR_READINESS_SEPARATION_AUDIT.json", "audit_summarizes_manifest", "Machine-readable local author readiness separation audit summarizes local-vs-author readiness, gate status, smoke/freeze/provenance snapshots after package verification."),
    ("local_author_readiness_separation", "materials/LOCAL_AUTHOR_READINESS_SEPARATION_AUDIT.csv", "audit_summarizes_manifest", "CSV local author readiness separation audit generated after package verification."),
    ("stale_snapshot_boundary", "materials/STALE_SNAPSHOT_BOUNDARY_AUDIT.md", "audit_summarizes_manifest", "Stale snapshot boundary audit summarizes release-manifest counts, artifact-provenance ratios, and gate statuses."),
    ("stale_snapshot_boundary", "materials/STALE_SNAPSHOT_BOUNDARY_AUDIT.json", "audit_summarizes_manifest", "Machine-readable stale snapshot boundary audit summarizes release-manifest counts, artifact-provenance ratios, and gate statuses."),
    ("stale_snapshot_boundary", "materials/STALE_SNAPSHOT_BOUNDARY_AUDIT.csv", "audit_summarizes_manifest", "CSV stale snapshot boundary audit summarizes release-manifest counts, artifact-provenance ratios, and gate statuses."),
    ("narrative_numeric_consistency", "materials/NARRATIVE_NUMERIC_CONSISTENCY_AUDIT.md", "audit_summarizes_manifest", "Narrative numeric consistency audit summarizes release-manifest counts and package gate statuses."),
    ("narrative_numeric_consistency", "materials/NARRATIVE_NUMERIC_CONSISTENCY_AUDIT.json", "audit_summarizes_manifest", "Machine-readable narrative numeric consistency audit summarizes release-manifest counts and package gate statuses."),
    ("narrative_numeric_consistency", "materials/NARRATIVE_NUMERIC_CONSISTENCY_AUDIT.csv", "audit_summarizes_manifest", "CSV narrative numeric consistency audit summarizes release-manifest counts and package gate statuses."),
    ("script_snapshot_integrity", "materials/SCRIPT_SNAPSHOT_INTEGRITY_AUDIT.md", "audit_summarizes_manifest", "Script snapshot integrity audit summarizes registered scripts, release-manifest coverage, and package gate statuses."),
    ("script_snapshot_integrity", "materials/SCRIPT_SNAPSHOT_INTEGRITY_AUDIT.json", "audit_summarizes_manifest", "Machine-readable script snapshot integrity audit summarizes registered scripts, release-manifest coverage, and package gate statuses."),
    ("script_snapshot_integrity", "materials/SCRIPT_SNAPSHOT_INTEGRITY_AUDIT.csv", "audit_summarizes_manifest", "CSV script snapshot integrity audit summarizes registered scripts, release-manifest coverage, and package gate statuses."),
    ("script_snapshot_integrity", "materials/SCRIPT_SNAPSHOT_EXTRA_FILES.csv", "audit_summarizes_manifest", "Extra script snapshot list generated with the script snapshot integrity audit."),
    ("machine_readable_table_integrity", "materials/MACHINE_READABLE_TABLE_INTEGRITY_AUDIT.md", "audit_summarizes_manifest", "Machine-readable table integrity audit summarizes release-manifest coverage and package gate statuses."),
    ("machine_readable_table_integrity", "materials/MACHINE_READABLE_TABLE_INTEGRITY_AUDIT.json", "audit_summarizes_manifest", "Machine-readable table integrity audit summarizes release-manifest coverage and package gate statuses."),
    ("machine_readable_table_integrity", "materials/MACHINE_READABLE_TABLE_INTEGRITY_AUDIT.csv", "audit_summarizes_manifest", "CSV machine-readable table integrity audit summarizes release-manifest coverage and package gate statuses."),
    ("release_provenance_coverage", "materials/RELEASE_PROVENANCE_COVERAGE_AUDIT.md", "audit_summarizes_manifest", "Release provenance coverage audit summarizes release-manifest files and artifact-provenance roles."),
    ("release_provenance_coverage", "materials/RELEASE_PROVENANCE_COVERAGE_AUDIT.json", "audit_summarizes_manifest", "Machine-readable release provenance coverage audit summarizes release-manifest files and artifact-provenance roles."),
    ("release_provenance_coverage", "materials/RELEASE_PROVENANCE_COVERAGE_AUDIT.csv", "audit_summarizes_manifest", "CSV release provenance coverage audit summarizes release-manifest files and artifact-provenance roles."),
    ("checksum_freeze", "materials/FINAL_CHECKSUM_FREEZE_RECORD.md", "freeze_report_updates_after_manifest", "Archive-facing freeze record generated after release-manifest export."),
    ("checksum_freeze", "materials/FINAL_CHECKSUM_FREEZE_RECORD.json", "freeze_report_updates_after_manifest", "Machine-readable freeze record generated after release-manifest export."),
    ("checksum_freeze", "materials/FINAL_CHECKSUM_FREEZE_RECORD.csv", "freeze_report_updates_after_manifest", "CSV freeze checks generated after release-manifest export."),
    ("checksum_freeze", "materials/FINAL_CHECKSUM_FREEZE_FILE_SNAPSHOTS.csv", "freeze_report_updates_after_manifest", "Key-file snapshot table generated after release-manifest export."),
    ("fair_metadata", "materials/FAIR_ARCHIVE_METADATA.md", "metadata_summarizes_manifest", "FAIR metadata summarizes the release manifest and external archive status."),
    ("fair_metadata", "materials/FAIR_ARCHIVE_METADATA.json", "metadata_summarizes_manifest", "Machine-readable FAIR metadata summarizes the release manifest and external archive status."),
    ("fair_metadata", "materials/FAIR_ARCHIVE_METADATA.csv", "metadata_summarizes_manifest", "CSV FAIR metadata summarizes the release manifest and external archive status."),
    ("exclusion_audit", "materials/ARCHIVE_MANIFEST_EXCLUSION_AUDIT.md", "audit_summarizes_manifest", "Markdown audit explaining self-referential exclusions; excluded to avoid checksum recursion."),
    ("exclusion_audit", "materials/ARCHIVE_MANIFEST_EXCLUSION_AUDIT.json", "audit_summarizes_manifest", "Machine-readable audit explaining self-referential exclusions; excluded to avoid checksum recursion."),
    ("exclusion_audit", "materials/ARCHIVE_MANIFEST_EXCLUSION_AUDIT.csv", "audit_summarizes_manifest", "CSV audit explaining self-referential exclusions; excluded to avoid checksum recursion."),
    ("archive_preflight", "materials/EXTERNAL_ARCHIVE_PREFLIGHT.md", "entry_report_summarizes_manifest", "External archive preflight summarizes release-manifest status and author-required archive metadata."),
    ("archive_preflight", "materials/EXTERNAL_ARCHIVE_PREFLIGHT.json", "entry_report_summarizes_manifest", "Machine-readable external archive preflight summarizes release-manifest status and author-required archive metadata."),
    ("archive_preflight", "materials/EXTERNAL_ARCHIVE_PREFLIGHT_ROWS.csv", "entry_report_summarizes_manifest", "CSV external archive preflight rows generated after release-manifest export."),
    ("archive_preflight", "materials/EXTERNAL_ARCHIVE_KEY_FILES.csv", "entry_report_summarizes_manifest", "CSV external archive key-file rows generated after release-manifest export."),
    ("archive_readme", "materials/ARCHIVE_README.md", "entry_report_summarizes_manifest", "Archive README summarizes release-manifest status and key package reports."),
    ("archive_readme", "materials/ARCHIVE_README.json", "entry_report_summarizes_manifest", "Machine-readable archive README summarizes release-manifest status and key package reports."),
    ("archive_readme", "materials/ARCHIVE_README.csv", "entry_report_summarizes_manifest", "CSV archive README entry table generated after release-manifest export."),
    ("archive_size_budget", "materials/ARCHIVE_SIZE_BUDGET_REPORT.md", "entry_report_summarizes_manifest", "Archive size budget report summarizes release-manifest sizes and upload partitions."),
    ("archive_size_budget", "materials/ARCHIVE_SIZE_BUDGET_REPORT.json", "entry_report_summarizes_manifest", "Machine-readable archive size budget report summarizes release-manifest sizes and upload partitions."),
    ("archive_size_budget", "materials/ARCHIVE_SIZE_BUDGET_CATEGORIES.csv", "entry_report_summarizes_manifest", "CSV release-category size budget generated after release-manifest export."),
    ("archive_size_budget", "materials/ARCHIVE_SIZE_BUDGET_UPLOAD_PARTITIONS.csv", "entry_report_summarizes_manifest", "CSV upload-partition size budget generated after release-manifest export."),
    ("archive_size_budget", "materials/ARCHIVE_SIZE_BUDGET_LARGEST_FILES.csv", "entry_report_summarizes_manifest", "CSV largest-file size budget generated after release-manifest export."),
    ("archive_size_budget", "materials/ARCHIVE_SIZE_BUDGET_CHECKS.csv", "entry_report_summarizes_manifest", "CSV conservative upload budget checks generated after release-manifest export."),
    ("slim_submission_package", "materials/SLIM_SUBMISSION_PACKAGE_MANIFEST.md", "entry_report_summarizes_manifest", "Slim submission package manifest summarizes release-manifest sizes and journal-facing upload partitions."),
    ("slim_submission_package", "materials/SLIM_SUBMISSION_PACKAGE_MANIFEST.json", "entry_report_summarizes_manifest", "Machine-readable slim submission package manifest summarizes release-manifest sizes and journal-facing upload partitions."),
    ("slim_submission_package", "materials/SLIM_SUBMISSION_PACKAGE_FILES.csv", "entry_report_summarizes_manifest", "CSV slim journal-facing file list generated after release-manifest export."),
    ("slim_submission_package", "materials/SLIM_SUBMISSION_PACKAGE_ARCHIVE_ONLY.csv", "entry_report_summarizes_manifest", "CSV archive-only and large-file routing list generated after release-manifest export."),
    ("slim_submission_package", "materials/SLIM_SUBMISSION_PACKAGE_PARTITIONS.csv", "entry_report_summarizes_manifest", "CSV slim package partition summary generated after release-manifest export."),
    ("author_upload_decision_memo", "materials/AUTHOR_UPLOAD_DECISION_MEMO.md", "entry_report_summarizes_manifest", "Author upload decision memo summarizes release-manifest, size-budget, dashboard, and author-action status."),
    ("author_upload_decision_memo", "materials/AUTHOR_UPLOAD_DECISION_MEMO.json", "entry_report_summarizes_manifest", "Machine-readable author upload decision memo summarizes release-manifest, size-budget, dashboard, and author-action status."),
    ("author_upload_decision_memo", "materials/AUTHOR_UPLOAD_DECISION_MEMO.csv", "entry_report_summarizes_manifest", "CSV author upload decision memo generated after release-manifest export."),
    ("final_author_handoff_checklist", "materials/FINAL_AUTHOR_HANDOFF_CHECKLIST.md", "entry_report_summarizes_manifest", "Final author handoff checklist summarizes dashboard, smoke-test, freeze, and author-action status."),
    ("final_author_handoff_checklist", "materials/FINAL_AUTHOR_HANDOFF_CHECKLIST.json", "entry_report_summarizes_manifest", "Machine-readable final author handoff checklist summarizes dashboard, smoke-test, freeze, and author-action status."),
    ("final_author_handoff_checklist", "materials/FINAL_AUTHOR_HANDOFF_CHECKLIST.csv", "entry_report_summarizes_manifest", "CSV final author handoff checklist generated after dashboard and smoke-test status changes."),
    ("submission_bundle", "materials/FINAL_SUBMISSION_FILE_BUNDLE.md", "entry_report_summarizes_manifest", "Final submission bundle summarizes release-manifest, smoke-test, and author-action status."),
    ("submission_bundle", "materials/FINAL_SUBMISSION_FILE_BUNDLE.json", "entry_report_summarizes_manifest", "Machine-readable final submission bundle summarizes release-manifest, smoke-test, and author-action status."),
    ("submission_bundle", "materials/FINAL_SUBMISSION_FILE_BUNDLE.csv", "entry_report_summarizes_manifest", "CSV final submission bundle generated after release-manifest export."),
    ("citation_metadata", "materials/CITATION_METADATA.md", "metadata_summarizes_manifest", "Citation metadata summarizes release-file counts and archive status."),
    ("citation_metadata", "materials/CITATION_METADATA.json", "metadata_summarizes_manifest", "Machine-readable citation metadata summarizes release-file counts and archive status."),
    ("citation_metadata", "materials/CITATION_METADATA.csv", "metadata_summarizes_manifest", "CSV citation metadata summarizes release-file counts and archive status."),
    ("citation_metadata", "materials/CITATION.cff", "metadata_summarizes_manifest", "CFF citation file generated from citation metadata and external archive status."),
    ("citation_metadata", "materials/CITATION.bib", "metadata_summarizes_manifest", "BibTeX citation file generated from citation metadata and external archive status."),
    ("submission_dashboard", "materials/SUBMISSION_READINESS_DASHBOARD.md", "entry_report_summarizes_manifest", "Submission readiness dashboard summarizes release, smoke-test, and reviewer-navigation status."),
    ("submission_dashboard", "materials/SUBMISSION_READINESS_DASHBOARD.json", "entry_report_summarizes_manifest", "Machine-readable submission readiness dashboard summarizes release, smoke-test, and reviewer-navigation status."),
    ("submission_dashboard", "materials/SUBMISSION_READINESS_DASHBOARD.csv", "entry_report_summarizes_manifest", "CSV submission readiness dashboard summarizes release, smoke-test, and reviewer-navigation status."),
    ("reporting_navigator", "materials/REPORTING_SUPPLEMENT_NAVIGATOR.md", "entry_report_summarizes_manifest", "Reporting supplement navigator summarizes freeze, dashboard, citation, and supplement status."),
    ("reporting_navigator", "materials/REPORTING_SUPPLEMENT_NAVIGATOR.json", "entry_report_summarizes_manifest", "Machine-readable reporting supplement navigator summarizes freeze, dashboard, citation, and supplement status."),
    ("reporting_navigator", "materials/REPORTING_SUPPLEMENT_NAVIGATOR.csv", "entry_report_summarizes_manifest", "CSV reporting supplement navigator summarizes freeze, dashboard, citation, and supplement status."),
    ("upload_plan", "materials/SUBMISSION_UPLOAD_SELECTION_PLAN.md", "entry_report_summarizes_manifest", "Submission upload plan summarizes final bundle, dashboard, verification, and release-manifest status."),
    ("upload_plan", "materials/SUBMISSION_UPLOAD_SELECTION_PLAN.json", "entry_report_summarizes_manifest", "Machine-readable submission upload plan summarizes final bundle, dashboard, verification, and release-manifest status."),
    ("upload_plan", "materials/SUBMISSION_UPLOAD_SELECTION_PLAN.csv", "entry_report_summarizes_manifest", "CSV submission upload plan summarizes final bundle, dashboard, verification, and release-manifest status."),
    ("archive_upload_readiness", "materials/ARCHIVE_UPLOAD_READINESS_MATRIX.md", "entry_report_summarizes_manifest", "Archive/upload readiness matrix summarizes release-manifest, verification, smoke-test, and external-archive status."),
    ("archive_upload_readiness", "materials/ARCHIVE_UPLOAD_READINESS_MATRIX.json", "entry_report_summarizes_manifest", "Machine-readable archive/upload readiness matrix summarizes release-manifest, verification, smoke-test, and external-archive status."),
    ("archive_upload_readiness", "materials/ARCHIVE_UPLOAD_READINESS_MATRIX.csv", "entry_report_summarizes_manifest", "CSV archive/upload readiness matrix summarizes release-manifest, verification, smoke-test, and external-archive status."),
    ("reporting_summary", "materials/TOP_JOURNAL_REPORTING_SUMMARY.md", "entry_report_summarizes_manifest", "Top-journal reporting summary includes release-manifest counts and archive-pending status."),
    ("reporting_summary", "materials/TOP_JOURNAL_REPORTING_SUMMARY.json", "entry_report_summarizes_manifest", "Machine-readable top-journal reporting summary includes release-manifest counts and archive-pending status."),
    ("reporting_summary", "materials/TOP_JOURNAL_REPORTING_SUMMARY.csv", "entry_report_summarizes_manifest", "CSV top-journal reporting summary includes release-manifest counts and archive-pending status."),
    ("portal_map", "materials/SUBMISSION_PORTAL_PACKAGE_MAP.md", "entry_report_summarizes_manifest", "Submission portal package map includes release-manifest counts and archive-upload status."),
    ("portal_map", "materials/SUBMISSION_PORTAL_PACKAGE_MAP.json", "entry_report_summarizes_manifest", "Machine-readable submission portal package map includes release-manifest counts and archive-upload status."),
    ("portal_map", "materials/SUBMISSION_PORTAL_PACKAGE_MAP.csv", "entry_report_summarizes_manifest", "CSV submission portal package map includes release-manifest counts and archive-upload status."),
    ("editorial_checklist", "materials/EDITORIAL_SUBMISSION_CHECKLIST.md", "entry_report_summarizes_manifest", "Editorial submission checklist includes release-manifest counts and author-owned archive actions."),
    ("editorial_checklist", "materials/EDITORIAL_SUBMISSION_CHECKLIST.json", "entry_report_summarizes_manifest", "Machine-readable editorial submission checklist includes release-manifest counts and author-owned archive actions."),
    ("editorial_checklist", "materials/EDITORIAL_SUBMISSION_CHECKLIST.csv", "entry_report_summarizes_manifest", "CSV editorial submission checklist includes release-manifest counts and author-owned archive actions."),
    ("editorial_triage", "materials/EDITORIAL_TRIAGE_AND_REVIEWER_CHECKLIST.md", "entry_report_summarizes_manifest", "Editorial triage and reviewer checklist summarizes dependency-map release coverage and archive status."),
    ("editorial_triage", "materials/EDITORIAL_TRIAGE_AND_REVIEWER_CHECKLIST.json", "entry_report_summarizes_manifest", "Machine-readable editorial triage and reviewer checklist summarizes dependency-map release coverage and archive status."),
    ("editorial_triage", "materials/EDITORIAL_TRIAGE_AND_REVIEWER_CHECKLIST.csv", "entry_report_summarizes_manifest", "CSV editorial triage and reviewer checklist summarizes dependency-map release coverage and archive status."),
    ("target_journal_matrix", "materials/TARGET_JOURNAL_COMPLIANCE_MATRIX.md", "entry_report_summarizes_manifest", "Target-journal compliance matrix includes release-manifest counts and archive-pending status."),
    ("target_journal_matrix", "materials/TARGET_JOURNAL_COMPLIANCE_MATRIX.json", "entry_report_summarizes_manifest", "Machine-readable target-journal compliance matrix includes release-manifest counts and archive-pending status."),
    ("target_journal_matrix", "materials/TARGET_JOURNAL_COMPLIANCE_MATRIX.csv", "entry_report_summarizes_manifest", "CSV target-journal compliance matrix includes release-manifest counts and archive-pending status."),
    ("reviewer_risk_dossier", "materials/REVIEWER_RISK_RESPONSE_DOSSIER.md", "entry_report_summarizes_manifest", "Reviewer risk-response dossier includes release-manifest counts in reproducibility response wording."),
    ("reviewer_risk_dossier", "materials/REVIEWER_RISK_RESPONSE_DOSSIER.json", "entry_report_summarizes_manifest", "Machine-readable reviewer risk-response dossier includes release-manifest counts in reproducibility response wording."),
    ("reviewer_risk_dossier", "materials/REVIEWER_RISK_RESPONSE_DOSSIER.csv", "entry_report_summarizes_manifest", "CSV reviewer risk-response dossier includes release-manifest counts in reproducibility response wording."),
    ("license_audit", "materials/SOFTWARE_DEPENDENCY_LICENSE_AUDIT.md", "entry_report_summarizes_manifest", "Software dependency/license audit includes release-manifest checksum counts."),
    ("license_audit", "materials/SOFTWARE_DEPENDENCY_LICENSE_AUDIT.json", "entry_report_summarizes_manifest", "Machine-readable software dependency/license audit includes release-manifest checksum counts."),
    ("license_audit", "materials/SOFTWARE_DEPENDENCY_LICENSE_AUDIT.csv", "entry_report_summarizes_manifest", "CSV software dependency/license audit includes release-manifest checksum counts."),
    ("artifact_dependency_map", "materials/ARTIFACT_DEPENDENCY_MAP.md", "entry_report_summarizes_manifest", "Artifact dependency map includes release-manifest counts and missing-release-output summaries."),
    ("artifact_dependency_map", "materials/ARTIFACT_DEPENDENCY_MAP.json", "entry_report_summarizes_manifest", "Machine-readable artifact dependency map includes release-manifest counts and missing-release-output summaries."),
    ("artifact_dependency_map", "materials/ARTIFACT_DEPENDENCY_MAP.csv", "entry_report_summarizes_manifest", "CSV artifact dependency map includes release-manifest counts and missing-release-output summaries."),
]


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_report(root):
    release = load_json(root / "materials" / "RELEASE_ARCHIVE_MANIFEST.json")
    freeze = load_json(root / "materials" / "FINAL_CHECKSUM_FREEZE_RECORD.json")
    smoke = load_json(root / "materials" / "PUBLICATION_SMOKE_TEST.json")
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    release_paths = {row["path"] for row in release["files"]}

    rows = []
    for group, rel_path, reason, note in EXCLUDED_OUTPUTS:
        path = root / rel_path
        exists = path.exists()
        in_release_manifest = rel_path in release_paths
        status = "pass" if exists and not in_release_manifest else "review_required"
        rows.append(
            {
                "group": group,
                "path": rel_path,
                "exists": exists,
                "in_release_manifest": in_release_manifest,
                "reason": reason,
                "status": status,
                "note": note,
            }
        )

    review_required = [row for row in rows if row["status"] != "pass"]
    return {
        "root": str(root),
        "title": "Archive manifest exclusion audit",
        "purpose": (
            "Document why self-referential manifest, gate, smoke, freeze, FAIR metadata, exclusion-audit, cross-report freshness audit, citation/readiness/reporting/upload-plan metadata, editor/reviewer navigation reports, and entry-point outputs are "
            "kept in the package but excluded from the release-manifest checksum set."
        ),
        "rows": rows,
        "summary": {
            "status": "pass" if not review_required else "review_required",
            "excluded_file_count": len(rows),
            "excluded_existing_count": sum(1 for row in rows if row["exists"]),
            "unexpected_in_release_count": sum(1 for row in rows if row["in_release_manifest"]),
            "review_required_count": len(review_required),
            "release_file_count": release["summary"]["file_count"],
            "release_size_reference": "materials/RELEASE_ARCHIVE_MANIFEST.json",
            "freeze_status": freeze["summary"]["status"],
            "freeze_release_file_count": freeze["summary"]["release_file_count"],
            "freeze_release_size_reference": "materials/FINAL_CHECKSUM_FREEZE_RECORD.json",
            "publication_smoke_test_reference": "materials/PUBLICATION_SMOKE_TEST.json",
            "publication_smoke_test_failed_checks": smoke["summary"]["failed_checks"],
            "publication_verification_status": verification["summary"]["status"],
            "publication_verification_failed_gates": verification["summary"]["failed_gates"],
        },
        "interpretation": (
            "Excluded outputs are still distributed in the local package and remain reviewer-facing. "
            "They are excluded only from the SHA256-locked release-manifest file list because they are "
            "generated after, or summarize, the release manifest itself. Stable scientific evidence files "
            "remain covered by the release manifest and by the smoke-test SHA256 gate."
        ),
    }


def write_csv(report, path):
    fields = ["group", "path", "exists", "in_release_manifest", "reason", "status", "note"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in report["rows"]:
            writer.writerow(row)


def write_markdown(report, path):
    lines = [
        "# Archive Manifest Exclusion Audit",
        "",
        report["purpose"],
        "",
        report["interpretation"],
        "",
        "## Summary",
        "",
    ]
    for key, value in report["summary"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(
        [
            "",
            "## Excluded Files",
            "",
            "| group | path | exists | in release manifest | reason | status | note |",
            "|---|---|---:|---:|---|---|---|",
        ]
    )
    for row in report["rows"]:
        lines.append(
            f"| {row['group']} | `{row['path']}` | {row['exists']} | {row['in_release_manifest']} | "
            f"{row['reason']} | {row['status']} | {row['note']} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export archive manifest exclusion audit.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_report(root)
    out_json = materials / "ARCHIVE_MANIFEST_EXCLUSION_AUDIT.json"
    out_md = materials / "ARCHIVE_MANIFEST_EXCLUSION_AUDIT.md"
    out_csv = materials / "ARCHIVE_MANIFEST_EXCLUSION_AUDIT.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv), "summary": report["summary"]}, indent=2))


if __name__ == "__main__":
    main()
