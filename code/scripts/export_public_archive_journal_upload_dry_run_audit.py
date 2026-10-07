#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def split_paths(value):
    if isinstance(value, list):
        return value
    if not value:
        return []
    return [item.strip() for item in str(value).split(";") if item.strip()]


def dry_row(check_id, stage, upload_channel, status, local_files, evidence, author_action, boundary, note):
    return {
        "check_id": check_id,
        "stage": stage,
        "upload_channel": upload_channel,
        "status": status,
        "local_files": local_files,
        "evidence": evidence,
        "author_action": author_action,
        "boundary": boundary,
        "note": note,
    }


def file_status(root, release_paths, documented_exclusions, paths):
    checked = []
    for rel in paths:
        p = root / rel
        checked.append(
            {
                "path": rel,
                "exists": p.exists(),
                "in_release_manifest": rel in release_paths,
                "documented_release_exclusion": rel in documented_exclusions,
                "size_bytes": p.stat().st_size if p.exists() and p.is_file() else None,
            }
        )
    missing = [item["path"] for item in checked if not item["exists"]]
    missing_release = [item["path"] for item in checked if item["exists"] and not item["in_release_manifest"]]
    undocumented_missing_release = [
        item["path"]
        for item in checked
        if item["exists"] and not item["in_release_manifest"] and not item["documented_release_exclusion"]
    ]
    documented_missing_release = [
        item["path"]
        for item in checked
        if item["exists"] and not item["in_release_manifest"] and item["documented_release_exclusion"]
    ]
    return checked, missing, missing_release, undocumented_missing_release, documented_missing_release


def build_report(root):
    materials = root / "materials"
    release = load_json(materials / "RELEASE_ARCHIVE_MANIFEST.json")
    freeze = load_json(materials / "FINAL_CHECKSUM_FREEZE_RECORD.json")
    verification = load_json(materials / "PUBLICATION_PACKAGE_VERIFICATION.json")
    smoke = load_json(materials / "PUBLICATION_SMOKE_TEST.json")
    final_bundle = load_json(materials / "FINAL_SUBMISSION_FILE_BUNDLE.json")
    upload_plan = load_json(materials / "SUBMISSION_UPLOAD_SELECTION_PLAN.json")
    slim = load_json(materials / "SLIM_SUBMISSION_PACKAGE_MANIFEST.json")
    size_budget = load_json(materials / "ARCHIVE_SIZE_BUDGET_REPORT.json")
    portal = load_json(materials / "SUBMISSION_PORTAL_FIELD_COMPLETION_PACK.json")
    archive = load_json(materials / "ARCHIVE_UPLOAD_READINESS_MATRIX.json")
    exclusion = load_json(materials / "ARCHIVE_MANIFEST_EXCLUSION_AUDIT.json")
    gap = load_json(materials / "AUTHOR_UPLOAD_GAP_CLOSURE_AUDIT.json")
    citation = load_json(materials / "CITATION_METADATA.json")
    fair = load_json(materials / "FAIR_ARCHIVE_METADATA.json")
    provenance = load_json(root / "tables" / "artifact_provenance.json")
    dictionary = load_json(materials / "DATA_DICTIONARY.json")

    release_paths = {item["path"] for item in release["files"]}
    documented_exclusions = {item["path"] for item in exclusion["rows"] if item.get("status") == "pass"}
    fair_identifier_pending = fair.get("availability", {}).get("external_archive_pending")
    if fair_identifier_pending is None:
        fair_identifier_pending = not (
            fair.get("identifier", {}).get("external_doi") or fair.get("identifier", {}).get("external_url")
        )

    core_journal_files = [
        "manuscript/main.md",
        "manuscript/main.tex",
        "manuscript/references.bib",
        "materials/TITLE_ABSTRACT_HIGHLIGHTS_PACKAGE.md",
        "materials/COVER_LETTER_DRAFT_PACKAGE.md",
        "materials/SUBMISSION_PORTAL_FIELD_COMPLETION_PACK.md",
    ]
    figure_files = [
        "figures/figure_1_multicar_overtake_results.pdf",
        "figures/figure_2_portfolio_selector_summary.pdf",
        "figures/figure_3_cross_heldout_validation.pdf",
        "figures/figure_1_source_data.csv",
        "figures/figure_2_source_data.csv",
        "figures/figure_3_source_data.csv",
    ]
    supplement_files = [
        "materials/SUPPLEMENTARY_INDEX.md",
        "materials/REPORTING_SUPPLEMENT_NAVIGATOR.md",
        "materials/REVIEWER_REPLICATION_ROUTE.md",
        "materials/REVIEWER_COMMAND_PREFLIGHT.md",
        "materials/MANUSCRIPT_SUPPLEMENT_ASSEMBLY_MAP.md",
        "materials/STATISTICAL_REPORTING_APPENDIX.md",
    ]
    archive_files = [
        "materials/ARCHIVE_README.md",
        "materials/RELEASE_ARCHIVE_MANIFEST.json",
        "materials/RELEASE_ARCHIVE_MANIFEST.csv",
        "materials/FAIR_ARCHIVE_METADATA.md",
        "materials/CITATION_METADATA.md",
        "materials/DATA_CODE_AVAILABILITY.md",
    ]

    file_groups = {
        "journal_text": core_journal_files,
        "figures_source_data": figure_files,
        "supplement": supplement_files,
        "public_archive": archive_files,
    }
    group_results = {}
    for name, paths in file_groups.items():
        checked, missing, missing_release, undocumented_missing_release, documented_missing_release = file_status(
            root, release_paths, documented_exclusions, paths
        )
        group_results[name] = {
            "checked": checked,
            "missing": missing,
            "missing_from_release": missing_release,
            "undocumented_missing_from_release": undocumented_missing_release,
            "documented_release_exclusions": documented_missing_release,
        }

    rows = [
        dry_row(
            "DRY01_local_gates",
            "pre_upload",
            "internal_qc",
            "pass" if verification["summary"]["status"] == "pass" else "review_required",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.md; materials/PUBLICATION_SMOKE_TEST.md",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json; materials/PUBLICATION_SMOKE_TEST.json",
            "Rerun both gates after final author edits, archive DOI insertion, or file renaming.",
            "Local gates are package checks, not journal acceptance or public-deposition receipts. The smoke-test status is contextual here and remains the final independent gate.",
            f"verification={verification['summary']['status']}; smoke={smoke['summary']['status']}.",
        ),
        dry_row(
            "DRY02_journal_text_files",
            "journal_upload",
            "main_manuscript_or_portal_text",
            "pass" if not group_results["journal_text"]["missing"] else "review_required",
            "; ".join(core_journal_files),
            "materials/FINAL_SUBMISSION_FILE_BUNDLE.md; materials/SUBMISSION_PORTAL_FIELD_COMPLETION_PACK.md",
            "Convert journal-neutral sources and portal text into the selected journal template.",
            "No target-journal template, author metadata, or final PDF is certified by this local dry run.",
            (
                f"missing={len(group_results['journal_text']['missing'])}; "
                f"undocumented_release_missing={len(group_results['journal_text']['undocumented_missing_from_release'])}; "
                f"documented_exclusions={len(group_results['journal_text']['documented_release_exclusions'])}."
            ),
        ),
        dry_row(
            "DRY03_figures_source_data",
            "journal_upload",
            "main_figures_and_source_data",
            "pass" if not group_results["figures_source_data"]["missing"] else "review_required",
            "; ".join(figure_files),
            "materials/FIGURE_SOURCE_DATA_AUDIT.md; materials/FIGURE_TECHNICAL_QC.md",
            "Upload figures/source-data files according to the selected journal production rules.",
            "Figures and source data summarize simulator evidence only.",
            (
                f"missing={len(group_results['figures_source_data']['missing'])}; "
                f"undocumented_release_missing={len(group_results['figures_source_data']['undocumented_missing_from_release'])}; "
                "large_tiff_reference=materials/SLIM_SUBMISSION_PACKAGE_MANIFEST.json."
            ),
        ),
        dry_row(
            "DRY04_supplement_bundle",
            "journal_upload",
            "supplementary_information",
            "pass" if not group_results["supplement"]["missing"] else "review_required",
            "; ".join(supplement_files),
            "materials/SUPPLEMENT_UPLOAD_DECISION_MATRIX.md; materials/SUPPLEMENTARY_TABLE_LEGENDS.md",
            "Use target-journal rules to decide whether to upload as separate files or a consolidated supplement.",
            "Supplement files coordinate existing evidence; they do not add new validation.",
            (
                f"missing={len(group_results['supplement']['missing'])}; "
                f"documented_exclusions={len(group_results['supplement']['documented_release_exclusions'])}; "
                f"optional_author_selection={upload_plan['summary']['author_selection_required_count']}."
            ),
        ),
        dry_row(
            "DRY05_public_archive_deposit",
            "public_archive",
            "full_release_deposition",
            "author_action_required" if fair_identifier_pending else "pass",
            "; ".join(archive_files),
            "materials/ARCHIVE_README.md; materials/FAIR_ARCHIVE_METADATA.md; materials/CITATION_METADATA.md",
            "Deposit the full release, obtain DOI/URL/accession, then update availability and citation fields.",
            "The dry run must not claim an external DOI or accession before public deposition.",
            (
                f"release_files={release['summary']['file_count']}; "
                "exact_release_size_locked_in=materials/RELEASE_ARCHIVE_MANIFEST.json; "
                f"doi_present={citation['summary']['external_doi_present']}; "
                f"url_present={citation['summary']['external_url_present']}."
            ),
        ),
        dry_row(
            "DRY06_size_routing",
            "upload_routing",
            "large_file_and_archive_only_routing",
            size_budget["summary"]["status"],
            "materials/ARCHIVE_SIZE_BUDGET_REPORT.md; materials/SLIM_SUBMISSION_PACKAGE_MANIFEST.md",
            "materials/ARCHIVE_SIZE_BUDGET_REPORT.json; materials/SLIM_SUBMISSION_PACKAGE_MANIFEST.json",
            "Route large TIFF, trace, sweep, and diagnostic files through archive or large-file channels.",
            "Size flags are operational upload planning, not evidence failures.",
            (
                "release_size_reference=materials/ARCHIVE_SIZE_BUDGET_REPORT.json; "
                f"single_file_over_50mb={size_budget['summary']['single_file_over_50mb_count']}; "
                f"budget_flags={size_budget['summary']['budget_review_required_count']}."
            ),
        ),
        dry_row(
            "DRY07_author_certification_fields",
            "journal_portal",
            "author_metadata_and_disclosures",
            "author_action_required" if portal["summary"]["author_required_count"] else "pass",
            "materials/SUBMISSION_PORTAL_FIELD_COMPLETION_PACK.md; materials/ETHICS_DISCLOSURE_READINESS_PACK.md",
            "materials/SUBMISSION_PORTAL_FIELD_COMPLETION_PACK.json; materials/AUTHOR_UPLOAD_GAP_CLOSURE_AUDIT.json",
            "Authors must certify affiliations, ORCID/contact, conflicts, funding, acknowledgements, CRediT roles, and archive identifiers.",
            "Automation does not infer or certify author-owned declarations.",
            f"portal_author_required={portal['summary']['author_required_count']}; gap_author_actions={gap['summary']['author_action_required_count']}.",
        ),
        dry_row(
            "DRY08_manifest_freeze",
            "pre_deposit",
            "checksum_manifest_and_freeze",
            "pass" if freeze["summary"]["status"] == "ready_for_author_freeze" else "review_required",
            "materials/RELEASE_ARCHIVE_MANIFEST.json; materials/FINAL_CHECKSUM_FREEZE_RECORD.md",
            "materials/FINAL_CHECKSUM_FREEZE_RECORD.json",
            "Regenerate the release manifest and freeze record after any file changes before archive upload.",
            "Freeze readiness is local until public deposition assigns an external identifier.",
            f"freeze={freeze['summary']['status']}; manifest_files={release['summary']['file_count']}.",
        ),
    ]

    review_required = [item for item in rows if item["status"] == "review_required"]
    author_required = [item for item in rows if item["status"] == "author_action_required"]
    release_missing_total = sum(len(item["missing_from_release"]) for item in group_results.values())
    undocumented_release_missing_total = sum(
        len(item["undocumented_missing_from_release"]) for item in group_results.values()
    )
    documented_release_exclusion_total = sum(len(item["documented_release_exclusions"]) for item in group_results.values())
    missing_total = sum(len(item["missing"]) for item in group_results.values())
    status_counts = {}
    for item in rows:
        status_counts[item["status"]] = status_counts.get(item["status"], 0) + 1

    return {
        "root": str(root),
        "title": "Public Archive and Journal Upload Dry-Run Audit",
        "purpose": (
            "Simulate the final journal-upload and public-archive handoff without uploading anything, checking local gates, "
            "file presence, release-manifest coverage, upload routing, size boundaries, author-certified fields, and archive DOI status."
        ),
        "summary": {
            "status": "pass" if not review_required else "review_required",
            "row_count": len(rows),
            "review_required_count": len(review_required),
            "author_action_required_count": len(author_required),
            "status_counts": status_counts,
            "checked_file_count": sum(len(paths) for paths in file_groups.values()),
            "missing_file_count": missing_total,
            "missing_from_release_count": release_missing_total,
            "undocumented_missing_from_release_count": undocumented_release_missing_total,
            "documented_release_exclusion_count": documented_release_exclusion_total,
            "publication_verification_status": verification["summary"]["status"],
            "publication_smoke_test_reference": "materials/PUBLICATION_SMOKE_TEST.json",
            "artifact_provenance": f"{provenance['complete_count']}/{len(provenance['artifacts'])}",
            "data_dictionary_complete": dictionary["summary"]["complete"],
            "release_file_count": release["summary"]["file_count"],
            "release_size_reference": "materials/RELEASE_ARCHIVE_MANIFEST.json",
            "final_bundle_missing_required": final_bundle["summary"]["missing_required_count"],
            "archive_upload_status": archive["summary"]["status"],
            "archive_manifest_exclusion_status": exclusion["summary"]["status"],
            "fair_external_identifier_pending": fair_identifier_pending,
        },
        "rows": rows,
        "file_groups": group_results,
        "interpretation": (
            "This dry run is a local pre-upload audit. It does not perform deposition, does not create DOI/accession records, "
            "does not certify author metadata, and does not replace target-journal instructions."
        ),
    }


def write_csv(report, path):
    fields = [
        "check_id",
        "stage",
        "upload_channel",
        "status",
        "local_files",
        "evidence",
        "author_action",
        "boundary",
        "note",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(report["rows"])


def write_markdown(report, path):
    lines = [
        "# Public Archive and Journal Upload Dry-Run Audit",
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
            "## Dry-Run Checks",
            "",
            "| check | stage | channel | status | files | author action | boundary | note |",
            "|---|---|---|---|---|---|---|---|",
        ]
    )
    for item in report["rows"]:
        lines.append(
            f"| {item['check_id']} | {item['stage']} | {item['upload_channel']} | {item['status']} | "
            f"`{item['local_files']}` | {item['author_action']} | {item['boundary']} | {item['note']} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export public archive and journal upload dry-run audit.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_report(root)
    out_json = materials / "PUBLIC_ARCHIVE_JOURNAL_UPLOAD_DRY_RUN_AUDIT.json"
    out_md = materials / "PUBLIC_ARCHIVE_JOURNAL_UPLOAD_DRY_RUN_AUDIT.md"
    out_csv = materials / "PUBLIC_ARCHIVE_JOURNAL_UPLOAD_DRY_RUN_AUDIT.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv), "summary": report["summary"]}, indent=2))


if __name__ == "__main__":
    main()
