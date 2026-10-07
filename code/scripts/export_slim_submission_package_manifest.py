#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


MB = 1024 * 1024


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def size_mb(size_bytes):
    if size_bytes is None:
        return ""
    return round(size_bytes / MB, 3)


def manifest_lookup(release):
    return {row["path"]: row for row in release["files"]}


def add_file(rows, release_by_path, root, section, rel_path, upload_role, priority, source, rationale, boundary):
    item = release_by_path.get(rel_path)
    path = root / rel_path
    is_self_referential_report = rel_path.startswith(
        (
            "materials/ARCHIVE_README",
            "materials/ARCHIVE_SIZE_BUDGET",
            "materials/FAIR_ARCHIVE_METADATA",
            "materials/RELEASE_ARCHIVE_MANIFEST",
            "materials/REPORTING_SUPPLEMENT_NAVIGATOR",
        )
    )
    exists = item is not None or is_self_referential_report
    rows.append(
        {
            "section": section,
            "path": rel_path,
            "upload_role": upload_role,
            "priority": priority,
            "include_in_slim_package": exists,
            "size_bytes": item["size_bytes"] if item else (path.stat().st_size if path.exists() else ""),
            "size_mb": size_mb(item["size_bytes"]) if item else (size_mb(path.stat().st_size) if path.exists() else ""),
            "sha256": item["sha256"] if item else "",
            "source": source,
            "rationale": rationale,
            "boundary": boundary,
            "status": "ready" if exists else "review_required",
        }
    )


def build_report(root):
    release = load_json(root / "materials" / "RELEASE_ARCHIVE_MANIFEST.json")
    final_bundle = load_json(root / "materials" / "FINAL_SUBMISSION_FILE_BUNDLE.json")
    upload_plan = load_json(root / "materials" / "SUBMISSION_UPLOAD_SELECTION_PLAN.json")
    size_budget = load_json(root / "materials" / "ARCHIVE_SIZE_BUDGET_REPORT.json")
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    smoke = load_json(root / "materials" / "PUBLICATION_SMOKE_TEST.json")
    dashboard = load_json(root / "materials" / "SUBMISSION_READINESS_DASHBOARD.json")
    data_dictionary = load_json(root / "materials" / "DATA_DICTIONARY.json")
    provenance = load_json(root / "tables" / "artifact_provenance.json")
    release_by_path = manifest_lookup(release)

    rows = []
    # Journal-facing minimal set: text scaffolds, figures in lightweight editable/review formats,
    # source data, core supplement, and claim/reproducibility navigators.
    for rel_path, role, priority, rationale in [
        ("manuscript/main.md", "main_manuscript_source", "author_template_conversion", "Local conservative manuscript source for target-journal conversion."),
        ("manuscript/main.tex", "journal_neutral_latex_source", "author_template_conversion", "Journal-neutral LaTeX scaffold for conversion to official template."),
        ("manuscript/references.bib", "bibliography", "required_upload", "Starter bibliography with resolved citation keys."),
        ("materials/COVER_LETTER_DRAFT_PACKAGE.md", "cover_letter_source", "author_adaptation", "Evidence-bound cover-letter source requiring author metadata and journal target."),
        ("materials/TITLE_ABSTRACT_HIGHLIGHTS_PACKAGE.md", "portal_short_text", "author_adaptation", "Evidence-bound title, abstract, highlights, keywords, and prohibited wording."),
        ("materials/SUBMISSION_PORTAL_FIELD_COMPLETION_PACK.md", "portal_field_pack", "author_completion", "Draft portal fields separated into copy-ready, archive-dependent, and author-required fields."),
    ]:
        add_file(rows, release_by_path, root, "main_text_and_portal", rel_path, role, priority, "final_bundle; upload_plan", rationale, "Author-certified metadata and target-journal formatting remain outside local automation.")

    for rel_path in [
        "figures/figure_1_multicar_overtake_results.pdf",
        "figures/figure_1_multicar_overtake_results.svg",
        "figures/figure_2_portfolio_selector_summary.pdf",
        "figures/figure_2_portfolio_selector_summary.svg",
        "figures/figure_3_cross_heldout_validation.pdf",
        "figures/figure_3_cross_heldout_validation.svg",
    ]:
        add_file(rows, release_by_path, root, "figures_lightweight", rel_path, "main_figure_lightweight", "required_or_journal_dependent", "figure_qc; size_budget", "PDF/SVG figure export suitable for review or production depending on journal preference.", "Figure evidence remains simulator-only.")

    for rel_path in [
        "figures/figure_1_source_data.csv",
        "figures/figure_2_source_data.csv",
        "figures/figure_3_source_data.csv",
        "figures/figure_3_source_data_dictionary.csv",
        "tables/seed_outcome_ledger.csv",
        "tables/cross_heldout_statistical_supplement_rows.csv",
    ]:
        add_file(rows, release_by_path, root, "source_data", rel_path, "source_data_upload", "required_source_data", "figure_source_data_audit; data_dictionary", "Machine-readable source data for figures, seed outcomes, and statistical reporting.", "Source data cover the saved simulator seed sets only.")

    for rel_path in [
        "materials/SUPPLEMENTARY_INDEX.md",
        "materials/MANUSCRIPT_SUPPLEMENT_ASSEMBLY_MAP.md",
        "materials/METHODS_REPRODUCIBILITY_CAPSULE.md",
        "materials/STATISTICAL_REPORTING_APPENDIX.md",
        "materials/CLAIM_EVIDENCE_MATRIX.md",
        "materials/THREATS_TO_VALIDITY_AUDIT.md",
        "materials/REVIEWER_REPLICATION_ROUTE.md",
        "materials/REPORTING_SUPPLEMENT_NAVIGATOR.md",
        "materials/ARCHIVE_SIZE_BUDGET_REPORT.md",
    ]:
        add_file(rows, release_by_path, root, "core_supplement", rel_path, "supplement_or_reviewer_support", "recommended_supplement", "supplement_index; navigator", "Core reviewer-facing supplement/navigation material for methods, statistics, claims, limitations, and upload routing.", "Supplement files coordinate existing evidence and do not add broader validation.")

    for rel_path in [
        "materials/DATA_CODE_AVAILABILITY.md",
        "materials/ARCHIVE_README.md",
        "materials/RELEASE_ARCHIVE_MANIFEST.csv",
        "materials/FAIR_ARCHIVE_METADATA.md",
        "tables/artifact_provenance.md",
        "materials/DATA_DICTIONARY.md",
    ]:
        add_file(rows, release_by_path, root, "archive_pointer", rel_path, "archive_pointer_or_supporting_file", "archive_dependent", "archive_readme; release_manifest", "Lightweight pointer/checksum/dictionary file for public archive deposition and reviewer navigation.", "External DOI/accession is pending until public deposition.")

    excluded_rows = []
    for rel_path in [
        "figures/figure_1_multicar_overtake_results.tiff",
        "figures/figure_2_portfolio_selector_summary.tiff",
        "figures/figure_3_cross_heldout_validation.tiff",
    ]:
        item = release_by_path.get(rel_path)
        excluded_rows.append(
            {
                "path": rel_path,
                "archive_role": "production_figure_or_full_archive",
                "size_bytes": item["size_bytes"] if item else "",
                "size_mb": size_mb(item["size_bytes"]) if item else "",
                "reason": "Keep available for production or full archive; route through journal-specific large-file figure upload if required.",
                "replacement_in_slim_package": rel_path.replace(".tiff", ".pdf") + "; " + rel_path.replace(".tiff", ".svg"),
                "status": "archive_or_large_file_upload",
            }
        )

    for row in size_budget["largest_files"]:
        path = row["path"]
        if path.endswith(".tiff"):
            continue
        if row["upload_partition"] in {"evaluation_archive", "archive_other", "tables_archive"} and row["size_bytes"] > MB:
            excluded_rows.append(
                {
                    "path": path,
                    "archive_role": "full_archive_detail",
                    "size_bytes": row["size_bytes"],
                    "size_mb": row["size_mb"],
                    "reason": "Detailed rollout, trace, sweep, or large diagnostic table retained in full archive rather than slim journal upload.",
                    "replacement_in_slim_package": "summary tables, source data, and reviewer navigation files",
                    "status": "archive_only",
                }
            )

    partition_rows = {}
    for row in rows:
        if not row["include_in_slim_package"]:
            continue
        entry = partition_rows.setdefault(row["section"], {"section": row["section"], "file_count": 0, "size_bytes": 0})
        entry["file_count"] += 1
        entry["size_bytes"] += row["size_bytes"] or 0
    partition_summary = []
    for item in sorted(partition_rows.values(), key=lambda row: row["section"]):
        partition_summary.append({**item, "size_mb": size_mb(item["size_bytes"])})

    slim_size = sum(row["size_bytes"] or 0 for row in rows if row["include_in_slim_package"])
    review_required_count = sum(1 for row in rows if row["status"] == "review_required")
    return {
        "root": str(root),
        "title": "Slim Submission Package Manifest",
        "purpose": (
            "Define a lightweight journal-facing upload set that points to the full archive while avoiding large "
            "production TIFFs, rollout traces, sweeps, and detailed diagnostics unless a journal or reviewer requests them."
        ),
        "summary": {
            "status": "pass" if review_required_count == 0 else "review_required",
            "slim_file_count": sum(1 for row in rows if row["include_in_slim_package"]),
            "slim_size_bytes": slim_size,
            "slim_size_mb": size_mb(slim_size),
            "full_release_file_count": release["summary"]["file_count"],
            "full_release_size_reference": "materials/RELEASE_ARCHIVE_MANIFEST.json",
            "excluded_or_archive_only_count": len(excluded_rows),
            "review_required_count": review_required_count,
            "publication_verification_status": verification["summary"]["status"],
            "publication_smoke_test_reference": "materials/PUBLICATION_SMOKE_TEST.json",
            "submission_dashboard_review_required": dashboard["summary"]["review_required_row_count"],
            "data_dictionary_complete": data_dictionary["summary"]["complete"],
            "artifact_provenance": f"{provenance['complete_count']}/{len(provenance['artifacts'])}",
            "large_tiff_count": sum(1 for row in excluded_rows if row["path"].endswith(".tiff")),
        },
        "rows": rows,
        "partition_summary": partition_summary,
        "excluded_rows": excluded_rows,
        "interpretation": (
            "This manifest is an operational planning aid. It does not replace the selected journal's upload rules "
            "and does not certify author-owned metadata, DOI/accession assignment, or final PDF/source conversion."
        ),
        "author_actions": [
            "Choose the target journal and decide whether PDF/SVG, TIFF, or both are required for figure upload.",
            "Convert manuscript sources to the official journal template and final PDF/source package.",
            "Deposit the full release package in a public archive and update DOI/URL/accession fields.",
            "Keep full archive checksums available for any file not included in the slim journal upload set.",
        ],
    }


def write_csv(rows, path, fields):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def write_markdown(report, path):
    lines = [
        "# Slim Submission Package Manifest",
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
            "## Partition Summary",
            "",
            "| section | files | size MB |",
            "|---|---:|---:|",
        ]
    )
    for row in report["partition_summary"]:
        lines.append(f"| {row['section']} | {row['file_count']} | {row['size_mb']} |")
    lines.extend(
        [
            "",
            "## Included Files",
            "",
            "| section | path | role | priority | size MB | status |",
            "|---|---|---|---|---:|---|",
        ]
    )
    for row in report["rows"]:
        lines.append(
            f"| {row['section']} | `{row['path']}` | {row['upload_role']} | {row['priority']} | "
            f"{row['size_mb']} | {row['status']} |"
        )
    lines.extend(
        [
            "",
            "## Archive-Only Or Large-File Rows",
            "",
            "| path | archive role | size MB | reason | slim replacement |",
            "|---|---|---:|---|---|",
        ]
    )
    for row in report["excluded_rows"]:
        lines.append(
            f"| `{row['path']}` | {row['archive_role']} | {row['size_mb']} | "
            f"{row['reason']} | {row['replacement_in_slim_package']} |"
        )
    lines.extend(["", "## Author Actions", ""])
    for item in report["author_actions"]:
        lines.append(f"- {item}")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export slim submission package manifest.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    report = build_report(root)
    out_json = materials / "SLIM_SUBMISSION_PACKAGE_MANIFEST.json"
    out_md = materials / "SLIM_SUBMISSION_PACKAGE_MANIFEST.md"
    included_csv = materials / "SLIM_SUBMISSION_PACKAGE_FILES.csv"
    excluded_csv = materials / "SLIM_SUBMISSION_PACKAGE_ARCHIVE_ONLY.csv"
    partition_csv = materials / "SLIM_SUBMISSION_PACKAGE_PARTITIONS.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(
        report["rows"],
        included_csv,
        ["section", "path", "upload_role", "priority", "include_in_slim_package", "size_bytes", "size_mb", "sha256", "source", "rationale", "boundary", "status"],
    )
    write_csv(
        report["excluded_rows"],
        excluded_csv,
        ["path", "archive_role", "size_bytes", "size_mb", "reason", "replacement_in_slim_package", "status"],
    )
    write_csv(report["partition_summary"], partition_csv, ["section", "file_count", "size_bytes", "size_mb"])
    print(
        json.dumps(
            {
                "json": str(out_json),
                "markdown": str(out_md),
                "included_csv": str(included_csv),
                "excluded_csv": str(excluded_csv),
                "partition_csv": str(partition_csv),
                "summary": report["summary"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
