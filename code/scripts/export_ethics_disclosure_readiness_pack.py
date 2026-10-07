#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def row(section, item, status, draft_text, author_action, evidence, boundary):
    return {
        "section": section,
        "item": item,
        "status": status,
        "draft_text": draft_text,
        "author_action": author_action,
        "evidence": evidence,
        "boundary": boundary,
    }


def build_report(root):
    metadata = load_json(root / "materials" / "SUBMISSION_METADATA_DRAFT.json")
    risk = load_json(root / "materials" / "RESEARCH_RISK_AND_SAFETY.json")
    sim2real = load_json(root / "materials" / "SIMULATION_TO_REAL_APPLICABILITY.json")
    portal_fields = load_json(root / "materials" / "SUBMISSION_PORTAL_FIELD_COMPLETION_PACK.json")
    license_audit = load_json(root / "materials" / "SOFTWARE_DEPENDENCY_LICENSE_AUDIT.json")
    data_code = load_json(root / "materials" / "DATA_CODE_AVAILABILITY.json")
    archive = load_json(root / "materials" / "EXTERNAL_ARCHIVE_PREFLIGHT.json")
    fair = load_json(root / "materials" / "FAIR_ARCHIVE_METADATA.json")
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    provenance = load_json(root / "tables" / "artifact_provenance.json")
    dashboard = load_json(root / "materials" / "SUBMISSION_READINESS_DASHBOARD.json")
    blockers = load_json(root / "materials" / "REMAINING_AUTHOR_BLOCKERS_MATRIX.json")

    disclosure_by_field = {item["field"]: item for item in metadata["disclosure_rows"]}
    portal_by_field = {item["portal_field"]: item for item in portal_fields["fields"]}

    rows = [
        row(
            "ethics",
            "human_subjects",
            "package_supported",
            "Not applicable: the package contains simulator rollouts and generated telemetry only.",
            "Confirm target-journal wording before submission.",
            "materials/RESEARCH_RISK_AND_SAFETY.md",
            risk["ethics_context"]["rationale"],
        ),
        row(
            "ethics",
            "animal_subjects",
            "package_supported",
            "Not applicable: no animal data or experiments are included.",
            "Confirm target-journal wording before submission.",
            "materials/RESEARCH_RISK_AND_SAFETY.md",
            "No animal data are present in the saved package.",
        ),
        row(
            "ethics",
            "personal_data",
            "package_supported",
            "Not applicable: no personal data are included.",
            "Confirm target-journal wording before submission.",
            "materials/RESEARCH_RISK_AND_SAFETY.md; materials/DATA_CODE_AVAILABILITY.md",
            "This does not certify external datasets beyond the local package.",
        ),
        row(
            "ethics",
            "real_world_testing",
            "package_supported_with_required_boundary",
            "No real-vehicle, public-road, or human-participant testing is reported.",
            "Preserve this simulator-only wording in the final manuscript and portal forms.",
            "materials/RESEARCH_RISK_AND_SAFETY.md; materials/SIMULATION_TO_REAL_APPLICABILITY.md",
            "No real-road readiness, perception robustness, or safety-certification claim is supported.",
        ),
        row(
            "disclosures",
            "competing_interests",
            disclosure_by_field["competing_interests"]["status"],
            disclosure_by_field["competing_interests"]["draft_text"],
            "Authors must certify the competing-interest statement.",
            disclosure_by_field["competing_interests"]["evidence"],
            "Local automation cannot certify author conflicts.",
        ),
        row(
            "disclosures",
            "funding",
            disclosure_by_field["funding"]["status"],
            disclosure_by_field["funding"]["draft_text"],
            "Authors must add funder names, grant numbers, or certify no specific funding.",
            disclosure_by_field["funding"]["evidence"],
            "Do not invent funders or grant identifiers.",
        ),
        row(
            "disclosures",
            "acknowledgements",
            disclosure_by_field["acknowledgements"]["status"],
            disclosure_by_field["acknowledgements"]["draft_text"],
            "Authors must confirm acknowledgements.",
            disclosure_by_field["acknowledgements"]["evidence"],
            "Do not infer acknowledgements from repository files.",
        ),
        row(
            "author_metadata",
            "authors_affiliations_orcid_email",
            "author_required",
            f"{metadata['summary']['author_count']} author name rows parsed; affiliations, ORCID identifiers, emails, and corresponding author flags are blank.",
            "Authors must complete and certify all author metadata.",
            "materials/SUBMISSION_METADATA_DRAFT.md; materials/SUBMISSION_METADATA_AUTHORS.csv",
            "Repository author names are not a complete submission metadata record.",
        ),
        row(
            "author_metadata",
            "credit_roles",
            "author_required",
            f"{metadata['summary']['credit_role_count']} CRediT roles listed with empty suggested contributors.",
            "Authors must assign contribution roles.",
            "materials/SUBMISSION_METADATA_CREDIT.csv",
            "Do not infer contribution roles from commit history or file ownership.",
        ),
        row(
            "availability",
            "data_availability",
            "package_supported_pending_archive",
            data_code["data_availability"],
            "Insert final public DOI/URL/accession after archive deposition.",
            "materials/DATA_CODE_AVAILABILITY.md; materials/EXTERNAL_ARCHIVE_PREFLIGHT.md",
            "Local package availability is not a public archive record.",
        ),
        row(
            "availability",
            "code_availability",
            "package_supported_pending_archive",
            data_code["code_availability"],
            "Insert final public DOI/URL/accession after archive deposition.",
            "materials/DATA_CODE_AVAILABILITY.md; materials/REPRODUCTION_GUIDE.md",
            "Local reproduction files do not replace public deposition if required by the journal.",
        ),
        row(
            "availability",
            "archive_identifier",
            "author_required",
            f"External DOI present={fair['identifier']['external_doi']}; external URL present={fair['identifier']['external_url']}.",
            "Deposit the package and update all archive-dependent fields.",
            "materials/FAIR_ARCHIVE_METADATA.md; materials/EXTERNAL_ARCHIVE_PREFLIGHT.md",
            "Do not claim a DOI/accession until it exists.",
        ),
        row(
            "license",
            "repository_license",
            "ready_with_author_review",
            f"Repository license recorded as {license_audit['summary']['repository_license']}.",
            "Author or institution should confirm final third-party license handling.",
            "materials/SOFTWARE_DEPENDENCY_LICENSE_AUDIT.md",
            "Local license audit is not legal advice.",
        ),
        row(
            "license",
            "third_party_dependencies",
            "ready_with_author_review",
            f"{license_audit['summary']['dependency_count']} dependency rows audited.",
            "Confirm journal/archive requirements for dependency notices.",
            "materials/SOFTWARE_DEPENDENCY_LICENSE_DEPENDENCIES.csv",
            "Dependency metadata may need final legal or institutional review.",
        ),
        row(
            "claim_boundaries",
            "simulation_only_wording",
            "ready",
            "; ".join(risk["required_submission_wording"]),
            "Copy the relevant wording into final manuscript, cover letter, and portal fields.",
            "materials/RESEARCH_RISK_AND_SAFETY.md; materials/CLAIM_EVIDENCE_MATRIX.md",
            "Simulator evidence does not imply real-road deployment readiness.",
        ),
        row(
            "claim_boundaries",
            "simulation_to_real_limit",
            "ready",
            "; ".join(sim2real["required_wording"]),
            "Preserve these applicability limits in final prose.",
            "materials/SIMULATION_TO_REAL_APPLICABILITY.md",
            "No VLM autonomy, perception-stack robustness, or safety certification is evidenced.",
        ),
        row(
            "portal",
            "ethics_statement_field",
            portal_by_field["ethics_statement"]["status"],
            portal_by_field["ethics_statement"]["draft_value"],
            portal_by_field["ethics_statement"]["author_action"],
            "materials/SUBMISSION_PORTAL_FIELD_COMPLETION_PACK.md",
            portal_by_field["ethics_statement"]["claim_boundary"],
        ),
        row(
            "portal",
            "competing_interests_field",
            portal_by_field["competing_interests"]["status"],
            portal_by_field["competing_interests"]["draft_value"],
            portal_by_field["competing_interests"]["author_action"],
            "materials/SUBMISSION_PORTAL_FIELD_COMPLETION_PACK.md",
            portal_by_field["competing_interests"]["claim_boundary"],
        ),
        row(
            "portal",
            "funding_field",
            portal_by_field["funding"]["status"],
            portal_by_field["funding"]["draft_value"],
            portal_by_field["funding"]["author_action"],
            "materials/SUBMISSION_PORTAL_FIELD_COMPLETION_PACK.md",
            portal_by_field["funding"]["claim_boundary"],
        ),
    ]

    author_required = [item for item in rows if item["status"] == "author_required"]
    archive_dependent = [item for item in rows if "pending_archive" in item["status"]]
    package_supported = [
        item
        for item in rows
        if item["status"] in {"package_supported", "ready", "package_supported_with_required_boundary"}
    ]

    return {
        "root": str(root),
        "title": "Ethics and Disclosure Readiness Pack",
        "purpose": (
            "Consolidate ethics, disclosure, author-metadata, availability, license, portal, and claim-boundary "
            "items for top-journal submission without certifying author-owned information."
        ),
        "rows": rows,
        "summary": {
            "status": "ready_with_author_completion",
            "row_count": len(rows),
            "package_supported_count": len(package_supported),
            "author_required_count": len(author_required),
            "archive_dependent_count": len(archive_dependent),
            "metadata_author_required_count": metadata["summary"]["author_required_count"],
            "portal_author_required_count": portal_fields["summary"]["author_required_count"],
            "remaining_author_required_count": blockers["summary"]["author_required_count"],
            "external_archive_pending": archive["summary"]["external_archive_pending"],
            "publication_verification_status": verification["summary"]["status"],
            "artifact_provenance": f"{provenance['complete_count']}/{len(provenance['artifacts'])}",
            "submission_dashboard_review_required": dashboard["summary"]["review_required_row_count"],
        },
        "interpretation": (
            "This pack is a disclosure-readiness aid. It separates package-supported statements from author-certified "
            "metadata and does not fill in conflicts, funding, affiliations, ORCID identifiers, or public archive identifiers."
        ),
    }


def write_csv(report, path):
    fields = ["section", "item", "status", "draft_text", "author_action", "evidence", "boundary"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(report["rows"])


def write_markdown(report, path):
    lines = [
        "# Ethics and Disclosure Readiness Pack",
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
            "| section | item | status | draft text | author action | evidence | boundary |",
            "|---|---|---|---|---|---|---|",
        ]
    )
    for item in report["rows"]:
        lines.append(
            f"| {item['section']} | {item['item']} | {item['status']} | {item['draft_text']} | "
            f"{item['author_action']} | `{item['evidence']}` | {item['boundary']} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export ethics and disclosure readiness pack.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_report(root)
    out_json = materials / "ETHICS_DISCLOSURE_READINESS_PACK.json"
    out_md = materials / "ETHICS_DISCLOSURE_READINESS_PACK.md"
    out_csv = materials / "ETHICS_DISCLOSURE_READINESS_PACK.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv), "summary": report["summary"]}, indent=2))


if __name__ == "__main__":
    main()
