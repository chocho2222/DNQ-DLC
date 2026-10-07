#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def row(section, destination, decision, status, evidence, author_action, boundary, note):
    return {
        "section": section,
        "destination": destination,
        "decision": decision,
        "status": status,
        "evidence": evidence,
        "author_action": author_action,
        "boundary": boundary,
        "note": note,
    }


def build_report(root):
    slim = load_json(root / "materials" / "SLIM_SUBMISSION_PACKAGE_MANIFEST.json")
    size_budget = load_json(root / "materials" / "ARCHIVE_SIZE_BUDGET_REPORT.json")
    upload_plan = load_json(root / "materials" / "SUBMISSION_UPLOAD_SELECTION_PLAN.json")
    final_bundle = load_json(root / "materials" / "FINAL_SUBMISSION_FILE_BUNDLE.json")
    portal = load_json(root / "materials" / "SUBMISSION_PORTAL_FIELD_COMPLETION_PACK.json")
    archive = load_json(root / "materials" / "ARCHIVE_README.json")
    citation = load_json(root / "materials" / "CITATION_METADATA.json")
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    smoke = load_json(root / "materials" / "PUBLICATION_SMOKE_TEST.json")

    rows = [
        row(
            "pre_upload_gate",
            "internal_pre_submission_qc",
            "run_before_upload",
            "pass" if verification["summary"]["status"] == "pass" else "review_required",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.md; materials/PUBLICATION_SMOKE_TEST.md",
            "Confirm both local gates pass after any final edits.",
            "Local gates check package consistency; they do not certify journal acceptance. The smoke test remains the final independent gate.",
            f"Verification={verification['summary']['status']}; smoke={smoke['summary']['status']}.",
        ),
        row(
            "main_text",
            "journal_submission",
            "convert_to_target_template",
            "author_action_required",
            "manuscript/main.md; manuscript/main.tex; manuscript/references.bib",
            "Convert journal-neutral sources to the selected journal template and final PDF/source package.",
            "Author metadata, journal template compliance, and final PDF remain author-owned.",
            "Do not upload the neutral source unchanged unless the journal explicitly accepts it.",
        ),
        row(
            "figures",
            "main_figure_upload",
            "choose_pdf_svg_or_tiff_by_journal_rules",
            "ready_with_author_selection",
            "materials/SLIM_SUBMISSION_PACKAGE_MANIFEST.md; materials/ARCHIVE_SIZE_BUDGET_REPORT.md",
            "Use PDF/SVG for lightweight review when allowed; use TIFF through figure/large-file channels when required.",
            "Figure exports summarize simulator-only evidence and must remain linked to source data.",
            (
                "large_tiff_reference=materials/SLIM_SUBMISSION_PACKAGE_MANIFEST.json; "
                "size_flag_reference=materials/ARCHIVE_SIZE_BUDGET_REPORT.json."
            ),
        ),
        row(
            "source_data",
            "source_data_upload",
            "upload_core_csv_source_data",
            "ready",
            "figures/figure_1_source_data.csv; figures/figure_2_source_data.csv; figures/figure_3_source_data.csv; tables/seed_outcome_ledger.csv",
            "Upload required source-data CSV files or place them in the journal source-data system.",
            "Source data cover saved simulator seed partitions only.",
            "Keep checksums in the full archive manifest for later reviewer audit.",
        ),
        row(
            "supplement",
            "supplementary_information",
            "upload_core_reviewer_supplement",
            "ready",
            "materials/SUPPLEMENTARY_INDEX.md; materials/MANUSCRIPT_SUPPLEMENT_ASSEMBLY_MAP.md; materials/STATISTICAL_REPORTING_APPENDIX.md",
            "Upload the core supplement/navigator files unless the journal requires consolidation into one PDF.",
            "Supplement coordinates existing evidence and does not add broader validation.",
            (
                f"Slim package has {slim['summary']['slim_file_count']} files; "
                "size reference=materials/SLIM_SUBMISSION_PACKAGE_MANIFEST.json."
            ),
        ),
        row(
            "archive",
            "public_archive",
            "deposit_full_release_then_update_doi",
            "author_action_required",
            "materials/ARCHIVE_README.md; materials/RELEASE_ARCHIVE_MANIFEST.csv; materials/FAIR_ARCHIVE_METADATA.md",
            "Deposit the full release package, obtain DOI/URL/accession, then update availability and citation fields.",
            "Local archive metadata is not a public archive record before deposition.",
            f"Full release size is locked in RELEASE_ARCHIVE_MANIFEST.json; files={size_budget['summary']['release_file_count']}.",
        ),
        row(
            "portal_fields",
            "journal_portal_forms",
            "copy_after_author_certification",
            "author_action_required",
            "materials/SUBMISSION_PORTAL_FIELD_COMPLETION_PACK.md; materials/SUBMISSION_METADATA_DRAFT.md",
            "Complete authorship, disclosures, funding, conflicts, ethics fields, and archive identifiers in the portal.",
            "The local package must not invent ORCID, funding, conflict, DOI, or target-journal information.",
            (
                f"Portal fields={portal['summary']['field_count']}; "
                f"author-required={portal['summary']['author_required_count']}; "
                f"copy-after-archive={portal['summary']['copy_after_archive_count']}."
            ),
        ),
        row(
            "large_files",
            "large_file_or_archive_channel",
            "route_large_tiffs_and_traces_outside_slim_upload",
            "ready_with_size_review",
            "materials/ARCHIVE_SIZE_BUDGET_REPORT.md; materials/SLIM_SUBMISSION_PACKAGE_ARCHIVE_ONLY.csv",
            "Keep large TIFFs, traces, sweeps, and detailed diagnostics in the full archive or special large-file channel.",
            "Large-file routing is operational planning, not a journal-specific rule.",
            (
                f"Archive-only/slim-excluded rows={slim['summary']['excluded_or_archive_only_count']}; "
                f"budget status={size_budget['summary']['status']}."
            ),
        ),
        row(
            "citation",
            "data_code_availability_statement",
            "update_after_public_deposition",
            "author_action_required",
            "materials/CITATION_METADATA.md; materials/DATA_CODE_AVAILABILITY.md",
            "Update DOI/URL/accession and final citation after public deposition.",
            "External identifiers remain pending until authors deposit the archive.",
            (
                f"External DOI present={citation['summary']['external_doi_present']}; "
                f"external URL present={citation['summary']['external_url_present']}; "
                f"citation author-required rows={citation['summary']['author_required_count']}; "
                f"archive author-required rows={archive['summary']['archive_author_required_count']}."
            ),
        ),
    ]

    status_counts = {}
    for item in rows:
        status_counts[item["status"]] = status_counts.get(item["status"], 0) + 1
    author_actions = [item for item in rows if item["status"] == "author_action_required"]
    review_required = [item for item in rows if item["status"] == "review_required"]

    return {
        "root": str(root),
        "title": "Target-Journal Upload Decision Checklist",
        "purpose": (
            "Translate the slim package, final bundle, portal-field pack, and archive size budget into "
            "a conservative target-journal upload decision checklist."
        ),
        "summary": {
            "status": "ready_with_author_actions" if not review_required else "review_required",
            "row_count": len(rows),
            "author_action_required_count": len(author_actions),
            "review_required_count": len(review_required),
            "status_counts": status_counts,
            "slim_file_count": slim["summary"]["slim_file_count"],
            "slim_size_reference": "materials/SLIM_SUBMISSION_PACKAGE_MANIFEST.json",
            "full_release_file_count": size_budget["summary"]["release_file_count"],
            "full_release_size_reference": "materials/RELEASE_ARCHIVE_MANIFEST.json",
            "final_bundle_missing_required_count": final_bundle["summary"]["missing_required_count"],
            "upload_plan_journal_candidates": upload_plan["summary"]["journal_portal_candidate_count"],
        },
        "rows": rows,
        "interpretation": (
            "This checklist is journal-neutral. Authors must still follow the selected journal portal, figure, "
            "source-data, supplement, and archive-deposition rules."
        ),
    }


def write_csv(report, path):
    fields = ["section", "destination", "decision", "status", "evidence", "author_action", "boundary", "note"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in report["rows"]:
            writer.writerow(item)


def write_markdown(report, path):
    lines = [
        "# Target-Journal Upload Decision Checklist",
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
            "## Checklist",
            "",
            "| section | destination | decision | status | evidence | author action | boundary |",
            "|---|---|---|---|---|---|---|",
        ]
    )
    for item in report["rows"]:
        lines.append(
            f"| {item['section']} | {item['destination']} | {item['decision']} | {item['status']} | "
            f"`{item['evidence']}` | {item['author_action']} | {item['boundary']} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export target-journal upload decision checklist.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_report(root)
    out_json = materials / "TARGET_JOURNAL_UPLOAD_DECISION_CHECKLIST.json"
    out_md = materials / "TARGET_JOURNAL_UPLOAD_DECISION_CHECKLIST.md"
    out_csv = materials / "TARGET_JOURNAL_UPLOAD_DECISION_CHECKLIST.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv), "summary": report["summary"]}, indent=2))


if __name__ == "__main__":
    main()
