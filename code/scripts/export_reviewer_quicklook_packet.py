#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def size_mb(size_bytes):
    if size_bytes in {"", None}:
        return ""
    return round(size_bytes / (1024 * 1024), 3)


def row(section, path, upload_role, priority, evidence, reviewer_check, rationale, boundary, status, note=""):
    return {
        "section": section,
        "path": path,
        "upload_role": upload_role,
        "priority": priority,
        "evidence": evidence,
        "reviewer_check": reviewer_check,
        "rationale": rationale,
        "boundary": boundary,
        "status": status,
        "note": note,
    }


def manifest_map(release):
    return {item["path"]: item for item in release["files"]}


def enrich_size(rows, release_by_path, root):
    enriched = []
    for item in rows:
        path = root / item["path"]
        manifest = release_by_path.get(item["path"])
        if manifest:
            size_bytes = manifest["size_bytes"]
            sha256 = manifest["sha256"]
        elif path.exists():
            size_bytes = path.stat().st_size
            sha256 = ""
        else:
            size_bytes = ""
            sha256 = ""
        enriched.append({**item, "size_bytes": size_bytes, "size_mb": size_mb(size_bytes), "sha256": sha256})
    return enriched


def build_report(root):
    release = load_json(root / "materials" / "RELEASE_ARCHIVE_MANIFEST.json")
    slim = load_json(root / "materials" / "SLIM_SUBMISSION_PACKAGE_MANIFEST.json")
    trace = load_json(root / "materials" / "REVIEWER_EVIDENCE_TRACE_PACK.json")
    response_seed = load_json(root / "materials" / "REVIEWER_RESPONSE_SEED_PACK.json")
    revision_checklist = load_json(root / "materials" / "REVISION_RESPONSE_EXECUTION_CHECKLIST.json")
    copyedit_lock = load_json(root / "materials" / "PORTAL_COPYEDIT_LOCK_AUDIT.json")
    blinded_audit = load_json(root / "materials" / "BLINDED_REVIEW_ANONYMIZATION_AUDIT.json")
    ai_disclosure = load_json(root / "materials" / "AI_TOOL_USE_DISCLOSURE_AUDIT.json")
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    smoke = load_json(root / "materials" / "PUBLICATION_SMOKE_TEST.json")
    dictionary = load_json(root / "materials" / "DATA_DICTIONARY.json")
    bundle = load_json(root / "materials" / "FINAL_SUBMISSION_FILE_BUNDLE.json")
    command_preflight = load_json(root / "materials" / "REVIEWER_COMMAND_PREFLIGHT.json")
    upload_gap = load_json(root / "materials" / "AUTHOR_UPLOAD_GAP_CLOSURE_AUDIT.json")
    upload_dry_run = load_json(root / "materials" / "PUBLIC_ARCHIVE_JOURNAL_UPLOAD_DRY_RUN_AUDIT.json")
    release_by_path = manifest_map(release)

    rows = [
        row(
            "start_here",
            "materials/SUBMISSION_READINESS_DASHBOARD.md",
            "reviewer_quicklook_start",
            "required_quicklook",
            "materials/SUBMISSION_READINESS_DASHBOARD.json",
            "Confirm local package gates pass and remaining actions are author/journal/archive tasks.",
            "Fast top-level readiness entry point.",
            "Dashboard is not a journal receipt and does not certify author-owned metadata.",
            "ready",
        ),
        row(
            "start_here",
            "materials/REPORTING_SUPPLEMENT_NAVIGATOR.md",
            "reviewer_quicklook_navigation",
            "required_quicklook",
            "materials/REPORTING_SUPPLEMENT_NAVIGATOR.json",
            "Use the navigator to choose the shortest route to claims, methods, figures, statistics, and archive files.",
            "Condensed map of the reporting package.",
            "Navigation file only; underlying evidence remains authoritative.",
            "ready",
        ),
        row(
            "claims",
            "materials/CLAIM_EVIDENCE_MATRIX.md",
            "claim_audit",
            "required_quicklook",
            "materials/CLAIM_EVIDENCE_MATRIX.json; materials/MANUSCRIPT_CLAIM_QA.md",
            "Check that each claim has evidence and an explicit do-not-claim boundary.",
            "Shortest claim-to-evidence audit path.",
            "Claims remain simulator-only and seed-set bounded.",
            "ready",
        ),
        row(
            "claims",
            "materials/CLAIM_DOWNGRADE_MAP.md",
            "claim_boundary_wording",
            "required_quicklook",
            "materials/CLAIM_BOUNDARY_COMMUNICATION_PACK.json; materials/WHAT_THIS_PAPER_DOES_NOT_CLAIM.md",
            "Check risky wording is downgraded to evidence-bounded language before submission or reviewer response.",
            "Fast editor-facing guardrail for overclaim prevention.",
            "Communication guardrail only; it adds no empirical evidence.",
            "ready",
        ),
        row(
            "claims",
            "materials/REVIEWER_EVIDENCE_TRACE_PACK.md",
            "claim_to_file_trace",
            "required_quicklook",
            "materials/REVIEWER_EVIDENCE_TRACE_PACK.json",
            f"Inspect {trace['summary']['trace_row_count']} trace rows; review-required rows should be zero.",
            "Claim, figure, statistics, dashboard, and package-gate trace.",
            "Trace pack does not replace source data or statistical checks.",
            "ready" if trace["summary"]["review_required_count"] == 0 else "review_required",
        ),
        row(
            "claims",
            "materials/REVIEWER_RESPONSE_SEED_PACK.md",
            "reviewer_response_seed",
            "recommended_quicklook",
            "materials/REVIEWER_RESPONSE_SEED_PACK.json; materials/REVIEWER_RISK_RESPONSE_DOSSIER.md",
            f"Review {response_seed['summary']['row_count']} response seeds before drafting rebuttal or editor-facing clarifications.",
            "Fast response-preparation route with claim boundaries attached.",
            "Response seeds are not final author-certified rebuttal text.",
            response_seed["summary"]["status"],
        ),
        row(
            "claims",
            "materials/REVISION_RESPONSE_EXECUTION_CHECKLIST.md",
            "revision_response_execution",
            "recommended_quicklook",
            "materials/REVISION_RESPONSE_EXECUTION_CHECKLIST.json; materials/REVIEWER_RESPONSE_SEED_PACK.md",
            f"Review {revision_checklist['summary']['row_count']} revision actions and fill manuscript line references after revision.",
            "Turns response seeds into author-execution tasks.",
            "Checklist is not final rebuttal text.",
            revision_checklist["summary"]["status"],
        ),
        row(
            "claims",
            "materials/PORTAL_COPYEDIT_LOCK_AUDIT.md",
            "portal_copyedit_lock",
            "recommended_quicklook",
            "materials/PORTAL_COPYEDIT_LOCK_AUDIT.json; materials/CLAIM_DOWNGRADE_MAP.md",
            f"Check blocker count is {copyedit_lock['summary']['blocker_count']} before portal copy-paste.",
            "Fast short-form text overclaim scan.",
            "Audit applies only to saved drafts and must be rerun after copyedits.",
            copyedit_lock["summary"]["status"],
        ),
        row(
            "claims",
            "materials/BLINDED_REVIEW_ANONYMIZATION_AUDIT.md",
            "blinded_review_readiness",
            "recommended_quicklook",
            "materials/BLINDED_REVIEW_ANONYMIZATION_AUDIT.json; materials/BLINDED_REVIEW_ANONYMIZATION_SCAN_HITS.csv",
            f"Review {blinded_audit['summary']['scan_hit_count']} blind-review scan hits if the venue requires anonymization.",
            "Fast route for double-blind/single-blind package decisions.",
            "Audit does not anonymize files or certify target-journal policy.",
            blinded_audit["summary"]["status"],
        ),
        row(
            "claims",
            "materials/AI_TOOL_USE_DISCLOSURE_AUDIT.md",
            "ai_tool_use_disclosure",
            "recommended_quicklook",
            "materials/AI_TOOL_USE_DISCLOSURE_AUDIT.json; materials/AI_TOOL_USE_DISCLOSURE_SCAN_HITS.csv",
            f"Review {ai_disclosure['summary']['scan_hit_count']} AI/tool-use scan hits and author-required declaration rows before upload.",
            "Fast route for AI/tool-use disclosure preparation.",
            "Audit does not certify private author tool use or replace journal forms.",
            ai_disclosure["summary"]["status"],
        ),
        row(
            "figures",
            "figures/figure_1_source_data.csv",
            "figure_source_data",
            "required_quicklook",
            "figures/figure_1_multicar_overtake_results.pdf; figures/figure_1_multicar_overtake_results.svg",
            "Confirm the main multicar overtaking source rows used for Figure 1.",
            "Small machine-readable source data behind Figure 1.",
            "Qualitative figure exports must stay linked to source data after production edits.",
            "ready",
        ),
        row(
            "figures",
            "figures/figure_2_source_data.csv",
            "figure_source_data",
            "required_quicklook",
            "figures/figure_2_portfolio_selector_summary.pdf; figures/figure_2_portfolio_selector_summary.svg",
            "Confirm selector/portfolio source rows used for Figure 2.",
            "Small machine-readable source data behind Figure 2.",
            "Selector claims remain limited to saved simulator seed partitions.",
            "ready",
        ),
        row(
            "figures",
            "figures/figure_3_source_data.csv",
            "figure_source_data",
            "required_quicklook",
            "figures/figure_3_cross_heldout_validation.pdf; figures/figure_3_cross_heldout_validation.svg",
            "Confirm cross-heldout source rows and linked dictionary for Figure 3.",
            "Small machine-readable source data behind Figure 3.",
            "Heldout4 supports post-repair external validation with partial transfer, not broad robustness.",
            "ready",
        ),
        row(
            "statistics",
            "materials/STATISTICAL_REPORTING_APPENDIX.md",
            "statistics_quicklook",
            "required_quicklook",
            "tables/cross_heldout_statistical_supplement_rows.csv; materials/STATISTICAL_CONSISTENCY_AUDIT.md",
            "Check Wilson intervals, exact paired tests, and consistency-audit status.",
            "Compact statistical audit path for main quantitative claims.",
            "Small-N descriptive statistics; no broad robustness claim.",
            "ready",
        ),
        row(
            "reproducibility",
            "materials/REVIEWER_REPLICATION_ROUTE.md",
            "replication_route",
            "recommended_quicklook",
            "materials/PUBLICATION_SMOKE_TEST.md; tables/artifact_provenance.md",
            "Choose fast static checks first; run expensive GPU rollout tiers only when needed.",
            "Reviewer-facing replication workflow.",
            "Replication plan does not add new empirical evidence.",
            "ready",
        ),
        row(
            "reproducibility",
            "materials/REVIEWER_COMMAND_PREFLIGHT.md",
            "replication_command_preflight",
            "recommended_quicklook",
            "materials/REVIEWER_COMMAND_PREFLIGHT.json; materials/REVIEWER_REPLICATION_ROUTE.md",
            (
                f"Check {command_preflight['summary']['subcommand_count']} reviewer subcommands have "
                f"{command_preflight['summary']['review_required_count']} review-required rows before execution."
            ),
            "Static command readiness check before optional reruns.",
            "Preflight does not execute commands, rerun rollouts, or add empirical evidence.",
            command_preflight["summary"]["status"],
        ),
        row(
            "archive",
            "materials/SLIM_SUBMISSION_PACKAGE_MANIFEST.md",
            "slim_upload_map",
            "recommended_quicklook",
            "materials/ARCHIVE_SIZE_BUDGET_REPORT.md; materials/FINAL_SUBMISSION_FILE_BUNDLE.md",
            f"Check {slim['summary']['slim_file_count']} slim files versus full release size and archive-only rows.",
            "Small journal-facing file set that points to the full archive.",
            "Operational planning aid; public DOI/accession remains pending until deposition.",
            slim["summary"]["status"],
        ),
        row(
            "archive",
            "materials/AUTHOR_UPLOAD_GAP_CLOSURE_AUDIT.md",
            "author_upload_gap_closure",
            "recommended_quicklook",
            "materials/AUTHOR_UPLOAD_GAP_CLOSURE_AUDIT.json; materials/FINAL_AUTHOR_HANDOFF_CHECKLIST.md",
            (
                f"Confirm local upload-entry gap closure has {upload_gap['summary']['review_required_count']} "
                f"review-required rows and {upload_gap['summary']['author_action_required_count']} author-action rows."
            ),
            "Fast author-handoff check for local entry alignment and remaining author-owned actions.",
            "A pass is local gap closure only; DOI/accession, certified metadata, and journal upload choices remain author-owned.",
            upload_gap["summary"]["status"],
        ),
        row(
            "archive",
            "materials/PUBLIC_ARCHIVE_JOURNAL_UPLOAD_DRY_RUN_AUDIT.md",
            "public_archive_journal_upload_dry_run",
            "recommended_quicklook",
            "materials/PUBLIC_ARCHIVE_JOURNAL_UPLOAD_DRY_RUN_AUDIT.json; materials/ARCHIVE_MANIFEST_EXCLUSION_AUDIT.md",
            (
                f"Confirm {upload_dry_run['summary']['checked_file_count']} dry-run file checks have "
                f"{upload_dry_run['summary']['review_required_count']} review-required rows and "
                f"{upload_dry_run['summary']['undocumented_missing_from_release_count']} undocumented release-missing files."
            ),
            "Fast no-upload rehearsal for journal upload and public archive handoff.",
            "Dry run does not upload files, mint DOI/accession records, or certify author declarations.",
            upload_dry_run["summary"]["status"],
        ),
        row(
            "archive",
            "materials/DATA_DICTIONARY.md",
            "table_dictionary",
            "recommended_quicklook",
            "materials/DATA_DICTIONARY.json",
            f"Confirm {dictionary['summary']['table_count']} tables and complete field definitions.",
            "Reviewer can understand machine-readable CSV fields without opening every generator script.",
            "Dictionary describes saved package tables only.",
            "ready" if dictionary["summary"]["complete"] else "review_required",
        ),
    ]

    rows = enrich_size(rows, release_by_path, root)
    missing = [item for item in rows if not (root / item["path"]).exists()]
    review_required = [item for item in rows if item["status"] == "review_required"]
    total_size = sum(item["size_bytes"] for item in rows if isinstance(item["size_bytes"], int))
    section_counts = {}
    for item in rows:
        section_counts[item["section"]] = section_counts.get(item["section"], 0) + 1

    return {
        "root": str(root),
        "title": "Reviewer Quick-Look Packet",
        "purpose": (
            "Define the smallest reviewer-facing route for auditing the main claims, figures, statistics, "
            "reproducibility, and archive linkage without downloading the full release first."
        ),
        "summary": {
            "status": "pass" if not missing and not review_required else "review_required",
            "file_count": len(rows),
            "packet_size_bytes": total_size,
            "packet_size_mb": size_mb(total_size),
            "missing_files": len(missing),
            "review_required_count": len(review_required),
            "section_counts": section_counts,
            "publication_verification_status": verification["summary"]["status"],
            "publication_smoke_test_reference": "materials/PUBLICATION_SMOKE_TEST.json",
            "slim_package_status": slim["summary"]["status"],
            "final_bundle_missing_required_count": bundle["summary"]["missing_required_count"],
        },
        "rows": rows,
        "interpretation": (
            "This packet is a triage aid. Full source data, release checksums, rollout traces, large TIFF exports, "
            "and author-certified submission fields remain in the full package or journal-specific upload slots."
        ),
    }


def write_csv(report, path):
    fields = [
        "section",
        "path",
        "upload_role",
        "priority",
        "evidence",
        "reviewer_check",
        "rationale",
        "boundary",
        "status",
        "note",
        "size_bytes",
        "size_mb",
        "sha256",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in report["rows"]:
            writer.writerow({field: item.get(field, "") for field in fields})


def write_markdown(report, path):
    lines = [
        "# Reviewer Quick-Look Packet",
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
            "## Quick-Look Files",
            "",
            "| section | priority | status | size MB | path | reviewer check | boundary |",
            "|---|---|---|---:|---|---|---|",
        ]
    )
    for item in report["rows"]:
        lines.append(
            f"| {item['section']} | {item['priority']} | {item['status']} | {item['size_mb']} | "
            f"`{item['path']}` | {item['reviewer_check']} | {item['boundary']} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export reviewer quick-look packet.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_report(root)
    out_json = materials / "REVIEWER_QUICKLOOK_PACKET.json"
    out_md = materials / "REVIEWER_QUICKLOOK_PACKET.md"
    out_csv = materials / "REVIEWER_QUICKLOOK_PACKET.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv), "summary": report["summary"]}, indent=2))


if __name__ == "__main__":
    main()
