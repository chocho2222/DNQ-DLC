#!/usr/bin/env python
import argparse
import csv
import json
import re
from pathlib import Path


SCAN_FILES = [
    "manuscript/main.md",
    "manuscript/main.tex",
    "manuscript/SOURCE_PACKAGE_README.md",
    "materials/COVER_LETTER_DRAFT_PACKAGE.md",
    "materials/SUBMISSION_METADATA_DRAFT.md",
    "materials/SUBMISSION_PORTAL_FIELD_COMPLETION_PACK.md",
    "materials/DATA_CODE_AVAILABILITY.md",
    "materials/ARCHIVE_README.md",
    "materials/CITATION_METADATA.md",
    "materials/REPRODUCTION_GUIDE.md",
    "materials/RELEASE_ARCHIVE_MANIFEST.md",
]

PATTERNS = [
    ("absolute_local_path", re.compile(r"/home/[^\s`),;]+|/mnt/[^\s`),;]+|/data/[^\s`),;]+")),
    ("email_like", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    ("orcid_like", re.compile(r"\b\d{4}-\d{4}-\d{4}-\d{3}[0-9X]\b")),
    ("doi_like", re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Za-z0-9]+\b")),
    ("acknowledgement_label", re.compile(r"\backnowledg(e)?ments?\b", re.IGNORECASE)),
    ("author_label", re.compile(r"\b(author|affiliation|corresponding author|credit|CRediT)\b", re.IGNORECASE)),
    ("repository_or_archive", re.compile(r"\b(GitHub|Zenodo|Figshare|OSF|DOI|accession|archive)\b", re.IGNORECASE)),
]


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def clean(text):
    return " ".join(str(text).split())


def match_snippets(path, text):
    rows = []
    lines = text.splitlines()
    for line_no, line in enumerate(lines, start=1):
        for pattern_id, pattern in PATTERNS:
            if pattern.search(line):
                rows.append(
                    {
                        "file": str(path),
                        "line": line_no,
                        "pattern_id": pattern_id,
                        "snippet": clean(line)[:260],
                    }
                )
    return rows


def decision_row(row_id, area, status, files, evidence, action, boundary, double_blind_relevance):
    return {
        "id": row_id,
        "area": area,
        "status": status,
        "files": files,
        "evidence": evidence,
        "author_action": action,
        "boundary": boundary,
        "double_blind_relevance": double_blind_relevance,
    }


def build_report(root):
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    smoke = load_json(root / "materials" / "PUBLICATION_SMOKE_TEST.json")
    metadata = load_json(root / "materials" / "SUBMISSION_METADATA_DRAFT.json")
    portal = load_json(root / "materials" / "SUBMISSION_PORTAL_FIELD_COMPLETION_PACK.json")
    availability = load_json(root / "materials" / "DATA_CODE_AVAILABILITY.json")
    citation = load_json(root / "materials" / "CITATION_METADATA.json")
    author_blockers = load_json(root / "materials" / "REMAINING_AUTHOR_BLOCKERS_MATRIX.json")

    scan_hits = []
    scanned_files = []
    missing_scan_files = []
    for rel in SCAN_FILES:
        path = root / rel
        if not path.exists():
            missing_scan_files.append(rel)
            continue
        scanned_files.append(rel)
        scan_hits.extend(match_snippets(rel, path.read_text(encoding="utf-8", errors="replace")))

    hit_counts = {}
    for hit in scan_hits:
        hit_counts[hit["pattern_id"]] = hit_counts.get(hit["pattern_id"], 0) + 1

    author_required = metadata["summary"]["author_required_count"] + portal["summary"]["author_required_count"]
    archive_pending = availability["summary"]["external_archive_pending"] or not citation["summary"]["external_doi_present"]

    rows = [
        decision_row(
            "BR01_manuscript_source",
            "manuscript",
            "ready_with_author_blind_review_decision",
            "manuscript/main.md; manuscript/main.tex",
            "manuscript/manuscript_manifest.json; materials/MANUSCRIPT_SOURCE_PACKAGE_AUDIT.md",
            "If the target venue requires double-blind review, remove author names, affiliations, acknowledgements, and self-identifying repository links from the review manuscript copy.",
            "Do not alter the archival source package unless the journal explicitly requires an anonymized source upload.",
            "high",
        ),
        decision_row(
            "BR02_cover_letter",
            "cover_letter",
            "single_blind_or_editor_only",
            "materials/COVER_LETTER_DRAFT_PACKAGE.md",
            "materials/COVER_LETTER_AUTHOR_CHECKLIST.csv",
            "Keep cover letter outside reviewer-facing materials when the journal uses double-blind peer review.",
            "Cover letters are editor-facing and may contain author-certified declarations after author completion.",
            "medium",
        ),
        decision_row(
            "BR03_author_metadata",
            "author_metadata",
            "author_required",
            "materials/SUBMISSION_METADATA_AUTHORS.csv; materials/SUBMISSION_METADATA_CREDIT.csv; materials/SUBMISSION_METADATA_DISCLOSURES.csv",
            "materials/SUBMISSION_METADATA_DRAFT.json",
            "Complete certified metadata only in the journal portal or non-reviewer-facing administrative files.",
            "Automation cannot certify names, ORCIDs, affiliations, funding, conflicts, or CRediT roles.",
            "high",
        ),
        decision_row(
            "BR04_archive_identifiers",
            "archive",
            "ready_pending_external_archive",
            "materials/DATA_CODE_AVAILABILITY.md; materials/CITATION_METADATA.md; materials/ARCHIVE_README.md",
            "materials/EXTERNAL_ARCHIVE_PREFLIGHT.md; materials/FAIR_ARCHIVE_METADATA.md",
            "For double-blind review, use the journal's anonymous data-access mechanism if required; add public DOI/URL only after the allowed stage.",
            "External archive deposition remains author-owned and must not be implied before completion.",
            "high",
        ),
        decision_row(
            "BR05_local_paths",
            "local_paths",
            "review_before_public_upload",
            "; ".join(scanned_files),
            "materials/BLINDED_REVIEW_ANONYMIZATION_AUDIT.csv",
            "Replace absolute local paths with relative package paths in any reviewer-facing copy if the target venue treats paths as identifying metadata.",
            "Local path hits in internal audit files do not invalidate simulator evidence.",
            "medium",
        ),
        decision_row(
            "BR06_reviewer_package",
            "reviewer_package",
            "ready_with_target_journal_policy_check",
            "materials/REVIEWER_QUICKLOOK_PACKET.md; materials/REPORTING_SUPPLEMENT_NAVIGATOR.md",
            "materials/PUBLICATION_SMOKE_TEST.md; materials/PUBLICATION_PACKAGE_VERIFICATION.md",
            "Select an anonymized subset only after the target journal policy is known; keep full checksums for the non-anonymous archive copy.",
            "This audit is journal-neutral and does not certify compliance with a specific double-blind policy.",
            "medium",
        ),
    ]

    status_counts = {}
    for item in rows:
        status_counts[item["status"]] = status_counts.get(item["status"], 0) + 1

    return {
        "root": str(root),
        "title": "Blinded Review and Anonymization Audit",
        "purpose": (
            "Provide a journal-neutral double-blind/single-blind readiness audit that separates reviewer-facing "
            "materials, editor-only files, author-certified metadata, archive identifiers, and local path exposure."
        ),
        "summary": {
            "status": "pass" if not missing_scan_files else "review_required",
            "row_count": len(rows),
            "status_counts": status_counts,
            "scanned_file_count": len(scanned_files),
            "missing_scan_file_count": len(missing_scan_files),
            "scan_hit_count": len(scan_hits),
            "scan_hit_counts": hit_counts,
            "author_required_count": author_required,
            "remaining_author_blockers": author_blockers["summary"]["author_required_count"],
            "external_archive_pending": archive_pending,
            "publication_verification_status": verification["summary"]["status"],
            "publication_smoke_test_reference": "materials/PUBLICATION_SMOKE_TEST.json",
        },
        "rows": rows,
        "scan_hits": scan_hits,
        "missing_scan_files": missing_scan_files,
        "interpretation": (
            "This audit does not anonymize files automatically. It identifies review-stage risks and author actions "
            "so the authors can prepare either a double-blind reviewer package or a standard non-blind submission package."
        ),
    }


def write_csv(report, path):
    fields = [
        "id",
        "area",
        "status",
        "files",
        "evidence",
        "author_action",
        "boundary",
        "double_blind_relevance",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in report["rows"]:
            writer.writerow({field: row.get(field, "") for field in fields})


def write_hits_csv(report, path):
    fields = ["file", "line", "pattern_id", "snippet"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in report["scan_hits"]:
            writer.writerow({field: row.get(field, "") for field in fields})


def write_markdown(report, path):
    lines = [
        "# Blinded Review and Anonymization Audit",
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
            "| id | area | status | files | author action | boundary |",
            "|---|---|---|---|---|---|",
        ]
    )
    for row in report["rows"]:
        lines.append(
            f"| {row['id']} | {row['area']} | {row['status']} | `{row['files']}` | "
            f"{row['author_action']} | {row['boundary']} |"
        )
    lines.extend(
        [
            "",
            "## Scan Hit Summary",
            "",
            "| pattern | count |",
            "|---|---:|",
        ]
    )
    for key, value in sorted(report["summary"]["scan_hit_counts"].items()):
        lines.append(f"| {key} | {value} |")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export blinded review and anonymization readiness audit.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_report(root)
    out_json = materials / "BLINDED_REVIEW_ANONYMIZATION_AUDIT.json"
    out_md = materials / "BLINDED_REVIEW_ANONYMIZATION_AUDIT.md"
    out_csv = materials / "BLINDED_REVIEW_ANONYMIZATION_AUDIT.csv"
    hits_csv = materials / "BLINDED_REVIEW_ANONYMIZATION_SCAN_HITS.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    write_hits_csv(report, hits_csv)
    print(
        json.dumps(
            {
                "json": str(out_json),
                "markdown": str(out_md),
                "csv": str(out_csv),
                "hits_csv": str(hits_csv),
                "summary": report["summary"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
