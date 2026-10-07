#!/usr/bin/env python
import argparse
import csv
import json
import re
from pathlib import Path


SELF_OUTPUTS = {
    "materials/CROSS_REPORT_FRESHNESS_AUDIT.md",
    "materials/CROSS_REPORT_FRESHNESS_AUDIT.json",
    "materials/CROSS_REPORT_FRESHNESS_AUDIT.csv",
}

SCAN_FILES = {
    "materials/ARCHIVE_README.md",
    "materials/ARCHIVE_README.json",
    "materials/ARCHIVE_SIZE_BUDGET_REPORT.md",
    "materials/ARCHIVE_SIZE_BUDGET_REPORT.json",
    "materials/ARCHIVE_UPLOAD_READINESS_MATRIX.md",
    "materials/ARCHIVE_UPLOAD_READINESS_MATRIX.json",
    "materials/AUTHOR_ACTION_FREEZE_PLAN.md",
    "materials/AUTHOR_ACTION_FREEZE_PLAN.json",
    "materials/AUTHOR_OWNED_SUBMISSION_INTEGRITY_AUDIT.md",
    "materials/AUTHOR_OWNED_SUBMISSION_INTEGRITY_AUDIT.json",
    "materials/CITATION_METADATA.md",
    "materials/CITATION_METADATA.json",
    "materials/CLAIM_EVIDENCE_MATRIX.md",
    "materials/CLAIM_EVIDENCE_MATRIX.json",
    "materials/COVER_LETTER_DRAFT_PACKAGE.md",
    "materials/COVER_LETTER_DRAFT_PACKAGE.json",
    "materials/DATA_CODE_AVAILABILITY.md",
    "materials/DATA_CODE_AVAILABILITY.json",
    "materials/DATA_DICTIONARY.md",
    "materials/DATA_DICTIONARY.json",
    "materials/EDITORIAL_SUBMISSION_CHECKLIST.md",
    "materials/EDITORIAL_SUBMISSION_CHECKLIST.json",
    "materials/EDITORIAL_DECISION_BRIEF.md",
    "materials/EDITORIAL_DECISION_BRIEF.json",
    "materials/EDITORIAL_NARRATIVE_PACKAGE.md",
    "materials/EDITORIAL_NARRATIVE_PACKAGE.json",
    "materials/EDITORIAL_TRIAGE_AND_REVIEWER_CHECKLIST.md",
    "materials/EDITORIAL_TRIAGE_AND_REVIEWER_CHECKLIST.json",
    "materials/ETHICS_DISCLOSURE_READINESS_PACK.md",
    "materials/ETHICS_DISCLOSURE_READINESS_PACK.json",
    "materials/EXTERNAL_ARCHIVE_PREFLIGHT.md",
    "materials/EXTERNAL_ARCHIVE_PREFLIGHT.json",
    "materials/FAIR_ARCHIVE_METADATA.md",
    "materials/FAIR_ARCHIVE_METADATA.json",
    "materials/FINAL_SUBMISSION_FILE_BUNDLE.md",
    "materials/FINAL_SUBMISSION_FILE_BUNDLE.json",
    "materials/FIGURE_SOURCE_DATA_AUDIT.md",
    "materials/FIGURE_SOURCE_DATA_AUDIT.json",
    "materials/FIGURE_TECHNICAL_QC.md",
    "materials/FIGURE_TECHNICAL_QC.json",
    "materials/LOCAL_AUTHOR_READINESS_SEPARATION_AUDIT.md",
    "materials/LOCAL_AUTHOR_READINESS_SEPARATION_AUDIT.json",
    "materials/MANUSCRIPT_SUPPLEMENT_ASSEMBLY_MAP.md",
    "materials/MANUSCRIPT_SUPPLEMENT_ASSEMBLY_MAP.json",
    "materials/MACHINE_READABLE_TABLE_INTEGRITY_AUDIT.md",
    "materials/MACHINE_READABLE_TABLE_INTEGRITY_AUDIT.json",
    "materials/METHODS_REPRODUCIBILITY_CAPSULE.md",
    "materials/METHODS_REPRODUCIBILITY_CAPSULE.json",
    "materials/REPORTING_SUPPLEMENT_NAVIGATOR.md",
    "materials/REPORTING_SUPPLEMENT_NAVIGATOR.json",
    "materials/REVIEWER_EVIDENCE_TRACE_PACK.md",
    "materials/REVIEWER_EVIDENCE_TRACE_PACK.json",
    "materials/REVIEWER_REPLICATION_ROUTE.md",
    "materials/REVIEWER_REPLICATION_ROUTE.json",
    "materials/REVIEWER_RISK_RESPONSE_DOSSIER.md",
    "materials/REVIEWER_RISK_RESPONSE_DOSSIER.json",
    "materials/REMAINING_AUTHOR_BLOCKERS_MATRIX.md",
    "materials/REMAINING_AUTHOR_BLOCKERS_MATRIX.json",
    "materials/SIGNIFICANCE_BRIEFING.md",
    "materials/SIGNIFICANCE_BRIEFING.json",
    "materials/SCRIPT_SNAPSHOT_INTEGRITY_AUDIT.md",
    "materials/SCRIPT_SNAPSHOT_INTEGRITY_AUDIT.json",
    "materials/SLIM_SUBMISSION_PACKAGE_MANIFEST.md",
    "materials/SLIM_SUBMISSION_PACKAGE_MANIFEST.json",
    "materials/STATISTICAL_ANALYSIS_PLAN_AUDIT.md",
    "materials/STATISTICAL_ANALYSIS_PLAN_AUDIT.json",
    "materials/STUDY_PROTOCOL_AND_DEVIATIONS.md",
    "materials/STUDY_PROTOCOL_AND_DEVIATIONS.json",
    "materials/STATISTICAL_REPORTING_APPENDIX.md",
    "materials/STATISTICAL_REPORTING_APPENDIX.json",
    "materials/SUBMISSION_METADATA_DRAFT.md",
    "materials/SUBMISSION_METADATA_DRAFT.json",
    "materials/SUBMISSION_PORTAL_FIELD_COMPLETION_PACK.md",
    "materials/SUBMISSION_PORTAL_FIELD_COMPLETION_PACK.json",
    "materials/SUBMISSION_PORTAL_PACKAGE_MAP.md",
    "materials/SUBMISSION_PORTAL_PACKAGE_MAP.json",
    "materials/SUBMISSION_READINESS_DASHBOARD.md",
    "materials/SUBMISSION_READINESS_DASHBOARD.json",
    "materials/SUPPLEMENTARY_MATERIALS_INDEX.md",
    "materials/SUPPLEMENTARY_MATERIALS_INDEX.json",
    "materials/SUPPLEMENTARY_TABLE_LEGENDS.md",
    "materials/SUPPLEMENTARY_TABLE_LEGENDS.json",
    "materials/TARGET_JOURNAL_COMPLIANCE_MATRIX.md",
    "materials/TARGET_JOURNAL_COMPLIANCE_MATRIX.json",
    "materials/TARGET_JOURNAL_UPLOAD_DECISION_CHECKLIST.md",
    "materials/TARGET_JOURNAL_UPLOAD_DECISION_CHECKLIST.json",
    "materials/TITLE_ABSTRACT_HIGHLIGHTS_PACKAGE.md",
    "materials/TITLE_ABSTRACT_HIGHLIGHTS_PACKAGE.json",
    "materials/TOP_JOURNAL_REPORTING_SUMMARY.md",
    "materials/TOP_JOURNAL_REPORTING_SUMMARY.json",
    "materials/TRANSPARENT_REPORTING_CHECKLIST.md",
    "materials/TRANSPARENT_REPORTING_CHECKLIST.json",
    "tables/artifact_provenance.md",
    "tables/artifact_provenance.json",
}

TEXT_SUFFIXES = {".md", ".csv"}
JSON_SUFFIXES = {".json"}


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def rel(path, root):
    return path.relative_to(root).as_posix()


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


def should_scan(path, root):
    if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES | JSON_SUFFIXES:
        return False
    rel_path = rel(path, root)
    if rel_path in SELF_OUTPUTS:
        return False
    return rel_path in SCAN_FILES


def walk_json(value, pointer=""):
    if isinstance(value, dict):
        for key, child in value.items():
            child_pointer = f"{pointer}.{key}" if pointer else str(key)
            yield from walk_json(child, child_pointer)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            child_pointer = f"{pointer}[{index}]"
            yield from walk_json(child, child_pointer)
    else:
        yield pointer, value


def canonical_values(root):
    release = load_json(root / "materials" / "RELEASE_ARCHIVE_MANIFEST.json")
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    smoke = load_json(root / "materials" / "PUBLICATION_SMOKE_TEST.json")
    dictionary = load_json(root / "materials" / "DATA_DICTIONARY.json")
    provenance = load_json(root / "tables" / "artifact_provenance.json")
    artifact_ratio = f"{provenance['complete_count']}/{len(provenance['artifacts'])}"
    return {
        "release_file_count": release["summary"]["file_count"],
        "data_dictionary_complete": dictionary["summary"]["complete"],
        "data_dictionary_table_count": dictionary["summary"]["table_count"],
        "artifact_provenance": artifact_ratio,
    }


def scan_json(path, root, canonical):
    rows = []
    try:
        data = load_json(path)
    except Exception as exc:
        add_row(
            rows,
            "CRF_json_parse",
            "json_parse",
            "fail",
            "valid JSON",
            repr(exc),
            rel(path, root),
            "file",
            "JSON file could not be parsed for freshness checks.",
        )
        return rows
    exact_keys = {
        "release_file_count": canonical["release_file_count"],
        "data_dictionary_complete": canonical["data_dictionary_complete"],
        "data_dictionary_table_count": canonical["data_dictionary_table_count"],
        "artifact_provenance": canonical["artifact_provenance"],
    }
    for pointer, value in walk_json(data):
        key = re.sub(r"\[\d+\]$", "", pointer.split(".")[-1])
        if key not in exact_keys:
            continue
        if key == "artifact_provenance" and not isinstance(value, str):
            continue
        if value != exact_keys[key]:
            add_row(
                rows,
                f"CRF_json_{key}",
                "json_freshness",
                "fail",
                str(exact_keys[key]),
                str(value),
                rel(path, root),
                pointer,
                "Machine-readable cross-report snapshot drifted from the current authoritative package value.",
            )
    return rows


def scan_text(path, root, canonical):
    rows = []
    text = path.read_text(encoding="utf-8", errors="replace").splitlines()
    patterns = [
        (
            "CRF_text_artifact_provenance",
            "text_artifact_ratio",
            re.compile(r"\bprovenance\s*=\s*(\d+\s*/\s*\d+)\b", re.IGNORECASE),
            canonical["artifact_provenance"],
            "Inline provenance snapshots should match tables/artifact_provenance.json.",
        ),
    ]
    release_patterns = [
        re.compile(r"release manifest lists\s+(\d+)\s+files\s+and\s+(\d+)\s+bytes", re.IGNORECASE),
        re.compile(r"local release manifest lists\s+(\d+)\s+files\s+and\s+(\d+)\s+bytes", re.IGNORECASE),
    ]
    for line_number, line in enumerate(text, start=1):
        for check_id, category, pattern, expected, note in patterns:
            for match in pattern.finditer(line):
                observed = re.sub(r"\s+", "", match.group(1))
                normalized_expected = re.sub(r"\s+", "", str(expected))
                if observed.lower() != normalized_expected.lower():
                    add_row(
                        rows,
                        check_id,
                        category,
                        "fail",
                        str(expected),
                        match.group(1),
                        rel(path, root),
                        f"line {line_number}",
                        note,
                    )
        for pattern in release_patterns:
            for match in pattern.finditer(line):
                observed_files = int(match.group(1))
                observed_bytes = int(match.group(2))
                if observed_files != canonical["release_file_count"]:
                    add_row(
                        rows,
                        "CRF_text_release_manifest",
                        "text_release_snapshot",
                        "fail",
                        f"{canonical['release_file_count']} files",
                        f"{observed_files} files and {observed_bytes} bytes",
                        rel(path, root),
                        f"line {line_number}",
                        "Reviewer-facing release-manifest snapshots should match RELEASE_ARCHIVE_MANIFEST.json.",
                    )
    return rows


def build_report(root):
    canonical = canonical_values(root)
    rows = []
    add_row(
        rows,
        "CRF_authoritative_values_loaded",
        "authoritative_source",
        "pass",
        "current package values loaded",
        json.dumps(canonical, sort_keys=True),
        "materials/RELEASE_ARCHIVE_MANIFEST.json; materials/PUBLICATION_PACKAGE_VERIFICATION.json; materials/PUBLICATION_SMOKE_TEST.json; materials/DATA_DICTIONARY.json; tables/artifact_provenance.json",
        "summary",
        "Authoritative values used for cross-report freshness checks.",
    )
    scanned_files = 0
    for path in sorted(root.rglob("*")):
        if not should_scan(path, root):
            continue
        scanned_files += 1
        if path.suffix.lower() in JSON_SUFFIXES:
            rows.extend(scan_json(path, root, canonical))
        else:
            rows.extend(scan_text(path, root, canonical))
    failed = [row for row in rows if row["status"] != "pass"]
    return {
        "root": str(root),
        "title": "Cross-report freshness audit",
        "purpose": (
            "Check reviewer-facing reports for stale local snapshots of package-gate status, release-manifest "
            "counts, artifact-provenance ratios, and data-dictionary counts after regeneration-order changes."
        ),
        "summary": {
            "status": "pass" if not failed else "fail",
            "row_count": len(rows),
            "failed_row_count": len(failed),
            "scanned_file_count": scanned_files,
            **canonical,
        },
        "rows": rows,
        "interpretation": (
            "This audit is a freshness guard over saved reports. It does not treat author-owned DOI, ORCID, "
            "funding, conflict, or target-journal fields as local evidence defects."
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
        "# Cross-report freshness audit",
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
        safe = {key: str(value).replace("|", "\\|") for key, value in row.items()}
        lines.append(
            "| {check_id} | {category} | {status} | {expected} | {observed} | `{file}` | {location} | {note} |".format(
                **safe
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
    out_json = materials / "CROSS_REPORT_FRESHNESS_AUDIT.json"
    out_md = materials / "CROSS_REPORT_FRESHNESS_AUDIT.md"
    out_csv = materials / "CROSS_REPORT_FRESHNESS_AUDIT.csv"
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
