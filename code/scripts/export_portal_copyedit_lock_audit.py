#!/usr/bin/env python
import argparse
import csv
import json
import re
from pathlib import Path


PROHIBITED_PATTERNS = [
    ("real_road_readiness", r"\breal[- ]?(road|world)\s+(ready|readiness|deployment|deployed)\b"),
    ("public_road", r"\bpublic[- ]road\b|\bon[- ]road\b"),
    ("safety_certification", r"\bsafety\s+(certification|certified|guarantee|guaranteed)\b"),
    ("broad_robustness", r"\b(broad|general|universal)\s+robust(ness)?\b"),
    ("vlm_autonomy", r"\bVLM\s+(autonomy|controller|driving|policy)\b"),
    ("oracle_controller", r"\boracle\s+(controller|policy|deployable|online)\b"),
    ("heldout3_external_validation", r"\bheldout3\b.{0,80}\bexternal validation\b"),
]

REQUIRED_BOUNDARY_TERMS = [
    "simulator",
    "diagnostic",
    "heldout",
]

ADMIN_PORTAL_FIELDS = {
    "competing_interests",
    "funding",
    "acknowledgements",
    "author_metadata",
    "credit_contributions",
    "archive_doi_or_url",
    "journal_upload_files",
}

ARCHIVE_PORTAL_FIELDS = {
    "data_availability_statement",
    "code_availability_statement",
}

ADMIN_BOUNDARY_TERMS = [
    "author",
    "confirmation",
    "required",
    "orcid",
    "credit",
    "archive",
    "doi",
    "url",
    "accession",
    "pending",
    "template",
    "selection",
]

NEGATION_CUES = [
    "not ",
    "no ",
    "does not ",
    "does not include ",
    "do not ",
    "must not ",
    "cannot ",
    "is not ",
    "not evidence of ",
    "avoid ",
    "without ",
]


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def clean(text):
    return " ".join(str(text).split())


def add_text(rows, source_file, text_id, text_type, text):
    value = clean(text)
    if value:
        rows.append(
            {
                "source_file": source_file,
                "text_id": text_id,
                "text_type": text_type,
                "text": value,
            }
        )


def collect_texts(root):
    rows = []
    shortform = load_json(root / "materials" / "TITLE_ABSTRACT_HIGHLIGHTS_PACKAGE.json")
    cover = load_json(root / "materials" / "COVER_LETTER_DRAFT_PACKAGE.json")
    narrative = load_json(root / "materials" / "EDITORIAL_NARRATIVE_PACKAGE.json")
    portal = load_json(root / "materials" / "SUBMISSION_PORTAL_FIELD_COMPLETION_PACK.json")

    for item in shortform.get("title_options", []):
        add_text(rows, "materials/TITLE_ABSTRACT_HIGHLIGHTS_PACKAGE.json", item.get("id", "title"), "title_option", item.get("text", ""))
    for item in shortform.get("structured_abstract", []):
        add_text(rows, "materials/TITLE_ABSTRACT_HIGHLIGHTS_PACKAGE.json", item.get("section", "abstract"), "abstract", item.get("text", ""))
    for item in shortform.get("highlights", []):
        add_text(rows, "materials/TITLE_ABSTRACT_HIGHLIGHTS_PACKAGE.json", item.get("id", "highlight"), "highlight", item.get("text", ""))
    for item in shortform.get("plain_language_summary", []):
        add_text(rows, "materials/TITLE_ABSTRACT_HIGHLIGHTS_PACKAGE.json", item.get("id", "plain_language"), "plain_language", item.get("text", ""))

    for item in cover.get("paragraphs", []):
        add_text(rows, "materials/COVER_LETTER_DRAFT_PACKAGE.json", item.get("id", "cover_paragraph"), "cover_letter", item.get("text", ""))
    add_text(rows, "materials/EDITORIAL_NARRATIVE_PACKAGE.json", "one_sentence_pitch", "editorial_pitch", narrative.get("one_sentence_pitch", ""))
    for item in narrative.get("narrative_threads", []):
        add_text(rows, "materials/EDITORIAL_NARRATIVE_PACKAGE.json", item.get("id", "narrative_thread"), "editorial_narrative", item.get("text", ""))
    for item in portal.get("fields", []):
        add_text(rows, "materials/SUBMISSION_PORTAL_FIELD_COMPLETION_PACK.json", item.get("portal_field", "portal_field"), "portal_field", item.get("draft_value", ""))
    return rows


def scan_row(item):
    text = item["text"]
    hits = []
    for name, pattern in PROHIBITED_PATTERNS:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            continue
        context = text[max(0, match.start() - 180) : min(len(text), match.end() + 70)].lower()
        if not any(cue in context for cue in NEGATION_CUES):
            hits.append(name)
    lower = text.lower()
    boundary_present = any(term in lower for term in REQUIRED_BOUNDARY_TERMS)
    admin_boundary_present = any(term in lower for term in ADMIN_BOUNDARY_TERMS)
    is_admin_portal = item["text_type"] == "portal_field" and item["text_id"] in ADMIN_PORTAL_FIELDS
    is_archive_portal = item["text_type"] == "portal_field" and item["text_id"] in ARCHIVE_PORTAL_FIELDS
    if hits:
        status = "blocker"
        action = "Revise wording before submission; route replacement wording through CLAIM_DOWNGRADE_MAP."
    elif is_admin_portal and admin_boundary_present:
        status = "pass"
        action = "Keep author-required or author-selection boundary visible during portal entry."
    elif is_archive_portal and admin_boundary_present:
        status = "pass"
        action = "Replace local archive wording only after a real DOI, URL, or accession exists."
    elif item["text_type"] in {"title_option", "highlight", "abstract", "cover_letter", "portal_field"} and not boundary_present:
        status = "caution"
        action = "Author style review should confirm nearby text preserves simulator-only and diagnostic boundaries."
    else:
        status = "pass"
        action = "Keep wording within the existing boundary during copyedit."
    return {
        **item,
        "prohibited_hits": ";".join(hits),
        "boundary_term_present": boundary_present,
        "status": status,
        "action": action,
    }


def build_report(root):
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    smoke = load_json(root / "materials" / "PUBLICATION_SMOKE_TEST.json")
    frontmatter = load_json(root / "materials" / "EDITORIAL_FRONTMATTER_CLAIM_AUDIT.json")
    claim_pack = load_json(root / "materials" / "CLAIM_BOUNDARY_COMMUNICATION_PACK.json")
    rows = [scan_row(item) for item in collect_texts(root)]
    blocker_count = sum(1 for row in rows if row["status"] == "blocker")
    caution_count = sum(1 for row in rows if row["status"] == "caution")
    status_counts = {}
    for row in rows:
        status_counts[row["status"]] = status_counts.get(row["status"], 0) + 1
    return {
        "root": str(root),
        "title": "Portal Copyedit Lock Audit",
        "purpose": (
            "Conservatively scan journal-facing title, abstract, highlights, cover-letter, narrative, and portal-field "
            "draft text for wording that could escape the saved claim boundaries."
        ),
        "summary": {
            "status": "pass" if blocker_count == 0 else "review_required",
            "scanned_text_count": len(rows),
            "blocker_count": blocker_count,
            "caution_count": caution_count,
            "status_counts": status_counts,
            "publication_verification_status": verification["summary"]["status"],
            "publication_smoke_test_reference": "materials/PUBLICATION_SMOKE_TEST.json",
            "frontmatter_claim_audit_status": frontmatter["summary"]["status"],
            "claim_boundary_status": claim_pack["summary"]["status"],
        },
        "rows": rows,
        "patterns": [{"id": name, "pattern": pattern} for name, pattern in PROHIBITED_PATTERNS],
        "interpretation": (
            "A pass means no listed prohibited phrasing was detected in saved drafts. It does not certify final "
            "author-edited portal text, target-journal edits, or manuscript changes after this audit."
        ),
    }


def write_csv(report, path):
    fields = [
        "source_file",
        "text_id",
        "text_type",
        "text",
        "prohibited_hits",
        "boundary_term_present",
        "status",
        "action",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in report["rows"]:
            writer.writerow({field: row.get(field, "") for field in fields})


def write_markdown(report, path):
    lines = [
        "# Portal Copyedit Lock Audit",
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
            "## Scanned Text",
            "",
            "| source | id | type | status | hits | action |",
            "|---|---|---|---|---|---|",
        ]
    )
    for row in report["rows"]:
        lines.append(
            f"| `{row['source_file']}` | {row['text_id']} | {row['text_type']} | "
            f"{row['status']} | {row['prohibited_hits']} | {row['action']} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export portal copyedit lock audit.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_report(root)
    out_json = materials / "PORTAL_COPYEDIT_LOCK_AUDIT.json"
    out_md = materials / "PORTAL_COPYEDIT_LOCK_AUDIT.md"
    out_csv = materials / "PORTAL_COPYEDIT_LOCK_AUDIT.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv), "summary": report["summary"]}, indent=2))


if __name__ == "__main__":
    main()
