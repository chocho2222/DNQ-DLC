#!/usr/bin/env python
import argparse
import csv
import hashlib
import json
from pathlib import Path


def sha256_file(path, chunk_size=1024 * 1024):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def categorize(rel_path):
    first = rel_path.parts[0] if rel_path.parts else ""
    if first in {"tables", "figures", "materials", "models", "evaluations", "baselines", "logs", "configs", "ablations", "sweeps"}:
        return first
    if rel_path.name == "manifest.json":
        return "manifest"
    return "other"


def build_manifest(root):
    files = []
    self_outputs = {
        "materials/RELEASE_ARCHIVE_MANIFEST.json",
        "materials/RELEASE_ARCHIVE_MANIFEST.md",
        "materials/RELEASE_ARCHIVE_MANIFEST.csv",
        "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
        "materials/PUBLICATION_PACKAGE_VERIFICATION.md",
        "materials/PUBLICATION_PACKAGE_VERIFICATION.csv",
        "materials/PUBLICATION_SMOKE_TEST.json",
        "materials/PUBLICATION_SMOKE_TEST.md",
        "materials/PUBLICATION_SMOKE_TEST.csv",
        "materials/CROSS_MATERIAL_CONSISTENCY_AUDIT.json",
        "materials/CROSS_MATERIAL_CONSISTENCY_AUDIT.md",
        "materials/CROSS_MATERIAL_CONSISTENCY_AUDIT.csv",
        "materials/CROSS_REPORT_FRESHNESS_AUDIT.json",
        "materials/CROSS_REPORT_FRESHNESS_AUDIT.md",
        "materials/CROSS_REPORT_FRESHNESS_AUDIT.csv",
        "materials/SUBMISSION_TEXT_FRESHNESS_AUDIT.json",
        "materials/SUBMISSION_TEXT_FRESHNESS_AUDIT.md",
        "materials/SUBMISSION_TEXT_FRESHNESS_AUDIT.csv",
        "materials/LOCAL_AUTHOR_READINESS_SEPARATION_AUDIT.json",
        "materials/LOCAL_AUTHOR_READINESS_SEPARATION_AUDIT.md",
        "materials/LOCAL_AUTHOR_READINESS_SEPARATION_AUDIT.csv",
        "materials/STALE_SNAPSHOT_BOUNDARY_AUDIT.json",
        "materials/STALE_SNAPSHOT_BOUNDARY_AUDIT.md",
        "materials/STALE_SNAPSHOT_BOUNDARY_AUDIT.csv",
        "materials/NARRATIVE_NUMERIC_CONSISTENCY_AUDIT.json",
        "materials/NARRATIVE_NUMERIC_CONSISTENCY_AUDIT.md",
        "materials/NARRATIVE_NUMERIC_CONSISTENCY_AUDIT.csv",
        "materials/SCRIPT_SNAPSHOT_INTEGRITY_AUDIT.json",
        "materials/SCRIPT_SNAPSHOT_INTEGRITY_AUDIT.md",
        "materials/SCRIPT_SNAPSHOT_INTEGRITY_AUDIT.csv",
        "materials/SCRIPT_SNAPSHOT_EXTRA_FILES.csv",
        "materials/MACHINE_READABLE_TABLE_INTEGRITY_AUDIT.json",
        "materials/MACHINE_READABLE_TABLE_INTEGRITY_AUDIT.md",
        "materials/MACHINE_READABLE_TABLE_INTEGRITY_AUDIT.csv",
        "materials/RELEASE_PROVENANCE_COVERAGE_AUDIT.json",
        "materials/RELEASE_PROVENANCE_COVERAGE_AUDIT.md",
        "materials/RELEASE_PROVENANCE_COVERAGE_AUDIT.csv",
        "materials/FINAL_CHECKSUM_FREEZE_RECORD.json",
        "materials/FINAL_CHECKSUM_FREEZE_RECORD.md",
        "materials/FINAL_CHECKSUM_FREEZE_RECORD.csv",
        "materials/FINAL_CHECKSUM_FREEZE_FILE_SNAPSHOTS.csv",
        "materials/FAIR_ARCHIVE_METADATA.json",
        "materials/FAIR_ARCHIVE_METADATA.md",
        "materials/FAIR_ARCHIVE_METADATA.csv",
        "materials/ARCHIVE_MANIFEST_EXCLUSION_AUDIT.json",
        "materials/ARCHIVE_MANIFEST_EXCLUSION_AUDIT.md",
        "materials/ARCHIVE_MANIFEST_EXCLUSION_AUDIT.csv",
        "materials/EXTERNAL_ARCHIVE_PREFLIGHT.json",
        "materials/EXTERNAL_ARCHIVE_PREFLIGHT.md",
        "materials/EXTERNAL_ARCHIVE_PREFLIGHT_ROWS.csv",
        "materials/EXTERNAL_ARCHIVE_KEY_FILES.csv",
        "materials/ARCHIVE_README.json",
        "materials/ARCHIVE_README.md",
        "materials/ARCHIVE_README.csv",
        "materials/ARCHIVE_SIZE_BUDGET_REPORT.json",
        "materials/ARCHIVE_SIZE_BUDGET_REPORT.md",
        "materials/ARCHIVE_SIZE_BUDGET_CATEGORIES.csv",
        "materials/ARCHIVE_SIZE_BUDGET_UPLOAD_PARTITIONS.csv",
        "materials/ARCHIVE_SIZE_BUDGET_LARGEST_FILES.csv",
        "materials/ARCHIVE_SIZE_BUDGET_CHECKS.csv",
        "materials/SLIM_SUBMISSION_PACKAGE_MANIFEST.json",
        "materials/SLIM_SUBMISSION_PACKAGE_MANIFEST.md",
        "materials/SLIM_SUBMISSION_PACKAGE_FILES.csv",
        "materials/SLIM_SUBMISSION_PACKAGE_ARCHIVE_ONLY.csv",
        "materials/SLIM_SUBMISSION_PACKAGE_PARTITIONS.csv",
        "materials/AUTHOR_UPLOAD_DECISION_MEMO.json",
        "materials/AUTHOR_UPLOAD_DECISION_MEMO.md",
        "materials/AUTHOR_UPLOAD_DECISION_MEMO.csv",
        "materials/FINAL_AUTHOR_HANDOFF_CHECKLIST.json",
        "materials/FINAL_AUTHOR_HANDOFF_CHECKLIST.md",
        "materials/FINAL_AUTHOR_HANDOFF_CHECKLIST.csv",
        "materials/FINAL_SUBMISSION_FILE_BUNDLE.json",
        "materials/FINAL_SUBMISSION_FILE_BUNDLE.md",
        "materials/FINAL_SUBMISSION_FILE_BUNDLE.csv",
        "materials/CITATION_METADATA.json",
        "materials/CITATION_METADATA.md",
        "materials/CITATION_METADATA.csv",
        "materials/CITATION.cff",
        "materials/CITATION.bib",
        "materials/SUBMISSION_READINESS_DASHBOARD.json",
        "materials/SUBMISSION_READINESS_DASHBOARD.md",
        "materials/SUBMISSION_READINESS_DASHBOARD.csv",
        "materials/REPORTING_SUPPLEMENT_NAVIGATOR.json",
        "materials/REPORTING_SUPPLEMENT_NAVIGATOR.md",
        "materials/REPORTING_SUPPLEMENT_NAVIGATOR.csv",
        "materials/SUBMISSION_UPLOAD_SELECTION_PLAN.json",
        "materials/SUBMISSION_UPLOAD_SELECTION_PLAN.md",
        "materials/SUBMISSION_UPLOAD_SELECTION_PLAN.csv",
        "materials/ARCHIVE_UPLOAD_READINESS_MATRIX.json",
        "materials/ARCHIVE_UPLOAD_READINESS_MATRIX.md",
        "materials/ARCHIVE_UPLOAD_READINESS_MATRIX.csv",
        "materials/TOP_JOURNAL_REPORTING_SUMMARY.json",
        "materials/TOP_JOURNAL_REPORTING_SUMMARY.md",
        "materials/TOP_JOURNAL_REPORTING_SUMMARY.csv",
        "materials/SUBMISSION_PORTAL_PACKAGE_MAP.json",
        "materials/SUBMISSION_PORTAL_PACKAGE_MAP.md",
        "materials/SUBMISSION_PORTAL_PACKAGE_MAP.csv",
        "materials/EDITORIAL_SUBMISSION_CHECKLIST.json",
        "materials/EDITORIAL_SUBMISSION_CHECKLIST.md",
        "materials/EDITORIAL_SUBMISSION_CHECKLIST.csv",
        "materials/EDITORIAL_TRIAGE_AND_REVIEWER_CHECKLIST.json",
        "materials/EDITORIAL_TRIAGE_AND_REVIEWER_CHECKLIST.md",
        "materials/EDITORIAL_TRIAGE_AND_REVIEWER_CHECKLIST.csv",
        "materials/TARGET_JOURNAL_COMPLIANCE_MATRIX.json",
        "materials/TARGET_JOURNAL_COMPLIANCE_MATRIX.md",
        "materials/TARGET_JOURNAL_COMPLIANCE_MATRIX.csv",
        "materials/REVIEWER_RISK_RESPONSE_DOSSIER.json",
        "materials/REVIEWER_RISK_RESPONSE_DOSSIER.md",
        "materials/REVIEWER_RISK_RESPONSE_DOSSIER.csv",
        "materials/SOFTWARE_DEPENDENCY_LICENSE_AUDIT.json",
        "materials/SOFTWARE_DEPENDENCY_LICENSE_AUDIT.md",
        "materials/SOFTWARE_DEPENDENCY_LICENSE_AUDIT.csv",
        "materials/ARTIFACT_DEPENDENCY_MAP.json",
        "materials/ARTIFACT_DEPENDENCY_MAP.md",
        "materials/ARTIFACT_DEPENDENCY_MAP.csv",
    }
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if ".git" in rel.parts:
            continue
        rel_str = rel.as_posix()
        if rel_str in self_outputs:
            continue
        files.append(
            {
                "path": rel_str,
                "category": categorize(rel),
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )

    by_category = {}
    for row in files:
        entry = by_category.setdefault(row["category"], {"file_count": 0, "size_bytes": 0})
        entry["file_count"] += 1
        entry["size_bytes"] += row["size_bytes"]

    return {
        "root": str(root),
        "release_status": "local_manifest_only",
        "external_archive": {
            "doi": None,
            "url": None,
            "note": "No external DOI or repository accession has been assigned yet.",
        },
        "summary": {
            "file_count": len(files),
            "size_bytes": sum(row["size_bytes"] for row in files),
            "by_category": by_category,
        },
        "files": files,
        "recommended_archive_contents": [
            "manifest.json",
            "materials/",
            "materials/ENVIRONMENT_REPRODUCIBILITY_AUDIT.*",
            "materials/EXPERIMENT_REGISTRY.*",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.*",
            "materials/FAIR_ARCHIVE_METADATA.*",
            "materials/RESEARCH_RISK_AND_SAFETY.*",
            "materials/TOP_JOURNAL_REPORTING_SUMMARY.*",
            "materials/EDITORIAL_SUBMISSION_CHECKLIST.*",
            "materials/SIGNIFICANCE_BRIEFING.*",
            "materials/EDITORIAL_NARRATIVE_PACKAGE.*",
            "materials/COVER_LETTER_DRAFT_PACKAGE.*",
            "materials/COVER_LETTER_AUTHOR_CHECKLIST.csv",
            "materials/SUBMISSION_PORTAL_PACKAGE_MAP.*",
            "materials/SUBMISSION_PORTAL_AUTHOR_ACTIONS.csv",
            "materials/EDITORIAL_DECISION_BRIEF.*",
            "materials/ARTIFACT_DEPENDENCY_MAP.*",
            "materials/ARTIFACT_DEPENDENCY_FILE_EDGES.csv",
            "materials/DATA_DICTIONARY.*",
            "tables/",
            "tables/seed_outcome_ledger.*",
            "figures/",
            "evaluations/",
            "models/",
            "baselines/",
            "logs/",
            "configs/",
            "environment.yml from repository root",
            "scripts/ and source tree from repository root or package snapshots in materials/",
        ],
        "integrity_note": (
            "The SHA256 values are computed from the local package files, excluding RELEASE_ARCHIVE_MANIFEST "
            "outputs, PUBLICATION_PACKAGE_VERIFICATION outputs, PUBLICATION_SMOKE_TEST outputs, "
            "CROSS_MATERIAL_CONSISTENCY_AUDIT outputs, CROSS_REPORT_FRESHNESS_AUDIT outputs, "
            "STALE_SNAPSHOT_BOUNDARY_AUDIT outputs, "
            "RELEASE_PROVENANCE_COVERAGE_AUDIT outputs, "
            "FINAL_CHECKSUM_FREEZE_RECORD outputs, the three FAIR_ARCHIVE_METADATA outputs, the "
            "ARCHIVE_MANIFEST_EXCLUSION_AUDIT outputs, citation/readiness/reporting/upload-plan metadata, "
            "editor/reviewer navigation reports, author handoff reports, and archive/submission entry-point reports that summarize "
            "this manifest, to avoid "
            "self-referential checksum drift. "
            "Regenerate this manifest after any file change and before uploading a public archive."
        ),
    }


def write_csv(report, root):
    path = root / "materials" / "RELEASE_ARCHIVE_MANIFEST.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["path", "category", "size_bytes", "sha256"])
        writer.writeheader()
        for row in report["files"]:
            writer.writerow(row)
    return path


def write_markdown(report, path):
    summary = report["summary"]
    lines = [
        "# Release Archive Manifest",
        "",
        "This manifest is a local archive-readiness record for the experiment package. It provides file counts, sizes, categories, and SHA256 checksums for release preparation.",
        "",
        "## Archive Status",
        "",
        f"- Status: `{report['release_status']}`",
        f"- DOI: `{report['external_archive']['doi']}`",
        f"- URL: `{report['external_archive']['url']}`",
        f"- Note: {report['external_archive']['note']}",
        "",
        "## Summary",
        "",
        f"- File count: {summary['file_count']}",
        f"- Size bytes: {summary['size_bytes']}",
        "",
        "## Category Summary",
        "",
        "| category | file count | size bytes |",
        "|---|---:|---:|",
    ]
    for category, row in sorted(summary["by_category"].items()):
        lines.append(f"| {category} | {row['file_count']} | {row['size_bytes']} |")
    lines.extend(
        [
            "",
            "## Recommended Archive Contents",
            "",
        ]
    )
    lines.extend(f"- `{item}`" for item in report["recommended_archive_contents"])
    lines.extend(
        [
            "",
            "## Integrity Note",
            "",
            report["integrity_note"],
            "",
            "## File Checksums",
            "",
            "The complete checksum table is available in `materials/RELEASE_ARCHIVE_MANIFEST.csv` and `materials/RELEASE_ARCHIVE_MANIFEST.json`.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export release archive manifest with SHA256 checksums.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    report = build_manifest(root)
    out_json = root / "materials" / "RELEASE_ARCHIVE_MANIFEST.json"
    out_md = root / "materials" / "RELEASE_ARCHIVE_MANIFEST.md"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    out_csv = write_csv(report, root)
    print(
        json.dumps(
            {
                "json": str(out_json),
                "markdown": str(out_md),
                "csv": str(out_csv),
                "file_count": report["summary"]["file_count"],
                "size_bytes": report["summary"]["size_bytes"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
