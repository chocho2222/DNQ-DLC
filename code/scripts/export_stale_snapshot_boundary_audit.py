#!/usr/bin/env python
import argparse
import csv
import json
import re
from pathlib import Path


SCAN_SUFFIXES = {".md", ".json", ".csv"}
SCAN_DIRS = ("materials", "tables")

SCAN_EXCLUDED_PREFIXES = {
    "ARCHIVE_MANIFEST_EXCLUSION_AUDIT",
    "CROSS_MATERIAL_CONSISTENCY_AUDIT",
    "CROSS_REPORT_FRESHNESS_AUDIT",
    "DATA_DICTIONARY",
    "FINAL_CHECKSUM_FREEZE_RECORD",
    "MACHINE_READABLE_TABLE_INTEGRITY_AUDIT",
    "NARRATIVE_NUMERIC_CONSISTENCY_AUDIT",
    "PUBLICATION_PACKAGE_VERIFICATION",
    "PUBLICATION_SMOKE_TEST",
    "RELEASE_ARCHIVE_MANIFEST",
    "SCRIPT_SNAPSHOT_INTEGRITY_AUDIT",
    "STALE_SNAPSHOT_BOUNDARY_AUDIT",
}

CORE_ENTRY_PATHS = {
    "materials/ARCHIVE_README.md",
    "materials/ARCHIVE_README.json",
    "materials/ARCHIVE_README.csv",
    "materials/CROSS_MATERIAL_CONSISTENCY_AUDIT.md",
    "materials/CROSS_MATERIAL_CONSISTENCY_AUDIT.json",
    "materials/CROSS_MATERIAL_CONSISTENCY_AUDIT.csv",
    "materials/CROSS_REPORT_FRESHNESS_AUDIT.md",
    "materials/CROSS_REPORT_FRESHNESS_AUDIT.json",
    "materials/CROSS_REPORT_FRESHNESS_AUDIT.csv",
    "materials/DATA_DICTIONARY.md",
    "materials/DATA_DICTIONARY.json",
    "materials/DATA_DICTIONARY.csv",
    "materials/EDITORIAL_SUBMISSION_CHECKLIST.md",
    "materials/EDITORIAL_SUBMISSION_CHECKLIST.json",
    "materials/EDITORIAL_SUBMISSION_CHECKLIST.csv",
    "materials/MACHINE_READABLE_TABLE_INTEGRITY_AUDIT.md",
    "materials/MACHINE_READABLE_TABLE_INTEGRITY_AUDIT.json",
    "materials/MACHINE_READABLE_TABLE_INTEGRITY_AUDIT.csv",
    "materials/PUBLICATION_PACKAGE_SUMMARY.md",
    "materials/PUBLICATION_PACKAGE_SUMMARY.json",
    "materials/PUBLICATION_PACKAGE_SUMMARY.csv",
    "materials/PUBLICATION_PACKAGE_VERIFICATION.md",
    "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
    "materials/PUBLICATION_PACKAGE_VERIFICATION.csv",
    "materials/PUBLICATION_SMOKE_TEST.md",
    "materials/PUBLICATION_SMOKE_TEST.json",
    "materials/PUBLICATION_SMOKE_TEST.csv",
    "materials/RELEASE_ARCHIVE_MANIFEST.md",
    "materials/RELEASE_ARCHIVE_MANIFEST.json",
    "materials/RELEASE_ARCHIVE_MANIFEST.csv",
    "materials/REPORTING_SUPPLEMENT_NAVIGATOR.md",
    "materials/REPORTING_SUPPLEMENT_NAVIGATOR.json",
    "materials/REPORTING_SUPPLEMENT_NAVIGATOR.csv",
    "materials/SCRIPT_SNAPSHOT_INTEGRITY_AUDIT.md",
    "materials/SCRIPT_SNAPSHOT_INTEGRITY_AUDIT.json",
    "materials/SCRIPT_SNAPSHOT_INTEGRITY_AUDIT.csv",
    "materials/SCRIPT_SNAPSHOT_EXTRA_FILES.csv",
    "materials/SUBMISSION_READINESS_DASHBOARD.md",
    "materials/SUBMISSION_READINESS_DASHBOARD.json",
    "materials/SUBMISSION_READINESS_DASHBOARD.csv",
    "tables/artifact_provenance.md",
    "tables/artifact_provenance.json",
}

SELF_REFERENTIAL_PREFIXES = (
    "ARCHIVE_MANIFEST_EXCLUSION_AUDIT",
    "ARCHIVE_README",
    "ARCHIVE_SIZE_BUDGET",
    "ARCHIVE_UPLOAD_READINESS",
    "CITATION",
    "CROSS_MATERIAL_CONSISTENCY_AUDIT",
    "CROSS_REPORT_FRESHNESS_AUDIT",
    "FAIR_ARCHIVE_METADATA",
    "FINAL_CHECKSUM_FREEZE",
    "FINAL_SUBMISSION_FILE_BUNDLE",
    "MACHINE_READABLE_TABLE_INTEGRITY_AUDIT",
    "NARRATIVE_NUMERIC_CONSISTENCY_AUDIT",
    "PUBLICATION_PACKAGE_VERIFICATION",
    "PUBLICATION_SMOKE_TEST",
    "RELEASE_ARCHIVE_MANIFEST",
    "REPORTING_SUPPLEMENT_NAVIGATOR",
    "SCRIPT_SNAPSHOT",
    "SLIM_SUBMISSION_PACKAGE",
    "STALE_SNAPSHOT_BOUNDARY_AUDIT",
    "SUBMISSION_READINESS_DASHBOARD",
    "SUBMISSION_UPLOAD_SELECTION_PLAN",
    "TOP_JOURNAL_REPORTING_SUMMARY",
)

AUTHOR_OR_SUBMISSION_PREFIXES = (
    "AUTHOR_",
    "COVER_LETTER",
    "EDITORIAL_",
    "ETHICS_",
    "REFERENCE_",
    "REMAINING_AUTHOR",
    "SUBMISSION_",
    "TARGET_JOURNAL",
)

HISTORICAL_PREFIXES = (
    "BASELINE_",
    "COMPUTE_",
    "DAGGER_",
    "EFFECT_",
    "ENDPOINT_",
    "EXTERNAL_VALIDITY",
    "FIGURE_",
    "HELDOUT",
    "NEGATIVE_",
    "SAMPLE_SIZE",
    "SELECTOR_",
    "STATISTICAL_",
    "VISUAL_",
)


def load_json(path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def line_no(text, index):
    return text.count("\n", 0, index) + 1


def line_text(text, index):
    start = text.rfind("\n", 0, index) + 1
    end = text.find("\n", index)
    if end == -1:
        end = len(text)
    return text[start:end].strip()


def is_non_artifact_ratio_context(context):
    lowered = context.lower()
    return "script snapshot" in lowered or "script snapshots" in lowered


def classify(rel_path):
    name = Path(rel_path).name
    stem = Path(rel_path).stem
    if rel_path in CORE_ENTRY_PATHS:
        return "blocking_core_entry"
    if rel_path.startswith("materials/scripts/"):
        return "ignored_script_snapshot"
    if any(stem.startswith(prefix) or name.startswith(prefix) for prefix in SELF_REFERENTIAL_PREFIXES):
        return "self_referential_or_excluded_report"
    if any(stem.startswith(prefix) or name.startswith(prefix) for prefix in AUTHOR_OR_SUBMISSION_PREFIXES):
        return "author_or_submission_draft"
    if any(stem.startswith(prefix) or name.startswith(prefix) for prefix in HISTORICAL_PREFIXES):
        return "non_blocking_historical_snapshot"
    if rel_path.startswith("tables/") and ("heldout" in rel_path or "selector" in rel_path or "statistical" in rel_path):
        return "non_blocking_historical_snapshot"
    return "non_blocking_historical_snapshot"


def should_scan(rel_path):
    if rel_path.startswith("materials/scripts/"):
        return False
    name = Path(rel_path).name
    stem = Path(rel_path).stem
    if any(stem.startswith(prefix) or name.startswith(prefix) for prefix in SCAN_EXCLUDED_PREFIXES):
        return False
    return True


def find_stale_snapshots(root, canonical):
    artifact_expected = f"{canonical['artifact_complete_count']}/{canonical['artifact_total_count']}"
    release_expected_count = str(canonical["release_file_count"])
    release_expected_size = str(canonical["release_size_bytes"])
    artifact_ratio = re.compile(r"\b(1[0-9]{2})/\1\b")
    file_count_phrase = re.compile(r"\b(\d{3,5})\s+files?\b", re.IGNORECASE)
    size_phrase = re.compile(r"\b(\d{6,12})\s+bytes?\b", re.IGNORECASE)

    rows = []
    for dirname in SCAN_DIRS:
        folder = root / dirname
        if not folder.exists():
            continue
        for path in sorted(folder.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in SCAN_SUFFIXES:
                continue
            rel = path.relative_to(root).as_posix()
            if not should_scan(rel):
                continue
            text = path.read_text(encoding="utf-8", errors="replace")

            for match in artifact_ratio.finditer(text):
                value = match.group(0)
                if value == artifact_expected:
                    continue
                context = line_text(text, match.start())
                if is_non_artifact_ratio_context(context):
                    continue
                category = classify(rel)
                rows.append(
                    {
                        "path": rel,
                        "line": line_no(text, match.start()),
                        "snapshot_type": "artifact_provenance_ratio",
                        "observed": value,
                        "expected": artifact_expected,
                        "category": category,
                        "blocking": category == "blocking_core_entry",
                        "context": context,
                    }
                )

            for match in file_count_phrase.finditer(text):
                value = match.group(1)
                if value == release_expected_count:
                    continue
                context = line_text(text, match.start())
                if not any(token in context.lower() for token in ("release", "manifest", "archive", "file count", "files")):
                    continue
                category = classify(rel)
                rows.append(
                    {
                        "path": rel,
                        "line": line_no(text, match.start()),
                        "snapshot_type": "release_file_count",
                        "observed": value,
                        "expected": release_expected_count,
                        "category": category,
                        "blocking": category == "blocking_core_entry",
                        "context": context,
                    }
                )

            for match in size_phrase.finditer(text):
                value = match.group(1)
                if value == release_expected_size:
                    continue
                context = line_text(text, match.start())
                if not any(token in context.lower() for token in ("release", "manifest", "archive", "size", "bytes")):
                    continue
                category = classify(rel)
                rows.append(
                    {
                        "path": rel,
                        "line": line_no(text, match.start()),
                        "snapshot_type": "release_size_bytes",
                        "observed": value,
                        "expected": release_expected_size,
                        "category": category,
                        "blocking": category == "blocking_core_entry",
                        "context": context,
                    }
                )
    return rows


def build_report(root):
    provenance = load_json(root / "tables" / "artifact_provenance.json")
    release = load_json(root / "materials" / "RELEASE_ARCHIVE_MANIFEST.json")
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    smoke = load_json(root / "materials" / "PUBLICATION_SMOKE_TEST.json")
    dictionary = load_json(root / "materials" / "DATA_DICTIONARY.json")
    freshness = load_json(root / "materials" / "CROSS_REPORT_FRESHNESS_AUDIT.json")

    canonical = {
        "artifact_complete_count": provenance["complete_count"],
        "artifact_total_count": len(provenance["artifacts"]),
        "release_file_count": release["summary"]["file_count"],
        "release_size_bytes": release["summary"]["size_bytes"],
        "publication_verification_status": verification["summary"]["status"],
        "publication_smoke_test_status": smoke["summary"]["status"],
        "data_dictionary_complete": dictionary["summary"]["complete"],
        "data_dictionary_table_count": dictionary["summary"]["table_count"],
        "cross_report_freshness_status": freshness["summary"]["status"],
    }
    rows = find_stale_snapshots(root, canonical)
    blocking = [row for row in rows if row["blocking"]]
    category_counts = {}
    type_counts = {}
    for row in rows:
        category_counts[row["category"]] = category_counts.get(row["category"], 0) + 1
        type_counts[row["snapshot_type"]] = type_counts.get(row["snapshot_type"], 0) + 1

    return {
        "root": str(root),
        "title": "Stale Snapshot Boundary Audit",
        "purpose": (
            "Classify stale numeric status snapshots so that current reviewer entry points are separated from "
            "historical diagnostic reports and author/submission drafts."
        ),
        "canonical_values": canonical,
        "rows": rows,
        "summary": {
            "status": "pass" if not blocking else "review_required",
            "total_stale_snapshot_count": len(rows),
            "blocking_core_count": len(blocking),
            "non_blocking_count": len(rows) - len(blocking),
            "category_counts": category_counts,
            "snapshot_type_counts": type_counts,
            "artifact_provenance": f"{canonical['artifact_complete_count']}/{canonical['artifact_total_count']}",
            "release_file_count": canonical["release_file_count"],
            "release_size_bytes": canonical["release_size_bytes"],
        },
        "interpretation": (
            "Rows in historical or author/submission drafts are retained as non-blocking provenance of earlier "
            "diagnostic states. Core entry-point materials must remain current and are separately guarded by the "
            "cross-material, cross-report freshness, verification, and smoke-test gates."
        ),
    }


def write_csv(report, path):
    fields = ["path", "line", "snapshot_type", "observed", "expected", "category", "blocking", "context"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in report["rows"]:
            writer.writerow({field: row[field] for field in fields})


def write_markdown(report, path):
    lines = [
        "# Stale Snapshot Boundary Audit",
        "",
        report["purpose"],
        "",
        report["interpretation"],
        "",
        "## Canonical Values",
        "",
    ]
    for key, value in report["canonical_values"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Summary", ""])
    for key, value in report["summary"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(
        [
            "",
            "## Findings",
            "",
            "| path | line | type | observed | expected | category | blocking | context |",
            "|---|---:|---|---|---|---|---:|---|",
        ]
    )
    for row in report["rows"]:
        context = str(row["context"]).replace("|", "\\|")
        lines.append(
            f"| `{row['path']}` | {row['line']} | {row['snapshot_type']} | `{row['observed']}` | "
            f"`{row['expected']}` | {row['category']} | {row['blocking']} | {context} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export stale snapshot boundary audit.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_report(root)
    out_json = materials / "STALE_SNAPSHOT_BOUNDARY_AUDIT.json"
    out_md = materials / "STALE_SNAPSHOT_BOUNDARY_AUDIT.md"
    out_csv = materials / "STALE_SNAPSHOT_BOUNDARY_AUDIT.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv), "summary": report["summary"]}, indent=2))


if __name__ == "__main__":
    main()
