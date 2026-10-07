#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


AUTHOR_REQUIRED_FIELDS = {
    "SUBMISSION_METADATA_AUTHORS": {
        "path": "materials/SUBMISSION_METADATA_AUTHORS.csv",
        "status_column": "metadata_status",
        "required_status": "author_required",
        "sensitive_columns": ["affiliation", "orcid", "email", "corresponding_author"],
    },
    "SUBMISSION_METADATA_CREDIT": {
        "path": "materials/SUBMISSION_METADATA_CREDIT.csv",
        "status_column": "status",
        "required_status": "author_required",
        "sensitive_columns": ["suggested_contributors"],
    },
    "SUBMISSION_METADATA_DISCLOSURES": {
        "path": "materials/SUBMISSION_METADATA_DISCLOSURES.csv",
        "status_column": "status",
        "required_status": "author_required",
        "required_fields": {"competing_interests", "funding", "acknowledgements"},
        "field_column": "field",
        "sensitive_columns": [],
    },
}


PORTAL_AUTHOR_FIELDS = {
    "competing_interests",
    "funding",
    "acknowledgements",
    "author_metadata",
    "credit_contributions",
    "archive_doi_or_url",
}


FORBIDDEN_COMPLETION_MARKERS = {
    "complete",
    "completed",
    "certified",
    "author_certified",
    "ready",
    "pass",
    "package_supported",
}


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def read_csv(path):
    with Path(path).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def check_row(check_id, category, status, expected, observed, evidence, note):
    return {
        "check_id": check_id,
        "category": category,
        "status": status,
        "expected": expected,
        "observed": observed,
        "evidence": evidence,
        "note": note,
    }


def check_csv_author_required(root, table_id, spec):
    rows = []
    path = root / spec["path"]
    if not path.exists():
        return [
            check_row(
                f"AO_{table_id}_exists",
                "missing_file",
                "fail",
                "file exists",
                "missing",
                spec["path"],
                "Author-owned metadata table is required for disclosure integrity review.",
            )
        ]

    csv_rows = read_csv(path)
    if not csv_rows:
        return [
            check_row(
                f"AO_{table_id}_nonempty",
                "empty_file",
                "fail",
                "non-empty CSV",
                "empty",
                spec["path"],
                "Author-owned metadata table should contain explicit author-action rows.",
            )
        ]

    required_fields = spec.get("required_fields")
    if required_fields:
        by_field = {row.get(spec["field_column"], ""): row for row in csv_rows}
        missing = sorted(required_fields - set(by_field))
        rows.append(
            check_row(
                f"AO_{table_id}_required_fields",
                "required_field_presence",
                "pass" if not missing else "fail",
                sorted(required_fields),
                missing if missing else "all present",
                spec["path"],
                "Competing interests, funding, and acknowledgements must stay explicitly author-owned.",
            )
        )
        target_rows = [by_field[field] for field in required_fields if field in by_field]
    else:
        target_rows = csv_rows

    wrong_status = [
        row
        for row in target_rows
        if row.get(spec["status_column"], "").strip() != spec["required_status"]
    ]
    rows.append(
        check_row(
            f"AO_{table_id}_author_required_status",
            "author_required_status",
            "pass" if not wrong_status else "fail",
            spec["required_status"],
            f"{len(wrong_status)} rows with other status",
            spec["path"],
            "Author-owned fields must not be marked complete by local automation.",
        )
    )

    filled_sensitive = []
    for index, row in enumerate(csv_rows, start=1):
        for column in spec["sensitive_columns"]:
            if row.get(column, "").strip():
                filled_sensitive.append({"row": index, "column": column, "value": row[column]})
    rows.append(
        check_row(
            f"AO_{table_id}_sensitive_placeholders_blank",
            "blank_sensitive_fields",
            "pass" if not filled_sensitive else "fail",
            "blank until author completion",
            filled_sensitive if filled_sensitive else "all blank",
            spec["path"],
            "Affiliations, ORCID, email, corresponding-author flags, and CRediT contributors require author confirmation.",
        )
    )
    return rows


def build_report(root):
    metadata = load_json(root / "materials" / "SUBMISSION_METADATA_DRAFT.json")
    portal = load_json(root / "materials" / "SUBMISSION_PORTAL_FIELD_COMPLETION_PACK.json")
    ethics = load_json(root / "materials" / "ETHICS_DISCLOSURE_READINESS_PACK.json")
    blockers = load_json(root / "materials" / "REMAINING_AUTHOR_BLOCKERS_MATRIX.json")
    freeze = load_json(root / "materials" / "AUTHOR_ACTION_FREEZE_PLAN.json")
    fair = load_json(root / "materials" / "FAIR_ARCHIVE_METADATA.json")
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    provenance = load_json(root / "tables" / "artifact_provenance.json")

    rows = []
    for table_id, spec in AUTHOR_REQUIRED_FIELDS.items():
        rows.extend(check_csv_author_required(root, table_id, spec))

    portal_fields = {row["portal_field"]: row for row in portal["fields"]}
    portal_missing = sorted(PORTAL_AUTHOR_FIELDS - set(portal_fields))
    rows.append(
        check_row(
            "AO_portal_author_fields_present",
            "portal_author_fields",
            "pass" if not portal_missing else "fail",
            sorted(PORTAL_AUTHOR_FIELDS),
            portal_missing if portal_missing else "all present",
            "materials/SUBMISSION_PORTAL_FIELD_COMPLETION_PACK.json",
            "Journal-portal fields that need author certification should be explicit.",
        )
    )
    portal_wrong = [
        {"field": field, "status": portal_fields[field]["status"]}
        for field in PORTAL_AUTHOR_FIELDS
        if field in portal_fields and portal_fields[field]["status"] != "author_required"
    ]
    rows.append(
        check_row(
            "AO_portal_author_fields_author_required",
            "portal_author_fields",
            "pass" if not portal_wrong else "fail",
            "author_required",
            portal_wrong if portal_wrong else "all author_required",
            "materials/SUBMISSION_PORTAL_FIELD_COMPLETION_PACK.json",
            "Portal declarations and external archive identifiers must not be treated as locally complete.",
        )
    )

    disclosure_rows = {row["field"]: row for row in metadata["disclosure_rows"]}
    disclosure_wrong = [
        {"field": field, "status": disclosure_rows.get(field, {}).get("status")}
        for field in ["competing_interests", "funding", "acknowledgements"]
        if disclosure_rows.get(field, {}).get("status") != "author_required"
    ]
    rows.append(
        check_row(
            "AO_metadata_disclosure_rows_author_required",
            "metadata_disclosures",
            "pass" if not disclosure_wrong else "fail",
            "author_required",
            disclosure_wrong if disclosure_wrong else "all author_required",
            "materials/SUBMISSION_METADATA_DRAFT.json",
            "Disclosure rows require author certification and should retain author_required status.",
        )
    )

    submission_fields = {row["field"]: row for row in metadata["submission_fields"]}
    archive_status = submission_fields.get("archive_doi_or_url", {}).get("status")
    rows.append(
        check_row(
            "AO_archive_identifier_author_required",
            "external_identifier",
            "pass" if archive_status == "author_required" else "fail",
            "author_required",
            archive_status,
            "materials/SUBMISSION_METADATA_DRAFT.json; materials/FAIR_ARCHIVE_METADATA.json",
            "Public DOI/URL/accession must remain pending until real archive deposition exists.",
        )
    )
    identifier = fair.get("identifier", {})
    external_doi = identifier.get("external_doi")
    external_url = identifier.get("external_url")
    rows.append(
        check_row(
            "AO_no_fabricated_external_identifier",
            "external_identifier",
            "pass" if not external_doi and not external_url else "fail",
            "external_doi and external_url empty before deposition",
            {"external_doi": external_doi, "external_url": external_url},
            "materials/FAIR_ARCHIVE_METADATA.json",
            "Do not claim a DOI, accession, or public URL until it exists.",
        )
    )

    freeze_author_rows = [row for row in freeze["rows"] if row["owner"] == "authors" and row["blocker_if_missing"]]
    blocker_rows = [row for row in blockers["rows"] if row["status"] == "author_required"]
    rows.append(
        check_row(
            "AO_author_blockers_visible",
            "author_action_visibility",
            "pass" if len(freeze_author_rows) >= 6 and len(blocker_rows) >= 6 else "fail",
            "at least six visible author-owned blockers",
            {"freeze_blockers": len(freeze_author_rows), "remaining_author_blockers": len(blocker_rows)},
            "materials/AUTHOR_ACTION_FREEZE_PLAN.json; materials/REMAINING_AUTHOR_BLOCKERS_MATRIX.json",
            "Submission readiness should keep author-owned blockers visible instead of hiding them behind local pass statuses.",
        )
    )

    ethics_statuses = {row["item"]: row["status"] for row in ethics["rows"]}
    sensitive_ethics_wrong = {
        item: status
        for item, status in ethics_statuses.items()
        if item in {"competing_interests", "funding", "acknowledgements", "authors_affiliations_orcid_email", "credit_roles", "archive_identifier"}
        and status in FORBIDDEN_COMPLETION_MARKERS
    }
    rows.append(
        check_row(
            "AO_ethics_pack_no_false_completion",
            "ethics_disclosure_pack",
            "pass" if not sensitive_ethics_wrong else "fail",
            "sensitive items not marked complete/ready/pass",
            sensitive_ethics_wrong if sensitive_ethics_wrong else "no false completion markers",
            "materials/ETHICS_DISCLOSURE_READINESS_PACK.json",
            "Ethics/disclosure readiness should separate package-supported statements from author-certified declarations.",
        )
    )

    failed = [row for row in rows if row["status"] != "pass"]
    return {
        "root": str(root),
        "title": "Author-Owned Submission Integrity Audit",
        "purpose": (
            "Audit author-certified submission fields, external archive identifiers, disclosures, ORCID/contact metadata, "
            "and CRediT roles so local automation cannot accidentally mark them complete."
        ),
        "rows": rows,
        "summary": {
            "status": "pass" if not failed else "fail",
            "check_count": len(rows),
            "failed_checks": len(failed),
            "metadata_author_required_count": metadata["summary"]["author_required_count"],
            "portal_author_required_count": portal["summary"]["author_required_count"],
            "ethics_author_required_count": ethics["summary"]["author_required_count"],
            "remaining_author_required_count": blockers["summary"]["author_required_count"],
            "freeze_blocker_count": freeze["summary"]["blocker_count"],
            "external_identifier_pending": not external_doi and not external_url,
            "publication_verification_status": verification["summary"]["status"],
            "artifact_provenance": f"{provenance['complete_count']}/{len(provenance['artifacts'])}",
        },
        "interpretation": (
            "This audit is intentionally conservative: it should pass only when author-owned information remains visibly "
            "author-required. It does not certify or invent author metadata, funding, conflicts, ORCID identifiers, "
            "CRediT roles, or public archive accessions."
        ),
    }


def write_csv(report, path):
    fields = ["check_id", "category", "status", "expected", "observed", "evidence", "note"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(report["rows"])


def write_markdown(report, path):
    lines = [
        "# Author-Owned Submission Integrity Audit",
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
            "## Checks",
            "",
            "| check_id | category | status | expected | observed | evidence | note |",
            "|---|---|---|---|---|---|---|",
        ]
    )
    for row in report["rows"]:
        lines.append(
            f"| {row['check_id']} | {row['category']} | {row['status']} | "
            f"{row['expected']} | {row['observed']} | `{row['evidence']}` | {row['note']} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export author-owned submission integrity audit.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_report(root)
    out_json = materials / "AUTHOR_OWNED_SUBMISSION_INTEGRITY_AUDIT.json"
    out_md = materials / "AUTHOR_OWNED_SUBMISSION_INTEGRITY_AUDIT.md"
    out_csv = materials / "AUTHOR_OWNED_SUBMISSION_INTEGRITY_AUDIT.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv), "summary": report["summary"]}, indent=2))


if __name__ == "__main__":
    main()
