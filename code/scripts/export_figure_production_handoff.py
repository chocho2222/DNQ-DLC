#!/usr/bin/env python
import argparse
import csv
import json
from pathlib import Path


MB = 1024 * 1024


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def size_mb(size_bytes):
    if size_bytes in {"", None}:
        return ""
    return round(size_bytes / MB, 3)


def manifest_map(release):
    return {item["path"]: item for item in release["files"]}


def figure_label(figure):
    return {
        "figure_1": "figure_1_multicar_overtake_results",
        "figure_2": "figure_2_portfolio_selector_summary",
        "figure_3": "figure_3_cross_heldout_validation",
    }.get(figure, figure)


def production_channel(file_row):
    fmt = file_row["format"]
    size = file_row["size_bytes"]
    if fmt == "tiff":
        return "production_raster_or_large_file_channel" if size > 50 * MB else "production_raster_upload"
    if fmt == "pdf":
        return "review_or_production_vector_upload"
    if fmt == "svg":
        return "editable_vector_or_production_support"
    if fmt == "png":
        return "review_preview_or_visual_qc"
    return "author_review"


def production_note(file_row):
    fmt = file_row["format"]
    if fmt == "tiff":
        return "Use when the journal requires high-resolution raster figures; route large TIFFs through the journal large-file channel if needed."
    if fmt == "pdf":
        return "Use as the lightweight review or production figure when the journal accepts PDF vector graphics."
    if fmt == "svg":
        return "Use for editability checks and production support when the journal accepts SVG or requests vector sources."
    if fmt == "png":
        return "Use only for reviewer preview or visual QC; do not treat PNG as the archival raster substitute for TIFF."
    return "Confirm target-journal requirements before upload."


def build_report(root):
    figure_qc = load_json(root / "materials" / "FIGURE_TECHNICAL_QC.json")
    source_audit = load_json(root / "materials" / "FIGURE_SOURCE_DATA_AUDIT.json")
    legends = load_json(root / "materials" / "FIGURE_LEGENDS.json")
    size_budget = load_json(root / "materials" / "ARCHIVE_SIZE_BUDGET_REPORT.json")
    slim = load_json(root / "materials" / "SLIM_SUBMISSION_PACKAGE_MANIFEST.json")
    verification = load_json(root / "materials" / "PUBLICATION_PACKAGE_VERIFICATION.json")
    smoke = load_json(root / "materials" / "PUBLICATION_SMOKE_TEST.json")
    release = load_json(root / "materials" / "RELEASE_ARCHIVE_MANIFEST.json")
    release_by_path = manifest_map(release)

    source_by_short = {}
    for row in source_audit["figures"]:
        source_by_short[row["source_data"]] = row
        source_by_short[row["figure"]] = row

    legend_by_figure = {row["figure"]: row for row in legends["legends"]}
    legend_by_figure.update({figure_label(row["figure"]): row for row in figure_qc["figures"] if figure_label(row["figure"]) in legend_by_figure})

    figure_rows = []
    file_rows = []
    source_rows = []
    for fig in figure_qc["figures"]:
        label = figure_label(fig["figure"])
        source = source_by_short.get(fig["source_data"]) or source_by_short.get(label, {})
        legend = legend_by_figure.get(label, {})
        tiff_large = False
        figure_files = [row for row in figure_qc["files"] if row["figure"] == fig["figure"]]
        for file_row in figure_files:
            rel_path = file_row["path"]
            manifest_item = release_by_path.get(rel_path, {})
            large_file_status = "large_file_review" if file_row["size_bytes"] > 50 * MB else "standard_file_size"
            if file_row["format"] == "tiff" and file_row["size_bytes"] > 50 * MB:
                tiff_large = True
            file_rows.append(
                {
                    "figure": fig["figure"],
                    "path": rel_path,
                    "format": file_row["format"],
                    "upload_role": production_channel(file_row),
                    "size_bytes": file_row["size_bytes"],
                    "size_mb": size_mb(file_row["size_bytes"]),
                    "sha256": manifest_item.get("sha256", ""),
                    "technical_status": file_row["technical_status"],
                    "in_release_manifest": file_row["in_release_manifest"],
                    "large_file_status": large_file_status,
                    "production_note": production_note(file_row),
                    "boundary": "Figure export supports simulator-only claims and must remain linked to source data and legends after production edits.",
                    "status": "ready" if file_row["technical_status"] == "pass" and file_row["in_release_manifest"] else "review_required",
                }
            )
        source_rows.append(
            {
                "figure": fig["figure"],
                "path": fig["source_data"],
                "role": "source_data",
                "source_rows": fig["source_rows"],
                "source_columns": fig["source_columns"],
                "status": "ready" if fig["source_rows"] > 0 and fig["source_columns"] > 0 else "review_required",
                "production_note": "Upload as source data or include in the public archive according to the target journal policy.",
                "boundary": "Source data cover saved simulator seed partitions only.",
            }
        )
        figure_rows.append(
            {
                "figure": fig["figure"],
                "display_label": label,
                "status": "ready" if fig["status"] == "pass" and fig["accessibility_status"] == "pass" and source.get("complete") else "review_required",
                "manifest": fig["manifest"],
                "source_data": fig["source_data"],
                "legend_title": legend.get("title", ""),
                "panel_count": fig["panel_count"],
                "format_count": fig["format_count"],
                "tiff_width_px": fig["tiff_width_px"],
                "tiff_height_px": fig["tiff_height_px"],
                "tiff_x_dpi": fig["tiff_x_dpi"],
                "tiff_y_dpi": fig["tiff_y_dpi"],
                "accessibility_status": fig["accessibility_status"],
                "source_data_audit_complete": fig["source_data_audit_complete"],
                "large_tiff_routing_required": tiff_large,
                "production_note": "Keep panel labels, confidence intervals, strict PASS/FAIL wording, and simulator-only boundaries visible after journal resizing.",
                "boundary": "Figure production handoff is packaging guidance, not new scientific validation.",
            }
        )

    review_required = [row for row in figure_rows + file_rows + source_rows if row["status"] == "review_required"]
    large_tiffs = [row for row in file_rows if row["format"] == "tiff" and row["large_file_status"] == "large_file_review"]
    total_figure_bytes = sum(row["size_bytes"] for row in file_rows if isinstance(row["size_bytes"], int))

    return {
        "root": str(root),
        "title": "Figure Production Handoff",
        "purpose": (
            "Provide a journal-production handoff for figures, export formats, source data, legends, "
            "large-file routing, and claim-boundary preservation."
        ),
        "summary": {
            "status": "pass" if not review_required else "review_required",
            "figure_count": len(figure_rows),
            "figure_file_count": len(file_rows),
            "source_data_file_count": len(source_rows),
            "review_required_count": len(review_required),
            "large_tiff_count": len(large_tiffs),
            "figure_export_size_bytes": total_figure_bytes,
            "figure_export_size_mb": size_mb(total_figure_bytes),
            "figure_qc_status": figure_qc["summary"]["status"],
            "figure_source_complete_count": source_audit["summary"]["complete_count"],
            "figure_source_incomplete_count": source_audit["summary"]["incomplete_count"],
            "publication_verification_status": verification["summary"]["status"],
            "publication_smoke_test_reference": "materials/PUBLICATION_SMOKE_TEST.json",
            "archive_size_budget_status": size_budget["summary"]["status"],
            "slim_package_large_tiff_count": slim["summary"]["large_tiff_count"],
        },
        "figures": figure_rows,
        "files": file_rows,
        "source_data": source_rows,
        "interpretation": (
            "This handoff is journal-neutral production guidance. Authors must still follow the selected journal's "
            "figure-format, source-data, accessibility, and large-file upload rules."
        ),
    }


def write_csv(rows, path, fields):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def write_markdown(report, path):
    lines = [
        "# Figure Production Handoff",
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
            "## Figure Rows",
            "",
            "| figure | status | source data | formats | TIFF DPI | large TIFF | production note | boundary |",
            "|---|---|---|---:|---|---|---|---|",
        ]
    )
    for row in report["figures"]:
        lines.append(
            f"| {row['figure']} | {row['status']} | `{row['source_data']}` | {row['format_count']} | "
            f"{row['tiff_x_dpi']}x{row['tiff_y_dpi']} | {row['large_tiff_routing_required']} | "
            f"{row['production_note']} | {row['boundary']} |"
        )
    lines.extend(
        [
            "",
            "## Export Files",
            "",
            "| figure | format | role | status | size MB | path | production note |",
            "|---|---|---|---|---:|---|---|",
        ]
    )
    for row in report["files"]:
        lines.append(
            f"| {row['figure']} | {row['format']} | {row['upload_role']} | {row['status']} | "
            f"{row['size_mb']} | `{row['path']}` | {row['production_note']} |"
        )
    lines.extend(
        [
            "",
            "## Source Data",
            "",
            "| figure | status | rows | columns | path | production note | boundary |",
            "|---|---|---:|---:|---|---|---|",
        ]
    )
    for row in report["source_data"]:
        lines.append(
            f"| {row['figure']} | {row['status']} | {row['source_rows']} | {row['source_columns']} | "
            f"`{row['path']}` | {row['production_note']} | {row['boundary']} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export figure production handoff.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    args = parser.parse_args()
    root = Path(args.root)
    materials = root / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    report = build_report(root)
    out_json = materials / "FIGURE_PRODUCTION_HANDOFF.json"
    out_md = materials / "FIGURE_PRODUCTION_HANDOFF.md"
    figure_csv = materials / "FIGURE_PRODUCTION_HANDOFF.csv"
    file_csv = materials / "FIGURE_PRODUCTION_HANDOFF_FILES.csv"
    source_csv = materials / "FIGURE_PRODUCTION_HANDOFF_SOURCE_DATA.csv"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    write_csv(
        report["figures"],
        figure_csv,
        [
            "figure",
            "display_label",
            "status",
            "manifest",
            "source_data",
            "legend_title",
            "panel_count",
            "format_count",
            "tiff_width_px",
            "tiff_height_px",
            "tiff_x_dpi",
            "tiff_y_dpi",
            "accessibility_status",
            "source_data_audit_complete",
            "large_tiff_routing_required",
            "production_note",
            "boundary",
        ],
    )
    write_csv(
        report["files"],
        file_csv,
        [
            "figure",
            "path",
            "format",
            "upload_role",
            "size_bytes",
            "size_mb",
            "sha256",
            "technical_status",
            "in_release_manifest",
            "large_file_status",
            "production_note",
            "boundary",
            "status",
        ],
    )
    write_csv(
        report["source_data"],
        source_csv,
        ["figure", "path", "role", "source_rows", "source_columns", "status", "production_note", "boundary"],
    )
    print(
        json.dumps(
            {
                "json": str(out_json),
                "markdown": str(out_md),
                "figure_csv": str(figure_csv),
                "file_csv": str(file_csv),
                "source_csv": str(source_csv),
                "summary": report["summary"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
