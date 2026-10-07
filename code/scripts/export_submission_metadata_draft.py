#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


CREDIT_ROLES = [
    "Conceptualization",
    "Methodology",
    "Software",
    "Validation",
    "Formal analysis",
    "Investigation",
    "Data curation",
    "Writing - original draft",
    "Writing - review & editing",
    "Visualization",
    "Supervision",
    "Project administration",
    "Funding acquisition",
]


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def parse_authors(repo_root):
    authors_path = repo_root / "AUTHORS"
    authors = []
    if not authors_path.exists():
        return authors
    for raw in authors_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        authors.append(line)
    return authors


def repo_root_from_package(root):
    return Path(root).resolve().parents[1]


def build_report(root):
    repo_root = repo_root_from_package(root)
    authors = parse_authors(repo_root)
    fair = load_json(root / "materials" / "FAIR_ARCHIVE_METADATA.json")
    checklist = load_json(root / "materials" / "EDITORIAL_SUBMISSION_CHECKLIST.json")
    risk = load_json(root / "materials" / "RESEARCH_RISK_AND_SAFETY.json")
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    reference = load_json(root / "materials" / "REFERENCE_READINESS_AUDIT.json")
    archive = load_json(root / "materials" / "EXTERNAL_ARCHIVE_PREFLIGHT.json")

    author_rows = []
    for index, name in enumerate(authors, start=1):
        author_rows.append(
            {
                "author_order": index,
                "name": name,
                "affiliation": "",
                "orcid": "",
                "email": "",
                "corresponding_author": "",
                "metadata_status": "author_required",
                "note": "Name parsed from AUTHORS; affiliation, ORCID, email, and contribution roles require author confirmation.",
            }
        )

    contribution_rows = []
    for role in CREDIT_ROLES:
        contribution_rows.append(
            {
                "credit_role": role,
                "suggested_contributors": "",
                "status": "author_required",
                "evidence": "AUTHORS; materials/EDITORIAL_SUBMISSION_CHECKLIST.md",
                "note": "Assign contributors manually before journal submission.",
            }
        )

    disclosure_rows = [
        {
            "field": "competing_interests",
            "draft_text": "The authors declare no competing interests. [AUTHOR CONFIRMATION REQUIRED]",
            "status": "author_required",
            "evidence": "materials/EDITORIAL_SUBMISSION_CHECKLIST.md",
        },
        {
            "field": "funding",
            "draft_text": "[AUTHOR REQUIRED: add funder names, grant numbers, and award identifiers, or state that no specific funding was received.]",
            "status": "author_required",
            "evidence": "materials/EDITORIAL_SUBMISSION_CHECKLIST.md; materials/EXTERNAL_ARCHIVE_PREFLIGHT.md",
        },
        {
            "field": "acknowledgements",
            "draft_text": "[AUTHOR REQUIRED: add acknowledgements or state none.]",
            "status": "author_required",
            "evidence": "materials/EDITORIAL_SUBMISSION_CHECKLIST.md",
        },
        {
            "field": "ethics_statement",
            "draft_text": risk["ethics_context"]["rationale"],
            "status": "package_supported",
            "evidence": "materials/RESEARCH_RISK_AND_SAFETY.md",
        },
        {
            "field": "data_availability",
            "draft_text": "Data and code are available locally in the package described by materials/DATA_CODE_AVAILABILITY.md; update this text with the public DOI/URL after external archiving.",
            "status": "package_supported_pending_archive",
            "evidence": "materials/DATA_CODE_AVAILABILITY.md; materials/EXTERNAL_ARCHIVE_PREFLIGHT.md",
        },
        {
            "field": "code_availability",
            "draft_text": "Code snapshots, reproduction commands, environment records, and artifact provenance are included in the local package; update with the public repository URL/DOI after archiving.",
            "status": "package_supported_pending_archive",
            "evidence": "materials/REPRODUCTION_GUIDE.md; tables/artifact_provenance.md",
        },
    ]

    submission_fields = [
        {
            "field": "title",
            "value": fair["title"],
            "status": "package_supported",
            "source": "materials/FAIR_ARCHIVE_METADATA.json",
        },
        {
            "field": "resource_type",
            "value": fair["resource_type"]["resource_type"],
            "status": "package_supported",
            "source": "materials/FAIR_ARCHIVE_METADATA.json",
        },
        {
            "field": "keywords",
            "value": "; ".join(fair["keywords"]),
            "status": "package_supported",
            "source": "materials/FAIR_ARCHIVE_METADATA.json",
        },
        {
            "field": "archive_doi_or_url",
            "value": "",
            "status": "author_required",
            "source": "materials/EXTERNAL_ARCHIVE_PREFLIGHT.json",
        },
        {
            "field": "reference_status",
            "value": f"{reference['summary']['citation_key_count']} cited keys; domain related work still author-completion",
            "status": "package_supported_with_limitation",
            "source": "materials/REFERENCE_READINESS_AUDIT.json",
        },
    ]

    author_required_count = (
        len(author_rows)
        + len(contribution_rows)
        + sum(1 for row in disclosure_rows if row["status"] == "author_required")
        + sum(1 for row in submission_fields if row["status"] == "author_required")
    )
    return {
        "root": str(root),
        "title": "Submission Metadata Draft",
        "purpose": "Provide journal-submission metadata templates while separating package-supported statements from author-required disclosures.",
        "summary": {
            "status": "pass",
            "author_count": len(author_rows),
            "credit_role_count": len(contribution_rows),
            "disclosure_field_count": len(disclosure_rows),
            "submission_field_count": len(submission_fields),
            "author_required_count": author_required_count,
            "publication_verification_status": verification["summary"]["status"],
            "artifact_provenance": verification["summary"]["artifact_provenance"],
            "external_archive_pending": archive["summary"]["external_archive_pending"],
            "editorial_checklist_needs_author_input": checklist["summary"]["status_counts"].get("needs_author_input", 0),
        },
        "author_rows": author_rows,
        "contribution_rows": contribution_rows,
        "disclosure_rows": disclosure_rows,
        "submission_fields": submission_fields,
        "interpretation": (
            "This file is a submission-system draft, not an author-certified disclosure form. "
            "Do not mark competing interests, funding, affiliations, ORCID identifiers, or corresponding-author metadata complete without author confirmation."
        ),
    }


def write_csv(report, materials):
    author_csv = materials / "SUBMISSION_METADATA_AUTHORS.csv"
    contribution_csv = materials / "SUBMISSION_METADATA_CREDIT.csv"
    disclosure_csv = materials / "SUBMISSION_METADATA_DISCLOSURES.csv"
    with author_csv.open("w", newline="", encoding="utf-8") as handle:
        fields = ["author_order", "name", "affiliation", "orcid", "email", "corresponding_author", "metadata_status", "note"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(report["author_rows"])
    with contribution_csv.open("w", newline="", encoding="utf-8") as handle:
        fields = ["credit_role", "suggested_contributors", "status", "evidence", "note"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(report["contribution_rows"])
    with disclosure_csv.open("w", newline="", encoding="utf-8") as handle:
        fields = ["field", "draft_text", "status", "evidence"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(report["disclosure_rows"])
    return author_csv, contribution_csv, disclosure_csv


def write_markdown(report, path):
    lines = [
        "# Submission Metadata Draft",
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
            "## Authors",
            "",
            "| order | name | status | note |",
            "|---:|---|---|---|",
        ]
    )
    for row in report["author_rows"]:
        lines.append(f"| {row['author_order']} | {row['name']} | {row['metadata_status']} | {row['note']} |")
    lines.extend(
        [
            "",
            "## CRediT Roles",
            "",
            "| role | status | note |",
            "|---|---|---|",
        ]
    )
    for row in report["contribution_rows"]:
        lines.append(f"| {row['credit_role']} | {row['status']} | {row['note']} |")
    lines.extend(
        [
            "",
            "## Disclosure Drafts",
            "",
            "| field | status | draft text |",
            "|---|---|---|",
        ]
    )
    for row in report["disclosure_rows"]:
        lines.append(f"| {row['field']} | {row['status']} | {row['draft_text']} |")
    lines.extend(
        [
            "",
            "## Submission Fields",
            "",
            "| field | status | value/source |",
            "|---|---|---|",
        ]
    )
    for row in report["submission_fields"]:
        value = row["value"] or row["source"]
        lines.append(f"| {row['field']} | {row['status']} | {value} |")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export journal submission metadata draft.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_report(root)
    out_json = materials / "SUBMISSION_METADATA_DRAFT.json"
    out_md = materials / "SUBMISSION_METADATA_DRAFT.md"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    author_csv, contribution_csv, disclosure_csv = write_csv(report, materials)
    print(
        json.dumps(
            {
                "json": str(out_json),
                "markdown": str(out_md),
                "author_csv": str(author_csv),
                "credit_csv": str(contribution_csv),
                "disclosure_csv": str(disclosure_csv),
                "status": report["summary"]["status"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
