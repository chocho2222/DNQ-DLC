#!/usr/bin/env python
import argparse
import csv
import json
import re
from pathlib import Path


SELF_OUTPUTS = {
    "materials/NARRATIVE_NUMERIC_CONSISTENCY_AUDIT.md",
    "materials/NARRATIVE_NUMERIC_CONSISTENCY_AUDIT.json",
    "materials/NARRATIVE_NUMERIC_CONSISTENCY_AUDIT.csv",
}

SKIP_PREFIXES = {
    "CROSS_MATERIAL_CONSISTENCY_AUDIT",
    "FINAL_CHECKSUM_FREEZE_RECORD",
    "NARRATIVE_NUMERIC_CONSISTENCY_AUDIT",
    "PUBLICATION_SMOKE_TEST",
    "RELEASE_ARCHIVE_MANIFEST",
}


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def rel(path, root):
    return path.relative_to(root).as_posix()


def should_scan(path, root):
    if not path.is_file() or path.suffix.lower() not in {".md", ".csv"}:
        return False
    rel_path = rel(path, root)
    if rel_path in SELF_OUTPUTS:
        return False
    parts = Path(rel_path).parts
    if len(parts) >= 2 and parts[0] == "materials" and parts[1] == "scripts":
        return False
    if parts[0] not in {"materials", "tables"}:
        return False
    stem = path.stem
    return not any(stem.startswith(prefix) for prefix in SKIP_PREFIXES)


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


def scan_text(path, root, canonical):
    rows = []
    checks = [
        {
            "check_id": "NN_smoke_check_count",
            "category": "narrative_count",
            "context": re.compile(r"\bsmoke(?:[- ]test)?\b", re.IGNORECASE),
            "pattern": re.compile(r"\b(\d+)\s+smoke\s+checks\b", re.IGNORECASE),
            "expected": str(canonical["smoke_check_count"]),
            "note": "Narrative smoke-test check counts should match PUBLICATION_SMOKE_TEST.json.",
        },
        {
            "check_id": "NN_statistical_consistency_check_count",
            "category": "narrative_count",
            "context": re.compile(r"\bstatistical\s+consistency\b", re.IGNORECASE),
            "pattern": re.compile(r"\b(\d+)\s+checks\b", re.IGNORECASE),
            "expected": str(canonical["statistical_consistency_check_count"]),
            "note": "Narrative statistical-consistency check counts should match STATISTICAL_CONSISTENCY_AUDIT.json.",
        },
        {
            "check_id": "NN_statistical_plan_check_count",
            "category": "narrative_count",
            "context": re.compile(r"\bstatistical\s+analysis\s+plan\b", re.IGNORECASE),
            "pattern": re.compile(r"\b(\d+)\s+checks\b", re.IGNORECASE),
            "expected": str(canonical["statistical_plan_check_count"]),
            "note": "Narrative statistical-analysis-plan audit counts should match STATISTICAL_ANALYSIS_PLAN_AUDIT.json.",
        },
        {
            "check_id": "NN_data_dictionary_table_count",
            "category": "narrative_count",
            "context": re.compile(r"\bdata\s+dictionary\b", re.IGNORECASE),
            "pattern": re.compile(r"\b(\d+)\s+tables?\b", re.IGNORECASE),
            "expected": str(canonical["data_dictionary_table_count"]),
            "note": "Narrative data-dictionary table counts should match DATA_DICTIONARY.json.",
        },
    ]
    release_pattern = re.compile(r"\b(\d+)\s+files?\s*;\s*(\d+)\s+bytes\b", re.IGNORECASE)
    release_pattern_comma = re.compile(r"\b(\d+)\s+files?,\s+(\d+)\s+bytes\b", re.IGNORECASE)

    for line_number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
        lower = line.lower()
        for spec in checks:
            if not spec["context"].search(line):
                continue
            for match in spec["pattern"].finditer(line):
                observed = match.group(1)
                if observed != spec["expected"]:
                    add_row(
                        rows,
                        spec["check_id"],
                        spec["category"],
                        "fail",
                        spec["expected"],
                        observed,
                        rel(path, root),
                        f"line {line_number}",
                        spec["note"],
                    )
        if "release manifest" in lower or "release_file_count" in lower:
            for pattern in (release_pattern, release_pattern_comma):
                for match in pattern.finditer(line):
                    observed_files = int(match.group(1))
                    observed_bytes = int(match.group(2))
                    if (
                        observed_files != canonical["release_file_count"]
                    ):
                        add_row(
                            rows,
                            "NN_release_manifest_file_count",
                            "narrative_release_metadata",
                            "fail",
                            f"{canonical['release_file_count']} files",
                            f"{observed_files} files; {observed_bytes} bytes",
                            rel(path, root),
                            f"line {line_number}",
                            "Narrative release-manifest file counts should match RELEASE_ARCHIVE_MANIFEST.json; byte-level integrity is checked by FINAL_CHECKSUM_FREEZE_RECORD.",
                        )
    return rows


def build_report(root):
    release = load_json(root / "materials" / "RELEASE_ARCHIVE_MANIFEST.json")
    smoke = load_json(root / "materials" / "PUBLICATION_SMOKE_TEST.json")
    stats = load_json(root / "materials" / "STATISTICAL_CONSISTENCY_AUDIT.json")
    sap = load_json(root / "materials" / "STATISTICAL_ANALYSIS_PLAN_AUDIT.json")
    dictionary = load_json(root / "materials" / "DATA_DICTIONARY.json")
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    provenance = load_json(root / "tables" / "artifact_provenance.json")

    canonical = {
        "release_file_count": release["summary"]["file_count"],
        "release_size_reference": "materials/RELEASE_ARCHIVE_MANIFEST.json",
        "smoke_check_count": smoke["summary"]["check_count"],
        "statistical_consistency_check_count": stats["summary"]["check_count"],
        "statistical_plan_check_count": sap["summary"]["check_count"],
        "data_dictionary_table_count": dictionary["summary"]["table_count"],
        "artifact_provenance": f"{provenance['complete_count']}/{len(provenance['artifacts'])}",
        "publication_verification_status": verification["summary"]["status"],
    }

    rows = []
    add_row(
        rows,
        "NN_authoritative_counts_loaded",
        "authoritative_source",
        "pass",
        "canonical narrative counts loaded",
        json.dumps(canonical, sort_keys=True),
        "materials/PUBLICATION_SMOKE_TEST.json; materials/STATISTICAL_CONSISTENCY_AUDIT.json; materials/STATISTICAL_ANALYSIS_PLAN_AUDIT.json; materials/DATA_DICTIONARY.json; materials/RELEASE_ARCHIVE_MANIFEST.json",
        "summary",
        "Authoritative counts used for narrative numeric consistency checks.",
    )

    scanned_files = 0
    for path in sorted(root.rglob("*")):
        if should_scan(path, root):
            scanned_files += 1
            rows.extend(scan_text(path, root, canonical))

    failed = [row for row in rows if row["status"] != "pass"]
    return {
        "root": str(root),
        "title": "Narrative numeric consistency audit",
        "purpose": (
            "Check reviewer-facing prose and CSV text for stale narrative counts that are not fully covered by "
            "machine-readable status audits, such as smoke-test check counts and data-dictionary table counts."
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
            "This audit is static and prose-focused. It does not recompute experiments; it guards against stale "
            "reviewer-facing numeric statements after adding or removing package checks."
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
        "# Narrative numeric consistency audit",
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
    out_json = materials / "NARRATIVE_NUMERIC_CONSISTENCY_AUDIT.json"
    out_md = materials / "NARRATIVE_NUMERIC_CONSISTENCY_AUDIT.md"
    out_csv = materials / "NARRATIVE_NUMERIC_CONSISTENCY_AUDIT.csv"
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
