#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def clean(text):
    return " ".join(str(text).split())


def field_row(section, field, value, status, evidence, action, boundary, max_words=""):
    return {
        "portal_section": section,
        "portal_field": field,
        "draft_value": clean(value),
        "status": status,
        "evidence": evidence,
        "author_action": action,
        "claim_boundary": boundary,
        "max_words_or_format": max_words,
    }


def row_text(rows, row_id):
    for row in rows:
        if row["id"] == row_id:
            return row["text"]
    raise KeyError(row_id)


def build_report(root):
    shortform = load_json(root / "materials" / "TITLE_ABSTRACT_HIGHLIGHTS_PACKAGE.json")
    metadata = load_json(root / "materials" / "SUBMISSION_METADATA_DRAFT.json")
    portal = load_json(root / "materials" / "SUBMISSION_PORTAL_PACKAGE_MAP.json")
    upload = load_json(root / "materials" / "SUBMISSION_UPLOAD_SELECTION_PLAN.json")
    availability = load_json(root / "materials" / "DATA_CODE_AVAILABILITY.json")
    risk = load_json(root / "materials" / "RESEARCH_RISK_AND_SAFETY.json")
    sim2real = load_json(root / "materials" / "SIMULATION_TO_REAL_APPLICABILITY.json")
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    provenance = load_json(root / "tables" / "artifact_provenance.json")
    stats = load_json(root / "materials" / "STATISTICAL_CONSISTENCY_AUDIT.json")
    blockers = load_json(root / "materials" / "REMAINING_AUTHOR_BLOCKERS_MATRIX.json")

    abstract = " ".join(item["text"] for item in shortform["structured_abstract"])
    highlights = "\n".join(f"- {item['text']}" for item in shortform["highlights"])
    keywords = "; ".join(item["text"] for item in shortform["keywords"])
    title = row_text(shortform["title_options"], "T1_recommended")
    plain = "\n\n".join(item["text"] for item in shortform["plain_language_summary"])

    disclosure = {row["field"]: row for row in metadata["disclosure_rows"]}
    submission_fields = {row["field"]: row for row in metadata["submission_fields"]}
    ethics = disclosure["ethics_statement"]["draft_text"]
    data_availability = disclosure["data_availability"]["draft_text"]
    code_availability = disclosure["code_availability"]["draft_text"]

    fields = [
        field_row(
            "manuscript_information",
            "title",
            title,
            "copy_ready_with_author_style_review",
            "materials/TITLE_ABSTRACT_HIGHLIGHTS_PACKAGE.md",
            "Adapt capitalization and article-type style after target journal choice.",
            "Title frames strict evaluation and limits, not broad robustness.",
            "journal-specific",
        ),
        field_row(
            "manuscript_information",
            "abstract",
            abstract,
            "copy_ready_with_author_style_review",
            "materials/TITLE_ABSTRACT_HIGHLIGHTS_PACKAGE.md; manuscript/main.md",
            "Trim or restructure to the target journal word limit.",
            "Must keep simulator-only, heldout3/heldout4 limits, and oracle-boundary wording.",
            f"{shortform['summary']['abstract_word_count']} words currently",
        ),
        field_row(
            "manuscript_information",
            "keywords",
            keywords,
            "copy_ready_with_author_style_review",
            "materials/TITLE_ABSTRACT_HIGHLIGHTS_PACKAGE.md",
            "Select the subset and order required by the target journal.",
            "Keywords should not imply VLM or real-road evidence.",
            "semicolon-separated draft",
        ),
        field_row(
            "manuscript_information",
            "highlights",
            highlights,
            "copy_ready_with_author_style_review",
            "materials/TITLE_ABSTRACT_HIGHLIGHTS_PACKAGE.md",
            "Adjust count and character limits to target-journal rules.",
            "Highlights must retain the strong baseline and held-out limitation statements.",
            f"{shortform['summary']['highlight_count']} highlights",
        ),
        field_row(
            "manuscript_information",
            "plain_language_summary",
            plain,
            "copy_ready_with_author_style_review",
            "materials/TITLE_ABSTRACT_HIGHLIGHTS_PACKAGE.md",
            "Use only if the journal requests a lay summary; trim if needed.",
            "Plain language cannot become a deployment-readiness claim.",
            f"{shortform['summary']['plain_language_word_count']} words currently",
        ),
        field_row(
            "data_and_code",
            "data_availability_statement",
            data_availability,
            "copy_after_archive",
            "materials/DATA_CODE_AVAILABILITY.md; materials/EXTERNAL_ARCHIVE_PREFLIGHT.md",
            "Replace local-path wording with public DOI/URL/accession after deposition.",
            "Local package readiness is not a public archive record.",
        ),
        field_row(
            "data_and_code",
            "code_availability_statement",
            code_availability,
            "copy_after_archive",
            "materials/DATA_CODE_AVAILABILITY.md; materials/REPRODUCTION_GUIDE.md",
            "Add public repository or archive DOI after deposition.",
            "Do not imply unsupported hardware, VLM perception, or real-road deployment support.",
        ),
        field_row(
            "ethics_and_safety",
            "ethics_statement",
            ethics,
            "copy_ready_with_author_confirmation",
            "materials/RESEARCH_RISK_AND_SAFETY.md",
            "Authors should confirm the journal-specific ethics checkbox wording.",
            "No human, animal, personal-data, real-vehicle, public-road, or VLM evidence is included.",
        ),
        field_row(
            "ethics_and_safety",
            "research_risk_or_dual_use_statement",
            risk["interpretation"],
            "copy_ready_with_author_confirmation",
            "materials/RESEARCH_RISK_AND_SAFETY.md; materials/SIMULATION_TO_REAL_APPLICABILITY.md",
            "Copy simulator-only and no-deployment wording into the journal form.",
            "This is a simulator study and not a safety certification.",
        ),
        field_row(
            "scope_boundaries",
            "simulation_to_real_boundary",
            sim2real["interpretation"],
            "copy_ready_with_author_style_review",
            "materials/SIMULATION_TO_REAL_APPLICABILITY.md",
            "Use in cover letter, editor note, or methods limitations if portal asks for deployment scope.",
            "No real-world transfer claim is supported.",
        ),
        field_row(
            "author_declarations",
            "competing_interests",
            disclosure["competing_interests"]["draft_text"],
            "author_required",
            "materials/SUBMISSION_METADATA_DISCLOSURES.csv",
            "Authors must certify competing interests before upload.",
            "The package cannot infer personal or institutional declarations.",
        ),
        field_row(
            "author_declarations",
            "funding",
            disclosure["funding"]["draft_text"],
            "author_required",
            "materials/SUBMISSION_METADATA_DISCLOSURES.csv",
            "Authors must add funder names, grant numbers, award identifiers, or a no-funding statement.",
            "Funding cannot be inferred locally.",
        ),
        field_row(
            "author_declarations",
            "acknowledgements",
            disclosure["acknowledgements"]["draft_text"],
            "author_required",
            "materials/SUBMISSION_METADATA_DISCLOSURES.csv",
            "Authors must add acknowledgements or state none.",
            "Acknowledgements require author confirmation.",
        ),
        field_row(
            "author_declarations",
            "author_metadata",
            f"{metadata['summary']['author_count']} author rows parsed; affiliation, ORCID, email, and corresponding-author fields are blank templates.",
            "author_required",
            "materials/SUBMISSION_METADATA_AUTHORS.csv",
            "Complete author names, affiliations, ORCIDs, emails, and corresponding-author designation.",
            "Repository AUTHORS data are not certified submission metadata.",
        ),
        field_row(
            "author_declarations",
            "credit_contributions",
            f"{metadata['summary']['credit_role_count']} CRediT roles templated.",
            "author_required",
            "materials/SUBMISSION_METADATA_CREDIT.csv",
            "Assign CRediT roles manually and confirm with all authors.",
            "CRediT roles are placeholders until author-certified.",
        ),
        field_row(
            "archive",
            "archive_doi_or_url",
            submission_fields["archive_doi_or_url"]["value"],
            "author_required",
            "materials/EXTERNAL_ARCHIVE_PREFLIGHT.md; materials/FAIR_ARCHIVE_METADATA.md",
            "Deposit package and paste DOI/URL/accession into all availability fields.",
            "External identifier is pending.",
        ),
        field_row(
            "upload_plan",
            "journal_upload_files",
            (
                f"{upload['summary']['journal_portal_candidate_count']} journal portal candidates; "
                f"{upload['summary']['archive_candidate_count']} archive candidates; "
                f"{upload['summary']['author_selection_required_count']} author-selection rows."
            ),
            "ready_with_author_selection",
            "materials/SUBMISSION_UPLOAD_SELECTION_PLAN.md",
            "Use the upload plan after target journal choice.",
            "Internal QC files are normally retained rather than uploaded.",
        ),
    ]

    status_counts = {}
    for item in fields:
        status_counts[item["status"]] = status_counts.get(item["status"], 0) + 1

    ready_statuses = {
        "copy_ready_with_author_style_review",
        "copy_ready_with_author_confirmation",
        "ready_with_author_selection",
    }
    author_required = [item for item in fields if item["status"] == "author_required"]
    copy_after_archive = [item for item in fields if item["status"] == "copy_after_archive"]

    return {
        "root": str(root),
        "title": "Submission Portal Field Completion Pack",
        "purpose": (
            "Provide a journal-portal field-by-field completion pack that separates copy-ready text, "
            "archive-dependent fields, and author-certified metadata/declarations."
        ),
        "fields": fields,
        "summary": {
            "status": "ready_with_author_completion",
            "field_count": len(fields),
            "status_counts": status_counts,
            "copy_ready_count": sum(1 for item in fields if item["status"] in ready_statuses),
            "copy_after_archive_count": len(copy_after_archive),
            "author_required_count": len(author_required),
            "publication_verification_status": verification["summary"]["status"],
            "statistical_consistency_status": stats["summary"]["status"],
            "artifact_provenance": f"{provenance['complete_count']}/{len(provenance['artifacts'])}",
            "portal_author_action_count": portal["summary"]["author_action_count"],
            "remaining_author_blockers": blockers["summary"]["author_required_count"],
        },
        "interpretation": (
            "This pack is intended for portal entry and internal pre-submission review. It does not certify author "
            "metadata, disclosures, target-journal formatting, or external archive deposition."
        ),
    }


def write_csv(report, path):
    fields = [
        "portal_section",
        "portal_field",
        "draft_value",
        "status",
        "evidence",
        "author_action",
        "claim_boundary",
        "max_words_or_format",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in report["fields"]:
            writer.writerow(item)


def write_markdown(report, path):
    lines = [
        "# Submission Portal Field Completion Pack",
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
            "## Fields",
            "",
            "| section | field | status | draft value | author action | evidence | boundary |",
            "|---|---|---|---|---|---|---|",
        ]
    )
    for item in report["fields"]:
        lines.append(
            f"| {item['portal_section']} | {item['portal_field']} | {item['status']} | "
            f"{item['draft_value']} | {item['author_action']} | `{item['evidence']}` | {item['claim_boundary']} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export journal submission portal field completion pack.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_report(root)
    out_json = materials / "SUBMISSION_PORTAL_FIELD_COMPLETION_PACK.json"
    out_md = materials / "SUBMISSION_PORTAL_FIELD_COMPLETION_PACK.md"
    out_csv = materials / "SUBMISSION_PORTAL_FIELD_COMPLETION_PACK.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv), "summary": report["summary"]}, indent=2))


if __name__ == "__main__":
    main()
