#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def csv_shape(path):
    if not path.exists():
        return [], 0, 0, []
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))
    if not rows:
        return [], 0, 0, []
    header = rows[0]
    duplicate_columns = sorted({column for column in header if header.count(column) > 1})
    return header, max(0, len(rows) - 1), len(header), duplicate_columns


def priority_for(path, supplementary_paths, source_data_paths):
    if path in source_data_paths:
        return "source_data"
    if path in supplementary_paths:
        return "supplementary_table"
    if path.startswith("figures/") and path.endswith(".csv"):
        return "figure_source_or_dictionary"
    if path.startswith("tables/"):
        return "analysis_table"
    if path.startswith("materials/"):
        return "materials_table"
    return "other_machine_readable_table"


def build_report(root):
    dictionary = load_json(root / "materials" / "DATA_DICTIONARY.json")
    supplement = load_json(root / "materials" / "SUPPLEMENTARY_MATERIALS_INDEX.json")
    legends = load_json(root / "materials" / "SUPPLEMENTARY_TABLE_LEGENDS.json")
    release = load_json(root / "materials" / "RELEASE_ARCHIVE_MANIFEST.json")
    exclusion_path = root / "materials" / "ARCHIVE_MANIFEST_EXCLUSION_AUDIT.json"
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    smoke = load_json(root / "materials" / "PUBLICATION_SMOKE_TEST.json")

    release_by_path = {item["path"]: item for item in release["files"]}
    documented_exclusions = {}
    if exclusion_path.exists():
        exclusion = load_json(exclusion_path)
        documented_exclusions = {
            item["path"]: item
            for item in exclusion.get("rows", [])
            if item.get("status") == "pass" and item.get("exists") and not item.get("in_release_manifest")
        }
    supplementary_paths = {item["path"] for item in supplement["items"] if item["upload_group"] == "supplementary_table"}
    source_data_paths = {item["path"] for item in supplement["items"] if item["upload_group"] == "source_data"}
    legend_paths = {item["path"] for item in legends["legends"]}
    dictionary_paths = {item["path"] for item in dictionary["tables"] if item["exists"]}

    rows = []
    for table in dictionary["tables"]:
        rel = table["path"]
        path = root / rel
        header, row_count, column_count, duplicate_columns = csv_shape(path)
        missing_dictionary_fields = [
            column
            for column in header
            if not any(field["table"] == rel and field["field"] == column for field in dictionary["fields"])
        ]
        priority = priority_for(rel, supplementary_paths, source_data_paths)
        requires_rows = priority in {"source_data", "supplementary_table", "analysis_table"}
        in_release = rel in release_by_path
        documented_exclusion = rel in documented_exclusions
        status = "ready"
        reasons = []
        if not path.exists():
            status = "review_required"
            reasons.append("missing_file")
        if column_count == 0:
            status = "review_required"
            reasons.append("empty_or_missing_header")
        if requires_rows and row_count == 0:
            status = "review_required"
            reasons.append("no_data_rows")
        if duplicate_columns:
            status = "review_required"
            reasons.append("duplicate_columns")
        if missing_dictionary_fields:
            status = "review_required"
            reasons.append("missing_dictionary_fields")
        if not in_release and not documented_exclusion:
            status = "review_required"
            reasons.append("not_in_release_manifest")
        if documented_exclusion:
            reasons.append("documented_release_manifest_exclusion")
        rows.append(
            {
                "path": rel,
                "title": table["title"],
                "priority": priority,
                "source": table["source"],
                "row_count": row_count,
                "column_count": column_count,
                "dictionary_status": "covered" if rel in dictionary_paths and not missing_dictionary_fields else "review_required",
                "legend_status": "covered" if rel in legend_paths else "not_applicable_or_not_in_legend_set",
                "in_release_manifest": in_release,
                "release_manifest_status": "in_release_manifest" if in_release else "documented_exclusion" if documented_exclusion else "not_in_release_manifest",
                "size_bytes": release_by_path.get(rel, {}).get("size_bytes", path.stat().st_size if path.exists() else ""),
                "sha256": release_by_path.get(rel, {}).get("sha256", ""),
                "duplicate_columns": ";".join(duplicate_columns),
                "missing_dictionary_fields": ";".join(missing_dictionary_fields),
                "status": status,
                "reason": ";".join(reasons) if reasons else "table_ready",
                "boundary": "Machine-readable table audit checks packaging, headers, dictionary coverage, and release membership; it does not reinterpret scientific results.",
            }
        )

    review_required = [row for row in rows if row["status"] == "review_required"]
    priority_counts = {}
    for row in rows:
        priority_counts[row["priority"]] = priority_counts.get(row["priority"], 0) + 1

    return {
        "root": str(root),
        "title": "Machine-Readable Table Integrity Audit",
        "purpose": (
            "Audit package CSV tables for existence, non-empty headers, data rows where required, duplicate columns, "
            "data-dictionary coverage, release-manifest inclusion, and supplement/source-data legend coverage."
        ),
        "summary": {
            "status": "pass" if not review_required else "review_required",
            "table_count": len(rows),
            "review_required_count": len(review_required),
            "priority_counts": priority_counts,
            "source_data_count": sum(1 for row in rows if row["priority"] == "source_data"),
            "supplementary_table_count": sum(1 for row in rows if row["priority"] == "supplementary_table"),
            "dictionary_complete": dictionary["summary"]["complete"],
            "supplementary_index_status": "pass" if supplement["summary"]["review_required_count"] == 0 else "review_required",
            "supplementary_table_legends_status": legends["summary"]["status"],
            "publication_verification_status": verification["summary"]["status"],
            "publication_smoke_test_status": smoke["summary"]["status"],
            "release_file_count": release["summary"]["file_count"],
            "documented_release_exclusion_count": sum(1 for row in rows if row.get("release_manifest_status") == "documented_exclusion"),
        },
        "rows": rows,
        "interpretation": (
            "This audit is a packaging and metadata integrity check for CSV tables. Author-selected journal formatting, "
            "table numbering, and final upload slot choices remain outside local automation."
        ),
    }


def write_csv(report, path):
    fields = [
        "path",
        "title",
        "priority",
        "source",
        "row_count",
        "column_count",
        "dictionary_status",
        "legend_status",
        "in_release_manifest",
        "release_manifest_status",
        "size_bytes",
        "sha256",
        "duplicate_columns",
        "missing_dictionary_fields",
        "status",
        "reason",
        "boundary",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in report["rows"]:
            writer.writerow({field: row.get(field, "") for field in fields})


def write_markdown(report, path):
    lines = [
        "# Machine-Readable Table Integrity Audit",
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
            "## Tables",
            "",
            "| priority | status | rows | columns | dictionary | release | path | reason |",
            "|---|---|---:|---:|---|---|---|---|",
        ]
    )
    for row in report["rows"]:
        lines.append(
            f"| {row['priority']} | {row['status']} | {row['row_count']} | {row['column_count']} | "
            f"{row['dictionary_status']} | {row['release_manifest_status']} | `{row['path']}` | {row['reason']} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export machine-readable table integrity audit.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_report(root)
    out_json = materials / "MACHINE_READABLE_TABLE_INTEGRITY_AUDIT.json"
    out_md = materials / "MACHINE_READABLE_TABLE_INTEGRITY_AUDIT.md"
    out_csv = materials / "MACHINE_READABLE_TABLE_INTEGRITY_AUDIT.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv), "summary": report["summary"]}, indent=2))


if __name__ == "__main__":
    main()
