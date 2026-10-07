#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_report(root):
    freeze = load_json(root / "materials" / "AUTHOR_ACTION_FREEZE_PLAN.json")
    portal = load_json(root / "materials" / "SUBMISSION_PORTAL_PACKAGE_MAP.json")
    metadata = load_json(root / "materials" / "SUBMISSION_METADATA_DRAFT.json")
    archive = load_json(root / "materials" / "EXTERNAL_ARCHIVE_PREFLIGHT.json")
    references = load_json(root / "materials" / "REFERENCE_READINESS_AUDIT.json")
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    related = load_json(root / "materials" / "RELATED_WORK_POSITIONING_MATRIX.json")

    freeze_rows = freeze["rows"]
    rows = []
    for row in freeze_rows:
        if row["blocker_if_missing"]:
            status = "author_required"
        elif row["id"] == "AF6_related_work_expansion" and references["summary"]["topic_needs_author_completion_count"] == 0:
            status = "locally_satisfied_pending_author_style_review"
        else:
            status = "recommended_or_if_requested"
        rows.append(
            {
                "id": row["id"],
                "category": row["category"],
                "owner": row["owner"],
                "status": status,
                "priority": row["priority"],
                "remaining_action": row["action"],
                "evidence": row["evidence"],
                "acceptance_criteria": row["acceptance_criteria"],
                "can_be_completed_locally": row["id"] in {"AF7_source_data_upload_pack", "AF8_claim_and_boundary_final_pass", "AF9_final_checksum_freeze"},
                "blocks_upload": row["blocker_if_missing"],
            }
        )

    author_required = [row for row in rows if row["status"] == "author_required"]
    locally_satisfied = [row for row in rows if row["status"] == "locally_satisfied_pending_author_style_review"]
    local_possible = [row for row in rows if row["can_be_completed_locally"]]

    return {
        "root": str(root),
        "title": "Remaining Author Blockers Matrix",
        "purpose": (
            "Separate remaining author-owned blockers from locally completed or locally maintainable pre-submission tasks. "
            "This prevents solved items, such as starter related-work coverage, from obscuring true upload blockers."
        ),
        "rows": rows,
        "summary": {
            "row_count": len(rows),
            "author_required_count": len(author_required),
            "locally_satisfied_pending_author_style_review_count": len(locally_satisfied),
            "locally_maintainable_count": len(local_possible),
            "portal_author_action_count": portal["summary"]["author_action_count"],
            "metadata_author_required_count": metadata["summary"]["author_required_count"],
            "archive_author_required_count": archive["summary"]["author_required_count"],
            "reference_topics_needing_author_completion": references["summary"]["topic_needs_author_completion_count"],
            "related_work_positioning_rows": related["summary"]["row_count"],
            "publication_verification_status": verification["summary"]["status"],
            "artifact_provenance": verification["summary"]["artifact_provenance"],
        },
        "interpretation": (
            "The current local package can support submission preparation, but final upload still depends on author-certified "
            "journal selection, author metadata, disclosures, and archive DOI/accession fields."
        ),
    }


def write_csv(report, path):
    fields = [
        "id",
        "category",
        "owner",
        "status",
        "priority",
        "remaining_action",
        "evidence",
        "acceptance_criteria",
        "can_be_completed_locally",
        "blocks_upload",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in report["rows"]:
            writer.writerow({key: row[key] for key in fields})


def write_markdown(report, path):
    lines = [
        "# Remaining Author Blockers Matrix",
        "",
        report["purpose"],
        "",
        report["interpretation"],
        "",
        "## Summary",
        "",
        f"- Rows: {report['summary']['row_count']}",
        f"- Author-required rows: {report['summary']['author_required_count']}",
        f"- Locally satisfied pending author style review: {report['summary']['locally_satisfied_pending_author_style_review_count']}",
        f"- Locally maintainable rows: {report['summary']['locally_maintainable_count']}",
        f"- Reference topics needing author completion: {report['summary']['reference_topics_needing_author_completion']}",
        f"- Publication verification: `{report['summary']['publication_verification_status']}`",
        f"- Artifact provenance: {report['summary']['artifact_provenance']}",
        "",
        "## Matrix",
        "",
        "| id | category | status | priority | blocks upload | local completion possible | remaining action | evidence |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for row in report["rows"]:
        lines.append(
            f"| {row['id']} | {row['category']} | {row['status']} | {row['priority']} | "
            f"{row['blocks_upload']} | {row['can_be_completed_locally']} | {row['remaining_action']} | `{row['evidence']}` |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export remaining author blocker matrix.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_report(root)
    out_json = materials / "REMAINING_AUTHOR_BLOCKERS_MATRIX.json"
    out_md = materials / "REMAINING_AUTHOR_BLOCKERS_MATRIX.md"
    out_csv = materials / "REMAINING_AUTHOR_BLOCKERS_MATRIX.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv), "summary": report["summary"]}, indent=2))


if __name__ == "__main__":
    main()
