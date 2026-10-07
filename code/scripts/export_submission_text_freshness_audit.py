#!/usr/bin/env python
import argparse
import csv
import json
import re
from pathlib import Path


SCAN_FILES = [
    "materials/TITLE_ABSTRACT_HIGHLIGHTS_PACKAGE.md",
    "materials/TITLE_ABSTRACT_HIGHLIGHTS_PACKAGE.json",
    "materials/TITLE_ABSTRACT_HIGHLIGHTS_PACKAGE.csv",
    "materials/SUBMISSION_PORTAL_FIELD_COMPLETION_PACK.md",
    "materials/SUBMISSION_PORTAL_FIELD_COMPLETION_PACK.json",
    "materials/SUBMISSION_PORTAL_FIELD_COMPLETION_PACK.csv",
    "materials/SUBMISSION_PORTAL_PACKAGE_MAP.md",
    "materials/SUBMISSION_PORTAL_PACKAGE_MAP.json",
    "materials/SIGNIFICANCE_BRIEFING.md",
    "materials/SIGNIFICANCE_BRIEFING.json",
    "materials/COVER_LETTER_DRAFT_PACKAGE.md",
    "materials/COVER_LETTER_DRAFT_PACKAGE.json",
    "materials/EDITORIAL_NARRATIVE_PACKAGE.md",
    "materials/EDITORIAL_NARRATIVE_PACKAGE.json",
    "materials/TOP_JOURNAL_REPORTING_SUMMARY.md",
    "materials/TOP_JOURNAL_REPORTING_SUMMARY.json",
    "materials/EDITORIAL_SUBMISSION_CHECKLIST.md",
    "materials/EDITORIAL_SUBMISSION_CHECKLIST.json",
    "materials/SUBMISSION_READINESS_DASHBOARD.md",
    "materials/SUBMISSION_READINESS_DASHBOARD.json",
]


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def line_hits(root, rel_path, expected):
    path = root / rel_path
    if not path.exists():
        return [
            {
                "file": rel_path,
                "line": "",
                "check": "file_exists",
                "status": "fail",
                "observed": "missing",
                "expected": "present",
                "context": "",
            }
        ]

    rows = []
    text = path.read_text(encoding="utf-8", errors="replace")
    ratio_pattern = re.compile(r"\b\d{2,4}/\d{2,4}\b")

    for lineno, line in enumerate(text.splitlines(), start=1):
        low = line.lower()
        context = line.strip()[:700]
        if "artifact provenance" in low or "artifact_provenance" in low:
            for observed in ratio_pattern.findall(line):
                parts = observed.split("/")
                if int(parts[0]) < 100 or int(parts[1]) < 100:
                    continue
                if observed != expected["artifact_provenance"]:
                    rows.append(
                        {
                            "file": rel_path,
                            "line": lineno,
                            "check": "artifact_provenance_ratio",
                            "status": "fail",
                            "observed": observed,
                            "expected": expected["artifact_provenance"],
                            "context": context,
                        }
                    )
    return rows


def build_report(root):
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    smoke = load_json(root / "materials" / "PUBLICATION_SMOKE_TEST.json")
    provenance = load_json(root / "tables" / "artifact_provenance.json")
    release = load_json(root / "materials" / "RELEASE_ARCHIVE_MANIFEST.json")
    dictionary = load_json(root / "materials" / "DATA_DICTIONARY.json")

    expected = {
        "artifact_provenance": f"{provenance['complete_count']}/{len(provenance['artifacts'])}",
        "release_file_count": release["summary"]["file_count"],
        "release_size_reference": "materials/RELEASE_ARCHIVE_MANIFEST.json",
        "publication_verification_status": verification["summary"]["status"],
        "publication_smoke_test_reference": "materials/PUBLICATION_SMOKE_TEST.json",
        "data_dictionary_table_count": dictionary["summary"]["table_count"],
    }
    rows = []
    for rel_path in SCAN_FILES:
        rows.extend(line_hits(root, rel_path, expected))

    status = "pass" if not rows else "fail"
    by_check = {}
    for item in rows:
        by_check[item["check"]] = by_check.get(item["check"], 0) + 1

    return {
        "root": str(root),
        "title": "Submission Text Freshness Audit",
        "purpose": (
            "Scan journal-facing short-form and portal-draft text for stale local package counts, "
            "artifact-provenance ratios, and pass/fail status snapshots."
        ),
        "expected": expected,
        "rows": rows,
        "summary": {
            "status": status,
            "scanned_file_count": len(SCAN_FILES),
            "failed_row_count": len(rows),
            "failure_counts_by_check": by_check,
            "artifact_provenance": expected["artifact_provenance"],
            "release_file_count": expected["release_file_count"],
            "release_size_reference": expected["release_size_reference"],
            "publication_verification_status": expected["publication_verification_status"],
            "publication_smoke_test_reference": expected["publication_smoke_test_reference"],
            "data_dictionary_table_count": expected["data_dictionary_table_count"],
        },
        "interpretation": (
            "A pass status means selected journal-facing drafts do not contain stale local preflight counts or failed gate snapshots. "
            "It does not certify author-owned metadata, disclosures, target-journal formatting, or archive DOI fields."
        ),
    }


def write_csv(report, path):
    fields = ["file", "line", "check", "status", "observed", "expected", "context"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in report["rows"]:
            writer.writerow(item)


def write_markdown(report, path):
    lines = [
        "# Submission Text Freshness Audit",
        "",
        report["purpose"],
        "",
        report["interpretation"],
        "",
        "## Summary",
        "",
        f"- Status: `{report['summary']['status']}`",
        f"- Scanned files: {report['summary']['scanned_file_count']}",
        f"- Failed rows: {report['summary']['failed_row_count']}",
        f"- Artifact provenance: {report['summary']['artifact_provenance']}",
        f"- Release files: {report['summary']['release_file_count']}",
        f"- Release size reference: `{report['summary']['release_size_reference']}`",
        f"- Publication verification: `{report['summary']['publication_verification_status']}`",
        f"- Publication smoke test reference: `{report['summary']['publication_smoke_test_reference']}`",
        "",
        "## Failures",
        "",
    ]
    if report["rows"]:
        lines.extend(["| file | line | check | observed | expected | context |", "|---|---:|---|---|---|---|"])
        for item in report["rows"]:
            context = str(item["context"]).replace("|", "\\|")
            lines.append(
                f"| `{item['file']}` | {item['line']} | {item['check']} | `{item['observed']}` | `{item['expected']}` | {context} |"
            )
    else:
        lines.append("No stale submission-text snapshots detected.")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export submission text freshness audit.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_report(root)
    out_json = materials / "SUBMISSION_TEXT_FRESHNESS_AUDIT.json"
    out_md = materials / "SUBMISSION_TEXT_FRESHNESS_AUDIT.md"
    out_csv = materials / "SUBMISSION_TEXT_FRESHNESS_AUDIT.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv), "summary": report["summary"]}, indent=2))


if __name__ == "__main__":
    main()
