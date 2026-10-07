#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import json
from pathlib import Path


OFFICIAL_SOURCES = [
    {
        "source_id": "TITS_OFFICIAL",
        "title": "IEEE Intelligent Transportation Systems Society: IEEE Transactions on Intelligent Transportation Systems",
        "url": "https://ieee-itss.org/pub/t-its/",
        "used_for": "Scope, regular paper length, abstract length, keyword count, ScholarOne submission entry, final manuscript file guidance.",
    },
    {
        "source_id": "IEEE_REPRO",
        "title": "IEEE Author Center: Reproducibility",
        "url": "https://ieeeauthorcenter.ieee.org/create-your-ieee-journal-article/create-the-text-of-your-article/reproducible-research/",
        "used_for": "Method detail, data repository, code repository, and reproducibility expectations.",
    },
    {
        "source_id": "IEEE_TOOLS",
        "title": "IEEE Author Center: Tools for IEEE Authors",
        "url": "https://ieeeauthorcenter.ieee.org/create-your-ieee-journal-article/create-the-text-of-your-article/tools-for-ieee-authors/",
        "used_for": "Author tools, templates, IEEE PDF Checker, and ORCID-related author workflow.",
    },
    {
        "source_id": "IEEE_AI",
        "title": "IEEE Author Guidelines for Artificial Intelligence (AI)-Generated Text",
        "url": "https://open.ieee.org/author-guidelines-for-artificial-intelligence-ai-generated-text/",
        "used_for": "AI-tool disclosure and author-side declaration checklist.",
    },
]


def exists(path):
    path = Path(path)
    return path.exists() and path.stat().st_size > 0


def row(area, requirement, status, evidence, author_action, source_id):
    return {
        "area": area,
        "requirement": requirement,
        "status": status,
        "evidence": evidence,
        "author_action": author_action,
        "source_id": source_id,
    }


def build_rows():
    return [
        row(
            "Scope",
            "Paper must fit intelligent transportation systems scope.",
            "local_ready",
            "METHODS_DRAFT.md; CONFIRMATORY_EVIDENCE_REPORT.md; benchmark focuses online multi-car overtaking in racing/traffic simulation.",
            "Final introduction should explicitly frame autonomous overtaking as an ITS/traffic automation problem.",
            "TITS_OFFICIAL",
        ),
        row(
            "Manuscript Type",
            "Regular paper length and formatting must follow current T-ITS instructions.",
            "author_action_required",
            "Manuscript draft package exists but is not converted to final IEEE T-ITS template.",
            "Convert draft into current IEEE double-column template, check page count, and run IEEE PDF tools before submission.",
            "TITS_OFFICIAL;IEEE_TOOLS",
        ),
        row(
            "Abstract",
            "Abstract must satisfy T-ITS length/style limits.",
            "local_ready_author_finalization_required",
            "tits_submission_metadata_pack/materials/TITLE_ABSTRACT_KEYWORDS_DRAFT.md contains a one-paragraph 178-word abstract draft and QA checks.",
            "Verify live portal word limit, final title/terminology, and author-approved wording before submission.",
            "TITS_OFFICIAL",
        ),
        row(
            "Keywords",
            "Keywords must follow current T-ITS keyword-count and selection rules.",
            "local_ready_author_finalization_required",
            "tits_submission_metadata_pack/tables/keyword_plan.csv proposes 2 application, 2 methodology, and 2 free keywords.",
            "Select or edit final keywords in the live portal using the current T-ITS category lists.",
            "TITS_OFFICIAL",
        ),
        row(
            "Submission Portal",
            "Submission must use the official T-ITS ScholarOne route.",
            "author_action_required",
            "Reviewer packet contains local reproducibility route, not portal metadata.",
            "Create/update ScholarOne submission and enter final title, abstract, keywords, author metadata, and disclosures.",
            "TITS_OFFICIAL",
        ),
        row(
            "Methods Reproducibility",
            "Methods must provide enough implementation detail to reproduce results.",
            "local_ready",
            "docs/tits_dynamic_graph_reproducibility_protocol.md; METHODS_DRAFT.md; reviewer replication README.",
            "When writing final manuscript, keep algorithm details and benchmark protocol linked to source code and exact commands.",
            "IEEE_REPRO",
        ),
        row(
            "Data Availability",
            "Data should be deposited or clearly made available with source data and provenance.",
            "local_ready_author_archive_required",
            "online_benchmark_source_data.csv; public_release_plan; artifact manifest; DATA_CODE_AVAILABILITY_DRAFT.md; DATA_CODE_AVAILABILITY_FINALIZATION.md.",
            "Deposit formal archive, obtain DOI/accession, and replace placeholder text in Data Availability.",
            "IEEE_REPRO",
        ),
        row(
            "Code Availability",
            "Code repository should enable reproduction or clearly document access.",
            "local_ready_author_archive_required",
            "public_release_plan routes code to GitHub/public repository and data to archive; reviewer smoke script exists.",
            "Create clean public repository or release tag; update URL/commit in manuscript and availability statement.",
            "IEEE_REPRO",
        ),
        row(
            "Statistical Evidence",
            "Claims should be supported by source data, uncertainty, and appropriate comparisons.",
            "local_ready",
            "confirmatory_paired_tests_vs_dlc.csv; online_benchmark_main_results.md; CONFIRMATORY_EVIDENCE_REPORT.md.",
            "In final Results, quote only numbers in manuscript_numeric_index.csv or source tables.",
            "IEEE_REPRO",
        ),
        row(
            "Figures and Source Data",
            "Figures should have source data and submission-ready formats.",
            "local_ready_author_format_required",
            "tits_figure_source_data_audit verifies 7 formal figures, PDF/SVG/PNG/TIFF exports, and 20 source tables.",
            "Choose final manuscript figure language and perform final IEEE template, caption, color, and PDF checks.",
            "TITS_OFFICIAL;IEEE_TOOLS",
        ),
        row(
            "Visual Evidence",
            "Supplementary visual evidence should be traceable and not replace statistics.",
            "local_ready",
            "publication_gif_manifest.md lists top-down and first-person GIFs with summaries/traces.",
            "Decide which GIFs to include as supplementary material and cite them as representative evidence only.",
            "IEEE_REPRO",
        ),
        row(
            "Ethics/AI/Conflicts",
            "Author declarations and AI-tool disclosures must be completed in final submission.",
            "local_ready_author_finalization_required",
            "tits_submission_metadata_pack/materials/AUTHOR_DECLARATIONS_AND_AI_DISCLOSURE_DRAFT.md contains editable draft text and placeholders.",
            "Complete IEEE/ScholarOne declarations, conflict-of-interest statement, author contributions, funding, and exact AI-tool disclosure.",
            "IEEE_TOOLS;IEEE_AI",
        ),
        row(
            "Cover Letter and Portal Metadata",
            "Submission metadata should be internally consistent with the manuscript, evidence package, and portal fields.",
            "local_ready_author_finalization_required",
            "tits_submission_metadata_pack contains title, abstract, keywords, cover letter, declaration drafts, and a submission checklist.",
            "Insert author identities, corresponding-author details, prior-work disclosures, and portal-specific fields.",
            "TITS_OFFICIAL;IEEE_TOOLS",
        ),
        row(
            "ORCID/Author Metadata",
            "Author identifiers and metadata must follow current IEEE workflow.",
            "author_action_required",
            "No author metadata is present in this local technical package.",
            "Add ORCID and final affiliation/funding metadata during submission.",
            "IEEE_TOOLS",
        ),
        row(
            "Final Archive Integrity",
            "Released files should have stable checksums and routing.",
            "local_ready_author_freeze_required",
            "tits_dynamic_graph_artifact_manifest_files.csv; public_release_plan; final_readiness_dashboard.",
            "After DOI/release-tag creation, rerun checksum manifest and freeze final upload package.",
            "IEEE_REPRO",
        ),
    ]


def write_csv(path, rows):
    fields = ["area", "requirement", "status", "evidence", "author_action", "source_id"]
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return str(path)


def write_md(path, rows):
    counts = {}
    for item in rows:
        counts[item["status"]] = counts.get(item["status"], 0) + 1
    lines = [
        "# IEEE T-ITS Compliance Matrix",
        "",
        "This matrix maps current local artifacts to official IEEE/T-ITS-facing requirements. It is a pre-submission planning aid, not a substitute for checking the live journal portal before upload.",
        "",
        "## Official Sources",
        "",
    ]
    for source in OFFICIAL_SOURCES:
        lines.append(f"- `{source['source_id']}`: {source['title']} ({source['url']})")
    lines.extend(
        [
            "",
            "## Status Summary",
            "",
        ]
    )
    for status, count in sorted(counts.items()):
        lines.append(f"- {status}: {count}")
    lines.extend(
        [
            "",
            "## Matrix",
            "",
            "| Area | Status | Requirement | Evidence | Author action | Source |",
            "|---|---|---|---|---|---|",
        ]
    )
    for item in rows:
        lines.append(
            f"| {item['area']} | {item['status']} | {item['requirement']} | {item['evidence']} | {item['author_action']} | {item['source_id']} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `local_ready` means the local evidence package supports the item.",
            "- `author_action_required` means the task depends on final submission metadata, journal portal actions, template formatting, or legal/license confirmation.",
            "- `local_ready_author_archive_required` means local files are ready, but a DOI/repository accession or public release URL is still needed.",
            "- `local_ready_author_finalization_required` means an editable local draft exists, but final author/portal wording remains author-owned.",
        ]
    )
    path = Path(path)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(path)


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


def main():
    parser = argparse.ArgumentParser(description="Export IEEE T-ITS compliance matrix for the current package.")
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/ieee_tits_compliance")
    args = parser.parse_args()
    rows = build_rows()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = write_csv(out_dir / "ieee_tits_compliance_matrix.csv", rows)
    md_path = write_md(out_dir / "IEEE_TITS_COMPLIANCE_MATRIX.md", rows)
    source_path = write_json(out_dir / "official_sources.json", OFFICIAL_SOURCES)
    local_ready = sum(1 for item in rows if item["status"].startswith("local_ready"))
    author_action = sum(1 for item in rows if item["status"] == "author_action_required")
    manifest = {
        "status": "author_action_required",
        "out_dir": str(out_dir),
        "row_count": len(rows),
        "local_ready_or_partially_ready": local_ready,
        "author_action_required": author_action,
        "paths": {
            "matrix_csv": csv_path,
            "matrix_md": md_path,
            "official_sources_json": source_path,
        },
        "note": "Official submission rules can change; verify live IEEE/T-ITS pages before final upload.",
    }
    manifest_path = write_json(out_dir / "ieee_tits_compliance_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, "rows": len(rows), "status": manifest["status"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
