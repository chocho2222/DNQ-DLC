#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def row(gap_id, section, status, local_evidence, author_action, closure_test, boundary, note):
    return {
        "gap_id": gap_id,
        "section": section,
        "status": status,
        "local_evidence": local_evidence,
        "author_action": author_action,
        "closure_test": closure_test,
        "boundary": boundary,
        "note": note,
    }


def build_report(root):
    materials = root / "materials"
    verification = load_json(materials / "PUBLICATION_PACKAGE_VERIFICATION.json")
    smoke = load_json(materials / "PUBLICATION_SMOKE_TEST.json")
    provenance = load_json(root / "tables" / "artifact_provenance.json")
    release = load_json(materials / "RELEASE_ARCHIVE_MANIFEST.json")
    final_bundle = load_json(materials / "FINAL_SUBMISSION_FILE_BUNDLE.json")
    upload_plan = load_json(materials / "SUBMISSION_UPLOAD_SELECTION_PLAN.json")
    portal_fields = load_json(materials / "SUBMISSION_PORTAL_FIELD_COMPLETION_PACK.json")
    freeze_plan = load_json(materials / "AUTHOR_ACTION_FREEZE_PLAN.json")
    handoff = load_json(materials / "FINAL_AUTHOR_HANDOFF_CHECKLIST.json")
    archive_upload = load_json(materials / "ARCHIVE_UPLOAD_READINESS_MATRIX.json")
    supplement_decision = load_json(materials / "SUPPLEMENT_UPLOAD_DECISION_MATRIX.json")
    slim = load_json(materials / "SLIM_SUBMISSION_PACKAGE_MANIFEST.json")
    dashboard = load_json(materials / "SUBMISSION_READINESS_DASHBOARD.json")
    journal = load_json(materials / "TARGET_JOURNAL_COMPLIANCE_MATRIX.json")
    citation = load_json(materials / "CITATION_METADATA.json")
    fair = load_json(materials / "FAIR_ARCHIVE_METADATA.json")
    ethics = load_json(materials / "ETHICS_DISCLOSURE_READINESS_PACK.json")
    author_integrity = load_json(materials / "AUTHOR_OWNED_SUBMISSION_INTEGRITY_AUDIT.json")
    blockers = load_json(materials / "REMAINING_AUTHOR_BLOCKERS_MATRIX.json")
    reviewer_preflight = load_json(materials / "REVIEWER_COMMAND_PREFLIGHT.json")

    provenance_ratio = f"{provenance['complete_count']}/{len(provenance['artifacts'])}"
    current_release_count = release["summary"]["file_count"]
    fair_identifier_pending = fair.get("availability", {}).get("external_archive_pending")
    if fair_identifier_pending is None:
        fair_identifier_pending = not (
            fair.get("identifier", {}).get("external_doi") or fair.get("identifier", {}).get("external_url")
        )
    stale_release_fields = []
    stale_provenance_fields = []
    for name, data in [
        ("final_bundle", final_bundle),
        ("upload_plan", upload_plan),
        ("archive_upload", archive_upload),
        ("supplement_decision", supplement_decision),
        ("slim_submission_package", slim),
        ("dashboard", dashboard),
        ("freeze_plan", freeze_plan),
        ("portal_fields", portal_fields),
    ]:
        summary = data.get("summary", {})
        if "release_file_count" in summary and summary["release_file_count"] != current_release_count:
            stale_release_fields.append(
                f"{name}.summary.release_file_count={summary['release_file_count']} expected {current_release_count}"
            )
        if "artifact_provenance" in summary and summary["artifact_provenance"] != provenance_ratio:
            stale_provenance_fields.append(
                f"{name}.summary.artifact_provenance={summary['artifact_provenance']} expected {provenance_ratio}"
            )

    rows = [
        row(
            "AUG01_local_package_gates",
            "local_package",
            "pass" if verification["summary"]["status"] == "pass" else "review_required",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.md; materials/PUBLICATION_SMOKE_TEST.md",
            "Rerun the gate commands after any final file, figure, table, or manuscript edit.",
            "Publication verification passes; the smoke-test status is recorded as context and rerun at the end of the package build.",
            "Local gates do not imply journal acceptance, public archive deposition, or author certification. The smoke test remains the final independent gate.",
            f"verification={verification['summary']['status']}; smoke={smoke['summary']['status']}",
        ),
        row(
            "AUG02_artifact_and_release_freeze",
            "local_package",
            "pass" if provenance["complete_count"] == len(provenance["artifacts"]) else "review_required",
            "tables/artifact_provenance.md; materials/RELEASE_ARCHIVE_MANIFEST.md",
            "Regenerate release manifest and checksum freeze after the final author-selected upload subset is fixed.",
            "Artifact provenance is complete and release manifest has a current file count and byte count.",
            "Checksums are local until a repository DOI/accession is assigned.",
            (
                f"artifact_provenance={provenance_ratio}; release_file_count={current_release_count}; "
                "release_size_reference=materials/RELEASE_ARCHIVE_MANIFEST.json"
            ),
        ),
        row(
            "AUG03_cross_entry_snapshot_alignment",
            "local_package",
            "pass" if not stale_release_fields and not stale_provenance_fields else "review_required",
            "materials/FINAL_SUBMISSION_FILE_BUNDLE.md; materials/SUBMISSION_UPLOAD_SELECTION_PLAN.md; materials/ARCHIVE_UPLOAD_READINESS_MATRIX.md; materials/SUPPLEMENT_UPLOAD_DECISION_MATRIX.md",
            "Refresh any listed entry material before author handoff or public archive upload.",
            "Submission-facing entry materials report the current provenance ratio and release-manifest count.",
            "Historical or self-referential stale snapshots may remain in dedicated stale-snapshot audits; this row targets active upload entry points.",
            "; ".join(stale_release_fields + stale_provenance_fields) or "active entry summaries aligned",
        ),
        row(
            "AUG04_required_file_bundle",
            "file_upload",
            "pass" if final_bundle["summary"]["missing_required_count"] == 0 else "review_required",
            "materials/FINAL_SUBMISSION_FILE_BUNDLE.md",
            "Use this bundle after choosing the target journal and before assembling the portal upload.",
            "No required local file rows are missing.",
            "The bundle map is not a journal receipt and does not decide optional journal-dependent files.",
            (
                f"file_rows={final_bundle['summary']['file_row_count']}; "
                f"missing_required={final_bundle['summary']['missing_required_count']}; "
                f"author_selection_required={final_bundle['summary']['author_selection_required_count']}"
            ),
        ),
        row(
            "AUG05_upload_selection_boundary",
            "file_upload",
            "author_action_required" if upload_plan["summary"]["author_selection_required_count"] else "pass",
            "materials/SUBMISSION_UPLOAD_SELECTION_PLAN.md; materials/SUPPLEMENT_UPLOAD_DECISION_MATRIX.md; materials/SLIM_SUBMISSION_PACKAGE_MANIFEST.md",
            "Choose optional or journal-dependent supplement/reviewer-support files after the target journal is fixed.",
            "Required upload and archive files are separated from optional author-selected files.",
            "Selection rows are operational routing decisions, not new evidence or claim expansion.",
            (
                f"upload_author_selection={upload_plan['summary']['author_selection_required_count']}; "
                f"supplement_author_selection={supplement_decision['summary']['author_selection_required_count']}; "
                f"slim_files={slim['summary']['slim_file_count']}; "
                "slim_size_reference=materials/SLIM_SUBMISSION_PACKAGE_MANIFEST.json"
            ),
        ),
        row(
            "AUG06_portal_field_completion",
            "journal_portal",
            portal_fields["summary"]["status"],
            "materials/SUBMISSION_PORTAL_FIELD_COMPLETION_PACK.md",
            "Fill author-required fields and archive-dependent fields in the selected journal portal.",
            "Copy-ready fields, archive-dependent fields, and author-required fields are explicitly separated.",
            "Automation does not certify conflicts, funding, affiliations, ORCID, contributions, or archive identifiers.",
            (
                f"fields={portal_fields['summary']['field_count']}; "
                f"copy_ready={portal_fields['summary']['copy_ready_count']}; "
                f"archive_dependent={portal_fields['summary']['copy_after_archive_count']}; "
                f"author_required={portal_fields['summary']['author_required_count']}"
            ),
        ),
        row(
            "AUG07_author_certified_metadata",
            "author_owned",
            "author_action_required",
            "materials/AUTHOR_OWNED_SUBMISSION_INTEGRITY_AUDIT.md; materials/ETHICS_DISCLOSURE_READINESS_PACK.md; materials/REMAINING_AUTHOR_BLOCKERS_MATRIX.md",
            "Authors must provide and certify affiliations, ORCID/contact details, conflicts, funding, acknowledgements, contribution roles, and AI/tool-use declarations.",
            "Author-owned metadata remain visible as required actions rather than silently filled.",
            "No author identity, conflict, funding, ORCID, CRediT, or institutional approval information is invented.",
            (
                f"ethics_author_required={ethics['summary']['author_required_count']}; "
                f"author_integrity_metadata_author_required={author_integrity['summary']['metadata_author_required_count']}; "
                f"remaining_blockers={blockers['summary']['author_required_count']}"
            ),
        ),
        row(
            "AUG08_archive_identifier_pending",
            "public_archive",
            "author_action_required" if fair_identifier_pending else "pass",
            "materials/FAIR_ARCHIVE_METADATA.md; materials/CITATION_METADATA.md; materials/ARCHIVE_UPLOAD_READINESS_MATRIX.md",
            "Deposit the final package, obtain DOI/accession/URL, and update citation, availability, and portal fields.",
            "Archive-ready metadata and checksum manifests are present, while the public identifier remains author/depositor-owned.",
            "The local package must not claim a DOI, accession, or public repository record before deposition.",
            (
                f"fair_identifier_pending={fair_identifier_pending}; "
                f"citation_external_doi_present={citation['summary']['external_doi_present']}; "
                f"citation_external_url_present={citation['summary']['external_url_present']}; "
                f"citation_author_required={citation['summary']['author_required_count']}; "
                f"archive_author_actions={archive_upload['summary']['author_action_required_count']}"
            ),
        ),
        row(
            "AUG09_target_journal_adaptation",
            "journal_portal",
            "author_action_required",
            "materials/TARGET_JOURNAL_COMPLIANCE_MATRIX.md; manuscript/SOURCE_PACKAGE_README.md",
            "Convert the journal-neutral manuscript, figures, captions, and source files into the selected journal template and portal limits.",
            "Common top-journal requirement classes are mapped to local evidence and author actions.",
            "The matrix is not a substitute for the current official instructions of the chosen journal.",
            f"journal_rows={journal['summary']['row_count']}; high_priority={journal['summary']['high_priority_count']}; author_actions={journal['summary']['author_action_count']}",
        ),
        row(
            "AUG10_handoff_and_freeze_sequence",
            "author_handoff",
            "ready_for_author_handoff",
            "materials/FINAL_AUTHOR_HANDOFF_CHECKLIST.md; materials/AUTHOR_ACTION_FREEZE_PLAN.md",
            "Follow the handoff sequence, complete blocking author rows, then rerun freeze/gate commands after all edits.",
            "The package has a concrete final author workflow with rerun commands and acceptance criteria.",
            "A ready handoff checklist still contains author-owned blockers by design.",
            (
                f"handoff_blocking_rows={handoff['summary']['blocking_row_count']}; "
                f"freeze_blockers={freeze_plan['summary']['blocker_count']}; "
                f"dashboard_review_required={dashboard['summary']['review_required_row_count']}"
            ),
        ),
        row(
            "AUG11_reviewer_command_route",
            "reviewer_reproducibility",
            reviewer_preflight["summary"]["status"],
            "materials/REVIEWER_COMMAND_PREFLIGHT.md; materials/REVIEWER_REPLICATION_ROUTE.md",
            "Use static command preflight before optional GPU reruns or reviewer-selected reproduction routes.",
            "Reviewer commands have registered scripts, root arguments, and optional expensive rerun boundaries.",
            "Static preflight does not execute experiments or create new empirical evidence.",
            (
                f"route_rows={reviewer_preflight['summary']['route_row_count']}; "
                f"subcommands={reviewer_preflight['summary']['subcommand_count']}; "
                f"review_required={reviewer_preflight['summary']['review_required_count']}"
            ),
        ),
    ]

    review_required_count = sum(1 for item in rows if item["status"] == "review_required")
    author_action_count = sum(1 for item in rows if "author_action" in item["status"])
    pass_count = sum(1 for item in rows if item["status"] in {"pass", "ready_for_author_handoff", "ready_with_author_completion"})
    status = "pass" if review_required_count == 0 else "review_required"

    return {
        "root": str(root),
        "title": "Author Upload Gap Closure Audit",
        "purpose": (
            "Close the gap between local evidence-package readiness and author-owned journal upload actions by "
            "checking file-bundle completeness, upload-selection boundaries, portal fields, archive identifiers, "
            "handoff sequence, and current package snapshots."
        ),
        "rows": rows,
        "summary": {
            "status": status,
            "row_count": len(rows),
            "pass_or_ready_count": pass_count,
            "review_required_count": review_required_count,
            "author_action_required_count": author_action_count,
            "publication_verification_status": verification["summary"]["status"],
            "publication_smoke_test_reference": "materials/PUBLICATION_SMOKE_TEST.json",
            "artifact_provenance": provenance_ratio,
            "release_file_count": current_release_count,
            "release_size_reference": "materials/RELEASE_ARCHIVE_MANIFEST.json",
            "final_bundle_missing_required": final_bundle["summary"]["missing_required_count"],
            "upload_selection_author_selection_required": upload_plan["summary"]["author_selection_required_count"],
            "portal_author_required_fields": portal_fields["summary"]["author_required_count"],
            "freeze_plan_blockers": freeze_plan["summary"]["blocker_count"],
            "handoff_blocking_rows": handoff["summary"]["blocking_row_count"],
            "fair_external_identifier_pending": fair_identifier_pending,
            "stale_active_entry_field_count": len(stale_release_fields) + len(stale_provenance_fields),
        },
        "interpretation": (
            "A pass here means active local upload-entry materials are internally aligned and no local required files "
            "are missing. Author-action rows remain expected and must not be auto-filled by local automation."
        ),
    }


def write_csv(report, path):
    fields = ["gap_id", "section", "status", "local_evidence", "author_action", "closure_test", "boundary", "note"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(report["rows"])


def write_markdown(report, path):
    lines = [
        "# Author Upload Gap Closure Audit",
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
            "## Gap Closure Rows",
            "",
            "| gap id | section | status | local evidence | author action | closure test | boundary | note |",
            "|---|---|---|---|---|---|---|---|",
        ]
    )
    for item in report["rows"]:
        lines.append(
            f"| {item['gap_id']} | {item['section']} | {item['status']} | `{item['local_evidence']}` | "
            f"{item['author_action']} | {item['closure_test']} | {item['boundary']} | {item['note']} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export author upload gap closure audit.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_report(root)
    out_json = materials / "AUTHOR_UPLOAD_GAP_CLOSURE_AUDIT.json"
    out_md = materials / "AUTHOR_UPLOAD_GAP_CLOSURE_AUDIT.md"
    out_csv = materials / "AUTHOR_UPLOAD_GAP_CLOSURE_AUDIT.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv), "summary": report["summary"]}, indent=2))


if __name__ == "__main__":
    main()
