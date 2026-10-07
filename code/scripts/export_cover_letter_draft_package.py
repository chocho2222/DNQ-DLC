#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_package(root):
    manifest = load_json(root / "manifest.json")
    summary = load_json(root / "materials" / "PUBLICATION_PACKAGE_SUMMARY.json")
    narrative = load_json(root / "materials" / "EDITORIAL_NARRATIVE_PACKAGE.json")
    significance = load_json(root / "materials" / "SIGNIFICANCE_BRIEFING.json")
    submission = load_json(root / "materials" / "SUBMISSION_METADATA_DRAFT.json")
    preflight = load_json(root / "materials" / "EXTERNAL_ARCHIVE_PREFLIGHT.json")
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    claims = load_json(root / "materials" / "CLAIM_EVIDENCE_MATRIX.json")
    replication = load_json(root / "materials" / "REVIEWER_REPLICATION_ROUTE.json")
    assembly = load_json(root / "materials" / "MANUSCRIPT_SUPPLEMENT_ASSEMBLY_MAP.json")

    main = summary["main_results"]
    title = significance["recommended_title"]
    pitch = significance["cover_letter_material"]["one_sentence_pitch"]
    author_required = submission["summary"]["author_required_count"]
    claim_ids = {row["id"]: row for row in claims["claims"]}

    paragraphs = [
        {
            "id": "P1_opening_and_fit",
            "role": "opening",
            "text": (
                "Dear Editor, We are pleased to submit our manuscript, tentatively titled "
                f"\"{title}\", for consideration. The study addresses a recurring weakness in "
                "autonomous overtaking reports: short, visually convincing rollouts can obscure failures in "
                "lap completion, rank, off-track behavior, and traffic quality. We therefore present a strict, "
                "simulator-only, full-lap multi-car overtaking evaluation package with preserved rule baselines, "
                "learned and shielded candidates, online portfolio probing, and evidence-linked reproducibility materials."
            ),
            "evidence": [
                "materials/METHODS.md",
                "materials/STATISTICAL_ANALYSIS_PLAN.md",
                "materials/EDITORIAL_NARRATIVE_PACKAGE.md",
            ],
            "boundary": "Do not imply real-road, VLM, perception-stack, or safety-certification evidence.",
        },
        {
            "id": "P2_core_contribution",
            "role": "contribution",
            "text": (
                f"Our central contribution is an evidence standard rather than a single overclaimed controller: {pitch} "
                "The package keeps the strongest rule baseline visible, uses diagnostic oracle portfolios only as "
                "upper bounds, and reports online simulator-loop selector outcomes separately from oracle coverage."
            ),
            "evidence": [
                "materials/SIGNIFICANCE_BRIEFING.md",
                "materials/CLAIM_EVIDENCE_MATRIX.md",
                "materials/BASELINE_FAIRNESS_AUDIT.md",
            ],
            "boundary": "Do not present oracle portfolios as online selector outputs.",
        },
        {
            "id": "P3_main_results",
            "role": "results",
            "text": (
                f"Under the locked strict protocol, the rule overtake baseline reaches {main['locked_rule_overtake']} "
                f"and graph-adaptive shielding reaches {main['locked_graph_adaptive']}. With the expanded candidate pool, "
                f"the online selector reaches {main['heldout1_expanded_selector']} on heldout1 and "
                f"{main['heldout2_expanded_selector']} on heldout2 against a {main['heldout2_expanded_candidate_oracle']} "
                "diagnostic oracle. These results show useful controller complementarity and bounded in-simulator "
                "online selection progress, while preserving residual selector misses."
            ),
            "evidence": [
                "tables/full_statistical_report.md",
                "tables/expanded_selector_generalization.md",
                "figures/figure_2_portfolio_selector_summary.*",
            ],
            "boundary": claim_ids["C10_expanded_selector_progress"]["do_not_claim"],
        },
        {
            "id": "P4_validation_boundary",
            "role": "validation_boundary",
            "text": (
                f"We also include evidence that limits the claims. Heldout3 is a diagnostic stress boundary "
                f"({main['heldout3_expanded_selector']} selector versus {main['heldout3_candidate_oracle']} oracle), "
                f"and heldout4 after targeted repair shows partial transfer "
                f"({main['heldout4_selector']} selector versus {main['heldout4_oracle']} oracle). "
                "We report these outcomes explicitly to avoid converting seed-targeted repair or oracle coverage into "
                "a broad robustness claim."
            ),
            "evidence": [
                "tables/heldout3_external_validation.md",
                "tables/heldout4_external_validation.md",
                "materials/EXTERNAL_VALIDITY_BOUNDARY_AUDIT.md",
                "figures/figure_3_cross_heldout_validation.*",
            ],
            "boundary": "Heldout3-targeted repair is diagnostic; heldout4 is partial transfer, not broad robustness.",
        },
        {
            "id": "P5_transparency_and_reproducibility",
            "role": "transparency",
            "text": (
                f"The local simulator-evidence package is accompanied by complete local provenance "
                f"({verification['summary']['artifact_provenance']}), source-data tables, figure manifests, "
                "claim guardrails, seed ledgers, reproducibility audits, archive metadata, and a data dictionary. "
                f"We also provide {replication['summary']['quickstart_count']} reviewer quickstart checks and "
                f"{assembly['summary']['evidence_route_count']} manuscript evidence routes so editors and reviewers can trace "
                "headline claims to source data before deciding whether optional GPU reruns are needed. Negative controls, "
                "selector misses, candidate gaps, and sample-size limits are retained as part of the scientific record rather than omitted."
            ),
            "evidence": [
                "tables/artifact_provenance.md",
                "tables/reproducibility_audit.md",
                "materials/DATA_DICTIONARY.md",
                "materials/REVIEWER_REPLICATION_ROUTE.md",
                "materials/MANUSCRIPT_SUPPLEMENT_ASSEMBLY_MAP.md",
                "materials/NEGATIVE_RESULTS_FAILURE_REGISTER.md",
                "materials/SAMPLE_SIZE_SENSITIVITY_BRIEF.md",
            ],
            "boundary": "Local evidence-package readiness and quickstart checks are not the same as final journal PDF/source readiness or public archive deposition.",
        },
        {
            "id": "P6_administrative_close",
            "role": "administrative",
            "text": (
                "The manuscript is original work and is not under consideration elsewhere. The current simulator-only local package "
                "contains no human-subject, animal, personal-data, public-road, or real-vehicle trial data. "
                "Author contributions, competing interests, funding statements, ORCID records, and final archive DOI/accession "
                "should be completed by the authors before journal upload."
            ),
            "evidence": [
                "materials/RESEARCH_RISK_AND_SAFETY.md",
                "materials/SUBMISSION_METADATA_DRAFT.md",
                "materials/EXTERNAL_ARCHIVE_PREFLIGHT.md",
            ],
            "boundary": "This paragraph is a draft; administrative declarations require author confirmation.",
        },
    ]

    editor_checklist = [
        {
            "item": "journal_target",
            "status": "author_required",
            "note": "Insert target journal name, section, and any required article type.",
        },
        {
            "item": "corresponding_author",
            "status": "author_required",
            "note": "Insert corresponding author name, affiliation, email, and ORCID.",
        },
        {
            "item": "administrative_disclosures",
            "status": "author_required",
            "note": f"{author_required} submission metadata fields remain intentionally unresolved.",
        },
        {
            "item": "archive_doi",
            "status": "author_required",
            "note": "External archive DOI/accession is pending until public deposition.",
        },
        {
            "item": "claim_boundary",
            "status": "ready",
            "note": "Cover letter draft avoids broad robustness, deployment, VLM, and oracle-as-controller claims.",
        },
    ]

    return {
        "root": str(root),
        "title": "Cover letter draft package",
        "purpose": (
            "Provide a claim-safe cover-letter draft and paragraph-to-evidence map for journal submission preparation."
        ),
        "target_journal_placeholder": "[TARGET JOURNAL]",
        "corresponding_author_placeholder": "[CORRESPONDING AUTHOR DETAILS]",
        "recommended_title": title,
        "paragraphs": paragraphs,
        "editor_checklist": editor_checklist,
        "evidence_boundaries": {
            "not_supported": narrative["publication_positioning"]["not_yet_supported"],
            "external_archive_pending": preflight["summary"]["external_archive_pending"],
            "author_required_submission_fields": author_required,
            "reviewer_quickstart_count": replication["summary"]["quickstart_count"],
            "manuscript_evidence_route_count": assembly["summary"]["evidence_route_count"],
        },
        "verification_snapshot": verification["summary"],
        "interpretation": (
            "This is a draft package for authors to adapt, not a final cover letter. It deliberately leaves "
            "journal target, author metadata, funding, conflicts, and archive DOI/accession as author-required fields."
        ),
    }


def write_csv(report, path):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["id", "role", "text", "evidence", "boundary"])
        writer.writeheader()
        for row in report["paragraphs"]:
            writer.writerow(
                {
                    "id": row["id"],
                    "role": row["role"],
                    "text": row["text"],
                    "evidence": "; ".join(row["evidence"]),
                    "boundary": row["boundary"],
                }
            )


def write_checklist_csv(report, path):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["item", "status", "note"])
        writer.writeheader()
        for row in report["editor_checklist"]:
            writer.writerow(row)


def write_markdown(report, path):
    lines = [
        "# Cover Letter Draft Package",
        "",
        report["purpose"],
        "",
        report["interpretation"],
        "",
        "## Draft",
        "",
        f"Target journal: {report['target_journal_placeholder']}",
        "",
        f"Corresponding author: {report['corresponding_author_placeholder']}",
        "",
    ]
    lines.extend(row["text"] + "\n" for row in report["paragraphs"])
    lines.extend(
        [
            "## Paragraph Evidence Map",
            "",
            "| paragraph | role | evidence | boundary |",
            "|---|---|---|---|",
        ]
    )
    for row in report["paragraphs"]:
        evidence = "; ".join(f"`{item}`" for item in row["evidence"])
        lines.append(f"| {row['id']} | {row['role']} | {evidence} | {row['boundary']} |")
    lines.extend(
        [
            "",
            "## Author Completion Checklist",
            "",
            "| item | status | note |",
            "|---|---|---|",
        ]
    )
    for row in report["editor_checklist"]:
        lines.append(f"| {row['item']} | {row['status']} | {row['note']} |")
    lines.extend(
        [
            "",
            "## Verification Snapshot",
            "",
            f"- Publication verification: `{report['verification_snapshot']['status']}`",
            f"- Artifact provenance: {report['verification_snapshot']['artifact_provenance']}",
            f"- External archive pending: {report['evidence_boundaries']['external_archive_pending']}",
            f"- Author-required submission fields: {report['evidence_boundaries']['author_required_submission_fields']}",
            f"- Reviewer quickstart checks: {report['evidence_boundaries']['reviewer_quickstart_count']}",
            f"- Manuscript evidence routes: {report['evidence_boundaries']['manuscript_evidence_route_count']}",
            "",
            "## Not Supported",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in report["evidence_boundaries"]["not_supported"])
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export claim-safe cover letter draft package.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_package(root)
    out_json = materials / "COVER_LETTER_DRAFT_PACKAGE.json"
    out_md = materials / "COVER_LETTER_DRAFT_PACKAGE.md"
    out_csv = materials / "COVER_LETTER_DRAFT_PACKAGE.csv"
    out_checklist = materials / "COVER_LETTER_AUTHOR_CHECKLIST.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    write_checklist_csv(report, out_checklist)
    print(
        json.dumps(
            {
                "json": str(out_json),
                "markdown": str(out_md),
                "csv": str(out_csv),
                "checklist_csv": str(out_checklist),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
