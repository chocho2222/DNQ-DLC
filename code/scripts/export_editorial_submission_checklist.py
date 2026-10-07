#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def item(category, requirement, status, evidence, action, note=""):
    return {
        "category": category,
        "requirement": requirement,
        "status": status,
        "evidence": evidence,
        "action": action,
        "note": note,
    }


def build_checklist(root):
    manifest = load_json(root / "manifest.json")
    summary = load_json(root / "materials" / "PUBLICATION_PACKAGE_SUMMARY.json")
    reporting = load_json(root / "materials" / "TOP_JOURNAL_REPORTING_SUMMARY.json")
    risk = load_json(root / "materials" / "RESEARCH_RISK_AND_SAFETY.json")
    fair = load_json(root / "materials" / "FAIR_ARCHIVE_METADATA.json")
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    provenance = load_json(root / "tables" / "artifact_provenance.json")
    release = load_json(root / "materials" / "RELEASE_ARCHIVE_MANIFEST.json")
    dictionary = load_json(root / "materials" / "DATA_DICTIONARY.json")
    manuscript_manifest = load_json(root / "manuscript" / "manuscript_manifest.json")

    rows = [
        item(
            "Manuscript",
            "Evidence-linked manuscript draft",
            "complete",
            "manuscript/main.md; manuscript/manuscript_manifest.json; materials/MANUSCRIPT_RESULTS_DISCUSSION_DRAFT.md",
            "Use as the conservative source draft; convert to journal-specific format only after final claims are frozen.",
            f"Draft status: {manuscript_manifest['status']}",
        ),
        item(
            "Manuscript",
            "Evidence-bound significance and cover-letter briefing",
            "complete",
            "materials/SIGNIFICANCE_BRIEFING.md; materials/CLAIM_EVIDENCE_MATRIX.md",
            "Use as source material for cover-letter wording, but add journal target and author-provided metadata manually.",
            "The briefing is not a final cover letter.",
        ),
        item(
            "Manuscript",
            "Final submission PDF/source",
            "limitation",
            "manuscript/main.md; materials/SUBMISSION_GAP_ACTION_PLAN.md",
            "Prepare final journal source package outside the experimental evidence folder.",
            "The current package intentionally stores a local draft, not a final submission PDF/source.",
        ),
        item(
            "Claims",
            "Claim-to-evidence guardrails",
            "complete",
            "materials/CLAIM_EVIDENCE_MATRIX.md; materials/MANUSCRIPT_CLAIM_QA.md",
            "Use allowed wording and prohibited-claim columns during manuscript editing.",
            f"Claim QA status: {verification['summary']['claim_qa']}",
        ),
        item(
            "Claims",
            "Oracle and targeted-repair boundaries",
            "complete",
            "materials/RESEARCH_RISK_AND_SAFETY.md; materials/PUBLICATION_PACKAGE_VERIFICATION.md",
            "Keep oracle results diagnostic and heldout3 targeted repair separate from external validation.",
            manifest["reporting_boundary"]["oracle_policy"],
        ),
        item(
            "Figures",
            "Main and supplementary figure exports",
            "complete",
            "figures/figure_1_multicar_overtake_results.*; figures/figure_2_portfolio_selector_summary.*; figures/figure_3_cross_heldout_validation.*",
            "Use exported PNG/PDF/SVG/TIFF files and source-data CSVs for submission.",
            "Figure source data and legends are included.",
        ),
        item(
            "Figures",
            "Figure legends and review-risk traceability",
            "complete",
            "materials/FIGURE_LEGENDS.md; figures/figure_1_manifest.json; figures/figure_2_manifest.json; figures/figure_3_manifest.json",
            "Copy legends after checking journal-specific length limits.",
            "Figure 3 is explicitly framed as partial transfer rather than broad robustness.",
        ),
        item(
            "Statistics",
            "Statistical analysis plan",
            "complete",
            "materials/STATISTICAL_ANALYSIS_PLAN.md; tables/full_statistical_report.md; tables/cross_heldout_statistical_supplement.md",
            "Report intervals and tests as descriptive because seed counts are small.",
            "The package retains negative held-out and calibration results.",
        ),
        item(
            "Reporting",
            "Top-journal reporting summary",
            "complete",
            "materials/TOP_JOURNAL_REPORTING_SUMMARY.md; materials/TRANSPARENT_REPORTING_CHECKLIST.md",
            "Use these rows for journal reporting forms and editorial checks.",
            f"Reporting summary: {reporting['summary']['status_counts']}",
        ),
        item(
            "Data",
            "Data and code availability statement",
            "complete",
            "materials/DATA_CODE_AVAILABILITY.md; materials/DATA_DICTIONARY.md; materials/ARCHIVE_UPLOAD_READINESS_MATRIX.md",
            "Update DOI/URL fields after external archiving.",
            f"Data dictionary complete: {dictionary['summary']['complete']}",
        ),
        item(
            "Data",
            "Archive and upload readiness matrix",
            "complete",
            "materials/ARCHIVE_UPLOAD_READINESS_MATRIX.md; materials/SUBMISSION_READINESS_DASHBOARD.md",
            "Use as the destination-level map for journal submission, source data, supplement, archive, reviewer support, and author-certified metadata.",
            "The matrix keeps upload decisions explicit and separate from local QC.",
        ),
        item(
            "Data",
            "External archive DOI/accession",
            "limitation",
            "materials/FAIR_ARCHIVE_METADATA.md; materials/RELEASE_ARCHIVE_MANIFEST.md",
            "Deposit the final package in a public archive and update DOI/URL before journal submission.",
            f"External archive pending: {fair['availability']['external_archive_pending']}",
        ),
        item(
            "Code",
            "Code snapshots and reproduction commands",
            "complete",
            "materials/scripts/; materials/dlc/; tables/artifact_provenance.md; materials/REPRODUCTION_GUIDE.md",
            "Use the fast audit path first; rerun expensive rollouts only when needed.",
            f"Artifact provenance: {provenance['complete_count']}/{len(provenance['artifacts'])}",
        ),
        item(
            "Code",
            "Artifact dependency and lineage map",
            "complete",
            "materials/ARTIFACT_DEPENDENCY_MAP.md; materials/ARTIFACT_DEPENDENCY_MAP.csv; materials/ARTIFACT_DEPENDENCY_FILE_EDGES.csv",
            "Use to trace reviewer-facing outputs to registered inputs, scripts, and commands.",
            "The artifact provenance file remains the authoritative command list.",
        ),
        item(
            "Environment",
            "Environment and compute record",
            "complete",
            "environment.yml; materials/ENVIRONMENT_REPRODUCIBILITY_AUDIT.md; tables/compute_cost_report.md",
            "Report GPU inventory and note that exact wall-clock/utilization logging is limited.",
            "Recorded runs used CUDA devices listed in manifest.json.",
        ),
        item(
            "Integrity",
            "Publication package preflight verification",
            "complete",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.md; tables/reproducibility_audit.md",
            "Run this gate after every material change.",
            f"Verification status: {verification['summary']['status']}, failed gates: {verification['summary']['failed_gates']}",
        ),
        item(
            "Integrity",
            "Release manifest and checksums",
            "complete",
            "materials/RELEASE_ARCHIVE_MANIFEST.md; materials/RELEASE_ARCHIVE_MANIFEST.csv",
            "Regenerate immediately before external archive upload.",
            f"Release manifest: {release['summary']['file_count']} files; exact byte size is locked in RELEASE_ARCHIVE_MANIFEST.json.",
        ),
        item(
            "Ethics",
            "Human/animal/personal-data statements",
            "complete",
            "materials/RESEARCH_RISK_AND_SAFETY.md",
            "Use the simulation-only statement in the journal ethics or methods form.",
            risk["ethics_context"]["rationale"],
        ),
        item(
            "Ethics",
            "Real-world deployment boundary",
            "complete",
            "materials/RESEARCH_RISK_AND_SAFETY.md; materials/CLAIM_EVIDENCE_MATRIX.md",
            "Do not describe the simulator evidence as road-vehicle deployment readiness.",
            "No real-vehicle or public-road testing is included.",
        ),
        item(
            "Administrative",
            "Author contributions",
            "needs_author_input",
            "AUTHORS",
            "Prepare journal-specific author contribution statements manually.",
            "The repository AUTHORS file is not a contribution taxonomy.",
        ),
        item(
            "Administrative",
            "Competing interests",
            "needs_author_input",
            "none in package",
            "Authors must provide journal-specific competing-interest disclosures.",
            "The experimental package cannot infer personal or institutional disclosures.",
        ),
        item(
            "Administrative",
            "Funding and acknowledgements",
            "needs_author_input",
            "none in package",
            "Authors must provide funding IDs and acknowledgements in the submission system.",
            "Not derivable from simulator artifacts.",
        ),
        item(
            "Administrative",
            "ORCID and corresponding-author metadata",
            "needs_author_input",
            "none in package",
            "Authors must provide names, affiliations, ORCIDs, and correspondence details.",
            "Not derivable from simulator artifacts.",
        ),
        item(
            "Scope",
            "Remaining scientific limitations",
            "limitation",
            "materials/SUBMISSION_GAP_ACTION_PLAN.md; materials/TOP_JOURNAL_READINESS_CHECKLIST.md",
            "Before making broader claims, run larger-N/fresh-heldout evaluations and close selector/candidate gaps.",
            summary["top_journal_readiness"]["not_ready"][0],
        ),
    ]

    counts = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1

    return {
        "root": str(root),
        "title": "Editorial submission checklist",
        "purpose": "Journal-submission-facing checklist for experimental, reproducibility, data, ethics, and administrative materials.",
        "rows": rows,
        "summary": {
            "item_count": len(rows),
            "status_counts": counts,
            "publication_verification_status": verification["summary"]["status"],
            "artifact_provenance": f"{provenance['complete_count']}/{len(provenance['artifacts'])}",
            "external_archive_pending": fair["availability"]["external_archive_pending"],
        },
        "interpretation": (
            "This checklist separates evidence-package readiness from author- or journal-system metadata that "
            "cannot be inferred from local simulator artifacts."
        ),
    }


def write_csv(report, path):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["category", "requirement", "status", "evidence", "action", "note"],
        )
        writer.writeheader()
        for row in report["rows"]:
            writer.writerow(row)


def write_markdown(report, path):
    lines = [
        "# Editorial Submission Checklist",
        "",
        report["purpose"],
        "",
        report["interpretation"],
        "",
        "## Summary",
        "",
        f"- Items: {report['summary']['item_count']}",
        f"- Status counts: {report['summary']['status_counts']}",
        f"- Publication verification: `{report['summary']['publication_verification_status']}`",
        f"- Artifact provenance: {report['summary']['artifact_provenance']}",
        f"- External archive pending: `{report['summary']['external_archive_pending']}`",
        "",
        "## Checklist",
        "",
        "| category | requirement | status | evidence | action | note |",
        "|---|---|---|---|---|---|",
    ]
    for row in report["rows"]:
        lines.append(
            f"| {row['category']} | {row['requirement']} | {row['status']} | "
            f"`{row['evidence']}` | {row['action']} | {row['note']} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export editorial submission checklist.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_checklist(root)
    out_json = materials / "EDITORIAL_SUBMISSION_CHECKLIST.json"
    out_md = materials / "EDITORIAL_SUBMISSION_CHECKLIST.md"
    out_csv = materials / "EDITORIAL_SUBMISSION_CHECKLIST.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv)}, indent=2))


if __name__ == "__main__":
    main()
