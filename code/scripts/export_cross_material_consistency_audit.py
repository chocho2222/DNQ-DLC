#!/usr/bin/env python
import argparse
import csv
import json
import re
from pathlib import Path


EXCLUDED_SCAN_PARTS = {
    ("materials", "scripts"),
}

SCAN_FILES = {
    "materials/ARCHIVE_README.md",
    "materials/ARCHIVE_README.json",
    "materials/ARCHIVE_SIZE_BUDGET_REPORT.md",
    "materials/ARCHIVE_SIZE_BUDGET_REPORT.json",
    "materials/DATA_DICTIONARY.md",
    "materials/DATA_DICTIONARY.json",
    "materials/EDITORIAL_SUBMISSION_CHECKLIST.md",
    "materials/EDITORIAL_SUBMISSION_CHECKLIST.json",
    "materials/MACHINE_READABLE_TABLE_INTEGRITY_AUDIT.md",
    "materials/MACHINE_READABLE_TABLE_INTEGRITY_AUDIT.json",
    "materials/METHODS_REPRODUCIBILITY_CAPSULE.md",
    "materials/METHODS_REPRODUCIBILITY_CAPSULE.json",
    "materials/REPORTING_SUPPLEMENT_NAVIGATOR.md",
    "materials/REPORTING_SUPPLEMENT_NAVIGATOR.json",
    "materials/REVIEWER_EVIDENCE_TRACE_PACK.md",
    "materials/REVIEWER_EVIDENCE_TRACE_PACK.json",
    "materials/SCRIPT_SNAPSHOT_INTEGRITY_AUDIT.md",
    "materials/SCRIPT_SNAPSHOT_INTEGRITY_AUDIT.json",
    "materials/SLIM_SUBMISSION_PACKAGE_MANIFEST.md",
    "materials/SLIM_SUBMISSION_PACKAGE_MANIFEST.json",
    "materials/SUBMISSION_PORTAL_PACKAGE_MAP.md",
    "materials/SUBMISSION_PORTAL_PACKAGE_MAP.json",
    "materials/SUBMISSION_READINESS_DASHBOARD.md",
    "materials/SUBMISSION_READINESS_DASHBOARD.json",
    "materials/TOP_JOURNAL_REPORTING_SUMMARY.md",
    "materials/TOP_JOURNAL_REPORTING_SUMMARY.json",
    "materials/TRANSPARENT_REPORTING_CHECKLIST.md",
    "materials/TRANSPARENT_REPORTING_CHECKLIST.json",
    "tables/artifact_provenance.md",
    "tables/artifact_provenance.json",
}

SELF_OUTPUTS = {
    "materials/CROSS_MATERIAL_CONSISTENCY_AUDIT.md",
    "materials/CROSS_MATERIAL_CONSISTENCY_AUDIT.json",
    "materials/CROSS_MATERIAL_CONSISTENCY_AUDIT.csv",
}

SELF_REFERENTIAL_PREFIXES = {
    "ARCHIVE_MANIFEST_EXCLUSION_AUDIT",
    "CROSS_MATERIAL_CONSISTENCY_AUDIT",
    "FINAL_CHECKSUM_FREEZE_RECORD",
    "FINAL_CHECKSUM_FREEZE_FILE_SNAPSHOTS",
    "PUBLICATION_SMOKE_TEST",
    "RELEASE_ARCHIVE_MANIFEST",
}

SMOKE_STATUS_SELF_REFERENTIAL_FILES = {
    "materials/MANUSCRIPT_SUPPLEMENT_ASSEMBLY_MAP.md",
    "materials/METHODS_REPRODUCIBILITY_CAPSULE.md",
    "materials/REPORTING_SUPPLEMENT_NAVIGATOR.md",
    "materials/REVIEWER_REPLICATION_ROUTE.md",
    "materials/STATISTICAL_REPORTING_APPENDIX.md",
    "materials/SUPPLEMENTARY_TABLE_LEGENDS.md",
}

TEXT_SUFFIXES = {".md", ".csv"}
JSON_SUFFIXES = {".json"}


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def rel(path, root):
    return path.relative_to(root).as_posix()


def should_scan(path, root):
    rel_parts = path.relative_to(root).parts
    rel_path = Path(*rel_parts).as_posix()
    if rel_path not in SCAN_FILES:
        return False
    if rel_path in SELF_OUTPUTS:
        return False
    if len(rel_parts) >= 2 and rel_parts[0] == "materials":
        stem = Path(rel_parts[-1]).stem
        if any(stem.startswith(prefix) for prefix in SELF_REFERENTIAL_PREFIXES):
            return False
    if len(rel_parts) >= 2 and tuple(rel_parts[:2]) in EXCLUDED_SCAN_PARTS:
        return False
    return path.suffix in TEXT_SUFFIXES or path.suffix in JSON_SUFFIXES


def add_row(rows, check_id, category, status, expected, observed, file_path, location, note):
    rows.append(
        {
            "check_id": check_id,
            "category": category,
            "status": status,
            "expected": expected,
            "observed": observed,
            "file": file_path,
            "location": location,
            "note": note,
        }
    )


def walk_json(value, prefix=""):
    if isinstance(value, dict):
        for key, child in value.items():
            child_prefix = f"{prefix}.{key}" if prefix else str(key)
            yield from walk_json(child, child_prefix)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            child_prefix = f"{prefix}[{index}]"
            yield from walk_json(child, child_prefix)
    else:
        yield prefix, value


def scan_json_file(path, root, canonical):
    rows = []
    try:
        data = load_json(path)
    except Exception as exc:
        add_row(
            rows,
            "CM_json_parse",
            "parse",
            "fail",
            "valid JSON",
            repr(exc),
            rel(path, root),
            "file",
            "JSON file could not be parsed for cross-material consistency checks.",
        )
        return rows

    checks = {
        "release_file_count": canonical["release_file_count"],
        "artifact_provenance": canonical["artifact_provenance"],
        "data_dictionary_complete": True,
    }

    artifact_ratio_keys = {
        "artifact_provenance",
        "artifact_provenance_ratio",
        "artifact_provenance_status",
    }
    for pointer, value in walk_json(data):
        key = pointer.split(".")[-1]
        key = re.sub(r"\[\d+\]$", "", key)
        if key == "artifact_provenance" and not (isinstance(value, str) and re.fullmatch(r"\d+\s*/\s*\d+", value.strip())):
            continue
        if key == "artifact_provenance" and key not in artifact_ratio_keys:
            continue
        if key in checks and value != checks[key]:
            add_row(
                rows,
                f"CM_json_{key}",
                "json_value",
                "fail",
                str(checks[key]),
                str(value),
                rel(path, root),
                pointer,
                "Machine-readable status or release metadata drifted from the authoritative package source.",
            )
    return rows


def scan_text_file(path, root, canonical):
    rows = []
    rel_path = rel(path, root)
    artifact_pattern = re.compile(r"(\d+)\s*/\s*(\d+)")
    release_pattern = re.compile(r"(\d+)\s+files?,\s+(\d+)\s+bytes", re.IGNORECASE)
    canonical_artifact = canonical["artifact_provenance"]
    canonical_files = canonical["release_file_count"]
    canonical_bytes = canonical["release_size_bytes"]

    for line_number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
        lower = line.lower()
        artifact_context = "artifact provenance" in lower or "artifact_provenance" in lower or "artifacts complete" in lower
        if artifact_context:
            match = (
                re.search(r"artifact[_ -]provenance[^0-9]{0,40}(\d+)\s*/\s*(\d+)", line, re.IGNORECASE)
                or re.search(r"(\d+)\s*/\s*(\d+)\s+artifacts\s+complete", line, re.IGNORECASE)
            )
            if match:
                observed = f"{match.group(1)}/{match.group(2)}"
                if observed != canonical_artifact:
                    add_row(
                        rows,
                        "CM_text_artifact_provenance",
                        "text_status",
                        "fail",
                        canonical_artifact,
                        observed,
                        rel(path, root),
                        f"line {line_number}",
                        "Reviewer-facing artifact provenance ratio should match tables/artifact_provenance.json.",
                    )
        if "release manifest" in lower and "bytes" in lower:
            for match in release_pattern.finditer(line):
                files = int(match.group(1))
                size = int(match.group(2))
                if files != canonical_files:
                    add_row(
                        rows,
                        "CM_text_release_manifest_file_count",
                        "text_release_metadata",
                        "fail",
                        f"{canonical_files} files",
                        f"{files} files, {size} bytes",
                        rel(path, root),
                        f"line {line_number}",
                        "Reviewer-facing release-manifest file count should match RELEASE_ARCHIVE_MANIFEST.json; byte-level integrity is checked by FINAL_CHECKSUM_FREEZE_RECORD.",
                    )
        if canonical.get("publication_smoke_test_status") == "pass" and "publication_smoke_test_status" in lower and "fail" in lower:
            if rel_path in SMOKE_STATUS_SELF_REFERENTIAL_FILES:
                continue
            add_row(
                rows,
                "CM_text_publication_smoke_status",
                "text_status",
                "fail",
                "publication_smoke_test_status pass",
                line.strip(),
                rel(path, root),
                f"line {line_number}",
                "Reviewer-facing smoke-test status should not retain an old fail snapshot.",
            )
        if (
            canonical.get("publication_smoke_test_status") == "pass"
            and "publication_smoke_test_failed_checks" in lower
            and re.search(r":\s*[1-9]\d*", line)
        ):
            if rel_path in SMOKE_STATUS_SELF_REFERENTIAL_FILES:
                continue
            add_row(
                rows,
                "CM_text_publication_smoke_failed_checks",
                "text_status",
                "fail",
                "publication_smoke_test_failed_checks 0",
                line.strip(),
                rel(path, root),
                f"line {line_number}",
                "Reviewer-facing smoke-test failed-check count should be zero.",
            )
    return rows


def build_report(root):
    release = load_json(root / "materials" / "RELEASE_ARCHIVE_MANIFEST.json")
    provenance = load_json(root / "tables" / "artifact_provenance.json")
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    smoke = load_json(root / "materials" / "PUBLICATION_SMOKE_TEST.json")
    dictionary = load_json(root / "materials" / "DATA_DICTIONARY.json")

    artifact_total = len(provenance["artifacts"])
    artifact_complete = provenance["complete_count"]
    canonical = {
        "release_file_count": release["summary"]["file_count"],
        "release_size_bytes": release["summary"]["size_bytes"],
        "artifact_provenance": f"{artifact_complete}/{artifact_total}",
        "publication_smoke_test_status": smoke["summary"]["status"],
    }

    rows = []
    add_row(
        rows,
        "CM_authoritative_release_manifest",
        "authoritative_source",
        "pass",
        "release manifest loaded",
        f"{canonical['release_file_count']} files, {canonical['release_size_bytes']} bytes",
        "materials/RELEASE_ARCHIVE_MANIFEST.json",
        "summary",
        "Authoritative release count and size for this audit.",
    )
    add_row(
        rows,
        "CM_authoritative_artifact_provenance",
        "authoritative_source",
        "pass",
        "artifact provenance loaded",
        canonical["artifact_provenance"],
        "tables/artifact_provenance.json",
        "complete_count/artifact_count",
        "Authoritative artifact provenance ratio for this audit.",
    )
    add_row(
        rows,
        "CM_authoritative_package_gates",
        "authoritative_source",
        "pass",
        "package gate snapshots loaded",
        f"verification={verification['summary']['status']}; smoke={smoke['summary']['status']}",
        "materials/PUBLICATION_PACKAGE_VERIFICATION.json; materials/PUBLICATION_SMOKE_TEST.json",
        "summary.status",
        "Package gate statuses are reported as context only; enforcing them here would create a circular dependency with publication verification and smoke tests.",
    )
    add_row(
        rows,
        "CM_authoritative_data_dictionary",
        "authoritative_source",
        "pass" if dictionary["summary"]["complete"] else "fail",
        "data dictionary complete",
        str(dictionary["summary"]["complete"]),
        "materials/DATA_DICTIONARY.json",
        "summary.complete",
        "Authoritative data-dictionary completeness status for this audit.",
    )

    for path in sorted(root.rglob("*")):
        if not path.is_file() or not should_scan(path, root):
            continue
        if path.suffix in JSON_SUFFIXES:
            rows.extend(scan_json_file(path, root, canonical))
        else:
            rows.extend(scan_text_file(path, root, canonical))

    failed = [row for row in rows if row["status"] != "pass"]
    scanned_files = sum(1 for path in root.rglob("*") if path.is_file() and should_scan(path, root))
    return {
        "root": str(root),
        "title": "Cross-material consistency audit",
        "purpose": (
            "Check reviewer-facing materials and tables for stale package-wide status snapshots, "
            "including artifact provenance counts, release-manifest file/byte counts, smoke-test status, "
            "and data-dictionary completeness. Publication-verification and statistical-consistency snapshots "
            "are reported by their dedicated gates to avoid circular status propagation."
        ),
        "summary": {
            "status": "pass" if not failed else "fail",
            "row_count": len(rows),
            "failed_row_count": len(failed),
            "scanned_file_count": scanned_files,
            "release_file_count": canonical["release_file_count"],
            "release_size_bytes": canonical["release_size_bytes"],
            "artifact_provenance": canonical["artifact_provenance"],
            "publication_verification_status": verification["summary"]["status"],
            "publication_smoke_test_status": smoke["summary"]["status"],
            "data_dictionary_complete": dictionary["summary"]["complete"],
        },
        "rows": rows,
        "interpretation": (
            "This is a static consistency audit over saved reviewer-facing files. It does not rerun simulation "
            "rollouts or recompute statistical endpoints; it catches stale cross-material status and manifest "
            "metadata after package-generation order changes."
        ),
    }


FIELDS = ["check_id", "category", "status", "expected", "observed", "file", "location", "note"]


def write_csv(report, path):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for row in report["rows"]:
            writer.writerow({key: row[key] for key in FIELDS})


def write_markdown(report, path):
    lines = [
        "# Cross-material consistency audit",
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
            "## Rows",
            "",
            "| check_id | category | status | expected | observed | file | location | note |",
            "|---|---|---|---|---|---|---|---|",
        ]
    )
    for row in report["rows"]:
        lines.append(
            "| {check_id} | {category} | {status} | {expected} | {observed} | `{file}` | {location} | {note} |".format(
                **{key: str(value).replace("|", "\\|") for key, value in row.items()}
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_report(root)
    out_json = materials / "CROSS_MATERIAL_CONSISTENCY_AUDIT.json"
    out_md = materials / "CROSS_MATERIAL_CONSISTENCY_AUDIT.md"
    out_csv = materials / "CROSS_MATERIAL_CONSISTENCY_AUDIT.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    print(
        json.dumps(
            {
                "json": str(out_json),
                "markdown": str(out_md),
                "csv": str(out_csv),
                "summary": report["summary"],
            },
            indent=2,
        )
    )
    if report["summary"]["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
