#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


OFFICIAL_SOURCES = {
    "Nature Portfolio": {
        "policy_url": "https://www.nature.com/nature-portfolio/editorial-policies/reporting-standards",
        "source_note": "Nature Portfolio reporting standards and availability policies.",
    },
    "Springer Nature": {
        "policy_url": "https://www.springernature.com/gp/authors/research-data-policy/data-availability-statements",
        "source_note": "Springer Nature data availability statement guidance.",
    },
    "Science/AAAS": {
        "policy_url": "https://www.science.org/content/page/science-journals-editorial-policies",
        "source_note": "Science Journals editorial policies and journal-specific author information.",
    },
    "Cell Press": {
        "policy_url": "https://www.cell.com/pb-assets/journals/assets/info-for-authors/resource-availability.html",
        "source_note": "Cell Press Resource Availability guidance for STAR Methods.",
    },
}


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def row(
    row_id,
    journal_family,
    requirement_area,
    requirement,
    local_evidence,
    current_status,
    author_action,
    boundary,
    priority,
):
    source = OFFICIAL_SOURCES[journal_family]
    return {
        "id": row_id,
        "journal_family": journal_family,
        "requirement_area": requirement_area,
        "requirement": requirement,
        "official_source": source["policy_url"],
        "source_note": source["source_note"],
        "local_evidence": local_evidence,
        "current_status": current_status,
        "author_action": author_action,
        "claim_boundary": boundary,
        "priority": priority,
    }


def build_matrix(root):
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    provenance = load_json(root / "tables" / "artifact_provenance.json")
    dictionary = load_json(root / "materials" / "DATA_DICTIONARY.json")
    release = load_json(root / "materials" / "RELEASE_ARCHIVE_MANIFEST.json")
    archive = load_json(root / "materials" / "EXTERNAL_ARCHIVE_PREFLIGHT.json")
    submission = load_json(root / "materials" / "SUBMISSION_METADATA_DRAFT.json")
    stats = load_json(root / "materials" / "STATISTICAL_CONSISTENCY_AUDIT.json")
    claim_qa = load_json(root / "materials" / "MANUSCRIPT_CLAIM_QA.json")
    references = load_json(root / "materials" / "REFERENCE_READINESS_AUDIT.json")
    reviewer = load_json(root / "materials" / "REVIEWER_RISK_RESPONSE_DOSSIER.json")

    provenance_label = f"{provenance['complete_count']}/{len(provenance['artifacts'])}"
    archive_pending = archive["summary"]["external_archive_pending"]
    reference_action = references["summary"]["topic_needs_author_completion_count"]
    stats_status = "pass" if stats["summary"]["status"] == "pass" else "review_required"
    reference_author_action = (
        "Related-work starter coverage is present; authors should adapt breadth and citation style to the selected journal."
        if reference_action == 0
        else "Expand recent related work for multi-agent RL, autonomous racing, safe learning, and sim-to-real boundaries."
    )

    rows = [
        row(
            "JC1_nature_materials_data_code",
            "Nature Portfolio",
            "data_code_materials",
            "Make materials, data, code, and protocols available without undue restriction, with restrictions disclosed at submission.",
            "materials/DATA_CODE_AVAILABILITY.md; materials/FAIR_ARCHIVE_METADATA.md; materials/RELEASE_ARCHIVE_MANIFEST.md",
            "ready_pending_external_archive" if archive_pending else "ready",
            "Deposit the package in an approved public repository and update DOI/URL fields.",
            "Local files and checksums support readiness but are not a public archive record until DOI/accession is assigned.",
            "high",
        ),
        row(
            "JC2_springer_data_statement",
            "Springer Nature",
            "data_availability_statement",
            "Provide a data availability statement describing what data support the results and how they can be accessed.",
            "materials/DATA_CODE_AVAILABILITY.md; materials/EXTERNAL_ARCHIVE_PREFLIGHT.md",
            "ready_with_author_update" if archive_pending else "ready",
            "Replace local-path wording with final repository DOI/accession before submission.",
            "A local availability statement should not be treated as final journal-ready text.",
            "high",
        ),
        row(
            "JC3_science_data_reproducibility",
            "Science/AAAS",
            "data_and_reproducibility",
            "Ensure data and materials needed to understand, verify, and extend the conclusions are available under the relevant editorial policies.",
            "tables/artifact_provenance.md; materials/REPRODUCTION_GUIDE.md; materials/DATA_DICTIONARY.md",
            "ready_pending_external_archive" if archive_pending else "ready",
            "Map final archive files to the journal data-availability field and supplement.",
            "Current status supports local reproducibility, not acceptance by any specific Science journal.",
            "high",
        ),
        row(
            "JC4_cell_resource_availability",
            "Cell Press",
            "resource_availability",
            "Prepare STAR Methods Resource Availability fields, including lead contact, materials availability, and data/code availability.",
            "materials/SUBMISSION_METADATA_DRAFT.md; materials/DATA_CODE_AVAILABILITY.md; materials/FAIR_ARCHIVE_METADATA.md",
            "author_action_required",
            "Complete lead-contact, author, affiliation, ORCID, repository, and accession fields.",
            "Automation cannot certify author identity, correspondence, or disclosures.",
            "high",
        ),
        row(
            "JC5_code_environment",
            "Nature Portfolio",
            "code_and_environment",
            "Provide code needed to interpret and replicate conclusions with appropriate availability and review information.",
            "materials/ENVIRONMENT_REPRODUCIBILITY_AUDIT.md; materials/SOFTWARE_DEPENDENCY_LICENSE_AUDIT.md; materials/scripts/",
            "ready_with_author_review",
            "Confirm third-party license handling and archive the exact script snapshots.",
            "Dependency/license audit is not legal advice.",
            "high",
        ),
        row(
            "JC6_statistics_reporting",
            "Nature Portfolio",
            "statistics_and_reporting",
            "Report statistical methods, sample sizes, and analysis boundaries transparently.",
            "materials/STATISTICAL_ANALYSIS_PLAN.md; materials/STATISTICAL_CONSISTENCY_AUDIT.md; materials/SAMPLE_SIZE_SENSITIVITY_BRIEF.md",
            stats_status,
            "Keep n=10/n=50 limitation wording in final abstract, results, and discussion.",
            "Descriptive seed-set evidence must not be promoted to broad robustness.",
            "high",
        ),
        row(
            "JC7_claim_control",
            "Science/AAAS",
            "claims_and_limitations",
            "Align conclusions with the evidence and avoid overstatement beyond available data.",
            "materials/CLAIM_EVIDENCE_MATRIX.md; materials/MANUSCRIPT_CLAIM_QA.md; materials/REVIEWER_RISK_RESPONSE_DOSSIER.md",
            claim_qa["summary"]["status"],
            "Rerun claim QA after final manuscript formatting.",
            "No real-road, VLM, safety-certification, or oracle-as-controller claim is supported.",
            "high",
        ),
        row(
            "JC8_negative_results",
            "Cell Press",
            "transparent_reporting",
            "Retain limitations and negative/diagnostic results needed for transparent interpretation.",
            "materials/NEGATIVE_RESULTS_FAILURE_REGISTER.md; materials/EXTERNAL_VALIDITY_BOUNDARY_AUDIT.md",
            "ready",
            "Keep negative controls and held-out failures in supplementary material.",
            "Negative results are evidence, not wording to hide for narrative simplicity.",
            "high",
        ),
        row(
            "JC9_source_data",
            "Nature Portfolio",
            "figure_source_data",
            "Provide source data and traceable figure inputs when requested by journal policy or reviewer practice.",
            "materials/FIGURE_SOURCE_DATA_AUDIT.md; figures/*_source_data.csv",
            "ready",
            "Convert local figure/source-data labels to target-journal naming conventions.",
            "Source data cover simulator figures only.",
            "medium",
        ),
        row(
            "JC10_author_metadata",
            "Springer Nature",
            "authorship_disclosures",
            "Prepare author metadata, contributions, competing interests, funding, acknowledgements, and ethics fields.",
            "materials/SUBMISSION_METADATA_DRAFT.md; materials/SUBMISSION_PORTAL_PACKAGE_MAP.md",
            "author_action_required",
            "Authors must certify names, affiliations, ORCID IDs, contributions, funding, and disclosures.",
            "Local drafts are placeholders until author-certified.",
            "high",
        ),
        row(
            "JC11_related_work",
            "Science/AAAS",
            "editorial_context",
            "Position the advance against current literature with journal-appropriate breadth.",
            "materials/REFERENCE_READINESS_AUDIT.md; materials/RELATED_WORK_POSITIONING_MATRIX.md; manuscript/references.bib",
            "author_action_required" if reference_action else "ready",
            reference_author_action,
            "Starter related-work coverage supports local preflight; final target-journal breadth and style remain author-curated.",
            "high",
        ),
        row(
            "JC12_pre_submission_review",
            "Cell Press",
            "reviewer_preparation",
            "Prepare concise responses to predictable reviewer concerns before submission.",
            "materials/REVIEWER_RISK_RESPONSE_DOSSIER.md; materials/EDITORIAL_TRIAGE_AND_REVIEWER_CHECKLIST.md",
            "ready_with_author_adaptation",
            "Adapt response wording to the final target journal and manuscript text.",
            "A response dossier is preparation material, not final rebuttal correspondence.",
            "medium",
        ),
    ]

    status_counts = {}
    for item in rows:
        status_counts[item["current_status"]] = status_counts.get(item["current_status"], 0) + 1

    return {
        "root": str(root),
        "title": "Target-journal compliance matrix",
        "purpose": (
            "Map current local evidence to common official Nature Portfolio, Science/AAAS, "
            "and Cell Press submission-readiness expectations."
        ),
        "official_sources": OFFICIAL_SOURCES,
        "rows": rows,
        "summary": {
            "row_count": len(rows),
            "high_priority_count": sum(1 for item in rows if item["priority"] == "high"),
            "author_action_count": sum(1 for item in rows if "author_action" in item["current_status"]),
            "status_counts": status_counts,
            "publication_verification_status": verification["summary"]["status"],
            "artifact_provenance": provenance_label,
            "data_dictionary_complete": dictionary["summary"]["complete"],
            "release_file_count": release["summary"]["file_count"],
            "reviewer_dossier_rows": reviewer["summary"]["row_count"],
            "external_archive_pending": archive_pending,
        },
        "interpretation": (
            "This matrix is a local pre-submission compliance aid. It does not certify acceptance by any journal, "
            "and target-journal instructions must be rechecked before upload."
        ),
    }


def write_csv(report, path):
    fields = [
        "id",
        "journal_family",
        "requirement_area",
        "requirement",
        "official_source",
        "source_note",
        "local_evidence",
        "current_status",
        "author_action",
        "claim_boundary",
        "priority",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in report["rows"]:
            writer.writerow(item)


def write_markdown(report, path):
    lines = [
        "# Target-Journal Compliance Matrix",
        "",
        report["purpose"],
        "",
        report["interpretation"],
        "",
        "## Summary",
        "",
        f"- Rows: {report['summary']['row_count']}",
        f"- High-priority rows: {report['summary']['high_priority_count']}",
        f"- Author-action rows: {report['summary']['author_action_count']}",
        f"- Publication verification: `{report['summary']['publication_verification_status']}`",
        f"- Artifact provenance: {report['summary']['artifact_provenance']}",
        f"- External archive pending: `{report['summary']['external_archive_pending']}`",
        "",
        "## Official Sources",
        "",
        "| journal family | policy URL | note |",
        "|---|---|---|",
    ]
    for name, source in report["official_sources"].items():
        lines.append(f"| {name} | {source['policy_url']} | {source['source_note']} |")
    lines.extend(
        [
            "",
            "## Compliance Rows",
            "",
            "| id | journal family | area | priority | status | requirement | local evidence | author action | claim boundary |",
            "|---|---|---|---|---|---|---|---|---|",
        ]
    )
    for item in report["rows"]:
        lines.append(
            f"| {item['id']} | {item['journal_family']} | {item['requirement_area']} | "
            f"{item['priority']} | {item['current_status']} | {item['requirement']} | "
            f"`{item['local_evidence']}` | {item['author_action']} | {item['claim_boundary']} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export target-journal compliance matrix.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_matrix(root)
    out_json = materials / "TARGET_JOURNAL_COMPLIANCE_MATRIX.json"
    out_md = materials / "TARGET_JOURNAL_COMPLIANCE_MATRIX.md"
    out_csv = materials / "TARGET_JOURNAL_COMPLIANCE_MATRIX.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv), "summary": report["summary"]}, indent=2))


if __name__ == "__main__":
    main()
