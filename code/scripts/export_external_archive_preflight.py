#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


AUTHOR_REQUIRED_FIELDS = [
    {
        "field": "external_doi_or_url",
        "status": "author_required",
        "reason": "A public DOI, repository URL, or accession cannot be minted by the local exporter.",
    },
    {
        "field": "creator_orcid_affiliations",
        "status": "author_required",
        "reason": "AUTHORS provides names only; final ORCID and affiliation metadata require author confirmation.",
    },
    {
        "field": "funding_and_awards",
        "status": "author_required",
        "reason": "Funding metadata are not present in the repository.",
    },
    {
        "field": "related_identifiers",
        "status": "author_required",
        "reason": "Final manuscript DOI, preprint DOI, or GitHub release URL must be added after public release.",
    },
]

SELF_DESCRIBING_EXCLUSIONS = {
    "materials/RELEASE_ARCHIVE_MANIFEST.md",
    "materials/RELEASE_ARCHIVE_MANIFEST.json",
    "materials/RELEASE_ARCHIVE_MANIFEST.csv",
    "materials/PUBLICATION_PACKAGE_VERIFICATION.md",
    "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
    "materials/PUBLICATION_PACKAGE_VERIFICATION.csv",
    "materials/PUBLICATION_SMOKE_TEST.md",
    "materials/PUBLICATION_SMOKE_TEST.json",
    "materials/PUBLICATION_SMOKE_TEST.csv",
    "materials/FINAL_CHECKSUM_FREEZE_RECORD.md",
    "materials/FINAL_CHECKSUM_FREEZE_RECORD.json",
    "materials/FINAL_CHECKSUM_FREEZE_RECORD.csv",
    "materials/FINAL_CHECKSUM_FREEZE_FILE_SNAPSHOTS.csv",
    "materials/FAIR_ARCHIVE_METADATA.md",
    "materials/FAIR_ARCHIVE_METADATA.json",
    "materials/FAIR_ARCHIVE_METADATA.csv",
    "materials/ARCHIVE_MANIFEST_EXCLUSION_AUDIT.md",
    "materials/ARCHIVE_MANIFEST_EXCLUSION_AUDIT.json",
    "materials/ARCHIVE_MANIFEST_EXCLUSION_AUDIT.csv",
    "materials/EXTERNAL_ARCHIVE_PREFLIGHT.md",
    "materials/EXTERNAL_ARCHIVE_PREFLIGHT.json",
    "materials/EXTERNAL_ARCHIVE_PREFLIGHT_ROWS.csv",
    "materials/EXTERNAL_ARCHIVE_KEY_FILES.csv",
    "materials/ARCHIVE_README.md",
    "materials/ARCHIVE_README.json",
    "materials/ARCHIVE_README.csv",
    "materials/FINAL_SUBMISSION_FILE_BUNDLE.md",
    "materials/FINAL_SUBMISSION_FILE_BUNDLE.json",
    "materials/FINAL_SUBMISSION_FILE_BUNDLE.csv",
    "materials/CITATION_METADATA.md",
    "materials/CITATION_METADATA.json",
    "materials/CITATION_METADATA.csv",
    "materials/CITATION.cff",
    "materials/CITATION.bib",
    "materials/SUBMISSION_READINESS_DASHBOARD.md",
    "materials/SUBMISSION_READINESS_DASHBOARD.json",
    "materials/SUBMISSION_READINESS_DASHBOARD.csv",
    "materials/REPORTING_SUPPLEMENT_NAVIGATOR.md",
    "materials/REPORTING_SUPPLEMENT_NAVIGATOR.json",
    "materials/REPORTING_SUPPLEMENT_NAVIGATOR.csv",
    "materials/SUBMISSION_UPLOAD_SELECTION_PLAN.md",
    "materials/SUBMISSION_UPLOAD_SELECTION_PLAN.json",
    "materials/SUBMISSION_UPLOAD_SELECTION_PLAN.csv",
    "materials/TOP_JOURNAL_REPORTING_SUMMARY.md",
    "materials/TOP_JOURNAL_REPORTING_SUMMARY.json",
    "materials/TOP_JOURNAL_REPORTING_SUMMARY.csv",
    "materials/SUBMISSION_PORTAL_PACKAGE_MAP.md",
    "materials/SUBMISSION_PORTAL_PACKAGE_MAP.json",
    "materials/SUBMISSION_PORTAL_PACKAGE_MAP.csv",
    "materials/EDITORIAL_SUBMISSION_CHECKLIST.md",
    "materials/EDITORIAL_SUBMISSION_CHECKLIST.json",
    "materials/EDITORIAL_SUBMISSION_CHECKLIST.csv",
    "materials/EDITORIAL_TRIAGE_AND_REVIEWER_CHECKLIST.md",
    "materials/EDITORIAL_TRIAGE_AND_REVIEWER_CHECKLIST.json",
    "materials/EDITORIAL_TRIAGE_AND_REVIEWER_CHECKLIST.csv",
    "materials/TARGET_JOURNAL_COMPLIANCE_MATRIX.md",
    "materials/TARGET_JOURNAL_COMPLIANCE_MATRIX.json",
    "materials/TARGET_JOURNAL_COMPLIANCE_MATRIX.csv",
    "materials/REVIEWER_RISK_RESPONSE_DOSSIER.md",
    "materials/REVIEWER_RISK_RESPONSE_DOSSIER.json",
    "materials/REVIEWER_RISK_RESPONSE_DOSSIER.csv",
    "materials/SOFTWARE_DEPENDENCY_LICENSE_AUDIT.md",
    "materials/SOFTWARE_DEPENDENCY_LICENSE_AUDIT.json",
    "materials/SOFTWARE_DEPENDENCY_LICENSE_AUDIT.csv",
    "materials/ARTIFACT_DEPENDENCY_MAP.md",
    "materials/ARTIFACT_DEPENDENCY_MAP.json",
    "materials/ARTIFACT_DEPENDENCY_MAP.csv",
}


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def build_report(root):
    fair = load_json(root / "materials" / "FAIR_ARCHIVE_METADATA.json")
    release = load_json(root / "materials" / "RELEASE_ARCHIVE_MANIFEST.json")
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    dictionary = load_json(root / "materials" / "DATA_DICTIONARY.json")
    reference = load_json(root / "materials" / "REFERENCE_READINESS_AUDIT.json")

    recommended_patterns = release["recommended_archive_contents"]
    release_paths = {row["path"] for row in release["files"]}
    key_paths = [
        "manifest.json",
        "materials/README.md",
        "materials/REPRODUCTION_GUIDE.md",
        "materials/PUBLICATION_PACKAGE_VERIFICATION.md",
        "materials/RELEASE_ARCHIVE_MANIFEST.json",
        "materials/RELEASE_ARCHIVE_MANIFEST.csv",
        "materials/FAIR_ARCHIVE_METADATA.md",
        "materials/DATA_DICTIONARY.md",
        "materials/REFERENCE_READINESS_AUDIT.md",
        "tables/artifact_provenance.md",
        "tables/reproducibility_audit.md",
        "manuscript/main.md",
        "manuscript/references.bib",
        "figures/figure_1_source_data.csv",
        "figures/figure_2_source_data.csv",
        "figures/figure_3_source_data.csv",
    ]
    key_rows = []
    for path in key_paths:
        exists = (root / path).exists()
        in_release = path in release_paths
        self_excluded = path in SELF_DESCRIBING_EXCLUSIONS
        status = "pass" if exists and (in_release or self_excluded) else "review"
        note = "Key archive file is present and checksummed."
        if self_excluded:
            note = "Self-describing manifest, gate, smoke, freeze, or metadata output is intentionally excluded from checksum rows to avoid drift."
        elif status != "pass":
            note = "Check archive inclusion."
        key_rows.append(
            {
                "path": path,
                "exists": exists,
                "in_release_manifest": in_release,
                "status": status,
                "note": note,
            }
        )

    preflight_rows = [
        {
            "id": "P01_release_manifest",
            "category": "integrity",
            "status": "pass" if release["summary"]["file_count"] > 0 else "fail",
            "evidence": "materials/RELEASE_ARCHIVE_MANIFEST.json",
            "action": "Regenerate immediately before external upload.",
        },
        {
            "id": "P02_publication_verification",
            "category": "verification",
            "status": "pass" if (root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json").exists() else "fail",
            "evidence": "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
            "action": "Rerun publication verification after archive metadata changes and upload only after failed gates are zero.",
        },
        {
            "id": "P03_data_dictionary",
            "category": "metadata",
            "status": "pass" if dictionary["summary"]["complete"] else "fail",
            "evidence": "materials/DATA_DICTIONARY.json",
            "action": "Keep DATA_DICTIONARY.* in the archive.",
        },
        {
            "id": "P04_reference_readiness",
            "category": "manuscript",
            "status": "pass" if reference["summary"]["status"] == "pass" else "fail",
            "evidence": "materials/REFERENCE_READINESS_AUDIT.json",
            "action": "Expand domain-specific related work before final manuscript submission.",
        },
        {
            "id": "P05_external_identifier",
            "category": "repository",
            "status": "author_required" if fair["availability"]["external_archive_pending"] else "pass",
            "evidence": "materials/FAIR_ARCHIVE_METADATA.json",
            "action": "Mint DOI/accession in the external archive and update FAIR/DATA_CODE materials.",
        },
        {
            "id": "P06_author_metadata",
            "category": "repository",
            "status": "author_required",
            "evidence": "AUTHORS; materials/FAIR_ARCHIVE_METADATA.json",
            "action": "Confirm creator order, affiliations, ORCID identifiers, and funding metadata.",
        },
    ]

    zenodo_metadata = {
        "upload_type": "dataset",
        "title": fair["title"],
        "creators": [
            {"name": creator["name"], "affiliation": "", "orcid": ""}
            for creator in fair["creators"]
        ],
        "description": fair["description"],
        "keywords": fair["keywords"],
        "license": fair["license"]["name"],
        "version": fair["version"]["package_label"],
        "related_identifiers": [],
        "notes": (
            "Local metadata draft. Fill affiliations, ORCID identifiers, funding, related identifiers, "
            "and the minted DOI/URL after uploading. Keep oracle and simulator-only claim boundaries."
        ),
    }

    failures = [row for row in preflight_rows if row["status"] == "fail"]
    author_required = [row for row in preflight_rows if row["status"] == "author_required"]
    return {
        "root": str(root),
        "title": "External Archive Preflight",
        "purpose": (
            "Prepare a local external-archive upload checklist and Zenodo-style metadata draft without minting a DOI."
        ),
        "summary": {
            "status": "pass" if not failures else "fail",
            "preflight_count": len(preflight_rows),
            "failed_count": len(failures),
            "author_required_count": len(author_required) + len(AUTHOR_REQUIRED_FIELDS),
            "recommended_pattern_count": len(recommended_patterns),
            "key_file_count": len(key_rows),
            "key_file_review_count": sum(1 for row in key_rows if row["status"] != "pass"),
            "release_file_count": release["summary"]["file_count"],
            "release_size_reference": "materials/RELEASE_ARCHIVE_MANIFEST.json",
            "publication_verification_status": verification["summary"]["status"],
            "artifact_provenance": verification["summary"]["artifact_provenance"],
            "external_archive_pending": fair["availability"]["external_archive_pending"],
        },
        "preflight_rows": preflight_rows,
        "author_required_fields": AUTHOR_REQUIRED_FIELDS,
        "recommended_archive_contents": recommended_patterns,
        "key_file_rows": key_rows,
        "zenodo_metadata_draft": zenodo_metadata,
        "interpretation": (
            "This report is a local preflight and metadata draft. It does not create a public repository record, "
            "DOI, accession, or final journal data-availability statement."
        ),
    }


def write_csv(report, materials):
    preflight_csv = materials / "EXTERNAL_ARCHIVE_PREFLIGHT_ROWS.csv"
    key_csv = materials / "EXTERNAL_ARCHIVE_KEY_FILES.csv"
    with preflight_csv.open("w", newline="", encoding="utf-8") as handle:
        fields = ["id", "category", "status", "evidence", "action"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(report["preflight_rows"])
        for row in report["author_required_fields"]:
            writer.writerow(
                {
                    "id": row["field"],
                    "category": "author_metadata",
                    "status": row["status"],
                    "evidence": "",
                    "action": row["reason"],
                }
            )
    with key_csv.open("w", newline="", encoding="utf-8") as handle:
        fields = ["path", "exists", "in_release_manifest", "status", "note"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(report["key_file_rows"])
    return preflight_csv, key_csv


def write_markdown(report, path):
    lines = [
        "# External Archive Preflight",
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
            "## Preflight Checks",
            "",
            "| id | category | status | evidence | action |",
            "|---|---|---|---|---|",
        ]
    )
    for row in report["preflight_rows"]:
        lines.append(f"| {row['id']} | {row['category']} | {row['status']} | `{row['evidence']}` | {row['action']} |")
    lines.extend(
        [
            "",
            "## Author-required Fields",
            "",
            "| field | status | reason |",
            "|---|---|---|",
        ]
    )
    for row in report["author_required_fields"]:
        lines.append(f"| {row['field']} | {row['status']} | {row['reason']} |")
    lines.extend(
        [
            "",
            "## Zenodo-style Metadata Draft",
            "",
            "```json",
            json.dumps(report["zenodo_metadata_draft"], indent=2),
            "```",
            "",
            "## Key File Review",
            "",
            "Full rows are available in `materials/EXTERNAL_ARCHIVE_KEY_FILES.csv`.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export external archive preflight and metadata draft.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_report(root)
    out_json = materials / "EXTERNAL_ARCHIVE_PREFLIGHT.json"
    out_md = materials / "EXTERNAL_ARCHIVE_PREFLIGHT.md"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    preflight_csv, key_csv = write_csv(report, materials)
    print(
        json.dumps(
            {
                "json": str(out_json),
                "markdown": str(out_md),
                "preflight_csv": str(preflight_csv),
                "key_csv": str(key_csv),
                "status": report["summary"]["status"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
