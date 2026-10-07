#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def csv_header(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return next(csv.reader(handle))


def legend_row(item, root, dictionary_paths):
    path = root / item["path"]
    columns = csv_header(path) if path.exists() and path.suffix.lower() == ".csv" else []
    dictionary_status = "covered" if item["path"] in dictionary_paths else "not_in_package_dictionary"
    caption = (
        f"{item['display_label']} This file contains {item['role']} "
        f"The table should be interpreted under the following boundary: {item['claim_boundary']}"
    )
    return {
        "id": item["id"],
        "display_label": item["display_label"],
        "upload_group": item["upload_group"],
        "path": item["path"],
        "source": item["source"],
        "caption": caption,
        "role": item["role"],
        "claim_boundary": item["claim_boundary"],
        "priority": item["priority"],
        "column_count": len(columns),
        "key_columns": ", ".join(columns[:8]),
        "dictionary_status": dictionary_status,
        "dictionary_file": "materials/DATA_DICTIONARY.md"
        if dictionary_status == "covered"
        else "figures/figure_3_source_data_dictionary.csv"
        if item["path"] == "figures/figure_3_source_data.csv"
        else "not_registered",
        "journal_action": (
            "Convert label, numbering, and caption style to the selected journal supplement template; "
            "keep claim-boundary sentence visible."
        ),
        "status": "ready" if item["status"] == "ready" and columns else "review_required",
    }


def build_report(root):
    supplement = load_json(root / "materials" / "SUPPLEMENTARY_MATERIALS_INDEX.json")
    dictionary = load_json(root / "materials" / "DATA_DICTIONARY.json")
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    smoke = load_json(root / "materials" / "PUBLICATION_SMOKE_TEST.json")
    provenance = load_json(root / "tables" / "artifact_provenance.json")
    figure_audit = load_json(root / "materials" / "FIGURE_SOURCE_DATA_AUDIT.json")
    stats = load_json(root / "materials" / "STATISTICAL_CONSISTENCY_AUDIT.json")

    dictionary_paths = {row["path"] for row in dictionary["tables"] if row["exists"]}
    included_groups = {"supplementary_table", "source_data"}
    rows = [
        legend_row(item, root, dictionary_paths)
        for item in supplement["items"]
        if item["upload_group"] in included_groups
    ]
    review_required = [row for row in rows if row["status"] != "ready"]
    return {
        "root": str(root),
        "title": "Supplementary Table and Source-Data Legends",
        "purpose": (
            "Provide journal-adaptable captions and interpretation boundaries for supplementary tables "
            "and source-data CSV files, linked to the package data dictionary."
        ),
        "scope": {
            "not_final_journal_numbering": True,
            "caption_boundary": (
                "Captions are conservative draft legends for reviewer clarity; final numbering, table titles, "
                "and journal style remain author actions."
            ),
            "source_data_boundary": figure_audit["interpretation"],
            "statistical_boundary": stats["interpretation"],
        },
        "legends": rows,
        "summary": {
            "status": "pass" if not review_required else "review_required",
            "legend_count": len(rows),
            "supplementary_table_count": sum(1 for row in rows if row["upload_group"] == "supplementary_table"),
            "source_data_count": sum(1 for row in rows if row["upload_group"] == "source_data"),
            "dictionary_covered_count": sum(1 for row in rows if row["dictionary_status"] == "covered"),
            "review_required_count": len(review_required),
            "publication_verification_status": verification["summary"]["status"],
            "publication_smoke_test_reference": "materials/PUBLICATION_SMOKE_TEST.json",
            "artifact_provenance": f"{provenance['complete_count']}/{len(provenance['artifacts'])}",
            "data_dictionary_complete": dictionary["summary"]["complete"],
            "supplementary_index_status": "pass"
            if supplement["summary"]["review_required_count"] == 0
            else "review_required",
        },
        "interpretation": (
            "This legend pack improves review readability and upload preparation. It does not add new results, "
            "change endpoints, or broaden simulator-only claims."
        ),
    }


def write_csv(report, path):
    fields = [
        "id",
        "display_label",
        "upload_group",
        "path",
        "source",
        "caption",
        "role",
        "claim_boundary",
        "priority",
        "column_count",
        "key_columns",
        "dictionary_status",
        "dictionary_file",
        "journal_action",
        "status",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(report["legends"])


def write_markdown(report, path):
    lines = [
        "# Supplementary Table and Source-Data Legends",
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
    lines.extend(["", "## Legends", ""])
    for row in report["legends"]:
        lines.extend(
            [
                f"### {row['id']}. {row['display_label']}",
                "",
                f"- File: `{row['path']}`",
                f"- Source: `{row['source']}`",
                f"- Caption: {row['caption']}",
                f"- Key columns: {row['key_columns']}",
                f"- Dictionary: `{row['dictionary_file']}` ({row['dictionary_status']})",
                f"- Journal action: {row['journal_action']}",
                f"- Status: {row['status']}",
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export supplementary table and source-data legends.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_report(root)
    out_json = materials / "SUPPLEMENTARY_TABLE_LEGENDS.json"
    out_md = materials / "SUPPLEMENTARY_TABLE_LEGENDS.md"
    out_csv = materials / "SUPPLEMENTARY_TABLE_LEGENDS.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(report, out_csv)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "csv": str(out_csv), "summary": report["summary"]}, indent=2))


if __name__ == "__main__":
    main()
