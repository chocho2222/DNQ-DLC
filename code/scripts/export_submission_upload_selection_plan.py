#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def destination_for(row):
    slot = row["slot"]
    package = row["upload_package"]
    path = row["path"]
    if package == "journal_submission" and slot.startswith("figure_"):
        return "main_figure_upload"
    if package == "journal_submission":
        return "main_manuscript_or_portal_text"
    if package == "source_data_upload":
        return "source_data_upload"
    if package == "supplement":
        return "supplementary_information"
    if package == "archive":
        return "public_archive"
    if package == "archive_and_submission":
        return "availability_statement_and_public_archive"
    if package == "internal_pre_submission":
        return "internal_pre_submission_qc"
    if package == "portal_reference" and path.endswith("/"):
        return "author_curated_archive_subset"
    if package == "portal_reference":
        return "portal_reference_or_supporting_upload"
    return "author_review"


def priority_for(destination, row):
    if row["required"] and destination in {"main_manuscript_or_portal_text", "main_figure_upload", "source_data_upload"}:
        return "required_upload"
    if destination in {"public_archive", "availability_statement_and_public_archive"}:
        return "required_archive"
    if destination == "supplementary_information":
        return "recommended_supplement"
    if destination == "internal_pre_submission_qc":
        return "do_not_upload_unless_requested"
    if row["status"] == "author_selection_required":
        return "author_selection_required"
    return "optional_or_journal_dependent"


def decision_rationale_for(destination, priority, row):
    if priority == "required_upload":
        return "Core manuscript, figure, or source-data material expected in the journal-facing submission path."
    if priority == "required_archive":
        return "Material required for public data/code availability and release provenance rather than only the journal portal."
    if priority == "recommended_supplement":
        return "Reviewer-facing support material that improves traceability and reporting completeness."
    if priority == "do_not_upload_unless_requested":
        return "Internal QC or pre-submission audit material; retain locally and in the archive unless the journal or reviewers request it."
    if priority == "author_selection_required":
        return "Directory-level or optional material whose final placement depends on target-journal limits and author upload strategy."
    if destination == "portal_reference_or_supporting_upload":
        return "Portal-supporting material that may be copied into forms, uploaded as support, or retained in the archive depending on journal rules."
    return "Journal-dependent support material; authors should decide after target-journal instructions are fixed."


def upload_condition_for(destination, priority, row):
    if priority == "required_upload":
        return "Upload or convert for the selected journal unless the portal uses an equivalent field or combined source package."
    if priority == "required_archive":
        return "Include in the public archive or availability package before final DOI/URL deposition."
    if priority == "recommended_supplement":
        return "Upload as supplementary information when size and format limits allow; otherwise merge or archive with clear navigation."
    if priority == "do_not_upload_unless_requested":
        return "Do not upload to the reviewer-facing portal by default; keep for internal final checks, archive provenance, or reviewer requests."
    if priority == "author_selection_required":
        return "Select a curated subset after target-journal file limits, anonymity policy, and repository deposition route are known."
    if destination == "portal_reference_or_supporting_upload":
        return "Use as portal copy/reference or supporting upload only if the target journal provides a matching slot."
    return "Review after target-journal instructions are known."


def build_report(root):
    bundle = load_json(root / "materials" / "FINAL_SUBMISSION_FILE_BUNDLE.json")
    dashboard = load_json(root / "materials" / "SUBMISSION_READINESS_DASHBOARD.json")
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    release = load_json(root / "materials" / "RELEASE_ARCHIVE_MANIFEST.json")
    release_paths = {item["path"] for item in release["files"]}

    rows = []
    for item in bundle["files"]:
        destination = destination_for(item)
        priority = priority_for(destination, item)
        decision_rationale = decision_rationale_for(destination, priority, item)
        upload_condition = upload_condition_for(destination, priority, item)
        rows.append(
            {
                "slot": item["slot"],
                "file_type": item["file_type"],
                "path": item["path"],
                "recommended_destination": destination,
                "upload_priority": priority,
                "exists": item["exists"],
                "in_release_manifest": item["path"] in release_paths,
                "journal_portal_candidate": destination
                in {
                    "main_manuscript_or_portal_text",
                    "main_figure_upload",
                    "source_data_upload",
                    "supplementary_information",
                    "portal_reference_or_supporting_upload",
                },
                "archive_candidate": item["path"] in release_paths and destination
                not in {"internal_pre_submission_qc"},
                "author_selection_required": item["status"] == "author_selection_required"
                or priority == "author_selection_required",
                "status": item["status"],
                "decision_rationale": decision_rationale,
                "upload_condition": upload_condition,
                "note": item["note"],
            }
        )

    destination_counts = {}
    priority_counts = {}
    for row in rows:
        destination_counts[row["recommended_destination"]] = destination_counts.get(row["recommended_destination"], 0) + 1
        priority_counts[row["upload_priority"]] = priority_counts.get(row["upload_priority"], 0) + 1

    return {
        "root": str(root),
        "title": "Submission Upload Selection Plan",
        "purpose": (
            "Convert the final file-bundle map into a practical upload/withhold plan for journal portals, "
            "source-data upload, supplementary information, public archive deposition, and internal QC files."
        ),
        "rows": rows,
        "summary": {
            "status": "ready_with_author_selection",
            "row_count": len(rows),
            "journal_portal_candidate_count": sum(1 for row in rows if row["journal_portal_candidate"]),
            "archive_candidate_count": sum(1 for row in rows if row["archive_candidate"]),
            "author_selection_required_count": sum(1 for row in rows if row["author_selection_required"]),
            "destination_counts": destination_counts,
            "priority_counts": priority_counts,
            "publication_verification_status": verification["summary"]["status"],
            "dashboard_author_action_rows": dashboard["summary"]["author_action_row_count"],
        },
        "interpretation": (
            "This plan is an operational upload checklist. It should be applied after authors choose the target journal "
            "and before final archive deposition; internal QC rows are normally retained rather than uploaded."
        ),
    }


def write_csv(report, path):
    fields = [
        "slot",
        "file_type",
        "path",
        "recommended_destination",
        "upload_priority",
        "exists",
        "in_release_manifest",
        "journal_portal_candidate",
        "archive_candidate",
        "author_selection_required",
        "status",
        "decision_rationale",
        "upload_condition",
        "note",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in report["rows"]:
            writer.writerow(row)


def write_markdown(report, path):
    lines = [
        "# Submission Upload Selection Plan",
        "",
        report["purpose"],
        "",
        report["interpretation"],
        "",
        "## Summary",
        "",
        f"- Status: `{report['summary']['status']}`",
        f"- Rows: {report['summary']['row_count']}",
        f"- Journal portal candidates: {report['summary']['journal_portal_candidate_count']}",
        f"- Archive candidates: {report['summary']['archive_candidate_count']}",
        f"- Author-selection rows: {report['summary']['author_selection_required_count']}",
        f"- Publication verification: `{report['summary']['publication_verification_status']}`",
        "",
        "## Upload Rows",
        "",
        "| destination | priority | slot | file type | status | path | decision rationale | upload condition | note |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for row in report["rows"]:
        lines.append(
            f"| {row['recommended_destination']} | {row['upload_priority']} | {row['slot']} | "
            f"{row['file_type']} | {row['status']} | `{row['path']}` | "
            f"{row['decision_rationale']} | {row['upload_condition']} | {row['note']} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export submission upload selection plan.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_report(root)
    out_json = materials / "SUBMISSION_UPLOAD_SELECTION_PLAN.json"
    out_md = materials / "SUBMISSION_UPLOAD_SELECTION_PLAN.md"
    out_csv = materials / "SUBMISSION_UPLOAD_SELECTION_PLAN.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv), "summary": report["summary"]}, indent=2))


if __name__ == "__main__":
    main()
