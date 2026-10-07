#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def decision_for(item):
    priority = item["priority"]
    group = item["upload_group"]
    if priority in {"required_supplement", "required_source_data"}:
        return "required_upload"
    if priority == "required_archive":
        return "required_archive"
    if group == "supplementary_analysis":
        return "author_selection_required"
    if priority == "recommended_supplement":
        return "recommended_supplement"
    return "journal_dependent"


def destination_for(decision):
    if decision == "required_upload":
        return "supplementary_information_or_source_data"
    if decision == "required_archive":
        return "public_archive"
    if decision == "author_selection_required":
        return "optional_supplement_or_reviewer_response_or_archive"
    if decision == "recommended_supplement":
        return "supplementary_information_if_space_allows"
    return "target_journal_dependent"


def status_for(item, decision):
    if not item["exists"] or not item["source_exists"]:
        return "missing_local_file"
    if decision in {"required_upload", "required_archive", "recommended_supplement"}:
        return "ready"
    if decision == "author_selection_required":
        return "ready_with_author_selection"
    return "ready_with_journal_selection"


def build_report(root):
    index = load_json(root / "materials" / "SUPPLEMENTARY_MATERIALS_INDEX.json")
    table_legends = load_json(root / "materials" / "SUPPLEMENTARY_TABLE_LEGENDS.json")
    upload_plan = load_json(root / "materials" / "SUBMISSION_UPLOAD_SELECTION_PLAN.json")
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    smoke = load_json(root / "materials" / "PUBLICATION_SMOKE_TEST.json")
    release = load_json(root / "materials" / "RELEASE_ARCHIVE_MANIFEST.json")
    provenance = load_json(root / "tables" / "artifact_provenance.json")
    release_paths = {item["path"] for item in release["files"]}

    rows = []
    for item in index["items"]:
        decision = decision_for(item)
        destination = destination_for(decision)
        status = status_for(item, decision)
        rows.append(
            {
                "id": item["id"],
                "upload_group": item["upload_group"],
                "display_label": item["display_label"],
                "path": item["path"],
                "source": item["source"],
                "priority": item["priority"],
                "decision": decision,
                "recommended_destination": destination,
                "exists": item["exists"],
                "source_exists": item["source_exists"],
                "in_release_manifest": item["path"] in release_paths,
                "status": status,
                "author_action": (
                    "Choose whether to upload as optional supplementary analysis, keep for reviewer response, or retain only in archive."
                    if decision == "author_selection_required"
                    else "Adapt labels and upload slot to the selected journal."
                ),
                "claim_boundary": item["claim_boundary"],
            }
        )

    missing_required = [
        row
        for row in rows
        if row["decision"] in {"required_upload", "required_archive"}
        and row["status"] != "ready"
    ]
    author_selection = [row for row in rows if row["decision"] == "author_selection_required"]
    status_counts = {}
    decision_counts = {}
    for row in rows:
        status_counts[row["status"]] = status_counts.get(row["status"], 0) + 1
        decision_counts[row["decision"]] = decision_counts.get(row["decision"], 0) + 1

    return {
        "root": str(root),
        "title": "Supplement Upload Decision Matrix",
        "purpose": (
            "Separate required supplementary tables/source data, required archive files, recommended supplements, "
            "and author-selected reviewer-support analyses before target-journal upload."
        ),
        "rows": rows,
        "summary": {
            "status": "ready_with_author_selection" if not missing_required else "review_required",
            "row_count": len(rows),
            "required_missing_count": len(missing_required),
            "author_selection_required_count": len(author_selection),
            "decision_counts": decision_counts,
            "status_counts": status_counts,
            "supplementary_index_status": "pass"
            if index["summary"]["review_required_count"] == 0
            else "review_required",
            "supplementary_index_review_required_count": index["summary"]["review_required_count"],
            "supplementary_table_legends_status": table_legends["summary"]["status"],
            "submission_upload_author_selection_required": upload_plan["summary"]["author_selection_required_count"],
            "publication_verification_status": verification["summary"]["status"],
            "publication_smoke_test_reference": "materials/PUBLICATION_SMOKE_TEST.json",
            "artifact_provenance": f"{provenance['complete_count']}/{len(provenance['artifacts'])}",
            "release_file_count": release["summary"]["file_count"],
        },
        "interpretation": (
            "A ready_with_author_selection status means local files and sources are present, while optional reviewer-support "
            "analyses still require author choice after the target journal is selected. It is not a missing-evidence flag."
        ),
    }


def write_csv(report, path):
    fields = [
        "id",
        "upload_group",
        "display_label",
        "path",
        "source",
        "priority",
        "decision",
        "recommended_destination",
        "exists",
        "source_exists",
        "in_release_manifest",
        "status",
        "author_action",
        "claim_boundary",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in report["rows"]:
            writer.writerow({field: row[field] for field in fields})


def write_markdown(report, path):
    lines = [
        "# Supplement Upload Decision Matrix",
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
            "## Rows",
            "",
            "| id | group | decision | destination | status | file | source | author action | boundary |",
            "|---|---|---|---|---|---|---|---|---|",
        ]
    )
    for row in report["rows"]:
        lines.append(
            f"| {row['id']} | {row['upload_group']} | {row['decision']} | {row['recommended_destination']} | "
            f"{row['status']} | `{row['path']}` | `{row['source']}` | {row['author_action']} | {row['claim_boundary']} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export supplement upload decision matrix.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_report(root)
    out_json = materials / "SUPPLEMENT_UPLOAD_DECISION_MATRIX.json"
    out_md = materials / "SUPPLEMENT_UPLOAD_DECISION_MATRIX.md"
    out_csv = materials / "SUPPLEMENT_UPLOAD_DECISION_MATRIX.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv), "summary": report["summary"]}, indent=2))


if __name__ == "__main__":
    main()
