#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def make_row(row_id, decision_area, current_evidence, author_action, readiness_boundary, status, files):
    return {
        "id": row_id,
        "decision_area": decision_area,
        "current_evidence": current_evidence,
        "author_action": author_action,
        "readiness_boundary": readiness_boundary,
        "status": status,
        "files": files,
    }


def build_report(root):
    dashboard = load_json(root / "materials" / "SUBMISSION_READINESS_DASHBOARD.json")
    slim = load_json(root / "materials" / "SLIM_SUBMISSION_PACKAGE_MANIFEST.json")
    archive_size = load_json(root / "materials" / "ARCHIVE_SIZE_BUDGET_REPORT.json")
    upload_matrix = load_json(root / "materials" / "ARCHIVE_UPLOAD_READINESS_MATRIX.json")
    final_bundle = load_json(root / "materials" / "FINAL_SUBMISSION_FILE_BUNDLE.json")
    freeze_plan = load_json(root / "materials" / "AUTHOR_ACTION_FREEZE_PLAN.json")
    blockers = load_json(root / "materials" / "REMAINING_AUTHOR_BLOCKERS_MATRIX.json")
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    smoke = load_json(root / "materials" / "PUBLICATION_SMOKE_TEST.json")
    provenance = load_json(root / "tables" / "artifact_provenance.json")
    data_dictionary = load_json(root / "materials" / "DATA_DICTIONARY.json")

    dashboard_summary = dashboard["summary"]
    archive_summary = archive_size["summary"]
    slim_summary = slim["summary"]
    matrix_summary = upload_matrix["summary"]
    bundle_summary = final_bundle["summary"]
    freeze_summary = freeze_plan["summary"]
    blocker_summary = blockers["summary"]

    rows = [
        make_row(
            "AUDM01_slim_journal_upload",
            "Slim journal-facing upload",
            (
                f"{slim_summary['slim_file_count']} files; "
                "size reference=materials/SLIM_SUBMISSION_PACKAGE_MANIFEST.json; "
                f"status={slim_summary['status']}"
            ),
            "Use the slim manifest as the default journal-facing file list, then adapt file names and formats to the selected portal.",
            "A slim local package is not a completed journal portal upload.",
            "ready",
            "materials/SLIM_SUBMISSION_PACKAGE_MANIFEST.md; materials/SLIM_SUBMISSION_PACKAGE_FILES.csv",
        ),
        make_row(
            "AUDM02_full_archive_deposition",
            "Full public archive deposition",
            (
                f"{archive_summary['release_file_count']} release files; "
                "release size reference=materials/ARCHIVE_SIZE_BUDGET_REPORT.json; "
                f"upload matrix status={matrix_summary['status']}"
            ),
            "Deposit the full release package in a public repository and replace pending DOI/URL/accession placeholders only after deposition.",
            "Local archive readiness is not an external DOI, accession, or repository receipt.",
            "author_action_required",
            "materials/ARCHIVE_README.md; materials/RELEASE_ARCHIVE_MANIFEST.md; materials/FAIR_ARCHIVE_METADATA.md; materials/CITATION.cff",
        ),
        make_row(
            "AUDM03_size_budget_review",
            "Upload-size and large-file routing",
            (
                f"archive size status={archive_summary['status']}; "
                f"budget flags={archive_summary['budget_review_required_count']}; "
                f"single files >50 MB={archive_summary['single_file_over_50mb_count']}"
            ),
            "Route large TIFF/GIF/trace files according to the selected journal and repository limits; keep full checksums in the archive manifest.",
            "The size flag is an operational upload review, not an evidence failure or statistical failure.",
            "ready_with_size_review",
            "materials/ARCHIVE_SIZE_BUDGET_REPORT.md; materials/ARCHIVE_SIZE_BUDGET_LARGEST_FILES.csv",
        ),
        make_row(
            "AUDM04_review_required_rows",
            "Review-required dashboard rows",
            (
                f"dashboard review_required={dashboard_summary['review_required_row_count']}; "
                f"reviewer route={dashboard_summary['reviewer_replication_route_status']}; "
                f"supplement assembly={dashboard_summary['manuscript_supplement_assembly_status']}"
            ),
            "Keep these as author/journal-placement decisions unless the target journal requires a different supplement or replication route.",
            "These rows are navigation and assembly decisions; core evidence gates remain pass.",
            "author_selection_required",
            "materials/SUBMISSION_READINESS_DASHBOARD.md; materials/REVIEWER_REPLICATION_ROUTE.md; materials/MANUSCRIPT_SUPPLEMENT_ASSEMBLY_MAP.md",
        ),
        make_row(
            "AUDM05_author_metadata",
            "Author-certified metadata and disclosures",
            (
                f"freeze blockers={freeze_summary['blocker_count']}; "
                f"remaining author blockers={blocker_summary['author_required_count']}"
            ),
            "Authors must complete ORCID, affiliations, CRediT roles, funding, conflicts, acknowledgements, correspondence, and final archive identifiers.",
            "The local package intentionally does not invent or certify author-owned metadata.",
            "author_action_required",
            "materials/AUTHOR_ACTION_FREEZE_PLAN.md; materials/REMAINING_AUTHOR_BLOCKERS_MATRIX.md; materials/ETHICS_DISCLOSURE_READINESS_PACK.md",
        ),
        make_row(
            "AUDM06_core_package_gates",
            "Core local package gates",
            (
                f"verification={verification['summary']['status']}; smoke={smoke['summary']['status']}; "
                f"artifact provenance={provenance['complete_count']}/{len(provenance['artifacts'])}; "
                f"data dictionary complete={data_dictionary['summary']['complete']}"
            ),
            "Rerun verification, smoke test, data dictionary, and checksum freeze after final author edits or archive deposition.",
            "Passing local gates support package integrity; they are not peer review, acceptance, or safety certification.",
            "pass",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.md; materials/PUBLICATION_SMOKE_TEST.md; materials/DATA_DICTIONARY.md; tables/artifact_provenance.md",
        ),
        make_row(
            "AUDM07_final_bundle",
            "Final file bundle routing",
            (
                f"bundle rows={bundle_summary['file_row_count']}; "
                f"missing required={bundle_summary['missing_required_count']}; "
                f"author selection required={bundle_summary['author_selection_required_count']}"
            ),
            "Use the final bundle and upload-selection plan to choose journal, source-data, supplement, archive, reviewer-support, and internal-only placements.",
            "The bundle maps local evidence to likely upload slots; target-journal rules still control final placement.",
            "ready_with_author_selection",
            "materials/FINAL_SUBMISSION_FILE_BUNDLE.md; materials/SUBMISSION_UPLOAD_SELECTION_PLAN.md; materials/ARCHIVE_UPLOAD_READINESS_MATRIX.md",
        ),
    ]

    status_counts = {}
    for row in rows:
        status_counts[row["status"]] = status_counts.get(row["status"], 0) + 1

    return {
        "root": str(root),
        "title": "Author Upload Decision Memo",
        "purpose": (
            "Provide an author-facing decision memo that separates local package completeness from target-journal upload choices, "
            "external archive deposition, large-file routing, and author-certified metadata."
        ),
        "summary": {
            "status": "ready_with_author_actions",
            "row_count": len(rows),
            "status_counts": status_counts,
            "publication_verification_status": verification["summary"]["status"],
            "publication_smoke_test_reference": "materials/PUBLICATION_SMOKE_TEST.json",
            "artifact_provenance": f"{provenance['complete_count']}/{len(provenance['artifacts'])}",
            "data_dictionary_complete": data_dictionary["summary"]["complete"],
            "dashboard_review_required": dashboard_summary["review_required_row_count"],
            "core_dashboard_review_required": dashboard_summary.get("core_dashboard_review_required", 0),
            "archive_size_budget_status": archive_summary["status"],
            "archive_size_budget_flags": archive_summary["budget_review_required_count"],
            "slim_submission_package_status": slim_summary["status"],
            "slim_submission_package_size_reference": "materials/SLIM_SUBMISSION_PACKAGE_MANIFEST.json",
            "final_bundle_missing_required": bundle_summary["missing_required_count"],
            "author_freeze_blockers": freeze_summary["blocker_count"],
        },
        "rows": rows,
        "interpretation": (
            "This memo is deliberately journal-neutral. It does not create new experimental evidence, claim external deposition, "
            "or certify author metadata. It records what is locally ready, what remains an author or target-journal decision, "
            "and why size/review-required flags are operational boundaries rather than evidence failures."
        ),
    }


def write_csv(report, path):
    fields = ["id", "decision_area", "status", "current_evidence", "author_action", "readiness_boundary", "files"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in report["rows"]:
            writer.writerow({field: row.get(field, "") for field in fields})


def write_markdown(report, path):
    lines = [
        "# Author Upload Decision Memo",
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
            "## Decisions",
            "",
            "| id | area | status | current evidence | author action | boundary | files |",
            "|---|---|---|---|---|---|---|",
        ]
    )
    for row in report["rows"]:
        lines.append(
            f"| {row['id']} | {row['decision_area']} | {row['status']} | {row['current_evidence']} | "
            f"{row['author_action']} | {row['readiness_boundary']} | `{row['files']}` |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export author upload decision memo.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_report(root)
    out_json = materials / "AUTHOR_UPLOAD_DECISION_MEMO.json"
    out_md = materials / "AUTHOR_UPLOAD_DECISION_MEMO.md"
    out_csv = materials / "AUTHOR_UPLOAD_DECISION_MEMO.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv), "summary": report["summary"]}, indent=2))


if __name__ == "__main__":
    main()
